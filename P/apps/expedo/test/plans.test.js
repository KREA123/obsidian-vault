import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { config } from '../src/config.js';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { createApp } from '../src/server.js';
import { couriers } from '../src/couriers/index.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import { shopifyClient, adminSubscription, partnerSubscription } from '../src/shopify/client.js';
import { handlers, schedulePeriodic } from '../src/worker.js';
import { t } from '../src/i18n/index.js';
import {
  PLANS, planIdFromName, planFor, can, usageThisPeriod, billingPeriod, planSummary, upgradeUrl, refreshPlan, applySubscription, minPlanFor,
} from '../src/core/plans.js';

// Pricing plans (core/plans.js): name mapping, usage per billing period, the monthly limit in the pipeline,
// feature gating, the subscription webhook, the API, and demo / own stores on Plus.

const SECRET = 'plans-secret';
let server, base, demo, store, seq = 0;
const calls = { createShipment: 0, cancelShipment: 0 };
const fakeCourier = {
  id: 'fakeplan', name: 'Fake courier', trackingUrl: (awb) => `https://fake.example/${awb}`, credentialFields: [], settingsFields: [],
  async testConnection() { return { ok: true }; },
  async createShipment() { calls.createShipment++; return { awb: `LIVE${calls.createShipment}`, price: 20 }; },
  async getLabel() { return Buffer.from('%PDF'); },
  async cancelShipment() { calls.cancelShipment++; },
  async track(ctx, awbs) { return awbs.map((awb) => ({ awb, status: TrackingStatus.IN_TRANSIT })); },
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
  store = db.upsertStore({ shop: 'plan-shop.myshopify.com', name: 'Plan shop', accessToken: 'tok' });
  db.saveStoreSettings(store.id, { mode: 'live', courier: { default: 'fakeplan' }, fulfillment: { fulfillInShopify: false, markCodPaidOnDelivery: false, registerCodPayment: false } });
  db.saveIntegration(store.id, 'courier', 'fakeplan', { credentials: { key: 'x' }, settings: {} });
  fresh();
  server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => { server?.close(); globalThis.fetch = realFetch; delete couriers.fakeplan; });
beforeEach(() => { shopifyAnswer = null; shopifyCalls.length = 0; });

// ---------------------------------------------------------------- catalog & mapping

test('catalog: four plans, limits, prices, address & phone check on every plan', () => {
  assert.deepEqual(Object.keys(PLANS), ['free', 'starter', 'growth', 'plus']);
  assert.deepEqual(Object.values(PLANS).map((p) => [p.name, p.price, p.limit]), [['Free', 0, 50], ['Starter', 14.99, 1000], ['Growth', 24.99, null], ['Plus', 49.99, null]]);
  for (const p of Object.values(PLANS)) for (const f of ['addressCheck', 'allIntegrations', 'testMode', 'tracking']) assert.ok(p.features.includes(f), `${p.id} ${f}`);
  assert.equal(minPlanFor('autoProcess'), 'growth');
  assert.equal(minPlanFor('codExport'), 'growth');
  assert.equal(minPlanFor('multiStore'), 'plus');
});

test('Shopify subscription name → plan id, case-insensitive; unknown → null', () => {
  for (const [name, want] of [['Free', 'free'], ['STARTER', 'starter'], ['growth', 'growth'], [' Plus ', 'plus'], ['Expedo Growth', 'growth'], ['growth_plan', 'growth'],
    ['starter-monthly', 'starter'], ['Pro', null], ['', null], [undefined, null], ['Growthy', null]]) {
    assert.equal(planIdFromName(name), want, String(name));
  }
});

test('subscriptions from Shopify: Admin API (ACTIVE only; dev-store test charges count) and Partner API', () => {
  const created = '2026-10-01T10:00:00Z';
  assert.equal(adminSubscription([]), null);
  assert.equal(adminSubscription([{ name: 'Growth', status: 'CANCELLED' }]), null);
  const s = adminSubscription([{ name: 'Growth', status: 'ACTIVE', test: true, trialDays: 30, createdAt: created, currentPeriodEnd: null }]);
  assert.deepEqual(s, { name: 'Growth', status: 'ACTIVE', trialEndsAt: '2026-10-31T10:00:00.000Z', periodEnd: null, test: true });
  const p = partnerSubscription({ trialEndsAt: null, currentBillingCycle: { startTime: '2026-10-01T00:00:00Z', endTime: '2026-10-31T00:00:00Z' }, items: [{ handle: 'starter', description: 'Starter' }] });
  assert.deepEqual([p.name, p.periodEnd], ['starter', '2026-10-31T00:00:00Z']);
  assert.equal(partnerSubscription(null), null);
});

