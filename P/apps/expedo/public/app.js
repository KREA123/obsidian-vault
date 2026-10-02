// Expedo dashboard — dependency-free SPA. Hash routes:
//   #/  #/orders?status=..  #/orders/:id  #/activity  #/settings/:section
// Every text goes through t() (src/i18n: the same engine the server uses, served as /i18n/core.js, and the
// `ui.` part of the catalog, served as /i18n/<locale>.json). Errors and history entries come translated
// from the server, in the same language (the X-Expedo-Locale header / the store's Language setting).
import { createTranslator, formatMoney, formatDate, formatDay, normalizeLocale } from '/i18n/core.js';

// ---------- tiny helpers ----------
class Raw { constructor(s) { this.s = s; } toString() { return this.s; } }
const raw = (s) => new Raw(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function html(strings, ...vals) {
  let out = '';
  strings.forEach((s, i) => {
    out += s;
    if (i < vals.length) {
      const v = vals[i];
      if (v == null || v === false) return;
      out += Array.isArray(v) ? v.map((x) => (x instanceof Raw ? x.s : esc(x))).join('') : v instanceof Raw ? v.s : esc(v);
    }
  });
  return raw(out);
}
/** Only http(s) links from providers end up in href (never javascript:). */
const safeUrl = (u) => (/^https?:\/\//i.test(String(u || '')) ? String(u) : '');
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// ---------- i18n ----------
const i18n = { locale: 'en', t: null };
/** Text from the catalog in the current language: t('ui.orders.title'), t('ui.orders.count', { count: 3 }). */
const t = (key, params) => (i18n.t ? i18n.t(i18n.locale, key, params) : key);
const money = (n, currency) => formatMoney(i18n.locale, n, currency);
const fmtDate = (s) => formatDate(i18n.locale, s);
const fmtDay = (s) => formatDay(i18n.locale, s);

/** Inside the Shopify admin: the admin user's language (App Bridge, or the `locale` param Shopify adds). */
function adminLocale() {
  if (!window.__EMBEDDED__) return '';
  return window.shopify?.config?.locale || new URLSearchParams(location.search).get('locale') || '';
}

async function loadLocale(locale) {
  const loc = normalizeLocale(locale);
  if (i18n.t && i18n.locale === loc) return;
  const res = await fetch(`/i18n/${loc}.json`);
  const catalog = res.ok ? await res.json() : {};
  i18n.locale = loc;
  i18n.t = createTranslator({ [loc]: catalog }).t;
  try { localStorage.setItem('expedo.locale', loc); } catch {}
  document.documentElement.lang = loc;
  document.title = t('ui.app.title');
  // Static parts of index.html: data-i18n="key" (text), data-i18n-attr="attr:key;attr:key".
  $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $$('[data-i18n-attr]').forEach((el) => el.dataset.i18nAttr.split(';').forEach((pair) => {
    const [attr, key] = pair.split(':');
    el.setAttribute(attr, t(key));
  }));
  $$('[data-i18n-href]').forEach((el) => { el.setAttribute('href', t(el.dataset.i18nHref)); });
}

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  cog: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  truck: '<path d="M1 3h15v13H1zM16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  print: '<path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  clip: '<path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
};
const icon = (name) => raw(`<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ''}</svg>`);

function toast(message, kind = '') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), kind === 'bad' ? 9000 : 4500);
}

// ---------- API ----------
const state = { meta: null, me: null, selected: new Set(), lastList: [] };
const storeId = () => { try { return localStorage.getItem('expedo.store') || ''; } catch { return ''; } };

async function authHeaders() {
  // Custom header on every request: the server refuses cookie-authenticated writes without it (CSRF).
  const h = { 'X-Expedo-Request': '1' };
  if (window.__EMBEDDED__ && window.shopify?.idToken) h.Authorization = `Bearer ${await window.shopify.idToken()}`;
  if (adminLocale()) h['X-Expedo-Locale'] = adminLocale();
  if (storeId()) h['X-Store-Id'] = storeId();
  return h;
}

async function api(path, { method = 'GET', body } = {}) {
  const headers = await authHeaders();
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && data.error?.code === 'LOGIN_REQUIRED') { showLogin(); throw new Error('login'); }
  if (!res.ok) {
    const err = new Error(data.error?.message || t('ui.errors.http', { status: res.status }));
    err.info = data.error;
    throw err;
  }
  return data;
}

/** Opens a PDF (labels, invoice) in a new tab; works embedded too by fetching with the token. */
async function openPdf(path) {
  const win = window.open('', '_blank');
  try {
    const res = await fetch(`/api${path}`, { headers: await authHeaders() });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error?.message || t('ui.errors.pdf'));
    }
    const url = URL.createObjectURL(await res.blob());
    if (win) win.location = url; else location.href = url;
  } catch (err) {
    win?.close();
    toast(err.message, 'bad');
  }
}

/** Downloads a file from the API (CSV export, customer data) with the auth headers. */
async function download(path, filename) {
  try {
    const res = await fetch(`/api${path}`, { headers: await authHeaders() });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error?.message || t('ui.errors.download'));
    }
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(await res.blob()), download: filename });
    a.click();
  } catch (err) {
    toast(err.message, 'bad');
  }
}

function showLogin() {
  $('.sidebar').hidden = true;
  $('#view').innerHTML = html`
    <div class="login card">
      <h1 style="margin-bottom:6px">Expedo</h1>
      <p class="muted">${window.__LOGIN_ENABLED__ ? t('ui.login.withPassword') : t('ui.login.openFromShopify')}</p>
      ${window.__LOGIN_ENABLED__ ? html`
      <form method="post" action="/login" style="display:flex;flex-direction:column;gap:10px">
        <input type="password" name="password" placeholder="${t('ui.login.password')}" aria-label="${t('ui.login.password')}" autofocus required>
        ${location.search.includes('login=fail') ? html`<div class="result bad">${t('ui.login.wrong')}</div>` : ''}
        <button class="btn primary">${t('ui.login.submit')}</button>
      </form>` : ''}
    </div>`;
}

// ---------- shared bits ----------
const STATUS_KIND = { ready: 'info', needs_attention: 'bad', on_hold: 'warn', shipped: 'info', in_transit: 'info', delivered: 'ok', returned: 'warn', cancelled: '', new: '' };
const statusBadge = (o) => html`<span class="badge ${STATUS_KIND[o.status] || ''}">${o.statusLabel || state.meta.statuses[o.status] || o.status}</span>`;
const payPill = (o) => o.paymentMethod === 'cod' ? html`<span class="pill cod">${t('ui.pay.cod')}</span>` : o.paymentMethod === 'card' ? html`<span class="pill card">${t('ui.pay.card')}</span>` : html`<span class="pill">${o.paymentMethod || '—'}</span>`;
const courierName = (id) => state.meta.couriers.find((c) => c.id === id)?.name || id || '—';
const invoicerName = (id) => state.meta.invoicers.find((c) => c.id === id)?.name || id || '—';

function setActiveNav(route) {
  $$('#nav a').forEach((a) => a.classList.toggle('active', a.dataset.route === route));
}

async function refreshChrome() {
  state.me = await api('/me');
  // The server decides the language (Shopify admin language / store setting); follow it.
  if (state.me.locale && state.me.locale !== i18n.locale) await loadLocale(state.me.locale);
  $('#test-banner').hidden = !state.me.testMode;
  $('#store-name').textContent = state.me.store.name || state.me.store.shop;
  const sw = $('#store-switch');
  if (state.me.stores.length > 1) {
    sw.hidden = false;
    sw.innerHTML = state.me.stores.map((s) => html`<option value="${s.id}" ${s.id === state.me.store.id ? 'selected' : ''}>${s.name || s.shop}</option>`).join('');
  }
  $('#logout-form').hidden = !!state.me.embedded || !window.__LOGIN_ENABLED__;
  const stats = await api('/stats');
  const nav = $('#nav-attention');
  nav.hidden = !stats.attention;
  nav.textContent = stats.attention;
}

