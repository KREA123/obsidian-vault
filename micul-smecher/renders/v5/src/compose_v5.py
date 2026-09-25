#!/usr/bin/env python3
"""compose_v5.py -- finishing steps of the v5 renders (system Python: numpy + Pillow).

    python3 compose_v5.py <shot> <tone-mapped.png> <outdir>
        hero          -> soul_v5_hero.png (1600 x 2000) + soul_v5_hero_crop.png (1600 x 1200, same camera)
        check1_*      -> kept next to the input; when all four panels exist -> soul_v5_check1.png (2400 x 1200),
                         with the ember band measured on the render and labelled
        front_00      -> soul_v5_front_00.png + proportions check (printed, written to <outdir>/checks_v5.txt)
        other         -> soul_v5_<shot>.png
    python3 compose_v5.py shadow20 - <outdir>   -> soul_v5_shadow20.png (20 px silhouettes: SOUL, v1 coin, v4 pebble)
"""
import json
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
INK = (92, 84, 74)


def lstar(rgb8):
    c = rgb8.astype(np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Y = 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
    f = np.where(Y > 216 / 24389, np.cbrt(Y), (24389 / 27 * Y + 16) / 116)
    return 116 * f - 16


def log_check(outdir, text):
    """Measurements go to the render temp dir (not into the vault)."""
    print(text)
    d = os.environ.get('TMP_DIR', '/tmp/soul_v5_render')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'checks_v5.txt'), 'a') as f:
        f.write(text + '\n')


# ------------------------------------------------------------------------------------------
def hero(png, outdir):
    im = Image.open(png).convert('RGB')
    W, H = im.size                                   # 2000 x 2000 (same camera for both frames)
    s = W / 2000.0
    im.crop((int(200 * s), 0, int(1800 * s), H)).resize((1600, 2000), Image.LANCZOS).save(
        os.path.join(outdir, 'soul_v5_hero.png'), optimize=True)
    im.crop((0, int(250 * s), W, int(1750 * s))).resize((1600, 1200), Image.LANCZOS).save(
        os.path.join(outdir, 'soul_v5_hero_crop.png'), optimize=True)


# ------------------------------------------------------------------------------------------
def ember_mask(a):
    r, g, b = [a[..., i].astype(float) for i in range(3)]
    return (r > 120) & (r - g > 55) & (g - b > 8) & (r - b > 90)


def measure_band(png, mm_per_px):
    """Vertical extent of the ember (contrast) sole at the centre column and at x = +-20 mm."""
    a = np.asarray(Image.open(png).convert('RGB'))
    m = ember_mask(a)
    H, W = m.shape
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    cx = W // 2
    out = {}
    for lab, dx_mm in (('centre', 0.0), ('x-20', -20.0), ('x+20', 20.0)):
        x = int(round(cx + dx_mm / mm_per_px))
        col = m[:, max(x - 1, 0):x + 2].any(1)
        yy = np.nonzero(col)[0]
        out[lab] = (yy.max() - yy.min() + 1) * mm_per_px if len(yy) else 0.0
    out['width'] = (xs.max() - xs.min() + 1) * mm_per_px
    return out


