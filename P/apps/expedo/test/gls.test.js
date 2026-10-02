import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { ProcessingError, authError } from '../src/core/errors.js';
import gls, { glsPasswordBytes, mapGlsStatus, parseGlsDate, buildParcel, parcelKey } from '../src/couriers/gls.js';

function fakeCtx({ routes, settings = {}, credentials = { username: 'shop@example.ro', password: 'Parola123!' } }) {
  const calls = [];
  const store = new Map();
  const http = async (provider, url, opts = {}) => {
    const u = new URL(url);
    const method = u.pathname.split('/').pop();
    calls.push({ host: u.host, path: u.pathname, method, json: opts.json, opts });
    const handler = routes[method];
    if (!handler) throw new Error(`unexpected call ${u.pathname}`);
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
  const logs = [];
  return {
    ctx: {
      credentials,
      settings: {
        clientNumber: '553001234',
        senderName: 'Magazin SRL', senderStreet: 'Str. Fabricii nr. 10', senderCity: 'Cluj-Napoca', senderZip: '400620',
        senderPhone: '0744000111', senderEmail: 'depozit@magazin.ro',
        ...settings,
      },
      http, cache, log: (m, d) => logs.push([m, d]),
    },
    calls, store, logs,
  };
}

const LOCATIONS = [
  { Name: 'Cluj-Napoca', ZipCode: '400114' },
  { Name: 'Cluj-Napoca', ZipCode: '400620' },
  { Name: 'Floresti', ZipCode: '407280' },
  { Name: 'Turda', ZipCode: '401001' },
  { Name: 'Bucuresti', ZipCode: '030167' },
];
const locationsBody = () => ({ body: { ErrorCode: 0, IsChanged: true, Data: [...gzipSync(Buffer.from(JSON.stringify(LOCATIONS)))] } });

const PDF = Buffer.from('%PDF-1.4 fake label');
const printOk = (json) => ({
  body: {
    Labels: [...PDF],
    PrintLabelsErrorList: [],
    PrintLabelsInfoList: json.ParcelList.flatMap((p, i) => Array.from({ length: p.Count }, (_, j) => ({ ClientReference: p.ClientReference, ParcelId: 9000 + i * 10 + j, ParcelNumber: 50012345670 + j }))),
  },
});

const shipment = (over = {}) => ({
  reference: '#2001',
  recipient: {
    name: 'Ion Pop', contactPerson: 'Ion Pop', phone: '0722123456', email: 'ion@example.ro',
    county: 'Cluj', countyCode: 'CJ', city: 'Cluj-Napoca', street: 'Str. Memorandumului nr. 28, ap. 3', zip: '400114', country: 'RO',
  },
  parcels: 1, weightKg: 1.5, envelopes: 0, cod: 199.99, currency: 'RON', declaredValue: 0, contents: 'Cosmetice',
  ...over,
});

const recipientWith = (over) => ({ ...shipment().recipient, ...over });

test('auth: Username + SHA-512 password bytes in every body, no ClientNumberList', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await gls.createShipment(ctx, shipment());
  const expected = [...createHash('sha512').update('Parola123!', 'utf8').digest()];
  assert.equal(expected.length, 64);
  assert.deepEqual(glsPasswordBytes('Parola123!'), expected);
  for (const c of calls) {
    assert.equal(c.json.Username, 'shop@example.ro');
    assert.deepEqual(c.json.Password, expected);
    assert.ok(c.json.Password.every((b) => Number.isInteger(b) && b >= 0 && b <= 255));
    assert.equal(c.json.ClientNumberList, undefined);
  }
  assert.equal(calls[0].host, 'api.mygls.ro');
  assert.equal(calls.find((c) => c.method === 'PrintLabels').path, '/ParcelService.svc/json/PrintLabels');
  assert.equal(calls.find((c) => c.method === 'GetLocations').path, '/MasterDataService.svc/json/GetLocations');
});

test('sandbox setting switches to api.test.mygls.ro', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetParcelList: () => ({ body: { GetParcelListErrors: [], PrintDataInfoList: [] } }) }, settings: { sandbox: true } });
  const r = await gls.testConnection(ctx);
  assert.equal(calls[0].host, 'api.test.mygls.ro');
  assert.match(r.message, /Conectat la GLS \(mod test\)/);
});

