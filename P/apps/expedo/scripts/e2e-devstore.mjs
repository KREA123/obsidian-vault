// End-to-end check against a real Shopify DEVELOPMENT store (never a live shop).
//
//   SHOPIFY_API_KEY=... SHOPIFY_API_SECRET=... node scripts/e2e-devstore.mjs dexters-laboratory.myshopify.com
//
// The app must be created in the Shopify Dev Dashboard by the same organization as the store and
// installed on it (client credentials grant). The script:
//   1. creates 3 Romanian test orders (COD, card, company with CUI), tagged "expedo-e2e"
//   2. imports them through Expedo (GraphQL query + mapper) and checks the mapping
//   3. runs the pipeline with the test courier/invoicing, then does the REAL Shopify steps:
//      fulfillment with tracking, tags, mark-as-paid for COD, fulfillment cancel
//   4. prints PASS/FAIL per check. Nothing is sent to customers (notifyCustomer=false, sendReceipt=false).

import { config } from '../src/config.js';
import * as db from '../src/db.js';
import { getShopify } from '../src/shopify/index.js';
import { importOrder, processOrder } from '../src/core/pipeline.js';
import { renderError } from '../src/core/errors.js';

const shop = process.argv[2];
if (!/\.myshopify\.com$/.test(shop || '')) {
  console.error('Usage: node scripts/e2e-devstore.mjs <store>.myshopify.com');
  process.exit(2);
}
config.shopify.ownStores = [shop];

