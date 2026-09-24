#!/usr/bin/env python3
"""
gen_shapes.py -- Micul Smecher: port of the concept silhouettes to OpenSCAD.

Re-implements the exact math of the concept page (window.SHAPES):
  * Catmull-Rom sampling (crSample) and the mirror helper (sym)
  * union-of-circles/rects outline (unionOutline)
  * the same Laplacian smoothing the 3D viewer applies (cloud 14x, others 5x)
and writes shapes.scad with, for every shape:
  pts   outline in concept units, relative to the FACE centre (= board centre),
        y pointing UP, counter-clockwise, resampled by arc length
  nrm   outward unit normals (used by the loft that rounds the edges)
  rho   convex radius of curvature per point (units; 1e6 = flat/concave),
        used to clamp the fillet inset on sharp tips (drop)
  dmin  smallest distance face-centre -> outline (units)
  tip   where the metal cap sits (units, relative)
  boss  3 screw-boss directions [angle_deg, D(angle) units]; D = ray length
        from the centre to the outline. micul_smecher.scad computes the
        mm-per-unit scale k so that the board + wall AND the bosses fit.

Run:  python3 gen_shapes.py            (writes shapes.scad next to this file)
      python3 gen_shapes.py --report   (also prints a table)
The concept space is 300 x 300 SVG units (y down), exactly like the page.
"""
import math, os, sys

# ---------------------------------------------------------------- concept math
def cr_sample(P, n):
    L = len(P); out = []
    for i in range(L):
        p0, p1, p2, p3 = P[(i - 1) % L], P[i], P[(i + 1) % L], P[(i + 2) % L]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out

def sym(right):
    left = [(300 - p[0], p[1]) for p in right[1:-1]][::-1]
    return right + left

def union_outline(circles, rects, c, n):
    out = []
    for i in range(n):
        th = i / n * 2 * math.pi; dx, dy = math.cos(th), math.sin(th); best = 0
        for cx, cy, r in circles:
            fx, fy = c[0] - cx, c[1] - cy
            b = 2 * (fx * dx + fy * dy); cc = fx * fx + fy * fy - r * r; disc = b * b - 4 * cc
            if disc < 0: continue
            t = (-b + math.sqrt(disc)) / 2
            best = max(best, t)
        for x0, y0, x1, y1 in rects:
            tmin, tmax = -1e9, 1e9
            if abs(dx) < 1e-9:
                if c[0] < x0 or c[0] > x1: continue
            else:
                t0, t1 = sorted(((x0 - c[0]) / dx, (x1 - c[0]) / dx)); tmin = max(tmin, t0); tmax = min(tmax, t1)
            if abs(dy) < 1e-9:
                if c[1] < y0 or c[1] > y1: continue
            else:
                t0, t1 = sorted(((y0 - c[1]) / dy, (y1 - c[1]) / dy)); tmin = max(tmin, t0); tmax = min(tmax, t1)
            if tmax >= max(tmin, 0) and tmax > best: best = tmax
        out.append((c[0] + dx * best, c[1] + dy * best))
    return out

def smooth(P, it):  # identical to the 3D viewer's relaxation loop
    for _ in range(it):
        L = len(P)
        P = [(p[0] * 0.5 + (P[i - 1][0] + P[(i + 1) % L][0]) * 0.25,
              p[1] * 0.5 + (P[i - 1][1] + P[(i + 1) % L][1]) * 0.25) for i, p in enumerate(P)]
    return P

CLOUD = cr_sample(union_outline([[150, 118, 62], [206, 146, 48], [94, 146, 48], [236, 198, 42], [64, 198, 42], [150, 190, 50]],
                                [[64, 196, 236, 240]], [150, 178], 240), 3)
DROP = cr_sample(sym([[150, 292], [178, 288], [206, 270], [226, 240], [234, 204], [228, 168], [214, 134], [198, 100],
                      [182, 68], [168, 40], [158, 20], [150, 12]]), 10)
GEM = [(150 + 104 * math.sin(i / 120 * 2 * math.pi), 150 - 132 * math.cos(i / 120 * 2 * math.pi)) for i in range(120)]
COIN = [(150 + 124 * math.sin(i / 120 * 2 * math.pi), 150 - 124 * math.cos(i / 120 * 2 * math.pi)) for i in range(120)]

# name: (points, face [cx,cy,r], tip [x,y], smoothing iterations, resample N, label)
SHAPES = {
    'coin':  (COIN,  (150, 150, 72), (150, 26), 5, 160, 'MONEDA (medalion)'),
    'drop':  (DROP,  (150, 196, 68), (150, 12), 5, 200, 'LACRIMA (pandantiv)'),
    'gem':   (GEM,   (150, 152, 70), (150, 18), 5, 160, 'CABOCHON (piatra)'),
    'cloud': (CLOUD, (150, 166, 64), (150, 56), 14, 240, 'NOR (norul cu talpa)'),
}

# ---------------------------------------------------------------- geometry helpers
def area(P):
    return 0.5 * sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))

def resample(P, N):
    L = len(P); seg = [math.dist(P[i], P[(i + 1) % L]) for i in range(L)]; tot = sum(seg)
    out = []; acc = 0.0; i = 0
    for k in range(N):
        s = k * tot / N
        while acc + seg[i] < s: acc += seg[i]; i += 1
        t = (s - acc) / seg[i] if seg[i] else 0
        a, b = P[i], P[(i + 1) % L]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out

def normals(P):
    L = len(P); out = []
    for i in range(L):
        a, b = P[i - 1], P[(i + 1) % L]
        tx, ty = b[0] - a[0], b[1] - a[1]; n = math.hypot(tx, ty)
        out.append((ty / n, -tx / n))  # outward for CCW
    return out

