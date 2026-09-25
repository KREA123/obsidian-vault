"""SOUL brand kit — core geometry (direction A 'Glass O', refined)."""
from soul import *

# ---------------- palette ----------------
GLASS = "#0B0B0C"
CREAM = "#FFF0C8"
INK = "#16181D"
PAPER = "#FAF8F3"
WHITE = "#F6F3EC"      # warm white for reverse use
BEZEL = "#CBCDCF"      # = Silver aluminium
PRODUCT = {            # aluminium sRGB from docs/02-MANUFACTURING.md
    "silver": ("Silver", "#CBCDCF"),
    "graphite": ("Graphite", "#55575B"),
    "midnight": ("Midnight", "#26324C"),
    "ember": ("Ember", "#D2622C"),
    "champagne": ("Champagne", "#D8C3A2"),
}
ON_PRODUCT_TEXT = {"silver": INK, "graphite": WHITE, "midnight": WHITE, "ember": WHITE, "champagne": INK}

FN = "Bric-700"
SZ = 200.0                      # master font size
CH = cap_height(FN, SZ)         # 132
BASE = 200.0                    # baseline in master space
TRACK = 0.055
KERN = {0: -3.0, 1: -3.0}       # S|O and O|U optical tightening around the disc


# ---------------- the face ----------------
def face_eyes(cx, cy, R, ccw=False, k=1.0):
    """Two lidded eyes inside a disc of radius R. Proportions follow the v6 render."""
    rx, ry = R * 0.20 * k, R * 0.34 * k
    gap = R * 0.64 * (1 + (k - 1) * 0.6)
    return eyes(cx, cy + R * 0.04, gap, rx, ry, -ry * 0.70, -ry * 0.48, ccw)


def face(cx, cy, R, mode="colour", k=1.0, bezel=False, glass=GLASS, eye=CREAM, knock=None):
    """mode colour: glass disc + cream eyes (optional silver bezel ring for dark grounds).
    mode mono: single colour `knock` disc with the eyes knocked out (transparent)."""
    if mode == "mono":
        return f'<path fill="{knock}" d="{circle(cx, cy, R)}{face_eyes(cx, cy, R, ccw=True, k=k)}"/>'
    out = ""
    if bezel:
        out += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="{BEZEL}"/>'
        out += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R * 0.915)}" fill="{glass}"/>'
        out += f'<path fill="{eye}" d="{face_eyes(cx, cy, R * 0.915, k=k)}"/>'
        return out
    out += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="{glass}"/>'
    out += f'<path fill="{eye}" d="{face_eyes(cx, cy, R, k=k)}"/>'
    return out


# ---------------- wordmark ----------------
def _letters(x=0.0, plainO=False):
    """Return (letters_d, O_box, width, full_bbox) for SOUL at master size."""
    cur = x
    ds, obox, boxes = [], None, []
    for i, ch in enumerate("SOUL"):
        d, adv, b = glyph(FN, ch, SZ, cur, BASE)
        if ch == "O":
            obox = b
            if plainO:
                ds.append(d)
        else:
            ds.append(d)
        boxes.append(b)
        cur += adv + TRACK * SZ + KERN.get(i, 0)
    x0 = min(b[0] for b in boxes); x1 = max(b[2] for b in boxes)
    y0 = min(b[1] for b in boxes); y1 = max(b[3] for b in boxes)
    return " ".join(ds), obox, (x0, y0, x1, y1)


def disc_of(obox):
    x0, y0, x1, y1 = obox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = (y1 - y0) / 2 * 1.02
    return cx, cy, R


def wordmark_body(text_fill, mode="colour", bezel=False, knock=None, plainO=False):
    d, obox, bb = _letters(plainO=plainO)
    body = f'<path fill="{text_fill}" d="{d}"/>'
    if not plainO:
        cx, cy, R = disc_of(obox)
        body += face(cx, cy, R, mode=mode, bezel=bezel, knock=knock or text_fill)
    return body, bb, disc_of(obox)


def wm_bbox():
    d, obox, bb = _letters()
    cx, cy, R = disc_of(obox)
    return (bb[0], min(bb[1], cy - R), bb[2], max(bb[3], cy + R))


def wordmark_svg(text_fill, mode="colour", bezel=False, knock=None, bg=None, pad=2.0, title="SOUL"):
    body, _, _ = wordmark_body(text_fill, mode, bezel, knock)
    x0, y0, x1, y1 = wm_bbox()
    p = pad
    w, h = x1 - x0 + 2 * p, y1 - y0 + 2 * p
    b = f'<rect x="{f(x0 - p)}" y="{f(y0 - p)}" width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x0 - p)} {f(y0 - p)} {f(w)} {f(h)}" '
            f'width="{f(w)}" height="{f(h)}" role="img" aria-label="SOUL"><title>{title}</title>{b}{body}</svg>\n')


# ---------------- lockups (symbol + plain-O wordmark: one face per layout) ----------------
def lockup_parts():
    d, obox, bb = _letters(plainO=True)
    return d, bb


