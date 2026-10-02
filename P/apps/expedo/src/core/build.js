import { validateAddress } from './address.js';
import { evaluateRules, ruleFacts } from './rules.js';

// Turns a normalized Shopify order (+ manual overrides + rules + settings) into:
//   plan     — which courier/service, parcels, weight, cod...
//   shipment — the courier-agnostic payload (couriers/contract.js)
//   invoice  — the invoicing payload (invoicing/contract.js)

const round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;

const COURIERS_NEEDING_ZIP = new Set(['gls', 'dpd']);

export function bucharestDate(d = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Bucharest', year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
}

/** UTC ISO instant of 00:00 Europe/Bucharest on the Bucharest day of `d` (DST-aware). */
export function bucharestDayStart(d = new Date()) {
  const [y, m, day] = bucharestDate(d).split('-').map(Number);
  const wanted = Date.UTC(y, m - 1, day);
  const wall = (t) => {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Bucharest', hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric' })
      .formatToParts(new Date(t)).map((x) => [x.type, Number(x.value)]));
    return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
  };
  let t = wanted;
  for (let i = 0; i < 3; i++) t -= wall(t) - wanted;
  return new Date(t).toISOString();
}

/** Effective shipping address: Shopify address with the merchant's manual fixes on top. */
export function effectiveAddress(order, overrides = {}) {
  return { ...(order.shippingAddress || order.billingAddress || {}), ...(overrides.address || {}) };
}

export function planOrder(order, settings, overrides = {}) {
  const rawAddress = effectiveAddress(order, overrides);
  const first = validateAddress(rawAddress);
  const { actions, matched } = evaluateRules(settings.rules, ruleFacts(order, first.address));

  const courier = overrides.courier || actions.courier || settings.courier.default || '';
  const { address, issues } = validateAddress(rawAddress, { requireZip: COURIERS_NEEDING_ZIP.has(courier) });

  if (!courier) {
    issues.push({ level: 'error', code: 'NO_COURIER', field: 'courier', message: 'Nu e ales niciun curier.', hint: 'Alege curierul implicit în Setări → Curieri sau adaugă o regulă.' });
  }
  if (order.cancelledAt) {
    issues.push({ level: 'error', code: 'ORDER_CANCELLED', message: 'Comanda e anulată în Shopify.', hint: 'Nu se mai expediază.' });
  }
  if (!order.lines.some((l) => l.requiresShipping && !l.isGiftCard)) {
    issues.push({ level: 'error', code: 'NOTHING_TO_SHIP', message: 'Comanda nu are produse fizice de expediat.', hint: 'Doar carduri cadou / produse digitale.' });
  }
  // What the courier collects: never more than Shopify says is still owed. (The mapper falls back to the
  // full total when nothing is outstanding, which would make a paid or refunded order pay again.)
  const owed = order.paymentMethod === 'cod' && typeof order.outstanding === 'number'
    ? round2(Math.max(0, Math.min(order.codAmount || 0, order.outstanding)))
    : order.codAmount || 0;
  if (order.paymentMethod === 'cod' && owed <= 0 && overrides.cod == null) {
    issues.push({ level: 'warning', code: 'COD_ZERO', message: 'Plata e ramburs, dar suma de încasat e 0.', hint: 'Verifică dacă a fost deja plătită.' });
  }

  const p = settings.packaging;
  const shopifyKg = (order.weightGrams || 0) / 1000;
  const weightKg = round2(Math.max(Number(overrides.weightKg || actions.weightKg || shopifyKg || p.defaultWeightKg), Number(p.minWeightKg) || 0.1));

  return {
    courier,
    service: overrides.service || actions.service || '',
    parcels: Number(overrides.parcels || actions.parcels || p.parcels || 1),
    weightKg,
    cod: overrides.cod != null ? Number(overrides.cod) : owed,
    openPackage: overrides.openPackage ?? actions.openPackage ?? p.openPackage,
    notes: overrides.notes ?? actions.notes ?? '',
    lockerId: overrides.lockerId || detectLocker(order),
    skipInvoice: !!(overrides.skipInvoice ?? actions.skipInvoice),
    hold: !!actions.hold,
    matchedRules: matched,
    address,
    issues,
    blocking: issues.some((i) => i.level === 'error'),
  };
}

