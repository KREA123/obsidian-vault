import { test } from 'node:test';
import assert from 'node:assert/strict';
import oblio from '../src/invoicing/oblio.js';
import { ProcessingError, authError } from '../src/core/errors.js';

// ── fakes ──────────────────────────────────────────────────────────────────

function fakeHttp(handler) {
  const calls = [];
  const http = async (provider, url, opts = {}) => {
    const call = { provider, url: new URL(url), method: opts.method || 'GET', headers: opts.headers || {}, json: opts.json, body: opts.body, opts };
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

let tokenSeq = 0;
const TOKEN = () => ({ access_token: `tok${++tokenSeq}`, expires_in: '3600', token_type: 'Bearer', scope: '', request_time: '1759400000' });
const INVOICE_OK = { status: 200, statusMessage: 'Success', data: { seriesName: 'FCT', number: '0053', link: 'https://www.oblio.eu/utils/show_file/?ic=1&id=2&it=abc' } };

const isToken = (c) => c.url.pathname === '/api/authorize/token';
const nonToken = (calls) => calls.filter((c) => !isToken(c));

function ctxWith(handler, settings = {}, cache = fakeCache()) {
  const { http, calls } = fakeHttp((c, all) => (isToken(c) ? { body: TOKEN() } : handler(c, all)));
  return {
    ctx: {
      credentials: { email: 'office@magazin.ro', secret: ' 1edd9e4f6abc ' },
      settings: { cif: 'RO37311090', series: 'FCT', vatPayer: true, ...settings },
      http,
      cache,
      log: () => {},
    },
    calls,
  };
}

const router = (overrides = {}) => (c) => {
  const key = `${c.method} ${c.url.pathname.replace('/api', '')}`;
  if (overrides[key]) return overrides[key](c);
  if (key === 'POST /docs/invoice') return { body: INVOICE_OK };
  if (key === 'GET /nomenclature/companies') return { body: { status: 200, data: [{ cif: 'RO37311090', company: 'MAGAZIN SRL', userTypeAccess: 'admin' }] } };
  if (key === 'GET /nomenclature/series') return { body: { status: 200, data: [{ type: 'Factura', name: 'FCT', next: '0054', default: true }, { type: 'Proforma', name: 'PR', next: '0008' }] } };
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
    { name: 'Transport', quantity: 1, unitPrice: 19.99, vatRate: 21, unit: 'buc', isShipping: true },
  ],
  total: 139.97,
  paid: false,
  paymentMethod: 'cod',
  mentions: 'Comanda #1024',
});

const invoiceCall = (calls) => calls.find((c) => c.method === 'POST' && c.url.pathname === '/api/docs/invoice');

// ── token ──────────────────────────────────────────────────────────────────

test('token: client credentials POST, then Bearer on API calls', async () => {
  const { ctx, calls } = ctxWith(router());
  await oblio.createInvoice(ctx, b2c());
  const t = calls.find(isToken);
  assert.equal(t.method, 'POST');
  assert.equal(t.url.href, 'https://www.oblio.eu/api/authorize/token');
  assert.equal(t.headers['Content-Type'], 'application/x-www-form-urlencoded');
  const form = new URLSearchParams(t.body);
  assert.equal(form.get('client_id'), 'office@magazin.ro');
  assert.equal(form.get('client_secret'), '1edd9e4f6abc', 'secret trimmed');
  assert.equal(form.get('grant_type'), 'client_credentials');
  assert.match(invoiceCall(calls).headers.Authorization, /^Bearer tok\d+$/);
});

test('token is cached until expiry (one token request for several calls)', async () => {
  const { ctx, calls } = ctxWith(router());
  await oblio.createInvoice(ctx, b2c());
  await oblio.createInvoice(ctx, b2c());
  await oblio.listSeries(ctx);
  assert.equal(calls.filter(isToken).length, 1);
  const auths = new Set(nonToken(calls).map((c) => c.headers.Authorization));
  assert.equal(auths.size, 1);
});

