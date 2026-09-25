"""SOUL: actions, offline parser, Claude + ChatGPT providers (mocked), BYOK keystore, MCP connector, HTTP API.

No network and no real keys: the LLM clients are fakes that record requests
and replay scripted responses.
"""
import asyncio
import datetime as dt
import json
import logging
import os
import re
import sqlite3
import stat
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import anthropic
import httpx
import openai
import pytest

from suflet_ai.actions import ACTIONS, TOOL_TO_ACTION, action_catalog
from suflet_ai.config import FALLBACK_BETA, Settings
from suflet_ai.dispatcher import Dispatcher
from suflet_ai.keystore import KeyStore, load_master_secret
from suflet_ai.providers.rules import detect_lang, fold, parse
from suflet_ai.soul import SoulService
from suflet_ai.state import StateStore

TZ = ZoneInfo("Europe/Bucharest")
NOW = dt.datetime(2026, 9, 24, 14, 30, tzinfo=TZ)  # a Thursday afternoon
ANT_KEY = "sk-ant-api03-TESTKEY-abcdefghijklmnopqrstuvwxyz0123456789"
OAI_KEY = "sk-proj-TESTKEY-abcdefghijklmnopqrstuvwxyz0123456789"


# ------------------------------------------------------------------ fakes --

def block(type_, **kw):
    return SimpleNamespace(type=type_, **kw)


def a_resp(stop, *blocks):
    return SimpleNamespace(stop_reason=stop, content=list(blocks),
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0))


def a_tool(id_, name, **inp):
    return block("tool_use", id=id_, name=name, input=inp)


def a_text(t):
    return a_resp("end_turn", block("thinking", thinking=""), block("text", text=t))


class FakeAnthropic:
    def __init__(self, outputs=(), models_error=None):
        self.outputs = list(outputs)
        self.calls = []
        self.models_error = models_error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.models = SimpleNamespace(list=self._models)

    def _create(self, **kw):
        # snapshot the messages: the provider keeps appending to the same list
        self.calls.append({**kw, "messages": [dict(m) for m in kw["messages"]]})
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    def _models(self, **kw):
        if self.models_error:
            raise self.models_error
        return [SimpleNamespace(id="claude-opus-5")]


def o_call(call_id, name, args):
    return SimpleNamespace(type="function_call", call_id=call_id, name=name,
                           arguments=args if isinstance(args, str) else json.dumps(args))


def o_resp(*items, text=""):
    return SimpleNamespace(output=list(items), output_text=text, status="completed")


def o_msg(text):
    return o_resp(SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text=text)]), text=text)


class FakeOpenAI:
    def __init__(self, outputs=(), models_error=None):
        self.outputs = list(outputs)
        self.calls = []
        self.models_error = models_error
        self.responses = SimpleNamespace(create=self._create)
        self.models = SimpleNamespace(list=self._models)

    def _create(self, **kw):
        self.calls.append({**kw, "input": list(kw["input"])})
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    def _models(self):
        if self.models_error:
            raise self.models_error
        return [SimpleNamespace(id="gpt-5")]


def http_resp(code):
    return httpx.Response(code, request=httpx.Request("POST", "https://api.example/v1"))


def make_soul(tmp_path, anthropic_client=None, openai_client=None, state=None):
    seen = {"anthropic": [], "openai": []}

    def af(key):
        seen["anthropic"].append(key)
        return anthropic_client or FakeAnthropic()

    def of(key):
        seen["openai"].append(key)
        return openai_client or FakeOpenAI()

    svc = SoulService(Settings(data_dir=str(tmp_path)), state=state or StateStore(":memory:"),
                      master_secret=b"m" * 32, clock=lambda: NOW, anthropic_factory=af, openai_factory=of)
    return svc, seen


# ---------------------------------------------------------------- actions --

