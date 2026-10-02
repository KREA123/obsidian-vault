// Shopify Admin GraphQL Order → normalized order used everywhere else in the app.

const money = (set) => Number(set?.shopMoney?.amount ?? 0);
const round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;
const round4 = (n) => Math.round((n + Number.EPSILON) * 10000) / 10000;

const COD_GATEWAYS = /(cash on delivery|\bcod\b|ramburs|plata la livrare|plată la livrare|numerar|cash)/i;
const TRANSFER_GATEWAYS = /(bank|transfer|ordin de plata|op\b)/i;

export function detectPaymentMethod(gateways = [], financialStatus) {
  const g = gateways.join(' | ');
  if (COD_GATEWAYS.test(g)) return 'cod';
  if (TRANSFER_GATEWAYS.test(g)) return 'transfer';
  // A bare "manual" gateway can be anything (bank transfer, pay at pickup): don't collect it as ramburs.
  if (/manual/i.test(g) && financialStatus !== 'PAID') return 'other';
  if (gateways.length) return 'card';
  return financialStatus === 'PAID' ? 'card' : 'other';
}

const attr = (attrs, ...names) => {
  const wanted = names.map((n) => n.toLowerCase());
  return attrs.find((a) => wanted.some((w) => a.key.toLowerCase().replace(/[._:-]/g, ' ').replace(/\s+/g, ' ').trim() === w))?.value?.trim() || '';
};

/** Detects B2B details: billing company + CUI from checkout attributes or the company field ("SC X SRL, RO123"). */
export function detectCompany(billing, attributes = []) {
  let vatCode = attr(attributes, 'cui', 'cif', 'cod fiscal', 'cod unic', 'vat', 'vat number', 'tax id', 'company vat');
  let regCom = attr(attributes, 'nr reg com', 'reg com', 'registrul comertului', 'nr registrul comertului', 'j');
  let name = attr(attributes, 'denumire firma', 'firma', 'company', 'nume firma') || billing?.company?.trim() || '';
  if (!vatCode && name) {
    const m = name.match(/\b(RO\s?)?(\d{2,10})\b/i);
    if (m && /srl|sa\b|pfa|ii\b|if\b|ong|asocia|cui|cif|\bro\s?\d/i.test(name)) {
      vatCode = (m[1] ? 'RO' : '') + m[2];
      name = name.replace(m[0], '').replace(/[,;\s-]+$/, '').trim();
    }
  }
  if (!name || !vatCode) return null;
  vatCode = vatCode.replace(/\s+/g, '').toUpperCase();
  return { name, vatCode, regCom };
}

export function mapOrder(o) {
  const attributes = o.customAttributes || [];
  const ship = o.shippingAddress || o.billingAddress || {};
  const lineVat = (tl) => (tl?.length ? round2(tl.reduce((s, t) => s + Number(t.rate || 0), 0) * 100) : null);
  // Stores whose prices exclude VAT: Shopify adds the tax on top. Everything downstream (ramburs,
  // invoices) works with what the customer pays, so add the line's tax back into the price.
  const addedTax = (tl) => (o.taxesIncluded === false ? (tl || []).reduce((s, t) => s + money(t.priceSet), 0) : 0);

  const lines = (o.lineItems?.nodes || [])
    .filter((li) => (li.currentQuantity ?? li.quantity) > 0)
    .map((li) => {
      const qty = li.currentQuantity ?? li.quantity;
      const unit = money(li.originalUnitPriceSet);
      const discount = (li.discountAllocations || []).reduce((s, d) => s + money(d.allocatedAmountSet), 0);
      // Discount allocations are for the original quantity; scale when items were removed.
      const scaledDiscount = li.quantity ? discount * (qty / li.quantity) : 0;
      return {
        id: li.id,
        title: li.title,
        variantTitle: li.variantTitle && li.variantTitle !== 'Default Title' ? li.variantTitle : '',
        sku: li.sku || '',
        quantity: qty,
        originalUnitPrice: unit,
        unitPrice: round4((unit * qty - scaledDiscount + addedTax(li.taxLines) * (li.quantity ? qty / li.quantity : 1)) / qty),
        vatRate: lineVat(li.taxLines),
        requiresShipping: li.requiresShipping !== false,
        isGiftCard: !!li.isGiftCard,
      };
    });

  const shippingLines = (o.shippingLines?.nodes || []).map((s) => ({
    title: s.title,
    code: s.code || '',
    source: s.source || '',
    price: round2(money(s.discountedPriceSet ?? s.originalPriceSet) + addedTax(s.taxLines)),
    vatRate: lineVat(s.taxLines),
  }));

  const financialStatus = o.displayFinancialStatus || '';
  const paymentMethod = detectPaymentMethod(o.paymentGatewayNames || [], financialStatus);
  const total = money(o.currentTotalPriceSet ?? o.totalPriceSet);
  const outstanding = money(o.totalOutstandingSet);

  return {
    shopifyId: o.id,
    name: o.name,
    createdAt: o.createdAt,
    cancelledAt: o.cancelledAt || null,
    closed: !!o.closed,
    test: !!o.test,
    currency: o.currencyCode || 'RON',
    taxesIncluded: o.taxesIncluded !== false,
    financialStatus,
    fulfillmentStatus: o.displayFulfillmentStatus || '',
    gateways: o.paymentGatewayNames || [],
    paymentMethod,
    total,
    // "current" amounts reflect order edits and refunds; the plain ones are what was first charged.
    subtotal: money(o.currentSubtotalPriceSet ?? o.subtotalPriceSet),
    shippingTotal: money(o.currentShippingPriceSet ?? o.totalShippingPriceSet),
    discountTotal: money(o.currentTotalDiscountsSet ?? o.totalDiscountsSet),
    outstanding,
    // Ramburs = what the customer still owes. Card orders: 0.
    codAmount: paymentMethod === 'cod' ? round2(o.totalOutstandingSet ? outstanding : total) : 0,
    email: o.email || '',
    phone: o.phone || ship.phone || o.billingAddress?.phone || '',
    customerName: [ship.firstName, ship.lastName].filter(Boolean).join(' ') || ship.name || '',
    shippingAddress: mapAddress(o.shippingAddress, o.phone),
    billingAddress: mapAddress(o.billingAddress, o.phone),
    company: detectCompany(o.billingAddress, attributes),
    lines,
    shippingLines,
    shippingMethod: shippingLines.map((s) => s.title).join(', '),
    tags: o.tags || [],
    note: o.note || '',
    attributes,
    weightGrams: Number(o.totalWeight || 0),
    fulfillmentOrders: (o.fulfillmentOrders?.nodes || []).map((f) => ({ id: f.id, status: f.status, location: f.assignedLocation?.name || '' })),
  };
}

function mapAddress(a, fallbackPhone) {
  if (!a) return null;
  return {
    firstName: a.firstName || '',
    lastName: a.lastName || '',
    name: a.name || [a.firstName, a.lastName].filter(Boolean).join(' '),
    company: a.company || '',
    address1: a.address1 || '',
    address2: a.address2 || '',
    city: a.city || '',
    province: a.province || '',
    provinceCode: a.provinceCode || '',
    zip: a.zip || '',
    countryCode: a.countryCodeV2 || 'RO',
    phone: a.phone || fallbackPhone || '',
  };
}
