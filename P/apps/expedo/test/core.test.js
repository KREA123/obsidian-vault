import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { validateAddress, normalizePhone, findCounty, findSector } from '../src/core/address.js';
import { evaluateRules, ruleFacts } from '../src/core/rules.js';
import { mapOrder, detectCompany, detectPaymentMethod } from '../src/shopify/mapper.js';
import { planOrder, buildShipment, buildInvoice } from '../src/core/build.js';
import { withDefaults } from '../src/core/settings.js';

test('phone normalization', () => {
  assert.deepEqual(normalizePhone('+40 722 334 455'), { phone: '0722334455', valid: true });
  assert.equal(normalizePhone('0040733111222').phone, '0733111222');
  assert.equal(normalizePhone('40744987654').phone, '0744987654');
  assert.equal(normalizePhone('744987654').phone, '0744987654');
  assert.equal(normalizePhone('0744 987 654').valid, true);
  assert.equal(normalizePhone('12345').valid, false);
  assert.equal(normalizePhone('+49 151 23456789').foreign, true);
});

test('county lookup tolerates diacritics, codes, prefixes and typos', () => {
  assert.equal(findCounty('Constanta').code, 'CT');
  assert.equal(findCounty('CJ').name, 'Cluj');
  assert.equal(findCounty('Jud. Iasi').code, 'IS');
  assert.equal(findCounty('Bucuresti Sector 3').code, 'B');
  assert.equal(findCounty('Sector 6').code, 'B');
  assert.equal(findCounty('Bistrita Nasaud').code, 'BN');
  assert.equal(findCounty('Timis').code, 'TM');
  assert.equal(findCounty('Brasv').code, 'BV');
  assert.equal(findCounty('Atlantis'), null);
});

test('Bucharest sector from city, address or postal code', () => {
  assert.equal(findSector('Bucuresti Sector 6'), 6);
  assert.equal(findSector('', 'Str. X 3, sect. 2'), 2);
  const { address } = validateAddress({ firstName: 'A', lastName: 'B', city: 'București', province: 'București', zip: '030167', address1: 'Bd. Unirii 45', phone: '0722000000' });
  assert.equal(address.sector, 3);
  assert.equal(address.city, 'București');
});

test('address validation reports blocking errors in Romanian', () => {
  const { issues } = validateAddress({ firstName: 'Ion', city: 'Iași', province: 'Iași', address1: 'Str. Lungă 1', phone: '' });
  assert.equal(issues.find((i) => i.level === 'error').code, 'ADDRESS_PHONE_MISSING');
  const zipNeeded = validateAddress({ firstName: 'Ion', city: 'Iași', province: 'Iași', address1: 'Str. Lungă 1', phone: '0744111222' }, { requireZip: true });
  assert.ok(zipNeeded.issues.some((i) => i.code === 'ADDRESS_ZIP_MISSING'));
  const noCounty = validateAddress({ firstName: 'Ion', city: 'Bragadiru', address1: 'Str. X 1', phone: '0744111222' });
  assert.ok(noCounty.issues.some((i) => i.code === 'ADDRESS_COUNTY_MISSING'));
  const ok = validateAddress({ firstName: 'Ion', city: 'Mun. Cluj-Napoca', province: 'Cluj', address1: 'Str. Observatorului 1', phone: '0744111222', zip: '400 394' });
  assert.equal(ok.issues.filter((i) => i.level === 'error').length, 0);
  assert.equal(ok.address.city, 'Cluj-Napoca');
  assert.equal(ok.address.zip, '400394');
});

test('payment method and company detection', () => {
  assert.equal(detectPaymentMethod(['Cash on Delivery (COD)'], 'PENDING'), 'cod');
  assert.equal(detectPaymentMethod(['Plata ramburs'], 'PENDING'), 'cod');
  assert.equal(detectPaymentMethod(['shopify_payments'], 'PAID'), 'card');
  assert.equal(detectPaymentMethod(['Bank Deposit'], 'PENDING'), 'transfer');
  assert.deepEqual(detectCompany({ company: 'Firma Mea SRL' }, [{ key: 'CUI', value: 'ro 123456' }]), { name: 'Firma Mea SRL', vatCode: 'RO123456', regCom: '' });
  assert.deepEqual(detectCompany({ company: 'Firma Mea SRL, RO123456' }, []), { name: 'Firma Mea SRL', vatCode: 'RO123456', regCom: '' });
  assert.equal(detectCompany({ company: 'Acasă' }, []), null);
});

