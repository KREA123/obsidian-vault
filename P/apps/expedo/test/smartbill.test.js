import { test } from 'node:test';
import assert from 'node:assert/strict';
import smartbill from '../src/invoicing/smartbill.js';
import { ProcessingError, authError } from '../src/core/errors.js';
import { ro } from './helpers-i18n.js';
import { catalogs } from '../src/i18n/index.js';

// ── fakes ──────────────────────────────────────────────────────────────────

/** Fake ctx.http with the same contract as src/lib/http.js: non-2xx → opts.mapError, else generic errors. */
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
      throw new ProcessingError({ code: status >= 500 ? 'PROVIDER_DOWN' : 'PROVIDER_REJECTED', message: `generic ${status}`, retryable: status >= 500, provider, details: out.body });
    }
    return { status, headers: new Headers(), body: out.body };
  };
  return { http, calls };
}

function fakeCache() {
  const m = new Map();
  return { get: (k) => m.get(k), set: (k, v) => m.set(k, v), map: m };
}

const TAXES = { errorText: '', taxes: [{ name: 'Normala', percentage: 21 }, { name: 'Redusa', percentage: 11 }, { name: 'Taxare inversa', percentage: 0 }] };
const OK_INVOICE = { errorText: '', message: '', number: '0007', series: 'EXP', url: '', documentViewUrl: 'https://cloud.smartbill.ro/documente/extern/pf/factura/abc' };

function ctxWith(handler, settings = {}) {
  const { http, calls } = fakeHttp(handler);
  return {
    ctx: {
      credentials: { email: 'office@magazin.ro', token: ' 003|abcdef ' },
      settings: { cif: 'RO12345678', series: 'EXP', vatPayer: true, ...settings },
      http,
      cache: fakeCache(),
      log: () => {},
    },
    calls,
  };
}

/** Default router: /tax, /series, /invoice/v2. */
const router = (overrides = {}) => (c) => {
  const path = c.url.pathname.replace('/SBORO/api', '');
  const key = `${c.method} ${path}`;
  if (overrides[key]) return overrides[key](c);
  if (key === 'GET /tax') return { body: TAXES };
  if (key === 'GET /series') return { body: { errorText: '', list: [{ name: 'EXP', nextNumber: 8, type: 'f' }, { name: 'TST', nextNumber: 1, type: 'f' }] } };
  if (key === 'POST /invoice/v2') return { body: OK_INVOICE };
  throw new Error(`unexpected ${key}`);
};

const b2c = () => ({
  reference: '#1024',
  issueDate: '2026-10-02',
  dueDate: '2026-10-02',
  currency: 'RON',
  language: 'RO',
  client: {
    name: 'Ion Popescu', isCompany: false, address: 'Str. Lalelelor 1', city: 'Cluj-Napoca', county: 'Cluj',
    countyCode: 'CJ', zip: '400001', country: 'Romania', email: 'ion@example.com', phone: '0722000000',
  },
  lines: [
    { name: 'Tricou negru (M)', code: 'TR-M', quantity: 2, unitPrice: 59.99, vatRate: 21, unit: 'buc' },
    { name: 'Carte', code: 'CRT-1', quantity: 1, unitPrice: 45.5, vatRate: 11, unit: 'buc' },
    { name: 'Transport', quantity: 1, unitPrice: 19.99, vatRate: 21, unit: 'buc', isShipping: true },
  ],
  total: 185.47,
  paid: false,
  paymentMethod: 'cod',
  mentions: 'Comanda #1024',
});

const b2bPaid = () => ({
  ...b2c(),
  client: { ...b2c().client, name: 'ACME SRL', isCompany: true, vatCode: 'ro 12345678', regCom: 'J12/123/2020' },
  paid: true,
  paymentMethod: 'card',
});

const invoiceCall = (calls) => calls.find((c) => c.method === 'POST' && c.url.pathname.endsWith('/invoice/v2'));

// ── tests ──────────────────────────────────────────────────────────────────

