#!/usr/bin/env node
// Builds the Shopify App Store listing kit for Expedo from the real demo UI.
//
//   node marketing/listing/build.mjs              # everything
//   node marketing/listing/build.mjs icon screens # only some parts: icon | screens | video | copy
//
// Env (all optional):
//   EXPEDO_APP_DIR   app to run (default: the frozen snapshot expedo-snap2 if present, else ../..)
//   PORT             demo server port (3302)
//   DB_FILE          demo database, recreated on every run (/tmp/claude-0/listing-demo.db)
//   CHROMIUM_PATH    Chromium for Playwright (/opt/pw-browsers/chromium-1194/chrome-linux/chrome)
//   PLAYWRIGHT_MODULE path to playwright's index.mjs if `import('playwright')` fails
//   BUILD_TMP        scratch dir for intermediate captures and video frames
//
// Nothing in the app is modified: the demo server runs with DEMO=1 on a throwaway database and is
// driven through its own UI and API (header X-Expedo-Request: 1). One state is staged directly in
// that throwaway database: a FAN Courier locality rejection, produced by the app's own
// localityError() on FAN's public locality list (the demo has no courier accounts). See LISTING.md.

import { spawn, execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync, readdirSync, statSync, copyFileSync } from 'node:fs';
import { dirname, join, resolve, basename } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import { COPY, LIMITS, SCREENSHOTS, MOBILE, FEATURE, INTEGRATIONS, PRICING } from './copy.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SNAP = '/tmp/claude-0/expedo-snap2/P/apps/expedo';
const APP_DIR = resolve(process.env.EXPEDO_APP_DIR || (existsSync(SNAP) ? SNAP : join(HERE, '..', '..')));
const PORT = Number(process.env.PORT || 3302);
const BASE = `http://localhost:${PORT}`;
const DB_FILE = process.env.DB_FILE || '/tmp/claude-0/listing-demo.db';
const TMP = process.env.BUILD_TMP || join(tmpdir(), 'expedo-listing-build');
const CHROMIUM = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const FONTS = join(HERE, 'assets', 'fonts');
const parts = new Set(process.argv.slice(2));
const want = (p) => parts.size === 0 || parts.has(p);

const BRAND = { cobalt: '#1f4bd8', cobaltDark: '#173aa8', yellow: '#f5c518', ink: '#16191f', soft: '#eef2fd', muted: '#4a5263' };

const log = (...a) => console.log('[listing]', ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ensureDir = (d) => { mkdirSync(d, { recursive: true }); return d; };

// ------------------------------------------------------------------ playwright
async function loadPlaywright() {
  try { return await import('playwright'); } catch {}
  const p = process.env.PLAYWRIGHT_MODULE || '/opt/node-tools/node_modules/playwright/index.mjs';
  return import(pathToFileURL(p).href);
}

// ------------------------------------------------------------------ fonts (Inter + JetBrains Mono, latin + latin-ext)
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36';
const GOOGLE_CSS = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap';

function ensureFonts() {
  ensureDir(FONTS);
  const cssFile = join(FONTS, 'google.css');
  if (!existsSync(cssFile)) execFileSync('curl', ['-sSf', '-A', UA, GOOGLE_CSS, '-o', cssFile]);
  const css = readFileSync(cssFile, 'utf8');
  const blocks = [...css.matchAll(/\/\* (\S+) \*\/\s*@font-face \{([\s\S]*?)\}/g)].filter(([, sub]) => sub === 'latin' || sub === 'latin-ext');
  let local = '';
  for (const [, sub, body] of blocks) {
    const url = body.match(/url\((.*?)\)/)[1];
    const file = basename(new URL(url).pathname);
    const dest = join(FONTS, file);
    if (!existsSync(dest)) execFileSync('curl', ['-sSf', '-A', UA, url, '-o', dest]);
    local += `/* ${sub} */\n@font-face {${body.replace(/url\((.*?)\)/, `url(${file})`)}}\n`;
  }
  writeFileSync(join(FONTS, 'fonts.css'), local);
  return local;
}

/** Serves Google Fonts requests of the app page from the local copies (no network, same files). */
async function routeFonts(context) {
  const localCss = readFileSync(join(FONTS, 'fonts.css'), 'utf8').replace(/url\(([^)]+)\)/g, 'url(https://fonts.gstatic.com/local/$1)');
  await context.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ status: 200, contentType: 'text/css', body: localCss }));
  await context.route('https://fonts.gstatic.com/**', (r) => {
    const f = join(FONTS, basename(new URL(r.request().url()).pathname));
    return existsSync(f) ? r.fulfill({ status: 200, contentType: 'font/woff2', body: readFileSync(f) }) : r.fulfill({ status: 404, body: '' });
  });
}

// ------------------------------------------------------------------ FAN public locality list (Ilfov) for the staged error
function ensureFanIlfov() {
  const f = join(HERE, 'assets', 'fan-localities-ilfov.json');
  if (!existsSync(f)) {
    const raw = execFileSync('curl', ['-sSf', '-m', '30', 'https://api.fancourier.ro/reports/localities?county=Ilfov&perPage=500']).toString();
    const data = JSON.parse(raw).data.map((d) => ({ name: d.name, county: d.county }));
    writeFileSync(f, JSON.stringify({ source: 'GET https://api.fancourier.ro/reports/localities?county=Ilfov (public)', fetchedAt: new Date().toISOString(), data }, null, 1));
  }
  return JSON.parse(readFileSync(f, 'utf8')).data;
}

