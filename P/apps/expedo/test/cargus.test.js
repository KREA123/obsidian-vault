import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ProcessingError, authError } from '../src/core/errors.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import cargus, { mapCargusEvent, mapAwbError, pickService, tokenCacheKey } from '../src/couriers/cargus.js';

// ---- fakes ---------------------------------------------------------------------------------

/** Mimics src/lib/http.js: non-2xx → opts.mapError(status, body) || authError (401/403) || PROVIDER_REJECTED. */
function fakeHttp(routes) {
  const calls = [];
  const http = async (provider, url, opts = {}) => {
    const method = opts.method || 'GET';
    calls.push({ provider, url, method, headers: opts.headers || {}, json: opts.json, body: opts.body });
    const route = routes.find((r) => (r.method || 'GET') === method && (typeof r.url === 'string' ? url.includes(r.url) : r.url.test(url)));
    if (!route) throw new Error(`fakeHttp: no route for ${method} ${url}`);
    const res = typeof route.reply === 'function' ? route.reply({ url, opts, calls }) : route.reply;
    const status = res.status ?? 200;
    if (status >= 400) {
      const mapped = opts.mapError?.(status, res.body);
      if (mapped) throw mapped;
      if (status === 401 || status === 403) throw authError(provider, res.body);
      throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: `${provider} a refuzat cererea`, provider, details: res.body });
    }
    return { status, headers: new Headers(), body: res.body };
  };
  return { http, calls };
}

function memCache() {
  const m = new Map();
  const sets = [];
  return {
    get: (k) => { const e = m.get(k); return e && e.exp > Date.now() ? e.v : undefined; },
    set: (k, v, ttl) => { sets.push({ k, ttl }); m.set(k, { v, exp: Date.now() + ttl * 1000 }); },
    sets,
  };
}

const COUNTIES = [
  { CountyId: 1, Name: 'Bucuresti', Abbreviation: 'B' },
  { CountyId: 2, Name: 'Alba', Abbreviation: 'AB' },
  { CountyId: 13, Name: 'Cluj', Abbreviation: 'CJ' },
  { CountyId: 24, Name: 'Iasi', Abbreviation: 'IS' },
  { CountyId: 27, Name: 'Ilfov', Abbreviation: 'IF' },
];
const LOCALITIES = {
  1: [{ LocalityId: 150, Name: 'Bucuresti', CodPostal: '' }],
  2: [
    { LocalityId: 201, Name: 'Alba Iulia', CodPostal: '510001' },
    { LocalityId: 278, Name: 'Floresti', CodPostal: '517176' },
    { LocalityId: 312, Name: 'Floresti', CodPostal: '515511' },
    { LocalityId: 592, Name: 'Floresti', CodPostal: '517596' },
    { LocalityId: 653, Name: 'Floresti', CodPostal: '517684' },
  ],
  13: [
    { LocalityId: 5479, Name: 'Cluj-Napoca', CodPostal: '400001' },
    { LocalityId: 5480, Name: 'Floresti', CodPostal: '407280' },
    { LocalityId: 5481, Name: 'Apahida', CodPostal: '407035' },
    { LocalityId: 5482, Name: 'Turda', CodPostal: '401001' },
  ],
  24: [{ LocalityId: 700, Name: 'Iasi', CodPostal: '700001' }, { LocalityId: 701, Name: 'Tomesti', CodPostal: '707515' }],
  27: [
    { LocalityId: 900, Name: 'Voluntari', CodPostal: '077190' },
    { LocalityId: 901, Name: 'Popesti Leordeni', CodPostal: '077160' },
    { LocalityId: 902, Name: 'Chiajna', CodPostal: '077040' },
    { LocalityId: 903, Name: 'Rosu', CodPostal: '077042' },
    { LocalityId: 904, Name: 'Otopeni', CodPostal: '075100' },
  ],
};

const PDF_B64 = Buffer.from('%PDF-1.4\n%fake\n').toString('base64');

function baseRoutes(extra = []) {
  return [
    ...extra,
    { method: 'POST', url: '/LoginUser', reply: { body: 'tok-1234567890abcdef' } },
    { url: '/Counties?countryId=1', reply: { body: COUNTIES } },
    { url: /\/Localities\?countryId=1&countyId=(\d+)/, reply: ({ url }) => ({ body: LOCALITIES[Number(url.match(/countyId=(\d+)/)[1])] || [] }) },
    { url: '/PickupLocations', reply: { body: [{ LocationId: 201266091, Name: 'Depozit Ilfov', LocalityName: 'Tunari', CountyName: 'Ilfov', AddressText: 'Sos. Centura 32' }] } },
    { method: 'POST', url: '/Awbs', reply: { body: 1100223344 } },
  ];
}

function makeCtx(routes, { settings = {}, credentials } = {}) {
  const { http, calls } = fakeHttp(routes);
  const logs = [];
  return {
    ctx: {
      credentials: credentials || { subscriptionKey: 'sub-key-123', username: 'mundishop', password: 'secret' },
      settings: { pickupPointId: '201266091', ...settings },
      http,
      cache: memCache(),
      log: (m, d) => logs.push({ m, d }),
    },
    calls,
    logs,
  };
}

