/* SOUL on Indiegogo: every campaign image as an HTML/CSS template (v2). page.html?id=<id>; build.py screenshots #root.
   All numbers and size-dependent facts come from window.DATA (facts.json + docs/size-s.json + goal_model.py, via build.py).
   v2 rules (review 2026-10-20): story images carry the object, the eyes or one big number, never paragraphs or tables
   (those are text on the page); text left inside an image is >= 44 px on a 1200 px canvas; render labels are >= 30 px
   on 1200 x 630 images or live in the caption; the planned retail price is never a "% off" badge; renders use the
   re-graded finishes (cuts/, regrade.py); scale is shown only with the true-scale S drawing; no CE claim. */
(function () {
'use strict';
const D = window.DATA, F = D.facts, S = F.size_S, P = F.product, C = F.campaign, A = D.asset, MOD = F.model, LAD = F.lad, SCN = F.scn;
const SE = window.SoulEyes, DSG = window.SOUL_DESIGNS, DES = DSG.designs;
const byId = id => DES.find(d => d.id === id) || DES[0];
const Q = new URLSearchParams(location.search), ID = Q.get('id'), FPS = +(Q.get('fps') || 30);
const root = document.getElementById('root');
const PEND = [];
const RLBL = 'Render (CGI)';
const NB = ' ';
const eur = v => '€' + Math.round(v).toLocaleString('en-US');
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const mon = ym => MON[+ym.slice(5, 7) - 1] + ' ' + ym.slice(0, 4);
const ALL = {
  silver: { name: 'Silver', hex: '#B9BEC5', eyes: 'original' },
  graphite: { name: 'Graphite', hex: '#4C5259', eyes: 'tangerine-dream' },
  midnight: { name: 'Midnight', hex: '#34466B', eyes: 'sunday-toast' },
  ember: { name: 'Ember', hex: '#D9662F', eyes: 'sugar-cube' },
  champagne: { name: 'Champagne', hex: '#D2AE76', eyes: 'pistachio' },
};
const COLS = F.colours.map(n => { const k = n.toLowerCase(); return Object.assign({ k }, ALL[k]); });
const COL = ALL;

// ------------------------------------------------------------------------------------------------ helpers
function el(tag, cls, parent, html, style) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  if (style) e.style.cssText += style;
  (parent || root).appendChild(e);
  return e;
}
function at(e, x, y, extra) { e.style.position = 'absolute'; if (x != null) e.style.left = x + 'px'; if (y != null) e.style.top = y + 'px'; if (extra) e.style.cssText += extra; return e; }
function size(w, h) { root.style.width = w + 'px'; if (h) root.style.height = h + 'px'; }
function track(img) { PEND.push(new Promise(r => { if (img.complete && img.naturalWidth) r(); else { img.onload = r; img.onerror = () => { console.error('missing image ' + img.src); r(); }; } })); return img; }
function img(src, parent, style) { const i = el('img', null, parent, null, style); i.src = src; return track(i); }
function lbl(text, pos, fs, parent, info) {
  const e = el('div', 'lbl' + (info ? ' info' : ''), parent || root, text);
  e.style.fontSize = (fs || 30) + 'px';
  for (const k in pos) e.style[k] = typeof pos[k] === 'number' ? pos[k] + 'px' : pos[k];
  return e;
}
function shade(hex, t) {
  const n = parseInt(hex.slice(1), 16); let r = n >> 16, g = (n >> 8) & 255, b = n & 255; const m = t > 0 ? 255 : 0, a = Math.abs(t);
  r = Math.round(r + (m - r) * a); g = Math.round(g + (m - g) * a); b = Math.round(b + (m - b) * a);
  return `rgb(${r},${g},${b})`;
}
function ringGrad(hex) { return `linear-gradient(135deg, ${shade(hex, .45)} 0%, ${shade(hex, -.25)} 32%, ${shade(hex, .25)} 58%, ${shade(hex, -.45)} 100%)`; }
function settle(e, o) {
  if (o.look0) e.lookAt(o.look0[0], o.look0[1]);
  for (let i = 0; i < 45; i++) e.step(1 / 30);
  if (o.expr) e.setExpression(o.expr);
  if (o.look) e.lookAt(o.look[0], o.look[1]);
  for (let i = 0; i < (o.steps ?? 50); i++) e.step(1 / 30);
  let k = 0;
  while (!o.allowClosed && e.rig.closed() > 0.02 && k++ < 400) e.step(1 / 60);
}
function drawEyes(cv, id, o) {
  o = o || {};
  const px = o.px || 512;
  cv.width = px; cv.height = px;
  const e = SE.createEyes(cv, byId(id), { manual: true, interactive: false, mode: 'live', seed: o.seed ?? 11, fit: o.fit ?? 1,
    bezel: !!o.bezel, sheen: o.sheen ?? true, glass: o.glass ?? true, background: o.bg ?? null, hetero: true });
  if (!o.raw) settle(e, o);
  e.draw();
  return e;
}
/* a transparent cut-out (re-graded, images/src/cuts) with the real eye engine drawn on its screen */
function prod(key, h, o) {
  o = o || {};
  const Cc = D.cuts[key], s = h / Cc.h;
  if (!Cc) throw new Error('no cut ' + key);
  const box = el('div', 'prod', o.parent || root);
  box.style.width = (Cc.w * s) + 'px'; box.style.height = h + 'px';
  if (o.shadow !== false) {
    const sh = el('div', 'shadow', box);
    sh.style.width = (Cc.w * s * .9) + 'px'; sh.style.height = (Cc.w * s * .16) + 'px'; sh.style.bottom = (-Cc.w * s * .06) + 'px';
  }
  const inn = el('div', 'prod-in', box);
  inn.style.width = Cc.w + 'px'; inn.style.height = Cc.h + 'px'; inn.style.transform = `scale(${s})`;
  const im = img(Cc.dir + Cc.src, inn, `width:${Cc.w}px;height:${Cc.h}px`);
  if (o.filter) im.style.filter = o.filter;
  if (o.eyes !== false) {
    const N = 1000;
    const c = [Cc.c[0] * Cc.w, Cc.c[1] * Cc.h];
    const vx = [(Cc.ux[0] - Cc.c[0]) * Cc.w, (Cc.ux[1] - Cc.c[1]) * Cc.h];
    const vy = [-(Cc.uy[0] - Cc.c[0]) * Cc.w, -(Cc.uy[1] - Cc.c[1]) * Cc.h];
    const cv = el('canvas', null, inn);
    cv.style.width = N + 'px'; cv.style.height = N + 'px';
    cv.style.transform = `matrix(${2 * vx[0] / N},${2 * vx[1] / N},${2 * vy[0] / N},${2 * vy[1] / N},${c[0] - vx[0] - vy[0]},${c[1] - vx[1] - vy[1]})`;
    const dpx = Math.hypot(vx[0], vx[1]) * s * 2 * 2;
    box._eyes = drawEyes(cv, o.eyes || 'original', Object.assign({ px: Math.max(256, Math.min(1600, Math.round(dpx * 1.25))) }, o));
  }
  return box;
}
const cut = k => (k === 'silver' ? 'soul_front_silver' : 'soul_col_' + k);
/* the black round screen with the real eye engine (what the AMOLED shows); optional anodised ring */
function disc(id, d, o) {
  o = o || {};
  const w = el('div', 'disc', o.parent || root);
  w.style.width = d + 'px'; w.style.height = d + 'px';
  let host = w;
  if (o.ring) {
    w.style.background = ringGrad(o.ring);
    const rw = d * (o.rw || .05);
    host = el('div', null, w, null, `position:absolute;inset:${rw}px;border-radius:50%;background:#000;overflow:hidden`);
  } else {
    w.style.background = '#000';
    if (o.edge !== false) w.style.boxShadow = '0 0 0 2px #26262b';
  }
  const cv = el('canvas', null, host);
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%';
  w._eyes = drawEyes(cv, id, Object.assign({ px: Math.round(d * 2), fit: 1, sheen: false, glass: false }, o));
  return w;
}
function osShot(file, d, parent) {
  const w = el('div', 'disc', parent);
  w.style.cssText += `width:${d}px;height:${d}px;background:#000;box-shadow:0 0 0 ${Math.max(3, d * .02)}px #2b2b30`;
  img(A + 'os/screenshots/alive/' + file, w, 'position:absolute;inset:0;width:100%;height:100%;border-radius:50%');
  return w;
}
function wordmark(w, parent) { return img(A + 'brand/SOUL-Brand-Package/Logo/Wordmark/SVG/SOUL-Wordmark-On-Dark.svg', parent, `width:${w}px;height:auto;display:block`); }
function story(h) { size(1200, h); root.style.background = '#0B0B0C'; return root; }
function spot(parent, x, y, w, h) { return at(el('div', 'spot', parent), x, y, `width:${w}px;height:${h}px`); }
const dims = () => `${S.width_mm} × ${S.height_mm} mm`;
const depth = () => `${S.thickness_mm.min}–${S.thickness_mm.max} mm`;
const big = (parent, txt, fs, style) => el('div', 'h', parent, txt, `font-size:${fs}px;${style || ''}`);
const word = (parent, txt, fs, style) => el('div', null, parent, txt, `font-size:${fs}px;font-weight:600;letter-spacing:-.02em;line-height:1.1;${style || ''}`);

// ------------------------------------------------------------------------------------------------ the true-scale drawing
function outlinePts(Wmm, Hmm) {
  const O = D.outline, maxw = Math.max(...O.w), span = O.H - O.z_bot;
  const sx = Wmm / (2 * maxw), sy = Hmm / span;
  const right = O.z.map((z, i) => [Wmm / 2 + O.w[i] * sx, (O.H - z) * sy]);
  const left = right.slice().reverse().map(([x, y]) => [Wmm - x, y]);
  return { pts: right.concat(left), sy, sx, glassY: (O.H - O.zc) * sy, glassR: O.r_glass * sx };
}
const path = (pts, k, ox, oy) => 'M' + pts.map(([x, y]) => `${(ox + x * k).toFixed(1)},${(oy + y * k).toFixed(1)}`).join('L') + 'Z';
function sizeDrawing(k, o) {
  o = o || {};
  const R = F.size_graphics.reference_objects_mm, card = R['credit_card_ID-1'], coin = R.euro_coin_2;
  const W = S.width_mm, H = S.height_mm, gap = o.gap || 11, fs = o.fs || 30;
  const ol = outlinePts(W, H);
  const items = [];
  if (o.card !== false) items.push({ t: 'card', w: card[0], h: card[1] });
  items.push({ t: 'soul', w: W, h: H });
  if (o.coin !== false) items.push({ t: 'coin', w: coin, h: coin });
  const totalMm = items.reduce((a, b) => a + b.w, 0) + gap * (items.length - 1);
  const Hmm = Math.max(...items.map(i => i.h));
  const top = fs * 1.6, bottom = o.labels === false ? 8 : fs * (o.glassNote ? 3 : 2) + 44;
  const Wpx = totalMm * k, Hpx = Hmm * k + top + bottom;
  const box = el('div', null, o.parent || root, null, `position:relative;width:${Wpx}px;height:${Hpx}px;flex:none`);
  const base = top + Hmm * k;
  let x = 0, svg = '';
  const lab = [];
  for (const it of items) {
    const X = x * k, Y = base - it.h * k;
    if (it.t === 'card') {
      svg += `<defs><linearGradient id="cg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a3f4c"/><stop offset="1" stop-color="#23262e"/></linearGradient></defs>`;
      svg += `<rect x="${X}" y="${Y}" width="${it.w * k}" height="${it.h * k}" rx="${3.18 * k}" fill="url(#cg)" stroke="rgba(255,255,255,.18)" stroke-width="1.5"/>`;
      svg += `<rect x="${X + 8 * k}" y="${Y + 19 * k}" width="${11 * k}" height="${8.5 * k}" rx="${1.2 * k}" fill="#bfa76a" opacity=".85"/>`;
      lab.push([X + it.w * k / 2, 'bank card', `${card[0].toFixed(1)} × ${card[1].toFixed(1)} mm`]);
    } else if (it.t === 'coin') {
      const r = it.w / 2 * k, cx = X + r, cy = base - r;
      svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="#c9cbce"/><circle cx="${cx}" cy="${cy}" r="${r * .7}" fill="#c8a24a"/>`;
      lab.push([cx, '€2 coin', `Ø${coin} mm`]);
    } else {
      const col = o.colour || ALL.silver.hex;
      svg += `<defs><linearGradient id="sg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${shade(col, .3)}"/><stop offset=".55" stop-color="${col}"/><stop offset="1" stop-color="${shade(col, -.35)}"/></linearGradient></defs>`;
      svg += `<path d="${path(ol.pts, k, X, Y)}" fill="url(#sg)"/>`;
      const gx = X + W / 2 * k, gy = Y + ol.glassY * k, gr = S.glass_mm.product_route_A / 2 * k;   // Ø52 glass (size-s.json glass_d)
      svg += `<circle cx="${gx}" cy="${gy}" r="${gr}" fill="#000"/>`;
      svg += `<circle cx="${gx}" cy="${gy}" r="${S.screen.active_area_mm / 2 * k}" fill="none" stroke="rgba(255,240,200,.35)" stroke-width="1.5" stroke-dasharray="4 4"/>`;
      if (o.dimlines !== false) {
        const dy = Y - fs * .5;
        svg += `<g stroke="#FFF0C8" stroke-width="2" fill="none"><path d="M${X},${dy - 8}v16M${X + W * k},${dy - 8}v16M${X},${dy}H${X + W * k}"/></g>`;
        svg += `<text x="${X + W * k / 2}" y="${dy - 14}" fill="#FFF0C8" font-family="Martian Mono" font-size="${fs}" text-anchor="middle">${W} mm</text>`;
      }
      lab.push([X + W / 2 * k, `SOUL ${S.label}`, dims()]);
      if (o.glassNote) lab.push([X + W / 2 * k, '', `glass Ø${S.glass_mm.product_route_A} · screen Ø${S.screen.active_area_mm}`, true]);
      const sr = S.screen.active_area_mm / 2 * k;   // AMOLED active area Ø43.76: the eyes live inside it
      box._screen = { x: gx - sr, y: gy - sr, d: sr * 2 };
    }
    x += it.w + gap;
  }
  svg += `<line x1="-10" y1="${base + .5}" x2="${Wpx + 10}" y2="${base + .5}" stroke="rgba(255,255,255,.22)" stroke-width="1.5"/>`;
  if (o.labels !== false) lab.forEach(([cx, t1, t2, third]) => {
    if (third) { svg += `<text x="${cx}" y="${base + 3 * fs + 34}" fill="#A4A7AE" font-family="Martian Mono" font-size="${fs * .7}" text-anchor="middle">${t2}</text>`; return; }
    svg += `<text x="${cx}" y="${base + fs + 14}" fill="#F6F3EC" font-family="Bricolage Grotesque" font-weight="650" font-size="${fs}" text-anchor="middle">${t1}</text>`;
    svg += `<text x="${cx}" y="${base + 2 * fs + 26}" fill="#A4A7AE" font-family="Martian Mono" font-size="${fs * .8}" text-anchor="middle">${t2}</text>`;
  });
  el('div', null, box, `<svg width="${Wpx}" height="${Hpx}" viewBox="0 0 ${Wpx} ${Hpx}" style="overflow:visible;display:block">${svg}</svg>`);
  if (box._screen && o.eyes !== false) {
    const sc = box._screen, cv = el('canvas', null, box, null, `position:absolute;left:${sc.x}px;top:${sc.y}px;width:${sc.d}px;height:${sc.d}px;border-radius:50%`);
    drawEyes(cv, o.eyesId || 'original', { px: Math.round(sc.d * 2), fit: 1, sheen: false, glass: false, look: [0.15, 0.1] });
  }
  return box;
}

// ------------------------------------------------------------------------------------------------ templates
const T = {};

T.card_700 = () => {   // hero use case + scale: SOUL S on a desk next to a phone, eyes looking out; small corner pill
  size(700, 700);
  root.style.background = '#E9DCCB';
  v10frame('desk', root, 700, 700, 0.86, -430, -228, { eyes: 'original', look: [0.05, 0.1], seed: 4 });
  const b = at(el('div', null, root), 32, 520, 'background:rgba(11,11,12,.88);border-radius:26px;padding:20px 26px;width:560px');
  word(b, 'it looks up when<br>your AI needs you.', 46, 'color:#F6F3EC');
  lbl(RLBL, { right: 22, top: 22 }, 22);
};

T.cover = () => {   // no text, per Indiegogo; eyes engine screens with anodised rings in the launch colours
  size(1743, 498);
  root.style.background = 'radial-gradient(60% 120% at 62% 50%, #1b1b20 0%, #0B0B0C 70%)';
  const rings = COLS.map(c => c.hex);
  const L = [['bucharest-night', 150, 170, 150, [0.6, 0.2]], ['sugar-cube', 210, 420, 230, [0.5, 0]], ['original', 330, 860, 249, [0, 0.1]],
    ['sunday-toast', 230, 1210, 250, [-0.4, 0.1]], ['tangerine-dream', 170, 1450, 170, [-0.6, -0.1]], ['pistachio', 120, 1640, 330, [-0.7, 0.2]], ['cat-cafe', 110, 640, 400, [0.3, -0.3]]];
  L.forEach(([id, d, cx, cy, look], i) => at(disc(id, d, { ring: rings[i % rings.length], look, seed: 3 + i }), cx - d / 2, cy - d / 2));
};

T.social = () => {
  size(1200, 630);
  root.style.background = 'radial-gradient(60% 90% at 76% 50%, #26262c 0%, #111114 55%, #0B0B0C 90%)';
  const col = at(el('div', null, root), 64, 0, 'height:630px;width:600px;display:flex;flex-direction:column;justify-content:center;gap:28px');
  el('h1', 'h', col, 'your ai has a brain.<br><span class="g">give it a soul.</span>', 'font-size:76px');
  el('p', 'lead', col, 'A palm-sized aluminium stone with living eyes. Your own AI, or none.', 'font-size:32px;width:540px;color:#C8CAD0');
  spot(root, 640, 60, 560, 560);
  const others = COLS.filter(c => c.k !== 'silver');
  if (others[0]) at(prod(cut(others[0].k), 300, { eyes: others[0].eyes, look: [0.4, 0.1], seed: 5 }), 655, 250);
  if (others[1]) at(prod(cut(others[1].k), 300, { eyes: others[1].eyes, look: [-0.5, 0.1], seed: 8 }), 960, 250);
  at(prod('soul_front_silver', 440, { eyes: 'original', look: [0, 0.15] }), 768, 110);
  lbl(RLBL, { right: 24, bottom: 22 }, 30);
};

T.avatar = () => {
  size(700, 700);
  root.style.background = '#0D0D0F';
  at(img(A + 'brand/SOUL-Brand-Package/Logo/Symbol/SVG/SOUL-Symbol-On-Dark.svg', root, 'width:440px;height:auto'), 130, 130);
};

T.launch = () => {
  size(700, 700);
  root.style.background = 'radial-gradient(80% 70% at 62% 62%, #2a2a30 0%, #121215 55%, #0B0B0C 85%)';
  at(el('h1', 'h', root, 'SOUL is live<br><span class="g">on Indiegogo.</span>'), 44, 54, 'font-size:80px;width:620px');
  spot(root, 240, 230, 470, 470);
  at(prod('soul_front_silver', 400, { eyes: 'original', look: [-0.35, 0.05] }), 320, 250);
  at(el('div', 'btn', root, 'back SOUL →'), 44, 300, 'font-size:34px');
  lbl(RLBL, { left: 44, bottom: 36 }, 24);
};

T.update = () => {
  size(700, 700);
  root.style.background = 'radial-gradient(70% 70% at 50% 46%, #1d1d22 0%, #0B0B0C 75%)';
  at(el('div', 'eb nodash', root, 'backer update'), 52, 52, 'font-size:28px');
  at(disc('original', 360, { ring: ALL.silver.hex, expr: 'happy', look: [0, 0.1] }), 170, 140);
  at(wordmark(240), 230, 560);
};

// ---------------------------------------------------------------- gallery (1200 x 630), in page order
T.g1_approve = () => {   // gallery 1: the hero use case on the S screen, big
  size(1200, 630);
  root.style.background = 'radial-gradient(60% 90% at 74% 50%, #26262c 0%, #111114 55%, #0B0B0C 90%)';
  at(el('h1', 'h', root, 'it looks up when<br><span class="g">your AI needs you.</span>'), 64, 70, 'font-size:66px;width:600px');
  at(word(root, 'Claude asks on the glass.<br>Hold to allow, tap twice to deny.', 38, 'color:#C8CAD0;font-weight:450'), 64, 300);
  at(sShot('s-13-claude-ask.png', 520, root), 640, 55);
  lbl(OS_S, { left: 64, bottom: 34 }, 24, root, true);
};

T.g2_size = () => {
  size(1200, 630);
  root.style.background = '#0B0B0C';
  at(el('h1', 'h', root, 'palm-sized, <span class="g">for real.</span>'), 64, 52, 'font-size:68px');
  const box = sizeDrawing(4.4, { fs: 26 });
  at(box, (1200 - parseFloat(box.style.width)) / 2, 140);
  lbl('Illustration · true scale', { right: 24, top: 36 }, 24, root, true);
};

T.g3_hero = () => {
  size(1200, 630);
  root.style.background = 'radial-gradient(55% 90% at 74% 52%, #2a2a30 0%, #121215 55%, #0B0B0C 90%)';
  at(wordmark(300), 72, 90);
  at(el('h1', 'h', root, 'palm-sized.<br>aluminium.<br><span class="g">alive.</span>'), 72, 230, 'font-size:92px');
  spot(root, 610, 40, 560, 560);
  at(prod('soul_front_silver', 540, { eyes: 'original', look: [-0.25, 0.1] }), 660, 40);
  lbl(RLBL, { right: 24, bottom: 22 }, 30);
};

const G3 = ['original', 'tangerine-dream', 'bucharest-night', 'sunday-toast', 'watermelon', 'cat-cafe', 'sugar-cube', 'half-moon-bay', 'ladybug', 'starstruck', 'smitten', 'crown-jewel', 'opal', 'disco-ball', 'genesis'];
T.g4_eyes = () => {
  size(1200, 630);
  root.style.background = '#0B0B0C';
  at(el('h1', 'h', root, `born with one of <span class="g">${P.eyes.designs} eyes.</span>`), 64, 90, 'font-size:76px;width:380px');
  const g = at(el('div', 'grid', root), 470, 40, 'grid-template-columns:repeat(5,130px);gap:14px');
  G3.forEach((id, i) => disc(id, 130, { parent: g, seed: 40 + i, look: [((i * 37) % 7 - 3) / 5, ((i * 11) % 5 - 2) / 6] }));
  at(el('div', 'mono', root, 'eyes engine · screen images'), 64, 560, 'font-size:24px;color:#A4A7AE');
};


T.g5_colours = () => {
  size(1200, 630);
  root.style.background = 'radial-gradient(80% 70% at 50% 70%, #232328 0%, #0D0D0F 70%)';
  at(el('h1', 'h', root, 'you pick the body. <span class="g">the eyes pick themselves.</span>'), 64, 40, 'font-size:54px;width:820px');
  const row = at(el('div', null, root), 0, 175, 'width:1200px;display:flex;justify-content:center;gap:40px');
  COLS.forEach((c, i) => {
    const cell = el('div', null, row, null, 'display:flex;flex-direction:column;align-items:center;gap:18px');
    prod(cut(c.k), 330, { parent: cell, eyes: c.eyes, look: [0.15 * (i - 1), 0.15], seed: 20 + i });
    el('div', null, cell, c.name, 'font-size:34px;font-weight:650;color:#F6F3EC');
  });
  lbl(RLBL, { right: 24, top: 24 }, 30);
};

// ---------------------------------------------------------------- story (1200 wide; no paragraphs, no tables)
T.s01_object = () => {
  story(1050);
  root.style.background = 'radial-gradient(52% 50% at 50% 48%, #2a2a30 0%, #141417 55%, #0B0B0C 100%)';
  const p = prod('soul_front_silver', 900, { eyes: 'original', look: [0.05, 0.12] });
  at(p, (1200 - parseFloat(p.style.width)) / 2, 60);
};

const BORN = ['original', 'bucharest-night', 'mint-condition', 'sunday-toast', 'watermelon', 'snow-day', 'ski-lift', 'grape-soda',
  'cat-cafe', 'sugar-cube', 'half-moon-bay', 'ladybug', 'toaster', 'teardrop-teal',
  'starstruck', 'smitten', 'crown-jewel', 'hypno-toad', 'opal', 'disco-ball', 'vortex', 'midas-touch', 'night-over-sibiu', 'genesis'];
T.s02_eyes = () => {
  story(820);
  const g = at(el('div', 'grid', root), 60, 50, 'grid-template-columns:repeat(6,160px);gap:24px 28px');
  BORN.forEach((id, i) => disc(id, 160, { parent: g, seed: 70 + i, look: [((i * 37) % 7 - 3) / 5, ((i * 11) % 5 - 2) / 6] }));
};

T.s03_ai = () => {
  story(1080);
  const rows = [['original', 'your Claude', 'your own key · Claude app connector', 'listening'], ['sunday-toast', 'your OpenAI key', 'your own API key · in development', 'thinking'], ['sugar-cube', 'offline', 'no AI, no sign-up', 'happy']];
  rows.forEach(([id, a, b, expr], i) => {
    const r = at(el('div', null, root), 80, 60 + i * 340, 'display:flex;gap:56px;align-items:center');
    disc(id, 280, { parent: r, ring: ALL.silver.hex, expr, seed: 90 + i, look: i === 1 ? [0.5, -0.4] : [0, 0.1] });
    const t = el('div', null, r, null, 'display:flex;flex-direction:column;gap:14px');
    big(t, a, 92);
    word(t, b, 42, 'color:#A4A7AE;font-weight:450');
  });
};

T.s03b_approve = () => {   // the hero use case, one S screen at 2x, caption outside the circle
  story(1000);
  root.style.background = 'radial-gradient(55% 55% at 50% 42%, #22222a 0%, #0B0B0C 80%)';
  const d = 700;
  at(sShot('s-13-claude-ask.png', d, root), (1200 - d) / 2, 50);
  at(word(root, 'claude asks. you approve.', 60, 'color:#F6F3EC;text-align:center;width:1200px'), 0, 800);
  at(word(root, 'hold = allow · tap twice = deny', 40, 'color:#A4A7AE;font-weight:450;text-align:center;width:1200px'), 0, 880);
};

T.s04_soulos = () => {   // two S screens at 2x, a one-line caption outside each circle
  story(760);
  const items = [['s-36-msg.png', 'a message, answered with a tap.'], ['s-35-voice-answer.png', 'a reminder, set by your AI.']];
  items.forEach(([f, cap], i) => {
    const x = 60 + i * 560;
    at(sShot(f, 520, root), x, 40);
    at(word(root, cap, 40, 'color:#F6F3EC;text-align:center;width:520px'), x, 610);
  });
};

T.s05_colours = () => {
  story(820);
  root.style.background = 'radial-gradient(70% 60% at 50% 45%, #232328 0%, #0B0B0C 80%)';
  const row = at(el('div', null, root), 0, 70, 'width:1200px;display:flex;justify-content:center;gap:24px');
  COLS.forEach((c, i) => {
    const cell = el('div', null, row, null, 'display:flex;flex-direction:column;align-items:center;gap:30px');
    prod(cut(c.k), Math.round(1100 / COLS.length / 0.87), { parent: cell, eyes: c.eyes, look: [0.15 * (i - 1), 0.15], seed: 20 + i });
    big(cell, c.name.toLowerCase(), 64);
  });
};

T.s06_size = () => {
  story(1320);
  const k = 5.6;
  const box = sizeDrawing(k, { fs: 40, glassNote: true });
  at(box, (1200 - parseFloat(box.style.width)) / 2, 40);
  // M prototype (dashed) vs S product (filled), same scale; labels outside the dashed outline
  const k2 = 5.0, M = F.prototype_M.dims_mm, olS = outlinePts(S.width_mm, S.height_mm), olM = outlinePts(M[0], M[1]);
  const Wm = M[0] * k2, Hm = M[1] * k2, ox = 330, oy = 760;
  let sv = `<path d="${path(olM.pts, k2, ox, oy)}" fill="none" stroke="#A4A7AE" stroke-width="3" stroke-dasharray="12 10"/>`;
  const sx = ox + (Wm - S.width_mm * k2) / 2, sy = oy + Hm - S.height_mm * k2;
  sv += `<path d="${path(olS.pts, k2, sx, sy)}" fill="${ALL.silver.hex}"/>`;
  sv += `<circle cx="${ox + Wm / 2}" cy="${sy + olS.glassY * k2}" r="${S.glass_mm.product_route_A / 2 * k2}" fill="#000"/>`;
  sv += `<line x1="${ox - 60}" y1="${oy + Hm}" x2="${ox + Wm + 60}" y2="${oy + Hm}" stroke="rgba(255,255,255,.25)" stroke-width="2"/>`;
  el('div', null, root, `<svg width="1200" height="1320" style="position:absolute;left:0;top:0">${sv}</svg>`);
  at(word(root, `S<br><span style="color:#A4A7AE;font-size:34px">${dims()}</span>`, 44, 'color:#F6F3EC'), 60, oy + Hm - 120);
  at(word(root, `M prototype<br><span style="font-size:34px">${M[0]} × ${M[1]} mm</span>`, 44, 'color:#A4A7AE'), ox + Wm + 40, oy + 20);
};

/* S at true size, from the v10 renders (renders/v10, S scale). Only hand/desk/vs_m renders may show scale.
   v10eyes: the v10 renders still have the old glowing eyes; paint them out (the glass is ~#010100) and draw the flat
   SoulOS eyes from the eyes engine on the screen area (active Ø43.76 of the Ø52 glass), in the glass's perspective.
   Glass ellipses measured from the renders (1600 x 1200 px): centre, semi-axes, rotation (deg, clockwise). */
const V10GEO = { hand: { cx: 805.9, cy: 577.8, a: 200, b: 145.8, rot: 11.2 }, desk: { cx: 809, cy: 570.9, a: 126, b: 123, rot: 0 } };
function v10eyes(key, parent, o) {
  o = o || {};
  const g = V10GEO[key], k = S.screen.active_area_mm / S.glass_mm.product_route_A;
  const box = el('div', null, parent, null, 'position:absolute;left:0;top:0;width:1600px;height:1200px;transform-origin:0 0');
  img(V10(key), box, 'position:absolute;left:0;top:0;width:1600px;height:1200px');
  const cover = el('div', null, box, null, `position:absolute;left:${g.cx - g.a * .66}px;top:${g.cy - g.b * .66}px;width:${g.a * 1.32}px;height:${g.b * 1.32}px;border-radius:50%;transform:rotate(${g.rot}deg);background:radial-gradient(closest-side,#010100 78%,rgba(1,1,0,0) 100%)`);
  const N = 600, cv = el('canvas', null, box);
  cv.style.cssText = `position:absolute;left:${g.cx - N / 2}px;top:${g.cy - N / 2}px;width:${N}px;height:${N}px;transform:rotate(${g.rot}deg) scale(${2 * g.a * k / N},${2 * g.b * k / N});border-radius:50%;mix-blend-mode:lighten`;
  drawEyes(cv, o.eyes || 'original', Object.assign({ px: 900, fit: 1, sheen: false, glass: false }, o));
  return box;
}
/* fit a 1600 x 1200 v10 frame into w x h: scale s, offset (dx, dy) */
function v10frame(key, parent, w, h, s, dx, dy, o) {
  const clip = el('div', null, parent, null, `position:absolute;left:0;top:0;width:${w}px;height:${h}px;overflow:hidden`);
  const b = v10eyes(key, clip, o);
  b.style.transform = `translate(${dx}px,${dy}px) scale(${s})`;
  return clip;
}
function sShot(file, d, parent) {   // SoulOS simulator capture at the S profile (466 x 466), firmware/sim/shots/alive-s
  const w = el('div', 'disc', parent);
  w.style.cssText += `width:${d}px;height:${d}px;background:#000;box-shadow:0 0 0 ${Math.max(4, d * .022)}px #2b2b30`;
  img(A + 'firmware/sim/shots/alive-s/' + file, w, 'position:absolute;inset:0;width:100%;height:100%;border-radius:50%');
  return w;
}
const OS_S = 'SoulOS simulator · S, 466 × 466';
const V10 = k => { const R = F.renders_v10 || {}, f = R.files && R.files[k]; if (!f) throw new Error('renders_v10 has no ' + k); return A + 'renders/v10/' + f; };
T.s06b_hand = () => {
  story(1080);
  root.style.background = '#EFE3D6';
  v10frame('hand', root, 1200, 900, 0.75, 0, 0, { eyes: 'original', look: [0, -0.45], seed: 6 });
  const band = at(el('div', null, root), 0, 900, 'width:1200px;height:180px;background:#0B0B0C;display:flex;align-items:center;padding:0 64px;gap:28px');
  word(band, `SOUL ${S.label} in an adult hand · ${dims()}`, 46, 'color:#F6F3EC');
  lbl(RLBL, { right: 24, top: 24 }, 26);
};

T.s06c_desk = () => {
  story(1080);
  v10frame('desk', root, 1200, 900, 0.75, 0, 0, { eyes: 'original', look: [-0.35, 0.05], seed: 8 });
  const band = at(el('div', null, root), 0, 900, 'width:1200px;height:180px;background:#0B0B0C;display:flex;align-items:center;padding:0 64px');
  word(band, `next to a phone (71.5 × 147 mm), same scale`, 46, 'color:#F6F3EC');
  lbl(RLBL, { right: 24, top: 24 }, 26);
};

T.g6_hand = () => {
  size(1200, 630);
  root.style.background = '#EFE3D6';
  v10frame('hand', root, 1200, 630, 0.75, 0, -150, { eyes: 'original', look: [0, -0.45], seed: 6 });
  const b = at(el('div', null, root), 40, 440, 'background:rgba(11,11,12,.86);border-radius:28px;padding:22px 30px');
  word(b, `fits in your palm.<br><span style="color:#A4A7AE">${dims()}</span>`, 52, 'color:#F6F3EC');
  lbl(RLBL, { right: 24, top: 24 }, 26);
};

T.s07_ou_night = () => {
  story(900);
  root.style.background = 'radial-gradient(45% 50% at 50% 55%, #3a2414 0%, #140d09 50%, #050505 100%)';
  const p = prod('soul_ou', 760, { eyes: 'original', expr: 'sleepy', allowClosed: true, filter: 'brightness(.62) sepia(.25)' });
  at(p, (1200 - parseFloat(p.style.width)) / 2, 70);
};

T.s08_box = () => {
  story(1200);
  const g = at(el('div', 'grid', root), 50, 50, 'grid-template-columns:535px 535px;gap:30px');
  const item = title => {
    const c = el('div', 'card', g, null, 'height:535px;display:flex;flex-direction:column;overflow:hidden;background:radial-gradient(70% 60% at 50% 40%, #26262c, #161619 70%)');
    const v = el('div', null, c, null, 'flex:1;display:flex;align-items:center;justify-content:center;min-height:0');
    big(c, title, 56, 'padding:0 36px 36px');
    return v;
  };
  prod('soul_front_silver', 330, { parent: item(`SOUL ${S.label}`), eyes: 'original', look: [0, 0.1] }).style.marginTop = '30px';
  prod('soul_ou', 330, { parent: item('OU'), eyes: 'original', expr: 'sleepy', allowClosed: true }).style.marginTop = '30px';
  el('div', null, item('USB-C cable'), `<svg width="420" height="260" viewBox="0 0 420 260"><path d="M60 210 C 60 120, 150 120, 210 150 S 340 200, 350 90" fill="none" stroke="#55575B" stroke-width="12" stroke-linecap="round"/><rect x="40" y="200" width="40" height="44" rx="8" fill="#B9BEC5"/><rect x="330" y="50" width="40" height="44" rx="8" fill="#B9BEC5" transform="rotate(10 350 72)"/></svg>`);
  el('div', null, item('quick guide'), `<svg width="300" height="300" viewBox="0 0 300 300"><rect x="70" y="40" width="170" height="230" rx="12" fill="#F6F3EC" transform="rotate(-6 155 155)"/><g transform="rotate(-6 155 155)"><circle cx="155" cy="105" r="38" fill="#0B0B0C"/><ellipse cx="143" cy="104" rx="7" ry="9" fill="#FFF0C8"/><ellipse cx="167" cy="104" rx="7" ry="9" fill="#FFF0C8"/><rect x="100" y="165" width="110" height="10" rx="5" fill="#C4C0B6"/><rect x="100" y="187" width="90" height="10" rx="5" fill="#C4C0B6"/></g></svg>`);
};

T.s09_privacy = () => {
  story(1240);
  const tiles = [['no camera', 'suspicious', 'original'], ['hold to talk', 'listening', 'bucharest-night'], ['memory on the stone', 'thinking', 'sunday-toast'],
    ['your AI only', 'happy', 'sugar-cube'], ['always says it\'s an AI', 'smug', 'cat-cafe'], ['never a brick', 'love', 'smitten']];
  const g = at(el('div', 'grid', root), 50, 50, 'grid-template-columns:535px 535px;gap:30px');
  tiles.forEach(([t, e, id], i) => {
    const c = el('div', 'card', g, null, 'height:350px;padding:40px;display:flex;flex-direction:column;justify-content:space-between');
    disc(id, 150, { parent: c, ring: ALL.silver.hex, expr: e, seed: 120 + i, rw: .06 });
    big(c, t, 58, 'line-height:1');
  });
};

T.s10_budget = () => {   // bars carry their € amounts; ~40 % shorter than v2
  const L = MOD.budget_lines;
  story(250 + L.length * 82);
  at(big(root, eur(MOD.goal_eur), 120), 60, 36);
  at(word(root, 'all-or-nothing goal', 40, 'color:#A4A7AE;font-weight:450'), 64, 170);
  const colors = { make: '#FFF0C8', setup: '#FF5A1F', cont: '#2440FF', vat: '#8C8F96', fees: '#55575B', fail: '#3a3a40', refund: '#6B4CC9' };
  const short = { make: 'making every SOUL', setup: 'batch set-up', cont: 'contingency', vat: F.pricing.vat_registered ? 'VAT' : 'VAT we expect to owe', fees: 'platform + payment fees', fail: 'failed payments', refund: 'refund reserve' };
  const max = Math.max(...L.map(l => l.pct));
  L.forEach((l, i) => {
    const y = 240 + i * 82;
    at(word(root, short[l.k] || l.label, 38), 60, y + 6);
    const bw = Math.max(10, 330 * l.pct / max);
    at(el("div", null, root, null, `width:${bw}px;height:44px;border-radius:12px;background:${colors[l.k] || "#55575B"}`), 520, y + 4);
    at(el("div", "mono", root, `${eur(l.eur)} · ${Math.round(l.pct * 100)}${NB}%`), 520 + bw + 18, y + 8, 'font-size:30px;color:#F6F3EC;white-space:nowrap');
  });
};

T.s11_timeline = () => {
  const short = { campaign: 'the campaign', money: 'payments', make: null, ship: 'shipping starts', promise: null };
  const rows = [];
  // before launch: only gates that have passed, with a tick and their date
  (SCN.before_launch || []).forEach(([d, k, what]) => { const g = F.gates[k]; if (g && g.passed) rows.push([`✓ ${g.date ? g.date.slice(8, 10) + ' ' + mon(g.date) : mon(d)}`, what, 'done']); });
  const makeNames = ['orders', 'machining', 'anodising', 'pilot run', 'assembly + test'];
  let mi = 0;
  SCN.timeline.forEach(([a, b, what, kind]) => {
    const when = b ? (mon(a) === mon(b) ? mon(a) : `${mon(a).split(' ')[0]}–${mon(b)}`) : mon(a);
    let t = short[kind];
    if (kind === 'make') t = makeNames[mi++] || 'making';
    if (kind === 'promise') t = what.includes('batch 2') ? 'delivery, batch 2 (estimate)' : 'delivery, batch 1 (estimate)';
    rows.push([when, t, kind]);
  });
  story(100 + rows.length * 112);
  const col = { done: '#7BD88F', campaign: '#FFF0C8', money: '#8C8F96', make: '#FF5A1F', ship: '#2440FF', promise: '#FFF0C8' };
  el('div', null, root, null, `position:absolute;left:441px;top:70px;height:${rows.length * 112 - 50}px;width:3px;background:rgba(255,255,255,.18)`);
  rows.forEach(([w, t, k], i) => {
    const y = 50 + i * 112, bigrow = k === 'promise' || k === 'campaign';
    at(el('div', 'mono', root, w), 0, y + 8, `width:400px;text-align:right;font-size:${bigrow ? 40 : 34}px;color:${bigrow ? '#FFF0C8' : '#C8CAD0'}`);
    at(el('i', null, root, null, `width:30px;height:30px;border-radius:50%;background:${col[k]};box-shadow:0 0 0 8px #0B0B0C`), 428, y + 14);
    at(word(root, t, bigrow ? 56 : 46, bigrow ? 'font-weight:720' : ''), 490, y);
  });
};

T.s13_team = () => {
  story(900);
  const ph = el('div', null, root, null, 'background:repeating-linear-gradient(-45deg,#FFF0C8 0 22px,#16181D 22px 44px);color:#16181D;padding:16px 60px;font:600 26px/1.3 var(--f-m)');
  el('span', null, ph, 'PLACEHOLDER · never published · replace with a real photo', 'background:#FFF0C8;padding:6px 12px;border-radius:8px');
  el('div', 'ph', root, '<div class="mono" style="font-size:34px;text-align:center;line-height:1.4">founder photo<br>(real, not generated)</div>', 'position:absolute;left:300px;top:180px;width:600px;height:600px;border-radius:50%;display:flex;align-items:center;justify-content:center');
};

T.s12_stretch = () => {
  const SG = MOD.stretch_goals;
  story(150 + SG.length * 300);
  const what = { languages: 'SoulOS in DE, FR, ES, IT', pouch: 'a felt pouch in every box', birth_card: 'a printed birth card in every box' };
  SG.forEach((g, i) => {
    const c = at(el('div', 'card', root), 50, 50 + i * 300, 'width:1100px;height:260px;padding:40px 50px;display:flex;flex-direction:column;justify-content:center;gap:14px');
    big(c, eur(g.at_eur), 110, 'color:#FFF0C8');
    word(c, what[g.id], 52);
  });
};

// ---------------------------------------------------------------- rewards (700 x 700): never a "% off" badge
function perk(o) {
  size(700, 700);
  root.style.background = o.bg || 'radial-gradient(85% 70% at 62% 50%, #26262c 0%, #121215 55%, #0B0B0C 88%)';
  at(el('div', 'eb nodash', root, o.kind || 'reward'), 40, 36, 'font-size:22px');
  at(el('div', 'h', root, o.name), 40, 74, `font-size:${o.name.length > 18 ? 50 : 64}px;width:${o.render ? 470 : 620}px;line-height:.95`);
  const v = at(el('div', null, root), 0, 0, 'width:700px;height:700px;pointer-events:none');
  o.visual(v);
  const p = at(el('div', null, root), 40, 452, 'display:flex;align-items:baseline;gap:16px');
  el('div', 'h', p, o.price, 'font-size:96px;letter-spacing:-.05em');
  if (o.per) el('div', 'mono', p, o.per, 'font-size:24px;color:#C8CAD0');
  const ch = at(el('div', 'chips', root), 40, 572, 'gap:10px;width:620px');
  (o.chips || []).forEach(([t, cream]) => el('span', 'pill' + (cream ? ' cream' : ''), ch, t, 'font-size:20px;padding:.5em .8em'));
  if (o.render) lbl(RLBL, { right: 22, top: 30 }, 22);
}
const retailChip = () => [`planned retail after the campaign: ${eur(LAD.retail_planned_eur)}`, true];
T.perk_supporter = () => perk({
  name: 'Soul Supporter', price: eur(F.pricing.supporter_eur), chips: [['no device', false], ['backer updates', false]],
  visual: v => { at(disc('original', 300, { parent: v, ring: ALL.silver.hex, expr: 'love', seed: 3 }), 360, 170); },
});
const single = (name, price, colour, chips) => () => perk({
  name, price: eur(price), render: true, chips,
  visual: v => { spot(v, 250, 140, 420, 420); at(prod(cut(colour), 380, { parent: v, eyes: COL[colour].eyes, look: [-0.3, 0.1], seed: 31 }), colour === 'silver' ? 330 : 345, 140); },
});
T.perk_first_light = single('First Light', LAD.launch.price_eur, 'silver', [[`first ${LAD.launch.cap}`, false], ['number engraved on the foot', false], retailChip()]);
T.perk_campaign = single('Campaign Price', LAD.campaign.price_eur, COLS[1] ? COLS[1].k : 'graphite', [[`batch 1 · ${LAD.campaign.cap}`, false], retailChip()]);
T.perk_campaign_b2 = single('Campaign Price · batch 2', LAD.campaign_b2.price_eur, COLS[0] ? COLS[0].k : 'silver', [[`batch 2 · delivery ${mon(SCN.estimated_delivery.late_pledge_batch_2)}`, true], retailChip()]);
T.perk_two_souls = () => perk({
  name: 'Two Souls', price: eur(LAD.two.price_eur), per: `${eur(LAD.two.price_eur / 2)} each`, render: true,
  chips: [['First Light price each', false], [`${LAD.two.cap} sets · batch 1`, false]],
  visual: v => {
    spot(v, 150, 140, 520, 420);
    const a = COLS[2] || COLS[0], b = COLS[1] || COLS[0];
    at(prod(cut(a.k), 330, { parent: v, eyes: a.eyes, look: [0.5, 0.1], seed: 7 }), 230, 160);
    at(prod(cut(b.k), 330, { parent: v, eyes: b.eyes, look: [-0.5, 0.1], seed: 9 }), 420, 160);
  },
});
T.perk_ou = () => perk({
  kind: 'add-on', name: 'Extra OU egg', price: eur(F.pricing.ou_extra_eur), render: true, chips: [['the egg only', true], ['SOUL not included', false]],
  visual: v => { spot(v, 250, 140, 440, 440); at(prod('soul_ou', 370, { parent: v, eyes: 'original', expr: 'sleepy', allowClosed: true }), 320, 140); },
});
T.perk_late = () => perk({
  kind: 'after the campaign', name: 'Late Pledge', price: eur(LAD.late_pledge_eur), render: true, chips: [[`delivered with batch 2 · ${mon(SCN.estimated_delivery.late_pledge_batch_2)}`, true]],
  visual: v => { spot(v, 250, 140, 420, 420); const c = COLS[COLS.length - 1]; at(prod(cut(c.k), 380, { parent: v, eyes: c.eyes, look: [-0.3, 0.1], seed: 13 }), 345, 140); },
});

// ---------------------------------------------------------------- stretch goals (700 x 700)
function stretch(i, visual) {
  const g = MOD.stretch_goals[i];
  size(700, 700);
  root.style.background = 'radial-gradient(80% 70% at 50% 40%, #1f1f24 0%, #0D0D0F 75%)';
  at(el('div', 'eb nodash', root, `stretch goal ${i + 1}`), 44, 40, 'font-size:24px');
  at(el('div', 'h', root, eur(g.at_eur)), 44, 84, 'font-size:112px;color:#FFF0C8');
  const what = { languages: 'SoulOS in German, French, Spanish and Italian', pouch: 'a felt travel pouch in every box', birth_card: 'a printed birth card in every box: your SOUL\'s eyes, chip ID and birth date' };
  at(el('div', null, root, what[g.id]), 44, 224, 'font-size:40px;font-weight:650;letter-spacing:-.02em;line-height:1.12;width:610px');
  const v = at(el('div', null, root), 0, 0, 'width:700px;height:700px');
  visual(v);
}
T.stretch_1 = () => stretch(0, v => { const row = at(el('div', 'chips', v), 44, 430, 'gap:16px'); ['DE', 'FR', 'ES', 'IT'].forEach(t => el('span', 'pill', row, t, 'font-size:44px;padding:.5em .8em;font-weight:600')); });
T.stretch_3 = () => stretch(2, v => {
  const c = at(el('div', null, v), 330, 400, 'width:320px;height:220px;border-radius:18px;background:#F6F3EC;transform:rotate(-5deg);display:flex;gap:20px;align-items:center;padding:24px');
  disc('original', 120, { parent: c, seed: 3, look: [0.2, 0.1] });
  el('div', 'mono', c, 'born<br>C0FFEE…<br>2028', 'font-size:22px;color:#16181D;line-height:1.5');
  at(el('div', 'mono', v, 'drawing'), 44, 620, 'font-size:24px;color:#A4A7AE');
});
T.stretch_2 = () => stretch(1, v => {
  at(el('div', null, v, `<svg width="300" height="230" viewBox="0 0 300 230"><path d="M30 60 Q150 20 270 60 L262 200 Q150 225 38 200 Z" fill="#3b3b42"/><circle cx="150" cy="128" r="30" fill="#0B0B0C"/><ellipse cx="141" cy="127" rx="5" ry="7" fill="#FFF0C8"/><ellipse cx="159" cy="127" rx="5" ry="7" fill="#FFF0C8"/></svg>`), 360, 400);
  at(el('div', 'mono', v, 'drawing'), 44, 620, 'font-size:24px;color:#A4A7AE');
});

// ---------------------------------------------------------------- animations, 1200 x 900 (stepped by build.py: ANIM.frame(i))
T.anim_eyes = () => {   // just the black round screen, as on the AMOLED: no drawn bezel
  size(1200, 900);
  root.style.background = '#000';
  const d = disc('original', 780, { raw: true, look0: [0, 0], edge: false });
  at(d, 210, 60);
  const e = d._eyes;
  e.lookAt(0, 0); for (let i = 0; i < 60; i++) e.step(1 / 30);
  const script = [[0.7, () => e.lookAt(-0.9, 0.05)], [1.6, () => e.lookAt(0.9, -0.3)], [2.4, () => e.blink(2)], [2.9, () => e.lookAt(0.15, 0.55)],
    [3.6, () => e.react('happy', 1.4)], [5.3, () => e.lookAt(0, 0)], [5.6, () => e.blink(1)]];
  let k = 0;
  window.ANIM = { frame(i) { const t = i / FPS; while (k < script.length && script[k][0] <= t) script[k++][1](); e.step(1 / FPS); e.draw(); } };
};
T.anim_colours = () => {
  size(1200, 900);
  root.style.background = 'radial-gradient(60% 70% at 50% 46%, #26262c 0%, #111114 60%, #0B0B0C 90%)';
  spot(root, 330, 40, 540, 600);
  const ps = COLS.map((c, i) => { const p = prod(cut(c.k), 680, { eyes: c.eyes, raw: true, seed: 20 + i }); at(p, (1200 - parseFloat(p.style.width)) / 2, 40); p.style.visibility = i ? 'hidden' : 'visible'; p._eyes.lookAt(0, 0.1); for (let j = 0; j < 40; j++) p._eyes.step(1 / 30); return p; });
  const name = at(el('div', 'h', root, COLS[0].name.toLowerCase()), 0, 770, 'width:1200px;text-align:center;font-size:84px');
  const seg = 1.8;
  let cur = 0, blinked = -1;
  window.ANIM = {
    frame(i) {
      const t = i / FPS, n = Math.floor(t / seg) % COLS.length, u = t - Math.floor(t / seg) * seg;
      if (n !== cur) { ps[cur].style.visibility = 'hidden'; ps[n].style.visibility = 'visible'; cur = n; name.textContent = COLS[n].name.toLowerCase(); ps[n]._eyes.hop(); }
      const e = ps[cur]._eyes;
      if (u > seg - 0.25 && blinked !== Math.floor(t / seg)) { blinked = Math.floor(t / seg); e.blink(1); }
      if (Math.abs(u - 0.9) < 0.5 / FPS) e.lookAt(n % 2 ? -0.5 : 0.5, 0.1);
      e.step(1 / FPS); e.draw();
    },
  };
};
T.anim_dial_bg = () => {
  size(1200, 900);
  root.style.background = '#000';
  const d = 780, x = 210, y = 60;
  window.SLOT = { x, y, d };
};

// video stills: the S object with the flat eyes, 1920 x 1080, for the hook and "the object" moments
T.vid_hook = () => {
  size(1280, 720);
  root.style.background = 'radial-gradient(45% 60% at 50% 50%, #26262c 0%, #111114 60%, #0B0B0C 100%)';
  spot(root, 340, 40, 600, 640);
  const p = prod('soul_front_silver', 600, { eyes: 'original', raw: true, look0: [0, 0], px: 900, shadow: false });
  at(p, (1280 - parseFloat(p.style.width)) / 2, 60);
  const e = p._eyes;
  e.setExpression && e.setExpression('sleepy');
  for (let i = 0; i < 40; i++) e.step(1 / 30);
  const script = [[0.35, () => { e.setExpression('neutral'); e.blink(1); }], [0.9, () => e.lookAt(-0.6, 0.1)], [1.6, () => e.lookAt(0.5, 0.05)], [2.3, () => e.lookAt(0, 0.15)], [2.9, () => e.react('happy', 1.2)]];
  let k = 0;
  window.ANIM = { frame(i) { const t = i / FPS; while (k < script.length && script[k][0] <= t) script[k++][1](); e.step(1 / FPS); e.draw(); } };
};
T.vid_colours = () => {
  size(1920, 1080);
  root.style.background = 'radial-gradient(70% 60% at 50% 55%, #232328 0%, #0B0B0C 80%)';
  const row = at(el('div', null, root), 0, 150, 'width:1920px;display:flex;justify-content:center;gap:80px');
  COLS.forEach((c, i) => prod(cut(c.k), 700, { parent: row, eyes: c.eyes, look: [0.2 * (i - 1), 0.15], seed: 20 + i }));
};

// ------------------------------------------------------------------------------------------------ run
(async () => {
  try {
    if (!T[ID]) throw new Error('unknown id ' + ID);
    T[ID]();
    await Promise.all(PEND);
    await document.fonts.ready;
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  } catch (e) { console.error(e && e.stack || e); }
  window.READY = true;
})();
})();
