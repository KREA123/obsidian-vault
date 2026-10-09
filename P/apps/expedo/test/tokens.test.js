import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { config } from '../src/config.js';
import * as db from '../src/db.js';
import { shopifyClient, migrateLegacyToken } from '../src/shopify/client.js';
import { exchangeSessionToken, exchangeCode, tokenFields } from '../src/shopify/auth.js';

// Expiring offline tokens: requested with expiring=1, renewed with the refresh token before they
// expire (once per store, even with parallel requests), legacy non-expiring tokens migrated, and a
// dead refresh token clears the store's token so the next app open runs token exchange again.

const realFetch = globalThis.fetch;
let tokenCalls, gqlTokens, tokenAnswer, seq;

before(() => {
  Object.assign(config.shopify, { apiKey: 'key-tok', apiSecret: 'secret-tok', ownStores: [] });
  db.openDb(':memory:');
  globalThis.fetch = async (url, opts) => {
    const u = String(url);
    if (u.endsWith('/admin/oauth/access_token')) {
      const params = Object.fromEntries(new URLSearchParams(String(opts.body)));
      tokenCalls.push({ contentType: opts.headers['Content-Type'], ...params });
      const [status, body] = tokenAnswer(params);
      return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
    }
    if (u.endsWith('/graphql.json')) {
      const token = opts.headers['X-Shopify-Access-Token'];
      gqlTokens.push(token);
      if (token.startsWith('dead')) return new Response('{"errors":"[API] Invalid API key or access token"}', { status: 401 });
      return new Response(JSON.stringify({ data: { shop: { id: 'gid://shopify/Shop/1', name: 'Tok shop' } } }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return realFetch(url, opts);
  };
});
after(() => { globalThis.fetch = realFetch; });
beforeEach(() => {
  tokenCalls = [];
  gqlTokens = [];
  seq = 0;
  tokenAnswer = () => [200, pair()];
});

const pair = () => ({ access_token: `new-${++seq}`, scope: 'read_orders', expires_in: 3600, refresh_token: `refresh-${seq}`, refresh_token_expires_in: 7776000 });
const inMinutes = (min) => new Date(Date.now() + min * 60_000).toISOString();
const newStore = (shop, fields) => db.upsertStore({ shop, scopes: 'read_orders', ...fields });

test('token exchange and the authorization code grant ask for expiring tokens (form-encoded)', async () => {
  await exchangeSessionToken('a.myshopify.com', 'id-token');
  await exchangeCode('a.myshopify.com', 'the-code');
  const [ex, code] = tokenCalls;
  assert.equal(ex.contentType, 'application/x-www-form-urlencoded');
  assert.equal(ex.grant_type, 'urn:ietf:params:oauth:grant-type:token-exchange');
  assert.equal(ex.subject_token, 'id-token');
  assert.equal(ex.requested_token_type, 'urn:shopify:params:oauth:token-type:offline-access-token');
  assert.equal(ex.expiring, '1');
  assert.equal(ex.client_id, 'key-tok');
  assert.equal(code.code, 'the-code');
  assert.equal(code.expiring, '1');
});

test('tokenFields: expiry times from the response; none for a non-expiring token', () => {
  const now = Date.parse('2026-10-09T12:00:00Z');
  assert.deepEqual(tokenFields({ access_token: 'a', scope: 's', expires_in: 3600, refresh_token: 'r', refresh_token_expires_in: 7776000 }, now), {
    accessToken: 'a', scopes: 's', refreshToken: 'r', tokenExpiresAt: '2026-10-09T13:00:00.000Z', refreshExpiresAt: '2027-01-07T12:00:00.000Z',
  });
  assert.equal(tokenFields({ access_token: 'a' }, now).tokenExpiresAt, null);
});

test('a valid token is used as is; one about to expire is refreshed once, even with parallel requests', async () => {
  const s = newStore('fresh.myshopify.com', { accessToken: 'live-1', refreshToken: 'r-1', tokenExpiresAt: inMinutes(50), refreshExpiresAt: inMinutes(60 * 24 * 80) });
  await shopifyClient(s).shopInfo();
  assert.deepEqual(gqlTokens, ['live-1']);
  assert.equal(tokenCalls.length, 0);

  db.saveStoreToken(s.id, { accessToken: 'live-1', refreshToken: 'r-1', tokenExpiresAt: inMinutes(2) });
  const client = shopifyClient(db.getStore(s.id));
  await Promise.all([client.shopInfo(), client.shopInfo(), client.shopInfo()]);
  assert.equal(tokenCalls.length, 1, 'one refresh for three requests');
  assert.equal(tokenCalls[0].grant_type, 'refresh_token');
  assert.equal(tokenCalls[0].refresh_token, 'r-1');
  assert.deepEqual(gqlTokens.slice(1), ['new-1', 'new-1', 'new-1']);
  const saved = db.getStore(s.id);
  assert.equal(saved.accessToken, 'new-1');
  assert.equal(saved.refreshToken, 'refresh-1', 'the rotated refresh token replaces the old one');
  assert.ok(Date.parse(saved.token_expires_at) > Date.now() + 55 * 60_000);
});

test('Shopify rejects the token (401): refreshed once and retried', async () => {
  const s = newStore('rejected.myshopify.com', { accessToken: 'dead-1', refreshToken: 'r-9', tokenExpiresAt: inMinutes(40) });
  const shop = await shopifyClient(s).shopInfo();
  assert.equal(shop.name, 'Tok shop');
  assert.deepEqual(gqlTokens, ['dead-1', 'new-1']);
});

test('a refresh token Shopify no longer accepts clears the token: SHOPIFY_NOT_CONNECTED until the app is opened again', async () => {
  const s = newStore('gone.myshopify.com', { accessToken: 'live-2', refreshToken: 'r-old', tokenExpiresAt: inMinutes(1) });
  tokenAnswer = () => [401, { error: 'invalid_request', error_description: 'This request requires an active refresh_token' }];
  await assert.rejects(shopifyClient(s).shopInfo(), (err) => err.code === 'SHOPIFY_NOT_CONNECTED');
  const saved = db.getStore(s.id);
  assert.equal(saved.accessToken, null);
  assert.equal(saved.refreshToken, null);
});

test('a temporary refresh failure keeps using the token while it is still valid', async () => {
  const s = newStore('flaky.myshopify.com', { accessToken: 'live-3', refreshToken: 'r-3', tokenExpiresAt: inMinutes(3) });
  tokenAnswer = () => [503, { error: 'unavailable' }];
  await shopifyClient(s).shopInfo();
  assert.deepEqual(gqlTokens, ['live-3']);
  assert.equal(db.getStore(s.id).refreshToken, 'r-3', 'kept for the next try');
});

test('legacy non-expiring tokens are migrated to an expiring pair; other stores are left alone', async () => {
  const legacy = newStore('legacy.myshopify.com', { accessToken: 'old-forever' });
  assert.equal(await migrateLegacyToken(legacy), true);
  const call = tokenCalls[0];
  assert.equal(call.grant_type, 'urn:ietf:params:oauth:grant-type:token-exchange');
  assert.equal(call.subject_token, 'old-forever');
  assert.equal(call.subject_token_type, 'urn:shopify:params:oauth:token-type:offline-access-token');
  assert.equal(call.requested_token_type, 'urn:shopify:params:oauth:token-type:offline-access-token');
  assert.equal(call.expiring, '1');
  const saved = db.getStore(legacy.id);
  assert.equal(saved.accessToken, 'new-1');
  assert.equal(saved.refreshToken, 'refresh-1');

  assert.equal(await migrateLegacyToken(saved), false, 'already expiring');
  config.shopify.ownStores = ['own.myshopify.com'];
  assert.equal(await migrateLegacyToken(newStore('own.myshopify.com', { accessToken: 'x' })), false, 'own stores use client credentials');
  config.shopify.ownStores = [];
  assert.equal(tokenCalls.length, 1);
});
