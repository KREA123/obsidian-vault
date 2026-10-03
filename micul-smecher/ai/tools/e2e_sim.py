#!/usr/bin/env python3
"""End to end with the FIRMWARE's own protocol code: the SoulOS simulator (firmware `pio run -e sim`) in cloud mode.

The device here is not a Python fake: it is `firmware/.pio/build/sim/program <dir> cloud <base>`, which runs
lib/Suflet (CloudDriver + CloudSession + CloudLink + DeviceKey + SoulOS) over a small host WebSocket client
(firmware/sim/sim_cloud.cpp). The story, against a running SOUL Cloud (`python -m suflet_ai.app serve`, dev mode,
SOUL_BUILTIN_AI=0: no AI paid by SOUL):

  1. the simulated SOUL signs in (ECDSA P-256 challenge), opens `soul.v1`, shows its pairing code
  2. a browser opens /pair, signs in with an email code (dev mailbox), types the code
  3. the simulated SOUL shows "Pair with Ana?"; the driver taps "Yes, pair" on the simulated glass -> paired
  4. /pair/brain: "Connect my Claude" + the owner's own Anthropic key (B2; the fake LLM stands in for the API)
  5. the connector: OAuth (MCP SDK client, loopback redirect) -> consent lists the paired SOUL -> Allow
  6. add_note / set_alarm / show_on_soul -> pushes applied by SoulOS on the simulated device, acked: delivered=shown
  7. a text turn typed on SOUL -> relay -> (fake) Claude with the owner's key -> reply + reminder push applied
  8. a note made on SOUL (item.add) and "Ask my Claude" (inbox.add) reach the cloud; the connector reads them
     (list_today, read_soul_inbox) and answers on SOUL (answer_soul) -> card applied

    python tools/e2e_sim.py --base http://127.0.0.1:8790 --mailbox /tmp/mail.txt [--sim ../firmware/.pio/build/sim/program]

Exit 0 = every step passed. Fakes: the LLM (tools/fake_llm.py), the email inbox (dev mailbox file), the browser
(httpx), the OAuth client (MCP SDK, loopback redirect: not claude.ai). Real: the cloud, the device protocol code,
SoulOS, the sockets.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e_connect import Browser, MemoryTokens, mailbox_file_reader, mcp_client, result_json  # noqa: E402

SIM = Path(__file__).resolve().parents[2] / "firmware" / ".pio" / "build" / "sim" / "program"
KEY = "sk-ant-api03-good-sim-0123456789abcdef"


class SimDevice:
    """The simulator in cloud mode: stdin = a finger, stdout = what the glass shows."""

    def __init__(self, program: str, base: str, workdir: str, log: Callable[[str], None]):
        self.log = log
        self.lines: List[str] = []
        self.q: "queue.Queue[str]" = queue.Queue()
        self.since = 0
        self.p = subprocess.Popen([program, workdir, "cloud", base, str(Path(workdir) / "device.key")],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                  bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        for line in self.p.stdout:
            line = line.rstrip("\n")
            self.lines.append(line)
            self.log("   sim> " + line)
            self.q.put(line)

    def send(self, cmd: str) -> None:
        self.since = len(self.lines)  # what the device shows after this command
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def wait(self, pattern: str, timeout: float = 15.0) -> re.Match:
        """A stdout line matching `pattern`, printed since the last command (in any order)."""
        rx = re.compile(pattern)
        end = time.time() + timeout
        while True:
            for line in self.lines[self.since:]:
                m = rx.search(line)
                if m:
                    return m
            if time.time() >= end:
                raise AssertionError(f"simulated SOUL: no line matching {pattern!r}; last lines: {self.lines[-6:]}")
            try:
                self.q.get(timeout=0.1)
            except queue.Empty:
                pass

    def close(self) -> int:
        try:
            self.send("quit")
            return self.p.wait(timeout=10)
        except Exception:  # noqa: BLE001
            self.p.kill()
            return -1


def run(base: str, read_code: Callable[[str], Optional[str]], program: str, log: Callable[[str], None] = print) -> dict:
    passed: List[str] = []

    def ok(name: str, detail: str = "") -> None:
        passed.append(name)
        log(f"PASS  {name}" + (f"  ({detail})" if detail else ""))

    work = tempfile.mkdtemp(prefix="soul-sim-")
    dev = SimDevice(program, base, work, log)
    browser = Browser(base, read_code, email="ana.pop@example.com", first_name="Ana")
    storage = MemoryTokens()
    loop = asyncio.new_event_loop()
    a = loop.run_until_complete
    try:
        # 1. the device code signs in with its ECDSA key and shows a code
        dev_id = dev.wait(r"^DEVICE (soul-[0-9a-f]{12})").group(1)
        dev.wait(r"^AUTH ok state=pending")
        code = dev.wait(r"^PAIRING code=([0-9A-Z]{8}) url=(\S+)").group(1)
        ok("firmware signs in (ECDSA P-256 challenge, soul.v1) and shows an 8-character pairing code",
           f"{dev_id}, {code[:4]}-{code[4:]}")

        # 2-3. /pair: email code, the code, then a tap on SOUL's glass
        pid = a(browser.pair_claim(f"{code[:4]}-{code[4:]}"))
        m = dev.wait(r"^CONFIRM pid=(\S+) name=Ana hint=a\*\*\*@example\.com view=pair")
        assert m.group(1) == pid, (m.group(1), pid)
        dev.send("tap yes")
        dev.wait(r"^SENT pair\.ok")
        dev.wait(r"^PAIRED owner=Ana")
        brain_path = a(browser.pair_wait(pid))
        assert brain_path == f"/pair/brain?d={dev_id}", brain_path
        ok("/pair: email sign-in + code typed -> 'Pair with Ana?' on the simulated SOUL -> tap -> paired")

        # 4. Connect my Claude + the owner's own Anthropic key (no AI paid by SOUL)
        page = a(browser.http.get(brain_path)).text
        assert "Connect my Claude" in page and 'value="cloud"' not in page
        r = a(browser.choose(page, "none", "/me/connect-claude"))
        conn = a(browser.http.get(r.headers["location"])).text
        assert f'value="{base}/mcp"' in conn
        csrf = re.search(r'name="csrf" value="([^"]+)"', conn).group(1)
        r = a(browser.http.post("/me/keys", data={"csrf": csrf, "provider": "anthropic", "key": KEY,
                                                  "device_id": dev_id}))
        assert r.status_code == 303, r.text[:200]
        dev.wait(r"^CONFIG brain=claude")
        me = a(browser.http.get("/me")).text
        assert KEY not in me and "checked" in me
        ok("brain page: Connect my Claude + own Anthropic key (live-checked against the fake API) -> config on SOUL")

        # 5. the connector (MCP SDK OAuth client) adds SOUL; consent lists the paired SOUL
        async def on_consent(page: str):
            assert f'value="{dev_id}"' in page, "the paired SOUL is not on the consent page"
            return await browser.allow(page, dev_id, ["soul.read", "soul.write", "soul.notes.read"])

        async def connect():
            client, http = mcp_client(base, storage, browser, on_consent)
            async with http, client as c:
                return sorted(t.name for t in (await c.list_tools()).tools)

        tools = a(connect())
        assert "add_note" in tools and "answer_soul" in tools
        ok("connector OAuth (DCR + PKCE + consent of the paired SOUL) -> token", f"{len(tools)} tools")

        async def call(calls):
            client, http = mcp_client(base, storage)
            async with http, client as c:
                return [result_json(await c.call_tool(n, args)) for n, args in calls]

        # 6. tools -> pushes applied by SoulOS on the simulated device
        note, alarm, card = a(call([
            ("add_note", {"text": "Buy batteries", "tags": ["shop"]}),
            ("set_alarm", {"time": "07:30", "days": ["mon", "tue", "wed", "thu", "fri"], "label": "Work"}),
            ("show_on_soul", {"title": "Hello from Claude", "body": "Your SOUL is connected."}),
        ]))
        for res in (note, alarm, card):
            assert res["delivered"] == "shown", res
        dev.wait(r"^PUSH seq=\d+ action=note\.create from=connector/\S* item=\S+ applied .*notes=1")
        dev.wait(r"^PUSH seq=\d+ action=alarm\.set from=connector/\S* item=\S+ applied .*alarms=1")
        dev.wait(r"^PUSH seq=\d+ action=answer\.show from=connector/\S* item=\S+ applied view=answer")
        ok("add_note / set_alarm / show_on_soul -> applied by SoulOS on the simulated SOUL, acked: delivered=shown")

        # 7. a text turn on SOUL -> relay -> (fake) Claude with the owner's key -> reply + the reminder
        dev.send("ask remind me tomorrow at 9 to call mom")
        dev.wait(r"^PUSH seq=\d+ action=reminder\.create from=turn/ item=\S+ applied .*reminders=1", 30)
        rep = dev.wait(r"^REPLY err=(\S+) note=(\S+) say=(.*)$", 30)
        assert rep.group(1) == "none" and rep.group(2) == "none", rep.group(0)
        ok("text turn typed on SOUL -> relay -> (fake) Claude, owner's key -> reply + reminder applied",
           rep.group(3)[:60])

        # 8. made on SOUL: a note (item.add) and "Ask my Claude" (inbox.add); the connector reads and answers
        dev.send("note milk from the corner shop")
        dev.wait(r"^SENT item\.add")
        dev.send("inbox What should I cook tonight?")
        dev.wait(r"^SENT inbox\.add")
        time.sleep(1.5)  # the device sends its queue at <= 2 frames/s
        today, inbox = a(call([("list_today", {}), ("read_soul_inbox", {})]))
        texts = [i.get("untrusted_text") or "" for i in today["items"]]
        assert any("milk from the corner shop" in t for t in texts), texts
        assert any(i["source"] == "device" for i in today["items"])
        q = next(i for i in inbox["items"] if "cook" in (i.get("untrusted_text") or ""))
        ans = a(call([("answer_soul", {"reply_to": q["id"], "title": "Tonight", "body": "Pasta with tomatoes."})]))[0]
        assert ans["delivered"] == "shown", ans
        dev.wait(r"^PUSH seq=\d+ action=answer\.show from=connector/\S* item=\S+ applied")
        ok("note made on SOUL (item.add) + 'Ask my Claude' (inbox.add) -> read by the connector -> answer_soul on SOUL")

        dev.send("state")
        st = dev.wait(r"^STATE state=paired .*outq=0")
        ok("the device's queue drained (every item.add / inbox.add acknowledged with `added`)", st.group(0)[6:80])
        return {"steps": passed, "device_id": dev_id}
    finally:
        try:
            loop.run_until_complete(browser.aclose())
        except Exception:  # noqa: BLE001
            pass
        loop.close()
        code_ = dev.close()
        log(f"   sim exited with {code_}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SOUL Cloud end to end with the firmware simulator as the device")
    ap.add_argument("--base", required=True)
    ap.add_argument("--mailbox", required=True, help="the server's SOUL_DEV_MAILBOX file")
    ap.add_argument("--sim", default=str(SIM), help="the simulator binary (pio run -e sim)")
    a = ap.parse_args(argv)
    if not Path(a.sim).exists():
        print(f"FAIL  no simulator at {a.sim}: run `pio run -e sim` in firmware/")
        return 1
    try:
        res = run(a.base, mailbox_file_reader(a.mailbox), a.sim)
    except AssertionError as e:
        print(f"FAIL  {e}")
        return 1
    print(f"\nall {len(res['steps'])} simulator steps passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
