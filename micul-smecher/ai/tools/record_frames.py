#!/usr/bin/env python3
"""Record the frames the real SOUL Cloud sends a device, for the firmware's replay tests (docs/07 §6.17).

Starts the production composition (`suflet_ai.app.create_app`) on 127.0.0.1 with a fresh data dir, then a
scripted device (the same ECDSA auth and `soul.v1` WebSocket as `tools/fake_device.py`) walks one story:

  challenge + auth (both HTTP answers recorded, plus the 400 / 401 / 403 error answers)
  -> hello -> welcome + pairing -> a claim -> pair.confirm -> pair.ok -> paired
  -> pushes of every action (needs_accept, private, missed, item.delete) -> acks
  -> a text turn (offline rules brain) -> reply + push
  -> item.add / inbox.add -> added / inbox.state; a 12 KB frame -> error too_big with id + cid;
     a bad item.add -> error invalid with cid
  -> config (time zone, brain) -> disconnect, a push while offline -> reconnect -> replay + replay.done
  -> hello with `after` ahead of the cloud -> resync -> unpair -> unpaired + close 4403

and writes `firmware/test/test_suflet/cloud_frames.h` (frames in arrival order, socket boundaries marked,
the expected final state and seq). Nothing here needs a key; the device key is a throwaway.

    python tools/record_frames.py            # from ai/; rewrites the header
    python tools/record_frames.py --check    # exit 1 if the header is out of date (frame *types* only)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

HEADER = HERE.parents[1] / "firmware" / "test" / "test_suflet" / "cloud_frames.h"
DEVICE_ID = "soul-c0ffee123456"


def _c_string(s: str) -> str:
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ord(ch) < 0x20:
            out.append(f"\\x{ord(ch):02x}")
        elif ord(ch) < 0x80:
            out.append(ch)
        else:  # UTF-8 bytes as octal escapes (no hex run-on into following hex digits)
            out.append("".join(f"\\{b:03o}" for b in ch.encode("utf-8")))
    return '"' + "".join(out) + '"'


class Recorder:
    def __init__(self, base: str, host: str, gw: Any):
        from fake_device import DeviceKey, auth_message

        self.base, self.host, self.gw = base, host, gw
        self.key = DeviceKey.generate()
        self.auth_message = auth_message
        self.frames: List[Dict[str, Any]] = []   # {"t", "json", "socket_start"}
        self.http: List[Dict[str, Any]] = []     # {"what", "status", "body"}
        self.seq = 0                              # like CloudSession.lastSeq
        self.token = ""
        self.conn = None
        self._new_socket = False
        self.state = ""

    # ------------------------------------------------------------------ http --
    def post(self, path: str, body: dict, what: str, record: bool = True) -> tuple:
        import httpx

        r = httpx.post(self.base + path, json=body, timeout=10)
        text = r.text
        if record:
            # the token is a real secret of this throwaway run: recorded as a same-length placeholder
            if '"token"' in text:
                j = r.json()
                j["token"] = "sdt_" + "R" * (len(j["token"]) - 4)
                text = json.dumps(j, separators=(",", ":"))
            self.http.append({"what": what, "status": r.status_code, "body": text})
        return r.status_code, (r.json() if r.content else None)

    def authenticate(self) -> None:
        st, ch = self.post("/v1/device/challenge", {"device_id": DEVICE_ID}, "challenge")
        assert st == 200, ch
        nonce = ch["nonce"]
        sig = self.key.sign(self.auth_message(self.host, DEVICE_ID, nonce))
        body = {"device_id": DEVICE_ID, "pub": self.key.pub, "nonce": nonce, "sig": sig, "fw": "1.2.0-rec",
                "hw": "lcd28", "reset": False}
        # error answers first: a replayed nonce after a good auth, a signature for another host
        st, res = self.post("/v1/device/auth", body, "auth_ok")
        assert st == 200, res
        self.token = res["token"]
        self.state = res["state"]
        st, _ = self.post("/v1/device/auth", body, "auth_bad_nonce")
        assert st == 400
        _, ch2 = self.post("/v1/device/challenge", {"device_id": DEVICE_ID}, "challenge2", record=False)
        bad = dict(body, nonce=ch2["nonce"], sig=self.key.sign(self.auth_message("evil.example", DEVICE_ID, ch2["nonce"])))
        st, _ = self.post("/v1/device/auth", bad, "auth_bad_signature")
        assert st == 401

    # -------------------------------------------------------------- socket --
    def connect(self) -> None:
        from websockets.sync.client import connect

        ws = self.base.replace("http://", "ws://", 1) + "/v1/device/ws"
        self.conn = connect(ws, subprotocols=["soul.v1"], additional_headers={"Authorization": f"Bearer {self.token}"})
        assert self.conn.subprotocol == "soul.v1"
        self._new_socket = True

    def send(self, m: dict) -> None:
        self.conn.send(json.dumps(m, ensure_ascii=False))

    def hello(self, after: Optional[int] = None) -> None:
        self.send({"v": 1, "t": "hello", "proto": [1], "fw": "1.2.0-rec", "hw": "lcd28",
                   "caps": ["text", "cards", "alarms", "reminders", "notes", "timers", "focus", "inbox", "confirm"],
                   "after": self.seq if after is None else after, "lang": "en", "brain_local": "cloud",
                   "power": "usb", "tz_posix": "EET-2EEST,M3.5.0/3,M10.5.0/4"})

    def recv(self, timeout: float = 5.0) -> Optional[dict]:
        try:
            raw = self.conn.recv(timeout=timeout)
        except TimeoutError:
            return None
        m = json.loads(raw)
        self.frames.append({"t": m.get("t", ""), "json": raw, "socket_start": self._new_socket})
        self._new_socket = False
        t = m.get("t")
        if t == "push":  # what CloudSession does: replays acked, new ones applied then acked
            self.send({"v": 1, "t": "ack", "seq": m["seq"], "ok": True})
            self.seq = max(self.seq, m["seq"])
        elif t == "resync":
            self.seq = m["last"]
        elif t == "welcome":
            self.state = m["state"]
        elif t == "paired":
            self.state = "paired"
        elif t == "unpaired":
            self.state = "unpaired"
        return m

    def until(self, pred, timeout: float = 8.0, what: str = "") -> dict:
        end = time.time() + timeout
        while time.time() < end:
            m = self.recv(max(0.05, end - time.time()))
            if m is not None and pred(m):
                return m
        raise AssertionError(f"timed out waiting for {what}; got {[f['t'] for f in self.frames[-10:]]}")

    def quiet(self, seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            self.recv(max(0.05, end - time.time()))

    def close(self) -> Optional[int]:
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass
        return None


def record(tmp: str) -> Recorder:
    from e2e_connect import ServerThread, free_port

    from suflet_ai import gateway as gateway_mod
    from suflet_ai.accounts import DevMailbox
    from suflet_ai.app import create_app
    from suflet_ai.config import Settings
    from suflet_ai.devices import DeviceStore
    from suflet_ai.gateway import Gateway
    from suflet_ai.soul import SoulService

    port = free_port()
    host = f"127.0.0.1:{port}"
    for k, v in {"SOUL_ENV": "dev", "SOUL_PUBLIC_HOST": host, "SOUL_PUBLIC_SCHEME": "http",
                 "SUFLET_TZ": "Europe/Bucharest"}.items():
        os.environ[k] = v
    for k in ("SUFLET_API_TOKEN", "SOUL_ANTHROPIC_KEY", "SOUL_OPENAI_KEY"):
        os.environ.pop(k, None)
    svc = SoulService(settings=Settings(data_dir=tmp), master_secret=b"m" * 32)
    gw = Gateway(svc, DeviceStore(os.path.join(tmp, "gateway.sqlite"), host=host, policy="pending", pepper=b"p" * 32,
                                  trial_turns=0))
    app = create_app(service=svc, gateway=gw, mailer=DevMailbox(), db_path=os.path.join(tmp, "auth.sqlite"))
    srv = ServerThread(app, port).start()
    rec = Recorder(srv.base, host, gw)
    try:
        rec.authenticate()
        rec.connect()
        rec.hello()
        rec.until(lambda m: m["t"] == "pairing", what="pairing")
        code = rec.frames[-1] and json.loads(rec.frames[-1]["json"])["code"]
        gw.claim("a_rec", "Ana", "ana.pop@example.com", code, "127.0.0.1")
        conf = rec.until(lambda m: m["t"] == "pair.confirm", what="pair.confirm")
        rec.send({"v": 1, "t": "pair.ok", "pid": conf["pid"]})   # the touch
        rec.until(lambda m: m["t"] == "paired", what="paired")
        rec.quiet(0.3)

        origin = {"kind": "connector", "app": "claude", "by": "Ana"}
        gw.push(DEVICE_ID, "note.create", {"text": "Buy batteries — și lapte", "tags": ["shop"]}, "it_n1", origin,
                say="From Claude: noted.")
        gw.push(DEVICE_ID, "reminder.create", {"when": "2030-10-03T03:00", "text": "Call the bank"}, "it_r1", origin,
                needs_accept=True)
        gw.push(DEVICE_ID, "reminder.create", {"when": "2020-10-01T08:00", "text": "Pills"}, "it_r0", origin)
        gw.push(DEVICE_ID, "alarm.set", {"hhmm": "07:30", "days": ["mon", "tue", "wed", "thu", "fri"], "label": "Work"},
                "it_a1", origin)
        gw.push(DEVICE_ID, "timer.start", {"seconds": 90, "label": "tea"}, "it_t1", {"kind": "app"})
        gw.push(DEVICE_ID, "focus.start", {"minutes": 25, "label": "write"}, "it_f1", {"kind": "app"})
        gw.push(DEVICE_ID, "answer.show", {"title": "Pancakes", "body": "1. flour\n2. eggs"}, "it_c1", origin,
                say="Here are the steps", private=True)
        gw.push(DEVICE_ID, "item.delete", {"item_id": "it_a1"}, "it_a1", {"kind": "app"})
        rec.until(lambda m: m["t"] == "push" and m["action"] == "item.delete", what="8 pushes")

        gw.send_config(DEVICE_ID, brain="none")  # offline rules: a turn with no LLM
        rec.until(lambda m: m["t"] == "config", what="config brain")
        rec.send({"v": 1, "t": "ask", "id": "a1", "text": "remind me tomorrow at 9 to call mom", "lang": "en",
                  "conv": None, "ctx": {"timer_left_min": None, "unsynced": []}})
        rec.until(lambda m: m["t"] == "reply", what="reply")
        rec.quiet(0.3)

        rec.send({"v": 1, "t": "item.add", "cid": "c0ffee0000000001", "action": "note.create",
                  "args": {"text": "made on SOUL", "tags": []}, "created": "2026-10-03T10:00"})
        rec.until(lambda m: m["t"] == "added", what="added")
        rec.send({"v": 1, "t": "inbox.add", "cid": "c0ffee0000000002", "text": "What should I cook tonight?",
                  "to": "claude"})
        rec.until(lambda m: m["t"] == "inbox.state", what="inbox.state")
        rec.send({"v": 1, "t": "item.add", "id": "big1", "cid": "c0ffee0000000003", "action": "note.create",
                  "args": {"text": "x" * 12000, "tags": []}, "created": "2026-10-03T10:00"})
        rec.until(lambda m: m["t"] == "error" and m["code"] == "too_big", what="too_big")
        rec.send({"v": 1, "t": "item.add", "cid": "c0ffee0000000004", "action": "alarm.set",
                  "args": {"hhmm": "99:99", "days": [], "label": ""}, "created": "2026-10-03T10:00"})
        rec.until(lambda m: m["t"] == "error" and m["code"] == "invalid", what="invalid")
        rec.send({"v": 1, "t": "item.state", "item_id": "it_r1", "state": "accepted", "at": int(time.time())})
        rec.send({"v": 1, "t": "connectors", "paused": False})
        rec.send({"v": 1, "t": "status", "rssi": -60, "power": "usb", "fw": "1.2.0-rec", "free_heap": 120000,
                  "awake": True})

        gw.send_config(DEVICE_ID, tz="Europe/London", quiet={"from": "23:00", "to": "07:00"})
        rec.until(lambda m: m["t"] == "config" and "posix_tz" in m, what="config tz")
        rec.quiet(0.3)

        # offline: a push waits; the reconnect replays it, then replay.done
        rec.close()
        time.sleep(0.2)
        gw.push(DEVICE_ID, "note.create", {"text": "While you were away", "tags": []}, "it_n2", origin)
        rec.connect()
        rec.hello()
        rec.until(lambda m: m["t"] == "replay.done", what="replay.done")
        rec.quiet(0.3)
        # a device ahead of the cloud (the cloud was restored): resync
        rec.close()
        rec.connect()
        rec.hello(after=rec.seq + 50)
        rec.until(lambda m: m["t"] == "resync", what="resync")
        rec.until(lambda m: m["t"] == "replay.done", what="replay.done 2")
        rec.quiet(0.3)
        gw.unpair(DEVICE_ID, "user")
        rec.until(lambda m: m["t"] == "unpaired", what="unpaired")
        try:
            rec.recv(2.0)
        except Exception as e:  # noqa: BLE001 - the 4403 close
            rcvd = getattr(e, "rcvd", None)
            rec.close_code = rcvd.code if rcvd else None
        return rec
    finally:
        rec.close()
        srv.stop()
        gateway_mod.set_gateway(None)


def header(rec: Recorder) -> str:
    types = []
    for f in rec.frames:
        if f["t"] not in types:
            types.append(f["t"])
    pushes = sum(1 for f in rec.frames if f["t"] == "push")
    lines = [
        "// GENERATED by ai/tools/record_frames.py from the running SOUL Cloud (suflet_ai.app). Do not edit:",
        "// run `python tools/record_frames.py` in ai/ to record again. Frames in arrival order; socket_start marks",
        "// a new WebSocket. The device token in the auth answer is replaced by a placeholder of the same length.",
        "#pragma once",
        "#include <stdint.h>",
        "",
        "struct RecordedFrame {",
        "  const char* t;",
        "  bool socket_start;",
        "  const char* json;",
        "};",
        "",
        "static const RecordedFrame kRecordedFrames[] = {",
    ]
    for f in rec.frames:
        lines.append(f"    {{{_c_string(f['t'])}, {'true' if f['socket_start'] else 'false'}, {_c_string(f['json'])}}},")
    lines += ["};", "", "static const char* const kRecordedTypes[] = {" + ", ".join(_c_string(t) for t in types) + "};",
              f"static const int kRecordedMin = {len(rec.frames)};",
              f"static const int kRecordedMinPushes = {max(0, pushes - 4)};",
              f"static const char* const kRecordedFinalState = {_c_string(rec.state)};",
              f"static const uint32_t kRecordedLastSeq = {rec.seq}u;", "",
              "struct RecordedHttp {", "  const char* what;", "  int status;", "  const char* body;", "};", "",
              "static const RecordedHttp kRecordedHttp[] = {"]
    for h in rec.http:
        lines.append(f"    {{{_c_string(h['what'])}, {h['status']}, {_c_string(h['body'])}}},")
    lines += ["};", ""]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    import logging
    import warnings

    logging.basicConfig(level=logging.WARNING)
    for name in ("httpx", "mcp", "uvicorn", "suflet_ai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(HEADER))
    ap.add_argument("--check", action="store_true", help="only compare the recorded frame types with the header")
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        rec = record(tmp)
    text = header(rec)
    if a.check:
        old = Path(a.out).read_text(encoding="utf-8") if Path(a.out).exists() else ""
        new_types = text.split("kRecordedTypes[] = ")[1].split(";")[0]
        ok = new_types in old
        print("cloud_frames.h is current" if ok else "cloud_frames.h is OUT OF DATE: run tools/record_frames.py")
        return 0 if ok else 1
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"recorded {len(rec.frames)} frames ({len(set(f['t'] for f in rec.frames))} types), "
          f"{len(rec.http)} HTTP answers -> {a.out}")
    print("types:", " ".join(dict.fromkeys(f["t"] for f in rec.frames)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
