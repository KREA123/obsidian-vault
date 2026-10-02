import { test } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fgo, { fgoHash, fgoCodUnic, fgoKey, fgoClientName } from '../src/invoicing/fgo.js';
import { ProcessingError, authError } from '../src/core/errors.js';

// ── fakes ──────────────────────────────────────────────────────────────────

function fakeHttp(handler) {
  const calls = [];
  const http = async (provider, url, opts = {}) => {
    const call = { provider, url: new URL(url), method: opts.method || 'GET', headers: opts.headers || {}, json: opts.json, opts };
    calls.push(call);
    const out = await handler(call, calls);
    if (out instanceof Error) throw out;
    const status = out.status ?? 200;
    if (status < 200 || status >= 300) {
      const mapped = opts.mapError?.(status, out.body);
      if (mapped) throw mapped;
      if (status === 401 || status === 403) throw authError(provider, out.body);
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: `generic ${status}`, provider, details: out.body });
    }
    return { status, headers: new Headers(), body: out.body };
  };
  return { http, calls };
}

function fakeCache() {
  const m = new Map();
  return { get: (k) => m.get(k), set: (k, v) => m.set(k, v) };
}

/** Independent reference implementation of the FGO hash, straight from the spec. */
const sha1Upper = (s) => crypto.createHash('sha1').update(Buffer.from(s, 'utf8')).digest('hex').toUpperCase();

const CUI = '12345678';
const KEY = 'A1B2C3D4E5F6';

function ctxWith(handler, settings = {}, credentials = {}) {
  const { http, calls } = fakeHttp(handler);
  const sleeps = [];
  return {
    ctx: {
      credentials: { cui: CUI, privateKey: KEY, ...credentials },
      settings: { series: 'MIDA', platformUrl: 'https://mida.ro', vatPayer: true, ...settings },
      http,
      cache: fakeCache(),
      log: () => {},
      sleep: async (ms) => { sleeps.push(ms); },
    },
    calls,
    sleeps,
  };
}

const LOCALITIES_CJ = { Success: true, List: [{ Nume: 'Aschileu-Mic' }, { Nume: 'Cluj-Napoca' }, { Nume: 'Turda' }] };
const EMITERE_OK = { Success: true, Message: '', Factura: { Numar: '001', Serie: 'MIDA', Link: 'https://www.fgo.ro/f/abc.pdf', LinkPlata: '' } };