test('adapter shape and field labels in both languages', () => {
  assert.equal(smartbill.id, 'smartbill');
  for (const k of ['testConnection', 'createInvoice', 'getPdf', 'cancelInvoice', 'stornoInvoice', 'registerPayment', 'listSeries']) {
    assert.equal(typeof smartbill[k], 'function', k);
  }
  assert.deepEqual(smartbill.credentialFields.map((f) => f.key), ['email', 'token']);
  const keys = smartbill.settingsFields.map((f) => f.key);
  for (const k of ['cif', 'series', 'vatPayer', 'sendEmail', 'useStock', 'warehouseName', 'language']) assert.ok(keys.includes(k), k);
  // Labels live in the catalogs (smartbill.fields.<key>.label), in English and Romanian.
  for (const f of [...smartbill.credentialFields, ...smartbill.settingsFields]) {
    const key = `smartbill.fields.${f.key}.label`;
    assert.ok(catalogs.en[key] && catalogs.ro[key], key);
    assert.equal(f.label, undefined, `${f.key}: no hard-coded label`);
  }
});

test('HTTP Basic auth uses email:token (token trimmed) on every call', async () => {
  const { ctx, calls } = ctxWith(router());
  await smartbill.createInvoice(ctx, b2c());
  const expected = 'Basic ' + Buffer.from('office@magazin.ro:003|abcdef').toString('base64');
  assert.ok(calls.length >= 2);
  for (const c of calls) assert.equal(c.headers.Authorization, expected);
});

test('createInvoice B2C: gross prices with isTaxIncluded, VAT names from /tax, shipping as service', async () => {
  const { ctx, calls } = ctxWith(router());
  const res = await smartbill.createInvoice(ctx, b2c());
  assert.deepEqual({ series: res.series, number: res.number }, { series: 'EXP', number: '0007' });
  assert.equal(res.url, OK_INVOICE.documentViewUrl);

  const tax = calls.find((c) => c.url.pathname.endsWith('/tax'));
  assert.equal(tax.url.searchParams.get('cif'), 'RO12345678');

  const body = invoiceCall(calls).json;
  assert.equal(body.companyVatCode, 'RO12345678');
  assert.equal(body.seriesName, 'EXP');
  assert.equal(body.isDraft, false);
  assert.equal(body.issueDate, '2026-10-02');
  assert.equal(body.dueDate, '2026-10-02');
  assert.equal(body.currency, 'RON');
  assert.equal(body.language, 'RO');
  assert.equal(body.mentions, 'Comanda #1024');
  assert.equal(body.payment, undefined, 'COD order is not marked as collected');
  assert.equal(body.sendEmail, undefined);

  assert.deepEqual(body.client, {
    name: 'Ion Popescu', vatCode: '0000000000000', isTaxPayer: false, address: 'Str. Lalelelor 1',
    city: 'Cluj-Napoca', county: 'Cluj', country: 'Romania', saveToDb: false, email: 'ion@example.com', phone: '0722000000',
  });

  const [tshirt, book, ship] = body.products;
  assert.deepEqual(tshirt, {
    name: 'Tricou negru (M)', code: 'TR-M', measuringUnitName: 'buc', currency: 'RON', quantity: 2, price: 59.99,
    isTaxIncluded: true, isService: false, isDiscount: false, saveToDb: false, taxName: 'Normala', taxPercentage: 21,
  });
  assert.equal(book.taxName, 'Redusa');
  assert.equal(book.taxPercentage, 11);
  assert.equal(book.price, 45.5, 'gross price passed through, never recomputed');
  assert.equal(ship.isService, true);
  assert.equal(ship.isTaxIncluded, true);
  assert.equal(ship.code, undefined);
});

test('createInvoice B2B paid by card: company client and payment block', async () => {
  const { ctx, calls } = ctxWith(router());
  await smartbill.createInvoice(ctx, b2bPaid());
  const body = invoiceCall(calls).json;
  assert.equal(body.client.name, 'ACME SRL');
  assert.equal(body.client.vatCode, 'RO12345678');
  assert.equal(body.client.isTaxPayer, true);
  assert.equal(body.client.regCom, 'J12/123/2020');
  assert.deepEqual(body.payment, { value: 185.47, type: 'Card online', isCash: false });
});

