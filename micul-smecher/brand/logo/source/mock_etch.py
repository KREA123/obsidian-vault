from kit import *
import re, numpy as np
from PIL import Image, ImageFilter

ROOT = "/home/user/obsidian-vault/micul-smecher/brand/logo"
src = Image.open("/home/user/obsidian-vault/micul-smecher/renders/v6/soul_v6_bottom.png").convert("RGB")
a = np.asarray(src).astype(np.float32)

# 1) remove the old second engraved line (rows ~414-440) by interpolating the plate vertically
y0, y1 = 411, 443
xs0, xs1 = 609, 990
top = a[y0 - 1, xs0:xs1].copy()
bot = a[y1 + 1, xs0:xs1].copy()
for y in range(y0, y1 + 1):
    t = (y - y0) / (y1 - y0)
    a[y, xs0:xs1] = top * (1 - t) + bot * t
# keep horizontal smoothness, add back the render's fine grain
rng = np.random.default_rng(7)
a[y0:y1 + 1, xs0:xs1] += rng.normal(0, 0.8, a[y0:y1 + 1, xs0:xs1].shape)

# 2) etch mask: mono wordmark (eyes stay un-etched plate), rendered 4x then downsampled
wm = wordmark_svg("#000000", mode="mono", pad=0)
m = re.search(r'viewBox="([-\d. ]+)"', wm)
_, _, w, h = map(float, m.group(1).split())
H = 30                       # etched height in px on the render (~6.5 mm on the part)
W = w * H / h
S = 4
big = re.sub(r'width="[\d.]+" height="[\d.]+"', f'width="{W * S:.0f}" height="{H * S:.0f}"', wm, count=1)
render_svg(big, "etch_mask.png", round(W * S), round(H * S), transparent=True)
mask = Image.open("etch_mask.png").split()[-1].resize((round(W), round(H)), Image.LANCZOS)
mk = np.asarray(mask).astype(np.float32) / 255
cx, cy = 800, 427
ox, oy = round(cx - W / 2), round(cy - H / 2)
hh, ww = mk.shape
reg = a[oy:oy + hh, ox:ox + ww]
# laser-etched plate: slightly darker, cooler, matte (less of the render's sheen), fine texture
tex = 1 + rng.normal(0, 0.018, (hh, ww))
etched = reg * 0.84 * tex[..., None] + np.array([-2, 0, 3], np.float32)
# engraved edge: soft shadow on the top edge, light catch on the lower edge
sh = np.roll(mk, 1, axis=0) - mk
hi = np.roll(mk, -1, axis=0) - mk
out = reg * (1 - mk[..., None]) + etched * mk[..., None]
out = out - 10 * np.clip(-hi, 0, 1)[..., None] + 12 * np.clip(-sh, 0, 1)[..., None] * 0
out = out + 8 * np.clip(hi, 0, 1)[..., None]
a[oy:oy + hh, ox:ox + ww] = out

img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
img.save(f"{ROOT}/mockups/mockup-etched-base.png", optimize=True)

# 3) detail crop (native pixels, 2x nearest-free upscale with Lanczos for a loupe inset)
crop = img.crop((560, 360, 1040, 520)).resize((960, 320), Image.LANCZOS)
top = img.crop((200, 170, 1400, 850))
sheet = Image.new("RGB", (1200, 680 + 360), "#EFEAE3")
sheet.paste(top, (0, 0))
sheet.paste(crop, ((1200 - 960) // 2, 700))
sheet.save(f"{ROOT}/mockups/mockup-etched-base-detail.png", optimize=True)
print(W, H)
