import { test, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { couriers } from '../src/couriers/index.js';
import { invoicers } from '../src/invoicing/index.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import { ProcessingError } from '../src/core/errors.js';
import { runDueJobs, recoverJobs } from '../src/worker.js';
import { PDFDocument } from 'pdf-lib';

// Edge cases of the processing pipeline: test mode vs live, status machine, idempotency,
// job dedupe. A fake "real" courier + invoicer stand in for live providers.

const calls = { createShipment: 0, cancelShipment: 0, getLabel: 0, createInvoice: 0, registerPayment: [] };
let shipmentBehaviour = null;
const fakeCourier = {
  id: 'fake', name: 'Curier fals', trackingUrl: (awb) => `https://fake.example/${awb}`, credentialFields: [], settingsFields: [],
  async testConnection() { return { ok: true }; },
  async createShipment() {
    calls.createShipment++;
    if (shipmentBehaviour) return shipmentBehaviour();
    return { awb: `REAL${calls.createShipment}`, price: 20 };
  },
  async getLabel() {
    calls.getLabel++;
    const d = await PDFDocument.create(); d.addPage([100, 100]);
    return Buffer.from(await d.save());
  },
  async cancelShipment() { calls.cancelShipment++; },
  async track(ctx, awbs) { return awbs.map((awb) => ({ awb, status: TrackingStatus.IN_TRANSIT, statusText: 'tranzit' })); },
};
const fakeInvoicer = {
  id: 'fakeinv', name: 'Facturare falsă', credentialFields: [], settingsFields: [],
  async testConnection() { return { ok: true }; },
  async createInvoice() { calls.createInvoice++; return { series: 'REAL', number: String(calls.createInvoice) }; },
  async getPdf() { return Buffer.from('%PDF'); },
  async cancelInvoice() {},
  async registerPayment(ctx, p) { calls.registerPayment.push(p); },
};

let store;
let seq = 0;

function normalized(extra = {}) {
  seq++;
  const addr = { firstName: 'Ion', lastName: 'Pop', name: 'Ion Pop', company: '', address1: 'Str. Lungă 1', address2: '', city: 'Brașov', province: 'Brașov', provinceCode: 'BV', zip: '500096', countryCode: 'RO', phone: '0744111222' };
  return {
    shopifyId: `gid://shopify/Order/${9000 + seq}`, name: `#${9000 + seq}`, createdAt: new Date().toISOString(), cancelledAt: null,
    currency: 'RON', financialStatus: 'PENDING', fulfillmentStatus: 'UNFULFILLED', paymentMethod: 'cod',
    total: 125, subtotal: 100, shippingTotal: 25, outstanding: 125, codAmount: 125, email: 'ion@example.com', phone: addr.phone,
    customerName: 'Ion Pop', shippingAddress: addr, billingAddress: addr, company: null,
    lines: [{ id: 'L1', title: 'Produs', variantTitle: '', sku: 'P1', quantity: 1, unitPrice: 100, vatRate: 21, requiresShipping: true, isGiftCard: false }],
    shippingLines: [{ title: 'Curier', price: 25, vatRate: 21 }], shippingMethod: 'Curier', tags: [], attributes: [], weightGrams: 1000,
    fulfillmentOrders: [{ id: 'FO1', status: 'OPEN' }],
    ...extra,
  };
}

const setMode = (mode, more = {}) => {
  const s = { ...db.getStore(store.id).settings, mode, ...more };
  db.saveStoreSettings(store.id, s);
  store = db.getStore(store.id);
};
const add = (extra) => P.importOrder(store, normalized(extra), { source: 'test' });

before(() => {
  db.openDb(':memory:');
  couriers.fake = fakeCourier;
  invoicers.fakeinv = fakeInvoicer;
  store = db.upsertStore({ shop: 'live-test.myshopify.com', name: 'Live', accessToken: 'tok' });
  db.saveStoreSettings(store.id, {
    mode: 'test',
    courier: { default: 'fake' },
    invoicing: { provider: 'fakeinv', when: 'on_awb' },
    // Never reach the real Shopify API from the tests.
    fulfillment: { fulfillInShopify: false, markCodPaidOnDelivery: false, registerCodPayment: true },
  });
  db.saveIntegration(store.id, 'courier', 'fake', { credentials: { key: 'x' }, settings: {} });
  db.saveIntegration(store.id, 'invoicing', 'fakeinv', { credentials: { key: 'y' }, settings: {} });
  store = db.getStore(store.id);
});

beforeEach(() => {
  setMode('test');
  shipmentBehaviour = null;
});

test('an order processed in test mode is never finished with real providers after going live', async () => {
  const o = add();
  assert.equal((await P.processOrder(store, o.id)).ok, true);
  assert.match(db.getOrder(o.id).awb, /^TEST/);
  assert.equal(db.getOrder(o.id).invoice_test, true);

  setMode('live');
  const before = { ...calls };
  const r = await P.processOrder(store, o.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'TEST_DATA');
  assert.equal(calls.createInvoice, before.createInvoice, 'no real invoice on top of a test AWB');

  // Explicit reset, then real processing.
  await P.resetTestData(store, o.id);
  const reset = db.getOrder(o.id);
  assert.equal(reset.awb, null);
  assert.equal(reset.invoice_number, null);
  assert.equal(reset.status, 'ready');
  const r2 = await P.processOrder(store, o.id, { force: true });
  assert.equal(r2.ok, true);
  const live = db.getOrder(o.id);
  assert.match(live.awb, /^REAL/);
  assert.equal(live.test_mode, false);
  assert.equal(live.invoice_series, 'REAL');
  assert.equal(live.invoice_test, false);
});

test('a test invoice and a real AWB keep separate flags', async () => {
  const o = add();
  await P.processOrder(store, o.id, { steps: ['invoice'], force: true });
  assert.equal(db.getOrder(o.id).invoice_series, 'TEST');
  setMode('live');
  const r = await P.processOrder(store, o.id, { force: true });
  assert.equal(r.error?.code, 'TEST_DATA', 'a real AWB must not be paired with a test invoice');
});

test('real AWBs keep using the real courier while the store is in test mode; Shopify untouched', async () => {
  setMode('live');
  const o = add();
  assert.equal((await P.processOrder(store, o.id, { force: true })).ok, true);
  setMode('test');
  const labels = calls.getLabel;
  await P.mergedLabels(store, [o.id], 'A6');
  assert.equal(calls.getLabel, labels + 1, 'label of a real AWB comes from the real courier');
  await assert.rejects(P.cancelAwb(store, o.id), (e) => e.code === 'REAL_AWB_IN_TEST_MODE');
  assert.ok(db.getOrder(o.id).awb, 'AWB kept');
  // Tracking a real AWB in test mode asks the real courier.
  await P.trackStore(store);
  assert.equal(db.getOrder(o.id).tracking_status, TrackingStatus.IN_TRANSIT);
});

test('order cancelled in Shopify after the AWB: needs attention, no invoice, no fulfillment', async () => {
  const o = add();
  await P.processOrder(store, o.id, { steps: ['awb'], force: true });
  const data = db.getOrder(o.id).data;
  P.importOrder(store, { ...data, cancelledAt: new Date().toISOString() });
  assert.equal(db.getOrder(o.id).status, 'needs_attention');
  const r = await P.processOrder(store, o.id, { steps: ['invoice'], force: true });
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'ORDER_CANCELLED');
  assert.equal(db.getOrder(o.id).invoice_number, null);
  await P.cancelAwb(store, o.id);
  assert.equal(db.getOrder(o.id).status, 'cancelled');
});

