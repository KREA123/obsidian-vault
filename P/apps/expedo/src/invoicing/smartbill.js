import { ProcessingError, authError } from '../core/errors.js';

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
//  - No idempotency key exists in V1: a timed-out create may still have issued the invoice.

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
    throw new ProcessingError({
      code: 'INVOICING_SETTINGS_MISSING',
      message: 'Lipsește CIF-ul firmei pentru SmartBill.',
      hint: 'Completează CIF-ul firmei în Setări → Facturare, exact cum apare în SmartBill Cloud.',
      provider: PROVIDER,
    });
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
  const m = fold(client.city).match(/sector(?:ul)?\s*([1-6])\b/i);
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

const RULES = [
  [/autentificare esuata/i, () => authError(PROVIDER)],
  [/firma la care incercati sa va conectati/i, (msg) => ({
    code: 'INVOICING_COMPANY_NOT_FOUND',
    message: `SmartBill: ${msg}`,
    hint: 'Verifică CIF-ul firmei în Setări → Facturare: trebuie să fie exact cel din SmartBill Cloud (cu sau fără RO, la fel ca acolo) și utilizatorul API să aibă acces la firmă.',
  })],
  [/seria nu a fost gasita/i, (msg) => ({
    code: 'INVOICE_SERIES_NOT_FOUND',
    message: `SmartBill: ${msg}`,
    hint: 'Verifică seria în Setări → Facturare. Seria trebuie să existe în SmartBill Cloud → Configurare → Serii (atenție la litere mari/mici).',
    field: 'settings.series',
  })],
  [/cota (tva )?.*nu a fost gasita|trebuie sa setezi o cota tva|cota default nu a fost gasita|nu are cota tva setata/i, (msg) => ({
    code: 'VAT_RATE_NOT_DEFINED',
    message: `SmartBill: ${msg}`,
    hint: 'Adaugă cota de TVA în SmartBill Cloud → Configurare → Cote TVA (ex. 21% „Normala”, 11% „Redusa”), apoi emite din nou factura.',
  })],
  [/nu are codul specificat/i, (msg) => ({
    code: 'PRODUCT_CODE_MISSING',
    message: `SmartBill: ${msg}`,
    hint: 'Firma are activată opțiunea „Folosește cod produs” în SmartBill: completează SKU-ul produsului în Shopify sau dezactivează opțiunea în SmartBill.',
    field: 'lines.code',
  })],
  [/nu aveti dreptul/i, (msg) => ({
    code: 'INVOICING_PERMISSION_DENIED',
    message: `SmartBill: ${msg}`,
    hint: 'Utilizatorul API nu are drepturi pe firmă sau pe serie. Cere administratorului contului SmartBill să le acorde din Utilizatori.',
  })],
  [/numarul maxim de documente/i, (msg) => ({
    code: 'INVOICING_PLAN_LIMIT',
    message: `SmartBill: ${msg}`,
    hint: 'Abonamentul SmartBill a atins limita de documente. Schimbă pachetul din contul SmartBill.',
  })],
  [/stoc|gestiunea|achizitie pentru produsul|factor de conversie|modulul stoc/i, (msg) => ({
    code: 'INVOICE_STOCK_ERROR',
    message: `SmartBill: ${msg}`,
    hint: 'Verifică gestiunea din Setări → Facturare și stocul produsului în SmartBill, sau dezactivează descărcarea de gestiune.',
  })],
  [/server-ul de email|adresa de email a clientului/i, (msg) => ({
    code: 'INVOICE_EMAIL_NOT_CONFIGURED',
    message: `SmartBill: ${msg}`,
    hint: 'Configurează serverul de e-mail în SmartBill Cloud → Configurare → Email sau dezactivează „Trimite factura clientului pe e-mail”.',
  })],
  [/client invalid|tara trebuie specificata|clientul exista deja/i, (msg) => ({
    code: 'INVOICE_CLIENT_INVALID',
    message: `SmartBill: ${msg}`,
    hint: 'Verifică numele și țara clientului din comandă. Dacă există un client duplicat în SmartBill (același nume, alt CIF), șterge duplicatul din Nomenclatoare → Clienți.',
    field: 'client.name',
  })],
  [/moneda nu a fost gasita/i, (msg) => ({
    code: 'INVOICE_CURRENCY_INVALID',
    message: `SmartBill: ${msg}`,
    hint: 'Moneda comenzii nu e acceptată de SmartBill. Verifică moneda magazinului.',
  })],
  [/deja stornata/i, (msg) => ({
    code: 'INVOICE_ALREADY_REVERSED',
    message: `SmartBill: ${msg}`,
    hint: 'Factura are deja o factură de stornare în SmartBill. Nu e nevoie de altă acțiune.',
  })],
  [/nu este ultimul din serie/i, (msg) => ({
    code: 'INVOICE_NOT_LAST',
    message: `SmartBill: ${msg}`,
    hint: 'Doar ultima factură din serie poate fi ștearsă. Folosește anularea sau stornarea.',
  })],
  [/anulata/i, (msg) => ({
    code: 'INVOICE_CANCELLED',
    message: `SmartBill: ${msg}`,
    hint: 'Factura este anulată în SmartBill. Restaureaz-o din SmartBill dacă vrei să o stornezi.',
  })],
  [/nu a fost gasita/i, (msg) => ({
    code: 'INVOICE_NOT_FOUND',
    message: `SmartBill: ${msg}`,
    hint: 'Verifică seria și numărul facturii; poate a fost ștearsă din SmartBill.',
  })],
];