function shipment(over = {}) {
  return {
    reference: '#1024',
    recipient: {
      name: 'Ion Popescu', contactPerson: 'Ion Popescu', phone: '0722123456', email: 'ion@example.com',
      county: 'Cluj', countyCode: 'CJ', city: 'Cluj-Napoca', street: 'Str. Memorandumului 28, ap. 4', zip: '400114', country: 'RO',
      ...(over.recipient || {}),
    },
    parcels: 1, weightKg: 1.2, envelopes: 0, cod: 149.9, currency: 'RON', declaredValue: 0, contents: 'Jucării',
    ...Object.fromEntries(Object.entries(over).filter(([k]) => k !== 'recipient')),
  };
}

const awbCall = (calls) => calls.find((c) => c.method === 'POST' && c.url.endsWith('/Awbs'));

// ---- auth ----------------------------------------------------------------------------------

describe('cargus auth', () => {
  test('logs in once, caches the token and sends subscription key + bearer', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await cargus.listPickupPoints(ctx);
    await cargus.listPickupPoints(ctx);
    const logins = calls.filter((c) => c.url.endsWith('/LoginUser'));
    assert.equal(logins.length, 1);
    assert.deepEqual(logins[0].json, { UserName: 'mundishop', Password: 'secret' });
    assert.equal(logins[0].headers['Ocp-Apim-Subscription-Key'], 'sub-key-123');
    const pl = calls.filter((c) => c.url.endsWith('/PickupLocations'));
    assert.equal(pl.length, 2);
    assert.equal(pl[1].headers.Authorization, 'Bearer tok-1234567890abcdef');
    assert.equal(pl[1].headers['Ocp-Apim-Subscription-Key'], 'sub-key-123');
    const tokenSet = ctx.cache.sets.find((s) => s.k.startsWith('cargus:token'));
    assert.ok(tokenSet.ttl > 20 * 3600 && tokenSet.ttl <= 24 * 3600);
  });

  test('expired token (401) → logs in again and retries once', async () => {
    let n = 0;
    const { ctx, calls } = makeCtx(baseRoutes([
      { url: '/PickupLocations', reply: () => (n++ === 0 ? { status: 401, body: 'Failed to authenticate!' } : { body: [] }) },
    ]));
    ctx.cache.set(tokenCacheKey(ctx), 'stale-token-xxxxxxxx', 3600);
    const points = await cargus.listPickupPoints(ctx);
    assert.deepEqual(points, []);
    assert.equal(calls.filter((c) => c.url.endsWith('/LoginUser')).length, 1);
    assert.equal(calls.filter((c) => c.url.endsWith('/PickupLocations'))[1].headers.Authorization, 'Bearer tok-1234567890abcdef');
  });

  test('bad credentials → AUTH_FAILED; bad subscription key → specific Romanian message', async () => {
    const bad = makeCtx(baseRoutes([{ method: 'POST', url: '/LoginUser', reply: { status: 400, body: 'Failed to authenticate!' } }]));
    await assert.rejects(cargus.testConnection(bad.ctx), (e) => e.code === 'AUTH_FAILED' && /Cargus/.test(e.message));

    const badKey = makeCtx(baseRoutes([{ method: 'POST', url: '/LoginUser', reply: { status: 401, body: { statusCode: 401, message: 'Access denied due to invalid subscription key.' } } }]));
    await assert.rejects(cargus.testConnection(badKey.ctx), (e) => e.code === 'AUTH_FAILED' && /Primary key/.test(e.message) && !/[{}]/.test(e.message));
  });

  test('testConnection reports pickup points in Romanian', async () => {
    const { ctx } = makeCtx(baseRoutes());
    const r = await cargus.testConnection(ctx);
    assert.equal(r.ok, true);
    assert.match(r.message, /Conectat la Cargus\. Am găsit 1 punct de ridicare\./);
    const r2 = await cargus.testConnection({ ...ctx, settings: { pickupPointId: '999' } });
    assert.match(r2.message, /999 din setări nu e în listă/);
  });
});

// ---- locality resolution -------------------------------------------------------------------

