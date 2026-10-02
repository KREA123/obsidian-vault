import { randomBytes } from 'node:crypto';
import { config } from '../config.js';
import { hmacHex, hmacBase64, hmacBase64Url, safeEqual } from '../lib/crypto.js';

// Shopify OAuth (install from outside the admin), session-token verification (embedded
// app inside the admin) and token exchange (embedded install without redirects).

export const isValidShop = (shop) => /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/i.test(String(shop || ''));

export function installUrl(shop, state) {
  const p = new URLSearchParams({
    client_id: config.shopify.apiKey,
    scope: config.shopify.scopes,
    redirect_uri: `${config.appUrl}/auth/callback`,
    state,
  });
  return `https://${shop}/admin/oauth/authorize?${p}`;
}

export const newState = () => randomBytes(16).toString('hex');

/** Verifies the `hmac` query param Shopify adds to OAuth callbacks and app loads. */
export function verifyQueryHmac(query) {
  const { hmac, signature, ...rest } = query;
  if (!hmac) return false;
  const message = Object.keys(rest).sort().map((k) => `${k}=${Array.isArray(rest[k]) ? rest[k].join(',') : rest[k]}`).join('&');
  return safeEqual(hmacHex(config.shopify.apiSecret, message), hmac);
}

export function verifyWebhookHmac(rawBody, header) {
  if (!header || !config.shopify.apiSecret) return false;
  return safeEqual(hmacBase64(config.shopify.apiSecret, rawBody), header);
}

async function tokenRequest(shop, body) {
  const res = await fetch(`https://${shop}/admin/oauth/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ client_id: config.shopify.apiKey, client_secret: config.shopify.apiSecret, ...body }),
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) throw new Error(`Shopify token request failed: ${res.status} ${await res.text()}`);
  return res.json(); // { access_token, scope }
}

export const exchangeCode = (shop, code) => tokenRequest(shop, { code });

/** Stores owned by the app's own organization: token via client credentials (valid ~24h, no user involved). */
export const clientCredentialsToken = (shop) => tokenRequest(shop, { grant_type: 'client_credentials' });

/** Embedded apps: swap an App Bridge session token for an offline Admin API token. */
export const exchangeSessionToken = (shop, sessionToken) => tokenRequest(shop, {
  grant_type: 'urn:ietf:params:oauth:grant-type:token-exchange',
  subject_token: sessionToken,
  subject_token_type: 'urn:ietf:params:oauth:token-type:id_token',
  requested_token_type: 'urn:shopify:params:oauth:token-type:offline-access-token',
});

/** Verifies an App Bridge session token (HS256 JWT signed with the app secret). Returns the shop or null. */
export function verifySessionToken(token) {
  const parts = String(token || '').split('.');
  if (parts.length !== 3 || !config.shopify.apiSecret) return null;
  const [h, p, sig] = parts;
  if (!safeEqual(hmacBase64Url(config.shopify.apiSecret, `${h}.${p}`), sig)) return null;
  let payload;
  try { payload = JSON.parse(Buffer.from(p, 'base64url').toString('utf8')); } catch { return null; }
  const now = Math.floor(Date.now() / 1000);
  if (payload.aud !== config.shopify.apiKey) return null;
  if (!payload.exp || payload.exp < now - 5) return null;
  if (payload.nbf && payload.nbf > now + 5) return null;
  const shop = String(payload.dest || '').replace(/^https:\/\//, '');
  return isValidShop(shop) ? { shop, payload } : null;
}

// ---- standalone dashboard session (signed cookie) ----
export function signSession(data) {
  const body = Buffer.from(JSON.stringify(data)).toString('base64url');
  return `${body}.${hmacBase64Url(config.sessionSecret, body)}`;
}
export function readSession(cookie) {
  const [body, sig] = String(cookie || '').split('.');
  if (!body || !sig || !safeEqual(hmacBase64Url(config.sessionSecret, body), sig)) return null;
  try {
    const data = JSON.parse(Buffer.from(body, 'base64url').toString('utf8'));
    return data.exp && data.exp < Date.now() ? null : data;
  } catch { return null; }
}