test('VAT rates are fetched once and cached', async () => {
  const { ctx, calls } = ctxWith(router());
  await smartbill.createInvoice(ctx, b2c());
  await smartbill.createInvoice(ctx, b2c());
  assert.equal(calls.filter((c) => c.url.pathname.endsWith('/tax')).length, 1);
});

test('non-VAT payer: no /tax lookup and no tax fields at all (spec example 14; 0% without a name = Taxare inversa)', async () => {
  const { ctx, calls } = ctxWith(router(), { vatPayer: false });
  await smartbill.createInvoice(ctx, b2c());
  assert.equal(calls.filter((c) => c.url.pathname.endsWith('/tax')).length, 0);
  for (const p of invoiceCall(calls).json.products) {
    assert.equal('taxPercentage' in p, false);
    assert.equal('taxName' in p, false);
    assert.equal(p.isTaxIncluded, true);
  }
});

test('precision follows the unit prices (up to 4 decimals) so totals match what the customer paid', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = b2c();
  inv.lines[0].unitPrice = 33.3333;
  inv.lines[0].quantity = 3;
  await smartbill.createInvoice(ctx, inv);
  const body = invoiceCall(calls).json;
  assert.equal(body.precision, 4);
  assert.equal(body.products[0].price, 33.3333);
});

test('stock and e-mail settings', async () => {
  const { ctx, calls } = ctxWith(router(), { useStock: true, warehouseName: 'Depozit', sendEmail: true });
  await smartbill.createInvoice(ctx, b2c());
  const body = invoiceCall(calls).json;
  assert.equal(body.useStock, true);
  assert.equal(body.products[0].warehouseName, 'Depozit');
  assert.equal(body.products[2].warehouseName, undefined, 'shipping is a service, not stock');
  assert.equal(body.sendEmail, true);
  assert.deepEqual(body.email, { to: 'ion@example.com' });
});

test('București: city becomes "Sector N" (from the postal code) for e-Factura', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = b2c();
  inv.client = { ...inv.client, city: 'București', county: 'București', countyCode: 'B', zip: '030167' };
  await smartbill.createInvoice(ctx, inv);
  assert.equal(invoiceCall(calls).json.client.city, 'Sector 3');
});

test('VAT rate missing in the SmartBill account → actionable error, no invoice call', async () => {
  const { ctx, calls } = ctxWith(router({ 'GET /tax': () => ({ body: { errorText: '', taxes: [{ name: 'Normala', percentage: 21 }] } }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.ok(err instanceof ProcessingError);
    assert.equal(err.code, 'VAT_RATE_NOT_DEFINED');
    assert.match(ro(err).message, /11%/);
    assert.match(ro(err).hint, /SmartBill.*Cote TVA/);
    return true;
  });
  assert.equal(invoiceCall(calls), undefined);
});

test('errorText "Seria nu a fost gasita" (HTTP 400) → series error with settings hint', async () => {
  const body = { errorText: 'Seria nu a fost gasita! Folositi o serie creata in contul de cloud.', number: '', series: '' };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.equal(err.code, 'INVOICE_SERIES_NOT_FOUND');
    assert.match(ro(err).message, /Seria nu a fost gasita/);
    assert.match(ro(err).hint, /Setări → Facturare/);
    assert.equal(err.retryable, false);
    assert.deepEqual(err.details, body, 'raw response kept in details');
    return true;
  });
});

test('errorText with HTTP 200 is still a failure; HTML is stripped from the message', async () => {
  const body = { errorText: 'Cantitate stoc insuficienta la <b>2026-10-02</b> pentru produsul <b>Tricou</b>', number: '' };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 200, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.equal(err.code, 'INVOICE_STOCK_ERROR');
    assert.doesNotMatch(ro(err).message, /</);
    return true;
  });
});

