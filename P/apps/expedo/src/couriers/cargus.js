import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus } from './contract.js';
import {
  matchLocality, matchCounty, localityError, countyError, isBucharest, normalizeText, compactKey,
} from './locality.js';
import {
  normalizePhoneRO, classifyStatusText, parseDimensions, collectMessages, shortText,
  accountKey, money, assertRonCod, courierDateToIso, saidBy,
} from './util.js';
import { m, t } from '../i18n/index.js';

// Cargus — "UrgentOnlineAPI" (Azure API Management).
// Sources: Cargus API technical documentation V3 (cargus.ro/wp-content/uploads/DocumentationAPIV3-2.3.2-EN.pdf),
// official Cargus WooCommerce plugin 1.6.0 (wordpress.org/plugins/cargus) and PrestaShop module
// (gitlab.com/cargus/cargus-modules/prestashop).
//
// Auth: every call sends `Ocp-Apim-Subscription-Key`; POST LoginUser {UserName, Password} returns a
// JSON string token (valid 24h) sent as `Authorization: Bearer <token>`.
//
// Live check 2026-10 (invalid credentials only): Azure API Management answers every known operation
// with HTTP 401 {"statusCode":401,"message":"Access denied due to invalid subscription key. ..."}
// ("... due to missing subscription key ..." without the header) and unknown operations with 404
// {"statusCode":404,"message":"Resource not found"} — the key is checked before the backend, so the
// "bad user, valid key" answer of LoginUser could not be observed (docs: non-200 status).
// APIM routes on required query parameters: LoginUser is POST-only, AwbDocuments needs barCodes+type,
// Localities needs countryId, AwbTrace/WithRedirect and DELETE Awbs need barCode. All paths below exist.
//
// Why we resolve the locality ourselves: competitors send CountyName/LocalityName as free text and
// Cargus refuses anything that is not spelled exactly like its nomenclator (diacritics, "Sector 3",
// "Mun.", villages vs communes). We match against Localities ourselves and send LocalityId.

const PROVIDER = 'cargus';
const NAME = 'Cargus';
export const BASE_URL = 'https://urgentcargus.azure-api.net/api'; // confirmed: docs + official WP plugin default
const COUNTRY_ID = 1; // Romania
const DAY = 24 * 60 * 60;
const TOKEN_TTL = 23 * 60 * 60; // token valid 24h; refresh a bit earlier
const NOMENCLATOR_TTL = 7 * DAY;

// Names: cargus.fields.service.options.<id> in the catalogs.
export const SERVICES = ['34', '35', '36', '38', '39', '1'].map((id) => ({ id }));

// ---------------------------------------------------------------------------------------------
// Tracking status mapping (Cargus → TrackingStatus)
//
// Cargus does not publish its event-id list. AwbTrace returns, per AWB, Event[] = {Date, EventId,
// Description, LocalityName}. We use:
//   EventId 21                                   → DELIVERED   (confirmed by several integrations)
//   no events yet (AWB exists)                    → CREATED
//   otherwise the Romanian Description:
//     "anulat", "șters"                           → CANCELLED
//     "returnat la expeditor", "predat expeditorului" → RETURNED
//     "refuzat", "retur", "redirecționat retur"   → RETURNING
//     "nelivrat", "destinatar absent", "adresă greșită/incompletă", "amânat", "avizat",
//     "nu răspunde", "reprogramat"                → FAILED_ATTEMPT
//     "livrat", "confirmat de destinatar"         → DELIVERED
//     "în livrare", "predat curierului pentru livrare", "disponibil în Ship & Go" → OUT_FOR_DELIVERY
//     "ridicat", "preluat de la expeditor"        → PICKED_UP
//     "tranzit", "depozit", "hub", "sortare", "sosit" → IN_TRANSIT
//     "emis", "tipărit", "validat", "înregistrat"  → CREATED
//     anything else                               → UNKNOWN (raw text kept in statusText)
// VERIFY: extend EVENT_IDS with ids observed in production logs (statusText + EventId are logged).
const EVENT_IDS = {
  21: TrackingStatus.DELIVERED,
};

