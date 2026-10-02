import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from '../src/config.js';
import * as db from '../src/db.js';
import * as P from '../src/core/pipeline.js';
import { seedDemo } from '../src/demo/seed.js';
import { createApp } from '../src/server.js';
import { createTranslator, flatten, formatMoney, formatDate, formatDay, isPlural } from '../src/i18n/core.js';
import { t, m, catalogs, clientCatalog, normalizeLocale, requestLocale, storeLocale, acceptLanguageLocale } from '../src/i18n/index.js';
import { ProcessingError, renderError, toProcessingError, authError, errorMessage } from '../src/core/errors.js';
import { localityError } from '../src/couriers/locality.js';
import { validateAddress } from '../src/core/address.js';
import en from '../src/i18n/en.js';
import ro from '../src/i18n/ro.js';

// The i18n module (src/i18n): t(), plurals, fallback, formats, locale resolution, error and event
// rendering in both languages, catalog completeness, and the API answering in the viewer's language.

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

// ---------------------------------------------------------------- t()

test('t(): {param} interpolation, nested messages, arrays, missing params', () => {
  const { t: tr } = createTranslator({
    en: { hi: 'Hi {name}!', wrap: 'Error: {inner}', list: 'Pick: {items}', inner: 'bad {what}' },
  });
  assert.equal(tr('en', 'hi', { name: 'Ana' }), 'Hi Ana!');
  assert.equal(tr('en', 'wrap', { inner: { key: 'inner', params: { what: 'zip' } } }), 'Error: bad zip');
  assert.equal(tr('en', 'list', { items: ['a', { key: 'inner', params: { what: 'b' } }] }), 'Pick: a, bad b');
  assert.equal(tr('en', 'hi'), 'Hi !', 'a missing param renders empty, never "undefined"');
  assert.equal(tr('en', { key: 'hi', params: { name: 'Ion' } }), 'Hi Ion!', 'a message object works as the key');
});

test('t(): English fallback for a key missing in Romanian; unknown key shows the key; unknown locale → English', () => {
  const { t: tr, has } = createTranslator({ en: { only: 'English only', both: 'Both' }, ro: { both: 'Amândouă' } });
  assert.equal(tr('ro', 'both'), 'Amândouă');
  assert.equal(tr('ro', 'only'), 'English only');
  assert.equal(tr('ro', 'nope.missing'), 'nope.missing');
  assert.equal(tr('de', 'both'), 'Both');
  assert.ok(has('only') && !has('nope'));
  assert.equal(tr('en', ''), '');
});

test('plurals: English one/other, Romanian one/few/other ("2 colete", "20 de colete")', () => {
  const p = (loc, count) => t(loc, 'errors.CUSTOMER_REFUSED_BEFORE.message', { count, total: 9 });
  assert.equal(p('en', 1), 'The customer refused 1 parcel before (out of 9).');
  assert.equal(p('en', 2), 'The customer refused 2 parcels before (out of 9).');
  assert.equal(p('en', 0), 'The customer refused 0 parcels before (out of 9).');
  assert.equal(p('ro', 1), 'Clientul a refuzat 1 colet înainte (din 9).');
  assert.equal(p('ro', 2), 'Clientul a refuzat 2 colete înainte (din 9).');
  assert.equal(p('ro', 19), 'Clientul a refuzat 19 colete înainte (din 9).');
  assert.equal(p('ro', 20), 'Clientul a refuzat 20 de colete înainte (din 9).');
  assert.equal(p('ro', 102), 'Clientul a refuzat 102 colete înainte (din 9).');
  assert.equal(t('en', 'ui.orders.count', { count: 1 }), '1 order');
  assert.equal(t('en', 'ui.orders.count', { count: 21 }), '21 orders');
});

