import { createHash } from 'node:crypto';
import { ProcessingError } from '../core/errors.js';
import { m } from '../i18n/index.js';
import { bucharestDateTime } from './ro-time.js';

// FGO API — official docs: https://api.fgo.ro/v1/testing.html ("FGO API Documentation v7.0", updated 2026-03-25)
// and the PDF "Metode API - integrare FGO v7.1" (https://testapp.fgo.ro/publicws/files/specificatii-api-latest.pdf).
//
// Verified against those sources:
//  - Production https://api.fgo.ro/v1, test https://api-testuat.fgo.ro/v1 (separate accounts, no sync).
//  - Bodies are RAW JSON (Content-Type: application/json) with nested Client{} / Continut[] — the v7.0 docs say
//    application/x-www-form-urlencoded is NOT supported (live 2026-10-02: a form POST is still parsed for the
//    top-level CodUnic, but nested Client/Continut can't be sent that way). The older PDF shows Client[Denumire]
//    form keys; those are the same fields, nested.
//  - Hash = UPPERCASE hex SHA-1 of:
//      emitere:                               CodUnic + CheiePrivata + Client.Denumire
//      print/anulare/stornare/getstatus/awb:  CodUnic + CheiePrivata + Numar  (the number exactly as emitere
//                                             returned it, e.g. "001" — leading zeros matter, no series)
//      incasare/stergereincasare:            CodUnic + CheiePrivata + NumarFactura
//      articol/*:                            CodUnic + CheiePrivata
//    Spec example: SHA-1("2864518" + "1234567890" + "Ionescu Popescu") = 8C3A7726804C121C6933F7D68494B439463996E2.
//    SHA-1 runs over the UTF-8 bytes: both code samples FGO publishes (v7.0 docs "Code Examples": PHP sha1() on a UTF-8
//    source string, Node crypto.createHash('sha1').update(string) = UTF-8) hash UTF-8; no FGO source mentions any
//    other encoding or diacritics handling. So the client name is
//    normalized ONCE (NFC, no control/zero-width chars, single spaces, ≤255 chars) and that exact string is both
//    hashed and sent. Credentials are stripped of whitespace/invisible chars: FGO support's own fix for hash errors
//    is "retype CIF and key, don't copy-paste".
//  - Errors come as HTTP 200 {Success:false, Message} — but some come as HTTP 500 with the same shape, e.g. the test
//    environment's getstatus answers bad credentials with 500 {Success:false, Message:"System.Exception: Codul unic
//    nu exista sau nu este asociat.\r\n   at Fgo.PublicApi..."} and malformed requests get 500 "Ne pare rau, a
//    intervenit o eroare". Rate limit: 1 request/second for invoice calls.
//  - Live 2026-10-02 (invalid credentials, test/fixtures/invoicing/live-responses.json): an unknown/unauthorized
//    CodUnic gets "Combinatia utilizator/companie nu este autorizata pentru utilizare API. Verificati starea acestuia
//    in Setari -> Utilizatori [<CodUnic>]." on production and "Codul unic nu exista sau nu este asociat." on
//    api-testuat. No documented message mentions the hash: FGO identifies the API user by CodUnic + Hash, so a wrong
//    hash most likely reads like the "not authorized" one — the diacritics retry therefore keys off any auth rejection.
//  - VerificareDuplicat=true + IdExtern = order reference → FGO doesn't issue a second invoice for the same order.
//    Answer when it already exists (official sources, no live sample): changelog v2.3 "Emitere: afișare Serie, NrFactura
//    și link download când factura există deja" + FGO's WooCommerce module guide error #6 "Factura……..exista deja
//    salvata." — handled both with the existing invoice in Factura (returned, flagged duplicate) and without it
//    (INVOICE_DUPLICATE). Success bodies per method: test/fixtures/invoicing/fgo-documented-success.json.
//  - Judet/Localitate must match FGO's nomenclature: ASCII names ("Bucuresti", "Bistrita-Nasaud", "Satu Mare"),
//    localities mostly hyphenated ("Baia-Mare", "Sector-3") with a few spaced exceptions ("Pipera Voluntari",
//    "Bistrita Bargaului Fabrici"). Live-checked: GET /nomenclator/judet (public, no auth) matches COUNTIES below
//    exactly (42 entries); /nomenclator/localitati?judet=B lists Bucuresti + Sector-1..Sector-6 and accepts the county
//    code or name; without judet it answers {Success:false, Message:"Este necesar sa transmiteti parametrul judet..."}.
//  - factura/incasare is only available on FGO Premium/Enterprise; TipIncasare nomenclature (GET /nomenclator/
//    tipincasare, public) is Banca / Retur Casa / Bon / Chitanta on production (api-testuat also lists Voucher and
//    Plata Speciala); there is no "Ramburs".