const money = (amount) => ({ shopMoney: { amount: String(amount), currencyCode: 'RON' } });
const gqlOrder = {
  id: 'gid://shopify/Order/1', name: '#1001', createdAt: '2026-10-01T10:00:00Z', cancelledAt: null, closed: false, test: false,
  currencyCode: 'RON', taxesIncluded: true, displayFinancialStatus: 'PENDING', displayFulfillmentStatus: 'UNFULFILLED',
  paymentGatewayNames: ['Cash on Delivery (COD)'], email: 'ion@example.com', phone: null, note: '', tags: ['vip'], totalWeight: '1300',
  customAttributes: [],
  totalPriceSet: money(205), subtotalPriceSet: money(180), totalShippingPriceSet: money(25), totalDiscountsSet: money(20), totalOutstandingSet: money(205),
  shippingAddress: { firstName: 'Ion', lastName: 'Pop', name: 'Ion Pop', company: '', address1: 'Str. Lungă 1', address2: '', city: 'Brașov', province: 'Brașov', provinceCode: 'BV', zip: '500096', countryCodeV2: 'RO', phone: '+40744111222' },
  billingAddress: null,
  shippingLines: { nodes: [{ title: 'Cargus', code: 'cargus', source: 'shopify', originalPriceSet: money(25), discountedPriceSet: money(25), taxLines: [{ rate: 0.21 }] }] },
  lineItems: { nodes: [
    { id: 'L1', name: 'A', title: 'Set A', variantTitle: 'Default Title', sku: 'A1', quantity: 2, currentQuantity: 2, requiresShipping: true, isGiftCard: false, originalUnitPriceSet: money(100), discountAllocations: [{ allocatedAmountSet: money(20) }], taxLines: [{ rate: 0.21 }] },
    { id: 'L2', name: 'B', title: 'Removed', variantTitle: null, sku: 'B1', quantity: 1, currentQuantity: 0, requiresShipping: true, isGiftCard: false, originalUnitPriceSet: money(50), discountAllocations: [], taxLines: [] },
  ] },
  fulfillmentOrders: { nodes: [{ id: 'FO1', status: 'OPEN', assignedLocation: { name: 'Depozit' } }] },
};

test('Shopify order mapping: discounts, removed items, COD', () => {
  const o = mapOrder(gqlOrder);
  assert.equal(o.lines.length, 1);
  assert.equal(o.lines[0].unitPrice, 90); // (2*100 - 20) / 2
  assert.equal(o.lines[0].vatRate, 21);
  assert.equal(o.lines[0].variantTitle, '');
  assert.equal(o.paymentMethod, 'cod');
  assert.equal(o.codAmount, 205);
  assert.equal(o.phone, '+40744111222');
  assert.equal(o.weightGrams, 1300);
});

test('rules: first match wins per action, multi-value contains', () => {
  const o = mapOrder({ ...gqlOrder, shippingLines: { nodes: [{ ...gqlOrder.shippingLines.nodes[0], title: 'Livrare la Easybox' }] } });
  const rules = [
    { name: 'locker', conditions: [{ field: 'shippingMethod', op: 'contains', value: 'easybox, locker' }], actions: { courier: 'sameday' } },
    { name: 'default', conditions: [], actions: { courier: 'cargus', parcels: 2 } },
    { name: 'off', enabled: false, conditions: [], actions: { notes: 'x' } },
  ];
  const r = evaluateRules(rules, ruleFacts(o));
  assert.deepEqual(r.actions, { courier: 'sameday', parcels: 2 });
  assert.deepEqual(r.matched, ['locker', 'default']);
  assert.equal(evaluateRules([{ conditions: [{ field: 'total', op: 'gt', value: '500' }], actions: { hold: true } }], ruleFacts(o)).matched.length, 0);
});

test('plan, shipment and invoice from an order', () => {
  const o = mapOrder(gqlOrder);
  const settings = withDefaults({ courier: { default: 'gls' } });
  const plan = planOrder(o, settings, { parcels: 3 });
  assert.equal(plan.courier, 'gls');
  assert.equal(plan.blocking, false);
  assert.equal(plan.parcels, 3);
  assert.equal(plan.weightKg, 1.3);
  const s = buildShipment(o, plan, settings);
  assert.equal(s.recipient.phone, '0744111222');
  assert.equal(s.recipient.countyCode, 'BV');
  assert.equal(s.cod, 205);
  assert.equal(s.reference, '#1001');
  const inv = buildInvoice(o, plan, settings);
  assert.equal(inv.lines.length, 2);
  assert.deepEqual(inv.lines[1], { name: 'Transport (Cargus)', quantity: 1, unitPrice: 25, vatRate: 21, unit: 'buc', isShipping: true });
  assert.equal(inv.total, 205);
  assert.equal(inv.mismatch, 0);
  assert.equal(inv.client.isCompany, false);
  assert.equal(inv.paid, false);
});

