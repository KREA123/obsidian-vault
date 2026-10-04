#!/usr/bin/env python3
"""EXPEDO trailer soundtrack: licensed music bed + synthesized trailer layer / UI SFX + neural TTS voice-over.

Same pipeline as the SOUL trailer (micul-smecher/trailer/audio.py), adapted:
- Music bed (about 3.5 dB under the voice, ducked a further ~7 dB while it speaks): "Electro Dreams" by Arulo, Mixkit (Mixkit Stock Music Free License: commercial use, no attribution
  required). See MUSIC-LICENSE.md. The mp3 is downloaded at build time and never committed (the licence forbids
  redistributing it as a standalone file). 120 BPM, edited on its own beat grid (1 beat = 0.5 s):
    video  0–40 s  ← track  8–48 s : the filtered intro build under the pain scene, the drop lands on the logo at 8 s
    video 40–44 s  ← track 60–64 s : last two bars of the breakdown (the "safety" beat)
    video 44–50 s  ← track 64–70 s : second drop on tracking / ramburs
    video 50–56 s  ← track 108–114 s: the track's own last two bars under the end card; it stops on the downbeat at 54 s
- Trailer layer (braams, impacts, sub drops, risers, reversed cymbals, glitches, packing-tape rips) and the UI SFX
  (clicks, key taps, pops, ticks, chimes, whooshes) are synthesized here and placed on the page's event times.
- Voice: one short line per scene, each starting on a beat. Microsoft neural voices via edge-tts:
  RO ro-RO-EmilNeural (chosen over ro-RO-AlinaNeural and the multilingual voices: by far the cleanest Romanian in an
  ASR round-trip), EN en-US-AndrewMultilingualNeural. VOICE_FILE_RO / VOICE_FILE_EN = a recorded track timed to the
  video from 0 s replaces the TTS.
- Light voice processing (low cut + gentle compression), music ducks ~7 dB under the voice,
  loudnorm to -14 LUFS (two-pass, linear), AAC 192k with a true-peak check on the encoded audio (≤ -2 dBTP), muxed into
  every rendered mp4 of that language.
  Writes voiceover_script.md (RO + EN, with timings).

usage: python3 audio.py [ro|en ...]        env: AUDIO_TMP (scratch dir), NO_MUX=1, NO_ASR=1, VOICE_FILE_RO / VOICE_FILE_EN
"""
import os, sys, json, wave, subprocess, pathlib, re, ssl, asyncio, urllib.request
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path(os.environ.get('AUDIO_TMP', '/tmp/claude-0/expedo_audio')); TMP.mkdir(parents=True, exist_ok=True)
SR = 48000
rng = np.random.default_rng(11)

# ── beat grid (must match expedo_trailer.html: b(n) = n * 0.5 s) ──
BEAT = 0.5
def b(n): return n * BEAT
T_END = 56.0
N = int(round(SR * T_END))

MUSIC_URL = 'https://assets.mixkit.co/music/190/190.mp3'   # "Electro Dreams" by Arulo (Mixkit), 120 BPM, ~F# minor
PHASE = 0.047                                              # first beat of the track's grid (kick onsets at 0.047 + 0.5 k)
# (video start, track start, video end). The last segment is the track's own ending: its final two bars run under the
# end card and the music stops by itself on the downbeat at video 54 s (track 112 s), with its natural tail.
MUSIC_EDIT = [(0.0, 8 + PHASE, 40.0), (40.0, 60 + PHASE, 44.0), (44.0, 64 + PHASE, 50.0), (50.0, 108 + PHASE, 56.0)]
PENT = [78, 81, 83, 85, 88, 90, 93, 95, 97, 100]          # F# minor pentatonic (F#5 …), for tonal pops