const router = (overrides = {}) => (c) => {
  const path = c.url.pathname.replace(/^\/v1\//, '');
  if (overrides[path]) return overrides[path](c);
  if (path === 'nomenclator/localitati') return { body: LOCALITIES_CJ };
  if (path === 'factura/emitere') return { body: EMITERE_OK };
  if (path === 'factura/incasare') return { body: { Success: true, Message: '', Incasare: { Numar: '1', Serie: 'CH' } } };
  if (path === 'factura/getstatus') return { body: { Success: true, Factura: { Numar: c.json.Numar, Serie: c.json.Serie, Valoare: '239.97', ValoareAchitata: '0' } } };
  throw new Error(`unexpected ${path}`);
};

const b2c = () => ({
  reference: '#1024',
  issueDate: '2026-10-02',
  dueDate: '2026-10-12',
  currency: 'RON',
  language: 'RO',
  client: {
    name: 'Ion Popescu', isCompany: false, address: 'Str. Lalelelor 1', city: 'Cluj Napoca', county: 'Cluj',
    countyCode: 'CJ', zip: '400001', country: 'Romania', email: 'ion@example.com', phone: '0722000000',
  },
  lines: [
    { name: 'Tricou negru (M)', code: 'TR-M', quantity: 2, unitPrice: 59.99, vatRate: 21, unit: 'buc' },
    { name: 'Carte', quantity: 3, unitPrice: 33.3333, vatRate: 11, unit: 'buc' },
    { name: 'Transport', quantity: 1, unitPrice: 19.99, vatRate: 21, unit: 'buc', isShipping: true },
  ],
  total: 239.97,
  paid: false,
  paymentMethod: 'cod',
  mentions: 'Comanda #1024',
});

const emitere = (calls) => calls.find((c) => c.url.pathname === '/v1/factura/emitere');

// ── hash ───────────────────────────────────────────────────────────────────

test('hash matches the official FGO spec example', () => {
  // "Metode API - integrare FGO", section "Cum se calculeaza HASH-ul?"
  assert.equal(fgoHash('2864518', '1234567890', 'Ionescu Popescu'), '8C3A7726804C121C6933F7D68494B439463996E2');
  assert.equal(sha1Upper('28645181234567890Ionescu Popescu'), '8C3A7726804C121C6933F7D68494B439463996E2');
  assert.equal(fgoHash('2864518', '1234567890', '123'), sha1Upper('28645181234567890123'));
  assert.equal(fgoHash('2864518', '1234567890'), sha1Upper('28645181234567890'));
});

test('credential normalization: no RO prefix, no spaces or invisible characters', () => {
  assert.equal(fgoCodUnic(' RO 12345678​ '), '12345678');
  assert.equal(fgoCodUnic('ro12345678'), '12345678');
  assert.equal(fgoKey(' A1B2C3 D4E5F6﻿\n'), 'A1B2C3D4E5F6');
});

test('client name normalization is stable (NFC, single spaces, no invisible chars, ≤255 chars)', () => {
  const decomposed = 'Ștefan  Țăranu​ '; // Ș/ț/ă written with combining marks + junk
  assert.equal(fgoClientName(decomposed), 'Ștefan Țăranu');
  assert.equal(fgoClientName(fgoClientName(decomposed)), 'Ștefan Țăranu', 'idempotent');
  assert.equal(fgoClientName('x'.repeat(300)).length, 255);
});

test('emitere: Hash = SHA1(CodUnic + key + Client.Denumire) and the same name is sent', async () => {
  const { ctx, calls } = ctxWith(router(), {}, { cui: 'RO 12345678 ', privateKey: ` ${KEY}​` });
  const inv = b2c();
  inv.client.name = '  Ștefan   Țăranu & Fiii "Ăîâșț" ';
  await fgo.createInvoice(ctx, inv);
  const body = emitere(calls).json;
  const sent = body.Client.Denumire;
  assert.equal(sent, 'Ștefan Țăranu & Fiii "Ăîâșț"');
  assert.equal(body.CodUnic, CUI);
  assert.equal(body.Hash, sha1Upper(CUI + KEY + sent));
  assert.match(body.Hash, /^[0-9A-F]{40}$/);
});

// ── emitere payload ────────────────────────────────────────────────────────

test('createInvoice B2C: JSON body, PretTotal incl. VAT, county/locality from FGO nomenclature', async () => {
  const { ctx, calls } = ctxWith(router());
  const res = await fgo.createInvoice(ctx, b2c());
  assert.deepEqual({ series: res.series, number: res.number, url: res.url }, { series: 'MIDA', number: '001', url: 'https://www.fgo.ro/f/abc.pdf' });

  const c = emitere(calls);
  assert.equal(c.method, 'POST');
  assert.equal(c.url.origin, 'https://api.fgo.ro');
  assert.ok(c.json && typeof c.json === 'object', 'sent as JSON (form-urlencoded is not supported anymore)');
  const body = c.json;
  assert.equal(body.Valuta, 'RON');
  assert.equal(body.TipFactura, 'Factura');
  assert.equal(body.Serie, 'MIDA');
  assert.equal(body.DataEmitere, '2026-10-02');
  assert.equal(body.DataScadenta, '2026-10-12');
  assert.equal(body.VerificareDuplicat, true);
  assert.equal(body.IdExtern, '#1024', 'order reference used for FGO duplicate check');
  assert.equal(body.PlatformaUrl, 'https://mida.ro');
  assert.equal(body.Explicatii, 'Comanda #1024');

  assert.deepEqual(body.Client, {
    Denumire: 'Ion Popescu', Tip: 'PF', Tara: 'RO', Judet: 'Cluj', Localitate: 'Cluj-Napoca',
    Adresa: 'Str. Lalelelor 1', Email: 'ion@example.com', Telefon: '0722000000',
  });
  assert.equal('CodUnic' in body.Client, false, 'no CNP placeholder for natural persons');

  const [tshirt, book, ship] = body.Continut;
  assert.deepEqual(tshirt, { Denumire: 'Tricou negru (M)', UM: 'buc', NrProduse: 2, CotaTVA: 21, PretTotal: 119.98, CodArticol: 'TR-M' });
  assert.equal(book.PretTotal, 100, '3 × 33.3333 rounded to what the customer paid');
  assert.equal(book.CotaTVA, 11);
  assert.equal('PretUnitar' in book, false, 'never both PretUnitar and PretTotal');
  assert.equal(ship.Denumire, 'Transport');
  assert.equal(ship.PretTotal, 19.99);

  const loc = calls.find((x) => x.url.pathname === '/v1/nomenclator/localitati');
  assert.equal(loc.url.searchParams.get('judet'), 'CJ');
});

test('locality nomenclature is cached per county', async () => {
  const { ctx, calls } = ctxWith(router());
  await fgo.createInvoice(ctx, b2c());
  await fgo.createInvoice(ctx, b2c());
  assert.equal(calls.filter((x) => x.url.pathname === '/v1/nomenclator/localitati').length, 1);
});

test('createInvoice B2B: PJ with CUI and Reg. Com.', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = b2c();
  inv.client = { ...inv.client, name: 'MI-DA SRL', isCompany: true, vatCode: 'ro 87654321', regCom: 'J12/123/2020' };
  await fgo.createInvoice(ctx, inv);
  const cl = emitere(calls).json.Client;
  assert.equal(cl.Tip, 'PJ');
  assert.equal(cl.CodUnic, 'RO87654321');
  assert.equal(cl.NrRegCom, 'J12/123/2020');
  assert.equal(emitere(calls).json.Hash, sha1Upper(CUI + KEY + 'MI-DA SRL'));
});

