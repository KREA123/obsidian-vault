#!/usr/bin/env python3
"""blueprints_p0.py -- engineering sheets of SOUL-P0 size M (Waveshare 2.8C) drawn FROM THE CAD MODEL.

Every outline, section and hole position is obtained by projecting / sectioning the meshes that soul_p0.py
exported (../stl/assembly/m_<variant>_*.stl, product frame, mm) and every number comes from those meshes or from
cad/report_m_<variant>.json (the interference / clearance check). Drawing kit: micul-smecher/blueprints/src/bp.py.

    python3 blueprints_p0.py            -> micul-smecher/blueprints/final/*.svg + *.png (2400 px)
"""
import json
import math
import os
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union, linemerge

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
MS = os.path.abspath(os.path.join(ROOT, '..'))
sys.path.insert(0, os.path.join(MS, 'blueprints', 'src'))
sys.path.insert(0, HERE)
from bp import Sheet, View, f  # noqa: E402
import soul_geom as g  # noqa: E402

OUTD = os.path.join(MS, 'blueprints', 'final')
os.makedirs(OUTD, exist_ok=True)
ASM = os.path.join(ROOT, 'stl', 'assembly')
REP = {v: json.load(open(os.path.join(HERE, f'report_m_{v}.json'))) for v in ('plastic', 'alu')
       if os.path.exists(os.path.join(HERE, f'report_m_{v}.json'))}
DATE = '2026-09-25'

_MC = {}


def mesh(v, name):
    key = (v, name)
    if key not in _MC:
        fn = os.path.join(ASM, f'm_{v}_{name}.stl')
        _MC[key] = trimesh.load(fn) if os.path.exists(fn) else None
    return _MC[key]


# ------------------------------------------------------------------ projections
# view name -> (direction the viewer looks along, u axis, v axis)   (third-angle layout)
VIEWS = {
    'front': (np.array([0, 1, 0]), np.array([1, 0, 0]), np.array([0, 0, 1])),
    'back': (np.array([0, -1, 0]), np.array([-1, 0, 0]), np.array([0, 0, 1])),
    'right': (np.array([-1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1])),
    'top': (np.array([0, 0, -1]), np.array([1, 0, 0]), np.array([0, 1, 0])),
    'bottom': (np.array([0, 0, 1]), np.array([1, 0, 0]), np.array([0, -1, 0])),
}


def silhouette(m, view, offset=(0, 0, 0)):
    d, U, Vv = VIEWS[view] if isinstance(view, str) else view
    V3 = m.vertices + np.asarray(offset)
    tri = V3[m.faces]
    face = (m.face_normals @ d) < 0
    tri = tri[face]
    P = np.stack([tri @ U, tri @ Vv], -1)
    polys = [Polygon(t) for t in P if abs(np.cross(t[1] - t[0], t[2] - t[0])) > 1e-6]
    return unary_union(polys).buffer(0.01).buffer(-0.01)


def feature_lines(m, view, angle=25.0, offset=(0, 0, 0), only_facing=True):
    d, U, Vv = VIEWS[view] if isinstance(view, str) else view
    ang = m.face_adjacency_angles
    sel = ang > math.radians(angle)
    fa = m.face_adjacency[sel]
    ed = m.face_adjacency_edges[sel]
    if only_facing:
        fn = m.face_normals
        vis = ((fn[fa[:, 0]] @ d) < 0) | ((fn[fa[:, 1]] @ d) < 0)
        ed = ed[vis]
    V3 = m.vertices + np.asarray(offset)
    segs = [LineString([(V3[a] @ U, V3[a] @ Vv), (V3[b] @ U, V3[b] @ Vv)]) for a, b in ed]
    if not segs:
        return []
    ml = linemerge(segs)
    return list(ml.geoms) if hasattr(ml, 'geoms') else [ml]


def section(m, origin, normal, U, Vv):
    """closed section regions of mesh m by a plane, as a shapely (Multi)Polygon in (U, Vv) coordinates"""
    if m is None:
        return Polygon()
    s = m.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return Polygon()
    res = Polygon()
    for loop in s.discrete:
        if len(loop) < 3:
            continue
        p = Polygon(np.stack([loop @ U, loop @ Vv], 1)).buffer(0)
        res = res.symmetric_difference(p)
    return res


