"""SOUL Cloud: the one ASGI app that goes on the internet (docs/07-CONNECT-AI.md §3.0, §3.12 `app.py`).

    python -m suflet_ai.app serve --host 0.0.0.0 --port 8080
    python -m suflet_ai.app check                       # production startup checks only, exit 1 on failure
    python -m suflet_ai.app import-factory keys.csv     # factory list: CSV with header "device_id,pub" (pub = b64url)

One process (Phase 0) holding, on one public host {BASE}:

- the device side (`gateway.py`): /v1/ping, /v1/device/challenge|auth|ws|poll|send, the relay (brain A / B2 / E);
- the SOUL connector (`mcp_remote.py`): /mcp (Streamable HTTP, OAuth 2.1), /authorize /token /register /revoke,
  both metadata documents, the sign-in and consent pages;
- /healthz for the platform's health check.

The legacy shared-token API (`server.py`) is never mounted here. The `/v1/dev/*` helpers (claim a pairing code,
push, config, a B2 key) are mounted only outside production and only when SUFLET_API_TOKEN is set.

`SOUL_ENV=production` refuses to start unless every rule of §3.0 holds (`assert_production_ready`).
"""
from __future__ import annotations

import argparse
import hmac
import logging
import os
import smtplib
import ssl
import sys
import threading
import time
from contextlib import asynccontextmanager
from email.message import EmailMessage
from typing import Any, Callable, Dict, List, Mapping, Optional

from fastapi import Depends, FastAPI, Header, HTTPException

from . import gateway as gateway_mod
from .accounts import DevMailbox, Mailer
from .mcp_remote import create_remote_app
from .soul import SoulService

log = logging.getLogger("suflet_ai.app")

VERSION = "0.3.0"

# Every variable the cloud reads. "secret" ones come from the platform's secret store, never from the repo.
ENV_VARS: List[Dict[str, Any]] = [
    {"name": "SOUL_ENV", "secret": False, "prod": True, "doc": "`production` or `pilot` (Phase 0 testers: same checks, `pending` enrolment allowed) turn on the startup checks; anything else is dev"},
    {"name": "SOUL_PUBLIC_HOST", "secret": False, "prod": True, "doc": "public host name, e.g. soul.example (no scheme); devices sign for it, OAuth issuer is https://{it}"},
    {"name": "SOUL_DATA_DIR", "secret": False, "prod": True, "doc": "where the SQLite files live (a persistent volume), e.g. /data"},
    {"name": "SOUL_ENROL_POLICY", "secret": False, "prod": True, "doc": "`factory` in production (only imported device keys); `pending` for dev builds"},
    {"name": "SOUL_TRUST_PROXY", "secret": False, "prod": True, "doc": "`1` behind the platform's TLS proxy (client IP = last X-Forwarded-For hop)"},
    {"name": "SOUL_MASTER_SECRET", "secret": True, "prod": True, "doc": ">= 32 bytes hex/base64; encrypts users' API keys (B2). Never let it fall back to <data>/master.key"},
    {"name": "SOUL_ID_PEPPER", "secret": True, "prod": True, "doc": ">= 32 random bytes hex; HMAC for ids, codes, safety_identifier"},
    {"name": "SOUL_ANTHROPIC_KEY", "secret": True, "prod": False, "doc": "SOUL's own Anthropic key for brain A (Claude inside SOUL)"},
    {"name": "SOUL_OPENAI_KEY", "secret": True, "prod": False, "doc": "SOUL's own OpenAI key for brain A when the owner picks the ChatGPT voice"},
    {"name": "SOUL_SMTP_HOST", "secret": False, "prod": True, "doc": "EU transactional mail server for sign-in codes (STARTTLS on 587, or TLS on 465)"},
    {"name": "SOUL_SMTP_PORT", "secret": False, "prod": False, "doc": "default 587"},
    {"name": "SOUL_SMTP_USER", "secret": False, "prod": False, "doc": "SMTP user name"},
    {"name": "SOUL_SMTP_PASSWORD", "secret": True, "prod": False, "doc": "SMTP password / API token"},
    {"name": "SOUL_MAIL_FROM", "secret": False, "prod": True, "doc": "sender, e.g. SOUL <hello@soul.example> (SPF/DKIM/DMARC set on the domain)"},
    {"name": "SOUL_CLAUDE_MODEL", "secret": False, "prod": False, "doc": "brain A/B2 Claude model (default claude-haiku-4-5)"},
    {"name": "SOUL_OPENAI_RELAY_MODEL", "secret": False, "prod": False, "doc": "brain A/B2 OpenAI model (default gpt-6-luna)"},
    {"name": "SOUL_ALLOWANCE_TURNS", "secret": False, "prod": False, "doc": "brain A turns per account per month (default 300) [E]"},
    {"name": "SOUL_TRIAL_TURNS", "secret": False, "prod": False, "doc": "trial turns of an unpaired factory unit (default 30) [E]"},
    {"name": "SOUL_B2_DAILY_CAP_MICRO", "secret": False, "prod": False, "doc": "per-device daily spend cap on the owner's own key, micro-USD (default 500000)"},
    {"name": "SOUL_BRAIN_A_KILL", "secret": False, "prod": False, "doc": "`1` moves brain A to the offline rules fleet-wide (spend emergency)"},
    {"name": "SOUL_BUILTIN_AI", "secret": False, "prod": False, "doc": "`1` turns on brain A (AI inside SOUL on SOUL's own keys, billed to SOUL). Default `0`: founder decision of 3 Oct 2026, SOUL includes no AI paid by us"},
    {"name": "SOUL_KEY_CHECK", "secret": False, "prod": False, "doc": "`0` skips the live check (GET /v1/models) of keys pasted on /me; they are saved as unverified"},
    {"name": "SUFLET_TZ", "secret": False, "prod": False, "doc": "server time zone for interpreting turns (default Europe/Bucharest)"},
    {"name": "SUFLET_API_TOKEN", "secret": True, "prod": False, "doc": "dev only: enables /v1/dev/*; production refuses to start when set"},
    {"name": "SOUL_PUBLIC_SCHEME", "secret": False, "prod": False, "doc": "dev only: `http` for a loopback test server; production is https only"},
    {"name": "SOUL_DEV_MAILBOX", "secret": False, "prod": False, "doc": "dev only: file (0600) that receives sign-in emails instead of SMTP"},
]


