#!/usr/bin/env python3
"""SoulOS Alive, every screen: the simulator's stills -> PNGs + the device-vs-web sheet.

    .pio/build/sim/program /tmp/scr screens                    # sim/sim_screens.cpp: NN-name.ppm + shots.txt
    node ../os/tests/alive-audit.mjs /tmp/web                  # the web prototype's stills (the same states)
    python3 tools/alive_sheet.py /tmp/scr sim/shots/alive --web /tmp/web

Writes <out>/screen-NN-name.png (one per state) and <out>/soulos-alive-device-vs-web.png: every state the web
audit has, the device's pixels on the left and the web prototype's on the right, then the screens only the
device has. Both are shown inside the round glass (the web stills' page background outside the circle is masked).
"""
import argparse
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
BG = (11, 11, 13)


def font(size, bold=False):
    path = os.path.join(FONTS, "BricolageGrotesque-VF.ttf")
    try:
        f = ImageFont.truetype(path, size)
        try:
            f.set_variation_by_axes([96 if bold else 24, 100, 700 if bold else 500])  # opsz, wdth, wght
        except Exception:
            pass
        return f
    except OSError:
        return ImageFont.load_default()


def disc(img, d):
    """img scaled to d x d inside a circle on the sheet's background, with a hairline rim."""
    img = img.convert("RGB").resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    mask = mask.resize((d, d), Image.LANCZOS)
    out = Image.new("RGB", (d, d), BG)
    out.paste(img, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((0, 0, d - 1, d - 1), outline=(46, 46, 52), width=2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--web", default="", help="the web audit's stills (node os/tests/alive-audit.mjs <dir>)")
    ap.add_argument("--title", default="SoulOS Alive: the device vs the web prototype, screen by screen")
    a = ap.parse_args()
    man = os.path.join(a.src, "shots.txt")
    if not os.path.exists(man):
        sys.exit("no shots.txt in " + a.src)
    rows = []
    for line in open(man, encoding="utf-8"):
        p = line.split()
        if len(p) >= 3:
            rows.append((p[0], p[1], p[2] if len(p) > 2 else ""))
    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "screen-[0-9][0-9]-*.png")):
        os.remove(f)
    for key, _, _ in rows:
        Image.open(os.path.join(a.src, key + ".ppm")).convert("RGB").save(os.path.join(a.out, "screen-" + key + ".png"), optimize=True)

    pairs = [(k, w) for k, w, _ in rows if w != "-"]
    solo = [k for k, w, _ in rows if w == "-"]
    D, GAP, PAD, LBL = 300, 14, 40, 34
    pair_w = 2 * D + GAP
    cols = 3
    solo_cols = 6
    rows_p = (len(pairs) + cols - 1) // cols
    rows_s = (len(solo) + solo_cols - 1) // solo_cols
    W = PAD * 2 + cols * pair_w + (cols - 1) * 56
    sd = (W - 2 * PAD - (solo_cols - 1) * 24) // solo_cols
    H = 150 + rows_p * (D + LBL + 30) + 90 + rows_s * (sd + LBL + 24) + PAD
    sheet = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD, 34), a.title, font=font(46, True), fill=(251, 244, 227))
    dr.text((PAD, 94), "Left: the firmware's own pixels (simulator, 480 px). Right: os/index.html (the approved design). "
            "Same states as the round audit; both inside the round glass.", font=font(24), fill=(170, 166, 158))
    y0 = 150
    lf, sf = font(24), font(20)
    for i, (key, web) in enumerate(pairs):
        cx = PAD + (i % cols) * (pair_w + 56)
        cy = y0 + (i // cols) * (D + LBL + 30)
        sheet.paste(disc(Image.open(os.path.join(a.src, key + ".ppm")), D), (cx, cy))
        wf = os.path.join(a.web, web + ".png") if a.web else ""
        if wf and os.path.exists(wf):
            sheet.paste(disc(Image.open(wf), D), (cx + D + GAP, cy))
        else:
            dr.ellipse((cx + D + GAP, cy, cx + 2 * D + GAP - 1, cy + D - 1), outline=(60, 60, 66), width=2)
            dr.text((cx + D + GAP + D // 2, cy + D // 2), "no web still", font=sf, fill=(120, 118, 112), anchor="mm")
        name = key.split("-", 1)[1].replace("-", " ")
        dr.text((cx + pair_w // 2, cy + D + 8), f"{key[:2]}  {name}", font=lf, fill=(230, 226, 216), anchor="ma")
        dr.text((cx + D // 2, cy + D + 8), "device", font=sf, fill=(120, 118, 112), anchor="ma")
        dr.text((cx + D + GAP + D // 2, cy + D + 8), "web", font=sf, fill=(120, 118, 112), anchor="ma")
    y1 = y0 + rows_p * (D + LBL + 30) + 20
    dr.text((PAD, y1), "Only on the device (no web counterpart)", font=font(32, True), fill=(251, 244, 227))
    y1 += 60
    for i, key in enumerate(solo):
        cx = PAD + (i % solo_cols) * (sd + 24)
        cy = y1 + (i // solo_cols) * (sd + LBL + 24)
        sheet.paste(disc(Image.open(os.path.join(a.src, key + ".ppm")), sd), (cx, cy))
        dr.text((cx + sd // 2, cy + sd + 8), f"{key[:2]}  {key.split('-', 1)[1].replace('-', ' ')}", font=sf,
                fill=(230, 226, 216), anchor="ma")
    out = os.path.join(a.out, "soulos-alive-device-vs-web.png")
    sheet.save(out, optimize=True)
    print(len(rows), "stills ->", a.out, "+", os.path.basename(out), sheet.size)


if __name__ == "__main__":
    main()
