import * as db from '../db.js';
import { withDefaults } from './settings.js';
import { emailHash } from './identity.js';
import { m, t } from '../i18n/index.js';
import { renderEvent } from '../db.js';

// Customer data protection (Shopify "protected customer data", GDPR):
//   - retention: customer data of finished orders is removed N days after delivery / return / cancel
//   - redaction: what "removed" means; the accounting trail (order name, totals, AWB, invoice, statuses) stays
//   - access log: who saw or exported customer data
//   - GDPR webhooks: customers/data_request, customers/redact, shop/redact
// See docs/securitate.md.

/** What the access log records (action → catalog key of the label shown in Activity). */
export const ACCESS_ACTIONS = Object.fromEntries(['order_view', 'invoice_pdf', 'labels', 'picking', 'cod_export', 'customer_export', 'data_request', 'customer_redact']
  .map((k) => [k, `access.actions.${k}`]));

export const ACCESS_LOG_DAYS = 365;

// Order fields kept after redaction: no names, addresses, phones, e-mails, notes or checkout attributes.
// Products and amounts stay for accounting and ramburs reconciliation.
const KEEP = ['shopifyId', 'name', 'createdAt', 'cancelledAt', 'closed', 'test', 'currency', 'taxesIncluded', 'financialStatus', 'fulfillmentStatus',
  'gateways', 'paymentMethod', 'total', 'subtotal', 'shippingTotal', 'discountTotal', 'outstanding', 'codAmount', 'lines', 'shippingLines',
  'shippingMethod', 'weightGrams', 'fulfillmentOrders'];

export function redactedData(data, at) {
  const out = Object.fromEntries(KEEP.filter((k) => Object.hasOwn(data || {}, k)).map((k) => [k, data[k]]));
  return { ...out, lines: out.lines || [], shippingLines: out.shippingLines || [], redactedAt: at };
}

/**
 * Removes the customer data of one order: from the order (data, manual address fixes, issues that
 * quote a phone, provider errors, search hashes), from its history (errors and manual edits deleted,
 * event details dropped) and from the test courier's saved shipment. Returns false if already done.
 */
export function redactOrder(store, orderId, reason) {
  const d = db.getDb();
  const order = db.getOrder(orderId);
  if (!order || order.store_id !== store.id || order.redacted_at) return false;
  const at = new Date().toISOString();
  d.prepare('UPDATE orders SET redacted_at = ? WHERE id = ?').run(at, orderId);
  const { address, notes, ...overrides } = order.overrides || {};
  db.updateOrder(orderId, { data: redactedData(order.data, at), overrides, issues: [], last_error: null }); // also clears the hashes
  d.prepare(`DELETE FROM events WHERE order_id = ? AND (level = 'error' OR step IN ('validate', 'edit'))`).run(orderId);
  d.prepare('UPDATE events SET data = NULL WHERE order_id = ?').run(orderId);
  if (order.awb && order.test_mode) forgetTestShipment(store.id, order.awb);
  db.logEvent(store.id, orderId, 'info', 'privacy', m(reason === 'gdpr' ? 'events.redactedGdpr' : 'events.redactedRetention'));
  return true;
}

function forgetTestShipment(storeId, awb) {
  const cache = db.storeCache(storeId);
  const issued = cache.get('mock:issued');
  if (!issued?.[awb]) return;
  delete issued[awb].shipment;
  cache.set('mock:issued', issued, 60 * 60 * 24 * 30);
}

/**
 * Daily: removes customer data of orders finished more than `retentionDays` ago. Only finished orders
 * (delivered, returned, cancelled, fulfilled outside Expedo) and never one being processed right now.
 */
export function applyRetention(store, now = new Date()) {
  const days = withDefaults(store.settings).privacy.retentionDays;
  const cutoff = new Date(now.getTime() - days * 86400_000).toISOString();
  const d = db.getDb();
  const ids = d.prepare(`SELECT id FROM orders WHERE store_id = ? AND redacted_at IS NULL AND processing_at IS NULL
    AND finished_at IS NOT NULL AND finished_at < ? AND ${db.FINISHED_SQL}`).all(store.id, cutoff).map((r) => r.id);
  let redacted = 0;
  for (const id of ids) if (redactOrder(store, id, 'retention')) redacted++;
  // Store-level events (provider logs) can carry details of a shipment in `data`.
  const events = d.prepare('UPDATE events SET data = NULL WHERE store_id = ? AND order_id IS NULL AND at < ? AND data IS NOT NULL').run(store.id, cutoff).changes;
  if (redacted) db.logEvent(store.id, null, 'info', 'privacy', m('events.retentionApplied', { count: redacted, days }));
  return { redacted, events, cutoff };
}

