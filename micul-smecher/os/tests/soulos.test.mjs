/* SoulOS Playwright suite: node os/tests/soulos.test.mjs [rm|390|1440|v4|live]
   Needs a global `playwright` (npm i -g playwright) with Chromium. Screenshots go to $SOULOS_SHOTS (default: a temp dir).
   The claude.ai `sample` capability does not exist outside claude.ai, so the v4 suite mocks window.claude; the API-key and
   ChatGPT paths are tested with page.route() fakes of api.anthropic.com / api.openai.com. "live" makes one real browser call. */
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import path from "path";
import os from "os";
import fs from "fs";
const root = execSync("npm root -g").toString().trim();
const { chromium } = await import(root + "/playwright/index.mjs");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const FILE = "file://" + path.resolve(HERE, "../index.html");
const OUT = (process.env.SOULOS_SHOTS || path.join(os.tmpdir(), "soulos-shots")) + "/"; fs.mkdirSync(OUT, { recursive: true });
const FONTS = path.join(os.tmpdir(), "soulos-fontcache"); fs.mkdirSync(FONTS, { recursive: true });
const only = process.argv[2];
const results = [];
const ok = (cond, msg) => { results.push((cond ? "PASS " : "FAIL ") + msg); if (!cond) console.log("FAIL", msg); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
/* Google Fonts through curl (the sandbox proxy is flaky for Chromium's parallel woff2 fetches); cached on disk */
async function fonts(page) {
  await page.route(/fonts\.(googleapis|gstatic)\.com/, async route => {
    const url = route.request().url(), f = path.join(FONTS, Buffer.from(url).toString("base64url").slice(-120));
    try { if (!fs.existsSync(f)) execSync(`curl -sS --retry 5 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36" -o "${f}" "${url}"`); } catch (e) {}
    if (!fs.existsSync(f)) return route.fulfill({ status: 200, body: "", headers: { "content-type": "text/css" } });
    await route.fulfill({ status: 200, body: fs.readFileSync(f), headers: { "content-type": /googleapis/.test(url) ? "text/css" : "font/woff2", "access-control-allow-origin": "*" } });
  });
}
/* skip the first-boot sequence (it has its own tests) */
const BORN = () => { try { localStorage.setItem("soulos-born", "1"); } catch (e) {} };

async function run(W, H, tag, dpr) {
  const browser = await chromium.launch();
  const mobile = W < 500;
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: dpr, ignoreHTTPSErrors: true, isMobile: mobile, hasTouch: mobile });
  await ctx.addInitScript(BORN);
  const page = await ctx.newPage();
  const errs = [];
  await fonts(page);
  page.on("console", m => { if (m.type() === "error") errs.push("console: " + m.text() + " @" + (m.location().url || "")); });
  page.on("pageerror", e => errs.push("pageerror: " + e.message));
  await page.goto(FILE, { waitUntil: "load" });
  await sleep(2600);
  await page.evaluate(() => { __soul.cancel("msg"); __soul.cancel("claude"); try { localStorage.clear(); } catch (e) {} __soul.S.ai = "claude"; });
  const box = async () => page.evaluate(() => { const b = document.getElementById("screen").getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width }; });
  await page.evaluate(() => document.getElementById("pebble").scrollIntoView({ block: "center" }));
  await sleep(200);
  let B = await box();
  const pt = (x, y) => [B.x + x / 466 * B.w, B.y + y / 466 * B.w];
  const recenter = async () => { await page.evaluate(() => document.getElementById("pebble").scrollIntoView({ block: "center" })); await sleep(120); B = await box(); };
  const tap = async (x, y, hold = 40) => { const [a, b] = pt(x, y); await page.mouse.move(a, b); await page.mouse.down(); await sleep(hold); await page.mouse.up(); };
  const tapEl = async sel => { const b = await page.locator(sel).first().boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down(); await sleep(40); await page.mouse.up(); };
  const shot = async name => { await page.locator("#pebble").screenshot({ path: OUT + name.replace(/^soulos-/, "soulos3-") + "-" + tag + ".png" }); };
  const keyAt = async ch => page.evaluate(c => { const k = __soul.S.kb.keys.find(k => k.ch && k.ch.toLowerCase() === c); return k ? [k.cx, k.y0 + 26] : null; }, ch);
  const keyId = async id => page.evaluate(i => { const k = __soul.S.kb.keys.find(k => k.id === i); return [k.cx, k.y0 + 26]; }, id);
  const typeTaps = async (str, gap = 70) => { for (const c of str) { const p = c === " " ? await keyId("space") : await keyAt(c); if (!p) throw new Error("no key " + c); await tap(p[0], p[1], 35); await sleep(gap); } };
  const text = async () => page.evaluate(() => __soul.S.kb ? __soul.S.kb.text : null);
  const clear = async () => page.evaluate(() => { const K = __soul.S.kb; K.text = ""; K.shift = "once"; K.lastAuto = null; __soul.kbRender(); });
  const view = async () => page.evaluate(() => __soul.S.view);

  ok(await page.evaluate(() => document.documentElement.lang === "en" && document.getElementById("lang-en").getAttribute("aria-pressed") === "true" && /orbit|Guided/.test(document.body.textContent)), `${tag} English is the default on first load`);
  // the drawn device is SOUL size M: a 90:103 aluminium body with the round glass at 82.5 % of its width
  ok(await page.evaluate(() => { const p = document.getElementById("pebble").getBoundingClientRect(), g = document.getElementById("glass").getBoundingClientRect();
    return Math.abs(p.width / p.height - 90 / 101) < 0.01 && Math.abs(g.width / p.width - 0.825) < 0.01 && !document.querySelector("#pebble svg.body"); }), `${tag} device drawn as SOUL size M (90:101 body, round glass 82.5 %)`);
  // English first load: the Claude reply speaks 12-hour English
  const nRem0 = await page.evaluate(() => __soul.S.rems.length);
  await page.evaluate(() => __soul.go("claude", "left")); await sleep(700);
  await tapEl('#cards .card:last-child [data-act="type-ai"]'); await sleep(500);
  await tap(233, 157); await sleep(150); await tap(...(await keyId("done")), 35); await sleep(2600);
  ok(await page.evaluate(() => /✓ Reminder set for 5:00 PM/.test(document.querySelector("#cards .card:last-child").textContent)), `${tag} EN: "Remind me at 5 to call the bank" -> "✓ Reminder set for 5:00 PM"`);
  ok(await page.evaluate(() => !/[ăâîșț„]/.test(document.getElementById("screen").innerText + document.querySelector(".panel").innerText)), `${tag} EN: no Romanian on the screen or in the panel`);
  await page.evaluate(n => { __soul.S.voice = null; __soul.S.rems.length = n; __soul.go("home", "down"); }, nRem0); await sleep(600);
  // EN keyboard: no Romanian auto-diacritics without Romanian evidence
  await page.evaluate(() => __soul.go("notes", "left")); await sleep(700);
  await tapEl('#cards .card:last-child [data-act="note-add"]'); await sleep(400);
  await typeTaps("sa si maine ", 60);
  ok((await text()) === "Sa si maine ", `${tag} EN keyboard leaves "sa si maine" alone -> "${await text()}"`);
  await clear(); await tapEl("#side"); await sleep(400);
  await page.evaluate(() => { delete __soul.S.drafts.note; });
  // Romanian is one tap away: the keyboard/diacritics suite below runs in RO
  await page.locator("#lang-ro").click(); await recenter();
  // ---------- Keyboard via the Claude app
  await page.evaluate(() => __soul.go("claude", "left")); await sleep(700);
  await tapEl('#cards .card:last-child [data-act="type-ai"]'); await sleep(500);
  ok(await page.evaluate(() => !!__soul.S.kb), `${tag} keyboard opens from Claude app`);
  await shot("soulos-keyboard-empty");
  await typeTaps("hello", 60);
  ok((await text()).toLowerCase() === "hello", `${tag} tap-typing hello (fast taps, 60ms) -> "${await text()}"`);
  await shot("soulos-keyboard-hello");
  // shortcut clash: physical d / Space / Backspace while typing
  await page.keyboard.press("d"); ok((await text()).toLowerCase() === "hellod", `${tag} physical "d" types (no double-tap shortcut)`);
  await page.keyboard.press("Backspace"); ok((await text()).toLowerCase() === "hello", `${tag} physical Backspace deletes (no side button)`);
  ok(await page.evaluate(() => !!__soul.S.kb), `${tag} keyboard still open after Backspace`);
  // hold ⌫ -> word delete + undo chip
  { const p = await keyId("bksp"); const [a, b] = pt(p[0], p[1]); await page.mouse.move(a, b); await page.mouse.down(); await sleep(1500); await page.mouse.up(); }
  ok((await text()) === "", `${tag} hold ⌫ deletes words`);
  await shot("soulos-keyboard-undo");
  await tap(233, 157); await sleep(100);
  ok((await text()).toLowerCase() === "hello", `${tag} ↶ undo chip restores -> "${await text()}"`);
  await clear();
  // auto-diacritics path: "maine si tar" -> suggestion, then space
  await typeTaps("maine ", 70);
  ok((await text()) === "Mâine ", `${tag} auto-diacritic maine->Mâine -> "${await text()}"`);
  await typeTaps("si tara", 70);
  await shot("soulos-keyboard-diacritics");
  await typeTaps(" ", 70);
  ok((await text()).trim().toLowerCase() === "mâine și țară", `${tag} tap-typing "mâine și țară" -> "${await text()}"`);
  // ⌫ right after auto change reverts
  await typeTaps("sa ", 70); await tap(...(await keyId("bksp")), 35); await sleep(80);
  ok((await text()).endsWith(" sa "), `${tag} ⌫ after auto-change restores "sa" -> "${await text()}"`);
  await clear();
  // long-press a -> tray, slide to â
  await typeTaps("m", 60);
  { const p = await keyAt("a"); const [a, b] = pt(p[0], p[1]); await page.mouse.move(a, b); await page.mouse.down(); await sleep(520);
    await shot("soulos-keyboard-tray");
    const [a2, b2] = pt(p[0] + 44, p[1]); await page.mouse.move(a2, b2, { steps: 4 }); await sleep(60); await page.mouse.up(); }
  ok((await text()) === "Mâ", `${tag} long-press a -> tray -> â -> "${await text()}"`);
  await typeTaps("ine ", 60);
  { const p = await keyAt("s"); const [a, b] = pt(p[0], p[1]); await page.mouse.move(a, b); await page.mouse.down(); await sleep(520); await page.mouse.up(); }
  await typeTaps("i ", 60);
  { const p = await keyAt("t"); const [a, b] = pt(p[0], p[1]); await page.mouse.move(a, b); await page.mouse.down(); await sleep(520); await page.mouse.up(); }
  await typeTaps("ar", 60);
  { const p = await keyAt("a"); const [a, b] = pt(p[0], p[1]); await page.mouse.move(a, b); await page.mouse.down(); await sleep(520); await page.mouse.up(); }
  ok((await text()).toLowerCase() === "mâine și țară", `${tag} long-press typing "mâine și țară" -> "${await text()}"`);
  // ?123 layer
  await tap(...(await keyId("layer")), 35); await sleep(120);
  await shot("soulos-keyboard-123");
  await typeTaps("?", 60);
  await tap(...(await keyId("layer")), 35); await sleep(80);
  ok((await text()).endsWith("?"), `${tag} ?123 layer types punctuation`);
  // physical typing
  await page.keyboard.type(" ok");
  ok((await text()).endsWith("? ok"), `${tag} desktop keyboard feeds field -> "${await text()}"`);
  // side button = back (draft kept), reopen restores
  await tapEl("#side"); await sleep(500);
  ok(await page.evaluate(() => !__soul.S.kb && __soul.S.view === "claude" && !!__soul.S.drafts.claude), `${tag} side button closes keyboard, keeps draft`);
  await tapEl('#cards .card:last-child [data-act="type-ai"]'); await sleep(400);
  ok((await text()).endsWith("ok"), `${tag} draft restored on reopen`);
  await clear(); await page.evaluate(() => { __soul.S.kb.text = ""; }); await typeTaps("x", 50); await tap(...(await keyId("bksp")), 35); await sleep(100);

  // ---------- Claude flow: context chip -> send -> think -> reply performs action
  await tap(233, 157); await sleep(150);   // middle chip "Bancă la 5"
  ok(/5/.test(await text()), `${tag} context chip inserts text -> "${await text()}"`);
  await shot("soulos-claude-type-text");
  await tap(...(await keyId("done")), 35); await sleep(700);
  await shot("soulos-claude-type-think");
  ok((await view()) === "voice", `${tag} send -> thinking`);
  await sleep(1800);
  await shot("soulos-claude-type-reply");
  ok(await page.evaluate(() => __soul.S.rems.some(r => r.time === "17:00" && r.text)), `${tag} Claude reply created reminder 17:00`);
  ok(await page.evaluate(() => /17:00/.test(document.querySelector("#cards .card:last-child").textContent)), `${tag} reply card shows ✓ 17:00 chip`);
  await sleep(300);

  // ---------- AI modes
  await page.evaluate(() => __soul.go("settings", "left")); await sleep(600);
  await shot("soulos-ai-mode-settings");
  await tapEl('#cards .card:last-child [data-act="ai"]'); await sleep(600);
  ok((await view()) === "aimode", `${tag} Settings › AI opens picker`);
  await tapEl('#cards .card:last-child [data-m="chatgpt"]'); await sleep(500);
  ok(await page.evaluate(() => __soul.S.ai === "chatgpt"), `${tag} pick ChatGPT mode`);
  await shot("soulos-ai-mode-picker");
  await page.evaluate(() => __soul.go("talk", "left")); await sleep(700);
  await shot("soulos-ai-mode-talk-chatgpt");
  await tapEl('#cards .card:last-child [data-act="type-ai"]'); await sleep(400);
  await tap(88, 157); await sleep(100); await tap(...(await keyId("done")), 35); await sleep(2600);
  await shot("soulos-ai-mode-chatgpt-reply");
  ok(await page.evaluate(() => /ChatGPT/.test(document.querySelector("#cards .card:last-child").textContent)), `${tag} reply tagged ChatGPT`);
  await page.evaluate(() => __soul.setAi("none")); await page.evaluate(() => { __soul.S.voice = null; __soul.go("talk", "fade"); }); await sleep(700);
  await shot("soulos-ai-mode-talk-none");
  await tapEl('#cards .card:last-child [data-act="type-ai"]'); await sleep(400);
  await shot("soulos-ai-mode-none-keyboard");
  await page.keyboard.type("Salut, ce faci?"); await page.keyboard.press("Enter"); await sleep(2500);
  await shot("soulos-ai-mode-none-reply");
  ok(await page.evaluate(() => __soul.S.notes.some(n => n.text === "Salut, ce faci?")), `${tag} no-AI message saved to Notes`);
  await page.evaluate(() => { __soul.S.voice = null; __soul.go("talk", "fade"); }); await sleep(500);
  await tapEl('#cards .card:last-child [data-act="type-ai"]'); await sleep(300);
  await page.keyboard.type("Pune alarma la 6:45"); await page.keyboard.press("Enter"); await sleep(2500);
  ok(await page.evaluate(() => __soul.S.alarms.some(a => a.h === 6 && a.m === 45)), `${tag} no-AI: local grammar sets alarm 06:45`);
  await page.evaluate(() => { __soul.setAi("claude"); __soul.S.voice = null; }); await sleep(300);

  // ---------- Notes
  await page.evaluate(() => __soul.go("notes", "left")); await sleep(700);
  await tapEl('#cards .card:last-child [data-act="note-add"]'); await sleep(400);
  await typeTaps("lapte si paine", 60);
  await shot("soulos-notes-type-typing");
  await tap(...(await keyId("done")), 35); await sleep(700);
  ok(await page.evaluate(() => __soul.S.notes.some(n => n.text === "Lapte și pâine")), `${tag} note saved "Lapte și pâine"`);
  await shot("soulos-notes-type-saved");
  await tapEl('#cards .card:last-child [data-act="note-edit"]'); await sleep(400);
  ok((await text()) === "Lapte și pâine", `${tag} edit opens with note text`);
  await typeTaps(" oua", 60); await tap(...(await keyId("done")), 35); await sleep(600);
  ok(await page.evaluate(() => __soul.S.notes.some(n => n.text === "Lapte și pâine ouă")), `${tag} note edited`);
  await shot("soulos-notes-type-edited");
  // reminders: typed + time grammar
  await page.evaluate(() => __soul.go("reminders", "left")); await sleep(700);
  await tapEl('#cards .card:last-child [data-act="rem-add"]'); await sleep(400);
  await page.keyboard.type("Ia pastilele");
  await tap(...(await keyId("done")), 35); await sleep(800);
  ok((await view()) === "dial", `${tag} reminder without time -> Rim-Dial`);
  await tap(233, 438, 40); await sleep(700);   // hour 0? bottom = 0
  await shot("soulos-notes-type-reminder-dial");
  await tapEl('#cards .card:last-child [data-act="dial-ok"]'); await sleep(700);
  ok(await page.evaluate(() => __soul.S.rems.some(r => r.text === "Ia pastilele")), `${tag} reminder added via dial`);
  await shot("soulos-notes-type-reminders");

  // ---------- Alarms
  await page.evaluate(() => __soul.go("alarms", "left")); await sleep(700);
  await shot("soulos-alarm-list");
  await tapEl('#cards .card:last-child [data-act="al-tog"]'); await sleep(200);
  await tapEl('#cards .card:last-child [data-act="al-add"]'); await sleep(700);
  ok((await view()) === "dial", `${tag} + opens Rim-Dial`);
  { const a = 195 * Math.PI / 180; const [x0, y0] = pt(233 + 205 * Math.cos(a + 0.5), 233 + 205 * Math.sin(a + 0.5)); const [x1, y1] = pt(233 + 205 * Math.cos(a), 233 + 205 * Math.sin(a));
    await page.mouse.move(x0, y0); await page.mouse.down(); await page.mouse.move(x1, y1, { steps: 12 }); await sleep(250); await shot("soulos-alarm-dial-hours"); await page.mouse.up(); }
  await sleep(700);
  ok(await page.evaluate(() => __soul.S.edit.h === 7 && __soul.S.edit.mode === "m"), `${tag} hour 7 set, auto-advance to minutes`);
  { const [x1, y1] = pt(233, 438); await page.mouse.move(x1 - 30, y1 - 3); await page.mouse.down(); await page.mouse.move(x1, y1, { steps: 10 }); await sleep(200); await page.mouse.up(); }
  await sleep(200);
  ok(await page.evaluate(() => __soul.S.edit.m === 30), `${tag} minute 30 set -> ${await page.evaluate(() => __soul.S.edit.h + ":" + __soul.S.edit.m)}`);
  await shot("soulos-alarm-dial-minutes");
  await tapEl('#cards .card:last-child [data-act="dial-ok"]'); await sleep(700);
  ok((await view()) === "alarms" && await page.evaluate(() => __soul.S.alarms.some(a => a.h === 7 && a.m === 30 && a.on)), `${tag} ✓ sets the alarm at once (+ · drag · ✓)`);
  { const id = await page.evaluate(() => __soul.S.alarms.find(a => a.h === 7 && a.m === 30).id); await tapEl(`#cards .card:last-child [data-act="al-edit"][data-id="${id}"]`); } await sleep(700);
  ok((await view()) === "alarmsum", `${tag} tap the alarm -> summary (days, label)`);
  await tapEl('#cards .card:last-child [data-act="as-day"][data-i="0"]'); await sleep(120);
  await tapEl('#cards .card:last-child [data-act="as-day"][data-i="2"]'); await sleep(120);
  await tapEl('#cards .card:last-child [data-act="as-day"][data-i="4"]'); await sleep(120);
  await tapEl('#cards .card:last-child [data-act="as-label"]'); await sleep(400);
  await shot("soulos-alarm-label-keyboard");
  await typeTaps("sala", 60); await tap(...(await keyId("done")), 35); await sleep(400);
  await shot("soulos-alarm-summary");
  await tapEl('#cards .card:last-child [data-act="as-set"]'); await sleep(700);
  ok(await page.evaluate(() => __soul.S.alarms.some(a => a.h === 7 && a.m === 30 && a.on && /^Sal/.test(a.label) && a.days[0] && a.days[2] && a.days[4])), `${tag} alarm 07:30 L Mi V "Sală" saved`);
  await shot("soulos-alarm-set");
  await page.evaluate(() => __soul.ringAlarm(__soul.S.alarms.find(a => a.h === 7 && a.m === 30))); await sleep(350);
  await shot("soulos-alarm-ring-asleep");
  await sleep(1400);
  await shot("soulos-alarm-ring-awake");
  await tapEl('#cards .card:last-child [data-act="ring-stop"]'); await sleep(600);
  ok((await view()) === "home" && await page.evaluate(() => !__soul.S.ringing), `${tag} stop alarm -> home`);

  // ---------- existing features
  await page.locator("#say-0").click(); await sleep(4200);
  ok((await view()) === "voice", `${tag} voice demo phrase runs`);
  await shot("soulos-regress-voice");
  await page.evaluate(() => { __soul.S.voice = null; __soul.cancel("voice"); __soul.cancel("answer"); __soul.go("home", "down"); }); await sleep(500);
  await page.locator("#say-claude").click(); await sleep(400); await recenter();
  ok(await page.evaluate(() => !!__soul.S.claude.pending), `${tag} Claude request arrives`);
  await page.evaluate(() => __soul.go("claude", "up")); await sleep(600);
  { const [a, b] = pt(233, 300); await page.mouse.move(a, b); await page.mouse.down(); await sleep(1900); await page.mouse.up(); }
  await sleep(300);
  ok(await page.evaluate(() => !__soul.S.claude.pending), `${tag} Claude hold-to-approve still works`);
  await page.locator("#lang-en").click(); await sleep(300); await recenter();
  await page.evaluate(() => __soul.go("alarms", "left")); await sleep(600);
  await shot("soulos-alarm-list-en");
  await page.evaluate(() => __soul.go("home", "down")); await sleep(600);
  await recenter();   // stays in English (the default) for the SoulOS 2 flows and screenshots
  // ================= SoulOS 2 =================
  const S2 = async name => { await page.locator("#pebble").screenshot({ path: OUT + "soulos3-" + name + "-" + tag + ".png" }); };
  const drag = async (x0, y0, x1, y1, steps = 10, keep = false) => { const [a, b] = pt(x0, y0); await page.mouse.move(a, b); await page.mouse.down();
    for (let i = 1; i <= steps; i++) { const [c, d] = pt(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps); await page.mouse.move(c, d); await sleep(16); } if (!keep) await page.mouse.up(); };
  const ev = f => page.evaluate(f);
  await recenter();
  await ev(() => { __soul.S.coach = true; __soul.go("home", "down"); }); await sleep(900);
  await S2("home");
  // launcher: swipe → on the face opens the Orbit (app names on the lower rim)
  await drag(140, 240, 330, 240, 10); await sleep(1400);
  ok((await view()) === "apps", `${tag} swipe → on the face opens the orbit`);
  await S2("launcher");
  const near0 = await ev(() => __soul.LN.near);
  await drag(330, 398, 150, 398, 10, true); await sleep(80); await S2("launcher-spin"); await page.mouse.up(); await sleep(1600);
  ok(await ev(() => Math.abs(__soul.LN.rot - Math.round(__soul.LN.rot)) < 0.01 && __soul.LN.tgt == null) && (await ev(() => __soul.LN.near)) !== near0, `${tag} the orbit spins with the finger and settles on a word (${near0} → ${await ev(() => __soul.LN.near)})`);
  // fling: it coasts, then lands on a detent
  await drag(380, 400, 110, 400, 4); await sleep(150);
  ok(await ev(() => Math.abs(__soul.LN.vr) > 1), `${tag} fling: the orbit coasts (v=${(await ev(() => __soul.LN.vr)).toFixed(1)} words/s)`);
  await sleep(2200);
  ok(await ev(() => Math.abs(__soul.LN.rot - Math.round(__soul.LN.rot)) < 0.01 && __soul.LN.tgt == null), `${tag} fling snaps to a word`);
  // tapping a neighbour word spins it to the middle and opens it
  await ev(() => __soul.lnSpinTo("alarms")); await sleep(1200);
  { const pos = await ev(() => __soul.lnIcon("notes")._pos); await tap(pos[0], pos[1]); } await sleep(1700);
  ok((await view()) === "notes", `${tag} tapping a neighbour word spins to it and opens it`);
  await ev(() => __soul.go("apps", "none")); await sleep(900);
  await ev(() => __soul.lnSpinTo("weather")); await sleep(1200);
  await S2("launcher-weather");
  { const pos = await ev(() => __soul.lnIcon("weather")._pos); await tap(pos[0], pos[1]); } await sleep(160);
  await S2("launcher-zoom");
  await sleep(1100);
  ok((await view()) === "weather", `${tag} tap the word: Weather comes out of the eyes`);
  await S2("weather");
  await tap(233, 350); await sleep(900);
  ok(await ev(() => __soul.S.wx.day === 1), `${tag} weather tap → tomorrow`);
  await S2("weather-tomorrow");
  await tap(233, 350); await sleep(900); await S2("weather-rain");
  // card follows the finger, springs back on a short slow drag
  await drag(300, 250, 250, 250, 12, true); await sleep(60);
  ok(await ev(() => Math.abs(document.querySelector("#cards .card:last-child")._st.x) > 20), `${tag} card follows the finger`);
  await S2("card-drag");
  await sleep(300); await page.mouse.up(); await sleep(700);
  ok((await view()) === "weather" && await ev(() => Math.abs(document.querySelector("#cards .card:last-child")._st.x) < 1), `${tag} short drag springs back`);
  await tapEl("#side"); await sleep(800);
  ok((await view()) === "home", `${tag} side button → home`);
  // Today stack
  await drag(233, 380, 233, 200, 8); await sleep(1100);
  ok((await view()) === "today", `${tag} swipe ↑ → Today`);
  await S2("today");
  await drag(233, 330, 233, 180, 8); await sleep(900);
  ok(await ev(() => __soul.TD.tgt === 1), `${tag} Today stack snaps one widget per flick`);
  await drag(233, 330, 233, 180, 8); await sleep(900);
  await S2("today-focus");
  await ev(() => __soul.go("home", "down")); await sleep(800);
  // Control Center
  await drag(233, 60, 233, 330, 10); await sleep(900);
  ok(await ev(() => __soul.S.cc), `${tag} pull ↓ opens Control Center`);
  await S2("control");
  await tapEl('#cc [data-act="cc-dnd"]'); await sleep(300);
  ok(await ev(() => __soul.S.dnd), `${tag} CC: do not disturb on`);
  const arcPt = a => [233 + 205 * Math.cos(a * Math.PI / 180), 233 + 205 * Math.sin(a * Math.PI / 180)];
  { const b0 = await ev(() => __soul.S.bright); await drag(...arcPt(226), ...arcPt(140), 8); ok(await ev(() => __soul.S.bright) < b0 - 0.2, `${tag} Control: light is a dial on the left rim (${b0} → ${(await ev(() => __soul.S.bright)).toFixed(2)})`); }
  { const v0 = await ev(() => __soul.S.vol); await drag(...arcPt(-35), ...arcPt(40), 8); ok(await ev(() => __soul.S.vol) < v0 - 0.2, `${tag} Control: volume is a dial on the right rim (${v0} → ${(await ev(() => __soul.S.vol)).toFixed(2)})`); }
  await S2("control-dnd");
  await tapEl('#cc [data-act="cc-dnd"]'); await sleep(200);
  await drag(233, 420, 233, 200, 8); await sleep(800);
  ok(await ev(() => !__soul.S.cc), `${tag} swipe ↑ closes Control Center`);
  await ev(() => __soul.setBright(1));
  // notifications stack
  await page.locator("#sys-notif").click(); await sleep(700); await page.locator("#sys-notif").click(); await sleep(350);
  await recenter();
  ok(await ev(() => document.querySelectorAll(".pill.ghost").length >= 1), `${tag} notifications stack (ghost behind the new banner)`);
  await S2("notif-stack");
  await sleep(2600);
  ok(await ev(() => __soul.S.nh.length >= 2), `${tag} notification history kept`);
  await ev(() => { __soul.S.pill && document.getElementById("pill").classList.remove("show"); __soul.S.pill = null; });
  // Timer
  await ev(() => __soul.go("timer", "left")); await sleep(700);
  await tapEl('#cards .card:last-child [data-act="sw-go"]'); await sleep(1300);
  await tapEl('#cards .card:last-child [data-act="sw-lap"]'); await sleep(500);
  ok(await ev(() => __soul.S.tm.sw.run && __soul.S.tm.sw.laps.length === 1), `${tag} stopwatch runs + lap`);
  await S2("timer-stopwatch");
  await tapEl('#cards .card:last-child [data-act="sw-go"]'); await sleep(200);
  await tapEl('#cards .card:last-child [data-act="tm-mode"][data-m="cd"]'); await sleep(300);
  await tapEl('#cards .card:last-child [data-act="cd-pre"][data-m="1"]'); await sleep(1600);
  ok(await ev(() => __soul.S.tm.cd.run && __soul.S.tm.cd.left < 59), `${tag} countdown 1′ runs`);
  await S2("timer-countdown");
  await ev(() => { __soul.S.tm.cd.left = 0.05; }); await sleep(900);
  ok(await ev(() => __soul.S.tm.cd.done), `${tag} countdown finishes`);
  await S2("timer-done");
  await ev(() => { __soul.S.tm.mode = "sw"; __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); });
  // Music
  await ev(() => __soul.go("music", "left")); await sleep(800); await S2("music");
  // Soul page + rename via the round keyboard
  await ev(() => __soul.go("soul", "left")); await sleep(800);
  await S2("soul");
  await tapEl('#cards .card:last-child [data-act="soul-name"]'); await sleep(400);
  await clear(); await typeTaps("pufi", 60); await tap(...(await keyId("done")), 35); await sleep(700);
  ok(await ev(() => __soul.S.soul.name === "Pufi"), `${tag} rename Soul via keyboard -> ${await ev(() => __soul.S.soul.name)}`);
  await tapEl('#cards .card:last-child [data-act="soul-mood"]'); await sleep(900);
  await S2("soul-renamed");
  await ev(() => { try { localStorage.removeItem("soulos-name"); } catch (e) {} __soul.S.soul.name = null; });
  // Games
  await ev(() => __soul.go("games", "left")); await sleep(800);
  await S2("games");
  await tapEl('#cards .card:last-child [data-act="game-start"]'); await sleep(200);
  for (let k = 0; k < 40 && (await ev(() => __soul.S.game.score)) < 3; k++) {
    const st = await ev(() => { const G = __soul.S.game; const s = G.stars.find(s => G.t - s.born > 0.15); return s ? [s.x, s.y] : null; });
    if (st) { await tap(st[0], st[1], 30); await sleep(90); } else await sleep(120);
  }
  ok(await ev(() => __soul.S.game.score >= 3), `${tag} game: tapping stars scores (${await ev(() => __soul.S.game.score)})`);
  await sleep(250); await S2("game");
  await ev(() => { __soul.S.game.left = 0.02; }); await sleep(1200);
  ok(await ev(() => __soul.S.game.over && !__soul.S.game.run), `${tag} game over screen`);
  await S2("game-over");
  // charging + sleep + wake
  await ev(() => { __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); __soul.go("home", "down"); }); await sleep(700);
  await page.locator("#sys-charge").click(); await recenter(); await sleep(1500);
  ok(await ev(() => __soul.S.batt.chg && __soul.S.chgShow), `${tag} charging animation`);
  await S2("charging");
  await sleep(2600);
  await page.locator("#sys-sleep").click(); await recenter(); await sleep(1800);
  ok(await ev(() => __soul.S.sleeping), `${tag} sleep: breathing eyes`);
  await S2("sleep");
  await tap(233, 233); await sleep(650);
  ok(await ev(() => !__soul.S.sleeping), `${tag} tap wakes it`);
  await S2("wake");
  await ev(() => __soul.plug(false)); await sleep(1800);
  // wheel = crown
  if (!mobile) {
    const [cx, cy] = pt(233, 233); await page.mouse.move(cx, cy); await page.mouse.wheel(0, 120); await sleep(1200);
    ok((await view()) === "apps", `${tag} wheel on the face opens the orbit`);
    const r1 = await ev(() => __soul.LN.rot); await page.mouse.wheel(0, 160); await sleep(700);
    ok(await page.evaluate(r => Math.abs(__soul.LN.rot - r) > 0.5, r1), `${tag} wheel (crown) turns the orbit one word (${r1} → ${(await ev(() => __soul.LN.rot)).toFixed(2)})`);
    // frame pacing while the honeycomb moves
    const meter = glide => page.evaluate(g => new Promise(res => { if (g) __soul.LN.vr = 12; let n = 0, t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 1500) requestAnimationFrame(f); else res(Math.round(n / 1.5)); }; requestAnimationFrame(f); }), glide);
    await sleep(1200); const base = await meter(false), fps = await meter(true);
    ok(fps >= base * 0.75, `${tag} orbit glide keeps the frame rate: ${fps} fps vs ${base} fps idle (headless software renderer caps near 50; real GPUs run 60)`);
    await tapEl("#side"); await sleep(700);
  }
  // touch: swipes inside the screen never scroll the page
  if (mobile) {
    const cdp = await ctx.newCDPSession(page);
    const touchDrag = async (x0, y0, x1, y1, steps = 8) => { const [a, b] = pt(x0, y0); await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a, y: b }] });
      for (let i = 1; i <= steps; i++) { const [c, d] = pt(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps); await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: c, y: d }] }); await sleep(16); }
      await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); };
    await ev(() => __soul.go("home", "down")); await sleep(700);
    const y0 = await ev(() => scrollY);
    await touchDrag(233, 380, 233, 150); await sleep(900);
    ok((await view()) === "today" && Math.abs((await ev(() => scrollY)) - y0) < 1, `${tag} touch swipe ↑ → Today, page did not scroll (${y0} → ${await ev(() => scrollY)})`);
    await touchDrag(233, 180, 233, 380); await sleep(900);
    await touchDrag(233, 60, 233, 330); await sleep(900);
    ok(await ev(() => __soul.S.cc) && Math.abs((await ev(() => scrollY)) - y0) < 1, `${tag} touch pull ↓ → Control Center, no page scroll`);
    await touchDrag(233, 420, 233, 180); await sleep(700);
    await touchDrag(130, 240, 340, 240); await sleep(1300);
    ok((await view()) === "apps", `${tag} touch swipe → orbit`);
    await touchDrag(233, 233, 140, 320); await sleep(300);
    ok(Math.abs((await ev(() => scrollY)) - y0) < 1, `${tag} touch spin on the orbit, no page scroll`);
    await tapEl("#side"); await sleep(700);
  }
  // guided tour: starts, plays, stops on touch
  await page.locator("#tourBtn").click(); await recenter(); await sleep(8500);
  ok(await ev(() => !!__soul.TOUR), `${tag} guided tour runs`);
  await S2("tour");
  await tap(233, 233); await sleep(500);
  ok(await ev(() => !__soul.TOUR), `${tag} touching the screen stops the tour`);
  await ev(() => { __soul.go("home", "down"); }); await sleep(800);
  // arrow keys still work when no field focused
  await page.locator("#screen").focus(); await page.keyboard.press("ArrowRight"); await sleep(500);
  ok((await view()) === "talk", `${tag} arrow shortcut works when not typing`);
  const hs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  ok(hs[0] <= hs[1], `${tag} no horizontal scroll (${hs[0]} <= ${hs[1]})`);
  await page.evaluate(() => __soul.go("home", "down")); await sleep(700);
  await page.evaluate(() => window.scrollTo(0, 0)); await sleep(100);
  await page.screenshot({ path: OUT + "soulos3-device-" + tag + ".png" });
  await page.screenshot({ path: OUT + "soulos3-page-" + tag + ".png", fullPage: true });
  ok(errs.length === 0, `${tag} zero console/page errors ${errs.join(" | ")}`);
  await browser.close();
}
async function reduced() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  await page.addInitScript(BORN);
  const errs = []; page.on("pageerror", e => errs.push(e.message));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.fulfill({ status: 200, body: "", headers: { "content-type": "text/css" } }));
  await page.goto(FILE, { waitUntil: "load" }); await sleep(800);
  await page.evaluate(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.go("apps", "none"); }); await sleep(200);
  const inst = await page.evaluate(() => __soul.LN.open === 1 && __soul.ANIMS.size === 0);
  await page.evaluate(() => __soul.openApp("weather", __soul.lnIcon("weather"))); await sleep(100);
  const inst2 = await page.evaluate(() => { const c = document.querySelector("#cards .card:last-child"); return __soul.S.view === "weather" && c._st.s === 1 && __soul.ANIMS.size === 0; });
  ok(inst && inst2 && !errs.length, `reduced-motion: launcher and app open are instant, no errors ${errs.join(" | ")}`);
  await browser.close();
}

