"""HTTP API for the SOUL device, the phone app, the web demo and the voice gateway.

    SUFLET_API_TOKEN=... uvicorn suflet_ai.server:app --port 8787

Every request needs "Authorization: Bearer <SUFLET_API_TOKEN>". Per-device
tokens and accounts come with the real backend; this is the v0 prototype.
"""
from __future__ import annotations

import hmac
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr

from .actions import action_catalog
from .companion import Companion
from .llm import LlmError
from .soul import SoulService

app = FastAPI(title="SOUL AI", version="0.2.0")
_companion: Optional[Companion] = None
_soul: Optional[SoulService] = None


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    # FastAPI echoes the offending input by default; a request body may hold an API key.
    errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


def soul() -> SoulService:
    global _soul
    if _soul is None:
        _soul = SoulService()
    return _soul


def companion() -> Companion:
    global _companion
    if _companion is None:
        _companion = Companion()
    return _companion


def auth(authorization: str = Header(default="")) -> None:
    token = os.environ.get("SUFLET_API_TOKEN", "")
    if not token:
        raise HTTPException(503, "server token not configured")
    given = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(given, token):
        raise HTTPException(401, "bad token")


class BirthIn(BaseModel):
    seed: str = Field(max_length=32)
    traits: dict = Field(default_factory=dict)
    owner: str = Field(default="", max_length=40)
    language: str = Field(default="ro", max_length=8)


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class EventsIn(BaseModel):
    events: List[dict] = Field(default_factory=list, max_length=5000)


@app.post("/v1/devices/{device_id}/birth", dependencies=[Depends(auth)])
def birth(device_id: str, body: BirthIn):
    try:
        return companion().birth(device_id, body.seed, body.traits, body.owner, body.language).model_dump()
    except (LlmError, ValueError) as e:
        raise HTTPException(422, str(e))


@app.post("/v1/devices/{device_id}/turn", dependencies=[Depends(auth)])
def turn(device_id: str, body: TurnIn):
    try:
        reply = companion().turn(device_id, body.text)
    except (LlmError, ValueError) as e:
        raise HTTPException(422, str(e))
    return reply.model_dump()


@app.post("/v1/devices/{device_id}/events", dependencies=[Depends(auth)])
def events(device_id: str, body: EventsIn):
    try:
        return {"added": companion().log_events(device_id, body.events)}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/v1/devices/{device_id}/reminders/due", dependencies=[Depends(auth)])
def due(device_id: str):
    try:
        return [r.model_dump() for r in companion().due_reminders(device_id)]
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/v1/devices/{device_id}/diary", dependencies=[Depends(auth)])
def diary(device_id: str, day: Optional[str] = None):
    try:
        return companion().diary(device_id, day).model_dump()
    except (LlmError, ValueError) as e:
        raise HTTPException(422, str(e))


@app.get("/v1/devices/{device_id}/memory", dependencies=[Depends(auth)])
def memory(device_id: str):
    """Everything it remembers, readable by the owner."""
    try:
        return companion().export(device_id)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.delete("/v1/devices/{device_id}/memory", dependencies=[Depends(auth)])
def forget(device_id: str):
    try:
        companion().forget_everything(device_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"forgotten": True}


# =============================================================== SOUL v1 ==
# The same endpoints serve every AI mode (none / claude / chatgpt). The device
# id travels in the body (or query), so one token can serve a user's devices.

DeviceId = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class AskIn(BaseModel):
    device_id: str = DeviceId
    text: str = Field(min_length=1, max_length=2000)
    lang: Optional[str] = Field(default=None, pattern=r"^(ro|en)$")


class ActionIn(BaseModel):
    device_id: str = DeviceId
    name: str = Field(max_length=40)
    args: dict = Field(default_factory=dict)
    lang: str = Field(default="en", pattern=r"^(ro|en)$")


class ModeIn(BaseModel):
    device_id: str = DeviceId
    mode: str = Field(pattern=r"^(none|claude|chatgpt)$")
    lang: Optional[str] = Field(default=None, pattern=r"^(ro|en)$")


class KeyIn(BaseModel):
    device_id: str = DeviceId
    provider: str = Field(pattern=r"^(anthropic|openai)$")
    api_key: SecretStr  # never echoed, never in reprs or validation errors


class KeyTestIn(BaseModel):
    device_id: str = DeviceId
    provider: str = Field(pattern=r"^(anthropic|openai)$")
    api_key: Optional[SecretStr] = None  # test a key before saving it; omitted = the stored one


def _bad(e: Exception):
    raise HTTPException(422, str(e))


@app.post("/v1/ask", dependencies=[Depends(auth)])
def ask(body: AskIn):
    """Text in, {say, face, card, chips, actions, provider, mode, note} out, in any AI mode."""
    try:
        return soul().ask(body.device_id, body.text, lang=body.lang).model_dump()
    except ValueError as e:
        _bad(e)


@app.post("/v1/action", dependencies=[Depends(auth)])
def action(body: ActionIn):
    """Run one typed action directly (phone app UI, on-device keyboard)."""
    try:
        r = soul().action(body.device_id, body.name, body.args, lang=body.lang, source="app")
    except ValueError as e:
        _bad(e)
    if not r.ok:
        raise HTTPException(422, r.error)
    return r.model_dump()


@app.get("/v1/actions", dependencies=[Depends(auth)])
def actions():
    """The action catalog with JSON Schemas (same ones the LLMs get)."""
    return action_catalog()


@app.get("/v1/mode", dependencies=[Depends(auth)])
def get_mode(device_id: str):
    try:
        return soul().mode_info(device_id)
    except ValueError as e:
        _bad(e)


@app.post("/v1/mode", dependencies=[Depends(auth)])
def set_mode(body: ModeIn):
    s = soul()
    try:
        s.set_mode(body.device_id, body.mode)
        if body.lang:
            s.state.set_setting(body.device_id, "lang", body.lang)
        return s.mode_info(body.device_id)
    except ValueError as e:
        _bad(e)


@app.get("/v1/key", dependencies=[Depends(auth)])
def key_status(device_id: str):
    """Which keys are set. Never returns a key or any part of it."""
    try:
        return soul().keys.status(device_id)
    except ValueError as e:
        _bad(e)


@app.post("/v1/key", dependencies=[Depends(auth)])
def set_key(body: KeyIn):
    try:
        return soul().set_key(body.device_id, body.provider, body.api_key.get_secret_value())
    except ValueError as e:
        _bad(e)


@app.post("/v1/key/test", dependencies=[Depends(auth)])
def test_key(body: KeyTestIn):
    try:
        key = body.api_key.get_secret_value() if body.api_key else None
        return soul().test_key(body.device_id, body.provider, key)
    except ValueError as e:
        _bad(e)


@app.delete("/v1/key", dependencies=[Depends(auth)])
def remove_key(device_id: str, provider: str):
    try:
        return soul().remove_key(device_id, provider)
    except ValueError as e:
        _bad(e)


@app.get("/v1/today", dependencies=[Depends(auth)])
def today(device_id: str, day: Optional[str] = None):
    try:
        return soul().today(device_id, day)
    except ValueError as e:
        _bad(e)


@app.get("/v1/sync", dependencies=[Depends(auth)])
def sync(device_id: str, since: int = 0):
    """Items created after `since` (use the last id you have); the device pulls this."""
    try:
        return soul().sync(device_id, since)
    except ValueError as e:
        _bad(e)


@app.get("/v1/due", dependencies=[Depends(auth)])
def due_soul(device_id: str):
    """Reminders whose time has come; each is returned once."""
    try:
        return soul().due(device_id)
    except ValueError as e:
        _bad(e)
