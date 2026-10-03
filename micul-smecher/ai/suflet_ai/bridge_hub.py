"""SOUL Bridge relay in SOUL Cloud: `/v1/bridge` (docs/08-OWN-CLAUDE.md §4, cloud transport).

SOUL Bridge is a small open-source program on the owner's computer that hands questions typed on SOUL to the
owner's own, official Claude Code (signed in by the owner, on that computer) and sends Claude's answer back.
The LAN transport is SOUL itself (`ws://soul-xxxx.local:8765/bridge`); this module is the cloud transport, for a
computer on another network or a SOUL that is only reachable through SOUL Cloud:

    bridge (PC) --wss /v1/bridge--> SOUL Cloud --soul.v1 socket / long-poll--> SOUL

Nothing here ever sees a Claude credential: the only secret is the bridge token `sbt_...` that SOUL Cloud
issues when a bridge pairs, stored as SHA-256, bound to one device and its owner's account, listed and
revocable on /me. Questions and answers pass through in memory (the answer's actions become ordinary
pushes, validated by the dispatcher like any brain's); nothing of the conversation is logged.

Frames (JSON text, <= 16 KB), the same as SOUL speaks on the LAN:

    bridge -> cloud   bridge.pair {v, code, bridge}            code shown on SOUL (8 Crockford chars, 5 min)
    cloud -> bridge   bridge.paired {token, device_id, name}  | bridge.denied {reason}   (then close)
    bridge -> cloud   bridge.hello {v, token, bridge, mode}    first frame of every other connection
    cloud -> bridge   bridge.welcome {device_id, name, lang, tz} | bridge.denied {reason}
    cloud -> bridge   ask {id, text, lang, now, tz, from}  ·  ask.cancel {id}  ·  answer.ack {id, shown}
    bridge -> cloud   ask.ack {id, state}  ·  answer {id, text, actions}  ·  answer.error {id, code, detail}

Device side (additive within soul.v1, must-ignore on older firmware):

    device -> cloud   bridge.code.get {}      (a touch on Settings > AI > My Claude on my computer)
                      bridge.forget {}        (a touch: forget every paired computer of this SOUL)
                      brain {brain}           (the owner picked "bridge" or "none" on SOUL)
    cloud -> device   bridge.code {code, expires_in, cmd}
                      bridge.state {paired, online, name}
                      ask.state {re, state: "waiting" | "thinking"}

Turn routing: a paired SOUL whose brain is `bridge` sends ordinary `ask`s; the gateway hands them to
`BridgeHub.ask`, which answers `bridge_offline` at once when no bridge is connected (SOUL then answers with its
offline rules and says "your computer is offline") and waits at most 120 s otherwise.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import re
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import WebSocket

from .devices import CROCKFORD, DEFAULT_TZ, DeviceStore, b64u, normalize_code, sha256_hex
from .memory_sync import memory_block

log = logging.getLogger("suflet_ai.bridge")

PROTOCOL_VERSION = 1
MAX_FRAME = 16 * 1024
FIRST_FRAME_S = 10.0
ANSWER_TIMEOUT_S = 120.0
CODE_TTL = 5 * 60
FLEET_FAILS_PER_HOUR = 1000
MAX_TOKENS_PER_DEVICE = 5
MAX_ACTIONS = 5
ANSWER_MAX = 1200
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_LABEL = re.compile(r"[\x00-\x1f<>]")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bridge_tokens (
    id TEXT PRIMARY KEY, hash TEXT NOT NULL UNIQUE, device_id TEXT NOT NULL, account_id TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '', created INTEGER NOT NULL, last_used INTEGER, revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS bridge_tokens_dev ON bridge_tokens(device_id);
CREATE TABLE IF NOT EXISTS bridge_codes (
    code_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, expires INTEGER NOT NULL, tries INTEGER NOT NULL DEFAULT 0
);
"""

# bridge answer.error codes -> the device's error codes (§6.9 + bridge_offline)
_ERR_MAP = {"timeout": "timeout", "claude_unavailable": "bridge_offline", "busy": "rate_limited",
            "bad_request": "invalid"}


class BridgeError(Exception):
    def __init__(self, code: str, msg: str = ""):
        super().__init__(f"{code}: {msg}")
        self.code = code
        self.msg = msg or code


@dataclass
class BridgeAnswer:
    text: str
    actions: List[dict] = field(default_factory=list)
    memory: List[dict] = field(default_factory=list)  # SOUL Memory ops ({op, text, ...}); SOUL validates them


