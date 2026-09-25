"""SOUL service: one entry point for the device, the phone app and the connector.

    mode "none"    -> offline rules (no account, no key, no internet)
    mode "claude"  -> the user's own Anthropic API key, if set; otherwise offline rules
                      (the user's Claude can still act on SOUL through the connector, mcp_server.py)
    mode "chatgpt" -> the user's own OpenAI API key, if set; otherwise offline rules
                      (the user's ChatGPT can still act on SOUL through the same MCP server as an app)

Whatever the mode, the result is the same AskResult and the same actions.
If a provider fails (bad key, no network, refusal), SOUL answers with the
offline rules instead of going silent, and says why in `note` for the app.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

from .config import Settings
from .dispatcher import ActionResult, Dispatcher
from .keystore import KeyStore, load_master_secret
from .providers.base import AskContext, AskResult, ProviderError, summarize
from .providers.chatgpt import ChatGPTProvider, verify_openai_key
from .providers.chatgpt import _client_for_key as _openai_client
from .providers.claude import ClaudeProvider, verify_anthropic_key
from .providers.claude import _client_for_key as _anthropic_client
from .providers.rules import RulesProvider, detect_lang
from .state import StateStore

MODES = ("none", "claude", "chatgpt")
MODE_PROVIDER = {"claude": "anthropic", "chatgpt": "openai"}

NO_KEY_NOTE = {
    "claude": "No Anthropic API key on this SOUL, so it used the offline parser. Add a key for direct "
              "conversation, or add SOUL as a connector in your Claude and ask Claude to act on SOUL.",
    "chatgpt": "No OpenAI API key on this SOUL, so it used the offline parser. Add a key for direct "
               "conversation, or add SOUL as an app in your ChatGPT and ask ChatGPT to act on SOUL.",
}


class SoulService:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        state: Optional[StateStore] = None,
        master_secret: Optional[bytes] = None,
        clock: Optional[Callable[[], dt.datetime]] = None,
        anthropic_factory: Callable[[str], Any] = _anthropic_client,
        openai_factory: Callable[[str], Any] = _openai_client,
    ):
        self.settings = settings or Settings()
        if state is None:
            os.makedirs(self.settings.data_dir, exist_ok=True)
            state = StateStore(os.environ.get("SOUL_DB") or os.path.join(self.settings.data_dir, "soul.sqlite"))
        self.state = state
        self.tz = ZoneInfo(self.settings.timezone)
        self._clock = clock
        self.dispatcher = Dispatcher(state, self.settings.timezone, clock=self.now)
        self.keys = KeyStore(state, master_secret or load_master_secret(self.settings.data_dir))
        self.rules = RulesProvider()
        self._factories = {"anthropic": anthropic_factory, "openai": openai_factory}

    def now(self) -> dt.datetime:
        return self._clock() if self._clock else dt.datetime.now(self.tz)

    # ----------------------------------------------------------------- mode --
    def get_mode(self, device: str) -> str:
        return self.state.get_setting(device, "ai_mode", "none")

    def set_mode(self, device: str, mode: str) -> str:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}")
        self.state.set_setting(device, "ai_mode", mode)
        return mode

    def mode_info(self, device: str) -> dict:
        mode = self.get_mode(device)
        keys = self.keys.status(device)
        prov = MODE_PROVIDER.get(mode)
        direct = bool(prov and keys[prov]["set"])
        return {"mode": mode, "modes": list(MODES), "keys": keys,
                "route": "direct-api" if direct else ("offline+connector" if prov else "offline")}

    # ------------------------------------------------------------------ ask --
    def _provider(self, mode: str, device: str):
        prov = MODE_PROVIDER[mode]
        key = self.keys.get(device, prov)
        if not key:
            return None
        factory = self._factories[prov]
        if mode == "claude":
            return ClaudeProvider(self.settings, api_key=key, client_factory=factory)
        return ChatGPTProvider(self.settings, api_key=key, client_factory=factory)

    def ask(self, device: str, text: str, lang: Optional[str] = None, mode: Optional[str] = None) -> AskResult:
        text = (text or "").strip()
        if not text:
            raise ValueError("empty text")
        mode = mode or self.get_mode(device)
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}")
        lang = lang if lang in ("ro", "en") else detect_lang(text)
        ctx = AskContext(device=device, text=text[:2000], now=self.now(), lang=lang,
                         dispatcher=self.dispatcher, mode=mode)
        if mode == "none":
            return self.rules.ask(ctx)
        try:
            provider = self._provider(mode, device)
        except ProviderError as e:
            provider, note = None, str(e)
        else:
            note = NO_KEY_NOTE[mode]
        if provider is None:
            res = self.rules.ask(ctx)
            res.note = note
            return res
        try:
            return provider.ask(ctx)
        except ProviderError as e:
            if ctx.executed:  # some actions already ran: report them, don't redo them offline
                ok = [r for r in ctx.executed if r.ok]
                say = ok[-1].say if ok else ("N-am reușit." if lang == "ro" else "That didn't work.")
                res = summarize(provider.name, mode, say, list(ctx.executed))
            else:
                ctx.executed.clear()
                res = self.rules.ask(ctx)
            res.note = f"{provider.name} unavailable ({e}); answered offline"
            return res

    # --------------------------------------------------------------- action --
    def action(self, device: str, name: str, args: dict, lang: str = "en", source: str = "app") -> ActionResult:
        return self.dispatcher.dispatch(device, name, args, lang=lang if lang in ("ro", "en") else "en",
                                        source=source)

    def today(self, device: str, day: Optional[str] = None) -> list:
        return self.state.today(device, day or self.now().strftime("%Y-%m-%d"))

    def sync(self, device: str, since: int = 0) -> list:
        return self.state.items(device, since=since)

    def due(self, device: str) -> list:
        return self.state.due(device, self.now().strftime("%Y-%m-%dT%H:%M"))

    # ------------------------------------------------------------------ keys --
    def set_key(self, device: str, provider: str, api_key: str) -> dict:
        self.keys.set(device, provider, api_key)
        return self.keys.status(device)

    def test_key(self, device: str, provider: str, api_key: Optional[str] = None) -> dict:
        key = api_key or self.keys.get(device, provider)
        if provider not in MODE_PROVIDER.values():
            raise ValueError("provider must be anthropic or openai")
        if not key:
            return {"ok": False, "error": "no key set"}
        factory = self._factories[provider]
        if provider == "anthropic":
            return verify_anthropic_key(key, factory)
        return verify_openai_key(key, factory)

    def remove_key(self, device: str, provider: str) -> dict:
        self.keys.remove(device, provider)
        return self.keys.status(device)
