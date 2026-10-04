#!/usr/bin/env python3
"""Capture the real Expedo UI for the trailer (Playwright, deviceScaleFactor 2). Re-runnable, one command:

  python3 capture.py                                              # frozen snapshot (default APP_DIR)
  python3 capture.py --app /tmp/claude-0/expedo-snap2/P/apps/expedo --port 3302 --ui-lang en   # → ui/en/
  python3 capture.py --app /tmp/claude-0/expedo-snap2/P/apps/expedo --port 3302 --ui-lang ro   # → ui/ro/

Starts the app in demo mode on a fresh database (DEMO=1, its own PORT and DB_FILE), drives it through the UI and the
API (what a merchant would click), and writes:

  ui/<lang>/<shot>.png   2x screenshots (a page viewport, or one element such as the order drawer)
  ui/<lang>/label_<n>.png pages of the labels PDF (one PDF for the whole bulk run), rasterised by pdftoppm
  ui/<lang>/manifest.json(.js) {shot: {w, h, rects: {name: [x, y, w, h]}}} in CSS px of the shot (image px / 2), plus the UI
                         language, live values (stats, texts) and indices the trailer needs. The trailer only reads
                         ui/, so re-capturing swaps every UI layer (e.g. Romanian → English UI) without touching it.

Selectors are structural (classes, data-attributes, hrefs), not UI text, so they work in any UI language.
The app source is never edited. What is set up in the demo database, and why:
  * the locality-error order (--loc-order, default #1110) gets the address "Eforie" and the error the real Cargus
    adapter raises for it, produced by the app's own code (src/couriers/locality.js: matchLocality + localityError)
    against real Constanța county locality names, so it is word-for-word what the merchant sees live
    ("… Ai vrut: Eforie Sud, Eforie Nord, Corbu?"). The demo uses the test courier, which has no nomenclator.
  * the test courier's issue time of one AWB is moved back step by step, so tracking walks through every status
    (picked up → depot → out for delivery → delivered → COD collected) in seconds instead of minutes.
  * customer-refusal warning: if the app has it (GET /api/orders/:id returns `customer`), the real warning of the
    demo customer with a refused parcel is captured. Older builds without the feature get the app's own .warn-box
    markup with the exact message text of src/core/build.js (CUSTOMER_REFUSED_BEFORE), rendered into the drawer.

options / env: --app APP_DIR  --port PORT (3301)  --db DB_FILE  --ui-lang en|ro (→ ui/en, ui/ro)  --locale  --loc-order (#1110)  --track-order (#1118)
               --out DIR (dry run elsewhere; the trailer reads ui/)
"""
import argparse, json, os, pathlib, re, signal, socket, subprocess, sys, time, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--app', default=os.environ.get('APP_DIR', '/tmp/claude-0/expedo-snap/P/apps/expedo'))
ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', 3301)))
ap.add_argument('--db', default=os.environ.get('DB_FILE', '/tmp/claude-0/trailer-demo.db'))
ap.add_argument('--ui-lang', default=os.environ.get('UI_LANG', 'en'), choices=['en', 'ro'],
                help='UI language: sets the demo store\'s language setting and the browser locale; output goes to ui/<lang>/')
ap.add_argument('--locale', default=None, help='browser locale (default: en-US for --ui-lang en, ro-RO for ro)')
ap.add_argument('--loc-order', default='#1110', help='order that gets the Cargus locality error ("Eforie")')
ap.add_argument('--track-order', default='#1118', help='ramburs order walked through tracking to delivered')
ap.add_argument('--out', default=None, help='output folder (default: ui/<ui-lang>/ next to this script, which the trailer reads)')
ARGS = ap.parse_args()

HERE = pathlib.Path(__file__).resolve().parent
APP = pathlib.Path(ARGS.app)
PORT = ARGS.port
DB = pathlib.Path(ARGS.db)
BASE = f'http://localhost:{PORT}'
OUT = pathlib.Path(ARGS.out) if ARGS.out else HERE / 'ui' / ARGS.ui_lang
LOCALE = ARGS.locale or {'en': 'en-US', 'ro': 'ro-RO'}[ARGS.ui_lang]
FD = HERE / 'fonts'
MAN = {}

