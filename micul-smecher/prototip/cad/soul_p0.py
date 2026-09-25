#!/usr/bin/env python3
"""soul_p0.py -- SOUL-P0, the DIY pilot enclosure of SOUL for the stock Waveshare ESP32-S3-Touch-AMOLED-1.75.

CadQuery 2.x. Builds, checks and exports every part in two material variants:

  PLASTIC  (FDM / SLA): 2.0 mm walls, 0.2 mm fit clearances, 1.2 mm glass lip, M2 heat-set inserts in the front shell
  ALU      (CNC 6061-T6): 1.4 mm walls, 0.1 mm clearances, 0.8 mm lip, M2 tapped holes in the front bosses,
           3-axis machinable halves split on a plane (no undercuts); option ALU_BAND = the same halves shortened
           by 1.5 mm each side of the seam + a 3 mm printed plastic band (RF window for Wi-Fi/BLE).

Parts: front_shell, back_shell, chassis (always printed), pin_pwr, pin_boot, [seam_band].
The base is flat and part of both shells (no separate base plate, no rocker).

Usage:
    python3 soul_p0.py                  # all variants -> ../stl, ../step, ../img/check_*.png, ../CHECKS.txt
    python3 soul_p0.py plastic          # one variant (plastic | alu | alu_band)

Frame (mm): origin = centre of the flat base, +Z up, the face looks toward -Y, +X = viewer's right.
Board frame: (bx, by) in the glass plane (by up, USB-C at by < 0), dd = depth behind the glass front.
Board numbers come from the Waveshare STEP via ../../cad/micul_smecher.scad (marked there as verified);
the ones marked UNVERIFIED must be measured with calipers before the final print.
"""
import json
import math
import os
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
                    cb_d=4.3, cb_depth=1.8, pin_hole=2.3, pin_d=1.9, band=0.0, chamfer=0.5, fillet_in=0.0),
    'alu': dict(wall=1.4, tol=0.1, lip_t=0.8, lip_over=1.5, tongue_t=0.8, tongue_h=1.2,
                boss_d=5.0, hole='tap', insert_d=1.6, insert_depth=4.5, clear_d=2.2,
                cb_d=4.2, cb_depth=1.7, pin_hole=2.1, pin_d=1.8, band=0.0, chamfer=0.3, fillet_in=1.0),
    'alu_band': dict(wall=1.4, tol=0.1, lip_t=0.8, lip_over=1.5, tongue_t=0.8, tongue_h=1.2,
                     boss_d=5.0, hole='tap', insert_d=1.6, insert_depth=4.5, clear_d=2.2,
                     cb_d=4.2, cb_depth=1.7, pin_hole=2.1, pin_d=1.8, band=3.0, chamfer=0.3, fillet_in=1.0),
}

# ============================================================================ board (Waveshare 1.75, verified STEP)
GLASS_R, GLASS_T, GLASS_FLAT_R, GLASS_CD = 24.48, 1.10, 22.08, 0.50
VIEW_R = 21.88                       # active area Ø43.76
MOD_R = 23.0                         # module + PCB Ø46.0
PCB_D = (5.70, 6.90)                 # PCB front / back depth behind the glass front
COMP_D = 8.70                        # back-side components under the battery footprint (8.9 incl. 0.2 air)
SO_POS = [(14.70, 13.75), (14.70, -13.75), (-20.50, 0.0)]   # M2 standoffs, tip at dd 10.43
SO_DEPTH = 10.43
USB_FACE_R, USB_DD = 23.80, 8.55     # USB-C receptacle face radius / tongue-centre depth
USB_PLUG_W, USB_PLUG_H = 12.4, 7.0   # cable overmold -- UNVERIFIED, measure your cable
HEADER = (17.48, 19.88, -10.43, 10.43, PCB_D[1], 12.70)     # 8-pin header box (bx0, bx1, by0, by1, dd0, dd1)
CONNS = [(-20.12, -15.92, 2.67, 10.32), (-20.12, -15.92, -10.63, -2.98)]   # SPK / BAT MX1.25, dd 6.9 .. 11.7
CONN_DD, PLUG_DD = 11.70, 14.0       # connector top / mated plug + wires keep-out (UNVERIFIED)
BTNS = {'pwr': ((-11.31, 17.20), 123.3, 7.60), 'boot': ((11.31, 17.10), 56.5, 7.60)}   # origin, dir deg, depth

