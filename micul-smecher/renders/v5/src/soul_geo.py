"""soul_geo.py -- pure-numpy geometry of the FINAL SOUL (HOPA, 63 x 74 x 27.1 mm), render brief v5 §2.

World frame (mm): origin = land centre on the table, +z up, the face looks toward -y, +x = viewer's right.
Used by soul_v5.py inside Blender and runnable on its own for the brief's numeric checks:
    python3 soul_geo.py            (prints rim heights, land size, plan size, silhouette ratios)

Construction (brief §2.2):
  loft L: rings at constant z; back half = superellipse 2.2, front = flat table |x| <= c(z) in the glass band +
          quarter-superellipse 2.4 roll, outside the band a superellipse 2.6; seam y_s = y_f + 0.36 D.
  sole ellipsoid E: (x/40)^2 + (y/36.9)^2 + ((z-39.4)/40)^2 <= 1, z >= 0.   Body = L n E.
  The intersection is done analytically per column: each column of the loft grid is followed down until it
  leaves E (the sole rim); below the rim the surface is E itself (great-circle meridians of the normalised
  ellipsoid), then the flat land at z = 0. The R1.5 rim bevel is a quadratic-Bezier fillet between the
  shell column and the E meridian (tangent distance R*tan(alpha/2)), and it belongs to the SOLE.
"""
import math

import numpy as np

# ---------------------------------------------------------------------------------------------
# tables (mm)
WZ = [0, 1.2, 2.2, 4, 6.3, 8, 10.5, 14, 18.5, 23, 28, 34, 40.5, 48, 55.5, 60, 63, 66, 69.5, 71.5, 73.2, 74]
WV = [6.9, 11.9, 14.7, 18.6, 22.5, 24.3, 26.0, 27.7, 28.9, 29.9, 30.6, 31.2, 31.5, 31.2, 30.4, 29.4, 28.3, 26.4,
      22.8, 19.0, 12.5, 0]
SZ = [1.9, 3, 4.5, 6.3, 8, 10.5, 14, 18.5, 23, 28, 34, 40.5, 48, 55.5, 60, 63, 66, 69.5, 71.5, 73.2, 74]
YF = [-12.5, -13.2, -13.8, -14.2, -14.4, -14.4, -14.2, -13.7, -13.1, -12.4, -11.5, -10.6, -9.6, -8.5, -7.9, -7.4,
      -7.0, -5.9, -4.7, -2.8, -1.0]
YB = [12.0, 12.4, 12.7, 12.8, 12.7, 12.4, 11.8, 11.0, 10.4, 9.9, 9.6, 9.4, 8.7, 7.6, 6.7, 5.8, 4.6, 2.7, 1.3, -0.1,
      -1.0]

LEAN = math.radians(8.0)
NRM = np.array([0.0, -math.cos(LEAN), math.sin(LEAN)])        # face normal n = (0, -0.990, 0.139)
UPV = np.array([0.0, math.sin(LEAN), math.cos(LEAN)])          # in-plane "up" of the face
GC = np.array([0.0, -10.6, 40.5])                              # glass centre G
R_TABLE = 26.2
Z_BAND = (40.5 - R_TABLE * math.cos(LEAN), 40.5 + R_TABLE * math.cos(LEAN))   # 14.56 .. 66.44
EA, EB, EC, EZ = 40.0, 36.9, 40.0, 39.4                        # sole ellipsoid
FADE = 1.5
DELTA = 1.0            # below z 8 the loft is widened by DELTA * smoothstep((8 - z) / 2)
R_BEVEL = 1.5


def pchip(xk, yk):
    """Monotone cubic (Fritsch-Carlson) interpolant; linear extrapolation with the end slopes."""
    xk = np.asarray(xk, float)
    yk = np.asarray(yk, float)
    h = np.diff(xk)
    d = np.diff(yk) / h
    n = len(xk)
    m = np.zeros(n)
    for k in range(1, n - 1):
        if d[k - 1] * d[k] <= 0:
            m[k] = 0.0
        else:
            w1 = 2 * h[k] + h[k - 1]
            w2 = h[k] + 2 * h[k - 1]
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
        lo = x <= xk[0]
        hi = x >= xk[-1]
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