// ---------------------------------------------------------------- usage

test('usage: live AWBs of the 30-day billing period; test mode excluded; boundaries; rolled forward when stale', () => {
  const s = db.upsertStore({ shop: 'usage-shop.myshopify.com', accessToken: 't' });
  db.saveStorePlan(s.id, 'starter', { name: 'Starter', periodEnd: '2026-10-20T00:00:00.000Z' });
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
  // During the trial the period runs to the trial end.
  db.saveStorePlan(s.id, 'starter', { name: 'Starter', trialEndsAt: '2026-10-25T00:00:00.000Z' });
  st = db.getStore(s.id);
  assert.equal(billingPeriod(st, now).start, '2026-09-25T00:00:00.000Z');
  assert.equal(planSummary(st, now).trialDaysLeft, 21);
});

test('usage without a subscription period: the calendar month in Bucharest time', () => {
  const s = db.upsertStore({ shop: 'month-shop.myshopify.com', accessToken: 't' });
  const now = new Date('2026-10-04T12:00:00Z');
  assert.deepEqual(billingPeriod(s, now), { start: '2026-09-30T21:00:00.000Z', end: '2026-10-31T22:00:00.000Z', kind: 'month' });
  liveAwb('2026-09-30T20:59:59.000Z', { s });
  liveAwb('2026-09-30T21:00:00.000Z', { s });
  assert.equal(usageThisPeriod(s, now), 1);
  assert.equal(planFor(s).id, 'free', 'no subscription → Free');
});

// ---------------------------------------------------------------- limit in the pipeline

test('Free: the 51st live AWB of the month is refused (PLAN_LIMIT_REACHED); tracking, cancel and started orders still work', async () => {
  setMode('live');
  assert.equal(planFor(store).id, 'free');
  const now = new Date().toISOString();
  const existing = [];
  for (let i = 0; i < 49; i++) existing.push(liveAwb(now));
  const fiftieth = add();
  assert.equal((await P.processOrder(store, fiftieth.id)).ok, true, 'the 50th is fine');
  assert.equal(usageThisPeriod(store), 50);

  const before = calls.createShipment;
  const next = add();
  const r = await P.processOrder(store, next.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'PLAN_LIMIT_REACHED');
  assert.equal(r.error.details.upgradeUrl, 'https://admin.shopify.com/store/plan-shop/charges/expedo/pricing_plans');
  assert.equal(calls.createShipment, before, 'no AWB asked from the courier');
  assert.equal(db.getOrder(next.id).awb, null);
  assert.notEqual(db.getOrder(next.id).status, 'needs_attention', 'the order isn’t marked as broken');
  const msg = t('en', 'errors.PLAN_LIMIT_REACHED.message', r.error.params);
  assert.equal(msg, 'You’ve reached the Free plan’s limit of 50 orders this month.');
  assert.match(t('en', 'errors.PLAN_LIMIT_REACHED.hint', r.error.params), /^Upgrade your plan \(Starter or higher\)/);
  assert.match(t('ro', 'errors.PLAN_LIMIT_REACHED.message', r.error.params), /Ai atins limita planului Free: 50 comenzi/);

  // Not blocked: the next steps of an order that already has its AWB, cancel, tracking.
  assert.equal((await P.processOrder(store, fiftieth.id, { steps: ['invoice', 'fulfill'] })).ok, true);
  await P.cancelAwb(store, existing[0].id);
  assert.equal(usageThisPeriod(store), 49, 'a canceled AWB frees its slot');
  assert.equal((await P.processOrder(store, next.id, { force: true })).ok, true);
  assert.equal(usageThisPeriod(store), 50);
  assert.ok((await P.trackStore(store)).checked >= 50);
  assert.equal((await P.processOrder(store, add().id)).error.code, 'PLAN_LIMIT_REACHED');

  // Test mode never counts and is never blocked.
  setMode('test');
  const t1 = add();
  assert.equal((await P.processOrder(store, t1.id)).ok, true);
  assert.equal(usageThisPeriod(store), 50);
  setMode('live');
  // A higher plan lifts the limit.
  db.saveStorePlan(store.id, 'starter', { name: 'Starter' });
  fresh();
  assert.equal((await P.processOrder(store, add().id)).ok, true);
  db.saveStorePlan(store.id, 'free', {});
  fresh();
});

