import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus } from './contract.js';
import {
  matchLocality, matchCounty, localityError, countyError, isBucharest, normalizeText, compactKey,
} from './locality.js';
import {
  normalizePhoneRO, classifyStatusText, collectMessages, shortText, accountKey, money, courierDateToIso, looksLikeHtml,
  saidBy,
} from './util.js';
import { m, t } from '../i18n/index.js';

// Sameday Courier API.
// Sources: official PHP SDK github.com/sameday-courier/php-sdk (v2.4.2 — endpoints, field names,
// form-encoded bodies) and the official WooCommerce plugin github.com/sameday-courier/woocommerce-plugin
// (sandbox host, service codes, OPCG open-package tax, easybox handling, cities nomenclator).
//
// Auth: POST /api/authenticate (form body remember_me=1) with X-AUTH-USERNAME / X-AUTH-PASSWORD →
// { token, expire_at: "Y-m-d H:i" }; then header X-AUTH-TOKEN. Bodies are application/x-www-form-urlencoded
// with PHP bracket notation (awbRecipient[name]=..., parcels[0][weight]=...), exactly as the SDK sends them.
//
// Live check 2026-10 (invalid credentials, production api.sameday.ro and demo sameday-api.demo.zitec.com
// behave the same): POST /api/authenticate with bad X-AUTH-* → HTTP 403
// {"error":{"code":403,"message":"Invalid credentials."}}; any /api/... call with a bad X-AUTH-TOKEN →
// HTTP 401 with the same shape (code 401); GET /api/authenticate → 405. Production sits behind
// Cloudflare, so a 403 can also be an HTML challenge page — that is not a credentials problem.
// DELETE /api/awb/{unknown} on production → 404 {"error":{"code":404,"message":"Couldn't determine an
// AWB/parcel with `X` number."}}.

const PROVIDER = 'sameday';
const NAME = 'Sameday';
export const PROD_URL = 'https://api.sameday.ro';
export const SANDBOX_URL = 'https://sameday-api.demo.zitec.com';
const DAY = 24 * 60 * 60;
const NOMENCLATOR_TTL = 7 * DAY;
const PAGE_SIZE = 500; // the official SDK itself requests 500/page (GetStatusSync); VERIFY on geolocation/lockers

// Service codes are stable; numeric ids differ per account, so we resolve ids via /api/client/services.
// Names: sameday.services.<code> in the catalogs.
export const SERVICE_CODES = ['24', 'LN', '6H', 'PP'];

// ---------------------------------------------------------------------------------------------
// Tracking status mapping (Sameday → TrackingStatus)
//
// GET /api/client/awb/{awb}/status → { expeditionSummary: {delivered, canceled, ...},
//   expeditionStatus: {statusId, status, statusLabel, statusState, statusDate, ...}, expeditionHistory: [...] }
// 1. expeditionSummary.canceled → CANCELLED; expeditionSummary.delivered → DELIVERED
// 2. statusId (ids observed in public integrations — VERIFY against Sameday's status list):
//      1  colet în așteptare / AWB emis          → CREATED
//      23 înregistrat                             → CREATED
//      4  ridicat de la expeditor                 → PICKED_UP
//      56 în tranzit                              → IN_TRANSIT
//      84 depozit central                         → IN_TRANSIT
//      33 în livrare                              → OUT_FOR_DELIVERY
//      78 încărcat în easybox / punct de livrare  → OUT_FOR_DELIVERY (așteaptă ridicarea)
//      9  livrat cu succes                        → DELIVERED
//      3  ramburs transferat                      → DELIVERED (codCollected)
// 3. otherwise the Romanian text (status / statusLabel / statusState), same rules as Cargus:
//      anulat → CANCELLED; returnat la expeditor → RETURNED; refuzat / retur → RETURNING;
//      nelivrat / destinatar absent / adresă greșită / amânat → FAILED_ATTEMPT; livrat → DELIVERED;
//      în livrare / depus în easybox → OUT_FOR_DELIVERY; ridicat / preluat → PICKED_UP;
//      tranzit / depozit / hub → IN_TRANSIT; înregistrat / emis → CREATED; else UNKNOWN.
const STATUS_IDS = {
  1: TrackingStatus.CREATED,
  23: TrackingStatus.CREATED,
  4: TrackingStatus.PICKED_UP,
  56: TrackingStatus.IN_TRANSIT,
  84: TrackingStatus.IN_TRANSIT,
  33: TrackingStatus.OUT_FOR_DELIVERY,
  78: TrackingStatus.OUT_FOR_DELIVERY,
  9: TrackingStatus.DELIVERED,
  3: TrackingStatus.DELIVERED,
};

