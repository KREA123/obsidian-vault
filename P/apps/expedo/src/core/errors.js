// Every failure the merchant can see goes through ProcessingError: a plain-Romanian
// message, a concrete hint on how to fix it, and whether retrying can help.
// Silent failures and raw API dumps are what make other connectors painful.

export class ProcessingError extends Error {
  /**
   * @param {object} p
   * @param {string} p.code       stable machine code, e.g. 'ADDRESS_CITY_NOT_FOUND'
   * @param {string} p.message    what went wrong, in Romanian, for the merchant
   * @param {string} [p.hint]     what to do about it, in Romanian
   * @param {boolean} [p.retryable] true when the same call may succeed later (network, 5xx, rate limit)
   * @param {string} [p.provider] 'cargus', 'smartbill', 'shopify'...
   * @param {string} [p.field]    order field to fix, e.g. 'shippingAddress.city'
   * @param {any} [p.details]     raw provider response, kept for the log, never shown as the main message
   */
  constructor({ code, message, hint, retryable = false, provider, field, details }) {
    super(message);
    this.name = 'ProcessingError';
    this.code = code;
    this.hint = hint;
    this.retryable = retryable;
    this.provider = provider;
    this.field = field;
    this.details = details;
  }

  toJSON() {
    return {
      code: this.code,
      message: this.message,
      hint: this.hint,
      retryable: this.retryable,
      provider: this.provider,
      field: this.field,
      details: this.details,
    };
  }
}

export function toProcessingError(err, provider) {
  if (err instanceof ProcessingError) return err;
  return new ProcessingError({
    code: 'UNEXPECTED',
    message: `Eroare neașteptată${provider ? ` la ${provider}` : ''}: ${err?.message || err}`,
    hint: 'Încearcă din nou. Dacă se repetă, trimite-ne detaliile din jurnal.',
    retryable: true,
    provider,
    details: err?.stack,
  });
}

export const authError = (provider, details) =>
  new ProcessingError({
    code: 'AUTH_FAILED',
    message: `Conectarea la ${provider} a eșuat: utilizatorul, parola sau cheia API nu sunt acceptate.`,
    hint: `Verifică datele de conectare ${provider} în Setări → Integrări și apasă „Testează conexiunea”.`,
    retryable: false,
    provider,
    details,
  });
