from kit import *
import base64, re
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = "/home/user/obsidian-vault/micul-smecher/brand/logo"
SITE = "/home/user/obsidian-vault/micul-smecher/site/index.html"
MK = f"{ROOT}/mockups"
import os
os.makedirs(MK, exist_ok=True)


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


CF = "/mnt/skills/examples/canvas-design/canvas-fonts/"
css = (f"@font-face{{font-family:'Fredoka';src:url(data:font/ttf;base64,{b64('fonts/Fredoka.ttf')});font-weight:300 700}}"
       f"@font-face{{font-family:'Instrument Sans';src:url(data:font/ttf;base64,{b64(CF + 'InstrumentSans-Regular.ttf')});font-weight:400}}"
       f"@font-face{{font-family:'Instrument Sans';src:url(data:font/ttf;base64,{b64(CF + 'InstrumentSans-Bold.ttf')});font-weight:500 700}}"
       f"@font-face{{font-family:'JetBrains Mono';src:url(data:font/ttf;base64,{b64(CF + 'JetBrainsMono-Regular.ttf')});font-weight:400 500}}")

logo = wordmark_svg(WHITE, bezel=True)
logo = re.sub(r'width="[\d.]+" height="[\d.]+"', 'height="21" style="display:block;overflow:visible"', logo, count=1)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 860}, device_scale_factor=2)
    # offline: block anything that is not a local file
    pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") or r.request.url.startswith("data:") else r.abort())
    pg.goto("file://" + SITE)
    pg.add_style_tag(content=css + ".brand{gap:0}")
    pg.evaluate("""(svg)=>{const a=document.querySelector('.nav .brand'); a.innerHTML=svg;}""", logo)
    pg.wait_for_timeout(1500)
    pg.screenshot(path="nav_full.png")
    b.close()

im = Image.open("nav_full.png").convert("RGB")      # 2880 x 1720
W = 1600
im = im.crop((0, 0, im.width, 1740 if im.height > 1740 else im.height))
full = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
full = full.crop((0, 0, W, 870))
# zoom strip: left part of the nav at 2x (native)
nav_h = 58 * 2
strip = im.crop((330, 0, 1640, nav_h))
canvas = Image.new("RGB", (W, full.height + 80 + nav_h + 60), "#E9E4DA")
canvas.paste(full, (0, 0))
sx = (W - strip.width) // 2
y = full.height + 80
# rounded-ish frame
frame = Image.new("RGB", (strip.width + 16, strip.height + 16), "#16181D")
canvas.paste(frame, (sx - 8, y - 8))
canvas.paste(strip, (sx, y))
canvas.save(f"{MK}/mockup-landing-nav.png", optimize=True)
print(canvas.size)
