import { ProcessingError } from '../core/errors.js';

// Helpers shared by the courier adapters (FAN Courier, GLS, DPD): diacritic-insensitive
// matching of Romanian localities against a courier nomenclator, nomenclator caching,
// small date / buffer utilities. Pure functions, no network.

export const NOMENCLATOR_TTL = 7 * 24 * 60 * 60; // 7 days, in seconds

/** Lowercase, no diacritics (ș/ş/ț/ţ/ă/â/î), punctuation → spaces, collapsed. */
export function norm(s) {
  return String(s ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

const PREFIX_TOKENS = new Set([
  'municipiul', 'municipiu', 'mun', 'm',
  'orasul', 'oras', 'or',
  'comuna', 'com', 'c',
  'satul', 'sat', 's',
  'localitatea', 'loc',
  'judetul', 'judet', 'jud',
]);

/** Drops administrative prefixes: "Mun. Cluj-Napoca" → "cluj napoca", "Com. Florești" → "floresti". */
export function stripPrefix(normalized) {
  const tokens = normalized.split(' ').filter(Boolean);
  // Keep at least one token: a place literally called "Sat" must survive.
  while (tokens.length > 1 && PREFIX_TOKENS.has(tokens[0])) tokens.shift();
  return tokens.join(' ');
}

const COUNTY_ALIASES = { bucharest: 'bucuresti', 'municipiul bucuresti': 'bucuresti', 'mun bucuresti': 'bucuresti' };

export function normCounty(s) {
  let n = norm(s).replace(/^(judetul|judet|jud)\s+/, '');
  n = COUNTY_ALIASES[n] || n;
  return n;
}

export function isBucharest(county, city) {
  if (normCounty(county) === 'bucuresti') return true;
  const c = stripPrefix(norm(city));
  return /^(bucuresti|bucharest)\b/.test(c) || /^sector(ul)? [1-6]$/.test(c);
}

export function extractSector(city) {
  const m = norm(city).match(/\bsector(?:ul)? ?([1-6])\b/);
  return m ? Number(m[1]) : undefined;
}

/**
 * Candidate spellings for a city, most specific first.
 * "Sat Florești, Com. Florești" → ["floresti"]; București + sector 3 → ["bucuresti sector 3", "sector 3", "bucuresti"].
 */
export function cityVariants({ city, county, sector }) {
  const out = [];
  if (isBucharest(county, city)) {
    const s = sector || extractSector(city);
    if (s) out.push(`bucuresti sector ${s}`, `sector ${s}`, `bucuresti sectorul ${s}`);
    out.push('bucuresti');
  }
  const parts = String(city ?? '').split(/[,;/]|\(|\)/).map((p) => stripPrefix(norm(p))).filter(Boolean);
  const countyN = normCounty(county);
  for (const p of parts) {
    if (parts.length > 1 && p === countyN) continue; // "Florești, Cluj": the county is not the city
    out.push(p);
  }
  return [...new Set(out)];
}

export function levenshtein(a, b) {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = cur;
  }
  return prev[b.length];
}

/** Up to `limit` display names closest to `target` (normalized). */
export function closest(items, target, { nameOf, describe = nameOf, limit = 3 } = {}) {
  const t = target || '';
  const scored = items.map((it) => {
    const n = stripPrefix(norm(nameOf(it)));
    let score = levenshtein(n, t) / Math.max(n.length, t.length, 1);
    if (t && (n.startsWith(t) || t.startsWith(n))) score -= 0.5;
    else if (t && (n.includes(t) || t.includes(n))) score -= 0.25;
    return { it, score };
  });
  scored.sort((a, b) => a.score - b.score);
  const names = [];
  for (const { it } of scored) {
    const d = describe(it);
    if (d && !names.includes(d)) names.push(d);
    if (names.length >= limit) break;
  }
  return names;
}

/**
 * Finds the recipient's locality in a courier nomenclator.
 *
 * @param {object[]} items  nomenclator entries
 * @param {object} address  { city, county, sector?, zip? }
 * @param {object} o
 * @param {(it)=>string} o.nameOf
 * @param {(it)=>string} [o.countyOf]   omit when the nomenclator has no county
 * @param {(it)=>string} [o.zipOf]      used to break ties
 * @param {(it)=>string} [o.describe]   label shown in suggestions (e.g. "Florești (com. Florești)")
 * @param {boolean} [o.allowDuplicates] same name twice is fine (courier only needs the name)
 * @param {string} o.provider           display name for messages
 * @param {string} o.providerId
 * @returns the matching entry
 * @throws ProcessingError ADDRESS_CITY_NOT_FOUND
 */
export function resolveLocality(items, address, o) {
  const { nameOf, countyOf, zipOf, describe = nameOf, allowDuplicates = false, provider, providerId } = o;
  const { city, county, zip } = address;
  const cityLabel = String(city ?? '').trim();

  if (!cityLabel) {
    throw new ProcessingError({
      code: 'ADDRESS_CITY_MISSING',
      message: 'Lipsește localitatea destinatarului.',
      hint: 'Completează localitatea în adresa de livrare.',
      field: 'shippingAddress.city',
      provider: providerId,
    });
  }

  let pool = items;
  let takeFirstDuplicate = allowDuplicates;
  let label = describe;
  if (countyOf && county) {
    const c = normCounty(county);
    const inCounty = items.filter((it) => normCounty(countyOf(it)) === c);
    if (inCounty.length) pool = inCounty;
    // County spelled differently in the nomenclator: search nationwide, but only accept a
    // name that is unique in the whole country (never guess between counties).
    else {
      takeFirstDuplicate = false;
      label = (it) => `${describe(it)} (jud. ${countyOf(it)})`;
    }
  }

  const variants = cityVariants(address);
  for (const v of variants) {
    let hits = pool.filter((it) => stripPrefix(norm(nameOf(it))) === v);
    if (!hits.length) continue;
    if (hits.length === 1) return hits[0];
    if (zip && zipOf) {
      const byZip = hits.filter((it) => String(zipOf(it) ?? '') === String(zip));
      if (byZip.length === 1) return byZip[0];
      if (byZip.length > 1) hits = byZip;
    }
    if (takeFirstDuplicate) return hits[0];
    const options = [...new Set(hits.map(label))].slice(0, 3);
    throw new ProcessingError({
      code: 'ADDRESS_CITY_NOT_FOUND',
      message: `Localitatea „${cityLabel}” apare de mai multe ori în nomenclatorul ${provider}${county ? ` (județul ${county})` : ''}.`,
      hint: `Ai vrut: ${options.join(', ')}? Completează codul poștal corect sau precizează comuna în adresa de livrare.`,
      field: 'shippingAddress.city',
      provider: providerId,
      details: { city, county, zip, candidates: hits.slice(0, 10) },
    });
  }

  const suggestions = closest(pool, variants[variants.length - 1] || norm(cityLabel), { nameOf, describe: label });
  throw new ProcessingError({
    code: 'ADDRESS_CITY_NOT_FOUND',
    message: `${provider} nu găsește localitatea „${cityLabel}”${county ? ` în județul ${county}` : ''}.`,
    hint: suggestions.length
      ? `Ai vrut: ${suggestions.join(', ')}? Corectează localitatea în adresa de livrare.`
      : 'Verifică localitatea și județul în adresa de livrare.',
    field: 'shippingAddress.city',
    provider: providerId,
    details: { city, county, zip, variants },
  });
}

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

/** "2023-03-01 04:46:46" in Europe/Bucharest local time → ISO string. */
export function roLocalToIso(s) {
  const m = String(s ?? '').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return undefined;
  const [, y, mo, d, h, mi, se = '0'] = m.map((x) => (x === undefined ? x : x));
  const asUtc = Date.UTC(+y, +mo - 1, +d, +h, +mi, +se);
  const offsetMin = tzOffsetMinutes(asUtc, 'Europe/Bucharest');
  return new Date(asUtc - offsetMin * 60_000).toISOString();
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

/** First human-meaningful status: walks events newest→oldest, skipping informational ones (mapper returns null). */
export function latestMeaningful(events, mapOne) {
  for (let i = events.length - 1; i >= 0; i--) {
    const mapped = mapOne(events[i]);
    if (mapped) return { event: events[i], status: mapped };
  }
  return undefined;
}
