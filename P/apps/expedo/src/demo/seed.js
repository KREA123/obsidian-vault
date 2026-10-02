import * as db from '../db.js';
import { importOrder } from '../core/pipeline.js';
import { saveStoreSettings, getStoreByShop, upsertStore } from '../db.js';

// Demo store with realistic Romanian orders, including the messy ones that break
// other connectors (no sector, +40 phones, wrong county, company with CUI, easybox).

const PRODUCTS = [
  { title: 'Set construcție Castelul Fermecat', sku: 'MS-10234', price: 249.9 },
  { title: 'Mașinuță de curse cu telecomandă', sku: 'MS-20411', price: 159 },
  { title: 'Puzzle 1000 piese - Peisaj de iarnă', sku: 'MS-30020', price: 69.9 },
  { title: 'Set construcție Stația spațială', sku: 'MS-10901', price: 389 },
  { title: 'Figurine dinozauri (12 buc.)', sku: 'MS-40112', price: 89.5 },
  { title: 'Joc de societate Aventura', sku: 'MS-50007', price: 129 },
];

const PEOPLE = [
  { firstName: 'Andreea', lastName: 'Popescu', city: 'Cluj-Napoca', province: 'Cluj', provinceCode: 'CJ', zip: '400394', address1: 'Str. Observatorului nr. 112, ap. 14', phone: '0745123456' },
  { firstName: 'Mihai', lastName: 'Ionescu', city: 'București', province: 'București', provinceCode: 'B', zip: '030167', address1: 'Bd. Unirii nr. 45, bl. E3, sc. 2, ap. 31', phone: '+40 722 334 455' },
  { firstName: 'Elena', lastName: 'Dumitrescu', city: 'Iași', province: 'Iași', provinceCode: 'IS', zip: '700259', address1: 'Șoseaua Păcurari nr. 8', phone: '0040733111222' },
  { firstName: 'Ion', lastName: 'Marin', city: 'Voluntari', province: 'Ilfov', provinceCode: 'IF', zip: '077190', address1: 'Str. Erou Iancu Nicolae 32A', phone: '0766555444' },
  { firstName: 'Cristina', lastName: 'Stan', city: 'Bucuresti Sector 6', province: 'Bucuresti', provinceCode: 'B', zip: '', address1: 'Str. Valea Cascadelor 21', phone: '0751222333' },
  { firstName: 'Radu', lastName: 'Georgescu', city: 'Timișoara', province: 'Timiș', provinceCode: 'TM', zip: '300223', address1: 'Calea Aradului nr. 56', phone: '0744 987 654' },
  { firstName: 'Ioana', lastName: 'Constantin', city: 'Brașov', province: 'Brașov', provinceCode: 'BV', zip: '500096', address1: 'Str. Lungă 101', phone: '0727000111' },
  { firstName: 'Florin', lastName: 'Matei', city: 'Constanța', province: 'Constanta', provinceCode: '', zip: '900178', address1: 'Bd. Mamaia 250', phone: '0763444555' },
  { firstName: 'Gabriela', lastName: 'Niculescu', city: 'Sibiu', province: 'Sibiu', provinceCode: 'SB', zip: '550024', address1: 'Str. Nicolae Bălcescu 7', phone: '0721888999' },
  { firstName: 'Bogdan', lastName: 'Lazăr', city: 'Oradea', province: 'Bihor', provinceCode: 'BH', zip: '410087', address1: 'Piața Unirii 3', phone: '0742111000' },
];

const daysAgo = (d, h = 0) => new Date(Date.now() - d * 86400_000 - h * 3600_000).toISOString();

function makeOrder(n, { person, items, payment = 'cod', createdAt, attributes = [], company = null, tags = [], shipping = 'Livrare prin curier', shippingPrice = 25, cancelled = false, noPhone = false, badCounty = false }) {
  const lines = items.map(([pi, qty], i) => {
    const p = PRODUCTS[pi];
    return { id: `gid://shopify/LineItem/${n}${i}`, title: p.title, variantTitle: '', sku: p.sku, quantity: qty, originalUnitPrice: p.price, unitPrice: p.price, vatRate: 21, requiresShipping: true, isGiftCard: false };
  });
  const subtotal = lines.reduce((s, l) => s + l.unitPrice * l.quantity, 0);
  const total = Math.round((subtotal + shippingPrice) * 100) / 100;
  const addr = {
    ...person,
    name: `${person.firstName} ${person.lastName}`,
    company: company?.name || '',
    address2: '',
    countryCode: 'RO',
    phone: noPhone ? '' : person.phone,
    ...(badCounty ? { city: 'Bragadiru', province: '', provinceCode: '', zip: '' } : {}),
  };
  const paid = payment === 'card';
  return {
    shopifyId: `gid://shopify/Order/${5000000000 + n}`,
    name: `#${n}`,
    createdAt,
    cancelledAt: cancelled ? createdAt : null,
    closed: false,
    test: false,
    currency: 'RON',
    taxesIncluded: true,
    financialStatus: paid ? 'PAID' : 'PENDING',
    fulfillmentStatus: 'UNFULFILLED',
    gateways: paid ? ['shopify_payments'] : ['Cash on Delivery (COD)'],
    paymentMethod: payment,
    total,
    subtotal,
    shippingTotal: shippingPrice,
    discountTotal: 0,
    outstanding: paid ? 0 : total,
    codAmount: paid ? 0 : total,
    email: `${person.firstName.toLowerCase()}.${person.lastName.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')}@example.com`,
    phone: addr.phone,
    customerName: addr.name,
    shippingAddress: addr,
    billingAddress: addr,
    company,
    lines,
    shippingLines: [{ title: shipping, code: shipping, source: 'shopify', price: shippingPrice, vatRate: 21 }],
    shippingMethod: shipping,
    tags,
    note: '',
    attributes,
    weightGrams: lines.reduce((s, l) => s + l.quantity * 650, 0),
    fulfillmentOrders: [{ id: `gid://shopify/FulfillmentOrder/${n}`, status: 'OPEN', location: 'Depozit' }],
  };
}

