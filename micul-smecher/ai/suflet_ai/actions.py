"""SOUL actions: the one typed API every mode uses.

The phone app, the on-device keyboard, the offline parser, Claude (API key or
connector) and ChatGPT (API key or app) all end up calling the same actions.
Each action has a Pydantic model (validation) and a JSON Schema (for LLM tool
use). The schemas are strict-mode compatible for both Anthropic and OpenAI:
every object lists all its properties as required and forbids extra ones, so
"optional" fields take an empty value ("" or []) instead of being left out.

Action names use dots (note.create) like os/ARCHITECTURE.md; LLM tool names
cannot contain dots, so they use underscores (note_create).
"""
from __future__ import annotations

import re
from typing import Dict, List, Literal, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_WHEN = re.compile(r"^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d$")


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NoteCreate(_Args):
    text: str = Field(min_length=1, max_length=2000, description="The note text, as the user said it.")
    tags: List[str] = Field(default_factory=list, max_length=10, description="Optional short tags; [] if none.")


class ReminderCreate(_Args):
    when: str = Field(description="Local date-time YYYY-MM-DDTHH:MM, computed from NOW.")
    text: str = Field(min_length=1, max_length=300, description="What to remind, short (e.g. 'call the bank').")

    @field_validator("when")
    @classmethod
    def _when(cls, v: str) -> str:
        if not _WHEN.match(v):
            raise ValueError("when must be local YYYY-MM-DDTHH:MM")
        return v


class AlarmSet(_Args):
    hhmm: str = Field(description="Alarm time, 24h HH:MM.")
    days: List[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(
        default_factory=list, description="Repeat days; [] means once (the next time HH:MM comes)."
    )
    label: str = Field(default="", max_length=60, description="Optional label; '' if none.")

    @field_validator("hhmm")
    @classmethod
    def _hhmm(cls, v: str) -> str:
        if not _HHMM.match(v):
            raise ValueError("hhmm must be 24h HH:MM")
        return v


class TimerStart(_Args):
    seconds: int = Field(ge=1, le=24 * 3600, description="Duration in seconds.")
    label: str = Field(default="", max_length=60, description="Optional label; '' if none.")


class FocusStart(_Args):
    minutes: int = Field(ge=1, le=240, description="Focus session length in minutes (25 is a classic).")
    label: str = Field(default="", max_length=60, description="What the focus is on; '' if none.")


class MessageDraft(_Args):
    to: str = Field(min_length=1, max_length=80, description="Recipient name as the user said it.")
    text: str = Field(min_length=1, max_length=1000, description="The message text.")
    channel: Literal["any", "sms", "whatsapp", "email"] = Field(
        default="any", description="Preferred channel; 'any' if not said."
    )


class ListAdd(_Args):
    list: str = Field(min_length=1, max_length=40, description="List name, e.g. 'shopping' / 'cumpărături'.")
    items: List[str] = Field(min_length=1, max_length=30, description="Items to add, one per entry.")


class AnswerShow(_Args):
    say: str = Field(min_length=1, max_length=400, description="What SOUL says aloud (<= 2 short sentences).")
    title: str = Field(default="", max_length=60, description="Card title on the round screen; '' for none.")
    body: str = Field(default="", max_length=600, description="Card body text (plain text); '' for none.")


class ActionSpec(BaseModel):
    name: str
    description: str
    model: Type[_Args]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def tool_name(self) -> str:
        return self.name.replace(".", "_")

    def json_schema(self) -> dict:
        return strict_schema(self.model)


ACTIONS: Dict[str, ActionSpec] = {
    s.name: s
    for s in [
        ActionSpec(name="note.create", model=NoteCreate,
                   description="Save a note on SOUL (it syncs to the phone). Use when the user says note / "
                               "write down / save / notează / scrie."),
        ActionSpec(name="reminder.create", model=ReminderCreate,
                   description="Create a reminder that SOUL shows and says at a local date-time. If the "
                               "time is unclear, ask instead of guessing."),
        ActionSpec(name="alarm.set", model=AlarmSet,
                   description="Set a wake-up alarm on SOUL (rings from any power state)."),
        ActionSpec(name="timer.start", model=TimerStart,
                   description="Start a countdown timer on SOUL."),
        ActionSpec(name="focus.start", model=FocusStart,
                   description="Start a focus session on SOUL (do-not-disturb plus a ring that fills up)."),
        ActionSpec(name="message.draft", model=MessageDraft,
                   description="Draft a message for the user to review and send from their phone. SOUL "
                               "never sends messages on its own."),
        ActionSpec(name="list.add", model=ListAdd,
                   description="Add items to a named list (shopping, to-do, packing...)."),
        ActionSpec(name="answer.show", model=AnswerShow,
                   description="Show an answer on SOUL's round screen as a card and say it aloud. Use for "
                               "answers worth keeping on screen (a translation, a short list, a fact)."),
    ]
}

TOOL_TO_ACTION = {s.tool_name: s.name for s in ACTIONS.values()}


def strict_schema(model: Type[BaseModel]) -> dict:
    """A plain JSON Schema for the model, made strict: all properties required,
    no extra properties, no titles/defaults (both vendors reject or ignore them)."""
    raw = model.model_json_schema()

    def clean(s: dict) -> dict:
        out: dict = {}
        for k, v in s.items():
            if k in ("title", "default"):
                continue
            if k == "properties":
                out[k] = {pk: clean(pv) for pk, pv in v.items()}
            elif k == "items" and isinstance(v, dict):
                out[k] = clean(v)
            else:
                out[k] = v
        if out.get("type") == "object":
            out["required"] = list(out.get("properties", {}))
            out["additionalProperties"] = False
        # length limits are enforced by Pydantic on our side; strict tool
        # schemas on some providers reject these keywords.
        for k in ("minLength", "maxLength", "minItems", "maxItems", "pattern", "minimum", "maximum"):
            out.pop(k, None)
        return out

    return clean(raw)


def action_catalog() -> List[dict]:
    """Machine-readable list of actions (for the phone app and docs)."""
    return [{"name": s.name, "tool": s.tool_name, "description": s.description, "schema": s.json_schema()}
            for s in ACTIONS.values()]
