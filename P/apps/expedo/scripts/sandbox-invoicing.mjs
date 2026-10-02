// End-to-end run of the REAL invoicing adapters against a provider TEST/DEMO account (never a merchant's live company).
//
//   FGO (test environment api-testuat.fgo.ro — account self-registered at https://testuat.fgo.ro/inregistrare,
//   no paid plan needed; FGO publishes no shared test account):
//     FGO_CUI=... FGO_PRIVATE_KEY=... FGO_SERIES=... node scripts/sandbox-invoicing.mjs fgo
//
//   SmartBill / Oblio have NO sandbox: they run only against a company the operator owns and declares as a demo/test
//   company (EXPEDO_DEMO_COMPANY=yes). Every document is issued to a fake client and says "TEST EXPEDO".
//     SMARTBILL_EMAIL=... SMARTBILL_TOKEN=... SMARTBILL_CIF=... SMARTBILL_SERIES=... EXPEDO_DEMO_COMPANY=yes \
//       node scripts/sandbox-invoicing.mjs smartbill
//     OBLIO_EMAIL=... OBLIO_SECRET=... OBLIO_CIF=... OBLIO_SERIES=... EXPEDO_DEMO_COMPANY=yes \
//       node scripts/sandbox-invoicing.mjs oblio
//
//   Options: --save  writes the SANITIZED responses to test/fixtures/invoicing/<provider>-success.json
//            (credentials, CIFs, tokens, hashes and link secrets are replaced; review the file before committing).
//            SANDBOX_B2B_CUI=... overrides the fake B2B client CUI (default 99999992: checksum-valid, outside the
//            range ever assigned, so it can't be a real company — a provider that checks ANAF may reject it).
//
// Steps: testConnection, listSeries, createInvoice B2C (card, paid) and B2B (CUI, cash on delivery) — both with a
// shipping line and a client name with diacritics (settles FGO's UTF-8 hash question: the first emitere is accepted,
// no diacritics-free retry) — getPdf (must start with %PDF), registerPayment (COD collected), stornoInvoice (card
// refund), cancelInvoice (on a third, unpaid invoice). Prints PASS/FAIL per step; exit code 1 on any failure.
// Credentials are read from the environment only and never printed or written.

import { writeFileSync } from 'node:fs';
import { request } from '../src/lib/http.js';
import { getInvoicer } from '../src/invoicing/index.js';
import { bucharestDay } from '../src/invoicing/ro-time.js';

const provider = process.argv[2];
const SAVE = process.argv.includes('--save');
const env = (k) => (process.env[k] ?? '').trim();

function setup() {
  if (provider === 'fgo') {
    return {
      credentials: { cui: env('FGO_CUI'), privateKey: env('FGO_PRIVATE_KEY') },
      // testMode is forced: this script never talks to api.fgo.ro (production).
      settings: { series: env('FGO_SERIES'), platformUrl: 'https://expedo-sandbox.test', vatPayer: env('FGO_VAT_PAYER') !== 'no', testMode: true,
        registerCardPayments: env('FGO_REGISTER_CARD_PAYMENTS') === 'yes' },
      secrets: [env('FGO_CUI'), env('FGO_PRIVATE_KEY')],
    };
  }
  if (provider === 'smartbill' || provider === 'oblio') {
    if (env('EXPEDO_DEMO_COMPANY') !== 'yes') {
      console.error(`${provider} has no sandbox. Set EXPEDO_DEMO_COMPANY=yes only for a demo/test company you own — never a merchant's live company.`);
      process.exit(2);
    }
    const P = provider.toUpperCase();
    const credentials = provider === 'smartbill'
      ? { email: env('SMARTBILL_EMAIL'), token: env('SMARTBILL_TOKEN') }
      : { email: env('OBLIO_EMAIL'), secret: env('OBLIO_SECRET') };
    return {
      credentials,
      settings: { cif: env(`${P}_CIF`), series: env(`${P}_SERIES`), vatPayer: env(`${P}_VAT_PAYER`) !== 'no', markPaid: true, sendEmail: false },
      secrets: [...Object.values(credentials), env(`${P}_CIF`), env(`${P}_CIF`).replace(/^RO/i, '')],
    };
  }
  console.error('Usage: node scripts/sandbox-invoicing.mjs fgo|smartbill|oblio [--save]');
  process.exit(2);
}

