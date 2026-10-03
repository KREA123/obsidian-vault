"""/me: Wi-Fi help, SOUL Bridge computers (a one-time code, revoke), data export (JSON download) and account
deletion (GDPR, docs/07 §3.5 / §4.2), over real sockets with a fake SOUL."""
from __future__ import annotations

import json

import pytest

from test_web_pair_me import GOOD, _hidden, _pair, cloud, run  # noqa: F401 - the fixture


@pytest.mark.builtin_off
def test_wifi_help_is_public_and_bilingual(cloud):
    b = cloud["browser"]()

    async def flow():
        en = await b.http.get("/me/wifi-help")
        ro = await b.http.get("/me/wifi-help?lang=ro")
        return en, ro

    en, ro = run(flow())
    assert en.status_code == 200 and "5 seconds" in en.text and "2.4 GHz" in en.text and "192.168.4.1" in en.text
    assert "frame-ancestors 'none'" in en.headers["content-security-policy"]
    assert "5 secunde" in ro.text and "Parolă greșită" in ro.text


@pytest.mark.builtin_off
def test_me_pairs_a_computer_lists_and_forgets_it(cloud):
    d = cloud["device"]()
    b = cloud["browser"]()
    mal = cloud["browser"]("mallory@example.com", "Mal")
    gw = cloud["gw"]

    async def flow():
        await _pair(b, d)
        me = (await b.http.get("/me")).text
        assert "Your computers (SOUL Bridge)" in me and "No computer paired yet." in me
        assert 'value="bridge"' in me  # the brain can be picked here too
        csrf = _hidden(me, "csrf")
        r = await b.http.post(f"/me/devices/{d.device_id}/bridge", data={"csrf": csrf})
        assert r.status_code == 200 and "soul-bridge pair " in r.text and "--cloud 127.0.0.1:" in r.text
        code = _hidden(r.text, "cmd").split()[2].replace("-", "")
        tok = gw.bridges.pair(code, "Ana's laptop", "198.51.100.3")
        me = (await b.http.get("/me")).text
        assert "Ana&#39;s laptop" in me and "not connected" in me
        # someone else cannot make codes for this SOUL, nor forget its computers
        mme = await mal.pair_page()
        r = await mal.http.post(f"/me/devices/{d.device_id}/bridge", data={"csrf": _hidden(mme, "csrf")})
        assert r.headers["location"] == "/me?err=forbidden"
        r = await mal.http.post(f"/me/bridge/{tok['token_id']}/revoke", data={"csrf": _hidden(mme, "csrf")})
        assert r.headers["location"] == "/me?err=forbidden"
        r = await b.http.post(f"/me/bridge/{tok['token_id']}/revoke", data={"csrf": csrf})
        assert r.headers["location"] == "/me"
        assert gw.bridges.tokens(gw.store.owner(d.device_id)) == []
        r = await b.http.post(f"/me/devices/{d.device_id}/brain", data={"csrf": csrf, "brain": "bridge"})
        assert r.status_code == 303
        assert d.wait_for(lambda rs: any(m.get("t") == "config" and m.get("brain") == "bridge" for m in rs), 10, "b")

    run(flow())


@pytest.mark.builtin_off
def test_export_then_delete_the_account(cloud):
    d = cloud["device"]()
    b = cloud["browser"]()
    gw, svc = cloud["gw"], cloud["svc"]

    async def flow():
        await _pair(b, d)
        account = gw.store.owner(d.device_id)
        csrf = _hidden((await b.http.get("/me")).text, "csrf")
        assert (await b.http.post("/me/keys", data={"csrf": csrf, "provider": "anthropic", "key": GOOD})).status_code == 303
        svc.action(d.device_id, "note.create", {"text": "buy milk", "tags": []}, lang="en", source="device")
        gw.bridges.pair(gw.bridges.pair_code(d.device_id)["code"], "pc", "198.51.100.3")
        oauth = cloud["app"].state.soul.oauth
        oauth.db.exec("INSERT INTO oauth_grants(grant_id, account_id, device_id, client_id, client_host, client_app, "
                      "verified, scopes, state, created) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      ("g_x", account, d.device_id, "c1", "claude.ai", "claude", 1, "soul.read", "connected", 1))
        # the export: a JSON download with everything, and no secret
        r = await b.http.get("/me/export")
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
        data = r.json()
        assert data["account"]["email"] == "ana.pop@example.com" and data["format"] == "soul-export/1"
        dev = data["devices"][0]
        assert dev["device"]["device_id"] == d.device_id
        assert "buy milk" in json.dumps(dev["items"])
        assert data["api_keys"]["anthropic"] == {"set": True}
        assert data["paired_computers"][0]["label"] == "pc"
        assert data["connected_apps"][0]["client_host"] == "claude.ai"
        blob = json.dumps(data)
        assert GOOD not in blob and "sbt_" not in blob and "sat_" not in blob and "sdt_" not in blob
        assert (await b.http.get("/v1/me/export")).json()["account"]["id"] == account
        signed_out = cloud["browser"]("eve@example.com", "Eve")
        r = await signed_out.http.get("/v1/me/export")
        assert r.status_code == 401
        # deletion: a confirmation page, the exact word, then everything goes
        page = await b.http.get("/me/delete")
        assert page.status_code == 200 and "Type DELETE to confirm" in page.text
        r = await b.http.post("/me/delete", data={"csrf": csrf, "confirm": "nope"})
        assert r.status_code == 422 and "exactly" in r.text
        assert gw.store.owner(d.device_id) == account
        r = await b.http.post("/me/delete", data={"csrf": csrf, "confirm": "delete"})
        assert r.status_code == 200 and "gone" in r.text
        assert d.wait_for(lambda rs: any(m.get("t") == "unpaired" for m in rs), 10, "unpaired")
        assert gw.store.owner(d.device_id) is None
        assert svc.keys.get(account, "anthropic") is None
        assert oauth.grants(account) == [] and gw.bridges.tokens(account) == []
        assert svc.state.items(d.device_id) == []
        acc = cloud["app"].state.soul.accounts
        assert acc.get_account(account) is None
        assert acc.db.one("SELECT 1 FROM accounts WHERE email=?", ("ana.pop@example.com",)) is None
        assert "Sign in to see your SOUL" in (await b.http.get("/me")).text

    run(flow())


@pytest.mark.builtin_off
def test_api_delete_needs_csrf_and_a_fresh_sign_in(cloud):
    b = cloud["browser"]()

    async def flow():
        await b.pair_page()  # signs in
        acc = cloud["app"].state.soul.accounts
        token = b.http.cookies.get("__Host-soul_csrf")
        r = await b.http.delete("/v1/me")
        assert r.status_code == 403
        real = acc.clock
        acc.clock = lambda: real() + 11 * 60
        r = await b.http.delete("/v1/me", headers={"X-CSRF-Token": token})
        assert r.status_code == 401 and r.json()["error"]["code"] == "reauth_required"
        acc.clock = real
        r = await b.http.delete("/v1/me", headers={"X-CSRF-Token": token})
        assert r.status_code == 204
        assert acc.db.one("SELECT 1 FROM accounts WHERE email=?", ("ana.pop@example.com",)) is None

    run(flow())