describe('cargus locality resolution', () => {
  const resolveVia = async (recipient) => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await cargus.createShipment(ctx, shipment({ recipient }));
    return { payload: awbCall(calls).json, calls, ctx };
  };

  test('diacritics, hyphens and "Mun." prefix resolve to the Cargus LocalityId', async () => {
    for (const city of ['Cluj-Napoca', 'cluj napoca', 'Mun. Cluj-Napoca', 'CLUJ–NAPOCA', 'Municipiul Cluj Napoca']) {
      const { payload } = await resolveVia({ city });
      assert.equal(payload.Recipient.LocalityId, 5479, city);
      assert.equal(payload.Recipient.LocalityName, 'Cluj-Napoca');
      assert.equal(payload.Recipient.CountyId, 13);
    }
    const { payload } = await resolveVia({ county: 'Iași', countyCode: 'IS', city: 'Iași', zip: '700259' });
    assert.equal(payload.Recipient.LocalityId, 700);
    const pl = await resolveVia({ county: 'Ilfov', countyCode: 'IF', city: 'Popești-Leordeni', zip: '' });
    assert.equal(pl.payload.Recipient.LocalityId, 901);
    const com = await resolveVia({ county: 'Ilfov', countyCode: 'IF', city: 'Com. Chiajna', zip: '' });
    assert.equal(com.payload.Recipient.LocalityId, 902);
  });

  test('"București Sector 3" → Bucuresti (LocalityId 150)', async () => {
    const { payload } = await resolveVia({ county: 'București', countyCode: 'B', city: 'București Sector 3', sector: 3, zip: '030167' });
    assert.equal(payload.Recipient.LocalityId, 150);
    assert.equal(payload.Recipient.LocalityName, 'Bucuresti');
    assert.equal(payload.Recipient.CountyName, 'Bucuresti');
    const s = await resolveVia({ county: 'Bucuresti', countyCode: 'B', city: 'Sectorul 3', zip: '' });
    assert.equal(s.payload.Recipient.LocalityId, 150);
  });

  test('Ilfov locality typed with county București is found in Ilfov', async () => {
    const { payload } = await resolveVia({ county: 'București', countyCode: 'B', city: 'Voluntari', zip: '' });
    assert.equal(payload.Recipient.LocalityId, 900);
    assert.equal(payload.Recipient.CountyName, 'Ilfov');
  });

  test('ambiguous village name → ADDRESS_CITY_NOT_FOUND with suggestions; postal code disambiguates', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    const s = shipment({ recipient: { county: 'Alba', countyCode: 'AB', city: 'Florești', zip: '' } });
    await assert.rejects(cargus.createShipment(ctx, s), (e) => {
      assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
      assert.equal(e.field, 'shippingAddress.city');
      assert.match(e.message, /Florești/);
      assert.match(e.message, /Alba/);
      assert.match(e.hint, /^Ai vrut: Floresti \(cod 517176\), Floresti \(cod 515511\), Floresti \(cod 517596\)\?/);
      return true;
    });
    assert.equal(awbCall(calls), undefined, 'no AWB call when locality is ambiguous');

    const { payload } = await resolveVia({ county: 'Alba', countyCode: 'AB', city: 'Floresti', zip: '515511' });
    assert.equal(payload.Recipient.LocalityId, 312);
  });

  test('unknown locality → error naming locality + county, up to 3 closest Cargus names', async () => {
    const { ctx } = makeCtx(baseRoutes());
    const s = shipment({ recipient: { city: 'Cluj Napocca Est', zip: '' } });
    await assert.rejects(cargus.createShipment(ctx, s), (e) => {
      assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
      assert.match(e.message, /„Cluj Napocca Est” nu există în nomenclatorul Cargus pentru județul Cluj/);
      assert.match(e.hint, /^Ai vrut: Cluj-Napoca/);
      assert.ok(e.hint.split('?')[0].split(',').length <= 3);
      return true;
    });
  });

  test('one-letter typo and zip-only matches are accepted', async () => {
    const typo = await resolveVia({ city: 'Cluj-Napoka' });
    assert.equal(typo.payload.Recipient.LocalityId, 5479);
    const zip = await resolveVia({ county: 'Ilfov', countyCode: 'IF', city: 'Pipera', zip: '077190' });
    assert.equal(zip.payload.Recipient.LocalityId, 900);
  });

  test('nomenclator is cached per county for 7 days', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await cargus.createShipment(ctx, shipment());
    await cargus.createShipment(ctx, shipment());
    assert.equal(calls.filter((c) => c.url.includes('/Localities')).length, 1);
    assert.equal(calls.filter((c) => c.url.includes('/Counties')).length, 1);
    const set = ctx.cache.sets.find((x) => x.k === 'cargus:localities:13');
    assert.equal(set.ttl, 7 * 24 * 3600);
  });

  test('unknown county → ADDRESS_COUNTY_NOT_FOUND', async () => {
    const { ctx } = makeCtx(baseRoutes());
    await assert.rejects(cargus.createShipment(ctx, shipment({ recipient: { county: 'Atlantida', countyCode: 'XX' } })),
      (e) => e.code === 'ADDRESS_COUNTY_NOT_FOUND' && e.field === 'shippingAddress.province');
  });
});

// ---- createShipment payload ----------------------------------------------------------------

