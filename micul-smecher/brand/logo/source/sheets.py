from kit import *
from kit import _letters
import base64, re, os
ROOT = "/home/user/obsidian-vault/micul-smecher/brand/logo"


def b64font(name):
    return base64.b64encode(open(f"fonts/{name}.ttf", "rb").read()).decode()


FONTCSS = (f"@font-face{{font-family:Bric;src:url(data:font/ttf;base64,{b64font('Bric-700')});font-weight:700}}"
           f"@font-face{{font-family:Bric;src:url(data:font/ttf;base64,{b64font('Bric-500')});font-weight:500}}"
           f"@font-face{{font-family:Mart;src:url(data:font/ttf;base64,{b64font('Mart-400')});font-weight:400}}"
           f"@font-face{{font-family:Mart;src:url(data:font/ttf;base64,{b64font('Mart-500')});font-weight:500}}")


def fit(svgtxt, w, h):
    return re.sub(r'width="[\d.]+" height="[\d.]+"',
                  f'style="max-width:{w}px;max-height:{h}px;width:100%;height:auto;overflow:visible;display:block"',
                  svgtxt, count=1)


PRINT_CMYK = {"#0B0B0C": (60, 50, 50, 100), "#16181D": (75, 65, 55, 80), "#FFF0C8": (0, 5, 25, 0),
              "#FAF8F3": (1, 1, 4, 0), "#F6F3EC": (2, 3, 7, 0), "#CBCDCF": (20, 14, 14, 0),
              "#55575B": (60, 50, 45, 30), "#26324C": (95, 80, 40, 35), "#D2622C": (5, 72, 95, 0),
              "#D8C3A2": (15, 22, 38, 0)}


def cmyk(hx):
    if hx.upper() in PRINT_CMYK:
        return PRINT_CMYK[hx.upper()]
    h = hx.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    k = 1 - max(r, g, b)
    if k >= 1:
        return (0, 0, 0, 100)
    c, m, y = ((1 - v - k) / (1 - k) for v in (r, g, b))
    return tuple(round(v * 100) for v in (c, m, y, k))


def rgb(hx):
    h = hx.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


BASECSS = """
*{box-sizing:border-box}body{margin:0;background:#EDE8DF;color:#16181D;font-family:Mart,monospace;-webkit-font-smoothing:antialiased}
.pg{padding:56px}
h1{font:700 44px/1 Bric;letter-spacing:-.01em;margin:0 0 6px}
h2{font:700 22px/1 Bric;margin:0 0 16px}
.sub{font:400 13px/1.5 Mart;color:#676B74;letter-spacing:.02em;text-transform:uppercase}
.card{background:#fff;border-radius:22px;padding:28px;position:relative;overflow:hidden}
.lbl{font:500 11px/1.3 Mart;letter-spacing:.08em;text-transform:uppercase;color:#676B74}
.dk .lbl{color:#9EA2AA}
"""


