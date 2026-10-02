import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus as S } from './contract.js';
import { findLocality, norm, normCounty } from './locality.js';
import {
  NOMENCLATOR_TTL, cached, cacheGet, cacheSet, chunk, isPdf, bufferToJson, roLocalToIso, latestMeaningful,
  accountKey, money, assertRonCod, shortText, saidBy,
} from './util.js';
import { m } from '../i18n/index.js';

// FAN Courier — selfAWB REST API v2.0 (https://api.fancourier.ro).
// Source: "API DOCUMENTATION FAN Courier V 2.0, September 2025" (fancourier.ro PDF) and the
// community PHP client shusaura85/fancourier-api (same endpoints/field names).
//
// Auth: POST /login (username, password) → bearer token valid 24h; cached via ctx.cache.
// Every call also needs `clientId` = the selfAWB branch (punct de lucru) the AWB is issued from.
//
// Live check 2026-10 (invalid credentials):
//   POST /login (form or JSON body) → 401 {"status":"error","message":"These credentials do not match our records."}
//   POST /login without fields     → 422 {"status":"fail","message":"The username field is required.",
//                                         "data":{"errors":{"username":[...],"password":[...]}}}
//   any authenticated route, bad/no token → 401 {"message":"These credentials do not match our records."}
//   (intern-awb / awb/label / DELETE awb add "status":"error"); unknown route → 404 {"message":"Not found"}.
//   Laravel validation errors are therefore under data.errors, not at the top level.
//
// Live run 2026-10-02 with the test account FAN publishes in its API docs (user on p.4, clientId
// 7032158, EN_FANCourier_API_130825-1.pdf p.4; production server): login, branches, services,
// localities, intern-awb (Cont Colector, COD) → AWB, label → real PDF, tracking, DELETE all succeeded;
// sanitized bodies in test/fixtures/couriers/fancourier-success.json. Seen there and handled below:
// a 200 intern-awb with "success":false and errors keyed "info.recipient.phone"; tracking rows without
// events; unknown AWBs returned as rows with a "not found" message; 422 on a second DELETE. A deleted
// AWB keeps tracking as "inregistrat" (FAN never reports the deletion) and its label still prints.
//
//   GET /reports/counties, /reports/localities (13 834 rows, no paging) and /reports/streets are PUBLIC:
//   no token needed. Locality names carry no diacritics, are unique per county, and same-named villages
//   of one county are spelled "Alun (Bosorod)" / "Alun (Bunila)" (827 such names).

const PROVIDER = 'FAN Courier';
const ID = 'fancourier';
const BASE = 'https://api.fancourier.ro';
const TOKEN_TTL = 23 * 60 * 60; // token lives 24h, refresh 1h early
const AWB_NOT_FOUND = /nu a fost gasit|not found/i;
const ALREADY_DELETED = /already deleted|deja (a fost )?sters/i;

// FAN tracking event ids (GET /reports/awb-events) → normalized status.
//   C0  ridicat de la expeditor ............................ picked_up
//   C1  preluat de curier pentru livrare ................... out_for_delivery
//   H0-H17 tranzit / sortare / depozit ..................... in_transit
//   S1  în livrare ......................................... out_for_delivery
//   S2  livrat ............................................. delivered
//   S3, S11 avizat (destinatar absent) ..................... failed_attempt
//   S4, S5, S10, S14, S19-S22, S24, S25, S27, S28, S30, S42, S49, S50
//       adresă incompletă/greșită, nu răspunde, fără bani, acces restricționat... failed_attempt
//   S12 contactat, livrare ulterioară ...................... failed_attempt
//   S6  refuz primire, S7 refuz plată transport, S15 refuz ramburs,
//   S16 retur la termen, S33 retur solicitat, S43 retur .... returning
//   S8  livrare din sediul FAN, S9 redirecționat, S35 retrimis în livrare, S47 predat partener extern ... in_transit
//   S46 predat în punctul de livrare (FANbox/PayPoint) ..... out_for_delivery
//   S38 AWB neexpediat ..................................... created
//   S37 despăgubit ......................................... unknown
const EVENT_STATUS = {
  C0: S.PICKED_UP,
  C1: S.OUT_FOR_DELIVERY,
  S1: S.OUT_FOR_DELIVERY,
  S2: S.DELIVERED,
  S46: S.OUT_FOR_DELIVERY,
  S8: S.IN_TRANSIT, S9: S.IN_TRANSIT, S35: S.IN_TRANSIT, S47: S.IN_TRANSIT,
  S6: S.RETURNING, S7: S.RETURNING, S15: S.RETURNING, S16: S.RETURNING, S33: S.RETURNING, S43: S.RETURNING,
  S38: S.CREATED,
  S37: S.UNKNOWN,
};
for (const id of ['S3', 'S4', 'S5', 'S10', 'S11', 'S12', 'S14', 'S19', 'S20', 'S21', 'S22', 'S24', 'S25', 'S27', 'S28', 'S30', 'S42', 'S49', 'S50']) {
  EVENT_STATUS[id] = S.FAILED_ATTEMPT;
}