test('HTTP 401 and ErrorCode 14 → AUTH_FAILED', async () => {
  const { ctx } = fakeCtx({ routes: { GetParcelList: () => ({ status: 401, body: '' }) } });
  await assert.rejects(gls.testConnection(ctx), (e) => e.code === 'AUTH_FAILED');
  const { ctx: ctx2 } = fakeCtx({ routes: { GetParcelList: () => ({ body: { GetParcelListErrors: [{ ErrorCode: 14, ErrorDescription: 'User not exists' }] } }) } });
  await assert.rejects(gls.testConnection(ctx2), (e) => e.code === 'AUTH_FAILED');
});

test('createShipment: parcel payload (COD, reference, addresses, services, date)', async () => {
  const { ctx, calls, store } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  const res = await gls.createShipment(ctx, shipment());
  assert.equal(res.awb, '50012345670');
  assert.deepEqual(res.raw.parcelIds, [9000]);
  assert.deepEqual(store.get(parcelKey(ctx, '50012345670')).parcelIds, [9000]);

  const req = calls.find((c) => c.method === 'PrintLabels').json;
  assert.equal(req.WebshopEngine, 'Shopify');
  assert.equal(req.TypeOfPrinter, 'A4_2x2');
  const p = req.ParcelList[0];
  assert.equal(p.ClientNumber, 553001234);
  assert.equal(p.ClientReference, '#2001');
  assert.equal(p.Count, 1);
  assert.equal(p.CODAmount, 199.99);
  assert.equal(p.CODReference, '#2001');
  assert.match(p.PickupDate, /^\/Date\(\d+\)\/$/);
  assert.deepEqual(p.PickupAddress, {
    Name: 'Magazin SRL', Street: 'Str. Fabricii', HouseNumber: '10', HouseNumberInfo: '', City: 'Cluj-Napoca', ZipCode: '400620',
    CountryIsoCode: 'RO', ContactName: 'Magazin SRL', ContactPhone: '+40744000111', ContactEmail: 'depozit@magazin.ro',
  });
  assert.deepEqual(p.DeliveryAddress, {
    Name: 'Ion Pop', Street: 'Str. Memorandumului', HouseNumber: '28', HouseNumberInfo: 'ap. 3', City: 'Cluj-Napoca', ZipCode: '400114',
    CountryIsoCode: 'RO', ContactName: 'Ion Pop', ContactPhone: '+40722123456', ContactEmail: 'ion@example.ro',
  });
  assert.deepEqual(p.ServiceList, [{ Code: 'FDS', FDSParameter: { Value: 'ion@example.ro' } }]);
  assert.equal(p.ParcelPropertyList[0].Weight, 1.5);
});

test('prepaid order has no COD fields; SMS + insurance + Saturday services', () => {
  const p = buildParcel(shipment({ cod: 0, declaredValue: 500, saturday: true }), { ...fakeCtx({ routes: {} }).ctx.settings, notifySms: true }, { clientNumber: 1, zip: '400114', city: 'Cluj-Napoca' });
  assert.equal(p.CODAmount, 0);
  assert.equal(p.CODReference, undefined);
  assert.deepEqual(p.ServiceList.map((s) => s.Code), ['FDS', 'FSS', 'INS', 'SAT']);
  // Live WSDL: INSParameter is ServiceParameterDecimal → a JSON number (a string would not deserialize).
  assert.strictEqual(p.ServiceList.find((s) => s.Code === 'INS').INSParameter.Value, 500);
  assert.equal(p.ServiceList.find((s) => s.Code === 'FSS').FSSParameter.Value, '+40722123456');
});

test('parcel shop / locker → PSD service with ParcelShop id; e-mail required', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await gls.createShipment(ctx, shipment({ lockerId: 'RO1234-PARCELSHOP' }));
  const p = calls.find((c) => c.method === 'PrintLabels').json.ParcelList[0];
  assert.deepEqual(p.ServiceList[0], { Code: 'PSD', PSDParameter: { StringValue: 'RO1234-PARCELSHOP' } });
  assert.equal(p.DeliveryAddress.ContactEmail, 'ion@example.ro');

  const { ctx: ctx2 } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await assert.rejects(
    gls.createShipment(ctx2, shipment({ lockerId: 'RO1', recipient: recipientWith({ email: '' }) })),
    (e) => e.code === 'ADDRESS_EMAIL_MISSING',
  );
});

