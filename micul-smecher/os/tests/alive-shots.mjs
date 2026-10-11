/* SoulOS Alive: device-size stills (480 x 480, round mask) of the key screens + one contact sheet, and zero console errors.
   node os/tests/alive-shots.mjs [outDir]   (default os/screenshots/alive; the sheet: os/screenshots/alive/soulos-alive-sheet.png)
   Needs a global `playwright` with Chromium, like soulos.test.mjs. The glass is shot at a device scale that makes it 480 px,
   then os/tools/alive_post.py masks every still to the round screen and builds the sheet. */
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import path from "path";
import os from "os";
import fs from "fs";
const root = execSync("npm root -g").toString().trim();
const { chromium } = await import(root + "/playwright/index.mjs");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const FILE = "file://" + path.resolve(HERE, "../index.html");
const OUT = path.resolve(process.argv[2] || path.join(HERE, "../screenshots/alive")) + "/"; fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(OUT)) if (/^\d\d-.*\.png$/.test(f)) fs.unlinkSync(OUT + f);
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
const results = [];
const ok = (c, m) => { results.push((c ? "PASS " : "FAIL ") + m); if (!c) console.log("FAIL", m); };
const browser = await chromium.launch();
/* the drawn glass is 440 x 0.825 = 363 CSS px wide: this scale makes it 480 device pixels */
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 480 / 363 });
await ctx.addInitScript(() => { try { localStorage.setItem("soulos-born", "1"); localStorage.setItem("soulos-chip", "C0FFEE123456"); localStorage.setItem("soulos-body", "silver"); } catch (e) {} });
await ctx.grantPermissions(["geolocation"]); await ctx.setGeolocation({ latitude: 44.4355, longitude: 26.1025 });
const page = await ctx.newPage(); await fonts(page);
const errs = [];
page.on("console", m => { if (m.type() === "error") errs.push("console: " + m.text()); });
page.on("pageerror", e => errs.push("pageerror: " + e.message));
await page.goto(FILE, { waitUntil: "load" }); await sleep(2400);
const ev = (f, a) => page.evaluate(f, a);
await ev(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.cancel("demo"); __soul.S.ai = "claude"; __soul.S.night = false; __soul.S.coach = false; document.getElementById("pebble").scrollIntoView({ block: "center" }); });
let n = 0;
const shot = async name => { n++; await page.locator("#glass").screenshot({ path: OUT + String(n).padStart(2, "0") + "-" + name + ".png" }); console.log("shot", n, name); };
const tapAt = async (x, y) => { const b = await page.locator("#screen").boundingBox(); await page.mouse.click(b.x + x / 466 * b.width, b.y + y / 466 * b.height); };
const card = s => "#cards .card:last-child " + s;
const tapEl = async sel => { await page.evaluate(s => { try { window.__soul && __soul.reveal && __soul.reveal(s); } catch (e) {} }, sel);   /* Alive: a list is a wheel; bring the row into focus first */
  const b = await page.locator(sel).first().boundingBox(); await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); };
const home = async () => { await ev(() => { __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); __soul.ALIVE.hide(); __soul.go("home", "fade"); document.getElementById("screen").classList.remove("peek"); __soul.cancel("peek"); }); await sleep(900); };