export function mapFanEvent(id) {
  const key = String(id ?? '').trim().toUpperCase();
  if (EVENT_STATUS[key]) return EVENT_STATUS[key];
  if (/^H\d+$/.test(key)) return S.IN_TRANSIT;
  if (/^C\d+$/.test(key)) return S.PICKED_UP;
  return S.UNKNOWN;
}

// Services whose COD goes to the merchant's bank account ("Cont Colector" variants).
const CONT_COLECTOR = {
  'Standard': 'Cont Colector',
  'RedCode': 'Red code-Cont Colector',
  'Express Loco 1H': 'Express Loco 1H-Cont Colector',
  'Express Loco 2H': 'Express Loco 2H-Cont Colector',
  'Express Loco 4H': 'Express Loco 4H-Cont Colector',
  'Express Loco 6H': 'Express Loco 6H-Cont Colector',
  'CollectPoint': 'CollectPoint Cont Colector',
  'Produse Albe': 'Produse Albe-Cont Colector',
  'Transport Marfa': 'Transport Marfa-Cont Colector',
  'Transport Marfa Produse Albe': 'Transport Marfa Produse Albe-Cont Colector',
  'FANbox': 'FANbox Cont Colector',
  'Export': 'Export-Cont Colector',
};
const WITHOUT_CONT_COLECTOR = Object.fromEntries(Object.entries(CONT_COLECTOR).map(([k, v]) => [v, k]));

/** Picks the FAN service name from the shipment + settings (Cont Colector when COD goes to bank). */
export function pickService(shipment, settings = {}) {
  let base = shipment.service || settings.service || 'Standard';
  if (WITHOUT_CONT_COLECTOR[base]) base = WITHOUT_CONT_COLECTOR[base];
  if (shipment.lockerId) base = 'FANbox';
  const toBank = settings.codToBankAccount !== false && settings.codToBankAccount !== 'false';
  if (shipment.cod > 0 && toBank) return CONT_COLECTOR[base] || base;
  return base;
}

function clientIdOf(ctx) {
  const id = ctx.settings?.clientId ?? ctx.credentials?.clientId;
  if (!id) {
    throw new ProcessingError({
      code: 'SETTINGS_MISSING',
      key: 'fancourier.errors.clientIdMissing',
      provider: ID,
      field: 'settings.clientId',
    });
  }
  return id;
}

// ---------------------------------------------------------------- auth & http

/** One token per account (user + password): two FAN accounts in one store never share it. */
export const tokenKey = (ctx) => `fancourier:token:${accountKey(ctx.credentials?.username, ctx.credentials?.password)}`;

async function login(ctx) {
  const { username, password } = ctx.credentials || {};
  if (!username || !password) throw authError(PROVIDER, 'missing credentials');
  const res = await ctx.http(PROVIDER, `${BASE}/login`, {
    method: 'POST',
    body: new URLSearchParams({ username, password }),
    mapError: (status, body) => ([400, 401, 403, 422].includes(status) ? authError(PROVIDER, body) : undefined),
  });
  const token = res.body?.data?.token;
  if (res.body?.status !== 'success' || !token) throw authError(PROVIDER, res.body);
  await cacheSet(ctx, tokenKey(ctx), token, TOKEN_TTL);
  return token;
}