// ------------------------------------------------------------------ demo server
let server = null;
async function startServer() {
  await stopServer();
  for (const ext of ['', '-wal', '-shm']) rmSync(DB_FILE + ext, { force: true });
  server = spawn(process.execPath, ['--disable-warning=ExperimentalWarning', 'src/server.js'], {
    cwd: APP_DIR,
    env: { ...process.env, DEMO: '1', PORT: String(PORT), DB_FILE, ADMIN_PASSWORD: '', APP_URL: BASE },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stderr.on('data', (d) => process.stderr.write(`[server] ${d}`));
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(`${BASE}/healthz`)).ok) break; } catch {}
    await sleep(150);
  }
  // advanceDemo() runs before listen(); wait until its 8 AWBs are there.
  for (let i = 0; i < 60; i++) {
    const s = await api('/stats');
    if (s.awbToday >= 8) break;
    await sleep(250);
  }
  log('demo server up on', BASE, 'from', APP_DIR);
}
async function stopServer() {
  if (!server) return;
  const s = server;
  server = null;
  s.kill('SIGTERM');
  await new Promise((r) => { s.once('exit', r); setTimeout(r, 3000); });
}
async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers: { 'X-Expedo-Request': '1', ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const ct = res.headers.get('content-type') || '';
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status} ${await res.text()}`);
  return ct.includes('json') ? res.json() : Buffer.from(await res.arrayBuffer());
}
async function orderByName(name) {
  const { orders } = await api(`/orders?status=all&q=${encodeURIComponent(name.replace('#', ''))}`);
  return orders.find((o) => o.name === name);
}

/**
 * Demo state used by every capture:
 *  - parcels tracked once, so the oldest test AWBs are delivered and their cash on delivery collected;
 *  - #1116 (Voluntari, Ilfov) carries the customer's typo "Volutari", is routed to FAN Courier and holds
 *    the rejection that FAN's locality list produces, built by the app's own localityError().
 */
async function stageDemo() {
  const mod = (f) => import(pathToFileURL(join(APP_DIR, f)).href);
  const db = await mod('src/db.js');
  db.openDb(DB_FILE);
  {
    // Like the app's own advanceDemo(): age the demo's test AWBs (4 more minutes) so several
    // cash-on-delivery parcels are already delivered when tracked, then track once.
    const store0 = db.getStoreByShop('demo.myshopify.com');
    const cache = db.storeCache(store0.id);
    const issued = cache.get('mock:issued') || {};
    for (const k of Object.keys(issued)) issued[k].at -= 4 * 60_000;
    cache.set('mock:issued', issued, 60 * 60 * 24 * 30);
  }
  await api('/track', { method: 'POST' });
  const { findLocality } = await mod('src/couriers/locality.js');
  const rows = ensureFanIlfov().map((d) => [d.name, d.county]);
  let err;
  try {
    findLocality(rows, { city: 'Volutari', county: 'Ilfov' }, { nameOf: (r) => r[0], countyOf: (r) => r[1], sameNameIsSame: true, provider: 'fancourier', providerName: 'FAN Courier' });
  } catch (e) { err = e; }
  if (err?.code !== 'ADDRESS_CITY_NOT_FOUND' || !/Did you mean/.test(err.hint || '')) throw new Error('expected a "Did you mean" locality error');

  // The app's own db/pipeline modules write the state (same DB file and APP_SECRET as the server).
  const P = await mod('src/core/pipeline.js');
  const { errorMessage, errorHint } = await mod('src/core/errors.js');
  const id = (await orderByName('#1116')).id;
  const o = db.getOrder(id);
  const data = structuredClone(o.data);
  data.shippingAddress.city = 'Volutari';
  if (data.billingAddress) data.billingAddress.city = 'Volutari';
  db.updateOrder(id, { data, overrides: { ...o.overrides, courier: 'fancourier' } });
  const store = db.getStore(o.store_id);
  P.validateOrder(store, id);
  db.updateOrder(id, { last_error: { ...err.toJSON(), step: 'awb', at: new Date().toISOString() }, status: 'needs_attention' });
  db.logEvent(store.id, id, 'error', 'awb', errorMessage(err), { hint: errorHint(err), code: err.code, details: err.details });
  log('staged:', err.message, '|', err.hint);
  return { stagedOrderId: id };
}

// ------------------------------------------------------------------ helpers for captures
const HIDE_BANNER = '#test-banner{display:none!important}';
const NO_ANIM = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';

async function newAppPage(browser, { width, height, dsf = 2, hideBanner = true, mobile = false }) {
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: dsf, isMobile: mobile, hasTouch: mobile, locale: 'en-US', timezoneId: 'Europe/Bucharest' });
  await routeFonts(context);
  const page = await context.newPage();
  page.on('pageerror', (e) => log('pageerror', e.message));
  page.hideBanner = hideBanner;
  return page;
}
async function go(page, hash) {
  await page.goto(`${BASE}/${hash}`);
  await settle(page);
}
async function settle(page, ms = 350) {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.evaluate(() => document.fonts.ready);
  await page.addStyleTag({ content: NO_ANIM + (page.hideBanner ? HIDE_BANNER : '') });
  await page.waitForTimeout(ms);
}
async function shot(page, file, clip) {
  await page.screenshot({ path: file, clip, animations: 'disabled' });
  return file;
}
/** Bounding box of an element relative to a clip, in CSS px. */
async function boxIn(page, selector, clip, pad = 6) {
  const loc = page.locator(selector).first();
  await loc.waitFor({ state: 'visible', timeout: 8000 });
  const b = await loc.boundingBox();
  if (!b) return null;
  return { x: b.x - clip.x - pad, y: b.y - clip.y - pad, w: b.width + pad * 2, h: b.height + pad * 2 };
}
const pngSize = (f) => { const b = readFileSync(f); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };

// ------------------------------------------------------------------ desktop + mobile captures
async function captureAll(browser, dir) {
  const C = {};
  const MAIN = 220; // sidebar width: captures of a page start after it unless the sidebar is wanted
  const clipOf = (b, pad = 0) => ({ x: Math.floor(b.x - pad), y: Math.floor(b.y - pad), width: Math.ceil(b.width + pad * 2), height: Math.ceil(b.height + pad * 2) });
  const cap = async (p, name, clip, marks = []) => {
    const file = await shot(p, join(dir, `${name}.png`), clip);
    const { w, h } = pngSize(file);
    const vp = p.viewportSize();
    if (Math.abs(w / h - clip.width / clip.height) > 0.01) throw new Error(`capture ${name}: clip ${clip.width}x${clip.height} outside the ${vp.width}x${vp.height} viewport`);
    return { file, w: clip.width, h: clip.height, marks: await Promise.all(marks.map(([sel, pad]) => boxIn(p, sel, clip, pad))) };
  };
  const id1116 = (await orderByName('#1116')).id;

  // 1. Dashboard, wide enough for the five stat tiles on one row
  {
    const p = await newAppPage(browser, { width: 1320, height: 602 });
    await go(p, '#/');
    C.dashboard = await cap(p, 'dashboard', { x: 0, y: 0, width: 1320, height: 602 }, [['.stat.alert', 4]]);
    await p.context().close();
  }

  // 2. Address check: the courier's rejection with "Ai vrut", and the address fixed and saved
  {
    const p = await newAppPage(browser, { width: 1180, height: 1500 });
    await go(p, '#/orders?status=needs_attention');
    C.attention = await cap(p, 'attention', { x: MAIN, y: 0, width: 960, height: 560 }, [[`tr[data-id="${id1116}"] .issue-line`, 6]]);
    await go(p, `#/orders/${id1116}`);
    await p.locator('.drawer-panel .error-box').first().waitFor({ state: 'visible', timeout: 8000 });
    const box = await p.locator('.drawer-panel .error-box').first().boundingBox();
    C.errorBox = await cap(p, 'error-box', clipOf(box, 2), [['.drawer-panel .error-box .hint', 4]]);
    await p.locator('#addr-form input[name=city]').fill('Voluntari');
    await p.locator('#addr-form button.btn').click();
    await p.waitForFunction(() => document.querySelector('.drawer-panel h2 .badge'), null, { timeout: 10000 });
    await settle(p, 300);
    await p.evaluate(() => document.querySelectorAll('.toast').forEach((t) => t.remove()));
    const card = await p.locator('.drawer-panel .card', { has: p.locator('#addr-form') }).boundingBox();
    const street = await p.locator('#addr-form label.field:has(input[name=address1])').boundingBox();
    C.addressCard = await cap(p, 'address-card', { x: Math.floor(card.x), y: Math.floor(card.y), width: Math.ceil(card.width), height: Math.ceil(street.y + street.height + 18 - card.y) },
      [['#addr-form label.field:has(input[name=city])', 6]]);
    await p.context().close();
  }

  // 4. Rules (test-mode banner visible on purpose) + test/live switch from a narrower window
  {
    const p = await newAppPage(browser, { width: 1180, height: 600, hideBanner: false });
    await go(p, '#/settings/rules');
    C.rules = await cap(p, 'rules', { x: MAIN, y: 0, width: 960, height: 600 }, [['.rule:first-of-type .rule-head', 4]]);
    await p.setViewportSize({ width: 1000, height: 900 });
    await go(p, '#/settings/general');
    C.mode = await cap(p, 'mode', clipOf(await p.locator('#section .card').first().boundingBox()));
    await p.context().close();
  }

  // 6. Couriers + invoicing
  {
    const p = await newAppPage(browser, { width: 1180, height: 600 });
    await go(p, '#/settings/couriers');
    C.couriers = await cap(p, 'couriers', { x: MAIN, y: 0, width: 960, height: 600 }, [['.provider-list', 6]]);
    await p.setViewportSize({ width: 1000, height: 900 });
    await go(p, '#/settings/invoicing');
    C.invoicing = await cap(p, 'invoicing', clipOf(await p.locator('#section .card').first().boundingBox()));
    await p.context().close();
  }

  // 5. Tracking + cash on delivery collected (oldest delivered COD order)
  {
    const { orders } = await api('/orders?status=delivered');
    // Orders processed by the app in this demo (the seeded past orders #10xx have no AWB history).
    const cod = orders.filter((o) => o.paymentMethod === 'cod' && o.codCollectedAt && o.name >= '#1100').sort((a, b) => a.name.localeCompare(b.name))[0];
    C.deliveredId = cod.id;
    const p = await newAppPage(browser, { width: 1180, height: 1400 });
    await go(p, '#/orders?status=delivered');
    await go(p, `#/orders/${cod.id}`);
    const head = await p.locator('.drawer-head').boundingBox();
    const liv = await p.locator('.drawer-panel .card').first().boundingBox();
    C.deliveredTop = await cap(p, 'delivered-top', { x: Math.floor(liv.x - 6), y: Math.floor(head.y - 6), width: Math.ceil(liv.width + 12), height: Math.ceil(liv.y + liv.height - head.y + 12) },
      [['.drawer-panel .kv .badge.ok', 5]]);
    // Feature image: the same view for another delivered cash-on-delivery order (unique image)
    const cod2 = orders.filter((o) => o.paymentMethod === 'cod' && o.codCollectedAt && o.name >= '#1100' && o.id !== cod.id)[0] || cod;
    await go(p, `#/orders/${cod2.id}`);
    {
      const h2 = await p.locator('.drawer-head').boundingBox();
      const l2 = await p.locator('.drawer-panel .card').first().boundingBox();
      C.featureCard = await cap(p, 'feature-card', { x: Math.floor(l2.x - 6), y: Math.floor(h2.y - 6), width: Math.ceil(l2.width + 12), height: Math.ceil(l2.y + l2.height - h2.y + 12) },
        [['.drawer-panel .kv .badge.ok', 5]]);
    }
    await p.setViewportSize({ width: 600, height: 1400 });
    await go(p, `#/orders/${cod.id}`);
    const hist = p.locator('.drawer-panel .card', { has: p.locator('h2', { hasText: /^\s*History\s*$/ }) });
    const histFile = join(dir, 'history.png');
    await hist.screenshot({ path: histFile, animations: 'disabled' });
    { const { w, h } = pngSize(histFile); C.history = { file: histFile, w: w / 2, h: h / 2, marks: [] }; }
    await p.context().close();
  }

  // Mobile (412 css wide, DSF 2): dashboard, the order with the locality error, a delivered order
  {
    const MW = 412, MH = 692;
    const p = await newAppPage(browser, { width: MW, height: MH, mobile: true });
    const full = { x: 0, y: 0, width: MW, height: MH };
    await go(p, '#/');
    C.mDash = await cap(p, 'm-dash', full);
    await go(p, `#/orders/${(await orderByName('#1111')).id}`);
    C.mRefused = await cap(p, 'm-refused', full);
    await go(p, `#/orders/${C.deliveredId}`);
    C.mDelivered = await cap(p, 'm-delivered', full);
    await p.context().close();
  }

  // 3. Bulk: every ready order selected, bulk bar in view; then really process them and render the labels PDF
  {
    const p = await newAppPage(browser, { width: 1360, height: 640 });
    await go(p, '#/orders?status=ready');
    await p.locator('#check-all').check();
    await p.mouse.move(5, 300);
    await p.waitForTimeout(200);
    const id1111 = (await orderByName('#1111')).id;
    C.bulk = await cap(p, 'bulk', { x: MAIN, y: 0, width: 1140, height: 640 }, [['[data-bulk=all]', 5], [`tr[data-id="${id1111}"] .issue-line.warning`, 5]]);
    const ids = (await api('/orders?status=ready')).orders.map((o) => o.id);
    await p.locator('[data-bulk=all]').click();
    await p.waitForFunction(() => location.hash.includes('ids='), null, { timeout: 30000 });
    const pdfFile = join(dir, 'labels.pdf');
    writeFileSync(pdfFile, await api(`/labels.pdf?ids=${ids.join(',')}`));
    execFileSync('pdftoppm', ['-r', '220', '-png', pdfFile, join(dir, 'label')]);
    C.labels = readdirSync(dir).filter((f) => /^label-\d+\.png$/.test(f)).sort().map((f) => join(dir, f));
    C.labelCount = C.labels.length;

    await p.context().close();
  }
  return C;
}