export function mapSamedayStatus(body) {
  const summary = body?.expeditionSummary || {};
  const st = body?.expeditionStatus || {};
  if (summary.canceled === true || summary.canceled === 1) return TrackingStatus.CANCELLED;
  const text = [st.status, st.statusLabel, st.statusState].filter(Boolean).join(' | ');
  const byText = classifyStatusText(text);
  // Returns/refusals/cancellations in the text win over the generic id (a return can be "delivered" to the sender).
  if ([TrackingStatus.RETURNED, TrackingStatus.RETURNING, TrackingStatus.CANCELLED].includes(byText)) return byText;
  if (summary.delivered === true || summary.delivered === 1) return TrackingStatus.DELIVERED;
  const byId = STATUS_IDS[Number(st.statusId)];
  if (byId) return byId;
  if (byText !== TrackingStatus.UNKNOWN) return byText;
  return st.statusId == null && !text ? TrackingStatus.CREATED : TrackingStatus.UNKNOWN;
}

// ---------------------------------------------------------------------------------------------
// HTTP + auth

const baseUrl = (ctx) => (ctx.settings?.sandbox === true || ctx.settings?.sandbox === 'true' || ctx.settings?.sandbox === 1 ? SANDBOX_URL : PROD_URL);
const env = (ctx) => (baseUrl(ctx) === SANDBOX_URL ? 'demo' : 'prod');
const account = (ctx) => accountKey(env(ctx), ctx.credentials?.username, ctx.credentials?.password);
/** Token cache key: per environment AND per account (user + password), never shared. */
export const tokenKey = (ctx) => `sameday:${env(ctx)}:token:${account(ctx)}`;
/** Shared nomenclator data (counties, cities): per environment only. */
const ck = (ctx, k) => `sameday:${env(ctx)}:${k}`;
/** Account data (services and their ids, pickup points, contact persons): per account. */
const ak = (ctx, k) => `sameday:${env(ctx)}:${account(ctx)}:${k}`;

/** Cloudflare challenge / HTML error page in front of the API: transient, not bad credentials. */
function blockedError(status, body) {
  return new ProcessingError({
    code: 'PROVIDER_DOWN',
    key: 'sameday.errors.blocked',
    params: { status },
    retryable: true,
    provider: PROVIDER,
    details: String(Buffer.isBuffer(body) ? body.toString('utf8') : body).slice(0, 300),
  });
}

/** PHP http_build_query: nested objects/arrays → a[b][0][c]=v; null/undefined skipped; booleans → 1/0. */
export function toForm(obj) {
  const params = new URLSearchParams();
  const add = (prefix, v) => {
    if (v === null || v === undefined) return;
    if (Array.isArray(v)) return v.forEach((x, i) => add(`${prefix}[${i}]`, x));
    if (typeof v === 'object') return Object.entries(v).forEach(([k, x]) => add(prefix ? `${prefix}[${k}]` : k, x));
    params.append(prefix, typeof v === 'boolean' ? (v ? '1' : '0') : String(v));
  };
  add('', obj);
  return params.toString();
}

