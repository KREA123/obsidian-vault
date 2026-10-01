#!/usr/bin/env python3
"""SOUL trailer soundtrack (v3): licensed music bed + synthesized trailer layer + SFX + TTS voice-over.

- Music bed: "Sci-Fi Score" by Arulo, Mixkit (Mixkit Stock Music Free License: commercial use, no
  attribution required). See MUSIC-LICENSE.md. The mp3 is downloaded at build time and not committed
  (the licence forbids redistributing it as a standalone file).
- Trailer layer (braams, impacts, sub drops, risers, reversed cymbals, toms) and UI SFX are synthesized here.
- Voice: one short line per scene, each starting on a beat, read by a Microsoft neural voice through edge-tts
  (en-US-AvaMultilingualNeural, chosen to match the founder's reference ad), checked with faster-whisper.
  VOICE_FILE=/path/voice.wav (a full recorded track timed to the video from 0 s) replaces the TTS.
- Light voice processing (low cut + gentle compression), music ducks ~7 dB under the voice,
  loudnorm to -14 LUFS / -2 dBTP, AAC 192k into both mp4s. Also writes voiceover_script.md.

Timing: cues below are written in the authoring timeline of soul_trailer.html (0-49 s) and mapped through
the same beat-grid warp (WARP_OLD -> WARP_BEATS) that the page uses, so every cut sits on a beat.
usage: python3 audio.py      env: AUDIO_TMP (scratch dir), VOICE_FILE (optional), NO_MUX (skip muxing)
"""
import os, json, wave, subprocess, pathlib, re, urllib.request
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly, iirnotch, filtfilt

HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path(os.environ.get('AUDIO_TMP', '/tmp/soul_audio')); TMP.mkdir(parents=True, exist_ok=True)
SR = 48000
rng = np.random.default_rng(7)

# ── beat grid / time warp (must match soul_trailer.html) ──
BEAT = 7.004 / 16                       # track tempo ≈ 137.07 BPM; a 16-beat phrase = 7.004 s
WARP_OLD   = [0, 5.5, 10.0, 13.5, 17.5, 19.55, 21.5, 24.5, 27.5, 31.0, 34.0, 37.0, 39.5, 42.0, 46.5, 49.0]
WARP_BEATS = [0, 12,  20,   28,   36,   40,    44,   50,   56,   64,   74,   80,   86,   92,   102,  108]
WARP_NEW = [b * BEAT for b in WARP_BEATS]
def nt(t_old): return float(np.interp(t_old, WARP_OLD, WARP_NEW))   # authoring time -> video time
T_END = WARP_NEW[-1]                    # ≈ 47.28 s
REVEAL_BEAT, END_BEAT = 92, 102         # logo reveal (drop) and end-card hit
N = int(round(SR * T_END))

MUSIC_URL = 'https://assets.mixkit.co/music/464/464.mp3'   # "Sci-Fi Score" by Arulo (Mixkit), key ≈ A
TRACK_DOWNBEAT = 16.682                 # a phrase downbeat in the track where the drive is already going
# music edit (video start, track start, video end), all on the beat grid: full energy from frame 0,
# one-beat stop-down before the logo reveal, the drop lands on a later phrase downbeat,
# and the bed stops on the end-card hit.
MUSIC_EDIT = [(0.0, TRACK_DOWNBEAT, (REVEAL_BEAT - 1) * BEAT), (REVEAL_BEAT * BEAT, TRACK_DOWNBEAT + 6 * 7.004, END_BEAT * BEAT)]

