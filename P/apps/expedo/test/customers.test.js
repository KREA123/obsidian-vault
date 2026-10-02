import { test, before } from 'node:test';
import assert from 'node:assert/strict';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { customerHistory, openOrdersOfCustomer } from '../src/core/customers.js';
import { planOrder } from '../src/core/build.js';
import { ruleFacts, RULE_FIELDS } from '../src/core/rules.js';
import { withDefaults } from '../src/core/settings.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import { ro, roText } from './helpers-i18n.js';

// Customer refusal history: counted per store by phone OR e-mail hash; warns before the AWB of a
// ramburs order; usable in rules.

let demo, live;
const byName = (s, name) => db.hydrateOrder(db.getDb().prepare('SELECT * FROM orders WHERE store_id = ? AND name = ?').get(s.id, name));
const issueCodes = (o) => o.issues.map((i) => i.code);

before(() => {
  db.openDb(':memory:');
  ({ store: demo } = seedDemo());
  live = db.upsertStore({ shop: 'real.myshopify.com', name: 'Real', accessToken: 'tok' });
  db.saveStoreSettings(live.id, { courier: { default: 'cargus' } });
  live = db.getStore(live.id);
});

let n = 0;
/** An order of `who` in the live store, finished as `outcome` ('delivered' | 'returned' | 'returning' | null). */
function order(who, { outcome = null, payment = 'cod', test = false, ago = 30 } = {}) {
  n++;
  const base = byName(demo, '#1101').data;
  const data = {
    ...base, shopifyId: `gid://shopify/Order/${9000 + n}`, name: `#R${n}`, createdAt: new Date(Date.now() - ago * 86400_000).toISOString(),
    paymentMethod: payment, codAmount: payment === 'cod' ? 100 : 0, outstanding: payment === 'cod' ? 100 : 0, total: 100,
    email: who.email ?? '', phone: '', customerName: who.name || 'Client Test',
    shippingAddress: { ...base.shippingAddress, name: who.name || 'Client Test', phone: who.phone ?? '' }, billingAddress: null,
  };
  const o = P.importOrder(live, data);
  if (!outcome) return o;
  const tracking = outcome === 'returning' ? TrackingStatus.RETURNING : outcome;
  db.updateOrder(o.id, { awb: `AWB${n}`, courier: 'cargus', test_mode: test, cod_amount: data.codAmount, tracking_status: tracking, status: P.deriveStatus({ ...o, awb: `AWB${n}`, tracking_status: tracking }) });
  return db.getOrder(o.id);
}

test('counts returned / refused and delivered parcels by phone, in any format', () => {
  const ion = { phone: '0766 555 444', email: 'ion@example.com' };
  order(ion, { outcome: 'returned' });
  order({ phone: '+40766555444' }, { outcome: 'returning' }); // same phone, no e-mail
  order({ phone: '0040 766 555 444' }, { outcome: 'delivered' });
  order(ion, { outcome: 'delivered', payment: 'card' });
  order(ion, { outcome: 'returned', payment: 'card' });
  order(ion, { outcome: null }); // no AWB yet: shown in the list, not counted
  const current = order(ion);
  const h = customerHistory(live, current);
  assert.equal(h.returned, 3);
  assert.equal(h.refusedCod, 2, 'only ramburs ones are a money risk');
  assert.equal(h.delivered, 2);
  assert.equal(h.total, 5);
  assert.equal(h.orders.length, 6, 'every other order of the customer, not this one');
  assert.ok(!h.orders.some((o) => o.id === current.id));
  assert.equal(h.orders.filter((o) => o.refused).length, 3);
});

test('matches by e-mail separately (another phone), case-insensitive; other customers and stores apart', () => {
  const ana = { phone: '0711000001', email: 'Ana@Example.com' };
  order({ phone: '0722999888', email: 'ana@example.com ' }, { outcome: 'returned' }); // new phone, same e-mail
  const cur = order(ana);
  assert.equal(customerHistory(live, cur).returned, 1);
  const stranger = order({ phone: '0733000002', email: 'altcineva@example.com' });
  assert.equal(customerHistory(live, stranger).total, 0);
  assert.deepEqual(customerHistory(live, order({ phone: '', email: '' })), { returned: 0, refusedCod: 0, delivered: 0, total: 0, orders: [] }, 'no phone and no e-mail: no history');
  // Same phone in the demo store: hashes are per store, so nothing leaks across.
  const elsewhere = P.importOrder(demo, { ...byName(demo, '#1102').data, shopifyId: 'gid://shopify/Order/1', name: '#X1', phone: '0766555444', shippingAddress: { ...byName(demo, '#1102').data.shippingAddress, phone: '0766555444' } });
  assert.equal(customerHistory(demo, elsewhere).total, 0);
});

test('test AWBs (modul de probă) are not real parcels: counted only in the demo store', () => {
  const vlad = { phone: '0744111222' };
  order(vlad, { outcome: 'returned', test: true });
  assert.equal(customerHistory(live, order(vlad)).returned, 0);
});

