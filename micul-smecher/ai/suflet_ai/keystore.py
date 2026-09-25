"""Bring your own key: the user's Anthropic / OpenAI API key, encrypted at rest.

- Encryption: Fernet (AES-128-CBC + HMAC-SHA256) from `cryptography`.
- Key: HKDF-SHA256 from a 32-byte master secret, bound to the device id and the
  provider, so a ciphertext copied to another device or provider row does not
  decrypt.
- Master secret: SOUL_MASTER_SECRET (base64/hex, e.g. injected from a KMS or
  the OS keystore), else a random file `<data_dir>/master.key` created with
  mode 0600 on first use.
- Never logged, never returned by the API (only "set / not set"), never on
  disk in plain text. Pydantic SecretStr keeps it out of reprs and errors.

Honest limit: whoever holds both the database and the master secret can
decrypt. For production keep the master secret outside the data volume (KMS,
Keychain/Keystore on the phone). os/ARCHITECTURE.md says the key should live on
the phone and never on the SOUL stone itself; this module is what that phone
app (or a SOUL cloud relay) runs.
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .state import StateStore, check_device

PROVIDERS = ("anthropic", "openai")
_INFO = b"soul-byok-v1"


def _decode_secret(s: str) -> bytes:
    s = s.strip()
    for dec in (bytes.fromhex, lambda x: base64.urlsafe_b64decode(x + "=" * (-len(x) % 4))):
        try:
            raw = dec(s)
        except (ValueError, binascii.Error):
            continue
        if len(raw) >= 32:
            return raw
    raise ValueError("SOUL_MASTER_SECRET must be >= 32 bytes, hex or base64")


def load_master_secret(data_dir: str) -> bytes:
    env = os.environ.get("SOUL_MASTER_SECRET")
    if env:
        return _decode_secret(env)
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "master.key")
    if not os.path.exists(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(os.urandom(32))
    with open(path, "rb") as f:
        return f.read()


class KeyStore:
    def __init__(self, state: StateStore, master_secret: bytes):
        if len(master_secret) < 32:
            raise ValueError("master secret too short")
        self._state = state
        self._master = master_secret

    def __repr__(self) -> str:  # never print the master secret
        return "KeyStore(<sealed>)"

    def _fernet(self, device: str, provider: str) -> Fernet:
        k = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                 info=_INFO + b"|" + device.encode() + b"|" + provider.encode()).derive(self._master)
        return Fernet(base64.urlsafe_b64encode(k))

    @staticmethod
    def _check(device: str, provider: str) -> None:
        check_device(device)
        if provider not in PROVIDERS:
            raise ValueError(f"provider must be one of {', '.join(PROVIDERS)}")

    def set(self, device: str, provider: str, api_key: str) -> None:
        self._check(device, provider)
        api_key = (api_key or "").strip()
        if not (20 <= len(api_key) <= 400) or any(c.isspace() for c in api_key):
            raise ValueError("that does not look like an API key")
        token = self._fernet(device, provider).encrypt(api_key.encode())
        self._state.put_secret(device, provider, token, dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))

    def get(self, device: str, provider: str) -> Optional[str]:
        self._check(device, provider)
        token = self._state.get_secret(device, provider)
        if token is None:
            return None
        try:
            return self._fernet(device, provider).decrypt(token).decode()
        except InvalidToken:
            return None  # wrong master secret or tampered row: treat as not set

    def status(self, device: str) -> dict:
        check_device(device)
        info = self._state.secret_info(device)
        return {p: {"set": p in info, "updated": info.get(p, "")} for p in PROVIDERS}

    def remove(self, device: str, provider: str) -> bool:
        self._check(device, provider)
        return self._state.delete_secret(device, provider)