// ------------------------------------------------------------------ composition (HTML -> PNG)
function fontFaceCss() {
  return readFileSync(join(FONTS, 'fonts.css'), 'utf8').replace(/url\(([^)]+)\)/g, (_, f) => `url(${pathToFileURL(join(FONTS, f)).href})`);
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const img = (f) => pathToFileURL(f).href;

const BASE_CSS = () => `${fontFaceCss()}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:var(--W);height:var(--H);overflow:hidden}
body{font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased;color:${BRAND.ink};background:${BRAND.soft};position:relative}
.cap{position:absolute;left:72px;top:58px;right:72px}
.cap h1{font-size:46px;line-height:1.12;font-weight:800;letter-spacing:-.022em;color:${BRAND.ink}}
.cap p{margin-top:12px;font-size:23px;line-height:1.38;color:${BRAND.muted};font-weight:500}
.arrow{position:absolute;width:0;height:0;border-left:22px solid transparent;border-right:22px solid transparent;border-top:26px solid ${BRAND.yellow};z-index:4}
.shot{position:absolute;border-radius:14px;overflow:hidden;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.08),0 18px 48px rgba(23,58,168,.20);border:1px solid rgba(22,25,31,.08)}
.shot img{display:block;width:100%;height:100%}
.fade{position:absolute;left:0;right:0;bottom:0;height:90px;background:linear-gradient(rgba(238,242,253,0),${BRAND.soft})}
.mark{position:absolute;border:4px solid ${BRAND.yellow};border-radius:12px;box-shadow:0 0 0 4px rgba(245,197,24,.28)}
.tag{position:absolute;background:${BRAND.ink};color:#fff;font-weight:700;font-size:17px;padding:7px 12px;border-radius:9px;letter-spacing:.01em}
`;

