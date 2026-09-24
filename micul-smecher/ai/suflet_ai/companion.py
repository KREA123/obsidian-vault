"""The companion service: birth, conversation turns, daily diary."""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

from . import prompts
from .config import Settings
from .llm import Llm, LlmError
from .memory import Memory, MemoryStore
from .schemas import (
    DIARY_SCHEMA,
    PERSONA_SCHEMA,
    REPLY_SCHEMA,
    DiaryEntry,
    Persona,
    Reminder,
    Reply,
)

# Plain words for the firmware's event names, used in TODAY and the diary.
EVENT_WORDS = {
    "boop": "booped",
    "laugh": "made to laugh",
    "purr": "petted",
    "shy": "got shy",
    "dizzy": "shaken (dizzy)",
    "pickup": "picked up / carried",
    "asleep": "napped",
    "missed_you": "missed the owner",
    "claude_busy": "watched Claude work",
    "claude_approve": "approved a Claude request",
    "claude_deny": "denied a Claude request",
    "claude_levelup": "celebrated a Claude milestone",
    "sneeze": "sneezed",
    "hiccup": "had hiccups",
    "night": "night light on",
}

FALLBACK_SAY = {
    "ro": "Hm, mi s-a încurcat firul gândului. Mai zi o dată?",
    "en": "Hmm, I lost my train of thought. Say that again?",
}


class Companion:
    def __init__(self, settings: Optional[Settings] = None, client: Optional[Any] = None):
        self.settings = settings or Settings()
        self.llm = Llm(self.settings, client)
        self.store = MemoryStore(self.settings.data_dir)

    # ------------------------------------------------------------- helpers --
    def now(self) -> dt.datetime:
        return dt.datetime.now(ZoneInfo(self.settings.timezone))

    @staticmethod
    def _stamp(t: dt.datetime) -> str:
        return t.strftime("%Y-%m-%dT%H:%M")

    @staticmethod
    def _human_now(t: dt.datetime) -> str:
        return t.strftime("%Y-%m-%d %H:%M (%A)")

    def _today_lines(self, mem: Memory, day: str) -> List[str]:
        todays = [e for e in mem.events if e["t"].startswith(day)]
        counts: Counter = Counter()
        first: dict = {}
        for e in todays:
            counts[e["ev"]] += e.get("n", 1)
            first.setdefault(e["ev"], e["t"][11:16])
        return [
            f"{EVENT_WORDS.get(ev, ev)} x{n} (first at {first[ev]})" for ev, n in counts.most_common(12)
        ]

    # --------------------------------------------------------------- birth --
    def birth(
        self, device_id: str, seed: str, traits: dict, owner: str = "", language: str = "ro"
    ) -> Persona:
        """Create the character once; later calls return the same one."""
        mem = self.store.load(device_id)
        if mem.persona:
            return mem.persona_model()
        persona = self.llm.structured(
            system=[{"type": "text", "text": prompts.BIRTH_SYSTEM}],
            messages=[{"role": "user", "content": prompts.birth_user(seed, traits, owner, language)}],
            schema=PERSONA_SCHEMA,
            model_cls=Persona,
            effort=self.settings.birth_effort,
            max_tokens=8000,
        )
        mem.persona = persona.model_dump()
        mem.owner = owner or mem.owner
        mem.language = language
        self.store.save(mem)
        return persona

    # ---------------------------------------------------------------- turn --
    def turn(self, device_id: str, said: str, now: Optional[dt.datetime] = None) -> Reply:
        mem = self.store.load(device_id)
        persona = mem.persona_model()
        if persona is None:
            raise LlmError("this device has not been born yet (call birth first)")
        now = now or self.now()
        said = said.strip()[:2000]

        # The system prompt only changes if the persona does, so it is cached.
        system = [
            {
                "type": "text",
                "text": prompts.companion_system(persona),
                "cache_control": {"type": "ephemeral"},
            }
        ]
        messages: List[dict] = []
        for h in mem.history[-self.settings.history_turns :]:
            messages.append({"role": "user", "content": h["user"]})
            messages.append({"role": "assistant", "content": h["assistant"]})
        user = prompts.turn_user(
            self._human_now(now), mem.owner, mem.facts, self._today_lines(mem, now.strftime("%Y-%m-%d")), said
        )
        messages.append({"role": "user", "content": user})

        try:
            reply = self.llm.structured(
                system=system,
                messages=messages,
                schema=REPLY_SCHEMA,
                model_cls=Reply,
                effort=self.settings.turn_effort,
                max_tokens=2048,
            )
        except LlmError:
            return Reply(say=FALLBACK_SAY.get(mem.language, FALLBACK_SAY["en"]), tone="neutral", reaction="confused")

        reply.say = reply.say.strip()[:400]
        stamp = self._stamp(now)
        mem.apply(reply, stamp)
        # keep the history short; the assistant side is the JSON it produced
        mem.history.append({"user": f"USER SAID: {said}", "assistant": reply.model_dump_json()})
        mem.history = mem.history[-self.settings.history_turns :]
        mem.topics.append({"t": stamp, "said": said[:80]})
        mem.topics = mem.topics[-100:]
        self.store.save(mem)
        return reply

    def due_reminders(self, device_id: str, now: Optional[dt.datetime] = None) -> List[Reminder]:
        mem = self.store.load(device_id)
        due = mem.due_reminders(self._stamp(now or self.now()))
        if due:
            self.store.save(mem)
        return due

    def log_events(self, device_id: str, events: List[dict]) -> int:
        mem = self.store.load(device_id)
        before = len(mem.events)
        mem.add_events(events)
        self.store.save(mem)
        return len(mem.events) - before

    # --------------------------------------------------------------- diary --
    def diary(self, device_id: str, day: Optional[str] = None) -> DiaryEntry:
        mem = self.store.load(device_id)
        persona = mem.persona_model()
        if persona is None:
            raise LlmError("this device has not been born yet (call birth first)")
        day = day or self.now().strftime("%Y-%m-%d")
        todays = [e for e in mem.events if e["t"].startswith(day)]
        counts: Counter = Counter()
        for e in todays:
            counts[EVENT_WORDS.get(e["ev"], e["ev"])] += e.get("n", 1)
        hours = sorted({e["t"][11:13] for e in todays})
        summary = {"counts": dict(counts.most_common(15)), "active_hours": hours}
        topics = [t["said"] for t in mem.topics if t["t"].startswith(day)]
        return self.llm.structured(
            system=[{"type": "text", "text": prompts.diary_system(persona)}],
            messages=[
                {"role": "user", "content": prompts.diary_user(day, mem.owner, mem.language, summary, topics)}
            ],
            schema=DIARY_SCHEMA,
            model_cls=DiaryEntry,
            effort=self.settings.diary_effort,
            max_tokens=4000,
        )

    # ------------------------------------------------------------- privacy --
    def export(self, device_id: str) -> dict:
        mem = self.store.load(device_id)
        return json.loads(json.dumps(mem.__dict__, ensure_ascii=False))

    def forget_everything(self, device_id: str) -> None:
        self.store.wipe(device_id)