def curvature_radius(P, step=2):
    L = len(P); out = []
    for i in range(L):
        a, b, c = P[i - step], P[i], P[(i + step) % L]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])  # >0 = convex (CCW)
        la, lb, lc = math.dist(a, b), math.dist(b, c), math.dist(a, c)
        if cross <= 1e-9: out.append(1e6); continue
        R = la * lb * lc / (2 * abs(cross))
        out.append(min(R, 1e6))
    return out

def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

def ray_len(P, ang):
    dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang)); best = 0
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12: continue
        t = (a[0] * ey - a[1] * ex) / den
        u = (a[0] * dy - a[1] * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9: best = max(best, t)
    return best

ROOM_CAP = 1.16   # a boss needs ~1.13 x dmin of ray length so it never drives the scale

def choose_bosses(P, name):
    """3 screw bosses. Rules: never in the USB-C sector at the bottom
    (|angle-270| < 25 deg), >= 60 deg apart, enough room (ray length, capped
    at ROOM_CAP*dmin so that extra room is not over-rewarded), then the most
    even spread (smallest largest gap between neighbouring bosses)."""
    dmin = min(seg_dist((0, 0), P[i], P[(i + 1) % len(P)]) for i in range(len(P)))
    cand = [a for a in range(0, 360, 5) if abs(a - 270) >= 25]
    D = {a: ray_len(P, a) for a in cand}
    sep = lambda a, b: min(abs(a - b), 360 - abs(a - b))
    best = None
    for i, a in enumerate(cand):
        for j in range(i + 1, len(cand)):
            b = cand[j]
            if sep(a, b) < 60: continue
            for c in cand[j + 1:]:
                if sep(a, c) < 60 or sep(b, c) < 60: continue
                s = sorted((a, b, c)); gaps = (s[1] - s[0], s[2] - s[1], 360 - s[2] + s[0])
                room = min(D[a], D[b], D[c], ROOM_CAP * dmin)
                score = (round(room / dmin / 0.02), -max(gaps), -abs(s[0] - 90))  # room quantised to 2 %
                if best is None or score > best[0]: best = (score, tuple(s))
    return [(a, D[a]) for a in best[1]]

# ---------------------------------------------------------------- build
def build():
    data = {}
    for name, (pts, face, tip, it, N, label) in SHAPES.items():
        P = smooth(list(pts), it)
        fx, fy = face[0], face[1]
        P = [(x - fx, fy - y) for (x, y) in P]  # face-centred, y up
        if area(P) < 0: P = P[::-1]
        P = resample(P, N)
        # start the list at the top point (cosmetic, stable seams)
        top = max(range(len(P)), key=lambda i: P[i][1]); P = P[top:] + P[:top]
        nrm = normals(P); rho = curvature_radius(P)
        dmin = min(seg_dist((0, 0), P[i], P[(i + 1) % len(P)]) for i in range(len(P)))
        bosses = choose_bosses(P, name)
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        data[name] = dict(P=P, nrm=nrm, rho=rho, dmin=dmin, tip=(tip[0] - fx, fy - tip[1]), bosses=bosses,
                          bbox=(min(xs), max(xs), min(ys), max(ys)), face_r=face[2], label=label)
    return data

def fmt(v): return ('%.4f' % v).rstrip('0').rstrip('.') if abs(v) < 1e5 else '1e6'

def write_scad(data, path):
    L = ['// shapes.scad -- GENERATED by gen_shapes.py. Do not edit by hand; edit gen_shapes.py and re-run.',
         '// Units: concept units (300x300 SVG space), origin = face/board centre, +y = up (towards the cap).',
         '// Each entry: [name, label, pts, nrm, rho, dmin, tip, bosses[[deg, D]], bbox[xmin,xmax,ymin,ymax], face_r]',
         '']
    for name, d in data.items():
        L.append('SH_%s = [' % name)
        L.append('  "%s", "%s",' % (name, d['label']))
        L.append('  [' + ','.join('[%s,%s]' % (fmt(x), fmt(y)) for x, y in d['P']) + '],')
        L.append('  [' + ','.join('[%s,%s]' % (fmt(x), fmt(y)) for x, y in d['nrm']) + '],')
        L.append('  [' + ','.join(fmt(r) for r in d['rho']) + '],')
        L.append('  %s,' % fmt(d['dmin']))
        L.append('  [%s,%s],' % (fmt(d['tip'][0]), fmt(d['tip'][1])))
        L.append('  [' + ','.join('[%s,%s]' % (fmt(a), fmt(D)) for a, D in d['bosses']) + '],')
        L.append('  [%s],' % ','.join(fmt(v) for v in d['bbox']))
        L.append('  %s' % fmt(d['face_r']))
        L.append('];')
        L.append('')
    L.append('function shape_data(name) = name=="coin" ? SH_coin : name=="drop" ? SH_drop : name=="gem" ? SH_gem : SH_cloud;')
    L.append('SHAPE_NAMES = ["coin","drop","gem","cloud"];')
    open(path, 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    data = build()
    write_scad(data, os.path.join(here, 'shapes.scad'))
    print('wrote', os.path.join(here, 'shapes.scad'))
    if '--report' in sys.argv:
        for n, d in data.items():
            b = d['bbox']
            print('%-6s N=%3d dmin=%6.1f  bbox W=%6.1f H=%6.1f  tip=(%.1f,%.1f)  min rho=%.1f  bosses=%s' % (
                n, len(d['P']), d['dmin'], b[1] - b[0], b[3] - b[2], d['tip'][0], d['tip'][1], min(d['rho']),
                ', '.join('%d deg D=%.1f' % (a, D) for a, D in d['bosses'])))
