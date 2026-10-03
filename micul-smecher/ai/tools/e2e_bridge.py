#!/usr/bin/env python3
"""End to end, SOUL Bridge through SOUL Cloud (docs/08-OWN-CLAUDE.md §4): the firmware simulator as SOUL, the real
cloud, the real `soul-bridge` (Node) and a MOCKED Claude Code. No model is called; no Claude account is involved.

    simulated SOUL (firmware lib/Suflet over a host socket)
        --soul.v1--> SOUL Cloud (gateway + /v1/bridge) --wss--> soul-bridge channel --stdio MCP--> mocked Claude Code
        <-- reply + actions as pushes --------------------------- soul_reply {text, actions} <------------------+

  1. the simulated SOUL signs in, is paired by Ana in the browser (/pair + email code + a tap on the glass)
  2. on the glass: Settings > AI > "My Claude on my computer" -> SOUL shows `soul-bridge pair XXXX-XXXX --cloud host`
  3. on the "computer": `soul-bridge pair <that code> --cloud <base>` -> a bridge token (SOUL's, not Claude's)
  4. the mocked Claude Code spawns the real `soul-bridge channel` (stdio), which connects to /v1/bridge -> SOUL
     shows "connected · <computer>"; /me lists the computer
  5. "Trezește-mă mâine la 7" typed on SOUL -> eyes wait, then think -> the channel event reaches "Claude" ->
     soul_reply with alarm.set -> the cloud validates and pushes it -> SoulOS sets the alarm, shows the answer
  6. a plain question -> a plain answer, no action
  7. the computer goes away (Claude Code closed) -> SOUL hears it; the next question gets `bridge_offline` and the
     offline rules answer on the device ("Your computer is offline: open Start SOUL")

And the LAN transport (`--lan`): the simulator serves ws://127.0.0.1:<port>/bridge with the firmware's own
BridgeServer (as SOUL serves ws://soul-xxxx.local:8765/bridge), `soul-bridge pair <6 digits> --soul ...`, the same
mocked Claude Code, answers whose actions SoulOS applies itself (no cloud on the way).

    python tools/e2e_bridge.py --base http://127.0.0.1:8790 --mailbox /tmp/mail.txt [--sim ...] [--bridge ../bridge]
    python tools/e2e_bridge.py --lan [--sim ...] [--bridge ../bridge]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e_connect import Browser, mailbox_file_reader  # noqa: E402
from e2e_sim import SIM, SimDevice  # noqa: E402

BRIDGE = Path(__file__).resolve().parents[2] / "bridge"


class Proc:
    """A child process whose stdout lines can be waited for."""

    def __init__(self, args: List[str], env: dict, log: Callable[[str], None], tag: str):
        self.lines: List[str] = []
        self.q: "queue.Queue[str]" = queue.Queue()
        self.log, self.tag = log, tag
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, bufsize=1, env=env)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        for line in self.p.stdout:
            line = line.rstrip("\n")
            self.lines.append(line)
            self.log(f"   {self.tag}> {line}")
            self.q.put(line)

    def wait(self, pattern: str, timeout: float = 20.0) -> re.Match:
        rx = re.compile(pattern)
        end = time.time() + timeout
        seen = 0
        while True:
            for line in self.lines[seen:]:
                m = rx.search(line)
                if m:
                    return m
            seen = 0
            if time.time() >= end:
                raise AssertionError(f"{self.tag}: no line matching {pattern!r}; last: {self.lines[-6:]}")
            try:
                self.q.get(timeout=0.1)
            except queue.Empty:
                pass

    def stop(self) -> None:
        if self.p.poll() is None:
            try:
                self.p.stdin.close()
                self.p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                self.p.kill()


def run(base: str, read_code: Callable[[str], Optional[str]], program: str, bridge_dir: str = str(BRIDGE),
        log: Callable[[str], None] = print, gw=None) -> dict:
    node = shutil.which("node")
    if not node:
        raise AssertionError("node (>= 20) is needed for soul-bridge")
    passed: List[str] = []

    def ok(name: str, detail: str = "") -> None:
        passed.append(name)
        log(f"PASS  {name}" + (f"  ({detail})" if detail else ""))

    work = tempfile.mkdtemp(prefix="soul-bridge-e2e-")
    env = {**os.environ, "SOUL_BRIDGE_HOME": str(Path(work) / "bridge-home"),
           "SOUL_CLAUDE_DIR": str(Path(work) / "SOUL-Claude")}
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):  # nothing Claude-ish ever reaches the bridge
        env.pop(k, None)
    cli = str(Path(bridge_dir) / "bin" / "soul-bridge.js")
    dev = SimDevice(program, base, work, log)
    browser = Browser(base, read_code, email="ana.pop@example.com", first_name="Ana")
    loop = asyncio.new_event_loop()
    a = loop.run_until_complete
    cc: Optional[Proc] = None
    try:
        # 1. paired by its owner
        dev_id = dev.wait(r"^DEVICE (soul-[0-9a-f]{12})").group(1)
        code = dev.wait(r"^PAIRING code=([0-9A-Z]{8})").group(1)
        pid = a(browser.pair_claim(f"{code[:4]}-{code[4:]}"))
        dev.wait(r"^CONFIRM pid=")
        dev.send("tap yes")
        dev.wait(r"^PAIRED owner=Ana")
        a(browser.pair_wait(pid))
        ok("the simulated SOUL is paired with Ana's account (/pair, email code, a tap on the glass)", dev_id)

        # 2. Settings > AI > My Claude on my computer
        dev.send("ai bridge")
        dev.wait(r"^AI mode=bridge view=bridge")
        m = dev.wait(r"^BRIDGECODE code=([0-9A-Z]{8}) cmd=(.*) view=bridge")
        bcode, cmd = m.group(1), m.group(2)
        assert cmd.startswith(f"soul-bridge pair {bcode[:4]}-{bcode[4:]} --cloud "), cmd
        ok("on the glass: My Claude on my computer -> brain `bridge`, the command to type on the computer", cmd)

        # 3. the computer pairs with that code (SOUL Cloud issues a bridge token: SOUL's, never a Claude credential)
        r = subprocess.run([node, cli, "pair", f"{bcode[:4]}-{bcode[4:]}", "--cloud", base], env=env,
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "through SOUL Cloud" in r.stdout, r.stdout
        cfg = json.loads((Path(env["SOUL_BRIDGE_HOME"]) / "config.json").read_text())
        assert cfg["token"].startswith("sbt_") and cfg["via"] == "cloud" and cfg["soul_url"].endswith("/v1/bridge")
        assert not re.search(r"sk-ant|oauth|session", json.dumps(cfg), re.I)
        dev.wait(r"^BRIDGE paired=1 online=0")
        ok("`soul-bridge pair XXXX-XXXX --cloud ...` -> a SOUL bridge token stored 0600 on the computer")

        # 4. the (mocked) Claude Code starts the real channel; it connects through the cloud
        cc = Proc([node, str(Path(bridge_dir) / "tools" / "fake-claude-code-cli.js")], env, log, "claude")
        ready = json.loads(cc.wait(r"^READY (.*)$").group(1))
        assert ready["channel"] is True and sorted(ready["tools"]) == ["soul_reply", "soul_status"], ready
        name = dev.wait(r"^BRIDGE paired=1 online=1 name=(\S.*)$").group(1)
        me = a(browser.http.get("/me")).text
        assert "Your computers (SOUL Bridge)" in me and "connected" in me
        ok("the mocked Claude Code spawns `soul-bridge channel` -> /v1/bridge -> SOUL shows the computer", name)

        # 5. a question typed on SOUL -> the computer -> an alarm back
        dev.send("ask Trezește-mă mâine la 7")
        dev.wait(r"^ASKSTATE waiting")
        ev = json.loads(cc.wait(r"^EVENT (.*)$").group(1))
        assert ev["content"] == "Trezește-mă mâine la 7" and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d", ev["now"]), ev
        assert ev["tz"] == "Europe/Bucharest" and all(re.fullmatch(r"[A-Za-z0-9_]+", k) for k in ev)
        dev.wait(r"^ASKSTATE thinking", 20)
        dev.wait(r"^PUSH seq=\d+ action=alarm\.set from=turn/ item=\S+ applied .*alarms=1", 30)
        rep = dev.wait(r"^REPLY err=(\S+) note=(\S+) say=(.*)$", 30)
        assert rep.group(1) == "none" and rep.group(3).startswith("Gata, te trezesc la 07:00"), rep.group(0)
        ok("SOUL -> cloud -> bridge -> (mocked) Claude -> soul_reply + alarm.set -> pushed, applied by SoulOS",
           rep.group(3))

        # 6. a plain question
        dev.send("ask Ce faci azi?")
        rep = dev.wait(r"^REPLY err=(\S+) note=(\S+) say=(.*)$", 30)
        assert rep.group(1) == "none" and "Ai întrebat: Ce faci azi?" in rep.group(3), rep.group(0)
        ok("a plain question gets a plain answer from the computer", rep.group(3)[:50])

        # 7. the computer goes away: SOUL hears it, the offline rules answer
        cc.stop()
        cc = None
        dev.wait(r"^BRIDGE paired=1 online=0", 20)
        dev.send("ask wake me at 8")
        dev.wait(r"^SENT item\.add", 20)  # the offline rules set the alarm on SOUL (and tell the cloud about it)
        dev.send("state")
        st = dev.wait(r"^STATE state=paired .*alarms=(\d+)")
        assert int(st.group(1)) == 2, st.group(0)
        assert not any(line.startswith("REPLY") for line in dev.lines[dev.since:]), "nothing went to the computer"
        ok("Claude Code closed -> SOUL shows the computer offline; the question is answered by the offline rules "
           "on SOUL (alarm at 08:00), nothing is sent", st.group(0)[6:60])
        return {"steps": passed, "device_id": dev_id}
    finally:
        if cc is not None:
            cc.stop()
        try:
            loop.run_until_complete(browser.aclose())
        except Exception:  # noqa: BLE001
            pass
        loop.close()
        dev.close()
        shutil.rmtree(work, ignore_errors=True)


def run_lan(program: str, bridge_dir: str = str(BRIDGE), log: Callable[[str], None] = print) -> dict:
    """SOUL Bridge on the home network: the simulated SOUL is the server, no cloud at all."""
    node = shutil.which("node")
    if not node:
        raise AssertionError("node (>= 20) is needed for soul-bridge")
    passed: List[str] = []

    def ok(name: str, detail: str = "") -> None:
        passed.append(name)
        log(f"PASS  {name}" + (f"  ({detail})" if detail else ""))

    work = tempfile.mkdtemp(prefix="soul-bridge-lan-")
    env = {**os.environ, "SOUL_BRIDGE_HOME": str(Path(work) / "bridge-home"),
           "SOUL_CLAUDE_DIR": str(Path(work) / "SOUL-Claude")}
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
        env.pop(k, None)
    cli = str(Path(bridge_dir) / "bin" / "soul-bridge.js")
    dev = Proc([program, work, "lan", "0"], env, log, "sim")
    cc: Optional[Proc] = None

    def cmd(c: str) -> None:
        dev.lines.clear()
        dev.p.stdin.write(c + "\n")
        dev.p.stdin.flush()

    try:
        port = int(dev.wait(r"^LAN port=(\d+)").group(1))
        cmd("ai bridge")
        dev.wait(r"^AI mode=bridge view=bridge")
        code = dev.wait(r"^LANCODE code=(\d{6}) view=bridge").group(1)
        ok("on the glass: My Claude on my computer -> SOUL listens on the Wi-Fi and shows a 6-digit code", code)
        r = subprocess.run([node, cli, "pair", code, "--soul", f"127.0.0.1:{port}"], env=env, capture_output=True,
                           text=True, timeout=30)
        assert r.returncode == 0 and "on this Wi-Fi" in r.stdout, r.stdout + r.stderr
        cfg = json.loads((Path(env["SOUL_BRIDGE_HOME"]) / "config.json").read_text())
        assert cfg["via"] == "lan" and cfg["soul_url"] == f"ws://127.0.0.1:{port}/bridge" and cfg["token"].startswith("sbt_")
        dev.wait(r"^BRIDGE online=0 name= tokens=1")
        ok("`soul-bridge pair <6 digits> --soul <address>` -> SOUL keeps only the token's hash")
        cc = Proc([node, str(Path(bridge_dir) / "tools" / "fake-claude-code-cli.js")], env, log, "claude")
        cc.wait(r"^READY ")
        name = dev.wait(r"^BRIDGE online=1 name=(\S+) tokens=1").group(1)
        ok("the (mocked) Claude Code's channel connects to SOUL on the Wi-Fi", name)
        cmd("ask Trezește-mă mâine la 7")
        dev.wait(r"^ASKSTATE waiting")  # (ask.ack and the mocked answer may arrive in the same round: no thinking line)
        rep = dev.wait(r"^REPLY err=(\S+) say=(.*) alarms=(\d+) notes=\d+$", 30)
        assert rep.group(1) == "none" and rep.group(2).startswith("Gata, te trezesc la 07:00") and rep.group(3) == "1", \
            rep.group(0)
        ok("SOUL -> bridge -> (mocked) Claude -> answer + alarm.set, applied by SoulOS itself (no cloud)", rep.group(2))
        cc.stop()
        cc = None
        dev.wait(r"^BRIDGE online=0 ", 20)
        cmd("ask wake me at 8")
        dev.wait(r"^ASKED wake me at 8 err=bridge_offline")
        cmd("state")
        st = dev.wait(r"^STATE ai=bridge .*alarms=(\d+)")
        assert st.group(1) == "2", st.group(0)
        ok("computer gone -> bridge_offline at once, the offline rules set the alarm on SOUL")
        return {"steps": passed}
    finally:
        if cc is not None:
            cc.stop()
        try:
            cmd("quit")
            dev.p.wait(timeout=5)
        except Exception:  # noqa: BLE001
            dev.p.kill()
        shutil.rmtree(work, ignore_errors=True)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SOUL Bridge through SOUL Cloud, end to end with the simulator")
    ap.add_argument("--base")
    ap.add_argument("--mailbox")
    ap.add_argument("--lan", action="store_true", help="the LAN transport: no cloud, the simulator is the server")
    ap.add_argument("--sim", default=str(SIM))
    ap.add_argument("--bridge", default=str(BRIDGE))
    a = ap.parse_args(argv)
    if not Path(a.sim).exists():
        print(f"FAIL  no simulator at {a.sim}: run `pio run -e sim` in firmware/")
        return 1
    if not (Path(a.bridge) / "node_modules").exists():
        print(f"FAIL  run `npm install` in {a.bridge} first")
        return 1
    try:
        if a.lan:
            res = run_lan(a.sim, a.bridge)
        else:
            if not a.base or not a.mailbox:
                ap.error("--base and --mailbox are needed (or --lan)")
            res = run(a.base, mailbox_file_reader(a.mailbox), a.sim, a.bridge)
    except AssertionError as e:
        print(f"FAIL  {e}")
        return 1
    print(f"\nall {len(res['steps'])} bridge steps passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
