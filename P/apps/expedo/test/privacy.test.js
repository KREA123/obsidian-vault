import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { config } from '../src/config.js';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { createApp } from '../src/server.js';
import { encrypt, sealJson, openJson, sealText, openText, isSealed, blindIndex } from '../src/lib/crypto.js';
import { orderIdentity, searchHashes, phoneHash } from '../src/core/identity.js';
import { applyRetention, redactOrder, pruneAccessLog, handleDataRequest, handleCustomerRedact } from '../src/core/privacy.js';
import { sanitizeSettings } from '../src/core/settings.js';
import { handlers } from '../src/worker.js';

// Customer data protection: encryption at rest, migration of old plaintext rows, search through
// keyed hashes, retention (never on orders in progress), redaction, access log, GDPR webhooks.

const SECRET = 'test-secret';
let store, server, base, cookie;
const byName = (name, s = store) => db.hydrateOrder(db.getDb().prepare('SELECT * FROM orders WHERE store_id = ? AND name = ?').get(s.id, name));
const rawRow = (id) => db.getDb().prepare('SELECT * FROM orders WHERE id = ?').get(id);
const daysAgo = (n) => new Date(Date.now() - n * 86400_000).toISOString();

before(async () => {
  Object.assign(config, { demo: false, adminPassword: 'parola-buna' });
  Object.assign(config.shopify, { apiSecret: SECRET, apiKey: 'key123' });
  db.openDb(':memory:');
  ({ store } = seedDemo());
  server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  base = `http://127.0.0.1:${server.address().port}`;
  const login = await fetch(`${base}/login`, { method: 'POST', body: new URLSearchParams({ password: 'parola-buna' }), redirect: 'manual' });
  cookie = login.headers.get('set-cookie').split(';')[0];
});
after(() => server?.close());

