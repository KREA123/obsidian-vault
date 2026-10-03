"""Shared kit for the device-gateway tests: a service, a store, a gateway app, signed auth, fake LLM clients.

No network, no real keys: LLM clients are fakes that record requests and replay scripted responses.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from suflet_ai.config import Settings
from suflet_ai.devices import DeviceStore
from suflet_ai.gateway import Gateway, build_dev_router, build_router
from suflet_ai.relay import Relay
from suflet_ai.soul import SoulService
from suflet_ai.state import StateStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fake_device import DeviceKey, FakeDevice, Http, WsAdapter, auth_message  # noqa: E402

HOST = "soul.example"
DEV = "soul-a1b2c3d4e5f6"
DEV2 = "soul-0011223344ff"
TZ = ZoneInfo("Europe/Bucharest")
NOW = dt.datetime(2026, 10, 3, 10, 0, tzinfo=TZ)
ANT_KEY = "sk-ant-api03-TESTKEY-abcdefghijklmnopqrstuvwxyz0123456789"
OAI_KEY = "sk-proj-TESTKEY-abcdefghijklmnopqrstuvwxyz0123456789"
SERVER_ANT = "sk-ant-api03-SERVERKEY-zyxwvutsrqponmlkjihgfedcba987654"
VECTOR = json.loads((Path(__file__).parent / "vectors" / "device_auth.json").read_text())


class Clock:
    def __init__(self, t: float = NOW.timestamp()):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


# ------------------------------------------------------------------ fake LLMs --

def block(type_, **kw):
    return SimpleNamespace(type=type_, **kw)


def a_resp(stop, *blocks, inp=100, out=20):
    return SimpleNamespace(stop_reason=stop, content=list(blocks),
                           usage=SimpleNamespace(input_tokens=inp, output_tokens=out))


def a_tool(id_, name, **inp):
    return block("tool_use", id=id_, name=name, input=inp)


def a_text(t):
    return a_resp("end_turn", block("thinking", thinking="", signature="sig"), block("text", text=t))


class FakeAnthropic:
    def __init__(self, outputs=()):
        self.outputs = list(outputs)
        self.calls: List[dict] = []
        self.beta_calls: List[dict] = []
        self.messages = SimpleNamespace(create=lambda **kw: self._create(self.calls, **kw))
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: self._create(self.beta_calls, **kw)))

    def _create(self, log, **kw):
        log.append({**kw, "messages": [dict(m) for m in kw["messages"]]})
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def o_call(call_id, name, args):
    return SimpleNamespace(type="function_call", call_id=call_id, name=name,
                           arguments=args if isinstance(args, str) else json.dumps(args))


def o_msg(text, inp=50, out=10):
    return SimpleNamespace(output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text",
                                                                                           text=text)])],
                           output_text=text, status="completed",
                           usage=SimpleNamespace(input_tokens=inp, output_tokens=out))


def o_resp(*items, text="", inp=50, out=10):
    return SimpleNamespace(output=list(items), output_text=text, status="completed",
                           usage=SimpleNamespace(input_tokens=inp, output_tokens=out))


class FakeOpenAI:
    def __init__(self, outputs=()):
        self.outputs = list(outputs)
        self.calls: List[dict] = []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append({**kw, "input": list(kw["input"])})
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


# ------------------------------------------------------------------- builders --

class Env:
    """A gateway with its store, relay, service and fakes, plus a TestClient app."""

    def __init__(self, tmp_path, *, policy: str = "pending", trial: int = 0, pending_trial: int = 0,
                 anthropic: Optional[FakeAnthropic] = None, openai: Optional[FakeOpenAI] = None,
                 server_keys: bool = True, user_keys: Optional[dict] = None, allowance: Optional[int] = None,
                 b2_cap: Optional[int] = None):
        self.clock = Clock()
        self.soul = SoulService(Settings(data_dir=str(tmp_path)), state=StateStore(":memory:"),
                                master_secret=b"m" * 32, clock=lambda: dt.datetime.fromtimestamp(self.clock(), TZ))
        self.store = DeviceStore(":memory:", host=HOST, policy=policy, pepper=b"p" * 32, clock=self.clock,
                                 trial_turns=trial, pending_trial_turns=pending_trial)
        self.ant = anthropic or FakeAnthropic()
        self.oai = openai or FakeOpenAI()
        self.factory_keys: List[str] = []
        self.user_keys = dict(user_keys or {})
        from suflet_ai.relay import Meter

        def af(k):
            self.factory_keys.append(k)
            return self.ant

        def of(k):
            self.factory_keys.append(k)
            return self.oai

        self.relay = Relay(self.soul, self.store,
                           user_key=lambda acc, prov: self.user_keys.get((acc, prov)),
                           anthropic_key=(lambda: SERVER_ANT) if server_keys else (lambda: None),
                           openai_key=(lambda: "sk-proj-SERVER-0123456789abcdef") if server_keys else (lambda: None),
                           anthropic_factory=af, openai_factory=of, retry_sleep=lambda s: None,
                           meter=Meter(self.store, allowance_turns=allowance, b2_daily_cap_micro=b2_cap))
        self.gw = Gateway(self.soul, self.store, self.relay)
        self.app = FastAPI()
        self.app.include_router(build_router(lambda: self.gw))
        self.app.include_router(build_dev_router(lambda: self.gw))
        self.client = TestClient(self.app)

    # -------------------------------------------------------------- devices --
    def device(self, device_id: str = DEV, key: Optional[DeviceKey] = None, **kw) -> FakeDevice:
        return FakeDevice(Http(self.client), device_id, key or DeviceKey.generate(), HOST, **kw)

    def ws(self, token: Optional[str], subprotocols=("soul.v1",)):
        headers = {"authorization": f"Bearer {token}"} if token else {}
        return self.client.websocket_connect("/v1/device/ws", subprotocols=list(subprotocols), headers=headers)

    def paired_device(self, device_id: str = DEV, account: str = "acc_1", name: str = "Ana",
                      email: str = "ana@example.com", **kw) -> FakeDevice:
        """Authenticate a fake device and pair it to `account` directly through the store (no socket)."""
        d = self.device(device_id, **kw)
        d.authenticate()
        ctx = self.store.device_from_token(d.token)
        code = self.store.current_code(device_id)["code"]
        claim = self.store.claim(account, name, email, code, "203.0.113.9")
        assert self.store.on_device_answer(ctx, claim["pid"], True) is not None
        d.state = "paired"
        return d


def recv(ws) -> dict:
    return json.loads(ws.receive_text())


def recv_until(ws, t: str, limit: int = 200) -> List[dict]:
    """Frames up to and including the first of type `t`."""
    got = []
    for _ in range(limit):
        m = recv(ws)
        got.append(m)
        if m.get("t") == t:
            return got
    raise AssertionError(f"no {t} in {[g.get('t') for g in got]}")


def send(ws, msg: dict) -> None:
    ws.send_text(json.dumps(msg))


def hello(after: int = 0, **kw) -> dict:
    return {"v": 1, "t": "hello", "proto": [1], "fw": "0.4.0", "hw": "lcd28", "caps": ["text", "cards"],
            "after": after, "lang": "en", "brain_local": "cloud", "power": "usb", **kw}


__all__ = ["ANT_KEY", "Any", "Clock", "DEV", "DEV2", "DeviceKey", "Env", "FakeAnthropic", "FakeDevice", "FakeOpenAI",
           "HOST", "Http", "NOW", "OAI_KEY", "SERVER_ANT", "TZ", "VECTOR", "WsAdapter", "a_resp", "a_text", "a_tool",
           "auth_message", "block", "hello", "o_call", "o_msg", "o_resp", "recv", "recv_until", "send"]