def check1(png, outdir):
    d = os.path.dirname(png)
    pre = '_preview' if png.endswith('_preview.png') else ''
    panels = [('check1_pearl_0', 'talpă perlă (standard)', 'la nivelul mesei (0°)'),
              ('check1_ember_0', 'talpă ember (accesoriu)', 'la nivelul mesei (0°)'),
              ('check1_pearl_9', 'talpă perlă (standard)', 'cameră la 9°'),
              ('check1_ember_9', 'talpă ember (accesoriu)', 'cameră la 9°')]
    paths = [os.path.join(d, p + pre + '.png') for p, _, _ in panels]
    if not all(os.path.exists(p) for p in paths):
        print('check1: waiting for', [os.path.basename(p) for p in paths if not os.path.exists(p)])
        return
    ims = [Image.open(p).convert('RGB') for p in paths]
    pw, ph = ims[0].size
    board = Image.new('RGB', (pw * 4, ph), (255, 255, 255))
    for i, im in enumerate(ims):
        board.paste(im, (i * pw, 0))
    # scale at the SOUL plane: 590 mm, 140 mm lens, 36 mm sensor across the panel height
    mm_per_px = (590.0 * 36.0 / 140.0) / ph
    dr = ImageDraw.Draw(board)
    f1 = ImageFont.truetype(FONT_R, int(ph * 0.021))
    f2 = ImageFont.truetype(FONT, int(ph * 0.019))
    f3 = ImageFont.truetype(FONT, int(ph * 0.017))
    dr.text((pw * 2, int(ph * 0.03)), 'SOUL · verificarea fondatorului nr. 1 · talpa văzută din față',
            font=ImageFont.truetype(FONT_R, int(ph * 0.024)), fill=INK, anchor='mt')
    res = {}
    for i, ((key, l1, l2), p) in enumerate(zip(panels, paths)):
        x0 = i * pw
        dr.text((x0 + pw / 2, int(ph * 0.075)), l1, font=f1, fill=INK, anchor='mt')
        dr.text((x0 + pw / 2, int(ph * 0.105)), l2, font=f2, fill=INK, anchor='mt')
        if 'ember' in key:
            m = measure_band(p, mm_per_px)
            res[key] = m
            if m:
                t = 'bandă ember măsurată: %.1f mm (centru) · %.1f / %.1f mm (x ±20) · lățime %.0f mm' % (
                    m['centre'], m['x-20'], m['x+20'], m['width'])
            else:
                t = 'bandă ember: nu se vede'
            dr.text((x0 + pw / 2, int(ph * 0.93)), t.split(' · ')[0], font=f3, fill=INK, anchor='mt')
            dr.text((x0 + pw / 2, int(ph * 0.955)), ' · '.join(t.split(' · ')[1:]), font=f3, fill=INK, anchor='mt')
        else:
            dr.text((x0 + pw / 2, int(ph * 0.93)), 'ton pe ton: doar linia de 0,1 mm la 1,7 mm', font=f3, fill=INK,
                    anchor='mt')
        if i:
            dr.line([(x0, int(ph * 0.07)), (x0, int(ph * 0.98))], fill=(200, 192, 182), width=1)
    dr.text((pw * 2, int(ph * 0.985)), 'randare / concept (CGI) · 09 §3.2 estimează 1,7–2,4 mm la nivelul mesei, '
            '0,8–0,9 mm la 9°', font=ImageFont.truetype(FONT, int(ph * 0.014)), fill=INK, anchor='mb')
    out = os.path.join(outdir, 'soul_v5_check1%s.png' % pre)
    board.save(out, optimize=True)
    log_check(outdir, 'check1 ember band (mm): ' + json.dumps({k: {a: round(b, 2) for a, b in v.items()} if v else None
                                                               for k, v in res.items()}))
    print('wrote', out)


# ------------------------------------------------------------------------------------------
def front_props(png, outdir):
    """Proportions on the front render: glass centre / eye line as % of height, glass share of the front, broad end."""
    a = np.asarray(Image.open(png).convert('RGB'))
    L = lstar(a)
    H, W = L.shape
    bg = np.median(np.concatenate([L[:30].ravel(), L[:, :30].ravel(), L[:, -30:].ravel()]))
    # object = everything that differs from the sweep, above the contact shadow line
    diff = np.abs(L - bg) > 7
    # glass = very dark pixels (plus the eyes inside it)
    dark = L < 12
    ys, xs = np.nonzero(dark)
    gy0, gy1, gx0, gx1 = ys.min(), ys.max(), xs.min(), xs.max()
    gcx, gcy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
    rg = ((gx1 - gx0) + (gy1 - gy0)) / 4
    # object silhouette: rows/cols spanned by the body (restrict to the band around the glass columns)
    rows = np.nonzero(diff[:, int(gcx)])[0]
    top = rows.min()
    # bottom: the lowest body row in the centre column above the table contact
    col = diff[:, int(gcx) - 2:int(gcx) + 3].any(1)
    bot = np.nonzero(col)[0].max()
    Hobj = bot - top
    yy, xx = np.mgrid[0:H, 0:W]
    glass_disc = (xx - gcx) ** 2 + (yy - gcy) ** 2 <= rg ** 2
    eyes = (L > 80) & glass_disc
    ey = np.nonzero(eyes)[0].mean()
    obj = np.zeros_like(diff)
    for r in range(top, bot + 1):
        c = np.nonzero(diff[r])[0]
        if len(c):
            obj[r, c.min():c.max() + 1] = True
    glass_share = glass_disc.sum() / obj.sum()

    def width_at(frac):
        r = int(round(bot - frac * Hobj))
        c = np.nonzero(obj[r])[0]
        return c.max() - c.min() + 1
    w25, w75 = width_at(18.5 / 74), width_at(55.5 / 74)
    txt = ('front_00 proportions (px; object %d px tall): glass centre %.1f %% of height (target 54-56), '
           'eye line %.1f %% (target 50-52), glass %.1f %% of the front (target ~52), broad end up %+.1f %% (target ~+5)'
           % (Hobj, 100 * (bot - gcy) / Hobj, 100 * (bot - ey) / Hobj, 100 * glass_share, 100 * (w75 / w25 - 1)))
    g = L[glass_disc & ~(L > 20)]
    txt += '\nfront_00 glass L*: median %.1f, p95 %.1f (outside eyes and glint)' % (np.median(g), np.percentile(g, 95))
    log_check(outdir, txt)


