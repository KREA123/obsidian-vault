from soul import *
import os
OUT="/home/user/obsidian-vault/micul-smecher/brand/logo/directions"
os.makedirs(OUT,exist_ok=True)
INK="#16181D"; CREAM="#FFF0C8"; GLASS="#0B0B0C"
FN="Bric-700"; SZ=200; CH=cap_height(FN,SZ)   # 132
# eye proportion helpers (relative to disc radius R)
def face_eyes(cx,cy,R,ccw=False,lid=True):
    rx,ry=R*0.19,R*0.30; gap=R*0.74
    return eyes(cx,cy+R*0.02,gap,rx,ry,(-ry*0.55 if lid else None),(-ry*0.30),ccw)

D={}
# A  Glass O --------------------------------------------------------------
def A_O(b):
    x0,y0,x1,y1=b; cx=(x0+x1)/2; cy=(y0+y1)/2; R=(y1-y0)/2
    return circle(cx,cy,R)+face_eyes(cx,cy,R,ccw=True)
wd,ww,_=word(FN,"SOUL",SZ,0,CH+10,0.03,{"O":A_O})
R=110
D["A"]=dict(name="Glass O",note="The O is SOUL's face: a black glass disc with two living eyes.",
  sym=f'<path fill-rule="evenodd" d="{circle(130,130,R)}{face_eyes(130,130,R,True)}" />',
  word=f'<path fill-rule="evenodd" d="{wd}"/>',ww=ww)
# B  Pebble ---------------------------------------------------------------
def peb(cx,cy,s,ccw=False):
    return pebble(cx,cy,s*0.93,s*0.86,s*1.0,yr=-s*0.18,kt=0.80,ks=0.72,kb=0.74,kbs=0.78,ccw=ccw)
s=118
body=peb(130,130,s)+circle(130,128,s*0.70,ccw=True)+circle(130,128,s*0.60)+face_eyes(130,128,s*0.60,True)
wd,ww,_=text(FN,"SOUL",SZ,0,CH+10,0.09)
D["B"]=dict(name="Pebble",note="The product silhouette as a pictogram; quiet spaced wordmark.",
  sym=f'<path fill-rule="evenodd" d="{body}"/>',word=f'<path d="{wd}"/>',ww=ww)
# C  Lidded counter -------------------------------------------------------
def C_O(b):
    x0,y0,x1,y1=b; cx=(x0+x1)/2; cy=(y0+y1)/2; R=(y1-y0)/2
    rx,ry=R*0.36,R*0.62
    return circle(cx,cy,R*1.0)+eye(cx,cy+R*0.08,rx,ry,-ry*0.60,-ry*0.18,"L",ccw=True)
wd,ww,_=word("Bric-800","SOUL",SZ,0,CH+10,0.03,{"O":C_O})
Rs=112
D["C"]=dict(name="Lidded Counter",note="A custom O whose counter is one half-lidded eye: the wordmark itself glances.",
  sym=f'<path fill-rule="evenodd" d="{C_O((130-Rs,130-Rs,130+Rs,130+Rs))}"/>',word=f'<path fill-rule="evenodd" d="{wd}"/>',ww=ww)
# D  Orbit ----------------------------------------------------------------
import math
def arc(cx,cy,r,a0,a1):
    p=lambda a:(cx+r*math.cos(math.radians(a)),cy+r*math.sin(math.radians(a)))
    x0,y0=p(a0);x1,y1=p(a1)
    return f"M{f(x0)} {f(y0)}A{f(r)} {f(r)} 0 0 1 {f(x1)} {f(y1)}"
sym=(f'<circle cx="130" cy="130" r="108" fill="none" stroke="currentColor" stroke-width="10"/>'
     f'<path d="{arc(130,130,108,40,140)}" fill="none" stroke="currentColor" stroke-width="26" stroke-linecap="round"/>'
     f'<path d="{face_eyes(130,122,96)}"/>')
wd,ww,_=text("Mart-500","SOUL",SZ*0.92,0,CH+10,0.16)
D["D"]=dict(name="Orbit",note="Glass ring, eyes and the SoulOS orbit arc on the lower rim; mono wordmark.",
  sym=sym,word=f'<path d="{wd}"/>',ww=ww)
# E  Blink ----------------------------------------------------------------
def E_O(b):
    x0,y0,x1,y1=b; cx=(x0+x1)/2; cy=(y0+y1)/2; ry=(y1-y0)/2*1.04
    rx=ry*0.62
    return eye(cx,cy+ry*0.04,rx,ry,-ry*0.98,-ry*0.62,"L")