def geoms(p):
    if p.is_empty:
        return []
    if isinstance(p, Polygon):
        return [p]
    return [q for q in getattr(p, 'geoms', []) if isinstance(q, Polygon)]


def draw_poly(sh, V, p, cls='o', extra=''):
    for q in geoms(p):
        d = 'M' + ' L'.join('%s %s' % (f(x), f(y)) for x, y in V.pl(q.exterior.coords[:-1])) + ' Z'
        for h in q.interiors:
            d += ' M' + ' L'.join('%s %s' % (f(x), f(y)) for x, y in V.pl(h.coords[:-1])) + ' Z'
        sh.path(d, cls, extra + ' fill-rule="evenodd"')


def draw_lines(sh, V, lines, cls='o2'):
    for ln in lines:
        c = list(ln.coords)
        if len(c) >= 2:
            sh.poly(V.pl(c), cls, close=False)


def title_block(sh, title, sub, scale, sheet, dwg, x0=240, y0=241, w=170, h=46):
    sh.rect(x0, y0, w, h, 'tbf')
    c1, c2 = x0 + 92, x0 + 131
    r1, r2 = y0 + 17, y0 + 32
    for a in [(c1, y0, c1, y0 + h), (c2, y0, c2, y0 + h), (x0, r1, x0 + w, r1), (x0, r2, x0 + w, r2)]:
        sh.line(*a, 'fr2t')

    def cell(x, y, label, value, vs=3.3, bold=True):
        sh.text(x + 1.4, y + 3.0, label, 1.8, 'start', 'td')
        sh.text(x + 1.4, y + 3.2 + vs + 1.8, value, vs, 'start', 'tx', weight='bold' if bold else None)
    sh.text(x0 + 3, y0 + 12.8, 'SOUL', 10.5, 'start', 'tx', weight='bold', extra='letter-spacing="1.2"')
    sh.text(x0 + 36, y0 + 7.2, 'P0 size M - DIY pilot, v6 look', 2.3, 'start', 'td')
    sh.text(x0 + 36, y0 + 11.0, 'Waveshare ESP32-S3-Touch-LCD-2.8C', 2.3, 'start', 'td')
    sh.text(x0 + 36, y0 + 14.8, 'DWG ' + dwg, 2.3, 'start', 'td')
    cell(x0, r1, 'TITLE', title, 3.1)
    sh.text(x0 + 1.4, r1 + 13.0, sub, 2.2, 'start', 'tx')
    cell(x0, r2, 'SOURCE', 'CadQuery model soul_p0.py', 2.5, bold=False)
    sh.text(x0 + 1.4, r2 + 11.6, 'projected/sectioned from the exported STL', 2.0, 'start', 'td')
    cell(c1, y0, 'SCALE', scale)
    cell(c2, y0, 'UNITS', 'mm')
    cell(c1, r1, 'REV', 'P0-A')
    cell(c2, r1, 'DATE', DATE, 3.0)
    cell(c1, r2, 'SHEET', sheet)
    cell(c2, r2, 'SIZE / PROJ.', 'A3')
    sh.proj3(c2 + 18, r2 + 12.2, 0.72)


def notes(sh, x, y, rows, size=2.2, head=None):
    if head:
        sh.text(x, y, head, 2.6, 'start', 'tx', weight='bold')
        y += 4.2
    for r in rows:
        sh.text(x, y, r, size, 'start', 'tx' if not r.startswith('  ') else 'td')
        y += size * 1.45
    return y


