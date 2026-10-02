import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { config } from './config.js';
import { encrypt, decrypt } from './lib/crypto.js';

let db;

export function openDb(file = config.dbFile) {
  if (file !== ':memory:') mkdirSync(dirname(file), { recursive: true });
  db = new DatabaseSync(file);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS stores (
      id INTEGER PRIMARY KEY,
      shop TEXT NOT NULL UNIQUE,              -- mystore.myshopify.com
      name TEXT,
      access_token TEXT,                      -- encrypted
      scopes TEXT,
      settings TEXT NOT NULL DEFAULT '{}',
      demo INTEGER NOT NULL DEFAULT 0,
      installed_at TEXT NOT NULL DEFAULT (datetime('now')),
      uninstalled_at TEXT
    );

    -- One row per configured courier / invoicing provider per store.
    CREATE TABLE IF NOT EXISTS integrations (
      store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
      kind TEXT NOT NULL CHECK (kind IN ('courier', 'invoicing')),
      provider TEXT NOT NULL,
      credentials TEXT,                       -- encrypted JSON
      settings TEXT NOT NULL DEFAULT '{}',
      enabled INTEGER NOT NULL DEFAULT 1,
      verified_at TEXT,
      PRIMARY KEY (store_id, kind, provider)
    );

    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY,
      store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
      shopify_id TEXT NOT NULL,
      name TEXT NOT NULL,
      data TEXT NOT NULL,                     -- normalized order (src/shopify/mapper.js)
      status TEXT NOT NULL DEFAULT 'new',     -- see ORDER_STATUS in core/pipeline.js
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL DEFAULT (datetime('now')),
      payment_method TEXT,
      total REAL,
      cod_amount REAL NOT NULL DEFAULT 0,
      courier TEXT,
      service TEXT,
      awb TEXT,
      awb_at TEXT,
      shipping_cost REAL,
      tracking_status TEXT,
      tracking_text TEXT,
      tracking_at TEXT,
      invoice_provider TEXT,
      invoice_series TEXT,
      invoice_number TEXT,
      invoice_url TEXT,
      invoice_at TEXT,
      fulfillment_id TEXT,
      fulfilled_at TEXT,
      cod_collected_at TEXT,
      paid_marked_at TEXT,
      issues TEXT NOT NULL DEFAULT '[]',      -- validation issues
      last_error TEXT,                        -- ProcessingError JSON
      overrides TEXT NOT NULL DEFAULT '{}',   -- manual edits (address fixes, parcels, courier...)
      test_mode INTEGER NOT NULL DEFAULT 0,   -- AWB/invoice were made by the test providers
      UNIQUE (store_id, shopify_id)
    );
    CREATE INDEX IF NOT EXISTS orders_store_status ON orders(store_id, status, created_at DESC);
    CREATE INDEX IF NOT EXISTS orders_awb ON orders(awb);

    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY,
      store_id INTEGER NOT NULL,
      order_id INTEGER,
      at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
      level TEXT NOT NULL DEFAULT 'info',     -- info | success | warning | error
      step TEXT,                              -- validate | awb | invoice | fulfill | tracking | ...
      message TEXT NOT NULL,
      data TEXT
    );
    CREATE INDEX IF NOT EXISTS events_order ON events(order_id, id);
    CREATE INDEX IF NOT EXISTS events_store ON events(store_id, id DESC);

    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY,
      store_id INTEGER NOT NULL,
      type TEXT NOT NULL,
      key TEXT,                               -- dedupe key: one pending job per key
      payload TEXT NOT NULL DEFAULT '{}',
      run_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
      attempts INTEGER NOT NULL DEFAULT 0,
      max_attempts INTEGER NOT NULL DEFAULT 6,
      status TEXT NOT NULL DEFAULT 'pending', -- pending | running | done | failed
      last_error TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS jobs_due ON jobs(status, run_at);

    CREATE TABLE IF NOT EXISTS cache (
      store_id INTEGER NOT NULL,
      key TEXT NOT NULL,
      value TEXT NOT NULL,
      expires_at INTEGER NOT NULL,
      PRIMARY KEY (store_id, key)
    );

    CREATE TABLE IF NOT EXISTS webhooks_seen (
      id TEXT PRIMARY KEY,
      at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
  migrate();
  return db;
}

/** Additive migrations for databases created by older versions. */
function migrate() {
  const cols = new Set(db.prepare('PRAGMA table_info(orders)').all().map((c) => c.name));
  // test_mode is about the AWB; the invoice has its own flag (an order can have a test invoice and a real AWB).
  if (!cols.has('invoice_test')) {
    db.exec('ALTER TABLE orders ADD COLUMN invoice_test INTEGER NOT NULL DEFAULT 0');
    db.exec('UPDATE orders SET invoice_test = test_mode WHERE invoice_number IS NOT NULL');
  }
  // Cross-process claim on an order while it is being processed (see claimOrder).
  if (!cols.has('processing_at')) db.exec('ALTER TABLE orders ADD COLUMN processing_at TEXT');
  // One *pending* job per key. A running job must not block a new one: a webhook that arrives while
  // the same order is being synced has to trigger another sync, or the update is lost.
  db.exec(`DROP INDEX IF EXISTS jobs_key;
    CREATE UNIQUE INDEX IF NOT EXISTS jobs_key_pending ON jobs(key) WHERE status = 'pending' AND key IS NOT NULL;`);
}

