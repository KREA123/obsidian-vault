#!/usr/bin/env python3
"""SOUL trailer soundtrack: voice-over (Piper TTS) + original synthesized music + synthesized SFX.

Everything here is generated, so nothing needs a licence: the music and SFX are numpy synthesis,
and the voice is Piper TTS with the en_US-lessac-high voice (rhasspy/piper-voices).
The cue times mirror the timeline in soul_trailer.html (T_END = 49 s). Scene cuts sit on
half-second boundaries, which are exactly the beats at 120 BPM, so every cut lands on a beat.

usage: python3 audio.py            → builds the mix and muxes it into both mp4s
env:   AUDIO_TMP (scratch dir), PIPER_VOICE (path to .onnx)
"""
import os, json, wave, subprocess, pathlib, re
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly

HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path(os.environ.get('AUDIO_TMP', '/tmp/soul_audio')); TMP.mkdir(parents=True, exist_ok=True)
VOICE = os.environ.get('PIPER_VOICE', str(TMP / 'en_US-lessac-high.onnx'))
SR = 48000
T_END = 49.0
N = int(SR * T_END)
BPM = 120; BEAT = 60 / BPM; BAR = 4 * BEAT
rng = np.random.default_rng(7)

# ───────────────────────── voice-over cues (start s, text, max length s) ─────────────────────────
VO = [
    (1.05,  "Meet Soul.", 3.0),
    (5.75,  "Every day, you talk to AI...", 2.4),
    (8.25,  "in a chat box.", 1.5),
    (10.15, "AI has a brain.", 1.7),
    (11.95, "Now it has a soul.", 1.6),
    (14.05, "It lives on your desk.", 3.0),
    (19.80, "It looks back.", 1.6),
    (21.85, "Hold the glass. It listens.", 2.6),
    (24.85, "Type.", .75), (25.63, "Talk.", .75), (26.41, "Remember.", 1.0),
    (27.65, "Claude asks.", 1.5), (29.30, "You approve.", 1.5),
    (31.15, "Works with the AI you already have.", 2.7),
    (34.25, "Five colours. One soul.", 2.6),
    (37.40, "Sleeps in its egg.", 2.0),
    (39.75, "Soul.", 1.6),
    (42.55, "Your AI, with a soul.", 2.0),
    (44.75, "From two hundred forty-nine euros.", 2.0),
    (46.95, "Join the waitlist.", 1.4),
]

# ───────────────────────── helpers ─────────────────────────
def t2i(t): return int(round(t * SR))
def tt(d): return np.arange(int(d * SR)) / SR
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x, axis=0)
def st(x, pan=0.0):  # mono → stereo (equal-power pan, -1..1)
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)
def add(bus, x, t):
    i = t2i(t)
    if i < 0: x = x[-i:]; i = 0
    j = min(len(bus), i + len(x))
    if j > i: bus[i:j] += x[:j - i]
def env_adsr(n, a, r, sus_end=None):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
def saw(f, d, ph=0.0):
    t = tt(d); return 2 * ((t * f + ph) % 1) - 1
def varlp(x, fc):  # time-varying one-pole low-pass (2 cascaded)
    a = 1 - np.exp(-2 * np.pi * np.asarray(fc) / SR)
    y1 = np.zeros_like(x); y2 = np.zeros_like(x); s1 = s2 = 0.0
    for i in range(len(x)):
        s1 += a[i] * (x[i] - s1); s2 += a[i] * (s1 - s2); y1[i] = s1; y2[i] = s2
    return y2
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

