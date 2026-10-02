import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ProcessingError, authError } from '../src/core/errors.js';
import fan, { mapFanEvent, pickService, resolveFanLocality, tokenKey } from '../src/couriers/fancourier.js';
import { ro } from './helpers-i18n.js';

// ---- fake ctx: routes ctx.http calls to handlers, emulating src/lib/http.js error handling
function fakeCtx({ routes, settings = {}, credentials = { username: 'shop', password: 'secret' } }) {
  const calls = [];
  const store = new Map();
  const http = async (provider, url, opts = {}) => {
    const u = new URL(url);
    calls.push({ method: opts.method || 'GET', path: u.pathname, query: u.searchParams, url, opts });
    const key = `${opts.method || 'GET'} ${u.pathname}`;
    const handler = routes[key];
    if (!handler) throw new Error(`unexpected call ${key}`);
    const { status = 200, body } = await handler({ url: u, opts, calls });
    if (status >= 400) {
      const mapped = opts.mapError?.(status, body);
      if (mapped) throw mapped;
      if (status === 401 || status === 403) throw authError(provider, body);
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: `${provider} a refuzat`, provider, details: body });
    }
    return { status, headers: new Headers(), body };
  };
  const cache = {
    get: (k) => store.get(k),
    set: (k, v) => { store.set(k, v); },
  };
  return { ctx: { credentials, settings: { clientId: '7032158', ...settings }, http, cache, log: () => {} }, calls, store };
}

const LOCALITIES = {
  status: 'success',
  data: [
    { id: 1, name: 'Cluj-Napoca', county: 'Cluj' },
    { id: 2, name: 'Floresti', county: 'Cluj' },
    { id: 3, name: 'Bucuresti', county: 'Bucuresti' },
    { id: 4, name: 'Floresti', county: 'Prahova' },
    { id: 5, name: 'Turda', county: 'Cluj' },
    { id: 6, name: 'Campia Turzii', county: 'Cluj' },
  ],
};

const okLogin = () => ({ body: { status: 'success', data: { token: 'TOKEN-1', expiresAt: '2030-01-01 00:00:00' } } });

function baseRoutes(extra = {}) {
  return {
    'POST /login': okLogin,
    'GET /reports/localities': () => ({ body: LOCALITIES }),
    'POST /intern-awb': () => ({ body: { response: [{ awbNumber: 2228300120233, tariff: 20, vat: 3.8, errors: null }] } }),
    ...extra,
  };
}

const shipment = (over = {}) => ({
  reference: '#1024',
  recipient: {
    name: 'Ana Pop', contactPerson: 'Ana Pop', phone: '0722123456', email: 'ana@example.ro',
    county: 'Cluj', countyCode: 'CJ', city: 'Mun. Cluj Napoca', street: 'Str. Memorandumului nr. 28', zip: '400114', country: 'RO',
  },
  parcels: 1, weightKg: 1.2, envelopes: 0, cod: 149.9, currency: 'RON', declaredValue: 0, contents: 'Jucării',
  ...over,
});

const lastJson = (calls, path) => calls.filter((c) => c.path === path).at(-1).opts.json;

test('login token is cached and reused; bearer header sent', async () => {
  const { ctx, calls } = fakeCtx({ routes: baseRoutes() });
  await fan.createShipment(ctx, shipment());
  await fan.createShipment(ctx, shipment({ reference: '#1025' }));
  assert.equal(calls.filter((c) => c.path === '/login').length, 1);
  const awbCalls = calls.filter((c) => c.path === '/intern-awb');
  assert.equal(awbCalls.length, 2);
  for (const c of awbCalls) assert.equal(c.opts.headers.Authorization, 'Bearer TOKEN-1');
  // login sends credentials in a form body, not in the URL
  const login = calls.find((c) => c.path === '/login');
  assert.equal(login.query.toString(), '');
  assert.equal(login.opts.body.get('username'), 'shop');
  assert.equal(login.opts.body.get('password'), 'secret');
  // nomenclator fetched once and cached
  assert.equal(calls.filter((c) => c.path === '/reports/localities').length, 1);
});