# ── voice-over: (beat, text, on-screen note[, rate override]) ──
VOICES = {'ro': ('ro-RO-EmilNeural', '+6%', '+2Hz'), 'en': ('en-US-AndrewMultilingualNeural', '+6%', '+0Hz')}
VO = {
 'ro': [
  (1,   'AWB eșuat. Factură cu eroare.',                         'error cards pile up'),
  (8,   'Și nimeni nu-ți spune ce să repari.',                   'headline over the blurred errors'),
  (17,  'Fă cunoștință cu Expedo.',                              'logo reveal on the drop'),
  (24,  'De la comandă la ramburs, totul automat.',              'the six-step chain + courier / invoicing names'),
  (32,  'Adresa e verificată înainte să ajungă la curier.',      'order #1110, Cargus locality error'),
  (40,  'Ai greșit localitatea? Corectezi pe loc.',              '"Ai vrut: …?", typing Eforie Nord, AWB + invoice'),
  (48,  'Fiecare eroare, pe românește, cu ce ai de făcut.',      'orders that need attention'),
  (56,  'Selectezi tot. Un singur clic.',                        'select all → Generează AWB + factură', '+12%'),
  (62,  'AWB-uri, facturi și etichete, într-un singur PDF.',     'AWB + invoice per row, labels PDF'),
  (72,  'Reguli pentru fiecare caz. Și un mod de probă.',        'rules, test mode'),
  (80,  'Fără AWB-uri duble. Și știi cine refuză colete.',       'safety cards: no duplicates, retries, refusal warning'),
  (88,  'Coletul e urmărit până la livrare.',                    'tracking timeline, second drop'),
  (94,  'Iar rambursul e bifat ca încasat.',                     'dashboard counter'),
  (100, 'Expedo. Comenzile pleacă singure.',                     'end card'),
  (107, 'Pentru magazinele Shopify.',                            'end card subline'),
 ],
 'en': [
  (1,   'Failed labels. Invoice errors.',                         'error cards pile up'),
  (8,   'And nobody tells you what to fix.',                      'headline over the blurred errors'),
  (17,  'Meet Expedo.',                                           'logo reveal on the drop'),
  (24,  'From order to cash on delivery. All automatic.',         'the six-step chain + courier / invoicing names'),
  (32,  'Every address is checked before it reaches the courier.', 'order #1110, Cargus locality error'),
  (40,  'Wrong town? Fix it on the spot.',                        '"Did you mean …?", typing Eforie Nord, label + invoice'),
  (48,  'Every error in plain words, plus what to do.',           'orders that need attention'),
  (56,  'Select all. One click.',                                 'select all → generate label + invoice'),
  (62,  'Labels and invoices for every order, in one PDF.',       'label + invoice per row, labels PDF'),
  (72,  'Rules for every case. And a test mode.',                 'rules, test mode'),
  (80,  'No duplicates. And a heads-up on customers who refuse parcels.', 'safety cards: no duplicates, retries, refusal warning', '+10%'),
  (88,  'Every parcel, tracked to the door.',                     'tracking timeline, second drop'),
  (94,  'And cash on delivery, marked as collected.',             'dashboard counter'),
  (100, 'Expedo. Orders that ship themselves.',                   'end card'),
  (107, 'Built for Shopify stores in Romania.',                       'end card subline'),
 ],
}
def tts_say(text, lang):   # phonetic help for the TTS only (on-screen text keeps the real spelling)
    if lang == 'ro': text = text.replace('AWB-uri', 'a-ve-be-uri').replace('AWB', 'a-ve-be')   # how merchants say it
    return text

# ───────────────────────── helpers ─────────────────────────
def t2i(t): return int(round(t * SR))
def tt(d): return np.arange(int(d * SR)) / SR
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x, axis=0)
def st(x, pan=0.0):
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)
def add(bus, x, t):
    i = t2i(t)
    if i < 0: x = x[-i:]; i = 0
    j = min(len(bus), i + len(x))
    if j > i: bus[i:j] += x[:j - i]
def addend(bus, x, t_end): add(bus, x, t_end - len(x) / SR)
def varlp(x, fc):
    a = 1 - np.exp(-2 * np.pi * np.asarray(fc) / SR)
    y = np.zeros_like(x); s1 = s2 = 0.0
    for i in range(len(x)):
        s1 += a[i] * (x[i] - s1); s2 += a[i] * (s1 - s2); y[i] = s2
    return y
def reverb_ir(dur=2.2, decay=2.6, seed=3):
    r = np.random.default_rng(seed); n = int(dur * SR); t = np.arange(n) / SR
    ir = r.standard_normal((n, 2)) * np.exp(-decay * t)[:, None]
    ir = lp(ir, 6000); ir[:int(.012 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0))
IR = reverb_ir()
def reverb(x, wet=.3):
    y = np.stack([fftconvolve(x[:, c], IR[:, c])[:len(x)] for c in range(2)], 1)
    return x + wet * y
def db(x): return 10 ** (x / 20)

# ───────────────────────── music bed ─────────────────────────
def load_track():
    mp3 = TMP / 'music_190.mp3'
    if not mp3.exists():
        req = urllib.request.Request(MUSIC_URL, headers={'User-Agent': 'Mozilla/5.0'})
        mp3.write_bytes(urllib.request.urlopen(req).read())
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(mp3), '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)