function mapErrorText(errorText, details, { status } = {}) {
  const msg = plainError(errorText);
  for (const [re, make] of RULES) {
    if (re.test(fold(msg))) {
      const r = make(msg);
      if (r instanceof ProcessingError) { r.details = details; return r; }
      return new ProcessingError({ retryable: false, provider: PROVIDER, details, ...r });
    }
  }
  const retryable = status === 429 || status >= 500;
  return new ProcessingError({
    code: retryable ? 'PROVIDER_DOWN' : 'PROVIDER_REJECTED',
    message: `SmartBill a refuzat cererea: ${msg}`,
    hint: retryable ? 'Reîncercăm automat în câteva minute.' : 'Verifică datele comenzii și setările de facturare, apoi încearcă din nou.',
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
      const params = body.errors.map((e) => e.param || e.code).filter(Boolean).join(', ');
      return new ProcessingError({
        code: 'PROVIDER_REJECTED',
        message: `SmartBill a respins structura cererii${params ? ` (câmp: ${params})` : ''}.`,
        hint: 'Este o eroare a integrării, nu a comenzii. Trimite-ne detaliile din jurnal.',
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
  const key = `smartbill:tax:${cif(ctx)}`;
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

async function taxFor(ctx, rate) {
  const list = await taxes(ctx);
  const hit = list.find((t) => Number(t.percentage) === Number(rate));
  if (hit) return { taxName: hit.name, taxPercentage: Number(rate) };
  throw new ProcessingError({
    code: 'VAT_RATE_NOT_DEFINED',
    message: `Cota de TVA ${rate}% nu este definită în SmartBill.`,
    hint: `Adaugă cota ${rate}% în SmartBill Cloud → Configurare → Cote TVA, apoi emite din nou factura.`,
    provider: PROVIDER,
    details: { configured: list },
  });
}

// ───────────────────────────── payload ─────────────────────────────

function clientPayload(c) {
  const isCompany = Boolean(c.isCompany && c.vatCode);
  let city = clean(c.city);
  if (isBucharest(c)) {
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
    county: clean(c.county),
    country: clean(c.country) || 'Romania',
    saveToDb: false,
  };
  if (isCompany && c.regCom) out.regCom = clean(c.regCom);
  if (c.email) out.email = clean(c.email);
  if (c.phone) out.phone = clean(c.phone);
  return out;
}

const PAID_TYPE = { card: 'Card online', transfer: 'Ordin plata', other: 'Alta incasare' };

async function invoicePayload(ctx, invoice) {
  const s = ctx.settings || {};
  const useStock = Boolean(s.useStock && clean(s.warehouseName));
  const prec = Math.min(4, Math.max(2, ...invoice.lines.map((l) => decimals(l.unitPrice))));
  const products = [];
  for (const l of invoice.lines) {
    const negative = Number(l.unitPrice) < 0; // price must be >= 0; a negative line goes as negative quantity
    const p = {
      name: clean(l.name),
      measuringUnitName: l.unit || 'buc',
      currency: invoice.currency || 'RON',
      quantity: negative ? -Math.abs(Number(l.quantity)) : Number(l.quantity),
      price: Math.abs(Number(l.unitPrice)),
      isTaxIncluded: true,
      isService: Boolean(l.isShipping),
      isDiscount: false,
      saveToDb: false,
    };
    if (l.code) p.code = clean(l.code);
    if (vatPayer(ctx)) Object.assign(p, await taxFor(ctx, l.vatRate));
    // VERIFY: for a non-VAT-payer company the official plugin omits taxName/taxPercentage entirely;
    // the spec marks taxPercentage required, so we send 0 and no taxName.
    else p.taxPercentage = 0;
    if (useStock && !l.isShipping) p.warehouseName = clean(s.warehouseName);
    products.push(p);
  }

  const body = {
    companyVatCode: cif(ctx),
    client: clientPayload(invoice.client),
    issueDate: invoice.issueDate,
    seriesName: clean(s.series),
    isDraft: false,
    currency: invoice.currency || 'RON',
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
      value: round(invoice.total, 2),
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

// ───────────────────────────── adapter ─────────────────────────────

export default {
  id: 'smartbill',
  name: 'SmartBill',

  credentialFields: [
    { key: 'email', label: 'E-mail cont SmartBill', type: 'text', required: true,
      help: 'Adresa cu care intri în SmartBill Cloud (Configurare → Integrări → API).' },
    { key: 'token', label: 'Token API', type: 'password', required: true,
      help: 'Îl găsești în SmartBill Cloud → Configurare → Integrări → API.' },
  ],

  settingsFields: [
    { key: 'cif', label: 'CIF firmă', type: 'text', required: true,
      help: 'Exact cum apare în SmartBill (Configurare → Integrări → API).' },
    { key: 'series', label: 'Serie factură', type: 'text', required: true,
      help: 'Seria de facturi din SmartBill → Configurare → Serii. Apasă „Testează conexiunea” ca să vezi seriile.' },
    { key: 'vatPayer', label: 'Firma este plătitoare de TVA', type: 'checkbox', default: true,
      help: 'Debifează dacă firma nu e plătitoare de TVA: facturile se emit fără TVA.' },
    { key: 'sendEmail', label: 'Trimite factura clientului pe e-mail', type: 'checkbox', default: false,
      help: 'Necesită server de e-mail configurat în SmartBill → Configurare → Email.' },
    { key: 'markPaid', label: 'Marchează încasate comenzile plătite online', type: 'checkbox', default: true,
      help: 'Factura comenzilor plătite cu cardul se emite direct ca încasată („Card online”).' },
    { key: 'useStock', label: 'Descarcă stocul din gestiune', type: 'checkbox', default: false,
      help: 'Scade stocul în SmartBill la emitere. Produsele trebuie să aibă același cod (SKU) ca în SmartBill.' },
    { key: 'warehouseName', label: 'Gestiune', type: 'text',
      help: 'Numele gestiunii din SmartBill, exact (contează literele mari/mici). Folosit doar cu descărcarea de stoc.' },
    { key: 'language', label: 'Limba facturii', type: 'select', default: 'RO',
      options: ['RO', 'EN', 'DE', 'FR', 'IT', 'ES'].map((v) => ({ value: v, label: v })) },
    { key: 'codPaymentType', label: 'Tip încasare la ramburs', type: 'select', default: 'Ramburs',
      options: [{ value: 'Ramburs', label: 'Ramburs' }, { value: 'Alta incasare', label: 'Altă încasare' }],
      help: 'Cum se înregistrează în SmartBill banii primiți de la curier.' },
  ],

  async testConnection(ctx) {
    const list = await taxes(ctx); // authenticates and validates the CIF
    const series = await listSeries(ctx);
    const wanted = clean(ctx.settings?.series);
    const names = series.map((x) => x.name);
    const vatInfo = list.length
      ? `Cote TVA: ${list.map((t) => `${t.name} ${t.percentage}%`).join(', ')}.`
      : 'Firma apare ca neplătitoare de TVA în SmartBill.';
    if (wanted && !names.includes(wanted)) {
      throw new ProcessingError({
        code: 'INVOICE_SERIES_NOT_FOUND',
        message: `Conectarea la SmartBill merge, dar seria „${wanted}” nu există în cont.`,
        hint: names.length ? `Alege una dintre seriile existente: ${names.join(', ')}.` : 'Creează o serie de facturi în SmartBill → Configurare → Serii.',
        provider: PROVIDER,
        field: 'settings.series',
      });
    }
    return {
      ok: true,
      message: wanted
        ? `Conectat la SmartBill. Seria „${wanted}” a fost găsită. ${vatInfo}`
        : `Conectat la SmartBill. Serii disponibile: ${names.join(', ') || 'niciuna'}. ${vatInfo}`,
      info: { series, taxes: list },
    };
  },

  listSeries,

  async createInvoice(ctx, invoice) {
    if (!clean(ctx.settings?.series)) {
      throw new ProcessingError({
        code: 'INVOICING_SETTINGS_MISSING',
        message: 'Nu este aleasă seria de facturi SmartBill.',
        hint: 'Alege seria în Setări → Facturare.',
        provider: PROVIDER,
        field: 'settings.series',
      });
    }
    const json = await invoicePayload(ctx, invoice);
    let body;
    try {
      body = await call(ctx, 'POST', '/invoice/v2', { json });
    } catch (err) {
      // SmartBill V1 has no idempotency key: after a timeout the invoice may exist. Never auto-retry blindly.
      if (err?.code === 'PROVIDER_TIMEOUT') {
        throw new ProcessingError({
          code: 'INVOICE_STATUS_UNKNOWN',
          message: `SmartBill nu a răspuns la timp; factura pentru comanda ${invoice.reference} poate fi emisă totuși.`,
          hint: 'Verifică în SmartBill Cloud dacă factura există înainte să încerci din nou, ca să nu emiți două facturi.',
          retryable: false,
          provider: PROVIDER,
          details: err.details,
        });
      }
      throw err;
    }
    if (!body?.number) {
      throw new ProcessingError({
        code: 'PROVIDER_REJECTED',
        message: 'SmartBill nu a întors numărul facturii.',
        hint: 'Verifică în SmartBill Cloud dacă factura a fost emisă.',
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
            message: `SmartBill nu a găsit factura ${series} ${number}.`,
            hint: 'Verifică dacă factura mai există în SmartBill Cloud. Dacă există, reîncearcă peste câteva minute.',
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
        message: `SmartBill nu a trimis PDF-ul facturii ${series} ${number}.`,
        hint: 'Reîncearcă peste câteva minute.',
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
    return { series: body?.series || series, number: String(body?.number ?? ''), url: body?.documentViewUrl || undefined };
  },

  async registerPayment(ctx, { series, number, amount, date, method }) {
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
    if (amount != null) json.value = round(amount, 2);
    if (date) json.issueDate = String(date).slice(0, 10);
    await call(ctx, 'POST', '/payment', { json });
  },
};
