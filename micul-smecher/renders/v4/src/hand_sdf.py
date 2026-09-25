#!/usr/bin/env python3
"""hand_sdf.py -- a stylised adult RIGHT hand, palm up, as a mesh (for the "in hand" render).

Signed-distance modelling (numpy): palm + thenar/hypothenar pads + forearm blended with a smooth
minimum, fingers and thumb as chains of tapered capsules with flexion, a shallow hollow in the palm
where the device rests; polygonised with marching cubes (scikit-image).  Units: mm.
Frame: palm facing +z, fingers towards +y, thumb on +x, palm centre at the origin.

    python3 hand_sdf.py [out.npz]        (default: tex/hand.npz; ~20 s)
"""
import math
import os
import sys

import numpy as np
from skimage.measure import marching_cubes

VOX = 1.0


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def ellipsoid(P, c, r):
    q = (P - c) / r
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / r, axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def rcapsule(P, a, b, ra, rb):
    """Capsule a->b with radius ra at a and rb at b (round cone approximation)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ba = b - a
    t = np.clip(((P - a) @ ba) / (ba @ ba), 0, 1)
    d = np.linalg.norm(P - (a + t[..., None] * ba), axis=-1)
    return d - (ra + (rb - ra) * t)


def rbox(P, c, half, r):
    q = np.abs(P - c) - (np.asarray(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - r


def finger_chain(base, yaw_deg, lengths, radii, flex_deg, side_deg=0.0):
    """Joint positions of a finger: flexion bends it towards +z (palm side), yaw turns it in xy."""
    pts = [np.array(base, float)]
    pitch = 0.0
    yaw = math.radians(yaw_deg)
    for L, f in zip(lengths, flex_deg):
        pitch += math.radians(f)
        yaw += math.radians(side_deg)
        d = np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
        pts.append(pts[-1] + d * L)
    return pts, radii


def hand_sdf(P):
    # palm block, slightly wider at the knuckles, thicker at the heel
    d = rbox(P, np.array([0.0, 2.0, -1.0]), (40.0, 46.0, 12.5), 11.0)
    d = smin(d, ellipsoid(P, np.array([22.0, -20.0, 2.0]), np.array([22.0, 28.0, 13.0])), 8.0)    # thenar
    d = smin(d, ellipsoid(P, np.array([-26.0, -14.0, 1.0]), np.array([16.0, 32.0, 12.5])), 8.0)   # hypothenar
    d = smin(d, ellipsoid(P, np.array([0.0, 38.0, 3.0]), np.array([38.0, 12.0, 11.0])), 6.0)      # finger pads
    # wrist + forearm (elliptic section: squash x)
    Q = P.copy()
    Q[..., 0] = Q[..., 0] / 1.32
    d = smin(d, rcapsule(Q, (0, -38, -3), (0, -175, -16), 17.0, 21.0), 14.0)
    # the hollow the stone rests in (shallow cup)
    d = smax(d, -(np.linalg.norm(P - np.array([2.0, 4.0, 66.0]), axis=-1) - 58.5), 7.0)
    fingers = [  # base (x, y, z), yaw, lengths, radii (base..tip), flexion per joint
        ((27.0, 42.0, 1.5), 4.0, (44, 26, 20), (9.4, 8.7, 8.1, 7.3), (22, 34, 24)),     # index
        ((7.5, 46.0, 2.0), 0.0, (48, 29, 21), (9.6, 8.9, 8.2, 7.4), (20, 34, 24)),      # middle
        ((-12.5, 44.0, 1.5), -4.0, (45, 27, 20), (9.2, 8.5, 7.9, 7.1), (22, 36, 24)),   # ring
        ((-30.0, 37.0, 0.5), -9.0, (36, 21, 18), (8.2, 7.6, 7.0, 6.4), (26, 38, 26)),  # little
    ]
    fd = None
    for base, yaw, L, R, F in fingers:
        pts, _ = finger_chain(base, yaw, L, R, F)
        dd = None
        for i in range(3):
            c = rcapsule(P, pts[i], pts[i + 1], R[i], R[i + 1])
            dd = c if dd is None else smin(dd, c, 2.0)
        fd = dd if fd is None else np.minimum(fd, dd)
    d = smin(d, fd, 5.0)
    # thumb: out of the thenar pad, rising and curling in over the palm edge
    pts, _ = finger_chain((30.0, -22.0, 2.0), 50.0, (30, 28, 24), None, (14, 30, 30), side_deg=-20.0)
    R = (12.5, 11.0, 10.0, 8.8)
    td = None
    for i in range(3):
        c = rcapsule(P, pts[i], pts[i + 1], R[i], R[i + 1])
        td = c if td is None else smin(td, c, 3.0)
    d = smin(d, td, 9.0)
    return d


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex',
                                                             'hand.npz')
    xs = np.arange(-62, 100, VOX)
    ys = np.arange(-180, 140, VOX)
    zs = np.arange(-42, 80, VOX)
    vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
    for i, x in enumerate(xs):       # slab by slab (memory)
        Y, Z = np.meshgrid(ys, zs, indexing='ij')
        P = np.stack([np.full_like(Y, x), Y, Z], -1)
        vol[i] = hand_sdf(P)
    v, f, n, _ = marching_cubes(vol, 0.0, spacing=(VOX, VOX, VOX))
    v += np.array([xs[0], ys[0], zs[0]])
    np.savez_compressed(out, verts=v.astype(np.float32), faces=f.astype(np.int32))
    print('wrote', out, len(v), 'verts', len(f), 'faces')


if __name__ == '__main__':
    main()
