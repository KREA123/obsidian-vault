import express from 'express';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { readFileSync } from 'node:fs';
import { config } from './config.js';
import * as db from './db.js';
import * as P from './core/pipeline.js';
import { couriers, getCourier } from './couriers/index.js';
import { invoicers, getInvoicer } from './invoicing/index.js';
import { RULE_FIELDS, RULE_OPS, RULE_ACTIONS } from './core/rules.js';
import { COUNTIES } from './core/address.js';
import { TRACKING_LABELS } from './couriers/contract.js';
import { planOrder, bucharestDate, bucharestDayStart } from './core/build.js';
import { DEFAULTS, sanitizeSettings, mergeSettings } from './core/settings.js';
import { safeEqual } from './lib/crypto.js';
import { request } from './lib/http.js';
import { toProcessingError } from './core/errors.js';
import { getShopify } from './shopify/index.js';
import * as auth from './shopify/auth.js';
import { startWorker, handlers } from './worker.js';
import { seedDemo, advanceDemo } from './demo/seed.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.disable('x-powered-by');

  // ---------- Shopify webhooks (raw body for HMAC) ----------
  app.post('/webhooks/shopify', express.raw({ type: '*/*', limit: '5mb' }), (req, res) => {
    if (!Buffer.isBuffer(req.body) || !auth.verifyWebhookHmac(req.body, req.get('X-Shopify-Hmac-Sha256'))) return res.status(401).send('invalid hmac');
    res.status(200).send('ok'); // answer fast; Shopify retries on slow responses
    if (!db.firstSeenWebhook(req.get('X-Shopify-Webhook-Id'))) return;
    try {
      handleWebhook(req.get('X-Shopify-Topic'), req.get('X-Shopify-Shop-Domain'), JSON.parse(req.body.toString('utf8')));
    } catch (err) {
      console.error('webhook', err);
    }
  });

  app.use(express.json({ limit: '2mb' }));
  app.use(express.urlencoded({ extended: false }));
  // Express 5 leaves req.body undefined when there is no body; handlers read fields from it.
  app.use((req, res, next) => { req.body ??= {}; next(); });

  // Allow being framed by the Shopify admin only.
  app.use((req, res, next) => {
    const shop = auth.isValidShop(req.query.shop) ? req.query.shop : '';
    res.setHeader('Content-Security-Policy', `frame-ancestors https://admin.shopify.com${shop ? ` https://${shop}` : ''};`);
    res.setHeader('X-Content-Type-Options', 'nosniff');
    next();
  });

  // ---------- OAuth install ----------
  app.get('/auth', (req, res) => {
    const { shop } = req.query;
    if (!auth.isValidShop(shop)) return res.status(400).send('Parametrul shop lipsește sau e invalid (ex: magazin.myshopify.com).');
    const state = auth.newState();
    res.setHeader('Set-Cookie', `expedo_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`);
    res.redirect(auth.installUrl(shop, state));
  });

  app.get('/auth/callback', async (req, res) => {
    const { shop, code, state } = req.query;
    const cookieState = parseCookies(req).expedo_state;
    if (!auth.isValidShop(shop) || !auth.verifyQueryHmac(req.query) || !state || state !== cookieState) {
      return res.status(400).send('Instalarea nu a putut fi verificată. Încearcă din nou din Shopify.');
    }
    try {
      const token = await auth.exchangeCode(shop, code);
      const store = await onInstalled(shop, token);
      res.setHeader('Set-Cookie', `expedo_state=; Path=/; Max-Age=0`);
      res.redirect(`https://${shop}/admin/apps/${config.shopify.apiKey}?installed=${store.id}`);
    } catch (err) {
      console.error(err);
      res.status(500).send('Instalarea a eșuat. Încearcă din nou.');
    }
  });

  // ---------- Standalone login ----------
  app.post('/login', (req, res) => {
    if (!config.adminPassword || !safeEqual(String(req.body.password ?? ''), config.adminPassword)) return res.redirect('/?login=fail');
    const cookie = auth.signSession({ admin: true, exp: Date.now() + 14 * 86400_000 });
    res.setHeader('Set-Cookie', `expedo_session=${cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${14 * 86400}${config.appUrl.startsWith('https') ? '; Secure' : ''}`);
    res.redirect('/');
  });
  app.post('/logout', (req, res) => {
    res.setHeader('Set-Cookie', 'expedo_session=; Path=/; Max-Age=0');
    res.redirect('/');
  });

  app.get('/healthz', (req, res) => res.json({ ok: true }));
  app.use(express.static(join(__dirname, '..', 'public'), { index: false }));
  const indexHtml = readFileSync(join(__dirname, '..', 'public', 'index.html'), 'utf8')
    .replaceAll('%SHOPIFY_API_KEY%', config.shopify.apiKey)
    .replaceAll('%LOGIN_ENABLED%', config.adminPassword ? '1' : '');
  app.get('/', (req, res) => res.type('html').send(indexHtml));

  // ---------- API ----------
  const api = express.Router();
  api.use(resolveStore);

  api.get('/me', (req, res) => {
    res.json({
      store: publicStore(req.store),
      stores: req.session?.admin ? db.listStores().map(publicStore) : [publicStore(req.store)],
      embedded: !!req.embedded,
      testMode: P.isTestMode(req.store),
    });
  });

  api.get('/meta', (req, res) => {
    const describe = (a) => ({ id: a.id, name: a.name, pending: !!a.pending, credentialFields: a.credentialFields, settingsFields: a.settingsFields,
      capabilities: Object.fromEntries(['listPickupPoints', 'listServices', 'listLockers', 'listSeries', 'stornoInvoice', 'registerPayment'].map((k) => [k, typeof a[k] === 'function'])) });
    res.json({
      couriers: Object.values(couriers).filter((c) => c.id !== 'mock').map(describe),
      invoicers: Object.values(invoicers).filter((c) => c.id !== 'mock').map(describe),
      rules: { fields: RULE_FIELDS, ops: RULE_OPS, actions: RULE_ACTIONS },
      statuses: P.ORDER_STATUS,
      tracking: TRACKING_LABELS,
      counties: COUNTIES,
      defaults: DEFAULTS,
    });
  });

  api.get('/orders', (req, res) => {
    const status = qstr(req.query.status) || 'all';
    const q = qstr(req.query.q).trim();
    const courier = qstr(req.query.courier);
    const payment = qstr(req.query.payment);
    const page = Math.max(1, Number.parseInt(qstr(req.query.page), 10) || 1);
    const ids = idList(req.query.ids);
    const where = ['store_id = ?'];
    const args = [req.store.id];
    if (status === 'open') where.push(`status IN ('ready', 'needs_attention', 'on_hold', 'new')`);
    else if (status !== 'all') { where.push('status = ?'); args.push(status); }
    if (courier) { where.push('courier = ?'); args.push(courier); }
    if (payment) { where.push('payment_method = ?'); args.push(payment); }
    if (ids.length) { where.push(`id IN (${ids.map(() => '?').join(',')})`); args.push(...ids); }
    if (q) {
      where.push(`(name LIKE ? ESCAPE '\\' OR awb LIKE ? ESCAPE '\\' OR invoice_number LIKE ? ESCAPE '\\' OR data LIKE ? ESCAPE '\\')`);
      const like = `%${q.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
      args.push(like, like, like, like);
    }
    const limit = 50;
    const offset = (page - 1) * limit;
    const d = db.getDb();
    const rows = d.prepare(`SELECT * FROM orders WHERE ${where.join(' AND ')} ORDER BY created_at DESC LIMIT ? OFFSET ?`).all(...args, limit, offset).map(db.hydrateOrder);
    const total = d.prepare(`SELECT COUNT(*) c FROM orders WHERE ${where.join(' AND ')}`).get(...args).c;
    const counts = Object.fromEntries(d.prepare('SELECT status, COUNT(*) c FROM orders WHERE store_id = ? GROUP BY status').all(req.store.id).map((r) => [r.status, r.c]));
    res.json({ orders: rows.map(orderSummary), total, page, pageSize: limit, counts });
  });

  api.get('/orders/:id', (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const plan = planOrder(order.data, P.storeSettings(req.store), order.overrides);
    const courier = getCourier(order.courier);
    res.json({
      order: { ...orderSummary(order), data: order.data, overrides: order.overrides, trackingUrl: order.awb && courier?.trackingUrl ? courier.trackingUrl(order.awb) : null },
      plan: { courier: plan.courier, service: plan.service, parcels: plan.parcels, weightKg: plan.weightKg, cod: plan.cod, openPackage: plan.openPackage, lockerId: plan.lockerId, matchedRules: plan.matchedRules, address: plan.address, skipInvoice: plan.skipInvoice, hold: plan.hold },
      events: db.orderEvents(order.id),
    });
  });

  // Manual fixes: address, courier, parcels, weight, COD, notes, hold.
  api.patch('/orders/:id', (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const overrides = { ...order.overrides };
    let patch;
    try { patch = cleanOrderPatch(req.body); } catch (err) { return res.status(400).json({ error: { code: 'INVALID', message: err.message } }); }
    for (const [k, v] of Object.entries(patch)) {
      if (v === null) delete overrides[k];
      else overrides[k] = k === 'address' ? { ...(overrides.address || {}), ...v } : v;
    }
    db.updateOrder(order.id, { overrides });
    db.logEvent(req.store.id, order.id, 'info', 'edit', 'Comanda a fost modificată manual.', req.body);
    P.validateOrder(req.store, order.id);
    res.json({ ok: true });
  });

  api.post('/orders/process', async (req, res) => {
    const ids = idList(req.body.ids);
    const steps = Array.isArray(req.body.steps) ? req.body.steps.filter((s) => ['awb', 'invoice', 'fulfill'].includes(s)) : ['awb', 'invoice', 'fulfill'];
    if (!steps.length) return res.status(400).json({ error: { code: 'INVALID', message: 'Pași necunoscuți.' } });
    // Held orders (tag, rule, manual hold) are processed only when asked for explicitly (from the order page),
    // not when they happen to be in a bulk selection.
    const force = req.body.force === true;
    const results = [];
    for (const id of ids) {
      const order = db.getOrder(id);
      if (!order || order.store_id !== req.store.id) continue;
      const r = await P.processOrder(req.store, id, { steps, force }).catch((err) => ({ ok: false, error: toProcessingError(err).toJSON() }));
      results.push({ id, name: order.name, ...r });
    }
    res.json({ results, ok: results.filter((r) => r.ok).length, failed: results.filter((r) => !r.ok).length });
  });

  api.post('/orders/:id/cancel-awb', wrap(async (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    await P.cancelAwb(req.store, order.id);
    res.json({ ok: true });
  }));

  api.post('/orders/:id/storno-invoice', wrap(async (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    await P.stornoInvoice(req.store, order.id);
    res.json({ ok: true });
  }));

  // After going live: drop the test AWB / invoice so the order can be processed for real.
  api.post('/orders/:id/reset-test', wrap(async (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    await P.resetTestData(req.store, order.id);
    res.json({ ok: true });
  }));

  api.post('/orders/:id/refresh', wrap(async (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const fresh = await getShopify(req.store).getOrder(order.shopify_id);
    if (fresh) P.importOrder(req.store, fresh, { source: 'reîmprospătare' });
    else P.validateOrder(req.store, order.id);
    res.json({ ok: true });
  }));

  api.get('/labels.pdf', wrap(async (req, res) => {
    const ids = idList(req.query.ids);
    const { pdf } = await P.mergedLabels(req.store, ids, qstr(req.query.format));
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename="etichete-${bucharestDate()}.pdf"`);
    res.send(pdf);
  }));

  api.get('/orders/:id/invoice.pdf', wrap(async (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const pdf = await P.invoicePdf(req.store, order.id);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename="factura-${`${order.invoice_series}-${order.invoice_number}`.replace(/[^\w.-]+/g, '_')}.pdf"`);
    res.send(pdf);
  }));

  // Picking list: what to take off the shelves for the selected orders.
  api.get('/picking', (req, res) => {
    const ids = idList(req.query.ids);
    const items = new Map();
    const names = [];
    for (const id of ids) {
      const o = db.getOrder(id);
      if (!o || o.store_id !== req.store.id) continue;
      names.push(o.name);
      for (const l of o.data.lines) {
        const key = l.sku || l.title;
        const cur = items.get(key) || { sku: l.sku, title: l.variantTitle ? `${l.title} - ${l.variantTitle}` : l.title, quantity: 0, orders: [] };
        cur.quantity += l.quantity;
        cur.orders.push(o.name);
        items.set(key, cur);
      }
    }
    res.json({ orders: names, items: [...items.values()].sort((a, b) => String(a.sku || a.title).localeCompare(String(b.sku || b.title))) });
  });

  api.get('/stats', (req, res) => {
    const d = db.getDb();
    const s = req.store.id;
    const one = (sql, ...a) => d.prepare(sql).get(s, ...a);
    // "Today" is the merchant's day (Europe/Bucharest), not the UTC one; timestamps are stored as UTC ISO strings.
    const today = bucharestDayStart();
    const days30 = new Date(Date.now() - 30 * 86400_000).toISOString();
    res.json({
      today: one(`SELECT COUNT(*) c, COALESCE(SUM(total),0) v FROM orders WHERE store_id = ? AND created_at >= ?`, today),
      awbToday: one(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND awb_at >= ?`, today).c,
      toProcess: one(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND status = 'ready'`).c,
      attention: one(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND status = 'needs_attention'`).c,
      inTransit: one(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND status IN ('shipped', 'in_transit')`).c,
      codPending: one(`SELECT COUNT(*) c, COALESCE(SUM(cod_amount),0) v FROM orders WHERE store_id = ? AND cod_amount > 0 AND awb IS NOT NULL AND cod_collected_at IS NULL AND status NOT IN ('returned', 'cancelled')`),
      codCollected30: one(`SELECT COUNT(*) c, COALESCE(SUM(cod_amount),0) v FROM orders WHERE store_id = ? AND cod_collected_at >= ?`, days30),
      delivered30: one(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND status = 'delivered' AND awb_at >= ?`, days30).c,
      returned30: one(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND status = 'returned' AND awb_at >= ?`, days30).c,
      shippingCost30: one(`SELECT COALESCE(SUM(shipping_cost),0) v FROM orders WHERE store_id = ? AND awb_at >= ?`, days30).v,
      byCourier: d.prepare(`SELECT courier, COUNT(*) c, SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) delivered, SUM(CASE WHEN status = 'returned' THEN 1 ELSE 0 END) returned
        FROM orders WHERE store_id = ? AND awb IS NOT NULL GROUP BY courier`).all(s),
    });
  });

  // COD reconciliation export: what each courier should transfer.
  api.get('/cod.csv', (req, res) => {
    const rows = db.getDb().prepare(`SELECT name, courier, awb, cod_amount, awb_at, cod_collected_at, status, invoice_series, invoice_number
      FROM orders WHERE store_id = ? AND cod_amount > 0 AND awb IS NOT NULL ORDER BY awb_at DESC`).all(req.store.id);
    const day = (iso) => (iso ? bucharestDate(new Date(iso)) : '');
    const csv = ['Comanda,Curier,AWB,Ramburs,Data AWB,Incasat la,Status,Factura']
      .concat(rows.map((r) => [r.name, r.courier, r.awb, r.cod_amount.toFixed(2), day(r.awb_at), day(r.cod_collected_at), P.ORDER_STATUS[r.status], [r.invoice_series, r.invoice_number].filter(Boolean).join(' ')].map(csvCell).join(',')))
      .join('\n');
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="ramburs.csv"');
    res.send('﻿' + csv);
  });

  api.get('/events', (req, res) => {
    const rows = db.getDb().prepare(`SELECT e.*, o.name order_name FROM events e LEFT JOIN orders o ON o.id = e.order_id
      WHERE e.store_id = ? ORDER BY e.id DESC LIMIT 200`).all(req.store.id);
    res.json({ events: rows.map((e) => ({ ...e, data: e.data ? JSON.parse(e.data) : null })) });
  });

  api.post('/sync', wrap(async (req, res) => {
    const days = Math.min(60, Math.max(1, Number.parseInt(req.body.days, 10) || 14));
    const r = req.store.demo ? { imported: 0 } : await handlers.sync_store(req.store, { days });
    res.json(r);
  }));

  api.post('/track', wrap(async (req, res) => {
    res.json(await P.trackStore(req.store));
  }));

  api.get('/settings', (req, res) => res.json({ settings: P.storeSettings(req.store) }));
  api.put('/settings', (req, res) => {
    let next;
    try { next = mergeSettings(req.store.settings, sanitizeSettings(req.body.settings)); } catch (err) { return res.status(400).json({ error: toProcessingError(err).toJSON() }); }
    if (next.mode === 'live' && req.store.demo) return res.status(400).json({ error: { message: 'Magazinul demo rămâne mereu în modul de probă.' } });
    db.saveStoreSettings(req.store.id, next);
    db.logEvent(req.store.id, null, 'info', 'settings', 'Setările au fost salvate.');
    const store = db.getStore(req.store.id);
    // Re-validate open orders: a new default courier or rule changes what's blocking.
    for (const r of db.getDb().prepare(`SELECT id FROM orders WHERE store_id = ? AND awb IS NULL AND status IN ('ready', 'needs_attention', 'on_hold', 'new')`).all(store.id)) P.validateOrder(store, r.id);
    res.json({ settings: P.storeSettings(store) });
  });

  api.get('/integrations', (req, res) => {
    const list = (kind) => db.listIntegrations(req.store.id, kind).map((i) => ({
      provider: i.provider, enabled: i.enabled, verified_at: i.verified_at, settings: i.settings,
      // never send secrets back, only which ones are filled in
      credentialsSet: Object.fromEntries(Object.keys(i.credentials).map((k) => [k, true])),
    }));
    res.json({ courier: list('courier'), invoicing: list('invoicing') });
  });

  api.put('/integrations/:kind/:provider', (req, res) => {
    const { kind, provider } = req.params;
    if (!integrationAdapter(kind, provider)) return res.status(404).json({ error: { message: 'Integrare necunoscută.' } });
    const plain = (o) => Object.fromEntries(Object.entries(o && typeof o === 'object' && !Array.isArray(o) ? o : {})
      .filter(([, v]) => v == null || ['string', 'number', 'boolean'].includes(typeof v)));
    const i = db.saveIntegration(req.store.id, kind, provider, { credentials: plain(req.body.credentials), settings: plain(req.body.settings), enabled: req.body.enabled !== false });
    db.logEvent(req.store.id, null, 'info', 'settings', `Integrarea ${integrationAdapter(kind, provider).name} a fost salvată.`);
    res.json({ ok: true, enabled: i.enabled });
  });

  api.post('/integrations/:kind/:provider/test', wrap(async (req, res) => {
    const { kind, provider } = req.params;
    const adapter = integrationAdapter(kind, provider);
    const integration = db.getIntegration(req.store.id, kind, provider);
    if (!adapter || !integration) return res.status(404).json({ error: { message: 'Salvează întâi datele de conectare.' } });
    if (adapter.pending) return res.status(400).json({ error: { message: `${adapter.name} e încă în lucru.` } });
    const ctx = { credentials: integration.credentials, settings: integration.settings, http: request, cache: db.storeCache(req.store.id), log: () => {} };
    const r = await adapter.testConnection(ctx);
    db.markIntegrationVerified(req.store.id, kind, provider);
    res.json(r);
  }));

  // Lists the courier/invoicing side offers (pickup points, services, series) to fill settings dropdowns.
  api.get('/integrations/:kind/:provider/options/:what', wrap(async (req, res) => {
    const { kind, provider, what } = req.params;
    const adapter = integrationAdapter(kind, provider);
    const integration = db.getIntegration(req.store.id, kind, provider);
    const fn = { pickupPoints: 'listPickupPoints', services: 'listServices', series: 'listSeries', lockers: 'listLockers' }[what];
    if (!adapter || !integration || !fn || typeof adapter[fn] !== 'function') return res.json({ items: [] });
    const ctx = { credentials: integration.credentials, settings: integration.settings, http: request, cache: db.storeCache(req.store.id), log: () => {} };
    res.json({ items: await adapter[fn](ctx, req.query) });
  }));

  app.use('/api', api);

  // Errors from handlers → Romanian message + hint for the UI.
  app.use((err, req, res, next) => {
    // Body-parser errors (bad JSON, too large) are the client's fault, not ours.
    if (err?.type && err.status >= 400 && err.status < 500) {
      return res.status(err.status).json({ error: { code: 'BAD_REQUEST', message: 'Cererea nu e validă.' } });
    }
    const e = toProcessingError(err);
    if (e.code === 'UNEXPECTED') console.error(err);
    res.status(e.code === 'UNEXPECTED' ? 500 : 400).json({ error: e.toJSON() });
  });

  return app;
}

// ---------- helpers ----------
const wrap = (fn) => (req, res, next) => fn(req, res, next).catch(next);

/** Express 5 query values can be strings or arrays (?a=1&a=2); handlers want one string. */
const qstr = (v) => String((Array.isArray(v) ? v[0] : v) ?? '');
const idList = (v) => (Array.isArray(v) ? v : String(v ?? '').split(',')).map((x) => Number(x)).filter((n) => Number.isInteger(n) && n > 0).slice(0, 500);

/** CSV cell; a leading = + - @ would make Excel run the value as a formula (CSV injection). */
export function csvCell(v) {
  let s = String(v ?? '');
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return `"${s.replace(/"/g, '""')}"`;
}

