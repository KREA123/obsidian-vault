#!/usr/bin/env python3
"""Render soul_trailer.html frame-by-frame with Playwright and encode with ffmpeg.

usage:
  python3 render.py stills h 1.0 7.5 ...        # a few PNG stills → <frames>/still_*.png
  python3 render.py video h                     # full horizontal video → soul_trailer.mp4
  python3 render.py video v                     # vertical → soul_trailer_vertical.mp4
env: FRAMES_DIR (default /tmp/soul_frames), WORKERS (default 4), FPS (30)
"""
import os, sys, subprocess, pathlib
from multiprocessing import Process
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE / 'soul_trailer.html').as_uri()
FPS = int(os.environ.get('FPS', 30))
FR = pathlib.Path(os.environ.get('FRAMES_DIR', '/tmp/soul_frames'))
SIZE = {'h': (1920, 1080), 'v': (1080, 1920)}


def open_page(p, lay):
    w, h = SIZE[lay]
    b = p.chromium.launch(args=['--allow-file-access-from-files', '--disable-web-security', '--force-color-profile=srgb'])
    pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
    pg.on('console', lambda m: print('[page]', m.text) if m.type in ('error', 'warning') else None)
    pg.goto(PAGE + ('?v=1' if lay == 'v' else ''))
    pg.wait_for_function('window.READY === true', timeout=60000)
    return b, pg


def worker(lay, frames, outdir):
    with sync_playwright() as p:
        b, pg = open_page(p, lay)
        for f in frames:
            pg.evaluate('t => render(t)', f / FPS)
            pg.screenshot(path=str(outdir / f'f{f:05d}.png'), type='png')
        b.close()


def stills(lay, ts):
    FR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b, pg = open_page(p, lay)
        for t in ts:
            pg.evaluate('t => render(t)', float(t))
            pg.screenshot(path=str(FR / f'still_{lay}_{float(t):05.2f}.png'))
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
    procs = [Process(target=worker, args=(lay, todo[i::W], outdir)) for i in range(W)]
    [pr.start() for pr in procs]
    [pr.join() for pr in procs]
    out = HERE / ('soul_trailer.mp4' if lay == 'h' else 'soul_trailer_vertical.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(outdir / 'f%05d.png'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-tune', 'animation', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', '-r', str(FPS), str(out)], check=True)
    print('wrote', out, out.stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    cmd, lay = sys.argv[1], sys.argv[2]
    if cmd == 'stills':
        stills(lay, sys.argv[3:])
    else:
        video(lay)
