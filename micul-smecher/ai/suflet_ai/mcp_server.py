"""SOUL connector: an MCP server that lets the user's own Claude (or ChatGPT) act on SOUL.

This is the legitimate route for people who pay for Claude or ChatGPT but have
no API key: SOUL can't use their subscription, but their Claude/ChatGPT can
call SOUL. Tools map 1:1 onto SOUL actions and run through the same
dispatcher as every other mode.

    # local (Claude Desktop / Claude Code, stdio):
    SOUL_DEVICE_ID=demo python -m suflet_ai.mcp_server
    # remote (custom connector in claude.ai / an app in ChatGPT), Streamable HTTP at /mcp:
    SOUL_DEVICE_ID=demo python -m suflet_ai.mcp_server --http --port 8788

Which device a call lands on: here SOUL_DEVICE_ID (one person, self-hosted).
In the real service the connector is protected with OAuth (MCP authorization
spec) and the signed-in SOUL account decides the device; do not expose the
HTTP transport publicly without that.
"""
from __future__ import annotations

import argparse
import os
import re
from typing import Annotated, Callable, List, Optional

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from .soul import SoulService

INSTRUCTIONS = (
    "SOUL is the user's small round AI device (a face on a round screen, a speaker). Use these tools to put "
    "things on it: notes, reminders, alarms, and short answers/cards to show. Reminders take the user's local "
    "time as YYYY-MM-DDTHH:MM (ask the user if unsure of the date or time). Keep card text short: the screen "
    "is round and 466 px wide. Call list_today to see what is already on SOUL today."
)

_WRITE = dict(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)


def build_server(service: SoulService, device: Callable[[], str]) -> MCPServer:
    mcp = MCPServer("SOUL", instructions=INSTRUCTIONS, version="0.2.0")

    def lang() -> str:
        return service.state.get_setting(device(), "lang", "ro")

    def run(name: str, args: dict) -> dict:
        r = service.action(device(), name, args, lang=lang(), source="connector")
        if not r.ok:
            raise ToolError(f"{name} failed: {r.error}")
        return {"ok": True, "id": r.id, "soul_says": r.say, "card": r.card, **r.data}

    @mcp.tool(name="add_note", title="Add a note to SOUL",
              annotations=ToolAnnotations(title="Add a note to SOUL", **_WRITE))
    def add_note(
        text: Annotated[str, Field(min_length=1, max_length=2000, description="The note text.")],
        tags: Annotated[Optional[List[str]], Field(description="Optional short tags.")] = None,
    ) -> dict:
        """Save a note on the user's SOUL device; it also syncs to their phone."""
        return run("note.create", {"text": text, "tags": tags or []})

    @mcp.tool(name="add_reminder", title="Add a reminder to SOUL",
              annotations=ToolAnnotations(title="Add a reminder to SOUL", **_WRITE))
    def add_reminder(
        when: Annotated[str, Field(description="Local date-time, YYYY-MM-DDTHH:MM, e.g. 2026-09-25T17:00.")],
        text: Annotated[str, Field(min_length=1, max_length=300, description="What to remind, short.")],
    ) -> dict:
        """Create a reminder that SOUL shows and says at the given local time."""
        return run("reminder.create", {"when": when.strip()[:16], "text": text})

    @mcp.tool(name="set_alarm", title="Set an alarm on SOUL",
              annotations=ToolAnnotations(title="Set an alarm on SOUL", **_WRITE))
    def set_alarm(
        time: Annotated[str, Field(description="24h time HH:MM, e.g. 07:30.")],
        days: Annotated[Optional[List[str]], Field(
            description="Repeat days from mon,tue,wed,thu,fri,sat,sun; empty or omitted = ring once.")] = None,
        label: Annotated[str, Field(max_length=60, description="Optional label.")] = "",
    ) -> dict:
        """Set a wake-up alarm on SOUL. It rings even when SOUL is asleep."""
        t = time.strip()
        if re.fullmatch(r"\d:\d{2}", t):
            t = "0" + t
        return run("alarm.set", {"hhmm": t, "days": [d.lower()[:3] for d in (days or [])], "label": label})

    @mcp.tool(name="show_on_soul", title="Show a card on SOUL",
              annotations=ToolAnnotations(title="Show a card on SOUL", **_WRITE))
    def show_on_soul(
        title: Annotated[str, Field(max_length=60, description="Card title (a few words).")],
        body: Annotated[str, Field(max_length=600, description="Card text: plan, list, translation...")] = "",
        say: Annotated[str, Field(max_length=400, description="Optional sentence SOUL says aloud.")] = "",
    ) -> dict:
        """Show a short card on SOUL's round screen (today's plan, a list, a translation), optionally spoken."""
        return run("answer.show", {"say": say or title, "title": title, "body": body})

    @mcp.tool(name="list_today", title="List today's items on SOUL",
              annotations=ToolAnnotations(title="List today's items on SOUL", read_only_hint=True,
                                          destructive_hint=False, idempotent_hint=True, open_world_hint=False))
    def list_today(
        date: Annotated[Optional[str], Field(description="YYYY-MM-DD; omitted = today on SOUL.")] = None,
    ) -> dict:
        """List what is on SOUL for a day: reminders, alarms, timers, notes and cards."""
        if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ToolError("date must be YYYY-MM-DD")
        day = date or service.now().strftime("%Y-%m-%d")
        items = service.today(device(), day)
        return {"date": day, "count": len(items), "items": items[:100]}

    return mcp


def _env_device() -> str:
    dev = os.environ.get("SOUL_DEVICE_ID", "")
    if not dev:
        raise ToolError("SOUL is not linked: set SOUL_DEVICE_ID (self-hosted) or sign in to your SOUL account")
    return dev


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="suflet_ai.mcp_server", description="SOUL connector (MCP server)")
    ap.add_argument("--http", action="store_true", help="Streamable HTTP at /mcp instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8788)
    a = ap.parse_args(argv)
    server = build_server(SoulService(), _env_device)
    if a.http:
        import uvicorn

        app = server.streamable_http_app(stateless_http=True, json_response=True, host=a.host)
        uvicorn.run(app, host=a.host, port=a.port)
    else:
        server.run("stdio")


if __name__ == "__main__":
    main()
