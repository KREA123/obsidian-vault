#!/usr/bin/env python3
"""A local stand-in for api.anthropic.com and api.openai.com, for end-to-end tests without real keys.

It answers the two calls the relay makes, in the providers' wire format as the official SDKs parse it:

    POST /v1/messages          (Anthropic Messages API; also /v1/messages?beta=true)
    POST /v1/responses         (OpenAI Responses API; served at /v1/responses and /openai/v1/responses)

Point the SDKs at it with their standard environment variables (no code change in the relay):

    ANTHROPIC_BASE_URL=http://127.0.0.1:8799            OPENAI_BASE_URL=http://127.0.0.1:8799/v1

The "model" is a script, so a test can predict every answer:

    user text contains "remind"  -> tool call reminder_create {when: NOW's next day 09:00, text}
    user text contains "note"    -> tool call note_create {text}
    user text contains "#refuse" -> a refusal (Anthropic stop_reason "refusal"; OpenAI refusal part)
    anything else                -> a short text answer ("Hi from fake Claude" / "Hi from fake ChatGPT")
    after a tool result          -> "Done: ..." text

The API key picks a failure, like a real account would produce it:

    key contains "bad"        -> 401 (authentication_error / invalid_api_key)
    key contains "ratelimit"  -> 429 rate limit (retry-after: 0)
    key contains "quota"      -> Anthropic 400 "credit balance is too low" [L: as observed in the wild],
                                 OpenAI 429 insufficient_quota
    key contains "overloaded" -> Anthropic 529 overloaded_error, OpenAI 503
    anything else             -> 200

Like the real Haiku 4.5, a request for `claude-haiku-4-5` that carries `output_config.effort` gets a 400.

GET /__fake/requests lists what was received (path, model, top-level body keys, the user text, the
result) without any key or header; POST /__fake/reset clears it. Keys are never stored or printed.

    python tools/fake_llm.py --port 8799
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import secrets
import threading
from typing import Any, Dict, List, Optional, Tuple

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

_NOW = re.compile(r"NOW: (\d{4}-\d{2}-\d{2})")


def _key_kind(key: str) -> str:
    k = (key or "").lower()
    for kind in ("bad", "ratelimit", "quota", "overloaded"):
        if kind in k:
            return kind
    return "ok" if k else "missing"


def _said(user_text: str) -> str:
    return user_text.split("USER SAID:", 1)[-1].strip()


def _tomorrow_9(user_text: str) -> str:
    m = _NOW.search(user_text)
    day = dt.date.fromisoformat(m.group(1)) if m else dt.date.today()
    return (day + dt.timedelta(days=1)).isoformat() + "T09:00"


def script(user_text: str) -> Tuple[str, Any]:
    """-> ("tool", (name, args)) | ("text", str) | ("refuse", None)."""
    said = _said(user_text)
    low = said.lower()
    if "#refuse" in low:
        return "refuse", None
    if "remind" in low or "amintește" in low:
        what = re.split(r"\bto\b|\bsă\b", said, maxsplit=1)[-1].strip(" .") if re.search(r"\bto\b|\bsă\b", said) \
            else said
        return "tool", ("reminder_create", {"when": _tomorrow_9(user_text), "text": what[:80] or "reminder"})
    if "note" in low or "notează" in low:
        what = re.split(r"note[: ]", said, maxsplit=1, flags=re.I)[-1].strip(" .")
        return "tool", ("note_create", {"text": what[:200] or said[:200]})
    return "text", None


class Recorder:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.rows: List[dict] = []

    def add(self, row: dict) -> None:
        with self.lock:
            self.rows.append(row)

    def all(self) -> List[dict]:
        with self.lock:
            return list(self.rows)

    def reset(self) -> None:
        with self.lock:
            self.rows.clear()


# ================================================================ Anthropic ==

def _anthropic_error(status: int, etype: str, msg: str, headers: Optional[dict] = None) -> JSONResponse:
    return JSONResponse({"type": "error", "error": {"type": etype, "message": msg},
                         "request_id": "req_fake"}, status_code=status, headers=headers)


def _last_user_text(messages: List[dict]) -> Tuple[str, bool]:
    """-> (text of the first user message, whether the last user message carries tool results)."""
    first = ""
    for m in messages:
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                first = first or c
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "text":
                        first = first or b.get("text", "")
    last = messages[-1] if messages else {}
    has_result = isinstance(last.get("content"), list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in last["content"])
    return first, has_result


def _user_text_anthropic(messages: List[dict]) -> str:
    # with history the first user message is an old one: take the newest plain-text user message
    for m in reversed(messages):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return m["content"]
    return _last_user_text(messages)[0]


async def anthropic_messages(request: Request) -> JSONResponse:
    rec: Recorder = request.app.state.rec
    key = request.headers.get("x-api-key", "")
    body = await request.json()
    model = body.get("model", "")
    messages = body.get("messages") or []
    user = _user_text_anthropic(messages)
    _, after_tool = _last_user_text(messages)
    kind = _key_kind(key)
    row = {"api": "anthropic", "path": request.url.path, "beta": request.query_params.get("beta") == "true",
           "model": model, "keys": sorted(body), "effort": (body.get("output_config") or {}).get("effort"),
           "thinking": body.get("thinking"), "tools": [t.get("name") for t in body.get("tools") or []],
           "said": _said(user), "after_tool": after_tool, "key_kind": kind,
           "anthropic_version": request.headers.get("anthropic-version")}

    def done(resp: JSONResponse, result: str) -> JSONResponse:
        row["result"] = result
        rec.add(row)
        return resp

    if kind == "missing":
        return done(_anthropic_error(401, "authentication_error", "x-api-key header is required"), "401")
    if kind == "bad":
        return done(_anthropic_error(401, "authentication_error", "invalid x-api-key"), "401")
    if kind == "ratelimit":
        return done(_anthropic_error(429, "rate_limit_error", "Number of request tokens has exceeded your "
                                     "per-minute rate limit", {"retry-after": "0"}), "429")
    if kind == "quota":
        return done(_anthropic_error(400, "invalid_request_error", "Your credit balance is too low to access the "
                                     "Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."),
                    "400-credit")
    if kind == "overloaded":
        return done(_anthropic_error(529, "overloaded_error", "Overloaded"), "529")
    if model == "claude-haiku-4-5" and (body.get("output_config") or {}).get("effort"):
        return done(_anthropic_error(400, "invalid_request_error", "output_config.effort: this model does not "
                                     "support the effort parameter"), "400-effort")
    usage = {"input_tokens": 1800 + len(user) // 4, "output_tokens": 40, "cache_creation_input_tokens": 0,
             "cache_read_input_tokens": 0}
    base = {"id": "msg_" + secrets.token_hex(8), "type": "message", "role": "assistant", "model": model,
            "stop_sequence": None, "usage": usage}
    if after_tool:
        return done(JSONResponse({**base, "content": [{"type": "text", "text": "Done: it is on your SOUL."}],
                                  "stop_reason": "end_turn"}), "text")
    what, data = script(user)
    if what == "refuse":
        return done(JSONResponse({**base, "content": [], "stop_reason": "refusal"}), "refusal")
    if what == "tool":
        name, args = data
        return done(JSONResponse({**base, "content": [
            {"type": "text", "text": "On it."},
            {"type": "tool_use", "id": "toolu_" + secrets.token_hex(8), "name": name, "input": args}],
            "stop_reason": "tool_use"}), "tool:" + name)
    return done(JSONResponse({**base, "content": [{"type": "text", "text": "Hi from fake Claude!"}],
                              "stop_reason": "end_turn"}), "text")


# =================================================================== OpenAI ==

def _openai_error(status: int, etype: str, code: Optional[str], msg: str,
                  headers: Optional[dict] = None) -> JSONResponse:
    return JSONResponse({"error": {"message": msg, "type": etype, "param": None, "code": code}},
                        status_code=status, headers=headers)


def _openai_user_text(items: List[Any]) -> Tuple[str, bool]:
    text, after_tool = "", False
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("role") == "user":
            c = it.get("content")
            text = c if isinstance(c, str) else " ".join(
                p.get("text", "") for p in (c or []) if isinstance(p, dict))
            after_tool = False
        elif it.get("type") == "function_call_output":
            after_tool = True
    return text, after_tool


async def openai_responses(request: Request) -> JSONResponse:
    rec: Recorder = request.app.state.rec
    key = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    body = await request.json()
    model = body.get("model", "")
    user, after_tool = _openai_user_text(body.get("input") or [])
    kind = _key_kind(key)
    row = {"api": "openai", "path": request.url.path, "model": model, "keys": sorted(body),
           "store": body.get("store"), "reasoning": body.get("reasoning"),
           "safety_identifier_len": len(body.get("safety_identifier") or ""),
           "tools": [t.get("name") for t in body.get("tools") or []], "said": _said(user), "after_tool": after_tool,
           "key_kind": kind}

    def done(resp: JSONResponse, result: str) -> JSONResponse:
        row["result"] = result
        rec.add(row)
        return resp

    if kind in ("missing", "bad"):
        return done(_openai_error(401, "invalid_request_error", "invalid_api_key",
                                  "Incorrect API key provided."), "401")
    if kind == "ratelimit":
        return done(_openai_error(429, "requests", "rate_limit_exceeded", "Rate limit reached for requests",
                                  {"retry-after": "0"}), "429")
    if kind == "quota":
        return done(_openai_error(429, "insufficient_quota", "insufficient_quota",
                                  "You exceeded your current quota, please check your plan and billing details."),
                    "429-quota")
    if kind == "overloaded":
        return done(_openai_error(503, "server_error", None, "The server is overloaded."), "503")
    usage = {"input_tokens": 1700 + len(user) // 4, "input_tokens_details": {"cached_tokens": 0},
             "output_tokens": 35, "output_tokens_details": {"reasoning_tokens": 0},
             "total_tokens": 1735 + len(user) // 4}
    base = {"id": "resp_" + secrets.token_hex(8), "object": "response", "created_at": int(dt.datetime.now().timestamp()),
            "status": "completed", "model": model, "usage": usage, "parallel_tool_calls": True, "tool_choice": "auto",
            "tools": [], "error": None, "incomplete_details": None, "instructions": None, "metadata": {},
            "temperature": 1.0, "top_p": 1.0}

    def message(text: str, kind_: str = "output_text") -> dict:
        part = {"type": "output_text", "text": text, "annotations": []} if kind_ == "output_text" else \
            {"type": "refusal", "refusal": text}
        return {"type": "message", "id": "msg_" + secrets.token_hex(8), "status": "completed", "role": "assistant",
                "content": [part]}

    if after_tool:
        return done(JSONResponse({**base, "output": [message("Done: it is on your SOUL.")]}), "text")
    what, data = script(user)
    if what == "refuse":
        return done(JSONResponse({**base, "output": [message("I can't help with that.", "refusal")]}), "refusal")
    if what == "tool":
        name, args = data
        return done(JSONResponse({**base, "output": [{
            "type": "function_call", "id": "fc_" + secrets.token_hex(8), "call_id": "call_" + secrets.token_hex(8),
            "name": name, "arguments": json.dumps(args), "status": "completed"}]}), "tool:" + name)
    return done(JSONResponse({**base, "output": [message("Hi from fake ChatGPT!")]}), "text")


# ===================================================================== app ==

def create_app() -> Starlette:
    async def requests_(request: Request) -> JSONResponse:
        return JSONResponse(request.app.state.rec.all())

    async def reset(request: Request) -> JSONResponse:
        request.app.state.rec.reset()
        return JSONResponse({"ok": True})

    app = Starlette(routes=[
        Route("/v1/messages", anthropic_messages, methods=["POST"]),
        Route("/v1/responses", openai_responses, methods=["POST"]),
        Route("/openai/v1/responses", openai_responses, methods=["POST"]),
        Route("/__fake/requests", requests_, methods=["GET"]),
        Route("/__fake/reset", reset, methods=["POST"]),
    ])
    app.state.rec = Recorder()
    return app


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="Fake Anthropic + OpenAI HTTP APIs for SOUL end-to-end tests")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8799)
    a = ap.parse_args(argv)
    import uvicorn

    uvicorn.run(create_app(), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
