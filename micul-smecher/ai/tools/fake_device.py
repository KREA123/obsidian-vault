#!/usr/bin/env python3
"""A fake SOUL that speaks the device side of docs/07-CONNECT-AI.md §6, for end-to-end tests.

It does what the firmware does: holds an ECDSA P-256 device key, signs the
challenge (`soul-auth-v1\\n{host}\\n{device_id}\\n{nonce}`), opens the
`soul.v1` WebSocket (or uses long-poll), sends `hello`, shows the pairing code,
answers `pair.confirm` (the "touch"), sends a text turn (`ask`), applies and
acks every `push`, and prints what a real SOUL would show.

    # terminal 1: the dev server (SOUL_PUBLIC_HOST must match the host the device signs for)
    SUFLET_API_TOKEN=dev SOUL_PUBLIC_HOST=soul.example uvicorn suflet_ai.server:app --port 8787

    # terminal 2: pair (claims the code as a dev account through /v1/dev/pair/claim), ask, listen
    python tools/fake_device.py --base http://127.0.0.1:8787 --claim --api-token dev --confirm yes \\
        --ask "remind me tomorrow at 9 to call the bank" --listen 10

    # long-poll instead of the WebSocket
    python tools/fake_device.py --base http://127.0.0.1:8787 --poll --ask "note buy milk"

What it never prints: the private key, the device token. The pairing code is
printed as the device's screen would show it (this is a fake device).
The key file (PEM, mode 0600) lives in ~/.config/soul-fake/ unless --key says otherwise.

The `FakeDevice` class is transport-agnostic so tests can drive it with
FastAPI's TestClient (see tests/test_fake_device.py).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

PROTOCOL = "soul.v1"
CAPS = ["text", "cards", "alarms", "reminders", "notes", "timers", "focus", "inbox", "confirm"]
PUSH_ACTIONS = ("note.create", "reminder.create", "alarm.set", "timer.start", "focus.start", "answer.show",
                "item.delete")


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


# =================================================================== key ==

class DeviceKey:
    """The device's ECDSA P-256 key. The private scalar never leaves this object (no getter, no repr)."""

    def __init__(self, private_key: ec.EllipticCurvePrivateKey):
        self._k = private_key

    def __repr__(self) -> str:
        return f"DeviceKey(pub={self.pub[:10]}…)"

    @classmethod
    def generate(cls) -> "DeviceKey":
        return cls(ec.generate_private_key(ec.SECP256R1()))

    @classmethod
    def from_scalar(cls, d: int) -> "DeviceKey":
        return cls(ec.derive_private_key(d, ec.SECP256R1()))

    @classmethod
    def load_or_create(cls, path: Path) -> "DeviceKey":
        if path.exists():
            k = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if not isinstance(k, ec.EllipticCurvePrivateKey) or not isinstance(k.curve, ec.SECP256R1):
                raise SystemExit(f"{path} is not a P-256 key")
            return cls(k)
        key = cls.generate()
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = key._k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                   serialization.NoEncryption())
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(pem)
        return key

    @property
    def pub(self) -> str:
        """b64u of the 65-byte uncompressed SEC1 point (87 characters)."""
        raw = self._k.public_key().public_bytes(serialization.Encoding.X962,
                                                serialization.PublicFormat.UncompressedPoint)
        return b64u(raw)

    def sign(self, msg: bytes) -> str:
        """ECDSA P-256 / SHA-256, raw r||s (64 bytes), b64u (86 characters)."""
        r, s = decode_dss_signature(self._k.sign(msg, ec.ECDSA(hashes.SHA256())))
        return b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def auth_message(host: str, device_id: str, nonce: str) -> bytes:
    return f"soul-auth-v1\n{host}\n{device_id}\n{nonce}".encode("utf-8")


def random_device_id() -> str:
    return "soul-" + secrets.token_hex(6)


# ============================================================ transports ==

class AuthFailed(Exception):
    def __init__(self, status: int, body: Any):
        code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        super().__init__(f"auth failed: HTTP {status} {code or ''}".strip())
        self.status, self.code = status, code


