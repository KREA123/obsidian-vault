import { ProcessingError, authError, errorMessage } from '../core/errors.js';
import { m } from '../i18n/index.js';
import { bucharestDay } from './ro-time.js';

// SmartBill Cloud API V1 — https://api.smartbill.ro/ (OpenAPI spec: https://api.smartbill.ro/smartbill-api-spec.yaml,
// last updated 2026-09). Basic auth "email:token", company CIF in body (companyVatCode) or query (cif).
//
// Things the spec spells out that are easy to get wrong:
//  - Invoices are created with POST /invoice/v2 (the /invoice path only has DELETE now).
//  - V1 rejects unknown fields with HTTP 400 {type:'invalid_request_error', errors:[{param}]} — no errorText.
//    So we only send field names that exist in the schema.
//  - errorText is the source of truth: HTTP 200 + non-empty errorText is a failure. It may contain HTML.
//  - Prices are WITHOUT VAT unless isTaxIncluded:true — we always send gross prices + isTaxIncluded:true.
//  - taxName must match a VAT rate configured in the account (GET /tax), so we map percentage → name from /tax.
//  - GET /invoice/pdf: do NOT send Accept: application/pdf (406). Missing invoice → 502 with HTML body.
//  - No idempotency key exists in V1: a timed-out create may still have issued the invoice. We read the series'
//    nextNumber before creating; after an ambiguous failure (timeout, 5xx, dropped connection) an unchanged
//    nextNumber proves nothing was issued (safe to retry), otherwise the merchant must check before retrying.
//
// Live-checked 2026-10-02 against ws.smartbill.ro with invalid credentials (test/fixtures/invoicing/live-responses.json):
//  - Bad e-mail/token (or no Authorization header) → HTTP 401 JSON {successfully:false, errorText:"Autentificare
//    esuata. Va rugam verificati datele si incercati din nou.", ...} on every V1 path (GET /tax, GET /series,
//    POST /invoice/v2, GET /invoice/pdf, PUT /invoice/cancel, POST /invoice/reverse, POST /payment, DELETE /invoice).
//  - Request-shape errors are checked BEFORE auth and have no errorText: {status, type:'invalid_request_error',
//    errors:[{code, message, param?}]} — 400 json_mapping_error (param set), 404 resource_not_found,
//    405 method_not_allowed, 406 invalid_accept_header (Accept: application/pdf on /invoice/pdf), 415 invalid_content_type.
//  - A malformed Basic header gives HTTP 500 with an HTML Tomcat page (we always send valid base64).

const PROVIDER = 'SmartBill';
const BASE = 'https://ws.smartbill.ro/SBORO/api';
const TAX_TTL = 6 * 60 * 60; // seconds

// ───────────────────────────── helpers ─────────────────────────────

const clean = (s) => String(s ?? '').replace(/[\u200B-\u200D\uFEFF]/g, '').trim();
const noSpaces = (s) => clean(s).replace(/\s+/g, '');
const fold = (s) => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036F]/g, '');
const round = (n, d = 2) => Math.round((Number(n) + Number.EPSILON) * 10 ** d) / 10 ** d;
const decimals = (n) => {
  const s = String(Number(n));
  return s.includes('.') ? s.split('.')[1].length : 0;
};

function cif(ctx) {
  const v = noSpaces(ctx.settings?.cif).toUpperCase();
  if (!v) {
    throw new ProcessingError({ code: 'INVOICING_SETTINGS_MISSING', key: 'smartbill.errors.cifMissing', provider: PROVIDER });
  }
  return v;
}

function authHeader(ctx) {
  const email = clean(ctx.credentials?.email);
  const token = noSpaces(ctx.credentials?.token);
  if (!email || !token) throw authError(PROVIDER, 'missing email/token');
  return 'Basic ' + Buffer.from(`${email}:${token}`, 'utf8').toString('base64');
}