test('formats: money, date and day per language (Intl)', () => {
  const nb = (s) => s.replace(/ /g, ' ');
  assert.equal(nb(formatMoney('en', 1234.5)), 'RON 1,234.50');
  assert.equal(nb(formatMoney('ro', 1234.5)), '1.234,50 lei');
  assert.equal(nb(formatMoney('en', 9.9, 'EUR')), 'EUR 9.90');
  assert.equal(nb(formatMoney('ro', 9.9, 'EUR')), '9,90 EUR');
  // Wall-clock independent: compare with Intl directly for the same instant.
  const iso = '2026-10-02T11:05:00.000Z';
  assert.equal(formatDate('en', iso), new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }));
  assert.match(formatDate('en', iso), /^Oct 2, \d\d:05$/);
  assert.match(formatDate('ro', iso), /^02 oct\.?, \d\d:05$/);
  assert.match(formatDay('en', iso), /^Oct 2$/);
  assert.equal(formatDate('en', ''), '');
  assert.equal(nb(t('en', 'events.codCollected', { amount: 149.9, test: '' })), 'COD of RON 149.90 collected by the courier.');
  assert.equal(nb(t('ro', 'events.codCollected', { amount: 149.9, test: m('events.testSuffix') })), 'Ramburs de 149,90 lei încasat de curier (probă).');
});

// ---------------------------------------------------------------- locale resolution

test('locale resolution: Shopify admin language first (ro* → ro, anything else → en), else the store setting (default English)', () => {
  for (const [raw, want] of [['ro', 'ro'], ['ro-RO', 'ro'], ['RO', 'ro'], ['ro_MD', 'ro'], ['en', 'en'], ['en-US', 'en'], ['de', 'en'], ['', 'en'], [undefined, 'en'], ['rom', 'en']]) {
    assert.equal(normalizeLocale(raw), want, String(raw));
  }
  const storeRo = { settings: { language: 'ro' } };
  const storeDefault = { settings: {} };
  assert.equal(storeLocale(storeDefault), 'en');
  assert.equal(storeLocale(storeRo), 'ro');
  assert.equal(storeLocale({ settings: { language: 'fr' } }), 'en');
  assert.equal(requestLocale({ embedded: true, embeddedLocale: 'ro-RO', store: storeDefault }), 'ro');
  assert.equal(requestLocale({ embedded: true, embeddedLocale: 'en-GB', store: storeRo }), 'en', 'inside the admin the admin language wins');
  assert.equal(requestLocale({ embedded: true, embeddedLocale: '', store: storeRo }), 'ro', 'no admin language → store setting');
  assert.equal(requestLocale({ embedded: false, embeddedLocale: 'en', store: storeRo }), 'ro', 'standalone: the store setting');
  assert.equal(acceptLanguageLocale('ro-RO,ro;q=0.9,en;q=0.8'), 'ro');
  assert.equal(acceptLanguageLocale('en-US,en;q=0.9,ro;q=0.8'), 'en');
});

// ---------------------------------------------------------------- errors

test('ProcessingError: stable code + params; message/hint rendered in the viewer language; English on the Error itself', () => {
  const e = new ProcessingError({ code: 'ADDRESS_PHONE_INVALID', params: { phone: '0711' }, field: 'shippingAddress.phone' });
  assert.equal(e.code, 'ADDRESS_PHONE_INVALID');
  assert.equal(e.message, 'Phone number “0711” doesn’t look valid.');
  const j = e.toJSON();
  assert.deepEqual(Object.keys(j).sort(), ['code', 'details', 'field', 'key', 'params', 'provider', 'retryable']);
  assert.equal(j.message, undefined, 'no rendered text is stored');
  assert.equal(renderError(j, 'ro').message, 'Telefonul „0711” nu pare valid.');
  assert.equal(renderError(j, 'ro').hint, 'Un număr românesc are 10 cifre și începe cu 07, 02 sau 03.');
  assert.equal(renderError(j, 'en').hint, 'A Romanian number has 10 digits and starts with 07, 02 or 03.');
  assert.equal(new ProcessingError(j).render('ro').message, 'Telefonul „0711” nu pare valid.', 'round-trips through JSON (job rows, worker)');
});

