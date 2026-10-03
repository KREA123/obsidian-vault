#!/usr/bin/env python3
"""SoulOS apps: the simulator's stills (sim_apps.cpp writes NN-name.ppm) -> PNGs + one contact sheet.

    .pio/build/sim/program /tmp/apps apps
    python3 tools/app_shots.py /tmp/apps sim/shots/apps [--title ...]

The sheet is os/tools/glass_sheet.py's (the same look as the web's), written as <out>/soulos-apps-sheet-device.png.
"""
import argparse
import glob
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, "..", "..", "os", "tools", "glass_sheet.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--title", default="SoulOS apps on the device (firmware v1.7.0 simulator, 480 px)")
    ap.add_argument("--sub", default="The firmware's own pixels: every app, the map and the games. Behind the eyes always black; the aura only on OS screens.")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "[0-9][0-9]-*.png")):
        os.remove(f)
    files = sorted(glob.glob(os.path.join(a.src, "[0-9][0-9]-*.ppm")))
    if not files:
        sys.exit("no stills in " + a.src)
    for f in files:
        Image.open(f).convert("RGB").save(os.path.join(a.out, os.path.basename(f)[:-4] + ".png"), optimize=True)
    sheet = os.path.join(a.out, "soulos-apps-sheet-device.png")
    subprocess.check_call([sys.executable, SHEET, a.out, sheet, "--title", a.title, "--sub", a.sub, "--cols", "6"])
    print(len(files), "stills ->", a.out, "+", os.path.basename(sheet))


if __name__ == "__main__":
    main()
