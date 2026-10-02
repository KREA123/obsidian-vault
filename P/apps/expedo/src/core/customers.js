import * as db from '../db.js';

// Customer refusal history: how many of the customer's earlier parcels came back (refused at the
// door, returned) and how many were delivered. A refused cash-on-delivery parcel costs the merchant
// shipping both ways, so a customer who did it before is worth a phone call before the AWB.
// "The customer" = same phone OR same e-mail in this store, matched by keyed hash (core/identity.js).
// Redacted orders (retention, GDPR) have no hashes any more, so the history covers the retention period.

const RETURNED = new Set(['returning', 'returned']);
const isReturned = (o) => !!o.awb && (o.status === 'returned' || RETURNED.has(o.tracking_status));

/**
 * The other orders of this order's customer, newest first, and the counts:
 *   returned   — parcels refused / returned (any payment)
 *   refusedCod — of those, the cash-on-delivery ones (the money risk)
 *   delivered  — parcels delivered
 * Test AWBs (modul de probă) never travelled, so they count only in the demo store.
 */
export function customerHistory(store, order, { limit = 20 } = {}) {
  const m = sameCustomer(order);
  if (!m) return { returned: 0, refusedCod: 0, delivered: 0, total: 0, orders: [] };
  const rows = db.getDb().prepare(`SELECT id, name, created_at, status, tracking_status, awb, cod_amount, payment_method, test_mode FROM orders
    WHERE store_id = ? AND id != ? AND ${m.sql} ORDER BY created_at DESC`).all(store.id, order.id, ...m.args);
  const counted = rows.filter((o) => o.awb && (store.demo || !o.test_mode));
  const returned = counted.filter(isReturned);
  const delivered = counted.filter((o) => !isReturned(o) && o.status === 'delivered').length;
  return {
    returned: returned.length,
    refusedCod: returned.filter((o) => o.cod_amount > 0).length,
    delivered,
    total: returned.length + delivered,
    orders: rows.slice(0, limit).map((o) => ({ id: o.id, name: o.name, createdAt: o.created_at, status: o.status, refused: isReturned(o), cod: o.cod_amount > 0 })),
  };
}

/** Open orders (no AWB yet) of the same customer: re-checked when one of their parcels comes back. */
export function openOrdersOfCustomer(store, order) {
  const m = sameCustomer(order);
  if (!m) return [];
  return db.getDb().prepare(`SELECT id FROM orders WHERE store_id = ? AND id != ? AND awb IS NULL
    AND status IN ('new', 'ready', 'needs_attention', 'on_hold') AND ${m.sql}`).all(store.id, order.id, ...m.args).map((r) => r.id);
}

/** SQL for "same phone or same e-mail" as this order; null when it has neither. */
function sameCustomer(order) {
  const { phone, email } = order.customerKeys || {};
  const parts = [phone && 'phone_hash = ?', email && 'email_hash = ?'].filter(Boolean);
  return parts.length ? { sql: `(${parts.join(' OR ')})`, args: [phone, email].filter(Boolean) } : null;
}