// ---------- dashboard ----------
async function viewDashboard() {
  setActiveNav('dashboard');
  const [stats, ev] = await Promise.all([api('/stats'), api('/events')]);
  const attention = await api('/orders?status=needs_attention');
  $('#view').innerHTML = html`
    <div class="page-head"><h1>${t('ui.dashboard.title')}</h1><div class="spacer"></div>
      <button class="btn" id="btn-track">${icon('refresh')} ${t('ui.dashboard.checkParcels')}</button>
      <a class="btn primary" href="#/orders?status=ready">${icon('truck')} ${t('ui.dashboard.process', { count: stats.toProcess })}</a>
    </div>
    <div class="stats">
      <a class="stat" href="#/orders?status=ready"><div class="label">${t('ui.dashboard.toProcess')}</div><div class="value">${stats.toProcess}</div><div class="sub">${t('ui.dashboard.toProcessSub')}</div></a>
      <a class="stat ${stats.attention ? 'alert' : ''}" href="#/orders?status=needs_attention"><div class="label">${t('ui.dashboard.attention')}</div><div class="value">${stats.attention}</div><div class="sub">${t('ui.dashboard.attentionSub')}</div></a>
      <a class="stat" href="#/orders?status=in_transit"><div class="label">${t('ui.dashboard.inTransit')}</div><div class="value">${stats.inTransit}</div><div class="sub">${t('ui.dashboard.awbToday', { count: stats.awbToday })}</div></a>
      <div class="stat"><div class="label">${t('ui.dashboard.codPending')}</div><div class="value">${money(stats.codPending.v)}</div><div class="sub">${t('ui.dashboard.codPendingSub', { count: stats.codPending.c })}</div></div>
      <div class="stat"><div class="label">${t('ui.dashboard.codCollected')}</div><div class="value">${money(stats.codCollected30.v)}</div><div class="sub">${t('ui.dashboard.codCollectedSub', { count: stats.codCollected30.c })}</div></div>
    </div>
    <div class="cols">
      <div>
        <div class="card">
          <h2>${t('ui.dashboard.todo')}</h2>
          ${attention.orders.length ? html`<table><tbody>${attention.orders.slice(0, 8).map((o) => html`
            <tr data-open="${o.id}"><td><span class="order-name">${o.name}</span><div class="faint small">${o.customer}</div></td>
            <td>${issueLines(o, 1)}</td></tr>`)}</tbody></table>`
            : html`<div class="empty">${t('ui.dashboard.nothingBlocked')} ${icon('check')}</div>`}
        </div>
        <div class="card">
          <h2>${t('ui.dashboard.couriers')}</h2>
          ${stats.byCourier.length ? html`<table><thead><tr><th>${t('ui.dashboard.courier')}</th><th class="num">${t('ui.dashboard.awbs')}</th><th class="num">${t('ui.dashboard.delivered')}</th><th class="num">${t('ui.dashboard.returned')}</th></tr></thead><tbody>
            ${stats.byCourier.map((c) => html`<tr><td>${courierName(c.courier)}</td><td class="num">${c.c}</td><td class="num">${c.delivered}</td><td class="num">${c.returned}${c.c ? html` <span class="faint small">(${Math.round((c.returned / c.c) * 100)}%)</span>` : ''}</td></tr>`)}
          </tbody></table>` : html`<div class="empty">${t('ui.dashboard.noAwb')}</div>`}
          <div class="form-actions"><button class="btn small" id="btn-cod">${icon('download')} ${t('ui.dashboard.codExport')}</button><span class="muted small">${t('ui.dashboard.shippingCost', { amount: money(stats.shippingCost30) })}</span></div>
        </div>
      </div>
      <div class="card">
        <h2>${t('ui.dashboard.recent')}</h2>
        ${eventList(ev.events.slice(0, 14), true)}
        <div class="form-actions"><a href="#/activity">${t('ui.dashboard.allActivity')}</a></div>
      </div>
    </div>`;
  $$('[data-open]').forEach((tr) => tr.addEventListener('click', () => openOrder(Number(tr.dataset.open))));
  $('#btn-track').onclick = trackNow;
  $('#btn-cod').onclick = () => download('/cod.csv', t('ui.files.cod'));
  bindDataDownloads($('#view'));
}

async function trackNow() {
  const r = await api('/track', { method: 'POST' });
  toast(t('ui.dashboard.tracked', { checked: r.checked, changed: r.changed }), 'ok');
  route();
}

function eventList(events, withOrder) {
  if (!events.length) return html`<div class="empty">${t('ui.events.empty')}</div>`;
  return html`<ul class="timeline">${events.map((e) => html`
    <li class="${e.level}">
      <div>${withOrder && e.order_name ? html`<a href="#/orders/${e.order_id}">${e.order_name}</a> · ` : ''}${e.message}</div>
      ${e.data?.hint ? html`<div class="hint">${e.data.hint}</div>` : ''}
      ${e.step === 'gdpr' && e.data?.orderIds?.length ? html`<button class="btn small" data-export="${e.data.orderIds.join(',')}">${icon('download')} ${t('ui.events.downloadCustomer')}</button>` : ''}
      <div class="when">${fmtDate(e.at)}</div>
    </li>`)}</ul>`;
}

/** "Download data" buttons (GDPR data request): a JSON file with everything Expedo holds. */
function bindDataDownloads(root) {
  $$('[data-export]', root).forEach((b) => b.addEventListener('click', (e) => {
    e.stopPropagation();
    download(`/customer-export?ids=${b.dataset.export}`, t('ui.files.customerData'));
  }));
}

/** Small badge: the customer refused parcels before (core/customers.js). */
const refusedBadge = (n) => (n ? html`<span class="badge warn plain" title="${t('ui.refused.title', { count: n })}">${t('ui.refused.badge', { count: n })}</span>` : '');

function issueLines(o, max = 3) {
  const list = [];
  if (o.lastError) list.push({ level: 'error', message: o.lastError.message, hint: o.lastError.hint });
  for (const i of o.issues || []) if (!list.some((x) => x.message === i.message)) list.push(i);
  return list.slice(0, max).map((i) => html`<div class="issue-line ${i.level}" title="${i.hint || ''}">● <span>${i.message}${i.hint ? html` <span class="faint">— ${i.hint}</span>` : ''}</span></div>`);
}

// ---------- orders ----------
const TABS = ['open', 'ready', 'needs_attention', 'on_hold', 'shipped', 'in_transit', 'delivered', 'returned', 'all'];

function hashQuery() {
  const [, q = ''] = location.hash.split('?');
  return new URLSearchParams(q);
}

async function viewOrders() {
  setActiveNav('orders');
  const q = hashQuery();
  const status = q.get('status') || 'open';
  const search = q.get('q') || '';
  const page = Number(q.get('page') || 1);
  const ids = q.get('ids') || '';
  const data = await api(`/orders?status=${encodeURIComponent(status)}&q=${encodeURIComponent(search)}&page=${page}${ids ? `&ids=${encodeURIComponent(ids)}` : ''}`);
  state.lastList = data.orders;
  for (const id of [...state.selected]) if (!data.orders.some((o) => o.id === id)) state.selected.delete(id);
  const c = data.counts;
  const openCount = (c.ready || 0) + (c.needs_attention || 0) + (c.on_hold || 0) + (c.new || 0);
  const count = (k) => (k === 'open' ? openCount : k === 'all' ? Object.values(c).reduce((a, b) => a + b, 0) : c[k] || 0);
  const pages = Math.ceil(data.total / data.pageSize);

  $('#view').innerHTML = html`
    <div class="page-head"><h1>${t('ui.orders.title')}</h1><div class="spacer"></div>
      <button class="btn" id="btn-sync">${icon('refresh')} ${t('ui.orders.sync')}</button>
    </div>
    <nav class="tabs">${TABS.map((k) => html`<a href="#/orders?status=${k}" class="${status === k ? 'active' : ''}">${t(`ui.orders.tabs.${k}`)}<span class="count ${k === 'needs_attention' && c.needs_attention ? 'bad' : ''}">${count(k)}</span></a>`)}</nav>
    <div class="toolbar">
      <input type="search" id="search" placeholder="${t('ui.orders.search')}" aria-label="${t('ui.orders.search')}" title="${t('ui.orders.searchTitle')}" value="${search}">
      <span class="muted small">${t('ui.orders.count', { count: data.total })}</span>
      ${ids ? html`<a class="btn small" href="#/orders?status=${status}">${t('ui.orders.onlyProcessed')} ${icon('x')}</a>` : ''}
    </div>
    <div class="table-wrap">
      ${data.orders.length ? html`<table>
        <thead><tr>
          <th class="check"><input type="checkbox" id="check-all" aria-label="${t('ui.orders.selectAll')}"></th>
          <th>${t('ui.orders.order')}</th><th>${t('ui.orders.customer')}</th><th class="num">${t('ui.orders.total')}</th><th class="hide-sm">${t('ui.orders.shipping')}</th><th class="hide-sm">${t('ui.orders.invoice')}</th><th>${t('ui.orders.status')}</th>
        </tr></thead>
        <tbody>${data.orders.map((o) => html`
          <tr data-id="${o.id}" class="${state.selected.has(o.id) ? 'selected' : ''}">
            <td class="check"><input type="checkbox" data-check="${o.id}" ${state.selected.has(o.id) ? 'checked' : ''} aria-label="${t('ui.orders.select', { name: o.name })}"></td>
            <td><div class="order-name">${o.name} ${o.testMode && o.awb ? html`<span class="pill test">${t('ui.orders.test')}</span>` : ''}</div><div class="faint small nowrap">${fmtDate(o.createdAt)}</div></td>
            <td><div>${o.redactedAt ? html`<span class="faint">${t('ui.orders.redacted')}</span>` : o.company || o.customer} ${refusedBadge(o.refusedBefore)}</div><div class="muted small">${[o.city, o.county].filter(Boolean).join(', ')}${o.city || o.county ? ' · ' : ''}${t('ui.orders.items', { count: o.items })}</div>${issueLines(o, 2)}</td>
            <td class="num"><div class="nowrap">${money(o.total, o.currency)}</div><div>${payPill(o)}</div></td>
            <td class="hide-sm">${o.awb ? html`<div>${courierName(o.courier)}</div><div class="mono">${o.awb}</div>${o.trackingText ? html`<div class="faint small">${o.trackingText}</div>` : ''}`
              : html`<span class="faint small">${o.courier ? `→ ${courierName(o.courier)}` : '—'}</span><div class="faint small">${o.shippingMethod || ''}</div>`}</td>
            <td class="hide-sm">${o.invoice ? html`<span class="nowrap">${o.invoice}</span>` : html`<span class="faint">—</span>`}</td>
            <td>${statusBadge(o)}</td>
          </tr>`)}</tbody></table>`
        : html`<div class="empty">${t('ui.orders.empty')}</div>`}
    </div>
    ${pages > 1 ? html`<div class="form-actions">
      ${page > 1 ? html`<a class="btn small" href="#/orders?status=${status}&q=${encodeURIComponent(search)}${ids ? `&ids=${ids}` : ''}&page=${page - 1}">${t('ui.orders.prev')}</a>` : ''}
      <span class="muted small">${t('ui.orders.page', { page, pages })}</span>
      ${page < pages ? html`<a class="btn small" href="#/orders?status=${status}&q=${encodeURIComponent(search)}${ids ? `&ids=${ids}` : ''}&page=${page + 1}">${t('ui.orders.next')}</a>` : ''}</div>` : ''}
    <div class="bulkbar" id="bulkbar" hidden>
      <span class="count" id="bulk-count"></span>
      <button class="btn primary" data-bulk="all">${icon('truck')} ${t('ui.orders.bulk.all')}</button>
      <button class="btn" data-bulk="awb">${t('ui.orders.bulk.awb')}</button>
      <button class="btn" data-bulk="invoice">${t('ui.orders.bulk.invoice')}</button>
      <button class="btn" data-bulk="labels">${icon('print')} ${t('ui.orders.bulk.labels')}</button>
      <button class="btn" data-bulk="picking">${icon('clip')} ${t('ui.orders.bulk.picking')}</button>
      <button class="btn" data-bulk="clear" aria-label="${t('ui.orders.bulk.clear')}" title="${t('ui.orders.bulk.clear')}">${icon('x')}</button>
    </div>`;

  const updateBulk = () => {
    $('#bulkbar').hidden = !state.selected.size;
    $('#bulk-count').textContent = t('ui.orders.bulk.selected', { count: state.selected.size });
    $$('tbody tr[data-id]').forEach((tr) => tr.classList.toggle('selected', state.selected.has(Number(tr.dataset.id))));
  };
  updateBulk();

  $$('tbody tr[data-id]').forEach((tr) => tr.addEventListener('click', (e) => {
    const id = Number(tr.dataset.id);
    if (e.target.matches('input[type=checkbox]')) {
      e.target.checked ? state.selected.add(id) : state.selected.delete(id);
      updateBulk();
      return;
    }
    openOrder(id);
  }));
  $('#check-all')?.addEventListener('change', (e) => {
    data.orders.forEach((o) => (e.target.checked ? state.selected.add(o.id) : state.selected.delete(o.id)));
    $$('[data-check]').forEach((cb) => { cb.checked = e.target.checked; });
    updateBulk();
  });
  let timer;
  $('#search').addEventListener('input', (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { location.hash = `#/orders?status=${status}&q=${encodeURIComponent(e.target.value)}`; }, 350);
  });
  $('#btn-sync').onclick = async (e) => {
    busy(e.currentTarget, true);
    try { const r = await api('/sync', { method: 'POST', body: { days: 14 } }); toast(t('ui.orders.synced', { count: r.imported }), 'ok'); route(); }
    catch (err) { toast(err.message, 'bad'); busy(e.currentTarget, false); }
  };
  $$('[data-bulk]').forEach((b) => b.addEventListener('click', () => bulk(b.dataset.bulk, b)));
  if (search) { const s = $('#search'); s.focus(); s.setSelectionRange(s.value.length, s.value.length); }
}