export function mapCargusEvent(event) {
  if (!event) return TrackingStatus.CREATED;
  const byId = EVENT_IDS[Number(event.EventId)];
  if (byId) return byId;
  return classifyStatusText(event.Description);
}

// ---------------------------------------------------------------------------------------------
// HTTP + auth

const subscriptionKey = (ctx) => String(ctx.credentials?.subscriptionKey || '').trim();
// One token per account (subscription key + user + password), never shared across accounts of a store.
export const tokenCacheKey = (ctx) => `cargus:token:${accountKey(subscriptionKey(ctx), ctx.credentials?.username, ctx.credentials?.password)}`;

function baseHeaders(ctx) {
  return { 'Ocp-Apim-Subscription-Key': subscriptionKey(ctx), 'Ocp-Apim-Trace': 'true' };
}

function isBadSubscriptionKey(body) {
  const t = JSON.stringify(body ?? '').toLowerCase();
  return t.includes('subscription key') || t.includes('subscription-key');
}

function subscriptionKeyError(details) {
  return new ProcessingError({
    code: 'AUTH_FAILED',
    key: 'cargus.errors.subscriptionKey',
    provider: PROVIDER,
    details,
  });
}

async function login(ctx, { force = false } = {}) {
  if (!force) {
    const cached = ctx.cache?.get(tokenCacheKey(ctx));
    if (cached) return cached;
  }
  const { username, password } = ctx.credentials || {};
  if (!subscriptionKey(ctx) || !username || !password) {
    throw new ProcessingError({ code: 'AUTH_FAILED', key: 'cargus.errors.missingCredentials', provider: PROVIDER });
  }
  const res = await ctx.http(NAME, `${BASE_URL}/LoginUser`, {
    method: 'POST',
    headers: baseHeaders(ctx),
    json: { UserName: username, Password: password },
    mapError: (status, body) => {
      if (status >= 500 || status === 429) return undefined;
      if (isBadSubscriptionKey(body)) return subscriptionKeyError(body);
      return authError(NAME, body);
    },
  });
  const token = typeof res.body === 'string' ? res.body.replace(/^"|"$/g, '').trim() : '';
  if (!token || /error|fail/i.test(token) || token.length < 10) throw authError(NAME, res.body);
  ctx.cache?.set(tokenCacheKey(ctx), token, TOKEN_TTL);
  return token;
}

/** Authenticated call; on 401 / "Failed to authenticate!" refreshes the token once and retries. */
async function api(ctx, method, path, { json, mapError, responseType } = {}) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const token = await login(ctx, { force: attempt > 0 });
    try {
      const res = await ctx.http(NAME, `${BASE_URL}/${path}`, {
        method,
        headers: { ...baseHeaders(ctx), Authorization: `Bearer ${token}` },
        json,
        responseType,
        mapError: (status, body) => {
          if (status === 401 || status === 403 || /failed to authenticate/i.test(String(body))) {
            if (isBadSubscriptionKey(body)) return subscriptionKeyError(body);
            return authError(NAME, body);
          }
          return mapError?.(status, body);
        },
      });
      if (typeof res.body === 'string' && /^"?failed to authenticate!?"?$/i.test(res.body.trim())) {
        throw authError(NAME, res.body);
      }
      return res.body;
    } catch (err) {
      if (attempt === 0 && err?.code === 'AUTH_FAILED' && err.key !== 'cargus.errors.subscriptionKey') {
        ctx.cache?.set(tokenCacheKey(ctx), null, 1);
        continue;
      }
      throw err;
    }
  }
  throw authError(NAME); // unreachable
}

const asArray = (b) => (Array.isArray(b) ? b : b ? [b] : []);

// ---------------------------------------------------------------------------------------------
// Nomenclator

