import * as db from '../db.js';
import { config } from '../config.js';
import { m } from '../i18n/index.js';

// Pricing plans (Shopify App Pricing, formerly "managed pricing": the plans live in the Partner Dashboard,
// Shopify hosts the plan selection page and bills the merchant). See PRICING.md.
//
// The plan is cached on the store row (stores.plan / plan_info / plan_checked_at). It is refreshed on
// install, when Shopify says the subscription changed, when the merchant comes back from the plan page,
// and at most every 6 hours by the worker. Demo stores and SHOPIFY_OWN_STORES are always on Plus.
//
// What is gated: the monthly AWB limit (live AWBs only; test mode never counts) and the Growth features.
// The address & phone check is on for every plan: it is what prevents failed AWBs.

/** Features a plan can include. Names are what can(store, feature) takes. */
export const FEATURES = [
  'addressCheck', 'allIntegrations', 'testMode', 'bulk', 'rules', 'tracking', 'codReconciliation',
  'autoProcess', 'refusalHistory', 'codExport', 'prioritySupport', 'multiStore', 'customIntegration',
];

const BASE = ['addressCheck', 'allIntegrations', 'testMode', 'bulk', 'rules', 'tracking', 'codReconciliation'];
const GROWTH = [...BASE, 'autoProcess', 'refusalHistory', 'codExport', 'prioritySupport'];

/**
 * The catalog. `name` must match the plan's name in the Partner Dashboard (case doesn't matter).
 * limit = live AWBs per billing period (30 days), null = unlimited. Prices in USD every 30 days.
 */
export const PLANS = {
  free: { id: 'free', name: 'Free', price: 0, limit: 50, features: BASE },
  starter: { id: 'starter', name: 'Starter', price: 14.99, limit: 1000, features: BASE },
  growth: { id: 'growth', name: 'Growth', price: 24.99, limit: null, features: GROWTH },
  plus: { id: 'plus', name: 'Plus', price: 49.99, limit: null, features: [...GROWTH, 'multiStore', 'customIntegration'] },
};
export const PLAN_IDS = Object.keys(PLANS);
export const TRIAL_DAYS = 30;
const PERIOD_MS = 30 * 86400_000;
/** Usage share from which the dashboard shows the "almost at your limit" banner. */
export const WARN_AT = 0.8;
/** The worker re-checks the subscription at most this often. */
export const REFRESH_MS = 6 * 3600_000;

/** Lowest plan that has a feature ("Available on Growth"). */
export function minPlanFor(feature) {
  return PLAN_IDS.find((id) => PLANS[id].features.includes(feature)) || 'plus';
}

/**
 * Shopify subscription name / plan handle → plan id. Case-insensitive; "Growth", "growth", "Expedo Growth",
 * "growth_plan" all give 'growth'. Unknown names → null.
 */
export function planIdFromName(name) {
  const s = String(name ?? '').trim().toLowerCase();
  if (!s) return null;
  for (const p of Object.values(PLANS)) if (s === p.id || s === p.name.toLowerCase()) return p.id;
  const words = new Set(s.split(/[^a-z0-9]+/).filter(Boolean));
  // Most expensive first: a name like "Plus (was Growth)" is not something to guess from, but "plus" wins.
  return [...PLAN_IDS].reverse().find((id) => words.has(id)) || null;
}

const isOwnStore = (store) => config.shopify.ownStores.includes(store?.shop);
/** Stores that are always on Plus and never asked about billing. */
export const isComplimentary = (store) => !!store?.demo || isOwnStore(store);

/** The store's plan id (cached). */
export function planIdFor(store) {
  if (isComplimentary(store)) return 'plus';
  return Object.hasOwn(PLANS, store?.plan || '') ? store.plan : 'free';
}

/** The store's plan from the catalog. */
export function planFor(store) {
  return PLANS[planIdFor(store)];
}

/** Does the store's plan include `feature`? */
export function can(store, feature) {
  return planFor(store).features.includes(feature);
}

/**
 * Current billing period [start, end): the subscription's 30-day period (rolled forward when the cached
 * end has passed), or the calendar month (Europe/Bucharest) when there is no paid subscription period.
 */
export function billingPeriod(store, now = new Date()) {
  const info = store?.plan_info || {};
  const anchor = Date.parse(info.periodEnd || info.trialEndsAt || '');
  if (Number.isFinite(anchor)) {
    let end = anchor;
    const t = now.getTime();
    if (end <= t) end += Math.ceil((t - end + 1) / PERIOD_MS) * PERIOD_MS;
    while (end - PERIOD_MS > t) end -= PERIOD_MS;
    return { start: new Date(end - PERIOD_MS).toISOString(), end: new Date(end).toISOString(), kind: 'subscription' };
  }
  return { ...bucharestMonth(now), kind: 'month' };
}

