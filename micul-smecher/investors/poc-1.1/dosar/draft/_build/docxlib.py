"""Small helpers to fill the official .docx templates in place (python-docx + lxml)."""
import copy, re
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def W(t):
    return qn('w:' + t)

RPR_ORDER = ['rStyle', 'rFonts', 'b', 'bCs', 'i', 'iCs', 'caps', 'smallCaps', 'strike', 'dstrike',
             'outline', 'shadow', 'emboss', 'imprint', 'noProof', 'snapToGrid', 'vanish', 'webHidden',
             'color', 'spacing', 'w', 'kern', 'position', 'sz', 'szCs', 'highlight', 'u', 'effect',
             'bdr', 'shd', 'fitText', 'vertAlign', 'rtl', 'cs', 'em', 'lang', 'eastAsianLayout',
             'specVanish', 'oMath']
PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr', 'widowControl', 'numPr',
             'suppressLineNumbers', 'pBdr', 'shd', 'tabs', 'suppressAutoHyphens', 'kinsoku', 'wordWrap',
             'overflowPunct', 'topLinePunct', 'autoSpaceDE', 'autoSpaceDN', 'bidi', 'adjustRightInd',
             'snapToGrid', 'spacing', 'ind', 'contextualSpacing', 'mirrorIndents', 'suppressOverlap', 'jc',
             'textDirection', 'textAlignment', 'textboxTightWrap', 'outlineLvl', 'divId', 'cnfStyle',
             'rPr', 'sectPr', 'pPrChange']


def _insert_ordered(parent, el, order):
    name = el.tag.split('}')[1]
    idx = order.index(name)
    for i, ch in enumerate(parent):
        cn = ch.tag.split('}')[1]
        if cn in order and order.index(cn) > idx:
            parent.insert(i, el)
            return el
    parent.append(el)
    return el


def set_rpr(rpr, tag, val=None):
    for old in rpr.findall(W(tag)):
        rpr.remove(old)
    el = OxmlElement('w:' + tag)
    if val is not None:
        el.set(W('val'), str(val))
    return _insert_ordered(rpr, el, RPR_ORDER)


def del_rpr(rpr, *tags):
    for t in tags:
        for old in rpr.findall(W(t)):
            rpr.remove(old)


def ptext(el):
    return ''.join(t.text or '' for t in el.iter(W('t')))


TOKEN = re.compile(r'(\*\*.+?\*\*|\[\[.+?\]\])')


def first_rpr(p):
    r = p.find(W('r'))
    if r is not None and r.find(W('rPr')) is not None:
        return copy.deepcopy(r.find(W('rPr')))
    ppr = p.find(W('pPr'))
    if ppr is not None and ppr.find(W('rPr')) is not None:
        x = copy.deepcopy(ppr.find(W('rPr')))
        x.tag = W('rPr')
        return x
    return OxmlElement('w:rPr')


def write_runs(p, text, base_rpr=None, plain=True, size=None, bold_all=False, color=None):
    """Replace all runs of paragraph p with text; **bold** and [[placeholder]] markup."""
    if base_rpr is None:
        base_rpr = first_rpr(p)
    for ch in list(p):
        if ch.tag != W('pPr'):
            p.remove(ch)
    for part in TOKEN.split(text):
        if not part:
            continue
        bold = hl = False
        if part.startswith('**') and part.endswith('**'):
            part, bold = part[2:-2], True
        elif part.startswith('[[') and part.endswith(']]'):
            part, hl = '[' + part[2:-2] + ']', True
        r = OxmlElement('w:r')
        rpr = copy.deepcopy(base_rpr)
        if plain:
            del_rpr(rpr, 'color', 'i', 'iCs', 'highlight', 'shd', 'b', 'bCs')
        if bold or bold_all:
            set_rpr(rpr, 'b')
            set_rpr(rpr, 'bCs')
        if hl:
            set_rpr(rpr, 'highlight', 'yellow')
        if color:
            set_rpr(rpr, 'color', color)
        if size:
            set_rpr(rpr, 'sz', size)
            set_rpr(rpr, 'szCs', size)
        r.append(rpr)
        t = OxmlElement('w:t')
        t.text = part
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t)
        p.append(r)
    return p