_w_z = pchip(WZ, WV)
_yf_z = pchip(SZ, YF)
_yb_z = pchip(SZ, YB)
# near the crown every section closes like sqrt(74 - z): interpolate there in s = sqrt(74 - z) so the pole is
# smooth (a z-space spline meets the pole with a finite slope = a point on the crown)
_ZC0, _ZC1 = 58.0, 64.0


def _s_pchip(zk, vk):
    zk = np.asarray(zk, float)
    vk = np.asarray(vk, float)
    k = zk >= 55.0
    s = np.sqrt(74.0 - zk[k])[::-1]
    return pchip(s, vk[k][::-1])


_w_s = _s_pchip(WZ, WV)
_yf_s = _s_pchip(SZ, YF)
_yb_s = _s_pchip(SZ, YB)


def _blend(fz, fs):
    def f(z):
        z = np.asarray(z, float)
        a = fz(z)
        s = np.sqrt(np.clip(74.0 - z, 0.0, None))
        b = fs(s)
        t = smoothstep((z - _ZC0) / (_ZC1 - _ZC0))
        return a + (b - a) * t
    return f


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


_w = _blend(_w_z, _w_s)
_yf = _blend(_yf_z, _yf_s)
_yb = _blend(_yb_z, _yb_s)
# below z 1.9 the side lines continue linearly with the slope of the first two points
_sf = (YF[1] - YF[0]) / (SZ[1] - SZ[0])
_sb = (YB[1] - YB[0]) / (SZ[1] - SZ[0])


def band_fade(z):
    z = np.asarray(z, float)
    return smoothstep(np.minimum(z - Z_BAND[0], Z_BAND[1] - z) / FADE)


def sections(z):
    """w, y_f, y_b, y_s, c, p_front at heights z (arrays)."""
    z = np.asarray(z, float)
    w = np.maximum(_w(np.minimum(z, 74.0)), 0.0) + DELTA * smoothstep((8.0 - z) / 2.0)
    yf = np.where(z < SZ[0], YF[0] + _sf * (z - SZ[0]), _yf(z))
    yb = np.where(z < SZ[0], YB[0] + _sb * (z - SZ[0]), _yb(z))
    fd = band_fade(z)
    plane = -10.6 + math.tan(LEAN) * (z - 40.5)
    yf = yf + fd * (plane - yf)
    arg = R_TABLE ** 2 - ((z - 40.5) / math.cos(LEAN)) ** 2
    c = np.sqrt(np.maximum(arg, 0.0)) * fd
    ys = yf + 0.36 * (yb - yf)
    pf = 2.6 + (2.4 - 2.6) * fd
    return w, yf, yb, ys, c, pf


def _spow(v, e):
    return np.sign(v) * np.abs(v) ** e


