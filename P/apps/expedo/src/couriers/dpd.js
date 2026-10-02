import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus as S } from './contract.js';
import { findLocality, norm, normCounty } from './locality.js';
import {
  NOMENCLATOR_TTL, cached, cacheGet, cacheSet, chunk, isPdf, bufferToJson, latestMeaningful, accountKey, money,
} from './util.js';

// DPD Romania — Web API v1 (https://api.dpd.ro/v1), JSON over POST.
// Source: https://api.dpd.ro/api/docs/ (Web API Documentation) and the official request examples
// at services.dpd.ro/api/api_examples.php. Same platform as Speedy (Bulgaria).
//
// No session: userName + password go in every JSON body. Errors usually come back as HTTP 200 with
// { error: { code, message, context, component } }.
// The AWB is the shipment id, which is also the id of the first parcel.
//
// Live check 2026-10 (invalid userName/password) on /client/contract, /location/country, /location/site,
// /location/site/csv/642 (POST JSON or GET query), /services, /shipment, /shipment/info, /print, /track,
// /location/office, /shipment/cancel — all HTTP 200 application/json:
//   {"error":{"context":"","message":"Nu s-a putut găsi utilizatorul pentru autentificare! (EE2026…)",
//             "id":"EE2026…","code":1}}            (language EN: "Unable to find user to authenticate!")
//   no userName at all → message "Wrong username format (EE…)". List methods add their empty list
//   ("countries":[], "sites":[], "services":[], "offices":[]). Unknown path → HTML 404 page.
// Code 1 is "General Error" in Appendix 3 (there is no auth-specific code), so auth is detected from the
// message. Docs (api.dpd.ro/api/docs): track ≤ 10 parcels per call; print paperSize A4 | A6 | A4_4xA6;
// the error `component` is a JSONPath like "$.recipient.address.siteId".

const PROVIDER = 'DPD';
const ID = 'dpd';
const BASE = 'https://api.dpd.ro/v1';
const ROMANIA = 642;
const DEFAULT_SERVICE = 2505; // "DPD Standard" (domestic). VERIFY per contract with listServices().
const PARCELS_TTL = 120 * 24 * 60 * 60;

// DPD track & trace operation codes (Appendix 1) → normalized status. `null` = informational.
//   148 date expediere primite ........................................ created
//   164 ridicare nereușită (încă la expeditor) ........................ created
//   39  ridicat de curier ............................................. picked_up
//   1, 2, 11, 21, 115, 116, 152, 176, 181, 217 scanări / tranzit / redirecționat ... in_transit
//   12  în livrare; 134 pregătit pentru ridicare de destinatar (oficiu/locker);
//   144 predat pentru verificare conținut ............................. out_for_delivery
//   -14 livrat ........................................................ delivered
//   44, 69, 136, 169, 190, 38 nelivrat / amânat / adresă incompletă / întors în oficiu ... failed_attempt
//   111 retur la expeditor, 121 oprit de expeditor, 123 refuzat, 195 refuz verificare ... returning
//   124 livrat înapoi expeditorului ................................... returned
//   128 anulat, 120 refuz de expediere ................................ cancelled
//   112, 114, 125, 127, 129 asigurări / distrugere / furt / închidere administrativă ... unknown
//   175 Predict, 1134 notificare trimisă .............................. informational
const DPD_STATUS = {
  148: S.CREATED, 164: S.CREATED,
  39: S.PICKED_UP,
  1: S.IN_TRANSIT, 2: S.IN_TRANSIT, 11: S.IN_TRANSIT, 21: S.IN_TRANSIT, 115: S.IN_TRANSIT, 116: S.IN_TRANSIT,
  152: S.IN_TRANSIT, 176: S.IN_TRANSIT, 181: S.IN_TRANSIT, 217: S.IN_TRANSIT,
  12: S.OUT_FOR_DELIVERY, 134: S.OUT_FOR_DELIVERY, 144: S.OUT_FOR_DELIVERY,
  [-14]: S.DELIVERED,
  44: S.FAILED_ATTEMPT, 69: S.FAILED_ATTEMPT, 136: S.FAILED_ATTEMPT, 169: S.FAILED_ATTEMPT, 190: S.FAILED_ATTEMPT, 38: S.FAILED_ATTEMPT,
  111: S.RETURNING, 121: S.RETURNING, 123: S.RETURNING, 195: S.RETURNING,
  124: S.RETURNED,
  128: S.CANCELLED, 120: S.CANCELLED,
  112: S.UNKNOWN, 114: S.UNKNOWN, 125: S.UNKNOWN, 127: S.UNKNOWN, 129: S.UNKNOWN,
  175: null, 1134: null,
};

