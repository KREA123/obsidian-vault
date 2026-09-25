"""alt_geo.py -- pure-numpy geometry of the two ALTERNATES (render brief v5 §4 PIATRA, §5 MĂRGĂRITAR).

Same world frame and the same section method as soul_geo.py (brief §2.2): rings at constant z, the back half a
superellipse, the front half a superellipse -- or, inside the face band, a flat table |x| <= c(z) with quarter-
superellipse rolls out to the seam -- and the seam y_s = y_f + 0.36 D on the silhouette (x = +-w).
    python3 alt_geo.py [out.png]      prints the numeric checks and draws front + side silhouettes of FINAL / A / B

PIATRA (62 x 70 x 26): front outline = two superellipses (2.6 above z 38.5, 2.4 below, clipped at z 1.2), depth
table 25 -> 26 -> 23.5 -> 21.3 -> 19 -> 17, front line y_f = -12.5 + 0.1405 (z - 1.2) (8 deg lean), front 36 % of D
exponent 3.2 / back 2.2, flat Ø52 table centred at z 38.1 for the Ø50 glass, hull ends at z 1.2 over a Ø25 zinc foot.
Above z 62 D closes with W (D/W >= 0.55 at the crown), so the crown is a round dome, not a blade.

MĂRGĂRITAR (63 x 72 x 24): half-width and depth tables (PCHIP; in sqrt(H - z) near the crown so the pole is smooth),
face leaning back 8 deg with a flat Ø56 zone for the flat Ø52 glass (centre z 38.9), bending at R150 into the chin;
back 2.2 / front 2.6 / roll 2.4 as §2.2; flat 28 x 17 land = the champagne zamak sole plate (0.5 reveal).
Above the table zone both crowns close through the seam line continued straight, y_f = y_s - 0.36 D, so the
forehead rolls into the crown (the literal R150 forehead would pinch the crown pole into a ridge).
"""
import math
import sys

import numpy as np

import soul_geo as SG

LEAN = SG.LEAN
T8 = math.tan(LEAN)
C8 = math.cos(LEAN)
NRM = SG.NRM
UPV = SG.UPV
smoothstep = SG.smoothstep
pchip = SG.pchip


def _spow(v, e):
    return np.sign(v) * np.abs(v) ** e


