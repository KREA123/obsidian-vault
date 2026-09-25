#!/usr/bin/env python3
"""measure.py -- acceptance-check helpers for the v5 renders (CIE L* of image regions, silhouette extents).

    python3 measure.py lstar IMG x0 y0 x1 y1 [...]      mean / p95 L* of boxes (pixel coords)
    python3 measure.py sil IMG                           bounding box of the non-background object (front shots)
"""
import sys

import numpy as np
from PIL import Image


def lstar(rgb8):
    c = rgb8.astype(np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Y = 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
    f = np.where(Y > 216 / 24389, np.cbrt(Y), (24389 / 27 * Y + 16) / 116)
    return 116 * f - 16


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    im = np.asarray(Image.open(path).convert('RGB'))
    L = lstar(im)
    if cmd == 'lstar':
        a = [int(v) for v in sys.argv[3:]]
        for i in range(0, len(a), 4):
            x0, y0, x1, y1 = a[i:i + 4]
            r = L[y0:y1, x0:x1]
            print('box %s: L* mean %.1f  p5 %.1f  p50 %.1f  p95 %.1f  max %.1f' % (
                a[i:i + 4], r.mean(), np.percentile(r, 5), np.percentile(r, 50), np.percentile(r, 95), r.max()))
    elif cmd == 'sil':
        bg = np.median(np.concatenate([L[:20].ravel(), L[:, :20].ravel()]))
        m = np.abs(L - bg) > 6
        ys, xs = np.nonzero(m)
        print('object bbox x %d..%d  y %d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()))


if __name__ == '__main__':
    main()
