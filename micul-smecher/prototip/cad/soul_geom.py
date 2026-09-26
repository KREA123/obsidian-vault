"""soul_geom.py -- outline math of SOUL-P0 size M (the DIY pilot of SOUL), pure numpy + shapely.

SHAPE: MĂRGĂRITAR (founder decision 2026-09-26; before it the P0 used the v6 HOPA outline, see git history).
The outline is the MĂRGĂRITAR section model of renders/v5/src/alt_geo.py (render brief v5 §5, tables copied
verbatim below), the same shape as the v9 renders (renders/v9/src/marg_geo.py), with the pilot changes:
  1. FLAT BASE: cut at MĂRGĂRITAR z = Z_CUT (2.4, as v9), closed by the printed base plate + oval foot.
  2. SCALE: UNIFORM by K in the front view (x and z) so the stock Waveshare 2.8C lens (Ø95.86) sits in the flat
     face table like the Ø52 glass of the v9 design: visible glass / width = 92.9 / 112.1 = 0.83 (v9: 52 / 63);
     by KY in depth (as the HOPA P0: 1.24, room for the Waveshare stack + the LiPo).
  3. PLANAR SEAM: the silhouette line y_s is replaced by its best-fit plane y = SEAM_A + SEAM_B * Z, so the
     maximum width lies on the parting plane -> no undercut for moulds / 3-axis CNC.

Frame (mm): origin = centre of the flat base, +Z up, the face looks toward -Y, +X = viewer's right.
"""
import math

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

# ---------------------------------------------------------------- MĂRGĂRITAR tables (alt_geo.py, brief v5 §5)
H5 = 72.0                         # crown pole (MĂRGĂRITAR z)
WZ = [0, 4, 8, 18, 30, 39.6, 54, 62, 67, 70, 72]
WV = [14.0, 21.5, 25.0, 27.5, 30.5, 31.5, 29.25, 25.5, 19.0, 11.0, 0]
DZ = [0, 6, 12, 30, 40, 55, 62, 68, 72]
DV = [17, 22, 24, 22, 20.5, 17.5, 16, 12, 0]
LEAN5 = math.radians(8.0)
T8, C8 = math.tan(LEAN5), math.cos(LEAN5)
ZC5 = 38.9                        # flat-table centre (glass centre)
R_TABLE = 28.0                    # flat Ø56 zone (the Ø52 glass sits in it)
R_BEND = 150.0                    # below the table the face bends at R150 into the chin
PF, PR, PB = 2.6, 2.4, 2.2        # front / table-roll / back superellipse exponents
FADE = 4.0
SEAM_FRAC = 0.36

# ---------------------------------------------------------------- pilot parameters (size M)
Z_CUT = 2.4                       # MĂRGĂRITAR height where the flat base is cut (as v9)
K = float(__import__("os").environ.get("SOUL_K", 1.78))     # uniform front-view scale (x, z): 63 x 69.6 -> 112.1 x 123.9
KY = float(__import__("os").environ.get("SOUL_KY", 1.24))   # depth scale
SZ = K
H_TOTAL = (H5 - Z_CUT) * K        # shell height above the flat base plane (the foot adds FOOT_H below)
K_BACK = 1.0                      # extra back-half depth scale about the seam (1.0 = none)
SEAM_A, SEAM_B = None, None       # parting plane y = A + B*Z, fitted below to the scaled silhouette line
FOOT_H = 1.2                      # oval foot below the base plane (v9: 28 x 13.8)
FOOT_A, FOOT_B, FOOT_P = 14.0 * K, 6.9 * KY, 2.6


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


