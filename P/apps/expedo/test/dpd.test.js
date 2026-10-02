import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ProcessingError, authError } from '../src/core/errors.js';
import dpd, { mapDpdOperation, parseCsv, compactSites, buildShipmentRequest, parseDpdDate, parcelsKey } from '../src/couriers/dpd.js';

function fakeCtx({ routes, settings = {}, credentials = { userName: 'api_shop', password: 'pw' } }) {
  const calls = [];
  const store = new Map();
  const http = async (provider, url, opts = {}) => {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/v1/, '');
    calls.push({ path, json: opts.json, opts });
    const handler = routes[path] || routes[path.replace(/\/\d+$/, '/:id')];
    if (!handler) throw new Error(`unexpected call ${path}`);
    const { status = 200, body } = await handler(opts.json, calls);
    if (status >= 400) {
      const mapped = opts.mapError?.(status, body);
      if (mapped) throw mapped;
      if (status === 401 || status === 403) throw authError(provider, body);
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: `${provider} a refuzat`, provider, details: body });
    }
    return { status, headers: new Headers(), body };
  };
  const cache = { get: (k) => store.get(k), set: (k, v) => { store.set(k, v); } };
  return { ctx: { credentials, settings, http, cache, log: () => {} }, calls, store };
}

// 100+ rows so the CSV is accepted as a real nomenclator.
const filler = Array.from({ length: 120 }, (_, i) => `${900000 + i},642,,s.,v.,SAT FILLER ${i},SAT FILLER ${i},COM X,COM X,ALBA,ALBA,510000`);
const SITES_CSV = [
  'id,countryId,mainSiteId,type,typeEn,name,nameEn,municipality,municipalityEn,region,regionEn,postCode,addressNomenclature,x,y,servingDays,servingOfficeId,servingHubOfficeId',
  '642279132,642,,mun.,mun.,CLUJ-NAPOCA,CLUJ-NAPOCA,CLUJ-NAPOCA,CLUJ-NAPOCA,CLUJ,CLUJ,400001,2,23.6,46.7,1111110,1,1',
  '642279200,642,,com.,com.,FLORESTI,FLORESTI,FLORESTI,FLORESTI,CLUJ,CLUJ,407280,1,23.5,46.7,1111100,1,1',
  '642100001,642,,s.,v.,VALEA MARE,VALEA MARE,"BUDESTI",BUDESTI,VALCEA,VALCEA,247061,0,0,0,1111100,1,1',
  '642100002,642,,s.,v.,VALEA MARE,VALEA MARE,"STEFANESTI, JUD",STEFANESTI,VALCEA,VALCEA,247562,0,0,0,1111100,1,1',
  '642000001,642,,mun.,mun.,BUCURESTI,BUCURESTI,BUCURESTI,BUCURESTI,BUCURESTI,BUCURESTI,010011,2,26.1,44.4,1111110,1,1',
  ...filler,
].join('\n');

const sitesRoute = () => ({ body: SITES_CSV });
const shipmentOk = (json) => ({ body: { id: '80012345678', parcels: Array.from({ length: json.content.parcelsCount }, (_, i) => ({ seqNo: i + 1, id: String(80012345678 + i) })), price: { total: 21.42 } } });

const shipment = (over = {}) => ({
  reference: '#3003',
  recipient: {
    name: 'Maria Ionescu', contactPerson: 'Maria Ionescu', phone: '0733 111 222', email: 'maria@example.ro',
    county: 'Cluj', countyCode: 'CJ', city: 'Cluj-Napoca', street: 'Str. Horea nr. 5, ap. 2', zip: '400174', country: 'RO',
  },
  parcels: 1, weightKg: 2.3, envelopes: 0, cod: 250, currency: 'RON', declaredValue: 0, contents: 'Haine',
  ...over,
});
const recipientWith = (over) => ({ ...shipment().recipient, ...over });