test('missing ZIP → ADDRESS_ZIP_MISSING (Romanian hint) unless the city has a single ZIP', async () => {
  // nomenclator unavailable: no guessing
  const { ctx } = fakeCtx({ routes: { GetLocations: () => ({ status: 500, body: 'down' }), PrintLabels: printOk } });
  await assert.rejects(gls.createShipment(ctx, shipment({ recipient: recipientWith({ zip: '' }) })), (e) => {
    assert.equal(e.code, 'ADDRESS_ZIP_MISSING');
    assert.equal(e.field, 'shippingAddress.zip');
    assert.match(e.message, /cod(ul)? poștal/);
    assert.match(e.hint, /Completează codul poștal/);
    return true;
  });
  // city with several ZIPs
  const { ctx: ctx2 } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await assert.rejects(gls.createShipment(ctx2, shipment({ recipient: recipientWith({ zip: undefined }) })), (e) => e.code === 'ADDRESS_ZIP_MISSING' && /400114/.test(e.hint));
  // city with exactly one ZIP: derived
  const { ctx: ctx3, calls } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await gls.createShipment(ctx3, shipment({ recipient: recipientWith({ city: 'Com. Florești', zip: '' }) }));
  const addr = calls.find((c) => c.method === 'PrintLabels').json.ParcelList[0].DeliveryAddress;
  assert.equal(addr.ZipCode, '407280');
  assert.equal(addr.City, 'Floresti');
});

test('malformed ZIP → ADDRESS_ZIP_INVALID', async () => {
  const { ctx } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await assert.rejects(gls.createShipment(ctx, shipment({ recipient: recipientWith({ zip: '4001' }) })), (e) => e.code === 'ADDRESS_ZIP_INVALID' && e.field === 'shippingAddress.zip');
});

test('unknown city and unknown ZIP → ADDRESS_CITY_NOT_FOUND with suggestions; nomenclator cached', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await assert.rejects(gls.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Cluj Napoka', zip: '499999' }) })), (e) => {
    assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
    assert.equal(e.field, 'shippingAddress.city');
    assert.match(e.hint, /^Ai vrut: Cluj-Napoca/);
    return true;
  });
  await gls.createShipment(ctx, shipment());
  assert.equal(calls.filter((c) => c.method === 'GetLocations').length, 1);
});

test('București with sector: city sent as GLS spells it', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: printOk } });
  await gls.createShipment(ctx, shipment({ recipient: recipientWith({ city: 'Sector 3', county: 'București', zip: '030167' }) }));
  assert.equal(calls.find((c) => c.method === 'PrintLabels').json.ParcelList[0].DeliveryAddress.City, 'Bucuresti');
});

test('PrintLabels errors are mapped (house number 0, ZIP validation, generic)', async () => {
  const err = (list) => fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: () => ({ body: { Labels: null, PrintLabelsErrorList: list, PrintLabelsInfoList: [] } }) } }).ctx;
  await assert.rejects(gls.createShipment(err([{ ErrorCode: 23, ErrorDescription: 'The house number cannot be 0' }]), shipment()), (e) => e.code === 'ADDRESS_STREET_INVALID' && e.field === 'shippingAddress.address1');
  await assert.rejects(gls.createShipment(err([{ ErrorCode: 13, ErrorDescription: 'Invalid DeliveryAddress.ZipCode' }]), shipment()), (e) => e.code === 'ADDRESS_ZIP_INVALID' && e.details.PrintLabelsErrorList[0].ErrorCode === 13);
  await assert.rejects(gls.createShipment(err([{ ErrorCode: 13, ErrorDescription: 'Something odd' }]), shipment()), (e) => e.code === 'COURIER_REJECTED' && e.message === 'GLS a refuzat coletul.');
  await assert.rejects(gls.createShipment(err([{ ErrorCode: 1001, ErrorDescription: 'Internal Problem' }]), shipment()), (e) => e.code === 'PROVIDER_DOWN' && e.retryable);
});