# ── voice-over: one short line per scene, each starting on a beat (beat index, text, on-screen note) ──
TTS_VOICE = os.environ.get('TTS_VOICE', 'en-US-AvaMultilingualNeural')   # Microsoft neural voice via edge-tts
TTS_RATE, TTS_PITCH = '+10%', '+10Hz'
def tts_say(text): return text.replace('Claude', 'Clawd')   # phonetic spelling: the voice mispronounces 'Claude'
VO_LINES = [
    (2,   "Meet Soul.",                              "SOUL title"),
    (6,   "A little device, with a soul.",           "A LITTLE DEVICE WITH A SOUL"),
    (12,  "Every day, you talk to AI.",              "typewriter line"),
    (17,  "In a chat box.",                          "typed into the chat box"),
    (20,  "AI has a brain.",                         ""),
    (24,  "Now, it has a soul.",                     "'soul' turns amber"),
    (29,  "It lives on your desk.",                  "collage orbit"),
    (36,  "Always on. Never in the way.",            "hero push-in"),
    (40.5, "It looks back.",                         "live eyes blink"),
    (44,  "Hold the glass. It listens.",             "finger-tap ripple"),
    (50.7, "Type.",                                  "word 1"),
    (52.3, "Talk.",                                  "word 2"),
    (53.8, "Remember.",                              "word 3"),
    (56,  "Claude asks.",                            "approval card"),
    (60,  "You approve.",                            "after the Approve tap"),
    (64,  "Works with the AI you already have.",     ""),
    (68.3, "Claude. ChatGPT. Your key.",             "the four pills (No AI · Claude · ChatGPT · Your key)", '+20%'),
    (74,  "Five colours. One soul.",                 "family"),
    (80,  "It sleeps in its egg.",                   "night shot"),
    (92.5, "Soul. From two hundred forty-nine euros.", "logo reveal on the drop, then From €249"),
    (99,  "Join the waitlist.",                      "waitlist button"),
    (102.6, "Designed in Romania.",                  "end card"),
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
def addo(bus, x, t_old): add(bus, x, nt(t_old))   # place at an authoring-timeline time
def addend(bus, x, t_new_end): add(bus, x, t_new_end - len(x) / SR)   # place so it ends exactly at a video time

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
    tr = load_track(); bed = np.zeros((N, 2)); fade = int(.004 * SR)
    b, a = iirnotch(14048, 30, SR); tr = filtfilt(b, a, tr, axis=0)      # tame a steady 14 kHz whine in the source
    for v0, s0, v1 in MUSIC_EDIT:
        seg = tr[t2i(s0):t2i(s0) + t2i(v1 - v0)].copy()
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]; seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        add(bed, seg, v0)
    # dynamics: full from frame 0; dip slightly under the night shot, filter-close into the stop-down
    g = np.interp(np.arange(N) / SR, [0, nt(36.9), nt(37.1), nt(39.4), (REVEAL_BEAT - 1) * BEAT, REVEAL_BEAT * BEAT, T_END],
                  [1, 1, .75, .75, .9, 1, 1])
    bed *= g[:, None]
    i0, i1 = t2i(nt(37.0)), t2i((REVEAL_BEAT - 1) * BEAT)  # low-pass sweep closing over the night shot + S o u l build
    dark = lp(bed[i0:i1], 900, 2); w = np.linspace(0, 1, i1 - i0)[:, None] ** .7
    bed[i0:i1] = bed[i0:i1] * (1 - w) + dark * w
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
    addo(s, impact(.55, 44, .3), 0.0); addo(s, braam(2.6, .55), 0.0)   # frame 0: downbeat hit
    addo(s, impact(.4, 45, .25), 5.5)                      # Problem
    addend(s, swell(1.5, .55), nt(11.95)); addend(s, revcym(1.2, .3), nt(11.95))
    addo(s, impact(.5), 11.95)                             # "Now it has a soul"
    addend(s, revcym(1.0, .4), nt(13.5)); addo(s, braam(3.0, .75), 13.5); addo(s, impact(.8), 13.5)   # drive kicks in
    for tc in (17.5, 21.5, 24.5, 27.5, 31.0, 34.0):       # taiko-style accents on the cuts
        addo(s, tom(.38, 92), tc); addo(s, tom(.25, 70), tc + .11)
    addo(s, impact(.4, 40, .15), 37.0)                     # night
    addend(s, riser(2.4, .42), (REVEAL_BEAT - 1) * BEAT); addend(s, revcym(1.6, .45), REVEAL_BEAT * BEAT)   # build → 1-beat stop-down
    addo(s, braam(3.6, 1.0), 42.0); addo(s, impact(1.1, 38, .5), 42.0); addo(s, subdrop(1.6, .7), 42.0)   # DROP / reveal
    addo(s, braam(3.0, 1.0, A1), 46.5); addo(s, impact(1.1, 36, .55), 46.5); addo(s, subdrop(1.8, .7), 46.5) # ending hit
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
        addo(s, whoosh(gain=g, pan=(-.5, .5) if int(tc * 2) % 2 else (.5, -.5)), tc - .3)
    for i in range(5): addo(s, whoosh(.4, 600, 6000, .14, (.8, -.2)), 34.1 + i * .11 - .05)
    l1 = 'Every day, you talk to AI…'
    for k in range(1, len(l1) + 1): addo(s, click(.1 if l1[k - 1] == ' ' else .17), 5.5 + (k + 3) / 15)
    l2 = '…in a chat box.'
    for k in range(1, len(l2) + 1): addo(s, click(.1 if l2[k - 1] == ' ' else .17), 8.25 + k / 15)
    pent = [81, 84, 86, 88, 91, 93, 96, 98, 100]          # A minor pentatonic, to sit in the track's key
    for i in range(0, 12, 2): addo(s, pop(pent[i // 2], .08, (i - 6) / 8), .3 + i * .06 + .12)
    for i in range(5): addo(s, pop(pent[i], .13, (i - 2) / 3), 5.5 + 1.2 + i * .13 + .1)
    addo(s, pop(86, .16), 10 + .75 + .12)
    addo(s, pop(93, .18), 10 + 2.95 + .12)
    for i in range(3): addo(s, pop(pent[5 + i], .1, (i - 1) / 2), 13.0 + i * .08 + .1)
    for i in range(3): addo(s, pop(pent[2 + i], .16), 24.5 + .5 + i * .78 + .1)
    for i in range(3): addo(s, pop(pent[5 + i], .1, (i - 1) / 2), 22.85 + .15 + i * .1 + .1)
    addo(s, pop(93, .16), 27.5 + 1.75 + .2 + .1)
    for i in range(4): addo(s, pop(pent[2 + i], .2, (i - 1.5) / 2), 31 + .8 + i * .2 + .12)
    addo(s, pop(88, .18), 41.85 + 3.35 + .12)
    addo(s, shimmer(1.6, .05, (93, 100, 105)), 12.75)
    for tb in [19.55 + .72, 19.55 + 1.6, 19.55 + 1.82, 27.5 + 1.32, 41.85 + 1.78, 41.85 + 3.97, 46.5 + 1.63]: addo(s, tick(.09), tb)
    for tp in [22.85, 29.25, 45.95]: addo(s, tap(.26), tp - .02)
    addo(s, shimmer(3.2, .07, (81, 88, 93, 100, 105)), 42.15)
    addo(s, shimmer(2.2, .04, (81, 88, 93, 100)), 46.75)
    return s

# ───────────────────────── voice track (TTS or external VOICE_FILE) ─────────────────────────
def load_voice(path):
    """Load a voice track (any format ffmpeg reads), apply light processing (low cut 80 Hz, gentle
    compression) and return it as a stereo array aligned to video time 0."""
    out = TMP / 'voice_fx.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(path), '-ac', '2', '-ar', str(SR), '-af',
                    'highpass=f=80:poles=2,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=150:makeup=1.5',
                    str(out)], check=True)
    v, _ = read_wav_st(out)
    v = v[:N] if len(v) >= N else np.pad(v, ((0, N - len(v)), (0, 0)))
    return v / (np.abs(v).max() + 1e-9) * .7

def tc(t):  # 00:00.00
    return f'{int(t // 60):02d}:{t % 60:05.2f}'
def write_script(durs):
    rows = ['# SOUL trailer v3: voice-over script',
            '',
            f'Timeline: `soul_trailer.mp4` / `soul_trailer_vertical.mp4`, {T_END:.2f} s, music at ~137 BPM (one beat = {BEAT:.3f} s).',
            'Each line starts on a beat, right on its cut, one short line per scene, in the style of the reference ad.',
            f'The current mix uses the Microsoft neural voice `{TTS_VOICE}` (edge-tts, rate {TTS_RATE}, pitch {TTS_PITCH}).',
            'To replace it with a real voice (ElevenLabs or a human), record these lines to these timecodes. **End** is the',
            'latest each line may run (the next line or cut); "TTS length" is how long the current synthetic read takes.',
            '',
            '| # | Start | End (max) | TTS length | Line | On screen |',
            '|---|---|---|---|---|---|']
    starts = [ln[0] * BEAT for ln in VO_LINES]
    for i, ((b, text, note, *_), t0) in enumerate(zip(VO_LINES, starts), 1):
        t1 = starts[i] if i < len(starts) else T_END - .6
        rows.append(f'| {i} | {tc(t0)} | {tc(t1)} | {durs[i-1]:.2f} s | {text} | {note} |')
    rows += ['',
             '**How to drop a recorded voice in:** export one WAV/MP3 of the whole voice track, starting at 00:00.00 and',
             'timed to the video. Then run `VOICE_FILE=/path/voice.wav python3 audio.py`. That replaces the TTS: a gentle',
             'low cut and compression, the music ducks about 7 dB under the voice, -14 LUFS, and both mp4s are re-muxed.', '']
    (HERE / 'voiceover_script.md').write_text('\n'.join(rows))

# ───────────────────────── TTS voice (edge-tts) ─────────────────────────
def tts_line(i, text, rate=None):
    rate = rate or TTS_RATE; text = tts_say(text)
    mp3 = TMP / f'tts_{TTS_VOICE}_{i:02d}.mp3'
    key = TMP / f'tts_{TTS_VOICE}_{i:02d}.txt'
    sig = f'{text}|{rate}|{TTS_PITCH}'
    if not (mp3.exists() and key.exists() and key.read_text() == sig):
        subprocess.run(['edge-tts', '--voice', TTS_VOICE, f'--rate={rate}', f'--pitch={TTS_PITCH}', '--text', text,
                        '--write-media', str(mp3)], check=True, capture_output=True)
        key.write_text(sig)
    b = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(mp3), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True, check=True).stdout
    x = np.frombuffer(b, np.float32).astype(np.float64)
    idx = np.nonzero(np.abs(x) > .01)[0]                     # trim edge silence so the line starts on the beat
    if len(idx): x = x[max(0, idx[0] - int(.005 * SR)): idx[-1] + int(.06 * SR)]
    return x
