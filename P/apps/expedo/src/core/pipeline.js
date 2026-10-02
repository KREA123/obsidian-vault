import { createHash } from 'node:crypto';
import { PDFDocument } from 'pdf-lib';
import * as db from '../db.js';
import { request } from '../lib/http.js';
import { couriers, getCourier } from '../couriers/index.js';
import { invoicers, getInvoicer } from '../invoicing/index.js';
import mockCourier from '../couriers/mock.js';
import mockInvoicer from '../invoicing/mock.js';
import { FINAL_STATUSES, TrackingStatus, TRACKING_LABELS } from '../couriers/contract.js';
import { ProcessingError, toProcessingError } from './errors.js';
import { withDefaults } from './settings.js';
import { planOrder, buildShipment, buildInvoice, bucharestDate } from './build.js';
import { getShopify } from '../shopify/index.js';

export const ORDER_STATUS = {
  new: 'Nouă',
  needs_attention: 'Necesită atenție',
  on_hold: 'În așteptare',
  ready: 'Gata de procesat',
  shipped: 'Expediată',
  in_transit: 'În livrare',
  delivered: 'Livrată',
  returned: 'Returnată',
  cancelled: 'Anulată',
};

const locks = new Set();

export function storeSettings(store) {
  return withDefaults(store.settings);
}

/** In test mode (or demo store) every provider is swapped for the test one: nothing real is created. */
export function isTestMode(store) {
  return store.demo || storeSettings(store).mode !== 'live';
}

function providerCtx(store, providerId, integration, test) {
  return {
    // The test providers never get the real credentials or settings (e.g. a real invoice series).
    credentials: test ? {} : integration.credentials,
    settings: test ? {} : integration.settings,
    http: request,
    cache: db.storeCache(store.id),
    log: (message, data) => db.logEvent(store.id, null, 'info', providerId, message, data),
  };
}

const registryFor = (kind) => (id) => (Object.hasOwn(kind === 'courier' ? couriers : invoicers, id) ? (kind === 'courier' ? getCourier : getInvoicer)(id) : undefined);

function realProvider(store, kind, providerId) {
  const realAdapter = registryFor(kind)(providerId);
  if (!realAdapter) {
    throw new ProcessingError({ code: 'PROVIDER_UNKNOWN', message: `Integrarea „${providerId}” nu există.`, hint: 'Alege alta în Setări.' });
  }
  const integration = db.getIntegration(store.id, kind, providerId);
  if (!integration || !integration.enabled) {
    throw new ProcessingError({
      code: 'PROVIDER_NOT_CONFIGURED',
      message: `${realAdapter.name} nu e configurat.`,
      hint: `Adaugă datele de conectare în Setări → ${kind === 'courier' ? 'Curieri' : 'Facturare'}.`,
      provider: providerId,
    });
  }
  return { adapter: realAdapter, realAdapter, test: false, ctx: providerCtx(store, providerId, integration, false) };
}

function testProvider(store, kind, providerId) {
  const adapter = kind === 'courier' ? mockCourier : mockInvoicer;
  return { adapter, realAdapter: registryFor(kind)(providerId) || adapter, test: true, ctx: providerCtx(store, providerId, null, true) };
}

/** Provider used to CREATE something now: the test one in test mode, the real one on live. */
export function providerContext(store, kind, providerId) {
  if (!registryFor(kind)(providerId)) {
    throw new ProcessingError({ code: 'PROVIDER_UNKNOWN', message: `Integrarea „${providerId}” nu există.`, hint: 'Alege alta în Setări.' });
  }
  return isTestMode(store) ? testProvider(store, kind, providerId) : realProvider(store, kind, providerId);
}

/**
 * Provider for an AWB / invoice that already exists: always the one that created it, whatever the
 * store's current mode (a test AWB stays with the test courier after going live, a real AWB keeps
 * being tracked and printed by the real courier while the store is back in test mode).
 */
export function existingProviderContext(store, kind, providerId, wasTest) {
  return wasTest ? testProvider(store, kind, providerId) : realProvider(store, kind, providerId);
}

