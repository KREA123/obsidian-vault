/*
  Verificare pachet A fără să atingem tema live: Chromium deschide pagina reală,
  iar HTML-ul primit e rescris în browser cu exact ce ar produce codul nou din
  pachet (snippets/*.liquid). Nimic nu se trimite înapoi la magazin.
  Rulare: node prototip.js <url> <eticheta> <lățime> <înălțime> [before|after]
*/
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PW || '/opt/node22/lib/node_modules/playwright');

const PKG = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(PKG, f), 'utf8');
const pick = (src, tag) => (src.match(new RegExp(`<${tag}>[\\s\\S]*?</${tag}>`)) || [''])[0];

const SHIP = '<p class="pp-ship {cls}">Livrare 25 lei · Cargus · ajunge în 24–72 de ore</p>';
const SEARCH_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';

function transform(html, url) {
  const isProduct = /\/products\//.test(url);
  const isHome = new URL(url).pathname === '/';
  let n = 0; const rep = (re, to) => { const b = html; html = html.replace(re, to); if (b !== html) n++; else console.warn('  ! fără potrivire:', String(re).slice(0, 80)); };

  // A1 · vechea bară #buybar (markup + scriptul ei)
  if (isProduct) rep(/<div class="buybar" id="buybar"[\s\S]*?<\/button>\s*<\/div>\s*<script>[\s\S]*?butonul a ieșit pe sus[\s\S]*?<\/script>/, '');

  // A6 · stelele: doar dacă produsul are recenzii reale (numărul și media vin din Judge.me, prin STELE=medie,număr)
  const [avg, cnt] = (process.env.STELE || '0,0').split(',').map(Number);
  const STARS = cnt > 0 ? `<a class="pp-stars" href="#judgeme_product_reviews"><span class="pp-stars-s" aria-hidden="true"><span style="width:${avg * 20}%">★★★★★</span></span><span class="pp-stars-n">${avg.toFixed(1).replace('.', ',')} · ${cnt} ${cnt === 1 ? 'recenzie' : 'recenzii'}</span></a>` : '';
  if (isProduct) {
    // A2 + A6 · stiluri, linia de livrare sub preț (sus pe telefon și în coloana de info)
    rep(/(shopify-forms-embed\{display:none!important\}\s*\}\s*<\/style>)/, `$1\n${pick(read('snippets/mundi-pp-style.liquid'), 'style')}`);
    rep(/(<div class="pp-mtop-p">[\s\S]*?<\/div>)(\s*<p class="pp-mtop-s">)/, `$1\n      ${STARS}${SHIP.replace('{cls}', 'pp-mtop-ship')}$2`);
    // A3 · „Retur 14 zile” ca link: sus și în lista de lângă buton
    rep(/(<p class="pp-mtop-s">[^<]*?)Retur 14 zile<\/p>/, '$1<a href="/pages/politica-de-retur">Retur 14 zile</a></p>');
    rep(/(<\/div>)(<div class="stock">)● În stoc — livrare în 24–72 ore<\/div>/, `$1${STARS}$2● În stoc</div>${SHIP.replace(' {cls}', '')}`);
    rep(/(<div class="trust">[\s\S]*?<svg[\s\S]*?<\/svg>)Retur simplu în 14 zile/, '$1<a href="/pages/politica-de-retur">Retur simplu în 14 zile</a>');
    // A8 · preîncărcarea pozei principale (LCP) în <head>
    const m = html.match(/<figure class="gals">\s*<img src="([^"]+)"\s*srcset="([^"]+)"\s*sizes="([^"]+)"/);
    if (m) rep(/(<meta name="viewport"[^>]*>)/, `$1<link rel="preload" as="image" fetchpriority="high" imagesrcset="${m[2]}" imagesizes="${m[3]}">`);
    // A8 · animația cu minifigurine: nu pe produs
    rep(/intro\(\);\s*peekers\(\);/, "if (TPL !== 'product') intro();\n    peekers();");
    // Recenzii · widgetul Judge.me existent (azi la ~9.800 px, după produsele similare) urcă imediat după
    // secțiunea principală; secțiunea goală și blocul Hoppy (aplicație dezactivată) ies din șablon.
    const jm = html.match(/<div id="shopify-section-template--\d+__1786919316f319acbc"[\s\S]*?(?=<div id="shopify-section-template--\d+__178913132619078dc7")/);
    if (jm) {
      rep(jm[0], () => '');
      rep(/<div id="shopify-section-template--\d+__product_extras"/, m => jm[0] + m);
      rep(/<div id="shopify-section-template--\d+__178913132619078dc7"[\s\S]*?(?=<\/main>)/, '');
    } else console.warn('  ! secțiunea Judge.me nu a fost găsită');
  }

  // A4 · header pe un rând
  rep(/(<div class="mh-act">\s*)/, `$1<button type="button" class="mh-sbtn" id="mh-sbtn" aria-label="Caută" aria-expanded="false" aria-controls="mh-sform">${SEARCH_SVG}</button>\n      `);
  rep(/<form class="mh-search"/, '<form class="mh-search" id="mh-sform"');
  if (isHome) rep(/<header class="mh-bar" id="mh-bar">/, '<header class="mh-bar mh-bar--home" id="mh-bar">');
  const hdr = read('snippets/mundi-header-mobil.liquid');
  rep(/(\s*<main class="pagew">)/, `${pick(hdr, 'style')}${pick(hdr, 'script')}$1`);

  // A7 · subsol: fără SOL (platforma ODR a fost închisă pe 20.07.2025), rămâne SAL
  rep(/<a href="https:\/\/ec\.europa\.eu\/consumers\/odr">[^<]*<\/a>/, '');
  rep(/\s*<a href="https:\/\/ec\.europa\.eu\/consumers\/odr" target="_blank" rel="noopener"><span class="mf-badge"><b>SOL<\/b>[^<]*<\/span><\/a>/, '');

  return { html, n };
}