export const getDb = () => db;

// ---------- helpers ----------
const j = (s, fallback) => { try { return s ? JSON.parse(s) : fallback; } catch { return fallback; } };

export function getStore(id) {
  const row = db.prepare('SELECT * FROM stores WHERE id = ?').get(id);
  return row && hydrateStore(row);
}
export function getStoreByShop(shop) {
  const row = db.prepare('SELECT * FROM stores WHERE shop = ?').get(shop);
  return row && hydrateStore(row);
}
export function listStores() {
  return db.prepare('SELECT * FROM stores WHERE uninstalled_at IS NULL ORDER BY id').all().map(hydrateStore);
}
function hydrateStore(row) {
  return { ...row, demo: !!row.demo, settings: j(row.settings, {}), accessToken: row.access_token ? decrypt(row.access_token) : null };
}
export function upsertStore({ shop, name, accessToken, scopes, demo = false }) {
  db.prepare(`INSERT INTO stores (shop, name, access_token, scopes, demo) VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(shop) DO UPDATE SET name = COALESCE(excluded.name, name), access_token = excluded.access_token,
      scopes = excluded.scopes, uninstalled_at = NULL`)
    .run(shop, name ?? null, accessToken ? encrypt(accessToken) : null, scopes ?? null, demo ? 1 : 0);
  return getStoreByShop(shop);
}
export function saveStoreSettings(storeId, settings) {
  db.prepare('UPDATE stores SET settings = ? WHERE id = ?').run(JSON.stringify(settings), storeId);
}

export function getIntegration(storeId, kind, provider) {
  const row = db.prepare('SELECT * FROM integrations WHERE store_id = ? AND kind = ? AND provider = ?').get(storeId, kind, provider);
  return row && hydrateIntegration(row);
}
export function listIntegrations(storeId, kind) {
  return db.prepare('SELECT * FROM integrations WHERE store_id = ? AND kind = ?').all(storeId, kind).map(hydrateIntegration);
}
function hydrateIntegration(row) {
  return { ...row, enabled: !!row.enabled, credentials: row.credentials ? j(decrypt(row.credentials), {}) : {}, settings: j(row.settings, {}) };
}
export function saveIntegration(storeId, kind, provider, { credentials, settings, enabled = true, verified = false }) {
  const existing = getIntegration(storeId, kind, provider);
  // Blank secret fields in the form mean "keep the saved value".
  const merged = { ...(existing?.credentials || {}) };
  for (const [k, v] of Object.entries(credentials || {})) if (v !== '' && v != null) merged[k] = v;
  db.prepare(`INSERT INTO integrations (store_id, kind, provider, credentials, settings, enabled, verified_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(store_id, kind, provider) DO UPDATE SET credentials = excluded.credentials, settings = excluded.settings,
      enabled = excluded.enabled, verified_at = COALESCE(excluded.verified_at, verified_at)`)
    .run(storeId, kind, provider, encrypt(JSON.stringify(merged)), JSON.stringify(settings || {}), enabled ? 1 : 0, verified ? new Date().toISOString() : null);
  return getIntegration(storeId, kind, provider);
}
export function markIntegrationVerified(storeId, kind, provider) {
  db.prepare('UPDATE integrations SET verified_at = ? WHERE store_id = ? AND kind = ? AND provider = ?').run(new Date().toISOString(), storeId, kind, provider);
}

export function hydrateOrder(row) {
  if (!row) return row;
  return { ...row, test_mode: !!row.test_mode, invoice_test: !!row.invoice_test, data: j(row.data, {}), issues: j(row.issues, []), last_error: j(row.last_error, null), overrides: j(row.overrides, {}) };
}
export function getOrder(id) {
  return hydrateOrder(db.prepare('SELECT * FROM orders WHERE id = ?').get(id));
}
export function getOrderByShopifyId(storeId, shopifyId) {
  return hydrateOrder(db.prepare('SELECT * FROM orders WHERE store_id = ? AND shopify_id = ?').get(storeId, shopifyId));
}

const ORDER_COLUMNS = new Set(['status', 'payment_method', 'total', 'cod_amount', 'courier', 'service', 'awb', 'awb_at', 'shipping_cost',
  'tracking_status', 'tracking_text', 'tracking_at', 'invoice_provider', 'invoice_series', 'invoice_number', 'invoice_url', 'invoice_at',
  'fulfillment_id', 'fulfilled_at', 'cod_collected_at', 'paid_marked_at', 'issues', 'last_error', 'overrides', 'test_mode', 'invoice_test', 'data', 'name']);