test('VAT rate rejected by SmartBill on create → hint to add it in SmartBill', async () => {
  const body = { errorText: 'Cota tva a produsului Tricou nu a fost gasita pe server!' };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'VAT_RATE_NOT_DEFINED' && /Configurare → Cote TVA/.test(ro(err).hint));
});

test('bad credentials → AUTH_FAILED', async () => {
  const body = { successfully: false, errorText: 'Autentificare esuata. Va rugam verificati datele si incercati din nou.' };
  const { ctx } = ctxWith(() => ({ status: 401, body }));
  await assert.rejects(smartbill.testConnection(ctx), (err) => err.code === 'AUTH_FAILED' && err.provider === 'SmartBill');
});

test('unknown field (json_mapping_error, no errorText) is reported as an integration error', async () => {
  const body = { status: 400, type: 'invalid_request_error', errors: [{ code: 'json_mapping_error', message: 'Unrecognized property: zzz.', param: 'zzz' }] };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'PROVIDER_REJECTED' && /zzz/.test(ro(err).message));
});

/** /series answers with a counter that the test can advance (as SmartBill does when an invoice is issued). */
const seriesCounter = (start = 8) => {
  const state = { next: start };
  return { state, handler: () => ({ body: { errorText: '', list: [{ name: 'EXP', nextNumber: state.next, type: 'f' }] } }) };
};

test('timeout on create after which the series counter moved → INVOICE_STATUS_UNKNOWN, not retryable', async () => {
  const counter = seriesCounter(8);
  const { ctx } = ctxWith(router({
    'GET /series': counter.handler,
    'POST /invoice/v2': () => {
      counter.state.next = 9; // SmartBill issued the invoice, but the answer never arrived
      return new ProcessingError({ code: 'PROVIDER_TIMEOUT', message: 'timeout', retryable: true, provider: 'SmartBill' });
    },
  }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.equal(err.code, 'INVOICE_STATUS_UNKNOWN');
    assert.equal(err.retryable, false);
    assert.match(ro(err).hint, /Verifică în SmartBill/);
    assert.match(ro(err).message, /probabil EXP 8/);
    return true;
  });
});

test('timeout on create with the series counter unchanged → nothing was issued, retryable', async () => {
  const counter = seriesCounter(8);
  const { ctx, calls } = ctxWith(router({
    'GET /series': counter.handler,
    'POST /invoice/v2': () => new ProcessingError({ code: 'PROVIDER_TIMEOUT', message: 'SmartBill nu a răspuns în 30 secunde.', retryable: true, provider: 'SmartBill' }),
  }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.equal(err.code, 'PROVIDER_TIMEOUT');
    assert.equal(err.retryable, true);
    assert.match(ro(err).message, /nu a fost emisă/);
    return true;
  });
  const series = calls.filter((c) => c.url.pathname.endsWith('/series'));
  assert.equal(series.length, 2); // before and after the create
  assert.ok(calls.indexOf(series[0]) < calls.indexOf(invoiceCall(calls)));
});

test('HTTP 500 on create and SmartBill still down for the check → INVOICE_STATUS_UNKNOWN', async () => {
  let n = 0;
  const { ctx } = ctxWith(router({
    'GET /series': () => (++n === 1 ? { body: { errorText: '', list: [{ name: 'EXP', nextNumber: 8, type: 'f' }] } } : { status: 503, body: '<html>503</html>' }),
    'POST /invoice/v2': () => ({ status: 500, body: '<html>Internal Server Error</html>' }),
  }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'INVOICE_STATUS_UNKNOWN' && err.retryable === false);
});

test('definite rejection on create (errorText) is not second-guessed: no extra /series check', async () => {
  const { ctx, calls } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body: { errorText: 'Seria nu a fost gasita! Folositi o serie creata in contul de cloud.' } }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'INVOICE_SERIES_NOT_FOUND');
  assert.equal(calls.filter((c) => c.url.pathname.endsWith('/series')).length, 1);
});

