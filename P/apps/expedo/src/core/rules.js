import { fold } from './address.js';

// Rules decide, per order, which courier/service to use and what to skip.
// A rule: { id, name, enabled, conditions: [{ field, op, value }], actions: {...} }
// All conditions must match. Rules are evaluated in order; every matching rule's actions
// are merged, earlier rules winning (so put specific rules first).

// Labels are in the catalogs: rules.fields.<field>, rules.values.<field>.<value>, rules.ops.<op>,
// rules.actions.<action> (the server sends them translated in /api/meta).
export const RULE_FIELDS = {
  shippingMethod: { type: 'text' },
  paymentMethod: { type: 'select', options: ['cod', 'card', 'transfer', 'other'] },
  total: { type: 'number' },
  weightKg: { type: 'number' },
  county: { type: 'text' },
  city: { type: 'text' },
  tags: { type: 'text' },
  sku: { type: 'text' },
  itemCount: { type: 'number' },
  isCompany: { type: 'select', options: ['true', 'false'] },
  refusedBefore: { type: 'number' },
};

export const RULE_OPS = Object.fromEntries(['contains', 'not_contains', 'equals', 'not_equals', 'gt', 'lt'].map((k) => [k, `rules.ops.${k}`]));

export const RULE_ACTIONS = Object.fromEntries(['courier', 'service', 'parcels', 'weightKg', 'openPackage', 'skipInvoice', 'hold', 'notes'].map((k) => [k, `rules.actions.${k}`]));

/** Values a rule can test, computed from the normalized order (+ the customer's history, core/customers.js). */
export function ruleFacts(order, normalizedAddress, history) {
  return {
    shippingMethod: order.shippingMethod || '',
    paymentMethod: order.paymentMethod,
    total: order.total,
    weightKg: (order.weightGrams || 0) / 1000,
    county: normalizedAddress?.county || order.shippingAddress?.province || '',
    city: normalizedAddress?.city || order.shippingAddress?.city || '',
    tags: (order.tags || []).join(', '),
    sku: order.lines.map((l) => l.sku).join(', '),
    itemCount: order.lines.reduce((s, l) => s + l.quantity, 0),
    isCompany: String(!!order.company),
    refusedBefore: history?.returned ?? 0,
  };
}

function test(fact, op, value) {
  if (op === 'gt' || op === 'lt') {
    const a = Number(fact), b = Number(value);
    if (Number.isNaN(a) || Number.isNaN(b)) return false;
    return op === 'gt' ? a > b : a < b;
  }
  const a = fold(fact);
  // "a, b, c" in the value = any of them.
  const options = String(value ?? '').split(',').map(fold).filter(Boolean);
  if (!options.length) return op === 'not_contains' || op === 'not_equals';
  switch (op) {
    case 'contains': return options.some((v) => a.includes(v));
    case 'not_contains': return options.every((v) => !a.includes(v));
    case 'equals': return options.some((v) => a === v);
    case 'not_equals': return options.every((v) => a !== v);
    default: return false;
  }
}

export function evaluateRules(rules = [], facts) {
  const actions = {};
  const matched = [];
  for (const rule of rules) {
    if (rule.enabled === false) continue;
    const conds = rule.conditions || [];
    if (conds.every((c) => test(facts[c.field], c.op, c.value))) {
      matched.push(rule.name || rule.id);
      for (const [k, v] of Object.entries(rule.actions || {})) {
        if (v !== '' && v != null && !(k in actions)) actions[k] = v;
      }
    }
  }
  return { actions, matched };
}