const vatPayer = (ctx) => ctx.settings?.vatPayer !== false;

/** București needs "Sector N" as city for e-Factura (SPV). Derive it from the city text or the postal code. */
function bucharestSector(client) {
  const m = fold(client.city).match(/sector(?:ul)?\s*([1-6])\b/i) || fold(client.address).match(/sector(?:ul)?\s*([1-6])\b/i);
  if (m) return Number(m[1]);
  const z = String(client.zip ?? '').trim().match(/^0([1-6])\d{4}$/);
  return z ? Number(z[1]) : null;
}
const isBucharest = (c) => c.countyCode === 'B' || /^(municipiul\s+)?bucuresti$/i.test(fold(c.county).trim());

// ───────────────────────────── errors ─────────────────────────────

/** First sentence of an errorText, stripped of the HTML SmartBill sometimes adds for its own UI. */
function plainError(text) {
  const t = String(text ?? '');
  const cut = t.indexOf('<');
  return (cut >= 0 ? t.slice(0, cut) : t).replace(/\s+/g, ' ').trim();
}

// SmartBill's own errorText → [code, field]. The text stays SmartBill's, verbatim ("SmartBill: …" /
// "SmartBill says: “…”"), with our hint: smartbill.errors.<code> in the catalogs.
const RULES = [
  [/autentificare esuata/i, 'AUTH_FAILED'],
  [/firma la care incercati sa va conectati/i, 'INVOICING_COMPANY_NOT_FOUND'],
  [/seria nu a fost gasita/i, 'INVOICE_SERIES_NOT_FOUND', 'settings.series'],
  [/cota (tva )?.*nu a fost gasita|trebuie sa setezi o cota tva|cota default nu a fost gasita|nu are cota tva setata/i, 'VAT_RATE_NOT_DEFINED'],
  [/nu are codul specificat/i, 'PRODUCT_CODE_MISSING', 'lines.code'],
  [/nu aveti dreptul/i, 'INVOICING_PERMISSION_DENIED'],
  [/numarul maxim de documente/i, 'INVOICING_PLAN_LIMIT'],
  [/stoc|gestiunea|achizitie pentru produsul|factor de conversie|modulul stoc/i, 'INVOICE_STOCK_ERROR'],
  [/server-ul de email|adresa de email a clientului/i, 'INVOICE_EMAIL_NOT_CONFIGURED'],
  [/client invalid|tara trebuie specificata|clientul exista deja/i, 'INVOICE_CLIENT_INVALID', 'client.name'],
  [/moneda nu a fost gasita/i, 'INVOICE_CURRENCY_INVALID'],
  [/deja stornata/i, 'INVOICE_ALREADY_REVERSED'],
  [/incasata sau stornata in totalitate/i, 'INVOICE_ALREADY_PAID'],
  [/nu este ultimul din serie/i, 'INVOICE_NOT_LAST'],
  [/anulata/i, 'INVOICE_CANCELLED'],
  [/nu a fost gasita/i, 'INVOICE_NOT_FOUND'],
];

function mapErrorText(errorText, details, { status } = {}) {
  const msg = plainError(errorText);
  for (const [re, code, field] of RULES) {
    if (re.test(fold(msg))) {
      if (code === 'AUTH_FAILED') return authError(PROVIDER, details);
      return new ProcessingError({ code, key: `smartbill.errors.${code}`, params: { text: msg }, field, retryable: false, provider: PROVIDER, details });
    }
  }
  const retryable = status === 429 || status >= 500;
  return new ProcessingError({
    code: retryable ? 'PROVIDER_DOWN' : 'PROVIDER_REJECTED',
    key: retryable ? 'smartbill.errors.rejectedRetry' : 'smartbill.errors.rejected',
    params: { text: msg },
    retryable,
    provider: PROVIDER,
    details,
  });
}