/** Recomputes the order's display status from what has been done to it. */
export function deriveStatus(order, { blocking, hold } = {}) {
  const d = order.data || {};
  const t = order.tracking_status;
  if (!order.awb) {
    if (d.cancelledAt) return 'cancelled';
    // Fulfilled outside Expedo (manually in Shopify): nothing left to do here.
    if (d.fulfillmentStatus === 'FULFILLED') return 'shipped';
    if (order.last_error || blocking) return 'needs_attention';
    if (hold) return 'on_hold';
    return 'ready';
  }
  if (t === TrackingStatus.DELIVERED) return 'delivered';
  if (t === TrackingStatus.RETURNED || t === TrackingStatus.RETURNING) return 'returned';
  // Has an AWB but something needs a decision: cancelled in Shopify (cancel the AWB?), AWB cancelled
  // at the courier (make a new one?), or a later step failed (invoice, Shopify fulfillment).
  if (d.cancelledAt || t === TrackingStatus.CANCELLED || order.last_error) return 'needs_attention';
  if (t && ![TrackingStatus.CREATED, TrackingStatus.UNKNOWN].includes(t)) return 'in_transit';
  return 'shipped';
}

/** Validates an order and stores issues + status. Returns the plan. */
export function validateOrder(store, orderId) {
  const order = db.getOrder(orderId);
  const settings = storeSettings(store);
  const plan = planOrder(order.data, settings, order.overrides);
  const skipTag = (order.data.tags || []).some((t) => settings.automation.skipTags.map((s) => s.toLowerCase()).includes(t.toLowerCase()));
  const staleValidationError = order.last_error?.step === 'validate' && !plan.blocking;
  const updated = db.updateOrder(orderId, {
    issues: plan.issues,
    courier: order.awb ? order.courier : plan.courier || null,
    ...(staleValidationError ? { last_error: null } : {}),
  });
  db.updateOrder(orderId, { status: deriveStatus(updated, { blocking: plan.blocking, hold: plan.hold || skipTag || !!order.overrides.hold }) });
  return { plan, skipTag };
}

/** Imports (or refreshes) a Shopify order and schedules auto-processing when enabled. */
export function importOrder(store, normalized, { source = 'sync' } = {}) {
  const existing = db.getOrderByShopifyId(store.id, normalized.shopifyId);
  const order = db.upsertOrder(store.id, normalized);
  if (!existing) db.logEvent(store.id, order.id, 'info', 'import', `Comanda ${order.name} a fost preluată din Shopify (${source}).`);
  if (normalized.cancelledAt && !existing?.data?.cancelledAt) {
    db.logEvent(store.id, order.id, order.awb ? 'warning' : 'info', 'import', order.awb
      ? `Comanda a fost anulată în Shopify, dar are AWB ${order.awb}. Anulează AWB-ul dacă nu a plecat coletul.`
      : 'Comanda a fost anulată în Shopify.');
  }
  if (existing?.awb && existing.data?.codAmount !== normalized.codAmount && Math.abs((normalized.codAmount || 0) - (existing.cod_amount || 0)) >= 0.01) {
    db.logEvent(store.id, order.id, 'warning', 'cod', `Suma de încasat din Shopify s-a schimbat după AWB: acum ${Number(normalized.codAmount || 0).toFixed(2)} lei, `
      + `dar AWB-ul ${existing.awb} are ramburs ${Number(existing.cod_amount || 0).toFixed(2)} lei. Dacă trebuie corectat, anulează AWB-ul și generează altul.`);
  }
  const { plan, skipTag } = validateOrder(store, order.id);

  const settings = storeSettings(store);
  const fresh = db.getOrder(order.id);
  if (!existing && settings.automation.autoProcess && fresh.status === 'ready' && !plan.blocking && !plan.hold && !skipTag) {
    const runAt = new Date(Date.now() + settings.automation.delayMinutes * 60_000).toISOString();
    enqueue(store.id, 'process_order', { orderId: order.id }, { runAt, key: `process:${order.id}` });
    db.logEvent(store.id, order.id, 'info', 'auto', `Se procesează automat în ${settings.automation.delayMinutes} minute.`);
  }
  return fresh;
}

export function enqueue(storeId, type, payload, { runAt, key, maxAttempts = 6 } = {}) {
  try {
    db.getDb().prepare('INSERT INTO jobs (store_id, type, key, payload, run_at, max_attempts) VALUES (?, ?, ?, ?, ?, ?)')
      .run(storeId, type, key ?? null, JSON.stringify(payload), runAt || new Date().toISOString(), maxAttempts);
  } catch (err) {
    if (!/UNIQUE/.test(err.message)) throw err; // same job already pending
  }
}

