import { ProcessingError } from '../core/errors.js';
import { fold, levenshtein } from '../core/address.js';

// Romanian locality matching against a courier nomenclator — the #1 cause of "AWB-urile dau erori".
// One implementation for all five adapters (it replaces ro-helpers.js and ro-nomenclator.js):
//
//  - diacritic / punctuation / case insensitive ("Cluj–Napoca" == "cluj napoca", ş == ș);
//  - administrative prefixes dropped ("Mun.", "Oraș", "Com.", "Sat", "Loc.", "Jud.");
//  - București: "Sector 3", "Sectorul 3", "S3", or the sector from a 03xxxx postal code, for
//    nomenclators split by sector (Sameday) or not (Cargus, FAN, DPD, GLS);
//  - several localities with the same name: postal code first, then the commune the customer typed
//    ("Valea Mare, com. Budești"), FAN's "Name (Commune)" spelling, otherwise an explicit
//    "Ai vrut: X (Comuna), Y (Comuna)?" error — we never guess between villages;
//  - otherwise a unique postal code, a nomenclator name contained in what was typed
//    ("Turda, jud. Cluj", "Voluntari Pipera"), and — only for adapters that opt in — a one-letter typo;
//  - not found: "Ai vrut: X, Y, Z?" with the three closest names.
//
// Real data shapes this was checked against (2026-10 live check, FAN /reports/localities is public):
// FAN names have no diacritics and are unique per county; 827 of 13 834 carry the commune in
// parentheses ("Alun (Bosorod)", "Merisor (Bucuresci)") and București is a single locality.

/** Lowercase ASCII words: diacritics stripped (ș/ş/ț/ţ/ă/â/î), punctuation → single spaces. */
export const normalizeText = (s) => fold(s);
export const norm = normalizeText;
export { levenshtein };

/** Same as normalizeText without spaces: "Cluj-Napoca" == "Cluj Napoca" == "clujnapoca". */
export const compactKey = (s) => normalizeText(s).replace(/ /g, '');

// Administrative prefixes customers type in front of the locality name. Single letters ("c", "s",
// "m") are deliberately absent: FAN has real localities called "C.A. Rosetti" and "I. L. Caragiale".
const PREFIX_WORDS = new Set([
  'mun', 'municipiul', 'municipiu', 'oras', 'orasul', 'or', 'com', 'comuna', 'sat', 'satul',
  'loc', 'localitatea', 'localitate', 'jud', 'judet', 'judetul', 'str',
]);

const SECTOR_RE = /\b(?:sectorul|sector|sect)\s*([1-6])\b/;

/** Drops leading administrative prefixes from normalized text; keeps at least one word. */
export function stripPrefix(normalized) {
  const words = String(normalized ?? '').split(' ').filter(Boolean);
  while (words.length > 1 && PREFIX_WORDS.has(words[0])) words.shift();
  return words.join(' ');
}

const COUNTY_ALIASES = { bucharest: 'bucuresti', 'municipiul bucuresti': 'bucuresti', 'mun bucuresti': 'bucuresti' };

/** County name → comparable key: "Jud. Bistrița-Năsăud" → "bistrita nasaud", "Bucharest" → "bucuresti". */
export function normCounty(s) {
  const n = normalizeText(s).replace(/^(judetul|judet|jud)\s+/, '');
  return COUNTY_ALIASES[n] || n;
}

export function isBucharest(county, countyCode) {
  if (String(countyCode || '').toUpperCase() === 'B') return true;
  return normCounty(county) === 'bucuresti';
}

/** City text that can only mean București ("Bucuresti S3", "Sectorul 2"). */
export function cityLooksBucharest(city) {
  const c = stripPrefix(normalizeText(city));
  return /^(bucuresti|bucharest)\b/.test(c) || /^sector(ul)? ?[1-6]$/.test(c);
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
  const words = normalizeText(s).replace(new RegExp(SECTOR_RE.source, 'g'), ' ').trim();
  return stripPrefix(words);
}

const isBucharestQuery = (q) => isBucharest(q.county, q.countyCode)
  || (!q.county && !q.countyCode && cityLooksBucharest(q.city));

/**
 * Candidate spellings for what the customer typed, most specific first (normalized, with spaces).
 * "Sat Florești, Com. Florești" → ["floresti", "sat floresti"]; București + sector 3 →
 * ["bucuresti sector 3", "sector 3", "bucuresti sectorul 3", "sectorul 3", "bucuresti", "municipiul bucuresti"].
 * Later comma/paren parts ("Roșu, Chiajna" → "chiajna") come last; the county itself is never a variant.
 */
export function cityVariants(q) {
  return variantList(q).map((x) => x.v);
}

