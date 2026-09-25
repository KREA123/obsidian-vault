"""Tiny SVG drafting kit for the SOUL blueprint sheets (A3 landscape, units = paper mm).

Everything is drawn in paper millimetres (viewBox 0 0 420 297); object geometry is mapped
through View objects (scale + projection). Two themes: 'blue' (classic blueprint) and 'white'
(engineering print).
"""
import math

FONT = "'DejaVu Sans Mono','Liberation Mono',monospace"
W, H = 420.0, 297.0
CW = 0.602  # DejaVu Sans Mono advance width / em

THEMES = {
    'blue': dict(bg='#0b3d91', paper2='#0d4299', fg='#ffffff', dim='#a9dcff', acc='#ffe08a',
                 grid='#ffffff', g1=0.055, g2=0.11, glass='#7fd0ff', glass_op=0.22,
                 fill2='#ffffff', fill2_op=0.07, batt='#ffe08a', batt_op=0.10),
    'white': dict(bg='#ffffff', paper2='#ffffff', fg='#111418', dim='#1d4f9c', acc='#8a5a00',
                  grid='#1d4f9c', g1=0.05, g2=0.09, glass='#4aa3df', glass_op=0.18,
                  fill2='#000000', fill2_op=0.05, batt='#c89400', batt_op=0.10),
}


def f(v):
    return ('%.3f' % v).rstrip('0').rstrip('.')


def pts_d(pts, close=True):
    s = 'M' + ' L'.join('%s %s' % (f(x), f(y)) for x, y in pts)
    return s + (' Z' if close else '')


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class View:
    """Maps object (u, v) [mm, v up] to paper; k = drawing scale."""

    def __init__(self, ox, oy, k, flipx=False):
        self.ox, self.oy, self.k, self.flipx = ox, oy, k, flipx

    def p(self, u, v):
        return (self.ox + (-u if self.flipx else u) * self.k, self.oy - v * self.k)

    def pl(self, pts):
        return [self.p(u, v) for u, v in pts]


