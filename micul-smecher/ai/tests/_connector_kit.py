"""Shared test kit for the SOUL connector (remote MCP + OAuth): a stub gateway, a fake clock, a browser
that walks the sign-in / consent pages, and an in-process OAuth client built on the official MCP SDK.

No network: every HTTP request goes to the ASGI app in process (httpx2.ASGITransport).
"""
from __future__ import annotations

import datetime as dt
import html
import re
import time
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx2

from suflet_ai.accounts import DevMailbox
from suflet_ai.config import Settings
from suflet_ai.soul import SoulService
from suflet_ai.state import StateStore

HOST = "soul.test"
BASE = f"https://{HOST}"
MCP_URL = BASE + "/mcp"
DEV = "soul-a1b2c3d4e5f6"
OTHER_DEV = "soul-0123456789ab"
TZ = ZoneInfo("Europe/Bucharest")
NOW = dt.datetime(2026, 10, 2, 14, 30, tzinfo=TZ)  # a Friday afternoon
PAIR_CODE = "7KQ3M9XD"
REDIRECT = "http://127.0.0.1:33418/callback"


class FakeClock:
    """Epoch seconds for the auth/OAuth stores and an aware datetime for SoulService, moved together.

    The epoch starts at the real time (the SDK's token handlers compare expiry with `time.time()`);
    the wall clock SoulService sees starts at the fixed NOW, so item times stay deterministic.
    """

    def __init__(self, start: dt.datetime = NOW):
        self.t0 = self.t = time.time()
        self.start = start

    def __call__(self) -> float:
        return self.t

    def now(self) -> dt.datetime:
        return self.start + dt.timedelta(seconds=self.t - self.t0)

    def advance(self, seconds: float) -> None:
        self.t += seconds


def make_service(tmp_path, clock: FakeClock) -> SoulService:
    settings = Settings(data_dir=str(tmp_path), timezone="Europe/Bucharest")
    return SoulService(settings=settings, state=StateStore(":memory:"), master_secret=b"k" * 32, clock=clock.now)


class StubGateway:
    """In-memory stand-in for `suflet_ai.gateway.Gateway` (same method names and shapes)."""

    def __init__(self, delivery: str = "shown", forecast: str = "unknown"):
        self.devices: Dict[str, dict] = {}
        self.pushes: List[dict] = []
        self.delivery = delivery
        self.forecast_answer = forecast
        self.claims: Dict[str, dict] = {}
        self.inbox_rows: Dict[str, List[dict]] = {}
        self.item_states: Dict[tuple, str] = {}

    def add_device(self, device_id: str, account_id: Optional[str], **kw) -> dict:
        d = {"device_id": device_id, "account_id": account_id, "name": kw.pop("name", "SOUL"), "online": True,
             "last_seen": "2026-10-02T14:29", "connectors_paused": False, "revoked": False, "tz": "Europe/Bucharest",
             "lang": "ro", **kw}
        self.devices[device_id] = d
        return d

    # the interface the connector uses ------------------------------------
    def device_info(self, device_id: str) -> Optional[dict]:
        d = self.devices.get(device_id)
        return dict(d) if d else None

    def devices_of(self, account_id: str) -> List[dict]:
        return [dict(d) for d in self.devices.values() if d["account_id"] == account_id]

    def push(self, device_id, action, args, item_id, origin, say=None, private=False, needs_accept=False):
        if not self.devices.get(device_id, {}).get("account_id"):
            raise ValueError("device is not paired")
        self.pushes.append({"seq": len(self.pushes) + 1, "device_id": device_id, "action": action, "args": args,
                            "item_id": item_id, "origin": origin, "say": say, "private": private,
                            "needs_accept": needs_accept})
        return len(self.pushes)

    async def push_and_wait(self, device_id: str, seq: int, timeout: float = 3.0) -> str:
        return self.delivery

    def forecast(self, device_id: str, due_local: str) -> str:
        return self.forecast_answer

    def is_online(self, device_id: str) -> bool:
        return self.delivery == "shown"

    def claim(self, account_id, first_name, email, code, ip):
        if re.sub(r"[\s-]", "", str(code)).upper() != PAIR_CODE:
            from suflet_ai.devices import GatewayError
            raise GatewayError(404, "not_found", "no SOUL shows this code")
        pid = f"p_{len(self.claims) + 1}"
        self.claims[pid] = {"account_id": account_id, "state": "awaiting_device", "first_name": first_name}
        return {"pid": pid, "device": {"id": DEV, "name": "SOUL"}, "state": "awaiting_device", "expires_in": 120}

    def claim_state(self, pid: str, account_id: str) -> dict:
        c = self.claims.get(pid)
        if not c or c["account_id"] != account_id:
            from suflet_ai.devices import GatewayError
            raise GatewayError(404, "not_found", "unknown pairing request")
        return {"state": c["state"]}

    def device_taps_ok(self, pid: str) -> None:
        """What SOUL does when its owner taps the check mark on the pair-confirm screen."""
        c = self.claims[pid]
        c["state"] = "paired"
        self.add_device(DEV, c["account_id"])

    def inbox(self, device_id: str, state: Optional[str] = "pending") -> List[dict]:
        return [dict(r) for r in self.inbox_rows.get(device_id, []) if state is None or r["state"] == state]

    def inbox_answered(self, device_id: str, item_id: str) -> bool:
        for r in self.inbox_rows.get(device_id, []):
            if r["item_id"] == item_id:
                r["state"] = "answered"
                return True
        return False

    def item_state(self, device_id: str, item_id: str) -> Optional[str]:
        return self.item_states.get((device_id, item_id))