export function seedDemo() {
  let store = getStoreByShop('demo.myshopify.com');
  if (store && db.getDb().prepare('SELECT COUNT(*) c FROM orders WHERE store_id = ?').get(store.id).c > 0) return { store, created: false };
  store = upsertStore({ shop: 'demo.myshopify.com', name: 'Magazin demo (jucării)', demo: true });
  saveStoreSettings(store.id, {
    mode: 'test',
    courier: { default: 'cargus', labelFormat: 'A6' },
    invoicing: { provider: 'smartbill', when: 'on_awb', includeShipping: true, defaultVatRate: 21 },
    automation: { autoProcess: false, delayMinutes: 15, skipTags: ['manual', 'nu-procesa'] },
    rules: [
      { id: 'r1', name: 'Easybox → Sameday', enabled: true, conditions: [{ field: 'shippingMethod', op: 'contains', value: 'easybox, locker' }], actions: { courier: 'sameday' } },
      { id: 'r2', name: 'Colete mari → 2 colete', enabled: true, conditions: [{ field: 'weightKg', op: 'gt', value: '5' }], actions: { parcels: 2 } },
      { id: 'r3', name: 'Comenzi mari plătite ramburs → verificare', enabled: true, conditions: [{ field: 'paymentMethod', op: 'equals', value: 'cod' }, { field: 'total', op: 'gt', value: '1500' }], actions: { hold: true } },
    ],
  });
  store = db.getStore(store.id);

  const P = PEOPLE;
  const orders = [
    makeOrder(1101, { person: P[0], items: [[0, 1]], createdAt: daysAgo(6, 3) }),
    makeOrder(1102, { person: P[1], items: [[1, 1], [2, 1]], payment: 'card', createdAt: daysAgo(6, 1) }),
    makeOrder(1103, { person: P[2], items: [[3, 1]], createdAt: daysAgo(5, 7) }),
    makeOrder(1104, { person: P[3], items: [[4, 2]], createdAt: daysAgo(5, 2) }),
    makeOrder(1105, { person: P[5], items: [[5, 1], [2, 2]], payment: 'card', createdAt: daysAgo(4, 9) }),
    makeOrder(1106, { person: P[6], items: [[0, 1], [4, 1]], createdAt: daysAgo(4, 4) }),
    makeOrder(1107, { person: P[8], items: [[1, 1]], createdAt: daysAgo(3, 6) }),
    makeOrder(1108, { person: P[9], items: [[3, 1], [0, 1]], payment: 'card', createdAt: daysAgo(3, 2) }),
    makeOrder(1109, { person: P[0], items: [[5, 1]], createdAt: daysAgo(2, 8), shipping: 'Livrare la easybox', shippingPrice: 15, attributes: [{ key: 'Easybox ID', value: '4127' }] }),
    makeOrder(1110, { person: P[4], items: [[2, 1]], createdAt: daysAgo(2, 5) }),
    makeOrder(1111, { person: P[7], items: [[1, 2]], createdAt: daysAgo(1, 10) }),
    makeOrder(1112, { person: P[5], items: [[3, 2], [0, 1]], createdAt: daysAgo(1, 7), company: { name: 'Grădinița Zâmbet SRL', vatCode: 'RO31458899', regCom: 'J35/1234/2013' }, payment: 'card' }),
    makeOrder(1113, { person: P[2], items: [[4, 1]], createdAt: daysAgo(1, 3), noPhone: true }),
    makeOrder(1114, { person: P[6], items: [[0, 4], [3, 2]], createdAt: daysAgo(0, 9) }),
    makeOrder(1115, { person: P[1], items: [[2, 1]], createdAt: daysAgo(0, 6), badCounty: true }),
    makeOrder(1116, { person: P[3], items: [[1, 1], [5, 1]], payment: 'card', createdAt: daysAgo(0, 4) }),
    makeOrder(1117, { person: P[9], items: [[4, 1]], createdAt: daysAgo(0, 2), tags: ['manual'] }),
    makeOrder(1118, { person: P[8], items: [[5, 2]], createdAt: daysAgo(0, 1) }),
    makeOrder(1119, { person: P[0], items: [[2, 1]], createdAt: daysAgo(0, 0.5), cancelled: true }),
  ];
  for (const o of orders) importOrder(store, o, { source: 'demo' });
  return { store, created: true };
}

/** Processes the oldest demo orders so the dashboard shows every stage on first open. */
export async function advanceDemo(store, processOrder) {
  const rows = db.getDb().prepare(`SELECT id, name FROM orders WHERE store_id = ? AND awb IS NULL AND status = 'ready' ORDER BY created_at LIMIT 8`).all(store.id);
  for (const r of rows) await processOrder(store, r.id);
  // Age the first AWBs so the test courier reports them further along.
  const cache = db.storeCache(store.id);
  const issued = cache.get('mock:issued') || {};
  const awbs = db.getDb().prepare(`SELECT awb FROM orders WHERE store_id = ? AND awb IS NOT NULL ORDER BY created_at`).all(store.id).map((r) => r.awb);
  awbs.forEach((awb, i) => { if (issued[awb]) issued[awb].at -= Math.max(0, 6 - i) * 2 * 60_000; });
  cache.set('mock:issued', issued, 60 * 60 * 24 * 30);
}
