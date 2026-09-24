#!/usr/bin/env python3
"""engrave.py -- mask texture for the engraved steel caseback (Ø40 mm disc).

White = engraved (cut) area. The texture spans the full disc: 0..N px = -20..+20 mm.
  * the serial ring  "SOUL · No. 0001 · born 24.09.2026"  on the top arc (reads clockwise)
  * two fine circles framing the text band
Run:  python3 engrave.py [outdir]    -> tex/caseback_engrave.png
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

N = 4096
R_MM = 20.0
TEXT = 'SOUL  ·  No. 0001  ·  born 24.09.2026'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def px(mm):
    return mm / (2 * R_MM) * N


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
    os.makedirs(out, exist_ok=True)
    im = Image.new('L', (N, N), 0)
    d = ImageDraw.Draw(im)
    c = N / 2
    lw = max(2, int(px(0.09)))
    for r in (16.0, 19.35):
        d.ellipse([c - px(r), c - px(r), c + px(r), c + px(r)], outline=255, width=lw)
    cap = 1.45                                    # cap height in mm
    font = ImageFont.truetype(FONT, int(px(cap) / 0.73))
    r_base = 17.05                                # baseline radius (letters stand outward)
    track = 0.32                                  # extra letter spacing, mm
    widths = [font.getlength(ch) / N * 2 * R_MM + track for ch in TEXT]
    total = sum(widths) - track
    ang = math.pi / 2 + (total / 2) / r_base     # start angle (left end of the top arc)
    for ch, w in zip(TEXT, widths):
        a_mid = ang - (w - track) / 2 / r_base
        if ch.strip():
            gw, gh = int(font.getlength(ch)) + 8, int(font.size * 1.3)
            g = Image.new('L', (gw, gh), 0)
            ImageDraw.Draw(g).text((4, 0), ch, font=font, fill=255)
            rot = math.degrees(a_mid - math.pi / 2)
            g = g.rotate(rot, resample=Image.BICUBIC, expand=True)
            asc = font.getmetrics()[0]
            rr = r_base + (asc * 0.5) / N * 2 * R_MM * 0.95
            x = c + px(rr) * math.cos(a_mid)
            y = c - px(rr) * math.sin(a_mid)
            im.paste(255, (int(x - g.width / 2), int(y - g.height / 2)), g)
        ang -= w / r_base
    im.save(os.path.join(out, 'caseback_engrave.png'))
    print('wrote caseback_engrave.png')


if __name__ == '__main__':
    main()