async function getToken(ctx, { fresh = false } = {}) {
  if (!fresh) {
    const t = await cacheGet(ctx, tokenKey(ctx));
    if (t) return t;
  }
  return login(ctx);
}

class TokenRejected extends ProcessingError {}

/** Authenticated call; on 401 refreshes the token once (FAN invalidates tokens server-side too). */
async function api(ctx, path, { query, ...opts } = {}) {
  const url = `${BASE}${path}${query ? `?${query}` : ''}`;
  const call = async (token) => ctx.http(PROVIDER, url, {
    ...opts,
    headers: { ...(opts.headers || {}), Authorization: `Bearer ${token}` },
    mapError: (status, body) => {
      if (status === 401) return new TokenRejected({ code: 'AUTH_FAILED', message: 'token', provider: ID, details: body });
      return mapHttpError(status, body);
    },
  });
  try {
    return await call(await getToken(ctx));
  } catch (err) {
    if (!(err instanceof TokenRejected)) throw err;
    try {
      return await call(await getToken(ctx, { fresh: true }));
    } catch (err2) {
      if (err2 instanceof TokenRejected) throw authError(PROVIDER, err2.details);
      throw err2;
    }
  }
}

function mapHttpError(status, body) {
  if (status === 422 || status === 400) {
    // Laravel: {"status":"fail","message":"...","data":{"errors":{"field":["..."]}}} (live shape);
    // older/other routes: {"errors":{...}} or just {"message":"..."}.
    const errs = body?.data?.errors || body?.errors || body?.message;
    return fanValidationError(errs, body);
  }
  return undefined;
}

// Field paths in FAN validation errors → the order field the merchant must fix (text: fancourier.errors.field.<code>).
const FIELD_MAP = [
  [/locality|localitate/i, 'shippingAddress.city', 'ADDRESS_CITY_NOT_FOUND'],
  [/county|judet/i, 'shippingAddress.province', 'ADDRESS_COUNTY_INVALID'],
  [/street|strada/i, 'shippingAddress.address1', 'ADDRESS_STREET_INVALID'],
  [/zip|postal/i, 'shippingAddress.zip', 'ADDRESS_ZIP_INVALID'],
  [/phone|telefon/i, 'shippingAddress.phone', 'ADDRESS_PHONE_INVALID'],
  [/pickupLocation|fanbox/i, 'lockerId', 'LOCKER_INVALID'],
  [/recipient\.name|contactPerson/i, 'shippingAddress.name', 'ADDRESS_NAME_INVALID'],
];

function fanValidationError(errors, raw) {
  const pairs = errors && typeof errors === 'object' && !Array.isArray(errors)
    ? Object.entries(errors).map(([k, v]) => [k, Array.isArray(v) ? v.join('; ') : String(v)])
    : [['', Array.isArray(errors) ? errors.join('; ') : String(errors ?? '')]];
  for (const [key, text] of pairs) {
    for (const [re, field, code] of FIELD_MAP) {
      if (re.test(key) || (!key && re.test(text))) {
        return new ProcessingError({ code, key: `fancourier.errors.field.${code}`, field, provider: ID, details: raw });
      }
    }
  }
  const said = shortText(pairs.map(([, x]) => x).filter(Boolean)[0]);
  return new ProcessingError({
    code: 'COURIER_REJECTED',
    key: 'fancourier.errors.rejected',
    params: { said: said ? saidBy('FAN', said) : m('fancourier.detailsInLog') },
    provider: ID,
    details: raw,
  });
}

// ---------------------------------------------------------------- nomenclator

async function loadLocalities(ctx) {
  return cached(ctx, 'fancourier:localities', NOMENCLATOR_TTL, async () => {
    // Public endpoint (no token): a login problem must not block address validation.
    const res = await ctx.http(PROVIDER, `${BASE}/reports/localities`, { timeoutMs: 60_000 });
    const rows = Array.isArray(res.body?.data) ? res.body.data : [];
    if (!rows.length) throw new ProcessingError({ code: 'PROVIDER_DOWN', key: 'fancourier.errors.localities', retryable: true, provider: ID, details: res.body });
    return rows.map((r) => [r.name, r.county]);
  });
}

