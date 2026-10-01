#!/usr/bin/env python3
"""SOUL trailer soundtrack (v2): Kokoro voice-over + licensed music bed + synthesized trailer layer and SFX.

- Voice: Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0), voice am_michael, speed 0.9.
- Music bed: "Sci-Fi Score" by Arulo, Mixkit (Mixkit Stock Music Free License: commercial use, no
  attribution required). See MUSIC-LICENSE.md. The mp3 is downloaded at build time and not committed
  (the licence forbids redistributing it as a standalone file).
- Trailer layer (braams, impacts, sub drops, risers, reversed cymbals) and UI SFX are synthesized here.
- Mix: music ducked under the voice, loudnorm to -14 LUFS / -2 dBTP, AAC 192k into both mp4s.

The cue times mirror soul_trailer.html (T_END = 49 s).
usage: python3 audio.py      env: AUDIO_TMP (scratch dir)
"""
import os, json, wave, subprocess, pathlib, re, urllib.request
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly, iirnotch, filtfilt

HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path(os.environ.get('AUDIO_TMP', '/tmp/soul_audio')); TMP.mkdir(parents=True, exist_ok=True)
SR = 48000
T_END = 49.0
N = int(SR * T_END)
rng = np.random.default_rng(7)

MUSIC_URL = 'https://assets.mixkit.co/music/464/464.mp3'   # "Sci-Fi Score" by Arulo (Mixkit), key ≈ A, ~137 BPM
# music edit: (video start, track start, video end). Quiet intro under Intro/Problem, the drive kicks in
# exactly on the Use-case cut (13.5 s), a half-second stop-down before the reveal, then the drop at 42.0 s
# lands on a phrase downbeat of the track (44.70 s), and everything stops on the final hit at 46.5 s.
MUSIC_EDIT = [(0.0, 0.5, 41.5), (42.0, 44.70, 46.5)]

KOKORO_VOICE, KOKORO_SPEED = 'am_michael', 0.9
# ───────────────────────── voice-over cues (start s, text, max length s) ─────────────────────────
VO = [
    (1.30,  "Meet Soul.", 3.2),
    (5.80,  "Every day, you talk to AI...", 2.4),
    (8.30,  "In a chat box.", 1.6),
    (10.20, "AI has a brain.", 1.75),
    (12.00, "Now, it has a soul.", 1.5),
    (14.10, "It lives on your desk.", 3.2),
    (21.90, "Hold the glass.", 2.4),
    (24.85, "Type. Talk. Remember.", 2.6),
    (27.70, "Claude asks.", 1.55),
    (29.30, "You approve.", 1.6),
    (31.20, "Works with the AI you already have.", 2.7),
    (37.45, "Sleeps in its egg.", 2.0),
    (42.45, "Soul.", 1.5),
    (44.70, "From two hundred forty-nine euros.", 2.25),
    (47.00, "Join the waitlist.", 1.2),
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

# ───────────────────────── music bed (licensed track, edited) ─────────────────────────
def load_track():
    mp3 = TMP / 'music_464.mp3'
    if not mp3.exists():
        req = urllib.request.Request(MUSIC_URL, headers={'User-Agent': 'Mozilla/5.0'})
        mp3.write_bytes(urllib.request.urlopen(req).read())
    b = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(mp3), '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, np.float32).reshape(-1, 2).astype(np.float64)

def make_bed():
    tr = load_track(); bed = np.zeros((N, 2)); fade = int(.012 * SR)
    b, a = iirnotch(14048, 30, SR); tr = filtfilt(b, a, tr, axis=0)      # tame a steady 14 kHz whine in the source
    for v0, s0, v1 in MUSIC_EDIT:
        seg = tr[t2i(s0):t2i(s0) + t2i(v1 - v0)].copy()
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]; seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        add(bed, seg, v0)
    # dynamics automation: fade in, sit lower under the dark night shot, filter-close into the stop-down
    g = np.interp(np.arange(N) / SR, [0, 1.2, 13.4, 13.5, 36.9, 37.1, 39.4, 41.5, 42.0, 49],
                  [0, .6, .6, 1, 1, .7, .7, .9, 1, 1])
    bed *= g[:, None]
    i0, i1 = t2i(37.0), t2i(41.5)          # low-pass sweep closing over the night shot + build
    dark = lp(bed[i0:i1], 900, 2); w = np.linspace(0, 1, i1 - i0)[:, None] ** .7
    bed[i0:i1] = bed[i0:i1] * (1 - w) + dark * w
    # last hit at 46.5: cut the bed with a short ring-out
    j = t2i(46.5); bed[j:] = 0
    return bed

# ───────────────────────── trailer layer (synthesized) ─────────────────────────
A1 = 55.0
def braam(d=3.2, gain=.5, root=A1):
    t = tt(d); n = len(t); x = np.zeros(n)
    for f, a in [(root, 1), (root * 2, .8), (root * 3, .45), (root * 4, .3), (root * 1.5 * 2, .35)]:
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
def tom(gain=.35, f0=95):
    t = tt(.9); fr = f0 * (1 + .5 * np.exp(-t / .03)); ph = 2 * np.pi * np.cumsum(fr) / SR
    x = np.sin(ph) * np.exp(-t / .22) + .3 * bp(rng.standard_normal(len(t)), 200, 1500) * np.exp(-t / .04)
    return reverb(st(np.tanh(1.3 * x) * gain, 0), .4)