async function getCounties(ctx) {
  const key = 'cargus:counties';
  let list = ctx.cache?.get(key);
  if (!list) {
    const body = await api(ctx, 'GET', `Counties?countryId=${COUNTRY_ID}`);
    list = asArray(body).map((c) => ({ id: c.CountyId, name: c.Name, code: c.Abbreviation }));
    if (list.length) ctx.cache?.set(key, list, NOMENCLATOR_TTL);
  }
  return list;
}

async function getLocalities(ctx, countyId) {
  const key = `cargus:localities:${countyId}`;
  let list = ctx.cache?.get(key);
  if (!list) {
    const body = await api(ctx, 'GET', `Localities?countryId=${COUNTRY_ID}&countyId=${countyId}`);
    list = asArray(body).map((l) => ({
      id: l.LocalityId,
      name: l.Name,
      // docs: CodPostal; some API versions: PostalCode
      postalCode: l.CodPostal ?? l.PostalCode ?? l.ZipCode ?? '',
      parent: l.ParentName || '',
      extraKm: l.ExtraKm,
    }));
    if (list.length) ctx.cache?.set(key, list, NOMENCLATOR_TTL);
  }
  return list;
}

/** Recipient county + locality as Cargus knows them, or ProcessingError ADDRESS_*. */
export async function resolveLocality(ctx, recipient) {
  const counties = await getCounties(ctx);
  const county = matchCounty(recipient, counties);
  if (!county) throw countyError({ provider: PROVIDER, providerName: NAME, county: recipient.county, countyCode: recipient.countyCode });

  const q = { city: recipient.city, zip: recipient.zip, sector: recipient.sector, county: recipient.county, countyCode: recipient.countyCode };
  const result = matchLocality(q, await getLocalities(ctx, county.id), { fuzzy: true });
  if (result.match) return { county, locality: result.match, via: result.via };

  // Bucharest ↔ Ilfov mix-ups are common ("Voluntari, București" or "București, Ilfov"):
  // accept the other county only on an exact name match.
  const bucharest = isBucharest(recipient.county, recipient.countyCode);
  const otherCode = bucharest ? 'IF' : String(recipient.countyCode || '').toUpperCase() === 'IF' || normalizeText(recipient.county) === 'ilfov' ? 'B' : null;
  if (otherCode && !result.ambiguous) {
    const other = counties.find((c) => String(c.code || '').toUpperCase() === otherCode)
      || matchCounty({ county: otherCode === 'B' ? 'Bucuresti' : 'Ilfov' }, counties);
    if (other) {
      const r2 = matchLocality({ ...q, county: other.name, countyCode: otherCode }, await getLocalities(ctx, other.id));
      if (r2.match && /^name/.test(r2.via)) {
        ctx.log?.(m('log.neighbourCounty', { provider: NAME }), { city: recipient.city, from: recipient.county, to: other.name });
        return { county: other, locality: r2.match, via: `${r2.via}+county` };
      }
    }
  }
  throw localityError({ provider: PROVIDER, providerName: NAME, city: recipient.city, county: county.name || recipient.county, result });
}

// ---------------------------------------------------------------------------------------------
// Error mapping for AWB creation

function rejected(code, key, params, field, details) {
  return new ProcessingError({ code, key: `cargus.errors.${key}`, params, retryable: false, provider: PROVIDER, field, details });
}

