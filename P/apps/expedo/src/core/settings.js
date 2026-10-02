import { ProcessingError } from './errors.js';
import { RULE_FIELDS, RULE_OPS, RULE_ACTIONS } from './rules.js';

// Per-store settings with defaults. Stored as JSON on the store row; anything missing
// falls back to DEFAULTS so older stores keep working after new options are added.

export const DEFAULTS = {
  // 'test' = all couriers & invoicing replaced by the test providers (nothing real is created).
  mode: 'test',
  courier: {
    default: '',               // provider id; '' = not configured yet
    labelFormat: 'A6',
  },
  invoicing: {
    provider: '',              // '' = no invoicing
    when: 'on_awb',            // on_awb | manual
    includeShipping: true,
    defaultVatRate: 21,        // used when Shopify sends no tax lines
    sendEmail: false,
  },
  automation: {
    autoProcess: false,        // generate AWB (+ invoice) automatically for new orders
    delayMinutes: 15,          // wait so customers can still cancel / edit
    skipTags: ['manual', 'nu-procesa'],
  },
  fulfillment: {
    fulfillInShopify: true,
    notifyCustomer: true,
    tags: ['expedo-awb'],
    markCodPaidOnDelivery: true,
    registerCodPayment: true,  // încasare in invoicing when the courier confirms delivery
  },
  packaging: {
    defaultWeightKg: 1,
    minWeightKg: 0.5,
    contents: 'Produse',
    openPackage: false,
    parcels: 1,
  },
  rules: [],
};

export function withDefaults(settings = {}) {
  const out = structuredClone(DEFAULTS);
  for (const [k, v] of Object.entries(settings || {})) {
    if (!Object.hasOwn(DEFAULTS, k)) continue;
    if (v && typeof v === 'object' && !Array.isArray(v) && out[k] && typeof out[k] === 'object' && !Array.isArray(out[k])) {
      out[k] = { ...out[k], ...v };
    } else if (v !== undefined) {
      out[k] = v;
    }
  }
  return out;
}

const ENUMS = { mode: ['test', 'live'], 'invoicing.when': ['on_awb', 'manual'], 'courier.labelFormat': ['A4', 'A6'] };
const NUMBER_RANGES = {
  'invoicing.defaultVatRate': [0, 100], 'automation.delayMinutes': [0, 7 * 24 * 60],
  'packaging.defaultWeightKg': [0, 1000], 'packaging.minWeightKg': [0, 1000], 'packaging.parcels': [1, 99],
};

const invalid = (what) => new ProcessingError({ code: 'SETTINGS_INVALID', message: `Setare greșită: ${what}.`, hint: 'Corectează valoarea și salvează din nou.' });

/** Coerces one value to the type of its default (forms send strings, JSON sends anything). */
function coerce(path, value, def) {
  if (ENUMS[path]) {
    if (!ENUMS[path].includes(value)) throw invalid(path);
    return value;
  }
  if (typeof def === 'boolean') {
    if (typeof value === 'boolean') return value;
    if (value === 'true' || value === 'false') return value === 'true';
    throw invalid(path);
  }
  if (typeof def === 'number') {
    const n = value === '' || value == null ? NaN : Number(value);
    const [min, max] = NUMBER_RANGES[path] || [0, Number.MAX_SAFE_INTEGER];
    if (!Number.isFinite(n) || n < min || n > max) throw invalid(path);
    return n;
  }
  if (Array.isArray(def)) {
    const arr = Array.isArray(value) ? value : String(value ?? '').split(',');
    return arr.map((x) => String(x ?? '').trim()).filter(Boolean).slice(0, 100);
  }
  return String(value ?? '').slice(0, 500);
}

function cleanRules(rules) {
  if (!Array.isArray(rules)) throw invalid('rules');
  return rules.slice(0, 200).map((r, i) => {
    if (!r || typeof r !== 'object') throw invalid(`rules[${i}]`);
    const conditions = (Array.isArray(r.conditions) ? r.conditions : [])
      .filter((c) => c && Object.hasOwn(RULE_FIELDS, c.field) && Object.hasOwn(RULE_OPS, c.op))
      .map((c) => ({ field: c.field, op: c.op, value: String(c.value ?? '').slice(0, 500) }));
    const actions = {};
    for (const [k, v] of Object.entries(r.actions && typeof r.actions === 'object' ? r.actions : {})) {
      if (!Object.hasOwn(RULE_ACTIONS, k) || v === '' || v == null) continue;
      if (['openPackage', 'skipInvoice', 'hold'].includes(k)) actions[k] = v === true || v === 'true';
      else if (['parcels', 'weightKg'].includes(k)) {
        const n = Number(v);
        if (!Number.isFinite(n) || n <= 0 || (k === 'parcels' && !Number.isInteger(n))) throw invalid(`regula „${r.name || i + 1}”: ${RULE_ACTIONS[k]}`);
        actions[k] = n;
      } else actions[k] = String(v).slice(0, 500);
    }
    return { id: String(r.id || `r${i + 1}`).slice(0, 64), name: String(r.name ?? '').slice(0, 200), enabled: r.enabled !== false, conditions, actions };
  });
}

/**
 * Validates settings sent by the client: unknown keys are dropped, values coerced to the type of
 * their default (a checkbox never saves "on", an empty number field never saves 0% VAT by accident).
 * Returns only what was sent; merge with mergeSettings().
 */
export function sanitizeSettings(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw invalid('settings');
  const out = {};
  for (const [section, def] of Object.entries(DEFAULTS)) {
    if (!Object.hasOwn(input, section)) continue;
    const value = input[section];
    if (section === 'rules') out.rules = cleanRules(value);
    else if (def && typeof def === 'object' && !Array.isArray(def)) {
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid(section);
      out[section] = {};
      for (const [k, d] of Object.entries(def)) if (Object.hasOwn(value, k)) out[section][k] = coerce(`${section}.${k}`, value[k], d);
    } else out[section] = coerce(section, value, def);
  }
  return out;
}

/** Saved settings + a sanitized patch; sections are merged key by key. */
export function mergeSettings(current = {}, patch = {}) {
  const next = { ...current };
  for (const [k, v] of Object.entries(patch)) {
    next[k] = v && typeof v === 'object' && !Array.isArray(v) ? { ...(current[k] && typeof current[k] === 'object' ? current[k] : {}), ...v } : v;
  }
  return next;
}
