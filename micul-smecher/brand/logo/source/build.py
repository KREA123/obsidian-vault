from kit import *
import os, re, shutil
from PIL import Image

ROOT = "/home/user/obsidian-vault/micul-smecher/brand/logo"
SV, PN, FV, OC = (os.path.join(ROOT, p) for p in ("svg", "png", "favicon", "svg/on-colour"))
for p in (SV, PN, FV, OC, os.path.join(ROOT, "png/on-colour")):
    os.makedirs(p, exist_ok=True)

files = {}


def put(name, txt):
    path = os.path.join(SV, name)
    open(path, "w").write(txt)
    files[name] = txt


# ---- wordmark
put("soul-wordmark.svg", wordmark_svg(INK))
put("soul-wordmark-dark.svg", wordmark_svg(WHITE, bezel=True))
put("soul-wordmark-black.svg", wordmark_svg("#000000", mode="mono"))
put("soul-wordmark-white.svg", wordmark_svg("#FFFFFF", mode="mono"))
# ---- symbol
put("soul-symbol.svg", symbol_svg(pad=1))
put("soul-symbol-dark.svg", symbol_svg(bezel=True, pad=1))
put("soul-symbol-black.svg", symbol_svg(mode="mono", knock="#000000", pad=1))
put("soul-symbol-white.svg", symbol_svg(mode="mono", knock="#FFFFFF", pad=1))
# ---- lockups
put("soul-lockup-horizontal.svg", horizontal_svg(INK))
put("soul-lockup-horizontal-dark.svg", horizontal_svg(WHITE, bezel=True))
put("soul-lockup-horizontal-black.svg", horizontal_svg("#000000", mode="mono"))
put("soul-lockup-horizontal-white.svg", horizontal_svg("#FFFFFF", mode="mono"))
put("soul-lockup-stacked.svg", stacked_svg(INK))
put("soul-lockup-stacked-dark.svg", stacked_svg(WHITE, bezel=True))
put("soul-lockup-stacked-black.svg", stacked_svg("#000000", mode="mono"))
put("soul-lockup-stacked-white.svg", stacked_svg("#FFFFFF", mode="mono"))
put("soul-lockup-stacked-tagline.svg", stacked_svg(INK, tagline=True))
put("soul-lockup-stacked-tagline-dark.svg", stacked_svg(WHITE, bezel=True, tagline=True))
# ---- app icons
put("soul-app-icon.svg", app_icon_svg(PRODUCT["silver"][1]))
for key, (nm, hx) in PRODUCT.items():
    put(f"soul-app-icon-{key}.svg", app_icon_svg(hx))
put("soul-app-icon-fullbleed.svg", app_icon_svg(PRODUCT["silver"][1], full_bleed=True))
# ---- on product colours (tile with background)
for key, (nm, hx) in PRODUCT.items():
    txt = ON_PRODUCT_TEXT[key]
    x0, y0, x1, y1 = wm_bbox()
    pad = (x1 - x0) * 0.22
    t = wordmark_svg(txt, bg=hx, pad=pad)
    put(f"on-colour/soul-wordmark-on-{key}.svg", t)

# ---- PNG exports (transparent, 2x)
for name, txt in files.items():
    m = re.search(r'viewBox="([-\d. ]+)"', txt)
    _, _, w, h = map(float, m.group(1).split())
    target = 1024 if "icon" in name or "symbol" in name else 1600
    sc = target / max(w, h)
    W, H = round(w * sc), round(h * sc)
    big = re.sub(r'width="[\d.]+" height="[\d.]+"', f'width="{W}" height="{H}"', txt, count=1)
    out = os.path.join(PN, name.replace(".svg", ".png"))
    render_svg(big, out, W, H, scale=1, transparent=True)

# ---- favicons
fav_svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<style>.b{fill:none}@media (prefers-color-scheme:dark){.b{fill:#CBCDCF}}</style>'
    f'<circle class="b" cx="32" cy="32" r="32"/>'
    f'<circle cx="32" cy="32" r="29.5" fill="{GLASS}"/>'
    f'<path fill="{CREAM}" d="{face_eyes(32, 32, 29.5, k=1.16)}"/></svg>\n')
open(os.path.join(FV, "favicon.svg"), "w").write(fav_svg)
small = symbol_svg(size=64, k=1.16)
for s in (16, 32, 48):
    t = re.sub(r'width="64" height="64"', f'width="{s}" height="{s}"', small, count=1)
    render_svg(t, os.path.join(FV, f"favicon-{s}.png"), s, s, scale=1, transparent=True)
for s, nm in ((180, "apple-touch-icon.png"), (512, "icon-512.png"), (192, "icon-192.png")):
    # full-bleed square: iOS / Android mask the corners themselves
    t = app_icon_svg(PRODUCT["silver"][1], size=s, full_bleed=True)
    render_svg(t, os.path.join(FV, nm), s, s, scale=1, transparent=False)
imgs = [Image.open(os.path.join(FV, f"favicon-{s}.png")) for s in (16, 32, 48)]
imgs[2].save(os.path.join(FV, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[:2])
print("ok", len(files))

# 16 px: pixel-fitted master (eyes snapped to the 16-px grid)
f16 = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
       f'<circle cx="8" cy="8" r="8" fill="{GLASS}"/>'
       f'<path fill="{CREAM}" d="M4 6L7 6.9V9.5Q7 11 5.5 11Q4 11 4 9.5Z M12 6L9 6.9V9.5Q9 11 10.5 11Q12 11 12 9.5Z"/></svg>\n')
open(os.path.join(FV, "favicon-16.svg"), "w").write(f16)
render_svg(f16, os.path.join(FV, "favicon-16.png"), 16, 16, scale=1, transparent=True)
imgs = [Image.open(os.path.join(FV, f"favicon-{s}.png")) for s in (16, 32, 48)]
imgs[2].save(os.path.join(FV, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[:2])
