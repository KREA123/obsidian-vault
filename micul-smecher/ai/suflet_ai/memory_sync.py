"""SOUL Memory in the cloud (docs/10-SOUL-MEMORY.md §5-6).

The memory lives ON the device; the cloud only ever sees it in two ways:

1. Per turn, the device sends a compact "What SOUL knows about you" block in `ask.ctx.memory` (<= 1500
   characters). The relay puts it in the user turn as data, never in the system prompt, never stored.
   The relay's model gets two extra tools, `memory_remember` / `memory_forget`; their calls do not touch
   any cloud store: they come back to the device in `reply.memory` ([{op, text, kind?, importance?}]) and SOUL
   validates them again before it keeps anything (secrets are refused on both sides). SOUL Bridge answers
   may carry the same `memory` list.

2. An optional backup, OFF by default, switched on only on the device (Settings > Memory > Backup): the
   device sends its export JSON in `memory.backup` parts; the cloud keeps ONE copy per device, encrypted at
   rest (Fernet, a key derived with HKDF from the master secret and bound to the device id, like the BYOK
   keys in keystore.py). The owner sees it on /me (facts, export as JSON, delete); switching backup off on
   SOUL (`memory.backup {"off": true}`), unpairing with erase, or the GDPR account delete removes it.

Honest limit: this is encryption at rest, not end-to-end: the server can decrypt it to show it on /me.
"""
from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAX_FACTS = 512
MAX_TEXT = 120
MAX_BLOCK = 1500
MAX_PARTS = 40
MAX_PART = 8000
MAX_BACKUP_BYTES = 200_000
KINDS = ("person", "preference", "plan", "place", "note", "summary", "other")
_INFO = b"soul-memory-v1"

_SECRET_WORDS = re.compile(
    r"\b(password|passwords|passwd|parola|parolei|passcode|pin|pin code|cod pin|codul pin|cvv|cvc|card number|"
    r"numar card|numarul cardului|cnp|ssn|social security|api key|cheie api|cheia api|token|seed phrase|"
    r"secret code|cod secret|iban|security code|cod de securitate|login code|codul de acces|access code|otp)\b")
_FOLD = str.maketrans("ăâîșşțţĂÂÎȘŞȚŢ", "aaissttaaisstt")


def looks_secret(text: str) -> bool:
    """The device's SoulMemory::looksSecret: passwords, PINs, card numbers, API keys are never kept."""
    f = re.sub(r"[^a-z0-9]+", " ", text.translate(_FOLD).lower().replace("-", ""))
    if _SECRET_WORDS.search(f):
        return True
    if "sk-" in text:
        return True
    run = 0
    for c in text:
        if c.isdigit():
            run += 1
            if run >= 12:
                return True
        elif c not in " -":
            run = 0
    return False


def _clean(s: Any, cap: int) -> str:
    if not isinstance(s, str):
        return ""
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:cap]


def memory_block(dctx: Any) -> str:
    """The device's context block, sanitised (data for the model, not instructions)."""
    if not isinstance(dctx, dict) or not isinstance(dctx.get("memory"), str):
        return ""
    lines = [re.sub(r"[\x00-\x09\x0b-\x1f\x7f]+", " ", ln).strip() for ln in dctx["memory"][:MAX_BLOCK].split("\n")]
    return "\n".join(ln for ln in lines if ln)


# ------------------------------------------------------------------ the relay's memory tools --