describe('cargus createShipment', () => {
  test('payload: sender point, COD to collector account, reference, service by weight, phone normalized', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    const res = await cargus.createShipment(ctx, shipment({ recipient: { phone: '+40 722 123 456' }, notes: 'Sunați înainte', openPackage: true, saturday: true, declaredValue: 150 }));
    assert.equal(res.awb, '1100223344');
    const p = awbCall(calls).json;
    assert.deepEqual(p.Sender, { LocationId: 201266091 });
    assert.equal(p.BankRepayment, 149.9);
    assert.equal(p.CashRepayment, 0);
    assert.equal(p.CustomString, '#1024');
    assert.equal(p.ServiceId, 34);
    assert.equal(p.TotalWeight, 2);
    assert.equal(p.Parcels, 1);
    assert.equal(p.ParcelCodes.length, 1);
    assert.equal(p.ParcelCodes[0].Type, 1);
    assert.equal(p.ShipmentPayer, 1);
    assert.equal(p.OpenPackage, true);
    assert.equal(p.SaturdayDelivery, true);
    assert.equal(p.DeclaredValue, 150);
    assert.equal(p.Observations, 'Sunați înainte');
    assert.equal(p.PackageContent, 'Jucării');
    assert.equal(p.Recipient.PhoneNumber, '0722123456');
    assert.equal(p.Recipient.AddressText, 'Str. Memorandumului 28, ap. 4');
    assert.equal(p.Recipient.CodPostal, '400114');
    assert.equal(p.Recipient.Email, 'ion@example.com');
    assert.equal(p.PriceTableId, undefined);
  });

  test('cash COD, prepaid, multi-parcel, heavy shipment, price table', async () => {
    const { ctx, calls } = makeCtx(baseRoutes(), { settings: { codType: 'cash', priceTableId: '23049' } });
    await cargus.createShipment(ctx, shipment({ parcels: 3, weightKg: 40.2 }));
    const p = awbCall(calls).json;
    assert.equal(p.CashRepayment, 149.9);
    assert.equal(p.BankRepayment, 0);
    assert.equal(p.ServiceId, 35);
    assert.equal(p.TotalWeight, 41);
    assert.equal(p.ParcelCodes.length, 3);
    assert.equal(p.ParcelCodes.reduce((a, x) => a + x.Weight, 0), 41);
    assert.equal(p.PriceTableId, 23049);

    const prepaid = makeCtx(baseRoutes());
    await cargus.createShipment(prepaid.ctx, shipment({ cod: 0 }));
    const q = awbCall(prepaid.calls).json;
    assert.equal(q.CashRepayment, 0);
    assert.equal(q.BankRepayment, 0);
  });

  test('pickService: explicit service wins, weight thresholds otherwise', () => {
    assert.equal(pickService({}, { weightKg: 31 }), 34);
    assert.equal(pickService({}, { weightKg: 31.5 }), 35);
    assert.equal(pickService({}, { weightKg: 80 }), 36);
    assert.equal(pickService({ service: '39' }, { weightKg: 5 }), 39);
    assert.equal(pickService({ service: '34' }, { weightKg: 5, service: '1' }), 1);
    assert.equal(pickService({}, { weightKg: 5, lockerId: '114142' }), 38);
  });

  test('Ship & Go locker: DeliveryPudoPoint + service 38, no locality lookup, email required', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await cargus.createShipment(ctx, shipment({ lockerId: '114142', openPackage: true }));
    const p = awbCall(calls).json;
    assert.equal(p.DeliveryPudoPoint, 114142);
    assert.equal(p.ServiceId, 38);
    assert.equal(p.OpenPackage, undefined);
    assert.equal(p.BankRepayment, 149.9);
    assert.deepEqual(Object.keys(p.Recipient).sort(), ['ContactPerson', 'Email', 'Name', 'PhoneNumber']);
    assert.equal(calls.filter((c) => c.url.includes('/Localities')).length, 0);

    const noMail = makeCtx(baseRoutes());
    await assert.rejects(cargus.createShipment(noMail.ctx, shipment({ lockerId: '114142', recipient: { email: '' } })),
      (e) => e.code === 'ADDRESS_EMAIL_MISSING' && /Ship & Go/.test(e.message));
  });

  test('missing pickup point: uses the only one, otherwise asks for it', async () => {
    const one = makeCtx(baseRoutes(), { settings: { pickupPointId: '' } });
    await cargus.createShipment(one.ctx, shipment());
    assert.deepEqual(awbCall(one.calls).json.Sender, { LocationId: 201266091 });

    const many = makeCtx(baseRoutes([{ url: '/PickupLocations', reply: { body: [{ LocationId: 1, Name: 'A' }, { LocationId: 2, Name: 'B' }] } }]), { settings: { pickupPointId: '' } });
    await assert.rejects(cargus.createShipment(many.ctx, shipment()),
      (e) => e.code === 'CONFIG_PICKUP_POINT_MISSING' && /Nu e ales punctul de ridicare Cargus/.test(e.message) && /ID 1/.test(e.hint));
  });

  test('WithGetAwb-style array response is accepted', async () => {
    const { ctx } = makeCtx(baseRoutes([{ method: 'POST', url: '/Awbs', reply: { body: [{ BarCode: '1199887766', ReturnCode: '' }] } }]));
    const r = await cargus.createShipment(ctx, shipment());
    assert.equal(r.awb, '1199887766');
  });
});