test('expired token (401) → re-login once and retry', async () => {
  let logins = 0;
  let awbTries = 0;
  const { ctx, calls } = fakeCtx({
    routes: baseRoutes({
      'POST /login': () => { logins++; return { body: { status: 'success', data: { token: `TOKEN-${logins}` } } }; },
      'POST /intern-awb': ({ opts }) => {
        awbTries++;
        if (opts.headers.Authorization === 'Bearer TOKEN-1') return { status: 401, body: { message: 'Unauthenticated.' } };
        return { body: { response: [{ awbNumber: 111, tariff: 10, errors: null }] } };
      },
    }),
  });
  const res = await fan.createShipment(ctx, shipment());
  assert.equal(res.awb, '111');
  assert.equal(logins, 2);
  assert.equal(awbTries, 2);
  assert.ok(calls.length >= 4);
});

test('bad credentials → AUTH_FAILED', async () => {
  const { ctx } = fakeCtx({ routes: { 'POST /login': () => ({ status: 401, body: { status: 'error', message: 'Invalid credentials' } }) } });
  await assert.rejects(fan.testConnection(ctx), (e) => e.code === 'AUTH_FAILED');
});

test('testConnection lists branches with a Romanian message', async () => {
  const { ctx } = fakeCtx({
    routes: {
      'POST /login': okLogin,
      'GET /reports/branches': () => ({ body: { status: 'success', data: [{ id: 7032158, name: 'Depozit Cluj', address: { locality: 'Cluj-Napoca', street: 'Fabricii', streetNo: '1' } }] } }),
    },
  });
  const r = await fan.testConnection(ctx);
  assert.equal(r.ok, true);
  assert.match(ro(r).message, /Conectat la FAN Courier/);
  assert.equal(r.info.branches[0].id, '7032158');
});