test('București: Judet "Bucuresti", Localitate "Sector-N" from the postal code', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = b2c();
  inv.client = { ...inv.client, city: 'București', county: 'București', countyCode: 'B', zip: '030167' };
  await fgo.createInvoice(ctx, inv);
  const cl = emitere(calls).json.Client;
  assert.equal(cl.Judet, 'Bucuresti');
  assert.equal(cl.Localitate, 'Sector-3');
});

test('county without code is matched to the FGO name (no diacritics)', async () => {
  const { ctx, calls } = ctxWith(router({ 'nomenclator/localitati': () => ({ body: { Success: true, List: [{ Nume: 'Bistrita' }] } }) }));
  const inv = b2c();
  inv.client = { ...inv.client, city: 'Bistrița', county: 'Bistrița-Năsăud', countyCode: '' };
  await fgo.createInvoice(ctx, inv);
  const cl = emitere(calls).json.Client;
  assert.equal(cl.Judet, 'Bistrita-Nasaud');
  assert.equal(cl.Localitate, 'Bistrita');
});

test('non-VAT payer: CotaTVA 0 on every line', async () => {
  const { ctx, calls } = ctxWith(router(), { vatPayer: false });
  await fgo.createInvoice(ctx, b2c());
  assert.deepEqual(emitere(calls).json.Continut.map((l) => l.CotaTVA), [0, 0, 0]);
});

test('warehouse code goes on goods, not on the shipping line', async () => {
  const { ctx, calls } = ctxWith(router(), { warehouseCode: 'G1' });
  await fgo.createInvoice(ctx, b2c());
  const lines = emitere(calls).json.Continut;
  assert.equal(lines[0].CodGestiune, 'G1');
  assert.equal(lines[2].CodGestiune, undefined);
});