test('getPdf returns a Buffer; uses query params and Accept: application/octet-stream', async () => {
  const pdf = Buffer.from('%PDF-1.4\n%fake\n');
  const { ctx, calls } = ctxWith(() => ({ body: pdf }));
  const out = await smartbill.getPdf(ctx, { series: 'EXP', number: '0007' });
  assert.ok(Buffer.isBuffer(out));
  assert.equal(out.toString(), pdf.toString());
  const c = calls[0];
  assert.equal(c.url.pathname, '/SBORO/api/invoice/pdf');
  assert.equal(c.url.searchParams.get('cif'), 'RO12345678');
  assert.equal(c.url.searchParams.get('seriesname'), 'EXP');
  assert.equal(c.url.searchParams.get('number'), '0007');
  assert.equal(c.headers.Accept, 'application/octet-stream');
  assert.equal(c.opts.responseType, 'buffer');
});

test('getPdf: 502 (SmartBill\'s "invoice not found") → INVOICE_NOT_FOUND', async () => {
  const { ctx } = ctxWith(() => ({ status: 502, body: Buffer.from('<html>502 Bad Gateway</html>') }));
  await assert.rejects(smartbill.getPdf(ctx, { series: 'EXP', number: '9999' }), (err) => err.code === 'INVOICE_NOT_FOUND');
});

test('cancelInvoice uses PUT /invoice/cancel with query params', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { errorText: '', message: 'Factura cu seria si numarul EXP0007 a fost anulata cu succes.' } }));
  await smartbill.cancelInvoice(ctx, { series: 'EXP', number: '0007' });
  assert.equal(calls[0].method, 'PUT');
  assert.equal(calls[0].url.pathname, '/SBORO/api/invoice/cancel');
  assert.equal(calls[0].url.searchParams.get('seriesname'), 'EXP');
});

test('stornoInvoice posts to /invoice/reverse and returns the storno number', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { errorText: '', number: '0008', series: 'EXP' } }));
  const out = await smartbill.stornoInvoice(ctx, { series: 'EXP', number: '0007' });
  assert.deepEqual({ series: out.series, number: out.number }, { series: 'EXP', number: '0008' });
  assert.equal(calls[0].url.pathname, '/SBORO/api/invoice/reverse');
  assert.deepEqual(calls[0].json, { companyVatCode: 'RO12345678', seriesName: 'EXP', number: '0007' });
});

test('storno of an already reversed invoice → clear error', async () => {
  const { ctx } = ctxWith(() => ({ status: 400, body: { errorText: 'Factura este deja stornata.' } }));
  await assert.rejects(smartbill.stornoInvoice(ctx, { series: 'EXP', number: '0007' }), (err) => err.code === 'INVOICE_ALREADY_REVERSED');
});

test('registerPayment for delivered COD: Ramburs linked to the invoice', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { errorText: '' } }));
  await smartbill.registerPayment(ctx, { series: 'EXP', number: '0007', amount: 185.47, date: '2026-10-05', method: 'cod' });
  const pay = calls.find((c) => c.url.pathname === '/SBORO/api/payment');
  assert.deepEqual(pay.json, {
    companyVatCode: 'RO12345678', type: 'Ramburs', isCash: false, useInvoiceDetails: true,
    invoicesList: [{ seriesName: 'EXP', number: '0007' }], value: 185.47, issueDate: '2026-10-05',
  });
});

test('testConnection reports the configured series', async () => {
  const { ctx, calls } = ctxWith(router());
  const res = await smartbill.testConnection(ctx);
  assert.equal(res.ok, true);
  assert.match(ro(res).message, /Seria „EXP” a fost găsită/);
  const series = calls.find((c) => c.url.pathname.endsWith('/series'));
  assert.equal(series.url.searchParams.get('type'), 'f');
});

test('testConnection: unknown series → error listing the available ones', async () => {
  const { ctx } = ctxWith(router(), { series: 'NOPE' });
  await assert.rejects(smartbill.testConnection(ctx), (err) => err.code === 'INVOICE_SERIES_NOT_FOUND' && /EXP, TST/.test(ro(err).hint));
});

