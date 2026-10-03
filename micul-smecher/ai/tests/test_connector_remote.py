"""SOUL connector as a remote MCP server (07-CONNECT-AI §3.7, §3.8, §5 Phase 0.11).

The whole OAuth dance runs with the official MCP client SDK (`OAuthClientProvider` + Streamable HTTP):
discovery from the 401, dynamic client registration, PKCE S256, sign-in by email code, pairing with
the code shown on SOUL, consent, `iss` on the redirect, token exchange, then MCP tool calls routed to
the paired device through the gateway. No network, no real keys.
"""
from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse

from mcp.client import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from _connector_kit import (BASE, DEV, HOST, MCP_URL, PAIR_CODE, REDIRECT, Browser, FakeClock, StubGateway,
                            asgi_client, callback_params, make_service)
from suflet_ai.accounts import DevMailbox
from suflet_ai.mcp_remote import create_remote_app

import httpx2


class MemoryStorage:
    def __init__(self):
        self.tokens = None
        self.client_info = None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self):
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info


def build(tmp_path, gateway=None, **kw):
    clock = FakeClock()
    mailbox = DevMailbox()
    svc = make_service(tmp_path, clock)
    gw = gateway or StubGateway()
    app = create_remote_app(svc, gw, public_host=HOST, db_path=":memory:", mailer=mailbox, clock=clock,
                            cimd_fetch=kw.pop("cimd_fetch", None), **kw)
    return app, gw, svc, mailbox, clock


async def oauth_session(app, browser: Browser, *, on_consent, scope: str = "soul.read soul.write soul.notes.read "
                        "offline_access", storage: MemoryStorage = None):
    """An authenticated MCP `Client` over the ASGI app, driven by the SDK's OAuth provider."""
    storage = storage or MemoryStorage()
    seen = {}

    async def redirect_handler(url: str) -> None:
        seen["authorize"] = url
        page = await browser.open_consent(url)
        resp = await on_consent(page)
        seen["final"] = resp

    async def callback_handler() -> AuthorizationCodeResult:
        resp = seen["final"]
        assert resp.status_code == 302, resp.text
        loc = resp.headers["location"]
        seen["redirect"] = loc
        p = callback_params(loc)
        return AuthorizationCodeResult(code=p["code"], state=p.get("state"), iss=p.get("iss"))

    meta = OAuthClientMetadata(client_name="test client", redirect_uris=[REDIRECT], grant_types=[
        "authorization_code", "refresh_token"], response_types=["code"], token_endpoint_auth_method="none",
        scope=scope)
    auth = OAuthClientProvider(MCP_URL, meta, storage, redirect_handler=redirect_handler,
                               callback_handler=callback_handler)
    http = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=BASE, auth=auth)
    return Client(streamable_http_client(MCP_URL, http_client=http)), http, seen, storage


def j(result):
    assert not result.is_error, result.content[0].text
    return json.loads(result.content[0].text)


# ----------------------------------------------------------------------- the dance --