# ============================================================================ stock parts inside
# LiPo 503035 (5.0 x 30 x 35, ~500 mAh, PCM + MX1.25 lead): envelope incl. PCM tape and 0.3 swell
BAT = dict(name='LiPo 503035', W=30.5, L=36.5, T=5.3, bx=0.3, top=(6.0, 9.1), tilt_to=(-30.1, 14.4))
# micro speaker 1511 (15 x 11 x 3.5 mm, 8 ohm 1 W, wires) lying on the PCB back, membrane facing the back shell
SPK = dict(name='speaker 1511', a=15.0, b=11.0, t=3.6, bx=3.0, by=13.0, dd=9.3)
# screws: M2 from the back.  lower pair clamps the chassis legs, upper pair goes straight into the front
SCREWS_LOW = [(-19.5, 11.0), (19.5, 11.0)]      # (x, Z) on the parting plane
SCREWS_UP = [(-23.0, 57.0), (23.0, 57.0)]
SLOT = dict(z0=45.5, z1=57.5, w=1.2)             # speaker slot in the +x seam
MAGNETS = [(-10.5, 2.5), (10.5, 2.5)]            # (x, y) of Ø6x2 magnet recesses in the base (optional)
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
    Zs = np.concatenate([[0.0, 0.4, 1.0, 1.8, 2.8, 4.0, 5.5, 7.5], np.linspace(10, 60, 21),
                         [62, 64, 66, 68, 69.5, 71, 72, 73, 73.8, 74.4, 74.8, 74.97]])
    return loft([(Z, g.ring_pts(Z, N_RING)) for Z in Zs])


def eroded_solid(t):
    """Inner solid = outer body eroded by a ball of radius t (sampled slices -> loft)."""
    rings = []
    Zs = list(np.concatenate([[t, t + 0.3, t + 0.8, t + 1.6, t + 2.6, t + 4.0, t + 6.0], np.linspace(t + 8.5, 68, 26),
                              np.arange(68.8, 76, 0.7)]))
    for Z in Zs:
        p = g.eroded_poly(Z, t)
        if p.is_empty or p.area < 30.0:
            break
        rings.append((Z, g.poly_ring(p, 72)))
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