def make_tts():
    bus = np.zeros(N); durs = []
    for i, (b, text, _, *opt) in enumerate(VO_LINES):
        x = tts_line(i, text, opt[0] if opt else None); x = x / (np.abs(x).max() + 1e-9) * .7
        add(bus, x, b * BEAT); durs.append(len(x) / SR)
    raw = TMP / 'tts_raw.wav'; write_wav(raw, st(bus, 0) * np.sqrt(2))
    return raw, durs

def write_wav(p, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
def read_wav_st(p):
    with wave.open(str(p)) as w:
        ch = w.getnchannels(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
        return x.reshape(-1, ch), w.getframerate()
def asr_check(path):
    """ASR round-trip (faster-whisper) to confirm the voice lines are intelligible and on time."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print('faster-whisper not installed; skipping ASR check'); return
    m = WhisperModel('base.en', device='cpu', compute_type='int8', cpu_threads=2)
    segs, _ = m.transcribe(str(path), beam_size=5, vad_filter=False)
    for sg in segs: print(f'ASR {sg.start:6.2f}-{sg.end:6.2f}  {sg.text.strip()}')

# ───────────────────────── mix ─────────────────────────
def main():
    raw, durs = make_tts(); write_script(durs)
    for (b, text, *_), d in zip(VO_LINES, durs): print(f'VO {b * BEAT:6.2f}s (beat {b:5.1f})  {d:4.2f}s  {text}')
    bed = make_bed(); trailer = make_trailer_layer(); sfx = make_sfx()
    vf = os.environ.get('VOICE_FILE')         # a recorded voice replaces the TTS
    vo = load_voice(vf or raw)
    if not vf: asr_check(raw)
    g = np.ones(N)
    if True:   # ducking gain from the voice (~-7 dB), smooth attack/release
        e = np.abs(vo).max(1); k = int(.03 * SR)
        e = np.convolve(e, np.ones(k) / k, 'same'); on = (e > .02).astype(float)
        cur = 1.0; att = 1 - np.exp(-1 / (.05 * SR)); rel = 1 - np.exp(-1 / (.30 * SR))
        tgt = 1 - (1 - db(-7)) * on
        for i in range(N):
            cur += (tgt[i] - cur) * (att if tgt[i] < cur else rel); g[i] = cur
    # SFX sit under the music; the trailer hits ride on top of the bed
    mix = bed * db(-1) * g[:, None] + trailer * db(-1) * np.sqrt(g)[:, None] + sfx * db(-10) + vo * db(1.5)
    fe = np.ones(N); i0 = t2i(nt(48.2)); fe[i0:] = np.linspace(1, 0, N - i0) ** 1.5; mix *= fe[:, None]
    mix *= .9 / np.abs(mix).max()
    pre = TMP / 'mix_pre.wav'; write_wav(pre, mix)
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