const PROVIDER = 'FGO';
const PROD = 'https://api.fgo.ro/v1';
const TEST = 'https://api-testuat.fgo.ro/v1';
const NOMENCLATURE_TTL = 7 * 24 * 60 * 60;
const MIN_INTERVAL_MS = 1100;

// Canonical FGO county names (GET /nomenclator/judet), keyed by ISO 3166-2:RO code.
const COUNTIES = {
  AB: 'Alba', AR: 'Arad', AG: 'Arges', BC: 'Bacau', BH: 'Bihor', BN: 'Bistrita-Nasaud', BT: 'Botosani',
  BR: 'Braila', BV: 'Brasov', B: 'Bucuresti', BZ: 'Buzau', CL: 'Calarasi', CS: 'Caras-Severin', CJ: 'Cluj',
  CT: 'Constanta', CV: 'Covasna', DB: 'Dambovita', DJ: 'Dolj', GL: 'Galati', GR: 'Giurgiu', GJ: 'Gorj',
  HR: 'Harghita', HD: 'Hunedoara', IL: 'Ialomita', IS: 'Iasi', IF: 'Ilfov', MM: 'Maramures', MH: 'Mehedinti',
  MS: 'Mures', NT: 'Neamt', OT: 'Olt', PH: 'Prahova', SJ: 'Salaj', SM: 'Satu Mare', SB: 'Sibiu', SV: 'Suceava',
  TR: 'Teleorman', TM: 'Timis', TL: 'Tulcea', VL: 'Valcea', VS: 'Vaslui', VN: 'Vrancea',
};

// ───────────────────────────── helpers ─────────────────────────────

const INVISIBLE = /[\u0000-\u001F\u007F\u00AD\u200B-\u200F\u2028\u2029\u2060\uFEFF]/g;
const clean = (s) => String(s ?? '').normalize('NFC').replace(INVISIBLE, '').replace(/[\s\u00A0]+/g, ' ').trim();
const fold = (s) => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036F]/g, '');
const round = (n, d = 2) => Math.round((Number(n) + Number.EPSILON) * 10 ** d) / 10 ** d;
const key = (s) => fold(s).toLowerCase().replace(/^(municipiul|mun\.?|orasul|oras|comuna|com\.?|satul|sat)\s+/, '').replace(/[\s_-]+/g, '-').trim();

/** Merchant CUI exactly as FGO identifies the company: digits only, no "RO", no spaces. */
export function fgoCodUnic(raw) {
  return String(raw ?? '').normalize('NFKC').replace(INVISIBLE, '').replace(/[\s\u00A0]+/g, '').replace(/^RO/i, '');
}
/** Private key: invisible/whitespace characters are never part of it (copy-paste artefacts). */
export function fgoKey(raw) {
  return String(raw ?? '').normalize('NFKC').replace(INVISIBLE, '').replace(/[\s\u00A0]+/g, '');
}
/** Client name as it will be hashed AND sent — call once and reuse the result. */
export function fgoClientName(raw) {
  return Array.from(clean(raw)).slice(0, 255).join('').trim();
}
/** Uppercase hex SHA-1 of the UTF-8 bytes of codUnic + key + suffix. */
export function fgoHash(codUnic, privateKey, suffix = '') {
  return createHash('sha1').update(`${codUnic}${privateKey}${suffix}`, 'utf8').digest('hex').toUpperCase();
}

