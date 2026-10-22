#!/usr/bin/env python3
"""SoulOS Alive stills: mask every NN-*.png in <dir> to the round 466 x 466 screen of SOUL S (transparent outside the glass),
then build <dir>/soulos-alive-sheet.png with glass_sheet.py.   python3 os/tools/alive_post.py os/screenshots/alive"""
import glob
import os
import subprocess
import sys

from PIL import Image, ImageDraw

d = sys.argv[1]
S = 466   # SOUL S, the 1.75" AMOLED (docs/size-s.json resolution)
mask = Image.new("L", (S * 4, S * 4), 0)
ImageDraw.Draw(mask).ellipse((0, 0, S * 4 - 1, S * 4 - 1), fill=255)
mask = mask.resize((S, S), Image.LANCZOS)
files = sorted(glob.glob(os.path.join(d, "[0-9][0-9]-*.png")))
for f in files:
    im = Image.open(f).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((S, S), Image.LANCZOS)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    out.save(f)
print("masked", len(files), "stills to", S, "x", S)
here = os.path.dirname(os.path.abspath(__file__))
subprocess.check_call([sys.executable, os.path.join(here, "glass_sheet.py"), d, os.path.join(d, "soulos-alive-sheet.png"),
                       "--title", "SoulOS Alive (web prototype, SOUL S 466 x 466)",
                       "--sub", "The eyes are the OS: pure black, flat pebbles, the palette of the eyes each SOUL is born with + its body colour.",
                       "--cols", "6"])