test('test environment uses api-testuat.fgo.ro', async () => {
  const { ctx, calls } = ctxWith(router(), { testMode: true });
  await fgo.createInvoice(ctx, b2c());
  assert.equal(emitere(calls).url.origin, 'https://api-testuat.fgo.ro');
});

test('missing PlatformaUrl → settings error before any call', async () => {
  const { ctx, calls } = ctxWith(router(), { platformUrl: '' });
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'INVOICING_SETTINGS_MISSING' && err.field === 'settings.platformUrl');
  assert.equal(emitere(calls), undefined);
});

// ── errors (Success:false arrives with HTTP 200) ──────────────────────────

test('Success:false with HTTP 200 is an error; series message → series hint', async () => {
  const body = { Success: false, Message: 'Seria MIDA nu exista sau nu are registru definit.' };
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ status: 200, body }) }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => {
    assert.ok(err instanceof ProcessingError);
    assert.equal(err.code, 'INVOICE_SERIES_NOT_FOUND');
    assert.match(err.message, /Seria MIDA/);
    assert.match(err.hint, /Setări → Facturare/);
    assert.deepEqual(err.details, body);
    return true;
  });
});

test('unauthorized API user → AUTH_FAILED with FGO-specific hint', async () => {
  const body = { Success: false, Message: 'Combinatia utilizator/companie nu este autorizata pentru utilizare API. Verificati starea acestuia in Setari -> Utilizatori [1].' };
  const { ctx } = ctxWith(() => ({ body }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'AUTH_FAILED' && /fără „RO”/.test(err.hint));
});

test('generic Success:false message is passed through in Romanian', async () => {
  const body = { Success: false, Message: 'Cantitatea trebuie sa fie diferita de 0.' };
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ body }) }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'PROVIDER_REJECTED' && /FGO a refuzat cererea: Cantitatea/.test(err.message));
});

test('emitere timeout message from FGO is retryable', async () => {
  const body = { Success: false, Message: 'Timpul maxim pentru emiterea unei facturi a expirat. Factura nu a fost emisa si este necesar sa reincercati. [3]' };
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ body }) }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.retryable === true);
});

test('duplicate check answering with the existing invoice → returns it instead of failing', async () => {
  const body = { Success: false, Message: 'Factura pentru comanda #1024 a fost deja emisa.', Factura: { Numar: '001', Serie: 'MIDA', Link: 'https://www.fgo.ro/f/abc.pdf' } };
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ body }) }));
  const res = await fgo.createInvoice(ctx, b2c());
  assert.equal(res.number, '001');
  assert.equal(res.duplicate, true);
});

test('hash rejected for a name with diacritics → one retry with the diacritic-free name (hashed consistently)', async () => {
  let n = 0;
  const { ctx, calls, sleeps } = ctxWith(router({
    'factura/emitere': () => (++n === 1 ? { body: { Success: false, Message: 'Hash invalid.' } } : { body: EMITERE_OK }),
  }));
  const inv = b2c();
  inv.client.name = 'Ștefan Țăranu';
  const res = await fgo.createInvoice(ctx, inv);
  assert.equal(res.number, '001');
  const both = calls.filter((c) => c.url.pathname === '/v1/factura/emitere');
  assert.equal(both.length, 2);
  assert.equal(both[0].json.Client.Denumire, 'Ștefan Țăranu');
  assert.equal(both[0].json.Hash, sha1Upper(CUI + KEY + 'Ștefan Țăranu'));
  assert.equal(both[1].json.Client.Denumire, 'Stefan Taranu');
  assert.equal(both[1].json.Hash, sha1Upper(CUI + KEY + 'Stefan Taranu'));
  assert.deepEqual(sleeps, [1100]);
});

