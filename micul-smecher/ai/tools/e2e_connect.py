#!/usr/bin/env python3
"""End-to-end driver for SOUL Cloud over real sockets: a fake SOUL, a connector client, mocked LLMs.

What it proves, against a running `suflet_ai.app` (or the same app started in-process by the tests):

  1. A fake SOUL (`tools/fake_device.py`) signs in with its ECDSA key and opens the `soul.v1` WebSocket.
  2. An MCP client does what claude.ai does when you add a custom connector: 401 -> metadata discovery ->
     dynamic client registration -> PKCE authorize -> sign-in by email code -> pairing code typed on the
     consent page -> the device's ✓ -> Allow -> token. Then it calls `add_note`, `add_reminder`,
     `set_alarm`, `show_on_soul`, `list_today`, and the fake SOUL receives each push on its socket and acks.
  3. Text turns typed on the device go through the relay to (fake) Claude and (fake) OpenAI, come back
     as a reply plus pushes, and brain A's monthly allowance goes down by one per turn.
  4. Failures carry the §6.9 codes in `reply.note`: bad_key, rate_limited, quota, network (provider
     unreachable), allowance (allowance used); a device that is offline gets connector pushes `queued`
     and replayed on reconnect.

    # terminal 1 and 2 (or just run tools/e2e_demo.sh, which does all of this)
    python tools/fake_llm.py --port 8799
    SOUL_PUBLIC_HOST=127.0.0.1:8790 SOUL_PUBLIC_SCHEME=http SUFLET_API_TOKEN=dev SOUL_DEV_MAILBOX=/tmp/mail.txt \\
      SOUL_ANTHROPIC_KEY=sk-ant-fake-ok SOUL_OPENAI_KEY=sk-fake-ok ANTHROPIC_BASE_URL=http://127.0.0.1:8799 \\
      OPENAI_BASE_URL=http://127.0.0.1:8799/v1 python -m suflet_ai.app serve --host 127.0.0.1 --port 8790
    python tools/e2e_connect.py --base http://127.0.0.1:8790 --llm http://127.0.0.1:8799 \\
      --mailbox /tmp/mail.txt --api-token dev --llm-pid <pid of fake_llm>

Nothing here needs or prints a real key. The fake keys only steer the fake LLM's behaviour.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import queue
import re
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import httpx2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_device import PROTOCOL, DeviceKey, FakeDevice, Http, random_device_id  # noqa: E402

REDIRECT = "http://127.0.0.1:33418/callback"  # a loopback app (like Claude Code); never actually opened
SCOPES = ["soul.read", "soul.write", "soul.notes.read"]


# =================================================================== servers ==

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerThread:
    """uvicorn serving an ASGI app on 127.0.0.1:<port> in a background thread (real sockets)."""

    def __init__(self, app: Any, port: Optional[int] = None):
        import uvicorn

        self.port = port or free_port()
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning",
                                                    ws_ping_interval=25, ws_ping_timeout=45, lifespan="on"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> "ServerThread":
        self.thread.start()
        deadline = time.time() + 15
        while not self.server.started:
            if time.time() > deadline or not self.thread.is_alive():
                raise RuntimeError("server did not start")
            time.sleep(0.02)
        return self

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


# =================================================================== browser ==

def _loopback_secure_context(client: httpx2.AsyncClient) -> Callable[[Any], Any]:
    """Like Chrome and Firefox, treat http://127.0.0.1 as a secure context so `Secure` / `__Host-` cookies are
    sent back. (http.cookiejar only returns Secure cookies over https, and httpx merges cookies into a fresh
    jar per request, so a cookie policy cannot do it; we clear the flag on loopback cookies instead.)"""

    async def hook(response: Any) -> None:
        if response.request.url.host in ("127.0.0.1", "localhost", "::1"):
            for c in client.cookies.jar:
                c.secure = False

    return hook


def _hidden(page: str, name: str) -> str:
    m = re.search(rf'name="{re.escape(name)}" value="([^"]*)"', page)
    if not m:
        raise AssertionError(f"no hidden field {name} on the page")
    return html.unescape(m.group(1))


def mailbox_file_reader(path: str) -> Callable[[str], Optional[str]]:
    """Read the newest 6-digit sign-in code sent to `email` from a SOUL_DEV_MAILBOX file."""

    def read(email: str) -> Optional[str]:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        code = None
        for block in text.split("\n---\n"):
            if block.strip().startswith(f"To: {email}"):
                m = re.search(r"\b(\d{6})\b", block.split("\n\n", 1)[-1])
                if m:
                    code = m.group(1)
        return code

    return read


class Browser:
    """The user's phone browser on the sign-in, pairing and consent pages."""

    def __init__(self, base: str, read_code: Callable[[str], Optional[str]], email: str = "ana.pop@example.com",
                 first_name: str = "Ana"):
        self.base = base.rstrip("/")
        self.http = httpx2.AsyncClient(base_url=self.base, timeout=30.0)
        self.http.event_hooks["response"].append(_loopback_secure_context(self.http))
        self.read_code = read_code
        self.email, self.first_name = email, first_name

    async def aclose(self) -> None:
        await self.http.aclose()

    async def sign_in(self, login_path: str) -> None:
        r = await self.http.get(login_path)
        assert r.status_code == 200, r.text
        csrf, nxt = _hidden(r.text, "csrf"), _hidden(r.text, "next")
        before = self.read_code(self.email)
        r = await self.http.post("/login", data={"csrf": csrf, "next": nxt, "email": self.email, "lang": "en",
                                                 "first_name": self.first_name})
        assert r.status_code == 200 and "one-time-code" in r.text, r.text[:300]
        code = None
        for _ in range(50):  # the mail may take a moment (SMTP / file)
            code = self.read_code(self.email)
            if code and code != before:
                break
            await asyncio.sleep(0.1)
        assert code, "no sign-in code arrived"
        r = await self.http.post("/login/verify", data={"csrf": csrf, "next": nxt, "email": self.email,
                                                        "code": code, "lang": "en", "first_name": self.first_name})
        assert r.status_code == 303, r.text[:300]

    async def consent_page(self, authorize_url: str) -> str:
        u = urlparse(authorize_url)
        r = await self.http.get(u.path + "?" + u.query)
        assert r.status_code == 302, r.text[:300]
        loc = r.headers["location"]
        assert loc.startswith(self.base + "/consent?req="), loc
        self.consent_path = loc[len(self.base):]
        r = await self.http.get(self.consent_path)
        if r.status_code == 303 and r.headers["location"].startswith("/login"):
            await self.sign_in(r.headers["location"])
            r = await self.http.get(self.consent_path)
        assert r.status_code == 200, r.text[:300]
        return r.text

    async def pair(self, page: str, code: str) -> str:
        r = await self.http.post("/consent/pair", data={"csrf": _hidden(page, "csrf"), "req": _hidden(page, "req"),
                                                        "code": code})
        assert r.status_code == 303, r.text[:300]
        return r.headers["location"].split("pid=")[1]

    async def pair_state(self, pid: str) -> str:
        return (await self.http.get(f"/consent/pair/{pid}")).json()["state"]

    async def allow(self, page: str, device_id: str, scopes: List[str]) -> httpx2.Response:
        fixed = re.findall(r'<input type="hidden" name="scope" value="([^"]+)">', page)
        data = {"csrf": _hidden(page, "csrf"), "req": _hidden(page, "req"), "device_id": device_id,
                "scope": list(dict.fromkeys(fixed + scopes)), "decision": "allow", "ack": "1"}
        return await self.http.post("/consent", data=data)