class Http:
    """The two calls the device makes: JSON POST and GET. `client` is httpx.Client or a FastAPI TestClient."""

    def __init__(self, client: Any, base: str = ""):
        self.client = client
        self.base = base.rstrip("/")
        self._timeouts = type(client).__name__ != "TestClient"  # Starlette's TestClient warns on timeout=

    def _kw(self, timeout: float) -> dict:
        return {"timeout": timeout} if self._timeouts else {}

    def post(self, path: str, body: Any, token: Optional[str] = None, timeout: float = 30.0):
        headers = {"content-type": "application/json"}
        if token:
            headers["authorization"] = f"Bearer {token}"
        r = self.client.post(self.base + path, content=json.dumps(body), headers=headers, **self._kw(timeout))
        return r.status_code, (r.json() if r.content else None)

    def get(self, path: str, token: Optional[str] = None, timeout: float = 30.0):
        headers = {"authorization": f"Bearer {token}"} if token else {}
        r = self.client.get(self.base + path, headers=headers, **self._kw(timeout))
        return r.status_code, (r.json() if r.content else None)


class Closed(Exception):
    def __init__(self, code: Optional[int]):
        super().__init__(f"socket closed ({code})")
        self.code = code


class WsAdapter:
    """send_text / receive_text over `websockets.sync.client` or Starlette's WebSocketTestSession."""

    def __init__(self, conn: Any):
        self.conn = conn

    def send_text(self, text: str) -> None:
        if hasattr(self.conn, "send_text"):
            self.conn.send_text(text)
        else:
            self.conn.send(text)

    def receive_text(self, timeout: Optional[float] = None) -> Optional[str]:
        """The next text frame; None on timeout (websockets only). Raises Closed when the socket closes."""
        try:
            if hasattr(self.conn, "receive_text"):  # Starlette test session (blocking)
                return self.conn.receive_text()
            from websockets.exceptions import ConnectionClosed

            try:
                data = self.conn.recv(timeout=timeout)
            except TimeoutError:
                return None
            except ConnectionClosed as e:
                rcvd = getattr(e, "rcvd", None)
                raise Closed(rcvd.code if rcvd else None) from None
            return data if isinstance(data, str) else None
        except Closed:
            raise
        except Exception as e:  # noqa: BLE001 - Starlette raises WebSocketDisconnect(code)
            if type(e).__name__ == "WebSocketDisconnect":
                raise Closed(getattr(e, "code", None)) from None
            raise

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass


# =========================================================== the device ==

@dataclass
class Shown:
    """What the round screen would show, newest last (the CLI prints it, tests inspect it)."""

    pairing: Optional[dict] = None
    confirms: List[dict] = field(default_factory=list)
    replies: List[dict] = field(default_factory=list)
    pushes: List[dict] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    other: List[dict] = field(default_factory=list)


