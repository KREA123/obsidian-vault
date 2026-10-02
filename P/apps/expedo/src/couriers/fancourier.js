import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus as S } from './contract.js';
import {
  NOMENCLATOR_TTL, cached, cacheGet, cacheSet, chunk, isPdf, bufferToJson, norm, normCounty,
  resolveLocality, roLocalToIso, latestMeaningful,
} from './ro-nomenclator.js';

// FAN Courier — selfAWB REST API v2.0 (https://api.fancourier.ro).
// Source: "API DOCUMENTATION FAN Courier V 2.0, September 2025" (fancourier.ro PDF) and the
// community PHP client shusaura85/fancourier-api (same endpoints/field names).
//
// Auth: POST /login (username, password) → bearer token valid 24h; cached via ctx.cache.
// Every call also needs `clientId` = the selfAWB branch (punct de lucru) the AWB is issued from.

const PROVIDER = 'FAN Courier';
const ID = 'fancourier';
const BASE = 'https://api.fancourier.ro';
const TOKEN_TTL = 23 * 60 * 60; // token lives 24h, refresh 1h early

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
      message: 'Lipsește ID-ul de client FAN Courier (punctul de ridicare).',
      hint: 'Completează „ID client” în Setări → Curieri → FAN Courier. Apasă „Testează conexiunea” ca să vezi ID-urile disponibile.',
      provider: ID,
      field: 'settings.clientId',
    });
  }
  return id;
}

// ---------------------------------------------------------------- auth & http

const tokenKey = (ctx) => `fancourier:token:${ctx.credentials?.username || ''}`;

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
    const errs = body?.errors || body?.message;
    return fanValidationError(errs, body);
  }
  return undefined;
}

// Field paths in FAN validation errors → the order field the merchant must fix.
const FIELD_MAP = [
  [/locality|localitate/i, 'shippingAddress.city', 'ADDRESS_CITY_NOT_FOUND', 'Localitatea nu este acceptată de FAN Courier.'],
  [/county|judet/i, 'shippingAddress.province', 'ADDRESS_COUNTY_INVALID', 'Județul nu este acceptat de FAN Courier.'],
  [/street|strada/i, 'shippingAddress.address1', 'ADDRESS_STREET_INVALID', 'Strada lipsește sau nu este acceptată de FAN Courier.'],
  [/zip|postal/i, 'shippingAddress.zip', 'ADDRESS_ZIP_INVALID', 'Codul poștal nu este acceptat de FAN Courier.'],
  [/phone|telefon/i, 'shippingAddress.phone', 'ADDRESS_PHONE_INVALID', 'Numărul de telefon nu este acceptat de FAN Courier.'],
  [/pickupLocation|fanbox/i, 'lockerId', 'LOCKER_INVALID', 'FANbox-ul ales nu este valid sau nu este disponibil.'],
  [/recipient\.name|contactPerson/i, 'shippingAddress.name', 'ADDRESS_NAME_INVALID', 'Numele destinatarului lipsește sau e prea lung.'],
];

function fanValidationError(errors, raw) {
  const pairs = errors && typeof errors === 'object' && !Array.isArray(errors)
    ? Object.entries(errors).map(([k, v]) => [k, Array.isArray(v) ? v.join('; ') : String(v)])
    : [['', Array.isArray(errors) ? errors.join('; ') : String(errors ?? '')]];
  for (const [key, text] of pairs) {
    for (const [re, field, code, message] of FIELD_MAP) {
      if (re.test(key) || (!key && re.test(text))) {
        return new ProcessingError({
          code, message, field, provider: ID,
          hint: 'Corectează adresa în comandă și reîncearcă.',
          details: raw,
        });
      }
    }
  }
  return new ProcessingError({
    code: 'COURIER_REJECTED',
    message: 'FAN Courier a refuzat AWB-ul.',
    hint: 'Verifică datele comenzii și setările FAN Courier (serviciu, ID client). Detaliile sunt în jurnal.',
    provider: ID,
    details: raw,
  });
}

// ---------------------------------------------------------------- nomenclator

