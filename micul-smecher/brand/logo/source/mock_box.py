from kit import *
import re, base64

ROOT = "/home/user/obsidian-vault/micul-smecher/brand/logo"


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


FONT = f"@font-face{{font-family:Mart;src:url(data:font/ttf;base64,{b64('fonts/Mart-400.ttf')})}}"
NOISE = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.55 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>').decode())


def sz(svgtxt, w):
    return re.sub(r'width="[\d.]+" height="[\d.]+"', f'style="width:{w}px;height:auto;display:block;overflow:visible"', svgtxt, count=1)


# foil wordmark: warm-white letters, glass O with a silver bezel (looks like the device's face)
wm = sz(wordmark_svg("#EFE8DA", bezel=True), 250)
# small side mark
side_wm = sz(wordmark_svg("#CFC8BA", mode="mono"), 64)

S, H = 500, 230
LID = 86
html = f"""<html><head><style>{FONT}
body{{margin:0;width:1600px;height:1100px;overflow:hidden;background:radial-gradient(120% 90% at 50% 30%,#F1EBE1 0%,#E3DACD 60%,#D3C8B8 100%);font-family:Mart}}
.scene{{position:absolute;inset:0;perspective:2600px;perspective-origin:50% 20%}}
.box{{position:absolute;left:calc(50% - {S / 2}px);top:300px;width:{S}px;height:{S}px;transform-style:preserve-3d;transform:rotateX(58deg) rotateZ(-34deg)}}
.f{{position:absolute;overflow:hidden}}
.f::after{{content:"";position:absolute;inset:0;background:url({NOISE});opacity:.18;mix-blend-mode:overlay}}
.top{{width:{S}px;height:{S}px;transform:translateZ({H}px);background:linear-gradient(160deg,#2B2C30 0%,#1E1F22 55%,#18191B 100%);display:flex;flex-direction:column;align-items:center;justify-content:center}}
.top .tag{{position:absolute;bottom:36px;left:0;right:0;text-align:center;font-size:8.5px;letter-spacing:.22em;color:#A9A396}}
.top .no{{position:absolute;top:30px;left:34px;font-size:8px;letter-spacing:.2em;color:#8F897D}}
.front{{width:{S}px;height:{H}px;transform-origin:top;transform:translateY({S}px) translateZ({H}px) rotateX(-90deg);background:linear-gradient(180deg,#141517,#0F1012)}}
.right{{left:-{H}px;width:{H}px;height:{S}px;transform-origin:right center;transform:translateZ({H}px) rotateY(-90deg);background:linear-gradient(270deg,#2A2B2F,#232427)}}
.front .seam,.right .seam{{position:absolute;background:rgba(0,0,0,.65);box-shadow:0 1px 0 rgba(255,255,255,.07)}}
.front .seam{{left:0;right:0;top:{LID}px;height:2px}}
.right .seam{{top:0;bottom:0;right:{LID}px;width:2px;box-shadow:-1px 0 0 rgba(255,255,255,.07)}}
.front .lbl{{position:absolute;left:0;right:0;bottom:44px;display:flex;justify-content:center}}
.right .lbl{{position:absolute;top:50%;left:{(H - LID) / 2}px;transform:translate(-50%,-50%) rotate(90deg);font-size:8px;letter-spacing:.24em;color:#8D877B;white-space:nowrap}}
.edge{{position:absolute;inset:0;box-shadow:inset 0 0 0 1px rgba(255,255,255,.06)}}
.shadow{{position:absolute;left:30px;top:50px;width:{S}px;height:{S}px;transform:translateZ(-1px);background:rgba(50,38,26,.55);filter:blur(46px)}}
.shadow2{{position:absolute;left:-4px;top:-2px;width:{S + 10}px;height:{S + 12}px;transform:translateZ(-1px);background:rgba(30,22,14,.6);filter:blur(7px)}}
.cap{{position:absolute;left:64px;bottom:56px;font-size:12px;letter-spacing:.14em;color:#6E685E;text-transform:uppercase}}
.gloss{{position:absolute;inset:0;background:linear-gradient(115deg,rgba(255,255,255,.07) 0%,rgba(255,255,255,0) 38%)}}
</style></head><body><svg style='position:absolute;inset:0' width='1600' height='1100'><defs><filter id='b1' x='-50%' y='-50%' width='200%' height='200%'><feGaussianBlur stdDeviation='34'/></filter><filter id='b2' x='-50%' y='-50%' width='200%' height='200%'><feGaussianBlur stdDeviation='5'/></filter></defs>
<polygon points='470,540 760,840 1215,630 900,330' fill='rgba(60,44,28,.55)' filter='url(#b1)'/>
<polygon points='449,508 724,800 1166,593 890,300' fill='rgba(30,22,14,.75)' filter='url(#b2)'/></svg><div class='scene'><div class='box'>

<div class='f right'><div class='seam'></div><div class='lbl'>SOUL · DESIGNED IN ROMANIA · SOULOS 3</div><div class='edge'></div></div>
<div class='f front'><div class='seam'></div><div class='lbl'>{side_wm}</div><div class='edge'></div></div>
<div class='f top'><div class='no'>FOUNDERS 00 · Nº 017/025</div>{wm}<div class='tag'>YOUR AI HAS A BRAIN. YOU GIVE IT A SOUL.</div><div class='gloss'></div><div class='edge'></div></div>
</div></div>
<div class='cap'>Packaging · soft-touch graphite board · warm-white foil wordmark</div>
</body></html>"""
open("box.html", "w").write(html)
render_html(html, f"{ROOT}/mockups/mockup-box-lid.png", 1600, 1100, scale=1)