def make_bed():
    tr = load_track(); bed = np.zeros((N, 2)); fade = int(.006 * SR)
    for v0, s0, v1 in MUSIC_EDIT:
        seg = tr[t2i(s0):t2i(s0) + t2i(v1 - v0)].copy()
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]; seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        add(bed, seg, v0)
    # the track's intro is ~16 dB under its drop: lift it so the pain scene isn't a hole, keep the contrast
    g = np.interp(np.arange(N) / SR, [0, 7.9, 8.0, 40, 40.05, 44, 52, T_END], [db(7), db(7), 1, 1, db(1.5), db(1.5), 1, 1])
    bed *= g[:, None]
    fe = np.ones(N); j0 = t2i(55.7); fe[j0:] = np.linspace(1, 0, N - j0)   # only a click guard on the last frames
    return bed * fe[:, None]

# ───────────────────────── trailer layer ─────────────────────────
ROOT = mtof(30)   # F#1 ≈ 46 Hz
def braam(d=3.2, gain=.5, root=ROOT):
    t = tt(d); x = np.zeros(len(t))
    for f, a in [(root, 1), (root * 2, .8), (root * 3, .45), (root * 4, .3), (root * 2.4, .3)]:   # root + minor third colour
        for det in (-.12, 0, .1):
            ff = f * 2 ** (det / 12); x += a * (2 * ((t * ff + rng.random()) % 1) - 1)
    fc = 180 + 2200 * np.exp(-t / .35) * (1 - np.exp(-t / .03))
    x = varlp(x / 6, fc)
    x = np.tanh(2.2 * x) * np.exp(-t / 1.3) * np.minimum(1, t / .015)
    sub = np.sin(2 * np.pi * root / 2 * t) * np.exp(-t / 1.6) * .6
    y = st((x + sub) * gain, 0); y[:, 1] = np.roll(y[:, 1], 90)
    return reverb(y, .45)
def impact(gain=.6, low=42, crack=.35):
    t = tt(2.4); fr = low + 70 * np.exp(-t / .05); ph = 2 * np.pi * np.cumsum(fr) / SR
    body = np.sin(ph) * np.exp(-t / .45)
    nz = bp(rng.standard_normal(len(t)), 300, 5000) * np.exp(-t / .07) * crack
    tail = lp(rng.standard_normal(len(t)), 1200) * np.exp(-t / .6) * .12
    return reverb(st(np.tanh(1.5 * (body + nz + tail)) * gain, 0), .55)
def subdrop(d=1.4, gain=.55):
    t = tt(d); f = 30 + 55 * np.exp(-t / .35); ph = 2 * np.pi * np.cumsum(f) / SR
    return st(np.sin(ph) * np.exp(-t / .7) * gain, 0)
def revcym(d=1.3, gain=.35):
    n = int(d * SR); t = np.arange(n) / n
    x = hp(rng.standard_normal(n), 4000, 2) * (np.exp(4 * t) - 1) / (np.e ** 4 - 1)
    x[-int(.004 * SR):] *= np.linspace(1, 0, int(.004 * SR))
    return np.stack([x, np.roll(x, 60)], 1) * gain
def riser(d=2.3, gain=.32):
    n = int(d * SR); t = np.arange(n) / n
    nz = varlp(rng.standard_normal(n), 300 * (9000 / 300) ** (t ** 1.4)) * t ** 1.8 * 3
    tone = np.sin(2 * np.pi * np.cumsum(mtof(54) * 2 ** (t * 1.0)) / SR) * t ** 2 * .15
    x = (nz + tone) * gain; x[-int(.02 * SR):] *= np.linspace(1, 0, int(.02 * SR))
    return np.stack([x, np.roll(x, 120)], 1)
def boom(gain=.55):
    t = tt(1.6); fr = 38 + 60 * np.exp(-t / .06); ph = 2 * np.pi * np.cumsum(fr) / SR
    return reverb(st(np.sin(ph) * np.exp(-t / .5) * gain, 0), .3)
def drone(d=8.0, gain=.12):
    """Dark tension bed for the pain scene: detuned low saws through a slowly opening filter, pulsing on the beat."""
    t = tt(d); x = np.zeros(len(t))
    for f in (ROOT * 2, ROOT * 2 * 2 ** (1 / 12) * 1.003, ROOT * 3):
        x += 2 * ((t * f) % 1) - 1
    x = varlp(x / 3, 120 + 900 * (t / d) ** 2)
    pul = .75 + .25 * np.cos(2 * np.pi * t / BEAT) ** 8
    x *= pul * np.minimum(1, t / .3) * np.minimum(1, (d - t) / .2) * gain
    return reverb(st(x), .3)