# =============================== overview =====================================
def overview():
    pal = [("Glass", GLASS, "the face, the O"), ("Eye Cream", CREAM, "the eyes, light"),
           ("Ink", INK, "type, mono"), ("Paper", PAPER, "light ground"), ("Warm White", WHITE, "type on dark")]
    prod = [(nm, hx) for nm, hx in PRODUCT.values()]

    def sw(nm, hx, note, dark):
        c = cmyk(hx)
        r = rgb(hx)
        fg = "#F3F0E9" if dark else "#16181D"
        return (f"<div class='sw' style='background:{hx};color:{fg}'><b>{nm}</b><span>{hx}<br>RGB {r[0]} {r[1]} {r[2]}"
                f"<br>CMYK≈ {c[0]} {c[1]} {c[2]} {c[3]}</span><i>{note}</i></div>")

    def lum(hx):
        r, g, b = rgb(hx)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    swatches = "".join(sw(n, h, note, lum(h) < 120) for n, h, note in pal)
    pswatches = "".join(sw(n, h, "aluminium", lum(h) < 120) for n, h in prod)

    oncol = ""
    for key, (nm, hx) in PRODUCT.items():
        t = wordmark_svg(ON_PRODUCT_TEXT[key])
        oncol += (f"<div class='oc' style='background:{hx}'>{fit(t, 190, 70)}"
                  f"<span class='lbl' style='color:{ON_PRODUCT_TEXT[key]};opacity:.7'>{nm}</span></div>")
    icons = "".join(f"<div class='ic'>{fit(app_icon_svg(hx), 118, 118)}<span class='lbl'>{nm}</span></div>"
                    for nm, hx in PRODUCT.values())

    html = f"""<html><head><style>{FONTCSS}{BASECSS}
.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:20px;margin-top:34px}}
.hero{{grid-column:1/9;height:420px;display:flex;align-items:center;justify-content:center;background:{PAPER}}}
.herodk{{grid-column:9/13;height:420px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px;background:#0E0F12}}
.c4{{grid-column:span 4;height:260px;display:flex;align-items:center;justify-content:center}}
.c3{{grid-column:span 3;height:260px;display:flex;align-items:center;justify-content:center}}
.card .lbl.tl{{position:absolute;left:24px;top:22px}}
.pal{{grid-column:1/13;display:grid;grid-template-columns:repeat(10,1fr);gap:0;border-radius:22px;overflow:hidden}}
.sw{{height:190px;padding:18px;display:flex;flex-direction:column;gap:8px;font:400 11px/1.45 Mart}}
.sw b{{font:700 18px/1 Bric}} .sw i{{font-style:normal;opacity:.6;margin-top:auto}}
.ocs{{grid-column:1/13;display:grid;grid-template-columns:repeat(5,1fr);gap:0;border-radius:22px;overflow:hidden}}
.oc{{height:190px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px}}
.ics{{grid-column:1/8;display:flex;justify-content:space-around;align-items:center;height:230px}}
.ic{{display:flex;flex-direction:column;align-items:center;gap:12px}}
.type{{grid-column:8/13;height:230px;display:flex;flex-direction:column;justify-content:center;gap:10px}}
.type .a{{font:700 54px/1 Bric;letter-spacing:-.02em}} .type .b{{font:400 15px/1.4 Mart}}
</style></head><body><div class='pg'>
<div class='sub'>SOUL · brand identity · v1.0 · September 2026</div>
<h1>The Glass O</h1>
<div class='sub' style='text-transform:none;letter-spacing:0;font-size:14px;max-width:900px'>The O in SOUL is the device's face: a round black glass disc with two living cream eyes. One face per layout.</div>
<div class='grid'>
 <div class='card hero'><span class='lbl tl'>Primary wordmark</span>{fit(wordmark_svg(INK), 640, 200)}</div>
 <div class='card herodk dk'><span class='lbl tl'>On dark · silver bezel</span>{fit(wordmark_svg(WHITE, bezel=True), 300, 100)}<div style='font:400 11px/1.4 Mart;letter-spacing:.06em;color:#9EA2AA;text-align:center'>YOUR AI HAS A BRAIN.<br>YOU GIVE IT A SOUL.</div></div>
 <div class='card c4'><span class='lbl tl'>Symbol</span>{fit(symbol_svg(), 150, 150)}</div>
 <div class='card c4'><span class='lbl tl'>Horizontal lockup</span>{fit(horizontal_svg(INK), 300, 90)}</div>
 <div class='card c4'><span class='lbl tl'>Stacked lockup</span>{fit(stacked_svg(INK), 150, 170)}</div>
 <div class='card c3' style='background:#fff'><span class='lbl tl'>Black</span>{fit(wordmark_svg('#000', mode='mono'), 230, 70)}</div>
 <div class='card c3 dk' style='background:#000'><span class='lbl tl'>White</span>{fit(wordmark_svg('#fff', mode='mono'), 230, 70)}</div>
 <div class='card c3' style='background:#fff'><span class='lbl tl'>Symbol black</span>{fit(symbol_svg(mode='mono', knock='#000'), 110, 110)}</div>
 <div class='card c3 dk' style='background:#000'><span class='lbl tl'>Symbol white</span>{fit(symbol_svg(mode='mono', knock='#fff'), 110, 110)}</div>
 <div class='ocs'>{oncol}</div>
 <div class='card ics'>{icons}</div>
 <div class='card type'><span class='lbl'>Typography</span><div class='a'>Bricolage Grotesque</div><div class='b'>Martian Mono — labels, data, captions.<br>0123456789 · SOULOS 3 · ORBIT</div></div>
 <div class='pal'>{swatches}{pswatches}</div>
</div></div></body></html>"""
    render_html(html, f"{ROOT}/brand-kit-overview.png", 1600, 1880)