def ring(z, n_raw=2048):
    """Dense closed ring (n_raw, 2) at height z, ordered: back centre -> +x seam -> front -> -x seam -> back."""
    w, yf, yb, ys, c, pf = [float(np.ravel(v)[0]) for v in sections(np.array([z]))]
    if w < 1e-6:
        return np.tile([0.0, ys], (n_raw, 1))
    nb = n_raw // 2
    # back half: t from pi/2 (back centre) to 0 (+x seam) ... then front, then -x
    t = np.linspace(0.5 * math.pi, 0.0, nb // 2, endpoint=False)
    back_r = np.stack([w * _spow(np.cos(t), 2 / 2.2), ys + (yb - ys) * _spow(np.sin(t), 2 / 2.2)], 1)
    nf = n_raw - nb
    if c > 1e-4:
        # +x seam -> roll -> table -> roll -> -x seam
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
    return np.vstack([back_r, front, back_l])


def resample_ring(P, n, curv_w=6.0):
    """Resample a closed ring into n points by arc length weighted with turning (denser on rolls/sides).
    Starts at P[0] (back centre)."""
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    if seg.sum() < 1e-9:
        return np.repeat(P[:1], n, 0)
    tang = np.diff(Q, axis=0)
    ang = np.arctan2(tang[:, 1], tang[:, 0])
    dth = np.abs(np.angle(np.exp(1j * (np.roll(ang, -1) - ang))))
    wgt = seg + curv_w * 0.5 * (dth + np.roll(dth, 1))
    L = np.concatenate([[0], np.cumsum(wgt)])
    s = np.linspace(0, L[-1], n, endpoint=False)
    return np.stack([np.interp(s, L, Q[:, 0]), np.interp(s, L, Q[:, 1])], 1)


def e_level(p):
    """> 0 outside the sole ellipsoid, < 0 inside (normalised radius - 1)."""
    return np.sqrt((p[..., 0] / EA) ** 2 + (p[..., 1] / EB) ** 2 + ((p[..., 2] - EZ) / EC) ** 2) - 1.0


def e_normal(p):
    g = np.stack([p[..., 0] / EA ** 2, p[..., 1] / EB ** 2, (p[..., 2] - EZ) / EC ** 2], -1)
    return g / np.linalg.norm(g, axis=-1, keepdims=True)


def to_sphere(p):
    return np.stack([p[..., 0] / EA, p[..., 1] / EB, (p[..., 2] - EZ) / EC], -1)


def from_sphere(q):
    return np.stack([q[..., 0] * EA, q[..., 1] * EB, q[..., 2] * EC + EZ], -1)


Z_LAND = -EZ / EC                     # sphere Z of the land plane (z = 0)
RHO_LAND = math.sqrt(1 - Z_LAND ** 2)  # land ellipse = (EA*RHO_LAND) x (EB*RHO_LAND) half-axes


class SoulGeo:
    """Grid of the body: NU columns around; per column: shell (from fillet top A up to the crown),
    fillet (A -> B), sole meridian (B -> land edge) and the land."""

    def __init__(self, NU=384, z_lo=-0.5, nz_fine=3000, bevel=R_BEVEL):
        self.NU = NU
        s_top = np.linspace(math.sqrt(10.0), 0.0, 1200)
        zf = np.concatenate([np.linspace(z_lo, 12.0, 1400, endpoint=False), np.linspace(12.0, 64.0, 900, endpoint=False),
                             74.0 - s_top ** 2])
        zf[-1] = 74.0
        self.zf = zf
        grid = np.zeros((len(zf), NU, 3))
        for i, z in enumerate(zf):
            if z >= 74.0 - 1e-9:
                w, yf, yb, ys, c, pf = sections(np.array([74.0]))
                grid[i, :, 0] = 0.0
                grid[i, :, 1] = float(ys[0])
            else:
                grid[i, :, :2] = resample_ring(ring(z), NU)
            grid[i, :, 2] = z
        self.grid = grid
        self._rim(bevel)

    # position of column j at height z (linear on the fine grid)
    def col_at(self, j, z):
        z = np.atleast_1d(np.asarray(z, float))
        out = np.empty((len(z), 3))
        for k in range(3):
            out[:, k] = np.interp(z, self.zf, self.grid[:, j, k])
        return out

    def _rim(self, bevel):
        NU = self.NU
        self.z_rim = np.zeros(NU)
        self.P_rim = np.zeros((NU, 3))
        for j in range(NU):
            lv = e_level(self.grid[:, j, :])
            ins = np.where(lv < 0)[0]
            i = ins[0]
            # refine between i-1 (outside) and i (inside)
            a, b = self.zf[i - 1], self.zf[i]
            for _ in range(40):
                m = 0.5 * (a + b)
                if e_level(self.col_at(j, m))[0] > 0:
                    a = m
                else:
                    b = m
            self.z_rim[j] = 0.5 * (a + b)
            self.P_rim[j] = self.col_at(j, self.z_rim[j])[0]
        # tangents at the rim: shell column going down, E meridian going toward the land
        self.A = np.zeros((NU, 3))
        self.B = np.zeros((NU, 3))
        self.zA = np.zeros(NU)
        self.alpha = np.zeros(NU)
        self.phi = np.zeros(NU)
        self.thB = np.zeros(NU)
        for j in range(NU):
            P = self.P_rim[j]
            zr = self.z_rim[j]
            # shell column tangent (pointing down)
            p_up = self.col_at(j, [zr, zr + 0.2])
            tS = p_up[0] - p_up[1]
            tS /= np.linalg.norm(tS)
            # E meridian at the azimuth of P
            q = to_sphere(P)
            phi = math.atan2(q[1], q[0])
            th = math.acos(np.clip(-q[2], -1, 1))    # polar angle measured from the bottom pole
            q2 = np.array([math.sin(th - 1e-3) * math.cos(phi), math.sin(th - 1e-3) * math.sin(phi), -math.cos(th - 1e-3)])
            tE = from_sphere(q2) - P
            tE /= np.linalg.norm(tE)
            ca = np.clip(np.dot(-tS, tE), -1, 1)    # angle between the two surfaces' in-section tangents
            alpha = math.pi - math.acos(ca)          # crease (turning) angle
            tf = bevel * math.tan(0.5 * alpha)
            tf = max(tf, 0.15)
            # A: along the shell column, arc distance tf above the rim
            zz = np.linspace(zr, zr + 6, 400)
            pc = self.col_at(j, zz)
            s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pc, axis=0), axis=1))])
            zA = float(np.interp(tf, s, zz))
            self.zA[j] = zA
            self.A[j] = self.col_at(j, zA)[0]
            # B: along the E meridian, arc distance tf below the rim
            ths = np.linspace(th, max(th - 0.3, 0.01), 400)
            qq = np.stack([np.sin(ths) * math.cos(phi), np.sin(ths) * math.sin(phi), -np.cos(ths)], 1)
            pe = from_sphere(qq)
            s2 = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pe, axis=0), axis=1))])
            thB = float(np.interp(tf, s2, ths))
            self.thB[j] = thB
            self.phi[j] = phi
            self.B[j] = from_sphere(np.array([math.sin(thB) * math.cos(phi), math.sin(thB) * math.sin(phi), -math.cos(thB)]))
            self.alpha[j] = alpha

    # ---------------------------------------------------------------------------------------
    def tau_map(self):
        """Global row parameter tau(z) in [0, 1]: arc length of the front and side silhouettes (+ a floor),
        so rows crowd where the surface turns (belly, forehead, crown)."""
        if not hasattr(self, '_tau'):
            z = self.zf
            w, yf, yb, ys, c, pf = sections(z)
            dz = np.diff(z)
            dl = np.sqrt(dz ** 2 + np.diff(w) ** 2) + np.sqrt(dz ** 2 + np.diff(yf) ** 2) + np.sqrt(dz ** 2 + np.diff(yb) ** 2)
            dl = dl + 0.6 * dz
            t = np.concatenate([[0], np.cumsum(dl)])
            self._tau = t / t[-1]
        return self._tau

    def shell_rows_tau(self, n_rows, z_top=73.999):
        """(n_rows, NU, 3): row 0 = the split line A, last row just under the crown pole."""
        tau = self.tau_map()
        t_top = float(np.interp(z_top, self.zf, tau))
        rows = np.zeros((n_rows, self.NU, 3))
        for j in range(self.NU):
            tA = float(np.interp(self.zA[j], self.zf, tau))
            tt = np.linspace(tA, t_top, n_rows)
            zz = np.interp(tt, tau, self.zf)
            rows[:, j, :] = self.col_at(j, zz)
        return rows

    def shell_rows_z(self, zs_template):
        """Rows at a template of normalised heights; zs_template in [0, 1] maps zA(u) .. crown."""
        rows = np.zeros((len(zs_template), self.NU, 3))
        for j in range(self.NU):
            z0, z1 = self.zA[j], 73.99
            rows[:, j, :] = self.col_at(j, z0 + (z1 - z0) * np.asarray(zs_template))
        return rows

    def fillet_rows(self, n=7):
        rows = np.zeros((n, self.NU, 3))
        for k, t in enumerate(np.linspace(0, 1, n)):
            rows[k] = (1 - t) ** 2 * self.A + 2 * t * (1 - t) * self.P_rim + t * t * self.B
        return rows

    def sole_rows(self, n=40):
        """E meridian from B (row 0) to the land edge (last row)."""
        th_land = math.acos(-Z_LAND)
        rows = np.zeros((n, self.NU, 3))
        for k, t in enumerate(np.linspace(0, 1, n)):
            th = self.thB + (th_land - self.thB) * t
            q = np.stack([np.sin(th) * np.cos(self.phi), np.sin(th) * np.sin(self.phi), -np.cos(th)], 1)
            rows[k] = from_sphere(q)
        rows[-1, :, 2] = 0.0
        return rows

    def land_rows(self, n=12):
        rows = np.zeros((n, self.NU, 3))
        for k, f in enumerate(np.linspace(1, 0.04, n)):
            rows[k, :, 0] = EA * RHO_LAND * f * np.cos(self.phi)
            rows[k, :, 1] = EB * RHO_LAND * f * np.sin(self.phi)
        return rows