function fail(store, orderId, step, err) {
  const e = toProcessingError(err, step);
  db.updateOrder(orderId, { last_error: { ...e.toJSON(), step, at: new Date().toISOString() } });
  db.logEvent(store.id, orderId, 'error', step, e.message, { hint: e.hint, code: e.code, details: e.details });
  return e;
}

/**
 * Runs the processing steps for one order. Every step is idempotent: an order that
 * already has an AWB never gets a second one, an invoiced order is never re-invoiced.
 * steps: ['awb', 'invoice', 'fulfill']
 */
export async function processOrder(store, orderId, { steps = ['awb', 'invoice', 'fulfill'], force = false } = {}) {
  const existing = db.getOrder(orderId);
  if (!existing || existing.store_id !== store.id) return { ok: false, error: { code: 'ORDER_NOT_FOUND', message: 'Comanda nu există.' } };
  const busy = { ok: false, error: { code: 'ORDER_BUSY', message: 'Comanda e deja în procesare.', hint: 'Încearcă din nou în câteva minute.' } };
  const lockKey = `${store.id}:${orderId}`;
  if (locks.has(lockKey)) return busy;
  locks.add(lockKey);
  let claimed = false;
  try {
    // The in-memory lock covers this process; the claim in the database covers other processes and
    // runs interrupted by a crash (the claim is never released, so we know the run did not finish).
    const claim = db.claimOrder(orderId, { takeOver: force || !!existing.awb });
    if (claim === 'busy') return busy;
    if (claim === 'stale') {
      const e = fail(store, orderId, 'awb', new ProcessingError({
        code: 'PROCESSING_INTERRUPTED',
        message: 'Procesarea anterioară a comenzii s-a întrerupt înainte să se termine.',
        hint: 'Verifică în contul curierului dacă s-a creat deja un AWB pentru comanda asta, apoi apasă „Generează AWB” ca să reiei.',
      }));
      db.updateOrder(orderId, { status: 'needs_attention' });
      return { ok: false, error: e.toJSON() };
    }
    claimed = true;
    if (claim === 'taken_over' && !existing.awb) {
      db.logEvent(store.id, orderId, 'warning', 'awb', 'O procesare anterioară s-a întrerupt; am reluat-o. Verifică la curier să nu existe un AWB în plus.');
    }

    const { plan, skipTag } = validateOrder(store, orderId);
    let order = db.getOrder(orderId);
    const settings = storeSettings(store);
    const test = isTestMode(store);
    const held = skipTag || plan.hold || !!order.overrides.hold;
    const refuse = (code, message, hint) => ({ ok: false, error: { code, message, hint } });

    if (order.data.cancelledAt) {
      // Status stays derived ('cancelled', or 'needs_attention' when an AWB exists); nothing to record.
      return refuse('ORDER_CANCELLED', order.awb
        ? `Comanda a fost anulată în Shopify, dar are AWB ${order.awb}.`
        : 'Comanda e anulată în Shopify.', order.awb ? 'Anulează AWB-ul dacă nu a plecat coletul. Nu se mai facturează și nu se marchează expediată.' : 'Nu se mai expediază.');
    }
    if (!test && ((order.awb && order.test_mode) || (order.invoice_number && order.invoice_test))) {
      // Finishing it now would e.g. send the customer a TEST AWB from Shopify, or pair a real AWB with a test invoice.
      return refuse('TEST_DATA', 'Comanda are AWB sau factură de probă, făcute în modul de probă.',
        'Apasă „Șterge datele de probă” în pagina comenzii, apoi procesează din nou ca să se facă AWB și factură reale.');
    }
    if (!order.awb && order.data.fulfillmentStatus === 'FULFILLED' && steps.includes('awb')) {
      return refuse('ALREADY_FULFILLED', 'Comanda e deja marcată ca expediată în Shopify.',
        'Dacă totuși îți trebuie AWB, anulează expedierea în Shopify, apoi apasă „Reîncarcă din Shopify”.');
    }
    if (plan.blocking && !order.awb) {
      const first = plan.issues.find((i) => i.level === 'error');
      const e = fail(store, orderId, 'validate', new ProcessingError({ code: first.code, message: first.message, hint: first.hint, field: first.field }));
      db.updateOrder(orderId, { status: 'needs_attention' });
      return { ok: false, error: e.toJSON() };
    }
    if (!force && held && !order.awb) {
      return refuse('ORDER_ON_HOLD', 'Comanda e în așteptare (etichetă sau regulă).', 'Deschide comanda și procesează-o manual.');
    }
    db.updateOrder(orderId, { last_error: null });

    // 1. AWB
    if (steps.includes('awb') && !order.awb) {
      try {
        const { adapter, ctx, realAdapter } = providerContext(store, 'courier', plan.courier);
        const shipment = buildShipment(order.data, plan, settings);
        const res = await adapter.createShipment(ctx, shipment);
        order = db.updateOrder(orderId, {
          awb: res.awb, awb_at: new Date().toISOString(), courier: plan.courier, service: plan.service || null,
          shipping_cost: res.price ?? null, tracking_status: TrackingStatus.CREATED, tracking_text: TRACKING_LABELS.created,
          cod_amount: shipment.cod, test_mode: test,
        });
        db.logEvent(store.id, orderId, 'success', 'awb', `AWB ${res.awb} generat la ${realAdapter.name}${test ? ' (probă)' : ''}.`,
          { cod: shipment.cod, weightKg: shipment.weightKg, parcels: shipment.parcels, rules: plan.matchedRules });
      } catch (err) {
        const e = fail(store, orderId, 'awb', ambiguousTimeout(toProcessingError(err, plan.courier), 'AWB-ul', 'curierului'));
        db.updateOrder(orderId, { status: 'needs_attention' });
        if (e.retryable) enqueue(store.id, 'process_order', { orderId }, { runAt: new Date(Date.now() + 5 * 60_000).toISOString(), key: `process:${orderId}` });
        return { ok: false, error: e.toJSON() };
      }
    }

    // 2. Invoice
    const invoicer = settings.invoicing.provider;
    if (steps.includes('invoice') && invoicer && !order.invoice_number && !plan.skipInvoice && (settings.invoicing.when === 'on_awb' || !steps.includes('awb'))) {
      try {
        const { adapter, ctx, realAdapter } = providerContext(store, 'invoicing', invoicer);
        const invoice = buildInvoice(order.data, plan, settings);
        // After a storno the order is invoiced again; FGO/Oblio would reject the same key as a duplicate.
        const previous = db.getDb().prepare(`SELECT COUNT(*) c FROM events WHERE order_id = ? AND step = 'invoice' AND level = 'success' AND message LIKE 'Factura % emisă%'`).get(orderId).c;
        invoice.idempotencyKey = invoiceIdempotencyKey(store, order.name, previous ? previous + 1 : 0);
        if (invoice.mismatch) {
          db.logEvent(store.id, orderId, 'warning', 'invoice', `Totalul facturii diferă de totalul din Shopify cu ${invoice.mismatch.toFixed(2)} lei (card cadou, comandă editată, rotunjiri?). Verifică factura.`);
        }
        const res = await adapter.createInvoice(ctx, invoice);
        order = db.updateOrder(orderId, {
          invoice_provider: invoicer, invoice_series: res.series, invoice_number: String(res.number),
          invoice_url: res.url || null, invoice_at: new Date().toISOString(), invoice_test: test,
        });
        db.logEvent(store.id, orderId, 'success', 'invoice', `Factura ${res.series} ${res.number} emisă în ${realAdapter.name}${test ? ' (probă)' : ''}.`);
      } catch (err) {
        const e = fail(store, orderId, 'invoice', ambiguousTimeout(toProcessingError(err, invoicer), 'factura', 'programului de facturare'));
        db.updateOrder(orderId, { status: 'needs_attention' });
        return { ok: false, error: e.toJSON(), partial: true };
      }
    }

    // 3. Shopify fulfillment with tracking (never in test mode: real customers would get e-mails)
    if (steps.includes('fulfill') && order.awb && !order.fulfilled_at && settings.fulfillment.fulfillInShopify) {
      // Test mode: the banner already says Shopify is left untouched; no per-order noise.
      if (!test) {
        try {
          const shopify = getShopify(store);
          const fresh = await shopify.getOrder(order.shopify_id);
          if (fresh) {
            db.upsertOrder(store.id, fresh);
            order = db.getOrder(orderId);
          }
          if (order.data.cancelledAt) {
            throw new ProcessingError({ code: 'ORDER_CANCELLED', message: 'Comanda a fost anulată în Shopify între timp; nu a fost marcată ca expediată.', hint: 'Anulează AWB-ul dacă nu a plecat coletul.', provider: 'shopify' });
          }
          const courier = getCourier(order.courier);
          const f = await shopify.fulfill(order.data, {
            awb: order.awb, company: courier.name, url: courier.trackingUrl(order.awb), notifyCustomer: settings.fulfillment.notifyCustomer,
          });
          order = db.updateOrder(orderId, { fulfillment_id: f.id, fulfilled_at: new Date().toISOString() });
          await shopify.addTags(order.shopify_id, settings.fulfillment.tags).catch(() => {});
          db.logEvent(store.id, orderId, 'success', 'fulfill', `Marcată ca expediată în Shopify${settings.fulfillment.notifyCustomer ? '; clientul a primit e-mail cu AWB-ul' : ''}.`);
        } catch (err) {
          const e = toProcessingError(err, 'shopify');
          if (e.code === 'SHOPIFY_NOTHING_TO_FULFILL') {
            db.updateOrder(orderId, { fulfilled_at: new Date().toISOString() });
            db.logEvent(store.id, orderId, 'warning', 'fulfill', e.message, { hint: e.hint });
          } else {
            fail(store, orderId, 'fulfill', e);
            if (e.retryable) enqueue(store.id, 'process_order', { orderId }, { runAt: new Date(Date.now() + 5 * 60_000).toISOString(), key: `process:${orderId}` });
            db.updateOrder(orderId, { status: 'needs_attention' });
            return { ok: false, error: e.toJSON(), partial: true };
          }
        }
      }
    }

    order = db.getOrder(orderId);
    db.updateOrder(orderId, { status: deriveStatus(order, { blocking: plan.blocking, hold: held }) });
    return { ok: true, awb: order.awb, invoice: order.invoice_number ? `${order.invoice_series} ${order.invoice_number}` : null };
  } finally {
    if (claimed) db.releaseOrder(orderId);
    locks.delete(lockKey);
  }
}