/* ================= SoulOS 4: the new eyes, first boot, a real brain (mocked here), approvals, modes, errors ================= */
/* window.claude as claude.ai serves it: claude.use("sample") → sample(turns, {onText, signal, modelTier, cache}).
   The mock answers in the SOUL JSON protocol, streams in three chunks, and can be told to fail or wait. */
function mockClaude() {
  window.__calls = []; window.__sampleDelay = 300; window.__sampleFail = null; window.__nextReply = null;
  const reply = last => {
    if (window.__nextReply) { const r = window.__nextReply; window.__nextReply = null; return r; }
    const m = last.match(/(\d{1,2})[:.](\d{2})/);
    if (m) return JSON.stringify({ say: `Alarm set for ${m[1]}:${m[2]}. Sleep well.`, face: "happy", actions: [{ type: "alarm.set", time: m[1].padStart(2, "0") + ":" + m[2], label: "Wake up", repeat: "once" }] });
    const t = last.match(/timer[^\d]*(\d+)/i);
    if (t) return JSON.stringify({ say: `Timer for ${t[1]} minutes, starting now.`, actions: [{ type: "timer.start", minutes: +t[1] }] });
    return JSON.stringify({ say: "Hi! I'm right here with you.", face: "happy", actions: [] });
  };
  const sample = async (input, opts = {}) => {
    window.__calls.push({ input, modelTier: opts.modelTier, cache: opts.cache });
    await new Promise(r => setTimeout(r, window.__sampleDelay));
    if (window.__sampleFail) { const f = window.__sampleFail; throw f; }
    const last = Array.isArray(input) ? input[input.length - 1].content : String(input), text = reply(last);
    if (opts.signal && opts.signal.aborted) throw { code: "cancelled", message: "cancelled" };
    const k = Math.ceil(text.length / 3);
    for (let i = 1; i <= 3; i++) { if (opts.onText) opts.onText({ text: text.slice(0, i * k), delta: text.slice((i - 1) * k, i * k) }); await new Promise(r => setTimeout(r, 80)); }
    return { text, truncated: false, modelTierApplied: "quick" };
  };
  window.claude = { use: async name => name === "sample" ? sample : null };
}
/* a microphone that hears what the test says */
function mockMic() {
  window.__srText = "wake me up at 6:30";
  class FakeSR { start() { window.__srStarted = (window.__srStarted || 0) + 1; this._t = setTimeout(() => { if (this.onresult) this.onresult({ results: [[{ transcript: window.__srText }]] }); }, 150); }
    stop() { setTimeout(() => this.onend && this.onend(), 40); } abort() { clearTimeout(this._t); } }
  window.SpeechRecognition = FakeSR;
}
async function v4() {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(mockClaude); await ctx.addInitScript(mockMic);
  const page = await ctx.newPage();
  await fonts(page);
  const errs = [];
  page.on("console", m => { if (m.type() === "error" && !/net::ERR_FAILED|Failed to load resource/.test(m.text())) errs.push("console: " + m.text()); });
  page.on("pageerror", e => errs.push("pageerror: " + e.message));
  const ev = (f, a) => page.evaluate(f, a);
  const shot = async name => page.locator("#pebble").screenshot({ path: OUT + "soulos4-" + name + ".png" });
  const box = async () => page.evaluate(() => { const b = document.getElementById("screen").getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width }; });
  let B;
  const pt = (x, y) => [B.x + x / 466 * B.w, B.y + y / 466 * B.w];
  const tap = async (x, y, hold = 40) => { const [a, b] = pt(x, y); await page.mouse.move(a, b); await page.mouse.down(); await sleep(hold); await page.mouse.up(); };
  const press = async (x, y) => { const [a, b] = pt(x, y); await page.mouse.move(a, b); await page.mouse.down(); };
  const tapEl = async sel => { const b = await page.locator(sel).first().boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down(); await sleep(40); await page.mouse.up(); };
  const card = s => `#cards .card:last-child ${s}`;
  const settle = () => sleep(450);

  // ---------- first boot: birth → name → brain → hold the glass
  await page.goto(FILE, { waitUntil: "load" }); await sleep(300);
  await ev(() => { window.__ex = []; __soul.soul.rig.onChange = n => window.__ex.push(n); });   // every expression the eyes take, in order
  const exSince = async n => ev(k => window.__ex.slice(k), n);
  await ev(() => document.getElementById("pebble").scrollIntoView({ block: "center" })); B = await box();
  ok(await ev(() => __soul.BOOT.on && __soul.S.view === "birth" && !__soul.BOOT.reveal), "v4 first boot starts with the birth (eyes not yet open)");
  await shot("boot-1-chip");
  await sleep(1900);
  ok(await ev(() => __soul.BOOT.reveal && window.__ex.includes("hello")), `v4 birth reveals the eyes with "hello" (${await ev(() => window.__ex.join(","))})`);
  const born = await ev(() => ({ name: __soul.BIRTH.roll.design.name, id: __soul.soul.design.id, rid: __soul.BIRTH.roll.design.id, chip: __soul.BIRTH.chip, txt: document.querySelector("#cards .card:last-child").textContent }));
  ok(born.id === born.rid && born.txt.includes(born.name) && /1 in/.test(born.txt), `v4 birth shows this unit's design: ${born.name} (chip ${born.chip})`);
  await sleep(700); await shot("boot-2-reveal");
  await tap(233, 233); await settle();
  ok(await ev(() => __soul.S.view === "bname"), "v4 tap → name step");
  await shot("boot-3-name");
  await tapEl(card('[data-act="boot-name"]')); await sleep(900);
  ok(await ev(() => __soul.S.view === "bai" && !!__soul.S.soul.name), `v4 one tap names it (${await ev(() => __soul.S.soul.name)}) → brain step`);
  ok(await ev(() => /live/i.test(document.querySelector('#cards .card:last-child [data-m="claude"]').textContent)), "v4 brain step shows Claude as live (capability present)");
  await shot("boot-4-brain");
  await tapEl(card('[data-act="boot-ai"][data-m="claude"]')); await sleep(900);
  ok(await ev(() => __soul.S.view === "bhold" && __soul.S.ai === "claude"), "v4 pick Claude → hold-the-glass tutorial");
  await shot("boot-5-hold");
  await press(233, 260); await sleep(800);
  ok(await ev(() => __soul.BOOT.holding && __soul.soul.st === "listen" && __soul.soul.mood === "listening"), `v4 holding the glass: eyes listen, rim turns ice (${await ev(() => [__soul.BOOT.holding, __soul.BOOT.step, __soul.S.view, __soul.soul.st, __soul.soul.mood, !!__soul.S.kb].join("/"))})`);
  await shot("boot-6-holding");
  await page.mouse.up(); await sleep(300);
  ok(await ev(() => __soul.BOOT.learned && __soul.soul.expression === "approve"), `v4 let go → "approve" (${await ev(() => __soul.soul.expression)})`);
  await shot("boot-7-done");
  await sleep(2100);
  ok(await ev(() => !__soul.BOOT.on && __soul.S.view === "home" && localStorage.getItem("soulos-born") === "1"), "v4 onboarding ends on the face, remembered");
  await ev(() => { __soul.cancel("msg"); __soul.cancel("claude"); });

  // ---------- the new eyes are the engine (inlined), not the old renderer
  const eng = await ev(() => ({ v: window.SoulEyes && SoulEyes.VERSION, n: (window.SOUL_DESIGNS || {}).designs.length, ex: SoulEyes.EXPRESSIONS.length }));
  ok(eng.v === "2.1.0" && eng.n === 120 && eng.ex === 31, `v4 SOUL eyes engine ${eng.v} inlined: ${eng.n} designs, ${eng.ex} expressions`);
  ok(await ev(() => { const c = document.getElementById("face"), x = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < x.length; i += 16) if (x[i] + x[i + 1] + x[i + 2] > 120) n++; return n > 500; }), "v4 the face canvas draws the eyes");

  // ---------- Claude (mocked capability): ask by typing → thinking → talking → the action happens
  await ev(() => __soul.go("talk", "left")); await settle();
  await tapEl(card('[data-act="type-ai"]')); await sleep(300);
  await ev(() => { window.__sampleDelay = 900; });
  await page.keyboard.type("Set an alarm for 6:45 please"); await page.keyboard.press("Enter"); await sleep(250);
  ok(await ev(() => __soul.S.view === "voice" && __soul.S.voice.phase === "think" && __soul.soul.expression === "thinking"), "v4 send → eyes think (thinking)");
  await shot("claude-think");
  await sleep(1300);
  const c1 = await ev(() => ({ calls: window.__calls.length, last: window.__calls[window.__calls.length - 1], txt: document.querySelector("#cards .card:last-child").textContent, al: __soul.S.alarms.some(a => a.h === 6 && a.m === 45 && a.on), src: __soul.S.voice && __soul.S.voice.src }));
  ok(c1.calls === 1 && c1.last.modelTier === "quick" && c1.last.cache === false && /alarm\.set/.test(c1.last.input[0].content) && /6:45/.test(c1.last.input[c1.last.input.length - 1].content), "v4 one sample() call: rules + device state first, the question last, quick tier, no cache");
  ok(c1.al && /Alarm set for 6:45/.test(c1.txt) && /✓ Alarm 6:45 AM/.test(c1.txt) && c1.src === "Claude · live", `v4 Claude's reply is shown and its alarm.set ran (${c1.src})`);
  ok(await ev(() => ["speak", "idle"].includes(__soul.soul.st)), "v4 eyes talk while the answer is said");
  await shot("claude-answer");
  await sleep(2600);
  ok((await ev(() => window.__ex.slice(-6))).includes("approve"), `v4 an answer that acted ends on approve (${(await ev(() => window.__ex.slice(-6))).join(",")})`);
  await ev(() => { __soul.S.voice = null; __soul.go("home", "down"); }); await settle();

  // ---------- an alarm in two gestures: hold the glass and say it (1), let go (2)
  await ev(() => { window.__srText = "wake me up at 6:30"; window.__sampleDelay = 300; }); const n0 = await ev(() => __soul.S.alarms.length);
  await press(233, 250); await sleep(700);
  ok(await ev(() => __soul.S.view === "voice" && __soul.S.voice.phase === "listen" && !__soul.S.voice.sim && __soul.soul.expression === "listening" && document.getElementById("srsay").textContent === "Listening…"), "v4 hold: real mic path, eyes listening, screen reader hears “Listening…”");
  await shot("voice-listen");
  await page.mouse.up(); await sleep(2200);
  ok(await ev(n => __soul.S.alarms.length === n + 1 && __soul.S.alarms.some(a => a.h === 6 && a.m === 30), n0), "v4 alarm in 2 gestures: hold + say “wake me up at 6:30”, let go → alarm 06:30");
  await ev(() => { __soul.S.voice = null; __soul.go("home", "down"); }); await settle();

  // ---------- a note by voice: on Notes, hold and speak; it is kept on the device, no AI round trip
  await ev(() => { window.__srText = "buy oat milk"; __soul.go("notes", "left"); }); await settle(); const calls0 = await ev(() => window.__calls.length);
  await press(233, 300); await sleep(600); await page.mouse.up(); await sleep(1500);
  ok(await ev(c => __soul.S.notes.some(n => n.text === "buy oat milk") && window.__calls.length === c, calls0), "v4 note by voice saved locally (no AI call)");
  await ev(() => { __soul.S.voice = null; __soul.go("home", "down"); }); await settle();

  // ---------- strict protocol validation
  const pv = await ev(() => {
    const P = __soul.parseReply;
    const a = P('{"say":"ok","actions":[{"type":"timer.start","minutes":10},{"type":"note.create","text":"milk"},{"type":"alarm.set","time":"25:00"},{"type":"alarm.set","time":"7:05","label":"x","extra":1},{"type":"timer.start","minutes":999},{"type":"rm -rf"}]}');
    const b = P("Sure! Here you go: {\"say\":\"Done\",\"actions\":[{\"type\":\"reminder.create\",\"time\":\"09:30\",\"day\":\"tomorrow\",\"text\":\"Call mom\"}]} hope that helps");
    const c = P("I am not JSON at all");
    const d = P('{"say":"x","actions":[{"type":"alarm.set","time":"07:00","repeat":"sometimes"}]}');
    const e = __soul.sayPartial('{"say":"Hello wor');
    return { a: [a.actions.length, a.rejected, a.actions.map(x => x.type).join(",")], b: [b.say, b.actions.length, b.actions[0] && b.actions[0].day], c: [c.say, c.actions.length], d: [d.actions.length, d.rejected], e };
  });
  ok(pv.a[0] === 2 && pv.a[1] === 4 && pv.a[2] === "timer.start,note.create", `v4 protocol: at most 3 actions read; bad time, extra key, out-of-range, unknown type rejected (${pv.a.join(" | ")})`);
  { const v = await ev(() => [__soul.validAction({ type: "alarm.set", time: "7:05", label: "Gym" }), __soul.validAction({ type: "alarm.set", time: "07:05", label: "x", extra: 1 }), __soul.validAction({ type: "focus.start", minutes: 2 })]);
    ok(v[0] && v[0].time === "07:05" && v[1] === null && v[2] === null, "v4 protocol: times normalised to HH:MM; extra keys and out-of-range minutes refused"); }
  ok(pv.b[0] === "Done" && pv.b[1] === 1 && pv.b[2] === "tomorrow", "v4 protocol: JSON wrapped in prose is still read");
  ok(pv.c[1] === 0 && /not JSON/.test(pv.c[0]), "v4 protocol: plain text becomes the reply, with no actions");
  ok(pv.d[0] === 0 && pv.d[1] === 1, "v4 protocol: an invalid enum drops the action");
  ok(pv.e === "Hello wor", "v4 streaming: the say of a half-written JSON reply is shown");
  // a reply with injected nonsense actions does nothing harmful
  await ev(() => { window.__nextReply = '{"say":"Doing it","actions":[{"type":"alarm.set","time":"99:99"},{"type":"messages.send","to":"all"}]}'; __soul.aiAsk("do weird stuff", "home"); }); await sleep(1300);
  ok(await ev(() => /2 actions ignored/.test(document.querySelector("#cards .card:last-child").textContent)), "v4 rejected actions are shown as “ignored”, nothing runs");
  await ev(() => { __soul.S.voice = null; __soul.go("home", "down"); }); await settle();

  // ---------- Claude asks for approval: shocked, then wide eyes on you; hold anywhere it shows = yes, 2× = no
  await ev(() => __soul.claudeArrive()); await sleep(150);
  ok(await ev(() => __soul.soul.expression === "shocked" && __soul.S.pill && __soul.S.pill.act === "claude"), "v4 a Claude request: eyes “shocked”, the note lands on the rim");
  await shot("approve-arrive");
  await sleep(1700);
  ok(await ev(() => __soul.soul.st === "wait" && __soul.soul.alert), "v4 then wide eyes looking at you, amber rim");
  await press(233, 260); await sleep(1900); await page.mouse.up(); await sleep(150);
  ok(await ev(() => !__soul.S.claude.pending && __soul.soul.expression === "approve"), "v4 approve in one gesture: hold the glass on the face (1.2 s)");
  await shot("approve-done");
  await sleep(1500);
  await ev(() => __soul.claudeArrive()); await sleep(1600);
  await tap(233, 260); await sleep(120); await tap(233, 260); await sleep(250);
  ok(await ev(() => !__soul.S.claude.pending && /Denied/.test(document.getElementById("pill").textContent)), "v4 double-tap the face = deny");
  await sleep(1500);

  // ---------- Claude working = the reading scan
  await ev(() => __soul.go("claude", "left")); await sleep(600);
  ok(await ev(() => __soul.soul.expression === "working"), "v4 Claude app: eyes do the reading scan (working)");
  await ev(() => __soul.go("home", "down")); await settle();

  // ---------- errors are said by the eyes first (confused), then a short line
  await ev(() => { window.__sampleFail = { code: "rate_limited", message: "x" }; __soul.aiAsk("tell me a joke", "home"); }); await sleep(1100);
  ok(await ev(() => __soul.soul.expression === "confused" && /Too many questions/.test(document.querySelector("#cards .card:last-child").textContent)), "v4 rate limit → confused + short text");
  await shot("error-rate");
  await ev(() => { window.__sampleFail = { code: "not_granted", message: "x" }; __soul.aiAsk("remind me at 9:15 to stretch", "home"); }); await sleep(1100);
  ok(await ev(() => /wasn.t allowed/.test(document.querySelector("#cards .card:last-child").textContent) && __soul.S.rems.some(r => r.time === "09:15")), "v4 not allowed → says so, and the device rules still set the reminder");
  await ev(() => { window.__sampleFail = null; __soul.S.voice = null; }); await ctx.setOffline(true);
  await ev(() => __soul.aiAsk("hello", "home")); await sleep(1000);
  ok(await ev(() => /offline/i.test(document.querySelector("#cards .card:last-child").textContent) && __soul.soul.expression === "confused"), "v4 offline → confused + “You're offline.”");
  await ctx.setOffline(false); await ev(() => { __soul.S.voice = null; __soul.go("home", "down"); }); await settle();

  // ---------- mode switching + your own key (api.anthropic.com faked with page.route)
  let seen = null, status = 200;
  await page.route("https://api.anthropic.com/v1/messages", async route => {
    const r = route.request(); seen = { h: r.headers(), body: JSON.parse(r.postData() || "{}") };
    if (r.method() === "OPTIONS") return route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST" } });
    if (status !== 200) return route.fulfill({ status, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify({ type: "error", error: { type: "authentication_error", message: "invalid x-api-key" } }) });
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify({ id: "msg_1", type: "message", role: "assistant", model: "claude-opus-5-5", stop_reason: "end_turn", content: [{ type: "thinking", thinking: "" }, { type: "text", text: '{"say":"Timer for 10 minutes. Go!","actions":[{"type":"timer.start","minutes":10}]}' }] }) });
  });
  await ev(() => __soul.go("settings", "left")); await settle();
  await tapEl(card('[data-act="ai"]')); await settle();
  ok(await ev(() => __soul.S.view === "aimode"), "v4 Settings › AI opens the brain list");
  await shot("aimode");
  await tapEl(card('[data-act="aim"][data-m="api"]')); await sleep(400);
  ok(await ev(() => __soul.S.ai === "api" && __soul.S.kb && __soul.S.kb.mask), "v4 pick “Your API key” with no key → the round keyboard asks for it (masked)");
  await page.keyboard.type("hello"); await page.keyboard.press("Enter"); await sleep(300);
  ok(await ev(() => !__soul.BRAIN.keys.anthropic && /look like a key/.test(document.getElementById("pill").textContent) && __soul.soul.expression === "confused"), "v4 a non-key is refused (confused)");
  await tapEl(card('[data-act="aim"][data-m="api"]')); await sleep(400);
  const fake = "sk-ant-api03-TESTKEYTESTKEYTESTKEY0123456789";
  await ev(k => { const dt = new DataTransfer(); dt.setData("text/plain", k); document.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true })); }, fake); await sleep(150);
  ok(await ev(() => /•••/.test(document.getElementById("kf").textContent) && !/TESTKEYTESTKEYTEST/.test(document.getElementById("kf").textContent)), "v4 a pasted key is shown masked");
  await shot("key-entry");
  await page.keyboard.press("Enter"); await sleep(300);
  ok(await ev(k => __soul.BRAIN.keys.anthropic === k && localStorage.getItem("soulos-key-anthropic") === null, fake), "v4 key kept in memory only (not in localStorage unless “remember” is ticked)");
  await ev(() => __soul.aiAsk("start a timer for 10 minutes", "home")); await sleep(1500);
  ok(seen && seen.h["x-api-key"] === fake && seen.h["anthropic-dangerous-direct-browser-access"] === "true" && seen.h["anthropic-version"] === "2023-06-01" && seen.body.model === "claude-opus-5-5" && seen.body.output_config.effort === "low" && seen.body.system.includes("timer.start"), "v4 your key: the page calls api.anthropic.com directly (model claude-opus-5-5, browser-access header)");
  ok(await ev(() => __soul.S.tm.cd.run && __soul.S.tm.cd.total === 600 && /Claude · your API key/.test(document.querySelector("#cards .card:last-child").textContent)), "v4 your key: reply parsed (thinking block skipped), timer 10 min started");
  await shot("api-answer");
  status = 401; await ev(() => __soul.aiAsk("hello", "home")); await sleep(1300);
  ok(await ev(() => /API key was rejected/.test(document.querySelector("#cards .card:last-child").textContent) && __soul.soul.expression === "confused"), "v4 a bad key (401) → confused + “That API key was rejected.”");
  await shot("api-badkey");
  // ChatGPT with its own key
  let oa = null;
  await page.route("https://api.openai.com/v1/chat/completions", async route => { const r = route.request(); oa = { h: r.headers(), body: JSON.parse(r.postData() || "{}") };
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify({ choices: [{ message: { role: "assistant", content: '{"say":"Noted: call the dentist.","actions":[{"type":"note.create","text":"Call the dentist"}]}' } }] }) }); });
  await ev(() => { __soul.S.voice = null; __soul.setKey("openai", "sk-proj-TESTKEYTESTKEYTESTKEY123"); __soul.setAi("chatgpt"); __soul.aiAsk("note: call the dentist", "home"); }); await sleep(1400);
  ok(oa && oa.h.authorization === "Bearer sk-proj-TESTKEYTESTKEYTESTKEY123" && oa.body.response_format.type === "json_object" && await ev(() => __soul.S.notes.some(n => n.text === "Call the dentist")), "v4 ChatGPT mode: api.openai.com with your key, note created");
  // the panel's mode picker and key fields
  await page.locator("#ai-api").click(); await sleep(200);
  ok(await ev(() => !document.getElementById("kfA").hidden && document.getElementById("kfO").hidden && document.activeElement.id !== "key-anthropic"), "v4 panel: API mode shows the Anthropic key field (key already set, so no focus jump)");
  await page.locator("#ai-none").click(); await sleep(200);
  ok(await ev(() => document.getElementById("keyForm").hidden && __soul.S.ai === "none"), "v4 panel: No AI hides the key fields");
  await ev(() => { __soul.S.voice = null; __soul.aiAsk("timer 5 minutes", "home"); }); await sleep(1200);
  ok(await ev(() => __soul.S.tm.cd.total === 300 && /No AI · on the device/.test(document.querySelector("#cards .card:last-child").textContent)), "v4 No AI: the device rules start a 5 min timer");
  await page.locator("#ai-claude").click(); await sleep(200);
  ok(await ev(() => __soul.S.ai === "claude" && /live/.test(document.getElementById("aiStatus").textContent)), "v4 back to Claude, status says live");
  await page.locator(".panel").screenshot({ path: OUT + "soulos4-panel.png" });
  await ev(() => { __soul.S.voice = null; __soul.go("home", "down"); }); await settle();

  // ---------- Settings › My SOUL + rebirth
  await ev(() => document.getElementById("pebble").scrollIntoView({ block: "center" })); await sleep(150); B = await box();   // the panel clicks scrolled the page
  await ev(() => __soul.go("settings", "left")); await settle();
  await tapEl(card('[data-act="mysoul"]')); await settle();
  const ms = await ev(() => ({ v: __soul.S.view, txt: document.querySelector("#cards .card:last-child").textContent, name: __soul.BIRTH.roll.design.name, chip: __soul.BIRTH.chip }));
  ok(ms.v === "mysoul" && ms.txt.includes(ms.name) && /\/ 120/.test(ms.txt) && /1 in/.test(ms.txt), `v4 My SOUL shows design, rarity, number and odds (${ms.name})`);
  await shot("mysoul");
  await tapEl(card('[data-act="rebirth"]')); await sleep(600);
  const rb = await ev(() => ({ chip: __soul.BIRTH.chip, name: __soul.BIRTH.roll.design.name, d: __soul.soul.design.id, rid: __soul.BIRTH.roll.design.id, txt: document.querySelector("#cards .card:last-child").textContent, ls: localStorage.getItem("soulos-chip") }));
  ok(rb.chip !== ms.chip && rb.d === rb.rid && rb.txt.includes(rb.name) && rb.ls === rb.chip, `v4 rebirth (demo): new chip → new roll → eyes swap (${ms.name} → ${rb.name})`);
  await shot("mysoul-reborn");
  // consistent back: the side button goes up one level
  await tapEl("#side"); await settle();
  ok(await ev(() => __soul.S.view === "settings"), "v4 side button on a sub-screen = back one level");
  // large text
  await tapEl(card('[data-act="bigtext"]')); await sleep(300);
  ok(await ev(() => document.getElementById("screen").classList.contains("big") && localStorage.getItem("soulos-big") === "1"), "v4 Settings › Text size: large");
  await shot("bigtext");
  await tapEl(card('[data-act="bigtext"]')); await sleep(200);
  // swipe down = back as well; the keyboard closes with a pull on its field
  await ev(() => __soul.go("aimode", "left")); await settle();
  { const [a, b] = pt(233, 200), [c, d] = pt(233, 360); await page.mouse.move(a, b); await page.mouse.down(); await page.mouse.move(c, d, { steps: 8 }); await page.mouse.up(); } await settle();
  ok(await ev(() => __soul.S.view === "settings"), "v4 swipe ↓ on a sub-screen = back");
  await ev(() => __soul.go("notes", "left")); await settle(); await tapEl(card('[data-act="note-add"]')); await sleep(300);
  await page.keyboard.type("draft");
  { const [a, b] = pt(233, 70), [c, d] = pt(233, 150); await page.mouse.move(a, b); await page.mouse.down(); await page.mouse.move(c, d, { steps: 6 }); await page.mouse.up(); } await sleep(300);
  ok(await ev(() => !__soul.S.kb && /^draft$/i.test(__soul.S.drafts.note || "")), `v4 pull the keyboard's field down = back, the draft is kept (${await ev(() => JSON.stringify([!!__soul.S.kb, __soul.S.drafts.note, __soul.S.view]))})`);

  // ---------- motion budget: navigation settles within ~250 ms
  await ev(() => __soul.go("home", "down")); await sleep(700);
  const ms2 = await ev(() => new Promise(res => { __soul.go("weather", "left"); const el = document.querySelector("#cards .card:last-child"), t0 = performance.now();
    const f = () => { const s = el._st; if (Math.abs(s.x) < 4 && s.o > 0.97 && Math.abs(s.s - 1) < 0.01) res(performance.now() - t0); else if (performance.now() - t0 > 2000) res(9999); else requestAnimationFrame(f); }; requestAnimationFrame(f); }));
  ok(ms2 <= 260, `v4 a screen change lands in ${Math.round(ms2)} ms (within 4 px, 97 % opacity; budget 250 ms + one frame)`);
  const pillT = await ev(() => parseFloat(getComputedStyle(document.getElementById("pill")).transitionDuration));
  ok(pillT <= 0.25, `v4 notification slides in ${pillT}s`);

  // ---------- a fresh view without the capability: Claude mode says so, kindly
  const ctx2 = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await ctx2.addInitScript(BORN);
  const p2 = await ctx2.newPage(); await fonts(p2);
  p2.on("pageerror", e => errs.push("pageerror(390): " + e.message));
  await p2.goto(FILE, { waitUntil: "load" }); await sleep(900);
  await p2.evaluate(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.setAi("claude"); __soul.aiAsk("what's the meaning of life?", "home"); }); await sleep(1500);
  ok(await p2.evaluate(() => /isn.t connected in this view/.test(document.querySelector("#cards .card:last-child").textContent) && __soul.soul.expression === "confused"), "v4 no capability (outside claude.ai) → confused + “Claude isn't connected in this view”");
  await p2.locator("#pebble").screenshot({ path: OUT + "soulos4-nocap-390.png" });
  ok(await p2.evaluate(() => /isn.t connected/.test(document.getElementById("aiStatus").textContent)), "v4 panel status explains where Claude works");
  const hs = await p2.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  ok(hs[0] <= hs[1], `v4 390 px: no horizontal scroll (${hs[0]} ≤ ${hs[1]})`);
  await p2.screenshot({ path: OUT + "soulos4-page-390.png", fullPage: true });
  await ctx2.close();
  ok(errs.length === 0, `v4 zero console/page errors ${errs.join(" | ")}`);
  await browser.close();
}
/* one real call from the browser to api.anthropic.com with a fake key: proves the request shape is accepted and the 401 path works */
async function live() {
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch(proxy ? { proxy: { server: proxy, bypass: process.env.NO_PROXY || process.env.no_proxy || "" } } : {});
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true }); await ctx.addInitScript(BORN);
  const page = await ctx.newPage(); await fonts(page);
  await page.goto(FILE, { waitUntil: "load" }); await sleep(800);
  await page.evaluate(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.setKey("anthropic", "sk-ant-api03-NOT-A-REAL-KEY-000000000000"); __soul.setAi("api"); __soul.aiAsk("hello", "home"); });
  let txt = ""; for (let i = 0; i < 40; i++) { await sleep(500); txt = await page.evaluate(() => { const c = document.querySelector("#cards .card:last-child"); return __soul.S.voice && __soul.S.voice.phase === "answer" ? c.textContent : ""; }); if (txt) break; }
  ok(/API key was rejected/.test(txt), `live: the browser reached api.anthropic.com and a fake key came back 401 → “${(txt.match(/That API key was rejected\.|Can't reach the AI from this page\./) || [txt.slice(0, 60)])[0]}”`);
  await browser.close();
}

if (!only || only === "v4") await v4();
if (!only || only === "rm") await reduced();
if (!only || only === "390") await run(390, 844, "390", 2);
if (!only || only === "1440") await run(1440, 900, "1440", 1);
if (only === "live") await live();
console.log(results.join("\n"));
const fails = results.filter(r => r.startsWith("FAIL")).length;
console.log(`\n${results.length - fails} / ${results.length} passed`);
process.exitCode = fails ? 1 : 0;
