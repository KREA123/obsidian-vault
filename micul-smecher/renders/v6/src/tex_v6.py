#!/usr/bin/env python3
"""tex_v6.py -- v6 textures (system Python + Pillow). CGI concept.

    python3 tex_v6.py [outdir]        (default: ./tex)

sole_engrave.png   plan-view laser-marking mask of the v6 flat base (as seen from BELOW, flipped for Blender's v),
                   same convention as v5 (60 x 60 mm, 50 px/mm, white = marked):
                   front strip of the polymer base plate (y -9.6 / -11.1): "SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA"
                   and the small legal line; back strip (y +9.4): CE and the crossed-bin symbol.
                   The foot (30 x 14 oval) carries only the contacts and the two Torx heads.
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'v5', 'src'))
import textures_v5 as T5  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex')


def sole_engrave(path):
    S = 50.0
    N = int(60 * S)
    img = Image.new('L', (N, N), 0)
    d = ImageDraw.Draw(img)
    c = N / 2.0

    def P(x, y):      # plan mm -> canvas px (the base seen from below: x right, +y (back) down)
        return c + x * S, c + y * S
    x, y = P(0, -9.7)
    d.text((x, y), 'SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA', font=T5.font(T5.FONT_XL, 1.05 * S), fill=255,
           anchor='mm')
    x, y = P(0, -11.35)
    d.text((x, y), 'SOUL S1 · SN 26-00417 · [PRODUCĂTOR] SRL · RO · Li-ion', font=T5.font(T5.FONT, 0.62 * S),
           fill=255, anchor='mm')
    ce = P(3.4, 9.3)
    T5.draw_ce(d, ce[0], ce[1], 2.6 * S * 0.62, 255, 0.16 * S)
    bn = P(-3.4, 9.3)
    T5.draw_bin(d, bn[0], bn[1], 2.8 * S, 255, 0.13 * S)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img.save(path)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    sole_engrave(os.path.join(OUT, 'sole_engrave.png'))
    print('wrote', os.path.join(OUT, 'sole_engrave.png'))
