from kit import *
import re, base64

ROOT = "/home/user/obsidian-vault/micul-smecher/brand/logo"


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


FONT = (f"@font-face{{font-family:Mart;src:url(data:font/ttf;base64,{b64('fonts/Mart-400.ttf')})}}"
        f"@font-face{{font-family:Bric;src:url(data:font/ttf;base64,{b64('fonts/Bric-500.ttf')});font-weight:500}}"
        f"@font-face{{font-family:Bric;src:url(data:font/ttf;base64,{b64('fonts/Bric-700.ttf')});font-weight:700}}")


def sz(svgtxt, w):
    return re.sub(r'width="[\d.]+" height="[\d.]+"', f'style="width:{w}px;height:{w}px;display:block"', svgtxt, count=1)


G = {  # generic line glyphs (24-grid), white
    "sun": '<circle cx="12" cy="12" r="4.5"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    "note": '<rect x="5" y="3.5" width="14" height="17" rx="2.5"/><path d="M8.5 8.5h7M8.5 12h7M8.5 15.5h4"/>',
    "cam": '<rect x="3" y="6.5" width="18" height="13" rx="3"/><circle cx="12" cy="13" r="3.6"/><path d="M8.5 6.5l1.5-2.5h4l1.5 2.5"/>',
    "music": '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    "map": '<path d="M3 6.5l6-2.5 6 2.5 6-2.5v13.5l-6 2.5-6-2.5-6 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>',
    "photo": '<rect x="3.5" y="4.5" width="17" height="15" rx="3"/><circle cx="9" cy="10" r="1.8"/><path d="M4 17l5-4.5 4 3.5 3-2.5 4 3.5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "mail": '<rect x="3" y="5.5" width="18" height="13" rx="2.5"/><path d="M3.5 7l8.5 6 8.5-6"/>',
    "cal": '<rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/>',
    "files": '<path d="M3.5 7.5a2 2 0 012-2H10l2 2.5h6.5a2 2 0 012 2V17a2 2 0 01-2 2h-13a2 2 0 01-2-2z"/>',
    "heart": '<path d="M12 19.5s-7.5-4.6-7.5-10A4.2 4.2 0 0112 7a4.2 4.2 0 017.5 2.5c0 5.4-7.5 10-7.5 10z"/>',
    "mic": '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0013 0M12 18v2.5"/>',
    "phone": '<path d="M6.5 3.5h3l1.5 4-2 1.5a11 11 0 005.5 5.5l1.5-2 4 1.5v3a2 2 0 01-2 2A15.5 15.5 0 014.5 5.5a2 2 0 012-2z"/>',
    "chat": '<path d="M4 6.5a3 3 0 013-3h10a3 3 0 013 3v7a3 3 0 01-3 3h-6l-4.5 3.5V16.5H7a3 3 0 01-3-3z"/>',
    "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.6 2.4 3.8 5.2 3.8 8.5s-1.2 6.1-3.8 8.5c-2.6-2.4-3.8-5.2-3.8-8.5S9.4 5.9 12 3.5z"/>',
    "set": '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8"/>',
}
apps = [("Weather", "sun", "#5B8DEF", "#3A67C9"), ("Notes", "note", "#F2C94C", "#DDA92C"), ("Camera", "cam", "#8E9196", "#5E6166"),
        ("Music", "music", "#F0616D", "#C93A52"), ("Maps", "map", "#58B98A", "#2F8E62"), ("Photos", "photo", "#B98CF0", "#8A5FCB"),
        ("Clock", "clock", "#2C2E33", "#15161A"), ("Mail", "mail", "#4AA3F0", "#2378C8"), ("Calendar", "cal", "#FFFFFF", "#E9E9EC"),
        ("Files", "files", "#5A8FD8", "#3B6CB5"), ("Health", "heart", "#F78FA7", "#E0617E"), ("Recorder", "mic", "#3A3C42", "#1F2024"),
        ("SOUL", None, None, None), ("Settings", "set", "#9A9DA3", "#6E7177"), ("", None, None, None), ("", None, None, None)]
dock = [("phone", "#5ACB6B", "#2FA544"), ("chat", "#5ACB6B", "#2FA544"), ("globe", "#4AA3F0", "#2378C8"), ("music", "#F0616D", "#C93A52")]

IC = 62


def tile(g, c1, c2, ink="#fff"):
    if g is None:
        return "<div class='ic'></div>"
    stroke = "#333" if c1 == "#FFFFFF" else ink
    return (f"<div class='ic' style='background:linear-gradient(180deg,{c1},{c2})'>"
            f"<svg viewBox='0 0 24 24' width='34' height='34' fill='none' stroke='{stroke}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>{G[g]}</svg></div>")