test('credentials go in every JSON body', async () => {
  const { ctx, calls } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': shipmentOk } });
  await dpd.createShipment(ctx, shipment());
  assert.equal(calls.length, 2);
  for (const c of calls) {
    assert.equal(c.json.userName, 'api_shop');
    assert.equal(c.json.password, 'pw');
  }
  assert.equal(calls[0].path, '/location/site/csv/642');
  assert.equal(calls[0].opts.responseType, 'text');
});

test('createShipment payload: site, COD cash, OBPD, reference, private person', async () => {
  const { ctx, calls, store } = fakeCtx({
    routes: { '/location/site/csv/:id': sitesRoute, '/shipment': shipmentOk },
    settings: { senderClientId: '123456789', openPackage: true, serviceId: 2505 },
  });
  const res = await dpd.createShipment(ctx, shipment());
  assert.equal(res.awb, '80012345678');
  assert.equal(res.price, 21.42);
  assert.deepEqual(store.get(parcelsKey(ctx, '80012345678')), ['80012345678']);
  const req = calls.find((c) => c.path === '/shipment').json;
  assert.deepEqual(req.sender, { clientId: 123456789 });
  assert.deepEqual(req.recipient, {
    privatePerson: true,
    clientName: 'Maria Ionescu',
    phone1: { number: '0733111222' },
    email: 'maria@example.ro',
    address: { countryId: 642, siteId: 642279132, addressNote: 'Str. Horea nr. 5, ap. 2' },
  });
  assert.equal(req.service.serviceId, 2505);
  assert.deepEqual(req.service.additionalServices.cod, { amount: 250, processingType: 'CASH' });
  assert.deepEqual(req.service.additionalServices.obpd, { option: 'OPEN', returnShipmentServiceId: 2505, returnShipmentPayer: 'SENDER' });
  assert.deepEqual(req.content, { parcelsCount: 1, totalWeight: 2.3, contents: 'Haine', package: 'BOX' });
  assert.deepEqual(req.payment, { courierServicePayer: 'SENDER' });
  assert.equal(req.ref1, '#3003');
});

test('company recipient, declared value, prepaid (no COD/OBPD)', () => {
  const req = buildShipmentRequest(
    shipment({ cod: 0, declaredValue: 300, openPackage: true, recipient: recipientWith({ company: 'Acme SRL' }) }),
    {},
    { siteId: 1 },
  );
  assert.equal(req.recipient.privatePerson, false);
  assert.equal(req.recipient.clientName, 'Acme SRL');
  assert.equal(req.recipient.contactName, 'Maria Ionescu');
  assert.deepEqual(req.service.additionalServices, { declaredValue: { amount: 300 } });
  assert.equal(req.sender, undefined);
  assert.equal(req.service.serviceId, 2505);
});

test('locker / office delivery uses pickupOfficeId and skips site resolution', async () => {
  const { ctx, calls } = fakeCtx({ routes: { '/shipment': shipmentOk } });
  await dpd.createShipment(ctx, shipment({ lockerId: '1234' }));
  const req = calls.find((c) => c.path === '/shipment').json;
  assert.equal(req.recipient.pickupOfficeId, 1234);
  assert.equal(req.recipient.address, undefined);
  assert.equal(calls.length, 1);
});

test('site resolution: diacritics, prefixes, București sector; nomenclator cached', async () => {
  const { ctx, calls } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': shipmentOk } });
  await dpd.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Com. Florești' }) }));
  assert.equal(calls.at(-1).json.recipient.address.siteId, 642279200);
  await dpd.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Sector 4', county: 'București' }) }));
  assert.equal(calls.at(-1).json.recipient.address.siteId, 642000001);
  assert.equal(calls.filter((c) => c.path.startsWith('/location/site/csv')).length, 1);
});

