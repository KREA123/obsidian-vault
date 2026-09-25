/* throwaway helpers for the SoulOS 3 language mockups (static, 466 px round screens) */
const C = 233;
let uidN = 0;
/* the eyes, approximated from Face.cpp: ellipses with a tilted upper lid, a soft highlight and a glow */
function eyes(cx, cy, k, gx = 0, gy = 0, col = "#FFF0C8", open = 1) {
  const S = 466 * k, out = [];
  for (const side of [-1, 1]) {
    const ex = cx + (side * 0.19 + gx * 0.055) * S, ey = cy + (0.02 + gy * 0.06) * S;
    const rx = 0.12 * S, ry = 0.19 * S * open, id = "e" + (++uidN);
    const yTop = ey - ry + 2 * 0.19 * ry, kk = Math.tan(0.16) * (-side);
    const lx0 = ex - rx * 1.4, lx1 = ex + rx * 1.4;
    out.push(`<clipPath id="${id}"><path d="M${lx0} ${yTop + kk * (lx0 - ex)} L${lx1} ${yTop + kk * (lx1 - ex)} L${lx1} ${ey + ry + 5} L${lx0} ${ey + ry + 5}Z"/></clipPath>
      <g clip-path="url(#${id})"><ellipse cx="${ex}" cy="${ey}" rx="${rx}" ry="${ry}" fill="${col}" filter="url(#glow)"/>
      <ellipse cx="${ex + rx * 0.22}" cy="${ey - ry * 0.12}" rx="${rx * 0.34}" ry="${ry * 0.46}" fill="#fff" opacity=".45"/></g>`);
  }
  return out.join("");
}
const defs = `<defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`;
/* arcs for text on the rim: bottom arcs run left→right through 6 o'clock (text upright, inside the rim) */
const bottomArc = (r, span = 170) => { const a0 = (90 + span / 2) * Math.PI / 180, a1 = (90 - span / 2) * Math.PI / 180; return `M${C + r * Math.cos(a0)} ${C + r * Math.sin(a0)} A${r} ${r} 0 0 0 ${C + r * Math.cos(a1)} ${C + r * Math.sin(a1)}`; };
const topArc = (r, span = 170) => { const a0 = (-90 - span / 2) * Math.PI / 180, a1 = (-90 + span / 2) * Math.PI / 180; return `M${C + r * Math.cos(a0)} ${C + r * Math.sin(a0)} A${r} ${r} 0 0 1 ${C + r * Math.cos(a1)} ${C + r * Math.sin(a1)}`; };
function rimText(txt, deg, r, style, where = "bottom") {
  const id = "p" + (++uidN), d = where === "bottom" ? bottomArc(r) : topArc(r), rot = where === "bottom" ? -deg : deg;
  return `<path id="${id}" d="${d}" fill="none"/><g transform="rotate(${rot} ${C} ${C})"><text style="${style}"><textPath href="#${id}" startOffset="50%" text-anchor="middle">${txt}</textPath></text></g>`;
}
function arc(r, a0, a1, stroke, w = 3, extra = "") {
  const P = a => [C + r * Math.cos(a * Math.PI / 180), C + r * Math.sin(a * Math.PI / 180)], [x0, y0] = P(a0), [x1, y1] = P(a1);
  return `<path d="M${x0} ${y0} A${r} ${r} 0 ${Math.abs(a1 - a0) > 180 ? 1 : 0} ${a1 > a0 ? 1 : 0} ${x1} ${y1}" fill="none" stroke="${stroke}" stroke-width="${w}" stroke-linecap="round" ${extra}/>`;
}
/* the SoulOS line glyphs: 24-unit grid, one stroke weight, round caps, no fills */
const G = {
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/>',
  cloud: '<path d="M7 18.5h10a4 4 0 0 0 .4-8 5.6 5.6 0 0 0-10.8 1.4A3.3 3.3 0 0 0 7 18.5z"/>',
  bell: '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  moon: '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5v3"/>',
  wave: '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2"/>',
  eyeClosed: '<path d="M4 11q4 4 8 0M12 11q4 4 8 0"/>',
  spark: '<path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4"/>',
  prompt: '<path d="M4 7l5 5-5 5M11 17h9"/>',
  note: '<path d="M6 3.5h9l3 3v14H6z"/><path d="M9 10h6M9 13.5h6M9 17h3.5"/>',
  alarm: '<circle cx="12" cy="13" r="7"/><path d="M12 9.5V13l2.5 1.8M4 6.5l3-2.5M20 6.5l-3-2.5"/>',
  sunLow: '<path d="M4 17h16M7.5 17a4.5 4.5 0 0 1 9 0M12 7.5v2M5.3 10.3l1.4 1.4M18.7 10.3l-1.4 1.4"/>',
  talk: '<path d="M4 12a8 7 0 1 1 4 6l-4 1.5 1.3-3.5A7 7 0 0 1 4 12z"/>',
  hand: '<path d="M8 12V6a1.5 1.5 0 0 1 3 0v5M11 11V4.5a1.5 1.5 0 0 1 3 0V11M14 11V6a1.5 1.5 0 0 1 3 0v8a6 6 0 0 1-6 6h-.5a6 6 0 0 1-5-2.7L3.5 14a1.5 1.5 0 0 1 2.4-1.8L8 14.5"/>',
};
const glyph = (k, x, y, s, col, w = 2) => `<svg x="${x - s / 2}" y="${y - s / 2}" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${col}" stroke-width="${(w * 24 / s).toFixed(2)}" stroke-linecap="round" stroke-linejoin="round">${G[k]}</svg>`;
function screen(id, title, body) {
  return `<figure><div class="scr" id="${id}"><svg viewBox="0 0 466 466" width="466" height="466">${defs}${body}</svg></div><figcaption>${title}</figcaption></figure>`;
}