test('hash rejected for an ASCII name → no retry, AUTH_FAILED', async () => {
  const { ctx, calls } = ctxWith(router({ 'factura/emitere': () => ({ body: { Success: false, Message: 'Hash invalid.' } }) }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'AUTH_FAILED');
  assert.equal(calls.filter((c) => c.url.pathname === '/v1/factura/emitere').length, 1);
});

// ── other operations: hash over the invoice number exactly as returned ──

test('getPdf: print hash uses the number with its leading zeros, then downloads the link into a Buffer', async () => {
  const pdf = Buffer.from('%PDF-1.7\nfake');
  const { ctx, calls } = ctxWith((c) => {
    if (c.url.pathname === '/v1/factura/print') return { body: { Success: true, Factura: { Numar: '001', Serie: 'MIDA', Link: 'https://storage.fgo.ro/x/001.pdf' } } };
    if (c.url.href === 'https://storage.fgo.ro/x/001.pdf') return { body: pdf };
    throw new Error('unexpected ' + c.url.href);
  });
  const out = await fgo.getPdf(ctx, { series: 'MIDA', number: '001' });
  assert.ok(Buffer.isBuffer(out));
  assert.equal(out.toString(), pdf.toString());
  const print = calls[0].json;
  assert.equal(print.Numar, '001');
  assert.equal(print.Serie, 'MIDA');
  assert.equal(print.Hash, sha1Upper(CUI + KEY + '001'));
  assert.notEqual(print.Hash, sha1Upper(CUI + KEY + '1'));
  assert.equal(calls[1].opts.responseType, 'buffer');
});

test('getPdf: link that is not a PDF → retryable error', async () => {
  const { ctx } = ctxWith((c) => (c.url.pathname === '/v1/factura/print'
    ? { body: { Success: true, Factura: { Numar: '001', Serie: 'MIDA', Link: 'https://storage.fgo.ro/x' } } }
    : { body: Buffer.from('<html>login</html>') }));
  await assert.rejects(fgo.getPdf(ctx, { series: 'MIDA', number: '001' }), (err) => err.code === 'INVOICE_PDF_UNAVAILABLE' && err.retryable);
});

test('cancelInvoice → factura/anulare with number hash', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { Success: true, Message: 'Factura a fost anulata.' } }));
  await fgo.cancelInvoice(ctx, { series: 'MIDA', number: '007' });
  assert.equal(calls[0].url.pathname, '/v1/factura/anulare');
  assert.equal(calls[0].json.Hash, sha1Upper(CUI + KEY + '007'));
  assert.equal(calls[0].json.PlatformaUrl, 'https://mida.ro');
});

test('stornoInvoice → factura/stornare; hash over the ORIGINAL number', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { Success: true, Factura: { Numar: '008', Serie: 'MIDA', Link: '' } } }));
  const out = await fgo.stornoInvoice(ctx, { series: 'MIDA', number: '007' });
  assert.deepEqual({ series: out.series, number: out.number }, { series: 'MIDA', number: '008' });
  assert.equal(calls[0].url.pathname, '/v1/factura/stornare');
  assert.equal(calls[0].json.Hash, sha1Upper(CUI + KEY + '007'));
});

test('registerPayment → factura/incasare with NumarFactura hash and FGO date format', async () => {
  const { ctx, calls } = ctxWith(router());
  await fgo.registerPayment(ctx, { series: 'MIDA', number: '001', amount: 239.97, date: '2025-10-05', method: 'cod' });
  assert.equal(calls[0].url.pathname, '/v1/factura/getstatus'); // what is still unpaid, so a repeat can't collect twice
  const inc = calls.find((c) => c.url.pathname === '/v1/factura/incasare');
  const body = inc.json;
  assert.equal(body.NumarFactura, '001');
  assert.equal(body.SerieFactura, 'MIDA');
  assert.equal(body.TipIncasare, 'Banca');
  assert.equal(body.SumaIncasata, 239.97);
  assert.equal(body.DataIncasare, '2025-10-05 00:00:00'); // a past plain date: start of that day
  assert.equal(body.Hash, sha1Upper(CUI + KEY + '001'));
});