test('ambiguous village: ZIP decides, otherwise ADDRESS_CITY_NOT_FOUND listing communes', async () => {
  const { ctx, calls } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': shipmentOk } });
  await dpd.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Valea Mare', county: 'Vâlcea', zip: '247562' }) }));
  assert.equal(calls.at(-1).json.recipient.address.siteId, 642100002);

  await assert.rejects(dpd.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Valea Mare', county: 'Vâlcea', zip: '' }) })), (e) => {
    assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
    assert.equal(e.field, 'shippingAddress.city');
    assert.equal(e.hint.split('?')[0], 'Ai vrut: VALEA MARE (BUDESTI), VALEA MARE (STEFANESTI, JUD)');
    return true;
  });
});

test('unknown locality → ADDRESS_CITY_NOT_FOUND with up to 3 suggestions', async () => {
  const { ctx } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': shipmentOk } });
  await assert.rejects(dpd.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Floreshti' }) })), (e) => {
    assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
    assert.match(e.hint, /^Ai vrut: FLORESTI/);
    assert.ok(e.hint.replace(/\?.*$/, '').split(', ').length <= 3);
    return true;
  });
});

test('CSV export refused → falls back to POST /location/site', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      '/location/site/csv/:id': () => ({ body: '{"error":{"code":1,"message":"Not allowed","id":"x"}}' }),
      '/location/site': (json) => ({ body: { sites: json.postCode ? [] : [{ id: 642279132, name: 'CLUJ-NAPOCA', municipality: 'CLUJ-NAPOCA', region: 'CLUJ', postCode: '400001' }] } }),
      '/shipment': shipmentOk,
    },
  });
  await dpd.createShipment(ctx, shipment());
  const finds = calls.filter((c) => c.path === '/location/site');
  assert.deepEqual(finds.map((c) => c.json.postCode || c.json.name), ['400174', 'CLUJ NAPOCA']);
  assert.equal(finds[0].json.countryId, 642);
  assert.equal(calls.at(-1).json.recipient.address.siteId, 642279132);
});

test('API errors are mapped: address, auth, generic', async () => {
  const withError = (error) => fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': () => ({ body: { error } }) } }).ctx;
  await assert.rejects(dpd.createShipment(withError({ code: 120, message: 'Invalid site', component: 'recipient.address.siteId' }), shipment()), (e) => e.code === 'ADDRESS_CITY_NOT_FOUND' && e.field === 'shippingAddress.city');
  await assert.rejects(dpd.createShipment(withError({ code: 100, message: 'Invalid phone', component: 'recipient.phone1.number' }), shipment()), (e) => e.code === 'ADDRESS_PHONE_INVALID');
  await assert.rejects(dpd.createShipment(withError({ code: 410, message: 'COD not allowed' }), shipment()), (e) => e.code === 'COD_INVALID' && e.details.error.code === 410);
  await assert.rejects(dpd.createShipment(withError({ code: 1, message: 'Something else' }), shipment()), (e) => e.code === 'COURIER_REJECTED' && e.message === 'DPD a refuzat cererea.');

  const { ctx } = fakeCtx({ routes: { '/client/contract': () => ({ body: { error: { code: 1, message: 'Invalid username or password', id: 'e1' } } }) } });
  await assert.rejects(dpd.testConnection(ctx), (e) => e.code === 'AUTH_FAILED');
});

test('testConnection lists contract clients in Romanian', async () => {
  const { ctx } = fakeCtx({ routes: { '/client/contract': () => ({ body: { clients: [{ clientId: 111, clientName: 'Magazin SRL', objectName: 'Depozit Cluj' }] } }) } });
  const r = await dpd.testConnection(ctx);
  assert.equal(r.ok, true);
  assert.match(r.message, /^Conectat la DPD\. Un punct de ridicare în contract: 111 \(Depozit Cluj\)\.$/);
});

