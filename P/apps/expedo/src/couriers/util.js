import { createHash } from 'node:crypto';
import { ProcessingError } from '../core/errors.js';
import { TrackingStatus } from './contract.js';
import { normalizeText } from './locality.js';
import { m } from '../i18n/index.js';

// Non-locality helpers shared by the courier adapters (moved here from the former ro-helpers.js /
// ro-nomenclator.js; locality matching lives in locality.js): caching, money, phones, dates,
// tracking-text classification, error-body digging. Pure functions, no network.

export const NOMENCLATOR_TTL = 7 * 24 * 60 * 60; // 7 days, in seconds

// ---------------------------------------------------------------- cache

/** get-or-load through ctx.cache (sync or async cache implementations both work). */
export async function cached(ctx, key, ttlSeconds, loader) {
  try {
    const hit = await ctx.cache?.get(key);
    if (hit !== undefined && hit !== null) return hit;
  } catch { /* cache is best-effort */ }
  const value = await loader();
  try { await ctx.cache?.set(key, value, ttlSeconds); } catch { /* ignore */ }
  return value;
}

export async function cacheGet(ctx, key) {
  try { return (await ctx.cache?.get(key)) ?? undefined; } catch { return undefined; }
}

export async function cacheSet(ctx, key, value, ttlSeconds) {
  try { await ctx.cache?.set(key, value, ttlSeconds); } catch { /* ignore */ }
}

/**
 * Short, non-reversible fingerprint of an account's credentials, for cache keys.
 * ctx.cache is per store, but one store can hold two accounts of the same courier (or switch
 * sandbox ↔ production, or change the password): tokens and per-account data must never be shared
 * between them. Including the secret means a changed password never reuses a token issued for the
 * old one.
 */
export function accountKey(...parts) {
  return createHash('sha256').update(parts.map((p) => String(p ?? '')).join('\u0000')).digest('hex').slice(0, 16);
}

// ---------------------------------------------------------------- money

/** Rounds to bani (2 decimals) without the 1.005 → 1.00 float trap; negatives/NaN → 0. */
export function money(v) {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

/**
 * For couriers whose API has no COD currency field (the amount is always RON): refuse a COD in
 * another currency instead of silently collecting 149.90 RON for a 149.90 EUR order.
 */
export function assertRonCod(shipment, { provider, providerName }) {
  const currency = String(shipment?.currency || 'RON').toUpperCase();
  if (money(shipment?.cod) > 0 && currency !== 'RON') {
    throw new ProcessingError({
      code: 'COD_CURRENCY_UNSUPPORTED',
      key: 'courier.codCurrency',
      params: { provider: providerName, currency },
      retryable: false,
      provider,
      field: 'cod',
      details: { cod: shipment.cod, currency },
    });
  }
}

// ---------------------------------------------------------------- misc

export function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

export function isPdf(buf) {
  return Buffer.isBuffer(buf) && buf.length > 4 && buf.subarray(0, 5).toString('latin1') === '%PDF-';
}

/** Body that came back as a Buffer but is really a JSON error. */
export function bufferToJson(buf) {
  try { return JSON.parse(Buffer.from(buf).toString('utf8')); } catch { return undefined; }
}

/** Parse "30x20x10" style settings. */
export function parseDimensions(s) {
  const m = String(s ?? '').match(/(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)/i);
  if (!m) return null;
  const n = (x) => Math.max(1, Math.round(Number(x.replace(',', '.'))));
  return { length: n(m[1]), width: n(m[2]), height: n(m[3]) };
}

// ---------------------------------------------------------------- dates

/** "2023-03-01 04:46:46" in Europe/Bucharest local time → ISO string. */
export function roLocalToIso(s) {
  const m = String(s ?? '').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return undefined;
  const [, y, mo, d, h, mi, se = '0'] = m;
  const asUtc = Date.UTC(+y, +mo - 1, +d, +h, +mi, +se);
  const offsetMin = tzOffsetMinutes(asUtc, 'Europe/Bucharest');
  return new Date(asUtc - offsetMin * 60_000).toISOString();
}

/** Courier date → ISO. Strings with an explicit zone ("Z", "+0200", "+02:00") are honoured; zone-less ones are Bucharest local time. */
export function courierDateToIso(v) {
  if (v == null || v === '') return undefined;
  const s = String(v).trim();
  if (/(?:Z|[+-]\d{2}:?\d{2})$/i.test(s)) {
    const d = new Date(s.replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
    return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
  }
  return roLocalToIso(s);
}

function tzOffsetMinutes(utcMs, timeZone) {
  try {
    const part = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'shortOffset' })
      .formatToParts(new Date(utcMs)).find((p) => p.type === 'timeZoneName')?.value || '';
    const m = part.match(/GMT([+-])(\d{1,2})(?::(\d{2}))?/);
    if (!m) return 0;
    return (m[1] === '-' ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3] || 0));
  } catch {
    return 0;
  }
}