// 1 · standby: the eyes alone, full size, on pure black
await home(); await sleep(4400); await shot("standby");
const blackStandby = await ev(() => { const s = document.getElementById("screen"); return !s.classList.contains("ui") && getComputedStyle(document.getElementById("aura")).display === "none"; });
ok(blackStandby, "standby: no UI, no aura (pure black behind the eyes)");
// 2-4 · waking: the eyes glide up and shrink, the OS rises under them, they say hello
await tapAt(233, 330); await sleep(70); await shot("wake-1");
await sleep(140); await shot("wake-2");
await sleep(700); await shot("wake-3");
ok(await ev(() => __soul.soul.lay.k < 0.6 && __soul.soul.layS.cy < -0.1), "wake: the eyes glide up and shrink");
ok(await ev(() => document.getElementById("speech").classList.contains("on") && __soul.ALIVE.said.length > 0), `wake: a personality line under the eyes (${await ev(() => __soul.ALIVE.said)})`);
// 5-7 · the home dial: pebbles orbiting the eyes; turning; opening = a blink
await ev(() => { __soul.ALIVE.hide(); __soul.go("apps", "none"); }); await sleep(1400);
await ev(() => __soul.lnSpinTo("talk")); await sleep(1300); await shot("home-dial");
ok(await ev(() => document.querySelectorAll("#cards .card:last-child .ow.f").length === 1 && document.querySelector("#cards .card:last-child .ow.f").dataset.app === __soul.LN.near), "dial: exactly one focused pebble, the one in the middle of the arc");
await ev(() => { __soul.LN.tgt = Math.round(__soul.LN.rot) + 2; }); await sleep(110); await shot("dial-turning");
await sleep(1300);
/* the dial's speech sits in the inner disc; the fact and the name step aside */
await ev(() => __soul.ALIVE.say("bored", 4000, false)); await sleep(500); await shot("dial-speech");
ok(await ev(() => { const r = document.querySelector("#speech span").getBoundingClientRect(), sc = document.getElementById("screen").getBoundingClientRect(), f = 466 / sc.width;
  const pts = [[r.left, r.top], [r.right, r.top], [r.left, r.bottom], [r.right, r.bottom]].map(([x, y]) => Math.hypot((x - sc.left) * f - 233, (y - sc.top) * f - 233));
  return Math.max(...pts) < 140 && r.width * f <= 232 && document.querySelector("#cards .card:last-child .orb.saying") && getComputedStyle(document.querySelector("#cards .card:last-child .opv")).opacity === "0"; }), "dial speech: inside the inner disc (r < 140), ≤ 2 lines, the fact and name hidden");
await ev(() => __soul.ALIVE.hide()); await sleep(300);
await ev(() => __soul.lnSpinTo("weather")); await sleep(1300);
/* opening an app = a blink of the whole glass: the lids are slowed 10× for the still (the same animation, in slow motion) */
const lids = await ev(() => new Promise(r => { document.getElementById("lids")._slow = 10; __soul.openApp("weather", __soul.lnIcon("weather")); let m = 0, g = 0, k = 0;
  const f = () => { m = Math.max(m, __soul.soul.rig.closed()); g = Math.max(g, +document.getElementById("lids").dataset.c || 0); if (++k < 60 && (g < 0.7 || m < 0.6)) requestAnimationFrame(f); else r([m, g]); }; requestAnimationFrame(f); }));
/* the still: the lids half open again, the app already behind them (the animation is paused for the screenshot) */
await ev(() => new Promise(r => { const L = document.getElementById("lids"); let seen = false; const f = () => { const c = +L.dataset.c || 0; if (c > 0.97) seen = true; if (seen && c < 0.55) { L._freeze = true; r(); } else requestAnimationFrame(f); }; requestAnimationFrame(f); }));
await shot("open-blink");
await ev(() => { document.getElementById("lids")._freeze = false; __soul.S.lastAct = performance.now(); });   // the slowed still must not trip the idle timer
ok(lids[0] > 0.6, `opening an app: the eyes blink (lids ${lids[0].toFixed(2)})`);
ok(lids[1] > 0.6, `opening an app: two lids close over the whole glass, the app changes behind them (closed ${lids[1].toFixed(2)})`);
await sleep(3200); await ev(() => { document.getElementById("lids")._slow = 1; });
const aft = await ev(() => [__soul.S.view, document.querySelectorAll("#cards .card").length, +document.getElementById("lids").dataset.c || 0]);
ok(aft[0] === "weather" && aft[1] === 1 && aft[2] < 0.01, `after the blink: the app, alone, lids open (${aft.join(" · ")})`);
await sleep(1200);
// 8-9 · AI: hold the glass → listening; the answer
await ev(() => { __soul.go("home", "fade"); }); await sleep(600);
await ev(() => { __soul.S.voice = null; __soul.go("talk", "left"); }); await sleep(900); await shot("ai-talk");
await ev(() => { __soul.S.voice = { phase: "listen", kind: "ask", shown: "Wake me at 6:45 tomorrow", sim: false, p: { q: "Wake me at 6:45 tomorrow" } }; __soul.go("voice", "fade"); }); await sleep(900); await shot("ai-hold-listening");
await ev(() => __soul.aiAsk("Remind me at 5 to call the bank", "talk")); await sleep(260);
const thinking = await ev(() => [__soul.soul.expression, __soul.S.voice.phase, +__soul.soul.rig.closed().toFixed(2)]);
await shot("ai-thinking");
ok(thinking[0] === "thinking" && thinking[1] === "think", `thinking: the eyes squint while the answer comes (${thinking.join(" · ")})`);
await sleep(2600); await shot("ai-answer");
ok(await ev(() => ["approve", "happy"].includes(__soul.soul.expression) && /Reminder set/.test(document.querySelector("#cards .card:last-child").textContent)),
  `the demo answer did what was asked: a happy face, not sad (${await ev(() => __soul.soul.expression)}); "not connected" is a chip`);
