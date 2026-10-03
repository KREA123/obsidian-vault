"""Deep-sleep wake-polls, cloud side (docs/07 §6.11): a paired SOUL says `sleep {wake_at}` and goes to sleep; every
<= 15 minutes it wakes, signs in, does one `GET /v1/device/poll?wait=0` (no socket, no hello), applies what came and
sends its acks + queue + the next `sleep` in one `POST /v1/device/send`. The connector's `will_ring` forecast
follows the announced wake."""
import time

from _gateway_kit import DEV, Env, hello, recv_until, send


def test_wake_poll_cycle_without_hello(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device()
    now = int(e.clock())
    with e.ws(d.token) as ws:
        send(ws, hello())
        recv_until(ws, "replay.done")
        send(ws, {"v": 1, "t": "sleep", "wake_at": now + 900})
        send(ws, {"v": 1, "t": "status", "rssi": -60})
        time.sleep(0.2)
    assert e.store.get_device(DEV)["wake_at"] == now + 900
    e.clock.advance(120)  # the socket is long gone: SOUL is asleep
    assert not e.gw.is_online(DEV)
    # a connector alarm while it sleeps: it will ring (SOUL wakes before), a 5-minute one would not
    seq = e.gw.push(DEV, "alarm.set", {"hhmm": "12:00", "days": [], "label": ""}, "it_a1",
                    {"kind": "connector", "app": "claude"})
    assert e.gw.forecast(DEV, "2026-10-03T12:00") == "yes"
    assert e.gw.forecast(DEV, "2026-10-03T10:05") == "no"
    assert e.store.push_status(DEV, seq)["acked"] is False
    # the wake: a fresh sign-in (the token lived in RAM), one poll, no hello
    e.clock.advance(780)
    d.authenticate()
    h = {"authorization": f"Bearer {d.token}"}
    r = e.client.get("/v1/device/poll?after=0&wait=0", headers=h)
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert [m["t"] for m in msgs if m["t"] != "inbox.state"] == ["push"]
    assert msgs[-1]["seq"] == seq and msgs[-1]["action"] == "alarm.set"
    assert not any(m["t"] == "welcome" for m in msgs)
    assert e.gw.is_online(DEV)  # polled just now
    nxt = int(e.clock()) + 900
    r = e.client.post("/v1/device/send", headers=h, json={"messages": [
        {"v": 1, "t": "ack", "seq": seq, "ok": True}, {"v": 1, "t": "sleep", "wake_at": nxt}]})
    assert r.status_code == 200 and r.json()["messages"] == []
    assert e.store.push_status(DEV, seq)["acked"] is True
    assert e.store.get_device(DEV)["wake_at"] == nxt
    # the next page is empty: nothing is delivered twice
    assert [m for m in e.client.get(f"/v1/device/poll?after={seq}&wait=0", headers=h).json()["messages"]
            if m["t"] == "push"] == []