class _Conn:
    def __init__(self, ws: WebSocket, device_id: str, token_id: str, label: str, mode: str):
        self.ws = ws
        self.device_id = device_id
        self.token_id = token_id
        self.label = label
        self.mode = mode
        self.lock = asyncio.Lock()
        self.closed = asyncio.Event()
        self.close_code: Optional[int] = None
        self.loop = asyncio.get_running_loop()

    async def send_from_any_loop(self, msg: dict) -> bool:
        """`send` from a coroutine that may run on another event loop (tests run one loop per socket)."""
        return await _on_loop(self.loop, self.send(msg))

    async def send(self, msg: dict) -> bool:
        if self.closed.is_set():
            return False
        async with self.lock:
            try:
                await self.ws.send_text(json.dumps(msg, ensure_ascii=False, separators=(",", ":")))
                return True
            except Exception:  # noqa: BLE001 - the peer went away
                self.closed.set()
                return False

    def close(self, code: int) -> None:
        def _do() -> None:
            if self.close_code is None:
                self.close_code = code
            self.closed.set()
        _soon(self.loop, _do)


@dataclass
class _Pending:
    device_id: str
    fut: "asyncio.Future[BridgeAnswer]"
    on_state: Optional[Callable[[str], Awaitable[None]]]
    conn: _Conn
    loop: asyncio.AbstractEventLoop  # the device side's loop (the future and on_state live there)

    def resolve(self, result: Optional[BridgeAnswer] = None, error: Optional[Exception] = None) -> None:
        def _do() -> None:
            if self.fut.done():
                return
            if error is not None:
                self.fut.set_exception(error)
            else:
                self.fut.set_result(result)
        _soon(self.loop, _do)

    def state(self, state: str) -> None:
        if self.on_state is not None:
            asyncio.run_coroutine_threadsafe(self.on_state(state), self.loop)


def _soon(loop: asyncio.AbstractEventLoop, fn: Callable[[], None]) -> None:
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is loop:
        fn()
    else:
        loop.call_soon_threadsafe(fn)


async def _on_loop(loop: asyncio.AbstractEventLoop, coro: Awaitable[Any]) -> Any:
    if asyncio.get_running_loop() is loop:
        return await coro
    return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, loop))


