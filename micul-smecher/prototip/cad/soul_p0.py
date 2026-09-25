#!/usr/bin/env python3
"""soul_p0.py -- SOUL-P0 size M: DIY pilot enclosure of SOUL (v6 look) for the stock
Waveshare ESP32-S3-Touch-LCD-2.8C (round 2.8" IPS 480x480, lens Ø95.86, active Ø70.64).

CadQuery 2.x. Builds, checks and exports every part in two material variants:

  PLASTIC  (FDM / SLA): 2.0 mm walls, 0.2 mm fit clearances, 1.2 mm lip over the lens, M2 heat-set inserts
  ALU      (CNC 6061-T6): 1.6 mm walls, 0.1 mm clearances, 0.8 mm lip, tapped M2 in the front bosses;
           2 halves split on ONE plane through the silhouette (3-axis, no undercut).
           The bottom is always the printed polymer BASE PLATE + oval foot = the antenna window (as v6).

Parts: front_shell, back_shell, base_plate (with the v6 oval foot), chassis (always printed),
       pin_boot, pin_rst.  Bought: board, LiPo 605060, speaker 2030, MAX98357A amp, INMP441 mic,
       USB-C 90-degree extension (male on the board, female socket in the back at the bottom).

Usage:
    python3 soul_p0.py                  # plastic + alu -> ../stl, ../step (+ .gz), ../cad/report_*.json
    python3 soul_p0.py plastic          # one variant
    python3 soul_p0.py finish plastic   # re-check + re-export from cache/ without rebuilding

Frame (mm): origin = centre of the flat base plane, +Z up, the face looks toward -Y, +X = viewer's right.
Board frame: (bx, by) in the lens plane (by up, seen from the FRONT), dd = depth behind the lens front.
Board numbers: Waveshare drawing ESP32-S3-Touch-LCD-2.8C-20241226 (lens OD 95.86, AV 70.64, lens 0.7,
LCD+AV 3.66, 5.7 / 9.7 stack, 4x M2 at (±29.5, 15.14) and (±18, -25.56), board Ø73). Positions of the keys,
connectors and USB-C are read off the Waveshare photo/drawing (+-1 mm) and are marked UNVERIFIED.
The 1.75" (size S) version of this kit is in ../legacy-S/.
"""
import gzip
import json
import math
import os
import shutil
import sys
import time

import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soul_geom as g  # noqa: E402

OUT = os.path.abspath(os.path.join(HERE, '..'))

# ============================================================================ variants
VARIANTS = {
    'plastic': dict(wall=2.0, tol=0.2, lip_t=1.2, lip_over=1.5, tongue_t=1.0, tongue_h=1.5,
                    boss_d=6.0, hole='insert', insert_d=3.2, insert_depth=4.6, clear_d=2.3,
                    cb_d=4.3, cb_depth=1.8, pin_hole=2.3, pin_d=1.9, chamfer=0.6, band=0.0),
    'alu': dict(wall=1.6, tol=0.1, lip_t=0.8, lip_over=1.5, tongue_t=0.9, tongue_h=1.2,
                boss_d=5.6, hole='tap', insert_d=1.6, insert_depth=4.5, clear_d=2.2,
                cb_d=4.2, cb_depth=1.7, pin_hole=2.1, pin_d=1.8, chamfer=0.8, band=0.0),
}
BASE_T = 3.0            # polymer base plate thickness (the shells start at Z = BASE_T)

# ============================================================================ board (Waveshare 2.8C)
LENS_R, LENS_T = 47.93, 0.70          # lens OD 95.86 +-0.1, glass 0.7 (drawing)
VIEW_R = 35.32                        # AV 70.64 (drawing)
LCD_R, LCD_D = 38.8, 3.66             # LCD cell behind the lens (73 x 77.6 panel, envelope r 38.8), LCD+AV 3.66
PCB_R, PCB_D = 36.5, 5.70             # board Ø73 (2 x 36.5), PCB back at 5.7 (drawing)
COMP_R, COMP_D = 36.0, 9.70           # tallest back-side parts at 9.7 (drawing)
MH = [(-29.5, 15.14), (29.5, 15.14), (-18.0, -25.56), (18.0, -25.56)]    # 4x M2 (drawing)
# keys at the +x edge (seen from the front; the drawing shows them on the left because it is the back view)
KEYS = {'boot': (34.5, 8.6), 'rst': (34.5, -1.0)}                          # UNVERIFIED +-1
KEY_DD = 7.6
SWITCH = (34.5, -7.9)                                                       # ON/OFF slide switch, UNVERIFIED
USBC = {'usb_r': (27.0, -26.5, -45.0), 'usb_l': (-27.0, -26.5, -135.0)}     # centre, outward dir (deg), UNVERIFIED
USB_USED = 'usb_r'                                                          # the UART (CH343) port gets the 90° plug
BATCONN = (22.0, 18.0)                                                      # MX1.25 BAT, UNVERIFIED
PLUG_DD = 13.0                                                              # mated plug + wires keep-out

# ============================================================================ bought parts inside (board frame)
BAT = dict(name='LiPo 605060 (6 x 50 x 60, ~2000 mAh, PCM, MX1.25)', W=50.5, L=61.0, T=6.3, bx=0.0, by=-20.0)
SPK = dict(name='speaker 2030 cavity 8 ohm 1 W', a=30.0, b=20.0, t=5.2, bx=20.0, by=32.0)
AMP = dict(name='MAX98357A I2S amp breakout', a=18.0, b=20.0, t=3.6, bx=-15.0, by=26.0)
MIC = dict(name='INMP441 I2S mic breakout', a=14.0, b=14.0, t=3.4, bx=-34.0, by=-1.0)
PLATE_DD = (10.0, 11.4)                 # chassis plate behind the tallest board parts
# screws: 4x M2 from the back, through the chassis legs, into the front bosses; 2x M2 from below (base plate)
SCREWS = [(-35.0, 22.0), (35.0, 22.0), (-40.5, 102.0), (40.5, 102.0)]     # (x, Z) on the parting plane
BASE_SCREWS = [(-16.0, -9.0), (16.0, -9.0)]                                # (x, y), into front-shell bosses
SLOT = dict(z0=80.0, z1=100.0, w=1.2)   # speaker slot in the +x seam (v6: 12 x 0.6 at S scale)
MIC_Z = 66.0                            # mic pinhole Ø1.0 in the -x seam
SOCKET = dict(z=BASE_T + 5.2, w=12.6, h=7.2, L=19.0, mouth_w=9.4, mouth_h=3.6)   # rear USB-C female (UNVERIFIED)
MAGNETS = [(-24.0, 3.0), (24.0, 3.0)]   # optional Ø6x2 recesses in the base plate top (x, y)
MAG_D, MAG_H = 6.2, 2.1