// ---- error mapping -------------------------------------------------------------------------

describe('cargus error mapping', () => {
  const cases = [
    [['Telefonul destinatarului este invalid'], 'ADDRESS_PHONE_INVALID', 'shippingAddress.phone'],
    [{ Message: 'The request is invalid.', ModelState: { 'awb.Recipient.PhoneNumber': ['The PhoneNumber field is required.'] } }, 'ADDRESS_PHONE_INVALID', 'shippingAddress.phone'],
    ['Greutatea totala depaseste limita serviciului', 'SHIPMENT_WEIGHT_INVALID', 'weightKg'],
    ['Localitatea destinatarului nu este valida', 'ADDRESS_CITY_NOT_FOUND', 'shippingAddress.city'],
    [['Invalid LocationId for sender'], 'CONFIG_PICKUP_POINT_INVALID', 'settings.pickupPointId'],
    ['Punctul PUDO nu accepta ramburs', 'LOCKER_INVALID', 'lockerId'],
    ['Something odd happened', 'PROVIDER_REJECTED', undefined],
  ];
  for (const [body, code, field] of cases) {
    test(`${JSON.stringify(body).slice(0, 60)} → ${code}`, async () => {
      const { ctx } = makeCtx(baseRoutes([{ method: 'POST', url: '/Awbs', reply: { status: 400, body } }]));
      await assert.rejects(cargus.createShipment(ctx, shipment()), (e) => {
        assert.equal(e.code, code);
        assert.equal(e.field, field);
        assert.equal(e.provider, 'cargus');
        assert.equal(e.retryable, false);
        assert.ok(!/[{}[\]]/.test(e.message), `no JSON in message: ${e.message}`);
        assert.deepEqual(e.details, body);
        return true;
      });
    });
  }

  test('empty/garbage 200 response is an error, not a fake AWB', async () => {
    const { ctx } = makeCtx(baseRoutes([{ method: 'POST', url: '/Awbs', reply: { body: [{ Error: 'Localitate invalida' }] } }]));
    await assert.rejects(cargus.createShipment(ctx, shipment()), (e) => e.code === 'ADDRESS_CITY_NOT_FOUND');
  });

  test('mapAwbError never puts raw JSON in the message', () => {
    const e = mapAwbError({ weird: { nested: true } }, shipment(), 400);
    assert.equal(e.code, 'PROVIDER_REJECTED');
    assert.equal(e.message, 'Cargus a refuzat AWB-ul (cod 400).');
  });
});

// ---- label, cancel, tracking ---------------------------------------------------------------

