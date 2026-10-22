#!/usr/bin/env python3
"""blueprints_s.py -- engineering sheets of SOUL size S (the final product, founder decision 2026-10-20).

Sheet 1 (product): SOUL S = MĂRGĂRITAR at its native design scale, drawn FROM THE SECTION MODEL the renders use
(renders/v9/src/marg_geo.py, "local" geometry, back half compressed to s_back 0.807 -> 23.0 mm deep; the numbers
are the ones in docs/size-s.json). Front / right (+x) / top / bottom views, 2 : 1, with dimensions.
Sheet 2 (S-P0 kit): the DIY prototype around the stock Waveshare ESP32-S3-Touch-AMOLED-1.75, projected and
sectioned from the meshes that soul_p0_s.py exported (../stl/s/assembly/s_<variant>_*.stl) + report_s_<variant>.json.

    python3 blueprints_s.py [prod] [p0]   -> micul-smecher/blueprints/final/soul_s_*.svg + .png (2400 px)
Same drawing kit and style as blueprints_p0.py (size M).
"""
import json
import math
import os
import sys

os.environ.setdefault('SOUL_K', '1')          # the S-P0 outline (soul_geom at K = KY = 1)
os.environ.setdefault('SOUL_KY', '1')
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from shapely.geometry import Polygon, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blueprints_p0 as BP  # noqa: E402  (helpers: draw_poly, draw_lines, notes, table, write, silhouette, ...)
from blueprints_p0 import Sheet, View, draw_poly, draw_lines, notes, table, write, silhouette, feature_lines, section  # noqa: E402
import soul_geom as g  # noqa: E402

MS = BP.MS
sys.path.insert(0, os.path.join(MS, 'renders', 'v9', 'src'))
import marg_geo as MG  # noqa: E402

DATE = '2026-10-20'
SPEC = json.load(open(os.path.join(MS, 'docs', 'size-s.json')))
D_S = SPEC['dims_mm']['d']
B = MG.MargaritarV9(depth_m=D_S * MG.K)        # depth() is compared with depth_m / K -> 23.0 mm at local scale
ZF = MG.Z_FOOT                                 # drawing Z = local z - ZF (foot bottom = 0)
C8, S8 = math.cos(math.radians(8.0)), math.sin(math.radians(8.0))
FOOT_A, FOOT_B, FOOT_P = 14.0, 6.9, 2.6        # v9 foot (soul_v9.py)


def tb(sh, title, sub, scale, sheet, dwg, l1, l2, src1, src2):
    x0, y0, w, h = 240, 241, 170, 46
    sh.rect(x0, y0, w, h, 'tbf')
    c1, c2 = x0 + 92, x0 + 131
    r1, r2 = y0 + 17, y0 + 32
    for a in [(c1, y0, c1, y0 + h), (c2, y0, c2, y0 + h), (x0, r1, x0 + w, r1), (x0, r2, x0 + w, r2)]:
        sh.line(*a, 'fr2t')

    def cell(x, y, label, value, vs=3.3, bold=True):
        sh.text(x + 1.4, y + 3.0, label, 1.8, 'start', 'td')
        sh.text(x + 1.4, y + 3.2 + vs + 1.8, value, vs, 'start', 'tx', weight='bold' if bold else None)
    sh.text(x0 + 3, y0 + 12.8, 'SOUL', 10.5, 'start', 'tx', weight='bold', extra='letter-spacing="1.2"')
    sh.text(x0 + 36, y0 + 7.2, l1, 2.3, 'start', 'td')
    sh.text(x0 + 36, y0 + 11.0, l2, 2.3, 'start', 'td')
    sh.text(x0 + 36, y0 + 14.8, 'DWG ' + dwg, 2.3, 'start', 'td')
    cell(x0, r1, 'TITLE', title, 3.1)
    sh.text(x0 + 1.4, r1 + 13.0, sub, 2.0, 'start', 'tx')
    cell(x0, r2, 'SOURCE', src1, 2.4, bold=False)
    sh.text(x0 + 1.4, r2 + 11.6, src2, 1.9, 'start', 'td')
    cell(c1, y0, 'SCALE', scale)
    cell(c2, y0, 'UNITS', 'mm')
    cell(c1, r1, 'REV', 'S-A')
    cell(c2, r1, 'DATE', DATE, 3.0)
    cell(c1, r2, 'SHEET', sheet)
    cell(c2, r2, 'SIZE / PROJ.', 'A3')
    sh.proj3(c2 + 18, r2 + 12.2, 0.72)


