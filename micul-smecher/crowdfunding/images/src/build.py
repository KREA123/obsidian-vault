#!/usr/bin/env python3
"""SOUL on Indiegogo: build every campaign image from HTML/CSS with Playwright + Chromium.

    python3 -I micul-smecher/crowdfunding/images/src/build.py            # everything (active ladder/scenario in facts.json)
    python3 -I micul-smecher/crowdfunding/images/src/build.py --video    # also the clips the video build uses
    python3 -I micul-smecher/crowdfunding/images/src/build.py --only card_700,perk_   # ids starting with these
    python3 -I micul-smecher/crowdfunding/images/src/build.py --no-anim  # skip the GIF/MP4 animations

Every number and size-dependent fact comes from ../../facts.json (and the goal model in ../../tools/goal_model.py).
Change facts.json, run tools/goal_model.py, then this (or tools/build_all.sh). Nothing is hard-coded here except layout.
Re-grade the cut-outs with regrade.py (cuts/) when trailer/assets change.

Sizes follow Indiegogo's help centre (HC/503, HC/483, HC/485, read 2026-10-20):
  thumbnail 700x700 · cover >= 1743x498, no text · social 1200x630 · gallery 1200x630 · rewards/add-ons 700x700 ·
  update and launch images 700x700 · avatar 700x700 · story images 840-1200 px wide, <= 12000 px tall, <= 20 MB
  (converted to .webp on upload) · story animations MP4/WebM <= 20 MB, >= 840 px wide.
"""
import argparse, asyncio, base64, importlib.util, io, json, math, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                                  # crowdfunding/images
CF = os.path.dirname(OUT)                                    # crowdfunding
MS = os.path.dirname(CF)                                     # micul-smecher
CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
FONT_CACHE = os.path.join(tempfile.gettempdir(), "soulos-fontcache")   # shared with os/tests/alive-shots.mjs

from PIL import Image

# ------------------------------------------------------------------------------------------------ data
sys.path.insert(0, os.path.join(CF, "tools"))
from facts import load as load_facts  # noqa: E402


def build_data():
    """facts.json + docs/size-s.json + goal_model.out.json (run tools/goal_model.py first) + the re-graded cut-outs."""
    F = load_facts()
    if "model" not in F:
        raise SystemExit("run tools/goal_model.py first")
    cuts = {}
    for d, prefix in ((os.path.join(HERE, "cuts"), "cuts/"), (os.path.join(MS, "trailer", "assets"), "../../../trailer/assets/")):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json") and f.startswith("soul_") and f[:-5] not in cuts:
                j = json.load(open(os.path.join(d, f)))
                g = list(j["souls"].values())[0]
                cuts[f[:-5]] = {"w": j["w"], "h": j["h"], "src": j["src"], "dir": prefix, "c": g["c"], "ux": g["ux"], "uy": g["uy"]}
    outline = json.load(open(os.path.join(HERE, "marg_s_outline.json"), encoding="utf-8"))
    return {"facts": F, "cuts": cuts, "outline": outline, "asset": "../../../"}


