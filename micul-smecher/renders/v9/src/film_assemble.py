#!/usr/bin/env python3
"""film_assemble.py -- cut the SOUL launch film from the v9 key renders (CGI concept), silent, 24 fps, H.264.
    python3 film_assemble.py            -> ../film/soul_launch.mp4 (1920x1080) + ../film/soul_launch_vertical.mp4 (1080x1920)
Camera moves are slow 2D push-ins / pans on the rendered frames; the rise and the orbit are rendered key frames
(render_film.sh) motion-interpolated by ffmpeg (minterpolate). Title cards and the end card are drawn here.
"""
import glob
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FILM = os.path.abspath(os.path.join(HERE, '..', 'film'))
KEYS = os.path.join(FILM, 'keys')
V9 = os.path.abspath(os.path.join(HERE, '..'))
TMP = '/tmp/soul_v9_film_cut'
FPS = 24
FONT = os.environ.get('FILM_FONT', os.path.join(FILM, 'tex', 'DMSans.ttf'))   # DM Sans (OFL)
if not os.path.exists(FONT):
    FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG = (10, 10, 11)
INK = (246, 243, 236)
LOGO_SVG = os.path.join(FILM, 'tex', 'soul_logo.svg')


def font(px, weight=None):
    f = ImageFont.truetype(FONT, px)
    if weight:
        try:
            f.set_variation_by_axes([14, weight])     # DM Sans: opsz, wght
        except Exception:
            pass
    return f


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def interp_seq(name, pattern, key_fps, dur):
    """rendered keys -> motion-interpolated 24 fps frames (cached PNGs)"""
    out = os.path.join(TMP, name)
    if not os.path.isdir(out) or not os.listdir(out):
        os.makedirs(out, exist_ok=True)
        files = pattern
        lst = os.path.join(TMP, name + '.txt')
        with open(lst, 'w') as f:
            for p in files:
                f.write("file '%s'\nduration %.4f\n" % (p, 1.0 / key_fps))
            f.write("file '%s'\n" % files[-1])
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                        '-vf', 'fps=%g,minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1' % (key_fps, FPS),
                        os.path.join(out, 'f%04d.png')], check=True)
    fr = sorted(glob.glob(os.path.join(out, 'f*.png')))
    n = int(round(dur * FPS))
    idx = np.linspace(0, len(fr) - 1, n).round().astype(int)
    return [fr[i] for i in idx]


_IMC = {}


def load(p):
    if p not in _IMC:
        if len(_IMC) > 40:
            _IMC.clear()
        _IMC[p] = Image.open(p).convert('RGB')
    return _IMC[p]


def cover(im, W, H, zoom=1.0, fx=0.5, fy=0.5):
    """crop im to aspect W:H around the focus (fx, fy) at the given zoom (>= 1), resize to W x H"""
    sw, sh = im.size
    a = W / H
    cw, ch = (sh * a, sh) if sw / sh > a else (sw, sw / a)
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(fx * sw, cw / 2), sw - cw / 2)
    cy = min(max(fy * sh, ch / 2), sh - ch / 2)
    return im.transform((W, H), Image.EXTENT, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), Image.BICUBIC)


# ---------------------------------------------------------------------------------------------- segments
# each segment: function(W, H) -> list of PIL frames generator (as a callable per frame index) and a length
class Seg:
    def __init__(self, n, fn):
        self.n, self.fn = n, fn


def seg_chat(W, H, dur=3.5):
    n = int(dur * FPS)
    s = W / 1920 if W > H else W / 1080
    bw, bh = (1000 * s, 120 * s) if W > H else (900 * s, 130 * s)
    f = font(int(44 * s))

    def fr(i):
        t = i / FPS
        im = Image.new('RGB', (W, H), BG)
        a = 1.0 - ease((t - 2.4) / 1.0)
        a *= ease(t / 0.5)
        if a <= 0:
            return im
        lay = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(lay)
        x0, y0 = (W - bw) / 2, (H - bh) / 2
        d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=bh / 3.2, fill=(250, 248, 244))
        if int(t * 2) % 2 == 0:
            cx = x0 + 48 * s
            d.rectangle((cx, y0 + bh * 0.28, cx + 3 * s, y0 + bh * 0.72), fill=(30, 30, 32))
        return Image.blend(im, lay, a)
    return Seg(n, fr)


def seg_title(W, H, text, dur=3.0):
    n = int(dur * FPS)
    s = W / 1920 if W > H else W / 1080
    f = font(int((64 if W > H else 70) * s), 500)
    d0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    maxw = W * (0.78 if W > H else 0.84)
    words, lines, cur = text.split(), [], ''
    for w in words:
        t2 = (cur + ' ' + w).strip()
        if d0.textlength(t2, font=f) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t2
    lines.append(cur)
    lh = f.size * 1.25
    base = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(base)
    y = H / 2 - lh * len(lines) / 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=INK)
        y += lh
    black = Image.new('RGB', (W, H), BG)

    def fr(i):
        t = i / FPS
        a = ease(t / 0.6) * (1 - ease((t - (dur - 0.6)) / 0.6))
        return Image.blend(black, base, a)
    return Seg(n, fr)


def seg_frames(W, H, frames, z0=1.0, z1=1.06, fx=0.5, fy=0.5, fade_in=0.0, fade_out=0.0):
    n = len(frames)

    def fr(i):
        t = i / max(n - 1, 1)
        im = frames[i] if not callable(frames[i]) else frames[i]()
        if isinstance(im, str):
            im = load(im)
        out = cover(im, W, H, z0 + (z1 - z0) * ease(t), fx, fy)
        a = 1.0
        if fade_in:
            a *= ease(i / FPS / fade_in)
        if fade_out:
            a *= 1 - ease((i - (n - fade_out * FPS)) / FPS / fade_out)
        if a < 1:
            out = Image.blend(Image.new('RGB', (W, H), BG), out, a)
        return out
    return Seg(n, fr)


