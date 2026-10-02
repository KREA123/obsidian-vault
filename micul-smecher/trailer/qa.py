#!/usr/bin/env python3
"""qa.py -- QA for the rendered trailer (v4).

  python3 qa.py diff soul_trailer.mp4             frame-to-frame difference: single-frame spikes (glitches / flicker)
                                                  and exact duplicates (dropped / repeated frames)
  python3 qa.py cuts soul_trailer.mp4 OUTDIR      10 fps contact sheets of +-0.7 s around every cut and VO line
  python3 qa.py contact soul_trailer.mp4 OUT.png  one-frame-per-second contact sheet
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

BEAT = 7.004 / 16
CUTS = [12, 20, 28, 36, 40, 44, 50, 56, 64, 74, 80, 92, 102]
EXTRA = [6, 17, 24, 60, 68.3, 99]


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_frames,r_frame_rate',
                          '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip().split(',')
    w, h, fr, n = int(out[0]), int(out[1]), out[2], int(out[3])
    a, c = fr.split('/')
    return w, h, float(a) / float(c), n


def frames(path, w, h):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE)
    sz = w * h * 3
    while True:
        b = p.stdout.read(sz)
        if len(b) < sz:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3).astype(np.float32)


def diff(path):
    W, H, fps, n = probe(path)
    w, h = (240, 135) if W > H else (135, 240)
    d, prev = [], None
    for f in frames(path, w, h):
        if prev is not None:
            d.append(np.abs(f - prev).mean())
        prev = f
    d = np.array(d)
    print(f'{path}: {n} frames @ {fps:g} fps, {W}x{H}; mean diff {d.mean():.2f}, max {d.max():.2f}')
    dup = np.nonzero(d == 0)[0]
    print(f'  exact duplicate frames: {len(dup)}', (dup[:20] + 1).tolist())
    # single-frame glitch: frame i differs from both neighbours a lot, while i-1 and i+1 are close to each other
    bad = []
    fr = list(frames(path, w, h))
    for i in range(1, len(fr) - 1):
        a, b_, c = fr[i - 1], fr[i], fr[i + 1]
        dab, dbc, dac = np.abs(b_ - a).mean(), np.abs(c - b_).mean(), np.abs(c - a).mean()
        if min(dab, dbc) > 2.5 and dac < .5 * min(dab, dbc):
            bad.append((i, round(i / fps, 2), round(float(dab), 2), round(float(dac), 2)))
    print(f'  single-frame outliers (frame, t, d_in, d_skip): {len(bad)}', bad[:30])
    # spikes relative to the local median (cuts are expected on the beat grid)
    med = np.array([np.median(d[max(0, i - 6):i + 7]) for i in range(len(d))])
    sp = [(i + 1, round((i + 1) / fps, 2), round(float(d[i]), 1)) for i in range(len(d)) if d[i] > 4 * med[i] + 3]
    cutf = {round(c * BEAT * fps) for c in CUTS}
    print('  diff spikes (frame, t, diff):', [(f, t, v, 'cut' if any(abs(f - c) <= 2 for c in cutf) else '') for f, t, v in sp])
    return d


def sheet(imgs, labels, cols, tw):
    th = int(imgs[0].height * tw / imgs[0].width)
    rows = (len(imgs) + cols - 1) // cols
    o = Image.new('RGB', (cols * tw, rows * (th + 16)), 'white')
    dr = ImageDraw.Draw(o)
    for i, (im, lb) in enumerate(zip(imgs, labels)):
        x, y = (i % cols) * tw, (i // cols) * (th + 16)
        o.paste(im.resize((tw, th), Image.LANCZOS), (x, y + 16))
        dr.text((x + 3, y + 2), lb, fill='red')
    return o


def grab(path, t0, dur, fps):
    W, H, _, _ = probe(path)
    w, h = (480, 270) if W > H else (216, 384)
    p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t0):.3f}', '-t', f'{dur:.3f}', '-i', path, '-vf', f'fps={fps},scale={w}:{h}',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    n = len(p) // (w * h * 3)
    return [Image.fromarray(np.frombuffer(p[i * w * h * 3:(i + 1) * w * h * 3], np.uint8).reshape(h, w, 3)) for i in range(n)]


def cuts(path, outdir):
    import os
    os.makedirs(outdir, exist_ok=True)
    for c in sorted(CUTS + EXTRA):
        t = c * BEAT
        ims = grab(path, t - .7, 1.4, 10)
        labels = [f'{t - .7 + i / 10:.2f}s' for i in range(len(ims))]
        W, H, _, _ = probe(path)
        sheet(ims, labels, 7 if W > H else 14, 360 if W > H else 150).save(f'{outdir}/cut_b{c:05.1f}.png')
    print('sheets ->', outdir)


def contact(path, out):
    W, H, fps, n = probe(path)
    ims = grab(path, 0, n / fps, 1)
    sheet(ims, [f'{i}s' for i in range(len(ims))], 8 if W > H else 12, 320 if W > H else 160).save(out)
    print('contact ->', out)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'diff':
        diff(sys.argv[2])
    elif cmd == 'cuts':
        cuts(sys.argv[2], sys.argv[3])
    else:
        contact(sys.argv[2], sys.argv[3])