# ------------------------------------------------------------------------------------------------ specs
# id, file, w, h, format, group. Story images are 1200 wide (Indiegogo's maximum); their height is set by the page.
SPECS = [
    ("card_700", "01_card_thumbnail_700x700.jpg", 700, 700, "jpg", "platform"),
    ("cover", "02_cover_1743x498.jpg", 1743, 498, "jpg", "platform"),
    ("social", "03_social_share_1200x630.jpg", 1200, 630, "jpg", "platform"),
    ("avatar", "04_avatar_700x700.png", 700, 700, "png", "platform"),
    ("launch", "05_launch_email_700x700.jpg", 700, 700, "jpg", "platform"),
    ("update", "06_update_header_700x700.jpg", 700, 700, "jpg", "platform"),
    ("g1_approve", "gallery_1_approve_1200x630.png", 1200, 630, "png", "gallery"),
    ("g2_size", "gallery_2_size_1200x630.png", 1200, 630, "png", "gallery"),
    ("g3_hero", "gallery_3_hero_1200x630.jpg", 1200, 630, "jpg", "gallery"),
    ("g4_eyes", "gallery_4_eyes_1200x630.png", 1200, 630, "png", "gallery"),
    ("g5_colours", "gallery_5_colours_1200x630.jpg", 1200, 630, "jpg", "gallery"),
    ("g6_hand", "gallery_6_in_hand_1200x630.jpg", 1200, 630, "jpg", "gallery"),
    ("s01_object", "story_01_object.jpg", 1200, 0, "jpg", "story"),
    ("s02_eyes", "story_02_eyes.png", 1200, 0, "png", "story"),
    ("s03_ai", "story_03_your_ai.png", 1200, 0, "png", "story"),
    ("s03b_approve", "story_03b_approve.png", 1200, 0, "png", "story"),
    ("s04_soulos", "story_04_soulos.png", 1200, 0, "png", "story"),
    ("s05_colours", "story_05_colours.jpg", 1200, 0, "jpg", "story"),
    ("s06_size", "story_06_size.png", 1200, 0, "png", "story"),
    ("s06b_hand", "story_06b_in_hand.jpg", 1200, 0, "jpg", "story"),
    ("s06c_desk", "story_06c_on_desk.jpg", 1200, 0, "jpg", "story"),
    ("s07_ou_night", "story_07_ou_night.jpg", 1200, 0, "jpg", "story"),
    ("s08_box", "story_08_box.jpg", 1200, 0, "jpg", "story"),
    ("s09_privacy", "story_09_privacy.png", 1200, 0, "png", "story"),
    ("s10_budget", "story_10_budget.png", 1200, 0, "png", "story"),
    ("s11_timeline", "story_11_timeline.png", 1200, 0, "png", "story"),
    ("s12_stretch", "story_12_stretch.png", 1200, 0, "png", "story"),
    ("s13_team", "story_13_team_PLACEHOLDER.png", 1200, 0, "png", "story"),
    ("perk_supporter", "reward_1_soul_supporter_700x700.png", 700, 700, "png", "reward"),
    ("perk_first_light", "reward_2_first_light_700x700.jpg", 700, 700, "jpg", "reward"),
    ("perk_campaign", "reward_3_campaign_price_700x700.jpg", 700, 700, "jpg", "reward"),
    ("perk_campaign_b2", "reward_3b_campaign_batch2_700x700.jpg", 700, 700, "jpg", "reward"),
    ("perk_two_souls", "reward_4_two_souls_700x700.jpg", 700, 700, "jpg", "reward"),
    ("perk_ou", "reward_5_addon_extra_ou_700x700.jpg", 700, 700, "jpg", "reward"),
    ("perk_late", "reward_6_late_pledge_700x700.jpg", 700, 700, "jpg", "reward"),
    ("stretch_1", "stretch_1_languages_700x700.png", 700, 700, "png", "stretch"),
    ("stretch_2", "stretch_2_felt_pouch_700x700.png", 700, 700, "png", "stretch"),
    ("stretch_3", "stretch_3_birth_card_700x700.png", 700, 700, "png", "stretch"),
]
ANIMS = [  # id, base name, w, h, seconds, gif fps, mp4 fps, gif width (email only)
    ("anim_eyes", "anim_1_eyes_alive", 1200, 900, 6.4, 15, 30, 600),
    ("anim_colours", "anim_3_colour_swap", 1200, 900, 5.4, 15, 30, 600),
]
VIDEO_CLIPS = [  # stills/animations for the video (video/build/assets), 1920 x 1080
    ("vid_hook", "hook_object_wake", 1280, 720, 4.0),
]
VIDEO_STILLS = [("vid_colours", "colours_launch.png", 1920, 1080)]
LIMIT = {"story": 20e6, "default": 20e6}        # Indiegogo: 20 MB per story image/animation; we aim far lower
TARGET_JPG_MAX = 1.5e6


def page_url(i):
    return "file://" + os.path.join(HERE, "page.html") + "?id=" + i


