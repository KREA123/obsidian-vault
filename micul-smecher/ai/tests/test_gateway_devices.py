"""Device identity, enrolment, tokens, pairing and the outbox (docs/07-CONNECT-AI.md §3.2, §3.4, §6.1-6.3, §6.10)."""
import logging

import pytest

from _gateway_kit import DEV, DEV2, HOST, VECTOR, DeviceKey, Env, auth_message
from suflet_ai.devices import (CROCKFORD, DeviceStore, GatewayError, account_hint, b64u_decode, normalize_code,
                               normalize_host, posix_tz, verify_sig)

IP = "203.0.113.7"


def signed(store, key, device_id=DEV, ip=IP, host=HOST, **extra):
    nonce = store.issue_nonce(device_id, ip)["nonce"]
    body = {"device_id": device_id, "pub": key.pub, "nonce": nonce,
            "sig": key.sign(auth_message(host, device_id, nonce)), "fw": "0.4.0", "hw": "lcd28", "reset": False}
    body.update(extra)
    return body


def err(fn, *a, **kw) -> GatewayError:
    with pytest.raises(GatewayError) as e:
        fn(*a, **kw)
    return e.value


# ------------------------------------------------------------- vector + crypto --

def test_shared_test_vector_verifies_and_matches_the_message_format():
    msg = auth_message(VECTOR["host"], VECTOR["device_id"], VECTOR["nonce"])
    assert msg.hex() == VECTOR["msg_hex"] and msg.decode() == VECTOR["msg_utf8"]
    assert msg == b"soul-auth-v1\nsoul.example\nsoul-a1b2c3d4e5f6\n" + VECTOR["nonce"].encode()
    pub, sig = b64u_decode(VECTOR["pub"]), b64u_decode(VECTOR["sig"])
    assert len(VECTOR["pub"]) == 87 and len(pub) == 65 and pub[0] == 4
    assert len(VECTOR["sig"]) == 86 and len(sig) == 64
    assert verify_sig(pub, msg, sig)
    assert not verify_sig(pub, msg, b64u_decode(VECTOR["sig_other_host"]))
    assert not verify_sig(pub, msg + b"x", sig)
    assert not verify_sig(pub, msg, sig[:63])
    assert DeviceKey.from_scalar(int(VECTOR["priv_hex"], 16)).pub == VECTOR["pub"]


def test_host_normalisation_and_helpers():
    assert normalize_host("HTTPS://Soul.Example:443/x") == "soul.example"
    assert normalize_host("localhost:8787") == "localhost:8787"
    assert normalize_code(" 7kq3-m9xd ") == "7KQ3M9XD" and normalize_code("O1IL") == "0111"
    assert account_hint("ana@gmail.com") == "a***@gmail.com"
    assert posix_tz("Europe/Bucharest") == "EET-2EEST,M3.5.0/3,M10.5.0/4"
    assert posix_tz("Not/AZone") == "EET-2EEST,M3.5.0/3,M10.5.0/4"


# ----------------------------------------------------------------------- auth --

def test_pending_enrolment_issues_a_token_and_state_pending(tmp_path):
    e = Env(tmp_path)
    key = DeviceKey.generate()
    res = e.store.authenticate(signed(e.store, key), IP)
    assert res["token"].startswith("sdt_") and len(res["token"]) > 40
    assert res["expires_in"] == 86400 and res["ws_url"] == f"wss://{HOST}/v1/device/ws"
    assert res["state"] == "pending" and res["owner"] == "" and res["trial"] is None
    ctx = e.store.device_from_token(res["token"])
    assert ctx.device_id == DEV and ctx.key_state == "pending"
    assert e.store.device_from_token("Bearer " + res["token"]).device_id == DEV
    # tokens are stored hashed
    rows = e.store.db.execute("SELECT hash FROM device_tokens").fetchall()
    assert all(res["token"] not in r["hash"] for r in rows)


def test_nonce_is_single_use_bound_to_device_network_and_60s(tmp_path):
    e = Env(tmp_path)
    key = DeviceKey.generate()
    body = signed(e.store, key)
    e.store.authenticate(body, IP)
    assert err(e.store.authenticate, body, IP).code == "bad_nonce"            # replayed
    assert err(e.store.authenticate, signed(e.store, key), "198.51.100.1").code == "bad_nonce"  # other /24
    e.store.authenticate(signed(e.store, key), "203.0.113.200")             # same /24 is fine
    body = signed(e.store, key)
    e.clock.advance(61)
    assert err(e.store.authenticate, body, IP).code == "bad_nonce"            # expired
    nonce = e.store.issue_nonce(DEV2, IP)["nonce"]                          # nonce of another device
    b = {"device_id": DEV, "pub": key.pub, "nonce": nonce, "sig": key.sign(auth_message(HOST, DEV, nonce))}
    assert err(e.store.authenticate, b, IP).code == "bad_nonce"


