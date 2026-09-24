"""HTTP API for the phone app, the web demo and the voice gateway.

    SUFLET_API_TOKEN=... uvicorn suflet_ai.server:app --port 8787

Every request needs "Authorization: Bearer <SUFLET_API_TOKEN>". Per-device
tokens and accounts come with the real backend; this is the v0 prototype.
"""
from __future__ import annotations

import hmac
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .companion import Companion
from .llm import LlmError

app = FastAPI(title="Suflet AI", version="0.1.0")
_companion: Optional[Companion] = None


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