def seam_curve(side=1, n=400, z0=None):
    """Girdle seam (side*w(z), y_s(z), z) from z0 up to the crown."""
    z0 = 6.0 if z0 is None else z0
    z = np.linspace(z0, 74.0, n)
    w, yf, yb, ys, c, pf = sections(z)
    return np.stack([side * w, ys, z], 1)


def front_silhouette(z):
    w, *_ = sections(z)
    return w


if __name__ == '__main__':
    g = SoulGeo(NU=256)
    P = g.P_rim
    az = np.degrees(np.arctan2(P[:, 1], P[:, 0]))

    def at(a):
        return int(np.argmin(np.abs(((az - a + 180) % 360) - 180)))
    print('sole rim z: front (x=0) %.2f | back %.2f | +x axis %.2f | -x axis %.2f | max %.2f (front-side corners)' % (
        g.z_rim[at(-90)], g.z_rim[at(90)], g.z_rim[at(0)], g.z_rim[at(180)], g.z_rim.max()))
    print('rim plan along the axes: %.1f x %.1f mm (bounding box %.1f x %.1f)' % (
        P[at(0), 0] - P[at(180), 0], P[at(90), 1] - P[at(-90), 1], np.ptp(P[:, 0]), np.ptp(P[:, 1])))
    print('split line A (top of the R1.5 bevel): front %.2f back %.2f' % (g.zA[at(-90)], g.zA[at(90)]))
    print('land %.2f x %.2f' % (2 * EA * RHO_LAND, 2 * EB * RHO_LAND))
    zz = np.linspace(0, 74, 7401)
    w = front_silhouette(zz)
    print('max half-width %.2f at z %.2f (%.1f %% of H)' % (w.max(), zz[np.argmax(w)], 100 * zz[np.argmax(w)] / 74))
    w18, w55 = front_silhouette(np.array([18.5, 55.5]))
    print('quarter widths %.1f / %.1f  broad-end-up %+.1f %%' % (2 * w18, 2 * w55, 100 * (w55 / w18 - 1)))
    _, yf, yb, *_ = sections(zz)
    D = yb - yf
    print('max depth %.2f at z %.1f ; depth at 40.5 %.2f ; at 60 %.2f' % (
        D.max(), zz[np.argmax(D)], float(np.interp(40.5, zz, D)), float(np.interp(60, zz, D))))
