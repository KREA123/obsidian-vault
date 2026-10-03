"""Unit tests: OAuth provider rules (oauth.py) and accounts (accounts.py), 07-CONNECT-AI §3.1, §3.3, §3.7."""
from __future__ import annotations

import asyncio
import logging

import pytest
from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, RegistrationError
from mcp.shared.auth import InvalidRedirectUriError
from pydantic import AnyUrl
from starlette.requests import Request

from _connector_kit import BASE, MCP_URL, FakeClock
from suflet_ai.accounts import (CSRF_COOKIE, Accounts, AuthError, CsrfError, Database, DevMailbox, RateLimited,
                                ReauthRequired, account_hint, require_csrf)
from suflet_ai.oauth import (REQUEST_IP, SoulClient, SoulOAuthProvider, check_registration, check_redirect_uri,
                             client_app_for_host)


def client(uris, name="x", cid="c1", **kw) -> SoulClient:
    return SoulClient(client_id=cid, redirect_uris=uris, client_name=name, token_endpoint_auth_method="none", **kw)


# ----------------------------------------------------------------- redirect URIs --

def test_loopback_port_is_ignored_https_is_exact():
    c = client(["http://127.0.0.1:33418/callback", "https://claude.ai/api/mcp/auth_callback",
                "http://localhost/cb?x=1"])
    assert c.validate_redirect_uri(AnyUrl("http://127.0.0.1:50123/callback"))
    assert c.validate_redirect_uri(AnyUrl("http://localhost:9999/cb?x=1"))
    assert c.validate_redirect_uri(AnyUrl("https://claude.ai/api/mcp/auth_callback"))
    for bad in ("http://127.0.0.1:50123/other", "https://claude.ai/api/mcp/auth_callback/",
                "https://claude.ai:8443/api/mcp/auth_callback", "http://claude.ai/api/mcp/auth_callback",
                "http://localhost:1/cb?x=2", "http://[::1]:1/callback", "http://127.0.0.1:1/callback#f"):
        with pytest.raises(InvalidRedirectUriError):
            c.validate_redirect_uri(AnyUrl(bad))
    with pytest.raises(InvalidRedirectUriError):
        c.validate_redirect_uri(None)  # more than one registered: must be explicit
    assert str(client(["https://a.example/cb"]).validate_redirect_uri(None)) == "https://a.example/cb"


def test_registration_rules():
    for bad in (["myapp://cb"], ["http://example.com/cb"], ["https://example.com/cb#frag"],
                ["https://user:pw@example.com/cb"], ["https://*.example.com/cb"], [f"https://e{i}.com/" for i in range(6)],
                ["javascript:alert(1)"]):
        with pytest.raises(RegistrationError):
            check_registration(client(bad))
    for name in ("Claude", "my ChatGPT helper", "Official SOUL app", "anthropic tools", "OpenAI"):
        with pytest.raises(RegistrationError):
            check_registration(client(["https://evil.example/cb"], name=name))
    check_registration(client(["https://claude.ai/api/mcp/auth_callback"], name="Claude"))
    check_registration(client(["https://chatgpt.com/connector_platform_oauth_redirect"], name="ChatGPT"))
    check_registration(client(["http://127.0.0.1:1234/cb", "http://[::1]/cb"], name="cli"))
    assert check_redirect_uri("https://chatgpt.com/connector/oauth/abc123") is None
    assert client_app_for_host("claude.ai") == "claude" and client_app_for_host("chatgpt.com") == "chatgpt"
    assert client_app_for_host("claude.ai.evil.example") == "other"


# ---------------------------------------------------------------------- provider --

def provider(clock=None, **kw) -> SoulOAuthProvider:
    return SoulOAuthProvider(Database(), BASE, MCP_URL, clock=clock or FakeClock(), **kw)


def test_dcr_rate_limit_and_purge():
    clock = FakeClock()
    p = provider(clock)

    async def go():
        tok = REQUEST_IP.set("198.51.100.7")
        try:
            for i in range(20):
                await p.register_client(client(["https://tools.example/cb"], cid=f"c{i}"))
            with pytest.raises(RegistrationError):
                await p.register_client(client(["https://tools.example/cb"], cid="c20"))
        finally:
            REQUEST_IP.reset(tok)
        assert await p.get_client("c3") is not None
        clock.advance(24 * 3600 + 1)
        assert p.purge_unused_clients() == 20
        assert await p.get_client("c3") is None

    asyncio.run(go())