def test_full_oauth_dance_pairing_and_tool_call(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    app, gw, svc, mailbox, clock = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            browser = Browser(app, mailbox)

            async def on_consent(page):
                # a brand-new account has no SOUL yet: the consent page offers the pairing-code field
                assert 'name="device_id"' not in page and "XXXX-XXXX" in page
                r = await browser.pair_on_consent(page, "7kq3-m9xd")  # dash and case are ignored
                assert r.status_code == 303
                pid = urlparse(r.headers["location"]).query.split("pid=")[1]
                r = await browser.http.get(r.headers["location"])
                assert "tap" in r.text.lower() or "atinge" in r.text.lower()
                st = await browser.http.get(f"/consent/pair/{pid}")
                assert st.json() == {"state": "awaiting_device"}  # nothing binds without the device
                gw.device_taps_ok(pid)  # the owner taps the check mark on SOUL
                st = await browser.http.get(f"/consent/pair/{pid}")
                assert st.json() == {"state": "paired"}
                page = (await browser.http.get("/consent?req=" + browser.last_consent_page.split(
                    'name="req" value="')[1].split('"')[0])).text
                assert f'value="{DEV}"' in page
                assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
                # a loopback client is not on the allowlist: explicit acknowledgement required
                assert "verified" not in page.split("<section")[1].split("</section>")[0] or "warn" in page
                return await browser.allow(page, DEV, ["soul.read", "soul.write", "soul.notes.read"])

            client, http, seen, storage = await oauth_session(app, browser, on_consent=on_consent)
            async with http, client as c:
                tools = {t.name: t for t in (await c.list_tools()).tools}
                r = await c.call_tool("add_reminder", {"text": "Call the bank", "day": "today", "time": "18:00"})
                today = await c.call_tool("list_today", {})
            await browser.aclose()
            return tools, r, today, seen, storage

    tools, r, today, seen, storage = asyncio.run(go())

    assert set(tools) == {"list_today", "read_soul_inbox", "add_note", "add_reminder", "set_alarm", "show_on_soul",
                          "answer_soul"}
    assert tools["list_today"].annotations.read_only_hint is True
    w = tools["add_note"].annotations
    assert (w.read_only_hint, w.destructive_hint, w.idempotent_hint, w.open_world_hint) == (False, False, False, False)

    # the authorization request used PKCE S256 and the resource indicator; the redirect carried iss
    q = callback_params(seen["authorize"])
    assert q["code_challenge_method"] == "S256" and q["resource"] == MCP_URL
    back = callback_params(seen["redirect"])
    assert back["iss"] in (BASE, BASE + "/") and seen["redirect"].startswith(REDIRECT)
    assert storage.tokens.access_token.startswith("sat_") and storage.tokens.refresh_token.startswith("srt_")
    assert storage.tokens.expires_in == 3600

    out = j(r)
    assert out["delivered"] == "shown" and out["will_ring"] == "yes"
    assert out["resolved"]["when_local"] == "2026-10-02T18:00" and out["tz"] == "Europe/Bucharest"
    assert out["tell_user"] and out["now_local"] == "2026-10-02T14:30"
    push = gw.pushes[-1]
    assert push["device_id"] == DEV and push["action"] == "reminder.create"
    assert push["args"] == {"when": "2026-10-02T18:00", "text": "Call the bank"}
    assert push["origin"] == {"kind": "connector", "app": "other"} and push["needs_accept"] is False
    items = j(today)["items"]
    assert items[0]["source"] == "connector:other" and items[0]["untrusted_text"] == "Call the bank"

    # nothing secret in the logs: tokens, login codes, pairing codes
    logs = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "sat_" not in logs and "srt_" not in logs and PAIR_CODE not in logs
    assert storage.tokens.access_token not in logs
    for _to, _s, body in mailbox.messages:
        code = "".join(ch for ch in body if ch.isdigit())[:6]
        if len(code) == 6:
            assert code not in logs


def test_unauthenticated_mcp_gets_401_with_resource_metadata(tmp_path):
    app, *_ = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            async with asgi_client(app) as http:
                r = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                    headers={"accept": "application/json, text/event-stream"})
                prm = await http.get("/.well-known/oauth-protected-resource/mcp")
                asm = await http.get("/.well-known/oauth-authorization-server")
                bad = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                      headers={"authorization": "Bearer sat_nope",
                                               "accept": "application/json, text/event-stream"})
                return r, prm, asm, bad

    r, prm, asm, bad = asyncio.run(go())
    assert r.status_code == 401 and bad.status_code == 401
    assert (f'resource_metadata="{BASE}/.well-known/oauth-protected-resource/mcp"'
            in r.headers["www-authenticate"])
    p = prm.json()
    assert p["resource"] == MCP_URL and p["authorization_servers"][0].rstrip("/") == BASE
    assert set(p["scopes_supported"]) == {"soul.read", "soul.write", "soul.notes.read"}
    a = asm.json()
    assert a["issuer"].rstrip("/") == BASE
    assert a["code_challenge_methods_supported"] == ["S256"]
    assert a["authorization_response_iss_parameter_supported"] is True
    assert a["token_endpoint_auth_methods_supported"] == ["none", "client_secret_post", "client_secret_basic"]
    assert "private_key_jwt" not in json.dumps(a)
    assert "client_id_metadata_document_supported" not in a  # no CIMD fetcher configured here
    assert set(a["scopes_supported"]) == {"soul.read", "soul.write", "soul.notes.read", "offline_access"}
    assert a["registration_endpoint"].endswith("/register")