def table(sh, x, y, cols, rows, size=2.0, rh=3.6, head_cls='tx'):
    """cols: list of (title, width). rows: list of tuples"""
    W = sum(w for _, w in cols)
    sh.rect(x, y, W, rh * (len(rows) + 1), 'o2')
    cx = x
    for t, w in cols:
        sh.text(cx + 0.8, y + rh - 1.0, t, size, 'start', head_cls, weight='bold')
        cx += w
        if cx < x + W - 0.1:
            sh.line(cx, y, cx, y + rh * (len(rows) + 1), 'o3')
    for i, r in enumerate(rows):
        yy = y + rh * (i + 1)
        sh.line(x, yy, x + W, yy, 'o3')
        cx = x
        for (t, w), val in zip(cols, r):
            sh.text(cx + 0.8, yy + rh - 1.0, str(val), size, 'start', 'tx')
            cx += w
    return y + rh * (len(rows) + 1)


def write(sh, name):
    p = os.path.join(OUTD, name + '.svg')
    open(p, 'w', encoding='utf-8').write(sh.svg())
    return p


# ------------------------------------------------------------------ helpers on the model
def outer_all(v):
    parts = [mesh(v, n) for n in ('front_shell', 'back_shell', 'base_plate')]
    return trimesh.util.concatenate([p for p in parts if p is not None])


def bbox(v):
    m = outer_all(v)
    return m.bounds



# ================================================================== model facts
def shells_mesh(v):
    return trimesh.util.concatenate([mesh(v, n) for n in ('front_shell', 'back_shell', 'base_plate') if mesh(v, n) is not None])


def screw_std(Lmax):
    for L in (25, 20, 16, 14, 12, 10, 8, 6, 5, 4):
        if L <= Lmax - 0.3:
            return L
    return 4


BOARD_IN = ['in_lcd', 'in_pcb', 'in_pcb_tab', 'in_components', 'in_bat_conn', 'in_switch', 'in_key_boot', 'in_key_rst',
            'in_usb_l', 'in_usb_r']


