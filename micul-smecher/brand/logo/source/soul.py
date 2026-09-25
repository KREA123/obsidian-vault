"""SOUL logo geometry helpers: font outlining + hand-built primitives."""
import math, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
_cache = {}


def font(name):
    if name not in _cache:
        _cache[name] = TTFont(os.path.join(FONTS, name + ".ttf"))
    return _cache[name]


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def glyph(fontname, ch, size, x, baseline):
    """Return (d, advance, bounds) of a glyph outlined at size px, origin x/baseline (y down)."""
    t = font(fontname)
    gs = t.getGlyphSet()
    cmap = t.getBestCmap()
    gname = cmap[ord(ch)]
    s = size / t["head"].unitsPerEm
    pen = SVGPathPen(gs, ntos=f)
    tp = TransformPen(pen, (s, 0, 0, -s, x, baseline))
    gs[gname].draw(tp)
    bp = BoundsPen(gs)
    gs[gname].draw(bp)
    b = bp.bounds or (0, 0, 0, 0)
    bounds = (x + b[0] * s, baseline - b[3] * s, x + b[2] * s, baseline - b[1] * s)
    return pen.getCommands(), gs[gname].width * s, bounds


def text(fontname, txt, size, x, baseline, tracking=0.0, kern=None):
    """Outline a string. tracking in em. kern: dict index->extra px after glyph i."""
    ds, cur, boxes = [], x, []
    for i, ch in enumerate(txt):
        if ch == " ":
            cur += size * 0.28 + tracking * size
            continue
        d, adv, b = glyph(fontname, ch, size, cur, baseline)
        ds.append(d)
        boxes.append(b)
        cur += adv + tracking * size + (kern or {}).get(i, 0)
    return " ".join(ds), cur - x - tracking * size, boxes


def cap_height(fontname, size):
    t = font(fontname)
    return t["OS/2"].sCapHeight * size / t["head"].unitsPerEm


def circle(cx, cy, r, ccw=False):
    sw = 0 if ccw else 1
    return (f"M{f(cx - r)} {f(cy)}A{f(r)} {f(r)} 0 1 {sw} {f(cx + r)} {f(cy)}"
            f"A{f(r)} {f(r)} 0 1 {sw} {f(cx - r)} {f(cy)}Z")


def ellipse(cx, cy, rx, ry, ccw=False):
    sw = 0 if ccw else 1
    return (f"M{f(cx - rx)} {f(cy)}A{f(rx)} {f(ry)} 0 1 {sw} {f(cx + rx)} {f(cy)}"
            f"A{f(rx)} {f(ry)} 0 1 {sw} {f(cx - rx)} {f(cy)}Z")


def eye(cx, cy, rx, ry, lid_outer, lid_inner, side="L", ccw=False):
    """Oval eye with a straight lid. lid_* = y offset of lid (relative to cy, negative = up)
    at the outer / inner edge of the eye (x = cx -/+ rx). side L: inner edge is right."""
    if lid_outer is None:
        return ellipse(cx, cy, rx, ry, ccw)
    xa, xb = cx - rx, cx + rx
    ya, yb = (cy + lid_outer, cy + lid_inner) if side == "L" else (cy + lid_inner, cy + lid_outer)
    m = (yb - ya) / (xb - xa)
    c0 = ya - m * xa  # y = m x + c0
    # ((x-cx)/rx)^2 + ((m x + c0 - cy)/ry)^2 = 1
    A = 1 / rx ** 2 + m * m / ry ** 2
    B = -2 * cx / rx ** 2 + 2 * m * (c0 - cy) / ry ** 2
    C = cx * cx / rx ** 2 + (c0 - cy) ** 2 / ry ** 2 - 1
    disc = math.sqrt(B * B - 4 * A * C)
    x1, x2 = (-B - disc) / (2 * A), (-B + disc) / (2 * A)
    y1, y2 = m * x1 + c0, m * x2 + c0
    # arc from left point via bottom to right point: angle decreasing -> sweep 0
    ymid = (y1 + y2) / 2
    large = 1 if ymid < cy else 0
    if ccw:
        return (f"M{f(x1)} {f(y1)}A{f(rx)} {f(ry)} 0 {large} 0 {f(x2)} {f(y2)}Z")
    return (f"M{f(x2)} {f(y2)}A{f(rx)} {f(ry)} 0 {large} 1 {f(x1)} {f(y1)}Z")


def eyes(cx, cy, gap, rx, ry, lid_outer, lid_inner, ccw=False):
    """Pair of eyes centred at cx; gap = distance between eye centres."""
    return (eye(cx - gap / 2, cy, rx, ry, lid_outer, lid_inner, "L", ccw) +
            eye(cx + gap / 2, cy, rx, ry, lid_outer, lid_inner, "R", ccw))


