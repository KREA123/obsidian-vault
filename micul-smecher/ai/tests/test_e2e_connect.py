"""End to end over real sockets: a simulated variant of docs/07-CONNECT-AI.md §0.1 steps 3, 5 and 7.

Not the §5 Phase 0 exit gate: steps 4 (/pair) and 6 (/me) are not built, pairing happens on the connector
consent page, the OAuth client uses a loopback redirect (claude.ai's own redirect and verified-host branch
are covered in test_connector_remote.py), and the device and the LLMs are our own fakes.

Three servers on 127.0.0.1, all in this process but talking only through TCP:

- `tools/fake_llm.py`: stands in for api.anthropic.com and api.openai.com (the official SDKs are pointed at
  it with ANTHROPIC_BASE_URL / OPENAI_BASE_URL, exactly as in production, so the relay code is unchanged);
- `suflet_ai.app.create_app()`: the production composition (device gateway + relay + connector + OAuth);
- `tools/fake_device.py` (through `tools/e2e_connect.DeviceRunner`): a SOUL on the `soul.v1` WebSocket.

The connector client is the official MCP SDK (`OAuthClientProvider` + Streamable HTTP over real HTTP).
No real key exists anywhere: the fake keys only steer the fake LLM ("bad", "ratelimit", "quota").
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fake_llm  # noqa: E402
from e2e_connect import ServerThread, free_port, run_scenario  # noqa: E402

from suflet_ai import gateway as gateway_mod
from suflet_ai.accounts import DevMailbox
from suflet_ai.app import assert_production_ready, create_app, production_problems
from suflet_ai.config import Settings
from suflet_ai.devices import DeviceStore
from suflet_ai.gateway import Gateway
from suflet_ai.soul import SoulService

API_TOKEN = "dev-e2e-token"
ALLOWANCE = 4


@pytest.fixture
def cloud(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    llm = ServerThread(fake_llm.create_app()).start()
    port = free_port()
    host = f"127.0.0.1:{port}"
    env = {
        "SOUL_ENV": "dev", "SUFLET_API_TOKEN": API_TOKEN, "SOUL_ALLOWANCE_TURNS": str(ALLOWANCE),
        "SOUL_ANTHROPIC_KEY": "sk-ant-fake-service-ok-0123456789", "SOUL_OPENAI_KEY": "sk-fake-service-ok-0123456789",
        "ANTHROPIC_BASE_URL": llm.base, "OPENAI_BASE_URL": llm.base + "/v1",
        "SOUL_PUBLIC_HOST": host, "SOUL_PUBLIC_SCHEME": "http",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    for k in ("SOUL_BRAIN_A_KILL", "SOUL_CLAUDE_MODEL", "SOUL_OPENAI_RELAY_MODEL", "SOUL_TRUST_PROXY"):
        monkeypatch.delenv(k, raising=False)
    svc = SoulService(settings=Settings(data_dir=str(tmp_path)), master_secret=b"m" * 32)
    gw = Gateway(svc, DeviceStore(str(tmp_path / "gateway.sqlite"), host=host, policy="pending", pepper=b"p" * 32))
    mailbox = DevMailbox()
    app = create_app(service=svc, gateway=gw, mailer=mailbox, db_path=str(tmp_path / "auth.sqlite"))
    srv = ServerThread(app, port).start()
    yield {"base": srv.base, "host": host, "llm": llm, "app": app, "gw": gw, "svc": svc, "mailbox": mailbox,
           "caplog": caplog}
    srv.stop()
    llm.stop()
    gateway_mod.set_gateway(None)


def test_e2e_device_connector_relay_and_errors(cloud):
    lines = []
    res = run_scenario(cloud["base"], cloud["host"], API_TOKEN, cloud["llm"].base, cloud["mailbox"].last_code,
                       cloud["llm"].stop, log=lines.append, allowance_turns=ALLOWANCE)
    assert len(res["steps"]) == 10, lines
    assert res["connector_pushes"] == ["answer.show", "note.create", "reminder.create", "alarm.set", "answer.show"]
    assert res["b2_notes"] == {"claude:bad": "bad_key", "claude:ratelimit": "rate_limited", "claude:quota": "quota",
                               "chatgpt:bad": "bad_key", "chatgpt:ratelimit": "rate_limited",
                               "chatgpt:quota": "quota"}

    # metering: one usage row per answered turn, brain A ones billed to the account, never any content
    store = cloud["gw"].store
    rows = [dict(r) for r in store.db.execute("SELECT * FROM usage ORDER BY rowid").fetchall()]
    cloud_rows = [r for r in rows if r["brain"] == "cloud"]
    assert len(cloud_rows) == ALLOWANCE and all(r["account_id"] and r["trial"] == 0 for r in cloud_rows)
    assert {r["provider"] for r in cloud_rows} == {"claude", "chatgpt"}
    assert all(r["input_tokens"] > 0 and r["output_tokens"] > 0 and r["cost_micro_usd"] > 0 for r in cloud_rows)
    assert {r["model"] for r in cloud_rows} == {"claude-haiku-4-5", "gpt-6-luna"}
    assert not ({"text", "say", "content"} & set(rows[0]))
    b2 = [r for r in rows if r["brain"] in ("claude", "chatgpt")]
    assert b2, "B2 turns are metered for the owner's view and the daily cap"

    # the grant is live, bound to the paired device
    grants = cloud["app"].state.soul.oauth.db.all("SELECT state, device_id FROM oauth_grants")
    assert [g["state"] for g in grants] == ["active"] or [g["state"] for g in grants] == ["connected"], grants

    # no secret in any log line: device/access/refresh tokens, fake keys, login and pairing codes
    logs = "\n".join(r.getMessage() for r in cloud["caplog"].records)
    for needle in ("sdt_", "sat_", "srt_", "sk-ant-", "sk-fake-"):
        assert needle not in logs, needle
    for _to, _subject, body in cloud["mailbox"].messages:
        for code in __import__("re").findall(r"\b\d{6}\b", body):
            assert code not in logs


def test_composition_serves_both_sides_and_hides_legacy(cloud):
    base = cloud["base"]
    with httpx.Client(base_url=base, timeout=10) as c:
        assert c.get("/healthz").json()["ok"] is True
        assert c.get("/v1/ping").json()["ok"] is True
        unauth = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                        headers={"accept": "application/json, text/event-stream"})
        assert unauth.status_code == 401
        assert f'resource_metadata="{base}/.well-known/oauth-protected-resource/mcp"' in \
            unauth.headers["www-authenticate"]
        prm = c.get("/.well-known/oauth-protected-resource/mcp").json()
        assert prm["resource"] == base + "/mcp" and prm["authorization_servers"][0].rstrip("/") == base
        asm = c.get("/.well-known/oauth-authorization-server").json()
        assert asm["code_challenge_methods_supported"] == ["S256"]
        assert asm["authorization_response_iss_parameter_supported"] is True
        # the legacy shared-token API (server.py) is not part of the app
        assert c.post("/v1/ask", json={"device_id": "x", "text": "hi"},
                      headers={"authorization": f"Bearer {API_TOKEN}"}).status_code == 404
        # /v1/dev/* needs the dev token
        assert c.post("/v1/dev/config", json={"device_id": "soul-000000000000", "lang": "en"}).status_code == 401
        # (DNS-rebinding protection on /mcp: tests/test_connector_remote.py)


PROD_OK = {
    "SOUL_ENV": "production", "SOUL_ENROL_POLICY": "factory", "SOUL_MASTER_SECRET": "ab" * 32,
    "SOUL_ID_PEPPER": "cd" * 32, "SOUL_PUBLIC_HOST": "soul.example", "SOUL_SMTP_HOST": "smtp.example",
    "SOUL_MAIL_FROM": "SOUL <hello@soul.example>",
}


@pytest.mark.parametrize("change, problem", [
    ({"SUFLET_API_TOKEN": "x"}, "SUFLET_API_TOKEN"),
    ({"SOUL_ENROL_POLICY": "pending"}, "SOUL_ENROL_POLICY"),
    ({"SOUL_MASTER_SECRET": ""}, "SOUL_MASTER_SECRET"),
    ({"SOUL_ID_PEPPER": "xyz12"}, "SOUL_ID_PEPPER"),
    ({"SOUL_PUBLIC_HOST": ""}, "SOUL_PUBLIC_HOST"),
    ({"SOUL_PUBLIC_HOST": "127.0.0.1:8080"}, "SOUL_PUBLIC_HOST"),
    ({"SOUL_PUBLIC_SCHEME": "http"}, "SOUL_PUBLIC_SCHEME"),
    ({"SOUL_SMTP_HOST": ""}, "SOUL_SMTP_HOST"),
    ({"SOUL_DEV_MAILBOX": "/tmp/x"}, "SOUL_DEV_MAILBOX"),
])
def test_production_startup_refusals(change, problem):
    assert production_problems(PROD_OK) == []
    env = {**PROD_OK, **change}
    probs = production_problems(env)
    assert len(probs) == 1 and problem in probs[0]
    with pytest.raises(RuntimeError) as e:
        assert_production_ready(env)
    for v in change.values():  # the refusal names the variable, never echoes a value
        if v and len(v) > 4:
            assert v not in str(e.value)


def test_create_app_refuses_in_production_with_dev_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUL_ENV", "production")
    monkeypatch.setenv("SUFLET_API_TOKEN", "legacy")
    with pytest.raises(RuntimeError, match="refused to start"):
        create_app(service=SoulService(settings=Settings(data_dir=str(tmp_path)), master_secret=b"m" * 32),
                   public_host="soul.example")


def test_smtp_mailer_sends_without_logging_the_code(caplog):
    from suflet_ai.app import SmtpMailer

    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host, self.port = host, port

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, password):
            sent.append(("login", user, bool(password)))

        def send_message(self, msg):
            sent.append(("msg", msg["To"], msg["Subject"], msg.get_content()))

    caplog.set_level(logging.DEBUG)
    m = SmtpMailer("smtp.example", 587, "apikey", "pw-secret", "SOUL <hello@soul.example>", smtp_factory=FakeSMTP, background=False)
    m("ana@example.com", "Your SOUL code: 123456", "Your SOUL sign-in code is 123456.")
    assert sent[0] == ("login", "apikey", True)
    assert sent[1][1] == "ana@example.com" and "123456" in sent[1][3]
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert "123456" not in logs and "ana@" not in logs and "pw-secret" not in repr(m)


def test_import_factory_cli(tmp_path, monkeypatch, capsys):
    from suflet_ai.app import main

    monkeypatch.setenv("SOUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SOUL_GATEWAY_DB", str(tmp_path / "gw.sqlite"))
    monkeypatch.setenv("SOUL_MASTER_SECRET", "ab" * 32)
    gateway_mod.set_gateway(None)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from fake_device import DeviceKey

    pub = DeviceKey.generate().pub
    csv = tmp_path / "keys.csv"
    csv.write_text(f"device_id,pub\nsoul-a1b2c3d4e5f6,{pub}\n")
    try:
        assert main(["import-factory", str(csv)]) == 0
        assert "imported 1" in capsys.readouterr().out
    finally:
        gateway_mod.set_gateway(None)


def test_pilot_mode_allows_pending_enrolment_only():
    pilot = {**PROD_OK, "SOUL_ENV": "pilot", "SOUL_ENROL_POLICY": "pending"}
    assert production_problems(pilot) == []
    assert production_problems({**pilot, "SOUL_ENV": "production"}) == ["SOUL_ENROL_POLICY must be 'factory'"]
    assert any("SUFLET_API_TOKEN" in p for p in production_problems({**pilot, "SUFLET_API_TOKEN": "t"}))
    assert any("SOUL_SMTP_HOST" in p for p in production_problems({**pilot, "SOUL_SMTP_HOST": ""}))


def test_fly_and_docker_files_hold_no_secret_and_match_the_checks():
    root = Path(__file__).resolve().parents[1]
    if not (root / "fly.toml").exists():
        pytest.skip("deployment files are not shipped inside the image")
    fly = (root / "fly.toml").read_text()
    docker = (root / "Dockerfile").read_text()
    for secret in ("SOUL_MASTER_SECRET", "SOUL_ID_PEPPER", "SOUL_ANTHROPIC_KEY", "SOUL_OPENAI_KEY",
                   "SOUL_SMTP_PASSWORD", "SUFLET_API_TOKEN"):
        assert f'{secret} = "' not in fly and f"{secret}=" not in docker.replace(" ", "")
    assert 'primary_region = "fra"' in fly  # EU
    import tomllib

    env = tomllib.loads(fly)["env"]
    fake_secrets = {"SOUL_MASTER_SECRET": "ab" * 32, "SOUL_ID_PEPPER": "cd" * 32}
    assert production_problems({**env, **fake_secrets}) == []


def test_smtp_mailer_runs_off_the_event_loop_and_logs_failures_without_details(caplog):
    import threading as th

    from suflet_ai.app import SmtpMailer

    done = th.Event()

    class Down:
        def __init__(self, host, port, timeout):
            done.set()
            raise ConnectionRefusedError("smtp.example refused for ana@example.com")

    caplog.set_level(logging.DEBUG)
    SmtpMailer("smtp.example", 587, sender="SOUL <hello@soul.example>", smtp_factory=Down)(
        "ana@example.com", "Your SOUL code: 654321", "code 654321")
    assert done.wait(5)
    for _ in range(50):
        if any("failed" in r.getMessage() for r in caplog.records):
            break
        __import__("time").sleep(0.05)
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert "sign-in mail to *@example.com failed: ConnectionRefusedError" in logs
    assert "654321" not in logs and "ana@" not in logs