/**
 * Key invoicing providers use to refuse duplicates (FGO IdExtern, Oblio...). They dedupe per company,
 * and two Shopify stores can invoice through the same company, so the key names the store too:
 * "magazin:#1024", "magazin:#1024-2" after a storno. Kept within 60 characters.
 */
export function invoiceIdempotencyKey(store, orderName, n = 0) {
  const name = n ? `${orderName}-${n}` : String(orderName);
  let shop = String(store.shop || '').replace(/\.myshopify\.com$/i, '');
  const room = 60 - name.length - 1;
  if (shop.length > room) shop = createHash('sha256').update(String(store.shop)).digest('hex').slice(0, Math.max(8, room));
  return `${shop}:${name}`;
}

/**
 * A timeout while creating an AWB / invoice is ambiguous: the provider may have created it and only
 * the answer was lost. Retrying automatically could make a second one, so it becomes a manual check.
 */
function ambiguousTimeout(e, what, where) {
  if (e.code !== 'PROVIDER_TIMEOUT') return e;
  return new ProcessingError({
    ...e.toJSON(),
    retryable: false,
    hint: `Nu am primit răspuns la timp; e posibil ca ${what} să fi fost creat(ă) totuși. Verifică în contul ${where} înainte să încerci din nou.`,
  });
}

