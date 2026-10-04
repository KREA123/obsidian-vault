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
import { TrackingStatus } from './couriers/contract.js';
import { planOrder, bucharestDate, bucharestDayStart } from './core/build.js';
import { DEFAULTS, sanitizeSettings, mergeSettings } from './core/settings.js';
import { safeEqual } from './lib/crypto.js';
import { request } from './lib/http.js';
import { ProcessingError, toProcessingError, renderError } from './core/errors.js';
import { t, m, has, catalogs, clientCatalog, requestLocale, acceptLanguageLocale, normalizeLocale, LOCALES } from './i18n/index.js';
import { getShopify } from './shopify/index.js';
import * as auth from './shopify/auth.js';
import { startWorker, handlers } from './worker.js';
import { seedDemo, advanceDemo } from './demo/seed.js';
import { searchHashes } from './core/identity.js';
import { customerHistory } from './core/customers.js';
import * as privacy from './core/privacy.js';
import { legalPage } from './legal.js';
import { can, planSummary, refreshPlan, minPlanFor, PLANS } from './core/plans.js';

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
    if (!auth.isValidShop(shop)) return res.status(400).send(t(acceptLanguageLocale(req.get('Accept-Language')), 'server.shopInvalid'));
    const state = auth.newState();
    res.setHeader('Set-Cookie', `expedo_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`);
    res.redirect(auth.installUrl(shop, state));
  });

  app.get('/auth/callback', async (req, res) => {
    const { shop, code, state } = req.query;
    const cookieState = parseCookies(req).expedo_state;
    if (!auth.isValidShop(shop) || !auth.verifyQueryHmac(req.query) || !state || state !== cookieState) {
      return res.status(400).send(t(acceptLanguageLocale(req.get('Accept-Language')), 'server.installUnverified'));
    }
    try {
      const token = await auth.exchangeCode(shop, code);
      const store = await onInstalled(shop, token);
      res.setHeader('Set-Cookie', `expedo_state=; Path=/; Max-Age=0`);
      res.redirect(`https://${shop}/admin/apps/${config.shopify.apiKey}?installed=${store.id}`);
    } catch (err) {
      console.error(err);
      res.status(500).send(t(acceptLanguageLocale(req.get('Accept-Language')), 'server.installFailed'));
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
  // Public pages (no login): linked from the app listing, the app footer and Settings.
  for (const [path, page, lang] of [['/confidentialitate', 'privacy', 'ro'], ['/privacy', 'privacy', 'en'], ['/termeni', 'terms', 'ro'], ['/terms', 'terms', 'en']]) {
    app.get(path, (req, res) => res.type('html').send(legalPage(page, lang)));
  }
  app.use(express.static(join(__dirname, '..', 'public'), { index: false }));
  // i18n for the SPA: the same engine as the server (src/i18n/core.js) and the `ui.` part of a catalog.
  const i18nCore = readFileSync(join(__dirname, 'i18n', 'core.js'), 'utf8');
  app.get('/i18n/core.js', (req, res) => res.type('text/javascript').send(i18nCore));
  app.get('/i18n/:locale.json', (req, res) => {
    const locale = LOCALES.includes(req.params.locale) ? req.params.locale : null;
    if (!locale) return res.status(404).json({});
    res.setHeader('Cache-Control', 'no-cache');
    res.json(clientCatalog(locale));
  });
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
      // Pricing plan, usage this period, trial, the Shopify plan page (core/plans.js).
      plan: planSummary(req.store),
      // Language the API answers in; the SPA loads the matching catalog.
      locale: req.locale,
    });
  });

  api.get('/meta', (req, res) => {
    const L = req.locale;
    // Field labels / help / option labels of an adapter live in the catalogs: <provider>.fields.<key>.(label|help|options.<value>).
    const field = (a) => (f) => {
      const base = `${a.id}.fields.${f.key}`;
      return {
        ...f,
        label: has(`${base}.label`) ? t(L, `${base}.label`) : f.label || f.key,
        help: has(`${base}.help`) ? t(L, `${base}.help`) : f.help,
        ...(f.options ? { options: f.options.map((o) => ({ ...o, label: has(`${base}.options.${o.value}`) ? t(L, `${base}.options.${o.value}`) : o.label })) } : {}),
      };
    };
    const describe = (a) => ({ id: a.id, name: a.name, pending: !!a.pending, credentialFields: a.credentialFields.map(field(a)), settingsFields: a.settingsFields.map(field(a)),
      capabilities: Object.fromEntries(['listPickupPoints', 'listServices', 'listLockers', 'listSeries', 'stornoInvoice', 'registerPayment'].map((k) => [k, typeof a[k] === 'function'])) });
    const labels = (obj) => Object.fromEntries(Object.entries(obj).map(([k, key]) => [k, t(L, key)]));
    res.json({
      couriers: Object.values(couriers).filter((c) => c.id !== 'mock').map(describe),
      invoicers: Object.values(invoicers).filter((c) => c.id !== 'mock').map(describe),
      rules: {
        fields: Object.fromEntries(Object.entries(RULE_FIELDS).map(([k, f]) => [k, {
          ...f, label: t(L, `rules.fields.${k}`),
          // A field the plan doesn't include: shown, not selectable ("Available on Pro Max").
          ...(k === 'refusedBefore' && !can(req.store, 'refusalHistory') ? { locked: PLANS[minPlanFor('refusalHistory')].name } : {}),
          ...(f.options ? { options: f.options.map((v) => [v, t(L, `rules.values.${k}.${v}`)]) } : {}),
        }])),
        ops: labels(RULE_OPS),
        actions: labels(RULE_ACTIONS),
      },
      statuses: Object.fromEntries(P.ORDER_STATUSES.map((s) => [s, t(L, `status.${s}`)])),
      tracking: Object.fromEntries(Object.values(TrackingStatus).map((s) => [s, t(L, `tracking.${s}`)])),
      counties: COUNTIES,
      defaults: DEFAULTS,
      accessActions: labels(privacy.ACCESS_ACTIONS),
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
      // Order number, AWB and invoice are plain columns. Customer data is encrypted: a phone, an e-mail or
      // whole name words are found through their keyed hashes (core/identity.js), exact matches only.
      const like = `%${q.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
      const terms = [`name LIKE ? ESCAPE '\\'`, `awb LIKE ? ESCAPE '\\'`, `invoice_number LIKE ? ESCAPE '\\'`];
      args.push(like, like, like);
      const { any, words } = searchHashes(req.store.id, q);
      const has = `(' ' || COALESCE(search_terms, '') || ' ') LIKE ?`;
      for (const h of any) { terms.push(has); args.push(`% ${h} %`); }
      if (words.length) { terms.push(`(${words.map(() => has).join(' AND ')})`); args.push(...words.map((h) => `% ${h} %`)); }
      where.push(`(${terms.join(' OR ')})`);
    }
    const limit = 50;
    const offset = (page - 1) * limit;
    const d = db.getDb();
    const rows = d.prepare(`SELECT * FROM orders WHERE ${where.join(' AND ')} ORDER BY created_at DESC LIMIT ? OFFSET ?`).all(...args, limit, offset).map(db.hydrateOrder);
    const total = d.prepare(`SELECT COUNT(*) c FROM orders WHERE ${where.join(' AND ')}`).get(...args).c;
    const counts = Object.fromEntries(d.prepare('SELECT status, COUNT(*) c FROM orders WHERE store_id = ? GROUP BY status').all(req.store.id).map((r) => [r.status, r.c]));
    // Small badge for customers who refused parcels before (one indexed lookup per row).
    const history = can(req.store, 'refusalHistory');
    const orders = rows.map((o) => ({ ...orderSummary(o, req.locale), refusedBefore: o.redacted_at || !history ? 0 : customerHistory(req.store, o, { limit: 0 }).returned }));
    res.json({ orders, total, page, pageSize: limit, counts });
  });

  api.get('/orders/:id', (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const opts = P.historyOptions(req.store, order);
    const history = opts.history;
    const plan = planOrder(order.data, P.storeSettings(req.store), order.overrides, opts);
    const courier = getCourier(order.courier);
    db.logAccess(req.store.id, { actor: req.actor, action: 'order_view', orderId: order.id, orderName: order.name });
    res.json({
      order: { ...orderSummary(order, req.locale), data: order.data, overrides: order.overrides, trackingUrl: order.awb && courier?.trackingUrl ? courier.trackingUrl(order.awb) : null },
      plan: { courier: plan.courier, service: plan.service, parcels: plan.parcels, weightKg: plan.weightKg, cod: plan.cod, openPackage: plan.openPackage, lockerId: plan.lockerId, matchedRules: plan.matchedRules, address: plan.address, skipInvoice: plan.skipInvoice, hold: plan.hold },
      // Refusal history is a plan feature: null (and customerLocked) on plans without it.
      customer: history ? { returned: history.returned, refusedCod: history.refusedCod, delivered: history.delivered, orders: history.orders } : null,
      customerLocked: !history ? PLANS[minPlanFor('refusalHistory')].name : null,
      events: db.orderEvents(order.id).map((e) => db.renderEvent(e, req.locale)),
    });
  });

  // Manual fixes: address, courier, parcels, weight, COD, notes, hold.
  api.patch('/orders/:id', (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const overrides = { ...order.overrides };
    let patch;
    try { patch = cleanOrderPatch(req.body); } catch (err) { return res.status(400).json({ error: renderError(toProcessingError(err), req.locale) }); }
    for (const [k, v] of Object.entries(patch)) {
      if (v === null) delete overrides[k];
      else overrides[k] = k === 'address' ? { ...(overrides.address || {}), ...v } : v;
    }
    db.updateOrder(order.id, { overrides });
    db.logEvent(req.store.id, order.id, 'info', 'edit', m('events.edited'), req.body);
    P.validateOrder(req.store, order.id);
    res.json({ ok: true });
  });

  api.post('/orders/process', async (req, res) => {
    const ids = idList(req.body.ids);
    const steps = Array.isArray(req.body.steps) ? req.body.steps.filter((s) => ['awb', 'invoice', 'fulfill'].includes(s)) : ['awb', 'invoice', 'fulfill'];
    if (!steps.length) return sendError(req, res, 400, 'STEPS_UNKNOWN');
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
    res.json({
      results: results.map((r) => (r.error ? { ...r, error: renderError(r.error, req.locale) } : r)),
      ok: results.filter((r) => r.ok).length, failed: results.filter((r) => !r.ok).length,
    });
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
    if (fresh) P.importOrder(req.store, fresh, { source: 'refresh' });
    else P.validateOrder(req.store, order.id);
    res.json({ ok: true });
  }));

  api.get('/labels.pdf', wrap(async (req, res) => {
    const ids = idList(req.query.ids);
    const { pdf } = await P.mergedLabels(req.store, ids, qstr(req.query.format));
    for (const id of ids) {
      const o = db.getOrder(id);
      if (o?.store_id === req.store.id && o.awb) db.logAccess(req.store.id, { actor: req.actor, action: 'labels', orderId: o.id, orderName: o.name, detail: m('access.detail.awb', { awb: o.awb }) });
    }
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename="${t(req.locale, 'server.files.labels')}-${bucharestDate()}.pdf"`);
    res.send(pdf);
  }));

  api.get('/orders/:id/invoice.pdf', wrap(async (req, res) => {
    const order = ownOrder(req, res);
    if (!order) return;
    const pdf = await P.invoicePdf(req.store, order.id);
    db.logAccess(req.store.id, { actor: req.actor, action: 'invoice_pdf', orderId: order.id, orderName: order.name });
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename="${t(req.locale, 'server.files.invoice')}-${`${order.invoice_series}-${order.invoice_number}`.replace(/[^\w.-]+/g, '_')}.pdf"`);
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
      db.logAccess(req.store.id, { actor: req.actor, action: 'picking', orderId: o.id, orderName: o.name });
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
    // The dashboard hides the button on plans without it; a direct call gets a clear answer.
    if (!can(req.store, 'codExport')) return sendError(req, res, 403, 'PLAN_FEATURE_LOCKED', { plan: PLANS[minPlanFor('codExport')].name });
    const rows = db.getDb().prepare(`SELECT name, courier, awb, cod_amount, awb_at, cod_collected_at, status, invoice_series, invoice_number
      FROM orders WHERE store_id = ? AND cod_amount > 0 AND awb IS NOT NULL ORDER BY awb_at DESC`).all(req.store.id);
    const day = (iso) => (iso ? bucharestDate(new Date(iso)) : '');
    // Amounts stay machine-readable (149.90) in both languages; headers and statuses are translated.
    const csv = [t(req.locale, 'server.csv.codHeader')]
      .concat(rows.map((r) => [r.name, r.courier, r.awb, r.cod_amount.toFixed(2), day(r.awb_at), day(r.cod_collected_at), has(`status.${r.status}`) ? t(req.locale, `status.${r.status}`) : r.status, [r.invoice_series, r.invoice_number].filter(Boolean).join(' ')].map(csvCell).join(',')))
      .join('\n');
    db.logAccess(req.store.id, { actor: req.actor, action: 'cod_export', detail: m('access.detail.rows', { count: rows.length }) });
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="${t(req.locale, 'server.files.cod')}.csv"`);
    res.send('﻿' + csv);
  });

  api.get('/events', (req, res) => {
    res.json({ events: db.storeEvents(req.store.id, 200).map((e) => db.renderEvent(e, req.locale)) });
  });

  // Who saw or exported customer data (Activity → Data access).
  api.get('/access-log', (req, res) => {
    const action = qstr(req.query.action);
    const page = Math.max(1, Number.parseInt(qstr(req.query.page), 10) || 1);
    const limit = 100;
    const { rows, total } = db.listAccess(req.store.id, {
      action: Object.hasOwn(privacy.ACCESS_ACTIONS, action) ? action : '', order: qstr(req.query.order).trim().slice(0, 50), limit, offset: (page - 1) * limit,
    });
    res.json({ entries: rows.map((r) => ({ ...r, detail: db.renderAccessDetail(r.detail, req.locale) })), total, page, pageSize: limit, keepDays: privacy.ACCESS_LOG_DAYS });
  });

  // Everything we hold about the given orders, for a customer's data request (logged).
  api.get('/customer-export', (req, res) => {
    const orders = idList(req.query.ids).map((id) => db.getOrder(id)).filter((o) => o?.store_id === req.store.id);
    if (!orders.length) return sendError(req, res, 404, 'ORDER_NOT_FOUND');
    for (const o of orders) db.logAccess(req.store.id, { actor: req.actor, action: 'customer_export', orderId: o.id, orderName: o.name });
    const data = privacy.customerExport(req.store, orders.map((o) => o.id), req.locale);
    res.setHeader('Content-Disposition', `attachment; filename="${t(req.locale, 'server.files.customerData')}-${bucharestDate()}.json"`);
    res.json(data);
  });

  api.post('/sync', wrap(async (req, res) => {
    const days = Math.min(60, Math.max(1, Number.parseInt(req.body.days, 10) || 14));
    const r = req.store.demo ? { imported: 0 } : await handlers.sync_store(req.store, { days });
    res.json(r);
  }));

  api.post('/track', wrap(async (req, res) => {
    res.json(await P.trackStore(req.store));
  }));

  // Plan and usage; POST re-checks with Shopify (after the merchant comes back from the plan page).
  api.get('/plan', (req, res) => res.json({ plan: planSummary(req.store) }));
  api.post('/plan/refresh', wrap(async (req, res) => {
    let store = req.store;
    const last = Date.parse(store.plan_checked_at || '');
    if (!(Number.isFinite(last) && Date.now() - last < 15_000)) store = await refreshPlan(store, getShopify(store), { source: 'manual' });
    res.json({ plan: planSummary(store) });
  }));

  api.get('/settings', (req, res) => res.json({ settings: P.storeSettings(req.store) }));
  api.put('/settings', (req, res) => {
    let next;
    try { next = mergeSettings(req.store.settings, sanitizeSettings(req.body.settings)); } catch (err) { return res.status(400).json({ error: renderError(toProcessingError(err), req.locale) }); }
    if (next.mode === 'live' && req.store.demo) return sendError(req, res, 400, 'DEMO_TEST_ONLY');
    db.saveStoreSettings(req.store.id, next);
    db.logEvent(req.store.id, null, 'info', 'settings', m('events.settingsSaved'));
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
    if (!integrationAdapter(kind, provider)) return sendError(req, res, 404, 'INTEGRATION_UNKNOWN');
    const plain = (o) => Object.fromEntries(Object.entries(o && typeof o === 'object' && !Array.isArray(o) ? o : {})
      .filter(([, v]) => v == null || ['string', 'number', 'boolean'].includes(typeof v)));
    const i = db.saveIntegration(req.store.id, kind, provider, { credentials: plain(req.body.credentials), settings: plain(req.body.settings), enabled: req.body.enabled !== false });
    db.logEvent(req.store.id, null, 'info', 'settings', m('events.integrationSaved', { provider: integrationAdapter(kind, provider).name }));
    res.json({ ok: true, enabled: i.enabled });
  });

  api.post('/integrations/:kind/:provider/test', wrap(async (req, res) => {
    const { kind, provider } = req.params;
    const adapter = integrationAdapter(kind, provider);
    const integration = db.getIntegration(req.store.id, kind, provider);
    if (!adapter || !integration) return sendError(req, res, 404, 'INTEGRATION_NOT_SAVED');
    if (adapter.pending) return sendError(req, res, 400, 'INTEGRATION_PENDING', { provider: adapter.name });
    const ctx = { credentials: integration.credentials, settings: integration.settings, http: request, cache: db.storeCache(req.store.id), log: () => {}, locale: req.locale };
    const r = await adapter.testConnection(ctx);
    db.markIntegrationVerified(req.store.id, kind, provider);
    // Adapters answer with a message { key, params } (src/i18n), rendered here in the viewer's language.
    res.json({ ...r, message: t(req.locale, r.message) });
  }));

  // Lists the courier/invoicing side offers (pickup points, services, series) to fill settings dropdowns.
  api.get('/integrations/:kind/:provider/options/:what', wrap(async (req, res) => {
    const { kind, provider, what } = req.params;
    const adapter = integrationAdapter(kind, provider);
    const integration = db.getIntegration(req.store.id, kind, provider);
    const fn = { pickupPoints: 'listPickupPoints', services: 'listServices', series: 'listSeries', lockers: 'listLockers' }[what];
    if (!adapter || !integration || !fn || typeof adapter[fn] !== 'function') return res.json({ items: [] });
    const ctx = { credentials: integration.credentials, settings: integration.settings, http: request, cache: db.storeCache(req.store.id), log: () => {}, locale: req.locale };
    res.json({ items: await adapter[fn](ctx, req.query) });
  }));

  app.use('/api', api);

  // Errors from handlers → message + hint for the UI, in the viewer's language.
  app.use((err, req, res, next) => {
    const locale = req.locale || fallbackLocale(req);
    // Body-parser errors (bad JSON, too large) are the client's fault, not ours.
    if (err?.type && err.status >= 400 && err.status < 500) {
      return res.status(err.status).json({ error: renderError(new ProcessingError({ code: 'BAD_REQUEST' }), locale) });
    }
    const e = toProcessingError(err);
    if (e.code === 'UNEXPECTED') console.error(err);
    res.status(e.code === 'UNEXPECTED' ? 500 : 400).json({ error: renderError(e, locale) });
  });

  return app;
}