test('getLabel prints all parcels of the shipment and returns a Buffer', async () => {
  const pdf = Buffer.from('%PDF-1.7 label');
  const { ctx, calls } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': shipmentOk, '/print': () => ({ body: pdf }) } });
  const { awb } = await dpd.createShipment(ctx, shipment({ parcels: 2 }));
  const buf = await dpd.getLabel(ctx, awb, { format: 'A6' });
  assert.ok(Buffer.isBuffer(buf));
  assert.equal(buf.toString('latin1', 0, 5), '%PDF-');
  const req = calls.find((c) => c.path === '/print');
  assert.equal(req.json.paperSize, 'A6');
  assert.deepEqual(req.json.parcels, [{ parcel: { id: '80012345678' } }, { parcel: { id: '80012345679' } }]);
  assert.equal(req.opts.responseType, 'buffer');
});

test('getLabel: JSON error body is mapped; unknown shipment uses /shipment/info', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      '/shipment/info': () => ({ body: { shipments: [{ id: '5', content: { parcels: [{ id: '5' }, { id: '6' }] } }] } }),
      '/print': () => ({ body: Buffer.from('{"error":{"code":1,"message":"Parcel not found","id":"z"}}') }),
    },
  });
  await assert.rejects(dpd.getLabel(ctx, '5', { format: 'A4' }), (e) => e.code === 'COURIER_REJECTED');
  const req = calls.find((c) => c.path === '/print').json;
  assert.equal(req.paperSize, 'A4');
  assert.deepEqual(req.parcels.map((p) => p.parcel.id), ['5', '6']);
});

test('cancelShipment: success and refusal', async () => {
  const { ctx, calls } = fakeCtx({ routes: { '/shipment/cancel': () => ({ body: {} }) } });
  await dpd.cancelShipment(ctx, '80012345678');
  assert.equal(calls[0].json.shipmentId, '80012345678');
  assert.ok(calls[0].json.comment);
  const { ctx: ctx2 } = fakeCtx({ routes: { '/shipment/cancel': () => ({ body: { error: { code: 1, message: 'Shipment already ordered for pickup' } } }) } });
  await assert.rejects(dpd.cancelShipment(ctx2, '1'), (e) => e.code === 'CANCEL_REFUSED');
});

test('track: batches of 10, maps operation codes, skips informational ones', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      '/track': (json) => ({
        body: {
          parcels: json.parcels.map(({ id }) => {
            if (id === 'D') return { parcelId: id, operations: [{ dateTime: '2026-05-01T09:00:00+0300', operationCode: 39, description: 'Ridicat' }, { dateTime: '2026-05-02T14:30:00+0300', operationCode: -14, description: 'Livrat' }] };
            if (id === 'P') return { parcelId: id, operations: [{ dateTime: '2026-05-02T08:00:00+0300', operationCode: 12, description: 'În livrare' }, { dateTime: '2026-05-02T08:01:00+0300', operationCode: 175, description: 'Predict' }] };
            if (id === 'R') return { parcelId: id, operations: [{ dateTime: '2026-05-03T08:00:00+0300', operationCode: 124, description: 'Returnat' }] };
            if (id === 'X') return { parcelId: id, error: { code: 1, message: 'Not found' } };
            return { parcelId: id, operations: [] };
          }),
        },
      }),
    },
  });
  const awbs = ['D', 'P', 'R', 'X', ...Array.from({ length: 8 }, (_, i) => `N${i}`)];
  const res = await dpd.track(ctx, awbs);
  assert.deepEqual(calls.map((c) => c.json.parcels.length), [10, 2]);
  const by = Object.fromEntries(res.map((r) => [r.awb, r]));
  assert.equal(by.D.status, 'delivered');
  assert.equal(by.D.at, '2026-05-02T11:30:00.000Z');
  assert.equal(by.D.codCollected, true);
  assert.equal(by.P.status, 'out_for_delivery');
  assert.equal(by.P.statusText, 'În livrare');
  assert.equal(by.R.status, 'returned');
  assert.equal(by.X, undefined);
  assert.equal(by.N0.status, 'created');
});