test('errors: provider words stay verbatim, wrapped ("SmartBill says: …" / "SmartBill: …"); hint override; raw and legacy errors', () => {
  const said = new ProcessingError({ code: 'INVOICE_SERIES_NOT_FOUND', key: 'smartbill.errors.INVOICE_SERIES_NOT_FOUND', params: { text: 'Seria nu a fost gasita.' } });
  assert.equal(said.render('en').message, 'SmartBill says: “Seria nu a fost gasita.”');
  assert.equal(said.render('ro').message, 'SmartBill: Seria nu a fost gasita.');
  const generic = new ProcessingError({ code: 'PROVIDER_REJECTED', params: { provider: 'Oblio', text: 'Numele clientului lipseste' } });
  assert.equal(generic.render('en').message, 'Oblio rejected the request. Oblio says: “Numele clientului lipseste”');
  assert.equal(generic.render('ro').message, 'Oblio a refuzat cererea: Numele clientului lipseste');

  const timeout = new ProcessingError({ ...new ProcessingError({ code: 'PROVIDER_TIMEOUT', params: { provider: 'Cargus', seconds: 30 } }).toJSON(), hintKey: 'errors.ambiguousTimeout.awb' });
  assert.match(timeout.render('en').hint, /AWB may have been created anyway/);
  assert.match(timeout.render('ro').hint, /e posibil ca AWB-ul să fi fost creat/);

  const raw = new ProcessingError({ code: 'X', message: 'raw text', hint: 'raw hint' });
  assert.deepEqual([raw.render('ro').message, raw.render('en').hint], ['raw text', 'raw hint']);
  // last_error saved by an older version: Romanian text, no key → shown as it is.
  const legacy = { code: 'AUTH_FAILED', message: 'Conectarea la Cargus a eșuat.', hint: 'Verifică datele.', step: 'awb' };
  assert.deepEqual(renderError(legacy, 'en'), legacy);

  const unexpected = toProcessingError(new Error('boom'), 'cargus');
  assert.equal(unexpected.render('en').message, 'Unexpected error at cargus: boom');
  assert.equal(unexpected.render('ro').message, 'Eroare neașteptată la cargus: boom');
  assert.equal(authError('FGO').render('en').message, 'Couldn’t connect to FGO: the username, password or API key wasn’t accepted.');
  assert.deepEqual(errorMessage(authError('FGO')), { key: 'errors.AUTH_FAILED.message', params: { provider: 'FGO' } });
});

test('errors: locality suggestions ("Did you mean: X, Y?" / "Ai vrut: X, Y?") built from catalog keys with params', () => {
  const e = localityError({
    provider: 'cargus', providerName: 'Cargus', city: 'Floresti', county: 'Alba',
    result: { ambiguous: [{ id: 1, name: 'Floresti', postalCode: '517176' }, { id: 2, name: 'Floresti', postalCode: '515511' }] },
  });
  assert.equal(e.code, 'ADDRESS_CITY_NOT_FOUND');
  assert.equal(e.render('en').message, 'City “Floresti” appears more than once in the Cargus list of places for Alba County.');
  assert.equal(e.render('en').hint, 'Did you mean: Floresti (postal code 517176), Floresti (postal code 515511)? Add the right postal code (or the commune) to the address so we can pick the right place.');
  assert.equal(e.render('ro').message, 'Localitatea „Floresti” apare de mai multe ori în nomenclatorul Cargus pentru județul Alba.');
  assert.match(e.render('ro').hint, /^Ai vrut: Floresti \(cod 517176\), Floresti \(cod 515511\)\? Adaugă codul poștal/);
});

test('validation issues carry code + params, rendered per language', () => {
  const { issues } = validateAddress({ firstName: 'Ana', city: 'Cluj-Napoca', province: 'Cluj', address1: 'Str. X 1', phone: '0711', zip: '4000' });
  const phone = issues.find((i) => i.code === 'ADDRESS_PHONE_INVALID');
  assert.deepEqual(phone.params, { phone: '0711' });
  assert.equal(renderError(phone, 'en').message, 'Phone number “0711” doesn’t look valid.');
  assert.equal(renderError(phone, 'ro').level, 'error');
  const zip = issues.find((i) => i.code === 'ADDRESS_ZIP_INVALID');
  assert.equal(renderError(zip, 'ro').message, 'Codul poștal „4000” nu are 6 cifre.');
});

// ---------------------------------------------------------------- events

