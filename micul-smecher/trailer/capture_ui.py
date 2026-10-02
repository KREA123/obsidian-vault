#!/usr/bin/env python3
"""capture_ui.py -- renders the real SoulOS screens (os/index.html, English UI) crisp at 3x for the trailer:
the #screen element of the live simulator in a given state, masked to its circle, saved as assets/ui_<name>.webp.
Google Fonts are fetched through the proxy (CA bundle) and served to the page by a route, so the UI fonts are right.
    python3 capture_ui.py [state ...]
"""
import re
import os
import sys, numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
P = 'file://' + os.path.abspath(os.path.join(HERE, '..', 'os', 'index.html'))
OUT = os.path.join(HERE, 'assets') + '/'
TMP = '/tmp/soul_ui_raw.png'
STATES = {
 'home':   "go('home','none')",
 'alarms': "go('alarms','none')",
 'kbd':    "go('claude','none'); kbOpen({ctx:'claude', initial:'Remind me to call Ana'})",
 'claude': "go('home','none'); claudeArrive(); go('claude','none')",
 'approved': "claudeDecide(true)",
 'today':  "go('today','none')",
 'apps':   "go('apps','none')",
 'weather':"go('weather','none')",
 'talk':   "go('talk','none')",
 'reminders': "go('reminders','none')",
 'notes': "go('notes','none')",
}
order = sys.argv[1:] or list(STATES)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--allow-file-access-from-files'])
    ctx=b.new_context(viewport={'width':1440,'height':900},device_scale_factor=3, ignore_https_errors=True)
    import urllib.request, ssl, os
    sslctx=ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
    cache={}
    def handler(route):
        u=route.request.url
        if u not in cache:
            req=urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'})
            r=urllib.request.urlopen(req, context=sslctx); cache[u]=(r.read(), r.headers.get('content-type'))
        body,ct=cache[u]
        route.fulfill(status=200, body=body, headers={'content-type':ct,'access-control-allow-origin':'*'})
    ctx.route(re.compile(r'https://fonts\.(googleapis|gstatic)\.com/.*'), handler)
    pg=ctx.new_page()
    pg.on('console', lambda m: print('[page]', m.text) if m.type=='error' else None)
    pg.goto(P); pg.wait_for_timeout(2500)
    pg.evaluate('document.fonts.ready.then(()=>1)')
    pg.click('#lang-en'); pg.wait_for_timeout(600)
    print('fonts', pg.evaluate("[...document.fonts].filter(f=>f.status=='loaded').map(f=>f.family).join(',')"))
    for k in order:
        pg.evaluate('window.showPill0=window.showPill0||showPill; hidePill(); S.nh=[];' + ('showPill=window.showPill0;' if k=='approved' else 'showPill=()=>{};')); pg.evaluate(STATES[k]); pg.wait_for_timeout(1800)
        el=pg.query_selector('#screen')
        el.screenshot(path=TMP)
        im=np.asarray(Image.open(TMP).convert('RGB')).astype(np.float32)
        h,w,_=im.shape; yy,xx=np.mgrid[0:h,0:w]; r=min(h,w)/2
        d=np.hypot(xx-(w-1)/2,yy-(h-1)/2)
        a=np.clip(r-d,0,1)
        Image.fromarray(np.dstack([im,a*255]).astype(np.uint8),'RGBA').save(OUT+'ui_'+k+'.webp','WEBP',quality=94,alpha_quality=100,method=6)
        print(k, w, h)
    b.close()
