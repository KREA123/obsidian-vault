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
