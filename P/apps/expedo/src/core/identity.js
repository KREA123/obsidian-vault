import { blindIndex } from '../lib/crypto.js';
import { normalizePhone, fold } from './address.js';

// Who the customer of an order is, without storing who they are: keyed hashes of the normalized
// phone, e-mail and name words. Used for search (the order data itself is encrypted) and for the
// customer's refusal history. Pure functions; the hashes are saved on the order row by db.js.

/** "+40 722 334 455", "0722334455", "0040722334455" → "0722334455". '' when it isn't a phone. */
export function phoneKey(input) {
  const p = normalizePhone(input);
  return p.phone.replace(/\D/g, '').length >= 9 ? p.phone : '';
}

export function emailKey(input) {
  const s = String(input ?? '').trim().toLowerCase();
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s) ? s : '';
}

/** "Andreea Popescu-Ionescu" → ['andreea', 'popescu', 'ionescu'] (lowercase, no diacritics). */
export const nameWords = (s) => fold(s).split(' ').filter((w) => w.length >= 2);

const hash = (storeId, kind, value) => (value ? blindIndex(`store:${storeId}`, `${kind}:${value}`) : null);
export const phoneHash = (storeId, phone) => hash(storeId, 'p', phoneKey(phone));
export const emailHash = (storeId, email) => hash(storeId, 'e', emailKey(email));

/**
 * Hashes stored on an order row:
 *   phoneHash, emailHash — the customer, for the refusal history (exact match)
 *   searchTerms          — every phone / e-mail / name word, space-separated, for the search box
 */
export function orderIdentity(storeId, data = {}, overrides = {}) {
  const ship = data.shippingAddress || {};
  const bill = data.billingAddress || {};
  const fix = overrides?.address || {};
  // A phone fixed by hand is the one the courier calls, so it identifies the customer best.
  const phones = [fix.phone, ship.phone, data.phone, bill.phone].map(phoneKey).filter(Boolean);
  const email = emailKey(data.email);
  const terms = new Set();
  for (const p of phones) terms.add(hash(storeId, 'p', p));
  if (email) terms.add(hash(storeId, 'e', email));
  for (const n of [data.customerName, ship.name, ship.firstName, ship.lastName, bill.name, bill.firstName, bill.lastName, fix.name, ship.company, data.company?.name]) {
    for (const w of nameWords(n)) terms.add(hash(storeId, 'n', w));
  }
  return {
    phoneHash: phones.length ? hash(storeId, 'p', phones[0]) : null,
    emailHash: email ? hash(storeId, 'e', email) : null,
    searchTerms: terms.size ? [...terms].join(' ') : null,
  };
}

/**
 * What to look for when the merchant types `q` in the search box:
 *   any   — a phone or e-mail hash; one match is enough
 *   words — name-word hashes; the order must have all of them ("Andreea Popescu")
 */
export function searchHashes(storeId, q) {
  const text = String(q ?? '').trim();
  const any = [];
  if (/^[\d\s+().-]+$/.test(text) && phoneKey(text)) any.push(hash(storeId, 'p', phoneKey(text)));
  if (emailKey(text)) any.push(hash(storeId, 'e', emailKey(text)));
  const words = text.includes('@') ? [] : [...new Set(nameWords(text))].map((w) => hash(storeId, 'n', w));
  return { any, words };
}
