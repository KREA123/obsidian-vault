/* SoulOS Alive · round-screen audit (os/DESIGN-ALIVE.md §9). Every content screen, measured at device scale (480 px):
     - cut:    no visible text glyph or control corner outside r = 228 (rounded corners are measured at their 45° point)
     - rim:    no rim label (curved text on the rim) overlaps the screen's text or controls
     - type:   no visible text below 18 device px
     - target: every control ([data-act], keyboard key, dial pebble) is at least 44 device px on its short side
     - eyes:   the eyes (the drawn pixels of the eye canvas) do not touch a rim title capsule or a control
   node os/tests/alive-audit.mjs [shotsDir]   (with a shotsDir it also writes one still per state + audit-sheet.png)
   Needs a global `playwright` with Chromium, like soulos.test.mjs. */
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import path from "path";
import os from "os";
import fs from "fs";
const root = execSync("npm root -g").toString().trim();
const { chromium } = await import(root + "/playwright/index.mjs");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const FILE = "file://" + path.resolve(HERE, "../index.html");
const SHOTS = process.argv[2] ? path.resolve(process.argv[2]) + "/" : null;
if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); for (const f of fs.readdirSync(SHOTS)) if (/^\d\d-.*\.png$/.test(f)) fs.unlinkSync(SHOTS + f); }
const FONTS = path.join(os.tmpdir(), "soulos-fontcache"); fs.mkdirSync(FONTS, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const ok = (c, m) => { results.push((c ? "PASS " : "FAIL ") + m); if (!c) console.log("FAIL", m); };
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 480 / 363 });
await ctx.addInitScript(() => { try { localStorage.setItem("soulos-born", "1"); localStorage.setItem("soulos-chip", "C0FFEE123456"); localStorage.setItem("soulos-body", "silver"); } catch (e) {} });
await ctx.grantPermissions(["geolocation"]); await ctx.setGeolocation({ latitude: 44.4355, longitude: 26.1025 });
const page = await ctx.newPage();
await page.route(/fonts\.(googleapis|gstatic)\.com/, async route => {
  const url = route.request().url(), f = path.join(FONTS, Buffer.from(url).toString("base64url").slice(-120));
  try { if (!fs.existsSync(f)) execSync(`curl -sS --retry 5 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36" -o "${f}" "${url}"`); } catch (e) {}
  if (!fs.existsSync(f)) return route.fulfill({ status: 200, body: "", headers: { "content-type": "text/css" } });
  await route.fulfill({ status: 200, body: fs.readFileSync(f), headers: { "content-type": /googleapis/.test(url) ? "text/css" : "font/woff2", "access-control-allow-origin": "*" } });
});
const errs = []; page.on("pageerror", e => errs.push(e.message)); page.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
await page.goto(FILE, { waitUntil: "load" }); await sleep(2400);
const ev = (f, a) => page.evaluate(f, a);
await ev(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.cancel("demo"); __soul.S.ai = "claude"; __soul.S.night = false; __soul.S.coach = false; document.getElementById("pebble").scrollIntoView({ block: "center" }); });