async function run(url, tag, W, H, mode) {
  const SPKI = process.env.SPKI;
  const browser = await chromium.launch({ executablePath: process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined, args: SPKI ? ['--ignore-certificate-errors-spki-list=' + SPKI] : [] });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'ro-RO',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/450.0.0.0;FBLC/ro_RO]' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message.slice(0, 160)));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 160)); });
  await page.route(u => u.href.split('?')[0] === url.split('?')[0], async route => {
    const resp = await route.fetch();
    let body = await resp.text();
    if (mode === 'after') { const t = transform(body, url); body = t.html; console.log(`  ${t.n} modificări aplicate`); }
    await route.fulfill({ response: resp, body });
  });
  await page.goto(url, { waitUntil: 'load', timeout: 90000 });
  await page.waitForTimeout(4500);   // lasă animațiile de intrare să treacă
  const out = path.join(process.env.OUT || '.', `${tag}-${mode}-${W}x${H}`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await page.screenshot({ path: out + '-1-primul-ecran.png' });
  const m = await page.evaluate(() => {
    const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); const cs = getComputedStyle(e); return cs.display === 'none' ? 'ascuns' : { top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height) }; };
    return { strip: r('.mh-strip'), header: r('#mh-bar'), titlu: r('.pp-mtop-t'), pret: r('.pp-mtop-now'), livrare: r('.pp-mtop .pp-ship'), poza: r('.gals img'), barMbb: r('#mbb'), buybar: r('#buybar'), overflowX: document.documentElement.scrollWidth > innerWidth };
  });
  const btn = await page.$('#mbb');
  await page.evaluate(() => window.scrollTo(0, 1400));
  await page.waitForTimeout(700);
  await page.screenshot({ path: out + '-2-derulat.png' });
  const bars = await page.evaluate(() => [...document.querySelectorAll('body *')].filter(e => { const cs = getComputedStyle(e); if (cs.position !== 'fixed') return false; const b = e.getBoundingClientRect(); return b.height > 30 && b.bottom > innerHeight - 5 && b.top < innerHeight && b.left < innerWidth && b.right > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; }).map(e => '#' + e.id + ' .' + e.className));
  let extra = {};
  if (mode === 'after' && await page.$('#mh-sbtn')) {
    await page.evaluate(() => window.scrollTo(0, 0));
    const vis = await page.isVisible('#mh-sbtn');
    if (vis) { await page.click('#mh-sbtn'); await page.waitForTimeout(300); await page.screenshot({ path: out + '-3-cautare-deschisa.png' });
      extra.cautare = await page.evaluate(() => ({ focus: document.activeElement && document.activeElement.type, header: Math.round(document.getElementById('mh-bar').getBoundingClientRect().height) })); }
  }
  const rev = await page.$('#judgeme_product_reviews');
  if (rev) { await rev.scrollIntoViewIfNeeded(); await page.waitForTimeout(5000); await page.screenshot({ path: out + '-4-recenzii.png' });
    extra.recenzii = await page.evaluate(() => { const w = document.getElementById('judgeme_product_reviews'); return w ? { top: Math.round(w.getBoundingClientRect().top + scrollY), h: Math.round(w.getBoundingClientRect().height), paginaH: document.body.scrollHeight, text: w.innerText.replace(/\s+/g, ' ').slice(0, 160) } : null; }); }
  const foot = await page.$('footer.mf');
  if (foot) { await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await page.waitForTimeout(500); await page.screenshot({ path: out + '-5-subsol.png' });
    extra.sol = await page.evaluate(() => document.querySelectorAll('a[href*="ec.europa.eu/consumers/odr"]').length);
    extra.sal = await page.evaluate(() => document.querySelectorAll('a[href*="anpc.ro/ce-este-sal"]').length); }
  console.log(JSON.stringify({ url, mode, W, H, primulEcran: m, bareLaBazaEcranului: bars, ...extra, erori: errors }, null, 1));
  await browser.close();
}

if (require.main === module) {
  const [url, tag, W, H, mode] = process.argv.slice(2);
  run(url, tag || 'pagina', +(W || 390), +(H || 660), mode || 'after').catch(e => { console.error(e); process.exit(1); });
}
module.exports = { transform };