test('the API shows the plan, the usage and the 80% warning', async () => {
  const me = (await get('/api/me')).data;
  assert.equal(me.plan.id, 'free');
  assert.equal(me.plan.limit, 50);
  assert.ok(me.plan.used >= 50);
  assert.equal(me.plan.reached, true);
  assert.equal(me.plan.nearLimit, true);
  assert.equal(me.plan.upgradeUrl, 'https://admin.shopify.com/store/plan-shop/charges/expedo/pricing_plans');
  assert.equal(me.plan.features.addressCheck, true);
  assert.equal(me.plan.features.autoProcess, false);
  const fresh80 = db.upsertStore({ shop: 'eighty.myshopify.com', accessToken: 't' });
  for (let i = 0; i < 39; i++) liveAwb(new Date().toISOString(), { s: fresh80 });
  assert.equal((await get('/api/plan', fresh80)).data.plan.nearLimit, false);
  liveAwb(new Date().toISOString(), { s: fresh80 });
  const p = (await get('/api/plan', fresh80)).data.plan;
  assert.deepEqual([p.used, p.nearLimit, p.reached, p.remaining], [40, true, false, 10]);
});

// ---------------------------------------------------------------- feature gating

test('gating: auto-processing, refusal history (warning + rule field) and the COD export need Growth; address checks never gated', async () => {
  const s = db.upsertStore({ shop: 'gate-shop.myshopify.com', accessToken: 't' });
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
  assert.equal(jobs(), 0, 'Free: no automatic processing');
  const codes = (x) => db.getOrder(x.id).issues.map((i) => i.code);
  assert.ok(!codes(o).includes('CUSTOMER_REFUSED_BEFORE'), 'Free: no refusal warning');
  assert.notEqual(db.getOrder(o.id).status, 'on_hold', 'Free: a "refused before" rule doesn’t apply');
  const bad = add(st, { shippingAddress: { ...normalized().shippingAddress, phone: '07' } });
  assert.ok(codes(bad).includes('ADDRESS_PHONE_INVALID'), 'address & phone check on Free too');
  const detail = (await get(`/api/orders/${o.id}`, st)).data;
  assert.equal(detail.customer, null);
  assert.equal(detail.customerLocked, 'Growth');
  assert.equal((await get('/api/meta', st)).data.rules.fields.refusedBefore.locked, 'Growth');
  const csv = await get('/api/cod.csv', st);
  assert.deepEqual([csv.status, csv.data.error.code, csv.data.error.message], [403, 'PLAN_FEATURE_LOCKED', 'Available on the Growth plan and up.']);

  db.saveStorePlan(st.id, 'growth', { name: 'Growth' });
  st = db.getStore(st.id);
  P.validateOrder(st, o.id);
  assert.ok(codes(o).includes('CUSTOMER_REFUSED_BEFORE'), 'Growth: refusal warning');
  assert.equal(db.getOrder(o.id).status, 'on_hold', 'Growth: the rule applies');
  add(st);
  assert.equal(jobs(), 0, 'held by the rule (same customer): not auto-processed');
  add(st, { email: 'other@example.com', phone: '0744000111', shippingAddress: { ...normalized().shippingAddress, phone: '0744000111' } });
  assert.equal(jobs(), 1, 'Growth: new orders are processed automatically');
  assert.equal((await get('/api/cod.csv', st)).status, 200);
  assert.equal((await get('/api/meta', st)).data.rules.fields.refusedBefore.locked, undefined);
  assert.ok((await get(`/api/orders/${o.id}`, st)).data.customer.returned >= 1);
});

// ---------------------------------------------------------------- reading the plan from Shopify

test('refresh: Admin API currentAppInstallation (fallback), dev-store test charge = active; outage keeps the cached plan', async () => {
  const s = db.upsertStore({ shop: 'refresh-shop.myshopify.com', accessToken: 'tok-r' });
  shopifyAnswer = () => ({ data: { currentAppInstallation: { activeSubscriptions: [{ id: 'gid://shopify/AppSubscription/1', name: 'growth', status: 'ACTIVE', test: true, trialDays: 30, createdAt: new Date().toISOString(), currentPeriodEnd: null, lineItems: [] }] } } });
  let st = await refreshPlan(s, shopifyClient(s));
  assert.equal(st.plan, 'growth');
  assert.equal(planSummary(st).test, true);
  assert.equal(planSummary(st).trialDaysLeft, 30);
  assert.match(shopifyCalls[0].query, /currentAppInstallation/);
  assert.ok(db.storeEvents(st.id).some((e) => e.key === 'events.planChanged'));

  shopifyAnswer = () => new Error('network down');
  await assert.rejects(refreshPlan(st, shopifyClient(st)));
  assert.equal(db.getStore(st.id).plan, 'growth', 'never downgraded by an outage');
  await handlers.refresh_plan(db.getStore(st.id), { force: true });
  assert.equal(db.getStore(st.id).plan, 'growth', 'the worker swallows the error and keeps the plan');

  shopifyAnswer = () => ({ data: { currentAppInstallation: { activeSubscriptions: [] } } });
  st = await refreshPlan(db.getStore(st.id), shopifyClient(st));
  assert.equal(st.plan, 'free', 'no subscription → Free');
});