async def font_route(route):
    url = route.request.url
    os.makedirs(FONT_CACHE, exist_ok=True)
    f = os.path.join(FONT_CACHE, base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")[-120:])
    if not os.path.exists(f):
        subprocess.run(["curl", "-sS", "--retry", "5", "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "-o", f, url], check=False)
    if not os.path.exists(f):
        return await route.fulfill(status=200, body="", headers={"content-type": "text/css"})
    await route.fulfill(status=200, body=open(f, "rb").read(), headers={"content-type": "text/css" if "googleapis" in url else "font/woff2", "access-control-allow-origin": "*"})


def save_still(png_bytes, path, w, h, fmt):
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if h == 0:
        h = round(im.size[1] * w / im.size[0])
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    if fmt == "jpg":
        q = 90
        while True:
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if q >= 88 else 2)
            if buf.tell() <= TARGET_JPG_MAX or q <= 72:
                break
            q -= 4
        open(path, "wb").write(buf.getvalue())
    else:
        im = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG) if os.environ.get("SOUL_PNG8") else im
        im.save(path, "PNG", optimize=True)
    return w, h


async def render_stills(browser, ids, results):
    ctx = await browser.new_context(viewport={"width": 1200, "height": 900}, device_scale_factor=2)
    page = await ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    for sid, fn, w, h, fmt, grp in SPECS:
        if ids and not any(sid.startswith(x) for x in ids):
            continue
        await page.set_viewport_size({"width": w, "height": h or 900})
        await page.goto(page_url(sid))
        await page.wait_for_function("window.READY === true", timeout=60000)
        root = page.locator("#root")
        png = await root.screenshot(type="png")
        path = os.path.join(OUT, fn)
        W, H = save_still(png, path, w, h, fmt)
        sz = os.path.getsize(path)
        assert H <= 12000 and sz <= LIMIT["default"], (fn, H, sz)
        results.append((fn, W, H, sz, grp))
        print(f"  {fn:46s} {W}x{H}  {sz/1e3:7.0f} kB", flush=True)
    if errs:
        print("PAGE ERRORS:", *errs[:20], sep="\n  ")
    await ctx.close()


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def encode(frames_dir, fps_in, base, w, h, gif_fps, mp4_fps, gif_w=None, results=None, label="", outdir=None, gif=True):
    outdir = outdir or OUT
    gifp = os.path.join(outdir, base + ".gif")
    mp4 = os.path.join(outdir, base + ".mp4")
    gw = gif_w or w
    pat = os.path.join(frames_dir, "f%05d.png")
    if gif:
        ffmpeg("-framerate", str(fps_in), "-i", pat, "-vf",
               f"fps={gif_fps},scale={gw}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160:stats_mode=full[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
               "-loop", "0", gifp)
    mw = max(w, 840) // 2 * 2
    ffmpeg("-framerate", str(fps_in), "-i", pat, "-vf", f"fps={mp4_fps},scale={mw}:-2:flags=lanczos,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-movflags", "+faststart", "-an", mp4)
    for p in ((gifp, mp4) if gif else (mp4,)):
        im = Image.open(p) if p.endswith(".gif") else None
        if im:
            W, H = im.size
        else:
            pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip().split(",")
            W, H = int(pr[0]), int(pr[1])
        sz = os.path.getsize(p)
        assert sz <= 20e6, (p, sz)
        if results is not None:
            results.append((os.path.basename(p), W, H, sz, "anim"))
        print(f"  {os.path.basename(p):46s} {W}x{H}  {sz/1e3:7.0f} kB", flush=True)


async def render_anims(browser, ids, results, specs=None, outdir=None, gif=True):
    for spec in (specs or ANIMS):
        aid, base, w, h, secs = spec[:5]
        gfps, mfps, gw = (spec[5], spec[6], spec[7]) if len(spec) > 5 else (15, 30, w)
        if ids and not any(aid.startswith(x) for x in ids):
            continue
        fps = 30
        n = int(round(secs * fps))
        ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        page = await ctx.new_page()
        await page.goto(page_url(aid) + f"&fps={fps}")
        await page.wait_for_function("window.READY === true", timeout=60000)
        d = tempfile.mkdtemp(prefix="soulanim_")
        for i in range(n):
            await page.evaluate(f"window.ANIM.frame({i})")
            await page.screenshot(path=os.path.join(d, f"f{i:05d}.png"), clip={"x": 0, "y": 0, "width": w, "height": h})
        await ctx.close()
        encode(d, fps, base, w, h, gfps, mfps, gif_w=gw, results=results, outdir=outdir, gif=gif)
        shutil.rmtree(d)


async def capture_dial(browser, results):
    """The home dial of the SoulOS web prototype (os/index.html), turning: a CDP screencast of the glass, resampled to
    30 fps, masked to the round screen and set on a captioned background (the page from page.html?id=anim_dial_bg)."""
    G = 780                                                          # glass size in the final frame (px)
    scale = G / 363                                                  # the page draws the glass 363 CSS px wide
    ctx = await browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=scale)
    await ctx.add_init_script("try{localStorage.setItem('soulos-born','1');localStorage.setItem('soulos-chip','C0FFEE123456');localStorage.setItem('soulos-body','silver')}catch(e){}")
    page = await ctx.new_page()
    await page.route("**/fonts.googleapis.com/**", font_route)
    await page.route("**/fonts.gstatic.com/**", font_route)
    await page.goto("file://" + os.path.join(MS, "os", "index.html"), wait_until="load")
    await page.wait_for_timeout(2400)
    ev = page.evaluate
    await ev("() => { __soul.cancel('msg'); __soul.cancel('claude'); __soul.cancel('demo'); __soul.S.ai = 'claude'; __soul.S.night = false; __soul.S.coach = false; document.getElementById('pebble').scrollIntoView({block:'center'}); }")
    await ev("() => { __soul.S.pill = null; document.getElementById('pill').classList.remove('show'); __soul.ALIVE.hide(); __soul.go('home','fade'); document.getElementById('screen').classList.remove('peek'); __soul.cancel('peek'); }")
    await page.wait_for_timeout(900)
    await ev("() => { __soul.ALIVE.hide(); __soul.go('apps','none'); }")
    await page.wait_for_timeout(1400)
    await ev("() => __soul.lnSpinTo('talk')")
    await page.wait_for_timeout(1500)
    box = await page.locator("#glass").bounding_box()
    cdp = await ctx.new_cdp_session(page)
    frames = []

    def on_frame(p):
        frames.append((p["metadata"]["timestamp"], p["data"]))
        asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": p["sessionId"]}))
    cdp.on("Page.screencastFrame", on_frame)
    vw = await ev("() => [innerWidth, innerHeight]")
    await cdp.send("Page.startScreencast", {"format": "png", "everyNthFrame": 1, "maxWidth": int(vw[0] * scale) + 2, "maxHeight": int(vw[1] * scale) + 2})
    t0 = time.time()
    await page.wait_for_timeout(700)
    # turn the ring: three pebbles forward, a pause, three back (the loop closes on the same pebble)
    for step in (1, 1, 1, 0, -1, -1, -1):
        if step:
            await ev(f"() => {{ __soul.LN.tgt = Math.round(__soul.LN.rot) + ({step}); }}")
        await page.wait_for_timeout(900 if step else 1200)
    await page.wait_for_timeout(500)
    await cdp.send("Page.stopScreencast")
    await page.wait_for_timeout(300)
    await ctx.close()
    if len(frames) < 10:
        raise RuntimeError("screencast produced %d frames" % len(frames))
    frames.sort()
    ts0, ts1 = frames[0][0], frames[-1][0]
    fps = 30
    n = int((ts1 - ts0) * fps)
    d = tempfile.mkdtemp(prefix="souldial_")
    # background with captions and the empty glass slot
    bgp = os.path.join(d, "bg.png")
    c2 = await browser.new_context(viewport={"width": 1200, "height": 900}, device_scale_factor=1)
    p2 = await c2.new_page()
    await p2.goto(page_url("anim_dial_bg"))
    await p2.wait_for_function("window.READY === true")
    slot = await p2.evaluate("window.SLOT")
    await p2.locator("#root").screenshot(path=bgp)
    await c2.close()
    bg = Image.open(bgp).convert("RGB")
    mask = Image.new("L", (G * 4, G * 4), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).ellipse((0, 0, G * 4 - 1, G * 4 - 1), fill=255)
    gsz = slot["d"]
    mask = mask.resize((gsz, gsz), Image.LANCZOS)
    j = 0
    cache = {}
    for i in range(n):
        t = ts0 + i / fps
        while j + 1 < len(frames) and frames[j + 1][0] <= t:
            j += 1
        if j not in cache:
            cache.clear()
            im = Image.open(io.BytesIO(base64.b64decode(frames[j][1]))).convert("RGB")
            fx = im.size[0] / vw[0]
            crop = im.crop((round(box["x"] * fx), round(box["y"] * fx), round((box["x"] + box["width"]) * fx), round((box["y"] + box["height"]) * fx)))
            cache[j] = crop.resize((gsz, gsz), Image.LANCZOS)
        fr = bg.copy()
        fr.paste(cache[j], (slot["x"], slot["y"]), mask)
        fr.save(os.path.join(d, f"f{i:05d}.png"))
    encode(d, fps, "anim_2_dial_turning", 1200, 900, 15, 30, gif_w=600, results=results)
    shutil.rmtree(d)