# ================================================================== product geometry (marg_geo local, Z from foot)
ZZ = np.concatenate([np.linspace(MG.Z_CUT, B.H - 6, 500), B.H - np.linspace(math.sqrt(6.0), 0, 200) ** 2])
W_, YF, YB, YS, C_, PF_ = B.sections(ZZ)
Z = ZZ - ZF


def sel(a, b, p, n=240):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.stack([a * np.sign(c) * np.abs(c) ** (2 / p), b * np.sign(s) * np.abs(s) ** (2 / p)], 1)


def front_sil():
    body = Polygon(np.vstack([np.stack([W_, Z], 1), np.stack([-W_[::-1], Z[::-1]], 1)])).buffer(0)
    foot = Polygon([(-FOOT_A, 0), (FOOT_A, 0), (FOOT_A, MG.FOOT_H + 0.01), (-FOOT_A, MG.FOOT_H + 0.01)])
    return unary_union([body, foot])


def side_sil():
    body = Polygon(np.vstack([np.stack([YF, Z], 1), np.stack([YB[::-1], Z[::-1]], 1)])).buffer(0)
    foot = Polygon([(-FOOT_B, 0), (FOOT_B, 0), (FOOT_B, MG.FOOT_H + 0.01), (-FOOT_B, MG.FOOT_H + 0.01)])
    return unary_union([body, foot])


def top_sil():
    return unary_union([Polygon(B.ring(z, 720)).buffer(0) for z in np.linspace(MG.Z_CUT, B.H - 0.05, 160)])


def dims():
    zz = np.linspace(MG.Z_CUT, B.H, 4000)
    w, yf, yb = B.sections(zz)[:3]
    cut = B.ring(MG.Z_CUT, 2048)
    return dict(W=2 * w.max(), H=B.H - ZF, D=yb.max() - yf.min(), z_wmax=zz[np.argmax(w)] - ZF,
                y0=yf.min(), y1=yb.max(), cut_w=cut[:, 0].max() - cut[:, 0].min(),
                cut_d=cut[:, 1].max() - cut[:, 1].min(), G=B.G())


def glass_ellipse(r, n=180):
    """the flat glass circle (radius r, on the 8 deg leaning face) seen from the front: x = r cos, Z = Gz + r C8 sin"""
    G = B.G()
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([r * np.cos(t), G[2] - ZF + r * C8 * np.sin(t)], 1)


