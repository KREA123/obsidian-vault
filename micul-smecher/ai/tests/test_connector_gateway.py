"""Exit gate of 07-CONNECT-AI §5 Phase 0, against the REAL device gateway (`suflet_ai.gateway.Gateway`).

A simulated SOUL signs in with its ECDSA P-256 key, shows its pairing code and long-polls. The user's
AI app (the official MCP client SDK) completes OAuth: sign-in, pairing code on the consent page, ✓ tapped
on the device, consent, tokens. Then `add_reminder` lands on the device socket and comes back
`delivered: "shown"`. Unpairing SOUL revokes the connector grant.
"""
from __future__ import annotations

import asyncio
import json

import httpx2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from _connector_kit import BASE, DEV, HOST, MCP_URL, Browser, FakeClock, asgi_client, make_service
from suflet_ai.accounts import DevMailbox
from suflet_ai.devices import DeviceStore, auth_message, b64u
from suflet_ai.gateway import Gateway
from suflet_ai.mcp_remote import create_remote_app
from test_connector_remote import oauth_session

DEVICE_IP = "192.0.2.10"


class SimulatedSoul:
    """The firmware side of §6 over long-poll: auth, pairing screen, ✓ on pair.confirm, ack every push."""

    def __init__(self, gw: Gateway):
        self.gw = gw
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.after = 0
        self.received: list = []
        self.code = None
        self.confirm = None

    def sign_in(self):
        st = self.gw.store
        nonce = st.issue_nonce(DEV, DEVICE_IP)["nonce"]
        der = self.key.sign(auth_message(st.host, DEV, nonce), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        sig = b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        pub = b64u(self.key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
        out = st.authenticate({"device_id": DEV, "pub": pub, "nonce": nonce, "sig": sig, "fw": "0.4.0",
                               "hw": "lcd28", "reset": False}, DEVICE_IP)
        self.ctx = st.device_from_token(out["token"])
        return out

    async def poll_once(self, wait: int = 0):
        res = await self.gw.poll(self.ctx, self.after, wait)
        acks = []
        for m in res["messages"]:
            self.received.append(m)
            if m["t"] == "pairing":
                self.code = m["code"]
            elif m["t"] == "pair.confirm":
                self.confirm = m
            elif m["t"] == "push":
                self.after = max(self.after, m["seq"])
                acks.append({"v": 1, "t": "ack", "seq": m["seq"], "ok": True})
        if acks:
            await self.gw.send(self.ctx, acks, DEVICE_IP)
        return res

    async def tap_ok(self):
        await self.gw.send(self.ctx, [{"v": 1, "t": "pair.ok", "pid": self.confirm["pid"]}], DEVICE_IP)

    async def run(self, stop: asyncio.Event):
        while not stop.is_set():
            await self.poll_once(wait=1)


def test_exit_gate_with_real_gateway(tmp_path):
    clock = FakeClock()
    mailbox = DevMailbox()
    svc = make_service(tmp_path, clock)
    store = DeviceStore(":memory:", host=HOST, policy="pending", clock=clock, pepper=b"p" * 32)
    gw = Gateway(svc, store, clock=clock)
    app = create_remote_app(svc, gw, public_host=HOST, db_path=":memory:", mailer=mailbox, clock=clock)
    soul = SimulatedSoul(gw)

    async def go():
        auth = soul.sign_in()
        assert auth["state"] == "pending" and auth["token"].startswith("sdt_")
        await soul.poll_once()
        assert soul.code and len(soul.code) == 8  # shown large on SOUL as XXXX-XXXX

        async with app.router.lifespan_context(app):
            browser = Browser(app, mailbox)

            async def on_consent(page):
                code = f"{soul.code[:4]}-{soul.code[4:]}"
                r = await browser.pair_on_consent(page, code)
                assert r.status_code == 303, r.text
                pid = r.headers["location"].split("pid=")[1]
                assert (await browser.http.get(f"/consent/pair/{pid}")).json()["state"] == "awaiting_device"
                await soul.poll_once()
                assert soul.confirm and soul.confirm["name"] == "Ana"
                assert soul.confirm["account_hint"] == "a***@example.com"
                await soul.tap_ok()  # a touch on SOUL, never anything else
                assert (await browser.http.get(f"/consent/pair/{pid}")).json()["state"] == "paired"
                req = page.split('name="req" value="')[1].split('"')[0]
                page = (await browser.http.get("/consent?req=" + req)).text
                assert f'value="{DEV}"' in page
                return await browser.allow(page, DEV, ["soul.read", "soul.write", "soul.notes.read"])

            client, http, seen, storage = await oauth_session(app, browser, on_consent=on_consent)
            stop = asyncio.Event()
            device_task = asyncio.create_task(soul.run(stop))
            try:
                async with http, client as c:
                    reminder = await c.call_tool("add_reminder", {"text": "Call the bank", "in_minutes": 120})
                    card = await c.call_tool("show_on_soul", {"title": "Hello", "say": "Hi from Claude",
                                                              "private": True})
                    today = await c.call_tool("list_today", {})
            finally:
                stop.set()
                await device_task

            access = storage.tokens.access_token
            # the owner unpairs SOUL: every connector grant on it dies
            gw.unpair(DEV, "user")
            async with asgi_client(app) as raw:
                after = await raw.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                       headers={"authorization": f"Bearer {access}",
                                                "accept": "application/json, text/event-stream"})
            await browser.aclose()
            return reminder, card, today, after

    reminder, card, today, after = asyncio.run(go())

    r = json.loads(reminder.content[0].text)
    assert not reminder.is_error
    assert r["delivered"] == "shown" and r["will_ring"] == "yes"
    assert r["resolved"]["when_local"] == "2026-10-02T16:30"
    c = json.loads(card.content[0].text)
    assert c["delivered"] == "shown"

    pushes = [m for m in soul.received if m["t"] == "push"]
    assert [p["action"] for p in pushes] == ["answer.show", "reminder.create", "answer.show"]
    # the first call of a new connection shows the "connected" card on SOUL (§0.1 step 7)
    assert pushes[0]["args"] == {"title": "An app is connected ✓", "body": ""} or \
        pushes[0]["args"] == {"title": "O aplicație e conectată ✓", "body": ""}
    assert pushes[1]["args"] == {"when": "2026-10-02T16:30", "text": "Call the bank"}
    assert pushes[1]["origin"]["kind"] == "connector"
    assert pushes[2]["private"] is True and pushes[2]["say"].startswith(("From an app: ", "De la o aplicație: "))
    assert [p["seq"] for p in pushes] == [1, 2, 3]  # gap-free per device

    items = json.loads(today.content[0].text)["items"]
    assert {i["kind"] for i in items} >= {"reminder", "card"}
    assert json.loads(today.content[0].text)["device"]["online"] is True

    assert after.status_code == 401
    grants = app.state.soul.oauth.db.all("SELECT state FROM oauth_grants")
    assert [g["state"] for g in grants] == ["revoked"]


def test_dev_composition_forwards_lifespan_and_serves_both_sides(tmp_path):
    """create_dev_app: device routes + connector in one ASGI app; the MCP lifespan is forwarded (§3.0 [U])."""
    from suflet_ai.mcp_remote import create_dev_app

    clock = FakeClock()
    svc = make_service(tmp_path, clock)
    gw = Gateway(svc, DeviceStore(":memory:", host=HOST, policy="pending", clock=clock, pepper=b"p" * 32),
                 clock=clock)
    app = create_dev_app(service=svc, gateway=gw, public_host=HOST, db_path=":memory:", mailer=DevMailbox(),
                         clock=clock)

    async def go():
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=BASE) as http:
                ping = await http.get("/v1/ping")
                chal = await http.post("/v1/device/challenge", json={"device_id": DEV})
                prm = await http.get("/.well-known/oauth-protected-resource/mcp")
                unauth = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                         headers={"accept": "application/json, text/event-stream"})
                login = await http.get("/login")
                return ping, chal, prm, unauth, login

    ping, chal, prm, unauth, login = asyncio.run(go())
    assert ping.json()["ok"] is True
    assert chal.status_code == 200 and len(chal.json()["nonce"]) == 43
    assert prm.json()["resource"] == MCP_URL
    assert unauth.status_code == 401
    assert login.status_code == 200 and "frame-ancestors 'none'" in login.headers["content-security-policy"]
