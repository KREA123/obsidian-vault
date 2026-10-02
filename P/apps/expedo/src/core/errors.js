import { t, has, m } from '../i18n/index.js';

// Every failure the merchant can see goes through ProcessingError: a stable `code`, a short message,
// a concrete hint on how to fix it, and whether retrying can help.
// Silent failures and raw API dumps are what make other connectors painful.
//
// The text is NOT stored on the error: `key` names a catalog entry with `.message` and (optionally)
// `.hint` (default `errors.<CODE>`), `params` fill it, and renderError() turns it into text in the
// viewer's language when it is shown (API answer, order page). The raw provider answer stays in `details`.

export class ProcessingError extends Error {
  /**
   * @param {object} p
   * @param {string} p.code       stable machine code, e.g. 'ADDRESS_CITY_NOT_FOUND'
   * @param {string} [p.key]      catalog entry with .message / .hint (default `errors.<code>`)
   * @param {object} [p.params]   values for the message and hint ({param} placeholders)
   * @param {string} [p.hintKey]  full catalog key of a hint that replaces `<key>.hint`
   * @param {string} [p.message]  raw text instead of a key (tests, legacy rows); shown as is
   * @param {string} [p.hint]     raw hint, with p.message
   * @param {boolean} [p.retryable] true when the same call may succeed later (network, 5xx, rate limit)
   * @param {string} [p.provider] 'cargus', 'smartbill', 'shopify'...
   * @param {string} [p.field]    order field to fix, e.g. 'shippingAddress.city'
   * @param {any} [p.details]     raw provider response, kept for the log, never shown as the main message
   */
  constructor({ code, key, params, hintKey, message, hint, retryable = false, provider, field, details } = {}) {
    const k = key || (message == null ? `errors.${code}` : undefined);
    const p = params || {};
    // Error.message / .hint in English: what ends up in server logs and job rows.
    super(k ? t('en', `${k}.message`, p) : String(message));
    this.name = 'ProcessingError';
    this.code = code;
    this.key = k;
    this.params = p;
    this.hintKey = hintKey;
    this.raw = k ? undefined : { message: String(message), hint };
    this.hint = k ? renderHint('en', k, hintKey, p) : hint;
    this.retryable = retryable;
    this.provider = provider;
    this.field = field;
    this.details = details;
  }

  /** Language-neutral form, stored on the order (last_error) and in job rows. */
  toJSON() {
    return {
      code: this.code,
      ...(this.key ? { key: this.key, params: this.params, ...(this.hintKey ? { hintKey: this.hintKey } : {}) } : { message: this.raw.message, hint: this.raw.hint }),
      retryable: this.retryable,
      provider: this.provider,
      field: this.field,
      details: this.details,
    };
  }

  /** { message, hint } in a language ('en' | 'ro'). */
  render(locale) {
    return renderError(this, locale);
  }
}

function renderHint(locale, key, hintKey, params) {
  if (hintKey) return t(locale, hintKey, params);
  return has(`${key}.hint`) ? t(locale, `${key}.hint`, params) : undefined;
}

/**
 * Error (ProcessingError, its JSON, or a validation issue { level, code, key, params }) → the same
 * object with `message` and `hint` as text in `locale`. Rows written before the catalog existed carry
 * their Romanian text in message/hint and no key: shown as they are.
 */
export function renderError(e, locale) {
  if (!e) return e;
  const j = typeof e.toJSON === 'function' ? e.toJSON() : e;
  const { key, params, hintKey, ...rest } = j;
  if (!key) return { ...rest };
  return { ...rest, message: t(locale, `${key}.message`, params || {}), hint: renderHint(locale, key, hintKey, params || {}) };
}

/** The error as a message object { key, params } (for event rows: "Couldn't …: {error}"). */
export function errorMessage(e) {
  const j = typeof e?.toJSON === 'function' ? e.toJSON() : e || {};
  return j.key ? m(`${j.key}.message`, j.params) : m('errors.raw', { text: j.message || String(e) });
}

/** The hint as a message object, or undefined. */
export function errorHint(e) {
  const j = typeof e?.toJSON === 'function' ? e.toJSON() : e || {};
  if (j.hintKey) return m(j.hintKey, j.params);
  if (j.key) return has(`${j.key}.hint`) ? m(`${j.key}.hint`, j.params) : undefined;
  return j.hint ? m('errors.raw', { text: j.hint }) : undefined;
}

export function toProcessingError(err, provider) {
  if (err instanceof ProcessingError) return err;
  return new ProcessingError({
    code: 'UNEXPECTED',
    key: provider ? 'errors.UNEXPECTED_AT' : 'errors.UNEXPECTED',
    params: { provider, text: String(err?.message || err) },
    retryable: true,
    provider,
    details: err?.stack,
  });
}

export const authError = (provider, details) =>
  new ProcessingError({ code: 'AUTH_FAILED', params: { provider }, retryable: false, provider, details });