test('getLabel: GetPrintedLabels by cached ParcelId, returns a Buffer', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      GetLocations: locationsBody,
      PrintLabels: printOk,
      GetPrintedLabels: (json) => ({ body: { Labels: [...PDF], GetPrintedLabelsErrorList: [], ParcelIds: json.ParcelIdList } }),
    },
  });
  const { awb } = await gls.createShipment(ctx, shipment({ parcels: 2 }));
  const buf = await gls.getLabel(ctx, awb, { format: 'A6' });
  assert.ok(Buffer.isBuffer(buf));
  assert.equal(buf.toString('latin1', 0, 5), '%PDF-');
  const req = calls.find((c) => c.method === 'GetPrintedLabels').json;
  assert.deepEqual(req.ParcelIdList, [9000, 9001]);
  assert.equal(req.TypeOfPrinter, 'Thermo');
  await gls.getLabel(ctx, awb, { format: 'A4' });
  assert.equal(calls.filter((c) => c.method === 'GetPrintedLabels').at(-1).json.TypeOfPrinter, 'A4_2x2');
});

test('getLabel without cache falls back to GetParcelList lookup', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      GetParcelList: () => ({ body: { GetParcelListErrors: [], PrintDataInfoList: [{ ParcelId: 77, ParcelNumber: 123456789 }, { ParcelId: 78, ParcelNumber: 222 }] } }),
      GetPrintedLabels: () => ({ body: { Labels: PDF.toString('base64'), GetPrintedLabelsErrorList: [] } }),
    },
  });
  const buf = await gls.getLabel(ctx, '123456789', {});
  assert.ok(Buffer.isBuffer(buf));
  assert.deepEqual(calls.find((c) => c.method === 'GetPrintedLabels').json.ParcelIdList, [77]);
});

test('cancelShipment: DeleteLabels by ParcelId; refusal mapped', async () => {
  const { ctx, calls, store } = fakeCtx({ routes: { DeleteLabels: () => ({ body: { DeleteLabelsErrorList: [], SuccessfullyDeletedList: [{ ParcelId: 9000 }] } }) } });
  store.set(parcelKey(ctx, '500'), { parcelIds: [9000] });
  await gls.cancelShipment(ctx, '500');
  assert.deepEqual(calls[0].json.ParcelIdList, [9000]);

  const { ctx: ctx2, store: store2 } = fakeCtx({ routes: { DeleteLabels: () => ({ body: { DeleteLabelsErrorList: [{ ErrorCode: 6, ErrorDescription: 'Parcel with this ID has different status than PRINTED' }] } }) } });
  store2.set(parcelKey(ctx2, '500'), { parcelIds: [9000] });
  await assert.rejects(gls.cancelShipment(ctx2, '500'), (e) => e.code === 'CANCEL_REFUSED');
});

test('track: batch statuses, informational codes skipped, dates parsed', async () => {
  const d = (iso) => `/Date(${Date.parse(iso)}+0300)/`;
  const { ctx, calls } = fakeCtx({
    routes: {
      GetParcelListStatuses: () => ({
        body: {
          GetParcelListStatusesErrors: [],
          ParcelList: [
            { ParcelNumber: 111, ParcelStatusList: [
              { StatusCode: '99', StatusDate: d('2026-05-02T09:00:00Z'), StatusDescription: 'Notificare e-mail' },
              { StatusCode: '4', StatusDate: d('2026-05-02T07:00:00Z'), StatusDescription: 'În livrare' },
              { StatusCode: '1', StatusDate: d('2026-05-01T07:00:00Z'), StatusDescription: 'Predat la GLS' },
            ] },
            { ParcelNumber: 222, ParcelStatusList: [{ StatusCode: '5', StatusDate: d('2026-05-03T10:00:00Z'), StatusDescription: 'Livrat' }] },
            { ParcelNumber: 333, ParcelStatusList: [{ StatusCode: '23', StatusDate: d('2026-05-03T10:00:00Z'), StatusDescription: 'Returnat' }] },
            { ParcelNumber: 444, ParcelStatusList: [] },
          ],
        },
      }),
    },
  });
  const res = await gls.track(ctx, ['111', '222', '333', '444']);
  assert.deepEqual(calls[0].json.ParcelNumberList, [111, 222, 333, 444]);
  assert.equal(calls[0].json.LanguageIsoCode, 'RO');
  assert.deepEqual(res.map((r) => [r.awb, r.status]), [['111', 'out_for_delivery'], ['222', 'delivered'], ['333', 'returned'], ['444', 'created']]);
  assert.equal(res[0].at, '2026-05-02T07:00:00.000Z');
  assert.equal(res[0].statusText, 'În livrare');
  assert.equal(res[1].codCollected, true);
});

