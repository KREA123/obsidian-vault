"""SOUL device side of the cloud: identity, tokens, pairing, outbox (docs/07-CONNECT-AI.md §3.2, §3.4, §6.1-6.3, §6.10).

Everything here is synchronous SQLite behind one lock, so the WebSocket hub
(gateway.py), the relay (relay.py), the MCP connector and the account pages can
all call it from any thread.

- Identity: `device_id` = "soul-" + 12 hex (public). Each device owns an ECDSA
  P-256 key; the cloud stores public keys only. Auth is challenge-response over
  `soul-auth-v1\\n{host}\\n{device_id}\\n{nonce}`, signature raw r||s, b64url.
- Enrolment policy (`SOUL_ENROL_POLICY`): `factory` (production: only imported
  keys) or `pending` (dev / P0: unknown keys are stored as pending, <= 5 per
  device; the one that completes pairing becomes bound).
- Device tokens `sdt_...`: 24 h, stored as SHA-256, revoked on unpair / reset.
- Pairing: 8 Crockford base32 characters (40 bits), stored as HMAC(pepper, code),
  10 min, single use; a claim never binds by itself, the device must answer
  `pair.ok` after a touch.
- Outbox: per-device gap-free `seq`, at-least-once delivery, acks, replay paging.

Secrets: nonces, tokens and pairing codes are stored hashed. The plaintext
pairing code of a device lives only in process memory (it has to be shown on
the device again after a reconnect); after a restart a new code is issued.
Nothing in this module logs a token, a code, a key or user text.
"""
from __future__ import annotations

import base64
import csv
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from cryptography.exceptions import InvalidSignature

from .config import default_brain
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

log = logging.getLogger("suflet_ai.devices")

DEVICE_ID_RE = re.compile(r"^soul-[0-9a-f]{12}$")
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_MAP = {"I": "1", "L": "1", "O": "0"}
AUTH_PREFIX = "soul-auth-v1"

NONCE_TTL = 60
TOKEN_TTL = 24 * 3600
CODE_TTL = 10 * 60
CLAIM_TTL = 120
MAX_PENDING_KEYS = 5
CARD_TTL = 6 * 3600          # answer.show expires after 6 h (§6.10)
MISSED_AFTER = 12 * 3600     # a reminder delivered > 12 h late arrives with missed: true
EVENTS_DAYS = 30
DEFAULT_TZ = "Europe/Bucharest"
DEFAULT_QUIET = ("22:00", "07:00")  # [E] product default until the owner sets it

BRAINS = ("cloud", "claude", "chatgpt", "direct", "none", "bridge")  # bridge: the owner's Claude Code (docs/08)
VOICES = ("claude", "chatgpt")


# ================================================================ errors ==

class GatewayError(Exception):
    """An error with an HTTP status and a §3.13 code. `msg` is safe to show and log."""

    def __init__(self, status: int, code: str, msg: str = "", retry_ms: Optional[int] = None):
        super().__init__(f"{status} {code}: {msg}")
        self.status = status
        self.code = code
        self.msg = msg or code
        self.retry_ms = retry_ms

    def body(self) -> dict:
        err: Dict[str, Any] = {"code": self.code, "msg": self.msg}
        if self.retry_ms is not None:
            err["retry_ms"] = int(self.retry_ms)
        return {"error": err}


# =============================================================== helpers ==

def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64u_decode(s: str) -> bytes:
    if not isinstance(s, str) or not re.fullmatch(r"[A-Za-z0-9_-]*", s):
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def check_device_id(device_id: Any) -> str:
    if not isinstance(device_id, str) or not DEVICE_ID_RE.match(device_id):
        raise GatewayError(400, "bad_request", "device_id must match ^soul-[0-9a-f]{12}$")
    return device_id


def auth_message(host: str, device_id: str, nonce: str) -> bytes:
    """The exact bytes the device signs (§6.2 step 2)."""
    return f"{AUTH_PREFIX}\n{host}\n{device_id}\n{nonce}".encode("utf-8")


def normalize_host(host: str) -> str:
    """`SOUL_PUBLIC_HOST` as the device writes it: lowercase, no scheme/path, `:port` only if not 443."""
    h = (host or "").strip().lower()
    h = re.sub(r"^[a-z]+://", "", h).split("/", 1)[0]
    if h.endswith(":443"):
        h = h[:-4]
    return h


def parse_pub(pub_b64u: Any) -> bytes:
    """Validate the 65-byte uncompressed SEC1 point (87 b64url chars) and return its bytes."""
    if not isinstance(pub_b64u, str) or len(pub_b64u) != 87:
        raise GatewayError(400, "bad_request", "pub must be 87 base64url characters")
    try:
        raw = b64u_decode(pub_b64u)
    except ValueError:
        raise GatewayError(400, "bad_request", "pub is not base64url") from None
    if len(raw) != 65 or raw[0] != 0x04:
        raise GatewayError(400, "bad_request", "pub must be an uncompressed P-256 point")
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
    except ValueError:
        raise GatewayError(400, "bad_request", "pub is not on P-256") from None
    return raw


def verify_sig(pub: bytes, msg: bytes, sig: bytes) -> bool:
    """ECDSA P-256 / SHA-256 over `msg`, signature as raw r||s (64 bytes)."""
    if len(sig) != 64:
        return False
    try:
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub)
        r = int.from_bytes(sig[:32], "big")
        s = int.from_bytes(sig[32:], "big")
        if not (0 < r and 0 < s):
            return False
        key.verify(encode_dss_signature(r, s), msg, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError):
        return False


def ip_prefix(ip: str) -> str:
    """Nonces are bound to the client's /24 (IPv4) or /56 (IPv6)."""
    try:
        a = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return ip or "-"
    bits = 24 if a.version == 4 else 56
    return str(ipaddress.ip_network(f"{a}/{bits}", strict=False))


def normalize_code(code: Any) -> str:
    if not isinstance(code, str):
        return ""
    c = re.sub(r"[\s-]", "", code).upper()
    return "".join(_CROCKFORD_MAP.get(ch, ch) for ch in c)


def account_hint(email: str) -> str:
    """a***@gmail.com"""
    email = (email or "").strip()
    if "@" not in email:
        return (email[:1] + "***") if email else ""
    user, dom = email.split("@", 1)
    return f"{user[:1]}***@{dom}"