/** mapError hook for ctx.http (non-2xx responses). Returns undefined to fall back to the generic mapping. */
function mapHttpError(status, body) {
  if (body && typeof body === 'object' && !Buffer.isBuffer(body)) {
    if (body.errorText) return mapErrorText(body.errorText, body, { status });
    if (body.type === 'invalid_request_error' && Array.isArray(body.errors)) {
      // A field name/type we sent is wrong — our bug, not the merchant's.
      // Only json_mapping_error names a field (param); 404/405/406/415 carry just code + message.
      const params = body.errors.map((e) => e.param).filter(Boolean).join(', ');
      const codes = body.errors.map((e) => e.code).filter(Boolean).join(', ');
      return new ProcessingError({
        code: 'PROVIDER_REJECTED',
        key: params ? 'smartbill.errors.structureField' : codes ? 'smartbill.errors.structureCodes' : 'smartbill.errors.structure',
        params: { params, codes, status },
        provider: PROVIDER,
        details: body,
      });
    }
  }
  if (status === 401 || status === 403) return authError(PROVIDER, body);
  return undefined;
}

async function call(ctx, method, path, { query, json, responseType, headers } = {}) {
  const url = new URL(BASE + path);
  for (const [k, v] of Object.entries(query || {})) if (v != null) url.searchParams.set(k, String(v));
  const res = await ctx.http(PROVIDER, url.toString(), {
    method,
    json,
    responseType,
    headers: { Authorization: authHeader(ctx), ...(headers || {}) },
    mapError: mapHttpError,
  });
  const body = res.body;
  if (body && typeof body === 'object' && !Buffer.isBuffer(body) && body.errorText) {
    throw mapErrorText(body.errorText, body, { status: res.status });
  }
  return body;
}

// ───────────────────────────── VAT ─────────────────────────────

/** VAT rates configured in the SmartBill account: [{ name, percentage }]. Empty list for non-VAT payers. */
async function taxes(ctx) {
  // Per account AND company: two SmartBill accounts (or a changed token owner) must not share a cached list.
  const key = `smartbill:tax:${clean(ctx.credentials?.email).toLowerCase()}:${cif(ctx)}`;
  const cached = ctx.cache?.get(key);
  if (cached) return cached;
  let list;
  try {
    const body = await call(ctx, 'GET', '/tax', { query: { cif: cif(ctx) } });
    list = Array.isArray(body?.taxes) ? body.taxes : [];
  } catch (err) {
    // SmartBill answers "Firma este neplatitoare de tva." for companies without VAT.
    if (/neplatitoare de tva/i.test(fold(err?.details?.errorText || err?.message))) list = [];
    else throw err;
  }
  ctx.cache?.set(key, list, TAX_TTL);
  return list;
}

/** Order in which 0% rates are picked: exempt (SDD/SFDD) before anything else, reverse charge last. */
const zeroRank = (name) => (/^s?f?dd$/i.test(fold(name).replace(/\s+/g, '')) ? 0 : /taxare\s*inversa/i.test(fold(name)) ? 2 : 1);

async function taxFor(ctx, rate) {
  const list = await taxes(ctx);
  const matches = list.filter((t) => Number(t.percentage) === Number(rate));
  // Several rates can share 0% ("Taxare inversa", "SDD", "SFDD", "TVA Inclus" — spec example /tax lists "Taxare
  // inversa" 0). Reverse charge on a shop sale is wrong, so it is only used when it's the account's only 0% rate.
  if (Number(rate) === 0) matches.sort((a, b) => zeroRank(a.name) - zeroRank(b.name));
  const hit = matches[0];
  if (hit) return { taxName: hit.name, taxPercentage: Number(rate) };
  throw new ProcessingError({
    code: 'VAT_RATE_NOT_DEFINED',
    key: 'smartbill.errors.vatRate',
    params: { rate },
    provider: PROVIDER,
    details: { configured: list },
  });
}

// ───────────────────────────── payload ─────────────────────────────

