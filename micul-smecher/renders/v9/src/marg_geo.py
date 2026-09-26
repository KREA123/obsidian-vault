"""marg_geo.py -- SOUL v9 = MĂRGĂRITAR (renders/v5/src/alt_geo.py, ALT B) as the final shape, at the v6 design
scale (glass Ø52, 63 wide). Pure numpy. The v9 renders scale it uniformly by K = 90 / 63 (glass Ø74.3, like v8).

Changes to the v5 MĂRGĂRITAR, all in the section tables' frame (z up, face toward -y, 8 deg lean kept):
  * depth: only the back half (behind the girdle seam) is compressed by a constant factor S_BACK, so the whole
    body is DEPTH_M / K deep (31.5 mm at size M, like v8); the front (face table, rolls, glass) is untouched.
  * y-shift: the section is moved in y so that the flat base (cut at Z_CUT) is centred on the origin, where the
    v6 polymer foot stands.
    python3 marg_geo.py      prints the numbers
"""
import math
import os
import sys

import numpy as np

_V5 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v5', 'src'))
if _V5 not in sys.path:
    sys.path.insert(0, _V5)
import alt_geo as AG  # noqa: E402

K = 90.0 / 63.0
DEPTH_M = 31.5
Z_CUT = 2.4            # flat cut (just above the v5 R0.6 base fillet), local mm
FOOT_H = 1.2
Z_FOOT = Z_CUT - FOOT_H


class MargaritarV9(AG.Margaritar):
    name = 'MARGARITAR_V9'

    def __init__(self, s_back=None, dy=None, depth_m=DEPTH_M):
        super().__init__()
        self.s_back = 1.0
        self.dy = 0.0
        if dy is None:
            ring = self.ring(Z_CUT, 4096)
            dy = -0.5 * (ring[:, 1].min() + ring[:, 1].max())
        self.dy = dy
        self.yg += dy
        if s_back is None:
            lo, hi = 0.3, 1.0
            for _ in range(50):
                m = 0.5 * (lo + hi)
                self.s_back = m
                d = self.depth()
                if d > depth_m / K:
                    hi = m
                else:
                    lo = m
            s_back = 0.5 * (lo + hi)
        self.s_back = s_back
        # recentre after the compression (the cut ring's back moved)
        ring = self.ring(Z_CUT, 4096)
        d2 = -0.5 * (ring[:, 1].min() + ring[:, 1].max())
        self.dy += d2
        self.yg += d2

    def sections(self, z):
        w, yf, yb, ys, c, pf = super().sections(z)
        yb = ys + (yb - ys) * self.s_back
        return w, yf, yb, ys, c, pf

    def depth(self, n=1500):
        zz = np.linspace(Z_CUT, self.H, n)
        w, yf, yb, ys, c, pf = self.sections(zz)
        return float(yb.max() - yf.min())


_B = {}


def geo():
    if 'b' not in _B:
        _B['b'] = MargaritarV9()
    return _B['b']


if __name__ == '__main__':
    B = geo()
    zz = np.linspace(Z_CUT, B.H, 4000)
    w, yf, yb, ys, c, pf = B.sections(zz)
    W, D, Hh = 2 * w.max(), yb.max() - yf.min(), B.H - Z_FOOT
    print('s_back %.4f  dy %.3f  G %s' % (B.s_back, B.dy, np.round(B.G(), 3)))
    print('local  W %.2f  H %.2f (foot bottom -> crown)  D %.2f   glass Ø%.1f' % (W, Hh, D, 2 * B.r_glass))
    print('size M W %.2f  H %.2f  D %.2f   glass Ø%.2f' % (W * K, Hh * K, D * K, 2 * B.r_glass * K))
    r = B.ring(Z_CUT, 2048)
    print('cut ring at z %.1f: x %.2f..%.2f  y %.2f..%.2f' % (Z_CUT, r[:, 0].min(), r[:, 0].max(), r[:, 1].min(), r[:, 1].max()))