export function updateOrder(id, fields) {
  const sets = [];
  const vals = [];
  for (const [k, v] of Object.entries(fields)) {
    if (!ORDER_COLUMNS.has(k)) throw new Error(`Unknown order column ${k}`);
    sets.push(`${k} = ?`);
    vals.push(v !== null && typeof v === 'object' ? JSON.stringify(v) : typeof v === 'boolean' ? Number(v) : v);
  }
  if (!sets.length) return getOrder(id);
  db.prepare(`UPDATE orders SET ${sets.join(', ')}, updated_at = datetime('now') WHERE id = ?`).run(...vals, id);
  return getOrder(id);
}

/** Inserts or refreshes an order coming from Shopify. Never overwrites our own processing columns. */
export function upsertOrder(storeId, order) {
  db.prepare(`INSERT INTO orders (store_id, shopify_id, name, data, created_at, payment_method, total, cod_amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(store_id, shopify_id) DO UPDATE SET name = excluded.name, data = excluded.data,
      payment_method = excluded.payment_method, total = excluded.total,
      cod_amount = CASE WHEN orders.awb IS NULL THEN excluded.cod_amount ELSE orders.cod_amount END,
      updated_at = datetime('now')`)
    .run(storeId, order.shopifyId, order.name, JSON.stringify(order), order.createdAt, order.paymentMethod, order.total, order.codAmount);
  return getOrderByShopifyId(storeId, order.shopifyId);
}

/**
 * Claims an order for processing, atomically in the database, so two processes (or a crashed
 * run and a retry) never work on it at once. Returns:
 *   'ok'      — claimed
 *   'busy'    — claimed by someone else less than `leaseMs` ago
 *   'stale'   — a previous claim was never released (crash mid-processing); NOT claimed
 *   'taken_over' — same, but `takeOver` was set: claimed
 */
export function claimOrder(id, { leaseMs = 10 * 60_000, takeOver = false } = {}) {
  const now = new Date();
  const r = db.prepare('UPDATE orders SET processing_at = ? WHERE id = ? AND processing_at IS NULL').run(now.toISOString(), id);
  if (r.changes === 1) return 'ok';
  const row = db.prepare('SELECT processing_at FROM orders WHERE id = ?').get(id);
  if (!row) return 'busy';
  if (!row.processing_at) return claimOrder(id, { leaseMs, takeOver });
  if (now - new Date(row.processing_at) < leaseMs) return 'busy';
  if (!takeOver) return 'stale';
  const t = db.prepare('UPDATE orders SET processing_at = ? WHERE id = ? AND processing_at = ?').run(now.toISOString(), id, row.processing_at);
  return t.changes === 1 ? 'taken_over' : 'busy';
}
export function releaseOrder(id) {
  db.prepare('UPDATE orders SET processing_at = NULL WHERE id = ?').run(id);
}

export function logEvent(storeId, orderId, level, step, message, data) {
  db.prepare('INSERT INTO events (store_id, order_id, level, step, message, data) VALUES (?, ?, ?, ?, ?, ?)')
    .run(storeId, orderId ?? null, level, step ?? null, message, data === undefined ? null : JSON.stringify(data));
}
export function orderEvents(orderId) {
  return db.prepare('SELECT * FROM events WHERE order_id = ? ORDER BY id').all(orderId).map((e) => ({ ...e, data: j(e.data, null) }));
}

/** Synchronous per-store cache handed to adapters as ctx.cache. */
export function storeCache(storeId) {
  return {
    get(key) {
      const row = db.prepare('SELECT value, expires_at FROM cache WHERE store_id = ? AND key = ?').get(storeId, key);
      if (!row) return undefined;
      if (row.expires_at < Date.now()) {
        db.prepare('DELETE FROM cache WHERE store_id = ? AND key = ?').run(storeId, key);
        return undefined;
      }
      return j(row.value, undefined);
    },
    set(key, value, ttlSeconds = 3600) {
      db.prepare(`INSERT INTO cache (store_id, key, value, expires_at) VALUES (?, ?, ?, ?)
        ON CONFLICT(store_id, key) DO UPDATE SET value = excluded.value, expires_at = excluded.expires_at`)
        .run(storeId, key, JSON.stringify(value), Date.now() + ttlSeconds * 1000);
    },
    delete(key) {
      db.prepare('DELETE FROM cache WHERE store_id = ? AND key = ?').run(storeId, key);
    },
  };
}

/** Returns true the first time a webhook id is seen (Shopify retries deliveries). */
export function firstSeenWebhook(id) {
  if (!id) return true;
  const r = db.prepare('INSERT OR IGNORE INTO webhooks_seen (id) VALUES (?)').run(id);
  return r.changes === 1;
}
