#!/usr/bin/env python3
"""Turn simulator output (raw RGB frames + JSON) into product-shot media.

    python3 tools/frames_to_media.py <sim_out_dir> <media_dir> [--gif] [--mp4] [--sheet]

Every frame is composited as the real object would look: the AMOLED under
its lens, set in a frosted body that glows with the "body light" colour the
firmware asked for on that frame. MP4 needs ffmpeg on PATH.
"""
import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 540          # output frame size
SCREEN_R = 196      # displayed screen radius (px)
BODY_R = 250        # frosted body radius (px)


def radial(size, r, feather):
    y, x = np.mgrid[0:size, 0:size]
    d = np.sqrt((x - size / 2 + 0.5) ** 2 + (y - size / 2 + 0.5) ** 2)
    return np.clip((r - d) / feather + 0.5, 0, 1)


def build_static():
    """Background, frosted body and the masks used for every frame."""
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    bg = np.zeros((SIZE, SIZE, 3), np.float32)
    t = y / SIZE
    bg[..., 0] = 16 + 14 * t
    bg[..., 1] = 18 + 16 * t
    bg[..., 2] = 24 + 20 * t
    body_mask = radial(SIZE, BODY_R, 1.5)
    screen_mask = radial(SIZE, SCREEN_R, 1.2)
    # frosted body: soft top-light gradient + inner rim shading
    d = np.sqrt((x - SIZE / 2) ** 2 + (y - SIZE / 2) ** 2) / BODY_R
    shade = 0.78 + 0.22 * np.clip(1 - (y - SIZE * 0.2) / SIZE, 0, 1) - 0.18 * np.clip(d - 0.82, 0, 1) / 0.18
    body = np.stack([234 * shade, 236 * shade, 241 * shade], -1)
    # ground shadow
    sh = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(sh).ellipse((SIZE / 2 - 190, SIZE - 60, SIZE / 2 + 190, SIZE - 22), fill=120)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
    bg *= (1 - 0.6 * sh[..., None])
    # lens highlight
    hl = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(hl).ellipse((SIZE / 2 - 150, SIZE / 2 - 185, SIZE / 2 + 40, SIZE / 2 - 95), fill=38)
    hl = np.asarray(hl.filter(ImageFilter.GaussianBlur(18)), np.float32) / 255
    return bg, body, body_mask, screen_mask, hl


def compose(frame, bl, static):
    bg, body, body_mask, screen_mask, hl = static
    r, g, b, level = bl
    img = bg * (1 - body_mask[..., None]) + body * body_mask[..., None]
    if level > 0.003:  # the frosted body lights up from the inside
        glow_col = np.array([r, g, b], np.float32)
        ring = body_mask * (1 - screen_mask)
        img = img * (1 - 0.55 * level * ring[..., None]) + glow_col * (0.55 * level * ring[..., None])
        halo = radial(SIZE, BODY_R + 30, 34) * (1 - body_mask)
        img = img + glow_col * (0.35 * level * halo[..., None])
    scr = Image.fromarray(frame).resize((SCREEN_R * 2, SCREEN_R * 2), Image.LANCZOS)
    s = np.zeros((SIZE, SIZE, 3), np.float32)
    o = SIZE // 2 - SCREEN_R
    s[o:o + SCREEN_R * 2, o:o + SCREEN_R * 2] = np.asarray(scr, np.float32)
    # thin dark bezel ring around the lens
    bezel = radial(SIZE, SCREEN_R + 7, 1.5) * (1 - screen_mask)
    img = img * (1 - bezel[..., None]) + np.array([30, 32, 38], np.float32) * bezel[..., None]
    img = img * (1 - screen_mask[..., None]) + s * screen_mask[..., None]
    img = img + 255 * hl[..., None] * screen_mask[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def frames_of(sim_dir, name):
    meta = json.load(open(os.path.join(sim_dir, name + ".json")))
    w, h, n = meta["w"], meta["h"], meta["frames"]
    raw = np.fromfile(os.path.join(sim_dir, name + ".rgb"), np.uint8)
    raw = raw[: n * w * h * 3].reshape(n, h, w, 3)
    return meta, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sim_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--mp4", action="store_true")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    static = build_static()
    names = sorted(f[:-5] for f in os.listdir(a.sim_dir) if f.endswith(".json"))
    if a.only:
        names = [n for n in names if n in a.only.split(",")]
    sheet_tiles = []
    for name in names:
        meta, raw = frames_of(a.sim_dir, name)
        fps = int(meta["fps"])
        body = meta["body"]
        comp = [compose(raw[i], body[i], static) for i in range(len(raw))]
        if a.mp4:
            out = os.path.join(a.out_dir, name + ".mp4")
            p = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                 "-s", f"{SIZE}x{SIZE}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "slow", "-movflags", "+faststart", out],
                stdin=subprocess.PIPE)
            for c in comp:
                p.stdin.write(c.tobytes())
            p.stdin.close()
            p.wait()
        if a.gif:
            small = [Image.fromarray(c).resize((300, 300), Image.LANCZOS) for c in comp[::2]]
            pal = small[len(small) // 2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
            q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in small]
            q[0].save(os.path.join(a.out_dir, name + ".gif"), save_all=True, append_images=q[1:],
                      duration=int(2000 / fps), loop=0, optimize=True)
        if a.sheet:
            picks = [int(len(comp) * f) for f in (0.15, 0.45, 0.75)]
            for i in picks:
                sheet_tiles.append((name, Image.fromarray(comp[i]).resize((270, 270), Image.LANCZOS)))
        print(f"{name}: {len(comp)} frames", file=sys.stderr)
    if a.sheet and sheet_tiles:
        cols = 6
        rows = math.ceil(len(sheet_tiles) / cols)
        sheet = Image.new("RGB", (cols * 270, rows * 290), (14, 16, 22))
        d = ImageDraw.Draw(sheet)
        for k, (name, im) in enumerate(sheet_tiles):
            x, y = (k % cols) * 270, (k // cols) * 290
            sheet.paste(im, (x, y))
            d.text((x + 10, y + 272), name, fill=(170, 176, 186))
        sheet.save(os.path.join(a.out_dir, "contact_sheet.png"))


if __name__ == "__main__":
    main()