describe('cargus label / cancel / track', () => {
  test('getLabel decodes the base64 PDF; A6 → format=1, A4 → format=0', async () => {
    const { ctx, calls } = makeCtx(baseRoutes([{ url: '/AwbDocuments', reply: { body: PDF_B64 } }]));
    const pdf = await cargus.getLabel(ctx, '1100223344', { format: 'A6' });
    assert.ok(Buffer.isBuffer(pdf));
    assert.equal(pdf.subarray(0, 4).toString(), '%PDF');
    assert.match(calls.at(-1).url, /AwbDocuments\?barCodes=%5B1100223344%5D&type=PDF&format=1&printMainOnce=1$/);
    await cargus.getLabel(ctx, '1100223344', { format: 'A4' });
    assert.match(calls.at(-1).url, /format=0/);
  });

  test('getLabel with a non-PDF answer → LABEL_UNAVAILABLE', async () => {
    const { ctx } = makeCtx(baseRoutes([{ url: '/AwbDocuments', reply: { body: '' } }]));
    await assert.rejects(cargus.getLabel(ctx, '1'), (e) => e.code === 'LABEL_UNAVAILABLE');
  });

  test('cancelShipment: DELETE Awbs?barCode=; false → CANCEL_REFUSED', async () => {
    const ok = makeCtx(baseRoutes([{ method: 'DELETE', url: '/Awbs?barCode=1100223344', reply: { body: true } }]));
    await cargus.cancelShipment(ok.ctx, '1100223344');
    assert.equal(ok.calls.at(-1).method, 'DELETE');
    const no = makeCtx(baseRoutes([{ method: 'DELETE', url: '/Awbs?barCode=', reply: { body: false } }]));
    await assert.rejects(cargus.cancelShipment(no.ctx, '1100223344'), (e) => e.code === 'CANCEL_REFUSED' && /ridicat de curier/.test(e.hint));
  });

  test('track: batch AwbTrace/WithRedirect, latest event wins, missing AWBs omitted', async () => {
    const trace = [
      { Code: '111', Event: [
        { Date: '2026-09-30T10:00:00', EventId: 1, Description: 'Expeditie preluata de curier', LocalityName: 'Tunari' },
        { Date: '2026-10-01T12:30:00', EventId: 21, Description: 'Confirmat', LocalityName: 'Cluj-Napoca' },
        { Date: '2026-10-01T08:00:00', EventId: 5, Description: 'In livrare', LocalityName: 'Cluj-Napoca' },
      ] },
      { Code: '222', Event: [{ Date: '2026-10-01T09:00:00', EventId: 7, Description: 'Destinatar absent', LocalityName: 'Iasi' }] },
      { Code: '333', Event: [] },
    ];
    const { ctx, calls } = makeCtx(baseRoutes([{ url: '/AwbTrace/WithRedirect', reply: { body: trace } }]));
    const res = await cargus.track(ctx, ['111', '222', '333', '444']);
    assert.match(calls.at(-1).url, /AwbTrace\/WithRedirect\?barCode=%5B111%2C222%2C333%2C444%5D$/);
    assert.deepEqual(res.map((r) => [r.awb, r.status]), [
      ['111', TrackingStatus.DELIVERED], ['222', TrackingStatus.FAILED_ATTEMPT], ['333', TrackingStatus.CREATED],
    ]);
    assert.equal(res[0].statusText, 'Confirmat');
    assert.equal(res[0].codCollected, true);
    assert.ok(res[0].at);
  });

  test('status mapping table', () => {
    const table = [
      [{ EventId: 21, Description: 'Confirmat' }, TrackingStatus.DELIVERED],
      [{ EventId: 99, Description: 'Livrat' }, TrackingStatus.DELIVERED],
      [{ Description: 'Expeditie preluata de la expeditor' }, TrackingStatus.PICKED_UP],
      [{ Description: 'Sosit in depozitul Cluj' }, TrackingStatus.IN_TRANSIT],
      [{ Description: 'In tranzit spre destinatie' }, TrackingStatus.IN_TRANSIT],
      [{ Description: 'Predat curierului pentru livrare' }, TrackingStatus.OUT_FOR_DELIVERY],
      [{ Description: 'Disponibil pentru ridicare in Ship & Go' }, TrackingStatus.OUT_FOR_DELIVERY],
      [{ Description: 'Nelivrat - adresa incompleta' }, TrackingStatus.FAILED_ATTEMPT],
      [{ Description: 'Livrare amanata la cererea destinatarului' }, TrackingStatus.FAILED_ATTEMPT],
      [{ Description: 'Refuzat de destinatar' }, TrackingStatus.RETURNING],
      [{ Description: 'Retur catre expeditor' }, TrackingStatus.RETURNING],
      [{ Description: 'Returnat la expeditor' }, TrackingStatus.RETURNED],
      [{ Description: 'AWB anulat' }, TrackingStatus.CANCELLED],
      [{ Description: 'AWB tiparit' }, TrackingStatus.CREATED],
      [{ Description: 'Ceva complet nou' }, TrackingStatus.UNKNOWN],
      [undefined, TrackingStatus.CREATED],
    ];
    for (const [ev, expected] of table) assert.equal(mapCargusEvent(ev), expected, JSON.stringify(ev));
  });

  test('listLockers filters PudoPoints by county/city and caches', async () => {
    const pudo = [
      { Id: 114142, Name: 'CARGUS SHIP & GO MAGURELE', City: 'Magurele', County: 'Ilfov', StreetName: 'Atomistilor', StreetNo: '99-115', ServiceCOD: false },
      { Id: 114143, Name: 'SHIP & GO CLUJ', City: 'Cluj-Napoca', County: 'Cluj', StreetName: 'Fabricii', StreetNo: '1', ServiceCOD: true },
    ];
    const { ctx, calls } = makeCtx(baseRoutes([{ url: '/PudoPoints', reply: { body: pudo } }]));
    const l = await cargus.listLockers(ctx, { county: 'Cluj', city: 'cluj napoca' });
    assert.deepEqual(l.map((x) => x.id), ['114143']);
    assert.equal(l[0].address, 'Fabricii 1, Cluj-Napoca, Cluj');
    await cargus.listLockers(ctx, { county: 'Ilfov' });
    assert.equal(calls.filter((c) => c.url.endsWith('/PudoPoints')).length, 1);
  });
});

// ---- live-check regressions (fixtures from the real API, invalid credentials) ----------------

const LIVE = JSON.parse(readFileSync(new URL('./fixtures/couriers/cargus.json', import.meta.url), 'utf8'));

