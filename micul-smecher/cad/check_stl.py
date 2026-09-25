#!/usr/bin/env python3
"""
check_stl.py -- sanity check for STL files exported by OpenSCAD (ASCII or binary).

For every file it reports: triangle count, bounding box, signed volume, number of
shells (connected components), degenerate triangles, and a manifold / edge check:
  * every undirected edge must be shared by exactly 2 triangles  (watertight, 2-manifold)
  * every directed edge must appear exactly once                 (consistent orientation)
Exit code 1 if any file fails.

Usage:  python3 check_stl.py stl/*.stl            (prints a table)
        python3 check_stl.py --json stl/*.stl     (machine readable)
"""
import json, math, struct, sys
from collections import defaultdict


def read_stl(path):
    data = open(path, 'rb').read()
    tris = []
    if data[:5].lower() == b'solid' and b'facet' in data[:512]:
        verts = []
        for line in data.decode('ascii', 'replace').splitlines():
            t = line.split()
            if t and t[0] == 'vertex':
                verts.append((float(t[1]), float(t[2]), float(t[3])))
                if len(verts) == 3:
                    tris.append(tuple(verts)); verts = []
    else:
        n = struct.unpack('<I', data[80:84])[0]
        for i in range(n):
            f = struct.unpack('<12f', data[84 + 50 * i: 84 + 50 * i + 48])
            tris.append(((f[3], f[4], f[5]), (f[6], f[7], f[8]), (f[9], f[10], f[11])))
    return tris


def check(path, eps=1e-6):
    tris = read_stl(path)
    key = lambda p: (round(p[0] / eps), round(p[1] / eps), round(p[2] / eps))
    vid = {}
    faces = []
    degenerate = 0
    for t in tris:
        ids = tuple(vid.setdefault(key(p), len(vid)) for p in t)
        if len(set(ids)) < 3:
            degenerate += 1; continue
        faces.append(ids)
    directed = defaultdict(int)
    undirected = defaultdict(int)
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            directed[(u, v)] += 1
            undirected[(min(u, v), max(u, v))] += 1
    bad_count = sum(1 for n in undirected.values() if n != 2)
    bad_orient = sum(1 for n in directed.values() if n != 1)
    # shells (union-find over vertices of the faces)
    parent = list(range(len(vid)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b, c in faces:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra; parent[find(rc)] = ra
    shells = len({find(v) for f in faces for v in f})
    vol = 0.0
    xs, ys, zs = [], [], []
    for t in tris:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = t
        vol += (x1 * (y2 * z3 - y3 * z2) - x2 * (y1 * z3 - y3 * z1) + x3 * (y1 * z2 - y2 * z1)) / 6.0
        xs += (x1, x2, x3); ys += (y1, y2, y3); zs += (z1, z2, z3)
    ok = len(tris) > 0 and bad_count == 0 and bad_orient == 0 and vol > 0
    return dict(file=path, triangles=len(tris), vertices=len(vid), degenerate=degenerate,
                non_manifold_edges=bad_count, misoriented_edges=bad_orient, shells=shells,
                volume_mm3=round(vol, 1),
                bbox_mm=[round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - min(zs), 2)] if xs else [0, 0, 0],
                ok=ok)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    res = [check(p) for p in args]
    if '--json' in sys.argv:
        print(json.dumps(res, indent=1))
    else:
        print('%-34s %8s %6s %6s %6s %5s %10s  %-22s %s' % ('file', 'tris', 'nonman', 'orient', 'degen', 'shell', 'vol mm3', 'bbox mm', 'result'))
        for r in res:
            print('%-34s %8d %6d %6d %6d %5d %10.1f  %-22s %s' % (
                r['file'].split('/')[-1], r['triangles'], r['non_manifold_edges'], r['misoriented_edges'],
                r['degenerate'], r['shells'], r['volume_mm3'], 'x'.join('%.1f' % v for v in r['bbox_mm']),
                'OK' if r['ok'] else 'FAIL'))
    sys.exit(0 if all(r['ok'] for r in res) else 1)