# ============================================================================ helpers
def vec(p):
    return cq.Vector(float(p[0]), float(p[1]), float(p[2]))


def loft(rings, ruled=False):
    wires = []
    for Z, P in rings:
        pts = [cq.Vector(float(x), float(y), float(Z)) for x, y in P]
        wires.append(cq.Wire.assembleEdges([cq.Edge.makeSpline(pts, periodic=True)]))
    s = cq.Solid.makeLoft(wires, ruled)
    if s.Volume() < 0:
        s = cq.Solid(s.wrapped.Reversed())
    return s


N_RING = 96


def outer_solid():
    f = g.H_TOTAL / 75.0
    Zs = np.concatenate([[0.0, 0.4, 1.0, 1.8, 2.8, 4.0, 5.5, 7.5, 10.0], np.linspace(12, 60, 21) * f,
                         np.array([62, 64, 66, 68, 69.5, 71, 72, 73, 73.8, 74.4, 74.8, 74.97]) * f])
    Zs[-1] = g.H_TOTAL - 0.02
    return loft([(Z, g.ring_pts(Z, N_RING)) for Z in Zs])


def eroded_solid(t):
    """Inner solid = outer body eroded by a ball of radius t (sampled slices -> loft)."""
    rings = []
    H = g.H_TOTAL
    Zs = list(np.concatenate([[t, t + 0.3, t + 0.8, t + 1.6, t + 2.6, t + 4.0, t + 6.0], np.linspace(t + 8.5, 0.9 * H, 32),
                              np.arange(0.9 * H + 1.0, H + 1, 0.8)]))
    for Z in Zs:
        p = g.eroded_poly(Z, t)
        if p.is_empty or p.area < 30.0:
            break
        r_ = g.poly_ring_angular(p, 96, cy=float(g.sections(np.array([Z]))[3][0]))
        if r_ is None:
            break
        rings.append((Z, r_))
    return loft(rings)


class BoardFrame:
    """Glass-front frame: local x = X, local y = in-plane up, local z = outward normal (depth dd = -local z)."""

    def __init__(self, dg):
        self.dg = dg
        self.O = g.G + dg * g.INW
        self.plane = cq.Plane(origin=vec(self.O), xDir=(1, 0, 0), normal=vec(g.N_OUT))

    def w(self, bx, by, dd):
        return self.O + bx * np.array([1.0, 0, 0]) + by * g.UP + dd * g.INW

    def cyl(self, r, dd0, dd1, bx=0.0, by=0.0):
        return (cq.Workplane(self.plane).center(bx, by).workplane(offset=-dd1)
                .circle(r).extrude(dd1 - dd0).val())

    def box(self, x0, x1, y0, y1, d0, d1):
        return (cq.Workplane(self.plane).workplane(offset=-d1).center((x0 + x1) / 2, (y0 + y1) / 2)
                .rect(x1 - x0, y1 - y0).extrude(d1 - d0).val())

    def slot(self, w, h, by0, by1, dd):
        """Stadium prism (w along bx, h along dd) running along by from by0 to by1, centred on bx=0, depth dd."""
        L = by1 - by0
        pl = cq.Plane(origin=vec(self.w(0, by0, dd)), xDir=(1, 0, 0), normal=vec(g.UP))
        return cq.Workplane(pl).slot2D(w, h, 0).extrude(L).val()


class SeamFrame:
    """Parting plane frame: s = signed distance toward the back (+Y side)."""
    NS = np.array([0.0, 1.0, -g.SEAM_B]) / math.hypot(1.0, g.SEAM_B)
    US = np.array([0.0, g.SEAM_B, 1.0]) / math.hypot(1.0, g.SEAM_B)
    P0 = np.array([0.0, g.SEAM_A, 0.0])
    plane = cq.Plane(origin=vec(P0), xDir=(1, 0, 0), normal=vec(NS))

    @classmethod
    def s(cls, p):
        return float(np.dot(np.asarray(p) - cls.P0, cls.NS))

    @classmethod
    def pt(cls, x, Z):
        """point on the plane at (x, Z)"""
        y = g.SEAM_A + g.SEAM_B * Z
        return np.array([x, y, Z])

    @classmethod
    def slab(cls, s0, s1, big=200.0):
        return (cq.Workplane(cls.plane).workplane(offset=s0).rect(big, big).extrude(s1 - s0).val())

    @classmethod
    def cyl(cls, x, Z, r, s0, s1):
        p = cls.pt(x, Z)
        pl = cq.Plane(origin=vec(p + s0 * cls.NS), xDir=(1, 0, 0), normal=vec(cls.NS))
        return cq.Workplane(pl).circle(r).extrude(s1 - s0).val()


def inside_outer(p):
    """point inside the outer body?"""
    from shapely.geometry import Point
    Z = float(p[2])
    if Z <= 0 or Z >= g.H_TOTAL:
        return False
    return g.outer_poly(round(Z, 2)).contains(Point(float(p[0]), float(p[1])))


