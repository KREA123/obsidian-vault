"""Output contracts. JSON Schemas go to the API as structured outputs;
the Pydantic models validate what comes back.

Tone and reaction values mirror the firmware enums in
firmware/lib/Suflet/src/Brain.h (Tone, Reaction), so a reply can drive the
eyes directly.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

TONES = ["neutral", "happy", "sad", "surprised", "cheeky", "sleepy", "love"]
REACTIONS = ["none", "laugh", "love", "shy", "hmph", "confused", "yawn", "celebrate", "boop"]

Tone = Literal["neutral", "happy", "sad", "surprised", "cheeky", "sleepy", "love"]
ReactionName = Literal["none", "laugh", "love", "shy", "hmph", "confused", "yawn", "celebrate", "boop"]


def _obj(props: dict, required: Optional[list] = None) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": required if required is not None else list(props),
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_STR_LIST = {"type": "array", "items": {"type": "string"}}

# ---------------------------------------------------------------- persona --

PERSONA_SCHEMA = _obj(
    {
        "name": _STR,
        "origin_story": _STR,
        "personality_line": _STR,
        "quirks": _STR_LIST,
        "likes": _STR_LIST,
        "dislikes": _STR_LIST,
        "speaking_style": _STR,
        "catchphrase": _STR,
        "first_words": _STR,
        "voice": _obj(
            {
                "pitch": {"type": "string", "enum": ["high", "mid", "low"]},
                "speed": {"type": "string", "enum": ["slow", "normal", "fast"]},
                "texture": _STR,
            }
        ),
    }
)


class Voice(BaseModel):
    pitch: Literal["high", "mid", "low"]
    speed: Literal["slow", "normal", "fast"]
    texture: str


class Persona(BaseModel):
    name: str
    origin_story: str
    personality_line: str
    quirks: List[str]
    likes: List[str]
    dislikes: List[str]
    speaking_style: str
    catchphrase: str
    first_words: str
    voice: Voice


# ------------------------------------------------------------------- turn --

REPLY_SCHEMA = _obj(
    {
        "say": _STR,
        "tone": {"type": "string", "enum": TONES},
        "reaction": {"type": "string", "enum": REACTIONS},
        "remember": _STR_LIST,
        "forget": _STR_LIST,
        "reminders": {"type": "array", "items": _obj({"at": _STR, "text": _STR})},
        "notes": _STR_LIST,
    }
)


class Reminder(BaseModel):
    at: str  # ISO-8601 local date-time, e.g. 2026-09-24T17:00
    text: str


class Reply(BaseModel):
    say: str
    tone: Tone = "neutral"
    reaction: ReactionName = "none"
    remember: List[str] = Field(default_factory=list)
    forget: List[str] = Field(default_factory=list)
    reminders: List[Reminder] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------ diary --

DIARY_SCHEMA = _obj(
    {
        "title": _STR,
        "entry": _STR,
        "mood": {"type": "string", "enum": TONES},
        "highlight": _STR,
        "share_line": _STR,
    }
)


class DiaryEntry(BaseModel):
    title: str
    entry: str
    mood: Tone
    highlight: str
    share_line: str
