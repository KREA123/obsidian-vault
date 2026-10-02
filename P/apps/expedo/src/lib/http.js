import { ProcessingError, authError } from '../core/errors.js';

// Thin fetch wrapper shared by every provider adapter. Adapters receive it as ctx.http
// so tests can swap in a fake without touching globals.

/**
 * @param {string} provider  display name used in error messages
 * @param {string} url
 * @param {object} [opts]
 * @param {string} [opts.method]
 * @param {object} [opts.headers]
 * @param {any}    [opts.json]      body serialized as JSON
 * @param {string|URLSearchParams|Buffer} [opts.body]
 * @param {'json'|'text'|'buffer'} [opts.responseType]  default 'json' (falls back to text when not JSON)
 * @param {number} [opts.timeoutMs]
 * @param {(status:number, body:any) => ProcessingError|undefined} [opts.mapError]  provider-specific error mapping
 * @returns {Promise<{status:number, headers:Headers, body:any}>}
 */
export async function request(provider, url, opts = {}) {
  const { method = 'GET', headers = {}, json, body, responseType = 'json', timeoutMs = 30000, mapError } = opts;
  const h = { Accept: 'application/json', ...headers };
  let payload = body;
  if (json !== undefined) {
    payload = JSON.stringify(json);
    h['Content-Type'] ??= 'application/json';
  }

  let res;
  try {
    res = await fetch(url, { method, headers: h, body: payload, signal: AbortSignal.timeout(timeoutMs) });
  } catch (err) {
    const timedOut = err?.name === 'TimeoutError' || err?.name === 'AbortError';
    throw new ProcessingError({
      code: timedOut ? 'PROVIDER_TIMEOUT' : 'PROVIDER_UNREACHABLE',
      params: { provider, seconds: Math.round(timeoutMs / 1000) },
      retryable: true,
      provider,
      details: String(err?.cause?.message || err?.message || err),
    });
  }

  let parsed;
  if (responseType === 'buffer') {
    parsed = Buffer.from(await res.arrayBuffer());
  } else {
    const text = await res.text();
    if (responseType === 'text') parsed = text;
    else {
      try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
    }
  }

  if (!res.ok) {
    const mapped = mapError?.(res.status, parsed);
    if (mapped) throw mapped;
    if (res.status === 401 || res.status === 403) throw authError(provider, parsed);
    if (res.status === 429 || res.status >= 500) {
      throw new ProcessingError({
        code: res.status === 429 ? 'PROVIDER_RATE_LIMIT' : 'PROVIDER_DOWN',
        params: { provider, status: res.status },
        retryable: true,
        provider,
        details: parsed,
      });
    }
    // The provider's own words stay verbatim, quoted ("Cargus says: …").
    const said = extractMessage(parsed);
    throw new ProcessingError({
      code: 'PROVIDER_REJECTED',
      key: said ? 'errors.PROVIDER_REJECTED' : 'errors.PROVIDER_REJECTED_STATUS',
      params: { provider, text: said, status: res.status },
      retryable: false,
      provider,
      details: parsed,
    });
  }
  return { status: res.status, headers: res.headers, body: parsed };
}

/** Best-effort human message out of an arbitrary provider error body. */
export function extractMessage(body) {
  if (body == null) return '';
  if (typeof body === 'string') return body.slice(0, 300);
  if (Buffer.isBuffer(body)) return '';
  for (const k of ['errorText', 'message', 'Message', 'error', 'Error', 'errors', 'Errors', 'title', 'detail']) {
    const v = body[k];
    if (!v) continue;
    if (typeof v === 'string') return v.slice(0, 300);
    if (Array.isArray(v)) return v.map((x) => (typeof x === 'string' ? x : extractMessage(x))).filter(Boolean).join('; ').slice(0, 300);
    if (typeof v === 'object') return extractMessage(v) || JSON.stringify(v).slice(0, 300);
  }
  return '';
}
