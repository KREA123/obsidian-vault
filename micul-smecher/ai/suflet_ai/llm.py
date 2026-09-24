"""One place that talks to Claude: structured output in, validated model out."""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional, Type, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from .config import FALLBACK_BETA, Settings

log = logging.getLogger("suflet_ai")
T = TypeVar("T", bound=BaseModel)


class LlmError(RuntimeError):
    """The model could not produce a usable answer (refusal, bad output)."""


class Llm:
    def __init__(self, settings: Settings, client: Optional[Any] = None):
        self.settings = settings
        # Credentials come from the environment (ANTHROPIC_API_KEY or an
        # `ant auth login` profile); tests inject a fake client.
        self.client = client if client is not None else anthropic.Anthropic()
        self.last_usage: Any = None

    def structured(
        self,
        *,
        system: List[dict],
        messages: List[dict],
        schema: dict,
        model_cls: Type[T],
        effort: str,
        max_tokens: int = 4096,
    ) -> T:
        kwargs: dict = dict(
            model=self.settings.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        if self.settings.use_fallbacks:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        try:
            resp = self.client.beta.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            raise LlmError("rate limited, try again shortly") from e
        except anthropic.APIConnectionError as e:
            raise LlmError("cannot reach the model") from e
        except anthropic.APIStatusError as e:
            raise LlmError(f"model API error {e.status_code}") from e

        self.last_usage = getattr(resp, "usage", None)
        if resp.stop_reason == "refusal":
            raise LlmError("the model declined this request")
        if resp.stop_reason == "max_tokens":
            raise LlmError("reply was cut off (max_tokens)")
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None)
        if text is None:
            raise LlmError("no text in the reply")
        try:
            return model_cls.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as e:
            log.warning("invalid structured output: %s", text[:300])
            raise LlmError("the reply did not match the expected format") from e