/** Locker / pickup point id saved by a checkout locker-picker app in order attributes. */
function detectLocker(order) {
  const a = (order.attributes || []).find((x) => /locker|easybox|fanbox|pudo|ship ?& ?go|parcel ?shop|punct ridicare/i.test(x.key));
  return a?.value?.match(/[A-Za-z0-9-]+/)?.[0] || '';
}

export function buildShipment(order, plan, settings) {
  const a = plan.address;
  return {
    reference: order.name,
    recipient: {
      name: a.company || a.name,
      contactPerson: a.name,
      phone: a.phone,
      email: order.email || undefined,
      county: a.county,
      countyCode: a.countyCode,
      city: a.city,
      sector: a.sector || undefined,
      street: a.street,
      zip: a.zip || undefined,
      country: a.country,
      company: a.company || undefined,
    },
    parcels: plan.parcels,
    weightKg: plan.weightKg,
    envelopes: 0,
    cod: round2(plan.cod),
    currency: order.currency,
    declaredValue: 0,
    contents: settings.packaging.contents || 'Produse',
    notes: plan.notes || undefined,
    service: plan.service || undefined,
    lockerId: plan.lockerId || undefined,
    openPackage: !!plan.openPackage,
  };
}

export function buildInvoice(order, plan, settings) {
  const inv = settings.invoicing;
  const billing = order.billingAddress || order.shippingAddress || {};
  const billingCheck = validateAddress(billing);
  const ba = billingCheck.address.city ? billingCheck.address : plan.address;
  const vat = (r) => (r == null ? Number(inv.defaultVatRate) : r);

  const lines = order.lines
    .filter((l) => !l.isGiftCard)
    .map((l) => ({
      name: l.variantTitle ? `${l.title} - ${l.variantTitle}` : l.title,
      code: l.sku || undefined,
      quantity: l.quantity,
      unitPrice: l.unitPrice,
      vatRate: vat(l.vatRate),
      unit: 'buc',
    }));
  if (inv.includeShipping) {
    for (const s of order.shippingLines) {
      if (s.price > 0) lines.push({ name: `Transport${s.title ? ` (${s.title})` : ''}`, quantity: 1, unitPrice: s.price, vatRate: vat(s.vatRate), unit: 'buc', isShipping: true });
    }
  }

  const total = round2(lines.reduce((s, l) => s + l.unitPrice * l.quantity, 0));
  const shippingCharged = (order.shippingLines || []).reduce((s, l) => s + (Number(l.price) || 0), 0);
  const expected = round2((Number(order.total) || 0) - (inv.includeShipping ? 0 : shippingCharged));
  const company = order.company;
  const today = bucharestDate();
  return {
    reference: order.name,
    issueDate: today,
    dueDate: today,
    currency: order.currency,
    language: 'RO',
    client: {
      name: company?.name || ba.name || order.customerName,
      isCompany: !!company,
      vatCode: company?.vatCode,
      regCom: company?.regCom || undefined,
      address: ba.street,
      city: ba.city,
      county: ba.county,
      countyCode: ba.countyCode,
      zip: ba.zip || undefined,
      country: 'Romania',
      email: order.email || undefined,
      phone: ba.phone || undefined,
    },
    lines,
    total,
    paid: order.paymentMethod === 'card' && order.financialStatus === 'PAID',
    paymentMethod: order.paymentMethod,
    mentions: `Comanda ${order.name}`,
    sendEmail: !!inv.sendEmail,
    // Gift-card redemptions, order edits, rounding etc. make the sum differ from what Shopify charged.
    // Without the shipping line on the invoice, compare against the total minus shipping.
    mismatch: Math.abs(total - expected) > 0.05 ? round2(expected - total) : 0,
  };
}
