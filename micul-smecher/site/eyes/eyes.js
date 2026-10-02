/*! SOUL eyes engine v2.1 — flat graphic eyes for SOUL's round glass.
 *
 *   const eyes = SoulEyes.createEyes(canvas, design, opts)
 *   eyes.setExpression('happy')   // a mood (holds) or a reaction (plays once, then returns)
 *   eyes.react('laugh')           // one-shot, returns to the current mood
 *   eyes.lookAt(x, y)             // -1..1 each; lookAt(null) = back to idle glances
 *   eyes.blink(2)                 // 1 or 2 (double blink)
 *   eyes.setDesign(design)        // swaps while the eyes are shut
 *   eyes.destroy()
 *
 * Vector only (canvas 2D fills), no blur. Deterministic: the rig only advances
 * through step(dt) and seeded RNGs. See README.md for the full API and the
 * design spec. Works as a classic <script> (window.SoulEyes) and in Node.
 */
(function (root, factory) {
  const E = factory();
  if (typeof module === 'object' && module.exports) module.exports = E;
  else root.SoulEyes = E;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const VERSION = '2.1.0';
  const TAU = Math.PI * 2, PI = Math.PI;

  // ------------------------------------------------------------ utils
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
  const inQuad = (t) => t * t;
  const outBack = (t, s = 2.2) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2);
  function mix32(x) { x >>>= 0; x = Math.imul(x ^ (x >>> 16), 0x7feb352d); x = Math.imul(x ^ (x >>> 15), 0x846ca68b); return (x ^ (x >>> 16)) >>> 0; }
  const h01 = (i) => mix32(i * 2654435761 + 12345) / 4294967296;
  function hashStr(s) { let h = 2166136261 >>> 0; s = String(s); for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; }
  function rng(seed) { let a = seed >>> 0 || 1; return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function hex2rgb(h) { h = String(h).replace('#', ''); if (h.length === 3) h = h.split('').map((c) => c + c).join(''); const n = parseInt(h.slice(0, 6), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  const rgba = (c, a) => { const [r, g, b] = hex2rgb(c); return 'rgba(' + r + ',' + g + ',' + b + ',' + clamp(a, 0, 1).toFixed(3) + ')'; };
  function mixHex(a, b, t) { const A = hex2rgb(a), B = hex2rgb(b); t = clamp(t, 0, 1); return '#' + A.map((v, i) => ('0' + Math.round(clamp(lerp(v, B[i], t), 0, 255)).toString(16)).slice(-2)).join(''); }
  const hsl = (h, s, l) => 'hsl(' + (((h % 360) + 360) % 360).toFixed(1) + ',' + s + '%,' + l + '%)';
  const clone = (o) => JSON.parse(JSON.stringify(o));
  function merge(a, b) {
    if (b === undefined) return clone(a);
    if (b === null || typeof b !== 'object' || Array.isArray(b)) return clone(b);
    const o = a && typeof a === 'object' && !Array.isArray(a) ? clone(a) : {};
    for (const k of Object.keys(b)) o[k] = merge(o[k], b[k]);
    return o;
  }

  // ------------------------------------------------------------ the design spec
  // All sizes are fractions of the screen diameter (shape) or of the eye radii (pupil).
  const DEFAULT_DESIGN = {
    id: 'soul-original', n: 0, name: 'Original', rarity: 'common', family: 'egg',
    shape: { type: 'egg', rx: 0.163, ry: 0.2, spacing: 0.19, y: 0.005, egg: 0.09, lean: 0.13 },
    white: '#FFF0C8',                       // the eye colour; whiteR = a different right eye
    pupil: { type: 'round', L: '#2440FF', R: '#FF5A1F', rx: 0.42, ry: 0.5, inset: 0.16, travel: 0.5 },
    glint: { color: '#FFF6E2', size: 1 },   // the pebble glint; null = none
    fx: [],                                 // shimmer | rainbow | chrome | aurora | starfield | folk | glitter | outline | galaxy
  };
  function normalizeDesign(d) { return merge(DEFAULT_DESIGN, d || {}); }

  // ------------------------------------------------------------ springs
  class Spring {
    constructor(v, k, z) { this.x = v; this.t = v; this.v = 0; this.k = k; this.z = z; }
    step(dt) { const c = 2 * Math.sqrt(this.k) * this.z; this.v += (-this.k * (this.x - this.t) - c * this.v) * dt; this.x += this.v * dt; }
  }
  const EYE_KEYS = ['lid', 'tilt', 'smile', 'size', 'pupil', 'alt', 'squeeze'];
  const BASE = {
    scale: 1, sx: 1, sy: 1, bob: 0, shift: 0, lift: 0, rot: 0, shake: 0, bounce: 0,
    blush: 0, tears: 0, cry: 0, q: 0, dots: 0, zzz: 0, spark: 0, check: 0, hearts: 0, bang: 0, spray: 0, listen: 0, bolt: 0,
    lidL: 0, lidR: 0, tiltL: 0.06, tiltR: 0.06, smileL: 0, smileR: 0, sizeL: 1, sizeR: 1,
    pupilL: 1, pupilR: 1, altL: 0, altR: 0, squeezeL: 0, squeezeR: 0,
  };
  function springFor(k) {
    if (/^alt/.test(k)) return [300, 0.34];
    if (/^squeeze/.test(k)) return [380, 0.4];
    if (/^(lid|tilt|smile)/.test(k)) return [420, 0.62];
    if (/^(scale|sx|sy|size)/.test(k)) return [300, 0.36];
    if (k === 'bob' || k === 'lift') return [220, 0.42];
    if (/^pupil/.test(k)) return [420, 0.5];
    if (k === 'shift' || k === 'rot') return [240, 0.5];
    if (k === 'shake' || k === 'bounce') return [60, 1];
    return [200, 0.7];
  }
  // expand {lid:.3} -> {lidL:.3, lidR:.3}; arrays [L,R] allowed
  function expand(set) {
    const o = {};
    for (const k in set) {
      const v = set[k];
      if (EYE_KEYS.indexOf(k) >= 0) { o[k + 'L'] = Array.isArray(v) ? v[0] : v; o[k + 'R'] = Array.isArray(v) ? v[1] : v; }
      else o[k] = v;
    }
    return o;
  }

  // ------------------------------------------------------------ moods & reactions
  // mood: holds until changed. reaction: plays its keys over `dur` seconds, then returns.
  // key fields: t, set (targets), kick (velocity), snap (jump now), gaze, mode (gaze mode),
  //             alt (alternate pupil type), blink, shakeF (Hz)
  const MOODS = {
    neutral: { label: 'Idle', set: {} },
    happy: { label: 'Happy', set: { smile: 0.8, lid: 0, tilt: 0, scale: 1.05, bob: 0.012, pupil: 0 }, antic: { d: 0.09, set: { sy: 0.88, bob: 0.012, scale: 0.98 } }, kick: { bob: -0.5, sy: 2.4 }, gaze: [0, -0.3] },
    surprised: { label: 'Surprised', set: { lid: 0, tilt: 0, scale: 1.12, sy: 1.07, pupil: 0.42, bob: -0.02 }, antic: { d: 0.1, set: { sy: 0.86, scale: 0.94, bob: 0.014 } }, kick: { scale: 3, sy: 2.2 }, blink: 1 },
    sleepy: { label: 'Sleepy', set: { lid: [0.56, 0.6], tilt: -0.12, scale: 0.97, bob: 0.022, zzz: 1, pupil: 0.95 }, gaze: [0, 0.45], mode: 'still', blinkSlow: 3, blinkEvery: 4.5 },
    love: { label: 'Love', set: { alt: 1, pupil: 0, lid: 0, tilt: 0, hearts: 1, scale: 1.03 }, alt: 'heart', antic: { d: 0.12, set: { pupil: 0, scale: 0.96 } }, kick: { altL: 5, altR: 5 }, mode: 'still' },
    smirk: { label: 'Șmecher', set: { lid: [0.3, 0], tilt: [0.3, 0], smile: [0.36, 0], shift: 0.03, size: [1, 1.06], pupil: 0.9 }, gaze: [0.82, 0.04], antic: { d: 0.1, set: { shift: -0.012 }, gaze: [-0.35, 0] }, kick: { shift: 0.4 }, mode: 'still' },
    sad: { label: 'Sad', set: { lid: 0.24, tilt: -0.34, pupil: 1.12, sy: 0.95, bob: 0.024, tears: 1 }, gaze: [0, 0.4], mode: 'wobble', blinkSlow: 1.6 },
    cry: { label: 'Cry', set: { lid: 0.36, tilt: -0.4, pupil: 1.05, sy: 0.92, bob: 0.03, cry: 1, smile: 0.12 }, gaze: [0, 0.35], mode: 'wobble', antic: { d: 0.12, set: { sy: 1.04 } }, kick: { bob: 0.3 } },
    angry: { label: 'Angry', set: { lid: 0.32, tilt: 0.5, pupil: 0.66, sx: 1.04, sy: 0.94, shake: 0.004, bob: 0.008 }, antic: { d: 0.08, set: { sy: 1.05, lid: 0 } }, kick: { sx: 2 }, shakeF: 24, mode: 'still' },
    dizzy: { label: 'Dizzy', set: { alt: 1, pupil: 0, rot: 0 }, alt: 'spiral', mode: 'spin', keys: [{ t: 0, kick: { rot: 1.2 } }] },
    suspicious: { label: 'Suspicious', set: { lid: 0.4, tilt: 0.12, smile: 0.24, pupil: 0.82 }, mode: 'sway' },
    smug: { label: 'Smug', set: { lid: 0.46, tilt: -0.06, smile: 0.14, rot: -0.07, lift: -0.028, pupil: 0.9 }, gaze: [0.12, -0.12], mode: 'still', antic: { d: 0.1, set: { lift: 0.01 } } },
    shy: { label: 'Shy', set: { lid: 0.16, tilt: -0.14, size: 0.95, blush: 1, rot: 0.05, shift: -0.02 }, gaze: [-0.65, 0.6], mode: 'still', blinkEvery: 1.6 },
    excited: { label: 'Excited', set: { alt: 1, pupil: 0, bounce: 1, spark: 1, scale: 1.06, lid: 0, tilt: 0 }, alt: 'star', antic: { d: 0.1, set: { sy: 0.86 } }, kick: { altL: 4, altR: 4, sy: 2 }, mode: 'still' },
    thinking: { label: 'Thinking', set: { lid: [0.14, 0.32], tilt: [0.04, -0.12], dots: 1, pupil: 0.92 }, gaze: [0.6, -0.58], mode: 'drift' },
    listening: { label: 'Listening', set: { scale: 1.05, lid: 0, tilt: 0, listen: 1 }, gaze: [0, 0], mode: 'still' },
    confused: { label: 'Confused', set: { size: [0.88, 1.12], rot: 0.11, q: 1, lid: [0.22, 0], tilt: [0.22, -0.1] }, gaze: [0.2, -0.3], mode: 'still', kick: { rot: 1 } },
    bored: { label: 'Bored', set: { lid: 0.5, tilt: 0, pupil: 0.8, sy: 0.96, bob: 0.01 }, gaze: [-0.35, 0.22], mode: 'still', blinkSlow: 2.6, blinkEvery: 3 },
    plan: { label: 'Evil plan', set: { pupil: 0.78, smile: 0.2 }, gaze: [-0.8, 0.12], mode: 'still', keys: [{ t: 0.2, set: { lid: 0.18, tilt: 0.2 } }, { t: 0.8, set: { lid: 0.32, tilt: 0.36 } }, { t: 1.5, set: { lid: 0.42, tilt: 0.46, smile: 0.32 } }] },
    working: { label: 'Claude is working', set: { pupil: 0.78, lid: 0.12, tilt: 0 }, mode: 'scan' },
    hungry: { label: 'Low battery', set: { alt: 1, pupil: 0, sy: 0.9, lid: 0.3, tilt: -0.16, bob: 0.03 }, alt: 'battery', mode: 'still', blinkSlow: 2 },
    charging: { label: 'Charging', set: { alt: 1, pupil: 0, bolt: 1 }, alt: 'level', mode: 'still', kick: { altL: 3, altR: 3 } },
  };
  const REACTIONS = {
    laugh: { label: 'Laugh', dur: 1.9, keys: [{ t: 0, set: { sy: 0.86 } }, { t: 0.08, set: { smile: 0.86, pupil: 0, lid: 0, tilt: 0, sy: 1, bounce: 1, shake: 0.004 }, kick: { sy: 2.5 }, shakeF: 9 }, { t: 1.45, set: { bounce: 0, shake: 0 } }] },
    wink: { label: 'Wink', dur: 1.05, keys: [{ t: 0, set: { sy: 0.94 } }, { t: 0.07, set: { sy: 1, smile: [0.98, 0.26], lid: [0, 0.06], pupil: [0, 1], shift: 0.012, rot: -0.04 }, kick: { bob: -0.3 } }, { t: 0.8, set: { smile: 0, shift: 0, rot: 0, pupil: 1 } }] },
    shocked: { label: 'Shocked', dur: 1.5, keys: [{ t: 0, set: { sy: 0.8, scale: 0.95 } }, { t: 0.07, set: { sy: 1.1, scale: 1.18, pupil: 0.2, lid: 0, tilt: 0, lift: -0.03, shake: 0.004, bang: 1 }, kick: { scale: 4, lift: -0.6 }, shakeF: 30, mode: 'still', gaze: [0, 0] }, { t: 1.05, set: { shake: 0, bang: 0 } }] },
    sneeze: { label: 'Sneeze', dur: 1.9, keys: [{ t: 0, set: { sy: 1.06, lift: -0.012, lid: 0, tilt: 0, pupil: 0.9 }, gaze: [0, -0.55], mode: 'still' }, { t: 0.32, set: { sy: 1.12, lift: -0.022, smile: 0.2 } }, { t: 0.62, set: { squeeze: 1, smile: 0, sy: 0.9, lift: 0.01 } }, { t: 0.8, set: { lift: 0, sy: 1, spray: 1, shake: 0.016 }, kick: { scale: 3.5, lift: 0.5 }, shakeF: 14 }, { t: 1.2, set: { squeeze: 0, shake: 0, spray: 0, pupil: 1 }, gaze: [0, 0], mode: 'idle', blink: 2 }] },
    startled: { label: 'Shaken', dur: 2.0, keys: [{ t: 0, set: { shake: 0.03, pupil: 0.45, scale: 1.1, lid: 0, tilt: 0, bang: 1 }, kick: { scale: 3 }, shakeF: 17, mode: 'rattle' }, { t: 0.65, set: { shake: 0, bang: 0, alt: 1, pupil: 0 }, alt: 'spiral', mode: 'spin' }, { t: 1.35, set: { alt: 0, pupil: 1, scale: 1 }, mode: 'idle', gaze: [0, 0], blink: 2 }] },
    approve: { label: 'Approve', dur: 1.7, keys: [{ t: 0, set: { sy: 0.9 } }, { t: 0.08, set: { sy: 1, smile: 0.42, pupil: 0.6, lid: 0, tilt: 0, check: 1 }, kick: { scale: 2.6, bob: -0.3 } }, { t: 1.35, set: { check: 0 } }] },
    hello: { label: 'Hello', dur: 1.6, keys: [{ t: 0, snap: { scale: 0.05, lid: 0.97 }, set: { scale: 0.05, lid: 0.97 } }, { t: 0.12, set: { scale: 1, lid: 0, tilt: 0 }, kick: { scale: 3, sy: 2.5 } }, { t: 0.75, blink: 2 }, { t: 0.95, set: { smile: 0.3 } }, { t: 1.35, set: { smile: 0 } }] },
    goodbye: { label: 'Goodbye', dur: 2.6, keys: [{ t: 0, set: { smile: 0.3 } }, { t: 0.5, set: { smile: 0, scale: 0.32, sy: 0.8, pupil: 0, lid: 0, tilt: 0 } }, { t: 1.05, set: { scale: 0, sy: 0.2 } }, { t: 1.9, snap: { scale: 0.05, lid: 0.97 }, set: { scale: 0.05, sy: 1 } }, { t: 2.0, set: { scale: 1, lid: 0, pupil: 1 }, kick: { scale: 3 } }] },
    wake: { label: 'Wake up', dur: 2.3, keys: [{ t: 0, snap: { lid: 0.95, lidL: 0.95, lidR: 0.95 }, set: { lid: 0.95, tilt: -0.1, bob: 0.03 }, gaze: [0, 0.4], mode: 'still' }, { t: 0.35, set: { lid: 0, tilt: 0, sy: 1.26, sx: 0.88, lift: -0.035, bob: 0 } }, { t: 0.85, set: { sy: 1, sx: 1, lift: 0 }, kick: { sy: -2 } }, { t: 1.05, blink: 2, gaze: [0, 0], mode: 'idle' }, { t: 1.6, set: { smile: 0.25 } }, { t: 2.0, set: { smile: 0 } }] },
  };
  const EXPRESSIONS = Object.keys(MOODS).map((k) => ({ name: k, label: MOODS[k].label, kind: 'mood' }))
    .concat(Object.keys(REACTIONS).map((k) => ({ name: k, label: REACTIONS[k].label, kind: 'reaction' })));

  // the 15 s demo performance (opts.mode = 'loop')
  const LOOP = 15;
  const SCRIPT = [
    { t: 0, mood: 'neutral', look: [0, 0] }, { t: 0.55, look: [-0.75, -0.1] }, { t: 1.15, look: [0.7, 0.2], blink: 1 },
    { t: 1.9, look: [0.05, -0.05] }, { t: 2.25, hop: 1 }, { t: 2.6, blink: 2 }, { t: 3.1, mood: 'happy' }, { t: 4.7, mood: 'neutral' },
    { t: 4.85, look: [-0.5, 0.35] }, { t: 5.35, look: [0, 0] }, { t: 5.6, mood: 'surprised' }, { t: 7.0, mood: 'neutral', blink: 1 },
    { t: 7.45, mood: 'smirk' }, { t: 8.7, blink: 1 }, { t: 9.35, mood: 'neutral' }, { t: 9.6, mood: 'love' }, { t: 11.45, mood: 'neutral', blink: 1 },
    { t: 11.8, mood: 'sleepy' }, { t: 12.9, blink: 1, slow: 3 }, { t: 14.2, mood: 'neutral', look: [0, 0] }, { t: 14.35, blink: 2 },
  ];
  const SEGMENTS = [['Idle', 0, 3.1], ['Happy', 3.1, 4.7], ['Look', 4.7, 5.6], ['Surprised', 5.6, 7.0], ['Șmecher', 7.0, 9.4], ['Love', 9.4, 11.6], ['Sleepy', 11.6, 14.2], ['', 14.2, 15]];
  const RANDOM_POOL = ['happy', 'laugh', 'wink', 'surprised', 'smirk', 'love', 'thinking', 'suspicious', 'smug', 'shy', 'excited', 'confused', 'approve', 'shocked', 'sneeze', 'bored', 'plan', 'sad', 'angry', 'dizzy', 'working', 'listening'];

  // ------------------------------------------------------------ rig
  class Rig {
    constructor(seed, mode) {
      this.seed = (seed >>> 0) || 7; this.r = rng(this.seed);
      this.t = 0; this.lt = 0; this.mode = mode || 'live';
      this.mood = 'neutral'; this.moodT = 0; this.reaction = null; this.pending = null;
      this.s = {};
      for (const k in BASE) { const [kk, z] = springFor(k); this.s[k] = new Spring(BASE[k], kk, z); }
      this.pL = [new Spring(0, 900, 0.52), new Spring(0, 900, 0.52)];
      this.pR = [new Spring(0, 760, 0.46), new Spring(0, 760, 0.46)];
      this.eyeG = [new Spring(0, 140, 0.75), new Spring(0, 140, 0.75)];
      this.gq = []; this.gazeT = [0, 0]; this.base = [0, 0]; this.look = null; this.gmode = 'idle';
      this.altType = 'heart'; this.shakeF = 20;
      this.blinkAt = -10; this.blinkN = 1; this.blinkSlow = 1; this.blinkEvery = 2; this.moodBlinkSlow = 1;
      this.nextMicro = 0.4; this.nextGlance = 1.5; this.glanceUntil = -1; this.nextBlink = 1.8 + this.r() * 1.5; this.nextHop = 4 + this.r() * 4;
      this.level = 0; this.levelExt = null; this.charge = 0;
      this.randomMood = false; this.nextRandom = 3 + this.r() * 4;
      this.keysDone = 0; this.moodKeysDone = 0;
      this.onChange = null;
    }
    _targets(set) { const e = expand(set); for (const k in e) if (this.s[k]) this.s[k].t = e[k]; }
    _kick(kick) { const e = expand(kick || {}); for (const k in e) if (this.s[k]) this.s[k].v += e[k]; }
    _snap(set) { const e = expand(set || {}); for (const k in e) if (this.s[k]) { this.s[k].x = e[k]; this.s[k].t = e[k]; this.s[k].v = 0; } }
    _applyKey(k) {
      if (k.snap) this._snap(k.snap);
      if (k.set) this._targets(k.set);
      if (k.kick) this._kick(k.kick);
      if (k.alt) this.altType = k.alt;
      if (k.gaze) this.base = k.gaze.slice();
      if (k.mode) this.gmode = k.mode;
      if (k.shakeF) this.shakeF = k.shakeF;
      if (k.blink) this.blink(k.blink);
    }
    // a mood holds; a reaction plays and then falls back to the mood
    setExpression(name) {
      if (REACTIONS[name]) return this.react(name);
      if (!MOODS[name]) name = 'neutral';
      const m = MOODS[name], changed = name !== this.mood || this.reaction;
      this.reaction = null;
      this.mood = name; this.moodT = 0; this.moodKeysDone = 0;
      const go = () => {
        this._targets(Object.assign({}, BASE, m.set));
        if (changed && m.kick) this._kick(m.kick);
        this.base = (m.gaze || [0, 0]).slice();
        this.gmode = m.mode || 'idle';
        if (m.alt) this.altType = m.alt;
        this.shakeF = m.shakeF || 20;
        this.moodBlinkSlow = m.blinkSlow || 1; this.blinkEvery = m.blinkEvery || 2;
        this.pending = null;
      };
      if (changed && m.antic) { this._targets(m.antic.set); if (m.antic.gaze) this.base = m.antic.gaze.slice(); this.pending = { at: this.t + m.antic.d, fn: go }; }
      else go();
      if (changed && m.blink) this.blink(m.blink);
      if (this.onChange) this.onChange(name);
    }
    react(name, hold) {
      if (MOODS[name]) { // a mood as a one-shot: hold it, then go back
        const back = this.mood === name ? 'neutral' : this.mood;
        this.setExpression(name);
        this.reaction = { name, t0: this.t, dur: hold || 2.4, keys: [], back };
        return;
      }
      const r = REACTIONS[name]; if (!r) return;
      this.pending = null;
      this._targets(Object.assign({}, BASE, (MOODS[this.mood] || {}).set || {}));
      this.reaction = { name, t0: this.t, dur: hold || r.dur, keys: r.keys, done: 0, back: this.mood };
      if (this.onChange) this.onChange(name);
    }
    hop() { this.s.bob.v -= 0.55; this.s.sy.v += 2.2; this.s.sx.v -= 1.2; }
    blink(n, slow) { this.blinkAt = this.t; this.blinkN = n || 1; this.blinkSlow = slow || this.moodBlinkSlow || 1; }
    closed() {
      const k = this.blinkSlow, c = 0.08 * k, h = 0.04 * k, o = 0.17 * k, q0 = this.t - this.blinkAt;
      const one = (q) => (q < 0 ? 0 : q < c ? inQuad(q / c) : q < c + h ? 1 : q < c + h + o ? 1 - outBack((q - c - h) / o, 1.8) : 0);
      let v = one(q0);
      if (this.blinkN > 1) { const v2 = one(q0 - (c + h + o * 0.7)); v = Math.abs(v2) > Math.abs(v) ? v2 : v; }
      return v;
    }
    update(dt) { const n = Math.max(1, Math.ceil(dt / (1 / 240))); for (let i = 0; i < n; i++) this.step(dt / n); }
    step(dt) {
      const prev = this.lt; this.t += dt; this.moodT += dt;
      const t = this.t, r = this.r;
      if (this.pending && t >= this.pending.at) this.pending.fn();
      // mood timelines
      const mk = (MOODS[this.mood] || {}).keys;
      if (mk && !this.reaction) while (this.moodKeysDone < mk.length && mk[this.moodKeysDone].t <= this.moodT) this._applyKey(mk[this.moodKeysDone++]);
      // reaction timeline
      const R = this.reaction;
      if (R) {
        const q = t - R.t0;
        while (R.done < R.keys.length && R.keys[R.done].t <= q) this._applyKey(R.keys[R.done++]);
        if (q >= R.dur) { this.reaction = null; const back = R.back; this.mood = '__'; this.setExpression(back); }
      }
      if (this.mode === 'loop') {
        this.lt = (this.lt + dt) % LOOP;
        const wrapped = this.lt < prev;
        for (const e of SCRIPT) {
          const hit = wrapped ? e.t > prev || e.t <= this.lt : e.t > prev && e.t <= this.lt;
          if (!hit) continue;
          if (e.mood) this.setExpression(e.mood);
          if (e.look) this.base = e.look.slice();
          if (e.blink) this.blink(e.blink, e.slow);
          if (e.hop) this.hop();
        }
        const slot = Math.floor(this.lt / 0.55);
        const quiet = this.lt > 14.1 || this.lt < 0.3 || ['sleepy', 'love', 'smirk'].indexOf(this.mood) >= 0;
        const m = quiet ? [0, 0] : [(h01(slot * 2 + 1) - 0.5) * 0.16, (h01(slot * 2 + 2) - 0.5) * 0.1];
        this.gazeT = this.look ? this.look.slice() : [this.base[0] + m[0], this.base[1] + m[1]];
      } else {
        if (this.randomMood && !this.reaction && t > this.nextRandom) {
          const pool = this.moodPool || RANDOM_POOL, ev = this.moodEvery || [3.2, 6.7];
          const pick = pool[Math.floor(r() * pool.length)];
          this.react(pick, MOODS[pick] ? 2.2 + r() * 1.5 : null);
          this.nextRandom = t + ev[0] + r() * (ev[1] - ev[0]);
        }
        this._gaze(dt);
        if (t > this.nextBlink) {
          if (this.s.smileL.x < 0.4 && this.s.altL.x < 0.5 && this.s.squeezeL.x < 0.3 && this.s.scale.x > 0.5) this.blink(r() < 0.22 ? 2 : 1, this.moodBlinkSlow);
          this.nextBlink = t + this.blinkEvery + r() * 3.6;
        }
        if (t > this.nextHop) { if (this.mood === 'neutral' && !this.reaction && r() < 0.6) this.hop(); this.nextHop = t + 3.5 + r() * 5; }
      }
      // levels: listening (voice-ish), charging (fills up)
      this.level = this.levelExt != null ? this.levelExt : clamp(0.45 + 0.3 * Math.sin(t * 7.1) * Math.sin(t * 2.3 + 1) + 0.25 * Math.sin(t * 13.7 + Math.sin(t * 3)), 0, 1);
      this.charge = this.levelExt != null ? this.levelExt : (this.moodT * 0.28) % 1.25;
      // gaze springs: the right pupil follows 45 ms later
      this.gq.push([t, this.gazeT[0], this.gazeT[1]]);
      while (this.gq.length > 2 && this.gq[1][0] <= t - 0.045) this.gq.shift();
      const late = this.gq[0];
      this.pL[0].t = this.gazeT[0]; this.pL[1].t = this.gazeT[1]; this.pR[0].t = late[1]; this.pR[1].t = late[2];
      this.eyeG[0].t = this.gazeT[0]; this.eyeG[1].t = this.gazeT[1];
      for (let i = 0; i < 2; i++) { this.pL[i].step(dt); this.pR[i].step(dt); this.eyeG[i].step(dt); }
      for (const k in this.s) this.s[k].step(dt);
    }
    _gaze() {
      const t = this.t, r = this.r, b = this.base;
      if (this.look) { this.gazeT = this.look.slice(); return; }
      switch (this.gmode) {
        case 'still': this.gazeT = b.slice(); return;
        case 'spin': this.gazeT = [Math.cos(t * 6.5) * 0.62, Math.sin(t * 6.5) * 0.48]; return;
        case 'rattle': this.gazeT = [(h01(Math.floor(t * 14)) - 0.5) * 1.4, (h01(Math.floor(t * 14) + 99) - 0.5) * 1.0]; return;
        case 'sway': this.gazeT = [Math.sin(t * 1.15) * 0.72, 0.06]; return;
        case 'drift': this.gazeT = [b[0] + Math.sin(t * 0.9) * 0.12, b[1] + Math.sin(t * 1.3) * 0.06]; return;
        case 'wobble': this.gazeT = [b[0] + Math.sin(t * 9) * 0.03, b[1]]; return;
        case 'scan': { // reading: hop along a line in small saccades, snap back, next line
          const line = 1.25, q = (t % (line * 3)) / line, li = Math.floor(q), f = q - li;
          const x = f < 0.85 ? -0.6 + Math.floor(f / 0.85 * 6) / 5 * 1.2 : -0.6;
          this.gazeT = [x, -0.25 + li * 0.22]; return;
        }
      }
      if (t > this.nextGlance) { this.gazeT = [b[0] + (r() * 2 - 1) * 0.8, b[1] + (r() * 2 - 1) * 0.5]; this.glanceUntil = t + 0.6 + r() * 1.3; this.nextGlance = t + 2 + r() * 3.5; if (r() < 0.3) this.blink(1); }
      else if (this.glanceUntil > 0 && t > this.glanceUntil) { this.gazeT = b.slice(); this.glanceUntil = -1; }
      else if (t > this.nextMicro) { const g = this.glanceUntil > 0 ? this.gazeT : b; this.gazeT = [g[0] + (r() * 2 - 1) * 0.09, g[1] + (r() * 2 - 1) * 0.06]; this.nextMicro = t + 0.3 + r() * 1.1; }
      else if (this.glanceUntil < 0 && Math.hypot(this.gazeT[0] - b[0], this.gazeT[1] - b[1]) > 0.25) this.gazeT = b.slice();
    }
  }

  // ------------------------------------------------------------ drawing
  function drawGlass(ctx, cx, cy, D, opt) {
    const R = D / 2;
    if (opt.bezel !== false) {
      const bw = D * 0.03;
      const g = ctx.createLinearGradient(cx - R, cy - R - bw, cx + R, cy + R + bw);
      g.addColorStop(0, '#EEEDEA'); g.addColorStop(0.3, '#9E9DA0'); g.addColorStop(0.56, '#DAD9D6'); g.addColorStop(1, '#6B6A6E');
      ctx.beginPath(); ctx.arc(cx, cy, R + bw, 0, TAU); ctx.fillStyle = g; ctx.fill();
      ctx.beginPath(); ctx.arc(cx, cy, R + bw * 0.2, 0, TAU); ctx.fillStyle = '#161618'; ctx.fill();
    }
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.fillStyle = '#000'; ctx.fill();
  }
  function drawSheen(ctx, cx, cy, D) {
    const R = D / 2; ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.clip();
    const g = ctx.createLinearGradient(cx - R, cy - R, cx + R * 0.3, cy + R * 0.3);
    g.addColorStop(0, 'rgba(255,255,255,.085)'); g.addColorStop(0.55, 'rgba(255,255,255,.01)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.beginPath(); ctx.ellipse(cx - R * 0.22, cy - R * 0.36, R * 0.92, R * 0.55, -0.55, 0, TAU); ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = Math.max(1, D * 0.004); ctx.strokeStyle = 'rgba(255,255,255,.09)';
    ctx.beginPath(); ctx.arc(cx, cy, R - ctx.lineWidth * 1.5, PI * 1.08, PI * 1.48); ctx.stroke(); ctx.restore();
  }
  function heartPath(ctx, x, y, s, rot) {
    ctx.beginPath(); const c = Math.cos(rot || 0), sn = Math.sin(rot || 0);
    for (let i = 0; i <= 72; i++) {
      const a = (i / 72) * TAU, si = Math.sin(a);
      const hx = ((16 * si * si * si) / 16.5) * s, hy = ((-(13 * Math.cos(a) - 5 * Math.cos(2 * a) - 2 * Math.cos(3 * a) - Math.cos(4 * a)) + 2.5) / 15) * s;
      const px = x + hx * c - hy * sn, py = y + hx * sn + hy * c; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.closePath();
  }
  function superPath(ctx, x, y, rx, ry, rot, n) { // SOUL's pebble silhouette
    ctx.beginPath(); const c = Math.cos(rot), s = Math.sin(rot);
    for (let i = 0; i < 40; i++) {
      const a = (i / 40) * TAU, ca = Math.cos(a), sa = Math.sin(a);
      const ux = Math.sign(ca) * Math.pow(Math.abs(ca), 2 / n) * rx, uy = Math.sign(sa) * Math.pow(Math.abs(sa), 2 / n) * ry;
      const px = x + ux * c - uy * s, py = y + ux * s + uy * c; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.closePath();
  }
  function starPath(ctx, x, y, r, n, inner, rot) {
    ctx.beginPath();
    for (let i = 0; i < n * 2; i++) { const a = rot - PI / 2 + (i / (n * 2)) * TAU, rr = i % 2 ? r * inner : r; i ? ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr) : ctx.moveTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
    ctx.closePath();
  }
  function sparkPath(ctx, x, y, r, rot) { starPath(ctx, x, y, r, 4, 0.3, rot); }
  function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x, y, w, h, r); else ctx.rect(x, y, w, h); }

  function eyeFrame(rig, d, side, cx, cy, D) {
    const s = rig.s, E = d.shape;
    const ex0 = rig.eyeG[0].x, ey0 = rig.eyeG[1].x;
    const b = rig.closed();
    const breath = Math.sin((rig.t * TAU) / 3.6 + side * 0.4);
    const par = 1 - 0.07 * ex0 * side;
    const sq = clamp(side < 0 ? s.squeezeL.x : s.squeezeR.x, 0, 1.2);
    const k = Math.max(0, s.scale.x) * par * (side < 0 ? s.sizeL.x : s.sizeR.x);
    const rx = E.rx * D * k * s.sx.x * (1 + 0.06 * Math.max(0, b)) * (1 + 0.006 * breath) * (1 - 0.5 * sq);
    const ry = E.ry * D * k * s.sy.x * (1 - 0.12 * b) * (1 + 0.012 * breath) * Math.max(0, 1 - sq);
    const x = cx + (side * E.spacing + ex0 * 0.028 + s.shift.x) * D;
    const y = cy + (E.y + ey0 * 0.022 + s.bob.x + s.lift.x + 0.016 * Math.max(0, b) + 0.002 * breath) * D;
    return { x, y, rx, ry, b, side, sq, k };
  }

  function silhouette(rig, d, g, D) {
    const s = rig.s, E = d.shape, side = g.side, L = side < 0;
    const { rx, ry, b } = g;
    const lean = -side * (E.lean || 0), cl = Math.cos(lean), sl = Math.sin(lean);
    const lid0 = clamp(L ? s.lidL.x : s.lidR.x, 0, 0.98), tilt = L ? s.tiltL.x : s.tiltR.x;
    const bb = clamp(b, 0, 1);
    const lid = lid0 + (1 - lid0) * bb;
    const kT = Math.tan(tilt) * -side * (1 - bb);
    const thick = 0.024 * D * Math.max(0.35, g.k);
    const bow = 0.1 * ry * Math.min(1, lid0 * 4) * (1 - bb);
    const lidY = (x) => -ry + lid * (2 * ry - thick) + kT * x + bow * (1 - Math.min(1, (x / rx) * (x / rx)));
    const smile = clamp(L ? s.smileL.x : s.smileR.x, 0, 1);
    const cutCy = ry * (2.2 - 1.78 * smile), cutA = rx * 1.42, cutB = ry * 1.1;
    const type = E.type || 'egg', egg = E.egg || 0;
    const pts = [], N = 120;
    for (let i = 0; i < N; i++) {
      const a = (i / N) * TAU, ca = Math.cos(a), sa = Math.sin(a);
      let ux, uy;
      switch (type) {
        case 'squircle': { const n = E.n || 3.4; ux = Math.sign(ca) * Math.pow(Math.abs(ca), 2 / n) * rx; uy = Math.sign(sa) * Math.pow(Math.abs(sa), 2 / n) * ry; break; }
        case 'almond': { ux = ca * rx; uy = sa * Math.pow(Math.abs(sa), E.q == null ? 0.5 : E.q) * ry; uy -= (E.flick || 0.18) * ry * Math.max(0, -ca * side) * (ca * side < 0 ? 1 : 0) * Math.abs(ca); break; }
        case 'drop': { const tip = Math.max(0, -sa); ux = ca * rx * (1 - 0.55 * Math.pow(tip, 1.6)); uy = sa * ry * (sa < 0 ? 1.12 : 0.92) + ry * 0.06; break; }
        case 'crescent': { ux = ca * rx; uy = sa * ry; const dip = -ry + (E.dip || 0.5) * ry * 2 * (1 - (ux / rx) * (ux / rx)); if (uy < dip) uy = dip; break; }
        default: ux = ca * rx * (1 - egg * Math.max(0, -sa)); uy = sa * ry;
      }
      let x = ux * cl - uy * sl, y = ux * sl + uy * cl;
      if (lid > 0.003) y = Math.max(y, lidY(x));
      if (smile > 0.003) { const q = 1 - (x / cutA) * (x / cutA); if (q > 0) y = Math.min(y, cutCy - cutB * Math.sqrt(q)); }
      pts.push([x, y]);
    }
    return pts;
  }

  // flat FX on the whites
  function whiteFill(ctx, d, side, g, t, gx) {
    const fx = d.fx || [];
    let col = side > 0 && d.whiteR ? d.whiteR : d.white;
    if (fx.indexOf('rainbow') >= 0) return hsl(t * 40 + side * 30 + (d.hue || 0), 95, 66);
    if (fx.indexOf('chrome') >= 0) {
      const gr = ctx.createLinearGradient(-g.rx - gx * g.rx * 0.8, -g.ry, g.rx - gx * g.rx * 0.8, g.ry);
      const c = hex2rgb(col);
      const tone = (k) => rgba(mixHex(col, k > 0 ? '#FFFFFF' : '#2A2C33', Math.abs(k)), 1);
      gr.addColorStop(0, tone(0.7)); gr.addColorStop(0.38, tone(-0.35)); gr.addColorStop(0.52, tone(0.85)); gr.addColorStop(0.66, tone(-0.55)); gr.addColorStop(1, tone(0.4)); void c;
      return gr;
    }
    if (fx.indexOf('aurora') >= 0) {
      const gr = ctx.createLinearGradient(-g.rx, g.ry, g.rx, -g.ry);
      const cols = d.auroraColors || ['#5CFFB0', '#3FD9FF', '#B07BFF'];
      for (let i = 0; i <= 6; i++) { const p = (i / 6 + t * 0.12) % 1; const k = p * cols.length; const a = cols[Math.floor(k) % cols.length], b = cols[(Math.floor(k) + 1) % cols.length]; gr.addColorStop(i / 6, mixHex(a, b, k % 1)); }
      return gr;
    }
    return col;
  }
  const MOTIF = ['....1....', '.1..1..1.', '..1.2.1..', '...121...', '112121211', '...121...', '..1.2.1..', '.1..1..1.', '....1....'];

  function drawPupilShape(ctx, d, type, px, py, prx, pry, color, t, side, rig) {
    ctx.fillStyle = color;
    switch (type) {
      case 'slit': ctx.beginPath(); ctx.ellipse(px, py, prx * clamp(0.5 * ((rig && rig.slitW) || 1), 0.3, 1.05), pry * 1.08, 0, 0, TAU); ctx.fill(); return { gx: 0.4 };
      case 'plus': { const w = Math.min(prx, pry) * 0.62; rrect(ctx, px - prx, py - w / 2, prx * 2, w, w / 2); ctx.fill(); rrect(ctx, px - w / 2, py - pry, w, pry * 2, w / 2); ctx.fill(); return { gx: 0.55, gy: 0.2, gs: 0.6 }; }
      case 'star': starPath(ctx, px, py, Math.max(prx, pry) * 1.12, 5, 0.5, Math.sin(t * 1.2) * 0.15); ctx.fill(); return { gs: 0.7 };
      case 'heart': heartPath(ctx, px, py + pry * 0.05, Math.max(prx, pry) * 1.15, side * 0.08); ctx.fill(); return { gx: -0.4, gy: -0.3, gs: 0.7 };
      case 'ring': { ctx.beginPath(); ctx.ellipse(px, py, prx, pry, 0, 0, TAU); ctx.ellipse(px, py, prx * 0.5, pry * 0.5, 0, 0, TAU); ctx.fill('evenodd'); return { gx: 0.45, gs: 0.6 }; }
      case 'double': { ctx.beginPath(); ctx.ellipse(px - prx * 0.1, py - pry * 0.18, prx * 0.78, pry * 0.68, 0, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.ellipse(px + prx * 0.55, py + pry * 0.62, prx * 0.32, pry * 0.27, 0, 0, TAU); ctx.fill(); return { gs: 0.75, gy: -0.6 }; }
      case 'pebble': superPath(ctx, px, py, prx * 1.04, pry * 0.9, side * -0.18, 2.6); ctx.fill(); return {};
      case 'crescent': { ctx.beginPath(); ctx.ellipse(px, py, prx, pry, 0, 0, TAU); ctx.ellipse(px + prx * 0.55 * -side, py - pry * 0.18, prx * 0.82, pry * 0.84, 0, 0, TAU); ctx.fill('evenodd'); return { none: true }; }
      case 'diamond': ctx.beginPath(); ctx.moveTo(px, py - pry * 1.12); ctx.lineTo(px + prx * 0.95, py); ctx.lineTo(px, py + pry * 1.12); ctx.lineTo(px - prx * 0.95, py); ctx.closePath(); ctx.fill(); return { gs: 0.65 };
      case 'spiral': {
        ctx.strokeStyle = color; ctx.lineCap = 'round'; ctx.lineWidth = Math.min(prx, pry) * 0.34; ctx.beginPath();
        const rot = t * 5 * side, R = Math.max(prx, pry) * 1.15;
        for (let i = 0; i <= 90; i++) { const q = i / 90, a = rot + q * TAU * 2.3, rr = q * R; const x = px + Math.cos(a) * rr, y = py + Math.sin(a) * rr * (pry / Math.max(prx, pry)); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
        ctx.stroke(); return { none: true };
      }
      case 'battery': {
        const w = prx * 1.6, h = pry * 1.3, lw = Math.min(w, h) * 0.16;
        ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineJoin = 'round';
        rrect(ctx, px - w / 2, py - h / 2 + lw * 0.6, w, h - lw * 0.6, lw); ctx.stroke();
        ctx.fillStyle = color; rrect(ctx, px - w * 0.18, py - h / 2 - lw * 0.7, w * 0.36, lw * 1.3, lw * 0.4); ctx.fill();
        if (Math.sin(t * 6) > -0.2) { ctx.fillStyle = '#FF3B3B'; rrect(ctx, px - w / 2 + lw * 1.1, py + h / 2 - lw * 1.1 - h * 0.18, w - lw * 2.2, h * 0.18, lw * 0.4); ctx.fill(); }
        return { none: true };
      }
      case 'level': {
        const w = prx * 1.5, h = pry * 1.45, lw = Math.min(w, h) * 0.15, lv = clamp(rig ? rig.charge : 0.6, 0, 1);
        ctx.strokeStyle = color; ctx.lineWidth = lw;
        rrect(ctx, px - w / 2, py - h / 2, w, h, w * 0.32); ctx.stroke();
        ctx.save(); rrect(ctx, px - w / 2 + lw, py - h / 2 + lw, w - lw * 2, h - lw * 2, w * 0.24); ctx.clip();
        const top = py + h / 2 - lw - (h - lw * 2) * lv;
        ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(px - w, py + h);
        for (let i = 0; i <= 12; i++) { const x = px - w / 2 + (i / 12) * w; ctx.lineTo(x, top + Math.sin(i * 0.9 + t * 6) * h * 0.025); }
        ctx.lineTo(px + w, py + h); ctx.closePath(); ctx.fill(); ctx.restore();
        return { none: true };
      }
      default: ctx.beginPath(); ctx.ellipse(px, py, prx, pry, 0, 0, TAU); ctx.fill(); return {};
    }
  }

  function drawEye(ctx, rig, d, side, cx, cy, D, opt) {
    const s = rig.s, P = d.pupil, g = eyeFrame(rig, d, side, cx, cy, D), t = rig.t;
    const fx = d.fx || [];
    const L = side < 0;
    if (g.k <= 0.004) return g;
    if (g.ry > 0.3) {
      const pts = silhouette(rig, d, g, D);
      ctx.save(); ctx.translate(g.x, g.y);
      const body = new Path2D(); pts.forEach(([x, y], i) => (i ? body.lineTo(x, y) : body.moveTo(x, y))); body.closePath();
      const G = L ? rig.pL : rig.pR, gx = G[0].x, gy = G[1].x;
      if (fx.indexOf('outline') >= 0) {
        ctx.lineWidth = D * 0.022 * g.k; ctx.lineJoin = 'round'; ctx.strokeStyle = whiteFill(ctx, d, side, g, t, gx); ctx.stroke(body);
      } else { ctx.fillStyle = whiteFill(ctx, d, side, g, t, gx); ctx.fill(body); }
      ctx.save(); ctx.clip(body);
      if (fx.indexOf('shimmer') >= 0) { // a crisp light band sweeping across
        const p = ((t + (L ? 0 : 0.12)) % 3.4) / 0.8;
        if (p < 1) { ctx.save(); ctx.rotate(0.45); ctx.fillStyle = 'rgba(255,255,255,.42)'; const x = lerp(-g.rx * 2, g.rx * 2, p); ctx.fillRect(x, -g.ry * 2, g.rx * 0.28, g.ry * 4); ctx.fillRect(x + g.rx * 0.38, -g.ry * 2, g.rx * 0.1, g.ry * 4); ctx.restore(); }
      }
      // pupil
      const pc = opt.hetero === false ? P.L : L ? P.L : P.R || P.L;
      const ps = Math.max(0, L ? s.pupilL.x : s.pupilR.x);
      const pulse = s.listen.x > 0.02 ? 1 + 0.28 * rig.level * clamp(s.listen.x, 0, 1) : 1;
      const wob = rig.gmode === 'wobble' ? Math.sin(t * 13 + side) * 0.025 : 0;
      const px = (-side * P.inset + gx * P.travel + wob) * g.rx, py = (gy * P.travel * 0.78 + 0.04) * g.ry;
      const prx = P.rx * g.rx * ps * pulse, pry = (P.ry * g.ry * ps * pulse) / (s.sy.x || 1) / Math.max(0.3, 1 - 0.12 * clamp(g.b, 0, 1)) * 0.98;
      if (ps > 0.01) {
        let info;
        if (fx.indexOf('starfield') >= 0 || fx.indexOf('galaxy') >= 0) {
          info = drawPupilShape(ctx, d, P.type, px, py, prx, pry, pc, t, side, rig);
          ctx.save(); ctx.beginPath(); ctx.ellipse(px, py, prx, pry, 0, 0, TAU); ctx.clip();
          for (let i = 0; i < 18; i++) {
            const z = ((h01(i + side * 50) + t * 0.25) % 1), a = h01(i * 7 + 3) * TAU, rr = z * Math.max(prx, pry) * 1.2;
            ctx.fillStyle = 'rgba(255,255,255,' + (0.3 + 0.7 * z).toFixed(2) + ')';
            ctx.beginPath(); ctx.arc(px + Math.cos(a) * rr, py + Math.sin(a) * rr, Math.max(0.6, prx * 0.06 * z), 0, TAU); ctx.fill();
          }
          ctx.restore();
        } else if (fx.indexOf('folk') >= 0) {
          const fr = Math.min(prx, pry);
          ctx.fillStyle = pc; ctx.beginPath(); ctx.arc(px, py, fr * 1.08, 0, TAU); ctx.fill();
          ctx.fillStyle = d.folkBase || '#FFF6E6'; ctx.beginPath(); ctx.arc(px, py, fr * 0.9, 0, TAU); ctx.fill();
          const n = 9, cell = (fr * 1.62) / n;
          ctx.lineCap = 'round'; ctx.lineWidth = cell * 0.42;
          for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
            const ch = MOTIF[j][i]; if (ch === '.') continue;
            const x = px + (i - 4) * cell, y = py + (j - 4) * cell, q = cell * 0.36;
            ctx.strokeStyle = ch === '1' ? pc : d.folkThread || '#141414';
            ctx.beginPath(); ctx.moveTo(x - q, y - q); ctx.lineTo(x + q, y + q); ctx.moveTo(x + q, y - q); ctx.lineTo(x - q, y + q); ctx.stroke();
          }
          info = { gs: 0.5, gx: 0.55, gy: -0.62 };
        } else info = drawPupilShape(ctx, d, P.type, px, py, prx, pry, pc, t, side, rig);
        if (d.glint && !info.none) {
          const gs = Math.min(prx, pry) * (d.glint.size || 1) * (info.gs || 1);
          ctx.fillStyle = d.glint.color || '#FFF6E2';
          superPath(ctx, px + (info.gx != null ? info.gx : 0.34) * prx, py + (info.gy != null ? info.gy : -0.46) * pry, 0.3 * gs, 0.2 * gs, -0.55, 2.6); ctx.fill();
        }
      }
      // alternate pupils (heart / star / spiral / battery / level) burst in with overshoot
      const av = L ? s.altL.x : s.altR.x;
      if (av > 0.01) {
        const k = Math.max(0, av), beat = rig.altType === 'heart' ? 1 + 0.09 * Math.pow(Math.max(0, Math.sin(t * TAU * 1.3)), 8) : 1;
        const col = rig.altType === 'heart' ? '#FF2E63' : rig.altType === 'star' ? '#FFD23A' : pc;
        const ar = P.rx * g.rx * 1.05 * k * beat, ary = P.ry * g.ry * 0.95 * k * beat;
        const ax = px * 0.5, ay = py * 0.5 - g.ry * 0.03;
        const inf = drawPupilShape(ctx, d, rig.altType, ax, ay, ar, ary, col, t, side, rig);
        if (!inf.none && d.glint) { ctx.fillStyle = d.glint.color || '#FFF6E2'; superPath(ctx, ax - ar * 0.4, ay - ary * 0.45, ar * 0.17, ar * 0.11, -0.6, 2.6); ctx.fill(); }
      }
      ctx.restore();
      ctx.restore();
    }
    // >< squeeze
    if (g.sq > 0.02) {
      const w = d.shape.rx * D * Math.max(0, s.scale.x) * 0.85 * clamp(g.sq, 0, 1.3), h = d.shape.ry * D * 0.45 * clamp(g.sq, 0, 1.3);
      ctx.save(); ctx.translate(g.x, g.y); ctx.strokeStyle = side > 0 && d.whiteR ? d.whiteR : d.white;
      if ((d.fx || []).indexOf('rainbow') >= 0) ctx.strokeStyle = hsl(t * 40, 95, 66);
      ctx.lineWidth = D * 0.032; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      const dir = -side;
      ctx.beginPath(); ctx.moveTo(-dir * w * 0.5, -h); ctx.lineTo(dir * w * 0.55, 0); ctx.lineTo(-dir * w * 0.5, h); ctx.stroke();
      ctx.restore();
    }
    return g;
  }

  function drawOverlays(ctx, rig, d, eyes, cx, cy, D) {
    const s = rig.s, t = rig.t, ink = d.white;
    const A = (v) => clamp(v, 0, 1);
    // blush: flat ovals with three little strokes
    if (s.blush.x > 0.02) for (const g of eyes) {
      const x = g.x + g.side * d.shape.rx * D * 0.35, y = g.y + d.shape.ry * D * 0.98;
      ctx.fillStyle = rgba('#FF6F9C', 0.55 * A(s.blush.x)); ctx.beginPath(); ctx.ellipse(x, y, D * 0.06, D * 0.026, 0, 0, TAU); ctx.fill();
      ctx.strokeStyle = rgba('#FF9DBC', 0.9 * A(s.blush.x)); ctx.lineWidth = D * 0.006; ctx.lineCap = 'round';
      for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.moveTo(x + i * D * 0.022 - D * 0.006, y + D * 0.01); ctx.lineTo(x + i * D * 0.022 + D * 0.006, y - D * 0.01); ctx.stroke(); }
    }
    // tears
    const drop = (x, y, r, a) => { ctx.fillStyle = rgba('#6FC3FF', a); ctx.beginPath(); ctx.moveTo(x, y - r * 1.7); ctx.quadraticCurveTo(x + r * 1.05, y - r * 0.2, x, y + r); ctx.quadraticCurveTo(x - r * 1.05, y - r * 0.2, x, y - r * 1.7); ctx.fill(); ctx.fillStyle = rgba('#E6F6FF', a); ctx.beginPath(); ctx.ellipse(x - r * 0.3, y - r * 0.15, r * 0.22, r * 0.32, -0.3, 0, TAU); ctx.fill(); };
    if (s.tears.x > 0.02) {
      const g = eyes[1], per = 2.2, p = (t % per) / per;
      const x = g.x + g.rx * 0.55, y0 = g.y + g.ry * 0.75;
      const grow = smooth(p / 0.45), fall = p > 0.45 ? Math.pow((p - 0.45) / 0.55, 2) : 0;
      drop(x, y0 + fall * D * 0.32, D * 0.017 * (0.4 + 0.6 * grow), A(s.tears.x) * (1 - smooth((fall - 0.7) / 0.3)));
    }
    if (s.cry.x > 0.02) for (const g of eyes) {
      const a = A(s.cry.x), x0 = g.x + g.side * g.rx * 0.45, y0 = g.y + g.ry * 0.5, w = D * 0.034;
      ctx.fillStyle = rgba('#6FC3FF', 0.85 * a);
      ctx.beginPath(); ctx.moveTo(x0 - w / 2, y0);
      for (let i = 0; i <= 12; i++) { const y = y0 + (i / 12) * D * 0.5; ctx.lineTo(x0 - w / 2 + Math.sin(i * 0.9 - t * 9) * D * 0.006, y); }
      for (let i = 12; i >= 0; i--) { const y = y0 + (i / 12) * D * 0.5; ctx.lineTo(x0 + w / 2 + Math.sin(i * 0.9 - t * 9 + 1) * D * 0.006, y); }
      ctx.closePath(); ctx.fill();
      for (let i = 0; i < 3; i++) { const p = (t * 1.6 + i / 3) % 1; drop(x0 + Math.sin(i * 3) * w * 0.2, y0 + p * D * 0.45, D * 0.012, a * (1 - p * 0.3)); }
    }
    // ? and ! and …
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    if (s.q.x > 0.03) {
      const k = clamp(s.q.x, 0, 1.3), x = cx + 0.3 * D, y = cy - 0.27 * D + Math.sin(t * 2.5) * D * 0.008, r = D * 0.032 * k;
      ctx.save(); ctx.translate(x, y); ctx.rotate(0.18 + Math.sin(t * 2) * 0.08); ctx.strokeStyle = ink; ctx.lineWidth = D * 0.016 * k;
      ctx.beginPath(); ctx.arc(0, 0, r, PI * 1.05, PI * 2.35); ctx.quadraticCurveTo(0, r * 0.9, 0, r * 1.5); ctx.stroke();
      ctx.fillStyle = ink; ctx.beginPath(); ctx.arc(0, r * 2.35, D * 0.01 * k, 0, TAU); ctx.fill(); ctx.restore();
    }
    if (s.bang.x > 0.03) {
      const k = clamp(s.bang.x, 0, 1.4), x = cx + 0.31 * D, y = cy - 0.3 * D;
      ctx.save(); ctx.translate(x, y); ctx.rotate(0.15); ctx.fillStyle = ink;
      ctx.beginPath(); ctx.moveTo(-D * 0.014 * k, -D * 0.05 * k); ctx.lineTo(D * 0.014 * k, -D * 0.05 * k); ctx.lineTo(D * 0.006 * k, D * 0.012 * k); ctx.lineTo(-D * 0.006 * k, D * 0.012 * k); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.arc(0, D * 0.032 * k, D * 0.01 * k, 0, TAU); ctx.fill(); ctx.restore();
    }
    if (s.dots.x > 0.03) for (let i = 0; i < 3; i++) {
      const bnc = Math.max(0, Math.sin(t * 5 - i * 0.9));
      ctx.fillStyle = rgba(ink, A(s.dots.x) * (0.4 + 0.6 * bnc));
      ctx.beginPath(); ctx.arc(cx + (0.2 + i * 0.05) * D, cy - (0.3 + i * 0.03) * D - bnc * 0.012 * D, D * (0.012 + i * 0.003), 0, TAU); ctx.fill();
    }
    if (s.zzz.x > 0.05) {
      ctx.save(); ctx.strokeStyle = ink; ctx.lineWidth = D * 0.013;
      for (let i = 0; i < 2; i++) {
        const p = (t * 0.36 + i * 0.5) % 1, x = cx + (0.3 + p * 0.05) * D, y = cy - (0.25 + p * 0.1) * D, z = D * (0.05 - i * 0.016) * (0.65 + 0.35 * p);
        ctx.globalAlpha = Math.sin(p * PI) * A(s.zzz.x);
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + z, y); ctx.lineTo(x, y + z); ctx.lineTo(x + z, y + z); ctx.stroke();
      }
      ctx.restore();
    }
    if (s.hearts.x > 0.02) for (let i = 0; i < 3; i++) {
      const per = 1.9, p = ((t + i * 0.63) % per) / per;
      const x = cx + [-0.08, 0.12, 0.02][i] * D + Math.sin(t * 2.4 + i) * 0.012 * D, y = cy + (0.3 - 0.42 * p) * D;
      const pop = p < 0.18 ? outBack(p / 0.18, 2.4) : 1 - smooth((p - 0.75) / 0.25);
      if (pop > 0.01) { heartPath(ctx, x, y, D * 0.034 * pop * A(s.hearts.x), Math.sin(t * 3 + i) * 0.25); ctx.fillStyle = '#FF2E63'; ctx.fill(); }
    }
    if (s.spark.x > 0.02) for (let i = 0; i < 6; i++) {
      const per = 1.1 + h01(i) * 0.6, p = ((t + h01(i + 9) * per) % per) / per, a = Math.sin(p * PI);
      const ang = (i / 6) * TAU + 0.4, rr = 0.33 + 0.05 * h01(i + 3);
      ctx.fillStyle = i % 2 ? '#FFD23A' : ink;
      sparkPath(ctx, cx + Math.cos(ang) * rr * D * 1.05, cy + Math.sin(ang) * rr * D * 0.85, D * 0.024 * a * A(s.spark.x), p); ctx.fill();
    }
    if (s.spray.x > 0.02) for (let i = 0; i < 12; i++) {
      const p = clamp((rig.t * 2.2 + h01(i)) % 1, 0, 1), ang = -PI / 2 + (h01(i + 5) - 0.5) * 2.6, rr = (0.08 + p * 0.38) * D;
      ctx.fillStyle = rgba(i % 3 ? '#BFE8FF' : ink, A(s.spray.x) * (1 - p));
      ctx.beginPath(); ctx.arc(cx + Math.cos(ang) * rr, cy + 0.12 * D + Math.sin(ang) * rr * 0.6, D * (0.006 + 0.006 * h01(i + 2)), 0, TAU); ctx.fill();
    }
    if (s.check.x > 0.02) {
      const k = clamp(s.check.x, 0, 1.3), x = cx, y = cy + 0.31 * D;
      ctx.save(); ctx.strokeStyle = '#4DFFB0'; ctx.lineWidth = D * 0.026; ctx.globalAlpha = A(s.check.x);
      ctx.beginPath(); ctx.moveTo(x - 0.045 * D * k, y); ctx.lineTo(x - 0.012 * D * k, y + 0.03 * D * k); ctx.lineTo(x + 0.055 * D * k, y - 0.04 * D * k); ctx.stroke();
      const p = (t % 1.2) / 1.2; ctx.lineWidth = D * 0.008; ctx.globalAlpha = A(s.check.x) * (1 - p) * 0.8;
      ctx.beginPath(); ctx.arc(cx, cy, D * (0.42 + 0.06 * p), 0, TAU); ctx.stroke(); ctx.restore();
    }
    if (s.listen.x > 0.02) {
      const a = A(s.listen.x), lv = rig.level;
      ctx.save(); ctx.strokeStyle = ink; ctx.lineWidth = D * 0.012;
      for (let i = 0; i < 3; i++) {
        const r = D * (0.05 + i * 0.035) * (0.9 + 0.2 * lv);
        ctx.globalAlpha = a * (0.9 - i * 0.25) * (0.5 + 0.5 * lv);
        ctx.beginPath(); ctx.arc(cx + 0.34 * D, cy + 0.02 * D, r, -0.6, 0.6); ctx.stroke();
        ctx.beginPath(); ctx.arc(cx - 0.34 * D, cy + 0.02 * D, r, PI - 0.6, PI + 0.6); ctx.stroke();
      }
      ctx.restore();
    }
    if (s.bolt.x > 0.02) {
      const k = clamp(s.bolt.x, 0, 1.3), x = cx, y = cy - 0.32 * D + Math.sin(t * 3) * D * 0.006;
      ctx.fillStyle = '#FFD23A'; ctx.beginPath();
      ctx.moveTo(x + 0.01 * D * k, y - 0.05 * D * k); ctx.lineTo(x - 0.03 * D * k, y + 0.006 * D * k); ctx.lineTo(x - 0.002 * D * k, y + 0.006 * D * k);
      ctx.lineTo(x - 0.012 * D * k, y + 0.05 * D * k); ctx.lineTo(x + 0.03 * D * k, y - 0.008 * D * k); ctx.lineTo(x + 0.002 * D * k, y - 0.008 * D * k); ctx.closePath(); ctx.fill();
    }
    if ((d.fx || []).indexOf('halo') >= 0) for (let i = 0; i < 14; i++) {
      const a = (i / 14) * TAU + t * 0.25, tw = 0.5 + 0.5 * Math.sin(t * 2.2 + i * 1.7);
      ctx.fillStyle = d.haloColor || '#FFD23A';
      sparkPath(ctx, cx + Math.cos(a) * D * 0.43, cy + Math.sin(a) * D * 0.43, D * (0.008 + 0.01 * tw), a); ctx.fill();
    }
    if ((d.fx || []).indexOf('glitter') >= 0) for (let i = 0; i < 6; i++) {
      const per = 2 + h01(i + 1) * 2, p = ((t + h01(i) * per) % per) / per, a = Math.sin(p * PI);
      const ang = h01(i * 3) * TAU, rr = 0.24 + 0.2 * h01(i * 5);
      ctx.fillStyle = d.glitterColor || '#FFFFFF';
      sparkPath(ctx, cx + Math.cos(ang) * rr * D, cy + Math.sin(ang) * rr * D * 0.85, D * 0.016 * a, 0); ctx.fill();
    }
  }

  function render(ctx, rig, design, cx, cy, D, opt) {
    opt = opt || {};
    const d = design;
    if (opt.glass !== false) drawGlass(ctx, cx, cy, D, opt);
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, D / 2, 0, TAU); ctx.clip();
    const s = rig.s;
    const shk = s.shake.x, bnc = clamp(s.bounce.x, 0, 1.5);
    const ox = shk * D * Math.sin(rig.t * TAU * rig.shakeF), oy = shk * D * 0.4 * Math.sin(rig.t * TAU * rig.shakeF * 1.3 + 1);
    const hopP = Math.abs(Math.sin(rig.t * TAU * 1.6));
    const by = -bnc * 0.03 * D * hopP;
    ctx.translate(cx + ox, cy + oy + by); ctx.rotate(s.rot.x); ctx.translate(-cx, -cy);
    if (bnc > 0.01) { const sq = 1 + bnc * 0.06 * (hopP - 0.5); s.sy.x *= sq; s.sx.x /= sq; }
    const eyes = [drawEye(ctx, rig, d, -1, cx, cy, D, opt), drawEye(ctx, rig, d, 1, cx, cy, D, opt)];
    if (bnc > 0.01) { const sq = 1 + bnc * 0.06 * (hopP - 0.5); s.sy.x /= sq; s.sx.x *= sq; }
    drawOverlays(ctx, rig, d, eyes, cx, cy, D);
    ctx.restore();
    if (opt.glass !== false && opt.sheen !== false) drawSheen(ctx, cx, cy, D);
  }

  // ------------------------------------------------------------ instances & shared loop
  const live = new Set();
  let rafId = 0, last = 0;
  function tick(now) {
    rafId = 0;
    const dt = Math.min(0.05, (now - last) / 1000 || 0.016); last = now;
    for (const inst of live) if (inst._visible && !inst._paused) { inst.step(dt * inst._speed); inst.draw(); }
    if (live.size) rafId = requestAnimationFrame(tick);
  }
  function ensureLoop() { if (!rafId && typeof requestAnimationFrame !== 'undefined') { last = performance.now(); rafId = requestAnimationFrame(tick); } }

  function createEyes(canvas, design, opts) {
    opts = Object.assign({ mode: 'live', bezel: true, sheen: true, background: null, fit: 0.9, hetero: true, interactive: true, randomMood: false, seed: null, manual: false, dpr: null, autoResize: true, speed: 1, onChange: null }, opts || {});
    let d = normalizeDesign(design);
    const ctx = canvas.getContext('2d');
    const rig = new Rig(opts.seed != null ? opts.seed : hashStr(d.id || d.name) ^ 0x5eed, opts.mode);
    rig.randomMood = !!opts.randomMood;
    if (opts.moodPool) rig.moodPool = opts.moodPool;
    if (opts.moodEvery) { rig.moodEvery = opts.moodEvery; rig.nextRandom = opts.moodEvery[0] * (0.3 + rig.r()); }
    rig.onChange = opts.onChange;
    const reduce = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
    const inst = {
      canvas, rig, _visible: true, _paused: false, _speed: opts.speed * (reduce ? 0.6 : 1),
      get design() { return d; },
      get expression() { return rig.reaction ? rig.reaction.name : rig.mood; },
      get mode() { return rig.mode; },
      get loopTime() { return rig.lt; },
      setExpression(name) { rig.setExpression(name); return inst; },
      react(name, hold) { rig.react(name, hold); return inst; },
      lookAt(x, y) { rig.look = x == null ? null : [clamp(x, -1, 1), clamp(y, -1, 1)]; return inst; },
      blink(n) { rig.blink(n || 1); return inst; },
      hop() { rig.hop(); return inst; },
      setDesign(nd, o) {
        const swap = () => { d = normalizeDesign(nd); };
        if (o && o.instant) swap(); else { rig.blink(1); setTimeout(swap, 110); }
        return inst;
      },
      setMode(m) { rig.mode = m; if (m === 'loop') { rig.lt = LOOP - 0.3; } rig.setExpression('neutral'); return inst; },
      setHetero(v) { opts.hetero = !!v; return inst; },
      setRandomMood(v) { rig.randomMood = !!v; rig.nextRandom = rig.t + 0.5; return inst; },
      setLevel(v) { rig.levelExt = v == null ? null : clamp(v, 0, 1); return inst; },
      hide() { rig.reaction = null; rig._snap({ scale: 0 }); return inst; },
      pause(v) { inst._paused = v !== false; return inst; },
      step(dt) { rig.update(dt); return inst; },
      resize() {
        const dpr = opts.dpr || Math.min(2, (typeof devicePixelRatio !== 'undefined' && devicePixelRatio) || 1);
        const w = canvas.clientWidth || canvas.width, h = canvas.clientHeight || canvas.height;
        if (w && h) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
        return inst;
      },
      draw() {
        const W = canvas.width, H = canvas.height;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        if (opts.background) { ctx.fillStyle = opts.background; ctx.fillRect(0, 0, W, H); } else ctx.clearRect(0, 0, W, H);
        const D = Math.min(W, H) * opts.fit;
        render(ctx, rig, d, W / 2, H / 2, D, opts);
        return inst;
      },
      destroy() {
        live.delete(inst);
        if (inst._io) inst._io.disconnect();
        if (inst._ro) inst._ro.disconnect();
        for (const [ev, fn] of inst._listeners || []) canvas.removeEventListener(ev, fn);
      },
    };
    if (!opts.manual) {
      if (opts.autoResize) {
        inst.resize();
        if (typeof ResizeObserver !== 'undefined') { inst._ro = new ResizeObserver(() => inst.resize()); inst._ro.observe(canvas); }
      }
      if (typeof IntersectionObserver !== 'undefined') { inst._io = new IntersectionObserver((es) => { inst._visible = es[es.length - 1].isIntersecting; }); inst._io.observe(canvas); }
      if (opts.interactive) {
        const mv = (e) => { const r = canvas.getBoundingClientRect(); inst.lookAt(((e.clientX - r.left) / r.width - 0.5) * 2.6, ((e.clientY - r.top) / r.height - 0.5) * 2.6); };
        const lv = () => inst.lookAt(null);
        const dn = () => { if (rig.mode !== 'loop') rig.react('happy', 1.3); };
        inst._listeners = [['pointermove', mv], ['pointerleave', lv], ['pointerdown', dn]];
        for (const [ev, fn] of inst._listeners) canvas.addEventListener(ev, fn);
      }
      live.add(inst); ensureLoop();
    }
    return inst;
  }

  // ------------------------------------------------------------ the collection & birth roll
  const RARITIES = [
    { key: 'common', name: 'Common', rate: 0.5, color: '#C9C4B8' },
    { key: 'uncommon', name: 'Uncommon', rate: 0.25, color: '#5CFFB0' },
    { key: 'rare', name: 'Rare', rate: 0.15, color: '#3FA9FF' },
    { key: 'epic', name: 'Epic', rate: 0.07, color: '#B57BFF' },
    { key: 'legendary', name: 'Legendary', rate: 0.025, color: '#FFC23A' },
    { key: 'mythic', name: 'Mythic', rate: 0.005, color: '#FF4F9A' },
  ];
  // seedHi/seedLo: the 64-bit chip seed (on device: the 48-bit eFuse MAC)
  function roll(designs, seedHi, seedLo) {
    const h = mix32((seedLo >>> 0) ^ mix32((seedHi >>> 0) ^ 0x534f554c));
    const u = mix32(h) / 4294967296;
    let acc = 0, tier = RARITIES[RARITIES.length - 1];
    for (const r of RARITIES) { acc += r.rate; if (u < acc) { tier = r; break; } }
    const pool = designs.filter((x) => x.rarity === tier.key);
    const k = Math.floor((mix32(h ^ 0x9e3779b9) / 4294967296) * pool.length);
    return { design: pool[k], rarity: tier.key, odds: tier.rate / pool.length };
  }
  function rollFromChipId(designs, hex) {
    hex = String(hex).replace(/[^0-9a-fA-F]/g, '').padStart(16, '0').slice(-16);
    return roll(designs, parseInt(hex.slice(0, 8), 16), parseInt(hex.slice(8), 16));
  }
  function rollRandom(designs, rand) { rand = rand || Math.random; return roll(designs, Math.floor(rand() * 4294967296), Math.floor(rand() * 4294967296)); }

  return {
    VERSION, createEyes, render, Rig, normalizeDesign, DEFAULT_DESIGN, MOODS, REACTIONS, EXPRESSIONS, RANDOM_POOL,
    LOOP, SEGMENTS, RARITIES, roll, rollFromChipId, rollRandom, hashStr, drawGlass, heartPath, sparkPath,
  };
});