function busy(btn, on) {
  if (!btn) return;
  if (on) { btn.dataset.label = btn.innerHTML; btn.innerHTML = `<span class="spinner"></span> ${esc(t('ui.common.working'))}`; btn.disabled = true; }
  else { btn.innerHTML = btn.dataset.label || btn.innerHTML; btn.disabled = false; }
}

async function bulk(action, btn) {
  const ids = [...state.selected];
  if (action === 'clear') { state.selected.clear(); return route(); }
  if (action === 'labels') return openPdf(`/labels.pdf?ids=${ids.join(',')}`);
  if (action === 'picking') return picking(ids);
  const steps = { all: ['awb', 'invoice', 'fulfill'], awb: ['awb', 'fulfill'], invoice: ['invoice'] }[action];
  busy(btn, true);
  try {
    const r = await api('/orders/process', { method: 'POST', body: { ids, steps } });
    if (r.failed) {
      const first = r.results.find((x) => !x.ok);
      toast(t('ui.orders.bulk.partial', { ok: r.ok, failed: r.failed, name: first.name, error: first.error?.message }), 'bad');
    } else {
      toast(t('ui.orders.bulk.done', { count: r.ok }), 'ok');
    }
    const done = r.results.filter((x) => x.ok && x.awb).map((x) => x.id);
    // Show exactly the orders just processed, still selected, so "Labels" is one click away
    // (they are not necessarily on the first page of "Shipped").
    if (done.length && steps.includes('awb')) {
      state.selected = new Set(done);
      location.hash = `#/orders?status=all&ids=${done.join(',')}`;
    } else route();
    refreshChrome();
  } catch (err) {
    toast(err.message, 'bad');
    busy(btn, false);
  }
}

async function picking(ids) {
  const p = await api(`/picking?ids=${ids.join(',')}`);
  const w = window.open('', '_blank');
  if (!w) return toast(t('ui.picking.popup'), 'bad');
  w.document.write(`<!doctype html><html lang="${i18n.locale}"><meta charset="utf-8"><title>${esc(t('ui.picking.title'))}</title>
    <style>body{font:14px system-ui;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px 8px;text-align:left}th{background:#f3f3f3}.q{font-size:18px;font-weight:700;text-align:center}</style>
    <h2>${esc(t('ui.picking.heading', { date: new Date().toLocaleString(i18n.locale === 'ro' ? 'ro-RO' : 'en-US') }))}</h2><p>${esc(t('ui.picking.orders', { list: p.orders.join(', ') }))}</p>
    <table><tr><th>✓</th><th>${esc(t('ui.picking.sku'))}</th><th>${esc(t('ui.picking.product'))}</th><th>${esc(t('ui.picking.qty'))}</th><th>${esc(t('ui.picking.ordersCol'))}</th></tr>
    ${p.items.map((i) => `<tr><td style="width:24px"></td><td>${esc(i.sku)}</td><td>${esc(i.title)}</td><td class="q">${i.quantity}</td><td>${esc(i.orders.join(', '))}</td></tr>`).join('')}
    </table><script>print()<\/script>`);
  w.document.close();
}