/* every state: [name, setup (runs in the page)] */
const plain = v => [v, `__soul.go(${JSON.stringify(v)}, "none")`];
const STATES = [
  ["home-peek", `__soul.go("home", "none"); __soul.peek()`],
  plain("apps"), plain("today"), plain("talk"), plain("weather"), plain("reminders"), plain("alarms"), plain("notes"), plain("focus"),
  plain("timer"), ["timer-countdown", `__soul.go("timer", "none"); __soul.S.tm.mode = "cd"; __soul.go("home", "none"); __soul.go("timer", "none")`],
  plain("claude"), ["claude-ask", `__soul.S.claude.pending = { cmd: "npm run build" }; __soul.go("claude", "none")`],
  plain("diary"), plain("translate"), plain("music"), plain("soul"), plain("games"), plain("settings"), plain("memory"), plain("about"), plain("aimode"),
  plain("mysoul"), plain("look"), plain("maps"), ["maps-here", `SoulApps.SA.m = null; __soul.go("maps", "none"); __soul.act("m-share", document.createElement("i"))`],
  plain("calendar"), plain("breathe"), plain("habits"), plain("worldclock"), plain("convert"), plain("findphone"), plain("device"), plain("appsset"),
  ["voice-listen", `__soul.S.voice = { phase: "listen", kind: "ask", shown: "Wake me at 6:45 tomorrow", sim: false, p: { q: "Wake me at 6:45 tomorrow" } }; __soul.go("voice", "none")`],
  ["voice-think", `__soul.S.voice = { phase: "think", kind: "ask", p: { q: "Remind me at 5 to call the bank" }, src: "Claude" }; __soul.go("voice", "none")`],
  ["voice-answer", `__soul.S.voice = { phase: "answer", kind: "ask", src: "SOUL · demo", p: { q: "Remind me at 5 to call the bank", a: "Done. I'll ping you at 5:00 PM.", chips: [["ok", "✓ Reminder set"]] } }; __soul.go("voice", "none")`],
  ["msg", `__soul.go("msg", "none")`],
  ["alarm-ring", `__soul.ringAlarm(__soul.S.alarms[0])`],
  ["alarm-set", `__soul.go("alarms", "none"); __soul.act("al-add", document.createElement("i"))`],
  ["keyboard", `__soul.go("notes", "none"); __soul.act("note-add", document.createElement("i"))`],
  ["control", `__soul.go("home", "none"); __soul.ccOpen()`],
  ["game-star", `__soul.go("games", "none"); __soul.gameStart()`],
];
const shotsOut = [];
let n = 0;
for (const [name, setup] of STATES) {
  await ev(() => { const s = __soul; if (s.S.kb) s.kbRender && document.getElementById("kb").classList.contains("on") && s.act && 0; s.S.pill = null; document.getElementById("pill").classList.remove("show"); s.ALIVE.hide(); if (s.S.cc) s.ccClose(true); if (s.S.ringing) { s.S.ringing = null; } s.S.voice = null; s.S.claude.pending = null; if (s.S.game.run) s.S.game.run = false; });
  await ev(() => { if (__soul.S.kb) { __soul.S.kb.text = ""; } }); await page.keyboard.press("Escape").catch(() => {});
  await ev(() => { __soul.go("home", "none"); }); await sleep(250);
  try { await ev(setup); } catch (e) { ok(false, `${name}: setup failed ${e.message}`); continue; }
  await sleep(1300);
  await ev(() => document.querySelectorAll(".dots, #dots").forEach(d => d.classList.add("hide")));   /* the 1.5 s "where am I" hint is checked separately below */
  if (SHOTS) { n++; const f = SHOTS + String(n).padStart(2, "0") + "-" + name + ".png"; await page.locator("#glass").screenshot({ path: f }); shotsOut.push(f); }
  const r = await ev(() => {
    const scr = document.getElementById("screen"), R = scr.getBoundingClientRect(), f = 480 / R.width, cx = R.left + R.width / 2, cy = R.top + R.height / 2;
    const vis = el => { for (let e = el; e && e !== scr; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === "none" || cs.visibility === "hidden" || +cs.opacity < 0.05) return false; } return true; };
    const dist = (x, y) => Math.hypot((x - cx) * f, (y - cy) * f);
    const corners = (r, rad = 0) => { const k = Math.min(rad, r.width / 2, r.height / 2) * 0.2929; return [[r.left + k, r.top + k], [r.right - k, r.top + k], [r.left + k, r.bottom - k], [r.right - k, r.bottom - k]]; };
    const radOf = el => { if (el instanceof SVGElement) return el.matches(".ow") ? 22 : 0; const cs = getComputedStyle(el); return parseFloat(cs.borderTopLeftRadius) * (R.width / 466) || 0; };
    const inter = (a, b, pad = 0) => a.left < b.right - pad && b.left < a.right - pad && a.top < b.bottom - pad && b.top < a.bottom - pad;
    const out = { cut: [], rim: [], tiny: [], small: [], eyes: [] };
    const label = el => ((el.dataset && el.dataset.act) || (el.className && (el.className.baseVal ?? el.className)) || el.tagName) + ":" + (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 20);
    // controls
    const ctrls = [...scr.querySelectorAll("[data-act], .kk, .ow")].filter(el => !el.closest("#face, .pill, .rim") && vis(el)).map(el => ({ el, r: el.getBoundingClientRect() })).filter(c => c.r.width > 1 && c.r.height > 1);
    for (const { el, r } of ctrls) {
      const w = r.width * f, h = r.height * f;
      if (Math.min(w, h) < 44 - 0.5) out.small.push(`${label(el)} ${w.toFixed(0)}x${h.toFixed(0)}`);
      const o = Math.max(...corners(r, radOf(el)).map(([x, y]) => dist(x, y))) - 228; if (o > 0.5 && !el.matches(".mapcv")) out.cut.push(`BTN ${label(el)} +${o.toFixed(0)}`);
    }
    // text: html text runs (range rects) and svg text (per glyph)
    const texts = [], rims = [];
    const tw = document.createTreeWalker(scr, NodeFilter.SHOW_TEXT); let t;
    while ((t = tw.nextNode())) {
      const s = t.textContent.trim(); if (!s) continue; const el = t.parentElement;
      if (el.closest("#face, #srsay, .sr, defs, style, script, .pill")) continue; if (!vis(el)) continue;
      const txt = el.closest("text");
      if (txt) {
        const ctm = txt.getScreenCTM(), fs = parseFloat(getComputedStyle(txt).fontSize) * Math.hypot(ctm.a, ctm.b) * f;
        if (fs < 18 - 0.05) out.tiny.push(`"${s.slice(0, 24)}" ${fs.toFixed(1)}px`);
        const N = txt.getNumberOfChars(), isRim = !!txt.closest("svg.rim");
        for (let i = 0; i < N; i++) { let b; try { b = txt.getExtentOfChar(i); } catch (e) { continue; } if (!b.width) continue;
          const p = new DOMPoint(b.x, b.y).matrixTransform(ctm), q = new DOMPoint(b.x + b.width, b.y + b.height).matrixTransform(ctm);
          const rr = { left: Math.min(p.x, q.x), right: Math.max(p.x, q.x), top: Math.min(p.y, q.y), bottom: Math.max(p.y, q.y) };
          const ch = txt.textContent[i] || ""; if (!ch.trim()) continue;
          const shrink = { left: rr.left + (rr.right - rr.left) * 0.2, right: rr.right - (rr.right - rr.left) * 0.2, top: rr.top + (rr.bottom - rr.top) * 0.2, bottom: rr.bottom - (rr.bottom - rr.top) * 0.2 };
          const o = Math.max(...corners(shrink).map(([x, y]) => dist(x, y))) - 228; if (o > 0.5) out.cut.push(`TXT "${s.slice(0, 20)}"[${ch}] +${o.toFixed(0)}`);
          (isRim ? rims : texts).push({ r: shrink, s, ch });
        }
        continue;
      }
      if (el.closest("svg") && !txt) continue;
      const rg = document.createRange(); rg.selectNodeContents(t);
      const fs = parseFloat(getComputedStyle(el).fontSize) * (R.width / scr.offsetWidth) * f * (() => { let s = 1; for (let e = el; e && e !== scr; e = e.parentElement) { const m = getComputedStyle(e); const tr = m.transform; if (tr && tr !== "none") { const mm = new DOMMatrix(tr); s *= Math.hypot(mm.a, mm.b); } if (m.scale && m.scale !== "none") s *= parseFloat(m.scale); } return s; })();
      if (fs >= 1 && fs < 18 - 0.05) out.tiny.push(`"${s.slice(0, 24)}" ${fs.toFixed(1)}px`);
      if (fs < 1) continue;
      for (const r of rg.getClientRects()) { if (r.width < 1) continue;
        const o = Math.max(...corners(r).map(([x, y]) => dist(x, y))) - 228; if (o > 0.5) out.cut.push(`TXT "${s.slice(0, 24)}" +${o.toFixed(0)}`);
        texts.push({ r, s }); }
    }
    // rim labels vs the screen's words and controls
    const things = texts.map(x => ({ r: x.r, s: x.s })).concat(ctrls.map(c => ({ r: c.r, s: label(c.el) })));
    for (const rm of rims) for (const th of things) if (inter(rm.r, th.r, 1)) { out.rim.push(`rim "${rm.s.slice(0, 18)}" × "${th.s.slice(0, 18)}"`); break; }
    // the eyes' drawn pixels
    const cv = document.getElementById("face"), g = cv.getContext("2d"), S = cv.width, img = g.getImageData(0, 0, S, S).data;
    let x0 = S, y0 = S, x1 = -1, y1 = -1;
    for (let y = 0; y < S; y += 2) for (let x = 0; x < S; x += 2) { if (Math.hypot(x - S / 2, y - S / 2) > 0.42 * S) continue; if (img[(y * S + x) * 4 + 3] > 40) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
    const cb = cv.getBoundingClientRect(), sx = cb.width / S;
    const eyes = x1 < 0 ? null : { left: cb.left + x0 * sx, right: cb.left + x1 * sx, top: cb.top + y0 * sx, bottom: cb.top + y1 * sx };
    if (eyes) {
      for (const c of [...scr.querySelectorAll(".rim .gcap")].filter(vis)) if (!c.closest(".pill") && inter(eyes, c.getBoundingClientRect(), 2)) out.eyes.push("rim capsule");
      for (const c of ctrls) if (!c.el.matches(".ow") && !c.el.closest("#kb") && inter(eyes, c.r, 2) && c.r.width < R.width * 0.8) out.eyes.push("control " + label(c.el));
      for (const tx of texts) if (inter(eyes, tx.r, 2)) { out.eyes.push(`text "${tx.s.slice(0, 18)}"`); break; }
    }
    out.eyesBox = eyes && [((eyes.left - R.left) * f).toFixed(0), ((eyes.top - R.top) * f).toFixed(0), ((eyes.right - eyes.left) * f).toFixed(0), ((eyes.bottom - eyes.top) * f).toFixed(0)].join(",");
    out.view = __soul.S.view;
    for (const k of ["cut", "rim", "tiny", "small", "eyes"]) out[k] = [...new Set(out[k])].slice(0, 12);
    return out;
  });
  const bad = ["cut", "rim", "tiny", "small", "eyes"].filter(k => r[k].length);
  ok(!bad.length, `${name} (${r.view}, eyes ${r.eyesBox}) ` + (bad.length ? bad.map(k => k + ": " + r[k].join(" | ")).join("  ;  ") : "round-safe, type ≥ 18, targets ≥ 44, eyes clear"));
}
/* the navigation hint (prev · CURRENT · next on the lower rim) never runs through content */
await ev(() => { __soul.go("home", "none"); }); await sleep(300);
await ev(() => { __soul.go("reminders", "left"); }); await sleep(500);
const hint = await ev(() => { const d = document.getElementById("dots"); if (d.classList.contains("hide")) return "hidden"; const rs = [...d.querySelectorAll("text")].map(t => t.getBoundingClientRect()); const cs = [...document.querySelectorAll("#cards .card:last-child [data-act], #cards .card:last-child .tx")].map(e => e.getBoundingClientRect());
  return rs.some(a => cs.some(b => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)) ? "overlaps" : "clear"; });
ok(hint !== "overlaps", `the "where am I" rim hint never overlaps content (${hint})`);
ok(errs.length === 0, "zero console / page errors " + errs.join(" | "));
await browser.close();
if (SHOTS && shotsOut.length) { try { execSync(`python3 "${path.join(HERE, "../tools/glass_sheet.py")}" "${SHOTS}" "${SHOTS}audit-sheet.png" --title "SoulOS Alive audit" --cols 8`, { stdio: "inherit" }); } catch (e) {} }
console.log(results.join("\n"));
console.log(`\n${results.filter(r => r.startsWith("PASS")).length} / ${results.length} passed`);
process.exit(results.some(r => r.startsWith("FAIL")) ? 1 : 0);
