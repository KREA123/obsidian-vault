"""/pair and /me, the phone pages (docs/07-CONNECT-AI.md §0.1 steps 4 and 6, §3.4, §3.5), over real sockets.

A fake SOUL (tools/fake_device.py through e2e_connect.DeviceRunner) shows its pairing code; a browser signs in by
email code on /pair, types the code, SOUL's owner taps Yes (the fake device answers pair.ok), the brain page offers
the founder's four choices (no AI paid by SOUL: SOUL_BUILTIN_AI=0 is the default), and /me manages keys, brains,
connected apps and unpairing. Keys are checked with a stub (no network) and never come back unmasked.
"""
from __future__ import annotations

import asyncio
import html
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from e2e_connect import Browser, DeviceRunner, ServerThread, _hidden, free_port  # noqa: E402

from suflet_ai import gateway as gateway_mod
from suflet_ai.accounts import DevMailbox
from suflet_ai.app import create_app
from suflet_ai.config import Settings
from suflet_ai.devices import DeviceStore
from suflet_ai.gateway import Gateway
from suflet_ai.soul import SoulService

GOOD = "sk-ant-api03-good-0123456789abcdefghij"
BAD = "sk-ant-api03-bad-0123456789abcdefghijk"
OAI = "sk-proj-good-0123456789abcdefghijklmn"


def stub_check(provider: str, key: str) -> str:
    return "bad" if "bad" in key else "ok" if "good" in key else "unverified"


@pytest.fixture
def cloud(tmp_path, monkeypatch):
    port = free_port()
    host = f"127.0.0.1:{port}"
    for k, v in {"SOUL_ENV": "dev", "SOUL_PUBLIC_HOST": host, "SOUL_PUBLIC_SCHEME": "http"}.items():
        monkeypatch.setenv(k, v)
    for k in ("SUFLET_API_TOKEN", "SOUL_ANTHROPIC_KEY", "SOUL_OPENAI_KEY", "SOUL_TRUST_PROXY"):
        monkeypatch.delenv(k, raising=False)
    svc = SoulService(settings=Settings(data_dir=str(tmp_path)), master_secret=b"m" * 32)
    gw = Gateway(svc, DeviceStore(str(tmp_path / "gateway.sqlite"), host=host, policy="pending", pepper=b"p" * 32))
    mailbox = DevMailbox()
    app = create_app(service=svc, gateway=gw, mailer=mailbox, db_path=str(tmp_path / "auth.sqlite"), key_check=stub_check)
    srv = ServerThread(app, port).start()
    devices, browsers = [], []

    def device() -> DeviceRunner:
        d = DeviceRunner(srv.base, host)
        devices.append(d)
        d.connect()
        d.wait_for(lambda rs: any(m.get("t") == "pairing" for m in rs), 10, "pairing code")
        return d

    def browser(email: str = "ana.pop@example.com", first: str = "Ana") -> Browser:
        b = Browser(srv.base, mailbox.last_code, email=email, first_name=first)
        browsers.append(b)
        return b

    yield {"base": srv.base, "gw": gw, "svc": svc, "device": device, "browser": browser, "app": app}
    for b in browsers:  # its connections belong to the test's (closed) loop: just drop them
        try:
            asyncio.run(b.aclose())
        except RuntimeError:
            pass
    for d in devices:
        d.close()
    srv.stop()
    gateway_mod.set_gateway(None)


def code_of(d: DeviceRunner) -> str:
    c = next(m["code"] for m in reversed(d.received) if m.get("t") == "pairing")
    return f"{c[:4]}-{c[4:]}"


def run(coro):
    return asyncio.run(coro)


async def _pair(b: Browser, d: DeviceRunner) -> str:
    pid = await b.pair_claim(code_of(d))
    assert d.wait_for(lambda rs: any(m.get("t") == "pair.confirm" for m in rs), 10, "pair.confirm")
    brain_path = await b.pair_wait(pid)
    assert brain_path == f"/pair/brain?d={d.device_id}"
    return pid