// ---------- order drawer ----------
function closeDrawer() {
  $('#drawer').hidden = true;
  if (location.hash.match(/^#\/orders\/\d+/)) history.replaceState(null, '', state.backHash || '#/orders');
}
$('#drawer').addEventListener('click', (e) => { if (e.target.matches('[data-close]')) closeDrawer(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('#drawer').hidden) closeDrawer(); });

function openOrder(id) {
  state.backHash = /^#\/orders\/\d+/.test(location.hash) ? state.backHash : location.hash || '#/orders';
  history.replaceState(null, '', `#/orders/${id}`);
  renderOrder(id);
}

async function renderOrder(id) {
  const panel = $('#drawer .drawer-panel');
  $('#drawer').hidden = false;
  // Another order's details must never stay on screen (or keep its buttons) while this one loads.
  if (state.drawerId !== id || !panel.innerHTML) panel.innerHTML = '<div class="empty"><span class="spinner"></span></div>';
  state.drawerId = id;
  const token = (state.drawerToken = (state.drawerToken || 0) + 1);
  let data;
  try { data = await api(`/orders/${id}`); } catch (err) { if (token === state.drawerToken) panel.innerHTML = html`<div class="error-box">${err.message}</div>`; return; }
  if (token !== state.drawerToken) return; // a newer render (other order or refresh) won
  const { order: o, plan, events, customer } = data;
  const d = o.data;
  const a = { ...(d.shippingAddress || {}), ...(o.overrides.address || {}) };
  const errors = [];
  if (o.lastError) errors.push({ level: 'error', message: o.lastError.message, hint: o.lastError.hint, details: o.lastError.details });
  for (const i of o.issues) if (!errors.some((e) => e.message === i.message)) errors.push(i);
  const canProcess = !o.awb && !o.cancelled;
  const hasTestData = (o.testMode && o.awb) || (o.invoiceTest && o.invoice);

  panel.innerHTML = html`
    <div class="drawer-head">
      <h1>${o.name}</h1> ${statusBadge(o)} ${(o.testMode && o.awb) || (o.invoiceTest && o.invoice) ? html`<span class="pill test">${t('ui.order.test')}</span>` : ''}
      <div class="spacer"></div>
      <button class="btn small" data-close aria-label="${t('ui.common.close')}" title="${t('ui.common.close')}">${icon('x')}</button>
    </div>
    ${errors.map((e) => html`<div class="${e.level === 'warning' ? 'warn-box' : 'error-box'}">
      <strong>${e.message}</strong>${e.hint ? html`<div class="hint">${e.hint}</div>` : ''}
      ${e.details ? html`<details class="small"><summary class="muted">${t('ui.order.technical')}</summary><pre class="mono" style="white-space:pre-wrap">${typeof e.details === 'string' ? e.details : JSON.stringify(e.details, null, 2)}</pre></details>` : ''}
    </div>`)}
    <div class="actions" style="margin-bottom:16px">
      ${canProcess ? html`<button class="btn primary" data-act="process">${icon('truck')} ${t('ui.order.actions.process')}</button>` : ''}
      ${!canProcess && !o.invoice && o.awb ? html`<button class="btn" data-act="invoice">${icon('file')} ${t('ui.order.actions.invoice')}</button>` : ''}
      ${o.awb ? html`<button class="btn" data-act="label">${icon('print')} ${t('ui.order.actions.label')}</button>` : ''}
      ${o.invoice ? html`<button class="btn" data-act="invoice-pdf">${icon('file')} ${t('ui.order.actions.invoicePdf')}</button>` : ''}
      ${o.awb && !o.fulfilledAt && !o.testMode && !o.cancelled && !state.me.testMode ? html`<button class="btn" data-act="fulfill">${t('ui.order.actions.fulfill')}</button>` : ''}
      ${hasTestData && !state.me.testMode ? html`<button class="btn" data-act="reset-test" title="${t('ui.order.actions.resetTestTitle')}">${t('ui.order.actions.resetTest')}</button>` : ''}
      ${o.awb ? html`<button class="btn danger" data-act="cancel-awb">${t('ui.order.actions.cancelAwb')}</button>` : ''}
      ${o.invoice ? html`<button class="btn danger" data-act="storno">${t('ui.order.actions.storno')}</button>` : ''}
      ${!o.awb ? html`<button class="btn" data-act="hold">${o.overrides.hold ? t('ui.order.actions.unhold') : t('ui.order.actions.hold')}</button>` : ''}
      <button class="btn" data-act="refresh">${icon('refresh')} ${t('ui.order.actions.refresh')}</button>
    </div>

    <div class="card">
      <h2>${t('ui.order.shipping.title')}</h2>
      <dl class="kv">
        ${o.awb ? html`<dt>AWB</dt><dd><span class="mono">${o.awb}</span> · ${courierName(o.courier)} ${safeUrl(o.trackingUrl) ? html`· <a href="${safeUrl(o.trackingUrl)}" target="_blank" rel="noopener">${t('ui.order.shipping.track')}</a>` : ''}<div class="muted small">${o.trackingText || ''}</div>${o.trackingDetail ? html`<div class="faint small">${t('ui.order.shipping.courierSays', { text: o.trackingDetail })}</div>` : ''}</dd>` : ''}
        <dt>${t('ui.order.shipping.payment')}</dt><dd>${payPill(o)} ${o.paymentMethod === 'cod' ? html`${t('ui.order.shipping.cod')} <strong>${money(o.awb ? o.codAmount : plan.cod)}</strong>${o.codCollectedAt ? html` · <span class="badge ok">${t('ui.order.shipping.collected', { date: fmtDay(o.codCollectedAt) })}</span>` : ''}` : d.financialStatus === 'PAID' ? t('ui.order.shipping.paidOnline') : d.financialStatus}</dd>
        <dt>${t('ui.order.shipping.method')}</dt><dd>${d.shippingMethod || '—'}${plan.lockerId ? html` · ${t('ui.order.shipping.locker')} <span class="mono">${plan.lockerId}</span>` : ''}</dd>
        ${plan.matchedRules.length ? html`<dt>${t('ui.order.shipping.rules')}</dt><dd>${plan.matchedRules.join(', ')}</dd>` : ''}
        ${o.invoice ? html`<dt>${t('ui.order.shipping.invoice')}</dt><dd>${o.invoice} ${safeUrl(o.invoiceUrl) ? html`· <a href="${safeUrl(o.invoiceUrl)}" target="_blank" rel="noopener">${t('ui.order.shipping.open')}</a>` : ''}</dd>` : ''}
      </dl>
      ${canProcess ? html`
      <form id="plan-form" style="margin-top:14px">
        <div class="grid3">
          <label class="field">${t('ui.order.shipping.courier')}
            <select name="courier">${[['', t('ui.order.shipping.courierDefault', { courier: courierName(plan.courier) })], ...state.meta.couriers.map((c) => [c.id, c.name])].map(([v, l]) => html`<option value="${v}" ${(o.overrides.courier || '') === v ? 'selected' : ''}>${l}</option>`)}</select>
          </label>
          <label class="field">${t('ui.order.shipping.parcels')} <input type="number" name="parcels" min="1" value="${o.overrides.parcels ?? ''}" placeholder="${plan.parcels}"></label>
          <label class="field">${t('ui.order.shipping.weight')} <input type="number" name="weightKg" min="0.1" step="0.1" value="${o.overrides.weightKg ?? ''}" placeholder="${plan.weightKg}"></label>
          <label class="field">${t('ui.order.shipping.codAmount')} <input type="number" name="cod" min="0" step="0.01" value="${o.overrides.cod ?? ''}" placeholder="${plan.cod}"></label>
          <label class="field">${t('ui.order.shipping.notes')} <input type="text" name="notes" value="${o.overrides.notes ?? ''}" placeholder="${t('ui.order.shipping.notesPlaceholder')}"></label>
          <label class="field">${t('ui.order.shipping.lockerId')} <input type="text" name="lockerId" value="${o.overrides.lockerId ?? ''}" placeholder="${plan.lockerId || t('ui.order.shipping.lockerPlaceholder')}"></label>
        </div>
        <label class="check" style="margin-top:10px"><input type="checkbox" name="openPackage" ${plan.openPackage ? 'checked' : ''}> ${t('ui.order.shipping.openPackage')}</label>
        <label class="check" style="margin-top:6px"><input type="checkbox" name="skipInvoice" ${plan.skipInvoice ? 'checked' : ''}> ${t('ui.order.shipping.skipInvoice')}</label>
        <div class="form-actions"><button class="btn small">${t('ui.common.save')}</button></div>
      </form>` : ''}
    </div>

    ${o.redactedAt ? html`<div class="card"><h2>${t('ui.order.redacted.title')}</h2><p class="muted small" style="margin:0">${t('ui.order.redacted.text', { date: fmtDay(o.redactedAt) })}</p></div>` : html`
    <div class="card">
      <h2>${t('ui.order.address.title')} ${o.overrides.address ? html`<span class="badge warn plain">${t('ui.order.address.edited')}</span>` : ''}</h2>
      ${canProcess ? html`
      <form id="addr-form">
        <div class="grid2">
          <label class="field">${t('ui.order.address.name')} <input type="text" name="name" value="${a.name || [a.firstName, a.lastName].filter(Boolean).join(' ')}"></label>
          <label class="field">${t('ui.order.address.phone')} <input type="text" name="phone" value="${a.phone}"></label>
          <label class="field">${t('ui.order.address.company')} <input type="text" name="company" value="${a.company}"></label>
          <label class="field">${t('ui.order.address.county')}
            <select name="province"><option value="">${t('ui.order.address.choose')}</option>${state.meta.counties.map((c) => html`<option value="${c.name}" ${plan.address.countyCode === c.code ? 'selected' : ''}>${c.name}</option>`)}</select>
          </label>
          <label class="field">${t('ui.order.address.city')} <input type="text" name="city" value="${a.city}"><span class="help">${t('ui.order.address.normalized', { city: `${plan.address.city || '—'}${plan.address.sector ? `, Sector ${plan.address.sector}` : ''}` })}</span></label>
          <label class="field">${t('ui.order.address.zip')} <input type="text" name="zip" value="${a.zip}"></label>
        </div>
        <label class="field" style="margin-top:12px">${t('ui.order.address.street')} <input type="text" name="address1" value="${a.address1}"></label>
        <label class="field" style="margin-top:12px">${t('ui.order.address.details')} <input type="text" name="address2" value="${a.address2}"></label>
        <div class="form-actions"><button class="btn small">${t('ui.order.address.save')}</button>${o.overrides.address ? html`<button type="button" class="link small" id="addr-reset">${t('ui.order.address.reset')}</button>` : ''}
          <span class="muted small">${t('ui.order.address.note')}</span></div>
      </form>` : html`<dl class="kv"><dt>${t('ui.order.address.recipient')}</dt><dd>${plan.address.name}${plan.address.company ? ` (${plan.address.company})` : ''}</dd><dt>${t('ui.order.address.phone')}</dt><dd>${plan.address.phone}</dd><dt>${t('ui.order.address.address')}</dt><dd>${plan.address.street}, ${plan.address.city}${plan.address.sector ? `, Sector ${plan.address.sector}` : ''}, ${plan.address.county} ${plan.address.zip}</dd></dl>`}
    </div>
    ${customer?.orders.length ? html`<div class="card">
      <h2>${t('ui.order.history.title')} ${customer.returned ? html`<span class="badge warn plain">${t('ui.refused.badge', { count: customer.returned })}</span>` : ''}</h2>
      <p class="muted small" style="margin-top:-6px">${t('ui.order.history.summary', { delivered: customer.delivered, returned: customer.returned })}</p>
      <table class="lines"><tbody>${customer.orders.map((h) => html`<tr data-open="${h.id}" class="clickable">
        <td><a href="#/orders/${h.id}">${h.name}</a></td><td class="muted small nowrap">${fmtDay(h.createdAt)}</td>
        <td>${h.refused ? html`<span class="badge warn">${t(h.cod ? 'ui.order.history.refusedCod' : 'ui.order.history.refused')}</span>` : statusBadge({ status: h.status })}</td></tr>`)}</tbody></table>
    </div>` : ''}`}

    <div class="card">
      <h2>${t('ui.order.products.title')}</h2>
      <table class="lines"><thead><tr><th>${t('ui.order.products.product')}</th><th>${t('ui.order.products.sku')}</th><th class="num">${t('ui.order.products.qty')}</th><th class="num">${t('ui.order.products.price')}</th></tr></thead><tbody>
        ${d.lines.map((l) => html`<tr><td>${l.title}${l.variantTitle ? html` <span class="muted">· ${l.variantTitle}</span>` : ''}</td><td class="mono">${l.sku}</td><td class="num">${l.quantity}</td><td class="num nowrap">${money(l.unitPrice, d.currency)}</td></tr>`)}
        ${d.shippingLines.map((s) => html`<tr><td class="muted">${t('ui.order.products.shipping', { title: s.title })}</td><td></td><td class="num">1</td><td class="num nowrap">${money(s.price, d.currency)}</td></tr>`)}
        <tr><td colspan="3"><strong>${t('ui.order.products.total')}</strong></td><td class="num nowrap"><strong>${money(d.total, d.currency)}</strong></td></tr>
      </tbody></table>
      ${d.company ? html`<p class="small" style="margin:10px 0 0">${t('ui.order.products.company')} <strong>${d.company.name}</strong> · ${t('ui.order.products.vatCode')} ${d.company.vatCode}${d.company.regCom ? ` · ${d.company.regCom}` : ''}</p>` : ''}
      ${d.note ? html`<p class="small muted" style="margin:10px 0 0">${t('ui.order.products.note', { note: d.note })}</p>` : ''}
    </div>

    <div class="card"><h2>${t('ui.order.timeline')}</h2>${eventList([...events].reverse(), false)}</div>`;

  $$('[data-close]', panel).forEach((b) => b.addEventListener('click', closeDrawer));
  $$('tr[data-open]', panel).forEach((tr) => tr.addEventListener('click', (e) => { e.preventDefault(); openOrder(Number(tr.dataset.open)); }));
  const after = async (msg) => { if (msg) toast(msg, 'ok'); await renderOrder(id); refreshList(); refreshChrome(); };
  const run = async (btn, fn) => { busy(btn, true); try { await fn(); } catch (err) { toast(err.message, 'bad'); await renderOrder(id); } };

  $$('[data-act]', panel).forEach((btn) => btn.addEventListener('click', () => {
    const act = btn.dataset.act;
    if (act === 'label') return openPdf(`/labels.pdf?ids=${id}`);
    if (act === 'invoice-pdf') return openPdf(`/orders/${id}/invoice.pdf`);
    if (act === 'cancel-awb' && !confirm(t('ui.order.confirm.cancelAwb', { awb: o.awb }))) return;
    if (act === 'storno' && !confirm(t('ui.order.confirm.storno', { invoice: o.invoice }))) return;
    if (act === 'reset-test' && !confirm(t('ui.order.confirm.resetTest'))) return;
    run(btn, async () => {
      if (act === 'process' || act === 'invoice' || act === 'fulfill') {
        const steps = { process: ['awb', 'invoice', 'fulfill'], invoice: ['invoice'], fulfill: ['fulfill'] }[act];
        // From the order page the merchant decides explicitly: held orders are processed too.
        const r = (await api('/orders/process', { method: 'POST', body: { ids: [id], steps, force: true } })).results[0];
        if (!r.ok) { toast(r.error?.message || t('ui.errors.failed'), 'bad'); return after(); }
        return after(r.awb ? t(r.invoice ? 'ui.order.toast.awbInvoice' : 'ui.order.toast.awb', { awb: r.awb, invoice: r.invoice }) : t('ui.order.toast.done'));
      }
      if (act === 'cancel-awb') { await api(`/orders/${id}/cancel-awb`, { method: 'POST' }); return after(t('ui.order.toast.awbCancelled')); }
      if (act === 'storno') { await api(`/orders/${id}/storno-invoice`, { method: 'POST' }); return after(t('ui.order.toast.reversed')); }
      if (act === 'reset-test') { await api(`/orders/${id}/reset-test`, { method: 'POST' }); return after(t('ui.order.toast.testReset')); }
      if (act === 'hold') { await api(`/orders/${id}`, { method: 'PATCH', body: { hold: o.overrides.hold ? null : true } }); return after(); }
      if (act === 'refresh') { await api(`/orders/${id}/refresh`, { method: 'POST' }); return after(t('ui.order.toast.reloaded')); }
    });
  }));

  $('#plan-form', panel)?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const body = Object.fromEntries(['courier', 'parcels', 'weightKg', 'cod', 'notes', 'lockerId'].map((k) => [k, f.get(k) === '' ? null : ['parcels', 'weightKg', 'cod'].includes(k) ? Number(f.get(k)) : f.get(k)]));
    // Unchanged checkboxes are not saved as overrides, so rules keep applying to them.
    const openPackage = f.get('openPackage') === 'on';
    const skipInvoice = f.get('skipInvoice') === 'on';
    if (openPackage !== !!plan.openPackage || o.overrides.openPackage != null) body.openPackage = openPackage;
    if (skipInvoice !== !!plan.skipInvoice || o.overrides.skipInvoice != null) body.skipInvoice = skipInvoice;
    try { await api(`/orders/${id}`, { method: 'PATCH', body }); } catch (err) { return toast(err.message, 'bad'); }
    after(t('ui.order.toast.saved'));
  });
  $('#addr-form', panel)?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    const [firstName, ...rest] = f.name.trim().split(/\s+/);
    try { await api(`/orders/${id}`, { method: 'PATCH', body: { address: { ...f, firstName, lastName: rest.join(' '), provinceCode: '' } } }); } catch (err) { return toast(err.message, 'bad'); }
    after(t('ui.order.toast.addressSaved'));
  });
  $('#addr-reset', panel)?.addEventListener('click', async () => {
    await api(`/orders/${id}`, { method: 'PATCH', body: { address: null } });
    after();
  });
}