def test_cimd_clients():
    calls = []
    docs = {
        "https://chatgpt.com/oauth/client.json": {
            "client_id": "https://chatgpt.com/oauth/client.json", "client_name": "ChatGPT",
            "redirect_uris": ["https://chatgpt.com/connector_platform_oauth_redirect"]},
        "https://evil.example/client.json": {"client_id": "https://other.example/client.json",
                                             "redirect_uris": ["https://evil.example/cb"]},
        "https://secret.example/c.json": {"client_id": "https://secret.example/c.json",
                                          "redirect_uris": ["https://secret.example/cb"],
                                          "token_endpoint_auth_method": "client_secret_post"},
        "https://bad.example/c.json": {"client_id": "https://bad.example/c.json", "redirect_uris": ["myapp://cb"]},
    }

    def fetch(url):
        calls.append(url)
        if url not in docs:
            raise RuntimeError("CimdRejected")
        return dict(docs[url])

    clock = FakeClock()
    p = provider(clock, cimd_fetch=fetch)

    async def go():
        c = await p.get_client("https://chatgpt.com/oauth/client.json")
        assert c is not None and "offline_access" in c.scope
        assert await p.get_client("https://chatgpt.com/oauth/client.json") is c  # cached
        assert calls.count("https://chatgpt.com/oauth/client.json") == 1
        clock.advance(301)
        await p.get_client("https://chatgpt.com/oauth/client.json")
        assert calls.count("https://chatgpt.com/oauth/client.json") == 2
        for bad in ("https://evil.example/client.json", "https://secret.example/c.json", "https://bad.example/c.json",
                    "https://unreachable.example/c.json"):
            assert await p.get_client(bad) is None
        row = p.db.one("SELECT verified, kind, host FROM oauth_clients WHERE client_id=?",
                       ("https://chatgpt.com/oauth/client.json",))
        assert (row["verified"], row["kind"], row["host"]) == (1, "cimd", "chatgpt.com")
        # without a fetcher CIMD ids are unknown clients
        assert await provider().get_client("https://chatgpt.com/oauth/client.json") is None

    asyncio.run(go())


def test_authorize_keeps_request_server_side_and_checks_resource():
    p = provider()

    async def go():
        c = client(["https://claude.ai/api/mcp/auth_callback"], name="Claude", cid="cl")
        await p.register_client(c)
        params = AuthorizationParams(state="s", scopes=["soul.write", "bogus"], code_challenge="a" * 43,
                                     redirect_uri=AnyUrl("https://claude.ai/api/mcp/auth_callback"),
                                     redirect_uri_provided_explicitly=True, resource=MCP_URL)
        url = await p.authorize(c, params)
        assert url.startswith(BASE + "/consent?req=rq_") and "code_challenge" not in url and "state" not in url
        req = await p.consent_request(url.split("req=")[1])
        assert req.verified and req.verified_name == "Claude" and req.client_app == "claude"
        assert req.scopes == ["soul.read", "soul.write"]  # soul.read is mandatory; unknown scopes dropped
        with pytest.raises(AuthorizeError):
            await p.authorize(c, params.model_copy(update={"resource": "https://other.example/mcp"}))
        # approve: only what was asked AND ticked is granted
        back = await p.approve(req.req_id, "a_1", "soul-a1b2c3d4e5f6", ["soul.write", "soul.notes.read"])
        assert back.startswith("https://claude.ai/api/mcp/auth_callback?") and "iss=" in back and "state=s" in back
        code = back.split("code=")[1].split("&")[0]
        ac = await p.load_authorization_code(c, code)
        assert ac.scopes == ["soul.read", "soul.write"] and ac.device_id == "soul-a1b2c3d4e5f6"
        assert await p.load_authorization_code(client(["https://x.example/cb"], cid="other"), code) is None
        with pytest.raises(AuthorizeError):
            await p.approve(req.req_id, "a_1", "soul-a1b2c3d4e5f6", [])  # a request is used once
        tok = await p.exchange_authorization_code(c, ac)
        assert tok.refresh_token is None  # no offline_access asked: no refresh token
        at = await p.load_access_token(tok.access_token)
        assert at.subject == "a_1" and at.claims["device_id"] == "soul-a1b2c3d4e5f6" and at.resource == MCP_URL
        grant = p.grants("a_1")[0].public()
        assert grant["client_host"] == "claude.ai" and grant["verified"] and grant["state"] == "connected"
        await p.revoke_token(at)
        assert await p.load_access_token(tok.access_token) is None
        assert p.grants("a_1") == []

    asyncio.run(go())


def test_access_token_expires_after_an_hour():
    clock = FakeClock()
    p = provider(clock)

    async def go():
        c = client(["https://claude.ai/api/mcp/auth_callback"], cid="cl",
                   scope="soul.read soul.write soul.notes.read offline_access")  # what DCR stores by default
        await p.register_client(c)
        url = await p.authorize(c, AuthorizationParams(
            state=None, scopes=None, code_challenge="a" * 43, redirect_uri=AnyUrl(str(c.redirect_uris[0])),
            redirect_uri_provided_explicitly=True, resource=None))
        back = await p.approve(url.split("req=")[1], "a_1", "soul-a1b2c3d4e5f6", ["soul.read", "offline_access"])
        ac = await p.load_authorization_code(c, back.split("code=")[1].split("&")[0])
        tok = await p.exchange_authorization_code(c, ac)
        assert tok.refresh_token.startswith("srt_")
        assert await p.load_access_token(tok.access_token) is not None
        clock.advance(3601)
        assert await p.load_access_token(tok.access_token) is None
        rt = await p.load_refresh_token(c, tok.refresh_token)
        new = await p.exchange_refresh_token(c, rt, [])
        assert await p.load_access_token(new.access_token) is not None
        clock.advance(61)
        assert await p.load_refresh_token(c, tok.refresh_token) is None  # old one replayed late: family revoked
        assert await p.load_access_token(new.access_token) is None
        assert p.get_grant(rt.grant_id).state == "needs_reconnect"

    asyncio.run(go())


