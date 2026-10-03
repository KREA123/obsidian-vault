"""Regression tests for the security / correctness review of the device gateway, relay and connector.

Each test names the reviewed issue it pins down (docs/07-CONNECT-AI.md section in brackets).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import threading
import time
from zoneinfo import ZoneInfo

import pytest
from starlette.websockets import WebSocketDisconnect

import suflet_ai.gateway as gateway_mod
from _gateway_kit import (DEV, HOST, DeviceKey, Env, FakeAnthropic, a_resp, a_text, a_tool, auth_message, block,
                          hello, recv, recv_until, send)
from suflet_ai.devices import GatewayError

IP = "203.0.113.7"
ATTACKER_IP = "198.51.100.66"
LONDON = "Europe/London"


def signed(store, key, device_id=DEV, ip=IP):
    nonce = store.issue_nonce(device_id, ip)["nonce"]
    return {"device_id": device_id, "pub": key.pub, "nonce": nonce,
            "sig": key.sign(auth_message(HOST, device_id, nonce)), "fw": "0.4.0", "hw": "lcd28"}


def gw_err(fn, *a, **kw) -> GatewayError:
    with pytest.raises(GatewayError) as e:
        fn(*a, **kw)
    return e.value


def close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as ei:
        for _ in range(500):
            ws.receive_text()
    return ei.value.code


def victim_push(e, text="PIN bancar 4711", **kw):
    return e.gw.push(DEV, "note.create", {"text": text, "tags": []}, "it_v1", {"kind": "connector", "app": "claude"},
                     **kw)


# ============================================ pending enrolment on a paired SOUL [§3.2] ==

def test_a_second_key_cannot_enrol_on_a_paired_soul_under_pending(tmp_path):
    e = Env(tmp_path, policy="pending")
    e.paired_device(account="acc_victim")
    victim_push(e)
    attacker = DeviceKey.generate()
    ex = gw_err(e.store.authenticate, signed(e.store, attacker, ip=ATTACKER_IP), ATTACKER_IP)
    assert (ex.status, ex.code) == (403, "not_enrolled")
    n = e.store.db.execute("SELECT COUNT(*) n FROM device_keys WHERE device_id=? AND state='pending'",
                           (DEV,)).fetchone()["n"]
    assert n == 0
    # the victim's push is untouched
    assert e.store.push_status(DEV, 1)["acked"] is False


def test_a_pending_token_from_before_pairing_gets_nothing_after_it(tmp_path):
    """A stranger enrolled while SOUL was still unpaired; the owner then pairs with the real key."""
    e = Env(tmp_path, policy="pending")
    stranger = e.device()
    stranger.authenticate()
    assert stranger.auth_info["state"] == "pending"
    # the stranger's key row and token survive in this scenario only if pairing did not clean them up:
    # put them back to model a race (two instances, a restore, ...) and check the gateway refuses anyway
    row = e.store.db.execute("SELECT * FROM device_keys WHERE device_id=?", (DEV,)).fetchone()
    tok = e.store.db.execute("SELECT * FROM device_tokens WHERE device_id=?", (DEV,)).fetchone()
    e.paired_device(account="acc_victim")
    e.store.db.execute("INSERT OR REPLACE INTO device_keys(device_id, pub, pub_hash, state, created) "
                       "VALUES (?,?,?,?,?)", (DEV, row["pub"], row["pub_hash"], "pending", row["created"]))
    e.store.db.execute("INSERT OR REPLACE INTO device_tokens(hash, device_id, pub_hash, expires) VALUES (?,?,?,?)",
                       tuple(tok))
    e.store.db.commit()
    victim_push(e, private=True)
    # token check: no WebSocket (so no 4409 kick of the real SOUL), no poll, no send
    assert gw_err(e.store.device_from_token, stranger.token).code == "unauthenticated"
    with e.ws(stranger.token) as ws:
        assert close_code(ws) == 4401
    r = e.client.get("/v1/device/poll?after=0", headers={"authorization": f"Bearer {stranger.token}"})
    assert r.status_code == 401 and "PIN" not in r.text
    r = e.client.post("/v1/device/send", headers={"authorization": f"Bearer {stranger.token}"},
                      json={"messages": [{"v": 1, "t": "ack", "seq": 1, "ok": True},
                                         {"v": 1, "t": "ask", "id": "x", "text": "set alarm 3:00"}]})
    assert r.status_code == 401
    assert e.store.push_status(DEV, 1)["acked"] is False
    assert e.soul.state.items(DEV, kind="alarm") == []


def test_an_open_socket_of_another_key_is_closed_when_soul_pairs(tmp_path):
    e = Env(tmp_path, policy="pending")
    stranger, owner = e.device(), e.device()
    stranger.authenticate()
    owner.authenticate()
    owner_ctx = e.store.device_from_token(owner.token)
    with e.ws(stranger.token) as ws:
        send(ws, hello())
        p = recv_until(ws, "pairing")[-1]
        c = e.gw.claim("acc_victim", "Ana", "ana@example.com", p["code"], IP)
        # the owner's key confirms over long-poll / send
        r = asyncio.run(e.gw.send(owner_ctx, [{"v": 1, "t": "pair.ok", "pid": c["pid"]}], IP))
        assert r["messages"][0]["t"] == "paired"
        victim_push(e)
        frames = []
        with pytest.raises(WebSocketDisconnect) as ei:
            for _ in range(50):
                frames.append(recv(ws))
        assert ei.value.code == 4401
        assert all(f.get("t") != "push" for f in frames)


# ============================================== remote lockout via public device_id [§3.2] ==

def test_junk_auth_and_challenges_from_elsewhere_cannot_lock_the_real_soul_out(tmp_path):
    e = Env(tmp_path, policy="factory")
    real = DeviceKey.generate()
    e.store.import_factory([(DEV, real.pub)])
    junk = {"device_id": DEV, "pub": DeviceKey.generate().pub, "nonce": "x", "sig": "A" * 86}
    for _ in range(30):
        with pytest.raises(GatewayError) as ei:
            e.store.authenticate(dict(junk), ATTACKER_IP)
        assert ei.value.code in ("bad_nonce", "rate_limited")
    for _ in range(40):
        try:
            e.store.issue_nonce(DEV, ATTACKER_IP)
        except GatewayError as ex:
            assert ex.code == "rate_limited"
    res = e.store.authenticate(signed(e.store, real), IP)
    assert res["state"] == "unpaired" and res["token"].startswith("sdt_")


def test_a_valid_key_is_still_limited_per_key(tmp_path):
    e = Env(tmp_path, policy="factory")
    real = DeviceKey.generate()
    e.store.import_factory([(DEV, real.pub)])
    for _ in range(10):
        e.store.authenticate(signed(e.store, real), IP)
    assert gw_err(e.store.authenticate, signed(e.store, real), IP).code == "rate_limited"


# ======================================================= device time zone [§6.0, §6.8] ==

def test_offline_turn_uses_the_device_zone(tmp_path):
    e = Env(tmp_path)  # clock: 10:00 Bucharest = 08:00 London
    e.paired_device()
    e.store.update_device(DEV, tz=LONDON, brain="none")
    r = e.relay.answer(DEV, "paired", {"v": 1, "t": "ask", "id": "a1", "text": "remind me in 60 minutes to stretch",
                                       "lang": "en"})
    push = e.store.replay(DEV, 0)[0][0]
    assert push["action"] == "reminder.create" and push["args"]["when"] == "2026-10-03T09:00", r


def test_brain_a_prompt_has_the_device_local_time(tmp_path):
    ant = FakeAnthropic([a_text("Hi")])
    e = Env(tmp_path, anthropic=ant)
    e.paired_device()
    e.store.update_device(DEV, tz=LONDON)
    e.relay.answer(DEV, "paired", {"v": 1, "t": "ask", "id": "a1", "text": "hi", "lang": "en"})
    user = ant.calls[0]["messages"][-1]["content"]
    assert "2026-10-03 08:00" in user and "10:00" not in user


def test_item_add_reminder_is_checked_in_the_device_zone(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    e.store.update_device(DEV, tz=LONDON)
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        send(ws, {"v": 1, "t": "item.add", "cid": "00112233aabbccdd", "action": "reminder.create",
                  "args": {"when": "2026-10-03T09:30", "text": "tea"}})
        m = recv(ws)
        assert m["t"] == "added", m
    it = e.soul.state.items(DEV, kind="reminder")[0]
    assert it["due"] == "2026-10-03T09:30"
    assert [x["id"] for x in e.soul.today(DEV, "2026-10-03")] == [it["id"]]


def test_connector_reminder_is_stored_in_the_device_zone(tmp_path):
    from test_connector_tools import call, ok, setup

    server, svc, gw, ctx, clock = setup(tmp_path)  # 14:30 Bucharest = 12:30 London
    gw.devices[DEV]["tz"] = LONDON
    r = ok(call(server, ("add_reminder", {"text": "call mum", "in_minutes": 60}))[0])
    assert r["resolved"]["when_local"] == "2026-10-02T13:30" and r["tz"] == LONDON
    assert gw.pushes[-1]["args"]["when"] == "2026-10-02T13:30"
    assert svc.state.items(DEV, kind="reminder")[0]["due"] == "2026-10-02T13:30"
    today = ok(call(server, ("list_today", {}))[0])
    assert [i["due"] for i in today["items"] if i["kind"] == "reminder"] == ["2026-10-02T13:30"]


# =========================================================== ask timeout [§6.6] ==

class _SlowAnthropic(FakeAnthropic):
    def __init__(self, outputs, delay_on_call: int, delay: float):
        super().__init__(outputs)
        self.n, self.delay_on_call, self.delay = 0, delay_on_call, delay

    def _create(self, log, **kw):
        self.n += 1
        if self.n == self.delay_on_call:
            time.sleep(self.delay)
        return super()._create(log, **kw)


def test_actions_of_a_timed_out_turn_are_pushed_without_a_reconnect(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway_mod, "ASK_TIMEOUT", 0.5)
    monkeypatch.setattr(gateway_mod, "RELAY_BUDGET", 10.0)  # let the turn outlive the device's wait
    ant = _SlowAnthropic([a_resp("tool_use", a_tool("t1", "note_create", text="late note", tags=[])),
                          a_text("Noted.")], delay_on_call=2, delay=1.0)
    e = Env(tmp_path, anthropic=ant)
    d = e.paired_device()
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        send(ws, {"v": 1, "t": "ask", "id": "q1", "text": "note late note", "lang": "en"})
        m = recv(ws)
        assert m["t"] == "error" and m["code"] == "timeout" and m["re"] == "q1"
        p = recv(ws)  # arrives on its own once the turn ends
        assert p["t"] == "push" and p["args"]["text"] == "late note"


def test_the_relay_stops_calling_the_model_at_its_deadline(tmp_path):
    ant = FakeAnthropic([a_resp("tool_use", a_tool("t1", "note_create", text="x", tags=[])), a_text("never")])
    e = Env(tmp_path, anthropic=ant)
    e.paired_device()
    t0 = time.monotonic()
    res = e.relay.answer(DEV, "paired", {"v": 1, "t": "ask", "id": "a1", "text": "note x", "lang": "en"},
                         deadline=time.monotonic() + 0.5)
    # no time for even one round: answered offline, with the provider timeout code
    assert time.monotonic() - t0 < 1 and ant.calls == []
    assert res["reply"]["note"] == "timeout"


def test_each_model_request_gets_a_timeout_inside_the_deadline(tmp_path):
    ant = FakeAnthropic([a_text("Hi")])
    e = Env(tmp_path, anthropic=ant)
    e.paired_device()
    e.relay.answer(DEV, "paired", {"v": 1, "t": "ask", "id": "a1", "text": "hi", "lang": "en"},
                   deadline=time.monotonic() + 8)
    assert 2 <= ant.calls[0]["timeout"] <= 8


# ===================================================== thread pool / push_and_wait ==

def test_push_and_wait_parks_no_thread(tmp_path, monkeypatch):
    e = Env(tmp_path)
    d = e.paired_device()

    def no_threads(*a, **kw):
        raise AssertionError("push_and_wait must not use a worker thread")

    monkeypatch.setattr(asyncio, "to_thread", no_threads)
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "inbox.state")
        seq = victim_push(e)
        out = {}
        t = threading.Thread(target=lambda: out.update(r=asyncio.run(e.gw.push_and_wait(DEV, seq, timeout=3.0))))
        t.start()
        assert recv(ws)["seq"] == seq
        send(ws, {"v": 1, "t": "ack", "seq": seq, "ok": True})
        t.join(5)
    assert out["r"] == "shown"


def test_relay_turns_run_on_their_own_pool(tmp_path):
    e = Env(tmp_path)
    assert e.gw._relay_pool._max_workers >= 4  # noqa: SLF001


# ===================================================== rejected pushes [§3.8] ==

def test_a_rejected_push_is_reported_as_rejected(tmp_path):
    e = Env(tmp_path)
    e.paired_device()
    seq = e.gw.push(DEV, "alarm.set", {"hhmm": "07:00", "days": [], "label": ""}, "it_a",
                    {"kind": "connector", "app": "claude"})
    e.store.ack(DEV, seq, ok=False, err="full")
    assert e.gw.wait_delivery(DEV, seq, timeout=0) == "rejected:full"
    assert asyncio.run(e.gw.push_and_wait(DEV, seq, timeout=0.1)) == "rejected:full"


@pytest.mark.parametrize("why,code", [("full", "limit_alarms"), ("paused", "connectors_paused"),
                                      ("unsupported", "invalid")])
def test_connector_tells_the_truth_when_soul_refuses_an_item(tmp_path, why, code):
    from test_connector_tools import call, err, setup

    server, svc, gw, ctx, clock = setup(tmp_path, delivery=f"rejected:{why}")
    text = err(call(server, ("set_alarm", {"time": "07:30"}))[0])
    assert text.startswith(code + ":")
    assert "reconnect" not in text


def test_connector_note_full_is_not_called_queued(tmp_path):
    from test_connector_tools import call, err, setup

    server, *_ = setup(tmp_path, delivery="rejected:full")
    assert err(call(server, ("add_note", {"text": "x"}))[0]).startswith("soul_full:")


# ===================================================== no new code during pair.confirm [§6.3] ==

def test_no_pairing_code_follows_pair_confirm_over_ws(tmp_path, monkeypatch):
    monkeypatch.setattr(gateway_mod, "TICK", 0.2)
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    with e.ws(d.token) as ws:
        send(ws, hello())
        p = recv_until(ws, "pairing")[-1]
        c = e.gw.claim("acc_1", "Ana", "ana@example.com", p["code"], IP)
        assert recv(ws)["t"] == "pair.confirm"
        time.sleep(0.7)  # several idle ticks
        send(ws, {"v": 1, "t": "status", "rssi": -60})
        send(ws, {"v": 1, "t": "pair.ok", "pid": c["pid"]})
        got = recv_until(ws, "inbox.state")
        assert [m["t"] for m in got] == ["paired", "inbox.state"]


def test_no_pairing_code_follows_pair_confirm_over_long_poll(tmp_path):
    e = Env(tmp_path)
    d = e.device()
    d.authenticate()
    ctx = e.store.device_from_token(d.token)
    first = asyncio.run(e.gw.poll(ctx, 0, 0))["messages"]
    code = [m for m in first if m["t"] == "pairing"][0]["code"]
    e.gw.claim("acc_1", "Ana", "ana@example.com", code, IP)
    batch = asyncio.run(e.gw.poll(ctx, 0, 0))["messages"]
    assert [m["t"] for m in batch] == ["pair.confirm"]
    assert asyncio.run(e.gw.poll(ctx, 0, 0))["messages"] == []
    # a reboot (hello) gets the same pair.confirm again, never a code
    r = asyncio.run(e.gw.send(ctx, [hello()], IP))["messages"]
    assert [m["t"] for m in r if m["t"] in ("pairing", "pair.confirm")] == ["pair.confirm"]
    # after the claim expires, a fresh code comes
    e.clock.advance(121)
    later = asyncio.run(e.gw.poll(ctx, 0, 0))["messages"]
    assert [m["t"] for m in later] == ["pairing"] and later[0]["code"] != code


# ===================================================== refusal after a tool round [§4.3] ==

def test_refusal_after_a_tool_round_undoes_the_stored_action(tmp_path):
    ant = FakeAnthropic([a_resp("tool_use", a_tool("t1", "alarm_set", hhmm="07:30", days=[], label="")),
                         a_resp("refusal", block("text", text=""))])
    e = Env(tmp_path, anthropic=ant)
    e.paired_device()
    res = e.relay.answer(DEV, "paired", {"v": 1, "t": "ask", "id": "a1", "text": "alarm 7:30", "lang": "en"})
    assert res["error"]["code"] == "refused" and res["seqs"] == []
    assert e.soul.state.items(DEV, kind="alarm") == []
    assert e.store.replay(DEV, 0) == ([], False)


# ===================================================== too_big echoes cid over long-poll [§6.4] ==

def test_too_big_over_send_echoes_cid_and_id(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    ctx = e.store.device_from_token(d.token)
    big = {"v": 1, "t": "item.add", "id": "n9", "cid": "0011223344556677", "action": "note.create",
           "args": {"text": "😀" * 2600, "tags": []}}
    ok_note = {"v": 1, "t": "item.add", "id": "n8", "cid": "0011223344556678", "action": "note.create",
               "args": {"text": "ă" * 2000, "tags": []}}
    out = asyncio.run(e.gw.send(ctx, [big, ok_note], IP))["messages"]
    assert out[0]["code"] == "too_big" and out[0]["cid"] == big["cid"] and out[0]["re"] == "n9"
    assert out[1]["t"] == "added"
    assert len(json.dumps(ok_note, ensure_ascii=False).encode()) > 4096


# ===================================================== B2 key hygiene [§4.1] ==

@pytest.mark.parametrize("provider,key", [
    ("anthropic", "sk-ant-admin01-" + "x" * 40),
    ("anthropic", "sk-ant-oat01-" + "x" * 40),
    ("openai", "sk-admin-" + "x" * 40),
])
def test_keystore_refuses_admin_and_subscription_tokens(tmp_path, provider, key):
    e = Env(tmp_path)
    with pytest.raises(ValueError):
        e.soul.keys.set("acc_1", provider, key)


def test_keystore_still_takes_api_keys(tmp_path):
    e = Env(tmp_path)
    e.soul.keys.set("acc_1", "anthropic", "sk-ant-api03-" + "x" * 40)
    assert e.soul.keys.get("acc_1", "anthropic").startswith("sk-ant-api03-")


def test_device_now_falls_back_on_a_bad_zone(tmp_path):
    from suflet_ai.relay import Relay

    e = Env(tmp_path)
    n = Relay.device_now(e.soul, {"tz": "Not/AZone"})
    assert n.utcoffset() == dt.datetime(2026, 10, 3, tzinfo=ZoneInfo("Europe/Bucharest")).utcoffset()