const realInTest = (store, wasTest) => !wasTest && isTestMode(store);

export async function cancelAwb(store, orderId) {
  const order = db.getOrder(orderId);
  if (!order.awb) throw new ProcessingError({ code: 'NO_AWB', message: 'Comanda nu are AWB.' });
  if ([TrackingStatus.PICKED_UP, TrackingStatus.IN_TRANSIT, TrackingStatus.OUT_FOR_DELIVERY, TrackingStatus.DELIVERED].includes(order.tracking_status)) {
    throw new ProcessingError({ code: 'AWB_ALREADY_MOVING', message: `Coletul a plecat deja (${order.tracking_text}). AWB-ul nu se mai poate anula.`, hint: 'Sună la curier pentru retur sau redirecționare.' });
  }
  if (realInTest(store, order.test_mode)) {
    // Cancelling it would also cancel the fulfillment in Shopify, which test mode never touches.
    throw new ProcessingError({ code: 'REAL_AWB_IN_TEST_MODE', message: `AWB-ul ${order.awb} e real, dar magazinul e acum în modul de probă.`, hint: 'Treci pe live ca să-l anulezi (se anulează la curier și în Shopify), sau anulează-l din contul curierului.' });
  }
  const { adapter, ctx, realAdapter } = existingProviderContext(store, 'courier', order.courier, order.test_mode);
  // Already cancelled at the courier (e.g. from their website): only clean up here.
  if (order.tracking_status !== TrackingStatus.CANCELLED) await adapter.cancelShipment(ctx, order.awb);
  let data = order.data;
  if (order.fulfillment_id && !order.test_mode) {
    try {
      await getShopify(store).cancelFulfillment(order.fulfillment_id);
      data = { ...data, fulfillmentStatus: 'UNFULFILLED' };
    } catch (err) {
      db.logEvent(store.id, orderId, 'warning', 'fulfill', `AWB anulat, dar expedierea din Shopify nu s-a putut anula: ${toProcessingError(err).message}`, { hint: 'Anulează expedierea manual în Shopify, apoi apasă „Reîncarcă din Shopify”.' });
    }
  }
  db.logEvent(store.id, orderId, 'success', 'awb', `AWB ${order.awb} anulat la ${realAdapter?.name || order.courier}${order.test_mode ? ' (probă)' : ''}.`);
  db.updateOrder(orderId, {
    awb: null, awb_at: null, tracking_status: null, tracking_text: null, tracking_at: null, fulfillment_id: null, fulfilled_at: null,
    shipping_cost: null, last_error: null, test_mode: false, cod_amount: order.data.codAmount || 0, data,
  });
  validateOrder(store, orderId);
}

