"""The account owner's rights (docs/07-CONNECT-AI.md §3.5 `GET /v1/me/export`, `DELETE /v1/me`, §4.2 GDPR).

`export_account` gathers everything SOUL Cloud holds about one account into one JSON document: the account,
its SOULs (settings, items, inbox, item states, the diary events), the connected apps, the paired computers
(SOUL Bridge), which API keys are set (never the keys), and the usage records. Secrets are never part of it:
no key material, no token, no code, no hash of one.

`delete_account` erases the account: every SOUL it owns is unpaired with its data erased (which also revokes
the connector grants and the bridge tokens of that SOUL and tells the device `unpaired`), every grant and
token family is revoked and deleted, the API keys and their check marks go, the usage records and the
conversation history of those SOULs go, then the sessions, the login codes and the account row itself.
What stays: the devices' own public keys (a SOUL is hardware; its next owner pairs it again) and the
anonymous delivery rows the outbox needs, none of which name the person.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List

log = logging.getLogger("suflet_ai.gdpr")


def _impl(rc: Any) -> Any:
    return getattr(rc.gateway, "impl", rc.gateway)


def _store(rc: Any) -> Any:
    return getattr(_impl(rc), "store", None)


def _owned(rc: Any, account_id: str) -> List[str]:
    st = _store(rc)
    if st is not None and hasattr(st, "account_devices"):
        return [d for d in st.account_devices(account_id) if st.owner(d) == account_id]
    f = getattr(_impl(rc), "devices_of", None)
    return [d["device_id"] for d in (f(account_id) if callable(f) else []) if d.get("account_id") == account_id]


def _rows(st: Any, sql: str, args: tuple) -> List[dict]:
    if st is None:
        return []
    try:
        with st.lock:
            return [dict(r) for r in st.db.execute(sql, args).fetchall()]
    except Exception:  # noqa: BLE001 - a table that does not exist in this deployment
        return []


def export_account(rc: Any, account_id: str) -> Dict[str, Any]:
    acc = rc.db.one("SELECT id, email, first_name, lang, tz, created FROM accounts WHERE id=?", (account_id,))
    impl, st = _impl(rc), _store(rc)
    devices = []
    for dev in _owned(rc, account_id):
        info_f = getattr(impl, "device_info", None)
        info = dict(info_f(dev) or {}) if callable(info_f) else {"device_id": dev}
        info.pop("members", None)
        try:
            items = rc.service.state.items(dev, limit=5000)
        except Exception:  # noqa: BLE001
            items = []
        devices.append({
            "device": info,
            "items": items,
            "inbox": st.inbox_list(dev, None, limit=1000) if st is not None else [],
            "item_states": _rows(st, "SELECT item_id, state, at FROM item_states WHERE device_id=?", (dev,)),
            "events": _rows(st, "SELECT kind, at FROM events WHERE device_id=? ORDER BY at", (dev,)),
            "conversation_turns": _rows(st, "SELECT conv_id, role, text, created FROM conv_turns WHERE device_id=? "
                                            "ORDER BY created", (dev,)),
            # SOUL Memory's backup (only if the owner switched it on, on SOUL): decrypted for its owner
            "memory_backup": (impl.memory_backups.get(dev) if getattr(impl, "memory_backups", None) is not None
                              else None),
        })
    grants = [g.public() for g in rc.oauth.grants(account_id)]
    keys = {}
    for p in ("anthropic", "openai"):
        try:
            keys[p] = {"set": bool(rc.service.keys.get(account_id, p))}
        except Exception:  # noqa: BLE001
            keys[p] = {"set": False}
    bridges = getattr(impl, "bridges", None)
    computers = bridges.tokens(account_id) if bridges is not None else []
    usage = _rows(st, "SELECT device_id, day, brain, provider, model, turns, requests, input_tokens, output_tokens, "
                      "cost_micro_usd FROM usage WHERE account_id=? ORDER BY day", (account_id,))
    return {
        "format": "soul-export/1",
        "exported_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account": dict(acc) if acc else {"id": account_id},
        "devices": devices,
        "connected_apps": grants,
        "paired_computers": computers,
        "api_keys": keys,
        "usage": usage,
        "note": "API keys, tokens and codes are never exported: SOUL Cloud keeps them encrypted or hashed.",
    }


def delete_account(rc: Any, account_id: str) -> Dict[str, int]:
    """Erase the account and everything that names it. Returns counts (for the log and the tests)."""
    impl, st = _impl(rc), _store(rc)
    owned = _owned(rc, account_id)
    out = {"devices": 0, "grants": 0, "keys": 0, "usage": 0}
    for dev in owned:
        unpair = getattr(impl, "unpair", None)
        if callable(unpair):
            unpair(dev, "user", erase=True)
        if st is not None:
            with st.lock:
                for t in ("conv_turns",):
                    try:
                        st.db.execute(f"DELETE FROM {t} WHERE device_id=?", (dev,))
                    except Exception:  # noqa: BLE001
                        pass
                st.db.commit()
        out["devices"] += 1
    for g in rc.oauth.grants(account_id):
        rc.oauth.revoke_grant(g.grant_id, "revoked")
        out["grants"] += 1
    grant_ids = [r["grant_id"] for r in rc.db.all("SELECT grant_id FROM oauth_grants WHERE account_id=?", (account_id,))]
    for gid in grant_ids:
        rc.db.exec("DELETE FROM oauth_tokens WHERE grant_id=?", (gid,))
    rc.db.exec("DELETE FROM oauth_grants WHERE account_id=?", (account_id,))
    rc.db.exec("DELETE FROM oauth_codes WHERE account_id=?", (account_id,))
    for p in ("anthropic", "openai"):
        try:
            if rc.service.keys.remove(account_id, p):
                out["keys"] += 1
        except Exception:  # noqa: BLE001
            pass
    try:
        rc.db.exec("DELETE FROM key_checks WHERE account_id=?", (account_id,))
    except Exception:  # noqa: BLE001
        pass
    if st is not None:
        with st.lock:
            for sql in ("DELETE FROM usage WHERE account_id=?", "DELETE FROM bridge_tokens WHERE account_id=?",
                        "DELETE FROM pair_claims WHERE account_id=?", "DELETE FROM device_members WHERE account_id=?"):
                try:
                    cur = st.db.execute(sql, (account_id,))
                    if sql.startswith("DELETE FROM usage"):
                        out["usage"] = cur.rowcount
                except Exception:  # noqa: BLE001
                    pass
            st.db.commit()
    acc = rc.db.one("SELECT email FROM accounts WHERE id=?", (account_id,))
    rc.db.exec("DELETE FROM web_sessions WHERE account_id=?", (account_id,))
    if acc is not None:
        rc.db.exec("DELETE FROM login_codes WHERE email=?", (acc["email"],))
    rc.db.exec("DELETE FROM accounts WHERE id=?", (account_id,))
    log.info("account erased (%d SOUL(s), %d app(s), %d key(s))", out["devices"], out["grants"], out["keys"])
    return out