_POSIX_FALLBACK = {
    "Europe/Bucharest": "EET-2EEST,M3.5.0/3,M10.5.0/4",
    "Europe/London": "GMT0BST,M3.5.0/1,M10.5.0",
    "Europe/Berlin": "CET-1CEST,M3.5.0,M10.5.0/3",
    "Europe/Paris": "CET-1CEST,M3.5.0,M10.5.0/3",
    "UTC": "UTC0",
}


def posix_tz(iana: str) -> str:
    """The POSIX TZ string for an IANA zone (the footer of the TZif v2+ file), for the ESP32's setenv("TZ")."""
    try:
        ZoneInfo(iana)
    except Exception:  # noqa: BLE001 - unknown zone
        return _POSIX_FALLBACK[DEFAULT_TZ]
    candidates: List[Path] = []
    try:
        import importlib.resources as ir

        candidates.append(Path(str(ir.files("tzdata").joinpath("zoneinfo", *iana.split("/")))))
    except Exception:  # noqa: BLE001 - tzdata package not installed
        pass
    candidates.append(Path("/usr/share/zoneinfo") / iana)
    for p in candidates:
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if data.startswith(b"TZif") and data[4:5] in (b"2", b"3", b"4"):
            footer = data.rstrip(b"\n").rsplit(b"\n", 1)[-1].decode("ascii", "replace")
            if footer:
                return footer
    return _POSIX_FALLBACK.get(iana, "UTC0")


def _load_pepper() -> bytes:
    env = os.environ.get("SOUL_ID_PEPPER", "")
    if env:
        return env.encode()
    # Dev: a per-process pepper. Production refuses to start without SOUL_ID_PEPPER (security.py).
    return secrets.token_bytes(32)


# ========================================================== rate limiter ==

class Buckets:
    """Small in-process token buckets. Production with several instances needs a shared store."""

    def __init__(self, clock: Callable[[], float]):
        self._clock = clock
        self._b: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def take(self, key: str, capacity: float, refill_per_s: float, cost: float = 1.0) -> Optional[int]:
        """Take `cost` tokens; returns None if allowed, else the ms to wait."""
        now = self._clock()
        with self._lock:
            tokens, last = self._b.get(key, (capacity, now))
            tokens = min(capacity, tokens + (now - last) * refill_per_s)
            if tokens >= cost:
                self._b[key] = (tokens - cost, now)
                return None
            self._b[key] = (tokens, now)
            need = (cost - tokens) / refill_per_s if refill_per_s > 0 else 3600
            return max(1, int(need * 1000))

    def check(self, key: str, capacity: float, refill_per_s: float, code: str = "rate_limited") -> None:
        wait = self.take(key, capacity, refill_per_s)
        if wait is not None:
            raise GatewayError(429, code, "too many requests, slow down", retry_ms=wait)


# ================================================================ schema ==

