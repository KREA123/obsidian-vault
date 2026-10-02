import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus as S } from './contract.js';
import { cityVariants, compactKey, localityKeys, matchLocality, localityError } from './locality.js';
import {
  NOMENCLATOR_TTL, cached, cacheGet, cacheSet, chunk, isPdf, splitStreet, toIntlPhone, latestMeaningful,
  accountKey, money,
} from './util.js';
import { m, t } from '../i18n/index.js';

// GLS Romania — MyGLS API, REST/JSON (https://api.mygls.ro/ParcelService.svc/json/<Method>).
// Source: "MyGLS API for system integration" ver. 25.12.11 (api.test.mygls.ro/docs/MyGLS_API.pdf)
// and webapix/mygls-sdk (PHP) for the exact JSON shapes.
//
// No session: every body carries Username + Password, where Password is the SHA-512 digest of the
// password as a JSON array of byte values (0-255). The doc's change log says ClientNumberList must
// not be used, so it is omitted.
//
// Live check 2026-10 (api.mygls.ro and api.test.mygls.ro behave the same; WSDL ?singleWsdl is public):
//  - bad credentials are NOT an HTTP error: HTTP 200 with the method's error list, e.g.
//    {"GetParcelStatusErrors":[{"ErrorCode":-1,"ErrorDescription":"Unauthorized.",...}],"ParcelNumber":0,
//     "ParcelStatusList":[],...} (same in GetParcelListErrors, GetPrintedLabelsErrorList,
//    DeleteLabelsErrorList, PrintLabelsErrorList);
//  - after ~5 failed logins the user is LOCKED: ErrorCode -1 "Too many failed login attempts. Your
//    account has been locked until 11:13. Please try logging in later." — so a wrong password must
//    never be retried in a loop (we stop at the first auth error and remember it for a while);
//  - GetParcelListStatuses with bad credentials answers {"GetParcelListStatusesErrors":[],"ParcelList":[]}
//    (silent!), so an empty batch is double-checked with GetParcelStatuses;
//  - MasterDataService/GetLocations drops the connection (prod) / 502 (test) — the locality
//    nomenclator is optional here; unknown methods → 404 HTML page.
//  - WSDL: INSParameter is ServiceParameterDecimal {Value: decimal}, PSDParameter is
//    {StringValue, IntegerValue}, StatusCode is a string, ParcelProperties.Weight decimal (kg).
//
// Parcels are addressed two ways: ParcelId (database id, needed by GetPrintedLabels / DeleteLabels)
// and ParcelNumber (the number printed on the label = our AWB, used for tracking). We remember the
// ParcelId(s) per AWB in ctx.cache and fall back to GetParcelList when the cache was lost.

const PROVIDER = 'GLS';
const ID = 'gls';
const WEBSHOP_ENGINE = 'Shopify'; // free text; the live WSDL has WebshopEngine on every request (APIRequestBase)
const PARCEL_MAP_TTL = 120 * 24 * 60 * 60;