/** Places a capture at (x, y) scaled to width w (height follows). Marks are capture-relative CSS boxes. */
function placeShot(c, { x, y, w, h, crop = null, marks = true, z = 1, radius = 14, fade = false }) {
  const scale = w / c.w;
  const fullH = c.h * scale;
  const boxH = h ?? fullH;
  const m = (marks && c.marks ? c.marks.filter(Boolean) : []).map((b) =>
    `<div class="mark" style="left:${x + b.x * scale}px;top:${y + b.y * scale - (crop || 0) * scale}px;width:${b.w * scale}px;height:${b.h * scale}px;z-index:${z + 1}"></div>`).join('');
  return `<div class="shot" style="left:${x}px;top:${y}px;width:${w}px;height:${boxH}px;z-index:${z};border-radius:${radius}px">
    <img src="${img(c.file)}" style="height:${fullH}px;margin-top:${-(crop || 0) * scale}px">${fade ? '<div class="fade"></div>' : ''}</div>${m}`;
}


async function renderHtml(browser, html, out, { width, height }) {
  const file = join(TMP, `${basename(out, '.png')}-${Math.random().toString(36).slice(2, 7)}.html`);
  writeFileSync(file, `<!doctype html><html><head><meta charset="utf-8"><style>:root{--W:${width}px;--H:${height}px}${BASE_CSS()}</style></head><body>${html}</body></html>`);
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(file).href);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => [...document.images].every((i) => i.complete));
  await page.waitForTimeout(100);
  // Fail loudly on text that does not fit its box (clipped captions).
  const overflow = await page.evaluate(() => [...document.querySelectorAll('[data-fit]')].filter((e) => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1).map((e) => e.textContent.trim().slice(0, 60)));
  if (overflow.length) throw new Error(`text overflow in ${out}: ${overflow.join(' | ')}`);
  const outside = await page.evaluate(([W, H]) => [...document.querySelectorAll('.tag,.cap,h1,p,span')].filter((e) => { const r = e.getBoundingClientRect(); return r.width && (r.right > W + 0.5 || r.bottom > H + 0.5 || r.left < 0 || r.top < 0); }).map((e) => e.textContent.trim().slice(0, 60)), [width, height]);
  if (outside.length) throw new Error(`text outside the canvas in ${out}: ${outside.join(' | ')}`);
  ensureDir(dirname(out));
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width, height } });
  await page.close();
  return out;
}