# ============================================================================ build one variant
def build(vname):
    V = VARIANTS[vname]
    t0 = time.time()
    log = []

    def say(*a):
        s = ' '.join(str(x) for x in a)
        print(s, flush=True)
        log.append(s)

    wall, tol = V['wall'], V['tol']
    dg = V['lip_t'] - 0.15            # glass flat front: its chamfer touches the lip underside at the aperture
    bf = BoardFrame(dg)
    say(f'== {vname}: wall {wall} tol {tol} lip {V["lip_t"]}')

    OUTER = outer_solid()
    INNER = eroded_solid(wall)
    say(f'  outer vol {vol(OUTER):.0f} mm3, inner {vol(INNER):.0f} mm3  ({time.time()-t0:.1f}s)')
    SHELL = hollow(OUTER, INNER)
    TONG_OUT = eroded_solid(wall + tol)
    TONG_IN = eroded_solid(wall + tol + V['tongue_t'])

    # ------------------------------------------------ board keep-outs (for cuts and checks)
    board = {
        'glass': (cq.Workplane(bf.plane).workplane(offset=-GLASS_T).circle(GLASS_R).extrude(GLASS_T - GLASS_CD)
                  .faces('>Z').workplane().circle(GLASS_R).workplane(offset=GLASS_CD).circle(GLASS_FLAT_R)
                  .loft().val()).fuse(bf.cyl(GLASS_R, GLASS_CD, GLASS_T)).clean(),
        'module': bf.cyl(MOD_R, GLASS_T, PCB_D[1]),
        'components': bf.cyl(22.0, PCB_D[1], COMP_D),
        'usb_receptacle': bf.box(-4.47, 4.47, -USB_FACE_R, -16.3, USB_DD - 1.63, USB_DD + 1.63),
        'header_8pin': bf.box(*HEADER),
    }
    for i, (x, y) in enumerate(SO_POS):
        board[f'standoff_{i+1}'] = bf.cyl(1.75, PCB_D[1], SO_DEPTH, x, y)
    for i, (x0, x1, y0, y1) in enumerate(CONNS):
        board[['conn_spk', 'conn_bat'][i]] = bf.box(x0, x1, y0, y1, PCB_D[1], CONN_DD)
        board[['plug_spk', 'plug_bat'][i]] = bf.box(x0 - 0.8, x1 + 0.8, y0 - 0.3, y1 + 0.3, CONN_DD, PLUG_DD)
    for k, ((ox, oy), ang, dd) in BTNS.items():
        a = math.radians(ang)
        c = np.array([ox, oy]) + 0.5 * np.array([math.cos(a), math.sin(a)])
        board[f'btn_{k}'] = bf.box(c[0] - 2.0, c[0] + 2.0, c[1] - 2.0, c[1] + 2.0, dd - 1.0, dd + 1.0)
    usb_plug = bf.slot(USB_PLUG_W, USB_PLUG_H, -USB_FACE_R - 40.0, -USB_FACE_R, USB_DD)

    a, nrm, top_f, bot_f = bat_geometry(bf)
    battery = tilted_box(bf, BAT['bx'] - BAT['W'] / 2, BAT['bx'] + BAT['W'] / 2, bot_f, a, nrm, BAT['L'], BAT['T'])
    speaker = bf.box(SPK['bx'] - SPK['a'] / 2, SPK['bx'] + SPK['a'] / 2, SPK['by'] - SPK['b'] / 2,
                     SPK['by'] + SPK['b'] / 2, SPK['dd'], SPK['dd'] + SPK['t'])

    # ------------------------------------------------ halves (additions and cuts are collected, then applied once)
    BIG = 200.0
    band = V['band']
    FRONT_HALF = SeamFrame.slab(-BIG, -band / 2)
    BACK_HALF = SeamFrame.slab(band / 2, BIG)
    BAND_SLAB = SeamFrame.slab(-band / 2, band / 2) if band > 0 else None
    add = {'front': [], 'back': [], 'band': []}
    sub = {'front': [], 'back': [], 'band': []}

    def to_all(solid):
        for k in sub:
            sub[k].append(solid)

    # alignment tongue: inside the back half's inner wall, tol clearance (in band mode it belongs to the band)
    tongue = hollow(TONG_OUT, TONG_IN).intersect(SeamFrame.slab(-band / 2 - 0.01, band / 2 + V['tongue_h']))
    add['band' if band > 0 else 'front'].append(tongue)

    # ------------------------------------------------ screw bosses
    say('  screw columns (x, Z): front wall -> back outer, along the seam normal')
    screw_info = []
    for (x, Z), kind in [(p, 'low') for p in SCREWS_LOW] + [(p, 'up') for p in SCREWS_UP]:
        p = SeamFrame.pt(x, Z)
        s_front = -ray_exit(p, -SeamFrame.NS)       # outer front surface (negative s)
        s_back = ray_exit(p, SeamFrame.NS)          # outer back surface
        r = V['boss_d'] / 2
        s_fb_top = -band / 2
        if kind == 'low':
            s_leg1 = round(min(s_back - wall - 2.5, 6.5), 2)   # chassis leg: seam .. s_leg1
            s_bb0 = s_leg1 + 0.15
        else:
            s_leg1 = None
            s_bb0 = band / 2
        add['front'].append(SeamFrame.cyl(x, Z, r, s_front - 1.0, s_fb_top).intersect(OUTER))
        add['back'].append(SeamFrame.cyl(x, Z, r, s_bb0, s_back + 1.0).intersect(OUTER).intersect(BACK_HALF))
        if band > 0 and kind == 'up':
            add['band'].append(SeamFrame.cyl(x, Z, r, -band / 2, band / 2).intersect(OUTER))
        depth = min(V['insert_depth'], (s_fb_top - s_front) - 1.6)
        sub['front'].append(SeamFrame.cyl(x, Z, V['insert_d'] / 2, s_fb_top - depth, s_fb_top + 0.1))
        through = SeamFrame.cyl(x, Z, V['clear_d'] / 2, -band / 2 - 0.2, s_back + 2)
        sub['back'].append(through)
        sub['band'].append(through)
        sub['back'].append(SeamFrame.cyl(x, Z, V['cb_d'] / 2, s_back - V['cb_depth'], s_back + 5))
        skin = (s_fb_top - depth) - s_front
        L_need = (s_back - V['cb_depth']) - (s_fb_top - depth + 0.5)     # longest screw that still clears the hole bottom
        screw_info.append(dict(kind=kind, x=x, Z=Z, s_front=round(s_front, 2), s_back=round(s_back, 2),
                               hole_depth=round(depth, 2), skin_under_hole=round(skin, 2), s_leg1=s_leg1,
                               screw_len_max=round(L_need, 2)))
        say(f'   {kind:3s} ({x:+.1f},{Z:.1f}): front {s_front:.2f} back {s_back:.2f} hole {depth:.1f} deep, '
            f'skin under hole {skin:.2f} -> screw <= {L_need:.1f} mm')

    # ------------------------------------------------ glass pocket, aperture, frame chamfer
    r_ap = GLASS_R - V['lip_over']
    # lip underside = table depth lip_t = board dd (lip_t - dg) = 0.15
    pocket = bf.cyl(GLASS_R + tol, V['lip_t'] - dg, GLASS_T + 0.6).fuse(
        bf.cyl(MOD_R + tol + 0.15, GLASS_T + 0.3, PCB_D[1] + 0.8))
    to_all(pocket)
    sub['front'].append(bf.cyl(r_ap, -dg - 3.0, 1.0))
    ch = V['chamfer']
    cone = (cq.Workplane(bf.plane).workplane(offset=dg - ch)
            .circle(r_ap).workplane(offset=ch + 0.01).circle(r_ap + ch + 0.01).loft().val())
    sub['front'].append(cone)

    # ------------------------------------------------ USB-C: plug tunnel + guide sleeve + base cable groove
    sleeve = bf.slot(USB_PLUG_W + 2 * tol + 2.4, USB_PLUG_H + 2 * tol + 2.4, -USB_FACE_R - 40, -USB_FACE_R - 0.6, USB_DD)
    sleeve = sleeve.intersect(OUTER)
    add['front'].append(sleeve.intersect(FRONT_HALF))
    add['back'].append(sleeve.intersect(BACK_HALF))
    if band > 0:
        add['band'].append(sleeve.intersect(BAND_SLAB))
    tunnel = bf.slot(USB_PLUG_W + 2 * tol + 0.2, USB_PLUG_H + 2 * tol + 0.2, -USB_FACE_R - 40, -USB_FACE_R + 3.0, USB_DD)
    pa = bf.w(0, -USB_FACE_R, USB_DD)
    y_t = float(pa[1] - g.UP[1] * pa[2] / g.UP[2])          # tunnel axis at Z = 0
    groove = (cq.Workplane('XY').center(0, (y_t + 20.0) / 2).rect(5.0, 20.0 - y_t)
              .extrude(4.5).translate((0, 0, -0.01)).val())
    to_all(tunnel)
    to_all(groove)

    # ------------------------------------------------ speaker slot in the +x seam
    zs = np.linspace(SLOT['z0'], SLOT['z1'], 7)
    w_, *_ = g.sections(zs)
    L = SLOT['z1'] - SLOT['z0']
    pc = SeamFrame.pt(float(w_.min()) - 7.0, (SLOT['z0'] + SLOT['z1']) / 2)
    pl = cq.Plane(origin=vec(pc), xDir=vec(SeamFrame.US), normal=(1, 0, 0))
    to_all(cq.Workplane(pl).slot2D(L, SLOT['w'], 0).extrude(12.0).val())

    # ------------------------------------------------ button pins: radial holes + guide sleeves
    pins = {}
    for k, ((ox, oy), ang, dd) in BTNS.items():
        a_ = math.radians(ang)
        d2 = np.array([math.cos(a_), math.sin(a_)])
        p_act = np.array([ox, oy]) + 1.6 * d2              # actuator tip (switch body ~3.2 mm) -- UNVERIFIED
        w_act = bf.w(p_act[0], p_act[1], dd)
        dwrld = d2[0] * np.array([1.0, 0, 0]) + d2[1] * g.UP
        t_exit = ray_exit(w_act, dwrld)
        s_exit = SeamFrame.s(w_act + t_exit * dwrld)
        side = 'back' if s_exit > band / 2 + 0.3 else 'front'
        pl = cq.Plane(origin=vec(w_act), xDir=vec(np.cross(dwrld, g.INW)), normal=vec(dwrld))
        g0 = max(t_exit - wall - 4.5, 2.5)
        guide = cq.Workplane(pl).workplane(offset=g0).circle(V['pin_hole'] / 2 + 1.2).extrude(6.0).val().intersect(OUTER)
        add[side].append(guide.intersect(BACK_HALF if side == 'back' else FRONT_HALF))
        sub[side].append(cq.Workplane(pl).workplane(offset=0.2).circle(V['pin_hole'] / 2).extrude(t_exit + 2).val())
        L_pin = t_exit - 0.2 - 0.3
        pin = (cq.Workplane('XY').circle(V['pin_d'] / 2).extrude(L_pin)
               .faces('<Z').workplane().circle(1.6).extrude(0.8).val())
        pins[k] = dict(solid=pin, L=round(L_pin, 2), s_exit=round(s_exit, 2), shell=side,
                       exit=[round(float(v), 2) for v in (w_act + t_exit * dwrld)], frame=pl, t_exit=t_exit, g0=g0)
        say(f'  pin {k}: length {L_pin:.1f} mm, exits at {pins[k]["exit"]} (s = {s_exit:+.2f} -> {side} shell)')

    # ------------------------------------------------ magnets in the base (optional, Ø6x2, glue in)
    for (mx, my) in MAGNETS:
        side = 'back' if SeamFrame.s((mx, my, 1.0)) > band / 2 else 'front'
        add[side].append(cq.Workplane('XY').center(mx, my).circle(MAG_D / 2 + 1.6).extrude(MAG_H + 1.2).val()
                         .intersect(OUTER))
        sub[side].append(cq.Workplane('XY').center(mx, my).circle(MAG_D / 2).extrude(MAG_H).translate((0, 0, -0.01)).val())

    # ------------------------------------------------ assemble the shells (one fuse + one cut per part)
    def finish(base, adds, subs):
        s = base
        if adds:
            s = s.fuse(*adds).clean()
        if subs:
            s = s.cut(*subs).clean()
        return s
    t1 = time.time()
    front = finish(SHELL.intersect(FRONT_HALF), add['front'], sub['front'])
    back = finish(SHELL.intersect(BACK_HALF), add['back'], sub['back'])
    seam_band = finish(SHELL.intersect(BAND_SLAB), add['band'], sub['band']) if band > 0 else None
    say(f'  shells assembled ({time.time()-t1:.0f}s); valid: front {front.isValid()} back {back.isValid()}'
        + ('' if seam_band is None else f' band {seam_band.isValid()}') + f'; volumes {vol(front):.0f} / {vol(back):.0f}')

    # ------------------------------------------------ CHASSIS (printed, both variants)
    a, nrm, top_f, bot_f = bat_geometry(bf)
    rail_t = 1.3
    lipw = 1.2
    Lr = BAT['L'] + 1.5
    pb = bot_f - a * 1.5                          # starts 1.5 below the battery bottom (bottom stop)
    bat_x0, bat_x1 = BAT['bx'] - BAT['W'] / 2, BAT['bx'] + BAT['W'] / 2
    Tr = BAT['T'] + 0.9 - 0.3
    L_low = abs((-11.8 - pb[0]) / a[0])           # -x rail stops below the SPK/BAT connectors
    ch_add = [
        tilted_box(bf, bat_x1 + 0.35, bat_x1 + 0.35 + rail_t, pb - nrm * 0.9, a, nrm, Lr, Tr),
        tilted_box(bf, bat_x0 - 0.35 - rail_t, bat_x0 - 0.35, pb - nrm * 0.9, a, nrm, L_low, Tr),
        tilted_box(bf, bat_x1 - lipw, bat_x1 + 0.35, pb - nrm * 0.9, a, nrm, Lr, 0.8),
        tilted_box(bf, bat_x0 - 0.35, bat_x0 + lipw, pb - nrm * 0.9, a, nrm, L_low, 0.8),
        tilted_box(bf, bat_x0 - 0.35 - rail_t, bat_x1 + 0.35 + rail_t, pb - nrm * 0.9, a, nrm, 1.5 - 0.35, Tr),
    ]
    sx0, sx1 = SPK['bx'] - SPK['a'] / 2 - 0.25, SPK['bx'] + SPK['a'] / 2 + 0.25
    sy0, sy1 = SPK['by'] - SPK['b'] / 2 - 0.25, SPK['by'] + SPK['b'] / 2 + 0.25
    d0, d1 = SPK['dd'] + 0.4, SPK['dd'] + SPK['t'] - 0.3
    so1 = SO_POS[0]
    ch_add += [
        bf.box(sx0 - 1.0, sx1 + 1.0, sy0 - 1.0, sy1 + 1.0, d0, d1).cut(bf.box(sx0, sx1, sy0, sy1, d0 - 1, d1 + 1)),
        bf.box(sx1, bat_x1 + 0.35 + rail_t, sy0 - 1.0, sy0 + 1.2, d0, d1),        # bridge speaker frame -> +x rail
        bf.box(sx1, so1[0] + 1.8, so1[1] - 1.8, so1[1] + 1.8, SO_DEPTH + 1.8, d1),  # arm to standoff 1
        bf.cyl(1.6, SO_DEPTH + 0.5, d1, so1[0], so1[1]),                            # post (0.5 mm EVA dot)
    ]
    ch_sub = []
    for si in [s for s in screw_info if s['kind'] == 'low']:
        x, Z = si['x'], si['Z']
        ch_add.append(SeamFrame.cyl(x, Z, V['boss_d'] / 2, band / 2 + 0.1, si['s_leg1']))
        pleg = SeamFrame.pt(x, Z) + (si['s_leg1'] - 1.2) * SeamFrame.NS
        web_to = bf.w(math.copysign(BAT['W'] / 2 + 0.35 + rail_t / 2, x), pb[0] + 0.8, pb[1] + BAT['T'] * 0.5)
        webv = np.asarray(web_to) - pleg
        Lw = float(np.linalg.norm(webv))
        xd = np.cross(webv / Lw, [0, 0, 1])
        plw = cq.Plane(origin=vec(pleg), xDir=vec(xd / np.linalg.norm(xd)), normal=vec(webv / Lw))
        ch_add.append(cq.Workplane(plw).rect(2.6, 2.6).extrude(Lw).val())
        ch_sub.append(SeamFrame.cyl(x, Z, V['clear_d'] / 2, band / 2 - 1, si['s_leg1'] + 1))
    t1 = time.time()
    chassis = ch_add[0].fuse(*ch_add[1:]).clean()
    chassis = chassis.intersect(TONG_OUT)
    keep_out = [s for k, s in board.items() if not k.startswith('standoff')]
    keep_out.append(bf.box(-40, 40, -40, 40, -5, COMP_D + 0.3))
    chassis = chassis.cut(*(ch_sub + keep_out + [battery, speaker, usb_plug])).clean()
    say(f'  chassis ({time.time()-t1:.0f}s), volume {vol(chassis):.0f} mm3, valid {chassis.isValid()}')

    shells = {'front_shell': front, 'back_shell': back, 'chassis': chassis}
    if seam_band is not None:
        shells['seam_band'] = seam_band
    parts_in = dict(board)
    parts_in['battery'] = battery
    parts_in['speaker'] = speaker
    parts_in['usb_plug'] = usb_plug
    cdir = os.path.join(HERE, 'cache', vname)
    os.makedirs(cdir, exist_ok=True)
    for k, v in list(shells.items()) + list(parts_in.items()):
        v.exportBrep(os.path.join(cdir, k + '.brep'))
    try:
        inter, clear = mesh_checks(shells, parts_in, say)
    except Exception as e:
        import traceback
        traceback.print_exc()
        say('  !! mesh checks failed: %r' % e)
        inter, clear = {}, {}

    # ------------------------------------------------ dimensions / masses
    bb = OUTER.BoundingBox()
    dims = dict(W=round(bb.xlen, 2), H=round(bb.zlen, 2), D=round(bb.ylen, 2), base=g.dims_report(), mass_g={})
    dens = {'plastic': 1.24, 'alu': 2.70, 'alu_band': 2.70}[vname]
    for n_, s_ in shells.items():
        d_ = 1.24 if n_ in ('chassis', 'seam_band') else dens
        dims['mass_g'][n_] = round(vol(s_) * d_ / 1000.0, 1)
    say(f'  size {dims["W"]} x {dims["H"]} x {dims["D"]} mm; masses (PLA 1.24 / Al 2.70 g/cm3) {dims["mass_g"]}')

    parts = dict(front_shell=front, back_shell=back, chassis=chassis)
    if seam_band is not None:
        parts['seam_band'] = seam_band
    for k, pd in pins.items():
        parts[f'pin_{k}'] = pd['solid']
    ctx = dict(bf=bf, board=board, battery=battery, speaker=speaker, usb_plug=usb_plug, pins=pins,
               screws=screw_info, inter=inter, clear=clear, dims=dims, log=log, V=V)
    say(f'  built in {time.time()-t0:.0f}s')
    return parts, ctx


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