# ------------------------------------------------------------------------------------------
def soul_outline_mm():
    sys.path.insert(0, HERE)
    import soul_geo as SG
    g = SG.SoulGeo(NU=256)
    land = g.land_rows(6)
    sole = g.sole_rows(20)
    fil = g.fillet_rows(6)
    shell = g.shell_rows_tau(200)
    P = np.concatenate([land, sole, fil, shell], 0).reshape(-1, 3)
    zb = np.linspace(0, 74, 297)
    xs = []
    for z0, z1 in zip(zb[:-1], zb[1:]):
        k = (P[:, 2] >= z0) & (P[:, 2] < z1)
        xs.append(np.abs(P[k, 0]).max() if k.any() else 0.0)
    zc = 0.5 * (zb[:-1] + zb[1:])
    xs = np.array(xs)
    right = np.stack([xs, zc], 1)
    left = np.stack([-xs[::-1], zc[::-1]], 1)
    return np.vstack([[0, 0], right, [[0, 74.0]], left])


def pebble_v4_mm():
    t = np.linspace(0, 2 * math.pi, 360, endpoint=False)
    y = 36.0 * np.sin(t)
    x = 32.0 * np.cos(t) * (1 + 0.045 * np.sin(t))
    y = np.maximum(y, y.min() + 2.2)
    return np.stack([x, y], 1)


def coin_v1_mm():
    t = np.linspace(0, 2 * math.pi, 360, endpoint=False)
    return np.stack([26.0 * np.cos(t), 26.0 * np.sin(t)], 1)


def draw_sil(P_mm, px_tall, ss=8):
    P = np.asarray(P_mm, float)
    P = P - [P[:, 0].min(), P[:, 1].min()]
    h = P[:, 1].max()
    k = px_tall * ss / h
    w = int(math.ceil(P[:, 0].max() * k)) + 2
    im = Image.new('L', (w, px_tall * ss + 2), 255)
    ImageDraw.Draw(im).polygon([(x * k + 1, px_tall * ss + 1 - y * k) for x, y in P], fill=0)
    return im.resize((max(1, round(w / ss)), px_tall), Image.LANCZOS)


def shadow20(outdir):
    items = [('SOUL v5 (final)', soul_outline_mm()), ('v1 · moneda Ø52', coin_v1_mm()), ('v4 · PEBBLE', pebble_v4_mm())]
    sil = [(lab, draw_sil(P, 20)) for lab, P in items]
    Wc, Hc = 900, 330
    board = Image.new('RGB', (Wc, Hc), (255, 255, 255))
    dr = ImageDraw.Draw(board)
    f = ImageFont.truetype(FONT, 15)
    fb = ImageFont.truetype(FONT_R, 16)
    dr.text((20, 14), 'Testul siluetei la 20 px: aceleași trei forme, fiecare scalată la 20 px înălțime (1:1, apoi mărit ×8)',
            font=fb, fill=INK)
    for i, (lab, im) in enumerate(sil):
        cx = 150 + i * 300
        board.paste(im.convert('RGB'), (int(cx - im.size[0] / 2), 60))
        big = im.resize((im.size[0] * 8, im.size[1] * 8), Image.NEAREST)
        board.paste(big.convert('RGB'), (int(cx - big.size[0] / 2), 100))
        dr.text((cx, 100 + 160 + 12), lab, font=f, fill=INK, anchor='mt')
    dr.text((20, Hc - 22), 'randare / concept (CGI) · contur calculat din geometria v5 (soul_geo.py)', font=f, fill=INK)
    out = os.path.join(outdir, 'soul_v5_shadow20.png')
    board.save(out, optimize=True)
    print('wrote', out)


def main():
    shot, png, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    if shot == 'shadow20':
        return shadow20(outdir)
    pre = png.endswith('_preview.png')
    if shot == 'hero':
        if pre:
            return
        return hero(png, outdir)
    if shot.startswith('check1'):
        return check1(png, outdir)
    if not pre:
        dst = os.path.join(outdir, 'soul_v5_%s.png' % shot)
        shutil.copyfile(png, dst)
        print('wrote', dst)
    if shot == 'front_00':
        front_props(png, outdir)


if __name__ == '__main__':
    main()
