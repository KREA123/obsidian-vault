# SoulOS Alive

The design language that replaces "Glass" (SoulOS 5, `DESIGN-GLASS.md`) on the web prototype
(`os/index.html` = `site/os.html`) and, next, in the firmware (`firmware/lib/Suflet/src`: `OsDraw.cpp`, `Glass.*`,
`SoulFace.*`). The founder, 2026-10-11: *"SoulOS has to match the product and the eyes. Everything is alive… except
the OS."* The frosted cards read like a generic smartwatch. In Alive, the OS looks like the eyes and the stone.

Five rules:

1. **The eyes are the OS.** They never leave. Standby is the eyes alone, full size, on pure black. When the OS
   wakes, the eyes glide up and shrink into the top of the circle, and they stay there as the face of every screen.
   They react to everything (§6).
2. **Same DNA as the eyes and the object.** Pure black ground. Flat, saturated colour. Chunky rounded shapes
   ("pebbles", the MĂRGĂRITAR outline). Thick strokes. Bricolage Grotesque for the voice, Martian Mono for the
   rim. No blur, no frost, no aura, no gradients. The only nod to the real glass is one 2 px specular highlight
   along the top edge of a pebble.
3. **Every SOUL's OS is its own.** The palette comes from the eye design the unit was born with (`designs.js`)
   and from its aluminium body colour (§2).
4. **Round-native.** The home is a dial of app pebbles that orbit the eyes. Labels follow the arc. Content uses
   the circle, never a rectangular phone layout cut off by the bezel.
5. **Buildable on the ESP32-S3.** Everything is a flat primitive: circle, ring, arc, rounded rect, superellipse
   pebble, line, text. That is cheaper than the Glass blur buffers (§8).

## 1 · States

