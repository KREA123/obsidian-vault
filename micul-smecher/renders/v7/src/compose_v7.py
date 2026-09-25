#!/usr/bin/env python3
"""compose_v7.py -- assemble the v7 size study from the post-processed renders in TMP:
  soul_v7_hands.png   hands_S | hands_M | hands_L side by side (same hand, same camera) + a caption strip
  soul_v7_lineup.png  lineup with subtle labels under each SOUL (positions from the render's annot json)
  soul_v7_typing.png  typing, with the CGI note
    python3 compose_v7.py TMP OUT [--preview]
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'firmware', 'tools', 'fonts'))
INK = (92, 84, 76)
INK2 = (140, 131, 121)
CGI = 'randare / concept (CGI)'
SIZES = [('S', '1,75″ AMOLED rotund · 466×466', '63 × 72 × 27 mm', 'ecranul de azi, Ø43,8 · taste 4,1 mm'),
         ('M', '2,8″ IPS rotund · 480×480', '93 × 106 × 31 mm', 'Ø71,1 · taste 6,7 mm'),
         ('L', '3,4″ IPS rotund · 800×800', '112 × 129 × 34 mm', 'Ø86,4 · taste 8,2 mm')]


def font(sz, bold=False):
    return ImageFont.truetype(os.path.join(FONTS, 'Nunito-Bold.ttf' if bold else 'Nunito-SemiBold.ttf'), sz)


def cgi_note(im, scale=1.0):
    d = ImageDraw.Draw(im)
    f = font(int(20 * scale))
    w = d.textlength(CGI, font=f)
    d.text((im.width - w - 24 * scale, im.height - 38 * scale), CGI, font=f, fill=INK2)


def centred(d, x, y, txt, f, fill):
    w = d.textlength(txt, font=f)
    d.text((x - w / 2, y), txt, font=f, fill=fill)


def hands(tmp, out, sfx):
    ims = [Image.open(os.path.join(tmp, 'hands_%s%s.png' % (s, sfx))).convert('RGB') for s, *_ in SIZES]
    w, h = ims[0].size
    k = w / 800.0
    strip = int(150 * k)
    o = Image.new('RGB', (w * 3, h + strip), ims[0].getpixel((w // 2, h - 2)))
    for i, im in enumerate(ims):
        o.paste(im, (i * w, 0))
    d = ImageDraw.Draw(o)
    bg = ims[0].getpixel((w // 2, h - 2))
    d.rectangle((0, h, 3 * w, h + strip), fill=tuple(int(c * 0.985) for c in bg))
    for i, (s, panel, dims, note) in enumerate(SIZES):
        cx = i * w + w / 2
        centred(d, cx, h + 16 * k, s, font(int(40 * k), True), INK)
        centred(d, cx, h + 66 * k, panel + '  ·  ' + dims, font(int(21 * k)), INK)
        centred(d, cx, h + 98 * k, note, font(int(19 * k)), INK2)
    cgi_note(o, k)
    o.save(os.path.join(out, 'soul_v7_hands%s.png' % sfx))


def lineup(tmp, out, sfx):
    im = Image.open(os.path.join(tmp, 'lineup%s.png' % sfx)).convert('RGB')
    meta = json.load(open(os.path.join(tmp, 'lineup%s.json' % sfx)))
    k = im.width / 2000.0
    d = ImageDraw.Draw(im)
    for an in meta['annot']:
        s, panel, dims = an['label'].split('|')
        x, y = an['a'][0] * im.width, an['a'][1] * im.height
        centred(d, x, y + 10 * k, s, font(int(34 * k), True), INK)
        centred(d, x, y + 56 * k, panel, font(int(19 * k)), INK2)
        centred(d, x, y + 82 * k, dims, font(int(19 * k)), INK2)
    cgi_note(im, k)
    im.save(os.path.join(out, 'soul_v7_lineup%s.png' % sfx))


def typing(tmp, out, sfx):
    im = Image.open(os.path.join(tmp, 'typing%s.png' % sfx)).convert('RGB')
    k = im.width / 1600.0
    d = ImageDraw.Draw(im)
    d.text((28 * k, im.height - 64 * k), 'M · 2,8″ IPS · 93 × 106 × 31 mm · tastatura SoulOS la scară: taste de 6,7 mm',
           font=font(int(21 * k)), fill=INK2)
    cgi_note(im, k)
    im.save(os.path.join(out, 'soul_v7_typing%s.png' % sfx))


if __name__ == '__main__':
    tmp, out = sys.argv[1], sys.argv[2]
    sfx = '_preview' if '--preview' in sys.argv else ''
    for fn, need in ((hands, 'hands_L'), (lineup, 'lineup'), (typing, 'typing')):
        if os.path.exists(os.path.join(tmp, need + sfx + '.png')):
            fn(tmp, out, sfx)
            print('composed', fn.__name__)