test('warning issue on a ramburs order before the AWB; message, hint, plural', () => {
  const geo = { phone: '0755123123' };
  order(geo, { outcome: 'returned' });
  order(geo, { outcome: 'returned' });
  order(geo, { outcome: 'delivered' });
  order(geo, { outcome: 'delivered' });
  order(geo, { outcome: 'delivered' });
  const cur = order(geo);
  const issue = cur.issues.find((i) => i.code === 'CUSTOMER_REFUSED_BEFORE');
  assert.equal(issue.level, 'warning');
  assert.equal(ro(issue).message, 'Clientul a refuzat 2 colete înainte (din 5).');
  assert.equal(ro(issue).hint, 'Sună-l înainte de AWB sau cere plata cu cardul.');
  assert.equal(cur.status, 'ready', 'a warning does not block');
  // Card order: already paid, no warning.
  assert.ok(!issueCodes(order(geo, { payment: 'card' })).includes('CUSTOMER_REFUSED_BEFORE'));
  // Only delivered before: no warning.
  const good = { phone: '0755000999' };
  order(good, { outcome: 'delivered' });
  assert.ok(!issueCodes(order(good)).includes('CUSTOMER_REFUSED_BEFORE'));
  // Refused only a card parcel: no ramburs risk shown.
  const cardOnly = { phone: '0755000777' };
  order(cardOnly, { outcome: 'returned', payment: 'card' });
  assert.ok(!issueCodes(order(cardOnly)).includes('CUSTOMER_REFUSED_BEFORE'));
  // Romanian plural from the catalog (Intl.PluralRules 'ro': one / few / other).
  const refused = (count) => ro({ key: 'errors.CUSTOMER_REFUSED_BEFORE', params: { count, total: 200 } }).message;
  assert.equal(refused(1), 'Clientul a refuzat 1 colet înainte (din 200).');
  assert.equal(refused(2), 'Clientul a refuzat 2 colete înainte (din 200).');
  assert.equal(refused(19), 'Clientul a refuzat 19 colete înainte (din 200).');
  assert.equal(refused(20), 'Clientul a refuzat 20 de colete înainte (din 200).');
  assert.equal(refused(101), 'Clientul a refuzat 101 colete înainte (din 200).');
  assert.equal(refused(100), 'Clientul a refuzat 100 de colete înainte (din 200).');
});

test('rule field "Colete refuzate înainte": refused > 0 → hold', () => {
  assert.equal(roText('rules.fields.refusedBefore'), 'Colete refuzate înainte');
  assert.equal(RULE_FIELDS.refusedBefore.type, 'number');
  const settings = withDefaults({ courier: { default: 'cargus' }, rules: [{ name: 'Refuzuri', conditions: [{ field: 'refusedBefore', op: 'gt', value: '0' }], actions: { hold: true } }] });
  const data = byName(demo, '#1101').data;
  assert.equal(ruleFacts(data, null, undefined).refusedBefore, 0);
  assert.equal(planOrder(data, settings, {}, { history: { returned: 0, refusedCod: 0, total: 0 } }).hold, false);
  const p = planOrder(data, settings, {}, { history: { returned: 1, refusedCod: 1, delivered: 0, total: 1 } });
  assert.equal(p.hold, true);
  assert.deepEqual(p.matchedRules, ['Refuzuri']);
  // Through the pipeline: the store rule puts the order on hold.
  db.saveStoreSettings(live.id, { courier: { default: 'cargus' }, rules: [{ id: 'r', name: 'Refuzuri', enabled: true, conditions: [{ field: 'refusedBefore', op: 'gt', value: '0' }], actions: { hold: true } }] });
  live = db.getStore(live.id);
  const mia = { phone: '0766000111' };
  order(mia, { outcome: 'returned' });
  assert.equal(order(mia).status, 'on_hold');
  assert.equal(order({ phone: '0766000222' }).status, 'ready');
  db.saveStoreSettings(live.id, { courier: { default: 'cargus' } });
  live = db.getStore(live.id);
});

test('a parcel coming back re-checks the customer\'s open orders', async () => {
  const dan = { phone: '0788123456' };
  const shipped = order(dan, { outcome: null });
  const open = order(dan);
  assert.ok(!issueCodes(open).includes('CUSTOMER_REFUSED_BEFORE'));
  assert.deepEqual(openOrdersOfCustomer(live, db.getOrder(shipped.id)), [open.id]);
  // The test courier reports the parcel refused.
  db.updateOrder(shipped.id, { awb: 'TESTRET1', test_mode: true, tracking_status: 'in_transit', status: 'in_transit' });
  const mock = (await import('../src/couriers/mock.js')).default;
  const track = mock.track;
  mock.track = async (ctx, awbs) => awbs.map((awb) => ({ awb, status: awb === 'TESTRET1' ? TrackingStatus.RETURNING : TrackingStatus.IN_TRANSIT, statusText: 'Refuzat' }));
  // Test parcels count only in the demo store, so track as if this were the demo.
  try { await P.trackStore({ ...live, demo: true }); } finally { mock.track = track; }
  assert.equal(db.getOrder(shipped.id).status, 'returned');
  assert.ok(issueCodes(db.getOrder(open.id)).includes('CUSTOMER_REFUSED_BEFORE'), 'open order re-checked right away');
});

test('demo store: Florin Matei refused a ramburs parcel before; his new order shows it', () => {
  const past = byName(demo, '#1090');
  assert.equal(past.status, 'returned');
  assert.equal(past.tracking_status, 'returned');
  assert.equal(byName(demo, '#1095').status, 'delivered');
  const cur = byName(demo, '#1111');
  const issue = cur.issues.find((i) => i.code === 'CUSTOMER_REFUSED_BEFORE');
  assert.equal(ro(issue).message, 'Clientul a refuzat 1 colet înainte (din 2).');
  assert.equal(cur.status, 'ready');
  const h = customerHistory(demo, cur);
  assert.deepEqual(h.orders.map((o) => o.name), ['#1095', '#1090']);
  // The example rule exists but is off, so demo statuses stay as they were.
  const rule = demo.settings.rules.find((r) => r.conditions.some((c) => c.field === 'refusedBefore'));
  assert.equal(rule.enabled, false);
});