describe('cargus: live error shapes and hardening', () => {
  test('real APIM 401 for a bad / missing subscription key → AUTH_FAILED about the Primary key, not retried', async () => {
    for (const sample of [LIVE.loginBadSubscriptionKey, LIVE.loginMissingSubscriptionKey]) {
      const { ctx, calls } = makeCtx(baseRoutes([{ method: 'POST', url: '/LoginUser', reply: { status: sample.status, body: sample.body } }]));
      await assert.rejects(cargus.testConnection(ctx), (e) => {
        assert.equal(e.code, 'AUTH_FAILED');
        assert.equal(e.retryable, false);
        assert.match(e.message, /Primary key/);
        return true;
      });
      assert.equal(calls.length, 1);
    }
    // Same answer on an authenticated call with a cached token: no re-login loop.
    const { ctx, calls } = makeCtx(baseRoutes([{ url: '/PickupLocations', reply: { status: 401, body: LIVE.authenticatedEndpointBadKey.body } }]));
    ctx.cache.set(tokenCacheKey(ctx), 'cached-token-xxxxxxxx', 3600);
    await assert.rejects(cargus.listPickupPoints(ctx), (e) => e.code === 'AUTH_FAILED' && /Primary key/.test(e.message));
    assert.equal(calls.filter((c) => c.url.endsWith('/LoginUser')).length, 0);
  });

  test('token cache key differs per account (key, user, password) and never contains the secrets', () => {
    const k = (credentials) => tokenCacheKey({ credentials });
    const base = { subscriptionKey: 'sub-1', username: 'shop', password: 'p1' };
    assert.notEqual(k(base), k({ ...base, subscriptionKey: 'sub-2' }));
    assert.notEqual(k(base), k({ ...base, username: 'shop2' }));
    assert.notEqual(k(base), k({ ...base, password: 'p2' }));
    assert.ok(!/sub-1|p1|shop/.test(k(base)));
  });

  test('two accounts in one store do not share a token', async () => {
    const routes = baseRoutes([{ method: 'POST', url: '/LoginUser', reply: ({ opts }) => ({ body: `tok-for-${opts.json.UserName}-xxxxxxxx` }) }]);
    const { ctx, calls } = makeCtx(routes);
    await cargus.listPickupPoints(ctx);
    const other = { ...ctx, credentials: { subscriptionKey: 'sub-key-999', username: 'second-account', password: 'x' } };
    await cargus.listPickupPoints(other);
    const pl = calls.filter((c) => c.url.endsWith('/PickupLocations'));
    assert.equal(pl[0].headers.Authorization, 'Bearer tok-for-mundishop-xxxxxxxx');
    assert.equal(pl[1].headers.Authorization, 'Bearer tok-for-second-account-xxxxxxxx');
  });

  test('COD in another currency is refused (Cargus has no currency field); amounts rounded to bani', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await assert.rejects(cargus.createShipment(ctx, shipment({ cod: 49.9, currency: 'EUR' })), (e) => e.code === 'COD_CURRENCY_UNSUPPORTED');
    assert.equal(awbCall(calls), undefined);
    await cargus.createShipment(ctx, shipment({ cod: 149.89999999999, declaredValue: 99.999 }));
    assert.equal(awbCall(calls).json.BankRepayment, 149.9);
    assert.equal(awbCall(calls).json.DeclaredValue, 100);
  });

  test('zone-less AwbTrace dates are Bucharest time, not the server zone', async () => {
    const trace = [{ Code: '111', Event: [{ Date: '2026-07-01T12:30:00', EventId: 21, Description: 'Confirmat' }] }];
    const { ctx } = makeCtx(baseRoutes([{ url: '/AwbTrace/WithRedirect', reply: { body: trace } }]));
    const [r] = await cargus.track(ctx, ['111']);
    assert.equal(r.at, '2026-07-01T09:30:00.000Z');
  });
});

// ---- success shapes: official WP plugin's cached API bodies + docs V3 2.3.2 (see _source in the fixture) ----

const OKC = JSON.parse(readFileSync(new URL('./fixtures/couriers/cargus-success.json', import.meta.url), 'utf8'));
const okRoutes = (extra = []) => [
  ...extra,
  { method: 'POST', url: '/LoginUser', reply: { body: OKC.loginUser.body } },
  { url: '/Counties?countryId=1', reply: { body: OKC.counties.body } },
  { url: /\/Localities\?countryId=1&countyId=(\d+)/, reply: ({ url }) => ({ body: OKC.localities.byCounty[url.match(/countyId=(\d+)/)[1]] || [] }) },
  { url: '/PickupLocations', reply: { body: OKC.pickupLocations.body } },
  { url: '/PudoPoints', reply: { body: OKC.pudoPoints.body } },
  { method: 'POST', url: '/Awbs', reply: { body: OKC.awbsPostNumeric.body } },
];

