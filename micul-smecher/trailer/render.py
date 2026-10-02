#!/usr/bin/env python3
"""Render soul_trailer.html (v4) frame by frame with Playwright and encode with ffmpeg.

Deterministic: the page preloads + decode()s every image and waits for document.fonts.ready before READY; each frame
is render(t), then two requestAnimationFrame ticks, then a lossless PNG screenshot. Frames are checked for count
before encoding (H.264 CRF 16, yuv420p, no -tune animation).

usage:
  python3 render.py stills h 1.0 7.5 ...        # PNG stills -> $FRAMES_DIR/still_h_01.00.png
  python3 render.py video h                     # horizontal -> soul_trailer.mp4
  python3 render.py video v                     # vertical   -> soul_trailer_vertical.mp4
env: FRAMES_DIR (default /tmp/soul_frames), WORKERS (default 4), FPS (30), ASSETS (asset dir, default assets/),
     KEEP_FRAMES=1 keeps the PNGs (default: deleted after encoding)
"""
import os
import sys
import shutil
import subprocess
import pathlib
from multiprocessing import Process
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE / 'soul_trailer.html').as_uri()
FPS = int(os.environ.get('FPS', 30))
FR = pathlib.Path(os.environ.get('FRAMES_DIR', '/tmp/soul_frames'))
SIZE = {'h': (1920, 1080), 'v': (1080, 1920)}
RAF2 = '() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))'


def open_page(p, lay):
    w, h = SIZE[lay]
    b = p.chromium.launch(args=['--allow-file-access-from-files', '--force-color-profile=srgb', '--disable-gpu-vsync',
                                '--hide-scrollbars'])
    pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
    pg.on('console', lambda m: print('[page]', m.text) if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: print('[page error]', e))
    q = ['v=1'] if lay == 'v' else []
    if os.environ.get('ASSETS'):
        q.append('a=' + os.environ['ASSETS'])
    pg.goto(PAGE + ('?' + '&'.join(q) if q else ''))
    pg.wait_for_function('window.READY === true', timeout=120000)
    return b, pg


def shot(pg, t, path):
    pg.evaluate('t => render(t)', float(t))
    pg.evaluate(RAF2)
    pg.screenshot(path=str(path), type='png')


def worker(lay, frames, outdir):
    with sync_playwright() as p:
        b, pg = open_page(p, lay)
        for f in frames:
            shot(pg, f / FPS, outdir / f'f{f:05d}.png')
        b.close()


def stills(lay, ts):
    FR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b, pg = open_page(p, lay)
        for t in ts:
            shot(pg, t, FR / f'still_{lay}_{float(t):05.2f}.png')
        b.close()


def video(lay):
    with sync_playwright() as p:
        b, pg = open_page(p, lay)
        T = pg.evaluate('window.T_END')
        b.close()
    n = int(round(T * FPS))
    outdir = FR / lay
    outdir.mkdir(parents=True, exist_ok=True)
    todo = [f for f in range(n) if not (outdir / f'f{f:05d}.png').exists()]
    W = int(os.environ.get('WORKERS', 4))
    # contiguous chunks per worker (each page keeps a warm cache of the scene it is in)
    k = (len(todo) + W - 1) // W
    procs = [Process(target=worker, args=(lay, todo[i * k:(i + 1) * k], outdir)) for i in range(W)]
    [pr.start() for pr in procs]
    [pr.join() for pr in procs]
    have = sorted(outdir.glob('f*.png'))
    assert len(have) == n, f'expected {n} frames, have {len(have)}'
    out = HERE / ('soul_trailer.mp4' if lay == 'h' else 'soul_trailer_vertical.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(outdir / 'f%05d.png'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                    '-movflags', '+faststart', '-r', str(FPS), str(out)], check=True)
    print('wrote', out, out.stat().st_size // 1024, 'KB', n, 'frames')
    if not os.environ.get('KEEP_FRAMES'):
        shutil.rmtree(outdir)


if __name__ == '__main__':
    cmd, lay = sys.argv[1], sys.argv[2]
    if cmd == 'stills':
        stills(lay, sys.argv[3:])
    else:
        video(lay)
