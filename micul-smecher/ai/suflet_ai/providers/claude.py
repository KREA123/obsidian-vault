"""Claude mode (bring your own Anthropic API key): Claude calls SOUL actions as tools.

A small manual tool loop over the Messages API: we need to run each tool call
against this device's state with the caller's clock and language, and cap the
number of rounds for a voice device. Tools are generated from actions.ACTIONS
with strict schemas, so arguments arrive schema-valid; the dispatcher still
validates them and returns errors as tool results so Claude can correct itself.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, List, Optional

import anthropic

from .. import prompts
from ..actions import ACTIONS
from ..config import FALLBACK_BETA, Settings
from ..dispatcher import ActionResult
from .base import AskContext, AskResult, ProviderError, summarize

log = logging.getLogger("suflet_ai.soul")

MAX_ROUNDS = 4  # model calls per request; a voice device can't wait for long agent loops


def claude_tools() -> List[dict]:
    return [
        {"name": s.tool_name, "description": s.description, "input_schema": s.json_schema(), "strict": True}
        for s in ACTIONS.values()
    ]


def _client_for_key(api_key: str) -> Any:
    return anthropic.Anthropic(api_key=api_key)


def _tool_result_content(r: ActionResult) -> str:
    return json.dumps({"ok": r.ok, "say": r.say, "error": r.error, "id": r.id, "data": r.data}, ensure_ascii=False)


class ClaudeProvider:
    name = "claude"

    def __init__(self, settings: Settings, api_key: Optional[str] = None, client: Optional[Any] = None,
                 client_factory: Callable[[str], Any] = _client_for_key):
        if client is None and not api_key:
            raise ProviderError("no Anthropic API key set")
        self.settings = settings
        # The key lives only in this object for the length of the request.
        self._client = client if client is not None else client_factory(api_key)  # type: ignore[arg-type]

    def _create(self, messages: List[dict]) -> Any:
        kwargs: dict = dict(
            model=self.settings.model,
            max_tokens=8000,  # short spoken replies; leaves room for adaptive thinking
            system=[{"type": "text", "text": prompts.SOUL_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=claude_tools(),
            messages=messages,
            output_config={"effort": self.settings.turn_effort},
        )
        if self.settings.use_fallbacks:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        try:
            return self._client.beta.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise ProviderError("the Anthropic API key was rejected") from e
        except anthropic.PermissionDeniedError as e:
            raise ProviderError("the Anthropic API key has no access to this model") from e
        except anthropic.RateLimitError as e:
            raise ProviderError("Claude is rate limited, try again shortly") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError("cannot reach Claude") from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"Claude API error {e.status_code}") from e

    def ask(self, ctx: AskContext) -> AskResult:
        messages: List[dict] = [{
            "role": "user",
            "content": prompts.soul_user(ctx.now.strftime("%Y-%m-%d %H:%M (%A)"), ctx.lang, ctx.text.strip()[:2000]),
        }]
        results: List[ActionResult] = []
        text = ""
        for _ in range(MAX_ROUNDS):
            resp = self._create(messages)
            if resp.stop_reason == "refusal":
                raise ProviderError("Claude declined this request")
            if resp.stop_reason == "max_tokens":
                raise ProviderError("Claude's reply was cut off")
            blocks = list(resp.content or [])
            text = " ".join(b.text for b in blocks if getattr(b, "type", "") == "text").strip() or text
            calls = [b for b in blocks if getattr(b, "type", "") == "tool_use"]
            if resp.stop_reason != "tool_use" or not calls:
                break
            # Return every tool result in ONE user message (keeps parallel calls working).
            tool_results = []
            for c in calls:
                r = ctx.run(c.name, dict(c.input or {}), source=self.name)
                results.append(r)
                tool_results.append({"type": "tool_result", "tool_use_id": c.id,
                                     "content": _tool_result_content(r), "is_error": not r.ok})
            messages.append({"role": "assistant", "content": blocks})  # unchanged, incl. thinking blocks
            messages.append({"role": "user", "content": tool_results})
        else:
            log.warning("claude tool loop hit %d rounds", MAX_ROUNDS)

        say = text or next((r.say for r in reversed(results) if r.ok and r.say), "")
        if not say:
            raise ProviderError("Claude returned no answer")
        return summarize(self.name, ctx.mode, say[:400], results)


def verify_anthropic_key(api_key: str, client_factory: Callable[[str], Any] = _client_for_key) -> dict:
    """Check a key with a free call (list one model). Never returns or logs the key."""
    try:
        client_factory(api_key).models.list(limit=1)
    except anthropic.AuthenticationError:
        return {"ok": False, "error": "key rejected by Anthropic"}
    except anthropic.PermissionDeniedError:
        return {"ok": False, "error": "key has no permission"}
    except anthropic.APIConnectionError:
        return {"ok": False, "error": "cannot reach Anthropic"}
    except anthropic.APIStatusError as e:
        return {"ok": False, "error": f"Anthropic API error {e.status_code}"}
    return {"ok": True, "error": ""}