function clientPayload(c) {
  const isCompany = Boolean(c.isCompany && c.vatCode);
  let city = clean(c.city);
  let county = clean(c.county);
  if (isBucharest(c)) {
    // The spec: when county is "Bucuresti", city must be "Sector 1".."Sector 6" or e-Factura fails in SPV.
    county = 'Bucuresti';
    const s = bucharestSector(c);
    if (s) city = `Sector ${s}`;
  }
  const out = {
    name: clean(c.name),
    // Natural persons: 13 zeros is the CNP placeholder e-Factura accepts; the official SmartBill
    // WooCommerce plugin sends exactly this when no valid CNP is known.
    vatCode: isCompany ? noSpaces(c.vatCode).toUpperCase() : '0000000000000',
    isTaxPayer: isCompany ? /^RO/i.test(noSpaces(c.vatCode)) : false,
    address: clean(c.address),
    city,
    county,
    country: clean(c.country) || 'Romania',
    saveToDb: false,
  };
  if (isCompany && c.regCom) out.regCom = clean(c.regCom);
  if (c.email) out.email = clean(c.email);
  if (c.phone) out.phone = clean(c.phone);
  return out;
}

const PAID_TYPE = { card: 'Card online', transfer: 'Ordin plata', other: 'Alta incasare' };
// InvoiceRequest.currency enum from the spec; anything else is a 400 json_mapping_error with no useful text.
const CURRENCIES = new Set(['RON', 'EUR', 'USD', 'GBP', 'CAD', 'AUD', 'CHF', 'TRY', 'CZK', 'DKK', 'HUF', 'MDL', 'SEK', 'NOK', 'JPY',
  'EGP', 'PLN', 'RUB', 'AED', 'BRL', 'CNY', 'HRK', 'INR', 'KRW', 'MXN', 'NZD', 'RSD', 'THB', 'UAH', 'XDR', 'ZAR']);

/** What the invoice will total: each line rounded to 2 decimals, then summed (how invoicing software totals). */
const invoiceTotal = (lines) => round(lines.reduce((s, l) => s + round(Number(l.quantity) * Number(l.unitPrice), 2), 0), 2);

async function invoicePayload(ctx, invoice) {
  const s = ctx.settings || {};
  const currency = clean(invoice.currency || 'RON').toUpperCase();
  if (!CURRENCIES.has(currency)) {
    throw new ProcessingError({ code: 'INVOICE_CURRENCY_INVALID', key: 'smartbill.errors.currency', params: { currency }, provider: PROVIDER });
  }
  const useStock = Boolean(s.useStock && clean(s.warehouseName));
  const prec = Math.min(4, Math.max(2, ...invoice.lines.map((l) => decimals(l.unitPrice))));
  const products = [];
  for (const l of invoice.lines) {
    const negative = Number(l.unitPrice) < 0; // price must be >= 0; a negative line goes as negative quantity
    const p = {
      name: clean(l.name),
      measuringUnitName: l.unit || 'buc',
      currency,
      quantity: negative ? -Math.abs(Number(l.quantity)) : Number(l.quantity),
      price: Math.abs(Number(l.unitPrice)),
      isTaxIncluded: true,
      isService: Boolean(l.isShipping),
      isDiscount: false,
      saveToDb: false,
    };
    if (l.code) p.code = clean(l.code);
    // Non-VAT-payer issuer: NO tax fields at all. Spec (api.smartbill.ro, "14. Emitere factura - emitent neplatitor de
    // TVA"): "nu este necesar sa completezi campurile legate de TVA pe produse"; the official WooCommerce plugin
    // (smartbill-facturare-si-gestiune 3.4.10, includes/class-smartbillutils.php) sets taxName/taxPercentage only when
    // isTaxPayer. Sending taxPercentage 0 without a name would be worse: "La cota 0% ... fara [taxName], API-ul alege
    // implicit Taxare inversa" (spec, example 15) — reverse charge on a non-payer's invoice.
    if (vatPayer(ctx)) Object.assign(p, await taxFor(ctx, l.vatRate));
    if (useStock && !l.isShipping) p.warehouseName = clean(s.warehouseName);
    products.push(p);
  }

  const body = {
    companyVatCode: cif(ctx),
    client: clientPayload(invoice.client),
    issueDate: invoice.issueDate,
    seriesName: clean(s.series),
    isDraft: false,
    currency,
    language: s.language || invoice.language || 'RO',
    precision: prec,
    products,
  };
  if (invoice.dueDate) body.dueDate = invoice.dueDate;
  if (invoice.mentions) body.mentions = invoice.mentions;
  if (useStock) body.useStock = true;
  const sendEmail = invoice.sendEmail ?? s.sendEmail;
  if (sendEmail && invoice.client.email) {
    body.sendEmail = true;
    body.email = { to: clean(invoice.client.email) };
  }
  if (invoice.paid && s.markPaid !== false) {
    body.payment = {
      // Sum of the rounded line totals = what SmartBill will show as total, so the invoice ends up fully paid
      // (invoice.total can differ by a cent when unit prices carry 4 decimals).
      value: invoiceTotal(invoice.lines),
      type: PAID_TYPE[invoice.paymentMethod] || 'Card online',
      isCash: false,
    };
  }
  return body;
}