/** cityVariants with their kind: 'name' (what the customer typed first) or 'part' (a later comma/paren part). */
function variantList({ city, county, countyCode, sector, zip }) {
  const out = [];
  const add = (v, kind) => { if (v && !out.some((x) => x.v === v)) out.push({ v, kind }); };
  const bucharest = isBucharestQuery({ city, county, countyCode });
  const base = cleanCityName(city);
  // "Voluntari" typed with county București is NOT Bucharest (callers may retry in Ilfov).
  if (bucharest && (!base || /^(buc|bucharest)/.test(base))) {
    const s = detectSector({ city, sector, zip, bucharest });
    if (s) for (const v of [`bucuresti sector ${s}`, `sector ${s}`, `bucuresti sectorul ${s}`, `sectorul ${s}`]) add(v, 'name');
    add('bucuresti', 'name');
    add('municipiul bucuresti', 'name');
    return out;
  }
  add(base, 'name');
  add(normalizeText(String(city ?? '').split(',')[0]), 'name');
  const countyN = normCounty(county);
  const parts = String(city ?? '').split(/[,;/]|\(|\)/)
    .map((p) => stripPrefix(normalizeText(p).replace(new RegExp(SECTOR_RE.source, 'g'), ' ').trim()))
    .filter(Boolean);
  for (const p of parts.slice(1)) if (normCounty(p) !== countyN) add(p, 'part');
  return out;
}

/** Every key a nomenclator name can be matched under: full, prefix-stripped, and without "(Commune)". */
export function localityKeys(name) {
  const n = normalizeText(name);
  const base = normalizeText(String(name ?? '').replace(/\(.*?\)/g, ' '));
  return [...new Set([compactKey(n), compactKey(stripPrefix(n)), compactKey(base), compactKey(stripPrefix(base))])].filter(Boolean);
}

// ---------------------------------------------------------------- matching

const cleanZip = (z) => String(z ?? '').replace(/\D/g, '');
const isSectorName = (name) => /^(sectorul|sector) [1-6]$/.test(normalizeText(name));

function similarity(a, b) {
  if (!a || !b) return 0;
  let score = 1 - levenshtein(a, b) / Math.max(a.length, b.length);
  if (a.startsWith(b) || b.startsWith(a)) score += 0.15;
  else if (a.includes(b) || b.includes(a)) score += 0.05;
  return score;
}

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

/** Words of `text` (normalized) that are not administrative prefixes. */
const wordsOf = (text) => new Set(normalizeText(text).split(' ').filter((w) => w && !PREFIX_WORDS.has(w)));
const qualifierOf = (c) => {
  const paren = String(c.name ?? '').match(/\((.*?)\)/)?.[1];
  return normalizeText(paren || (c.parent && compactKey(c.parent) !== compactKey(c.name) ? c.parent : ''));
};

/** Commune the customer typed next to the village ("Valea Mare, com. Budești", "Alun Bosorod"). */
function disambiguateByParent(cands, city) {
  const typed = wordsOf(city);
  const hits = cands.filter((c) => {
    const q = qualifierOf(c);
    const words = q.split(' ').filter((w) => w && !PREFIX_WORDS.has(w));
    return words.length && words.every((w) => typed.has(w));
  });
  return hits.length === 1 ? hits[0] : null;
}

function resolveSameName(cands, q, via, opts) {
  const uniq = [...new Set(cands)];
  if (uniq.length === 1) return { match: uniq[0], via };
  const byZip = disambiguateByZip(uniq, q.zip);
  if (byZip) return { match: byZip, via: `${via}+zip` };
  const byParent = disambiguateByParent(uniq, q.city);
  if (byParent) return { match: byParent, via: `${via}+parent` };
  // Couriers that identify localities by name only (FAN) do not care which same-named entry we pick.
  if (opts.sameNameIsSame && new Set(uniq.map((c) => compactKey(c.name))).size === 1) return { match: uniq[0], via };
  return { ambiguous: uniq };
}

/**
 * Match a recipient locality against a courier nomenclator.
 * @param {{city:string, zip?:string, sector?:number, county?:string, countyCode?:string}} q
 * @param {{id?:any, name:string, postalCode?:string, parent?:string}[]} candidates  localities of ONE county
 *        (or of the whole country when the nomenclator has no county); `parent` = commune, if known
 * @param {{fuzzy?:boolean, sameNameIsSame?:boolean}} [opts]
 *        fuzzy: accept a unique one-letter typo on names ≥ 5 letters (off by default: "Bucium" and
 *        "Buciumi" are different villages);
 *        sameNameIsSame: same-named entries are interchangeable for this courier.
 * @returns {{match, via} | {ambiguous: object[]} | {notFound: true, suggestions: object[]}}
 */
