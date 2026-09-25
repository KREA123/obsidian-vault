#!/usr/bin/env python3
"""hand_sdf_v7.py -- the v4/v5 stylised right hand (renders/v5/src/hand_sdf.py), re-posed for v7:

  open   : a flatter open palm (fingers only slightly curled, no cup), so SOULs of three sizes can lie in the same
           hand for the size comparison (soul_v7_hands.png)
  type   : the same open palm with the thumb lifted and bent in over the palm, its tip hovering where the
           keyboard of a device lying in the palm would be (soul_v7_typing.png)

Frame and units as hand_sdf.py (mm; palm +z, fingers +y, thumb +x, palm centre at the origin).
    python3 hand_sdf_v7.py open|type out.npz [key=value ...]
"""
import math
import os
import sys

import numpy as np
from skimage.measure import marching_cubes

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v5', 'src')))
from hand_sdf import smin, smax, ellipsoid, rcapsule, rbox, finger_chain  # noqa: E402

P_ = dict(flex_k=0.45, cup=0.0,
          # thumb (typing pose): base, yaw, pitch-per-joint, side-per-joint
          t_yaw=-35.0, t_f1=38.0, t_f2=12.0, t_f3=-18.0, t_side=-22.0, t_len1=34.0, t_len2=30.0, t_len3=25.0)


def hand_sdf(P, pose):
    d = rbox(P, np.array([0.0, 2.0, -1.0]), (40.0, 46.0, 12.5), 11.0)
    d = smin(d, ellipsoid(P, np.array([22.0, -20.0, 2.0]), np.array([22.0, 28.0, 13.0])), 8.0)
    d = smin(d, ellipsoid(P, np.array([-26.0, -14.0, 1.0]), np.array([16.0, 32.0, 12.5])), 8.0)
    d = smin(d, ellipsoid(P, np.array([0.0, 38.0, 3.0]), np.array([38.0, 12.0, 11.0])), 6.0)
    Q = P.copy()
    Q[..., 0] = Q[..., 0] / 1.32
    d = smin(d, rcapsule(Q, (0, -38, -3), (0, -175, -16), 17.0, 21.0), 14.0)
    if P_['cup'] > 0:
        d = smax(d, -(np.linalg.norm(P - np.array([2.0, 4.0, 66.0]), axis=-1) - 58.5 - (1 - P_['cup']) * 4), 7.0)
    k = P_['flex_k']
    fingers = [
        ((27.0, 42.0, 1.5), 5.0, (44, 26, 20), (9.4, 8.7, 8.1, 7.3), (22, 34, 24)),
        ((7.5, 46.0, 2.0), 0.5, (48, 29, 21), (9.6, 8.9, 8.2, 7.4), (20, 34, 24)),
        ((-12.5, 44.0, 1.5), -4.5, (45, 27, 20), (9.2, 8.5, 7.9, 7.1), (22, 36, 24)),
        ((-30.0, 37.0, 0.5), -11.0, (36, 21, 18), (8.2, 7.6, 7.0, 6.4), (26, 38, 26)),
    ]
    fd = None
    for base, yaw, L, R, F in fingers:
        pts, _ = finger_chain(base, yaw, L, R, [f * k for f in F])
        dd = None
        for i in range(3):
            c = rcapsule(P, pts[i], pts[i + 1], R[i], R[i + 1])
            dd = c if dd is None else smin(dd, c, 2.0)
        fd = dd if fd is None else np.minimum(fd, dd)
    d = smin(d, fd, 5.0)
    if pose == 'type':
        pts, _ = finger_chain((30.0, -22.0, 2.0), P_['t_yaw'], (P_['t_len1'], P_['t_len2'], P_['t_len3']), None,
                              (P_['t_f1'], P_['t_f2'], P_['t_f3']), side_deg=P_['t_side'])
    else:
        pts, _ = finger_chain((30.0, -22.0, 2.0), 50.0, (30, 28, 24), None, (6, 10, 8), side_deg=-12.0)
    R = (12.5, 11.0, 10.0, 8.8)
    td = None
    for i in range(3):
        c = rcapsule(P, pts[i], pts[i + 1], R[i], R[i + 1])
        td = c if td is None else smin(td, c, 3.0)
    d = smin(d, td, 9.0)
    return d, pts


def main():
    pose = sys.argv[1]
    out = sys.argv[2]
    for kv in sys.argv[3:]:
        a, b = kv.split('=')
        P_[a] = float(b)
    vox = 1.0
    xs = np.arange(-62, 110, vox)
    ys = np.arange(-180, 150, vox)
    zs = np.arange(-42, 110, vox)
    vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
    tip = None
    for i, x in enumerate(xs):
        Y, Z = np.meshgrid(ys, zs, indexing='ij')
        P = np.stack([np.full_like(Y, x), Y, Z], -1)
        vol[i], tip = hand_sdf(P, pose)
    v, f, n, _ = marching_cubes(vol, 0.0, spacing=(vox, vox, vox))
    v += np.array([xs[0], ys[0], zs[0]])
    np.savez_compressed(out, verts=v.astype(np.float32), faces=f.astype(np.int32),
                        thumb=np.array(tip, np.float32))
    print('wrote', out, len(v), 'verts; thumb joints', np.round(np.array(tip), 1).tolist())


if __name__ == '__main__':
    main()
