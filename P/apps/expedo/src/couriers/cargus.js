import { ProcessingError, authError } from '../core/errors.js';
import { TrackingStatus } from './contract.js';
import {
  matchLocality, matchCounty, localityError, countyError, isBucharest, normalizePhoneRO,
  classifyStatusText, parseDimensions, collectMessages, shortText, normalizeText, compactKey,
} from './ro-helpers.js';

// Cargus — "UrgentOnlineAPI" (Azure API Management).
// Sources: Cargus API technical documentation V3 (cargus.ro/wp-content/uploads/DocumentationAPIV3-2.3.2-EN.pdf),
// official Cargus WooCommerce plugin 1.6.0 (wordpress.org/plugins/cargus) and PrestaShop module
// (gitlab.com/cargus/cargus-modules/prestashop).
//
// Auth: every call sends `Ocp-Apim-Subscription-Key`; POST LoginUser {UserName, Password} returns a
// JSON string token (valid 24h) sent as `Authorization: Bearer <token>`.
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

export const SERVICES = [
  { id: '34', name: 'Economic Standard (până la 31 kg)' },
  { id: '35', name: 'Standard Plus (31–50 kg)' },
  { id: '36', name: 'Palet Standard (peste 50 kg)' },
  { id: '38', name: 'PUDO / Ship & Go (livrare la punct)' },
  { id: '39', name: 'Multipiece (max 15 colete, max 31 kg/colet)' },
  { id: '1', name: 'Standard (contracte vechi)' },
];

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
const tokenCacheKey = (ctx) => `cargus:token:${ctx.credentials?.username || ''}`;

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
    message: 'Cheia API Cargus (Primary key) nu e acceptată.',
    hint: 'Copiază „Primary key” din contul tău de pe urgentcargus.portal.azure-api.net (Products → UrgentOnlineAPI) și testează din nou conexiunea.',
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
    throw new ProcessingError({
      code: 'AUTH_FAILED',
      message: 'Lipsesc datele de conectare Cargus (cheie API, utilizator sau parolă).',
      hint: 'Completează-le în Setări → Integrări → Cargus.',
      provider: PROVIDER,
    });
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
      if (attempt === 0 && err?.code === 'AUTH_FAILED' && !/Primary key/.test(err.message)) {
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
      parent: l.ParentName,
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
  const result = matchLocality(q, await getLocalities(ctx, county.id));
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
        ctx.log?.('cargus: localitate găsită în județul vecin', { city: recipient.city, from: recipient.county, to: other.name });
        return { county: other, locality: r2.match, via: `${r2.via}+county` };
      }
    }
  }
  throw localityError({ provider: PROVIDER, providerName: NAME, city: recipient.city, county: county.name || recipient.county, result });
}

// ---------------------------------------------------------------------------------------------
// Error mapping for AWB creation

function rejected(code, message, hint, field, details) {
  return new ProcessingError({ code, message, hint, retryable: false, provider: PROVIDER, field, details });
}