test('auto-processing a cancelled order leaves it cancelled (not "needs attention")', async () => {
  const o = add({ cancelledAt: new Date().toISOString() });
  assert.equal(db.getOrder(o.id).status, 'cancelled');
  const r = await P.processOrder(store, o.id);
  assert.equal(r.ok, false);
  assert.equal(db.getOrder(o.id).status, 'cancelled');
  assert.equal(db.getOrder(o.id).last_error, null);
});

test('courier reports the AWB cancelled → needs attention, not "in delivery"', () => {
  const o = add();
  db.updateOrder(o.id, { awb: 'X1', awb_at: new Date().toISOString(), tracking_status: TrackingStatus.CANCELLED });
  assert.equal(P.deriveStatus(db.getOrder(o.id)), 'needs_attention');
});

test('an error after the AWB (invoice/fulfillment) keeps the order in "needs attention" even while moving', () => {
  const o = add();
  db.updateOrder(o.id, { awb: 'X2', tracking_status: TrackingStatus.IN_TRANSIT, last_error: { step: 'invoice', message: 'x' } });
  assert.equal(P.deriveStatus(db.getOrder(o.id)), 'needs_attention');
});

test('held order stays on hold after an invoice-only run and after cancelling its AWB', async () => {
  const o = add({ tags: ['manual'] });
  assert.equal(db.getOrder(o.id).status, 'on_hold');
  await P.processOrder(store, o.id, { steps: ['invoice'], force: true });
  assert.equal(db.getOrder(o.id).status, 'on_hold');
  await P.processOrder(store, o.id, { force: true });
  assert.equal(db.getOrder(o.id).status, 'shipped');
  await P.cancelAwb(store, o.id);
  assert.equal(db.getOrder(o.id).status, 'on_hold');
});