def ray_exit(p0, d, step=0.02, tmax=60.0):
    """distance along d from an inside point p0 until it leaves the outer body"""
    d = np.asarray(d, float) / np.linalg.norm(d)
    t = 0.0
    while t < tmax and inside_outer(p0 + t * d):
        t += 0.25
    lo, hi = max(t - 0.25, 0), t
    while hi - lo > step:
        m = (lo + hi) / 2
        if inside_outer(p0 + m * d):
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def hollow(outer, inner):
    """solid between two nested closed lofts (a Boolean cut of nested lofts gives an invalid solid in OCCT)"""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.TopoDS import TopoDS
    mk = BRepBuilderAPI_MakeSolid()
    mk.Add(outer.Shells()[0].wrapped)
    mk.Add(TopoDS.Shell_s(inner.Shells()[0].wrapped.Reversed()))
    return cq.Solid(mk.Solid())


def fuse(*shapes):
    shapes = [s for s in shapes if s is not None]
    r = shapes[0]
    for s in shapes[1:]:
        r = r.fuse(s)
    return r.clean()


def cut(a, *bs):
    for b in bs:
        if b is not None:
            a = a.cut(b)
    return a


def vol(s):
    try:
        return abs(s.Volume())
    except Exception:
        return 0.0


def bat_geometry(bf):
    """tilted battery envelope: returns (solid, dict with corners in board frame)"""
    (byt, ddt) = BAT['top']
    (byb, ddb) = BAT['tilt_to']
    a = np.array([byt - byb, ddt - ddb])
    a /= np.linalg.norm(a)                                    # bottom -> top, in (by, dd)
    nrm = np.array([a[1], -a[0]]) if a[1] < 0 else np.array([-a[1], a[0]])
    if nrm[1] < 0:
        nrm = -nrm                                             # toward +dd (back)
    top_f = np.array([byt, ddt])
    bot_f = top_f - a * BAT['L']
    return a, nrm, top_f, bot_f


def tilted_box(bf, x0, x1, p_bot, a, nrm, L, T):
    """box in board frame: x from x0..x1, starting at (by,dd)=p_bot, length L along a, thickness T along nrm"""
    o = bf.w(0, p_bot[0], p_bot[1])
    ydir = a[0] * g.UP + a[1] * g.INW                          # along the long axis (world)
    zdir = nrm[0] * g.UP + nrm[1] * g.INW                      # thickness direction (world)
    pl = cq.Plane(origin=vec(o), xDir=(1, 0, 0), normal=vec(zdir))
    # plane local y = normal x xDir; make sure it points along ydir
    ly = np.cross(zdir, [1, 0, 0])
    sgn = 1.0 if np.dot(ly, ydir) > 0 else -1.0
    return (cq.Workplane(pl).center((x0 + x1) / 2, sgn * L / 2).rect(x1 - x0, L).extrude(T).val())



def to_mesh(shape, tol=0.03):
    import tempfile
    import trimesh
    fd, fn = tempfile.mkstemp(suffix='.stl')
    os.close(fd)
    cq.exporters.export(cq.Workplane().add(shape), fn, tolerance=tol, angularTolerance=0.2)
    m = trimesh.load(fn)
    os.remove(fn)
    m.merge_vertices()
    if not m.is_volume:
        trimesh.repair.fill_holes(m)
        trimesh.repair.fix_normals(m)
    return m


def inter_vol(a, b, A=None, B=None):
    import trimesh
    try:
        iv = trimesh.boolean.intersection([a, b], engine='manifold')
        return float(iv.volume) if len(iv.faces) else 0.0
    except Exception:
        return vol(A.intersect(B)) if A is not None else -1.0


def grow(solid, d):
    """approximate offset of a (convex-ish) solid by d: scale about its centre so the bbox grows by 2d"""
    bb = solid.BoundingBox()
    c = bb.center
    sx = (bb.xlen + 2 * d) / max(bb.xlen, 1e-6)
    sy = (bb.ylen + 2 * d) / max(bb.ylen, 1e-6)
    sz = (bb.zlen + 2 * d) / max(bb.zlen, 1e-6)
    from OCP.gp import gp_GTrsf, gp_Mat, gp_XYZ
    from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
    gt = gp_GTrsf()
    gt.SetVectorialPart(gp_Mat(sx, 0, 0, 0, sy, 0, 0, 0, sz))
    gt.SetTranslationPart(gp_XYZ(c.x * (1 - sx), c.y * (1 - sy), c.z * (1 - sz)))
    return cq.Shape.cast(BRepBuilderAPI_GTransform(solid.wrapped, gt, True).Shape())



def align(s, v_from, v_to):
    v_from = np.asarray(v_from, float) / np.linalg.norm(v_from)
    v_to = np.asarray(v_to, float) / np.linalg.norm(v_to)
    ax = np.cross(v_from, v_to)
    sn = np.linalg.norm(ax)
    cs = float(np.dot(v_from, v_to))
    if sn < 1e-9:
        if cs > 0:
            return s
        return s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180)
    ang = math.degrees(math.atan2(sn, cs))
    return s.rotate(cq.Vector(0, 0, 0), vec(ax / sn), ang)


def place_pin(pin, pl):
    """pin is built along +Z from 0 (tip at the actuator); map local Z to the pin axis frame pl (offset 0.2)."""
    T = cq.Location(cq.Plane(origin=pl.origin + pl.zDir * 0.2, xDir=pl.xDir, normal=pl.zDir))
    return pin.moved(T)



# ============================================================================ build one variant (size M)

def rbox(bf, cx, cy, ang, L, W, d0, d1):
    """box in the board frame centred at (cx, cy), long side L along direction ang (deg), depth d0..d1"""
    return (cq.Workplane(bf.plane).workplane(offset=-d1).center(cx, cy).transformed(rotate=(0, 0, ang))
            .rect(L, W).extrude(d1 - d0).val())