_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    account_id TEXT,
    owner_name TEXT NOT NULL DEFAULT '',
    owner_hint TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT 'SOUL',
    brain TEXT NOT NULL DEFAULT 'cloud',
    voice TEXT NOT NULL DEFAULT 'claude',
    lang TEXT NOT NULL DEFAULT 'ro',
    tz TEXT NOT NULL DEFAULT 'Europe/Bucharest',
    quiet_from TEXT NOT NULL DEFAULT '22:00',
    quiet_to TEXT NOT NULL DEFAULT '07:00',
    fw TEXT NOT NULL DEFAULT '',
    hw TEXT NOT NULL DEFAULT '',
    caps TEXT NOT NULL DEFAULT '[]',
    power TEXT NOT NULL DEFAULT '',
    brain_local TEXT NOT NULL DEFAULT '',
    tz_hint TEXT NOT NULL DEFAULT '',
    connectors_paused INTEGER NOT NULL DEFAULT 0,
    rssi INTEGER, battery INTEGER, free_heap INTEGER, awake INTEGER,
    last_seen INTEGER,
    wake_at INTEGER,
    trial_total INTEGER NOT NULL DEFAULT 0,
    trial_left INTEGER NOT NULL DEFAULT 0,
    created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS device_keys (
    device_id TEXT NOT NULL,
    pub BLOB NOT NULL,
    pub_hash TEXT NOT NULL,
    state TEXT NOT NULL,            -- factory | pending | bound | revoked
    created INTEGER NOT NULL,
    last_auth INTEGER,
    PRIMARY KEY (device_id, pub_hash)
);
CREATE TABLE IF NOT EXISTS device_members (
    device_id TEXT NOT NULL, account_id TEXT NOT NULL, role TEXT NOT NULL, created INTEGER NOT NULL,
    PRIMARY KEY (device_id, account_id)
);
CREATE TABLE IF NOT EXISTS device_nonces (
    nonce_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, ip_prefix TEXT NOT NULL,
    expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS device_tokens (
    hash TEXT PRIMARY KEY, device_id TEXT NOT NULL, pub_hash TEXT NOT NULL, expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS device_tokens_dev ON device_tokens(device_id);
CREATE TABLE IF NOT EXISTS pairing_codes (
    device_id TEXT PRIMARY KEY, code_hash TEXT NOT NULL, expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS pairing_codes_hash ON pairing_codes(code_hash);
CREATE TABLE IF NOT EXISTS pair_claims (
    pid TEXT PRIMARY KEY, device_id TEXT NOT NULL, account_id TEXT NOT NULL,
    first_name TEXT NOT NULL, hint TEXT NOT NULL, state TEXT NOT NULL, expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS device_counters (device_id TEXT PRIMARY KEY, next_seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (
    device_id TEXT NOT NULL, seq INTEGER NOT NULL, item_id TEXT NOT NULL, action TEXT NOT NULL,
    args TEXT NOT NULL, origin TEXT NOT NULL, say TEXT, flags TEXT NOT NULL DEFAULT '{}',
    created INTEGER NOT NULL, expires_at INTEGER, acked_at INTEGER, ack_ok INTEGER, ack_err TEXT,
    PRIMARY KEY (device_id, seq)
);
CREATE TABLE IF NOT EXISTS device_cids (
    device_id TEXT NOT NULL, cid TEXT NOT NULL, item_id TEXT NOT NULL, created INTEGER NOT NULL,
    PRIMARY KEY (device_id, cid)
);
CREATE TABLE IF NOT EXISTS inbox (
    item_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, cid TEXT NOT NULL, text TEXT NOT NULL,
    to_app TEXT NOT NULL, created INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
    answered_at INTEGER
);
CREATE INDEX IF NOT EXISTS inbox_dev ON inbox(device_id, state);
CREATE TABLE IF NOT EXISTS item_states (
    device_id TEXT NOT NULL, item_id TEXT NOT NULL, state TEXT NOT NULL, at INTEGER NOT NULL,
    PRIMARY KEY (device_id, item_id)
);
CREATE TABLE IF NOT EXISTS events (device_id TEXT NOT NULL, kind TEXT NOT NULL, at INTEGER NOT NULL);
"""


@dataclass
class DeviceCtx:
    """Who is on the other end of a device token. `device_id` comes only from the token."""

    device_id: str
    pub_hash: str
    key_state: str

    def __repr__(self) -> str:
        return f"DeviceCtx({self.device_id}, key={self.key_state})"


# ================================================================= store ==

class DeviceStore:
    def __init__(self, path: str = ":memory:", *, host: Optional[str] = None, policy: Optional[str] = None,
                 pepper: Optional[bytes] = None, clock: Callable[[], float] = time.time,
                 trial_turns: Optional[int] = None, pending_trial_turns: Optional[int] = None):
        self.path = path
        self.host = normalize_host(host or os.environ.get("SOUL_PUBLIC_HOST", "soul.example"))
        self.policy = policy or os.environ.get("SOUL_ENROL_POLICY", "pending")
        if self.policy not in ("factory", "pending"):
            raise ValueError("SOUL_ENROL_POLICY must be factory or pending")
        self._pepper = pepper or _load_pepper()
        self.clock = clock
        self.trial_turns = int(os.environ.get("SOUL_TRIAL_TURNS", "30") if trial_turns is None else trial_turns)
        self.pending_trial_turns = int(os.environ.get("SOUL_PENDING_TRIAL_TURNS", "0")
                                       if pending_trial_turns is None else pending_trial_turns)
        self.lock = threading.RLock()
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.executescript(_SCHEMA)
            self.db.commit()
        self.buckets = Buckets(clock)
        self._codes: Dict[str, Tuple[str, int]] = {}  # device_id -> (plaintext code, expires); memory only
        self._fails_account: Dict[str, Deque[float]] = defaultdict(deque)
        self._fails_ip: Dict[str, Deque[float]] = defaultdict(deque)
        self._fleet_fails: Deque[float] = deque()
        self._claims_paused_until = 0.0
        self.alerts: List[Callable[[str, dict], None]] = []
        self.on_unpair: List[Callable[[str, str, Optional[str], bool], None]] = []

    def __repr__(self) -> str:
        return f"DeviceStore({self.path!r}, host={self.host!r}, policy={self.policy!r})"

    def now(self) -> int:
        return int(self.clock())

    def _hmac(self, s: str) -> str:
        return hmac.new(self._pepper, s.encode(), hashlib.sha256).hexdigest()

    def executescript(self, sql: str) -> None:
        with self.lock:
            self.db.executescript(sql)
            self.db.commit()

    def _alert(self, kind: str, data: dict) -> None:
        log.warning("alert %s %s", kind, {k: v for k, v in data.items() if k in ("device_id", "count", "kind")})
        for fn in self.alerts:
            try:
                fn(kind, data)
            except Exception:  # noqa: BLE001 - an alert hook must never break the caller
                log.exception("alert hook failed")

    # ---------------------------------------------------------- devices --
    def _ensure_device(self, device_id: str, trial: int = 0) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO devices(device_id, trial_total, trial_left, created) VALUES (?,?,?,?)",
            (device_id, trial, trial, self.now()))

    def get_device(self, device_id: str) -> Optional[dict]:
        with self.lock:
            r = self.db.execute("SELECT * FROM devices WHERE device_id=?", (device_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["caps"] = json.loads(d.get("caps") or "[]")
        return d

    _UPDATABLE = {"name", "brain", "voice", "lang", "tz", "quiet_from", "quiet_to", "fw", "hw", "caps", "power",
                  "brain_local", "tz_hint", "connectors_paused", "rssi", "battery", "free_heap", "awake",
                  "last_seen", "wake_at", "trial_left"}

    def update_device(self, device_id: str, **fields: Any) -> None:
        bad = set(fields) - self._UPDATABLE
        if bad:
            raise ValueError(f"cannot update {sorted(bad)}")
        if "brain" in fields and fields["brain"] not in BRAINS:
            raise ValueError("bad brain")
        if "voice" in fields and fields["voice"] not in VOICES:
            raise ValueError("bad voice")
        if "tz" in fields:
            ZoneInfo(fields["tz"])  # raises for an unknown zone
        if "caps" in fields:
            fields["caps"] = json.dumps(list(fields["caps"]))
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        with self.lock:
            self.db.execute(f"UPDATE devices SET {cols} WHERE device_id=?", (*fields.values(), device_id))
            self.db.commit()

    def touch(self, device_id: str) -> None:
        with self.lock:
            self.db.execute("UPDATE devices SET last_seen=? WHERE device_id=?", (self.now(), device_id))
            self.db.commit()

    def device_state(self, ctx: DeviceCtx) -> str:
        """unpaired | paired | pending (dev enrolment, not yet paired)."""
        with self.lock:
            k = self.db.execute("SELECT state FROM device_keys WHERE device_id=? AND pub_hash=?",
                                (ctx.device_id, ctx.pub_hash)).fetchone()
            d = self.db.execute("SELECT account_id FROM devices WHERE device_id=?", (ctx.device_id,)).fetchone()
        if not k or k["state"] == "pending":
            return "pending"
        return "paired" if d and d["account_id"] else "unpaired"

    def trial(self, device_id: str, state: str) -> Optional[dict]:
        d = self.get_device(device_id)
        if not d or state == "paired" or d["trial_total"] <= 0 or default_brain() != "cloud":
            return None  # no trial without built-in AI (SOUL_BUILTIN_AI=0)
        return {"left": max(0, int(d["trial_left"])), "unit": "turns"}

    def use_trial(self, device_id: str) -> int:
        with self.lock:
            self.db.execute("UPDATE devices SET trial_left=MAX(0, trial_left-1) WHERE device_id=?", (device_id,))
            self.db.commit()
            r = self.db.execute("SELECT trial_left FROM devices WHERE device_id=?", (device_id,)).fetchone()
        return int(r["trial_left"]) if r else 0

    def owner(self, device_id: str) -> Optional[str]:
        d = self.get_device(device_id)
        return d["account_id"] if d else None

    def members(self, device_id: str) -> List[str]:
        with self.lock:
            rows = self.db.execute("SELECT account_id FROM device_members WHERE device_id=? ORDER BY created",
                                   (device_id,)).fetchall()
        return [r["account_id"] for r in rows]

    def revoked(self, device_id: str) -> bool:
        """True when the device has keys on file and every one of them is revoked."""
        with self.lock:
            rows = self.db.execute("SELECT state FROM device_keys WHERE device_id=?", (device_id,)).fetchall()
        return bool(rows) and all(r["state"] == "revoked" for r in rows)

    def account_devices(self, account_id: str) -> List[str]:
        with self.lock:
            rows = self.db.execute(
                "SELECT device_id FROM devices WHERE account_id=? UNION "
                "SELECT device_id FROM device_members WHERE account_id=? ORDER BY 1", (account_id, account_id)
            ).fetchall()
        return [r["device_id"] for r in rows]

    # ----------------------------------------------------- factory list --
    def import_factory(self, rows: Iterable[Tuple[str, str]] | str) -> int:
        """Import `(device_id, pub_b64u)` pairs (or a CSV path with columns device_id,pub). Returns the count."""
        if isinstance(rows, (str, os.PathLike)):
            with open(rows, newline="") as f:
                rows = [(r["device_id"].strip(), r["pub"].strip()) for r in csv.DictReader(f)]
        n = 0
        with self.lock:
            for device_id, pub_s in rows:
                check_device_id(device_id)
                pub = parse_pub(pub_s)
                self._ensure_device(device_id, trial=self.trial_turns)
                self.db.execute(
                    "INSERT OR IGNORE INTO device_keys(device_id, pub, pub_hash, state, created) VALUES (?,?,?,?,?)",
                    (device_id, pub, sha256_hex(pub), "factory", self.now()))
                n += 1
            self.db.commit()
        return n

    def revoke_key(self, device_id: str, pub_b64u: str) -> None:
        pub = parse_pub(pub_b64u)
        with self.lock:
            self.db.execute("UPDATE device_keys SET state='revoked' WHERE device_id=? AND pub_hash=?",
                            (device_id, sha256_hex(pub)))
            self.db.execute("DELETE FROM device_tokens WHERE device_id=? AND pub_hash=?", (device_id, sha256_hex(pub)))
            self.db.commit()

    # ------------------------------------------------------------ auth --
    def issue_nonce(self, device_id: Any, ip: str) -> dict:
        check_device_id(device_id)
        # Nothing about the caller is proven yet and device_id is public, so no bucket may be keyed by the
        # device alone (a third party could drain it and lock the real SOUL out). Per network, and per
        # (device, network): a stranger elsewhere cannot touch the real device's budget.
        self.buckets.check(f"chal:ip:{ip_prefix(ip)}", 120, 120 / 3600)
        self.buckets.check(f"chal:dev:{device_id}:{ip_prefix(ip)}", 20, 20 / 3600)
        nonce = b64u(secrets.token_bytes(32))
        now = self.now()
        with self.lock:
            self.db.execute("DELETE FROM device_nonces WHERE expires < ?", (now - 60,))
            self.db.execute("INSERT INTO device_nonces(nonce_hash, device_id, ip_prefix, expires) VALUES (?,?,?,?)",
                            (sha256_hex(nonce), device_id, ip_prefix(ip), now + NONCE_TTL))
            self.db.commit()
        return {"nonce": nonce, "expires_in": NONCE_TTL}

    def authenticate(self, body: Any, ip: str) -> dict:
        if not isinstance(body, dict):
            raise GatewayError(400, "bad_request", "body must be a JSON object")
        device_id = check_device_id(body.get("device_id"))
        pub = parse_pub(body.get("pub"))
        nonce, sig_s = body.get("nonce"), body.get("sig")
        if not isinstance(nonce, str) or not (1 <= len(nonce) <= 64):
            raise GatewayError(400, "bad_request", "nonce missing")
        if not isinstance(sig_s, str) or len(sig_s) != 86:
            raise GatewayError(400, "bad_request", "sig must be 86 base64url characters")
        try:
            sig = b64u_decode(sig_s)
        except ValueError:
            raise GatewayError(400, "bad_request", "sig is not base64url") from None
        fw = str(body.get("fw", ""))[:24]
        hw = str(body.get("hw", ""))[:24]
        reset = body.get("reset") is True
        # Before verification only the caller's network pays (device_id is public: a per-device bucket
        # here would let anyone lock a SOUL out). The per-device bucket is charged after the signature.
        self.buckets.check(f"auth:ip:{ip_prefix(ip)}", 60, 60 / 3600)

        now = self.now()
        with self.lock:
            n = self.db.execute("SELECT * FROM device_nonces WHERE nonce_hash=?", (sha256_hex(nonce),)).fetchone()
            if n:  # single use, even when the signature turns out wrong
                self.db.execute("UPDATE device_nonces SET used=1 WHERE nonce_hash=?", (n["nonce_hash"],))
                self.db.commit()
        if (not n or n["used"] or n["expires"] < now or n["device_id"] != device_id
                or n["ip_prefix"] != ip_prefix(ip)):
            raise GatewayError(400, "bad_nonce", "nonce unknown, used, expired or from another network")
        if not verify_sig(pub, auth_message(self.host, device_id, nonce), sig):
            raise GatewayError(401, "bad_signature", "signature does not verify")

        ph = sha256_hex(pub)
        # proven: this caller holds `pub`. Its own budget, which nobody else can spend.
        self.buckets.check(f"auth:key:{device_id}:{ph}", 10, 10 / 3600)
        with self.lock:
            k = self.db.execute("SELECT state FROM device_keys WHERE device_id=? AND pub_hash=?",
                                (device_id, ph)).fetchone()
            if k is None:
                if self.policy == "factory":
                    raise GatewayError(403, "not_enrolled", "this SOUL is not registered")
                # `pending` enrols unknown keys only while nobody owns the device and no known key exists.
                # device_id is public (MAC, box QR, SoftAP name), so otherwise anyone could attach a key to
                # a paired SOUL and read / ack its pushes. A re-flashed SOUL is unpaired by its owner first.
                if self._locked_to_known_key(device_id):
                    raise GatewayError(403, "not_enrolled", "this SOUL is already registered to another key")
                pend = self.db.execute(
                    "SELECT pub_hash FROM device_keys WHERE device_id=? AND state='pending' ORDER BY created",
                    (device_id,)).fetchall()
                for old in pend[: max(0, len(pend) - (MAX_PENDING_KEYS - 1))]:
                    self.db.execute("DELETE FROM device_keys WHERE device_id=? AND pub_hash=?",
                                    (device_id, old["pub_hash"]))
                self._ensure_device(device_id, trial=self.pending_trial_turns)
                self.db.execute(
                    "INSERT INTO device_keys(device_id, pub, pub_hash, state, created) VALUES (?,?,?,?,?)",
                    (device_id, pub, ph, "pending", now))
                key_state = "pending"
            else:
                key_state = k["state"]
                if key_state == "revoked":
                    raise GatewayError(403, "key_revoked", "this SOUL belongs to another account")
            self.db.execute("UPDATE device_keys SET last_auth=? WHERE device_id=? AND pub_hash=?", (now, device_id, ph))
            self.db.execute("UPDATE devices SET fw=?, hw=?, last_seen=? WHERE device_id=?", (fw, hw, now, device_id))
            self.db.commit()

        if reset and key_state in ("bound", "factory") and self.owner(device_id):
            self.unpair(device_id, "reset", erase=False)

        token = "sdt_" + b64u(secrets.token_bytes(32))
        with self.lock:
            self.db.execute("DELETE FROM device_tokens WHERE expires < ?", (now,))
            self.db.execute("INSERT INTO device_tokens(hash, device_id, pub_hash, expires) VALUES (?,?,?,?)",
                            (sha256_hex(token), device_id, ph, now + TOKEN_TTL))
            self.db.commit()
        ctx = DeviceCtx(device_id, ph, key_state)
        state = self.device_state(ctx)
        d = self.get_device(device_id) or {}
        return {
            "token": token,
            "expires_in": TOKEN_TTL,
            "ws_url": f"wss://{self.host}/v1/device/ws",
            "server_time": now,
            "state": state,
            "owner": d.get("owner_name", "") if state == "paired" else "",
            "trial": self.trial(device_id, state),
        }

    def _locked_to_known_key(self, device_id: str) -> bool:
        """True when the device has an owner or a factory key: no new key may enrol then.

        (A `bound` key without an owner is a SOUL its owner released, or one that reset itself: it is
        unpaired again, and under `pending` an unpaired SOUL goes to whoever pairs it first.)"""
        with self.lock:
            d = self.db.execute("SELECT account_id FROM devices WHERE device_id=?", (device_id,)).fetchone()
            k = self.db.execute("SELECT 1 FROM device_keys WHERE device_id=? AND state='factory' LIMIT 1",
                                (device_id,)).fetchone()
        return bool((d and d["account_id"]) or k)

    def key_allowed(self, ctx: DeviceCtx) -> bool:
        """May this key's transport be served at all? Not when it is unknown or revoked, and not when the
        device is paired and this is not its factory / bound key (a pending key never sees a paired SOUL)."""
        with self.lock:
            k = self.db.execute("SELECT state FROM device_keys WHERE device_id=? AND pub_hash=?",
                                (ctx.device_id, ctx.pub_hash)).fetchone()
            d = self.db.execute("SELECT account_id FROM devices WHERE device_id=?", (ctx.device_id,)).fetchone()
        if not k or k["state"] == "revoked":
            return False
        if d and d["account_id"] and k["state"] not in ("bound", "factory"):
            return False
        return True

    def device_from_token(self, bearer: Optional[str]) -> DeviceCtx:
        token = (bearer or "").strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if not token.startswith("sdt_") or len(token) > 100:
            raise GatewayError(401, "unauthenticated", "device token missing")
        with self.lock:
            t = self.db.execute("SELECT * FROM device_tokens WHERE hash=?", (sha256_hex(token),)).fetchone()
            if not t:
                raise GatewayError(401, "unauthenticated", "device token unknown or revoked")
            if t["expires"] < self.now():
                raise GatewayError(401, "token_expired", "device token expired")
            k = self.db.execute("SELECT state FROM device_keys WHERE device_id=? AND pub_hash=?",
                                (t["device_id"], t["pub_hash"])).fetchone()
        if not k or k["state"] == "revoked":
            raise GatewayError(401, "unauthenticated", "device key revoked")
        ctx = DeviceCtx(t["device_id"], t["pub_hash"], k["state"])
        if not self.key_allowed(ctx):
            raise GatewayError(401, "unauthenticated", "this key is not the paired SOUL's key")
        return ctx

    def revoke_tokens(self, device_id: str) -> None:
        with self.lock:
            self.db.execute("DELETE FROM device_tokens WHERE device_id=?", (device_id,))
            self.db.commit()

    # --------------------------------------------------------- pairing --
    def pairing_url(self, code: str, device_id: str) -> str:
        return f"https://{self.host}/pair#c={code}&d={device_id}"

    def current_code(self, device_id: str, force_new: bool = False) -> dict:
        """The `pairing` message for this device; rotates the code when expired (or when forced)."""
        now = self.now()
        with self.lock:
            cur = self._codes.get(device_id)
            row = self.db.execute("SELECT * FROM pairing_codes WHERE device_id=?", (device_id,)).fetchone()
            valid = (cur and row and cur[1] > now and row["code_hash"] == self._hmac(cur[0]))
            if force_new or not valid:
                code = "".join(secrets.choice(CROCKFORD) for _ in range(8))
                exp = now + CODE_TTL
                self.db.execute(
                    "INSERT INTO pairing_codes(device_id, code_hash, expires) VALUES (?,?,?) "
                    "ON CONFLICT(device_id) DO UPDATE SET code_hash=excluded.code_hash, expires=excluded.expires",
                    (device_id, self._hmac(code), exp))
                self.db.commit()
                self._codes[device_id] = (code, exp)
                cur = (code, exp)
        code, exp = cur  # type: ignore[misc]
        return {"v": 1, "t": "pairing", "code": code, "expires_in": max(1, exp - now),
                "url": self.pairing_url(code, device_id)}

    def code_id(self, device_id: str) -> Optional[str]:
        """An opaque id of the device's current code (to know whether it changed), never the code."""
        cur = self._codes.get(device_id)
        return self._hmac("id:" + cur[0]) if cur and cur[1] > self.now() else None

    def _drop_code(self, device_id: str) -> None:
        self._codes.pop(device_id, None)
        self.db.execute("DELETE FROM pairing_codes WHERE device_id=?", (device_id,))

    def _claim_fail(self, account_id: str, ip: str) -> None:
        now = self.clock()
        self._fails_account[account_id].append(now)
        self._fails_ip[ip_prefix(ip)].append(now)
        self._fleet_fails.append(now)
        while self._fleet_fails and self._fleet_fails[0] < now - 3600:
            self._fleet_fails.popleft()
        if len(self._fleet_fails) >= 1000 and self._claims_paused_until <= now:
            self._claims_paused_until = now + 15 * 60
            self._alert("pairing_fleet_limit", {"count": len(self._fleet_fails)})

    def _check_claim_limits(self, account_id: str, ip: str) -> None:
        now = self.clock()
        if self._claims_paused_until > now:
            raise GatewayError(429, "rate_limited", "pairing is paused, try again later",
                               retry_ms=int((self._claims_paused_until - now) * 1000))
        for q, window, limit in ((self._fails_account[account_id], 600, 5), (self._fails_ip[ip_prefix(ip)], 3600, 20)):
            while q and q[0] < now - window:
                q.popleft()
            if len(q) >= limit:
                raise GatewayError(429, "rate_limited", "too many wrong codes, wait a little",
                                   retry_ms=int((q[0] + window - now) * 1000))

    def claim(self, account_id: str, first_name: str, email: str, code: Any, ip: str,
              hint: Optional[str] = None) -> dict:
        """A signed-in account typed / scanned a code. Returns the claim and the `pair.confirm` for the device.

        `hint` (e.g. "a***@gmail.com") overrides the one derived from `email` when the caller only has a hint."""
        if not isinstance(account_id, str) or not account_id:
            raise GatewayError(401, "unauthenticated", "sign in first")
        self._check_claim_limits(account_id, ip)
        c = normalize_code(code)
        if len(c) != 8 or any(ch not in CROCKFORD for ch in c):
            self._claim_fail(account_id, ip)
            raise GatewayError(422, "invalid", "a pairing code has 8 characters")
        now = self.now()
        with self.lock:
            row = self.db.execute("SELECT * FROM pairing_codes WHERE code_hash=?", (self._hmac(c),)).fetchone()
            if not row:
                self._claim_fail(account_id, ip)
                raise GatewayError(404, "not_found", "no SOUL shows this code")
            device_id = row["device_id"]
            if row["expires"] < now:
                self._claim_fail(account_id, ip)
                raise GatewayError(410, "code_expired", "this code expired; SOUL shows a new one")
            d = self.get_device(device_id) or {}
            if d.get("account_id") and d["account_id"] != account_id:
                raise GatewayError(409, "device_owned", "this SOUL belongs to another account")
            # code is single use
            self._drop_code(device_id)
            self.db.execute("UPDATE pair_claims SET state='expired' WHERE device_id=? AND state='awaiting_device'",
                            (device_id,))
            pid = "p_" + b64u(secrets.token_bytes(12))
            hint = (hint if hint is not None else account_hint(email))[:80]
            name = (first_name or "").strip()[:40] or hint or "?"
            self.db.execute(
                "INSERT INTO pair_claims(pid, device_id, account_id, first_name, hint, state, expires) "
                "VALUES (?,?,?,?,?,?,?)", (pid, device_id, account_id, name, hint, "awaiting_device", now + CLAIM_TTL))
            self.db.commit()
        confirm = {"v": 1, "t": "pair.confirm", "pid": pid, "name": name, "account_hint": hint,
                   "expires_in": CLAIM_TTL}
        return {"pid": pid, "device": {"id": device_id, "name": d.get("name", "SOUL")},
                "state": "awaiting_device", "expires_in": CLAIM_TTL, "_device_msg": confirm}

    def awaiting_confirm(self, device_id: str) -> Optional[dict]:
        """The `pair.confirm` of a live claim waiting for the owner's tap on this device, else None."""
        now = self.now()
        with self.lock:
            r = self.db.execute("SELECT * FROM pair_claims WHERE device_id=? AND state='awaiting_device' "
                                "AND expires>=? ORDER BY expires DESC LIMIT 1", (device_id, now)).fetchone()
        if not r:
            return None
        return {"v": 1, "t": "pair.confirm", "pid": r["pid"], "name": r["first_name"], "account_hint": r["hint"],
                "expires_in": max(1, r["expires"] - now)}

    def claim_state(self, pid: str, account_id: str) -> dict:
        with self.lock:
            r = self.db.execute("SELECT * FROM pair_claims WHERE pid=? AND account_id=?", (pid, account_id)).fetchone()
        if not r:
            raise GatewayError(404, "not_found", "unknown pairing request")
        state = r["state"]
        if state == "awaiting_device" and r["expires"] < self.now():
            state = "expired"
        return {"state": state}

    def expire_claims(self) -> List[str]:
        """Mark timed-out claims expired; returns the devices that need a new code."""
        now = self.now()
        with self.lock:
            rows = self.db.execute("SELECT pid, device_id FROM pair_claims WHERE state='awaiting_device' AND expires<?",
                                   (now,)).fetchall()
            for r in rows:
                self.db.execute("UPDATE pair_claims SET state='expired' WHERE pid=?", (r["pid"],))
            self.db.commit()
        return [r["device_id"] for r in rows]

    def on_device_answer(self, ctx: DeviceCtx, pid: Any, ok: bool) -> Optional[dict]:
        """`pair.ok` / `pair.no` from this device's authenticated transport. Returns the `paired` message on success."""
        if not isinstance(pid, str):
            return None
        now = self.now()
        with self.lock:
            r = self.db.execute("SELECT * FROM pair_claims WHERE pid=?", (pid,)).fetchone()
            if not r or r["device_id"] != ctx.device_id or r["state"] != "awaiting_device":
                return None
            if r["expires"] < now:
                self.db.execute("UPDATE pair_claims SET state='expired' WHERE pid=?", (pid,))
                self.db.commit()
                return None
            if not ok:
                self.db.execute("UPDATE pair_claims SET state='rejected' WHERE pid=?", (pid,))
                self.db.commit()
                return None
            d = self.get_device(ctx.device_id) or {}
            if d.get("account_id") and d["account_id"] != r["account_id"]:
                self.db.execute("UPDATE pair_claims SET state='rejected' WHERE pid=?", (pid,))
                self.db.commit()
                return None
            # this key becomes bound; other pending keys go, other bound keys are revoked
            self.db.execute("DELETE FROM device_keys WHERE device_id=? AND state='pending' AND pub_hash<>?",
                            (ctx.device_id, ctx.pub_hash))
            self.db.execute("UPDATE device_keys SET state='revoked' WHERE device_id=? AND pub_hash<>? "
                            "AND state IN ('bound','factory')", (ctx.device_id, ctx.pub_hash))
            self.db.execute("DELETE FROM device_tokens WHERE device_id=? AND pub_hash<>?",
                            (ctx.device_id, ctx.pub_hash))
            self.db.execute("UPDATE device_keys SET state='bound' WHERE device_id=? AND pub_hash=?",
                            (ctx.device_id, ctx.pub_hash))
            self.db.execute("UPDATE devices SET account_id=?, owner_name=?, owner_hint=?, brain=? "
                            "WHERE device_id=?", (r["account_id"], r["first_name"], r["hint"], default_brain(),
                                                  ctx.device_id))
            self.db.execute("INSERT OR REPLACE INTO device_members(device_id, account_id, role, created) "
                            "VALUES (?,?,?,?)", (ctx.device_id, r["account_id"], "owner", now))
            self.db.execute("UPDATE pair_claims SET state='paired' WHERE pid=?", (pid,))
            self._drop_code(ctx.device_id)
            self.db.commit()
        ctx.key_state = "bound"
        return {"v": 1, "t": "paired", "owner": r["first_name"], "account_hint": r["hint"]}

    def unpair(self, device_id: str, reason: str, erase: bool = False) -> Optional[str]:
        """Release the device. Revokes its tokens and drops undelivered pushes. Returns the old owner."""
        if reason not in ("user", "reset", "transfer", "revoked"):
            raise ValueError("bad reason")
        with self.lock:
            d = self.db.execute("SELECT account_id FROM devices WHERE device_id=?", (device_id,)).fetchone()
            old = d["account_id"] if d else None
            self.db.execute("UPDATE devices SET account_id=NULL, owner_name='', owner_hint='', brain=?, "
                            "connectors_paused=0 WHERE device_id=?", (default_brain(), device_id))
            self.db.execute("DELETE FROM device_members WHERE device_id=?", (device_id,))
            self.db.execute("DELETE FROM outbox WHERE device_id=? AND acked_at IS NULL", (device_id,))
            self.db.execute("UPDATE pair_claims SET state='expired' WHERE device_id=? AND state='awaiting_device'",
                            (device_id,))
            self.db.execute("DELETE FROM device_tokens WHERE device_id=?", (device_id,))
            if erase:
                for t in ("inbox", "item_states", "device_cids", "events"):
                    self.db.execute(f"DELETE FROM {t} WHERE device_id=?", (device_id,))
                self.db.execute("DELETE FROM outbox WHERE device_id=?", (device_id,))
            self.db.commit()
        for fn in self.on_unpair:
            try:
                fn(device_id, reason, old, erase)
            except Exception:  # noqa: BLE001
                log.exception("unpair hook failed")
        return old

    # ---------------------------------------------------------- outbox --
    def next_seq(self, device_id: str) -> int:
        with self.lock:
            r = self.db.execute("SELECT next_seq FROM device_counters WHERE device_id=?", (device_id,)).fetchone()
            seq = r["next_seq"] if r else 1
            self.db.execute("INSERT INTO device_counters(device_id, next_seq) VALUES (?,?) "
                            "ON CONFLICT(device_id) DO UPDATE SET next_seq=excluded.next_seq", (device_id, seq + 1))
            return seq

    def last_seq(self, device_id: str) -> int:
        with self.lock:
            r = self.db.execute("SELECT next_seq FROM device_counters WHERE device_id=?", (device_id,)).fetchone()
        return (r["next_seq"] - 1) if r else 0

    def enqueue(self, device_id: str, action: str, args: dict, item_id: str, origin: dict, say: Optional[str] = None,
                private: bool = False, needs_accept: bool = False, expires_at: Optional[int] = None) -> int:
        """Store a push for the device and return its gap-free `seq`."""
        if not isinstance(item_id, str) or not (1 <= len(item_id) <= 32):
            raise ValueError("item_id must be 1..32 characters")
        if action == "answer.show" and expires_at is None:
            expires_at = self.now() + CARD_TTL
        if action == "nav.start" and expires_at is None:  # "take me to ..." an hour later is not wanted any more
            expires_at = self.now() + 3600
        flags = {"private": bool(private), "needs_accept": bool(needs_accept)}
        with self.lock:
            seq = self.next_seq(device_id)  # same transaction as the insert: gap-free
            self.db.execute(
                "INSERT INTO outbox(device_id, seq, item_id, action, args, origin, say, flags, created, expires_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (device_id, seq, item_id, action, json.dumps(args, ensure_ascii=False),
                 json.dumps(origin, ensure_ascii=False), (say or None) and say[:200], json.dumps(flags),
                 self.now(), expires_at))
            self.db.commit()
        return seq

    def _push_msg(self, r: sqlite3.Row, tz: str) -> dict:
        m: Dict[str, Any] = {"v": 1, "t": "push", "seq": r["seq"], "action": r["action"],
                             "args": json.loads(r["args"]), "item_id": r["item_id"], "origin": json.loads(r["origin"])}
        if r["say"]:
            m["say"] = r["say"]
        flags = json.loads(r["flags"] or "{}")
        if flags.get("private"):
            m["private"] = True
        if flags.get("needs_accept"):
            m["needs_accept"] = True
        if r["expires_at"]:
            m["expires_at"] = r["expires_at"]
        if r["action"] == "reminder.create":
            try:
                when = dt.datetime.strptime(m["args"]["when"], "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo(tz))
                if self.now() - when.timestamp() > MISSED_AFTER:
                    m["missed"] = True
            except (KeyError, ValueError, TypeError):
                pass
        return m

    def replay(self, device_id: str, after: int, limit: int = 50) -> Tuple[List[dict], bool]:
        """Unacked, unexpired pushes with seq > after, oldest first, at most `limit`; `more` if there are others."""
        d = self.get_device(device_id) or {}
        tz = d.get("tz") or DEFAULT_TZ
        with self.lock:
            rows = self.db.execute(
                "SELECT * FROM outbox WHERE device_id=? AND seq>? AND acked_at IS NULL "
                "AND (expires_at IS NULL OR expires_at>?) ORDER BY seq LIMIT ?",
                (device_id, int(after), self.now(), limit + 1)).fetchall()
        return [self._push_msg(r, tz) for r in rows[:limit]], len(rows) > limit

    def ack(self, device_id: str, seq: Any, ok: bool, err: Optional[str] = None) -> Optional[dict]:
        if not isinstance(seq, int) or isinstance(seq, bool):
            return None
        with self.lock:
            r = self.db.execute("SELECT * FROM outbox WHERE device_id=? AND seq=?", (device_id, seq)).fetchone()
            if not r:
                return None
            if r["acked_at"] is None:
                self.db.execute("UPDATE outbox SET acked_at=?, ack_ok=?, ack_err=? WHERE device_id=? AND seq=?",
                                (self.now(), 1 if ok else 0, (err or None) and str(err)[:24], device_id, seq))
                self.db.commit()
        return {"seq": seq, "ok": bool(ok), "err": err, "needs_accept": json.loads(r["flags"]).get("needs_accept", False),
                "item_id": r["item_id"]}

    def ack_upto(self, device_id: str, after: int) -> None:
        """`hello.after = N` means the device applied everything up to N."""
        with self.lock:
            self.db.execute("UPDATE outbox SET acked_at=?, ack_ok=1 WHERE device_id=? AND seq<=? AND acked_at IS NULL",
                            (self.now(), device_id, int(after)))
            self.db.commit()

    def push_status(self, device_id: str, seq: int) -> Optional[dict]:
        with self.lock:
            r = self.db.execute("SELECT acked_at, ack_ok, ack_err, flags FROM outbox WHERE device_id=? AND seq=?",
                                (device_id, seq)).fetchone()
        if not r:
            return None
        return {"acked": r["acked_at"] is not None, "ok": bool(r["ack_ok"]), "err": r["ack_err"],
                "needs_accept": json.loads(r["flags"]).get("needs_accept", False)}

    def expire_cards(self) -> int:
        with self.lock:
            cur = self.db.execute("UPDATE outbox SET acked_at=?, ack_ok=0, ack_err='expired' "
                                  "WHERE acked_at IS NULL AND expires_at IS NOT NULL AND expires_at<=?",
                                  (self.now(), self.now()))
            self.db.commit()
            return cur.rowcount

    # ------------------------------------------- items from the device --
    def cid_item(self, device_id: str, cid: str) -> Optional[str]:
        with self.lock:
            r = self.db.execute("SELECT item_id FROM device_cids WHERE device_id=? AND cid=?", (device_id, cid)).fetchone()
        return r["item_id"] if r else None

    def remember_cid(self, device_id: str, cid: str, item_id: str) -> None:
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO device_cids(device_id, cid, item_id, created) VALUES (?,?,?,?)",
                            (device_id, cid, item_id, self.now()))
            self.db.commit()

    def inbox_add(self, device_id: str, cid: str, text: str, to_app: str) -> str:
        item_id = "ib_" + b64u(secrets.token_bytes(9))
        with self.lock:
            self.db.execute("INSERT INTO inbox(item_id, device_id, cid, text, to_app, created) VALUES (?,?,?,?,?,?)",
                            (item_id, device_id, cid, text, to_app, self.now()))
            self.db.execute("INSERT OR IGNORE INTO device_cids(device_id, cid, item_id, created) VALUES (?,?,?,?)",
                            (device_id, cid, item_id, self.now()))
            self.db.commit()
        return item_id

    def inbox_list(self, device_id: str, state: Optional[str] = "pending", limit: int = 20) -> List[dict]:
        q, args = "SELECT * FROM inbox WHERE device_id=?", [device_id]
        if state:
            q += " AND state=?"
            args.append(state)
        q += " ORDER BY created LIMIT ?"
        args.append(limit)
        with self.lock:
            rows = self.db.execute(q, args).fetchall()
        return [{"item_id": r["item_id"], "text": r["text"], "to": r["to_app"], "created": r["created"],
                 "state": r["state"]} for r in rows]

    def inbox_answer(self, device_id: str, item_id: str) -> bool:
        with self.lock:
            cur = self.db.execute("UPDATE inbox SET state='answered', answered_at=? WHERE device_id=? AND item_id=?",
                                  (self.now(), device_id, item_id))
            self.db.commit()
            return cur.rowcount > 0

    def inbox_counts(self, device_id: str) -> dict:
        with self.lock:
            rows = self.db.execute("SELECT state, COUNT(*) n FROM inbox WHERE device_id=? GROUP BY state",
                                   (device_id,)).fetchall()
        c = {r["state"]: r["n"] for r in rows}
        return {"pending": c.get("pending", 0), "answered": c.get("answered", 0)}

    def set_item_state(self, device_id: str, item_id: str, state: str, at: int) -> None:
        with self.lock:
            self.db.execute("INSERT INTO item_states(device_id, item_id, state, at) VALUES (?,?,?,?) "
                            "ON CONFLICT(device_id, item_id) DO UPDATE SET state=excluded.state, at=excluded.at",
                            (device_id, item_id, state, at))
            self.db.commit()

    def item_state(self, device_id: str, item_id: str) -> Optional[str]:
        with self.lock:
            r = self.db.execute("SELECT state FROM item_states WHERE device_id=? AND item_id=?",
                                (device_id, item_id)).fetchone()
        return r["state"] if r else None

    def add_events(self, device_id: str, events: List[Tuple[str, int]]) -> int:
        now = self.now()
        with self.lock:
            self.db.executemany("INSERT INTO events(device_id, kind, at) VALUES (?,?,?)",
                                [(device_id, k, at) for k, at in events])
            self.db.execute("DELETE FROM events WHERE at < ?", (now - EVENTS_DAYS * 86400,))
            self.db.commit()
        return len(events)
