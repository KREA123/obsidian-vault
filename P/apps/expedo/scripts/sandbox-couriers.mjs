// Runs a REAL courier adapter end to end against the courier's servers, with a test account the
// courier itself publishes (or your own sandbox account). Credentials come ONLY from environment
// variables and are never written anywhere.
//
//   EXPEDO_SANDBOX_CREDENTIALS='{"username":"…","password":"…"}' \
//   EXPEDO_SANDBOX_SETTINGS='{"clientId":"…"}' \
//   node scripts/sandbox-couriers.mjs fancourier [--create] [--awb <awb>] [--record out.json] [--label out.pdf]
//
// Without --create only read-only calls run: testConnection, listPickupPoints, listServices and
// locality resolution for a few tricky addresses. With --create ONE shipment (with COD) is created
// for an obviously fake recipient ("Test Expedo", reference EXPEDO-TEST), its label is downloaded and
// checked to be a PDF, it is tracked and then CANCELLED straight away. --awb <awb> skips creation and
// runs label/track/cancel on an existing AWB (use it to clean up after an interrupted run).
//
// The recipient phone is 0700000000 unless EXPEDO_SANDBOX_PHONE is set: FAN Courier blacklists it
// ("app.awbGeneration.recipient.blacklistedPhone"), so for FAN use the phone from FAN's own documented
// AWB example (0723456789).
//
// --record writes every HTTP exchange (tokens, passwords and Authorization headers redacted, label
// bytes summarized) to a JSON file, to build test fixtures from.
//
// Safety: stops at the first authentication failure (GLS locks an account after ~5 failed logins).

import { writeFileSync } from 'node:fs';
import { request } from '../src/lib/http.js';
import { couriers } from '../src/couriers/index.js';
import { isPdf } from '../src/couriers/util.js';
import { t } from '../src/i18n/index.js';
import { resolveFanLocality } from '../src/couriers/fancourier.js';
import { resolveLocality as resolveCargus } from '../src/couriers/cargus.js';
import { resolveLocality as resolveSameday } from '../src/couriers/sameday.js';
import { resolveGlsAddress } from '../src/couriers/gls.js';
import { resolveDpdSite } from '../src/couriers/dpd.js';

const args = process.argv.slice(2);
const courierId = args[0];
const flag = (name) => args.includes(name);
const opt = (name) => { const i = args.indexOf(name); return i > 0 ? args[i + 1] : undefined; };

const adapter = couriers[courierId];
if (!adapter || courierId === 'mock') {
  console.error(`Usage: node scripts/sandbox-couriers.mjs <${Object.keys(couriers).filter((c) => c !== 'mock').join('|')}> [--create] [--awb <awb>] [--record file.json] [--label file.pdf]`);
  process.exit(2);
}

function envJson(name) {
  const raw = process.env[name];
  if (!raw) return {};
  try { return JSON.parse(raw); } catch { console.error(`${name} is not valid JSON`); process.exit(2); }
}
const credentials = envJson('EXPEDO_SANDBOX_CREDENTIALS');
const settings = envJson('EXPEDO_SANDBOX_SETTINGS');
if (!Object.keys(credentials).length) {
  console.error('Set EXPEDO_SANDBOX_CREDENTIALS (JSON with the adapter credential fields: '
    + `${adapter.credentialFields.map((f) => f.key).join(', ')}).`);
  process.exit(2);
}

// ---------------------------------------------------------------- recording http

const SECRET_KEY = /token|password|authorization|secret|apikey|subscription/i;
const secretValues = Object.values(credentials).filter((v) => typeof v === 'string' && v.length >= 3);

function redact(v, depth = 0) {
  if (depth > 12) return v;
  if (Buffer.isBuffer(v)) {
    return { _buffer: true, bytes: v.length, startsWith: v.subarray(0, 8).toString('latin1'), isPdf: isPdf(v) };
  }
  if (Array.isArray(v)) {
    // Big nomenclators: keep the shape, not 13 000 rows.
    if (v.length > 20) return [...v.slice(0, 5).map((x) => redact(x, depth + 1)), `… ${v.length - 5} more rows`];
    return v.map((x) => redact(x, depth + 1));
  }
  if (v && typeof v === 'object') {
    return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, SECRET_KEY.test(k) && x ? '<redacted>' : redact(x, depth + 1)]));
  }
  if (typeof v === 'string') {
    let s = v;
    for (const secret of secretValues) s = s.split(secret).join('<redacted>');
    if (s.length > 4000) s = `${s.slice(0, 4000)}… (${s.length} chars)`;
    return s;
  }
  return v;
}