def half_prism(side, z0=None, big=300.0):
    """one clean prism: the front (side -1) or back (+1) of the parting plane, above the base plate (Z > z0)"""
    z0 = BASE_T if z0 is None else z0
    A, B = g.SEAM_A, g.SEAM_B
    zt = 400.0
    ys0, ys1 = A + B * z0, A + B * zt
    far = -big if side < 0 else big
    pts = [(ys0, z0), (ys1, zt), (far, zt), (far, z0)]
    w = cq.Workplane('YZ', origin=(-big, 0, 0)).polyline(pts).close().extrude(2 * big)
    return w.val()


def zslab(z0, z1, big=300.0):
    return cq.Workplane('XY').workplane(offset=z0).rect(big, big).extrude(z1 - z0).val()


def superellipse(a, b, p, n=160):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.stack([a * np.sign(c) * np.abs(c) ** (2 / p), b * np.sign(s) * np.abs(s) ** (2 / p)], 1)


def foot_solid(yc):
    pts = superellipse(g.FOOT_A, g.FOOT_B, g.FOOT_P)
    pts[:, 1] += yc
    w = cq.Workplane('XY').workplane(offset=-g.FOOT_H).polyline([tuple(p) for p in pts]).close().extrude(g.FOOT_H + 0.3)
    try:
        w = w.faces('<Z').edges().fillet(0.4)
    except Exception:
        pass
    return w.val()