def sheet_product(theme='blue'):
    d = dims()
    G = B.G()
    gz = G[2] - ZF
    sh = Sheet(theme)
    sh.frame()
    k = 2.0
    VF = View(88, 222, k)          # front: u = X, v = Z
    VR = View(200, 222, k)         # right (+x): u = Y (back to the right), v = Z
    VT = View(88, 44, k)           # top: u = X, v = Y (back up)
    VBo = View(318, 46, k)         # bottom: u = X, v = -Y (front up)
    TY = 238

    # ---------------- FRONT
    fs = front_sil()
    draw_poly(sh, VF, fs, 'o')
    sh.line(*VF.p(-d['cut_w'] / 2, MG.FOOT_H), *VF.p(d['cut_w'] / 2, MG.FOOT_H), 'o3')
    draw_poly(sh, VF, Polygon(glass_ellipse(26.0)), 'gl')
    sh.poly(VF.pl(glass_ellipse(26.0 + 0.45)), 'o3')
    sh.poly(VF.pl(glass_ellipse(21.88)), 'ph')
    sh.centermark(*VF.p(0, gz), 26 * k, 3)
    zw = d['z_wmax']
    sh.dim_h(*VF.p(-d['W'] / 2, zw), *VF.p(d['W'] / 2, zw), VF.p(0, 0)[1] + 9, '%.2f' % d['W'])
    sh.dim_v(*VF.p(-d['W'] / 2, 0), *VF.p(-d['W'] / 2, d['H']), VF.p(-d['W'] / 2, 0)[0] - 9, '%.1f (incl. foot %.1f)' % (d['H'], MG.FOOT_H))
    sh.dim_v(*VF.p(d['W'] / 2, 0), *VF.p(d['W'] / 2, gz), VF.p(d['W'] / 2, 0)[0] + 6, '%.1f' % gz)
    sh.dim_h(*VF.p(-26, gz), *VF.p(26, gz), VF.p(0, gz)[1] - 26 * k * C8 - 6, 'GLASS Ø52 flat, 2.5D', size=2.4)
    sh.dim_h(*VF.p(-FOOT_A, 0), *VF.p(FOOT_A, 0), VF.p(0, 0)[1] + 4, 'foot 28', size=2.0)
    sh.leader(VF.p(21.88 * 0.71, gz - 21.88 * C8 * 0.71), (VF.p(d['W'] / 2, 0)[0] + 3, VF.p(0, 6)[1]), '',
              lines=['screen Ø43.76 active', '1.75" AMOLED 466x466', '(dash-dot)'], side=1, size=2.0)
    sh.leader(VF.p(26.45 * 0.71, gz + 26.45 * C8 * 0.71), (VF.p(d['W'] / 2, 0)[0] + 3, VF.p(0, 66)[1]), '',
              lines=['45° chamfer 0.45', 'glass seat'], side=1, size=2.0)
    sh.text(VF.p(0, 0)[0], TY, 'FRONT', 3.2, 'middle', 'tx', weight='bold')
    sh.text(VF.p(0, 0)[0], TY + 3.8, 'face leans back 8°, glass seen foreshortened', 2.1, 'middle', 'td')

    # ---------------- RIGHT (+X)
    draw_poly(sh, VR, side_sil(), 'o')
    sh.poly(VR.pl(np.stack([YS, Z], 1)), 'ph', close=False)
    up = np.array([S8, C8])
    gc = np.array([G[1], gz])
    a_, b_ = gc - 26 * up, gc + 26 * up
    nrm = np.array([C8, -S8])
    sh.poly(VR.pl([a_, b_, b_ + 0.7 * nrm, a_ + 0.7 * nrm]), 'gl')
    # speaker slot on the +x seam (v9: local z 42-54, 0.6 wide)
    zs = np.linspace(42.0, 54.0, 40)
    ys = B.sections(zs)[3]
    sh.poly(VR.pl(np.vstack([np.stack([ys - 0.3, zs - ZF], 1), np.stack([ys[::-1] + 0.3, zs[::-1] - ZF], 1)])), 'o2')
    sh.line(*VR.p(d['y0'], MG.FOOT_H), *VR.p(d['y1'], MG.FOOT_H), 'o3')
    sh.dim_h(*VR.p(d['y0'], 20), *VR.p(d['y1'], 20), VR.p(0, 0)[1] + 9, '%.1f' % d['D'])
    sh.dim_h(*VR.p(-FOOT_B, 0), *VR.p(FOOT_B, 0), VR.p(0, 0)[1] + 4, 'foot 13.8', size=2.0, arrows_out=True)
    sh.leader(VR.p(float(ys[20]) + 0.3, 48 - ZF), (VR.p(d['y1'] + 8, 0)[0], VR.p(0, 58)[1]), '',
              lines=['SPEAKER SLOT 12 x 0.6', 'laser, +x seam', 'Z %.1f-%.1f' % (42 - ZF, 54 - ZF)], side=1, size=2.0)
    sh.leader(VR.p(float(B.sections(np.array([30.0]))[3][0]), 30 - ZF), (VR.p(d['y1'] + 8, 0)[0], VR.p(0, 36)[1]), '',
              lines=['SEAM (silhouette line)', 'front / back halves'], side=1, size=2.0)
    sh.leader(VR.p(float(gc[0] + 0.35), gz), (VR.p(d['y1'] + 8, 0)[0], VR.p(0, 82)[1] if False else VR.p(0, 75)[1]), '',
              lines=['8° face, flat glass', 'centre Z %.1f' % gz], side=1, size=2.0)
    sh.leader(VR.p(4, 0.6), (VR.p(d['y1'] + 8, 0)[0], VR.p(0, 12)[1]), '',
              lines=['polymer base plate', '+ oval foot 1.2', '(antenna window,', ' 5 pogo contacts)'], side=1, size=2.0)
    sh.text(VR.p(0, 0)[0], TY, 'RIGHT (+X)', 3.2, 'middle', 'tx', weight='bold')
    sh.text(VR.p(0, 0)[0], TY + 3.8, 'back compressed, s_back %.3f' % B.s_back, 2.1, 'middle', 'td')

    # ---------------- TOP
    ts = top_sil()
    draw_poly(sh, VT, ts, 'o')
    ym = float(B.sections(np.array([d['z_wmax'] + ZF]))[3][0])
    sh.line(*VT.p(-d['W'] / 2 - 4, ym), *VT.p(d['W'] / 2 + 4, ym), 'ph')
    sh.text(VT.p(d['W'] / 2 + 5, 0)[0], VT.p(0, ym)[1] + 0.8, 'SEAM', 1.9, 'start', 'td')
    sh.dim_v(*VT.p(-d['W'] / 2, d['y0']), *VT.p(-d['W'] / 2, d['y1']), VT.p(-d['W'] / 2, 0)[0] - 7, '%.1f' % d['D'])
    sh.text(VT.p(0, 0)[0], VT.p(0, d['y0'])[1] + 7, 'TOP  (face toward the bottom of the sheet)', 2.6, 'middle', 'tx', weight='bold')

    # ---------------- BOTTOM
    cut = B.ring(MG.Z_CUT, 720)
    bot = np.stack([cut[:, 0], -cut[:, 1]], 1)
    draw_poly(sh, VBo, Polygon(bot).buffer(0), 'o')
    ft = sel(FOOT_A, FOOT_B, FOOT_P)
    draw_poly(sh, VBo, Polygon(ft), 'f2')
    t = np.linspace(0, 2 * math.pi, 120)
    sh.poly(VBo.pl(np.stack([6.8 * np.cos(t), 6.25 * np.sin(t)], 1)), 'o3')
    for a in (0, 90, 180, 270):
        sh.circle(*VBo.p(4.0 * math.cos(math.radians(a)), 4.0 * math.sin(math.radians(a))), 0.6 * k, 'o3')
    sh.circle(*VBo.p(0, 0), 0.9 * k, 'o3')
    for sx in (-1, 1):
        sh.circle(*VBo.p(sx * 11.2, 0), 1.3 * k, 'o3')
    sh.dim_h(*VBo.p(-d['cut_w'] / 2, 0), *VBo.p(d['cut_w'] / 2, 0), VBo.p(0, -d['cut_d'] / 2)[1] + 7,
             'FLAT BASE %.1f x %.1f' % (d['cut_w'], d['cut_d']))
    sh.dim_v(*VBo.p(FOOT_A, -FOOT_B), *VBo.p(FOOT_A, FOOT_B), VBo.p(d['cut_w'] / 2, 0)[0] + 5, '13.8', size=2.0)
    sh.text(VBo.p(0, 0)[0], VBo.p(0, d['cut_d'] / 2)[1] - 5, 'BOTTOM  (front up)', 2.8, 'middle', 'tx', weight='bold')
    sh.text(VBo.p(0, 0)[0], VBo.p(0, -d['cut_d'] / 2)[1] + 12, 'foot 28 x 13.8 superellipse; 5 gold contacts in a TPU ring;',
            1.9, 'middle', 'td')
    sh.text(VBo.p(0, 0)[0], VBo.p(0, -d['cut_d'] / 2)[1] + 15, '2x Torx T5 (v9 render model, layout [E] until EVT)',
            1.9, 'middle', 'td')

    # ---------------- notes + S vs M
    y = notes(sh, 300, 86, [
        'Envelope %.1f x %.1f x %.1f' % (d['W'], d['H'], d['D']),
        '  (W x H incl. foot x D)',
        'Shape MARGARITAR v9, design scale',
        '  marg_geo.py local, s_back %.3f' % B.s_back,
        'Glass Ø52 flat 2.5D black, 0.7 [E]',
        'Screen 1.75" AMOLED 466x466,',
        '  CO5300 QSPI, true black',
        'Shell 6061-T6, bead-blast, anodise II',
        '  wall 1.4 [E]; 5 colours',
        'Battery 750 mAh LiPo 603040 class [E]',
        'Mass ~85 g [E] (75-95)',
        'Mics 2 ports -x seam (Z 18.8, 44.8)',
        'No camera. Not CE-certified yet.',
    ], size=2.0, head='SOUL S (product)')
    rows = [('W x H x D', '63.0 x 70.8 x 23.0', '90 x 101 x 31.5'),
            ('glass', 'Ø52', 'Ø74.3'),
            ('screen', '1.75" AMOLED 466²', '2.8" IPS 480²'),
            ('board', 'own PCB (dev: AMOLED-1.75)', 'Waveshare 2.8C'),
            ('battery', '750 mAh [E]', '1500 mAh'),
            ('role', 'final product', 'prototype, PoC TRL 3')]
    table(sh, 300, y + 4, [('', 15), ('S (this sheet)', 42), ('M', 52 - 22)], rows, size=1.75, rh=3.3)
    tb(sh, 'GENERAL ARRANGEMENT', 'SOUL S, final product size, from the render section model', '2 : 1', '1 / 2',
       'SOUL-S-01', 'size S - final product, MARGARITAR', '1.75" AMOLED 466x466, glass Ø52',
       'marg_geo.py + docs/size-s.json', 'renders/v10 use the same body')
    return sh