# ---------------------------------------------------------------------- accounts --

def accounts(clock=None):
    mb = DevMailbox()
    return Accounts(Database(), mailer=mb, clock=clock or FakeClock(), pepper=b"x" * 32), mb


def test_email_code_sign_in_and_notice(caplog):
    caplog.set_level(logging.DEBUG)
    a, mb = accounts()
    a.start_email_login("Ana.Pop@Example.com", "ro", "1.2.3.4")
    code = mb.last_code("ana.pop@example.com")
    assert mb.messages[-1][1] == f"Codul tău SOUL: {code}"
    s = a.verify_email_login("ana.pop@example.com", code[:3] + " " + code[3:], "1.2.3.4", first_name="Ana")
    assert s.token and s.account.new and s.account.first_name == "Ana" and s.account.hint == "a***@example.com"
    assert mb.messages[-1][1] == "Conectare nouă la SOUL"  # every sign-in is announced by email
    with pytest.raises(AuthError):
        a.verify_email_login("ana.pop@example.com", code, "1.2.3.4")  # single use
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert code not in logs and "ana.pop@example.com" not in logs and s.token not in logs
    assert a.session_from_token(s.token).account_id == s.account_id


def test_code_dies_after_five_wrong_tries_and_expires():
    clock = FakeClock()
    a, mb = accounts(clock)
    a.start_email_login("b@example.com", "en", "1.2.3.4")
    code = mb.last_code("b@example.com")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(AuthError):
            a.verify_email_login("b@example.com", wrong, "1.2.3.4")
    with pytest.raises(AuthError):
        a.verify_email_login("b@example.com", code, "1.2.3.4")  # dead even with the right code
    a.start_email_login("b@example.com", "en", "1.2.3.4")
    clock.advance(601)
    with pytest.raises(AuthError) as e:
        a.verify_email_login("b@example.com", mb.last_code("b@example.com"), "1.2.3.4")
    assert e.value.code == "code_expired"


def test_code_rate_limits_and_no_account_probing():
    a, mb = accounts()
    for _ in range(10):
        a.start_email_login("c@example.com", "en", "1.2.3.4")  # unknown email: same answer, no error
    with pytest.raises(RateLimited) as e:
        a.start_email_login("c@example.com", "en", "1.2.3.4")
    assert e.value.status == 429 and e.value.retry_ms > 0
    for i in range(19):
        a.start_email_login(f"d{i}@example.com", "en", "1.2.3.4")
    with pytest.raises(RateLimited):
        a.start_email_login("e@example.com", "en", "1.2.3.4")  # 30 per IP per hour
    with pytest.raises(AuthError):
        a.start_email_login("not an email", "en", "5.6.7.8")


def test_sessions_slide_and_reauth():
    clock = FakeClock()
    a, mb = accounts(clock)
    a.start_email_login("f@example.com", "en", "1.2.3.4")
    s = a.verify_email_login("f@example.com", mb.last_code("f@example.com"), "1.2.3.4")
    a.require_reauth(s)
    clock.advance(11 * 60)
    s2 = a.session_from_token(s.token)
    with pytest.raises(ReauthRequired):
        a.require_reauth(s2)
    a.start_email_login("f@example.com", "en", "1.2.3.4")
    a.verify_email_login("f@example.com", mb.last_code("f@example.com"), "1.2.3.4", session=s2)
    a.require_reauth(a.session_from_token(s.token))
    clock.advance(29 * 86400)
    assert a.session_from_token(s.token) is not None  # sliding
    clock.advance(31 * 86400)
    assert a.session_from_token(s.token) is None
    assert account_hint("x@y.com") == "x***@y.com"


def _req(cookie=None, header=None):
    headers = []
    if cookie:
        headers.append((b"cookie", f"{CSRF_COOKIE}={cookie}".encode()))
    if header:
        headers.append((b"x-csrf-token", header.encode()))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers, "query_string": b""})


def test_csrf_double_submit():
    require_csrf(_req("abc", "abc"), None)
    require_csrf(_req("abc"), "abc")
    for r, given in ((_req("abc", "abd"), None), (_req(None, "abc"), None), (_req("abc"), "")):
        with pytest.raises(CsrfError):
            require_csrf(r, given)


def test_production_refuses_dev_mailbox(monkeypatch):
    monkeypatch.setenv("SOUL_ENV", "production")
    with pytest.raises(RuntimeError):
        Accounts(Database())