const ADDRESS_KEYS = ['name', 'firstName', 'lastName', 'company', 'address1', 'address2', 'city', 'province', 'provinceCode', 'zip', 'phone', 'countryCode'];
const NUMBER_LIMITS = { parcels: [1, 99, true], weightKg: [0.01, 1000], cod: [0, 1_000_000] };

/** Validates a manual edit of an order. null / '' = remove the override. Throws with a Romanian message. */
export function cleanOrderPatch(body) {
  const out = {};
  for (const k of ['address', 'courier', 'service', 'parcels', 'weightKg', 'cod', 'notes', 'hold', 'openPackage', 'lockerId', 'skipInvoice']) {
    if (!Object.hasOwn(body, k)) continue;
    const v = body[k];
    if (v === '' || v === null) { out[k] = null; continue; }
    if (k === 'address') {
      if (typeof v !== 'object' || Array.isArray(v)) throw new Error('Adresa nu e validă.');
      out.address = Object.fromEntries(ADDRESS_KEYS.filter((a) => Object.hasOwn(v, a)).map((a) => [a, String(v[a] ?? '').slice(0, 300)]));
    } else if (k in NUMBER_LIMITS) {
      const [min, max, int] = NUMBER_LIMITS[k];
      const n = Number(v);
      if (!Number.isFinite(n) || n < min || n > max || (int && !Number.isInteger(n))) throw new Error(`Valoare greșită pentru ${k}: ${v}.`);
      out[k] = n;
    } else if (['hold', 'openPackage', 'skipInvoice'].includes(k)) {
      if (typeof v !== 'boolean') throw new Error(`Valoare greșită pentru ${k}.`);
      out[k] = v;
    } else if (k === 'courier') {
      if (v === 'mock' || !Object.hasOwn(couriers, v)) throw new Error(`Curier necunoscut: ${v}.`);
      out[k] = v;
    } else {
      out[k] = String(v).slice(0, 500);
    }
  }
  return out;
}