function caption(t, { maxW = 1456 } = {}) {
  return `<div class="cap" data-fit style="height:178px;max-width:${maxW}px"><h1>${esc(t.title)}</h1><p>${esc(t.sub)}</p></div>`;
}

// Scene layouts (1600x900). Captures are 2x pixels drawn at ~1.0-1.3x their CSS size: crisp.
const SCENES = {
  dashboard: (C) => placeShot(C.dashboard, { x: 72, y: 236, w: 1456, h: 664, fade: true }),
  address: (C) => {
    const eh = C.errorBox.h * (1000 / C.errorBox.w);
    return placeShot(C.errorBox, { x: 72, y: 244, w: 1000, z: 2 }) +
      `<div class="arrow" style="left:740px;top:${244 + eh + 14}px"></div>` +
      placeShot(C.addressCard, { x: 528, y: 244 + eh + 56, w: 1000, h: 900 - (244 + eh + 56), z: 3, fade: true });
  },
  bulk: (C) => {
    const labels = C.labels.slice(0, 3).map((f, i) => {
      const { w, h } = pngSize(f);
      const lw = 250, lh = (h / w) * lw;
      return `<div class="shot" style="left:${1240 + i * 42}px;top:${282 + i * 58}px;width:${lw}px;height:${lh}px;z-index:${5 + i};border-radius:6px;transform:rotate(${(i - 1) * 2.2}deg)"><img src="${img(f)}" style="height:${lh}px"></div>`;
    }).join('');
    const tag = `labels.pdf · ${C.labelCount} A6 labels`;
    return placeShot(C.bulk, { x: 72, y: 236, w: 1120 }) + labels + `<div class="tag" style="left:1232px;top:${282 + 2 * 58 + 384}px;z-index:9">${esc(tag)}</div>`;
  },
  rules: (C) => placeShot(C.rules, { x: 72, y: 236, w: 1060, h: 664, fade: true }) + placeShot(C.mode, { x: 928, y: 486, w: 600, z: 3 }),
  tracking: (C) => placeShot(C.deliveredTop, { x: 72, y: 244, w: 940 }) + placeShot(C.history, { x: 880, y: 380, w: 648, h: Math.min(C.history.h * 648 / C.history.w, 520), z: 3, fade: C.history.h * 648 / C.history.w > 520 }),
  settings: (C) => placeShot(C.couriers, { x: 72, y: 236, w: 1060, h: 664, fade: true }) + placeShot(C.invoicing, { x: 928, y: 520, w: 600, z: 3 }),
};

function desktopHtml(scene, C) {
  const t = SCREENSHOTS.find((s) => s.scene === scene);
  return caption(t) + SCENES[scene](C);
}

function mobileHtml(m, C) {
  const t = m;
  const c = { 'm-dash': C.mDash, 'm-refused': C.mRefused, 'm-delivered': C.mDelivered }[m.scene];
  return `<div class="cap" data-fit style="left:60px;right:60px;top:70px;height:150px"><h1 style="font-size:50px">${esc(t.title)}</h1></div>` +
    placeShot(c, { x: 60, y: 250, w: 780, radius: 28 });
}