class FakeDevice:
    def __init__(self, http: Http, device_id: str, key: DeviceKey, host: str, *, lang: str = "en",
                 caps: Optional[List[str]] = None, confirm: Callable[[dict], bool] = lambda m: True,
                 say: Callable[[str], None] = lambda s: None, fw: str = "0.4.0-fake", hw: str = "lcd28",
                 power: str = "usb"):
        self.http = http
        self.device_id = device_id
        self.key = key
        self.host = host
        self.lang = lang
        self.caps = list(caps or CAPS)
        self.confirm = confirm      # the "touch": decides pair.ok / pair.no
        self.say = say              # output for humans (print in the CLI)
        self.fw, self.hw, self.power = fw, hw, power
        self.token: Optional[str] = None
        self.token_exp = 0.0
        self.auth_info: dict = {}
        self.welcome: dict = {}
        self.state = "unknown"
        self.seq = 0                # last applied push seq (NVS soulsync/seq on the real device)
        self.items: Dict[str, dict] = {}   # item_id -> push (the device store)
        self.pending: Dict[str, dict] = {}  # needs_accept items waiting for a tap
        self.paused = False         # NVS soulsync/conn
        self.conv: Optional[str] = None
        self.conv_at = 0.0
        self.reset_flag = False     # NVS soulid/rst
        self.shown = Shown()

    def __repr__(self) -> str:
        return f"FakeDevice({self.device_id}, state={self.state}, seq={self.seq})"

    # ------------------------------------------------------------ auth --
    def authenticate(self) -> dict:
        st, ch = self.http.post("/v1/device/challenge", {"device_id": self.device_id})
        if st != 200:
            raise AuthFailed(st, ch)
        nonce = ch["nonce"]
        body = {"device_id": self.device_id, "pub": self.key.pub, "nonce": nonce,
                "sig": self.key.sign(auth_message(self.host, self.device_id, nonce)),
                "fw": self.fw, "hw": self.hw, "reset": self.reset_flag}
        st, res = self.http.post("/v1/device/auth", body)
        if st != 200:
            raise AuthFailed(st, res)
        self.token = res["token"]
        self.token_exp = time.time() + int(res.get("expires_in", 0))
        self.reset_flag = False  # cleared after an auth 200 (§6.1)
        self.state = res.get("state", "unknown")
        self.auth_info = {k: v for k, v in res.items() if k != "token"}
        return self.auth_info

    # ---------------------------------------------------------- frames --
    def hello(self) -> dict:
        return {"v": 1, "t": "hello", "proto": [1], "fw": self.fw, "hw": self.hw, "caps": self.caps,
                "after": self.seq, "lang": self.lang, "brain_local": "cloud", "power": self.power}

    def ask_msg(self, text: str, ctx: Optional[dict] = None) -> dict:
        conv = self.conv if self.conv and time.time() - self.conv_at < 600 else None
        return {"v": 1, "t": "ask", "id": "a" + secrets.token_hex(6), "text": text, "lang": self.lang,
                "conv": conv, "ctx": ctx or {"timer_left_min": None, "unsynced": []}}

    def connectors_msg(self, paused: bool) -> dict:
        self.paused = paused
        return {"v": 1, "t": "connectors", "paused": paused}

    def accept(self, item_id: str, ok: bool = True) -> Optional[dict]:
        """The user taps a pending (needs_accept) card."""
        p = self.pending.pop(item_id, None)
        if p is None:
            return None
        if ok:
            self.items[item_id] = p
        return {"v": 1, "t": "item.state", "item_id": item_id, "state": "accepted" if ok else "rejected",
                "at": int(time.time())}

    def process(self, m: dict) -> List[dict]:
        """Apply one cloud -> device message; returns the frames the device sends back."""
        t = m.get("t")
        out: List[dict] = []
        if t == "welcome":
            self.welcome = m
            self.state = m.get("state", self.state)
            self.say(f"welcome: state={self.state} brain={m.get('brain')} owner={m.get('owner') or '-'} "
                     f"tz={m.get('tz')}")
        elif t == "pairing":
            self.shown.pairing = m
            code = m.get("code", "")
            self.say(f"SCREEN pairing code {code[:4]}-{code[4:]}  (QR: {m.get('url')})")
        elif t == "pair.confirm":
            self.shown.confirms.append(m)
            self.say(f"SCREEN Pair with {m.get('name')} ({m.get('account_hint')})?  [touch]")
            out.append({"v": 1, "t": "pair.ok" if self.confirm(m) else "pair.no", "pid": m.get("pid")})
        elif t == "paired":
            self.state = "paired"
            self.say(f"SCREEN Hi {m.get('owner')}! (paired)")
        elif t == "unpaired":
            self.state = "unpaired"
            self.say(f"SCREEN unpaired ({m.get('reason')})")
        elif t in ("replay.done",):
            self.shown.other.append(m)
        elif t == "resync":
            self.seq = int(m.get("last", 0))
            self.shown.other.append(m)
        elif t == "reply":
            self.shown.replies.append(m)
            if m.get("conv"):
                self.conv, self.conv_at = m["conv"], time.time()
            self.say(f"SAY [{m.get('provider')}/{m.get('brain')}] {m.get('say')}"
                     + (f"  (note: {m['note']})" if m.get("note") else ""))
        elif t == "push":
            out.append(self._push(m))
        elif t == "error":
            self.shown.errors.append(m)
            self.say(f"error {m.get('code')}: {m.get('msg')}")
        else:  # added, inbox.state, config, say.delta and anything unknown (must-ignore)
            self.shown.other.append(m)
        return out

    def _push(self, m: dict) -> dict:
        seq, item_id, action = m.get("seq"), m.get("item_id"), m.get("action")
        ack = {"v": 1, "t": "ack", "seq": seq, "ok": True}
        origin = m.get("origin") or {}
        if action not in PUSH_ACTIONS:
            ack.update(ok=False, err="unsupported")
        elif self.paused and origin.get("kind") in ("connector", "shortcut"):
            ack.update(ok=False, err="paused")
        elif item_id in self.items or item_id in self.pending:
            pass  # at-least-once: already applied, ack again
        else:
            if action == "item.delete":
                self.items.pop(m.get("args", {}).get("item_id", ""), None)
            elif m.get("needs_accept"):
                self.pending[item_id] = m
            else:
                self.items[item_id] = m
            self.shown.pushes.append(m)
            src = origin.get("app") or origin.get("kind")
            body = json.dumps(m.get("args"), ensure_ascii=False)
            self.say(f"PUSH #{seq} {action} from {src}: {body}" + ("  [tap to accept]" if m.get("needs_accept") else ""))
        if isinstance(seq, int):
            self.seq = max(self.seq, seq)
        return ack

    # --------------------------------------------------------- WS loop --
    def ws_session(self, ws: WsAdapter, *, ask: Optional[str] = None, listen: float = 0.0,
                   until: Optional[Callable[["FakeDevice"], bool]] = None, max_frames: int = 500) -> Optional[int]:
        """hello -> welcome/replay -> (ask) -> handle frames until `until(self)`, `listen` s of quiet, or close.

        Returns the close code when the server closed the socket, else None."""
        ws.send_text(json.dumps(self.hello()))
        asked = ask is None
        deadline = time.time() + listen if listen else None
        for _ in range(max_frames):
            try:
                raw = ws.receive_text(timeout=max(0.1, deadline - time.time()) if deadline else None)
            except Closed as c:
                return c.code
            if raw is None:
                if deadline and time.time() >= deadline:
                    return None
                continue
            m = json.loads(raw)
            for f in self.process(m):
                ws.send_text(json.dumps(f))
            if not asked and m.get("t") == "replay.done":
                ws.send_text(json.dumps(self.ask_msg(ask)))
                asked = True
            if until is not None and until(self):
                return None
        return None

    # ---------------------------------------------------- long-poll loop --
    def send(self, msgs: List[dict]) -> List[dict]:
        st, res = self.http.post("/v1/device/send", {"messages": msgs}, token=self.token)
        if st != 200:
            raise AuthFailed(st, res)
        replies = res.get("messages", [])
        back: List[dict] = []
        for m in replies:
            back += self.process(m)
        if back:
            self.send(back)
        return replies

    def poll(self, wait: int = 0) -> List[dict]:
        got: List[dict] = []
        while True:
            st, res = self.http.get(f"/v1/device/poll?after={self.seq}&wait={wait}", token=self.token,
                                    timeout=wait + 10)
            if st != 200:
                raise AuthFailed(st, res)
            msgs = res.get("messages", [])
            got += msgs
            back: List[dict] = []
            for m in msgs:
                back += self.process(m)
            if back:
                self.send(back)
            if not res.get("more"):
                return got
            wait = 0


