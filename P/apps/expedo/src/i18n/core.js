// Tiny i18n engine, no dependencies, shared by the server (src/i18n/index.js) and the SPA
// (served as /i18n/core.js). Catalogs are nested objects of strings; a leaf can be:
//   'Text with {param}'                 interpolation
//   'Total: {amount, money}'            formatted param: money | number | date | day
//   { one: '1 parcel', other: '{count} parcels' }   plural, chosen by params.count (Intl.PluralRules;
//                                       Romanian also has `few`: "2 colete" vs "20 de colete")
// A param can itself be a message { key, params } (rendered in the same locale) or an array of them.

export const LOCALES = ['en', 'ro'];
export const DEFAULT_LOCALE = 'en';
const PLURAL_KEYS = new Set(['zero', 'one', 'two', 'few', 'many', 'other']);

/** 'ro', 'ro-RO', 'ro_MD' → 'ro'; anything else (en-US, de, '', undefined) → 'en'. */
export function normalizeLocale(raw) {
  return /^ro\b|^ro[-_]/i.test(String(raw ?? '').trim()) ? 'ro' : 'en';
}

export const isPlural = (v) => !!v && typeof v === 'object' && !Array.isArray(v) && 'other' in v
  && Object.keys(v).every((k) => PLURAL_KEYS.has(k)) && Object.values(v).every((x) => typeof x === 'string');

/** { a: { b: 'x' } } → { 'a.b': 'x' }; plural objects stay leaves. */
export function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj || {})) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === 'string' || isPlural(v)) out[key] = v;
    else if (v && typeof v === 'object') flatten(v, key, out);
  }
  return out;
}

/** A message to render later, in the viewer's language: stored in the DB, sent in API answers. */
export const m = (key, params) => (params && Object.keys(params).length ? { key, params } : { key });
export const isMessage = (v) => !!v && typeof v === 'object' && !Array.isArray(v) && typeof v.key === 'string';

const intlTag = (locale) => (locale === 'ro' ? 'ro-RO' : 'en-US');
const pluralRules = {};
function pluralCategory(locale, count) {
  pluralRules[locale] ||= new Intl.PluralRules(intlTag(locale));
  return pluralRules[locale].select(Number(count) || 0);
}

/** en: "RON 1,234.50"; ro: "1.234,50 lei" (as the app always showed it). */
export function formatMoney(locale, n, currency = 'RON') {
  const v = Number(n || 0).toLocaleString(intlTag(locale), { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const cur = String(currency || 'RON').toUpperCase();
  if (locale === 'ro') return cur === 'RON' ? `${v} lei` : `${v} ${cur}`;
  return `${cur} ${v}`;
}

export function formatNumber(locale, n, digits) {
  const opts = digits == null ? {} : { minimumFractionDigits: digits, maximumFractionDigits: digits };
  return Number(n || 0).toLocaleString(intlTag(locale), opts);
}

/** en: "Oct 2, 14:05"; ro: "02 oct., 14:05". */
export function formatDate(locale, s) {
  if (!s) return '';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '';
  return locale === 'ro'
    ? d.toLocaleString('ro-RO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
}

/** en: "Oct 2"; ro: "02 oct.". */
export function formatDay(locale, s) {
  if (!s) return '';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '';
  return locale === 'ro'
    ? d.toLocaleDateString('ro-RO', { day: '2-digit', month: 'short' })
    : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Builds t(locale, key, params) over flat catalogs { en: {...}, ro: {...} }. Missing keys fall back to
 * English, then to the key itself (visible, so a gap is noticed, never a crash).
 */
export function createTranslator(flatCatalogs) {
  const lookup = (locale, key) => flatCatalogs[locale]?.[key] ?? flatCatalogs[DEFAULT_LOCALE]?.[key];
  const has = (key, locale = DEFAULT_LOCALE) => lookup(locale, key) != null;

  function value(locale, v, format, params) {
    if (v == null) return '';
    if (Array.isArray(v)) return v.map((x) => value(locale, x, format, params)).join(', ');
    if (isMessage(v)) return t(locale, v.key, v.params);
    switch (format) {
      case 'money': return formatMoney(locale, v, params?.currency);
      case 'number': return formatNumber(locale, v);
      case 'decimal': return formatNumber(locale, v, 2);
      case 'date': return formatDate(locale, v);
      case 'day': return formatDay(locale, v);
      default: return String(v);
    }
  }

  function t(locale, key, params = {}) {
    if (isMessage(key)) return t(locale, key.key, key.params);
    if (key == null || key === '') return '';
    const loc = flatCatalogs[locale] ? locale : DEFAULT_LOCALE;
    let s = lookup(loc, key);
    if (s == null) return String(key);
    const p = params || {};
    if (typeof s === 'object') s = s[pluralCategory(loc, p.count)] ?? s.other;
    return s.replace(/\{(\w+)(?:,\s*(\w+))?\}/g, (_, name, format) => value(loc, p[name], format, p));
  }

  return { t, has };
}