function featureHtml(C) {
  const t = FEATURE;
  return `<div style="position:absolute;inset:0;background:${BRAND.cobalt}"></div>
  <div style="position:absolute;left:84px;top:96px;display:flex;align-items:center;gap:18px">
    <svg viewBox="0 0 32 32" width="64" height="64"><rect width="32" height="32" rx="7.5" fill="#fff"/>${ICON_PATHS(32, 1, BRAND.cobalt)}</svg>
    <span style="font-size:44px;font-weight:800;color:#fff;letter-spacing:-.02em">Expedo</span></div>
  <div data-fit style="position:absolute;left:84px;top:230px;width:560px;height:440px">
    <h1 style="font-size:58px;line-height:1.08;font-weight:800;color:#fff;letter-spacing:-.025em">${esc(t.title)}</h1>
    <div style="width:96px;height:8px;background:${BRAND.yellow};border-radius:4px;margin:30px 0 26px"></div>
    <p style="font-size:26px;line-height:1.35;color:rgba(255,255,255,.9);font-weight:500">${esc(t.sub)}</p></div>
  ${placeShot(C.featureCard, { x: 690, y: 450 - (C.featureCard.h * 830 / C.featureCard.w) / 2, w: 830, radius: 16 })}`;
}

// ------------------------------------------------------------------ icon
// The favicon mark (isometric parcel, 32-unit grid) redrawn for 1200 px: thicker strokes, round joins,
// a yellow lid so it still reads as a parcel at 64 px, and a light/dark side for depth. No text.
function ICON_PATHS(size, f = 0.9, stroke = '#fff') {
  // f = 1 reproduces the favicon proportions (parcel 18/32 of the tile high); smaller = more padding.
  const s = (size / 32) * f;
  const c = size / 2;
  const pt = (x, y) => `${(c + (x - 16) * s).toFixed(2)},${(c + (y - 16) * s).toFixed(2)}`;
  const sw = (2.4 * s).toFixed(2);
  return `
  <path d="M${pt(8, 11)}L${pt(16, 15)}L${pt(16, 25)}L${pt(8, 21)}Z" fill="${stroke}" fill-opacity=".10"/>
  <path d="M${pt(24, 11)}L${pt(16, 15)}L${pt(16, 25)}L${pt(24, 21)}Z" fill="#0b1a4d" fill-opacity=".22"/>
  <path d="M${pt(8, 11)}L${pt(16, 7)}L${pt(24, 11)}L${pt(16, 15)}Z" fill="${BRAND.yellow}"/>
  <path d="M${pt(8, 11)}L${pt(16, 7)}L${pt(24, 11)}L${pt(24, 21)}L${pt(16, 25)}L${pt(8, 21)}Z" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
  <path d="M${pt(8, 11)}L${pt(16, 15)}L${pt(24, 11)}M${pt(16, 15)}L${pt(16, 25)}" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round"/>`;
}
function iconSvg({ size = 1200, rounded = false } = {}) {
  const r = rounded ? size * 0.2237 : 0;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2553e6"/><stop offset="1" stop-color="${BRAND.cobalt}"/></linearGradient></defs>
  <rect width="${size}" height="${size}" rx="${r}" fill="url(#g)"/>${ICON_PATHS(size, 0.92)}
</svg>`;
}
async function buildIcon(browser) {
  const out = ensureDir(join(HERE, 'icon'));
  writeFileSync(join(out, 'expedo-icon.svg'), iconSvg());
  writeFileSync(join(out, 'expedo-icon-rounded.svg'), iconSvg({ rounded: true }));
  const page = await browser.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 1 });
  const files = [];
  for (const [name, size, rounded] of [['expedo-icon-1200.png', 1200, false], ['expedo-icon-512.png', 512, false], ['expedo-icon-256.png', 256, false], ['expedo-icon-128.png', 128, false], ['expedo-icon-64.png', 64, false], ['expedo-icon-rounded-512.png', 512, true], ['expedo-icon-rounded-64.png', 64, true]]) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(`<html><body style="margin:0;background:transparent">${iconSvg({ size, rounded })}</body></html>`);
    const f = join(out, name);
    await page.screenshot({ path: f, omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
    files.push(f);
  }
  // Preview sheet: how it reads at listing sizes, on light and dark.
  await page.setViewportSize({ width: 900, height: 300 });
  await page.setContent(`<html><body style="margin:0;display:flex;font-family:sans-serif">
    ${['#ffffff', '#16191f'].map((bg) => `<div style="flex:1;background:${bg};display:flex;align-items:center;justify-content:center;gap:28px">
      ${[160, 96, 64, 32].map((s) => `<div style="width:${s}px;height:${s}px;border-radius:${s * 0.2237}px;overflow:hidden">${iconSvg({ size: s })}</div>`).join('')}</div>`).join('')}</body></html>`);
  await page.screenshot({ path: join(out, 'icon-preview.png') });
  await page.close();
  return files;
}

// ------------------------------------------------------------------ PNG optimisation (lossless) via Pillow
function optimizePngs(files) {
  const script = `
import sys
from PIL import Image
for f in sys.argv[1:]:
    im = Image.open(f)
    im.load()
    if im.mode == 'RGBA' and im.getextrema()[3][0] == 255:
        im = im.convert('RGB')
    im.save(f, optimize=True)
`;
  execFileSync('python3', ['-c', script, ...files]);
}

// ------------------------------------------------------------------ screens: desktop, mobile, feature
async function buildScreens(browser) {
  for (const d of ['screenshots', 'feature']) rmSync(join(HERE, d), { recursive: true, force: true });
  const capDir = ensureDir(join(TMP, 'captures'));
  for (const f of readdirSync(capDir)) rmSync(join(capDir, f), { force: true });
  await startServer();
  await stageDemo();
  const C = await captureAll(browser, capDir);
  await stopServer();
  const out = [];
  for (const s of SCREENSHOTS) out.push(await renderHtml(browser, desktopHtml(s.scene, C), join(HERE, 'screenshots', `${s.id}.png`), { width: 1600, height: 900 }));
  for (const m of MOBILE) out.push(await renderHtml(browser, mobileHtml(m, C), join(HERE, 'screenshots', 'mobile', `${m.id}.png`), { width: 900, height: 1600 }));
  out.push(await renderHtml(browser, featureHtml(C), join(HERE, 'feature', 'feature.png'), { width: 1600, height: 900 }));
  copyFileSync(join(capDir, 'labels.pdf'), join(HERE, 'screenshots', 'labels-sample.pdf'));
  return out;
}

// ------------------------------------------------------------------ screencast for review (1920x1080, English captions)
async function buildScreencast(browser) {
  const { recordScreencast } = await import('./screencast.mjs');
  await startServer();
  await stageDemo();
  const file = await recordScreencast({ browser, BASE, TMP, HERE, api, orderByName, routeFonts, fontFaceCss, BRAND, ICON_PATHS, pngSize, log });
  await stopServer();
  return file;
}

// ------------------------------------------------------------------ copy docs (generated from copy.mjs, with limit checks)
function checkLimits() {
  const errs = [];
  const c = COPY;
  const chk = (field, v, lim) => { if (v.length > lim) errs.push(`${field}: ${v.length} > ${lim}`); };
  chk('appName', c.appName, LIMITS.appName);
  for (const a of c.appNameAlternatives || []) chk('appNameAlternative', a, LIMITS.appName);
  chk('subtitle', c.subtitle, LIMITS.subtitle);
  chk('introduction', c.introduction, LIMITS.introduction);
  chk('details', c.details, LIMITS.details);
  c.features.forEach((f, i) => chk(`feature[${i}]`, f, LIMITS.feature));
  if (c.searchTerms.length > LIMITS.searchTerms) errs.push(`searchTerms: ${c.searchTerms.length} terms`);
  if (INTEGRATIONS.recommendedSix.length > LIMITS.integrations) errs.push('integrations > 6');
  if (PRICING.plans.length > LIMITS.publicPlans) errs.push('more than 8 public plans');
  for (const p of PRICING.plans) {
    chk(`plan ${p.name} name`, p.name, LIMITS.planName);
    p.features.forEach((f, i) => chk(`plan ${p.name} feature[${i}]`, f, LIMITS.planFeature));
  }
  const prices = /(\$|USD|\bRON\b|\blei\b)\s?\d|\d\s?(\$|USD|RON|lei)\b/i;
  for (const t of [...SCREENSHOTS.flatMap((x) => [x.title, x.sub]), ...MOBILE.map((x) => x.title), FEATURE.title, FEATURE.sub]) if (prices.test(t)) errs.push(`price in an image caption: ${t}`);
  if (errs.length) throw new Error(`copy over limits:\n${errs.join('\n')}`);
}

function writeCopyDocs() {
  checkLimits();
  const c = COPY;
  const cnt = (s, lim) => `\`${s.length}/${lim}\``;
  const usd = (n) => (n === 0 ? '$0' : `$${n.toFixed(2)} USD ${PRICING.interval}`);
  const md = `# Expedo listing copy (English, the only listing)

Generated by \`node P/apps/expedo/marketing/listing/build.mjs copy\` from \`copy.mjs\`; edit there, not here.
Counts are characters as typed in the Partner Dashboard (limits and sources in REQUIREMENTS.md).

## App name ${cnt(c.appName, LIMITS.appName)}

${c.appName}

Alternatives (must stay "similar" to the TOML name \`Expedo\`, req. 4.1.1): ${c.appNameAlternatives.map((a) => `"${a}" ${cnt(a, LIMITS.appName)}`).join(', ')}

## App card subtitle ${cnt(c.subtitle, LIMITS.subtitle)}

${c.subtitle}

## App introduction ${cnt(c.introduction, LIMITS.introduction)}

${c.introduction}

## App details ${cnt(c.details, LIMITS.details)}

${c.details}

## Feature list (max ${LIMITS.feature} characters each)

${c.features.map((f) => `- ${f} ${cnt(f, LIMITS.feature)}`).join('\n')}

## Search terms (max ${LIMITS.searchTerms}, one idea each)

${c.searchTerms.map((s) => `- ${s}`).join('\n')}

## Languages

${c.languages.join(', ')} (the app UI is usable in both; req. 4.3.2)

## Pricing (Shopify App Pricing, ${PRICING.currency}, billed ${PRICING.interval})

Billing method: ${PRICING.billing}. Free trial: **${PRICING.trialDays} days** on every paid plan (a free plan has nothing to trial).
Plan display names and top features: shopify.dev gives no character limit; names kept ≤ ${LIMITS.planName} and each feature ≤ ${LIMITS.planFeature} characters (counts below).

${PRICING.plans.map((p) => `### ${p.name} ${cnt(p.name, LIMITS.planName)}: ${usd(p.price)}${p.price ? `, ${PRICING.trialDays}-day free trial` : ''}

${p.features.map((f) => `- ${f} ${cnt(f, LIMITS.planFeature)}`).join('\n')}`).join('\n\n')}

## Screenshot alt text

${SCREENSHOTS.map((s) => `- \`screenshots/${s.id}.png\`: ${s.alt}`).join('\n')}
${MOBILE.map((s) => `- \`screenshots/mobile/${s.id}.png\`: ${s.alt}`).join('\n')}