# ── local fonts: the app links Google Fonts (Inter, JetBrains Mono); serve them from fonts/ (offline, deterministic)
CSS = re.sub(r'url\((.*?)\)', r'url(https://fonts.gstatic.com/local/\1)', (FD / 'fonts.css').read_text())
def route(r):
    u = r.request.url
    if 'fonts.googleapis.com' in u: return r.fulfill(body=CSS, content_type='text/css')
    if 'fonts.gstatic.com/local/' in u:
        return r.fulfill(body=(FD / u.rsplit('/', 1)[1]).read_bytes(), content_type='font/woff2', headers={'access-control-allow-origin': '*'})
    if u.startswith(BASE): return r.continue_()
    return r.abort()

def api(method, path, body=None):
    req = urllib.request.Request(BASE + '/api' + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'X-Expedo-Request': '1', 'Content-Type': 'application/json', 'X-Expedo-Locale': ARGS.ui_lang})
    with urllib.request.urlopen(req) as r:
        b = r.read()
        return json.loads(b) if r.headers.get('content-type', '').startswith('application/json') else b

def start_server():
    with socket.socket() as so:
        if so.connect_ex(('127.0.0.1', PORT)) == 0: sys.exit(f'port {PORT} is busy: stop that server or pass --port')
    for f in DB.parent.glob(DB.name + '*'): f.unlink()
    env = {**os.environ, 'DEMO': '1', 'PORT': str(PORT), 'DB_FILE': str(DB)}
    p = subprocess.Popen(['npm', 'start', '--silent'], cwd=APP, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    for _ in range(150):
        try: urllib.request.urlopen(BASE + '/healthz'); break
        except Exception: time.sleep(.2)
    else: sys.exit('the app did not start: ' + (p.stdout.read() if p.poll() is not None else '(still starting)'))
    time.sleep(1.5)            # demo seed + advanceDemo (processes the oldest orders)
    return p

def stop_server(p):
    try: os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError: pass

def order_id(name):
    return next(o['id'] for o in api('GET', '/orders?status=all&q=' + urllib.parse.quote(name))['orders'] if o['name'] == name)

def app_db(script, **params):
    """Runs a snippet against the demo database through the app's own db module (src/db.js), so it works whether the
    app stores rows in plain JSON or encrypted at rest. `db` (the module) and `P` (params) are in scope; print JSON."""
    js = (f"import * as db from {json.dumps(str(APP / 'src/db.js'))};\n"
          f"db.openDb(process.env.DB_FILE);\nconst P = {json.dumps(params)};\n" + script)
    r = subprocess.run(['node', '--disable-warning=ExperimentalWarning', '--input-type=module', '-e', js], cwd=APP,
                       env={**os.environ, 'DB_FILE': str(DB), 'DEMO': '1'}, capture_output=True, text=True)
    if r.returncode: sys.exit('db helper failed: ' + r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None

def setup_locality_error(name):
    """The customer typed "Eforie"; Cargus only has "Eforie Nord" / "Eforie Sud" → the real adapter error, from the app's
    own code. Works with both error styles: text messages (older builds) and catalog keys rendered per language (i18n)."""
    r = app_db("""
      const L = await import(P.app + '/src/couriers/locality.js');
      const E = await import(P.app + '/src/core/errors.js');
      const CT = ['Constanta','Mangalia','Medgidia','Navodari','Ovidiu','Eforie Nord','Eforie Sud','Techirghiol','Cumpana',
        'Valu lui Traian','Lumina','Agigea','Mamaia-Sat','Corbu','Tuzla','23 August','Costinesti','Murfatlar','Basarabi',
        'Poarta Alba','Mihail Kogalniceanu','Cernavoda','Harsova','Negru Voda'].map((name, i) => ({ id: i + 1, name }));
      const q = { city: 'Eforie', county: 'Constanta', zip: '' };
      const e = L.localityError({ provider: 'cargus', providerName: 'Cargus', city: q.city, county: q.county, result: L.matchLocality(q, CT, { fuzzy: true }) });
      const row = db.getDb().prepare('SELECT id, store_id FROM orders WHERE name = ?').get(P.name);
      const o = db.getOrder(row.id), d = o.data;
      for (const k of ['shippingAddress', 'billingAddress'])
        Object.assign(d[k], { city: 'Eforie', province: 'Constanța', provinceCode: 'CT', address1: 'Str. Tudor Vladimirescu nr. 12', zip: '' });
      db.updateOrder(row.id, { data: d, last_error: { ...e.toJSON(), step: 'awb', at: new Date().toISOString() }, status: 'needs_attention' });
      // the same event the pipeline logs when a step fails (core/pipeline.js fail())
      const msg = E.errorMessage ? E.errorMessage(e) : e.message, hint = E.errorHint ? E.errorHint(e) : e.hint;
      db.logEvent(row.store_id, row.id, 'error', 'awb', msg, { hint, code: e.code, details: e.details });
      const txt = e.render ? e.render(P.lang) : { message: e.message, hint: e.hint };
      console.log(JSON.stringify({ id: row.id, message: txt.message, hint: txt.hint }));
    """, name=name, app=str(APP), lang=ARGS.ui_lang)
    print('locality error on', name, ':', r['message'], '|', r['hint'])
    return r['id'], r

def age_awb(awb, minutes):
    """Moves the test courier's issue time of one AWB back, so the next tracking check sees the next status."""
    app_db("""
      for (const s of db.getDb().prepare('SELECT id FROM stores').all()) {
        const c = db.storeCache(s.id), v = c.get('mock:issued');
        if (v && v[P.awb]) { v[P.awb].at = Date.now() - P.min * 60000 - 5000; c.set('mock:issued', v, 60 * 60 * 24 * 30); }
      }
      console.log('true');
    """, awb=awb, min=minutes)

# ── screenshot helpers
RECT_JS = """([sels, root]) => {
  const R = root ? document.querySelector(root).getBoundingClientRect() : { left: 0, top: 0 };
  const out = {};
  for (const [k, s] of Object.entries(sels)) {
    let el;
    if (s.startsWith('range=')) {          // range=<selector>|<substring>: the box of that substring of the element's text
      const [sel, txt] = s.slice(6).split('|');
      const host = document.querySelector(sel); if (!host) continue;
      const tw = document.createTreeWalker(host, NodeFilter.SHOW_TEXT); let n, hit = null;
      while ((n = tw.nextNode())) { const i = n.data.indexOf(txt); if (i >= 0) { hit = [n, i]; break; } }
      if (!hit) continue;
      const rg = document.createRange(); rg.setStart(hit[0], hit[1]); rg.setEnd(hit[0], hit[1] + txt.length);
      const rs = [...rg.getClientRects()];
      const l = Math.min(...rs.map(r => r.left)), t = Math.min(...rs.map(r => r.top)), r2 = Math.max(...rs.map(r => r.right)), b2 = Math.max(...rs.map(r => r.bottom));
      out[k] = [l - R.left, t - R.top, r2 - l, b2 - t].map(v => Math.round(v * 10) / 10);
      continue;
    }
    if (s.startsWith('rangeq=')) {         // rangeq=<selector>: from the start of its text to the first '?' (the "Did you mean …?" part)
      const host = document.querySelector(s.slice(7)); if (!host) continue;
      const tw = document.createTreeWalker(host, NodeFilter.SHOW_TEXT); let n, hit = null;
      while ((n = tw.nextNode())) { const i = n.data.indexOf('?'); if (i >= 0) { hit = [n, i]; break; } }
      if (!hit) continue;
      const rg = document.createRange(); rg.setStart(hit[0], 0); rg.setEnd(hit[0], hit[1] + 1);
      const rs = [...rg.getClientRects()].filter(r => r.width > 0);
      const l = Math.min(...rs.map(r => r.left)), t = Math.min(...rs.map(r => r.top)), r2 = Math.max(...rs.map(r => r.right)), b2 = Math.max(...rs.map(r => r.bottom));
      out[k] = [l - R.left, t - R.top, r2 - l, b2 - t].map(v => Math.round(v * 10) / 10);
      continue;
    }
    if (s.startsWith('lines=')) {          // lines=<selector>: one box per rendered line of an inline element
      const el2 = document.querySelector(s.slice(6)); if (!el2) continue;
      const rg = document.createRange(); rg.selectNodeContents(el2);
      const byLine = new Map();
      for (const r of rg.getClientRects()) { if (r.width < 1) continue; const key = Math.round(r.top / 4);
        const o = byLine.get(key); byLine.set(key, o ? [Math.min(o[0], r.left), Math.min(o[1], r.top), Math.max(o[2], r.right), Math.max(o[3], r.bottom)] : [r.left, r.top, r.right, r.bottom]); }
      out[k] = [...byLine.values()].map(([l, t, r2, b2]) => [l - R.left, t - R.top, r2 - l, b2 - t].map(v => Math.round(v * 10) / 10));
      continue;
    }
    if (s.startsWith('text=')) {           // text=<selector>|<text>: the first element matching selector containing text
      const [sel, txt] = s.slice(5).split('|');
      el = [...document.querySelectorAll(sel)].find(e => e.textContent.includes(txt));
    } else el = document.querySelector(s);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    out[k] = [r.left - R.left, r.top - R.top, r.width, r.height].map(v => Math.round(v * 10) / 10);
  }
  return out;
}"""
def shot(pg, name, sels=None, el=None, full=False, keep=False):
    path = OUT / f'{name}.png'
    pg.wait_for_timeout(350)
    if not keep:   # toasts are captured on their own (toast()), keep them out of page shots
        pg.evaluate("document.querySelectorAll('#toasts .toast').forEach(t => t.remove())")
    if el:
        loc = pg.locator(el).first
        loc.screenshot(path=str(path), animations='disabled')
        bb = loc.bounding_box(); w, h = bb['width'], bb['height']
    else:
        pg.screenshot(path=str(path), full_page=full, animations='disabled')
        w, h = pg.viewport_size['width'], (pg.evaluate('document.documentElement.scrollHeight') if full else pg.viewport_size['height'])
    rects = pg.evaluate(RECT_JS, [sels or {}, el]) if sels else {}
    MAN[name] = {'w': round(w, 1), 'h': round(h, 1), 'rects': rects}
    print(f'{name:22s} {w:.0f}x{h:.0f}  rects: {", ".join(rects)}')

def toast(pg, name):
    t = pg.locator('#toasts .toast').last
    t.wait_for(state='visible', timeout=8000)
    pg.wait_for_timeout(250)
    shot(pg, name, el='#toasts .toast:last-child', keep=True)
    MAN[name]['text'] = t.inner_text()

def goto(pg, hash_, wait='#view > *'):
    pg.goto(f'{BASE}/#{hash_}')
    pg.wait_for_selector(wait)
    pg.wait_for_timeout(500)

def open_order(pg, oid, height=1900):
    pg.set_viewport_size({'width': 1440, 'height': height})
    goto(pg, '/orders')
    pg.evaluate("h => { location.hash = h; }", f'#/orders/{oid}')
    pg.wait_for_selector('.drawer-panel .drawer-head')
    pg.wait_for_timeout(600)

# structural selectors (no UI text) → work for any UI language
DRAWER = {
    'head': '.drawer-head', 'badge': '.drawer-head .badge', 'error': '.drawer-panel .error-box', 'error_title': '.drawer-panel .error-box strong',
    'error_hint': '.drawer-panel .error-box .hint', 'details': '.drawer-panel .error-box details', 'process': '[data-act=process]',
    'actions': '.drawer-panel .actions', 'city': 'input[name=city]', 'phone': 'input[name=phone]', 'county': 'select[name=province]',
    'zip': 'input[name=zip]', 'addr_save': '#addr-form button:not([type=button])',
    'addr_card': '.drawer-panel .card:has(#addr-form), .drawer-panel .card:has(.kv) ~ .card:has(.kv)',
    'livrare': '.drawer-panel .card:has(.kv)', 'kv': '.drawer-panel .kv', 'history': '.drawer-panel .card:has(.timeline)',
    'timeline': '.drawer-panel .timeline', 'cod_badge': '.drawer-panel .kv .badge.ok', 'awb': '.drawer-panel .kv dd .mono',
    'aivrut': 'rangeq=.drawer-panel .error-box .hint', 'nord': 'range=.drawer-panel .error-box .hint|Eforie Nord',
    'factura': 'text=.drawer-panel .kv dd|TEST 0', 'pay': '.drawer-panel .kv dd:has(.pill)',
    **{f'li{i}': f'.drawer-panel .timeline li:nth-child({i + 1})' for i in range(14)},
    **{f'lit{i}': f'lines=.drawer-panel .timeline li:nth-child({i + 1}) > div:first-child' for i in range(14)},
}
STATS = {**{f'stat{i}': f'.stats > :nth-child({i + 1})' for i in range(6)},
         **{f'val{i}': f'.stats > :nth-child({i + 1}) .value' for i in range(6)}, **{f'sub{i}': f'.stats > :nth-child({i + 1}) .sub' for i in range(6)}}

def texts(pg, sels):
    return pg.evaluate("s => Object.fromEntries(Object.entries(s).map(([k, q]) => [k, document.querySelector(q)?.innerText ?? null]))", sels)

def num(t):
    """'1.441,30 lei' / '1,441.30 RON' → 1441.3"""
    m = re.search(r'\d[\d.,\s\u00a0]*', t or '')
    if not m: return None
    x = re.sub(r'[\s\u00a0]', '', m.group(0)).rstrip('.,')
    if re.search(r'[.,]\d{2}$', x): x = re.sub(r'[.,]', '', x[:-3]) + '.' + x[-2:]
    else: x = re.sub(r'[.,]', '', x)
    return float(x)

def refusal_order():
    """An open order whose customer refused a parcel before (apps with the refusal history), else None."""
    for o in api('GET', '/orders?status=all')['orders']:
        if o.get('awb'): continue
        d = api('GET', f"/orders/{o['id']}")
        c = d.get('customer') or {}
        iss = [i for i in (d.get('plan', {}).get('issues') or d.get('order', {}).get('issues') or []) if i.get('code') == 'CUSTOMER_REFUSED_BEFORE']
        if c.get('returned') and iss: return o['id'], o['name'], iss[0]
    return None

REFUSED_FALLBACK = {   # src/core/build.js (CUSTOMER_REFUSED_BEFORE), for builds whose UI predates the feature
    'ro': ('Clientul a refuzat 2 colete înainte (din 3).', 'Sună-l înainte de AWB sau cere plata cu cardul.'),
    'en': ('The customer refused 2 parcels before (out of 3).', 'Call them before the AWB, or ask for card payment.'),
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob('*.png'): f.unlink()
    srv = start_server()
    try:
        # the demo store's UI language (apps with i18n; older builds ignore the unknown setting or answer 400)
        try: api('PUT', '/settings', {'settings': {'language': ARGS.ui_lang}})
        except Exception as e: print('language setting not supported:', e)
        refused = refusal_order()                       # find it before we change anything
        loc_id, loc_err = setup_locality_error(ARGS.loc_order)
        with sync_playwright() as p:
            b = p.chromium.launch(args=['--force-color-profile=srgb', '--font-render-hinting=none'])
            ctx = b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=2, color_scheme='light', locale=LOCALE,
                                timezone_id='Europe/Bucharest')
            pg = ctx.new_page(); pg.route('**/*', route)
            pg.on('dialog', lambda d: d.accept())

            # 1. dashboard before anything
            goto(pg, '/')
            # UI language: what the navigation actually says (falls back to <html lang>)
            MAN['uiLang'] = pg.evaluate("""() => { const t = document.querySelector('#nav')?.innerText || '';
              if (/\\b(Orders|Settings|Activity|Dashboard)\\b/.test(t)) return 'en';
              if (/Comenzi|Setări|Activitate|Panou/.test(t)) return 'ro';
              return (document.documentElement.lang || 'ro').slice(0, 2); }""")
            print('UI language:', MAN['uiLang'])
            shot(pg, 'dash_before', {**STATS, 'banner': '#test-banner', 'brand': '.brand', 'cta': '.page-head .btn.primary',
                                     'todo': '.cols > div > .card:first-child', 'activity': '.cols > .card'})
            MAN['dash_before']['texts'] = texts(pg, {k: v for k, v in STATS.items() if k[:3] in ('val', 'sub')})

            # 2. orders that need attention: errors in plain words, in red, with what to do
            goto(pg, '/orders?status=needs_attention')
            rows = {f'row{i}': f'tbody tr:nth-child({i + 1})' for i in range(5)}
            issues = {**{f'issue{i}': f'tbody tr:nth-child({i + 1}) .issue-line' for i in range(5)},
                      **{f'msg{i}': f'lines=tbody tr:nth-child({i + 1}) .issue-line > span' for i in range(5)}}
            shot(pg, 'orders_attention', {**rows, **issues, 'table': '.table-wrap', 'tabs': '.tabs', 'tab_bad': '.tabs a[href*="needs_attention"]'})
            MAN['orders_attention']['count'] = pg.locator('tbody tr').count()

            # 3. the address is checked against the courier's locality list: "Did you mean …?" → typed fix → AWB + invoice
            open_order(pg, loc_id)
            shot(pg, 'dloc_err', DRAWER, el='.drawer-panel')
            pg.locator('input[name=city]').click(); pg.wait_for_timeout(100)
            pg.locator('input[name=city]').press('End'); pg.locator('input[name=city]').type(' Nord', delay=40)
            shot(pg, 'dloc_typed', DRAWER, el='.drawer-panel')
            pg.locator(DRAWER['addr_save']).first.click()
            toast(pg, 'toast_loc_saved'); pg.wait_for_timeout(500)
            pg.locator('[data-act=process]').click()
            toast(pg, 'toast_loc_done'); pg.wait_for_timeout(600)
            shot(pg, 'dloc_done', DRAWER, el='.drawer-panel')
            MAN['loc'] = {'order': ARGS.loc_order, 'message': loc_err['message'], 'hint': loc_err['hint']}

            # 3b. an order with a missing phone: fixed through the order panel (so it ships in the bulk run below)
            try:
                pid = order_id('#1113')
                open_order(pg, pid)
                if pg.locator('input[name=phone]').count() and not pg.locator('input[name=phone]').input_value():
                    pg.locator('input[name=phone]').click(); pg.locator('input[name=phone]').type('0733 111 222', delay=20)
                    pg.locator(DRAWER['addr_save']).first.click(); pg.wait_for_timeout(800)
            except StopIteration: pass

            # 4. customer refusal warning
            if refused:
                rid, rname, iss = refused
                open_order(pg, rid)
                box = pg.locator('.drawer-panel .warn-box', has_text=iss['message'][:24]).first
                box.evaluate("e => e.id = 'refused'")
                shot(pg, 'warn_refused', el='#refused')
                MAN['warn_refused'].update(real=True, order=rname, text=iss['message'] + ' ' + (iss.get('hint') or ''))
            else:
                msg, hint = REFUSED_FALLBACK.get(MAN['uiLang'], REFUSED_FALLBACK['en'])
                open_order(pg, order_id('#1117'))
                pg.evaluate("""([m, h]) => { const box = document.createElement('div'); box.className = 'warn-box'; box.id = 'refused';
                  box.innerHTML = '<strong></strong><div class="hint"></div>'; box.querySelector('strong').textContent = m;
                  box.querySelector('.hint').textContent = h; document.querySelector('.drawer-head').after(box); }""", [msg, hint])
                shot(pg, 'warn_refused', el='#refused')
                MAN['warn_refused'].update(real=False, text=msg + ' ' + hint)

            # 5. bulk: select every order that is ready → one click → AWB + invoice → one labels PDF
            pg.set_viewport_size({'width': 1440, 'height': 900})
            pg.goto(f'{BASE}/#/'); pg.wait_for_selector('.stats')
            goto(pg, '/orders?status=ready')
            rsel = {**{f'row{i}': f'tbody tr:nth-child({i + 1})' for i in range(8)}, **{f'cb{i}': f'tbody tr:nth-child({i + 1}) input' for i in range(8)},
                    'checkall': '#check-all', 'table': '.table-wrap', 'tabs': '.tabs', 'tab_ready': '.tabs a[href*="status=ready"]'}
            shot(pg, 'ready', rsel)
            pg.locator('#check-all').check(); pg.wait_for_timeout(300)
            bsel = {**rsel, 'bulkbar': '#bulkbar', 'bulk_count': '#bulk-count', 'bulk_all': '[data-bulk=all]', 'bulk_labels': '[data-bulk=labels]'}
            shot(pg, 'ready_selected', bsel)
            ready_ids = sorted(pg.evaluate("[...document.querySelectorAll('[data-check]')].map(c => Number(c.dataset.check))"))
            pg.locator('[data-bulk=all]').click()
            toast(pg, 'toast_bulk')
            pg.wait_for_selector('tbody tr .mono'); pg.wait_for_timeout(800)
            # AWB / invoice / status columns found by header position (no text)
            cols = pg.evaluate("""() => { const th = [...document.querySelectorAll('thead th')];
              const i = c => th.findIndex(t => t.matches(c)) + 1; return { awb: th.length - 2, inv: th.length - 1, st: th.length }; }""")
            shot(pg, 'bulk_done', {**bsel, **{f'awb{i}': f'tbody tr:nth-child({i + 1}) td:nth-child({cols["awb"]})' for i in range(8)},
                                   **{f'inv{i}': f'tbody tr:nth-child({i + 1}) td:nth-child({cols["inv"]})' for i in range(8)},
                                   **{f'st{i}': f'tbody tr:nth-child({i + 1}) td:nth-child({cols["st"]})' for i in range(8)}})
            done = api('GET', '/orders?status=all&ids=' + ','.join(map(str, ready_ids)))['orders']
            MAN['bulk_orders'] = [{k: o.get(k) for k in ('id', 'name', 'customer', 'city', 'awb', 'invoice', 'courier', 'total', 'paymentMethod')} for o in done]
            pdf = api('GET', '/labels.pdf?ids=' + ','.join(str(o['id']) for o in done))
            (OUT / 'labels.pdf').write_bytes(pdf)
            subprocess.run(['pdftoppm', '-r', '220', '-png', str(OUT / 'labels.pdf'), str(OUT / 'label')], check=True)
            (OUT / 'labels.pdf').unlink()
            labels = sorted(OUT.glob('label-*.png'))
            for i, f in enumerate(labels, 1): f.rename(OUT / f'label_{i}.png')
            MAN['labels'] = {'count': len(labels)}
            print('labels:', len(labels))

            # 6. rules (the easybox → Sameday rule and the big-COD → on hold rule, found in the settings) + test mode
            rules = api('GET', '/settings')['settings']['rules']
            ia = next((i for i, r in enumerate(rules) if (r.get('actions') or {}).get('courier') == 'sameday'), 0)
            ib = next((i for i, r in enumerate(rules) if (r.get('actions') or {}).get('hold') and any(c.get('field') == 'total' for c in r.get('conditions', []))), 2)
            pg.set_viewport_size({'width': 1440, 'height': 1000})
            goto(pg, '/settings/rules', '.rule')
            shot(pg, 'rules', {'ruleA': f'.rule:nth-of-type({ia + 1})', 'ruleB': f'.rule:nth-of-type({ib + 1})',
                               'rnameA': f'.rule:nth-of-type({ia + 1}) .rule-head', 'rnameB': f'.rule:nth-of-type({ib + 1}) .rule-head',
                               'section': '#section .card', 'subnav': '.subnav'}, full=True)
            goto(pg, '/settings/general', '.mode-switch')
            shot(pg, 'general', {'banner': '#test-banner', 'mode': '.mode-switch', 'probe': '.mode-switch .provider.active',
                                 'live': '.mode-switch .provider:not(.active)', 'after': '#section .card:nth-of-type(2)'})

            # 7. tracking: the test courier walks one COD parcel to "delivered"; COD is marked collected
            o = next(x for x in done if x['name'] == ARGS.track_order)
            for k in (1, 2, 3, 4):
                age_awb(o['awb'], 2 * k)
                api('POST', '/track'); time.sleep(.3)
            open_order(pg, o['id'])
            shot(pg, 'dtrack', DRAWER, el='.drawer-panel')
            MAN['dtrack']['li'] = pg.evaluate("[...document.querySelectorAll('.drawer-panel .timeline li')].map(l => l.className)")
            pg.set_viewport_size({'width': 1440, 'height': 900})
            pg.goto(f'{BASE}/#/'); pg.wait_for_selector('.stats'); pg.wait_for_timeout(600)
            shot(pg, 'dash_after', {**STATS, 'todo': '.cols > div > .card:first-child', 'activity': '.cols > .card'})
            MAN['dash_after']['texts'] = texts(pg, {k: v for k, v in STATS.items() if k[:3] in ('val', 'sub')})
            st = api('GET', '/stats'); MAN['stats_after'] = st
            # which stat card is "COD collected (30 days)": the one showing that number
            vals = {k: num(v) for k, v in MAN['dash_after']['texts'].items() if k.startswith('val') and v}
            MAN['codStat'] = next((int(k[3:]) for k, v in vals.items() if v is not None and abs(v - st['codCollected30']['v']) < .01), 4)
            b.close()
    finally:
        stop_server(srv)
    (OUT / 'manifest.json').write_text(json.dumps(MAN, ensure_ascii=False, indent=1))
    (OUT / 'manifest.js').write_text('window.UI_MANIFEST = ' + json.dumps(MAN, ensure_ascii=False) + ';\n')   # for the trailer page (file://)
    tot = sum(f.stat().st_size for f in OUT.glob('*.png'))
    print(f'wrote {len(list(OUT.glob("*.png")))} images, {tot // 1024} KB')

if __name__ == '__main__':
    main()