// ---------------------------------------------------------------- phones & streets

/** "+40 722 123 456" / "0040722123456" / "722123456" → "0722123456". Returns digits as-is when it can't tell. */
export function normalizePhoneRO(phone) {
  let d = String(phone ?? '').replace(/\D/g, '');
  if (d.startsWith('0040')) d = `0${d.slice(4)}`;
  else if (d.startsWith('40') && d.length === 11) d = `0${d.slice(2)}`;
  else if (d.length === 9 && d.startsWith('7')) d = `0${d}`;
  return d;
}

/** Phone in local Romanian format → international (+40...). Leaves others alone. */
export function toIntlPhone(phone) {
  const p = String(phone ?? '').replace(/[^\d+]/g, '');
  if (p.startsWith('+')) return p;
  if (p.startsWith('0040')) return `+${p.slice(2)}`;
  if (p.startsWith('40') && p.length === 11) return `+${p}`;
  if (p.startsWith('0')) return `+40${p.slice(1)}`;
  return p;
}

/**
 * Splits "Str. Memorandumului nr. 28, ap. 3" → { street: 'Str. Memorandumului', number: '28', info: 'ap. 3' }.
 * Conservative: when no clear house number is found, everything stays in `street`.
 */
export function splitStreet(address) {
  const s = String(address ?? '').replace(/\s+/g, ' ').trim();
  let m = s.match(/^(.*?)[,\s]+(?:nr\.?|numarul|număr(?:ul)?|no\.?)\s*(\d+)\s*([a-zA-Z]?\b)?[,\s]*(.*)$/i);
  if (m && m[1]) return { street: m[1].replace(/[,\s]+$/, ''), number: m[2], info: [m[3], m[4]].filter(Boolean).join(' ').trim() };
  m = s.match(/^(\D*?[a-zA-ZăâîșşțţĂÂÎȘŞȚŢ.])\s+(\d+)\s*([a-zA-Z]?)(?:\s*,\s*(.*))?$/);
  if (m) return { street: m[1].trim(), number: m[2], info: [m[3], m[4]].filter(Boolean).join(' ').trim() };
  return { street: s, number: '', info: '' };
}

// ---------------------------------------------------------------- tracking

/** First human-meaningful status: walks events newest→oldest, skipping informational ones (mapper returns null). */
export function latestMeaningful(events, mapOne) {
  for (let i = events.length - 1; i >= 0; i--) {
    const mapped = mapOne(events[i]);
    if (mapped) return { event: events[i], status: mapped };
  }
  return undefined;
}

/**
 * Fallback mapping from a Romanian (or English) courier status text to TrackingStatus.
 * Order matters: "nelivrat" must hit FAILED_ATTEMPT before "livrat" hits DELIVERED,
 * "returnat la expeditor" must hit RETURNED before "retur" hits RETURNING.
 */
