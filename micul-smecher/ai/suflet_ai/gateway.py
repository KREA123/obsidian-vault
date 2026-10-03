"""SOUL device gateway: device auth, the `soul.v1` WebSocket, long-poll, the hub (docs/07-CONNECT-AI.md §3.2, §6).

    POST /v1/device/challenge     {"device_id"}                       -> {"nonce", "expires_in"}
    POST /v1/device/auth          {"device_id","pub","nonce","sig",...} -> {"token","ws_url",...}
    GET  /v1/device/ws            WebSocket, subprotocol soul.v1, Bearer sdt_...
    GET  /v1/device/poll          ?after=&wait=   long-poll fallback (same envelopes)
    POST /v1/device/send          {"messages": [...]}  -> {"messages": [answers]}
    GET  /v1/ping                 {"ok": true, "time": epoch}  (no auth; the portal's internet test)

`Gateway` is also the in-process API the rest of the cloud uses to reach a
device (thread-safe, callable from sync code such as MCP tools):

    gw.push(device_id, action, args, item_id, origin, say=..., private=..., needs_accept=...) -> seq
    await gw.push_and_wait(device_id, seq) / gw.wait_delivery(...)  -> "shown" | "queued" | "pending_accept"
    gw.forecast(device_id, "YYYY-MM-DDTHH:MM") -> "yes" | "no" | "unknown";  gw.is_online(device_id)
    gw.claim(account_id, first_name, email, code, ip) / gw.claim_state(pid, account_id)
    gw.unpair(device_id, reason, erase);  gw.send_config(device_id, **fields);  gw.inbox(device_id)

Liveness: the device pings every 25 s; run uvicorn with `--ws-ping-interval 25
--ws-ping-timeout 45` so a silent socket is dropped after ~70 s (ASGI apps do
not see ping frames). One process holds the hub (Phase 0); several instances
need Postgres LISTEN/NOTIFY between hubs.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import functools
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse

from .devices import (BRAINS, DEFAULT_TZ, VOICES, DeviceCtx, DeviceStore, GatewayError, check_device_id, posix_tz)
from .relay import DEFAULT_CLAUDE_MODEL, DEFAULT_OPENAI_MODEL, Relay

log = logging.getLogger("suflet_ai.gateway")

PROTOCOL = "soul.v1"
PROTO_VERSIONS = (1,)
LIMITS = {"ask_per_min": 20, "ask_per_day": 600, "frames_per_s": 2}
HELLO_TIMEOUT = 10.0
ASK_TIMEOUT = 25.0
TICK = 15.0
FRAME_IN_MAX = 4096
SEND_MAX_BYTES = 16384
SEND_MAX_MESSAGES = 20
POLL_PAGE = 50
ONLINE_POLL_WINDOW = 60
CAPS = {"text", "cards", "alarms", "reminders", "notes", "timers", "focus", "inbox", "confirm", "mic", "speaker",
        "stream", "ota"}
PUSH_ACTIONS = ("note.create", "reminder.create", "alarm.set", "timer.start", "focus.start", "answer.show",
                "item.delete")
DEVICE_ITEM_ACTIONS = ("note.create", "reminder.create", "alarm.set", "timer.start", "focus.start", "answer.show")
ITEM_STATES = ("rang", "dismissed", "snoozed", "done", "deleted", "accepted", "rejected")
EVENT_KINDS = ("boop", "wake", "sleep", "face_down", "focus_done")
_CID = re.compile(r"^[0-9a-f]{16}$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _err(code: str, msg: str = "", re_: Any = None, retry_ms: Optional[int] = None, **extra: Any) -> dict:
    m: Dict[str, Any] = {"v": 1, "t": "error", "code": code, "msg": msg or code}
    if re_ is not None:
        m["re"] = re_
    if retry_ms is not None:
        m["retry_ms"] = int(retry_ms)
    m.update(extra)
    return m


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


class Session:
    """One authenticated transport context (a WebSocket, or one long-poll request)."""

    def __init__(self, ctx: DeviceCtx, transport: str, ip: str, out: Callable[[dict], Awaitable[None]]):
        self.ctx = ctx
        self.transport = transport
        self.ip = ip
        self.out = out
        self.aborted: Set[str] = set()
        self.hello = False


class Conn(Session):
    def __init__(self, ctx: DeviceCtx, ip: str, ws: WebSocket, loop: asyncio.AbstractEventLoop):
        super().__init__(ctx, "ws", ip, self._send)
        self.ws = ws
        self.loop = loop
        self.send_lock = asyncio.Lock()
        self.flush_lock = asyncio.Lock()
        self.sent_upto = 0
        self.replay_done = False
        self.close_code: Optional[int] = None
        self.close_event = asyncio.Event()
        self.tasks: Set[asyncio.Task] = set()

    async def _send(self, msg: dict) -> None:
        if self.close_code is not None:
            return
        async with self.send_lock:
            await self.ws.send_text(json.dumps(msg, ensure_ascii=False, separators=(",", ":")))

    def request_close(self, code: int) -> None:
        """Thread-safe: ask the receive loop to close the socket with `code`."""
        def _do() -> None:
            if self.close_code is None:
                self.close_code = code
            self.close_event.set()
        self.loop.call_soon_threadsafe(_do)

    def spawn(self, coro: Awaitable[Any]) -> None:
        t = asyncio.ensure_future(coro)
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)


class Gateway:
    def __init__(self, soul: Any, store: Optional[DeviceStore] = None, relay: Optional[Relay] = None,
                 clock: Callable[[], float] = time.time):
        env = os.environ.get("SOUL_ENV", "dev")
        self.store = store or DeviceStore(clock=clock)
        if env == "production":
            if self.store.policy != "factory":
                raise RuntimeError("SOUL_ENV=production requires SOUL_ENROL_POLICY=factory")
            if not os.environ.get("SOUL_PUBLIC_HOST"):
                raise RuntimeError("SOUL_ENV=production requires SOUL_PUBLIC_HOST")
        self.soul = soul
        self.relay = relay or Relay(soul, self.store)
        self.clock = self.store.clock
        self.conns: Dict[str, Conn] = {}
        self._control: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=20))
        self._pollers: Dict[str, List[Tuple[asyncio.AbstractEventLoop, asyncio.Event]]] = defaultdict(list)
        self._waiters: Dict[Tuple[str, int], threading.Event] = {}
        self._last_poll: Dict[str, float] = {}
        self._sent_code: Dict[str, Optional[str]] = {}
        self._flaps: Dict[str, Deque[Tuple[float, str]]] = defaultdict(deque)
        self._lock = threading.RLock()
        self.on_inbox: List[Callable[[str, dict], None]] = []
        self.on_connectors: List[Callable[[str, bool], None]] = []
        self.models = {"claude": os.environ.get("SOUL_B1_CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL),
                       "openai": os.environ.get("SOUL_B1_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)}

    def __repr__(self) -> str:
        return f"Gateway({self.store!r}, online={len(self.conns)})"

    # ============================================================ public API ==
    def is_online(self, device_id: str) -> bool:
        if device_id in self.conns:
            return True
        return self.clock() - self._last_poll.get(device_id, 0) <= ONLINE_POLL_WINDOW

    def push(self, device_id: str, action: str, args: dict, item_id: str, origin: dict, say: Optional[str] = None,
             private: bool = False, needs_accept: bool = False, expires_at: Optional[int] = None) -> int:
        """Queue a push for a paired device and deliver it at once if it is online. Thread-safe."""
        check_device_id(device_id)
        if action not in PUSH_ACTIONS:
            raise ValueError(f"unknown push action {action}")
        if not self.store.owner(device_id):
            raise ValueError("device is not paired")
        if not isinstance(origin, dict) or origin.get("kind") not in ("connector", "shortcut", "app", "turn", "device"):
            raise ValueError("origin.kind must be connector|shortcut|app|turn|device")
        seq = self.store.enqueue(device_id, action, args, item_id, origin, say=say, private=private,
                                 needs_accept=needs_accept, expires_at=expires_at)
        with self._lock:
            self._waiters.setdefault((device_id, seq), threading.Event())
        self.notify(device_id)
        return seq

    def _delivery(self, device_id: str, seq: int) -> str:
        st = self.store.push_status(device_id, seq)
        if st and st["acked"] and st["ok"]:
            return "pending_accept" if st["needs_accept"] else "shown"
        return "queued"

    def wait_delivery(self, device_id: str, seq: int, timeout: float = 3.0) -> str:
        """Block (sync callers) until the device acks `seq` or `timeout` passes."""
        with self._lock:
            ev = self._waiters.setdefault((device_id, seq), threading.Event())
        if self._delivery(device_id, seq) == "queued":
            ev.wait(timeout)
        with self._lock:
            self._waiters.pop((device_id, seq), None)
        return self._delivery(device_id, seq)

    async def push_and_wait(self, device_id: str, seq: int, timeout: float = 3.0) -> str:
        return await asyncio.to_thread(self.wait_delivery, device_id, seq, timeout)

    def forecast(self, device_id: str, due_local: str) -> str:
        """Will SOUL have an item due at `due_local` (device local time) in time? yes | no | unknown."""
        if self.is_online(device_id):
            return "yes"
        d = self.store.get_device(device_id)
        if not d:
            return "no"
        try:
            due = dt.datetime.strptime(due_local, "%Y-%m-%dT%H:%M").replace(
                tzinfo=ZoneInfo(d.get("tz") or DEFAULT_TZ)).timestamp()
        except (ValueError, TypeError):
            return "unknown"
        now = self.clock()
        if d.get("wake_at") and (d.get("last_seen") or 0) >= now - 3600:
            return "yes" if d["wake_at"] <= due - 60 else "no"
        if not d.get("last_seen") or d["last_seen"] < now - 24 * 3600:
            return "no"
        return "unknown"

    def claim(self, account_id: str, first_name: str, email: str, code: Any, ip: str) -> dict:
        res = self.store.claim(account_id, first_name, email, code, ip)
        msg = res.pop("_device_msg")
        self.control(res["device"]["id"], msg)
        return res

    def claim_state(self, pid: str, account_id: str) -> dict:
        return self.store.claim_state(pid, account_id)

    def unpair(self, device_id: str, reason: str = "user", erase: bool = False) -> Optional[str]:
        old = self.store.unpair(device_id, reason, erase=erase)
        if erase:
            try:
                self.soul.state.wipe(device_id)
            except (ValueError, AttributeError):
                pass
        msg = {"v": 1, "t": "unpaired", "reason": reason}
        conn = self.conns.get(device_id)
        if conn is not None:
            async def _send_close() -> None:
                await conn.out(msg)
                conn.request_close(4401)  # tokens are revoked: re-auth, then a fresh `pairing`
            conn.loop.call_soon_threadsafe(lambda: conn.spawn(_send_close()))
        else:
            self._queue(device_id, msg)
        return old

    def send_config(self, device_id: str, **fields: Any) -> dict:
        """Persist settings and push a `config` message (brain, voice, lang, name, tz, quiet, models)."""
        upd: Dict[str, Any] = {}
        msg: Dict[str, Any] = {"v": 1, "t": "config"}
        for k, v in fields.items():
            if k == "brain":
                if v not in BRAINS:
                    raise ValueError("bad brain")
                upd["brain"] = msg["brain"] = v
            elif k == "voice":
                if v not in VOICES:
                    raise ValueError("bad voice")
                upd["voice"] = msg["voice"] = v
            elif k == "lang":
                if v not in ("ro", "en"):
                    raise ValueError("bad lang")
                upd["lang"] = msg["lang"] = v
            elif k == "name":
                upd["name"] = msg["name"] = str(v)[:24]
            elif k == "tz":
                ZoneInfo(v)
                upd["tz"] = msg["tz"] = v
                msg["posix_tz"] = posix_tz(v)
            elif k == "quiet":
                if not (isinstance(v, dict) and _HHMM.match(str(v.get("from"))) and _HHMM.match(str(v.get("to")))):
                    raise ValueError("quiet must be {from: HH:MM, to: HH:MM}")
                upd["quiet_from"], upd["quiet_to"] = v["from"], v["to"]
                msg["quiet"] = {"from": v["from"], "to": v["to"]}
            elif k == "models":
                msg["models"] = dict(v)
            else:
                raise ValueError(f"unknown config field {k}")
        self.store.update_device(device_id, **upd)
        self.control(device_id, msg)
        return msg

    def inbox(self, device_id: str, state: Optional[str] = "pending") -> List[dict]:
        return self.store.inbox_list(device_id, state)

    def inbox_answered(self, device_id: str, item_id: str) -> bool:
        ok = self.store.inbox_answer(device_id, item_id)
        if ok:
            self.control(device_id, {"v": 1, "t": "inbox.state", **self.store.inbox_counts(device_id)})
        return ok

    # ======================================================== delivery core ==
    def notify(self, device_id: str) -> None:
        """New pushes for this device: flush its socket, wake its long-polls. Thread-safe."""
        conn = self.conns.get(device_id)
        if conn is not None and conn.replay_done:
            conn.loop.call_soon_threadsafe(lambda: conn.spawn(self._flush(conn)))
        self._wake_pollers(device_id)

    def _wake_pollers(self, device_id: str) -> None:
        with self._lock:
            waiters = list(self._pollers.get(device_id, []))
        for loop, ev in waiters:
            loop.call_soon_threadsafe(ev.set)

    def _queue(self, device_id: str, msg: dict) -> None:
        with self._lock:
            q = self._control[device_id]
            if msg["t"] in ("pairing", "inbox.state"):  # a newer one replaces the old one
                for old in [m for m in q if m["t"] == msg["t"]]:
                    q.remove(old)
            q.append(msg)
        self._wake_pollers(device_id)

    def control(self, device_id: str, msg: dict) -> None:
        """Send a non-sequenced message (pairing, pair.confirm, paired, unpaired, config, inbox.state). Thread-safe."""
        conn = self.conns.get(device_id)
        if conn is not None and conn.replay_done:
            if msg["t"] == "pairing":
                self._sent_code[device_id] = self.store.code_id(device_id)
            conn.loop.call_soon_threadsafe(lambda: conn.spawn(conn.out(msg)))
        else:
            self._queue(device_id, msg)

    def _drain(self, device_id: str) -> List[dict]:
        with self._lock:
            q = self._control.pop(device_id, None)
        msgs = list(q or [])
        for m in msgs:
            if m["t"] == "pairing":
                self._sent_code[device_id] = self.store.code_id(device_id)
        return msgs

    async def _flush(self, conn: Conn) -> None:
        async with conn.flush_lock:
            if self.store.device_state(conn.ctx) != "paired":
                return
            while True:
                msgs, more = self.store.replay(conn.ctx.device_id, conn.sent_upto, POLL_PAGE)
                for m in msgs:
                    await conn.out(m)
                    conn.sent_upto = max(conn.sent_upto, m["seq"])
                if not more:
                    break

    def _pairing_msgs(self, device_id: str, force_new: bool = False) -> List[dict]:
        """The `pairing` message if the device has not seen its current code yet (rotates expired codes)."""
        msg = self.store.current_code(device_id, force_new=force_new)
        cid = self.store.code_id(device_id)
        if force_new or self._sent_code.get(device_id) != cid:
            self._sent_code[device_id] = cid
            return [msg]
        return []

    def _tick(self) -> None:
        for dev in self.store.expire_claims():
            self.control(dev, self.store.current_code(dev, force_new=True))
        self.store.expire_cards()

    # ============================================================== welcome ==
    def welcome(self, ctx: DeviceCtx, state: str) -> dict:
        d = self.store.get_device(ctx.device_id) or {}
        tz = d.get("tz") or DEFAULT_TZ
        paired = state == "paired"
        trial = self.store.trial(ctx.device_id, state)
        if paired:
            brain = d.get("brain") or "cloud"
        else:
            brain = "cloud" if trial and trial["left"] > 0 else "none"
        allowance = None
        if paired and brain == "cloud" and d.get("account_id"):
            allowance = self.relay.meter.allowance(d["account_id"])
        return {
            "v": 1, "t": "welcome", "server_time": int(self.clock()), "tz": tz, "posix_tz": posix_tz(tz),
            "state": state, "owner": d.get("owner_name", "") if paired else "", "brain": brain,
            "voice": d.get("voice") or "claude", "lang": d.get("lang") or "ro",
            "quiet": {"from": d.get("quiet_from") or "22:00", "to": d.get("quiet_to") or "07:00"},
            "connectors_paused": bool(d.get("connectors_paused")), "limits": dict(LIMITS),
            "allowance": allowance, "trial": trial, "models": dict(self.models),
        }

    # ============================================================= handlers ==
    async def handle(self, s: Session, m: Any) -> None:
        if not isinstance(m, dict):
            return
        t = m.get("t")
        if m.get("v", 1) != 1:
            await s.out(_err("invalid", "unsupported envelope version", m.get("id")))
            return
        fn = self._HANDLERS.get(t) if isinstance(t, str) else None
        if fn is None:
            return  # must-ignore
        await fn(self, s, m)

    async def _h_hello(self, s: Session, m: dict) -> None:
        dev = s.ctx.device_id
        proto = m.get("proto")
        if isinstance(proto, list) and proto and not any(p in PROTO_VERSIONS for p in proto):
            if isinstance(s, Conn):
                s.request_close(4426)
            else:
                await s.out(_err("invalid", "protocol version unsupported"))
            return
        state = self.store.device_state(s.ctx)
        upd: Dict[str, Any] = {"last_seen": int(self.clock())}
        if isinstance(m.get("fw"), str):
            upd["fw"] = m["fw"][:24]
        if isinstance(m.get("hw"), str):
            upd["hw"] = m["hw"][:24]
        if isinstance(m.get("caps"), list):
            upd["caps"] = [c for c in m["caps"] if c in CAPS]
        if m.get("power") in ("usb", "battery"):
            upd["power"] = m["power"]
        if m.get("brain_local") in BRAINS:
            upd["brain_local"] = m["brain_local"]
        if isinstance(m.get("tz_posix"), str):
            upd["tz_hint"] = m["tz_posix"][:64]
        if state != "paired" and m.get("lang") in ("ro", "en"):
            upd["lang"] = m["lang"]
        upd["wake_at"] = None
        self.store.update_device(dev, **upd)
        s.hello = True

        after = m.get("after") if _is_int(m.get("after")) and m["after"] >= 0 else 0
        last = self.store.last_seq(dev)
        await s.out(self.welcome(s.ctx, state))
        if after > last:
            await s.out({"v": 1, "t": "resync", "last": last})
            after = last
        if state == "paired":
            self.store.ack_upto(dev, after)
            self._release_waiters(dev)
        if isinstance(s, Conn):
            s.sent_upto = after
            if state == "paired":
                await self._flush(s)
            await s.out({"v": 1, "t": "replay.done", "last": self.store.last_seq(dev)})
            s.replay_done = True
            for cm in self._drain(dev):
                await s.out(cm)
        else:
            # long-poll: control messages and pushes come with the next poll
            pass
        if state == "paired":
            await s.out({"v": 1, "t": "inbox.state", **self.store.inbox_counts(dev)})
        else:
            for pm in self._pairing_msgs(dev, force_new=False):
                await s.out(pm)

    async def _h_ask(self, s: Session, m: dict) -> None:
        dev = s.ctx.device_id
        mid = m.get("id") if isinstance(m.get("id"), str) and len(m["id"]) <= 24 else None
        text = m.get("text")
        if mid is None or not isinstance(text, str) or not (1 <= len(text.strip()) <= 2000):
            await s.out(_err("invalid", "ask needs id (<= 24) and text (1..2000)", mid))
            return
        for key, cap, per_s in ((f"ask:min:{dev}", LIMITS["ask_per_min"], LIMITS["ask_per_min"] / 60),
                                (f"ask:day:{dev}", LIMITS["ask_per_day"], LIMITS["ask_per_day"] / 86400)):
            wait = self.store.buckets.take(key, cap, per_s)
            if wait is not None:
                await s.out(_err("rate_limited", "too many questions, try in a minute", mid, retry_ms=wait))
                return
        if isinstance(s, Conn):
            s.spawn(self._run_ask(s, m, mid))
        else:
            await self._run_ask(s, m, mid)

    async def _run_ask(self, s: Session, m: dict, mid: str) -> None:
        dev = s.ctx.device_id
        state = self.store.device_state(s.ctx)
        try:
            res = await asyncio.wait_for(asyncio.to_thread(self.relay.answer, dev, state, m), ASK_TIMEOUT)
        except asyncio.TimeoutError:
            await s.out(_err("timeout", "the answer took too long", mid))
            return
        except Exception:  # noqa: BLE001 - never leak internals to the device
            log.exception("relay failed")
            await s.out(_err("upstream", "the brain failed", mid))
            return
        if res.get("seqs"):
            self._wake_pollers(dev)
            if isinstance(s, Conn) and s.replay_done:
                await self._flush(s)
        if mid in s.aborted:
            return
        if "error" in res:
            await s.out(_err(res["error"]["code"], res["error"]["msg"], mid))
            return
        await s.out(res["reply"])

    async def _h_abort(self, s: Session, m: dict) -> None:
        if isinstance(m.get("re"), str):
            s.aborted.add(m["re"][:24])

    async def _h_ack(self, s: Session, m: dict) -> None:
        if not _is_int(m.get("seq")) or not isinstance(m.get("ok"), bool):
            return
        err = m.get("err") if m.get("err") in ("unsupported", "invalid", "full", "paused") else None
        if self.store.device_state(s.ctx) != "paired":
            return
        if self.store.ack(s.ctx.device_id, m["seq"], m["ok"], err) is not None:
            with self._lock:
                ev = self._waiters.get((s.ctx.device_id, m["seq"]))
            if ev:
                ev.set()

    def _release_waiters(self, device_id: str) -> None:
        with self._lock:
            evs = [ev for (d, _), ev in self._waiters.items() if d == device_id]
        for ev in evs:
            ev.set()

    async def _require_paired(self, s: Session, m: dict) -> bool:
        if self.store.device_state(s.ctx) != "paired":
            await s.out(_err("unpaired", "pair SOUL first", m.get("id"), cid=m.get("cid")))
            return False
        return True

    def _item_rate(self, dev: str) -> Optional[int]:
        return self.store.buckets.take(f"items:{dev}", 60, 1.0)

    async def _h_item_add(self, s: Session, m: dict) -> None:
        dev = s.ctx.device_id
        cid, action, args = m.get("cid"), m.get("action"), m.get("args")
        if not (isinstance(cid, str) and _CID.match(cid)) or action not in DEVICE_ITEM_ACTIONS \
                or not isinstance(args, dict):
            await s.out(_err("invalid", "item.add needs cid (16 hex), a known action and args", m.get("id"),
                             cid=cid if isinstance(cid, str) else None))
            return
        if not await self._require_paired(s, m):
            return
        known = self.store.cid_item(dev, cid)
        if known:
            await s.out({"v": 1, "t": "added", "cid": cid, "item_id": known})
            return
        wait = self._item_rate(dev)
        if wait is not None:
            await s.out(_err("rate_limited", "too many items", m.get("id"), retry_ms=wait, cid=cid))
            return
        a = dict(args)
        if action == "answer.show":
            title, body = str(a.get("title", "")), str(a.get("body", ""))
            a = {"say": (title or body or "…")[:400], "title": title[:60], "body": body[:600]}
        d = self.store.get_device(dev) or {}
        lang = d.get("lang") if d.get("lang") in ("ro", "en") else "en"
        r = self.soul.action(dev, action, a, lang=lang, source="device")
        if not r.ok:
            await s.out(_err("invalid", r.error[:200], m.get("id"), cid=cid))
            return
        item_id = f"it_{r.id}"
        self.store.remember_cid(dev, cid, item_id)
        await s.out({"v": 1, "t": "added", "cid": cid, "item_id": item_id})

    async def _h_item_state(self, s: Session, m: dict) -> None:
        dev = s.ctx.device_id
        state, at = m.get("state"), m.get("at")
        item_id = m.get("item_id") if isinstance(m.get("item_id"), str) else None
        if item_id is None and isinstance(m.get("cid"), str):
            item_id = self.store.cid_item(dev, m["cid"])
        if state not in ITEM_STATES or not item_id or len(item_id) > 32:
            await s.out(_err("invalid", "item.state needs item_id or a known cid, and a state", m.get("id")))
            return
        if self.store.device_state(s.ctx) != "paired":
            return
        self.store.set_item_state(dev, item_id, state, at if _is_int(at) else int(self.clock()))
        st = self.soul.state
        try:
            if hasattr(st, "set_state"):
                st.set_state(dev, item_id, state)
            elif state in ("rang", "dismissed", "done", "deleted") and item_id.startswith("it_") \
                    and item_id[3:].isdigit():
                st.mark_done(dev, int(item_id[3:]))
        except (ValueError, TypeError):
            pass

    async def _h_inbox_add(self, s: Session, m: dict) -> None:
        dev = s.ctx.device_id
        cid, text, to = m.get("cid"), m.get("text"), m.get("to")
        if not (isinstance(cid, str) and _CID.match(cid)) or not isinstance(text, str) \
                or not (1 <= len(text.strip()) <= 1000) or to not in ("claude", "chatgpt", "any"):
            await s.out(_err("invalid", "inbox.add needs cid, text (1..1000) and to", m.get("id"),
                             cid=cid if isinstance(cid, str) else None))
            return
        if not await self._require_paired(s, m):
            return
        known = self.store.cid_item(dev, cid)
        if known:
            await s.out({"v": 1, "t": "added", "cid": cid, "item_id": known})
            return
        wait = self._item_rate(dev)
        if wait is not None:
            await s.out(_err("rate_limited", "too many items", m.get("id"), retry_ms=wait, cid=cid))
            return
        item_id = self.store.inbox_add(dev, cid, text.strip(), to)
        await s.out({"v": 1, "t": "added", "cid": cid, "item_id": item_id})
        await s.out({"v": 1, "t": "inbox.state", **self.store.inbox_counts(dev)})
        for fn in self.on_inbox:
            try:
                fn(dev, {"item_id": item_id, "to": to})
            except Exception:  # noqa: BLE001
                log.exception("inbox hook failed")

    async def _h_pair(self, s: Session, m: dict) -> None:
        dev = s.ctx.device_id
        ok = m.get("t") == "pair.ok"
        paired = self.store.on_device_answer(s.ctx, m.get("pid"), ok)
        if paired:
            await s.out(paired)
            if isinstance(s, Conn):
                await self._flush(s)
            await s.out({"v": 1, "t": "inbox.state", **self.store.inbox_counts(dev)})
            return
        if self.store.device_state(s.ctx) != "paired":
            for pm in self._pairing_msgs(dev, force_new=True):
                await s.out(pm)

    async def _h_connectors(self, s: Session, m: dict) -> None:
        if isinstance(m.get("paused"), bool) and self.store.device_state(s.ctx) == "paired":
            self.store.update_device(s.ctx.device_id, connectors_paused=1 if m["paused"] else 0)
            for fn in self.on_connectors:
                try:
                    fn(s.ctx.device_id, m["paused"])
                except Exception:  # noqa: BLE001
                    log.exception("connectors hook failed")

    async def _h_sleep(self, s: Session, m: dict) -> None:
        if _is_int(m.get("wake_at")):
            self.store.update_device(s.ctx.device_id, wake_at=m["wake_at"], awake=0, last_seen=int(self.clock()))

    async def _h_status(self, s: Session, m: dict) -> None:
        upd: Dict[str, Any] = {"last_seen": int(self.clock())}
        if _is_int(m.get("rssi")):
            upd["rssi"] = m["rssi"]
        if _is_int(m.get("battery")) and 0 <= m["battery"] <= 100:
            upd["battery"] = m["battery"]
        if m.get("power") in ("usb", "battery"):
            upd["power"] = m["power"]
        if isinstance(m.get("fw"), str):
            upd["fw"] = m["fw"][:24]
        if _is_int(m.get("free_heap")):
            upd["free_heap"] = m["free_heap"]
        if isinstance(m.get("awake"), bool):
            upd["awake"] = 1 if m["awake"] else 0
        self.store.update_device(s.ctx.device_id, **upd)

    async def _h_event(self, s: Session, m: dict) -> None:
        evs = m.get("events")
        if not isinstance(evs, list):
            return
        ok = [(e["kind"], e["at"]) for e in evs[:20]
              if isinstance(e, dict) and e.get("kind") in EVENT_KINDS and _is_int(e.get("at"))]
        if ok:
            self.store.add_events(s.ctx.device_id, ok)

    _HANDLERS: Dict[str, Callable[["Gateway", Session, dict], Awaitable[None]]] = {
        "hello": _h_hello, "ask": _h_ask, "abort": _h_abort, "ack": _h_ack, "item.add": _h_item_add,
        "item.state": _h_item_state, "inbox.add": _h_inbox_add, "pair.ok": _h_pair, "pair.no": _h_pair,
        "connectors": _h_connectors, "sleep": _h_sleep, "status": _h_status, "event": _h_event,
    }

    # ============================================================ WebSocket ==
    def _register(self, conn: Conn) -> None:
        dev = conn.ctx.device_id
        with self._lock:
            old = self.conns.get(dev)
            self.conns[dev] = conn
        if old is not None and old is not conn:
            old.request_close(4409)
            now = self.clock()
            q = self._flaps[dev]
            if old.ip != conn.ip:
                q.append((now, conn.ip))
            while q and q[0][0] < now - 3600:
                q.popleft()
            if len(q) > 3:
                self.store._alert("socket_flap", {"device_id": dev, "count": len(q)})  # noqa: SLF001
                q.clear()

    def _unregister(self, conn: Conn) -> None:
        with self._lock:
            if self.conns.get(conn.ctx.device_id) is conn:
                del self.conns[conn.ctx.device_id]

    async def ws_endpoint(self, ws: WebSocket) -> None:
        offered = ws.scope.get("subprotocols") or []
        if PROTOCOL not in offered:
            await ws.accept()
            await ws.close(4426)
            return
        await ws.accept(subprotocol=PROTOCOL)
        try:
            ctx = self.store.device_from_token(ws.headers.get("authorization"))
        except GatewayError:
            await ws.close(4401)
            return
        ip = _client_ip(ws)
        conn = Conn(ctx, ip, ws, asyncio.get_running_loop())
        self._register(conn)
        recv: Optional[asyncio.Future] = None
        closer = asyncio.ensure_future(conn.close_event.wait())
        deadline = time.monotonic() + HELLO_TIMEOUT
        try:
            while True:
                if recv is None:
                    recv = asyncio.ensure_future(ws.receive())
                timeout = max(0.05, deadline - time.monotonic()) if not conn.hello else TICK
                done, _ = await asyncio.wait({recv, closer}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
                if closer in done:
                    break
                if not done:
                    if not conn.hello:
                        conn.close_code = 4400
                        break
                    self._tick()
                    if self.store.device_state(conn.ctx) != "paired":
                        for pm in self._pairing_msgs(ctx.device_id):
                            await conn.out(pm)
                    continue
                msg = recv.result()
                recv = None
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("text") is None:
                    continue  # binary frames: Phase 2 audio
                code = await self._ws_frame(conn, msg["text"])
                if code:
                    conn.close_code = code
                    break
        except Exception:  # noqa: BLE001 - a broken socket must not take the hub down
            log.exception("websocket loop failed")
        finally:
            for f in (recv, closer):
                if f is not None and not f.done():
                    f.cancel()
            self._unregister(conn)
            code = conn.close_code
            conn.close_code = conn.close_code or 1000
            if code:
                try:
                    await ws.close(code)
                except Exception:  # noqa: BLE001 - already closed
                    pass

    async def _ws_frame(self, conn: Conn, text: str) -> Optional[int]:
        dev = conn.ctx.device_id
        wait = self.store.buckets.take(f"frames:{dev}", 10, LIMITS["frames_per_s"])
        if wait is not None:
            await conn.out(_err("rate_limited", "too many frames", retry_ms=max(wait, 30000)))
            return 4429
        if len(text.encode("utf-8")) > FRAME_IN_MAX:
            await conn.out(_err("too_big", "frame over 4 KB"))
            return None
        try:
            m = json.loads(text)
        except json.JSONDecodeError:
            return 4400
        if not isinstance(m, dict):
            return 4400
        if not conn.hello and m.get("t") != "hello":
            return 4400
        self.store.touch(dev)
        await self.handle(conn, m)
        return conn.close_code if conn.close_event.is_set() else None

    # ============================================================ long-poll ==
    async def poll(self, ctx: DeviceCtx, after: int, wait: int) -> dict:
        dev = ctx.device_id
        self._last_poll[dev] = self.clock()
        self.store.touch(dev)
        self._tick()
        msgs, more = self._poll_batch(ctx, after)
        if not msgs and wait > 0:
            loop = asyncio.get_running_loop()
            ev = asyncio.Event()
            with self._lock:
                self._pollers[dev].append((loop, ev))
            try:
                await asyncio.wait_for(ev.wait(), wait)
            except asyncio.TimeoutError:
                pass
            finally:
                with self._lock:
                    self._pollers[dev] = [w for w in self._pollers[dev] if w[1] is not ev]
            self._last_poll[dev] = self.clock()
            msgs, more = self._poll_batch(ctx, after)
        return {"messages": msgs, "more": more}

    def _poll_batch(self, ctx: DeviceCtx, after: int) -> Tuple[List[dict], bool]:
        dev = ctx.device_id
        msgs = self._drain(dev)
        state = self.store.device_state(ctx)
        more = False
        if state == "paired":
            last = self.store.last_seq(dev)
            if after > last:
                msgs.append({"v": 1, "t": "resync", "last": last})
                after = last
            pushes, more = self.store.replay(dev, after, POLL_PAGE)
            msgs += pushes
        else:
            msgs = [m for m in msgs if m["t"] != "pairing"] + self._pairing_msgs(dev)
        return msgs, more

    async def send(self, ctx: DeviceCtx, messages: List[Any], ip: str) -> dict:
        out: List[dict] = []

        async def collect(msg: dict) -> None:
            out.append(msg)

        self._last_poll[ctx.device_id] = self.clock()
        self.store.touch(ctx.device_id)
        s = Session(ctx, "poll", ip, collect)
        for m in messages:
            if isinstance(m, dict) and len(json.dumps(m, ensure_ascii=False).encode()) > FRAME_IN_MAX:
                out.append(_err("too_big", "message over 4 KB", m.get("id")))
                continue
            await self.handle(s, m)
        return {"messages": out}


# ================================================================= router ==

def _client_ip(conn: Any) -> str:
    if os.environ.get("SOUL_TRUST_PROXY") == "1":
        fwd = conn.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return conn.client.host if conn.client else "-"


def _error_response(e: GatewayError) -> JSONResponse:
    headers = {}
    if e.status == 429 and e.retry_ms is not None:
        headers["Retry-After"] = str(max(1, (int(e.retry_ms) + 999) // 1000))
    return JSONResponse(status_code=e.status, content=e.body(), headers=headers)


def _guard(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except GatewayError as e:
            return _error_response(e)
    return wrapper


async def _json_body(request: Request, limit: int) -> Any:
    raw = await request.body()
    if len(raw) > limit:
        raise GatewayError(413, "too_big", f"body over {limit} bytes")
    try:
        return json.loads(raw or b"null")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise GatewayError(400, "bad_request", "body is not JSON") from None


def build_router(get_gw: Callable[[], Gateway]) -> APIRouter:
    """The public device routes. Production mounts this from app.py; dev mounts it in server.py."""
    r = APIRouter()

    @r.get("/v1/ping")
    async def ping() -> dict:
        return {"ok": True, "time": int(time.time())}

    @r.post("/v1/device/challenge")
    @_guard
    async def challenge(request: Request):
        body = await _json_body(request, 1024)
        if not isinstance(body, dict):
            raise GatewayError(400, "bad_request", "body must be a JSON object")
        return get_gw().store.issue_nonce(body.get("device_id"), _client_ip(request))

    @r.post("/v1/device/auth")
    @_guard
    async def auth(request: Request):
        body = await _json_body(request, 4096)
        return get_gw().store.authenticate(body, _client_ip(request))

    @r.get("/v1/device/poll")
    @_guard
    async def poll(request: Request, after: int = 0, wait: int = 0):
        gw = get_gw()
        ctx = gw.store.device_from_token(request.headers.get("authorization"))
        return await gw.poll(ctx, max(0, after), min(25, max(0, wait)))

    @r.post("/v1/device/send")
    @_guard
    async def send(request: Request):
        gw = get_gw()
        ctx = gw.store.device_from_token(request.headers.get("authorization"))
        body = await _json_body(request, SEND_MAX_BYTES)
        msgs = body.get("messages") if isinstance(body, dict) else None
        if not isinstance(msgs, list) or len(msgs) > SEND_MAX_MESSAGES:
            raise GatewayError(400, "bad_request", f"messages must be a list of <= {SEND_MAX_MESSAGES}")
        return await gw.send(ctx, msgs, _client_ip(request))

    @r.websocket("/v1/device/ws")
    async def ws(websocket: WebSocket):
        await get_gw().ws_endpoint(websocket)

    return r


def build_dev_router(get_gw: Callable[[], Gateway]) -> APIRouter:
    """Dev / self-host helpers behind the legacy shared token (server.py adds that dependency).

    They stand in for the account pages and the connector until those exist, so
    tools/fake_device.py can run the pairing and push flows end to end. Disabled
    when SOUL_ENV=production.
    """
    r = APIRouter(prefix="/v1/dev")

    def _gw() -> Gateway:
        if os.environ.get("SOUL_ENV") == "production":
            raise GatewayError(404, "not_found", "not available")
        return get_gw()

    @r.post("/pair/claim")
    @_guard
    async def claim(request: Request):
        b = await _json_body(request, 2048)
        if not isinstance(b, dict):
            raise GatewayError(400, "bad_request", "body must be a JSON object")
        res = _gw().claim(str(b.get("account_id", "acc_dev")), str(b.get("first_name", "Dev")),
                          str(b.get("email", "dev@example.com")), b.get("code"), _client_ip(request))
        return JSONResponse(status_code=202, content=res)

    @r.get("/pair/{pid}")
    @_guard
    async def claim_state(pid: str, account_id: str = "acc_dev"):
        return _gw().claim_state(pid, account_id)

    @r.post("/push")
    @_guard
    async def push(request: Request):
        b = await _json_body(request, 8192)
        if not isinstance(b, dict):
            raise GatewayError(400, "bad_request", "body must be a JSON object")
        gw = _gw()
        try:
            seq = gw.push(str(b.get("device_id")), str(b.get("action")), dict(b.get("args") or {}),
                          str(b.get("item_id") or f"dev_{int(time.time() * 1000) % 10**10}"),
                          dict(b.get("origin") or {"kind": "connector", "app": "claude"}), say=b.get("say"),
                          private=bool(b.get("private")), needs_accept=bool(b.get("needs_accept")))
        except ValueError as e:
            raise GatewayError(422, "invalid", str(e)) from None
        return {"seq": seq, "delivered": await gw.push_and_wait(str(b["device_id"]), seq, 3.0)}

    @r.post("/unpair")
    @_guard
    async def unpair(request: Request):
        b = await _json_body(request, 1024)
        if not isinstance(b, dict):
            raise GatewayError(400, "bad_request", "body must be a JSON object")
        dev = check_device_id(b.get("device_id"))
        _gw().unpair(dev, "user", erase=bool(b.get("erase")))
        return {"ok": True}

    @r.post("/config")
    @_guard
    async def config(request: Request):
        b = await _json_body(request, 2048)
        if not isinstance(b, dict):
            raise GatewayError(400, "bad_request", "body must be a JSON object")
        dev = check_device_id(b.pop("device_id", None))
        try:
            return _gw().send_config(dev, **b)
        except (ValueError, KeyError) as e:
            raise GatewayError(422, "invalid", str(e)) from None

    return r


_default: Optional[Gateway] = None
_default_lock = threading.Lock()


def default_gateway(soul_getter: Callable[[], Any]) -> Gateway:
    """The process-wide gateway for server.py (dev / self-host): state in SOUL_GATEWAY_DB or <data_dir>/gateway.sqlite."""
    global _default
    with _default_lock:
        if _default is None:
            soul = soul_getter()
            path = os.environ.get("SOUL_GATEWAY_DB") or os.path.join(soul.settings.data_dir, "gateway.sqlite")
            _default = Gateway(soul, DeviceStore(path))
        return _default