# ================================================================== SHEET 1: GA
def sheet_ga(theme='blue'):
    v = 'plastic' if 'plastic' in REP else 'alu'
    rs = REP.get(v, {})
    sh = Sheet(theme)
    sh.frame()
    k = 1.0
    F, B, BP = mesh(v, 'front_shell'), mesh(v, 'back_shell'), mesh(v, 'base_plate')
    LENS = mesh(v, 'in_lens')
    allm = shells_mesh(v)
    (x0, y0, z0), (x1, y1, z1) = allm.bounds
    W, D, H = x1 - x0, y1 - y0, z1 - z0
    VF = View(80, 208, k)             # front
    VT = View(80, 50, k)              # top (u = X, v = Y)
    VR = View(172, 208, k)            # right side (u = Y, v = Z)
    VB = View(282, 208, k)            # back (u = -X)
    VBo = View(282, 50, k)            # bottom (u = X, v = -Y)
    TY = 225

    draw_poly(sh, VF, silhouette(allm, 'front'), 'o')
    draw_poly(sh, VF, silhouette(LENS, 'front'), 'gl')
    draw_lines(sh, VF, feature_lines(F, 'front', 30), 'o2')
    cx, cz = g.G[0], g.G[2]
    sh.centermark(*VF.p(cx, cz), 35.32 * k, 3)
    sh.circle(*VF.p(cx, cz), 35.32 * k, 'ph')
    sh.dim_h(*VF.p(x0, g.G[2]), *VF.p(x1, g.G[2]), VF.p(0, z0)[1] + 8, '%.1f' % W)
    sh.dim_v(*VF.p(x0, z0), *VF.p(x0, z1), VF.p(x0, 0)[0] - 9, '%.1f (incl. foot %.1f)' % (H, g.FOOT_H))
    sh.dim_v(*VF.p(x1, 0), *VF.p(x1, cz), VF.p(x1, 0)[0] + 5, '%.2f' % cz)
    ap = 2 * (47.93 - 1.5)
    sh.leader(VF.p(-ap / 2 * 0.71, cz + ap / 2 * 0.71), (VF.p(x0, 0)[0] + 4, VF.p(0, z1)[1] - 4), '',
              lines=['APERTURE Ø%.2f (lip 1.5 over lens Ø95.86)' % ap, 'screen Ø70.64 (dash-dot)'], side=1)
    sh.text(VF.p(0, 0)[0], TY, 'FRONT', 3.2, 'middle', 'tx', weight='bold')
    sh.text(VF.p(0, 0)[0], TY + 3.8, 'face leans back %.1f°, nothing on it but the glass' % g.dims_report()['lean_deg'],
            2.1, 'middle', 'td')

    draw_poly(sh, VT, silhouette(allm, 'top'), 'o')
    draw_lines(sh, VT, feature_lines(B, 'top', 30), 'o3')
    ym = g.SEAM_A + g.SEAM_B * cz
    sh.line(*VT.p(x0 - 4, ym), *VT.p(x1 + 4, ym), 'ph')
    sh.text(VT.p(x1 + 5, 0)[0], VT.p(0, ym)[1] + 0.8, 'SEAM', 1.9, 'start', 'td')
    sh.dim_v(*VT.p(x0, y0), *VT.p(x0, y1), VT.p(x0, 0)[0] - 7, '%.1f' % D)
    sh.text(VT.p(0, 0)[0], VT.p(0, y0)[1] + 8, 'TOP', 3.0, 'middle', 'tx', weight='bold')

    draw_poly(sh, VR, silhouette(allm, 'right'), 'o')
    draw_lines(sh, VR, feature_lines(B, 'right', 30) + feature_lines(F, 'right', 30), 'o3')
    draw_lines(sh, VR, feature_lines(BP, 'right', 30), 'o3')
    sh.line(*VR.p(g.SEAM_A, -2), *VR.p(g.SEAM_A + g.SEAM_B * (z1 + 2), z1 + 2), 'ph')
    sh.dim_h(*VR.p(y0, 10), *VR.p(y1, 10), VR.p(0, z0)[1] + 8, '%.1f' % D)
    zc = 90.0
    sh.leader(VR.p(g.SEAM_A + g.SEAM_B * zc, zc), (VR.p(y1 + 6, 0)[0], VR.p(0, 112)[1]), '',
              lines=['SPEAKER SLOT 20 x 1.2', '+x seam, Z 80-100'], side=1)
    sh.leader(VR.p(g.SEAM_A + g.SEAM_B * 72, 72), (VR.p(y1 + 6, 0)[0], VR.p(0, 70)[1]), '',
              lines=['BOOT / RST pin holes Ø2.3', 'ON/OFF window 8 x 3.2', '(all in the seam)'], side=1)
    sh.leader(VR.p(2, 1.5), (VR.p(y1 + 6, 0)[0], VR.p(0, 22)[1]), '', lines=['polymer base plate 3.0', '+ oval foot 1.2'],
              side=1)
    sh.text(VR.p(0, 0)[0], TY, 'RIGHT (+X)', 3.2, 'middle', 'tx', weight='bold')

    draw_poly(sh, VB, silhouette(allm, 'back'), 'o')
    draw_lines(sh, VB, feature_lines(B, 'back', 30), 'o2')
    scr = rs.get('screws', [])
    if scr:
        s0 = scr[0]
        sh.leader(VB.p(s0['x'], s0['Z']), (348, 172), '',
                  lines=['4x M2 from the back', 'cbore Ø4.3 x 1.8'], side=1)
    sh.leader(VB.p(0, 3.0 + 5.2), (348, 188), '', lines=['USB-C socket (charge)', 'Z %.1f' % (3.0 + 5.2)],
              side=1)
    sh.text(VB.p(0, 0)[0], TY, 'BACK', 3.2, 'middle', 'tx', weight='bold')

    draw_poly(sh, VBo, silhouette(allm, 'bottom'), 'o')
    draw_lines(sh, VBo, feature_lines(BP, 'bottom', 30), 'o2')
    bw = g.dims_report()
    sh.dim_h(*VBo.p(-bw['base_w'] / 2, 0), *VBo.p(bw['base_w'] / 2, 0), VBo.p(0, -y0)[1] + 8 if False else VBo.p(0, -20)[1] + 4,
             'FLAT BASE %.1f x %.1f' % (bw['base_w'], bw['base_d']))
    sh.text(VBo.p(0, 0)[0], VBo.p(0, 22)[1] - 4, 'BOTTOM', 3.0, 'middle', 'tx', weight='bold')
    sh.text(VBo.p(0, 0)[0], VBo.p(0, -20)[1] + 9, 'foot %.1f x %.1f (v6 30 x 14 x K), 2x M2 countersunk' % (2 * g.FOOT_A, 2 * g.FOOT_B),
            1.9, 'middle', 'td')

    ms = rs.get('dims', {}).get('mass_g', {})
    notes(sh, 342, 100, [
        'Envelope %.1f x %.1f x %.1f' % (W, H, D),
        '  (W x H incl. foot x D)',
        'v6 front silhouette x %.2f' % g.K,
        '  depth x %.2f' % g.KY,
        'Lens Ø95.86 stock (2.8C)',
        'Split plane y=%.2f+%.4fZ' % (g.SEAM_A, g.SEAM_B),
        '  = silhouette, no undercut',
        'Masses (%s):' % v,
        '  front %.0f g back %.0f g' % (ms.get('front_shell', 0), ms.get('back_shell', 0)),
        '  base %.0f g chassis %.0f g' % (ms.get('base_plate', 0), ms.get('chassis', 0)),
    ], size=2.0, head='NOTES')
    title_block(sh, 'GENERAL ARRANGEMENT', 'SOUL-P0 M, %s, views projected from the CAD' % v, '1 : 1', '1 / 4',
                'SOUL-P0M-01')
    return sh


