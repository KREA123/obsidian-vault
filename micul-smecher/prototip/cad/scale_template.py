#!/usr/bin/env python3
"""scale_template.py -- the true-scale print template ../SOUL-marimi-scara-reala.pdf (A4 landscape, 2 pages).

Rev 2026-10-20 (founder decision: the final product is size S; the prototype stays M). Page 1 shows, at 1 : 1,
SOUL S (chosen) from the front, from the side with its final depth 23.0 mm and from the top, next to the M prototype
(front + side, 31.5 mm). Every outline comes from the render section model (renders/v9/src/marg_geo.py, local
geometry; M = x 90/63 with s_back 0.735) and the numbers from docs/size-s.json. Page 2: what changes S vs M.
The first version (2026-10-12: S / S+ / M to choose from) was a hand-made HTML; this script replaces it.

    python3 scale_template.py      -> ../SOUL-marimi-scara-reala.pdf (Playwright Chromium, print at 100 %)
"""
import json
import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(MS, 'renders', 'v9', 'src'))
import marg_geo as MG  # noqa: E402

SPEC = json.load(open(os.path.join(MS, 'docs', 'size-s.json')))
OUT = os.path.join(MS, 'prototip', 'SOUL-marimi-scara-reala.pdf')
C8 = math.cos(math.radians(8.0))
BS = MG.MargaritarV9(depth_m=SPEC['dims_mm']['d'] * MG.K)     # S: 23.0 mm deep
BM = MG.MargaritarV9()                                          # M: v9, 31.5 mm at K
FOOT_A, FOOT_B, FOOT_P = 14.0, 6.9, 2.6


def prof(B, k):
    zz = np.concatenate([np.linspace(MG.Z_CUT, B.H - 6, 300), B.H - np.linspace(math.sqrt(6.0), 0, 120) ** 2])
    w, yf, yb, ys, c, pf = B.sections(zz)
    return zz, w, yf, yb


def path(pts):
    return 'M' + ' L'.join('%.3f %.3f' % (x, y) for x, y in pts) + ' Z'


def front_svg(B, k, x0, ybase, eyes=True, label_active=True):
    """front view at 1:1 (paper mm): x0 = centre, ybase = paper y of the foot bottom"""
    zz, w, yf, yb = prof(B, k)
    Z = (zz - MG.Z_FOOT) * k
    P = [(x0 + wi * k, ybase - z) for wi, z in zip(w, Z)] + [(x0 - wi * k, ybase - z) for wi, z in zip(w[::-1], Z[::-1])]
    G = B.G()
    gz = ybase - (G[2] - MG.Z_FOOT) * k
    r = 26.0 * k
    ra = 21.88 * k
    s = ['<path d="%s" class="alu"/>' % path(P)]
    s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" class="foot"/>' % (x0 - FOOT_A * k, ybase - MG.FOOT_H * k,
                                                                                   2 * FOOT_A * k, MG.FOOT_H * k))
    s.append('<ellipse cx="%.2f" cy="%.2f" rx="%.2f" ry="%.2f" class="glass"/>' % (x0, gz, r, r * C8))
    s.append('<ellipse cx="%.2f" cy="%.2f" rx="%.2f" ry="%.2f" class="act"/>' % (x0, gz, ra, ra * C8))
    if eyes:
        ew, eh, dx = 0.085 * ra, 0.30 * ra, 0.30 * ra
        for sx in (-1, 1):
            s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" class="eye"/>' % (
                x0 + sx * dx - ew, gz - eh / 2, 2 * ew, eh, ew))
    return '\n'.join(s), (x0 - w.max() * k, x0 + w.max() * k, ybase - Z.max())


def side_svg(B, k, x0, ybase):
    """right side at 1:1: x0 = paper x of the foot centre (y = 0), face to the left"""
    zz, w, yf, yb = prof(B, k)
    Z = (zz - MG.Z_FOOT) * k
    P = [(x0 + y * k, ybase - z) for y, z in zip(yf, Z)] + [(x0 + y * k, ybase - z) for y, z in zip(yb[::-1], Z[::-1])]
    G = B.G()
    up = np.array([math.sin(math.radians(8)), C8])
    gc = np.array([G[1], G[2] - MG.Z_FOOT])
    a, b = (gc - 26 * up) * k, (gc + 26 * up) * k
    s = ['<path d="%s" class="alu"/>' % path(P),
         '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" class="foot"/>' % (x0 - FOOT_B * k, ybase - MG.FOOT_H * k,
                                                                               2 * FOOT_B * k, MG.FOOT_H * k),
         '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="gside"/>' % (x0 + a[0], ybase - a[1], x0 + b[0], ybase - b[1])]
    y0, y1 = yf.min() * k, yb.max() * k
    return '\n'.join(s), (x0 + y0, x0 + y1, ybase - Z.max())


def top_svg(B, k, cx, cy):
    rings = [B.ring(z, 360) for z in np.linspace(MG.Z_CUT, B.H - 0.1, 90)]
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    u = unary_union([Polygon(r).buffer(0) for r in rings])
    P = [(cx + x * k, cy - y * k) for x, y in np.asarray(u.exterior.coords)]
    return '<path d="%s" class="alu"/>' % path(P)


