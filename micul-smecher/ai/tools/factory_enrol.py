#!/usr/bin/env python3
"""The factory provisioning station's enrolment step (docs/07-CONNECT-AI.md §5 founder action 5, §6.1, §3.2).

For each SOUL on the line, after flashing:

  1. over USB serial (115200), send `SOULKEY GEN`: the device makes its ECDSA P-256 key ONCE, with its hardware
     RNG, in its own NVS partition `soulid` (never erased by a factory reset), and answers
     `SOULKEY PUB soul-<12 hex> <pub b64url, 87 chars>[ new]` (or `SOULKEY ERR <why>`). There is no command that
     prints the private key: it never leaves the device.
  2. the public key is checked (a valid P-256 point, the device id from the eFuse MAC) and appended to the factory
     list CSV (`device_id,pub`), refusing a device id that is already listed with another key.
  3. optionally (`--import-db`) imported straight into the cloud's device store as `factory` keys, which is what
     `SOUL_ENROL_POLICY=factory` (production) accepts. On the deployed cloud the same CSV goes in with
     `python -m suflet_ai.app import-factory keys.csv` (fly ssh console).
  4. the box label: the device id (the QR on the box) is printed for the label printer.

    python tools/factory_enrol.py --port /dev/ttyACM0 --csv factory_keys.csv [--import-db gateway.sqlite]
    python tools/factory_enrol.py --log station.log --csv factory_keys.csv      # replay a captured serial log

The CSV holds public keys only; nothing secret ever passes through the station. pyserial is needed only for
--port (`pip install pyserial`).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Protocol, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from suflet_ai.devices import GatewayError, check_device_id, parse_pub  # noqa: E402

LINE = re.compile(r"^SOULKEY (PUB|ERR) ?(.*)$")
PUB = re.compile(r"^(soul-[0-9a-f]{12}) ([A-Za-z0-9_-]{87})( new)?$")


class Port(Protocol):
    def write(self, data: bytes) -> int: ...
    def readline(self) -> bytes: ...


class EnrolError(Exception):
    pass


def parse_reply(line: str) -> Optional[Tuple[str, str, bool]]:
    """`SOULKEY PUB soul-… <pub>[ new]` -> (device_id, pub, new); `SOULKEY ERR …` raises; other lines -> None."""
    m = LINE.match(line.strip())
    if not m:
        return None
    if m.group(1) == "ERR":
        raise EnrolError(f"the device said: {m.group(2) or 'error'}")
    p = PUB.match(m.group(2))
    if not p:
        raise EnrolError("the device answered SOULKEY PUB without a device id and an 87-character key")
    device_id, pub = check_device_id(p.group(1)), p.group(2)
    try:
        parse_pub(pub)  # a real point on P-256
    except GatewayError as e:
        raise EnrolError(f"not a P-256 public key: {e.msg}") from None
    return device_id, pub, bool(p.group(3))


def ask_device(port: Port, timeout_s: float = 10.0, clock=time.monotonic) -> Tuple[str, str, bool]:
    """SOULKEY GEN over the serial port; returns (device_id, pub, new). Boot chatter and logs are skipped."""
    port.write(b"SOULKEY GEN\n")
    end = clock() + timeout_s
    while clock() < end:
        raw = port.readline()
        if not raw:
            continue
        r = parse_reply(raw.decode("utf-8", "replace"))
        if r:
            return r
    raise EnrolError("no SOULKEY answer from the device (is it flashed with SOUL >= 1.3.0, at 115200?)")


def load_csv(path: Path) -> List[Tuple[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return [(r["device_id"].strip(), r["pub"].strip()) for r in csv.DictReader(f)]


def add_to_csv(path: Path, device_id: str, pub: str) -> bool:
    """Append (device_id, pub); False if it is already there. A device id with ANOTHER key is refused: that is
    either a re-flashed unit whose `soulid` partition was erased (fix the line) or a cloned MAC."""
    rows = load_csv(path)
    for d, p in rows:
        if d == device_id:
            if p == pub:
                return False
            raise EnrolError(f"{device_id} is already enrolled with another key: refusing (erased soulid, or a "
                             "duplicated MAC?)")
    new = not path.exists()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    with os.fdopen(fd, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["device_id", "pub"])
        w.writerow([device_id, pub])
    return True


def import_into(db: str, rows: Iterable[Tuple[str, str]], host: Optional[str] = None) -> int:
    from suflet_ai.devices import DeviceStore

    return DeviceStore(db, host=host, policy="factory").import_factory(list(rows))


def label(device_id: str) -> str:
    return f"SOUL  {device_id[9:13].upper()}-{device_id[13:17].upper()}  ({device_id})"  # the last 8 hex digits


def enrol_one(port: Port, csv_path: Path, import_db: Optional[str] = None, log=print) -> Tuple[str, str]:
    device_id, pub, made = ask_device(port)
    added = add_to_csv(csv_path, device_id, pub)
    if import_db:
        import_into(import_db, [(device_id, pub)])
    log(f"{'NEW ' if made else ''}{'ENROLLED' if added else 'ALREADY LISTED'}  {label(device_id)}")
    return device_id, pub


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SOUL factory station: device key -> factory list")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port", help="the device's USB serial port, e.g. /dev/ttyACM0 or COM5")
    src.add_argument("--log", help="a captured serial log to replay (lines with SOULKEY PUB …)")
    ap.add_argument("--csv", required=True, help="the factory list (device_id,pub), appended")
    ap.add_argument("--import-db", help="also import into this gateway.sqlite (factory keys)")
    a = ap.parse_args(argv)
    csv_path = Path(a.csv)
    try:
        if a.log:
            n = 0
            for line in Path(a.log).read_text(errors="replace").splitlines():
                r = parse_reply(line)
                if r and add_to_csv(csv_path, r[0], r[1]):
                    n += 1
                    print(f"ENROLLED  {label(r[0])}")
            if a.import_db:
                import_into(a.import_db, load_csv(csv_path))
            print(f"{n} new device(s) in {csv_path}")
            return 0
        try:
            import serial  # pyserial
        except ImportError:
            print("pip install pyserial (only needed with --port)")
            return 2
        with serial.Serial(a.port, 115200, timeout=0.5) as port:
            time.sleep(0.3)
            port.reset_input_buffer()
            enrol_one(port, csv_path, a.import_db)
        return 0
    except EnrolError as e:
        print(f"FAIL  {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
