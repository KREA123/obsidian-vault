# SoulOS 5 · Glass

The design language that replaces "Orbit" (SoulOS 3/4) on the web prototype (`os/index.html` = `site/os.html`)
and in the firmware (`firmware/lib/Suflet/src/Glass.*`, `OsDraw.cpp`). The founder's two rules:

1. **Glassmorphism, premium.** Words sit on frosted glass over a soft colour field, never on flat black boxes.
2. **Standby is the eyes alone.** When SOUL is idle, or you are not using SoulOS, the round screen is pure
   black with the two eyes on it: no clock, no rings, no hints. Any UI appears only when you interact, and
   fades back to the eyes after a short idle.

The eyes engine (`eyes/eyes.js`, `EyeRender.cpp`) is not touched: the glass is built around it.

## 1 · States

| State | What is on the glass | Enters | Leaves |
|---|---|---|---|
| **Standby** | Eyes only, true black (`#000`). No aura, no status ring, no clock, no rim light (a pending Claude request is shown by the eyes: wide, looking at you). | Boot done; any screen left alone for `APP_IDLE_MS`; home after `PEEK_MS` | a touch, the wheel/crown, an event (notification, alarm, charger) |
| **Peek** | Standby + the aura + one glass capsule on the top rim (time · date · status) + the home hint/tag; the battery/Claude rim marks. | a touch on the face in standby | `PEEK_MS` = 4 s without a touch |
| **Screen** | The eyes step back (scale down to the top, -10 % brightness), the aura rises behind them, the screen's words sit on glass. | opening anything | side button / swipe ↓ / `APP_IDLE_MS` = 15 s idle (except while listening, typing, a running timer, the dial, ringing, a game) |
| **Event** | A notification capsule slides along the rim over the aura; the charger shows a mint glass dial. | the event | its own timer |
| **Asleep** | The sleeping eyes only (dimmed); no always-on clock. | 45 s idle, face down | a touch, pick-up |

## 2 · The aura

Deep near-black with three big soft glows and one state glow, slowly drifting; it leans a few pixels
against the tilt (IMU on the device, pointer / `deviceorientation` on the web).

| Token | Value | Where |
|---|---|---|
| `--au-base` | `#05050A` | the field |
| `--au-ember` | `rgb(255,138,61)` · peak α .50 · Ø 360 px · lower left | drifts 27 s |
| `--au-night` | `rgb(39,71,184)` · α .72 · Ø 400 px · upper right | drifts 33 s |
| `--au-lilac` | `rgb(154,127,224)` · α .42 · Ø 280 px · lower right | drifts 23 s |
| `--acc` (state glow) | Ø 330 × 300 px · top centre (behind the eyes) · α .40 | drifts 19 s |
| tone: default | `rgb(255,179,71)` amber-gold (SOUL) | |
| tone: `ice` (listening, dictation, boot "hold the glass") | `rgb(127,178,255)` | |
| tone: `amber` (needs you: Claude asks, alarm ringing, amber notification) | `rgb(255,162,58)` | |
| tone: `mint` (done: an answer, a mint notification, focus done, charging) | `rgb(127,227,192)` | |
| grain | fractal noise, 7 % overlay (web) · 4×4 ordered dither (device) | keeps the dark gradients from banding |
| parallax | ±12 px (web) · ±10 px (device), eased (rate 4/s) | |
| fade in / out | 420 ms | |

Glow falloff: `radial-gradient(circle, c·α 0 %, c·α/3 ≈ 45 %, transparent 70 %)`; on the device
`(1 − (d/R)²)²`, then a 3-pass box blur at ¼ resolution (that is the "blurred once per aura change").

## 3 · Glass

Glass = a translucent white fill over the (already blurred) aura + a 1 px edge that catches the light at the
top-left + a soft drop shadow, rounded to the round screen (concentric capsules and bands on the rim).

| Token | Web | Device |
|---|---|---|
| fill | `linear-gradient(155deg, rgba(255,255,255,.15), rgba(255,255,255,.06) 64%)` | 15 % → 6 % white over the *frosted* aura buffer, 8 gradient steps via LUTs |
| fill, pressed / selected | `.24 → .10` | +9 % |
| edge (top-left light) | `inset 1.25px 1.25px 0 -.25px rgba(255,255,255,.46)` | 1.5 px band, α .46 × (0.25 + 0.75 · max(0, n·L)), L = top-left |
| edge (bottom-right) | `inset -1px -1px 0 rgba(255,255,255,.07)` + `inset 0 0 0 1px rgba(255,255,255,.07)` | α .07 floor |
| shadow | `0 18px 34px -16px rgba(0,0,0,.8), 0 3px 10px -3px rgba(0,0,0,.4)` | 10 px falloff, offset +5 px, ×0.55 darkening |
| accent glow (amber / mint / ice) | `0 0 46px -8px` of the tone + `inset 0 0 0 1px` tinted edge | 14 px outer glow of the tone, tinted edge |
| radius: card / sheet | 30 px / 36 px | 30 / 36 design px |
| radius: row / key / pill | 22 px / 14 px / 999 px | same |
| rim capsule | centre radius 204 (top titles), 192 (bottom actions), half-width 17–22 | same geometry (`capsuleArc`) |
| ink on glass | `#FFF6E4`; secondary `rgba(255,244,222,.66)`; faint `.42` | cream `#FFF0C8`, α .66 / .42 |

