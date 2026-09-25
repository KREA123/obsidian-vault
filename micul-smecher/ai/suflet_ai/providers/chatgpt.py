"""ChatGPT mode (bring your own OpenAI API key): the Responses API with function calling.

Same actions, same loop shape as claude.py. Requests are stateless
(store=False) and the conversation is resent each round; reasoning items come
back encrypted so they can be passed along without OpenAI storing them.

The OpenAI SDK is imported lazily so SOUL runs (no-AI and Claude modes)
without it installed.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, List, Optional

from .. import prompts
from ..actions import ACTIONS
from ..config import Settings
from ..dispatcher import ActionResult
from .base import AskContext, AskResult, ProviderError, summarize

log = logging.getLogger("suflet_ai.soul")
MAX_ROUNDS = 4


def openai_model() -> str:
    # A product decision like the Claude model; set SOUL_OPENAI_MODEL to what you tested.
    return os.environ.get("SOUL_OPENAI_MODEL", "gpt-5")


def openai_tools() -> List[dict]:
    return [
        {"type": "function", "name": s.tool_name, "description": s.description,
         "parameters": s.json_schema(), "strict": True}
        for s in ACTIONS.values()
    ]


def _client_for_key(api_key: str) -> Any:
    try:
        import openai
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise ProviderError("the openai package is not installed") from e
    return openai.OpenAI(api_key=api_key)


def _map_error(e: Exception) -> ProviderError:
    try:
        import openai
    except ImportError:  # pragma: no cover
        return ProviderError("ChatGPT error")
    if isinstance(e, openai.AuthenticationError):
        return ProviderError("the OpenAI API key was rejected")
    if isinstance(e, openai.RateLimitError):
        return ProviderError("ChatGPT is rate limited or out of credit, try again later")
    if isinstance(e, openai.APIConnectionError):
        return ProviderError("cannot reach ChatGPT")
    if isinstance(e, openai.APIStatusError):
        return ProviderError(f"OpenAI API error {e.status_code}")
    return ProviderError("ChatGPT error")


def _is_openai_error(e: Exception) -> bool:
    try:
        import openai
    except ImportError:  # pragma: no cover
        return False
    return isinstance(e, openai.OpenAIError)


class ChatGPTProvider:
    name = "chatgpt"

    def __init__(self, settings: Settings, api_key: Optional[str] = None, client: Optional[Any] = None,
                 client_factory: Callable[[str], Any] = _client_for_key, model: Optional[str] = None):
        if client is None and not api_key:
            raise ProviderError("no OpenAI API key set")
        self.settings = settings
        self.model = model or openai_model()
        self._client = client if client is not None else client_factory(api_key)  # type: ignore[arg-type]

    def _create(self, items: List[Any]) -> Any:
        try:
            return self._client.responses.create(
                model=self.model,
                instructions=prompts.SOUL_SYSTEM,
                input=items,
                tools=openai_tools(),
                max_output_tokens=8000,
                store=False,
                include=["reasoning.encrypted_content"],
            )
        except Exception as e:  # noqa: BLE001 - mapped to a safe message below
            if _is_openai_error(e):
                raise _map_error(e) from e
            raise

    def ask(self, ctx: AskContext) -> AskResult:
        items: List[Any] = [{
            "role": "user",
            "content": prompts.soul_user(ctx.now.strftime("%Y-%m-%d %H:%M (%A)"), ctx.lang, ctx.text.strip()[:2000]),
        }]
        results: List[ActionResult] = []
        text = ""
        for _ in range(MAX_ROUNDS):
            resp = self._create(items)
            if getattr(resp, "status", "completed") == "incomplete":
                raise ProviderError("ChatGPT's reply was cut off")
            output = list(resp.output or [])
            for it in output:
                if getattr(it, "type", "") == "message":
                    for part in getattr(it, "content", []) or []:
                        if getattr(part, "type", "") == "refusal":
                            raise ProviderError("ChatGPT declined this request")
            text = (getattr(resp, "output_text", "") or "").strip() or text
            calls = [it for it in output if getattr(it, "type", "") == "function_call"]
            if not calls:
                break
            items += output  # pass back every output item (reasoning + calls) unchanged
            for c in calls:
                try:
                    args = json.loads(c.arguments or "{}")
                except json.JSONDecodeError:
                    args = None
                r = ctx.run(c.name, args if isinstance(args, dict) else {}, source=self.name) if args is not None \
                    else ActionResult(ok=False, action=c.name, error="arguments were not valid JSON")
                results.append(r)
                items.append({"type": "function_call_output", "call_id": c.call_id,
                              "output": json.dumps({"ok": r.ok, "say": r.say, "error": r.error, "id": r.id},
                                                   ensure_ascii=False)})
        else:
            log.warning("chatgpt tool loop hit %d rounds", MAX_ROUNDS)

        say = text or next((r.say for r in reversed(results) if r.ok and r.say), "")
        if not say:
            raise ProviderError("ChatGPT returned no answer")
        return summarize(self.name, ctx.mode, say[:400], results)


def verify_openai_key(api_key: str, client_factory: Callable[[str], Any] = _client_for_key) -> dict:
    """Check a key with a free call (list models). Never returns or logs the key."""
    try:
        client_factory(api_key).models.list()
    except ProviderError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        if _is_openai_error(e):
            return {"ok": False, "error": str(_map_error(e))}
        raise
    return {"ok": True, "error": ""}