def clone_par(p, text, numid=None, plain=True, keep_num=False):
    np_ = copy.deepcopy(p)
    ppr = np_.find(W('pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr')
        np_.insert(0, ppr)
    if not keep_num:
        for n in ppr.findall(W('numPr')):
            ppr.remove(n)
    if numid is not None:
        num = OxmlElement('w:numPr')
        il = OxmlElement('w:ilvl'); il.set(W('val'), '0')
        ni = OxmlElement('w:numId'); ni.set(W('val'), str(numid))
        num.append(il); num.append(ni)
        _insert_ordered(ppr, num, PPR_ORDER)
    write_runs(np_, text, base_rpr=first_rpr(p), plain=plain)
    return np_


# ---------------------------------------------------------------- tables

def rows(tbl):
    return tbl.findall(W('tr'))


def tcs(tr):
    return tr.findall(W('tc'))


def row_text(tr):
    return ptext(tr)


def set_cell(tc, text, plain=True, size=None, bold=False, align=None):
    ps = tc.findall(W('p'))
    p0 = ps[0]
    base = first_rpr(p0)
    for extra in ps[1:]:
        tc.remove(extra)
    lines = text.split('\n') if isinstance(text, str) else text
    write_runs(p0, lines[0], base_rpr=base, plain=plain, size=size, bold_all=bold)
    if align:
        ppr = p0.find(W('pPr'))
        if ppr is None:
            ppr = OxmlElement('w:pPr'); p0.insert(0, ppr)
        for j in ppr.findall(W('jc')):
            ppr.remove(j)
        jc = OxmlElement('w:jc'); jc.set(W('val'), align)
        _insert_ordered(ppr, jc, PPR_ORDER)
    prev = p0
    for ln in lines[1:]:
        np_ = copy.deepcopy(p0)
        write_runs(np_, ln, base_rpr=base, plain=plain, size=size, bold_all=bold)
        prev.addnext(np_)
        prev = np_


def fill_row(tr, values, **kw):
    cells = tcs(tr)
    for c, v in zip(cells, values):
        if v is not None:
            set_cell(c, v, **kw)


def add_row_after(tr, values=None, **kw):
    n = copy.deepcopy(tr)
    tr.addnext(n)
    if values is not None:
        fill_row(n, values, **kw)
    return n


def fill_table_rows(tbl, first_data_idx, data, proto_idx=None, **kw):
    """Fill data rows starting at first_data_idx; add rows (cloning proto) as needed; drop surplus."""
    rs = rows(tbl)
    proto = rs[proto_idx if proto_idx is not None else first_data_idx]
    existing = rs[first_data_idx:first_data_idx + len(data)]
    template_count = None
    # rows after the data block (e.g. totals) are identified by caller via proto range
    last = None
    for i, vals in enumerate(data):
        if i < len(existing):
            tr = existing[i]
            fill_row(tr, vals, **kw)
            last = tr
        else:
            last = add_row_after(last, vals, **kw)
    return last


def delete(el):
    el.getparent().remove(el)


def build_table(proto_tbl, header, data, widths, hdr_idx=0, data_idx=1, size=None, compact=False,
                bold_first_col=False, center_cols=()):
    t = copy.deepcopy(proto_tbl)
    rs = rows(t)
    hdr_proto = copy.deepcopy(rs[hdr_idx])
    dat_proto = copy.deepcopy(rs[data_idx])
    for r in rs:
        t.remove(r)
    tblpr = t.find(W('tblPr'))
    tw = tblpr.find(W('tblW'))
    if tw is not None:
        tw.set(W('w'), str(sum(widths))); tw.set(W('type'), 'dxa')
    lay = tblpr.find(W('tblLayout'))
    if lay is None:
        lay = OxmlElement('w:tblLayout')
        for ch in tblpr:
            if ch.tag.split('}')[1] in ('tblCellMar', 'tblLook', 'tblCaption', 'tblDescription'):
                ch.addprevious(lay); break
        else:
            tblpr.append(lay)
    lay.set(W('type'), 'fixed')
    grid = t.find(W('tblGrid'))
    for g in list(grid):
        grid.remove(g)
    for w in widths:
        g = OxmlElement('w:gridCol'); g.set(W('w'), str(w)); grid.append(g)

    def mk(proto, vals, is_hdr):
        tr = copy.deepcopy(proto)
        trpr = tr.find(W('trPr'))
        if trpr is not None:
            for tag in ('gridBefore', 'wBefore', 'gridAfter', 'wAfter'):
                for x in trpr.findall(W(tag)):
                    trpr.remove(x)
        for x in tr.findall(W('tblPrEx')):
            tr.remove(x)
        cells = tcs(tr)
        ptc = cells[0] if is_hdr else (cells[1] if len(cells) > 1 else cells[0])
        for c in cells:
            tr.remove(c)
        for j, (w, v) in enumerate(zip(widths, vals)):
            c = copy.deepcopy(ptc)
            tcpr = c.find(W('tcPr'))
            for x in tcpr.findall(W('gridSpan')) + tcpr.findall(W('vMerge')):
                tcpr.remove(x)
            tcw = tcpr.find(W('tcW'))
            tcw.set(W('w'), str(w)); tcw.set(W('type'), 'dxa')
            if compact:
                mar = tcpr.find(W('tcMar'))
                if mar is not None:
                    for side in mar:
                        side.set(W('w'), '30')
            al = 'center' if (is_hdr or j in center_cols) else 'left'
            set_cell(c, v if v is not None else '', plain=not is_hdr, size=size,
                     bold=(bold_first_col and j == 0 and not is_hdr), align=al)
            tr.append(c)
        return tr
    t.append(mk(hdr_proto, header, True))
    for vals in data:
        t.append(mk(dat_proto, vals, False))
    return t


def set_widths(tbl, widths):
    grid = tbl.find(W('tblGrid'))
    for g in list(grid):
        grid.remove(g)
    for w in widths:
        g = OxmlElement('w:gridCol'); g.set(W('w'), str(w)); grid.append(g)
    for tr in rows(tbl):
        cs = tcs(tr)
        if len(cs) == len(widths):
            for c, w in zip(cs, widths):
                c.find(W('tcPr')).find(W('tcW')).set(W('w'), str(w))


def set_widths_gb(tbl, widths, before=10):
    """For tables whose rows start with gridBefore: grid = [before] + widths + [rest]."""
    total = int(tbl.find(W('tblPr')).find(W('tblW')).get(W('w')))
    grid_w = [before] + list(widths) + [max(total - before - sum(widths), 8)]
    grid = tbl.find(W('tblGrid'))
    for g in list(grid):
        grid.remove(g)
    for w in grid_w:
        g = OxmlElement('w:gridCol'); g.set(W('w'), str(w)); grid.append(g)
    for tr in rows(tbl):
        cs = tcs(tr)
        if len(cs) == len(widths):
            for c, w in zip(cs, widths):
                c.find(W('tcPr')).find(W('tcW')).set(W('w'), str(w))


def normalize_table(tbl, widths):
    """Drop gridBefore/After and spans; single-cell rows span all columns; grid = widths."""
    n = len(widths)
    tp = tbl.find(W('tblPr'))
    tw = tp.find(W('tblW'))
    if tw is not None:
        tw.set(W('w'), str(sum(widths))); tw.set(W('type'), 'dxa')
    ind = tp.find(W('tblInd'))
    if ind is not None:
        ind.set(W('w'), '0')
    for tr in rows(tbl):
        trpr = tr.find(W('trPr'))
        if trpr is not None:
            for tag in ('gridBefore', 'wBefore', 'gridAfter', 'wAfter'):
                for x in trpr.findall(W(tag)):
                    trpr.remove(x)
        for x in tr.findall(W('tblPrEx')):
            pass
        cs = tcs(tr)
        for c in cs:
            for x in c.find(W('tcPr')).findall(W('gridSpan')):
                c.find(W('tcPr')).remove(x)
        if len(cs) == 1 and n > 1:
            gs = OxmlElement('w:gridSpan'); gs.set(W('val'), str(n))
            tcpr = cs[0].find(W('tcPr'))
            tcpr.find(W('tcW')).addnext(gs)
            tcpr.find(W('tcW')).set(W('w'), str(sum(widths)))
        elif len(cs) == n:
            for c, w in zip(cs, widths):
                c.find(W('tcPr')).find(W('tcW')).set(W('w'), str(w))
    grid = tbl.find(W('tblGrid'))
    for g in list(grid):
        grid.remove(g)
    for w in widths:
        g = OxmlElement('w:gridCol'); g.set(W('w'), str(w)); grid.append(g)


W14 = '{http://schemas.microsoft.com/office/word/2010/wordml}'


def finalize(doc):
    """Strip duplicated w14 paragraph ids created by cloning; keep rows from splitting."""
    for el in doc.element.body.iter():
        for a in (W14 + 'paraId', W14 + 'textId'):
            if a in el.attrib:
                del el.attrib[a]
    for tr in doc.element.body.iter(W('tr')):
        trpr = tr.find(W('trPr'))
        if trpr is None:
            trpr = OxmlElement('w:trPr'); tr.insert(0 if tr.find(W('tblPrEx')) is None else 1, trpr)
        if trpr.find(W('cantSplit')) is None:
            cs = OxmlElement('w:cantSplit')
            for ch in trpr:
                if ch.tag.split('}')[1] in ('trHeight', 'tblHeader', 'tblCellSpacing', 'jc', 'hidden', 'ins', 'del', 'trPrChange'):
                    ch.addprevious(cs); break
            else:
                trpr.append(cs)
