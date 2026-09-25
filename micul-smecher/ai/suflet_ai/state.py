"""SOUL device state: what the actions create, in SQLite.

One small table of items (notes, reminders, alarms, timers, focus sessions,
message drafts, list items, answer cards) plus per-device settings (the AI
mode). ":memory:" works for tests; a file path for the real service. The
device pulls new items with `since` (a monotonically increasing row id), the
same pattern as the outbox sync in os/ARCHITECTURE.md (D8).
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from typing import List, Optional

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

KINDS = ("note", "reminder", "alarm", "timer", "focus", "draft", "list_item", "card")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    device   TEXT NOT NULL,
    kind     TEXT NOT NULL,
    body     TEXT NOT NULL,
    created  TEXT NOT NULL,
    due      TEXT,            -- local YYYY-MM-DDTHH:MM for things that happen at a time
    done     INTEGER NOT NULL DEFAULT 0,
    source   TEXT NOT NULL DEFAULT 'app'
);
CREATE INDEX IF NOT EXISTS items_dev ON items(device, kind, seq);
CREATE TABLE IF NOT EXISTS settings (
    device TEXT NOT NULL,
    key    TEXT NOT NULL,
    value  TEXT NOT NULL,
    PRIMARY KEY (device, key)
);
CREATE TABLE IF NOT EXISTS secrets (
    device   TEXT NOT NULL,
    provider TEXT NOT NULL,
    token    BLOB NOT NULL,     -- Fernet ciphertext, never the plain key
    updated  TEXT NOT NULL,
    PRIMARY KEY (device, provider)
);
"""


def check_device(device_id: str) -> str:
    if not isinstance(device_id, str) or not _SAFE_ID.match(device_id):
        raise ValueError("invalid device id")
    return device_id


class StateStore:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self._lock:
            self.db.executescript(_SCHEMA)
            self.db.commit()

    # ---------------------------------------------------------------- items --
    def add(self, device: str, kind: str, body: dict, created: str, due: Optional[str] = None,
            source: str = "app") -> int:
        check_device(device)
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind}")
        with self._lock:
            cur = self.db.execute(
                "INSERT INTO items(device, kind, body, created, due, source) VALUES (?,?,?,?,?,?)",
                (device, kind, json.dumps(body, ensure_ascii=False), created, due, source[:32]),
            )
            self.db.commit()
            return int(cur.lastrowid)

    def items(self, device: str, kind: Optional[str] = None, since: int = 0,
              include_done: bool = True, limit: int = 500) -> List[dict]:
        check_device(device)
        q = "SELECT * FROM items WHERE device=? AND seq>?"
        args: list = [device, since]
        if kind:
            q += " AND kind=?"
            args.append(kind)
        if not include_done:
            q += " AND done=0"
        q += " ORDER BY seq LIMIT ?"
        args.append(limit)
        with self._lock:
            return [self._row(r) for r in self.db.execute(q, args).fetchall()]

    def today(self, device: str, day: str) -> List[dict]:
        """Everything due on `day` (YYYY-MM-DD) plus what was created that day."""
        check_device(device)
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM items WHERE device=? AND (due LIKE ? OR (due IS NULL AND created LIKE ?)) "
                "ORDER BY COALESCE(due, created), seq",
                (device, day + "%", day + "%"),
            ).fetchall()
        return [self._row(r) for r in rows]

    def due(self, device: str, now_local: str) -> List[dict]:
        """Reminders whose time has come; each is returned once."""
        check_device(device)
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM items WHERE device=? AND kind='reminder' AND done=0 AND due<=? ORDER BY due",
                (device, now_local),
            ).fetchall()
            if rows:
                self.db.executemany("UPDATE items SET done=1 WHERE seq=?", [(r["seq"],) for r in rows])
                self.db.commit()
        return [self._row(r) for r in rows]

    def mark_done(self, device: str, seq: int) -> bool:
        check_device(device)
        with self._lock:
            cur = self.db.execute("UPDATE items SET done=1 WHERE device=? AND seq=?", (device, seq))
            self.db.commit()
            return cur.rowcount > 0

    @staticmethod
    def _row(r: sqlite3.Row) -> dict:
        return {"id": r["seq"], "kind": r["kind"], "created": r["created"], "due": r["due"],
                "done": bool(r["done"]), "source": r["source"], **json.loads(r["body"])}

    # ------------------------------------------------------------- settings --
    def get_setting(self, device: str, key: str, default: str = "") -> str:
        check_device(device)
        with self._lock:
            r = self.db.execute("SELECT value FROM settings WHERE device=? AND key=?", (device, key)).fetchone()
        return r["value"] if r else default

    def set_setting(self, device: str, key: str, value: str) -> None:
        check_device(device)
        with self._lock:
            self.db.execute(
                "INSERT INTO settings(device, key, value) VALUES (?,?,?) "
                "ON CONFLICT(device, key) DO UPDATE SET value=excluded.value",
                (device, key, value),
            )
            self.db.commit()

    # -------------------------------------------------------------- secrets --
    # Only ciphertext passes through here; see keystore.py.
    def put_secret(self, device: str, provider: str, token: bytes, updated: str) -> None:
        check_device(device)
        with self._lock:
            self.db.execute(
                "INSERT INTO secrets(device, provider, token, updated) VALUES (?,?,?,?) "
                "ON CONFLICT(device, provider) DO UPDATE SET token=excluded.token, updated=excluded.updated",
                (device, provider, token, updated),
            )
            self.db.commit()

    def get_secret(self, device: str, provider: str) -> Optional[bytes]:
        check_device(device)
        with self._lock:
            r = self.db.execute("SELECT token FROM secrets WHERE device=? AND provider=?",
                                (device, provider)).fetchone()
        return bytes(r["token"]) if r else None

    def secret_info(self, device: str) -> dict:
        check_device(device)
        with self._lock:
            rows = self.db.execute("SELECT provider, updated FROM secrets WHERE device=?", (device,)).fetchall()
        return {r["provider"]: r["updated"] for r in rows}

    def delete_secret(self, device: str, provider: str) -> bool:
        check_device(device)
        with self._lock:
            cur = self.db.execute("DELETE FROM secrets WHERE device=? AND provider=?", (device, provider))
            self.db.commit()
            return cur.rowcount > 0

    # ---------------------------------------------------------------- wipe --
    def wipe(self, device: str) -> None:
        check_device(device)
        with self._lock:
            for t in ("items", "settings", "secrets"):
                self.db.execute(f"DELETE FROM {t} WHERE device=?", (device,))
            self.db.commit()