test('track falls back to GetParcelStatuses when the batch method fails', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      GetParcelListStatuses: () => ({ status: 404, body: 'Endpoint not found' }),
      GetParcelStatuses: (json) => ({ body: { ParcelNumber: json.ParcelNumber, ParcelStatusList: [{ StatusCode: '17', StatusDate: '/Date(1700000000000)/', StatusDescription: 'Refuzat' }] } }),
    },
  });
  const res = await gls.track(ctx, ['10', '20']);
  assert.equal(calls.filter((c) => c.method === 'GetParcelStatuses').length, 2);
  assert.deepEqual(res.map((r) => r.status), ['returning', 'returning']);
});

test('GLS status table', () => {
  const cases = { 51: 'created', 1: 'picked_up', 2: 'in_transit', 3: 'in_transit', 4: 'out_for_delivery', 5: 'delivered', 54: 'out_for_delivery', 58: 'delivered', 11: 'failed_attempt', 12: 'failed_attempt', 20: 'failed_attempt', 17: 'returning', 23: 'returned', 40: 'returned', 91: 'cancelled', 999: 'unknown' };
  for (const [code, st] of Object.entries(cases)) assert.equal(mapGlsStatus(code), st, code);
  assert.equal(mapGlsStatus('99'), null);
  assert.equal(parseGlsDate('/Date(1598911199000+0200)/'), '2020-08-31T21:59:59.000Z');
});

test('nomenclator outage is remembered (no repeated GetLocations waits)', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetLocations: () => ({ status: 500, body: 'down' }), PrintLabels: printOk } });
  await gls.createShipment(ctx, shipment());
  await gls.createShipment(ctx, shipment());
  assert.equal(calls.filter((c) => c.method === 'GetLocations').length, 1);
  assert.equal(calls.filter((c) => c.method === 'PrintLabels').length, 2);
});

// ---- live-check regressions (fixtures from the real API, invalid credentials) ----------------

const LIVE = JSON.parse(readFileSync(new URL('./fixtures/couriers/gls.json', import.meta.url), 'utf8'));
const live = (name) => () => ({ status: LIVE[name].status, body: LIVE[name].body });

test('live: HTTP 200 + ErrorCode -1 "Unauthorized." → AUTH_FAILED on every method', async () => {
  const { ctx } = fakeCtx({ routes: { GetParcelList: live('getParcelListUnauthorized') } });
  await assert.rejects(gls.testConnection(ctx), (e) => e.code === 'AUTH_FAILED' && !e.retryable);

  const { ctx: c2, store } = fakeCtx({ routes: { GetPrintedLabels: live('getPrintedLabelsUnauthorized'), DeleteLabels: live('deleteLabelsUnauthorized') } });
  store.set(parcelKey(c2, '500'), { parcelIds: [9000] });
  await assert.rejects(gls.getLabel(c2, '500', {}), (e) => e.code === 'AUTH_FAILED');

  const { ctx: c3, store: s3 } = fakeCtx({ routes: { DeleteLabels: live('deleteLabelsUnauthorized') } });
  s3.set(parcelKey(c3, '500'), { parcelIds: [9000] });
  await assert.rejects(gls.cancelShipment(c3, '500'), (e) => e.code === 'AUTH_FAILED');

  const { ctx: c4 } = fakeCtx({ routes: { GetLocations: () => ({ status: 502, body: '<html>502 Bad Gateway</html>' }), PrintLabels: live('printLabelsLocked') } });
  await assert.rejects(gls.createShipment(c4, shipment()), (e) => {
    assert.equal(e.code, 'AUTH_FAILED');
    assert.match(e.message, /blocat temporar.*până la 11:13/);
    return true;
  });
});