# ───────────────────────── sfx ─────────────────────────
def whoosh(d=.55, lo=300, hi=5000, gain=.5, pan=(-.6, .6)):
    n = int(d * SR); t = np.arange(n) / n
    e = np.sin(np.pi * t) ** 2 * np.exp(-1.2 * t)
    fc = lo * (hi / lo) ** np.sin(np.pi * t)
    x = lp(varlp(rng.standard_normal(n), fc), 7000, 4) * e * gain * 2.6
    p = np.linspace(pan[0], pan[1], n); a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)
def click(gain=.18, pan=None):
    t = tt(.03); x = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t / .0025) + .4 * np.sin(2 * np.pi * (1800 + 400 * rng.random()) * t) * np.exp(-t / .008)
    return st(x * gain, rng.uniform(-.2, .2) if pan is None else pan)
def mouse(gain=.3):   # mouse button: two close clicks (down/up)
    s = np.zeros((int(.12 * SR), 2)); add(s, click(gain, 0), 0); add(s, click(gain * .6, 0), .07); return s
def key(gain=.16):    # keyboard tap
    t = tt(.06); x = bp(rng.standard_normal(len(t)), 900, 5000) * np.exp(-t / .008) + .3 * np.sin(2 * np.pi * 300 * t) * np.exp(-t / .01)
    return st(x * gain, rng.uniform(-.15, .15))
def pop(midi=85, gain=.22, pan=0.0):
    t = tt(.18); f = mtof(midi) * (1 + .6 * np.exp(-t / .012)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / .05) + .1 * hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / .004)
    return st(x * gain, pan)
def tick(gain=.12, f=2600):
    t = tt(.04); x = (np.sin(2 * np.pi * f * t) + .6 * np.sin(2 * np.pi * f / 2 * t)) * np.exp(-t / .006)
    return st(x * gain, 0)
def chime(notes=(85, 90, 97), gain=.12):   # success: a quick rising arpeggio
    s = np.zeros((int(1.6 * SR), 2))
    for i, m in enumerate(notes):
        t = tt(1.2); x = (np.sin(2 * np.pi * mtof(m) * t) + .25 * np.sin(4 * np.pi * mtof(m) * t)) * np.exp(-t / .35) * np.minimum(1, t / .004)
        add(s, st(x * gain, (i - 1) * .3), i * .07)
    return reverb(s, .35)
def shimmer(d=3.2, gain=.09, notes=(78, 85, 90, 97, 102)):
    t = tt(d); x = np.zeros(len(t))
    for i, m in enumerate(notes):
        x += np.sin(2 * np.pi * mtof(m) * t + i) * (.6 + .4 * np.sin(2 * np.pi * (5 + i * 1.7) * t)) * np.exp(-t / (1.0 + .3 * i))
    x *= np.minimum(1, t / .04)
    return reverb(np.stack([x, np.roll(x, 240)], 1) * gain, .7)
def errbuzz(gain=.2, pan=0.0):
    """Error notification: a short detuned square 'nope' (two falling notes) with a digital crunch."""
    out = np.zeros(int(.3 * SR))
    for k, (m, d0) in enumerate([(70, 0.0), (65, .085)]):
        t = tt(.12); f = mtof(m)
        x = np.sign(np.sin(2 * np.pi * f * t)) * .5 + np.sign(np.sin(2 * np.pi * f * 1.012 * t)) * .5
        x = lp(x, 3500) * np.exp(-t / .05) * np.minimum(1, t / .003)
        i = int(d0 * SR); out[i:i + len(x)] += x
    crunch = np.round(bp(rng.standard_normal(len(out)), 800, 6000) * 6) / 6 * np.exp(-np.arange(len(out)) / SR / .02) * .35
    return st((out + crunch) * gain, pan)
def glitch(d=1.6, gain=.25):
    """Stutter / bit-crushed bursts for the pain scene's breakdown."""
    n = int(d * SR); x = np.zeros(n); r = np.random.default_rng(5)
    i = 0
    while i < n:
        L = int(SR * r.choice([.03, .045, .06, .09])); g = r.choice([0, 1, 1])
        seg = bp(r.standard_normal(L), r.uniform(300, 1500), r.uniform(2500, 7000)) * g
        seg = np.round(seg * 4) / 4
        x[i:i + L] += seg[:max(0, min(L, n - i))]; i += L + int(SR * r.choice([0, .015, .03]))
    x *= np.linspace(.3, 1, n)
    return st(x * gain, 0)
def heartbeat(gain=.5):
    """lub-dub: two soft low thumps"""
    out = np.zeros(int(.5 * SR))
    for d0, a in ((0, 1.0), (.17, .7)):
        t = tt(.25); f = 52 + 30 * np.exp(-t / .03); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .07) * a
        i = int(d0 * SR); out[i:i + len(x)] += x
    return st(out * gain)