test('DPD operation table and helpers', () => {
  const cases = { 148: 'created', 39: 'picked_up', 1: 'in_transit', 2: 'in_transit', 12: 'out_for_delivery', 134: 'out_for_delivery', '-14': 'delivered', 44: 'failed_attempt', 190: 'failed_attempt', 123: 'returning', 111: 'returning', 124: 'returned', 128: 'cancelled', 4242: 'unknown' };
  for (const [code, st] of Object.entries(cases)) assert.equal(mapDpdOperation(code), st, code);
  assert.equal(mapDpdOperation(1134), null);
  assert.equal(parseDpdDate('2026-01-10T10:00:00+0200'), '2026-01-10T08:00:00.000Z');
  assert.deepEqual(parseCsv('a,"b, c","d ""q"""\n1,2,3\r\n'), [['a', 'b, c', 'd "q"'], ['1', '2', '3']]);
  assert.deepEqual(compactSites('1,642,,s.,v.,X,X,M,M,R,R,123')[0], [1, 'X', 'M', 'R', '123', 's.']);
});

// ---- live-check regressions (fixtures from the real API, invalid credentials) ----------------

const LIVE = JSON.parse(readFileSync(new URL('./fixtures/couriers/dpd.json', import.meta.url), 'utf8'));

test('live: HTTP 200 {"error":{code:1,"Nu s-a putut găsi utilizatorul..."}} → AUTH_FAILED (RO, EN, no user)', async () => {
  for (const name of ['authErrorRo', 'authErrorEn', 'wrongUsernameFormat']) {
    const { ctx } = fakeCtx({ routes: { '/client/contract': () => ({ body: LIVE[name].body }) } });
    await assert.rejects(dpd.testConnection(ctx), (e) => e.code === 'AUTH_FAILED' && !e.retryable && e.provider === 'dpd', name);
  }
  const { ctx } = fakeCtx({ routes: { '/location/office': () => ({ body: LIVE.authErrorList.body }) } });
  await assert.rejects(dpd.listLockers(ctx, { city: 'Cluj-Napoca' }), (e) => e.code === 'AUTH_FAILED');
});

test('live: site CSV answered with the JSON auth error → AUTH_FAILED, not "nomenclator unavailable"', async () => {
  const { ctx, calls, store } = fakeCtx({ routes: { '/location/site/csv/:id': () => ({ body: JSON.stringify(LIVE.siteCsvAuthError.body) }), '/shipment': shipmentOk } });
  await assert.rejects(dpd.createShipment(ctx, shipment()), (e) => e.code === 'AUTH_FAILED');
  assert.equal(calls.filter((c) => c.path === '/shipment').length, 0);
  assert.equal([...store.keys()].some((k) => k.includes('unavailable')), false);
});

test('a recipient error mentioning a name is not mistaken for an auth error', async () => {
  const body = { error: { code: 100, message: 'Numele utilizatorului destinatar este invalid', component: '$.recipient.clientName', id: 'x' } };
  const { ctx } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': () => ({ body }) } });
  await assert.rejects(dpd.createShipment(ctx, shipment()), (e) => e.code === 'ADDRESS_NAME_INVALID');
});

test('no shipment id and no error → not retried blindly (duplicate risk)', async () => {
  const { ctx } = fakeCtx({ routes: { '/location/site/csv/:id': sitesRoute, '/shipment': () => ({ body: {} }) } });
  await assert.rejects(dpd.createShipment(ctx, shipment()), (e) => e.code === 'COURIER_REJECTED' && e.retryable === false);
});

test('parcel map per account; COD and declared value rounded; tracking URL is the redirect target', () => {
  const a = { credentials: { userName: 'a', password: 'p' } };
  assert.notEqual(parcelsKey(a, '1'), parcelsKey({ credentials: { userName: 'b', password: 'p' } }, '1'));
  const req = buildShipmentRequest(shipment({ cod: 149.89999999, declaredValue: 10.005 }), {}, { siteId: 1 });
  assert.equal(req.service.additionalServices.cod.amount, 149.9);
  assert.equal(req.service.additionalServices.declaredValue.amount, 10.01);
  assert.equal(dpd.trackingUrl('80012345678'), 'https://services.dpd.ro/tracking/?shipmentNumber=80012345678&language=ro');
});