const { credentials, settings, secrets } = setup();
for (const [k, v] of Object.entries({ ...credentials, series: settings.series })) {
  if (!v) { console.error(`Missing ${k} (see the environment variables at the top of this script).`); process.exit(2); }
}

// ── ctx: the real HTTP client, recording every response for the sanitized fixture ──
const recorded = [];
const mem = new Map();
const ctx = {
  credentials,
  settings,
  cache: { get: (k) => { const e = mem.get(k); return e && e.exp > Date.now() ? e.v : undefined; }, set: (k, v, ttl = 60) => mem.set(k, { v, exp: Date.now() + ttl * 1000 }) },
  log: (msg, data) => console.log(`      log: ${msg}`, data ? JSON.stringify(data) : ''),
  http: async (prov, url, opts = {}) => {
    const u = new URL(url);
    const entry = { request: `${opts.method || 'GET'} ${u.origin}${u.pathname}` };
    recorded.push(entry);
    try {
      const res = await request(prov, url, opts);
      entry.status = res.status;
      entry.body = Buffer.isBuffer(res.body) ? `<${res.body.length} bytes, starts with ${JSON.stringify(res.body.subarray(0, 8).toString('latin1'))}>` : res.body;
      return res;
    } catch (err) {
      entry.error = { code: err.code, message: err.message, details: err.details };
      throw err;
    }
  },
};
const adapter = getInvoicer(provider);

// ── fake clients, "TEST EXPEDO" everywhere ──
const today = bucharestDay();
const stamp = Date.now().toString(36);
const lines = [
  { name: 'Produs test Expedo — tricou (M)', code: 'EXPEDO-TEST-1', quantity: 2, unitPrice: 59.99, vatRate: 21, unit: 'buc' },
  { name: 'Transport', quantity: 1, unitPrice: 19.99, vatRate: 21, unit: 'buc', isShipping: true },
];
const total = 139.97;
const address = { address: 'Strada Testului nr. 1, TEST EXPEDO', city: 'Cluj-Napoca', county: 'Cluj', countyCode: 'CJ', zip: '400001', country: 'Romania' };
const invoiceFor = (ref, client, extra) => ({
  reference: ref, issueDate: today, dueDate: today, currency: 'RON', language: 'RO', client, lines, total,
  mentions: `TEST EXPEDO — comanda de test ${ref}, nu este o vânzare reală.`, sendEmail: false,
  idempotencyKey: `expedo-sandbox:${ref}`, ...extra,
});
const b2c = invoiceFor(`#T${stamp}A`, { name: 'Ștefănescu Țăranu Client Test Expedo', isCompany: false, email: 'client.test@example.com', phone: '0700000000', ...address },
  { paid: true, paymentMethod: 'card' });
const b2b = invoiceFor(`#T${stamp}B`, { name: 'Client Test Expedo Științific SRL', isCompany: true, vatCode: env('SANDBOX_B2B_CUI') || '99999992', regCom: 'J12/0000/2026', email: 'firma.test@example.com', ...address },
  { paid: false, paymentMethod: 'cod' });
const toCancel = invoiceFor(`#T${stamp}C`, { name: 'Client Test Expedo Anulare', isCompany: false, ...address }, { paid: false, paymentMethod: 'cod' });