export function mapDpdOperation(code) {
  const n = Number(code);
  if (Object.hasOwn(DPD_STATUS, n)) return DPD_STATUS[n];
  return S.UNKNOWN;
}

/** "2024-03-01T10:20:00+0200" → ISO. */
export function parseDpdDate(v) {
  if (!v) return undefined;
  const s = String(v).replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}

// ---------------------------------------------------------------- http & errors

const AUTH_RE = /(user ?name|utilizator|parol|password|autentific|authenticat|login|credential|neautoriz|unauthori)/i;

function dpdError(err, raw) {
  const code = Number(err?.code);
  const text = `${err?.message || ''} ${err?.context || ''} ${err?.component || ''}`;
  // Confirmed live: auth failures are code 1 (General Error) with "Nu s-a putut găsi utilizatorul pentru
  // autentificare!" / "Wrong username format". VERIFY: the message for an existing user with a wrong password.
  if ((code === 1 || !code) && AUTH_RE.test(err?.message || '') && !/recipient|destinatar|sender\.|expeditor/i.test(text)) {
    const e = authError(PROVIDER, raw);
    e.provider = ID;
    return e;
  }
  const component = String(err?.component || err?.context || '');
  const mk = (c, message, field, hint = 'Corectează datele comenzii și reîncearcă.') =>
    new ProcessingError({ code: c, message, hint, field, provider: ID, details: raw });
  if (code === 120 || /address/i.test(component)) {
    if (/site|postCode/i.test(component)) return mk('ADDRESS_CITY_NOT_FOUND', 'DPD nu acceptă localitatea sau codul poștal al destinatarului.', 'shippingAddress.city');
    return mk('ADDRESS_STREET_INVALID', 'DPD nu acceptă adresa destinatarului.', 'shippingAddress.address1', 'Completează strada și numărul în adresa de livrare.');
  }
  if (/phone/i.test(component)) return mk('ADDRESS_PHONE_INVALID', 'DPD nu acceptă telefonul destinatarului.', 'shippingAddress.phone', 'Telefonul trebuie să înceapă cu 0 sau + și să conțină doar cifre.');
  if (/clientName|contactName/i.test(component)) return mk('ADDRESS_NAME_INVALID', 'DPD nu acceptă numele destinatarului (minim 3 caractere).', 'shippingAddress.name');
  if (/email/i.test(component)) return mk('ADDRESS_EMAIL_INVALID', 'DPD nu acceptă e-mailul destinatarului.', 'email');
  if (code === 180 || /pickupOffice/i.test(component)) return mk('LOCKER_INVALID', 'Oficiul / lockerul DPD ales nu este valid.', 'lockerId', 'Alege alt punct DPD sau livrare la adresă.');
  if (code === 160 || code === 100 || /sender/i.test(component)) return mk('SETTINGS_INVALID', 'DPD nu acceptă expeditorul din setări.', 'settings.senderClientId', 'Verifică „ID client expeditor” și „Oficiu de predare” în Setări → Curieri → DPD.');
  if (code === 400) return mk('SETTINGS_INVALID', 'Serviciul DPD ales nu este disponibil pentru această destinație.', 'settings.serviceId', 'Alege alt serviciu în Setări → Curieri → DPD.');
  if (code === 410) return mk('COD_INVALID', 'DPD nu acceptă rambursul pentru această expediere.', 'cod', 'Verifică dacă ai anexa de ramburs în contract și suma.');
  if (code === 415) return mk('DECLARED_VALUE_INVALID', 'DPD nu acceptă valoarea declarată.', 'declaredValue');
  if (code === 420) return mk('OPEN_PACKAGE_INVALID', 'DPD nu acceptă opțiunea de deschidere colet pentru această expediere.', 'openPackage', 'Dezactivează „Deschidere colet” sau verifică contractul.');
  if (code === 620 || code === 630) return mk('PARCELS_INVALID', 'DPD nu acceptă greutatea sau coletele declarate.', 'weightKg');
  if (code === 600) return mk('CONTENT_INVALID', 'DPD nu acceptă descrierea conținutului.', 'contents');
  if (code === 700) return mk('SETTINGS_INVALID', 'DPD nu acceptă plătitorul transportului ales.', 'settings.payer');
  return new ProcessingError({
    code: 'COURIER_REJECTED',
    message: 'DPD a refuzat cererea.',
    hint: 'Verifică datele comenzii și setările DPD. Detaliile sunt în jurnal.',
    provider: ID,
    details: raw,
  });
}

