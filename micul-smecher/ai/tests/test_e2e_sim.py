"""End to end with the firmware's own protocol code (docs/07 §6.17): the SoulOS simulator in cloud mode.

Skipped when the simulator is not built (`cd firmware && pio run -e sim`). The device is
firmware/.pio/build/sim/program (lib/Suflet CloudDriver + CloudSession + CloudLink + DeviceKey + SoulOS over a host
WebSocket); the cloud is `create_app()` on a real socket; the LLM is tools/fake_llm.py; no AI is paid by SOUL.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fake_llm  # noqa: E402
from e2e_connect import ServerThread, free_port  # noqa: E402
from e2e_sim import SIM, run  # noqa: E402

from suflet_ai import gateway as gateway_mod
from suflet_ai.accounts import DevMailbox
from suflet_ai.app import create_app
from suflet_ai.config import Settings
from suflet_ai.devices import DeviceStore
from suflet_ai.gateway import Gateway
from suflet_ai.soul import SoulService


@pytest.mark.builtin_off
@pytest.mark.skipif(not SIM.exists(), reason="firmware simulator not built (pio run -e sim)")
def test_firmware_simulator_pairs_receives_pushes_and_talks(tmp_path, monkeypatch):
    llm = ServerThread(fake_llm.create_app()).start()
    port = free_port()
    host = f"127.0.0.1:{port}"
    for k, v in {"SOUL_ENV": "dev", "SOUL_PUBLIC_HOST": host, "SOUL_PUBLIC_SCHEME": "http",
                 "ANTHROPIC_BASE_URL": llm.base, "OPENAI_BASE_URL": llm.base + "/v1"}.items():
        monkeypatch.setenv(k, v)
    for k in ("SUFLET_API_TOKEN", "SOUL_ANTHROPIC_KEY", "SOUL_OPENAI_KEY", "SOUL_TRUST_PROXY"):
        monkeypatch.delenv(k, raising=False)
    svc = SoulService(settings=Settings(data_dir=str(tmp_path)), master_secret=b"m" * 32)
    gw = Gateway(svc, DeviceStore(str(tmp_path / "gateway.sqlite"), host=host, policy="pending", pepper=b"p" * 32))
    mailbox = DevMailbox()
    app = create_app(service=svc, gateway=gw, mailer=mailbox, db_path=str(tmp_path / "auth.sqlite"))
    srv = ServerThread(app, port).start()
    lines = []
    try:
        res = run(srv.base, mailbox.last_code, str(SIM), log=lines.append)
    finally:
        srv.stop()
        llm.stop()
        gateway_mod.set_gateway(None)
    assert len(res["steps"]) == 8, lines
    reqs = [r for r in llm.server.config.app.state.rec.all() if r["api"] == "anthropic"]
    assert reqs and all(r["model"] == "claude-haiku-4-5" for r in reqs)  # the owner's key, B2