test('after one rejected login no further GLS calls are made (protects the account from lockout)', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetParcelList: live('getParcelListUnauthorized'), GetParcelListStatuses: live('getParcelListStatusesBadCredentials') } });
  await assert.rejects(gls.testConnection(ctx), (e) => e.code === 'AUTH_FAILED');
  await assert.rejects(gls.track(ctx, ['1', '2', '3']), (e) => e.code === 'AUTH_FAILED');
  await assert.rejects(gls.testConnection(ctx), (e) => e.code === 'AUTH_FAILED');
  assert.equal(calls.length, 1);
  // Fixed password → different account key → calls go out again.
  const fixed = { ...ctx, credentials: { ...ctx.credentials, password: 'Corecta!' }, http: fakeCtx({ routes: { GetParcelList: () => ({ body: { GetParcelListErrors: [], PrintDataInfoList: [] } }) } }).ctx.http };
  assert.equal((await gls.testConnection(fixed)).ok, true);
});

test('track with bad credentials: the silent empty batch is double-checked, one probe, then AUTH_FAILED', async () => {
  const { ctx, calls } = fakeCtx({ routes: { GetParcelListStatuses: live('getParcelListStatusesBadCredentials'), GetParcelStatuses: live('getParcelStatusesUnauthorized') } });
  await assert.rejects(gls.track(ctx, ['111', '222', '333']), (e) => e.code === 'AUTH_FAILED');
  assert.deepEqual(calls.map((c) => c.method), ['GetParcelListStatuses', 'GetParcelStatuses']);
});

test('track: unknown / non-GLS AWBs are omitted, never reported as "created"', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      GetParcelListStatuses: () => ({ status: 404, body: 'Endpoint not found' }),
      GetParcelStatuses: (json) => (json.ParcelNumber === 10
        ? { body: { ParcelNumber: 10, GetParcelStatusErrors: [], ParcelStatusList: [{ StatusCode: '5', StatusDate: '/Date(1700000000000)/', StatusDescription: 'Livrat' }] } }
        : { body: { ...LIVE.getParcelStatusesUnauthorized.body, GetParcelStatusErrors: [{ ErrorCode: 2, ErrorDescription: 'Parcel not found.' }] } }),
    },
  });
  const res = await gls.track(ctx, ['10', '99', '1ONB2412', '10']);
  assert.deepEqual(res.map((r) => [r.awb, r.status]), [['10', 'delivered']]);
  assert.deepEqual(calls.filter((c) => c.method === 'GetParcelStatuses').map((c) => c.json.ParcelNumber), [10, 99]);
});

test('track: empty batch for real parcels (batch unusable) → per-parcel fallback', async () => {
  const { ctx } = fakeCtx({
    routes: {
      GetParcelListStatuses: () => ({ body: { GetParcelListStatusesErrors: [], ParcelList: [] } }),
      GetParcelStatuses: (json) => ({ body: { ParcelNumber: json.ParcelNumber, GetParcelStatusErrors: [], ParcelStatusList: [{ StatusCode: '1', StatusDate: '/Date(1700000000000)/', StatusDescription: 'Predat' }] } }),
    },
  });
  const res = await gls.track(ctx, ['10', '20']);
  assert.deepEqual(res.map((r) => [r.awb, r.status]), [['10', 'picked_up'], ['20', 'picked_up']]);
});

test('PrintLabels without a parcel number is not retried blindly (would duplicate the label)', async () => {
  const { ctx } = fakeCtx({ routes: { GetLocations: locationsBody, PrintLabels: () => ({ body: { Labels: null, PrintLabelsErrorList: [], PrintLabelsInfoList: [] } }) } });
  await assert.rejects(gls.createShipment(ctx, shipment()), (e) => e.code === 'COURIER_REJECTED' && e.retryable === false);
});