export function matchLocality(q, candidates, opts = {}) {
  const cands = (candidates || []).filter((c) => c && c.name);
  const primary = new Map(); // full / prefix-stripped name
  const secondary = new Map(); // name without "(Commune)"
  const put = (map, k, c) => { if (!map.has(k)) map.set(k, []); if (!map.get(k).includes(c)) map.get(k).push(c); };
  for (const c of cands) {
    const n = normalizeText(c.name);
    put(primary, compactKey(n), c);
    put(primary, compactKey(stripPrefix(n)), c);
    for (const k of localityKeys(c.name)) if (!primary.has(k) || !primary.get(k).includes(c)) put(secondary, k, c);
  }

  // 1. Exact (diacritic/hyphen/prefix-insensitive) name, most specific variant first.
  for (const { v, kind } of variantList(q)) {
    const k = compactKey(v);
    const hit = primary.get(k) || secondary.get(k);
    if (hit) return resolveSameName(hit, q, kind, opts);
  }
  const bucharest = isBucharestQuery(q);
  const base = cleanCityName(q.city);
  if (bucharest && (!base || /^(buc|bucharest)/.test(base))) {
    // Nomenclator split by sector (Sameday "Sectorul 1..6") and we don't know which one.
    const sectors = cands.filter((c) => isSectorName(c.name));
    if (sectors.length) return { ambiguous: sectors.sort((a, b) => a.name.localeCompare(b.name)) };
  }

  // 2. Unique postal code (customer typed a neighbourhood but the zip is right).
  const z = cleanZip(q.zip);
  if (z.length === 6) {
    const zipHits = cands.filter((c) => cleanZip(c.postalCode) === z);
    if (zipHits.length === 1) return { match: zipHits[0], via: 'zip' };
  }

  // 3. A nomenclator name appearing as whole words inside what the customer typed
  //    ("Voluntari Pipera", "Ploiesti Prahova", "Sat Rosu Com Chiajna" → one unique name).
  const typed = ` ${normalizeText(q.city)} `;
  const byName = new Map();
  for (const c of cands) {
    const n = normalizeText(String(c.name).replace(/\(.*?\)/g, ' '));
    if (n.length >= 4 && typed.includes(` ${n} `)) put(byName, compactKey(n), c);
  }
  if (byName.size === 1) return resolveSameName([...byName.values()][0], q, 'contains', opts);

  // 4. One-letter typo on a reasonably long name ("Bucurest", "Constana") — opt-in.
  const qk = compactKey(base);
  if (opts.fuzzy && qk.length >= 5) {
    const close = new Map();
    for (const c of cands) for (const k of localityKeys(c.name)) if (levenshtein(k, qk) <= 1) put(close, compactKey(c.name), c);
    if (close.size === 1) return resolveSameName([...close.values()][0], q, 'typo', opts);
  }

  // Not found: up to 3 closest distinct names.
  const seen = new Map();
  for (const c of cands) {
    const s = Math.max(...localityKeys(c.name).map((k) => similarity(k, qk)));
    const key = compactKey(c.name);
    if (!seen.has(key) || seen.get(key).s < s) seen.set(key, { c, s });
  }
  const suggestions = [...seen.values()]
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
  const key = normCounty(county);
  const bucharest = isBucharest(county, countyCode);
  return counties.find((c) => {
    const k = normCounty(c.name);
    return (key && k === key) || (bucharest && k === 'bucuresti');
  }) || null;
}

// ---------------------------------------------------------------- errors