export function mapAwbError(body, shipment, status) {
  const msgs = collectMessages(body);
  const text = normalizeText(msgs.map((m) => `${m.path} ${m.message}`).join(' | '));
  const first = shortText(msgs[0]?.message);
  const said = first ? ` Cargus spune: „${first}”.` : '';
  const r = shipment?.recipient || {};
  if (/pudo|ship ?go|ship and go|deliverypudopoint/.test(text)) {
    return rejected('LOCKER_INVALID', 'Punctul Ship & Go ales nu e acceptat de Cargus (inactiv sau fără ramburs).',
      `Alege alt punct Ship & Go sau livrează la adresă.${said}`, 'lockerId', body);
  }
  if (/telefon|phone/.test(text)) {
    return rejected('ADDRESS_PHONE_INVALID', `Cargus nu acceptă numărul de telefon „${r.phone || ''}”.`,
      `Folosește un număr de 10 cifre (ex. 07xxxxxxxx), fără spații.${said}`, 'shippingAddress.phone', body);
  }
  if (/localit|locality|\bcity\b|\boras\b/.test(text)) {
    return rejected('ADDRESS_CITY_NOT_FOUND', `Cargus nu acceptă localitatea „${r.city || ''}” (județul ${r.county || '-'}).`,
      `Verifică localitatea și județul din adresa de livrare.${said}`, 'shippingAddress.city', body);
  }
  if (/judet|county/.test(text)) {
    return rejected('ADDRESS_COUNTY_NOT_FOUND', `Cargus nu acceptă județul „${r.county || ''}”.`,
      `Corectează județul în adresa de livrare.${said}`, 'shippingAddress.province', body);
  }
  if (/greutat|weight|\bkg\b/.test(text)) {
    return rejected('SHIPMENT_WEIGHT_INVALID', `Cargus nu acceptă greutatea de ${shipment?.weightKg ?? '?'} kg pentru serviciul ales.`,
      `Verifică greutatea produselor. Economic Standard: max 31 kg, Standard Plus: 31–50 kg, peste 50 kg: Palet.${said}`, 'weightKg', body);
  }
  if (/punct de ridicare|pickup|locationid|sender|expeditor/.test(text)) {
    return rejected('CONFIG_PICKUP_POINT_INVALID', 'Punctul de ridicare Cargus din setări nu e valid sau nu e activ pentru utilizatorul tău.',
      `Alege din nou punctul de ridicare în Setări → Integrări → Cargus.${said}`, 'settings.pickupPointId', body);
  }
  if (/serviciu|service/.test(text)) {
    return rejected('CONFIG_SERVICE_INVALID', 'Serviciul Cargus ales nu e disponibil în contractul tău.',
      `Alege alt serviciu în Setări → Integrări → Cargus (de obicei Economic Standard).${said}`, 'settings.service', body);
  }
  if (/ramburs|repayment/.test(text)) {
    return rejected('COD_INVALID', 'Cargus a refuzat rambursul.',
      `Dacă nu ai cont colector activ, alege „Ramburs numerar” în setările Cargus.${said}`, 'cod', body);
  }
  if (/tarif|pricetable/.test(text)) {
    return rejected('CONFIG_PRICE_TABLE_INVALID', 'ID-ul de tarif Cargus din setări nu e valid.',
      `Golește câmpul „ID tarif” din Setări → Integrări → Cargus sau cere ID-ul corect de la Cargus.${said}`, 'settings.priceTableId', body);
  }
  if (/e ?mail/.test(text)) {
    return rejected('ADDRESS_EMAIL_INVALID', `Cargus nu acceptă emailul „${r.email || ''}”.`,
      `Corectează emailul clientului.${said}`, 'email', body);
  }
  if (/adresa|address|strada|street/.test(text)) {
    return rejected('ADDRESS_STREET_INVALID', 'Cargus nu acceptă adresa (strada/numărul) destinatarului.',
      `Verifică strada și numărul în adresa de livrare.${said}`, 'shippingAddress.address1', body);
  }
  return rejected('PROVIDER_REJECTED', first ? `Cargus a refuzat AWB-ul: ${first}` : `Cargus a refuzat AWB-ul (cod ${status ?? '?'}).`,
    'Verifică datele comenzii și setările Cargus; detaliile complete sunt în jurnal.', undefined, body);
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
  const cod = Math.max(0, Number(shipment.cod) || 0);
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
    DeclaredValue: Math.max(0, Number(shipment.declaredValue) || 0),
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
    return /^\d{6,}$/.test(t) ? t : null;
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
    message: 'Nu e ales punctul de ridicare Cargus.',
    hint: points.length
      ? `Alege-l în Setări → Integrări → Cargus (ai ${points.length} puncte: ${points.slice(0, 3).map((p) => `${p.name} – ID ${p.id}`).join('; ')}).`
      : 'Contul Cargus nu are niciun punct de ridicare activ. Adaugă unul în WebExpress, apoi alege-l în Setări → Integrări → Cargus.',
    provider: PROVIDER,
    field: 'settings.pickupPointId',
  });
}

// Docs pass AWB lists as a JSON array in the query (barCodes=[804419419,804418863]).
// VERIFY: AwbDocuments/AwbTrace batch format against the live API (official plugins pass the same JSON list).
const encodeBarcodes = (awbs) => encodeURIComponent(`[${awbs.map((a) => (/^\d+$/.test(a) ? a : JSON.stringify(a))).join(',')}]`);

// ---------------------------------------------------------------------------------------------

