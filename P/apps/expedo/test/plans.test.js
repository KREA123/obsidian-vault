import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { PDFDocument } from 'pdf-lib';
import { config } from '../src/config.js';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { createApp } from '../src/server.js';
import { couriers } from '../src/couriers/index.js';
import { invoicers } from '../src/invoicing/index.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import { shopifyClient, adminSubscription, partnerSubscription } from '../src/shopify/client.js';
import { handlers, schedulePeriodic } from '../src/worker.js';
import { t } from '../src/i18n/index.js';
import {
  PLANS, TRIAL_DAYS, planIdFromName, planIdFor, planFor, can, usageThisPeriod, billingPeriod, planSummary, upgradeUrl, refreshPlan, applySubscription, minPlanFor,
} from '../src/core/plans.js';

// Pricing plans (core/plans.js): Pro / Pro Max, no plan ('none' → PLAN_REQUIRED), name mapping (old ids too),
// usage per billing period, the Pro limit in the pipeline, feature gating, the subscription webhook, the API,
// and demo / own stores on Pro Max.

const SECRET = 'plans-secret';
let server, base, demo, store, seq = 0;
const calls = { createShipment: 0, cancelShipment: 0, createInvoice: 0, storno: 0 };
const fakeCourier = {
  id: 'fakeplan', name: 'Fake courier', trackingUrl: (awb) => `https://fake.example/${awb}`, credentialFields: [], settingsFields: [],
  async testConnection() { return { ok: true }; },
  async createShipment() { calls.createShipment++; return { awb: `LIVE${calls.createShipment}`, price: 20 }; },
  async getLabel() { const d = await PDFDocument.create(); d.addPage(); return Buffer.from(await d.save()); },
  async cancelShipment() { calls.cancelShipment++; },
  async track(ctx, awbs) { return awbs.map((awb) => ({ awb, status: TrackingStatus.IN_TRANSIT })); },
};
const fakeInvoicer = {
  id: 'fakeplaninv', name: 'Fake invoicing', credentialFields: [], settingsFields: [],
  async testConnection() { return { ok: true }; },
  async createInvoice() { calls.createInvoice++; return { series: 'PL', number: String(calls.createInvoice) }; },
  async getPdf() { return Buffer.from('%PDF'); },
  async cancelInvoice() {},
  async stornoInvoice() { calls.storno++; return { series: 'PL', number: `S${calls.storno}` }; },
};

function normalized(extra = {}) {
  seq++;
  const addr = { firstName: 'Ion', lastName: 'Pop', name: 'Ion Pop', company: '', address1: 'Str. Lunga 1', address2: '', city: 'Brasov', province: 'Brasov', provinceCode: 'BV', zip: '500096', countryCode: 'RO', phone: '0744111222' };
  return {
    shopifyId: `gid://shopify/Order/${5000 + seq}`, name: `#P${seq}`, createdAt: new Date().toISOString(), cancelledAt: null,
    currency: 'RON', financialStatus: 'PENDING', fulfillmentStatus: 'UNFULFILLED', paymentMethod: 'cod',
    total: 125, subtotal: 100, shippingTotal: 25, outstanding: 125, codAmount: 125, email: 'ion@example.com', phone: addr.phone,
    customerName: 'Ion Pop', shippingAddress: addr, billingAddress: addr, company: null,
    lines: [{ id: 'L1', title: 'Produs', variantTitle: '', sku: 'P1', quantity: 1, unitPrice: 100, vatRate: 21, requiresShipping: true, isGiftCard: false }],
    shippingLines: [{ title: 'Curier', price: 25, vatRate: 21 }], shippingMethod: 'Curier', tags: [], attributes: [], weightGrams: 1000,
    fulfillmentOrders: [{ id: 'FO1', status: 'OPEN' }],
    ...extra,
  };
}
const fresh = () => (store = db.getStore(store.id));
const setMode = (mode, more = {}) => { db.saveStoreSettings(store.id, { ...db.getStore(store.id).settings, mode, ...more }); fresh(); };
const add = (s = store, extra) => P.importOrder(s, normalized(extra), { source: 'test' });
/** An order with a live AWB made at `at` (straight in the database: what counts is the row). */
function liveAwb(at, { test = false, s = store } = {}) {
  const o = add(s);
  return db.updateOrder(o.id, { awb: `X${o.id}`, awb_at: at, courier: 'fakeplan', test_mode: test, tracking_status: TrackingStatus.CREATED });
}