def test_cimd_advertised_only_with_fetcher(tmp_path):
    app, *_ = build(tmp_path, cimd_fetch=lambda url: {})

    async def go():
        async with asgi_client(app) as http:
            return (await http.get("/.well-known/oauth-authorization-server")).json()

    assert asyncio.run(go())["client_id_metadata_document_supported"] is True


async def mint_token(app, gw, device_id=DEV, account_id="a_test", scopes=("soul.read", "soul.write")) -> str:
    """A valid access token straight from the provider (register, authorize, approve, exchange)."""
    from mcp.server.auth.provider import AuthorizationParams
    from pydantic import AnyUrl

    from suflet_ai.oauth import SoulClient

    p = app.state.soul.oauth
    gw.add_device(device_id, account_id)
    c = SoulClient(client_id="c_test", redirect_uris=[REDIRECT], token_endpoint_auth_method="none",
                   scope="soul.read soul.write soul.notes.read offline_access")
    await p.register_client(c)
    url = await p.authorize(c, AuthorizationParams(state=None, scopes=list(scopes), code_challenge="a" * 43,
                                                   redirect_uri=AnyUrl(REDIRECT),
                                                   redirect_uri_provided_explicitly=True, resource=MCP_URL))
    back = await p.approve(url.split("req=")[1], account_id, device_id, list(scopes))
    ac = await p.load_authorization_code(c, callback_params(back)["code"])
    return (await p.exchange_authorization_code(c, ac)).access_token


def test_dns_rebinding_protection_rejects_other_hosts(tmp_path):
    app, gw, *_ = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            tok = await mint_token(app, gw)
            hdr = {"accept": "application/json, text/event-stream", "authorization": f"Bearer {tok}",
                   "content-type": "application/json"}
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app),
                                          base_url="https://evil.example") as http:
                evil = await http.post("/mcp", json=body, headers=hdr)
            async with asgi_client(app) as http:
                cross = await http.post("/mcp", json=body, headers={**hdr, "origin": "https://evil.example"})
            return evil, cross

    evil, cross = asyncio.run(go())
    assert evil.status_code == 421  # Host header not {BASE}
    assert cross.status_code == 403  # a browser page on another origin


def test_body_limit_on_mcp(tmp_path):
    app, gw, *_ = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            tok = await mint_token(app, gw)
            async with asgi_client(app) as http:
                return await http.post("/mcp", content=b"x" * 70000,
                                       headers={"content-type": "application/json", "authorization": f"Bearer {tok}",
                                                "accept": "application/json, text/event-stream"})

    assert asyncio.run(go()).status_code == 413  # max_request_body_size = 64 KB


# ------------------------------------------------------------------ token lifecycle --

def test_refresh_rotation_and_grace_over_http(tmp_path):
    """Token endpoint: rotation on use; the previous token within 60 s returns the same pair; later = family dies."""
    app, gw, svc, mailbox, clock = build(tmp_path)
    gw.add_device(DEV, None)

    async def go():
        async with app.router.lifespan_context(app):
            browser = Browser(app, mailbox)

            async def on_consent(page):
                acc = app.state.soul.accounts.db.one("SELECT id FROM accounts")["id"]
                gw.devices[DEV]["account_id"] = acc  # already paired to this account
                page = (await browser.http.get("/consent?req=" + page.split('name="req" value="')[1]
                                               .split('"')[0])).text
                return await browser.allow(page, DEV, ["soul.read", "soul.write"])

            client, http, seen, storage = await oauth_session(app, browser, on_consent=on_consent)
            async with http, client as c:
                await c.list_tools()
            cid = storage.client_info.client_id
            t1 = storage.tokens
            async with asgi_client(app) as raw:
                def refresh(tok):
                    return raw.post("/token", data={"grant_type": "refresh_token", "refresh_token": tok,
                                                    "client_id": cid})
                r2 = await refresh(t1.refresh_token)
                r2b = await refresh(t1.refresh_token)  # replay inside the grace window: same pair
                clock.advance(61)
                r3 = await refresh(t1.refresh_token)  # replay after 60 s: the family is revoked
                r4 = await refresh(r2.json()["refresh_token"])  # ...including the newest one
                use = await raw.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                     headers={"authorization": "Bearer " + r2.json()["access_token"],
                                              "accept": "application/json, text/event-stream",
                                              "mcp-protocol-version": "2025-11-25"})
            await browser.aclose()
            return t1, r2, r2b, r3, r4, use

    t1, r2, r2b, r3, r4, use = asyncio.run(go())
    assert r2.status_code == 200 and r2.json()["refresh_token"] != t1.refresh_token
    assert r2.json()["scope"].split() == ["soul.read", "soul.write", "offline_access"] or \
        set(r2.json()["scope"].split()) == {"soul.read", "soul.write", "offline_access"}
    assert r2b.status_code == 200 and r2b.json() == r2.json()
    assert r3.status_code == 400 and r3.json()["error"] == "invalid_grant"
    assert r4.status_code == 400 and r4.json()["error"] == "invalid_grant"
    assert use.status_code == 401
    grants = app.state.soul.oauth.db.all("SELECT state FROM oauth_grants")
    assert [g["state"] for g in grants] == ["needs_reconnect"]


