#!/usr/bin/env python3
"""compose_v9.py -- post steps for v9 (no rendering):
    python3 compose_v9.py vs V8_FRONT.png V9_FRONT.png      -> ../soul_v9_vs_v8.png (same camera = same scale)
    python3 compose_v9.py site                              -> ../../../site/media/soul-m-*.jpg (+ -sm), same names,
                                                               sizes, crops and JPEG settings as the v8 set
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))
SITE = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'site', 'media'))
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_L = '/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf'


def vs(p8, p9):
    a, b = Image.open(p8).convert('RGB'), Image.open(p9).convert('RGB')
    W, H = a.size
    # crop the same window from both (the product sits in the middle of the 1600 x 1600 front frame)
    box = (int(W * 0.17), int(H * 0.12), int(W * 0.83), int(H * 0.90))
    a, b = a.crop(box), b.crop(box)
    w, h = a.size
    pad, top, bot = 40, 20, 150
    im = Image.new('RGB', (2 * w + pad, h + top + bot), a.getpixel((5, 5)))
    im.paste(a, (0, top))
    im.paste(b, (w + pad, top))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT, 40)
    f2 = ImageFont.truetype(FONT_L, 28)
    f3 = ImageFont.truetype(FONT_L, 22)
    col = (70, 66, 62)
    for x0, t1, t2 in ((0, 'v8 · HOPA', '90,0 × 103,1 × 31,5 mm · sticlă Ø74,3'),
                       (w + pad, 'v9 · MĂRGĂRITAR (final)', '90,0 × 101,1 × 31,5 mm · sticlă Ø74,3')):
        for txt, fnt, y in ((t1, f1, h + top + 22), (t2, f2, h + top + 80)):
            tw = d.textlength(txt, font=fnt)
            d.text((x0 + (w - tw) / 2, y), txt, font=fnt, fill=col)
    note = 'randare / concept (CGI) · aceeași cameră, aceeași scară, vedere din față'
    d.text((im.width - d.textlength(note, font=f3) - 24, im.height - 34), note, font=f3, fill=(120, 114, 108))
    out = os.path.join(OUT, 'soul_v9_vs_v8.png')
    im.save(out)
    print('wrote', out, im.size)


# name: (source png, crop box in the source or None, full size)   -- the crops of the v8 site set
SITE_SET = {
    'hero': ('soul_v9_hero.png', None, (1600, 1200)),
    'family': ('soul_v9_family.png', None, (1600, 900)),
    'hand': ('soul_v9_hand.png', None, (1600, 1200)),
    'desk': ('soul_v9_desk.png', (0, 152, 1600, 1052), (1600, 900)),
    'typing': ('soul_v9_typing.png', (0, 136, 1600, 1036), (1600, 900)),
    'ou-night': ('soul_v9_ou_night.png', (320, 0, 1280, 1200), (960, 1200)),
    'side': ('soul_v9_side.png', (370, 0, 1330, 1200), (960, 1200)),
}


def site():
    for k, (src, box, size) in SITE_SET.items():
        im = Image.open(os.path.join(OUT, src)).convert('RGB')
        if box:
            im = im.crop(box)
        full = im.resize(size, Image.LANCZOS)
        sm = im.resize((size[0] // 2, size[1] // 2), Image.LANCZOS)
        for nm, img in (('soul-m-%s.jpg' % k, full), ('soul-m-%s-sm.jpg' % k, sm)):
            p = os.path.join(SITE, nm)
            img.save(p, 'JPEG', quality=90, subsampling=0, optimize=True, progressive=True)
            print('wrote', p, img.size, os.path.getsize(p) // 1000, 'kB')


if __name__ == '__main__':
    if sys.argv[1] == 'vs':
        vs(sys.argv[2], sys.argv[3])
    else:
        site()