export function classifyStatusText(text) {
  const t = normalizeText(text);
  if (!t) return TrackingStatus.UNKNOWN;
  // COD money paid out to the merchant happens after delivery ("Ramburs returnat expeditorului" is NOT a parcel return).
  if (/\bramburs (transferat|returnat|platit|achitat|virat|incasat)/.test(t)) return TrackingStatus.DELIVERED;
  if (/\b(anulat|anulata|anulare|sters|stearsa|deleted|cancel+ed)\b/.test(t)) return TrackingStatus.CANCELLED;
  if (/(returnat[a]? (la|catre) expeditor|predat[a]? expeditorului|livrat[a]? (la |catre )?expeditor|retur livrat|returned to sender)/.test(t)) return TrackingStatus.RETURNED;
  if (/(refuz|retur|return)/.test(t)) return TrackingStatus.RETURNING;
  if (/(nelivrat|nu a putut fi livrat|livrare esuata|esuat|absent|adresa (gresita|incompleta|incorecta|inexistenta)|nu raspunde|telefon inchis|reprogramat|amanat|avizat|imposibil|failed)/.test(t)) return TrackingStatus.FAILED_ATTEMPT;
  if (/(\blivrat|\blivrata|delivered|ridicat[a]? (din easybox|din locker|de destinatar|de catre destinatar)|confirmat[a]? de destinatar)/.test(t)) return TrackingStatus.DELIVERED;
  if (/(in livrare|in curs de livrare|pentru livrare|out for delivery|depus[a]? in|incarcat[a]? in|disponibil[a]? (pentru ridicare|in)|in easybox|in locker|ship go)/.test(t)) return TrackingStatus.OUT_FOR_DELIVERY;
  if (/(ridicat|preluat|picked)/.test(t)) return TrackingStatus.PICKED_UP;
  if (/(tranzit|transit|depozit|hub|sortare|sortat|transfer|sosit|plecat|expediat)/.test(t)) return TrackingStatus.IN_TRANSIT;
  if (/(inregistrat|emis|creat|generat|tiparit|validat|asteptare|registered)/.test(t)) return TrackingStatus.CREATED;
  return TrackingStatus.UNKNOWN;
}

// ---------------------------------------------------------------- error bodies

/** Collect every human string out of an arbitrary error body (arrays, ModelState, Symfony form errors...). */
export function collectMessages(body, path = '', out = [], depth = 0) {
  if (body == null || depth > 8 || out.length > 30) return out;
  if (Buffer.isBuffer(body)) {
    try { return collectMessages(JSON.parse(body.toString('utf8')), path, out, depth + 1); } catch { return out; }
  }
  if (typeof body === 'string' || typeof body === 'number') {
    const s = String(body).trim();
    if (s) out.push({ path, message: s });
    return out;
  }
  if (Array.isArray(body)) {
    for (const x of body) collectMessages(x, path, out, depth + 1);
    return out;
  }
  if (typeof body === 'object') {
    for (const [k, v] of Object.entries(body)) {
      if (['code', 'statusCode', 'status', 'traceId', 'type'].includes(k)) continue;
      const structural = ['errors', 'children', 'Errors', 'ModelState', 'modelState', 'message', 'Message', 'error', 'Error', 'ErrorMessage', 'title', 'detail'].includes(k);
      collectMessages(v, structural ? path : (path ? `${path}.${k}` : k), out, depth + 1);
    }
  }
  return out;
}

/**
 * " Cargus says: “…”." after a hint: the courier's own words, verbatim but quoted, so they read the
 * same in both languages ('' when there is nothing useful to quote).
 */
export function saidBy(providerName, text) {
  const s = shortText(text);
  return s ? m('courier.says', { provider: providerName, text: s }) : '';
}

/** Short, single-line courier message suitable for a hint (never a JSON dump). */
export function shortText(s, max = 160) {
  const t = String(s ?? '').replace(/\s+/g, ' ').trim();
  if (!t || /^[[{]/.test(t)) return '';
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

/** True for an HTML page (Cloudflare challenge, proxy error page...) instead of the courier's JSON. */
export function looksLikeHtml(body) {
  const s = Buffer.isBuffer(body) ? body.subarray(0, 200).toString('utf8') : typeof body === 'string' ? body.slice(0, 200) : '';
  return /^\s*(<!doctype html|<html|<\?xml)/i.test(s);
}
