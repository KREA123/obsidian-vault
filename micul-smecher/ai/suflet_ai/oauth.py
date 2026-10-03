"""OAuth 2.1 authorization server for the SOUL connector (07-CONNECT-AI §3.7).

Built on the `mcp` 2.2.0 SDK: the SDK serves /authorize, /token, /register, /revoke, the RFC 8414
and RFC 9728 metadata and the bearer middleware; this module is the provider behind them
(`SoulOAuthProvider`), plus what the SDK does not do:

- `SoulClient.validate_redirect_uri`: https = exact string match; loopback (127.0.0.1, [::1],
  localhost over http) ignores the port only (RFC 8252 §7.3); never a fragment.
- DCR rules (`check_registration`): no http on non-loopback hosts, no custom schemes, fragments,
  userinfo or wildcards, at most 5 URIs, no client_name with Claude / Anthropic / ChatGPT / OpenAI /
  SOUL unless every redirect host is allowlisted; 20 registrations per hour per IP; clients with no
  grant after 24 h are purged.
- CIMD (an https `client_id`): fetched through an injected `cimd_fetch` (cimd.py, SSRF-safe). When no
  fetcher is configured CIMD is off and the metadata does not claim it.
- Consent request store: `authorize()` keeps the request server-side and redirects to
  `/consent?req=<opaque id>`; the consent page (mcp_remote.py) completes it with the account, the
  device and the scopes the user granted. The redirect back carries `iss` (RFC 9207).
- Codes: 160-bit random, 5 min, single use (a replayed code revokes the grant it produced), bound to
  client, redirect URI, PKCE S256 challenge, resource, account, device and scopes.
- Tokens: access `sat_` (1 h), refresh `srt_` (sliding 90 days, rotated on every use, only with
  `offline_access`), stored as SHA-256. Grace window: the immediately previous refresh token replayed
  within 60 s returns the same pair (kept encrypted under a key derived from that previous token, so
  the database alone cannot decrypt it); any other replay revokes the whole family and marks the
  grant `needs_reconnect`.
- Access tokens carry `subject = account_id`, `claims = {"device_id", "grant_id", "client_app"}`,
  `resource` = the MCP URL (the SDK checks it with `validate_token_resource=True`).
"""
from __future__ import annotations

import base64
import contextvars
import json
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence
from urllib.parse import urlencode, urlparse

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import AnyUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.routes import build_metadata
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import InvalidRedirectUriError, OAuthClientInformationFull, OAuthToken

from .accounts import Database, SlidingWindow, sha256_hex
from .accounts import RateLimited as _RateLimited

log = logging.getLogger("soul.oauth")

# ------------------------------------------------------------------------- constants --

SCOPES = ["soul.read", "soul.write", "soul.notes.read", "offline_access"]
RESOURCE_SCOPES = ["soul.read", "soul.write", "soul.notes.read"]
ACCESS_TTL_S = 3600
REFRESH_TTL_S = 90 * 86400
CODE_TTL_S = 5 * 60
REQUEST_TTL_S = 10 * 60
GRACE_S = 60
UNUSED_CLIENT_TTL_S = 24 * 3600
REGISTER_PER_IP_HOUR = 20
MAX_REDIRECT_URIS = 5

LOOPBACK_HOSTS = {"127.0.0.1", "[::1]", "::1", "localhost"}
# Redirect hosts shown with a "verified" badge on the consent page [V: §3.7].
VERIFIED_HOSTS = {"claude.ai": "Claude", "chatgpt.com": "ChatGPT"}
# CIMD client ids shown as verified [V: §3.7]. Claude's hosted-app CIMD id is unknown [U].
VERIFIED_CIMD = {
    "https://chatgpt.com/oauth/client.json": "ChatGPT",
    "https://claude.ai/oauth/claude-code-client-metadata": "Claude Code",
}
RESERVED_NAMES = ("claude", "anthropic", "chatgpt", "openai", "soul")

