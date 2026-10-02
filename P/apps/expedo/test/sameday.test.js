import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { ProcessingError, authError } from '../src/core/errors.js';
import { TrackingStatus } from '../src/couriers/contract.js';
import sameday, { mapSamedayStatus, mapAwbError, toForm, tokenTtl, tokenKey, PROD_URL, SANDBOX_URL } from '../src/couriers/sameday.js';

// ---- fakes ---------------------------------------------------------------------------------

/** Mimics src/lib/http.js: non-2xx → opts.mapError(status, body) || authError (401/403) || PROVIDER_REJECTED. */
function fakeHttp(routes) {
  const calls = [];
  const http = async (provider, url, opts = {}) => {
    const method = opts.method || 'GET';
    calls.push({ provider, url, method, headers: opts.headers || {}, body: opts.body, responseType: opts.responseType });
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

const page = (data) => ({ data, currentPage: 1, pages: 1, perPage: 500, total: data.length });
const inTwoDays = () => {
  const d = new Date(Date.now() + 2 * 24 * 3600 * 1000);
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)}`;
};

const COUNTIES = [
  { id: 10, name: 'Bucuresti', code: 'B' },
  { id: 1, name: 'Alba', code: 'AB' },
  { id: 13, name: 'Cluj', code: 'CJ' },
  { id: 23, name: 'Ilfov', code: 'IF' },
];
// Real names / postal codes from Sameday's nomenclator (woocommerce-plugin/classes/files/cities.json).
const CITIES = {
  10: [1, 2, 3, 4, 5, 6].map((n) => ({ id: n, name: `Sectorul ${n}`, postalCode: `0${n}0011`, county: { id: 10, name: 'Bucuresti', code: 'B' } })),
  1: [
    { id: 111, name: 'Abrud', postalCode: '515100' },
    { id: 278, name: 'Floresti', postalCode: '517176' },
    { id: 312, name: 'Floresti', postalCode: '515511' },
    { id: 592, name: 'Floresti', postalCode: '517596' },
    { id: 653, name: 'Floresti', postalCode: '517684' },
  ],
  13: [{ id: 5479, name: 'Cluj-Napoca', postalCode: '400001' }, { id: 5500, name: 'Floresti', postalCode: '407280' }],
  23: [
    { id: 20, name: 'Popesti-Leordeni', postalCode: '077160' },
    { id: 21, name: 'Voluntari', postalCode: '077190' },
    { id: 22, name: 'Chiajna', postalCode: '077040' },
    { id: 23, name: 'Darasti-Ilfov', postalCode: '077085' },
  ],
};
const SERVICES = [
  { id: 7, name: '24H', serviceCode: '24', deliveryType: { id: 1, name: 'Standard' }, defaultServices: true,
    serviceOptionalTaxes: [{ id: 3, name: 'Deschidere colet', taxCode: 'OPCG', costType: 'Fix', tax: 2, packageType: 0 }] },
  { id: 15, name: 'Locker NextDay', serviceCode: 'LN', deliveryType: { id: 2, name: 'Locker' }, defaultServices: true, serviceOptionalTaxes: [] },
];
const PICKUP_POINTS = [{
  id: 4455, alias: 'Depozit MundiShop', address: 'Str. Fabricii 10', defaultPickupPoint: true,
  country: { id: 187, name: 'Romania', code: 'RO' }, county: { id: 23, name: 'Ilfov', code: 'IF' }, city: { id: 22, name: 'Chiajna' },
  pickupPointContactPerson: [{ id: 901, name: 'Ana', phoneNumber: '0711111111', defaultContactPerson: true }],
}];
const LOCKER = { lockerId: 1234, name: 'easybox Kaufland Mărăști', county: 'Cluj', city: 'Cluj-Napoca', address: 'Str. Aurel Vlaicu 3', postalCode: '400582' };

function baseRoutes(extra = []) {
  return [
    ...extra,
    { method: 'POST', url: '/api/authenticate', reply: { body: { token: 'sd-token-1', expire_at: inTwoDays() } } },
    { url: '/api/geolocation/county', reply: { body: page(COUNTIES) } },
    { url: '/api/geolocation/city', reply: ({ url }) => ({ body: page(CITIES[Number(new URL(url).searchParams.get('county'))] || []) }) },
    { url: '/api/client/services', reply: { body: page(SERVICES) } },
    { url: '/api/client/pickup-points', reply: { body: page(PICKUP_POINTS) } },
    { url: '/api/client/lockers', reply: ({ url }) => ({ body: page(new URL(url).searchParams.get('lockersList') === '1234' || !new URL(url).searchParams.get('lockersList') ? [LOCKER] : []) }) },
    { method: 'POST', url: '/api/awb', reply: { body: { awbNumber: '1ONB24123456789', awbCost: 17.5, parcels: [{ position: 1, awbNumber: '1ONB24123456789001' }] } } },
  ];
}

function makeCtx(routes, { settings = {}, credentials } = {}) {
  const { http, calls } = fakeHttp(routes);
  return {
    ctx: { credentials: credentials || { username: 'mundishop', password: 'secret' }, settings, http, cache: memCache(), log: () => {} },
    calls,
  };
}

function shipment(over = {}) {
  return {
    reference: '#1024',
    recipient: {
      name: 'Ion Popescu', contactPerson: 'Ion Popescu', phone: '0722 123 456', email: 'ion@example.com',
      county: 'Cluj', countyCode: 'CJ', city: 'Cluj-Napoca', street: 'Str. Memorandumului 28', zip: '400114', country: 'RO',
      ...(over.recipient || {}),
    },
    parcels: 1, weightKg: 1.2, envelopes: 0, cod: 149.9, currency: 'RON', declaredValue: 0, contents: 'Jucării',
    ...Object.fromEntries(Object.entries(over).filter(([k]) => k !== 'recipient')),
  };
}

const awbForm = (calls) => {
  const c = calls.find((x) => x.method === 'POST' && x.url.endsWith('/api/awb'));
  return c && new URLSearchParams(c.body);
};

// ---- auth ----------------------------------------------------------------------------------

describe('sameday auth', () => {
  test('authenticates with X-AUTH headers + remember_me, caches token until expire_at, sends X-AUTH-TOKEN', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await sameday.listPickupPoints(ctx);
    await sameday.listServices(ctx);
    const auth = calls.filter((c) => c.url.endsWith('/api/authenticate'));
    assert.equal(auth.length, 1);
    assert.equal(auth[0].url, `${PROD_URL}/api/authenticate`);
    assert.equal(auth[0].headers['X-AUTH-USERNAME'], 'mundishop');
    assert.equal(auth[0].headers['X-AUTH-PASSWORD'], 'secret');
    assert.equal(auth[0].body, 'remember_me=1');
    const svc = calls.find((c) => c.url.includes('/api/client/services'));
    assert.equal(svc.headers['X-AUTH-TOKEN'], 'sd-token-1');
    const set = ctx.cache.sets.find((s) => s.k.includes(':token:'));
    assert.ok(set.ttl > 24 * 3600 && set.ttl < 2 * 24 * 3600, `ttl ${set.ttl}`);
  });

  test('sandbox setting switches the base URL (and cache namespace)', async () => {
    const { ctx, calls } = makeCtx(baseRoutes(), { settings: { sandbox: true } });
    await sameday.listPickupPoints(ctx);
    assert.ok(calls.every((c) => c.url.startsWith(SANDBOX_URL)));
    assert.ok(ctx.cache.sets.some((s) => s.k.startsWith('sameday:demo:token')));
  });

  test('401 on an authenticated call → re-authenticates and retries once', async () => {
    let n = 0;
    const { ctx, calls } = makeCtx(baseRoutes([
      { url: '/api/client/pickup-points', reply: () => (n++ === 0 ? { status: 401, body: { code: 401, message: 'Invalid token' } } : { body: page(PICKUP_POINTS) }) },
    ]));
    ctx.cache.set(tokenKey(ctx), 'old', 3600);
    const pts = await sameday.listPickupPoints(ctx);
    assert.equal(pts.length, 1);
    assert.equal(calls.filter((c) => c.url.endsWith('/api/authenticate')).length, 1);
  });

  test('bad credentials → AUTH_FAILED; testConnection message in Romanian with pickup points', async () => {
    const bad = makeCtx(baseRoutes([{ method: 'POST', url: '/api/authenticate', reply: { status: 400, body: { code: 400, message: 'Bad credentials' } } }]));
    await assert.rejects(sameday.testConnection(bad.ctx), (e) => e.code === 'AUTH_FAILED' && /Conectarea la Sameday a eșuat/.test(e.message));

    const { ctx } = makeCtx(baseRoutes(), { settings: { sandbox: true } });
    const r = await sameday.testConnection(ctx);
    assert.equal(r.ok, true);
    assert.equal(r.message, 'Conectat la Sameday (mod test). Am găsit 1 punct de ridicare.');
  });

  test('tokenTtl parses "Y-m-d H:i" and never overshoots', () => {
    const now = Date.parse('2026-10-02T10:00:00Z');
    assert.equal(tokenTtl('2026-10-03 13:00', now), 24 * 3600 - 300); // 13:00+03:00 = 10:00Z next day
    assert.equal(tokenTtl('garbage', now), 12 * 3600);
    assert.equal(tokenTtl('2026-10-01 10:00', now), 60);
  });
});

// ---- locality ------------------------------------------------------------------------------

describe('sameday locality resolution', () => {
  const formFor = async (recipient) => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await sameday.createShipment(ctx, shipment({ recipient }));
    return awbForm(calls);
  };

  test('"Sector 3" in București → Sectorul 3 city id', async () => {
    const f = await formFor({ county: 'București', countyCode: 'B', city: 'București Sector 3', zip: '' });
    assert.equal(f.get('awbRecipient[city]'), '3');
    assert.equal(f.get('awbRecipient[county]'), '10');
    const viaField = await formFor({ county: 'Bucuresti', countyCode: 'B', city: 'Bucuresti', sector: 5, zip: '' });
    assert.equal(viaField.get('awbRecipient[city]'), '5');
    const viaZip = await formFor({ county: 'Bucuresti', countyCode: 'B', city: 'Bucuresti', zip: '030167' });
    assert.equal(viaZip.get('awbRecipient[city]'), '3');
  });

  test('București without sector or zip → error suggesting sectors', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await assert.rejects(sameday.createShipment(ctx, shipment({ recipient: { county: 'București', countyCode: 'B', city: 'București', zip: '' } })), (e) => {
      assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
      assert.equal(e.field, 'shippingAddress.city');
      assert.match(e.message, /București, Sameday cere sectorul/);
      assert.match(e.hint, /^Ai vrut: Sectorul 1, Sectorul 2, Sectorul 3\? Adaugă sectorul/);
      return true;
    });
    assert.equal(awbForm(calls), undefined);
  });

  test('diacritics and hyphen/space differences', async () => {
    assert.equal((await formFor({ county: 'Ilfov', countyCode: 'IF', city: 'Popești Leordeni', zip: '' })).get('awbRecipient[city]'), '20');
    assert.equal((await formFor({ county: 'Ilfov', countyCode: 'IF', city: 'Orașul Popești-Leordeni', zip: '' })).get('awbRecipient[city]'), '20');
    assert.equal((await formFor({ county: 'Ilfov', countyCode: 'IF', city: 'Dărăști Ilfov', zip: '' })).get('awbRecipient[city]'), '23');
    assert.equal((await formFor({ city: 'Cluj Napoca' })).get('awbRecipient[city]'), '5479');
  });

  test('ambiguous name → suggestions with postal codes; correct zip resolves it', async () => {
    const { ctx } = makeCtx(baseRoutes());
    await assert.rejects(sameday.createShipment(ctx, shipment({ recipient: { county: 'Alba', countyCode: 'AB', city: 'Florești', zip: '' } })), (e) => {
      assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
      assert.match(e.message, /„Florești” apare de mai multe ori în nomenclatorul Sameday pentru județul Alba/);
      assert.match(e.hint, /^Ai vrut: Floresti \(cod 517176\), Floresti \(cod 515511\), Floresti \(cod 517596\)\?/);
      return true;
    });
    assert.equal((await formFor({ county: 'Alba', countyCode: 'AB', city: 'Floresti', zip: '517684' })).get('awbRecipient[city]'), '653');
  });

  test('not found → names locality + county, ≤ 3 suggestions', async () => {
    const { ctx } = makeCtx(baseRoutes());
    await assert.rejects(sameday.createShipment(ctx, shipment({ recipient: { county: 'Ilfov', countyCode: 'IF', city: 'Voluntarii Noi', zip: '' } })), (e) => {
      assert.match(e.message, /„Voluntarii Noi” nu există în nomenclatorul Sameday pentru județul Ilfov/);
      assert.match(e.hint, /^Ai vrut: Voluntari/);
      assert.ok(e.details.options.length <= 3);
      return true;
    });
  });

  test('cities are cached per county for 7 days', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await sameday.createShipment(ctx, shipment());
    await sameday.createShipment(ctx, shipment());
    assert.equal(calls.filter((c) => c.url.includes('/api/geolocation/city')).length, 1);
    assert.equal(ctx.cache.sets.find((s) => s.k === 'sameday:prod:cities:13').ttl, 7 * 24 * 3600);
  });
});

// ---- createShipment ------------------------------------------------------------------------

describe('sameday createShipment', () => {
  test('form payload: pickup point + contact, service id from code, COD, reference, recipient, parcels', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    const res = await sameday.createShipment(ctx, shipment({ weightKg: 3, parcels: 2, declaredValue: 200, notes: 'Sunați înainte', dimensionsCm: { length: 30, width: 20, height: 10 } }));
    assert.deepEqual(res, { awb: '1ONB24123456789', price: 17.5, raw: res.raw });
    const c = calls.find((x) => x.url.endsWith('/api/awb'));
    assert.equal(c.headers['Content-Type'], 'application/x-www-form-urlencoded');
    const f = awbForm(calls);
    assert.equal(f.get('pickupPoint'), '4455');
    assert.equal(f.get('contactPerson'), '901');
    assert.equal(f.get('service'), '7');
    assert.equal(f.get('packageType'), '0');
    assert.equal(f.get('packageNumber'), '2');
    assert.equal(f.get('packageWeight'), '3');
    assert.equal(f.get('awbPayment'), '1');
    assert.equal(f.get('cashOnDelivery'), '149.9');
    assert.equal(f.get('insuredValue'), '200');
    assert.equal(f.get('thirdPartyPickup'), '0');
    assert.equal(f.get('clientInternalReference'), '#1024');
    assert.equal(f.get('observation'), 'Jucării | Sunați înainte');
    assert.equal(f.get('currency'), 'RON');
    assert.equal(f.get('awbRecipient[name]'), 'Ion Popescu');
    assert.equal(f.get('awbRecipient[phoneNumber]'), '0722123456');
    assert.equal(f.get('awbRecipient[personType]'), '0');
    assert.equal(f.get('awbRecipient[email]'), 'ion@example.com');
    assert.equal(f.get('awbRecipient[address]'), 'Str. Memorandumului 28');
    assert.equal(f.get('awbRecipient[postalCode]'), '400114');
    assert.equal(f.get('awbRecipient[city]'), '5479');
    assert.equal(f.get('awbRecipient[county]'), '13');
    assert.equal(f.get('parcels[0][weight]'), '1.5');
    assert.equal(f.get('parcels[1][weight]'), '1.5');
    assert.equal(f.get('parcels[0][length]'), '30');
    assert.equal(f.has('serviceTaxes[0]'), false);
    assert.equal(f.has('lockerLastMile'), false);
  });

  test('open package → serviceTaxes[0]=OPCG; company → personType 1', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await sameday.createShipment(ctx, shipment({ openPackage: true, recipient: { company: 'Acme SRL' } }));
    const f = awbForm(calls);
    assert.equal(f.get('serviceTaxes[0]'), 'OPCG');
    assert.equal(f.get('awbRecipient[personType]'), '1');
    assert.equal(f.get('awbRecipient[companyName]'), 'Acme SRL');
  });

  test('open package on a service without OPCG → clear Romanian error before calling Sameday', async () => {
    const { ctx, calls } = makeCtx(baseRoutes(), { settings: { service: 'LN' } });
    await assert.rejects(sameday.createShipment(ctx, shipment({ openPackage: true })),
      (e) => e.code === 'OPEN_PACKAGE_UNAVAILABLE' && /nu permite deschiderea coletului/.test(e.message));
    assert.equal(awbForm(calls), undefined);
  });

  test('easybox: LN service, lockerLastMile, locker address, no open package, no city lookup', async () => {
    const { ctx, calls } = makeCtx(baseRoutes());
    await sameday.createShipment(ctx, shipment({ lockerId: '1234', openPackage: true }));
    const f = awbForm(calls);
    assert.equal(f.get('service'), '15');
    assert.equal(f.get('lockerLastMile'), '1234');
    assert.equal(f.get('awbRecipient[cityString]'), 'Cluj-Napoca');
    assert.equal(f.get('awbRecipient[countyString]'), 'Cluj');
    assert.equal(f.get('awbRecipient[address]'), 'Str. Aurel Vlaicu 3');
    assert.equal(f.has('awbRecipient[city]'), false);
    assert.equal(f.has('serviceTaxes[0]'), false);
    assert.equal(f.get('cashOnDelivery'), '149.9');
    assert.equal(calls.filter((c) => c.url.includes('/api/geolocation/city')).length, 0);

    const gone = makeCtx(baseRoutes());
    await assert.rejects(sameday.createShipment(gone.ctx, shipment({ lockerId: '999' })), (e) => e.code === 'LOCKER_INVALID');
  });

  test('explicit pickup point / unknown service', async () => {
    const { ctx, calls } = makeCtx(baseRoutes(), { settings: { pickupPointId: '4455', service: '6H' } });
    await assert.rejects(sameday.createShipment(ctx, shipment()), (e) => {
      assert.equal(e.code, 'CONFIG_SERVICE_INVALID');
      assert.match(e.message, /6H/);
      assert.match(e.hint, /24H \(24\)/);
      return true;
    });
    assert.equal(awbForm(calls), undefined);
    const byId = makeCtx(baseRoutes(), { settings: { service: '7' } });
    await sameday.createShipment(byId.ctx, shipment());
    assert.equal(awbForm(byId.calls).get('service'), '7');
  });

  test('toForm uses PHP bracket notation and skips null/undefined', () => {
    assert.equal(decodeURIComponent(toForm({ a: 1, b: null, c: undefined, d: true, e: { f: 'x', g: [1, { h: 2 }] } })), 'a=1&d=1&e[f]=x&e[g][0]=1&e[g][1][h]=2');
  });
});

// ---- error mapping -------------------------------------------------------------------------

describe('sameday error mapping', () => {
  const form = (children) => ({ code: 400, message: 'Validation Failed', errors: { children } });
  const cases = [
    [form({ awbRecipient: { children: { phoneNumber: { errors: ['Invalid phone number.'] } } } }), 'ADDRESS_PHONE_INVALID', 'shippingAddress.phone'],
    [form({ awbRecipient: { children: { city: { errors: ['This value is not valid.'] } } } }), 'ADDRESS_CITY_NOT_FOUND', 'shippingAddress.city'],
    [form({ awbRecipient: { children: { email: { errors: ['This value is not a valid email address.'] } } } }), 'ADDRESS_EMAIL_INVALID', 'email'],
    [form({ packageWeight: { errors: ['This value should be greater than 0.'] } }), 'SHIPMENT_WEIGHT_INVALID', 'weightKg'],
    [form({ pickupPoint: { errors: ['This value is not valid.'] } }), 'CONFIG_PICKUP_POINT_INVALID', 'settings.pickupPointId'],
    [form({ lockerLastMile: { errors: ['Locker is full.'] } }), 'LOCKER_INVALID', 'lockerId'],
    [form({ serviceTaxes: { errors: ['Invalid tax.'] } }), 'OPEN_PACKAGE_UNAVAILABLE', 'openPackage'],
    [{ code: 400, message: 'Something unexpected' }, 'PROVIDER_REJECTED', undefined],
  ];
  for (const [body, code, field] of cases) {
    test(`${JSON.stringify(body).slice(0, 70)} → ${code}`, async () => {
      const { ctx } = makeCtx(baseRoutes([{ method: 'POST', url: '/api/awb', reply: { status: 400, body } }]));
      await assert.rejects(sameday.createShipment(ctx, shipment()), (e) => {
        assert.equal(e.code, code);
        assert.equal(e.field, field);
        assert.equal(e.provider, 'sameday');
        assert.ok(!/[{}[\]]/.test(e.message), `no JSON in message: ${e.message}`);
        assert.deepEqual(e.details, body);
        return true;
      });
    });
  }

  test('phone error message is Romanian and quotes the courier text in the hint', () => {
    const e = mapAwbError(form({ awbRecipient: { children: { phoneNumber: { errors: ['Invalid phone number.'] } } } }), shipment(), 400);
    assert.equal(e.message, 'Sameday nu acceptă numărul de telefon „0722 123 456”.');
    assert.match(e.hint, /Sameday spune: „Invalid phone number\.”/);
  });
});

// ---- label, cancel, tracking ---------------------------------------------------------------

describe('sameday label / cancel / track', () => {
  test('getLabel downloads the PDF as buffer in A6 / A4', async () => {
    const pdf = Buffer.from('%PDF-1.7 fake');
    const { ctx, calls } = makeCtx(baseRoutes([{ url: '/api/awb/download/', reply: { body: pdf } }]));
    const out = await sameday.getLabel(ctx, '1ONB24123456789', { format: 'A6' });
    assert.ok(out.equals(pdf));
    assert.ok(calls.at(-1).url.endsWith('/api/awb/download/1ONB24123456789/A6'));
    assert.equal(calls.at(-1).responseType, 'buffer');
    await sameday.getLabel(ctx, '1ONB24123456789', { format: 'A4' });
    assert.ok(calls.at(-1).url.endsWith('/A4'));
    const def = makeCtx(baseRoutes([{ url: '/api/awb/download/', reply: { body: pdf } }]), { settings: { labelFormat: 'A4' } });
    await sameday.getLabel(def.ctx, 'X');
    assert.ok(def.calls.at(-1).url.endsWith('/X/A4'));
  });

  test('cancelShipment: DELETE /api/awb/{awb}; 404 is treated as already cancelled; 400 → CANCEL_REFUSED', async () => {
    const ok = makeCtx(baseRoutes([{ method: 'DELETE', url: '/api/awb/', reply: { status: 204, body: null } }]));
    await sameday.cancelShipment(ok.ctx, 'A1');
    assert.ok(ok.calls.at(-1).url.endsWith('/api/awb/A1'));
    const gone = makeCtx(baseRoutes([{ method: 'DELETE', url: '/api/awb/', reply: { status: 404, body: { code: 404, message: 'Not found' } } }]));
    await sameday.cancelShipment(gone.ctx, 'A1');
    const late = makeCtx(baseRoutes([{ method: 'DELETE', url: '/api/awb/', reply: { status: 400, body: { code: 400, message: 'Awb cannot be deleted' } } }]));
    await assert.rejects(sameday.cancelShipment(late.ctx, 'A1'), (e) => e.code === 'CANCEL_REFUSED' && /Awb cannot be deleted/.test(e.hint));
  });

  test('track: one call per AWB, 404 omitted, status mapped', async () => {
    const statuses = {
      A: { expeditionSummary: { delivered: true, canceled: false }, expeditionStatus: { statusId: 9, status: 'Livrata cu succes', statusLabel: 'Livrat', statusState: 'Livrat', statusDate: '2026-10-01T12:00:00+03:00' } },
      B: { expeditionSummary: { delivered: false, canceled: false }, expeditionStatus: { statusId: 33, status: 'In livrare', statusLabel: 'In livrare', statusState: 'In livrare', statusDate: '2026-10-02T08:00:00+03:00' } },
    };
    const { ctx, calls } = makeCtx(baseRoutes([{
      url: /\/api\/client\/awb\/(\w+)\/status/,
      reply: ({ url }) => { const k = url.match(/awb\/(\w+)\/status/)[1]; return statuses[k] ? { body: statuses[k] } : { status: 404, body: { code: 404 } }; },
    }]));
    const res = await sameday.track(ctx, ['A', 'B', 'C']);
    assert.equal(calls.filter((c) => c.url.includes('/status')).length, 3);
    assert.deepEqual(res.map((r) => [r.awb, r.status]), [['A', TrackingStatus.DELIVERED], ['B', TrackingStatus.OUT_FOR_DELIVERY]]);
    assert.equal(res[0].codCollected, true);
    assert.equal(res[0].at, '2026-10-01T09:00:00.000Z');
    assert.equal(res[1].statusText, 'In livrare');
  });

  test('status mapping table', () => {
    const s = (statusId, status, summary = {}) => ({ expeditionSummary: { delivered: false, canceled: false, ...summary }, expeditionStatus: { statusId, status, statusLabel: status, statusState: status } });
    const table = [
      [s(1, 'Colet in asteptare'), TrackingStatus.CREATED],
      [s(23, 'Inregistrat'), TrackingStatus.CREATED],
      [s(4, 'Ridicat de la expeditor'), TrackingStatus.PICKED_UP],
      [s(56, 'In tranzit'), TrackingStatus.IN_TRANSIT],
      [s(84, 'Depozit central'), TrackingStatus.IN_TRANSIT],
      [s(33, 'In livrare'), TrackingStatus.OUT_FOR_DELIVERY],
      [s(78, 'Depus in easybox'), TrackingStatus.OUT_FOR_DELIVERY],
      [s(9, 'Livrata cu succes'), TrackingStatus.DELIVERED],
      [s(3, 'Ramburs transferat'), TrackingStatus.DELIVERED],
      [s(999, 'Destinatar absent'), TrackingStatus.FAILED_ATTEMPT],
      [s(999, 'Refuzat de destinatar'), TrackingStatus.RETURNING],
      [s(999, 'Returnat la expeditor', { delivered: true }), TrackingStatus.RETURNED],
      [s(999, 'Expeditie anulata'), TrackingStatus.CANCELLED],
      [s(5, 'Anything', { canceled: true }), TrackingStatus.CANCELLED],
      [s(999, 'Status nou necunoscut'), TrackingStatus.UNKNOWN],
      [{ expeditionStatus: {} }, TrackingStatus.CREATED],
    ];
    for (const [body, expected] of table) assert.equal(mapSamedayStatus(body), expected, JSON.stringify(body.expeditionStatus));
  });

  test('listLockers filters by county/city; listServices / listPickupPoints shapes', async () => {
    const { ctx } = makeCtx(baseRoutes());
    assert.deepEqual(await sameday.listLockers(ctx, { county: 'Cluj', city: 'Cluj Napoca' }), [
      { id: '1234', name: 'easybox Kaufland Mărăști', address: 'Str. Aurel Vlaicu 3, Cluj-Napoca, Cluj', city: 'Cluj-Napoca', county: 'Cluj', postalCode: '400582' },
    ]);
    assert.deepEqual(await sameday.listLockers(ctx, { county: 'Ilfov' }), []);
    assert.deepEqual(await sameday.listServices(ctx), [{ id: '7', name: '24H (24)', code: '24' }, { id: '15', name: 'Locker NextDay (LN)', code: 'LN' }]);
    assert.deepEqual(await sameday.listPickupPoints(ctx), [{ id: '4455', name: 'Depozit MundiShop', address: 'Str. Fabricii 10, Chiajna, Ilfov', default: true }]);
  });
});