async function call(path, { method = 'GET', body, headers = {}, auth = true } = {}) {
  const h = { 'X-Store-Id': String(store.id), ...headers };
  if (auth) h.Cookie = cookie;
  if (method !== 'GET') h['X-Expedo-Request'] = '1';
  if (body !== undefined) h['Content-Type'] = 'application/json';
  const res = await fetch(base + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
  const type = res.headers.get('content-type') || '';
  return { status: res.status, data: type.includes('json') ? await res.json() : await res.text(), headers: res.headers };
}

// ---------- encryption ----------

test('sealing: round trip, random IV, tampering detected, legacy plaintext still readable', () => {
  const v = { name: 'Andreea Popescu', phone: '0745123456', nested: [1, 'ă î ș ț'] };
  const a = sealJson(v);
  const b = sealJson(v);
  assert.ok(isSealed(a));
  assert.notEqual(a, b, 'a new IV every time');
  assert.deepEqual(openJson(a), v);
  assert.ok(!a.includes('Popescu') && !a.includes('0745123456'));
  assert.equal(openText(sealText('Telefonul „0712” nu pare valid.')), 'Telefonul „0712” nu pare valid.');
  // GCM: a flipped byte is refused, never decrypted into garbage.
  const buf = Buffer.from(a.slice(5), 'base64');
  buf[buf.length - 1] ^= 1;
  assert.throws(() => openText(`enc1:${buf.toString('base64')}`));
  assert.equal(openJson(`enc1:${buf.toString('base64')}`, 'fallback'), 'fallback');
  // Rows from before the migration.
  assert.deepEqual(openJson('{"a":1}'), { a: 1 });
  assert.equal(openText('mesaj vechi'), 'mesaj vechi');
  assert.equal(sealJson(null), null);
  assert.equal(openJson(null, []).length, 0);
});

test('blind index: stable, keyed, scoped per store', () => {
  assert.equal(blindIndex('store:1', 'p:0745123456'), blindIndex('store:1', 'p:0745123456'));
  assert.notEqual(blindIndex('store:1', 'p:0745123456'), blindIndex('store:2', 'p:0745123456'));
  const plainSha = createHmac('sha256', '').update('store:1|p:0745123456').digest('hex').slice(0, 32);
  assert.notEqual(blindIndex('store:1', 'p:0745123456'), plainSha, 'needs the app secret');
  assert.equal(phoneHash(1, '+40 745 123 456'), phoneHash(1, '0745123456'), 'phone normalized first');
  assert.equal(phoneHash(1, ''), null);
});

test('at rest: order data, overrides, issues, events and cache are encrypted in the database', async () => {
  const o = byName('#1113'); // no phone → has issues
  db.updateOrder(o.id, { overrides: { address: { phone: '0722111333', name: 'Elena Dumitrescu' } } });
  db.logEvent(store.id, o.id, 'error', 'validate', 'Telefonul „0711” nu pare valid.', { body: { phone: '0711' } });
  await P.processOrder(store, byName('#1101').id);
  const row = rawRow(o.id);
  for (const col of ['data', 'overrides', 'issues']) assert.ok(isSealed(row[col]), col);
  const dump = JSON.stringify(db.getDb().prepare('SELECT * FROM orders').all()) + JSON.stringify(db.getDb().prepare('SELECT * FROM events').all())
    + JSON.stringify(db.getDb().prepare('SELECT * FROM cache').all());
  for (const secret of ['Dumitrescu', 'Popescu', '0745123456', '0722111333', '0711', 'example.com', 'Observatorului', 'Cluj-Napoca']) {
    assert.ok(!dump.includes(secret), `${secret} not in plaintext`);
  }
  // ...and everything reads back.
  const back = db.getOrder(o.id);
  assert.equal(back.data.customerName, 'Elena Dumitrescu');
  assert.equal(back.overrides.address.phone, '0722111333');
  assert.ok(Array.isArray(back.issues));
  assert.equal(db.orderEvents(o.id).at(-1).message, 'Telefonul „0711” nu pare valid.');
  assert.deepEqual(db.orderEvents(o.id).at(-1).data, { body: { phone: '0711' } });
  assert.ok(db.storeCache(store.id).get('mock:issued'), 'test courier cache still readable');
  // The keyed hashes are never sent to the browser.
  const r = await call(`/api/orders/${o.id}`);
  assert.ok(!JSON.stringify(r.data).includes(row.phone_hash));
});

test('migration: plaintext rows of an older database are encrypted once, with hashes and finished_at', () => {
  const dir = mkdtempSync(join(tmpdir(), 'expedo-mig-'));
  const file = join(dir, 'old.db');
  try {
    // Schema as written by the previous version (no hash / retention columns, plaintext JSON).
    const old = new DatabaseSync(file);
    old.exec(`CREATE TABLE stores (id INTEGER PRIMARY KEY, shop TEXT NOT NULL UNIQUE, name TEXT, access_token TEXT, scopes TEXT, settings TEXT NOT NULL DEFAULT '{}',
        demo INTEGER NOT NULL DEFAULT 0, installed_at TEXT NOT NULL DEFAULT (datetime('now')), uninstalled_at TEXT);
      CREATE TABLE orders (id INTEGER PRIMARY KEY, store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE, shopify_id TEXT NOT NULL, name TEXT NOT NULL,
        data TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT (datetime('now')), payment_method TEXT,
        total REAL, cod_amount REAL NOT NULL DEFAULT 0, courier TEXT, service TEXT, awb TEXT, awb_at TEXT, shipping_cost REAL, tracking_status TEXT, tracking_text TEXT,
        tracking_at TEXT, invoice_provider TEXT, invoice_series TEXT, invoice_number TEXT, invoice_url TEXT, invoice_at TEXT, fulfillment_id TEXT, fulfilled_at TEXT,
        cod_collected_at TEXT, paid_marked_at TEXT, issues TEXT NOT NULL DEFAULT '[]', last_error TEXT, overrides TEXT NOT NULL DEFAULT '{}',
        test_mode INTEGER NOT NULL DEFAULT 0, invoice_test INTEGER NOT NULL DEFAULT 0, processing_at TEXT, UNIQUE (store_id, shopify_id));
      CREATE TABLE events (id INTEGER PRIMARY KEY, store_id INTEGER NOT NULL, order_id INTEGER, at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        level TEXT NOT NULL DEFAULT 'info', step TEXT, message TEXT NOT NULL, data TEXT);
      CREATE TABLE cache (store_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, expires_at INTEGER NOT NULL, PRIMARY KEY (store_id, key));
      INSERT INTO stores (id, shop) VALUES (1, 'vechi.myshopify.com');`);
    const data = { name: '#1', customerName: 'Ion Marin', email: 'Ion.Marin@Example.com', phone: '+40 766 555 444', shippingAddress: { name: 'Ion Marin', phone: '0766555444', city: 'Voluntari' }, lines: [], shippingLines: [] };
    old.prepare(`INSERT INTO orders (id, store_id, shopify_id, name, data, status, created_at, issues, last_error, overrides, awb, tracking_status, tracking_at)
      VALUES (1, 1, 'gid://shopify/Order/1', '#1', ?, 'delivered', '2026-01-01T10:00:00Z', ?, ?, ?, 'AWB1', 'delivered', '2026-01-03T10:00:00.000Z')`)
      .run(JSON.stringify(data), JSON.stringify([{ message: 'Telefonul „0766” nu pare valid.' }]), JSON.stringify({ message: 'eroare', details: { phone: '0766555444' } }), JSON.stringify({ address: { phone: '0766555444' } }));
    old.prepare(`INSERT INTO orders (id, store_id, shopify_id, name, data, status, created_at) VALUES (2, 1, 'gid://shopify/Order/2', '#2', ?, 'ready', '2026-02-01T10:00:00Z')`)
      .run(JSON.stringify({ ...data, name: '#2' }));
    old.prepare(`INSERT INTO events (store_id, order_id, message, data) VALUES (1, 1, 'Comanda #1 a fost modificată manual.', ?)`).run(JSON.stringify({ phone: '0766555444' }));
    old.prepare(`INSERT INTO cache (store_id, key, value, expires_at) VALUES (1, 'mock:issued', ?, ?)`).run(JSON.stringify({ AWB1: { shipment: { recipient: { name: 'Ion Marin' } } } }), Date.now() + 1e6);
    old.close();

    db.openDb(file);
    const rows = db.getDb().prepare('SELECT * FROM orders ORDER BY id').all();
    for (const r of rows) {
      assert.ok(isSealed(r.data) && isSealed(r.overrides) && isSealed(r.issues), `order ${r.id} encrypted`);
      assert.equal(r.phone_hash, phoneHash(1, '0766555444'));
      assert.ok(r.email_hash && r.search_terms);
    }
    assert.ok(isSealed(rows[0].last_error));
    assert.equal(rows[0].finished_at, '2026-01-03T10:00:00.000Z', 'delivered: finished when tracked');
    assert.equal(rows[1].finished_at, null, 'ready: not finished');
    const ev = db.getDb().prepare('SELECT * FROM events').get();
    assert.ok(isSealed(ev.message) && isSealed(ev.data));
    assert.ok(isSealed(db.getDb().prepare('SELECT value FROM cache').get().value));
    const raw = JSON.stringify(rows) + JSON.stringify(ev);
    assert.ok(!raw.includes('Marin') && !raw.includes('0766'));
    // Same content after migration.
    const o1 = db.getOrder(1);
    assert.deepEqual(o1.data, data);
    assert.equal(o1.issues[0].message, 'Telefonul „0766” nu pare valid.');
    assert.equal(o1.last_error.details.phone, '0766555444');
    assert.equal(db.orderEvents(1)[0].message, 'Comanda #1 a fost modificată manual.');
    assert.equal(db.storeCache(1).get('mock:issued').AWB1.shipment.recipient.name, 'Ion Marin');
    // Idempotent: a second start does not encrypt twice.
    const before2 = db.getDb().prepare('SELECT data FROM orders WHERE id = 1').get().data;
    db.openDb(file);
    assert.equal(db.getDb().prepare('SELECT data FROM orders WHERE id = 1').get().data, before2);
    assert.deepEqual(db.getOrder(1).data, data);
  } finally {
    db.openDb(':memory:');
    ({ store } = seedDemo());
    rmSync(dir, { recursive: true, force: true });
  }
});

// ---------- search ----------

test('search: phone in any format, e-mail, whole name words, order number, AWB; not street or partial names', async () => {
  const ids = (r) => r.data.orders.map((o) => o.name).sort();
  const q = async (s) => ids(await call(`/api/orders?status=all&q=${encodeURIComponent(s)}`));
  const andreea = ['#1101', '#1109', '#1119'];
  assert.deepEqual(await q('0745123456'), andreea);
  assert.deepEqual(await q('+40 745 123 456'), andreea);
  assert.deepEqual(await q('ANDREEA.popescu@example.com'), andreea);
  assert.deepEqual(await q('Andreea Popescu'), andreea);
  assert.deepEqual(await q('popescu'), andreea, 'one word, any case');
  assert.deepEqual(await q('Lazăr'), ['#1108', '#1117']);
  assert.deepEqual(await q('lazar'), ['#1108', '#1117'], 'without diacritics');
  assert.deepEqual(await q('Andreea Ionescu'), [], 'all words must match');
  assert.deepEqual(await q('Popes'), [], 'partial names are not searchable (hashed)');
  assert.deepEqual(await q('Observatorului'), [], 'street is not searchable');
  assert.deepEqual(await q('#1104'), ['#1104']);
  await P.processOrder(store, byName('#1104').id);
  const awb = byName('#1104').awb;
  assert.deepEqual(await q(awb.slice(0, 9)), ['#1104'], 'partial AWB');
  // Address fixed by hand: the new phone is found.
  const id = byName('#1110').id;
  await call(`/api/orders/${id}`, { method: 'PATCH', body: { address: { phone: '0799 000 111' } } });
  assert.deepEqual(await q('0799000111'), ['#1110']);
  assert.deepEqual(searchHashes(store.id, 'x@y.ro').words, [], 'an e-mail is not split into name words');
});

// ---------- retention ----------

/** Sets an order straight into a state, as if it happened `ago` days ago. */
function age(name, fields, ago) {
  const o = byName(name);
  db.updateOrder(o.id, fields);
  db.getDb().prepare('UPDATE orders SET finished_at = CASE WHEN finished_at IS NULL THEN NULL ELSE ? END WHERE id = ?').run(daysAgo(ago), o.id);
  return byName(name);
}

test('retention: removes customer data of old finished orders only; never orders in progress', () => {
  // Old and in progress, in every way an order can be: must stay untouched.
  const inProgress = [
    age('#1102', { awb: 'AWBSHIP', status: 'shipped', tracking_status: 'created' }, 400),
    age('#1103', { awb: 'AWBTRANSIT', status: 'in_transit', tracking_status: 'in_transit' }, 400),
    age('#1113', { status: 'needs_attention' }, 400),
    age('#1114', { status: 'on_hold' }, 400),
    age('#1116', { status: 'ready' }, 400),
  ];
  db.getDb().prepare(`UPDATE orders SET created_at = ?, updated_at = ? WHERE store_id = ? AND name IN ('#1102','#1103','#1113','#1114','#1116')`).run(daysAgo(400), daysAgo(400), store.id);
  for (const o of inProgress) assert.equal(o.finished_at, null, `${o.name} is not finished`);
  // A delivered order still being processed right now (claimed) is not touched either.
  const busy = age('#1105', { awb: 'AWBBUSY', status: 'delivered', tracking_status: 'delivered' }, 400);
  db.claimOrder(busy.id);

  const delivered = age('#1106', { awb: 'AWBOLD', status: 'delivered', tracking_status: 'delivered', invoice_series: 'FCT', invoice_number: '77', cod_amount: 300, cod_collected_at: daysAgo(200) }, 200);
  const returned = age('#1107', { awb: 'AWBRET', status: 'returned', tracking_status: 'returned' }, 181);
  const cancelled = byName('#1119');
  db.getDb().prepare('UPDATE orders SET finished_at = ? WHERE id = ?').run(daysAgo(190), cancelled.id);
  const recent = age('#1108', { awb: 'AWBNEW', status: 'delivered', tracking_status: 'delivered' }, 10);
  db.logEvent(store.id, delivered.id, 'error', 'awb', 'Localitatea „Observatorului 112” nu există.', { details: { phone: '0745' } });
  db.logEvent(store.id, delivered.id, 'info', 'edit', 'Comanda a fost modificată manual.', { address: { phone: '0745' } });
  db.logEvent(store.id, delivered.id, 'success', 'awb', 'AWB AWBOLD generat la Cargus.', { cod: 300 });
  const snapshot = Object.fromEntries(inProgress.map((o) => [o.id, rawRow(o.id)]));

  const r = applyRetention(store);
  assert.equal(r.redacted, 3);
  for (const o of inProgress) assert.deepEqual(rawRow(o.id), snapshot[o.id], `${o.name} untouched`);
  assert.equal(byName('#1105').redacted_at, null, 'claimed order skipped');
  assert.equal(byName('#1108').redacted_at, null, 'finished 10 days ago: kept');
  assert.ok(byName('#1108').data.customerName);

  for (const o of [delivered, returned, cancelled]) {
    const red = byName(o.name);
    assert.ok(red.redacted_at, `${o.name} redacted`);
    for (const k of ['customerName', 'email', 'phone', 'shippingAddress', 'billingAddress', 'company', 'note', 'attributes', 'tags']) assert.equal(red.data[k], undefined, `${o.name}.${k}`);
    // Kept for accounting / ramburs reconciliation.
    assert.equal(red.name, o.name);
    assert.equal(red.total, o.total);
    assert.equal(red.status, o.status);
    assert.equal(red.awb, o.awb);
    assert.equal(red.data.total, o.data.total);
    assert.deepEqual(red.data.lines, o.data.lines);
    const row = rawRow(o.id);
    assert.equal(row.phone_hash, null);
    assert.equal(row.email_hash, null);
    assert.equal(row.search_terms, null);
  }
  assert.equal(byName('#1106').invoice_number, '77');
  assert.equal(byName('#1106').cod_amount, 300);
  assert.equal(byName('#1119').status, 'cancelled', 'status survives re-validation of redacted data');
  P.validateOrder(store, cancelled.id);
  assert.equal(byName('#1119').status, 'cancelled');
  // Events: errors and manual edits gone, details dropped, the accounting trail kept.
  const ev = db.orderEvents(delivered.id);
  assert.ok(!ev.some((e) => e.level === 'error' || e.step === 'edit'));
  assert.ok(ev.every((e) => e.data === null));
  assert.ok(ev.some((e) => e.message === 'AWB AWBOLD generat la Cargus.'));
  assert.equal(applyRetention(store).redacted, 0, 'idempotent');
  db.releaseOrder(busy.id);
  assert.equal(applyRetention(store).redacted, 1, 'released: its turn now');
});

test('retention period follows the store setting (90 / 180 / 365 / 730 days)', () => {
  const o = age('#1112', { awb: 'AWB100', status: 'delivered', tracking_status: 'delivered' }, 100);
  db.saveStoreSettings(store.id, { ...store.settings, privacy: { retentionDays: 365 } });
  store = db.getStore(store.id);
  applyRetention(store);
  assert.equal(byName('#1112').redacted_at, null, '100 days < 365');
  db.saveStoreSettings(store.id, { ...store.settings, privacy: { retentionDays: 90 } });
  store = db.getStore(store.id);
  applyRetention(store);
  assert.ok(byName('#1112').redacted_at, '100 days > 90');
  assert.equal(o.id, byName('#1112').id);
  db.saveStoreSettings(store.id, { ...store.settings, privacy: { retentionDays: 180 } });
  store = db.getStore(store.id);
  assert.deepEqual(sanitizeSettings({ privacy: { retentionDays: '365' } }), { privacy: { retentionDays: 365 } });
  for (const bad of [100, '0', '', 'forever', -1]) assert.throws(() => sanitizeSettings({ privacy: { retentionDays: bad } }), String(bad));
});

test('re-imported from Shopify after redaction: data back, redacted again later; cancelled AWB clears finished_at', async () => {
  const o = byName('#1106');
  assert.ok(o.redacted_at);
  const fresh = { ...o.data, customerName: 'Ioana Constantin', email: 'ioana@example.com', shippingAddress: { name: 'Ioana Constantin', phone: '0727000111' }, billingAddress: null };
  db.upsertOrder(store.id, fresh);
  const back = byName('#1106');
  assert.equal(back.redacted_at, null);
  assert.equal(back.data.customerName, 'Ioana Constantin');
  assert.ok(rawRow(o.id).phone_hash);
  assert.equal(applyRetention(store).redacted, 1);
  // Leaving a final state (AWB cancelled → ready again) makes the order "in progress" again.
  const d = age('#1108', { status: 'delivered' }, 5);
  assert.ok(d.finished_at);
  db.updateOrder(d.id, { awb: null, status: 'ready' });
  assert.equal(byName('#1108').finished_at, null);
});

test('worker: daily privacy job is scheduled per store and runs retention + access log pruning', async () => {
  const { schedulePeriodic } = await import('../src/worker.js');
  schedulePeriodic();
  const job = db.getDb().prepare(`SELECT * FROM jobs WHERE key = ?`).get(`privacy:${store.id}`);
  assert.ok(job);
  assert.ok(new Date(job.run_at) - Date.now() > 23 * 3600_000, 'about a day from now');
  const r = await handlers.privacy_cleanup(store);
  assert.equal(typeof r.redacted, 'number');
});

// ---------- access log ----------

test('access log: order page, labels, invoice, picking, COD export; who and when', async () => {
  db.getDb().exec('DELETE FROM access_log');
  const id = byName('#1101').id;
  await P.processOrder(store, id); // AWB + invoice
  await call(`/api/orders/${id}`);
  await call(`/api/orders/${id}`); // reloaded right after an action: one visit
  await call(`/api/labels.pdf?ids=${id}`);
  await call(`/api/orders/${id}/invoice.pdf`);
  await call(`/api/picking?ids=${id},${byName('#1102').id}`);
  await call('/api/cod.csv');
  const rows = db.listAccess(store.id).rows;
  const actions = rows.map((r) => r.action).sort();
  assert.deepEqual(actions, ['cod_export', 'invoice_pdf', 'labels', 'order_view', 'picking', 'picking']);
  assert.ok(rows.every((r) => r.actor === 'admin'));
  assert.ok(rows.filter((r) => r.action !== 'cod_export').every((r) => r.order_name));
  assert.match(rows.find((r) => r.action === 'labels').detail, /^AWB /);
  assert.ok(!JSON.stringify(rows).includes('Popescu'), 'no customer data in the log');

  // Embedded: the Shopify staff user from the session token.
  const other = db.upsertStore({ shop: 'alt.myshopify.com', name: 'Alt', accessToken: 'tok' });
  const oo = P.importOrder(other, { ...byName('#1102').data, shopifyId: 'gid://shopify/Order/9', name: '#ALT9' });
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const h = b64({ alg: 'HS256', typ: 'JWT' });
  const p = b64({ dest: 'https://alt.myshopify.com', aud: 'key123', exp: now + 60, nbf: now - 1, sub: '4242' });
  const token = `${h}.${p}.${createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url')}`;
  await call(`/api/orders/${oo.id}`, { auth: false, headers: { Authorization: `Bearer ${token}` } });
  const alt = db.listAccess(other.id).rows;
  assert.equal(alt.length, 1);
  assert.equal(alt[0].actor, 'shopify-session 4242');
  assert.equal(db.listAccess(store.id).rows.filter((r) => r.order_name === '#ALT9').length, 0, 'per store');

  // API: filter by action and order, other store's rows invisible.
  const api = await call('/api/access-log?action=picking');
  assert.equal(api.status, 200);
  assert.equal(api.data.entries.length, 2);
  assert.deepEqual((await call('/api/access-log?order=1102')).data.entries.map((e) => e.order_name), ['#1102']);
  assert.equal((await call('/api/access-log?action=nonsense')).data.total, rows.length, 'unknown action = no filter');
  assert.equal((await call('/api/access-log?order=%25')).data.total, 0, '% is literal');
  assert.equal((await call('/api/access-log', { auth: false })).status, 401);
});

test('access log is pruned after 365 days', () => {
  db.getDb().prepare(`INSERT INTO access_log (store_id, at, actor, action) VALUES (?, ?, 'admin', 'order_view'), (?, ?, 'admin', 'order_view')`)
    .run(store.id, daysAgo(366), store.id, daysAgo(300));
  const before = db.getDb().prepare('SELECT COUNT(*) c FROM access_log').get().c;
  assert.equal(pruneAccessLog(), 1);
  assert.equal(db.getDb().prepare('SELECT COUNT(*) c FROM access_log').get().c, before - 1);
});

// ---------- GDPR webhooks ----------

const sendWebhook = (topic, shop, payload) => {
  const body = JSON.stringify(payload);
  return fetch(`${base}/webhooks/shopify`, {
    method: 'POST', body,
    headers: { 'Content-Type': 'application/json', 'X-Shopify-Topic': topic, 'X-Shopify-Shop-Domain': shop, 'X-Shopify-Webhook-Id': `w${Math.random()}`,
      'X-Shopify-Hmac-Sha256': createHmac('sha256', SECRET).update(body).digest('base64') },
  });
};
const settle = () => new Promise((r) => setTimeout(r, 30));

test('customers/data_request: logged in the access log and Activitate; export file has the data', async () => {
  const andreea = byName('#1109');
  const res = await sendWebhook('customers/data_request', store.shop, {
    shop_domain: store.shop, customer: { id: 1, email: 'andreea.popescu@example.com', phone: '' }, orders_requested: [5000001109], data_request: { id: 9001 },
  });
  assert.equal(res.status, 200);
  await settle();
  const logged = db.listAccess(store.id, { action: 'data_request' }).rows;
  // #1119 is already redacted (retention test above): no e-mail hash left to find it by.
  assert.deepEqual(logged.map((r) => r.order_name).sort(), ['#1101', '#1109'], 'listed order + same e-mail');
  assert.ok(logged.every((r) => r.actor === 'shopify' && r.detail.includes('9001')));
  const ev = db.storeEvents(store.id, 5).find((e) => e.step === 'gdpr');
  assert.equal(ev.level, 'warning');
  assert.match(ev.message, /#1109/);
  assert.match(ev.data.hint, /Descarcă datele/);

  const exp = await call(`/api/customer-export?ids=${andreea.id}`);
  assert.equal(exp.status, 200);
  assert.match(exp.headers.get('content-disposition'), /attachment/);
  assert.equal(exp.data.orders[0].customer.name, 'Andreea Popescu');
  assert.equal(exp.data.orders[0].customer.phone, '0745123456');
  assert.ok(exp.data.orders[0].history.length);
  assert.equal(db.listAccess(store.id, { action: 'customer_export' }).rows[0].order_name, '#1109');
  assert.equal((await call('/api/customer-export?ids=999999')).status, 404);

  // A customer we know nothing about: still recorded, nothing to send.
  assert.equal(handleDataRequest(store, { customer: { email: 'nimeni@example.com' }, orders_requested: [] }), 0);
  assert.match(db.listAccess(store.id, { action: 'data_request' }).rows[0].detail, /nicio comandă/);
});

test('customers/redact: data removed from the listed orders and those with the same e-mail; not by shared phone', async () => {
  // Someone else ordered with Andreea's phone (family): their order must survive.
  const relative = P.importOrder(store, { ...byName('#1102').data, shopifyId: 'gid://shopify/Order/88', name: '#1188', email: 'ruda@example.com', customerName: 'Rudă Popescu', phone: '0745123456' });
  await sendWebhook('customers/redact', store.shop, { shop_domain: store.shop, customer: { id: 1, email: 'andreea.popescu@example.com', phone: '0745123456' }, orders_to_redact: [5000001101] });
  await settle();
  for (const n of ['#1101', '#1109']) {
    const o = byName(n);
    assert.ok(o.redacted_at, n);
    assert.equal(o.data.customerName, undefined);
  }
  assert.equal(byName('#1188').redacted_at, null);
  assert.equal(byName('#1188').data.customerName, 'Rudă Popescu');
  assert.ok(byName('#1101').awb, 'accounting trail kept');
  assert.equal(db.listAccess(store.id, { action: 'customer_redact' }).rows.length, 2);
  assert.match(db.storeEvents(store.id, 3).find((e) => e.step === 'gdpr').message, /ștergerea/);
  // The test courier forgot the shipment (recipient) of the redacted test AWB.
  const issued = db.storeCache(store.id).get('mock:issued');
  assert.equal(issued[byName('#1101').awb].shipment, undefined);
  assert.equal(handleCustomerRedact(store, { orders_to_redact: [5000001101] }), 0, 'already done');
  // A redacted order's page still renders.
  const page = await call(`/api/orders/${byName('#1109').id}`);
  assert.equal(page.status, 200);
  assert.ok(page.data.order.redactedAt);
  assert.equal(relative.name, '#1188');
});

test('shop/redact: every row of the store goes, access log included; other stores untouched', async () => {
  const gone = db.upsertStore({ shop: 'pleaca.myshopify.com', name: 'Pleacă', accessToken: 'tok' });
  const o = P.importOrder(gone, { ...byName('#1103').data, shopifyId: 'gid://shopify/Order/77', name: '#P1' });
  db.logAccess(gone.id, { actor: 'admin', action: 'order_view', orderId: o.id, orderName: '#P1' });
  db.storeCache(gone.id).set('k', { a: 1 });
  P.enqueue(gone.id, 'track_store', {}, { key: `track:${gone.id}` });
  await sendWebhook('shop/redact', gone.shop, { shop_domain: gone.shop, shop_id: 1 });
  await settle();
  assert.equal(db.getStore(gone.id), undefined);
  for (const t of ['orders', 'events', 'jobs', 'cache', 'access_log', 'integrations']) {
    assert.equal(db.getDb().prepare(`SELECT COUNT(*) c FROM ${t} WHERE store_id = ?`).get(gone.id).c, 0, t);
  }
  assert.ok(db.getDb().prepare('SELECT COUNT(*) c FROM orders WHERE store_id = ?').get(store.id).c > 0);
});

test('redactOrder refuses another store\'s order', () => {
  const other = db.getStoreByShop('alt.myshopify.com');
  assert.equal(redactOrder(other, byName('#1110').id, 'gdpr'), false);
  assert.equal(byName('#1110').redacted_at, null);
});

// ---------- public pages ----------

test('privacy and terms pages: public, both languages, accurate basics', async () => {
  for (const [path, lang, words] of [
    ['/confidentialitate', 'ro', ['ARTEMIS DIGITAL SRL', 'office@krea.ro', 'AES-256-GCM', '180', '72 de ore']],
    ['/privacy', 'en', ['ARTEMIS DIGITAL SRL', 'processor', '72 hours', 'Render Services']],
    ['/termeni', 'ro', ['Acord de prelucrare a datelor', 'Sub-împuterniciți', 'SmartBill', 'Cargus', 'Shopify', '72 de ore']],
    ['/terms', 'en', ['Data Processing Agreement', 'Sub-processors', 'controller', '72 hours']],
  ]) {
    const r = await fetch(base + path);
    assert.equal(r.status, 200, path);
    const text = await r.text();
    assert.match(text, new RegExp(`<html lang="${lang}">`));
    for (const w of words) assert.ok(text.includes(w), `${path}: ${w}`);
    assert.ok(!/ISO 27001|SOC 2|certificat/i.test(text), `${path}: no certification claims`);
  }
});