test('events: stored as key + params, rendered when read in either language; older text rows still shown', () => {
  const store = db.upsertStore({ shop: 'events-test.myshopify.com', name: 'E' });
  db.logEvent(store.id, null, 'success', 'awb', m('events.awbCreated', { awb: 'A1', courier: 'Cargus', test: m('events.testSuffix') }));
  db.logEvent(store.id, null, 'error', 'awb', errorMessage(new ProcessingError({ code: 'ADDRESS_PHONE_MISSING' })), { hint: m('errors.ADDRESS_PHONE_MISSING.hint'), code: 'ADDRESS_PHONE_MISSING' });
  db.logEvent(store.id, null, 'info', 'edit', 'Comanda a fost modificată manual.', { hint: 'text vechi' });
  const raw = db.getDb().prepare('SELECT key, message, params FROM events WHERE store_id = ? ORDER BY id').all(store.id);
  assert.equal(raw[0].key, 'events.awbCreated');
  assert.ok(!/A1/.test(raw[0].message) && !/A1/.test(raw[0].params), 'message and params are encrypted at rest');
  const [a, b, c] = db.storeEvents(store.id).reverse();
  assert.equal(db.renderEvent(a, 'en').message, 'AWB A1 created with Cargus (test).');
  assert.equal(db.renderEvent(a, 'ro').message, 'AWB A1 generat la Cargus (probă).');
  assert.equal(db.renderEvent(b, 'en').message, 'The recipient’s phone number is missing.');
  assert.equal(db.renderEvent(b, 'ro').data.hint, 'Curierii nu primesc AWB fără telefon. Adaugă-l în comandă.');
  assert.equal(db.renderEvent(c, 'en').message, 'Comanda a fost modificată manual.', 'pre-catalog row: stored text');
  assert.equal(db.renderEvent(c, 'en').data.hint, 'text vechi');
  db.logAccess(store.id, { actor: 'admin', action: 'cod_export', detail: m('access.detail.rows', { count: 3 }) });
  db.logAccess(store.id, { actor: 'admin', action: 'labels', detail: 'AWB 123' });
  const [d1, d2] = db.listAccess(store.id).rows;
  assert.equal(db.renderAccessDetail(d2.detail, 'en'), '3 rows');
  assert.equal(db.renderAccessDetail(d2.detail, 'ro'), '3 rânduri');
  assert.equal(db.renderAccessDetail(d1.detail, 'en'), 'AWB 123');
});

// ---------------------------------------------------------------- catalogs

const flatEn = flatten(en);
const flatRo = flatten(ro);
const placeholders = (v) => [...new Set((isPlural(v) ? Object.values(v).join(' ') : v).match(/\{(\w+)/g) || [])].sort();

test('catalog completeness: every key exists in both languages, same kind (text / plural), same {params}, nothing empty', () => {
  const onlyEn = Object.keys(flatEn).filter((k) => !(k in flatRo));
  const onlyRo = Object.keys(flatRo).filter((k) => !(k in flatEn));
  assert.deepEqual(onlyEn, [], 'missing in ro.js');
  assert.deepEqual(onlyRo, [], 'missing in en.js');
  for (const k of Object.keys(flatEn)) {
    const a = flatEn[k];
    const b = flatRo[k];
    assert.ok(isPlural(a) ? Object.values(a).every(Boolean) : a !== '', `empty en ${k}`);
    assert.ok(isPlural(b) ? Object.values(b).every(Boolean) : b !== '', `empty ro ${k}`);
    // A plural in one language may be plain text in the other (Romanian "{count} comenzi" for every count).
    assert.deepEqual(placeholders(a).filter((p) => p !== '{count'), placeholders(b).filter((p) => p !== '{count'), `params differ: ${k}`);
  }
  assert.ok(Object.keys(flatEn).length > 1000);
});

test('catalog: the SPA gets only the ui.* part, with English fallback', () => {
  const c = clientCatalog('ro');
  assert.ok(Object.keys(c).every((k) => k.startsWith('ui.')));
  assert.equal(c['ui.nav.orders'], 'Comenzi');
  assert.equal(clientCatalog('xx')['ui.nav.orders'], 'Orders');
});

// Every key the code names literally exists; no key in the catalogs is left unused (dynamic prefixes aside).
const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : /\.(js|html)$/.test(p) ? [p] : []; });
const SOURCES = [...walk(join(ROOT, 'src')).filter((f) => !/[/\\]i18n[/\\](en|ro)\.js$/.test(f)), join(ROOT, 'public/app.js'), join(ROOT, 'public/index.html')];
const code = SOURCES.map((f) => readFileSync(f, 'utf8')).join('\n');

