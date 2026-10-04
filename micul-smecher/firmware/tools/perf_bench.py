#!/usr/bin/env python3
"""The reproducible frame-cost table of firmware/PERF.md, and the pixel-exact before/after check.

    python3 tools/perf_bench.py                       every scenario under callgrind -> a markdown table + JSON
    python3 tools/perf_bench.py --designs             + standby on all 120 designs (bench_eyes, SIM_DESIGN=i)
    python3 tools/perf_bench.py --json out.json       keep the numbers (compare two runs with --compare)
    python3 tools/perf_bench.py --compare a.json b.json   the before -> after table
    python3 tools/perf_bench.py --hashes DIR          every scenario + design + the app stills, one hash per frame
    python3 tools/perf_bench.py --check DIR_A DIR_B   are two --hashes runs pixel-identical? (exit 1 if not)
    python3 tools/perf_bench.py --verify              every incremental frame vs the same state drawn whole
                                                      (SIM_VERIFY=1): which views ever differ, how many frames

Needs `pio run -e sim` first and valgrind. Instructions are callgrind's Ir (x86-64, the sim built -O2): the
same counts BRINGUP.md §4-4e used. The ESP32-S3 estimate scales them by NS_PER_IR (calibrated in BRINGUP §4b:
6.3 M instructions ~ 11-18 ms on the S3 at 240 MHz, i.e. 1.75-2.9 ns; the middle is used) and adds the copy
into the 2.8C's back frame buffer at PSRAM_MBPS. Both are estimates until BRINGUP §5 measures them on a board.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FW = Path(__file__).resolve().parents[1]
PROGRAM = FW / ".pio" / "build" / "sim" / "program"
NS_PER_IR = 2.3        # ESP32-S3 ns per x86 instruction of the sim (BRINGUP §4b calibration, mid-range)
PSRAM_MBPS = 50.0      # canvas -> back frame buffer memcpy, PSRAM to PSRAM (payload MB/s; measure: `F`, push ms)
LOOP_MS = 1.0          # touch, IMU, BLE, the Brain and SoulOS update per frame (outside compose)
COMPOSE = "suflet::FrameComposer::compose*"
MICRO = "suflet_bench_*"

# (scenario, what it is, fps SoulOS asks for there)
FRAMES = [
    ("bench_standby", "Standby: the eyes alone, nobody touches it (Lollipop, spiral pupils)", 24),
    ("home", "Home: boop, laugh, look at the finger", 30),
    ("expressions", "All 31 expressions / reactions", 30),
    ("motion", "IMU motion: level keeping, spin (dizzy), marble pupils, nod", 30),
    ("bench_notify", "Notifications: a capsule on standby every 1.5 s", 30),
    ("launcher", "Launcher orbit: swipe, open Alarms, set one", 30),
    ("bench_typing", "Keyboard typing (35 glass caps)", 30),
    ("bench_screen", "Glass screen open, idle (Settings, aura on)", 30),
    ("bench_drift", "Glass screen, device tilted (aura drift / tilt repaints)", 30),
    ("bench_nav", "Screens opened and closed every second (aura fades on/off)", 30),
    ("talk", "Talk: keyboard, thinking, the answer", 30),
    ("claude", "Claude asks: shocked, wide eyes, rim rings", 30),
    ("bench_maps", "Maps: pan, rim zoom, route preview, walking", 30),
    ("bench_games", "Games: tilt ball + rhythm", 30),
]
MICROS = [
    ("bench_json", "Cloud JSON: the recorded SOUL Cloud session (33 frames) + a Claude answer", "session"),
    ("bench_memory", "SOUL Memory: rank + context block over 200 facts", "question"),
    ("bench_wifi", "Wi-Fi roam: a scan of 30 APs against 8 saved networks", "scan"),
    ("bench_boot", "Boot: SoulOS begin (glass aura built) + the first frame", "boot"),
]
APPS_STILLS = "apps"


def callgrind(scenario: str, toggle: str, env: dict | None = None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "cg.out")
        e = dict(os.environ, SIM_HASH="1", **(env or {}))
        p = subprocess.run(["valgrind", "--tool=callgrind", f"--toggle-collect={toggle}", f"--callgrind-out-file={out}",
                            str(PROGRAM), tmp, scenario], capture_output=True, text=True, env=e)
        if p.returncode != 0:
            raise RuntimeError(f"{scenario}: {p.stderr[-800:]}")
        total = 0
        with open(out) as f:
            for line in f:
                if line.startswith(("summary:", "totals:")):
                    total = int(line.split()[1])
        res = {"ir": total}
        m = re.search(r"^BENCH \S+ composed=(\d+) changed_px=(\d+) copied_px=(\d+)", p.stdout, re.M)
        if m:
            res.update(frames=int(m[1]), changed_px=int(m[2]), copied_px=int(m[3]))
        m = re.search(r"^MICRO \S+ ops=(\d+)", p.stdout, re.M)
        if m:
            res.update(ops=int(m[1]))
        return res


def frame_row(name: str, r: dict, fps_asked: int) -> dict:
    n = max(1, r.get("frames", 1))
    mir = r["ir"] / n / 1e6
    render = mir * NS_PER_IR
    push = r.get("copied_px", 0) * 2 / (PSRAM_MBPS * 1e6) * 1e3
    frame = render + push + LOOP_MS
    cap = 1000.0 / (frame * 1.6)  # main.cpp's adaptive cap keeps the loop under ~60 % of a core
    fps = min(fps_asked, max(12.0, cap)) if cap < fps_asked else fps_asked
    return dict(name=name, frames=n, mir=mir, render_ms=render, copied_px=r.get("copied_px", 0), push_ms=push,
                frame_ms=frame, fps=fps, fps_asked=fps_asked)


def run_all(designs: bool, jobs: int) -> dict:
    tasks = {}
    with cf.ThreadPoolExecutor(jobs) as ex:
        for name, _what, _fps in FRAMES:
            tasks[("frame", name)] = ex.submit(callgrind, name, COMPOSE)
        for name, _what, _unit in MICROS:
            tasks[("micro", name)] = ex.submit(callgrind, name, MICRO)
        if designs:
            for i in range(120):
                tasks[("design", i)] = ex.submit(callgrind, "bench_eyes", COMPOSE, {"SIM_DESIGN": str(i)})
        res = {"frames": {}, "micro": {}, "designs": {}}
        for (kind, key), fut in tasks.items():
            r = fut.result()
            if kind == "frame":
                fps = next(f for n, _w, f in FRAMES if n == key)
                res["frames"][key] = frame_row(key, r, fps)
            elif kind == "micro":
                res["micro"][key] = dict(name=key, ops=r.get("ops", 1), ir=r["ir"], ir_per_op=r["ir"] / max(1, r.get("ops", 1)))
            else:
                res["designs"][str(key)] = frame_row(f"design {key}", r, 24)
    return res


def design_names() -> list[str]:
    names = []
    src = (FW / "lib" / "Suflet" / "src" / "EyeTables.h").read_text()
    for m in re.finditer(r'^\s*\{"([a-z0-9_-]+)",\s*.+?,\s*(\d+),\s*Rarity::(\w+)', src, re.M):
        names.append(f"#{int(m[2]):03d} {m[1]} ({m[3]})")
    return names


def table(res: dict) -> str:
    out = ["| Scenario | M instr / frame | est. render ms | px copied / frame | est. push ms | est. fps (asked) |",
           "|---|---:|---:|---:|---:|---:|"]
    for name, what, _fps in FRAMES:
        r = res["frames"].get(name)
        if not r:
            continue
        out.append(f"| {what} (`{name}`) | {r['mir']:.2f} | {r['render_ms']:.1f} | {r['copied_px']:,} | "
                   f"{r['push_ms']:.1f} | {r['fps']:.0f} ({r['fps_asked']}) |")
    out += ["", "| Work | instr / op | est. ESP32 ms / op |", "|---|---:|---:|"]
    for name, what, unit in MICROS:
        r = res["micro"].get(name)
        if r:
            out.append(f"| {what} (`{name}`, per {unit}) | {r['ir_per_op'] / 1e6:.2f} M | {r['ir_per_op'] * NS_PER_IR / 1e6:.2f} |")
    if res.get("designs"):
        names = design_names()
        rows = sorted(res["designs"].items(), key=lambda kv: -kv[1]["mir"])
        mirs = [r["mir"] for _k, r in rows]
        out += ["", f"All {len(rows)} designs, standby (`bench_eyes`, 4 s): median {sorted(mirs)[len(mirs) // 2]:.2f} M, "
                f"max {mirs[0]:.2f} M instructions / frame. The ten heaviest:", "",
                "| Design | M instr / frame | est. render ms |", "|---|---:|---:|"]
        for k, r in rows[:10]:
            nm = names[int(k)] if int(k) < len(names) else k
            out.append(f"| {nm} | {r['mir']:.2f} | {r['render_ms']:.1f} |")
    return "\n".join(out)


def compare(a: dict, b: dict) -> str:
    out = ["| Scenario | before M instr | after M instr | Δ | before px copied | after px copied | est. frame ms before → after | est. fps before → after |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, what, _fps in FRAMES:
        x, y = a["frames"].get(name), b["frames"].get(name)
        if not x or not y:
            continue
        out.append(f"| {what} | {x['mir']:.2f} | {y['mir']:.2f} | {100 * (y['mir'] / x['mir'] - 1):+.0f} % | "
                   f"{x['copied_px']:,} | {y['copied_px']:,} | {x['frame_ms']:.1f} → {y['frame_ms']:.1f} | "
                   f"{x['fps']:.0f} → {y['fps']:.0f} |")
    out += ["", "| Work | before instr / op | after | Δ |", "|---|---:|---:|---:|"]
    for name, what, unit in MICROS:
        x, y = a["micro"].get(name), b["micro"].get(name)
        if x and y:
            out.append(f"| {what} (per {unit}) | {x['ir_per_op'] / 1e6:.2f} M | {y['ir_per_op'] / 1e6:.2f} M | "
                       f"{100 * (y['ir_per_op'] / x['ir_per_op'] - 1):+.0f} % |")
    if a.get("designs") and b.get("designs"):
        names = design_names()
        keys = sorted(a["designs"], key=lambda k: -a["designs"][k]["mir"])
        xa = sorted(r["mir"] for r in a["designs"].values())
        xb = sorted(r["mir"] for r in b["designs"].values())
        out += ["", f"All 120 designs (standby): median {xa[60]:.2f} → {xb[60]:.2f} M, worst {xa[-1]:.2f} → {xb[-1]:.2f} M "
                "instructions / frame.", "", "| Design (the ten heaviest before) | before M | after M | Δ |", "|---|---:|---:|---:|"]
        for k in keys[:10]:
            x, y = a["designs"][k]["mir"], b["designs"][k]["mir"]
            out.append(f"| {names[int(k)] if int(k) < len(names) else k} | {x:.2f} | {y:.2f} | {100 * (y / x - 1):+.0f} % |")
    return "\n".join(out)


def hashes(dest: Path, jobs: int) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, SIM_HASH="1")

    def one(args, sub=None, extra=None):
        d = dest / sub if sub else dest
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(PROGRAM), str(d), *args], check=True, capture_output=True, env=dict(env, **(extra or {})))

    with cf.ThreadPoolExecutor(jobs) as ex:
        futs = [ex.submit(one, ["all"]), ex.submit(one, ["bench_maps"]), ex.submit(one, ["bench_games"]),
                ex.submit(one, [APPS_STILLS], "apps")]
        futs += [ex.submit(one, ["all", "000000000000", "466"], "s466")]  # the AMOLED 1.75 size too
        futs += [ex.submit(one, ["bench_eyes"], f"design{i:03d}", {"SIM_DESIGN": str(i)}) for i in range(120)]
        for f in futs:
            f.result()
    # the app stills are .ppm files: hash them too
    for ppm in sorted((dest / "apps").glob("*.ppm")):
        import hashlib
        (ppm.with_suffix(".hash")).write_text(hashlib.sha256(ppm.read_bytes()).hexdigest() + "\n")
        ppm.unlink()


def check(a: Path, b: Path) -> int:
    bad = 0
    files = sorted(p.relative_to(a) for p in a.rglob("*.hash"))
    if not files:
        print("no .hash files in", a)
        return 1
    for rel in files:
        fa, fb = (a / rel).read_text().split(), ((b / rel).read_text().split() if (b / rel).exists() else [])
        if fa != fb:
            diff = [i for i, (x, y) in enumerate(zip(fa, fb)) if x != y]
            print(f"DIFF {rel}: {len(fa)} vs {len(fb)} frames, first different frame {diff[:5] if diff else 'length'}")
            bad += 1
    print(f"{len(files)} hash files, {sum(len((a / r).read_text().split()) for r in files)} frames: "
          f"{'IDENTICAL' if not bad else f'{bad} differ'}")
    return 1 if bad else 0


def verify(jobs: int) -> int:
    """The frame pipeline's promise: what the dirty rectangles leave on the glass == a full redraw."""
    runs = [["all"], ["apps"], ["bench_maps"], ["bench_games"], ["all", "000000000000", "466"]]
    counts: dict = {}
    with tempfile.TemporaryDirectory() as tmp, cf.ThreadPoolExecutor(jobs) as ex:
        futs = [ex.submit(subprocess.run, [str(PROGRAM), tmp, *r], capture_output=True, text=True,
                          env=dict(os.environ, SIM_HASH="1", SIM_VERIFY="1")) for r in runs]
        for r, f in zip(runs, futs):
            for line in f.result().stderr.splitlines():
                m = re.match(r"frame \d+ view (\w+): (\d+) px differ", line)
                if m:
                    k = (" ".join(r), m[1])
                    n, px = counts.get(k, (0, 0))
                    counts[k] = (n + 1, max(px, int(m[2])))
    for (run, view), (n, px) in sorted(counts.items()):
        print(f"{run:>24}  view {view:<12} {n:4d} frames differ from a full redraw (at most {px} px)")
    print(f"{sum(n for n, _ in counts.values())} frames differ in all")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--compare", nargs=2)
    ap.add_argument("--hashes")
    ap.add_argument("--check", nargs=2)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.compare:
        print(compare(json.load(open(a.compare[0])), json.load(open(a.compare[1]))))
        return 0
    if a.check:
        return check(Path(a.check[0]), Path(a.check[1]))
    if not PROGRAM.exists():
        sys.exit("build the simulator first: pio run -e sim")
    if a.verify:
        return verify(a.jobs)
    if a.hashes:
        hashes(Path(a.hashes), a.jobs)
        return 0
    res = run_all(a.designs, a.jobs)
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
    print(table(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