def pebble(cx, cy, wt, wb, h, yr=0.0, kt=0.80, ks=0.80, kb=0.78, kbs=0.80, ccw=False):
    """Upright 'pebble-shield': 4 symmetric cubic segments.
    wt = half-width used for the upper shoulders, wb = for the lower,
    h = half-height, yr = y of widest point (relative, negative = up)."""
    T = (cx, cy - h)
    R = (cx + max(wt, wb), cy + yr)
    Bo = (cx, cy + h)
    L = (cx - max(wt, wb), cy + yr)
    W = max(wt, wb)
    # top -> right
    s1 = ((cx + kt * wt, cy - h), (cx + W, cy + yr - ks * (h + yr)), R)
    s2 = ((cx + W, cy + yr + kbs * (h - yr)), (cx + kb * wb, cy + h), Bo)
    s3 = ((cx - kb * wb, cy + h), (cx - W, cy + yr + kbs * (h - yr)), L)
    s4 = ((cx - W, cy + yr - ks * (h + yr)), (cx - kt * wt, cy - h), T)
    segs = [s1, s2, s3, s4]
    start = T
    if ccw:
        # reverse
        pts = [T, s1, s2, s3, s4]
        rev = []
        nodes = [T, R, Bo, L, T]
        ctrls = [(s[0], s[1]) for s in segs]
        d = f"M{f(T[0])} {f(T[1])}"
        for i in range(3, -1, -1):
            c1, c2 = ctrls[i][1], ctrls[i][0]
            end = nodes[i]
            d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(end[0])} {f(end[1])}"
        return d + "Z"
    d = f"M{f(start[0])} {f(start[1])}"
    for c1, c2, e in segs:
        d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(e[0])} {f(e[1])}"
    return d + "Z"


def rrect(x, y, w, h, r, ccw=False):
    """Rounded rect, iOS-ish (plain arcs)."""
    if not ccw:
        return (f"M{f(x + r)} {f(y)}H{f(x + w - r)}A{f(r)} {f(r)} 0 0 1 {f(x + w)} {f(y + r)}"
                f"V{f(y + h - r)}A{f(r)} {f(r)} 0 0 1 {f(x + w - r)} {f(y + h)}H{f(x + r)}"
                f"A{f(r)} {f(r)} 0 0 1 {f(x)} {f(y + h - r)}V{f(y + r)}A{f(r)} {f(r)} 0 0 1 {f(x + r)} {f(y)}Z")
    return (f"M{f(x + r)} {f(y)}A{f(r)} {f(r)} 0 0 0 {f(x)} {f(y + r)}V{f(y + h - r)}"
            f"A{f(r)} {f(r)} 0 0 0 {f(x + r)} {f(y + h)}H{f(x + w - r)}A{f(r)} {f(r)} 0 0 0 {f(x + w)} {f(y + h - r)}"
            f"V{f(y + r)}A{f(r)} {f(r)} 0 0 0 {f(x + w - r)} {f(y)}Z")


def svg(w, h, body, bg=None, title=None):
    t = f"<title>{title}</title>" if title else ""
    b = f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" '
            f'width="{f(w)}" height="{f(h)}">{t}{b}{body}</svg>\n')


# ---------- rendering via headless chromium ----------
_pw = None


def render_html(html, out, w, h, scale=1, transparent=False):
    global _pw
    from playwright.sync_api import sync_playwright
    if _pw is None:
        _pw = sync_playwright().start()
        render_html.browser = _pw.chromium.launch()
    page = render_html.browser.new_page(viewport={"width": int(w), "height": int(h)},
                                        device_scale_factor=scale)
    page.set_content(html)
    page.wait_for_timeout(150)
    page.screenshot(path=out, omit_background=transparent,
                    clip={"x": 0, "y": 0, "width": int(w), "height": int(h)})
    page.close()


def render_svg(svgtext, out, w, h, scale=1, transparent=True):
    html = ("<html><body style='margin:0;background:transparent'>" + svgtext
            + "</body></html>")
    render_html(html, out, w, h, scale, transparent)


def word(fontname, txt, size, x, baseline, tracking=0.0, replace=None, kern=None):
    """Like text() but letters in `replace` are drawn by callback(box)->d (box = font glyph bbox)."""
    replace = replace or {}
    ds, cur = [], x
    boxes = []
    for i, ch in enumerate(txt):
        d, adv, b = glyph(fontname, ch, size, cur, baseline)
        if ch in replace:
            d = replace[ch](b)
        ds.append(d)
        boxes.append(b)
        cur += adv + tracking * size + (kern or {}).get(i, 0)
    return " ".join(ds), cur - x - tracking * size, boxes