// 10 · memory
await ev(() => { __soul.S.voice = null; __soul.go("memory", "left"); }); await sleep(900); await shot("memory");
// 11 · maps (the demo place, the phone's location)
await ev(() => { SoulApps.SA.m = null; __soul.go("maps", "fade"); }); await sleep(900);
try { await tapEl(card('[data-act="m-share"]')); await sleep(1700); } catch (e) {}
await shot("maps");
// 12-13 · settings, and Settings › My SOUL › Look (births and bodies)
await ev(() => __soul.go("settings", "left")); await sleep(900); await shot("settings");
await ev(() => __soul.go("mysoul", "left")); await sleep(900); await shot("my-soul");
await tapEl(card('[data-act="look"]')); await sleep(900);
ok(await ev(() => __soul.S.view === "look"), "My SOUL › Look opens the preview");
await tapEl(card('[data-act="look-next"]')); await sleep(500);
await tapEl(card('[data-act="look-body"][data-b="ember"]')); await sleep(900); await shot("look-preview");
ok(await ev(() => __soul.LOOK.i != null && __soul.LOOK.body === "ember" && getComputedStyle(document.getElementById("screen")).getPropertyValue("--b0").trim().toUpperCase() === "#D2622C"), "Look: preview another birth + the Ember body changes the palette");
await tapEl(card('[data-act="look-reset"]')); await sleep(600);
ok(await ev(() => __soul.LOOK.i == null && __soul.soul.design.id === __soul.BIRTH.roll.design.id), "Look: back to its own birth");
// 14 · a notification: a solid banner on the rim, the eyes widen
await home(); await ev(() => __soul.showPill({ incoming: true, who: "Ana", text: "Home for dinner at 6?", dur: 6000 })); await sleep(260); await shot("notification");
ok(await ev(() => __soul.soul.expression === "surprised"), `notification: the eyes widen (${await ev(() => __soul.soul.expression)})`);
await sleep(600);
// 15 · Claude needs you (approval sheet)
await ev(() => { __soul.S.pill = null; document.getElementById("pill").classList.remove("show"); __soul.S.claude.pending = { cmd: "npm run build" }; __soul.go("claude", "left"); }); await sleep(900); await shot("claude-approval");
/* the owner can see how to say yes or no: two big buttons, drawn (non-black pixels inside their boxes), and the shortcut hint inside the circle */
for (const sel of ['[data-act="c-allow"]', '[data-act="c-deny"]']) {
  const b = await page.locator(card(sel)).boundingBox(), png = (await page.screenshot({ clip: b })).toString("base64");
  const lit = await ev(async b64 => { const im = new Image(); im.src = "data:image/png;base64," + b64; await im.decode(); const c = document.createElement("canvas"); c.width = im.width; c.height = im.height; const x = c.getContext("2d"); x.drawImage(im, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 150) n++; return n / (d.length / 4); }, png);
  const sz = await ev(s => { const r = document.querySelector("#cards .card:last-child " + s).getBoundingClientRect(), f = 480 / document.getElementById("screen").getBoundingClientRect().width; return Math.min(r.width, r.height) * f; }, sel);
  ok(lit > 0.25 && sz >= 64, `Claude asks: ${sel} is visible (${Math.round(lit * 100)} % lit, ${sz.toFixed(0)} px)`);
}
ok(await ev(() => { const h = document.querySelector("#cards .card:last-child .askhint"), f = 480 / document.getElementById("screen").getBoundingClientRect().width; return h && parseFloat(getComputedStyle(h).fontSize) * f * (document.getElementById("screen").getBoundingClientRect().width / 466) >= 22 && /2×/.test(h.textContent); }), "Claude asks: the hold / 2× shortcut hint is ≥ 22 px inside the circle");
await tapEl(card('[data-act="c-allow"]')); await sleep(400);
ok(await ev(() => !__soul.S.claude.pending && __soul.soul.expression === "approve"), "Allow: approved, the eyes approve");
await ev(() => { __soul.S.claude.pending = null; });
// 16 · keyboard
await ev(() => __soul.go("notes", "left")); await sleep(700);
await tapEl(card('[data-act="note-add"]')); await sleep(500); await page.keyboard.type("Buy figs for Ana"); await sleep(300); await shot("keyboard");
await ev(() => { __soul.S.kb && (__soul.S.kb.text = ""); }); await page.locator("#side").click(); await sleep(500); await ev(() => { delete __soul.S.drafts.note; });
// 17 · a game (catch the star)
await ev(() => __soul.go("games", "left")); await sleep(800);
await ev(() => __soul.gameStart()); await sleep(1500); await shot("game");
await ev(() => { __soul.go("home", "fade"); }); await sleep(600);
// 18 · sad on an error, dizzy on a shake, sleepy at night
await ev(() => { __soul.go("apps", "none"); }); await sleep(900);
await ev(() => __soul.soul.react("error")); await sleep(450); await shot("dial-error-sad");
ok(await ev(() => __soul.soul.expression === "sad"), "an error: sad eyes");
await ev(() => { __soul.soul.st = "error"; __soul.soul.react("error"); }); await sleep(3200);
ok(await ev(() => __soul.soul.expression === "sad"), `a held error stays sad after the reaction (${await ev(() => __soul.soul.expression)})`);
await ev(() => { __soul.applyFaceState(); }); await sleep(600);
await ev(() => __soul.soul.react("dizzy")); await sleep(600); await shot("dial-shake-dizzy");
ok(await ev(() => __soul.soul.expression === "dizzy"), "a shake: dizzy eyes");
await home(); await ev(() => { __soul.S.night = true; __soul.applyFaceState(); }); await sleep(4300); await shot("standby-night-sleepy");
ok(await ev(() => __soul.soul.mood === "sleepy"), "at night the resting eyes are sleepy");
await ev(() => { __soul.S.night = false; });
// 19-21 · the same dial, three other births and bodies: every SOUL's OS is its own
for (const [i, body] of [[12, "midnight"], [57, "ember"], [101, "champagne"]]) {
  await ev(([i, body]) => { __soul.LOOK.i = i; __soul.LOOK.body = body; __soul.ALIVE.apply(); __soul.go("home", "fade"); }, [i, body]); await sleep(500);
  await ev(() => __soul.go("apps", "none")); await sleep(1200); await ev(() => __soul.lnSpinTo("weather")); await sleep(1400);
  const nm = await ev(() => __soul.soul.design.name.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
  await shot(`dial-${nm}-${body}`);
}
await ev(() => { __soul.LOOK.i = null; __soul.LOOK.body = "silver"; __soul.ALIVE.apply(); });
ok(errs.length === 0, "zero console / page errors " + errs.join(" | "));
await browser.close();
try { execSync(`python3 "${path.join(HERE, "../tools/alive_post.py")}" "${OUT}"`, { stdio: "inherit" }); } catch (e) { ok(false, "post: " + e.message); }
console.log(results.join("\n"));
console.log(`\n${results.filter(r => r.startsWith("PASS")).length} / ${results.length} passed`);
process.exit(results.some(r => r.startsWith("FAIL")) ? 1 : 0);
