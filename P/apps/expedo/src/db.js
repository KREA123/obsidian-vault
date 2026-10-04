import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { config } from './config.js';
import { encrypt, decrypt, sealJson, openJson, sealText, openText, isSealed } from './lib/crypto.js';
import { orderIdentity } from './core/identity.js';
import { t, isMessage } from './i18n/index.js';

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
      data TEXT NOT NULL,                     -- normalized order (src/shopify/mapper.js), encrypted
      status TEXT NOT NULL DEFAULT 'new',     -- see ORDER_STATUSES in core/pipeline.js
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
      issues TEXT NOT NULL DEFAULT '[]',      -- validation issues, encrypted (can quote the phone)
      last_error TEXT,                        -- ProcessingError JSON, encrypted (provider answers)
      overrides TEXT NOT NULL DEFAULT '{}',   -- manual edits (address fixes, parcels, courier...), encrypted
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
      message TEXT NOT NULL,                  -- encrypted; '' when key is set (older rows: Romanian text)
      data TEXT,                              -- encrypted
      key TEXT,                               -- catalog key of the message (src/i18n), rendered when read
      params TEXT                             -- encrypted JSON params of the message
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

    -- Who looked at or exported customer data (Shopify protected customer data). No customer data here.
    CREATE TABLE IF NOT EXISTS access_log (
      id INTEGER PRIMARY KEY,
      store_id INTEGER NOT NULL,
      at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
      actor TEXT NOT NULL,                    -- 'shopify-session <user id>' | 'admin' | 'shopify' (GDPR webhooks)
      action TEXT NOT NULL,                   -- see ACCESS_ACTIONS in core/privacy.js
      order_id INTEGER,
      order_name TEXT,                        -- kept when the order is deleted (shop/redact deletes this too)
      detail TEXT
    );
    CREATE INDEX IF NOT EXISTS access_store ON access_log(store_id, id DESC);
    CREATE INDEX IF NOT EXISTS access_at ON access_log(at);
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
  // Keyed hashes of the customer (core/identity.js): search and refusal history without plaintext.
  for (const c of ['phone_hash', 'email_hash', 'search_terms']) if (!cols.has(c)) db.exec(`ALTER TABLE orders ADD COLUMN ${c} TEXT`);
  // When the order reached a final state (retention counts from here) and when its customer data was removed.
  if (!cols.has('finished_at')) {
    db.exec('ALTER TABLE orders ADD COLUMN finished_at TEXT');
    db.exec(`UPDATE orders SET finished_at = strftime('%Y-%m-%dT%H:%M:%fZ', COALESCE(tracking_at, updated_at)) WHERE ${FINISHED_SQL}`);
  }
  if (!cols.has('redacted_at')) db.exec('ALTER TABLE orders ADD COLUMN redacted_at TEXT');
  // Events store a catalog key + params instead of rendered (Romanian) text; old rows keep their text.
  const eventCols = new Set(db.prepare('PRAGMA table_info(events)').all().map((c) => c.name));
  if (!eventCols.has('key')) db.exec('ALTER TABLE events ADD COLUMN key TEXT');
  if (!eventCols.has('params')) db.exec('ALTER TABLE events ADD COLUMN params TEXT');
  // Pricing plan cache (core/plans.js): plan id, what Shopify said (JSON), when it was last checked.
  const storeCols = new Set(db.prepare('PRAGMA table_info(stores)').all().map((c) => c.name));
  for (const c of ['plan', 'plan_info', 'plan_checked_at']) if (!storeCols.has(c)) db.exec(`ALTER TABLE stores ADD COLUMN ${c} TEXT`);
  db.exec(`CREATE INDEX IF NOT EXISTS orders_phone ON orders(store_id, phone_hash);
    CREATE INDEX IF NOT EXISTS orders_email ON orders(store_id, email_hash);
    CREATE INDEX IF NOT EXISTS orders_finished ON orders(store_id, finished_at);`);
  encryptPlaintextRows();
}

/**
 * One-time migration: rows written before customer data was encrypted are re-saved encrypted,
 * with their search hashes. Safe to run on every start: sealed rows are skipped.
 */
function encryptPlaintextRows() {
  const orders = db.prepare(`SELECT id, store_id, data, overrides, issues, last_error FROM orders WHERE data NOT LIKE 'enc1:%'`).all();
  const events = db.prepare(`SELECT id, message, data FROM events WHERE message NOT LIKE 'enc1:%'`).all();
  const cache = db.prepare(`SELECT store_id, key, value FROM cache WHERE value NOT LIKE 'enc1:%'`).all();
  if (!orders.length && !events.length && !cache.length) return;
  db.exec('BEGIN');
  try {
    const upOrder = db.prepare(`UPDATE orders SET data = ?, overrides = ?, issues = ?, last_error = ?, phone_hash = ?, email_hash = ?, search_terms = ? WHERE id = ?`);
    for (const o of orders) {
      const data = openJson(o.data, {});
      const overrides = openJson(o.overrides, {});
      const id = orderIdentity(o.store_id, data, overrides);
      upOrder.run(sealJson(data), sealJson(overrides), sealJson(openJson(o.issues, [])), o.last_error ? sealJson(openJson(o.last_error, null)) : null,
        id.phoneHash, id.emailHash, id.searchTerms, o.id);
    }
    const upEvent = db.prepare('UPDATE events SET message = ?, data = ? WHERE id = ?');
    for (const e of events) upEvent.run(sealText(e.message), isSealed(e.data) || e.data == null ? e.data : sealText(e.data), e.id);
    const upCache = db.prepare('UPDATE cache SET value = ? WHERE store_id = ? AND key = ?');
    for (const c of cache) upCache.run(sealText(c.value), c.store_id, c.key);
    db.exec('COMMIT');
  } catch (err) {
    db.exec('ROLLBACK');
    throw err;
  }
}