| State | What the glass shows | Eyes (layout `k`, `cy`) |
|---|---|---|
| **Standby** | Only the eyes, on `#000`. No clock, no rings, no hints (unchanged). | `home` 1, 0 |
| **Wake** (a touch on the face) | The eyes glide up and shrink. The clock capsule rises on the top rim. One personality line appears under the eyes. After `PEEK_MS` = 4 s with no touch, everything goes back to standby. | `peek` 0.52, −0.17 |
| **Home dial** (swipe →, side button, wheel/crown) | A ring of app pebbles around the eyes. The focused pebble sits at the bottom. Its name curves along the arc above it, and its live fact is set under the eyes. | `apps` 0.44, −0.07 |
| **App screen** | The eyes sit small at the top of the circle. Content is laid out on pebbles below them. | `card` 0.30, −0.33 (per app: see `LAYOUT`) |
| **Face moment** (listening, thinking, answer, ringing, Claude's ask, notification over standby) | The eyes stay big, and the words sit on a pebble or a solid banner. | `listen` 0.70, −0.10 · `answer` 0.42, −0.26 |
| **Asleep** | The sleeping eyes, dimmed and breathing. | `sleep` 0.74, −0.07 |

`k` is the eye canvas scale (1 = standby size). `cy` is the vertical offset, as a fraction of the 466 px web
screen (= 480 px on the device). The eyes move between layouts on the critically damped spring in `Soul.update`:
K = 260, ζ = 0.78, which settles in about 0.35 s.

## 2 · Tokens: the born palette

`bornPalette(design, body)` in `index.html` computes these. The device does the same computation once, at birth
and whenever the body is changed in Look.

| Token | Derivation | Use |
|---|---|---|
| `--e1` | `design.white` (the eye colour), lifted until its relative luminance is ≥ 0.30 | Primary fills: default buttons, focused pebble, banners, selected rows, toggles on, rim ticks, the speech bubble |
| `--e2` | The pupil colour (L or R) with the highest *saturation × (1 − \|lightness − 0.5\|)*. If that is ≤ 0.22 (near-black or grey pupils), or `e1` is saturated (chroma ≥ 0.35) and the pupil's hue is within 28° of it, use instead `hsl(hue(e1) + 165°, 90 %, 60 %)`. Lifted to luminance ≥ 0.17. | Second accent: every 2nd dial pebble, list checks, a pressed button |
| `--b1` | The body colour (below), lifted to luminance ≥ 0.20 by raising HSL lightness. Saturation is held ≥ 0.5 for chromatic bodies. | Third accent: every 3rd dial pebble |
| `--on1/2/b` | `#0B0B0C` if the accent's luminance > 0.30, else `#FBF4E3` (brand Warm White) | Ink on a filled accent |
| `--peb` | `mix(#000, e1, 0.14)` | Every surface (rows, sheets, keys, capsules, the dial track) |
| `--peb2` | `mix(#000, e1, 0.23)` | Pressed or secondary surface, toggle track, function keys |
| `--pebe` | `mix(#000, e1, 0.40)` | 2.5–3 px edges (rim capsules, field, toggle track) |
| `--ink` | `#FBF4E3`; `--ink2` = 66 % alpha, `--ink3` = 42 % (82 / 62 % with large text) | Words |
| State colours | mint `#C9F2E4` = done · amber `#FFB347` = Claude / needs you · ice `#9FC6FF` = listening (unchanged semantics). Inks on them: `#06231B`, `#2A1700`, `#071A33`. | ok / warn / listening fills and edges |

**Bodies** (aluminium sRGB, `brand/logo/README.md`) and their lifted `--b1`: Silver `#CBCDCF` → `#CBCDCF`,
Graphite `#55575B` → `#7C7F85`, Midnight `#26324C` → `#587BC7`, Ember `#D2622C` → `#D2622C`,
Champagne `#D8C3A2` → `#D8C3A2`.

**Examples** (computed by the page):

| Birth | Eyes / pupils | Body | e1 | e2 | b1 | peb · peb2 · pebe |
|---|---|---|---|---|---|---|
| #001 Original | `#FFF0C8` / `#2440FF` `#FF5A1F` | Silver | `#FFF0C8` | `#FF5A1F` | `#CBCDCF` | `#24221C` `#3B372E` `#666050` |
| #013 Sunday Toast | `#FFD23A` / `#5A2A10` | Midnight | `#FFD23A` | `#3D95F5` | `#587BC7` | `#241D08` `#3B300D` `#665417` |
| #058 Sugar Cube | `#F4F4F4` / `#FF5A1F` `#2440FF` | Ember | `#F4F4F4` | `#FF5A1F` | `#D2622C` | `#222222` `#383838` `#626262` |
| #098 Lollipop | `#FFB3E6` / `#FF2E63` `#2440FF` | Silver | `#FFB3E6` | `#4D64FF` | `#CBCDCF` | `#241920` `#3B2935` `#66485C` |
| #102 Disco Ball | `#E8E8F0` / `#FF1F8F` `#2BD9FF` | Champagne | `#E8E8F0` | `#FF1F8F` | `#D8C3A2` | `#202022` `#353537` `#5D5D60` |

**Settings › My SOUL › Look** previews other births: ‹ › walks through all 120 designs, and the eyes swap during
a blink. It also sets the body (5 swatches, saved as `soulos-body`). A previewed birth is marked *preview* on the
dial's rim, and **Back to {name}** returns to the unit's own birth. The birth itself never changes: it comes from
the chip id, and only the demo "Rebirth" re-rolls it.

### Geometry (on 480 × 480; the web uses 466, × 1.03)

- Grid: the centre is (240, 240). The usable circle is r = 228. The rim text radius is 204–210.
- Pebble outline: a superellipse with n = 3.1 and aspect 90 : 101, 7 % narrower at the bottom (`PEB_D`).
  Rows and buttons use the asymmetric radius `22 26 24 20 / 24 20 26 22` px. Sheets use `30 34 32 28 / 32 28 34 30`.
- Strokes: 3 px (2.5 on rim capsules). The eyes' rim rings are now flat, 1.4× thicker, and have no glow.
- Type: Bricolage Grotesque 680 for titles (34 px), 560 for body (27), 640 in the speech bubble (19). Martian Mono
  500 for the rim (15, tracking 0.16 em). Numerals 700, tabular.
- Hit targets ≥ 52 px. Dial pebbles are 52 × 58 at rest and 78 × 87 when focused.

## 3 · Motion = the eyes' motion

| What | Timing |
|---|---|
| Eyes' layout (wake, open, close) | Spring K 260, ζ 0.78 (≈ 0.35 s). |
| Blink (eyes.js `Rig.closed`) | Close 80 ms (in-quad), hold 40 ms, open 170 ms (out-back 1.8). Double blink: the second starts 0.7 × open later. |
| Screen change | Card spring k 560, c 40 (≈ 200 ms, ≤ 6 % overshoot). "zoom" from the eyes: k 480, c 37. |
| Dial | Snap spring 95 / 17. A fling coasts with `vr` and lands on the detent `round(rot + vr / 3.2)`. Opening the dial: pebbles spread from the bottom, spring 300 / 32. |
| Breathing idle | Sheets, lists and the dial track swell 1.2 % over 5.5 s, the same period as the sleeping eyes' breath. |
| Speech | Rises with the eyes' spring (`cubic-bezier(.34,1.56,.64,1)`, 0.32 s). Stays 2.2–3.2 s. |
| Tilt parallax | Pointer or `deviceorientation` → ±12 px on the dial track, ±4 px on the eyes. Approach rate 4 / s. |
| Reduced motion | Layouts, cards and the dial snap. No breathing, no parallax, no speech animation. Blinks still happen (they are information). |

## 4 · Screens

- **Standby / wake / sleep**: §1. A face drag still squashes and moves the eyes directly (rubber band 110 px).
- **Home dial** (`launcherHTML`, `launcherFrame`): 18–27 apps (`ORB`, which can be reordered or hidden in Settings ›
  Apps). Pebbles sit on r = 170 every 28°, coloured `e1`, `e2`, `b1` in turn: a `peb` fill, a 3 px edge in their
  colour, and a glyph in their colour. The focused pebble (bottom) grows ×1.5 and fills with its colour, with the
  glyph in its ink. Pebbles fade out past ±132–158°, so the top of the ring stays free for the clock capsule.
  A 74 px `peb` track is drawn under the ring. The focused app's name is set in Bricolage 700 30 px along the arc
  r = 120 above it. Its live fact (`orbFact`) is set in Martian Mono `e1` under the eyes. Input: horizontal drag or
  fling, wheel/crown, a tilt past ~17° (one step every 0.45 s), a tap on a neighbour (it spins there and opens),
  or a tap on the focused one or the fact.
- **App screens**: the title sits in a `peb` capsule on the top rim. The words sit on `peb` pebbles. Primary
  actions are filled `e1` pebble buttons, and a second button in the same row is `peb2` with a 3 px `e1` edge.
  ok / warn / listening buttons are filled mint / amber / ice. Lists are one pebble per row, and the newest row
  carries a 4 px `e1` edge on the left. Settings is one pebble sheet with 3 px black seams between rows, like the
  stone's parting line. Toggles are a `peb2` track with a `pebe` edge; when on, the track is filled `e1` with a
  dark knob. Round controls are `peb` discs with a 3 px ring; play, go and OK are filled.
- **AI** (Talk, hold-the-glass listening, thinking, answer, Claude's ask): face moments on black. The answer sits
  on a `peb` sheet. Claude's ask is a sheet with a 3 px amber edge.
- **Memory, Maps, Calendar, Games…**: same tokens. The map keeps its canvas. Game rings are flat.
- **Keyboard**: the same Round QWERTY geometry (unchanged hit-testing). Keys are `peb` and function keys `peb2`.
  A pressed key fills `e1`. Send is an amber disc and save a mint disc. The field is a pebble with a `pebe` edge.
- **Notifications**: a solid banner of `e1` (or amber / mint) on the top rim, with dark text.
- **Look**: the eyes are big at the top. Below them: ‹ name ›, the rarity and number, the three palette chips
  (`e1 e2 b1`), the 5 body swatches, the body name, and *Back to {name}* when previewing.

## 5 · Speech

The lines are the firmware's offline personality, `firmware/lib/Suflet/src/Lines.cpp` (EN + RO, ≤ 44 characters),
grouped as hello, morning, night, thanks, bored and compliment. They show as one `e1` bubble under the eyes, only
on the face or the dial, never over content.

| Moment | Topic |
|---|---|
| Waking (peek), at most once every 20 s | morning 05–11 h · night 23–06 h · hello otherwise |
| Every 3rd boop on the face | compliment |
| After you approve a Claude request | thanks |
| The dial left untouched for 11 s | bored |

## 6 · Eye reactions (event → expression)

| Event | Expression (eyes.js) | Where |
|---|---|---|
| Any tap on a control | blink ×1 | `tap()` |
| Finger down / a card dragged | look toward the finger | `ripple()`, `dragMove` |
| Dial turning / settled | look sideways toward the incoming pebble / look down at the focused one | `launcherFrame` |
| Open an app | blink: the lids close and the app is there behind them | `go()` (zoom) |
| Close an app (back to the dial / face) | blink: the lids open again | `go()` |
| Loading / AI thinking | `thinking` (squint, lids 0.14–0.32, dots) | `soul.st = "think"` |
| Claude working | `working` (reading scan) | Claude app |
| A notification arrives | `surprised` 0.9 s (eyes widen, ×1.12) + look up at the banner | `showPill` |
| Claude needs you | `shocked`, then `wait` = wide eyes looking at you | `claudeArrive` |
| Success (approve, actions done, key saved) | `approve` / `happy` | unchanged |
| An error (AI error, bad key, rate limit, offline) | `sad` 2.6 s (was `confused`) | `RX.error` |
| Misfire / cancel | `confused` 1.4 s | `RX.nope` |
| Night (23–06 h) at rest on the face | `sleepy` | `applyFaceState` |
| Shake | `dizzy` 2.2 s (spiral pupils) | `imu("shake")` |
| Spin / strong motion (IMU) | `dizzy` via `EYES.Motion` cue `dizzyStart`. Tilt also does level keeping and marble pupils. | `ALIVE.sink` ← `bindDeviceMotion` |
| Listening (hold the glass) | `listening` + the ice rim ring | unchanged |

## 7 · What stayed

All flows, views, `data-act` contracts, the keyboard geometry, the AI paths (Claude via claude.ai or your own key,
ChatGPT with your key, No AI), memory, maps, apps, games and Settings. The suites' only contract changes are:
errors are `sad` (5 assertions), and an app screen is now a flat opaque pebble on pure black instead of a frosted
sheet over the aura (1 assertion). `tests/alive-shots.mjs` adds the Alive checks and the stills.

## 8 · Firmware port (OsDraw / Glass / SoulFace)

| Element | Primitive | Notes |
|---|---|---|
| Palette | `bornPalette()` → 10 `Rgb` in `Os` (computed at birth or on a body change) | Port the 40-line JS as is (HSL lift, mix). Store `body` in NVS. |
| `peb` surfaces (rows, sheets, cards) | `Canvas::roundRect(x0,y0,x1,y1,r,peb)` | Asymmetric radii → one r = 26 is fine on device. Replaces `Os::glassPanel`, so the `GlassLayer` buffers (aura, frost and the two optional back buffers, each (480 + 2·kMargin)² × 2 bytes, plus the ¼-res planes) can be freed. |
| Specular highlight | `Canvas::arc` along the top edge, 2 px, white α 0.075 (0.3 on fills) | Or skip on device. |
| Thick edges | `roundRect` outline = two `roundRect`s, or `Canvas::ring` for discs | 3 px |
| Pebble (dial, Look swatches) | `fillSdf` with the superellipse SDF \|x/a\|^3.1 + \|y/b\|^3.1 − 1, or `roundRect(r = 0.42 h)` | 52 × 58 / 78 × 87 px. Cache the 2 sizes × 3 colours as sprites. |
| Rim capsule | `rimCapsule()` → `Canvas::arc(r, a0, a1, thick 34, peb)` + `arc(..., pebe, 2.5)` | Text on the arc as today (`Os::rimTop`). |
| Banner (notification) | `Canvas::arc(thick 44, e1)` + dark text on the arc | |
| Dial track | `Canvas::ring(240, 240, 175, 76, peb)` | Drawn once into the background; pebbles redraw only within their damage rects (the launcher already damages per item). |
| Dial pebbles | sprite blit at `(240 + 175 sin a, 240 + 175 cos a)`, scale 1–1.5 by focus | The 3 sizes in between can snap: 1.0, 1.25, 1.5. |
| Curved name | `Os::rimBottom` text on r = 124 | Font: Bricolage 30 bold (FontData). |
| Toggles, discs | `ring` + `ellipse` | |
| Keyboard keys | `roundRect(r = 14, peb)` | Unchanged geometry (`Keyboard.cpp`). |
| Speech bubble | `roundRect(e1)` + a 45° square (two triangles via `segment`) + `drawText` | Under `SoulFace` layout: y = 240 + cy·480 + 0.25·k·480 + 12. |
| Eyes | `SoulFace` / `EyeRender` unchanged; new `FaceLayoutT` for `peek` {0.52, −0.17}, `apps` {0.44, −0.07}, `look` {0.42, −0.255} | Blink on open / close: `rig_.blink(1)` in `Os::go`. |
| Reactions | `SoulFace::react(expr)`: map `error` → Sad, `notify` → Surprised, `shake` → Dizzy, night → Sleepy | `EyeMotion` already drives dizzy and level keeping from the QMI8658. |
| Breathing | Skip on device (it would need a full repaint), or ±1 px on the dial track every 2.75 s | |
| Parallax | Offset the eyes' `cx/cy` by ±4 px from the IMU gravity | Free: the eyes repaint every frame anyway. |

Rule: nothing in Alive needs a blur, an alpha-blended full-screen layer or a gradient. Every surface is one flat
fill plus at most one edge, so a damage-rect repaint is a few `roundRect`s and a text run.