def mesh_checks(shells, parts_in, say):
    """Interference = volume of the mesh intersection (manifold3d); clearance = min distance from surface samples
    of each internal part to each shell (negative = inside)."""
    import trimesh
    say('  -- checks on meshes (tessellation 0.03 mm) --')
    M = {k: to_mesh(v) for k, v in shells.items()}
    say('   watertight: ' + ', '.join('%s %s' % (k, m.is_volume) for k, m in M.items()))
    P = {k: to_mesh(v, 0.02) for k, v in parts_in.items()}
    inter, clear = {}, {}
    for sn, sm in M.items():
        for pn, pm in P.items():
            inter[f'{sn} x {pn}'] = round(inter_vol(sm, pm, shells[sn], parts_in[pn]), 3)
    for a_, b_ in [('front_shell', 'back_shell'), ('front_shell', 'chassis'), ('back_shell', 'chassis')] + \
            ([('seam_band', 'front_shell'), ('seam_band', 'back_shell'), ('seam_band', 'chassis')] if 'seam_band' in M else []):
        inter[f'{a_} x {b_}'] = round(inter_vol(M[a_], M[b_], shells[a_], shells[b_]), 3)
    for a_, b_ in [('battery', 'speaker'), ('battery', 'components'), ('speaker', 'components'),
                   ('battery', 'usb_receptacle'), ('battery', 'plug_bat'), ('speaker', 'btn_boot')]:
        inter[f'{a_} x {b_}'] = round(inter_vol(P[a_], P[b_], parts_in[a_], parts_in[b_]), 3)
    bad = {k: v for k, v in inter.items() if abs(v) > 0.01}
    say(f'   interference: {len(inter)} pairs checked, {len(bad)} with overlap > 0.01 mm3 {bad if bad else ""}')
    # clearances
    say('   minimum clearance of each internal part to each printed/machined part (mm):')
    for pn in ['glass', 'module', 'components', 'header_8pin', 'plug_spk', 'plug_bat', 'usb_receptacle', 'usb_plug',
               'btn_pwr', 'btn_boot', 'standoff_1', 'standoff_2', 'standoff_3', 'battery', 'speaker']:
        pts, _ = trimesh.sample.sample_surface_even(P[pn], 6000)
        pts = np.vstack([pts, P[pn].vertices])
        row = {}
        for sn, sm in M.items():
            d = trimesh.proximity.signed_distance(sm, pts)       # >0 inside the shell mesh
            row[sn] = round(float(-d.max()), 2)
        clear[pn] = row
        say('    %-15s ' % pn + '  '.join('%s %5.2f' % (k[:5], v) for k, v in row.items()))
    return inter, clear


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


