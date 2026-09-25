#!/usr/bin/env python3
"""hand_sdf_v8.py -- the SAME stylised right hand as v4/v5/v6 (renders/v5/src/hand_sdf.py: palm, pads, forearm,
four fingers and the thumb, same radii and lengths), re-posed so that it cradles the bigger SOUL M (90 x 103 mm)
like a large pebble: the palm hollow is wider and shallower, the fingers curl up around the crown and the thumb
comes up along the side. The device itself (a rounded box, passed in by soul_v8.py in hand coordinates) is carved
out of the hand with a soft maximum, so the fingers and pads press against it instead of passing through it.

Frame and units as hand_sdf.py (mm; palm +z, fingers +y, thumb +x, palm centre at the origin).
    python3 hand_sdf_v8.py out.npz [key=value ...]
"""
import os
import sys

import numpy as np
from skimage.measure import marching_cubes

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v5', 'src')))
from hand_sdf import smin, smax, ellipsoid, rcapsule, rbox, finger_chain  # noqa: E402

P_ = dict(fk=1.0, f0=1.0, cup_z=96.0, cup_r=84.0, cup_k=9.0,
          t_yaw=42.0, t_f1=10.0, t_f2=22.0, t_f3=16.0, t_side=-14.0,
          bx_hw=0.0, carve_k=2.5, carve_off=0.3)


def dev_sdf(P):
    c = np.array([P_['bx_cx'], P_['bx_cy'], P_['bx_cz']])
    A = np.array([[P_['bx_%s%d' % (ax, i)] for ax in 'xyz'] for i in range(3)])      # rows = box axes
    hw = np.array([P_['bx_hw'], P_['bx_hd'], P_['bx_hh']])
    q = (P - c) @ A.T
    return rbox(q, np.zeros(3), hw, P_.get('bx_r', 12.0))


def hand_sdf(P):
    d = rbox(P, np.array([0.0, 2.0, -1.0]), (40.0, 46.0, 12.5), 11.0)
    d = smin(d, ellipsoid(P, np.array([22.0, -20.0, 2.0]), np.array([22.0, 28.0, 13.0])), 8.0)    # thenar
    d = smin(d, ellipsoid(P, np.array([-26.0, -14.0, 1.0]), np.array([16.0, 32.0, 12.5])), 8.0)   # hypothenar
    d = smin(d, ellipsoid(P, np.array([0.0, 38.0, 3.0]), np.array([38.0, 12.0, 11.0])), 6.0)      # finger pads
    Q = P.copy()
    Q[..., 0] = Q[..., 0] / 1.32
    d = smin(d, rcapsule(Q, (0, -38, -3), (0, -175, -16), 17.0, 21.0), 14.0)
    # a wider, shallower hollow than v5's (the M is 90 x 103 mm)
    d = smax(d, -(np.linalg.norm(P - np.array([2.0, 6.0, P_['cup_z']]), axis=-1) - P_['cup_r']), P_['cup_k'])
    fingers = [
        ((27.0, 42.0, 1.5), 4.0, (44, 26, 20), (9.4, 8.7, 8.1, 7.3), (22, 34, 24)),     # index
        ((7.5, 46.0, 2.0), 0.0, (48, 29, 21), (9.6, 8.9, 8.2, 7.4), (20, 34, 24)),      # middle
        ((-12.5, 44.0, 1.5), -4.0, (45, 27, 20), (9.2, 8.5, 7.9, 7.1), (22, 36, 24)),   # ring
        ((-30.0, 37.0, 0.5), -9.0, (36, 21, 18), (8.2, 7.6, 7.0, 6.4), (26, 38, 26)),  # little
    ]
    fd = None
    for base, yaw, L, R, F in fingers:
        F = (F[0] * P_['f0'], F[1] * P_['fk'], F[2] * P_['fk'])
        pts, _ = finger_chain(base, yaw, L, R, F)
        dd = None
        for i in range(3):
            c = rcapsule(P, pts[i], pts[i + 1], R[i], R[i + 1])
            dd = c if dd is None else smin(dd, c, 2.0)
        fd = dd if fd is None else np.minimum(fd, dd)
    d = smin(d, fd, 5.0)
    pts, _ = finger_chain((30.0, -22.0, 2.0), P_['t_yaw'], (30, 28, 24), None,
                          (P_['t_f1'], P_['t_f2'], P_['t_f3']), side_deg=P_['t_side'])
    R = (12.5, 11.0, 10.0, 8.8)
    td = None
    for i in range(3):
        c = rcapsule(P, pts[i], pts[i + 1], R[i], R[i + 1])
        td = c if td is None else smin(td, c, 3.0)
    d = smin(d, td, 9.0)
    if P_['bx_hw'] > 0:
        d = smax(d, -(dev_sdf(P) + P_['carve_off']), P_['carve_k'])
    return d


def main():
    out = sys.argv[1]
    for kv in sys.argv[2:]:
        a, b = kv.split('=')
        P_[a] = float(b)
    vox = 1.0
    xs = np.arange(-72, 115, vox)
    ys = np.arange(-180, 160, vox)
    zs = np.arange(-42, 120, vox)
    vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
    for i, x in enumerate(xs):
        Y, Z = np.meshgrid(ys, zs, indexing='ij')
        P = np.stack([np.full_like(Y, x), Y, Z], -1)
        vol[i] = hand_sdf(P)
    v, f, n, _ = marching_cubes(vol, 0.0, spacing=(vox, vox, vox))
    v += np.array([xs[0], ys[0], zs[0]])
    np.savez_compressed(out, verts=v.astype(np.float32), faces=f.astype(np.int32))
    print('wrote', out, len(v), 'verts', len(f), 'faces')


if __name__ == '__main__':
    main()
