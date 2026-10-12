// Smoke renderer: approximates Shopify Liquid for the SOUL theme so the output can be opened in a browser.
const { Liquid } = require('liquidjs');
const fs = require('fs'), path = require('path');
const T = process.argv[2], OUTD = process.argv[3];
const read = f => fs.readFileSync(path.join(T, f), 'utf8');
const strip = s => s.replace(/{%-?\s*schema\s*-?%}[\s\S]*?{%-?\s*endschema\s*-?%}/g, '').replace(/posted_successfully\?/g, 'posted_successfully');
const engine = new Liquid({ root: [path.join(T, 'snippets')], extname: '.liquid', fs: {
  readFileSync: f => strip(fs.readFileSync(f, 'utf8')), readFile: async f => strip(fs.readFileSync(f, 'utf8')),
  existsSync: fs.existsSync, exists: async f => fs.existsSync(f), resolve: (r, f, e) => path.resolve(r, f.endsWith(e) ? f : f + e), contains: () => true, dirname: path.dirname, sep: '/' } });
let LOC = {};
const get = (o, k) => k.split('.').reduce((a, p) => a && a[p], o);
const kw = args => { const o = {}; args.forEach(a => { if (Array.isArray(a)) o[a[0]] = a[1]; }); return o; };
engine.registerFilter('t', (k, ...a) => { let v = get(LOC, k); if (v == null) return 'MISSING:' + k; const o = kw(a); return String(v).replace(/{{\s*(\w+)\s*}}/g, (_, n) => o[n] ?? ''); });
engine.registerFilter('asset_url', n => 'assets/' + n);
const money = c => '€' + (Number(c) / 100).toFixed(0);
engine.registerFilter('money', c => money(c)); engine.registerFilter('money_without_trailing_zeros', c => money(c)); engine.registerFilter('money_with_currency', c => money(c) + ' EUR');
engine.registerFilter('preload_tag', (u, ...a) => `<link rel="preload" href="${u}" ${Object.entries(kw(a)).map(([k, v]) => `${k}="${v}"`).join(' ')}>`);
engine.registerFilter('stylesheet_tag', u => `<link rel="stylesheet" href="${u}">`);
engine.registerFilter('image_url', (i) => i && i.src);
engine.registerFilter('image_tag', (u, ...a) => `<img src="${u}" width="10" height="10" alt="${kw(a).alt || ''}">`);
engine.registerFilter('default_errors', e => String(e)); engine.registerFilter('structured_data', () => '');
engine.registerFilter('handleize', s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''));
engine.registerFilter('time_tag', d => d); engine.registerFilter('format_code', d => d);
function renderSection(type, settings, id, ctx) {
  const src = read(`sections/${type}.liquid`);
  const sch = JSON.parse((src.match(/{%\s*schema\s*%}([\s\S]*?){%\s*endschema\s*%}/) || [0, '{}'])[1]);
  const html = engine.parseAndRenderSync(strip(src), { ...ctx, section: { id, settings } });
  return `<div id="shopify-section-${id}" class="shopify-section ${sch.class || ''}">${html}</div>`;
}
engine.registerTag('sections', { parse(t) { this.g = t.args.replace(/['"]/g, '').trim(); },
  * render(ctx) { const g = JSON.parse(read(`sections/${this.g}.json`)); const c = ctx.getAll(); return g.order.map(k => renderSection(g.sections[k].type, g.sections[k].settings, k, c)).join('\n'); } });
engine.registerTag('section', { parse(t) { this.s = t.args.replace(/['"]/g, '').trim(); }, * render(ctx) { return renderSection(this.s, {}, this.s, ctx.getAll()); } });
engine.registerTag('form', { parse(t, rem) { this.args = t.args; this.tpls = []; const s = this.liquid.parser.parseStream(rem); s.on('tag:endform', () => s.stop()).on('template', x => this.tpls.push(x)).on('end', () => { throw new Error('no endform'); }); s.start(); },
  * render(ctx, emitter) { const id = (this.args.match(/id: '([^']+)'/) || [])[1] || ''; const cls = (this.args.match(/class: '([^']+)'/) || [])[1] || '';
    const nat = /data-native/.test(this.args) ? ' data-native="true"' : '';
    emitter.write(`<form method="post" action="/x" id="${id}" class="${cls}"${nat} novalidate>`); ctx.push({ form: { posted_successfully: false, errors: null } }); yield this.liquid.renderer.renderTemplates(this.tpls, ctx, emitter); ctx.pop(); emitter.write('</form>'); } });
const product = { title: 'SOUL', url: '/products/soul', description: '<p>The stone.</p>', price_varies: false, has_only_default_variant: false, media: [], price_min: 24900,
  options_with_values: [{ name: 'Colour', selected_value: 'Ember', values: ['Silver', 'Graphite', 'Midnight', 'Ember', 'Champagne'] }],
  variants: ['Silver', 'Graphite', 'Midnight', 'Ember', 'Champagne'].map((c, i) => ({ id: 100 + i, title: c, options: [c], available: false, price: 24900 })) };
product.selected_or_first_available_variant = product.variants[3];
const base = lang => ({ settings: JSON.parse(read('config/settings_data.json')).current, request: { locale: { iso_code: lang }, page_type: 'index' },
  routes: { root_url: lang === 'ro' ? '/ro' : '/', cart_url: '/cart', cart_add_url: '/cart/add', search_url: '/search' },
  localization: { available_languages: [{ iso_code: 'en', endonym_name: 'English' }, { iso_code: 'ro', endonym_name: 'Română' }], language: { iso_code: lang },
    available_countries: [{ iso_code: 'RO', name: 'Romania', currency: { iso_code: 'RON', symbol: 'lei' } }, { iso_code: 'DE', name: 'Germany', currency: { iso_code: 'EUR', symbol: '€' } }], country: { iso_code: 'RO' } },
  shop: { name: 'SOUL', privacy_policy: { url: '/policies/privacy-policy' }, terms_of_service: { url: '/policies/terms-of-service' } },
  cart: { item_count: 0, currency: { iso_code: 'EUR' }, items: [] }, page_title: 'SOUL', canonical_url: 'https://soul.example/', current_page: 1, content_for_header: '' });
// snippets see theme settings as globals, like on Shopify
engine.options.globals = { settings: JSON.parse(read('config/settings_data.json')).current };
for (const [tplName, lang] of [['index', 'en'], ['index', 'ro'], ['product', 'en'], ['page.legal', 'ro']]) {
  LOC = JSON.parse(read(`locales/${lang === 'en' ? 'en.default' : lang}.json`));
  const tpl = JSON.parse(read(`templates/${tplName}.json`));
  const ctx = { ...base(lang), template: { name: tplName.split('.')[0] }, product, page: { title: 'Legal', content: '<p>text</p>' } };
  const content = tpl.order.map(k => renderSection(tpl.sections[k].type, tpl.sections[k].settings, k, ctx)).join('\n');
  const html = engine.parseAndRenderSync(strip(read('layout/theme.liquid')), { ...ctx, content_for_layout: content });
  fs.writeFileSync(path.join(OUTD, `${tplName}-${lang}.html`), html);
  const miss = html.match(/MISSING:[\w.]+/g); console.log(tplName, lang, html.length, miss ? miss : 'ok', /{{|{%/.test(html) ? 'LIQUID LEFT' : '');
}