def vibrate(gain=.2):
    """a phone buzzing on the desk: two gated 160 Hz bursts with a rattle"""
    out = np.zeros(int(.6 * SR))
    for d0 in (0, .3):
        t = tt(.2); x = np.tanh(3 * np.sin(2 * np.pi * 160 * t)) * (1 + .4 * np.sin(2 * np.pi * 37 * t))
        x = bp(x, 120, 2500) * np.minimum(1, t / .01) * np.minimum(1, (.2 - t) / .02)
        i = int(d0 * SR); out[i:i + len(x)] += x
    return st(out * gain, .35)
def swell(d=3.0, gain=.15):
    n = int(d * SR); t = np.arange(n) / n
    x = varlp(rng.standard_normal(n), 200 * (4000 / 200) ** (t ** 1.5)) * t ** 2 * 2.5
    x[-int(.03 * SR):] *= np.linspace(1, 0, int(.03 * SR))
    return np.stack([x, np.roll(x, 90)], 1) * gain
def tape(d=.42, gain=.32, pan=0.0):
    """Packing tape pulled off the roll: crackly noise with fast irregular amplitude modulation."""
    n = int(d * SR); t = np.arange(n) / SR; r = np.random.default_rng(int(abs(pan) * 100) + 7)
    am = (r.random(n // 60 + 2) ** 3).repeat(60)[:n]
    x = bp(r.standard_normal(n), 900, 6000) * am * 2.2
    x *= np.minimum(1, t / .01) * np.exp(-((t - d * .45) / (d * .5)) ** 2)
    return st(x * gain, pan)
def slap(gain=.4):   # tape slapped down: low thud + papery crack
    t = tt(.3); x = np.sin(2 * np.pi * 110 * t) * np.exp(-t / .05) + bp(rng.standard_normal(len(t)), 600, 4000) * np.exp(-t / .015) * .6
    return reverb(st(x * gain), .2)

def make_trailer_layer():
    s = np.zeros((N, 2))
    add(s, impact(.45, 44, .25), 0.0); add(s, drone(8.0, .16), 0.0)
    add(s, boom(.5), b(8))                                   # "Și nimeni nu-ți spune…"
    add(s, glitch(1.1, .22), b(14)); addend(s, riser(2.6, .4), b(16)); addend(s, revcym(1.4, .4), b(16))
    for g, x in ((1.0, braam(3.6, 1.0)), (1.0, impact(1.0, 38, .45)), (1.0, subdrop(1.6, .7)), (1.0, shimmer(3.0, .07))):
        add(s, x * g, b(16))                                 # DROP 1: logo
    add(s, impact(.4, 46, .2), b(32))                        # address scene
    add(s, impact(.35, 46, .2), b(56))
    add(s, impact(.45, 42, .25), b(80)); add(s, shimmer(3.5, .05, (78, 85, 90, 97)), b(80))   # breakdown
    addend(s, riser(3.4, .42), b(88)); addend(s, revcym(1.5, .45), b(88))
    add(s, braam(3.2, .85), b(88)); add(s, impact(.95, 38, .45), b(88)); add(s, subdrop(1.5, .65), b(88))   # DROP 2
    add(s, braam(3.6, .9), b(100)); add(s, impact(1.0, 36, .5), b(100)); add(s, subdrop(1.8, .65), b(100))   # end card
    add(s, shimmer(4.0, .07, (78, 85, 90, 97, 102)), b(100.3))
    return s

def make_sfx():
    s = np.zeros((N, 2))
    # pain: one error buzz per card (times / x positions as in the page)
    t0s = [0, .25, .5, .75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.25]
    xs = [.5, .28, .72, .30, .70, .50, .22, .78, .52, .48]
    for t0, x in zip(t0s, xs): add(s, errbuzz(.22, (x - .5) * 1.4), t0 + .02)
    add(s, whoosh(.6, 200, 3000, .25, (-.3, .3)), b(7.6))
    # pain, denser: a clock ticking on the eighths, a heartbeat on the beat, phones buzzing, frantic retry clicks,
    # keyboard bursts and a noise swell that builds under "…nobody tells you what to fix"
    for k in range(30):
        add(s, tick(.035 + .03 * k / 30, 3300 if k % 2 == 0 else 2500), k * .25)
    for k in range(15): add(s, heartbeat(.5 + .25 * k / 15), k * BEAT)
    for tb in (1.75, 3.6, 5.6): add(s, vibrate(.2), tb)
    for tc in (2.55, 2.7, 2.85, 5.4, 5.55): add(s, mouse(.22), tc)
    for k in range(9): add(s, key(.12), 1.0 + k * .085 + (.04 if k % 3 == 0 else 0))
    addend(s, swell(3.4, .16), b(15.2))
    # logo: mark draws, word, tape slap
    add(s, whoosh(.5, 600, 7000, .22, (.4, -.4)), b(16) + .15); add(s, pop(PENT[3], .14), b(16) + .55)
    add(s, tape(.3, .3, .2), b(16) + 1.25); add(s, slap(.35), b(16) + 1.55)
    # tape wipes
    for tc in (b(24), b(56), b(100)): add(s, tape(.5, .38, -.3), tc - .3); add(s, whoosh(.5, 400, 6000, .3, (-.7, .7)), tc - .28)
    # flow: node activations, chips
    for i in range(6): add(s, pop(PENT[i], .16, (i - 2.5) / 3), b(24) + .35 + i * .52)
    for i in range(8): add(s, tick(.05, 3000), b(24) + 1.25 + (i if i < 5 else i + 1) * .08)
    # address scene (scene start b32 = 16 s; times from the page's keyframes)
    T4 = b(32)
    add(s, whoosh(.5, 300, 5000, .22, (.6, -.2)), T4 - .05)
    add(s, pop(PENT[4], .14), T4 + 2.0); add(s, tick(.08), T4 + 2.75)
    add(s, whoosh(.45, 300, 4000, .12, (0, 0)), T4 + 3.5)
    add(s, mouse(.28), T4 + 4.05)
    for i in range(5): add(s, key(.18), T4 + 4.25 + i * .11)
    add(s, mouse(.28), T4 + 5.5); add(s, pop(PENT[2], .1), T4 + 5.62)
    add(s, mouse(.28), T4 + 6.35); add(s, chime((85, 90, 97), .1), T4 + 6.55)
    # plain-Romanian errors: highlighter swishes
    T5 = b(48); add(s, whoosh(.45, 300, 5000, .2, (-.6, .4)), T5 - .1)
    for i in range(3): add(s, whoosh(.25, 2000, 8000, .09, (-.5, .5)), T5 + .6 + i * .75)
    # bulk
    T6 = b(56)
    add(s, mouse(.28), T6 + 1.0)
    for i in range(6): add(s, tick(.06, 2200 + i * 120), T6 + 1.02 + i * .04)
    add(s, whoosh(.35, 500, 4000, .1, (0, 0)), T6 + 1.1)
    add(s, mouse(.3), T6 + 2.5)
    for i in range(6): add(s, pop(PENT[i + 1], .12, (i - 2.5) / 4), T6 + 3.08 + i * .13)
    add(s, chime((85, 90, 97, 102), .1), T6 + 3.9)
    add(s, mouse(.28), T6 + 4.95)
    for i in range(6): add(s, whoosh(.3, 800, 7000, .12, ((i - 2.5) / 3, (i - 2.5) / 2)), T6 + 5.05 + i * .09)
    add(s, pop(PENT[5], .18), T6 + 5.85)
    # rules + test mode
    T7 = b(72); add(s, whoosh(.45, 300, 5000, .2, (.6, -.4)), T7 - .1)
    add(s, pop(PENT[3], .12), T7 + .4); add(s, whoosh(.35, 300, 3000, .08), T7 + 1.15); add(s, pop(PENT[4], .12), T7 + 1.75)
    add(s, whoosh(.45, 300, 4000, .18, (-.6, .2)), T7 + 1.95); add(s, pop(PENT[5], .13), T7 + 2.6)
    # safety cards (breakdown)
    T8 = b(80)
    for i, tc in enumerate((0, .9, 2.0)): add(s, pop(PENT[2 + i * 2], .14), T8 + tc + .05); add(s, whoosh(.35, 300, 3000, .08), T8 + tc - .1)
    # tracking timeline + counter
    T9 = b(88)
    for i in range(10): add(s, tick(.07, 1800 + i * 140), T9 + .25 + i * .23)
    add(s, pop(PENT[6], .14), T9 + 1.95)
    add(s, whoosh(.4, 300, 5000, .2, (.5, -.5)), T9 + 2.85)
    for i in range(22): add(s, tick(.035 + .02 * (i / 22), 2400 + 30 * i), T9 + 3.3 + 1.3 * (1 - (1 - i / 22) ** 1.6))
    add(s, chime((90, 97, 102), .12), T9 + 4.6)
    # end card
    T10 = b(100); add(s, tape(.32, .3, .3), T10 + 1.0); add(s, slap(.3), T10 + 1.15)
    add(s, shimmer(2.2, .05, (85, 90, 97, 102)), b(108))       # the music's own final downbeat
    return s

# ───────────────────────── voice ─────────────────────────
CA = os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
def edge_tts_save(text, voice, rate, pitch, out):
    import edge_tts, edge_tts.communicate as c
    if CA: c._SSL_CTX = ssl.create_default_context(cafile=CA)   # trust the egress proxy's CA (no verification is disabled)
    asyncio.run(edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=os.environ.get('HTTPS_PROXY')).save(str(out)))

def tts_line(lang, i, text, rate=None):
    voice, r0, pitch = VOICES[lang]; rate = rate or r0; say = tts_say(text, lang)
    mp3 = TMP / f'tts_{voice}_{i:02d}.mp3'; key_ = TMP / f'tts_{voice}_{i:02d}.txt'
    sig = f'{say}|{rate}|{pitch}'
    if not (mp3.exists() and key_.exists() and key_.read_text() == sig):
        edge_tts_save(say, voice, rate, pitch, mp3); key_.write_text(sig)
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(mp3), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    idx = np.nonzero(np.abs(x) > .01)[0]                     # trim edge silence so the line starts on the beat
    if len(idx): x = x[max(0, idx[0] - int(.005 * SR)): idx[-1] + int(.06 * SR)]
    return x

def make_tts(lang):
    bus = np.zeros(N); durs = []
    for i, (bt, text, _, *opt) in enumerate(VO[lang]):
        x = tts_line(lang, i, text, opt[0] if opt else None); x = x / (np.abs(x).max() + 1e-9) * .7
        add(bus, x, b(bt)); durs.append(len(x) / SR)
    raw = TMP / f'tts_raw_{lang}.wav'; write_wav(raw, st(bus, 0) * np.sqrt(2))
    return raw, durs

def load_voice(path, lang):
    out = TMP / f'voice_fx_{lang}.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(path), '-ac', '2', '-ar', str(SR), '-af',
                    'highpass=f=80:poles=2,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=150:makeup=1.5',
                    str(out)], check=True)
    v, _ = read_wav_st(out)
    v = v[:N] if len(v) >= N else np.pad(v, ((0, N - len(v)), (0, 0)))
    return v / (np.abs(v).max() + 1e-9) * .7

