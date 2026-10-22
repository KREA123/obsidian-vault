#!/usr/bin/env python3
"""Re-grade the transparent SOUL cut-outs (trailer/assets) into the five anodised finishes, so stills, GIFs and the
video show the same bead-blasted aluminium.

    python3 -I micul-smecher/crowdfunding/images/src/regrade.py

Method: the Silver cut-out is the master for every colour (same geometry, most tonal detail). Outside the glass
ellipse (from the cut-out's JSON), its luminance is normalised and mapped through a 4-stop ramp per finish
(a gradient map), then a fine grain is added for the bead-blast micro-texture. The glass keeps its original pixels.
Output: images/src/cuts/soul_col_<colour>.webp + .json (same geometry), soul_front_silver.webp + .json.
Ramps follow docs/02-MANUFACTURING.md §3 (sRGB targets) with cooler greys and a clearly warmer Champagne.
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
MS = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(MS, "trailer", "assets")
OUT = os.path.join(HERE, "cuts")

RAMPS = {  # shadow, low-mid, high-mid, highlight (sRGB)
    "silver":    ["#4A5058", "#8D939B", "#B9BEC5", "#E3E7EB"],
    "graphite":  ["#121417", "#2C3035", "#4C5259", "#878E97"],
    "midnight":  ["#0D1220", "#1E2A44", "#34466B", "#7D8DB0"],
    "ember":     ["#5A1E08", "#A8441A", "#D9662F", "#F7A777"],
    "champagne": ["#5E4524", "#A8844F", "#D2AE76", "#F3DDB2"],
}


def hexrgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255.0


def ramp(L, stops):
    cols = [hexrgb(h) for h in stops]
    pos = np.linspace(0, 1, len(cols))
    out = np.zeros(L.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(L, pos, [x[c] for x in cols])
    return out


def glass_mask(meta, w, h, grow=1.0):
    g = list(meta["souls"].values())[0]
    poly = [(x * w, y * h) for x, y in g["glass"]]
    cx, cy = g["c"][0] * w, g["c"][1] * h
    poly = [(cx + (x - cx) * grow, cy + (y - cy) * grow) for x, y in poly]
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    return np.asarray(m, np.float32) / 255.0


def grade(src_name, colour, out_name, seed=7):
    im = Image.open(os.path.join(SRC, src_name + ".webp")).convert("RGBA")
    meta = json.load(open(os.path.join(SRC, src_name + ".json")))
    a = np.asarray(im, np.float32) / 255.0
    rgb, alpha = a[..., :3], a[..., 3]
    w, h = im.size
    glass = glass_mask(meta, w, h, 1.0)
    body = (alpha > 0.02) & (glass < 0.5)
    L = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lo, hi = np.percentile(L[body], [1.5, 99.5])
    Lin = np.clip((L - lo) / max(hi - lo, 1e-4), 0, 1)
    # the render is mostly highlights: blend the linear stretch with a rank (CDF) map so every finish shows its full ramp
    vals = np.sort(L[body])
    cdf = np.searchsorted(vals, L) / len(vals)
    Ln = 0.45 * Lin + 0.55 * cdf
    rng = np.random.default_rng(seed)
    grain = rng.normal(0, 0.012, L.shape).astype(np.float32)
    new = ramp(np.clip(Ln + grain, 0, 1), RAMPS[colour])
    # keep the glass exactly; feather the boundary over a few pixels
    soft = np.asarray(Image.fromarray((glass * 255).astype(np.uint8)).resize((w, h)), np.float32) / 255.0
    mix = np.clip(1.0 - soft, 0, 1)[..., None]
    outrgb = rgb * (1 - mix) + new * mix
    out = np.concatenate([outrgb, alpha[..., None]], -1)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, out_name + ".webp"), quality=92, method=6)
    m2 = dict(meta)
    m2["src"] = out_name + ".webp"
    json.dump(m2, open(os.path.join(OUT, out_name + ".json"), "w"))
    print("  ", out_name)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for c in RAMPS:
        grade("soul_col_silver", c, "soul_col_" + c)
    grade("soul_front", "silver", "soul_front_silver")
    grade("soul_front", "graphite", "soul_front_graphite")
    grade("soul_front", "ember", "soul_front_ember")