def build(vname):
    V = VARIANTS[vname]
    t0 = time.time()
    log = []

    def say(*a):
        s = ' '.join(str(x) for x in a)
        print(s, flush=True)
        log.append(s)

    wall, tol = V['wall'], V['tol']
    dg = V['lip_t'] - 0.15
    bf = BoardFrame(dg)
    say(f'== {vname}: wall {wall} tol {tol} lip {V["lip_t"]}  (K {g.K}, KY {g.KY})')
    OUTER = outer_solid()
    INNER = eroded_solid(wall)
    TONG_OUT = eroded_solid(wall + tol)
    TONG_IN = eroded_solid(wall + tol + V['tongue_t'])
    TONG_CLR = eroded_solid(wall + 2 * tol + V['tongue_t'])
    say(f'  outer vol {vol(OUTER):.0f} mm3, inner {vol(INNER):.0f} mm3  ({time.time()-t0:.1f}s)')
    SHELL = hollow(OUTER, INNER)
    ABOVE = zslab(BASE_T, 400)

    # ------------------------------------------------ board keep-outs
    board = {
        'lens': bf.cyl(LENS_R, 0.0, LENS_T),
        'lcd': bf.cyl(LCD_R, LENS_T, LCD_D),
        'pcb': bf.cyl(PCB_R, LCD_D, PCB_D),
        'pcb_tab': bf.box(-20.4, 20.4, -44.0, -33.0, LENS_T, PCB_D),
        'components': bf.cyl(COMP_R, PCB_D, COMP_D),
        'bat_conn': bf.box(BATCONN[0] - 3.8, BATCONN[0] + 3.8, BATCONN[1] - 2.1, BATCONN[1] + 2.1, PCB_D, 10.5),
        'bat_plug': bf.box(BATCONN[0] - 4.8, BATCONN[0] + 4.8, BATCONN[1] - 3.0, BATCONN[1] + 3.0, 10.5, PLUG_DD),
        'switch': bf.box(SWITCH[0] - 2.0, SWITCH[0] + 3.0, SWITCH[1] - 3.5, SWITCH[1] + 3.5, PCB_D, 9.2),
    }
    for k, (x, y) in KEYS.items():
        board[f'key_{k}'] = bf.box(x - 1.8, x + 1.8, y - 1.8, y + 1.8, PCB_D, 9.0)
    for k, (x, y, a) in USBC.items():
        board[k] = rbox(bf, x, y, a, 7.6, 9.2, PCB_D, 9.2)
    ux, uy, ua = USBC[USB_USED]
    ar = math.radians(ua)
    # right-angle USB-C male plug: head 12 x 7, runs 10 mm outward then the cable turns back (dd +)
    pc = np.array([ux, uy]) + 7.5 * np.array([math.cos(ar), math.sin(ar)])
    usb_plug = rbox(bf, pc[0], pc[1], ua, 11.0, 12.6, 3.4, 16.0)

    # battery / speaker / amp / mic, lying on the chassis plate (their front at PLATE_DD[1] + 0.3)
    d_in = PLATE_DD[1] + 0.3

    def flat(D):
        a, b = D.get('W', D.get('a')), D.get('L', D.get('b'))
        return bf.box(D['bx'] - a / 2, D['bx'] + a / 2, D['by'] - b / 2, D['by'] + b / 2, d_in, d_in + D['T' if 'T' in D else 't'])
    battery, speaker, amp, mic = flat(BAT), flat(SPK), flat(AMP), flat(MIC)

    # ------------------------------------------------ halves: additions / cuts collected, applied once
    BIG = 300.0
    FRONT_HALF = half_prism(-1)
    BACK_HALF = half_prism(+1)
    add = {'front': [], 'back': [], 'base': []}
    sub = {'front': [], 'back': [], 'base': []}

    def to_shells(s):
        sub['front'].append(s)
        sub['back'].append(s)

    add['front'].append(TONG_OUT.intersect(SeamFrame.slab(-0.01, V['tongue_h'])).cut(TONG_IN).cut(zslab(-50, BASE_T)))
    sub['back'].append(INNER.intersect(SeamFrame.slab(-0.05, V['tongue_h'] + tol)).cut(TONG_CLR))

    # ------------------------------------------------ 4 screws from the back
    say('  screw columns (x, Z): front surface / back surface along the seam normal (s)')
    screw_info = []
    for (x, Z) in SCREWS:
        p = SeamFrame.pt(x, Z)
        s_front = -ray_exit(p, -SeamFrame.NS)
        s_back = ray_exit(p, SeamFrame.NS)
        r = V['boss_d'] / 2
        s_leg1 = round(max(min(s_back - wall - 2.5, 7.0), 1.5), 2)
        add['front'].append(SeamFrame.cyl(x, Z, r, s_front - 1.0, 0.0).intersect(OUTER))
        add['back'].append(SeamFrame.cyl(x, Z, r, s_leg1 + 0.15, s_back + 1.0).intersect(OUTER).intersect(BACK_HALF))
        depth = min(V['insert_depth'], -s_front - 1.6)
        sub['front'].append(SeamFrame.cyl(x, Z, V['insert_d'] / 2, -depth, 0.1))
        sub['back'].append(SeamFrame.cyl(x, Z, V['clear_d'] / 2, -0.2, s_back + 2))
        sub['back'].append(SeamFrame.cyl(x, Z, V['cb_d'] / 2, s_back - V['cb_depth'], s_back + 5))
        L_need = (s_back - V['cb_depth']) - (-depth + 0.5)
        screw_info.append(dict(x=x, Z=Z, s_front=round(s_front, 2), s_back=round(s_back, 2), hole_depth=round(depth, 2),
                               skin_under_hole=round(-depth - s_front, 2), s_leg1=s_leg1, screw_len_max=round(L_need, 2)))
        say(f'   ({x:+.1f},{Z:.1f}): front {s_front:.2f} back {s_back:.2f} hole {depth:.1f}, skin {-depth - s_front:.2f}'
            f', leg to s={s_leg1} -> screw <= {L_need:.1f} mm')

    # ------------------------------------------------ lens pocket, aperture, v6 chamfer
    r_ap = LENS_R - V['lip_over']
    pocket = bf.cyl(LENS_R + tol, V['lip_t'] - dg, LENS_T + 0.5).fuse(
        bf.cyl(LCD_R + tol + 0.3, LENS_T + 0.2, PCB_D + 0.5), bf.box(-21, 21, -45, -30, LENS_T + 0.2, PCB_D + 0.5))
    to_shells(pocket)
    sub['front'].append(bf.cyl(r_ap, -dg - 3.0, 1.0))
    ch = V['chamfer']
    sub['front'].append(cq.Workplane(bf.plane).workplane(offset=dg - ch).circle(r_ap)
                        .workplane(offset=ch + 0.01).circle(r_ap + ch + 0.01).loft().val())

    # ------------------------------------------------ side seam features: speaker slot (+x), mic hole (-x)
    L = SLOT['z1'] - SLOT['z0']
    zc = (SLOT['z0'] + SLOT['z1']) / 2
    w_c = float(g.sections(np.array([zc]))[0][0])
    pc_ = SeamFrame.pt(w_c - 9.0, zc)
    pl = cq.Plane(origin=vec(pc_), xDir=vec(SeamFrame.US), normal=(1, 0, 0))
    to_shells(cq.Workplane(pl).slot2D(L, SLOT['w'], 0).extrude(14.0).val())
    w_m = float(g.sections(np.array([MIC_Z]))[0][0])
    pm = SeamFrame.pt(-w_m + 6.0, MIC_Z)
    plm = cq.Plane(origin=vec(pm), xDir=(0, 1, 0), normal=(-1, 0, 0))
    to_shells(cq.Workplane(plm).circle(0.5).extrude(10.0).val())

    # ------------------------------------------------ keys: radial pins (+x), slide switch window
    pins = {}
    for k, (kx, ky_) in KEYS.items():
        w_act = bf.w(kx + 2.0, ky_, KEY_DD)
        dwrld = np.array([1.0, 0, 0])
        t_exit = ray_exit(w_act, dwrld)
        s_exit = SeamFrame.s(w_act + t_exit * dwrld)
        pl = cq.Plane(origin=vec(w_act), xDir=(0, 1, 0), normal=(1, 0, 0))
        to_shells(cq.Workplane(pl).workplane(offset=0.2).circle(V['pin_hole'] / 2).extrude(t_exit + 2).val())
        g0 = max(t_exit - wall - 4.5, 2.5)
        guide = cq.Workplane(pl).workplane(offset=g0).circle(V['pin_hole'] / 2 + 1.2).extrude(6.0).val().intersect(OUTER)
        add['front'].append(guide.intersect(FRONT_HALF))
        add['back'].append(guide.intersect(BACK_HALF))
        L_pin = t_exit - 0.2 - 0.3
        pin = (cq.Workplane('XY').circle(V['pin_d'] / 2).extrude(L_pin)
               .faces('<Z').workplane().circle(1.6).extrude(0.8).val())
        pins[k] = dict(solid=pin, L=round(L_pin, 2), s_exit=round(s_exit, 2), frame=pl, t_exit=t_exit,
                       exit=[round(float(v), 2) for v in (w_act + t_exit * dwrld)])
        say(f'  pin {k}: length {L_pin:.1f} mm, exits at {pins[k]["exit"]} (s = {s_exit:+.2f}, on the seam line)')
    sw_c = bf.w(SWITCH[0] + 3.0, SWITCH[1], KEY_DD)
    pls = cq.Plane(origin=vec(sw_c), xDir=vec(g.UP), normal=(1, 0, 0))
    to_shells(cq.Workplane(pls).rect(8.0, 3.2).extrude(40.0).val())
    say('  switch window 8 x 3.2 mm in the +x seam (push the ON/OFF lever with a toothpick)')

    # ------------------------------------------------ rear USB-C socket (female end of the 90° extension)
    S_ = SOCKET
    y_back = float(g.sections(np.array([S_['z']]))[2][0])
    sock_body = (cq.Workplane('XZ', origin=(0, y_back - 0.8, S_['z'])).rect(S_['w'], S_['h'])
                 .extrude(S_['L']).val())             # 'XZ' extrudes toward -Y
    mouth = cq.Workplane('XZ', origin=(0, y_back + 3.0, S_['z'])).slot2D(S_['mouth_w'] + 0.4, S_['mouth_h'] + 0.4, 0) \
        .extrude(8.0).val()
    sub['back'] += [mouth, sock_body]

    # ------------------------------------------------ base plate (polymer, antenna window) + v6 oval foot
    yc = 0.5 * float(g.sections(np.array([0.0]))[1][0] + g.sections(np.array([0.0]))[2][0])
    base = OUTER.intersect(zslab(0.0, BASE_T))
    rim = TONG_OUT.intersect(zslab(BASE_T - 0.01, BASE_T + 2.5)).cut(TONG_IN)
    add['base'] += [rim, foot_solid(yc)]
    clamp = (cq.Workplane('XY', origin=(0, y_back - 0.8 - S_['L'] / 2 - 0.5, BASE_T - 0.01))
             .rect(S_['w'] + 3.0, S_['L'] - 3.0).extrude(S_['z'] - BASE_T - S_['h'] / 2 + 0.01).val())
    add['base'].append(clamp.intersect(TONG_OUT))
    sub['base'].append(sock_body)
    for (bx_, by_) in BASE_SCREWS:
        col = cq.Workplane('XY', origin=(bx_, by_, BASE_T - 0.01)).circle(3.0).extrude(9.0).val().intersect(OUTER)
        add['front'].append(col.intersect(FRONT_HALF))
        sub['front'].append(cq.Workplane('XY', origin=(bx_, by_, BASE_T - 0.1)).circle(V['insert_d'] / 2).extrude(4.7).val())
        sub['base'].append(cq.Workplane('XY', origin=(bx_, by_, -5)).circle(V['clear_d'] / 2).extrude(20).val())
        sub['base'].append(cq.Workplane('XY', origin=(bx_, by_, -g.FOOT_H - 0.01)).circle(2.2).extrude(2.0).val())
        sub['base'].append(cq.Workplane('XY', origin=(bx_, by_, -g.FOOT_H + 1.99)).circle(2.2)
                           .workplane(offset=1.1).circle(1.15).loft().val())
    for (mx, my) in MAGNETS:
        sub['base'].append(cq.Workplane('XY', origin=(mx, my, BASE_T - MAG_H)).circle(MAG_D / 2).extrude(MAG_H + 0.1).val())
    # ------------------------------------------------ assemble
    def finish(base_s, adds, subs, tag=''):
        """Booleans one at a time, each guarded: an op that makes the solid invalid or changes its volume
        implausibly is retried after .fix() and otherwise skipped (and logged)."""
        s = base_s
        v0 = vol(s)
        for kind, ops in (('fuse', adds), ('cut', subs)):
            for i, o in enumerate(ops):
                try:
                    vo = vol(o)
                    if vo < 1e-6:
                        continue
                    r = (s.fuse(o) if kind == 'fuse' else s.cut(o)).clean()
                    vr = vol(r)
                    tv = 0.004 * v0 + 1.0     # B-spline volumes are only good to ~0.1 %
                    ok = ((kind == 'fuse' and v0 - tv <= vr <= v0 + vo + tv) or
                          (kind == 'cut' and max(0.0, v0 - vo) - tv <= vr <= v0 + tv)) and vr > 1.0
                    if not ok:
                        r = (s.fuse(o.fix()) if kind == 'fuse' else s.cut(o.fix())).clean().fix()
                        vr = vol(r)
                        ok = vr > 1.0 and ((kind == 'fuse' and v0 - tv <= vr <= v0 + vo + tv) or
                                           (kind == 'cut' and max(0.0, v0 - vo) - tv <= vr <= v0 + tv))
                    if ok:
                        s, v0 = r, vr
                    else:
                        say(f'   !! {tag}: {kind} #{i} skipped (invalid result)')
                except Exception as e:
                    say(f'   !! {tag}: {kind} #{i} failed: {e!r}')
        return s
    t1 = time.time()
    say(f'  shell {vol(SHELL):.0f} mm3, base plate {vol(base):.0f} mm3')
    front = finish(OUTER.intersect(FRONT_HALF).cut(INNER), add['front'], sub['front'], 'front')
    back = finish(OUTER.intersect(BACK_HALF).cut(INNER), add['back'], sub['back'], 'back')
    base_plate = finish(base, add['base'], sub['base'], 'base')
    say(f'  shells assembled ({time.time()-t1:.0f}s); valid: front {front.isValid()} back {back.isValid()} '
        f'base {base_plate.isValid()}; volumes {vol(front):.0f} / {vol(back):.0f} / {vol(base_plate):.0f}')

    # ------------------------------------------------ CHASSIS (printed): plate + posts + rails + pockets + legs
    p0, p1 = PLATE_DD
    ch_add = [bf.cyl(44.0, p0, p1).fuse(bf.box(-BAT['W'] / 2 - 2.0, BAT['W'] / 2 + 2.0,
                                                BAT['by'] - BAT['L'] / 2 - 2.0, 0, p0, p1))]
    for (x, y) in MH:                                   # posts onto the 4 M2 pads (0.5 mm EVA dot)
        ch_add.append(bf.cyl(2.2, PCB_D + 0.5, p0 + 0.01, x, y))
    xr = BAT['W'] / 2 + 0.3
    y0b, y1b = BAT['by'] - BAT['L'] / 2 - 0.3, BAT['by'] + BAT['L'] / 2 + 0.3
    ch_add += [bf.box(xr, xr + 1.4, y0b - 1.4, y1b, p1, p1 + 4.5), bf.box(-xr - 1.4, -xr, y0b - 1.4, y1b, p1, p1 + 4.5),
               bf.box(-xr - 1.4, xr + 1.4, y0b - 1.4, y0b, p1, p1 + 4.5)]
    for D in (SPK, AMP, MIC):
        a_, b_ = D['a'] / 2 + 0.3, D['b'] / 2 + 0.3
        fr = bf.box(D['bx'] - a_ - 1.2, D['bx'] + a_ + 1.2, D['by'] - b_ - 1.2, D['by'] + b_ + 1.2, p1, p1 + 2.2)
        ch_add.append(fr.cut(bf.box(D['bx'] - a_, D['bx'] + a_, D['by'] - b_, D['by'] + b_, p0, p1 + 3)))
    ch_sub = []
    for si in screw_info:
        x, Z = si['x'], si['Z']
        ch_add.append(SeamFrame.cyl(x, Z, V['boss_d'] / 2, 0.1, si['s_leg1']))
        pleg = SeamFrame.pt(x, Z) + (si['s_leg1'] - 1.0) * SeamFrame.NS
        # web from the leg toward the plate centre, in the plate
        tgt = bf.w(0.0, float(np.dot(pleg - bf.O, g.UP)) * 0.8, (p0 + p1) / 2)
        webv = np.asarray(tgt) - pleg
        Lw = float(np.linalg.norm(webv))
        xd = np.cross(webv / Lw, [0, 0, 1.0])
        xd = xd / np.linalg.norm(xd) if np.linalg.norm(xd) > 1e-6 else np.array([1.0, 0, 0])
        plw = cq.Plane(origin=vec(pleg), xDir=vec(xd), normal=vec(webv / Lw))
        ch_add.append(cq.Workplane(plw).rect(3.0, 2.4).extrude(Lw).val())
        ch_sub.append(SeamFrame.cyl(x, Z, V['clear_d'] / 2, -1, si['s_leg1'] + 1))
    t1 = time.time()
    chassis = ch_add[0].fuse(*ch_add[1:]).clean().intersect(TONG_OUT)
    keep = [s for k, s in board.items() if k not in ('components',)]
    keep.append(board['components'].cut(fuse(*[bf.cyl(2.3, 0, 20, x, y) for x, y in MH])))
    chassis = chassis.cut(*(ch_sub + keep + [battery, speaker, amp, mic, usb_plug, grow(board['bat_plug'], 0.3), sock_body]
                            )).clean()
    # holes for wires: one window in the plate next to the BAT connector
    chassis = chassis.cut(bf.box(BATCONN[0] - 7, BATCONN[0] + 7, BATCONN[1] - 5, BATCONN[1] + 5, p0 - 1, p1 + 1)).clean()
    say(f'  chassis ({time.time()-t1:.0f}s), volume {vol(chassis):.0f} mm3, valid {chassis.isValid()}')

    shells = {'front_shell': front, 'back_shell': back, 'base_plate': base_plate, 'chassis': chassis}
    parts_in = dict(board)
    parts_in.update(battery=battery, speaker=speaker, amp=amp, mic=mic, usb_plug=usb_plug, usb_socket=sock_body)
    cdir = os.path.join(HERE, 'cache', 'm_' + vname)
    os.makedirs(cdir, exist_ok=True)
    for k, v in list(shells.items()) + list(parts_in.items()):
        v.exportBrep(os.path.join(cdir, k + '.brep'))
    json.dump(dict(screws=screw_info, pins={k: dict(L=v['L'], exit=v['exit'], s_exit=v['s_exit']) for k, v in pins.items()}),
              open(os.path.join(cdir, 'info.json'), 'w'), indent=1)
    return finish_parts(vname, shells, parts_in, pins, screw_info, bf, log, say, t0)


