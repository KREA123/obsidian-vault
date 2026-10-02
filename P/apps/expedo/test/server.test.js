import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { config } from '../src/config.js';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { createApp, csvCell } from '../src/server.js';

// HTTP-level checks: auth, store isolation, CSRF, validation, secrets never echoed.

let server, base, demo, other, otherOrder, cookie;
const SECRET = 'test-secret';

before(async () => {
  Object.assign(config, { demo: false, adminPassword: 'parola-buna' });
  Object.assign(config.shopify, { apiSecret: SECRET, apiKey: 'key123' });
  db.openDb(':memory:');
  ({ store: demo } = seedDemo());
  other = db.upsertStore({ shop: 'alt-magazin.myshopify.com', name: 'Alt magazin', accessToken: 'tok' });
  const o = db.getOrder(db.getDb().prepare('SELECT id FROM orders WHERE store_id = ? LIMIT 1').get(demo.id).id).data;
  otherOrder = P.importOrder(other, { ...o, shopifyId: 'gid://shopify/Order/777', name: '#ALT1' });
  server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server?.close());

async function call(path, { method = 'GET', body, headers = {}, auth = true, csrf = true, raw } = {}) {
  const h = { ...headers };
  if (auth && cookie) h.Cookie = cookie;
  if (csrf && method !== 'GET') h['X-Expedo-Request'] = '1';
  if (body !== undefined) h['Content-Type'] = 'application/json';
  const res = await fetch(base + path, { method, headers: h, body: raw ?? (body === undefined ? undefined : JSON.stringify(body)), redirect: 'manual' });
  const type = res.headers.get('content-type') || '';
  const data = type.includes('json') ? await res.json() : type.includes('pdf') ? Buffer.from(await res.arrayBuffer()) : await res.text();
  return { status: res.status, data, headers: res.headers };
}
const demoH = () => ({ 'X-Store-Id': String(demo.id) });
const demoOrder = (name) => db.getDb().prepare('SELECT id FROM orders WHERE store_id = ? AND name = ?').get(demo.id, name).id;

function sessionToken(shop) {
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const h = b64({ alg: 'HS256', typ: 'JWT' });
  const p = b64({ dest: `https://${shop}`, aud: 'key123', exp: now + 60, nbf: now - 1 });
  return `${h}.${p}.${createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url')}`;
}

test('every /api route requires a login', async () => {
  for (const [method, path] of [['GET', '/api/me'], ['GET', '/api/orders'], ['GET', `/api/orders/${otherOrder.id}`], ['GET', '/api/settings'],
    ['GET', '/api/integrations'], ['GET', '/api/cod.csv'], ['GET', '/api/labels.pdf?ids=1'], ['POST', '/api/orders/process'], ['PUT', '/api/settings']]) {
    const r = await call(path, { method, auth: false, body: method === 'GET' ? undefined : {} });
    assert.equal(r.status, 401, `${method} ${path}`);
    assert.equal(r.data.error.code, 'LOGIN_REQUIRED');
  }
});

test('login: wrong password gets no cookie, right one does', async () => {
  const bad = await fetch(`${base}/login`, { method: 'POST', body: new URLSearchParams({ password: 'nu' }), redirect: 'manual' });
  assert.equal(bad.status, 302);
  assert.match(bad.headers.get('location'), /login=fail/);
  assert.equal(bad.headers.get('set-cookie'), null);
  const ok = await fetch(`${base}/login`, { method: 'POST', body: new URLSearchParams({ password: 'parola-buna' }), redirect: 'manual' });
  const set = ok.headers.get('set-cookie');
  assert.match(set, /expedo_session=.+; Path=\/; HttpOnly; SameSite=Lax/);
  cookie = set.split(';')[0];
  const me = await call('/api/me', { headers: demoH() });
  assert.equal(me.status, 200);
  assert.equal(me.data.store.id, demo.id);
});

test('CSRF: cookie-authenticated writes need the X-Expedo-Request header', async () => {
  const r = await call('/api/orders/process', { method: 'POST', body: { ids: [demoOrder('#1101')] }, headers: demoH(), csrf: false });
  assert.equal(r.status, 403);
  assert.equal(r.data.error.code, 'CSRF');
  assert.equal(db.getOrder(demoOrder('#1101')).awb, null);
});

test('orders list: filters, search, bad page values, LIKE wildcards', async () => {
  const all = await call('/api/orders?status=all', { headers: demoH() });
  assert.equal(all.status, 200);
  assert.equal(all.data.total, 21);
  assert.ok(all.data.orders.every((o) => o.name !== '#ALT1'), 'no orders of another store');
  const bad = await call('/api/orders?page=abc&status=all', { headers: demoH() });
  assert.equal(bad.status, 200);
  assert.equal(bad.data.page, 1);
  const arr = await call('/api/orders?status=all&status=ready', { headers: demoH() });
  assert.equal(arr.status, 200);
  assert.equal((await call('/api/orders?status=all&q=%25', { headers: demoH() })).data.total, 0, '% is literal');
  const found = await call(`/api/orders?status=all&q=${encodeURIComponent('Popescu')}`, { headers: demoH() });
  assert.ok(found.data.total >= 1);
  // Refusal history: badge count in the list, history in the order page.
  const matei = (await call(`/api/orders?status=all&q=${encodeURIComponent('Florin Matei')}`, { headers: demoH() })).data.orders;
  assert.deepEqual(matei.map((o) => [o.name, o.refusedBefore]).sort(), [['#1090', 0], ['#1095', 1], ['#1111', 1]]);
  const detail = (await call(`/api/orders/${demoOrder('#1111')}`, { headers: demoH() })).data;
  assert.deepEqual([detail.customer.returned, detail.customer.delivered], [1, 1]);
  assert.deepEqual(detail.customer.orders.map((o) => [o.name, o.refused]), [['#1095', false], ['#1090', true]]);
  assert.ok(detail.order.issues.some((i) => i.code === 'CUSTOMER_REFUSED_BEFORE'));
  const ids = [demoOrder('#1101'), demoOrder('#1102')];
  const byIds = await call(`/api/orders?status=all&ids=${ids.join(',')}`, { headers: demoH() });
  assert.deepEqual(byIds.data.orders.map((o) => o.id).sort(), ids.sort());
});

test('order detail and store isolation', async () => {
  const d = await call(`/api/orders/${demoOrder('#1101')}`, { headers: demoH() });
  assert.equal(d.status, 200);
  assert.equal(d.data.order.name, '#1101');
  assert.ok(d.data.plan.courier);
  // Admin switched to the demo store: the other store's order is not reachable through it.
  assert.equal((await call(`/api/orders/${otherOrder.id}`, { headers: demoH() })).status, 404);
  assert.equal((await call(`/api/orders/${otherOrder.id}`, { method: 'PATCH', body: { parcels: 2 }, headers: demoH() })).status, 404);
  const proc = await call('/api/orders/process', { method: 'POST', body: { ids: [otherOrder.id] }, headers: demoH() });
  assert.deepEqual(proc.data.results, []);
  assert.equal(db.getOrder(otherOrder.id).awb, null);
});

test('embedded session token: only its own store, X-Store-Id ignored, no CSRF header needed', async () => {
  const bearer = { Authorization: `Bearer ${sessionToken('alt-magazin.myshopify.com')}`, 'X-Store-Id': String(demo.id) };
  const list = await call('/api/orders?status=all', { headers: bearer, auth: false });
  assert.equal(list.status, 200);
  assert.deepEqual(list.data.orders.map((o) => o.name), ['#ALT1']);
  assert.equal((await call(`/api/orders/${demoOrder('#1101')}`, { headers: bearer, auth: false })).status, 404);
  const labels = await call(`/api/labels.pdf?ids=${demoOrder('#1101')}`, { headers: bearer, auth: false });
  assert.equal(labels.status, 400, 'another store\'s labels are never rendered');
  const patch = await call(`/api/orders/${otherOrder.id}`, { method: 'PATCH', body: { notes: 'fragil' }, headers: bearer, auth: false, csrf: false });
  assert.equal(patch.status, 200);
  const forged = await call('/api/orders', { headers: { Authorization: 'Bearer a.b.c' }, auth: false });
  assert.equal(forged.status, 401);
});

test('PATCH validates manual edits', async () => {
  const id = demoOrder('#1103');
  for (const body of [{ cod: 'abc' }, { parcels: 0 }, { parcels: 1.5 }, { weightKg: -1 }, { courier: 'constructor' }, { courier: 'mock' }, { hold: 'yes' }, { address: 'x' }]) {
    const r = await call(`/api/orders/${id}`, { method: 'PATCH', body, headers: demoH() });
    assert.equal(r.status, 400, JSON.stringify(body));
  }
  const ok = await call(`/api/orders/${id}`, { method: 'PATCH', body: { parcels: 2, cod: 10.5, address: { city: 'Iași', evil: 'x' } }, headers: demoH() });
  assert.equal(ok.status, 200);
  const o = db.getOrder(id);
  assert.equal(o.overrides.parcels, 2);
  assert.equal(o.overrides.cod, 10.5);
  assert.equal(o.overrides.address.evil, undefined);
  await call(`/api/orders/${id}`, { method: 'PATCH', body: { parcels: null, cod: '' }, headers: demoH() });
  assert.equal(db.getOrder(id).overrides.parcels, undefined);
  assert.equal(db.getOrder(id).overrides.cod, undefined);
});

test('process, labels, invoice PDF; held orders need an explicit force', async () => {
  const id = demoOrder('#1104');
  const r = await call('/api/orders/process', { method: 'POST', body: { ids: [id] }, headers: demoH() });
  assert.equal(r.status, 200);
  assert.equal(r.data.ok, 1);
  assert.match(r.data.results[0].awb, /^TEST/);
  const pdf = await call(`/api/labels.pdf?ids=${id}`, { headers: demoH() });
  assert.equal(pdf.status, 200);
  assert.equal(pdf.headers.get('content-type'), 'application/pdf');
  assert.equal(pdf.data.subarray(0, 4).toString(), '%PDF');
  const inv = await call(`/api/orders/${id}/invoice.pdf`, { headers: demoH() });
  assert.equal(inv.status, 200);

  const held = demoOrder('#1117'); // tag "manual"
  const bulk = await call('/api/orders/process', { method: 'POST', body: { ids: [held] }, headers: demoH() });
  assert.equal(bulk.data.ok, 0);
  assert.equal(db.getOrder(held).awb, null);
  const forced = await call('/api/orders/process', { method: 'POST', body: { ids: [held], force: true }, headers: demoH() });
  assert.equal(forced.data.ok, 1);

  const badSteps = await call('/api/orders/process', { method: 'POST', body: { ids: [id], steps: ['drop'] }, headers: demoH() });
  assert.equal(badSteps.status, 400);
});

test('settings: validated, merged per section, demo stays in test mode', async () => {
  const s = await call('/api/settings', { headers: demoH() });
  assert.equal(s.status, 200);
  assert.equal(s.data.settings.mode, 'test');
  assert.equal((await call('/api/settings', { method: 'PUT', body: { settings: { mode: 'live' } }, headers: demoH() })).status, 400);
  assert.equal((await call('/api/settings', { method: 'PUT', body: { settings: { mode: 'banana' } }, headers: demoH() })).status, 400);
  assert.equal((await call('/api/settings', { method: 'PUT', body: { settings: { invoicing: { defaultVatRate: '' } } }, headers: demoH() })).status, 400);
  const saved = await call('/api/settings', { method: 'PUT', body: { settings: { packaging: { parcels: '2' }, automation: { autoProcess: 'true' }, __proto__x: 1 } }, headers: demoH() });
  assert.equal(saved.status, 200);
  assert.equal(saved.data.settings.packaging.parcels, 2);
  assert.equal(saved.data.settings.packaging.defaultWeightKg, 1, 'other keys of the section kept');
  assert.equal(saved.data.settings.automation.autoProcess, true);
  assert.equal(saved.data.settings.automation.delayMinutes, 15);
  assert.equal(saved.data.settings.invoicing.provider, 'smartbill', 'untouched sections kept');
  assert.equal(saved.data.settings.__proto__x, undefined);
  await call('/api/settings', { method: 'PUT', body: { settings: { automation: { autoProcess: false } } }, headers: demoH() });
});

test('integrations: secrets are never sent back', async () => {
  const put = await call('/api/integrations/courier/cargus', { method: 'PUT', body: { credentials: { username: 'u', password: 'super-secret-123', subscriptionKey: 'key-xyz' }, settings: { pickupPointId: '5' } }, headers: demoH() });
  assert.equal(put.status, 200);
  assert.ok(!JSON.stringify(put.data).includes('super-secret-123'));
  const list = await call('/api/integrations', { headers: demoH() });
  const text = JSON.stringify(list.data);
  assert.ok(!text.includes('super-secret-123') && !text.includes('key-xyz'));
  const c = list.data.courier.find((i) => i.provider === 'cargus');
  assert.equal(c.credentialsSet.password, true);
  assert.equal(c.settings.pickupPointId, '5');
  // Blank = keep the saved secret.
  await call('/api/integrations/courier/cargus', { method: 'PUT', body: { credentials: { password: '' }, settings: {} }, headers: demoH() });
  assert.equal(db.getIntegration(demo.id, 'courier', 'cargus').credentials.password, 'super-secret-123');
  for (const p of ['__proto__', 'constructor', 'mock']) {
    assert.equal((await call(`/api/integrations/courier/${p}`, { method: 'PUT', body: {}, headers: demoH() })).status, 404, p);
  }
  // Not visible from another store.
  const bearer = { Authorization: `Bearer ${sessionToken('alt-magazin.myshopify.com')}` };
  assert.deepEqual((await call('/api/integrations', { headers: bearer, auth: false })).data.courier, []);
});

test('reset test data endpoint', async () => {
  const id = demoOrder('#1105');
  await call('/api/orders/process', { method: 'POST', body: { ids: [id] }, headers: demoH() });
  assert.ok(db.getOrder(id).awb);
  const r = await call(`/api/orders/${id}/reset-test`, { method: 'POST', headers: demoH() });
  assert.equal(r.status, 200);
  assert.equal(db.getOrder(id).awb, null);
  assert.equal(db.getOrder(id).status, 'ready');
  const again = await call(`/api/orders/${id}/reset-test`, { method: 'POST', headers: demoH() });
  assert.equal(again.status, 400);
});

test('COD CSV escapes formulas and uses Bucharest dates', async () => {
  const id = demoOrder('#1106');
  await call('/api/orders/process', { method: 'POST', body: { ids: [id] }, headers: demoH() });
  db.updateOrder(id, { name: '=HYPERLINK("http://x","y")', awb_at: '2026-10-01T22:30:00.000Z' });
  const r = await call('/api/cod.csv', { headers: demoH() });
  assert.equal(r.status, 200);
  assert.ok(r.data.includes(`"'=HYPERLINK(""http://x"",""y"")"`));
  assert.ok(r.data.includes('"2026-10-02"'), 'AWB made at 01:30 Bucharest time is on the 2nd');
  assert.equal(csvCell('-5'), `"'-5"`);
  assert.equal(csvCell('@SUM(A1)'), `"'@SUM(A1)"`);
  assert.equal(csvCell('Cargus'), '"Cargus"');
});

test('stats and other read routes answer', async () => {
  for (const p of ['/api/stats', '/api/events', '/api/meta', `/api/picking?ids=${demoOrder('#1101')},${otherOrder.id}`]) {
    const r = await call(p, { headers: demoH() });
    assert.equal(r.status, 200, p);
  }
  const pick = await call(`/api/picking?ids=${demoOrder('#1101')},${otherOrder.id}`, { headers: demoH() });
  assert.deepEqual(pick.data.orders, ['#1101']);
});

test('malformed JSON is a 400, not a 500', async () => {
  const r = await call(`/api/orders/${demoOrder('#1107')}`, { method: 'PATCH', raw: '{bad', headers: { ...demoH(), 'Content-Type': 'application/json' } });
  assert.equal(r.status, 400);
});

test('webhooks: HMAC on the raw body; shop in the body must match the header', async () => {
  const send = (topic, shop, payload, hmac) => {
    const body = JSON.stringify(payload);
    return fetch(`${base}/webhooks/shopify`, {
      method: 'POST', body,
      headers: { 'Content-Type': 'application/json', 'X-Shopify-Topic': topic, 'X-Shopify-Shop-Domain': shop, 'X-Shopify-Webhook-Id': `w${Math.random()}`,
        'X-Shopify-Hmac-Sha256': hmac ?? createHmac('sha256', SECRET).update(body).digest('base64') },
    });
  };
  assert.equal((await send('orders/create', other.shop, { admin_graphql_api_id: 'gid://shopify/Order/1' }, 'bad')).status, 401);
  assert.equal((await fetch(`${base}/webhooks/shopify`, { method: 'POST' })).status, 401);
  assert.equal((await send('orders/create', other.shop, { admin_graphql_api_id: 'gid://shopify/Order/1' })).status, 200);
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(db.getDb().prepare(`SELECT COUNT(*) c FROM jobs WHERE key = 'sync_order:gid://shopify/Order/1'`).get().c, 1);
  // A signed uninstall body of shop A replayed with shop B's header does nothing to B.
  await send('app/uninstalled', other.shop, { myshopify_domain: 'altcineva.myshopify.com' });
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(db.getStore(other.id).uninstalled_at, null);
});

test('open demo mode (no password) never exposes a real store', async () => {
  Object.assign(config, { demo: true, adminPassword: '' });
  try {
    const r = await call('/api/me', { auth: false, headers: { 'X-Store-Id': String(other.id) } });
    assert.equal(r.status, 200);
    assert.equal(r.data.store.id, demo.id);
    assert.equal((await call(`/api/orders/${otherOrder.id}`, { auth: false })).status, 404);
  } finally {
    Object.assign(config, { demo: false, adminPassword: 'parola-buna' });
  }
});