# Set by mcp_remote.RequestContextMiddleware for the duration of one HTTP request; the SDK handlers
# do not pass the request to the provider.
REQUEST_IP: contextvars.ContextVar[str] = contextvars.ContextVar("soul_request_ip", default="")
REQUEST_UI_LOCALES: contextvars.ContextVar[str] = contextvars.ContextVar("soul_ui_locales", default="")


def auth_settings(issuer_url: str, resource_url: str) -> AuthSettings:
    """The exact AuthSettings of §3.7 (scopes live in ClientRegistrationOptions)."""
    return AuthSettings(
        issuer_url=issuer_url,
        resource_server_url=resource_url,
        required_scopes=["soul.read"],
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=list(SCOPES),
            default_scopes=list(SCOPES),
        ),
        revocation_options=RevocationOptions(enabled=True),
        validate_token_resource=True,
    )


def as_metadata(settings: AuthSettings, cimd_supported: bool) -> dict:
    """RFC 8414 metadata: the SDK's document plus the §3.7 override."""
    md = build_metadata(settings.issuer_url, settings.service_documentation_url,
                        settings.client_registration_options or ClientRegistrationOptions(),
                        settings.revocation_options or RevocationOptions())
    md.token_endpoint_auth_methods_supported = ["none", "client_secret_post", "client_secret_basic"]
    md.revocation_endpoint_auth_methods_supported = ["none", "client_secret_post", "client_secret_basic"]
    md.authorization_response_iss_parameter_supported = True
    md.client_id_metadata_document_supported = True if cimd_supported else None
    return md.model_dump(mode="json", exclude_none=True)


def issuer_string(settings: AuthSettings) -> str:
    """The issuer exactly as the metadata renders it (clients compare `iss` as a plain string)."""
    return str(settings.issuer_url)


# ------------------------------------------------------------------- redirect URIs --

def _is_loopback(host: Optional[str]) -> bool:
    return (host or "").lower() in LOOPBACK_HOSTS


def check_redirect_uri(uri: str) -> Optional[str]:
    """Why a redirect URI is not acceptable for registration, or None if it is."""
    if not isinstance(uri, str) or len(uri) > 2000:
        return "invalid redirect URI"
    if "*" in uri:
        return "wildcards are not allowed"
    p = urlparse(uri)
    if p.fragment or "#" in uri:
        return "fragments are not allowed"
    if p.username or p.password or "@" in (p.netloc or ""):
        return "userinfo is not allowed"
    if p.scheme == "https":
        if not p.hostname:
            return "missing host"
        return None
    if p.scheme == "http":
        return None if _is_loopback(p.hostname) else "http is only allowed for loopback addresses"
    return "custom schemes are not allowed"


def redirect_host(uri: str) -> str:
    return (urlparse(str(uri)).hostname or "").lower()


def client_app_for_host(host: str) -> str:
    """'claude' | 'chatgpt' | 'other' (drives the source badge and the 'From Claude:' prefix)."""
    host = (host or "").lower()
    if host == "claude.ai" or host.endswith(".claude.ai") or host.endswith(".anthropic.com"):
        return "claude"
    if host in ("chatgpt.com", "chat.openai.com") or host.endswith(".chatgpt.com"):
        return "chatgpt"
    return "other"


class SoulClient(OAuthClientInformationFull):
    """A registered (DCR) or fetched (CIMD) client, with the §3.7 redirect rule."""

    def validate_redirect_uri(self, redirect_uri: Optional[AnyUrl]) -> AnyUrl:
        registered = [str(u) for u in (self.redirect_uris or [])]
        if redirect_uri is None:
            if len(registered) == 1:
                return AnyUrl(registered[0])
            raise InvalidRedirectUriError("redirect_uri must be specified unless the client has exactly one")
        given = str(redirect_uri)
        g = urlparse(given)
        if g.fragment or "#" in given:
            raise InvalidRedirectUriError("redirect_uri must not contain a fragment")
        if g.scheme == "https":
            if given in registered:
                return redirect_uri
        elif g.scheme == "http" and _is_loopback(g.hostname):
            for r in registered:
                p = urlparse(r)
                if (p.scheme == "http" and (p.hostname or "").lower() == (g.hostname or "").lower()
                        and p.path == g.path and p.query == g.query and not p.fragment):
                    return redirect_uri
        raise InvalidRedirectUriError("redirect_uri is not registered for this client")