def finish_parts(vname, shells, parts_in, pins, screw_info, bf, log, say, t0):
    V = VARIANTS[vname]
    try:
        inter, clear = mesh_checks(shells, parts_in, say)
    except Exception as e:
        import traceback
        traceback.print_exc()
        say('  !! mesh checks failed: %r' % e)
        inter, clear = {}, {}
    bb = shells['front_shell'].fuse(shells['back_shell']).BoundingBox()
    dims = dict(W=round(bb.xlen, 2), H_shells=round(bb.zmax, 2), H_total=round(bb.zmax + g.FOOT_H, 2),
                D=round(bb.ylen, 2), base=g.dims_report(), mass_g={})
    dens = 1.24 if vname == 'plastic' else 2.70
    for n_, s_ in shells.items():
        dims['mass_g'][n_] = round(vol(s_) * (dens if n_ in ('front_shell', 'back_shell') else 1.24) / 1000.0, 1)
    say(f'  size {dims["W"]} x {dims["H_total"]} (incl. foot) x {dims["D"]} mm; masses {dims["mass_g"]}')
    parts = dict(shells)
    for k, pd in pins.items():
        parts[f'pin_{k}'] = pd['solid']
    ctx = dict(bf=bf, board={k: v for k, v in parts_in.items()}, pins=pins, screws=screw_info, inter=inter,
               clear=clear, dims=dims, log=log, V=V)
    files = export_all(vname, parts, ctx)
    rep = dict(screws=screw_info, interference=inter, clearance=clear, dims=dims,
               pins={k: dict(L=v['L'], exit=v['exit'], s_exit=v['s_exit']) for k, v in pins.items()},
               log=log, files=[os.path.relpath(f, OUT) for f in files])
    with open(os.path.join(OUT, 'cad', f'report_m_{vname}.json'), 'w') as f:
        json.dump(rep, f, indent=1, default=float)
    say(f'  built + exported in {time.time()-t0:.0f}s')
    return parts, ctx