// ---- success shapes built from the official DPD Web API documentation (see _source in the fixture) ----

const DOC = JSON.parse(readFileSync(new URL('./fixtures/couriers/dpd-success.json', import.meta.url), 'utf8'));

test('documented success: CreateShipmentResponse → awb = id, price = total; parcels remembered for print', async () => {
  const pdf = Buffer.from('%PDF-1.4\n%%EOF');
  const { ctx, calls } = fakeCtx({
    routes: {
      '/location/site/csv/:id': sitesRoute,
      '/shipment': () => ({ body: DOC.createShipment.body }),
      '/print': () => ({ body: pdf }),
      '/shipment/cancel': () => ({ body: DOC.cancelShipment.body }),
    },
  });
  const res = await dpd.createShipment(ctx, shipment({ reference: 'EXPEDO-TEST', parcels: 2 }));
  assert.equal(res.awb, '80912345678');
  assert.equal(res.price, 21.42);
  assert.equal(await dpd.getLabel(ctx, res.awb, { format: 'A6' }), pdf);
  const print = calls.find((c) => c.path === '/print');
  assert.deepEqual(print.json.parcels, [{ parcel: { id: '80912345678' } }, { parcel: { id: '80912345679' } }]);
  assert.equal(print.json.paperSize, 'A6');
  assert.equal(print.opts.responseType, 'buffer');
  await dpd.cancelShipment(ctx, res.awb); // documented success = empty JSON object
  assert.deepEqual(calls.find((c) => c.path === '/shipment/cancel').json.shipmentId, '80912345678');
});

test('documented success: label without cached parcels → ShipmentInformationResponse content.parcels', async () => {
  const { ctx, calls } = fakeCtx({ routes: { '/shipment/info': () => ({ body: DOC.shipmentInfo.body }), '/print': () => ({ body: Buffer.from('%PDF-1.4') }) } });
  await dpd.getLabel(ctx, '80912345678');
  assert.deepEqual(calls.find((c) => c.path === '/print').json.parcels.map((p) => p.parcel.id), ['80912345678', '80912345679']);
});

test('documented success: TrackResponse → statuses, informational 1134 skipped, per-parcel error omitted', async () => {
  const { ctx } = fakeCtx({ routes: { '/track': () => ({ body: DOC.track.body }) } });
  const res = await dpd.track(ctx, ['80912345678', '80912345680', '80912345681', '80900000000']);
  assert.deepEqual(res, [
    { awb: '80912345678', status: 'delivered', statusText: 'Delivered', at: '2026-10-03T09:41:00.000Z', codCollected: true },
    { awb: '80912345680', status: 'failed_attempt', statusText: 'Unsuccessful Delivery', at: '2026-10-03T11:00:00.000Z' },
    { awb: '80912345681', status: 'created', statusText: 'AWB emis', at: undefined },
  ]);
});

test('documented success: contract clients and services', async () => {
  const { ctx } = fakeCtx({ routes: { '/client/contract': () => ({ body: DOC.contractClients.body }), '/services': () => ({ body: DOC.services.body }) } });
  const conn = await dpd.testConnection(ctx);
  assert.equal(conn.ok, true);
  assert.match(conn.message, /77001234000 \(Depozit Test\)/);
  assert.deepEqual(await dpd.listPickupPoints(ctx), [{ id: '77001234000', name: 'Depozit Test', address: 'mun. CLUJ-NAPOCA [400001] str. TEST No 1' }]);
  assert.deepEqual(await dpd.listServices(ctx), [{ id: '2505', name: 'DPD STANDARD' }, { id: '2412', name: 'PALLET ONE RO' }]);
});