function bucharestMonth(now) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Bucharest', year: 'numeric', month: 'numeric' })
    .formatToParts(now).map((x) => [x.type, Number(x.value)]));
  return { start: bucharestMidnight(p.year, p.month), end: bucharestMidnight(p.month === 12 ? p.year + 1 : p.year, p.month === 12 ? 1 : p.month + 1) };
}

/** UTC instant of 00:00 Europe/Bucharest on the 1st of a month (DST-aware). */
function bucharestMidnight(year, month) {
  const wanted = Date.UTC(year, month - 1, 1);
  const wall = (t) => {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Bucharest', hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' })
      .formatToParts(new Date(t)).map((x) => [x.type, Number(x.value)]));
    return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
  };
  let t = wanted;
  for (let i = 0; i < 3; i++) t -= wall(t) - wanted;
  return new Date(t).toISOString();
}

/** Live AWBs created in the current billing period (test-mode AWBs never count; canceled AWBs are gone). */
export function usageThisPeriod(store, now = new Date()) {
  const { start, end } = billingPeriod(store, now);
  return db.getDb().prepare(`SELECT COUNT(*) c FROM orders WHERE store_id = ? AND awb IS NOT NULL AND test_mode = 0
    AND awb_at >= ? AND awb_at < ?`).get(store.id, start, end).c;
}

/** Shopify's hosted plan selection page for this store (null for demo / own stores). */
export function upgradeUrl(store) {
  if (isComplimentary(store) || !store?.shop) return null;
  const handle = String(store.shop).replace(/\.myshopify\.com$/i, '');
  return `https://admin.shopify.com/store/${encodeURIComponent(handle)}/charges/${encodeURIComponent(config.shopify.appHandle)}/pricing_plans`;
}

/** Everything the dashboard shows about the plan (Settings → Plan, usage banner). */
export function planSummary(store, now = new Date()) {
  const plan = planFor(store);
  const info = store?.plan_info || {};
  const period = billingPeriod(store, now);
  const used = usageThisPeriod(store, now);
  const trialEnd = Date.parse(info.trialEndsAt || '');
  const trialDaysLeft = Number.isFinite(trialEnd) && trialEnd > now.getTime() ? Math.ceil((trialEnd - now.getTime()) / 86400_000) : 0;
  return {
    id: plan.id, name: plan.name, price: plan.price, limit: plan.limit, used,
    remaining: plan.limit == null ? null : Math.max(0, plan.limit - used),
    nearLimit: plan.limit != null && used >= plan.limit * WARN_AT,
    reached: plan.limit != null && used >= plan.limit,
    periodStart: period.start, periodEnd: period.end, periodKind: period.kind,
    trialDaysLeft, test: !!info.test, complimentary: isComplimentary(store),
    features: Object.fromEntries(FEATURES.map((f) => [f, plan.features.includes(f)])),
    upgradeUrl: upgradeUrl(store), checkedAt: store?.plan_checked_at || null,
  };
}

/** Saves what Shopify says; logs an event when the plan changes. Returns the fresh store. */
export function applySubscription(store, sub, { source = 'refresh' } = {}) {
  const id = sub ? planIdFromName(sub.name) : 'free';
  if (sub && !id) console.warn(`plans: unknown subscription name "${sub.name}" for ${store.shop}; treated as Free`);
  const plan = id || 'free';
  const info = sub ? { name: sub.name, status: sub.status || 'ACTIVE', trialEndsAt: sub.trialEndsAt || null, periodEnd: sub.periodEnd || null, test: !!sub.test, source } : { source };
  const before = planIdFor(store);
  db.saveStorePlan(store.id, plan, info);
  const fresh = db.getStore(store.id);
  if (before !== planIdFor(fresh) || !store.plan) {
    db.logEvent(store.id, null, 'info', 'plan', m('events.planChanged', { plan: PLANS[plan].name }));
  }
  return fresh;
}

/**
 * Asks Shopify for the store's active subscription and caches it. Demo / own stores are skipped (Plus).
 * On a network or API error the cached plan stays: a paying merchant is never downgraded by an outage.
 */
export async function refreshPlan(store, client, { source = 'refresh' } = {}) {
  if (isComplimentary(store)) return store;
  const sub = await client.activeSubscription();
  return applySubscription(store, sub, { source });
}

/** True when the cached plan is older than the refresh interval. */
export const planStale = (store, now = Date.now()) => !store?.plan_checked_at || now - Date.parse(store.plan_checked_at) >= REFRESH_MS;