function labelFor(c, { sameNames, parentsDistinct }) {
  let s = c.name;
  if (sameNames) {
    const q = qualifierOf(c);
    if (parentsDistinct && q && !/\(/.test(c.name)) s = `${c.name} (${c.parent})`;
    else if (!parentsDistinct && c.postalCode) s = `${c.name} (cod ${c.postalCode})`;
  }
  if (c.countyLabel) s = `${s} (jud. ${c.countyLabel})`;
  return s;
}

/** ProcessingError for a locality the courier won't accept, with "Ai vrut: X, Y, Z?" suggestions. */
export function localityError({ provider, providerName, city, county, result }) {
  const ambiguous = result?.ambiguous;
  const options = (ambiguous || result?.suggestions || []).slice(0, 3);
  const sameNames = Boolean(ambiguous) && new Set(ambiguous.map((c) => compactKey(c.name))).size === 1;
  const parentsDistinct = sameNames && options.every((c) => qualifierOf(c))
    && new Set(options.map((c) => qualifierOf(c))).size === options.length;
  const isSectors = Boolean(ambiguous) && options.every((c) => isSectorName(c.name));
  const did = options.length ? `Ai vrut: ${[...new Set(options.map((c) => labelFor(c, { sameNames, parentsDistinct })))].join(', ')}? ` : '';
  const inCounty = county ? ` pentru județul ${county}` : '';
  let message;
  let fix;
  if (isSectors) {
    message = `Pentru București, ${providerName} cere sectorul, iar în adresă nu apare.`;
    fix = 'Adaugă sectorul în localitate (ex. „Sector 3”) sau codul poștal corect.';
  } else if (ambiguous) {
    message = `Localitatea „${city}” apare de mai multe ori în nomenclatorul ${providerName}${inCounty}.`;
    fix = 'Adaugă codul poștal corect (sau comuna) în adresă ca să alegem localitatea potrivită.';
  } else {
    message = `Localitatea „${city}” nu există în nomenclatorul ${providerName}${inCounty}.`;
    fix = 'Corectează localitatea (și județul) în adresa de livrare a comenzii.';
  }
  return new ProcessingError({
    code: 'ADDRESS_CITY_NOT_FOUND',
    message,
    hint: `${did}${fix}`,
    retryable: false,
    provider,
    field: 'shippingAddress.city',
    details: { city, county, options: options.map((c) => ({ id: c.id, name: c.name, postalCode: c.postalCode, parent: c.parent })) },
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

export function cityMissingError(provider) {
  return new ProcessingError({
    code: 'ADDRESS_CITY_MISSING',
    message: 'Lipsește localitatea destinatarului.',
    hint: 'Completează localitatea în adresa de livrare.',
    retryable: false,
    field: 'shippingAddress.city',
    provider,
  });
}

/**
 * Finds the recipient's locality in a whole-country nomenclator whose entries carry their county
 * (FAN, DPD). Searches the recipient's county; București ↔ Ilfov mix-ups are accepted on an exact
 * name only; when the county is unknown to the nomenclator, searches nationwide but only accepts a
 * name that is unique in the country (never guesses between counties).
 *
 * @param {object[]} items  raw nomenclator entries
 * @param {object} address  { city, county, countyCode?, sector?, zip? }
 * @param {object} o
 * @param {(it)=>string} o.nameOf
 * @param {(it)=>string} [o.countyOf]
 * @param {(it)=>string} [o.zipOf]
 * @param {(it)=>string} [o.parentOf]   commune, used to tell same-named villages apart
 * @param {string} o.provider           provider id for ProcessingError
 * @param {string} o.providerName       display name for messages
 * @returns the matching raw entry
 * @throws ProcessingError ADDRESS_CITY_MISSING / ADDRESS_CITY_NOT_FOUND
 */
export function findLocality(items, address, o) {
  const { nameOf, countyOf, zipOf, parentOf, provider, providerName, fuzzy = false, sameNameIsSame = false } = o;
  const city = String(address.city ?? '').trim();
  if (!city) throw cityMissingError(provider);
  const toCand = (it, countyLabel) => ({
    item: it,
    name: String(nameOf(it) ?? ''),
    postalCode: zipOf ? String(zipOf(it) ?? '') : '',
    parent: parentOf ? String(parentOf(it) ?? '') : '',
    ...(countyLabel ? { countyLabel: countyOf(it) } : {}),
  });
  const q = { city, zip: address.zip, sector: address.sector, county: address.county, countyCode: address.countyCode };
  const inCounty = (key) => items.filter((it) => normCounty(countyOf(it)) === key).map((it) => toCand(it));

  if (!countyOf || !(address.county || address.countyCode)) {
    const result = matchLocality(q, items.map((it) => toCand(it)), { fuzzy, sameNameIsSame });
    if (result.match) return result.match.item;
    throw localityError({ provider, providerName, city, county: address.county, result });
  }

  const key = normCounty(address.county) || (isBucharest(address.county, address.countyCode) ? 'bucuresti' : '');
  const pool = inCounty(key);
  if (!pool.length) {
    // County spelled differently in the nomenclator: nationwide, unique names only.
    const result = matchLocality(q, items.map((it) => toCand(it, true)), { fuzzy, sameNameIsSame: false });
    if (result.match) return result.match.item;
    throw localityError({ provider, providerName, city, county: address.county, result });
  }
  const result = matchLocality(q, pool, { fuzzy, sameNameIsSame });
  if (result.match) return result.match.item;
  // București ↔ Ilfov ("Voluntari, București", "București, Ilfov"): exact name in the neighbour only.
  const other = key === 'bucuresti' ? 'ilfov' : key === 'ilfov' ? 'bucuresti' : null;
  if (other && !result.ambiguous) {
    const otherCode = other === 'ilfov' ? 'IF' : 'B';
    const r2 = matchLocality({ ...q, county: other, countyCode: otherCode }, inCounty(other), { sameNameIsSame });
    if (r2.match && /^name/.test(r2.via)) return r2.match.item;
  }
  throw localityError({ provider, providerName, city, county: address.county, result });
}
