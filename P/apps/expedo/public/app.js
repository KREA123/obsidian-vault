// Expedo dashboard — dependency-free SPA. Hash routes:
//   #/  #/orders?status=..  #/orders/:id  #/activity  #/settings/:section

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
const lei = (n) => `${Number(n || 0).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} lei`;
const fmtDate = (s) => s ? new Date(s).toLocaleString('ro-RO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
const fmtDay = (s) => s ? new Date(s).toLocaleDateString('ro-RO', { day: '2-digit', month: 'short' }) : '';
const ago = (s) => {
  const m = Math.round((Date.now() - new Date(s)) / 60000);
  if (m < 1) return 'acum';
  if (m < 60) return `acum ${m} min`;
  if (m < 60 * 24) return `acum ${Math.round(m / 60)} h`;
  return fmtDay(s);
};

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
    const err = new Error(data.error?.message || `Eroare ${res.status}`);
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
      throw new Error(data.error?.message || 'Nu am putut genera PDF-ul.');
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
      throw new Error(data.error?.message || 'Nu am putut descărca fișierul.');
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
      <p class="muted">${window.__LOGIN_ENABLED__ ? 'Intră cu parola de administrator.' : 'Deschide aplicația din adminul Shopify (Aplicații → Expedo).'}</p>
      ${window.__LOGIN_ENABLED__ ? html`
      <form method="post" action="/login" style="display:flex;flex-direction:column;gap:10px">
        <input type="password" name="password" placeholder="Parolă" autofocus required>
        ${location.search.includes('login=fail') ? html`<div class="result bad">Parola nu e corectă.</div>` : ''}
        <button class="btn primary">Intră</button>
      </form>` : ''}
    </div>`;
}

// ---------- shared bits ----------
const STATUS_KIND = { ready: 'info', needs_attention: 'bad', on_hold: 'warn', shipped: 'info', in_transit: 'info', delivered: 'ok', returned: 'warn', cancelled: '', new: '' };
const statusBadge = (o) => html`<span class="badge ${STATUS_KIND[o.status] || ''}">${o.statusLabel || state.meta.statuses[o.status] || o.status}</span>`;
const payPill = (o) => o.paymentMethod === 'cod' ? html`<span class="pill cod">Ramburs</span>` : o.paymentMethod === 'card' ? html`<span class="pill card">Card</span>` : html`<span class="pill">${o.paymentMethod || '—'}</span>`;
const courierName = (id) => state.meta.couriers.find((c) => c.id === id)?.name || id || '—';
const invoicerName = (id) => state.meta.invoicers.find((c) => c.id === id)?.name || id || '—';

function setActiveNav(route) {
  $$('#nav a').forEach((a) => a.classList.toggle('active', a.dataset.route === route));
}

async function refreshChrome() {
  state.me = await api('/me');
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
    <div class="page-head"><h1>Panou</h1><div class="spacer"></div>
      <button class="btn" id="btn-track">${icon('refresh')} Verifică coletele</button>
      <a class="btn primary" href="#/orders?status=ready">${icon('truck')} Procesează comenzile (${stats.toProcess})</a>
    </div>
    <div class="stats">
      <a class="stat" href="#/orders?status=ready"><div class="label">De procesat</div><div class="value">${stats.toProcess}</div><div class="sub">gata pentru AWB</div></a>
      <a class="stat ${stats.attention ? 'alert' : ''}" href="#/orders?status=needs_attention"><div class="label">Necesită atenție</div><div class="value">${stats.attention}</div><div class="sub">au o problemă de rezolvat</div></a>
      <a class="stat" href="#/orders?status=in_transit"><div class="label">Pe drum</div><div class="value">${stats.inTransit}</div><div class="sub">${stats.awbToday} AWB-uri azi</div></a>
      <div class="stat"><div class="label">Ramburs de încasat</div><div class="value">${lei(stats.codPending.v)}</div><div class="sub">${stats.codPending.c} colete la curieri</div></div>
      <div class="stat"><div class="label">Ramburs încasat (30 zile)</div><div class="value">${lei(stats.codCollected30.v)}</div><div class="sub">${stats.codCollected30.c} colete livrate</div></div>
    </div>
    <div class="cols">
      <div>
        <div class="card">
          <h2>De rezolvat</h2>
          ${attention.orders.length ? html`<table><tbody>${attention.orders.slice(0, 8).map((o) => html`
            <tr data-open="${o.id}"><td><span class="order-name">${o.name}</span><div class="faint small">${o.customer}</div></td>
            <td>${issueLines(o, 1)}</td></tr>`)}</tbody></table>`
            : html`<div class="empty">Nicio comandă blocată. ${icon('check')}</div>`}
        </div>
        <div class="card">
          <h2>Curieri (toate AWB-urile)</h2>
          ${stats.byCourier.length ? html`<table><thead><tr><th>Curier</th><th class="num">AWB-uri</th><th class="num">Livrate</th><th class="num">Returnate</th></tr></thead><tbody>
            ${stats.byCourier.map((c) => html`<tr><td>${courierName(c.courier)}</td><td class="num">${c.c}</td><td class="num">${c.delivered}</td><td class="num">${c.returned}${c.c ? html` <span class="faint small">(${Math.round((c.returned / c.c) * 100)}%)</span>` : ''}</td></tr>`)}
          </tbody></table>` : html`<div class="empty">Încă niciun AWB.</div>`}
          <div class="form-actions"><button class="btn small" id="btn-cod">${icon('download')} Export ramburs (CSV)</button><span class="muted small">Cost transport ultimele 30 zile: ${lei(stats.shippingCost30)}</span></div>
        </div>
      </div>
      <div class="card">
        <h2>Activitate recentă</h2>
        ${eventList(ev.events.slice(0, 14), true)}
        <div class="form-actions"><a href="#/activity">Toată activitatea →</a></div>
      </div>
    </div>`;
  $$('[data-open]').forEach((tr) => tr.addEventListener('click', () => openOrder(Number(tr.dataset.open))));
  $('#btn-track').onclick = trackNow;
  $('#btn-cod').onclick = () => download('/cod.csv', 'ramburs.csv');
  bindDataDownloads($('#view'));
}

async function trackNow() {
  const r = await api('/track', { method: 'POST' });
  toast(`Am verificat ${r.checked} colete; ${r.changed} au status nou.`, 'ok');
  route();
}

