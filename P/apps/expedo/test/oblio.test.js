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
    vatIncluded: 1, quantity: 2, productType: 'Marfa', save: 0, vatName: '', vatPercentage: 21,
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

test('non-VAT payer: vatName "" + vatPercentage null, exactly as the official plugin; 0% lines as SDD for VAT payers', async () => {
  const a = ctxWith(router(), { vatPayer: false });
  await oblio.createInvoice(a.ctx, b2c());
  for (const p of invoiceCall(a.calls).json.products) {
    assert.equal(p.vatName, '');
    assert.equal(p.vatPercentage, null);
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
  assert.equal(nonToken(calls)[0].url.pathname, '/api/docs/invoice'); // existing collects checked first
  const c = nonToken(calls)[1];
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

// ── live-checked responses (test/fixtures/invoicing/live-responses.json) ──

import { readFileSync } from 'node:fs';
const LIVE = JSON.parse(readFileSync(new URL('./fixtures/invoicing/live-responses.json', import.meta.url), 'utf8')).oblio;

/** ctx whose token endpoint answers with `tokenOut` and API calls with `handler`. */
function rawCtx(tokenOut, handler, credentials = { email: 'nu-exista@example.invalid', secret: 'x' }) {
  const { http, calls } = fakeHttp((c, all) => (isToken(c) ? tokenOut(c) : handler(c, all)));
  return { ctx: { credentials, settings: { cif: 'RO37311090', series: 'FCT' }, http, cache: fakeCache(), log: () => {} }, calls };
}

test('live: token 400 invalid_client → AUTH_FAILED, not retryable, no API call', async () => {
  const { ctx, calls } = rawCtx(() => ({ status: 400, body: LIVE.tokenBadClient.body }), () => { throw new Error('no API call expected'); });
  await assert.rejects(oblio.testConnection(ctx), (err) => err.code === 'AUTH_FAILED' && err.retryable === false && err.provider === 'Oblio');
  await assert.rejects(oblio.createInvoice(ctx, b2c()), (err) => err.code === 'AUTH_FAILED');
  assert.equal(nonToken(calls).length, 0);
});

test('live: 401 "access token provided is invalid" twice (even after a fresh token) → AUTH_FAILED', async () => {
  const { ctx, calls } = ctxWith(() => ({ status: 401, body: LIVE.invalidToken.body }));
  await assert.rejects(oblio.createInvoice(ctx, b2c()), (err) => err.code === 'AUTH_FAILED' && err.retryable === false);
  assert.equal(calls.filter(isToken).length, 2); // refreshed once, then gave up
  assert.equal(nonToken(calls).length, 2);
});

test('live: unknown path answers HTTP 200 HTML → retryable error, never "success without number"', async () => {
  const { ctx } = ctxWith(() => ({ status: 200, body: LIVE.unknownPath.bodyStart }));
  await assert.rejects(oblio.getPdf(ctx, { series: 'FCT', number: '0053' }), (err) => err.code === 'PROVIDER_DOWN' && err.retryable === true);
  const t = rawCtx(() => ({ status: 200, body: '<html>maintenance</html>' }), () => ({ body: {} }));
  await assert.rejects(oblio.testConnection(t.ctx), (err) => err.code === 'PROVIDER_DOWN' && err.retryable === true);
});

// ── adversarial review fixes ──

test('token cache: two Oblio accounts sharing one cache never share a token', async () => {
  const cache = fakeCache();
  const seen = [];
  const handler = (c) => { seen.push(c.headers.Authorization); return router()(c); };
  const tokens = { 'a@x.ro': 'tokA', 'b@x.ro': 'tokB' };
  const mk = (email) => {
    const { http } = fakeHttp((c) => (isToken(c) ? { body: { access_token: tokens[new URLSearchParams(c.body).get('client_id')], expires_in: '3600' } } : handler(c)));
    return { credentials: { email, secret: `secret-${email}` }, settings: { cif: 'RO37311090', series: 'FCT' }, http, cache, log: () => {} };
  };
  await oblio.createInvoice(mk('a@x.ro'), b2c());
  await oblio.createInvoice(mk('b@x.ro'), b2c());
  await oblio.createInvoice(mk('a@x.ro'), b2c());
  assert.deepEqual(seen, ['Bearer tokA', 'Bearer tokB', 'Bearer tokA']);
});

test('idempotencyKey: "#1024-2" after a storno is used (sanitized); falls back to the order reference', async () => {
  const a = ctxWith(router());
  await oblio.createInvoice(a.ctx, { ...b2c(), idempotencyKey: '#1024-2' });
  assert.equal(invoiceCall(a.calls).json.idempotencyKey, 'expedo-1024-2');
  const b = ctxWith(router());
  await oblio.createInvoice(b.ctx, b2c());
  assert.equal(invoiceCall(b.calls).json.idempotencyKey, 'expedo-1024');
});

test('timeout on create stays retryable and the retry carries the same idempotencyKey (Oblio dedupes)', async () => {
  let n = 0;
  const { ctx, calls } = ctxWith(router({
    'POST /docs/invoice': () => (++n === 1 ? new ProcessingError({ code: 'PROVIDER_TIMEOUT', message: 't', retryable: true, provider: 'Oblio' }) : { body: INVOICE_OK }),
  }));
  const inv = { ...b2c(), idempotencyKey: '#1024' };
  await assert.rejects(oblio.createInvoice(ctx, inv), (err) => err.retryable === true);
  await oblio.createInvoice(ctx, inv);
  const posts = calls.filter((c) => c.method === 'POST' && c.url.pathname === '/api/docs/invoice');
  assert.equal(posts[0].json.idempotencyKey, posts[1].json.idempotencyKey);
});

test('București: state "Bucuresti" and SECTOR from the street address; e-mail flag only with a client e-mail', async () => {
  const { ctx, calls } = ctxWith(router(), { sendEmail: true });
  const inv = b2c();
  inv.client = { ...inv.client, city: 'București', county: 'Municipiul București', countyCode: 'B', zip: '', address: 'Str. X 1, sector 4', email: '' };
  await oblio.createInvoice(ctx, inv);
  const body = invoiceCall(calls).json;
  assert.equal(body.client.state, 'Bucuresti');
  assert.equal(body.client.city, 'SECTOR 4');
  assert.equal(body.sendEmail, 0);
});

test('registerPayment: repeated call with the same document number → no second collect; 0 → nothing; UTC → Bucharest day', async () => {
  const dup = ctxWith((c) => (c.method === 'GET' ? { body: { status: 200, data: { collects: [{ type: 'Ramburs', number: '#1024', value: 139.97 }] } } } : { body: { status: 200, data: {} } }));
  assert.deepEqual(await oblio.registerPayment(dup.ctx, { series: 'FCT', number: '0053', amount: 139.97, method: 'cod', reference: '#1024' }), { alreadyPaid: true });
  assert.equal(nonToken(dup.calls).filter((c) => c.method === 'PUT').length, 0);

  const zero = ctxWith(() => { throw new Error('no call expected'); });
  assert.deepEqual(await oblio.registerPayment(zero.ctx, { series: 'FCT', number: '0053', amount: 0, method: 'cod', reference: '#1024' }), { skipped: true });

  const tz = ctxWith(() => ({ body: { status: 200, data: { collects: [] } } }));
  await oblio.registerPayment(tz.ctx, { series: 'FCT', number: '0053', amount: 5, date: '2026-10-01T21:15:00Z', method: 'cod', reference: 'AWB1' });
  assert.equal(nonToken(tz.calls).find((c) => c.method === 'PUT').json.collect.issueDate, '2026-10-02');
});

test('getPdf: show_file link answering with the HTML login page (seen live for a stale link) → not retryable', async () => {
  const { ctx } = ctxWith((c) => (c.url.hostname === 'www.oblio.eu' && c.url.pathname === '/api/docs/invoice'
    ? { body: { status: 200, data: { link: 'https://www.oblio.eu/utils/show_file/?ic=1&id=2&it=old' } } }
    : { body: Buffer.from('<!DOCTYPE html><html><title>Login</title>') }));
  await assert.rejects(oblio.getPdf(ctx, { series: 'FCT', number: '0053' }), (err) => err.code === 'INVOICE_PDF_UNAVAILABLE' && err.retryable === false && /direct din Oblio/.test(err.hint));
});

// ── documented success shapes (test/fixtures/invoicing/oblio-documented-success.json — oblio.eu/api + official plugin, see _source) ──

const DOC = JSON.parse(readFileSync(new URL('./fixtures/invoicing/oblio-documented-success.json', import.meta.url), 'utf8'));

test('docs: token body (expires_in as a string) is accepted and used as Bearer', async () => {
  const { http, calls } = fakeHttp((c) => (isToken(c) ? { body: DOC.token } : { body: DOC.companies }));
  const ctx = { credentials: { email: 'test@expedo.ro', secret: 'x' }, settings: {}, http, cache: fakeCache(), log: () => {} };
  const res = await oblio.testConnection(ctx);
  assert.equal(res.ok, true);
  assert.equal(calls[1].headers.Authorization, `Bearer ${DOC.token.access_token}`);
});

test('docs: create invoice → { series, number with leading zeros, url = data.link } (what the official plugin stores)', async () => {
  const { ctx } = ctxWith(router({ 'POST /docs/invoice': () => ({ body: DOC.createInvoice }) }));
  const res = await oblio.createInvoice(ctx, b2c());
  assert.deepEqual({ series: res.series, number: res.number, url: res.url }, { series: 'FCT', number: '0053', url: DOC.createInvoice.data.link });
});

test('docs: view invoice → link downloaded into a PDF Buffer', async () => {
  const pdf = Buffer.from('%PDF-1.4\n% TEST EXPEDO\n');
  const { ctx } = ctxWith((c) => (c.url.pathname === '/api/docs/invoice' ? { body: DOC.viewInvoice } : c.url.href === DOC.viewInvoice.data.link ? { body: pdf } : new Error(c.url.href)));
  const out = await oblio.getPdf(ctx, { series: 'FCT', number: '0055' });
  assert.equal(out.subarray(0, 4).toString('latin1'), '%PDF');
});

test('docs: cancel response (statusMessage "Documentul a fost anulat.") resolves', async () => {
  const { ctx } = ctxWith(() => ({ body: DOC.cancelInvoice }));
  await oblio.cancelInvoice(ctx, { series: 'FCT', number: '0055' });
});

test('docs: storno answers like a created invoice → storno { series, number, url }; no number → error', async () => {
  const { ctx } = ctxWith(() => ({ body: DOC.createInvoice }));
  assert.deepEqual(await oblio.stornoInvoice(ctx, { series: 'FCT', number: '0052' }), { series: 'FCT', number: '0053', url: DOC.createInvoice.data.link });
  const b = ctxWith(() => ({ body: { status: 200, statusMessage: 'Success', data: {} } }));
  await assert.rejects(oblio.stornoInvoice(b.ctx, { series: 'FCT', number: '0052' }), (err) => err.code === 'PROVIDER_REJECTED');
});

test('docs: collects listed on the invoice ("OP 7001") → same reference is a no-op; a new one is PUT and the documented reply (statusMessage "") resolves', async () => {
  const seen = ctxWith(() => ({ body: DOC.viewInvoice }));
  assert.deepEqual(await oblio.registerPayment(seen.ctx, { series: 'FCT', number: '0055', amount: 428.4, method: 'transfer', reference: 'OP 7001' }), { alreadyPaid: true });
  assert.equal(nonToken(seen.calls).filter((c) => c.method === 'PUT').length, 0);
  const fresh = ctxWith((c) => (c.method === 'PUT' ? { body: DOC.collect } : { body: DOC.viewInvoice }));
  assert.deepEqual(await oblio.registerPayment(fresh.ctx, { series: 'FCT', number: '0055', amount: 10, method: 'cod', reference: 'AWB123' }), {});
  assert.equal(nonToken(fresh.calls).find((c) => c.method === 'PUT').json.collect.type, 'Ramburs');
});

test('docs: companies / series / vat_rates nomenclature bodies → testConnection, listSeries, listVatRates', async () => {
  const { ctx } = ctxWith((c) => {
    const p = c.url.pathname.replace('/api', '');
    if (p === '/nomenclature/companies') return { body: DOC.companies };
    if (p === '/nomenclature/series') return { body: DOC.series };
    if (p === '/nomenclature/vat_rates') return { body: DOC.vatRates };
    return new Error(p);
  });
  const res = await oblio.testConnection(ctx);
  assert.match(res.message, /OBLIO SOFTWARE SRL/);
  assert.deepEqual(await oblio.listSeries(ctx), [{ id: 'FCT', name: 'FCT', next: '0051', default: true }]);
  assert.deepEqual((await oblio.listVatRates(ctx)).map((v) => v.percent), [19, 9, 0]);
});