# ================================================================ the device ==

class DeviceRunner:
    """A fake SOUL on a real WebSocket in its own thread: applies and acks pushes, sends what we queue."""

    def __init__(self, base: str, host: str, device_id: Optional[str] = None, lang: str = "en"):
        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=30.0)
        self.lines: List[str] = []
        self.dev = FakeDevice(Http(self.http, self.base), device_id or random_device_id(), DeviceKey.generate(),
                              host, lang=lang, confirm=lambda m: True, say=self.lines.append)
        self.out: "queue.Queue[dict]" = queue.Queue()
        self.received: List[dict] = []
        self.close_code: Optional[int] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.cond = threading.Condition()

    @property
    def device_id(self) -> str:
        return self.dev.device_id

    def connect(self) -> dict:
        info = self.dev.authenticate()
        self._stop.clear()
        self.close_code = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return info

    def _run(self) -> None:
        from websockets.exceptions import ConnectionClosed
        from websockets.sync.client import connect

        ws_url = self.base.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/v1/device/ws"
        with connect(ws_url, subprotocols=[PROTOCOL],
                     additional_headers={"Authorization": f"Bearer {self.dev.token}"}) as conn:
            conn.send(json.dumps(self.dev.hello()))
            while not self._stop.is_set():
                try:
                    while True:
                        conn.send(json.dumps(self.out.get_nowait()))
                except queue.Empty:
                    pass
                try:
                    raw = conn.recv(timeout=0.05)
                except TimeoutError:
                    continue
                except ConnectionClosed as e:
                    rcvd = getattr(e, "rcvd", None)
                    self.close_code = rcvd.code if rcvd else -1
                    break
                if not isinstance(raw, str):
                    continue
                m = json.loads(raw)
                for f in self.dev.process(m):
                    conn.send(json.dumps(f))
                with self.cond:
                    self.received.append(m)
                    self.cond.notify_all()
        with self.cond:
            self.cond.notify_all()

    def disconnect(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def send(self, frame: dict) -> None:
        self.out.put(frame)

    def wait_for(self, pred: Callable[[List[dict]], Any], timeout: float = 15.0, what: str = "") -> Any:
        deadline = time.time() + timeout
        with self.cond:
            while True:
                got = pred(self.received)
                if got:
                    return got
                left = deadline - time.time()
                if left <= 0:
                    raise AssertionError(f"device: timed out waiting for {what or pred}; "
                                         f"last frames {[m.get('t') for m in self.received[-8:]]}")
                self.cond.wait(left)

    def pushes(self) -> List[dict]:
        return [m for m in self.received if m.get("t") == "push"]

    def ask(self, text: str, timeout: float = 30.0) -> dict:
        msg = self.dev.ask_msg(text)
        self.send(msg)
        return self.wait_for(lambda rs: next((m for m in rs if m.get("re") == msg["id"]
                                              and m.get("t") in ("reply", "error")), None), timeout, f"reply to {text!r}")

    def close(self) -> None:
        self.disconnect()
        self.http.close()


# ============================================================== the connector ==

class MemoryTokens:
    def __init__(self) -> None:
        self.tokens = None
        self.client_info = None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens) -> None:
        self.tokens = tokens

    async def get_client_info(self):
        return self.client_info

    async def set_client_info(self, client_info) -> None:
        self.client_info = client_info