test('createShipment payload: Cont Colector for COD, resolved locality, reference, options', async () => {
  const { ctx, calls } = fakeCtx({ routes: baseRoutes(), settings: { openPackage: true } });
  const res = await fan.createShipment(ctx, shipment());
  assert.equal(res.awb, '2228300120233');
  assert.equal(res.price, 23.8);
  const body = lastJson(calls, '/intern-awb');
  assert.equal(body.clientId, 7032158);
  const { info, recipient } = body.shipments[0];
  assert.equal(info.service, 'Cont Colector');
  assert.equal(info.cod, 149.9);
  assert.equal(info.payment, 'sender');
  assert.deepEqual(info.packages, { parcel: 1, envelope: 0 });
  assert.ok(info.options.includes('A'), 'open package option A');
  assert.match(info.content, /#1024/);
  assert.equal(recipient.address.locality, 'Cluj-Napoca');
  assert.equal(recipient.address.county, 'Cluj');
  assert.equal(recipient.address.zipCode, '400114');
  assert.equal(recipient.phone, '0722123456');
});

test('COD without Cont Colector setting keeps Standard; prepaid keeps Standard', () => {
  assert.equal(pickService({ cod: 50 }, { codToBankAccount: false }), 'Standard');
  assert.equal(pickService({ cod: 0 }, {}), 'Standard');
  assert.equal(pickService({ cod: 10 }, { service: 'RedCode' }), 'Red code-Cont Colector');
  assert.equal(pickService({ cod: 0, service: 'Cont Colector' }, {}), 'Standard');
  assert.equal(pickService({ cod: 10, lockerId: 'F1' }, {}), 'FANbox Cont Colector');
});

test('FANbox: service, option V, pickupLocationId and locker county/locality', async () => {
  const { ctx, calls } = fakeCtx({
    routes: baseRoutes({
      'GET /reports/pickup-points': ({ url }) => {
        assert.equal(url.searchParams.get('id'), 'FAN0033');
        return { body: { status: 'success', data: [{ id: 'FAN0033', name: 'FANbox Kaufland', address: { county: 'Bucuresti', locality: 'Bucuresti' } }] } };
      },
    }),
    settings: { openPackage: true },
  });
  await fan.createShipment(ctx, shipment({ lockerId: 'FAN0033' }));
  const { info, recipient } = lastJson(calls, '/intern-awb').shipments[0];
  assert.equal(info.service, 'FANbox Cont Colector');
  assert.deepEqual(info.options, ['V']);
  assert.equal(recipient.address.pickupLocationId, 'FAN0033');
  assert.equal(recipient.address.locality, 'Bucuresti');
  assert.equal(recipient.address.street, undefined);
});

test('FANbox refuses more than one parcel', async () => {
  const { ctx } = fakeCtx({ routes: baseRoutes() });
  await assert.rejects(fan.createShipment(ctx, shipment({ lockerId: 'F1', parcels: 2 })), (e) => e.code === 'LOCKER_MULTI_PARCEL');
});

test('locality resolution: București sector, prefixes, diacritics', async () => {
  const { ctx } = fakeCtx({ routes: baseRoutes() });
  assert.deepEqual(await resolveFanLocality(ctx, { city: 'Sector 3', county: 'București' }), { locality: 'Bucuresti', county: 'Bucuresti' });
  assert.deepEqual(await resolveFanLocality(ctx, { city: 'București', county: 'Bucuresti', sector: 6 }), { locality: 'Bucuresti', county: 'Bucuresti' });
  assert.deepEqual(await resolveFanLocality(ctx, { city: 'Com. Florești', county: 'Cluj' }), { locality: 'Floresti', county: 'Cluj' });
  assert.deepEqual(await resolveFanLocality(ctx, { city: 'Câmpia Turzii', county: 'Cluj' }), { locality: 'Campia Turzii', county: 'Cluj' });
  assert.deepEqual(await resolveFanLocality(ctx, { city: 'Floresti', county: 'Prahova' }), { locality: 'Floresti', county: 'Prahova' });
});

test('unknown locality → ADDRESS_CITY_NOT_FOUND with suggestions', async () => {
  const { ctx } = fakeCtx({ routes: baseRoutes() });
  await assert.rejects(fan.createShipment(ctx, shipment({ recipient: { ...shipment().recipient, city: 'Cluj Napca' } })), (e) => {
    assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
    assert.equal(e.field, 'shippingAddress.city');
    assert.match(ro(e).hint, /^Ai vrut: Cluj-Napoca/);
    assert.ok(ro(e).hint.split(',').length <= 3);
    return true;
  });
});

test('FAN validation errors are mapped to order fields', async () => {
  const { ctx } = fakeCtx({
    routes: baseRoutes({
      'POST /intern-awb': () => ({ body: { response: [{ awbNumber: null, success: false, errors: { 'recipient.phone': 'Invalid phone' } }] } }),
    }),
  });
  await assert.rejects(fan.createShipment(ctx, shipment()), (e) => {
    assert.equal(e.code, 'ADDRESS_PHONE_INVALID');
    assert.equal(e.field, 'shippingAddress.phone');
    assert.deepEqual(e.details.response[0].errors, { 'recipient.phone': 'Invalid phone' });
    return true;
  });

  const { ctx: ctx2 } = fakeCtx({
    routes: baseRoutes({ 'POST /intern-awb': () => ({ status: 422, body: { status: 'error', errors: { 'info.service': ['Serviciu invalid'] } } }) }),
  });
  await assert.rejects(fan.createShipment(ctx2, shipment()), (e) => e.code === 'COURIER_REJECTED' && /FAN Courier/.test(ro(e).message));
});

test('missing clientId setting → SETTINGS_MISSING', async () => {
  const { ctx } = fakeCtx({ routes: baseRoutes() });
  ctx.settings = {};
  await assert.rejects(fan.createShipment(ctx, shipment()), (e) => e.code === 'SETTINGS_MISSING' && e.field === 'settings.clientId');
});

test('getLabel returns the PDF buffer and asks for pdf + format', async () => {
  const pdf = Buffer.from('%PDF-1.4\n...');
  const { ctx, calls } = fakeCtx({ routes: { 'POST /login': okLogin, 'GET /awb/label': () => ({ body: pdf }) } });
  const buf = await fan.getLabel(ctx, '2228300120233', { format: 'A4' });
  assert.ok(Buffer.isBuffer(buf));
  assert.equal(buf.toString('latin1', 0, 5), '%PDF-');
  const c = calls.find((x) => x.path === '/awb/label');
  assert.deepEqual(c.query.getAll('awbs[]'), ['2228300120233']);
  assert.equal(c.query.get('pdf'), '1');
  assert.equal(c.query.get('format'), 'A4');
  assert.equal(c.query.get('clientId'), '7032158');
  assert.equal(c.opts.responseType, 'buffer');
});

test('getLabel with a non-PDF body → LABEL_FAILED', async () => {
  const { ctx } = fakeCtx({ routes: { 'POST /login': okLogin, 'GET /awb/label': () => ({ body: Buffer.from('{"status":"error","message":"AWB not found"}') }) } });
  await assert.rejects(fan.getLabel(ctx, '1', { format: 'A6' }), (e) => e.code === 'LABEL_FAILED' && e.details.message === 'AWB not found');
});

test('cancelShipment: success and refusal', async () => {
  const { ctx, calls } = fakeCtx({ routes: { 'POST /login': okLogin, 'DELETE /awb': () => ({ body: { status: 'success', data: 'The AWB was successfully deleted' } }) } });
  await fan.cancelShipment(ctx, '123');
  assert.equal(calls.find((c) => c.path === '/awb').query.get('awb'), '123');

  const { ctx: ctx2 } = fakeCtx({ routes: { 'POST /login': okLogin, 'DELETE /awb': () => ({ status: 400, body: { status: 'error', message: 'AWB cannot be deleted' } }) } });
  await assert.rejects(fan.cancelShipment(ctx2, '123'), (e) => e.code === 'CANCEL_REFUSED');
});

test('track maps FAN events (batch, ISO dates, missing AWBs omitted)', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      'POST /login': okLogin,
      'GET /reports/awb/tracking': () => ({
        body: {
          status: 'success',
          data: [
            { awbNumber: 'A1', events: [{ id: 'C0', name: 'Expeditie preluata', date: '2023-03-01 04:46:46' }, { id: 'S1', name: 'In livrare', date: '2023-03-01 08:43:28' }, { id: 'S2', name: 'Livrat', date: '2023-07-06 13:58:43' }] },
            { awbNumber: 'A2', events: [{ id: 'H4', name: 'Sortat', date: '2023-03-01 04:46:46' }, { id: 'S6', name: 'Refuz primire', date: '2023-03-02 10:00:00' }] },
            { awbNumber: 'A3', events: [] },
          ],
        },
      }),
    },
  });
  const res = await fan.track(ctx, ['A1', 'A2', 'A3', 'A4']);
  assert.deepEqual(calls.find((c) => c.path === '/reports/awb/tracking').query.getAll('awb[]'), ['A1', 'A2', 'A3', 'A4']);
  assert.equal(res.length, 3);
  const [a1, a2, a3] = res;
  assert.equal(a1.status, 'delivered');
  assert.equal(a1.codCollected, true);
  assert.equal(a1.at, '2023-07-06T10:58:43.000Z'); // EEST, UTC+3
  assert.equal(a2.status, 'returning');
  assert.equal(a3.status, 'created');
});