test('expired cached token: a fresh one is requested', async () => {
  const cache = fakeCache();
  const { ctx, calls } = ctxWith(router(), {}, cache);
  await oblio.listSeries(ctx);
  for (const [k, v] of cache.map) if (k.startsWith('oblio:token:')) cache.map.set(k, { ...v, expiresAt: Date.now() - 1 });
  await oblio.listSeries(ctx);
  assert.equal(calls.filter(isToken).length, 2);
});

test('401 with a cached token → refresh once and retry', async () => {
  let n = 0;
  const { ctx, calls } = ctxWith(router({ 'GET /nomenclature/series': () => (++n === 1 ? { status: 401, body: { status: 401, statusMessage: 'Invalid token' } } : { body: { status: 200, data: [{ type: 'Factura', name: 'FCT' }] } }) }));
  const series = await oblio.listSeries(ctx);
  assert.deepEqual(series.map((s) => s.id), ['FCT']);
  assert.equal(calls.filter(isToken).length, 2);
  const [first, second] = nonToken(calls);
  assert.notEqual(first.headers.Authorization, second.headers.Authorization);
});

test('bad credentials at /authorize/token → AUTH_FAILED', async () => {
  const { http } = fakeHttp(() => ({ status: 400, body: { status: 400, statusMessage: 'Invalid client' } }));
  const ctx = { credentials: { email: 'x@y.ro', secret: 'bad' }, settings: { cif: 'RO1', series: 'FCT' }, http, cache: fakeCache() };
  await assert.rejects(oblio.testConnection(ctx), (err) => err.code === 'AUTH_FAILED' && err.provider === 'Oblio');
});

// ── createInvoice ──────────────────────────────────────────────────────────

test('createInvoice B2C: VAT-inclusive prices, Marfa vs Serviciu, idempotency key from the order', async () => {
  const { ctx, calls } = ctxWith(router());
  const res = await oblio.createInvoice(ctx, b2c());
  assert.deepEqual({ series: res.series, number: res.number, url: res.url }, { series: 'FCT', number: '0053', url: INVOICE_OK.data.link });

  const body = invoiceCall(calls).json;
  assert.equal(body.cif, 'RO37311090');
  assert.equal(body.seriesName, 'FCT');
  assert.equal(body.issueDate, '2026-10-02');
  assert.equal(body.dueDate, '2026-10-02');
  assert.equal(body.language, 'RO');
  assert.equal(body.currency, 'RON');
  assert.equal(body.precision, 2);
  assert.equal(body.mentions, 'Comanda #1024');
  assert.equal(body.sendEmail, 0);
  assert.equal(body.useStock, 0);
  assert.equal(body.idempotencyKey, 'expedo-1024');
  assert.equal(body.collect, undefined, 'COD not collected at issue time');

  assert.deepEqual(body.client, {
    cif: '', name: 'Ion Popescu', address: 'Str. Lalelelor 1', state: 'Cluj', city: 'Cluj-Napoca', country: 'Romania',
    email: 'ion@example.com', phone: '0722000000', vatPayer: 0, save: 1,
  });

  const [tshirt, ship] = body.products;
  assert.deepEqual(tshirt, {
    name: 'Tricou negru (M)', code: 'TR-M', description: '', price: 59.99, measuringUnit: 'buc', currency: 'RON',
    vatIncluded: 1, quantity: 2, productType: 'Marfa', vatName: '', vatPercentage: 21,
  });
  assert.equal(ship.productType, 'Serviciu');
  assert.equal(ship.price, 19.99);
  assert.equal(ship.vatIncluded, 1);
});

test('createInvoice B2B paid by card: company client and collect block', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = { ...b2c(), paid: true, paymentMethod: 'card' };
  inv.client = { ...inv.client, name: 'ACME SRL', isCompany: true, vatCode: 'ro 12345678', regCom: 'J12/123/2020' };
  await oblio.createInvoice(ctx, inv);
  const body = invoiceCall(calls).json;
  assert.equal(body.client.cif, 'RO12345678');
  assert.equal(body.client.vatPayer, 1);
  assert.equal(body.client.rc, 'J12/123/2020');
  assert.deepEqual(body.collect, { type: 'Card', documentNumber: '#1024' });
});