function parseCookies(req) {
  return Object.fromEntries(String(req.headers.cookie || '').split(';').map((c) => c.trim().split('=')).filter((p) => p[0]).map(([k, ...v]) => [k, decodeURIComponent(v.join('='))]));
}

function integrationAdapter(kind, provider) {
  if (provider === 'mock') return null;
  if (kind === 'courier') return Object.hasOwn(couriers, provider) ? getCourier(provider) : null;
  if (kind === 'invoicing') return Object.hasOwn(invoicers, provider) ? getInvoicer(provider) : null;
  return null;
}

function publicStore(s) {
  return { id: s.id, shop: s.shop, name: s.name, demo: s.demo };
}

function ownOrder(req, res) {
  const order = db.getOrder(Number(req.params.id));
  if (!order || order.store_id !== req.store.id) {
    res.status(404).json({ error: { message: 'Comanda nu există.' } });
    return null;
  }
  return order;
}

function orderSummary(o) {
  const d = o.data;
  return {
    id: o.id, name: o.name, createdAt: o.created_at, status: o.status, statusLabel: P.ORDER_STATUS[o.status] || o.status,
    customer: d.customerName, city: d.shippingAddress?.city, county: d.shippingAddress?.province,
    total: o.total, currency: d.currency, paymentMethod: o.payment_method, codAmount: o.cod_amount,
    items: d.lines?.reduce((s, l) => s + l.quantity, 0) || 0, shippingMethod: d.shippingMethod, company: d.company?.name || null,
    courier: o.courier, awb: o.awb, awbAt: o.awb_at, trackingStatus: o.tracking_status, trackingText: o.tracking_text,
    invoice: o.invoice_number ? `${o.invoice_series} ${o.invoice_number}` : null, invoiceUrl: o.invoice_url,
    fulfilledAt: o.fulfilled_at, codCollectedAt: o.cod_collected_at, issues: o.issues, lastError: o.last_error,
    testMode: o.test_mode, invoiceTest: o.invoice_test, hold: !!o.overrides?.hold, tags: d.tags, cancelled: !!d.cancelledAt,
  };
}