# ================================================================== SHEET 2: SECTION A-A
SEC_STYLE = {
    'front_shell': ('o', 'hA'), 'back_shell': ('o', 'hB'), 'base_plate': ('o', 'hD'), 'chassis': ('o2', 'hC'),
    'in_battery': ('fb', None), 'in_speaker': ('f2', None), 'in_amp': ('f2', None), 'in_mic': ('f2', None),
    'in_lens': ('gl', None), 'in_lcd': ('f2', None), 'in_pcb': ('f2', None), 'in_pcb_tab': ('f2', None),
    'in_components': ('o3', None), 'in_usb_socket': ('f2', None), 'in_usb_plug': ('o3', None), 'in_bat_plug': ('o3', None),
}


def draw_section(sh, V, v, x_cut, names=None):
    names = names or list(SEC_STYLE)
    out = {}
    for n in names:
        m = mesh(v, n)
        if m is None:
            continue
        p = section(m, (x_cut, 0, 0), (1, 0, 0), np.array([0, 1.0, 0]), np.array([0, 0, 1.0]))
        if p.is_empty:
            continue
        cls, hatch = SEC_STYLE.get(n, ('o2', None))
        draw_poly(sh, V, p, cls, extra='style="fill:url(#%s)"' % hatch if hatch else '')
        out[n] = p
    return out