/** "2026-10-03 14:20" (Bucharest time, no zone) → seconds from now, minus a safety margin. */
export function tokenTtl(expireAt, now = Date.now()) {
  const m = String(expireAt || '').match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?/);
  if (!m) return 12 * 60 * 60;
  // Assume UTC+3 (summer time) so we never keep a token past its real expiry.
  const t = Date.parse(`${m[1]}T${m[2]}:${m[3] || '00'}+03:00`);
  if (Number.isNaN(t)) return 12 * 60 * 60;
  return Math.max(60, Math.min(30 * DAY, Math.floor((t - now) / 1000) - 300));
}

async function authenticate(ctx, { force = false } = {}) {
  if (!force) {
    const cached = ctx.cache?.get(tokenKey(ctx));
    if (cached) return cached;
  }
  const { username, password } = ctx.credentials || {};
  if (!username || !password) {
    throw new ProcessingError({ code: 'AUTH_FAILED', key: 'sameday.errors.missingCredentials', provider: PROVIDER });
  }
  const res = await ctx.http(NAME, `${baseUrl(ctx)}/api/authenticate`, {
    method: 'POST',
    headers: { 'X-AUTH-USERNAME': username, 'X-AUTH-PASSWORD': password, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: toForm({ remember_me: true }),
    mapError: (status, body) => {
      if (status >= 500 || status === 429) return undefined;
      if (looksLikeHtml(body)) return blockedError(status, body);
      if (env(ctx) === 'demo') {
        return new ProcessingError({ ...authError(NAME, body).toJSON(), hintKey: 'sameday.errors.sandboxAuthHint' });
      }
      return authError(NAME, body);
    },
  });
  const token = res.body?.token;
  if (!token) throw authError(NAME, res.body);
  ctx.cache?.set(tokenKey(ctx), token, tokenTtl(res.body?.expire_at));
  return token;
}

/** Authenticated call; a 401/403 drops the cached token and retries once (same as the SDK). */
async function api(ctx, method, path, { query, form, mapError, responseType } = {}) {
  const qs = query ? `?${new URLSearchParams(Object.entries(query).filter(([, v]) => v != null && v !== '').map(([k, v]) => [k, String(v)]))}` : '';
  for (let attempt = 0; attempt < 2; attempt++) {
    const token = await authenticate(ctx, { force: attempt > 0 });
    try {
      const headers = { 'X-AUTH-TOKEN': token };
      if (form) headers['Content-Type'] = 'application/x-www-form-urlencoded';
      const res = await ctx.http(NAME, `${baseUrl(ctx)}${path}${qs}`, {
        method,
        headers,
        body: form ? toForm(form) : undefined,
        responseType,
        mapError: (status, body) => {
          if ((status === 401 || status === 403) && looksLikeHtml(body)) return blockedError(status, body);
          return status === 401 || status === 403 ? authError(NAME, body) : mapError?.(status, body);
        },
      });
      return res.body;
    } catch (err) {
      if (attempt === 0 && err?.code === 'AUTH_FAILED') {
        ctx.cache?.set(tokenKey(ctx), null, 1);
        continue;
      }
      throw err;
    }
  }
  throw authError(NAME);
}

/** Paginated GET: { data, currentPage, pages, perPage, total }. */
async function getAll(ctx, path, query = {}) {
  const all = [];
  for (let page = 1; page <= 100; page++) {
    const body = await api(ctx, 'GET', path, { query: { ...query, page, countPerPage: PAGE_SIZE } });
    const data = Array.isArray(body?.data) ? body.data : [];
    all.push(...data);
    const pages = Number(body?.pages) || 1;
    if (page >= pages || !data.length) break;
  }
  return all;
}

// ---------------------------------------------------------------------------------------------
// Cached lookups

async function cached(ctx, key, ttl, load) {
  const hit = ctx.cache?.get(key);
  if (hit) return hit;
  const value = await load();
  if (value && (!Array.isArray(value) || value.length)) ctx.cache?.set(key, value, ttl);
  return value;
}

const getCounties = (ctx) => cached(ctx, ck(ctx, 'counties'), NOMENCLATOR_TTL, async () =>
  (await getAll(ctx, '/api/geolocation/county')).map((c) => ({ id: c.id, name: c.name, code: c.code })));

const getCities = (ctx, countyId) => cached(ctx, ck(ctx, `cities:${countyId}`), NOMENCLATOR_TTL, async () =>
  (await getAll(ctx, '/api/geolocation/city', { county: countyId })).map((c) => ({
    // `village` is the commune the locality belongs to (SDK sample: "2 Mai" → "Limanu").
    id: c.id, name: c.name, postalCode: c.postalCode || '', village: c.village, parent: c.village || '', extraKm: c.extraKM,
  })));

const getServices = (ctx) => cached(ctx, ak(ctx, 'services'), DAY, () => getAll(ctx, '/api/client/services'));
const getPickupPointsRaw = (ctx) => cached(ctx, ak(ctx, 'pickup-points'), 60 * 60, () => getAll(ctx, '/api/client/pickup-points'));

/** Recipient county + city ids as Sameday knows them, or ProcessingError ADDRESS_*. */
export async function resolveLocality(ctx, recipient) {
  const counties = await getCounties(ctx);
  const county = matchCounty(recipient, counties);
  if (!county) throw countyError({ provider: PROVIDER, providerName: NAME, county: recipient.county, countyCode: recipient.countyCode });
  const q = { city: recipient.city, zip: recipient.zip, sector: recipient.sector, county: recipient.county, countyCode: recipient.countyCode };
  const result = matchLocality(q, await getCities(ctx, county.id), { fuzzy: true });
  if (result.match) return { county, city: result.match, via: result.via };

  // Bucharest ↔ Ilfov mix-ups: accept the neighbouring county only on an exact name match.
  const bucharest = isBucharest(recipient.county, recipient.countyCode);
  const ilfov = String(recipient.countyCode || '').toUpperCase() === 'IF' || normalizeText(recipient.county) === 'ilfov';
  if ((bucharest || ilfov) && !result.ambiguous) {
    const otherCode = bucharest ? 'IF' : 'B';
    const other = matchCounty({ county: bucharest ? 'Ilfov' : 'Bucuresti', countyCode: otherCode }, counties);
    if (other) {
      const r2 = matchLocality({ ...q, county: other.name, countyCode: otherCode }, await getCities(ctx, other.id));
      if (r2.match && /^name/.test(r2.via)) {
        ctx.log?.(m('log.neighbourCounty', { provider: NAME }), { city: recipient.city, from: recipient.county, to: other.name });
        return { county: other, city: r2.match, via: `${r2.via}+county` };
      }
    }
  }
  throw localityError({ provider: PROVIDER, providerName: NAME, city: recipient.city, county: county.name || recipient.county, result });
}

// ---------------------------------------------------------------------------------------------
// Errors

function rejected(code, key, params, field, details, retryable = false) {
  return new ProcessingError({ code, key: `sameday.errors.${key}`, params, retryable, provider: PROVIDER, field, details });
}

/** Map a Sameday 4xx body (Symfony form errors: errors.children.awbRecipient.children.phoneNumber.errors[]) to a clear error. */
export function mapAwbError(body, shipment, status) {
  const msgs = collectMessages(body).filter((x) => !/^validation failed$/i.test(x.message));
  const fieldMsg = msgs.find((x) => x.path) || msgs[0];
  const path = (fieldMsg?.path || '').toLowerCase();
  const all = normalizeText(msgs.map((x) => `${x.path} ${x.message}`).join(' | '));
  const said = saidBy(NAME, fieldMsg?.message);
  const r = shipment?.recipient || {};
  const has = (re) => re.test(path) || re.test(all);

  if (has(/lockerlastmile|locker|easybox|oohlastmile/)) return rejected('LOCKER_INVALID', 'locker', { said }, 'lockerId', body);
  if (has(/phonenumber|phone|telefon/)) return rejected('ADDRESS_PHONE_INVALID', 'phone', { phone: r.phone || '', said }, 'shippingAddress.phone', body);
  if (has(/awbrecipient\.(city|citystring)|\bcity\b|localitat|oras/)) {
    return rejected('ADDRESS_CITY_NOT_FOUND', 'city', { city: r.city || '', county: r.county || '-', said }, 'shippingAddress.city', body);
  }
  if (has(/awbrecipient\.(county|countystring)|county|judet/)) {
    return rejected('ADDRESS_COUNTY_NOT_FOUND', 'county', { county: r.county || '', said }, 'shippingAddress.province', body);
  }
  if (has(/postalcode|cod postal/)) return rejected('ADDRESS_ZIP_INVALID', 'zip', { zip: r.zip || '', said }, 'shippingAddress.zip', body);
  if (has(/email/)) return rejected('ADDRESS_EMAIL_INVALID', 'email', { email: r.email || '', said }, 'email', body);
  if (has(/awbrecipient\.address|adresa|address/)) return rejected('ADDRESS_STREET_INVALID', 'street', { said }, 'shippingAddress.address1', body);
  if (has(/awbrecipient\.name|recipient name/)) return rejected('ADDRESS_NAME_INVALID', 'name', { said }, 'shippingAddress.name', body);
  if (has(/weight|greutat/)) return rejected('SHIPMENT_WEIGHT_INVALID', 'weight', { weight: shipment?.weightKg ?? '?', said }, 'weightKg', body);
  if (has(/pickuppoint|contactperson|punct de ridicare/)) return rejected('CONFIG_PICKUP_POINT_INVALID', 'pickupPoint', { said }, 'settings.pickupPointId', body);
  if (has(/servicetax|opcg/)) return rejected('OPEN_PACKAGE_UNAVAILABLE', 'openPackage', { said }, 'openPackage', body);
  if (has(/service|serviciu/)) return rejected('CONFIG_SERVICE_INVALID', 'service', { said }, 'settings.service', body);
  if (has(/cashondelivery|ramburs/)) return rejected('COD_INVALID', 'cod', { said }, 'cod', body);
  if (has(/insuredvalue|asigur/)) return rejected('DECLARED_VALUE_INVALID', 'declaredValue', { said }, 'declaredValue', body);
  const first = shortText(msgs[0]?.message);
  return first
    ? rejected('PROVIDER_REJECTED', 'rejected', { text: first }, undefined, body)
    : rejected('PROVIDER_REJECTED', 'rejectedStatus', { status: status ?? '?' }, undefined, body);
}

// ---------------------------------------------------------------------------------------------
// Payload helpers

async function resolvePickupPoint(ctx) {
  const points = await getPickupPointsRaw(ctx);
  const wanted = String(ctx.settings?.pickupPointId || '').trim();
  let point = wanted ? points.find((p) => String(p.id) === wanted) : points.find((p) => p.defaultPickupPoint) || (points.length === 1 ? points[0] : null);
  if (wanted && !point) {
    // Unknown id: still send it (maybe the list is stale), Sameday will validate it.
    point = { id: Number(wanted) || wanted };
  }
  if (!point) {
    throw rejected('CONFIG_PICKUP_POINT_MISSING', points.length ? 'pickupPointMissing' : 'pickupPointMissingNone',
      { count: points.length, points: points.slice(0, 3).map((p) => `${p.alias || p.address} – ID ${p.id}`).join('; ') },
      'settings.pickupPointId');
  }
  const contacts = Array.isArray(point.pickupPointContactPerson) ? point.pickupPointContactPerson : [];
  const contact = contacts.find((c) => c.defaultContactPerson) || contacts[0];
  return { pickupPointId: point.id, contactPersonId: contact?.id };
}

async function resolveService(ctx, shipment) {
  const wanted = String(shipment.service || (shipment.lockerId ? 'LN' : ctx.settings?.service || '24')).trim();
  const services = await getServices(ctx);
  const byCode = services.find((s) => String(s.serviceCode || '').toUpperCase() === wanted.toUpperCase());
  const service = byCode || services.find((s) => String(s.id) === wanted);
  if (!service) {
    throw rejected('CONFIG_SERVICE_INVALID', services.length ? 'serviceInactive' : 'serviceInactiveNone',
      { service: SERVICE_CODES.includes(wanted) ? m(`sameday.services.${wanted}`) : wanted, services: services.slice(0, 6).map((x) => `${x.name} (${x.serviceCode})`).join(', ') },
      'settings.service', { wanted, services: services.map((x) => ({ id: x.id, code: x.serviceCode, name: x.name })) });
  }
  return service;
}

async function getLocker(ctx, lockerId) {
  const key = ak(ctx, `locker:${lockerId}`);
  return cached(ctx, key, DAY, async () => {
    const body = await api(ctx, 'GET', '/api/client/lockers', { query: { lockersList: lockerId, page: 1, countPerPage: 10 } });
    const list = Array.isArray(body?.data) ? body.data : [];
    return list.find((l) => String(l.lockerId) === String(lockerId)) || null;
  });
}

export function buildAwbForm(ctx, shipment, { pickupPointId, contactPersonId, service, place, locker }) {
  const r = shipment.recipient;
  const n = Math.max(1, Math.round(Number(shipment.parcels) || 1));
  const total = Math.max(0.1, Number(shipment.weightKg) || 1);
  // Per-parcel weights that add up exactly to the total (Sameday's SDK sends packageWeight = Σ parcels).
  const per = Math.floor((total / n) * 100) / 100;
  const first = Math.round((total - per * (n - 1)) * 100) / 100;
  const dims = shipment.dimensionsCm || {};
  const openPackage = Boolean(shipment.openPackage ?? ctx.settings?.openPackage ?? false) && !shipment.lockerId;
  const company = (r.company || '').trim();

  const awbRecipient = {
    name: (r.contactPerson || r.name || '').trim(),
    phoneNumber: normalizePhoneRO(r.phone),
    personType: company ? 1 : 0, // 0 = persoană fizică, 1 = companie
    email: r.email || undefined,
  };
  if (company) awbRecipient.companyName = company;
  if (locker) {
    // easybox: the AWB address is the locker's (as the official plugin does).
    awbRecipient.cityString = locker.city;
    awbRecipient.countyString = locker.county;
    awbRecipient.address = locker.address;
    awbRecipient.postalCode = locker.postalCode || undefined;
  } else {
    awbRecipient.city = place.city.id;
    awbRecipient.county = place.county.id;
    awbRecipient.address = String(r.street || '').slice(0, 250);
    awbRecipient.postalCode = r.zip || place.city.postalCode || undefined;
  }

  const form = {
    pickupPoint: pickupPointId,
    contactPerson: contactPersonId,
    packageType: 0, // 0 = colet, 1 = plic, 2 = colet mare
    packageNumber: n,
    packageWeight: total,
    service: service.id,
    awbPayment: 1, // expeditorul plătește transportul
    cashOnDelivery: money(shipment.cod),
    cashOnDeliveryReturns: undefined,
    insuredValue: money(shipment.declaredValue),
    thirdPartyPickup: 0,
    serviceTaxes: openPackage ? ['OPCG'] : undefined, // codes, as the official plugin sends them
    awbRecipient,
    parcels: Array.from({ length: n }, (_, i) => ({ weight: i === 0 ? first : per, width: dims.width, length: dims.length, height: dims.height })),
    observation: [shipment.contents, shipment.notes].filter(Boolean).join(' | ').slice(0, 250) || undefined,
    clientInternalReference: shipment.reference || undefined,
    lockerLastMile: shipment.lockerId ? Number(shipment.lockerId) || shipment.lockerId : undefined,
    currency: shipment.currency || 'RON',
  };
  return form;
}

function hasOpenPackageTax(service) {
  const taxes = service?.serviceOptionalTaxes;
  if (!Array.isArray(taxes)) return true; // unknown → let Sameday decide
  return taxes.some((t) => String(t.taxCode || t.code || '').toUpperCase() === 'OPCG');
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let i = 0;
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  }));
  return out;
}

