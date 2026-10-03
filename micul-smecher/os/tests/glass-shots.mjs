/* SoulOS 5 "Glass": screenshots of the key screens + one contact sheet.
   node os/tests/glass-shots.mjs [outDir]   (default os/screenshots/glass; the sheet is built by os/tools/glass_sheet.py)
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
const OUT = path.resolve(process.argv[2] || path.join(HERE, "../screenshots/glass")) + "/"; fs.mkdirSync(OUT, { recursive: true });
const FONTS = path.join(os.tmpdir(), "soulos-fontcache"); fs.mkdirSync(FONTS, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function fonts(page) {
  await page.route(/fonts\.(googleapis|gstatic)\.com/, async route => {
    const url = route.request().url(), f = path.join(FONTS, Buffer.from(url).toString("base64url").slice(-120));
    try { if (!fs.existsSync(f)) execSync(`curl -sS --retry 5 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36" -o "${f}" "${url}"`); } catch (e) {}
    if (!fs.existsSync(f)) return route.fulfill({ status: 200, body: "", headers: { "content-type": "text/css" } });
    await route.fulfill({ status: 200, body: fs.readFileSync(f), headers: { "content-type": /googleapis/.test(url) ? "text/css" : "font/woff2", "access-control-allow-origin": "*" } });
  });
}
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage(); await fonts(page);
const errs = []; page.on("pageerror", e => errs.push(e.message));
const born = () => { try { localStorage.setItem("soulos-born", "1"); localStorage.setItem("soulos-chip", "C0FFEE123456"); } catch (e) {} };
await ctx.addInitScript(born);
await page.goto(FILE, { waitUntil: "load" }); await sleep(2400);
await page.evaluate(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.cancel("demo"); __soul.S.ai = "none"; document.getElementById("pebble").scrollIntoView({ block: "center" }); });
const ev = f => page.evaluate(f);
const shot = async name => { await page.locator("#glass").screenshot({ path: OUT + name + ".png" }); console.log("shot", name); };
const tapAt = async (x, y) => { const b = await page.locator("#screen").boundingBox(); await page.mouse.click(b.x + x / 466 * b.width, b.y + y / 466 * b.height); };
const settle = (ms = 1800) => sleep(ms);   // past the orbit hint (1.5 s) that follows every move

// 1 · standby: the eyes alone on black
await ev(() => { __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); __soul.go("home", "fade"); });
await sleep(5200);
await shot("01-standby-eyes-only");
// 2 · a touch peeks: clock capsule + status, then it fades back
await tapAt(233, 300); await settle(500); await shot("02-standby-touched");
// 3 · launcher
await ev(() => __soul.go("apps", "none")); await settle(1500); await shot("03-launcher");
// 4 · keyboard
await ev(() => __soul.go("notes", "left")); await settle();
await page.locator('#cards .card:last-child [data-act="note-add"]').click(); await settle(400);
await page.keyboard.type("Buy figs for Ana", { delay: 40 }); await settle(500); await shot("04-keyboard");
await ev(() => { __soul.S.kb && (__soul.S.kb.text = ""); }); await page.locator("#side").click(); await settle(400);
await ev(() => { delete __soul.S.drafts.note; });
// 5 · ask: listening, then the answer card
await ev(() => { __soul.go("talk", "left"); }); await settle();
await ev(() => { __soul.S.voice = { phase: "listen", kind: "ask", shown: "Wake me at 6:45 tomorrow", sim: false, p: { q: "Wake me at 6:45 tomorrow" } }; __soul.go("voice", "fade"); }); await settle(); await shot("05-ask-listening");
await ev(() => __soul.aiAsk("Remind me at 5 to call the bank", "home")); await settle(2600); await shot("06-answer");
// 7 · Claude approval: a glass sheet with an amber glow
await ev(() => { __soul.S.voice = null; __soul.go("home", "fade"); }); await settle(500);
await ev(() => __soul.claudeArrive()); await settle(700); await shot("07-claude-notification");
await ev(() => { __soul.go("claude", "left"); }); await settle(1200); await shot("08-claude-approval");
await ev(() => { __soul.S.claude.pending = null; __soul.go("home", "fade"); }); await settle(400);
// 9 · notification at home
await ev(() => __soul.showPill({ who: "Ana", text: "Dinner at 8? I'll bring figs", incoming: true, dur: 6000 })); await settle(700); await shot("09-notification");
await ev(() => { __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); });
// 10 · alarms: the list, the glass dial, ringing
await ev(() => __soul.go("alarms", "left")); await settle(); await shot("10-alarms");
await page.locator('#cards .card:last-child [data-act="al-add"]').click(); await settle(1000); await shot("11-alarm-dial");
await page.locator("#side").click(); await settle(600);
await ev(() => __soul.ringAlarm(__soul.S.alarms[0])); await settle(1200); await shot("12-alarm-ringing");
await ev(() => { __soul.S.ringing = null; __soul.go("home", "fade"); }); await settle(400);
// 13 · timer / focus
await ev(() => { __soul.S.focus.run = true; __soul.S.focus.left = 1112; __soul.go("focus", "left"); }); await settle(); await shot("13-focus");
await ev(() => { __soul.S.focus.run = false; __soul.S.focus.left = 1500; });
await ev(() => __soul.go("timer", "left")); await settle(); await shot("14-timer");
// 15 · settings
await ev(() => __soul.go("settings", "left")); await settle(); await shot("15-settings");
await ev(() => __soul.go("aimode", "left")); await settle(); await shot("16-settings-ai");
// 17 · Today + Control
await ev(() => __soul.go("today", "up")); await settle(1200); await shot("17-today");
await ev(() => { __soul.go("home", "fade"); }); await settle(400);
await ev(() => __soul.ccOpen()); await settle(900); await shot("18-control");
await ev(() => __soul.ccClose(true)); await settle(300);
// 19 · onboarding
await ev(() => __soul.bootStart()); await settle(3000); await shot("19-onboarding-born");
await ev(() => { __soul.BOOT.step = "bname"; __soul.go("bname", "left"); }); await settle(1000); await shot("20-onboarding-name");
await ev(() => { __soul.BOOT.step = "bai"; __soul.go("bai", "left"); }); await settle(1000); await shot("21-onboarding-brain");
await ev(() => { __soul.BOOT.step = "bhold"; __soul.go("bhold", "left"); }); await settle(1000); await shot("22-onboarding-hold");
await ev(() => __soul.bootDone(true)); await settle(400);
if (errs.length) console.log("page errors:", errs.join(" | "));
await browser.close();