def concave_majorant(f, z0, z1, n=4000, sigma_mm=1.2):
    """The least concave majorant of f on [z0, z1] (removes PCHIP's small waists), lightly smoothed; as a function."""
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
    g = np.exp(-0.5 * (xs / k) ** 2)
    g /= g.sum()
    hp = np.pad(h, len(xs) // 2, mode='reflect', reflect_type='odd')
    hs = np.convolve(hp, g, mode='valid')
    # keep the ends exact (the land width and the crown pole)
    t = smoothstep(np.minimum(z - z0, z1 - z) / (3 * sigma_mm))
    hs = h + (hs - h) * t

    def g_(q):
        return np.interp(np.asarray(q, float), z, hs)
    return g_


def softmin(a, b, k=1.5):
    m = np.minimum(a, b)
    return m - k * np.log(np.exp(-(a - m) / k) + np.exp(-(b - m) / k))


def pole_pchip(zk, vk, H, zc0, zc1, z_s_from):
    """PCHIP in z, blended over [zc0, zc1] into a PCHIP in s = sqrt(H - z) (smooth pole at z = H)."""
    fz = pchip(zk, vk)
    zk = np.asarray(zk, float)
    vk = np.asarray(vk, float)
    k = zk >= z_s_from
    fs = pchip(np.sqrt(H - zk[k])[::-1], vk[k][::-1])

    def f(z):
        z = np.asarray(z, float)
        a = fz(z)
        b = fs(np.sqrt(np.clip(H - z, 0.0, None)))
        t = smoothstep((z - zc0) / (zc1 - zc0))
        return np.maximum(a + (b - a) * t, 0.0)
    return f


# ------------------------------------------------------------------------------------------------------------------
class AltBody:
    """Common section machinery. Subclasses define: H, z_bot, r_fil, zc (table centre z), r_table, r_glass, pf, pb,
    pr, w(z), D(z), plane(z) (front line inside the band) and front_extra(z) (chin bend, >= 0 toward +y)."""
    seam_frac = 0.36
    FADE = 1.5

    def band(self):
        h = self.r_table * C8
        return self.zc - h, self.zc + h

    def G(self):
        return np.array([0.0, float(self.plane(np.array([self.zc]))[0]), self.zc])

    def _ys_raw(self, z):
        return self.plane(z) + self.front_extra(z) + self.seam_frac * self.D(z)

    def sections(self, z):
        """w, y_f, y_b, y_s, c, p_front at heights z (arrays)."""
        z = np.atleast_1d(np.asarray(z, float))
        b0, b1 = self.band()
        z1 = self.z_top_line
        D = self.D(z)
        w = self.w(z)
        ys = self._ys_raw(z)
        # above z1 the seam line runs on straight (C1) and the front closes with D
        e = 0.05
        ys1 = float(self._ys_raw(np.array([z1]))[0])
        sl = float((self._ys_raw(np.array([z1])) - self._ys_raw(np.array([z1 - e])))[0]) / e
        hi = z > z1
        ys = np.where(hi, ys1 + sl * (z - z1), ys)
        yf = ys - self.seam_frac * D
        yb = ys + (1 - self.seam_frac) * D
        fd = smoothstep(np.minimum(z - b0, b1 - z) / self.FADE)
        arg = self.r_table ** 2 - ((z - self.zc) / C8) ** 2
        c = np.sqrt(np.maximum(arg, 0.0)) * fd
        c = np.minimum(c, np.maximum(w - 0.8, 0.0))
        p_front = self.pf + (self.pr - self.pf) * fd
        return w, yf, yb, ys, c, p_front

    def ring(self, z, n_raw=2048):
        w, yf, yb, ys, c, pf = [float(v[0]) for v in self.sections(np.array([z]))]
        pb = self.pb
        if w < 1e-6:
            return np.tile([0.0, ys], (n_raw, 1))
        nb = n_raw // 2
        t = np.linspace(0.5 * math.pi, 0.0, nb // 2, endpoint=False)
        back_r = np.stack([w * _spow(np.cos(t), 2 / pb), ys + (yb - ys) * _spow(np.sin(t), 2 / pb)], 1)
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
        back_l = np.stack([w * _spow(np.cos(t3), 2 / pb), ys + (yb - ys) * _spow(np.sin(t3), 2 / pb)], 1)
        return np.vstack([back_r, front, back_l])

    # --------------------------------------------------------------------------------------------------------------
    def rows(self, NU=320, n_shell=300, n_fil=7, n_cap=10):
        """(rows, n_bottom): bottom cap rings (flat, z_bot) -> fillet -> shell -> just under the crown pole.
        Returns rows (R, NU, 3), the bottom centre and the crown pole."""
        H, zb, r = self.H, self.z_bot, self.r_fil
        zf = np.concatenate([np.linspace(zb, H - 10, 1500, endpoint=False), H - np.linspace(math.sqrt(10.0), 0, 900) ** 2])
        w, yf, yb, ys, c, pf = self.sections(zf)
        dz = np.diff(zf)
        dl = (np.sqrt(dz ** 2 + np.diff(w) ** 2) + np.sqrt(dz ** 2 + np.diff(yf) ** 2) + np.sqrt(dz ** 2 + np.diff(yb) ** 2)
              + 0.6 * dz)
        tau = np.concatenate([[0], np.cumsum(dl)])
        tau /= tau[-1]
        zA = zb + r
        tA = float(np.interp(zA, zf, tau))
        tT = float(np.interp(H - 0.004, zf, tau))
        zs = np.interp(np.linspace(tA, tT, n_shell), tau, zf)
        shell = np.zeros((n_shell, NU, 3))
        for i, z in enumerate(zs):
            shell[i, :, :2] = SG.resample_ring(self.ring(z), NU)
            shell[i, :, 2] = z
        # bottom fillet: quadratic Bezier A (row zA) -> C (the wall carried down to z_bot) -> B (C moved inward r)
        Cr = SG.resample_ring(self.ring(zb), NU)
        tg = np.roll(Cr, -1, 0) - np.roll(Cr, 1, 0)
        n2 = np.stack([tg[:, 1], -tg[:, 0]], 1)
        n2 /= np.linalg.norm(n2, axis=1, keepdims=True)
        ctr = Cr.mean(0)
        if np.mean(np.einsum('ij,ij->i', n2, Cr - ctr)) < 0:
            n2 = -n2
        A = shell[0]
        C = np.column_stack([Cr, np.full(NU, zb)])
        B = np.column_stack([Cr - n2 * r, np.full(NU, zb)])
        fil = np.array([(1 - t) ** 2 * A + 2 * t * (1 - t) * C + t * t * B for t in np.linspace(0, 1, n_fil)])
        bc = B[:, :2].mean(0)
        cap = np.array([np.column_stack([bc + (B[:, :2] - bc) * f, np.full(NU, zb)]) for f in np.linspace(0.04, 1, n_cap)])
        rows = np.concatenate([cap, fil[::-1][:-1], shell], 0)
        pole = np.array([0.0, float(self.sections(np.array([H]))[3][0]), H])
        return rows, np.array([bc[0], bc[1], zb]), pole

    def seam(self, side, z0=None, n=300):
        """Girdle seam (side*w, y_s, z) with its outward normal, from z0 to the crown pole."""
        z0 = self.z_bot + self.r_fil + 1.0 if z0 is None else z0
        zs = np.unique(np.concatenate([np.linspace(z0, self.H - 4, n // 2), self.H - np.linspace(2.0, 0.0, n // 2) ** 2]))
        w, yf, yb, ys, c, pf = self.sections(zs)
        P = np.stack([side * w, ys, zs], 1)
        dw = np.gradient(w, zs)
        nrm = np.stack([np.full_like(zs, side), np.zeros_like(zs), -dw], 1)
        nrm[-1] = (0, 0, 1)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        return P, nrm


# ------------------------------------------------------------------------------------------------------------------
class Piatra(AltBody):
    name = 'PIATRA'
    H = 70.0
    z_bot = 1.2               # the hull ends 1.2 above the table (hover shadow line over the zinc foot)
    r_fil = 1.0
    zc = 38.1                 # flat Ø52 table centre
    r_table = 26.0
    r_glass = 25.0            # Ø50 x 0.7 glass
    pf = pr = 3.2
    pb = 2.2
    foot_r = 12.5             # Ø25 x 1.2 zinc foot
    foot_c = (0.0, 1.0)       # under the centre of mass (the 8 deg lean puts it ~2-3 mm behind the chin)
    DZ = [1.2, 8, 20, 38.5, 50, 62]
    DV = [25, 26, 23.5, 21.3, 19, 17]

    def __init__(self):
        self._D = pchip(self.DZ, self.DV)
        self.z_top_line = self.band()[1]
        self._W62 = 2 * float(self.w(np.array([62.0]))[0])

    def w(self, z):
        z = np.asarray(z, float)
        up = 31.0 * np.clip(1 - np.abs((z - 38.5) / 31.5) ** 2.6, 0, None) ** (1 / 2.6)
        lo = 31.0 * np.clip(1 - np.abs((38.5 - z) / 40.5) ** 2.4, 0, None) ** (1 / 2.4)
        return np.where(z >= 38.5, up, lo)

    def D(self, z):
        z = np.asarray(z, float)
        a = self._D(np.minimum(z, 62.0)) + (z > 62.0) * (z - 62.0) * ((self.DV[-1] - self.DV[-2]) / (self.DZ[-1] - self.DZ[-2]))
        W = 2 * self.w(z)
        close = softmin(17.0 * np.clip(W / self._W62, 0, None) ** 0.6, 0.62 * W, 1.2)
        t = smoothstep((z - 60.0) / 4.0)
        return np.maximum(a + (close - a) * t, 0.0) * (z < self.H)

    def plane(self, z):
        return -12.5 + T8 * (np.asarray(z, float) - 1.2)

    def front_extra(self, z):
        return np.zeros_like(np.asarray(z, float))


class Margaritar(AltBody):
    name = 'MARGARITAR'
    H = 72.0
    z_bot = 1.5               # pearl hull; the 28 x 17 zamak plate below it (z 0 - 1.0) + a 0.5 reveal
    r_fil = 0.6
    plate_t = 1.0
    zc = 38.9
    r_table = 28.0            # flat Ø56 zone; beyond it the face bends at R150 into the chin
    r_glass = 26.0            # flat Ø52 2.5D glass
    pf, pr, pb = 2.6, 2.4, 2.2
    R_BEND = 150.0
    WZ = [0, 4, 8, 18, 30, 39.6, 54, 62, 67, 70, 72]
    WV = [14.0, 21.5, 25.0, 27.5, 30.5, 31.5, 29.25, 25.5, 19.0, 11.0, 0]
    DZ = [0, 6, 12, 30, 40, 55, 62, 68, 72]
    DV = [17, 22, 24, 22, 20.5, 17.5, 16, 12, 0]

    def __init__(self):
        # PCHIP leaves a 0.2 mm waist at z 15-21 (the table's 8-18-30 run is straight): use its concave majorant
        self._w = concave_majorant(pole_pchip(self.WZ, self.WV, self.H, 60.0, 66.0, 54.0), 0.0, self.H)
        self._D = pole_pchip(self.DZ, self.DV, self.H, 58.0, 64.0, 55.0)
        b0, b1 = self.band()
        # the land is centred on the origin: y_f(0) = -D(0)/2 = -8.5
        self.yg = -8.5 + T8 * self.zc - (b0 ** 2) / (2 * self.R_BEND)
        self.z_top_line = b1

    def w(self, z):
        return self._w(z)

    def D(self, z):
        return self._D(z)

    def plane(self, z):
        return self.yg + T8 * (np.asarray(z, float) - self.zc)

    def front_extra(self, z):
        b0 = self.band()[0]
        z = np.asarray(z, float)
        return np.where(z < b0, (b0 - z) ** 2 / (2 * self.R_BEND), 0.0)


# ------------------------------------------------------------------------------------------------------------------
def silhouettes(png):
    from PIL import Image, ImageDraw
    s = 5.0
    im = Image.new('RGB', (int(6 * 90 * s), int(100 * s)), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    def poly(pts, ox, col):
        dr.polygon([(ox + x * s, (90 - z) * s) for x, z in pts], fill=col)

    zz = np.linspace(0, 74, 600)
    w, yf, yb, ys, c, pf = SG.sections(zz)
    bodies = [('FINAL', zz, w, yf, yb, 0.0)]
    for B in (Piatra(), Margaritar()):
        z = np.linspace(B.z_bot, B.H, 600)
        w, yf, yb, ys, c, pf = B.sections(z)
        bodies.append((B.name, z, w, yf, yb, B.z_bot))
    for i, (nm, z, w, yf, yb, zb) in enumerate(bodies):
        ox = (2 * i + 0.5) * 90 * s
        poly(list(zip(w, z)) + list(zip(-w[::-1], z[::-1])), ox, (40, 40, 40))
        ox2 = (2 * i + 1.5) * 90 * s
        poly(list(zip(yb, z)) + list(zip(yf[::-1], z[::-1])), ox2, (40, 40, 40))
        dr.text((ox - 40, 5), nm, fill=(0, 0, 0))
        dr.line([(ox - 45 * s, 90 * s), (ox2 + 45 * s, 90 * s)], fill=(200, 0, 0))
    im.save(png)
    print('wrote', png)


if __name__ == '__main__':
    for B in (Piatra(), Margaritar()):
        zz = np.linspace(B.z_bot, B.H, 7001)
        w, yf, yb, ys, c, pf = B.sections(zz)
        D = yb - yf
        b0, b1 = B.band()
        G = B.G()
        print('%s: H %.1f  max W %.2f at z %.1f  max D %.2f at z %.1f  band z %.2f-%.2f  G (%.2f, %.2f, %.2f)' % (
            B.name, B.H, 2 * w.max(), zz[np.argmax(w)], D.max(), zz[np.argmax(D)], b0, b1, *G))
        for zq in (B.z_bot, 5, 10, 20, 30, 38.5, 50, 60, 64, 66, 68, 69, 70, 71):
            if zq > B.H:
                continue
            q = [float(v[0]) for v in B.sections(np.array([zq]))]
            print('   z %5.1f  W %5.2f  D %5.2f  y_f %6.2f  y_b %6.2f  y_s %6.2f  c %5.2f  D/W %.2f' % (
                zq, 2 * q[0], q[2] - q[1], q[1], q[2], q[3], q[4], (q[2] - q[1]) / max(2 * q[0], 1e-6)))
        # table flatness: the front at x = 0 inside the band vs the plane
        zb_ = np.linspace(b0 + 2, b1 - 2, 200)
        _, yfb, *_ = B.sections(zb_)
        print('   table flatness (max |y_f - plane|) %.4f mm' % np.max(np.abs(yfb - B.plane(zb_))))
        wg = B.w(np.array([B.zc - B.r_glass * C8 + 0.5, B.zc, B.zc + B.r_glass * C8 - 0.5]))
        print('   glass Ø%.0f: bottom edge z %.2f, top edge z %.2f' % (2 * B.r_glass, B.zc - B.r_glass * C8,
                                                                     B.zc + B.r_glass * C8))
    silhouettes(sys.argv[1] if len(sys.argv) > 1 else '/tmp/alt_sil.png')
