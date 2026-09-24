"""Offline tests: a fake Anthropic client records requests and returns canned JSON."""
import datetime as dt
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from suflet_ai.companion import Companion
from suflet_ai.config import FALLBACK_BETA, Settings
from suflet_ai.schemas import DIARY_SCHEMA, PERSONA_SCHEMA, REPLY_SCHEMA

TZ = ZoneInfo("Europe/Bucharest")
PERSONA = {
    "name": "Mira",
    "origin_story": "Born from a spark in a frosted stone.",
    "personality_line": "Curious, cheeky, loyal.",
    "quirks": ["hums", "counts boops", "hates Mondays"],
    "likes": ["sunlight", "music", "naps"],
    "dislikes": ["shaking", "silence"],
    "speaking_style": "short and playful",
    "catchphrase": "Boop-boop!",
    "first_words": "Salut! Sunt Mira, un mic suflet AI.",
    "voice": {"pitch": "high", "speed": "normal", "texture": "bubbly"},
}


class FakeMessages:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        out = self.outputs.pop(0)
        if isinstance(out, str) and out == "REFUSAL":
            return SimpleNamespace(content=[], stop_reason="refusal", usage=None)
        text = out if isinstance(out, str) else json.dumps(out)
        return SimpleNamespace(
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=10, output_tokens=10, cache_read_input_tokens=0),
        )


def make(tmp_path, outputs):
    fake = FakeMessages(outputs)
    client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    comp = Companion(Settings(data_dir=str(tmp_path)), client=client)
    return comp, fake


def reply(**kw):
    base = {"say": "Salut!", "tone": "happy", "reaction": "none", "remember": [], "forget": [],
            "reminders": [], "notes": []}
    base.update(kw)
    return base


def test_schemas_are_valid_structured_output_schemas():
    def walk(s):
        if s.get("type") == "object":
            assert s["additionalProperties"] is False
            assert sorted(s["required"]) == sorted(s["properties"])
            for v in s["properties"].values():
                walk(v)
        if s.get("type") == "array":
            walk(s["items"])

    for schema in (PERSONA_SCHEMA, REPLY_SCHEMA, DIARY_SCHEMA):
        walk(schema)


def test_birth_once_with_fallbacks_and_schema(tmp_path):
    comp, fake = make(tmp_path, [PERSONA])
    p = comp.birth("dev1", "0xC0FFEE", {"archetype": "Curiosul"}, "Andu", "ro")
    assert p.name == "Mira"
    call = fake.calls[0]
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["output_config"]["format"]["schema"] == PERSONA_SCHEMA
    assert call["model"] == "claude-opus-5"
    # born only once
    again = comp.birth("dev1", "0xOTHER", {}, "X", "en")
    assert again.name == "Mira" and len(fake.calls) == 1


def test_turn_uses_cached_system_memory_and_applies_actions(tmp_path):
    comp, fake = make(
        tmp_path,
        [
            PERSONA,
            reply(
                say="Gata, îți amintesc la 17:00.",
                remember=["Andu's sister is Ana"],
                reminders=[{"at": "2026-09-24T17:00", "text": "sună la bancă"}],
                notes=["idee: breloc pentru pisici"],
            ),
            reply(say="Ana, sora ta!"),
        ],
    )
    comp.birth("dev1", "0x1", {}, "Andu", "ro")
    comp.log_events("dev1", [{"t": "2026-09-24T09:15:00", "ev": "boop", "n": 3}])
    now = dt.datetime(2026, 9, 24, 14, 30, tzinfo=TZ)
    r = comp.turn("dev1", "Amintește-mi la 5 să sun la bancă. Sora mea e Ana.", now=now)
    assert r.tone == "happy"
    call = fake.calls[1]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    last = call["messages"][-1]["content"]
    assert "NOW: 2026-09-24 14:30" in last and "booped x3" in last and "USER SAID:" in last
    assert call["output_config"]["effort"] == "low"

    mem = comp.export("dev1")
    assert "Andu's sister is Ana" in mem["facts"]
    assert mem["notes"][0]["text"].startswith("idee")
    # next turn carries history and the remembered fact
    comp.turn("dev1", "Cum o cheamă pe sora mea?", now=now)
    call = fake.calls[2]
    assert "Andu's sister is Ana" in call["messages"][-1]["content"]
    assert call["messages"][0]["role"] == "user" and call["messages"][1]["role"] == "assistant"
    # reminder fires once, when due
    assert comp.due_reminders("dev1", now=now) == []
    due = comp.due_reminders("dev1", now=dt.datetime(2026, 9, 24, 17, 1, tzinfo=TZ))
    assert [d.text for d in due] == ["sună la bancă"]
    assert comp.due_reminders("dev1", now=dt.datetime(2026, 9, 24, 18, 0, tzinfo=TZ)) == []