def test_every_action_has_a_strict_tool_schema():
    assert set(ACTIONS) == {"note.create", "reminder.create", "alarm.set", "timer.start", "focus.start",
                            "message.draft", "list.add", "answer.show"}

    def walk(s):
        if s.get("type") == "object":
            assert s["additionalProperties"] is False
            assert sorted(s["required"]) == sorted(s["properties"])
            for v in s["properties"].values():
                walk(v)
        if s.get("type") == "array":
            walk(s["items"])
        assert "title" not in s and "default" not in s

    for spec in ACTIONS.values():
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", spec.tool_name)
        assert TOOL_TO_ACTION[spec.tool_name] == spec.name
        walk(spec.json_schema())
    assert len(action_catalog()) == 8


def test_dispatcher_runs_each_action_and_stores_it():
    st = StateStore()
    d = Dispatcher(st, clock=lambda: NOW)
    calls = [
        ("note.create", {"text": "idee breloc", "tags": []}),
        ("reminder.create", {"when": "2026-09-24T17:00", "text": "sun la bancă"}),
        ("alarm.set", {"hhmm": "07:30", "days": ["fri", "mon"], "label": ""}),
        ("timer.start", {"seconds": 600, "label": "paste"}),
        ("focus.start", {"minutes": 25, "label": "deck"}),
        ("message.draft", {"to": "Ana", "text": "Întârzii 10 minute", "channel": "any"}),
        ("list.add", {"list": "Shopping", "items": ["milk", "eggs"]}),
        ("answer_show", {"say": "Bonjour means hello.", "title": "Bonjour", "body": "= hello"}),  # tool name works too
    ]
    for name, args in calls:
        r = d.dispatch("dev1", name, args, lang="ro")
        assert r.ok, (name, r.error)
        assert r.say
    kinds = [i["kind"] for i in st.items("dev1")]
    assert kinds == ["note", "reminder", "alarm", "timer", "focus", "draft", "list_item", "list_item", "card"]
    alarm = st.items("dev1", kind="alarm")[0]
    assert alarm["days"] == ["mon", "fri"] and alarm["due"] == "2026-09-25T07:30"  # next Friday = tomorrow
    assert st.items("dev1", kind="list_item")[0]["list"] == "shopping"
    r = d.dispatch("dev1", "reminder.create", {"when": "2026-09-24T17:00", "text": "x"}, lang="en")
    assert r.say == "Done, I'll remind you today at 17:00: x."


def test_dispatcher_returns_errors_instead_of_raising():
    d = Dispatcher(StateStore(), clock=lambda: NOW)
    assert "unknown action" in d.dispatch("dev1", "door.unlock", {}).error
    bad = d.dispatch("dev1", "alarm.set", {"hhmm": "25:00", "days": [], "label": ""})
    assert not bad.ok and "hhmm" in bad.error
    extra = d.dispatch("dev1", "note.create", {"text": "x", "tags": [], "evil": 1})
    assert not extra.ok
    past = d.dispatch("dev1", "reminder.create", {"when": "2026-09-24T09:00", "text": "x"})
    assert not past.ok and "passed" in past.error
    assert not d.dispatch("../etc", "note.create", {"text": "x", "tags": []}).ok


def test_state_today_due_sync_and_wipe():
    st = StateStore()
    d = Dispatcher(st, clock=lambda: NOW)
    d.dispatch("d", "reminder.create", {"when": "2026-09-24T17:00", "text": "bank"})
    d.dispatch("d", "reminder.create", {"when": "2026-09-25T09:00", "text": "tomorrow"})
    d.dispatch("d", "note.create", {"text": "n", "tags": []})
    assert [i.get("text") for i in st.today("d", "2026-09-24")] == ["n", "bank"]
    assert st.due("d", "2026-09-24T16:59") == []
    assert [r["text"] for r in st.due("d", "2026-09-24T17:00")] == ["bank"]
    assert st.due("d", "2026-09-24T18:00") == []  # fired once
    first = st.items("d")[0]["id"]
    assert len(st.items("d", since=first)) == 2
    st.wipe("d")
    assert st.items("d") == []


# ---------------------------------------------------------- offline rules --

