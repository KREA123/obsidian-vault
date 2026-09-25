#!/usr/bin/env python3
"""stl_fix.py -- make exported STL meshes watertight/manifold (pymeshfix) when the B-rep tessellation leaves
non-manifold edges where two faces meet tangentially. Usage: python3 stl_fix.py a.stl b.stl ..."""
import sys
import numpy as np
import trimesh
import pymeshfix

for fn in sys.argv[1:]:
    m = trimesh.load(fn)
    m.merge_vertices()
    if m.is_watertight and m.is_winding_consistent:
        print(fn, 'ok')
        continue
    v0 = m.volume
    mf = pymeshfix.MeshFix(np.asarray(m.vertices), np.asarray(m.faces))
    mf.repair(joincomp=True, remove_smallest_components=False)
    r = trimesh.Trimesh(mf.points, mf.faces)
    trimesh.repair.fix_normals(r)
    print(fn, 'fixed' if r.is_watertight else 'STILL OPEN', 'vol %.0f -> %.0f' % (v0, r.volume), len(m.faces), '->', len(r.faces))
    if r.is_watertight and abs(r.volume - v0) < 0.05 * abs(v0) + 50:
        r.export(fn)