def mcp_client(base: str, storage: MemoryTokens, browser: Optional[Browser] = None,
               on_consent: Optional[Callable[[str], Any]] = None):
    """(Client, http) for {base}/mcp with the SDK's OAuth provider, as a remote connector client does it."""
    from mcp.client import Client
    from mcp.client.auth import OAuthClientProvider
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata

    seen: Dict[str, Any] = {}

    async def redirect_handler(url: str) -> None:
        if browser is None:
            raise AssertionError("the connector asked for a new sign-in")
        seen["authorize"] = url
        page = await browser.consent_page(url)
        seen["final"] = await on_consent(page)

    async def callback_handler() -> AuthorizationCodeResult:
        resp = seen["final"]
        assert resp.status_code == 302, resp.text[:300]
        loc = resp.headers["location"]
        seen["redirect"] = loc
        q = {k: v[0] for k, v in parse_qs(urlparse(loc).query).items()}
        return AuthorizationCodeResult(code=q["code"], state=q.get("state"), iss=q.get("iss"))

    meta = OAuthClientMetadata(client_name="e2e test connector", redirect_uris=[REDIRECT],
                               grant_types=["authorization_code", "refresh_token"], response_types=["code"],
                               token_endpoint_auth_method="none",
                               scope="soul.read soul.write soul.notes.read offline_access")
    url = base.rstrip("/") + "/mcp"
    auth = OAuthClientProvider(url, meta, storage, redirect_handler=redirect_handler, callback_handler=callback_handler)
    http = httpx2.AsyncClient(timeout=30.0, auth=auth)
    client = Client(streamable_http_client(url, http_client=http))
    client._soul_seen = seen  # noqa: SLF001 - for the caller's assertions
    return client, http