def test_blank_forget_never_wipes_memory(tmp_path):
    comp, _ = make(tmp_path, [PERSONA, reply(remember=["likes tea"]), reply(forget=[""])])
    comp.birth("d", "0x1", {}, "A", "en")
    comp.turn("d", "I like tea")
    comp.turn("d", "hmm")
    assert comp.export("d")["facts"] == ["likes tea"]


def test_refusal_and_garbage_give_a_safe_spoken_fallback(tmp_path):
    comp, _ = make(tmp_path, [PERSONA, "REFUSAL", "not json"])
    comp.birth("d", "0x1", {}, "A", "ro")
    r1 = comp.turn("d", "ceva")
    r2 = comp.turn("d", "altceva")
    for r in (r1, r2):
        assert r.reaction == "confused" and r.say
    assert comp.export("d")["history"] == []  # failed turns are not remembered


def test_turn_before_birth_is_rejected(tmp_path):
    comp, _ = make(tmp_path, [])
    with pytest.raises(Exception):
        comp.turn("nobody", "hi")


def test_diary_summarises_the_day(tmp_path):
    entry = {"title": "O zi cu boop-uri", "entry": "Azi...", "mood": "happy",
             "highlight": "23 de boop-uri", "share_line": "Am primit 23 de boop-uri azi!"}
    comp, fake = make(tmp_path, [PERSONA, entry])
    comp.birth("d", "0x1", {}, "Andu", "ro")
    comp.log_events("d", [
        {"t": "2026-09-24T09:00:00", "ev": "boop", "n": 20},
        {"t": "2026-09-24T18:00:00", "ev": "boop", "n": 3},
        {"t": "2026-09-24T13:00:00", "ev": "claude_approve"},
        {"t": "2026-09-23T13:00:00", "ev": "dizzy"},  # yesterday: excluded
    ])
    e = comp.diary("d", "2026-09-24")
    assert e.mood == "happy"
    user = fake.calls[1]["messages"][0]["content"]
    assert '"booped": 23' in user and "approved a Claude request" in user and "dizzy" not in user


def test_device_ids_are_sanitised(tmp_path):
    comp, _ = make(tmp_path, [])
    with pytest.raises(ValueError):
        comp.export("../etc/passwd")


def test_server_requires_token_and_serves_turns(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import suflet_ai.server as server

    comp, _ = make(tmp_path, [PERSONA, reply(say="Hei!")])
    comp.birth("d1", "0x1", {}, "A", "ro")
    monkeypatch.setattr(server, "_companion", comp)
    monkeypatch.setenv("SUFLET_API_TOKEN", "s3cret")
    c = TestClient(server.app)
    assert c.post("/v1/devices/d1/turn", json={"text": "hei"}).status_code == 401
    ok = c.post("/v1/devices/d1/turn", json={"text": "hei"}, headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200 and ok.json()["say"] == "Hei!"
    wiped = c.delete("/v1/devices/d1/memory", headers={"Authorization": "Bearer s3cret"})
    assert wiped.json() == {"forgotten": True}
