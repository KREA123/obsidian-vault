"""Generate the SOUL blueprint sheets (SVG). Run from anywhere:  python3 gen_sheets.py
Geometry source: research/06-product-design-v2 (sections 2-3, 5) + STEP-verified 1.75" board data
from the project CAD (cad/README.md). Values tagged (E) are engineering estimates.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from bp import *

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ---------------------------------------------------------------- production target (E unless noted)
PR = dict(a=30.0, R=30.0, cy=4.0, b=38.0, n=2.6)      # plan: 60 wide x 68 tall, display centre +4.0
T, RD, RF, RB = 19.0, 80.0, 4.0, 3.0                  # centre thickness, dome R, edge rounds
Z_PART = -7.0                                          # parting line front/back shell
G_R, G_T = 24.48, 1.10                                 # cover glass (V, STEP)
ACT_R = 21.88                                          # active / touch area (V)
MOD_R = 23.0                                           # module + PCB (V)
LIP_IN, LIP_OUT, LIP_H = 24.58, 25.38, 0.4             # frosted lip (research: 0.3-0.5 proud)
BTN_A, BTN_SPAN = 35.0, 15.2                           # button centre angle (deg from +x), span (8 mm)
MIC_A = (60.0, 120.0)                                  # mic ports on the upper perimeter (E)
SCREWS = [(18, 22), (-18, 22), (15, -24), (-15, -24)]
PADS = [(0, -15), (0, -19)]
POCKET = dict(x=5.0, y0=29.5, y1=33.0, z0=-8.5, z1=-12.5, bar_y=31.2, bar_z=-10.3)

OUTL = outline(**PR)
PROF_Y, INFO_Y = profile(34.0, T, RD, RF, RB)
PROF_X, INFO_X = profile(30.0, T, RD, RF, RB)


def on_arc(a, r=30.0, cy=4.0):
    return (r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))


def eyes(sh, V, cx, cy, k=1.0, c='ph'):
    """Two 'living eyes' (reference UI graphic), rounded capsules."""
    for sx in (-1, 1):
        ex = cx + sx * 7.2 * k
        w, h = 7.4 * k, 12.5 * k
        r = w / 2
        pts = arc_pts(ex, cy + h / 2 - r, r, 0, 180, 12) + arc_pts(ex, cy - h / 2 + r, r, 180, 360, 12)
        sh.poly(V.pl(pts), c)
        # highlight
        hx, hy = ex + sx * -1.3 * k, cy + 3.0 * k
        sh.poly(V.pl(arc_pts(hx, hy, 1.1 * k, 0, 360, 16)), c)


# ================================================================ SHEET 1 : GA
def sheet_ga(theme):
    sh = Sheet(theme)
    sh.frame()
    k = 2.0
    VF = View(92, 160, k)             # front
    VT = View(92, 70, k)              # top   (u = x, v = -z)
    VS = View(190, 160, k)            # right side (u = -z, v = y)
    VB = View(332, 160, k, flipx=True)  # rear
    TY = 236.5                        # view-title baseline

    # ---------- FRONT VIEW ----------
    sh.poly(VF.pl(OUTL), 'o')
    sh.poly(VF.pl(offset_poly(OUTL, RF)), 'o3')                      # tangent edge of front round
    sh.poly(VF.pl(arc_pts(0, 4, LIP_OUT, 0, 360, 120)), 'o')          # lip outer
    sh.poly(VF.pl(arc_pts(0, 4, G_R, 0, 360, 120)), 'o2')             # glass edge / lip inner
    sh.poly(VF.pl(arc_pts(0, 4, ACT_R, 0, 360, 120)), 'ph')           # active area
    eyes(sh, VF, 0, 5.5)
    x0, y0 = VF.p(0, 0)
    yd = VF.p(0, 4)[1]
    sh.line(x0, VF.p(0, 37)[1], x0, VF.p(0, -37)[1], 'c')
    sh.line(VF.p(-34, 4)[0], yd, VF.p(34, 4)[0], yd, 'c')
    sh.line(VF.p(-34, 0)[0], y0, VF.p(-27, 0)[0], y0, 'c')
    sh.line(VF.p(27, 0)[0], y0, VF.p(34, 0)[0], y0, 'c')
    a0, a1 = BTN_A - BTN_SPAN / 2, BTN_A + BTN_SPAN / 2
    for a in (a0, a1):
        sh.line(*VF.p(*on_arc(a, 30.0)), *VF.p(*on_arc(a, 28.6)), 'o2')
    sh.poly(VF.pl(arc_pts(0, 4, 28.6, a0, a1, 12)), 'h', close=False)
    for a in MIC_A:
        sh.line(*VF.p(*on_arc(a, 30.0)), *VF.p(*on_arc(a, 27.0)), 'h')
    for i in range(-4, 5):
        cx, cy = on_arc(270 + i * 3.44, 30.0)
        sh.circle(*VF.p(cx, cy), 0.4 * k, 'o2')
    # section line A-A
    ya, yb = VF.p(0, 40)[1], VF.p(0, -40)[1]
    sh.line(x0, ya, x0, yb, 'cut')
    sh.section_arrow(x0, ya, 'A', (-1, 0))
    sh.section_arrow(x0, yb, 'A', (-1, 0))
    # display-centre offset
    xl = VF.p(-34, 0)[0]
    sh.line(xl, yd, 18.4, yd, 't')
    sh.line(xl, y0, 18.4, y0, 't')
    sh.dim_v(20, yd, 20, y0, 20, '4.0', gap=0, tside=-1)
    sh.text(24.2, y0 + 1.2, 'BODY CL', 1.9, 'start', 'td')
    sh.text(24.2, yd - 0.9, 'DISPLAY CL', 1.9, 'start', 'td')
    cxp, cyp = VF.p(0, 4)
    # R30 concentric
    t = VF.p(*on_arc(113, 30))
    sh.line(cxp, cyp, t[0], t[1], 't')
    sh.arrow(t, (cxp, cyp))
    sh.text(cxp - 8.2, cyp - 31, 'R30', 2.6, 'middle', 'td')
    # upper-left callouts
    lead_l(sh, VF.p(*on_arc(MIC_A[1], 30.0)), 88, ['2× MIC PORT Ø0.8 (E)'])
    lead_l(sh, VF.p(*on_arc(150, LIP_OUT)), 97, ['Ø50.76 FROSTED LIP', '0.4 PROUD (0.3-0.5)'])
    lead_l(sh, VF.p(*on_arc(160, G_R)), 107, ['Ø48.96 COVER GLASS', 'FLUSH, t1.10 (V)'])
    # lower-left callouts
    lead_l(sh, VF.p(*on_arc(222, ACT_R)), 212, ['Ø43.76 ACTIVE AREA', '466×466 px (V)'])
    lead_l(sh, VF.p(*on_arc(270 - 4 * 3.44, 30.0)), 224, ['SPEAKER GRILLE', '9× Ø0.8 ON R30 (E)'])
    # right callouts
    lead_r(sh, VF.p(*on_arc(BTN_A + 3, 30.0)), 156, 104, ['BUTTON 8×2.5, FLUSH', 'HOLD = TALK', 'HW MIC GATE (E)'])
    lob = VF.p(*OUTL[206])
    lead_r(sh, lob, 156, 216, ['LOWER LOBE', 'SUPERELLIPSE', 'n2.6, 30×38 (E)'])
    sh.text(x0 + 30, TY, 'FRONT VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- TOP VIEW ----------
    def pt(x, z):
        return VT.p(x, -z)
    sh.poly([pt(s, z) for s, z in PROF_X], 'o')
    sh.poly([pt(-LIP_OUT, 0), pt(-LIP_OUT, LIP_H), pt(LIP_OUT, LIP_H), pt(LIP_OUT, 0)], 'o', close=False)
    sh.line(*pt(-30, Z_PART), *pt(30, Z_PART), 'o2')
    sh.line(*pt(-30, -RF), *pt(30, -RF), 'o3')
    tpx, tpz = INFO_X['tp']
    sh.line(*pt(-tpx, tpz), *pt(tpx, tpz), 'o3')
    for a in MIC_A:
        x, _ = on_arc(a, 30)
        sh.circle(*pt(x, -5.5), 0.4 * k, 'o2')
    bx0, bx1 = on_arc(a1, 30)[0], on_arc(a0, 30)[0]
    sh.poly([pt(bx0, -4.6), pt(bx1, -4.6), pt(bx1, -6.5), pt(bx0, -6.5)], 'o2')
    P = POCKET
    sh.poly([pt(-P['x'], P['z0']), pt(P['x'], P['z0']), pt(P['x'], P['z1']), pt(-P['x'], P['z1'])], 'h')
    sh.line(*pt(0, 2.5), *pt(0, -21.5), 'c')
    yb_ = pt(0, -T)[1]
    sh.dim_h(pt(-30, -6)[0], pt(-30, -6)[1], pt(30, -6)[0], pt(30, -6)[1], yb_ - 8, '60.0')
    sh.dim_v(pt(-tpx, tpz)[0], pt(-tpx, tpz)[1], pt(-26, 0)[0], pt(-26, 0)[1], pt(-30, 0)[0] - 7, '≈13.9 (E)')
    lead_r(sh, pt(18, dome_z(18, T, RD)), 156, 36, ['BACK DOME R80 (E)'])
    lead_r(sh, pt(P['x'], (P['z0'] + P['z1']) / 2), 156, 46, ['STRAP BAR POCKET', '10×3.5, HIDDEN'])
    lead_r(sh, pt(30, Z_PART), 156, 58, ['PARTING LINE', 'z −7.0 (E)'])
    sh.text(pt(0, 0)[0], yb_ - 13, 'TOP VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- RIGHT SIDE VIEW ----------
    def ps(z, y):
        return VS.p(-z, y)
    sh.poly([ps(z, s) for s, z in PROF_Y], 'o')
    sh.poly([ps(0, -LIP_OUT + 4), ps(LIP_H, -LIP_OUT + 4), ps(LIP_H, LIP_OUT + 4), ps(0, LIP_OUT + 4)], 'o', close=False)
    sh.line(*ps(Z_PART, -34), *ps(Z_PART, 34), 'o2')
    sh.line(*ps(-RF, -34), *ps(-RF, 34), 'o3')
    tpy, tpzy = INFO_Y['tp']
    sh.line(*ps(tpzy, -tpy), *ps(tpzy, tpy), 'o3')
    by0, by1 = on_arc(a0, 30)[1], on_arc(a1, 30)[1]
    sh.poly([ps(-4.6, by0), ps(-4.6, by1), ps(-6.5, by1), ps(-6.5, by0)], 'o')
    _, my = on_arc(MIC_A[0], 30)
    sh.circle(*ps(-5.5, my), 0.4 * k, 'o2')
    sh.poly([ps(P['z0'], P['y0']), ps(P['z0'], P['y1']), ps(P['z1'], P['y1']), ps(P['z1'], P['y0'])], 'h')
    sh.line(*ps(2.5, 0), *ps(-21.5, 0), 'c')
    sh.line(*ps(2.5, 4), *ps(-3, 4), 'c')
    xr = ps(-T, 0)[0]
    sh.dim_v(ps(-6.7, 34)[0], ps(-6.7, 34)[1], ps(-6.7, -34)[0], ps(-6.7, -34)[1], xr + 7, '68.0')
    yy = ps(0, -9)[1]
    sh.line(ps(0, -9)[0], yy, ps(dome_z(9, T, RD), -9)[0], yy, 't')
    sh.arrow(ps(0, -9), ps(-5, -9))
    sh.arrow(ps(dome_z(9, T, RD), -9), ps(-10, -9))
    sh.text((ps(0, 0)[0] + ps(-T, 0)[0]) / 2, yy - 1.0, '19.0', 2.6, 'middle', 'td')
    sh.text((ps(0, 0)[0] + ps(-T, 0)[0]) / 2, yy + 3.2, '@ CL', 2.0, 'middle', 'td')
    ytop = ps(0, 34)[1] - 6
    sh.dim_h(ps(0, 30)[0], ps(0, 30)[1], ps(tpzy, tpy)[0], ps(tpzy, tpy)[1], ytop, '≈12.2 (E)')
    xa = xr + 12
    lead_r(sh, ps(LIP_H, 26), xa, 112, ['LIP 0.4'])
    lead_r(sh, ps(-5.5, by1 - 1), xa, 122, ['BUTTON'])
    lead_r(sh, ps(dome_z(12, T, RD), 12), xa, 150, ['R80 (E)'])
    lead_r(sh, ps(Z_PART, -14), xa, 176, ['PARTING', 'z −7.0'])
    fcx, fcz = INFO_Y['fc']
    t = ps(fcz - RB * math.sin(math.radians(35)), -(fcx + RB * math.cos(math.radians(35))))
    lead_r(sh, t, xa, 222, ['R3 BACK'])
    t = ps(-RF + RF * math.sin(math.radians(45)), -(30 + RF * math.cos(math.radians(45))))
    lead_r(sh, t, xa, 230, ['R4 FRONT'])
    sh.text(ps(-T / 2, 0)[0], TY, 'RIGHT SIDE', 3.2, 'middle', 'tx', weight='bold')

    # ---------- REAR VIEW ----------
    cid = sh.clip(VB.pl(OUTL))
    sh.poly(VB.pl(OUTL), 'o')
    sh.poly(VB.pl(offset_poly(OUTL, 1.9)), 'o3')
    sh.add('<g clip-path="url(#%s)">' % cid)
    for sag in (1, 2, 3, 4, 5):
        r = math.sqrt(RD ** 2 - (RD - sag) ** 2)
        sh.poly(VB.pl(arc_pts(0, 0, r, 0, 360, 90)), 'ph')
    sh.add('</g>')
    sh.poly(VB.pl(arc_pts(0, 0, 12, 0, 360, 72)), 'h')
    for sx in (-1, 1):
        sh.poly(VB.pl([(sx * 14, -11), (sx * 25, -11), (sx * 25, 11), (sx * 14, 11)]), 'h')
    for x, y in PADS:
        px, py = VB.p(x, y)
        sh.circle(px, py, 1.25 * k, 'o')
        sh.circle(px, py, 0.7 * k, 'solid')
    for x, y in SCREWS:
        px, py = VB.p(x, y)
        sh.circle(px, py, 1.5 * k, 'o')
        for ang in (0, 60, 120):
            dx, dy = math.cos(math.radians(ang)) * 1.4, math.sin(math.radians(ang)) * 1.4
            sh.line(px - dx, py - dy, px + dx, py + dy, 'o3')
    r_ = 1.75
    pk = arc_pts(P['x'] - r_, (P['y0'] + P['y1']) / 2, r_, -90, 90, 10) + arc_pts(-P['x'] + r_, (P['y0'] + P['y1']) / 2, r_, 90, 270, 10)
    sh.poly(VB.pl(pk), 'o')
    for yb2 in (P['bar_y'] - 0.8, P['bar_y'] + 0.8):
        sh.line(*VB.p(-P['x'] + 0.3, yb2), *VB.p(P['x'] - 0.3, yb2), 'o2')
    mx, my = VB.p(0, 5.0)
    sh.text(mx, my, 'SOUL', 5.2, 'middle', 'tx', extra='style="fill:none;stroke:%s;stroke-width:0.22" letter-spacing="0.8"' % sh.th['fg'])
    sh.poly(VB.pl([(-8, -30.5), (8, -30.5), (8, -27), (-8, -27)]), 'ph')
    xb0, yb0 = VB.p(0, 0)
    sh.line(xb0, VB.p(0, 37)[1], xb0, VB.p(0, -37)[1], 'c')
    sh.line(VB.p(34, 0)[0], yb0, VB.p(-34, 0)[0], yb0, 'c')
    # lettered tags (key in the notes block)
    XR, XL = VB.p(-34, 0)[0] + 5, VB.p(34, 0)[0] - 5     # right / left of the view on paper
    def tg(feat, at, l):
        tag(sh, VB.p(*feat), *VB.p(*at), l)
    tg((-1.25, -19), (-32, -20), 'a')
    tg((-15 - 1.1, -24 - 1.1), (-30, -29), 'b')
    tg((-P['x'], P['y1']), (-20, 38.5), 'c')
    tg((-8.5, 8.5), (-35, 13), 'd')
    tg((20, 8), (35, 16), 'e')
    tg(on_arc(200, 17.7, 0)[::1] if False else (-16.6, -6.1), (-34, -7), 'f')
    tg((8, -30.5), (24, -34), 'g')
    sh.text(xb0, TY, 'REAR VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- notes + rear key ----------
    nx, ny = 196, 16
    sh.text(nx, ny + 2, 'GENERAL NOTES', 3.0, 'start', 'tx', weight='bold')
    notes = [
        '1. THIRD-ANGLE PROJECTION. mm. A3, SCALE 2:1.',
        '2. DISPLAY 1.75" ROUND AMOLED 466×466 (~270 ppi).',
        '   GLASS Ø48.96×1.10, ACTIVE Ø43.76, MODULE Ø46.0 (V)',
        '3. DISPLAY CL 4.0 ABOVE BODY CL; UPPER OUTLINE',
        '   R30 CONCENTRIC WITH THE DISPLAY.',
        '4. FROSTED TRANSLUCENT PC, RF-TRANSPARENT, 2-PART',
        '   SHELL. WALL 1.5, DOME R80, ROUNDS R4 / R3 (E).',
        '5. GLASS FLUSH; FROSTED LIP 0.4 PROUD (0.3-0.5).',
        '6. INPUTS: TOUCH, 1 FLUSH BUTTON, IMU, BACK TOUCH.',
        '7. CHARGING: POGO PADS ON BACK (MAGNETIC DOCK).',
        '   USB-C ONLY ON DEV UNITS, UNDER THE STRAP BAR.',
        '8. SECTION A-A: SHEET 2 · PARTS LIST: SHEET 3.',
    ]
    for i, n in enumerate(notes):
        sh.text(nx, ny + 7.5 + i * 3.4, n, 2.1, 'start', 'tx')
    sh.text(nx, ny + 7.5 + len(notes) * 3.4 + 1.2, '(V) VERIFIED STEP  (K) SPEC SHEET  (E) ESTIMATE', 2.1, 'start', 'ta')
    kx = 312
    sh.text(kx, ny + 2, 'REAR VIEW KEY', 3.0, 'start', 'tx', weight='bold')
    key = [
        ('a', '2× CHARGE PAD Ø2.5 Au, flush', 'on CL at y −15 / −19 (E)'),
        ('b', '4× M1.6×4 TORX, battery access', '(±18, 22) (±15, −24) (E)'),
        ('c', 'STRAP BAR POCKET 10×3.5', 'Ø1.6 SS bar across (E)'),
        ('d', 'BALLAST / CLIP PLATE Ø24', 'SUS430 magnetic, hidden (E)'),
        ('e', '2× BACK-TOUCH ELECTRODE', 'Cu foil inside shell, hidden'),
        ('f', 'DOME CONTOURS, 1 mm STEPS', 'sphere R80, apex at body CL'),
        ('g', 'REGULATORY MARK ZONE 16×3.5', 'laser mark (E)'),
    ]
    for i, (l, a, b) in enumerate(key):
        yy = ny + 8.5 + i * 7.0
        sh.circle(kx + 2.2, yy - 0.9, 2.0, 'bal')
        sh.text(kx + 2.2, yy, l, 2.4, 'middle', 'tx', weight='bold')
        sh.text(kx + 6, yy - 0.9, a, 2.1, 'start', 'tx')
        sh.text(kx + 6, yy + 2.3, b, 2.0, 'start', 'td')

    # ---------- key data ----------
    kx, ky = 16, 247
    sh.text(kx, ky, 'KEY DATA · PRODUCTION TARGET', 2.8, 'start', 'tx', weight='bold')
    rows = [
        ('ENVELOPE', '68.0 × 60.0 × 19.0 (+0.4 lip) · edge ≈12 · R80 back'),
        ('MASS', 'target 75-90 g · parts-list estimate ≈73 g (E)'),
        ('BATTERY', '1000 mAh LiPo 523450, 5.2×34×50, ~19 g (K)'),
        ('AUDIO / HAPTIC', 'sealed 1813 speaker + LRA Ø10 in the lower lobe (E)'),
        ('RADIO', 'ESP32-S3 Wi-Fi / BLE · antenna keep-out at top edge'),
    ]
    for i, (a, b) in enumerate(rows):
        yy = ky + 6 + i * 7.0
        sh.line(kx, yy + 2.3, kx + 214, yy + 2.3, 'fr1')
        sh.text(kx, yy, a, 2.3, 'start', 'td')
        sh.text(kx + 36, yy, b, 2.5, 'start', 'tx')
    sh.title_block('GENERAL ARRANGEMENT', 'PRODUCTION TARGET · 68 × 60 × 19', '2:1', '1 / 4', 'SOUL-GA-001')
    return sh


# ================================================================ SHEET 2 : SECTION A-A
WALL = 1.5
BAT = dict(s0=-17.0, s1=17.0, z0=-5.9, z1=-11.1)
SPK = dict(s0=-31.8, s1=-18.8, z0=-2.7, z1=-6.7)
LRA = dict(s0=-29.3, s1=-19.3, z0=-7.0, z1=-10.0)


def inner_z(s):
    zc = -T + RD
    return zc - math.sqrt((RD - WALL) ** 2 - s * s)


def sec_geometry():
    """All section-A-A regions (object coords s = y, z) as (cls, pts, fill) tuples."""
    R = []
    # front shell, top end
    top = [(28.58, 0.4), (29.28, 0.4), (29.58, 0.0), (30.0, 0.0)] + arc_pts(30, -4, 4, 90, 0, 14) + \
          [(34, -7), (32.5, -7), (32.5, -4.5)] + arc_pts(30, -4.5, 2.5, 0, 90, 10) + \
          [(27.1, -2.0), (27.1, -1.2), (28.58, -1.2)]
    chin = [(-20.58, 0.0), (-20.58, -1.2), (-19.1, -1.2), (-19.1, -2.0), (-21.0, -2.0), (-21.6, -1.2)] + \
           arc_pts(-30, -3.7, 2.5, 90, 180, 10) + [(-32.5, -7), (-34, -7)] + \
           arc_pts(-30, -4, 4, 180, 90, 14) + [(-21.58, 0.0), (-21.28, 0.4), (-20.58, 0.4)]
    # fix chin inner: the arc starts at (-30,-1.2)
    chin = [(-20.58, 0.0), (-20.58, -1.2), (-19.1, -1.2), (-19.1, -2.0), (-21.0, -2.0), (-21.6, -1.2), (-30, -1.2)] + \
           arc_pts(-30, -3.7, 2.5, 90, 180, 10)[1:] + [(-32.5, -7), (-34, -7)] + \
           arc_pts(-30, -4, 4, 180, 90, 14) + [(-21.58, 0.0), (-21.28, 0.4), (-20.58, 0.4)]
    R.append(('fs', top))
    R.append(('fs', chin))
    # back shell (with locating tongue)
    ob = back_curve(34.0, T, RD, RB)
    ib = back_curve(32.5, T - WALL, RD - WALL, RB - WALL)
    bs = [(34, -7)] + ob + [(-34, -7), (-32.5, -7), (-32.5, -5.6), (-31.8, -5.6), (-31.8, -7.0)]
    bs += list(reversed(ib))[1:-1]
    bs += [(31.8, -7.0), (31.8, -5.6), (32.5, -5.6), (32.5, -7)]
    R.append(('bs', bs))
    # strap-bar boss block (part of back shell) and LRA rib
    blk = [(27.3, -7.4), (32.5, -7.4)] + [(s, inner_z(s)) for s in (32.3, 30.0, 27.3)]
    R.append(('bs', blk))
    rib = [(-28.0, LRA['z1']), (-21.0, LRA['z1'])] + [(s, inner_z(s) + 0.05) for s in (-21.0, -24.5, -28.0)]
    R.append(('bs', rib))
    return R


def draw_section(sh, V, k, detail=False):
    p = V.p
    th = sh.th
    for cls, pts in sec_geometry():
        pat = 'hA' if cls == 'fs' else 'hB'
        sh.poly(V.pl(pts), 'o2', extra='style="fill:url(#%s)"' % pat)
    # strap pocket (cut through the boss) + bar
    P = POCKET
    pk = [(P['y0'], P['z0']), (33.4, P['z0']), (33.4, -16), (P['y0'], -16)]
    sh.poly(V.pl(pk), 'o2', extra='style="fill:%s;stroke:none"' % th['bg'])
    # re-stroke the outer profile + pocket edges
    ob = back_curve(34.0, T, RD, RB)
    cz = [q for q in ob if q[0] > 29.4]
    sh.poly(V.pl([(P['y0'], inner_z(P['y0'])) , (P['y0'], P['z0']), (32.5, P['z0'])]), 'o2', close=False)
    sh.circle(*p(P['bar_y'], P['bar_z']), 0.8 * k, 'o2', extra='style="fill:url(#hS)"')
    # glass
    sh.poly(V.pl([(-20.48, 0), (28.48, 0), (28.48, -1.1), (-20.48, -1.1)]), 'gl')
    # AMOLED + touch
    sh.poly(V.pl([(-19.0, -1.1), (27.0, -1.1), (27.0, -2.6), (-19.0, -2.6)]), 'f2')
    # graphite / foam
    sh.poly(V.pl([(-18.5, -2.6), (26.5, -2.6), (26.5, -3.0), (-18.5, -3.0)]), 'o3', extra='style="fill:url(#hD)"')
    # PCB
    sh.poly(V.pl([(-18.0, -3.0), (26.0, -3.0), (26.0, -3.8), (-18.0, -3.8)]), 'o2', extra='style="fill:url(#hC)"')
    for s0, s1, h in ((-2.0, 14.0, 1.6), (15.5, 19.5, 1.0), (-12.5, -6.5, 1.0), (-16.5, -13.8, 1.3), (6.0 - 30, -14.5 + 0, 0)):
        if h:
            sh.poly(V.pl([(s0, -3.8), (s1, -3.8), (s1, -3.8 - h), (s0, -3.8 - h)]), 'f2')
    # battery
    B = BAT
    sh.poly(V.pl([(B['s0'], B['z0']), (B['s1'], B['z0']), (B['s1'], B['z1']), (B['s0'], B['z1'])]), 'fb')
    sh.line(*p(B['s1'] - 4.0, B['z0']), *p(B['s1'] - 4.0, B['z1']), 'o3')
    for i in range(1, 6):
        zz = B['z0'] + (B['z1'] - B['z0']) * i / 6
        sh.line(*p(B['s0'] + 0.6, zz), *p(B['s1'] - 4.6, zz), 'o3', extra='stroke-opacity="0.35"')
    # foam between battery and ballast
    sh.poly(V.pl([(-13.0, -11.1), (13.0, -11.1), (13.0, -12.2), (-13.0, -12.2)]), 'o3', extra='style="fill:url(#hD)"')
    # ballast plate formed to the dome
    bal = [(-12.0, -12.2), (12.0, -12.2)] + [(s, inner_z(s)) for s in [12 - i for i in range(0, 25)]]
    sh.poly(V.pl(bal), 'o2', extra='style="fill:url(#hS)"')
    # charge pads
    for sc in (-15.0, -19.0):
        pts = [(sc - 1.25, inner_z(sc - 1.25) + 0.35), (sc + 1.25, inner_z(sc + 1.25) + 0.35),
               (sc + 1.25, dome_z(sc + 1.25, T, RD)), (sc - 1.25, dome_z(sc - 1.25, T, RD))]
        sh.poly(V.pl(pts), 'o2', extra='style="fill:%s;fill-opacity:0.55"' % th['acc'])
    # speaker (sealed 1813) + gasket
    S = SPK
    sh.poly(V.pl([(S['s0'], S['z0']), (S['s1'], S['z0']), (S['s1'], S['z1']), (S['s0'], S['z1'])]), 'f2')
    sm = (S['s0'] + S['s1']) / 2
    sh.poly(V.pl([(S['s0'] + 1.5, S['z0'] - 0.3), (sm - 2.0, S['z0'] - 1.8), (sm + 2.0, S['z0'] - 1.8), (S['s1'] - 1.5, S['z0'] - 0.3)]), 'o3', close=False)
    sh.poly(V.pl([(sm - 2.2, S['z0'] - 2.0), (sm + 2.2, S['z0'] - 2.0), (sm + 2.2, S['z1'] + 0.4), (sm - 2.2, S['z1'] + 0.4)]), 'o3')
    for g0, g1 in ((-31.8, -30.6), (-22.0, -20.8)):
        sh.poly(V.pl([(g0, -1.2), (g1, -1.2), (g1, -2.7), (g0, -2.7)]), 'o3', extra='style="fill:url(#hD)"')
    # grille hole (through the chin skin at CL)
    sh.poly(V.pl([(-26.4, 0.05), (-25.6, 0.05), (-25.6, -1.25), (-26.4, -1.25)]), 'o3', extra='style="fill:%s"' % th['bg'])
    # LRA
    L = LRA
    sh.poly(V.pl([(L['s0'], L['z0']), (L['s1'], L['z0']), (L['s1'], L['z1']), (L['s0'], L['z1'])]), 'f2')
    lm = (L['s0'] + L['s1']) / 2
    sh.poly(V.pl([(lm - 3.5, L['z0'] - 0.8), (lm + 3.5, L['z0'] - 0.8), (lm + 3.5, L['z1'] + 0.8), (lm - 3.5, L['z1'] + 0.8)]), 'o3')
    # outer silhouette on top
    sh.poly(V.pl(PROF_Y), 'o')
    sh.poly(V.pl([(-25.38 + 4, 0), (-25.38 + 4, 0.4), (25.38 + 4, 0.4), (25.38 + 4, 0)]), 'o', close=False)


def sheet_section(theme):
    sh = Sheet(theme)
    sh.frame()
    k = 4.0
    V = View(160, 46, k)
    p = V.p
    draw_section(sh, V, k)
    # centre lines
    sh.line(*p(0, 3.0), *p(0, -21.5), 'c')
    sh.line(*p(4, 3.0), *p(4, -4.0), 'c')
    sh.text(p(0, 0)[0] - 1, p(0, -21.5)[1] + 0.6, 'BODY CL', 1.9, 'end', 'td')
    sh.line(*p(4, -17.0), *p(4, -21.5), 'c')
    sh.text(p(4, 0)[0] + 1, p(0, -21.5)[1] + 0.6, 'DISPLAY CL', 1.9, 'start', 'td')
    # detail B marker
    bc = p(30.6, -3.6)
    sh.circle(bc[0], bc[1], 5.4 * k, 'ph')
    sh.text(bc[0] + 5.4 * k * 0.72 + 1.5, bc[1] - 5.4 * k * 0.72 - 1, 'B', 4.2, 'start', 'tx', weight='bold')
    # dims
    yb = p(0, -T)[1]
    sh.dim_h(*p(-34, -6.5), *p(34, -6.5), yb + 15, '68.0')
    sh.dim_v(*p(-30, 0), *p(0, -T), p(-34, 0)[0] - 6, '19.0 @ CL')
    tpy, tpzy = INFO_Y['tp']
    sh.dim_v(*p(30, 0), *p(tpy, tpzy), p(34, 0)[0] + 7, '≈12.2 (E)')
    sh.dim_h(*p(-20.48, 0.4), *p(28.48, 0.4), p(0, 0.4)[1] - 8, 'Ø48.96 GLASS (V)')
    sh.dim_h(*p(0, 3), *p(4, 3), p(0, 0.4)[1] - 16, '4.0', gap=0.0)
    sh.dim_h(*p(SPK['s0'], SPK['z1']), *p(SPK['s1'], SPK['z1']), yb + 5.5, '13.0 SPK', gap=13)
    sh.dim_h(*p(BAT['s0'], BAT['z1']), *p(BAT['s1'], BAT['z1']), yb + 5.5, '34.0 CELL', gap=5)
    # balloons
    def bl(n, feat, at):
        sh.balloon(*at, n, tip=p(*feat))
    top = 24.0
    bot = yb + 25
    bl(1, (-27.5, -0.6), (40, top))
    bl(2, (-12, -0.55), (100, top))
    bl(3, (-6, -1.85), (116, top))
    bl(10, (-8, -2.8), (132, top))
    bl(4, (8, -3.4), (206, top))
    bl(1, (32.8, -5.5), (292, top))
    bl(7, (-27, -4.5), (22, bot))
    bl(8, (-26, -8.1), (38, bot))
    bl(14, (-4, -18.3), (70, bot))
    bl(13, (-15, -16.6), (100, bot))
    bl(9, (-10, -8.5), (130, bot))
    bl(11, (0, -14.5), (160, bot))
    bl(10, (8, -11.6), (190, bot))
    bl(14, (30.0, -9.2), (p(34, 0)[0] + 4, yb - 8))
    bl(16, (31.2, -10.3), (p(34, 0)[0] + 4, yb + 4))
    sh.text(p(0, 0)[0], 12.0 + 3.6, 'SECTION A-A  ·  SCALE 4:1  ·  (ROTATED 90°: FRONT UP, TOP OF DEVICE RIGHT)', 3.0, 'middle', 'tx', weight='bold')

    # ---------- detail B (8:1) ----------
    kd = 8.0
    cx, cy, rr = 360.0, 64.0, 42.0
    VD = View(cx - 30.6 * kd, cy - 3.6 * kd, kd)
    cid = sh.clip(arc_pts(cx, cy, rr, 0, 360, 90))
    sh.add('<g clip-path="url(#%s)">' % cid)
    sh.circle(cx, cy, rr, 'bgf')
    draw_section(sh, VD, kd, detail=True)
    sh.add('</g>')
    sh.circle(cx, cy, rr, 'o2')
    q = VD.p
    sh.dim_h(*q(32.5, -6.2), *q(34, -6.2), q(0, -6.2)[1], '1.5', size=2.3, arrows_out=True, gap=0)
    sh.leader(q(29.0, 0.4), (cx - 34, cy - 36), '', lines=['LIP 0.4 PROUD', '0.7 WIDE, FROSTED'], size=2.0, side=-1)
    sh.leader(q(27.8, -1.6), (cx - 36, cy + 26), '', lines=['LEDGE 1.48×0.8', 'PSA 0.1 (E)'], size=2.0, side=-1)
    sh.leader(q(27.4, -0.55), (cx - 36, cy - 12), '', lines=['GLASS t1.10 (V)'], size=2.0, side=-1)
    sh.leader(q(31.5, -1.0), (cx + 22, cy - 38), '', lines=['FRAME 2.0'], size=2.0)
    sh.leader(q(33.2, -2.0), (cx + 30, cy - 26), '', lines=['R4 / R2.5'], size=2.0, side=-1)
    sh.text(cx, cy + rr + 6, 'DETAIL B  ·  8:1', 3.0, 'middle', 'tx', weight='bold')

    # ---------- callout table ----------
    tx0, ty0 = 14, 165
    cols = [0, 9, 92, 152, 170, 214]
    sh.text(tx0, ty0 - 3, 'STACK-UP AT A-A  (z = 0 AT COVER-GLASS FRONT, − = TOWARD BACK)', 2.7, 'start', 'tx', weight='bold')
    hdr = ['#', 'ELEMENT', 'z FROM → TO', 't', 'NOTE']
    rows = [
        ('1', 'Front shell: frame / chin skin / wall', '+0.40 → −7.00', '2.0/1.2/1.5', 'frosted PC (E)'),
        ('2', 'Cover glass Ø48.96', '0.00 → −1.10', '1.10', '(V) STEP'),
        ('3', 'AMOLED panel + touch + OCA Ø46', '−1.10 → −2.60', '1.50', '(E)'),
        ('10', 'Graphite / foam sheet', '−2.60 → −3.00', '0.40', 'heat spread (E)'),
        ('4', 'Main PCB, FR4 0.8', '−3.00 → −3.80', '0.80', '(E)'),
        ('4', 'Components / shield can', '−3.80 → −5.40', '1.60', 'ESP32-S3 (E)'),
        ('–', 'Clearance (swell / FPC)', '−5.40 → −5.90', '0.50', '(E)'),
        ('9', 'Battery 523450 1000 mAh', '−5.90 → −11.10', '5.20', '(K)'),
        ('10', 'Compression foam, no glue', '−11.10 → −12.20', '1.10', 'EU 2023/1542'),
        ('11', 'Ballast/clip plate, formed', '−12.20 → −17.50', '≤5.3', 'SUS430 (E)'),
        ('14', 'Back shell wall, dome R80', '−17.50 → −19.00', '1.50', '(E)'),
        ('7', 'Speaker 1813 sealed (lower lobe)', '−2.70 → −6.70', '4.00', 'fires via chin'),
        ('8', 'LRA Ø10 Z-axis (lower lobe)', '−7.00 → −10.00', '3.00', 'on back rib'),
        ('13', 'Charge pads (2), Au', '−15.6 → −17.6', '2.0', 'y −15/−19'),
        ('16', 'Strap bar Ø1.6 SS in pocket', 'z −10.3', '–', 'y +31.2 (E)'),
    ]
    rh = 5.6
    for j, h in enumerate(hdr):
        sh.text(tx0 + cols[j] + 1, ty0 + 4.2, h, 2.1, 'start', 'td')
    sh.rect(tx0, ty0, cols[-1], rh * (len(rows) + 1), 'fr2t')
    sh.line(tx0, ty0 + rh, tx0 + cols[-1], ty0 + rh, 'fr2t')
    for c in cols[1:-1]:
        sh.line(tx0 + c, ty0, tx0 + c, ty0 + rh * (len(rows) + 1), 'fr1')
    for i, r in enumerate(rows):
        yy = ty0 + rh * (i + 1)
        if i:
            sh.line(tx0, yy, tx0 + cols[-1], yy, 'fr1')
        for j, v in enumerate(r):
            sh.text(tx0 + cols[j] + 1, yy + 4.2, v, 2.2 if j != 1 else 2.2, 'start', 'ta' if (j == 4 and '(V)' in v) else 'tx')
    sh.text(tx0, ty0 + rh * (len(rows) + 1) + 4.5, 'Total @ CL: 19.0 = glass..shell 17.5 + wall 1.5. Walls: side 1.5, back 1.5, chin skin 1.2, frame 2.0; locating tongue 0.7\u00d71.4 (E).', 2.1, 'start', 'td')

    # ---------- key plan 1:1 ----------
    VK = View(268, 180, 0.85)
    sh.poly(VK.pl(OUTL), 'o2')
    sh.poly(VK.pl(arc_pts(0, 4, G_R, 0, 360, 90)), 'o3')
    sh.poly(VK.pl([(-25, -17), (25, -17), (25, 17), (-25, 17)]), 'h')
    sh.poly(VK.pl([(-9, SPK['s0']), (9, SPK['s0']), (9, SPK['s1']), (-9, SPK['s1'])]), 'h')
    x0 = VK.p(0, 0)[0]
    sh.line(x0, VK.p(0, 38)[1], x0, VK.p(0, -38)[1], 'cut')
    sh.section_arrow(x0, VK.p(0, 38)[1], 'A', (-1, 0), size=3.2)
    sh.section_arrow(x0, VK.p(0, -38)[1], 'A', (-1, 0), size=3.2)
    sh.text(x0, VK.p(0, -38)[1] + 7, 'KEY PLAN (FRONT)', 2.4, 'middle', 'tx', weight='bold')
    sh.text(x0, VK.p(0, -38)[1] + 10.5, 'hidden: cell, speaker', 2.0, 'middle', 'td')

    # ---------- stack-up ruler ----------
    zx, ztop, zs = 318, 136, 4.9
    layers = [
        (0.4, 0.0, 'lip', 'o3'), (0.0, -1.1, 'glass', 'gl'), (-1.1, -2.6, 'AMOLED', 'f2'), (-2.6, -3.0, 'graphite', 'o3'),
        (-3.0, -3.8, 'PCB', 'o3'), (-3.8, -5.4, 'parts', 'f2'), (-5.4, -5.9, 'gap', 'o3'), (-5.9, -11.1, 'cell', 'fb'),
        (-11.1, -12.2, 'foam', 'o3'), (-12.2, -17.5, 'ballast', 'f2'), (-17.5, -19.0, 'wall', 'f2')]
    def zy(z):
        return ztop + (0.4 - z) * zs
    sh.text(zx + 8, ztop - 5, 'STACK @ CL', 2.6, 'middle', 'tx', weight='bold')
    n = len(layers)
    for i, (z0, z1, name, cls) in enumerate(layers):
        sh.rect(zx, zy(z0), 16, zy(z1) - zy(z0), cls)
        ly = ztop + 2 + i * (zy(-19.0) - ztop - 4) / (n - 1)
        my = (zy(z0) + zy(z1)) / 2
        sh.poly([(zx + 16, my), (zx + 22, my), (zx + 26, ly), (zx + 28, ly)], 't', close=False)
        sh.text(zx + 29, ly + 0.8, '%-8s %6.2f' % (name, z1), 2.2, 'start', 'tx')
    sh.text(zx + 8, zy(-19.0) + 4.5, 'z in mm', 2.0, 'middle', 'td')

    sh.title_block('SECTION A-A · STACK-UP', 'PRODUCTION TARGET · walls & layers', '4:1', '2 / 4', 'SOUL-GA-002')
    return sh


# ================================================================ SHEET 3 : EXPLODED + BOM
def hull(points):
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in points))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


class Axo:
    def __init__(self, ox, oy, k, A=-50.0, B=20.0):
        self.ox, self.oy, self.k = ox, oy, k
        self.ca, self.sa = math.cos(math.radians(A)), math.sin(math.radians(A))
        self.cb, self.sb = math.cos(math.radians(B)), math.sin(math.radians(B))

    def t(self, x, y, z):
        x1 = x * self.ca + z * self.sa
        z1 = -x * self.sa + z * self.ca
        y2 = y * self.cb - z1 * self.sb
        d = y * self.sb + z1 * self.cb
        return (self.ox + x1 * self.k, self.oy - y2 * self.k), d

    def p(self, x, y, z):
        return self.t(x, y, z)[0]


def sheet_exploded(theme):
    sh = Sheet(theme)
    sh.frame()
    AX = Axo(100, 146, 1.33)
    items = []   # (depth, draw-fn)

    def prism(outl, z0, z1, dz, face_extra=None, cls='ob', face_cls='o', off=(0, 0)):
        ox_, oy_ = off
        P0 = [AX.p(x + ox_, y + oy_, z0 + dz) for x, y in outl]
        P1 = [AX.p(x + ox_, y + oy_, z1 + dz) for x, y in outl]
        cx = sum(x for x, _ in outl) / len(outl) + ox_
        cy = sum(y for _, y in outl) / len(outl) + oy_
        depth = AX.t(cx, cy, (z0 + z1) / 2 + dz)[1]

        def draw():
            sh.poly(hull(P0 + P1), cls)
            sh.poly(P1, face_cls)
            if face_extra:
                face_extra()
        items.append((depth, draw))

    def circ(r, cx=0.0, cy=0.0, n=72):
        return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

    def rrect(w, h, r, cx=0.0, cy=0.0):
        pts = []
        for (qx, qy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
            pts += arc_pts(cx + qx, cy + qy, r, a0, a0 + 90, 6)
        return pts

    def face_poly(pts2, z, cls='o2'):
        sh.poly([AX.p(x, y, z) for x, y in pts2], cls)

    anchors = {}
    D = dict(glass=58, amoled=44, fshell=22, pcb=0, spk=-12, lra=-22, batt=-36, foam=-49, ball=-59, pads=-70, bshell=-88, screws=-110)

    # 2 cover glass
    def gl_extra():
        face_poly(circ(ACT_R, 0, 4), 0 + D['glass'], 'ph')
        for sx in (-1, 1):
            e = rrect(7.4, 12.5, 3.7, sx * 7.2, 5.5)
            face_poly(e, D['glass'], 'o3')
    prism(circ(G_R, 0, 4), -G_T, 0, D['glass'], gl_extra, cls='gl', face_cls='o')
    anchors[2] = AX.p(-G_R * 0.7, 4 + G_R * 0.7, D['glass'])
    # 3 AMOLED module + FPC tail
    prism(circ(MOD_R, 0, 4), -2.6, -1.1, D['amoled'], lambda: face_poly(circ(ACT_R, 0, 4), -1.1 + D['amoled'], 'o3'), cls='f2')
    prism(rrect(12, 9, 0.5, 0, -22.5), -2.8, -2.6, D['amoled'], cls='f2', face_cls='o2')
    anchors[3] = AX.p(-MOD_R * 0.7, 4 + MOD_R * 0.7, -1.1 + D['amoled'])

    # 1 front shell
    def fs_extra():
        z = 0.4 + D['fshell']
        face_poly(circ(LIP_OUT, 0, 4, 120), z, 'o')
        face_poly(circ(LIP_IN, 0, 4, 120), z, 'o2')
        face_poly(circ(23.2, 0, 4, 120), -1.2 + D['fshell'], 'o3')
        face_poly(offset_poly(OUTL, RF), z, 'o3')
        for i in range(-4, 5):
            cx, cy = on_arc(270 + i * 3.44, 30.0)
            face_poly(circ(0.45, cx, cy, 10), z, 'o3')
    prism(OUTL, -7.0, 0.4, D['fshell'], fs_extra, cls='ob')
    anchors[1] = AX.p(*OUTL[40], 0 + D['fshell'])

    # 4 PCB + 5 mics + 6 button
    pcb = [q for q in circ(22.0, 0, 4, 90) if q[1] > -17.5]
    pcb = pcb + [(-math.sqrt(22 ** 2 - 21.5 ** 2), -17.5), (math.sqrt(22 ** 2 - 21.5 ** 2), -17.5)]
    pcb = hull(pcb)

    def pcb_extra():
        z = -3.0 + D['pcb']
        face_poly(rrect(8, 3, 0.4, 0, -12), z, 'o3')      # display FPC connector
        face_poly(rrect(5, 5, 0.3, -12, 10), z, 'o3')     # ALS / misc
        face_poly(rrect(10, 4, 0.3, 0, 20), z, 'ph')      # antenna keep-out
    prism(pcb, -3.8, -3.0, D['pcb'], pcb_extra, cls='ob')
    prism(rrect(16, 14, 0.6, 2, 3), -5.4, -3.8, D['pcb'], cls='ob', face_cls='o2')
    anchors[4] = AX.p(-15, 18, -3.0 + D['pcb'])
    for a in MIC_A:
        mx, my = on_arc(a, 26.0)
        prism(rrect(3.5, 2.6, 0.3, mx, my), -3.0, -2.0, D['pcb'], cls='o2b', face_cls='o2')
    anchors[5] = AX.p(*on_arc(MIC_A[1], 26.0), -2.0 + D['pcb'])
    bx, by = on_arc(BTN_A, 27.2)
    prism(rrect(3.0, 6.0, 0.5, bx, by), -7.0, -4.2, D['pcb'], cls='o2b', face_cls='o2')
    anchors[6] = AX.p(bx, by + 3, -4.2 + D['pcb'])

    # 7 speaker, 8 LRA
    S = SPK
    prism(rrect(18, 13, 1.5, 0, (S['s0'] + S['s1']) / 2), S['z1'], S['z0'], D['spk'],
          lambda: face_poly(rrect(12, 8, 3.5, 0, (S['s0'] + S['s1']) / 2), S['z0'] + D['spk'], 'o3'), cls='ob')
    anchors[7] = AX.p(-9, (S['s0'] + S['s1']) / 2, S['z0'] + D['spk'])
    L = LRA
    prism(circ(5.0, 0, (L['s0'] + L['s1']) / 2, 40), L['z1'], L['z0'], D['lra'],
          lambda: face_poly(circ(2.0, 0, (L['s0'] + L['s1']) / 2, 20), L['z0'] + D['lra'], 'o3'), cls='ob')
    anchors[8] = AX.p(-5, (L['s0'] + L['s1']) / 2, L['z0'] + D['lra'])

    # 9 battery
    B = BAT

    def bat_extra():
        z = B['z0'] + D['batt']
        face_poly([(-21.0, -17), (-21.0, 17)], z, 'o3')
        c = AX.p(0, 0, z)
        sh.text(c[0], c[1] + 1, '523450  1000 mAh', 2.2, 'middle', 'tx', extra='transform="rotate(0)"')
    prism(rrect(50, 34, 1.0), B['z1'], B['z0'], D['batt'], bat_extra, cls='ob')
    anchors[9] = AX.p(-25, 10, B['z0'] + D['batt'])
    # 10 foam
    prism(rrect(26, 26, 2.0), -12.2, -11.1, D['foam'], cls='ob', face_cls='o2',
          face_extra=lambda: [face_poly([(-13 + i * 3.25, -13), (-13 + i * 3.25 + 1.5, 13)], -11.1 + D['foam'], 'o3') for i in range(8)])
    anchors[10] = AX.p(-13, 8, -11.1 + D['foam'])
    # 11 ballast
    prism(circ(12.0), -16.5, -12.2, D['ball'], cls='ob', face_extra=lambda: face_poly(circ(1.2), -12.2 + D['ball'], 'o3'))
    anchors[11] = AX.p(-12 * 0.7, 12 * 0.7, -12.2 + D['ball'])
    # 12 electrodes, 13 pads
    for sx in (-1, 1):
        prism(rrect(11, 22, 1.5, sx * 19.5, 0), -15.0, -14.8, D['pads'], cls='o2b', face_cls='o2')
    anchors[12] = AX.p(-19.5, 11, -14.8 + D['pads'])
    for x, y in PADS:
        prism(circ(1.25, x, y, 20), -17.6, -15.6, D['pads'], cls='ob', face_cls='o2')
    prism(rrect(3, 16, 0.5, 0, -9), -15.6, -15.5, D['pads'], cls='o2b', face_cls='o3')
    anchors[13] = AX.p(1.3, -19, -15.6 + D['pads'])

    # 14 back shell (dome) -- rim faces the viewer
    def bs_pts():
        pts = []
        for zz, sc in ((-7.0, 1.0), (-11.0, 0.93), (-14.0, 0.8), (-16.5, 0.6), (-18.3, 0.35), (-19.0, 0.05)):
            pts += [(x * sc, y * sc, zz) for x, y in OUTL[::6]]
        return pts

    def bshell():
        dz = D['bshell']
        P = [AX.p(x, y, z + dz) for x, y, z in bs_pts()]
        sh.poly(hull(P), 'ob')
        sh.poly([AX.p(x, y, -7.0 + dz) for x, y in OUTL], 'o')
        inner = offset_poly(OUTL, 1.5)
        sh.poly([AX.p(x, y, -7.0 + dz) for x, y in inner], 'o2')
        sh.poly([AX.p(x * 0.62, y * 0.62, -16.8 + dz) for x, y in OUTL], 'ph')
        for x, y in SCREWS:
            sh.poly([AX.p(x + u, y + v, -7.0 + dz) for u, v in circ(1.6, 0, 0, 20)], 'o2')
            sh.poly([AX.p(x + u, y + v, -7.0 + dz) for u, v in circ(0.7, 0, 0, 14)], 'o3')
        Pk = POCKET
        sh.poly([AX.p(x, y, -8.0 + dz) for x, y in rrect(10, 3.5, 1.7, 0, 31.2)], 'o2')
    items.append((AX.t(0, 0, -12 + D['bshell'])[1], bshell))
    anchors[14] = AX.p(*OUTL[150], -7.0 + D['bshell'])
    # 15 screws (behind the back shell)
    for x, y in SCREWS:
        def scr(x=x, y=y):
            dz = D['screws']
            prism_pts = []
        prism(circ(1.5, x, y, 16), -21.0, -20.0, D['screws'], cls='ob', face_cls='o2')
        prism(circ(0.8, x, y, 12), -20.0, -16.0, D['screws'], cls='ob', face_cls='o3')
    anchors[15] = AX.p(-15, -24, -20.0 + D['screws'])
    # 16 strap bar (exploded upwards) + 17 strap loop
    BY = 42.0
    prism(rrect(12, 1.6, 0.8, 0, BY), -11.1, -9.5, D['bshell'], cls='ob', face_cls='o2')
    anchors[16] = AX.p(-6, BY + 0.8, -9.5 + D['bshell'])

    def strap():
        dz = D['bshell'] - 10.3
        for w in (4.0, 5.0):
            loop = arc_pts(0, BY + 22, w, 0, 180, 14) + [(-w, BY + 0.8)] + [(w, BY + 0.8)]
            sh.poly([AX.p(x, y, dz) for x, y in loop], 'o2', close=False)
            sh.line(*AX.p(w, BY + 0.8, dz), *AX.p(w, BY + 22, dz), 'o2')
        sh.line(*AX.p(-5, BY + 12, dz), *AX.p(5, BY + 12, dz), 'o3')
    items.append((AX.t(0, BY + 10, D['bshell'] - 10)[1] + 5, strap))
    anchors[17] = AX.p(-5, BY + 16, D['bshell'] - 10.3)

    # explosion axis (centre line through all parts)
    a_ = AX.p(0, 4, D['glass'] + 12)
    b_ = AX.p(0, 4, D['screws'] - 26)
    sh.line(a_[0], a_[1], b_[0], b_[1], 'c')
    for d, fn in sorted(items, key=lambda q: q[0]):
        fn()

    # balloons
    off = {
        2: (-10, -40), 3: (4, -46), 1: (-14, 40), 4: (0, -40), 5: (-10, -30), 6: (14, -34),
        7: (-6, 34), 8: (6, 36), 9: (-4, -34), 10: (0, -40), 11: (6, -44), 12: (-8, -58),
        13: (-22, 36), 14: (30, 24), 15: (20, 20), 16: (22, 8), 17: (-18, -6),
    }
    for n, (dx, dy) in off.items():
        ax, ay = anchors[n]
        sh.balloon(ax + dx, ay + dy, n, tip=anchors[n])
    sh.text(22, 18.5, 'EXPLODED AXONOMETRIC  ·  NTS  ·  ASSEMBLY ORDER FRONT → BACK', 3.0, 'start', 'tx', weight='bold')
    steps = [
        'ASSEMBLY SEQUENCE (E)',
        '1  Bond glass + AMOLED module (2, 3) into front shell (1) on the PSA ledge; seat mics (5), button (6).',
        '2  Fit main PCB (4) on front-shell ribs, connect display FPC; graphite sheet (10) between.',
        '3  Sealed speaker (7) into the lower lobe on its gasket; LRA (8) on the back-shell rib.',
        '4  Cell (9) on compression foam (10), plug to PCB - no adhesive, replaceable (EU 2023/1542).',
        '5  Back shell (14) pre-assembled with ballast (11), electrodes (12), charge pads + flex (13).',
        '6  Close with 4\u00d7 M1.6 Torx T5 (15); fit strap bar (16) and strap (17).',
    ]
    for i, t_ in enumerate(steps):
        sh.text(22, 226 + i * 4.6, t_, 2.5 if i == 0 else 2.2, 'start', 'tx' if i == 0 else 'td', weight='bold' if i == 0 else None)

    # ---------- BOM table ----------
    bom = [
        ('1', 'Front shell + frosted lip', '1', 'PC translucent, frosted, 2-shot lip', 'E', '9.0'),
        ('2', 'Cover glass Ø48.96 × 1.10', '1', 'strengthened glass, AR/AF', 'V', '5.2'),
        ('3', 'AMOLED 1.75" 466² + touch', '1', 'CO5300 + CST9217, Ø46.0', 'V', '3.5'),
        ('4', 'Main PCB assembly', '1', 'ESP32-S3 16/8 MB, AXP2101, ES8311', 'K', '5.0'),
        ('', '', '', 'ES7210, QMI8658, PCF85063, DRV2605L', '', ''),
        ('5', 'MEMS microphone', '2', 'top-port + gasket, AEC pair', 'E', '0.1'),
        ('6', 'Push button + flush cap', '1', 'side tact switch, PC cap', 'E', '0.3'),
        ('7', 'Speaker 1813, sealed box', '1', '8 Ω ~0.7-1 W + acoustic mesh', 'E', '2.0'),
        ('8', 'LRA Ø10 Z-axis', '1', 'LRA, driven by DRV2605L', 'E', '1.5'),
        ('9', 'Battery LiPo 523450', '1', '1000 mAh 3.7 V + PCM, 5.2×34×50', 'K', '19.0'),
        ('10', 'Foam, graphite, gaskets', 'set', 'PORON / EVA, graphite 0.1', 'E', '0.8'),
        ('11', 'Ballast / clip plate Ø24', '1', 'SUS430 (magnetic), formed R78.5', 'E', '17.0'),
        ('12', 'Back-touch electrode', '2', 'Cu foil / FPC, to ESP32 touch', 'E', '0.3'),
        ('13', 'Charge pad Ø2.5 + flex', '2', 'brass, Au plated, dock pogo target', 'E', '0.4'),
        ('14', 'Back shell, dome R80', '1', 'PC frosted | ZrO₂ (premium)', 'E', '8.0'),
        ('15', 'Screw M1.6 × 4 Torx T5', '4', 'A2 stainless, into brass inserts', 'E', '0.2'),
        ('16', 'Strap bar Ø1.6 × 10', '1', 'SUS316 pin in hidden pocket', 'E', '0.3'),
        ('17', 'Wrist strap / lanyard', '1', 'woven nylon, lark’s-head loop', 'E', '(4.0)'),
    ]
    tx0, ty0 = 256, 16
    cols = [0, 8, 55, 63, 133, 140, 154]
    sh.text(tx0, ty0 + 2.5, 'PARTS LIST', 3.0, 'start', 'tx', weight='bold')
    ty = ty0 + 6
    rh = 7.4
    hdr = ['#', 'PART', 'QTY', 'MATERIAL / SPEC', 'S', 'g']
    sh.rect(tx0, ty, cols[-1], rh * (len(bom) + 1) + 7, 'fr2t')
    for j, h in enumerate(hdr):
        sh.text(tx0 + cols[j] + 1, ty + 4.8, h, 2.1, 'start', 'td')
    sh.line(tx0, ty + rh, tx0 + cols[-1], ty + rh, 'fr2t')
    for c in cols[1:-1]:
        sh.line(tx0 + c, ty, tx0 + c, ty + rh * (len(bom) + 1) + 7, 'fr1')
    for i, r in enumerate(bom):
        yy = ty + rh * (i + 1)
        if r[0]:
            sh.line(tx0, yy, tx0 + cols[-1], yy, 'fr1')
        for j, v in enumerate(r):
            if not v:
                continue
            anchor = 'end' if j == 5 else 'start'
            x = tx0 + cols[j] + 1 if j != 5 else tx0 + cols[-1] - 0.8
            cls = 'ta' if (j == 4 and v == 'V') else 'tx'
            sh.text(x, yy + 4.8, v, 2.05 if j in (1, 3) else 2.2, anchor, cls)
    yy = ty + rh * (len(bom) + 1)
    sh.line(tx0, yy, tx0 + cols[-1], yy, 'fr2t')
    sh.text(tx0 + 9, yy + 4.8, 'DEVICE MASS (1-16), est.', 2.2, 'start', 'tx', weight='bold')
    sh.text(tx0 + cols[-1] - 0.8, yy + 4.8, '≈73', 2.3, 'end', 'tx', weight='bold')
    sh.text(tx0, yy + 11, 'S = source: V verified (STEP) · K spec sheet · E estimate', 2.0, 'start', 'td')
    sh.text(tx0, yy + 14.5, 'Target 75-90 g; ZrO₂ back → ≈100-110 g. Weigh proto.', 2.0, 'start', 'td')
    sh.title_block('EXPLODED VIEW · PARTS LIST', 'PRODUCTION TARGET · 17 items', 'NTS', '3 / 4', 'SOUL-GA-003')
    return sh


# ================================================================ SHEET 4 : PROTOTYPE ON WAVESHARE 1.75
PP = dict(a=32.0, R=32.0, cy=4.0, b=40.0, n=2.6)      # 64 x 72
PT, PZF, PRD, PRF, PRB = 24.0, 1.0, 250.0, 5.0, 8.0     # thickness, front skin, back R, rounds
P_PART = -12.0
P_OUTL = outline(**PP)
P_PROF_Y, P_INFO_Y = profile(36.0, PT, PRD, PRF, PRB, zf=PZF)
P_PROF_X, P_INFO_X = profile(32.0, PT, PRD, PRF, PRB, zf=PZF)
# board data rotated 180 deg into the model frame (display centre at (0, 4)); (V) from STEP
def rot(x, y):
    return (-x, -y + 4.0)
P_SO = [rot(14.70, 13.75), rot(14.70, -13.75), rot(-20.50, 0.0)]
P_PWR = (rot(-11.31, 17.20), 123.3 + 180)
P_BOOT = (rot(11.31, 17.10), 56.5 + 180)
P_MICS = [(rot(-10.96, -17.54), 238.0 - 180), (rot(11.74, -17.35), 304.1 - 180)]
P_USB_Y = 4.0 + 23.80
P_HDR = dict(x0=-20.0, x1=-17.4, y0=-6.0, y1=14.0)          # 8-pin header at the board edge (extent E)
P_BAT = dict(x0=-25, x1=25, y0=-13, y1=21, z0=-13.0, z1=-18.2)
P_SPK = dict(x0=-15, x1=15, y0=-34, y1=-14, z0=-9.1, z1=-14.6)
P_LRA = dict(c=(-12.0, -26.0), r=5.0, z0=-2.0, z1=-5.0)
P_BOSS = [(-23.8, 17.75), (23.8, 17.75), (-22.0, -20.0), (22.0, -20.0)]


def ray_exit(o, a, outl_hw):
    dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
    t = 0.0
    while t < 60:
        x, y = o[0] + dx * t, o[1] + dy * t
        if abs(x) > outl_hw(y):
            return (x, y)
        t += 0.1
    return (x, y)


def sheet_proto(theme):
    sh = Sheet(theme)
    sh.frame()
    k = 2.0
    VF = View(98, 160, k)
    VT = View(98, 76, k)
    VS = View(204, 160, k)
    hw = lambda y: half_width(y, **PP)
    TY = 238.5

    # ---------- FRONT ----------
    sh.poly(VF.pl(P_OUTL), 'o')
    sh.poly(VF.pl(offset_poly(P_OUTL, PRF)), 'o3')
    r_ap = G_R - 0.8
    sh.poly(VF.pl(arc_pts(0, 4, r_ap, 0, 360, 120)), 'o')                 # aperture (lip 0.8 over glass)
    sh.poly(VF.pl(arc_pts(0, 4, G_R, 0, 360, 120)), 'h')                  # glass edge (hidden)
    sh.poly(VF.pl(arc_pts(0, 4, ACT_R, 0, 360, 120)), 'ph')
    sh.poly(VF.pl(arc_pts(0, 4, MOD_R, 0, 360, 120)), 'h')
    eyes(sh, VF, 0, 5.5)
    # standoffs, header, USB, keys, mics, battery, speaker, LRA, bosses (hidden = behind the glass)
    for x, y in P_SO:
        px, py = VF.p(x, y)
        sh.circle(px, py, 1.6 * k, 'h')
        sh.line(px - 2.2 * k, py, px + 2.2 * k, py, 'c')
        sh.line(px, py - 2.2 * k, px, py + 2.2 * k, 'c')
    H = P_HDR
    sh.poly(VF.pl([(H['x0'], H['y0']), (H['x1'], H['y0']), (H['x1'], H['y1']), (H['x0'], H['y1'])]), 'h')
    sh.poly(VF.pl([(-4.5, P_USB_Y - 7.3), (4.5, P_USB_Y - 7.3), (4.5, P_USB_Y), (-4.5, P_USB_Y)]), 'h')
    cut_top = 4 + 32
    sh.poly(VF.pl([(-6.2, P_USB_Y), (-6.2, cut_top - 0.2), (6.2, cut_top - 0.2), (6.2, P_USB_Y)]), 'h', close=False)
    B = P_BAT
    sh.poly(VF.pl([(B['x0'], B['y0']), (B['x1'], B['y0']), (B['x1'], B['y1']), (B['x0'], B['y1'])]), 'ph')
    S = P_SPK
    spk = arc_pts(S['x1'] - 9.5, (S['y0'] + S['y1']) / 2, 9.5, -90, 90, 12) + arc_pts(S['x0'] + 9.5, (S['y0'] + S['y1']) / 2, 9.5, 90, 270, 12)
    sh.poly(VF.pl(spk), 'h')
    sh.poly(VF.pl(arc_pts(*P_LRA['c'], P_LRA['r'], 0, 360, 40)), 'h')
    for x, y in P_BOSS:
        sh.poly(VF.pl(arc_pts(x, y, 2.8, 0, 360, 24)), 'o3')
        sh.poly(VF.pl(arc_pts(x, y, 1.6, 0, 360, 16)), 'h')
    holes = []
    for (o, a), d in ((P_PWR, 2.6), (P_BOOT, 1.6)):
        e = ray_exit(o, a, hw)
        sh.line(*VF.p(*o), *VF.p(*e), 'h')
        sh.circle(*VF.p(*o), 0.9 * k, 'o3')
        holes.append(e)
    for o, a in P_MICS:
        e = ray_exit(o, a, hw)
        sh.line(*VF.p(*o), *VF.p(*e), 'h')
        holes.append(e)
    x0, y0 = VF.p(0, 0)
    yd = VF.p(0, 4)[1]
    sh.line(x0, VF.p(0, 39)[1], x0, VF.p(0, -39)[1], 'c')
    sh.line(VF.p(-36, 4)[0], yd, VF.p(36, 4)[0], yd, 'c')
    # section line B-B
    ya, yb = VF.p(0, 42)[1], VF.p(0, -42)[1]
    sh.line(x0, ya, x0, yb, 'cut')
    sh.section_arrow(x0, ya, 'B', (-1, 0))
    sh.section_arrow(x0, yb, 'B', (-1, 0))
    # callouts
    lead_l(sh, VF.p(*holes[3]), 86, ['2\u00d7 MIC \u00d81.0 (port dir. ?)'], xl=13)
    lead_l(sh, VF.p(H['x0'], 12), 94, ['8-PIN HEADER, 12.7 DEEP (V)'], xl=13)
    lead_l(sh, VF.p(*arc_pts(0, 4, r_ap, 150, 150, 1)[0]), 103, ['APERTURE \u00d747.36', 'LIP 0.8 OVER GLASS'], xl=13)
    lead_l(sh, VF.p(*P_SO[0]), 200, ['3\u00d7 M2 STANDOFF', 'END z\u221210.43 (V)'], xl=13)
    lead_l(sh, VF.p(*holes[1]), 214, ['BOOT \u00d81.6 / PWR \u00d82.6', 'PIN HOLES (V pos.)'], xl=13)
    lead_l(sh, VF.p(-12.0 - 3.5, -26 - 3.5), 228, ['LRA \u00d810 + DRV2605L', '(E)'], xl=13)
    lead_r(sh, VF.p(*P_BOSS[1]), 166, 98, ['4× M2 INSERT BOSS', 'Ø5.6 (E)'])
    lead_r(sh, VF.p(24, 20), 166, 112, ['CELL 523450', '50×34 (hidden)'])
    lead_r(sh, VF.p(*P_SO[2]), 166, 150, ['BOARD Ø46.0 (V)', 'ROTATED 180°'])
    lead_r(sh, VF.p(14.2, -27), 166, 214, ['KIT SPEAKER 2030', '20×30×5.5 (unverif.)'])
    sh.text(x0 + 30, TY, 'FRONT VIEW', 3.2, 'middle', 'tx', weight='bold')
    # display CL offset
    sh.dim_v(VF.p(-36, 4)[0], yd, VF.p(-36, 0)[0], y0, VF.p(-36, 0)[0] - 3, '4.0', gap=0.5, arrows_out=True, size=2.3)
    sh.line(VF.p(-36, 0)[0], y0, VF.p(-26, 0)[0], y0, 'c')

    # ---------- TOP ----------
    def pt(x, z):
        return VT.p(x, -z)
    sh.poly([pt(s, z) for s, z in P_PROF_X], 'o')
    sh.line(*pt(-32, P_PART), *pt(32, P_PART), 'o2')
    sh.line(*pt(-32, PZF - PRF), *pt(32, PZF - PRF), 'o3')
    tpx, tpz = P_INFO_X['tp']
    sh.line(*pt(-tpx, tpz), *pt(tpx, tpz), 'o3')
    sh.poly([pt(-6.2, -5.05), pt(6.2, -5.05), pt(6.2, -12.05), pt(-6.2, -12.05)], 'o')   # USB-C cut
    sh.poly([pt(-4.5, -7.0), pt(4.5, -7.0), pt(4.5, -10.1), pt(-4.5, -10.1)], 'o2')       # receptacle
    for o, a in P_MICS:
        e = ray_exit(o, a, hw)
        sh.circle(*pt(e[0], -7.5), 0.5 * k, 'o2')
    sh.poly([pt(-5, -14.0), pt(5, -14.0), pt(5, -18.0), pt(-5, -18.0)], 'h')             # strap pocket
    sh.line(*pt(0, 3.0), *pt(0, -26.0), 'c')
    ybt = pt(0, -PT + PZF)[1]
    sh.dim_h(*pt(-32, -8), *pt(32, -8), ybt - 7, '64.0')
    lead_r(sh, pt(6.2, -8.5), 166, 52, ['USB-C CUT 12.4×7.0', 'CL AT z −8.55 (V)'])
    lead_r(sh, pt(5, -16), 166, 66, ['STRAP POCKET (E)'])
    sh.text(pt(0, 0)[0], ybt - 12, 'TOP VIEW', 3.2, 'middle', 'tx', weight='bold')

    # ---------- SECTION B-B (right side, cut at x = 0) ----------
    def ps(z, y):
        return VS.p(-z, y)
    zc = PZF - PT + PRD
    def inner_back(y):
        return zc - math.sqrt((PRD - 2.0) ** 2 - y * y)
    # shells: approximate as outer profile hatched, then carve the cavity
    sh.poly([ps(z, s) for s, z in P_PROF_Y], 'o2', extra='style="fill:url(#hA)"')
    # cavity: from z = -1.2 (behind aperture lip) to the inner back, |y| <= 34.2
    cav_pts, _ = profile(34.2, 21.0, PRD - 2.0, PRF - 1.8, PRB - 2.0, zf=0.0)
    cav = [(z, y) for y, z in cav_pts]
    sh.poly([ps(z, y) for z, y in cav], 'o2', extra='style="fill:%s"' % sh.th['bg'])
    sh.line(*ps(P_PART, -35.0), *ps(P_PART, 35.0), 'o3')
    ra = G_R - 0.8
    sh.poly([ps(PZF + 0.2, 4 - ra), ps(PZF + 0.2, 4 + ra), ps(0, 4 + ra), ps(0, 4 - ra)], 'o3', extra='style="fill:%s;stroke:none"' % sh.th['bg'])
    sh.line(*ps(PZF, 4 + ra), *ps(0, 4 + ra), 'o2')
    sh.line(*ps(PZF, 4 - ra), *ps(0, 4 - ra), 'o2')
    # glass, module, PCB, components
    sh.poly([ps(0, -20.48), ps(0, 28.48), ps(-1.1, 28.48), ps(-1.1, -20.48)], 'gl')
    sh.poly([ps(-1.1, -19.0), ps(-1.1, 27.0), ps(-5.7, 27.0), ps(-5.7, -19.0)], 'f2')
    sh.poly([ps(-5.7, -19.0), ps(-5.7, 27.0), ps(-6.9, 27.0), ps(-6.9, -19.0)], 'o2', extra='style="fill:url(#hC)"')
    for y0_, y1_, d in ((-10.0, 2.0, 8.9), (6.0, 14.0, 8.2), (-17.5, -12.5, 7.6)):
        sh.poly([ps(-6.9, y0_), ps(-6.9, y1_), ps(-d, y1_), ps(-d, y0_)], 'f2')
    # USB-C receptacle at top (x = 0 lies in the section)
    sh.poly([ps(-7.0, P_USB_Y - 7.3), ps(-7.0, P_USB_Y), ps(-10.1, P_USB_Y), ps(-10.1, P_USB_Y - 7.3)], 'o2', extra='style="fill:url(#hS)"')
    sh.poly([ps(-5.05, P_USB_Y), ps(-5.05, 36.2), ps(-12.05, 36.2), ps(-12.05, P_USB_Y)], 'o2', extra='style="fill:%s"' % sh.th['bg'])
    # header (projected, hidden), standoff (projected)
    sh.poly([ps(-6.9, H['y0']), ps(-6.9, H['y1']), ps(-12.7, H['y1']), ps(-12.7, H['y0'])], 'h')
    so = P_SO[0]
    sh.poly([ps(-6.9, so[1] - 1.6), ps(-6.9, so[1] + 1.6), ps(-10.43, so[1] + 1.6), ps(-10.43, so[1] - 1.6)], 'h')
    # battery + foam
    B = P_BAT
    sh.poly([ps(B['z0'], B['y0']), ps(B['z0'], B['y1']), ps(B['z1'], B['y1']), ps(B['z1'], B['y0'])], 'fb')
    sh.poly([ps(B['z1'], B['y0'] + 2), ps(B['z1'], B['y1'] - 2), ps(-19.0, B['y1'] - 2), ps(-19.0, B['y0'] + 2)], 'o3', extra='style="fill:url(#hD)"')
    # speaker
    S = P_SPK
    sh.poly([ps(S['z0'], S['y0']), ps(S['z0'], S['y1']), ps(S['z1'], S['y1']), ps(S['z1'], S['y0'])], 'f2')
    sh.poly([ps(S['z0'] - 0.4, S['y0'] + 3), ps(S['z1'] + 1.0, S['y0'] + 7), ps(S['z1'] + 1.0, S['y1'] - 7), ps(S['z0'] - 0.4, S['y1'] - 3)], 'o3', close=False)
    # LRA (projected hidden)
    L = P_LRA
    sh.poly([ps(L['z0'], L['c'][1] - 5), ps(L['z0'], L['c'][1] + 5), ps(L['z1'], L['c'][1] + 5), ps(L['z1'], L['c'][1] - 5)], 'h')
    sh.poly([ps(z, s) for s, z in P_PROF_Y], 'o')
    sh.line(*ps(3.0, 0), *ps(-26, 0), 'c')
    sh.line(*ps(3.0, 4), *ps(-3, 4), 'c')
    xr = ps(-PT + PZF, 0)[0]
    sh.dim_v(*ps(-11, 36), *ps(-11, -36), xr + 7, '72.0')
    yy = ps(0, -6)[1]
    sh.line(ps(PZF, -6)[0], yy, ps(dome_z(6, PT, PRD, PZF), -6)[0], yy, 't')
    sh.arrow(ps(PZF, -6), ps(-5, -6))
    sh.arrow(ps(dome_z(6, PT, PRD, PZF), -6), ps(-10, -6))
    tw_ = sh.tw('24.0 @ CL', 2.4)
    sh.rect(ps(-11, 0)[0] - tw_ / 2 - 0.8, yy + 0.9, tw_ + 1.6, 3.4, 'bgf')
    sh.text(ps(-11, 0)[0], yy + 3.4, '24.0 @ CL', 2.4, 'middle', 'td')
    tpy, tpzy = P_INFO_Y['tp']
    fz = P_INFO_Y['fc'][1]
    sh.dim_h(*ps(PZF - PRF, 36), *ps(fz, 36), ps(0, 36)[1] - 6, '≈14.4 edge (E)')
    xa = xr + 12
    lead_r(sh, ps(-9.5, P_USB_Y - 3), xa, 100, ['USB-C', 'z −8.55'])
    lead_r(sh, ps(-6.3, 20.0), xa, 114, ['PCB', '5.70/6.90'])
    lead_r(sh, ps(-12.7, 10), xa, 128, ['HEADER', '12.70 (V)'])
    lead_r(sh, ps(-15.6, 8), xa, 146, ['CELL', '13.0-18.2'])
    lead_r(sh, ps(-18.6, -4), xa, 160, ['FOAM 0.8'])
    lead_r(sh, ps(-12.0, -24), xa, 180, ['SPEAKER', '9.1-14.6'])
    lead_r(sh, ps(P_PART, -34), xa, 194, ['SPLIT', 'z −12.0 (E)'])
    lead_r(sh, ps(dome_z(18, PT, PRD, PZF) + 0.3, -18), xa, 210, ['BACK R250', 'WALL 2.0 (E)'])
    lead_r(sh, ps(-3.5, -26), xa, 224, ['LRA (hidden)'])
    sh.text(ps(-12, 0)[0], TY, 'SECTION B-B', 3.2, 'middle', 'tx', weight='bold')

    # ---------- board table ----------
    tx0, ty0 = 298, 16
    sh.text(tx0, ty0 + 2.5, 'WAVESHARE ESP32-S3-TOUCH-AMOLED-1.75', 2.45, 'start', 'tx', weight='bold')
    sh.text(tx0, ty0 + 6.5, 'data from the Waveshare STEP model', 2.0, 'start', 'td')
    rows = [
        ('Cover glass', 'Ø48.96 × 1.10', 'V'),
        ('Flat front of glass', 'Ø44.16', 'V'),
        ('Active / touch area', 'Ø43.76 (466×466)', 'V'),
        ('Display module + PCB', 'Ø46.0', 'V'),
        ('PCB front / back depth', '5.70 / 6.90', 'V'),
        ('Deepest: 8-pin header, edge', '12.70', 'V'),
        ('Deepest under cell footprint', '8.90', 'V'),
        ('M2 standoffs (3), end depth', '10.43', 'V'),
        ('  native (14.70, ±13.75), (−20.50, 0)', '', 'V'),
        ('USB-C face r / tongue depth', '23.80 / 8.55', 'V'),
        ('PWR / BOOT key depth', '7.60', 'V'),
        ('Mics (2) depth / port dir.', '7.5 / ?', 'V/?'),
        ('Board orientation in shell', 'rot. 180°', 'E'),
        ('Cell LiPo 523450 1000 mAh', '5.2×34×50', 'K'),
        ('Kit speaker 2030 (8 Ω 2 W)', '20×30×5.5', '?'),
        ('Shell: SLA clear, frosted', 'wall 1.8-2.0', 'E'),
        ('Envelope', '72×64×24', 'E'),
        ('Mass (research estimate)', '95-105 g', 'E'),
    ]
    cols = [0, 64, 101, 112]
    ty = ty0 + 10
    rh = 6.2
    sh.rect(tx0, ty, cols[-1], rh * (len(rows) + 1), 'fr2t')
    for j, h in enumerate(['ITEM', 'VALUE (mm)', 'SRC']):
        sh.text(tx0 + cols[j] + 1, ty + 4.3, h, 2.1, 'start', 'td')
    sh.line(tx0, ty + rh, tx0 + cols[-1], ty + rh, 'fr2t')
    for c in cols[1:-1]:
        sh.line(tx0 + c, ty, tx0 + c, ty + rh * (len(rows) + 1), 'fr1')
    for i, r in enumerate(rows):
        yy = ty + rh * (i + 1)
        if not r[0].startswith('  '):
            sh.line(tx0, yy, tx0 + cols[-1], yy, 'fr1')
        for j, v in enumerate(r):
            cls = 'ta' if (j == 2 and v == 'V') else 'tx'
            sh.text(tx0 + cols[j] + 1, yy + 4.3, v.strip() if j else v, 2.1, 'start', cls)
    yy = ty + rh * (len(rows) + 1) + 5
    notes = [
        'PROTOTYPE NOTES',
        '1. Same outline family as sheet 1, scaled to fit',
        '   the dev board: 72×64×24 vs 68×60×19.',
        '2. Board rotated 180°: USB-C at 12 o\'clock under',
        '   the strap bar; mics top, PWR/BOOT lower edge.',
        '   Eyes re-oriented in firmware (rotation flag).',
        '3. Cell covers the header edge, so it sits behind',
        '   z −13.0 (header 12.70 + 0.3): drives 24 mm.',
        '4. Charge current: raise AXP2101 to ~500 mA.',
        '5. Measure with calipers before printing: cell,',
        '   kit speaker, cable plug, mic port direction.',
    ]
    for i, n in enumerate(notes):
        sh.text(tx0, yy + i * 3.6, n, 2.5 if i == 0 else 2.1, 'start', 'tx' if i else 'tx', weight='bold' if i == 0 else None)

    sh.title_block('GA · DEV PROTOTYPE', 'WAVESHARE 1.75 BOARD · 72 × 64 × 24', '2:1', '4 / 4', 'SOUL-GA-004')
    return sh


def write(sh, name):
    p = os.path.join(OUT, name)
    open(p, 'w', encoding='utf-8').write(sh.svg())
    print('svg', p)
    return p


if __name__ == '__main__':
    which = sys.argv[1:] or ['ga']
    if 'ga' in which:
        write(sheet_ga('blue'), 'soul_blueprint_ga.svg')
        write(sheet_ga('white'), 'soul_ga_white.svg')
    if 'pro' in which:
        write(sheet_proto('blue'), 'soul_blueprint_proto.svg')
    if 'exp' in which:
        write(sheet_exploded('blue'), 'soul_blueprint_exploded.svg')
    if 'sec' in which:
        write(sheet_section('blue'), 'soul_blueprint_section.svg')