async function call(ctx, path, body = {}, opts = {}) {
  const { userName, password } = ctx.credentials || {};
  if (!userName || !password) throw authError(PROVIDER, 'missing credentials');
  const res = await ctx.http(PROVIDER, `${BASE}${path}`, {
    method: 'POST',
    json: { userName, password, language: 'RO', ...body },
    timeoutMs: 60_000,
    ...opts,
  });
  const b = res.body;
  if (b && !Buffer.isBuffer(b) && typeof b === 'object' && b.error) throw dpdError(b.error, b);
  return b;
}

// ---------------------------------------------------------------- nomenclator

/** Minimal CSV parser (quoted fields, "" escapes). */
export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let q = false;
  const s = String(text ?? '').replace(/^﻿/, '');
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (q) {
      if (ch === '"') {
        if (s[i + 1] === '"') { field += '"'; i++; } else q = false;
      } else field += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && s[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some((x) => x !== '')) rows.push(row);
      row = [];
    } else field += ch;
  }
  row.push(field);
  if (row.some((x) => x !== '')) rows.push(row);
  return rows;
}

const SITE_COLUMNS = ['id', 'countryId', 'mainSiteId', 'type', 'typeEn', 'name', 'nameEn', 'municipality', 'municipalityEn', 'region', 'regionEn', 'postCode'];

/** CSV → compact rows [id, name, municipality, region, postCode, type]. */
export function compactSites(csvText) {
  const rows = parseCsv(csvText);
  if (!rows.length) return [];
  let header = SITE_COLUMNS;
  if (/^id$/i.test(rows[0][0]?.trim())) header = rows.shift().map((h) => h.trim());
  const ix = (k) => header.findIndex((h) => h.toLowerCase() === k.toLowerCase());
  const [iId, iName, iMun, iReg, iPost, iType] = ['id', 'name', 'municipality', 'region', 'postCode', 'type'].map(ix);
  return rows
    .filter((r) => r[iId] && r[iName])
    .map((r) => [Number(r[iId]), r[iName], r[iMun] || '', r[iReg] || '', r[iPost] || '', r[iType] || '']);
}

// Whether the CSV export is allowed depends on the account, so the "unavailable" flag is per account.
const sitesOffKey = (ctx) => `dpd:sites:642:unavailable:${accountKey(ctx.credentials?.userName, ctx.credentials?.password)}`;

async function loadSites(ctx) {
  return cached(ctx, 'dpd:sites:642', NOMENCLATOR_TTL, async () => {
    const text = await call(ctx, `/location/site/csv/${ROMANIA}`, {}, { responseType: 'text', headers: { Accept: 'text/csv, application/json' } });
    if (typeof text === 'string' && text.trim().startsWith('{')) {
      const j = JSON.parse(text);
      if (j.error) throw dpdError(j.error, j);
    }
    const sites = compactSites(text);
    if (sites.length < 100) throw new ProcessingError({ code: 'PROVIDER_REJECTED', message: 'DPD nu a trimis nomenclatorul de localități.', provider: ID, retryable: true, details: String(text).slice(0, 300) });
    return sites;
  });
}

/** Fallback when the CSV export is not allowed for the account: POST /location/site (max 10 results). */
async function findSites(ctx, recipient) {
  const toAscii = (s) => norm(s).toUpperCase();
  const queries = [{ countryId: ROMANIA, name: toAscii(String(recipient.city).replace(/^(mun|municipiul|oras|orasul|com|comuna|sat)\.?\s+/i, '')) }];
  if (recipient.zip) queries.unshift({ countryId: ROMANIA, postCode: String(recipient.zip) });
  const seen = new Map();
  for (const q of queries) {
    const body = await call(ctx, '/location/site', q);
    for (const s of body?.sites || []) seen.set(s.id, [s.id, s.name, s.municipality || '', s.region || '', s.postCode || '', s.type || '']);
  }
  return [...seen.values()];
}