function redactUrl(url) {
  const u = new URL(url);
  for (const k of [...u.searchParams.keys()]) if (SECRET_KEY.test(k)) u.searchParams.set(k, '<redacted>');
  return redact(u.toString());
}

const exchanges = [];
async function http(provider, url, opts = {}) {
  const entry = { at: new Date().toISOString(), method: opts.method || 'GET', url: redactUrl(url) };
  if (opts.json !== undefined) entry.json = redact(opts.json);
  else if (opts.body && !/login|auth/i.test(url)) entry.body = redact(String(opts.body));
  exchanges.push(entry);
  try {
    const res = await request(provider, url, opts);
    entry.status = res.status;
    entry.contentType = res.headers?.get?.('content-type') || undefined;
    entry.response = redact(res.body);
    return res;
  } catch (err) {
    entry.error = { code: err.code, message: err.message, details: redact(err.details) };
    throw err;
  }
}

const store = new Map();
const ctx = {
  credentials,
  settings,
  http,
  cache: {
    get: (k) => { const e = store.get(k); return e && e.exp > Date.now() ? e.v : undefined; },
    set: (k, v, ttl = 3600) => { store.set(k, { v, exp: Date.now() + ttl * 1000 }); },
  },
  log: (message, data) => console.log(`   log: ${message}`, data ? JSON.stringify(redact(data)).slice(0, 300) : ''),
};

// ---------------------------------------------------------------- checks

