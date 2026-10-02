import { createHash } from 'node:crypto';
import { ProcessingError, authError } from '../core/errors.js';
import { bucharestDay } from './ro-time.js';

// Oblio REST API — https://www.oblio.eu/api, official PHP client github.com/OblioSoftware/OblioApi and the official
// WooCommerce plugin github.com/OblioSoftware/woocommerce-oblio (field choices below mirror that plugin).
//
//  - OAuth2 client credentials: POST /api/authorize/token {client_id: e-mail, client_secret: API secret from
//    Setări → Date cont} → {access_token, expires_in: "3600", token_type: "Bearer", request_time}.
//    The secret is regenerated whenever the Oblio password is reset.
//  - Documents: POST /api/docs/invoice (raw JSON). Errors: HTTP 400/401 {status, statusMessage}.
//  - idempotencyKey ("Cheie unica pentru a evita dublarea") makes a retried create safe.
//  - Prices: vatIncluded 1 = price includes VAT (the default). Shipping as productType "Serviciu".
//  - VAT: the plugin sends vatName '' + vatPercentage (Oblio resolves the rate), 'SDD' for 0%, and leaves both
//    empty when the shop doesn't charge VAT.
//  - Storno: POST /api/docs/invoice with referenceDocument {type:'Factura', seriesName, number, refund:1}.
//  - Rate limits: 30 document requests / 100 s, 30 other requests / 10 s.
//  - Product "save" defaults to 1 = "salveaza pretul de lista": every order would overwrite the Oblio list price with
//    the (discounted) Shopify price, so we send save: 0.
//
// Live-checked 2026-10-02 with invalid credentials (test/fixtures/invoicing/live-responses.json):
//  - POST /authorize/token with an unknown client_id/secret → HTTP 400 {error:"invalid_client", error_description:
//    "The client credentials are invalid"} (same for a JSON body). → AUTH_FAILED.
//  - Authenticated endpoints with a bad Bearer → HTTP 401 {status:401, statusMessage:"The access token provided is
//    invalid"}; without Authorization → 401 {status:401, statusMessage:"Authorization header not detected"}.
//  - An unknown /api/... path answers HTTP 200 with an HTML "Pagina inexistenta" page — never treat 200 as success
//    unless the body is Oblio JSON.

const PROVIDER = 'Oblio';
const BASE = 'https://www.oblio.eu/api';
const memTokens = new Map(); // fallback when ctx.cache is missing (per process)

const clean = (s) => String(s ?? '').replace(/[\u200B-\u200D\uFEFF]/g, '').replace(/\s+/g, ' ').trim();
const noSpaces = (s) => String(s ?? '').replace(/[\s\u00A0\u200B-\u200D\uFEFF]+/g, '');
const fold = (s) => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036F]/g, '');
const round = (n, d = 2) => Math.round((Number(n) + Number.EPSILON) * 10 ** d) / 10 ** d;
const decimals = (n) => {
  const s = String(Number(n));
  return s.includes('.') ? s.split('.')[1].length : 0;
};
const sameCif = (a, b) => noSpaces(a).toUpperCase().replace(/^RO/, '') === noSpaces(b).toUpperCase().replace(/^RO/, '');

function cif(ctx) {
  const v = noSpaces(ctx.settings?.cif).toUpperCase();
  if (!v) {
    throw new ProcessingError({
      code: 'INVOICING_SETTINGS_MISSING',
      message: 'Lipsește CIF-ul firmei pentru Oblio.',
      hint: 'Completează CIF-ul firmei în Setări → Facturare, exact ca în Oblio → Setări → Date firmă.',
      provider: PROVIDER,
      field: 'settings.cif',
    });
  }
  return v;
}

// ───────────────────────────── token ─────────────────────────────

function tokenKey(ctx) {
  const id = createHash('sha256').update(`${clean(ctx.credentials?.email).toLowerCase()}:${noSpaces(ctx.credentials?.secret)}`).digest('hex').slice(0, 24);
  return `oblio:token:${id}`;
}

function readToken(ctx) {
  const k = tokenKey(ctx);
  const t = ctx.cache ? ctx.cache.get(k) : memTokens.get(k);
  return t && t.expiresAt > Date.now() ? t : null;
}

