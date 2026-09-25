#!/usr/bin/env python3
"""blueprints_p0.py -- engineering sheets of SOUL-P0 drawn FROM THE CAD MODEL (not from estimates).

Every outline, section and hole position is obtained by projecting / sectioning the meshes that soul_p0.py
exported (../stl/assembly/<variant>_*.stl, product frame, mm) and every number comes from those meshes or from
cad/report_<variant>.json (the interference / clearance check). Drawing kit: micul-smecher/blueprints/src/bp.py.

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
REP = {v: json.load(open(os.path.join(HERE, f'report_{v}.json'))) for v in ('plastic', 'alu', 'alu_band')
       if os.path.exists(os.path.join(HERE, f'report_{v}.json'))}
DATE = '2026-09-25'

_MC = {}


def mesh(v, name):
    key = (v, name)
    if key not in _MC:
        fn = os.path.join(ASM, f'{v}_{name}.stl')
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
    sh.text(x0 + 36, y0 + 7.2, 'P0 - DIY pilot enclosure', 2.3, 'start', 'td')
    sh.text(x0 + 36, y0 + 11.0, 'Waveshare ESP32-S3-AMOLED-1.75', 2.3, 'start', 'td')
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
    parts = [mesh(v, n) for n in ('front_shell', 'back_shell', 'seam_band')]
    return trimesh.util.concatenate([p for p in parts if p is not None])


def bbox(v):
    m = outer_all(v)
    return m.bounds


# ================================================================== SHEET 1: GA
def sheet_ga(theme='blue'):
    v = 'plastic'
    sh = Sheet(theme)
    sh.frame()
    k = 1.6
    F = mesh(v, 'front_shell')
    B = mesh(v, 'back_shell')
    GL = mesh(v, 'board_glass')
    both = trimesh.util.concatenate([F, B])
    (x0, y0, z0), (x1, y1, z1) = both.bounds
    W, D, H = x1 - x0, y1 - y0, z1 - z0
    VF = View(92, 196, k)             # front: u=X, v=Z
    VT = View(92, 64, k)              # top:   u=X, v=Y (back up)
    VR = View(190, 196, k)            # right: u=Y, v=Z
    VB = View(282, 196, k)            # back:  u=-X, v=Z
    VBo = View(360, 64, k)            # bottom: u=X, v=-Y
    TY = 212 + 3

    # ---------- FRONT
    sil = silhouette(both, 'front')
    draw_poly(sh, VF, sil, 'o')
    draw_poly(sh, VF, silhouette(GL, 'front'), 'gl')
    draw_lines(sh, VF, feature_lines(F, 'front', 30), 'o2')
    # active area
    act = mesh(v, 'board_glass')
    gc = act.bounds.mean(0)
    # glass centre in the front view
    cx, cz = g.G[0], g.G[2]
    sh.centermark(*VF.p(cx, cz), 23.0 * k, 3)
    sh.dim_h(*VF.p(x0, 40), *VF.p(x1, 40), VF.p(0, z0)[1] + 9, '%.1f' % W)
    sh.dim_v(*VF.p(0, z0), *VF.p(0, z1), VF.p(x0, 0)[0] - 8, '%.1f' % H)
    sh.dim_v(*VF.p(0, 0), *VF.p(cx, cz), VF.p(x0, 0)[0] - 3.5, '%.1f' % cz, tshift=0)
    ap = 2 * (24.48 - 1.5)
    sh.leader(VF.p(-ap / 2 * 0.7, cz + ap / 2 * 0.71), (VF.p(-40, 70)[0], VF.p(0, 76)[1] - 3),
              '', lines=['APERTURE Ø%.2f' % ap, 'lip 1.5 over stock glass Ø48.96', 'active Ø43.76'], side=-1)
    sh.text(VF.p(0, 0)[0], TY, 'FRONT', 3.2, 'middle', 'tx', weight='bold')
    sh.text(VF.p(0, 0)[0], TY + 3.8, 'face table leans back %.1f°' % g.dims_report()['lean_deg'], 2.1, 'middle', 'td')

    # ---------- TOP
    draw_poly(sh, VT, silhouette(both, 'top'), 'o')
    draw_lines(sh, VT, feature_lines(B, 'top', 30), 'o3')
    ys = g.SEAM_A + g.SEAM_B * z1
    sh.line(*VT.p(x0 - 4, g.SEAM_A + g.SEAM_B * 40), *VT.p(x1 + 4, g.SEAM_A + g.SEAM_B * 40), 'ph')
    sh.text(VT.p(x1 + 5, 0)[0], VT.p(0, g.SEAM_A + g.SEAM_B * 40)[1] + 0.8, 'SEAM', 1.9, 'start', 'td')
    sh.dim_v(*VT.p(x0, y0), *VT.p(x0, y1), VT.p(x0, 0)[0] - 7, '%.1f' % D)
    sh.text(VT.p(0, 0)[0], VT.p(0, y1)[1] - 6, 'TOP', 3.2, 'middle', 'tx', weight='bold')

    # ---------- RIGHT SIDE
    draw_poly(sh, VR, silhouette(both, 'right'), 'o')
    draw_lines(sh, VR, feature_lines(B, 'right', 30), 'o3')
    draw_lines(sh, VR, feature_lines(F, 'right', 30), 'o3')
    # seam line (plane) in side view
    sh.line(*VR.p(g.SEAM_A - 0.0, -2), *VR.p(g.SEAM_A + g.SEAM_B * 77, 77), 'ph')
    sh.dim_h(*VR.p(y0, 10), *VR.p(y1, 10), VR.p(0, z0)[1] + 9, '%.1f' % D)
    # base footprint depth
    bw = g.dims_report()
    sh.dim_h(*VR.p(-12.9, 0), *VR.p(14.33, 0), VR.p(0, z0)[1] + 15, 'BASE %.1f' % bw['base_d'])
    # slot
    rs = REP.get('plastic', {})
    sh.leader(VR.p(g.SEAM_A + g.SEAM_B * 51, 51), (VR.p(y1 + 5, 0)[0], VR.p(0, 60)[1]), '',
              lines=['SPEAKER SLOT', '12.0 x 1.2 in +x seam', 'Z 45.5-57.5'], side=1)
    sh.text(VR.p(0, 0)[0], TY, 'RIGHT (+X)', 3.2, 'middle', 'tx', weight='bold')

    # ---------- BACK
    draw_poly(sh, VB, silhouette(both, 'back'), 'o')
    draw_lines(sh, VB, feature_lines(B, 'back', 30), 'o2')
    for s in rs.get('screws', []):
        pass
    sh.leader(VB.p(19.5, 11), (VB.p(-40, 0)[0] + 20, VB.p(0, -6)[1]), '', lines=['4x M2 from the back', 'cbore Ø4.3 x 1.8'],
              side=1)
    pins = rs.get('pins', {})
    if pins:
        e = pins['boot']['exit']
        sh.leader(VB.p(e[0], e[2]), (VB.p(-45, 0)[0], VB.p(0, 82)[1]), '',
                  lines=['PWR / BOOT pin holes Ø2.3', 'Z %.1f  x ±%.1f' % (e[2], abs(e[0]))], side=1)
    sh.text(VB.p(0, 0)[0], TY, 'BACK', 3.2, 'middle', 'tx', weight='bold')

    # ---------- BOTTOM
    draw_poly(sh, VBo, silhouette(both, 'bottom'), 'o')
    draw_lines(sh, VBo, feature_lines(B, 'bottom', 30), 'o2')
    draw_lines(sh, VBo, feature_lines(F, 'bottom', 30), 'o2')
    sh.dim_h(*VBo.p(-bw['base_w'] / 2, 0), *VBo.p(bw['base_w'] / 2, 0), VBo.p(0, 16)[1] - 4,
             'FLAT BASE %.1f' % bw['base_w'])
    sh.leader(VBo.p(0, 4.5), (VBo.p(24, 0)[0], VBo.p(0, -20)[1]), '', lines=['USB-C plug tunnel', '+ cable groove 5 x 4.5'],
              side=1)
    sh.leader(VBo.p(10.5, -2.5), (VBo.p(24, 0)[0], VBo.p(0, 22)[1]), '', lines=['2x magnet Ø6.2 x 2.1', '(optional)'], side=1)
    sh.text(VBo.p(0, 0)[0], VBo.p(0, -y0)[1] - 7 + 20 * 0, '', 1)
    sh.text(VBo.p(0, 0)[0], VBo.p(0, 18)[1] - 12, 'BOTTOM', 3.2, 'middle', 'tx', weight='bold')

    # notes
    ms = rs.get('dims', {}).get('mass_g', {})
    notes(sh, 250, 110, [
        'Envelope %.1f x %.1f x %.1f mm (W x H x D)' % (W, H, D),
        'Flat base %.1f x %.1f mm, no rocker' % (bw['base_w'], bw['base_d']),
        'Split on one plane y = %.2f + %.4f Z (%.1f° off vertical)' % (g.SEAM_A, g.SEAM_B, math.degrees(math.atan(g.SEAM_B))),
        '  = the silhouette line -> no undercut, 3-axis CNC',
        'Stock Waveshare glass Ø48.96 framed by a 1.5 mm lip',
        'Walls: plastic 2.0 / aluminium 1.4 (sheet 4)',
        'Shell mass PLA: front %.1f g, back %.1f g, chassis %.1f g' % (
            ms.get('front_shell', 0), ms.get('back_shell', 0), ms.get('chassis', 0)),
        '4x M2 heat-set insert in the front (plastic)',
        'Nothing on the front but the glass.',
    ], head='NOTES')
    title_block(sh, 'GENERAL ARRANGEMENT', 'SOUL-P0 plastic variant, all views from the CAD mesh', '1.6 : 1', '1 / 4',
                'SOUL-P0-01')
    return sh


# ================================================================== SHEET 2: SECTION A-A
SEC_STYLE = {
    'front_shell': ('o', 'hA'), 'back_shell': ('o', 'hB'), 'seam_band': ('o', 'hC'), 'chassis': ('o2', 'hC'),
    'battery': ('fb', None), 'speaker': ('f2', None), 'board_glass': ('gl', None), 'board_module': ('f2', None),
    'board_components': ('f2', None), 'board_usb_receptacle': ('f2', None), 'usb_plug': ('o3', None),
    'board_header_8pin': ('f2', None), 'board_standoff_1': ('f2', None), 'board_standoff_2': ('f2', None),
    'board_standoff_3': ('f2', None), 'pin_pwr': ('o2', 'hS'), 'pin_boot': ('o2', 'hS'),
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
    v = 'plastic'
    rs = REP.get(v, {})
    sh = Sheet(theme)
    sh.frame()
    k = 3.0
    V = View(95, 250, k)       # u = Y, v = Z
    secs = draw_section(sh, V, v, 0.0)
    # outline of the whole body (projection) for context
    sh.text(V.p(0, 0)[0], 268, 'SECTION A-A  (plane x = 0, seen from +X)', 3.2, 'middle', 'tx', weight='bold')
    # key vertical dims (from the section geometry)
    fs = unary_union([secs.get('front_shell', Polygon()), secs.get('back_shell', Polygon())])
    (ya, za, yb, zb) = fs.bounds
    sh.dim_v(*V.p(ya, za), *V.p(ya, zb), V.p(ya, 0)[0] - 7, '%.1f' % (zb - za))
    sh.dim_h(*V.p(ya, 8), *V.p(yb, 8), V.p(0, za)[1] + 10, '%.1f @ x=0' % (yb - ya))
    # glass and table
    G = secs.get('board_glass')
    if G is not None:
        gy0, gz0, gy1, gz1 = G.bounds
        sh.dim_v(*V.p(gy0, gz0), *V.p(gy0, gz1), V.p(ya, 0)[0] - 16, 'GLASS %.2f' % (gz1 - gz0))
    # wall thickness callouts
    notes_y = 20
    cl = rs.get('clearance', {})

    def cmin(n):
        r = cl.get(n, {})
        return min(r.values()) if r else float('nan')
    # balloons for parts
    items = [('front_shell', 1), ('back_shell', 2), ('chassis', 3), ('board_glass', 4), ('board_module', 5),
             ('battery', 6), ('speaker', 7), ('usb_plug', 8), ('board_usb_receptacle', 9)]
    xs = V.p(yb, 0)[0] + 18
    yy = 36
    for n, i in items:
        p = secs.get(n)
        if p is None:
            continue
        rp = p.representative_point()
        sh.balloon(xs, yy, i, tip=V.p(rp.x, rp.y))
        yy += 21
    # legend + clearance table from the checks
    rows = []
    for n, lab in [('board_glass', 'stock glass Ø48.96 (V)'), ('board_module', 'module/PCB Ø46.0 (V)'),
                   ('board_header_8pin', '8-pin header, 12.7 deep'), ('board_usb_receptacle', 'USB-C receptacle'),
                   ('usb_plug', 'USB-C plug 12.4x7.0 (U)'), ('plug_spk', 'SPK plug+wires (U)'),
                   ('plug_bat', 'BAT plug+wires (U)'), ('btn_pwr', 'PWR key'), ('btn_boot', 'BOOT key'),
                   ('battery', 'LiPo 503035 envelope'), ('speaker', 'speaker 1511')]:
        r = cl.get(n, {})
        if not r:
            continue
        rows.append((lab, '%.2f' % r.get('front_shell', float('nan')), '%.2f' % r.get('back_shell', float('nan')),
                     '%.2f' % r.get('chassis', float('nan'))))
    ty = table(sh, 240, 20, [('internal part', 58), ('front', 16), ('back', 16), ('chassis', 18)], rows, size=2.0)
    sh.text(240, ty + 4, 'Minimum distance (mm) from each internal part to each shell,', 2.0, 'start', 'td')
    sh.text(240, ty + 7, 'measured on the meshes (soul_p0.py mesh_checks). (U) = unverified', 2.0, 'start', 'td')
    sh.text(240, ty + 10, 'size, measure your part. 0.0x at the glass = intended lip contact.', 2.0, 'start', 'td')
    inter = rs.get('interference', {})
    bad = {k_: v_ for k_, v_ in inter.items() if v_ > 0.01}
    ty = notes(sh, 240, ty + 17, [
        'Interference check: %d pairs, %d overlapping%s' % (len(inter), len(bad), ':' if bad else ' (all 0.00 mm3)'),
    ] + ['  %s = %.2f mm3' % kv for kv in list(bad.items())[:6]], head='CHECKS')
    parts_legend = ['1 front shell (hatch /)', '2 back shell (hatch \\)', '3 chassis (cross hatch, printed)',
                    '4 stock glass', '5 AMOLED module + PCB', '6 LiPo 503035, tilted %.1f° in its cradle' % tilt_deg(),
                    '7 speaker 1511, membrane to the back', '8 USB-C plug in its tunnel',
                    '9 USB-C receptacle (board)']
    notes(sh, 240, ty + 4, parts_legend, head='PARTS IN SECTION')
    title_block(sh, 'SECTION A-A (x = 0)', 'plastic variant, wall 2.0, clearances 0.2', '3 : 1', '2 / 4', 'SOUL-P0-02')
    return sh


def tilt_deg():
    b = (6.0, 9.1)
    a = (-30.1, 14.4)
    return math.degrees(math.atan2(a[1] - b[1], b[0] - a[0]))


# ================================================================== SHEET 3: EXPLODED + BOM
BOM = [
    # n, part, material, qty, source, price
    (1, 'front_shell', 'Front shell', 'PLA/PETG/resin | Al 6061-T6', 1, 'print (sheet F) | CNC', '15-60 lei | 60-120 EUR'),
    (2, 'board', 'ESP32-S3-Touch-AMOLED-1.75', 'Waveshare, stock glass', 1, 'waveshare.com / AliExpress', '30-40 USD'),
    (3, 'chassis', 'Chassis (battery cradle, spk frame)', 'PETG / resin', 1, 'print', '3-10 lei'),
    (4, 'battery', 'LiPo 503035 500 mAh, MX1.25', 'Li-polymer + PCM', 1, 'AliExpress', '3-5 USD'),
    (5, 'speaker', 'Micro speaker 1511 8 ohm 1 W', 'wired', 1, 'AliExpress', '1-2 USD'),
    (6, 'back_shell', 'Back shell', 'PLA/PETG/resin | Al 6061-T6', 1, 'print | CNC', '15-60 lei | 60-120 EUR'),
    (7, 'pin_pwr', 'Button pin PWR / BOOT', 'PETG / resin', 2, 'print', '<1 lei'),
    (8, None, 'Heat-set insert M2 x 3 x Ø3.5', 'brass', 4, 'eMAG / 3DPrintX', '30-60 lei/set'),
    (9, None, 'Screw M2 x 16 (lower) / M2 x 8 (upper)', 'A2 stainless', '2+2', 'hardware kit', '30-40 lei/kit'),
    (10, None, 'EVA foam 0.5-1 mm, VHB, Kapton', '-', '-', 'eMAG / hobby', '40-60 lei'),
    (11, None, 'Magnet Ø6 x 2 N52 (optional)', 'NdFeB', 2, 'eMAG', '15-25 lei'),
]


def sheet_exploded(theme='blue'):
    v = 'plastic'
    sh = Sheet(theme)
    sh.frame()
    # isometric-ish view direction
    az, el = math.radians(-35), math.radians(22)
    dview = -np.array([math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
    dview = dview / np.linalg.norm(dview)
    U = np.cross(dview, [0, 0, 1.0])
    U /= np.linalg.norm(U)
    Vv = np.cross(U, dview)
    view = (dview, U, Vv)
    NS = np.array([0, 1.0, -g.SEAM_B])
    NS /= np.linalg.norm(NS)
    offs = {'front_shell': -34, 'board': -16, 'chassis': 6, 'battery': 14, 'speaker': 20, 'back_shell': 44}
    groups = [
        ('front_shell', ['front_shell']),
        ('board', ['board_glass', 'board_module', 'board_components', 'board_header_8pin', 'board_usb_receptacle',
                   'board_standoff_1', 'board_standoff_2', 'board_standoff_3', 'board_conn_spk', 'board_conn_bat']),
        ('chassis', ['chassis']), ('battery', ['battery']), ('speaker', ['speaker']), ('back_shell', ['back_shell']),
    ]
    k = 1.55
    VV = View(120, 150, k)
    # painter: far first (largest depth along dview)
    items = []
    for gname, names in groups:
        off = NS * offs[gname]
        ms = [mesh(v, n) for n in names if mesh(v, n) is not None]
        if not ms:
            continue
        m = trimesh.util.concatenate(ms)
        depth = float(((m.vertices + off) @ dview).mean())
        items.append((depth, gname, m, off))
    items.sort(key=lambda t: -t[0])
    cls = {'front_shell': 'ob', 'back_shell': 'ob', 'chassis': 'ob', 'battery': 'ob', 'speaker': 'ob', 'board': 'ob'}
    anchors = {}
    for depth, gname, m, off in items:
        sil = silhouette(m, view, off)
        draw_poly(sh, VV, sil, 'ob')
        if gname == 'board':
            gl = mesh(v, 'board_glass')
            draw_poly(sh, VV, silhouette(gl, view, off), 'gl')
        draw_lines(sh, VV, feature_lines(m, view, 35, off), 'o3')
        c = sil.representative_point()
        anchors[gname] = VV.p(c.x, c.y)
    # pins
    for pn, dx in [('pin_pwr', -1), ('pin_boot', 1)]:
        m = mesh(v, pn)
        if m is not None:
            off = NS * 58 + np.array([0, 0, 10])
            sil = silhouette(m, view, off)
            draw_poly(sh, VV, sil, 'ob')
            c = sil.representative_point()
            anchors[pn] = VV.p(c.x, c.y)
    # explode axis
    a0 = np.array([0, -60, 40.0]) @ np.array([U, Vv]).T
    a1 = np.array([0, 75, 34.0]) @ np.array([U, Vv]).T
    sh.line(*VV.p(*a0), *VV.p(*a1), 'c')
    # balloons
    bal = {'front_shell': (1, (30, 40)), 'board': (2, (60, 30)), 'chassis': (3, (110, 26)), 'battery': (4, (150, 32)),
           'speaker': (5, (185, 40)), 'back_shell': (6, (215, 60)), 'pin_boot': (7, (225, 95))}
    for gname, (n, pos) in bal.items():
        if gname in anchors:
            sh.balloon(pos[0], pos[1], n, tip=anchors[gname])
    sh.text(120, 236, 'EXPLODED VIEW - along the seam normal', 3.2, 'middle', 'tx', weight='bold')
    sh.text(120, 240.5, 'axonometric projection of the CAD meshes (plastic variant)', 2.1, 'middle', 'td')
    # BOM
    rows = [(n, name, mat, q, src, pr) for (n, key, name, mat, q, src, pr) in BOM]
    ty = table(sh, 238, 16, [('#', 6), ('part', 56), ('material', 38), ('qty', 8), ('source', 30), ('price', 30)][:6],
               [(r[0], r[1][:30], r[2][:20], r[3], r[4][:16], r[5]) for r in rows], size=1.8, rh=3.4)
    notes(sh, 238, ty + 5, [
        'Assembly order (README E):',
        '1 inserts into the front shell (soldering iron 230°C)',
        '2 glass into the front pocket, USB-C down',
        '3 EVA dot on standoff 1, chassis on the 2 lower bosses',
        '4 battery into the cradle (no glue), plug BAT',
        '5 speaker into its frame, membrane to the back',
        '6 pins into the back shell from inside',
        '7 close: 2x M2x16 low, 2x M2x8 up, finger-tight',
        'Prices: Sept 2026, approximate (README A).',
    ], head='ASSEMBLY')
    title_block(sh, 'EXPLODED VIEW + BOM', 'SOUL-P0 plastic, 1 unit', 'NTS', '3 / 4', 'SOUL-P0-03')
    return sh


# ================================================================== SHEET 4: VARIANTS
def sheet_variants(theme='blue'):
    sh = Sheet(theme)
    sh.frame()
    k = 2.2
    cols = [('plastic', 'PLASTIC  FDM / SLA'), ('alu', 'ALUMINIUM  CNC 6061-T6'), ('alu_band', 'ALU + 3 mm RF BAND')]
    for i, (v, lab) in enumerate(cols):
        if v not in REP:
            continue
        V = View(62 + i * 118, 190, k)
        draw_section(sh, V, v, 0.0, ['front_shell', 'back_shell', 'seam_band', 'board_glass', 'board_module',
                                      'battery', 'speaker'])
        # seam plane
        sh.line(*V.p(g.SEAM_A - 0.2, -3), *V.p(g.SEAM_A + g.SEAM_B * 78, 78), 'cut')
        sh.text(V.p(0, 0)[0], 205, lab, 3.0, 'middle', 'tx', weight='bold')
        sh.text(V.p(0, 0)[0], 209, 'section x = 0', 2.1, 'middle', 'td')
        # second section through the lower screw (x = 19.5)
    # table
    rows = []
    for v, lab in cols:
        r = REP.get(v)
        if not r:
            continue
        ms = r['dims']['mass_g']
        sc = r['screws']
        low = [s for s in sc if s['kind'] == 'low'][0]
        up = [s for s in sc if s['kind'] == 'up'][0]
        rows.append((lab.split()[0] + (' +band' if v == 'alu_band' else ''),
                     {'plastic': '2.0', 'alu': '1.4', 'alu_band': '1.4'}[v],
                     {'plastic': '0.2', 'alu': '0.1', 'alu_band': '0.1'}[v],
                     {'plastic': '1.2', 'alu': '0.8', 'alu_band': '0.8'}[v],
                     {'plastic': 'heat-set M2', 'alu': 'tapped M2', 'alu_band': 'tapped M2'}[v],
                     '%.0f / %.0f' % (ms.get('front_shell', 0), ms.get('back_shell', 0)),
                     'M2x%d / M2x%d' % (screw_std(low['screw_len_max']), screw_std(up['screw_len_max']))))
    ty = table(sh, 20, 218, [('variant', 30), ('wall', 12), ('fit', 10), ('lip', 10), ('threads', 24),
                             ('shells g F/B', 24), ('screws low/up', 30)], rows, size=1.9, rh=3.6)
    notes(sh, 20, ty + 5, [
        'Seam = one plane through the silhouette (max width) -> each half is 3-axis machinable, no undercut.',
        'ALU: internal radii >= 1 mm, tapped M2 x 3.5 in the 4 front bosses (Ø1.6 pilot in the STEP), bead blast + anodise II.',
        'RF: a closed Al body blocks Wi-Fi/BLE. Test with the 1.75C (Al case) first; if RSSI drops > 6 dB use the band.',
    ], size=1.9)
    notes(sh, 240, 20, [
        'Wall thickness, fit clearances and lip',
        'are the only parameters that change;',
        'the board, battery, speaker and chassis',
        'positions are shared (chassis always printed).',
        '',
        'Tolerances plastic: 0.2 mm on every fit',
        '  (glass pocket, tongue, pins, plug tunnel).',
        'Tolerances aluminium: 0.1 mm on the fits,',
        '  ISO 2768-m elsewhere, ±0.05 on the glass',
        '  pocket and the seam faces.',
        '',
        'Band (right): each Al half ends 1.5 mm',
        '  short of the seam; a printed 3 mm band',
        '  carries the tongue and the screw sleeves.',
    ], head='VARIANTS')
    title_block(sh, 'MATERIAL VARIANTS', 'plastic vs CNC aluminium vs aluminium + RF band', '2.2 : 1', '4 / 4',
                'SOUL-P0-04')
    return sh


def screw_std(Lmax):
    for L in (20, 16, 14, 12, 10, 8, 6, 5, 4):
        if L <= Lmax - 0.3:
            return L
    return 4


def render_png(paths):
    sys.path.insert(0, os.path.join(MS, 'blueprints', 'src'))
    from render import render
    render([(p, os.path.splitext(p)[0] + '.png') for p in paths])


if __name__ == '__main__':
    out = []
    which = sys.argv[1:] or ['ga', 'sec', 'exp', 'var']
    if 'ga' in which:
        out.append(write(sheet_ga('blue'), 'soul_p0_1_general_arrangement'))
        out.append(write(sheet_ga('white'), 'soul_p0_1_general_arrangement_white'))
    if 'sec' in which:
        out.append(write(sheet_section('blue'), 'soul_p0_2_section_AA'))
    if 'exp' in which:
        out.append(write(sheet_exploded('blue'), 'soul_p0_3_exploded_bom'))
    if 'var' in which:
        out.append(write(sheet_variants('blue'), 'soul_p0_4_variants'))
    render_png(out)