test('testConnection for a non-VAT-payer company', async () => {
  const { ctx } = ctxWith(router({ 'GET /tax': () => ({ status: 400, body: { errorText: 'Firma este neplatitoare de tva.' } }) }));
  const res = await smartbill.testConnection(ctx);
  assert.match(ro(res).message, /neplătitoare de TVA/);
});

test('listSeries maps the series list', async () => {
  const { ctx } = ctxWith(router());
  assert.deepEqual((await smartbill.listSeries(ctx)).map((s) => s.id), ['EXP', 'TST']);
});

// ── live-checked responses (test/fixtures/invoicing/live-responses.json) ──

import { readFileSync } from 'node:fs';
const LIVE = JSON.parse(readFileSync(new URL('./fixtures/invoicing/live-responses.json', import.meta.url), 'utf8')).smartbill;

test('live 401 body (bad e-mail/token) → AUTH_FAILED, not retryable, on testConnection and before any invoice POST', async () => {
  const { ctx, calls } = ctxWith(() => ({ status: LIVE.auth401.status, body: LIVE.auth401.body }));
  await assert.rejects(smartbill.testConnection(ctx), (err) => err.code === 'AUTH_FAILED' && err.retryable === false && /Setări → Integrări/.test(ro(err).hint));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'AUTH_FAILED' && err.retryable === false);
  assert.equal(invoiceCall(calls), undefined);
});

test('live 401 body arriving with HTTP 200 would still be AUTH_FAILED (errorText is the source of truth)', async () => {
  const { ctx } = ctxWith(() => ({ status: 200, body: LIVE.auth401.body }));
  await assert.rejects(smartbill.listSeries(ctx), (err) => err.code === 'AUTH_FAILED');
});

test('live invalid_request_error without param (404/406/415) names the code, not a bogus field', async () => {
  for (const k of ['unknownPath404', 'acceptPdf406', 'formBody415']) {
    const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: LIVE[k].status, body: LIVE[k].body }) }));
    await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
      assert.equal(err.code, 'PROVIDER_REJECTED');
      assert.equal(err.retryable, false);
      assert.doesNotMatch(ro(err).message, /câmp/);
      assert.match(ro(err).message, new RegExp(`${LIVE[k].body.errors[0].code}, HTTP ${LIVE[k].status}`));
      return true;
    });
  }
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body: LIVE.unknownField400.body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => /câmp: fooBar/.test(ro(err).message));
});

// ── adversarial review fixes ──

test('card payment value = sum of rounded line totals (what SmartBill totals), not the raw order total', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = { ...b2bPaid(), lines: [{ name: 'Carte', quantity: 3, unitPrice: 33.3333, vatRate: 11, unit: 'buc' }, { name: 'Pix', quantity: 1, unitPrice: 0.995, vatRate: 21, unit: 'buc' }], total: 101 };
  await smartbill.createInvoice(ctx, inv);
  assert.equal(invoiceCall(calls).json.payment.value, 101); // 100.00 + 1.00 (0.995 → 1.00), not round(100.9949)
});

test('currency outside the SmartBill enum → clear Romanian error, no invoice call', async () => {
  const { ctx, calls } = ctxWith(router());
  await assert.rejects(smartbill.createInvoice(ctx, { ...b2c(), currency: 'BGN' }), (err) => err.code === 'INVOICE_CURRENCY_INVALID');
  assert.equal(invoiceCall(calls), undefined);
  await smartbill.createInvoice(ctx, { ...b2c(), currency: 'eur' });
  const body = invoiceCall(calls).json;
  assert.equal(body.currency, 'EUR');
  assert.ok(body.products.every((p) => p.currency === 'EUR'));
});

test('București: county sent as "Bucuresti" and sector read from the street address when city/zip lack it', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = b2c();
  inv.client = { ...inv.client, city: 'București', county: 'Municipiul București', countyCode: 'B', zip: '', address: 'Bd. Unirii 10, Sectorul 3' };
  await smartbill.createInvoice(ctx, inv);
  const client = invoiceCall(calls).json.client;
  assert.equal(client.county, 'Bucuresti');
  assert.equal(client.city, 'Sector 3');
});