/** The access log itself is kept one year. */
export function pruneAccessLog(now = new Date()) {
  const cutoff = new Date(now.getTime() - ACCESS_LOG_DAYS * 86400_000).toISOString();
  return db.getDb().prepare('DELETE FROM access_log WHERE at < ?').run(cutoff).changes;
}

// ---------- GDPR webhooks ----------

/**
 * Orders of the customer named in a GDPR webhook: the order ids Shopify lists, plus orders with the
 * same e-mail. Not by phone: people share phones (family, company), and a data request must never
 * hand someone else's order to the requester.
 */
export function gdprOrders(store, payload) {
  const ids = new Set();
  for (const id of [...(payload?.orders_requested || []), ...(payload?.orders_to_redact || [])]) {
    const o = db.getOrderByShopifyId(store.id, `gid://shopify/Order/${id}`);
    if (o) ids.add(o.id);
  }
  const email = emailHash(store.id, payload?.customer?.email);
  if (email) for (const r of db.getDb().prepare('SELECT id FROM orders WHERE store_id = ? AND email_hash = ?').all(store.id, email)) ids.add(r.id);
  return [...ids].map((id) => db.getOrder(id)).sort((a, b) => a.created_at.localeCompare(b.created_at));
}

/** customers/data_request: recorded so the merchant sees it and can send the customer their data. */
export function handleDataRequest(store, payload) {
  const orders = gdprOrders(store, payload);
  // Access-log details are stored as messages too (db.logAccess), translated when the log is shown.
  const ref = payload?.data_request?.id ? m('access.detail.request', { id: payload.data_request.id }) : m('access.detail.requestNoId');
  for (const o of orders) db.logAccess(store.id, { actor: 'shopify', action: 'data_request', orderId: o.id, orderName: o.name, detail: ref });
  if (!orders.length) db.logAccess(store.id, { actor: 'shopify', action: 'data_request', detail: m('access.detail.noOrders', { request: ref }) });
  const names = orders.map((o) => o.name).join(', ');
  db.logEvent(store.id, null, 'warning', 'gdpr', orders.length
    ? m('events.dataRequest', { count: orders.length, orders: names })
    : m('events.dataRequestNone'), {
    hint: m(orders.length ? 'events.dataRequestHint' : 'events.dataRequestNoneHint'),
    orderIds: orders.map((o) => o.id),
  });
  return orders.length;
}

/** customers/redact: the customer's data goes from every order of theirs; the accounting trail stays. */
export function handleCustomerRedact(store, payload) {
  const orders = gdprOrders(store, payload);
  let n = 0;
  for (const o of orders) {
    if (redactOrder(store, o.id, 'gdpr')) n++;
    db.logAccess(store.id, { actor: 'shopify', action: 'customer_redact', orderId: o.id, orderName: o.name, detail: m('access.detail.redacted') });
  }
  db.logEvent(store.id, null, 'info', 'gdpr', n
    ? m('events.redactRequest', { count: n, orders: orders.map((o) => o.name).join(', ') })
    : m('events.redactRequestNone'));
  return n;
}

/** shop/redact (48 h after uninstall): everything about the store goes. */
export function handleShopRedact(store) {
  const d = db.getDb();
  // events / jobs / cache / access_log have no foreign key to stores; orders and integrations cascade.
  for (const t of ['events', 'jobs', 'cache', 'access_log']) d.prepare(`DELETE FROM ${t} WHERE store_id = ?`).run(store.id);
  d.prepare('DELETE FROM stores WHERE id = ?').run(store.id);
}

/** Everything Expedo holds about the given orders, to send to a customer who asked for their data. */
export function customerExport(store, orderIds, locale = 'en') {
  const orders = orderIds.map((id) => db.getOrder(id)).filter((o) => o && o.store_id === store.id);
  return {
    generatedAt: new Date().toISOString(),
    shop: store.shop,
    note: t(locale, 'export.note'),
    orders: orders.map((o) => ({
      order: o.name,
      createdAt: o.created_at,
      status: o.status,
      customer: {
        name: o.data.customerName, email: o.data.email, phone: o.data.phone,
        shippingAddress: o.data.shippingAddress, billingAddress: o.data.billingAddress, company: o.data.company,
      },
      manualAddressFix: o.overrides.address || null,
      products: (o.data.lines || []).map((l) => ({ title: l.title, sku: l.sku, quantity: l.quantity, unitPrice: l.unitPrice })),
      total: o.total,
      cashOnDelivery: o.cod_amount,
      courier: o.courier, awb: o.awb, trackingStatus: o.tracking_text,
      invoice: o.invoice_number ? `${o.invoice_series} ${o.invoice_number}` : null,
      redactedAt: o.redacted_at || null,
      history: db.orderEvents(o.id).map((e) => ({ at: e.at, message: renderEvent(e, locale).message })),
    })),
  };
}