async function listSeries(ctx) {
  const body = await call(ctx, 'GET', '/series', { query: { cif: cif(ctx), type: 'f' } });
  return (body?.list || []).filter((x) => !x.type || x.type === 'f').map((x) => ({ id: x.name, name: x.name, nextNumber: x.nextNumber }));
}

/** nextNumber of an invoice series, or undefined when the series isn't listed. */
async function nextNumber(ctx, seriesName) {
  const hit = (await listSeries(ctx)).find((x) => x.name === seriesName);
  return hit?.nextNumber == null ? undefined : Number(hit.nextNumber);
}

// Failures after which the invoice may or may not exist. 4xx/errorText answers and 429 are definite (nothing issued).
const AMBIGUOUS = new Set(['PROVIDER_TIMEOUT', 'PROVIDER_UNREACHABLE', 'PROVIDER_DOWN', 'UNEXPECTED']);

async function resolveAmbiguous(ctx, invoice, seriesName, before, err) {
  let after;
  try { after = await nextNumber(ctx, seriesName); } catch { /* SmartBill still unreachable: stay cautious */ }
  if (before !== undefined && after === before) {
    // The series counter did not move: no invoice was issued, so retrying cannot create a duplicate.
    return new ProcessingError({
      code: err?.code || 'PROVIDER_DOWN',
      key: 'smartbill.errors.notIssued',
      params: { error: err ? errorMessage(err) : m('smartbill.noAnswer'), order: invoice.reference },
      retryable: true,
      provider: PROVIDER,
      details: err?.details,
    });
  }
  const candidate = before !== undefined && after === before + 1 ? m('smartbill.candidate', { series: seriesName, number: before }) : '';
  ctx.log?.(m('log.invoiceUnknown', { provider: 'SmartBill' }), { reference: invoice.reference, before, after, error: err?.message });
  return new ProcessingError({
    code: 'INVOICE_STATUS_UNKNOWN',
    key: 'smartbill.errors.statusUnknown',
    params: { order: invoice.reference, candidate },
    retryable: false,
    provider: PROVIDER,
    details: { error: err?.message, code: err?.code, nextNumberBefore: before, nextNumberAfter: after, providerDetails: err?.details },
  });
}

// ───────────────────────────── adapter ─────────────────────────────

