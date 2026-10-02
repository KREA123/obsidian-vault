#!/usr/bin/env python3
"""Capture the real Expedo UI for the trailer (Playwright, deviceScaleFactor 2).

Starts the app in demo mode on a fresh database, drives it through the UI and the API
(exactly what a merchant would click), and saves crisp screenshots + element rectangles:

  ui/<shot>.png        2x screenshots (a page viewport, or one element such as the order drawer)
  ui/label_<n>.png     pages of the labels PDF (one PDF for the whole bulk run), rasterised by pdftoppm
  ui/manifest.json(.js) {shot: {w, h, rects: {name: [x, y, w, h]}}}  in CSS px of the shot (image px / 2)

The app source is never edited. Two things are set up in the demo database, because the demo
uses the test courier (which never talks to a real courier nomenclator):
  * order #1111 gets the address "Eforie" and the error the real Cargus adapter raises for it.
    The message is produced by the app's own code (src/couriers/locality.js: matchLocality +
    localityError) against real Constanța county locality names, so it is word-for-word what the
    merchant sees live: "Localitatea „Eforie” nu există în nomenclatorul Cargus … Ai vrut: Eforie Sud,
    Eforie Nord, Corbu?"
  * the test courier's issue time of one AWB is moved back step by step, so tracking walks through
    every status (ridicat → depozit → în livrare → livrat → ramburs încasat) in seconds, not minutes.
Plus one DOM-only element: the customer-refusal warning (CUSTOMER_REFUSED_BEFORE) is newer than this
frozen copy of the UI, so it is rendered into the drawer with the app's own .warn-box markup and the
exact message text from src/core/build.js (working copy) and captured as a crop.

usage: python3 capture.py        env: APP_DIR (frozen app), PORT (3301), DB_FILE
"""
import json, os, pathlib, re, shutil, sqlite3, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
APP = pathlib.Path(os.environ.get('APP_DIR', '/tmp/claude-0/expedo-snap/P/apps/expedo'))
PORT = int(os.environ.get('PORT', 3301))
DB = pathlib.Path(os.environ.get('DB_FILE', '/tmp/claude-0/trailer-demo.db'))
BASE = f'http://localhost:{PORT}'
OUT = HERE / 'ui'
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
                                 headers={'X-Expedo-Request': '1', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as r:
        b = r.read()
        return json.loads(b) if r.headers.get('content-type', '').startswith('application/json') else b

def start_server():
    for f in DB.parent.glob(DB.name + '*'): f.unlink()
    env = {**os.environ, 'DEMO': '1', 'PORT': str(PORT), 'DB_FILE': str(DB)}
    p = subprocess.Popen(['node', '--disable-warning=ExperimentalWarning', 'src/server.js'], cwd=APP, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(100):
        try: urllib.request.urlopen(BASE + '/healthz'); break
        except Exception: time.sleep(.2)
    time.sleep(1.5)            # demo seed + advanceDemo (processes 8 orders)
    return p

def order_id(name):
    return next(o['id'] for o in api('GET', '/orders?status=all&q=' + urllib.parse.quote(name))['orders'] if o['name'] == name)

# ── #1111: the customer typed "Eforie"; Cargus has only "Eforie Nord" / "Eforie Sud" → real adapter error
def setup_locality_error():
    js = """
      import { matchLocality, localityError } from '%s/src/couriers/locality.js';
      const CT = ['Constanta','Mangalia','Medgidia','Navodari','Ovidiu','Eforie Nord','Eforie Sud','Techirghiol','Cumpana',
        'Valu lui Traian','Lumina','Agigea','Mamaia-Sat','Corbu','Tuzla','23 August','Costinesti','Murfatlar','Basarabi',
        'Poarta Alba','Mihail Kogalniceanu','Cernavoda','Harsova','Negru Voda'].map((name, i) => ({ id: i + 1, name }));
      const q = { city: 'Eforie', county: 'Constanta', zip: '' };
      const e = localityError({ provider: 'cargus', providerName: 'Cargus', city: q.city, county: q.county, result: matchLocality(q, CT, { fuzzy: true }) });
      console.log(JSON.stringify(e.toJSON()));
    """ % APP
    err = json.loads(subprocess.run(['node', '--input-type=module', '-e', js], capture_output=True, text=True, check=True).stdout)
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    row = con.execute("SELECT id, data, store_id FROM orders WHERE name = '#1111'").fetchone()
    d = json.loads(row['data'])
    for k in ('shippingAddress', 'billingAddress'):
        d[k].update(city='Eforie', address1='Str. Tudor Vladimirescu nr. 12', zip='')
    now = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
    con.execute('UPDATE orders SET data = ?, last_error = ?, status = ? WHERE id = ?',
                (json.dumps(d), json.dumps({**err, 'step': 'awb', 'at': now}), 'needs_attention', row['id']))
    con.execute('INSERT INTO events (store_id, order_id, level, step, message, data) VALUES (?, ?, ?, ?, ?, ?)',
                (row['store_id'], row['id'], 'error', 'awb', err['message'], json.dumps({'hint': err['hint'], 'code': err['code'], 'details': err['details']})))
    con.commit(); con.close()
    print('locality error:', err['message'], '|', err['hint'])

def age_awb(awb, minutes):
    """Moves the test courier's issue time of one AWB back, so the next tracking check sees the next status."""
    con = sqlite3.connect(DB)
    store_id, raw = con.execute("SELECT store_id, value FROM cache WHERE key = 'mock:issued'").fetchone()
    v = json.loads(raw); v[awb]['at'] = int(time.time() * 1000 - minutes * 60_000 - 5_000)
    con.execute("UPDATE cache SET value = ? WHERE store_id = ? AND key = 'mock:issued'", (json.dumps(v), store_id))
    con.commit(); con.close()

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

DRAWER = {
    'head': '.drawer-head', 'badge': '.drawer-head .badge', 'error': '.drawer-panel .error-box', 'error_title': '.drawer-panel .error-box strong',
    'error_hint': '.drawer-panel .error-box .hint', 'details': '.drawer-panel .error-box details', 'process': '[data-act=process]',
    'actions': '.drawer-panel .actions', 'city': 'input[name=city]', 'phone': 'input[name=phone]', 'county': 'select[name=province]',
    'zip': 'input[name=zip]', 'addr_card': 'text=.drawer-panel .card|Adresa de livrare', 'addr_save': 'text=#addr-form button|Salvează adresa',
    'livrare': 'text=.drawer-panel .card|Livrare', 'kv': '.drawer-panel .kv', 'history': 'text=.drawer-panel .card|Istoric',
    'timeline': '.drawer-panel .timeline', 'cod_badge': '.drawer-panel .kv .badge.ok', 'awb': '.drawer-panel .kv dd .mono',
    'aivrut': 'range=.drawer-panel .error-box .hint|Ai vrut: Eforie Sud, Eforie Nord, Corbu?', 'nord': 'range=.drawer-panel .error-box .hint|Eforie Nord',
    'factura': 'text=.drawer-panel .kv dd|TEST 0', 'pay': 'text=.drawer-panel .kv dd|ramburs',
    **{f'li{i}': f'.drawer-panel .timeline li:nth-child({i + 1})' for i in range(12)},
}

def main():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob('*.png'): f.unlink()
    srv = start_server()
    try:
        setup_locality_error()
        with sync_playwright() as p:
            b = p.chromium.launch(args=['--force-color-profile=srgb', '--font-render-hinting=none'])
            ctx = b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=2, color_scheme='light', locale='ro-RO',
                                timezone_id='Europe/Bucharest')
            pg = ctx.new_page(); pg.route('**/*', route)
            pg.on('dialog', lambda d: d.accept())

            # 1. dashboard before anything
            goto(pg, '/')
            stats = {**{f'stat{i}': f'.stats > :nth-child({i + 1})' for i in range(5)},
                     **{f'val{i}': f'.stats > :nth-child({i + 1}) .value' for i in range(5)}, **{f'sub{i}': f'.stats > :nth-child({i + 1}) .sub' for i in range(5)}}
            shot(pg, 'dash_before', {**stats, 'todo': 'text=.card|De rezolvat', 'banner': '#test-banner', 'brand': '.brand',
                                     'cta': '.page-head .btn.primary', 'activity': 'text=.card|Activitate recentă'})

            # 2. orders that need attention: plain-Romanian errors, in red
            goto(pg, '/orders?status=needs_attention')
            rows = {f'row{i}': f'tbody tr:nth-child({i + 1})' for i in range(4)}
            issues = {**{f'issue{i}': f'tbody tr:nth-child({i + 1}) .issue-line' for i in range(4)},
                      **{f'msg{i}': f'lines=tbody tr:nth-child({i + 1}) .issue-line > span' for i in range(4)}}
            shot(pg, 'orders_attention', {**rows, **issues, 'table': '.table-wrap', 'tabs': '.tabs', 'tab_bad': 'text=.tabs a|Necesită'})
            goto(pg, '/orders')
            shot(pg, 'orders_open', {**{f'row{i}': f'tbody tr:nth-child({i + 1})' for i in range(10)}, 'table': '.table-wrap', 'tabs': '.tabs'}, full=True)

            # 3. #1111 — the address is checked against the courier's locality list: "Ai vrut: …?"
            o1111 = order_id('#1111')
            open_order(pg, o1111)
            shot(pg, 'd1111_err', DRAWER, el='.drawer-panel')
            pg.locator('input[name=city]').click(); pg.wait_for_timeout(100)
            pg.locator('input[name=city]').press('End'); pg.locator('input[name=city]').type(' Nord', delay=40)
            shot(pg, 'd1111_typed', DRAWER, el='.drawer-panel')
            pg.locator('#addr-form button', has_text='Salvează adresa').click()
            toast(pg, 'toast_addr_saved'); pg.wait_for_timeout(500)
            shot(pg, 'd1111_saved', DRAWER, el='.drawer-panel')
            pg.locator('[data-act=process]').click()
            toast(pg, 'toast_1111_done'); pg.wait_for_timeout(600)
            shot(pg, 'd1111_done', DRAWER, el='.drawer-panel')

            # 4. #1113 — missing phone: say it in Romanian, fix it in the order
            o1113 = order_id('#1113')
            open_order(pg, o1113)
            shot(pg, 'd1113_err', DRAWER, el='.drawer-panel')
            pg.locator('input[name=phone]').click(); pg.locator('input[name=phone]').type('0733 111 222', delay=40)
            shot(pg, 'd1113_typed', DRAWER, el='.drawer-panel')
            pg.locator('#addr-form button', has_text='Salvează adresa').click()
            toast(pg, 'toast_1113_saved'); pg.wait_for_timeout(500)
            shot(pg, 'd1113_fixed', DRAWER, el='.drawer-panel')

            # 5. customer refusal warning (newer than this UI snapshot): the app's own .warn-box markup + message
            o1117 = order_id('#1117')
            open_order(pg, o1117)
            pg.evaluate("""() => {
              const box = document.createElement('div'); box.className = 'warn-box'; box.id = 'refused';
              box.innerHTML = '<strong>Clientul a refuzat 2 colete înainte (din 3).</strong><div class="hint">Sună-l înainte de AWB sau cere plata cu cardul.</div>';
              document.querySelector('.drawer-head').after(box);
            }""")
            shot(pg, 'warn_refused', el='#refused')
            shot(pg, 'd1117_refused', DRAWER, el='.drawer-panel')

            # 6. bulk: select every order that is ready → one click → AWB + invoice → one labels PDF
            pg.set_viewport_size({'width': 1440, 'height': 900})
            pg.goto(f'{BASE}/#/'); pg.wait_for_selector('.stats')
            goto(pg, '/orders?status=ready')
            rsel = {**{f'row{i}': f'tbody tr:nth-child({i + 1})' for i in range(8)}, **{f'cb{i}': f'tbody tr:nth-child({i + 1}) input' for i in range(8)},
                    'checkall': '#check-all', 'table': '.table-wrap', 'tabs': '.tabs', 'tab_ready': 'text=.tabs a|Gata de procesat'}
            shot(pg, 'ready', rsel)
            pg.locator('#check-all').check(); pg.wait_for_timeout(300)
            bsel = {**rsel, 'bulkbar': '#bulkbar', 'bulk_count': '#bulk-count', 'bulk_all': '[data-bulk=all]', 'bulk_labels': '[data-bulk=labels]'}
            shot(pg, 'ready_selected', bsel)
            ready_ids = sorted(pg.evaluate("[...document.querySelectorAll('[data-check]')].map(c => Number(c.dataset.check))"))
            pg.locator('[data-bulk=all]').click()
            toast(pg, 'toast_bulk')
            pg.wait_for_selector('tbody tr .mono'); pg.wait_for_timeout(800)
            shot(pg, 'bulk_done', {**bsel, **{f'awb{i}': f'tbody tr:nth-child({i + 1}) td:nth-child(5)' for i in range(8)},
                                   **{f'inv{i}': f'tbody tr:nth-child({i + 1}) td:nth-child(6)' for i in range(8)},
                                   **{f'st{i}': f'tbody tr:nth-child({i + 1}) td:nth-child(7)' for i in range(8)}})
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

            # 7. rules + test mode
            pg.set_viewport_size({'width': 1440, 'height': 1000})
            goto(pg, '/settings/rules', '.rule')
            shot(pg, 'rules', {**{f'rule{i}': f'.rule:nth-of-type({i + 1})' for i in range(3)}, 'section': '#section .card', 'subnav': '.subnav',
                               **{f'rname{i}': f'.rule:nth-of-type({i + 1}) .rule-head' for i in range(3)}}, full=True)
            goto(pg, '/settings/general', '.mode-switch')
            shot(pg, 'general', {'banner': '#test-banner', 'mode': '.mode-switch', 'probe': '.mode-switch .provider.active',
                                 'live': '.mode-switch .provider:not(.active)', 'after': 'text=.card|După generarea'})

            # 8. tracking: the test courier walks one ramburs parcel to "Livrat", ramburs marked collected
            o = next(x for x in done if x['name'] == '#1118')
            for k in (1, 2, 3, 4):
                age_awb(o['awb'], 2 * k)
                api('POST', '/track'); time.sleep(.3)
            open_order(pg, o['id'])
            shot(pg, 'd1118_tracked', DRAWER, el='.drawer-panel')
            pg.set_viewport_size({'width': 1440, 'height': 900})
            pg.evaluate("location.hash = '#/'"); pg.wait_for_timeout(300)
            pg.goto(f'{BASE}/#/'); pg.wait_for_selector('.stats'); pg.wait_for_timeout(600)
            shot(pg, 'dash_after', {**stats, 'todo': 'text=.card|De rezolvat', 'activity': 'text=.card|Activitate recentă',
                                    'couriers': 'text=.card|Curieri'})
            MAN['stats_after'] = api('GET', '/stats')
            b.close()
    finally:
        srv.terminate()
    (OUT / 'manifest.json').write_text(json.dumps(MAN, ensure_ascii=False, indent=1))
    (OUT / 'manifest.js').write_text('window.UI_MANIFEST = ' + json.dumps(MAN, ensure_ascii=False) + ';\n')   # for the trailer page (file://)
    tot = sum(f.stat().st_size for f in OUT.glob('*.png'))
    print(f'wrote {len(list(OUT.glob("*.png")))} images, {tot // 1024} KB')

if __name__ == '__main__':
    import urllib.parse
    main()