// GLS StatusCode (Appendix G) → normalized status. `null` = informational, ignored when picking the
// current status (e.g. an e-mail notification after "out for delivery" must not change it).
//   51, 52, 83, 84, 85 date colet înregistrate, neridicat ............... created
//   1 predat la GLS ...................................................... picked_up
//   2, 3, 6, 7, 8, 9, 13, 21, 22, 24, 25, 26, 27, 29, 30, 37, 41, 46, 47, 53, 80, 86,
//   60-76 (vamă), 401-404, 420 (probleme locker → redirecționat) ......... in_transit
//   4, 32 în livrare azi; 54, 55, 56, 97 depus în ParcelShop/locker, așteaptă ridicarea ... out_for_delivery
//   5, 58, 59, 92 livrat (la destinatar, vecin, ridicat din ParcelShop) .. delivered
//   11, 12, 14, 15, 16, 18, 19, 20, 33, 36, 38, 39, 88, 89 nelivrat (absent, închis, adresă...) ... failed_attempt
//   17, 34, 35, 68 refuzat; 57 termen de păstrare depășit în ParcelShop .. returning
//   23, 40 returnat la expeditor ......................................... returned
//   87, 90, 91 ridicare anulată .......................................... cancelled
//   28, 31, 42, 43, 44 distrus / pierdut / exclus ........................ unknown
//   10, 93, 99 (scanare de control, semnătură confirmată, notificare e-mail) informational
const GLS_STATUS = {};
const put = (codes, status) => codes.forEach((c) => { GLS_STATUS[c] = status; });
put([51, 52, 83, 84, 85], S.CREATED);
put([1], S.PICKED_UP);
put([2, 3, 6, 7, 8, 9, 13, 21, 22, 24, 25, 26, 27, 29, 30, 37, 41, 46, 47, 53, 80, 86, 401, 402, 403, 404, 420], S.IN_TRANSIT);
for (let c = 60; c <= 76; c++) GLS_STATUS[c] = S.IN_TRANSIT;
put([4, 32, 54, 55, 56, 97], S.OUT_FOR_DELIVERY); // VERIFY: 54/55 = deposited in locker/shop (not yet collected)
put([5, 58, 59, 92], S.DELIVERED);
put([11, 12, 14, 15, 16, 18, 19, 20, 33, 36, 38, 39, 88, 89], S.FAILED_ATTEMPT);
put([17, 34, 35, 57, 68], S.RETURNING);
put([23, 40], S.RETURNED);
put([87, 90, 91], S.CANCELLED);
put([28, 31, 42, 43, 44], S.UNKNOWN);
put([10, 93, 99], null);

export function mapGlsStatus(code) {
  const n = Number(code);
  if (Object.hasOwn(GLS_STATUS, n)) return GLS_STATUS[n];
  return S.UNKNOWN;
}

const AUTH_FAIL_TTL = 15 * 60; // remember a rejected login: each retry counts towards GLS's lockout

// MyGLS ErrorCode (Appendix A) → [code, field]; text: gls.errors.code<N> in the catalogs.
const GLS_ERRORS = {
  8: ['COD_INVALID', 'cod'],
  14: null, // user not exists → auth
  15: null, // not authorized for parcel → auth
  23: ['ADDRESS_STREET_INVALID', 'shippingAddress.address1'],
  27: null, // not authorized for client → auth
  28: ['PARCELS_INVALID', 'parcels'],
  29: ['PARCELS_INVALID', 'parcels'],
  31: ['PROVIDER_RATE_LIMIT', undefined],
  32: ['REFERENCE_MISSING', undefined],
  33: ['CONTENT_MISSING', 'contents'],
  34: ['SETTINGS_INVALID', 'settings.printerType'],
  48: ['COD_INVALID', 'currency'],
};

export function glsPasswordBytes(password) {
  return [...createHash('sha512').update(String(password ?? ''), 'utf8').digest()];
}