wd,ww,_=word(FN,"SOUL",SZ,0,CH+10,0.03,{"O":E_O},kern={0:-6,1:-6})
D["E"]=dict(name="Blink",note="The eyes are the whole mark. In the wordmark the O becomes one solid lidded eye.",
  sym=f'<path d="{eyes(130,134,108,36,62,-30,-14)}"/>',word=f'<path d="{wd}"/>',ww=ww)
# F  Grid monogram --------------------------------------------------------
fs=112
g=""
for ch,(x,y) in zip("SUL",[(0,0),(0,1),(1,1)]):
    d,adv,bb=glyph(FN,ch,fs,0,0)
    bw=bb[2]-bb[0]; bh=bb[3]-bb[1]
    cx=76+x*108; cy=76+y*108
    d,adv,bb=glyph(FN,ch,fs,cx-bw/2-bb[0],cy+bh/2)
    g+=d
cx,cy=184,76
g+=circle(cx,cy,39)+face_eyes(cx,cy,39,True)
tile=rrect(10,10,240,240,64)
D["F"]=dict(name="Grid Monogram",note="S O / U L on a 2x2 grid in a rounded tile; the O is the face.",
  sym=f'<path fill-rule="evenodd" d="{tile}"/><path fill="BGC" fill-rule="evenodd" d="{g}"/>',
  word=f'<path fill-rule="evenodd" d="{text(FN,"SOUL",SZ,0,CH+10,0.06)[0]}"/>',ww=text(FN,"SOUL",SZ,0,CH+10,0.06)[1])

import json
for k,v in D.items():
    open(f"{OUT}/{k}_{v['name'].lower().replace(' ','-')}_symbol.svg","w").write(svg(260,260,f'<g fill="{INK}" color="{INK}">{v["sym"].replace("BGC","#FFFFFF")}</g>'))
    open(f"{OUT}/{k}_{v['name'].lower().replace(' ','-')}_wordmark.svg","w").write(svg(v["ww"]+20,CH+20,f'<g fill="{INK}" transform="translate(10,0)">{v["word"]}</g>'))
json.dump(D,open("dirs.json","w"))

# contact sheet ---------------------------------------------------------
cards=""
for k,v in D.items():
    sc=min(1, 420/v["ww"])
    def blk(fg,bg,eyec):
        symfill=fg
        return (f'<div class="p" style="background:{bg};color:{fg}">'
          f'<svg viewBox="0 0 260 260" width="150" height="150"><g fill="{fg}" color="{fg}">{v["sym"].replace("BGC",bg)}</g></svg>'
          f'<svg viewBox="-10 0 {v["ww"]+20} {CH+20}" width="{(v["ww"]+20)*0.62*sc:.0f}"><g fill="{fg}">{v["word"]}</g></svg></div>')
    cards+=(f'<div class="c" style="{"outline:3px solid #D2622C" if k=="A" else ""}"><div class="h"><b>{k}</b> {v["name"]}{" &nbsp;<span style=color:#D2622C>&#10003; chosen</span>" if k=="A" else ""}</div>'
            f'<div class="row">{blk(INK,"#F3EFE8",CREAM)}{blk(CREAM,"#0E0F12",CREAM)}</div>'
            f'<div class="n">{v["note"]}</div></div>')
html=f"""<html><head><style>
body{{margin:0;background:#E6E1D8;font-family:sans-serif;color:#16181D}}
.wrap{{padding:40px;display:grid;grid-template-columns:1fr 1fr;gap:28px}}
h1{{grid-column:1/3;margin:0;font:600 26px sans-serif;letter-spacing:.02em}}
.c{{background:#fff;border-radius:18px;padding:18px}}
.h{{font:600 18px sans-serif;margin-bottom:12px}} .h b{{display:inline-block;width:28px;height:28px;border-radius:50%;background:#16181D;color:#fff;text-align:center;line-height:28px;margin-right:8px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.p{{height:300px;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px}}
.n{{margin-top:12px;font-size:15px;color:#555}}
</style></head><body><div class="wrap"><h1>SOUL — six logo directions · chosen: A, Glass O (refined in the brand kit)</h1>{cards}</div></body></html>"""
open("sheet.html","w").write(html)
render_html(html,"/home/user/obsidian-vault/micul-smecher/brand/logo/logo-directions.png",1600,1420)
