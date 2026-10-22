#!/usr/bin/env python3
"""SOUL campaign video: build the ROUGH CUT (1920x1080) and the vertical TEASER (1080x1920) from existing material.

    python3 -I micul-smecher/crowdfunding/video/build/build.py            # both
    python3 -I micul-smecher/crowdfunding/video/build/build.py --only rough
    python3 -I micul-smecher/crowdfunding/video/build/build.py --only teaser

What it does
- Cuts clips from the trailer, the v9 launch film and the eyes-engine recordings (only scale-neutral moments:
  NO hand or desk shot, because those show the M size), stills from SoulOS simulator shots and campaign images.
- Every shot that does not exist yet becomes a "[PROTOTYPE SHOT — to film]" title card with the shot brief
  from ../script.md (same ids F01..F10).
- Every frame carries its honesty label (render / eyes engine / SoulOS / illustration) from ../../facts.json -> labels.
- The voice-over text is burned in as captions so the cut reads without sound. NO audio: the track is a silent
  AAC stream. Music and voice are added only in the final edit, with a licence (see script.md, "Music").
- Writes ../subtitles/*.srt (EN + RO) and build/timeline.json with the real timecodes of this cut.

Size-dependent facts (S dims, screen, prices, dates) come from facts.json; nothing size-dependent is hard-coded.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.dirname(HERE)                      # crowdfunding/video
CF = os.path.dirname(VID)                        # crowdfunding
MS = os.path.dirname(CF)                         # micul-smecher
sys.path.insert(0, os.path.join(CF, "tools"))
from facts import load as load_facts, month as fmonth  # noqa: E402
FACTS = load_facts()
NUM_EN = {2: "two", 3: "three", 4: "four", 5: "five"}
NUM_RO = {2: "două", 3: "trei", 4: "patru", 5: "cinci"}
CE_OK = FACTS["gates"]["CE"]["passed"]
DERIVED = {
    "colours_n_word": NUM_EN[len(FACTS["colours"])].capitalize(),
    "colours_n_word_ro": NUM_RO[len(FACTS["colours"])].capitalize(),
    "delivery_eu": fmonth(FACTS["scn"]["estimated_delivery"]["EU"]),
    "delivery_eu_ro": fmonth(FACTS["scn"]["estimated_delivery"]["EU"], "ro"),
    "ce_vo": ("SOUL passed its CE tests, and the EU Declaration of Conformity is signed." if CE_OK else
              ("SOUL isn't CE-certified yet. This campaign opens only after it passes." if FACTS["campaign"]["scenario"] == "after_ce" else
               "SOUL isn't CE-certified yet. It ships only after it passes the lab.")),
    "ce_vo_ro": ("SOUL a trecut testele CE, iar declarația UE de conformitate e semnată." if CE_OK else
                 ("SOUL nu are încă certificare CE. Campania se deschide abia după ce trece testele." if FACTS["campaign"]["scenario"] == "after_ce" else
                  "SOUL nu are încă certificare CE. Se livrează doar după ce trece testele de laborator.")),
}
SEG = json.load(open(os.path.join(HERE, "segments.json"), encoding="utf-8"))

FONT_B = os.path.join(MS, "brand/SOUL-Brand-Package/Fonts/Bricolage-Grotesque/BricolageGrotesque[opsz,wdth,wght].ttf")
FONT_M = os.path.join(MS, "brand/SOUL-Brand-Package/Fonts/Martian-Mono/MartianMono[wdth,wght].ttf")
LOGO = os.path.join(MS, "brand/SOUL-Brand-Package/Logo/Lockup-Stacked-Tagline/PNG/SOUL-Lockup-Stacked-Tagline-On-Dark_1024px.png")
WORDMARK_DIR = os.path.join(MS, "brand/SOUL-Brand-Package/Logo/Wordmark/PNG")

GLASS = (11, 11, 12)
CREAM = (255, 240, 200)
WARM = (246, 243, 236)
EMBER = (210, 98, 44)
DIM = (150, 150, 155)
FPS = 30
BUILD_DATE = "2026-10-22b"

# ------------------------------------------------------------------------------------------------ text
_fc = {}
def font(kind, size, style="Bold"):
    key = (kind, size, style)
    if key not in _fc:
        f = ImageFont.truetype(FONT_B if kind == "b" else FONT_M, size)
        try:
            f.set_variation_by_name(style)
        except Exception:
            pass
        _fc[key] = f
    return _fc[key]

def fill_vars(s):
    """{{path.to.fact}} -> value from facts.json (keeps size facts in one place)."""
    out, i = "", 0
    while True:
        j = s.find("{{", i)
        if j < 0:
            return out + s[i:]
        k = s.find("}}", j)
        key, fmt = s[j + 2:k], None
        if key in DERIVED:
            out += s[i:j] + DERIVED[key]
            i = k + 2
            continue
        if key.startswith("month:") or key.startswith("month_ro:"):
            fmt, key = key.split(":", 1)
        v = FACTS
        for p in key.split("."):
            v = v[int(p)] if isinstance(v, list) else v[p]
        out += s[i:j] + (month_name(v, fmt == "month_ro") if fmt else str(v))
        i = k + 2

def wrap_px(text, f, max_w):
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if f.getlength(t) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines

def pill(d, xy, text, f, fg=WARM, bg=(0, 0, 0, 170), dot=None, pad=(18, 10)):
    x, y = xy
    tw = f.getlength(text)
    asc, desc = f.getmetrics()
    h = asc + desc + pad[1] * 2
    dx = 22 if dot else 0
    d.rounded_rectangle([x, y, x + tw + pad[0] * 2 + dx, y + h], radius=h // 2, fill=bg, outline=(255, 255, 255, 60), width=1)
    if dot:
        cy = y + h // 2
        d.ellipse([x + pad[0], cy - 5, x + pad[0] + 10, cy + 5], fill=dot)
    d.text((x + pad[0] + dx, y + pad[1]), text, font=f, fill=fg)
    return x + tw + pad[0] * 2 + dx, y + h

# ------------------------------------------------------------------------------------------------ overlays
def label_text(key):
    if not key:
        return None, None
    L = FACTS["labels"]
    table = {
        "render": ("RENDER (CGI), NOT A PHOTO", EMBER),
        "trailer": ("TRAILER: RENDERS (CGI) + SOULOS SCREENS. NOT REAL FOOTAGE", EMBER),
        "eyes": ("EYES ENGINE: SCREEN ANIMATION FROM THE DEVICE CODE, NOT A PHOTO", (90, 140, 255)),
        "soulos_sim": ("SOULOS SIMULATOR CAPTURE, 480 × 480. ON S: {} × {} AMOLED".format(*FACTS["size_S"]["screen"]["resolution_px"]), (90, 140, 255)),
        "soulos_s": ("SOULOS SIMULATOR CAPTURE AT S SIZE, {} × {}. NOT A REAL DEVICE".format(*FACTS["size_S"]["screen"]["resolution_px"]), (90, 140, 255)),
        "render_eyes": ("RENDER (CGI), NOT A PHOTO · EYES FROM THE EYES ENGINE", EMBER),
        "soulos_web": ("SOULOS WEB PROTOTYPE, 480 × 480. ON S: {} × {} AMOLED".format(*FACTS["size_S"]["screen"]["resolution_px"]), (90, 140, 255)),
        "illustration": ("ILLUSTRATION", DIM),
        "true_scale": ("ILLUSTRATION · TRUE SCALE", DIM),
        "card": ("ROUGH-CUT TITLE CARD", DIM),
        "prototype_m": (L["prototype_footage"].upper(), EMBER),
    }
    return table[key]

def overlay(W, H, seg, section, vertical=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = 1.0 if not vertical else 1.05
    m = int(36 * s)
    # top-left: honesty label
    lt, col = label_text(seg.get("label"))
    fl = font("m", int(19 * s), "Medium")
    if lt:
        maxw = W - 2 * m
        if fl.getlength(lt) + 80 > maxw:
            for ln_i, ln in enumerate(wrap_px(lt, fl, maxw - 80)):
                pill(d, (m, m + ln_i * int(50 * s)), ln, fl, dot=col if ln_i == 0 else None)
        else:
            pill(d, (m, m), lt, fl, dot=col)
    # top-right (or bottom on vertical): rough-cut stamp + section
    fs = font("m", int(16 * s), "Regular")
    stamp = f"ROUGH CUT · NOT FOR PUBLISHING · GUIDE VOICE = TTS · {BUILD_DATE}"
    sec = f"{section['num']} {section['name'].upper()}  ·  {seg['id']}"
    if section.get("publishable"):
        stamp, sec = "", ""
    if not vertical:
        d.text((W - m - fs.getlength(stamp), m + 2), stamp, font=fs, fill=(255, 255, 255, 150))
        d.text((W - m - fs.getlength(sec), m + 26), sec, font=fs, fill=(255, 255, 255, 150))
    else:
        y0 = int(H * 0.115)
        d.text((m, y0), stamp, font=fs, fill=(255, 255, 255, 150))
        d.text((m, y0 + 26), sec, font=fs, fill=(255, 255, 255, 150))
    # optional stand-in banner: one small line under the label (the final shot is real footage)
    if seg.get("standin"):
        fb = font("m", int(19 * s), "Bold")
        t = "[PROTOTYPE SHOT — to film] " + seg["standin"]
        y = m + int(56 * s) if not vertical else int(H * 0.16)
        for ln in wrap_px(t, fb, W - 2 * m - 60)[:2]:
            pill(d, (m, y), ln, fb, fg=(20, 20, 20), bg=(255, 240, 200, 235), pad=(14, 8))
            y += int(44 * s)
    # caption (voice-over text)
    cap = fill_vars(seg.get("vo", "")) if seg.get("caption", True) else ""
    by = H
    if cap:
        fc = font("b", int(40 * s) if not vertical else 50, "Medium")
        maxw = int(W * (0.78 if not vertical else 0.86))
        lines = wrap_px(cap, fc, maxw)
        asc, desc = fc.getmetrics()
        lh = asc + desc + 6
        bh = lh * len(lines) + 30
        by = H - bh - (int(60 * s) if not vertical else int(H * 0.22))
        if seg.get("cap_pos") == "top":
            by = int(H * 0.25)
        bw = max(fc.getlength(l) for l in lines) + 60
        bx = (W - bw) // 2
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=18, fill=(0, 0, 0, 185))
        y = by + 15
        for l in lines:
            d.text(((W - fc.getlength(l)) // 2, y), l, font=fc, fill=WARM)
            y += lh
    # on-screen note (a fact line that must be visible, e.g. "ChatGPT: in development")
    note = seg.get("note")
    if note:
        fn = font("m", int(20 * s), "Medium")
        note = fill_vars(note)
        lines = wrap_px(note, fn, W - 2 * m - 60)
        y = (H - int(250 * s)) if not vertical else int(H * 0.70)
        if seg.get("vo") and not vertical:
            y = (by if cap else H - 60) - 14 - int(48 * s) * len(lines)   # just above the caption band, below the round screen
        for ln in lines:
            pill(d, ((W - fn.getlength(ln) - 36) // 2, y), ln, fn, bg=(30, 30, 34, 220))
            y += int(48 * s)
    return im

# ------------------------------------------------------------------------------------------------ cards
def bg_glass(W, H):
    im = Image.new("RGB", (W, H), GLASS)
    g = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(g)
    gd.ellipse([W * 0.15, -H * 0.4, W * 0.85, H * 0.6], fill=28)
    g = g.filter(ImageFilter.GaussianBlur(min(W, H) // 5))
    im.paste(Image.new("RGB", (W, H), (40, 40, 46)), (0, 0), g)
    return im

def film_card(W, H, shot, vertical=False):
    im = bg_glass(W, H)
    d = ImageDraw.Draw(im)
    m = 120 if not vertical else 80
    y = int(H * 0.17) if not vertical else int(H * 0.22)
    fk = font("m", 30 if not vertical else 34, "Bold")
    d.text((m, y), "[PROTOTYPE SHOT — to film]", font=fk, fill=EMBER)
    y += 70
    ft = font("b", 76 if not vertical else 80, "ExtraBold")
    for ln in wrap_px(f"{shot['id']} · {shot['title']}", ft, W - 2 * m):
        d.text((m, y), ln, font=ft, fill=WARM)
        y += 88
    y += 20
    fb = font("b", 32 if not vertical else 38, "Regular")
    fh = font("m", 20 if not vertical else 24, "Medium")
    for k in ("action", "framing", "proof"):
        if k not in shot:
            continue
        d.text((m, y + 8), {"action": "ACTION", "framing": "FRAMING", "proof": "PROOF"}[k], font=fh, fill=DIM)
        col = m + (190 if not vertical else 0)
        if vertical:
            y += 40
        for ln in wrap_px(fill_vars(shot[k]), fb, W - col - m):
            d.text((col, y), ln, font=fb, fill=(220, 220, 225))
            y += 44 if not vertical else 50
        y += 18
    foot = "Film on SOUL S, aluminium (gate G2). If it is filmed on the M prototype, this label stays on screen: " + FACTS["labels"]["prototype_footage"]
    ff = font("m", 18 if not vertical else 22, "Regular")
    lines = wrap_px(foot, ff, W - 2 * m)
    fy = H - 300 if not vertical else int(H * 0.66)
    for ln in lines:
        d.text((m, fy), ln, font=ff, fill=(170, 170, 175))
        fy += 30
    return im

def odds_card(W, H):
    im = bg_glass(W, H)
    d = ImageDraw.Draw(im)
    designs = json.load(open(os.path.join(MS, "eyes/designs.json"), encoding="utf-8"))
    L = designs.get("designs") or [v for v in designs.values() if isinstance(v, list)][0]
    counts = {}
    for x in L:
        counts[x["rarity"].capitalize()] = counts.get(x["rarity"].capitalize(), 0) + 1
    odds = FACTS["product"]["eyes"]["rarity_odds_at_birth"]
    m = 140
    d.text((m, 130), "—  BORN, NOT MADE · THE REAL ODDS FROM THE BIRTH CODE", font=font("m", 22, "Medium"), fill=DIM)
    d.text((m, 175), f"{sum(counts.values())} pairs of eyes. one is yours.", font=font("b", 80, "ExtraBold"), fill=WARM)
    cols = [m, m + 420, m + 760, m + 1060]
    y = 300
    fh = font("m", 22, "Medium")
    for c, t in zip(cols, ["RARITY", "CHANCE AT BIRTH", "DESIGNS", "ONE EXACT PAIR"]):
        d.text((c, y), t, font=fh, fill=DIM)
    y += 50
    fr = font("b", 44, "SemiBold")
    tint = {"Common": (200, 200, 200), "Uncommon": (110, 210, 140), "Rare": (90, 140, 255), "Epic": (180, 120, 255), "Legendary": (240, 190, 70), "Mythic": (255, 90, 110)}
    for r, p in odds.items():
        n = counts.get(r, 0)
        d.line([m, y - 8, W - m, y - 8], fill=(45, 45, 50), width=1)
        d.ellipse([cols[0], y + 18, cols[0] + 16, y + 34], fill=tint.get(r, WARM))
        d.text((cols[0] + 34, y), r, font=fr, fill=WARM)
        d.text((cols[1], y), f"{p * 100:g} %", font=fr, fill=WARM)
        d.text((cols[2], y), str(n), font=fr, fill=WARM)
        d.text((cols[3], y), f"1 in {round(n / p):,}" if n else "–", font=fr, fill=WARM)
        y += 66
    d.text((m, y + 10), "Rarity changes only the eyes. Nobody can choose, buy, swap or re-roll them.", font=font("b", 30, "Regular"), fill=(200, 200, 205))
    return im

def privacy_card(W, H):
    im = bg_glass(W, H)
    d = ImageDraw.Draw(im)
    m = 140
    d.text((m, 140), "—  PROMISES, NOT SETTINGS", font=font("m", 22, "Medium"), fill=DIM)
    d.text((m, 185), "it only listens while you hold it.", font=font("b", 78, "ExtraBold"), fill=WARM)
    items = [
        ("no camera", "there is no camera in SOUL."),
        ("hold to talk", "the mic listens only while a finger is on the glass."),
        ("memory on the stone", "SOUL Memory lives on the device."),
        ("works offline", "eyes, notes, reminders, alarms, focus: no Wi-Fi needed."),
        ("your own AI", "your key, your account. We never include or resell AI."),
        ("no subscription to us", "you pay your AI provider directly, if you use one."),
    ]
    y = 360
    for i, (a, b) in enumerate(items):
        x = m + (i % 2) * 830
        yy = y + (i // 2) * 150
        d.ellipse([x, yy + 14, x + 18, yy + 32], fill=CREAM)
        d.text((x + 40, yy), a, font=font("b", 44, "Bold"), fill=WARM)
        for j, ln in enumerate(wrap_px(b, font("b", 28, "Regular"), 720)):
            d.text((x + 40, yy + 58 + j * 34), ln, font=font("b", 28, "Regular"), fill=(190, 190, 195))
    return im

def honesty_card(W, H, vertical=False):
    """Hero render + the honest status lines (CE, delivery)."""
    im = bg_glass(W, H)
    hero = Image.open(os.path.join(CF, "images/src/cuts/soul_front_silver.webp")).convert("RGBA")
    if not vertical:
        hh = int(H * 0.72)
        hero = hero.resize((int(hero.width * hh / hero.height), hh), Image.LANCZOS)
        im.paste(hero, (W - hero.width - 160, (H - hh) // 2 - 20), hero)
        x, y = 140, 250
        maxw = W - hero.width - 400
    else:
        hw = int(W * 0.7)
        hero = hero.resize((hw, int(hero.height * hw / hero.width)), Image.LANCZOS)
        im.paste(hero, ((W - hw) // 2, int(H * 0.16)), hero)
        x, y = 80, int(H * 0.16) + hero.height + 40
        maxw = W - 160
    d = ImageDraw.Draw(im)
    d.text((x, y), "—  BEFORE YOU BACK", font=font("m", 24, "Medium"), fill=DIM)
    y += 60
    dl = FACTS["scn"]["estimated_delivery"]
    if CE_OK:
        top, sub = "CE: tests passed.", "EU Declaration of Conformity signed."
    elif FACTS["campaign"]["scenario"] == "after_ce":
        top, sub = "not CE-certified yet.", "this campaign opens only after it passes."
    else:
        top, sub = "not CE-certified yet.", "ships only after it passes an accredited lab."
    lines = [
        (top, WARM),
        (sub, (200, 200, 205)),
        (f"estimated delivery: {month_name(dl['EU'])} (EU), {month_name(dl['UK'])} (UK).", (200, 200, 205)),
    ]
    for t, c in lines:
        f = font("b", 64 if c == WARM else 40, "ExtraBold" if c == WARM else "Regular")
        for ln in wrap_px(t, f, maxw):
            d.text((x, y), ln, font=f, fill=c)
            y += 74 if c == WARM else 52
        y += 10
    return im

def month_name(ym, ro=False):
    y, mth = ym.split("-")
    if ro:
        return ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"][int(mth) - 1] + " " + y
    return ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][int(mth) - 1] + " " + y

def end_eyes_box(W, H, vertical=False):
    D = int(H * 0.40) if not vertical else int(W * 0.62)
    return ((W - D) // 2, int(H * 0.08) if not vertical else int(H * 0.16), D)

def end_card(W, H, mode, vertical=False, eyes=False):
    im = bg_glass(W, H)
    d = ImageDraw.Draw(im)
    if eyes:
        x0, y0, D = end_eyes_box(W, H, vertical)
        d.ellipse([x0 - 14, y0 - 14, x0 + D + 14, y0 + D + 14], fill=(203, 205, 207))
        d.ellipse([x0 - 4, y0 - 4, x0 + D + 4, y0 + D + 4], fill=(0, 0, 0))
        y = y0 + D + (50 if not vertical else 80)
    else:
        logo = Image.open(LOGO).convert("RGBA")
        lw = int(W * (0.30 if not vertical else 0.62))
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        ly = int(H * (0.14 if not vertical else 0.2))
        im.paste(logo, ((W - lw) // 2, ly), logo)
        y = ly + logo.height + (60 if not vertical else 90)
    fl = FACTS["lad"]["launch"]
    if mode == "campaign":
        big = "back SOUL on Indiegogo"
        small = [f"the first {fl['cap']} are €{fl['price_eur']} · then €{FACTS['lad']['campaign']['price_eur']}",
                 FACTS["labels"]["ai_short"]]
    else:
        big = "coming to Indiegogo"
        small = ["get told first: link in the description", "from €{} in the campaign".format(fl["price_eur"]), FACTS["labels"]["ai_short"]]
    fb = font("b", 72 if not vertical else 84, "ExtraBold")
    for ln in wrap_px(big, fb, W - 160):
        d.text(((W - fb.getlength(ln)) // 2, y), ln, font=fb, fill=WARM)
        y += 92
    y += 20
    fs = font("b", 34 if not vertical else 40, "Regular")
    for s in small:
        for ln in wrap_px(s, fs, W - 200):
            d.text(((W - fs.getlength(ln)) // 2, y), ln, font=fs, fill=(200, 200, 205))
            y += 48
    ff = font("m", 18 if not vertical else 22, "Regular")
    # the campaign card never carries "not CE-certified yet" (the live campaign exists only after CE); the pre-launch teaser does
    foot = ("Not CE-certified yet. " if (mode != "campaign" and not CE_OK) else "") + "Renders (CGI) and screen animations are labelled. ARTEMIS DIGITAL S.R.L., Bucharest, Romania."
    fy = H - (90 if not vertical else int(H * 0.2))
    for ln in wrap_px(foot, ff, W - 200):
        d.text(((W - ff.getlength(ln)) // 2, fy), ln, font=ff, fill=(150, 150, 155))
        fy += 30
    return im

CHAT_PROMPT = "remind me at 5 to call mom"   # paid off on SOUL's glass right after (s-35-voice-answer: "Reminder 17:00")

def chatbox_frame(W, H, typed, cursor=True, vertical=False):
    """Illustration for the 'problem' beat: a generic chat input box (no brand, no logo)."""
    im = bg_glass(W, H)
    d = ImageDraw.Draw(im)
    bw = int(W * (0.62 if not vertical else 0.86))
    bh = 120 if not vertical else 140
    bx, by = (W - bw) // 2, int(H * (0.36 if not vertical else 0.40))
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=(30, 30, 34), outline=(70, 70, 76), width=2)
    f = font("b", 44 if not vertical else 50, "Regular")
    txt = typed if typed else "Ask anything"
    col = WARM if typed else (120, 120, 126)
    ty = by + (bh - (f.getmetrics()[0] + f.getmetrics()[1])) // 2
    d.text((bx + 56, ty), txt, font=f, fill=col)
    if cursor:
        cx = bx + 56 + (f.getlength(typed) + 6 if typed else 0)
        d.rectangle([cx, ty + 6, cx + 3, ty + 52], fill=WARM)
    r = bh // 2 - 18
    ax, ay = bx + bw - bh // 2, by + bh // 2
    d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(70, 70, 76))
    d.polygon([(ax, ay - 14), (ax - 12, ay + 2), (ax + 12, ay + 2)], fill=WARM)
    d.rectangle([ax - 3, ay, ax + 3, ay + 14], fill=WARM)
    return im

def soulos_frame(W, H, shot, vertical=False):
    im = bg_glass(W, H)
    sub = "alive-s" if shot.startswith("s-") else "alive"
    src = Image.open(os.path.join(MS, "firmware/sim/shots", sub, shot + ".png")).convert("RGB")
    D = int(min(W, H) * (0.62 if not vertical else 0.82))   # the caption band below the circle stays free (review 2026-10-22)
    src = src.resize((D, D), Image.LANCZOS)
    mask = Image.new("L", (D, D), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, D - 1, D - 1], fill=255)
    cx, cy = W // 2, (int(H * 0.42)) if not vertical else int(H * 0.43)
    d = ImageDraw.Draw(im)
    r = D // 2 + 22
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(203, 205, 207))
    r2 = D // 2 + 6
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(0, 0, 0))
    im.paste(src, (cx - D // 2, cy - D // 2), mask)
    return im

def fit_image(path, W, H, mode="contain"):
    src = Image.open(path).convert("RGB")
    if mode == "band":   # contain inside the area above the caption band
        sc = min(W / src.width, (H - 300) / src.height)
        src = src.resize((int(src.width * sc), int(src.height * sc)), Image.LANCZOS)
        im = Image.new("RGB", (W, H), GLASS)
        im.paste(src, ((W - src.width) // 2, 70))
        return im
    if mode == "cover":
        sc = max(W / src.width, H / src.height)
    else:
        sc = min(W / src.width, H / src.height)
    src = src.resize((int(src.width * sc), int(src.height * sc)), Image.LANCZOS)
    corner = src.getpixel((2, 2))
    im = Image.new("RGB", (W, H), corner)
    im.paste(src, ((W - src.width) // 2, (H - src.height) // 2))
    return im

# ------------------------------------------------------------------------------------------------ ffmpeg
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(" ".join(cmd) + "\n" + r.stderr[-3000:])
        raise SystemExit(1)

ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(FPS)]

def seg_video(seg, section, W, H, tmp, idx, vertical, shots_by_id):
    ov = os.path.join(tmp, f"ov_{idx:02d}.png")
    overlay(W, H, seg, section, vertical).save(ov)
    out = os.path.join(tmp, f"seg_{idx:02d}.mp4")
    dur = float(seg["dur"])
    kind = seg["kind"]
    if kind == "clip":
        src = os.path.join(MS, seg["src"])
        fit = seg.get("fit", "cover")
        pre = (seg["precrop"] + ",") if seg.get("precrop") else ""
        if fit == "cover":
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        else:  # square source shown whole, on glass, leaving room for the caption
            box = int(min(W, H) * (0.66 if not vertical else 0.9))
            yoff = "70" if not vertical else "(oh-ih)/2-120"
            vf = f"scale={box}:{box}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:{yoff}:color=0x0B0B0C"
        if fit == "cover" and seg.get("crop_x") is not None:
            vf = f"scale=-2:{H},crop={W}:{H}:{seg['crop_x']}*(iw-{W}):0"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(seg["ss"]), "-t", str(dur), "-i", src, "-i", ov,
             "-filter_complex", f"[0:v]{pre}{vf},fps={FPS},setsar=1[b];[b][1:v]overlay=0:0,format=yuv420p[v]",
             "-map", "[v]", "-an", *ENC, out])
        return out
    # still-based kinds
    frames = []
    if kind == "film":
        frames = [(film_card(W, H, shots_by_id[seg["shot"]], vertical), dur)]
    elif kind == "image":
        frames = [(fit_image(os.path.join(MS, seg["src"]), W, H, seg.get("fit", "contain")), dur)]
    elif kind == "odds":
        frames = [(odds_card(W, H), dur)]
    elif kind == "privacy":
        frames = [(privacy_card(W, H), dur)]
    elif kind == "honesty":
        frames = [(honesty_card(W, H, vertical), dur)]
    elif kind == "end" and seg.get("eyes"):
        # the ask ends on living eyes: the eyes-engine loop inside the card's circle
        bgp = os.path.join(tmp, f"end_{idx:02d}.png")
        end_card(W, H, seg.get("mode", "campaign"), vertical, eyes=True).save(bgp)
        x0, y0, D = end_eyes_box(W, H, vertical)
        mk = os.path.join(tmp, f"mask_{idx:02d}.png")
        m = Image.new("L", (D, D), 0); ImageDraw.Draw(m).ellipse([0, 0, D - 1, D - 1], fill=255); m.save(mk)
        src = os.path.join(MS, seg["eyes_src"])
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{dur:.3f}", "-i", bgp, "-ss", str(seg.get("ss", 0)), "-t", f"{dur:.3f}", "-i", src,
             "-loop", "1", "-t", f"{dur:.3f}", "-i", mk, "-i", ov,
             "-filter_complex", f"[1:v]crop=780:780:210:60,scale={D}:{D},fps={FPS},format=rgba[e];[2:v]scale={D}:{D},format=gray[m];[e][m]alphamerge[em];"
                                f"[0:v]fps={FPS},setsar=1[b];[b][em]overlay={x0}:{y0}:shortest=1[c];[c][3:v]overlay=0:0,format=yuv420p,trim=duration={dur:.3f}[v]",
             "-map", "[v]", "-an", *ENC, "-frames:v", str(int(round(dur * FPS))), out])
        return out
    elif kind == "end":
        frames = [(end_card(W, H, seg.get("mode", "campaign"), vertical), dur)]
    elif kind == "chatbox":
        n_typed = len(CHAT_PROMPT)
        steps = [("", True, 0.5), ("", False, 0.4)] if dur >= 3 else []
        stride = 2 if dur >= 3 else 4
        for k in range(stride, n_typed + stride, stride):
            steps.append((CHAT_PROMPT[:k], True, (2 if dur >= 3 else 1) / FPS))
        rest = max(0.3, dur - sum(x[2] for x in steps))
        steps += [(CHAT_PROMPT, False, rest / 2), (CHAT_PROMPT, True, rest / 2)]
        frames = [(chatbox_frame(W, H, t, c, vertical), d_) for t, c, d_ in steps]
        seg = dict(seg, zoom=0)
    elif kind == "soulos":
        per = dur / len(seg["shots"])
        frames = [(soulos_frame(W, H, s, vertical), per) for s in seg["shots"]]
    parts = []
    for j, (img, d) in enumerate(frames):
        p = os.path.join(tmp, f"st_{idx:02d}_{j:02d}.png")
        img.save(p)
        part = os.path.join(tmp, f"st_{idx:02d}_{j:02d}.mp4")
        z = seg.get("zoom", 0.03 if kind in ("image", "soulos", "honesty") else 0.0)
        n = int(round(d * FPS))
        if z:
            vf = (f"scale={W*2}:{H*2},zoompan=z='1+{z}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}")
        else:
            vf = f"fps={FPS}"
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{d:.3f}", "-i", p, "-i", ov,
             "-filter_complex", f"[0:v]{vf},setsar=1,trim=duration={d:.3f}[b];[b][1:v]overlay=0:0,format=yuv420p[v]",
             "-map", "[v]", "-an", *ENC, "-frames:v", str(n), part])
        parts.append(part)
    if len(parts) == 1:
        shutil.move(parts[0], out)
    else:
        lst = os.path.join(tmp, f"lst_{idx:02d}.txt")
        open(lst, "w").write("".join(f"file '{q}'\n" for q in parts))
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    return out

SCRATCH_GUESS = [os.environ.get("SOUL_PIPER_MODEL", ""),
                 "/tmp/claude-0/-home-user-obsidian-vault/ed786c2e-2b4e-5bb0-b0e8-a62c849e07d8/scratchpad/voices/en_US-lessac-high.onnx"]
MUSIC_URL = "https://assets.mixkit.co/music/464/464.mp3"   # "Sci-Fi Score" by Arulo, Mixkit Free License (trailer/MUSIC-LICENSE.md)


def piper_model():
    for p in SCRATCH_GUESS:
        if p and os.path.exists(p):
            return p
    return None


def music_file(tmp):
    import glob, urllib.request
    p = os.environ.get("SOUL_MUSIC_464", "")
    if p and os.path.exists(p):
        return p
    for g in glob.glob("/tmp/claude-0/*/*/scratchpad/music/m464.mp3") + glob.glob("/tmp/claude-0/*/*/scratchpad/audio*/music_464.mp3"):
        return g
    try:
        out = os.path.join(tmp, "m464.mp3")
        req = urllib.request.Request(MUSIC_URL, headers={"User-Agent": "Mozilla/5.0"})
        open(out, "wb").write(urllib.request.urlopen(req, timeout=30).read())
        return out
    except Exception:
        return None


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip() or 0)


def guide_audio(timeline, total, tmp, music_from=None, music_ss=58.71, tts=True):
    """A GUIDE track for pacing only: TTS voice-over (Piper, offline) per segment + the licensed track under the ask.
    Not for publishing: the final film uses a human voice (script.md §2)."""
    model = piper_model() if tts else None
    inputs, filters = [], []
    if model:
        for k, s in enumerate(timeline):
            if not s["vo"] or s.get("no_tts"):
                continue
            wav = os.path.join(tmp, f"vo_{k:02d}.wav")
            r = subprocess.run([sys.executable, "-m", "piper", "-m", model, "-f", wav], input=s["vo"], text=True, capture_output=True)
            if r.returncode or not os.path.exists(wav):
                continue
            room = (s["end"] - s["start"]) - 0.35
            d = dur_of(wav)
            tempo = min(1.3, max(1.0, d / room)) if room > 0 else 1.0
            idx = len([x for x in inputs if x == "-i"])
            inputs += ["-i", wav]
            filters.append(f"[{idx}:a]atempo={tempo:.3f},adelay={int((s['start'] + 0.2) * 1000)}|{int((s['start'] + 0.2) * 1000)},aformat=channel_layouts=stereo[v{idx}]")
    mf = music_file(tmp) if music_from is not None else None
    if mf:
        idx = len([x for x in inputs if x == "-i"])
        inputs += ["-ss", f"{music_ss}", "-i", mf]
        mlen = total - music_from
        filters.append(f"[{idx}:a]atrim=0:{mlen:.2f},afade=t=in:d=0.6,afade=t=out:st={max(0, mlen - 1.5):.2f}:d=1.5,volume={0.32 if tts else 0.6},adelay={int(music_from * 1000)}|{int(music_from * 1000)},aformat=channel_layouts=stereo[m{idx}]")
    if not filters:
        return None
    labels = "".join(f"[{f.rsplit('[', 1)[1]}" for f in filters)
    out = os.path.join(tmp, "guide.wav")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
         ";".join(filters) + f";{labels}amix=inputs={len(filters)}:normalize=0,apad,atrim=0:{total:.2f}[a]", "-map", "[a]", "-ar", "48000", out])
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    mi, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"

def build(which):
    cfg = SEG[which]
    W, H = cfg["size"]
    vertical = H > W
    shots_by_id = {s["id"]: s for s in SEG["film_shots"]}
    tmp = tempfile.mkdtemp(prefix=f"soulvid_{which}_")
    outs, t, timeline = [], 0.0, []
    idx = 0
    for section in cfg["sections"]:
        for seg in section["segs"]:
            outs.append(seg_video(seg, section, W, H, tmp, idx, vertical, shots_by_id))
            timeline.append({"start": round(t, 2), "end": round(t + seg["dur"], 2), "section": f"{section['num']} {section['name']}", "no_tts": seg.get("no_tts", False), "music": seg.get("music", False),
                             "id": seg["id"], "kind": seg["kind"], "label": seg.get("label"), "vo": fill_vars(seg.get("vo", "")),
                             "vo_ro": fill_vars(seg.get("vo_ro", "")), "src": seg.get("src") or seg.get("shot") or seg.get("shots")})
            t += seg["dur"]
            idx += 1
    lst = os.path.join(tmp, "all.txt")
    open(lst, "w").write("".join(f"file '{q}'\n" for q in outs))
    joined = os.path.join(tmp, "joined.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    final = os.path.join(VID, cfg["out"])
    # final pass: size cap (< 40 MB) + the guide audio (TTS voice + licensed music under the ask), or silence
    mus = next((x["start"] for x in timeline if x.get("music")), None)
    ga = guide_audio(timeline, t, tmp, mus, cfg.get("music_ss", 58.71), cfg.get("tts", True)) if cfg.get("audio", True) else None
    ain = ["-i", ga] if ga else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    run(["ffmpeg", "-v", "error", "-y", "-i", joined, *ain,
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
         "-maxrate", cfg.get("maxrate", "1600k"), "-bufsize", "3200k", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "96k" if ga else "32k", "-shortest", "-movflags", "+faststart",
         "-metadata", f"title=SOUL {which} (rough, {BUILD_DATE}) - not for publishing", final])
    json.dump({"file": cfg["out"], "duration_s": round(t, 2), "segments": timeline},
              open(os.path.join(HERE, f"timeline_{which}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if which == "rough":
        for lang, key in (("en", "vo"), ("ro", "vo_ro")):
            n, out = 0, []
            for s in timeline:
                if s[key]:
                    n += 1
                    out.append(f"{n}\n{srt_time(s['start'] + 0.15)} --> {srt_time(s['end'] - 0.15)}\n" +
                               "\n".join(textwrap.wrap(s[key], 42)) + "\n")
            open(os.path.join(VID, "subtitles", f"soul-campaign-roughcut.{lang}.srt"), "w", encoding="utf-8").write("\n".join(out))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{final}  {t:.2f} s  {os.path.getsize(final) / 1e6:.1f} MB")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["rough", "teaser"])
    a = ap.parse_args()
    for w in (["rough", "teaser"] if not a.only else [a.only]):
        build(w)
