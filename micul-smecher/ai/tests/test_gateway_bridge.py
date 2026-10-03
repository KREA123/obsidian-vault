"""SOUL Bridge through SOUL Cloud (/v1/bridge, docs/08 §4): pairing by a code shown on SOUL, bridge tokens,
turns of brain `bridge` relayed to the owner's computer and back, offline / timeout / revoke / long-poll."""
import json

import pytest
from starlette.websockets import WebSocketDisconnect

from _gateway_kit import DEV, DEV2, Env, hello, recv, recv_until, send


def bridge_ws(e):
    return e.client.websocket_connect("/v1/bridge")


def close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as ei:
        for _ in range(200):
            ws.receive_text()
    return ei.value.code


class device_socket:
    """The device's socket, said hello and replayed; closed on exit even when an assertion fails."""

    def __init__(self, e, d):
        self.cm = e.ws(d.token)

    def __enter__(self):
        ws = self.cm.__enter__()
        send(ws, hello())
        recv_until(ws, "replay.done")
        return ws

    def __exit__(self, *a):
        return self.cm.__exit__(*a)


def state_until(ws, online: bool) -> dict:
    for _ in range(20):
        m = recv_until(ws, "bridge.state")[-1]
        if m["online"] is online:
            return m
    raise AssertionError("no bridge.state with online=%s" % online)


def get_code(ws) -> dict:
    send(ws, {"v": 1, "t": "bridge.code.get"})
    return recv_until(ws, "bridge.code")[-1]


def pair_bridge(e, code: str) -> dict:
    with bridge_ws(e) as b:
        send(b, {"t": "bridge.pair", "v": 1, "code": code, "bridge": "soul-bridge/0.2.0", "label": "Ana's Mac"})
        m = recv(b)
    return m


def test_pair_with_the_code_on_soul_then_a_turn_goes_to_the_computer_and_back(tmp_path):
    e = Env(tmp_path)
    with e.client:
        d = e.paired_device()
        with device_socket(e, d) as ws:
            c = get_code(ws)
            assert len(c["code"]) == 8 and c["expires_in"] == 300
            assert c["cmd"] == f"soul-bridge pair {c['code'][:4]}-{c['code'][4:]} --cloud soul.example"
            st = recv_until(ws, "bridge.state")[-1]
            assert (st["paired"], st["online"]) == (False, False)

            paired = pair_bridge(e, c["code"][:4] + "-" + c["code"][4:].lower())  # dash and case do not matter
            assert paired["t"] == "bridge.paired" and paired["device_id"] == DEV and paired["token"].startswith("sbt_")
            assert pair_bridge(e, c["code"])["t"] == "bridge.denied"  # single use
            assert e.gw.bridges.tokens("acc_1")[0]["label"] == "Ana's Mac"
            # the token is stored hashed only
            rows = e.store.db.execute("SELECT * FROM bridge_tokens").fetchall()
            assert all(paired["token"] not in json.dumps(dict(r)) for r in rows)

            send(ws, {"v": 1, "t": "brain", "brain": "bridge"})
            recv_until(ws, "bridge.state")
            assert e.store.get_device(DEV)["brain"] == "bridge"
            with bridge_ws(e) as b:
                send(b, {"t": "bridge.hello", "v": 1, "token": paired["token"], "bridge": "soul-bridge/0.2.0",
                         "mode": "channel"})
                w = recv(b)
                assert w["t"] == "bridge.welcome" and w["device_id"] == DEV and w["tz"] == "Europe/Bucharest"
                st = state_until(ws, True)
                assert (st["paired"], st["online"], st["name"]) == (True, True, "Ana's Mac")

                send(ws, {"v": 1, "t": "ask", "id": "a1", "text": "Trezește-mă mâine la 7", "lang": "ro", "conv": None,
                          "ctx": {"timer_left_min": None, "unsynced": []}})
                assert recv_until(ws, "ask.state")[-1] == {"v": 1, "t": "ask.state", "re": "a1", "state": "waiting"}
                q = recv(b)
                assert q["t"] == "ask" and q["id"] == "a1" and q["text"] == "Trezește-mă mâine la 7"
                assert q["lang"] == "ro" and q["tz"] == "Europe/Bucharest" and q["now"] == "2026-10-03T10:00"
                send(b, {"t": "ask.ack", "id": "a1", "state": "thinking"})
                assert recv_until(ws, "ask.state")[-1]["state"] == "thinking"
                send(b, {"t": "answer", "id": "a1", "text": "Gata, te trezesc la 07:00.",
                         "actions": [{"type": "alarm.set", "args": {"hhmm": "07:00", "days": [], "label": ""}}]})
                assert recv(b) == {"t": "answer.ack", "id": "a1", "shown": True}
                got = recv_until(ws, "reply")
                push = next(m for m in got if m["t"] == "push")
                assert push["action"] == "alarm.set" and push["args"]["hhmm"] == "07:00"
                assert push["origin"]["kind"] == "turn"
                r = got[-1]
                assert r["re"] == "a1" and r["say"] == "Gata, te trezesc la 07:00." and r["brain"] == "bridge"
                assert r["provider"] == "claude" and r["seqs"] == [push["seq"]] and r["face"] == "happy"
                send(ws, {"v": 1, "t": "ack", "seq": push["seq"], "ok": True})

                # an answer with an invalid action still shows; the action is dropped and noted
                send(ws, {"v": 1, "t": "ask", "id": "a2", "text": "x", "lang": "ro", "conv": None})
                recv(b)
                send(b, {"t": "answer", "id": "a2", "text": "Hm.", "actions": [{"type": "alarm.set",
                                                                              "args": {"hhmm": "25:99"}}]})
                r2 = recv_until(ws, "reply")[-1]
                assert r2["seqs"] == [] and r2["note"] == "invalid"
                # an answer for an unknown question is ignored
                send(b, {"t": "answer", "id": "nope", "text": "x", "actions": []})
            # the bridge went away: SOUL hears it, and the next turn fails over at once
            assert state_until(ws, False)["paired"] is True
            send(ws, {"v": 1, "t": "ask", "id": "a3", "text": "Ce faci?", "lang": "ro", "conv": None})
            got = recv_until(ws, "error")
            assert got[-1]["code"] == "bridge_offline" and got[-1]["re"] == "a3"