export async function resolveDpdSite(ctx, recipient) {
  let sites;
  if (!(await cacheGet(ctx, sitesOffKey(ctx)))) {
    try {
      sites = await loadSites(ctx);
    } catch (err) {
      if (err?.code === 'AUTH_FAILED') throw err;
      await cacheSet(ctx, sitesOffKey(ctx), true, 6 * 60 * 60); // do not retry the export on every order
      ctx.log?.('dpd: site CSV unavailable, using findSite', { err: err?.message });
    }
  }
  if (!sites) sites = await findSites(ctx, recipient);
  // Same-named villages are told apart by postal code, then by the commune (municipality) typed.
  const hit = findLocality(sites, recipient, {
    nameOf: (r) => r[1],
    countyOf: (r) => r[3],
    zipOf: (r) => r[4],
    parentOf: (r) => r[2],
    provider: ID,
    providerName: PROVIDER,
  });
  return { siteId: hit[0], siteName: hit[1] };
}

// ---------------------------------------------------------------- payload

const truthy = (v) => v === true || v === 'true';

export function buildShipmentRequest(shipment, settings, { siteId }) {
  const r = shipment.recipient;
  const serviceId = Number(shipment.service || settings.serviceId || DEFAULT_SERVICE);
  const isCompany = !!r.company;
  const recipient = {
    privatePerson: !isCompany,
    clientName: (isCompany ? r.company : r.name || '').slice(0, 60),
    ...(isCompany ? { contactName: (r.contactPerson || r.name || '').slice(0, 60) } : {}),
    phone1: { number: String(r.phone || '').replace(/[^\d+]/g, '') },
    ...(r.email ? { email: r.email } : {}),
  };
  if (shipment.lockerId) {
    recipient.pickupOfficeId = Number(shipment.lockerId);
  } else {
    // Street matching against DPD's street nomenclator is fragile; the doc accepts
    // "all components of the address within the site stored in addressNote".
    recipient.address = { countryId: ROMANIA, siteId, addressNote: String(r.street || '').slice(0, 200) };
  }

  const sender = {};
  if (settings.senderClientId) sender.clientId = Number(settings.senderClientId);
  if (settings.dropoffOfficeId) sender.dropoffOfficeId = Number(settings.dropoffOfficeId);
  if (settings.senderPhone) sender.phone1 = { number: String(settings.senderPhone).replace(/[^\d+]/g, '') };

  const additionalServices = {};
  if (money(shipment.cod) > 0) {
    additionalServices.cod = { amount: money(shipment.cod), processingType: 'CASH', ...(shipment.currency && shipment.currency !== 'RON' ? { currencyCode: shipment.currency } : {}) };
    const open = shipment.openPackage ?? truthy(settings.openPackage);
    // OBPD = options before payment; only meaningful with COD. VERIFY: return service/payer per contract.
    if (open) additionalServices.obpd = { option: 'OPEN', returnShipmentServiceId: serviceId, returnShipmentPayer: 'SENDER' };
  }
  if (money(shipment.declaredValue) > 0) additionalServices.declaredValue = { amount: money(shipment.declaredValue) };

  const req = {
    ...(Object.keys(sender).length ? { sender } : {}),
    recipient,
    service: {
      serviceId,
      autoAdjustPickupDate: true,
      ...(shipment.saturday ? { saturdayDelivery: true } : {}),
      ...(Object.keys(additionalServices).length ? { additionalServices } : {}),
    },
    content: {
      parcelsCount: Math.max(1, shipment.parcels || 1),
      totalWeight: Math.max(0.1, Number(shipment.weightKg || 1)),
      contents: String(shipment.contents || 'Colet').slice(0, 100),
      package: settings.package || 'BOX',
    },
    payment: { courierServicePayer: settings.payer === 'RECIPIENT' ? 'RECIPIENT' : 'SENDER' },
    ref1: String(shipment.reference ?? '').slice(0, 30),
    ...(shipment.notes ? { shipmentNote: String(shipment.notes).slice(0, 200) } : {}),
  };
  if (req.content.parcelsCount === 1 && shipment.dimensionsCm) {
    const d = shipment.dimensionsCm;
    req.content.parcels = [{ seqNo: 1, weight: req.content.totalWeight, size: { width: Math.round(d.width), depth: Math.round(d.length), height: Math.round(d.height) } }];
  }
  return req;
}