const adapter = {
  id: PROVIDER,
  name: NAME,
  trackingUrl: (awb) => `https://www.cargus.ro/personal/urmareste-coletul/?tracking_number=${encodeURIComponent(awb)}`,

  credentialFields: [
    { key: 'subscriptionKey', label: 'Cheie API (Primary key)', type: 'password', required: true,
      help: 'Din urgentcargus.portal.azure-api.net → Products → UrgentOnlineAPI → Primary key.' },
    { key: 'username', label: 'Utilizator WebExpress', type: 'text', required: true,
      help: 'Același utilizator cu care intri în WebExpress Cargus.' },
    { key: 'password', label: 'Parolă WebExpress', type: 'password', required: true },
  ],

  settingsFields: [
    { key: 'pickupPointId', label: 'Punct de ridicare (LocationId)', type: 'text', required: true,
      help: 'De unde ridică curierul coletele. Apasă „Testează conexiunea” ca să vezi ID-urile.' },
    { key: 'service', label: 'Serviciu implicit', type: 'select', default: 'auto',
      options: [{ value: 'auto', label: 'Automat după greutate (34 / 35 / 36)' }, ...SERVICES.filter((x) => x.id !== '38').map((x) => ({ value: x.id, label: x.name }))],
      help: 'Pentru livrări la Ship & Go se folosește automat serviciul 38.' },
    { key: 'codType', label: 'Tip ramburs', type: 'select', default: 'bank',
      options: [{ value: 'bank', label: 'Cont colector (în bancă)' }, { value: 'cash', label: 'Numerar (în plic)' }],
      help: 'Cum îți returnează Cargus banii din ramburs. Trebuie să corespundă contractului.' },
    { key: 'openPackage', label: 'Deschidere colet la livrare', type: 'checkbox', default: false,
      help: 'Valoarea implicită; poate fi schimbată per comandă.' },
    { key: 'labelFormat', label: 'Format etichetă', type: 'select', default: 'A6',
      options: [{ value: 'A6', label: 'Etichetă 10x14 cm (A6)' }, { value: 'A4', label: 'Pagină A4' }] },
    { key: 'defaultDimensions', label: 'Dimensiuni implicite colet (cm)', type: 'text', default: '30x20x10',
      help: 'Lungime x lățime x înălțime, folosite când comanda nu are dimensiuni.' },
    { key: 'priceTableId', label: 'ID tarif (opțional)', type: 'text',
      help: 'Doar dacă Cargus ți-a dat un PriceTableId. Altfel lasă gol.' },
  ],

  async testConnection(ctx) {
    await login(ctx, { force: true });
    const points = await adapter.listPickupPoints(ctx);
    const chosen = String(ctx.settings?.pickupPointId || '').trim();
    let message = `Conectat la Cargus. Am găsit ${points.length} ${points.length === 1 ? 'punct' : 'puncte'} de ridicare.`;
    if (chosen && !points.some((p) => String(p.id) === chosen)) {
      message += ` Atenție: punctul de ridicare ${chosen} din setări nu e în listă.`;
    } else if (!chosen && points.length > 1) {
      message += ' Alege punctul de ridicare în setări.';
    }
    return { ok: true, message, info: { pickupPoints: points } };
  },

  async listPickupPoints(ctx) {
    const body = await api(ctx, 'GET', 'PickupLocations');
    return asArray(body).map((p) => ({
      id: String(p.LocationId),
      name: p.Name || `Punct ${p.LocationId}`,
      address: [p.AddressText || [p.StreetName, p.BuildingNumber].filter(Boolean).join(' '), p.LocalityName, p.CountyName].filter(Boolean).join(', '),
    }));
  },

  async listServices() {
    return SERVICES.map((x) => ({ ...x }));
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
        address: [[p.StreetName, p.StreetNo].filter(Boolean).join(' '), p.City, p.County].filter(Boolean).join(', '),
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
    const pickupPointId = await resolvePickupPointId(ctx);
    let place = {};
    if (shipment.lockerId) {
      if (!r.email) {
        throw rejected('ADDRESS_EMAIL_MISSING', 'Pentru livrare la Ship & Go, Cargus cere emailul destinatarului.',
          'Adaugă emailul clientului în comandă sau livrează la adresă.', 'email');
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
    ctx.log?.('cargus: AWB creat', { awb, reference: shipment.reference, localityId: place.locality?.id, via: place.via });
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
        message: `Cargus nu a trimis eticheta pentru AWB ${awb}.`,
        hint: 'Verifică dacă AWB-ul mai există (nu a fost anulat) și încearcă din nou.',
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
        message: `Cargus nu a anulat AWB-ul ${awb}.`,
        hint: 'Se poate anula doar înainte să fie ridicat de curier. Dacă a plecat deja, cere returul din WebExpress.',
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
        const d = last?.Date ? new Date(last.Date) : null; // VERIFY: Cargus dates have no timezone (Europe/Bucharest)
        out.push({
          awb: code,
          status,
          statusText: last?.Description || (last ? 'Necunoscut' : 'AWB emis'),
          at: d && !Number.isNaN(d.getTime()) ? d.toISOString() : undefined,
          codCollected: status === TrackingStatus.DELIVERED,
        });
      }
    }
    return out;
  },
};

export default adapter;
