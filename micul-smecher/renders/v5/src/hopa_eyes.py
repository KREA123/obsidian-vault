#!/usr/bin/env python3
"""hopa_eyes.py -- per-frame eye textures for the HOPA animation (CGI concept).

Each frame = eyes.render(**hopa_motion.eyes(t)), rotated inside the round panel by the lagged level angle
(hopa_motion.psi_lagged), so the eyes stay level while the body rocks. soul_v5.py 'hopa' maps these PNGs as an
image sequence on the (un-rotated) glass.

    python3 hopa_eyes.py [outdir]      (default: $SOUL_V5_CACHE/hopa_eyes, i.e. /tmp/soul_v5_cache/hopa_eyes)
"""
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eyes as E  # noqa: E402
import hopa_motion as HM  # noqa: E402

E.N = 512


def frame_png(f):
    t = HM.frame_time(f)
    img = E.render(color='#FFF0C8', **HM.eyes(t))
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    psi = math.degrees(HM.psi_lagged(t))
    if abs(psi) > 1e-3:
        # texture u = glass +x, v = glass +y, PNG row 0 = top => a CCW rotation seen from the front = PIL CCW
        im = im.rotate(psi, resample=Image.BICUBIC)
    return im


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.environ.get('SOUL_V5_CACHE', '/tmp/soul_v5_cache'), 'hopa_eyes')
    os.makedirs(out, exist_ok=True)
    for f in range(1, HM.NF + 1):
        frame_png(f).save(os.path.join(out, 'eyes_hopa_%04d.png' % f))
    print('wrote %d eye frames to %s' % (HM.NF, out))


if __name__ == '__main__':
    main()
