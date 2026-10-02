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
    if (v && typeof v === 'object' && !Array.isArray(v) && out[k] && typeof out[k] === 'object' && !Array.isArray(out[k])) {
      out[k] = { ...out[k], ...v };
    } else if (v !== undefined) {
      out[k] = v;
    }
  }
  return out;
}