test('paid by card with registerCardPayments: emitere, 1 s pause (rate limit), then incasare', async () => {
  const { ctx, calls, sleeps } = ctxWith(router(), { registerCardPayments: true });
  const inv = { ...b2c(), paid: true, paymentMethod: 'card' };
  const res = await fgo.createInvoice(ctx, inv);
  assert.equal(res.number, '001');
  const inc = calls.find((c) => c.url.pathname === '/v1/factura/incasare');
  assert.ok(inc);
  assert.equal(inc.json.SumaIncasata, 239.97);
  assert.deepEqual(sleeps, [1100]);
});

test('payment failure after a successful emitere does not fail the invoice', async () => {
  const { ctx } = ctxWith(router({ 'factura/incasare': () => ({ body: { Success: false, Message: 'Metoda disponibila doar pentru Premium & Enterprise' } }) }), { registerCardPayments: true });
  const res = await fgo.createInvoice(ctx, { ...b2c(), paid: true, paymentMethod: 'card' });
  assert.equal(res.number, '001');
  assert.match(res.paymentError, /Premium/);
});

test('testConnection: credentials accepted when FGO only complains about the probe invoice', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { Success: false, Message: 'Factura nu a fost gasita.' } }));
  const res = await fgo.testConnection(ctx);
  assert.equal(res.ok, true);
  assert.match(res.message, /acceptate/);
  assert.equal(calls[0].json.Hash, sha1Upper(CUI + KEY + '0'));
});

test('testConnection: bad credentials → AUTH_FAILED', async () => {
  const { ctx } = ctxWith(() => ({ body: { Success: false, Message: 'Codul unic nu exista sau nu este asociat.' } }));
  await assert.rejects(fgo.testConnection(ctx), (err) => err.code === 'AUTH_FAILED');
});

test('adapter fields are in Romanian and include PlatformaUrl and test mode', () => {
  const keys = fgo.settingsFields.map((f) => f.key);
  for (const k of ['series', 'platformUrl', 'vatPayer', 'testMode']) assert.ok(keys.includes(k), k);
  assert.deepEqual(fgo.credentialFields.map((f) => f.key), ['cui', 'privateKey']);
});

// ── live-checked responses (test/fixtures/invoicing/live-responses.json) ──

import { readFileSync } from 'node:fs';
const LIVE = JSON.parse(readFileSync(new URL('./fixtures/invoicing/live-responses.json', import.meta.url), 'utf8')).fgo;

test('live: production "not authorized for API use" and test-env "Codul unic nu exista" → AUTH_FAILED, not retryable', async () => {
  for (const k of ['prodUnknownCui', 'testUnknownCui']) {
    const { ctx } = ctxWith(() => ({ status: LIVE[k].status, body: LIVE[k].body }));
    await assert.rejects(fgo.testConnection(ctx), (err) => err.code === 'AUTH_FAILED' && err.retryable === false, k);
    await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'AUTH_FAILED' && err.retryable === false, k);
  }
});

test('live: test-env getstatus answers bad credentials with HTTP 500 + .NET stack → AUTH_FAILED, stack never shown', async () => {
  const { ctx } = ctxWith(() => ({ status: LIVE.testGetstatusUnknownCui500.status, body: LIVE.testGetstatusUnknownCui500.body }), { testMode: true });
  await assert.rejects(fgo.testConnection(ctx), (err) => err.code === 'AUTH_FAILED');
  const other = ctxWith(() => ({ status: 500, body: { Success: false, Message: 'System.Exception: Seria XYZ nu exista.\r\n   at Fgo.PublicApi.Controllers.FacturaController.<Print>d__9.MoveNext()' } }));
  await assert.rejects(fgo.getPdf(other.ctx, { series: 'XYZ', number: '001' }), (err) => {
    assert.equal(err.message, 'FGO: Seria XYZ nu exista.');
    return true;
  });
});

