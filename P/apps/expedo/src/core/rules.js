import { fold } from './address.js';

// Rules decide, per order, which courier/service to use and what to skip.
// A rule: { id, name, enabled, conditions: [{ field, op, value }], actions: {...} }
// All conditions must match. Rules are evaluated in order; every matching rule's actions
// are merged, earlier rules winning (so put specific rules first).

export const RULE_FIELDS = {
  shippingMethod: { label: 'Metoda de livrare', type: 'text' },
  paymentMethod: { label: 'Plata', type: 'select', options: [['cod', 'Ramburs'], ['card', 'Card'], ['transfer', 'Transfer'], ['other', 'Altă']] },
  total: { label: 'Total comandă (lei)', type: 'number' },
  weightKg: { label: 'Greutate (kg)', type: 'number' },
  county: { label: 'Județ', type: 'text' },
  city: { label: 'Localitate', type: 'text' },
  tags: { label: 'Etichete Shopify', type: 'text' },
  sku: { label: 'SKU în comandă', type: 'text' },
  itemCount: { label: 'Număr produse', type: 'number' },
  isCompany: { label: 'Client firmă', type: 'select', options: [['true', 'Da'], ['false', 'Nu']] },
};

export const RULE_OPS = {
  contains: 'conține',
  not_contains: 'nu conține',
  equals: 'este',
  not_equals: 'nu este',
  gt: 'mai mare decât',
  lt: 'mai mic decât',
};

export const RULE_ACTIONS = {
  courier: 'Curier',
  service: 'Serviciu curier',
  parcels: 'Număr colete',
  weightKg: 'Greutate fixă (kg)',
  openPackage: 'Deschidere colet',
  skipInvoice: 'Fără factură',
  hold: 'Pune în așteptare (nu procesa automat)',
  notes: 'Observații pe AWB',
};

/** Values a rule can test, computed from the normalized order. */
export function ruleFacts(order, normalizedAddress) {
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
