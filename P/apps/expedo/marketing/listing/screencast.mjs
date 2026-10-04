// Screencast for Shopify app review: a real walkthrough of the Expedo demo UI, captured frame by frame
// with Playwright (no screen recorder, so text stays sharp), English captions burned in, encoded with
// ffmpeg to H.264. Output: review/expedo-review-screencast.mp4 (1920x1080) + .srt with the captions.
//
// Layout of every frame: the app at 1280x640 CSS px x1.5 = 1920x960, and a 1920x120 caption bar below.
// The pointer drawn on screen is injected into the page for the recording only; clicks, typing and
// selections are real Playwright input on the running demo server.

import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const VW = 1280, VH = 640, DSF = 1.5, BAR = 80;

const CURSOR_SVG = `<svg width="26" height="26" viewBox="0 0 26 26"><path d="M3 2l18 9.5-7.6 1.9L9.8 21z" fill="#16191f" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`;

const INIT = `(() => {
  const add = () => {
    if (document.getElementById('__cursor')) return;
    const c = document.createElement('div');
    c.id = '__cursor';
    c.innerHTML = ${JSON.stringify(CURSOR_SVG)} + '<span id="__ripple"></span>';
    c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform:translate(-60px,-60px)';
    const st = document.createElement('style');
    st.textContent = '#__ripple{position:absolute;left:-14px;top:-14px;width:28px;height:28px;border-radius:50%;background:rgba(245,197,24,.55);border:2px solid #f5c518;opacity:0}#__cursor.click #__ripple{opacity:1}#__cursor svg{position:absolute;left:-3px;top:-2px}*{caret-color:transparent!important}';
    document.documentElement.append(st);
    document.documentElement.append(c);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();`;