Why no live backdrop blur: the aura is already a blur, so a translucent fill over it reads as frosted glass;
on the device a real-time blur is out of budget, so both use the same model (a pre-blurred "frosted" field +
fill + edge) and look alike.

## 4 · Components

| Component | Glass treatment |
|---|---|
| Rim title / status | glass capsule bent along the top rim (`capD(204, 17, …)`), mono caps inside |
| Actions ("Snooze", "Type", a reply) | glass capsule buttons, 50 px high, 22 px padding; ok = mint glow, warn = amber glow (no more underlines) |
| Lists (reminders, notes, alarms) | each row a glass slab (radius 22), 8 px apart |
| Toggles | a glass track (62 × 34) with a light inside; on = mint track + glowing mint knob |
| Settings / AI picker | one glass sheet (radius 30), rows split by 1 px hairlines; the chosen brain in an amber glass lens |
| Launcher (the orbit) | the app names ride a glass band on the lower rim; the chosen one sits in a brighter glass lens; its live fact in a glass card in the middle |
| Keyboard | glass keycaps (radius 14), the field a glass capsule, suggestions in glass pills, ✓/↑ glass orbs with a glow |
| Claude's ask | a glass sheet with an amber glow (the command in mono), amber aura, "hold = yes · 2× = no" on an amber rim capsule |
| Answers, messages, About | a glass card |
| Notifications | a glass capsule that slides along the top rim (bottom rim while the keyboard is up), tinted edge per kind |
| Alarm dial, Focus | a glass annulus (the track) with the ticks on it; the knob a dark glass orb |
| Timer / music controls | glass orbs |
| Control | glass tiles; light and volume stay rim dials |
| Today | glass cards stacked like a teleprompter |
| Onboarding | glass capsules for names, the brain picker a glass sheet |

## 5 · Type

Bricolage Grotesque (display, the voice) + Martian Mono (rim labels, numbers in small caps) on the web.
The device's bitmap atlas is Nunito (`Font.cpp`, `FontData.h`) at three sizes + digits; that difference is
older than Glass and kept (the atlas is generated by `firmware/tools/gen_font.py`).
Hierarchy: one big thing per screen (34–104 px), one secondary line (20–24 px, 66 %), captions in mono caps
(12–15 px, .12–.16 em tracking, 42–66 %). Generous spacing: 12–24 px inside glass, 8 px between rows.

## 6 · Motion

- Glass in: fade + scale .94 → 1 (spring, settles ≤ 220 ms); out: the card spring.
- The aura fades in/out in 420 ms; it drifts on 19–33 s loops; parallax is a translate (cheap).
- The eyes always go back to centre stage (full size) in standby; on a screen they spring to the top.
- Peek fades in in 180 ms, out in 320 ms.
- `prefers-reduced-motion`: no drift, no parallax.

## 7 · Device implementation (firmware v1.4.0)

- `Glass.h/.cpp`: `GlassLayer` owns two PSRAM buffers of (W + 2M)² RGB565 (M = 12 px margin for the
  drift/parallax translate): the **aura** and the **frosted** aura. They are rebuilt only when the tone
  changes: glows at ¼ resolution → 3-pass box blur (aura) / 6-pass (frosted) → bilinear upscale with a 4×4
  ordered dither into 565. Drift + tilt only move the read offset (≤ 4 Hz, ≥ 1 px change) and repaint.
- Painting: `background()` copies aura rows under the clip; `panel()` / `capsuleArc()` / `band()` /
  `orb()` evaluate a cheap SDF per pixel and blend the frosted buffer with white through per-panel LUTs
  (8 gradient steps × 32/64/32 entries), an edge term from the SDF normal, an outer shadow and glow.
  No heap per frame; the dirty-rect composer is unchanged.
- Standby: `render()` does a black fill as before (no aura), the home screen draws nothing unless peeking.
- Numbers (callgrind, instructions per frame vs v1.3.0) are in `firmware/BRINGUP.md`.
