"""End to end with tools/fake_device.py: pair, open the socket, ask, receive pushes (docs/07 §0.1 steps 3-7, §6)."""
import json
import socket
import threading
import time

import pytest

import suflet_ai.gateway as gateway_mod
from _gateway_kit import DEV, Env, FakeAnthropic, WsAdapter, a_resp, a_text, a_tool


def test_fake_device_pairs_asks_and_gets_pushes_over_the_socket(tmp_path):
    ant = FakeAnthropic([a_resp("tool_use", a_tool("t1", "reminder_create", when="2026-10-04T09:00",
                                                   text="call the bank")),
                         a_text("I'll remind you tomorrow at 9.")])
    e = Env(tmp_path, anthropic=ant)
    lines = []
    d = e.device(say=lines.append)
    assert d.authenticate()["state"] == "pending"

    def claim_when_code_shows(dev):
        if dev.shown.pairing and not dev.shown.confirms and not getattr(dev, "_claimed", False):
            dev._claimed = True
            e.gw.claim("acc_1", "Ana", "ana@example.com", dev.shown.pairing["code"], "198.51.100.4")
        return dev.state == "paired"

    with e.ws(d.token) as conn:
        ws = WsAdapter(conn)
        d.ws_session(ws, until=claim_when_code_shows)
        assert d.state == "paired" and e.store.owner(DEV) == "acc_1"
        # the next session: hello -> welcome(paired) -> replay -> ask -> push + reply
        d.ws_session(ws, ask="remind me tomorrow at 9 to call the bank",
                     until=lambda dev: bool(dev.shown.replies))
        reply = d.shown.replies[-1]
        assert reply["say"] == "I'll remind you tomorrow at 9." and reply["brain"] == "cloud"
        push = d.shown.pushes[-1]
        assert push["action"] == "reminder.create" and reply["seqs"] == [push["seq"]] and d.seq == push["seq"]
        assert push["item_id"] in d.items
        # a connector push (the user's own Claude) while connected; the device acks it
        seq = e.gw.push(DEV, "note.create", {"text": "from claude.ai", "tags": []}, "it_ext",
                        {"kind": "connector", "app": "claude"}, say="From Claude: note saved")
        m = json.loads(ws.receive_text())
        for f in d.process(m):
            ws.send_text(json.dumps(f))
        assert e.gw.wait_delivery(DEV, seq, timeout=2.0) == "shown"
        # pause connectors (a touch on SOUL): the device refuses connector pushes with err paused
        ws.send_text(json.dumps(d.connectors_msg(True)))
        seq2 = e.gw.push(DEV, "note.create", {"text": "blocked", "tags": []}, "it_ext2",
                         {"kind": "connector", "app": "claude"})
        for f in d.process(json.loads(ws.receive_text())):
            assert f == {"v": 1, "t": "ack", "seq": seq2, "ok": False, "err": "paused"}
            ws.send_text(json.dumps(f))
        assert e.gw.wait_delivery(DEV, seq2, timeout=2.0) == "queued"
    assert any(x.startswith("SCREEN pairing code ") for x in lines)
    assert not any(d.token in x for x in lines)


def test_fake_device_over_long_poll(tmp_path):
    e = Env(tmp_path)
    d = e.device(confirm=lambda m: True)
    d.authenticate()
    d.send([d.hello()])
    assert d.shown.pairing and d.state == "pending"
    e.gw.claim("acc_1", "Ana", "ana@example.com", d.shown.pairing["code"], "198.51.100.4")
    d.poll()  # pair.confirm -> pair.ok (sent by the fake device) -> paired
    assert d.state == "paired"
    e.store.update_device(DEV, brain="none")
    d.send([d.ask_msg("note buy milk")])
    assert d.shown.replies[-1]["provider"] == "rules"
    d.poll()
    assert d.shown.pushes[-1]["action"] == "note.create" and d.seq == 1
    assert e.gw.wait_delivery(DEV, 1, timeout=0) == "shown"  # the fake device acked it


def test_server_py_registers_the_device_routes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from suflet_ai import server

    e = Env(tmp_path)
    monkeypatch.setenv("SUFLET_API_TOKEN", "dev-token-for-tests")
    gateway_mod.set_gateway(e.gw)
    try:
        c = TestClient(server.app)
        assert c.get("/v1/ping").json()["ok"] is True
        d = e.device()
        d.http.client = c
        d.authenticate()
        st = c.post("/v1/device/send", json={"messages": [d.hello()]},
                    headers={"authorization": f"Bearer {d.token}"}).json()
        code = next(m for m in st["messages"] if m["t"] == "pairing")["code"]
        # the dev claim route sits behind the shared token; the device routes never use it
        assert c.post("/v1/dev/pair/claim", json={"code": code}).status_code == 401
        r = c.post("/v1/dev/pair/claim", json={"code": code},
                   headers={"authorization": "Bearer dev-token-for-tests"})
        assert r.status_code == 202 and r.json()["state"] == "awaiting_device"
        r = c.get(f"/v1/dev/pair/{r.json()['pid']}", headers={"authorization": "Bearer dev-token-for-tests"})
        assert r.json() == {"state": "awaiting_device"}
    finally:
        gateway_mod.set_gateway(None)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_cli_against_a_real_server(tmp_path, monkeypatch, capsys):
    """The CLI as a human would run it: real HTTP, a real WebSocket (websockets), the dev claim route."""
    uvicorn = pytest.importorskip("uvicorn")
    pytest.importorskip("websockets")
    import sys
    from pathlib import Path

    from fastapi import Depends

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import fake_device

    from suflet_ai.gateway import build_dev_router, build_router
    from suflet_ai.server import auth

    e = Env(tmp_path, server_keys=False)  # brain A without a service key answers with the rules (note: upstream)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(build_router(lambda: e.gw))
    app.include_router(build_dev_router(lambda: e.gw), dependencies=[Depends(auth)])
    monkeypatch.setenv("SUFLET_API_TOKEN", "cli-dev-token")
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                                           ws_ping_interval=None))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        key = tmp_path / "k" / "dev.pem"
        rc = fake_device.main(["--base", f"http://127.0.0.1:{port}", "--host", "soul.example",
                               "--device-id", DEV, "--key", str(key), "--claim", "--api-token", "cli-dev-token",
                               "--confirm", "yes", "--ask", "note buy milk", "--listen", "1.5"])
        out = capsys.readouterr().out
        assert rc == 0, out
        assert "auth ok: state=pending" in out and "SCREEN pairing code" in out
        assert "claim: HTTP 202 awaiting_device" in out and "SCREEN Hi Dev! (paired)" in out
        assert "PUSH #1 note.create" in out and "SAY [rules/" in out
        assert (key.stat().st_mode & 0o777) == 0o600 and e.store.owner(DEV) == "acc_dev"
        assert "BEGIN PRIVATE KEY" not in out and "sdt_" not in out
        # the same key file and long-poll on the next run
        rc = fake_device.main(["--base", f"http://127.0.0.1:{port}", "--host", "soul.example",
                               "--device-id", DEV, "--key", str(key), "--poll", "--ask", "note eggs",
                               "--listen", "1"])
        out = capsys.readouterr().out
        assert rc == 0 and "auth ok: state=paired" in out and "note.create" in out
    finally:
        server.should_exit = True
        t.join(5)
