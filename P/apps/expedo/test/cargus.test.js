import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { ProcessingError, authError } from '../src/core/errors.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import cargus, { mapCargusEvent, mapAwbError, pickService } from '../src/couriers/cargus.js';
import { matchLocality, classifyStatusText, normalizePhoneRO, cleanCityName, detectSector } from '../src/couriers/ro-helpers.js';

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
    ctx.cache.set('cargus:token:mundishop', 'stale-token-xxxxxxxx', 3600);
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

// ---- shared helpers ------------------------------------------------------------------------

describe('ro-helpers', () => {
  test('cleanCityName / detectSector / normalizePhoneRO', () => {
    assert.equal(cleanCityName('Mun. Cluj-Napoca'), 'cluj napoca');
    assert.equal(cleanCityName('Sat Roșu, Com. Chiajna'), 'rosu');
    assert.equal(cleanCityName('Voluntari (Ilfov)'), 'voluntari');
    assert.equal(detectSector({ city: 'București, Sectorul 4' }), 4);
    assert.equal(detectSector({ city: 'Bucuresti', zip: '061344', bucharest: true }), 6);
    assert.equal(detectSector({ city: 'Bucuresti', zip: '400001', bucharest: true }), undefined);
    assert.equal(normalizePhoneRO('+40 (722) 123-456'), '0722123456');
    assert.equal(normalizePhoneRO('0040722123456'), '0722123456');
    assert.equal(normalizePhoneRO('722123456'), '0722123456');
  });

  test('matchLocality handles "contains" (county appended) and rejects unrelated names', () => {
    const cands = LOCALITIES[13].map((l) => ({ id: l.LocalityId, name: l.Name, postalCode: l.CodPostal }));
    assert.equal(matchLocality({ city: 'Turda, jud. Cluj', county: 'Cluj' }, cands).match.id, 5482);
    assert.equal(matchLocality({ city: 'Apahida Cluj', county: 'Cluj' }, cands).match.id, 5481);
    const r = matchLocality({ city: 'Gherla', county: 'Cluj' }, cands);
    assert.equal(r.notFound, true);
  });

  test('classifyStatusText checks negatives before positives', () => {
    assert.equal(classifyStatusText('Colet nelivrat'), TrackingStatus.FAILED_ATTEMPT);
    assert.equal(classifyStatusText('Coletul a fost livrat cu succes'), TrackingStatus.DELIVERED);
    assert.equal(classifyStatusText('Retur livrat la expeditor'), TrackingStatus.RETURNED);
    assert.equal(classifyStatusText('Ramburs returnat expeditorului'), TrackingStatus.DELIVERED);
  });
});