export async function resolveFanLocality(ctx, recipient) {
  const rows = await loadLocalities(ctx);
  // FAN takes county + locality NAMES, so the exact FAN spelling ("Alun (Bosorod)") is what we send.
  const hit = findLocality(rows, recipient, {
    nameOf: (r) => r[0], countyOf: (r) => r[1], sameNameIsSame: true, provider: ID, providerName: PROVIDER,
  });
  return { locality: hit[0], county: hit[1] };
}

async function getPickupPoint(ctx, id) {
  const res = await api(ctx, '/reports/pickup-points', { query: new URLSearchParams({ id }).toString() });
  const p = Array.isArray(res.body?.data) ? res.body.data[0] : res.body?.data;
  return p || undefined;
}

// ---------------------------------------------------------------- payload

const DEFAULT_DIMENSIONS = { length: 20, width: 15, height: 9 }; // fits a FANbox "S" drawer; docs Sept 2025: info.dimensions is mandatory

export function buildAwbPayload(shipment, settings, { clientId, county, locality, locker }) {
  const r = shipment.recipient;
  const service = pickService(shipment, settings);
  const isFanbox = /^FANbox/.test(service);
  const options = [];
  if (isFanbox) options.push('V'); // V = livrare în FANbox (obligatoriu pentru FANbox)
  const openPackage = shipment.openPackage ?? (settings.openPackage === true || settings.openPackage === 'true');
  // A = deschidere la livrare; FANbox nu o permite, iar FAN o acceptă doar când plătește expeditorul.
  if (openPackage && !isFanbox && settings.payer !== 'recipient') options.push('A');
  if (shipment.saturday) options.push('S');
  if (settings.labelFormat === 'A6') options.push('X'); // X = ePOD: eticheta A6 tipărită de expeditor
  const dims = shipment.dimensionsCm || DEFAULT_DIMENSIONS;

  const address = isFanbox
    ? {
      county: locker?.address?.county || county,
      locality: locker?.address?.locality || locality,
      // The schema table says "pickupLocation"; the FANbox/PayPoint chapters of the Sept 2025 docs, all
      // their examples and the PHP client use "pickupLocationId" (e.g. "F1011137").
      pickupLocationId: shipment.lockerId,
    }
    : {
      county,
      locality,
      street: r.street,
      streetNo: '',
      zipCode: r.zip || '',
    };

  return {
    clientId: Number(clientId) || clientId,
    shipments: [{
      info: {
        service,
        packages: { parcel: isFanbox ? 1 : Math.max(0, shipment.parcels ?? 1), envelope: shipment.envelopes || 0 },
        weight: Math.max(1, Math.ceil(shipment.weightKg || 1)), // VERIFY: docs say "numeric", every example is an int
        cod: money(shipment.cod), // no currency field: always RON (non-RON refused in createShipment)
        declaredValue: money(shipment.declaredValue),
        payment: settings.payer === 'recipient' ? 'recipient' : 'sender',
        observation: (shipment.notes || '').slice(0, 255),
        content: [shipment.reference, shipment.contents].filter(Boolean).join(' ').slice(0, 255),
        dimensions: { length: dims.length, height: dims.height, width: dims.width },
        costCenter: (settings.costCenter || shipment.reference || '').slice(0, 40),
        options,
      },
      recipient: {
        name: (r.company || r.name || '').slice(0, 50),
        contactPerson: (r.contactPerson || r.name || '').slice(0, 50),
        phone: r.phone,
        email: r.email || '',
        address,
      },
    }],
  };
}

// ---------------------------------------------------------------- adapter