def contact_sheet(results):
    from PIL import ImageDraw, ImageFont
    fdir = os.path.join(MS, "brand", "SOUL-Brand-Package", "Fonts")
    try:
        fb = ImageFont.truetype(os.path.join(fdir, "Bricolage-Grotesque", "BricolageGrotesque[opsz,wdth,wght].ttf"), 44)
        fm = ImageFont.truetype(os.path.join(fdir, "Martian-Mono", "MartianMono[wdth,wght].ttf"), 15)
    except Exception:
        fb = fm = ImageFont.load_default()
    order = {"platform": 0, "gallery": 1, "story": 2, "reward": 3, "stretch": 4, "anim": 5}
    seen, items = set(), []
    for fn, W, H, sz, grp in sorted(results, key=lambda r: (order.get(r[4], 9), r[0])):
        if fn.endswith(".mp4"):
            continue
        items.append((fn, W, H, sz, grp))
    TW, PAD, COLS = 340, 28, 6
    tiles = []
    for fn, W, H, sz, grp in items:
        p = os.path.join(OUT, fn)
        im = Image.open(p)
        if fn.endswith(".gif"):
            im.seek(min(im.n_frames - 1, im.n_frames // 3))
        im = im.convert("RGB")
        th = min(round(TW * im.size[1] / im.size[0]), 600)
        im = im.resize((TW, round(TW * im.size[1] / im.size[0])), Image.LANCZOS).crop((0, 0, TW, th))
        mp4 = os.path.join(OUT, fn[:-4] + ".mp4")
        extra = f" + .mp4 {os.path.getsize(mp4)/1e6:.1f} MB" if fn.endswith(".gif") and os.path.exists(mp4) else ""
        tiles.append((im, fn, f"{W}×{H} · {sz/1e6:.2f} MB{extra}"))
    rows, row = [], []
    for t in tiles:
        row.append(t)
        if len(row) == COLS:
            rows.append(row); row = []
    if row:
        rows.append(row)
    heights = [max(t[0].size[1] for t in r) + 64 for r in rows]
    SW = PAD + COLS * (TW + PAD)
    SH = 150 + sum(h + PAD for h in heights)
    sheet = Image.new("RGB", (SW, SH), (13, 13, 15))
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD, 40), "SOUL · Indiegogo images (generated " + time.strftime("%Y-%m-%d") + ")", font=fb, fill=(246, 243, 236))
    dr.text((PAD, 100), "micul-smecher/crowdfunding/images · build: python3 -I micul-smecher/crowdfunding/images/src/build.py · sizes per Indiegogo HC/503, HC/483", font=fm, fill=(164, 167, 174))
    y = 150
    for r, hh in zip(rows, heights):
        x = PAD
        for im, fn, meta in r:
            sheet.paste(im, (x, y))
            dr.rectangle((x - 1, y - 1, x + im.size[0], y + im.size[1]), outline=(60, 60, 66))
            dr.text((x, y + im.size[1] + 10), fn[:44], font=fm, fill=(246, 243, 236))
            dr.text((x, y + im.size[1] + 32), meta, font=fm, fill=(140, 143, 150))
            x += TW + PAD
        y += hh + PAD
    sheet.save(os.path.join(OUT, "_sheet.png"), optimize=True)
    print("  _sheet.png", sheet.size)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", action="store_true", help="also render the video clips into ../../video/build/assets")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-anim", action="store_true")
    a = ap.parse_args()
    ids = [x for x in a.only.split(",") if x]
    data = build_data()
    open(os.path.join(HERE, "data.js"), "w", encoding="utf-8").write("/* generated by build.py from facts.json + tools/goal_model.py; do not edit */\nwindow.DATA=" + json.dumps(data, ensure_ascii=False) + ";\n")
    from playwright.async_api import async_playwright
    results = []
    man = os.path.join(OUT, "_manifest.json")
    old = json.load(open(man)) if os.path.exists(man) else []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, args=["--allow-file-access-from-files", "--font-render-hinting=none", "--force-color-profile=srgb"])
        await render_stills(browser, ids, results)
        if a.video:
            vdir = os.path.join(CF, "video", "build", "assets")
            os.makedirs(vdir, exist_ok=True)
            await render_anims(browser, [], [], specs=VIDEO_CLIPS, outdir=vdir, gif=False)
            ctx = await browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
            pg = await ctx.new_page()
            for sid, fn, w, h in VIDEO_STILLS:
                await pg.goto(page_url(sid)); await pg.wait_for_function("window.READY === true", timeout=60000)
                await pg.locator("#root").screenshot(path=os.path.join(vdir, fn))
            await ctx.close()
        if not a.no_anim:
            await render_anims(browser, ids, results)
            if not ids or any("anim_dial".startswith(x) or x.startswith("anim_dial") for x in ids):
                await capture_dial(browser, results)
        await browser.close()
    done = {r[0] for r in results}
    keep = {x[1] for x in SPECS} | {b + e for _, b, *_ in ANIMS for e in (".gif", ".mp4")} | {"anim_2_dial_turning.gif", "anim_2_dial_turning.mp4"}
    allr = [tuple(r) for r in old if r[0] not in done and r[0] in keep and os.path.exists(os.path.join(OUT, r[0]))] + results
    json.dump(allr, open(man, "w"), indent=0)
    contact_sheet(allr)


if __name__ == "__main__":
    asyncio.run(main())