export async function stornoInvoice(store, orderId) {
  const order = db.getOrder(orderId);
  if (!order.invoice_number) throw new ProcessingError({ code: 'NO_INVOICE', message: 'Comanda nu are factură.' });
  if (realInTest(store, order.invoice_test)) {
    throw new ProcessingError({ code: 'REAL_INVOICE_IN_TEST_MODE', message: `Factura ${order.invoice_series} ${order.invoice_number} e reală, dar magazinul e acum în modul de probă.`, hint: 'Treci pe live ca s-o stornezi, sau stornează-o din programul de facturare.' });
  }
  const { adapter, ctx, realAdapter } = existingProviderContext(store, 'invoicing', order.invoice_provider, order.invoice_test);
  const ref = { series: order.invoice_series, number: order.invoice_number };
  let message;
  let level = 'success';
  try {
    if (adapter.stornoInvoice) {
      const s = await adapter.stornoInvoice(ctx, ref);
      message = `Factura ${ref.series} ${ref.number} a fost stornată (factură storno ${s.series} ${s.number}).`;
    } else {
      await adapter.cancelInvoice(ctx, ref);
      message = `Factura ${ref.series} ${ref.number} a fost anulată.`;
    }
  } catch (err) {
    // A storno retried after a timeout: the first one went through. Done, not stuck.
    if (err?.code !== 'INVOICE_ALREADY_REVERSED') throw err;
    level = 'warning';
    message = `Factura ${ref.series} ${ref.number} era deja stornată; am marcat-o ca stornată și aici.`;
  }
  db.logEvent(store.id, orderId, level, 'invoice', `${message} (${realAdapter?.name}${order.invoice_test ? ', probă' : ''})`);
  db.updateOrder(orderId, { invoice_series: null, invoice_number: null, invoice_url: null, invoice_at: null, invoice_test: false });
}

/**
 * Drops the test AWB / invoice made in test mode, so the order can be processed for real after
 * going live. Only test data is touched; real AWBs and invoices are never removed here.
 */