def concave_majorant(f, z0, z1, n=4000, sigma_mm=1.2):
    """least concave majorant of f on [z0, z1], lightly smoothed (alt_geo.py: removes PCHIP's small waists)"""
    z = np.linspace(z0, z1, n)
    v = f(z)
    hull = []
    for i in range(n):
        while len(hull) >= 2:
            a, b = hull[-2], hull[-1]
            if (z[b] - z[a]) * (v[i] - v[a]) - (v[b] - v[a]) * (z[i] - z[a]) >= 0:
                hull.pop()
            else:
                break
        hull.append(i)
    h = np.interp(z, z[hull], v[hull])
    k = sigma_mm / (z[1] - z[0])
    xs = np.arange(-int(4 * k), int(4 * k) + 1)
    gk = np.exp(-0.5 * (xs / k) ** 2)
    gk /= gk.sum()
    hp = np.pad(h, len(xs) // 2, mode='reflect', reflect_type='odd')
    hs = np.convolve(hp, gk, mode='valid')
    t = smoothstep(np.minimum(z - z0, z1 - z) / (3 * sigma_mm))
    hs = h + (hs - h) * t
    return lambda q: np.interp(np.asarray(q, float), z, hs)


def pole_pchip(zk, vk, H, zc0, zc1, z_s_from):
    """PCHIP in z blended over [zc0, zc1] into a PCHIP in s = sqrt(H - z) (smooth crown pole)"""
    fz = pchip(zk, vk)
    zk, vk = np.asarray(zk, float), np.asarray(vk, float)
    k = zk >= z_s_from
    fs = pchip(np.sqrt(H - zk[k])[::-1], vk[k][::-1])

    def f(z):
        z = np.asarray(z, float)
        a = fz(z)
        b = fs(np.sqrt(np.clip(H - z, 0.0, None)))
        return np.maximum(a + (b - a) * smoothstep((z - zc0) / (zc1 - zc0)), 0.0)
    return f


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


_w5 = concave_majorant(pole_pchip(WZ, WV, H5, 60.0, 66.0, 54.0), 0.0, H5)
_D5 = pole_pchip(DZ, DV, H5, 58.0, 64.0, 55.0)
Z_BAND = (ZC5 - R_TABLE * C8, ZC5 + R_TABLE * C8)
_YG = -8.5 + T8 * ZC5 - (Z_BAND[0] ** 2) / (2 * R_BEND)


def _plane5(z):
    return _YG + T8 * (np.asarray(z, float) - ZC5)


def _ys_raw5(z):
    z = np.asarray(z, float)
    bend = np.where(z < Z_BAND[0], (Z_BAND[0] - z) ** 2 / (2 * R_BEND), 0.0)
    return _plane5(z) + bend + SEAM_FRAC * _D5(z)


def sections5(z):
    """MĂRGĂRITAR sections (its own frame, unscaled): w, y_f, y_b, y_s, c, p_front"""
    z = np.atleast_1d(np.asarray(z, float))
    b0, b1 = Z_BAND
    D = _D5(z)
    w = _w5(z)
    ys = _ys_raw5(z)
    e = 0.05
    ys1 = float(_ys_raw5(np.array([b1]))[0])
    sl = float((_ys_raw5(np.array([b1])) - _ys_raw5(np.array([b1 - e])))[0]) / e
    ys = np.where(z > b1, ys1 + sl * (z - b1), ys)
    yf = ys - SEAM_FRAC * D
    yb = ys + (1 - SEAM_FRAC) * D
    fd = smoothstep(np.minimum(z - b0, b1 - z) / FADE)
    c = np.sqrt(np.maximum(R_TABLE ** 2 - ((z - ZC5) / C8) ** 2, 0.0)) * fd
    c = np.minimum(c, np.maximum(w - 0.8, 0.0))
    return w, yf, yb, ys, c, PF + (PR - PF) * fd


def _dy5():
    """y shift that centres the cut base section on the origin"""
    w, yf, yb, ys, c, pf = sections5(np.array([Z_CUT]))
    return -0.5 * float(yf[0] + yb[0])


DY5 = _dy5()


def z5(Z):
    """pilot Z -> MĂRGĂRITAR z"""
    return np.asarray(Z, float) / K + Z_CUT


def _v5_ys(Z):
    z = np.minimum(z5(Z), H5)
    return KY * (sections5(z)[3] + DY5)


def _fit_seam():
    Zs = np.linspace(0.04 * H_TOTAL, 0.96 * H_TOTAL, 80)
    A = np.vstack([np.ones_like(Zs), Zs]).T
    a, b = np.linalg.lstsq(A, _v5_ys(Zs), rcond=None)[0]
    return float(a), float(b)


def sections(Z):
    """Pilot sections at heights Z: half-width w, front y_f, back y_b, seam y_s, table half-width c, front exponent."""
    z = np.minimum(z5(Z), H5)
    w5, yf5, yb5, ys5, c5, pf = sections5(z)
    w = K * np.maximum(w5, 0.0)
    c = K * c5
    yf, yb = KY * (yf5 + DY5), KY * (yb5 + DY5)
    ysr = KY * (ys5 + DY5)
    yb = ysr + (yb - ysr) * K_BACK
    ys = SEAM_A + SEAM_B * np.asarray(Z, float)
    ys = np.clip(ys, yf + 0.05, None)
    yb = np.maximum(yb, ys + 0.05)
    return w, yf, yb, ys, c, pf


def _spow(v, e):
    return np.sign(v) * np.abs(v) ** e


def ring(Z, n_raw=1536):
    """Closed outer ring (n_raw, 2) at pilot height Z, starting at the back centre, counter-clockwise seen from +Z
    ordering: back centre -> +x seam -> front -> -x seam -> back."""
    w, yf, yb, ys, c, pf = [float(np.ravel(v)[0]) for v in sections(np.array([Z]))]
    nb = n_raw // 2
    t = np.linspace(0.5 * math.pi, 0.0, nb // 2, endpoint=False)
    back_r = np.stack([w * _spow(np.cos(t), 2 / PB), ys + (yb - ys) * _spow(np.sin(t), 2 / PB)], 1)
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
    back_l = np.stack([w * _spow(np.cos(t3), 2 / PB), ys + (yb - ys) * _spow(np.sin(t3), 2 / PB)], 1)
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
SEAM_A, SEAM_B = _fit_seam()
LEAN = math.atan(math.tan(LEAN5) * KY / K)                   # face lean after the anisotropic scale
N_OUT = np.array([0.0, -math.cos(LEAN), math.sin(LEAN)])     # outward face normal
UP = np.array([0.0, math.sin(LEAN), math.cos(LEAN)])         # in-plane up
INW = -N_OUT
G = np.array([0.0, KY * (float(_plane5(ZC5)) + DY5), (ZC5 - Z_CUT) * K])   # centre of the flat table (glass centre)
R_TAB = R_TABLE * K                                          # table radius (in x)


def table_y(Z):
    return G[1] + math.tan(LEAN) * (np.asarray(Z, float) - G[2])


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
    return resample(P, n, curv_w=0.0)


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


def poly_ring_angular(poly, n, cy=None):
    """Resample a star-shaped polygon at n uniform angles about (0, cy): consistent point correspondence between
    rings (a loft through rings resampled by arc length can twist and give a solid OCCT cannot Boolean)."""
    from shapely.geometry import LineString
    c = poly.centroid
    cx0, cy0 = 0.0, c.y if cy is None else cy
    R = 400.0
    out = []
    for a in np.linspace(0.5 * math.pi, 0.5 * math.pi + 2 * math.pi, n, endpoint=False):
        ray = LineString([(cx0, cy0), (cx0 + R * math.cos(a), cy0 + R * math.sin(a))])
        ip = poly.exterior.intersection(ray)
        pts = [ip] if ip.geom_type == 'Point' else list(getattr(ip, 'geoms', []))
        pts = [p for p in pts if p.geom_type == 'Point']
        if not pts:
            return None
        far = max(pts, key=lambda p: (p.x - cx0) ** 2 + (p.y - cy0) ** 2)
        out.append((far.x, far.y))
    return np.array(out)