function dropToken(ctx) {
  const k = tokenKey(ctx);
  if (ctx.cache) ctx.cache.set(k, null, 1);
  memTokens.delete(k);
}

async function token(ctx) {
  const cached = readToken(ctx);
  if (cached) return cached.accessToken;
  const email = clean(ctx.credentials?.email);
  const secret = noSpaces(ctx.credentials?.secret);
  if (!email || !secret) throw authError(PROVIDER, 'missing email/secret');
  const res = await ctx.http(PROVIDER, `${BASE}/authorize/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ client_id: email, client_secret: secret, grant_type: 'client_credentials' }).toString(),
    mapError: (status, body) => (status === 400 || status === 401 || status === 403 ? authError(PROVIDER, body) : undefined),
  });
  if (!res.body || typeof res.body !== 'object') {
    // HTML maintenance/error page with HTTP 200: not a credentials problem.
    throw new ProcessingError({ code: 'PROVIDER_DOWN', message: 'Oblio a trimis un răspuns neașteptat la autentificare.', hint: 'Reîncercăm automat în câteva minute.', retryable: true, provider: PROVIDER, details: String(res.body ?? '').slice(0, 300) });
  }
  const accessToken = res.body.access_token;
  if (!accessToken) throw authError(PROVIDER, res.body);
  const ttl = Math.max(60, Number(res.body.expires_in) || 3600);
  const entry = { accessToken, expiresAt: Date.now() + (ttl - 60) * 1000 }; // refresh a minute early
  const k = tokenKey(ctx);
  if (ctx.cache) ctx.cache.set(k, entry, ttl - 60);
  else memTokens.set(k, entry);
  return accessToken;
}

// ───────────────────────────── errors ─────────────────────────────

function mapOblioError(status, body) {
  const msg = clean(body?.statusMessage || (typeof body === 'string' ? body : '')) || `cod ${status}`;
  const m = fold(msg);
  const mk = (p) => new ProcessingError({ retryable: false, provider: PROVIDER, details: body, ...p });
  if (status === 429 || /prea multe|too many/i.test(m)) {
    return mk({ code: 'PROVIDER_RATE_LIMIT', message: 'Oblio ne cere să încetinim (prea multe cereri).', hint: 'Reîncercăm automat în câteva minute.', retryable: true });
  }
  if (status >= 500) return undefined; // generic PROVIDER_DOWN, retryable
  if (/seri/i.test(m)) {
    return mk({ code: 'INVOICE_SERIES_NOT_FOUND', message: `Oblio: ${msg}`, hint: 'Verifică seria în Setări → Facturare; trebuie să existe în Oblio → Setări → Serii documente.', field: 'settings.series' });
  }
  if (/cota|tva/i.test(m)) {
    return mk({ code: 'VAT_RATE_NOT_DEFINED', message: `Oblio: ${msg}`, hint: 'Verifică în Oblio → Setări → Cote TVA că există cota folosită (ex. 21% sau 11%) și setarea „plătitor de TVA”.' });
  }
  if (/stoc|gestiun/i.test(m)) {
    return mk({ code: 'INVOICE_STOCK_ERROR', message: `Oblio: ${msg}`, hint: 'Verifică gestiunea din Setări → Facturare și stocul produsului în Oblio, sau dezactivează descărcarea de gestiune.' });
  }
  if (/acces/i.test(m) && /firm|cif|compan/i.test(m)) {
    return mk({ code: 'INVOICING_COMPANY_NOT_FOUND', message: `Oblio: ${msg}`, hint: 'Verifică CIF-ul firmei în Setări → Facturare și că utilizatorul Oblio are acces la firmă.' });
  }
  if (status === 401 || status === 403) return authError(PROVIDER, body);
  if (/nu (a fost gasit|exista)|inexistent/i.test(m)) {
    return mk({ code: 'INVOICE_NOT_FOUND', message: `Oblio: ${msg}`, hint: 'Verifică seria și numărul facturii în Oblio.' });
  }
  return mk({ code: 'PROVIDER_REJECTED', message: `Oblio a refuzat cererea: ${msg}`, hint: 'Verifică datele comenzii și setările de facturare, apoi încearcă din nou.' });
}

async function call(ctx, method, path, { query, json } = {}, retried = false) {
  const url = new URL(BASE + path);
  for (const [k, v] of Object.entries(query || {})) if (v != null) url.searchParams.set(k, String(v));
  const bearer = await token(ctx);
  try {
    const res = await ctx.http(PROVIDER, url.toString(), {
      method,
      json,
      headers: { Authorization: `Bearer ${bearer}` },
      mapError: (status, body) => {
        // 401 with a cached token usually means it expired early: signal the caller to refresh once.
        if (status === 401 && !retried) return new ProcessingError({ code: 'OBLIO_TOKEN_EXPIRED', message: 'token', provider: PROVIDER, details: body });
        return mapOblioError(status, body);
      },
    });
    const body = res.body;
    if (typeof body === 'string' || Buffer.isBuffer(body)) {
      // e.g. HTTP 200 "Pagina inexistenta" HTML for an unknown path or a maintenance page.
      throw new ProcessingError({ code: 'PROVIDER_DOWN', message: 'Oblio a trimis un răspuns neașteptat (nu JSON).', hint: 'Reîncercăm automat în câteva minute.', retryable: true, provider: PROVIDER, details: String(body).slice(0, 300) });
    }
    if (body && typeof body === 'object' && body.status && Number(body.status) !== 200) {
      throw mapOblioError(Number(body.status), body) || mapOblioError(400, body);
    }
    return body;
  } catch (err) {
    if (err?.code === 'OBLIO_TOKEN_EXPIRED') {
      dropToken(ctx);
      return call(ctx, method, path, { query, json }, true);
    }
    throw err;
  }
}

// ───────────────────────────── payload ─────────────────────────────

function bucharestCity(c) {
  const m = fold(c.city).match(/sector(?:ul)?\s*([1-6])\b/i) || fold(c.address).match(/sector(?:ul)?\s*([1-6])\b/i);
  const z = String(c.zip ?? '').trim().match(/^0([1-6])\d{4}$/);
  const s = m ? m[1] : z ? z[1] : null;
  return s ? `SECTOR ${s}` : clean(c.city);
}
const isBucharest = (c) => c.countyCode === 'B' || /^(municipiul\s+)?bucuresti$/i.test(fold(c.county).trim());

function clientPayload(c) {
  const isCompany = Boolean(c.isCompany && c.vatCode);
  const out = {
    // Natural persons: no CNP placeholder — the official plugin sends an empty cif and Oblio handles e-Factura.
    cif: isCompany ? noSpaces(c.vatCode).toUpperCase() : '',
    name: clean(c.name),
    address: clean(c.address),
    state: isBucharest(c) ? 'Bucuresti' : clean(c.county),
    city: isBucharest(c) ? bucharestCity(c) : clean(c.city),
    country: clean(c.country) || 'Romania',
    email: clean(c.email),
    phone: clean(c.phone),
    vatPayer: isCompany && /^RO/i.test(noSpaces(c.vatCode)) ? 1 : 0,
    save: 1,
  };
  if (isCompany && c.regCom) out.rc = clean(c.regCom);
  return out;
}

const COLLECT_TYPE = { card: 'Card', transfer: 'Ordin de plata', cod: 'Ramburs', other: 'Alta incasare banca' };

function idempotencyKey(prefix, value) {
  return `${prefix}-${String(value).replace(/[^A-Za-z0-9_-]+/g, '')}`.slice(0, 64);
}

function invoicePayload(ctx, invoice) {
  const s = ctx.settings || {};
  const vatPayer = s.vatPayer !== false;
  const management = s.useStock ? clean(s.management) : '';
  const currency = invoice.currency || 'RON';
  const products = invoice.lines.map((l) => {
    const negative = Number(l.unitPrice) < 0;
    const p = {
      name: clean(l.name),
      code: clean(l.code),
      description: '',
      price: Math.abs(Number(l.unitPrice)),
      measuringUnit: l.unit || 'buc',
      currency,
      vatIncluded: 1,
      quantity: negative ? -Math.abs(Number(l.quantity)) : Number(l.quantity),
      productType: l.isShipping ? 'Serviciu' : 'Marfa',
      save: 0, // never overwrite the Oblio list price with this order's (possibly discounted) price
    };
    if (vatPayer) {
      // Oblio picks the account's VAT rate by percentage when vatName is empty (as the official plugin does);
      // 0% must be named: 'SDD' (scutit fără drept de deducere).
      p.vatName = Number(l.vatRate) === 0 ? 'SDD' : '';
      p.vatPercentage = Number(l.vatRate);
    } else {
      // Exactly what the official plugin sends when the shop charges no VAT (OblioSoftware/woocommerce-oblio@372d02f,
      // woocommerce-oblio.php: 'vatName' => $woocommerce_calc_taxes ? $vatName : '', 'vatPercentage' => ... : null) —
      // the path every non-VAT-payer WooCommerce shop uses; the docs mark both fields optional.
      p.vatName = '';
      p.vatPercentage = null;
    }
    if (management && !l.isShipping) p.management = management;
    return p;
  });
  const body = {
    cif: cif(ctx),
    client: clientPayload(invoice.client),
    issueDate: invoice.issueDate,
    seriesName: clean(s.series),
    language: s.language || invoice.language || 'RO',
    precision: Math.min(4, Math.max(2, ...invoice.lines.map((l) => decimals(l.unitPrice)))),
    currency,
    products,
    useStock: management ? 1 : 0,
    // Without a client e-mail Oblio has nowhere to send it; don't fail the invoice over it.
    sendEmail: (invoice.sendEmail ?? s.sendEmail) && clean(invoice.client?.email) ? 1 : 0,
    idempotencyKey: idempotencyKey('expedo', invoice.idempotencyKey || invoice.reference),
  };
  if (invoice.dueDate) body.dueDate = invoice.dueDate;
  if (invoice.mentions) body.mentions = clean(invoice.mentions);
  if (clean(s.workStation)) body.workStation = clean(s.workStation);
  if (invoice.paid && s.markPaid !== false) {
    body.collect = {
      type: COLLECT_TYPE[invoice.paymentMethod] || 'Card',
      documentNumber: clean(invoice.reference), // required for every collect type except "Chitanta"
      // value omitted: defaults to the invoice total, so rounding can never leave a 0.01 balance.
    };
  }
  return body;
}

async function listSeries(ctx) {
  const body = await call(ctx, 'GET', '/nomenclature/series', { query: { cif: cif(ctx) } });
  return (body?.data || []).filter((x) => !x.type || x.type === 'Factura').map((x) => ({ id: x.name, name: x.name, next: x.next, default: Boolean(x.default) }));
}

// ───────────────────────────── adapter ─────────────────────────────

export default {
  id: 'oblio',
  name: 'Oblio',

  credentialFields: [
    { key: 'email', label: 'E-mail cont Oblio', type: 'text', required: true,
      help: 'Adresa cu care intri în Oblio.' },
    { key: 'secret', label: 'Cheie API (secret)', type: 'password', required: true,
      help: 'Din Oblio → Setări → Date cont. Se schimbă dacă îți resetezi parola Oblio.' },
  ],

  settingsFields: [
    { key: 'cif', label: 'CIF firmă', type: 'text', required: true,
      help: 'Exact ca în Oblio → Setări → Date firmă (ex. RO12345678).' },
    { key: 'series', label: 'Serie factură', type: 'text', required: true,
      help: 'Seria de facturi din Oblio. Apasă „Testează conexiunea” ca să vezi seriile.' },
    { key: 'vatPayer', label: 'Firma este plătitoare de TVA', type: 'checkbox', default: true,
      help: 'Debifează dacă firma nu e plătitoare de TVA: facturile se emit fără TVA.' },
    { key: 'sendEmail', label: 'Trimite factura clientului pe e-mail', type: 'checkbox', default: false,
      help: 'Folosește e-mailul configurat în Oblio → Setări → E-mail-uri.' },
    { key: 'markPaid', label: 'Marchează încasate comenzile plătite online', type: 'checkbox', default: true,
      help: 'Factura comenzilor plătite cu cardul se emite direct ca încasată.' },
    { key: 'useStock', label: 'Descarcă stocul din gestiune', type: 'checkbox', default: false,
      help: 'Necesită stocuri active în Oblio. Produsele trebuie să aibă același cod (SKU) ca în Oblio.' },
    { key: 'management', label: 'Gestiune', type: 'text',
      help: 'Numele gestiunii din Oblio, folosit doar cu descărcarea de stoc.' },
    { key: 'workStation', label: 'Punct de lucru', type: 'text',
      help: 'Opțional, doar cu stocuri active (implicit „Sediu”).' },
    { key: 'language', label: 'Limba facturii', type: 'select', default: 'RO',
      options: ['RO', 'EN', 'DE', 'FR', 'IT', 'ES', 'HU'].map((v) => ({ value: v, label: v })) },
  ],

  async testConnection(ctx) {
    const companies = (await call(ctx, 'GET', '/nomenclature/companies'))?.data || [];
    const wantedCif = noSpaces(ctx.settings?.cif);
    const company = wantedCif ? companies.find((c) => sameCif(c.cif, wantedCif)) : null;
    if (wantedCif && !company) {
      throw new ProcessingError({
        code: 'INVOICING_COMPANY_NOT_FOUND',
        message: `Conectarea la Oblio merge, dar firma cu CIF ${wantedCif} nu e în cont.`,
        hint: companies.length ? `Firme disponibile: ${companies.map((c) => `${c.company} (${c.cif})`).join(', ')}.` : 'Adaugă firma în Oblio sau verifică contul folosit.',
        provider: PROVIDER,
        field: 'settings.cif',
      });
    }
    if (!company) {
      return { ok: true, message: `Conectat la Oblio. Firme în cont: ${companies.map((c) => `${c.company} (${c.cif})`).join(', ') || 'niciuna'}.`, info: { companies } };
    }
    const series = await listSeries(ctx);
    const wanted = clean(ctx.settings?.series);
    if (wanted && !series.some((x) => x.name === wanted)) {
      throw new ProcessingError({
        code: 'INVOICE_SERIES_NOT_FOUND',
        message: `Conectat la Oblio (${company.company}), dar seria „${wanted}” nu există.`,
        hint: series.length ? `Alege una dintre seriile existente: ${series.map((x) => x.name).join(', ')}.` : 'Creează o serie de facturi în Oblio → Setări → Serii documente.',
        provider: PROVIDER,
        field: 'settings.series',
      });
    }
    return {
      ok: true,
      message: wanted
        ? `Conectat la Oblio (${company.company}). Seria „${wanted}” a fost găsită.`
        : `Conectat la Oblio (${company.company}). Serii disponibile: ${series.map((x) => x.name).join(', ') || 'niciuna'}.`,
      info: { company, series },
    };
  },

  listSeries,

  async listVatRates(ctx) {
    const body = await call(ctx, 'GET', '/nomenclature/vat_rates', { query: { cif: cif(ctx) } });
    return (body?.data || []).map((x) => ({ name: x.name, percent: Number(x.percent), default: Boolean(x.default) }));
  },

  async createInvoice(ctx, invoice) {
    if (!clean(ctx.settings?.series)) {
      throw new ProcessingError({ code: 'INVOICING_SETTINGS_MISSING', message: 'Nu este aleasă seria de facturi Oblio.', hint: 'Alege seria în Setări → Facturare.', provider: PROVIDER, field: 'settings.series' });
    }
    const json = invoicePayload(ctx, invoice);
    const body = await call(ctx, 'POST', '/docs/invoice', { json });
    const d = body?.data || {};
    if (!d.number) {
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: 'Oblio nu a întors numărul facturii.', hint: 'Verifică în Oblio dacă factura a fost emisă.', provider: PROVIDER, details: body });
    }
    return { series: d.seriesName || json.seriesName, number: String(d.number), url: d.link || undefined, raw: body };
  },

  async getPdf(ctx, { series, number }) {
    const body = await call(ctx, 'GET', '/docs/invoice', { query: { cif: cif(ctx), seriesName: series, number } });
    const link = body?.data?.link;
    if (!link) {
      throw new ProcessingError({ code: 'INVOICE_PDF_UNAVAILABLE', message: `Oblio nu a trimis linkul PDF pentru factura ${series} ${number}.`, hint: 'Reîncearcă peste câteva minute.', retryable: true, provider: PROVIDER, details: body });
    }
    // The link needs no Oblio session: the official plugin redirects the shopper's browser to data.link and puts it in
    // the invoice e-mail to the customer (woocommerce-oblio.php, wp_redirect($result['data']['link']) and the [link]
    // e-mail placeholder). VERIFY (needs a real document): that a server-side GET of a fresh link returns the PDF bytes
    // rather than a viewer page. Live 2026-10-02: a stale/invalid show_file link (the docs' sample) answers 301 →
    // /account/ → the HTML login page, so an HTML answer means the link isn't usable — retrying won't help.
    const res = await ctx.http(PROVIDER, link, { method: 'GET', responseType: 'buffer', headers: { Accept: 'application/pdf, */*' } });
    const buf = Buffer.isBuffer(res.body) ? res.body : Buffer.from(res.body ?? '');
    if (buf.subarray(0, 4).toString('latin1') !== '%PDF') {
      const html = /^\s*<(!doctype|html)/i.test(buf.subarray(0, 100).toString('utf8'));
      throw new ProcessingError({
        code: 'INVOICE_PDF_UNAVAILABLE',
        message: `Linkul Oblio pentru factura ${series} ${number} nu a întors un PDF.`,
        hint: html ? 'Oblio a cerut autentificare pentru link. Descarcă factura direct din Oblio.' : 'Reîncearcă peste câteva minute.',
        retryable: !html,
        provider: PROVIDER,
        details: { link, start: buf.toString('utf8').slice(0, 200) },
      });
    }
    return buf;
  },

  async cancelInvoice(ctx, { series, number }) {
    await call(ctx, 'PUT', '/docs/invoice/cancel', { json: { cif: cif(ctx), seriesName: series, number: String(number) } });
  },

  /** Hard delete — Oblio allows it only for the last invoice in a series. Not used by cancel. */
  async deleteInvoice(ctx, { series, number }) {
    await call(ctx, 'DELETE', '/docs/invoice', { json: { cif: cif(ctx), seriesName: series, number: String(number), deleteCollect: true } });
  },

  async stornoInvoice(ctx, { series, number, issueDate }) {
    const json = {
      cif: cif(ctx),
      seriesName: series,
      referenceDocument: { type: 'Factura', seriesName: series, number: String(number), refund: 1 },
      idempotencyKey: idempotencyKey('expedo-storno', `${series}${number}`),
    };
    if (issueDate) json.issueDate = issueDate;
    const body = await call(ctx, 'POST', '/docs/invoice', { json });
    const d = body?.data || {};
    if (d.number == null || String(d.number).trim() === '') {
      // The idempotencyKey makes a retry safe, but a "success" without a number must be looked at, not assumed.
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: `Oblio nu a întors numărul facturii de stornare pentru ${series} ${number}.`, hint: 'Verifică în Oblio dacă stornarea a fost emisă.', provider: PROVIDER, details: body });
    }
    // Docs: storno = POST /api/docs/invoice with referenceDocument.refund — same response as a created invoice.
    return { series: d.seriesName || series, number: String(d.number), url: d.link || undefined };
  },

  async registerPayment(ctx, { series, number, amount, date, method, reference, idempotencyKey: key }) {
    if (amount != null && !(Number(amount) > 0)) {
      ctx.log?.('Oblio: încasare cu suma 0 ignorată', { series, number, amount });
      return { skipped: true };
    }
    const documentNumber = clean(reference) || clean(key) || `${series}${number}`;
    // Collects have no idempotency key: look at the invoice's collects first so a repeated call (webhook
    // redelivery, manual retry) can't record the same money twice.
    const existing = await call(ctx, 'GET', '/docs/invoice', { query: { cif: cif(ctx), seriesName: series, number: String(number) } });
    const dupKeys = new Set([documentNumber, clean(key)].filter(Boolean));
    if ((existing?.data?.collects || []).some((x) => dupKeys.has(clean(x.number)))) return { alreadyPaid: true };
    const collect = { type: COLLECT_TYPE[method] || 'Ramburs', documentNumber };
    if (amount != null) collect.value = round(amount, 2);
    if (date) collect.issueDate = bucharestDay(date);
    await call(ctx, 'PUT', '/docs/invoice/collect', { json: { cif: cif(ctx), seriesName: series, number: String(number), collect } });
    return {};
  },
};