let failed = 0;
const check = (name, ok, extra = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? `  — ${extra}` : ''}`);
  if (!ok) failed++;
};

function finish(code) {
  const out = opt('--record');
  if (out) {
    writeFileSync(out, `${JSON.stringify({ courier: courierId, recordedAt: new Date().toISOString(), exchanges }, null, 2)}\n`);
    console.log(`Recorded ${exchanges.length} HTTP exchanges → ${out}`);
  }
  process.exit(code ?? (failed ? 1 : 0));
}

async function step(name, fn, { fatalOnAuth = true } = {}) {
  try {
    return await fn();
  } catch (err) {
    check(name, false, `${err.code || err.name}: ${err.message}${err.hint ? ` (${err.hint})` : ''}`);
    if (fatalOnAuth && err.code === 'AUTH_FAILED') {
      console.log('Authentication failed: stopping here (no further login attempts).');
      finish(1);
    }
    return undefined;
  }
}

const RESOLVERS = {
  fancourier: async (r) => { const x = await resolveFanLocality(ctx, r); return `${x.locality}, ${x.county}`; },
  cargus: async (r) => { const x = await resolveCargus(ctx, r); return JSON.stringify(x); },
  sameday: async (r) => { const x = await resolveSameday(ctx, r); return JSON.stringify(x); },
  gls: async (r) => { const x = await resolveGlsAddress(ctx, r); return JSON.stringify(x); },
  dpd: async (r) => { const x = await resolveDpdSite(ctx, r); return JSON.stringify(x); },
};

// Tricky addresses: București by sector, an Ilfov town next to it, and same-named villages.
const ADDRESSES = [
  { label: 'București Sector 3', r: { county: 'București', countyCode: 'B', city: 'București Sector 3', sector: 3, zip: '030167' }, expect: /bucuresti/i },
  { label: 'Voluntari, Ilfov', r: { county: 'Ilfov', countyCode: 'IF', city: 'Voluntari', zip: '077190' }, expect: /voluntari/i },
  { label: 'Alun, com. Bosorod (Hunedoara has two villages named Alun)', r: { county: 'Hunedoara', countyCode: 'HD', city: 'Alun, com. Bosorod', zip: '' }, expect: /alun/i },
  { label: 'Alun, Hunedoara, no commune (ambiguous → must NOT guess)', r: { county: 'Hunedoara', countyCode: 'HD', city: 'Alun', zip: '' }, expectError: /^ADDRESS_/ },
  { label: 'Florești, Cluj (Florești also exists in Prahova)', r: { county: 'Cluj', countyCode: 'CJ', city: 'Florești', zip: '407280' }, expect: /floresti/i },
];

// ---------------------------------------------------------------- run

console.log(`== ${adapter.name}: sandbox run (${flag('--create') ? 'WITH one test shipment' : opt('--awb') ? `existing AWB ${opt('--awb')}` : 'read-only'})`);

const conn = await step('testConnection', () => adapter.testConnection(ctx));
if (conn) check('testConnection', conn.ok === true, t('en', conn.message));

if (adapter.listPickupPoints) {
  const pts = await step('listPickupPoints', () => adapter.listPickupPoints(ctx));
  if (pts) check('listPickupPoints', Array.isArray(pts) && pts.every((p) => p.id && p.name !== undefined), `${pts.length}: ${pts.slice(0, 3).map((p) => `${p.id} ${p.name}`).join(' | ')}`);
}
if (adapter.listServices) {
  const svcs = await step('listServices', () => adapter.listServices(ctx));
  if (svcs) check('listServices', Array.isArray(svcs) && svcs.length > 0, `${svcs.length}: ${svcs.slice(0, 6).map((s) => s.name).join(', ')}`);
}

for (const a of ADDRESSES) {
  const recipient = { name: 'Test Expedo', street: 'Str. Test 1', country: 'RO', ...a.r };
  try {
    const got = await RESOLVERS[courierId](recipient);
    if (a.expectError) check(`locality: ${a.label}`, false, `expected an ADDRESS_* error, got ${got}`);
    else check(`locality: ${a.label}`, a.expect.test(got.normalize('NFD').replace(/[̀-ͯ]/g, '')), got);
  } catch (err) {
    if (err.code === 'AUTH_FAILED') { check(`locality: ${a.label}`, false, err.message); finish(1); }
    const ok = !!a.expectError && a.expectError.test(err.code || '');
    check(`locality: ${a.label}`, ok, `${err.code}: ${err.message}${err.hint ? ` — ${err.hint}` : ''}`);
  }
}

let awb = opt('--awb');
if (flag('--create') && !awb) {
  const shipment = {
    reference: 'EXPEDO-TEST',
    recipient: {
      name: 'Test Expedo', contactPerson: 'Test Expedo', phone: process.env.EXPEDO_SANDBOX_PHONE || '0700000000', email: '',
      county: 'Cluj', countyCode: 'CJ', city: 'Cluj-Napoca', street: 'Str. Test 1', zip: '400001', country: 'RO',
    },
    parcels: 1, weightKg: 1, envelopes: 0, cod: 10, currency: 'RON', declaredValue: 0,
    contents: 'Test API Expedo - NU EXPEDIATI', notes: 'TEST API - AWB anulat imediat',
  };
  const created = await step('createShipment (COD 10 RON)', () => adapter.createShipment(ctx, shipment));
  if (created) {
    awb = created.awb;
    check('createShipment (COD 10 RON)', /^\w{6,}$/.test(String(awb)), `AWB ${awb}${created.price != null ? `, price ${created.price}` : ''}`);
  }
}

if (awb) {
  const label = await step('getLabel', () => adapter.getLabel(ctx, awb, { format: 'A4' }), { fatalOnAuth: false });
  if (label) {
    check('getLabel returns a PDF', isPdf(label), `${label.length} bytes, starts with ${JSON.stringify(label.subarray(0, 8).toString('latin1'))}`);
    if (opt('--label')) writeFileSync(opt('--label'), label);
  }
  const tr = await step('track', () => adapter.track(ctx, [awb]), { fatalOnAuth: false });
  if (tr) check('track', tr.length === 1 && tr[0].awb === String(awb), JSON.stringify(tr));
  const cancelled = await step('cancelShipment', async () => { await adapter.cancelShipment(ctx, awb); return true; }, { fatalOnAuth: false });
  if (cancelled) check('cancelShipment', true, `AWB ${awb} cancelled`);
  const after = await step('track after cancel', () => adapter.track(ctx, [awb]), { fatalOnAuth: false });
  if (after) console.log(`INFO  track after cancel — ${JSON.stringify(after)}`);
}

console.log(failed ? `${failed} check(s) failed.` : 'All checks passed.');
finish();
