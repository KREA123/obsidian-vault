"""SOUL Bridge end to end (docs/08 §4): the firmware simulator -> SOUL Cloud /v1/bridge -> the real `soul-bridge`
(Node) -> a mocked Claude Code -> reply + actions back on SOUL. And the long-poll transport with the simulator.

Skipped when the simulator is not built (`cd firmware && pio run -e sim`) or the bridge has no node_modules
(`cd bridge && npm install`). No model is called anywhere.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from e2e_bridge import BRIDGE, run, run_lan  # noqa: E402
from e2e_connect import Browser, ServerThread, free_port  # noqa: E402
from e2e_sim import SIM, SimDevice  # noqa: E402

from suflet_ai import gateway as gateway_mod
from suflet_ai.accounts import DevMailbox
from suflet_ai.app import create_app
from suflet_ai.config import Settings
from suflet_ai.devices import DeviceStore
from suflet_ai.gateway import Gateway
from suflet_ai.soul import SoulService

needs = pytest.mark.skipif(not SIM.exists() or not (BRIDGE / "node_modules").exists() or not shutil.which("node"),
                           reason="simulator, node or bridge/node_modules missing")


def cloud(tmp_path, monkeypatch):
    port = free_port()
    host = f"127.0.0.1:{port}"
    for k, v in {"SOUL_ENV": "dev", "SOUL_PUBLIC_HOST": host, "SOUL_PUBLIC_SCHEME": "http"}.items():
        monkeypatch.setenv(k, v)
    for k in ("SUFLET_API_TOKEN", "SOUL_ANTHROPIC_KEY", "SOUL_OPENAI_KEY", "SOUL_TRUST_PROXY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    svc = SoulService(settings=Settings(data_dir=str(tmp_path)), master_secret=b"m" * 32)
    gw = Gateway(svc, DeviceStore(str(tmp_path / "gateway.sqlite"), host=host, policy="pending", pepper=b"p" * 32))
    mailbox = DevMailbox()
    app = create_app(service=svc, gateway=gw, mailer=mailbox, db_path=str(tmp_path / "auth.sqlite"))
    return ServerThread(app, port).start(), gw, mailbox


@pytest.mark.builtin_off
@needs
def test_sim_device_to_cloud_to_bridge_and_back(tmp_path, monkeypatch):
    srv, gw, mailbox = cloud(tmp_path, monkeypatch)
    lines = []
    try:
        res = run(srv.base, mailbox.last_code, str(SIM), str(BRIDGE), log=lines.append)
    finally:
        srv.stop()
        gateway_mod.set_gateway(None)
    assert len(res["steps"]) == 7, "\n".join(lines[-40:])


@needs
def test_sim_device_to_bridge_on_the_home_network():
    """The LAN transport: the simulator serves /bridge with the firmware's BridgeServer; no cloud."""
    lines = []
    res = run_lan(str(SIM), str(BRIDGE), log=lines.append)
    assert len(res["steps"]) == 5, "\n".join(lines[-40:])


@pytest.mark.builtin_off
@pytest.mark.skipif(not SIM.exists(), reason="firmware simulator not built (pio run -e sim)")
def test_sim_device_over_long_poll_when_the_socket_is_blocked(tmp_path, monkeypatch):
    """SIM_NO_WS=1: the device's socket never opens (a proxy that drops upgrades). After 3 tries it switches to
    GET /v1/device/poll + POST /v1/device/send (§6.4): signs in, is paired with a tap, receives a push."""
    import asyncio

    srv, gw, mailbox = cloud(tmp_path, monkeypatch)
    monkeypatch.setenv("SIM_NO_WS", "1")
    lines = []
    dev = SimDevice(str(SIM), srv.base, str(tmp_path), lines.append)
    browser = Browser(srv.base, mailbox.last_code, email="ana.pop@example.com", first_name="Ana")
    loop = asyncio.new_event_loop()
    try:
        dev_id = dev.wait(r"^DEVICE (soul-[0-9a-f]{12})").group(1)
        dev.wait(r"^POLLMODE 1", 40)
        code = dev.wait(r"^PAIRING code=([0-9A-Z]{8})", 30).group(1)
        pid = loop.run_until_complete(browser.pair_claim(f"{code[:4]}-{code[4:]}"))
        dev.wait(r"^CONFIRM pid=", 30)
        dev.send("tap yes")
        dev.wait(r"^PAIRED owner=Ana", 30)
        assert loop.run_until_complete(browser.pair_wait(pid)).startswith("/pair/brain")
        seq = gw.push(dev_id, "note.create", {"text": "via long-poll", "tags": []}, "it_lp1", {"kind": "app"})
        dev.wait(r"^PUSH seq=%d action=note\.create .* applied" % seq, 30)
        import time

        for _ in range(60):  # the ack goes up with the next send
            if gw.store.push_status(dev_id, seq)["acked"]:
                break
            time.sleep(0.5)
        assert gw.store.push_status(dev_id, seq)["acked"]
        assert dev_id not in gw.conns  # never a socket
    finally:
        try:
            loop.run_until_complete(browser.aclose())
        except Exception:  # noqa: BLE001
            pass
        loop.close()
        dev.close()
        srv.stop()
        gateway_mod.set_gateway(None)