test('non-VAT payer: no VAT name/percentage sent; 0% lines as SDD for VAT payers', async () => {
  const a = ctxWith(router(), { vatPayer: false });
  await oblio.createInvoice(a.ctx, b2c());
  for (const p of invoiceCall(a.calls).json.products) {
    assert.equal('vatName' in p, false);
    assert.equal('vatPercentage' in p, false);
    assert.equal(p.vatIncluded, 1);
  }
  const b = ctxWith(router());
  const inv = b2c();
  inv.lines[0].vatRate = 0;
  await oblio.createInvoice(b.ctx, inv);
  const p0 = invoiceCall(b.calls).json.products[0];
  assert.equal(p0.vatName, 'SDD');
  assert.equal(p0.vatPercentage, 0);
});

test('stock: management on goods only; e-mail flag; București sector', async () => {
  const { ctx, calls } = ctxWith(router(), { useStock: true, management: 'Magazin', sendEmail: true });
  const inv = b2c();
  inv.client = { ...inv.client, city: 'București', county: 'București', countyCode: 'B', zip: '060042' };
  await oblio.createInvoice(ctx, inv);
  const body = invoiceCall(calls).json;
  assert.equal(body.useStock, 1);
  assert.equal(body.sendEmail, 1);
  assert.equal(body.products[0].management, 'Magazin');
  assert.equal(body.products[1].management, undefined);
  assert.equal(body.client.city, 'SECTOR 6');
});

test('precision follows unit prices with more than 2 decimals', async () => {
  const { ctx, calls } = ctxWith(router());
  const inv = b2c();
  inv.lines[0] = { ...inv.lines[0], unitPrice: 33.3333, quantity: 3 };
  await oblio.createInvoice(ctx, inv);
  assert.equal(invoiceCall(calls).json.precision, 4);
});

// ── errors ─────────────────────────────────────────────────────────────────

test('series error (HTTP 400 statusMessage) → INVOICE_SERIES_NOT_FOUND with hint', async () => {
  const body = { status: 400, statusMessage: 'Seria FCT nu exista', data: [] };
  const { ctx } = ctxWith(router({ 'POST /docs/invoice': () => ({ status: 400, body }) }));
  await assert.rejects(oblio.createInvoice(ctx, b2c()), (err) => {
    assert.ok(err instanceof ProcessingError);
    assert.equal(err.code, 'INVOICE_SERIES_NOT_FOUND');
    assert.match(err.message, /Seria FCT nu exista/);
    assert.match(err.hint, /Setări → Facturare/);
    assert.deepEqual(err.details, body);
    return true;
  });
});

test('other rejection keeps Oblio\'s Romanian message; 5xx stays retryable', async () => {
  const a = ctxWith(router({ 'POST /docs/invoice': () => ({ status: 400, body: { status: 400, statusMessage: 'Numele clientului este obligatoriu' } }) }));
  await assert.rejects(oblio.createInvoice(a.ctx, b2c()), (err) => err.code === 'PROVIDER_REJECTED' && /Numele clientului/.test(err.message) && !err.retryable);
  const b = ctxWith(router({ 'POST /docs/invoice': () => ({ status: 503, body: 'Service Unavailable' }) }));
  await assert.rejects(oblio.createInvoice(b.ctx, b2c()), (err) => err.retryable === true);
});

test('VAT error → hint to check VAT rates in Oblio', async () => {
  const { ctx } = ctxWith(router({ 'POST /docs/invoice': () => ({ status: 400, body: { status: 400, statusMessage: 'Cota TVA 11% nu exista' } }) }));
  await assert.rejects(oblio.createInvoice(ctx, b2c()), (err) => err.code === 'VAT_RATE_NOT_DEFINED' && /Oblio/.test(err.hint));
});

// ── other operations ───────────────────────────────────────────────────────