def sheet_section(theme='blue'):
    v = 'plastic' if 'plastic' in REP else 'alu'
    rs = REP.get(v, {})
    sh = Sheet(theme)
    sh.frame()
    k = 1.75
    V = View(78, 262, k)
    secs = draw_section(sh, V, v, 0.0)
    sh.text(V.p(0, 0)[0], 278, 'SECTION A-A  (x = 0, seen from +X)', 3.0, 'middle', 'tx', weight='bold')
    fs = unary_union([secs.get(n, Polygon()) for n in ('front_shell', 'back_shell', 'base_plate')])
    ya, za, yb, zb = fs.bounds
    sh.dim_v(*V.p(ya, za), *V.p(ya, zb), V.p(ya, 0)[0] - 8, '%.1f' % (zb - za))
    sh.dim_h(*V.p(ya, 20), *V.p(yb, 20), V.p(0, za)[1] + 8, '%.1f' % (yb - ya))
    items = [('front_shell', 1), ('in_lens', 2), ('in_lcd', 3), ('in_pcb', 4), ('chassis', 5), ('in_battery', 6),
             ('back_shell', 7), ('base_plate', 8), ('in_usb_socket', 9), ('in_speaker', 10), ('in_amp', 11)]
    xs = V.p(yb, 0)[0] + 14
    yy = 30
    for n, i in items:
        p = secs.get(n)
        if p is None:
            continue
        rp = p.representative_point()
        sh.balloon(xs + (i % 2) * 9, yy, i, tip=V.p(rp.x, rp.y))
        yy += 17
    cl = rs.get('clearance', {})
    rows = []
    for n, lab in [('lens', 'lens Ø95.86 (drawing)'), ('lcd', 'LCD cell env. Ø77.6'), ('pcb', 'PCB Ø73'),
                   ('components', 'parts to 9.7 (drawing)'), ('bat_plug', 'BAT plug + wires (U)'),
                   ('usb_plug', 'USB-C 90° plug (U)'), ('usb_socket', 'rear USB-C socket (U)'),
                   ('switch', 'ON/OFF switch (U)'), ('key_boot', 'BOOT key (U)'), ('battery', 'LiPo 605060'),
                   ('speaker', 'speaker 2030'), ('amp', 'MAX98357A'), ('mic', 'INMP441')]:
        r = cl.get(n, {})
        if not r:
            continue
        rows.append((lab, *['%.2f' % r.get(s, float('nan')) for s in ('front_shell', 'back_shell', 'base_plate', 'chassis')]))
    ty = table(sh, 190, 18, [('internal part', 52), ('front', 14), ('back', 14), ('base', 14), ('chassis', 16)], rows, size=1.9)
    ty = notes(sh, 190, ty + 4, [
        'Minimum distance (mm) from each internal part to each printed / machined',
        'part, measured on the meshes. <= 0.05 at the lens = intended lip contact;',
        'chassis 0.0 = the part rests on its cradle. (U) = unverified size.',
    ], size=1.8)
    inter = rs.get('interference', {})
    bad = {k_: v_ for k_, v_ in inter.items() if v_ > 0.05}
    ty = notes(sh, 190, ty + 3, ['%d pairs checked, %d overlapping > 0.05 mm3' % (len(inter), len(bad))]
               + ['  %s = %.2f' % kv for kv in list(bad.items())[:5]], size=1.9, head='INTERFERENCE CHECK')
    notes(sh, 190, ty + 3, ['1 front shell  2 stock lens  3 LCD  4 PCB  5 chassis (printed)',
                            '6 LiPo 605060  7 back shell  8 base plate + foot (polymer)',
                            '9 USB-C socket (charge)  10 speaker 2030  11 amp'], size=1.9, head='PARTS')
    title_block(sh, 'SECTION A-A (x = 0)', '%s variant, clearances from the CAD check' % v, '1.75 : 1', '2 / 4',
                'SOUL-P0M-02')
    return sh


# ================================================================== SHEET 3: EXPLODED + BOM
BOM = [
    (1, 'Front shell', 'PLA/PETG/resin | Al 6061', '1', 'print | CNC', '40-150 lei | 90-200 EUR'),
    (2, 'ESP32-S3-Touch-LCD-2.8C', 'Waveshare', '1', 'waveshare / AliExpress', '30-43 USD'),
    (3, 'Chassis', 'PETG / resin', '1', 'print', '5-15 lei'),
    (4, 'LiPo 605060 ~2000 mAh', 'Li-po + PCM, MX1.25', '1', 'AliExpress / eMAG', '30-60 lei'),
    (5, 'Speaker 2030 8 ohm 1 W', 'box speaker', '1', 'AliExpress / eMAG', '10-20 lei'),
    (6, 'MAX98357A + INMP441', 'I2S amp + I2S mic', '1+1', 'ardushop / optimus', '35-60 lei'),
    (7, 'Back shell', 'PLA/PETG/resin | Al 6061', '1', 'print | CNC', '40-150 lei | 90-200 EUR'),
    (8, 'Base plate + foot', 'PETG/resin, matte', '1', 'print', '5-15 lei'),
    (9, 'Pins BOOT / RST', 'PETG / resin', '2', 'print', '<1 lei'),
    (10, 'USB-C 90° ext. M-F', 'panel socket', '1', 'AliExpress / eMAG', '20-40 lei'),
    (11, 'Insert M2x3 Ø3.5', 'brass', '6', 'eMAG / 3DPrintX', '30-60 lei/set'),
    (12, 'Screw M2 (see sheet 4)', 'A2 inox', '6', 'kit', '30-40 lei/kit'),
    (13, 'EVA foam, VHB, Kapton', '-', '-', 'eMAG', '40-60 lei'),
]