def test_bridge_tokens_are_checked_revoked_and_die_with_the_pairing(tmp_path):
    e = Env(tmp_path)
    with e.client:
        e.paired_device()
        tok = e.gw.bridges.pair(e.gw.bridges.pair_code(DEV)["code"], "pc", "198.51.100.1")
        with bridge_ws(e) as b:
            send(b, {"t": "bridge.hello", "v": 1, "token": "sbt_" + "x" * 43, "bridge": "t", "mode": "channel"})
            assert recv(b)["t"] == "bridge.denied"
            assert close_code(b) == 4401
        with bridge_ws(e) as b:  # a first frame that is neither pair nor hello
            send(b, {"t": "ask", "id": "x"})
            assert close_code(b) == 4400
        with bridge_ws(e) as b:
            send(b, {"t": "bridge.hello", "v": 1, "token": tok["token"], "bridge": "t", "mode": "channel"})
            assert recv(b)["t"] == "bridge.welcome"
            assert e.gw.bridges.online(DEV)
            assert e.gw.bridges.revoke("acc_1", tok["token_id"])
            assert close_code(b) == 4401
        assert e.gw.bridges.tokens("acc_1") == []
        # another account cannot revoke, a wrong id is refused
        tok2 = e.gw.bridges.pair(e.gw.bridges.pair_code(DEV)["code"], "pc2", "198.51.100.1")
        assert not e.gw.bridges.revoke("acc_other", tok2["token_id"])
        # unpairing the SOUL kills every bridge token
        e.gw.unpair(DEV, "user")
        assert e.gw.bridges.tokens("acc_1") == []
        with bridge_ws(e) as b:
            send(b, {"t": "bridge.hello", "v": 1, "token": tok2["token"], "bridge": "t", "mode": "channel"})
            assert recv(b)["t"] == "bridge.denied"


def test_codes_need_a_paired_soul_expire_and_are_rate_limited(tmp_path):
    e = Env(tmp_path)
    d = e.device(DEV2)
    d.authenticate()
    from suflet_ai.bridge_hub import BridgeError
    with pytest.raises(BridgeError):
        e.gw.bridges.pair_code(DEV2)  # not paired with an account
    e.paired_device()
    c = e.gw.bridges.pair_code(DEV)["code"]
    e.clock.advance(301)
    with pytest.raises(BridgeError) as ei:
        e.gw.bridges.pair(c, "pc", "198.51.100.7")
    assert ei.value.code == "wrong_code"
    from suflet_ai.devices import GatewayError
    with pytest.raises((BridgeError, GatewayError)):
        for _ in range(25):  # 20 per network per hour
            try:
                e.gw.bridges.pair("AAAAAAAA", "pc", "198.51.100.7")
            except BridgeError:
                pass


