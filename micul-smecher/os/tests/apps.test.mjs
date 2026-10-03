/* SoulOS apps on the web (os/APPS.md, docs/11-MAPS.md): node os/tests/apps.test.mjs [outDir]
   Every app opens from the orbit, does its core thing, goes back with the side button / a swipe down, and the page logs no
   errors. Stills go to os/screenshots/apps/NN-name.png (+ the contact sheet via os/tools/glass_sheet.py).
   Needs a global `playwright` with Chromium, like soulos.test.mjs. The map is the synthetic demo city that SOUL Cloud's tests
   use (ai/tools/gen_app_fixtures.py), the phone's location is Playwright's geolocation. */
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import path from "path";
import os from "os";
import fs from "fs";
const root = execSync("npm root -g").toString().trim();
const { chromium } = await import(root + "/playwright/index.mjs");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const FILE = "file://" + path.resolve(HERE, "../index.html");
const OUT = path.resolve(process.argv[2] || path.join(HERE, "../screenshots/apps")) + "/"; fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) if (/^\d\d-.*\.png$/.test(f)) fs.unlinkSync(OUT + f);
const FONTS = path.join(os.tmpdir(), "soulos-fontcache"); fs.mkdirSync(FONTS, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const ok = (cond, msg) => { results.push((cond ? "PASS " : "FAIL ") + msg); if (!cond) console.log("FAIL", msg); };
async function fonts(page) {
  await page.route(/fonts\.(googleapis|gstatic)\.com/, async route => {
    const url = route.request().url(), f = path.join(FONTS, Buffer.from(url).toString("base64url").slice(-120));
    try { if (!fs.existsSync(f)) execSync(`curl -sS --retry 5 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36" -o "${f}" "${url}"`); } catch (e) {}
    if (!fs.existsSync(f)) return route.fulfill({ status: 200, body: "", headers: { "content-type": "text/css" } });
    await route.fulfill({ status: 200, body: fs.readFileSync(f), headers: { "content-type": /googleapis/.test(url) ? "text/css" : "font/woff2", "access-control-allow-origin": "*" } });
  });
}
const LAT = 44.4355, LON = 26.1025;   // the fixture's demo place (kFixLat / kFixLon)
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2, geolocation: { latitude: LAT + 0.0004, longitude: LON - 0.0003, accuracy: 18 }, permissions: ["geolocation"] });
await ctx.addInitScript(() => { window.card = s => "#cards .card:last-child " + s; try { localStorage.setItem("soulos-born", "1"); localStorage.removeItem("soulos-orbit"); localStorage.removeItem("soulos-habits"); } catch (e) {} });
const page = await ctx.newPage(); await fonts(page);
const errs = [];
page.on("console", m => { if (m.type() === "error" && !/Failed to load resource|ERR_CERT/.test(m.text())) errs.push("console: " + m.text()); });
page.on("pageerror", e => errs.push("pageerror: " + e.message));
await page.goto(FILE, { waitUntil: "load" }); await sleep(2400);
await page.evaluate(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.cancel("demo"); __soul.S.ai = "none"; __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); document.getElementById("pebble").scrollIntoView({ block: "center" }); });
const ev = (f, a) => page.evaluate(f, a);
let n = 0;
const shot = async name => { n++; await page.locator("#glass").screenshot({ path: OUT + String(n).padStart(2, "0") + "-" + name + ".png" }); };
const box = () => page.locator("#screen").boundingBox();
const pt = async (x, y) => { const b = await box(); return [b.x + x / 466 * b.width, b.y + y / 466 * b.height]; };
const tapAt = async (x, y) => { const [a, b] = await pt(x, y); await page.mouse.move(a, b); await page.mouse.down(); await sleep(40); await page.mouse.up(); };
const drag = async (x0, y0, x1, y1, steps = 10) => { const [a, b] = await pt(x0, y0); await page.mouse.move(a, b); await page.mouse.down();
  for (let i = 1; i <= steps; i++) { const [c, d] = await pt(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps); await page.mouse.move(c, d); await sleep(16); } await page.mouse.up(); };