async function refreshList() {
  if (!location.hash.startsWith('#/orders') && location.hash !== '' && location.hash !== '#/') return;
  // Re-render the page underneath without closing the drawer.
  const hash = state.backHash || '#/orders';
  if (hash.startsWith('#/orders')) {
    const cur = location.hash;
    history.replaceState(null, '', hash);
    await viewOrders();
    history.replaceState(null, '', cur);
  } else if (hash === '#/' || hash === '') {
    await viewDashboard();
  }
}

// ---------- activity ----------
const actorLabel = (a) => (a === 'admin' ? t('ui.activity.actor.admin') : a === 'shopify' ? t('ui.activity.actor.shopify')
  : /^shopify-session /.test(String(a)) ? t('ui.activity.actor.session', { id: String(a).replace(/^shopify-session /, '') }) : String(a));

async function viewActivity() {
  setActiveNav('activity');
  const q = hashQuery();
  const tab = q.get('tab') === 'access' ? 'access' : 'events';
  const head = html`<div class="page-head"><h1>${t('ui.activity.title')}</h1></div>
    <nav class="tabs"><a href="#/activity" class="${tab === 'events' ? 'active' : ''}">${t('ui.activity.events')}</a><a href="#/activity?tab=access" class="${tab === 'access' ? 'active' : ''}">${icon('shield')} ${t('ui.activity.access')}</a></nav>`;
  if (tab === 'events') {
    const { events } = await api('/events');
    $('#view').innerHTML = html`${head}<div class="card">${eventList(events, true)}</div>`;
    bindDataDownloads($('#view'));
    return;
  }
  const action = q.get('action') || '';
  const order = q.get('order') || '';
  const page = Number(q.get('page') || 1);
  const data = await api(`/access-log?action=${encodeURIComponent(action)}&order=${encodeURIComponent(order)}&page=${page}`);
  const pages = Math.ceil(data.total / data.pageSize);
  const link = (p) => `#/activity?tab=access&action=${encodeURIComponent(action)}&order=${encodeURIComponent(order)}&page=${p}`;
  $('#view').innerHTML = html`${head}
    <div class="toolbar">
      <select id="acc-action" aria-label="${t('ui.activity.action')}"><option value="">${t('ui.activity.allActions')}</option>${Object.entries(state.meta.accessActions).map(([k, l]) => html`<option value="${k}" ${action === k ? 'selected' : ''}>${l}</option>`)}</select>
      <input type="search" id="acc-order" placeholder="${t('ui.activity.orderPlaceholder')}" aria-label="${t('ui.activity.orderPlaceholder')}" value="${order}">
      <span class="muted small">${t('ui.activity.count', { count: data.total, days: data.keepDays })}</span>
    </div>
    <div class="table-wrap">
      ${data.entries.length ? html`<table class="static"><thead><tr><th>${t('ui.activity.when')}</th><th>${t('ui.activity.who')}</th><th>${t('ui.activity.what')}</th><th>${t('ui.activity.order')}</th><th class="hide-sm">${t('ui.activity.details')}</th></tr></thead><tbody>
        ${data.entries.map((e) => html`<tr>
          <td class="nowrap small">${fmtDate(e.at)}</td><td class="small">${actorLabel(e.actor)}</td><td class="small">${state.meta.accessActions[e.action] || e.action}</td>
          <td>${e.order_id ? html`<a href="#/orders/${e.order_id}">${e.order_name}</a>` : e.order_name || html`<span class="faint">—</span>`}
            ${e.action === 'data_request' && e.order_id ? html`<div><button class="btn small" data-export="${e.order_id}">${icon('download')} ${t('ui.activity.download')}</button></div>` : ''}</td>
          <td class="hide-sm faint small">${e.detail || ''}</td></tr>`)}
      </tbody></table>` : html`<div class="empty">${t('ui.activity.empty')}</div>`}
    </div>
    ${pages > 1 ? html`<div class="form-actions">${page > 1 ? html`<a class="btn small" href="${link(page - 1)}">${t('ui.orders.prev')}</a>` : ''}<span class="muted small">${t('ui.orders.page', { page, pages })}</span>${page < pages ? html`<a class="btn small" href="${link(page + 1)}">${t('ui.orders.next')}</a>` : ''}</div>` : ''}
    <p class="muted small">${t('ui.activity.note')}</p>`;
  bindDataDownloads($('#view'));
  const go = () => { location.hash = `#/activity?tab=access&action=${encodeURIComponent($('#acc-action').value)}&order=${encodeURIComponent($('#acc-order').value.trim())}`; };
  $('#acc-action').addEventListener('change', go);
  let timer;
  $('#acc-order').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(go, 400); });
  if (order) { const i = $('#acc-order'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }
}

// ---------- settings ----------
const SECTIONS = ['general', 'couriers', 'invoicing', 'automation', 'rules', 'packaging', 'privacy'];