def test_timeout_cancel_and_claude_unavailable(tmp_path, monkeypatch):
    e = Env(tmp_path)
    e.gw.bridges.answer_timeout = 0.3
    with e.client:
        d = e.paired_device()
        e.store.update_device(DEV, brain="bridge")
        tok = e.gw.bridges.pair(e.gw.bridges.pair_code(DEV)["code"], "pc", "198.51.100.1")
        with device_socket(e, d) as ws:
            with bridge_ws(e) as b:
                send(b, {"t": "bridge.hello", "v": 1, "token": tok["token"], "bridge": "t", "mode": "channel"})
                recv(b)
                send(ws, {"v": 1, "t": "ask", "id": "t1", "text": "slow one", "lang": "en", "conv": None})
                assert recv(b)["t"] == "ask"
                assert recv(b) == {"t": "ask.cancel", "id": "t1"}  # 0.3 s later
                got = recv_until(ws, "error")
                assert got[-1]["code"] == "timeout" and got[-1]["re"] == "t1"
                # Claude Code not signed in -> the bridge says claude_unavailable -> SOUL hears bridge_offline
                send(ws, {"v": 1, "t": "ask", "id": "t2", "text": "hi", "lang": "en", "conv": None})
                recv(b)
                send(b, {"t": "answer.error", "id": "t2", "code": "claude_unavailable", "detail": "not signed in"})
                assert recv_until(ws, "error")[-1]["code"] == "bridge_offline"
                # SOUL gives up (its own timeout): the bridge is told to drop the question
                e.gw.bridges.answer_timeout = 30
                send(ws, {"v": 1, "t": "ask", "id": "t3", "text": "hi", "lang": "en", "conv": None})
                recv(b)
                send(ws, {"v": 1, "t": "abort", "re": "t3"})
                assert recv(b) == {"t": "ask.cancel", "id": "t3"}


def test_bridge_turn_over_long_poll_arrives_with_the_next_poll(tmp_path):
    e = Env(tmp_path)
    with e.client:
        d = e.paired_device()
        e.store.update_device(DEV, brain="bridge")
        tok = e.gw.bridges.pair(e.gw.bridges.pair_code(DEV)["code"], "pc", "198.51.100.1")
        h = {"authorization": f"Bearer {d.token}"}
        with bridge_ws(e) as b:
            send(b, {"t": "bridge.hello", "v": 1, "token": tok["token"], "bridge": "t", "mode": "print"})
            recv(b)
            r = e.client.post("/v1/device/send", headers=h, json={"messages": [
                {"v": 1, "t": "ask", "id": "p1", "text": "Pune un minutar de 5 minute", "lang": "ro", "conv": None}]})
            assert r.json()["messages"] == [{"v": 1, "t": "ask.state", "re": "p1", "state": "waiting"}]
            assert recv(b)["id"] == "p1"
            send(b, {"t": "answer", "id": "p1", "text": "Pornit.",
                     "actions": [{"type": "timer.start", "args": {"seconds": 300, "label": ""}}]})
            recv(b)  # answer.ack
            msgs = []
            for _ in range(20):
                msgs += e.client.get("/v1/device/poll?after=0&wait=1", headers=h).json()["messages"]
                if any(m["t"] == "reply" for m in msgs):
                    break
            assert any(m["t"] == "push" and m["action"] == "timer.start" for m in msgs)
            reply = next(m for m in msgs if m["t"] == "reply")
            assert reply["re"] == "p1" and reply["say"] == "Pornit."


def test_brain_message_accepts_only_device_side_brains(tmp_path):
    e = Env(tmp_path)
    with e.client:
        d = e.paired_device()
        e.store.update_device(DEV, brain="none")
        with device_socket(e, d) as ws:
            send(ws, {"v": 1, "t": "brain", "brain": "claude"})  # B2 needs a key from /me: never from SOUL
            send(ws, {"v": 1, "t": "brain", "brain": "bridge"})
            recv_until(ws, "bridge.state")
            assert e.store.get_device(DEV)["brain"] == "bridge"
            send(ws, {"v": 1, "t": "bridge.forget"})
            assert recv_until(ws, "bridge.state")[-1]["paired"] is False
            send(ws, {"v": 1, "t": "brain", "brain": "none"})
            send(ws, {"v": 1, "t": "status", "rssi": -50})
    assert e.store.get_device(DEV)["brain"] == "none"
