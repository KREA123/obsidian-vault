#!/usr/bin/env python3
"""compose_v10.py -- post step for v10 (no rendering):
    python3 compose_v10.py vs      ../soul_v10_vs_m.png -> labelled in place (S and M under each, one camera, one scale)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_L = '/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf'


def vs(src, xs=0.367, xm=0.634):          # body centres in the vs_az = 0 frame (render_v10.sh)
    a = Image.open(src).convert('RGB')
    if a.size[1] > a.size[0] * 9 // 16 + 2:          # already labelled: relabel from the untouched render on top
        a = a.crop((0, 0, a.size[0], a.size[0] * 9 // 16))
    W, H = a.size
    bot = 200
    im = Image.new('RGB', (W, H + bot), (236, 230, 222))
    im.paste(a, (0, 0))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT, 40)
    f2 = ImageFont.truetype(FONT, 25)
    f3 = ImageFont.truetype(FONT_L, 21)
    col = (60, 56, 52)
    for x, t1, t2, t3 in ((xs * W, 'S · produsul final', '63,0 × 70,8 × 23,0 mm', 'sticlă Ø52 · 1,75″ AMOLED'),
                          (xm * W, 'M · prototipul', '90 × 101 × 31,5 mm', 'sticlă Ø74,3 · 2,8″ IPS')):
        for txt, fnt, y in ((t1, f1, H + 24), (t2, f2, H + 80), (t3, f2, H + 114)):
            tw = d.textlength(txt, font=fnt)
            d.text((x - tw / 2, y), txt, font=fnt, fill=col)
    note = 'randare / concept (CGI) · aceeași cameră, aceeași scară'
    d.text((W - d.textlength(note, font=f3) - 24, H + bot - 34), note, font=f3, fill=(120, 114, 108))
    im.save(src, optimize=True)
    print('wrote', src, im.size, os.path.getsize(src) // 1000, 'kB')


if __name__ == '__main__':
    if sys.argv[1] == 'vs':
        vs(sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, 'soul_v10_vs_m.png'))