# ================================================================ startup checks ==

def production_problems(env: Mapping[str, str] = os.environ) -> List[str]:
    """Everything that makes this environment unfit for SOUL_ENV=production (§3.0). Never prints values.

    SOUL_ENV=pilot (a Phase 0 deployment for known testers, §3.2 "dev and P0 builds only") applies the same
    rules except that SOUL_ENROL_POLICY may be `pending`, because no factory key list exists yet."""
    p: List[str] = []
    pilot = env.get("SOUL_ENV") == "pilot"
    if env.get("SUFLET_API_TOKEN"):
        p.append("SUFLET_API_TOKEN is set: the legacy shared-token API must not exist in production")
    policy = env.get("SOUL_ENROL_POLICY", "pending")
    if policy != "factory" and not (pilot and policy == "pending"):
        p.append("SOUL_ENROL_POLICY must be 'factory'" + (" or 'pending'" if pilot else ""))
    if not env.get("SOUL_MASTER_SECRET"):
        p.append("SOUL_MASTER_SECRET missing (inject it from the secret manager; no master.key file in production)")
    if len(env.get("SOUL_ID_PEPPER", "")) < 32:
        p.append("SOUL_ID_PEPPER missing or shorter than 32 characters")
    host = env.get("SOUL_PUBLIC_HOST", "")
    if not host or "/" in host or host.startswith(("localhost", "127.")):
        p.append("SOUL_PUBLIC_HOST missing or not a public host name")
    if env.get("SOUL_PUBLIC_SCHEME", "https") != "https":
        p.append("SOUL_PUBLIC_SCHEME must be https (or unset)")
    if not env.get("SOUL_SMTP_HOST") or not env.get("SOUL_MAIL_FROM"):
        p.append("SOUL_SMTP_HOST / SOUL_MAIL_FROM missing: sign-in codes need a real mail sender")
    if env.get("SOUL_DEV_MAILBOX"):
        p.append("SOUL_DEV_MAILBOX is set (dev only)")
    return p


def assert_production_ready(env: Mapping[str, str] = os.environ) -> None:
    problems = production_problems(env)
    if problems:
        raise RuntimeError(f"SOUL_ENV={env.get('SOUL_ENV', '')} refused to start: " + "; ".join(problems))
    if env.get("SOUL_ENV") == "pilot" and env.get("SOUL_ENROL_POLICY", "pending") == "pending":
        log.warning("pilot: pending enrolment (whoever pairs a new device id first owns it); testers only")
    if not (env.get("SOUL_ANTHROPIC_KEY") or env.get("SOUL_OPENAI_KEY")):
        log.warning("no SOUL_ANTHROPIC_KEY / SOUL_OPENAI_KEY: brain A answers with the offline rules (note upstream)")


# ======================================================================== mail ==

class SmtpMailer:
    """Sign-in emails through an EU transactional SMTP relay. Logs the recipient domain only, never the body.

    `Accounts` calls the mailer inside a request handler on the event loop, so by default the SMTP exchange
    runs on a short-lived thread: a slow mail server must not stall every device socket."""

    def __init__(self, host: str, port: int = 587, user: str = "", password: str = "", sender: str = "",
                 timeout: float = 10.0, smtp_factory: Callable[..., Any] = None, background: bool = True):
        if not sender:
            raise ValueError("SOUL_MAIL_FROM is required")
        self.host, self.port, self.user, self._password = host, int(port), user, password
        self.sender, self.timeout = sender, timeout
        self._factory = smtp_factory
        self.background = background

    def __repr__(self) -> str:
        return f"SmtpMailer({self.host}:{self.port}, <credentials sealed>)"

    def __call__(self, to: str, subject: str, body: str) -> None:
        if not self.background:
            self._send(to, subject, body)
            return
        threading.Thread(target=self._send_logged, args=(to, subject, body), daemon=True).start()

    def _send_logged(self, to: str, subject: str, body: str) -> None:
        try:
            self._send(to, subject, body)
        except Exception as e:  # noqa: BLE001 - the user sees "no email" and can resend; ops sees the class
            log.error("sign-in mail to *@%s failed: %s", to.rpartition("@")[2], type(e).__name__)

    def _send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        if self._factory is not None:
            smtp = self._factory(self.host, self.port, timeout=self.timeout)
        elif self.port == 465:
            smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=ctx)
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
        with smtp as s:
            if self.port != 465 and self._factory is None:
                s.starttls(context=ctx)
            if self.user:
                s.login(self.user, self._password)
            s.send_message(msg)
        log.info("sign-in mail sent to *@%s", to.rpartition("@")[2])


