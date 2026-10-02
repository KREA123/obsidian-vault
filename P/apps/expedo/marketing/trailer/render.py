#!/usr/bin/env python3
"""Render expedo_trailer.html frame-by-frame with Playwright and encode with ffmpeg (same pipeline as the SOUL trailer).

usage:
  python3 render.py stills ro h 1.0 7.5 ...     # PNG stills → $FRAMES_DIR/still_<lang><layout>_<t>.png
  python3 render.py video ro h                  # expedo_trailer_ro.mp4            (1920x1080)
  python3 render.py video en h                  # expedo_trailer_en.mp4
  python3 render.py video ro v                  # expedo_trailer_ro_vertical.mp4   (1080x1920)
  python3 render.py contact                     # expedo_trailer_contact.png (key frames, EN h + EN v + RO h)
env: FRAMES_DIR (default /tmp/claude-0/expedo_frames), WORKERS (default 4), FPS (30)
The video is written silent; audio.py adds the soundtrack and muxes it into every mp4 that exists.
"""
import os, sys, subprocess, pathlib
from multiprocessing import Process
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE / 'expedo_trailer.html').as_uri()
FPS = int(os.environ.get('FPS', 30))
FR = pathlib.Path(os.environ.get('FRAMES_DIR', '/tmp/claude-0/expedo_frames'))
SIZE = {'h': (1920, 1080), 'v': (1080, 1920)}
OUT = {('ro', 'h'): 'expedo_trailer_ro.mp4', ('en', 'h'): 'expedo_trailer_en.mp4',
       ('ro', 'v'): 'expedo_trailer_ro_vertical.mp4', ('en', 'v'): 'expedo_trailer_en_vertical.mp4'}


def open_page(p, lang, lay):
    w, h = SIZE[lay]
    b = p.chromium.launch(args=['--allow-file-access-from-files', '--force-color-profile=srgb', '--font-render-hinting=none'])
    pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
    pg.on('console', lambda m: print('[page]', m.text) if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: print('[page error]', e))
    pg.goto(f'{PAGE}?lang={lang}&layout={lay}')
    pg.wait_for_function('window.READY === true', timeout=120000)
    return b, pg


def worker(lang, lay, frames, outdir):
    with sync_playwright() as p:
        b, pg = open_page(p, lang, lay)
        for f in frames:
            pg.evaluate('t => render(t)', f / FPS)
            pg.screenshot(path=str(outdir / f'f{f:05d}.jpg'), type='jpeg', quality=95)
        b.close()


def stills(lang, lay, ts):
    FR.mkdir(parents=True, exist_ok=True)
    out = []
    with sync_playwright() as p:
        b, pg = open_page(p, lang, lay)
        for t in ts:
            pg.evaluate('t => render(t)', float(t))
            f = FR / f'still_{lang}{lay}_{float(t):05.2f}.png'
            pg.screenshot(path=str(f)); out.append(f)
        b.close()
    return out


def video(lang, lay):
    with sync_playwright() as p:
        b, pg = open_page(p, lang, lay)
        T = pg.evaluate('window.T_END')
        b.close()
    n = int(round(T * FPS))
    outdir = FR / f'{lang}{lay}'
    outdir.mkdir(parents=True, exist_ok=True)
    todo = [f for f in range(n) if not (outdir / f'f{f:05d}.jpg').exists()]
    W = int(os.environ.get('WORKERS', 4))
    procs = [Process(target=worker, args=(lang, lay, todo[i::W], outdir)) for i in range(W)]
    [pr.start() for pr in procs]
    [pr.join() for pr in procs]
    out = HERE / OUT[(lang, lay)]
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(outdir / 'f%05d.jpg'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-tune', 'animation', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', '-r', str(FPS), str(out)], check=True)
    print('wrote', out, out.stat().st_size // 1024, 'KB')


def contact():
    """Key-frame contact sheet: EN horizontal, EN vertical, RO horizontal."""
    from PIL import Image, ImageDraw, ImageFont
    ts = [1.6, 5.0, 10.0, 14.5, 17.5, 19.2, 21.0, 23.0, 26.5, 29.0, 31.6, 34.0, 37.0, 39.0, 42.5, 45.5, 48.5, 53.0]
    rows = [('en', 'h', 6), ('en', 'v', 9), ('ro', 'h', 6)]   # English first (primary), Romanian secondary
    sheets = []
    for lang, lay, cols in rows:
        fs = stills(lang, lay, ts)
        tw = 480 if lay == 'h' else 300
        ims = [Image.open(f).convert('RGB') for f in fs]
        th = int(ims[0].height * tw / ims[0].width)
        rws = (len(ims) + cols - 1) // cols
        sh = Image.new('RGB', (cols * (tw + 8) + 8, rws * (th + 30) + 8), '#0b0d12')
        d = ImageDraw.Draw(sh)
        for i, (im, t) in enumerate(zip(ims, ts)):
            x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 30)
            sh.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x + 4, y + th + 6), f'{lang.upper()} {lay}  {t:05.2f}s', fill='#aab')
        sheets.append(sh)
    W_ = max(s.width for s in sheets); H_ = sum(s.height for s in sheets)
    out = Image.new('RGB', (W_, H_), '#0b0d12'); y = 0
    for s in sheets: out.paste(s, (0, y)); y += s.height
    p = HERE / 'expedo_trailer_contact.png'
    out.save(p, optimize=True); print('wrote', p, p.stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'stills': stills(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == 'video': video(sys.argv[2], sys.argv[3])
    elif cmd == 'contact': contact()
