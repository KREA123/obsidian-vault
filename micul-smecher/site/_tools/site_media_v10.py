"""Site media from renders/v10: desk (size S next to a phone) with blank glass + glass map, and the og image."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull
from scipy.linalg import sqrtm

R10 = "/home/user/obsidian-vault/micul-smecher/renders/v10"
OUT = "/home/user/obsidian-vault/micul-smecher/site/media/v10"
DBG = sys.argv[1] if len(sys.argv) > 1 else None


def lum(a):
    return a[..., 0] * .2126 + a[..., 1] * .7152 + a[..., 2] * .0722


def blank_glass(a, seed, dark=34):
    """a: float RGB. seed: (x, y) inside the glass on a dark pixel. Returns blanked image, centre, 2x2 map (column-major)."""
    L = lum(a)
    lab, _ = ndi.label(L < dark)
    sx, sy = seed
    reg = lab == lab[sy, sx]
    ys, xs = np.nonzero(reg)
    pts = np.c_[xs, ys]
    hull = ConvexHull(pts)
    poly = [tuple(map(float, pts[i])) for i in hull.vertices]
    m = Image.new("L", (a.shape[1], a.shape[0]), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    disc = np.array(m) > 0
    ys, xs = np.nonzero(disc)
    c = np.array([xs.mean(), ys.mean()])
    cov = np.cov(np.c_[xs - c[0], ys - c[1]].T)
    M = np.real(2 * sqrtm(cov))  # unit disc -> image px
    # unit-disc coordinates of every pixel
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    inv = np.linalg.inv(M)
    u = inv[0, 0] * (xx - c[0]) + inv[0, 1] * (yy - c[1])
    v = inv[1, 0] * (xx - c[0]) + inv[1, 1] * (yy - c[1])
    r = np.hypot(u, v)
    bright = (L > dark) & (r < 0.92)
    blab, n = ndi.label(bright)
    eyes = np.zeros_like(bright); streak = np.zeros_like(bright)
    for i in range(1, n + 1):
        comp = blab == i
        cu, cv_ = u[comp].mean(), v[comp].mean()
        if np.hypot(cu, cv_) < 0.62 and comp.sum() > 30:  # eyes sit in the middle; the reflection streak runs near the rim
            eyes |= comp
        else:
            streak |= comp
    R = np.sqrt(abs(np.linalg.det(M)))
    streak = ndi.binary_dilation(streak, iterations=int(0.05 * R) + 2)
    halo = ndi.binary_dilation(eyes, iterations=int(0.2 * R)) & (r < 0.93) & ~streak
    known = ((r < 0.95) & ~halo & ~streak).astype(float)
    out = a.copy()
    fill = out * known[..., None]
    for s_ in (int(0.25 * R), int(0.12 * R), int(0.06 * R)):
        num = np.stack([ndi.gaussian_filter(fill[..., k], s_) for k in range(3)], -1)
        den = ndi.gaussian_filter(known, s_)[..., None]
        est = num / np.maximum(den, 1e-6)
        out[halo] = est[halo]
    return out, c, M, eyes, halo


def save_variants(img, stem, widths, avif=False):
    for wd in widths:
        h = round(img.height * wd / img.width)
        im = img.resize((wd, h), Image.LANCZOS)
        im.save(f"{OUT}/{stem}-{wd}.webp", quality=82, method=6)
        if avif:
            im.save(f"{OUT}/{stem}-{wd}.avif", quality=60)


# ---------------- desk: S next to a generic phone (71.5 x 147 mm), crop to a wide frame
src = np.asarray(Image.open(f"{R10}/soul_v10_desk.png").convert("RGB")).astype(float)
crop = (0, 300, 1600, 1100)  # x0, y0, x1, y1  -> 1600 x 800
a = src[crop[1]:crop[3], crop[0]:crop[2]]
out, c, M, eyes, halo = blank_glass(a, seed=(812, 680 - crop[1]))
H, W = a.shape[:2]
im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
save_variants(im, "desk-s", (800, 1600), avif=True)
gm = {"w": W, "h": H, "glass": [{"c": [round(c[0] / W, 5), round(c[1] / H, 5)],
                                  "m": [round(M[0, 0], 2), round(M[1, 0], 2), round(M[0, 1], 2), round(M[1, 1], 2)]}]}
print("desk", json.dumps(gm), "eye px", int(eyes.sum()), "halo px", int(halo.sum()))
if DBG:
    d = im.copy(); dr = ImageDraw.Draw(d)
    t = np.linspace(0, 2 * np.pi, 200)
    ring = [(c[0] + M[0, 0] * np.cos(q) + M[0, 1] * np.sin(q), c[1] + M[1, 0] * np.cos(q) + M[1, 1] * np.sin(q)) for q in t]
    dr.line(ring + [ring[0]], fill=(255, 0, 0), width=2)
    d.save(f"{DBG}/desk_dbg.png")

# ---------------- og image (1200 x 630) from the hero, eyes kept
hero = Image.open(f"{R10}/soul_v10_hero.png").convert("RGB")  # 1600 x 1200
og = hero.crop((0, 180, 1600, 1020)).resize((1200, 630), Image.LANCZOS)
og.save(f"{OUT}/og-s.jpg", quality=86, optimize=True, progressive=True)
print("og ok")
