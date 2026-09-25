#!/usr/bin/env python3
"""annotate.py -- draws the dimension lines of the scale shot on the tone-mapped PNG.

    python3 annotate.py <shot.json> <in.png> [out.png]
The json (written by soul_scene.py) holds, per device, the two projected end points of its width
(normalised image coordinates) and the label.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    meta = json.load(open(sys.argv[1]))
    im = Image.open(sys.argv[2]).convert('RGB')
    out = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2]
    W, H = im.size
    ss = 3
    ov = Image.new('RGBA', (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    col = (92, 84, 74, 235)
    size = int(H * 0.024) * ss
    try:
        f = ImageFont.truetype(os.path.join(HERE, 'fonts', 'Fredoka-Variable.ttf'), size,
                               layout_engine=ImageFont.Layout.RAQM if features.check('raqm') else ImageFont.Layout.BASIC)
        f.set_variation_by_name('Medium')
    except Exception:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
    lw = max(2, int(H * 0.0016)) * ss
    for a in meta.get('annot', []):
        (ax, ay), (bx, by) = a['a'], a['b']
        ax, ay, bx, by = ax * W * ss, ay * H * ss, bx * W * ss, by * H * ss
        tick = H * 0.012 * ss
        d.line([(ax, ay), (bx, by)], fill=col, width=lw)
        for x, y in ((ax, ay), (bx, by)):
            d.line([(x, y - tick), (x, y + tick)], fill=col, width=lw)
        d.text(((ax + bx) / 2, (ay + by) / 2 + tick + size * 0.2), a['label'], font=f, fill=col, anchor='mt')
    ov = ov.resize((W, H), Image.LANCZOS)
    im.paste(ov, (0, 0), ov)
    im.save(out, optimize=True)
    print('annotated', out)


if __name__ == '__main__':
    main()