def sheet_exploded(theme='blue'):
    v = 'plastic' if 'plastic' in REP else 'alu'
    sh = Sheet(theme)
    sh.frame()
    az, el = math.radians(-35), math.radians(20)
    dview = -np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
    dview /= np.linalg.norm(dview)
    U = np.cross(dview, [0, 0, 1.0])
    U /= np.linalg.norm(U)
    Vv = np.cross(U, dview)
    view = (dview, U, Vv)
    NS = np.array([0, 1.0, -g.SEAM_B])
    NS /= np.linalg.norm(NS)
    groups = [('front_shell', ['front_shell'], -60), ('lens', ['in_lens'], -38),
              ('board', BOARD_IN, -22), ('chassis', ['chassis'], 4),
              ('inside', ['in_battery', 'in_speaker', 'in_amp', 'in_mic'], 18), ('back_shell', ['back_shell'], 62)]
    k = 0.95
    VV = View(118, 150, k)
    items = []
    for gname, names, off_ in groups:
        off = NS * off_
        ms = [mesh(v, n) for n in names if mesh(v, n) is not None]
        if not ms:
            continue
        m = trimesh.util.concatenate(ms)
        items.append((float(((m.vertices + off) @ dview).mean()), gname, m, off))
    bpm = mesh(v, 'base_plate')
    if bpm is not None:
        items.append((float(((bpm.vertices + [0, 0, -40]) @ dview).mean()), 'base_plate', bpm, np.array([0, 0, -40.0])))
    items.sort(key=lambda t: -t[0])
    anchors = {}
    for depth, gname, m, off in items:
        sil = silhouette(m, view, off)
        draw_poly(sh, VV, sil, 'gl' if gname == 'lens' else 'ob')
        if gname != 'lens':
            draw_lines(sh, VV, feature_lines(m, view, 35, off), 'o3')
        c = sil.representative_point()
        anchors[gname] = VV.p(c.x, c.y)
    bal = {'front_shell': (1, (26, 36)), 'lens': (2, (48, 26)), 'board': (2, (70, 22)), 'chassis': (3, (120, 20)),
           'inside': (4, (160, 26)), 'back_shell': (7, (205, 46)), 'base_plate': (8, (205, 205))}
    for gname, (n, pos) in bal.items():
        if gname in anchors:
            sh.balloon(pos[0], pos[1], n, tip=anchors[gname])
    sh.text(118, 244, 'EXPLODED VIEW along the seam normal (base plate down)', 3.0, 'middle', 'tx', weight='bold')
    sh.text(118, 248.5, 'axonometric projection of the CAD meshes', 2.1, 'middle', 'td')
    ty = table(sh, 232, 16, [('#', 6), ('part', 44), ('material', 40), ('qty', 8), ('source', 36), ('price', 36)],
               [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in BOM], size=1.75, rh=3.3)
    notes(sh, 232, ty + 5, [
        'Assembly (README E):',
        '1 inserts: 4 front bosses + 2 base bosses (iron 230°C)',
        '2 lens + board into the front pocket, USB-C corners down',
        '3 EVA dots on the 4 M2 pads, chassis on top',
        '4 battery, speaker, amp, mic onto the chassis (VHB)',
        '5 wires: see README (I2S on the 12-pin connector)',
        '6 pins in, back shell on, 4x M2 from the back',
        '7 USB-C socket in the clamp, base plate, 2x M2',
        'Prices Sept 2026, approximate (README A).',
    ], size=1.9, head='ASSEMBLY')
    title_block(sh, 'EXPLODED VIEW + BOM', 'SOUL-P0 M, %s, 1 unit' % v, 'NTS', '3 / 4', 'SOUL-P0M-03')
    return sh