## Feature image alt text

- \`feature/feature.png\`: ${FEATURE.alt}

## Screenshot captions (already on the images)

${SCREENSHOTS.map((s) => `- **${s.title}.** ${s.sub}`).join('\n')}
`;
  writeFileSync(join(HERE, 'LISTING-COPY.md'), md);
  log('wrote LISTING-COPY.md');
}

// ------------------------------------------------------------------ LISTING.md asset table (from the files on disk)
function writeAssetTable() {
  const rows = [];
  const dims = (f) => {
    if (f.endsWith('.png')) { const { w, h } = pngSize(f); return `${w}×${h}`; }
    if (f.endsWith('.mp4')) {
      try {
        const o = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=width,height', '-show_entries', 'format=duration', '-of', 'default=nw=1', f]).toString();
        const g = (k) => (o.match(new RegExp(`${k}=([\\d.]+)`)) || [])[1];
        const d = Number(g('duration'));
        return `${g('width')}×${g('height')}, ${Math.floor(d / 60)}:${String(Math.round(d % 60)).padStart(2, '0')}`;
      } catch { return ''; }
    }
    return '';
  };
  const add = (rel, purpose, field) => {
    const f = join(HERE, rel);
    if (!existsSync(f)) return;
    const kb = statSync(f).size / 1024;
    rows.push(`| \`${rel}\` | ${[dims(f), kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`].filter(Boolean).join(', ')} | ${purpose} | ${field} |`);
  };
  add('icon/expedo-icon-1200.png', 'App icon, square (Shopify rounds the corners), no text', '**App icon** in the listing and in the app configuration (Dev Dashboard)');
  for (const s of [512, 256, 128, 64]) add(`icon/expedo-icon-${s}.png`, 'Smaller export of the icon', 'Not uploaded; website, e-mail, docs');
  for (const s of [512, 64]) add(`icon/expedo-icon-rounded-${s}.png`, 'Rounded-corner variant', 'Not uploaded to Shopify (it rounds the square itself); website, favicon');
  add('icon/expedo-icon.svg', 'Vector master of the icon', 'Source');
  add('icon/expedo-icon-rounded.svg', 'Vector master, rounded variant', 'Source');
  add('icon/icon-preview.png', 'Icon at 160/96/64/32 px on light and dark', 'Check only');
  add('feature/feature.png', `Feature image: ${FEATURE.title}`, '**Feature media** (static image)');
  SCREENSHOTS.forEach((sc, i) => add(`screenshots/${sc.id}.png`, `Screenshot ${i + 1}: ${sc.title}`, `**Desktop screenshots**, position ${i + 1}`));
  MOBILE.forEach((m, i) => add(`screenshots/mobile/${m.id}.png`, `Mobile screenshot ${i + 1}: ${m.title}`, `**Mobile screenshots**, position ${i + 1}`));
  add('screenshots/labels-sample.pdf', 'The labels PDF rendered in screenshot 3 (test labels)', 'Reference only');
  add('review/expedo-review-screencast.mp4', 'Screencast for review: real walkthrough of the demo UI, English captions burned in, H.264 CRF 23', '**Testing instructions → screencast** (upload, or unlisted video link)');
  add('review/expedo-review-screencast.en.srt', 'The screencast captions as subtitles', 'Optional: subtitles if uploaded to YouTube/Vimeo');
  add('review/screencast-chapters.json', 'Caption timestamps', 'Reference for the reviewer notes');
  const table = ['| File | Size | Purpose | Form field |', '|---|---|---|---|', ...rows].join('\n');
  const f = join(HERE, 'LISTING.md');
  const md = readFileSync(f, 'utf8').replace(/<!-- assets:start -->[\s\S]*?<!-- assets:end -->/, `<!-- assets:start -->\n${table}\n<!-- assets:end -->`);
  writeFileSync(f, md);
  log('updated the asset table in LISTING.md');
}

// ------------------------------------------------------------------ main
async function main() {
  ensureDir(TMP);
  if (want('copy')) writeCopyDocs();
  if (!(want('icon') || want('screens') || want('video'))) { writeAssetTable(); return; }
  ensureFonts();
  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({ executablePath: existsSync(CHROMIUM) ? CHROMIUM : undefined });
  const produced = [];
  try {
    if (want('icon')) produced.push(...await buildIcon(browser));
    if (want('screens')) produced.push(...await buildScreens(browser));
    if (want('video')) await buildScreencast(browser);
  } finally {
    await browser.close();
    await stopServer();
  }
  const pngs = produced.filter((f) => f.endsWith('.png'));
  if (pngs.length) optimizePngs(pngs);
  for (const f of produced) log(`${(statSync(f).size / 1024).toFixed(0).padStart(6)} KB  ${f.replace(HERE + '/', '')}`);
  writeAssetTable();
}

main().catch(async (e) => { console.error(e); await stopServer(); process.exit(1); });