# ============================================================================ print / machining orientation + export
def print_pose(name, s, ctx, vname):
    """Rotate a part into its print/fixture pose (lowest face on the bed at Z = 0)."""
    NS = SeamFrame.NS
    if name in ('front_shell',):
        # face down on the bed: rotate so the outward normal of the table points to -Z
        s = align(s, g.N_OUT, (0, 0, -1))
    elif name in ('back_shell', 'seam_band'):
        # open side down: the seam plane on the bed (back dome up)
        s = align(s, -NS, (0, 0, -1))
    elif name == 'chassis':
        # battery-back side down
        a, nrm, *_ = bat_geometry(ctx['bf'])
        zdir = nrm[0] * g.UP + nrm[1] * g.INW
        s = align(s, zdir, (0, 0, -1))
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-bb.center.x, -bb.center.y, -bb.zmin))


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


def export_all(vname, parts, ctx):
    os.makedirs(os.path.join(OUT, 'stl', vname), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'step', vname), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'stl', 'assembly'), exist_ok=True)
    files = []
    for name, s in parts.items():
        if name.startswith('pin_'):
            posed = s
        else:
            posed = print_pose(name, s, ctx, vname)
        stl = os.path.join(OUT, 'stl', vname, f'soul_p0_{vname}_{name}.stl')
        cq.exporters.export(cq.Workplane().add(posed), stl, tolerance=0.02, angularTolerance=0.15)
        files.append(stl)
        if not (vname != 'plastic' and name == 'chassis' and False):
            stp = os.path.join(OUT, 'step', vname, f'soul_p0_{vname}_{name}.step')
            cq.exporters.export(cq.Workplane().add(posed), stp)
            files.append(stp)
    # assembled (in the product frame) for renders and for the CNC shop's reference
    for name, s in parts.items():
        if name.startswith('pin_'):
            pd = ctx['pins'][name[4:]]
            pl = pd['frame']
            # pin in place: shaft from 0.2 beyond the actuator along the pin axis
            loc = cq.Location(pl, cq.Vector(0, 0, 0))
            s = cq.Workplane(pl).add(s.moved(cq.Location(cq.Vector(0, 0, 0.2)))).val()
            s = s.moved(cq.Location(pl.origin, pl.zDir, 0)) if False else place_pin(s, pl)
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, 'stl', 'assembly', f'{vname}_{name}.stl'),
                            tolerance=0.03, angularTolerance=0.2)
    for name in ['battery', 'speaker', 'usb_plug']:
        cq.exporters.export(cq.Workplane().add(ctx[name]), os.path.join(OUT, 'stl', 'assembly', f'{vname}_{name}.stl'),
                            tolerance=0.05)
    for name, s in ctx['board'].items():
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, 'stl', 'assembly', f'{vname}_board_{name}.stl'),
                            tolerance=0.05)
    if vname == 'plastic':
        asm = cq.Assembly()
        for name, s in parts.items():
            if not name.startswith('pin_'):
                asm.add(s, name=name)
        asm.add(ctx['battery'], name='dummy_battery_503035', color=cq.Color(0.55, 0.7, 0.85))
        asm.add(ctx['speaker'], name='dummy_speaker_1511', color=cq.Color(0.2, 0.2, 0.2))
        for n_, s_ in ctx['board'].items():
            asm.add(s_, name='dummy_board_' + n_, color=cq.Color(0.1, 0.1, 0.12))
        asm.save(os.path.join(OUT, 'step', 'soul_p0_plastic_ASSEMBLY_with_board.step'))
    return files


def place_pin(pin, pl):
    """pin is built along +Z from 0 (tip at the actuator); map local Z to the pin axis frame pl (offset 0.2)."""
    T = cq.Location(cq.Plane(origin=pl.origin + pl.zDir * 0.2, xDir=pl.xDir, normal=pl.zDir))
    return pin.moved(T)


def main():
    which = sys.argv[1:] or ['plastic', 'alu', 'alu_band']
    report = {}
    for vn in which:
        parts, ctx = build(vn)
        files = export_all(vn, parts, ctx)
        report[vn] = dict(screws=ctx['screws'], interference=ctx['inter'], clearance=ctx['clear'], dims=ctx['dims'],
                          pins={k: dict(L=v['L'], exit=v['exit'], shell=v['shell']) for k, v in ctx['pins'].items()},
                          log=ctx['log'], files=[os.path.relpath(f, OUT) for f in files])
        with open(os.path.join(OUT, 'cad', f'report_{vn}.json'), 'w') as f:
            json.dump(report[vn], f, indent=1, default=float)
    print('done')


if __name__ == '__main__':
    main()