def write_wav(p, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
def read_wav_st(p):
    with wave.open(str(p)) as w:
        ch = w.getnchannels(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
        return x.reshape(-1, ch), w.getframerate()

def asr_check(path, lang):
    """ASR round-trip (faster-whisper) to confirm the lines are intelligible and on time."""
    if os.environ.get('NO_ASR'): return []
    try: from faster_whisper import WhisperModel
    except ImportError: print('faster-whisper not installed; skipping ASR check'); return []
    m = WhisperModel(os.environ.get('ASR_MODEL', 'small'), device='cpu', compute_type='int8', cpu_threads=4)
    segs, _ = m.transcribe(str(path), beam_size=5, language=lang, vad_filter=False, word_timestamps=False)
    out = [(sg.start, sg.end, sg.text.strip()) for sg in segs]
    for a, z, tx in out: print(f'ASR[{lang}] {a:6.2f}-{z:6.2f}  {tx}')
    return out

def ebur128(path):
    """(integrated LUFS, true peak dBTP) of an audio/video file"""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    tail = r[r.rfind('Summary:'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', tail).group(1)), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', tail).group(1))

def tc(t): return f'{int(t // 60):02d}:{t % 60:05.2f}'
def write_script(all_durs):
    rows = ['# Expedo trailer: voice-over script (EN + RO)', '',
            f'Timeline: `expedo_trailer_en.mp4` / `expedo_trailer_en_vertical.mp4` (English, primary) and `expedo_trailer_ro.mp4` / '
            f'`expedo_trailer_ro_vertical.mp4` (Romanian), {T_END:.0f} s, '
            f'music at 120 BPM (one beat = {BEAT} s). Each line starts on a beat, right on its cut: one short line per scene.',
            'Voices: Microsoft neural TTS through edge-tts. EN `en-US-AndrewMultilingualNeural` (rate %s), RO `ro-RO-EmilNeural` (rate %s, pitch %s).'
            % (VOICES['en'][1], VOICES['ro'][1], VOICES['ro'][2]),
            'To replace a voice with a recorded one (ElevenLabs or a human), record these lines to these timecodes: **Start** is the beat',
            'the line starts on, **End (max)** the latest it may run (the next line or cut), "TTS length" what the current synthetic read takes.', '']
    for lang, title in (('en', 'English (primary)'), ('ro', 'Română')):
        rows += [f'## {title}', '', '| # | Start | End (max) | TTS length | Line | On screen |', '|---|---|---|---|---|---|']
        starts = [b(l[0]) for l in VO[lang]]
        for i, ((bt, text, note, *_), t0) in enumerate(zip(VO[lang], starts), 1):
            t1 = starts[i] if i < len(starts) else T_END - .5
            d = all_durs.get(lang, [None] * len(starts))[i - 1]
            rows.append(f'| {i} | {tc(t0)} | {tc(t1)} | {"%.2f s" % d if d else "–"} | {text} | {note} |')
        rows.append('')
    rows += ['**How to drop a recorded voice in:** export one WAV/MP3 of the whole voice track, starting at 00:00.00 and timed to',
             'the video. Then run `VOICE_FILE_RO=/path/voice_ro.wav python3 audio.py ro` (or `VOICE_FILE_EN=… python3 audio.py en`).',
             'That replaces the TTS: gentle low cut and compression, the music ducks about 7 dB under the voice, -14 LUFS, and the',
             "language's mp4s are re-muxed.", '']
    (HERE / 'voiceover_script.md').write_text('\n'.join(rows))

# ───────────────────────── mix ─────────────────────────
def mix_lang(lang, bed, trailer, sfx):
    vf = os.environ.get(f'VOICE_FILE_{lang.upper()}')
    raw, durs = make_tts(lang)
    starts = [b(l[0]) for l in VO[lang]]
    for i, ((bt, text, *_), d) in enumerate(zip(VO[lang], durs)):
        nxt = starts[i + 1] if i + 1 < len(starts) else T_END
        flag = '  <-- OVERLAPS NEXT LINE' if starts[i] + d > nxt - .05 else ''
        print(f'VO[{lang}] {starts[i]:6.2f}s (b{bt:>5})  {d:4.2f}s  ends {starts[i] + d:6.2f} / next {nxt:6.2f}  {text}{flag}')
    vo = load_voice(vf or raw, lang)
    if not vf: asr_check(raw, lang)
    # ducking gain from the voice (~-7 dB), smooth attack/release
    e = np.abs(vo).max(1); k = int(.03 * SR)
    e = np.convolve(e, np.ones(k) / k, 'same'); on = (e > .02).astype(float)
    tgt = 1 - (1 - db(-7)) * on
    att = 1 - np.exp(-1 / (.05 * SR)); rel = 1 - np.exp(-1 / (.30 * SR))
    g = np.empty(N); cur = 1.0
    for i in range(N):
        cur += (tgt[i] - cur) * (att if tgt[i] < cur else rel); g[i] = cur
    mix = bed * db(-4.5) * g[:, None] + trailer * db(-4) * np.sqrt(g)[:, None] + sfx * db(-7) + vo * db(2)
    mix *= .9 / np.abs(mix).max()
    pre = TMP / f'mix_pre_{lang}.wav'; write_wav(pre, mix)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(pre), '-af', 'loudnorm=I=-14:TP=-2.8:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr).group(0))
    final = TMP / f'mix_final_{lang}.wav'
    af = (f"loudnorm=I=-14:TP=-2.8:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(pre), '-af', af, '-ar', str(SR), str(final)], check=True)
    # AAC adds inter-sample overshoot: encode, measure the true peak of the encoded audio, pull the gain down until ≤ -2 dBTP
    aac = TMP / f'mix_{lang}.m4a'; trim = 0.0
    for _ in range(4):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(final), '-af', f'volume={trim}dB', '-c:a', 'aac', '-b:a', '192k',
                        '-ac', '2', '-ar', str(SR), str(aac)], check=True)
        I, tp = ebur128(aac)
        print(f'AUDIO[{lang}] {I:.1f} LUFS, true peak {tp:.1f} dBTP (trim {trim:.1f} dB)')
        if tp <= -2.05: break
        trim -= tp + 2.15
    if not os.environ.get('NO_MUX'):
        for v in (f'expedo_trailer_{lang}.mp4', f'expedo_trailer_{lang}_vertical.mp4'):
            src = HERE / v
            if not src.exists(): continue
            tmp = TMP / ('mux_' + v)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-i', str(aac), '-map', '0:v:0', '-map', '1:a:0',
                            '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', str(tmp)], check=True)
            os.replace(tmp, src); print('muxed', src)
    return durs

def main():
    langs = [a for a in sys.argv[1:] if a in VO] or ['ro', 'en']
    bed = make_bed(); trailer = make_trailer_layer(); sfx = make_sfx()
    durs = {}
    for lang in langs: durs[lang] = mix_lang(lang, bed, trailer, sfx)
    # keep the other language's lengths in the script if it was not rebuilt this run
    for lang in VO:
        if lang not in durs:
            try: durs[lang] = [len(tts_line(lang, i, l[1], l[3] if len(l) > 3 else None)) / SR for i, l in enumerate(VO[lang])]
            except Exception: pass
    write_script(durs)

if __name__ == '__main__':
    main()
