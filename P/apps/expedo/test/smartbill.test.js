import { test } from 'node:test';
import assert from 'node:assert/strict';
import smartbill from '../src/invoicing/smartbill.js';
import { ProcessingError, authError } from '../src/core/errors.js';

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

test('adapter shape and Romanian field labels', () => {
  assert.equal(smartbill.id, 'smartbill');
  for (const k of ['testConnection', 'createInvoice', 'getPdf', 'cancelInvoice', 'stornoInvoice', 'registerPayment', 'listSeries']) {
    assert.equal(typeof smartbill[k], 'function', k);
  }
  assert.deepEqual(smartbill.credentialFields.map((f) => f.key), ['email', 'token']);
  const keys = smartbill.settingsFields.map((f) => f.key);
  for (const k of ['cif', 'series', 'vatPayer', 'sendEmail', 'useStock', 'warehouseName', 'language']) assert.ok(keys.includes(k), k);
  assert.ok(smartbill.settingsFields.every((f) => f.label && /[a-zăâîșț]/i.test(f.label)));
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

test('non-VAT payer: no /tax lookup, 0% and no taxName', async () => {
  const { ctx, calls } = ctxWith(router(), { vatPayer: false });
  await smartbill.createInvoice(ctx, b2c());
  assert.equal(calls.filter((c) => c.url.pathname.endsWith('/tax')).length, 0);
  for (const p of invoiceCall(calls).json.products) {
    assert.equal(p.taxPercentage, 0);
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
    assert.match(err.message, /11%/);
    assert.match(err.hint, /SmartBill.*Cote TVA/);
    return true;
  });
  assert.equal(invoiceCall(calls), undefined);
});

test('errorText "Seria nu a fost gasita" (HTTP 400) → series error with settings hint', async () => {
  const body = { errorText: 'Seria nu a fost gasita! Folositi o serie creata in contul de cloud.', number: '', series: '' };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.equal(err.code, 'INVOICE_SERIES_NOT_FOUND');
    assert.match(err.message, /Seria nu a fost gasita/);
    assert.match(err.hint, /Setări → Facturare/);
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
    assert.doesNotMatch(err.message, /</);
    return true;
  });
});

test('VAT rate rejected by SmartBill on create → hint to add it in SmartBill', async () => {
  const body = { errorText: 'Cota tva a produsului Tricou nu a fost gasita pe server!' };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'VAT_RATE_NOT_DEFINED' && /Configurare → Cote TVA/.test(err.hint));
});

test('bad credentials → AUTH_FAILED', async () => {
  const body = { successfully: false, errorText: 'Autentificare esuata. Va rugam verificati datele si incercati din nou.' };
  const { ctx } = ctxWith(() => ({ status: 401, body }));
  await assert.rejects(smartbill.testConnection(ctx), (err) => err.code === 'AUTH_FAILED' && err.provider === 'SmartBill');
});

test('unknown field (json_mapping_error, no errorText) is reported as an integration error', async () => {
  const body = { status: 400, type: 'invalid_request_error', errors: [{ code: 'json_mapping_error', message: 'Unrecognized property: zzz.', param: 'zzz' }] };
  const { ctx } = ctxWith(router({ 'POST /invoice/v2': () => ({ status: 400, body }) }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => err.code === 'PROVIDER_REJECTED' && /zzz/.test(err.message));
});

test('timeout on create is NOT retryable (no idempotency key in SmartBill)', async () => {
  const { ctx } = ctxWith(router({
    'POST /invoice/v2': () => new ProcessingError({ code: 'PROVIDER_TIMEOUT', message: 'timeout', retryable: true, provider: 'SmartBill' }),
  }));
  await assert.rejects(smartbill.createInvoice(ctx, b2c()), (err) => {
    assert.equal(err.code, 'INVOICE_STATUS_UNKNOWN');
    assert.equal(err.retryable, false);
    assert.match(err.hint, /Verifică în SmartBill/);
    return true;
  });
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
  assert.equal(calls[0].url.pathname, '/SBORO/api/payment');
  assert.deepEqual(calls[0].json, {
    companyVatCode: 'RO12345678', type: 'Ramburs', isCash: false, useInvoiceDetails: true,
    invoicesList: [{ seriesName: 'EXP', number: '0007' }], value: 185.47, issueDate: '2026-10-05',
  });
});

test('testConnection reports the configured series', async () => {
  const { ctx, calls } = ctxWith(router());
  const res = await smartbill.testConnection(ctx);
  assert.equal(res.ok, true);
  assert.match(res.message, /Seria „EXP” a fost găsită/);
  const series = calls.find((c) => c.url.pathname.endsWith('/series'));
  assert.equal(series.url.searchParams.get('type'), 'f');
});

test('testConnection: unknown series → error listing the available ones', async () => {
  const { ctx } = ctxWith(router(), { series: 'NOPE' });
  await assert.rejects(smartbill.testConnection(ctx), (err) => err.code === 'INVOICE_SERIES_NOT_FOUND' && /EXP, TST/.test(err.hint));
});

test('testConnection for a non-VAT-payer company', async () => {
  const { ctx } = ctxWith(router({ 'GET /tax': () => ({ status: 400, body: { errorText: 'Firma este neplatitoare de tva.' } }) }));
  const res = await smartbill.testConnection(ctx);
  assert.match(res.message, /neplătitoare de TVA/);
});

test('listSeries maps the series list', async () => {
  const { ctx } = ctxWith(router());
  assert.deepEqual((await smartbill.listSeries(ctx)).map((s) => s.id), ['EXP', 'TST']);
});