test('missing courier and cancelled orders block processing', () => {
  const o = mapOrder({ ...gqlOrder, cancelledAt: '2026-10-01T11:00:00Z' });
  const plan = planOrder(o, withDefaults({}), {});
  assert.ok(plan.blocking);
  assert.ok(plan.issues.some((i) => i.code === 'NO_COURIER'));
  assert.ok(plan.issues.some((i) => i.code === 'ORDER_CANCELLED'));
});

test('Shopify signatures: webhook HMAC, OAuth query HMAC, session token', async () => {
  process.env.SHOPIFY_API_SECRET = 'shh';
  process.env.SHOPIFY_API_KEY = 'key123';
  const { config } = await import('../src/config.js');
  config.shopify.apiSecret = 'shh';
  config.shopify.apiKey = 'key123';
  const auth = await import('../src/shopify/auth.js');

  const body = Buffer.from('{"id":1}');
  const good = createHmac('sha256', 'shh').update(body).digest('base64');
  assert.equal(auth.verifyWebhookHmac(body, good), true);
  assert.equal(auth.verifyWebhookHmac(body, 'nope'), false);

  const q = { shop: 'x.myshopify.com', code: 'abc', state: '1', timestamp: '2' };
  const msg = 'code=abc&shop=x.myshopify.com&state=1&timestamp=2';
  assert.equal(auth.verifyQueryHmac({ ...q, hmac: createHmac('sha256', 'shh').update(msg).digest('hex') }), true);
  assert.equal(auth.verifyQueryHmac({ ...q, hmac: 'bad' }), false);

  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const h = b64({ alg: 'HS256', typ: 'JWT' });
  const p = b64({ dest: 'https://x.myshopify.com', aud: 'key123', exp: now + 60, nbf: now - 1 });
  const sig = createHmac('sha256', 'shh').update(`${h}.${p}`).digest('base64url');
  assert.equal(auth.verifySessionToken(`${h}.${p}.${sig}`).shop, 'x.myshopify.com');
  assert.equal(auth.verifySessionToken(`${h}.${p}.x${sig.slice(1)}`), null);
  const expired = b64({ dest: 'https://x.myshopify.com', aud: 'key123', exp: now - 600 });
  assert.equal(auth.verifySessionToken(`${h}.${expired}.${createHmac('sha256', 'shh').update(`${h}.${expired}`).digest('base64url')}`), null);
});

test('COD: an order with nothing left to pay is not collected again', () => {
  // Marked as paid / refunded in Shopify: totalOutstanding is 0, the mapper falls back to the total.
  const o = mapOrder({ ...gqlOrder, displayFinancialStatus: 'PAID', totalOutstandingSet: money(0) });
  const plan = planOrder(o, withDefaults({ courier: { default: 'cargus' } }), {});
  assert.equal(plan.cod, 0);
  assert.ok(plan.issues.some((i) => i.code === 'COD_ZERO'));
  // Partially paid: only the rest.
  const part = mapOrder({ ...gqlOrder, totalOutstandingSet: money(55.5) });
  assert.equal(planOrder(part, withDefaults({ courier: { default: 'cargus' } }), {}).cod, 55.5);
  // A manual amount always wins.
  assert.equal(planOrder(o, withDefaults({ courier: { default: 'cargus' } }), { cod: 12 }).cod, 12);
});

test('invoice mismatch ignores shipping when shipping is not invoiced', () => {
  const o = mapOrder(gqlOrder);
  const noShip = withDefaults({ courier: { default: 'gls' }, invoicing: { includeShipping: false } });
  const inv = buildInvoice(o, planOrder(o, noShip, {}), noShip);
  assert.equal(inv.total, 180);
  assert.equal(inv.mismatch, 0);
  // A real difference (e.g. gift card) is still reported.
  const gift = mapOrder({ ...gqlOrder, totalPriceSet: money(185) });
  assert.equal(buildInvoice(gift, planOrder(gift, noShip, {}), noShip).mismatch, -20);
});

test('bucharestDayStart is local midnight in UTC, DST-aware', async () => {
  const { bucharestDayStart } = await import('../src/core/build.js');
  assert.equal(bucharestDayStart(new Date('2026-10-01T22:30:00Z')), '2026-10-01T21:00:00.000Z');
  assert.equal(bucharestDayStart(new Date('2026-01-15T12:00:00Z')), '2026-01-14T22:00:00.000Z');
  assert.equal(bucharestDayStart(new Date('2026-03-29T12:00:00Z')), '2026-03-28T22:00:00.000Z');
});
