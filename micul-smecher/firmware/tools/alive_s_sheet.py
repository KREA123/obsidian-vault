#!/usr/bin/env python3
"""SOUL S, the core screens: the simulator's stills -> PNGs + the S-vs-M sheet at true size in the hand.

    .pio/build/sim/program /tmp/as alive-s               # sim/sim_screens.cpp: s-NN-name.ppm, m-NN-name.ppm
    python3 tools/alive_s_sheet.py /tmp/as sim/shots/alive-s

Writes <out>/s-NN-name.png (SOUL S, the 466 px AMOLED-1.75, pixel for pixel) and <out>/s-vs-m-true-size.png:
each state on S (left) and on M (right), both drawn at the same pixels per millimetre, so the sheet shows how big
each screen is in the hand (S: the Ø43.76 mm lit disc; M: Ø70.13 mm). Lit discs from firmware Geometry.h.
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
BG = (11, 11, 13)
MM_S, MM_M = 43.76, 70.13
PX_PER_MM = 7.0  # the sheet's scale


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
    s_files = sorted(glob.glob(os.path.join(a.src, "s-*.ppm")))
    for f in s_files:
        Image.open(f).save(os.path.join(a.out, os.path.basename(f)[:-4] + ".png"), optimize=True)
    ds, dm = round(MM_S * PX_PER_MM), round(MM_M * PX_PER_MM)
    pad, label = 28, 34
    rowh = dm + label + pad
    W = pad + ds + pad + dm + pad
    sheet = Image.new("RGB", (W, 90 + rowh * len(s_files)), BG)
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 24), "SOUL S (1.75\" AMOLED) vs SOUL M (2.8\" IPS), true size", fill=(251, 244, 227), font=font(24))
    dr.text((pad, 58), f"both at {PX_PER_MM:g} px/mm · S Ø{MM_S} mm lit · M Ø{MM_M} mm lit · SoulOS Alive density layer (Density.h)",
            fill=(160, 160, 168), font=font(18))
    y = 90
    for f in s_files:
        name = os.path.basename(f)[2:-4]
        m = os.path.join(a.src, "m-" + name + ".ppm")
        dr.text((pad, y + 4), "S · " + name[3:], fill=(201, 242, 228), font=font(20))
        dr.text((pad + ds + pad, y + 4), "M", fill=(159, 198, 255), font=font(20))
        sheet.paste(disc(Image.open(f), ds), (pad, y + label + (dm - ds) // 2))
        if os.path.exists(m):
            sheet.paste(disc(Image.open(m), dm), (pad + ds + pad, y + label))
        y += rowh
    sheet.save(os.path.join(a.out, "s-vs-m-true-size.png"), optimize=True)
    print(f"{len(s_files)} S stills + the sheet -> {a.out}")


if __name__ == "__main__":
    main()