test('order fulfilled outside Expedo: shown as shipped, no AWB is created for it', async () => {
  const o = add({ fulfillmentStatus: 'FULFILLED', shippingAddress: { ...normalized().shippingAddress, phone: '' } });
  assert.equal(db.getOrder(o.id).status, 'shipped');
  const before = calls.createShipment;
  setMode('live');
  const r = await P.processOrder(store, o.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(calls.createShipment, before);
});

test('a courier timeout is not retried automatically (the AWB may exist)', async () => {
  setMode('live');
  const o = add();
  shipmentBehaviour = () => { throw new ProcessingError({ code: 'PROVIDER_TIMEOUT', message: 'timeout', retryable: true }); };
  const r = await P.processOrder(store, o.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(r.error.retryable, false);
  const jobs = db.getDb().prepare(`SELECT COUNT(*) c FROM jobs WHERE key = ?`).get(`process:${o.id}`).c;
  assert.equal(jobs, 0);
  assert.match(r.error.hint, /verific/i);
});

test('DB claim: an interrupted run blocks automatic re-processing; a manual run takes over', async () => {
  setMode('live');
  const o = add();
  db.getDb().prepare('UPDATE orders SET processing_at = ? WHERE id = ?').run(new Date(Date.now() - 60 * 60_000).toISOString(), o.id);
  const before = calls.createShipment;
  const r = await P.processOrder(store, o.id);
  assert.equal(r.ok, false);
  assert.equal(r.error.code, 'PROCESSING_INTERRUPTED');
  assert.equal(calls.createShipment, before);
  assert.equal(db.getOrder(o.id).status, 'needs_attention');
  const r2 = await P.processOrder(store, o.id, { force: true });
  assert.equal(r2.ok, true);
  assert.equal(db.getOrder(o.id).processing_at, null);
  // A fresh claim held elsewhere (another process) is respected.
  const o2 = add();
  db.getDb().prepare('UPDATE orders SET processing_at = ? WHERE id = ?').run(new Date().toISOString(), o2.id);
  const r3 = await P.processOrder(store, o2.id, { force: true });
  assert.equal(r3.ok, false);
  assert.equal(r3.error.code, 'ORDER_BUSY');
});

test('processOrder refuses an order of another store', async () => {
  const other = db.upsertStore({ shop: 'other.myshopify.com', accessToken: 't' });
  const o = add();
  const r = await P.processOrder(other, o.id, { force: true });
  assert.equal(r.ok, false);
  assert.equal(db.getOrder(o.id).awb, null);
});

test('COD amount changed in Shopify after the AWB → warning, AWB amount kept', async () => {
  const o = add();
  await P.processOrder(store, o.id, { force: true });
  P.importOrder(store, { ...db.getOrder(o.id).data, codAmount: 100, outstanding: 100, total: 100 });
  const after = db.getOrder(o.id);
  assert.equal(after.cod_amount, 125);
  assert.ok(db.orderEvents(o.id).some((e) => e.level === 'warning' && /ramburs/i.test(e.message)));
});

test('delivery of a real AWB in test mode does not register the payment on a real invoice', async () => {
  setMode('live');
  const o = add();
  await P.processOrder(store, o.id, { force: true });
  setMode('test');
  fakeCourier.track = async (ctx, awbs) => awbs.map((awb) => ({ awb, status: TrackingStatus.DELIVERED, statusText: 'livrat' }));
  const before = calls.registerPayment.length;
  await P.trackStore(store);
  assert.equal(db.getOrder(o.id).status, 'delivered');
  assert.equal(calls.registerPayment.length, before);
  setMode('live');
  const o2 = add();
  await P.processOrder(store, o2.id, { force: true });
  await P.trackStore(store);
  const p = calls.registerPayment.at(-1);
  assert.match(p.date, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(p.amount, 125);
  fakeCourier.track = async (ctx, awbs) => awbs.map((awb) => ({ awb, status: TrackingStatus.IN_TRANSIT, statusText: 'tranzit' }));
});

test('jobs: a webhook arriving while the same sync runs is not lost; retries never get stuck', async () => {
  const d = db.getDb();
  d.prepare(`INSERT INTO jobs (store_id, type, key, payload, status) VALUES (?, 'sync_order', 'k1', '{}', 'running')`).run(store.id);
  P.enqueue(store.id, 'sync_order', {}, { key: 'k1' });
  assert.equal(d.prepare(`SELECT COUNT(*) c FROM jobs WHERE key = 'k1' AND status = 'pending'`).get().c, 1);

  // Crash recovery with a pending twin must not throw and must leave one pending job.
  recoverJobs();
  assert.equal(d.prepare(`SELECT COUNT(*) c FROM jobs WHERE key = 'k1' AND status IN ('pending', 'running')`).get().c, 1);
});

test('worker: a retryable failure while a twin job is pending does not leave the job running', async () => {
  const d = db.getDb();
  setMode('live');
  const o = add();
  // processOrder enqueues its own retry (same key) while the worker job is running.
  shipmentBehaviour = () => { throw new ProcessingError({ code: 'PROVIDER_DOWN', message: 'down', retryable: true }); };
  P.enqueue(store.id, 'process_order', { orderId: o.id }, { key: `process:${o.id}` });
  await runDueJobs();
  const rows = d.prepare(`SELECT status FROM jobs WHERE key = ?`).all(`process:${o.id}`).map((r) => r.status);
  assert.ok(!rows.includes('running'), `job stuck: ${rows}`);
  assert.equal(rows.filter((s) => s === 'pending').length, 1);
});