/** "/Date(1598911199000+0200)/" → ISO string. */
export function parseGlsDate(v) {
  if (!v) return undefined;
  const m = String(v).match(/\/Date\((-?\d+)/);
  if (m) return new Date(Number(m[1])).toISOString();
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}

export const glsDate = (d = new Date()) => `/Date(${d.getTime()})/`;

function baseUrl(ctx) {
  const test = ctx.settings?.sandbox === true || ctx.settings?.sandbox === 'true';
  return test ? 'https://api.test.mygls.ro' : 'https://api.mygls.ro';
}

function clientNumber(ctx) {
  const n = Number(ctx.settings?.clientNumber ?? ctx.credentials?.clientNumber);
  if (!n) {
    throw new ProcessingError({
      code: 'SETTINGS_MISSING',
      key: 'gls.errors.clientNumberMissing',
      provider: ID, field: 'settings.clientNumber',
    });
  }
  return n;
}

const account = (ctx) => accountKey(baseUrl(ctx), ctx.credentials?.username, ctx.credentials?.password);
const authFailKey = (ctx) => `gls:authfail:${account(ctx)}`;

async function call(ctx, service, method, body, { timeoutMs = 60_000 } = {}) {
  const { username, password } = ctx.credentials || {};
  if (!username || !password) throw authError(PROVIDER, 'missing credentials');
  const failed = await cacheGet(ctx, authFailKey(ctx));
  if (failed) throw rememberedAuthError(failed);
  const url = `${baseUrl(ctx)}/${service}.svc/json/${method}`;
  const res = await ctx.http(PROVIDER, url, {
    method: 'POST',
    json: { Username: username, Password: glsPasswordBytes(password), ...body },
    timeoutMs,
  });
  return res.body || {};
}

/** "Too many failed login attempts... locked until 11:13" → "11:13". */
const lockedUntil = (text) => String(text || '').match(/locked until ([0-9:. apmAPM]+?)(?:\.|\s*Please|$)/)?.[1]?.trim();

/** MyGLS auth failure: ErrorCode 14/15/27 (Appendix A) or -1 "Unauthorized." / lockout (live). */
function glsAuthError(first, raw) {
  const text = String(first?.ErrorDescription || '');
  const until = lockedUntil(text);
  if (/locked|too many/i.test(text)) {
    return new ProcessingError({ code: 'AUTH_FAILED', key: until ? 'gls.errors.lockedUntil' : 'gls.errors.locked', params: { until }, provider: ID, details: raw });
  }
  return new ProcessingError({ ...authError(PROVIDER, raw).toJSON(), provider: ID });
}

/** The remembered login failure ({ key, params } or, from older versions, { message, hint }). */
function rememberedAuthError(failed) {
  if (failed.key) return new ProcessingError({ code: 'AUTH_FAILED', key: failed.key, params: failed.params, provider: ID, details: failed.details });
  if (failed.message) return new ProcessingError({ code: 'AUTH_FAILED', message: failed.message, hint: failed.hint, provider: ID, details: failed.details });
  return new ProcessingError({ ...authError(PROVIDER, failed.details).toJSON(), provider: ID });
}

const isAuthErrorInfo = (e) => [14, 15, 27].includes(Number(e?.ErrorCode))
  || (Number(e?.ErrorCode) === -1 && /unauthori[sz]ed|login|locked|password|credential|user/i.test(String(e?.ErrorDescription || '')));

/** Throws a merchant-readable error for a MyGLS ErrorInfo list (no-op when empty). */
function throwGlsErrors(list, raw, ctx) {
  if (!Array.isArray(list) || !list.length) return;
  const first = list[0] || {};
  const code = Number(first.ErrorCode);
  if (isAuthErrorInfo(first)) {
    const e = glsAuthError(first, raw);
    // Every further call with the same password counts as another failed login → lockout. Stop here.
    // (Only login failures: 15/27 are "not authorized for this parcel / client", not a bad password.)
    if (ctx && [-1, 14].includes(code)) cacheSet(ctx, authFailKey(ctx), { key: e.key, params: e.params, details: first }, AUTH_FAIL_TTL);
    throw e;
  }
  if (code === 1000 || code === 1001) {
    throw new ProcessingError({ code: 'PROVIDER_DOWN', key: 'gls.errors.internal', retryable: true, provider: ID, details: raw });
  }
  const known = GLS_ERRORS[code];
  if (known) {
    const [c, field] = known;
    throw new ProcessingError({ code: c, key: `gls.errors.code${code}`, field, retryable: code === 31, provider: ID, details: raw });
  }
  const text = list.map((e) => e.ErrorDescription).filter(Boolean).join('; ');
  const byField = [
    [/zip|postal|irányítószám/i, 'ADDRESS_ZIP_INVALID', 'shippingAddress.zip'],
    [/city|town/i, 'ADDRESS_CITY_NOT_FOUND', 'shippingAddress.city'],
    [/street|house/i, 'ADDRESS_STREET_INVALID', 'shippingAddress.address1'],
    [/phone/i, 'ADDRESS_PHONE_INVALID', 'shippingAddress.phone'],
    [/email/i, 'ADDRESS_EMAIL_INVALID', 'email'],
    [/psd|parcel ?shop|delivery ?point/i, 'LOCKER_INVALID', 'lockerId'],
    [/pickup ?address|sender/i, 'SETTINGS_INVALID', 'settings.senderStreet'],
  ];
  for (const [re, c, field] of byField) {
    if (re.test(text)) throw new ProcessingError({ code: c, key: `gls.errors.field.${c}`, field, provider: ID, details: raw });
  }
  throw new ProcessingError({ code: 'COURIER_REJECTED', key: 'gls.errors.rejected', provider: ID, details: raw });
}

function toBuffer(labels) {
  if (!labels) return undefined;
  if (Array.isArray(labels)) return Buffer.from(labels);
  if (typeof labels === 'string') return Buffer.from(labels, 'base64');
  return undefined;
}

// ---------------------------------------------------------------- nomenclator (ZIP ↔ locality)

// MasterDataService/GetLocations (added to the doc 2026-03, present in the live WSDL): GZIP-compressed JSON
// list of { Name, ZipCode, ... } per country, returned as Data (byte array). Live check with invalid
// credentials: production drops the connection, test answers 502 — VERIFY with a real account. When the
// call fails we simply skip the local check (remembered for 6 h) and let PrintLabels validate.
const LOCATIONS_OFF_KEY = 'gls:locations:RO:unavailable';

async function loadLocations(ctx) {
  return cached(ctx, 'gls:locations:RO', NOMENCLATOR_TTL, async () => {
    const body = await call(ctx, 'MasterDataService', 'GetLocations', { CountryIsoCode: 'RO' }, { timeoutMs: 20_000 });
    if (Array.isArray(body.GetLocationsErrors)) throwGlsErrors(body.GetLocationsErrors, { ...body, Data: undefined }, ctx);
    if (body.ErrorCode) throw new ProcessingError({ code: 'PROVIDER_REJECTED', key: 'gls.errors.locations', provider: ID, details: body });
    const raw = toBuffer(body.Data);
    if (!raw?.length) throw new ProcessingError({ code: 'PROVIDER_REJECTED', key: 'gls.errors.locationsEmpty', provider: ID, details: { ...body, Data: undefined } });
    const list = JSON.parse(gunzipSync(raw).toString('utf8'));
    return list.map((l) => [l.Name, String(l.ZipCode)]);
  });
}

/**
 * GLS routes by ZIP, so the ZIP is mandatory. The nomenclator has no county, so it is used
 * conservatively (same village names exist in many counties):
 *  - missing ZIP: derive it only when the locality name has exactly one ZIP in the whole country,
 *    otherwise ADDRESS_ZIP_MISSING (with the closest names when the city is unknown too);
 *  - ZIP and city both unknown to GLS: ADDRESS_CITY_NOT_FOUND with "Ai vrut: ..." suggestions;
 *  - anything else goes through; PrintLabels validates the ZIP itself and we map its error.
 * Returns the ZIP to send and the city spelling (GLS's own name when the ZIP confirms it).
 */
export async function resolveGlsAddress(ctx, recipient) {
  const zipIn = String(recipient.zip ?? '').replace(/\s+/g, '');
  if (zipIn && !/^\d{6}$/.test(zipIn)) throw zipInvalid(zipIn);

  let rows;
  if (!(await cacheGet(ctx, LOCATIONS_OFF_KEY))) {
    try {
      rows = await loadLocations(ctx);
    } catch (err) {
      if (err?.code === 'AUTH_FAILED') throw err;
      // Remember the failure for a while so every shipment does not wait on it again.
      await cacheSet(ctx, LOCATIONS_OFF_KEY, true, 6 * 60 * 60);
      ctx.log?.(m('log.localitiesUnavailableSkip', { provider: PROVIDER }), { err: err?.message });
    }
  }
  if (!rows) {
    if (!zipIn) throw zipMissing();
    return { zip: zipIn, city: displayCity(recipient) };
  }

  const wanted = new Set(cityVariants(recipient).map(compactKey));
  const isCity = (r) => localityKeys(r[0]).some((k) => wanted.has(k));
  const cityRows = rows.filter(isCity);
  // The nomenclator has no county: suggestions only, never a match we would act on.
  const suggest = () => matchLocality({ city: recipient.city }, rows.map((r) => ({ name: r[0], postalCode: r[1] })));

  if (!zipIn) {
    const zips = [...new Set(cityRows.map((r) => r[1]))];
    if (zips.length === 1) return { zip: zips[0], city: cityRows[0][0] };
    const suggestions = cityRows.length ? [] : (suggest().suggestions || []).map((c) => c.name);
    throw zipMissing(zips, suggestions);
  }

  const zipRows = rows.filter((r) => r[1] === zipIn);
  const confirmed = zipRows.find(isCity);
  if (confirmed) return { zip: zipIn, city: confirmed[0] };
  if (!zipRows.length && !cityRows.length) {
    // Neither the ZIP nor the city exist for GLS: almost certainly a typo in the city.
    const result = suggest();
    if (!result.match) throw localityError({ provider: ID, providerName: PROVIDER, city: recipient.city, result: { notFound: true, suggestions: result.suggestions || [] } });
  }
  if (zipRows.length && cityRows.length) {
    ctx.log?.(m('log.zipOtherCity', { provider: PROVIDER }), { city: recipient.city, zip: zipIn, glsCityForZip: zipRows[0][0] });
  }
  return { zip: zipIn, city: displayCity(recipient) };
}

function displayCity(r) {
  return /^sector(ul)?\s*\d$/i.test(String(r.city || '').trim()) ? 'Bucuresti' : r.city;
}

function zipMissing(zips = [], suggestions = []) {
  let hintKey = 'gls.errors.zipMissing.hint';
  if (zips.length > 1) hintKey = 'gls.errors.zipMissing.hintZips';
  else if (suggestions.length) hintKey = 'gls.errors.zipMissing.hintSuggestions';
  return new ProcessingError({
    code: 'ADDRESS_ZIP_MISSING',
    key: 'gls.errors.zipMissing',
    hintKey,
    params: { zips: zips.slice(0, 3).join(', '), suggestions: suggestions.join(', ') },
    field: 'shippingAddress.zip', provider: ID,
  });
}

function zipInvalid(zip) {
  return new ProcessingError({ code: 'ADDRESS_ZIP_INVALID', key: 'gls.errors.zipInvalid', params: { zip }, field: 'shippingAddress.zip', provider: ID });
}

// ---------------------------------------------------------------- payload

function pickupAddress(settings) {
  const missing = ['senderName', 'senderStreet', 'senderCity', 'senderZip'].filter((k) => !settings[k]);
  if (missing.length) {
    throw new ProcessingError({
      code: 'SETTINGS_MISSING',
      key: 'gls.errors.senderIncomplete',
      provider: ID, field: `settings.${missing[0]}`,
    });
  }
  const st = splitStreet(settings.senderStreet);
  return {
    Name: settings.senderName,
    Street: st.street,
    HouseNumber: settings.senderHouseNumber || st.number || '',
    HouseNumberInfo: st.info || '',
    City: settings.senderCity,
    ZipCode: String(settings.senderZip),
    CountryIsoCode: 'RO',
    ContactName: settings.senderContactName || settings.senderName,
    ContactPhone: settings.senderPhone ? toIntlPhone(settings.senderPhone) : '',
    ContactEmail: settings.senderEmail || '',
  };
}

export function buildParcel(shipment, settings, { clientNumber: cn, zip, city, pickupDate = new Date() }) {
  const r = shipment.recipient;
  const st = splitStreet(r.street);
  const phone = toIntlPhone(r.phone);
  const services = [];

  if (shipment.lockerId) {
    if (!r.email) {
      throw new ProcessingError({
        code: 'ADDRESS_EMAIL_MISSING',
        key: 'gls.errors.emailMissing',
        field: 'email', provider: ID,
      });
    }
    services.push({ Code: 'PSD', PSDParameter: { StringValue: String(shipment.lockerId) } });
  }
  const notifyEmail = settings.notifyEmail !== false && settings.notifyEmail !== 'false';
  if (notifyEmail && r.email) services.push({ Code: 'FDS', FDSParameter: { Value: r.email } });
  const notifySms = settings.notifySms === true || settings.notifySms === 'true';
  if (notifySms && phone) {
    if (notifyEmail && r.email) services.push({ Code: 'FSS', FSSParameter: { Value: phone } }); // FSS needs FDS
    else services.push({ Code: 'SM2', SM2Parameter: { Value: phone } });
  }
  // INSParameter is a WCF decimal: a JSON number, not a string.
  if (money(shipment.declaredValue) > 0) services.push({ Code: 'INS', INSParameter: { Value: money(shipment.declaredValue) } });
  if (shipment.saturday) services.push({ Code: 'SAT' });

  const cod = money(shipment.cod);
  const hasCod = cod > 0;
  const parcel = {
    ClientNumber: cn,
    ClientReference: String(shipment.reference ?? '').slice(0, 40),
    Count: Math.max(1, shipment.parcels || 1),
    CODAmount: cod,
    // COD needs no ServiceList entry: CODAmount > 0 is enough (doc + SDKs). VERIFY with GLS RO contract.
    ...(hasCod ? { CODReference: String(shipment.reference ?? '').slice(0, 40), CODCurrency: shipment.currency || 'RON' } : {}),
    Content: [shipment.contents, shipment.notes].filter(Boolean).join(' / ').slice(0, 100) || String(shipment.reference ?? ''),
    PickupDate: glsDate(pickupDate),
    PickupAddress: pickupAddress(settings),
    DeliveryAddress: {
      Name: (r.company || r.name || '').slice(0, 40),
      Street: st.street,
      HouseNumber: st.number,
      HouseNumberInfo: st.info,
      City: city,
      ZipCode: zip,
      CountryIsoCode: 'RO',
      ContactName: r.contactPerson || r.name,
      ContactPhone: phone,
      ContactEmail: r.email || '',
    },
    ServiceList: services,
  };
  if (shipment.weightKg && (shipment.parcels || 1) === 1) {
    const d = shipment.dimensionsCm;
    parcel.ParcelPropertyList = [{
      Content: shipment.contents || '',
      PackageType: 2, // Box
      ...(d ? { Height: Math.round(d.height), Length: Math.round(d.length), Width: Math.round(d.width) } : {}),
      Weight: shipment.weightKg,
    }];
  }
  return parcel;
}

const PRINTERS = ['A4_2x2', 'A4_4x1', 'Thermo'];
function printerFor(settings, format) {
  if (format === 'A6') return 'Thermo';
  if (format === 'A4') return settings.printerType && settings.printerType !== 'Thermo' ? settings.printerType : 'A4_2x2';
  return PRINTERS.includes(settings.printerType) ? settings.printerType : 'A4_2x2';
}

/** AWB → ParcelId map, per environment + account: test and production parcel numbers can collide. */
export const parcelKey = (ctx, awb) => `gls:parcel:${account(ctx)}:${awb}`;

async function parcelIdsFor(ctx, awb) {
  const hit = await cacheGet(ctx, parcelKey(ctx, awb));
  if (hit?.parcelIds?.length) return hit.parcelIds;
  // Fallback: look the parcel up among the labels printed in the last 30 days.
  const now = Date.now();
  const body = await call(ctx, 'ParcelService', 'GetParcelList', {
    PrintDateFrom: glsDate(new Date(now - 30 * 864e5)),
    PrintDateTo: glsDate(new Date(now + 864e5)),
  });
  throwGlsErrors(body.GetParcelListErrors, body, ctx);
  const want = String(awb);
  const hits = (body.PrintDataInfoList || []).filter((p) => String(p.ParcelNumber) === want || String(p.ParcelNumberWithCheckdigit) === want);
  const ids = hits.map((p) => p.ParcelId).filter(Boolean);
  if (ids.length) await cacheSet(ctx, parcelKey(ctx, awb), { parcelIds: ids }, PARCEL_MAP_TTL);
  return ids;
}

// ---------------------------------------------------------------- adapter

export default {
  id: ID,
  name: PROVIDER,
  trackingUrl: (awb) => `https://gls-group.com/RO/ro/urmarire-colet?match=${encodeURIComponent(awb)}`,

  // Labels and help: gls.fields.<key> in the catalogs (src/i18n).
  credentialFields: [
    { key: 'username', type: 'text', required: true },
    { key: 'password', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'clientNumber', type: 'text', required: true },
    { key: 'senderName', type: 'text', required: true },
    { key: 'senderStreet', type: 'text', required: true },
    { key: 'senderCity', type: 'text', required: true },
    { key: 'senderZip', type: 'text', required: true },
    { key: 'senderContactName', type: 'text' },
    { key: 'senderPhone', type: 'text' },
    { key: 'senderEmail', type: 'text' },
    { key: 'printerType', type: 'select', default: 'A4_2x2', options: [{ value: 'A4_2x2' }, { value: 'A4_4x1' }, { value: 'Thermo' }] },
    { key: 'notifyEmail', type: 'checkbox', default: true },
    { key: 'notifySms', type: 'checkbox', default: false },
    { key: 'sandbox', type: 'checkbox', default: false },
  ],

  async testConnection(ctx) {
    const cn = clientNumber(ctx);
    const now = Date.now();
    const body = await call(ctx, 'ParcelService', 'GetParcelList', {
      PrintDateFrom: glsDate(new Date(now - 864e5)),
      PrintDateTo: glsDate(new Date(now)),
    });
    throwGlsErrors(body.GetParcelListErrors, body, ctx);
    const test = baseUrl(ctx).includes('.test.');
    return {
      ok: true,
      message: m('gls.test.connected', { sandbox: test ? m('gls.test.sandbox') : '', client: cn, count: (body.PrintDataInfoList || []).length }),
    };
  },

  async createShipment(ctx, shipment) {
    const cn = clientNumber(ctx);
    const settings = ctx.settings || {};
    const { zip, city } = await resolveGlsAddress(ctx, shipment.recipient);
    const parcel = buildParcel(shipment, settings, { clientNumber: cn, zip, city });
    const body = await call(ctx, 'ParcelService', 'PrintLabels', {
      WebshopEngine: WEBSHOP_ENGINE,
      ParcelList: [parcel],
      TypeOfPrinter: printerFor(settings),
      PrintPosition: 1,
      ShowPrintDialog: false,
    });
    throwGlsErrors(body.PrintLabelsErrorList, { ...body, Labels: undefined }, ctx);
    const infos = body.PrintLabelsInfoList || [];
    if (!infos.length || !infos[0].ParcelNumber) {
      // Not retryable: the label may exist already and a blind retry would print a second one.
      throw new ProcessingError({ code: 'COURIER_REJECTED', key: 'gls.errors.noParcelNumber', retryable: false, provider: ID, details: { ...body, Labels: undefined } });
    }
    const awb = String(infos[0].ParcelNumber);
    const parcelIds = infos.map((i) => i.ParcelId).filter(Boolean);
    await cacheSet(ctx, parcelKey(ctx, awb), { parcelIds, parcelNumbers: infos.map((i) => String(i.ParcelNumber)) }, PARCEL_MAP_TTL);
    return { awb, raw: { parcelIds, parcelNumbers: infos.map((i) => String(i.ParcelNumber)), zip, city } };
  },

  async getLabel(ctx, awb, { format } = {}) {
    const ids = await parcelIdsFor(ctx, awb);
    if (!ids.length) {
      throw new ProcessingError({ code: 'LABEL_FAILED', key: 'gls.errors.labelNotFound', params: { awb }, provider: ID });
    }
    const body = await call(ctx, 'ParcelService', 'GetPrintedLabels', {
      ParcelIdList: ids.slice(0, 99),
      TypeOfPrinter: printerFor(ctx.settings || {}, format),
      PrintPosition: 1,
      ShowPrintDialog: false,
    });
    throwGlsErrors(body.GetPrintedLabelsErrorList, { ...body, Labels: undefined }, ctx);
    const pdf = toBuffer(body.Labels);
    if (!isPdf(pdf)) {
      throw new ProcessingError({ code: 'LABEL_FAILED', key: 'gls.errors.label', params: { awb }, retryable: true, provider: ID, details: { ...body, Labels: undefined } });
    }
    return pdf;
  },

  async cancelShipment(ctx, awb) {
    const ids = await parcelIdsFor(ctx, awb);
    if (!ids.length) {
      throw new ProcessingError({ code: 'CANCEL_REFUSED', key: 'gls.errors.cancelNotFound', params: { awb }, provider: ID });
    }
    const body = await call(ctx, 'ParcelService', 'DeleteLabels', { ParcelIdList: ids.slice(0, 50) });
    if (Array.isArray(body.DeleteLabelsErrorList) && body.DeleteLabelsErrorList.length) {
      if (isAuthErrorInfo(body.DeleteLabelsErrorList[0])) throwGlsErrors(body.DeleteLabelsErrorList, body, ctx);
      throw new ProcessingError({
        code: 'CANCEL_REFUSED',
        key: 'gls.errors.cancel',
        params: { awb },
        provider: ID, details: body,
      });
    }
  },

  async track(ctx, awbs) {
    // GLS parcel numbers are digits; anything else cannot be a GLS parcel (missing AWBs are omitted).
    const wanted = [...new Set((awbs || []).map((a) => String(a).trim()).filter((a) => /^\d{1,15}$/.test(a)))];
    if (!wanted.length) return [];
    const out = [];
    const single = async (awb) => {
      const body = await call(ctx, 'ParcelService', 'GetParcelStatuses', { ParcelNumber: Number(awb), ReturnPOD: false, LanguageIsoCode: 'RO' });
      const errs = body.GetParcelStatusErrors;
      // Auth errors stop everything (each further call is another failed login → lockout).
      if (Array.isArray(errs) && errs.length) {
        if (isAuthErrorInfo(errs[0])) throwGlsErrors(errs, body, ctx);
        return null; // e.g. unknown parcel number
      }
      return { ParcelNumber: Number(body.ParcelNumber) || Number(awb), ParcelStatusList: body.ParcelStatusList || [] };
    };
    for (const group of chunk(wanted, 100)) {
      let parcels;
      try {
        const body = await call(ctx, 'ParcelService', 'GetParcelListStatuses', {
          ParcelNumberList: group.map(Number),
          LanguageIsoCode: 'RO',
        });
        if (Array.isArray(body.GetParcelListStatusesErrors) && body.GetParcelListStatusesErrors.length && !body.ParcelList?.length) {
          throwGlsErrors(body.GetParcelListStatusesErrors, body, ctx);
        }
        parcels = body.ParcelList || [];
        if (!parcels.length) {
          // Live: with bad credentials the batch method answers an empty list and NO error. Ask about one
          // parcel with the single method, which does report "Unauthorized." / lockout.
          const probe = await single(group[0]);
          if (probe?.ParcelStatusList?.length) throw new Error('batch method returned nothing for a known parcel');
        }
      } catch (err) {
        if (err?.code === 'AUTH_FAILED') throw err;
        // Batch method is new (2026-03; in the live RO WSDL); fall back to one call per parcel.
        // VERIFY: its answer for real parcels / unknown parcel numbers with a real account.
        ctx.log?.(m('log.statusBatchFailed', { provider: PROVIDER }), { err: err?.message });
        parcels = [];
        for (const awb of group) {
          const p = await single(awb);
          if (p) parcels.push(p);
        }
      }
      for (const p of parcels) {
        const awb = String(p?.ParcelNumber ?? '');
        if (!group.includes(awb)) continue; // ParcelNumber 0 (error answer) or not asked for
        if (out.some((o) => o.awb === awb)) continue;
        const events = [...(p.ParcelStatusList || [])]
          .sort((a, b) => (Date.parse(parseGlsDate(a.StatusDate) || 0) || 0) - (Date.parse(parseGlsDate(b.StatusDate) || 0) || 0));
        const last = latestMeaningful(events, (e) => mapGlsStatus(e.StatusCode));
        const status = last ? last.status : S.CREATED;
        out.push({
          awb,
          status,
          // No events yet: no words of the courier's own (the status label 'AWB created' is shown, translated).
          statusText: last ? String(last.event.StatusDescription || '').trim() : undefined,
          at: last ? parseGlsDate(last.event.StatusDate) : undefined,
          ...(status === S.DELIVERED ? { codCollected: true } : {}),
        });
      }
    }
    return out;
  },

  async listServices(ctx) {
    return [
      { id: 'standard', name: 'GLS Business Parcel (standard)' },
      { id: 'PSD', name: t(ctx?.locale, 'gls.services.PSD') },
    ];
  },
};