def result_json(r: Any) -> dict:
    text = r.content[0].text if r.content else ""
    if getattr(r, "is_error", False):
        raise AssertionError(f"tool error: {text}")
    return json.loads(text)


async def connect_connector(base: str, browser: Browser, device: DeviceRunner, storage: MemoryTokens) -> dict:
    """The whole 'add custom connector' journey; the pairing code is read off the device's screen."""
    flow: Dict[str, Any] = {}

    async def on_consent(page: str):
        assert "XXXX-XXXX" in page, "a new account should be offered the pairing-code field"
        code = device.wait_for(lambda rs: next((m["code"] for m in reversed(rs) if m.get("t") == "pairing"), None),
                               10, "pairing code on the screen")
        pid = await browser.pair(page, f"{code[:4]}-{code[4:]}")
        flow["pid"] = pid
        flow["state_before_tap"] = await browser.pair_state(pid)
        device.wait_for(lambda rs: any(m.get("t") == "pair.confirm" for m in rs), 10, "pair.confirm")
        device.wait_for(lambda rs: any(m.get("t") == "paired" for m in rs), 10, "paired")
        for _ in range(50):
            flow["state_after_tap"] = await browser.pair_state(pid)
            if flow["state_after_tap"] == "paired":
                break
            await asyncio.sleep(0.1)
        r = await browser.http.get(browser.consent_path)
        assert f'value="{device.device_id}"' in r.text, "the paired SOUL is not offered on the consent page"
        return await browser.allow(r.text, device.device_id, SCOPES)

    client, http = mcp_client(base, storage, browser, on_consent)
    async with http, client as c:
        tools = sorted(t.name for t in (await c.list_tools()).tools)
    flow.update(tools=tools, seen=client._soul_seen)  # noqa: SLF001
    return flow


async def call_tools(base: str, storage: MemoryTokens, calls: List[tuple]) -> List[dict]:
    """Reuse the stored tokens (no new sign-in) and call tools in order; returns the parsed results."""
    client, http = mcp_client(base, storage)
    out = []
    async with http, client as c:
        for name, args in calls:
            out.append(result_json(await c.call_tool(name, args)))
    return out


# ================================================================== scenario ==

