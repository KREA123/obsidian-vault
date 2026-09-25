#!/usr/bin/env python3
"""alive_eyes.py -- the 'alive' clip timeline (5 s, 24 fps): SOUL stands still, only the eyes live. CGI concept.

0.0 front . 0.75 blink . 1.2 glance left (held) . 2.3 glance right, curious . 3.35 blink . 3.7 back to the viewer,
a little lift . 4.6 settle to front (the last frame equals the first: the GIF loops seamlessly).

    python3 alive_eyes.py [outdir]    -> eyes_alive_0001.png ... + alive_frames.txt (frame -> unique eye state)
"""
import hashlib
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'v5', 'src'))
import eyes as E  # noqa: E402
from hopa_motion import smooth, blink, _lerp, FRONT  # noqa: E402

E.N = 512
FPS = 24
DUR = 5.0
NF = int(round(FPS * DUR))
LEFT = dict(FRONT, gx=-0.75, gy=-0.05, lid_top=0.22)
RIGHT = dict(FRONT, gx=0.85, gy=-0.15, lid_top=0.14, lid_tilt=0.12, scale=1.03)
UP = dict(FRONT, gx=0.05, gy=-0.30, lid_top=0.10, lid_tilt=0.13, scale=1.04)


def frame_time(f):
    return (f - 1) / FPS


def state(t):
    e = dict(FRONT)
    for (a, b, S0, S1) in ((1.20, 1.42, FRONT, LEFT), (2.30, 2.55, LEFT, RIGHT), (3.70, 3.95, RIGHT, UP),
                           (4.55, 4.85, UP, FRONT)):
        if t >= a:
            e = _lerp(S0, S1, float(smooth(a, b, t)))
    e['open_'] *= blink(t, 0.75, 0.18) * blink(t, 3.35, 0.20)
    return {k: round(float(v), 4) for k, v in e.items()}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/soul_v6_cache/alive_eyes'
    os.makedirs(out, exist_ok=True)
    rows = []
    for f in range(1, NF + 1):
        st = state(frame_time(f))
        img = E.render(color='#FFF0C8', **st)
        im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
        im.save(os.path.join(out, 'eyes_alive_%04d.png' % f))
        rows.append((f, hashlib.md5(repr(sorted(st.items())).encode()).hexdigest()[:10]))
    with open(os.path.join(out, 'alive_frames.txt'), 'w') as fh:
        for f, h in rows:
            fh.write('%d %s\n' % (f, h))
    print('wrote %d eye frames, %d unique states -> %s' % (NF, len(set(h for _, h in rows)), out))


if __name__ == '__main__':
    main()