# ───────────────────────── music ─────────────────────────
# D major, I–V–vi–IV (one chord per 2 s bar), add9 colours for warmth
CHORDS = [  # (bass midi, pad voicing, arp tones)
    (38, [62, 66, 69, 76], [62, 66, 69, 74, 76, 81]),   # D add9
    (33, [61, 64, 69, 71], [61, 64, 69, 73, 76, 81]),   # A add9 (sus-ish)
    (35, [62, 66, 71, 73], [59, 62, 66, 71, 74, 78]),   # Bm add9
    (31, [62, 67, 71, 69], [59, 62, 67, 71, 74, 79]),   # G add9
]
def chord_at(t): return CHORDS[int(t // BAR) % 4]

def automation(points):
    """piecewise-linear automation curve over the whole timeline: [(t, v), ...]"""
    ts, vs = zip(*points); return np.interp(np.arange(N) / SR, ts, vs)

def make_music():
    pad_b = np.zeros((N, 2)); pad_d = np.zeros((N, 2)); arp = np.zeros((N, 2)); bass = np.zeros(N)
    kick = np.zeros(N); clap = np.zeros((N, 2)); hat = np.zeros((N, 2))
    nbars = int(np.ceil(T_END / BAR))
    for b in range(nbars):
        t0 = b * BAR; bassm, voic, tones = CHORDS[b % 4]
        d = BAR + .9
        for k, m in enumerate(voic):
            for c, det in enumerate([-.11, .09]):
                f = mtof(m) * 2 ** (det / 12)
                x = (saw(f, d, rng.random()) + saw(f * 2 ** (.05 / 12), d, rng.random()) * .7) * env_adsr(int(d * SR), .5, .9)
                v = x * .05
                add(pad_b[:, c], lp(v, 2600), t0); add(pad_d[:, c], lp(v, 700), t0)
        # plucky arp: 16ths, up pattern through the chord tones
        for s in range(16):
            ts = t0 + s * BEAT / 4; m = tones[[0, 2, 4, 1, 3, 5, 2, 4][s % 8]]
            f = mtof(m); t = tt(.5); e = np.exp(-t / .13)
            x = (np.sin(2 * np.pi * f * t) + .35 * np.sin(4 * np.pi * f * t) * np.exp(-t / .05) + .12 * np.sin(6 * np.pi * f * t)) * e
            x[:int(.002 * SR)] *= np.linspace(0, 1, int(.002 * SR))
            add(arp, st(x * (.11 if s % 4 == 0 else .075), pan=.35 * np.sin(s * 1.3)), ts)
        # bass: pulsing 8ths on the root
        for s in range(8):
            ts = t0 + s * BEAT / 2; f = mtof(bassm + 12); t = tt(.26)
            x = (np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)) * np.exp(-t / .16) * env_adsr(len(t), .006, .04)
            add(bass, np.tanh(1.6 * x) * .22, ts)
        # drums
        for q in range(4):
            tb = t0 + q * BEAT
            if q in (0, 2) or (q == 3 and b % 2):      # kick 1, 3 (+ 4& on odd bars)
                tk = tb + (BEAT / 2 if q == 3 else 0); t = tt(.45)
                fr = 46 + 95 * np.exp(-t / .035); ph = 2 * np.pi * np.cumsum(fr) / SR
                x = np.sin(ph) * np.exp(-t / .28) + .3 * np.exp(-t / .004) * rng.standard_normal(len(t)) * .3
                add(kick, x * .55, tk)
            if q in (1, 3):                              # soft clap 2, 4
                t = tt(.3); nz = rng.standard_normal(len(t))
                e = sum(np.exp(-np.clip(t - o, 0, None) / .012) * (t >= o) for o in (0, .011, .022)) * .6 + np.exp(-t / .12) * .5
                x = bp(nz * e, 900, 2600) * .22
                add(clap, st(x, .1), tb)
            for h in (0, 1):                             # 8th hats, accent on the off-beat
                t = tt(.08); x = hp(rng.standard_normal(len(t)), 7000) * np.exp(-t / (.025 if h == 0 else .04))
                add(hat, st(x * (.035 if h == 0 else .06), .3 if h else -.3), tb + h * BEAT / 2)
    # sidechain from the kick
    sc = np.ones(N)
    kick_hits = np.nonzero(np.diff((np.abs(kick) > .2).astype(int)) == 1)[0]
    for k in kick_hits:
        t = tt(.35); g = 1 - .45 * np.exp(-t / .1); j = min(N, k + len(t)); sc[k:j] = np.minimum(sc[k:j], g[:j - k])

    # arrangement (automation), cuts on beats
    A = lambda p: automation(p)
    pad_bright = A([(0, 0), (1.5, .55), (5.4, .6), (5.5, 0), (11.9, 0), (12.0, .6), (37, .6), (37.1, 0), (39.5, 0), (41.8, .55), (42, 1.0), (46.5, .9), (49, 0)])
    pad_dark   = A([(0, .2), (1.2, .45), (5.5, 1.0), (11.9, 1.0), (12.0, .35), (37, .35), (37.1, 1.0), (39.5, 1.0), (41.8, .5), (42, .4), (46.5, 1.1), (48.2, .8), (49, 0)])
    arp_g      = A([(0, 0), (2.5, .5), (5.4, .55), (5.5, 0), (12.0, 0), (12.05, .75), (13.5, 1), (37, 1), (37.05, .35), (39.5, .45), (41.85, .9), (41.86, 0), (42.0, 0), (42.05, 1.0), (46.5, .8), (47.5, 0), (49, 0)])
    bass_g     = A([(0, 0), (13.45, 0), (13.5, 1), (37, 1), (37.05, 0), (42, 0), (42.01, 1), (46.5, 1), (46.51, 0), (49, 0)])
    drum_g     = A([(0, 0), (13.45, 0), (13.5, 1), (37, 1), (37.01, 0), (42, 0), (42.01, 1), (46.5, 1), (46.51, 0), (49, 0)])
    hat_g      = A([(0, 0), (12.0, 0), (12.01, .6), (13.5, 1), (39.5, 1), (39.51, 0), (42, 0), (42.01, 1), (46.5, 1), (46.51, 0), (49, 0)])
    m = pad_b * pad_bright[:, None] * sc[:, None] + pad_d * pad_dark[:, None] * sc[:, None] * 1.1
    m = reverb(m, .35)
    a = arp * arp_g[:, None]
    # ping-pong 3/16 delay on the arp
    dl = t2i(BEAT * .75); y = a.copy()
    for k in range(1, 5):
        sh = np.zeros_like(a); sh[dl * k:] = a[:-dl * k] * (.38 ** k)
        y += sh[:, ::-1] if k % 2 else sh
    m += reverb(lp(y, 5200), .25)
    m += st(bass * bass_g * sc, 0)
    m += st(kick * drum_g, 0) + (clap * drum_g[:, None]) + reverb(hat * hat_g[:, None], .1)
    # final resolve: sustained D major chord with a slow swell, under the end card
    t = tt(3.4); ch = sum(np.sin(2 * np.pi * mtof(mm) * t + rng.random() * 6) for mm in (50, 57, 62, 66, 69, 74))
    ch = ch * env_adsr(len(t), .4, 2.4) * .045
    add(m, reverb(st(lp(ch, 3000), 0), .5), 46.5)
    return m

# ───────────────────────── sfx ─────────────────────────
def whoosh(d=.55, lo=300, hi=5000, gain=.5, pan=(-.6, .6)):
    n = int(d * SR); t = np.arange(n) / n
    e = np.sin(np.pi * t) ** 2 * np.exp(-1.2 * t)
    fc = lo * (hi / lo) ** np.sin(np.pi * t)
    x = lp(varlp(rng.standard_normal(n), fc), 7000, 4) * e * gain * 2.6
    p = np.linspace(pan[0], pan[1], n); a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)