export function mapAwbError(body, shipment, status) {
  const msgs = collectMessages(body);
  const text = normalizeText(msgs.map((x) => `${x.path} ${x.message}`).join(' | '));
  const first = shortText(msgs[0]?.message);
  const said = saidBy(NAME, first);
  const r = shipment?.recipient || {};
  if (/pudo|ship ?go|ship and go|deliverypudopoint/.test(text)) return rejected('LOCKER_INVALID', 'locker', { said }, 'lockerId', body);
  if (/telefon|phone/.test(text)) return rejected('ADDRESS_PHONE_INVALID', 'phone', { phone: r.phone || '', said }, 'shippingAddress.phone', body);
  if (/localit|locality|\bcity\b|\boras\b/.test(text)) {
    return rejected('ADDRESS_CITY_NOT_FOUND', 'city', { city: r.city || '', county: r.county || '-', said }, 'shippingAddress.city', body);
  }
  if (/judet|county/.test(text)) return rejected('ADDRESS_COUNTY_NOT_FOUND', 'county', { county: r.county || '', said }, 'shippingAddress.province', body);
  if (/greutat|weight|\bkg\b/.test(text)) return rejected('SHIPMENT_WEIGHT_INVALID', 'weight', { weight: shipment?.weightKg ?? '?', said }, 'weightKg', body);
  if (/punct de ridicare|pickup|locationid|sender|expeditor/.test(text)) {
    return rejected('CONFIG_PICKUP_POINT_INVALID', 'pickupPoint', { said }, 'settings.pickupPointId', body);
  }
  if (/serviciu|service/.test(text)) return rejected('CONFIG_SERVICE_INVALID', 'service', { said }, 'settings.service', body);
  if (/ramburs|repayment/.test(text)) return rejected('COD_INVALID', 'cod', { said }, 'cod', body);
  if (/tarif|pricetable/.test(text)) return rejected('CONFIG_PRICE_TABLE_INVALID', 'priceTable', { said }, 'settings.priceTableId', body);
  if (/e ?mail/.test(text)) return rejected('ADDRESS_EMAIL_INVALID', 'email', { email: r.email || '', said }, 'email', body);
  if (/adresa|address|strada|street/.test(text)) return rejected('ADDRESS_STREET_INVALID', 'street', { said }, 'shippingAddress.address1', body);
  return first
    ? rejected('PROVIDER_REJECTED', 'rejected', { text: first }, undefined, body)
    : rejected('PROVIDER_REJECTED', 'rejectedStatus', { status: status ?? '?' }, undefined, body);
}

// ---------------------------------------------------------------------------------------------
// Payload

export function pickService(settings, shipment) {
  if (shipment.lockerId) return 38;
  const chosen = String(shipment.service || settings?.service || 'auto');
  if (chosen !== 'auto' && /^\d+$/.test(chosen)) return Number(chosen);
  const w = Number(shipment.weightKg) || 1;
  // ServiceId per docs annex: 34 ≤ 31 kg, 35 31–50 kg, 36 > 50 kg.
  // VERIFY: multi-parcel shipments may require 39 (Multipiece) on some contracts.
  if (w <= 31) return 34;
  if (w <= 50) return 35;
  return 36;
}

function splitWeight(total, n) {
  const base = Math.floor(total / n);
  const rest = total - base * n;
  return Array.from({ length: n }, (_, i) => Math.max(1, base + (i < rest ? 1 : 0)));
}

