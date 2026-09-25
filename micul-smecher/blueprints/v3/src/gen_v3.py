"""Generate the SOUL v3 ("the amulet") blueprint sheets (SVG).

    python3 gen_v3.py ga sec exp pro     # then: python3 ../../src/render.py ../*.svg

Reuses the v2 drafting kit (../../src/bp.py) and the axonometric helpers of ../../src/gen_sheets.py.
Geometry source: research/07-amulet-design-language (section 3.3 + 5: v3 spec) and the
STEP-verified Waveshare 1.75" board data (cad/README.md, research/06).
(V) = verified STEP, (K) = spec sheet / background knowledge, (E) = engineering estimate.
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'src'))
import bp
from bp import *
from gen_sheets import Axo, hull   # reused axonometric helpers (v2 generator)

OUT = os.path.abspath(os.path.join(HERE, '..'))


class Sheet3(bp.Sheet):
    """Same sheet furniture as v2, v3 wording in the title block."""

    def title_block(self, title, variant, scale, sheet, dwg, x0=240, y0=241, w=170, h=46):
        self.rect(x0, y0, w, h, 'tbf')
        c1 = x0 + 92
        c2 = c1 + 39
        r1 = y0 + 17
        r2 = y0 + 32
        self.line(c1, y0, c1, y0 + h, 'fr2t')
        self.line(c2, y0, c2, y0 + h, 'fr2t')
        self.line(x0, r1, x0 + w, r1, 'fr2t')
        self.line(x0, r2, x0 + w, r2, 'fr2t')

        def cell(x, y, label, value, vs=3.3, bold=True):
            self.text(x + 1.4, y + 3.0, label, 1.8, 'start', 'td')
            self.text(x + 1.4, y + 3.2 + vs + 1.8, value, vs, 'start', 'tx', weight='bold' if bold else None)

        self.text(x0 + 3, y0 + 12.8, 'SOUL', 10.5, 'start', 'tx', weight='bold', extra='letter-spacing="1.2"')
        self.text(x0 + 36, y0 + 7.2, 'v3 · the amulet', 2.3, 'start', 'td')
        self.text(x0 + 36, y0 + 11.0, 'round eye in a frame, crown at 12', 2.3, 'start', 'td')
        self.text(x0 + 36, y0 + 14.8, 'DWG ' + dwg, 2.3, 'start', 'td')
        cell(x0, r1, 'TITLE', title, 3.3)
        self.text(x0 + 1.4, r1 + 13.0, variant, 2.5, 'start', 'tx')
        cell(x0, r2, 'MATERIAL / FINISH', 'see notes & parts list', 2.6, bold=False)
        self.text(x0 + 1.4, r2 + 11.6, 'tol. unless noted ±0.2 · (E) = estimate', 2.1, 'start', 'td')
        cell(c1, y0, 'SCALE', scale)
        cell(c2, y0, 'UNITS', 'mm')
        cell(c1, r1, 'REV', 'v3-A')
        cell(c2, r1, 'DATE', '2026-09-24', 3.0)
        cell(c1, r2, 'SHEET', sheet)
        cell(c2, r2, 'SIZE / PROJ.', 'A3')
        self.proj3(c2 + 18, r2 + 12.2, 0.72)


# ================================================================ v3 production geometry
# z = 0 : front face of the rim / halo ; + = toward the viewer ; glass is proud by GP.
RO = 28.0                      # outer radius, Ø56 (research 07 §5)
TB, GP = 15.9, 0.6             # rim face -> back apex ; glass proud  => 16.5 at CL
RF, RB, RD = 1.0, 2.0, 140.0   # front edge round, back fillet, caseback dome radius (E)
Z_SPLIT = -8.2                 # case / caseback parting (bayonet) (E)
G_R, G_T = 24.48, 1.10         # cover glass (V)
ACT_R, MOD_R = 21.88, 23.0     # active area, module (V)
H_IN, H_OUT = 24.73, 25.73     # halo light pipe ring, 1.0 wide (E)
CAR_O = 24.45                  # floating carrier OD (E)
SPIG_I, SPIG_O = 25.5, 26.8    # bayonet spigot on the case (E)
SK_I = 26.9                    # caseback skirt ID
CW_T = 1.2                     # caseback wall
# crown (x, y in the face plane; z depth)
CR = dict(neck=2.5, hw=4.5, y0=RO, yn=29.2, top=34.0, z0=-1.0, z1=-7.6, eye_y=31.0, eye_r=1.1,
          notch=(31.9, 32.7), mag_x=2.4, cont_x=3.0)
# internal layout (E) — cell 603040 lies 40 across (x), 30 along y
CELL = dict(x=20.0, y=15.0, z0=-6.25, z1=-12.25)
SPK = dict(x=6.0, y0=16.0, y1=24.0, z0=-5.95, z1=-8.45)      # 1208 side-port box, 12 o'clock
LRA = dict(c=(0.0, -20.0), r=4.0, z0=-5.95, z1=-9.15)       # Ø8 coin, 6 o'clock
LUGS = (90.0, 210.0, 330.0)
MIC_A = (264.0, 276.0)

PROF, INFO = profile(RO, TB, RD, RF, RB)          # closed (s, z) outline, front plane at z = 0
FCZ = INFO['fc'][1]                                 # flank end (≈ −11.43)
ZC = -TB + RD


def zo(r):   # outer caseback surface
    return ZC - math.sqrt(RD * RD - r * r)


def zi(r):   # inner caseback surface (offset CW_T)
    return ZC - math.sqrt((RD - CW_T) ** 2 - r * r)


def circ(r, cx=0.0, cy=0.0, n=120):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rrect(w, h, r, cx=0.0, cy=0.0, n=6):
    pts = []
    for (qx, qy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        pts += arc_pts(cx + qx, cy + qy, r, a0, a0 + 90, n)
    return pts


def polar(a, r):
    return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))


def glass_prof(s0=-G_R, s1=G_R, top=GP, bot=GP - G_T):
    e = 0.3
    return [(s0, bot), (s0, top - e), (s0 + e, top), (s1 - e, top), (s1, top - e), (s1, bot)]


def crown_head(hw=None, top=None, yn=None, notch=None):
    """Crown outline in the face plane (x, y), neck + head with latch notches."""
    hw = hw or CR['hw']; top = top or CR['top']; yn = yn or CR['yn']; n0, n1 = notch or CR['notch']
    nk = CR['neck']
    yb = math.sqrt(RO ** 2 - nk ** 2) - 0.05
    right = [(nk, yb), (nk, yn), (hw, yn), (hw, n0), (hw - 0.5, n0), (hw - 0.5, n1), (hw, n1)] + \
        arc_pts(hw - 0.8, top - 0.8, 0.8, 0, 90, 6)
    left = [(-x, y) for x, y in reversed(right)]
    return right + left


def eyes(sh, V, cx, cy, k=1.0, c='ph'):
    for sx in (-1, 1):
        ex = cx + sx * 7.0 * k
        w, h = 7.2 * k, 12.0 * k
        r = w / 2
        pts = arc_pts(ex, cy + h / 2 - r, r, 0, 180, 12) + arc_pts(ex, cy - h / 2 + r, r, 180, 360, 12)
        sh.poly(V.pl(pts), c)
        sh.poly(V.pl(arc_pts(ex - sx * 1.3 * k, cy + 2.9 * k, 1.05 * k, 0, 360, 16)), c)


def lead_l(sh, tip, y, lines, xl=13.0, size=2.2):
    tw = max(sh.tw(l, size) for l in lines)
    sh.leader(tip, (xl + tw + 0.8 + 3.0, y), '', lines=lines, size=size, side=-1)


def lead_r(sh, tip, x, y, lines, size=2.2):
    sh.leader(tip, (x, y), '', lines=lines, size=size, side=1)


def tag(sh, tip, cx, cy, letter, r=2.3):
    dx, dy = tip[0] - cx, tip[1] - cy
    d = math.hypot(dx, dy) or 1
    sh.line(cx + dx / d * r, cy + dy / d * r, tip[0], tip[1], 't')
    sh.circle(tip[0], tip[1], 0.45, 'ah')
    sh.circle(cx, cy, r, 'bal')
    sh.text(cx, cy + 0.95, letter, 2.6, 'middle', 'tx', weight='bold')


def key_list(sh, kx, ky, title, key, dy=7.0):
    sh.text(kx, ky, title, 3.0, 'start', 'tx', weight='bold')
    for i, (l, a, b) in enumerate(key):
        yy = ky + 6.5 + i * dy
        sh.circle(kx + 2.2, yy - 0.9, 2.0, 'bal')
        sh.text(kx + 2.2, yy, l, 2.4, 'middle', 'tx', weight='bold')
        sh.text(kx + 6, yy - 0.9, a, 2.1, 'start', 'tx')
        sh.text(kx + 6, yy + 2.3, b, 2.0, 'start', 'td')


def table(sh, x0, y0, cols, hdr, rows, rh=5.2, size=2.1, hsize=2.0, bold_last=False):
    n = len(rows) + 1
    sh.rect(x0, y0, cols[-1], rh * n, 'fr2t')
    for j, h in enumerate(hdr):
        sh.text(x0 + cols[j] + 1, y0 + rh * 0.72, h, hsize, 'start', 'td')
    sh.line(x0, y0 + rh, x0 + cols[-1], y0 + rh, 'fr2t')
    for c in cols[1:-1]:
        sh.line(x0 + c, y0, x0 + c, y0 + rh * n, 'fr1')
    for i, r in enumerate(rows):
        yy = y0 + rh * (i + 1)
        if i and r[0] != '':
            sh.line(x0, yy, x0 + cols[-1], yy, 'fr1')
        for j, v in enumerate(r):
            if not v:
                continue
            right = isinstance(v, tuple)
            if right:
                v = v[0]
            cls = 'ta' if v in ('V', '(V)') else 'tx'
            if right:
                sh.text(x0 + cols[j + 1] - 0.8, yy + rh * 0.72, v, size, 'end', cls)
            else:
                sh.text(x0 + cols[j] + 1, yy + rh * 0.72, v, size, 'start', cls)
    return y0 + rh * n


# ================================================================ SHEET 1 : GA
def sheet_ga(theme):
    sh = Sheet3(theme)
    sh.frame()
    k = 2.0
    VF = View(92, 168, k)
    VT = View(92, 72, k)
    VS = View(186, 168, k)
    VB = View(336, 168, k, flipx=True)
    TY = 236.0
    fg = sh.th['fg']

    # ---------- FRONT VIEW ----------
    cxp, cyp = VF.p(0, 0)
    sh.poly(VF.pl(crown_head()), 'o')
    sh.circle(cxp, cyp, RO * k, 'o')
    sh.circle(cxp, cyp, (RO - RF) * k, 'o3')                               # tangent edge of R1
    sh.circle(cxp, cyp, H_OUT * k, 'o')
    sh.circle(cxp, cyp, (H_OUT + H_IN) / 2 * k, 'o3', extra='style="stroke-opacity:0.5;stroke-dasharray:0.6 0.6"')
    sh.circle(cxp, cyp, H_IN * k, 'o2')
    sh.circle(cxp, cyp, G_R * k, 'o')
    sh.circle(cxp, cyp, (G_R - 0.3) * k, 'o3')                               # 2.5D edge
    sh.circle(cxp, cyp, ACT_R * k, 'ph')
    eyes(sh, VF, 0, 1.5)
    ex, ey = VF.p(0, CR['eye_y'])
    sh.circle(ex, ey, CR['eye_r'] * k, 'o')
    for sx in (-1, 1):                                                        # magnets (hidden)
        sh.poly(VF.pl([(sx * (CR['mag_x'] - 1), 32.8), (sx * (CR['mag_x'] + 1), 32.8), (sx * (CR['mag_x'] + 1), 34.0), (sx * (CR['mag_x'] - 1), 34.0)]), 'h')
    # antenna keep-out 2-4 o'clock
    sh.poly(VF.pl(arc_pts(0, 0, RO + 1.4, -30, 30, 30)), 'ph', close=False)
    for a in (-30, 30):
        sh.line(*VF.p(*polar(a, RO + 0.4)), *VF.p(*polar(a, RO + 2.4)), 'ph')
    for a in MIC_A:
        sh.line(*VF.p(*polar(a, RO)), *VF.p(*polar(a, RO - 3.0)), 'h')
    # centre lines
    sh.line(cxp, VF.p(0, 36.5)[1], cxp, VF.p(0, -31)[1], 'c')
    sh.line(VF.p(-31, 0)[0], cyp, VF.p(31, 0)[0], cyp, 'c')
    # section A-A
    ya, yb = VF.p(0, 38.5)[1], VF.p(0, -31.5)[1]
    sh.line(cxp, ya, cxp, yb, 'cut')
    sh.section_arrow(cxp, ya, 'A', (-1, 0))
    sh.section_arrow(cxp, yb, 'A', (-1, 0))
    # crown dims
    yh = VF.p(0, CR['top'])[1]
    sh.dim_h(*VF.p(-CR['hw'], 33.4), *VF.p(CR['hw'], 33.4), yh - 4.5, '9.0', tshift=6)
    sh.dim_v(*VF.p(CR['hw'], CR['top']), *VF.p(CR['hw'], RO), VF.p(CR['hw'], 0)[0] + 7, '6.0', gap=0.8)
    # left callouts
    lead_l(sh, VF.p(*polar(128, H_OUT - 0.5)), 104, ['HALO RING Ø49.46 / Ø51.46', '1.0 WIDE, FROSTED, FLUSH'])
    lead_l(sh, VF.p(*polar(143, RO - 1.1)), 114, ['RIM FACE 2.27 WIDE', 'Ø56.0 OUTSIDE'])
    lead_l(sh, VF.p(*polar(160, G_R)), 124, ['Ø48.96 COVER GLASS (V)', '0.6 PROUD = THE EYE'])
    lead_l(sh, VF.p(*polar(215, ACT_R)), 208, ['Ø43.76 ACTIVE (V)', '466×466 AMOLED'])
    lead_l(sh, VF.p(*polar(MIC_A[0], RO - 0.3)), 222, ['2× MIC PORT Ø0.6', 'ON FLANK, 6 o\'clock (E)'])
    # right callouts
    lead_r(sh, (ex + CR['eye_r'] * k * 0.7, ey - CR['eye_r'] * k * 0.7), 150, 96, ['CROWN / BAIL', 'EYE Ø2.2'])
    lead_r(sh, VF.p(CR['hw'] - 0.25, 32.3), 150, 106, ['LATCH NOTCH', '2× 0.5'])
    lead_r(sh, VF.p(*polar(12, RO + 1.4)), 150, 150, ['ANTENNA', 'ZONE 2-4h', 'NO METAL'])
    lead_r(sh, VF.p(*polar(-40, (H_IN + H_OUT) / 2)), 150, 206, ['PRESS', 'THE EYE:', 'WHOLE GLASS', '= 1 BUTTON'])
    sh.text(cxp, TY, 'FRONT VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- TOP VIEW (looking down on the crown) ----------
    def pt(x, z):
        return VT.p(x, -z)
    sh.poly([pt(s, z) for s, z in PROF], 'o')
    sh.poly([pt(*q) for q in glass_prof()], 'o', close=False)
    sh.line(*pt(-RO, Z_SPLIT), *pt(RO, Z_SPLIT), 'o2')
    sh.line(*pt(-RO, -RF), *pt(RO, -RF), 'o3')
    tpx, tpz = INFO['tp']
    sh.line(*pt(-tpx, tpz), *pt(tpx, tpz), 'o3')
    ch = rrect(2 * CR['hw'], CR['z0'] - CR['z1'], 0.8, 0, (CR['z0'] + CR['z1']) / 2)
    sh.poly([pt(x, z) for x, z in ch], 'ob')
    for sx in (-1, 1):
        sh.circle(*pt(sx * CR['mag_x'], -4.3), 1.0 * k, 'o2')
        sh.line(*pt(sx * (CR['hw'] - 0.5), CR['z0'] - 0.3), *pt(sx * (CR['hw'] - 0.5), CR['z1'] + 0.3), 'h')
        sh.poly([pt(sx * 2.9, -6.3), pt(sx * 4.2, -6.3), pt(sx * 4.2, -7.5), pt(sx * 2.9, -7.5)], 'h')
    sh.line(*pt(0, 2.2), *pt(0, -18.0), 'c')
    ytop = pt(0, -TB)[1]
    sh.dim_h(*pt(-RO, -6), *pt(RO, -6), ytop - 7, '56.0')
    sh.dim_v(*pt(-RO, 0), *pt(-RO, FCZ), pt(-RO, 0)[0] - 6, '11.4', tshift=0)
    lead_r(sh, pt(18, zo(18)), 150, 36, ['CASEBACK DOME R140 (E)'])
    lead_r(sh, pt(CR['mag_x'] + 0.7, -4.3 + 0.7), 150, 45, ['2× N52 MAGNET Ø2 (E)'])
    lead_r(sh, pt(4.2, -7.2), 150, 55, ['SPEAKER SLOTS 2× 1.3×1.2', 'HIDDEN UNDER THE CROWN'])
    lead_r(sh, pt(RO, Z_SPLIT), 150, 68, ['BAYONET PARTING z −8.2'])
    sh.text(pt(0, 0)[0], ytop - 13, 'TOP VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- RIGHT SIDE VIEW ----------
    def ps(z, y):
        return VS.p(-z, y)
    sh.poly([ps(z, s) for s, z in PROF], 'o')
    sh.poly([ps(z, s) for s, z in glass_prof()], 'o', close=False)
    sh.line(*ps(Z_SPLIT, -RO), *ps(Z_SPLIT, RO), 'o2')
    sh.line(*ps(-RF, -RO), *ps(-RF, RO), 'o3')
    sh.line(*ps(tpz, -tpx), *ps(tpz, tpx), 'o3')
    cside = [(CR['z0'], RO - 0.3), (CR['z0'], CR['top'] - 0.8)] + \
        [(CR['z0'] - 0.8 + 0.8 * math.cos(math.radians(a)), CR['top'] - 0.8 + 0.8 * math.sin(math.radians(a))) for a in range(0, 91, 15)] + \
        [(CR['z1'] + 0.8 + 0.8 * math.cos(math.radians(a)), CR['top'] - 0.8 + 0.8 * math.sin(math.radians(a))) for a in range(90, 181, 15)] + \
        [(CR['z1'], RO - 0.3)]
    sh.poly([ps(z, y) for z, y in cside], 'ob', close=False)
    for yy_ in (CR['eye_y'] - CR['eye_r'], CR['eye_y'] + CR['eye_r']):
        sh.line(*ps(CR['z0'], yy_), *ps(CR['z1'], yy_), 'h')
    sh.line(*ps(CR['z1'] - 0.35, 30.4), *ps(CR['z1'] - 0.35, 31.6), 'o', extra='style="stroke-width:0.9;stroke:%s"' % sh.th['acc'])
    sh.line(*ps(2.2, 0), *ps(-18.0, 0), 'c')
    xr = ps(-TB, 0)[0]
    sh.dim_v(*ps(-4, RO), *ps(-4, -RO), xr + 6, '56.0')
    sh.dim_v(*ps(CR['z1'], CR['top']), *ps(-10, -RO), xr + 14, '62.0 OVERALL')
    yy = ps(0, -10)[1]
    sh.line(ps(GP, -10)[0], yy, ps(zo(10), -10)[0], yy, 't')
    sh.arrow(ps(GP, -10), ps(-5, -10))
    sh.arrow(ps(zo(10), -10), ps(-10, -10))
    sh.text((ps(GP, 0)[0] + ps(-TB, 0)[0]) / 2, yy - 1.0, '16.5', 2.6, 'middle', 'td')
    sh.text((ps(GP, 0)[0] + ps(-TB, 0)[0]) / 2, yy + 3.2, '@ CL', 2.0, 'middle', 'td')
    sh.dim_h(*ps(CR['z0'], CR['top']), *ps(CR['z1'], CR['top']), ps(0, CR['top'])[1] - 5, '6.6')
    xa = xr + 20
    lead_r(sh, ps(GP, 18), xa, 118, ['GLASS 0.6 PROUD'])
    lead_r(sh, ps(0.0, 25.2), xa, 110, ['HALO + RIM FLUSH', 'z 0'])
    lead_r(sh, ps(CR['z1'] - 0.35, 31.0), xa, 100, ['2× CHARGE', 'CONTACT Au', '(ALTAR POGO)'])
    lead_r(sh, ps(zo(12), 12), xa, 142, ['R140 (E)'])
    lead_r(sh, ps(Z_SPLIT, -16), xa, 180, ['BAYONET', 'z −8.2'])
    lead_r(sh, ps(-RF + RF * 0.7, -(RO - RF + RF * 0.7)), xa, 226, ['R1 FRONT'])
    fcx, fcz = INFO['fc']
    lead_r(sh, ps(fcz - RB * 0.6, -(fcx + RB * 0.8)), xa, 218, ['R2 BACK'])
    sh.text(ps(-TB / 2, 0)[0], TY, 'RIGHT SIDE', 3.2, 'middle', 'tx', weight='bold')

    # ---------- REAR VIEW ----------
    bx, by = VB.p(0, 0)
    sh.poly(VB.pl(crown_head()), 'o')
    sh.circle(bx, by, RO * k, 'o')
    sh.circle(bx, by, tpx * k, 'o3')
    for sag in (1.0, 2.0):
        r = math.sqrt(RD ** 2 - (RD - sag) ** 2)
        sh.circle(bx, by, r * k, 'ph')
    sh.circle(bx, by, (SPIG_O - 0.5) * k, 'h')                  # O-ring (hidden)
    for a in LUGS:                                             # bayonet lugs (hidden)
        pts = arc_pts(0, 0, SPIG_O, a - 9, a + 9, 8) + list(reversed(arc_pts(0, 0, SPIG_O + 0.5, a - 9, a + 9, 8)))
        sh.poly(VB.pl(pts), 'h')
    sh.poly(VB.pl([(-CELL['x'], -CELL['y']), (CELL['x'], -CELL['y']), (CELL['x'], CELL['y']), (-CELL['x'], CELL['y'])]), 'ph')
    # engraving ring
    r_in, r_out, r_t = 17.2, 21.6, 18.7
    sh.circle(bx, by, r_in * k, 'o3')
    sh.circle(bx, by, r_out * k, 'o3')
    R = r_t * k
    sh.defs.append('<path id="engr%s" d="M %s %s A %s %s 0 1 1 %s %s A %s %s 0 1 1 %s %s"/>' % (
        theme, f(bx - R), f(by), f(R), f(R), f(bx + R), f(by), f(R), f(R), f(bx - R), f(by)))
    sh.add('<text class="tx" font-size="3.4" letter-spacing="0.35"><textPath href="#engr%s" startOffset="25%%" text-anchor="middle">SOUL · No. 0001 · born 24.09.2026</textPath></text>' % theme)
    # coin slot
    sh.poly(VB.pl(rrect(14.0, 1.6, 0.8)), 'o')
    sh.poly(VB.pl(arc_pts(0, 0, 9.5, 200, 250, 16)), 't', close=False)
    t0 = VB.p(*polar(200, 9.5))
    sh.arrow(t0, VB.p(*polar(206, 9.5)))
    sh.text(*VB.p(*polar(232, 11.8)), 'OPEN', 2.0, 'middle', 'td')
    # crown rear face: eye + 2 contacts
    sh.circle(*VB.p(0, CR['eye_y']), CR['eye_r'] * k, 'o')
    for sx in (-1, 1):
        px, py = VB.p(sx * CR['cont_x'], CR['eye_y'])
        sh.circle(px, py, 0.6 * k, 'o', extra='style="fill:%s;fill-opacity:0.7"' % sh.th['acc'])
    sh.line(bx, VB.p(0, 36.5)[1], bx, VB.p(0, -31)[1], 'c')
    sh.line(VB.p(31, 0)[0], by, VB.p(-31, 0)[0], by, 'c')

    def tg(feat, at, l):
        tag(sh, VB.p(*feat), *VB.p(*at), l)
    tg((-CR['cont_x'], CR['eye_y']), (-12, 36), 'a')
    tg((-6.5, 0.0), (-20, -4.5), 'b')
    tg(polar(150, 20.9), (-31, 21), 'c')
    tg(polar(30, SPIG_O + 0.25), (31, 22), 'd')
    tg(polar(-20, SPIG_O - 0.5), (32, -10), 'e')
    tg((CELL['x'], -CELL['y'] + 3), (31, -24), 'f')
    tg(polar(235, math.sqrt(RD ** 2 - (RD - 2) ** 2)), (-27, -26), 'g')
    tg(polar(215, 9.5), (-31, -14), 'h')
    sh.text(bx, TY, 'REAR VIEW (CASEBACK)', 3.2, 'middle', 'tx', weight='bold')

    # ---------- notes + rear key ----------
    nx, ny = 196, 16
    sh.text(nx, ny + 2, 'GENERAL NOTES', 3.0, 'start', 'tx', weight='bold')
    notes = [
        '1. THIRD-ANGLE PROJECTION. mm. A3, SCALE 2:1.',
        '2. 1.75" ROUND AMOLED 466×466. GLASS Ø48.96×1.10,',
        '   ACTIVE Ø43.76, MODULE Ø46.0 (V, STEP).',
        '3. CROWN AT 12 DEFINES "UP". SILHOUETTE = CIRCLE',
        '   + CROWN. NO LOGO, NO SCREW, NO PORT ON FRONT.',
        '4. PRESS THE EYE: GLASS + MODULE FLOAT 0.30 ON A',
        '   GASKET OVER ONE Ø5 DOME (2.5-3.5 N). SHEET 2.',
        '5. HALO: 12 RGB LEDs UNDER A 1.0 FROSTED PIPE.',
        '6. CHARGING ONLY VIA 2 Au CONTACTS ON THE CROWN',
        '   (ALTAR DOCK). SPEAKER FIRES UNDER THE CROWN.',
        '7. CASEBACK: BAYONET 3 LUGS, 1/8 TURN, COIN SLOT,',
        '   O-RING (IP54). CELL 603040 BEHIND IT.',
    ]
    for i, n in enumerate(notes):
        sh.text(nx, ny + 7.5 + i * 3.4, n, 2.05, 'start', 'tx')
    sh.text(nx, ny + 7.5 + len(notes) * 3.4 + 1.0, '(V) STEP  (K) SPEC SHEET  (E) ESTIMATE', 2.05, 'start', 'ta')
    key = [
        ('a', '2× CHARGE CONTACT Ø1.2 Au', 'crown rear face, pitch 6.0'),
        ('b', 'COIN SLOT 14×1.6, 0.8 DEEP', 'twist ⟲ 1/8 turn to open'),
        ('c', 'ENGRAVING RING Ø34.4-43.2', 'SOUL · No. · born date (E)'),
        ('d', '3× BAYONET LUG (hidden)', '90° / 210° / 330°, 18° wide'),
        ('e', 'O-RING 0.7 cs (hidden)', 'on case spigot Ø52.6'),
        ('f', 'CELL 603040 (phantom)', '40×30×6, 650 mAh (K)'),
        ('g', 'DOME CONTOURS, 1 mm sag', 'sphere R140, apex at CL'),
        ('h', 'OPENING DIRECTION', 'counter-clockwise'),
    ]
    key_list(sh, 314, ny + 2, 'REAR VIEW KEY', key, dy=6.6)

    # ---------- key data ----------
    kx, ky = 16, 247
    sh.text(kx, ky, 'KEY DATA · PRODUCTION TARGET', 2.8, 'start', 'tx', weight='bold')
    rows = [
        ('ENVELOPE', 'Ø56.0 × 16.5 @ CL · rim flank 11.4 · crown → 62.0 overall'),
        ('MASS', '≈50 g Bone (PC back) · ≈56 g Heirloom (316L back) (E)'),
        ('BATTERY', '603040 LiPo ≈650 mAh, 6×30×40 (K) · charge via crown'),
        ('AUDIO / HAPTIC', '1208 box speaker under the crown · LRA Ø8 at 6 (E)'),
        ('INPUT / LIGHT', 'press the eye (dome) · touch · IMU · halo 12× RGB'),
    ]
    for i, (a, b) in enumerate(rows):
        yy = ky + 6 + i * 7.0
        sh.line(kx, yy + 2.3, kx + 214, yy + 2.3, 'fr1')
        sh.text(kx, yy, a, 2.3, 'start', 'td')
        sh.text(kx + 36, yy, b, 2.4, 'start', 'tx')
    sh.title_block('GENERAL ARRANGEMENT', 'PRODUCTION TARGET · Ø56 × 16.5', '2:1', '1 / 4', 'SOUL-V3-001')
    return sh


# ================================================================ SHEET 2 : SECTION A-A
Z_MF0, Z_MF1 = -5.25, -5.85          # mid-frame
BOSS_Z = -13.9                        # coin-slot boss inner face


def zi_b(s):
    return BOSS_Z if abs(s) <= 3.0 else zi(abs(s))


def case_half(sg):
    """Front case cross-section, one side (sg = +1 crown side, −1 bottom side)."""
    pts = [(H_OUT, 0.0), (RO - RF, 0.0)] + arc_pts(RO - RF, -RF, RF, 90, 0, 8) + [(RO, Z_SPLIT), (SPIG_O, Z_SPLIT),
           (SPIG_O, -9.05), (26.35, -9.05), (26.35, -9.75), (SPIG_O, -9.75)]
    if sg > 0:
        pts += [(SPIG_O, -10.0), (27.3, -10.0), (27.3, -10.6)]
    else:
        pts += [(SPIG_O, -10.6)]
    pts += [(SPIG_I, -10.6), (SPIG_I, Z_MF1), (H_OUT, Z_MF1)]
    return [(sg * a, b) for a, b in pts]


def caseback_pts():
    out = back_curve(RO, TB, RD, RB)
    x8 = 0.8
    out = [q for q in out if abs(q[0]) > x8]
    i = next(j for j, q in enumerate(out) if q[0] < 0)
    z8 = zo(x8)
    out = out[:i] + [(x8, z8), (x8, z8 + 0.8), (-x8, z8 + 0.8), (-x8, z8)] + out[i:]
    inner = []
    s_ = -25.3
    while s_ <= 25.31:
        inner.append((s_, zi_b(s_)))
        s_ += 0.5 if abs(s_) > 3.2 else 0.1
    inner = [(-3.0, zi(3.0)), (-3.0, BOSS_Z), (3.0, BOSS_Z), (3.0, zi(3.0))]
    left = [(s_, zi(abs(s_))) for s_ in [-25.3 + 0.5 * i for i in range(45)] if s_ < -3.0]
    right = [(s_, zi(abs(s_))) for s_ in [3.2 + 0.5 * i for i in range(45)] if s_ <= 25.3]
    inner = left + inner + right + [(25.3, zi(25.3))]
    pts = [(RO, Z_SPLIT)] + out + [(-RO, Z_SPLIT), (-SK_I, Z_SPLIT), (-SK_I, -10.8), (-25.3, -10.8)] + inner + \
          [(25.3, -10.8), (SK_I, -10.8), (SK_I, -10.7), (27.4, -10.7), (27.4, -9.9), (SK_I, -9.9), (SK_I, Z_SPLIT)]
    return pts


def region(sh, V, pts, pat=None, cls='o2', fill=None):
    P = V.pl(pts)
    if pat:
        sh.poly(P, 'o2', extra='style="fill:%s;stroke:none"' % sh.th['bg'])
        sh.poly(P, cls, extra='style="fill:url(#%s)"' % pat)
    elif fill:
        sh.poly(P, cls, extra='style="fill:%s"' % fill)
    else:
        sh.poly(P, cls)


def box(s0, s1, z0, z1):
    return [(s0, z0), (s1, z0), (s1, z1), (s0, z1)]


def draw_section(sh, V, k, detail=False):
    th = sh.th
    acc = th['acc']
    region(sh, V, case_half(1), 'hA')
    region(sh, V, case_half(-1), 'hA')
    region(sh, V, caseback_pts(), 'hB')
    for sg in (1, -1):
        m = lambda pts: [(sg * a, b) for a, b in pts]
        region(sh, V, m(box(H_IN, H_OUT, 0.0, -4.6)), cls='o2', fill=acc + '" fill-opacity="0.22')
        region(sh, V, m([(23.2, -0.5), (CAR_O, -0.5), (CAR_O, -4.8), (21.8, -4.8), (21.8, -3.0), (23.2, -3.0)]), 'hC')
        region(sh, V, m([(CAR_O, -0.95), (24.8, -1.15), (24.8, -1.3), (CAR_O, -1.5)]), cls='o3', fill=th['fg'])
        region(sh, V, m(box(21.9, 24.3, -4.8, Z_MF0)), 'hD', cls='o3')
        region(sh, V, m(box(24.5, H_OUT, -5.15, Z_MF0)), cls='o3', fill=th['dim'])
        region(sh, V, m(box(24.78, 25.68, -4.65, -5.15)), cls='o3', fill=acc)
        sh.circle(*V.p(sg * 26.55, -9.4), 0.33 * k, 'o3', extra='style="fill:%s"' % th['fg'])
    region(sh, V, box(-H_OUT, H_OUT, Z_MF0, Z_MF1), 'hA', cls='o2')
    sh.poly(V.pl(glass_prof()), 'gl')
    region(sh, V, box(-MOD_R, MOD_R, -0.5, -2.0), cls='f2')
    region(sh, V, box(-22.5, 22.5, -2.0, -2.2), 'hD', cls='o3')
    region(sh, V, box(-MOD_R, MOD_R, -2.2, -3.0), 'hC')
    for s0, s1, h in ((-20.5, -14.0, 1.0), (-12.5, -9.5, 0.7), (10.0, 17.5, 1.2), (18.5, 21.0, 0.8)):
        region(sh, V, box(s0, s1, -3.0, -3.0 - h), cls='f2')
    region(sh, V, box(-8.0, 8.0, -3.0, -4.5), cls='f2')
    region(sh, V, box(-1.0, 1.0, -4.5, -4.8), 'hS')
    # dome + flex
    region(sh, V, box(-4.0, 4.0, -5.15, Z_MF0), cls='o3', fill=th['dim'])
    dm = [(-2.5, -5.15)] + [(2.5 * math.cos(math.radians(a)), -5.15 + 0.35 * math.sin(math.radians(a))) for a in range(180, -1, -10)]
    sh.poly(V.pl(dm), 'o2', extra='style="fill:url(#hS)"')
    # foam, cell, pad
    region(sh, V, box(-14.0, 14.0, Z_MF1, CELL['z0']), 'hD', cls='o3')
    region(sh, V, box(-CELL['y'], CELL['y'], CELL['z0'], CELL['z1']), cls='fb')
    for i in range(1, 6):
        zz = CELL['z0'] + (CELL['z1'] - CELL['z0']) * i / 6
        sh.line(*V.p(-CELL['y'] + 0.6, zz), *V.p(CELL['y'] - 0.6, zz), 'o3', extra='stroke-opacity="0.3"')
    pad = [(-10.0, CELL['z1']), (10.0, CELL['z1'])] + [(s_, zi_b(s_) + 0.02) for s_ in [10 - 0.5 * i for i in range(41)]]
    region(sh, V, pad, 'hD', cls='o3')
    # speaker (12 o'clock side) + LRA (6 o'clock side)
    region(sh, V, box(SPK['y0'], SPK['y1'], SPK['z0'], SPK['z1']), cls='f2')
    sh.poly(V.pl([(SPK['y1'] - 0.2, -6.4), (SPK['y1'] - 1.6, -6.9), (SPK['y1'] - 1.6, -7.5), (SPK['y1'] - 0.2, -8.0)]), 'o3', close=False)
    for zz in (-6.3, -7.5):
        sh.line(*V.p(SPK['y1'], zz), *V.p(RO, zz), 'h')
    region(sh, V, box(-LRA['c'][1] * -1 - LRA['r'], -LRA['c'][1] * -1 + LRA['r'], LRA['z0'], LRA['z1']), cls='f2')
    lm = LRA['c'][1]
    sh.poly(V.pl(box(lm - 2.2, lm + 2.2, LRA['z0'] - 0.7, LRA['z1'] + 0.7)), 'o3')
    # mic port (6 o'clock, off-plane) hidden
    for zz in (-3.7, -4.3):
        if not detail:
            sh.line(*V.p(-H_OUT, zz), *V.p(-RO, zz), 'h')
    # crown (cut through the eye) + stud
    region(sh, V, box(26.3, RO + 0.02, -3.3, -5.3), 'hS')
    region(sh, V, box(RO, CR['eye_y'] - CR['eye_r'], CR['z0'], CR['z1']), 'hS')
    top = [(CR['eye_y'] + CR['eye_r'], CR['z0'])] + arc_pts(CR['top'] - 0.8, CR['z0'] - 0.8, 0.8, 90, 0, 6) + \
          arc_pts(CR['top'] - 0.8, CR['z1'] + 0.8, 0.8, 0, -90, 6) + [(CR['eye_y'] + CR['eye_r'], CR['z1'])]
    region(sh, V, top, 'hS')
    # outline on top
    sh.poly(V.pl(PROF), 'o')
    sh.poly(V.pl(glass_prof()), 'o', close=False)


def sheet_section(theme):
    sh = Sheet3(theme)
    sh.frame()
    k = 4.0
    V = View(142, 54, k)
    p = V.p
    draw_section(sh, V, k)
    sh.line(*p(0, 3.2), *p(0, -18.5), 'c')
    sh.text(p(0, 0)[0] + 1, p(0, -18.5)[1] + 0.2, 'CL', 2.0, 'start', 'td')
    yb = p(0, -TB)[1]
    # dims
    sh.dim_v(*p(-12, GP), *p(0, -TB), 17, '16.5 @ CL')
    sh.dim_v(*p(-RO, 0), *p(-RO, FCZ), 23.5, '11.4')
    sh.dim_h(*p(-RO, -6), *p(RO, -6), yb + 7, '56.0')
    sh.dim_h(*p(-G_R, GP), *p(G_R, GP), p(0, GP)[1] - 7, 'Ø48.96 GLASS (V)', tshift=-40)
    sh.dim_h(*p(-RO, 0), *p(CR['top'], CR['z0']), p(0, GP)[1] - 13, '62.0 OVERALL', tshift=-40)
    # balloons (item numbers = parts list, sheet 3)
    def bl(n, feat, at):
        sh.balloon(*at, n, tip=p(*feat))
    top, bot = 27.0, yb + 13.5
    bl(2, (-14, 0.2), (72, top))
    bl(3, (-9, -1.3), (84, top))
    bl(5, (-5, -2.6), (96, top))
    bl(14, (12, -2.1), (190, top))
    bl(9, (H_IN + 0.5, -2.0), (228, top))
    bl(17, (CR['top'] - 0.9, -3.0), (262, top))
    bl(12, (lm_ := LRA['c'][1], -7.5), (46, bot))
    bl(16, (-12, zo(12) + 0.4), (80, bot))
    bl(13, (-6, -9.0), (100, bot))
    bl(8, (-18, -5.55), (58, bot))
    bl(7, (0.8, -5.0), (140, bot))
    bl(14, (6, -12.9), (160, bot))
    bl(11, (20, -7.2), (206, bot))
    bl(15, (26.55, -9.4), (240, bot))
    bl(1, (27.4, -6.5), (262, bot))
    bl(18, (27.2, -4.3), (282, 76))
    sh.text(p(3, 0)[0], 17.0, 'SECTION A-A  ·  SCALE 4:1  ·  ROTATED 90°: FRONT UP, CROWN (12 o\'clock) RIGHT', 3.0, 'middle', 'tx', weight='bold')

    # detail markers
    DB, DC = (-25.1, -2.6), (0.0, -4.9)
    for (c, l, dx) in ((DB, 'B', -1), (DC, 'C', 1)):
        cc = p(*c)
        sh.circle(cc[0], cc[1], 3.3 * k, 'ph')
        sh.text(cc[0] + dx * 3.3 * k * 0.8 + dx * 2.0, cc[1] - 3.3 * k * 0.7, l, 4.0, 'middle', 'tx', weight='bold')

    def detail(c, cx, cy, rr, kd):
        VD = View(cx - c[0] * kd, cy + c[1] * kd, kd)
        cid = sh.clip(arc_pts(cx, cy, rr, 0, 360, 90))
        sh.add('<g clip-path="url(#%s)">' % cid)
        sh.circle(cx, cy, rr, 'bgf')
        draw_section(sh, VD, kd, detail=True)
        sh.add('</g>')
        sh.circle(cx, cy, rr, 'o2')
        return VD.p

    # ---------- detail B : floating glass edge 10:1 ----------
    kd = 10.0
    bx, by, br = 352.0, 72.0, 33.0
    q = detail(DB, bx, by, br, kd)
    L = lambda tip, x, y, lines, side: sh.leader(tip, (x, y), '', lines=lines, size=1.9, side=side)
    L(q(-24.6, 0.3), bx - 22, by - 38, ['GAP 0.25 = FLOAT CLEARANCE'], -1)
    L(q(-25.3, -1.6), bx - 36, by - 22, ['HALO PIPE 1.0', 'FLUSH z 0'], -1)
    L(q(-27.0, -2.4), bx - 36, by - 6, ['CASE WALL', '2.27'], -1)
    L(q(-25.2, -4.9), bx - 36, by + 12, ['LED 1010 RGB', 'on halo flex', '(dry side)'], -1)
    L(q(-24.0, -5.6), bx - 34, by + 30, ['MID-FRAME 0.6'], -1)
    L(q(-22.8, 0.1), bx + 24, by - 38, ['GLASS 1.10 (V)'], 1)
    L(q(-24.7, -1.25), bx + 36, by - 22, ['LIP SEAL on', 'CARRIER OD', '(IP54, slides)'], 1)
    L(q(-22.6, -3.8), bx + 36, by - 2, ['FLOATING', 'CARRIER', 'PC-GF30'], 1)
    L(q(-22.6, -5.05), bx + 36, by + 18, ['GASKET 0.45', 'LSR = SPRING', '+ SEAL'], 1)
    sh.dim_h(*q(-G_R, 0.6), *q(-H_IN, 0.6), q(0, 0.6)[1] - 4, '0.25', size=1.9, arrows_out=True, gap=0)
    sh.dim_v(*q(-24.6, 0.6), *q(-24.6, 0.0), q(-28.2, 0)[0], '0.6', size=1.9, arrows_out=True, gap=0)
    sh.text(bx, by + br + 5.5, 'DETAIL B  ·  10:1  ·  FLOATING GLASS EDGE', 2.8, 'middle', 'tx', weight='bold')

    # ---------- detail C : press-the-eye dome 10:1 ----------
    cx, cy, cr = 262.0, 186.0, 33.0
    q = detail(DC, cx, cy, cr, kd)
    L(q(-1.5, -2.6), cx + 36, cy - 26, ['PCB 0.8 (floats)'], 1)
    L(q(0.5, -4.65), cx + 36, cy - 14, ['ACTUATOR NUB Ø2'], 1)
    L(q(-1.2, -5.05), cx + 36, cy - 2, ['METAL DOME Ø5', '2.5-3.5 N (K)'], 1)
    L(q(2.8, -5.2), cx + 36, cy + 12, ['DOME FLEX 0.1', 'MIC POWER GATE'], 1)
    L(q(1.5, -5.6), cx + 36, cy + 24, ['MID-FRAME (fixed)'], 1)
    sh.dim_v(*q(-2.2, -4.8), *q(-2.2, -5.15), q(-3.0, 0)[0], '0.35', size=1.9, arrows_out=True, gap=0)
    sh.text(cx, cy + cr + 5.5, 'DETAIL C  ·  10:1  ·  PRESS THE EYE', 2.8, 'middle', 'tx', weight='bold')

    # ---------- press-the-eye data ----------
    px, py = 340.0, 146.0
    sh.text(px, py, 'PRESS THE EYE', 3.0, 'start', 'tx', weight='bold')
    rows = [
        'Glass + AMOLED + PCB + carrier = one',
        'floating unit (≈17 g) on gasket 6.',
        'Travel 0.30 ±0.05, hard stop 0.40 (E)',
        'Force 2.5-3.5 N, anywhere on the',
        'glass: 3 PTFE glide pads at 120°',
        'keep an edge press on the dome.',
        'Click = wake / OK · double = back',
        'Hold = talk: mics powered ONLY',
        'while the dome is closed.',
        'Life ≥ 1 M cycles (K). LRA 10-15 ms',
        'tick confirms every press.',
        'Swipes / rim-scroll: touch panel.',
    ]
    for i, r in enumerate(rows):
        sh.text(px, py + 6 + i * 3.35, r, 2.05, 'start', 'tx' if i not in (7, 8) else 'ta')

    # ---------- stack table ----------
    tx0, ty0 = 14.0, 146.0
    sh.text(tx0, ty0 - 3, 'STACK-UP  (z = 0 AT RIM FACE, + TOWARD VIEWER)', 2.7, 'start', 'tx', weight='bold')
    rows = [
        ('2', 'Cover glass Ø48.96, 0.6 proud', '+0.60 → −0.50', '1.10', '(V) STEP'),
        ('3', 'AMOLED + touch + OCA, Ø46.0', '−0.50 → −2.00', '1.50', '(E)'),
        ('14', 'Graphite / foam sheet', '−2.00 → −2.20', '0.20', '(E)'),
        ('5', 'Main PCB, custom Ø46', '−2.20 → −3.00', '0.80', '(E)'),
        ('5', 'Shield can + actuator nub', '−3.00 → −4.80', '1.80', '(E)'),
        ('7', 'Metal dome Ø5 + flex', '−4.80 → −5.25', '0.45', 'travel 0.30'),
        ('8', 'Mid-frame, bonded to case', '−5.25 → −5.85', '0.60', 'PC-GF (E)'),
        ('14', 'Foam = cell swell space', '−5.85 → −6.25', '0.40', '≈7 % of cell'),
        ('13', 'Cell 603040 ≈650 mAh', '−6.25 → −12.25', '6.00', '(K)'),
        ('14', 'Retaining pad, no glue', '−12.25 → −13.90', '1.65', 'EU 2023/1542'),
        ('16', 'Caseback + coin-slot boss', '−13.90 → −15.90', '2.00', 'R140 (E)'),
        ('9', 'Halo pipe (edge, r 24.73-25.73)', '0.00 → −4.60', '4.60', 'frosted PMMA'),
        ('10', 'Halo LED 1010 + flex (edge)', '−4.65 → −5.25', '0.60', '12× RGB-IC'),
        ('4', 'Floating carrier (edge)', '−0.50 → −4.80', '4.30', 'PC-GF30'),
        ('6', 'Perimeter gasket (edge)', '−4.80 → −5.25', '0.45', 'LSR 40 ShA'),
        ('11', 'Speaker 1208, 12 o\'clock', '−5.95 → −8.45', '2.50', 'fires under crown'),
        ('12', 'LRA Ø8 coin, 6 o\'clock', '−5.95 → −9.15', '3.20', '(E)'),
    ]
    yend = table(sh, tx0, ty0, [0, 9, 84, 128, 145, 204], ['#', 'ELEMENT', 'z FROM → TO', 't', 'NOTE'], rows, rh=4.9, size=2.05)
    sh.text(tx0, yend + 4.2, 'At CL: 0.6 + 15.9 = 16.5. Walls: rim 2.27, spigot 1.3, caseback 1.2, skirt 1.1 (E).', 2.0, 'start', 'td')
    sh.title_block('SECTION A-A · PRESS THE EYE', 'PRODUCTION TARGET · stack & mechanism', '4:1 / 10:1', '2 / 4', 'SOUL-V3-002')
    return sh


# ================================================================ SHEET 3 : EXPLODED + PARTS LIST
BOM = [
    ('1', 'Case: rim Ø56 + spigot', '1', 'PC-GF ceramic-look white | 316L', 'E', 7.0),
    ('2', 'Cover glass Ø48.96 × 1.10', '1', 'strengthened, 2.5D, AR + AF', 'V', 5.2),
    ('3', 'AMOLED 1.75" 466² + touch', '1', 'CO5300 + CST9217, Ø46.0', 'V', 4.0),
    ('4', 'Floating carrier + lip seal', '1', 'PC-GF30 + LSR 2K lip', 'E', 1.5),
    ('5', 'Main PCB assembly', '1', 'ESP32-S3, AXP2101, ES8311/7210,', 'K', 6.0),
    ('', '', '', 'QMI8658, DRV2605L, 2 mics, prox', '', None),
    ('6', 'Perimeter gasket 0.45', '1', 'LSR 40 Sh A: spring + seal', 'E', 0.3),
    ('7', 'Metal dome Ø5 + flex', '1', '2.5-3.5 N, ≥1 M cycles', 'K', 0.1),
    ('8', 'Mid-frame 0.6', '1', 'PC-GF, bonded, dome base', 'E', 1.7),
    ('9', 'Halo light pipe 1.0 wide', '1', 'PMMA frosted, flush z 0', 'E', 0.6),
    ('10', 'Halo LED flex', '1', '12× RGB-IC 1010, 1 GPIO', 'E', 0.5),
    ('11', 'Speaker 1208, side port', '1', '8 Ω box, fires under crown', 'E', 1.0),
    ('12', 'LRA Ø8 coin, Z-axis', '1', 'heartbeat / click 10-15 ms', 'E', 0.8),
    ('13', 'Cell 603040 LiPo', '1', '≈650 mAh 3.7 V + PCM, 6×30×40', 'K', 13.0),
    ('14', 'Foam set', '1', 'PORON pad Ø20, swell foam, graphite', 'E', 0.5),
    ('15', 'O-ring 0.7 cs', '1', 'FKM, bayonet seal IP54', 'E', 0.1),
    ('16', 'Caseback, bayonet', '1', 'PC pearl (Bone) | 316L (Heirloom)', 'E', 5.0),
    ('17', 'Crown / bail', '1', '316L MIM, 2× N52 Ø2, latch notches', 'E', 2.5),
    ('18', 'Crown contacts + flex', '2', 'Au-plated brass, altar pogo target', 'E', 0.3),
]


class Ax2:
    """Exploded projection: object z (explode axis) vertical on paper, disks seen as flattened ellipses."""

    def __init__(self, ox, oy, k, rz=32.0, e=26.0):
        self.ox, self.oy, self.k = ox, oy, k
        self.c, self.s = math.cos(math.radians(rz)), math.sin(math.radians(rz))
        self.ce, self.se = math.cos(math.radians(e)), math.sin(math.radians(e))

    def t(self, x, y, z):
        x1 = x * self.c - y * self.s
        y1 = x * self.s + y * self.c
        X = self.ox + self.k * x1
        Y = self.oy - self.k * (z * self.ce + y1 * self.se)
        return (X, Y), z * self.se - y1 * self.ce

    def p(self, x, y, z):
        return self.t(x, y, z)[0]


OFFX = {17: (24, 30), 18: (24, 44), 1: (24, 60), 9: (24, 76), 2: (24, 96), 3: (24, 116), 4: (24, 138), 5: (24, 162),
        6: (128, 44), 10: (128, 64), 8: (128, 96), 13: (128, 148), 15: (128, 184), 16: (128, 206),
        7: (234, 70), 11: (234, 104), 12: (234, 130), 14: (234, 170)}
ABS = set(OFFX)


def sheet_exploded(theme):
    sh = Sheet3(theme)
    sh.frame()
    AX1 = Ax2(78, 118, 1.22)
    AX2 = Ax2(182, 116, 1.12)
    cur = [AX1]
    items = []

    def prism(outl, z0, z1, dz, face_extra=None, cls='ob', face_cls='o', off=(0, 0), bias=0.0, hole=None):
        ox_, oy_ = off
        P0 = [cur[0].p(x + ox_, y + oy_, z0 + dz) for x, y in outl]
        P1 = [cur[0].p(x + ox_, y + oy_, z1 + dz) for x, y in outl]
        cx = sum(x for x, _ in outl) / len(outl) + ox_
        cy = sum(y for _, y in outl) / len(outl) + oy_
        depth = cur[0].t(cx, cy, (z0 + z1) / 2 + dz)[1] + bias

        ax = cur[0]

        def draw():
            saved = cur[0]
            cur[0] = ax
            if hole:
                Hp = [cur[0].p(x, y, z1 + dz) for x, y in circ(hole, n=96)]
                sh.path(pts_d(hull(P0 + P1)) + ' ' + pts_d(list(reversed(Hp))), cls, extra='fill-rule="evenodd"')
                rz = math.degrees(math.atan2(ax.s, ax.c))
                sh.poly([cur[0].p(x, y, z0 + dz) for x, y in arc_pts(0, 0, hole, -rz, 180 - rz, 40)], 'o3', close=False)
                sh.poly(Hp, 'o2')
            else:
                sh.poly(hull(P0 + P1), cls)
            sh.poly(P1, face_cls)
            if face_extra:
                face_extra()
            cur[0] = saved
        items.append((depth, draw))

    def face(pts2, z, cls='o2'):
        sh.poly([cur[0].p(x, y, z) for x, y in pts2], cls)

    A = {}
    D = dict(case=62, halo=42, glass=22, amoled=4, carrier=-16, pcb=-36, gasket=68, led=56, dome=44, mid=30,
             spk=4, cell=-22, pad=-38, oring=-50, back=-62)
    # 1 case
    def case_x():
        z = D['case']
        face(circ(RO - RF), z, 'o3')
        face(circ(H_OUT), z, 'o')
    prism(circ(RO), Z_SPLIT, 0.0, D['case'], case_x, hole=H_OUT)
    A[1] = cur[0].p(*polar(200, RO), D['case'])
    # 17 crown, exploded upward
    def crown_x():
        face([(x, y + 12) for x, y in circ(CR['eye_r'], 0, CR['eye_y'], 20)], CR['z0'] + D['case'], 'o2')
    prism(crown_head(), CR['z1'], CR['z0'], D['case'], crown_x, off=(0, 12))
    A[17] = cur[0].p(-CR['hw'], CR['top'] + 12 - 1, CR['z0'] + D['case'])
    A[18] = cur[0].p(-CR['cont_x'], CR['eye_y'] + 12, CR['z1'] + D['case'])
    # 9 halo
    prism(circ(H_OUT), -4.6, 0.0, D['halo'], None, cls='ob', face_cls='o2', hole=H_IN)
    A[9] = cur[0].p(*polar(160, H_OUT), D['halo'])
    # 2 glass
    def gl_x():
        face(circ(ACT_R), GP + D['glass'], 'ph')
        for sx in (-1, 1):
            face(rrect(7.2, 12.0, 3.6, sx * 7.0, 1.5), GP + D['glass'], 'o3')
    prism(circ(G_R), GP - G_T, GP, D['glass'], gl_x, cls='gl')
    A[2] = cur[0].p(*polar(150, G_R), GP + D['glass'])
    # 3 AMOLED + FPC
    prism(circ(MOD_R), -2.0, -0.5, D['amoled'], lambda: face(circ(ACT_R), -0.5 + D['amoled'], 'o3'), cls='f2')
    prism(rrect(12, 8, 0.5, 0, -24.0), -2.2, -2.0, D['amoled'], cls='f2', face_cls='o2')
    A[3] = cur[0].p(*polar(150, MOD_R), -0.5 + D['amoled'])
    # 4 carrier
    def car_x():
        z = -0.5 + D['carrier']
        face(circ(23.2), z, 'o2')
        for a in (90, 210, 330):
            face(circ(0.9, *polar(a, 22.5), 12), -4.8 + D['carrier'], 'o3')
    prism(circ(CAR_O), -4.8, -0.5, D['carrier'], car_x, cls='ob', face_cls='o', hole=23.2)
    A[4] = cur[0].p(*polar(160, CAR_O), -0.5 + D['carrier'])
    # 5 PCB + shield
    prism(circ(MOD_R), -3.0, -2.2, D['pcb'], lambda: face(rrect(10, 4, 0.3, 0, 18), -2.2 + D['pcb'], 'ph'), cls='ob')
    prism(rrect(16, 16, 1.0), -4.5, -3.0, D['pcb'], cls='ob', face_cls='o2', bias=-0.5)
    A[5] = cur[0].p(*polar(165, MOD_R), -2.2 + D['pcb'])
    # ---- column 2: rear sub-assembly
    a_ = cur[0].p(0, 0, D['case'] + 12); b_ = cur[0].p(0, 0, D['pcb'] - 10)
    sh.line(a_[0], a_[1], b_[0], b_[1], 'c')
    cur[0] = AX2
    # 6 gasket
    prism(circ(24.3), -5.25, -4.8, D['gasket'], None, cls='ob', face_cls='o2', hole=21.9)
    A[6] = cur[0].p(*polar(160, 24.3), -4.8 + D['gasket'])
    # 10 LED flex
    def led_x():
        face(circ(24.5), -5.15 + D['led'], 'o3')
        for i in range(12):
            c = polar(15 + 30 * i, 25.2)
            face(rrect(1.0, 1.0, 0.1, *c), -4.65 + D['led'], 'o2')
    prism(circ(H_OUT), -5.25, -5.15, D['led'], led_x, cls='ob', face_cls='o2', hole=24.5)
    A[10] = cur[0].p(*polar(195, 25.2), -4.65 + D['led'])
    # 7 dome + flex
    prism(rrect(8, 16, 1.0, 0, -4), -5.25, -5.15, D['dome'], cls='ob', face_cls='o2')
    prism(circ(2.5, 0, 0, 24), -5.15, -4.8, D['dome'], cls='ob', face_cls='o', bias=8.0)
    A[7] = cur[0].p(-2.5, 0, -4.8 + D['dome'])
    # 8 mid-frame
    prism(circ(H_OUT), Z_MF1, Z_MF0, D['mid'], lambda: face(rrect(6, 3, 0.5, 0, -18), Z_MF0 + D['mid'], 'o3'), cls='ob')
    A[8] = cur[0].p(*polar(200, H_OUT), Z_MF0 + D['mid'])
    # 11 speaker, 12 LRA
    prism(rrect(2 * SPK['x'], SPK['y1'] - SPK['y0'], 1.0, 0, (SPK['y0'] + SPK['y1']) / 2), SPK['z1'], SPK['z0'], D['spk'],
          lambda: face(rrect(8, 4, 1.5, 0, 20), SPK['z0'] + D['spk'], 'o3'))
    A[11] = cur[0].p(SPK['x'], 21, SPK['z0'] + D['spk'])
    prism(circ(LRA['r'], *LRA['c'], 30), LRA['z1'], LRA['z0'], D['spk'],
          lambda: face(circ(1.6, *LRA['c'], 16), LRA['z0'] + D['spk'], 'o3'))
    A[12] = cur[0].p(-LRA['r'], -20, LRA['z0'] + D['spk'])
    # 13 cell
    def cell_x():
        z = CELL['z0'] + D['cell']
        face([(-17.0, -CELL['y']), (-17.0, CELL['y'])], z, 'o3')
        c = cur[0].p(1.5, 0, z)
        sh.text(c[0], c[1] + 1, '603040  650 mAh', 2.2, 'middle', 'tx')
    prism(rrect(2 * CELL['x'], 2 * CELL['y'], 1.0), CELL['z1'], CELL['z0'], D['cell'], cell_x)
    A[13] = cur[0].p(-CELL['x'], 8, CELL['z0'] + D['cell'])
    # 14 pad
    prism(circ(10.0, 0, 0, 40), -13.9, CELL['z1'], D['pad'], cls='ob', face_cls='o2')
    A[14] = cur[0].p(-7, 7, CELL['z1'] + D['pad'])
    # 15 O-ring
    prism(circ(26.9), -9.75, -9.05, D['oring'], None, cls='ob', face_cls='o2', hole=26.2)
    A[15] = cur[0].p(*polar(205, 26.9), -9.05 + D['oring'])
    # 16 caseback (inside faces the viewer)
    def back():
        dz = D['back']
        pts = []
        for r_ in [RO] + [RO - 0.5 * i for i in range(1, 8)] + [20, 14, 8, 2]:
            zz = Z_SPLIT if r_ >= RO else min(zo(r_), FCZ if r_ > tpx_ else zo(r_))
            pts += [(x, y, zz) for x, y in circ(r_, n=48)]
        P = [cur[0].p(x, y, z + dz) for x, y, z in pts]
        sh.poly(hull(P), 'ob')
        sh.poly([cur[0].p(x, y, Z_SPLIT + dz) for x, y in circ(RO)], 'o')
        sh.poly([cur[0].p(x, y, Z_SPLIT + dz) for x, y in circ(SK_I)], 'o2')
        sh.poly([cur[0].p(x, y, -10.8 + dz) for x, y in circ(25.3)], 'o3')
        for a in LUGS:
            sh.poly([cur[0].p(x, y, -9.9 + dz) for x, y in arc_pts(0, 0, SK_I, a - 9, a + 9 + 20, 10)], 'o2', close=False)
        for r_ in (13.0, 17.0):
            sh.poly([cur[0].p(x, y, zi(r_) + dz) for x, y in circ(r_, n=72)], 'ph')
        sh.poly([cur[0].p(x, y, BOSS_Z + dz) for x, y in rrect(6, 6, 2.9)], 'o3')
        c = cur[0].p(0, -9, zi(9) + dz)
        sh.text(c[0], c[1] + 0.8, 'birth certificate engraved inside', 1.9, 'middle', 'td')
    tpx_ = INFO['tp'][0]
    items.append((cur[0].t(0, 0, -12 + D['back'])[1], back))
    A[16] = cur[0].p(*polar(210, RO), Z_SPLIT + D['back'])

    a_ = cur[0].p(0, 0, D['gasket'] + 10)
    b_ = cur[0].p(0, 0, D['back'] - 22)
    sh.line(a_[0], a_[1], b_[0], b_[1], 'c')
    for d, fn in sorted(items, key=lambda q: q[0]):
        fn()

    off = OFFX
    for n, (dx, dy) in off.items():
        ax, ay = A[n]
        sh.balloon(dx, dy, n, tip=A[n]) if n in ABS else sh.balloon(ax + dx, ay + dy, n, tip=A[n])
    sh.text(20, 18.5, 'EXPLODED VIEW  ·  NTS  ·  LEFT: FRONT SUB-ASSEMBLY  ·  RIGHT: REAR SUB-ASSEMBLY', 3.0, 'start', 'tx', weight='bold')
    steps = [
        'ASSEMBLY SEQUENCE (E)',
        '1  Laminate glass (2) + AMOLED (3); bond into floating carrier (4); fit PCB (5), connect display FPC.',
        '2  Case (1) face-down in a nest: crown (17) + contacts (18) pinned and bonded; press halo pipe (9).',
        '3  Drop the floating unit (2-5) into the case; lay gasket (6), halo LED flex (10), speaker (11).',
        '4  Mid-frame (8) with dome (7) + LRA (12): bond to the case at 0.30 preload; check 2.5-3.5 N click.',
        '5  Cell (13) on foam (14), plug in - no adhesive. O-ring (15) on the spigot.',
        '6  Caseback (16): align lugs, push, twist 1/8 turn. Test halo, press, charge via crown, IP54.',
    ]
    for i, t_ in enumerate(steps):
        sh.text(18, 228 + i * 4.5, t_, 2.5 if i == 0 else 2.12, 'start', 'tx' if i == 0 else 'td', weight='bold' if i == 0 else None)

    # parts list
    tx0, ty0 = 252.0, 16.0
    cols = [0, 8, 57, 64, 136, 143, 158]
    sh.text(tx0, ty0 + 2.5, 'PARTS LIST', 3.0, 'start', 'tx', weight='bold')
    rows = []
    for n, part, q, spec, src, g in BOM:
        rows.append((n, part, q, spec, src, (('%.1f' % g) if g is not None else '',)))
    rows = [tuple(c if c != ('',) else '' for c in r) for r in rows]
    yend = table(sh, tx0, ty0 + 6, cols, ['#', 'PART', 'QTY', 'MATERIAL / SPEC', 'S', 'g'], rows, rh=6.6, size=2.0)
    tot = sum(g for *_, g in BOM if g)
    sh.rect(tx0, yend, cols[-1], 13.2, 'fr2t')
    sh.text(tx0 + 9, yend + 4.8, 'DEVICE MASS, Bone (PC caseback)', 2.2, 'start', 'tx', weight='bold')
    sh.text(tx0 + cols[-1] - 0.8, yend + 4.8, '≈%.0f' % tot, 2.4, 'end', 'tx', weight='bold')
    sh.text(tx0 + 9, yend + 11.2, 'Heirloom: 316L caseback 0.6 wall ≈11 g', 2.2, 'start', 'tx')
    sh.text(tx0 + cols[-1] - 0.8, yend + 11.2, '≈%.0f' % (tot + 6.0), 2.4, 'end', 'tx', weight='bold')
    notes = [
        'S = source: V verified STEP · K spec sheet · E estimate',
        'Research budget (07 §3.3): ≈50 g PC back, ≈56 g steel.',
        'Not in mass: cord 75 cm + breakaway clasp, fob chain,',
        'Altar dock (magnetic crown seat, pogo, 15-20° tilt).',
        'Floating unit (2-5) ≈16.7 g rides on gasket 6 + dome 7.',
    ]
    for i, n_ in enumerate(notes):
        sh.text(tx0, yend + 18.5 + i * 3.5, n_, 2.0, 'start', 'td')
    print('mass', tot, tot + 6)
    sh.title_block('EXPLODED VIEW · PARTS LIST', 'PRODUCTION TARGET · 18 items', 'NTS', '3 / 4', 'SOUL-V3-003')
    return sh


# ================================================================ SHEET 4 : DEV PROTOTYPE ON WAVESHARE 1.75
# z = 0 at the rim face, glass front at +0.6. Board data (V) from the STEP model, native orientation
# (USB-C at 6 o'clock); STEP depths d are measured from the glass front -> z = 0.6 - d.
QR, QTB, QRF, QRB, QRD = 30.0, 19.6, 1.5, 2.0, 3000.0
Q_SPLIT = -15.0
Q_HIN, Q_HOUT = 24.78, 25.78
Q_SPI, Q_SPO, Q_SKI = 27.8, 28.8, 28.9
Q_PROF, Q_INFO = profile(QR, QTB, QRD, QRF, QRB)
Q_FCZ = Q_INFO['fc'][1]
Q_ZC = -QTB + QRD
QZ = lambda d: GP - d
Q_SO = [(14.70, 13.75), (14.70, -13.75), (-20.50, 0.0)]
Q_PWR, Q_BOOT = ((-11.31, 17.20), 123.3), ((11.31, 17.10), 56.5)
Q_MICS = [((-10.96, -17.54), 238.0), ((11.74, -17.35), 304.1)]
Q_HDR = dict(x0=17.4, x1=20.0, y0=-10.0, y1=10.0)            # extent (E), depth 12.70 (V)
Q_USB = dict(x=4.5, y0=-23.8, y1=-16.5, zc=QZ(8.55))
Q_CELL = dict(x0=-23.0, x1=17.0, y=15.0, z0=-12.08, z1=-18.08)
Q_SPK = dict(x=6.0, y0=16.0, y1=24.0, z0=-12.08, z1=-14.58)
Q_LRA = dict(c=(0.0, -20.0), r=4.0, z0=-12.08, z1=-15.28)
Q_CR = dict(dy=2.0, z0=-4.0, z1=-14.0)
Q_CAR, Q_FL0, Q_FL1 = (23.4, 24.4), QZ(10.43), QZ(10.43) - 0.8     # carrier wall, floor
Q_MP0, Q_MP1 = Q_FL1 - 0.45, Q_FL1 - 1.25                          # mid-plate


def qzo(r):
    return Q_ZC - math.sqrt(QRD * QRD - r * r)


def qzi(r):
    return Q_ZC - math.sqrt((QRD - 1.2) ** 2 - r * r)


def q_crown():
    return [(x, y + Q_CR['dy']) for x, y in crown_head()]


def q_ray(o, a):
    dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
    t = 0.0
    while math.hypot(o[0] + dx * t, o[1] + dy * t) < QR:
        t += 0.05
    return (o[0] + dx * t, o[1] + dy * t)


def q_case_half(sg):
    if sg > 0:
        pts = [(Q_HOUT, 0.0), (QR - QRF, 0.0)] + arc_pts(QR - QRF, -QRF, QRF, 90, 0, 8) + [
            (QR, Q_SPLIT), (Q_SPO, Q_SPLIT), (Q_SPO, -15.85), (28.4, -15.85), (28.4, -16.55), (Q_SPO, -16.55),
            (Q_SPO, -17.3), (Q_SPI, -17.3), (Q_SPI, -6.0), (24.6, -6.0), (24.6, -5.05), (Q_HOUT, -5.05)]
        return [pts]
    up = [(Q_HOUT, 0.0), (QR - QRF, 0.0)] + arc_pts(QR - QRF, -QRF, QRF, 90, 0, 8) + [(QR, -4.45), (Q_HOUT, -4.45)]
    lo = [(QR, -11.45), (QR, Q_SPLIT), (Q_SPO, Q_SPLIT), (Q_SPO, -15.85), (28.4, -15.85), (28.4, -16.55), (Q_SPO, -16.55),
          (Q_SPO, -17.3), (Q_SPI, -17.3), (Q_SPI, -11.45)]
    return [[(-a, b) for a, b in up], [(-a, b) for a, b in lo]]


def q_caseback():
    out = back_curve(QR, QTB, QRD, QRB)
    inner = [(s_, qzi(abs(s_))) for s_ in [-Q_SPI + 0.5 * i for i in range(int(2 * Q_SPI / 0.5) + 1)]] + [(Q_SPI, qzi(Q_SPI))]
    return [(QR, Q_SPLIT)] + out + [(-QR, Q_SPLIT), (-Q_SKI, Q_SPLIT), (-Q_SKI, -17.5), (-Q_SPI, -17.5)] + inner + \
           [(Q_SPI, -17.5), (Q_SKI, -17.5), (Q_SKI, Q_SPLIT)]


def sheet_proto(theme):
    sh = Sheet3(theme)
    sh.frame()
    k = 2.0
    VF = View(95, 166, k)
    VT = View(95, 72, k)
    VS = View(192, 166, k)
    TY = 238.0
    cx, cy = VF.p(0, 0)

    # ---------- FRONT ----------
    sh.poly(VF.pl(q_crown()), 'o')
    sh.circle(cx, cy, QR * k, 'o')
    sh.circle(cx, cy, (QR - QRF) * k, 'o3')
    sh.circle(cx, cy, Q_HOUT * k, 'o')
    sh.circle(cx, cy, Q_HIN * k, 'o2')
    sh.circle(cx, cy, G_R * k, 'o')
    sh.circle(cx, cy, ACT_R * k, 'ph')
    sh.circle(*VF.p(0, CR['eye_y'] + Q_CR['dy']), CR['eye_r'] * k, 'o')
    eyes(sh, VF, 0, 1.5)
    sh.circle(cx, cy, MOD_R * k, 'h')
    sh.circle(cx, cy, Q_CAR[1] * k, 'h')
    for x, y in Q_SO:
        px, py = VF.p(x, y)
        sh.circle(px, py, 1.6 * k, 'h')
        sh.line(px - 2.4 * k, py, px + 2.4 * k, py, 'c')
        sh.line(px, py - 2.4 * k, px, py + 2.4 * k, 'c')
    H = Q_HDR
    sh.poly(VF.pl(box(H['x0'], H['x1'], H['y0'], H['y1'])), 'h')
    U = Q_USB
    sh.poly(VF.pl(box(-U['x'], U['x'], U['y1'], U['y0'])), 'h')
    for sx in (-1, 1):
        sh.line(*VF.p(sx * 6.2, -math.sqrt(Q_HOUT ** 2 - 6.2 ** 2)), *VF.p(sx * 6.2, -math.sqrt(QR ** 2 - 6.2 ** 2)), 'o2')
    C = Q_CELL
    sh.poly(VF.pl(box(C['x0'], C['x1'], -C['y'], C['y'])), 'ph')
    sh.poly(VF.pl(rrect(2 * Q_SPK['x'], Q_SPK['y1'] - Q_SPK['y0'], 0.8, 0, (Q_SPK['y0'] + Q_SPK['y1']) / 2)), 'h')
    sh.poly(VF.pl(circ(Q_LRA['r'], *Q_LRA['c'], 40)), 'h')
    sh.poly(VF.pl(circ(2.5, 0, 0, 30)), 'h')
    holes = []
    for (o, a), d in ((Q_PWR, 2.6), (Q_BOOT, 1.6)):
        e = q_ray(o, a)
        sh.line(*VF.p(*o), *VF.p(*e), 'h')
        sh.circle(*VF.p(*o), 0.9 * k, 'o3')
        sh.circle(*VF.p(*e), d / 2 * k, 'o2')
        holes.append(e)
    for o, a in Q_MICS:
        e = q_ray(o, a)
        sh.line(*VF.p(*o), *VF.p(*e), 'h')
        holes.append(e)
    sh.line(cx, VF.p(0, 38.5)[1], cx, VF.p(0, -33)[1], 'c')
    sh.line(VF.p(-33, 0)[0], cy, VF.p(33, 0)[0], cy, 'c')
    ya, yb = VF.p(0, 40.5)[1], VF.p(0, -33.5)[1]
    sh.line(cx, ya, cx, yb, 'cut')
    sh.section_arrow(cx, ya, 'B', (-1, 0))
    sh.section_arrow(cx, yb, 'B', (-1, 0))
    lead_l(sh, VF.p(*holes[0]), 98, ['PWR PIN HOLE Ø2.6', '(V position)'])
    lead_l(sh, VF.p(*polar(150, Q_HOUT - 0.5)), 110, ['HALO Ø49.56/Ø51.56', 'clear resin, sanded'])
    lead_l(sh, VF.p(-20.5 - 1.1, 1.1), 150, ['3× M2 STANDOFF (V)', '→ carrier screws'])
    lead_l(sh, VF.p(C['x0'], -8), 170, ['CELL 603040', '3.0 OFF-CENTRE'])
    lead_l(sh, VF.p(*holes[2]), 216, ['2× MIC Ø1.0', '(port dir. ?)'])
    lead_l(sh, VF.p(-6.2, -28.5), 228, ['USB-C CUT 12.4×7.0', 'dev charging (V pos.)'])
    lead_r(sh, VF.p(*holes[1]), 158, 100, ['BOOT Ø1.6'])
    lead_r(sh, VF.p(Q_SPK['x'], 21), 158, 110, ['SPK 1208'])
    lead_r(sh, VF.p(H['x1'], 6), 158, 142, ['8-PIN', 'HEADER', '12.70 (V)'])
    lead_r(sh, VF.p(1.8, -1.8), 158, 168, ['DOME Ø5', '(centre)'])
    lead_r(sh, VF.p(Q_LRA['r'], -20), 158, 214, ['LRA Ø8'])
    sh.text(cx, TY, 'FRONT VIEW · BOARD PLACEMENT', 3.2, 'middle', 'tx', weight='bold')

    # ---------- TOP ----------
    def pt(x, z):
        return VT.p(x, -z)
    sh.poly([pt(s_, z) for s_, z in Q_PROF], 'o')
    sh.poly([pt(*q) for q in glass_prof()], 'o', close=False)
    sh.line(*pt(-QR, Q_SPLIT), *pt(QR, Q_SPLIT), 'o2')
    sh.line(*pt(-QR, -QRF), *pt(QR, -QRF), 'o3')
    sh.poly([pt(x, z) for x, z in rrect(2 * CR['hw'], Q_CR['z0'] - Q_CR['z1'], 0.8, 0, (Q_CR['z0'] + Q_CR['z1']) / 2)], 'ob')
    for sx in (-1, 1):
        sh.poly([pt(sx * 2.9, -12.4), pt(sx * 4.2, -12.4), pt(sx * 4.2, -13.6), pt(sx * 2.9, -13.6)], 'h')
    for (o, a), d in ((Q_PWR, 2.6), (Q_BOOT, 1.6)):
        e = q_ray(o, a)
        sh.circle(*pt(e[0], QZ(7.60)), d / 2 * k, 'o2')
    sh.line(*pt(0, 2.2), *pt(0, -21.5), 'c')
    ytop = pt(0, -QTB)[1]
    sh.dim_h(*pt(-QR, -8), *pt(QR, -8), ytop - 6, '60.0')
    sh.dim_v(*pt(-QR, 0), *pt(-QR, Q_FCZ), pt(-QR, 0)[0] - 6, '17.5')
    lead_r(sh, pt(4.5, -9.0), 158, 34, ['PROTO CROWN 9×6×10', 'covers speaker slot'])
    lead_r(sh, pt(4.2, -13.0), 158, 46, ['SPEAKER SLOTS z −13'])
    lead_r(sh, pt(QR, Q_SPLIT), 158, 58, ['BAYONET z −15.0 (E)'])
    lead_r(sh, pt(*q_ray(*Q_BOOT)[:1], QZ(7.6)) if False else pt(q_ray(*Q_BOOT)[0], QZ(7.6)), 158, 68, ['PWR / BOOT z −7.0 (V)'])
    sh.text(pt(0, 0)[0], ytop - 11.5, 'TOP VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- SECTION B-B ----------
    th = sh.th

    def ps(z, y):
        return VS.p(-z, y)

    class VSV:
        @staticmethod
        def pl(pts):
            return [ps(z, s_) for s_, z in pts]

        @staticmethod
        def p(s_, z):
            return ps(z, s_)
    V = VSV
    for sg in (1, -1):
        for part in q_case_half(sg):
            region(sh, V, part, 'hA')
    region(sh, V, q_caseback(), 'hB')
    for sg in (1, -1):
        m = lambda pts: [(sg * a, b) for a, b in pts]
        region(sh, V, m(box(Q_HIN, Q_HOUT, 0.0, -4.4)), cls='o2', fill=th['acc'] + '" fill-opacity="0.22')
        if sg > 0:
            region(sh, V, m(box(24.8, 25.7, -4.45, -4.95)), cls='o3', fill=th['acc'])
            region(sh, V, m(box(24.6, Q_HOUT, -4.95, -5.05)), cls='o3', fill=th['dim'])
            region(sh, V, m(box(Q_CAR[0], Q_CAR[1], -0.5, Q_FL0)), 'hC')
            region(sh, V, m(box(20.0, 24.2, Q_FL1, Q_MP0)), 'hD', cls='o3')
            region(sh, V, box(0, Q_SPI, Q_MP0, Q_MP1), 'hA')
            region(sh, V, box(0, Q_CAR[1], Q_FL0, Q_FL1), 'hC')
        else:
            region(sh, V, m(box(Q_CAR[0], Q_CAR[1], -0.5, -5.8)), 'hC')
            region(sh, V, m(box(20.0, 23.6, Q_FL1, Q_MP0)), 'hD', cls='o3')
            region(sh, V, box(-23.6, 0, Q_MP0, Q_MP1), 'hA')
            region(sh, V, box(-23.6, 0, Q_FL0, Q_FL1), 'hC')
        sh.circle(*V.p(sg * 28.55, -16.2), 0.33 * k, 'o3', extra='style="fill:%s"' % th['fg'])
    sh.poly(V.pl(glass_prof()), 'gl')
    region(sh, V, box(-MOD_R, MOD_R, -0.5, QZ(5.70)), cls='f2')
    region(sh, V, box(-MOD_R, MOD_R, QZ(5.70), QZ(6.90)), 'hC')
    for s0, s1, d in ((-14.0, -4.0, 8.9), (2.0, 13.0, 8.9), (13.5, 16.0, 7.9)):
        region(sh, V, box(s0, s1, QZ(6.90), QZ(d)), cls='f2')
    region(sh, V, box(U['y0'], U['y1'], U['zc'] + 1.6, U['zc'] - 1.6), 'hS')
    for zz in (-4.45, -11.45):
        sh.line(*V.p(-QR, zz), *V.p(-Q_HOUT, zz), 'o3')
    sh.poly(V.pl(box(H['y0'], H['y1'], QZ(6.90), QZ(12.70))), 'h')
    sh.poly(V.pl(box(Q_SO[0][1] - 1.6, Q_SO[0][1] + 1.6, QZ(6.90), QZ(10.43))), 'h')
    sh.poly(V.pl(box(-Q_SO[0][1] - 1.6, -Q_SO[0][1] + 1.6, QZ(6.90), QZ(10.43))), 'h')
    region(sh, V, box(-4.0, 4.0, Q_MP0 + 0.1, Q_MP0), cls='o3', fill=th['dim'])
    dm = [(-2.5, Q_MP0 + 0.1)] + [(2.5 * math.cos(math.radians(a)), Q_MP0 + 0.1 + 0.35 * math.sin(math.radians(a))) for a in range(180, -1, -10)]
    sh.poly(V.pl(dm), 'o2', extra='style="fill:url(#hS)"')
    C = Q_CELL
    region(sh, V, box(-C['y'], C['y'], C['z0'], C['z1']), cls='fb')
    region(sh, V, box(-12, 12, C['z1'], qzi(12) + 0.02), 'hD', cls='o3')
    region(sh, V, box(Q_SPK['y0'], Q_SPK['y1'], Q_SPK['z0'], Q_SPK['z1']), cls='f2')
    for zz in (-12.4, -13.6):
        sh.line(*V.p(Q_SPK['y1'], zz), *V.p(QR, zz), 'h')
    region(sh, V, box(-24.0, -16.0, Q_LRA['z0'], Q_LRA['z1']), cls='f2')
    region(sh, V, box(28.3, QR + 0.02, -8.0, -10.0), 'hS')
    ey = CR['eye_y'] + Q_CR['dy']
    region(sh, V, box(QR, ey - CR['eye_r'], Q_CR['z0'], Q_CR['z1']), 'hS')
    tp = CR['top'] + Q_CR['dy']
    top = [(ey + CR['eye_r'], Q_CR['z0'])] + arc_pts(tp - 0.8, Q_CR['z0'] - 0.8, 0.8, 90, 0, 6) + \
          arc_pts(tp - 0.8, Q_CR['z1'] + 0.8, 0.8, 0, -90, 6) + [(ey + CR['eye_r'], Q_CR['z1'])]
    region(sh, V, top, 'hS')
    sh.poly(V.pl(Q_PROF), 'o')
    sh.poly(V.pl(glass_prof()), 'o', close=False)
    sh.line(*ps(2.2, 0), *ps(-21.5, 0), 'c')
    xr = ps(-QTB, 0)[0]
    sh.dim_v(*ps(-8, QR), *ps(-8, -QR), xr + 6, '60.0')
    sh.dim_v(*ps(Q_CR['z1'], tp), *ps(-12, -QR), xr + 13, '66.0 OVERALL')
    yy = ps(0, -9)[1]
    sh.line(ps(GP, -9)[0], yy, ps(qzo(9), -9)[0], yy, 't')
    sh.arrow(ps(GP, -9), ps(-5, -9))
    sh.arrow(ps(qzo(9), -9), ps(-10, -9))
    tw_ = sh.tw('20.2 @ CL', 2.4)
    sh.rect(ps(-10, 0)[0] - tw_ / 2 - 0.8, yy + 0.9, tw_ + 1.6, 3.4, 'bgf')
    sh.text(ps(-10, 0)[0], yy + 3.4, '20.2 @ CL', 2.4, 'middle', 'td')
    xa = xr + 21
    lead_r(sh, ps(QZ(6.3), 20.0), xa, 104, ['PCB 5.70/6.90 (V)'])
    lead_r(sh, ps(Q_FL0 - 0.4, 22), xa, 114, ['FLOATING CARRIER', 'on standoffs'])
    lead_r(sh, ps(Q_MP0 + 0.2, 1.0), xa, 126, ['DOME Ø5 ON', 'MID-PLATE'])
    lead_r(sh, ps(QZ(12.70), 8), xa, 138, ['HEADER 12.70', '(projected)'])
    lead_r(sh, ps(-15.0, 10), xa, 152, ['CELL 603040', 'z −12.1…−18.1'])
    lead_r(sh, ps(-13.3, 22), xa, 92, ['SPK 1208', 'fires under crown'])
    lead_r(sh, ps(-16.2, -28.55), xa, 176, ['O-RING, BAYONET', 'z −15.0 (E)'])
    lead_r(sh, ps(U['zc'], -20), xa, 196, ['USB-C z −7.95 (V)', 'plug blocks press'])
    lead_r(sh, ps(-13.5, -20), xa, 208, ['LRA Ø8'])
    lead_r(sh, ps(qzo(18) + 0.3, -18), xa, 220, ['FLAT BACK', 'WALL 1.2 (E)'])
    sh.text(ps(-10, 0)[0], TY, 'SECTION B-B', 3.2, 'middle', 'tx', weight='bold')

    # ---------- table ----------
    tx0, ty0 = 298.0, 16.0
    sh.text(tx0, ty0 + 2.5, 'WAVESHARE ESP32-S3-TOUCH-AMOLED-1.75', 2.45, 'start', 'tx', weight='bold')
    sh.text(tx0, ty0 + 6.3, 'native orientation, USB-C at 6 o\'clock', 2.0, 'start', 'td')
    rows = [
        ('Cover glass', 'Ø48.96 × 1.10', 'V'),
        ('Active / touch area', 'Ø43.76', 'V'),
        ('Display module + PCB', 'Ø46.0', 'V'),
        ('PCB front / back depth', '5.70 / 6.90', 'V'),
        ('Deepest: 8-pin header, edge', '12.70', 'V'),
        ('Deepest under cell footprint', '8.90', 'V'),
        ('M2 standoffs (3), end depth', '10.43', 'V'),
        ('USB-C face r / tongue depth', '23.80 / 8.55', 'V'),
        ('PWR / BOOT key depth', '7.60', 'V'),
        ('Cell 603040 ≈650 mAh', '6×30×40', 'K'),
        ('Carrier floor / mid-plate', '0.8 / 0.8 SLA', 'E'),
        ('Dome travel / gasket', '0.35 / 0.45', 'E'),
        ('Envelope (glass → back)', 'Ø60 × 20.2', 'E'),
        ('Mass (SLA, est.)', '≈70-75 g', 'E'),
    ]
    yend = table(sh, tx0, ty0 + 9, [0, 64, 101, 112], ['ITEM', 'VALUE (mm)', 'SRC'], rows, rh=5.9, size=2.05)
    notes = [
        'PROTOTYPE NOTES / FIT CHECK',
        '1. Stack at CL: glass +0.6, board to 10.43,',
        '   carrier 0.8, dome 0.45, mid-plate 0.8,',
        '   cell 6.0, pad 0.3, back 1.2 = 20.2.',
        '2. 603040 cannot sit centred: the 8-pin',
        '   header (x 17.4-20, 12.7 deep) is in the',
        '   cell band. Shifted 3.0 → 0.4 to header,',
        '   corner r 27.46 → 0.34 to the spigot.',
        '3. Ø58 does NOT fit this cell + header;',
        '   Ø58 only with header desoldered or a',
        '   503040 / 502535 cell. Ø60 drawn.',
        '4. Halo LEDs: 1010 on a flex ring (no LED',
        '   rim on the Waveshare board).',
        '5. Raise AXP2101 charge to ~325 mA (0.5C).',
    ]
    for i, n_ in enumerate(notes):
        sh.text(tx0, yend + 5 + i * 3.45, n_, 2.4 if i == 0 else 2.05, 'start', 'tx', weight='bold' if i == 0 else None)
    sh.title_block('GA · DEV PROTOTYPE', 'WAVESHARE 1.75 · Ø60 × 20.2', '2:1', '4 / 4', 'SOUL-V3-004')
    return sh


def write(sh, name):
    p = os.path.join(OUT, name)
    open(p, 'w', encoding='utf-8').write(sh.svg())
    print('svg', p)
    return p


if __name__ == '__main__':
    which = sys.argv[1:] or ['ga']
    if 'ga' in which:
        write(sheet_ga('blue'), 'soul_v3_ga.svg')
        write(sheet_ga('white'), 'soul_v3_ga_white.svg')
    if 'sec' in which:
        write(sheet_section('blue'), 'soul_v3_section.svg')
    if 'exp' in which:
        write(sheet_exploded('blue'), 'soul_v3_exploded.svg')
    if 'pro' in which:
        write(sheet_proto('blue'), 'soul_v3_proto.svg')