def check_registration(info: OAuthClientInformationFull) -> None:
    """DCR rules of §3.7. Raises RegistrationError."""
    uris = [str(u) for u in (info.redirect_uris or [])]
    if not uris:
        raise RegistrationError("invalid_redirect_uri", "at least one redirect URI is required")
    if len(uris) > MAX_REDIRECT_URIS:
        raise RegistrationError("invalid_redirect_uri", f"at most {MAX_REDIRECT_URIS} redirect URIs")
    for u in uris:
        why = check_redirect_uri(u)
        if why:
            raise RegistrationError("invalid_redirect_uri", why)
    name = (info.client_name or "").lower()
    if any(w in name for w in RESERVED_NAMES):
        if not all(redirect_host(u) in VERIFIED_HOSTS for u in uris):
            raise RegistrationError("invalid_client_metadata",
                                    "client_name uses a reserved name for a redirect host we cannot verify")


# ------------------------------------------------------------------------ the store --

_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id  TEXT PRIMARY KEY,
    metadata   TEXT NOT NULL,
    kind       TEXT NOT NULL,                  -- 'dcr' | 'cimd'
    host       TEXT NOT NULL,
    verified   INTEGER NOT NULL DEFAULT 0,
    created    INTEGER NOT NULL,
    last_grant INTEGER
);
CREATE TABLE IF NOT EXISTS oauth_requests (
    req_id      TEXT PRIMARY KEY,
    client_id   TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    redirect_explicit INTEGER NOT NULL,
    challenge   TEXT NOT NULL,
    state       TEXT,
    resource    TEXT NOT NULL,
    scopes      TEXT NOT NULL,
    ui_locales  TEXT NOT NULL DEFAULT '',
    expires     INTEGER NOT NULL,
    done        INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS oauth_codes (
    hash        TEXT PRIMARY KEY,
    client_id   TEXT NOT NULL,
    account_id  TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    client_app  TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    redirect_explicit INTEGER NOT NULL,
    challenge   TEXT NOT NULL,
    resource    TEXT NOT NULL,
    scopes      TEXT NOT NULL,
    expires     INTEGER NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    grant_id    TEXT
);
CREATE TABLE IF NOT EXISTS oauth_grants (
    grant_id   TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    device_id  TEXT NOT NULL,
    client_id  TEXT NOT NULL,
    client_host TEXT NOT NULL,
    client_app TEXT NOT NULL,
    verified   INTEGER NOT NULL DEFAULT 0,
    scopes     TEXT NOT NULL,
    state      TEXT NOT NULL,                  -- 'connected' | 'needs_reconnect' | 'revoked'
    created    INTEGER NOT NULL,
    last_used  INTEGER
);
CREATE INDEX IF NOT EXISTS oauth_grants_acc ON oauth_grants(account_id);
CREATE TABLE IF NOT EXISTS oauth_tokens (
    hash       TEXT PRIMARY KEY,
    grant_id   TEXT NOT NULL,
    kind       TEXT NOT NULL,                  -- 'access' | 'refresh'
    client_id  TEXT NOT NULL,
    scopes     TEXT NOT NULL,
    resource   TEXT NOT NULL,
    prev_hash  TEXT,
    expires    INTEGER NOT NULL,
    rotated_at INTEGER,
    next_pair  BLOB,                           -- encrypted under a key derived from this refresh token
    revoked    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS oauth_tokens_grant ON oauth_tokens(grant_id);
CREATE INDEX IF NOT EXISTS oauth_tokens_prev ON oauth_tokens(prev_hash);
"""


class SoulAuthCode(AuthorizationCode):
    account_id: str
    device_id: str
    client_app: str


class SoulRefreshToken(RefreshToken):
    grant_id: str
    replay: bool = False  # the immediately previous token, inside the grace window


@dataclass
class ConsentRequest:
    req_id: str
    client: SoulClient
    kind: str                  # 'dcr' | 'cimd'
    redirect_uri: str
    state: Optional[str]
    scopes: List[str]
    resource: str
    ui_locales: str
    host: str                  # what the consent page names: CIMD host, else the redirect host
    verified: bool
    verified_name: str = ""
    loopback: bool = False

    @property
    def client_app(self) -> str:
        return client_app_for_host(self.host) if self.verified else "other"


@dataclass
class Grant:
    grant_id: str
    account_id: str
    device_id: str
    client_id: str
    client_host: str
    client_app: str
    verified: bool
    scopes: List[str]
    state: str
    created: int
    last_used: Optional[int]

    def public(self) -> dict:
        """What GET /v1/me/grants returns (§3.5)."""
        return {"id": self.grant_id, "client_host": self.client_host, "verified": self.verified,
                "scopes": self.scopes, "device_id": self.device_id, "created": self.created,
                "last_used": self.last_used, "state": self.state}


def _fernet_for(token: str) -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"soul-refresh-grace-v1").derive(token.encode())
    return Fernet(base64.urlsafe_b64encode(key))


class SoulOAuthProvider:
    """Implements the SDK 2.2.0 `OAuthAuthorizationServerProvider` protocol."""

    def __init__(self, db: Database, issuer_url: str, resource_url: str,
                 consent_path: str = "/consent",
                 cimd_fetch: Optional[Callable[[str], dict]] = None,
                 clock: Callable[[], float] = time.time):
        self.db = db
        self.db.script(_SCHEMA)
        self.settings = auth_settings(issuer_url, resource_url)
        self.issuer = issuer_string(self.settings)
        self.resource = str(self.settings.resource_server_url)
        self.consent_url = self.issuer.rstrip("/") + consent_path
        self.cimd_fetch = cimd_fetch
        self.clock = clock
        self.limits = SlidingWindow(clock)
        self._cimd_cache: Dict[str, tuple] = {}

    def now(self) -> int:
        return int(self.clock())

    # ----------------------------------------------------------------- clients --
    async def get_client(self, client_id: str) -> Optional[SoulClient]:
        if not client_id or len(client_id) > 512:
            return None
        if client_id.startswith("https://"):
            return self._cimd_client(client_id)
        row = self.db.one("SELECT metadata FROM oauth_clients WHERE client_id=? AND kind='dcr'", (client_id,))
        return SoulClient.model_validate_json(row["metadata"]) if row else None

    def _cimd_client(self, client_id: str) -> Optional[SoulClient]:
        if self.cimd_fetch is None:
            return None
        hit = self._cimd_cache.get(client_id)
        if hit and hit[0] > self.now():
            return hit[1]
        try:
            doc = self.cimd_fetch(client_id)
        except Exception as e:  # CimdRejected or a network error: unknown client
            log.warning("CIMD client rejected (%s)", type(e).__name__)
            return None
        if not isinstance(doc, dict) or doc.get("client_id") != client_id:
            return None
        doc = {k: v for k, v in doc.items() if k != "client_secret"}
        doc.setdefault("token_endpoint_auth_method", "none")
        if doc["token_endpoint_auth_method"] != "none":
            return None  # CIMD clients are public: no secret is ever exchanged
        doc["scope"] = " ".join(SCOPES)  # CIMD clients are given all valid scopes; consent decides
        try:
            client = SoulClient.model_validate(doc)
            check_registration(client)
        except (ValueError, RegistrationError):
            return None
        self._cimd_cache[client_id] = (self.now() + 300, client)
        self._remember_client(client, "cimd", urlparse(client_id).hostname or "")
        return client

    def _remember_client(self, client: OAuthClientInformationFull, kind: str, host: str) -> None:
        verified = (kind == "cimd" and client.client_id in VERIFIED_CIMD) or (
            kind == "dcr" and all(redirect_host(str(u)) in VERIFIED_HOSTS for u in client.redirect_uris or []))
        self.db.exec("INSERT INTO oauth_clients(client_id, metadata, kind, host, verified, created) "
                     "VALUES (?,?,?,?,?,?) ON CONFLICT(client_id) DO UPDATE SET metadata=excluded.metadata",
                     (client.client_id, client.model_dump_json(exclude_none=True), kind, host.lower(),
                      1 if verified else 0, self.now()))

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        try:
            self.limits.hit(f"register:{REQUEST_IP.get()}", REGISTER_PER_IP_HOUR, 3600)
        except _RateLimited:
            raise RegistrationError("invalid_client_metadata", "too many registrations from this address")
        check_registration(client_info)
        uris = [str(u) for u in client_info.redirect_uris or []]
        self._remember_client(client_info, "dcr", redirect_host(uris[0]))
        log.info("client registered (%s)", redirect_host(uris[0]))

    def purge_unused_clients(self) -> int:
        """Delete DCR clients that never got a grant within 24 h (run periodically)."""
        cur = self.db.exec("DELETE FROM oauth_clients WHERE kind='dcr' AND last_grant IS NULL AND created < ?",
                           (self.now() - UNUSED_CLIENT_TTL_S,))
        return cur.rowcount

    # --------------------------------------------------------------- authorize --
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        resource = params.resource or self.resource
        if resource.rstrip("/") != self.resource.rstrip("/"):
            raise AuthorizeError("invalid_target", "unknown resource")
        scopes = params.scopes if params.scopes is not None else (client.scope or "").split()
        scopes = [s for s in dict.fromkeys(scopes) if s in SCOPES]
        if "soul.read" not in scopes:
            scopes.insert(0, "soul.read")  # mandatory (§3.7); the consent page shows it
        req_id = "rq_" + secrets.token_urlsafe(24)
        self.db.exec(
            "INSERT INTO oauth_requests(req_id, client_id, redirect_uri, redirect_explicit, challenge, state, "
            "resource, scopes, ui_locales, expires) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (req_id, client.client_id, str(params.redirect_uri), 1 if params.redirect_uri_provided_explicitly else 0,
             params.code_challenge, params.state, self.resource, " ".join(scopes),
             REQUEST_UI_LOCALES.get()[:32], self.now() + REQUEST_TTL_S))
        return f"{self.consent_url}?{urlencode({'req': req_id})}"

    async def consent_request(self, req_id: str) -> Optional[ConsentRequest]:
        row = self.db.one("SELECT * FROM oauth_requests WHERE req_id=?", (req_id or "",))
        if row is None or row["done"] or row["expires"] < self.now():
            return None
        return await self.consent_request_from_row(row)

    def _redirect(self, req_row, **params: Optional[str]) -> str:
        return construct_redirect_uri(req_row["redirect_uri"], state=req_row["state"], iss=self.issuer, **params)

    async def approve(self, req_id: str, account_id: str, device_id: str, granted: Sequence[str]) -> str:
        """Consent given: mint a code and return the redirect URL back to the client (with `iss`)."""
        with self.db.lock:
            row = self.db.one("SELECT * FROM oauth_requests WHERE req_id=? AND done=0 AND expires>=?",
                              (req_id, self.now()))
            if row is None:
                raise AuthorizeError("invalid_request", "the authorization request expired")
            self.db.exec("UPDATE oauth_requests SET done=1 WHERE req_id=?", (req_id,))
        req = await self.consent_request_from_row(row)
        if req is None:
            raise AuthorizeError("unauthorized_client", "the client is no longer registered")
        allowed = set(row["scopes"].split())
        scopes = [s for s in SCOPES if s in allowed and s in set(granted)]
        if "soul.read" not in scopes:
            scopes.insert(0, "soul.read")
        code = secrets.token_urlsafe(20)  # 160 bits
        self.db.exec(
            "INSERT INTO oauth_codes(hash, client_id, account_id, device_id, client_app, redirect_uri, "
            "redirect_explicit, challenge, resource, scopes, expires) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (sha256_hex(code), row["client_id"], account_id, device_id, req.client_app, row["redirect_uri"],
             row["redirect_explicit"], row["challenge"], row["resource"], " ".join(scopes),
             self.now() + CODE_TTL_S))
        return self._redirect(row, code=code)

    async def consent_request_from_row(self, row) -> Optional[ConsentRequest]:
        client = await self.get_client(row["client_id"])
        if client is None:
            return None
        if client.client_id.startswith("https://"):
            kind, host = "cimd", (urlparse(client.client_id).hostname or "").lower()
            vname = VERIFIED_CIMD.get(client.client_id, "")
        else:
            kind, host = "dcr", redirect_host(row["redirect_uri"])
            vname = VERIFIED_HOSTS.get(host, "")
        return ConsentRequest(req_id=row["req_id"], client=client, kind=kind, redirect_uri=row["redirect_uri"],
                              state=row["state"], scopes=row["scopes"].split(), resource=row["resource"],
                              ui_locales=row["ui_locales"], host=host, verified=bool(vname), verified_name=vname,
                              loopback=_is_loopback(host))

    async def deny(self, req_id: str) -> Optional[str]:
        with self.db.lock:
            row = self.db.one("SELECT * FROM oauth_requests WHERE req_id=? AND done=0", (req_id,))
            if row is None:
                return None
            self.db.exec("UPDATE oauth_requests SET done=1 WHERE req_id=?", (req_id,))
        return self._redirect(row, error="access_denied", error_description="the user did not allow access")

    # -------------------------------------------------------------------- codes --
    async def load_authorization_code(self, client: OAuthClientInformationFull,
                                      authorization_code: str) -> Optional[SoulAuthCode]:
        row = self.db.one("SELECT * FROM oauth_codes WHERE hash=?", (sha256_hex(authorization_code or ""),))
        if row is None or row["client_id"] != client.client_id:
            return None
        if row["used"]:
            # RFC 6749 §4.1.2: a replayed code revokes what it produced
            if row["grant_id"]:
                self.revoke_grant(row["grant_id"], state="revoked")
            return None
        return SoulAuthCode(
            code=authorization_code, scopes=row["scopes"].split(), expires_at=float(row["expires"]),
            client_id=row["client_id"], code_challenge=row["challenge"], redirect_uri=AnyUrl(row["redirect_uri"]),
            redirect_uri_provided_explicitly=bool(row["redirect_explicit"]), resource=row["resource"],
            subject=row["account_id"], account_id=row["account_id"], device_id=row["device_id"],
            client_app=row["client_app"])

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: SoulAuthCode) -> OAuthToken:
        h = sha256_hex(authorization_code.code)
        grant_id = "g_" + secrets.token_urlsafe(12)
        with self.db.lock:
            cur = self.db.exec("UPDATE oauth_codes SET used=1, grant_id=? WHERE hash=? AND used=0", (grant_id, h))
            if cur.rowcount != 1:
                raise TokenError("invalid_grant", "authorization code already used")
            crow = self.db.one("SELECT verified, host FROM oauth_clients WHERE client_id=?", (client.client_id,))
            host = crow["host"] if crow else ""
            self.db.exec(
                "INSERT INTO oauth_grants(grant_id, account_id, device_id, client_id, client_host, client_app, "
                "verified, scopes, state, created) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (grant_id, authorization_code.account_id, authorization_code.device_id, client.client_id,
                 host, authorization_code.client_app, crow["verified"] if crow else 0,
                 " ".join(authorization_code.scopes), "connected", self.now()))
            self.db.exec("UPDATE oauth_clients SET last_grant=? WHERE client_id=?", (self.now(), client.client_id))
        log.info("grant created (%s, %s)", host, grant_id[:6])
        return self._issue(grant_id, client.client_id, authorization_code.scopes,
                           authorization_code.resource or self.resource, prev_hash=None)

    # ------------------------------------------------------------------- tokens --
    def _issue(self, grant_id: str, client_id: str, scopes: List[str], resource: str,
               prev_hash: Optional[str], refresh_scopes: Optional[List[str]] = None) -> OAuthToken:
        now = self.now()
        access = "sat_" + secrets.token_urlsafe(32)
        self.db.exec("INSERT INTO oauth_tokens(hash, grant_id, kind, client_id, scopes, resource, expires) "
                     "VALUES (?,?,?,?,?,?,?)",
                     (sha256_hex(access), grant_id, "access", client_id, " ".join(scopes), resource, now + ACCESS_TTL_S))
        refresh = None
        rscopes = refresh_scopes or scopes
        if "offline_access" in rscopes:
            refresh = "srt_" + secrets.token_urlsafe(32)
            self.db.exec("INSERT INTO oauth_tokens(hash, grant_id, kind, client_id, scopes, resource, prev_hash, "
                         "expires) VALUES (?,?,?,?,?,?,?,?)",
                         (sha256_hex(refresh), grant_id, "refresh", client_id, " ".join(rscopes), resource,
                          prev_hash, now + REFRESH_TTL_S))
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=ACCESS_TTL_S,
                          scope=" ".join(scopes), refresh_token=refresh)

    def _grant_state(self, grant_id: str) -> Optional[str]:
        row = self.db.one("SELECT state FROM oauth_grants WHERE grant_id=?", (grant_id,))
        return row["state"] if row else None

    async def load_refresh_token(self, client: OAuthClientInformationFull,
                                 refresh_token: str) -> Optional[SoulRefreshToken]:
        h = sha256_hex(refresh_token or "")
        with self.db.lock:
            row = self.db.one("SELECT * FROM oauth_tokens WHERE hash=? AND kind='refresh'", (h,))
            if row is None or row["client_id"] != client.client_id or row["revoked"]:
                return None
            if self._grant_state(row["grant_id"]) != "connected":
                return None
            replay = False
            if row["rotated_at"] is not None:
                nxt = self.db.one("SELECT rotated_at, revoked FROM oauth_tokens WHERE prev_hash=? AND kind='refresh'",
                                  (h,))
                in_grace = (self.now() - row["rotated_at"] <= GRACE_S and nxt is not None
                            and nxt["rotated_at"] is None and not nxt["revoked"] and row["next_pair"])
                if not in_grace:
                    log.warning("refresh token replay: revoking grant %s", row["grant_id"][:6])
                    self.revoke_grant(row["grant_id"], state="needs_reconnect")
                    return None
                replay = True
        return SoulRefreshToken(token=refresh_token, client_id=row["client_id"], scopes=row["scopes"].split(),
                                expires_at=row["expires"], resource=row["resource"], grant_id=row["grant_id"],
                                replay=replay)

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: SoulRefreshToken,
                                     scopes: List[str]) -> OAuthToken:
        h = sha256_hex(refresh_token.token)
        if refresh_token.replay:
            return self._replay_pair(h, refresh_token.token)
        with self.db.lock:
            cur = self.db.exec("UPDATE oauth_tokens SET rotated_at=? WHERE hash=? AND rotated_at IS NULL AND revoked=0",
                               (self.now(), h))
            if cur.rowcount != 1:  # lost a race with a parallel refresh of the same token
                return self._replay_pair(h, refresh_token.token)
            grow = self.db.one("SELECT scopes FROM oauth_grants WHERE grant_id=?", (refresh_token.grant_id,))
            grant_scopes = grow["scopes"].split() if grow else refresh_token.scopes
            access_scopes = [s for s in scopes if s in grant_scopes] or grant_scopes
            tok = self._issue(refresh_token.grant_id, client.client_id, access_scopes,
                              refresh_token.resource or self.resource, prev_hash=h, refresh_scopes=grant_scopes)
            pair = json.dumps(tok.model_dump(exclude_none=True)).encode()
            self.db.exec("UPDATE oauth_tokens SET next_pair=? WHERE hash=?",
                         (_fernet_for(refresh_token.token).encrypt(pair), h))
            self.db.exec("UPDATE oauth_grants SET last_used=? WHERE grant_id=?", (self.now(), refresh_token.grant_id))
        return tok

    def _replay_pair(self, h: str, raw: str) -> OAuthToken:
        row = self.db.one("SELECT next_pair FROM oauth_tokens WHERE hash=?", (h,))
        try:
            data = json.loads(_fernet_for(raw).decrypt(row["next_pair"]))
        except (TypeError, InvalidToken, ValueError):
            raise TokenError("invalid_grant", "refresh token is no longer valid")
        return OAuthToken.model_validate(data)

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        if not token or not token.startswith("sat_") or len(token) > 128:
            return None
        row = self.db.one("SELECT t.*, g.account_id, g.device_id, g.client_app, g.state AS gstate, g.last_used "
                          "FROM oauth_tokens t JOIN oauth_grants g ON g.grant_id=t.grant_id "
                          "WHERE t.hash=? AND t.kind='access'", (sha256_hex(token),))
        now = self.now()
        if row is None or row["revoked"] or row["expires"] < now or row["gstate"] != "connected":
            return None
        if not row["last_used"] or now - row["last_used"] > 60:
            self.db.exec("UPDATE oauth_grants SET last_used=? WHERE grant_id=?", (now, row["grant_id"]))
        return AccessToken(token=token, client_id=row["client_id"], scopes=row["scopes"].split(),
                           expires_at=row["expires"], resource=row["resource"], subject=row["account_id"],
                           claims={"iss": self.issuer, "device_id": row["device_id"], "grant_id": row["grant_id"],
                                   "client_app": row["client_app"]})

    async def revoke_token(self, token) -> None:
        grant_id = getattr(token, "grant_id", None)
        if grant_id is None:
            row = self.db.one("SELECT grant_id FROM oauth_tokens WHERE hash=?", (sha256_hex(token.token),))
            grant_id = row["grant_id"] if row else None
        if grant_id:
            self.revoke_grant(grant_id, state="revoked")

    # ------------------------------------------------------------------- grants --
    def revoke_grant(self, grant_id: str, state: str = "revoked") -> None:
        """Revoke the whole token family of a grant ('revoked', or 'needs_reconnect' after a replay)."""
        with self.db.lock:
            self.db.exec("UPDATE oauth_tokens SET revoked=1, next_pair=NULL WHERE grant_id=?", (grant_id,))
            self.db.exec("UPDATE oauth_grants SET state=? WHERE grant_id=? AND state!='revoked'", (state, grant_id))

    def revoke_device_grants(self, device_id: str) -> int:
        """On unpair / reset / transfer (pairing.py calls this)."""
        rows = self.db.all("SELECT grant_id FROM oauth_grants WHERE device_id=? AND state!='revoked'", (device_id,))
        for r in rows:
            self.revoke_grant(r["grant_id"], "revoked")
        return len(rows)

    def get_grant(self, grant_id: str) -> Optional[Grant]:
        row = self.db.one("SELECT * FROM oauth_grants WHERE grant_id=?", (grant_id,))
        return self._grant(row) if row else None

    def grants(self, account_id: str) -> List[Grant]:
        return [self._grant(r) for r in self.db.all(
            "SELECT * FROM oauth_grants WHERE account_id=? AND state!='revoked' ORDER BY created", (account_id,))]

    @staticmethod
    def _grant(row) -> Grant:
        return Grant(grant_id=row["grant_id"], account_id=row["account_id"], device_id=row["device_id"],
                     client_id=row["client_id"], client_host=row["client_host"], client_app=row["client_app"],
                     verified=bool(row["verified"]), scopes=row["scopes"].split(), state=row["state"],
                     created=row["created"], last_used=row["last_used"])

    def purge_expired(self) -> None:
        now = self.now()
        self.db.exec("DELETE FROM oauth_requests WHERE expires < ?", (now - 86400,))
        self.db.exec("DELETE FROM oauth_codes WHERE expires < ?", (now - 86400,))
        self.db.exec("DELETE FROM oauth_tokens WHERE expires < ? OR (revoked=1 AND kind='access')", (now,))
        self.db.exec("UPDATE oauth_tokens SET next_pair=NULL WHERE rotated_at IS NOT NULL AND rotated_at < ?",
                     (now - GRACE_S,))

