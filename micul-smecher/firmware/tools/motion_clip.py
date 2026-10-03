#!/usr/bin/env python3
"""The eyes' motion behaviours as a demo clip: the simulator's "motion" scene
(the real firmware eyes, fed by a simulated IMU) set in a SOUL body that turns,
spins, tips and gets tapped exactly as the IMU was told.

    pio run -e sim
    .pio/build/sim/program /tmp/sim motion C0FFEE0AC117      # a unit with the Original design
    python3 tools/motion_clip.py /tmp/sim/motion ../eyes/soul_eye_motion.mp4 [--size 1080]

The sim writes per frame [roll, pitch, yaw, tap, dizzy, caption] (radians;
roll + = counter-clockwise as you look at it, pitch + = top toward you,
yaw + = turned to its right). Needs numpy, Pillow and ffmpeg.
"""
import argparse
import json
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (11, 11, 12)


def font(px):
    try:
        return ImageFont.truetype(os.path.join(HERE, "fonts", "Nunito-Bold.ttf"), px)
    except OSError:
        return ImageFont.load_default()


def body_texture(T):
    """The device seen from the front, in its own frame (T x T, RGBA): a
    frosted round body, the black glass, a side button and the USB-C port so
    you can see it turn."""
    S = 4  # supersample
    big = Image.new("RGBA", (T * S, T * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c = T * S / 2
    R = 0.49 * T * S
    for i in range(40):  # a soft radial shade on the body
        k = i / 39
        r = R * (1 - 0.06 * k)
        col = tuple(int(a + (b - a) * k) for a, b in zip((196, 191, 182), (236, 232, 223)))
        d.ellipse([c - r, c - r, c + r, c + r], fill=col + (255,))
    # side button (right edge) and USB-C (bottom edge)
    d.rounded_rectangle([c + R - 6 * S, c - 0.11 * T * S, c + R + 5 * S, c - 0.02 * T * S], radius=4 * S, fill=(150, 146, 138, 255))
    d.rounded_rectangle([c - 0.05 * T * S, c + R - 9 * S, c + 0.05 * T * S, c + R - 1 * S], radius=4 * S, fill=(60, 58, 56, 255))
    return big.resize((T, T), Image.LANCZOS)


def homography(src, dst):
    """Coefficients for PIL's PERSPECTIVE transform: output (dst) -> input (src)."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def rot(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    return Ry @ Rx @ Rz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", help="sim output without extension, e.g. /tmp/sim/motion")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=1080)
    a = ap.parse_args()
    meta = json.load(open(a.scene + ".json"))
    n, W, fps = meta["frames"], meta["w"], meta["fps"]
    frames = np.fromfile(a.scene + ".rgb", dtype=np.uint8).reshape(n, W, W, 3)
    poses = meta["pose"]
    O = a.size
    T = int(O * 0.8)  # the device texture
    body = body_texture(T)
    glassR = 0.43 * T
    yy, xx = np.mgrid[0:W, 0:W]
    disc = (((xx + 0.5 - W / 2) ** 2 + (yy + 0.5 - W / 2) ** 2) <= (W / 2) ** 2).astype(np.uint8) * 255
    disc = Image.fromarray(disc, "L")
    cap_font, tag_font = font(int(O * 0.04)), font(int(O * 0.022))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{O}x{O}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                           "-preset", "slow", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    jolt = 0.0
    cap_prev, cap_t = "", 0
    for i in range(n):
        roll, pitch, yaw, tap, dizzy, cap = poses[i]
        jolt = 1.0 if tap else jolt * 0.6
        # the face: the panel picture in the glass of the body texture
        tex = body.copy()
        screen = Image.fromarray(frames[i]).resize((int(2 * glassR), int(2 * glassR)), Image.LANCZOS)
        m = disc.resize(screen.size, Image.LANCZOS)
        g0 = int(T / 2 - glassR)
        ImageDraw.Draw(tex).ellipse([g0 - 3, g0 - 3, g0 + 2 * glassR + 3, g0 + 2 * glassR + 3], fill=(18, 18, 20, 255))
        tex.paste(screen, (g0, g0), m)
        # project the device plane (perspective, camera in front)
        M = rot(roll, pitch, yaw)
        f = O * 3.0
        half = T / 2
        jx = math.sin(i * 2.7) * jolt * O * 0.008
        jy = math.cos(i * 3.1) * jolt * O * 0.008
        dst = []
        for (u, v) in [(-half, -half), (half, -half), (half, half), (-half, half)]:
            p = M @ np.array([u, -v, 0.0])  # texture y is down, device y is up
            s = f / (f - p[2])
            dst.append((O / 2 + p[0] * s + jx, O * 0.46 - p[1] * s + jy))
        src = [(0, 0), (T, 0), (T, T), (0, T)]
        coeffs = homography(src, dst)
        frame = Image.new("RGB", (O, O), BG)
        # a soft shadow under it
        sh = Image.new("L", (O, O), 0)
        sd = ImageDraw.Draw(sh)
        xs = [p[0] for p in dst]
        w = (max(xs) - min(xs)) * 0.42
        sd.ellipse([O / 2 - w, O * 0.86 - O * 0.018, O / 2 + w, O * 0.86 + O * 0.018], fill=110)
        sh = sh.filter(ImageFilter.GaussianBlur(O * 0.02))
        frame.paste((0, 0, 0), (0, 0), sh)
        warped = tex.transform((O, O), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
        frame.paste(warped, (0, 0), warped)
        # captions
        d = ImageDraw.Draw(frame)
        if cap != cap_prev:
            cap_prev, cap_t = cap, i
        if cap:
            al = min(1.0, (i - cap_t) / 6)
            col = tuple(int(BG[k] + (c - BG[k]) * al) for k, c in enumerate((241, 239, 233)))
            d.text((O / 2, O * 0.93), cap, font=cap_font, fill=col, anchor="mm")
        d.text((O * 0.04, O * 0.04), "SOUL · eyes that feel the world", font=tag_font, fill=(150, 148, 156), anchor="la")
        d.text((O * 0.96, O * 0.04), "gyro + accel · real firmware", font=tag_font, fill=(150, 148, 156), anchor="ra")
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print(a.out, n, "frames,", round(n / fps, 1), "s")


if __name__ == "__main__":
    main()