def dim_h(x1, x2, y, txt):
    return ('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="dim"/>' % (x1, y, x2, y)
            + '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="dim"/>' % (x1, y - 1.5, x1, y + 1.5)
            + '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="dim"/>' % (x2, y - 1.5, x2, y + 1.5)
            + '<text x="%.2f" y="%.2f" class="dt">%s</text>' % ((x1 + x2) / 2, y - 1.0, txt))


def page1():
    yb = 121.0
    els = []
    s1, bS = front_svg(BS, 1.0, 45, yb)
    s2, bSs = side_svg(BS, 1.0, 105, yb)
    s3 = top_svg(BS, 1.0, 45, 167)
    s4, bM = front_svg(BM, MG.K, 185, yb)
    s5, bMs = side_svg(BM, MG.K, 262, yb)
    els += [s1, s2, s3, s4, s5]
    d = SPEC['dims_mm']
    els.append(dim_h(bS[0], bS[1], yb + 5.5, '%.1f' % d['w']))
    els.append(dim_h(bSs[0], bSs[1], yb + 5.5, '%.1f' % d['d']))
    els.append(dim_h(bM[0], bM[1], yb + 5.5, '90,0'))
    els.append(dim_h(bMs[0], bMs[1], yb + 5.5, '31,5'))
    txt = [
        (75, yb + 14, 'big', 'S — ALES (produsul final)'),
        (75, yb + 19.5, 'mid', '63 × 70,8 × 23,0 mm · sticlă Ø52'),
        (75, yb + 24, 'small', 'ecran 1,75″ AMOLED 466×466 · negru adevărat · baterie 750 mAh [estimare]'),
        (223, yb + 14, 'bigm', 'M — prototipul (rămâne)'),
        (223, yb + 19.5, 'mid', '90 × 101 × 31,5 mm · sticlă Ø74,3'),
        (223, yb + 24, 'small', 'ecran 2,8″ IPS 480×480 · Waveshare 2.8C · pentru teste și dovada TRL 3'),
        (45, bS[2] - 3, 'lab', 'față'), (105, bSs[2] - 3, 'lab', 'profil (+x)'),
        (185, bM[2] - 3, 'lab', 'față'), (262, bMs[2] - 3, 'lab', 'profil (+x)'),
        (45, 182.5, 'lab', 'S văzut de sus (fața în jos), adâncime 23,0'),
    ]
    for x, y, c, t in txt:
        els.append('<text x="%.2f" y="%.2f" class="%s">%s</text>' % (x, y, c, t))
    # 10 cm ruler
    rx, ry = 100, 170
    r = ['<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="rul"/>' % (rx, ry, rx + 100, ry)]
    for i in range(101):
        h = 3.2 if i % 10 == 0 else (2.2 if i % 5 == 0 else 1.3)
        r.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="rul"/>' % (rx + i, ry, rx + i, ry - h))
        if i % 10 == 0:
            r.append('<text x="%.2f" y="%.2f" class="rt">%d</text>' % (rx + i, ry + 3.6, i // 10))
    r.append('<text x="%.2f" y="%.2f" class="note">← rigla trebuie să aibă exact 10 cm.</text>' % (rx + 103, ry - 2.0))
    r.append('<text x="%.2f" y="%.2f" class="note">Dacă nu, ai printat cu „fit to page”: printează din nou la 100 %%.</text>'
             % (rx + 103, ry + 1.6))
    els += r
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="185mm" viewBox="0 0 297 185">%s</svg>' % '\n'.join(els)
    return svg


CSS = """
@page { size: A4 landscape; margin: 0 }
html, body { margin: 0; padding: 0; font-family: 'DejaVu Sans', sans-serif; color: #1b1b1b }
.page { width: 297mm; height: 210mm; position: relative; overflow: hidden; page-break-after: always; box-sizing: border-box }
h1 { font-size: 20pt; margin: 0; position: absolute; left: 12mm; top: 8mm }
.sub { position: absolute; left: 12mm; top: 17.5mm; font-size: 8.4pt; color: #444; width: 272mm }
.art { position: absolute; left: 0; top: 23mm }
svg .alu { fill: #d9dadc; stroke: #222; stroke-width: 0.25 }
svg .foot { fill: #8d8f92; stroke: none }
svg .glass { fill: #050505; stroke: none }
svg .gside { stroke: #050505; stroke-width: 0.9 }
svg .act { fill: none; stroke: #8a8a8a; stroke-width: 0.2; stroke-dasharray: 1 0.8 }
svg .eye { fill: #f3ead6 }
svg .dim { stroke: #1d4f9c; stroke-width: 0.18 }
svg .dt { font-size: 2.6px; fill: #1d4f9c; text-anchor: middle }
svg .big { font-size: 5px; font-weight: bold; text-anchor: middle; fill: #111 }
svg .bigm { font-size: 5px; font-weight: bold; text-anchor: middle; fill: #555 }
svg .mid { font-size: 3.2px; text-anchor: middle }
svg .small { font-size: 2.5px; text-anchor: middle; fill: #555 }
svg .lab { font-size: 2.6px; text-anchor: middle; fill: #666 }
svg .rul { stroke: #111; stroke-width: 0.2 }
svg .rt { font-size: 2.4px; text-anchor: middle }
svg .note { font-size: 2.6px; fill: #333 }
table { border-collapse: collapse; font-size: 8.6pt; position: absolute; left: 12mm; top: 28mm; width: 273mm }
td, th { border: 0.3pt solid #999; padding: 1.6mm 2mm; vertical-align: top; text-align: left }
th { background: #eee }
td.s { background: #f6f6ef }
.foot2 { position: absolute; left: 12mm; top: 168mm; width: 273mm; font-size: 8.4pt; line-height: 1.45 }
"""


def page2():
    s = SPEC
    bl = s['est_battery_life']
    rows = [
        ('Rol', '<b>produsul final</b> (decizia fondatorului, 20.10.2026)', 'prototipul de lucru: teste și dovada TRL 3 (PoC)'),
        ('Corp L × Î × A', '<b>63,0 × 70,8 × 23,0 mm</b> (cu piciorul de 1,2 mm)', '90 × 101 × 31,5 mm (design v9); kitul P0-M e 112 × 125 × 31,6'),
        ('Forma', 'MĂRGĂRITAR la scara de design; doar spatele e comprimat (s_back 0,807)', 'aceeași formă × 1,43 (s_back 0,735)'),
        ('Sticla', 'Ø52, plată, 2.5D, neagră', 'Ø74,3 (design) / Ø95,86 a plăcii 2.8C (kit)'),
        ('Ecran', '1,75″ <b>AMOLED</b> 466×466, CO5300, negru adevărat', '2,8″ IPS 480×480, ST7701'),
        ('Placa', 'dezvoltare: Waveshare ESP32-S3-Touch-AMOLED-1.75 (2 microfoane + difuzor pe placă); produs: PCB propriu [estimare, EVT]',
         'Waveshare ESP32-S3-Touch-LCD-2.8C, SoulOS 1.9.1 („SoulOS Alive”)'),
        ('Baterie', '<b>%d mAh</b> LiPo 603040 [estimare]; prototipul S-P0: ~%d mAh (503030) [estimare]' % (
            s['battery_mAh'], s['variants']['S-P0_dev_board']['battery_mAh']), '1500 mAh (803450)'),
        ('Autonomie (ziua-model docs/09)', '≈ %d h (%d–%d h) [estimare]; ≈ %d h cu light sleep' % (
            bl['typical_day_h'], bl['range_h'][0], bl['range_h'][1], bl['with_light_sleep_firmware_h']),
         '≈ %d h' % bl['m_for_comparison_h']),
        ('Greutate', '≈ %d g [estimare]' % s['weight_g_est'], '–'),
        ('Neschimbat', 'cele 5 culori anodizate · ochii vii (120 de modele, rarități) · SoulOS Alive · AI-ul proprietarului (nu e inclus) · fără cameră · încă fără CE · de la 249 €', ''),
    ]
    tr = ''.join('<tr><th>%s</th><td class="s">%s</td><td>%s</td></tr>' % r for r in rows)
    return ('<div class="page"><h1>SOUL S (ales) și M (prototip) — ce se schimbă</h1>'
            '<table><tr><th></th><th>S — produsul final</th><th>M — prototipul</th></tr>%s</table>'
            '<div class="foot2">Cifrele vin din <code>docs/size-s.json</code> și <code>docs/12-SIZE-S.md</code>. Bateria, autonomia și '
            'greutatea sunt <b>estimări</b> (geometrie + liste de prețuri), nu măsurători pe placă. Contururile de pe pagina 1 sunt '
            'din modelul de secțiuni al randărilor (<code>renders/v9/src/marg_geo.py</code>), la scara 1 : 1.<br>'
            'ARTEMIS DIGITAL S.R.L. · 20.10.2026</div></div>') % tr


def main():
    html = ('<!doctype html><html><head><meta charset="utf-8"><title>SOUL la mărime reală — S (ales) și M</title>'
            '<style>%s</style></head><body>'
            '<div class="page"><h1>SOUL la mărime reală — S (ales) și M (prototip)</h1>'
            '<div class="sub">Printează la 100 %% (scară reală), decupează și ține-le în mână. Negru = sticla, linia punctată = zona '
            'activă a ecranului, gri = aluminiul; piciorul de polimer e gri închis. Profilul arată adâncimea finală: S 23,0 mm, M 31,5 mm.</div>'
            '<div class="art">%s</div></div>%s</body></html>') % (CSS, page1(), page2())
    from playwright.sync_api import sync_playwright
    fd, fn = tempfile.mkstemp(suffix='.html')
    os.close(fd)
    open(fn, 'w', encoding='utf-8').write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        pg = b.new_page()
        pg.goto('file://' + fn)
        pg.pdf(path=OUT, width='297mm', height='210mm', print_background=True, prefer_css_page_size=True)
        b.close()
    os.remove(fn)
    print('wrote', OUT, os.path.getsize(OUT))


if __name__ == '__main__':
    main()