test('parcel map is per environment and account; COD rounded', async () => {
  const { ctx } = fakeCtx({ routes: {} });
  assert.notEqual(parcelKey(ctx, '1'), parcelKey({ ...ctx, settings: { ...ctx.settings, sandbox: true } }, '1'));
  assert.notEqual(parcelKey(ctx, '1'), parcelKey({ ...ctx, credentials: { username: 'b@x.ro', password: 'p' } }, '1'));
  const p = buildParcel(shipment({ cod: 199.98999999 }), ctx.settings, { clientNumber: 1, zip: '400114', city: 'Cluj-Napoca' });
  assert.equal(p.CODAmount, 199.99);
});

// ---- success shapes built from the official MyGLS API documentation (see _source in the fixture) ----

const DOC = JSON.parse(readFileSync(new URL('./fixtures/couriers/gls-success.json', import.meta.url), 'utf8'));

test('documented success: PrintLabels → AWB = first ParcelNumber; GetPrintedLabels byte array → PDF; DeleteLabels ok', async () => {
  const { ctx, calls } = fakeCtx({
    routes: {
      GetLocations: locationsBody,
      PrintLabels: () => ({ body: DOC.printLabels.body }),
      GetPrintedLabels: () => ({ body: DOC.getPrintedLabels.body }),
      DeleteLabels: () => ({ body: DOC.deleteLabels.body }),
    },
  });
  const res = await gls.createShipment(ctx, shipment({ reference: 'EXPEDO-TEST', parcels: 2 }));
  assert.equal(res.awb, '6110000123');
  assert.deepEqual(res.raw.parcelIds, [512345678, 512345679]);
  const label = await gls.getLabel(ctx, res.awb, { format: 'A4' });
  assert.ok(Buffer.isBuffer(label));
  assert.equal(label.subarray(0, 5).toString('latin1'), '%PDF-');
  assert.deepEqual(calls.find((c) => c.method === 'GetPrintedLabels').json.ParcelIdList, [512345678, 512345679]);
  await gls.cancelShipment(ctx, res.awb);
  assert.deepEqual(calls.find((c) => c.method === 'DeleteLabels').json.ParcelIdList, [512345678, 512345679]);
});

test('documented success: GetParcelList finds the ParcelId by ParcelNumber or ParcelNumberWithCheckdigit', async () => {
  for (const awb of ['6110000123', '61100001234']) {
    const { ctx, calls } = fakeCtx({ routes: { GetParcelList: () => ({ body: DOC.getParcelList.body }), GetPrintedLabels: () => ({ body: DOC.getPrintedLabels.body }) } });
    const pdf = await gls.getLabel(ctx, awb);
    assert.ok(Buffer.isBuffer(pdf));
    assert.deepEqual(calls.find((c) => c.method === 'GetPrintedLabels').json.ParcelIdList, [512345678], awb);
  }
});

test('documented success: GetParcelListStatuses (string StatusCode, /Date()/ dates, informational 93 skipped)', async () => {
  const { ctx } = fakeCtx({ routes: { GetParcelListStatuses: () => ({ body: DOC.getParcelListStatuses.body }) } });
  const res = await gls.track(ctx, ['6110000123', '6110000125', '6110000126', '6110000999']);
  assert.deepEqual(res, [
    { awb: '6110000123', status: 'delivered', statusText: 'The parcel has been delivered.', at: '2026-09-30T11:20:00.000Z', codCollected: true },
    { awb: '6110000125', status: 'created', statusText: 'The parcel data was entered into the GLS IT system; the parcel was not yet handed over to GLS.', at: '2026-10-01T08:00:00.000Z' },
    { awb: '6110000126', status: 'out_for_delivery', statusText: 'The parcel has been delivered at the ParcelShop (see ParcelShop information).', at: '2026-10-01T09:00:00.000Z' },
  ]);
});

test('documented success: GetParcelStatuses (single-parcel fallback) → returned to sender', async () => {
  const { ctx } = fakeCtx({
    routes: {
      GetParcelListStatuses: () => ({ status: 404, body: 'Endpoint not found' }),
      GetParcelStatuses: () => ({ body: DOC.getParcelStatuses.body }),
    },
  });
  const [r] = await gls.track(ctx, ['6110000123']);
  assert.deepEqual(r, { awb: '6110000123', status: 'returned', statusText: 'The parcel has been returned to sender.', at: '2026-10-02T07:00:00.000Z' });
});