class Sheet:
    def __init__(self, theme='blue'):
        self.th = THEMES[theme]
        self.theme = theme
        self.el = []
        self.defs = []
        self.nclip = 0

    # ---------------- primitives ----------------
    def add(self, s):
        self.el.append(s)

    def line(self, x1, y1, x2, y2, c='o', extra=''):
        self.add('<line class="%s" x1="%s" y1="%s" x2="%s" y2="%s" %s/>' % (c, f(x1), f(y1), f(x2), f(y2), extra))

    def poly(self, pts, c='o', close=True, extra=''):
        self.add('<path class="%s" d="%s" %s/>' % (c, pts_d(pts, close), extra))

    def path(self, d, c='o', extra=''):
        self.add('<path class="%s" d="%s" %s/>' % (c, d, extra))

    def circle(self, cx, cy, r, c='o', extra=''):
        self.add('<circle class="%s" cx="%s" cy="%s" r="%s" %s/>' % (c, f(cx), f(cy), f(r), extra))

    def rect(self, x, y, w, h, c='o', rx=0, extra=''):
        self.add('<rect class="%s" x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>' % (c, f(x), f(y), f(w), f(h), f(rx), extra))

    def text(self, x, y, s, size=2.5, anchor='start', c='tx', rot=0, weight=None, extra=''):
        tr = ' transform="rotate(%s %s %s)"' % (f(rot), f(x), f(y)) if rot else ''
        wt = ' font-weight="%s"' % weight if weight else ''
        self.add('<text class="%s" x="%s" y="%s" font-size="%s" text-anchor="%s"%s%s %s>%s</text>' % (
            c, f(x), f(y), f(size), anchor, tr, wt, extra, esc(s)))

    def tw(self, s, size):
        return len(s) * CW * size

    def clip(self, pts):
        self.nclip += 1
        cid = 'clp%d' % self.nclip
        self.defs.append('<clipPath id="%s"><path d="%s"/></clipPath>' % (cid, pts_d(pts)))
        return cid

    def group(self, inner, extra=''):
        self.add('<g %s>' % extra)
        inner()
        self.add('</g>')

    # ---------------- drafting symbols ----------------
    def arrow(self, tip, frm, c='ah', L=2.3, Wd=0.55):
        dx, dy = tip[0] - frm[0], tip[1] - frm[1]
        n = math.hypot(dx, dy) or 1
        ux, uy = dx / n, dy / n
        bx, by = tip[0] - ux * L, tip[1] - uy * L
        pts = [tip, (bx - uy * Wd, by + ux * Wd), (bx + uy * Wd, by - ux * Wd)]
        self.poly(pts, c)

    def dim_h(self, x1, y1, x2, y2, at, txt, tshift=0, gap=1.0, over=1.6, tside=-1, size=2.6, arrows_out=None):
        """Horizontal dimension between points (x1,y1),(x2,y2); dimension line at paper y=at."""
        for x, y in ((x1, y1), (x2, y2)):
            sgn = 1 if at > y else -1
            if abs(at - y) > gap:
                self.line(x, y + sgn * gap, x, at + sgn * over, 't')
        xa, xb = min(x1, x2), max(x1, x2)
        tw = self.tw(txt, size)
        out = arrows_out if arrows_out is not None else (xb - xa) < 7
        if out:
            self.line(xa - 6, at, xb + 6, at, 't')
            self.arrow((xa, at), (xa - 5, at))
            self.arrow((xb, at), (xb + 5, at))
        else:
            self.line(xa, at, xb, at, 't')
            self.arrow((xa, at), (xb, at))
            self.arrow((xb, at), (xa, at))
        tx = (xa + xb) / 2 + tshift
        ty = at - 0.9 if tside < 0 else at + size + 0.6
        self.text(tx, ty, txt, size, 'middle', 'td')

    def dim_v(self, x1, y1, x2, y2, at, txt, tshift=0, gap=1.0, over=1.6, tside=-1, size=2.6, arrows_out=None):
        """Vertical dimension; dimension line at paper x=at; text rotated, reads from the right."""
        for x, y in ((x1, y1), (x2, y2)):
            sgn = 1 if at > x else -1
            if abs(at - x) > gap:
                self.line(x + sgn * gap, y, at + sgn * over, y, 't')
        ya, yb = min(y1, y2), max(y1, y2)
        out = arrows_out if arrows_out is not None else (yb - ya) < 7
        if out:
            self.line(at, ya - 6, at, yb + 6, 't')
            self.arrow((at, ya), (at, ya - 5))
            self.arrow((at, yb), (at, yb + 5))
        else:
            self.line(at, ya, at, yb, 't')
            self.arrow((at, ya), (at, yb))
            self.arrow((at, yb), (at, ya))
        ty = (ya + yb) / 2 + tshift
        tx = at - 0.9 if tside < 0 else at + size + 0.4
        self.text(tx, ty, txt, size, 'middle', 'td', rot=-90)

    def leader(self, tip, elbow, txt, size=2.4, side=None, dot=False, lines=None, c='td'):
        """Leader with arrow at tip, going to elbow, then a 3 mm shoulder and text."""
        if side is None:
            side = 1 if elbow[0] >= tip[0] else -1
        self.line(tip[0], tip[1], elbow[0], elbow[1], 't')
        if dot:
            self.circle(tip[0], tip[1], 0.5, 'ah')
        else:
            self.arrow(tip, elbow)
        ex = elbow[0] + side * 3
        self.line(elbow[0], elbow[1], ex, elbow[1], 't')
        rows = [txt] if lines is None else lines
        for i, r in enumerate(rows):
            self.text(ex + side * 0.8, elbow[1] + size * 0.35 + i * size * 1.25, r, size,
                      'start' if side > 0 else 'end', c)

    def centermark(self, cx, cy, r, ext=2.5):
        self.line(cx - r - ext, cy, cx + r + ext, cy, 'c')
        self.line(cx, cy - r - ext, cx, cy + r + ext, 'c')

    def balloon(self, cx, cy, n, tip=None, r=3.4):
        if tip:
            dx, dy = tip[0] - cx, tip[1] - cy
            d = math.hypot(dx, dy) or 1
            self.line(cx + dx / d * r, cy + dy / d * r, tip[0], tip[1], 't')
            self.circle(tip[0], tip[1], 0.55, 'ah')
        self.circle(cx, cy, r, 'bal')
        self.text(cx, cy + 1.15, str(n), 3.1, 'middle', 'tx', weight='bold')

    def section_arrow(self, x, y, label, direction, size=4.2):
        """Cutting-plane end: thick stub + arrow pointing the viewing direction + letter."""
        dx, dy = direction
        self.line(x, y, x + dx * 7, y + dy * 7, 'cutw')
        self.arrow((x + dx * 7, y + dy * 7), (x, y), 'ah', L=3.2, Wd=1.1)
        self.text(x + dx * 10.5, y + dy * 10.5 + size * 0.35, label, size, 'middle', 'tx', weight='bold')

    def proj3(self, x, y, s=1.0):
        """Third-angle projection symbol, lower-left corner at (x,y), ~ 16 x 8 mm."""
        # truncated cone side view (left), circles (right)
        h = 7 * s
        self.poly([(x, y - h * 0.25), (x + 8 * s, y - h * 0.0 - h * 0.0), (x + 8 * s, y - h), (x, y - h * 0.75)], 'o2')
        # fix: cone: small end at left
        self.el.pop()
        self.poly([(x, y - h * 0.3), (x + 8 * s, y), (x + 8 * s, y - h), (x, y - h * 0.7)], 'o2')
        cx, cy = x + 13.5 * s, y - h / 2
        self.circle(cx, cy, h / 2, 'o2')
        self.circle(cx, cy, h * 0.2, 'o2')
        self.line(x - 1.5 * s, cy, x + 18.5 * s, cy, 'c')
        self.line(cx, y - h - 1.5 * s, cx, y + 1.5 * s, 'c')

    # ---------------- sheet furniture ----------------
    def frame(self, zones=True):
        th = self.th
        self.rect(0, 0, W, H, 'bgf')
        # grid inside frame
        g = []
        x = 10
        while x <= 410.01:
            major = abs((x - 10) % 25) < 1e-6
            g.append('<line x1="%s" y1="10" x2="%s" y2="287" stroke="%s" stroke-opacity="%s" stroke-width="%s"/>' % (
                f(x), f(x), th['grid'], th['g2'] if major else th['g1'], '0.16' if major else '0.1'))
            x += 5
        y = 10
        while y <= 287.01:
            major = abs((y - 10) % 25) < 1e-6
            g.append('<line x1="10" y1="%s" x2="410" y2="%s" stroke="%s" stroke-opacity="%s" stroke-width="%s"/>' % (
                f(y), f(y), th['grid'], th['g2'] if major else th['g1'], '0.16' if major else '0.1'))
            y += 5
        self.add('<g>' + ''.join(g) + '</g>')
        self.rect(5, 5, 410, 287, 'fr1')
        self.rect(10, 10, 400, 277, 'fr2')
        if zones:
            cols = 8
            for i in range(cols + 1):
                xx = 10 + i * 400 / cols
                if 0 < i < cols:
                    self.line(xx, 5, xx, 10, 'fr1')
                    self.line(xx, 287, xx, 292, 'fr1')
            for i in range(cols):
                xx = 10 + (i + 0.5) * 400 / cols
                self.text(xx, 8.6, str(i + 1), 2.4, 'middle', 'td')
                self.text(xx, 290.6, str(i + 1), 2.4, 'middle', 'td')
            rows = 'ABCDEF'
            for i in range(len(rows) + 1):
                yy = 10 + i * 277 / len(rows)
                if 0 < i < len(rows):
                    self.line(5, yy, 10, yy, 'fr1')
                    self.line(410, yy, 415, yy, 'fr1')
            for i, r in enumerate(rows):
                yy = 10 + (i + 0.5) * 277 / len(rows) + 0.9
                self.text(7.5, yy, r, 2.4, 'middle', 'td')
                self.text(412.5, yy, r, 2.4, 'middle', 'td')
            # centring marks
            for (x1, y1, x2, y2) in ((210, 0, 210, 10), (210, 287, 210, 297), (0, 148.5, 10, 148.5), (410, 148.5, 420, 148.5)):
                self.line(x1, y1, x2, y2, 'fr2')

    def title_block(self, title, variant, scale, sheet, dwg, extra_rows=None, x0=240, y0=241, w=170, h=46):
        th = self.th
        self.rect(x0, y0, w, h, 'tbf')
        c1 = x0 + 92
        c2 = c1 + 39
        r1 = y0 + 17
        r2 = y0 + 32
        self.line(c1, y0, c1, y0 + h, 'fr2t')
        self.line(c2, y0, c2, y0 + h, 'fr2t')
        self.line(x0, r1, x0 + w, r1, 'fr2t')
        self.line(x0, r2, x0 + w, r2, 'fr2t')

        def cell(x, y, label, value, vs=3.3, anchor='start', bold=True):
            self.text(x + 1.4, y + 3.0, label, 1.8, 'start', 'td')
            self.text(x + 1.4, y + 3.2 + vs + 1.8, value, vs, anchor, 'tx', weight='bold' if bold else None)

        # product mark
        self.text(x0 + 3, y0 + 12.8, 'SOUL', 10.5, 'start', 'tx', weight='bold', extra='letter-spacing="1.2"')
        self.text(x0 + 36, y0 + 7.2, 'palm-sized AI companion', 2.3, 'start', 'td')
        self.text(x0 + 36, y0 + 11.0, 'round AMOLED · two living eyes', 2.3, 'start', 'td')
        self.text(x0 + 36, y0 + 14.8, 'DWG ' + dwg, 2.3, 'start', 'td')
        cell(x0, r1, 'TITLE', title, 3.3)
        self.text(x0 + 1.4, r1 + 13.0, variant, 2.5, 'start', 'tx')
        cell(x0, r2, 'MATERIAL / FINISH', 'see notes & parts list', 2.6, bold=False)
        self.text(x0 + 1.4, r2 + 11.6, 'tol. unless noted ±0.2 · (E) = estimate', 2.1, 'start', 'td')
        cell(c1, y0, 'SCALE', scale)
        cell(c2, y0, 'UNITS', 'mm')
        cell(c1, r1, 'REV', 'A')
        cell(c2, r1, 'DATE', '2026-09-24', 3.0)
        cell(c1, r2, 'SHEET', sheet)
        cell(c2, r2, 'SIZE / PROJ.', 'A3')
        self.proj3(c2 + 18, r2 + 12.2, 0.72)

    # ---------------- output ----------------
    def svg(self):
        th = self.th
        css = """
        .bgf{fill:%(bg)s;stroke:none}
        .tbf{fill:%(paper2)s;stroke:%(fg)s;stroke-width:0.6}
        .fr1{fill:none;stroke:%(fg)s;stroke-width:0.25}
        .fr2{fill:none;stroke:%(fg)s;stroke-width:0.7}
        .fr2t{fill:none;stroke:%(fg)s;stroke-width:0.35}
        .o{fill:none;stroke:%(fg)s;stroke-width:0.5;stroke-linejoin:round;stroke-linecap:round}
        .ob{fill:%(bg)s;stroke:%(fg)s;stroke-width:0.5;stroke-linejoin:round;stroke-linecap:round}
        .o2{fill:none;stroke:%(fg)s;stroke-width:0.32;stroke-linejoin:round;stroke-linecap:round}
        .o2b{fill:%(bg)s;stroke:%(fg)s;stroke-width:0.32;stroke-linejoin:round}
        .o3{fill:none;stroke:%(fg)s;stroke-width:0.2;stroke-linejoin:round;stroke-linecap:round}
        .t{fill:none;stroke:%(dim)s;stroke-width:0.2}
        .h{fill:none;stroke:%(fg)s;stroke-width:0.28;stroke-dasharray:1.6 0.9;stroke-opacity:0.85}
        .c{fill:none;stroke:%(dim)s;stroke-width:0.18;stroke-dasharray:7 1.2 1.2 1.2}
        .ph{fill:none;stroke:%(dim)s;stroke-width:0.22;stroke-dasharray:5 1 1 1 1 1}
        .cut{fill:none;stroke:%(acc)s;stroke-width:0.3;stroke-dasharray:9 1.5 1.5 1.5}
        .cutw{fill:none;stroke:%(acc)s;stroke-width:0.9;stroke-linecap:butt}
        .ah{fill:%(dim)s;stroke:none}
        .bal{fill:%(bg)s;stroke:%(fg)s;stroke-width:0.35}
        .gl{fill:%(glass)s;fill-opacity:%(glass_op)s;stroke:%(fg)s;stroke-width:0.4}
        .f2{fill:%(fill2)s;fill-opacity:%(fill2_op)s;stroke:%(fg)s;stroke-width:0.4}
        .fb{fill:%(batt)s;fill-opacity:%(batt_op)s;stroke:%(fg)s;stroke-width:0.4}
        .solid{fill:%(fg)s;stroke:none}
        text{white-space:pre}
        .tx{fill:%(fg)s;font-family:%(font)s}
        .td{fill:%(dim)s;font-family:%(font)s}
        .ta{fill:%(acc)s;font-family:%(font)s}
        """ % dict(th, font=FONT)
        pat = """
        <pattern id="hA" patternUnits="userSpaceOnUse" width="1.1" height="1.1" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="1.1" stroke="%(fg)s" stroke-width="0.16" stroke-opacity="0.85"/></pattern>
        <pattern id="hB" patternUnits="userSpaceOnUse" width="1.1" height="1.1" patternTransform="rotate(-45)">
          <line x1="0" y1="0" x2="0" y2="1.1" stroke="%(fg)s" stroke-width="0.16" stroke-opacity="0.85"/></pattern>
        <pattern id="hC" patternUnits="userSpaceOnUse" width="0.8" height="0.8" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="0.8" stroke="%(fg)s" stroke-width="0.12" stroke-opacity="0.8"/>
          <line x1="0" y1="0" x2="0.8" y2="0" stroke="%(fg)s" stroke-width="0.12" stroke-opacity="0.8"/></pattern>
        <pattern id="hD" patternUnits="userSpaceOnUse" width="2.2" height="2.2" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="2.2" stroke="%(fg)s" stroke-width="0.14" stroke-opacity="0.6"/></pattern>
        <pattern id="hS" patternUnits="userSpaceOnUse" width="0.7" height="0.7" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="0.7" stroke="%(fg)s" stroke-width="0.22"/></pattern>
        """ % th
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%dmm" height="%dmm">\n'
                '<style>%s</style>\n<defs>%s%s</defs>\n%s\n</svg>\n') % (
            W, H, W, H, css, pat, ''.join(self.defs), '\n'.join(self.el))