def test_signature_for_another_host_or_key_is_rejected(tmp_path):
    e = Env(tmp_path)
    key = DeviceKey.generate()
    ex = err(e.store.authenticate, signed(e.store, key, host="evil.example"), IP)
    assert (ex.status, ex.code) == (401, "bad_signature")
    body = signed(e.store, key)
    body["pub"] = DeviceKey.generate().pub
    assert err(e.store.authenticate, body, IP).code == "bad_signature"


@pytest.mark.parametrize("patch,code", [
    ({"device_id": "soul-XYZ"}, "bad_request"), ({"pub": "abc"}, "bad_request"),
    ({"pub": "A" * 87}, "bad_request"), ({"sig": "short"}, "bad_request"), ({"nonce": 5}, "bad_request"),
])
def test_malformed_auth_bodies(tmp_path, patch, code):
    e = Env(tmp_path)
    body = signed(e.store, DeviceKey.generate())
    body.update(patch)
    ex = err(e.store.authenticate, body, IP)
    assert ex.status == 400 and ex.code == code


def test_factory_policy_only_accepts_imported_keys_and_gives_a_trial(tmp_path):
    e = Env(tmp_path, policy="factory", trial=30)
    key = DeviceKey.generate()
    ex = err(e.store.authenticate, signed(e.store, key), IP)
    assert (ex.status, ex.code) == (403, "not_enrolled")
    csv = tmp_path / "factory.csv"
    csv.write_text(f"device_id,pub\n{DEV},{key.pub}\n")
    assert e.store.import_factory(str(csv)) == 1
    res = e.store.authenticate(signed(e.store, key), IP)
    assert res["state"] == "unpaired" and res["trial"] == {"left": 30, "unit": "turns"}
    other = DeviceKey.generate()
    assert err(e.store.authenticate, signed(e.store, other), IP).code == "not_enrolled"


def test_pending_keys_are_capped_at_five_per_device(tmp_path):
    e = Env(tmp_path)
    for _ in range(6):
        e.store.buckets = type(e.store.buckets)(e.clock)  # reset the per-device auth bucket
        e.store.authenticate(signed(e.store, DeviceKey.generate()), IP)
    n = e.store.db.execute("SELECT COUNT(*) n FROM device_keys WHERE device_id=? AND state='pending'",
                           (DEV,)).fetchone()["n"]
    assert n == 5


def test_auth_rate_limits_per_device(tmp_path):
    e = Env(tmp_path)
    key = DeviceKey.generate()
    for _ in range(10):
        e.store.authenticate(signed(e.store, key), IP)
    ex = err(e.store.authenticate, signed(e.store, key), IP)
    assert (ex.status, ex.code) == (429, "rate_limited") and ex.retry_ms > 0


def test_token_expiry_and_garbage(tmp_path):
    e = Env(tmp_path)
    tok = e.store.authenticate(signed(e.store, DeviceKey.generate()), IP)["token"]
    assert err(e.store.device_from_token, "").code == "unauthenticated"
    assert err(e.store.device_from_token, "sdt_nope").code == "unauthenticated"
    e.clock.advance(86401)
    assert err(e.store.device_from_token, tok).code == "token_expired"


# -------------------------------------------------------------------- pairing --

def _auth(e, key=None, device_id=DEV):
    key = key or DeviceKey.generate()
    tok = e.store.authenticate(signed(e.store, key, device_id=device_id), IP)["token"]
    return key, e.store.device_from_token(tok)


def test_pairing_code_shape_url_and_hashing(tmp_path):
    e = Env(tmp_path)
    _auth(e)
    m = e.store.current_code(DEV)
    assert m["t"] == "pairing" and len(m["code"]) == 8 and set(m["code"]) <= set(CROCKFORD)
    assert m["url"] == f"https://{HOST}/pair#c={m['code']}&d={DEV}" and m["expires_in"] == 600
    assert e.store.current_code(DEV)["code"] == m["code"]          # stable until it expires
    row = e.store.db.execute("SELECT code_hash FROM pairing_codes").fetchone()
    assert m["code"] not in row["code_hash"]
    e.clock.advance(601)
    assert e.store.current_code(DEV)["code"] != m["code"]          # rotated on expiry