async function viewSettings(section = 'general') {
  setActiveNav('settings');
  const [{ settings }, integrations] = await Promise.all([api('/settings'), api('/integrations')]);
  $('#view').innerHTML = html`
    <div class="page-head"><h1>${t('ui.settings.title')}</h1></div>
    <div class="settings-layout">
      <nav class="subnav">${SECTIONS.map((k) => html`<a href="#/settings/${k}" class="${section === k ? 'active' : ''}">${t(`ui.settings.sections.${k}`)}</a>`)}</nav>
      <div id="section"></div>
    </div>`;
  const el = $('#section');
  const save = async (patch, msg = t('ui.settings.saved')) => {
    try {
      const r = await api('/settings', { method: 'PUT', body: { settings: patch } });
      if (msg) toast(msg, 'ok');
      refreshChrome();
      return r.settings;
    } catch (err) {
      toast(`${err.message}${err.info?.hint ? ` ${err.info.hint}` : ''}`, 'bad');
      return null;
    }
  };
  ({ general: sectionGeneral, couriers: sectionProviders, invoicing: sectionProviders, automation: sectionAutomation, rules: sectionRules, packaging: sectionPackaging, privacy: sectionPrivacy }[section] || sectionGeneral)(el, settings, integrations, save, section);
}

function sectionGeneral(el, s, integrations, save) {
  const demo = state.me.store.demo;
  const embedded = !!state.me.embedded;
  el.innerHTML = html`
    <div class="card">
      <h2>${t('ui.settings.general.mode')}</h2>
      <div class="mode-switch">
        <label class="provider ${s.mode !== 'live' ? 'active' : ''}"><span class="name"><input type="radio" name="mode" value="test" ${s.mode !== 'live' ? 'checked' : ''}> ${t('ui.settings.general.test')}</span>
          <span class="muted small">${t('ui.settings.general.testHelp')}</span></label>
        <label class="provider ${s.mode === 'live' ? 'active' : ''}"><span class="name"><input type="radio" name="mode" value="live" ${s.mode === 'live' ? 'checked' : ''} ${demo ? 'disabled' : ''}> ${t('ui.settings.general.live')}</span>
          <span class="muted small">${t('ui.settings.general.liveHelp')}</span></label>
      </div>
      ${demo ? html`<p class="muted small">${t('ui.settings.general.demoNote')}</p>` : ''}
    </div>
    <div class="card">
      <h2>${t('ui.settings.general.language')}</h2>
      ${embedded ? html`<p class="muted small" style="margin:0">${t('ui.settings.general.languageEmbedded')}</p>` : html`
      <label class="field" style="max-width:260px">${t('ui.settings.general.languageLabel')}
        <select name="language" id="language">${['en', 'ro'].map((l) => html`<option value="${l}" lang="${l}" ${(s.language || 'en') === l ? 'selected' : ''}>${t(`ui.settings.languages.${l}`)}</option>`)}</select>
        <span class="help">${t('ui.settings.general.languageHelp')}</span></label>`}
    </div>
    <div class="card">
      <h2>${t('ui.settings.general.afterAwb')}</h2>
      <form id="f">
        <label class="check"><input type="checkbox" name="fulfillInShopify" ${s.fulfillment.fulfillInShopify ? 'checked' : ''}> <span>${t('ui.settings.general.fulfill')}</span></label>
        <label class="check" style="margin-top:8px"><input type="checkbox" name="notifyCustomer" ${s.fulfillment.notifyCustomer ? 'checked' : ''}> <span>${t('ui.settings.general.notify')}</span></label>
        <label class="check" style="margin-top:8px"><input type="checkbox" name="markCodPaidOnDelivery" ${s.fulfillment.markCodPaidOnDelivery ? 'checked' : ''}> <span>${t('ui.settings.general.markPaid')}</span></label>
        <label class="check" style="margin-top:8px"><input type="checkbox" name="registerCodPayment" ${s.fulfillment.registerCodPayment ? 'checked' : ''}> <span>${t('ui.settings.general.registerCod')}</span></label>
        <label class="field" style="margin-top:14px;max-width:420px">${t('ui.settings.general.tags')} <input type="text" name="tags" value="${s.fulfillment.tags.join(', ')}"><span class="help">${t('ui.settings.general.tagsHelp')}</span></label>
        <div class="form-actions"><button class="btn primary">${t('ui.common.save')}</button></div>
      </form>
    </div>`;
  $$('input[name=mode]', el).forEach((r) => r.addEventListener('change', async () => {
    if (r.value === 'live' && !confirm(t('ui.settings.general.confirmLive'))) { r.checked = false; $('input[value=test]', el).checked = true; return; }
    await save({ mode: r.value }, r.value === 'live' ? t('ui.settings.general.nowLive') : t('ui.settings.general.nowTest'));
    viewSettings('general');
  }));
  // Standalone dashboard: the store's language. The answer comes back in the new language, so reload the texts.
  $('#language', el)?.addEventListener('change', async (e) => {
    const next = await save({ language: e.target.value }, '');
    if (!next) return;
    await loadLocale(next.language);
    toast(t('ui.settings.general.languageSaved'), 'ok');
    state.meta = await api('/meta');
    await refreshChrome();
    viewSettings('general');
  });
  $('#f', el).addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    save({ fulfillment: { ...s.fulfillment, fulfillInShopify: f.has('fulfillInShopify'), notifyCustomer: f.has('notifyCustomer'), markCodPaidOnDelivery: f.has('markCodPaidOnDelivery'), registerCodPayment: f.has('registerCodPayment'), tags: String(f.get('tags')).split(',').map((t) => t.trim()).filter(Boolean) } });
  });
}

function fieldInput(f, value, isSecret, isSet) {
  const name = `${isSecret ? 'cred' : 'set'}.${f.key}`;
  const v = value ?? f.default ?? '';
  if (f.type === 'checkbox') return html`<label class="check"><input type="checkbox" name="${name}" ${v === true || v === 'true' ? 'checked' : ''}> <span>${f.label}${f.help ? html`<br><span class="muted small">${f.help}</span>` : ''}</span></label>`;
  const control = f.type === 'select'
    ? html`<select name="${name}">${(f.options || []).map((o) => html`<option value="${o.value}" ${String(v) === String(o.value) ? 'selected' : ''}>${o.label}</option>`)}</select>`
    : html`<input type="${f.type === 'password' ? 'password' : f.type === 'number' ? 'number' : 'text'}" name="${name}" value="${isSecret ? '' : v}" placeholder="${isSecret && isSet ? t('ui.settings.providers.secretSaved') : ''}" autocomplete="off">`;
  return html`<label class="field">${f.label}${f.required ? ' *' : ''} ${control}${f.help ? html`<span class="help">${f.help}</span>` : ''}</label>`;
}

