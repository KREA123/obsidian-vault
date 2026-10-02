import { test, before } from 'node:test';
import assert from 'node:assert/strict';
import { PDFDocument } from 'pdf-lib';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import { ro } from './helpers-i18n.js';
import { renderError } from '../src/core/errors.js';

// End-to-end over the demo store: test providers, in-memory database.
let store;
before(() => {
  db.openDb(':memory:');
  ({ store } = seedDemo());
});

const byName = (name) => db.hydrateOrder(db.getDb().prepare('SELECT * FROM orders WHERE store_id = ? AND name = ?').get(store.id, name));

test('demo import: statuses reflect validation, rules and tags', () => {
  assert.equal(byName('#1101').status, 'ready');
  assert.equal(byName('#1113').status, 'needs_attention'); // no phone
  assert.equal(byName('#1115').status, 'needs_attention'); // no county
  assert.equal(byName('#1114').status, 'on_hold');         // rule: big COD order
  assert.equal(byName('#1117').status, 'on_hold');         // tag "manual"
  assert.equal(byName('#1119').status, 'cancelled');
  assert.equal(byName('#1109').courier, 'sameday');        // rule: easybox
});

test('processing creates AWB + invoice once (idempotent)', async () => {
  const o = byName('#1101');
  const r1 = await P.processOrder(store, o.id);
  assert.equal(r1.ok, true);
  const after1 = db.getOrder(o.id);
  assert.match(after1.awb, /^TEST/);
  assert.equal(after1.invoice_series, 'TEST');
  assert.equal(after1.status, 'shipped');
  assert.equal(after1.test_mode, true);

  const r2 = await P.processOrder(store, o.id);
  assert.equal(r2.ok, true);
  const after2 = db.getOrder(o.id);
  assert.equal(after2.awb, after1.awb);
  assert.equal(after2.invoice_number, after1.invoice_number);
});

test('concurrent clicks never produce two AWBs', async () => {
  const o = byName('#1102');
  const [a, b] = await Promise.all([P.processOrder(store, o.id), P.processOrder(store, o.id)]);
  assert.equal([a, b].filter((r) => r.ok).length, 1);
  const awbs = db.getDb().prepare(`SELECT COUNT(*) c FROM events WHERE order_id = ? AND step = 'awb' AND level = 'success'`).get(o.id).c;
  assert.equal(awbs, 1);
});

test('blocked order explains why, then succeeds after a manual fix', async () => {
  const o = byName('#1113');
  const r = await P.processOrder(store, o.id);
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'ADDRESS_PHONE_MISSING');
  assert.ok(ro(r.error).hint);
  assert.equal(r.error.key, 'errors.ADDRESS_PHONE_MISSING');
  db.updateOrder(o.id, { overrides: { address: { phone: '+40 745 111 222' } } });
  P.validateOrder(store, o.id);
  assert.equal(db.getOrder(o.id).status, 'ready');
  const r2 = await P.processOrder(store, o.id);
  assert.equal(r2.ok, true);
});

test('held orders need force; skipInvoice skips the invoice', async () => {
  const o = byName('#1114');
  assert.equal((await P.processOrder(store, o.id, { force: false })).ok, false);
  db.updateOrder(o.id, { overrides: { skipInvoice: true } });
  const r = await P.processOrder(store, o.id, { force: true });
  assert.equal(r.ok, true);
  assert.equal(db.getOrder(o.id).invoice_number, null);
});

test('labels merge into one PDF; cancel AWB resets the order', async () => {
  const ids = ['#1101', '#1102', '#1105'].map((n) => byName(n).id);
  await P.processOrder(store, ids[2]);
  const { pdf } = await P.mergedLabels(store, ids, 'A6');
  assert.equal((await PDFDocument.load(pdf)).getPageCount(), 3);

  await P.cancelAwb(store, ids[2]);
  const o = db.getOrder(ids[2]);
  assert.equal(o.awb, null);
  assert.equal(o.status, 'ready');
  assert.ok(o.invoice_number, 'invoice is kept; storno is a separate, explicit action');
  await P.stornoInvoice(store, ids[2]);
  assert.equal(db.getOrder(ids[2]).invoice_number, null);
});

test('tracking: delivery marks COD as collected', async () => {
  const o = byName('#1101');
  // Age the test AWB so the test courier reports it delivered.
  const cache = db.storeCache(store.id);
  const issued = cache.get('mock:issued');
  issued[db.getOrder(o.id).awb].at -= 60 * 60_000;
  cache.set('mock:issued', issued, 3600);
  await P.trackStore(store);
  const after = db.getOrder(o.id);
  assert.equal(after.tracking_status, TrackingStatus.DELIVERED);
  assert.equal(after.status, 'delivered');
  assert.ok(after.cod_collected_at);
});

test('live mode without configured courier gives a clear error', async () => {
  const live = { ...store, demo: false, settings: { ...store.settings, mode: 'live' } };
  const o = byName('#1106');
  const r = await P.processOrder(live, o.id);
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'PROVIDER_NOT_CONFIGURED');
  assert.match(ro(r.error).hint, /Setări → Curieri/);
  assert.match(renderError(r.error, 'en').hint, /Settings → Couriers/);
});