# ---------------- product geometry ----------------
def outline(a, R, cy, b, n, N=240):
    """Soft oval: upper half = circle R about (0,cy) (concentric with the display),
    lower lobe = superellipse (a, b, n) below y = cy. CCW from +x."""
    pts = []
    for i in range(N):
        t = 2 * math.pi * i / N
        c, s = math.cos(t), math.sin(t)
        if s >= 0:
            pts.append((R * c, cy + R * s))
        else:
            pts.append((a * math.copysign(abs(c) ** (2 / n), c), cy - b * abs(s) ** (2 / n)))
    return pts


def half_width(y, a, R, cy, b, n):
    if y >= cy:
        d = y - cy
        return math.sqrt(max(R * R - d * d, 0))
    r = abs(y - cy) / b
    return 0 if r >= 1 else a * (1 - r ** n) ** (1 / n)


def offset_poly(pts, d):
    """Offset a closed CCW polygon inward by d (simple normal offset, fine for smooth convex)."""
    n = len(pts)
    out = []
    for i in range(n):
        x0, y0 = pts[i - 1]
        x2, y2 = pts[(i + 1) % n]
        tx, ty = x2 - x0, y2 - y0
        L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L  # left normal = inward for CCW
        out.append((pts[i][0] + nx * d, pts[i][1] + ny * d))
    return out