def test_pkce_mismatch_and_code_replay(tmp_path):
    """Drive /authorize + consent by hand: wrong verifier fails; a replayed code revokes what it produced."""
    import base64
    import hashlib
    import secrets

    app, gw, svc, mailbox, clock = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            async with asgi_client(app) as raw:
                reg = (await raw.post("/register", json={"client_name": "x", "redirect_uris": [REDIRECT],
                                                         "token_endpoint_auth_method": "none",
                                                         "grant_types": ["authorization_code", "refresh_token"],
                                                         "response_types": ["code"]})).json()
            verifier = secrets.token_urlsafe(48)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            url = (f"{BASE}/authorize?response_type=code&client_id={reg['client_id']}&redirect_uri="
                   f"{REDIRECT}&state=st1&code_challenge={challenge}&code_challenge_method=S256"
                   f"&resource={MCP_URL}&scope=soul.read%20soul.write%20offline_access")
            browser = Browser(app, mailbox)
            page = await browser.open_consent(url)
            acc = app.state.soul.accounts.db.one("SELECT id FROM accounts")["id"]
            gw.add_device(DEV, acc)
            page = (await browser.http.get("/consent?req=" + page.split('name="req" value="')[1]
                                           .split('"')[0])).text
            # CSRF: a POST without the token is refused, and nothing is granted
            bad = await browser.http.post("/consent", data={"req": page.split('name="req" value="')[1]
                                                            .split('"')[0], "device_id": DEV,
                                                            "decision": "allow", "ack": "1"})
            ok = await browser.allow(page, DEV, ["soul.read", "soul.write"])
            p = callback_params(ok.headers["location"])
            async with asgi_client(app) as raw:
                tok = lambda v: raw.post("/token", data={"grant_type": "authorization_code", "code": p["code"],
                                                         "redirect_uri": REDIRECT, "client_id": reg["client_id"],
                                                         "code_verifier": v})
                wrong = await tok(secrets.token_urlsafe(48))
                good = await tok(verifier)
                again = await tok(verifier)
                after = await raw.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                       headers={"authorization": "Bearer " + good.json()["access_token"],
                                                "accept": "application/json, text/event-stream"})
            await browser.aclose()
            return bad, ok, p, wrong, good, again, after

    bad, ok, p, wrong, good, again, after = asyncio.run(go())
    assert bad.status_code == 403
    assert ok.status_code == 302 and p["state"] == "st1" and p["iss"].rstrip("/") == BASE
    assert wrong.status_code == 400 and wrong.json()["error"] == "invalid_grant"
    assert good.status_code == 200 and good.json()["token_type"].lower() == "bearer"
    assert set(good.json()["scope"].split()) == {"soul.read", "soul.write", "offline_access"}
    assert again.status_code == 400  # single use
    assert after.status_code == 401  # ... and the replay revoked the grant it had produced


def test_consent_deny_returns_access_denied_with_iss(tmp_path):
    app, gw, svc, mailbox, clock = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            async with asgi_client(app) as raw:
                reg = (await raw.post("/register", json={"client_name": "x", "redirect_uris": [REDIRECT],
                                                         "token_endpoint_auth_method": "none"})).json()
            url = (f"{BASE}/authorize?response_type=code&client_id={reg['client_id']}&redirect_uri={REDIRECT}"
                   f"&state=s9&code_challenge={'a' * 43}&code_challenge_method=S256")
            browser = Browser(app, mailbox)
            page = await browser.open_consent(url)
            r = await browser.http.post("/consent", data={"csrf": page.split('name="csrf" value="')[1].split('"')[0],
                                                          "req": page.split('name="req" value="')[1].split('"')[0],
                                                          "decision": "deny"})
            await browser.aclose()
            return r

    r = asyncio.run(go())
    p = callback_params(r.headers["location"])
    assert r.status_code == 302 and p["error"] == "access_denied" and p["state"] == "s9"
    assert p["iss"].rstrip("/") == BASE


