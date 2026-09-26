#!/usr/bin/env python3
"""film_assemble2.py -- SOUL launch film v2 (CGI concept), silent, 24 fps, H.264.
    python3 film_assemble2.py      -> ../film/soul_launch_v2.mp4 (1920x1080) + ../film/soul_launch_v2_vertical.mp4
The shots are rendered animations (film2_v9.py, every 2nd frame) interpolated to 24 fps by ffmpeg minterpolate
(small per-frame motion, so the interpolation is clean). Title cards: large, centred, <= 5 words, fade in/out.
"""
import glob
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import film_assemble as A  # noqa: E402

FILM = A.FILM
V2 = os.path.join(FILM, 'v2')
TMP = '/tmp/soul_v9_film2_cut'
FPS = 24


def shot_frames(name):
    out = os.path.join(TMP, name)
    if not (os.path.isdir(out) and os.listdir(out)):
        os.makedirs(out, exist_ok=True)
        src = sorted(glob.glob(os.path.join(V2, name, 'f*.png')))
        lst = os.path.join(TMP, name + '.txt')
        with open(lst, 'w') as f:
            for p in src:
                f.write("file '%s'\nduration %.5f\n" % (p, 2.0 / FPS))
            f.write("file '%s'\n" % src[-1])
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-vf',
                        'fps=12,minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
                        os.path.join(out, 'f%04d.png')], check=True)
    return sorted(glob.glob(os.path.join(out, 'f*.png')))


def seg_shot(W, H, name, fin=0.7, fout=0.7, fx=0.5, fy=0.5, z0=1.0, z1=1.0):
    fr = shot_frames(name)
    return A.seg_frames(W, H, fr, z0, z1, fx, fy, fade_in=fin, fade_out=fout)


def build(W, H):
    return [
        seg_shot(W, H, 's_reveal', fin=1.2, fout=0.8),
        A.seg_title(W, H, 'Lives in a chat box.', 2.8),
        seg_shot(W, H, 's_macro'),
        A.seg_title(W, H, 'Hold the glass.', 2.6),
        seg_shot(W, H, 's_eyes', z0=1.0, z1=1.02),
        A.seg_title(W, H, 'Works with your AI.', 2.8),
        seg_shot(W, H, 's_family', fx=0.5),
        A.seg_title(W, H, 'From €249.', 2.6),
        A.seg_end(W, H, 4.5),
    ]


def render(W, H, out):
    segs = build(W, H)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    n = 0
    for sg in segs:
        for i in range(sg.n):
            p.stdin.write(sg.fn(i).tobytes())
            n += 1
    p.stdin.close()
    p.wait()
    print('wrote', out, '%.1f s' % (n / FPS), os.path.getsize(out) // 1000, 'kB')


if __name__ == '__main__':
    os.makedirs(TMP, exist_ok=True)
    render(1920, 1080, os.path.join(FILM, 'soul_launch_v2.mp4'))
    render(1080, 1920, os.path.join(FILM, 'soul_launch_v2_vertical.mp4'))