class BridgeHub:
    """Bridge tokens, bridge pairing codes and the live bridge sockets (one per device, newest wins)."""

    def __init__(self, store: DeviceStore, *, clock: Callable[[], float] = time.time,
                 notify_device: Optional[Callable[[str, dict], None]] = None,
                 answer_timeout: float = ANSWER_TIMEOUT_S):
        self.store = store
        self.clock = clock
        self.notify_device = notify_device  # gateway.control: sends bridge.state / bridge.code to SOUL
        self.answer_timeout = answer_timeout
        store.executescript(_SCHEMA)
        self.conns: Dict[str, _Conn] = {}
        self.pending: Dict[str, _Pending] = {}  # ask id -> waiting turn
        self._fails: Deque[int] = deque()  # failed bridge pairings, fleet-wide (last hour)

    def now(self) -> int:
        return int(self.clock())

    # ------------------------------------------------------------------ tokens --
    def tokens(self, account_id: str, device_id: Optional[str] = None) -> List[dict]:
        """The account's paired computers (never the token itself)."""
        q = "SELECT * FROM bridge_tokens WHERE account_id=? AND revoked=0"
        args: tuple = (account_id,)
        if device_id:
            q += " AND device_id=?"
            args += (device_id,)
        with self.store.lock:
            rows = self.store.db.execute(q + " ORDER BY created", args).fetchall()
        out = []
        for r in rows:
            c = self.conns.get(r["device_id"])
            out.append({"id": r["id"], "device_id": r["device_id"], "label": r["label"] or "computer",
                        "created": r["created"], "last_used": r["last_used"],
                        "online": bool(c and c.token_id == r["id"] and not c.closed.is_set())})
        return out

    def _issue(self, device_id: str, account_id: str, label: str) -> tuple[str, str]:
        token = "sbt_" + b64u(secrets.token_bytes(32))
        tid = "bt_" + b64u(secrets.token_bytes(9))
        label = _LABEL.sub("", str(label or ""))[:40] or "computer"
        with self.store.lock:
            live = self.store.db.execute(
                "SELECT id FROM bridge_tokens WHERE device_id=? AND revoked=0 ORDER BY created", (device_id,)).fetchall()
            for old in live[: max(0, len(live) - (MAX_TOKENS_PER_DEVICE - 1))]:  # keep the newest few
                self.store.db.execute("UPDATE bridge_tokens SET revoked=1 WHERE id=?", (old["id"],))
            self.store.db.execute(
                "INSERT INTO bridge_tokens(id, hash, device_id, account_id, label, created) VALUES (?,?,?,?,?,?)",
                (tid, sha256_hex(token), device_id, account_id, label, self.now()))
            self.store.db.commit()
        return tid, token

    def revoke(self, account_id: str, token_id: str) -> bool:
        with self.store.lock:
            r = self.store.db.execute("SELECT device_id FROM bridge_tokens WHERE id=? AND account_id=? AND revoked=0",
                                      (token_id, account_id)).fetchone()
            if not r:
                return False
            self.store.db.execute("UPDATE bridge_tokens SET revoked=1 WHERE id=?", (token_id,))
            self.store.db.commit()
        c = self.conns.get(r["device_id"])
        if c is not None and c.token_id == token_id:
            c.close(4401)
        self._state_changed(r["device_id"])
        return True

    def revoke_device(self, device_id: str) -> int:
        """Unpair / reset / "forget computers" on SOUL / account deletion: every token of the device goes."""
        with self.store.lock:
            cur = self.store.db.execute("UPDATE bridge_tokens SET revoked=1 WHERE device_id=? AND revoked=0",
                                        (device_id,))
            self.store.db.execute("DELETE FROM bridge_codes WHERE device_id=?", (device_id,))
            self.store.db.commit()
        c = self.conns.get(device_id)
        if c is not None:
            c.close(4401)
        return cur.rowcount

    def _token(self, token: Any) -> Optional[dict]:
        if not isinstance(token, str) or not token.startswith("sbt_") or len(token) > 128:
            return None
        with self.store.lock:
            r = self.store.db.execute("SELECT * FROM bridge_tokens WHERE hash=? AND revoked=0",
                                      (sha256_hex(token),)).fetchone()
        if not r:
            return None
        if self.store.owner(r["device_id"]) != r["account_id"]:  # the SOUL changed hands: the token is dead
            return None
        return dict(r)

    # ----------------------------------------------------------- pairing codes --
    def pair_code(self, device_id: str) -> dict:
        """A one-time code for `soul-bridge pair` (shown on SOUL, or on /me). Paired SOULs only."""
        if not self.store.owner(device_id):
            raise BridgeError("unpaired", "pair SOUL with your account first")
        code = "".join(secrets.choice(CROCKFORD) for _ in range(8))
        now = self.now()
        with self.store.lock:
            self.store.db.execute("DELETE FROM bridge_codes WHERE device_id=? OR expires < ?", (device_id, now))
            self.store.db.execute("INSERT INTO bridge_codes(code_hash, device_id, expires) VALUES (?,?,?)",
                                  (self.store._hmac("bridge:" + code), device_id, now + CODE_TTL))  # noqa: SLF001
            self.store.db.commit()
        return {"code": code, "expires_in": CODE_TTL,
                "cmd": f"soul-bridge pair {code[:4]}-{code[4:]} --cloud {self.store.host}"}

    def pair(self, code: Any, label: str, ip: str) -> dict:
        """Exchange a code for a token. Limits: 20 tries per network per hour, 1000 failures fleet-wide per hour."""
        from .devices import ip_prefix

        self.store.buckets.check(f"bridgepair:ip:{ip_prefix(ip)}", 20, 20 / 3600)
        now = self.now()
        while self._fails and self._fails[0] < now - 3600:
            self._fails.popleft()
        if len(self._fails) >= FLEET_FAILS_PER_HOUR:
            raise BridgeError("rate_limited", "too many tries, wait a few minutes")
        norm = normalize_code(code)
        if len(norm) != 8:
            self._fails.append(now)
            raise BridgeError("wrong_code", "the code has 8 characters, as shown on SOUL")
        h = self.store._hmac("bridge:" + norm)  # noqa: SLF001
        with self.store.lock:
            r = self.store.db.execute("SELECT * FROM bridge_codes WHERE code_hash=?", (h,)).fetchone()
            if r is not None:
                self.store.db.execute("DELETE FROM bridge_codes WHERE code_hash=?", (h,))  # single use
                self.store.db.commit()
        if r is None or r["expires"] < now:
            self._fails.append(now)
            raise BridgeError("wrong_code", "wrong or expired code: show a new one on SOUL")
        account = self.store.owner(r["device_id"])
        if not account:
            raise BridgeError("unpaired", "this SOUL is not paired with an account any more")
        tid, token = self._issue(r["device_id"], account, label)
        d = self.store.get_device(r["device_id"]) or {}
        log.info("bridge paired for %s", r["device_id"])
        return {"token": token, "device_id": r["device_id"], "name": d.get("name") or "SOUL", "token_id": tid}

    # ----------------------------------------------------------------- presence --
    def online(self, device_id: str) -> bool:
        c = self.conns.get(device_id)
        return bool(c and not c.closed.is_set())

    def state_msg(self, device_id: str) -> dict:
        with self.store.lock:
            n = self.store.db.execute("SELECT COUNT(*) AS n FROM bridge_tokens WHERE device_id=? AND revoked=0",
                                      (device_id,)).fetchone()["n"]
        c = self.conns.get(device_id)
        on = bool(c and not c.closed.is_set())
        return {"v": 1, "t": "bridge.state", "paired": n > 0, "online": on, "name": c.label if on else ""}

    def _state_changed(self, device_id: str) -> None:
        if self.notify_device is not None:
            try:
                self.notify_device(device_id, self.state_msg(device_id))
            except Exception:  # noqa: BLE001 - presence is best effort
                log.exception("bridge.state notify failed")

    # --------------------------------------------------------------------- turns --
    async def ask(self, device_id: str, ask: dict, lang: str, on_state: Optional[Callable[[str], Awaitable[None]]] = None,
                  now_local: Optional[str] = None, tz: Optional[str] = None) -> BridgeAnswer:
        """Hand one question to the device's bridge; raises BridgeError(bridge_offline | timeout | ...)."""
        c = self.conns.get(device_id)
        if c is None or c.closed.is_set():
            raise BridgeError("bridge_offline", "your computer is offline: open Start SOUL")
        qid = str(ask["id"])
        if qid in self.pending:
            raise BridgeError("invalid", "this question is already waiting")
        d = self.store.get_device(device_id) or {}
        tz = tz or d.get("tz") or DEFAULT_TZ
        if now_local is None:
            now_local = dt.datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%dT%H:%M")
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self.pending[qid] = _Pending(device_id, fut, on_state, c, loop)
        frame = {"t": "ask", "id": qid, "text": str(ask["text"]).strip()[:2000], "lang": lang, "now": now_local,
                 "tz": tz, "from": "keyboard"}
        mem = memory_block(ask.get("ctx"))
        if mem:  # SOUL Memory: what SOUL knows about the owner, for their Claude Code (docs/10 §4)
            frame["memory"] = mem
        try:
            if not await c.send_from_any_loop(frame):
                raise BridgeError("bridge_offline", "your computer is offline: open Start SOUL")
            try:
                return await asyncio.wait_for(asyncio.shield(fut), self.answer_timeout)
            except asyncio.TimeoutError:
                await c.send_from_any_loop({"t": "ask.cancel", "id": qid})
                raise BridgeError("timeout", "Claude on your computer did not answer in time") from None
        finally:
            self.pending.pop(qid, None)

    async def cancel(self, qid: str) -> None:
        p = self.pending.pop(qid, None)
        if p is not None:
            await p.conn.send_from_any_loop({"t": "ask.cancel", "id": qid})
            p.resolve(error=BridgeError("cancelled", "the question was cancelled on SOUL"))

    # ---------------------------------------------------------------- websocket --
    async def ws_endpoint(self, ws: WebSocket, client_ip: str = "-") -> None:
        await ws.accept()
        try:
            raw = await asyncio.wait_for(ws.receive_text(), FIRST_FRAME_S)
        except Exception:  # noqa: BLE001 - timeout, disconnect or a binary frame
            await _close(ws, 4400)
            return
        m = _parse(raw)
        if m is None:
            await _close(ws, 4400)
            return
        if m.get("t") == "bridge.pair":
            await self._ws_pair(ws, m, client_ip)
            return
        if m.get("t") != "bridge.hello":
            await _close(ws, 4400)
            return
        tok = self._token(m.get("token"))
        if tok is None:
            await _send(ws, {"t": "bridge.denied", "reason": "unknown bridge: pair again"})
            await _close(ws, 4401)
            return
        dev = tok["device_id"]
        mode = m.get("mode") if m.get("mode") in ("channel", "print") else "channel"
        conn = _Conn(ws, dev, tok["id"], tok["label"], mode)
        old = self.conns.get(dev)
        self.conns[dev] = conn
        if old is not None and old is not conn:
            old.close(4409)  # one bridge per SOUL: the newest wins
        with self.store.lock:
            self.store.db.execute("UPDATE bridge_tokens SET last_used=? WHERE id=?", (self.now(), tok["id"]))
            self.store.db.commit()
        d = self.store.get_device(dev) or {}
        await conn.send({"t": "bridge.welcome", "device_id": dev, "name": d.get("name") or "SOUL",
                         "lang": d.get("lang") or "ro", "tz": d.get("tz") or DEFAULT_TZ})
        log.info("bridge online for %s (%s)", dev, mode)
        self._state_changed(dev)
        recv: Optional[asyncio.Future] = None
        closer = asyncio.ensure_future(conn.closed.wait())
        try:
            while True:
                if recv is None:
                    recv = asyncio.ensure_future(ws.receive())
                done, _ = await asyncio.wait({recv, closer}, return_when=asyncio.FIRST_COMPLETED)
                if closer in done:
                    break
                msg = recv.result()
                recv = None
                if msg["type"] == "websocket.disconnect":
                    break
                text = msg.get("text")
                if text is None:
                    continue
                if len(text) > MAX_FRAME:
                    conn.close(1009)
                    break
                fm = _parse(text)
                if fm is not None:
                    await self._from_bridge(conn, fm)
        except Exception:  # noqa: BLE001 - a broken bridge must not take the hub down
            log.exception("bridge socket failed")
        finally:
            for f in (recv, closer):
                if f is not None and not f.done():
                    f.cancel()
            if self.conns.get(dev) is conn:
                del self.conns[dev]
            for qid, p in list(self.pending.items()):
                if p.conn is conn:
                    p.resolve(error=BridgeError("bridge_offline", "your computer went offline"))
            await _close(ws, conn.close_code or 1000)
            log.info("bridge offline for %s", dev)
            self._state_changed(dev)

    async def _ws_pair(self, ws: WebSocket, m: dict, ip: str) -> None:
        label = str(m.get("label") or m.get("bridge") or "computer")
        try:
            r = self.pair(m.get("code"), label, ip)
        except BridgeError as e:
            await _send(ws, {"t": "bridge.denied", "reason": e.msg})
            await _close(ws, 4403)
            return
        except Exception as e:  # noqa: BLE001 - rate limits come as GatewayError
            await _send(ws, {"t": "bridge.denied", "reason": getattr(e, "msg", "") or "try again later"})
            await _close(ws, 4429)
            return
        await _send(ws, {"t": "bridge.paired", "token": r["token"], "device_id": r["device_id"], "name": r["name"]})
        await _close(ws, 1000)
        self._state_changed(r["device_id"])

    async def _from_bridge(self, conn: _Conn, m: dict) -> None:
        t, qid = m.get("t"), m.get("id")
        if not isinstance(qid, str) or not _ID.match(qid):
            return
        p = self.pending.get(qid)
        if p is None or p.conn is not conn or p.fut.done():
            return  # an answer for a question that timed out, was cancelled, or belongs to another SOUL
        if t == "ask.ack":
            p.state("thinking")
        elif t == "answer":
            text = m.get("text")
            if not isinstance(text, str) or not text.strip():
                p.resolve(error=BridgeError("invalid", "the computer sent an empty answer"))
                return
            raw = m.get("actions") if isinstance(m.get("actions"), list) else []
            acts = [a for a in raw if isinstance(a, dict) and isinstance(a.get("type"), str)
                    and isinstance(a.get("args", {}), dict)][:MAX_ACTIONS]
            mem = [x for x in m.get("memory") if isinstance(x, dict)][:3] if isinstance(m.get("memory"), list) else []
            p.resolve(BridgeAnswer(text.strip()[:ANSWER_MAX], acts, mem))
            await conn.send({"t": "answer.ack", "id": qid, "shown": True})
        elif t == "answer.error":
            code = _ERR_MAP.get(str(m.get("code")), "upstream")
            p.resolve(error=BridgeError(code, str(m.get("detail") or code)[:200]))


def _parse(raw: Any) -> Optional[dict]:
    if not isinstance(raw, str) or len(raw) > MAX_FRAME:
        return None
    try:
        m = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(m, dict) or not isinstance(m.get("t"), str):
        return None
    if m.get("v", PROTOCOL_VERSION) != PROTOCOL_VERSION:
        return None
    return m


async def _send(ws: WebSocket, msg: dict) -> None:
    try:
        await ws.send_text(json.dumps(msg, ensure_ascii=False, separators=(",", ":")))
    except Exception:  # noqa: BLE001
        pass


async def _close(ws: WebSocket, code: int) -> None:
    try:
        await ws.close(code)
    except Exception:  # noqa: BLE001 - already closed
        pass