def test_claim_never_binds_until_the_device_says_ok(tmp_path):
    e = Env(tmp_path)
    _, ctx = _auth(e)
    code = e.store.current_code(DEV)["code"]
    c = e.store.claim("acc_1", "Ana", "ana@example.com", code[:4] + "-" + code[4:].lower(), IP)
    assert c["state"] == "awaiting_device" and c["expires_in"] == 120 and c["device"]["id"] == DEV
    confirm = c["_device_msg"]
    assert confirm == {"v": 1, "t": "pair.confirm", "pid": c["pid"], "name": "Ana",
                       "account_hint": "a***@example.com", "expires_in": 120}
    assert e.store.owner(DEV) is None and e.store.claim_state(c["pid"], "acc_1") == {"state": "awaiting_device"}
    assert err(e.store.claim, "acc_2", "Bo", "b@x.io", code, IP).code == "not_found"   # single use
    # another device's socket cannot confirm
    _, ctx2 = _auth(e, device_id=DEV2)
    assert e.store.on_device_answer(ctx2, c["pid"], True) is None
    paired = e.store.on_device_answer(ctx, c["pid"], True)
    assert paired == {"v": 1, "t": "paired", "owner": "Ana", "account_hint": "a***@example.com"}
    assert e.store.owner(DEV) == "acc_1" and e.store.device_state(ctx) == "paired"
    assert e.store.claim_state(c["pid"], "acc_1") == {"state": "paired"}
    assert err(e.store.claim_state, c["pid"], "acc_other").code == "not_found"
    assert e.store.members(DEV) == ["acc_1"] and e.store.account_devices("acc_1") == [DEV]


def test_pair_no_and_expiry(tmp_path):
    e = Env(tmp_path)
    _, ctx = _auth(e)
    c = e.store.claim("acc_1", "Ana", "ana@example.com", e.store.current_code(DEV)["code"], IP)
    assert e.store.on_device_answer(ctx, c["pid"], False) is None
    assert e.store.claim_state(c["pid"], "acc_1")["state"] == "rejected"
    c = e.store.claim("acc_1", "Ana", "ana@example.com", e.store.current_code(DEV)["code"], IP)
    e.clock.advance(121)
    assert e.store.claim_state(c["pid"], "acc_1")["state"] == "expired"
    assert e.store.expire_claims() == [DEV]
    assert e.store.on_device_answer(ctx, c["pid"], True) is None and e.store.owner(DEV) is None


def test_device_owned_by_another_account(tmp_path):
    e = Env(tmp_path)
    e.paired_device(account="acc_1")
    ex = err(e.store.claim, "acc_2", "Bo", "bo@example.com", e.store.current_code(DEV)["code"], IP)
    assert (ex.status, ex.code) == (409, "device_owned")


def test_failed_claim_limits_per_account_and_fleet(tmp_path):
    e = Env(tmp_path)
    for _ in range(5):
        assert err(e.store.claim, "acc_1", "A", "a@x.io", "ZZZZZZZZ", IP).code == "not_found"
    assert err(e.store.claim, "acc_1", "A", "a@x.io", "ZZZZZZZZ", IP).code == "rate_limited"
    # fleet-wide: 1,000 failures an hour pause every claim for 15 minutes (+ alert)
    alerts = []
    e.store.alerts.append(lambda kind, data: alerts.append(kind))
    for i in range(1000):
        e.store._claim_fail(f"acc_x{i}", f"10.{i // 250}.{i % 250}.1")
    assert alerts == ["pairing_fleet_limit"]
    _auth(e)
    ex = err(e.store.claim, "acc_new", "N", "n@x.io", e.store.current_code(DEV)["code"], "192.0.2.1")
    assert ex.code == "rate_limited" and ex.retry_ms > 0
    e.clock.advance(15 * 60 + 1)
    assert e.store.claim("acc_new", "N", "n@x.io", e.store.current_code(DEV)["code"], "192.0.2.1")["pid"]


def test_pairing_a_new_key_revokes_the_old_ones(tmp_path):
    e = Env(tmp_path)
    old = DeviceKey.generate()
    e.paired_device(key=old, account="acc_1")
    e.store.unpair(DEV, "user")
    new, ctx = _auth(e)
    c = e.store.claim("acc_2", "Bo", "bo@example.com", e.store.current_code(DEV)["code"], IP)
    assert e.store.on_device_answer(ctx, c["pid"], True)
    ex = err(e.store.authenticate, signed(e.store, old), IP)
    assert (ex.status, ex.code) == (403, "key_revoked")