describe('cargus: documented success bodies', () => {
  test('LoginUser string token → Bearer; PickupLocations (documented Sender shape) → pick-up points', async () => {
    const { ctx, calls } = makeCtx(okRoutes(), { settings: { pickupPointId: '' } });
    const conn = await cargus.testConnection(ctx);
    assert.equal(conn.ok, true);
    assert.deepEqual(conn.info.pickupPoints, [{ id: '1005962049', name: 'ECOM TEST', address: 'nr: 32; Sos centura nr 32, Tunari, Ilfov' }]);
    assert.equal(calls.find((c) => c.url.endsWith('/PickupLocations')).headers.Authorization, `Bearer ${OKC.loginUser.body}`);
  });

  test('real Counties list (44 rows) + Localities fields → București and Voluntari resolve to their ids', async () => {
    const { ctx, calls } = makeCtx(okRoutes(), { settings: { pickupPointId: '' } });
    const res = await cargus.createShipment(ctx, shipment({
      reference: 'EXPEDO-TEST',
      recipient: { name: 'Test Expedo', contactPerson: 'Test Expedo', phone: '0700000000', county: 'Ilfov', countyCode: 'IF', city: 'Voluntari', street: 'Str. Test 1', zip: '077190' },
    }));
    assert.equal(res.awb, '804419419'); // POST Awbs answers the bare barcode (a JSON number)
    const p = awbCall(calls).json;
    assert.equal(p.Sender.LocationId, 1005962049); // the only pick-up point is used when none is set
    assert.deepEqual([p.Recipient.CountyId, p.Recipient.CountyName, p.Recipient.LocalityId, p.Recipient.LocalityName], [27, 'Ilfov', 29445920, 'Voluntari']);
    assert.equal(p.BankRepayment, 149.9);
    const buc = makeCtx(okRoutes());
    await cargus.createShipment(buc.ctx, shipment({ recipient: { county: 'București', countyCode: 'B', city: 'București Sector 3', sector: 3, zip: '030167' } }));
    assert.equal(awbCall(buc.calls).json.Recipient.LocalityId, 150);
  });

  test('alphanumeric barcode (docs 9.7/9.8 "URGC10875236") is accepted; error texts are not', async () => {
    const toVoluntari = () => shipment({ recipient: { county: 'Ilfov', countyCode: 'IF', city: 'Voluntari', zip: '077190' } });
    const { ctx } = makeCtx(okRoutes([{ method: 'POST', url: '/Awbs', reply: { body: OKC.awbsPostAlphanumeric.body } }]));
    assert.equal((await cargus.createShipment(ctx, toVoluntari())).awb, 'URGC10875236');
    for (const text of ['Error', 'Failed to authenticate!', 'Invalid']) {
      const bad = makeCtx(okRoutes([{ method: 'POST', url: '/Awbs', reply: { body: text } }]));
      await assert.rejects(cargus.createShipment(bad.ctx, toVoluntari()), (e) => e instanceof ProcessingError && !e.message.includes('URGC'), text);
    }
  });

  test('AwbDocuments base64 → PDF Buffer; DELETE true ok, false refused', async () => {
    const { ctx, calls } = makeCtx(okRoutes([
      { url: '/AwbDocuments', reply: { body: OKC.awbDocuments.body } },
      { method: 'DELETE', url: '/Awbs?barCode=804419419', reply: { body: OKC.deleteAwb.body } },
    ]));
    const pdf = await cargus.getLabel(ctx, '804419419', { format: 'A6' });
    assert.equal(pdf.subarray(0, 5).toString('latin1'), '%PDF-');
    assert.match(calls.find((c) => c.url.includes('/AwbDocuments')).url, /barCodes=%5B804419419%5D&type=PDF&format=1/);
    await cargus.cancelShipment(ctx, '804419419');
    const refused = makeCtx(okRoutes([{ method: 'DELETE', url: '/Awbs?barCode=', reply: { body: OKC.deleteAwbRefused.body } }]));
    await assert.rejects(cargus.cancelShipment(refused.ctx, '804419419'), (e) => e.code === 'CANCEL_REFUSED');
  });

  test('AwbTrace/WithRedirect documented fields → delivered (EventId 21) / created (no events)', async () => {
    const { ctx } = makeCtx(okRoutes([{ url: '/AwbTrace/WithRedirect', reply: { body: OKC.awbTrace.body } }]));
    const res = await cargus.track(ctx, ['804419419', '804418863']);
    assert.deepEqual(res, [
      { awb: '804419419', status: 'delivered', statusText: 'Confirmat', at: '2019-10-25T10:33:12.035Z', codCollected: true },
      { awb: '804418863', status: 'created', statusText: 'AWB emis', at: undefined, codCollected: false },
    ]);
  });

  test('real PudoPoints rows: full Address used even when StreetName is empty; București/Ilfov filters', async () => {
    const { ctx } = makeCtx(okRoutes());
    const all = await cargus.listLockers(ctx, {});
    assert.equal(all.length, 3);
    for (const l of all) assert.ok(l.address.length > 20, `address too short: ${l.address}`);
    assert.deepEqual((await cargus.listLockers(ctx, { county: 'Maramureș', city: 'Târgu Lăpuș' })).map((l) => [l.id, l.address]),
      [['229937', 'Targu Lapus, STR DOINEI NR 19 AP 9, Nr. n/a, Cod postal. 435600']]);
    assert.deepEqual((await cargus.listLockers(ctx, { county: 'București', city: 'București' })).map((l) => l.id), ['114141']);
    assert.deepEqual((await cargus.listLockers(ctx, { county: 'Ilfov', city: 'Voluntari' })).map((l) => l.id), ['230819']);
  });
});
