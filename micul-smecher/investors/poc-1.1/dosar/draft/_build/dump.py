import sys, docx
from docx.table import Table
from docx.text.paragraph import Paragraph
d=docx.Document(sys.argv[1])
body=d.element.body
i=0
for el in body.iterchildren():
    tag=el.tag.split('}')[1]
    if tag=='p':
        p=Paragraph(el,d)
        cols=set()
        for r in p.runs:
            c=r.font.color
            if c is not None and c.type is not None and c.rgb is not None: cols.add(str(c.rgb))
            if r.font.highlight_color: cols.add('HL'+str(r.font.highlight_color))
        t=p.text
        if t.strip(): print(f"[{i}] P<{p.style.name}>{sorted(cols)}: {t}")
        else: print(f"[{i}] P<{p.style.name}> (empty)")
    elif tag=='tbl':
        tb=Table(el,d)
        print(f"[{i}] TABLE {len(tb.rows)}x{len(tb.columns)}")
        for ri,row in enumerate(tb.rows):
            cells=[]
            prev=None
            for c in row.cells:
                if c._tc is prev: continue
                prev=c._tc
                cols=set()
                for p in c.paragraphs:
                    for r in p.runs:
                        cc=r.font.color
                        if cc is not None and cc.type is not None and cc.rgb is not None: cols.add(str(cc.rgb))
                cells.append(c.text.replace('\n',' / ')[:150]+(str(sorted(cols)) if cols else ''))
            print(f"    r{ri}: "+" | ".join(cells))
    else: print(f"[{i}] {tag}")
    i+=1