def click(gain=.18):
    t = tt(.03); x = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t / .0025) + .4 * np.sin(2 * np.pi * (1800 + 400 * rng.random()) * t) * np.exp(-t / .008)
    return st(x * gain, rng.uniform(-.2, .2))
def pop(midi=86, gain=.22, pan=0.0):
    t = tt(.18); f = mtof(midi) * (1 + .6 * np.exp(-t / .012)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / .05) + .1 * hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / .004)
    return st(x * gain, pan)
def tick(gain=.12):
    t = tt(.04); x = (np.sin(2 * np.pi * 2600 * t) + .6 * np.sin(2 * np.pi * 1300 * t)) * np.exp(-t / .006)
    return st(x * gain, 0)
def tap(gain=.3):
    t = tt(.5); f = 640 * np.exp(-t / .5) + 0; f = np.maximum(f, 420); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / .09) + .25 * np.sin(2 * ph) * np.exp(-t / .04)
    return reverb(st(x * gain, 0), .25)
def shimmer(d=3.2, gain=.09, notes=(86, 93, 98, 102, 105)):
    t = tt(d); x = np.zeros(len(t))
    for i, m in enumerate(notes):
        x += np.sin(2 * np.pi * mtof(m) * t + i) * (.6 + .4 * np.sin(2 * np.pi * (5 + i * 1.7) * t)) * np.exp(-t / (1.0 + .3 * i))
    x *= np.minimum(1, t / .04)
    s = np.stack([x, np.roll(x, 240)], 1) * gain
    return reverb(s, .7)