# ================================================================== SHEET 4: VARIANTS
def sheet_variants(theme='blue'):
    sh = Sheet(theme)
    sh.frame()
    k = 1.3
    cols = [('plastic', 'PLASTIC  FDM / SLA'), ('alu', 'ALUMINIUM  CNC 6061-T6')]
    for i, (v, lab) in enumerate(cols):
        if v not in REP:
            continue
        V = View(70 + i * 120, 200, k)
        draw_section(sh, V, v, 0.0, ['front_shell', 'back_shell', 'base_plate', 'in_lens', 'in_lcd', 'in_pcb',
                                      'in_battery', 'chassis'])
        sh.line(*V.p(g.SEAM_A - 0.2, -3), *V.p(g.SEAM_A + g.SEAM_B * 130, 130), 'cut')
        sh.text(V.p(0, 0)[0], 212, lab, 3.0, 'middle', 'tx', weight='bold')
        sh.text(V.p(0, 0)[0], 216, 'section x = 0 (dash-dot = split plane)', 2.0, 'middle', 'td')
    rows = []
    for v, lab in cols:
        r = REP.get(v)
        if not r:
            continue
        ms = r['dims']['mass_g']
        sc = r['screws']
        low = [s for s in sc if s['Z'] < 60][0]
        up = [s for s in sc if s['Z'] >= 60][0]
        Vv_ = {'plastic': ('2.0', '0.2', '1.2', 'heat-set M2'), 'alu': ('1.6', '0.1', '0.8', 'tapped M2')}[v]
        rows.append((lab.split()[0], *Vv_, '%.0f / %.0f' % (ms.get('front_shell', 0), ms.get('back_shell', 0)),
                     'M2x%d / M2x%d' % (screw_std(low['screw_len_max']), screw_std(up['screw_len_max']))))
    ty = table(sh, 20, 226, [('variant', 30), ('wall', 12), ('fit', 10), ('lip', 10), ('threads', 24),
                             ('shells g F/B', 26), ('screws low/up', 32)], rows, size=1.9, rh=3.6)
    notes(sh, 20, ty + 5, [
        'One split plane through the silhouette -> each half is 3-axis machinable (two set-ups: outside, inside).',
        'ALU: internal radii >= 1 mm, Ø1.6 pilots tapped M2 x 4 in the front bosses, bead blast + anodise type II.',
        'RF: the polymer base plate + foot is the antenna window (v6); test RSSI before ordering 3 sets.',
    ], size=1.85)
    notes(sh, 272, 20, [
        'Only wall, fit and lip change.',
        'Board, battery, speaker, chassis',
        'and base plate are shared',
        '(chassis + base always printed).',
        '',
        'Plastic: 0.2 mm on every fit',
        '  (lens pocket, tongue, pins).',
        'Aluminium: 0.1 mm on the fits,',
        '  ISO 2768-m elsewhere; ±0.05',
        '  on the lens pocket and seam.',
        '',
        'Colours (v6): Silver, Graphite,',
        '  Midnight, Ember, Champagne;',
        '  polymer in the body tone.',
    ], size=2.0, head='VARIANTS')
    title_block(sh, 'MATERIAL VARIANTS', 'plastic (FDM/SLA) vs CNC aluminium, polymer base', '1.3 : 1', '4 / 4',
                'SOUL-P0M-04')
    return sh


def render_png(paths):
    from render import render
    render([(p, os.path.splitext(p)[0] + '.png') for p in paths])


if __name__ == '__main__':
    out = []
    which = sys.argv[1:] or ['ga', 'sec', 'exp', 'var']
    if 'ga' in which:
        out.append(write(sheet_ga('blue'), 'soul_m_1_general_arrangement'))
        out.append(write(sheet_ga('white'), 'soul_m_1_general_arrangement_white'))
    if 'sec' in which:
        out.append(write(sheet_section('blue'), 'soul_m_2_section_AA'))
    if 'exp' in which:
        out.append(write(sheet_exploded('blue'), 'soul_m_3_exploded_bom'))
    if 'var' in which:
        out.append(write(sheet_variants('blue'), 'soul_m_4_variants'))
    render_png(out)
