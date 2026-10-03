#!/usr/bin/env python3
"""Contact sheet of round SoulOS screens (web Playwright shots or firmware sim stills).

    python3 os/tools/glass_sheet.py <png_dir> <out.png> [--title T] [--sub S] [--cols 6] [--glob 'NN-*.png']

Every PNG whose name starts with two digits ("07-claude-approval.png") becomes one cell: the picture is
cropped to the round glass (centred circle), set on near-black, and labelled from its file name.
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "..", "firmware", "tools", "fonts", "Nunito-SemiBold.ttf")
FONT_B = os.path.join(HERE, "..", "..", "firmware", "tools", "fonts", "Nunito-Bold.ttf")


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def disc(img, d, inset):
    """Crop the centred circle of `img` (inset = fraction trimmed from each side) and return a d x d RGBA disc."""
    w, h = img.size
    s = min(w, h)
    c = int(s * inset)
    img = img.crop(((w - s) // 2 + c, (h - s) // 2 + c, (w + s) // 2 - c, (h + s) // 2 - c)).resize((d * 2, d * 2), Image.LANCZOS)
    m = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    m = m.resize((d * 2, d * 2), Image.LANCZOS)
    out = Image.new("RGBA", (d * 2, d * 2), (0, 0, 0, 0))
    out.paste(img.convert("RGB"), (0, 0), m)
    return out.resize((d, d), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("out")
    ap.add_argument("--title", default="SoulOS · Glass")
    ap.add_argument("--sub", default="")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--glob", default="[0-9][0-9]-*.png")
    ap.add_argument("--inset", type=float, default=0.0, help="fraction of the picture outside the glass on each side")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dir, a.glob)))
    files = [f for f in files if os.path.abspath(f) != os.path.abspath(a.out)]
    if not files:
        raise SystemExit("no pictures in " + a.dir)
    D, PAD, LAB, TOP = 300, 34, 46, 128
    cols = min(a.cols, len(files))
    rows = (len(files) + cols - 1) // cols
    W = cols * D + (cols + 1) * PAD
    H = TOP + rows * (D + LAB) + (rows + 1) * PAD
    sheet = Image.new("RGB", (W, H), (9, 9, 12))
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD, 34), a.title, font=font(FONT_B, 40), fill=(255, 244, 222))
    if a.sub:
        dr.text((PAD, 86), a.sub, font=font(FONT, 20), fill=(170, 164, 150))
    fl = font(FONT, 21)
    for i, f in enumerate(files):
        r, c = divmod(i, cols)
        x = PAD + c * (D + PAD)
        y = TOP + PAD + r * (D + LAB + PAD)
        img = Image.open(f)
        d = disc(img, D, a.inset)
        ring = Image.new("RGBA", (D + 8, D + 8), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, D + 7, D + 7), outline=(60, 60, 70, 255), width=2)
        sheet.paste(ring, (x - 4, y - 4), ring)
        sheet.paste(d, (x, y), d)
        name = os.path.splitext(os.path.basename(f))[0]
        num, _, label = name.partition("-")
        label = num + "  " + label.replace("-", " ")
        tw = dr.textlength(label, font=fl)
        dr.text((x + (D - tw) / 2, y + D + 12), label, font=fl, fill=(214, 206, 188))
    sheet.save(a.out, optimize=True)
    print("sheet", a.out, sheet.size, len(files), "screens")


if __name__ == "__main__":
    main()