def xfade_list(pairs):
    """[(path, seconds), ...] -> per-frame list with 6-frame crossfades between consecutive entries"""
    out = []
    for k, (p, d) in enumerate(pairs):
        out += [p] * int(round(d * FPS))
    cf = 6
    res = list(out)
    b = 0
    for k, (p, d) in enumerate(pairs[:-1]):
        b += int(round(d * FPS))
        nxt = pairs[k + 1][0]
        for j in range(cf):
            i = b - cf // 2 + j
            if 0 <= i < len(res):
                a = (j + 1) / (cf + 1)
                res[i] = (lambda p0=p, p1=nxt, a=a: Image.blend(load(p0), load(p1), a))
    return res


def seg_end(W, H, dur=4.5):
    n = int(dur * FPS)
    import cairosvg
    import io
    lw = int(W * (0.36 if W > H else 0.62))
    png = cairosvg.svg2png(url=LOGO_SVG, output_width=lw)
    logo = Image.open(io.BytesIO(png)).convert('RGBA')
    s = W / 1920 if W > H else W / 1080
    f = font(int(34 * s), 400)
    fs = font(int(18 * s), 400)
    base = Image.new('RGB', (W, H), BG)
    base.paste(logo, ((W - logo.width) // 2, int(H / 2 - logo.height * 0.75)), logo)
    d = ImageDraw.Draw(base)
    tx = 'Designed in Romania.'
    d.text(((W - d.textlength(tx, font=f)) / 2, H / 2 + logo.height * 0.55), tx, font=f, fill=(200, 196, 188))
    note = 'CGI concept renders'
    d.text((W - d.textlength(note, font=fs) - 30 * s, H - 50 * s), note, font=fs, fill=(90, 88, 84))
    black = Image.new('RGB', (W, H), BG)

    def fr(i):
        t = i / FPS
        return Image.blend(black, base, ease(t / 0.8) * (1 - ease((t - (dur - 0.7)) / 0.7)))
    return Seg(n, fr)


def K(name):
    p = os.path.join(KEYS, name + '.png')
    if not os.path.exists(p):
        sys.exit('missing key ' + p)
    return p


def build(W, H):
    vert = H > W
    rise = interp_seq('rise', [K('f_rise_l%d' % L) for L in (60, 50, 40, 30, 20, 10, 0)], 3.0, 2.6)
    orbit = interp_seq('orbit', [K('f_orbit_a%d' % a) for a in (64, 60, 56, 52, 48, 44, 40, 36, 32, 28, 24)], 2.75, 4.0)
    segs = [
        seg_chat(W, H),
        seg_title(W, H, 'The smartest thing ever made lives in a chat box.'),
        seg_frames(W, H, rise + xfade_list([(K('f_rise_l0'), 0.4), (K('f_rise_open'), 1.1), (K('f_rise_blink'), 0.15),
                                            (K('f_rise_open'), 1.2)]),
                   1.0, 1.10, 0.5, 0.45, fade_in=0.6, fade_out=0.3),
        seg_frames(W, H, orbit, 1.0, 1.03, 0.5, 0.5, fade_out=0.5),
        seg_title(W, H, 'Hold the glass.', 2.6),
        seg_frames(W, H, xfade_list([(K('f_hand_down'), 1.8), (K('f_hand_wide'), 2.2)]), 1.0, 1.08, 0.5, 0.5, fade_in=0.4),
        seg_frames(W, H, [os.path.join(V9, 'soul_v9_typing.png')] * int(3.5 * FPS), 1.0, 1.08, 0.5, 0.45, fade_out=0.5),
        seg_title(W, H, 'Works with the AI you already have.', 2.8),
        seg_frames(W, H, xfade_list([(K('f_laptop_front'), 1.5), (K('f_laptop_wide'), 1.5), (K('f_laptop_happy'), 2.0)]),
                   1.0, 1.10, 0.62 if not vert else 0.6, 0.55, fade_in=0.4),
        seg_frames(W, H, [os.path.join(V9, 'soul_v9_family.png')] * int(4.0 * FPS), 1.04, 1.0,
                   0.5, 0.55, fade_out=0.5),
        seg_frames(W, H, xfade_list([(K('f_rise_sleepy'), 2.0), (K('f_rise_blink'), 2.2)]), 1.06, 1.12, 0.5, 0.45,
                   fade_out=1.0),
        seg_title(W, H, 'From €249 · Join the waitlist', 3.0),
        seg_end(W, H),
    ]
    return segs


def render(W, H, out):
    segs = build(W, H)
    cf = 12                       # 0.5 s crossfade between photographic segments (titles fade through black)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    total = 0
    prev_tail = None
    for k, sg in enumerate(segs):
        frames = range(sg.n)
        for i in frames:
            im = sg.fn(i)
            p.stdin.write(im.tobytes())
            total += 1
    p.stdin.close()
    p.wait()
    print('wrote', out, '%.1f s' % (total / FPS), os.path.getsize(out) // 1000, 'kB')


if __name__ == '__main__':
    os.makedirs(TMP, exist_ok=True)
    render(1920, 1080, os.path.join(FILM, 'soul_launch.mp4'))
    if '--no-vertical' not in sys.argv:
        render(1080, 1920, os.path.join(FILM, 'soul_launch_vertical.mp4'))
