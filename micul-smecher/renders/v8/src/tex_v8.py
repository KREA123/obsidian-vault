#!/usr/bin/env python3
"""tex_v8.py -- the SoulOS keyboard screenshot (os/screenshots/soulos3-EN-keyboard-hello-1440.png, English UI, a 660 x 755 capture of
the whole device) cropped to its round screen and resampled to a 1024 x 1024 screen texture (the circle fills the
square, black outside), so it maps onto the glass exactly like the v5/v6 eye textures.
    python3 tex_v8.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'os', 'screenshots', 'soulos3-EN-keyboard-hello-1440.png'))
OUT = os.path.join(HERE, 'tex', 'kbd_soulos3.png')


def main():
    im = Image.open(SRC).convert('RGB')
    a = np.asarray(im).astype(int)
    dark = a.sum(2) < 60
    ys, xs = np.nonzero(dark)
    cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
    r = min(xs.max() - xs.min(), ys.max() - ys.min()) / 2.0 - 1.0      # just inside the mockup's bezel line
    box = (cx - r, cy - r, cx + r, cy + r)
    N = 1024
    sq = im.transform((N, N), Image.EXTENT, box, resample=Image.BICUBIC)
    sq = sq.resize((N, N), Image.LANCZOS)
    b = np.asarray(sq).astype(np.float32)
    yy, xx = np.mgrid[0:N, 0:N]
    d = np.hypot(xx - (N - 1) / 2, yy - (N - 1) / 2) / (N / 2)
    m = np.clip((1.0 - d) * N / 2 / 2.0, 0, 1)[..., None]           # 2 px soft edge
    b = b * m
    # the mockup bakes a faint grey glass sheen into the upper left of the screen: crush everything that is dark
    # and neutral to true black (the glass is black where the pixels are black); UI text and keys survive
    lum = b.mean(2, keepdims=True)
    sat = b.max(2, keepdims=True) - b.min(2, keepdims=True)
    t = np.clip((np.maximum(lum, sat * 3) - 26.0) / 22.0, 0, 1)
    b = b * (t * t * (3 - 2 * t))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    Image.fromarray(b.clip(0, 255).astype(np.uint8)).save(OUT)
    print('screen circle c=(%.1f, %.1f) r=%.1f px -> %s' % (cx, cy, r, OUT))


if __name__ == '__main__':
    main()
