import * as db from '../db.js';
import { config } from '../config.js';
import { m } from '../i18n/index.js';

// Pricing plans (Shopify App Pricing, formerly "managed pricing": the plans live in the Partner Dashboard,
// Shopify hosts the plan selection page and bills the merchant). See PRICING.md.
//
// The plan is cached on the store row (stores.plan / plan_info / plan_checked_at). It is refreshed on
// install, when Shopify says the subscription changed, when the merchant comes back from the plan page,
// and at most every 6 hours by the worker. Demo stores and SHOPIFY_OWN_STORES are always on Pro Max.
//
// There is no free plan: every plan starts with a 5-day free trial (set on the plan in the Partner Dashboard).
// Without an active subscription (never chose a plan, trial cancelled, subscription expired or frozen) the
// store is on 'none': live AWBs and invoices are refused (PLAN_REQUIRED), test mode works fully, and existing
// documents (tracking, labels, cancel, storno) are never blocked.
//
// What is gated: no plan → no live documents; Pro → 1,000 live AWBs per billing period (test mode never
// counts); the Pro Max features. The address & phone check is on for every plan: it prevents failed AWBs.

/** Features a plan can include. Names are what can(store, feature) takes. */
export const FEATURES = [
  'addressCheck', 'allIntegrations', 'testMode', 'bulk', 'rules', 'tracking', 'codReconciliation',
  'autoProcess', 'refusalHistory', 'codExport', 'multiStore', 'prioritySupport',
];

const BASE = ['addressCheck', 'allIntegrations', 'testMode', 'bulk', 'rules', 'tracking', 'codReconciliation'];
const PRO_MAX = [...BASE, 'autoProcess', 'refusalHistory', 'codExport', 'multiStore', 'prioritySupport'];

/**
 * The catalog. `name` must match the plan's name in the Partner Dashboard (case doesn't matter).
 * limit = live AWBs per billing period (30 days), null = unlimited. Prices in USD every 30 days.
 */
export const PLANS = {
  pro: { id: 'pro', name: 'Pro', price: 15, limit: 1000, features: BASE },
  promax: { id: 'promax', name: 'Pro Max', price: 30, limit: null, features: PRO_MAX },
};
export const PLAN_IDS = Object.keys(PLANS);
/**
 * No active subscription. Not a plan merchants can pick: live AWBs and invoices need one (PLAN_REQUIRED).
 * Its features are what test mode needs; the Pro Max features stay locked.
 */
export const NO_PLAN = { id: 'none', name: 'None', price: null, limit: null, features: BASE };
/** Old plan ids (cached on store rows) and names → today's plan id. */
const LEGACY = { free: 'none', starter: 'pro', growth: 'promax', plus: 'promax' };
/** Free trial of every plan, in days (set on each plan in the Partner Dashboard). */
export const TRIAL_DAYS = 5;
const PERIOD_MS = 30 * 86400_000;
/** Usage share from which the dashboard shows the "almost at your limit" banner. */
export const WARN_AT = 0.8;
/** The worker re-checks the subscription at most this often. */
export const REFRESH_MS = 6 * 3600_000;

/** Lowest plan that has a feature ("Available on Pro Max"). */
export function minPlanFor(feature) {
  return PLAN_IDS.find((id) => PLANS[id].features.includes(feature)) || 'promax';
}

/**
 * Shopify subscription name / plan handle → plan id. Case-insensitive; "Pro Max", "pro_max", "promax",
 * "Expedo Pro Max" give 'promax'; "Pro", "Expedo Pro" give 'pro'. Old plan names map to today's plans
 * (Starter → pro, Growth / Plus → promax, Free → none). Unknown names → null.
 */
export function planIdFromName(name) {
  const words = String(name ?? '').trim().toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  if (!words.length) return null;
  const has = (w) => words.includes(w);
  // Pro Max before Pro: "Pro Max" also contains the word "pro".
  if (has('promax') || words.some((w, i) => w === 'pro' && words[i + 1] === 'max')) return 'promax';
  if (has('pro')) return 'pro';
  for (const old of ['plus', 'growth', 'starter', 'free']) if (has(old)) return LEGACY[old];
  return null;
}