def _tool_schema(forget: bool) -> dict:
    props: Dict[str, Any] = {"text": {"type": "string"}}
    if not forget:
        props["kind"] = {"type": "string", "enum": list(KINDS)}
        props["importance"] = {"type": "integer"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_REMEMBER_DESC = ("Ask SOUL to keep one durable fact about the owner in its on-device memory (people and pets, "
                  "birthdays, preferences, ongoing plans), in the owner's words ('My sister is Ana'), <= 120 "
                  "characters, importance 1-5. Never passwords, codes, card or ID numbers, health, religion, "
                  "politics or sexuality unless the owner explicitly asks. SOUL shows 'Remembered' with undo.")
_FORGET_DESC = "Ask SOUL to forget the facts in its on-device memory that contain this keyword (>= 3 characters)."


def claude_memory_tools() -> List[dict]:
    return [{"name": "memory_remember", "description": _REMEMBER_DESC, "input_schema": _tool_schema(False), "strict": True},
            {"name": "memory_forget", "description": _FORGET_DESC, "input_schema": _tool_schema(True), "strict": True}]


def openai_memory_tools() -> List[dict]:
    return [{"type": "function", "name": "memory_remember", "description": _REMEMBER_DESC,
             "parameters": _tool_schema(False), "strict": True},
            {"type": "function", "name": "memory_forget", "description": _FORGET_DESC,
             "parameters": _tool_schema(True), "strict": True}]


MEMORY_TOOL_NAMES = ("memory_remember", "memory_forget")


def memory_op(name: str, args: Any) -> Optional[dict]:
    """A validated op for the device, or None. Mirrors AiProtocol.cpp validMemOp."""
    if not isinstance(args, dict):
        return None
    if name == "memory_forget":
        text = _clean(args.get("text"), 80)
        return {"op": "forget", "text": text} if len(re.sub(r"[^a-z0-9]", "", text.lower())) >= 3 else None
    if name != "memory_remember":
        return None
    raw = args.get("text")
    if not isinstance(raw, str) or len(raw) > 400:
        return None
    text = _clean(raw, MAX_TEXT)
    if not text or looks_secret(text):
        return None
    op: Dict[str, Any] = {"op": "remember", "text": text}
    kind = args.get("kind")
    if kind is not None:
        if kind not in KINDS:
            return None
        op["kind"] = kind
    imp = args.get("importance")
    if imp is not None:
        if isinstance(imp, bool) or not isinstance(imp, (int, float)) or not 1 <= imp <= 5:
            return None
        op["importance"] = int(round(imp))
    return op


def clean_ops(raw: Any) -> List[dict]:
    """A `memory` list from a bridge answer ({op, text, kind?, importance?}) -> validated ops (at most 3)."""
    out: List[dict] = []
    if not isinstance(raw, list):
        return out
    for m in raw[:3]:
        if not isinstance(m, dict):
            continue
        name = {"remember": "memory_remember", "forget": "memory_forget"}.get(m.get("op"))
        op = memory_op(name or "", {k: v for k, v in m.items() if k != "op"})
        if op:
            out.append(op)
    return out


# ------------------------------------------------------------------------- the backup --

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_backup (
  device_id TEXT PRIMARY KEY,
  token BLOB NOT NULL,
  facts INTEGER NOT NULL,
  bytes INTEGER NOT NULL,
  gen INTEGER NOT NULL,
  updated INTEGER NOT NULL
);
"""


def validate_export(doc: Any) -> Optional[dict]:
    """The device's exportJson(): {"v": 1, "facts": [{id, kind, text, subject?, date?, importance, source,
    pinned, created, used?}]}. Returns a cleaned copy (secrets dropped) or None."""
    if not isinstance(doc, dict) or not isinstance(doc.get("facts"), list) or len(doc["facts"]) > MAX_FACTS:
        return None
    facts = []
    for f in doc["facts"]:
        if not isinstance(f, dict):
            continue
        text = _clean(f.get("text"), MAX_TEXT)
        if not text or looks_secret(text):
            continue
        c: Dict[str, Any] = {"text": text, "kind": f.get("kind") if f.get("kind") in KINDS else "other"}
        for k in ("id", "importance", "created", "used"):
            if isinstance(f.get(k), int) and not isinstance(f.get(k), bool) and 0 <= f[k] < 2**32:
                c[k] = f[k]
        if isinstance(f.get("subject"), str):
            c["subject"] = _clean(f["subject"], 32)
        if isinstance(f.get("date"), str) and re.fullmatch(r"\d{2}-\d{2}", f["date"]):
            c["date"] = f["date"]
        if f.get("source") in ("user", "ai", "rules", "cloud", "import"):
            c["source"] = f["source"]
        if isinstance(f.get("pinned"), bool):
            c["pinned"] = f["pinned"]
        facts.append(c)
    return {"v": 1, "kind": "soul-memory", "facts": facts}


class MemoryBackups:
    """One encrypted copy of each device's memory (only when the owner switched backup on, on SOUL)."""

    def __init__(self, store: Any, master_secret: bytes):
        if len(master_secret) < 32:
            raise ValueError("master secret too short")
        self.store = store
        self._master = master_secret
        store.executescript(_SCHEMA)
        self._parts: Dict[str, Dict[str, Any]] = {}

    def __repr__(self) -> str:
        return "MemoryBackups(<sealed>)"

    def _fernet(self, device_id: str) -> Fernet:
        k = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                 info=_INFO + b"|" + device_id.encode()).derive(self._master)
        return Fernet(base64.urlsafe_b64encode(k))

    # ---- the device's frames ----------------------------------------------------------------
    def frame(self, device_id: str, m: dict) -> Optional[str]:
        """One `memory.backup` frame. Returns an error code ("invalid", "too_big") or None."""
        if m.get("off") is True:
            self._parts.pop(device_id, None)
            self.delete(device_id)
            return None
        gen, part, parts, data = m.get("gen"), m.get("part"), m.get("parts"), m.get("data")
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (gen, part, parts)) or not isinstance(data, str):
            return "invalid"
        if not (1 <= parts <= MAX_PARTS and 0 <= part < parts) or len(data) > MAX_PART:
            return "too_big" if parts > MAX_PARTS or len(data) > MAX_PART else "invalid"
        cur = self._parts.get(device_id)
        if cur is None or cur["gen"] != gen or cur["n"] != parts or time.monotonic() - cur["t"] > 300:
            cur = self._parts[device_id] = {"gen": gen, "n": parts, "got": {}, "t": time.monotonic()}
        cur["got"][part] = data
        if len(cur["got"]) < parts:
            return None
        self._parts.pop(device_id, None)
        text = "".join(cur["got"][i] for i in range(parts))
        if len(text.encode()) > MAX_BACKUP_BYTES:
            return "too_big"
        try:
            doc = validate_export(json.loads(text))
        except json.JSONDecodeError:
            doc = None
        if doc is None:
            return "invalid"
        self.put(device_id, doc, gen)
        return None

    # ---- the store ---------------------------------------------------------------------------
    def put(self, device_id: str, doc: dict, gen: int = 0) -> None:
        raw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
        token = self._fernet(device_id).encrypt(raw)
        with self.store.lock:
            self.store.db.execute(
                "INSERT INTO memory_backup(device_id, token, facts, bytes, gen, updated) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(device_id) DO UPDATE SET token=excluded.token, facts=excluded.facts, "
                "bytes=excluded.bytes, gen=excluded.gen, updated=excluded.updated",
                (device_id, token, len(doc["facts"]), len(raw), int(gen), self.store.now()))
            self.store.db.commit()

    def get(self, device_id: str) -> Optional[dict]:
        with self.store.lock:
            row = self.store.db.execute("SELECT token FROM memory_backup WHERE device_id=?", (device_id,)).fetchone()
        if row is None:
            return None
        try:
            return json.loads(self._fernet(device_id).decrypt(row["token"]))
        except (InvalidToken, ValueError):
            return None  # another master secret or a tampered row: as if none

    def info(self, device_id: str) -> Optional[dict]:
        with self.store.lock:
            row = self.store.db.execute("SELECT facts, bytes, updated FROM memory_backup WHERE device_id=?",
                                        (device_id,)).fetchone()
        return None if row is None else {"facts": row["facts"], "bytes": row["bytes"], "updated": row["updated"]}

    def delete(self, device_id: str) -> bool:
        with self.store.lock:
            cur = self.store.db.execute("DELETE FROM memory_backup WHERE device_id=?", (device_id,))
            self.store.db.commit()
            return cur.rowcount > 0
