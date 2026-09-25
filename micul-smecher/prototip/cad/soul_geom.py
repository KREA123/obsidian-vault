"""soul_geom.py -- outline math of SOUL-P0 (the DIY pilot of SOUL), pure numpy + shapely.

The outline is the v5 SOUL loft (render-brief v5 §2 / renders/v5/src/soul_geo.py, tables copied verbatim)
with four pilot changes:
  1. FLAT BASE: the loft is cut at v5 z = Z_CUT (no rocker sole, no sole ellipsoid) and the body is stretched
     in z so the total height is H_TOTAL (75 mm). Base footprint ~ 33 x 25 mm.
  2. DEEPER BACK: the back half of every section is scaled by K_BACK about the seam (27.1 -> ~29.5 mm deep),
     room for the Waveshare stack (8.9 mm) + a stock LiPo.
  3. PLANAR SEAM: the silhouette line y_s is replaced by its best-fit plane y = SEAM_A + SEAM_B * Z (max 0.67 mm
     change), so the maximum width lies exactly on the parting plane -> no undercut for moulds / 3-axis CNC.
  4. The v5 below-z-8 widening (DELTA, only needed for the sole Boolean) is removed.

Frame (mm): origin = centre of the flat base, +Z up, the face looks toward -Y, +X = viewer's right.
"""
import math

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

# ---------------------------------------------------------------- v5 tables (render-brief v5 §2.1)
WZ = [0, 1.2, 2.2, 4, 6.3, 8, 10.5, 14, 18.5, 23, 28, 34, 40.5, 48, 55.5, 60, 63, 66, 69.5, 71.5, 73.2, 74]
WV = [6.9, 11.9, 14.7, 18.6, 22.5, 24.3, 26.0, 27.7, 28.9, 29.9, 30.6, 31.2, 31.5, 31.2, 30.4, 29.4, 28.3, 26.4,
      22.8, 19.0, 12.5, 0]
SZ_ = [1.9, 3, 4.5, 6.3, 8, 10.5, 14, 18.5, 23, 28, 34, 40.5, 48, 55.5, 60, 63, 66, 69.5, 71.5, 73.2, 74]
YF = [-12.5, -13.2, -13.8, -14.2, -14.4, -14.4, -14.2, -13.7, -13.1, -12.4, -11.5, -10.6, -9.6, -8.5, -7.9, -7.4,
      -7.0, -5.9, -4.7, -2.8, -1.0]
YB = [12.0, 12.4, 12.7, 12.8, 12.7, 12.4, 11.8, 11.0, 10.4, 9.9, 9.6, 9.4, 8.7, 7.6, 6.7, 5.8, 4.6, 2.7, 1.3, -0.1,
      -1.0]
LEAN5 = math.radians(8.0)
R_TABLE = 26.2
FADE = 1.5

# ---------------------------------------------------------------- pilot parameters
Z_CUT = 2.5                       # v5 height where the flat base is cut
H_TOTAL = 75.0                    # pilot height
SZ = H_TOTAL / (74.0 - Z_CUT)     # vertical stretch (1.049)
K_BACK = 1.13                     # back-half depth scale about the seam
SEAM_A, SEAM_B = -5.16, 0.0396    # parting plane y = A + B*Z (least-squares fit of v5 y_s)