// ---------- helpers ----------
const wrap = (fn) => (req, res, next) => fn(req, res, next).catch(next);

/** Language before the store is known (login, bad session): what the Shopify admin / browser says. */
const fallbackLocale = (req) => (req.get('X-Expedo-Locale') ? normalizeLocale(req.get('X-Expedo-Locale')) : acceptLanguageLocale(req.get('Accept-Language')));

/** JSON error answer { error: { code, message, hint } } with the text in the request's language. */
function sendError(req, res, status, code, params) {
  return res.status(status).json({ error: renderError(new ProcessingError({ code, params }), req.locale || fallbackLocale(req)) });
}

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

/** Validates a manual edit of an order. null / '' = remove the override. Throws ProcessingError INVALID_EDIT. */
export function cleanOrderPatch(body) {
  const out = {};
  for (const k of ['address', 'courier', 'service', 'parcels', 'weightKg', 'cod', 'notes', 'hold', 'openPackage', 'lockerId', 'skipInvoice']) {
    if (!Object.hasOwn(body, k)) continue;
    const v = body[k];
    if (v === '' || v === null) { out[k] = null; continue; }
    if (k === 'address') {
      if (typeof v !== 'object' || Array.isArray(v)) throw new ProcessingError({ code: 'INVALID_EDIT', key: 'errors.INVALID_EDIT.address' });
      out.address = Object.fromEntries(ADDRESS_KEYS.filter((a) => Object.hasOwn(v, a)).map((a) => [a, String(v[a] ?? '').slice(0, 300)]));
    } else if (k in NUMBER_LIMITS) {
      const [min, max, int] = NUMBER_LIMITS[k];
      const n = Number(v);
      if (!Number.isFinite(n) || n < min || n > max || (int && !Number.isInteger(n))) throw new ProcessingError({ code: 'INVALID_EDIT', key: 'errors.INVALID_EDIT.value', params: { field: k, value: String(v) } });
      out[k] = n;
    } else if (['hold', 'openPackage', 'skipInvoice'].includes(k)) {
      if (typeof v !== 'boolean') throw new ProcessingError({ code: 'INVALID_EDIT', key: 'errors.INVALID_EDIT.flag', params: { field: k } });
      out[k] = v;
    } else if (k === 'courier') {
      if (v === 'mock' || !Object.hasOwn(couriers, v)) throw new ProcessingError({ code: 'INVALID_EDIT', key: 'errors.INVALID_EDIT.courier', params: { courier: String(v) } });
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
    sendError(req, res, 404, 'ORDER_NOT_FOUND');
    return null;
  }
  return order;
}

/** Romanian tracking labels older versions stored in tracking_text: not the courier's own words. */
const OLD_TRACKING_LABELS = new Set(Object.values(TrackingStatus).map((s) => catalogs.ro[`tracking.${s}`]));

function orderSummary(o, locale) {
  const d = o.data;
  return {
    id: o.id, name: o.name, createdAt: o.created_at, status: o.status, statusLabel: has(`status.${o.status}`) ? t(locale, `status.${o.status}`) : o.status,
    customer: d.customerName, city: d.shippingAddress?.city, county: d.shippingAddress?.province,
    total: o.total, currency: d.currency, paymentMethod: o.payment_method, codAmount: o.cod_amount,
    items: d.lines?.reduce((s, l) => s + l.quantity, 0) || 0, shippingMethod: d.shippingMethod, company: d.company?.name || null,
    // trackingText: the status in the viewer's language; trackingDetail: the courier's own words, when they add something.
    courier: o.courier, awb: o.awb, awbAt: o.awb_at, trackingStatus: o.tracking_status,
    trackingText: o.tracking_status ? t(locale, `tracking.${o.tracking_status}`) : o.tracking_text,
    trackingDetail: o.tracking_status && o.tracking_text && !OLD_TRACKING_LABELS.has(o.tracking_text) ? o.tracking_text : null,
    invoice: o.invoice_number ? `${o.invoice_series} ${o.invoice_number}` : null, invoiceUrl: o.invoice_url,
    fulfilledAt: o.fulfilled_at, codCollectedAt: o.cod_collected_at,
    issues: (o.issues || []).map((i) => renderError(i, locale)), lastError: o.last_error ? renderError(o.last_error, locale) : null,
    testMode: o.test_mode, invoiceTest: o.invoice_test, hold: !!o.overrides?.hold, tags: d.tags, cancelled: !!d.cancelledAt,
    redactedAt: o.redacted_at || null,
  };
}

/** Works out which store the request is for: Shopify session token (embedded) or admin cookie (standalone). */
async function resolveStore(req, res, next) {
  try {
    const bearer = (req.get('Authorization') || '').replace(/^Bearer\s+/i, '');
    if (bearer) {
      const v = auth.verifySessionToken(bearer);
      if (!v) return sendError(req, res, 401, 'SESSION_INVALID');
      let store = db.getStoreByShop(v.shop);
      if (!store?.accessToken || store.uninstalled_at) {
        // Embedded first load (Shopify managed install): get an offline token via token exchange.
        const token = await auth.exchangeSessionToken(v.shop, bearer);
        store = await onInstalled(v.shop, token);
      }
      req.store = store;
      req.embedded = true;
      // Inside the Shopify admin: the admin user's language (App Bridge locale, sent by the SPA).
      req.locale = requestLocale({ embedded: true, embeddedLocale: req.get('X-Expedo-Locale') || qstr(req.query.locale), store });
      // The Shopify staff member (session token `sub`), for the access log.
      req.actor = `shopify-session ${v.payload.sub || '?'}`;
      return next();
    }
    const session = auth.readSession(parseCookies(req).expedo_session);
    const autoDemo = config.demo && !config.adminPassword;
    if (!session?.admin && !autoDemo) return sendError(req, res, 401, 'LOGIN_REQUIRED');
    // Cookie auth: a cross-site form or image can carry the cookie, but cannot set a custom header
    // (that needs a CORS preflight we never allow). So every write must come from our own fetch().
    if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method) && req.get('X-Expedo-Request') !== '1') {
      return sendError(req, res, 403, 'CSRF');
    }
    req.session = session || { admin: true };
    req.actor = 'admin';
    const wanted = Number(req.get('X-Store-Id') || qstr(req.query.storeId));
    // Open demo mode (no password) only ever exposes the demo store, never a real one in the same database.
    const stores = db.listStores().filter((st) => session?.admin || st.demo);
    req.store = stores.find((s) => s.id === wanted) || stores.find((s) => !s.demo) || stores[0];
    if (!req.store) return sendError(req, res, 404, 'NO_STORE');
    // Standalone dashboard: the store's "Language" setting (English by default).
    req.locale = requestLocale({ embedded: false, store: req.store });
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
  try {
    await refreshPlan(db.getStore(store.id), client, { source: 'install' });
  } catch (err) {
    console.error('post-install plan', err);
  }
  store = db.getStore(store.id);
  db.logEvent(store.id, null, 'success', 'install', m('events.installed'));
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
    case 'app_subscriptions/update':
      // Plan changed (or canceled / frozen): re-read it from Shopify rather than trusting the payload alone.
      P.enqueue(store.id, 'refresh_plan', { force: true }, { key: `plan_now:${store.id}`, maxAttempts: 2 });
      break;
    case 'app/uninstalled':
      db.getDb().prepare(`UPDATE stores SET uninstalled_at = datetime('now'), access_token = NULL WHERE id = ?`).run(store.id);
      break;
    // GDPR (mandatory compliance webhooks): core/privacy.js
    case 'shop/redact':
      privacy.handleShopRedact(store);
      break;
    case 'customers/redact':
      privacy.handleCustomerRedact(store, payload);
      break;
    case 'customers/data_request':
      privacy.handleDataRequest(store, payload);
      break;
    default:
      break;
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
    console.log(`Expedo running on ${config.appUrl}${config.demo ? ' (demo mode)' : ''}`);
  });
}
