/* SOUL Memory on the web SoulOS (docs/10-SOUL-MEMORY.md): node os/tests/memory.test.mjs
   The AI is a mocked claude.ai `sample` capability; the memory lives in localStorage "soulos-memory". */
import { execSync } from "child_process";
import { fileURLToPath } from "url";
import path from "path";
const root = execSync("npm root -g").toString().trim();
const { chromium } = await import(root + "/playwright/index.mjs");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const FILE = "file://" + path.resolve(HERE, "../index.html");
const results = [];
const ok = (cond, msg) => { results.push((cond ? "PASS " : "FAIL ") + msg); if (!cond) console.log("FAIL", msg); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

function mock() {
  try { localStorage.setItem("soulos-born", "1"); } catch (e) {}
  window.__calls = []; window.__nextReply = null;
  const sample = async (input, opts = {}) => {
    window.__calls.push({ input });
    await new Promise(r => setTimeout(r, 120));
    const text = window.__nextReply || JSON.stringify({ say: "Hi!", actions: [] }); window.__nextReply = null;
    if (opts.onText) opts.onText({ text, delta: text });
    return { text, truncated: false, modelTierApplied: "quick" };
  };
  window.claude = { use: async name => name === "sample" ? sample : null };
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
await ctx.addInitScript(mock);
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(e.message));
const ev = (f, a) => page.evaluate(f, a);
await page.goto(FILE, { waitUntil: "load" }); await sleep(1500);
await ev(() => { __soul.cancel("msg"); __soul.cancel("claude"); __soul.setAi("claude"); try { localStorage.removeItem("soulos-memory"); } catch (e) {} SoulMem.clear(); });
const answer = () => ev(() => { const c = document.querySelector("#cards .card:last-child"); return c ? c.textContent : ""; });
const ask = async (t, ms = 1300) => { await ev(q => __soul.aiAsk(q, "home"), t); await sleep(ms); };

// "remember that…" is kept on the device, at once, with an undo pill; no AI call
const calls0 = await ev(() => window.__calls.length);
await ask("remember that my sister is Ana");
ok(await ev(() => SoulMem.size() === 1 && SoulMem.facts[0].subject === "Ana" && SoulMem.facts[0].pinned), "memory: “remember that…” keeps the fact on the device (subject Ana, pinned)");
ok((await ev(() => window.__calls.length)) === calls0, "memory: no AI round trip for “remember that…”");
ok(/Remembered: My sister is Ana/.test(await answer()), "memory: SOUL says “Remembered: My sister is Ana”");
ok(await ev(() => __soul.S.pill && __soul.S.pill.act === "memundo"), "memory: the pill offers undo");
await ev(() => SoulMem.tapUndo());
ok(await ev(() => SoulMem.size() === 0), "memory: undo takes it back");
await ask("remember that my sister is Ana");
// every AI request carries the block; the AI's memory.remember is validated and kept
await ev(() => { window.__nextReply = JSON.stringify({ say: "A green scarf?", actions: [{ type: "memory.remember", text: "Ana likes green scarves", kind: "preference", importance: 3 }, { type: "memory.remember", text: "her PIN is 1234" }, { type: "timer.start", minutes: 5 }] }); });
await ask("gift idea for my sister?", 1600);
const sent = await ev(() => window.__calls[window.__calls.length - 1].input[0].content);
ok(/What SOUL knows about you/.test(sent) && /My sister is Ana/.test(sent) && /memory\.remember/.test(sent), "memory: the AI request carries “What SOUL knows about you” and the two memory actions");
ok(await ev(() => SoulMem.size() === 2 && SoulMem.facts.some(f => f.text === "Ana likes green scarves" && f.source === "ai") && !SoulMem.facts.some(f => /PIN/.test(f.text))), "memory: the AI's fact is kept, its secret refused");
ok(await ev(() => __soul.S.tm.cd.run), "memory: memory ops do not use up the three actions (the timer still ran)");
const pr = await ev(() => __soul.parseReply(JSON.stringify({ say: "x", actions: [{ type: "memory.forget", text: "a" }, { type: "memory.remember", text: "ok", extra: 1 }] })));
ok(pr.memory.length === 0 && pr.rejected === 2, "memory: bad memory ops are dropped and counted");
// offline: answered from memory, and simple facts said in passing are kept
await ev(() => __soul.setAi("none"));
await ask("Ana's birthday is May 12");
await ask("când e ziua Anei?");
ok(/12 May|12 mai/.test(await answer()), `memory: offline “când e ziua Anei?” → ${(await answer()).slice(0, 80)}`);
await ask("what's my wifi password?");
ok(/password manager|manager de parole/.test(await answer()), "memory: no secrets, ever");
await ask("forget everything");
ok(await ev(() => SoulMem.size() === 3), "memory: “forget everything” needs Settings and a hold");
// Settings › Memory: the real list, search, tap = forget, hold = wipe
await ev(() => __soul.go("memory", "left")); await sleep(500);
const lst = await ev(() => [...document.querySelectorAll('#cards .card:last-child [data-act="memdel"]')].map(e => e.textContent));
ok(lst.length === 3 && lst.some(t => /My sister is Ana/.test(t)), `memory: Settings › Memory lists the facts (${lst.length})`);
await ev(() => { __soul.S.memQ = "green"; __soul.go("settings", "fade"); }); await sleep(300); await ev(() => __soul.go("memory", "left")); await sleep(500);
ok((await ev(() => document.querySelectorAll('#cards .card:last-child [data-act="memdel"]').length)) === 1, "memory: search narrows the list");
await ev(() => { const el = document.querySelector('#cards .card:last-child [data-act="memdel"]'); __soul.act("memdel", el); }); await sleep(300);
ok(await ev(() => SoulMem.size() === 2 && !SoulMem.facts.some(f => /scarves/.test(f.text))), "memory: a tap on a fact forgets it");
ok(await ev(() => JSON.parse(localStorage.getItem("soulos-memory")).facts.length === 2), "memory: kept in localStorage (survives a reload)");
await ev(() => { __soul.S.memQ = ""; SoulMem.clear(); });
ok(await ev(() => SoulMem.size() === 0), "memory: wipe");
ok(errs.length === 0, `memory: zero page errors ${errs.join(" | ")}`);
await browser.close();
console.log(results.join("\n"));
const fails = results.filter(r => r.startsWith("FAIL")).length;
console.log(`\n${results.length - fails} / ${results.length} passed`);
process.exitCode = fails ? 1 : 0;