export function buildAwbPayload(ctx, shipment, { locality, county, pickupPointId }) {
  const s = ctx.settings || {};
  const r = shipment.recipient;
  const parcels = Math.max(0, Math.round(Number(shipment.parcels ?? 1)));
  const envelopes = Math.min(9, Math.max(0, Math.round(Number(shipment.envelopes ?? 0))));
  let totalWeight = Math.max(1, Math.ceil(Number(shipment.weightKg) || 1));
  if (parcels === 0 && envelopes > 0) totalWeight = 1;
  if (parcels > 0) totalWeight = Math.max(totalWeight, parcels);
  const dims = shipment.dimensionsCm || parseDimensions(s.defaultDimensions) || { length: 30, width: 20, height: 10 };
  const contents = String(shipment.contents || '').slice(0, 250);
  const cod = money(shipment.cod); // Cargus has no currency field: always RON (non-RON refused in createShipment)
  const bank = (s.codType || 'bank') === 'bank';
  const serviceId = pickService(s, shipment);
  const phone = normalizePhoneRO(r.phone);
  const name = (r.company || r.name || '').trim();
  const contact = (r.contactPerson || r.name || '').trim();

  const payload = {
    Sender: { LocationId: Number(pickupPointId) || pickupPointId },
    Parcels: parcels,
    Envelopes: envelopes,
    TotalWeight: totalWeight,
    ServiceId: serviceId,
    DeclaredValue: money(shipment.declaredValue),
    CashRepayment: bank ? 0 : cod,
    BankRepayment: bank ? cod : 0,
    OtherRepayment: '',
    OpenPackage: Boolean(shipment.openPackage ?? s.openPackage ?? false),
    ShipmentPayer: 1, // sender pays the shipping
    SaturdayDelivery: Boolean(shipment.saturday),
    MorningDelivery: false,
    Observations: String(shipment.notes || '').slice(0, 250),
    PackageContent: contents,
    CustomString: String(shipment.reference || ''),
    SenderReference1: String(shipment.reference || ''), // VERIFY: which reference field is printed on the label
    ParcelCodes: [
      ...splitWeight(totalWeight, parcels || 0).map((w) => ({
        Code: '0', Type: 1, Weight: w, Length: dims.length, Width: dims.width, Height: dims.height, ParcelContent: contents,
      })),
      ...Array.from({ length: parcels === 0 ? envelopes : 0 }, () => ({ Code: '0', Type: 0, Weight: 1, Length: 1, Width: 1, Height: 1, ParcelContent: contents })),
    ],
  };
  if (s.priceTableId) payload.PriceTableId = Number(s.priceTableId) || s.priceTableId;

  if (shipment.lockerId) {
    // Ship & Go (PUDO) — docs 9.3.2: DeliveryPudoPoint + ServiceId 38; recipient needs only contact data.
    payload.DeliveryPudoPoint = Number(shipment.lockerId) || shipment.lockerId;
    payload.Recipient = { Name: name, ContactPerson: contact, PhoneNumber: phone, Email: r.email || '' };
    delete payload.OpenPackage; // official plugin drops it for PUDO
  } else {
    payload.Recipient = {
      LocationId: null,
      Name: name,
      CountyId: county.id,
      CountyName: county.name,
      LocalityId: locality.id,
      LocalityName: locality.name,
      StreetId: null,
      StreetName: '', // VERIFY: street nomenclator not used; full street goes in AddressText (as the PrestaShop module does)
      BuildingNumber: '',
      AddressText: String(r.street || '').slice(0, 250),
      ContactPerson: contact,
      PhoneNumber: phone,
      Email: r.email || '',
      CodPostal: r.zip || locality.postalCode || '',
      CountryId: COUNTRY_ID,
    };
  }
  return payload;
}

/** Awbs POST answers with the barcode (number or string); WithGetAwb-style answers are arrays of {BarCode|Error}. */
function extractBarcode(body) {
  if (typeof body === 'number') return String(body);
  if (typeof body === 'string') {
    const t = body.replace(/^"|"$/g, '').trim();
    // Digits as a rule; the docs V3 2.3.2 (9.7 / 9.8) also show alphanumeric barcodes ("BarCode": "URGC10875236").
    // An error text ("Failed to authenticate!", "Error") never matches: letters prefix + at least 6 digits only.
    return /^[A-Z]{0,6}\d{6,}$/i.test(t) ? t : null;
  }
  const first = Array.isArray(body) ? body[0] : body;
  if (first && typeof first === 'object') {
    if (first.Error || first.ErrorMessage) return null;
    if (first.BarCode) return String(first.BarCode);
  }
  if (typeof first === 'number' || typeof first === 'string') return extractBarcode(first);
  return null;
}

async function resolvePickupPointId(ctx) {
  const id = String(ctx.settings?.pickupPointId || '').trim();
  if (id) return id;
  const points = await adapter.listPickupPoints(ctx);
  if (points.length === 1) return points[0].id;
  throw new ProcessingError({
    code: 'CONFIG_PICKUP_POINT_MISSING',
    key: points.length ? 'cargus.errors.pickupPointMissing' : 'cargus.errors.pickupPointMissingNone',
    params: { count: points.length, points: points.slice(0, 3).map((p) => `${p.name} – ID ${p.id}`).join('; ') },
    provider: PROVIDER,
    field: 'settings.pickupPointId',
  });
}