def arc_pts(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def profile(L, T, Rd, rf, rb, zf=0.0, nd=60):
    """Closed section profile (s, z): front plane z = zf with edge round rf, flank at |s| = L,
    back fillet rb tangent to a spherical dome of radius Rd whose apex is at (0, zf - T).
    Returns (pts, info)."""
    zc = zf - T + Rd
    fcx = L - rb
    fcz = zc - math.sqrt((Rd - rb) ** 2 - fcx ** 2)
    d = math.hypot(fcx, fcz - zc)
    tpx, tpz = fcx / d * Rd, zc + (fcz - zc) / d * Rd
    a_tp = math.degrees(math.atan2(tpz - fcz, tpx - fcx))
    right = []
    right += arc_pts(L - rf, zf - rf, rf, 90, 0, 16)           # front round
    right += arc_pts(fcx, fcz, rb, 0, a_tp, 16)                 # back fillet
    # dome from tangent point to apex
    a0 = math.degrees(math.atan2(tpz - zc, tpx))
    right += arc_pts(0, zc, Rd, a0, -90, nd)
    left = [(-x, z) for x, z in reversed(right)]
    # order: start at front centre, go right/down, around back to the left, up, back to front
    pts = [(0, zf)] + right + left[1:]
    info = dict(zc=zc, fc=(fcx, fcz), tp=(tpx, tpz), flank=(zf - rf, fcz))
    return pts, info


def dome_z(r, T, Rd, zf=0.0):
    zc = zf - T + Rd
    return zc - math.sqrt(max(Rd * Rd - r * r, 0))


def lead_l(sh, tip, y, lines, xl=13.0, size=2.3):
    """Leader whose text block starts at x = xl and ends at the shoulder (text left of the shoulder)."""
    tw = max(sh.tw(l, size) for l in lines)
    elbow = (xl + tw + 0.8 + 3.0, y)
    sh.leader(tip, elbow, '', lines=lines, size=size, side=-1)


def lead_r(sh, tip, x, y, lines, size=2.3):
    """Leader with elbow at (x, y) and text to the right."""
    sh.leader(tip, (x, y), '', lines=lines, size=size, side=1)


def tag(sh, tip, cx, cy, letter, r=2.3):
    dx, dy = tip[0] - cx, tip[1] - cy
    d = math.hypot(dx, dy) or 1
    sh.line(cx + dx / d * r, cy + dy / d * r, tip[0], tip[1], 't')
    sh.circle(tip[0], tip[1], 0.45, 'ah')
    sh.circle(cx, cy, r, 'bal')
    sh.text(cx, cy + 0.95, letter, 2.6, 'middle', 'tx', weight='bold')


def back_curve(L, T, Rd, rb, zf=0.0, nd=60):
    """Back part of the section profile from the right flank end (L, fcz) round to (-L, fcz)."""
    zc = zf - T + Rd
    fcx = L - rb
    fcz = zc - math.sqrt((Rd - rb) ** 2 - fcx ** 2)
    d = math.hypot(fcx, fcz - zc)
    tpx, tpz = fcx / d * Rd, zc + (fcz - zc) / d * Rd
    a_tp = math.degrees(math.atan2(tpz - fcz, tpx - fcx))
    right = arc_pts(fcx, fcz, rb, 0, a_tp, 12)
    a0 = math.degrees(math.atan2(tpz - zc, tpx))
    right += arc_pts(0, zc, Rd, a0, -90, nd)[1:]
    left = [(-x, z) for x, z in reversed(right)]
    return right + left[1:]