def horizontal_svg(text_fill, mode="colour", bezel=False, knock=None, bg=None, pad=2.0):
    d, bb = lockup_parts()
    x0, y0, x1, y1 = bb
    capH = y1 - y0
    R = capH * 0.78               # symbol a bit taller than caps (1.56 x cap)
    gap = capH * 0.52
    cx = x0 - gap - R
    cy = (y0 + y1) / 2
    body = face(cx, cy, R, mode=mode, bezel=bezel, knock=knock or text_fill)
    body += f'<path fill="{text_fill}" d="{d}"/>'
    X0, Y0, X1, Y1 = cx - R - pad, cy - R - pad, x1 + pad, cy + R + pad
    w, h = X1 - X0, Y1 - Y0
    b = f'<rect x="{f(X0)}" y="{f(Y0)}" width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(X0)} {f(Y0)} {f(w)} {f(h)}" '
            f'width="{f(w)}" height="{f(h)}" role="img" aria-label="SOUL"><title>SOUL</title>{b}{body}</svg>\n')


def stacked_svg(text_fill, mode="colour", bezel=False, knock=None, bg=None, pad=2.0, tagline=False):
    d, bb = lockup_parts()
    x0, y0, x1, y1 = bb
    capH = y1 - y0
    wcx = (x0 + x1) / 2
    R = capH * 1.25
    gap = capH * 0.62
    cy = y0 - gap - R
    body = face(wcx, cy, R, mode=mode, bezel=bezel, knock=knock or text_fill)
    body += f'<path fill="{text_fill}" d="{d}"/>'
    bottom = y1
    left, right = x0, x1
    if tagline:
        ts = capH * 0.215
        td, tw, tb = text("Mart-500", "YOUR AI HAS A BRAIN. YOU GIVE IT A SOUL.", ts, 0, 0, tracking=0.04)
        tx = wcx - tw / 2
        ty = y1 + capH * 0.62 + cap_height("Mart-500", ts)
        td, tw, tb = text("Mart-500", "YOUR AI HAS A BRAIN. YOU GIVE IT A SOUL.", ts, tx, ty, tracking=0.04)
        body += f'<path fill="{text_fill}" fill-opacity="0.72" d="{td}"/>'
        bottom = ty + 2
        left, right = min(left, tx), max(right, tx + tw)
    X0 = min(left, wcx - R) - pad
    X1 = max(right, wcx + R) + pad
    Y0 = cy - R - pad
    Y1 = bottom + pad
    w, h = X1 - X0, Y1 - Y0
    b = f'<rect x="{f(X0)}" y="{f(Y0)}" width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(X0)} {f(Y0)} {f(w)} {f(h)}" '
            f'width="{f(w)}" height="{f(h)}" role="img" aria-label="SOUL"><title>SOUL</title>{b}{body}</svg>\n')


# ---------------- symbol & app icon ----------------
def symbol_svg(mode="colour", bezel=False, knock=INK, size=512, k=1.0, pad=0.0):
    R = size / 2 - pad
    body = face(size / 2, size / 2, R, mode=mode, bezel=bezel, knock=knock, k=k)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
            f'role="img" aria-label="SOUL"><title>SOUL</title>{body}</svg>\n')


def shade(hexc, amt):
    """amt>0 lighten, <0 darken."""
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if amt >= 0:
        r, g, b = (int(c + (255 - c) * amt) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + amt)) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def app_icon_svg(colour="#CBCDCF", size=1024, full_bleed=False, flat=False):
    """Rounded tile in a product colour with the glass face. full_bleed: square (OS masks it)."""
    s = size
    rid = colour.lstrip("#")
    r = 0 if full_bleed else s * 0.2237
    R = s * 0.335
    cx, cy = s / 2, s * 0.5
    defs = ""
    if flat:
        tile = f'<rect width="{s}" height="{s}" rx="{f(r)}" fill="{colour}"/>'
        ring = ""
    else:
        defs = (f'<defs><linearGradient id="t{rid}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{shade(colour, 0.16)}"/><stop offset="1" stop-color="{shade(colour, -0.10)}"/></linearGradient>'
                f'<linearGradient id="b{rid}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{shade(colour, -0.22)}"/><stop offset="1" stop-color="{shade(colour, 0.22)}"/></linearGradient>'
                f'</defs>')
        tile = f'<rect width="{s}" height="{s}" rx="{f(r)}" fill="url(#t{rid})"/>'
        # a machined chamfer ring around the glass, lit from above
        ring = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R * 1.075)}" fill="url(#b{rid})"/>'
    body = tile + ring
    body += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="{GLASS}"/>'
    body += f'<path fill="{CREAM}" d="{face_eyes(cx, cy, R)}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s} {s}" width="{s}" height="{s}" '
            f'role="img" aria-label="SOUL"><title>SOUL</title>{defs}{body}</svg>\n')