/** Works out which store the request is for: Shopify session token (embedded) or admin cookie (standalone). */
async function resolveStore(req, res, next) {
  try {
    const bearer = (req.get('Authorization') || '').replace(/^Bearer\s+/i, '');
    if (bearer) {
      const v = auth.verifySessionToken(bearer);
      if (!v) return res.status(401).json({ error: { code: 'SESSION_INVALID', message: 'Sesiunea Shopify a expirat. Reîncarcă pagina.' } });
      let store = db.getStoreByShop(v.shop);
      if (!store?.accessToken || store.uninstalled_at) {
        // Embedded first load (Shopify managed install): get an offline token via token exchange.
        const token = await auth.exchangeSessionToken(v.shop, bearer);
        store = await onInstalled(v.shop, token);
      }
      req.store = store;
      req.embedded = true;
      return next();
    }
    const session = auth.readSession(parseCookies(req).expedo_session);
    const autoDemo = config.demo && !config.adminPassword;
    if (!session?.admin && !autoDemo) return res.status(401).json({ error: { code: 'LOGIN_REQUIRED', message: 'Autentifică-te.' } });
    // Cookie auth: a cross-site form or image can carry the cookie, but cannot set a custom header
    // (that needs a CORS preflight we never allow). So every write must come from our own fetch().
    if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method) && req.get('X-Expedo-Request') !== '1') {
      return res.status(403).json({ error: { code: 'CSRF', message: 'Cerere respinsă. Reîncarcă pagina.' } });
    }
    req.session = session || { admin: true };
    const wanted = Number(req.get('X-Store-Id') || qstr(req.query.storeId));
    // Open demo mode (no password) only ever exposes the demo store, never a real one in the same database.
    const stores = db.listStores().filter((st) => session?.admin || st.demo);
    req.store = stores.find((s) => s.id === wanted) || stores.find((s) => !s.demo) || stores[0];
    if (!req.store) return res.status(404).json({ error: { code: 'NO_STORE', message: 'Niciun magazin conectat. Instalează aplicația din Shopify.' } });
    next();
  } catch (err) {
    next(err);
  }
}

