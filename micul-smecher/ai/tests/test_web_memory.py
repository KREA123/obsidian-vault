"""/me › SOUL Memory backup (docs/10-SOUL-MEMORY.md §5): the owner sees the encrypted copy, downloads it as JSON,
deletes it; another account cannot; the GDPR export carries it."""
from __future__ import annotations

import json

import pytest

from test_web_pair_me import _hidden, _pair, cloud, run  # noqa: F401  (the fixture)


@pytest.mark.builtin_off
def test_me_memory_backup_view_export_delete(cloud):  # noqa: F811
    d = cloud["device"]()
    b = cloud["browser"]()
    mal = cloud["browser"]("mallory@example.com", "Mal")
    backups = cloud["gw"].memory_backups

    async def flow():
        await _pair(b, d)
        me = (await b.http.get("/me")).text
        assert "Memory backup" in me and "backup off" in me
        backups.put(d.device_id, {"v": 1, "facts": [{"text": "My sister is Ana", "kind": "person", "created": 2},
                                                    {"text": "I like tea", "kind": "preference", "created": 1}]})
        me = (await b.http.get("/me")).text
        assert f"/me/devices/{d.device_id}/memory" in me and "2 facts" in me
        page = (await b.http.get(f"/me/devices/{d.device_id}/memory")).text
        assert "My sister is Ana" in page and "I like tea" in page
        page = (await b.http.get(f"/me/devices/{d.device_id}/memory?q=tea")).text
        assert "I like tea" in page and "My sister is Ana" not in page
        r = await b.http.get(f"/me/devices/{d.device_id}/memory.json")
        assert r.headers["content-disposition"].startswith("attachment") and len(r.json()["facts"]) == 2
        exp = (await b.http.get("/me/export")).json()
        assert exp["devices"][0]["memory_backup"]["facts"][0]["text"] == "My sister is Ana"
        # another account sees nothing and cannot delete
        mme = await mal.pair_page()  # signs Mal in
        r = await mal.http.get(f"/me/devices/{d.device_id}/memory")
        assert r.status_code == 404 and "My sister" not in r.text
        r = await mal.http.post(f"/me/devices/{d.device_id}/memory/delete", data={"csrf": _hidden(mme, "csrf")})
        assert r.headers["location"] == "/me?err=forbidden" and backups.get(d.device_id) is not None
        # the owner deletes it
        r = await b.http.post(f"/me/devices/{d.device_id}/memory/delete", data={"csrf": _hidden(page, "csrf")})
        assert r.status_code == 200 and "Backup deleted" in r.text and backups.get(d.device_id) is None
        assert json.loads((await b.http.get(f"/me/devices/{d.device_id}/memory.json")).text)["facts"] == []

    run(flow())