// ---------------------------------------------------------------------------------------------

const adapter = {
  id: PROVIDER,
  name: NAME,
  // VERIFY: sameday.ro answers non-browser clients with a Cloudflare challenge (403), so the page could not be checked.
  trackingUrl: (awb) => `https://sameday.ro/#awb=${encodeURIComponent(awb)}`,

  // Labels and help: sameday.fields.<key> in the catalogs (src/i18n).
  credentialFields: [
    { key: 'username', type: 'text', required: true },
    { key: 'password', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'sandbox', type: 'checkbox', default: false },
    { key: 'pickupPointId', type: 'text' },
    { key: 'service', type: 'select', default: '24', options: SERVICE_CODES.filter((c) => c !== 'LN' && c !== 'PP').map((value) => ({ value })) },
    { key: 'openPackage', type: 'checkbox', default: false },
    { key: 'labelFormat', type: 'select', default: 'A6', options: [{ value: 'A6' }, { value: 'A4' }] },
  ],

  async testConnection(ctx) {
    await authenticate(ctx, { force: true });
    ctx.cache?.set(ak(ctx, 'pickup-points'), null, 1);
    const points = await adapter.listPickupPoints(ctx);
    const chosen = String(ctx.settings?.pickupPointId || '').trim();
    const extra = chosen && !points.some((p) => p.id === chosen) ? m('sameday.test.pointMissing', { id: chosen }) : '';
    const message = m('sameday.test.connected', { count: points.length, sandbox: env(ctx) === 'demo' ? m('sameday.test.sandbox') : '', extra });
    return { ok: true, message, info: { pickupPoints: points, environment: env(ctx) } };
  },

  async listPickupPoints(ctx) {
    const points = await getPickupPointsRaw(ctx);
    return points.map((p) => ({
      id: String(p.id),
      name: p.alias || t(ctx.locale, 'cargus.pointName', { id: p.id }),
      address: [p.address, p.city?.name, p.county?.name].filter(Boolean).join(', '),
      default: Boolean(p.defaultPickupPoint),
    }));
  },

  async listServices(ctx) {
    const services = await getServices(ctx);
    return services.map((s) => ({ id: String(s.id), name: `${s.name}${s.serviceCode ? ` (${s.serviceCode})` : ''}`, code: s.serviceCode }));
  },

  async listLockers(ctx, { county, city } = {}) {
    const lockers = await cached(ctx, ak(ctx, 'lockers'), DAY, async () =>
      (await getAll(ctx, '/api/client/lockers')).map((l) => ({
        id: String(l.lockerId),
        name: l.name,
        address: [l.address, l.city, l.county].filter(Boolean).join(', '),
        city: l.city,
        county: l.county,
        postalCode: l.postalCode,
      })));
    const ckey = county && compactKey(county);
    const tkey = city && compactKey(city);
    return lockers.filter((l) => (!ckey || compactKey(l.county) === ckey || (isBucharest(county) && isBucharest(l.county)))
      && (!tkey || compactKey(l.city) === tkey));
  },

  async createShipment(ctx, shipment) {
    const r = shipment.recipient || {};
    const { pickupPointId, contactPersonId } = await resolvePickupPoint(ctx);
    const service = await resolveService(ctx, shipment);
    let locker = null;
    let place = null;
    if (shipment.lockerId) {
      locker = await getLocker(ctx, shipment.lockerId);
      if (!locker) {
        throw rejected('LOCKER_INVALID', 'lockerGone', { locker: shipment.lockerId }, 'lockerId');
      }
    } else {
      place = await resolveLocality(ctx, r);
      if (Boolean(shipment.openPackage ?? ctx.settings?.openPackage) && !hasOpenPackageTax(service)) {
        throw rejected('OPEN_PACKAGE_UNAVAILABLE', 'openPackageService', { service: service.name }, 'openPackage');
      }
    }
    const form = buildAwbForm(ctx, shipment, { pickupPointId, contactPersonId, service, place, locker });
    const body = await api(ctx, 'POST', '/api/awb', {
      form,
      mapError: (status, b) => (status >= 400 && status < 500 && status !== 429 ? mapAwbError(b, shipment, status) : undefined),
    });
    const awb = body?.awbNumber;
    if (!awb) throw mapAwbError(body, shipment, 200);
    ctx.log?.(m('log.awbCreated', { provider: NAME, awb }), { awb, reference: shipment.reference, cityId: place?.city?.id, via: place?.via });
    const price = Number(body.awbCost);
    return { awb: String(awb), price: Number.isFinite(price) ? price : undefined, raw: body };
  },

  async getLabel(ctx, awb, { format } = {}) {
    const f = (format || ctx.settings?.labelFormat || 'A6') === 'A4' ? 'A4' : 'A6';
    const pdf = await api(ctx, 'GET', `/api/awb/download/${encodeURIComponent(awb)}/${f}`, {
      responseType: 'buffer',
      mapError: (status, b) => (status === 404
        ? rejected('LABEL_UNAVAILABLE', 'labelNotFound', { awb }, undefined, b?.toString?.('utf8')?.slice(0, 500))
        : undefined),
    });
    if (!Buffer.isBuffer(pdf) || pdf.subarray(0, 4).toString('latin1') !== '%PDF') {
      throw rejected('LABEL_UNAVAILABLE', 'label', { awb }, undefined,
        Buffer.isBuffer(pdf) ? pdf.toString('utf8').slice(0, 500) : pdf, true);
    }
    return pdf;
  },

  async cancelShipment(ctx, awb) {
    try {
      await api(ctx, 'DELETE', `/api/awb/${encodeURIComponent(awb)}`, {
        mapError: (status, b) => {
          if (status === 404) return rejected('AWB_NOT_FOUND', 'notFound', { awb }, undefined, b);
          if (status === 400 || status === 409 || status === 422) {
            return rejected('CANCEL_REFUSED', 'cancel', { awb, said: saidBy(NAME, collectMessages(b)[0]?.message) }, undefined, b);
          }
          return undefined;
        },
      });
    } catch (err) {
      if (err?.code === 'AWB_NOT_FOUND') { ctx.log?.(m('log.cancelNotFound', { provider: NAME }), { awb }); return; }
      throw err;
    }
  },

  async track(ctx, awbs) {
    const list = [...new Set((awbs || []).map(String).filter(Boolean))];
    const results = await mapLimit(list, 5, async (awb) => {
      let body;
      try {
        body = await api(ctx, 'GET', `/api/client/awb/${encodeURIComponent(awb)}/status`, {
          mapError: (status, b) => (status === 404 ? rejected('AWB_NOT_FOUND', 'notFound', { awb }, undefined, b) : undefined),
        });
      } catch (err) {
        if (err?.code === 'AWB_NOT_FOUND') return null;
        throw err;
      }
      const st = body?.expeditionStatus || {};
      const summary = body?.expeditionSummary || {};
      const status = mapSamedayStatus(body);
      let statusText = st.statusLabel || st.status || st.statusState || 'AWB emis';
      let at = courierDateToIso(st.statusDate); // "2019-02-26T09:37:28+0200" (SDK sample)
      // The SDK's own sample (tests/Responses/SamedayGetAwbStatusHistoryResponseTest.php) has
      // expeditionSummary.delivered = true + deliveredAt while expeditionStatus still says "AWB Emis":
      // the summary decides the status, so text and date must come from it too, not "Document de transport emis".
      const summaryDelivered = summary.delivered === true || summary.delivered === 1;
      if (status === TrackingStatus.DELIVERED && summaryDelivered && classifyStatusText(statusText) !== TrackingStatus.DELIVERED) {
        statusText = 'Livrat';
        at = courierDateToIso(summary.deliveredAt) || at;
      }
      return { awb, status, statusText, at, codCollected: status === TrackingStatus.DELIVERED };
    });
    return results.filter(Boolean);
  },
};

export default adapter;