# ================================================================== S-P0 kit (from the CAD meshes)
ASM = os.path.join(MS, 'prototip', 'stl', 's', 'assembly')
_MC = {}


def mesh(v, name):
    key = (v, name)
    if key not in _MC:
        fn = os.path.join(ASM, f's_{v}_{name}.stl')
        _MC[key] = trimesh.load(fn) if os.path.exists(fn) else None
    return _MC[key]


SEC = {'front_shell': ('o', 'hA'), 'back_shell': ('o', 'hB'), 'chassis': ('o2', 'hC'), 'battery': ('fb', None),
       'speaker': ('f2', None), 'board_glass': ('gl', None), 'board_module': ('f2', None),
       'board_components': ('o3', None), 'board_header_8pin': ('o3', None), 'board_usb_receptacle': ('f2', None),
       'usb_plug': ('o3', None)}


def sheet_p0(v='plastic', theme='blue'):
    rp = os.path.join(HERE, f'report_s_{v}.json')
    rs = json.load(open(rp)) if os.path.exists(rp) else {}
    VAR = {'plastic': (2.0, 0.2, 1.2), 'alu': (1.4, 0.1, 0.8), 'alu_band': (1.4, 0.1, 0.8)}[v]   # soul_p0_s.VARIANTS
    sh = Sheet(theme)
    sh.frame()
    k = 2.0
    F, Bk = mesh(v, 'front_shell'), mesh(v, 'back_shell')
    allm = trimesh.util.concatenate([F, Bk])
    GL = mesh(v, 'board_glass')
    (x0, y0, z0), (x1, y1, z1) = allm.bounds
    W, D, H = x1 - x0, y1 - y0, z1 - z0
    # labels use the CAD B-rep size (report_s_*.json, = size-s.json S-P0 25.65); the STL tessellation of the curved back reads ~0.03 less
    Dm = D
    Dl = rs.get('dims', {}).get('D', D)
    VF = View(92, 206, k)
    VS = View(206, 206, k)
    VT = View(326, 52, k)
    TY = 226
    # ---- front
    draw_poly(sh, VF, silhouette(allm, 'front', offset=(0, 0, g.FOOT_H)), 'o')
    if GL is not None:
        draw_poly(sh, VF, silhouette(GL, 'front', offset=(0, 0, g.FOOT_H)), 'gl')
    draw_lines(sh, VF, feature_lines(F, 'front', 30, offset=(0, 0, g.FOOT_H)), 'o2')
    gz = g.G[2] + g.FOOT_H
    sh.dim_h(*VF.p(x0, 0), *VF.p(x1, 0), VF.p(0, 0)[1] + 9, '%.1f' % W)
    sh.dim_v(*VF.p(x0, 0), *VF.p(x0, H), VF.p(x0, 0)[0] - 8, '%.1f (incl. foot)' % H)
    ap = 2 * (24.48 - 1.5)
    sh.leader(VF.p(ap / 2 * 0.71, gz + ap / 2 * 0.69), (VF.p(x1, 0)[0] + 6, VF.p(0, H - 2)[1]), '',
              lines=['APERTURE Ø%.2f' % ap, '(lip 1.5 over the', ' stock glass Ø48.96)'], side=1, size=2.0)
    sh.text(VF.p(0, 0)[0], TY, 'FRONT', 3.2, 'middle', 'tx', weight='bold')
    sh.text(VF.p(0, 0)[0], TY + 3.8, 'seam bosses: 4x M2 (2 low, 2 high)', 2.0, 'middle', 'td')

    # ---- section A-A at x = 0.3 (battery centre); the USB-C cable plug is clipped 6 mm below the foot
    from shapely.affinity import translate as _tr
    from shapely.geometry import box as _box
    xc = 0.3
    for n, (cls, hatch) in SEC.items():
        m = mesh(v, n)
        if m is None:
            continue
        p = section(m, (xc, 0, 0), (1, 0, 0), np.array([0, 1.0, 0]), np.array([0, 0, 1.0]))
        if p.is_empty:
            continue
        p = _tr(p, 0, g.FOOT_H)
        if n == 'usb_plug':
            p = p.intersection(_box(-100, -3, 100, 200))
        draw_poly(sh, VS, p, cls, extra='style="fill:url(#%s)"' % hatch if hatch else '')
    sh.dim_h(*VS.p(y0, 0), *VS.p(y1, 0), VS.p(0, 0)[1] + 9, '%.2f' % Dl)
    sh.line(*VS.p(g.SEAM_A, -2 + g.FOOT_H), *VS.p(g.SEAM_A + g.SEAM_B * (H + 2), H + 2 + g.FOOT_H), 'cut')
    sh.text(VS.p(0, 0)[0] + 6, TY, 'SECTION A-A (x = 0.3)', 3.2, 'middle', 'tx', weight='bold')
    sh.text(VS.p(0, 0)[0] + 6, TY + 3.8, 'glass, module, LiPo (tinted), 1511, chassis;', 2.0, 'middle', 'td')
    sh.text(VS.p(0, 0)[0] + 6, TY + 7.0, 'USB-C plug in its tunnel (cut 3 below)', 2.0, 'middle', 'td')

    # ---- top
    draw_poly(sh, VT, silhouette(allm, 'top'), 'o')
    sh.line(*VT.p(x0 - 4, g.SEAM_A + g.SEAM_B * g.G[2]), *VT.p(x1 + 4, g.SEAM_A + g.SEAM_B * g.G[2]), 'ph')
    sh.text(VT.p(x1 + 5, 0)[0], VT.p(0, g.SEAM_A + g.SEAM_B * g.G[2])[1] + 0.8, 'SEAM', 2.0, 'start', 'td')
    sh.dim_v(*VT.p(x0, y0), *VT.p(x0, y1), VT.p(x0, 0)[0] - 8, '%.2f' % Dl)
    sh.text(VT.p(0, 0)[0], VT.p(0, y0)[1] + 8, 'TOP  (face toward the bottom of the sheet)', 2.8, 'middle', 'tx', weight='bold')

    inter = rs.get('interference', {})
    bad = {kk: vv for kk, vv in inter.items() if abs(vv) > 0.01}
    cl = rs.get('clearance', {})
    ms = rs.get('dims', {}).get('mass_g', {})
    sc = rs.get('screws', [])
    Lo = [s['screw_len_max'] for s in sc if s['kind'] == 'low']
    Up = [s['screw_len_max'] for s in sc if s['kind'] == 'up']
    L_lo = BP.screw_std(min(Lo)) if Lo else 12
    L_up = BP.screw_std(min(Up)) if Up else 8
    rows = ['Envelope %.1f x %.1f x %.2f (CAD B-rep)' % (W, H + g.FOOT_H if H < 70 else H, Dl),
            '  = S product W x H, uncompressed back (s_back 1.0)',
            '  (the STL mesh reads %.2f deep: tessellation)' % Dm,
            'Board Waveshare ESP32-S3-Touch-AMOLED-1.75',
            '  stock glass Ø48.96 x 1.10 under a %.1f lip' % VAR[2],
            'Battery LiPo 503030 class, ~450 mAh [estimare]',
            '  envelope 30.5 x 31 x 5.55, 6° off the board',
            'Speaker 1511 (kit), slot 12 x 1.2 in the +x seam',
            'Walls %.1f, fit clearance %.1f (%s)' % (VAR[0], VAR[1], v),
            'Interference: %d pairs, %d > 0.01 mm3' % (len(inter), len(bad))]
    if ms:
        rows.append('Masses: front %.0f g, back %.0f g, chassis %.0f g' % (
            ms.get('front_shell', 0), ms.get('back_shell', 0), ms.get('chassis', 0)))
    rows.append('UNVERIFIED (calipers first): USB-C cable overmold')
    rows.append('  12.4 x 7.0, MX1.25 plug heights, button travel')
    notes(sh, 262, 98, rows, size=2.0, head='S-P0 KIT (%s)' % v)
    bom = [('1', 'front shell', 'PLA/PETG, seam down'),
           ('2', 'back shell', 'PLA/PETG, seam down'),
           ('3', 'chassis (battery cradle)', 'PETG'),
           ('4', 'pin PWR + pin BOOT', 'PETG, 2 pcs'),
           ('5', 'heat-set insert M2 x 3.2', '4 pcs, front shell'),
           ('6', 'screw M2 x %d' % L_lo, '2 pcs, low (chassis legs)'),
           ('7', 'screw M2 x %d' % L_up, '2 pcs, high'),
           ('8', 'LiPo 503030 class + PCM', '2-pin MX1.25, CHECK +/-'),
           ('9', 'speaker 1511 8 ohm', 'from the board kit'),
           ('10', 'EVA foam 0.3-0.5 / VHB', 'under cell + speaker')]
    table(sh, 262, 150, [('#', 7), ('part', 52), ('note', 82)], bom, size=1.9, rh=3.5)
    tb(sh, 'S-P0 KIT, GA + SECTION', 'DIY prototype of SOUL S around the stock AMOLED-1.75 board', '2 : 1', '2 / 2',
       'SOUL-S-P0-01', 'S-P0 - DIY pilot, MARGARITAR S', 'Waveshare ESP32-S3-Touch-AMOLED-1.75',
       'CadQuery model soul_p0_s.py', 'projected/sectioned from the exported STL')
    return sh


if __name__ == '__main__':
    which = sys.argv[1:] or ['prod', 'p0']
    out = []
    if 'prod' in which:
        out.append(write(sheet_product('blue'), 'soul_s_1_general_arrangement'))
        out.append(write(sheet_product('white'), 'soul_s_1_general_arrangement_white'))
    if 'p0' in which and mesh('plastic', 'front_shell') is not None:
        out.append(write(sheet_p0('plastic', 'blue'), 'soul_s_2_p0_kit'))
    BP.render_png(out)