function eventList(events, withOrder) {
  if (!events.length) return html`<div class="empty">Nimic încă.</div>`;
  return html`<ul class="timeline">${events.map((e) => html`
    <li class="${e.level}">
      <div>${withOrder && e.order_name ? html`<a href="#/orders/${e.order_id}">${e.order_name}</a> · ` : ''}${e.message}</div>
      ${e.data?.hint ? html`<div class="hint">${e.data.hint}</div>` : ''}
      ${e.step === 'gdpr' && e.data?.orderIds?.length ? html`<button class="btn small" data-export="${e.data.orderIds.join(',')}">${icon('download')} Descarcă datele clientului</button>` : ''}
      <div class="when">${fmtDate(e.at)}</div>
    </li>`)}</ul>`;
}

/** "Descarcă datele" buttons (GDPR data request): a JSON file with everything Expedo holds. */
function bindDataDownloads(root) {
  $$('[data-export]', root).forEach((b) => b.addEventListener('click', (e) => {
    e.stopPropagation();
    download(`/customer-export?ids=${b.dataset.export}`, 'date-client.json');
  }));
}

/** Small badge: the customer refused parcels before (core/customers.js). */
const refusedBadge = (n) => (n ? html`<span class="badge warn plain" title="Clientul a refuzat ${n === 1 ? 'un colet' : `${n} colete`} înainte">${n === 1 ? 'a refuzat 1 colet' : `a refuzat ${n} colete`}</span>` : '');

function issueLines(o, max = 3) {
  const list = [];
  if (o.lastError) list.push({ level: 'error', message: o.lastError.message, hint: o.lastError.hint });
  for (const i of o.issues || []) if (!list.some((x) => x.message === i.message)) list.push(i);
  return list.slice(0, max).map((i) => html`<div class="issue-line ${i.level}" title="${i.hint || ''}">● <span>${i.message}${i.hint ? html` <span class="faint">— ${i.hint}</span>` : ''}</span></div>`);
}

// ---------- orders ----------
const TABS = [
  ['open', 'De lucru'], ['ready', 'Gata de procesat'], ['needs_attention', 'Necesită atenție'], ['on_hold', 'În așteptare'],
  ['shipped', 'Expediate'], ['in_transit', 'În livrare'], ['delivered', 'Livrate'], ['returned', 'Returnate'], ['all', 'Toate'],
];

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
    <div class="page-head"><h1>Comenzi</h1><div class="spacer"></div>
      <button class="btn" id="btn-sync">${icon('refresh')} Sincronizează cu Shopify</button>
    </div>
    <nav class="tabs">${TABS.map(([k, label]) => html`<a href="#/orders?status=${k}" class="${status === k ? 'active' : ''}">${label}<span class="count ${k === 'needs_attention' && c.needs_attention ? 'bad' : ''}">${count(k)}</span></a>`)}</nav>
    <div class="toolbar">
      <input type="search" id="search" placeholder="Caută: comandă, AWB, factură, nume, telefon, e-mail…" title="Numele și telefonul se caută întregi (ex. „Popescu”, „0745123456”)" value="${search}">
      <span class="muted small">${data.total} comenzi</span>
      ${ids ? html`<a class="btn small" href="#/orders?status=${status}">Doar comenzile procesate acum ${icon('x')}</a>` : ''}
    </div>
    <div class="table-wrap">
      ${data.orders.length ? html`<table>
        <thead><tr>
          <th class="check"><input type="checkbox" id="check-all" aria-label="Selectează tot"></th>
          <th>Comandă</th><th>Client</th><th class="num">Total</th><th class="hide-sm">Livrare</th><th class="hide-sm">Factură</th><th>Status</th>
        </tr></thead>
        <tbody>${data.orders.map((o) => html`
          <tr data-id="${o.id}" class="${state.selected.has(o.id) ? 'selected' : ''}">
            <td class="check"><input type="checkbox" data-check="${o.id}" ${state.selected.has(o.id) ? 'checked' : ''} aria-label="Selectează ${o.name}"></td>
            <td><div class="order-name">${o.name} ${o.testMode && o.awb ? html`<span class="pill test">probă</span>` : ''}</div><div class="faint small nowrap">${fmtDate(o.createdAt)}</div></td>
            <td><div>${o.redactedAt ? html`<span class="faint">Date șterse</span>` : o.company || o.customer} ${refusedBadge(o.refusedBefore)}</div><div class="muted small">${[o.city, o.county].filter(Boolean).join(', ')}${o.city || o.county ? ' · ' : ''}${o.items} buc.</div>${issueLines(o, 2)}</td>
            <td class="num"><div class="nowrap">${lei(o.total)}</div><div>${payPill(o)}</div></td>
            <td class="hide-sm">${o.awb ? html`<div>${courierName(o.courier)}</div><div class="mono">${o.awb}</div>${o.trackingText ? html`<div class="faint small">${o.trackingText}</div>` : ''}`
              : html`<span class="faint small">${o.courier ? `→ ${courierName(o.courier)}` : '—'}</span><div class="faint small">${o.shippingMethod || ''}</div>`}</td>
            <td class="hide-sm">${o.invoice ? html`<span class="nowrap">${o.invoice}</span>` : html`<span class="faint">—</span>`}</td>
            <td>${statusBadge(o)}</td>
          </tr>`)}</tbody></table>`
        : html`<div class="empty">Nicio comandă aici.</div>`}
    </div>
    ${pages > 1 ? html`<div class="form-actions">
      ${page > 1 ? html`<a class="btn small" href="#/orders?status=${status}&q=${encodeURIComponent(search)}${ids ? `&ids=${ids}` : ''}&page=${page - 1}">← Înapoi</a>` : ''}
      <span class="muted small">Pagina ${page} din ${pages}</span>
      ${page < pages ? html`<a class="btn small" href="#/orders?status=${status}&q=${encodeURIComponent(search)}${ids ? `&ids=${ids}` : ''}&page=${page + 1}">Înainte →</a>` : ''}</div>` : ''}
    <div class="bulkbar" id="bulkbar" hidden>
      <span class="count" id="bulk-count"></span>
      <button class="btn primary" data-bulk="all">${icon('truck')} Generează AWB + factură</button>
      <button class="btn" data-bulk="awb">Doar AWB</button>
      <button class="btn" data-bulk="invoice">Doar factură</button>
      <button class="btn" data-bulk="labels">${icon('print')} Etichete</button>
      <button class="btn" data-bulk="picking">${icon('clip')} Listă de picking</button>
      <button class="btn" data-bulk="clear">${icon('x')}</button>
    </div>`;

  const updateBulk = () => {
    $('#bulkbar').hidden = !state.selected.size;
    $('#bulk-count').textContent = `${state.selected.size} selectate`;
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
  let t;
  $('#search').addEventListener('input', (e) => {
    clearTimeout(t);
    t = setTimeout(() => { location.hash = `#/orders?status=${status}&q=${encodeURIComponent(e.target.value)}`; }, 350);
  });
  $('#btn-sync').onclick = async (e) => {
    busy(e.currentTarget, true);
    try { const r = await api('/sync', { method: 'POST', body: { days: 14 } }); toast(`Sincronizat: ${r.imported} comenzi din ultimele 14 zile.`, 'ok'); route(); }
    catch (err) { toast(err.message, 'bad'); busy(e.currentTarget, false); }
  };
  $$('[data-bulk]').forEach((b) => b.addEventListener('click', () => bulk(b.dataset.bulk, b)));
  if (search) { const s = $('#search'); s.focus(); s.setSelectionRange(s.value.length, s.value.length); }
}