grid = ""
for name, g, c1, c2 in apps:
    if name == "SOUL":
        grid += f"<div class='app'><div class='ic soul'>{sz(app_icon_svg(PRODUCT['silver'][1], size=1024), IC)}</div><span>SOUL</span></div>"
    elif name == "":
        grid += "<div class='app'></div>"
    else:
        grid += f"<div class='app'>{tile(g, c1, c2)}<span>{name}</span></div>"
dk = "".join(f"<div class='app'>{tile(g, c1, c2)}</div>" for g, c1, c2 in dock)

colours = "".join(f"<div class='cv'>{sz(app_icon_svg(hx, size=1024), 92)}<span>{nm}</span></div>" for nm, hx in PRODUCT.values())
html = f"""<html><head><style>{FONT}
*{{box-sizing:border-box}}
body{{margin:0;width:1600px;height:1100px;background:linear-gradient(180deg,#EFEAE1,#E2DACD);font-family:Bric;position:relative;overflow:hidden}}
.phone{{position:absolute;left:170px;top:70px;width:470px;height:960px;border-radius:78px;background:#1A1B1E;padding:14px;
 box-shadow:0 0 0 2px #7E8187,0 0 0 5px #C9CBCE,0 60px 90px -30px rgba(40,30,20,.55),0 20px 40px -20px rgba(40,30,20,.4)}}
.scr{{width:100%;height:100%;border-radius:64px;overflow:hidden;position:relative;
 background:radial-gradient(90% 60% at 20% 10%,#F7D8B5 0%,rgba(247,216,181,0) 60%),radial-gradient(80% 60% at 90% 80%,#D2622C 0%,rgba(210,98,44,0) 70%),linear-gradient(180deg,#E9C9A8 0%,#B8886A 55%,#6A4A3C 100%)}}
.island{{position:absolute;top:14px;left:50%;transform:translateX(-50%);width:26px;height:26px;top:18px;background:#0A0A0B;border-radius:50%;box-shadow:inset 0 0 0 3px #1C1D21}}
.sb{{position:absolute;top:22px;left:44px;right:40px;display:flex;justify-content:space-between;font:600 17px Bric;color:#fff}}
.grid{{position:absolute;top:96px;left:26px;right:26px;display:grid;grid-template-columns:repeat(4,1fr);row-gap:26px}}
.app{{display:flex;flex-direction:column;align-items:center;gap:7px}}
.app span{{font:500 12.5px Bric;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.25)}}
.ic{{width:{IC}px;height:{IC}px;border-radius:{IC * 0.2237:.1f}px;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.ic.soul{{box-shadow:0 8px 18px -6px rgba(0,0,0,.45)}}
.dock{{position:absolute;bottom:22px;left:18px;right:18px;height:96px;border-radius:38px;background:rgba(255,255,255,.28);backdrop-filter:blur(20px);
 display:grid;grid-template-columns:repeat(4,1fr);align-items:center}}
.dots{{position:absolute;bottom:136px;left:0;right:0;display:flex;gap:8px;justify-content:center}}
.dots i{{width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.45)}} .dots i:first-child{{background:#fff}}
.right{{position:absolute;left:760px;top:120px;width:760px}}
.big{{width:360px;height:360px;filter:drop-shadow(0 40px 50px rgba(60,40,20,.28))}}
.lbl{{font:400 12px Mart;letter-spacing:.14em;text-transform:uppercase;color:#6E685E}}
h2{{font:700 40px Bric;margin:26px 0 8px;letter-spacing:-.01em;color:#16181D}}
p{{font:400 14px/1.6 Mart;color:#4A4D55;max-width:600px;margin:0}}
.cvs{{display:flex;gap:26px;margin-top:40px}}
.cv{{display:flex;flex-direction:column;align-items:center;gap:10px;font:400 11px Mart;letter-spacing:.1em;text-transform:uppercase;color:#6E685E}}
</style></head><body>
<div class='phone'><div class='scr'><div class='island'></div><div class='sb'><span>10:24</span><span>●●● ▮</span></div>
<div class='grid'>{grid}</div><div class='dots'><i></i><i></i><i></i></div><div class='dock'>{dk}</div></div></div>
<div class='right'><div class='lbl'>App icon · companion app</div>
<div class='big' style='margin-top:26px'>{sz(app_icon_svg(PRODUCT['silver'][1], size=1024), 360)}</div>
<h2>The device, from the front.</h2>
<p>The icon is SOUL's own face on its aluminium: glass disc, cream eyes, a machined chamfer. Ship the Silver icon by default; the other finishes are alternate icons the owner can match to their SOUL.</p>
<div class='cvs'>{colours}</div></div>
</body></html>"""
render_html(html, f"{ROOT}/mockups/mockup-app-icon-phone.png", 1600, 1100, scale=1)