export async function resetTestData(store, orderId) {
  const order = db.getOrder(orderId);
  const fields = {};
  const parts = [];
  if (order.awb && order.test_mode) {
    await mockCourier.cancelShipment({ cache: db.storeCache(store.id) }, order.awb);
    Object.assign(fields, {
      awb: null, awb_at: null, tracking_status: null, tracking_text: null, tracking_at: null, fulfillment_id: null, fulfilled_at: null,
      shipping_cost: null, cod_collected_at: null, cod_amount: order.data.codAmount || 0, test_mode: false,
    });
    parts.push(`AWB ${order.awb}`);
  }
  if (order.invoice_number && order.invoice_test) {
    Object.assign(fields, { invoice_provider: null, invoice_series: null, invoice_number: null, invoice_url: null, invoice_at: null, invoice_test: false });
    parts.push(`factura ${order.invoice_series} ${order.invoice_number}`);
  }
  if (!parts.length) throw new ProcessingError({ code: 'NO_TEST_DATA', message: 'Comanda nu are AWB sau factură de probă.' });
  db.updateOrder(orderId, { ...fields, last_error: null });
  db.logEvent(store.id, orderId, 'info', 'reset', `Datele de probă au fost șterse (${parts.join(', ')}). Comanda poate fi procesată din nou.`);
  validateOrder(store, orderId);
}

/** One PDF with the labels of all given orders, in order. Orders without AWB are skipped. */
export async function mergedLabels(store, orderIds, format) {
  const settings = storeSettings(store);
  const fmt = ['A4', 'A6'].includes(format) ? format : null;
  const out = await PDFDocument.create();
  const skipped = [];
  for (const id of orderIds) {
    const order = db.getOrder(id);
    if (!order || order.store_id !== store.id) continue;
    if (!order.awb) { skipped.push(order.name); continue; }
    const { adapter, ctx } = existingProviderContext(store, 'courier', order.courier, order.test_mode);
    const pdf = await adapter.getLabel(ctx, order.awb, { format: fmt || ctx.settings?.labelFormat || settings.courier.labelFormat });
    const src = await PDFDocument.load(pdf);
    for (const p of await out.copyPages(src, src.getPageIndices())) out.addPage(p);
    db.logEvent(store.id, id, 'info', 'label', `Eticheta AWB ${order.awb} a fost descărcată.`);
  }
  if (!out.getPageCount()) throw new ProcessingError({ code: 'NO_LABELS', message: 'Niciuna dintre comenzile selectate nu are AWB.', hint: 'Generează întâi AWB-urile.' });
  return { pdf: Buffer.from(await out.save()), skipped };
}

export async function invoicePdf(store, orderId) {
  const order = db.getOrder(orderId);
  if (!order?.invoice_number || order.store_id !== store.id) throw new ProcessingError({ code: 'NO_INVOICE', message: 'Comanda nu are factură.' });
  const { adapter, ctx } = existingProviderContext(store, 'invoicing', order.invoice_provider, order.invoice_test);
  return adapter.getPdf(ctx, { series: order.invoice_series, number: order.invoice_number });
}