const card = sel => `#cards .card:last-child ${sel}`;
const tapEl = async sel => { const b = await page.locator(sel).first().boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down(); await sleep(40); await page.mouse.up(); };
const view = () => ev(() => __soul.S.view);
const settle = (ms = 900) => sleep(ms);
const quiet = () => ev(() => { __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); });
const open = async v => { await ev(v => { __soul.go("home", "none"); __soul.openApp(v); }, v); await settle(2000); await quiet(); };
const backSide = async () => { await tapEl("#side"); await settle(800); };
const swipeDown = async () => { await drag(233, 190, 233, 370, 8); await settle(800); };
const cardText = () => ev(() => document.querySelector("#cards .card:last-child").textContent);

// ---- the orbit holds every app, and two gestures reach the top ones
const APPS = ["maps", "weather", "calendar", "breathe", "habits", "stopwatch", "worldclock", "convert", "findphone", "device", "games", "music", "focus", "timer", "today", "notes", "alarms", "reminders", "settings"];
const orb = await ev(() => __soul.ORB.slice());
ok(APPS.every(v => orb.includes(v)), `the orbit holds every app (${orb.length}: ${orb.join(" ")})`);
ok(orb.indexOf("maps") <= 2 && orb.indexOf("weather") <= 3, `Maps and Weather sit next to Talk: swipe → then one turn (${orb.slice(0, 4).join(", ")})`);
await ev(() => __soul.go("apps", "none")); await settle(1500);
await ev(() => __soul.lnSpinTo("maps")); await settle(1300); await quiet();
await shot("launcher-maps");
{ const pos = await ev(() => __soul.lnIcon("maps")._pos); await tapAt(pos[0], pos[1]); } await settle(1500);
ok((await view()) === "maps", `tap the word: Maps opens (${await view()})`);

// ---- Maps: where are you? → the phone shares → pan, rim zoom → where to? → preview → steps → send to phone → end
await ev(() => { SoulApps.SA.m = null; __soul.go("maps", "fade"); }); await settle(); await quiet();
ok(/Where are you\?/.test(await cardText()), "maps without a fix asks where you are (no GPS on SOUL)");
await shot("maps-where-are-you");
await tapEl(card('[data-act="m-share"]')); await settle(1600);
const fx = await ev(() => SoulApps.M().fix);
ok(fx && fx.src === "phone" && Math.abs(fx.lat - 44.4359) < 0.001, `"Share my location" takes the phone's position (${JSON.stringify(fx)})`);
ok(await ev(() => { const c = document.querySelector(card(".mapcv")); if (!c) return false; const d = c.getContext("2d").getImageData(300, 300, 340, 340).data; let lit = 0; for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 160) lit++; return lit > 2000; }), "the map is drawn (roads on the canvas)");
await quiet(); await shot("maps-here");
{ const c0 = await ev(() => SoulApps.M().cx); await drag(240, 260, 160, 230, 10); await settle(300);
  ok(Math.abs((await ev(() => SoulApps.M().cx)) - c0) > 40 && (await view()) === "maps", "drag pans the map"); }
{ const z0 = await ev(() => SoulApps.M().z + Math.log2(SoulApps.M().s)); const P = []; for (let a = 20; a <= 80; a += 6) P.push([233 + 205 * Math.cos(a * Math.PI / 180), 233 + 205 * Math.sin(a * Math.PI / 180)]);
  let [x, y] = await pt(...P[0]); await page.mouse.move(x, y); await page.mouse.down(); for (const p of P.slice(1)) { [x, y] = await pt(...p); await page.mouse.move(x, y); await sleep(16); } await page.mouse.up(); await settle(300);
  const z1 = await ev(() => SoulApps.M().z + Math.log2(SoulApps.M().s));
  ok(Math.abs(z1 - z0) > 0.5, `dragging along the rim zooms (${z0.toFixed(2)} → ${z1.toFixed(2)})`); }