/** Nothing left to do for the order: delivered, returned, cancelled, or fulfilled outside Expedo (no AWB). */
export const FINISHED_SQL = `(status IN ('delivered', 'returned', 'cancelled') OR (status = 'shipped' AND awb IS NULL))`;

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
  return { ...row, demo: !!row.demo, settings: j(row.settings, {}), plan_info: j(row.plan_info, {}), accessToken: row.access_token ? decrypt(row.access_token) : null };
}
/** A failed plan check: keep the cached plan, check again after the usual interval. */
export function touchPlanChecked(storeId) {
  db.prepare('UPDATE stores SET plan_checked_at = ? WHERE id = ?').run(new Date().toISOString(), storeId);
}
/** Caches the store's pricing plan (core/plans.js). */
export function saveStorePlan(storeId, plan, info = {}) {
  db.prepare('UPDATE stores SET plan = ?, plan_info = ?, plan_checked_at = ? WHERE id = ?').run(plan, JSON.stringify(info), new Date().toISOString(), storeId);
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
  const { phone_hash, email_hash, search_terms, ...rest } = row;
  return {
    ...rest, test_mode: !!row.test_mode, invoice_test: !!row.invoice_test,
    data: openJson(row.data, {}), issues: openJson(row.issues, []), last_error: openJson(row.last_error, null), overrides: openJson(row.overrides, {}),
    // Hashes stay out of everything sent to the browser; customer history reads them from the row.
    customerKeys: { phone: phone_hash, email: email_hash },
  };
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

// Columns with customer data: encrypted on write, decrypted by hydrateOrder.
const SEALED_COLUMNS = new Set(['data', 'overrides', 'issues', 'last_error']);

export function updateOrder(id, fields) {
  const sets = [];
  const vals = [];
  for (const [k, v] of Object.entries(fields)) {
    if (!ORDER_COLUMNS.has(k)) throw new Error(`Unknown order column ${k}`);
    sets.push(`${k} = ?`);
    if (SEALED_COLUMNS.has(k)) vals.push(v == null ? (k === 'last_error' ? null : sealJson(k === 'issues' ? [] : {})) : sealJson(v));
    else vals.push(v !== null && typeof v === 'object' ? JSON.stringify(v) : typeof v === 'boolean' ? Number(v) : v);
  }
  if (!sets.length) return getOrder(id);
  db.prepare(`UPDATE orders SET ${sets.join(', ')}, updated_at = datetime('now') WHERE id = ?`).run(...vals, id);
  if ('data' in fields || 'overrides' in fields) refreshIdentity(id);
  if ('status' in fields || 'awb' in fields) markFinished(id);
  return getOrder(id);
}

/** Recomputes the customer hashes (search + history) from the order's data and manual fixes. */
function refreshIdentity(id) {
  const row = db.prepare('SELECT store_id, data, overrides, redacted_at FROM orders WHERE id = ?').get(id);
  if (!row) return;
  const k = row.redacted_at ? {} : orderIdentity(row.store_id, openJson(row.data, {}), openJson(row.overrides, {}));
  db.prepare('UPDATE orders SET phone_hash = ?, email_hash = ?, search_terms = ? WHERE id = ?').run(k.phoneHash ?? null, k.emailHash ?? null, k.searchTerms ?? null, id);
}

/** finished_at = when the order reached a final state; cleared if it leaves it (e.g. AWB cancelled). */
function markFinished(id) {
  db.prepare(`UPDATE orders SET finished_at = CASE WHEN ${FINISHED_SQL} THEN COALESCE(finished_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) ELSE NULL END WHERE id = ?`).run(id);
}

/** Inserts or refreshes an order coming from Shopify. Never overwrites our own processing columns. */
export function upsertOrder(storeId, order) {
  // A redacted order that Shopify sends again (orders/updated) has its customer data back: the
  // retention job removes it again once the retention period has passed.
  db.prepare(`INSERT INTO orders (store_id, shopify_id, name, data, created_at, payment_method, total, cod_amount)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(store_id, shopify_id) DO UPDATE SET name = excluded.name, data = excluded.data,
      payment_method = excluded.payment_method, total = excluded.total,
      cod_amount = CASE WHEN orders.awb IS NULL THEN excluded.cod_amount ELSE orders.cod_amount END,
      redacted_at = NULL, updated_at = datetime('now')`)
    .run(storeId, order.shopifyId, order.name, sealJson(order), order.createdAt, order.paymentMethod, order.total, order.codAmount);
  const { id } = db.prepare('SELECT id FROM orders WHERE store_id = ? AND shopify_id = ?').get(storeId, order.shopifyId);
  refreshIdentity(id);
  return getOrder(id);
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

/**
 * Records an event in the order / store history. `message` is a message { key, params } (src/i18n m()),
 * rendered in the viewer's language when read; a plain string is stored as is (shown verbatim).
 * `data.hint` may be a message too.
 */
export function logEvent(storeId, orderId, level, step, message, data) {
  const keyed = isMessage(message);
  db.prepare('INSERT INTO events (store_id, order_id, level, step, message, data, key, params) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
    .run(storeId, orderId ?? null, level, step ?? null, sealText(keyed ? '' : String(message)), data === undefined ? null : sealJson(data),
      keyed ? message.key : null, keyed && message.params ? sealJson(message.params) : null);
}
const hydrateEvent = (e) => ({ ...e, message: openText(e.message), data: openJson(e.data, null), params: openJson(e.params, null) });

/** Event row → text in `locale` (message, data.hint). Rows from before the catalogs keep their stored text. */
export function renderEvent(e, locale) {
  const { params, key, ...rest } = e;
  const hint = rest.data?.hint;
  return {
    ...rest,
    message: key ? t(locale, key, params || {}) : rest.message,
    data: rest.data && hint != null ? { ...rest.data, hint: isMessage(hint) ? t(locale, hint) : hint } : rest.data,
  };
}
export function orderEvents(orderId) {
  return db.prepare('SELECT * FROM events WHERE order_id = ? ORDER BY id').all(orderId).map(hydrateEvent);
}
/** Latest events of a store (Activitate), with the order name. */
export function storeEvents(storeId, limit = 200) {
  return db.prepare(`SELECT e.*, o.name order_name FROM events e LEFT JOIN orders o ON o.id = e.order_id
    WHERE e.store_id = ? ORDER BY e.id DESC LIMIT ?`).all(storeId, limit).map(hydrateEvent);
}

// ---------- access log ----------
/**
 * Records that someone saw or exported customer data. Opening the same order again within a few
 * minutes (the panel reloads after every action) is one visit, not ten.
 */
export function logAccess(storeId, { actor, action, orderId = null, orderName = null, detail = null }) {
  if (action === 'order_view' && orderId) {
    const recent = db.prepare(`SELECT 1 FROM access_log WHERE store_id = ? AND order_id = ? AND actor = ? AND action = 'order_view'
      AND at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-5 minutes')`).get(storeId, orderId, actor);
    if (recent) return;
  }
  // A message detail ({ key, params }) is kept as JSON and translated when the log is shown.
  const text = detail == null ? null : isMessage(detail) ? JSON.stringify(detail) : String(detail);
  db.prepare('INSERT INTO access_log (store_id, actor, action, order_id, order_name, detail) VALUES (?, ?, ?, ?, ?, ?)')
    .run(storeId, String(actor).slice(0, 120), action, orderId, orderName, text == null ? null : text.slice(0, 500));
}

/** Access-log detail → text in `locale` (plain text from older rows as is). */
export function renderAccessDetail(detail, locale) {
  if (detail == null || detail === '') return detail;
  if (detail.startsWith('{"key"')) {
    try { return t(locale, JSON.parse(detail)); } catch { /* plain text */ }
  }
  return detail;
}
export function listAccess(storeId, { action = '', order = '', limit = 100, offset = 0 } = {}) {
  const where = ['store_id = ?'];
  const args = [storeId];
  if (action) { where.push('action = ?'); args.push(action); }
  if (order) { where.push(`order_name LIKE ? ESCAPE '\\'`); args.push(`%${order.replace(/[\\%_]/g, (c) => `\\${c}`)}%`); }
  const rows = db.prepare(`SELECT * FROM access_log WHERE ${where.join(' AND ')} ORDER BY id DESC LIMIT ? OFFSET ?`).all(...args, limit, offset);
  const total = db.prepare(`SELECT COUNT(*) c FROM access_log WHERE ${where.join(' AND ')}`).get(...args).c;
  return { rows, total };
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
      return openJson(row.value, undefined);
    },
    // Encrypted too: the test courier keeps the shipments it "made" (recipient included) for its labels.
    set(key, value, ttlSeconds = 3600) {
      db.prepare(`INSERT INTO cache (store_id, key, value, expires_at) VALUES (?, ?, ?, ?)
        ON CONFLICT(store_id, key) DO UPDATE SET value = excluded.value, expires_at = excluded.expires_at`)
        .run(storeId, key, sealText(JSON.stringify(value ?? null)), Date.now() + ttlSeconds * 1000);
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