def test_unverified_client_needs_ack_and_fresh_reauth(tmp_path):
    app, gw, svc, mailbox, clock = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            async with asgi_client(app) as raw:
                reg = (await raw.post("/register", json={"client_name": "My tool",
                                                         "redirect_uris": ["https://tools.example/cb"],
                                                         "token_endpoint_auth_method": "none"})).json()
            url = (f"{BASE}/authorize?response_type=code&client_id={reg['client_id']}&redirect_uri="
                   f"https://tools.example/cb&state=s&code_challenge={'a' * 43}&code_challenge_method=S256")
            browser = Browser(app, mailbox)
            page = await browser.open_consent(url)
            acc = app.state.soul.accounts.db.one("SELECT id FROM accounts")["id"]
            gw.add_device(DEV, acc)
            req = page.split('name="req" value="')[1].split('"')[0]
            page = (await browser.http.get("/consent?req=" + req)).text
            no_ack = await browser.allow(page, DEV, ["soul.read"], ack=False)
            clock.advance(11 * 60)  # the sign-in is no longer fresh; the app starts a new request
            page2 = await browser.open_consent(url.replace("state=s", "state=s2"))
            stale = await browser.allow(page2, DEV, ["soul.read"], ack=True)
            # re-auth with a new email code, then come back and allow
            r = await browser.http.get(stale.headers["location"])
            assert r.status_code == 200 and browser.email in r.text
            csrf, nxt = r.text.split('name="csrf" value="')[1].split('"')[0], \
                r.text.split('name="next" value="')[1].split('"')[0]
            r = await browser.http.post("/login", data={"csrf": csrf, "next": nxt, "email": browser.email,
                                                        "lang": "en"})
            assert r.status_code == 200
            r = await browser.http.post("/login/verify", data={"csrf": csrf, "next": nxt, "email": browser.email,
                                                               "code": mailbox.last_code(browser.email),
                                                               "lang": "en"})
            assert r.status_code == 303
            page3 = (await browser.http.get(r.headers["location"])).text
            done = await browser.allow(page3, DEV, ["soul.read", "soul.write"], ack=True)
            await browser.aclose()
            return page, no_ack, stale, done

    page, no_ack, stale, done = asyncio.run(go())
    assert "tools.example" in page and "class=\"warn\"" in page
    # only soul.read is pre-ticked for an unknown host
    assert 'value="soul.write" >' in page or 'value="soul.write" ' in page
    assert 'value="soul.write" checked' not in page
    assert no_ack.status_code == 400
    assert stale.status_code == 303 and "reauth=1" in stale.headers["location"]
    p = callback_params(done.headers["location"])
    assert done.status_code == 302 and done.headers["location"].startswith("https://tools.example/cb?")
    assert p["state"] == "s2" and p["code"]


def test_verified_host_is_named_by_host_not_client_name(tmp_path):
    app, gw, svc, mailbox, clock = build(tmp_path)

    async def go():
        async with app.router.lifespan_context(app):
            async with asgi_client(app) as raw:
                reg = (await raw.post("/register", json={"client_name": "Claude",
                                                         "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
                                                         "token_endpoint_auth_method": "none"})).json()
                spoof = await raw.post("/register", json={"client_name": "Claude (official)",
                                                          "redirect_uris": ["https://claude-ai.example/cb"],
                                                          "token_endpoint_auth_method": "none"})
            url = (f"{BASE}/authorize?response_type=code&client_id={reg['client_id']}&redirect_uri="
                   f"https://claude.ai/api/mcp/auth_callback&state=s&code_challenge={'a' * 43}"
                   f"&code_challenge_method=S256&ui_locales=ro")
            browser = Browser(app, mailbox)
            page = await browser.open_consent(url)
            await browser.aclose()
            return page, spoof

    page, spoof = asyncio.run(go())
    assert spoof.status_code == 400 and spoof.json()["error"] == "invalid_client_metadata"
    assert "verificat" in page and "claude.ai" in page and 'lang="ro"' in page
