import { ProcessingError } from '../core/errors.js';
import { TrackingStatus } from './contract.js';

// Romanian-specific helpers shared by courier adapters (Cargus, Sameday...):
//  - locality matching against a courier nomenclator (the #1 cause of "AWB-urile dau erori")
//  - phone normalization
//  - Romanian tracking-text → TrackingStatus fallback classifier

/** Lowercase ASCII words: diacritics stripped (ș/ş/ț/ţ/ă/â/î), punctuation → spaces. */
export function normalizeText(s) {
  return String(s ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

/** Same as normalizeText without spaces: "Cluj-Napoca" == "Cluj Napoca" == "clujnapoca". */
export const compactKey = (s) => normalizeText(s).replace(/ /g, '');

// Administrative prefixes customers type in front of the locality name.
const PREFIX_WORDS = new Set([
  'mun', 'municipiul', 'municipiu', 'oras', 'orasul', 'or', 'com', 'comuna', 'sat', 'satul',
  'loc', 'localitatea', 'localitate', 'jud', 'judet', 'judetul', 'str',
]);

export function isBucharest(county, countyCode) {
  if (String(countyCode || '').toUpperCase() === 'B') return true;
  const n = normalizeText(county).replace(/^municipiul /, '');
  return n === 'bucuresti' || n === 'bucharest';
}

/** Sector from explicit value, from the city text ("Sector 3", "sectorul 3", "S3") or from a Bucharest zip (03xxxx → 3). */
export function detectSector({ city, sector, zip, bucharest }) {
  const explicit = Number(sector);
  if (explicit >= 1 && explicit <= 6) return explicit;
  const m = normalizeText(city).match(/\b(?:sectorul|sector|sect|s)\s*([1-6])\b/);
  if (m) return Number(m[1]);
  if (bucharest) {
    const z = String(zip || '').replace(/\D/g, '');
    const zm = z.match(/^0([1-6])\d{4}$/);
    if (zm) return Number(zm[1]);
  }
  return undefined;
}

/** Strip "Mun.", "Com.", "Sat", trailing "(Ilfov)", ", jud. X" and sector mentions → bare locality name (normalized). */
export function cleanCityName(city) {
  let s = String(city ?? '').replace(/\(.*?\)/g, ' ');
  s = s.split(',')[0];
  let words = normalizeText(s).replace(/\b(?:sectorul|sector|sect)\s*[1-6]\b/g, ' ').trim().split(' ').filter(Boolean);
  while (words.length > 1 && PREFIX_WORDS.has(words[0])) words = words.slice(1);
  return words.join(' ');
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

function similarity(a, b) {
  if (!a || !b) return 0;
  let score = 1 - levenshtein(a, b) / Math.max(a.length, b.length);
  if (a.startsWith(b) || b.startsWith(a)) score += 0.15;
  return score;
}

const cleanZip = (z) => String(z ?? '').replace(/\D/g, '');

/** Pick among same-named localities using the postal code (exact, then longest common prefix ≥ 4). */
function disambiguateByZip(cands, zip) {
  const z = cleanZip(zip);
  if (!z || z.length !== 6) return null;
  const exact = cands.filter((c) => cleanZip(c.postalCode) === z);
  if (exact.length === 1) return exact[0];
  const prefixLen = (p) => { let i = 0; while (i < 6 && p[i] === z[i]) i++; return i; };
  const scored = cands.map((c) => ({ c, n: prefixLen(cleanZip(c.postalCode)) })).sort((x, y) => y.n - x.n);
  if (scored.length && scored[0].n >= 4 && (scored.length === 1 || scored[1].n < scored[0].n)) return scored[0].c;
  return null;
}

function resolveSameName(cands, zip, via) {
  if (cands.length === 1) return { match: cands[0], via };
  const byZip = disambiguateByZip(cands, zip);
  if (byZip) return { match: byZip, via: `${via}+zip` };
  return { ambiguous: cands };
}

/**
 * Match a recipient locality against a courier nomenclator.
 * @param {{city:string, zip?:string, sector?:number, county?:string, countyCode?:string}} q
 * @param {{id:any, name:string, postalCode?:string}[]} candidates   localities of ONE county
 * @returns {{match, via} | {ambiguous: object[]} | {notFound: true, suggestions: object[]}}
 */
export function matchLocality(q, candidates) {
  const cands = (candidates || []).filter((c) => c && c.name);
  const bucharest = isBucharest(q.county, q.countyCode);
  const sector = detectSector({ city: q.city, sector: q.sector, zip: q.zip, bucharest });
  const base = cleanCityName(q.city);
  const byKey = new Map();
  for (const c of cands) {
    const k = compactKey(c.name);
    if (!byKey.has(k)) byKey.set(k, []);
    byKey.get(k).push(c);
  }

  // 1. Exact (diacritic/hyphen/prefix-insensitive) name match, most specific variant first.
  const variants = [];
  // "București", "Bucuresti Sector 3", "Sectorul 3", "Buc." → Bucharest itself; "Voluntari" typed with
  // county București is NOT Bucharest (caller may retry in Ilfov).
  const looksBucharest = bucharest && (!base || /^(buc|bucharest)/.test(base));
  if (looksBucharest) {
    if (sector) variants.push(`sectorul ${sector}`, `sector ${sector}`, `bucuresti sectorul ${sector}`, `bucuresti sector ${sector}`);
    variants.push('bucuresti', 'municipiul bucuresti');
  } else {
    variants.push(base, normalizeText(String(q.city ?? '').split(',')[0]));
  }
  for (const v of variants) {
    const hit = byKey.get(compactKey(v));
    if (hit) return resolveSameName(hit, q.zip, 'name');
  }
  if (looksBucharest) {
    // Nomenclator split by sector (e.g. Sameday "Sectorul 1..6") and we don't know which one.
    const sectors = cands.filter((c) => /^(sectorul|sector) [1-6]$/.test(normalizeText(c.name)));
    if (sectors.length) return { ambiguous: sectors.sort((a, b) => a.name.localeCompare(b.name)) };
  }

  // 2. Unique postal code (customer typed a commune/neighbourhood but the zip is right).
  const z = cleanZip(q.zip);
  if (z.length === 6) {
    const zipHits = cands.filter((c) => cleanZip(c.postalCode) === z);
    if (zipHits.length === 1) return { match: zipHits[0], via: 'zip' };
  }

  // 3. A nomenclator name appearing as whole words inside what the customer typed
  //    ("Voluntari Pipera", "Ploiesti Prahova", "Sat Rosu Com Chiajna" → one unique hit).
  const qWords = ` ${normalizeText(q.city)} `;
  const contained = [...byKey.entries()].filter(([, list]) => {
    const n = normalizeText(list[0].name);
    return n.length >= 4 && qWords.includes(` ${n} `);
  });
  if (contained.length === 1) return resolveSameName(contained[0][1], q.zip, 'contains');

  // 4. One-letter typo on a reasonably long name ("Bucurest", "Constana").
  const qk = compactKey(base);
  if (qk.length >= 5) {
    const close = [...byKey.entries()].filter(([k]) => levenshtein(k, qk) <= 1);
    if (close.length === 1) return resolveSameName(close[0][1], q.zip, 'typo');
  }

  // Not found: up to 3 closest distinct names.
  const suggestions = [...byKey.values()]
    .map((list) => ({ c: list[0], s: similarity(compactKey(list[0].name), qk) }))
    .sort((a, b) => b.s - a.s)
    .slice(0, 3)
    .filter((x) => x.s > 0.3)
    .map((x) => x.c);
  return { notFound: true, suggestions };
}

/** County by code ("CJ", "B") then by name, diacritic-insensitive. */
export function matchCounty({ county, countyCode }, counties) {
  const code = String(countyCode || '').toUpperCase();
  if (code) {
    const hit = counties.find((c) => String(c.code || '').toUpperCase() === code);
    if (hit) return hit;
  }
  const key = compactKey(String(county || '').replace(/^(jud(etul)?\.?)\s+/i, ''));
  const bucharest = isBucharest(county, countyCode);
  return counties.find((c) => {
    const k = compactKey(c.name);
    return k === key || (bucharest && (k === 'bucuresti' || k === 'municipiulbucuresti'));
  }) || null;
}

const label = (c, withZip) => (withZip && c.postalCode ? `${c.name} (cod ${c.postalCode})` : c.name);

/** ProcessingError for a locality the courier won't accept, with "Ai vrut: X, Y, Z?" suggestions. */
export function localityError({ provider, providerName, city, county, result }) {
  const ambiguous = result?.ambiguous;
  const options = (ambiguous || result?.suggestions || []).slice(0, 3);
  const sameNames = ambiguous && new Set(ambiguous.map((c) => compactKey(c.name))).size === 1;
  const isSectors = ambiguous && options.every((c) => /^(sectorul|sector) [1-6]$/.test(normalizeText(c.name)));
  const did = options.length ? `Ai vrut: ${options.map((c) => label(c, sameNames)).join(', ')}? ` : '';
  let message;
  let fix;
  if (isSectors) {
    message = `Pentru București, ${providerName} cere sectorul, iar în adresă nu apare.`;
    fix = 'Adaugă sectorul în localitate (ex. „Sector 3”) sau codul poștal corect.';
  } else if (ambiguous) {
    message = `Localitatea „${city}” apare de mai multe ori în nomenclatorul ${providerName} pentru județul ${county}.`;
    fix = 'Adaugă codul poștal corect în adresă ca să alegem localitatea potrivită.';
  } else {
    message = `Localitatea „${city}” nu există în nomenclatorul ${providerName} pentru județul ${county}.`;
    fix = 'Corectează localitatea (și județul) în adresa de livrare a comenzii.';
  }
  return new ProcessingError({
    code: 'ADDRESS_CITY_NOT_FOUND',
    message,
    hint: `${did}${fix}`,
    retryable: false,
    provider,
    field: 'shippingAddress.city',
    details: { city, county, options: options.map((c) => ({ id: c.id, name: c.name, postalCode: c.postalCode })) },
  });
}

export function countyError({ provider, providerName, county, countyCode }) {
  return new ProcessingError({
    code: 'ADDRESS_COUNTY_NOT_FOUND',
    message: `Județul „${county || countyCode || '-'}” nu e recunoscut de ${providerName}.`,
    hint: 'Corectează județul în adresa de livrare a comenzii.',
    retryable: false,
    provider,
    field: 'shippingAddress.province',
    details: { county, countyCode },
  });
}

/** "+40 722 123 456" / "0040722123456" / "722123456" → "0722123456". Returns digits as-is when it can't tell. */
export function normalizePhoneRO(phone) {
  let d = String(phone ?? '').replace(/\D/g, '');
  if (d.startsWith('0040')) d = `0${d.slice(4)}`;
  else if (d.startsWith('40') && d.length === 11) d = `0${d.slice(2)}`;
  else if (d.length === 9 && d.startsWith('7')) d = `0${d}`;
  return d;
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

/** Parse "1.2" / "30x20x10" style settings. */
export function parseDimensions(s) {
  const m = String(s ?? '').match(/(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)/i);
  if (!m) return null;
  const n = (x) => Math.max(1, Math.round(Number(x.replace(',', '.'))));
  return { length: n(m[1]), width: n(m[2]), height: n(m[3]) };
}

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

/** Short, single-line courier message suitable for a hint (never a JSON dump). */
export function shortText(s, max = 160) {
  const t = String(s ?? '').replace(/\s+/g, ' ').trim();
  if (!t || /^[[{]/.test(t)) return '';
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}