// Docs V3 pass AWB lists as a JSON array in the query (AwbDocuments?barCodes=[804419419,804418863]&type=PDF
// &format=1, AwbTrace/WithRedirect?barCode=[...]); the live APIM accepts those parameter names.
// VERIFY: max AWBs per AwbTrace call (we send 50) — the docs give no limit.
const encodeBarcodes = (awbs) => encodeURIComponent(`[${awbs.map((a) => (/^\d+$/.test(a) ? a : JSON.stringify(a))).join(',')}]`);

// ---------------------------------------------------------------------------------------------

const adapter = {
  id: PROVIDER,
  name: NAME,
  trackingUrl: (awb) => `https://www.cargus.ro/personal/urmareste-coletul/?tracking_number=${encodeURIComponent(awb)}`,

  // Labels and help: cargus.fields.<key> in the catalogs (src/i18n).
  credentialFields: [
    { key: 'subscriptionKey', type: 'password', required: true },
    { key: 'username', type: 'text', required: true },
    { key: 'password', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'pickupPointId', type: 'text', required: true },
    { key: 'service', type: 'select', default: 'auto',
      options: [{ value: 'auto' }, ...SERVICES.filter((x) => x.id !== '38').map((x) => ({ value: x.id }))] },
    { key: 'codType', type: 'select', default: 'bank', options: [{ value: 'bank' }, { value: 'cash' }] },
    { key: 'openPackage', type: 'checkbox', default: false },
    { key: 'labelFormat', type: 'select', default: 'A6', options: [{ value: 'A6' }, { value: 'A4' }] },
    { key: 'defaultDimensions', type: 'text', default: '30x20x10' },
    { key: 'priceTableId', type: 'text' },
  ],

  async testConnection(ctx) {
    await login(ctx, { force: true });
    const points = await adapter.listPickupPoints(ctx);
    const chosen = String(ctx.settings?.pickupPointId || '').trim();
    let extra = '';
    if (chosen && !points.some((p) => String(p.id) === chosen)) extra = m('cargus.test.pointMissing', { id: chosen });
    else if (!chosen && points.length > 1) extra = m('cargus.test.choosePoint');
    return { ok: true, message: m('cargus.test.connected', { count: points.length, extra }), info: { pickupPoints: points } };
  },

  async listPickupPoints(ctx) {
    const body = await api(ctx, 'GET', 'PickupLocations');
    return asArray(body).map((p) => ({
      id: String(p.LocationId),
      name: p.Name || t(ctx.locale, 'cargus.pointName', { id: p.LocationId }),
      address: [p.AddressText || [p.StreetName, p.BuildingNumber].filter(Boolean).join(' '), p.LocalityName, p.CountyName].filter(Boolean).join(', '),
    }));
  },

  async listServices(ctx) {
    return SERVICES.map((x) => ({ ...x, name: t(ctx?.locale, `cargus.fields.service.options.${x.id}`) }));
  },

  async listLockers(ctx, { county, city } = {}) {
    const key = 'cargus:pudo';
    let list = ctx.cache?.get(key);
    if (!list) {
      // Official plugins call `PudoPoints` (docs name it PUDO_Get).
      const body = await api(ctx, 'GET', 'PudoPoints');
      list = asArray(body).map((p) => ({
        id: String(p.Id),
        name: p.Name,
        // Real PudoPoints rows (official WP plugin 1.6.0 ships them in admin/locations/pudo_locations.json):
        // 638 of 1966 have an empty StreetName, but every row has the full `Address`
        // ("Targu Lapus, STR DOINEI NR 19 AP 9, Nr. n/a, Cod postal. 435600").
        address: String(p.Address || '').trim()
          || [[p.StreetName, p.StreetNo].filter(Boolean).join(' '), p.City, p.County].filter(Boolean).join(', '),
        city: p.City,
        county: p.County,
        cod: p.ServiceCOD !== false,
      }));
      if (list.length) ctx.cache?.set(key, list, DAY);
    }
    const ck = county && compactKey(county);
    const tk = city && compactKey(city);
    return list.filter((p) => (!ck || compactKey(p.county) === ck || (isBucharest(county) && isBucharest(p.county)))
      && (!tk || compactKey(p.city) === tk || (isBucharest(city) && isBucharest(p.city))));
  },

  async createShipment(ctx, shipment) {
    const r = shipment.recipient || {};
    assertRonCod(shipment, { provider: PROVIDER, providerName: NAME });
    const pickupPointId = await resolvePickupPointId(ctx);
    let place = {};
    if (shipment.lockerId) {
      if (!r.email) {
        throw rejected('ADDRESS_EMAIL_MISSING', 'emailMissing', {}, 'email');
      }
    } else {
      place = await resolveLocality(ctx, r);
    }
    const payload = buildAwbPayload(ctx, shipment, { ...place, pickupPointId });
    const body = await api(ctx, 'POST', 'Awbs', {
      json: payload,
      mapError: (status, b) => (status >= 400 && status < 500 && status !== 429 ? mapAwbError(b, shipment, status) : undefined),
    });
    const awb = extractBarcode(body);
    if (!awb) throw mapAwbError(body, shipment, 200);
    ctx.log?.(m('log.awbCreated', { provider: NAME, awb }), { awb, reference: shipment.reference, localityId: place.locality?.id, via: place.via });
    return { awb, raw: { response: body, localityId: place.locality?.id, localityName: place.locality?.name } };
  },

  async getLabel(ctx, awb, { format } = {}) {
    const f = (format || ctx.settings?.labelFormat || 'A6') === 'A4' ? 0 : 1; // 0 = A4, 1 = 10x14 label
    const body = await api(ctx, 'GET', `AwbDocuments?barCodes=${encodeBarcodes([String(awb)])}&type=PDF&format=${f}&printMainOnce=1`);
    const b64 = typeof body === 'string' ? body.replace(/^"|"$/g, '').trim() : '';
    const pdf = Buffer.from(b64, 'base64');
    if (pdf.subarray(0, 4).toString('latin1') !== '%PDF') {
      throw new ProcessingError({
        code: 'LABEL_UNAVAILABLE',
        key: 'cargus.errors.label',
        params: { awb },
        retryable: true,
        provider: PROVIDER,
        details: typeof body === 'string' ? body.slice(0, 500) : body,
      });
    }
    return pdf;
  },

  async cancelShipment(ctx, awb) {
    const body = await api(ctx, 'DELETE', `Awbs?barCode=${encodeURIComponent(awb)}`);
    if (body === false || String(body).toLowerCase() === 'false') {
      throw new ProcessingError({
        code: 'CANCEL_REFUSED',
        key: 'cargus.errors.cancel',
        params: { awb },
        provider: PROVIDER,
        details: body,
      });
    }
  },

  async track(ctx, awbs) {
    const out = [];
    const list = [...new Set((awbs || []).map(String).filter(Boolean))];
    for (let i = 0; i < list.length; i += 50) {
      const chunk = list.slice(i, i + 50);
      const body = await api(ctx, 'GET', `AwbTrace/WithRedirect?barCode=${encodeBarcodes(chunk)}`);
      for (const item of asArray(body)) {
        const code = String(item.Code ?? item.BarCode ?? '');
        if (!chunk.includes(code)) continue;
        const events = asArray(item.Event ?? item.Events)
          .slice()
          .sort((a, b) => String(a.Date).localeCompare(String(b.Date)));
        const last = events[events.length - 1];
        const status = mapCargusEvent(last);
        out.push({
          awb: code,
          status,
          statusText: last?.Description || (last ? 'Necunoscut' : 'AWB emis'),
          // Docs examples carry no zone ("2019-10-24T12:33:12.035"): Bucharest local time, not the server's.
          at: courierDateToIso(last?.Date),
          codCollected: status === TrackingStatus.DELIVERED,
        });
      }
    }
    return out;
  },
};

export default adapter;