test('testConnection: valid credentials whose probe getstatus fails with HTTP 500 about the invoice → accepted', async () => {
  const { ctx } = ctxWith(() => ({ status: 500, body: { Success: false, Message: 'System.Exception: Factura nu a fost gasita.\r\n   at Fgo.PublicApi...' } }));
  const res = await fgo.testConnection(ctx);
  assert.equal(res.ok, true);
});

test('live: FGO generic 500 "Ne pare rau, a intervenit o eroare" → retryable PROVIDER_DOWN; testConnection does not claim success', async () => {
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ status: 500, body: LIVE.prodGeneric500.body }) }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'PROVIDER_DOWN' && err.retryable === true);
  const t = ctxWith(() => ({ status: 500, body: LIVE.prodGeneric500.body }));
  await assert.rejects(fgo.testConnection(t.ctx), (err) => err.code === 'PROVIDER_DOWN');
});

test('live: auth rejection that does not mention the hash still triggers the one diacritics-free retry', async () => {
  let n = 0;
  const { ctx, calls } = ctxWith(router({ 'factura/emitere': () => (++n === 1 ? { body: LIVE.prodUnknownCui.body } : { body: EMITERE_OK }) }));
  const inv = b2c();
  inv.client.name = 'Ștefan Țăranu';
  const res = await fgo.createInvoice(ctx, inv);
  assert.equal(res.number, '001');
  const both = calls.filter((c) => c.url.pathname === '/v1/factura/emitere');
  assert.equal(both.length, 2);
  assert.equal(both[1].json.Hash, sha1Upper(CUI + KEY + 'Stefan Taranu'));
  // genuinely bad credentials: exactly one extra attempt, then AUTH_FAILED
  const bad = ctxWith(router({ 'factura/emitere': () => ({ body: LIVE.prodUnknownCui.body }) }));
  await assert.rejects(fgo.createInvoice(bad.ctx, inv), (err) => err.code === 'AUTH_FAILED');
  assert.equal(bad.calls.filter((c) => c.url.pathname === '/v1/factura/emitere').length, 2);
});

test('live nomenclator: county map equals GET /nomenclator/judet; Bucuresti localities are Sector-N', async () => {
  for (const { Cod, Nume } of LIVE.judet.body.List) {
    const { ctx, calls } = ctxWith(router({ 'nomenclator/localitati': () => ({ body: { Success: true, List: [] } }) }));
    const inv = b2c();
    inv.client = { ...inv.client, county: 'x', countyCode: Cod, city: 'Sector 2', zip: '' };
    await fgo.createInvoice(ctx, inv);
    assert.equal(emitere(calls).json.Client.Judet, Nume, Cod);
    if (Cod === 'B') assert.ok(LIVE.localitiesB.body.List.some((l) => l.Nume === emitere(calls).json.Client.Localitate));
  }
});

test('live nomenclator: spaced locality names ("Pipera Voluntari") are matched and sent exactly', async () => {
  const { ctx, calls } = ctxWith(router({ 'nomenclator/localitati': () => ({ body: LIVE.localitiesIFExcerpt.body }) }));
  const inv = b2c();
  inv.client = { ...inv.client, county: 'Ilfov', countyCode: 'IF', city: 'Pipera-Voluntari' };
  await fgo.createInvoice(ctx, inv);
  assert.equal(emitere(calls).json.Client.Localitate, 'Pipera Voluntari');
  inv.client.city = 'Popești Leordeni';
  await fgo.createInvoice(ctx, inv);
  assert.equal(emitere(calls.slice(-1)).json.Client.Localitate, 'Popesti-Leordeni');
});

// ── adversarial review fixes ──