const baseUrl = (ctx) => (ctx.settings?.testMode ? TEST : PROD);
const sleep = (ctx, ms) => (ctx.sleep ? ctx.sleep(ms) : new Promise((r) => setTimeout(r, ms)));

function creds(ctx) {
  const codUnic = fgoCodUnic(ctx.credentials?.cui);
  const privateKey = fgoKey(ctx.credentials?.privateKey);
  if (!codUnic || !privateKey) throw fgoAuthError('missing CUI or private key');
  return { codUnic, privateKey };
}

function platformUrl(ctx) {
  let u = String(ctx.settings?.platformUrl ?? '').trim();
  if (!u) {
    throw new ProcessingError({
      code: 'INVOICING_SETTINGS_MISSING',
      key: 'fgo.errors.platformUrlMissing',
      provider: PROVIDER,
      field: 'settings.platformUrl',
    });
  }
  if (!/^https?:\/\//i.test(u)) u = `https://${u}`;
  return u;
}

function fgoAuthError(details) {
  return new ProcessingError({
    code: 'AUTH_FAILED',
    key: 'fgo.errors.auth',
    retryable: false,
    provider: PROVIDER,
    details,
  });
}

// ───────────────────────────── errors ─────────────────────────────

// Observed live: "...nu este autorizata pentru utilizare API..." (prod) and "Codul unic nu exista sau nu este
// asociat." (test env). "Utilizatorul nu exista sau nu are drepturi de acces." is error #1 in FGO's own WooCommerce
// module guide (sources.fgo.ro/addons/instructiuni-utilizare-modul-FGO-Woocommerce.pdf, "Anexa – cele mai frecvente
// mesaje de eroare": test-mode/production mix-up). hash/semnatura/cheia privata are kept for wordings we haven't seen.
const AUTH_RE = /utilizare api|codul unic nu exista|nu este asociat|utilizatorul nu exista|nu are drepturi de acces|\bhash\b|semnatur|chei[ae] privat/i;
// FGO module guide, error #6: "Factura……..exista deja salvata." = VerificareDuplicat found the invoice. A field-required
// message ("The “IdExtern field” is required", error #4) is NOT a duplicate.
const DUPLICATE_RE = /exista deja|\bdeja\b.*\bemis|duplicat/i;
const REQUIRED_RE = /obligatori|required/i;

/** FGO's Message without the .NET exception prefix and stack trace it sometimes includes. */
function fgoMessage(body) {
  let msg = String(body?.Message ?? '');
  msg = msg.split(/\r?\n\s*at\s|\r?\n---/)[0];
  msg = msg.replace(/^\s*System\.[\w.]*Exception:\s*/, '');
  return clean(msg);
}

function mapFgoError(body, op, status = 200) {
  // FGO's own words stay verbatim ("FGO: …" / "FGO says: “…”"); our hint: fgo.errors.<key> in the catalogs.
  const said = fgoMessage(body);
  const f = fold(said);
  const text = said || m('fgo.unknownError');
  const mk = (code, key, p = {}) => new ProcessingError({ retryable: false, provider: PROVIDER, details: body, code, key: `fgo.errors.${key}`, params: { text }, ...p });
  if (AUTH_RE.test(f)) return fgoAuthError(body);
  if (/timpul maxim/i.test(f)) return mk('PROVIDER_TIMEOUT', 'timeout', { retryable: true });
  if (op === 'emitere' && DUPLICATE_RE.test(f) && !REQUIRED_RE.test(f)) {
    // VerificareDuplicat found an invoice for this IdExtern but didn't return it (when it does, we use it).
    return mk('INVOICE_DUPLICATE', 'duplicate');
  }
  if (/seri|registr/i.test(f)) {
    // "Registrul pentru seria … nu este definit sau a expirat" / "Registrul pentru acest utilizator nu exista…" (module guide #7)
    return mk('INVOICE_SERIES_NOT_FOUND', 'series', { field: 'settings.series' });
  }
  if (/judet/i.test(f)) return mk('ADDRESS_COUNTY_INVALID', 'county', { field: 'client.county' });
  if (/localitat/i.test(f)) return mk('ADDRESS_CITY_NOT_FOUND', 'city', { field: 'client.city' });
  if (/codgestiune/i.test(f)) {
    // Module guide #5: "Valoarea…asociata parametrului Continut[…][CodGestiune] nu a fost identificata."
    return mk('INVOICE_STOCK_ERROR', 'warehouse', { field: 'settings.warehouseCode' });
  }
  if (/\b(cod(ul)? ?unic|cui|cif|cod(ul)? fiscal)\b/i.test(f)) return mk('CLIENT_VAT_CODE_INVALID', 'clientVatCode', { field: 'client.vatCode' });
  if (/tva/i.test(f)) return mk('VAT_RATE_NOT_DEFINED', 'vat');
  if (/decomisionat|premium|enterprise|abonament|pachet/i.test(f)) return mk('INVOICING_PLAN_LIMIT', op === 'incasare' ? 'planPayments' : 'plan');
  if (/request|cereri|interval|limita/i.test(f)) return mk('PROVIDER_RATE_LIMIT', 'rateLimit', { retryable: true });
  if (/nu (a fost gasita|exista)|inexistent/i.test(f) && op !== 'emitere') return mk('INVOICE_NOT_FOUND', 'notFound');
  if (status >= 500) {
    // e.g. 500 "Ne pare rau, a intervenit o eroare". On emitere a retry is safe: VerificareDuplicat + IdExtern.
    return mk('PROVIDER_DOWN', 'server', { retryable: true });
  }
  return mk('PROVIDER_REJECTED', 'rejected');
}

/** POST to FGO with CodUnic/Hash/PlatformaUrl added; throws on Success:false (which arrives with HTTP 200). */
async function post(ctx, path, payload, hashSuffix, { op, allowFailureBody } = {}) {
  const { codUnic, privateKey } = creds(ctx);
  const json = { CodUnic: codUnic, Hash: fgoHash(codUnic, privateKey, hashSuffix), ...payload, PlatformaUrl: platformUrl(ctx) };
  const res = await ctx.http(PROVIDER, `${baseUrl(ctx)}/${path}`, {
    method: 'POST',
    json,
    timeoutMs: 30000,
    mapError: (status, body) => {
      if (!body || typeof body !== 'object' || body.Success !== false) return undefined;
      // A Success:false body is FGO's answer whatever the HTTP status (getstatus answers some with 500).
      if (allowFailureBody?.(body)) return Object.assign(new Error('fgo-failure-body'), { fgoBody: body });
      return mapFgoError(body, op, status);
    },
  }).catch((err) => {
    if (err?.fgoBody) return { status: 200, body: err.fgoBody };
    throw err;
  });
  const body = res.body;
  if (!body || typeof body !== 'object') {
    throw new ProcessingError({ code: 'PROVIDER_REJECTED', key: 'fgo.errors.unexpected', retryable: true, provider: PROVIDER, details: body });
  }
  if (body.Success !== true && !(allowFailureBody && allowFailureBody(body))) throw mapFgoError(body, op, res.status);
  return body;
}

// ───────────────────────────── address ─────────────────────────────

function countyName(c) {
  const code = String(c.countyCode ?? '').trim().toUpperCase();
  if (COUNTIES[code]) return { code, name: COUNTIES[code] };
  const k = key(c.county).replace(/-/g, ' ');
  for (const [cc, name] of Object.entries(COUNTIES)) {
    if (key(name).replace(/-/g, ' ') === k) return { code: cc, name };
  }
  return { code: '', name: fold(clean(c.county)) };
}

function bucharestSector(c) {
  const m = fold(c.city).match(/sector(?:ul)?\s*([1-6])\b/i) || fold(c.address).match(/sector(?:ul)?\s*([1-6])\b/i);
  if (m) return Number(m[1]);
  const z = String(c.zip ?? '').trim().match(/^0([1-6])\d{4}$/);
  return z ? Number(z[1]) : null;
}

async function localities(ctx, countyCode) {
  const cacheKey = `fgo:loc:${ctx.settings?.testMode ? 't' : 'p'}:${countyCode}`;
  const hit = ctx.cache?.get(cacheKey);
  if (hit) return hit;
  try {
    const res = await ctx.http(PROVIDER, `${baseUrl(ctx)}/nomenclator/localitati?judet=${encodeURIComponent(countyCode)}`, { method: 'GET', timeoutMs: 10000 });
    const list = (res.body?.List || []).map((x) => x.Nume).filter(Boolean);
    if (list.length) ctx.cache?.set(cacheKey, list, NOMENCLATURE_TTL);
    return list;
  } catch (err) {
    ctx.log?.(m('log.localitiesUnavailablePlain', { provider: PROVIDER }), { countyCode, error: err?.message });
    return [];
  }
}

async function localityName(ctx, c, county) {
  if (county.code === 'B') {
    const s = bucharestSector(c);
    return s ? `Sector-${s}` : 'Bucuresti';
  }
  const wanted = key(c.city);
  if (county.code) {
    const list = await localities(ctx, county.code);
    const found = list.find((n) => key(n) === wanted);
    if (found) return found;
  }
  // VERIFY: unknown whether FGO rejects a locality outside its nomenclature; we send the closest canonical form.
  return fold(clean(c.city)).replace(/\s+/g, '-');
}

// ───────────────────────────── adapter ─────────────────────────────

async function buildEmitere(ctx, invoice, clientName) {
  const s = ctx.settings || {};
  const c = invoice.client;
  const isRo = !c.country || /^(ro|romania)$/i.test(fold(clean(c.country)));
  const county = isRo ? countyName(c) : { code: '', name: clean(c.county) };
  const isCompany = Boolean(c.isCompany && c.vatCode);

  const client = {
    Denumire: clientName,
    Tip: isCompany ? 'PJ' : 'PF',
    Tara: isRo ? 'RO' : clean(c.country),
    Judet: county.name,
    Localitate: isRo ? await localityName(ctx, c, county) : clean(c.city),
    Adresa: clean(c.address).slice(0, 500),
  };
  // PF: no CNP placeholder — FGO ignores invalid CNPs and identifies natural persons by name + county.
  if (isCompany) client.CodUnic = String(c.vatCode).replace(/\s+/g, '').toUpperCase();
  if (isCompany && c.regCom) client.NrRegCom = clean(c.regCom);
  if (c.email) client.Email = clean(c.email).slice(0, 100);
  if (c.phone) client.Telefon = clean(c.phone).slice(0, 100);

  const vatPayer = s.vatPayer !== false;
  const warehouse = clean(s.warehouseCode);
  const Continut = invoice.lines.map((l) => {
    const qty = Number(l.quantity);
    const total = round(Math.abs(qty * Number(l.unitPrice)), 2);
    const negative = Number(l.unitPrice) < 0;
    const item = {
      Denumire: clean(l.name).slice(0, 1000),
      UM: String(l.unit || 'buc').slice(0, 5),
      // Negative lines (discounts) go as negative quantity, per spec.
      NrProduse: negative ? -Math.abs(qty) : qty,
      CotaTVA: vatPayer ? Number(l.vatRate) : 0,
      // PretTotal = what the customer paid for the line, VAT and quantity included ("calcul invers").
      // FGO derives the unit price and VAT from it, so we never compute nets ourselves.
      PretTotal: total,
    };
    if (l.code) item.CodArticol = clean(l.code).slice(0, 128);
    if (warehouse && !l.isShipping) item.CodGestiune = warehouse;
    return item;
  });

  const body = {
    Valuta: invoice.currency || 'RON',
    TipFactura: 'Factura',
    Serie: clean(s.series),
    DataEmitere: invoice.issueDate,
    VerificareDuplicat: true,
    IdExtern: String(invoice.idempotencyKey || invoice.reference || '').slice(0, 36),
    Client: client,
    Continut,
  };
  if (invoice.dueDate) body.DataScadenta = invoice.dueDate;
  // "Text" is the old "Destinatar" field (delegate name); free mentions belong in "Explicatii".
  if (invoice.mentions) body.Explicatii = clean(invoice.mentions).slice(0, 2000);
  if (!body.IdExtern) delete body.IdExtern;
  return body;
}

function paymentType(ctx, method) {
  // Live-checked: GET /nomenclator/tipincasare is public (no CodUnic) and lists Banca / Retur Casa / Bon / Chitanta on
  // production — environment-wide, not per account. "Banca" is the right default; the settings allow an override.
  if (method === 'card') return ctx.settings?.cardPaymentType || 'Banca';
  if (method === 'cod' || !method) return ctx.settings?.codPaymentType || 'Banca';
  return 'Banca';
}

async function invoiceStatus(ctx, series, num) {
  const body = await post(ctx, 'factura/getstatus', { Numar: num, Serie: series }, num, { op: 'getstatus' });
  const f = body.Factura || {};
  return { total: Number(f.Valoare), paid: Number(f.ValoareAchitata), raw: body };
}

async function incasare(ctx, { series, number, amount, date, method }, { fresh = false } = {}) {
  const num = String(number);
  let value = amount == null ? null : round(amount, 2);
  if (value != null && !(value > 0)) {
    ctx.log?.(m('log.zeroPayment', { provider: PROVIDER }), { series, number: num, amount });
    return { skipped: true };
  }
  if (!fresh) {
    // No external id on încasări: check what is still unpaid so a repeated call can't collect twice.
    const st = await invoiceStatus(ctx, series, num);
    const due = round(st.total - (st.paid || 0), 2);
    if (Number.isFinite(due) && due <= 0) return { alreadyPaid: true };
    if (value == null || (Number.isFinite(due) && value > due)) value = due;
    await sleep(ctx, MIN_INTERVAL_MS); // FGO: max 1 invoice/payment request per second
  }
  if (value == null || !Number.isFinite(value)) {
    throw new ProcessingError({ code: 'PAYMENT_AMOUNT_MISSING', key: 'fgo.errors.paymentAmount', params: { series, number: num }, provider: PROVIDER });
  }
  await post(ctx, 'factura/incasare', {
    NumarFactura: num,
    SerieFactura: series,
    TipIncasare: paymentType(ctx, method),
    SumaIncasata: value,
    DataIncasare: bucharestDateTime(date),
  }, num, { op: 'incasare' });
  return {};
}

export default {
  id: 'fgo',
  name: 'FGO',

  // Labels and help: fgo.fields.<key> in the catalogs (src/i18n).
  credentialFields: [
    { key: 'cui', type: 'text', required: true },
    { key: 'privateKey', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'series', type: 'text', required: true },
    { key: 'platformUrl', type: 'text', required: true },
    { key: 'vatPayer', type: 'checkbox', default: true },
    { key: 'warehouseCode', type: 'text' },
    { key: 'registerCardPayments', type: 'checkbox', default: false },
    // Values from FGO's own "Tip încasare" list.
    { key: 'cardPaymentType', type: 'text', default: 'Banca' },
    { key: 'codPaymentType', type: 'text', default: 'Banca' },
    { key: 'testMode', type: 'checkbox', default: false },
  ],

  async testConnection(ctx) {
    platformUrl(ctx);
    // FGO has no "whoami" call. getstatus for a non-existent number authenticates first, then fails on the
    // invoice — so an auth error means bad credentials and any other error means they were accepted.
    // Auth wording is live-checked (see header; test env answers it with HTTP 500) plus FGO's module-guide wording
    // "Utilizatorul nu exista sau nu are drepturi de acces." (test/production mix-up). VERIFY: the wording FGO uses for
    // "invoice 0 not found" with VALID credentials — no FGO document lists it; only a real (test) account can show it.
    const series = clean(ctx.settings?.series) || 'X';
    const body = await post(ctx, 'factura/getstatus', { Numar: '0', Serie: series }, '0', {
      op: 'test',
      // Any specific complaint about the probe invoice means the credentials passed; FGO's generic
      // "a intervenit o eroare" proves nothing.
      allowFailureBody: (b) => Boolean(fgoMessage(b)) && !AUTH_RE.test(fold(fgoMessage(b))) && !/a intervenit o eroare/i.test(fold(fgoMessage(b))),
    });
    if (body.Success === false && /seri|registr/i.test(fold(fgoMessage(body))) && !/factura/i.test(fold(fgoMessage(body)))) {
      throw mapFgoError(body, 'test');
    }
    return {
      ok: true,
      message: m('fgo.test.connected', { sandbox: ctx.settings?.testMode ? m('fgo.test.sandbox') : '' }),
      info: { response: body },
    };
  },

  async createInvoice(ctx, invoice) {
    if (!clean(ctx.settings?.series)) {
      throw new ProcessingError({ code: 'INVOICING_SETTINGS_MISSING', key: 'fgo.errors.seriesNotChosen', provider: PROVIDER, field: 'settings.series' });
    }
    let name = fgoClientName(invoice.client.name);
    if (!name) {
      throw new ProcessingError({ code: 'CLIENT_NAME_MISSING', key: 'fgo.errors.clientName', provider: PROVIDER, field: 'client.name' });
    }
    const payload = await buildEmitere(ctx, invoice, name);
    // Duplicate check may answer with the existing invoice (changelog v2.3: "afișare Serie, NrFactura și link download
    // când factura există deja").
    const invoiceNumber = (b) => b?.Factura?.Numar ?? b?.Factura?.NrFactura;
    const isExisting = (b) => Boolean(invoiceNumber(b));

    let body;
    try {
      body = await post(ctx, 'factura/emitere', payload, name, { op: 'emitere', allowFailureBody: isExisting });
    } catch (err) {
      // Defensive: if FGO's side hashes a different byte form of a name with diacritics, the call fails before any
      // invoice exists, so one retry with the diacritic-free name is safe (the same string is hashed and sent).
      // FGO's live auth rejections never mention the hash (see header), so any auth rejection of a non-ASCII name
      // gets the one retry; with genuinely bad credentials it costs one extra request and fails the same way.
      // VERIFY: remove once FGO confirms UTF-8 hashing on their side.
      const ascii = fgoClientName(fold(name));
      if (err?.code === 'AUTH_FAILED' && ascii !== name) {
        ctx.log?.(m('log.fgoDiacriticsRetry', { provider: PROVIDER }), { reference: invoice.reference });
        await sleep(ctx, MIN_INTERVAL_MS);
        name = ascii;
        const retry = { ...payload, Client: { ...payload.Client, Denumire: ascii } };
        body = await post(ctx, 'factura/emitere', retry, ascii, { op: 'emitere', allowFailureBody: isExisting });
      } else {
        throw err;
      }
    }

    const f = body.Factura || {};
    const num = invoiceNumber(body);
    if (num == null || String(num).trim() === '') {
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', key: 'fgo.errors.noNumber', provider: PROVIDER, details: body });
    }
    // Spec examples: Link is "" in the PDF spec, a URL in the v7 HTML docs — "" means "no link", not a URL.
    const result = { series: f.Serie || payload.Serie, number: String(num), url: f.Link || undefined, raw: body };
    // Success:false + the existing invoice, or (defensively) Success:true whose message says it already existed.
    if (body.Success !== true || DUPLICATE_RE.test(fold(fgoMessage(body)))) result.duplicate = true;

    if (invoice.paid && ctx.settings?.registerCardPayments && !result.duplicate) {
      try {
        await sleep(ctx, MIN_INTERVAL_MS); // FGO: max 1 invoice/payment request per second
        // Amount = sum of the PretTotal values FGO received, i.e. exactly the invoice total FGO computes.
        const amount = round(payload.Continut.reduce((sum, l) => sum + Math.sign(l.NrProduse) * l.PretTotal, 0), 2);
        await incasare(ctx, { series: result.series, number: result.number, amount, date: invoice.issueDate, method: invoice.paymentMethod }, { fresh: true });
      } catch (err) {
        // The invoice exists; a failed "încasare" must not make the pipeline issue it again.
        ctx.log?.(m('log.paymentAfterInvoiceFailed', { provider: PROVIDER }), { reference: invoice.reference, error: err?.message });
        result.paymentError = err?.message;
      }
    }
    return result;
  },

  async getPdf(ctx, { series, number }) {
    const num = String(number);
    const body = await post(ctx, 'factura/print', { Numar: num, Serie: series }, num, { op: 'print' });
    const link = body.Factura?.Link;
    if (!link) {
      throw new ProcessingError({ code: 'INVOICE_PDF_UNAVAILABLE', key: 'fgo.errors.pdfLink', params: { series, number: num }, retryable: true, provider: PROVIDER, details: body });
    }
    const res = await ctx.http(PROVIDER, link, { method: 'GET', responseType: 'buffer', headers: { Accept: 'application/pdf, */*' } });
    const buf = Buffer.isBuffer(res.body) ? res.body : Buffer.from(res.body ?? '');
    if (buf.subarray(0, 4).toString('latin1') !== '%PDF') {
      throw new ProcessingError({ code: 'INVOICE_PDF_UNAVAILABLE', key: 'fgo.errors.pdf', params: { series, number: num }, retryable: true, provider: PROVIDER, details: { link, start: buf.toString('utf8').slice(0, 200) } });
    }
    return buf;
  },

  async cancelInvoice(ctx, { series, number }) {
    const num = String(number);
    await post(ctx, 'factura/anulare', { Numar: num, Serie: series }, num, { op: 'anulare' });
  },

  async stornoInvoice(ctx, { series, number, issueDate }) {
    const num = String(number);
    const payload = { Numar: num, Serie: series };
    if (issueDate) payload.DataEmitere = issueDate;
    const body = await post(ctx, 'factura/stornare', payload, num, { op: 'stornare' });
    const stornoNumber = body.Factura?.Numar;
    if (stornoNumber == null || String(stornoNumber).trim() === '') {
      // Never re-sent automatically: a second stornare would reverse the invoice twice.
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', key: 'fgo.errors.noStornoNumber', params: { series, number: num }, provider: PROVIDER, details: body });
    }
    return { series: body.Factura?.Serie || series, number: String(stornoNumber), url: body.Factura?.Link || undefined };
  },

  async registerPayment(ctx, p) {
    return incasare(ctx, p);
  },

  /** Total and paid amount of an invoice (factura/getstatus). */
  async getInvoiceStatus(ctx, { series, number }) {
    return invoiceStatus(ctx, series, String(number));
  },
};