/** AWB → parcel ids, per account (two DPD accounts in one store must not mix them up). */
export const parcelsKey = (ctx, awb) => `dpd:parcels:${accountKey(ctx.credentials?.userName, ctx.credentials?.password)}:${awb}`;

async function parcelIdsFor(ctx, awb) {
  const hit = await cacheGet(ctx, parcelsKey(ctx, awb));
  if (Array.isArray(hit) && hit.length) return hit;
  try {
    const body = await call(ctx, '/shipment/info', { shipmentIds: [String(awb)] });
    const ids = (body?.shipments?.[0]?.content?.parcels || []).map((p) => String(p.id)).filter(Boolean);
    if (ids.length) {
      await cacheSet(ctx, parcelsKey(ctx, awb), ids, PARCELS_TTL);
      return ids;
    }
  } catch (err) {
    if (err?.code === 'AUTH_FAILED') throw err;
  }
  return [String(awb)];
}

// ---------------------------------------------------------------- adapter

export default {
  id: ID,
  name: PROVIDER,
  // tracking.dpd.ro/?shipmentNumber=… answers 301 to this URL (live check); the page itself sits behind a
  // Cloudflare browser check, so only a real browser sees the content.
  trackingUrl: (awb) => `https://services.dpd.ro/tracking/?shipmentNumber=${encodeURIComponent(awb)}&language=ro`,

  credentialFields: [
    { key: 'userName', label: 'Utilizator API DPD', type: 'text', required: true, help: 'Primit de la DPD pentru integrare (nu e același cu contul de pe site, de obicei).' },
    { key: 'password', label: 'Parolă API DPD', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'senderClientId', label: 'ID client expeditor (punct de ridicare)', type: 'text', help: 'Lasă gol pentru adresa contului. „Testează conexiunea” îți arată ID-urile disponibile.' },
    { key: 'dropoffOfficeId', label: 'Oficiu DPD de predare (opțional)', type: 'text', help: 'Completează doar dacă predai coletele tu la un oficiu DPD.' },
    { key: 'senderPhone', label: 'Telefon expeditor', type: 'text', help: 'Apare pe AWB; implicit cel din contul DPD.' },
    { key: 'serviceId', label: 'Serviciu implicit', type: 'number', default: DEFAULT_SERVICE, help: '2505 = DPD Standard. Lista exactă vine din contractul tău.' },
    {
      key: 'labelFormat', label: 'Format etichetă', type: 'select', default: 'A6',
      options: [{ value: 'A6', label: 'A6 (imprimantă termică)' }, { value: 'A4', label: 'A4' }],
    },
    { key: 'openPackage', label: 'Deschidere colet la livrare', type: 'checkbox', default: false, help: 'Clientul poate deschide coletul înainte să plătească rambursul.' },
    {
      key: 'payer', label: 'Cine plătește transportul', type: 'select', default: 'SENDER',
      options: [{ value: 'SENDER', label: 'Expeditorul (tu)' }, { value: 'RECIPIENT', label: 'Destinatarul' }],
    },
  ],

  async testConnection(ctx) {
    const body = await call(ctx, '/client/contract');
    const clients = body?.clients || [];
    const list = clients.map((c) => `${c.clientId} (${c.objectName || c.clientName})`);
    return {
      ok: true,
      message: `Conectat la DPD. ${clients.length === 1 ? 'Un punct de ridicare' : `${clients.length} puncte de ridicare`} în contract${list.length ? `: ${list.slice(0, 5).join(', ')}` : ''}.`,
      info: { clients },
    };
  },

  async createShipment(ctx, shipment) {
    const settings = ctx.settings || {};
    let siteId;
    if (!shipment.lockerId) ({ siteId } = await resolveDpdSite(ctx, shipment.recipient));
    const req = buildShipmentRequest(shipment, settings, { siteId });
    const body = await call(ctx, '/shipment', req);
    if (!body?.id) {
      // Not retryable: without an id we cannot tell whether DPD created it; a blind retry may duplicate it.
      throw new ProcessingError({ code: 'COURIER_REJECTED', message: 'DPD nu a emis AWB-ul.', hint: 'Verifică în contul DPD dacă expedierea a fost creată înainte să reîncerci, ca să nu se dubleze.', retryable: false, provider: ID, details: body });
    }
    const parcelIds = (body.parcels || []).map((p) => String(p.id)).filter(Boolean);
    if (parcelIds.length) await cacheSet(ctx, parcelsKey(ctx, body.id), parcelIds, PARCELS_TTL);
    return { awb: String(body.id), price: body.price?.total, raw: body };
  },

  async getLabel(ctx, awb, { format } = {}) {
    const paperSize = (format || ctx.settings?.labelFormat || 'A6') === 'A4' ? 'A4' : 'A6';
    const ids = await parcelIdsFor(ctx, awb);
    const buf = await call(ctx, '/print', { paperSize, format: 'pdf', parcels: ids.map((id) => ({ parcel: { id } })) }, { responseType: 'buffer', headers: { Accept: 'application/pdf, application/json' } });
    if (isPdf(buf)) return buf;
    const j = Buffer.isBuffer(buf) ? bufferToJson(buf) : buf;
    if (j?.error) throw dpdError(j.error, j);
    throw new ProcessingError({ code: 'LABEL_FAILED', message: `DPD nu a trimis eticheta pentru AWB ${awb}.`, hint: 'Reîncearcă în câteva minute.', retryable: true, provider: ID, details: j ?? String(buf).slice(0, 300) });
  },

  async cancelShipment(ctx, awb) {
    try {
      await call(ctx, '/shipment/cancel', { shipmentId: String(awb), comment: 'Anulat din Expedo' });
    } catch (err) {
      if (err?.code === 'AUTH_FAILED' || err?.retryable) throw err;
      throw new ProcessingError({
        code: 'CANCEL_REFUSED',
        message: `DPD nu a anulat AWB-ul ${awb}.`,
        hint: 'DPD anulează doar AWB-urile pentru care nu s-a comandat încă ridicarea. Sună la DPD dacă trebuie oprit.',
        provider: ID,
        details: err?.details ?? String(err?.message || err),
      });
    }
  },

  async track(ctx, awbs) {
    if (!awbs?.length) return [];
    const out = [];
    for (const group of chunk([...new Set(awbs.map(String))], 10)) { // API limit (docs): up to 10 parcels per request
      const body = await call(ctx, '/track', { parcels: group.map((id) => ({ id: String(id) })), lastOperationOnly: false });
      for (const p of body?.parcels || []) {
        if (!p?.parcelId || p.error) continue;
        const ops = [...(p.operations || [])].sort((a, b) => (Date.parse(parseDpdDate(a.dateTime)) || 0) - (Date.parse(parseDpdDate(b.dateTime)) || 0));
        const last = latestMeaningful(ops, (o) => mapDpdOperation(o.operationCode));
        const status = last ? last.status : S.CREATED;
        out.push({
          awb: String(p.parcelId),
          status,
          statusText: last ? String(last.event.description || '').trim() : 'AWB emis',
          at: last ? parseDpdDate(last.event.dateTime) : undefined,
          ...(status === S.DELIVERED ? { codCollected: true } : {}),
        });
      }
    }
    return out;
  },

  async listServices(ctx) {
    const body = await call(ctx, '/services');
    return (body?.services || []).map((s) => ({ id: String(s.id), name: s.name || s.nameEn }));
  },

  async listPickupPoints(ctx) {
    const body = await call(ctx, '/client/contract');
    return (body?.clients || []).map((c) => ({
      id: String(c.clientId),
      name: c.objectName || c.clientName,
      address: c.address?.fullAddressString || '',
    }));
  },

  async listLockers(ctx, { county, city } = {}) {
    const body = await call(ctx, '/location/office', { countryId: ROMANIA, ...(city ? { siteName: norm(city).toUpperCase() } : {}), limit: 200 });
    return (body?.offices || [])
      .filter((o) => !county || !o.address?.siteAddressString || normCounty(o.address.siteAddressString).includes(normCounty(county)))
      .map((o) => ({ id: String(o.id), name: o.name, address: o.address?.fullAddressString || '' }));
  },
};