test('FAN event table', () => {
  const cases = {
    C0: 'picked_up', C1: 'out_for_delivery', H10: 'in_transit', H17: 'in_transit', S1: 'out_for_delivery', S2: 'delivered',
    S3: 'failed_attempt', S12: 'failed_attempt', S30: 'failed_attempt', S6: 'returning', S15: 'returning', S43: 'returning',
    S46: 'out_for_delivery', S38: 'created', ZZ: 'unknown',
  };
  for (const [id, st] of Object.entries(cases)) assert.equal(mapFanEvent(id), st, id);
});

// ---- live-check regressions (fixtures from the real API, invalid credentials) ----------------

const LIVE = JSON.parse(readFileSync(new URL('./fixtures/couriers/fancourier.json', import.meta.url), 'utf8'));
const liveLocalities = () => ({ body: LIVE.localitiesSample.body });

test('live: real 401 from /login → AUTH_FAILED (testConnection and createShipment)', async () => {
  const bad = () => ({ status: LIVE.loginBadCredentials.status, body: LIVE.loginBadCredentials.body });
  const { ctx } = fakeCtx({ routes: { 'POST /login': bad } });
  await assert.rejects(fan.testConnection(ctx), (e) => e.code === 'AUTH_FAILED' && !e.retryable);
  const { ctx: ctx2 } = fakeCtx({ routes: { ...baseRoutes(), 'POST /login': bad } });
  await assert.rejects(fan.createShipment(ctx2, shipment()), (e) => e.code === 'AUTH_FAILED');
});

test('live: 401 on an authenticated route with a cached token → re-login once, then AUTH_FAILED', async () => {
  let logins = 0;
  const { ctx } = fakeCtx({
    routes: {
      'POST /login': () => (++logins === 1 ? okLogin() : { status: 401, body: LIVE.loginBadCredentials.body }),
      'GET /reports/branches': () => ({ status: 401, body: LIVE.authenticatedRouteBadToken.body }),
    },
  });
  await assert.rejects(fan.listPickupPoints(ctx), (e) => e.code === 'AUTH_FAILED');
  assert.equal(logins, 2);
});