const isOwnStore = (store) => config.shopify.ownStores.includes(store?.shop);
/** Stores that are always on Pro Max and never asked about billing. */
export const isComplimentary = (store) => !!store?.demo || isOwnStore(store);

/** The store's plan id (cached): 'pro', 'promax', or 'none' without an active subscription. */
export function planIdFor(store) {
  if (isComplimentary(store)) return 'promax';
  const id = store?.plan || '';
  if (Object.hasOwn(PLANS, id)) return id;
  return Object.hasOwn(LEGACY, id) ? LEGACY[id] : 'none';
}

/** The store's plan from the catalog (NO_PLAN without a subscription). */
export function planFor(store) {
  return PLANS[planIdFor(store)] || NO_PLAN;
}

/** True when the store has no active subscription: live AWBs and invoices need a plan. */
export const needsPlan = (store) => planIdFor(store) === 'none';

/** Does the store's plan include `feature`? */
export function can(store, feature) {
  return planFor(store).features.includes(feature);
}

/**
 * Current billing period [start, end): the subscription's 30-day period (rolled forward when the cached
 * end has passed), or the calendar month (Europe/Bucharest) when there is no subscription period.
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
    id: plan.id, name: plan.name, price: plan.price, limit: plan.limit, used, required: plan.id === 'none',
    remaining: plan.limit == null ? null : Math.max(0, plan.limit - used),
    nearLimit: plan.limit != null && used >= plan.limit * WARN_AT,
    reached: plan.limit != null && used >= plan.limit,
    periodStart: period.start, periodEnd: period.end, periodKind: period.kind,
    trialDaysLeft, test: !!info.test, complimentary: isComplimentary(store),
    features: Object.fromEntries(FEATURES.map((f) => [f, plan.features.includes(f)])),
    upgradeUrl: upgradeUrl(store), checkedAt: store?.plan_checked_at || null, trialDays: TRIAL_DAYS,
    // Both plans, for Settings → Plan (side by side).
    catalog: Object.values(PLANS).map((p) => ({ id: p.id, name: p.name, price: p.price, limit: p.limit, features: p.features })),
  };
}

/** Saves what Shopify says; logs an event when the plan changes. Returns the fresh store. */
export function applySubscription(store, sub, { source = 'refresh' } = {}) {
  const id = sub ? planIdFromName(sub.name) : 'none';
  // An active subscription with a name we don't know is still a paying store: never lock it out (Pro).
  if (sub && !id) console.warn(`plans: unknown subscription name "${sub.name}" for ${store.shop}; treated as Pro`);
  const plan = id || 'pro';
  const info = sub ? { name: sub.name, status: sub.status || 'ACTIVE', trialEndsAt: sub.trialEndsAt || null, periodEnd: sub.periodEnd || null, test: !!sub.test, source } : { source };
  const before = planIdFor(store);
  db.saveStorePlan(store.id, plan, info);
  const fresh = db.getStore(store.id);
  if (before !== planIdFor(fresh) || !store.plan) {
    db.logEvent(store.id, null, 'info', 'plan', plan === 'none' ? m('events.planNone') : m('events.planChanged', { plan: PLANS[plan].name }));
  }
  return fresh;
}

/**
 * Asks Shopify for the store's active subscription and caches it. Demo / own stores are skipped (Pro Max).
 * On a network or API error the cached plan stays: a paying merchant is never downgraded by an outage.
 */
export async function refreshPlan(store, client, { source = 'refresh' } = {}) {
  if (isComplimentary(store)) return store;
  const sub = await client.activeSubscription();
  return applySubscription(store, sub, { source });
}

/** True when the cached plan is older than the refresh interval. */
export const planStale = (store, now = Date.now()) => !store?.plan_checked_at || now - Date.parse(store.plan_checked_at) >= REFRESH_MS;