function sectionProviders(el, s, integrations, save, section) {
  const kind = section === 'couriers' ? 'courier' : 'invoicing';
  const list = kind === 'courier' ? state.meta.couriers : state.meta.invoicers;
  const saved = integrations[kind];
  const current = kind === 'courier' ? s.courier.default : s.invoicing.provider;
  let open = hashQuery().get('p') || current || list[0]?.id;

  const draw = () => {
    const adapter = list.find((a) => a.id === open);
    const integ = saved.find((i) => i.provider === open);
    el.innerHTML = html`
      <div class="card">
        <h2>${kind === 'courier' ? t('ui.settings.providers.couriers') : t('ui.settings.providers.invoicing')}</h2>
        <p class="muted small" style="margin-top:-6px">${kind === 'courier' ? t('ui.settings.providers.couriersHelp') : t('ui.settings.providers.invoicingHelp')}</p>
        <div class="provider-list">${list.map((a) => {
          const i = saved.find((x) => x.provider === a.id);
          return html`<button type="button" class="provider ${open === a.id ? 'active' : ''}" data-p="${a.id}">
            <span class="name">${a.name} ${current === a.id ? html`<span class="badge info plain">${t('ui.settings.providers.default')}</span>` : ''}</span>
            <span class="small">${a.pending ? html`<span class="faint">${t('ui.settings.providers.pending')}</span>` : i?.verified_at ? html`<span class="badge ok">${t('ui.settings.providers.connected')}</span>` : i ? html`<span class="badge warn">${t('ui.settings.providers.untested')}</span>` : html`<span class="faint">${t('ui.settings.providers.notSet')}</span>`}</span>
          </button>`;
        })}</div>
      </div>
      ${adapter ? html`<div class="card">
        <h2>${adapter.name}</h2>
        ${adapter.pending ? html`<p class="muted">${t('ui.settings.providers.pendingText')}</p>` : html`
        <form id="pf">
          ${adapter.credentialFields.length ? html`<h3>${t('ui.settings.providers.credentials')}</h3><div class="grid2">${adapter.credentialFields.map((f) => fieldInput(f, '', true, integ?.credentialsSet?.[f.key]))}</div>` : ''}
          ${adapter.settingsFields.length ? html`<h3 style="margin-top:16px">${t('ui.settings.providers.options')}</h3><div class="grid2">${adapter.settingsFields.map((f) => fieldInput(f, integ?.settings?.[f.key], false))}</div>` : ''}
          ${adapter.capabilities.listPickupPoints ? html`<p class="small" style="margin:12px 0 0"><button type="button" class="link" id="load-pp">${t('ui.settings.providers.showPoints', { provider: adapter.name })}</button></p><div id="pp" class="small"></div>` : ''}
          ${adapter.capabilities.listSeries ? html`<p class="small" style="margin:12px 0 0"><button type="button" class="link" id="load-series">${t('ui.settings.providers.showSeries', { provider: adapter.name })}</button></p><div id="series" class="small"></div>` : ''}
          <div class="form-actions">
            <button class="btn primary">${t('ui.common.save')}</button>
            <button type="button" class="btn" id="test" ${integ ? '' : 'disabled'}>${t('ui.settings.providers.test')}</button>
            ${current !== adapter.id ? html`<button type="button" class="btn" id="make-default" ${integ ? '' : 'disabled'}>${t('ui.settings.providers.makeDefault')}</button>` : ''}
            <span class="result" id="res"></span>
          </div>
        </form>`}
      </div>` : ''}
      ${kind === 'invoicing' ? html`<div class="card"><h2>${t('ui.settings.invoicing.title')}</h2><form id="invf">
        <div class="grid2">
          <label class="field">${t('ui.settings.invoicing.when')} <select name="when"><option value="on_awb" ${s.invoicing.when === 'on_awb' ? 'selected' : ''}>${t('ui.settings.invoicing.onAwb')}</option><option value="manual" ${s.invoicing.when === 'manual' ? 'selected' : ''}>${t('ui.settings.invoicing.manual')}</option></select></label>
          <label class="field">${t('ui.settings.invoicing.vat')} <input type="number" name="defaultVatRate" value="${s.invoicing.defaultVatRate}"><span class="help">${t('ui.settings.invoicing.vatHelp')}</span></label>
        </div>
        <label class="check" style="margin-top:10px"><input type="checkbox" name="includeShipping" ${s.invoicing.includeShipping ? 'checked' : ''}> <span>${t('ui.settings.invoicing.shipping')}</span></label>
        <label class="check" style="margin-top:6px"><input type="checkbox" name="none" ${!s.invoicing.provider ? 'checked' : ''}> <span>${t('ui.settings.invoicing.none')}</span></label>
        <div class="form-actions"><button class="btn primary">${t('ui.common.save')}</button></div></form></div>` : ''}`;

    $$('[data-p]', el).forEach((b) => b.addEventListener('click', () => { open = b.dataset.p; draw(); }));
    const form = $('#pf', el);
    const collect = () => {
      const f = new FormData(form);
      const credentials = {};
      const settings = {};
      for (const fd of adapter.credentialFields) credentials[fd.key] = fd.type === 'checkbox' ? f.has(`cred.${fd.key}`) : f.get(`cred.${fd.key}`) ?? '';
      for (const fd of adapter.settingsFields) {
        const v = f.get(`set.${fd.key}`) ?? '';
        settings[fd.key] = fd.type === 'checkbox' ? f.has(`set.${fd.key}`) : fd.type === 'number' && v !== '' ? Number(v) : v;
      }
      return { credentials, settings };
    };
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api(`/integrations/${kind}/${open}`, { method: 'PUT', body: collect() });
        toast(t('ui.settings.providers.savedTest', { provider: adapter.name }), 'ok');
        Object.assign(integrations, await api('/integrations'));
        saved.splice(0, saved.length, ...integrations[kind]);
        draw();
      } catch (err) { toast(err.message, 'bad'); }
    });
    $('#test', el)?.addEventListener('click', async (e) => {
      const res = $('#res', el);
      busy(e.currentTarget, true);
      try {
        const r = await api(`/integrations/${kind}/${open}/test`, { method: 'POST' });
        res.className = 'result ok';
        res.textContent = r.message || t('ui.settings.providers.testOk');
        Object.assign(integrations, await api('/integrations'));
        saved.splice(0, saved.length, ...integrations[kind]);
      } catch (err) {
        res.className = 'result bad';
        res.textContent = `${err.message}${err.info?.hint ? ` ${err.info.hint}` : ''}`;
      }
      busy(e.currentTarget, false);
    });
    $('#make-default', el)?.addEventListener('click', async () => {
      const next = kind === 'courier' ? { courier: { ...s.courier, default: open } } : { invoicing: { ...s.invoicing, provider: open } };
      Object.assign(s, await save(next, t('ui.settings.providers.nowDefault', { provider: adapter.name })));
      viewSettings(section);
    });
    const loadOptions = (what, target) => async () => {
      const box = $(target, el);
      box.textContent = t('ui.settings.providers.loading');
      try {
        const { items } = await api(`/integrations/${kind}/${open}/options/${what}`);
        box.innerHTML = items.length ? html`<ul>${items.map((i) => html`<li><span class="mono">${i.id}</span> — ${i.name}${i.address ? html` <span class="muted">(${i.address})</span>` : ''}</li>`)}</ul>` : esc(t('ui.settings.providers.nothing'));
      } catch (err) { box.textContent = err.message; }
    };
    $('#load-pp', el)?.addEventListener('click', loadOptions('pickupPoints', '#pp'));
    $('#load-series', el)?.addEventListener('click', loadOptions('series', '#series'));
    $('#invf', el)?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const f = new FormData(e.target);
      Object.assign(s, await save({ invoicing: { ...s.invoicing, when: f.get('when'), defaultVatRate: f.get('defaultVatRate') === '' ? s.invoicing.defaultVatRate : Number(f.get('defaultVatRate')), includeShipping: f.has('includeShipping'), provider: f.has('none') ? '' : s.invoicing.provider || open } }));
      viewSettings(section);
    });
  };
  draw();
}

function sectionAutomation(el, s, integrations, save) {
  const a = s.automation;
  el.innerHTML = html`<div class="card">
    <h2>${t('ui.settings.automation.title')}</h2>
    <form id="f">
      <label class="check"><input type="checkbox" name="autoProcess" ${a.autoProcess ? 'checked' : ''}> <span><strong>${t('ui.settings.automation.auto')}</strong><br><span class="muted small">${t('ui.settings.automation.autoHelp')}</span></span></label>
      <div class="grid2" style="margin-top:14px">
        <label class="field">${t('ui.settings.automation.delay')} <input type="number" name="delayMinutes" min="0" value="${a.delayMinutes}"><span class="help">${t('ui.settings.automation.delayHelp')}</span></label>
        <label class="field">${t('ui.settings.automation.skipTags')} <input type="text" name="skipTags" value="${a.skipTags.join(', ')}"><span class="help">${t('ui.settings.automation.skipTagsHelp')}</span></label>
      </div>
      <div class="form-actions"><button class="btn primary">${t('ui.common.save')}</button></div>
    </form></div>
    <div class="card"><h2>${t('ui.settings.automation.always')}</h2>
      <ul class="muted" style="margin:0;padding-left:18px">
        <li>${t('ui.settings.automation.a1')}</li>
        <li>${t('ui.settings.automation.a2')}</li>
        <li>${t('ui.settings.automation.a3')}</li>
        <li>${t('ui.settings.automation.a4')}</li>
      </ul></div>`;
  $('#f', el).addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    save({ automation: { ...a, autoProcess: f.has('autoProcess'), delayMinutes: Number(f.get('delayMinutes') || 0), skipTags: String(f.get('skipTags')).split(',').map((t) => t.trim()).filter(Boolean) } });
  });
}

function sectionPackaging(el, s, integrations, save) {
  const p = s.packaging;
  el.innerHTML = html`<div class="card"><h2>${t('ui.settings.packaging.title')}</h2><form id="f"><div class="grid2">
    <label class="field">${t('ui.settings.packaging.defaultWeight')} <input type="number" step="0.1" name="defaultWeightKg" value="${p.defaultWeightKg}"><span class="help">${t('ui.settings.packaging.defaultWeightHelp')}</span></label>
    <label class="field">${t('ui.settings.packaging.minWeight')} <input type="number" step="0.1" name="minWeightKg" value="${p.minWeightKg}"></label>
    <label class="field">${t('ui.settings.packaging.parcels')} <input type="number" name="parcels" min="1" value="${p.parcels}"></label>
    <label class="field">${t('ui.settings.packaging.contents')} <input type="text" name="contents" value="${p.contents}"></label>
    <label class="field">${t('ui.settings.packaging.labelFormat')} <select name="labelFormat"><option value="A6" ${s.courier.labelFormat === 'A6' ? 'selected' : ''}>${t('ui.settings.packaging.a6')}</option><option value="A4" ${s.courier.labelFormat === 'A4' ? 'selected' : ''}>${t('ui.settings.packaging.a4')}</option></select></label>
  </div>
  <label class="check" style="margin-top:10px"><input type="checkbox" name="openPackage" ${p.openPackage ? 'checked' : ''}> <span>${t('ui.settings.packaging.openPackage')}</span></label>
  <div class="form-actions"><button class="btn primary">${t('ui.common.save')}</button></div></form></div>`;
  $('#f', el).addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    save({ packaging: { defaultWeightKg: Number(f.get('defaultWeightKg')), minWeightKg: Number(f.get('minWeightKg')), parcels: Number(f.get('parcels')), contents: f.get('contents'), openPackage: f.has('openPackage') }, courier: { ...s.courier, labelFormat: f.get('labelFormat') } });
  });
}