def pchip(xk, yk):
    """Monotone cubic (Fritsch-Carlson); linear extrapolation with the end slopes (same as soul_geo.py)."""
    xk = np.asarray(xk, float)
    yk = np.asarray(yk, float)
    h = np.diff(xk)
    d = np.diff(yk) / h
    n = len(xk)
    m = np.zeros(n)
    for k in range(1, n - 1):
        if d[k - 1] * d[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])

    def end(h0, h1, d0, d1):
        v = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if np.sign(v) != np.sign(d0):
            return 0.0
        if np.sign(d0) != np.sign(d1) and abs(v) > abs(3 * d0):
            return 3 * d0
        return v
    m[0] = end(h[0], h[1], d[0], d[1])
    m[-1] = end(h[-1], h[-2], d[-1], d[-2])

    def f(x):
        x = np.asarray(x, float)
        out = np.empty_like(x)
        lo, hi = x <= xk[0], x >= xk[-1]
        mid = ~(lo | hi)
        out[lo] = yk[0] + m[0] * (x[lo] - xk[0])
        out[hi] = yk[-1] + m[-1] * (x[hi] - xk[-1])
        xm = x[mid]
        i = np.clip(np.searchsorted(xk, xm) - 1, 0, n - 2)
        t = (xm - xk[i]) / h[i]
        t2, t3 = t * t, t * t * t
        out[mid] = ((2 * t3 - 3 * t2 + 1) * yk[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * yk[i + 1]
                    + (t3 - t2) * h[i] * m[i + 1])
        return out
    return f


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _s_pchip(zk, vk):
    zk, vk = np.asarray(zk, float), np.asarray(vk, float)
    k = zk >= 55.0
    return pchip(np.sqrt(74.0 - zk[k])[::-1], vk[k][::-1])


def _blend(fz, fs, z0=58.0, z1=64.0):
    def f(z):
        z = np.asarray(z, float)
        a = fz(z)
        b = fs(np.sqrt(np.clip(74.0 - z, 0.0, None)))
        return a + (b - a) * smoothstep((z - z0) / (z1 - z0))
    return f


_w = _blend(pchip(WZ, WV), _s_pchip(WZ, WV))
_yf = _blend(pchip(SZ_, YF), _s_pchip(SZ_, YF))
_yb = _blend(pchip(SZ_, YB), _s_pchip(SZ_, YB))
_sf = (YF[1] - YF[0]) / (SZ_[1] - SZ_[0])
_sb = (YB[1] - YB[0]) / (SZ_[1] - SZ_[0])
Z_BAND = (40.5 - R_TABLE * math.cos(LEAN5), 40.5 + R_TABLE * math.cos(LEAN5))


def z5(Z):
    """pilot Z -> v5 z"""
    return np.asarray(Z, float) / SZ + Z_CUT


def sections(Z):
    """Pilot sections at heights Z: half-width w, front y_f, back y_b, seam y_s, table half-width c, front exponent."""
    z = np.minimum(z5(Z), 74.0)
    w = np.maximum(_w(z), 0.0)
    yf = np.where(z < SZ_[0], YF[0] + _sf * (z - SZ_[0]), _yf(z))
    yb = np.where(z < SZ_[0], YB[0] + _sb * (z - SZ_[0]), _yb(z))
    fd = smoothstep(np.minimum(z - Z_BAND[0], Z_BAND[1] - z) / FADE)
    plane = -10.6 + math.tan(LEAN5) * (z - 40.5)
    yf = yf + fd * (plane - yf)
    c = np.sqrt(np.maximum(R_TABLE ** 2 - ((z - 40.5) / math.cos(LEAN5)) ** 2, 0.0)) * fd
    ys5 = yf + 0.36 * (yb - yf)
    yb = ys5 + (yb - ys5) * K_BACK
    ys = SEAM_A + SEAM_B * np.asarray(Z, float)
    ys = np.clip(ys, yf + 0.05, None)
    yb = np.maximum(yb, ys + 0.05)
    pf = 2.6 + (2.4 - 2.6) * fd
    return w, yf, yb, ys, c, pf


def _spow(v, e):
    return np.sign(v) * np.abs(v) ** e


def ring(Z, n_raw=1536):
    """Closed outer ring (n_raw, 2) at pilot height Z, starting at the back centre, counter-clockwise seen from +Z
    ordering: back centre -> +x seam -> front -> -x seam -> back."""
    w, yf, yb, ys, c, pf = [float(np.ravel(v)[0]) for v in sections(np.array([Z]))]
    nb = n_raw // 2
    t = np.linspace(0.5 * math.pi, 0.0, nb // 2, endpoint=False)
    back_r = np.stack([w * _spow(np.cos(t), 2 / 2.2), ys + (yb - ys) * _spow(np.sin(t), 2 / 2.2)], 1)
    nf = n_raw - nb
    if c > 1e-4:
        nroll = nf // 3
        nt = nf - 2 * nroll
        tt = np.linspace(0.0, 0.5 * math.pi, nroll, endpoint=False)
        roll_r = np.stack([c + (w - c) * _spow(np.cos(tt), 2 / pf), ys - (ys - yf) * _spow(np.sin(tt), 2 / pf)], 1)
        xs = np.linspace(c, -c, nt, endpoint=False)
        table = np.stack([xs, np.full(nt, yf)], 1)
        tt2 = np.linspace(0.5 * math.pi, math.pi, nroll, endpoint=False)
        roll_l = np.stack([-c + (w - c) * _spow(np.cos(tt2), 2 / pf), ys - (ys - yf) * _spow(np.sin(tt2), 2 / pf)], 1)
        front = np.vstack([roll_r, table, roll_l])
    else:
        tt = np.linspace(0.0, math.pi, nf, endpoint=False)
        front = np.stack([w * _spow(np.cos(tt), 2 / pf), ys - (ys - yf) * _spow(np.sin(tt), 2 / pf)], 1)
    t3 = np.linspace(math.pi, 0.5 * math.pi, nb - nb // 2, endpoint=False)
    back_l = np.stack([w * _spow(np.cos(t3), 2 / 2.2), ys + (yb - ys) * _spow(np.sin(t3), 2 / 2.2)], 1)
    P = np.vstack([back_r, front, back_l])
    # the listed order runs clockwise seen from +Z (back -> +x -> front); flip to CCW for shapely/OCC
    return P[::-1]


def resample(P, n, curv_w=4.0):
    """Resample a closed ring to n points (arc length + turning weighted), starting at the back-centre point."""
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    tang = np.diff(Q, axis=0)
    ang = np.arctan2(tang[:, 1], tang[:, 0])
    dth = np.abs(np.angle(np.exp(1j * (np.roll(ang, -1) - ang))))
    wgt = seg + curv_w * 0.5 * (dth + np.roll(dth, 1))
    L = np.concatenate([[0], np.cumsum(wgt)])
    s = np.linspace(0, L[-1], n, endpoint=False)
    return np.stack([np.interp(s, L, Q[:, 0]), np.interp(s, L, Q[:, 1])], 1)


def start_at_back(P):
    """Roll a CCW ring so it starts at the point with max y among |x| small (back centre)."""
    score = P[:, 1] - 5.0 * np.abs(P[:, 0])
    i = int(np.argmax(score))
    return np.roll(P, -i, axis=0)


# ---------------------------------------------------------------- face / glass frame
LEAN = math.atan(math.tan(LEAN5) / SZ)                       # 7.63 deg after the z stretch
N_OUT = np.array([0.0, -math.cos(LEAN), math.sin(LEAN)])     # outward face normal
UP = np.array([0.0, math.sin(LEAN), math.cos(LEAN)])         # in-plane up
INW = -N_OUT
G = np.array([0.0, -10.6, (40.5 - Z_CUT) * SZ])              # centre of the flat table (glass centre)


def table_y(Z):
    return -10.6 + math.tan(LEAN) * (np.asarray(Z, float) - G[2])


# ---------------------------------------------------------------- slices of solids (for offsets / checks)
_SLICE_CACHE = {}


def outer_poly(Z):
    key = round(float(Z), 4)
    if key not in _SLICE_CACHE:
        if Z < 0 or Z > H_TOTAL - 1e-3:
            _SLICE_CACHE[key] = Polygon()
        else:
            _SLICE_CACHE[key] = Polygon(ring(Z, 720)).buffer(0)
    return _SLICE_CACHE[key]


def eroded_poly(Z, t, nd=9):
    """Slice at Z of the outer body eroded by a ball of radius t (exact morphological offset, sampled)."""
    if Z < t - 1e-9:
        return Polygon()
    res = None
    for d in np.linspace(-t, t, nd):
        r = math.sqrt(max(t * t - d * d, 0.0))
        p = outer_poly(Z + d)
        if p.is_empty:
            return Polygon()
        q = p.buffer(-r, resolution=24) if r > 1e-6 else p
        res = q if res is None else res.intersection(q)
        if res.is_empty:
            return Polygon()
    if res.geom_type != 'Polygon':
        res = max(res.geoms, key=lambda g: g.area) if hasattr(res, 'geoms') and len(res.geoms) else Polygon()
    return res


def poly_ring(poly, n):
    P = np.asarray(poly.exterior.coords)[:-1]
    # shapely exterior orientation: make CCW
    if Polygon(P).exterior.is_ccw is False:
        P = P[::-1]
    P = resample(P, 4 * n, curv_w=0.0)
    P = start_at_back(P)
    return resample(P, n, curv_w=2.0)


def ring_pts(Z, n):
    P = start_at_back(ring(Z, 2048))
    return resample(P, n)


def dims_report():
    zz = np.linspace(0, H_TOTAL, 1501)
    w, yf, yb, ys, c, pf = sections(zz)
    D = yb - yf
    return dict(width=2 * w.max(), height=H_TOTAL, depth=D.max(), z_wmax=zz[np.argmax(w)], z_dmax=zz[np.argmax(D)],
                base_w=2 * w[0], base_d=D[0], lean_deg=math.degrees(LEAN), G=G.tolist())


if __name__ == '__main__':
    print(dims_report())