def mesh_checks(shells, parts_in, say):
    import trimesh
    say('  -- checks on meshes --')
    M = {k: to_mesh(v, 0.05) for k, v in shells.items()}
    say('   watertight: ' + ', '.join('%s %s' % (k, m.is_volume) for k, m in M.items()))
    P = {k: to_mesh(v, 0.03) for k, v in parts_in.items()}
    inter, clear = {}, {}
    env = ('components', 'pcb', 'lcd')          # envelopes the chassis posts reach through on purpose
    for sn, sm in M.items():
        for pn, pm in P.items():
            if sn == 'chassis' and pn in env:
                continue
            inter[f'{sn} x {pn}'] = round(inter_vol(sm, pm, shells[sn], parts_in[pn]), 3)
    names = list(M)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            inter[f'{names[i]} x {names[j]}'] = round(inter_vol(M[names[i]], M[names[j]], shells[names[i]],
                                                                shells[names[j]]), 3)
    inside = ['battery', 'speaker', 'amp', 'mic', 'usb_plug', 'usb_socket']
    for i in range(len(inside)):
        for j in range(i + 1, len(inside)):
            a_, b_ = inside[i], inside[j]
            inter[f'{a_} x {b_}'] = round(inter_vol(P[a_], P[b_], parts_in[a_], parts_in[b_]), 3)
        for bn in ('components', 'bat_plug', 'lcd', 'pcb'):
            inter[f'{inside[i]} x {bn}'] = round(inter_vol(P[inside[i]], P[bn], parts_in[inside[i]], parts_in[bn]), 3)
    bad = {k: v for k, v in inter.items() if abs(v) > 0.05}
    say(f'   interference: {len(inter)} pairs checked, {len(bad)} with overlap > 0.05 mm3 {bad if bad else ""}')
    say('   minimum clearance of each internal part to each printed/machined part (mm, <0 = overlap):')
    for pn in parts_in:
        pts, _ = trimesh.sample.sample_surface_even(P[pn], 1500)
        row = {}
        for sn, sm in M.items():
            d = trimesh.proximity.signed_distance(sm, pts[:1500])
            row[sn] = round(float(-d.max()), 2)
        clear[pn] = row
        say('    %-15s ' % pn + '  '.join('%s %6.2f' % (k[:6], v) for k, v in row.items()))
    return inter, clear


