"""CIMD (Client ID Metadata Documents, MCP authorization spec / docs/07 §3.7): the SSRF-safe fetcher, and the
whole OAuth dance with the official MCP client SDK using an https client_id instead of DCR (what claude.ai's
"Use Claude's published identity" does). No network: DNS and HTTPS are injected."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

import pytest
from mcp.client import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata

import httpx2
from _connector_kit import (BASE, DEV, HOST, MCP_URL, REDIRECT, Browser, FakeClock, StubGateway, asgi_client,
                            callback_params, make_service)
from suflet_ai.accounts import DevMailbox
from suflet_ai.cimd import CimdRejected, check_url, fetch_client_metadata, ip_allowed, make_fetcher
from suflet_ai.mcp_remote import create_remote_app

CID = "https://claude.example/oauth/mcp-client-metadata"
CLAUDE_CODE = "https://claude.ai/oauth/claude-code-client-metadata"


def doc(**kw):
    d = {"client_id": CID, "client_name": "Mail helper", "redirect_uris": [REDIRECT],
         "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
         "token_endpoint_auth_method": "none"}
    d.update(kw)
    return d


def served(d, status=200, ctype="application/json"):
    calls = []

    def get(ip, host, path, timeout):
        calls.append((ip, host, path))
        return status, ctype, json.dumps(d).encode() if not isinstance(d, bytes) else d
    return get, calls


def public(host):
    return ["93.184.216.34"]


def test_url_rules():
    assert check_url(CID) == ("claude.example", "/oauth/mcp-client-metadata")
    for bad in ("http://claude.example/c", "https://claude.example", "https://claude.example/",
                "https://u:p@claude.example/c", "https://claude.example:8443/c", "https://claude.example/c#x",
                "https://localhost/c", "https://soul.local/c", "ftp://x/y", "https://" + "a" * 600 + "/c"):
        with pytest.raises(CimdRejected):
            check_url(bad)


def test_only_public_addresses():
    for ip in ("93.184.216.34", "2606:4700:4700::1111"):
        assert ip_allowed(ip), ip
    for ip in ("127.0.0.1", "10.1.2.3", "172.16.0.9", "192.168.1.1", "169.254.169.254", "100.64.0.1", "0.0.0.0",
               "::1", "fe80::1", "fd00::1", "::ffff:10.0.0.1", "224.0.0.1", "198.51.100.7", "garbage"):
        assert not ip_allowed(ip), ip


def test_fetch_rules():
    get, calls = served(doc())
    assert fetch_client_metadata(CID, resolver=public, get=get)["client_name"] == "Mail helper"
    assert calls == [("93.184.216.34", "claude.example", "/oauth/mcp-client-metadata")]  # the pinned address
    cases = [
        (lambda h: ["93.184.216.34", "10.0.0.5"], served(doc())[0], "non-public"),  # one private answer is enough
        (lambda h: ["169.254.169.254"], served(doc())[0], "non-public"),
        (public, served(doc(), status=302)[0], "redirect"),
        (public, served(doc(), status=404)[0], "HTTP 404"),
        (public, served(b"x" * (16 * 1024 + 1))[0], "16 KB"),
        (public, served(doc(), ctype="text/html")[0], "not JSON"),
        (public, served(b"{not json")[0], "not JSON"),
        (public, served(doc(client_id="https://other.example/c"))[0], "differs"),
        (public, served(doc(redirect_uris=[]))[0], "redirect_uris"),
        (public, served(doc(client_secret="s"))[0], "public"),
        (public, served([1, 2])[0], "object"),
    ]
    for resolver, get, why in cases:
        with pytest.raises(CimdRejected) as ei:
            fetch_client_metadata(CID, resolver=resolver, get=get)
        assert why in ei.value.reason, (why, ei.value.reason)

    def boom(*a):
        raise OSError("connection refused")
    with pytest.raises(CimdRejected):
        fetch_client_metadata(CID, resolver=public, get=boom)


def test_full_oauth_dance_with_a_cimd_client(tmp_path):
    """The SDK client has no registration: its client_id is the URL; SOUL fetches the document."""
    clock = FakeClock()
    mailbox = DevMailbox()
    gw = StubGateway()
    get, calls = served(doc())
    app = create_remote_app(make_service(tmp_path, clock), gw, public_host=HOST, db_path=":memory:", mailer=mailbox,
                            clock=clock, cimd_fetch=make_fetcher(resolver=public, get=get))

    class Storage:
        tokens = client_info = None

        async def get_tokens(self):
            return self.tokens

        async def set_tokens(self, t):
            self.tokens = t

        async def get_client_info(self):
            return self.client_info

        async def set_client_info(self, c):
            self.client_info = c

    async def go():
        async with app.router.lifespan_context(app):
            async with asgi_client(app) as http:
                asm = (await http.get("/.well-known/oauth-authorization-server")).json()
                reg_before = await http.post("/register", json={"redirect_uris": ["https://evil.example/cb"]})
            browser = Browser(app, mailbox)
            seen = {}
            storage = Storage()

            async def redirect_handler(url):
                seen["authorize"] = url
                page = await browser.open_consent(url)
                seen["page"] = page
                r = await browser.pair_on_consent(page, "7KQ3M9XD")
                pid = urlparse(r.headers["location"]).query.split("pid=")[1]
                gw.device_taps_ok(pid)
                page = (await browser.http.get("/consent?req=" + browser.last_consent_page.split(
                    'name="req" value="')[1].split('"')[0])).text
                seen["final"] = await browser.allow(page, DEV, ["soul.read", "soul.write"])

            async def callback_handler():
                p = callback_params(seen["final"].headers["location"])
                return AuthorizationCodeResult(code=p["code"], state=p.get("state"), iss=p.get("iss"))

            meta = OAuthClientMetadata(client_name="Mail helper", redirect_uris=[REDIRECT], token_endpoint_auth_method="none",
                                       grant_types=["authorization_code", "refresh_token"], response_types=["code"],
                                       scope="soul.read soul.write offline_access")
            auth = OAuthClientProvider(MCP_URL, meta, storage, redirect_handler=redirect_handler,
                                       callback_handler=callback_handler, client_metadata_url=CID)
            http = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=BASE, auth=auth)
            async with http, Client(streamable_http_client(MCP_URL, http_client=http)) as c:
                r = await c.call_tool("show_on_soul", {"title": "Hello from CIMD"})
            await browser.aclose()
            return asm, reg_before, seen, storage, r

    asm, reg, seen, storage, r = asyncio.run(go())
    assert asm["client_id_metadata_document_supported"] is True
    q = callback_params(seen["authorize"])
    assert q["client_id"] == CID  # no /register call: the URL is the client id
    assert storage.client_info.client_id == CID
    assert storage.tokens.access_token.startswith("sat_")
    assert calls and calls[0][1] == "claude.example"
    assert "claude.example" in seen["page"]  # the consent page names the client by its client_id host
    assert not r.is_error and gw.pushes[-1]["action"] == "answer.show"


def test_reserved_names_only_from_the_vouched_host(tmp_path):
    """Claude Code's own CIMD document (claude.ai, loopback redirects, name "Claude Code") is accepted; the same
    name served from any other host is not (a lookalike)."""
    from suflet_ai.oauth import SoulOAuthProvider
    from suflet_ai.accounts import Database

    docs = {CLAUDE_CODE: doc(client_id=CLAUDE_CODE, client_name="Claude Code"),
            CID: doc(client_name="Claude Code")}
    p = SoulOAuthProvider(Database(":memory:"), BASE, MCP_URL, cimd_fetch=lambda u: dict(docs[u]))

    async def go():
        return await p.get_client(CLAUDE_CODE), await p.get_client(CID)

    ok, bad = asyncio.run(go())
    assert ok is not None and ok.client_name == "Claude Code"
    assert bad is None