@pytest.mark.builtin_off
def test_pair_page_signs_in_claims_and_needs_the_tap_on_soul(cloud):
    d = cloud["device"]()
    b = cloud["browser"]()

    async def flow():
        # signed out: one clear step, the security headers, the brand, and GET claims nothing
        r = await b.http.get("/pair")
        assert r.status_code == 200 and 'id="signin"' in r.text and "Continue with email" in r.text
        assert r.headers["content-security-policy"].startswith("default-src 'self'")
        assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
        assert r.headers["referrer-policy"] == "no-referrer" and r.headers["x-frame-options"] == "DENY"
        assert 'class="wordmark"' in r.text and "/static/soul-web.css" in r.text
        css = (await b.http.get("/static/soul-web.css")).text
        assert "Bricolage Grotesque" in css and "#FFF0C8" in css and "#16181D" in css
        assert (await b.http.get("/static/fonts/bricolage.woff2")).headers["content-type"] == "font/woff2"
        js = (await b.http.get("/static/soul-pair.js")).text
        assert "location.hash" in js and "sessionStorage" in js  # the code travels in the fragment only
        # sign in by email code (lands back on /pair), type the code
        pid = await b.pair_claim(code_of(d))
        # nothing is bound before the tap
        assert cloud["gw"].store.owner(d.device_id) is None
        api = (await b.http.get(f"/v1/me/pair/{pid}")).json()
        assert api["state"] in ("awaiting_device", "paired")
        conf = d.wait_for(lambda rs: next((m for m in rs if m.get("t") == "pair.confirm"), None), 10, "pair.confirm")
        assert conf["name"] == "Ana" and conf["account_hint"] == "a***@example.com"
        brain = await b.pair_wait(pid)  # the fake SOUL answered pair.ok (its owner's tap)
        assert brain == f"/pair/brain?d={d.device_id}"
        assert (await b.http.get(f"/v1/me/pair/{pid}")).json() == {"state": "paired"}
        assert cloud["gw"].store.owner(d.device_id)
        # the founder's four choices, and no AI paid by SOUL
        page = (await b.http.get(brain)).text
        for want in ("Connect my ChatGPT", "Coming soon, pending OpenAI", "Connect my Claude", "My own API key",
                     "Offline (no AI)"):
            assert want in html.unescape(page), want
        assert 'value="cloud"' not in page and "SOUL Cloud</h2>" not in page
        # "Connect my Claude": brain none on SOUL (no paid AI), then the connector steps with the address to copy
        r = await b.choose(page, "none", "/me/connect-claude")
        assert r.status_code == 303 and r.headers["location"] == f"/me/connect-claude?d={d.device_id}"
        c = (await b.http.get(r.headers["location"])).text
        assert f'value="{cloud["base"]}/mcp"' in c and "Register automatically" in c and "data-copy" in c
        assert 'name="key"' in c  # optional own Anthropic key, to talk to Claude on SOUL
        cfg = d.wait_for(lambda rs: next((m for m in rs if m.get("t") == "config" and "brain" in m), None), 10, "config")
        assert cfg["brain"] == "none"
        # "Connect my ChatGPT": the Sign in with ChatGPT stub + the connector meanwhile
        s = html.unescape((await b.http.get(f"/me/signin-chatgpt?d={d.device_id}")).text)
        assert "Coming soon, pending OpenAI's approval" in s and "Developer mode" in s and "/mcp" in s

    run(flow())


@pytest.mark.builtin_off
def test_pair_page_errors_and_json_api(cloud):
    d = cloud["device"]()
    b = cloud["browser"]()
    other = cloud["browser"]("mallory@example.com", "Mal")

    async def flow():
        page = await b.pair_page()
        csrf = _hidden(page, "csrf")
        r = await b.http.post("/pair/claim", data={"csrf": csrf, "code": "ZZZZ-ZZZZ"})
        assert r.status_code == 404 and "That code is not valid" in r.text
        r = await b.http.post("/pair/claim", data={"csrf": "nope", "code": code_of(d)})
        assert r.status_code == 403  # CSRF
        r = await b.http.post("/v1/me/pair/claim", json={"code": "ZZZZZZZZ"})
        assert r.status_code == 403  # CSRF header missing
        token = b.http.cookies.get("__Host-soul_csrf")
        r = await b.http.post("/v1/me/pair/claim", json={"code": code_of(d)}, headers={"X-CSRF-Token": token})
        assert r.status_code == 202, r.text
        body = r.json()
        assert body["state"] == "awaiting_device" and body["device"]["id"] == d.device_id and body["expires_in"] == 120
        assert "_device_msg" not in body
        await b.pair_wait(body["pid"])
        # someone else's account: the SOUL is owned
        await other.pair_page()
        d.wait_for(lambda rs: any(m.get("t") == "paired" for m in rs), 10, "paired")
        # a fresh SOUL whose code Mallory types while it is owned by Ana is a different SOUL; Ana's is not claimable
        assert (await other.http.get(f"/v1/me/pair/{body['pid']}")).json()["state"] == "expired"  # not hers

    run(flow())