function sessionToken(shop) {
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const h = b64({ alg: 'HS256', typ: 'JWT' });
  const p = b64({ dest: `https://${shop}`, aud: 'key-plans', exp: now + 60, nbf: now - 1, sub: '7' });
  return `${h}.${p}.${createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url')}`;
}
const get = async (path, s = store) => {
  const res = await fetch(base + path, { headers: { Authorization: `Bearer ${sessionToken(s.shop)}` } });
  return { status: res.status, data: (res.headers.get('content-type') || '').includes('json') ? await res.json() : await res.text() };
};

// Shopify / Partner API answers, by URL; everything else (the local test server) goes through.
const realFetch = globalThis.fetch;
let shopifyAnswer = null;
const shopifyCalls = [];
globalThis.fetch = async (url, opts) => {
  const u = String(url);
  if (/myshopify\.com|partners\.shopify\.com/.test(u)) {
    const body = JSON.parse(opts.body);
    shopifyCalls.push({ url: u, query: body.query, variables: body.variables, token: opts.headers['X-Shopify-Access-Token'] });
    const answer = shopifyAnswer(u, body);
    if (answer instanceof Error) throw answer;
    return new Response(JSON.stringify(answer), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }
  return realFetch(url, opts);
};

before(async () => {
  Object.assign(config, { demo: false, adminPassword: 'x'.repeat(16) });
  Object.assign(config.shopify, { apiSecret: SECRET, apiKey: 'key-plans', appHandle: 'expedo', ownStores: ['own-store.myshopify.com'] });
  db.openDb(':memory:');
  ({ store: demo } = seedDemo());
  couriers.fakeplan = fakeCourier;
  invoicers.fakeplaninv = fakeInvoicer;
  store = db.upsertStore({ shop: 'plan-shop.myshopify.com', name: 'Plan shop', accessToken: 'tok' });
  db.saveStoreSettings(store.id, { mode: 'live', courier: { default: 'fakeplan' }, fulfillment: { fulfillInShopify: false, markCodPaidOnDelivery: false, registerCodPayment: false } });
  db.saveIntegration(store.id, 'courier', 'fakeplan', { credentials: { key: 'x' }, settings: {} });
  fresh();
  server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => { server?.close(); globalThis.fetch = realFetch; delete couriers.fakeplan; delete invoicers.fakeplaninv; });
beforeEach(() => { shopifyAnswer = null; shopifyCalls.length = 0; });


// ---------------------------------------------------------------- catalog & mapping

test('catalog: Pro ($15, 1,000 orders) and Pro Max ($30, unlimited); 5-day trial; address & phone check on every plan', () => {
  assert.deepEqual(Object.keys(PLANS), ['pro', 'promax']);
  assert.deepEqual(Object.values(PLANS).map((p) => [p.name, p.price, p.limit]), [['Pro', 15, 1000], ['Pro Max', 30, null]]);
  assert.equal(TRIAL_DAYS, 5);
  for (const p of Object.values(PLANS)) {
    for (const f of ['addressCheck', 'allIntegrations', 'testMode', 'bulk', 'rules', 'tracking', 'codReconciliation']) assert.ok(p.features.includes(f), `${p.id} ${f}`);
  }
  for (const f of ['autoProcess', 'refusalHistory', 'codExport', 'multiStore', 'prioritySupport']) {
    assert.equal(minPlanFor(f), 'promax', f);
    assert.ok(!PLANS.pro.features.includes(f), `Pro has no ${f}`);
  }
  assert.ok(!Object.values(PLANS).some((p) => p.features.includes('customIntegration')), 'custom integration is gone');
});

test('Shopify subscription name → plan id: Pro Max before Pro, case-insensitive; old names map; unknown → null', () => {
  for (const [name, want] of [
    ['Pro Max', 'promax'], ['pro_max', 'promax'], ['promax', 'promax'], ['Expedo Pro Max', 'promax'], ['PRO-MAX', 'promax'], [' pro max ', 'promax'],
    ['Pro', 'pro'], ['Expedo Pro', 'pro'], ['pro', 'pro'], ['pro_monthly', 'pro'],
    ['Growth', 'promax'], ['Plus', 'promax'], ['Starter', 'pro'], ['Free', 'none'],
    ['Professional', null], ['Promaxx', null], ['', null], [undefined, null], ['Max', null],
  ]) {
    assert.equal(planIdFromName(name), want, String(name));
  }
});

test('cached plan ids from the old catalog map sensibly: growth / plus → promax, starter → pro, free → none', () => {
  const s = db.upsertStore({ shop: 'legacy-shop.myshopify.com', accessToken: 't' });
  for (const [cached, want] of [['growth', 'promax'], ['plus', 'promax'], ['starter', 'pro'], ['free', 'none'], ['pro', 'pro'], ['promax', 'promax'], ['bogus', 'none'], [null, 'none']]) {
    db.saveStorePlan(s.id, cached, {});
    assert.equal(planIdFor(db.getStore(s.id)), want, String(cached));
  }
  db.saveStorePlan(s.id, 'growth', {});
  assert.equal(can(db.getStore(s.id), 'codExport'), true, 'an old Growth row keeps its features');
  db.saveStorePlan(s.id, 'starter', {});
  assert.equal(planFor(db.getStore(s.id)).limit, 1000);
});

test('subscriptions from Shopify: Admin API (ACTIVE only; dev-store test charges count) and Partner API', () => {
  const created = '2026-10-01T10:00:00Z';
  assert.equal(adminSubscription([]), null);
  assert.equal(adminSubscription([{ name: 'Pro Max', status: 'CANCELLED' }]), null);
  assert.equal(adminSubscription([{ name: 'Pro Max', status: 'FROZEN' }]), null, 'frozen → no plan');
  const s = adminSubscription([{ name: 'Pro Max', status: 'ACTIVE', test: true, trialDays: 5, createdAt: created, currentPeriodEnd: null }]);
  assert.deepEqual(s, { name: 'Pro Max', status: 'ACTIVE', trialEndsAt: '2026-10-06T10:00:00.000Z', periodEnd: null, test: true });
  const p = partnerSubscription({ trialEndsAt: null, currentBillingCycle: { startTime: '2026-10-01T00:00:00Z', endTime: '2026-10-31T00:00:00Z' }, items: [{ handle: 'pro', description: 'Pro' }] });
  assert.deepEqual([p.name, p.periodEnd], ['pro', '2026-10-31T00:00:00Z']);
  assert.equal(partnerSubscription(null), null);
});

// ---------------------------------------------------------------- usage

test('usage: live AWBs of the 30-day billing period; test mode excluded; boundaries; rolled forward when stale', () => {
  const s = db.upsertStore({ shop: 'usage-shop.myshopify.com', accessToken: 't' });
  db.saveStorePlan(s.id, 'pro', { name: 'Pro', periodEnd: '2026-10-20T00:00:00.000Z' });
  let st = db.getStore(s.id);
  const now = new Date('2026-10-04T12:00:00Z');
  assert.deepEqual(billingPeriod(st, now), { start: '2026-09-20T00:00:00.000Z', end: '2026-10-20T00:00:00.000Z', kind: 'subscription' });
  liveAwb('2026-09-19T23:59:59.000Z', { s: st }); // previous period
  liveAwb('2026-09-20T00:00:00.000Z', { s: st });
  liveAwb('2026-10-19T23:59:59.000Z', { s: st });
  liveAwb('2026-10-03T10:00:00.000Z', { s: st, test: true }); // test mode never counts
  liveAwb('2026-10-20T00:00:00.000Z', { s: st }); // next period
  const canceled = liveAwb('2026-10-02T10:00:00.000Z', { s: st });
  db.updateOrder(canceled.id, { awb: null, awb_at: null }); // canceled AWB: not counted
  assert.equal(usageThisPeriod(st, now), 2);
  // The cached period end has passed (no refresh yet): roll forward by 30 days.
  assert.deepEqual(billingPeriod(st, new Date('2026-11-01T00:00:00Z')).start, '2026-10-20T00:00:00.000Z');
  assert.equal(usageThisPeriod(st, new Date('2026-11-01T00:00:00Z')), 1);
  // During the 5-day trial the period runs to the trial end.
  db.saveStorePlan(s.id, 'pro', { name: 'Pro', trialEndsAt: '2026-10-08T00:00:00.000Z' });
  st = db.getStore(s.id);
  assert.equal(billingPeriod(st, now).start, '2026-09-08T00:00:00.000Z');
  assert.equal(planSummary(st, now).trialDaysLeft, 4);
});

test('usage without a subscription period: the calendar month in Bucharest time', () => {
  const s = db.upsertStore({ shop: 'month-shop.myshopify.com', accessToken: 't' });
  const now = new Date('2026-10-04T12:00:00Z');
  assert.deepEqual(billingPeriod(s, now), { start: '2026-09-30T21:00:00.000Z', end: '2026-10-31T22:00:00.000Z', kind: 'month' });
  liveAwb('2026-09-30T20:59:59.000Z', { s });
  liveAwb('2026-09-30T20:00:00.000Z', { s });
  liveAwb('2026-09-30T21:00:00.000Z', { s });
  assert.equal(usageThisPeriod(s, now), 1);
  assert.equal(planFor(s).id, 'none', 'no subscription → no plan');
});

// ---------------------------------------------------------------- no plan: PLAN_REQUIRED

test('no plan: live AWBs and invoices are refused (PLAN_REQUIRED); test mode, tracking, labels, cancel, storno and fulfilling keep working', async () => {
  db.saveStoreSettings(store.id, { ...db.getStore(store.id).settings, invoicing: { provider: 'fakeplaninv', when: 'on_awb' } });
  db.saveIntegration(store.id, 'invoicing', 'fakeplaninv', { credentials: { key: 'y' }, settings: {} });
  setMode('live');
  assert.equal(planFor(store).id, 'none');
  const before = { ...calls };

  const o = add();
  const r = await P.processOrder(store, o.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'PLAN_REQUIRED');
  assert.equal(r.error.details.upgradeUrl, 'https://admin.shopify.com/store/plan-shop/charges/expedo/pricing_plans');
  assert.equal(db.getOrder(o.id).awb, null);
  assert.notEqual(db.getOrder(o.id).status, 'needs_attention', 'the order isn’t marked as broken');
  assert.equal(t('en', 'errors.PLAN_REQUIRED.message', r.error.params), 'Choose a plan to start shipping — every plan starts with a 5-day free trial.');
  assert.match(t('en', 'errors.PLAN_REQUIRED.hint', r.error.params), /Settings → Plan.*Pro or Pro Max.*Test mode/);
  assert.match(t('ro', 'errors.PLAN_REQUIRED.message', r.error.params), /^Alege un plan .* 5 zile de probă gratuită\.$/);
  assert.equal((await P.processOrder(store, o.id, { steps: ['awb', 'fulfill'] })).error.code, 'PLAN_REQUIRED', 'AWB only, too');

  // An order that already has a live AWB (made while subscribed): a new invoice is refused, the rest works.
  const shipped = liveAwb(new Date().toISOString());
  assert.equal((await P.processOrder(store, shipped.id, { steps: ['invoice'], force: true })).error.code, 'PLAN_REQUIRED');
  assert.equal((await P.processOrder(store, shipped.id, { steps: ['fulfill'], force: true })).ok, true, 'fulfilling an existing AWB');
  assert.ok((await P.trackStore(store)).checked >= 1, 'tracking');
  assert.ok((await P.mergedLabels(store, [shipped.id], 'A4')).pdf.length > 0, 'labels');
  const invoiced = liveAwb(new Date().toISOString());
  db.updateOrder(invoiced.id, { invoice_provider: 'fakeplaninv', invoice_series: 'PL', invoice_number: '77', invoice_test: false });
  await P.stornoInvoice(store, invoiced.id);
  assert.equal(db.getOrder(invoiced.id).invoice_number, null, 'storno of an existing invoice');
  const toCancel = liveAwb(new Date().toISOString()); // not picked up by the courier yet
  await P.cancelAwb(store, toCancel.id);
  assert.equal(db.getOrder(toCancel.id).awb, null, 'cancel an existing AWB');
  assert.deepEqual([calls.createShipment, calls.createInvoice], [before.createShipment, before.createInvoice], 'nothing new asked from the providers');
  assert.equal(calls.cancelShipment, before.cancelShipment + 1);

  // Test mode works fully without a plan, so merchants can explore.
  setMode('test');
  const tr = await P.processOrder(store, add().id);
  assert.equal(tr.ok, true);
  assert.ok(tr.awb);
  setMode('live');

  // The API: plan 'none', the persistent banner flag, both plans for the Plan page, Pro Max features locked.
  const me = (await get('/api/me')).data.plan;
  assert.deepEqual([me.id, me.required, me.complimentary, me.trialDays, me.nearLimit, me.reached], ['none', true, false, 5, false, false]);
  assert.equal(me.upgradeUrl, 'https://admin.shopify.com/store/plan-shop/charges/expedo/pricing_plans');
  assert.deepEqual(me.catalog.map((c) => [c.id, c.name, c.price, c.limit]), [['pro', 'Pro', 15, 1000], ['promax', 'Pro Max', 30, null]]);
  assert.equal(me.features.testMode, true);
  assert.equal(me.features.autoProcess, false);
  assert.equal(me.features.codExport, false);
  const csv = await get('/api/cod.csv');
  assert.deepEqual([csv.status, csv.data.error.code, csv.data.error.message], [403, 'PLAN_FEATURE_LOCKED', 'Available on the Pro Max plan.']);
});

// ---------------------------------------------------------------- Pro limit in the pipeline

test('Pro: the 1,001st live AWB of the period is refused (PLAN_LIMIT_REACHED → Pro Max); tracking, cancel and started orders still work', async () => {
  db.saveStorePlan(store.id, 'pro', { name: 'Pro' });
  setMode('live');
  assert.equal(planFor(store).id, 'pro');
  const now = new Date().toISOString();
  const start = usageThisPeriod(store);
  const existing = [];
  for (let i = start; i < 999; i++) existing.push(liveAwb(now));
  const last = add();
  assert.equal((await P.processOrder(store, last.id)).ok, true, 'the 1,000th is fine');
  assert.equal(usageThisPeriod(store), 1000);

  const before = calls.createShipment;
  const next = add();
  const r = await P.processOrder(store, next.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'PLAN_LIMIT_REACHED');
  assert.equal(r.error.details.upgradeUrl, 'https://admin.shopify.com/store/plan-shop/charges/expedo/pricing_plans');
  assert.equal(calls.createShipment, before, 'no AWB asked from the courier');
  assert.equal(db.getOrder(next.id).awb, null);
  assert.notEqual(db.getOrder(next.id).status, 'needs_attention', 'the order isn’t marked as broken');
  assert.equal(t('en', 'errors.PLAN_LIMIT_REACHED.message', r.error.params), 'You’ve reached the Pro plan’s limit of 1,000 orders this month.');
  assert.match(t('en', 'errors.PLAN_LIMIT_REACHED.hint', r.error.params), /^Upgrade to Pro Max for unlimited orders/);
  assert.match(t('ro', 'errors.PLAN_LIMIT_REACHED.message', r.error.params), /Ai atins limita planului Pro: 1\.000 de comenzi/);

  // Not blocked: the next steps of an order that already has its AWB, cancel, tracking.
  assert.equal((await P.processOrder(store, last.id, { steps: ['invoice', 'fulfill'] })).ok, true);
  await P.cancelAwb(store, existing[0].id);
  assert.equal(usageThisPeriod(store), 999, 'a canceled AWB frees its slot');
  assert.equal((await P.processOrder(store, next.id, { force: true })).ok, true);
  assert.equal(usageThisPeriod(store), 1000);
  assert.ok((await P.trackStore(store)).checked >= 1000);
  assert.equal((await P.processOrder(store, add().id)).error.code, 'PLAN_LIMIT_REACHED');

  // Test mode never counts and is never blocked.
  setMode('test');
  assert.equal((await P.processOrder(store, add().id)).ok, true);
  assert.equal(usageThisPeriod(store), 1000);
  setMode('live');
  // Pro Max lifts the limit.
  db.saveStorePlan(store.id, 'promax', { name: 'Pro Max' });
  fresh();
  assert.equal((await P.processOrder(store, add().id)).ok, true);
  db.saveStorePlan(store.id, 'pro', { name: 'Pro' });
  fresh();
});

test('the API shows the plan, the usage and the 80% warning (Pro)', async () => {
  const me = (await get('/api/me')).data;
  assert.equal(me.plan.id, 'pro');
  assert.equal(me.plan.required, false);
  assert.equal(me.plan.limit, 1000);
  assert.ok(me.plan.used >= 1000);
  assert.equal(me.plan.reached, true);
  assert.equal(me.plan.nearLimit, true);
  assert.equal(me.plan.upgradeUrl, 'https://admin.shopify.com/store/plan-shop/charges/expedo/pricing_plans');
  assert.equal(me.plan.features.addressCheck, true);
  assert.equal(me.plan.features.autoProcess, false);
  const s80 = db.upsertStore({ shop: 'eighty.myshopify.com', accessToken: 't' });
  db.saveStorePlan(s80.id, 'pro', { name: 'Pro' });
  const st = db.getStore(s80.id);
  for (let i = 0; i < 799; i++) liveAwb(new Date().toISOString(), { s: st });
  assert.equal((await get('/api/plan', st)).data.plan.nearLimit, false);
  liveAwb(new Date().toISOString(), { s: st });
  const p = (await get('/api/plan', st)).data.plan;
  assert.deepEqual([p.used, p.nearLimit, p.reached, p.remaining], [800, true, false, 200]);
});

// ---------------------------------------------------------------- feature gating

test('gating: auto-processing, refusal history (warning + rule field) and the COD export need Pro Max; address checks never gated', async () => {
  const s = db.upsertStore({ shop: 'gate-shop.myshopify.com', accessToken: 't' });
  db.saveStorePlan(s.id, 'pro', { name: 'Pro' });
  db.saveStoreSettings(s.id, {
    courier: { default: 'fakeplan' }, automation: { autoProcess: true, delayMinutes: 0 },
    rules: [{ id: 'r', name: 'Refused', enabled: true, conditions: [{ field: 'refusedBefore', op: 'gt', value: '0' }], actions: { hold: true } }],
  });
  let st = db.getStore(s.id);
  const jobs = () => db.getDb().prepare(`SELECT COUNT(*) c FROM jobs WHERE store_id = ? AND type = 'process_order'`).get(st.id).c;
  assert.equal(can(st, 'autoProcess'), false);
  // A customer who refused a COD parcel before.
  const prev = liveAwb(new Date().toISOString(), { s: st });
  db.updateOrder(prev.id, { cod_amount: 125, tracking_status: TrackingStatus.RETURNED, status: 'returned' });
  const o = add(st, { phone: '' });
  assert.equal(jobs(), 0, 'Pro: no automatic processing');
  const codes = (x) => db.getOrder(x.id).issues.map((i) => i.code);
  assert.ok(!codes(o).includes('CUSTOMER_REFUSED_BEFORE'), 'Pro: no refusal warning');
  assert.notEqual(db.getOrder(o.id).status, 'on_hold', 'Pro: a "refused before" rule doesn’t apply');
  const bad = add(st, { shippingAddress: { ...normalized().shippingAddress, phone: '07' } });
  assert.ok(codes(bad).includes('ADDRESS_PHONE_INVALID'), 'address & phone check on Pro too');
  const detail = (await get(`/api/orders/${o.id}`, st)).data;
  assert.equal(detail.customer, null);
  assert.equal(detail.customerLocked, 'Pro Max');
  assert.equal((await get('/api/meta', st)).data.rules.fields.refusedBefore.locked, 'Pro Max');
  const csv = await get('/api/cod.csv', st);
  assert.deepEqual([csv.status, csv.data.error.code, csv.data.error.message], [403, 'PLAN_FEATURE_LOCKED', 'Available on the Pro Max plan.']);

  db.saveStorePlan(st.id, 'promax', { name: 'Pro Max' });
  st = db.getStore(st.id);
  P.validateOrder(st, o.id);
  assert.ok(codes(o).includes('CUSTOMER_REFUSED_BEFORE'), 'Pro Max: refusal warning');
  assert.equal(db.getOrder(o.id).status, 'on_hold', 'Pro Max: the rule applies');
  add(st);
  assert.equal(jobs(), 0, 'held by the rule (same customer): not auto-processed');
  add(st, { email: 'other@example.com', phone: '0744000111', shippingAddress: { ...normalized().shippingAddress, phone: '0744000111' } });
  assert.equal(jobs(), 1, 'Pro Max: new orders are processed automatically');
  assert.equal((await get('/api/cod.csv', st)).status, 200);
  assert.equal((await get('/api/meta', st)).data.rules.fields.refusedBefore.locked, undefined);
  assert.ok((await get(`/api/orders/${o.id}`, st)).data.customer.returned >= 1);

  // Without a plan, the Pro Max features are locked too (and nothing is auto-processed).
  db.saveStorePlan(st.id, null, {});
  st = db.getStore(st.id);
  assert.equal(can(st, 'autoProcess'), false);
  add(st, { email: 'third@example.com', phone: '0744000222', shippingAddress: { ...normalized().shippingAddress, phone: '0744000222' } });
  assert.equal(jobs(), 1, 'no plan: no automatic processing');
  assert.equal((await get('/api/cod.csv', st)).status, 403);
});

// ---------------------------------------------------------------- reading the plan from Shopify

test('refresh: Admin API currentAppInstallation (fallback), dev-store test charge = active; outage keeps the cached plan', async () => {
  const s = db.upsertStore({ shop: 'refresh-shop.myshopify.com', accessToken: 'tok-r' });
  shopifyAnswer = () => ({ data: { currentAppInstallation: { activeSubscriptions: [{ id: 'gid://shopify/AppSubscription/1', name: 'Pro Max', status: 'ACTIVE', test: true, trialDays: 5, createdAt: new Date().toISOString(), currentPeriodEnd: null, lineItems: [] }] } } });
  let st = await refreshPlan(s, shopifyClient(s));
  assert.equal(st.plan, 'promax');
  assert.equal(planSummary(st).test, true);
  assert.equal(planSummary(st).trialDaysLeft, 5);
  assert.match(shopifyCalls[0].query, /currentAppInstallation/);
  assert.ok(db.storeEvents(st.id).some((e) => e.key === 'events.planChanged'));

  shopifyAnswer = () => new Error('network down');
  await assert.rejects(refreshPlan(st, shopifyClient(st)));
  assert.equal(db.getStore(st.id).plan, 'promax', 'never downgraded by an outage');
  await handlers.refresh_plan(db.getStore(st.id), { force: true });
  assert.equal(db.getStore(st.id).plan, 'promax', 'the worker swallows the error and keeps the plan');

  // Trial canceled / subscription expired: no active subscription → no plan.
  shopifyAnswer = () => ({ data: { currentAppInstallation: { activeSubscriptions: [] } } });
  st = await refreshPlan(db.getStore(st.id), shopifyClient(st));
  assert.equal(st.plan, 'none', 'no subscription → no plan');
  assert.equal(planSummary(st).required, true);
  assert.ok(db.storeEvents(st.id).some((e) => e.key === 'events.planNone'));

  // An active subscription with a name the app doesn't know is still a paying store: Pro, never locked out.
  const warn = console.warn;
  console.warn = () => {};
  try {
    assert.equal(applySubscription(st, { name: 'Mystery', status: 'ACTIVE' }).plan, 'pro');
  } finally { console.warn = warn; }
});

test('refresh: Partner API activeSubscription when configured (Shopify App Pricing)', async () => {
  const s = db.upsertStore({ shop: 'partner-shop.myshopify.com', accessToken: 'tok-p' });
  Object.assign(config.shopify.partner, { orgId: '123', token: 'prt', appGid: 'gid://shopify/App/9' });
  try {
    shopifyAnswer = (url) => (url.includes('partners.shopify.com')
      ? { data: { activeSubscription: { billingPeriod: 'EVERY_30_DAYS', trialEndsAt: null, currentBillingCycle: { startTime: '2026-10-01T00:00:00Z', endTime: '2026-10-31T00:00:00Z' }, items: [{ handle: 'pro_max', description: 'Pro Max' }] } } }
      : { data: { shop: { id: 'gid://shopify/Shop/77', name: 'P', myshopifyDomain: s.shop, currencyCode: 'RON' } } });
    const st = await refreshPlan(s, shopifyClient(s));
    assert.equal(st.plan, 'promax');
    assert.equal(st.plan_info.periodEnd, '2026-10-31T00:00:00Z');
    const partner = shopifyCalls.find((c) => c.url.includes('partners'));
    assert.equal(partner.url, 'https://partners.shopify.com/123/api/2026-07/graphql.json');
    assert.deepEqual(partner.variables, { appId: 'gid://shopify/App/9', shopId: 'gid://shopify/Shop/77' });
    assert.equal(partner.token, 'prt');
    shopifyAnswer = (url) => (url.includes('partners.shopify.com') ? { errors: [{ message: 'Too many requests' }] } : { data: { shop: { id: 'gid://shopify/Shop/77' } } });
    await assert.rejects(refreshPlan(st, shopifyClient(st)), /Too many requests/);
    assert.equal(db.getStore(st.id).plan, 'promax', 'a throttled answer isn’t "no subscription"');
  } finally {
    Object.assign(config.shopify.partner, { orgId: '', token: '', appGid: '' });
  }
});

test('APP_SUBSCRIPTIONS_UPDATE webhook queues an immediate re-check; the worker schedules one every 6 hours', async () => {
  const body = JSON.stringify({ app_subscription: { admin_graphql_api_id: 'gid://shopify/AppSubscription/1', name: 'Pro', status: 'ACTIVE' } });
  const res = await fetch(`${base}/webhooks/shopify`, {
    method: 'POST', body,
    headers: { 'Content-Type': 'application/json', 'X-Shopify-Topic': 'app_subscriptions/update', 'X-Shopify-Shop-Domain': store.shop, 'X-Shopify-Webhook-Id': `w-plan-${Date.now()}`,
      'X-Shopify-Hmac-Sha256': createHmac('sha256', SECRET).update(body).digest('base64') },
  });
  assert.equal(res.status, 200);
  await new Promise((r) => setTimeout(r, 20));
  const job = db.getDb().prepare(`SELECT * FROM jobs WHERE key = ?`).get(`plan_now:${store.id}`);
  assert.equal(job.type, 'refresh_plan');
  assert.deepEqual(JSON.parse(job.payload), { force: true });
  shopifyAnswer = () => ({ data: { currentAppInstallation: { activeSubscriptions: [{ name: 'Expedo Pro', status: 'ACTIVE', test: false, trialDays: 0, createdAt: '2026-09-01T00:00:00Z', currentPeriodEnd: '2026-10-30T00:00:00Z', lineItems: [] }] } } });
  await handlers.refresh_plan(store, JSON.parse(job.payload));
  assert.equal(fresh().plan, 'pro');
  assert.equal(planFor(store).limit, 1000);
  // Not stale: the periodic job does nothing; demo / own stores never get one.
  assert.deepEqual(await handlers.refresh_plan(store, {}), { skipped: true });
  schedulePeriodic();
  const next = db.getDb().prepare(`SELECT run_at FROM jobs WHERE key = ? AND status = 'pending'`).get(`plan:${store.id}`);
  assert.ok(Date.parse(next.run_at) - Date.now() > 5.9 * 3600_000);
  assert.equal(db.getDb().prepare(`SELECT COUNT(*) c FROM jobs WHERE key = ?`).get(`plan:${demo.id}`).c, 0);
});

test('demo store and SHOPIFY_OWN_STORES are on Pro Max, without asking Shopify, and never see the "choose a plan" banner', async () => {
  assert.equal(planFor(demo).id, 'promax');
  assert.equal(can(demo, 'codExport'), true);
  assert.equal(upgradeUrl(demo), null);
  const own = db.upsertStore({ shop: 'own-store.myshopify.com' });
  assert.equal(planFor(own).id, 'promax');
  assert.equal(await refreshPlan(own, { activeSubscription: () => { throw new Error('must not be called'); } }), own);
  assert.equal(applySubscription(own, null).plan, 'none', 'even with a cached "none" row…');
  assert.equal(planFor(db.getStore(own.id)).id, 'promax', '…an own store stays on Pro Max');
  const s = planSummary(demo);
  assert.deepEqual([s.id, s.name, s.limit, s.complimentary, s.required, s.upgradeUrl], ['promax', 'Pro Max', null, true, false, null]);
});