function busy(btn, on) {
  if (!btn) return;
  if (on) { btn.dataset.label = btn.innerHTML; btn.innerHTML = '<span class="spinner"></span> Se lucrează…'; btn.disabled = true; }
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
      toast(`${r.ok} reușite, ${r.failed} cu probleme. Ex. ${first.name}: ${first.error?.message}`, 'bad');
    } else {
      toast(`Gata: ${r.ok} comenzi procesate.`, 'ok');
    }
    const done = r.results.filter((x) => x.ok && x.awb).map((x) => x.id);
    // Show exactly the orders just processed, still selected, so "Etichete" is one click away
    // (they are not necessarily on the first page of "Expediate").
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
  if (!w) return toast('Permite ferestrele pop-up ca să printezi lista.', 'bad');
  w.document.write(`<!doctype html><meta charset="utf-8"><title>Listă de picking</title>
    <style>body{font:14px system-ui;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px 8px;text-align:left}th{background:#f3f3f3}.q{font-size:18px;font-weight:700;text-align:center}</style>
    <h2>Listă de picking — ${esc(new Date().toLocaleString('ro-RO'))}</h2><p>Comenzi: ${esc(p.orders.join(', '))}</p>
    <table><tr><th>✓</th><th>SKU</th><th>Produs</th><th>Cant.</th><th>Comenzi</th></tr>
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
      <h1>${o.name}</h1> ${statusBadge(o)} ${(o.testMode && o.awb) || (o.invoiceTest && o.invoice) ? html`<span class="pill test">probă</span>` : ''}
      <div class="spacer"></div>
      <button class="btn small" data-close>${icon('x')}</button>
    </div>
    ${errors.map((e) => html`<div class="${e.level === 'warning' ? 'warn-box' : 'error-box'}">
      <strong>${e.message}</strong>${e.hint ? html`<div class="hint">${e.hint}</div>` : ''}
      ${e.details ? html`<details class="small"><summary class="muted">Detalii tehnice</summary><pre class="mono" style="white-space:pre-wrap">${typeof e.details === 'string' ? e.details : JSON.stringify(e.details, null, 2)}</pre></details>` : ''}
    </div>`)}
    <div class="actions" style="margin-bottom:16px">
      ${canProcess ? html`<button class="btn primary" data-act="process">${icon('truck')} Generează AWB + factură</button>` : ''}
      ${!canProcess && !o.invoice && o.awb ? html`<button class="btn" data-act="invoice">${icon('file')} Emite factura</button>` : ''}
      ${o.awb ? html`<button class="btn" data-act="label">${icon('print')} Eticheta AWB</button>` : ''}
      ${o.invoice ? html`<button class="btn" data-act="invoice-pdf">${icon('file')} Factura PDF</button>` : ''}
      ${o.awb && !o.fulfilledAt && !o.testMode && !o.cancelled && !state.me.testMode ? html`<button class="btn" data-act="fulfill">Marchează expediată în Shopify</button>` : ''}
      ${hasTestData && !state.me.testMode ? html`<button class="btn" data-act="reset-test" title="AWB-ul / factura de probă se șterg; comanda se poate procesa real.">Șterge datele de probă</button>` : ''}
      ${o.awb ? html`<button class="btn danger" data-act="cancel-awb">Anulează AWB</button>` : ''}
      ${o.invoice ? html`<button class="btn danger" data-act="storno">Stornează factura</button>` : ''}
      ${!o.awb ? html`<button class="btn" data-act="hold">${o.overrides.hold ? 'Scoate din așteptare' : 'Pune în așteptare'}</button>` : ''}
      <button class="btn" data-act="refresh">${icon('refresh')} Reîncarcă din Shopify</button>
    </div>

    <div class="card">
      <h2>Livrare</h2>
      <dl class="kv">
        ${o.awb ? html`<dt>AWB</dt><dd><span class="mono">${o.awb}</span> · ${courierName(o.courier)} ${safeUrl(o.trackingUrl) ? html`· <a href="${safeUrl(o.trackingUrl)}" target="_blank" rel="noopener">urmărește</a>` : ''}<div class="muted small">${o.trackingText || ''}</div></dd>` : ''}
        <dt>Plată</dt><dd>${payPill(o)} ${o.paymentMethod === 'cod' ? html`ramburs <strong>${lei(o.awb ? o.codAmount : plan.cod)}</strong>${o.codCollectedAt ? html` · <span class="badge ok">încasat ${fmtDay(o.codCollectedAt)}</span>` : ''}` : d.financialStatus === 'PAID' ? 'plătită online' : d.financialStatus}</dd>
        <dt>Metodă</dt><dd>${d.shippingMethod || '—'}${plan.lockerId ? html` · locker <span class="mono">${plan.lockerId}</span>` : ''}</dd>
        ${plan.matchedRules.length ? html`<dt>Reguli aplicate</dt><dd>${plan.matchedRules.join(', ')}</dd>` : ''}
        ${o.invoice ? html`<dt>Factură</dt><dd>${o.invoice} ${safeUrl(o.invoiceUrl) ? html`· <a href="${safeUrl(o.invoiceUrl)}" target="_blank" rel="noopener">deschide</a>` : ''}</dd>` : ''}
      </dl>
      ${canProcess ? html`
      <form id="plan-form" style="margin-top:14px">
        <div class="grid3">
          <label class="field">Curier
            <select name="courier">${[['', `Implicit / reguli (${courierName(plan.courier)})`], ...state.meta.couriers.map((c) => [c.id, c.name])].map(([v, l]) => html`<option value="${v}" ${(o.overrides.courier || '') === v ? 'selected' : ''}>${l}</option>`)}</select>
          </label>
          <label class="field">Colete <input type="number" name="parcels" min="1" value="${o.overrides.parcels ?? ''}" placeholder="${plan.parcels}"></label>
          <label class="field">Greutate (kg) <input type="number" name="weightKg" min="0.1" step="0.1" value="${o.overrides.weightKg ?? ''}" placeholder="${plan.weightKg}"></label>
          <label class="field">Ramburs (lei) <input type="number" name="cod" min="0" step="0.01" value="${o.overrides.cod ?? ''}" placeholder="${plan.cod}"></label>
          <label class="field">Observații pe AWB <input type="text" name="notes" value="${o.overrides.notes ?? ''}" placeholder="ex. sunați înainte"></label>
          <label class="field">Locker / punct <input type="text" name="lockerId" value="${o.overrides.lockerId ?? ''}" placeholder="${plan.lockerId || 'ID easybox / FANbox'}"></label>
        </div>
        <label class="check" style="margin-top:10px"><input type="checkbox" name="openPackage" ${plan.openPackage ? 'checked' : ''}> Deschidere colet la livrare</label>
        <label class="check" style="margin-top:6px"><input type="checkbox" name="skipInvoice" ${plan.skipInvoice ? 'checked' : ''}> Fără factură pentru comanda asta</label>
        <div class="form-actions"><button class="btn small">Salvează</button></div>
      </form>` : ''}
    </div>

    ${o.redactedAt ? html`<div class="card"><h2>Datele clientului au fost șterse</h2><p class="muted small" style="margin:0">Pe ${fmtDay(o.redactedAt)}, după zilele de păstrare din Setări → Date clienți (sau la cererea clientului). Au rămas numărul comenzii, sumele, produsele, AWB-ul și factura.</p></div>` : html`
    <div class="card">
      <h2>Adresa de livrare ${o.overrides.address ? html`<span class="badge warn plain">modificată manual</span>` : ''}</h2>
      ${canProcess ? html`
      <form id="addr-form">
        <div class="grid2">
          <label class="field">Nume <input type="text" name="name" value="${a.name || [a.firstName, a.lastName].filter(Boolean).join(' ')}"></label>
          <label class="field">Telefon <input type="text" name="phone" value="${a.phone}"></label>
          <label class="field">Firmă <input type="text" name="company" value="${a.company}"></label>
          <label class="field">Județ
            <select name="province"><option value="">— alege —</option>${state.meta.counties.map((c) => html`<option value="${c.name}" ${plan.address.countyCode === c.code ? 'selected' : ''}>${c.name}</option>`)}</select>
          </label>
          <label class="field">Localitate <input type="text" name="city" value="${a.city}"><span class="help">Normalizat: ${plan.address.city || '—'}${plan.address.sector ? `, Sector ${plan.address.sector}` : ''}</span></label>
          <label class="field">Cod poștal <input type="text" name="zip" value="${a.zip}"></label>
        </div>
        <label class="field" style="margin-top:12px">Stradă, număr, bloc, ap. <input type="text" name="address1" value="${a.address1}"></label>
        <label class="field" style="margin-top:12px">Detalii adresă <input type="text" name="address2" value="${a.address2}"></label>
        <div class="form-actions"><button class="btn small">Salvează adresa</button>${o.overrides.address ? html`<button type="button" class="link small" id="addr-reset">Revino la adresa din Shopify</button>` : ''}
          <span class="muted small">Modificarea rămâne aici; nu schimbă comanda în Shopify.</span></div>
      </form>` : html`<dl class="kv"><dt>Destinatar</dt><dd>${plan.address.name}${plan.address.company ? ` (${plan.address.company})` : ''}</dd><dt>Telefon</dt><dd>${plan.address.phone}</dd><dt>Adresă</dt><dd>${plan.address.street}, ${plan.address.city}${plan.address.sector ? `, Sector ${plan.address.sector}` : ''}, ${plan.address.county} ${plan.address.zip}</dd></dl>`}
    </div>
    ${customer?.orders.length ? html`<div class="card">
      <h2>Istoricul clientului ${customer.returned ? html`<span class="badge warn plain">a refuzat ${customer.returned === 1 ? '1 colet' : `${customer.returned} colete`}</span>` : ''}</h2>
      <p class="muted small" style="margin-top:-6px">Alte comenzi cu același telefon sau e-mail: <strong>${customer.delivered}</strong> livrate, <strong>${customer.returned}</strong> refuzate sau returnate.</p>
      <table class="lines"><tbody>${customer.orders.map((h) => html`<tr data-open="${h.id}" class="clickable">
        <td><a href="#/orders/${h.id}">${h.name}</a></td><td class="muted small nowrap">${fmtDay(h.createdAt)}</td>
        <td>${h.refused ? html`<span class="badge warn">Refuzat${h.cod ? ' (ramburs)' : ''}</span>` : statusBadge({ status: h.status })}</td></tr>`)}</tbody></table>
    </div>` : ''}`}

    <div class="card">
      <h2>Produse</h2>
      <table class="lines"><thead><tr><th>Produs</th><th>SKU</th><th class="num">Cant.</th><th class="num">Preț</th></tr></thead><tbody>
        ${d.lines.map((l) => html`<tr><td>${l.title}${l.variantTitle ? html` <span class="muted">· ${l.variantTitle}</span>` : ''}</td><td class="mono">${l.sku}</td><td class="num">${l.quantity}</td><td class="num nowrap">${lei(l.unitPrice)}</td></tr>`)}
        ${d.shippingLines.map((s) => html`<tr><td class="muted">Transport · ${s.title}</td><td></td><td class="num">1</td><td class="num nowrap">${lei(s.price)}</td></tr>`)}
        <tr><td colspan="3"><strong>Total</strong></td><td class="num nowrap"><strong>${lei(d.total)}</strong></td></tr>
      </tbody></table>
      ${d.company ? html`<p class="small" style="margin:10px 0 0">Factură pe firmă: <strong>${d.company.name}</strong> · CUI ${d.company.vatCode}${d.company.regCom ? ` · ${d.company.regCom}` : ''}</p>` : ''}
      ${d.note ? html`<p class="small muted" style="margin:10px 0 0">Notă client: ${d.note}</p>` : ''}
    </div>

    <div class="card"><h2>Istoric</h2>${eventList([...events].reverse(), false)}</div>`;

  $$('[data-close]', panel).forEach((b) => b.addEventListener('click', closeDrawer));
  $$('tr[data-open]', panel).forEach((tr) => tr.addEventListener('click', (e) => { e.preventDefault(); openOrder(Number(tr.dataset.open)); }));
  const after = async (msg) => { if (msg) toast(msg, 'ok'); await renderOrder(id); refreshList(); refreshChrome(); };
  const run = async (btn, fn) => { busy(btn, true); try { await fn(); } catch (err) { toast(err.message, 'bad'); await renderOrder(id); } };

  $$('[data-act]', panel).forEach((btn) => btn.addEventListener('click', () => {
    const act = btn.dataset.act;
    if (act === 'label') return openPdf(`/labels.pdf?ids=${id}`);
    if (act === 'invoice-pdf') return openPdf(`/orders/${id}/invoice.pdf`);
    if (act === 'cancel-awb' && !confirm(`Anulezi AWB-ul ${o.awb}? Dacă e marcată expediată în Shopify, se anulează și acolo.`)) return;
    if (act === 'storno' && !confirm(`Stornezi factura ${o.invoice}? Se emite o factură de stornare.`)) return;
    if (act === 'reset-test' && !confirm('Ștergi AWB-ul și factura de probă ale comenzii? Apoi o poți procesa real.')) return;
    run(btn, async () => {
      if (act === 'process' || act === 'invoice' || act === 'fulfill') {
        const steps = { process: ['awb', 'invoice', 'fulfill'], invoice: ['invoice'], fulfill: ['fulfill'] }[act];
        // From the order page the merchant decides explicitly: held orders are processed too.
        const r = (await api('/orders/process', { method: 'POST', body: { ids: [id], steps, force: true } })).results[0];
        if (!r.ok) { toast(r.error?.message || 'Nu a mers.', 'bad'); return after(); }
        return after(r.awb ? `AWB ${r.awb}${r.invoice ? ` · factura ${r.invoice}` : ''}` : 'Gata.');
      }
      if (act === 'cancel-awb') { await api(`/orders/${id}/cancel-awb`, { method: 'POST' }); return after('AWB anulat.'); }
      if (act === 'storno') { await api(`/orders/${id}/storno-invoice`, { method: 'POST' }); return after('Factura a fost stornată.'); }
      if (act === 'reset-test') { await api(`/orders/${id}/reset-test`, { method: 'POST' }); return after('Datele de probă au fost șterse.'); }
      if (act === 'hold') { await api(`/orders/${id}`, { method: 'PATCH', body: { hold: o.overrides.hold ? null : true } }); return after(); }
      if (act === 'refresh') { await api(`/orders/${id}/refresh`, { method: 'POST' }); return after('Reîncărcat.'); }
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
    after('Salvat.');
  });
  $('#addr-form', panel)?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    const [firstName, ...rest] = f.name.trim().split(/\s+/);
    try { await api(`/orders/${id}`, { method: 'PATCH', body: { address: { ...f, firstName, lastName: rest.join(' '), provinceCode: '' } } }); } catch (err) { return toast(err.message, 'bad'); }
    after('Adresa a fost salvată și verificată din nou.');
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
const actorLabel = (a) => (a === 'admin' ? 'Administrator' : a === 'shopify' ? 'Shopify (cerere GDPR)' : String(a).replace(/^shopify-session /, 'Utilizator Shopify #'));

async function viewActivity() {
  setActiveNav('activity');
  const q = hashQuery();
  const tab = q.get('tab') === 'access' ? 'access' : 'events';
  const head = html`<div class="page-head"><h1>Activitate</h1></div>
    <nav class="tabs"><a href="#/activity" class="${tab === 'events' ? 'active' : ''}">Ce s-a întâmplat</a><a href="#/activity?tab=access" class="${tab === 'access' ? 'active' : ''}">${icon('shield')} Acces la date</a></nav>`;
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
      <select id="acc-action" aria-label="Acțiune"><option value="">Toate acțiunile</option>${Object.entries(state.meta.accessActions).map(([k, l]) => html`<option value="${k}" ${action === k ? 'selected' : ''}>${l}</option>`)}</select>
      <input type="search" id="acc-order" placeholder="Comanda (ex. #1101)" value="${order}">
      <span class="muted small">${data.total} înregistrări · se păstrează ${data.keepDays} de zile</span>
    </div>
    <div class="table-wrap">
      ${data.entries.length ? html`<table class="static"><thead><tr><th>Când</th><th>Cine</th><th>Ce</th><th>Comanda</th><th class="hide-sm">Detalii</th></tr></thead><tbody>
        ${data.entries.map((e) => html`<tr>
          <td class="nowrap small">${fmtDate(e.at)}</td><td class="small">${actorLabel(e.actor)}</td><td class="small">${state.meta.accessActions[e.action] || e.action}</td>
          <td>${e.order_id ? html`<a href="#/orders/${e.order_id}">${e.order_name}</a>` : e.order_name || html`<span class="faint">—</span>`}
            ${e.action === 'data_request' && e.order_id ? html`<div><button class="btn small" data-export="${e.order_id}">${icon('download')} Descarcă datele</button></div>` : ''}</td>
          <td class="hide-sm faint small">${e.detail || ''}</td></tr>`)}
      </tbody></table>` : html`<div class="empty">Nicio înregistrare.</div>`}
    </div>
    ${pages > 1 ? html`<div class="form-actions">${page > 1 ? html`<a class="btn small" href="${link(page - 1)}">← Înapoi</a>` : ''}<span class="muted small">Pagina ${page} din ${pages}</span>${page < pages ? html`<a class="btn small" href="${link(page + 1)}">Înainte →</a>` : ''}</div>` : ''}
    <p class="muted small">Aici apare cine a deschis o comandă sau a descărcat etichete, facturi, lista de picking, exportul de ramburs sau datele unui client. Cererile clienților venite prin Shopify apar tot aici.</p>`;
  bindDataDownloads($('#view'));
  const go = () => { location.hash = `#/activity?tab=access&action=${encodeURIComponent($('#acc-action').value)}&order=${encodeURIComponent($('#acc-order').value.trim())}`; };
  $('#acc-action').addEventListener('change', go);
  let t;
  $('#acc-order').addEventListener('input', () => { clearTimeout(t); t = setTimeout(go, 400); });
  if (order) { const i = $('#acc-order'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }
}

// ---------- settings ----------
const SECTIONS = [['general', 'General'], ['couriers', 'Curieri'], ['invoicing', 'Facturare'], ['automation', 'Automatizări'], ['rules', 'Reguli'], ['packaging', 'Colete'], ['privacy', 'Date clienți']];

async function viewSettings(section = 'general') {
  setActiveNav('settings');
  const [{ settings }, integrations] = await Promise.all([api('/settings'), api('/integrations')]);
  $('#view').innerHTML = html`
    <div class="page-head"><h1>Setări</h1></div>
    <div class="settings-layout">
      <nav class="subnav">${SECTIONS.map(([k, l]) => html`<a href="#/settings/${k}" class="${section === k ? 'active' : ''}">${l}</a>`)}</nav>
      <div id="section"></div>
    </div>`;
  const el = $('#section');
  const save = async (patch, msg = 'Setările au fost salvate.') => {
    try {
      const r = await api('/settings', { method: 'PUT', body: { settings: patch } });
      toast(msg, 'ok');
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
  el.innerHTML = html`
    <div class="card">
      <h2>Modul de lucru</h2>
      <div class="mode-switch">
        <label class="provider ${s.mode !== 'live' ? 'active' : ''}"><span class="name"><input type="radio" name="mode" value="test" ${s.mode !== 'live' ? 'checked' : ''}> Probă</span>
          <span class="muted small">AWB-uri și facturi de test. Nu se trimite nimic la curieri sau la facturare, iar Shopify nu se modifică. Bun ca să verifici regulile pe comenzi reale.</span></label>
        <label class="provider ${s.mode === 'live' ? 'active' : ''}"><span class="name"><input type="radio" name="mode" value="live" ${s.mode === 'live' ? 'checked' : ''} ${demo ? 'disabled' : ''}> Live</span>
          <span class="muted small">AWB-uri reale la curier, facturi reale, comenzile se marchează expediate în Shopify și clientul primește AWB-ul pe e-mail.</span></label>
      </div>
      ${demo ? html`<p class="muted small">Magazinul demo rămâne mereu în probă.</p>` : ''}
    </div>
    <div class="card">
      <h2>După generarea AWB-ului</h2>
      <form id="f">
        <label class="check"><input type="checkbox" name="fulfillInShopify" ${s.fulfillment.fulfillInShopify ? 'checked' : ''}> <span>Marchează comanda ca expediată în Shopify, cu AWB-ul și link de urmărire</span></label>
        <label class="check" style="margin-top:8px"><input type="checkbox" name="notifyCustomer" ${s.fulfillment.notifyCustomer ? 'checked' : ''}> <span>Trimite clientului e-mailul Shopify cu AWB-ul</span></label>
        <label class="check" style="margin-top:8px"><input type="checkbox" name="markCodPaidOnDelivery" ${s.fulfillment.markCodPaidOnDelivery ? 'checked' : ''}> <span>Când coletul ramburs e livrat, marchează comanda ca plătită în Shopify</span></label>
        <label class="check" style="margin-top:8px"><input type="checkbox" name="registerCodPayment" ${s.fulfillment.registerCodPayment ? 'checked' : ''}> <span>…și înregistrează încasarea pe factură (dacă programul de facturare permite)</span></label>
        <label class="field" style="margin-top:14px;max-width:420px">Etichete adăugate în Shopify <input type="text" name="tags" value="${s.fulfillment.tags.join(', ')}"><span class="help">Separate prin virgulă. Gol = nicio etichetă.</span></label>
        <div class="form-actions"><button class="btn primary">Salvează</button></div>
      </form>
    </div>`;
  $$('input[name=mode]', el).forEach((r) => r.addEventListener('change', async () => {
    if (r.value === 'live' && !confirm('Treci pe LIVE? De acum se generează AWB-uri și facturi reale.')) { r.checked = false; $('input[value=test]', el).checked = true; return; }
    await save({ mode: r.value }, r.value === 'live' ? 'Ești pe live. Comenzile procesate în probă au butonul „Șterge datele de probă”.' : 'Ești în modul de probă.');
    viewSettings('general');
  }));
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
    : html`<input type="${f.type === 'password' ? 'password' : f.type === 'number' ? 'number' : 'text'}" name="${name}" value="${isSecret ? '' : v}" placeholder="${isSecret && isSet ? '•••••• salvat — lasă gol ca să nu schimbi' : ''}" autocomplete="off">`;
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
        <h2>${kind === 'courier' ? 'Curieri' : 'Program de facturare'}</h2>
        <p class="muted small" style="margin-top:-6px">${kind === 'courier' ? 'Poți conecta mai mulți curieri; regulile aleg curierul pentru fiecare comandă.' : 'Facturile se emit automat la generarea AWB-ului (sau manual).'}</p>
        <div class="provider-list">${list.map((a) => {
          const i = saved.find((x) => x.provider === a.id);
          return html`<button type="button" class="provider ${open === a.id ? 'active' : ''}" data-p="${a.id}">
            <span class="name">${a.name} ${current === a.id ? html`<span class="badge info plain">implicit</span>` : ''}</span>
            <span class="small">${a.pending ? html`<span class="faint">în lucru</span>` : i?.verified_at ? html`<span class="badge ok">conectat</span>` : i ? html`<span class="badge warn">netestat</span>` : html`<span class="faint">neconfigurat</span>`}</span>
          </button>`;
        })}</div>
      </div>
      ${adapter ? html`<div class="card">
        <h2>${adapter.name}</h2>
        ${adapter.pending ? html`<p class="muted">Integrarea e încă în lucru.</p>` : html`
        <form id="pf">
          ${adapter.credentialFields.length ? html`<h3>Date de conectare</h3><div class="grid2">${adapter.credentialFields.map((f) => fieldInput(f, '', true, integ?.credentialsSet?.[f.key]))}</div>` : ''}
          ${adapter.settingsFields.length ? html`<h3 style="margin-top:16px">Opțiuni</h3><div class="grid2">${adapter.settingsFields.map((f) => fieldInput(f, integ?.settings?.[f.key], false))}</div>` : ''}
          ${adapter.capabilities.listPickupPoints ? html`<p class="small" style="margin:12px 0 0"><button type="button" class="link" id="load-pp">Arată punctele de ridicare din contul ${adapter.name}</button></p><div id="pp" class="small"></div>` : ''}
          ${adapter.capabilities.listSeries ? html`<p class="small" style="margin:12px 0 0"><button type="button" class="link" id="load-series">Arată seriile de facturi din ${adapter.name}</button></p><div id="series" class="small"></div>` : ''}
          <div class="form-actions">
            <button class="btn primary">Salvează</button>
            <button type="button" class="btn" id="test" ${integ ? '' : 'disabled'}>Testează conexiunea</button>
            ${current !== adapter.id ? html`<button type="button" class="btn" id="make-default" ${integ ? '' : 'disabled'}>Folosește ca implicit</button>` : ''}
            <span class="result" id="res"></span>
          </div>
        </form>`}
      </div>` : ''}
      ${kind === 'invoicing' ? html`<div class="card"><h2>Cum se facturează</h2><form id="invf">
        <div class="grid2">
          <label class="field">Când se emite factura <select name="when"><option value="on_awb" ${s.invoicing.when === 'on_awb' ? 'selected' : ''}>Odată cu AWB-ul</option><option value="manual" ${s.invoicing.when === 'manual' ? 'selected' : ''}>Doar manual</option></select></label>
          <label class="field">Cota TVA implicită (%) <input type="number" name="defaultVatRate" value="${s.invoicing.defaultVatRate}"><span class="help">Folosită când Shopify nu trimite TVA pe produs.</span></label>
        </div>
        <label class="check" style="margin-top:10px"><input type="checkbox" name="includeShipping" ${s.invoicing.includeShipping ? 'checked' : ''}> <span>Pune transportul pe factură</span></label>
        <label class="check" style="margin-top:6px"><input type="checkbox" name="none" ${!s.invoicing.provider ? 'checked' : ''}> <span>Nu emite facturi din Expedo</span></label>
        <div class="form-actions"><button class="btn primary">Salvează</button></div></form></div>` : ''}`;

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
        toast(`${adapter.name} salvat. Apasă „Testează conexiunea”.`, 'ok');
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
        res.textContent = r.message || 'Conexiune reușită.';
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
      Object.assign(s, await save(next, `${adapter.name} e acum implicit.`));
      viewSettings(section);
    });
    const loadOptions = (what, target) => async () => {
      const box = $(target, el);
      box.textContent = 'Se încarcă…';
      try {
        const { items } = await api(`/integrations/${kind}/${open}/options/${what}`);
        box.innerHTML = items.length ? html`<ul>${items.map((i) => html`<li><span class="mono">${i.id}</span> — ${i.name}${i.address ? html` <span class="muted">(${i.address})</span>` : ''}</li>`)}</ul>` : 'Nimic găsit (salvează și testează întâi).';
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
    <h2>Procesare automată</h2>
    <form id="f">
      <label class="check"><input type="checkbox" name="autoProcess" ${a.autoProcess ? 'checked' : ''}> <span><strong>Generează automat AWB-ul și factura pentru comenzile noi</strong><br><span class="muted small">Doar pentru comenzile fără probleme. Cele cu adresă greșită, telefon lipsă etc. rămân la „Necesită atenție”.</span></span></label>
      <div class="grid2" style="margin-top:14px">
        <label class="field">Așteaptă înainte (minute) <input type="number" name="delayMinutes" min="0" value="${a.delayMinutes}"><span class="help">Ca să apuce clientul să anuleze sau să corecteze comanda.</span></label>
        <label class="field">Nu procesa comenzile cu etichetele <input type="text" name="skipTags" value="${a.skipTags.join(', ')}"><span class="help">Separate prin virgulă.</span></label>
      </div>
      <div class="form-actions"><button class="btn primary">Salvează</button></div>
    </form></div>
    <div class="card"><h2>Ce se întâmplă singur, oricum</h2>
      <ul class="muted" style="margin:0;padding-left:18px">
        <li>Comenzile noi vin din Shopify în câteva secunde; o dată la 15 minute verificăm să nu fi scăpat vreuna.</li>
        <li>Statusul coletelor se verifică la fiecare 30 de minute.</li>
        <li>Erorile temporare (curier căzut, timeout) se reîncearcă singure: după 1, 5, 15, 60 și 180 de minute.</li>
        <li>O comandă nu primește niciodată două AWB-uri sau două facturi, chiar dacă apeși de mai multe ori.</li>
      </ul></div>`;
  $('#f', el).addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    save({ automation: { ...a, autoProcess: f.has('autoProcess'), delayMinutes: Number(f.get('delayMinutes') || 0), skipTags: String(f.get('skipTags')).split(',').map((t) => t.trim()).filter(Boolean) } });
  });
}

function sectionPackaging(el, s, integrations, save) {
  const p = s.packaging;
  el.innerHTML = html`<div class="card"><h2>Colete</h2><form id="f"><div class="grid2">
    <label class="field">Greutate implicită (kg) <input type="number" step="0.1" name="defaultWeightKg" value="${p.defaultWeightKg}"><span class="help">Când produsele nu au greutate în Shopify.</span></label>
    <label class="field">Greutate minimă (kg) <input type="number" step="0.1" name="minWeightKg" value="${p.minWeightKg}"></label>
    <label class="field">Număr colete implicit <input type="number" name="parcels" min="1" value="${p.parcels}"></label>
    <label class="field">Conținut (pe AWB) <input type="text" name="contents" value="${p.contents}"></label>
    <label class="field">Format etichetă <select name="labelFormat"><option value="A6" ${s.courier.labelFormat === 'A6' ? 'selected' : ''}>A6 (imprimantă termică 10×15)</option><option value="A4" ${s.courier.labelFormat === 'A4' ? 'selected' : ''}>A4</option></select></label>
  </div>
  <label class="check" style="margin-top:10px"><input type="checkbox" name="openPackage" ${p.openPackage ? 'checked' : ''}> <span>Deschidere colet la livrare, implicit</span></label>
  <div class="form-actions"><button class="btn primary">Salvează</button></div></form></div>`;
  $('#f', el).addEventListener('submit', (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    save({ packaging: { defaultWeightKg: Number(f.get('defaultWeightKg')), minWeightKg: Number(f.get('minWeightKg')), parcels: Number(f.get('parcels')), contents: f.get('contents'), openPackage: f.has('openPackage') }, courier: { ...s.courier, labelFormat: f.get('labelFormat') } });
  });
}

function sectionPrivacy(el, s, integrations, save) {
  const days = s.privacy.retentionDays;
  const label = (d) => ({ 90: '90 de zile (3 luni)', 180: '180 de zile (6 luni)', 365: '365 de zile (1 an)', 730: '730 de zile (2 ani)' }[d] || `${d} de zile`);
  el.innerHTML = html`<div class="card">
    <h2>Păstrează datele clienților</h2>
    <form id="f">
      <label class="field" style="max-width:340px">După ce comanda e livrată, returnată sau anulată
        <select name="retentionDays">${[90, 180, 365, 730].map((d) => html`<option value="${d}" ${days === d ? 'selected' : ''}>${label(d)}</option>`)}</select>
        <span class="help">Apoi ștergem numele, adresa, telefonul și e-mailul clientului din comandă. Rămân numărul comenzii, sumele, produsele, AWB-ul și factura, pentru contabilitate și verificarea rambursului.</span></label>
      <ul class="muted small" style="margin:12px 0 0;padding-left:18px">
        <li>Comenzile încă în lucru nu se ating.</li>
        <li>Istoricul de refuzuri al clienților ține tot atât.</li>
        <li>Ștergerea rulează o dată pe zi.</li>
      </ul>
      <div class="form-actions"><button class="btn primary">Salvează</button></div>
    </form></div>
    <div class="card"><h2>Cum sunt protejate datele</h2>
      <ul class="muted" style="margin:0;padding-left:18px">
        <li>Numele, adresele, telefoanele și e-mailurile clienților sunt criptate în baza de date.</li>
        <li>Fiecare deschidere de comandă și fiecare export se notează în <a href="#/activity?tab=access">Activitate → Acces la date</a>.</li>
        <li>Când un client cere prin Shopify datele lui sau ștergerea lor, cererea apare în Activitate și se rezolvă de aici.</li>
      </ul>
      <p class="small" style="margin:12px 0 0"><a href="/confidentialitate" target="_blank" rel="noopener">Politica de confidențialitate</a> · <a href="/termeni" target="_blank" rel="noopener">Termeni și acordul de prelucrare a datelor</a></p>
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
    if (['openPackage', 'skipInvoice', 'hold'].includes(key)) return html`<select data-a="${ri}:${key}"><option value="">—</option><option value="true" ${v === true ? 'selected' : ''}>Da</option><option value="false" ${v === false ? 'selected' : ''}>Nu</option></select>`;
    return html`<input type="${['parcels', 'weightKg'].includes(key) ? 'number' : 'text'}" data-a="${ri}:${key}" value="${v}">`;
  };
  const draw = () => {
    el.innerHTML = html`<div class="card">
      <h2>Reguli</h2>
      <p class="muted small" style="margin-top:-6px">Se aplică de sus în jos. Dacă două reguli setează același lucru, câștigă cea de sus. Pentru „conține” poți pune mai multe valori separate prin virgulă.</p>
      ${rules.map((r, ri) => html`<div class="rule">
        <div class="rule-head"><input type="checkbox" data-en="${ri}" ${r.enabled !== false ? 'checked' : ''} title="Activă"><input type="text" data-name="${ri}" value="${r.name}" placeholder="Numele regulii">
          <button class="btn small" data-up="${ri}" ${ri === 0 ? 'disabled' : ''}>↑</button><button class="btn small danger" data-del="${ri}">${icon('x')}</button></div>
        <div class="rule-label">Dacă</div>
        ${(r.conditions || []).map((c, ci) => html`<div class="rule-row">
          <select data-c="${ri}:${ci}:field">${Object.entries(fields).map(([k, f]) => html`<option value="${k}" ${c.field === k ? 'selected' : ''}>${f.label}</option>`)}</select>
          <select data-c="${ri}:${ci}:op">${Object.entries(ops).map(([k, l]) => html`<option value="${k}" ${c.op === k ? 'selected' : ''}>${l}</option>`)}</select>
          ${fields[c.field]?.type === 'select' ? html`<select data-c="${ri}:${ci}:value">${fields[c.field].options.map(([v, l]) => html`<option value="${v}" ${c.value === v ? 'selected' : ''}>${l}</option>`)}</select>`
            : html`<input type="text" data-c="${ri}:${ci}:value" value="${c.value}">`}
          <button class="btn small" data-cdel="${ri}:${ci}">${icon('x')}</button></div>`)}
        <button class="link small" data-cadd="${ri}">+ condiție</button>
        <div class="rule-label">Atunci</div>
        <div class="grid3">${Object.entries(actions).map(([k, l]) => html`<label class="field small">${l} ${actionInput(r, ri, k)}</label>`)}</div>
      </div>`)}
      <div class="form-actions"><button class="btn" id="add">${icon('plus')} Regulă nouă</button><button class="btn primary" id="save">Salvează regulile</button></div>
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
    $('#add', el).onclick = () => { sync(); rules.push({ id: `r${Date.now()}`, name: 'Regulă nouă', enabled: true, conditions: [{ field: 'shippingMethod', op: 'contains', value: '' }], actions: {} }); draw(); };
    $('#save', el).onclick = async () => { sync(); Object.assign(s, await save({ rules }, 'Regulile au fost salvate; comenzile deschise au fost reverificate.')); };
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