async function onInstalled(shop, token) {
  let store = db.upsertStore({ shop, accessToken: token.access_token, scopes: token.scope });
  const client = getShopify(store);
  try {
    const info = await client.shopInfo();
    db.getDb().prepare('UPDATE stores SET name = ? WHERE id = ?').run(info.name, store.id);
    await client.registerWebhooks(config.appUrl);
  } catch (err) {
    console.error('post-install', err);
  }
  store = db.getStore(store.id);
  db.logEvent(store.id, null, 'success', 'install', 'Aplicația a fost conectată la magazin.');
  // Own key: the periodic 3-day re-sync (key sync:<id>) may already be pending and must not swallow this one.
  P.enqueue(store.id, 'sync_store', { days: 14 }, { key: `initial_sync:${store.id}` });
  return store;
}

function handleWebhook(topic, shop, payload) {
  const store = db.getStoreByShop(shop);
  if (!store) return;
  // The HMAC covers the body, not the headers: the shop named in the body must match the header.
  const bodyShop = payload?.myshopify_domain || payload?.shop_domain;
  if (bodyShop && bodyShop !== shop) return;
  switch (topic) {
    case 'orders/create':
    case 'orders/updated':
    case 'orders/cancelled':
      // Collapse bursts of updates into one fetch of the full order.
      P.enqueue(store.id, 'sync_order', { gid: payload.admin_graphql_api_id }, { key: `sync_order:${payload.admin_graphql_api_id}`, runAt: new Date(Date.now() + 3000).toISOString() });
      break;
    case 'app/uninstalled':
      db.getDb().prepare(`UPDATE stores SET uninstalled_at = datetime('now'), access_token = NULL WHERE id = ?`).run(store.id);
      break;
    case 'shop/redact':
      // events / jobs / cache have no foreign key to stores; they hold customer data too.
      for (const t of ['events', 'jobs', 'cache']) db.getDb().prepare(`DELETE FROM ${t} WHERE store_id = ?`).run(store.id);
      db.getDb().prepare('DELETE FROM stores WHERE id = ?').run(store.id);
      break;
    case 'customers/redact':
      for (const id of payload.orders_to_redact || []) {
        const o = db.getOrderByShopifyId(store.id, `gid://shopify/Order/${id}`);
        if (!o) continue;
        db.getDb().prepare('DELETE FROM events WHERE order_id = ?').run(o.id);
        db.getDb().prepare('DELETE FROM orders WHERE id = ?').run(o.id);
      }
      break;
    default:
      break; // customers/data_request: we only hold order data already visible in Shopify
  }
}

// ---------- boot ----------
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  db.openDb();
  if (config.demo) {
    const { store, created } = seedDemo();
    if (created) await advanceDemo(store, P.processOrder);
  }
  // Own-organization stores (client credentials): make sure they exist and get an initial sync.
  for (const shop of config.shopify.ownStores) {
    if (!auth.isValidShop(shop)) continue;
    const existing = db.getStoreByShop(shop);
    if (!existing || existing.uninstalled_at) {
      const store = db.upsertStore({ shop, name: shop });
      P.enqueue(store.id, 'sync_store', { days: 30 }, { key: `sync:${store.id}` });
    }
  }
  startWorker();
  createApp().listen(config.port, () => {
    console.log(`Expedo pornit pe ${config.appUrl}${config.demo ? ' (mod demo)' : ''}`);
  });
}