test('VAT-rate cache is per SmartBill account: another e-mail on the same CIF reads /tax again', async () => {
  const { ctx, calls } = ctxWith(router());
  await smartbill.createInvoice(ctx, b2c());
  await smartbill.createInvoice({ ...ctx, credentials: { email: 'alt@firma.ro', token: 'xyz' } }, b2c());
  assert.equal(calls.filter((c) => c.url.pathname.endsWith('/tax')).length, 2);
});

test('registerPayment: a UTC timestamp becomes the Bucharest calendar day', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { errorText: '' } }));
  await smartbill.registerPayment(ctx, { series: 'EXP', number: '0007', amount: 10, date: '2026-10-01T22:30:00.000Z', method: 'cod' });
  assert.equal(calls.find((c) => c.method === 'POST').json.issueDate, '2026-10-02');
});

test('registerPayment: amount 0 → no call; already fully paid invoice → idempotent no-op', async () => {
  const zero = ctxWith(() => { throw new Error('no call expected'); });
  assert.deepEqual(await smartbill.registerPayment(zero.ctx, { series: 'EXP', number: '0007', amount: 0, method: 'cod' }), { skipped: true });
  const paid = ctxWith((c) => (c.method === 'POST' ? { status: 400, body: { errorText: 'Factura este incasata sau stornata in totalitate.' } } : { body: { errorText: '' } }));
  assert.deepEqual(await smartbill.registerPayment(paid.ctx, { series: 'EXP', number: '0007', amount: 10, method: 'cod' }), { alreadyPaid: true });
});

test('registerPayment: checks /invoice/paymentstatus first — fully paid → no call; partly paid → only the rest', async () => {
  const status = (unpaidAmount) => (c) => (c.url.pathname.endsWith('/paymentstatus')
    ? { body: { errorText: '', invoiceTotalAmount: 185.47, paidAmount: round2(185.47 - unpaidAmount), unpaidAmount, paid: unpaidAmount === 0 } }
    : { body: { errorText: '' } });
  const round2 = (n) => Math.round(n * 100) / 100;
  const paid = ctxWith(status(0));
  assert.deepEqual(await smartbill.registerPayment(paid.ctx, { series: 'EXP', number: '0007', amount: 185.47, method: 'cod' }), { alreadyPaid: true });
  assert.equal(paid.calls.filter((c) => c.method === 'POST').length, 0);
  assert.equal(paid.calls[0].url.searchParams.get('number'), '0007'); // leading zeros kept
  const part = ctxWith(status(85.47));
  await smartbill.registerPayment(part.ctx, { series: 'EXP', number: '0007', amount: 185.47, method: 'cod' });
  assert.equal(part.calls.find((c) => c.method === 'POST').json.value, 85.47);
});

// ── documented success shapes (test/fixtures/invoicing/smartbill-documented-success.json — official spec, see _source) ──

const DOC = JSON.parse(readFileSync(new URL('./fixtures/invoicing/smartbill-documented-success.json', import.meta.url), 'utf8'));

/** Router answering with the spec's documented bodies. */
const docRouter = (overrides = {}) => router({
  'GET /tax': () => ({ body: DOC.getTax }),
  'GET /series': () => ({ body: { ...DOC.getSeries_invoice, list: [{ name: 'ff', nextNumber: 7, type: 'f' }] } }),
  'POST /invoice/v2': () => ({ body: DOC.createInvoiceV2_success }),
  ...overrides,
});

test('spec: createInvoiceV2 success → { series, number, url = documentViewUrl (public), not documentUrl (editor) }', async () => {
  const { ctx } = ctxWith(docRouter(), { series: 'ff' });
  const res = await smartbill.createInvoice(ctx, b2c());
  assert.deepEqual({ series: res.series, number: res.number, url: res.url },
    { series: 'ff', number: '0007', url: DOC.createInvoiceV2_success.documentViewUrl });
});