/** Polls couriers for every open AWB of the store and reacts to delivery / return. */
export async function trackStore(store) {
  const rows = db.getDb().prepare(`SELECT id FROM orders WHERE store_id = ? AND awb IS NOT NULL
    AND (tracking_status IS NULL OR tracking_status NOT IN ('delivered', 'returned', 'cancelled'))`).all(store.id);
  const orders = rows.map((r) => db.getOrder(r.id));
  const groups = new Map();
  for (const o of orders) {
    const key = o.test_mode ? 'mock' : o.courier;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(o);
  }
  let changed = 0;
  for (const [courierId, list] of groups) {
    let results;
    try {
      const { adapter, ctx } = courierId === 'mock'
        ? existingProviderContext(store, 'courier', list[0].courier, true)
        : existingProviderContext(store, 'courier', courierId, false);
      results = [];
      for (let i = 0; i < list.length; i += 50) results.push(...await adapter.track(ctx, list.slice(i, i + 50).map((o) => o.awb)));
    } catch (err) {
      db.logEvent(store.id, null, 'warning', 'tracking', `Nu am putut verifica AWB-urile ${courierId}: ${toProcessingError(err).message}`);
      continue;
    }
    for (const r of results) {
      const order = list.find((o) => o.awb === r.awb);
      if (!order || (order.tracking_status === r.status && order.tracking_text === r.statusText)) continue;
      changed++;
      let updated = db.updateOrder(order.id, { tracking_status: r.status, tracking_text: r.statusText || TRACKING_LABELS[r.status], tracking_at: r.at || new Date().toISOString() });
      db.logEvent(store.id, order.id, r.status === TrackingStatus.FAILED_ATTEMPT || r.status === TrackingStatus.RETURNING || r.status === TrackingStatus.CANCELLED ? 'warning' : 'info', 'tracking',
        `${TRACKING_LABELS[r.status] || r.status}${r.statusText && r.statusText !== TRACKING_LABELS[r.status] ? `: ${r.statusText}` : ''}`);
      if (r.status === TrackingStatus.DELIVERED) await onDelivered(store, updated);
      if ((r.status === TrackingStatus.RETURNED || r.status === TrackingStatus.RETURNING) && order.tracking_status !== TrackingStatus.RETURNING) {
        db.logEvent(store.id, order.id, 'warning', 'tracking', 'Coletul se întoarce. Când ajunge, verifică produsele și stornează factura din pagina comenzii.');
      }
      if (r.status === TrackingStatus.CANCELLED) {
        db.logEvent(store.id, order.id, 'warning', 'tracking', 'Curierul raportează AWB-ul ca anulat. Apasă „Anulează AWB” ca să poți genera altul.');
      }
      updated = db.getOrder(order.id);
      db.updateOrder(order.id, { status: deriveStatus(updated) });
    }
  }
  return { checked: orders.length, changed };
}

async function onDelivered(store, order) {
  const settings = storeSettings(store);
  const test = isTestMode(store);
  if (order.cod_amount > 0 && !order.cod_collected_at) {
    db.updateOrder(order.id, { cod_collected_at: new Date().toISOString() });
    db.logEvent(store.id, order.id, 'success', 'cod', `Ramburs de ${order.cod_amount.toFixed(2)} lei încasat de curier${order.test_mode ? ' (probă)' : ''}.`);
    if (settings.fulfillment.registerCodPayment && order.invoice_number) {
      if (realInTest(store, order.invoice_test)) {
        db.logEvent(store.id, order.id, 'info', 'invoice', `Încasarea nu a fost înregistrată pe factura ${order.invoice_series} ${order.invoice_number}: magazinul e în modul de probă. Înregistreaz-o manual.`);
      } else {
        try {
          const { adapter, ctx } = existingProviderContext(store, 'invoicing', order.invoice_provider, order.invoice_test);
          if (adapter.registerPayment) {
            const r = await adapter.registerPayment(ctx, { series: order.invoice_series, number: order.invoice_number, amount: order.cod_amount, date: bucharestDate(), method: 'cod', reference: order.awb || order.name });
            const ref = `${order.invoice_series} ${order.invoice_number}`;
            if (r?.alreadyPaid) db.logEvent(store.id, order.id, 'info', 'invoice', `Factura ${ref} era deja încasată în programul de facturare.`);
            else if (r?.skipped) db.logEvent(store.id, order.id, 'info', 'invoice', `Încasarea nu a fost înregistrată pe factura ${ref} (programul de facturare a sărit-o${r.reason ? `: ${r.reason}` : ''}).`);
            else db.logEvent(store.id, order.id, 'success', 'invoice', `Încasarea a fost înregistrată pe factura ${ref}.`);
          }
        } catch (err) {
          db.logEvent(store.id, order.id, 'warning', 'invoice', `Încasarea nu s-a putut înregistra: ${toProcessingError(err).message}`);
        }
      }
    }
    // Shopify is never touched in test mode, nor for a test AWB.
    if (settings.fulfillment.markCodPaidOnDelivery && !order.test_mode && !test && !order.paid_marked_at) {
      try {
        await getShopify(store).markAsPaid(order.shopify_id);
        db.updateOrder(order.id, { paid_marked_at: new Date().toISOString() });
        db.logEvent(store.id, order.id, 'success', 'shopify', 'Comanda a fost marcată ca plătită în Shopify.');
      } catch (err) {
        db.logEvent(store.id, order.id, 'warning', 'shopify', `Nu am putut marca plata în Shopify: ${toProcessingError(err).message}`);
      }
    }
  }
}

export { FINAL_STATUSES };