# ------------------------------------------------------------------------ browser --

def asgi_client(app) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=BASE)


def hidden(page: str, name: str) -> str:
    m = re.search(rf'name="{re.escape(name)}" value="([^"]*)"', page)
    assert m, f"no hidden field {name}"
    return html.unescape(m.group(1))


class Browser:
    """The user's phone browser: follows the authorize redirect, signs in by email code, pairs, consents."""

    def __init__(self, app, mailbox: DevMailbox, email: str = "ana.pop@example.com", first_name: str = "Ana"):
        self.http = asgi_client(app)
        self.mailbox = mailbox
        self.email = email
        self.first_name = first_name
        self.last_consent_page = ""

    async def aclose(self) -> None:
        await self.http.aclose()

    async def sign_in(self, next_url: str) -> httpx2.Response:
        r = await self.http.get(next_url if next_url.startswith("/login") else "/login")
        assert r.status_code == 200, r.text
        csrf = hidden(r.text, "csrf")
        nxt = hidden(r.text, "next")
        r = await self.http.post("/login", data={"csrf": csrf, "next": nxt, "email": self.email, "lang": "en",
                                                 "first_name": self.first_name})
        assert r.status_code == 200 and "one-time-code" in r.text, r.text
        code = self.mailbox.last_code(self.email)
        assert code
        return await self.http.post("/login/verify", data={"csrf": csrf, "next": nxt, "email": self.email,
                                                           "code": code, "lang": "en",
                                                           "first_name": self.first_name})

    async def open_consent(self, authorize_url: str) -> str:
        """GET /authorize, sign in if asked, land on the consent page; returns its HTML."""
        u = urlparse(authorize_url)
        r = await self.http.get(u.path + "?" + u.query)
        assert r.status_code == 302, r.text
        loc = r.headers["location"]
        assert loc.startswith(BASE + "/consent?req=")
        consent_path = loc[len(BASE):]
        r = await self.http.get(consent_path)
        if r.status_code == 303 and r.headers["location"].startswith("/login"):
            r2 = await self.sign_in(r.headers["location"])
            assert r2.status_code == 303 and r2.headers["location"] == consent_path, r2.text
            r = await self.http.get(consent_path)
        assert r.status_code == 200, r.text
        self.last_consent_page = r.text
        return r.text

    async def pair_on_consent(self, page: str, code: str) -> httpx2.Response:
        return await self.http.post("/consent/pair", data={"csrf": hidden(page, "csrf"), "req": hidden(page, "req"),
                                                           "code": code})

    async def allow(self, page: str, device_id: str, scopes: List[str], ack: bool = True) -> httpx2.Response:
        # like a real form: the hidden scope inputs (soul.read, offline_access when asked) plus the ticked boxes
        fixed = re.findall(r'<input type="hidden" name="scope" value="([^"]+)">', page)
        data = {"csrf": hidden(page, "csrf"), "req": hidden(page, "req"), "device_id": device_id,
                "scope": list(dict.fromkeys(fixed + list(scopes))), "decision": "allow"}
        if ack:
            data["ack"] = "1"
        return await self.http.post("/consent", data=data)


def callback_params(location: str) -> Dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}
