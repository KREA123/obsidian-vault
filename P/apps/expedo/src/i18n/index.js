import en from './en.js';
import ro from './ro.js';
import { createTranslator, flatten, normalizeLocale, m, isMessage, formatMoney, formatDate, formatDay, LOCALES, DEFAULT_LOCALE } from './core.js';

// Server side of the i18n module: the two catalogs, t(), and how a request's language is chosen.
//   - inside the Shopify admin: the admin user's language (App Bridge `shopify.config.locale`, or the
//     `locale` query param Shopify adds), sent by the SPA in the X-Expedo-Locale header;
//   - standalone dashboard: the store setting "Language" (Settings → General), English by default.
// Romanian for anything starting with "ro", English otherwise.

export const catalogs = { en: flatten(en), ro: flatten(ro) };
export const { t, has } = createTranslator(catalogs);
export { normalizeLocale, m, isMessage, formatMoney, formatDate, formatDay, LOCALES, DEFAULT_LOCALE };

/** Keys the SPA needs (it renders everything under `ui.`; the server renders the rest). */
export function clientCatalog(locale) {
  const loc = LOCALES.includes(locale) ? locale : DEFAULT_LOCALE;
  const out = {};
  for (const [k, v] of Object.entries(catalogs[DEFAULT_LOCALE])) if (k.startsWith('ui.')) out[k] = catalogs[loc][k] ?? v;
  return out;
}

/** The store's own language (standalone dashboard, background work): settings.language, default English. */
export function storeLocale(store) {
  const lang = store?.settings?.language;
  return LOCALES.includes(lang) ? lang : DEFAULT_LOCALE;
}

/** Language for one API request. `embeddedLocale` = what the Shopify admin says (header / query). */
export function requestLocale({ embedded, embeddedLocale, store }) {
  if (embedded && embeddedLocale) return normalizeLocale(embeddedLocale);
  return storeLocale(store);
}

/** Pages outside the app (install errors): the browser's preferred language. */
export function acceptLanguageLocale(header) {
  const first = String(header || '').split(',')[0];
  return normalizeLocale(first);
}

/** "Name: …" for a field label coming from the catalog of an adapter (`<provider>.fields.<key>`). */
export function fieldText(locale, provider, field, part) {
  const key = `${provider}.fields.${field}.${part}`;
  return has(key) ? t(locale, key) : undefined;
}