test('live: Laravel 422 {"status":"fail","data":{"errors":{...}}} is mapped by field', async () => {
  const body = { status: 'fail', message: 'The given data was invalid.', data: { errors: { 'shipments.0.recipient.address.locality': ['The selected locality is invalid.'] } } };
  const { ctx } = fakeCtx({ routes: baseRoutes({ 'POST /intern-awb': () => ({ status: 422, body }) }) });
  await assert.rejects(fan.createShipment(ctx, shipment()), (e) => e.code === 'ADDRESS_CITY_NOT_FOUND' && e.field === 'shippingAddress.city');
  // Unknown field: generic, but FAN's own words reach the merchant.
  const { ctx: ctx2 } = fakeCtx({ routes: baseRoutes({ 'POST /intern-awb': () => ({ status: 422, body: LIVE.validationError.body }) }) });
  await assert.rejects(fan.createShipment(ctx2, shipment()), (e) => e.code === 'COURIER_REJECTED' && /The per page must be a number/.test(ro(e).hint));
});

test('live: localities are public — fetched without a token; "Name (Commune)" spelling sent as FAN has it', async () => {
  const { ctx, calls } = fakeCtx({ routes: baseRoutes({ 'GET /reports/localities': liveLocalities }) });
  const r = { ...shipment().recipient, county: 'Hunedoara', countyCode: 'HD', city: 'Merișor', zip: '' };
  await fan.createShipment(ctx, shipment({ recipient: r }));
  assert.equal(calls.find((c) => c.path === '/reports/localities').opts.headers?.Authorization, undefined);
  assert.equal(lastJson(calls, '/intern-awb').shipments[0].recipient.address.locality, 'Merisor (Bucuresci)');

  await assert.rejects(fan.createShipment(ctx, shipment({ recipient: { ...r, city: 'Alun' } })), (e) => {
    assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
    assert.equal(ro(e).hint.split('?')[0], 'Ai vrut: Alun (Bosorod), Alun (Bunila)');
    return true;
  });
  await fan.createShipment(ctx, shipment({ recipient: { ...r, city: 'Alun, com. Bunila' } }));
  assert.equal(lastJson(calls, '/intern-awb').shipments[0].recipient.address.locality, 'Alun (Bunila)');
  // "Voluntari" typed with county București: FAN's Voluntari is in Ilfov, never "Bucuresti".
  await fan.createShipment(ctx, shipment({ recipient: { ...r, county: 'București', countyCode: 'B', city: 'Voluntari' } }));
  assert.deepEqual(lastJson(calls, '/intern-awb').shipments[0].recipient.address, { county: 'Ilfov', locality: 'Voluntari', street: r.street, streetNo: '', zipCode: '' });
});

test('COD: only RON (FAN has no currency field), rounded to bani', async () => {
  const { ctx, calls } = fakeCtx({ routes: baseRoutes() });
  await assert.rejects(fan.createShipment(ctx, shipment({ cod: 50, currency: 'EUR' })), (e) => e.code === 'COD_CURRENCY_UNSUPPORTED');
  assert.equal(calls.filter((c) => c.path === '/intern-awb').length, 0);
  await fan.createShipment(ctx, shipment({ cod: 149.89999999999 }));
  assert.equal(lastJson(calls, '/intern-awb').shipments[0].info.cod, 149.9);
});

test('token cache is per account', async () => {
  const { ctx, calls } = fakeCtx({ routes: { ...baseRoutes(), 'POST /login': ({ opts }) => ({ body: { status: 'success', data: { token: `T-${opts.body.get('username')}` } } }) } });
  await fan.createShipment(ctx, shipment());
  await fan.createShipment({ ...ctx, credentials: { username: 'other', password: 'x' } }, shipment());
  const awbs = calls.filter((c) => c.path === '/intern-awb').map((c) => c.opts.headers.Authorization);
  assert.deepEqual(awbs, ['Bearer T-shop', 'Bearer T-other']);
  assert.notEqual(tokenKey(ctx), tokenKey({ credentials: { username: 'shop', password: 'changed' } }));
});

// ---- REAL success responses (test account published in FAN's API docs, run 2026-10-02 by
// scripts/sandbox-couriers.mjs; see _source in the fixture).
const OK = JSON.parse(readFileSync(new URL('./fixtures/couriers/fancourier-success.json', import.meta.url), 'utf8'));
const sandboxShipment = () => ({
  reference: 'EXPEDO-TEST',
  recipient: {
    name: 'Test Expedo', contactPerson: 'Test Expedo', phone: '0723456789', email: '',
    county: 'Cluj', countyCode: 'CJ', city: 'Cluj-Napoca', street: 'Str. Test 1', zip: '400001', country: 'RO',
  },
  parcels: 1, weightKg: 1, envelopes: 0, cod: 10, currency: 'RON', declaredValue: 0,
  contents: 'Test API Expedo - NU EXPEDIATI', notes: 'TEST API - AWB anulat imediat',
});

