#!/usr/bin/env python3
"""screens.py -- screen textures for the SOUL v2 renders (1.75" AMOLED, 466 x 466, round).

* eyes_*.png  : the v1 eye renderer (../../src/eyes.py, a port of firmware Face.cpp drawEye),
                rendered at 1024 px for the texture (same proportions on any panel size).
* ui_*.png    : OS screens drawn with PIL at the real panel resolution (466 x 466, black outside
                the circle) and saved both as-is (ui_*_466.png) and upscaled 2x for the texture.

Font: Fredoka (OFL, fonts/Fredoka-Variable.ttf); Romanian letters without a precomposed glyph
(ă) are shaped as base letter + combining breve (needs Pillow with libraqm), fallback DejaVu Sans Bold.

    python3 screens.py [outdir]          (default: ./tex)
"""
import math
import os
import sys
import unicodedata

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'src')))   # v1 pipeline
import eyes as E  # noqa: E402

FREDOKA = os.path.join(HERE, 'fonts', 'Fredoka-Variable.ttf')
DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
PX = 466
CREAM = (255, 240, 200)
MINT = (201, 242, 228)
MINT_DEEP = (120, 222, 186)
AMBER = (255, 179, 71)
MUTED = (150, 146, 136)


def font(size, weight='SemiBold'):
    try:
        f = ImageFont.truetype(FREDOKA, size, layout_engine=ImageFont.Layout.RAQM
                               if features.check('raqm') else ImageFont.Layout.BASIC)
        f.set_variation_by_name(weight)
        return f, True
    except Exception:
        return ImageFont.truetype(DEJAVU, size), False


def text(d, xy, s, size, fill, weight='SemiBold', anchor='mm', spacing=0):
    f, fredoka = font(size, weight)
    if fredoka and features.check('raqm'):
        s = unicodedata.normalize('NFD', s)   # ă -> a + U+0306 (Fredoka has the mark, not ă)
    if spacing:
        # letter-spaced small caps label
        w = sum(d.textlength(c, font=f) for c in s) + spacing * (len(s) - 1)
        x = xy[0] - w / 2
        for c in s:
            d.text((x, xy[1]), c, font=f, fill=fill, anchor='lm')
            x += d.textlength(c, font=f) + spacing
        return
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def check(d, cx, cy, r, col, w):
    pts = [(cx - 0.45 * r, cy + 0.02 * r), (cx - 0.12 * r, cy + 0.34 * r), (cx + 0.48 * r, cy - 0.32 * r)]
    d.line(pts, fill=col, width=w, joint='curve')
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=col)


def mini_eyes(img, cx, cy, s, col):
    """Tiny version of the signature eyes (status 'face' at the top of the card)."""
    sub = E.N
    E.N = 256
    try:
        e = E.render(color='#%02X%02X%02X' % col, gx=0.2, gy=-0.2)
    finally:
        E.N = sub
    e = Image.fromarray((np.clip(e, 0, 1) * 255).astype(np.uint8)).resize((s, s), Image.LANCZOS)
    img.paste(e, (int(cx - s / 2), int(cy - s / 2)), Image.fromarray(np.array(e).max(-1)))


def ui_reminder(done=True, ss=4):
    """Round card: '17:00 · Sună la bancă ✓' in cream on black, mint progress ring."""
    S = PX * ss
    img = Image.new('RGB', (S, S), (0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    # progress ring: dim track + mint arc (4 of 5 tasks today), round caps
    rr, w = S / 2 - 16 * ss, 13 * ss
    d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=(34, 38, 37), width=w)
    a0, a1 = -90, -90 + 360 * 0.8
    glow = Image.new('RGB', (S, S), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.arc([c - rr, c - rr, c + rr, c + rr], a0, a1, fill=MINT_DEEP, width=w + 10 * ss)
    glow = glow.filter(ImageFilter.GaussianBlur(9 * ss))
    img = Image.fromarray(np.maximum(np.array(img), (np.array(glow) * 0.45).astype(np.uint8)))
    d = ImageDraw.Draw(img)
    d.arc([c - rr, c - rr, c + rr, c + rr], a0, a1, fill=MINT, width=w)
    for a in (a0, a1):
        x, y = c + (rr - w / 2) * math.cos(math.radians(a)), c + (rr - w / 2) * math.sin(math.radians(a))
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=MINT)
    # content
    mini_eyes(img, c, c - 122 * ss, 118 * ss, CREAM)
    d = ImageDraw.Draw(img)
    text(d, (c, c - 62 * ss), 'MEMENTO · 4/5 AZI', 17 * ss, MUTED, 'Medium', spacing=2 * ss)
    text(d, (c, c + 0 * ss), '17:00', 92 * ss, CREAM, 'SemiBold')
    text(d, (c, c + 70 * ss), 'Sună la bancă', 38 * ss, CREAM, 'Medium')
    # done pill with a check mark
    pw, ph = 118 * ss, 44 * ss
    py = c + 128 * ss
    col = MINT if done else (60, 60, 58)
    d.rounded_rectangle([c - pw / 2, py - ph / 2, c + pw / 2, py + ph / 2], radius=ph / 2, fill=col)
    check(d, c - 30 * ss, py, 17 * ss, (18, 22, 20), 5 * ss)
    text(d, (c + 14 * ss, py + 1 * ss), 'gata', 25 * ss, (18, 22, 20), 'SemiBold')
    # round panel mask
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).ellipse([0, 0, S - 1, S - 1], fill=255)
    img = Image.composite(img, Image.new('RGB', (S, S)), m)
    return img.resize((PX, PX), Image.LANCZOS)


def save_eyes(out):
    variants = dict(E.VARIANTS)
    variants.update({
        'cream_front': dict(color='#FFF0C8', gx=0.1, gy=-0.1),
        'cream_side': dict(color='#FFF0C8', gx=-0.45, gy=-0.15),
        'amber_sleepy': dict(color='#FFC96B', lid_top=0.34, gy=0.2, extra_glow=0.25),
        'mint_up': dict(color='#D2FFE6', gx=0.2, gy=-0.6, lid_top=0.12),
        'peach_look': dict(color='#FFDCC8', gx=-0.3, gy=-0.3),
        'ice_look': dict(color='#D8F0FF', gx=0.3, gy=-0.2),
        'lilac_look': dict(color='#E6DAFF', gx=0.35, gy=-0.25),
        'gold_look': dict(color='#FFD76B', gx=-0.1, gy=-0.3),
    })
    for name, kw in variants.items():
        img = E.render(**kw)
        Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
            os.path.join(out, 'eyes_%s.png' % name))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex')
    os.makedirs(out, exist_ok=True)
    save_eyes(out)
    for name, im in (('reminder', ui_reminder(True)), ('reminder_todo', ui_reminder(False))):
        im.save(os.path.join(out, 'ui_%s_466.png' % name))
        im.resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, 'ui_%s.png' % name))
        print('wrote ui_%s' % name)
    print('font: %s' % ('Fredoka' if font(20)[1] else 'DejaVu Sans Bold'))


if __name__ == '__main__':
    main()