await tapEl(card('[data-act="m-center"]')); await settle(400);
await tapEl(card('[data-act="m-to"]')); await settle(500);
ok(await ev(() => !!__soul.S.kb), "Where to? opens the keyboard");
await page.keyboard.type("Ateneul Roman", { delay: 20 }); await settle(200);
await page.keyboard.press("Enter"); await settle(1100); await quiet();
const pv = await ev(() => ({ p: SoulApps.M().preview, to: SoulApps.ROUTE && SoulApps.ROUTE.to, steps: SoulApps.ROUTE && SoulApps.ROUTE.steps.length }));
ok(pv.p && pv.to && pv.steps >= 3, `route preview: ${pv.to}, ${pv.steps} steps`);
ok(/km · \d+ min/.test(await cardText()), "the preview says distance · minutes · arrival");
await shot("maps-route-preview");
await tapEl(card('[data-act="m-start"]')); await settle(900); await quiet();
ok(await ev(() => SoulApps.M().nav && SoulApps.M().step === 1), "Start: navigation begins at the first turn");
const card1 = await cardText();
ok(/\d+ m|km/.test(card1) && /(left|right|Straight|Slight|Sharp)/i.test(card1), `the step card: distance + the turn (${card1.slice(0, 60)})`);
await shot("maps-next-turn");
const ang = await ev(() => [1, 2, 3].map(i => Math.round(SoulApps.turnAngle(i))));
ok(ang.some(a => Math.abs(a) > 30), `the arrow turns relative to the line walked, no compass (${ang.join("°, ")}°)`);
await tapEl(card('[data-act="m-next"]')); await settle(500);
ok(await ev(() => SoulApps.M().step === 2), "tap the card at the turn → the next step");
await tapEl(card('[data-act="m-phone"]')); await settle(600); await quiet();
const glink = await ev(() => { const a = document.querySelector(card('[data-live="glink"]')); return a && a.href; });
ok(/^https:\/\/www\.google\.com\/maps\/dir\/\?api=1&destination=44\.\d+,26\.\d+&travelmode=walking$/.test(glink || ""), `Send to phone: a Google Maps link (${glink})`);
await shot("maps-send-to-phone");
await swipeDown();
ok((await view()) === "maps" && await ev(() => !SoulApps.M().send && SoulApps.M().nav), "swipe down closes the phone sheet, navigation goes on");
for (let i = 0; i < 8; i++) { await tapEl(card('[data-act="m-next"]')); await settle(250); }
ok(/You're there/.test(await cardText()), "the last step: You're there");
await tapEl(card('[data-act="m-end"]')); await settle(500);
ok(await ev(() => !SoulApps.M().nav && !SoulApps.M().preview), "End: back to the map");
// "Take me to…" by voice/typing: the navigate action (here the on-device rules: no AI configured)
await ev(() => { __soul.go("home", "none"); __soul.aiAsk("Take me to Ateneul Român", "home"); }); await settle(4200); await quiet();
ok((await view()) === "maps" && await ev(() => SoulApps.M().preview), `"Take me to Ateneul Român" → the navigate action opens the route (${await view()})`);
ok(await ev(() => { const a = __soul.validAction({ type: "navigate", to: "Gara de Nord", mode: "bike" }), b = __soul.validAction({ type: "navigate", to: "x", mode: "plane" }); return a && a.mode === "bike" && b === null; }), "navigate is validated like every action (mode walk|bike|car)");
await ev(() => { SoulApps.M().preview = false; });
await backSide();
ok((await view()) !== "maps", `side button: back from Maps (${await view()})`);

// ---- Weather (the cloud's Open-Meteo shape on the device; the web keeps its demo days)
await open("weather"); ok((await view()) === "weather", "Weather opens"); await shot("weather"); await swipeDown(); ok((await view()) !== "weather", "swipe down: back from Weather");

// ---- Calendar: the agenda from the cloud's ICS parser; a row opens the event, swipe down = back to the list
await open("calendar");
const rows = await ev(() => document.querySelectorAll(card('[data-act="cal-open"]')).length);
ok(rows >= 2, `Calendar: the agenda lists the next events (${rows})`);
await shot("calendar");
await tapEl(card('[data-act="cal-open"]')); await settle(500);
ok(await ev(() => SoulApps.SA.cal.sel === 0), "tap a row: the event"); await shot("calendar-event");
await swipeDown(); ok((await view()) === "calendar" && await ev(() => SoulApps.SA.cal.sel === -1), "swipe down: back to the list");
await swipeDown(); ok((await view()) !== "calendar", "swipe down again: out of Calendar");

// ---- Music (focus sounds), Focus, Timer/Stopwatch
await open("music"); ok((await view()) === "music", "Music opens"); await shot("music"); await backSide();
await open("focus"); ok((await view()) === "focus", "Focus opens"); await shot("focus-pomodoro"); await backSide();
await open("stopwatch"); ok((await view()) === "timer" && await ev(() => __soul.S.tm.mode === "sw"), "Stopwatch opens the timer in stopwatch mode"); await shot("stopwatch"); await backSide();

// ---- Breathe: the eyes breathe, on pure black (a face moment: no aura)
await open("breathe"); await shot("breathe");
await tapAt(233, 220); await settle(1800);
ok(await ev(() => SoulApps.SA.br.on), "Breathe: tap the eyes to begin");
ok(await ev(() => !document.getElementById("screen").classList.contains("aura")), "breathing is a face moment: black behind the eyes, no aura");
const k1 = await ev(() => __soul.soul.lay.k); await sleep(1500); const k2 = await ev(() => __soul.soul.lay.k);
ok(Math.abs(k2 - k1) > 0.02, `the eyes grow and shrink with the breath (${k1.toFixed(2)} → ${k2.toFixed(2)})`);
await shot("breathe-in");
await tapAt(233, 220); await settle(400); await backSide(); ok((await view()) !== "breathe", "back from Breathe");

// ---- Habits: tap = done today (kept in this browser)
await open("habits");
await tapEl(card('[data-act="hab"]')); await settle(400);
ok(await ev(() => JSON.parse(localStorage.getItem("soulos-habits"))[0].days.length === 1), "Habits: tap = done today, saved");
await shot("habits"); await backSide();

// ---- World clock, Convert (offline units + ECB rates), Find my phone, Device
await open("worldclock");
const c0 = await ev(() => SoulApps.SA.clocks[0]); await tapEl(card('[data-act="wc"]')); await settle(300);
ok((await ev(() => SoulApps.SA.clocks[0])) !== c0, "World clock: tap a row → another city"); await shot("world-clock"); await backSide();
await open("convert");
ok(await ev(() => Math.abs(SoulApps.convert(0, 0, 5, 1) - 3.28084) < 1e-4 && Math.abs(SoulApps.convert(2, 0, 1, 100) - 212) < 1e-9), "Convert: 1 m = 3.28084 ft, 100 °C = 212 °F (offline)");
for (let i = 0; i < 5; i++) { await tapEl(card('[data-act="cv-q"]')); await settle(150); }
const cur = await cardText();
ok(/EUR/.test(cur) && /ECB rates of 20\d\d-\d\d-\d\d/.test(cur), "Convert: currency with the ECB reference rates (cloud)");
await shot("convert-currency"); await backSide();
await open("findphone"); await tapEl(card('[data-act="fp-ring"]')); await settle(500); await quiet();
ok(/Ringing/.test(await cardText()), "Find my phone: rings it (/me/where)"); await shot("find-my-phone");
await tapEl(card('[data-act="fp-found"]')); await settle(300); await backSide();
await open("device"); ok(/%/.test(await cardText()) && /SoulOS/.test(await cardText()), "Device: battery + storage"); await shot("device"); await backSide();

// ---- Games: the menu, tilt ball, rhythm, eye memory, game over
await open("games");
ok(await ev(() => document.querySelectorAll(card('[data-act^="g-"], [data-act="game-start"]')).length === 4), "Games: four games in the menu");
await shot("games");
await tapEl(card('[data-act="g-tilt"]')); await settle(300);
{ const [a, b] = await pt(330, 233); await page.mouse.move(a, b); await page.mouse.down(); await sleep(900); await page.mouse.up(); }
const tb = await ev(() => SoulApps.SA.game);
ok(tb.kind === "tilt" && tb.run && Math.hypot(tb.x, tb.y) > 20, `Tilt ball: the ball rolls toward the finger (x ${tb.x.toFixed(0)})`);
await shot("game-tilt-ball");
await drag(233, 70, 233, 250, 8); await settle(600); ok(await ev(() => !SoulApps.SA.game) && (await view()) === "games", "pull down from the top edge: out of the game, back to the menu");
await tapEl(card('[data-act="g-rhy"]')); await settle(2600);
ok(await ev(() => !document.getElementById("screen").classList.contains("aura")), "Rhythm: the eyes on black");
await tapAt(233, 233); await settle(200);
await shot("game-rhythm");
await ev(() => { const G = SoulApps.SA.game; G.t = G.beats[G.beats.length - 1].t + 2; }); await settle(300);
ok(await ev(() => SoulApps.SA.game.over), "Rhythm ends after the last beat"); await shot("game-over");
await tapEl(card('[data-act="g-menu"]')); await settle(300);
await tapEl(card('[data-act="g-mem"]')); await settle(1300);
const seq = await ev(() => SoulApps.SA.game.seq.slice());
const spot = [[233, 60], [406, 233], [233, 406], [60, 233]];
await ev(() => { SoulApps.SA.game.phase = "in"; SoulApps.SA.game.lit = -1; });
await tapAt(...spot[seq[0]]); await settle(300);
ok(await ev(() => SoulApps.SA.game.seq.length === 2 && SoulApps.SA.game.score === 1), "Eye memory: repeat where the eyes looked → the next round");
await settle(400); await shot("game-eye-memory");
await drag(233, 70, 233, 250, 8); await settle(500); await backSide();

// ---- Today stack: next event + habits cards
await open("today"); const wg = await ev(() => document.querySelector("#cards .card:last-child").innerText);
ok((await view()) === "today", "Today opens"); await shot("today"); await backSide();

// ---- Settings › Apps: hide and reorder the orbit (saved), Settings can't be hidden
await open("settings"); await tapEl(card('[data-act="appsset"]')); await settle(900); await quiet();
ok((await view()) === "appsset", "Settings › Apps opens");
await shot("settings-apps");
const before = await ev(() => __soul.ORB.slice());
await tapEl(card('[data-act="as-tog"][data-v="maps"]')); await settle(300);
ok(await ev(() => !__soul.ORB.includes("maps") && JSON.parse(localStorage.getItem("soulos-orbit")).hidden.includes("maps")), "hide Maps: off the orbit, saved");
await tapEl(card('[data-act="as-tog"][data-v="maps"]')); await settle(300);
await tapEl(card('[data-act="as-up"][data-v="weather"]')); await settle(300);
const after = await ev(() => __soul.ORB.slice());
ok(after.indexOf("weather") === before.indexOf("weather") - 1 && after.includes("maps"), `move Weather up the orbit (${after.slice(0, 4).join(", ")})`);
await tapEl(card('[data-act="as-up"][data-v="weather"]')).catch(() => {}); await settle(200);
await ev(() => { localStorage.removeItem("soulos-orbit"); });
await backSide(); ok((await view()) === "settings", "back from Settings › Apps = Settings");

// ---- quick replies stay in the answer flow; the control centre
await ev(() => __soul.ccOpen()); await settle(700); await shot("control"); await ev(() => __soul.ccClose()); await settle(500);

// ---- standby is still the eyes alone
await ev(() => __soul.go("home", "fade")); await settle(5200);
ok(await ev(() => { const s = document.getElementById("screen"); return !s.classList.contains("ui") && !s.classList.contains("aura"); }), "standby: the eyes alone, no glass, no aura");
await shot("standby-eyes-only");

// ---- Romanian too
await ev(() => { document.getElementById("lang-ro").click(); }); await settle(300);
await open("maps"); ok(/Unde mergem|oraș demo|telefon/.test(await cardText()), `RO: Maps speaks Romanian (${(await cardText()).replace(/\s+/g, " ").slice(0, 60)})`);
const ro = await ev(() => [__soul.ORB.includes("maps"), document.querySelector("#cards .card:last-child").textContent]);
ok(!/Where to\?|Share my location/.test(ro[1]), "RO: no English left on the Maps screen");
await ev(() => { document.getElementById("lang-en").click(); }); await settle(200);

ok(errs.length === 0, `zero console/page errors ${errs.join(" | ")}`);
await browser.close();
try { execSync(`python3 "${path.join(HERE, "../tools/glass_sheet.py")}" "${OUT}" "${OUT}soulos-apps-sheet-web.png" --title "SoulOS apps on the web (os/index.html)" --sub "Maps, Calendar, Breathe, Habits, World clock, Convert, Find my phone, Device, Games and Settings > Apps. Behind the eyes always black." --cols 6`, { stdio: "inherit" }); } catch (e) { ok(false, "contact sheet: " + e.message); }
console.log(results.join("\n"));
console.log(`\n${results.filter(r => r.startsWith("PASS")).length} / ${results.length} passed`);
process.exit(results.some(r => r.startsWith("FAIL")) ? 1 : 0);