# ============================================================================ print pose + export
def print_pose(name, s, ctx, vname):
    NS = SeamFrame.NS
    if name == 'front_shell':
        s = align(s, NS, (0, 0, -1))            # seam down, face up (no supports on the visible face)
    elif name == 'back_shell':
        s = align(s, -NS, (0, 0, -1))           # seam down, dome up
    elif name == 'base_plate':
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180)   # flat inside face down, foot up
    elif name == 'chassis':
        s = align(s, g.INW, (0, 0, -1))         # plate on the bed
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-bb.center.x, -bb.center.y, -bb.zmin))


def gz(path):
    with open(path, 'rb') as fi, gzip.open(path + '.gz', 'wb', compresslevel=9) as fo:
        shutil.copyfileobj(fi, fo)


def export_all(vname, parts, ctx):
    for d in ('stl/' + vname, 'step/' + vname, 'stl/assembly'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    files = []
    for name, s in parts.items():
        posed = s if name.startswith('pin_') else print_pose(name, s, ctx, vname)
        stl = os.path.join(OUT, 'stl', vname, f'soul_m_{vname}_{name}.stl')
        cq.exporters.export(cq.Workplane().add(posed), stl, tolerance=0.02, angularTolerance=0.15)
        files.append(stl)
        stp = os.path.join(OUT, 'step', vname, f'soul_m_{vname}_{name}.step')
        cq.exporters.export(cq.Workplane().add(posed), stp)
        gz(stp)
        files += [stp, stp + '.gz']
        if name.startswith('pin_'):
            s = place_pin(s, ctx['pins'][name[4:]]['frame'])
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, 'stl', 'assembly', f'm_{vname}_{name}.stl'),
                            tolerance=0.03, angularTolerance=0.2)
    for name, s in ctx['board'].items():
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, 'stl', 'assembly', f'm_{vname}_in_{name}.stl'),
                            tolerance=0.05)
    asm = cq.Assembly()
    for name, s in parts.items():
        if not name.startswith('pin_'):
            asm.add(s, name=name)
    for n_, s_ in ctx['board'].items():
        asm.add(s_, name='dummy_' + n_, color=cq.Color(0.1, 0.1, 0.12))
    ap = os.path.join(OUT, 'step', f'soul_m_{vname}_ASSEMBLY_with_board.step')
    asm.save(ap)
    gz(ap)
    files += [ap, ap + '.gz']
    return files


def from_cache(vname):
    log = []

    def say(*a):
        s = ' '.join(str(x) for x in a)
        print(s, flush=True)
        log.append(s)
    t0 = time.time()
    V = VARIANTS[vname]
    cdir = os.path.join(HERE, 'cache', 'm_' + vname)
    ld = lambda n: cq.Shape.importBrep(os.path.join(cdir, n + '.brep'))  # noqa: E731
    info = json.load(open(os.path.join(cdir, 'info.json')))
    shells = {n: ld(n) for n in ('front_shell', 'back_shell', 'base_plate', 'chassis')}
    names = [f[:-5] for f in os.listdir(cdir) if f.endswith('.brep') and f[:-5] not in shells]
    parts_in = {n: ld(n) for n in names}
    bf = BoardFrame(V['lip_t'] - 0.15)
    pins = {}
    for k, (kx, ky_) in KEYS.items():
        w_act = bf.w(kx + 2.0, ky_, KEY_DD)
        pl = cq.Plane(origin=vec(w_act), xDir=(0, 1, 0), normal=(1, 0, 0))
        d = info['pins'][k]
        pin = (cq.Workplane('XY').circle(V['pin_d'] / 2).extrude(d['L']).faces('<Z').workplane().circle(1.6)
               .extrude(0.8).val())
        pins[k] = dict(solid=pin, L=d['L'], exit=d['exit'], s_exit=d['s_exit'], frame=pl)
    say(f'== {vname} (from cache)')
    return finish_parts(vname, shells, parts_in, pins, info['screws'], bf, log, say, t0)


def main():
    a = sys.argv[1:]
    if a and a[0] == 'finish':
        for vn in a[1:]:
            from_cache(vn)
        return
    for vn in (a or ['plastic', 'alu']):
        build(vn)
    print('done')


if __name__ == '__main__':
    main()