let failed = 0;
const check = (name, ok, extra = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? `  — ${extra}` : ''}`);
  if (!ok) failed++;
};

db.openDb(':memory:');
const store = db.upsertStore({ shop, name: shop });
const shopify = getShopify(store);

const info = await shopify.shopInfo();
check('Conectare la magazin (client credentials)', !!info?.myshopifyDomain, `${info?.name} / ${info?.myshopifyDomain}`);
if (info.myshopifyDomain !== shop) throw new Error(`Connected to ${info.myshopifyDomain}, expected ${shop}`);

const ORDER_CREATE = `
mutation Create($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
  orderCreate(order: $order, options: $options) { order { id name } userErrors { field message } }
}`;

const money = (amount) => ({ shopMoney: { amount: String(amount), currencyCode: 'RON' } });
const line = (title, sku, price, quantity) => ({ title, sku, quantity, priceSet: money(price), requiresShipping: true, taxable: true, taxLines: [{ title: 'TVA', rate: 0.21, priceSet: money(Math.round((price * quantity - (price * quantity) / 1.21) * 100) / 100) }] });
const runId = Date.now().toString(36);

const fixtures = [
  {
    label: 'ramburs, București fără sector în oraș, telefon +40',
    order: {
      email: `e2e-cod-${runId}@example.com`,
      currency: 'RON',
      taxesIncluded: true,
      financialStatus: 'PENDING',
      lineItems: [line('Set construcție Castelul Fermecat', 'E2E-1', 249.9, 1)],
      shippingLines: [{ title: 'Livrare prin curier', priceSet: money(25) }],
      shippingAddress: { firstName: 'Mihai', lastName: 'Ionescu', address1: 'Bd. Unirii nr. 45, bl. E3, ap. 31', city: 'Bucuresti', provinceCode: 'B', countryCode: 'RO', zip: '030167', phone: '+40 722 334 455' },
      transactions: [{ kind: 'SALE', status: 'PENDING', gateway: 'Cash on Delivery (COD)', amountSet: money(274.9) }],
      tags: ['expedo-e2e'],
    },
    expect: { paymentMethod: 'cod', codAmount: 274.9, phone: '0722334455', county: 'București', sector: 3 },
  },
  {
    label: 'card, plătită',
    order: {
      email: `e2e-card-${runId}@example.com`,
      currency: 'RON',
      financialStatus: 'PAID',
      lineItems: [line('Puzzle 1000 piese', 'E2E-2', 69.9, 2)],
      shippingLines: [{ title: 'Livrare prin curier', priceSet: money(25) }],
      shippingAddress: { firstName: 'Andreea', lastName: 'Popescu', address1: 'Str. Observatorului 112', city: 'Cluj-Napoca', provinceCode: 'CJ', countryCode: 'RO', zip: '400394', phone: '0745123456' },
      transactions: [{ kind: 'SALE', status: 'SUCCESS', gateway: 'manual', amountSet: money(164.8) }],
      tags: ['expedo-e2e'],
    },
    expect: { paymentMethod: 'card', codAmount: 0, phone: '0745123456', county: 'Cluj', grossMatchesTotal: true },
  },
  {
    label: 'firmă cu CUI în atribute, ramburs',
    order: {
      email: `e2e-b2b-${runId}@example.com`,
      currency: 'RON',
      taxesIncluded: true,
      financialStatus: 'PENDING',
      lineItems: [line('Joc de societate Aventura', 'E2E-3', 129, 3)],
      shippingLines: [{ title: 'Livrare prin curier', priceSet: money(25) }],
      shippingAddress: { firstName: 'Radu', lastName: 'Georgescu', company: 'Grădinița Zâmbet SRL', address1: 'Calea Aradului 56', city: 'Timișoara', provinceCode: 'TM', countryCode: 'RO', zip: '300223', phone: '0744987654' },
      billingAddress: { firstName: 'Radu', lastName: 'Georgescu', company: 'Grădinița Zâmbet SRL', address1: 'Calea Aradului 56', city: 'Timișoara', provinceCode: 'TM', countryCode: 'RO', zip: '300223', phone: '0744987654' },
      customAttributes: [{ key: 'CUI', value: 'RO31458899' }, { key: 'Nr. Reg. Com.', value: 'J35/1234/2013' }],
      transactions: [{ kind: 'SALE', status: 'PENDING', gateway: 'Cash on Delivery (COD)', amountSet: money(412) }],
      tags: ['expedo-e2e'],
    },
    expect: { paymentMethod: 'cod', codAmount: 412, phone: '0744987654', county: 'Timiș', company: 'RO31458899' },
  },
];

// 1. create orders
const created = [];
for (const f of fixtures) {
  const res = await shopify.gql(ORDER_CREATE, { order: f.order, options: { sendReceipt: false, sendFulfillmentReceipt: false, inventoryBehaviour: 'BYPASS' } });
  const errs = res.orderCreate.userErrors;
  check(`Comandă creată: ${f.label}`, !errs.length && !!res.orderCreate.order, errs.map((e) => e.message).join('; ') || res.orderCreate.order?.name);
  if (res.orderCreate.order) created.push({ ...f, gid: res.orderCreate.order.id, name: res.orderCreate.order.name });
}

// 2. import via Expedo + mapping
store.settings = { ...store.settings, courier: { default: 'cargus' }, invoicing: { provider: 'smartbill' } };
db.saveStoreSettings(store.id, store.settings);
// Shopify's search index lags a few seconds behind orderCreate.
let listed = [];
for (let i = 0; i < 10 && listed.length < created.length; i++) {
  if (i) await new Promise((r) => setTimeout(r, 3000));
  listed = (await shopify.listOrders({ search: 'tag:expedo-e2e', max: 50 })).filter((o) => created.some((c) => c.gid === o.shopifyId));
}
check('Interogarea de comenzi (ORDERS_QUERY) merge', listed.length === created.length, `${listed.length}/${created.length} comenzi noi găsite după etichetă`);

for (const c of created) {
  const o = await shopify.getOrder(c.gid);
  check(`${c.name} citită (ORDER_QUERY)`, !!o);
  if (!o) continue;
  const row = importOrder(db.getStore(store.id), o, { source: 'e2e' });
  const issues = row.issues.filter((i) => i.level === 'error');
  check(`${c.name} adresa trece validarea`, !issues.length, issues.map((i) => renderError(i, 'en').message).join('; '));
  check(`${c.name} metoda de plată = ${c.expect.paymentMethod}`, o.paymentMethod === c.expect.paymentMethod, `${o.paymentMethod} (gateways: ${o.gateways.join(', ')}, status ${o.financialStatus})`);
  check(`${c.name} ramburs = ${c.expect.codAmount}`, Math.abs(o.codAmount - c.expect.codAmount) < 0.01, String(o.codAmount));
  check(`${c.name} telefon normalizat`, row.issues.every((i) => !i.code.startsWith('ADDRESS_PHONE')), o.phone);
  check(`${c.name} produse și transport`, o.lines.length === c.order.lineItems.length && o.shippingLines.length === 1, `${o.lines.length} linii, transport ${o.shippingLines[0]?.price}`);
  check(`${c.name} TVA preluat (21%)`, o.lines.every((l) => l.vatRate === 21), o.lines.map((l) => l.vatRate).join(','));
  check(`${c.name} are fulfillment order deschis`, o.fulfillmentOrders.some((f) => f.status === 'OPEN'), o.fulfillmentOrders.map((f) => f.status).join(','));
  if (c.expect.grossMatchesTotal) {
    const sum = o.lines.reduce((t, l) => t + l.unitPrice * l.quantity, 0) + o.shippingLines.reduce((t, x) => t + x.price, 0);
    check(`${c.name} prețuri fără TVA în magazin → sume cu TVA în Expedo`, Math.abs(sum - o.total) < 0.05, `linii+transport ${sum.toFixed(2)} / total Shopify ${o.total}`);
  }
  if (c.expect.company) check(`${c.name} firmă + CUI detectate`, o.company?.vatCode === c.expect.company, JSON.stringify(o.company));
  c.orderId = row.id;
}

// 3. pipeline in test mode (test courier + invoicing), then the real Shopify steps
const s = db.getStore(store.id);
for (const c of created) {
  if (!c.orderId) continue;
  const r = await processOrder(s, c.orderId);
  check(`${c.name} AWB + factură de test`, r.ok, r.ok ? `${r.awb} / ${r.invoice}` : renderError(r.error, 'en')?.message);
  const order = db.getOrder(c.orderId);
  if (!order.awb) continue;
  try {
    const f = await shopify.fulfill(order.data, { awb: order.awb, company: 'Cargus', url: `https://www.cargus.ro/personal/urmareste-coletul/?tracking_number=${order.awb}`, notifyCustomer: false });
    check(`${c.name} marcată expediată în Shopify cu AWB`, f?.trackingInfo?.[0]?.number === order.awb, `${f?.id} ${f?.status}`);
    c.fulfillmentId = f?.id;
  } catch (err) {
    check(`${c.name} marcată expediată în Shopify cu AWB`, false, err.message);
  }
  try {
    await shopify.addTags(order.shopify_id, ['expedo-awb']);
    check(`${c.name} etichetă adăugată`, true);
  } catch (err) {
    check(`${c.name} etichetă adăugată`, false, err.message);
  }
  if (order.payment_method === 'cod') {
    try {
      const res = await shopify.markAsPaid(order.shopify_id);
      check(`${c.name} marcată plătită (ramburs livrat)`, res?.order?.displayFinancialStatus === 'PAID', res?.order?.displayFinancialStatus);
    } catch (err) {
      check(`${c.name} marcată plătită (ramburs livrat)`, false, err.message);
    }
  }
}

// cancel one fulfillment to exercise "Anulează AWB" on the Shopify side
const withF = created.find((c) => c.fulfillmentId);
if (withF) {
  try {
    const res = await shopify.cancelFulfillment(withF.fulfillmentId);
    check(`${withF.name} expediere anulată în Shopify`, res?.fulfillment?.status === 'CANCELLED', res?.fulfillment?.status);
  } catch (err) {
    check(`${withF.name} expediere anulată în Shopify`, false, err.message);
  }
}

// a second processing must not create anything new (idempotency against Shopify state)
const again = created.find((c) => c.orderId);
if (again) {
  const before = db.getOrder(again.orderId);
  await processOrder(s, again.orderId);
  const after = db.getOrder(again.orderId);
  check('Procesare repetată nu dublează AWB/factura', before.awb === after.awb && before.invoice_number === after.invoice_number);
}

console.log(`\n${failed ? `${failed} verificări au picat` : 'Toate verificările au trecut'}. Comenzile de test au eticheta „expedo-e2e”: ${created.map((c) => c.name).join(', ')}`);
process.exit(failed ? 1 : 0);
