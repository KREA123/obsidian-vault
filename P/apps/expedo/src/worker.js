import * as db from './db.js';
import { config } from './config.js';
import { processOrder, trackStore, importOrder, enqueue } from './core/pipeline.js';
import { getShopify } from './shopify/index.js';
import { ProcessingError, toProcessingError, errorMessage, errorHint } from './core/errors.js';
import { m } from './i18n/index.js';
import { applyRetention, pruneAccessLog } from './core/privacy.js';
import { refreshPlan, planStale, isComplimentary, REFRESH_MS } from './core/plans.js';

// Background jobs stored in SQLite, so nothing is lost on restart.
// Backoff for retryable failures: 1, 5, 15, 60, 180 minutes.
const BACKOFF_MIN = [1, 5, 15, 60, 180];

export const handlers = {
  async process_order(store, { orderId }) {
    const res = await processOrder(store, orderId);
    // processOrder records the error on the order; a retryable one goes back to the queue with backoff.
    if (!res.ok && res.error?.retryable) throw new ProcessingError(res.error);
    return res;
  },
  async sync_order(store, { gid }) {
    const order = await getShopify(store).getOrder(gid);
    if (order) importOrder(store, order, { source: 'webhook' });
  },
  async sync_store(store, { days = 14 } = {}) {
    const since = new Date(Date.now() - days * 86400_000).toISOString().slice(0, 10);
    const orders = await getShopify(store).listOrders({ search: `created_at:>=${since}`, max: 500 });
    for (const o of orders.reverse()) importOrder(store, o, { source: 'resync' });
    return { imported: orders.length };
  },
  async track_store(store) {
    return trackStore(store);
  },
  // Pricing plan from Shopify: every 6 hours, or right away (force) after a subscription webhook.
  async refresh_plan(store, { force = false } = {}) {
    if (isComplimentary(store) || (!force && !planStale(store))) return { skipped: true };
    try {
      await refreshPlan(store, getShopify(store), { source: force ? 'webhook' : 'refresh' });
    } catch (err) {
      // Keep the cached plan (never downgrade on an outage) and try again at the next interval.
      console.error('refresh_plan', store.shop, err.message);
      db.touchPlanChecked(store.id);
      return { ok: false };
    }
    return { ok: true };
  },
  // Daily: customer data of old finished orders (store setting "Keep customer data"), access log > 1 year.
  async privacy_cleanup(store) {
    const r = applyRetention(store);
    pruneAccessLog();
    return r;
  },
};

let running = false;

export async function runDueJobs(limit = 10) {
  if (running) return 0;
  running = true;
  try {
    const d = db.getDb();
    const now = new Date().toISOString();
    const jobs = d.prepare(`SELECT * FROM jobs WHERE status = 'pending' AND run_at <= ? ORDER BY run_at LIMIT ?`).all(now, limit);
    for (const job of jobs) {
      // Skip a job another runner already took (status changed since the SELECT).
      if (d.prepare(`UPDATE jobs SET status = 'running', attempts = attempts + 1 WHERE id = ? AND status = 'pending'`).run(job.id).changes !== 1) continue;
      const store = db.getStore(job.store_id);
      try {
        if (!store || store.uninstalled_at) throw new ProcessingError({ code: 'STORE_GONE' });
        if (!Object.hasOwn(handlers, job.type)) throw new ProcessingError({ code: 'JOB_UNKNOWN', params: { job: job.type } });
        await handlers[job.type](store, JSON.parse(job.payload));
        d.prepare(`UPDATE jobs SET status = 'done' WHERE id = ?`).run(job.id);
      } catch (err) {
        const e = toProcessingError(err, job.type);
        const attempts = job.attempts + 1;
        if (e.retryable && attempts < job.max_attempts) {
          const at = new Date(Date.now() + BACKOFF_MIN[Math.min(attempts - 1, BACKOFF_MIN.length - 1)] * 60_000).toISOString();
          try {
            d.prepare(`UPDATE jobs SET status = 'pending', run_at = ?, last_error = ? WHERE id = ?`).run(at, e.message, job.id);
          } catch (err2) {
            // The same work is already queued again (e.g. processOrder scheduled its own retry): keep that one.
            if (!/UNIQUE/.test(err2.message)) throw err2;
            d.prepare(`UPDATE jobs SET status = 'done', last_error = ? WHERE id = ?`).run(`${e.message} (retry already scheduled)`, job.id);
          }
        } else {
          d.prepare(`UPDATE jobs SET status = 'failed', last_error = ? WHERE id = ?`).run(e.message, job.id);
          if (store) db.logEvent(store.id, job.payload.includes('orderId') ? JSON.parse(job.payload).orderId : null, 'error', job.type, m('events.jobFailed', { job: job.type, error: errorMessage(e) }), { hint: errorHint(e) });
        }
      }
    }
    return jobs.length;
  } finally {
    running = false;
  }
}

/** Periodic safety nets: tracking for all stores, and a re-sync in case a webhook was missed. */
export function schedulePeriodic() {
  const now = Date.now();
  for (const store of db.listStores()) {
    enqueue(store.id, 'track_store', {}, { key: `track:${store.id}`, runAt: new Date(now + config.trackingIntervalMinutes * 60_000).toISOString(), maxAttempts: 1 });
    if (!store.demo) enqueue(store.id, 'sync_store', { days: 3 }, { key: `sync:${store.id}`, runAt: new Date(now + 15 * 60_000).toISOString(), maxAttempts: 2 });
    // Never-checked stores (installed before plans existed) right away, the others 6 hours after the last check.
    const nextPlanCheck = store.plan_checked_at ? Math.max(now, Date.parse(store.plan_checked_at) + REFRESH_MS) : now;
    if (!isComplimentary(store)) enqueue(store.id, 'refresh_plan', {}, { key: `plan:${store.id}`, runAt: new Date(nextPlanCheck).toISOString(), maxAttempts: 1 });
    enqueue(store.id, 'privacy_cleanup', {}, { key: `privacy:${store.id}`, runAt: new Date(now + 24 * 3600_000).toISOString(), maxAttempts: 2 });
  }
}

/** Startup cleanup: drops old finished jobs and requeues jobs left "running" by a crash. */
export function recoverJobs() {
  const d = db.getDb();
  d.exec(`DELETE FROM jobs WHERE status IN ('done', 'failed') AND created_at < datetime('now', '-7 days');
    DELETE FROM webhooks_seen WHERE at < datetime('now', '-7 days');`);
  for (const job of d.prepare(`SELECT id FROM jobs WHERE status = 'running'`).all()) {
    try {
      d.prepare(`UPDATE jobs SET status = 'pending' WHERE id = ?`).run(job.id);
    } catch (err) {
      // An identical job is already pending; that one will do the work.
      if (!/UNIQUE/.test(err.message)) throw err;
      d.prepare(`UPDATE jobs SET status = 'done', last_error = 'interrupted; replaced by an identical job' WHERE id = ?`).run(job.id);
    }
  }
}

export function startWorker() {
  recoverJobs();
  schedulePeriodic();
  const t1 = setInterval(() => runDueJobs().catch((e) => console.error('worker', e)), config.workerIntervalMs);
  const t2 = setInterval(schedulePeriodic, 60_000);
  t1.unref(); t2.unref();
}
