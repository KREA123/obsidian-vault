#!/usr/bin/env python3
"""SOUL S, every SoulOS Alive screen: the simulator's stills -> PNGs + the S-next-to-M sheet at true size in the hand.

    .pio/build/sim/program /tmp/as alive-s               # sim/sim_screens.cpp: s-NN-name.ppm, m-NN-name.ppm
    python3 tools/alive_s_sheet.py /tmp/as sim/shots/alive-s

Writes <out>/s-NN-name.png (SOUL S, the 466 px AMOLED-1.75, pixel for pixel: every state of sim/alive_states.h,
the same ones the round audit checks on both glasses) and <out>/soulos-alive-S-sheet.png: each state on S (left of
the pair) next to M (right), both drawn at the same pixels per millimetre, so the sheet shows how big each screen
is in the hand (S: the Ø43.76 mm lit disc; M: Ø70.13 mm). Lit discs from firmware Geometry.h.
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
BG = (11, 11, 13)
MM_S, MM_M = 43.76, 70.13
PX_PER_MM = 5.0  # the sheet's scale
COLS = 3         # pairs per row


def font(size):
    try:
        f = ImageFont.truetype(os.path.join(FONTS, "BricolageGrotesque-VF.ttf"), size)
        try:
            f.set_variation_by_axes([24, 100, 600])
        except Exception:
            pass
        return f
    except OSError:
        return ImageFont.load_default()


def disc(img, d):
    img = img.convert("RGB").resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    out = Image.new("RGB", (d, d), BG)
    out.paste(img, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((0, 0, d - 1, d - 1), outline=(60, 60, 66), width=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for old in glob.glob(os.path.join(a.out, "s-*.png")):  # (the numbering follows sim/alive_states.h)
        os.remove(old)
    s_files = sorted(glob.glob(os.path.join(a.src, "s-*.ppm")))
    for f in s_files:
        Image.open(f).save(os.path.join(a.out, os.path.basename(f)[:-4] + ".png"), optimize=True)
    ds, dm = round(MM_S * PX_PER_MM), round(MM_M * PX_PER_MM)
    pad, label, gap = 22, 30, 14
    cellw = ds + gap + dm
    cellh = label + dm + pad
    rows = (len(s_files) + COLS - 1) // COLS
    W = pad + COLS * (cellw + pad)
    top = 96
    sheet = Image.new("RGB", (W, top + rows * cellh), BG)
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 22), f"SoulOS Alive on SOUL S (1.75\" AMOLED, left) next to SOUL M (2.8\" IPS, right): {len(s_files)} screens, true size",
            fill=(251, 244, 227), font=font(26))
    dr.text((pad, 60), f"both at {PX_PER_MM:g} px/mm · S Ø{MM_S} mm lit, 466 px · M Ø{MM_M} mm lit, 480 px · the density layer "
            "(Density.h) and the S screens (firmware/SOUL-S.md §5) · the round audit passes on both", fill=(160, 160, 168), font=font(18))
    for i, f in enumerate(s_files):
        name = os.path.basename(f)[2:-4]
        m = os.path.join(a.src, "m-" + name + ".ppm")
        x = pad + (i % COLS) * (cellw + pad)
        y = top + (i // COLS) * cellh
        dr.text((x, y + 2), name.replace("-", " ", 1), fill=(201, 242, 228), font=font(19))
        sheet.paste(disc(Image.open(f), ds), (x, y + label + (dm - ds) // 2))
        if os.path.exists(m):
            sheet.paste(disc(Image.open(m), dm), (x + ds + gap, y + label))
    sheet.save(os.path.join(a.out, "soulos-alive-S-sheet.png"), optimize=True)
    print(f"{len(s_files)} S stills + the sheet -> {a.out}")


if __name__ == "__main__":
    main()
