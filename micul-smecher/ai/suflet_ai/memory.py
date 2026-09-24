"""Per-device memory, stored as plain JSON the owner can read and wipe.

Transparency is a product feature: GET shows everything it remembers,
DELETE forgets it all. No audio is ever stored — only text facts.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from .schemas import Persona, Reminder, Reply

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_FACTS = 200
MAX_NOTES = 500
MAX_EVENTS = 2000


@dataclass
class Memory:
    device_id: str
    owner: str = ""
    language: str = "ro"
    persona: Optional[dict] = None
    facts: List[str] = field(default_factory=list)
    reminders: List[dict] = field(default_factory=list)
    notes: List[dict] = field(default_factory=list)
    history: List[dict] = field(default_factory=list)  # recent turns for context
    events: List[dict] = field(default_factory=list)  # device event log (recent days)
    topics: List[dict] = field(default_factory=list)  # one-line topics of past chats

    def add_events(self, events: List[dict]) -> None:
        for e in events:
            if isinstance(e, dict) and isinstance(e.get("t"), str) and isinstance(e.get("ev"), str):
                self.events.append({"t": e["t"][:19], "ev": e["ev"][:32], "n": int(e.get("n", 1))})
        self.events = self.events[-MAX_EVENTS:]

    # ---- updates from a reply ------------------------------------------------
    def apply(self, reply: Reply, now_iso: str) -> None:
        for f in reply.forget:
            key = f.strip().lower()
            if len(key) < 3:  # never let a blank keyword wipe everything
                continue
            self.facts = [x for x in self.facts if key not in x.lower()]
        for f in reply.remember:
            f = f.strip()
            if f and f not in self.facts:
                self.facts.append(f)
        self.facts = self.facts[-MAX_FACTS:]
        for r in reply.reminders:
            self.reminders.append({"at": r.at, "text": r.text, "created": now_iso, "done": False})
        for n in reply.notes:
            if n.strip():
                self.notes.append({"text": n.strip(), "created": now_iso})
        self.notes = self.notes[-MAX_NOTES:]

    def due_reminders(self, now_iso: str) -> List[Reminder]:
        """Reminders whose time has come (ISO strings compare correctly)."""
        due = []
        for r in self.reminders:
            if not r.get("done") and r["at"] <= now_iso:
                r["done"] = True
                due.append(Reminder(at=r["at"], text=r["text"]))
        return due

    def persona_model(self) -> Optional[Persona]:
        return Persona.model_validate(self.persona) if self.persona else None


class MemoryStore:
    def __init__(self, data_dir: str):
        self.dir = data_dir
        os.makedirs(self.dir, exist_ok=True)

    def _path(self, device_id: str) -> str:
        if not _SAFE_ID.match(device_id):
            raise ValueError("invalid device id")
        return os.path.join(self.dir, f"{device_id}.json")

    def load(self, device_id: str) -> Memory:
        p = self._path(device_id)
        if not os.path.exists(p):
            return Memory(device_id=device_id)
        with open(p, encoding="utf-8") as f:
            return Memory(**json.load(f))

    def save(self, mem: Memory) -> None:
        p = self._path(mem.device_id)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(mem), f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)

    def wipe(self, device_id: str) -> None:
        p = self._path(device_id)
        if os.path.exists(p):
            os.remove(p)