@pytest.mark.builtin_off
def test_me_keys_brains_apps_and_unpair(cloud):
    d = cloud["device"]()
    b = cloud["browser"]()
    mal = cloud["browser"]("mallory@example.com", "Mal")
    svc = cloud["svc"]

    async def flow():
        await _pair(b, d)
        me = (await b.http.get("/me")).text
        assert d.device_id[-4:] in me and "Your SOULs" in me and "online" in me
        assert 'value="cloud"' not in me  # no built-in AI to pick
        csrf = _hidden(me, "csrf")
        # keys: a bad one is refused by the provider check, an admin key by its prefix, a good one saved masked
        r = await b.http.post("/me/keys", data={"csrf": csrf, "provider": "anthropic", "key": BAD})
        assert r.status_code == 422 and "does not work" in r.text
        r = await b.http.post("/me/keys", data={"csrf": csrf, "provider": "anthropic",
                                                "key": "sk-ant-admin01-0123456789abcdefghij"})
        assert r.status_code == 422 and "admin keys" in r.text
        r = await b.http.post("/me/keys", data={"csrf": csrf, "provider": "anthropic", "key": GOOD})
        assert r.status_code == 303
        r = await b.http.post("/me/keys", data={"csrf": csrf, "provider": "openai", "key": OAI,
                                                "device_id": d.device_id})
        assert r.status_code == 303 and r.headers["location"] == "/me?done=key"  # and SOUL switched to it
        me = (await b.http.get("/me")).text
        assert GOOD not in me and OAI not in me and "sk-ant-…ghij" in html.unescape(me)
        assert "checked" in me
        account = cloud["gw"].store.owner(d.device_id)
        assert svc.keys.get(account, "anthropic") == GOOD  # stored encrypted, for the relay (B2)
        assert d.wait_for(lambda rs: any(m.get("t") == "config" and m.get("brain") == "chatgpt" for m in rs), 10, "b")
        # brains: cloud is refused while built-in AI is off; claude needs the key (now there)
        r = await b.http.post(f"/me/devices/{d.device_id}/brain", data={"csrf": csrf, "brain": "cloud"})
        assert r.headers["location"] == "/me?err=forbidden"
        r = await b.http.post(f"/me/devices/{d.device_id}/brain", data={"csrf": csrf, "brain": "claude"})
        assert r.headers["location"] == "/me?done=key"
        assert d.wait_for(lambda rs: any(m.get("t") == "config" and m.get("brain") == "claude" for m in rs), 10, "c")
        # removing the key moves a SOUL that used it off it
        await b.http.post("/me/keys/anthropic/delete", data={"csrf": csrf})
        assert svc.keys.get(account, "anthropic") is None
        assert cloud["gw"].store.get_device(d.device_id)["brain"] == "none"  # no paid AI to fall back to
        # another account cannot touch this SOUL
        mme = (await mal.pair_page())
        r = await mal.http.post(f"/me/devices/{d.device_id}/brain",
                                data={"csrf": _hidden(mme, "csrf"), "brain": "none"})
        assert r.headers["location"] == "/me?err=forbidden"
        r = await mal.http.post(f"/me/devices/{d.device_id}/unpair", data={"csrf": _hidden(mme, "csrf")})
        assert r.headers["location"] == "/me?err=forbidden"
        # a connected app shows up and can be disconnected
        grant = cloud["app"].state.soul.oauth  # the OAuth provider
        grant.db.exec("INSERT INTO oauth_grants(grant_id, account_id, device_id, client_id, client_host, client_app, "
                      "verified, scopes, state, created) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      ("g_test", account, d.device_id, "c1", "claude.ai", "claude", 1, "soul.read soul.write",
                       "connected", 1))
        me = (await b.http.get("/me")).text
        assert "Claude" in me and "/me/grants/g_test/revoke" in me
        r = await mal.http.post("/me/grants/g_test/revoke", data={"csrf": _hidden(mme, "csrf")})
        assert r.headers["location"] == "/me?err=forbidden"
        await b.http.post("/me/grants/g_test/revoke", data={"csrf": csrf})
        assert "/me/grants/g_test/revoke" not in (await b.http.get("/me")).text
        # unpair: SOUL is told, the grant family is gone
        r = await b.http.post(f"/me/devices/{d.device_id}/unpair", data={"csrf": csrf})
        assert r.status_code == 303 and r.headers["location"] == "/me"
        assert d.wait_for(lambda rs: any(m.get("t") == "unpaired" for m in rs), 10, "unpaired")
        assert cloud["gw"].store.owner(d.device_id) is None
        # sign out
        r = await b.http.post("/me/logout", data={"csrf": csrf})
        assert "Sign in to see your SOUL" in (await b.http.get("/me")).text

    run(flow())


