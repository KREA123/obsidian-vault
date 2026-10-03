"""The device hub: WebSocket `soul.v1`, long-poll parity, pushes, acks, replay, close codes (docs/07 §6.4-6.11)."""
import json
import threading
import time

import pytest
from starlette.websockets import WebSocketDisconnect

import suflet_ai.gateway as gateway_mod
from _gateway_kit import DEV, DEV2, Env, hello, recv, recv_until, send


def note_push(e, i=0, device=DEV, **kw):
    return e.gw.push(device, "note.create", {"text": f"note {i}", "tags": []}, f"it_n{i}",
                     {"kind": "connector", "app": "claude"}, **kw)


def close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as ei:
        for _ in range(500):
            ws.receive_text()
    return ei.value.code


# ------------------------------------------------------------------ handshake --

def test_ping_is_public(tmp_path):
    r = Env(tmp_path).client.get("/v1/ping")
    assert r.status_code == 200 and r.json()["ok"] is True and isinstance(r.json()["time"], int)


def test_ws_needs_the_subprotocol_and_a_valid_token(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    with e.ws(d.token, subprotocols=("other",)) as ws:
        assert close_code(ws) == 4426
    with e.ws("sdt_wrong") as ws:
        assert close_code(ws) == 4401
    with e.ws(None) as ws:
        assert close_code(ws) == 4401


def test_first_frame_must_be_hello_and_hello_has_a_deadline(tmp_path, monkeypatch):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    with e.ws(d.token) as ws:
        send(ws, {"v": 1, "t": "status", "rssi": -60})
        assert close_code(ws) == 4400
    with e.ws(d.token) as ws:
        ws.send_text("not json")
        assert close_code(ws) == 4400
    monkeypatch.setattr(gateway_mod, "HELLO_TIMEOUT", 0.2)
    with e.ws(d.token) as ws:
        assert close_code(ws) == 4400


def test_unpaired_hello_welcome_pairing_then_confirm_on_device(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    with e.ws(d.token) as ws:
        send(ws, hello(lang="ro", tz_posix="EET-2EEST,M3.5.0/3,M10.5.0/4"))
        w = recv(ws)
        assert w["t"] == "welcome" and w["state"] == "pending" and w["brain"] == "none"
        assert w["tz"] == "Europe/Bucharest" and w["posix_tz"].startswith("EET-2EEST")
        assert w["limits"] == {"ask_per_min": 20, "ask_per_day": 600, "frames_per_s": 2}
        assert w["allowance"] is None and w["trial"] is None and w["lang"] == "ro"
        assert set(w["models"]) == {"claude", "openai"} and w["quiet"] == {"from": "22:00", "to": "07:00"}
        rd = recv(ws)
        assert rd == {"v": 1, "t": "replay.done", "last": 0}
        p = recv(ws)
        assert p["t"] == "pairing" and len(p["code"]) == 8 and p["url"].endswith(f"&d={DEV}")
        # the account claims the code (the /pair page); the device must confirm with a touch
        c = e.gw.claim("acc_1", "Ana", "ana@example.com", p["code"], "198.51.100.4")
        assert e.gw.claim_state(c["pid"], "acc_1") == {"state": "awaiting_device"}
        m = recv(ws)
        assert m["t"] == "pair.confirm" and m["pid"] == c["pid"] and m["name"] == "Ana"
        assert m["account_hint"] == "a***@example.com" and m["expires_in"] == 120
        send(ws, {"v": 1, "t": "pair.ok", "pid": c["pid"]})
        got = recv_until(ws, "inbox.state")
        assert got[0] == {"v": 1, "t": "paired", "owner": "Ana", "account_hint": "a***@example.com"}
        assert got[-1] == {"v": 1, "t": "inbox.state", "pending": 0, "answered": 0}
    assert e.gw.claim_state(c["pid"], "acc_1") == {"state": "paired"}
    info = e.gw.device_info(DEV)
    assert info["account_id"] == "acc_1" and info["members"] == ["acc_1"] and info["revoked"] is False
    assert [x["device_id"] for x in e.gw.devices_of("acc_1")] == [DEV]


def test_pair_no_gets_a_fresh_code(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    with e.ws(d.token) as ws:
        send(ws, hello())
        p = recv_until(ws, "pairing")[-1]
        c = e.gw.claim("acc_1", "Ana", "ana@example.com", p["code"], "198.51.100.4")
        assert recv(ws)["t"] == "pair.confirm"
        send(ws, {"v": 1, "t": "pair.no", "pid": c["pid"]})
        p2 = recv(ws)
        assert p2["t"] == "pairing" and p2["code"] != p["code"]
    assert e.gw.claim_state(c["pid"], "acc_1")["state"] == "rejected" and e.store.owner(DEV) is None


def test_reconnect_resends_the_current_code(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    codes = []
    for _ in range(2):
        with e.ws(d.token) as ws:
            send(ws, hello())
            codes.append(recv_until(ws, "pairing")[-1]["code"])
    assert codes[0] == codes[1]


# ---------------------------------------------------------- pushes and acks --

def test_live_push_ack_and_delivery_states(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        got = recv_until(ws, "inbox.state")
        assert [m["t"] for m in got] == ["welcome", "replay.done", "inbox.state"]
        assert got[0]["state"] == "paired" and got[0]["owner"] == "Ana" and got[0]["brain"] == "cloud"
        assert got[0]["allowance"]["unit"] == "turns" and got[0]["allowance"]["renews"] == "2026-11-01"
        seq = e.gw.push(DEV, "reminder.create", {"when": "2026-10-04T09:00", "text": "call the bank"}, "it_7",
                        {"kind": "connector", "app": "claude"}, say="From Claude: call the bank")
        m = recv(ws)
        assert m == {"v": 1, "t": "push", "seq": seq, "action": "reminder.create",
                     "args": {"when": "2026-10-04T09:00", "text": "call the bank"}, "item_id": "it_7",
                     "origin": {"kind": "connector", "app": "claude"}, "say": "From Claude: call the bank"}
        assert e.gw.wait_delivery(DEV, seq, timeout=0.05) == "queued"
        send(ws, {"v": 1, "t": "ack", "seq": seq, "ok": True})
        assert e.gw.wait_delivery(DEV, seq, timeout=2.0) == "shown"
        seq2 = e.gw.push(DEV, "alarm.set", {"hhmm": "02:00", "days": [], "label": ""}, "it_8",
                         {"kind": "connector", "app": "chatgpt"}, needs_accept=True)
        assert recv(ws)["needs_accept"] is True
        send(ws, {"v": 1, "t": "ack", "seq": seq2, "ok": True})
        assert e.gw.wait_delivery(DEV, seq2, timeout=2.0) == "pending_accept"
        seq3 = note_push(e, 3)
        recv(ws)
        send(ws, {"v": 1, "t": "ack", "seq": seq3, "ok": False, "err": "paused"})
        assert e.gw.wait_delivery(DEV, seq3, timeout=2.0) == "queued"


def test_push_and_wait_wakes_on_the_ack(tmp_path):
    import asyncio

    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        seq = note_push(e)
        out = {}
        t = threading.Thread(target=lambda: out.update(r=asyncio.run(e.gw.push_and_wait(DEV, seq, timeout=3.0))))
        t0 = time.monotonic()
        t.start()
        assert recv(ws)["seq"] == seq
        send(ws, {"v": 1, "t": "ack", "seq": seq, "ok": True})
        t.join(5)
        assert out["r"] == "shown" and time.monotonic() - t0 < 2.5


def test_push_needs_a_paired_device_and_a_known_action(tmp_path):
    e = Env(tmp_path)
    with pytest.raises(ValueError):
        note_push(e)
    e.paired_device()
    with pytest.raises(ValueError):
        e.gw.push(DEV, "factory.reset", {}, "it_x", {"kind": "connector"})
    with pytest.raises(ValueError):
        e.gw.push(DEV, "note.create", {"text": "x", "tags": []}, "it_x", {"kind": "llm"})


def test_offline_pushes_replay_in_pages_after_hello(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    for i in range(60):
        note_push(e, i)
    with e.ws(d.token) as ws:
        send(ws, hello(after=0))
        got = recv_until(ws, "replay.done")
        pushes = [m for m in got if m["t"] == "push"]
        assert [m["seq"] for m in pushes] == list(range(1, 61)) and got[-1]["last"] == 60
        for m in pushes:  # the device acks every push of the burst (not rate limited into 4429)
            send(ws, {"v": 1, "t": "ack", "seq": m["seq"], "ok": True})
        assert recv(ws)["t"] == "inbox.state"
        deadline = time.time() + 2
        while e.store.replay(DEV, 0)[0] and time.time() < deadline:
            time.sleep(0.02)
    assert e.store.replay(DEV, 0) == ([], False)


def test_hello_after_acks_older_pushes_and_resync_when_ahead(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    for i in range(3):
        note_push(e, i)
    with e.ws(d.token) as ws:
        send(ws, hello(after=2))
        got = recv_until(ws, "replay.done")
        assert [m["seq"] for m in got if m["t"] == "push"] == [3]
    assert e.gw.wait_delivery(DEV, 1, timeout=0) == "shown"
    with e.ws(d.token) as ws:
        send(ws, hello(after=99))
        got = recv_until(ws, "replay.done")
        assert {"v": 1, "t": "resync", "last": 3} in got


def test_a_second_socket_replaces_the_first_with_4409(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws1:
        send(ws1, hello())
        recv_until(ws1, "inbox.state")
        with e.ws(d.token) as ws2:
            send(ws2, hello())
            recv_until(ws2, "inbox.state")
            assert close_code(ws1) == 4409
            seq = note_push(e)
            assert recv(ws2)["seq"] == seq


def test_frame_flood_closes_4429_after_an_error(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        for _ in range(12):
            send(ws, {"v": 1, "t": "status", "rssi": -50, "power": "usb", "fw": "0.4.0", "free_heap": 1,
                      "awake": True})
        err = recv(ws)
        assert err["t"] == "error" and err["code"] == "rate_limited" and err["retry_ms"] >= 30000
        assert close_code(ws) == 4429


def test_big_frames_and_must_ignore(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello(future_field={"x": 1}))
        recv_until(ws, "inbox.state")
        send(ws, {"v": 1, "t": "teleport", "to": "mars"})           # unknown type: ignored
        send(ws, {"v": 1, "t": "note", "text": "x" * 5000})          # over 4 KB
        assert recv(ws)["code"] == "too_big"
        send(ws, {"v": 2, "t": "status", "id": "s1"})
        assert recv(ws) == {"v": 1, "t": "error", "code": "invalid", "msg": "unsupported envelope version",
                            "re": "s1"}


def test_unpair_sends_unpaired_and_closes_4403(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        e.gw.unpair(DEV, "user")
        assert recv(ws) == {"v": 1, "t": "unpaired", "reason": "user"}
        assert close_code(ws) == 4403
    assert e.client.get("/v1/device/poll", headers={"authorization": f"Bearer {d.token}"}).status_code == 401


# ------------------------------------------------------------- device items --

def test_item_add_is_stored_deduped_and_not_echoed(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        msg = {"v": 1, "t": "item.add", "cid": "00112233aabbccdd", "action": "note.create",
               "args": {"text": "buy milk", "tags": []}, "created": "2026-10-03T10:00"}
        send(ws, msg)
        a = recv(ws)
        assert a["t"] == "added" and a["cid"] == "00112233aabbccdd" and a["item_id"].startswith("it_")
        send(ws, msg)
        assert recv(ws) == a
        send(ws, {**msg, "cid": "nothex"})
        assert recv(ws)["code"] == "invalid"
        send(ws, {"v": 1, "t": "item.state", "cid": "00112233aabbccdd", "state": "done", "at": 1790000000})
        send(ws, {"v": 1, "t": "inbox.add", "cid": "ffeeddccbbaa0099", "text": "what is a good book?", "to": "claude"})
        assert recv(ws)["t"] == "added"
        assert recv(ws) == {"v": 1, "t": "inbox.state", "pending": 1, "answered": 0}
    assert e.store.last_seq(DEV) == 0  # nothing echoed back to the device
    assert e.gw.item_state(DEV, a["item_id"]) == "done"
    notes = e.soul.state.items(DEV, kind="note", include_done=True)
    assert [n["text"] for n in notes] == ["buy milk"] and notes[0]["source"] == "device"
    assert notes[0]["done"] is True  # item.state done reached the item store
    inbox = e.gw.inbox(DEV)
    assert inbox[0]["text"] == "what is a good book?" and inbox[0]["to"] == "claude"
    assert e.gw.inbox_answered(DEV, inbox[0]["item_id"]) and e.gw.inbox(DEV) == []


def test_item_add_needs_pairing(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "pairing")
        send(ws, {"v": 1, "t": "item.add", "cid": "00112233aabbccdd", "action": "note.create",
                  "args": {"text": "x", "tags": []}})
        m = recv(ws)
        assert m["code"] == "unpaired" and m["cid"] == "00112233aabbccdd"


def test_status_sleep_connectors_and_forecast(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    paused = []
    e.gw.on_connectors.append(lambda dev, p: paused.append(p))
    with e.ws(d.token) as ws:
        send(ws, hello(power="battery"))
        recv_until(ws, "inbox.state")
        send(ws, {"v": 1, "t": "status", "rssi": -61, "battery": 80, "power": "battery", "fw": "0.4.1",
                  "free_heap": 123456, "awake": True})
        send(ws, {"v": 1, "t": "connectors", "paused": True})
        send(ws, {"v": 1, "t": "event", "events": [{"kind": "boop", "at": 1790000000}, {"kind": "hack", "at": 1}]})
        assert e.gw.forecast(DEV, "2026-10-03T12:00") == "yes"  # online
        wake = int(e.clock()) + 900
        send(ws, {"v": 1, "t": "sleep", "wake_at": wake})
        time.sleep(0.2)
    dev = e.store.get_device(DEV)
    assert dev["battery"] == 80 and dev["rssi"] == -61 and dev["fw"] == "0.4.1" and dev["connectors_paused"] == 1
    assert dev["wake_at"] == wake and paused == [True]
    assert e.store.db.execute("SELECT COUNT(*) n FROM events").fetchone()["n"] == 1
    e.clock.advance(120)  # past the poll window: not "online" any more
    assert e.gw.forecast(DEV, "2026-10-03T12:00") == "yes"   # wakes at +15 min, due in ~2 h
    assert e.gw.forecast(DEV, "2026-10-03T10:05") == "no"    # due before the next wake
    assert e.gw.forecast(DEV, "garbage") == "unknown"
    e.clock.advance(2 * 86400)
    assert e.gw.forecast(DEV, "2026-10-09T12:00") == "no"    # silent for days
    assert e.gw.forecast(DEV2, "2026-10-09T12:00") == "no"   # unknown device


def test_config_is_persisted_and_sent(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        e.gw.send_config(DEV, brain="claude", tz="Europe/London", quiet={"from": "23:00", "to": "06:30"})
        m = recv(ws)
        assert m == {"v": 1, "t": "config", "brain": "claude", "tz": "Europe/London",
                     "posix_tz": "GMT0BST,M3.5.0/1,M10.5.0", "quiet": {"from": "23:00", "to": "06:30"}}
    assert e.store.get_device(DEV)["brain"] == "claude"
    with pytest.raises(ValueError):
        e.gw.send_config(DEV, brain="skynet")


# ------------------------------------------------------------------ long-poll --

def auth_hdr(d):
    return {"authorization": f"Bearer {d.token}"}


def test_long_poll_parity_hello_pairing_pushes_paging_and_acks(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    r = e.client.post("/v1/device/send", json={"messages": [hello()]}, headers=auth_hdr(d))
    msgs = r.json()["messages"]
    assert [m["t"] for m in msgs] == ["welcome", "pairing"]
    assert e.client.get("/v1/device/poll?after=0&wait=0", headers=auth_hdr(d)).json() == {"messages": [],
                                                                                           "more": False}
    c = e.gw.claim("acc_1", "Ana", "ana@example.com", msgs[1]["code"], "198.51.100.4")
    got = e.client.get("/v1/device/poll?after=0&wait=0", headers=auth_hdr(d)).json()["messages"]
    assert got[0]["t"] == "pair.confirm"
    r = e.client.post("/v1/device/send", json={"messages": [{"v": 1, "t": "pair.ok", "pid": c["pid"]}]},
                      headers=auth_hdr(d))
    assert r.json()["messages"][0]["t"] == "paired"
    for i in range(55):
        note_push(e, i)
    p1 = e.client.get("/v1/device/poll?after=0&wait=0", headers=auth_hdr(d)).json()
    assert len(p1["messages"]) == 50 and p1["more"] is True
    p2 = e.client.get("/v1/device/poll?after=50&wait=0", headers=auth_hdr(d)).json()
    assert [m["seq"] for m in p2["messages"]] == list(range(51, 56)) and p2["more"] is False
    acks = [{"v": 1, "t": "ack", "seq": s, "ok": True} for s in range(1, 22)]
    assert e.client.post("/v1/device/send", json={"messages": acks}, headers=auth_hdr(d)).status_code == 400
    e.client.post("/v1/device/send", json={"messages": acks[:20]}, headers=auth_hdr(d))
    p3 = e.client.get("/v1/device/poll?after=0&wait=0", headers=auth_hdr(d)).json()
    assert p3["messages"][0]["seq"] == 21
    p4 = e.client.get("/v1/device/poll?after=500&wait=0", headers=auth_hdr(d)).json()
    assert p4["messages"][0] == {"v": 1, "t": "resync", "last": 55}


def test_long_poll_wait_wakes_on_a_push(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    threading.Timer(0.3, lambda: note_push(e, 1)).start()
    t0 = time.monotonic()
    got = e.client.get("/v1/device/poll?after=0&wait=5", headers=auth_hdr(d)).json()
    assert got["messages"][0]["t"] == "push" and time.monotonic() - t0 < 4
    assert e.gw.is_online(DEV)


def test_http_errors_have_the_documented_shape(tmp_path):
    e = Env(tmp_path)
    r = e.client.post("/v1/device/challenge", json={"device_id": "nope"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"
    for _ in range(20):
        e.client.post("/v1/device/challenge", json={"device_id": DEV})
    r = e.client.post("/v1/device/challenge", json={"device_id": DEV})
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and r.json()["error"]["retry_ms"] > 0
    assert e.client.get("/v1/device/poll").status_code == 401
    d = e.device(DEV2)
    d.authenticate()
    big = {"messages": [{"v": 1, "t": "status", "x": "y" * 17000}]}
    r = e.client.post("/v1/device/send", content=json.dumps(big), headers=auth_hdr(d))
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_big"
    r = e.client.post("/v1/device/auth", content=b"{not json")
    assert r.status_code == 400


def test_dev_routes_are_disabled_in_production(tmp_path, monkeypatch):
    e = Env(tmp_path)
    monkeypatch.setenv("SOUL_ENV", "production")
    r = e.client.post("/v1/dev/push", json={"device_id": DEV})
    assert r.status_code == 404


def test_production_refuses_pending_enrolment(tmp_path, monkeypatch):
    e = Env(tmp_path)
    monkeypatch.setenv("SOUL_ENV", "production")
    monkeypatch.setenv("SOUL_PUBLIC_HOST", "soul.example")
    with pytest.raises(RuntimeError):
        gateway_mod.Gateway(e.soul, e.store, e.relay)
