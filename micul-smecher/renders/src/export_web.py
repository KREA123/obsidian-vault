#!/usr/bin/env python3
"""Export web-sized copies of the product renders for the landing page.

    python3 renders/src/export_web.py                 # writes site/media/render-*.jpg
    python3 renders/src/export_web.py --cad-hires     # also re-renders the CAD exploded view at 1500 px

Each image is cropped for its slot on the page and saved twice: a full version
(max 1600 px wide) and a small one (half width, name-sm.jpg) for phones, both progressive JPEG
under 400 KB. Paths are relative to the micul-smecher folder, so it runs from anywhere.
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REN = os.path.join(ROOT, 'renders')
CAD = os.path.join(ROOT, 'cad')
OUT = os.path.join(ROOT, 'site', 'media')
MAX_BYTES = 400 * 1024

# name, source file, crop box (x0, y0, x1, y1) on the 1600x1200 render or None, full width
JOBS = [
    ('render-hero',   'suflet_hero.png',   None,                     1600),  # 4:3
    ('render-lineup', 'suflet_lineup.png', (0, 170, 1600, 970),      1600),  # 2:1 band with the four shapes
    ('render-night',  'suflet_night.png',  (0, 90, 1600, 990),       1600),  # 16:9, headroom for the ring
    ('render-desk',   'suflet_desk.png',   (0, 250, 1600, 1150),     1600),  # 16:9
    ('render-bag',    'suflet_bag.png',    (220, 0, 1180, 1200),      960),  # 4:5 portrait
]


def save_jpg(im, path, q=88):
    while True:
        im.save(path, 'JPEG', quality=q, optimize=True, progressive=True, subsampling='4:2:0')
        if os.path.getsize(path) <= MAX_BYTES or q <= 60:
            return q
        q -= 4


def export(name, im, full_w, q=88):
    out = []
    for w, suffix in ((full_w, ''), (full_w // 2, '-sm')):
        w = min(w, im.width)
        h = round(im.height * w / im.width)
        path = os.path.join(OUT, '%s%s.jpg' % (name, suffix))
        qq = save_jpg(im.resize((w, h), Image.LANCZOS) if w != im.width else im, path, q)
        out.append((os.path.relpath(path, ROOT), w, h, os.path.getsize(path) // 1024, qq))
    return out


def cad_exploded(hires):
    """CAD exploded view of the 1.43 coin (Founders Desk build: USB-C, no battery), cropped to 4:5.

    The 900 px fallback in cad/renders/ still shows the battery build; run with --cad-hires once."""
    src = os.path.join(CAD, 'renders', 'ms143_coin_exploded.png')
    tmp = os.path.join(tempfile.gettempdir(), 'suflet_exploded_nobat_1500.png')
    if not hires and os.path.exists(tmp):
        src = tmp  # reuse the last high-res render
    if hires:
        cmd = ['xvfb-run', '-a', '-s', '-screen 0 1600x1600x24', 'openscad', '-o', tmp,
               '-D', 'board="1.43"', '-D', 'shape="coin"', '-D', 'part="exploded"', '-D', 'battery=false',
               '--colorscheme=Tomorrow', '--imgsize=1500,1500', '--viewall', '--autocenter',
               '--camera=0,0,0,68,0,28,0', os.path.join(CAD, 'micul_smecher.scad')]
        subprocess.run(cmd, check=True, capture_output=True)
        src = tmp
    im = Image.open(src).convert('RGB')
    bg = im.getpixel((4, 4))
    diff = Image.eval(im.convert('L'), lambda v: 255 if abs(v - sum(bg) // 3) > 4 else 0)
    x0, y0, x1, y1 = diff.getbbox()
    m = round(0.08 * (y1 - y0))
    y0, y1 = max(0, y0 - m), min(im.height, y1 + m)
    w = round((y1 - y0) * 4 / 5)
    cx = (x0 + x1) // 2
    x0 = max(0, min(im.width - w, cx - w // 2))
    return im.crop((x0, y0, x0 + w, y1))


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for name, src, box, w in JOBS:
        p = os.path.join(REN, src)
        if not os.path.exists(p):
            print('skip (missing)', src)
            continue
        im = Image.open(p).convert('RGB')
        if box:
            im = im.crop(box)
        rows += export(name, im, w)
    inside = cad_exploded('--cad-hires' in sys.argv)
    rows += export('render-inside', inside, min(inside.width, 1000), q=90)
    for r in rows:
        print('%-36s %5dx%-5d %4d KB  q%d' % r)


if __name__ == '__main__':
    main()