class Steps:
    def __init__(self, log: Callable[[str], None] = print):
        self.log = log
        self.passed: List[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed.append(name)
        self.log(f"PASS  {name}" + (f"  ({detail})" if detail else ""))


def dev_post(base: str, token: str, path: str, body: dict) -> dict:
    r = httpx.post(base.rstrip("/") + path, json=body, headers={"authorization": f"Bearer {token}"}, timeout=30)
    assert r.status_code < 300, f"{path}: HTTP {r.status_code} {r.text[:200]}"
    return r.json()


def fake_llm_requests(llm_base: str) -> List[dict]:
    return httpx.get(llm_base.rstrip("/") + "/__fake/requests", timeout=10).json()


def run_scenario(base: str, host: str, api_token: str, llm_base: str, read_code: Callable[[str], Optional[str]],
                 llm_down: Callable[[], None], log: Callable[[str], None] = print,
                 allowance_turns: int = 4) -> Dict[str, Any]:
    """The whole story. Raises AssertionError at the first step that does not hold."""
    st = Steps(log)
    res: Dict[str, Any] = {}
    device = DeviceRunner(base, host)
    browser = Browser(base, read_code)
    storage = MemoryTokens()
    try:
        # ---- 1. SOUL on Wi-Fi: device auth + socket + pairing code on screen
        info = device.connect()
        assert info["state"] == "pending" and "token" not in info, info
        device.wait_for(lambda rs: any(m.get("t") == "pairing" for m in rs), 10, "pairing code")
        st.ok("device signs in (ECDSA challenge) and shows a pairing code", f"device {device.device_id}")

        # ---- 2. the user's AI app adds the connector: OAuth + pairing on the consent page + ✓ on SOUL
        flow = asyncio.run(connect_connector(base, browser, device, storage))
        assert flow["state_before_tap"] == "awaiting_device" and flow["state_after_tap"] == "paired", flow
        assert set(flow["tools"]) == {"add_note", "add_reminder", "answer_soul", "list_today", "read_soul_inbox",
                                      "set_alarm", "show_on_soul"}, flow["tools"]
        q = {k: v[0] for k, v in parse_qs(urlparse(flow["seen"]["authorize"]).query).items()}
        assert q["code_challenge_method"] == "S256" and q["resource"] == base.rstrip("/") + "/mcp", q
        back = {k: v[0] for k, v in parse_qs(urlparse(flow["seen"]["redirect"]).query).items()}
        assert back["iss"].rstrip("/") == base.rstrip("/"), back
        assert storage.tokens.access_token.startswith("sat_") and storage.tokens.refresh_token.startswith("srt_")
        res["flow"] = {k: flow[k] for k in ("state_before_tap", "state_after_tap", "tools")}
        st.ok("connector OAuth: DCR + PKCE S256 + sign-in + pairing code + device ✓ + consent + token",
              "nothing bound before the tap")

        # ---- 3. tools -> pushes on the device socket
        n0 = len(device.pushes())
        results = asyncio.run(call_tools(base, storage, [
            ("add_note", {"text": "Buy batteries", "tags": ["shop"]}),
            ("add_reminder", {"text": "Call the bank", "in_minutes": 120}),
            ("set_alarm", {"time": "07:30", "days": ["mon", "tue", "wed", "thu", "fri"], "label": "Work"}),
            ("show_on_soul", {"title": "Hello", "body": "Hi from your Claude", "say": "Hello!"}),
            ("list_today", {}),
        ]))
        note, rem, alarm, card, today = results
        for r in (note, rem, alarm, card):
            assert r["delivered"] == "shown", r
        assert rem["will_ring"] == "yes" and rem["resolved"]["when_local"], rem
        pushes = device.wait_for(lambda rs: (lambda p: p if len(p) >= n0 + 5 else None)(
            [m for m in rs if m.get("t") == "push"]), 10, "5 connector pushes")
        mine = pushes[n0:]
        actions = [p["action"] for p in mine]
        # the first call of a new connection shows the "connected" card (§0.1 step 7)
        assert actions == ["answer.show", "note.create", "reminder.create", "alarm.set", "answer.show"], actions
        assert all(p["origin"]["kind"] == "connector" for p in mine)
        assert mine[1]["args"]["text"] == "Buy batteries" and mine[2]["args"]["text"] == "Call the bank"
        assert mine[3]["args"]["hhmm"] == "07:30" and mine[4]["args"]["title"] == "Hello"
        seqs = [p["seq"] for p in pushes]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
        kinds = {i["kind"] for i in today["items"]}
        assert {"note", "reminder", "card"} <= kinds, kinds  # the weekday alarm is not "today" on weekends
        assert today["device"]["online"] is True
        res["connector_pushes"] = actions
        st.ok("add_note / add_reminder / set_alarm / show_on_soul land on the device socket, acked, delivered=shown",
              ", ".join(actions))

        # ---- 4. device turns through the relay (brain A = SOUL's key) to fake Claude
        r1 = device.ask("remind me tomorrow at 9 to call mom")
        assert r1["t"] == "reply" and r1["brain"] == "cloud" and r1["provider"] == "claude", r1
        assert r1["seqs"] and "note" not in r1, r1
        p = device.wait_for(lambda rs: next((m for m in rs if m.get("t") == "push" and m["seq"] == r1["seqs"][0]),
                                            None), 10, "turn push")
        assert p["action"] == "reminder.create" and p["args"]["text"] == "call mom" and p["origin"]["kind"] == "turn", p
        assert p["args"]["when"].endswith("T09:00"), p
        left1 = r1["allowance"]["left"]
        assert left1 == allowance_turns - 1, r1
        r2 = device.ask("hello there")
        assert r2["say"] == "Hi from fake Claude!" and r2["allowance"]["left"] == left1 - 1, r2
        res["claude_turns"] = [r1["say"], r2["say"]]
        st.ok("device text turn -> relay -> (fake) Claude -> reply + reminder push; allowance decrements",
              f"left {allowance_turns} -> {left1} -> {r2['allowance']['left']}")

        # ---- 5. brain A with the ChatGPT voice -> fake OpenAI
        dev_post(base, api_token, "/v1/dev/config", {"device_id": device.device_id, "voice": "chatgpt"})
        r3 = device.ask("note: pick up the parcel")
        assert r3["t"] == "reply" and r3["provider"] == "chatgpt" and r3["brain"] == "cloud", r3
        p = device.wait_for(lambda rs: next((m for m in rs if m.get("t") == "push" and r3["seqs"]
                                             and m["seq"] == r3["seqs"][0]), None), 10, "openai push")
        assert p["action"] == "note.create" and "parcel" in p["args"]["text"], p
        assert r3["allowance"]["left"] == r2["allowance"]["left"] - 1
        st.ok("device text turn -> relay -> (fake) OpenAI Responses -> reply + note push; allowance decrements",
              f"left {r3['allowance']['left']}")

        # ---- 6. allowance used up -> offline rules + note allowance
        r4 = device.ask("hello again")
        assert r4["provider"] == "claude" or r4["provider"] == "chatgpt", r4
        assert r4["allowance"]["left"] == 0, r4
        r5 = device.ask("hello once more")
        assert r5["note"] == "allowance" and r5["provider"] == "rules", r5
        st.ok("allowance used up -> offline rules answer, note=allowance")

        # ---- 7. B2: the owner's own key; bad key / rate limit / quota
        notes = {}
        for brain, prov in (("claude", "anthropic"), ("chatgpt", "openai")):
            dev_post(base, api_token, "/v1/dev/config", {"device_id": device.device_id, "brain": brain})
            dev_post(base, api_token, "/v1/dev/key", {"device_id": device.device_id, "provider": prov,
                                                      "api_key": f"sk-fake-{prov}-good-0123456789abcdef"})
            ok = device.ask("hello with my own key")
            assert ok["brain"] == brain and ok["provider"] == brain and "note" not in ok and "allowance" not in ok, ok
            for kind, want in (("bad", "bad_key"), ("ratelimit", "rate_limited"), ("quota", "quota")):
                dev_post(base, api_token, "/v1/dev/key", {"device_id": device.device_id, "provider": prov,
                                                          "api_key": f"sk-fake-{prov}-{kind}-0123456789abcdef"})
                r = device.ask(f"hello ({kind})")
                assert r["t"] == "reply" and r.get("note") == want and r["provider"] == "rules", (kind, r)
                notes[f"{brain}:{kind}"] = r["note"]
            dev_post(base, api_token, "/v1/dev/key", {"device_id": device.device_id, "provider": prov,
                                                      "api_key": f"sk-fake-{prov}-good-0123456789abcdef"})
        res["b2_notes"] = notes
        st.ok("B2 (owner's key): ok answer; bad key -> bad_key, 429 -> rate_limited, billing -> quota "
              "(Claude and OpenAI)", json.dumps(notes))

        # ---- 8. what the fake providers received
        reqs = fake_llm_requests(llm_base)
        ant = [r for r in reqs if r["api"] == "anthropic" and r["key_kind"] == "ok"]
        oai = [r for r in reqs if r["api"] == "openai" and r["key_kind"] == "ok"]
        assert ant and all(r["model"] == "claude-haiku-4-5" and r["effort"] is None for r in ant), ant
        assert any(r["after_tool"] for r in ant), "Claude never got the tool result back"
        assert oai and all(r["model"] == "gpt-6-luna" and r["store"] is False and r["reasoning"] == {"effort": "none"}
                           and r["safety_identifier_len"] == 32 for r in oai), oai
        st.ok("requests as specified: claude-haiku-4-5 without effort; gpt-6-luna store=false, reasoning none, "
              "32-char safety_identifier", f"{len(ant)} Anthropic + {len(oai)} OpenAI calls")

        # ---- 9. provider unreachable -> network
        llm_down()
        r = device.ask("hello while the provider is down")
        assert r.get("note") == "network" and r["provider"] == "rules", r
        st.ok("provider unreachable -> offline rules answer, note=network")

        # ---- 10. device offline: connector push queued, replayed on reconnect
        device.disconnect()
        time.sleep(0.3)
        queued = asyncio.run(call_tools(base, storage, [("add_note", {"text": "While you were away"})]))[0]
        assert queued["delivered"] == "queued", queued
        before = len(device.pushes())
        device.connect()
        got = device.wait_for(lambda rs: next((m for m in rs[before:] if m.get("t") == "push"
                                               and m["args"].get("text") == "While you were away"), None), 15,
                              "replayed push")
        assert got["origin"]["kind"] == "connector"
        st.ok("device offline -> add_note delivered=queued, replayed and acked after reconnect")
        res["steps"] = st.passed
        return res
    finally:
        try:
            asyncio.run(browser.aclose())
        except Exception:  # noqa: BLE001
            pass
        device.close()


# ======================================================================== CLI ==

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SOUL Cloud end-to-end driver (fake device + connector + fake LLM)")
    ap.add_argument("--base", required=True, help="cloud base URL, e.g. http://127.0.0.1:8790")
    ap.add_argument("--host", help="host the device signs for (default: host:port of --base)")
    ap.add_argument("--llm", required=True, help="fake LLM base URL, e.g. http://127.0.0.1:8799")
    ap.add_argument("--llm-pid", type=int, help="pid of tools/fake_llm.py (stopped for the 'provider down' step)")
    ap.add_argument("--mailbox", required=True, help="the server's SOUL_DEV_MAILBOX file")
    ap.add_argument("--api-token", default=os.environ.get("SUFLET_API_TOKEN", ""), help="dev token for /v1/dev/*")
    ap.add_argument("--allowance", type=int, default=int(os.environ.get("SOUL_ALLOWANCE_TURNS", "4")))
    a = ap.parse_args(argv)
    host = a.host or urlparse(a.base).netloc

    def llm_down() -> None:
        if not a.llm_pid:
            raise SystemExit("--llm-pid is needed for the provider-down step")
        os.kill(a.llm_pid, signal.SIGTERM)
        for _ in range(50):
            try:
                httpx.get(a.llm + "/__fake/requests", timeout=0.5)
            except httpx.HTTPError:
                return
            time.sleep(0.1)

    try:
        res = run_scenario(a.base, host, a.api_token, a.llm, mailbox_file_reader(a.mailbox), llm_down,
                           allowance_turns=a.allowance)
    except AssertionError as e:
        print(f"FAIL  {e}")
        return 1
    print(f"\nall {len(res['steps'])} steps passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