# =============================== construction =====================================
def construction():
    d, obox, bb = _letters()
    cx, cy, R = disc_of(obox)
    x0, y0, x1, y1 = wm_bbox()
    X = R  # clear-space unit = disc radius (= half the O)
    base = BASE
    capTop = base - CH
    body, _, _ = wordmark_body(INK)
    m = 1.9 * X
    vb = (x0 - m, y0 - m, (x1 - x0) + 2 * m, (y1 - y0) + 2 * m)
    ln = 'stroke="#D2622C" stroke-width="0.8" fill="none"'
    th = 'stroke="#D2622C" stroke-width="0.5" stroke-dasharray="3 3" fill="none"'
    g = ""
    # clear space box
    g += f'<rect x="{f(x0 - X)}" y="{f(y0 - X)}" width="{f(x1 - x0 + 2 * X)}" height="{f(y1 - y0 + 2 * X)}" fill="#D2622C" fill-opacity="0.07" stroke="#D2622C" stroke-width="0.6" stroke-dasharray="4 3"/>'
    # X markers (small discs) in the corners
    for (px, py) in ((x0 - X, y0 - X), (x1, y0 - X), (x0 - X, y1), (x1, y1)):
        g += f'<circle cx="{f(px + X / 2)}" cy="{f(py + X / 2)}" r="{f(X / 2)}" fill="none" stroke="#D2622C" stroke-width="0.6"/>'
        g += f'<text x="{f(px + X / 2)}" y="{f(py + X / 2 + 3)}" font-family="Mart" font-size="9" fill="#D2622C" text-anchor="middle">X</text>'
    # guides
    for yy in (base, capTop):
        g += f'<line x1="{f(x0 - X * 0.6)}" x2="{f(x1 + X)}" y1="{f(yy)}" y2="{f(yy)}" {th}/>'
    for yy in (cy - R, cy + R):
        g += f'<line x1="{f(cx - R * 1.5)}" x2="{f(cx + R * 1.5)}" y1="{f(yy)}" y2="{f(yy)}" {th}/>'
    g += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" {ln}/>'
    g += f'<line x1="{f(cx)}" x2="{f(cx)}" y1="{f(cy - R)}" y2="{f(cy + R)}" {th}/>'
    g += f'<line x1="{f(cx - R)}" x2="{f(cx + R)}" y1="{f(cy)}" y2="{f(cy)}" {th}/>'
    fsz = 7.5
    g += f'<text x="{f(x1 + X + 6)}" y="{f(base + 3)}" font-family="Mart" font-size="{fsz}" fill="#D2622C">baseline</text>'
    g += f'<text x="{f(x1 + X + 6)}" y="{f(capTop + 3)}" font-family="Mart" font-size="{fsz}" fill="#D2622C">cap height H</text>'
    g += f'<text x="{f(cx)}" y="{f(cy - R - 6)}" font-family="Mart" font-size="{fsz}" fill="#D2622C" text-anchor="middle">Ø = 1.06 H (O + overshoot)</text>'
    g += f'<text x="{f(x0 - X * 0.5)}" y="{f(y1 + X * 1.35)}" font-family="Mart" font-size="{fsz}" fill="#D2622C">clear space X = Ø / 2 on every side</text>'
    svgc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(f(v) for v in vb)}" width="1400">'
            f'{g}{body}</svg>')

    # face detail
    Rf = 200
    c0 = 260
    fb = face(c0, c0, Rf)
    rx, ry = Rf * 0.20, Rf * 0.34
    gap = Rf * 0.64
    ecx = c0 - gap / 2
    ecy = c0 + Rf * 0.04
    ann = 'stroke="#D2622C" stroke-width="1.2" fill="none"'
    fg = f'<circle cx="{c0}" cy="{c0}" r="{Rf}" {ann}/>'
    fg += f'<ellipse cx="{f(ecx)}" cy="{f(ecy)}" rx="{f(rx)}" ry="{f(ry)}" stroke="#D2622C" stroke-width="1" stroke-dasharray="4 3" fill="none"/>'
    fg += f'<ellipse cx="{f(c0 + gap / 2)}" cy="{f(ecy)}" rx="{f(rx)}" ry="{f(ry)}" stroke="#D2622C" stroke-width="1" stroke-dasharray="4 3" fill="none"/>'
    fg += f'<line x1="{f(ecx)}" x2="{f(c0 + gap / 2)}" y1="{f(ecy + ry + 26)}" y2="{f(ecy + ry + 26)}" {ann}/>'
    for xx in (ecx, c0 + gap / 2):
        fg += f'<line x1="{f(xx)}" x2="{f(xx)}" y1="{f(ecy)}" y2="{f(ecy + ry + 32)}" stroke="#D2622C" stroke-width="0.8" stroke-dasharray="3 3"/>'
    # lid line extended
    lo, li = -ry * 0.70, -ry * 0.48
    xa, xb = ecx - rx, ecx + rx
    ya, yb = ecy + lo, ecy + li
    mslope = (yb - ya) / (xb - xa)
    fg += f'<line x1="{f(xa - 30)}" y1="{f(ya - 30 * mslope)}" x2="{f(xb + 30)}" y2="{f(yb + 30 * mslope)}" {ann}/>'
    xa2, xb2 = c0 + gap / 2 - rx, c0 + gap / 2 + rx
    fg += f'<line x1="{f(xa2 - 30)}" y1="{f(yb + 30 * mslope)}" x2="{f(xb2 + 30)}" y2="{f(ya - 30 * mslope)}" {ann}/>'
    ff = 'font-family="Mart" font-size="13" fill="#D2622C"'
    fg += f'<text x="{c0}" y="{f(ecy + ry + 48)}" {ff} text-anchor="middle">eye spacing 0.64 R</text>'
    fg += f'<text x="{c0}" y="{c0 - Rf - 14}" {ff} text-anchor="middle">disc R</text>'
    face_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 520" width="520">{fb}{fg}</svg>')

    rows = [("Primary wordmark", "72 px wide", "18 mm", "10 mm (laser)", wordmark_svg(INK), 72),
            ("Horizontal lockup", "96 px wide", "22 mm", "14 mm", horizontal_svg(INK), 96),
            ("Symbol", "16 px (use favicon-16 master below 24 px)", "5 mm", "4 mm", symbol_svg(), 16)]
    mins = ""
    for nm, px, pr, lz, sv, w in rows:
        mins += (f"<tr><td>{nm}</td><td><div style='width:{w}px'>{fit(sv, w, 60)}</div></td><td>{px}</td><td>{pr}</td><td>{lz}</td></tr>")

    html = f"""<html><head><style>{FONTCSS}{BASECSS}
table{{border-collapse:collapse;width:100%;font:400 13px/1.4 Mart}} td,th{{text-align:left;padding:14px 10px;border-bottom:1px solid #E3DED4;vertical-align:middle}}
th{{font:500 11px Mart;letter-spacing:.08em;text-transform:uppercase;color:#676B74}}
.spec{{font:400 13px/1.7 Mart}} .spec b{{font-weight:500}}
</style></head><body><div class='pg'>
<div class='sub'>SOUL · construction, clear space & minimum size</div><h1>Built, not typed</h1>
<div class='card' style='margin-top:28px;background:{PAPER}'>{svgc.replace('width="1400"', 'style="width:100%;height:auto;display:block"')}</div>
<div style='display:grid;grid-template-columns:520px 1fr;gap:20px;margin-top:20px'>
 <div class='card' style='background:{PAPER};padding:0'>{face_svg}</div>
 <div class='card spec'><h2>The face (symbol) geometry</h2>
 <b>Disc</b> radius R, colour Glass #0B0B0C.<br>
 <b>Eyes</b> ellipses 0.40 R wide × 0.68 R tall, centres 0.64 R apart, 0.04 R below centre.<br>
 <b>Lids</b> one straight cut per eye: 0.24 R above the eye centre at the outer edge, 0.16 R at the inner edge (an 11° brow); the same knowing look as the eyes in the v6 renders.<br>
 <b>In the wordmark</b> the disc replaces the Bricolage O at 1.02 × the O's height (1.06 H), same centre, optically kerned 1.5% of cap height tighter on both sides.<br>
 <b>Letters</b> S, U, L: Bricolage Grotesque, wght 700, opsz 96, wdth 100, tracking +55/1000, outlined; overlaps removed.<br>
 <b>Dark grounds</b> add the silver bezel: disc at 0.915 R inside a #CBCDCF ring (like the chrome ring round the real glass).<br><br>
 <h2 style='margin-top:10px'>Minimum sizes</h2>
 <table><tr><th>Asset</th><th>At minimum</th><th>Screen</th><th>Print</th><th>Etch / deboss</th></tr>{mins}</table>
 </div></div>
</div></body></html>"""
    render_html(html, f"{ROOT}/construction-clearspace.png", 1600, 1600)


if __name__ == "__main__":
    overview()
    construction()
