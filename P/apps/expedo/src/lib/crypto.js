import { createCipheriv, createDecipheriv, createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { config } from '../config.js';

const key = () => createHash('sha256').update(`expedo:${config.appSecret}`).digest();

/** AES-256-GCM. Output: base64(iv | tag | ciphertext). */
export function encrypt(plain) {
  const iv = randomBytes(12);
  const c = createCipheriv('aes-256-gcm', key(), iv);
  const enc = Buffer.concat([c.update(String(plain), 'utf8'), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), enc]).toString('base64');
}

export function decrypt(b64) {
  const buf = Buffer.from(b64, 'base64');
  const d = createDecipheriv('aes-256-gcm', key(), buf.subarray(0, 12));
  d.setAuthTag(buf.subarray(12, 28));
  return Buffer.concat([d.update(buf.subarray(28)), d.final()]).toString('utf8');
}

export function safeEqual(a, b) {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && timingSafeEqual(x, y);
}

export const hmacHex = (secret, data) => createHmac('sha256', secret).update(data).digest('hex');
export const hmacBase64 = (secret, data) => createHmac('sha256', secret).update(data).digest('base64');
export const hmacBase64Url = (secret, data) => createHmac('sha256', secret).update(data).digest('base64url');

// ---- personal data at rest ----
// Columns holding customer data (orders.data, events.message...) are stored as 'enc1:' + encrypt(...).
// Rows written by older versions are plaintext; open*() still reads them until the migration in
// db.js has re-saved them encrypted.
const SEALED = 'enc1:';
export const isSealed = (s) => typeof s === 'string' && s.startsWith(SEALED);
export const sealText = (s) => (s == null ? null : SEALED + encrypt(s));
export const openText = (s) => (isSealed(s) ? decrypt(s.slice(SEALED.length)) : s);
export const sealJson = (v) => (v === undefined || v === null ? null : sealText(JSON.stringify(v)));
export function openJson(s, fallback) {
  if (s == null || s === '') return fallback;
  try { return JSON.parse(openText(s)); } catch { return fallback; }
}

/**
 * Keyed hash ("blind index") for exact-match lookups on encrypted data: same phone → same hash,
 * but without APP_SECRET the hash says nothing. Scoped per store so two merchants' customers
 * can never be linked. Own key, derived separately from the encryption key.
 */
const indexKey = () => createHash('sha256').update(`expedo-index:${config.appSecret}`).digest();
export const blindIndex = (scope, term) => createHmac('sha256', indexKey()).update(`${scope}|${term}`).digest('hex').slice(0, 32);