test('card încasare at emitere = sum of the PretTotal values sent (FGO\'s own total), not the raw order total', async () => {
  const { ctx, calls } = ctxWith(router(), { registerCardPayments: true });
  const inv = { ...b2c(), paid: true, paymentMethod: 'card', total: 999 };
  await fgo.createInvoice(ctx, inv);
  const sent = emitere(calls).json.Continut.reduce((s, l) => s + l.PretTotal, 0);
  const inc = calls.find((c) => c.url.pathname === '/v1/factura/incasare');
  assert.equal(inc.json.SumaIncasata, Math.round(sent * 100) / 100);
  assert.equal(calls.filter((c) => c.url.pathname === '/v1/factura/getstatus').length, 0); // fresh invoice: no pre-check
});

test('registerPayment: already fully paid → no second încasare; missing amount → what is still unpaid; 0 → nothing', async () => {
  const paid = ctxWith(router({ 'factura/getstatus': () => ({ body: { Success: true, Factura: { Valoare: '239.97', ValoareAchitata: '239.97' } } }) }));
  assert.deepEqual(await fgo.registerPayment(paid.ctx, { series: 'MIDA', number: '001', amount: 239.97, method: 'cod' }), { alreadyPaid: true });
  assert.equal(paid.calls.filter((c) => c.url.pathname === '/v1/factura/incasare').length, 0);

  const partial = ctxWith(router({ 'factura/getstatus': () => ({ body: { Success: true, Factura: { Valoare: '239.97', ValoareAchitata: '100' } } }) }));
  await fgo.registerPayment(partial.ctx, { series: 'MIDA', number: '001', method: 'cod' });
  assert.equal(partial.calls.find((c) => c.url.pathname === '/v1/factura/incasare').json.SumaIncasata, 139.97);
  assert.deepEqual(partial.sleeps, [1100]);

  const zero = ctxWith(() => { throw new Error('no call expected'); });
  assert.deepEqual(await fgo.registerPayment(zero.ctx, { series: 'MIDA', number: '001', amount: 0, method: 'cod' }), { skipped: true });
});

test('registerPayment: DataIncasare is Bucharest local time, never UTC', async () => {
  const { ctx, calls } = ctxWith(router());
  await fgo.registerPayment(ctx, { series: 'MIDA', number: '001', amount: 10, date: '2026-07-01T22:30:15.000Z', method: 'cod' });
  assert.equal(calls.find((c) => c.url.pathname === '/v1/factura/incasare').json.DataIncasare, '2026-07-02 01:30:15'); // EEST, UTC+3
});

test('duplicate IdExtern rejected without the existing invoice → INVOICE_DUPLICATE (never retried into a second invoice)', async () => {
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ body: { Success: false, Message: 'Exista deja o factura emisa pentru IdExtern #1024.' } }) }));
  await assert.rejects(fgo.createInvoice(ctx, b2c()), (err) => err.code === 'INVOICE_DUPLICATE' && err.retryable === false);
});

test('IdExtern uses idempotencyKey ("#1024-2" after a storno), falling back to the order reference', async () => {
  const a = ctxWith(router());
  await fgo.createInvoice(a.ctx, { ...b2c(), idempotencyKey: '#1024-2' });
  assert.equal(emitere(a.calls).json.IdExtern, '#1024-2');
  assert.equal(emitere(a.calls).json.VerificareDuplicat, true);
  const b = ctxWith(router());
  await fgo.createInvoice(b.ctx, b2c());
  assert.equal(emitere(b.calls).json.IdExtern, '#1024');
});

test('client CUI rejected ("Codul unic al clientului...") → CLIENT_VAT_CODE_INVALID, not an auth error', async () => {
  const { ctx } = ctxWith(router({ 'factura/emitere': () => ({ body: { Success: false, Message: 'Codul unic al clientului RO123 nu este valid (ANAF).' } }) }));
  const inv = { ...b2c(), client: { ...b2c().client, name: 'ACME SRL', isCompany: true, vatCode: 'RO123' } };
  await assert.rejects(fgo.createInvoice(ctx, inv), (err) => err.code === 'CLIENT_VAT_CODE_INVALID' && err.field === 'client.vatCode');
});
