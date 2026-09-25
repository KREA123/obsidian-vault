"""The provider interface and the answer shape shared by every mode."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional, Protocol

from pydantic import BaseModel, Field

from ..dispatcher import ActionResult, Dispatcher


class ProviderError(RuntimeError):
    """The provider could not produce an answer (no key, refusal, network, bad output).

    Messages are safe to show and log: they never contain the API key."""


class AskResult(BaseModel):
    """What SOUL shows and says: {say, card, face, chips, actions} (os/ARCHITECTURE.md D5)."""

    say: str
    provider: str  # "rules" | "claude" | "chatgpt"
    mode: str = "none"
    face: str = "neutral"  # a firmware Tone (schemas.TONES)
    card: Optional[dict] = None
    chips: List[str] = Field(default_factory=list)
    actions: List[ActionResult] = Field(default_factory=list)
    note: str = ""  # why a fallback happened, for the app (never shown as an error on the stone)


@dataclass
class AskContext:
    device: str
    text: str
    now: dt.datetime
    lang: str  # "ro" | "en" (best guess; providers may reply in the user's language anyway)
    dispatcher: Dispatcher
    mode: str = "none"

    def run(self, name: str, args: dict, source: str) -> ActionResult:
        return self.dispatcher.dispatch(self.device, name, args, lang=self.lang, source=source, now=self.now)


class Provider(Protocol):
    name: str

    def ask(self, ctx: AskContext) -> AskResult: ...


def summarize(provider: str, mode: str, say: str, results: List[ActionResult]) -> AskResult:
    """Build the AskResult after a provider ran some actions."""
    ok = [r for r in results if r.ok]
    card = next((r.card for r in reversed(ok) if r.card), None)
    face = "happy" if ok else ("confused" if results else "neutral")
    return AskResult(say=say, provider=provider, mode=mode, face=face, card=card, actions=results)