def mailer_from_env(env: Mapping[str, str] = os.environ) -> Mailer:
    if env.get("SOUL_SMTP_HOST"):
        return SmtpMailer(env["SOUL_SMTP_HOST"], int(env.get("SOUL_SMTP_PORT", "587")), env.get("SOUL_SMTP_USER", ""),
                          env.get("SOUL_SMTP_PASSWORD", ""), env.get("SOUL_MAIL_FROM", ""))
    if env.get("SOUL_ENV") == "production":
        raise RuntimeError("production needs SOUL_SMTP_HOST for sign-in codes")
    return DevMailbox(env.get("SOUL_DEV_MAILBOX") or None)


# ========================================================================= app ==

def _dev_token_check(authorization: str = Header(default="")) -> None:
    token = os.environ.get("SUFLET_API_TOKEN", "")
    given = authorization.removeprefix("Bearer ").strip()
    if not token or not hmac.compare_digest(given, token):
        raise HTTPException(401, "bad token")


def create_app(*, service: Optional[SoulService] = None, gateway: Optional[gateway_mod.Gateway] = None,
               mailer: Optional[Mailer] = None, public_host: Optional[str] = None, scheme: Optional[str] = None,
               db_path: Optional[str] = None, clock: Callable[[], float] = time.time,
               cimd_fetch: Optional[Callable[[str], dict]] = None,
               key_check: Optional[Callable[[str, str], str]] = None) -> FastAPI:
    """The production composition: device routes + connector, one SoulService, one Gateway, one lifespan."""
    env = os.environ.get("SOUL_ENV", "dev")
    if env in ("production", "pilot"):
        assert_production_ready()
    scheme = scheme or os.environ.get("SOUL_PUBLIC_SCHEME", "https")
    service = service or SoulService()
    gw = gateway or gateway_mod.default_gateway(lambda: service)
    if gw.soul is not service:
        raise RuntimeError("the gateway and the connector must share one SoulService")
    gateway_mod.set_gateway(gw)
    mailer = mailer if mailer is not None else mailer_from_env()
    remote = create_remote_app(service, gw, public_host=public_host, scheme=scheme, db_path=db_path, mailer=mailer,
                               clock=clock, cimd_fetch=cimd_fetch, key_check=key_check)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with remote.router.lifespan_context(remote):  # the MCP session manager (§3.0 [U] -> tested)
            yield

    api = FastAPI(title="SOUL Cloud", version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None,
                  openapi_url=None)

    @api.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True, "version": VERSION}

    api.include_router(gateway_mod.build_router(lambda: gw))
    if env not in ("production", "pilot") and os.environ.get("SUFLET_API_TOKEN"):
        api.include_router(gateway_mod.build_dev_router(lambda: gw), dependencies=[Depends(_dev_token_check)])
    api.mount("/", remote)
    api.state.soul = remote.state.soul
    api.state.gateway = gw
    api.state.mailer = mailer
    return api


# ========================================================================= CLI ==

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="suflet_ai.app", description="SOUL Cloud")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    s.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    sub.add_parser("check", help="run the production startup checks and exit")
    f = sub.add_parser("import-factory", help="import factory device keys (CSV with header device_id,pub)")
    f.add_argument("csv")
    sub.add_parser("env", help="list the environment variables (names and meaning only)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if a.cmd == "check":  # checks the rules of SOUL_ENV=production (or pilot, when SOUL_ENV=pilot)
        problems = production_problems()
        for p in problems:
            print("FAIL", p)
        print("OK: production checks pass" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if a.cmd == "env":
        for v in ENV_VARS:
            print(f"{v['name']:<26} {'secret ' if v['secret'] else '       '}{'required ' if v['prod'] else '         '}"
                  f"{v['doc']}")
        return 0
    if a.cmd == "import-factory":
        gw = gateway_mod.default_gateway()
        n = gw.store.import_factory(a.csv)
        print(f"imported {n} device key(s)")
        return 0

    import uvicorn

    # proxy_headers off: our code reads the proxy's own X-Forwarded-For hop itself (SOUL_TRUST_PROXY=1);
    # access_log off: uvicorn would log query strings (§3.0 forbids it)
    uvicorn.run(create_app(), host=a.host, port=a.port, proxy_headers=False, ws_ping_interval=25,
                ws_ping_timeout=45, server_header=False, log_level="info", access_log=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