export default {
  id: 'smartbill',
  name: 'SmartBill',

  // Labels and help: smartbill.fields.<key> in the catalogs (src/i18n).
  credentialFields: [
    { key: 'email', type: 'text', required: true },
    { key: 'token', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'cif', type: 'text', required: true },
    { key: 'series', type: 'text', required: true },
    { key: 'vatPayer', type: 'checkbox', default: true },
    { key: 'sendEmail', type: 'checkbox', default: false },
    { key: 'markPaid', type: 'checkbox', default: true },
    { key: 'useStock', type: 'checkbox', default: false },
    { key: 'warehouseName', type: 'text' },
    { key: 'language', type: 'select', default: 'RO', options: ['RO', 'EN', 'DE', 'FR', 'IT', 'ES'].map((v) => ({ value: v, label: v })) },
    // Values are SmartBill's own payment types.
    { key: 'codPaymentType', type: 'select', default: 'Ramburs', options: [{ value: 'Ramburs' }, { value: 'Alta incasare' }] },
  ],

  async testConnection(ctx) {
    const list = await taxes(ctx); // authenticates and validates the CIF
    const series = await listSeries(ctx);
    const wanted = clean(ctx.settings?.series);
    const names = series.map((x) => x.name);
    const vat = list.length
      ? m('smartbill.test.vatRates', { rates: list.map((x) => `${x.name} ${x.percentage}%`).join(', ') })
      : m('smartbill.test.noVat');
    if (wanted && !names.includes(wanted)) {
      throw new ProcessingError({
        code: 'INVOICE_SERIES_NOT_FOUND',
        key: names.length ? 'smartbill.errors.seriesMissing' : 'smartbill.errors.seriesMissingNone',
        params: { series: wanted, list: names.join(', ') },
        provider: PROVIDER,
        field: 'settings.series',
      });
    }
    return {
      ok: true,
      message: wanted
        ? m('smartbill.test.connectedSeries', { series: wanted, vat })
        : m('smartbill.test.connectedList', { list: names.join(', ') || m('smartbill.test.none'), vat }),
      info: { series, taxes: list },
    };
  },

  listSeries,

  async createInvoice(ctx, invoice) {
    if (!clean(ctx.settings?.series)) {
      throw new ProcessingError({
        code: 'INVOICING_SETTINGS_MISSING',
        key: 'smartbill.errors.seriesNotChosen',
        provider: PROVIDER,
        field: 'settings.series',
      });
    }
    const json = await invoicePayload(ctx, invoice);
    // nextNumber before the call: the only way to tell afterwards whether an unanswered create issued an invoice.
    const before = await nextNumber(ctx, json.seriesName);
    let body;
    try {
      body = await call(ctx, 'POST', '/invoice/v2', { json });
    } catch (err) {
      if (!AMBIGUOUS.has(err?.code) && err instanceof ProcessingError) throw err;
      throw await resolveAmbiguous(ctx, invoice, json.seriesName, before, err);
    }
    if (!body?.number) {
      throw new ProcessingError({
        code: 'PROVIDER_REJECTED',
        key: 'smartbill.errors.noNumber',
        provider: PROVIDER,
        details: body,
      });
    }
    return {
      series: body.series || json.seriesName,
      number: String(body.number),
      url: body.documentViewUrl || body.documentUrl || undefined,
      raw: body,
    };
  },

  async getPdf(ctx, { series, number }) {
    const pdf = await ctx.http(PROVIDER, `${BASE}/invoice/pdf?${new URLSearchParams({ cif: cif(ctx), seriesname: series, number })}`, {
      method: 'GET',
      responseType: 'buffer',
      // Accept: application/pdf is rejected with 406 — the spec asks for octet-stream.
      headers: { Authorization: authHeader(ctx), Accept: 'application/octet-stream' },
      mapError: (status, body) => {
        if (status === 502) {
          return new ProcessingError({
            code: 'INVOICE_NOT_FOUND',
            key: 'smartbill.errors.pdfNotFound',
            params: { series, number },
            retryable: true,
            provider: PROVIDER,
          });
        }
        let parsed = body;
        if (Buffer.isBuffer(body)) { try { parsed = JSON.parse(body.toString('utf8')); } catch { parsed = undefined; } }
        return mapHttpError(status, parsed);
      },
    });
    const buf = Buffer.isBuffer(pdf.body) ? pdf.body : Buffer.from(pdf.body ?? '');
    if (buf.subarray(0, 4).toString('latin1') !== '%PDF') {
      let parsed;
      try { parsed = JSON.parse(buf.toString('utf8')); } catch { /* not JSON */ }
      if (parsed?.errorText) throw mapErrorText(parsed.errorText, parsed);
      throw new ProcessingError({
        code: 'INVOICE_PDF_UNAVAILABLE',
        key: 'smartbill.errors.pdf',
        params: { series, number },
        retryable: true,
        provider: PROVIDER,
        details: buf.toString('utf8').slice(0, 500),
      });
    }
    return buf;
  },

  async cancelInvoice(ctx, { series, number }) {
    await call(ctx, 'PUT', '/invoice/cancel', { query: { cif: cif(ctx), seriesname: series, number } });
  },

  /** Hard delete — SmartBill allows it only for the last invoice in a series. Not used by cancel. */
  async deleteInvoice(ctx, { series, number }) {
    await call(ctx, 'DELETE', '/invoice', { query: { cif: cif(ctx), seriesname: series, number } });
  },

  async stornoInvoice(ctx, { series, number, issueDate }) {
    const json = { companyVatCode: cif(ctx), seriesName: series, number: String(number) };
    if (issueDate) json.issueDate = issueDate;
    const body = await call(ctx, 'POST', '/invoice/reverse', { json });
    if (body?.number == null || String(body.number).trim() === '') {
      // Never re-sent automatically: a second /invoice/reverse would reverse the invoice twice.
      throw new ProcessingError({
        code: 'PROVIDER_REJECTED',
        key: 'smartbill.errors.noStornoNumber',
        params: { series, number },
        provider: PROVIDER,
        details: body,
      });
    }
    return { series: body.series || series, number: String(body.number), url: body.documentViewUrl || body.documentUrl || undefined };
  },

  async registerPayment(ctx, { series, number, amount, date, method }) {
    if (amount != null && !(Number(amount) > 0)) {
      ctx.log?.(m('log.zeroPayment', { provider: 'SmartBill' }), { series, number, amount });
      return { skipped: true };
    }
    const type = method === 'card' ? 'Card'
      : method === 'transfer' ? 'Ordin plata'
      : method === 'cod' || !method ? (ctx.settings?.codPaymentType || 'Ramburs')
      : 'Alta incasare';
    const json = {
      companyVatCode: cif(ctx),
      type,
      isCash: false,
      useInvoiceDetails: true, // client taken from the invoice (avoids "CIF client difera")
      invoicesList: [{ seriesName: series, number: String(number) }],
    };
    let value = amount == null ? null : round(amount, 2);
    // Payments carry no idempotency key: cap at what is still unpaid so a repeated call can't collect twice.
    const st = await call(ctx, 'GET', '/invoice/paymentstatus', { query: { cif: cif(ctx), seriesname: series, number: String(number) } });
    const unpaid = st?.unpaidAmount == null ? NaN : round(Number(st.unpaidAmount), 2);
    if (Number.isFinite(unpaid)) {
      if (unpaid <= 0) return { alreadyPaid: true };
      if (value == null || value > unpaid) value = unpaid;
    }
    if (value != null) json.value = value;
    if (date) json.issueDate = bucharestDay(date);
    try {
      await call(ctx, 'POST', '/payment', { json });
    } catch (err) {
      // Repeated delivery webhook / manual collection already done: nothing left to collect — idempotent no-op.
      if (err?.code === 'INVOICE_ALREADY_PAID') return { alreadyPaid: true };
      throw err;
    }
    return {};
  },
};