function sectionPrivacy(el, s, integrations, save) {
  const days = s.privacy.retentionDays;
  const label = (d) => ([90, 180, 365, 730].includes(d) ? t(`ui.settings.privacy.days.${d}`) : t('ui.settings.privacy.daysOther', { days: d }));
  el.innerHTML = html`<div class="card">
    <h2>${t('ui.settings.privacy.title')}</h2>
    <form id="f">
      <label class="field" style="max-width:340px">${t('ui.settings.privacy.after')}
        <select name="retentionDays">${[90, 180, 365, 730].map((d) => html`<option value="${d}" ${days === d ? 'selected' : ''}>${label(d)}</option>`)}</select>
        <span class="help">${t('ui.settings.privacy.help')}</span></label>
      <ul class="muted small" style="margin:12px 0 0;padding-left:18px">
        <li>${t('ui.settings.privacy.l1')}</li>
        <li>${t('ui.settings.privacy.l2')}</li>
        <li>${t('ui.settings.privacy.l3')}</li>
      </ul>
      <div class="form-actions"><button class="btn primary">${t('ui.common.save')}</button></div>
    </form></div>
    <div class="card"><h2>${t('ui.settings.privacy.protect')}</h2>
      <ul class="muted" style="margin:0;padding-left:18px">
        <li>${t('ui.settings.privacy.p1')}</li>
        <li>${t('ui.settings.privacy.p2')} <a href="#/activity?tab=access">${t('ui.settings.privacy.p2Link')}</a>.</li>
        <li>${t('ui.settings.privacy.p3')}</li>
      </ul>
      <p class="small" style="margin:12px 0 0"><a href="${t('ui.legal.privacyUrl')}" target="_blank" rel="noopener">${t('ui.settings.privacy.privacyPolicy')}</a> · <a href="${t('ui.legal.termsUrl')}" target="_blank" rel="noopener">${t('ui.settings.privacy.terms')}</a></p>
    </div>`;
  $('#f', el).addEventListener('submit', (e) => {
    e.preventDefault();
    save({ privacy: { retentionDays: Number(new FormData(e.target).get('retentionDays')) } });
  });
}

function sectionRules(el, s, integrations, save) {
  const rules = structuredClone(s.rules || []);
  const { fields, ops, actions } = state.meta.rules;
  const actionInput = (r, ri, key) => {
    const v = r.actions?.[key] ?? '';
    if (key === 'courier') return html`<select data-a="${ri}:courier"><option value="">—</option>${state.meta.couriers.map((c) => html`<option value="${c.id}" ${v === c.id ? 'selected' : ''}>${c.name}</option>`)}</select>`;
    if (['openPackage', 'skipInvoice', 'hold'].includes(key)) return html`<select data-a="${ri}:${key}"><option value="">—</option><option value="true" ${v === true ? 'selected' : ''}>${t('ui.common.yes')}</option><option value="false" ${v === false ? 'selected' : ''}>${t('ui.common.no')}</option></select>`;
    return html`<input type="${['parcels', 'weightKg'].includes(key) ? 'number' : 'text'}" data-a="${ri}:${key}" value="${v}">`;
  };
  const draw = () => {
    el.innerHTML = html`<div class="card">
      <h2>${t('ui.settings.rules.title')}</h2>
      <p class="muted small" style="margin-top:-6px">${t('ui.settings.rules.help')}</p>
      ${rules.map((r, ri) => html`<div class="rule">
        <div class="rule-head"><input type="checkbox" data-en="${ri}" ${r.enabled !== false ? 'checked' : ''} title="${t('ui.settings.rules.active')}" aria-label="${t('ui.settings.rules.active')}"><input type="text" data-name="${ri}" value="${r.name}" placeholder="${t('ui.settings.rules.namePlaceholder')}" aria-label="${t('ui.settings.rules.namePlaceholder')}">
          <button class="btn small" data-up="${ri}" ${ri === 0 ? 'disabled' : ''} title="${t('ui.settings.rules.moveUp')}" aria-label="${t('ui.settings.rules.moveUp')}">↑</button><button class="btn small danger" data-del="${ri}" title="${t('ui.common.remove')}" aria-label="${t('ui.common.remove')}">${icon('x')}</button></div>
        <div class="rule-label">${t('ui.settings.rules.if')}</div>
        ${(r.conditions || []).map((c, ci) => html`<div class="rule-row">
          <select data-c="${ri}:${ci}:field">${Object.entries(fields).map(([k, f]) => html`<option value="${k}" ${c.field === k ? 'selected' : ''}>${f.label}</option>`)}</select>
          <select data-c="${ri}:${ci}:op">${Object.entries(ops).map(([k, l]) => html`<option value="${k}" ${c.op === k ? 'selected' : ''}>${l}</option>`)}</select>
          ${fields[c.field]?.type === 'select' ? html`<select data-c="${ri}:${ci}:value">${fields[c.field].options.map(([v, l]) => html`<option value="${v}" ${c.value === v ? 'selected' : ''}>${l}</option>`)}</select>`
            : html`<input type="text" data-c="${ri}:${ci}:value" value="${c.value}">`}
          <button class="btn small" data-cdel="${ri}:${ci}" title="${t('ui.common.remove')}" aria-label="${t('ui.common.remove')}">${icon('x')}</button></div>`)}
        <button class="link small" data-cadd="${ri}">${t('ui.settings.rules.addCondition')}</button>
        <div class="rule-label">${t('ui.settings.rules.then')}</div>
        <div class="grid3">${Object.entries(actions).map(([k, l]) => html`<label class="field small">${l} ${actionInput(r, ri, k)}</label>`)}</div>
      </div>`)}
      <div class="form-actions"><button class="btn" id="add">${icon('plus')} ${t('ui.settings.rules.newRule')}</button><button class="btn primary" id="save">${t('ui.settings.rules.save')}</button></div>
    </div>`;
    const sync = () => {
      $$('[data-name]', el).forEach((i) => { rules[i.dataset.name].name = i.value; });
      $$('[data-en]', el).forEach((i) => { rules[i.dataset.en].enabled = i.checked; });
      $$('[data-c]', el).forEach((i) => { const [ri, ci, k] = i.dataset.c.split(':'); rules[ri].conditions[ci][k] = i.value; });
      $$('[data-a]', el).forEach((i) => {
        const [ri, k] = i.dataset.a.split(':');
        rules[ri].actions ||= {};
        let v = i.value;
        if (v === '') delete rules[ri].actions[k];
        else rules[ri].actions[k] = v === 'true' ? true : v === 'false' ? false : ['parcels', 'weightKg'].includes(k) ? Number(v) : v;
      });
    };
    el.onchange = (e) => { if (e.target.matches('[data-c$=":field"]')) { sync(); draw(); } };
    $('#add', el).onclick = () => { sync(); rules.push({ id: `r${Date.now()}`, name: t('ui.settings.rules.newRule'), enabled: true, conditions: [{ field: 'shippingMethod', op: 'contains', value: '' }], actions: {} }); draw(); };
    $('#save', el).onclick = async () => { sync(); Object.assign(s, await save({ rules }, t('ui.settings.rules.saved'))); };
    $$('[data-del]', el).forEach((b) => (b.onclick = () => { sync(); rules.splice(Number(b.dataset.del), 1); draw(); }));
    $$('[data-up]', el).forEach((b) => (b.onclick = () => { sync(); const i = Number(b.dataset.up); [rules[i - 1], rules[i]] = [rules[i], rules[i - 1]]; draw(); }));
    $$('[data-cadd]', el).forEach((b) => (b.onclick = () => { sync(); rules[b.dataset.cadd].conditions.push({ field: 'total', op: 'gt', value: '' }); draw(); }));
    $$('[data-cdel]', el).forEach((b) => (b.onclick = () => { sync(); const [ri, ci] = b.dataset.cdel.split(':'); rules[ri].conditions.splice(ci, 1); draw(); }));
  };
  draw();
}

// ---------- router ----------
async function route() {
  const h = location.hash || '#/';
  const path = h.slice(1).split('?')[0];
  try {
    if (path === '/' || path === '') { $('#drawer').hidden = true; return await viewDashboard(); }
    const m = path.match(/^\/orders\/(\d+)$/);
    if (m) {
      if (!$('#view').innerHTML.trim()) { history.replaceState(null, '', '#/orders'); await viewOrders(); history.replaceState(null, '', h); }
      return renderOrder(Number(m[1]));
    }
    $('#drawer').hidden = true;
    $('#drawer .drawer-panel').innerHTML = '';
    if (path === '/orders') return await viewOrders();
    if (path === '/activity') return await viewActivity();
    if (path.startsWith('/settings')) return await viewSettings(path.split('/')[2] || 'general');
    location.hash = '#/';
  } catch (err) {
    if (err.message !== 'login') $('#view').innerHTML = html`<div class="error-box"><strong>${err.message}</strong>${err.info?.hint ? html`<div class="hint">${err.info.hint}</div>` : ''}</div>`;
  }
}

async function boot() {
  $$('[data-icon]').forEach((i) => { i.innerHTML = icon(i.dataset.icon); });
  // First guess, before the server says: the Shopify admin language, else the last one used here, else English.
  let first = adminLocale();
  if (!first) { try { first = localStorage.getItem('expedo.locale') || ''; } catch { first = ''; } }
  await loadLocale(first || 'en');
  $('#store-switch').addEventListener('change', (e) => { try { localStorage.setItem('expedo.store', e.target.value); } catch {} state.selected.clear(); location.hash = '#/'; refreshChrome().then(route); });
  try {
    [state.meta] = await Promise.all([api('/meta'), refreshChrome()]);
  } catch (err) {
    if (err.message !== 'login') $('#view').innerHTML = html`<div class="error-box"><strong>${err.message}</strong>${err.info?.hint ? html`<div class="hint">${err.info.hint}</div>` : ''}</div>`;
    return;
  }
  window.addEventListener('hashchange', (e) => {
    // Opening/closing the drawer shouldn't re-render the page underneath.
    if (/^#\/orders\/\d+/.test(location.hash)) {
      const old = new URL(e.oldURL).hash || '#/';
      if (!/^#\/orders\/\d+/.test(old)) state.backHash = old;
      return renderOrder(Number(location.hash.split('/')[2]));
    }
    route();
  });
  route();
}

boot();