async function loadLocalities(ctx) {
  return cached(ctx, 'fancourier:localities', NOMENCLATOR_TTL, async () => {
    const res = await api(ctx, '/reports/localities');
    const rows = Array.isArray(res.body?.data) ? res.body.data : [];
    if (!rows.length) throw new ProcessingError({ code: 'PROVIDER_DOWN', message: 'FAN Courier nu a trimis lista de localități.', hint: 'Reîncercăm automat.', retryable: true, provider: ID, details: res.body });
    return rows.map((r) => [r.name, r.county]);
  });
}

export async function resolveFanLocality(ctx, recipient) {
  const rows = await loadLocalities(ctx);
  const hit = resolveLocality(rows, recipient, {
    nameOf: (r) => r[0], countyOf: (r) => r[1], describe: (r) => r[0],
    allowDuplicates: true, provider: PROVIDER, providerId: ID,
  });
  return { locality: hit[0], county: hit[1] };
}

async function getPickupPoint(ctx, id) {
  const res = await api(ctx, '/reports/pickup-points', { query: new URLSearchParams({ id }).toString() });
  const p = Array.isArray(res.body?.data) ? res.body.data[0] : res.body?.data;
  return p || undefined;
}

// ---------------------------------------------------------------- payload

const DEFAULT_DIMENSIONS = { length: 20, width: 15, height: 9 }; // fits a FANbox "S" drawer; VERIFY: FAN requires dimensions

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
      // The schema table says "pickupLocation", every example and the PHP client send "pickupLocationId".
      pickupLocationId: shipment.lockerId, // VERIFY: field name (docs disagree)
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
        weight: Math.max(1, Math.ceil(shipment.weightKg || 1)), // VERIFY: FAN wants integer kg (examples use ints)
        cod: shipment.cod > 0 ? Number(shipment.cod.toFixed(2)) : 0,
        declaredValue: shipment.declaredValue || 0,
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
    { key: 'username', label: 'Utilizator selfAWB', type: 'text', required: true, help: 'Același utilizator cu care intri în selfawb.ro.' },
    { key: 'password', label: 'Parolă selfAWB', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'clientId', label: 'ID client (punct de ridicare)', type: 'text', required: true, help: 'ID-ul punctului de lucru din selfAWB. „Testează conexiunea” îți arată ID-urile contului.' },
    {
      key: 'service', label: 'Serviciu implicit', type: 'select', default: 'Standard',
      options: [
        { value: 'Standard', label: 'Standard' },
        { value: 'RedCode', label: 'RedCode (a doua zi până la 10:00)' },
        { value: 'Express Loco 2H', label: 'Express Loco 2H' },
        { value: 'Express Loco 4H', label: 'Express Loco 4H' },
        { value: 'Express Loco 6H', label: 'Express Loco 6H' },
        { value: 'Produse Albe', label: 'Produse Albe' },
      ],
      help: 'Pentru livrare în FANbox serviciul se alege automat.',
    },
    { key: 'codToBankAccount', label: 'Ramburs în cont (Cont Colector)', type: 'checkbox', default: true, help: 'Bifat: rambursul vine în contul bancar și AWB-ul se emite pe „Cont Colector”. Debifat: ramburs numerar.' },
    {
      key: 'labelFormat', label: 'Format etichetă', type: 'select', default: 'A4',
      options: [{ value: 'A4', label: 'A4 (imprimantă obișnuită)' }, { value: 'A5', label: 'A5' }, { value: 'A6', label: 'A6 termică (ePOD)' }],
      help: 'A6 activează opțiunea ePOD la FAN; trebuie să o ai în contract.',
    },
    { key: 'openPackage', label: 'Deschidere colet la livrare', type: 'checkbox', default: false, help: 'Clientul poate verifica produsele înainte să plătească.' },
    {
      key: 'payer', label: 'Cine plătește transportul', type: 'select', default: 'sender',
      options: [{ value: 'sender', label: 'Expeditorul (tu)' }, { value: 'recipient', label: 'Destinatarul' }],
    },
  ],

  async testConnection(ctx) {
    await getToken(ctx, { fresh: true });
    const res = await api(ctx, '/reports/branches');
    const branches = (res.body?.data || []).map((b) => ({ id: String(b.id), name: b.name, address: [b.address?.street, b.address?.streetNo, b.address?.locality].filter(Boolean).join(' ') }));
    const configured = ctx.settings?.clientId ? String(ctx.settings.clientId) : '';
    let message = `Conectat la FAN Courier. ${branches.length === 1 ? 'Un punct de ridicare' : `${branches.length} puncte de ridicare`} în cont.`;
    if (configured && branches.length && !branches.some((b) => b.id === configured)) {
      message += ` Atenție: ID-ul ${configured} nu apare în cont; alege unul dintre: ${branches.map((b) => b.id).join(', ')}.`;
    } else if (!configured && branches.length) {
      message += ` Completează „ID client” cu: ${branches.map((b) => `${b.id} (${b.name})`).join(', ')}.`;
    }
    return { ok: true, message, info: { branches } };
  },

  async createShipment(ctx, shipment) {
    const clientId = clientIdOf(ctx);
    const settings = ctx.settings || {};
    const r = shipment.recipient;
    let county = r.county;
    let locality = r.city;
    let locker;

    if (shipment.lockerId) {
      if ((shipment.parcels ?? 1) > 1) {
        throw new ProcessingError({
          code: 'LOCKER_MULTI_PARCEL',
          message: 'În FANbox se poate trimite un singur colet pe AWB.',
          hint: 'Pune produsele într-un singur colet sau alege livrare la adresă.',
          provider: ID, field: 'parcels',
        });
      }
      try { locker = await getPickupPoint(ctx, shipment.lockerId); } catch (err) {
        if (err?.code === 'AUTH_FAILED') throw err;
        ctx.log?.('fancourier: FANbox lookup failed, using recipient address', { lockerId: shipment.lockerId, err: err?.message });
      }
    }

    if (!locker) {
      try {
        ({ county, locality } = await resolveFanLocality(ctx, r));
      } catch (err) {
        if (String(err?.code || '').startsWith('ADDRESS_') || err?.code === 'AUTH_FAILED') throw err;
        // Nomenclator unavailable: FAN validates names server-side anyway.
        ctx.log?.('fancourier: locality nomenclator unavailable, sending raw names', { err: err?.message });
      }
    }

    const payload = buildAwbPayload(shipment, settings, { clientId, county, locality, locker });
    const res = await api(ctx, '/intern-awb', { method: 'POST', json: payload });
    const item = Array.isArray(res.body?.response) ? res.body.response[0] : undefined;
    if (!item) {
      throw new ProcessingError({
        code: 'COURIER_REJECTED',
        message: 'FAN Courier nu a emis AWB-ul.',
        hint: 'Verifică setările FAN Courier și reîncearcă. Detaliile sunt în jurnal.',
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
    // FAN prints A4/A5; A6 only for AWBs issued with ePOD (option X). VERIFY: A6 on non-ePOD AWBs.
    q.set('format', fmt === 'A6' ? (ctx.settings?.labelFormat === 'A6' ? 'A6' : 'A5') : fmt);
    const res = await api(ctx, '/awb/label', { query: q.toString(), responseType: 'buffer', headers: { Accept: 'application/pdf' } });
    if (!isPdf(res.body)) {
      throw new ProcessingError({
        code: 'LABEL_FAILED',
        message: `FAN Courier nu a trimis eticheta pentru AWB ${awb}.`,
        hint: 'Verifică dacă AWB-ul există în selfAWB și aparține punctului de ridicare setat.',
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
      throw cancelRefused(awb, err?.details ?? err);
    }
    if (res.body?.status && res.body.status !== 'success') throw cancelRefused(awb, res.body);
  },

  async track(ctx, awbs) {
    if (!awbs?.length) return [];
    const clientId = clientIdOf(ctx);
    const out = [];
    for (const group of chunk(awbs, 50)) {
      const q = new URLSearchParams({ clientId: String(clientId), language: 'ro' });
      for (const a of group) q.append('awb[]', a);
      const res = await api(ctx, '/reports/awb/tracking', { query: q.toString() });
      for (const row of res.body?.data || []) {
        if (!row?.awbNumber) continue;
        const events = Array.isArray(row.events) ? row.events : [];
        const last = latestMeaningful(events, (e) => mapFanEvent(e.id));
        const status = last ? last.status : S.CREATED;
        out.push({
          awb: String(row.awbNumber),
          status,
          statusText: last ? String(last.event.name || '').trim() : 'AWB emis',
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
    message: `FAN Courier nu a anulat AWB-ul ${awb}.`,
    hint: 'De obicei coletul a fost deja ridicat de curier. Anulează din selfAWB sau sună la FAN Courier.',
    provider: ID,
    details,
  });
}
