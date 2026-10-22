import re, markdown, sys
src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
s = re.sub(r"^---\n.*?\n---\n", "", s, flags=re.S)
s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
LI = re.compile(r"^(\s*[-*] |\s*\d+\. )")
fixed = []
for ln in s.split("\n"):
    prev = fixed[-1] if fixed else ""
    if LI.match(ln) and prev.strip() and not LI.match(prev) and not prev.startswith(" "):
        fixed.append("")
    if ln.startswith("|") and prev.strip() and not prev.startswith("|"):
        fixed.append("")
    fixed.append(ln)
s = "\n".join(fixed)
body = markdown.markdown(s, extensions=["tables", "sane_lists"])
css = """
@page { size: A4; margin: 14mm 13mm 15mm 13mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'DejaVu Sans', 'Noto Sans', 'Liberation Sans', sans-serif; font-size: 9.2pt; line-height: 1.4; color: #1b1b1f; background: #fff; }
h1 { font-size: 19pt; margin: 0 0 6pt; border-bottom: 2px solid #1b1b1f; padding-bottom: 4pt; }
h2 { font-size: 13pt; margin: 14pt 0 5pt; color: #0d3b66; break-after: avoid; }
p, li { margin: 3pt 0; }
ul, ol { padding-left: 16pt; margin: 3pt 0; }
blockquote { margin: 4pt 0 8pt; padding: 4pt 8pt; background: #f2f4f7; border-left: 3px solid #0d3b66; font-size: 8.5pt; }
blockquote p { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 8pt; font-size: 7.8pt; break-inside: auto; }
tr { break-inside: avoid; }
th, td { border: 0.6pt solid #b9bec7; padding: 2.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #e6ebf2; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.8pt; background: #f2f4f7; padding: 0 2pt; word-break: break-all; }
a { color: #0d3b66; text-decoration: none; word-break: break-word; }
strong { color: #000; }
.foot { margin-top: 12pt; font-size: 7.5pt; color: #666; }
"""
html = f"""<!doctype html><html lang="ro"><head><meta charset="utf-8"><title>SOUL — Fabrică și lanț de producție</title><style>{css}</style></head>
<body>{body}<p class="foot">ARTEMIS DIGITAL S.R.L. · SOUL · actualizat 2026-10-22 (mărimea S) · [estimare] = calcul fără ofertă · [neverificat] = sursă unică sau nereverificată</p></body></html>"""
open(out, "w", encoding="utf-8").write(html)
