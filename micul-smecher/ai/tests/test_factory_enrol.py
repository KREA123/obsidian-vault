"""The factory station (tools/factory_enrol.py): SOULKEY GEN over serial -> the factory list -> production enrolment
(`SOUL_ENROL_POLICY=factory` accepts exactly these keys). The device is a fake serial port that answers like the
firmware does (src/main.cpp 'S' command)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import factory_enrol as fe  # noqa: E402
from fake_device import DeviceKey, FakeDevice, Http  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from suflet_ai.devices import DeviceStore  # noqa: E402

DEV = "soul-a1b2c3d4e5f6"


class FakeSerial:
    """Answers SOULKEY GEN like the firmware: boot chatter first, then the public key (made once)."""

    def __init__(self, device_id: str, key: DeviceKey, err: str = ""):
        self.device_id, self.key, self.err = device_id, key, err
        self.out = [b"[board] lcd28 480x480\n", b"\n"]
        self.made = False

    def write(self, data: bytes) -> int:
        assert data == b"SOULKEY GEN\n"
        if self.err:
            self.out.append(f"SOULKEY ERR {self.err}\n".encode())
        else:
            self.out.append(f"SOULKEY PUB {self.device_id} {self.key.pub}{'' if self.made else ' new'}\n".encode())
            self.made = True
        return len(data)

    def readline(self) -> bytes:
        return self.out.pop(0) if self.out else b""


def test_parse_replies():
    k = DeviceKey.generate()
    assert fe.parse_reply(f"SOULKEY PUB {DEV} {k.pub} new") == (DEV, k.pub, True)
    assert fe.parse_reply("[cloud] signed in") is None
    with pytest.raises(fe.EnrolError):
        fe.parse_reply("SOULKEY ERR generate failed")
    with pytest.raises(fe.EnrolError):
        fe.parse_reply(f"SOULKEY PUB {DEV} " + "A" * 87)  # not a point on the curve
    with pytest.raises(fe.EnrolError):
        fe.parse_reply(f"SOULKEY PUB soul-XYZ {k.pub}")


def test_station_enrols_and_production_accepts_only_listed_keys(tmp_path):
    key = DeviceKey.generate()
    csv_path = tmp_path / "factory.csv"
    db = str(tmp_path / "gateway.sqlite")
    logs = []
    assert fe.enrol_one(FakeSerial(DEV, key), csv_path, db, log=logs.append) == (DEV, key.pub)
    assert logs[-1].startswith("NEW ENROLLED") and "A1B2-C3D4" not in logs[-1] and "C3D4-E5F6" in logs[-1]
    # the same unit again: listed once
    port = FakeSerial(DEV, key)
    port.made = True
    fe.enrol_one(port, csv_path, log=logs.append)
    assert logs[-1].startswith("ALREADY LISTED")
    assert fe.load_csv(csv_path) == [(DEV, key.pub)]
    assert csv_path.read_text().splitlines()[0] == "device_id,pub"
    assert "PRIVATE" not in csv_path.read_text().upper()
    # a re-flashed unit with a new key (soulid erased) is refused, not silently re-enrolled
    with pytest.raises(fe.EnrolError):
        fe.enrol_one(FakeSerial(DEV, DeviceKey.generate()), csv_path)
    with pytest.raises(fe.EnrolError):
        fe.enrol_one(FakeSerial("soul-0011223344ff", key, err="generate failed"), csv_path)
    # production enrolment: the listed key signs in, another key for the same id does not
    store = DeviceStore(db, host="soul.example", policy="factory", pepper=b"p" * 32)
    gw_app = FastAPI()
    from suflet_ai.gateway import Gateway, build_router
    from suflet_ai.soul import SoulService
    from suflet_ai.config import Settings

    gw = Gateway(SoulService(Settings(data_dir=str(tmp_path)), master_secret=b"m" * 32), store)
    gw_app.include_router(build_router(lambda: gw))
    client = TestClient(gw_app)
    good = FakeDevice(Http(client), DEV, key, "soul.example")
    assert good.authenticate()["state"] == "unpaired"
    bad = FakeDevice(Http(client), DEV, DeviceKey.generate(), "soul.example")
    with pytest.raises(Exception) as ei:
        bad.authenticate()
    assert "not_enrolled" in str(ei.value)


def test_replay_a_captured_log(tmp_path, capsys):
    k1, k2 = DeviceKey.generate(), DeviceKey.generate()
    log = tmp_path / "station.log"
    log.write_text(f"boot\nSOULKEY PUB {DEV} {k1.pub} new\nnoise\nSOULKEY PUB soul-0011223344ff {k2.pub}\n")
    db = str(tmp_path / "g.sqlite")
    assert fe.main(["--log", str(log), "--csv", str(tmp_path / "f.csv"), "--import-db", db]) == 0
    assert "2 new device(s)" in capsys.readouterr().out
    store = DeviceStore(db, host="soul.example", policy="factory", pepper=b"p" * 32)
    rows = store.db.execute("SELECT device_id, state FROM device_keys ORDER BY device_id").fetchall()
    assert [(r["device_id"], r["state"]) for r in rows] == [("soul-0011223344ff", "factory"), (DEV, "factory")]
