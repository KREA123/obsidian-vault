"""Runtime configuration, all overridable from the environment."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    # The model is a product decision (latency and cost per user). Claude Opus 5
    # is the default; claude-sonnet-5 or claude-haiku-4-5 are the cheaper,
    # faster options to evaluate for voice. Set SUFLET_MODEL to switch.
    model: str = field(default_factory=lambda: os.environ.get("SUFLET_MODEL", "claude-opus-5"))
    # Spoken replies are short; low effort keeps the reply fast.
    turn_effort: str = field(default_factory=lambda: os.environ.get("SUFLET_TURN_EFFORT", "low"))
    birth_effort: str = field(default_factory=lambda: os.environ.get("SUFLET_BIRTH_EFFORT", "high"))
    diary_effort: str = field(default_factory=lambda: os.environ.get("SUFLET_DIARY_EFFORT", "medium"))
    # Server-side fallback on a safety decline (re-run on the recommended model).
    use_fallbacks: bool = field(
        default_factory=lambda: os.environ.get("SUFLET_FALLBACKS", "1") not in ("0", "false", "no")
    )
    data_dir: str = field(default_factory=lambda: os.environ.get("SUFLET_DATA_DIR", "./data"))
    history_turns: int = 6  # past exchanges resent with each turn
    timezone: str = field(default_factory=lambda: os.environ.get("SUFLET_TZ", "Europe/Bucharest"))


FALLBACK_BETA = "server-side-fallback-2026-07-01"
