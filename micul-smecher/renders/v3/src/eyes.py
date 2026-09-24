#!/usr/bin/env python3
"""eyes.py -- screen textures for the product renders.

A numpy port of the "Normal" eye of firmware/lib/Suflet/src/Face.cpp (drawEye):
two soft glowing ellipses (half-width 0.12, half-height 0.19 of the screen
diameter S, centres +-0.19 S from the middle, 0.02 S below it), a top lid that
hides 19 % of the eye height and is tilted 0.16 rad so the INNER corners are
lower (the cheeky look), a white highlight ellipse up-right in each eye and the
same quadratic halo (glowR = 0.05 S, glowA = 0.34).

Writes square PNGs (black outside the round screen) used as an emissive image
texture by suflet_scene.py.   Run:  python3 eyes.py [outdir]
"""
import math
import os
import sys

import numpy as np
from PIL import Image

N = 1024  # texture size; the real panel is 466 x 466


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def sd_ellipse(px, py, cx, cy, rx, ry):
    # iq's approximate ellipse distance (good enough for AA + halo)
    x = (px - cx) / rx
    y = (py - cy) / ry
    k0 = np.sqrt(x * x + y * y)
    k1 = np.sqrt((x / rx) ** 2 + (y / ry) ** 2) + 1e-9
    return k0 * (k0 - 1.0) / k1


def coverage(d, glowR=0.0, glowA=0.0):
    """Same alpha law as Canvas::fillSdf."""
    a = np.zeros_like(d)
    a[d <= -0.5] = 1.0
    m = (d > -0.5) & (d < 0.5)
    a[m] = 0.5 - d[m]
    if glowA > 0:
        j = m & (glowA > a)
        a[j] = a[j] + (glowA - a[j]) * (d[j] + 0.5)
        h = (d >= 0.5) & (d < glowR)
        k = 1.0 - d[h] / glowR
        a[h] = glowA * k * k
    return a


def render(color='#FFF0C8', gx=0.0, gy=0.0, lid_top=0.19, lid_tilt=0.16, open_=1.0,
           scale=1.0, glow=1.0, extra_glow=0.0):
    """Returns float RGB (N,N,3) in 0..1 (display-referred, like the panel)."""
    S = float(N)
    cx0 = cy0 = N * 0.5
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    px, py = xs + 0.5, ys + 0.5
    img = np.zeros((N, N, 3), np.float32)
    col = hexrgb(color)
    white = np.ones(3, np.float32)

    def blend(c, a):
        a = np.clip(a, 0, 1)[..., None]
        img[:] = img * (1 - a) + c * a

    glowR, glowA = 0.05 * S, 0.34 * glow
    for side in (-1, 1):
        par = 1.0 - 0.07 * gx * side
        ex = cx0 + (side * 0.19 + gx * 0.055) * S
        ey = cy0 + (0.02 + gy * 0.06) * S
        rx = 0.12 * scale * par * S
        ry = 0.19 * scale * par * S * open_
        k = math.tan(lid_tilt) * (-side)
        inv = 1.0 / math.sqrt(1 + k * k)
        yTop = ey + (-1.0 + 2.0 * lid_top) * ry
        d = sd_ellipse(px, py, ex, ey, rx, ry)
        dt = (yTop + k * (px - ex) - py) * inv
        body = np.maximum(d, dt)
        if extra_glow > 0:  # wide, faint bloom of the lit pixels behind the cover glass
            g = np.clip(1.0 - body / (0.16 * S), 0, 1) ** 3 * extra_glow
            blend(col, g)
        blend(col, coverage(body, glowR, glowA))
        hx, hy, hrx, hry = ex + rx * 0.22, ey - ry * 0.12, rx * 0.34, ry * 0.46
        hl = np.maximum(sd_ellipse(px, py, hx, hy, hrx, hry), dt)
        blend(white, coverage(hl) * 0.45)
    # the panel is round: black outside
    r = np.hypot(px - cx0, py - cy0)
    img *= np.clip((N * 0.5 - r), 0, 1)[..., None]
    return img


VARIANTS = {
    # name: kwargs  -- eye tints = the six birth tints of firmware Personality.cpp (kTints)
    'cream': dict(color='#FFF0C8'),
    'cream_look': dict(color='#FFF0C8', gx=0.35, gy=-0.25),              # glance to the camera
    'cream_front': dict(color='#FFF0C8', gx=0.1, gy=-0.1),
    'cream_down': dict(color='#FFF0C8', gx=-0.1, gy=0.45, lid_top=0.24),  # worn: looking down, calm
    'listen_up': dict(color='#FFF0C8', gx=0.1, gy=-1.0, lid_top=0.08),   # listening: looking up
    'amber_sleepy': dict(color='#FFC96B', lid_top=0.36, gy=0.2, extra_glow=0.25),  # night light
    'ice': dict(color='#D8F0FF', gx=0.25, gy=-0.15),
    'mint': dict(color='#D2FFE6', gx=0.1, gy=-0.3),
    'peach': dict(color='#FFDCC8', gx=-0.2, gy=-0.1),
    'lilac': dict(color='#E6DAFF', gx=0.2, gy=-0.25),
    'gold': dict(color='#FFD76B', gx=-0.1, gy=-0.2),
    'cream_lu': dict(color='#FFF0C8', gx=-0.15, gy=-0.2),
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
    os.makedirs(out, exist_ok=True)
    for name, kw in VARIANTS.items():
        img = render(**kw)
        Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, 'eyes_%s.png' % name))
        print('wrote', name)


if __name__ == '__main__':
    main()