test('getPdf: reads the link from GET /docs/invoice and returns a Buffer', async () => {
  const pdf = Buffer.from('%PDF-1.4 fake');
  const { ctx, calls } = ctxWith((c) => {
    if (c.url.pathname === '/api/docs/invoice') return { body: { status: 200, data: { seriesName: 'FCT', number: '0053', link: 'https://www.oblio.eu/utils/show_file/?id=2' } } };
    if (c.url.pathname === '/utils/show_file/') return { body: pdf };
    throw new Error('unexpected ' + c.url.href);
  });
  const out = await oblio.getPdf(ctx, { series: 'FCT', number: '0053' });
  assert.ok(Buffer.isBuffer(out));
  assert.equal(out.toString(), pdf.toString());
  const q = nonToken(calls)[0].url.searchParams;
  assert.deepEqual([q.get('cif'), q.get('seriesName'), q.get('number')], ['RO37311090', 'FCT', '0053']);
  assert.equal(nonToken(calls)[1].opts.responseType, 'buffer');
});

test('cancelInvoice → PUT /docs/invoice/cancel', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { status: 200, statusMessage: 'Documentul a fost anulat.' } }));
  await oblio.cancelInvoice(ctx, { series: 'FCT', number: '0053' });
  const c = nonToken(calls)[0];
  assert.equal(c.method, 'PUT');
  assert.equal(c.url.pathname, '/api/docs/invoice/cancel');
  assert.deepEqual(c.json, { cif: 'RO37311090', seriesName: 'FCT', number: '0053' });
});

test('stornoInvoice → POST /docs/invoice with referenceDocument refund', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { status: 200, data: { seriesName: 'FCT', number: '0054', link: 'x' } } }));
  const out = await oblio.stornoInvoice(ctx, { series: 'FCT', number: '0053' });
  assert.deepEqual({ series: out.series, number: out.number }, { series: 'FCT', number: '0054' });
  const body = invoiceCall(calls).json;
  assert.deepEqual(body.referenceDocument, { type: 'Factura', seriesName: 'FCT', number: '0053', refund: 1 });
  assert.equal(body.cif, 'RO37311090');
  assert.equal(body.seriesName, 'FCT');
  assert.equal(body.idempotencyKey, 'expedo-storno-FCT0053');
});

test('registerPayment for COD → PUT /docs/invoice/collect with Ramburs', async () => {
  const { ctx, calls } = ctxWith(() => ({ body: { status: 200, data: {} } }));
  await oblio.registerPayment(ctx, { series: 'FCT', number: '0053', amount: 139.97, date: '2026-10-05', method: 'cod', reference: '#1024' });
  const c = nonToken(calls)[0];
  assert.equal(c.method, 'PUT');
  assert.equal(c.url.pathname, '/api/docs/invoice/collect');
  assert.deepEqual(c.json, {
    cif: 'RO37311090', seriesName: 'FCT', number: '0053',
    collect: { type: 'Ramburs', documentNumber: '#1024', value: 139.97, issueDate: '2026-10-05' },
  });
});

test('testConnection: finds the company and the series', async () => {
  const { ctx } = ctxWith(router());
  const res = await oblio.testConnection(ctx);
  assert.equal(res.ok, true);
  assert.match(res.message, /MAGAZIN SRL/);
  assert.match(res.message, /Seria „FCT” a fost găsită/);
});

test('testConnection: CIF compared without RO prefix; unknown series → error', async () => {
  const a = ctxWith(router(), { cif: '37311090', series: 'XYZ' });
  await assert.rejects(oblio.testConnection(a.ctx), (err) => err.code === 'INVOICE_SERIES_NOT_FOUND' && /FCT/.test(err.hint));
  const b = ctxWith(router(), { cif: 'RO999' });
  await assert.rejects(oblio.testConnection(b.ctx), (err) => err.code === 'INVOICING_COMPANY_NOT_FOUND' && /MAGAZIN SRL/.test(err.hint));
});

test('listSeries returns invoice series only', async () => {
  const { ctx } = ctxWith(router());
  assert.deepEqual((await oblio.listSeries(ctx)).map((s) => s.name), ['FCT']);
});

test('adapter fields', () => {
  assert.deepEqual(oblio.credentialFields.map((f) => f.key), ['email', 'secret']);
  const keys = oblio.settingsFields.map((f) => f.key);
  for (const k of ['cif', 'series', 'vatPayer', 'sendEmail', 'useStock', 'management', 'language']) assert.ok(keys.includes(k), k);
});