def swell(d=1.1, gain=.5):
    n = int(d * SR); t = np.arange(n) / n
    nz = varlp(rng.standard_normal(n), 150 * (3500 / 150) ** (t ** 1.6)) * (t ** 2.2) * 3
    sub = np.sin(2 * np.pi * np.cumsum(45 + 25 * t) / SR) * t ** 1.5 * .5
    x = (nz + sub) * gain; x[-int(.01 * SR):] *= np.linspace(1, 0, int(.01 * SR))
    return st(x, 0)
def riser(d=2.3, gain=.32):
    n = int(d * SR); t = np.arange(n) / n
    nz = varlp(rng.standard_normal(n), 300 * (9000 / 300) ** (t ** 1.4)) * t ** 1.8 * 3
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (t * 1.0)) / SR) * t ** 2 * .15
    x = (nz + tone) * gain; x[-int(.02 * SR):] *= np.linspace(1, 0, int(.02 * SR))
    return np.stack([x, np.roll(x, 120)], 1)
def boom(gain=.55):
    t = tt(1.6); fr = 38 + 60 * np.exp(-t / .06); ph = 2 * np.pi * np.cumsum(fr) / SR
    return reverb(st(np.sin(ph) * np.exp(-t / .5) * gain, 0), .3)

def make_sfx():
    s = np.zeros((N, 2))
    # whooshes on the cuts (peak lands on the cut)
    for tc, g in [(0.05, .35), (5.5, .4), (10.0, .25), (13.5, .55), (17.1, .4), (17.5, .4), (19.35, .5), (21.5, .4),
                  (24.5, .4), (27.5, .4), (31.0, .4), (34.05, .3), (37.0, .3), (39.5, .4), (46.5, .35), (9.45, .3)]:
        add(s, whoosh(gain=g, pan=(-.5, .5) if int(tc * 2) % 2 else (.5, -.5)), tc - .3)
    for i in range(5):  # family sliding in
        add(s, whoosh(.4, 600, 6000, .16, (.8, -.2)), 34.1 + i * .11 - .05)
    # typewriter clicks
    l1 = 'Every day, you talk to AI…'
    for k in range(1, len(l1) + 1): add(s, click(.12 if l1[k - 1] == ' ' else .2), 5.5 + (k + 3) / 15)
    l2 = '…in a chat box.'
    for k in range(1, len(l2) + 1): add(s, click(.12 if l2[k - 1] == ' ' else .2), 8.25 + k / 15)
    # pops (pitched to the D-major pentatonic so they sit in the music)
    pent = [74, 76, 78, 81, 83, 86, 88, 90, 93]
    for i in range(0, 12, 2): add(s, pop(pent[3 + i // 2], .1, (i - 6) / 8), .3 + i * .06 + .12)
    for i in range(5): add(s, pop(pent[2 + i], .16, (i - 2) / 3), 5.5 + 1.2 + i * .13 + .1)
    add(s, pop(86, .2), 10 + .75 + .12)
    add(s, pop(90, .22), 10 + 2.95 + .12)
    for i in range(3): add(s, pop(93 + i * 2, .12, (i - 1) / 2), 13.0 + i * .08 + .1)
    for i in range(3): add(s, pop(pent[4 + i], .2), 24.5 + .5 + i * .78 + .1)
    for i in range(3): add(s, pop(93 + i * 2, .12, (i - 1) / 2), 22.85 + .15 + i * .1 + .1)
    add(s, pop(93, .2), 27.5 + 1.75 + .2 + .1)
    for i in range(4): add(s, pop(pent[3 + i], .24, (i - 1.5) / 2), 31 + .8 + i * .2 + .12)
    add(s, pop(86, .22), 41.85 + 3.35 + .12)
    # "soul" turns amber: a little sparkle; low swell into "Now it has a soul"
    add(s, shimmer(1.6, .05, (93, 98, 102)), 12.75)
    add(s, swell(1.05, .45), 10.9)
    # blinks
    for tb in [19.55 + .72, 19.55 + 1.6, 19.55 + 1.82, 27.5 + 1.32, 41.85 + 1.78, 41.85 + 3.97, 46.5 + 1.63]: add(s, tick(.1), tb)
    # taps
    for tp in [22.85, 29.25, 45.95]: add(s, tap(.3), tp - .02)
    # build → reveal
    add(s, riser(2.3, .3), 39.55)
    add(s, boom(.5), 41.98)
    add(s, shimmer(3.2, .08), 42.15)
    add(s, shimmer(2.2, .04, (86, 90, 93, 98)), 46.75)
    return s

# ───────────────────────── voice-over ─────────────────────────
def read_wav(p):
    with wave.open(str(p)) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x, sr
def trim(x, thr=.01):
    idx = np.nonzero(np.abs(x) > thr)[0]
    if len(idx) == 0: return x
    a = max(0, idx[0] - int(.01 * SR)); b = min(len(x), idx[-1] + int(.06 * SR)); return x[a:b]
def make_vo():
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(VOICE)
    bus = np.zeros(N); report = []
    for i, (t0, text, mx) in enumerate(VO):
        ls = 1.06
        for attempt in range(6):
            p = TMP / f'vo_{i:02d}.wav'
            with wave.open(str(p), 'wb') as w:
                voice.synthesize_wav(text, w, syn_config=SynthesisConfig(length_scale=ls, noise_scale=.55, noise_w_scale=.7))
            x, sr = read_wav(p)
            x = trim(resample_poly(x, SR // 50, sr // 50) if sr != SR else x)
            if len(x) / SR <= mx or ls < .8: break
            ls *= .93
        x = x / (np.abs(x).max() + 1e-9) * .7
        x[:int(.004 * SR)] *= np.linspace(0, 1, int(.004 * SR))
        add(bus, x, t0); report.append((t0, text, round(len(x) / SR, 2), mx, round(ls, 3)))
    raw = TMP / 'vo_raw.wav'; write_wav(raw, st(bus, 0) * np.sqrt(2))
    # voice chain: high-pass, warmth/presence EQ, gentle compression, a touch of room
    out = TMP / 'vo_fx.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-af',
                    'highpass=f=85,equalizer=f=220:t=q:w=1:g=1.5,equalizer=f=450:t=q:w=1.2:g=-2,'
                    'equalizer=f=3800:t=q:w=1.4:g=2.5,equalizer=f=9000:t=q:w=1:g=1.5,'
                    'acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,'
                    'aecho=0.85:0.6:38|67:0.12|0.08', '-ar', str(SR), str(out)], check=True)
    vo, _ = read_wav_st(out)
    return vo[:N] if len(vo) >= N else np.pad(vo, ((0, N - len(vo)), (0, 0))), report

def write_wav(p, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
def read_wav_st(p):
    with wave.open(str(p)) as w:
        ch = w.getnchannels(); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, ch), sr

# ───────────────────────── mix ─────────────────────────
def main():
    vo, report = make_vo()
    for r in report: print('VO %6.2fs  %-40s %.2fs (max %.1f, ls %.3f)' % r)
    music = make_music(); sfx = make_sfx()
    # duck the music under the voice (~-8 dB), smooth attack/release
    e = np.abs(vo).max(1); k = int(.03 * SR)
    e = np.convolve(e, np.ones(k) / k, 'same'); on = (e > .02).astype(float)
    g = np.ones(N); cur = 1.0; att = 1 - np.exp(-1 / (.06 * SR)); rel = 1 - np.exp(-1 / (.35 * SR))
    tgt = 1 - (1 - db(-8)) * on
    for i in range(N):
        cur += (tgt[i] - cur) * (att if tgt[i] < cur else rel); g[i] = cur
    mix = music * db(-3) * g[:, None] + sfx * db(-4) + vo * db(0)
    # fade the very end with the picture
    fe = np.ones(N); i0 = t2i(48.2); fe[i0:] = np.linspace(1, 0, N - i0) ** 1.5; mix *= fe[:, None]
    mix *= .9 / np.abs(mix).max()
    pre = TMP / 'mix_pre.wav'; write_wav(pre, mix)
    for name, x in (('music', music), ('sfx', sfx), ('vo', vo)): write_wav(TMP / f'stem_{name}.wav', x / (np.abs(x).max() + 1e-9) * .9)
    # loudness: two-pass EBU R128 to -14 LUFS integrated, -2 dBTP
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(pre), '-af', 'loudnorm=I=-14:TP=-2:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr).group(0))
    final = TMP / 'mix_final.wav'
    af = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(pre), '-af', af, '-ar', str(SR), str(final)], check=True)
    for v in ('soul_trailer.mp4', 'soul_trailer_vertical.mp4'):
        src = HERE / v; tmp = TMP / ('mux_' + v)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-i', str(final), '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-ar', str(SR), '-shortest', '-movflags', '+faststart', str(tmp)], check=True)
        os.replace(tmp, src); print('muxed', src)

if __name__ == '__main__':
    main()