export async function recordScreencast({ browser, BASE, TMP, HERE, api, orderByName, routeFonts, fontFaceCss, BRAND, ICON_PATHS, log }) {
  const dir = join(TMP, 'screencast');
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(join(dir, 'f'), { recursive: true });
  const outDir = join(HERE, 'review');
  mkdirSync(outDir, { recursive: true });

  const context = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: DSF, locale: 'en-US', timezoneId: 'Europe/Bucharest' });
  await routeFonts(context);
  await context.addInitScript(INIT);
  const page = await context.newPage();
  const cardPage = await browser.newPage({ viewport: { width: VW, height: VH }, deviceScaleFactor: DSF });
  const barPage = await browser.newPage({ viewport: { width: VW, height: BAR }, deviceScaleFactor: DSF });

  // ---------------------------------------------------------------- timeline
  const frames = []; // { file, dur, cap }
  let n = 0;
  let cap = { step: '', text: '' };
  let cur = { x: VW / 2, y: VH / 2 };
  const caps = new Map();
  const setCap = (step, text) => { cap = { step, text }; };
  const fname = () => join(dir, 'f', `${String(n++).padStart(5, '0')}.png`);

  async function frame(dur, p = page) {
    const file = fname();
    await p.screenshot({ path: file, animations: 'disabled' });
    frames.push({ file, dur, cap: { ...cap } });
  }
  const hold = (sec) => frame(sec);
  async function settle(ms = 250) {
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(ms);
  }
  async function placeCursor(x, y, clicking = false) {
    cur = { x, y };
    await page.evaluate(([x, y, c]) => {
      const el = document.getElementById('__cursor');
      if (!el) return;
      el.style.transform = `translate(${x}px,${y}px)`;
      el.classList.toggle('click', c);
    }, [x, y, clicking]);
  }
  async function moveTo(target, { steps = 12, dx = 0.5, dy = 0.5 } = {}) {
    const loc = typeof target === 'string' ? page.locator(target).first() : target;
    await loc.scrollIntoViewIfNeeded();
    const b = await loc.boundingBox();
    const tx = b.x + b.width * dx, ty = b.y + b.height * dy;
    const sx = cur.x, sy = cur.y;
    for (let i = 1; i <= steps; i++) {
      const t = i / steps, e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
      const x = sx + (tx - sx) * e, y = sy + (ty - sy) * e;
      await page.mouse.move(x, y);
      await placeCursor(x, y);
      await frame(1 / 30);
    }
    return loc;
  }
  async function click(target, { after = 0.6, ...o } = {}) {
    const loc = await moveTo(target, o);
    await placeCursor(cur.x, cur.y, true);
    await frame(0.12);
    await loc.click();
    await placeCursor(cur.x, cur.y, false);
    await settle();
    if (after) await hold(after);
  }
  async function type(target, text) {
    const loc = await moveTo(target);
    await loc.click();
    await loc.press('Control+A');
    await loc.press('Backspace');
    await frame(0.15);
    for (const ch of text) { await loc.press(ch === ' ' ? 'Space' : ch); await frame(0.075); }
  }
  async function go(hash, sec = 0) {
    await page.goto(`${BASE}/${hash}`);
    await settle(350);
    await placeCursor(cur.x, cur.y);
    if (sec) await hold(sec);
  }
  async function card(html, sec) {
    const file = join(dir, `card-${n}.html`);
    writeFileSync(file, `<!doctype html><meta charset="utf-8"><style>${fontFaceCss()}
      *{box-sizing:border-box;margin:0;padding:0}body{width:${VW}px;height:${VH}px;overflow:hidden;font-family:Inter,sans-serif;background:${BRAND.cobalt};color:#fff;-webkit-font-smoothing:antialiased;padding:64px 80px;position:relative}
      h1{font-size:44px;line-height:1.1;font-weight:800;letter-spacing:-.02em}h2{font-size:22px;font-weight:600;color:${BRAND.yellow};margin-bottom:14px;letter-spacing:.02em;text-transform:uppercase}
      ol,ul{margin-top:26px;padding-left:28px;font-size:23px;line-height:1.5;font-weight:500}li{margin:5px 0}li::marker{color:${BRAND.yellow};font-weight:800}
      p{font-size:22px;line-height:1.45;margin-top:20px;color:rgba(255,255,255,.9)}code{font-family:'JetBrains Mono',monospace;font-size:.9em;background:rgba(255,255,255,.14);padding:1px 7px;border-radius:5px}
      .brand{position:absolute;right:72px;bottom:56px;display:flex;align-items:center;gap:12px;font-size:28px;font-weight:800}
    </style><body>${html}<div class="brand"><svg viewBox="0 0 32 32" width="44" height="44"><rect width="32" height="32" rx="7.5" fill="#fff"/>${ICON_PATHS(32, 1, BRAND.cobalt)}</svg>Expedo</div></body>`);
    await cardPage.goto(pathToFileURL(file).href);
    await cardPage.evaluate(() => document.fonts.ready);
    await frame(sec, cardPage);
  }

  // ---------------------------------------------------------------- script
  const id = async (name) => (await orderByName(name)).id;
  const popup = () => context.waitForEvent('page', { timeout: 15000 });

  setCap('Expedo', 'Screencast for app review. The app UI is in English (Romanian is the second language); captions explain each step.');
  await card(`<h2>Screencast for Shopify app review</h2><h1>Expedo: Romanian orders to AWB,<br>invoice and collected cash on delivery</h1>
    <ul><li>Demo store with realistic Romanian orders, including problem orders</li><li>Test mode: no courier or invoicing account needed, nothing is sent anywhere</li><li>Walkthrough: install, orders, address fix, refused-parcel warning, bulk AWB + invoice, labels, tracking, settings</li></ul>`, 7);

  setCap('1 · Install', 'Install on a development store, approve access, pick a plan (no charge on development stores), then open Expedo from Apps.');
  await card(`<h2>Step 1 · Install</h2><h1>Install and open the app</h1>
    <ol><li>Open the install link for your development store and approve the requested access (orders, merchant-managed fulfillments).</li>
    <li>Pick a plan on Shopify’s plan page (free of charge on development stores). Expedo opens inside the admin: <code>Apps → Expedo</code>.</li>
    <li>It imports the last 14 days of orders and listens for new ones.</li>
    <li>New stores start in <b>Test mode</b>: real orders, test AWBs and test invoices.</li></ol>`, 11);

  setCap('2 · Dashboard', 'After install, the dashboard shows what to do today: orders to process, orders needing attention, parcels on the way and cash on delivery.');
  await go('#/', 4.5);
  await moveTo('.stat.alert', { steps: 16 });
  await hold(2.5);

  setCap('3 · Test mode', 'The store is in Test mode (yellow banner): AWBs and invoices are test documents, couriers and invoicing apps are not called, Shopify is not changed. Settings → General also sets the language.');
  await click('#nav a[data-route=settings]', { after: 5.5 });

  setCap('4 · Couriers', 'Five couriers: Cargus, Sameday, FAN Courier, GLS, DPD. On a live store you paste the API credentials and click “Test connection”.');
  await click('.subnav a[href="#/settings/couriers"]', { after: 3.5 });
  await click('.provider[data-p=sameday]', { after: 3.5 });
  setCap('4 · Couriers', 'Reviewers: in Test mode no account is needed. Click “Save” with empty fields, then “Use as default”.');
  await click('#pf button.btn.primary', { after: 1.6 });
  await click('#make-default', { after: 3 });

  setCap('5 · Invoicing', 'SmartBill, FGO or Oblio are set up the same way. The invoice is issued together with the AWB, or only manually.');
  await click('.subnav a[href="#/settings/invoicing"]', { after: 5 });

  setCap('6 · Rules', 'Rules choose the courier per order: easybox orders go to Sameday, heavy orders get two parcels, large cash-on-delivery orders wait for a check.');
  await click('.subnav a[href="#/settings/rules"]', { after: 6 });

  setCap('7 · Orders', 'Orders with a problem are stopped before any courier call. Each problem says what is wrong and what to do.');
  await click('#nav a[data-route=orders]', { after: 1.5 });
  await click('.tabs a[href="#/orders?status=needs_attention"]', { after: 4.5 });

  const o1115 = await id('#1115');
  setCap('8 · Address fix', 'Order #1115 has no county (“The county is missing.”). Pick it from the list and save: the address is checked again.');
  await click(`tr[data-id="${o1115}"] .order-name`, { after: 2.5 });
  await moveTo('#addr-form select[name=province]');
  await page.locator('#addr-form select[name=province]').selectOption({ label: 'Ilfov' });
  await frame(1.2);
  await click('#addr-form button.btn', { after: 3.5 });
  await click('.drawer-panel [data-close]', { after: 0.8 });

  const o1116 = await id('#1116');
  setCap('8 · Address fix', 'Order #1116: FAN Courier does not know the locality “Volutari”. Expedo suggests “Did you mean: Voluntari, …?” from the courier’s list.');
  await click(`tr[data-id="${o1116}"] .order-name`, { after: 4 });
  setCap('8 · Address fix', 'Type the right locality and save. The change stays in Expedo; the order in Shopify is not modified.');
  await type('#addr-form input[name=city]', 'Voluntari');
  await click('#addr-form button.btn', { after: 2.5 });
  setCap('9 · AWB + invoice', '“Create AWB + invoice” creates the AWB at the courier and the invoice. In Test mode both are test documents.');
  await page.locator('.drawer-panel').evaluate((el) => el.scrollTo(0, 0));
  await click('.drawer-panel [data-act=process]', { after: 4.5 });
  await click('.drawer-panel [data-close]', { after: 0.6 });

  setCap('10 · Bulk', 'Open “Ready to process”, select the orders and click “Create AWB + invoice” once for all of them. Order #1111 is flagged: this customer refused a parcel before.');
  await click('.tabs a[href="#/orders?status=ready"]', { after: 2 });
  const readyIds = (await api('/orders?status=ready')).orders.map((o) => o.id);
  await click('#check-all', { after: 1.2 });
  await moveTo(`tr[data-id="${await id('#1111')}"] .issue-line.warning`, { steps: 14 });
  await hold(3);
  await click('[data-bulk=all]', { after: 0 });
  await page.waitForFunction(() => location.hash.includes('ids='), null, { timeout: 30000 });
  await settle(400);
  setCap('10 · Bulk', 'Done: every order has one AWB and one invoice. Clicking again never creates a second AWB or invoice for the same order.');
  await hold(5);

  setCap('11 · Labels', '“Labels” opens one PDF with every label, A6 or A4. In Test mode the labels are marked as test labels.');
  const pdfPopup = popup();
  await click('[data-bulk=labels]', { after: 0 });
  try { (await pdfPopup).close(); } catch {}
  const ids = [...new Set([...readyIds, o1116])];
  const pdf = await api(`/labels.pdf?ids=${ids.join(',')}`);
  writeFileSync(join(dir, 'labels.pdf'), pdf);
  execFileSync('pdftoppm', ['-r', '120', '-png', join(dir, 'labels.pdf'), join(dir, 'lbl')]);
  const lbls = readdirSync(dir).filter((f) => /^lbl-\d+\.png$/.test(f)).sort();
  const viewer = join(dir, 'labels.html');
  writeFileSync(viewer, `<!doctype html><meta charset="utf-8"><style>${fontFaceCss()}body{margin:0;background:#3b3f46;font-family:Inter,sans-serif;height:${VH}px;overflow:hidden}
    .bar{height:44px;background:#24272c;color:#e8eaee;display:flex;align-items:center;padding:0 20px;font-size:15px;font-weight:600;gap:12px}.bar span{color:#a2a9b6;font-weight:500}
    .pages{display:flex;gap:22px;padding:28px 30px;flex-wrap:wrap}.pages img{height:250px;background:#fff;box-shadow:0 6px 18px rgba(0,0,0,.35)}</style>
    <div class="bar">labels.pdf <span>${lbls.length} pages · A6 · one label per parcel</span></div><div class="pages">${lbls.map((f) => `<img src="${pathToFileURL(join(dir, f)).href}">`).join('')}</div>`);
  await cardPage.goto(pathToFileURL(viewer).href);
  await cardPage.waitForFunction(() => [...document.images].every((i) => i.complete));
  await frame(5.5, cardPage);

  setCap('11 · Picking list', '“Picking list” adds up the products to pick for the selected orders, ready to print.');
  const pickPopup = popup();
  await click('[data-bulk=picking]', { after: 0 });
  try {
    const pp = await pickPopup;
    await pp.setViewportSize({ width: VW, height: VH });
    await pp.waitForLoadState();
    await pp.waitForTimeout(300);
    await frame(5, pp);
    await pp.close();
  } catch (e) { log('picking popup:', e.message); }

  setCap('12 · Tracking', 'Parcels are checked every 30 minutes, or on demand with “Check parcels”.');
  await click('#nav a[data-route=dashboard]', { after: 1 });
  await click('#btn-track', { after: 3.5 });

  const delivered = (await api('/orders?status=delivered')).orders.filter((o) => o.paymentMethod === 'cod' && o.codCollectedAt && o.name >= '#1100').sort((a, b) => a.name.localeCompare(b.name))[0];
  setCap('12 · Cash on delivery', 'A delivered cash-on-delivery parcel is marked “collected”. On a live store the order is also marked paid in Shopify.');
  await go(`#/orders?status=delivered`);
  await click(`tr[data-id="${delivered.id}"] .order-name`, { after: 1 });
  await moveTo('.drawer-panel .kv .badge.ok', { steps: 14 });
  await hold(4.5);
  setCap('12 · History', 'Every step is in the order history: import, AWB, invoice, tracking, delivery, cash collected and payment recorded on the invoice.');
  const hist = page.locator('.drawer-panel .card', { has: page.locator('h2', { hasText: /^\s*History\s*$/ }) });
  await hist.evaluate((el) => el.scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(150);
  await hold(5.5);
  await click('.drawer-panel [data-close]', { after: 0.4 });

  setCap('13 · COD export', '“COD export (CSV)” exports cash-on-delivery amounts per parcel, to check courier payments.');
  await go('#/', 0.8);
  await moveTo('#btn-cod', { steps: 16 });
  await hold(4);

  setCap('14 · Automation', 'Optional automatic processing for new orders. Temporary courier errors are retried after 1, 5, 15, 60 and 180 minutes.');
  await click('#nav a[data-route=settings]', { after: 0.6 });
  await click('.subnav a[href="#/settings/automation"]', { after: 6 });

  setCap('15 · Go live', 'When ready: switch to Live. Real AWBs and invoices; the order is fulfilled in Shopify with tracking and the customer gets Shopify’s shipping e-mail.');
  await click('.subnav a[href="#/settings/general"]', { after: 0.6 });
  await moveTo('input[name=mode][value=live]', { steps: 14 });
  await hold(4);
  await moveTo('input[name=fulfillInShopify]', { steps: 12 });
  await hold(3.5);

  setCap('Expedo', 'Support: office@krea.ro · ARTEMIS DIGITAL SRL');
  await card(`<h2>Thank you for reviewing</h2><h1>Expedo</h1>
    <p>Test mode lets you try every step on a development store without courier or invoicing accounts.<br>Step-by-step test instructions are in the review notes.</p>
    <p>Support: <b>office@krea.ro</b><br>Publisher: ARTEMIS DIGITAL SRL</p>`, 5);

  await context.close();
  await cardPage.close();

  // ---------------------------------------------------------------- caption bars
  for (const f of frames) {
    const key = `${f.cap.step}|${f.cap.text}`;
    if (caps.has(key)) { f.bar = caps.get(key); continue; }
    const file = join(dir, `bar-${caps.size}.png`);
    await barPage.setContent(`<!doctype html><meta charset="utf-8"><style>${fontFaceCss()}*{margin:0;box-sizing:border-box}
      body{width:${VW}px;height:${BAR}px;background:${BRAND.ink};font-family:Inter,sans-serif;display:flex;align-items:center;gap:16px;padding:0 26px;-webkit-font-smoothing:antialiased}
      .s{flex:none;background:${BRAND.yellow};color:${BRAND.ink};font-weight:800;font-size:15px;padding:6px 11px;border-radius:7px;white-space:nowrap}
      .t{color:#fff;font-size:19.5px;line-height:1.3;font-weight:600}</style><body><span class="s">${f.cap.step}</span><span class="t" id="t">${f.cap.text}</span></body>`);
    await barPage.evaluate(() => document.fonts.ready);
    // shrink if a caption does not fit two lines
    await barPage.evaluate((H) => { const t = document.getElementById('t'); let s = 19.5; while (t.scrollHeight > H - 8 && s > 15) { s -= 0.5; t.style.fontSize = s + 'px'; } }, BAR);
    await barPage.screenshot({ path: file });
    caps.set(key, file);
    f.bar = file;
  }
  await barPage.close();

  // ---------------------------------------------------------------- encode
  const list = (key) => frames.map((f) => `file '${f[key]}'\nduration ${f.dur.toFixed(4)}`).join('\n') + `\nfile '${frames.at(-1)[key]}'\n`;
  writeFileSync(join(dir, 'app.txt'), list('file'));
  writeFileSync(join(dir, 'bar.txt'), list('bar'));
  const out = join(outDir, 'expedo-review-screencast.mp4');
  execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error',
    '-f', 'concat', '-safe', '0', '-i', join(dir, 'app.txt'),
    '-f', 'concat', '-safe', '0', '-i', join(dir, 'bar.txt'),
    '-filter_complex', '[0:v]fps=30,scale=1920:960:flags=lanczos,setsar=1[a];[1:v]fps=30,scale=1920:120:flags=lanczos,setsar=1[b];[a][b]vstack=inputs=2,format=yuv420p[v]',
    '-map', '[v]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-tune', 'stillimage', '-r', '30', '-movflags', '+faststart', out]);

  // ---------------------------------------------------------------- captions as SRT too
  const ts = (s) => { const ms = Math.round(s * 1000); const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60; return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };
  const cues = [];
  let t = 0;
  for (const f of frames) {
    const key = `${f.cap.step}|${f.cap.text}`;
    if (cues.length && cues.at(-1).key === key) cues.at(-1).end = t + f.dur;
    else cues.push({ key, start: t, end: t + f.dur, text: `${f.cap.step}: ${f.cap.text}` });
    t += f.dur;
  }
  writeFileSync(join(outDir, 'expedo-review-screencast.en.srt'), cues.map((c, i) => `${i + 1}\n${ts(c.start)} --> ${ts(c.end)}\n${c.text}\n`).join('\n'));
  writeFileSync(join(outDir, 'screencast-chapters.json'), JSON.stringify(cues.map((c) => ({ at: ts(c.start).slice(0, 8), caption: c.text })), null, 1));
  log(`screencast: ${frames.length} frames, ${t.toFixed(1)} s, ${(statSync(out).size / 1048576).toFixed(1)} MB`);
  if (!existsSync(out)) throw new Error('ffmpeg produced no file');
  return out;
}