def test_reset_true_from_a_bound_key_unpairs_and_revokes_tokens(tmp_path):
    e = Env(tmp_path)
    d = e.paired_device(account="acc_1")
    old_token = d.token
    seen = []
    e.store.on_unpair.append(lambda dev, reason, old, erase: seen.append((dev, reason, old)))
    d.reset_flag = True
    d.authenticate()
    assert d.auth_info["state"] == "unpaired" and e.store.owner(DEV) is None
    assert seen == [(DEV, "reset", "acc_1")]
    assert err(e.store.device_from_token, old_token).code == "unauthenticated"
    assert e.store.device_from_token(d.token).device_id == DEV


# --------------------------------------------------------------------- outbox --

def test_outbox_is_gap_free_pages_and_acks(tmp_path):
    e = Env(tmp_path)
    e.paired_device()
    seqs = [e.store.enqueue(DEV, "note.create", {"text": f"n{i}", "tags": []}, f"it_{i}", {"kind": "app"})
            for i in range(60)]
    assert seqs == list(range(1, 61)) and e.store.last_seq(DEV) == 60
    page, more = e.store.replay(DEV, 0)
    assert len(page) == 50 and more and page[0]["seq"] == 1 and page[-1]["seq"] == 50
    page2, more2 = e.store.replay(DEV, 50)
    assert [m["seq"] for m in page2] == list(range(51, 61)) and not more2
    assert e.store.ack(DEV, 3, True)["item_id"] == "it_2"
    assert e.store.ack(DEV, 999, True) is None and e.store.ack(DEV, True, True) is None
    e.store.ack_upto(DEV, 40)
    page, _ = e.store.replay(DEV, 0)
    assert page[0]["seq"] == 41
    assert e.store.next_seq(DEV2) == 1  # counters are per device


def test_push_shape_flags_card_ttl_and_missed_reminders(tmp_path):
    e = Env(tmp_path)
    e.paired_device()
    e.store.enqueue(DEV, "answer.show", {"title": "T", "body": "B"}, "it_c", {"kind": "connector", "app": "claude"},
                    say="De la Claude: hi", private=True)
    e.store.enqueue(DEV, "reminder.create", {"when": "2026-10-01T09:00", "text": "old"}, "it_r",
                    {"kind": "connector", "app": "claude"}, needs_accept=True)
    page, _ = e.store.replay(DEV, 0)
    card, rem = page
    assert card["private"] is True and card["say"] == "De la Claude: hi"
    assert card["expires_at"] == int(e.clock()) + 6 * 3600 and "needs_accept" not in card
    assert rem["needs_accept"] is True and rem["missed"] is True and "expires_at" not in rem
    e.clock.advance(6 * 3600)
    assert e.store.expire_cards() == 1
    assert [m["item_id"] for m in e.store.replay(DEV, 0)[0]] == ["it_r"]


def test_unpair_drops_undelivered_pushes_and_erase_wipes(tmp_path):
    e = Env(tmp_path)
    e.paired_device()
    e.store.enqueue(DEV, "note.create", {"text": "x", "tags": []}, "it_1", {"kind": "app"})
    e.store.inbox_add(DEV, "0123456789abcdef", "hello claude", "claude")
    e.store.unpair(DEV, "user", erase=True)
    assert e.store.replay(DEV, 0) == ([], False)
    assert e.store.inbox_list(DEV, None) == [] and e.store.revoked(DEV) is False
    assert e.store.last_seq(DEV) == 1  # the counter survives: seq never goes back


def test_no_secret_reaches_the_log(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    e = Env(tmp_path)
    key = DeviceKey.generate()
    body = signed(e.store, key)
    tok = e.store.authenticate(body, IP)["token"]
    code = e.store.current_code(DEV)["code"]
    for _ in range(5):
        try:
            e.store.claim("acc_1", "A", "a@x.io", "WRONG123", IP)
        except GatewayError:
            pass
    text = caplog.text + repr(e.store)
    for secret in (tok, code, body["nonce"], body["sig"]):
        assert secret not in text


def test_store_on_disk(tmp_path):
    path = tmp_path / "gw" / "gateway.sqlite"
    s = DeviceStore(str(path), host=HOST, policy="pending", pepper=b"p" * 32)
    s.import_factory([(DEV, DeviceKey.generate().pub)])
    assert DeviceStore(str(path), host=HOST, policy="factory", pepper=b"p" * 32).get_device(DEV) is not None
    with pytest.raises(ValueError):
        DeviceStore(":memory:", policy="open")