def subdrop(d=1.4, gain=.55):
    t = tt(d); f = 30 + 55 * np.exp(-t / .35); ph = 2 * np.pi * np.cumsum(f) / SR
    return st(np.sin(ph) * np.exp(-t / .7) * gain, 0)
def revcym(d=1.3, gain=.35):
    n = int(d * SR); t = np.arange(n) / n
    x = hp(rng.standard_normal(n), 4000, 2) * (np.exp(4 * t) - 1) / (np.e ** 4 - 1)
    x[-int(.004 * SR):] *= np.linspace(1, 0, int(.004 * SR))
    return np.stack([x, np.roll(x, 60)], 1) * gain

def make_trailer_layer():
    s = np.zeros((N, 2))
    add(s, impact(.2, 48, .15), 0.15)                     # card opens
    add(s, impact(.28, 45, .2), 5.5)                      # Problem
    add(s, swell(1.5, .55), 10.5); add(s, revcym(1.2, .3), 10.75)
    add(s, impact(.5), 11.95)                             # "Now it has a soul"
    add(s, revcym(1.0, .4), 12.5); add(s, braam(3.0, .75), 13.5); add(s, impact(.8), 13.5)   # drive kicks in
    for tc in (17.5, 21.5, 24.5, 27.5, 31.0, 34.0):       # taiko-style accents on the cuts
        add(s, tom(.38, 92), tc); add(s, tom(.25, 70), tc + .11)
    add(s, impact(.4, 40, .15), 37.0)                     # night
    add(s, riser(2.4, .42), 39.55); add(s, revcym(1.6, .45), 40.4)
    add(s, braam(3.6, 1.0), 42.0); add(s, impact(1.1, 38, .5), 42.0); add(s, subdrop(1.6, .7), 42.0)   # DROP / reveal
    add(s, braam(3.0, 1.0, A1), 46.5); add(s, impact(1.1, 36, .55), 46.5); add(s, subdrop(1.8, .7), 46.5) # ending hit
    return s

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
    for tc, g in [(5.5, .3), (10.0, .22), (13.5, .4), (17.1, .3), (17.5, .3), (19.35, .4), (21.5, .3),
                  (24.5, .3), (27.5, .3), (31.0, .3), (34.05, .25), (37.0, .25), (39.5, .3), (9.45, .25)]:
        add(s, whoosh(gain=g, pan=(-.5, .5) if int(tc * 2) % 2 else (.5, -.5)), tc - .3)
    for i in range(5): add(s, whoosh(.4, 600, 6000, .14, (.8, -.2)), 34.1 + i * .11 - .05)
    l1 = 'Every day, you talk to AI…'
    for k in range(1, len(l1) + 1): add(s, click(.1 if l1[k - 1] == ' ' else .17), 5.5 + (k + 3) / 15)
    l2 = '…in a chat box.'
    for k in range(1, len(l2) + 1): add(s, click(.1 if l2[k - 1] == ' ' else .17), 8.25 + k / 15)
    pent = [81, 84, 86, 88, 91, 93, 96, 98, 100]          # A minor pentatonic, to sit in the track's key
    for i in range(0, 12, 2): add(s, pop(pent[i // 2], .08, (i - 6) / 8), .3 + i * .06 + .12)
    for i in range(5): add(s, pop(pent[i], .13, (i - 2) / 3), 5.5 + 1.2 + i * .13 + .1)
    add(s, pop(86, .16), 10 + .75 + .12)
    add(s, pop(93, .18), 10 + 2.95 + .12)
    for i in range(3): add(s, pop(pent[5 + i], .1, (i - 1) / 2), 13.0 + i * .08 + .1)
    for i in range(3): add(s, pop(pent[2 + i], .16), 24.5 + .5 + i * .78 + .1)
    for i in range(3): add(s, pop(pent[5 + i], .1, (i - 1) / 2), 22.85 + .15 + i * .1 + .1)
    add(s, pop(93, .16), 27.5 + 1.75 + .2 + .1)
    for i in range(4): add(s, pop(pent[2 + i], .2, (i - 1.5) / 2), 31 + .8 + i * .2 + .12)
    add(s, pop(88, .18), 41.85 + 3.35 + .12)
    add(s, shimmer(1.6, .05, (93, 100, 105)), 12.75)
    for tb in [19.55 + .72, 19.55 + 1.6, 19.55 + 1.82, 27.5 + 1.32, 41.85 + 1.78, 41.85 + 3.97, 46.5 + 1.63]: add(s, tick(.09), tb)
    for tp in [22.85, 29.25, 45.95]: add(s, tap(.26), tp - .02)
    add(s, shimmer(3.2, .07, (81, 88, 93, 100, 105)), 42.15)
    add(s, shimmer(2.2, .04, (81, 88, 93, 100)), 46.75)
    return s

# ───────────────────────── voice-over (Kokoro) ─────────────────────────
def trim(x, thr=.008):
    idx = np.nonzero(np.abs(x) > thr)[0]
    if len(idx) == 0: return x
    a = max(0, idx[0] - int(.01 * SR)); b = min(len(x), idx[-1] + int(.08 * SR)); return x[a:b]
def make_vo():
    from kokoro import KPipeline
    pipe = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
    bus = np.zeros(N); report = []
    for i, (t0, text, mx) in enumerate(VO):
        sp = KOKORO_SPEED
        for attempt in range(6):
            x = np.concatenate([np.asarray(a, dtype=np.float64) for _, _, a in pipe(text, voice=KOKORO_VOICE, speed=sp)])
            x = trim(resample_poly(x, 2, 1))           # 24 kHz → 48 kHz
            if len(x) / SR <= mx or sp > 1.15: break
            sp *= 1.05
        x = x / (np.abs(x).max() + 1e-9) * .7
        x[:int(.004 * SR)] *= np.linspace(0, 1, int(.004 * SR))
        add(bus, x, t0); report.append((t0, text, round(len(x) / SR, 2), mx, round(sp, 3)))
    raw = TMP / 'vo_raw.wav'; write_wav(raw, st(bus, 0) * np.sqrt(2))
    out = TMP / 'vo_fx.wav'
    # voice chain: low cut 80 Hz, presence +2 dB @ 4 kHz, a little low-mid cleanup, compression, subtle room
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-af',
                    'highpass=f=80:poles=2,equalizer=f=120:t=q:w=1:g=1.5,equalizer=f=350:t=q:w=1.2:g=-2,'
                    'equalizer=f=4000:t=q:w=1.2:g=2,equalizer=f=10000:t=q:w=1:g=1,'
                    'acompressor=threshold=-22dB:ratio=3.5:attack=6:release=140:makeup=2.5,'
                    'aecho=0.85:0.55:32|58:0.10|0.06', '-ar', str(SR), str(out)], check=True)
    vo, _ = read_wav_st(out)
    vo = vo[:N] if len(vo) >= N else np.pad(vo, ((0, N - len(vo)), (0, 0)))
    return vo, report

def write_wav(p, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
def read_wav_st(p):
    with wave.open(str(p)) as w:
        ch = w.getnchannels(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
        return x.reshape(-1, ch), w.getframerate()

def asr_check(path):
    """ASR round-trip on the voice stem (faster-whisper) to confirm the lines are intelligible."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print('faster-whisper not installed; skipping ASR check'); return
    m = WhisperModel('base.en', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(str(path), beam_size=5, word_timestamps=False, vad_filter=False)
    for sg in segs: print(f'ASR {sg.start:6.2f}-{sg.end:6.2f}  {sg.text.strip()}')

# ───────────────────────── mix ─────────────────────────
def main():
    vo, report = make_vo()
    for r in report: print('VO %6.2fs  %-40s %.2fs (max %.1f, speed %.3f)' % r)
    bed = make_bed(); trailer = make_trailer_layer(); sfx = make_sfx()
    # ducking gain from the voice (~-7 dB), smooth attack/release
    e = np.abs(vo).max(1); k = int(.03 * SR)
    e = np.convolve(e, np.ones(k) / k, 'same'); on = (e > .02).astype(float)
    g = np.ones(N); cur = 1.0; att = 1 - np.exp(-1 / (.05 * SR)); rel = 1 - np.exp(-1 / (.30 * SR))
    tgt = 1 - (1 - db(-7)) * on
    for i in range(N):
        cur += (tgt[i] - cur) * (att if tgt[i] < cur else rel); g[i] = cur
    music = bed * db(-2) + trailer * db(-1)
    # the bed ducks under the voice; the trailer hits only partly, so the drops keep their punch
    mix = bed * db(-2) * g[:, None] + trailer * db(-1) * np.sqrt(g)[:, None] + sfx * db(-6) + vo * db(1.5)
    fe = np.ones(N); i0 = t2i(48.0); fe[i0:] = np.linspace(1, 0, N - i0) ** 1.5; mix *= fe[:, None]
    mix *= .9 / np.abs(mix).max()
    pre = TMP / 'mix_pre.wav'; write_wav(pre, mix)
    for name, x in (('music', music), ('sfx', sfx), ('vo', vo)): write_wav(TMP / f'stem_{name}.wav', x / (np.abs(x).max() + 1e-9) * .9)
    asr_check(TMP / 'stem_vo.wav')
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(pre), '-af', 'loudnorm=I=-14:TP=-2:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr).group(0))
    final = TMP / 'mix_final.wav'
    af = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(pre), '-af', af, '-ar', str(SR), str(final)], check=True)
    if os.environ.get('NO_MUX'): return
    for v in ('soul_trailer.mp4', 'soul_trailer_vertical.mp4'):
        src = HERE / v; tmp = TMP / ('mux_' + v)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-i', str(final), '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-ar', str(SR), '-shortest', '-movflags', '+faststart', str(tmp)], check=True)
        os.replace(tmp, src); print('muxed', src)

if __name__ == '__main__':
    main()