test('spec: createInvoiceV2 success without documentViewUrl → falls back to documentUrl; empty "url" (payment URL) is ignored', async () => {
  const { documentViewUrl, ...noView } = DOC.createInvoiceV2_success;
  const { ctx } = ctxWith(docRouter({ 'POST /invoice/v2': () => ({ body: noView }) }), { series: 'ff' });
  const res = await smartbill.createInvoice(ctx, b2c());
  assert.equal(res.url, DOC.createInvoiceV2_success.documentUrl);
});

test('spec: getInvoicePdf binary → PDF Buffer', async () => {
  const pdf = Buffer.from('%PDF-1.4\n% TEST EXPEDO\n');
  const { ctx } = ctxWith(() => ({ body: pdf }));
  const out = await smartbill.getPdf(ctx, { series: 'ff', number: '0007' });
  assert.equal(out.subarray(0, 4).toString('latin1'), '%PDF');
});

test('spec: createStornoInvoice → { series, number, url } of the storno; success without number → error, no blind retry', async () => {
  const { ctx } = ctxWith(() => ({ body: DOC.createStornoInvoice }));
  const out = await smartbill.stornoInvoice(ctx, { series: 'SERIA_FACTURII', number: '3738' });
  assert.deepEqual(out, { series: 'SERIA_FACTURII', number: '3739', url: DOC.createStornoInvoice.documentViewUrl });
  const b = ctxWith(() => ({ body: { errorText: '', message: '', number: '', series: '', url: '' } }));
  await assert.rejects(smartbill.stornoInvoice(b.ctx, { series: 'ff', number: '0007' }), (err) => err.code === 'PROVIDER_REJECTED' && !err.retryable);
});

test('spec: cancelInvoice success and "deja anulata" (idempotent 200) both resolve', async () => {
  for (const body of Object.values(DOC.cancelInvoice)) {
    const { ctx } = ctxWith(() => ({ body }));
    await smartbill.cancelInvoice(ctx, { series: 'fac', number: '3744' });
  }
});

test('spec: paymentstatus (unpaid 121) + createPayment bodies → payment of what is unpaid, resolves for both response kinds', async () => {
  for (const payBody of Object.values(DOC.createPayment)) {
    const { ctx, calls } = ctxWith((c) => (c.url.pathname.endsWith('/invoice/paymentstatus') ? { body: DOC.getInvoicePaymentStatus } : { body: payBody }));
    assert.deepEqual(await smartbill.registerPayment(ctx, { series: 'ff', number: '0007', amount: 150, method: 'cod' }), {});
    assert.equal(calls.find((c) => c.url.pathname.endsWith('/payment')).json.value, 121);
  }
});

test('spec: /tax example — 21/11 map to Normala/Redusa; 0% picks SDD over Taxare inversa, Taxare inversa only when alone', async () => {
  const only = ctxWith(docRouter(), { series: 'ff' });
  const inv = b2c();
  inv.lines[1].vatRate = 0;
  await smartbill.createInvoice(only.ctx, inv);
  const ps = invoiceCall(only.calls).json.products;
  assert.deepEqual(ps.map((p) => [p.taxName, p.taxPercentage]), [['Normala', 21], ['Taxare inversa', 0], ['Normala', 21]]);
  const withSdd = ctxWith(docRouter({ 'GET /tax': () => ({ body: { ...DOC.getTax, taxes: [...DOC.getTax.taxes, { name: 'SDD', percentage: 0 }] } }) }), { series: 'ff' });
  await smartbill.createInvoice(withSdd.ctx, inv);
  assert.equal(invoiceCall(withSdd.calls).json.products[1].taxName, 'SDD');
});

test('spec: /series examples → listSeries keeps invoice series with nextNumber; testConnection finds "fac"', async () => {
  const { ctx } = ctxWith(router({ 'GET /series': () => ({ body: DOC.getSeries_all }), 'GET /tax': () => ({ body: DOC.getTax }) }), { series: 'fac' });
  assert.deepEqual(await smartbill.listSeries(ctx), [{ id: 'fac', name: 'fac', nextNumber: 3821 }]);
  const res = await smartbill.testConnection(ctx);
  assert.equal(res.ok, true);
  assert.match(ro(res).message, /fac/);
});