@pytest.mark.builtin_off
def test_keys_need_a_fresh_sign_in_and_unverified_keys(cloud, monkeypatch):
    d = cloud["device"]()
    b = cloud["browser"]()

    async def flow():
        await _pair(b, d)
        csrf = _hidden((await b.http.get("/me")).text, "csrf")
        # a key the check cannot verify (no network) is saved, marked "not checked yet"
        r = await b.http.post("/me/keys", data={"csrf": csrf, "provider": "openai",
                                                "key": "sk-proj-maybe-0123456789abcdefghij"})
        assert r.status_code == 303
        assert "saved, not checked yet" in (await b.http.get("/me")).text
        # 11 minutes later, keys and unpairing need a new email code
        acc = cloud["app"].state.soul.accounts
        acc.clock = lambda: __import__("time").time() + 11 * 60
        r = await b.http.post("/me/keys", data={"csrf": csrf, "provider": "anthropic", "key": GOOD})
        assert r.status_code == 303 and "reauth=1" in r.headers["location"]
        r = await b.http.post(f"/me/devices/{d.device_id}/unpair", data={"csrf": csrf})
        assert "reauth=1" in r.headers["location"]

    run(flow())


def test_builtin_ai_flag_shows_soul_cloud(cloud):
    """SOUL_BUILTIN_AI=1 (tests' default for the older suites): the built-in choice is back."""
    d = cloud["device"]()
    b = cloud["browser"]()

    async def flow():
        await _pair(b, d)
        page = (await b.http.get(f"/pair/brain?d={d.device_id}")).text
        assert 'value="cloud"' in page and "SOUL Cloud</h2>" in page
        r = await b.choose(page, "cloud")
        assert r.headers["location"] == "/me?done=cloud"

    run(flow())


@pytest.mark.builtin_off
def test_no_paid_ai_by_default_device_turns_use_the_rules(cloud):
    """With SOUL_BUILTIN_AI=0 a paired SOUL starts on `none`; even a stored `cloud` brain answers with the rules."""
    d = cloud["device"]()
    b = cloud["browser"]()

    async def flow():
        await _pair(b, d)

    run(flow())
    gw = cloud["gw"]
    assert gw.store.get_device(d.device_id)["brain"] == "none"
    w = [m for m in d.received if m.get("t") == "welcome"]
    assert w and w[0]["trial"] is None and w[0]["brain"] == "none"
    gw.store.update_device(d.device_id, brain="cloud")  # an old row
    r = d.ask("remind me tomorrow at 9 to call mom")
    assert r["t"] == "reply" and r["provider"] == "rules" and r.get("note") == "no_key", r
    assert any(m.get("t") == "push" and m.get("action") == "reminder.create" for m in d.received)
