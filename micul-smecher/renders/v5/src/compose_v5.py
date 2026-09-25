#!/usr/bin/env python3
"""compose_v5.py -- finishing steps of the v5 renders (system Python: numpy + Pillow).

    python3 compose_v5.py <shot> <tone-mapped.png> <outdir>
        hero          -> soul_v5_hero.png (1600 x 2000) + soul_v5_hero_crop.png (1600 x 1200, same camera)
        check1_*      -> kept next to the input; when all four panels exist -> soul_v5_check1.png (2400 x 1200),
                         with the ember band measured on the render and labelled
        front_00      -> soul_v5_front_00.png + proportions check (printed, written to <outdir>/checks_v5.txt)
        choices       -> soul_v5_choices.png (+ the small CGI note; the labels come from annotate.py)
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

sys.dont_write_bytecode = True

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
def measure_band(png, mm_per_px):
    """Visible height of the ember sole, measured on the render's albedo pass (the ember albedo is unique in the
    frame; shading, contact shadow and the floor reflection do not change it), at the centre column and x = +-20 mm."""
    sys.path.insert(0, HERE)
    from post import read_exr
    alb = read_exr(png[:-4] + '_albedo_0001.exr')
    # ember albedo = (0.69, 0.10, 0.02) mixed with the coat's Fresnel toward grey: classify by hue, not distance
    m = ((alb[..., 0] - alb[..., 1]) > 0.25) & (alb[..., 0] > 0.4)
    H, W = m.shape
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    cx = W / 2.0
    out = {}
    for lab, dx_mm in (('centre', 0.0), ('x-20', -20.0), ('x+20', 20.0)):
        x = int(round(cx + dx_mm / mm_per_px))
        col = m[:, x - 1:x + 2].any(1)
        yy = np.nonzero(col)[0]
        out[lab] = (yy.max() - yy.min() + 1) * mm_per_px if len(yy) else 0.0
    mc = m.copy()
    mc[:int(H * 0.6)] = False                        # the chin region only
    out['max'] = max((np.ptp(np.nonzero(mc[:, x])[0]) + 1) * mm_per_px for x in range(W) if mc[:, x].any())
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
                t = 'bandă ember măsurată: %.1f mm la centru · %.1f / %.1f mm la x ±20 · max %.1f mm · lățime %.0f mm' % (
                    m['centre'], m['x-20'], m['x+20'], m['max'], m['width'])
            else:
                t = 'bandă ember: nu se vede'
            parts = t.split(' · ')
            dr.text((x0 + pw / 2, int(ph * 0.885)), parts[0], font=f3, fill=INK, anchor='mt')
            dr.text((x0 + pw / 2, int(ph * 0.908)), ' · '.join(parts[1:3]), font=f3, fill=INK, anchor='mt')
            dr.text((x0 + pw / 2, int(ph * 0.931)), ' · '.join(parts[3:]), font=f3, fill=INK, anchor='mt')
        else:
            dr.text((x0 + pw / 2, int(ph * 0.885)), 'ton pe ton: se vede doar linia de 0,1 mm', font=f3, fill=INK,
                    anchor='mt')
            dr.text((x0 + pw / 2, int(ph * 0.908)), 'de la marginea tălpii', font=f3, fill=INK, anchor='mt')
        if i:
            dr.line([(x0, int(ph * 0.07)), (x0, int(ph * 0.95))], fill=(200, 192, 182), width=1)
    dr.text((pw * 2, int(ph * 0.985)), 'randare / concept (CGI) · 09 §3.2 estimează 1,7–2,4 mm la nivelul mesei, '
            '0,8–0,9 mm la 9°', font=ImageFont.truetype(FONT, int(ph * 0.014)), fill=INK, anchor='mb')
    out = os.path.join(outdir, 'soul_v5_check1%s.png' % pre)
    board.save(out, optimize=True)
    log_check(outdir, 'check1 ember band (mm): ' + json.dumps({k: {a: round(b, 2) for a, b in v.items()} if v else None
                                                               for k, v in res.items()}))
    print('wrote', out)


# ------------------------------------------------------------------------------------------
def front_props(png, outdir):
    """Proportions on the front render (brief §10.2). Scale = the glass's horizontal diameter (52.0 mm); the body's
    top edge is found against a per-row background (the sweep has a vertical gradient); z 0 = top + 74 mm."""
    a = np.asarray(Image.open(png).convert('RGB'))
    L = lstar(a)
    H, W = L.shape
    # silhouette from the albedo pass (white pearl on a warm-white sweep defeats luminance; albedo ignores shadows)
    exr = png[:-4] + '_albedo_0001.exr'
    sys.path.insert(0, HERE)
    from post import read_exr
    alb = read_exr(exr)[::-1] if False else read_exr(exr)
    bga = np.median(np.concatenate([alb[:, :120].reshape(-1, 3), alb[:, -120:].reshape(-1, 3)]), 0)
    diff = np.abs(alb - bga).max(-1) > 0.06
    dark = L < 12
    ys, xs = np.nonzero(dark)
    gx0, gx1 = np.percentile(xs, 0.2), np.percentile(xs, 99.8)
    gy0, gy1 = np.percentile(ys, 0.2), np.percentile(ys, 99.8)
    gcx, gcy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
    rg = (gx1 - gx0) / 2
    s = (gx1 - gx0) / 52.0                            # px per mm at the glass
    colc = diff[:, int(gcx) - 3:int(gcx) + 4].all(1)
    top = int(np.nonzero(colc[:int(gy0)])[0].min())
    bot = top + 74.0 * s
    yy, xx = np.mgrid[0:H, 0:W]
    disc = (xx - gcx) ** 2 + (yy - gcy) ** 2 <= (rg * 0.98) ** 2
    # eyes: bright pixels in the disc, excluding the glint band (upper-left chord, > 0.6 r from the centre)
    u = ((-(xx - gcx)) + (-(yy - gcy))) / math.sqrt(2) / rg
    eyes = (L > 80) & disc & (u < 0.55)
    ey = np.nonzero(eyes)[0].mean()

    def width_at(z):
        r = int(round(bot - z * s))
        c = np.nonzero(diff[r])[0]
        return (c.max() - c.min() + 1) / s
    rows = [r for r in range(top, int(bot) - int(3 * s))]
    area = sum((lambda c: (c.max() - c.min() + 1) if len(c) else 0)(np.nonzero(diff[r])[0]) for r in rows) / s ** 2
    area += 3.0 * width_at(1.5)                        # the last 3 mm (rocker) by its mid width
    glass_area = math.pi * 26.0 ** 2
    w25, w75 = width_at(18.5), width_at(55.5)
    txt = ('front_00 proportions (scale %.2f px/mm from the Ø52 glass): glass centre %.1f %% of height (target 54-56), '
           'eye line %.1f %% (target 50-52), glass %.1f %% of the front silhouette (target ~52), quarter widths '
           '%.1f / %.1f mm -> broad end up %+.1f %% (target ~+5), max width %.1f mm'
           % (s, 100 * (bot - gcy) / (bot - top), 100 * (bot - ey) / (bot - top), 100 * glass_area / area, w25, w75,
              100 * (w75 / w25 - 1), max(width_at(z) for z in np.arange(10, 70, 0.5))))
    g = L[disc & ~(L > 20) & (u < 0.55)]
    txt += '\nfront_00 glass L* (outside the eyes and the glint band): median %.1f, p95 %.1f, p99 %.1f' % (
        np.median(g), np.percentile(g, 95), np.percentile(g, 99))
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


def choices(png, outdir):
    """Decision board (labels already drawn by annotate.py): add the small CGI note in the lower-right corner."""
    im = Image.open(png).convert('RGB')
    W, H = im.size
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, int(H * 0.016))
    d.text((W - int(H * 0.03), H - int(H * 0.03)), 'randare / concept (CGI)', font=f, fill=INK, anchor='rs')
    dst = os.path.join(outdir, 'soul_v5_choices.png')
    im.save(dst, optimize=True)
    print('wrote', dst)


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
    if shot == 'choices' and not pre:
        return choices(png, outdir)
    if not pre:
        dst = os.path.join(outdir, 'soul_v5_%s.png' % shot)
        shutil.copyfile(png, dst)
        print('wrote', dst)
    if shot == 'front_00':
        front_props(png, outdir)


if __name__ == '__main__':
    main()
