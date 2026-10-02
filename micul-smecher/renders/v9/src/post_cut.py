#!/usr/bin/env python3
"""post_cut.py -- the RGBA cut-out post for the trailer (soul_v9.py --shot cut_*): OIDN denoise of the premultiplied
colour, exposure, AgX on the UN-premultiplied colour (so the edge pixels keep the object's own colour, no dark or
light fringe), then a straight-alpha image cropped to the alpha bounding box + a margin. The projected glass outline
in <base>_glass.json is re-expressed in the cropped image's normalised coordinates.

    python3 post_cut.py /tmp/soul_cut/cut_front --out ../../../trailer/assets/soul_front.webp [--scale 1.0]
needs: numpy, OpenEXR, Pillow, PyOpenColorIO, oidn (as v5/src/post.py)
"""
import argparse
import json
import os
import sys

import numpy as np
import OpenEXR
import Imath
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v5', 'src'))
import post as P5  # noqa: E402


def read_rgba(path):
    f = OpenEXR.InputFile(path)
    dw = f.header()['dataWindow']
    w, h = dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    ch = f.header()['channels'].keys()
    out = [np.frombuffer(f.channel(c, pt), np.float32).reshape(h, w) for c in ('R', 'G', 'B')]
    a = np.frombuffer(f.channel('A', pt), np.float32).reshape(h, w) if 'A' in ch else np.ones((h, w), np.float32)
    return np.ascontiguousarray(np.stack(out, -1)), a.copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('--out', required=True)
    ap.add_argument('--margin', type=int, default=24)
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--exposure', type=float)
    ap.add_argument('--quality', type=int, default=92)
    a = ap.parse_args()
    meta = json.load(open(a.base + '.json'))
    f = meta['frames'][0]
    col, alpha = read_rgba('%s_color_%04d.exr' % (a.base, f))
    alb = P5.read_exr('%s_albedo_%04d.exr' % (a.base, f))
    nrm = P5.read_exr('%s_normal_%04d.exr' % (a.base, f))
    col = P5.denoise(col, alb, nrm)
    exp = meta.get('exposure', 0.0) if a.exposure is None else a.exposure
    alpha = np.clip(alpha, 0, 1)
    # alpha below 1/255 is noise in empty space: drop it; un-premultiply the rest
    alpha[alpha < 0.004] = 0
    un = np.where(alpha[..., None] > 0, np.maximum(col, 0) / np.maximum(alpha[..., None], 1e-4), 0)
    un = un * (2.0 ** exp)
    img = P5.agx(un, meta.get('look', 'AgX - Medium High Contrast'))
    img = np.clip(img, 0, 1)
    # bleed edge colours outward into the fully transparent area (so a resampled edge never mixes with black)
    rgb = img.copy()
    solid = alpha > 0.5
    if solid.any():
        from scipy import ndimage
        idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
        rgb = img[idx[0], idx[1]]
        rgb[solid] = img[solid]
        part = (alpha > 0) & ~solid
        rgb[part] = img[part]
    H, W = alpha.shape
    ys, xs = np.nonzero(alpha > 0.004)
    m = a.margin
    x0, x1 = max(0, xs.min() - m), min(W, xs.max() + 1 + m)
    y0, y1 = max(0, ys.min() - m), min(H, ys.max() + 1 + m)
    rgba = np.dstack([rgb, alpha])[y0:y1, x0:x1]
    out = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')
    if a.scale != 1.0:
        out = out.resize((round(out.width * a.scale), round(out.height * a.scale)), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.out.endswith('.webp'):
        out.save(a.out, 'WEBP', quality=a.quality, alpha_quality=100, method=6)
    else:
        out.save(a.out, optimize=True)
    gj = a.base + '_glass.json'
    info = dict(w=out.width, h=out.height, src=os.path.basename(a.out))
    if os.path.exists(gj):
        g = json.load(open(gj))
        cw, ch = x1 - x0, y1 - y0

        def tr(p):
            return [round((p[0] * W - x0) / cw, 5), round((p[1] * H - y0) / ch, 5)]
        souls = {}
        for k, rec in g['souls'].items():
            souls[k] = {kk: ([tr(p) for p in v] if isinstance(v[0], (list, tuple)) else tr(v)) for kk, v in rec.items()}
        info['souls'] = souls
    json.dump(info, open(os.path.splitext(a.out)[0] + '.json', 'w'))
    print('wrote', a.out, out.size, os.path.getsize(a.out) // 1024, 'KB')


if __name__ == '__main__':
    main()