test('live success: testConnection, listPickupPoints and listServices on the real bodies', async () => {
  const { ctx } = fakeCtx({ routes: { 'POST /login': () => OK.login, 'GET /reports/branches': () => OK.branches, 'GET /reports/services': () => OK.services } });
  const conn = await fan.testConnection(ctx);
  assert.equal(conn.ok, true);
  assert.deepEqual(conn.info.branches.map((b) => b.id), ['7032158']); // numeric id in the body → string
  assert.doesNotMatch(ro(conn).message, /Atenție/);
  const pts = await fan.listPickupPoints(ctx);
  assert.deepEqual(pts, [{ id: '7032158', name: 'FAN Courier - cont test', address: 'Fabrica de Glucoza (sosea), 11C, Bucuresti, Bucuresti' }]);
  const svcs = await fan.listServices(ctx);
  assert.equal(svcs.length, 16);
  assert.ok(svcs.some((s) => s.id === 'Cont Colector') && svcs.some((s) => s.id === 'FANbox Cont Colector'));
});

test('live success: createShipment sends exactly the payload FAN accepted and returns the real AWB + price', async () => {
  const { ctx, calls } = fakeCtx({ routes: baseRoutes({ 'POST /login': () => OK.login, 'POST /intern-awb': () => OK.internAwbSuccess }) });
  const res = await fan.createShipment(ctx, sandboxShipment());
  assert.deepEqual(lastJson(calls, '/intern-awb'), OK.internAwbRequest.json);
  assert.equal(res.awb, '7000170297615'); // number in the body → string
  assert.equal(res.price, 46.31); // tariff 38.27 + vat 8.04
});

test('live: 200 intern-awb with success:false and "info.recipient.phone" blacklisted → ADDRESS_PHONE_INVALID', async () => {
  const { ctx } = fakeCtx({ routes: baseRoutes({ 'POST /intern-awb': () => OK.internAwbBlacklistedPhone }) });
  await assert.rejects(fan.createShipment(ctx, sandboxShipment()), (e) => e.code === 'ADDRESS_PHONE_INVALID' && e.field === 'shippingAddress.phone');
});

test('live success: label is requested as pdf=1 and the PDF buffer is returned', async () => {
  assert.equal(OK.label.contentType, 'application/pdf');
  assert.equal(OK.label.bodySummary.startsWith, '%PDF-1.4');
  const pdf = Buffer.from('%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF');
  const { ctx, calls } = fakeCtx({ routes: { 'POST /login': okLogin, 'GET /awb/label': () => ({ body: pdf }) } });
  assert.equal(await fan.getLabel(ctx, '7000170297615', { format: 'A4' }), pdf);
  const q = calls.find((c) => c.path === '/awb/label').query;
  assert.deepEqual([q.get('clientId'), q.getAll('awbs[]'), q.get('pdf'), q.get('format')], ['7032158', ['7000170297615'], '1', 'A4']);
});

test('live: tracking rows without events — unknown AWB omitted, registered AWB = created with FAN\'s text', async () => {
  for (const fixture of [OK.trackingNoEvents, OK.trackingNotFoundEn]) {
    const { ctx } = fakeCtx({ routes: { 'POST /login': okLogin, 'GET /reports/awb/tracking': () => fixture } });
    const res = await fan.track(ctx, ['7000000000001', '7000170297615']);
    assert.ok(!res.some((r) => r.awb === '7000000000001'), 'unknown AWB must be omitted');
    if (fixture === OK.trackingNoEvents) {
      assert.deepEqual(res, [{ awb: '7000170297615', status: 'created', statusText: 'AWB-ul a fost inregistrat de catre clientul expeditor', at: undefined }]);
    }
  }
});

test('live: DELETE succeeds, and a second DELETE (422 "already deleted") counts as cancelled', async () => {
  const { ctx } = fakeCtx({ routes: { 'POST /login': okLogin, 'DELETE /awb': () => OK.deleteSuccess } });
  await fan.cancelShipment(ctx, '7000170297615');
  const { ctx: ctx2 } = fakeCtx({ routes: { 'POST /login': okLogin, 'DELETE /awb': () => OK.deleteAgain } });
  await fan.cancelShipment(ctx2, '7000170297615');
});