export default {
  id: ID,
  name: PROVIDER,
  trackingUrl: (awb) => `https://www.fancourier.ro/awb-tracking/?tracking=${encodeURIComponent(awb)}`,

  credentialFields: [
    { key: 'username', type: 'text', required: true },
    { key: 'password', type: 'password', required: true },
  ],

  // Labels and help: fancourier.fields.<key> in the catalogs (src/i18n); FAN service names stay as FAN spells them.
  settingsFields: [
    { key: 'clientId', type: 'text', required: true },
    {
      key: 'service', type: 'select', default: 'Standard',
      options: [
        { value: 'Standard', label: 'Standard' },
        { value: 'RedCode' },
        { value: 'Express Loco 2H', label: 'Express Loco 2H' },
        { value: 'Express Loco 4H', label: 'Express Loco 4H' },
        { value: 'Express Loco 6H', label: 'Express Loco 6H' },
        { value: 'Produse Albe' },
      ],
    },
    { key: 'codToBankAccount', type: 'checkbox', default: true },
    { key: 'labelFormat', type: 'select', default: 'A4', options: [{ value: 'A4' }, { value: 'A5', label: 'A5' }, { value: 'A6' }] },
    { key: 'openPackage', type: 'checkbox', default: false },
    { key: 'payer', type: 'select', default: 'sender', options: [{ value: 'sender' }, { value: 'recipient' }] },
  ],

  async testConnection(ctx) {
    await getToken(ctx, { fresh: true });
    const res = await api(ctx, '/reports/branches');
    const branches = (res.body?.data || []).map((b) => ({ id: String(b.id), name: b.name, address: [b.address?.street, b.address?.streetNo, b.address?.locality].filter(Boolean).join(' ') }));
    const configured = ctx.settings?.clientId ? String(ctx.settings.clientId) : '';
    let extra = '';
    if (configured && branches.length && !branches.some((b) => b.id === configured)) {
      extra = m('fancourier.test.idMissing', { id: configured, ids: branches.map((b) => b.id).join(', ') });
    } else if (!configured && branches.length) {
      extra = m('fancourier.test.fillId', { list: branches.map((b) => `${b.id} (${b.name})`).join(', ') });
    }
    return { ok: true, message: m('fancourier.test.connected', { count: branches.length, extra }), info: { branches } };
  },

  async createShipment(ctx, shipment) {
    const clientId = clientIdOf(ctx);
    assertRonCod(shipment, { provider: ID, providerName: PROVIDER });
    const settings = ctx.settings || {};
    const r = shipment.recipient;
    let county = r.county;
    let locality = r.city;
    let locker;

    if (shipment.lockerId) {
      if ((shipment.parcels ?? 1) > 1) {
        throw new ProcessingError({
          code: 'LOCKER_MULTI_PARCEL',
          key: 'fancourier.errors.lockerMultiParcel',
          provider: ID, field: 'parcels',
        });
      }
      try { locker = await getPickupPoint(ctx, shipment.lockerId); } catch (err) {
        if (err?.code === 'AUTH_FAILED') throw err;
        ctx.log?.(m('log.lockerLookupFailed', { provider: PROVIDER }), { lockerId: shipment.lockerId, err: err?.message });
      }
    }

    if (!locker) {
      try {
        ({ county, locality } = await resolveFanLocality(ctx, r));
      } catch (err) {
        if (String(err?.code || '').startsWith('ADDRESS_') || err?.code === 'AUTH_FAILED') throw err;
        // Nomenclator unavailable: FAN validates names server-side anyway.
        ctx.log?.(m('log.localitiesUnavailable', { provider: PROVIDER }), { err: err?.message });
      }
    }

    const payload = buildAwbPayload(shipment, settings, { clientId, county, locality, locker });
    const res = await api(ctx, '/intern-awb', { method: 'POST', json: payload });
    const item = Array.isArray(res.body?.response) ? res.body.response[0] : undefined;
    if (!item) {
      throw new ProcessingError({
        code: 'COURIER_REJECTED',
        key: 'fancourier.errors.noAwb',
        provider: ID, details: res.body,
      });
    }
    if (item.errors || !item.awbNumber) throw fanValidationError(item.errors || item.message, res.body);
    return { awb: String(item.awbNumber), price: item.tariff != null ? Number(item.tariff) + Number(item.vat || 0) : undefined, raw: item };
  },

  async getLabel(ctx, awb, { format } = {}) {
    const clientId = clientIdOf(ctx);
    const fmt = format || ctx.settings?.labelFormat || 'A4';
    const q = new URLSearchParams({ clientId: String(clientId) });
    q.append('awbs[]', awb);
    q.set('pdf', '1');
    // FAN prints A4/A5; A6 only for AWBs issued with ePOD (option X) — docs: "A6 (only for ePOD)".
    q.set('format', fmt === 'A6' ? (ctx.settings?.labelFormat === 'A6' ? 'A6' : 'A5') : fmt);
    const res = await api(ctx, '/awb/label', { query: q.toString(), responseType: 'buffer', headers: { Accept: 'application/pdf' } });
    if (!isPdf(res.body)) {
      throw new ProcessingError({
        code: 'LABEL_FAILED',
        key: 'fancourier.errors.label',
        params: { awb },
        retryable: true, provider: ID, details: bufferToJson(res.body) ?? String(res.body).slice(0, 300),
      });
    }
    return res.body;
  },

  async cancelShipment(ctx, awb) {
    const clientId = clientIdOf(ctx);
    const q = new URLSearchParams({ clientId: String(clientId), awb: String(awb) });
    let res;
    try {
      res = await api(ctx, '/awb', { method: 'DELETE', query: q.toString() });
    } catch (err) {
      if (err?.code === 'AUTH_FAILED' || err?.retryable) throw err;
      // Live 2026-10, second DELETE of the same AWB: 422 {"status":"fail","message":"The AWB was already
      // deleted.",...}. The goal (AWB gone) is reached — e.g. a retry after a timeout on the first DELETE.
      if (ALREADY_DELETED.test(String(err?.details?.message || ''))) return;
      throw cancelRefused(awb, err?.details ?? err);
    }
    if (res.body?.status && res.body.status !== 'success') throw cancelRefused(awb, res.body);
  },

  async track(ctx, awbs) {
    if (!awbs?.length) return [];
    const clientId = clientIdOf(ctx);
    const out = [];
    for (const group of chunk([...new Set(awbs.map(String))], 50)) {
      const q = new URLSearchParams({ clientId: String(clientId), language: 'ro' });
      for (const a of group) q.append('awb[]', a);
      const res = await api(ctx, '/reports/awb/tracking', { query: q.toString() });
      for (const row of res.body?.data || []) {
        if (!row?.awbNumber) continue;
        const events = Array.isArray(row.events) ? row.events : [];
        // Live 2026-10: an unknown AWB still comes back as a row, without events, with
        // "message":"AWB-ul nu a fost gasit." / "The AWB was not found" — contract: omit it.
        if (!events.length && AWB_NOT_FOUND.test(String(row.message || ''))) continue;
        const last = latestMeaningful(events, (e) => mapFanEvent(e.id));
        const status = last ? last.status : S.CREATED;
        out.push({
          awb: String(row.awbNumber),
          status,
          // Without events FAN sends "message":"AWB-ul a fost inregistrat de catre clientul expeditor".
          statusText: last ? String(last.event.name || '').trim() : (String(row.message || '').trim() || 'AWB emis'),
          at: last ? roLocalToIso(last.event.date) : undefined,
          ...(status === S.DELIVERED ? { codCollected: true } : {}),
        });
      }
    }
    return out;
  },

  async listPickupPoints(ctx) {
    const res = await api(ctx, '/reports/branches');
    return (res.body?.data || []).map((b) => ({
      id: String(b.id),
      name: b.name,
      address: [b.address?.street, b.address?.streetNo, b.address?.locality, b.address?.county].filter(Boolean).join(', '),
    }));
  },

  async listServices(ctx) {
    const res = await api(ctx, '/reports/services');
    return (res.body?.data || []).map((s) => ({ id: s.name, name: s.name }));
  },

  async listLockers(ctx, { county, city } = {}) {
    const all = await cached(ctx, 'fancourier:fanbox', 24 * 60 * 60, async () => {
      const res = await api(ctx, '/reports/pickup-points', { query: 'type=fanbox' });
      return (res.body?.data || []).map((p) => ({
        id: String(p.id),
        name: p.name,
        county: p.address?.county,
        locality: p.address?.locality,
        address: [p.address?.street, p.address?.streetNo, p.address?.locality].filter(Boolean).join(' '),
      }));
    });
    return all
      .filter((p) => !county || normCounty(p.county) === normCounty(county))
      .filter((p) => !city || norm(p.locality) === norm(city))
      .map(({ id, name, address }) => ({ id, name, address }));
  },
};

function cancelRefused(awb, details) {
  return new ProcessingError({
    code: 'CANCEL_REFUSED',
    key: 'fancourier.errors.cancel',
    params: { awb },
    provider: ID,
    details,
  });
}