# ================================================================== CLI ==

def _claim(http: Http, api_token: str, code: str) -> dict:
    """Dev only: claim the code shown on the device as a dev account (stands in for the /pair page)."""
    headers = {"authorization": f"Bearer {api_token}", "content-type": "application/json"}
    r = http.client.post(http.base + "/v1/dev/pair/claim", headers=headers,
                         content=json.dumps({"code": code, "account_id": "acc_dev", "first_name": "Dev",
                                             "email": "dev@example.com"}))
    return {"status": r.status_code, **(r.json() if r.content else {})}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="A fake SOUL device for end-to-end tests (docs/07 §6).")
    ap.add_argument("--base", default=os.environ.get("SOUL_BASE", "http://127.0.0.1:8787"),
                    help="cloud base URL (http(s)://host[:port])")
    ap.add_argument("--host", default=os.environ.get("SOUL_PUBLIC_HOST", "soul.example"),
                    help="the host the device signs for (must equal the server's SOUL_PUBLIC_HOST)")
    ap.add_argument("--device-id", default=os.environ.get("SOUL_FAKE_DEVICE_ID"))
    ap.add_argument("--key", help="PEM file of the device key (created if missing, mode 0600)")
    ap.add_argument("--lang", default="en", choices=["ro", "en"])
    ap.add_argument("--poll", action="store_true", help="use long-poll instead of the WebSocket")
    ap.add_argument("--confirm", default="ask", choices=["ask", "yes", "no"],
                    help="answer to pair.confirm: ask on stdin (the touch), or always yes / no")
    ap.add_argument("--claim", action="store_true", help="dev: claim the pairing code via /v1/dev/pair/claim")
    ap.add_argument("--api-token", default=os.environ.get("SUFLET_API_TOKEN", ""),
                    help="shared dev token for --claim (never needed by the device itself)")
    ap.add_argument("--ask", help="send this text turn after the replay")
    ap.add_argument("--listen", type=float, default=5.0, help="seconds to keep listening after the turn")
    ap.add_argument("--reset", action="store_true", help="report a factory reset (auth reset: true)")
    args = ap.parse_args(argv)

    import httpx

    device_id = args.device_id or random_device_id()
    key_path = Path(args.key) if args.key else Path.home() / ".config" / "soul-fake" / f"{device_id}.pem"
    key = DeviceKey.load_or_create(key_path)

    def confirm(m: dict) -> bool:
        if args.confirm != "ask":
            return args.confirm == "yes"
        try:
            return input("touch ✓ to pair? [y/N] ").strip().lower() in ("y", "yes", "da")
        except EOFError:
            return False

    with httpx.Client(timeout=40.0) as client:
        http = Http(client, args.base)
        dev = FakeDevice(http, device_id, key, args.host, lang=args.lang, confirm=confirm, say=print)
        dev.reset_flag = args.reset
        print(f"device {device_id} (key {key_path})")
        try:
            info = dev.authenticate()
        except AuthFailed as e:
            print(e)
            return 2
        print(f"auth ok: state={info.get('state')} trial={info.get('trial')}")

        claimed = False

        def maybe_claim(d: FakeDevice) -> bool:
            nonlocal claimed
            if args.claim and not claimed and d.state != "paired" and d.shown.pairing:
                claimed = True
                res = _claim(http, args.api_token, d.shown.pairing["code"])
                print(f"claim: HTTP {res.get('status')} {res.get('state') or res.get('error')}")
            return False

        if args.poll:
            dev.send([dev.hello()])
            for _ in range(10):
                maybe_claim(dev)
                dev.poll(wait=3 if dev.state != "paired" else 0)
                if dev.state == "paired" or not args.claim:
                    break
            if args.ask:
                dev.send([dev.ask_msg(args.ask)])
            end = time.time() + args.listen
            while time.time() < end:
                dev.poll(wait=max(1, min(25, int(end - time.time()))))
            return 0

        from websockets.sync.client import connect

        ws_base = args.base.replace("https://", "wss://", 1).replace("http://", "ws://", 1).rstrip("/")
        with connect(ws_base + "/v1/device/ws", subprotocols=[PROTOCOL],
                     additional_headers={"Authorization": f"Bearer {dev.token}"}) as conn:
            ws = WsAdapter(conn)
            if args.claim and dev.state != "paired":
                dev.ws_session(ws, until=lambda d: maybe_claim(d) or d.state == "paired", listen=30)
            # (re-)hello on the same socket: fresh welcome + replay, then the turn
            code = dev.ws_session(ws, ask=args.ask, listen=args.listen)
            if code:
                print(f"socket closed by the cloud: {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