@pytest.mark.parametrize("text,action,args", [
    ("amintește-mi la 5 să sun la bancă", "reminder.create", {"when": "2026-09-24T17:00", "text": "sun la bancă"}),
    ("pune alarma la 7:30", "alarm.set", {"hhmm": "07:30", "days": [], "label": ""}),
    ("notează: idee breloc", "note.create", {"text": "idee breloc", "tags": []}),
    ("remind me at 5 to call the bank", "reminder.create", {"when": "2026-09-24T17:00", "text": "call the bank"}),
    ("Amintește-mi mâine la 9 dimineața să iau pastilele", "reminder.create",
     {"when": "2026-09-25T09:00", "text": "iau pastilele"}),
    ("remind me tomorrow at 9am to call mom", "reminder.create", {"when": "2026-09-25T09:00", "text": "call mom"}),
    ("amintește-mi peste 10 minute să mă ridic", "reminder.create", {"when": "2026-09-24T14:40", "text": "mă ridic"}),
    ("amintește-mi diseară la 8 să scot gunoiul", "reminder.create", {"when": "2026-09-24T20:00", "text": "scot gunoiul"}),
    ("remind me to buy bread for 2 people at 5", "reminder.create",
     {"when": "2026-09-24T17:00", "text": "buy bread for 2 people"}),
    ("trezește-mă la 6 și jumătate în zilele lucrătoare", "alarm.set",
     {"hhmm": "06:30", "days": ["mon", "tue", "wed", "thu", "fri"], "label": ""}),
    ("set an alarm for 6:45 pm", "alarm.set", {"hhmm": "18:45", "days": [], "label": ""}),
    ("wake me up at 7 every day", "alarm.set",
     {"hhmm": "07:00", "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "label": ""}),
    ("alarma la 12 noaptea", "alarm.set", {"hhmm": "00:00", "days": [], "label": ""}),
    ("pune un timer de 5 minute", "timer.start", {"seconds": 300, "label": ""}),
    ("set a timer for 90 seconds", "timer.start", {"seconds": 90, "label": ""}),
    ("focus 50", "focus.start", {"minutes": 50, "label": ""}),
    ("start focus", "focus.start", {"minutes": 25, "label": ""}),
    ("adaugă lapte și ouă pe lista de cumpărături", "list.add", {"list": "cumpărături", "items": ["lapte", "ouă"]}),
    ("add milk and eggs to my shopping list", "list.add", {"list": "shopping", "items": ["milk", "eggs"]}),
    ("scrie-i lui Ana că întârzii 10 minute", "message.draft",
     {"to": "Ana", "text": "întârzii 10 minute", "channel": "any"}),
    ("text Ana I'm running late", "message.draft", {"to": "Ana", "text": "I'm running late", "channel": "any"}),
])
def test_offline_parser(text, action, args):
    p = parse(text, NOW, detect_lang(text))
    assert p is not None and p.action == action
    assert p.args == args
    assert ACTIONS[action].model.model_validate(p.args)  # parser output is a valid action


def test_offline_parser_asks_or_gives_up_instead_of_guessing():
    assert parse("amintește-mi să sun la bancă", NOW, "ro").ask.startswith("La ce oră")
    assert parse("remind me tomorrow to call", NOW, "en").ask.startswith("What time")
    assert parse("pune alarma", NOW, "ro").ask
    assert parse("tell me a joke", NOW, "en") is None
    assert parse("ce vreme e mâine?", NOW, "ro") is None


def test_fold_keeps_length_and_language_detection():
    s = "Amintește-mi mâine ȘI țara"
    assert len(fold(s)) == len(s) and fold(s) == "aminteste-mi maine si tara"
    assert detect_lang("pune alarma la 7:30") == "ro"
    assert detect_lang("remind me at 5 to call the bank") == "en"


def test_no_ai_mode_end_to_end(tmp_path):
    svc, seen = make_soul(tmp_path)
    r = svc.ask("dev1", "amintește-mi la 5 să sun la bancă")
    assert r.provider == "rules" and r.mode == "none" and r.face == "happy"
    assert r.say == "Gata, îți amintesc azi la 17:00: sun la bancă."
    assert r.actions[0].action == "reminder.create" and r.card["icon"] == "reminder"
    assert [i["text"] for i in svc.today("dev1")] == ["sun la bancă"]
    unknown = svc.ask("dev1", "care e capitala Franței?")
    assert unknown.face == "confused" and unknown.chips and not unknown.actions
    assert seen == {"anthropic": [], "openai": []}  # no AI was touched


# ---------------------------------------------------------------- Claude --

def test_claude_calls_soul_actions_as_tools(tmp_path):
    fake = FakeAnthropic([
        a_resp("tool_use", block("thinking", thinking=""), block("text", text="Sure."),
               a_tool("tu_1", "reminder_create", when="2026-09-24T17:00", text="call the bank"),
               a_tool("tu_2", "note_create", text="keychain idea", tags=[])),
        a_text("Done: bank at 5pm, and I saved your idea."),
    ])
    svc, seen = make_soul(tmp_path, anthropic_client=fake)
    svc.set_key("dev1", "anthropic", ANT_KEY)
    svc.set_mode("dev1", "claude")
    r = svc.ask("dev1", "remind me at 5 to call the bank and note keychain idea")

    assert seen["anthropic"] == [ANT_KEY]  # decrypted only to build the client
    assert r.provider == "claude" and r.say == "Done: bank at 5pm, and I saved your idea."
    assert [a.action for a in r.actions] == ["reminder.create", "note.create"] and all(a.ok for a in r.actions)
    assert {i["kind"] for i in svc.sync("dev1")} == {"reminder", "note"}
    assert all(i["source"] == "claude" for i in svc.sync("dev1"))

    first, second = fake.calls
    assert first["model"] == "claude-opus-5"
    assert first["betas"] == [FALLBACK_BETA] and first["fallbacks"] == "default"
    assert first["output_config"] == {"effort": "low"}
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert all(t["strict"] is True for t in first["tools"])
    assert {t["name"] for t in first["tools"]} == set(TOOL_TO_ACTION)
    assert "NOW: 2026-09-24 14:30 (Thursday)" in first["messages"][0]["content"]
    # assistant turn passed back unchanged, then ONE user message with both tool results
    assert second["messages"][1]["role"] == "assistant"
    assert [b.type for b in second["messages"][1]["content"]] == ["thinking", "text", "tool_use", "tool_use"]
    results = second["messages"][2]["content"]
    assert [x["tool_use_id"] for x in results] == ["tu_1", "tu_2"]
    assert all(x["is_error"] is False for x in results)
    assert json.loads(results[0]["content"])["ok"] is True


def test_claude_sees_tool_errors_and_retries(tmp_path):
    fake = FakeAnthropic([
        a_resp("tool_use", a_tool("tu_1", "alarm_set", hhmm="7:30", days=[], label="")),
        a_resp("tool_use", a_tool("tu_2", "alarm_set", hhmm="07:30", days=[], label="")),
        a_text("Alarm set for 7:30."),
    ])
    svc, _ = make_soul(tmp_path, anthropic_client=fake)
    svc.set_key("dev1", "anthropic", ANT_KEY)
    svc.set_mode("dev1", "claude")
    r = svc.ask("dev1", "wake me at 7:30")
    err = fake.calls[1]["messages"][2]["content"][0]
    assert err["is_error"] is True and "hhmm" in json.loads(err["content"])["error"]
    assert [a.ok for a in r.actions] == [False, True]
    assert len(svc.sync("dev1")) == 1


def test_claude_refusal_or_bad_key_falls_back_to_offline(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    refusal = a_resp("refusal")
    auth = anthropic.AuthenticationError("invalid x-api-key", response=http_resp(401), body=None)
    for out, why in [(refusal, "declined"), (auth, "rejected")]:
        svc, _ = make_soul(tmp_path, anthropic_client=FakeAnthropic([out]))
        svc.set_key("dev1", "anthropic", ANT_KEY)
        svc.set_mode("dev1", "claude")
        r = svc.ask("dev1", "pune alarma la 7:30")
        assert r.provider == "rules" and r.actions[0].action == "alarm.set"
        assert why in r.note and ANT_KEY not in r.note
    assert ANT_KEY not in caplog.text


def test_claude_mode_without_key_uses_offline_and_explains(tmp_path):
    svc, seen = make_soul(tmp_path)
    svc.set_mode("dev1", "claude")
    r = svc.ask("dev1", "notează: idee breloc")
    assert r.provider == "rules" and r.mode == "claude" and "connector" in r.note
    assert seen["anthropic"] == []
    assert svc.mode_info("dev1")["route"] == "offline+connector"


# --------------------------------------------------------------- ChatGPT --

def test_chatgpt_calls_soul_actions_with_function_calling(tmp_path):
    reasoning = SimpleNamespace(type="reasoning", id="rs_1", encrypted_content="...")
    fake = FakeOpenAI([
        o_resp(reasoning, o_call("call_1", "list_add", {"list": "shopping", "items": ["milk", "eggs"]})),
        o_msg("Added milk and eggs."),
    ])
    svc, seen = make_soul(tmp_path, openai_client=fake)
    svc.set_key("dev1", "openai", OAI_KEY)
    svc.set_mode("dev1", "chatgpt")
    r = svc.ask("dev1", "add milk and eggs to my shopping list")
    assert seen["openai"] == [OAI_KEY]
    assert r.provider == "chatgpt" and r.say == "Added milk and eggs." and r.actions[0].ok
    assert [i["item"] for i in svc.state.items("dev1", kind="list_item")] == ["milk", "eggs"]

    first, second = fake.calls
    assert first["store"] is False and first["include"] == ["reasoning.encrypted_content"]
    tool = first["tools"][0]
    assert tool["type"] == "function" and tool["strict"] is True and "parameters" in tool
    assert first["instructions"].startswith("You are the assistant inside SOUL")
    # reasoning + call passed back, then the output for that call
    assert second["input"][1] is reasoning and second["input"][2].call_id == "call_1"
    out = second["input"][3]
    assert out["type"] == "function_call_output" and out["call_id"] == "call_1"
    assert json.loads(out["output"])["ok"] is True


def test_chatgpt_bad_arguments_and_errors(tmp_path):
    fake = FakeOpenAI([o_resp(o_call("c1", "note_create", "{not json")), o_msg("Sorry, try again.")])
    svc, _ = make_soul(tmp_path, openai_client=fake)
    svc.set_key("dev1", "openai", OAI_KEY)
    svc.set_mode("dev1", "chatgpt")
    r = svc.ask("dev1", "note something")
    assert not r.actions[0].ok and "JSON" in r.actions[0].error
    assert json.loads(fake.calls[1]["input"][-1]["output"])["ok"] is False

    limited = openai.RateLimitError("quota", response=http_resp(429), body=None)
    svc2, _ = make_soul(tmp_path, openai_client=FakeOpenAI([limited]))
    svc2.set_key("dev1", "openai", OAI_KEY)
    svc2.set_mode("dev1", "chatgpt")
    r2 = svc2.ask("dev1", "focus 25")
    assert r2.provider == "rules" and r2.actions[0].action == "focus.start" and "rate limited" in r2.note


# ------------------------------------------------------------ BYOK store --

def test_keys_are_encrypted_at_rest_and_bound_to_device(tmp_path):
    db = str(tmp_path / "soul.sqlite")
    st = StateStore(db)
    ks = KeyStore(st, b"k" * 32)
    ks.set("dev1", "anthropic", ANT_KEY)
    assert ks.get("dev1", "anthropic") == ANT_KEY
    assert ks.status("dev1")["anthropic"]["set"] and not ks.status("dev1")["openai"]["set"]
    st.db.commit()
    raw = open(db, "rb").read()
    assert ANT_KEY.encode() not in raw and b"TESTKEY" not in raw

    # the same ciphertext copied to another device or provider does not decrypt
    token = st.get_secret("dev1", "anthropic")
    st.put_secret("dev2", "anthropic", token, "x")
    st.put_secret("dev1", "openai", token, "x")
    assert ks.get("dev2", "anthropic") is None and ks.get("dev1", "openai") is None
    # nor with another master secret
    assert KeyStore(st, b"z" * 32).get("dev1", "anthropic") is None
    assert "k" * 32 not in repr(ks)

    with pytest.raises(ValueError):
        ks.set("dev1", "anthropic", "short")
    with pytest.raises(ValueError):
        ks.set("dev1", "gemini", ANT_KEY)
    assert ks.remove("dev1", "anthropic") and ks.get("dev1", "anthropic") is None


def test_master_secret_file_is_private(tmp_path, monkeypatch):
    monkeypatch.delenv("SOUL_MASTER_SECRET", raising=False)
    s1 = load_master_secret(str(tmp_path))
    assert len(s1) == 32 and load_master_secret(str(tmp_path)) == s1
    mode = stat.S_IMODE(os.stat(tmp_path / "master.key").st_mode)
    assert mode == 0o600
    monkeypatch.setenv("SOUL_MASTER_SECRET", "ab" * 32)
    assert load_master_secret(str(tmp_path)) == bytes.fromhex("ab" * 32)


def test_verify_key_uses_a_free_call(tmp_path):
    svc, seen = make_soul(tmp_path)
    assert svc.test_key("dev1", "anthropic") == {"ok": False, "error": "no key set"}
    assert svc.test_key("dev1", "anthropic", ANT_KEY) == {"ok": True, "error": ""}
    bad = FakeAnthropic(models_error=anthropic.AuthenticationError("bad", response=http_resp(401), body=None))
    svc2, _ = make_soul(tmp_path, anthropic_client=bad)
    assert svc2.test_key("dev1", "anthropic", ANT_KEY) == {"ok": False, "error": "key rejected by Anthropic"}
    badoai = FakeOpenAI(models_error=openai.AuthenticationError("bad", response=http_resp(401), body=None))
    svc3, _ = make_soul(tmp_path, openai_client=badoai)
    svc3.set_key("dev1", "openai", OAI_KEY)
    assert svc3.test_key("dev1", "openai") == {"ok": False, "error": "the OpenAI API key was rejected"}


# ------------------------------------------------------------- connector --

def test_mcp_connector_exposes_soul_actions(tmp_path):
    from mcp.client import Client

    from suflet_ai.mcp_server import build_server

    svc, _ = make_soul(tmp_path)
    server = build_server(svc, lambda: "dev1")

    async def go():
        async with Client(server) as c:
            tools = {t.name: t for t in (await c.list_tools()).tools}
            assert set(tools) == {"add_note", "add_reminder", "set_alarm", "show_on_soul", "list_today"}
            assert tools["list_today"].annotations.read_only_hint is True
            assert tools["add_note"].annotations.destructive_hint is False
            r1 = await c.call_tool("add_reminder", {"when": "2026-09-24T17:00", "text": "sună la bancă"})
            r2 = await c.call_tool("set_alarm", {"time": "7:30", "days": ["Monday", "fri"]})
            r3 = await c.call_tool("show_on_soul", {"title": "Plan azi", "body": "1. bancă\n2. sală"})
            r4 = await c.call_tool("add_note", {"text": "idee breloc"})
            bad = await c.call_tool("add_reminder", {"when": "mâine", "text": "x"})
            today = await c.call_tool("list_today", {})
            return r1, r2, r3, r4, bad, today

    r1, r2, r3, r4, bad, today = asyncio.run(go())
    for r in (r1, r2, r3, r4):
        assert not r.is_error
    assert "17:00" in r1.content[0].text
    assert bad.is_error and "YYYY-MM-DDTHH:MM" in bad.content[0].text
    items = json.loads(today.content[0].text)["items"]
    assert {i["kind"] for i in items} >= {"reminder", "note", "card"}
    assert all(i["source"] == "connector" for i in svc.sync("dev1"))
    alarm = svc.state.items("dev1", kind="alarm")[0]
    assert alarm["hhmm"] == "07:30" and alarm["days"] == ["mon", "fri"]


# -------------------------------------------------------------- HTTP API --

def test_http_api_for_device_and_phone(tmp_path, monkeypatch, caplog):
    from fastapi.testclient import TestClient

    import suflet_ai.server as server

    caplog.set_level(logging.DEBUG)
    fake = FakeAnthropic([a_resp("tool_use", a_tool("t1", "timer_start", seconds=300, label="tea")),
                          a_text("Tea timer: 5 minutes.")])
    svc, _ = make_soul(tmp_path, anthropic_client=fake)
    monkeypatch.setattr(server, "_soul", svc)
    monkeypatch.setenv("SUFLET_API_TOKEN", "s3cret")
    c = TestClient(server.app)
    H = {"Authorization": "Bearer s3cret"}

    assert c.post("/v1/ask", json={"device_id": "d1", "text": "hei"}).status_code == 401
    # no-AI mode by default
    r = c.post("/v1/ask", json={"device_id": "d1", "text": "pune alarma la 7:30"}, headers=H)
    assert r.status_code == 200 and r.json()["provider"] == "rules" and r.json()["actions"][0]["action"] == "alarm.set"
    # direct action from the phone UI
    r = c.post("/v1/action", json={"device_id": "d1", "name": "note.create", "args": {"text": "x", "tags": []}},
               headers=H)
    assert r.status_code == 200 and r.json()["ok"]
    assert c.post("/v1/action", json={"device_id": "d1", "name": "alarm.set", "args": {"hhmm": "99:99"}},
                  headers=H).status_code == 422
    assert len(c.get("/v1/actions", headers=H).json()) == 8

    # key: set (never echoed), status, test, then Claude mode
    r = c.post("/v1/key", json={"device_id": "d1", "provider": "anthropic", "api_key": ANT_KEY}, headers=H)
    assert r.status_code == 200 and r.json()["anthropic"]["set"] is True and ANT_KEY not in r.text
    assert c.get("/v1/key", params={"device_id": "d1"}, headers=H).json()["anthropic"]["set"] is True
    assert c.post("/v1/key/test", json={"device_id": "d1", "provider": "anthropic"}, headers=H).json()["ok"] is True
    bad = c.post("/v1/key", json={"device_id": "d1", "provider": "nope", "api_key": ANT_KEY}, headers=H)
    assert bad.status_code == 422 and ANT_KEY not in bad.text
    bad2 = c.post("/v1/key", json=[ANT_KEY], headers=H)
    assert bad2.status_code == 422 and ANT_KEY not in bad2.text

    m = c.post("/v1/mode", json={"device_id": "d1", "mode": "claude", "lang": "en"}, headers=H).json()
    assert m["mode"] == "claude" and m["route"] == "direct-api"
    assert c.post("/v1/mode", json={"device_id": "d1", "mode": "gemini"}, headers=H).status_code == 422
    r = c.post("/v1/ask", json={"device_id": "d1", "text": "tea timer 5 min"}, headers=H).json()
    assert r["provider"] == "claude" and r["say"] == "Tea timer: 5 minutes." and r["card"]["icon"] == "timer"

    assert len(c.get("/v1/sync", params={"device_id": "d1"}, headers=H).json()) == 3
    assert c.get("/v1/today", params={"device_id": "d1"}, headers=H).status_code == 200
    assert c.get("/v1/due", params={"device_id": "d1"}, headers=H).json() == []

    r = c.delete("/v1/key", params={"device_id": "d1", "provider": "anthropic"}, headers=H)
    assert r.json()["anthropic"]["set"] is False
    assert c.get("/v1/mode", params={"device_id": "d1"}, headers=H).json()["route"] == "offline+connector"
    assert c.get("/v1/mode", params={"device_id": "../x"}, headers=H).status_code == 422
    assert ANT_KEY not in caplog.text


def test_plaintext_key_never_reaches_the_database_file(tmp_path):
    db = tmp_path / "soul.sqlite"
    svc, _ = make_soul(tmp_path, state=StateStore(str(db)))
    svc.set_key("dev1", "openai", OAI_KEY)
    svc.set_mode("dev1", "chatgpt")
    con = sqlite3.connect(str(db))
    dump = "\n".join(con.iterdump())
    assert OAI_KEY not in dump and "TESTKEY" not in dump