test('refresh: Partner API activeSubscription when configured (Shopify App Pricing)', async () => {
  const s = db.upsertStore({ shop: 'partner-shop.myshopify.com', accessToken: 'tok-p' });
  Object.assign(config.shopify.partner, { orgId: '123', token: 'prt', appGid: 'gid://shopify/App/9' });
  try {
    shopifyAnswer = (url) => (url.includes('partners.shopify.com')
      ? { data: { activeSubscription: { billingPeriod: 'EVERY_30_DAYS', trialEndsAt: null, currentBillingCycle: { startTime: '2026-10-01T00:00:00Z', endTime: '2026-10-31T00:00:00Z' }, items: [{ handle: 'plus', description: 'Plus' }] } } }
      : { data: { shop: { id: 'gid://shopify/Shop/77', name: 'P', myshopifyDomain: s.shop, currencyCode: 'RON' } } });
    const st = await refreshPlan(s, shopifyClient(s));
    assert.equal(st.plan, 'plus');
    assert.equal(st.plan_info.periodEnd, '2026-10-31T00:00:00Z');
    const partner = shopifyCalls.find((c) => c.url.includes('partners'));
    assert.equal(partner.url, 'https://partners.shopify.com/123/api/2026-07/graphql.json');
    assert.deepEqual(partner.variables, { appId: 'gid://shopify/App/9', shopId: 'gid://shopify/Shop/77' });
    assert.equal(partner.token, 'prt');
    shopifyAnswer = (url) => (url.includes('partners.shopify.com') ? { errors: [{ message: 'Too many requests' }] } : { data: { shop: { id: 'gid://shopify/Shop/77' } } });
    await assert.rejects(refreshPlan(st, shopifyClient(st)), /Too many requests/);
    assert.equal(db.getStore(st.id).plan, 'plus', 'a throttled answer isn’t "no subscription"');
  } finally {
    Object.assign(config.shopify.partner, { orgId: '', token: '', appGid: '' });
  }
});

test('APP_SUBSCRIPTIONS_UPDATE webhook queues an immediate re-check; the worker schedules one every 6 hours', async () => {
  const body = JSON.stringify({ app_subscription: { admin_graphql_api_id: 'gid://shopify/AppSubscription/1', name: 'Starter', status: 'ACTIVE' } });
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
  shopifyAnswer = () => ({ data: { currentAppInstallation: { activeSubscriptions: [{ name: 'Starter', status: 'ACTIVE', test: false, trialDays: 0, createdAt: '2026-09-01T00:00:00Z', currentPeriodEnd: '2026-10-30T00:00:00Z', lineItems: [] }] } } });
  await handlers.refresh_plan(store, JSON.parse(job.payload));
  assert.equal(fresh().plan, 'starter');
  assert.equal(planFor(store).limit, 1000);
  // Not stale: the periodic job does nothing; demo / own stores never get one.
  assert.deepEqual(await handlers.refresh_plan(store, {}), { skipped: true });
  schedulePeriodic();
  const next = db.getDb().prepare(`SELECT run_at FROM jobs WHERE key = ? AND status = 'pending'`).get(`plan:${store.id}`);
  assert.ok(Date.parse(next.run_at) - Date.now() > 5.9 * 3600_000);
  assert.equal(db.getDb().prepare(`SELECT COUNT(*) c FROM jobs WHERE key = ?`).get(`plan:${demo.id}`).c, 0);
  db.saveStorePlan(store.id, 'free', {});
  fresh();
});

test('demo store and SHOPIFY_OWN_STORES are on Plus, without asking Shopify', async () => {
  assert.equal(planFor(demo).id, 'plus');
  assert.equal(can(demo, 'codExport'), true);
  assert.equal(upgradeUrl(demo), null);
  const own = db.upsertStore({ shop: 'own-store.myshopify.com' });
  assert.equal(planFor(own).id, 'plus');
  assert.equal(await refreshPlan(own, { activeSubscription: () => { throw new Error('must not be called'); } }), own);
  assert.equal(applySubscription(own, null).plan, 'free', 'even with a cached Free row…');
  assert.equal(planFor(db.getStore(own.id)).id, 'plus', '…an own store stays on Plus');
  const s = planSummary(demo);
  assert.deepEqual([s.id, s.limit, s.complimentary, s.upgradeUrl], ['plus', null, true, null]);
});
