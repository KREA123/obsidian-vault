#!/usr/bin/env python3
"""textures_v5.py -- printed / engraved textures of the v5 renders (system Python + Pillow).

    python3 textures_v5.py [outdir]      (default: ./tex)

sole_engrave.png   plan-view mask of the sole engraving (as seen from BELOW, flipped for Blender's v axis):
                   outer ring r 10.5 (1.0 mm caps), inner ring r 8.3 (0.6 mm caps), CE (5 mm) at (+16,-4),
                   crossed-bin WEEE at (-16,-4). 60 x 60 mm, 50 px/mm. White = engraved.
box_back.png       sleeve back panel 118 x 150 mm (legal block 60 x 40 mm at 6 pt, CE, bin, QR placeholder).
box_front.png      sleeve front mask 118 x 150 mm: white = hot-foil eye ovals.
box_spine.png      sleeve spine 78 x 150 mm, "SOUL" reading bottom-to-top.
seal.png           paper seal 30 x 12 mm "Nº 00417".
card_nudge.png     cream card 70 x 100 mm, the two lines of 09 §5.
Real text only; the manufacturer's name/address/e-mail are not decided yet and stay as [placeholders].
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex')
FONT_XL = '/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_C = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'
FONT_CB = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'


def font(path, px):
    return ImageFont.truetype(path, max(4, int(round(px))))


# ------------------------------------------------------------------------------------------
# symbols
def draw_ce(d, cx, cy, h, col, lw):
    """CE mark, h = height in px: two identical open circle arcs; the E adds its middle stroke."""
    r = h / 2.0
    for ox, is_e in ((-0.56 * h, False), (0.56 * h, True)):
        x0 = cx + ox
        bb = [x0 - r + lw / 2, cy - r + lw / 2, x0 + r - lw / 2, cy + r - lw / 2]
        d.arc(bb, 45, 315, fill=col, width=int(lw))
        if is_e:
            d.line([(x0 - r + lw, cy), (x0 + r * 0.62, cy)], fill=col, width=int(lw))


def draw_bin(d, cx, cy, h, col, lw):
    """Crossed-out wheelie bin (WEEE), h = total height in px incl. the bar below."""
    w = h * 0.62
    top = cy - h * 0.46
    bot = cy + h * 0.30
    # lid
    d.line([(cx - w * 0.55, top), (cx + w * 0.55, top)], fill=col, width=int(lw))
    d.line([(cx - w * 0.12, top - h * 0.06), (cx + w * 0.12, top - h * 0.06)], fill=col, width=int(lw))
    # body (tapered)
    d.line([(cx - w * 0.45, top + lw), (cx - w * 0.36, bot)], fill=col, width=int(lw))
    d.line([(cx + w * 0.45, top + lw), (cx + w * 0.36, bot)], fill=col, width=int(lw))
    d.line([(cx - w * 0.36, bot), (cx + w * 0.36, bot)], fill=col, width=int(lw))
    # wheel
    rr = h * 0.06
    d.ellipse([cx + w * 0.28 - rr, bot - rr, cx + w * 0.28 + rr, bot + rr], outline=col, width=int(lw))
    # cross
    d.line([(cx - w * 0.62, top - h * 0.10), (cx + w * 0.62, bot + h * 0.08)], fill=col, width=int(lw))
    d.line([(cx + w * 0.62, top - h * 0.10), (cx - w * 0.62, bot + h * 0.08)], fill=col, width=int(lw))
    # solid bar below
    d.rectangle([cx - w * 0.55, cy + h * 0.40, cx + w * 0.55, cy + h * 0.50], fill=col)


def draw_qr_placeholder(d, x0, y0, size, col, seed=417, bg=(241, 233, 218)):
    """A QR-like placeholder (21 x 21 modules, finder patterns). Not a real code: it is a render prop."""
    n = 21
    m = size / n
    rng = np.random.default_rng(seed)
    grid = rng.random((n, n)) > 0.52
    for (fx, fy) in ((0, 0), (n - 7, 0), (0, n - 7)):
        grid[fy:fy + 7, fx:fx + 7] = False
        grid[fy:fy + 8 if fy == 0 else fy + 7, fx:fx + 8 if fx == 0 else fx + 7] = False
    for j in range(n):
        for i in range(n):
            if grid[j, i]:
                d.rectangle([x0 + i * m, y0 + j * m, x0 + (i + 1) * m - 1, y0 + (j + 1) * m - 1], fill=col)
    for (fx, fy) in ((0, 0), (n - 7, 0), (0, n - 7)):
        X, Y = x0 + fx * m, y0 + fy * m
        d.rectangle([X, Y, X + 7 * m - 1, Y + 7 * m - 1], fill=col)
        d.rectangle([X + m, Y + m, X + 6 * m - 1, Y + 6 * m - 1], fill=bg)
        d.rectangle([X + 2 * m, Y + 2 * m, X + 5 * m - 1, Y + 5 * m - 1], fill=col)


# ------------------------------------------------------------------------------------------
def ring_text(img, text, cx, cy, r, cap_px, fpath, start_deg=-90.0, clockwise=True, fill=255):
    """Text along a circle, letters upright pointing away from the centre, reading clockwise (as on a coin)."""
    f = font(fpath, cap_px / 0.73)          # DejaVu cap height ~ 0.73 em
    widths = [f.getlength(ch) for ch in text]
    total = sum(widths) + 0.0
    ang_total = total / r
    a = math.radians(start_deg) - ang_total / 2 if clockwise else math.radians(start_deg) + ang_total / 2
    for ch, wch in zip(text, widths):
        am = a + (wch / 2) / r * (1 if clockwise else -1)
        if ch != ' ':
            size = int(f.size * 2.8) + 6
            tile = Image.new('L', (size, size), 0)
            td = ImageDraw.Draw(tile)
            td.text((size / 2, size / 2), ch, font=f, fill=fill, anchor='ms')
            # rotate so the letter's up points outward: angle of the radius + 90
            rot = -math.degrees(am) - 90 if clockwise else -math.degrees(am) + 90
            tile = tile.rotate(rot, resample=Image.BICUBIC, center=(size / 2, size / 2))
            px = cx + r * math.cos(am)
            py = cy + r * math.sin(am)
            img.paste(255, (int(px - size / 2), int(py - size / 2)), tile)
        a += wch / r * (1 if clockwise else -1)


def sole_engrave(path):
    S = 50.0          # px per mm
    N = int(60 * S)
    img = Image.new('L', (N, N), 0)
    d = ImageDraw.Draw(img)
    c = N / 2.0

    def P(x, y):      # plan mm -> canvas px, canvas = the sole as seen from below (x right, +y (back) down)
        return c + x * S, c + y * S
    cx, cy = P(0, 0)
    ring_text(img, 'SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA', cx, cy, 10.5 * S, 1.0 * S, FONT_XL,
              start_deg=-90)
    ring_text(img, 'SOUL S1 · SN 26-00417 · [PRODUCĂTOR] SRL · [STRADĂ, ORAȘ] RO · [E-MAIL] · Li-ion',
              cx, cy, 8.3 * S, 0.6 * S, FONT, start_deg=-90)
    ce = P(16, -4)
    draw_ce(d, ce[0], ce[1], 5.0 * S * 0.62, 255, 0.28 * S)
    bn = P(-16, -4)
    draw_bin(d, bn[0], bn[1], 5.0 * S, 255, 0.22 * S)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)      # Blender's v runs up = plan +y
    img.save(path)


# ------------------------------------------------------------------------------------------
BOX_W, BOX_D, BOX_H = 118.0, 78.0, 150.0
INK = (34, 30, 26)


def box_back(path):
    S = 20.0
    W, H = int(BOX_W * S), int(BOX_H * S)
    img = Image.new('RGB', (W, H), (241, 233, 218))
    d = ImageDraw.Draw(img)
    # top: small wordmark + the one line
    d.text((W / 2, 22 * S), 'SOUL', font=font(FONT_XL, 11 * S), fill=INK, anchor='mm')
    d.text((W / 2, 33 * S), 'un suflet mic care trăiește cu tine', font=font(FONT_XL, 3.6 * S), fill=INK,
           anchor='mm')
    d.text((W / 2, 40 * S), 'Ridică-l: se uită.  Ține-l: te ascultă.  Închide oul: doarme.',
           font=font(FONT_XL, 2.9 * S), fill=INK, anchor='mm')
    # contents line
    d.text((W / 2, 52 * S), 'În cutie: SOUL · OU (capsula) · COCON (husă tricotată) · cablu USB-C · certificat · ghid RO/EN',
           font=font(FONT_XL, 2.3 * S), fill=INK, anchor='mm')
    # legal block 60 x 40 mm at 6 pt (line pitch 2.6 mm, cap ~1.5 mm)
    bx, by = (BOX_W - 60) / 2 * S, 84 * S
    d.rectangle([bx - 2 * S, by - 2 * S, bx + 62 * S, by + 42 * S], outline=INK, width=int(0.18 * S))
    pt6 = 6 * 0.3528 * S          # 6 pt in px (em size)
    fL = font(FONT_C, pt6)
    fB = font(FONT_CB, pt6)
    lines = [
        ('b', 'SOUL S1 · companion AI · Nº 00417 · lot 26-09'),
        ('b', 'Companion AI · vorbești cu o inteligență artificială,'),
        ('b', 'nu cu un om.'),
        ('b', 'Nu este o jucărie · 14+'),
        ('', 'Nu este destinat copiilor sub 14 ani. Conține magneți.'),
        ('', 'Contul AI (Claude sau ChatGPT, opțional): 18+.'),
        ('', 'Baterie Li-ion 3,7 V · ≈ 1000 mAh · ≈ 3,7 Wh,'),
        ('', 'înlocuibilă de utilizator (4 × Torx T5).'),
        ('', 'Proiectat în România · Fabricat în China.'),
        ('', 'Producător: [denumire] SRL · [stradă, nr., oraș], România'),
        ('', '[e-mail] · garanție 2 ani · reclamații: [e-mail]'),
        ('', 'Declarația UE de conformitate și ghidul RO/EN: codul QR.'),
    ]
    y = by + 1.2 * S
    for kind, t in lines:
        d.text((bx, y), t, font=fB if kind == 'b' else fL, fill=INK, anchor='la')
        y += 2.5 * S
    # symbols row
    sy = by + 36.3 * S
    draw_ce(d, bx + 5 * S, sy, 5.0 * S, INK, 0.45 * S)
    draw_bin(d, bx + 17 * S, sy, 6.0 * S, INK, 0.25 * S)
    d.text((bx + 23 * S, sy), 'Li-ion', font=font(FONT_C, 2.4 * S), fill=INK, anchor='lm')
    draw_qr_placeholder(d, bx + 52 * S, sy - 3.6 * S, 7.6 * S, INK)
    # batch/serial label bottom right
    d.rectangle([BOX_W * S - 44 * S, H - 14 * S, BOX_W * S - 8 * S, H - 6 * S], outline=INK, width=int(0.15 * S))
    d.text((BOX_W * S - 26 * S, H - 10 * S), 'SN 26-00417  ·  PERLĂ', font=font(FONT_C, 2.2 * S), fill=INK,
           anchor='mm')
    img.save(path)


def box_front(path):
    """Mask: white where the hot-foil eye ovals are. Eye pair spans ~40 % of the front width."""
    S = 10.0
    W, H = int(BOX_W * S), int(BOX_H * S)
    sys.path.insert(0, HERE)
    import eyes as E
    ey = E.render(color='#FFFFFF', gx=0.0, gy=-0.05, lid_top=0.19, lid_tilt=0.16, glow=0.0)
    m = np.clip(ey[..., 0], 0, 1)
    m = (m > 0.5).astype(np.uint8) * 255
    tile = Image.fromarray(m)
    bb = tile.getbbox()
    tile = tile.crop(bb)
    tw = int(0.40 * BOX_W * S)
    th = int(tile.size[1] * tw / tile.size[0])
    tile = tile.resize((tw, th), Image.LANCZOS)
    img = Image.new('L', (W, H), 0)
    img.paste(tile, ((W - tw) // 2, int(0.40 * H - th / 2)))
    img.save(path)


def box_spine(path):
    S = 12.0
    W, H = int(BOX_D * S), int(BOX_H * S)
    img = Image.new('RGB', (H, W), (241, 233, 218))       # drawn horizontally, rotated below
    d = ImageDraw.Draw(img)
    d.text((H / 2, W / 2), 'S O U L', font=font(FONT_XL, 16 * S), fill=INK, anchor='mm')
    img = img.rotate(90, expand=True)
    img.save(path)


def seal(path):
    S = 40.0
    W, H = int(30 * S), int(12 * S)
    img = Image.new('RGB', (W, H), (250, 246, 238))
    d = ImageDraw.Draw(img)
    d.rectangle([0.8 * S, 0.8 * S, W - 0.8 * S, H - 0.8 * S], outline=(170, 70, 40), width=int(0.15 * S))
    d.text((W / 2, H / 2), 'Nº 00417', font=font(FONT_XL, 6.0 * S), fill=(120, 48, 28), anchor='mm')
    img.save(path)


def card(path, lines):
    S = 16.0
    W, H = int(70 * S), int(100 * S)
    img = Image.new('RGB', (W, H), (246, 239, 226))
    d = ImageDraw.Draw(img)
    y = 44 * S
    for t, sz in lines:
        d.text((W / 2, y), t, font=font(FONT_XL, sz * S), fill=INK, anchor='mm')
        y += sz * S * 1.7
    d.text((W / 2, H - 9 * S), 'SOUL', font=font(FONT_XL, 3.2 * S), fill=INK, anchor='mm')
    img.save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    sole_engrave(os.path.join(OUT, 'sole_engrave.png'))
    box_back(os.path.join(OUT, 'box_back.png'))
    box_front(os.path.join(OUT, 'box_front.png'))
    box_spine(os.path.join(OUT, 'box_spine.png'))
    seal(os.path.join(OUT, 'seal.png'))
    card(os.path.join(OUT, 'card_nudge.png'), [('Împinge-l ușor.', 6.0), ('Nudge it.', 4.2)])
    card(os.path.join(OUT, 'card_ritual.png'), [('Ridică-l: se uită.', 4.4), ('Ține-l: te ascultă.', 4.4),
                                                ('Închide oul: doarme.', 4.4)])
    print('textures written to', OUT)


if __name__ == '__main__':
    main()