// ── run ──
let failed = 0;
const results = {};
const pause = () => new Promise((r) => setTimeout(r, provider === 'fgo' ? 1200 : 400)); // FGO: 1 request/second
async function step(name, fn, check = () => true) {
  await pause();
  try {
    const out = await fn();
    const ok = check(out);
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${typeof ok === 'string' ? `  — ${ok}` : ''}`);
    if (!ok) failed++;
    results[name] = out;
    return out;
  } catch (err) {
    failed++;
    console.log(`FAIL  ${name}  — ${err.code || err.name}: ${err.message}${err.hint ? ` (${err.hint})` : ''}`);
    return undefined;
  }
}
const issued = (r) => Boolean(r?.series && r?.number && r.number !== 'undefined');

console.log(`Expedo invoicing sandbox — ${adapter.name}${provider === 'fgo' ? ' (api-testuat.fgo.ro)' : ' (demo company)'} — ${today}`);
const conn = await step('testConnection', () => adapter.testConnection(ctx), (r) => r?.ok === true);
if (!conn) { console.log('\nStopped: the account is not usable (nothing was issued).'); process.exit(1); }
if (adapter.listSeries) await step('listSeries', () => adapter.listSeries(ctx), (r) => Array.isArray(r) && r.some((s) => s.name === settings.series));

const inv1 = await step('createInvoice B2C (card, paid, diacritics, shipping line)', () => adapter.createInvoice(ctx, b2c), issued);
if (provider === 'fgo' && inv1) {
  const emits = recorded.filter((e) => e.request.endsWith('/factura/emitere'));
  const ok = emits.length === 1;
  console.log(`${ok ? 'PASS' : 'FAIL'}  FGO hash over UTF-8 with diacritics accepted on the first emitere (${emits.length} call(s))`);
  if (!ok) failed++;
}
const inv2 = await step('createInvoice B2B (CUI, cash on delivery, diacritics, shipping line)', () => adapter.createInvoice(ctx, b2b), issued);
if (inv1) {
  // Only where the provider dedupes (FGO VerificareDuplicat+IdExtern, Oblio idempotencyKey). SmartBill V1 has no
  // idempotency key: a second call WOULD issue a second invoice, so it is not tried there.
  if (provider !== 'smartbill') {
    await step('createInvoice B2C again with the same idempotencyKey (duplicate protection)', () => adapter.createInvoice(ctx, b2c),
      (r) => (r?.number === inv1.number ? `same invoice ${r.series} ${r.number}${r.duplicate ? ' (flagged duplicate)' : ''}` : false));
  }
  await step('getPdf (B2C)', () => adapter.getPdf(ctx, inv1), (buf) => Buffer.isBuffer(buf) && buf.subarray(0, 4).toString('latin1') === '%PDF' && `${buf.length} bytes`);
}
if (inv2) {
  await step('registerPayment (B2B, COD collected)', () => adapter.registerPayment(ctx, { series: inv2.series, number: inv2.number, amount: total, date: today, method: 'cod', reference: b2b.reference }), (r) => r && !r.skipped);
  await step('registerPayment again (must not collect twice)', () => adapter.registerPayment(ctx, { series: inv2.series, number: inv2.number, amount: total, date: today, method: 'cod', reference: b2b.reference }), (r) => r?.alreadyPaid === true);
}
if (inv1) await step('stornoInvoice (B2C refund)', () => adapter.stornoInvoice(ctx, { series: inv1.series, number: inv1.number, issueDate: today }), issued);
const inv3 = await step('createInvoice (to be cancelled)', () => adapter.createInvoice(ctx, toCancel), issued);
if (inv3) await step('cancelInvoice', () => adapter.cancelInvoice(ctx, inv3), () => true);

console.log(failed ? `\n${failed} step(s) FAILED` : '\nAll steps passed');

// ── sanitized fixture ──
if (SAVE) {
  const secretList = secrets.filter((s) => s && s.length >= 4).sort((a, b) => b.length - a.length);
  const scrub = (v) => {
    if (typeof v === 'string') {
      let s = v;
      for (const sec of secretList) s = s.split(sec).join('<REDACTED>');
      // Link secrets: keep host/path/param names, drop the values (show_file it=, extern view tokens, etc.).
      s = s.replace(/(https?:\/\/[^\s"?]+)\?([^\s"]+)/g, (_, base, q) => `${base}?${q.split('&').map((kv) => `${kv.split('=')[0]}=<REDACTED>`).join('&')}`);
      s = s.replace(/\b[0-9a-f]{32,}\b/gi, '<REDACTED_HEX>');
      return s;
    }
    if (Array.isArray(v)) return v.map(scrub);
    if (v && typeof v === 'object') {
      return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, /^(access_token|Hash|token|client_secret)$/i.test(k) ? '<REDACTED>' : scrub(x)]));
    }
    return v;
  };
  const file = new URL(`../test/fixtures/invoicing/${provider}-success.json`, import.meta.url);
  writeFileSync(file, JSON.stringify({
    _source: `Captured ${new Date().toISOString()} by scripts/sandbox-invoicing.mjs against ${provider === 'fgo' ? 'api-testuat.fgo.ro (FGO test environment)' : `a ${adapter.name} demo company`}. Sanitized: credentials, company CIF, tokens, hashes and link query values replaced. Fake clients only ("TEST EXPEDO").`,
    failedSteps: failed,
    exchanges: scrub(recorded),
  }, null, 2) + '\n');
  console.log(`Saved sanitized responses to ${file.pathname} — review before committing.`);
}
process.exit(failed ? 1 : 0);