test('catalog: every literal key used in the code exists', () => {
  const used = new Set();
  for (const re of [/(?<![.\w])m\(\s*'([a-z][\w.]*)'/gi, /(?<![.\w])t\(\s*(?:[\w.]+,\s*)?'([a-z][\w.]*)'/gi, /(?<![.\w])has\(\s*'([a-z][\w.]*)'/gi, /data-i18n(?:-href)?="([\w.]+)"/g, /:(ui\.[\w.]+)/g]) {
    for (const [, k] of code.matchAll(re)) used.add(k);
  }
  const keyed = new Set();
  // Error keys (catalog nodes with .message): dotted values of `key:`; adapter fields use plain `key: 'username'`.
  for (const [, k] of code.matchAll(/\bkey:\s*'([a-z]\w*\.[\w.]+)'/gi)) keyed.add(k);
  for (const [, k] of code.matchAll(/\bhintKey:\s*'([a-z][\w.]*)'/gi)) used.add(k);
  const missing = [...used].filter((k) => !(k in flatEn) && !/^[a-z]+$/.test(k));
  const missingNodes = [...keyed].filter((k) => !(`${k}.message` in flatEn));
  assert.deepEqual(missing, [], 'keys used with m()/t()');
  assert.deepEqual(missingNodes, [], 'error keys without .message');
  assert.ok(used.size > 200);
});

test('catalog: no unused keys (keys built at run time are matched by their prefix)', () => {
  const literals = new Set([...code.matchAll(/['"`]([a-z][\w.]*[\w])['"`]/gi)].map((x) => x[1]));
  for (const [, k] of code.matchAll(/data-i18n(?:-href)?="([\w.]+)"/g)) literals.add(k);
  for (const [, k] of code.matchAll(/:(ui\.[\w.]+)/g)) literals.add(k);
  // Prefixes of keys built from data: `status.${s}`, `${base}.label`, `errors.${code}`...
  const prefixes = [...code.matchAll(/`([a-z][\w.]*)\$\{/gi)].map((x) => x[1]).filter((p) => p.includes('.'));
  prefixes.push('errors.', 'rules.', 'access.actions.', 'status.', 'tracking.', 'events.source.');
  // Adapter fields: <provider>.fields.<key>.(label|help|options.*), looked up by the server for each adapter.
  for (const p of ['cargus', 'sameday', 'fancourier', 'gls', 'dpd', 'smartbill', 'fgo', 'oblio']) prefixes.push(`${p}.fields.`);
  const used = (k) => literals.has(k) || literals.has(k.replace(/\.(message|hint)$/, '')) || prefixes.some((p) => k.startsWith(p));
  const unused = Object.keys(flatEn).filter((k) => !used(k));
  assert.deepEqual(unused, []);
});

test('no Romanian text left in the code outside the catalogs (except data: counties, demo orders, legal pages)', () => {
  const allowFiles = /[/\\](i18n[/\\]ro\.js|legal\.js|demo[/\\]seed\.js|core[/\\]address\.js)$/;
  const found = [];
  for (const f of SOURCES.filter((x) => x.endsWith('.js') && !allowFiles.test(x))) {
    readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
      const s = line.trim();
      if (/^(\/\/|\*|\/\*)/.test(s)) return; // comments
      const literals = line.replace(/\s\/\/\s.*$/, '').match(/'[^'\n]*'|`[^`\n]*`|"[^"\n]*"/g) || [];
      for (const l of literals) {
        // en.js quotes the providers' own (Romanian) menu names; regexes match Romanian input.
        if (/[ăâîșțşţĂÂÎȘȚ]/.test(l) && !f.endsWith('en.js')) found.push(`${f.slice(ROOT.length + 1)}:${i + 1} ${l.slice(0, 60)}`);
      }
    });
  }
  assert.deepEqual(found, []);
});

// ---------------------------------------------------------------- API in the viewer's language

let server, base, demo, other;
const SECRET = 'i18n-secret';
function sessionToken(shop) {
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const h = b64({ alg: 'HS256', typ: 'JWT' });
  const p = b64({ dest: `https://${shop}`, aud: 'key-i18n', exp: now + 60, nbf: now - 1, sub: '42' });
  return `${h}.${p}.${createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url')}`;
}

before(async () => {
  Object.assign(config, { demo: true, adminPassword: '' });
  Object.assign(config.shopify, { apiSecret: SECRET, apiKey: 'key-i18n' });
  db.openDb(':memory:');
  ({ store: demo } = seedDemo());
  other = db.upsertStore({ shop: 'magazin-ro.myshopify.com', name: 'RO', accessToken: 'tok' });
  server = createApp().listen(0);
  await new Promise((r) => server.once('listening', r));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server?.close());

const get = async (path, headers = {}) => {
  const res = await fetch(base + path, { headers });
  const type = res.headers.get('content-type') || '';
  return { status: res.status, headers: res.headers, data: type.includes('json') ? await res.json() : await res.text() };
};
const put = (path, body) => fetch(base + path, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Expedo-Request': '1' }, body: JSON.stringify(body) }).then((r) => r.json());

test('API: demo store answers in English by default; the Language setting switches it to Romanian', async () => {
  const me = await get('/api/me');
  assert.equal(me.data.locale, 'en');
  const meta = await get('/api/meta');
  assert.equal(meta.data.statuses.needs_attention, 'Needs attention');
  assert.equal(meta.data.rules.ops.not_contains, 'doesn’t contain');
  assert.equal(meta.data.couriers.find((c) => c.id === 'cargus').credentialFields[0].label, 'API key (Primary key)');
  const order = db.getDb().prepare('SELECT id FROM orders WHERE store_id = ? AND name = ?').get(demo.id, '#1113').id;
  const en1 = await get(`/api/orders/${order}`);
  assert.equal(en1.data.order.issues[0].message, 'The recipient’s phone number is missing.');
  assert.equal(en1.data.order.statusLabel, 'Needs attention');
  assert.ok(en1.data.events.some((e) => /^Order #1113 imported from Shopify \(demo\)\.$/.test(e.message)));
  const missing = await get('/api/orders/999999');
  assert.deepEqual([missing.status, missing.data.error.code, missing.data.error.message], [404, 'ORDER_NOT_FOUND', 'Order not found.']);
  assert.match((await get('/api/cod.csv')).data, /^﻿?Order,Courier,AWB,COD amount/);

  const saved = await put('/api/settings', { settings: { language: 'ro' } });
  assert.equal(saved.settings.language, 'ro');
  assert.equal((await get('/api/me')).data.locale, 'ro');
  const ro1 = await get(`/api/orders/${order}`);
  assert.equal(ro1.data.order.issues[0].message, 'Lipsește telefonul destinatarului.');
  assert.equal(ro1.data.order.statusLabel, 'Necesită atenție');
  assert.ok(ro1.data.events.some((e) => e.message === 'Comanda #1113 a fost preluată din Shopify (demo).'));
  assert.equal((await get('/api/orders/999999')).data.error.message, 'Comanda nu există.');
  assert.equal((await get('/api/meta')).data.statuses.needs_attention, 'Necesită atenție');
  const csv = await get('/api/cod.csv');
  assert.match(csv.data, /Comanda,Curier,AWB,Ramburs/);
  assert.match(csv.headers.get('content-disposition'), /ramburs\.csv/);

  const bad = await put('/api/settings', { settings: { language: 'fr' } });
  assert.equal(bad.error.code, 'SETTINGS_INVALID');
  assert.equal(bad.error.message, 'Setare greșită: language.');
  await put('/api/settings', { settings: { language: 'en' } });
});

test('API: inside the Shopify admin the admin user\'s language wins (X-Expedo-Locale / ?locale=)', async () => {
  const auth = { Authorization: `Bearer ${sessionToken(other.shop)}` };
  assert.equal((await get('/api/me', { ...auth, 'X-Expedo-Locale': 'ro-RO' })).data.locale, 'ro');
  assert.equal((await get('/api/me', { ...auth, 'X-Expedo-Locale': 'en-US' })).data.locale, 'en');
  assert.equal((await get('/api/me?locale=ro', auth)).data.locale, 'ro');
  assert.equal((await get('/api/me', auth)).data.locale, 'en', 'no admin language: the store setting (English)');
  const nf = await get('/api/orders/999999', { ...auth, 'X-Expedo-Locale': 'ro' });
  assert.equal(nf.data.error.message, 'Comanda nu există.');
  // Before a store is known (bad token): the admin language too.
  const expired = await get('/api/me', { Authorization: 'Bearer x.y.z', 'X-Expedo-Locale': 'ro' });
  assert.deepEqual([expired.status, expired.data.error.message], [401, 'Sesiunea Shopify a expirat. Reîncarcă pagina.']);
});

test('i18n assets for the SPA: /i18n/core.js and /i18n/<locale>.json', async () => {
  const core = await get('/i18n/core.js');
  assert.match(core.headers.get('content-type'), /javascript/);
  assert.match(core.data, /export function createTranslator/);
  const cat = await get('/i18n/ro.json');
  assert.equal(cat.data['ui.dashboard.title'], 'Panou');
  assert.equal((await get('/i18n/en.json')).data['ui.dashboard.title'], 'Dashboard');
  assert.equal((await get('/i18n/xx.json')).status, 404);
});

test('processing results and tracking come back translated; tracking keeps the courier\'s own words apart', async () => {
  const id = db.getDb().prepare('SELECT id FROM orders WHERE store_id = ? AND name = ?').get(demo.id, '#1113').id;
  const res = await fetch(`${base}/api/orders/process`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Expedo-Request': '1' }, body: JSON.stringify({ ids: [id] }) }).then((r) => r.json());
  assert.equal(res.results[0].error.code, 'ADDRESS_PHONE_MISSING');
  assert.equal(res.results[0].error.message, 'The recipient’s phone number is missing.');
  const shipped = db.getDb().prepare(`SELECT id FROM orders WHERE store_id = ? AND awb IS NOT NULL LIMIT 1`).get(demo.id).id;
  db.updateOrder(shipped, { tracking_status: 'out_for_delivery', tracking_text: 'Predat curierului pentru livrare' });
  const o = (await get(`/api/orders/${shipped}`)).data.order;
  assert.equal(o.trackingText, 'Out for delivery');
  assert.equal(o.trackingDetail, 'Predat curierului pentru livrare');
  db.updateOrder(shipped, { tracking_text: 'În livrare' }); // an older row: our own Romanian label, not the courier's words
  assert.equal((await get(`/api/orders/${shipped}`)).data.order.trackingDetail, null);
  P.validateOrder(demo, shipped);
});

test('the English copy uses the agreed terms', () => {
  const text = Object.values(flatEn).map((v) => (isPlural(v) ? Object.values(v).join(' ') : v)).join('\n');
  assert.match(flatEn['ui.banner.text'], /Shipping labels \(AWBs\)/, 'AWB introduced on first mention');
  assert.match(text, /cash on delivery \(COD\)/i);
  assert.doesNotMatch(text, /\bcancelled\b/i, 'US English: canceled');
  assert.doesNotMatch(text, /\bmode de test\b|\btest-mode\b/);
  assert.equal(flatEn['status.needs_attention'], 'Needs attention');
  assert.equal(flatEn['status.on_hold'], 'On hold');
  assert.equal(flatEn['ui.settings.general.test'], 'Test');
});

test('every adapter field has a label (and every select option a text) in both languages', async () => {
  const { couriers } = await import('../src/couriers/index.js');
  const { invoicers } = await import('../src/invoicing/index.js');
  const missing = [];
  for (const a of [...Object.values(couriers), ...Object.values(invoicers)].filter((x) => x.id !== 'mock')) {
    for (const f of [...a.credentialFields, ...a.settingsFields]) {
      const base = `${a.id}.fields.${f.key}`;
      if (!(`${base}.label` in flatEn) || !(`${base}.label` in flatRo)) missing.push(`${base}.label`);
      for (const o of f.options || []) if (o.label == null && !(`${base}.options.${o.value}` in flatEn)) missing.push(`${base}.options.${o.value}`);
    }
  }
  assert.deepEqual(missing, []);
});
