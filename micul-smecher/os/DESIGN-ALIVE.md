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
   ("pebbles", the MĂRGĂRITAR's real front silhouette). Thick strokes. Bricolage Grotesque for every word; Martian
   Mono only for ≤ 2-word tags (an AI's name, a rarity) at 18 px+. No blur, no frost, no aura. The only nod to the
   real glass is one 2 px specular highlight along the top edge of a pebble.
3. **Every SOUL's OS is its own.** The palette comes from the eye design the unit was born with (`designs.js`)
   and from its aluminium body colour (§2).
4. **Round-native.** The home is a dial of app pebbles that orbit the eyes. Labels follow the arc. Content lives in
   the safe circle under the eyes, one focal element per screen; lists are wheels (one big focused row). Nothing is
   cut by the bezel and no rim word runs through content.
5. **Buildable on the ESP32-S3.** Everything is a flat primitive: circle, ring, arc, rounded rect, superellipse
   pebble, line, text. That is cheaper than the Glass blur buffers (§8).

Every claim below about sizes, targets and the circle is checked by `tests/alive-audit.mjs` (§9) on 46 screens.

## 1 · States

| State | What the glass shows | Eyes (layout `k`, `cy`) |
|---|---|---|
| **Standby** | Only the eyes, on `#000`. No clock, no rings, no hints (unchanged). | `home` 1, 0 |
| **Wake** (a touch on the face) | The eyes glide up and shrink. The clock capsule rises on the top rim. One personality line appears under the eyes. After `PEEK_MS` = 4 s with no touch, everything goes back to standby. | `peek` 0.52, −0.17 |
| **Home dial** (swipe →, side button, wheel/crown) | A ring of stone-shaped app pebbles around the eyes, on pure black. The focused pebble sits at the bottom, filled with its colour; its name curves along the arc above it, and one short fact (Bricolage 22) sits under the eyes. | `apps` 0.44, −0.07 |
| **App screen** | **One eye slot for every app** (also Today, Your AI, Settings › Apps, Claude's ask, Convert, Maps): the eyes sit at the top of the circle, centre y = 118 device px, 107 × 50 px. Content sits under them in the safe circle. | `card` 0.30, −0.254 |
| **Face moments** | Talk, listening (hold the glass), thinking, a ringing alarm, My SOUL / Look, Breathe: the eyes stay big and are the content. | `talk` 0.62, −0.11 · `listen` 0.70, −0.10 · `think` 0.60, −0.05 · `ring` 0.44, −0.20 |
| **Keyboard** | The eyes sit above the field, small but never below k 0.24. | `kb` 0.24, −0.43 |
| **Asleep** | The sleeping eyes, dimmed and breathing. | `sleep` 0.74, −0.07 |

`k` is the eye canvas scale (1 = standby size). `cy` is the vertical offset, as a fraction of the 466 px web screen
(= 480 px on the device). The rule is now simple: **face moment = big eyes; any other screen = the one slot**
(k 0.30, never below 0.24). The eyes are drawn **over** the content (z-order), so a full-bleed map never hides them; on
the map they sit on a black pebble disc. The eyes move between layouts on the critically damped spring in
`Soul.update`: K = 260, ζ = 0.78, which settles in about 0.35 s.

## 2 · Tokens: the born palette

`bornPalette(design, body)` in `index.html` computes these. The device does the same computation once, at birth
and whenever the body is changed in Look.

| Token | Derivation | Use |
|---|---|---|
| `--e1` | `design.white` (the eye colour), lifted until its relative luminance is ≥ 0.30 | Primary fills: default buttons, focused pebble, banners, selected rows, toggles on, rim ticks, the speech bubble |
| `--e2` | The pupil colour (L or R) with the highest *saturation × (1 − \|lightness − 0.5\|)*. If that is ≤ 0.22 (near-black or grey pupils), or `e1` is saturated (chroma ≥ 0.35) and the pupil's hue is within 28° of it, use instead `hsl(hue(e1) + 165°, 90 %, 60 %)`. Lifted to luminance ≥ 0.17. | Second accent: every 2nd dial pebble, list checks, a pressed button |
| `--b1` | The body colour (below), lifted to luminance ≥ 0.20 by raising HSL lightness. Saturation is held ≥ 0.5 for chromatic bodies. | Third accent: every 3rd dial pebble |
| `--on1/2/b` | `#0B0B0C` if the accent's luminance > 0.30, else `#FBF4E3` (brand Warm White) | Ink on a filled accent |
| `--peb` | `mix(#000, e1, 0.14)` | Every surface (rows, sheets, keys, capsules) |
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

### Geometry and type (on 480 × 480; the web uses 466, × 1.03)

- Grid: the centre is (240, 240). **Safe circle r = 218** for any word or control corner (the audit fails at 228; a
  rounded corner is measured at its 45° point). The rim text radius is 204–210.
- **Zones** (466 grid): rim title capsule y 12–46 · eyes y 91–139 · content y 158–410 · bottom rim tag y 405–446.
- **Pebble** = the MĂRGĂRITAR's front silhouette, sampled from `renders/v9/src/marg_geo.py` (half-width per height,
  29 points per side on a cosine spacing, flat sitting base 60 % of the width, the widest point just above the middle = the shoulders, a domed top, 90 : 101),
  smoothed with Catmull-Rom (`stonePath()`, `STONE`). Used for the dial pebbles and the Look body swatches. Rows and
  buttons keep the asymmetric radius `22 26 24 20 / 24 20 26 22` px (a stone outline on a word button reads as a bug).
- **Strokes**: rings and arcs 8 px with round caps (focus, countdown, music, device, game, breathe, alarm dial, the
  Control dials, the wheel's scroll arc); edges 3 px; glyphs 4 px at 24 (min 2.6 px), round caps: chunky, like the eyes.
- **Type floor** (device px): rim tags and Martian Mono tags ≥ 18 · anything secondary ≥ 20 · body 24–27 · titles
  30–34 · digits 78–104. Anything you must read is ≥ 80 % alpha (`--ink2` = 66 % is used only for secondary words at
  ≥ 20 px). Rim titles are Bricolage 600 19 px (19.6 device), sentence case. Sublabels nobody needs on a 2.8″ glass
  are gone ("on claude.ai", the AI's sub-tag on Talk, the birth date on Soul, the chip id moved to the rim tag).
- **Targets** ≥ 44 device px on the short side, everywhere (audited): toggles 78 × 50 (in Settings › Apps the
  whole 64 px row is the toggle), timer segments 52 tall, Look swatches 48 × 52, keyboard keys at their full
  44 px pitch with 1.5 px black seams (no gaps in `kbHit`) plus the press callout, dial pebbles 52 × 58 (78 × 87
  focused), wheel neighbours scaled 0.9 so their controls stay ≥ 44.

## 3 · Motion = the eyes' motion

| What | Timing | Device? |
|---|---|---|
| Eyes' layout (wake, open, close) | Spring K 260, ζ 0.78 (≈ 0.35 s). | yes (`SoulFace`) |
| Blink (eyes.js `Rig.closed`) | Close 80 ms (in-quad), hold 40 ms, open 170 ms (out-back 1.8). | yes |
| **Lid wipe** (open / close an app) | Two flat black lids (an upper and a lower ellipse, 160 % × 62 % of the glass) close in 80 ms (in-quad); the screen changes behind them; they hold 40 ms and open in 170 ms on the same out-back 1.8 curve. The small eyes blink too. Reverse on close (back to the dial or the face). | yes: two `fillEllipse` per frame for 290 ms |
| Screen change (no lids: swipes between apps, overlays) | Card spring k 560, c 40 (≈ 200 ms, ≤ 6 % overshoot). | yes (slide = blit offset) |
| Dial | Snap spring 95 / 17. A fling coasts with `vr` and lands on the detent `round(rot + vr / 3.2)`. Opening: pebbles spread from the bottom, spring 300 / 32. | yes (sprite blits, per-pebble damage) |
| Wheel (lists) | Rows move on the eyes' spring curve (`cubic-bezier(.34,1.56,.64,1)`, 0.34 s). | yes (3 rows redraw) |
| Breathing idle | The focused pebble swells 1.2 % over 5.5 s, the sleeping eyes' period. | **web only** (a full repaint of the content on the device) |
| Speech | Rises with the eyes' spring (0.32 s). Stays 2.2–3.2 s. | yes |
| Tilt parallax | Pointer or `deviceorientation` → ±12 px on the dial's orbit line, ±4 px on the eyes. Approach rate 4 / s. | eyes only (the dial would need a ring repaint) |
| Reduced motion | Layouts, cards, wheels and the dial snap. No lids, no breathing, no parallax, no speech animation. Blinks still happen (they are information). | — |

## 4 · Screens

- **Standby / wake / sleep**: §1. A face drag still squashes and moves the eyes directly (rubber band 110 px).
- **Home dial** (`launcherHTML`, `launcherFrame`): 18–27 apps (`ORB`, reorder / hide in Settings › Apps). Stone
  pebbles on r = 170 every 28°, on pure black, coloured `e1`, `e2`, `b1` in turn: black fill, a 4 px edge and a 4 px
  glyph in their colour. The focused pebble (bottom) grows ×1.5 and becomes an eye-coloured stone (filled, the
  glyph in its ink); the eyes look down at it. The only track is a 3 px dotted `e1` orbit line (no tinted donut).
  Pebbles fade out past ±132–158°, so the top stays free for the clock capsule. The name: Bricolage 700 30 px on the
  arc r = 120. The fact: one short Bricolage 600 22 px line under the eyes ("17° cloudy"). Input: horizontal drag or
  fling, wheel/crown, a tilt past ~17°, a tap on a neighbour (spins there and opens), a tap on the focused one.
- **Lists = wheels** (`wheelize`, `wheelPlace`): every `.list` / `.set` (Settings, Your AI, Reminders, Alarms, Diary,
  Games, Calendar, Habits, World clock, Settings › Apps, Memory) shows one big focused row at y 290 (min 74 px tall,
  27 px words, a 3 px `e1` edge), the row above and the row below at 0.9 scale and 50 % alpha, the rest off the glass.
  Each row's width is the chord of the circle at its height (r 212), so nothing is cut. A thick `e1` scroll arc on
  the right rim shows where you are when there are more than 3 rows. Swipe / crown / tilt turn it; a tap on a
  neighbour turns it there and acts; swipe down from the first row = back. "+ New" / "+ City" are the wheel's last row.
  Notes keep their two-per-page layout (swipe pages).
- **Rim manners** (`roundFit`): a bottom-rim hint or the 1.5 s "where am I" names (prev · CURRENT · next) are drawn
  only if no glyph of them touches a word or a control of the screen; otherwise they are dropped.
- **Today**: one widget at a time, centred in the safe circle; the next one waits off the glass (swipe / crown).
- **Claude asks** (`claude` with a pending request): the eyes in the one slot (below the "Claude asks" capsule),
  the command on an amber-edged pebble, then two 66 px buttons — mint **Allow** and `peb2` with a 4 px amber edge
  **Deny** — and the shortcut hint "Hold = yes · 2× = no" at 22 px inside the circle.
- **AI**: Talk, listening and thinking are face moments. The answer sits on a round pebble (`.ansdisc`, 340 × ≥ 230,
  mint edge when actions were done, amber on an error), never a rectangle; the source sits on top in ice (or, for a demo / on-device fallback, "Demo · AI not connected" in amber: a note, not a sad face).
- **Maps**: the map keeps its full-bleed canvas; the eyes are drawn over it on a black disc. "Where to?" sits at
  y 322 so the "demo city · not OpenStreetMap data" tag keeps the bottom rim.
- **Keyboard**: the same Round QWERTY geometry, keys at full pitch. Send is an amber disc and save a mint disc.
- **Notifications**: a solid banner of `e1` (or amber / mint) on the top rim, with dark text.
- **Look**: the eyes are big at the top. Below them: ‹ name ›, the rarity and number, the three palette chips
  (`e1 e2 b1`), the 5 body swatches drawn as the stone, the body name, and *Back to {name}* when previewing.

## 5 · Speech

The lines are the firmware's offline personality, `firmware/lib/Suflet/src/Lines.cpp` (EN + RO, ≤ 44 characters),
grouped as hello, morning, night, thanks, bored and compliment. They show as one `e1` bubble (Bricolage 640 20 px)
under the eyes, only on the face or the dial, never over content. **On the dial** the bubble lives in the inner disc
(max 200 px wide, 2 lines) and the fact and the curved name step aside while it shows.

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
| A list turning | look at the focused row | `wheelTo` |
| Open an app | the lids close over the glass, the app is there when they open (+ the eyes blink) | `go()` → `lidWipe` |
| Close an app (back to the dial / face) | the same blink, the other way | `go()` |
| Loading / AI thinking | `thinking` (squint, lids 0.14–0.32, dots, the amber arc), at least 700 ms (900 ms before a fallback answer) | `soul.st = "think"` |
| Claude working | `working` (reading scan) | Claude app |
| A notification arrives | `surprised` 0.9 s (eyes widen) + look up at the banner | `showPill` |
| Claude needs you | `shocked`, then `wait` = wide eyes looking at you | `claudeArrive` |
| Success (approve, actions done — also by the demo / on-device fallback, key saved) | `approve` at once, `happy` held while it talks and after | `answer()`, `soul.speakMood` |
| A failure that did nothing (AI error with no fallback, bad key, rate limit, offline) | `sad` 2.6 s, and a held `error` state stays `sad` | `RX.error`, `MOOD_OF.error` |
| Misfire / cancel | `confused` 1.4 s | `RX.nope` |
| Night (23–06 h) at rest on the face | `sleepy` | `applyFaceState` |
| Shake | `dizzy` 2.2 s (spiral pupils) | `imu("shake")` |
| Spin / strong motion (IMU) | `dizzy` via `EYES.Motion` cue `dizzyStart`; tilt also does level keeping and marble pupils | `ALIVE.sink` ← `bindDeviceMotion` |
| Listening (hold the glass) | `listening` + the ice rim ring | unchanged |

## 7 · What stayed (and the test contract changes)

All flows, views, `data-act` contracts, the keyboard geometry, the AI paths (Claude via claude.ai or your own key,
ChatGPT with your key, No AI), memory, maps, apps, games and Settings. Contract changes in the suites, each because
the UI legitimately changed: errors are `sad`; an app screen is a flat opaque pebble on pure black; Settings is a
wheel, so its *focused row* is the pebble that is checked; the tests' `tapEl` first brings a wheel row into focus
(`__soul.reveal(sel)`, what a finger does with a swipe) before tapping it. Nothing was weakened.

## 8 · Firmware port (OsDraw / Glass / SoulFace)

| Element | Primitive | Notes |
|---|---|---|
| Palette | `bornPalette()` → 10 `Rgb` in `Os` (computed at birth or on a body change) | Port the 40-line JS as is (HSL lift, mix). Store `body` in NVS. |
| `peb` surfaces (rows, sheets, cards) | `Canvas::roundRect(x0,y0,x1,y1,r,peb)` | One r = 26 on the device. Replaces `Os::glassPanel`, so the `GlassLayer` buffers (aura, frost, the two back buffers and the ¼-res planes) can be freed. |
| Specular highlight | `Canvas::arc` along the top edge, 2 px, white α 0.075 (0.3 on fills) | Optional. |
| Thick edges | `roundRect` outline = two `roundRect`s, or `Canvas::ring` for discs | 3–4 px |
| Stone pebble (dial, Look) | `fillPolygon` of the 58-point `STONE` outline (or `fillSdf` with a polygon SDF), cached as sprites: 2 sizes × 3 colours + the focused filled one | 52 × 58 / 78 × 87 px; in-between scales snap to 1.0 / 1.25 / 1.5. |
| Dial orbit | dotted `ring` r 170: 77 dots of 3 px, `e1` at 55 % | Drawn once into the background. |
| Wheel rows | 3 `roundRect`s + text; neighbours drawn at 0.9 with the row colour mixed 50 % to black (no alpha layer) | Damage = the wheel band only. |
| Rim capsule / tags | `Canvas::arc(r, a0, a1, thick 34, peb)` + `drawTextArc` (exists: per-glyph rotated blit) | 19 px Bricolage. |
| Banner (notification) | `Canvas::arc(thick 44, e1)` + `drawTextArc` in dark ink | |
| Rings (focus, timer, music, device, Control) | `Canvas::arc(…, 8 px, round caps)` in `e1` / `e2` over a `peb2` track | |
| Lid wipe | two `fillEllipse` (black) moving vertically, 290 ms | No blending: black over everything. |
| Speech bubble | `roundRect(e1)` + a 45° square (two `segment` triangles) + `drawText` | Under `SoulFace` layout: y = 240 + cy·480 + 0.25·k·480 + 12; on the dial inside r < 140. |
| Answer pebble | `fillEllipse` (or the stone polygon) 350 × 236 + `ring` 4 px edge | |
| Toggles, discs | `ring` + `fillCircle` | 78 × 50 |
| Keyboard keys | `roundRect(r = 14, peb)` at full pitch, 1.5 px black seams | Unchanged geometry (`Keyboard.cpp`). |
| Eyes | `SoulFace` / `EyeRender` unchanged; `FaceLayoutT` gains `card` {0.30, −0.254} (all apps), `think` {0.60, −0.05}, `kb` {0.24, −0.43}, `peek` {0.52, −0.17}, `apps` {0.44, −0.07} | Drawn after the content (on top). Blink on open / close: `rig_.blink(1)` in `Os::go` + the lid wipe. |
| Reactions | `SoulFace::react(expr)`: `error` → Sad (held too), `notify` → Surprised, `shake` → Dizzy, night → Sleepy, fallback-with-actions → Approve | `EyeMotion` already drives dizzy and level keeping from the QMI8658. |

### Fonts (new atlases for `tools/gen_font.py`)

The firmware has only Nunito today: small 22, text 26, large 36, digits 88 (`Font.h`, `FontData.h` ≈ 275 KB).
Alive needs the brand faces. Add the OFL TTFs to `firmware/tools/fonts/` (Bricolage Grotesque, Martian Mono, both
SIL OFL 1.1 from Google Fonts) and extend `SIZES` with the static instances below. Charset = the existing `FULL`
(ASCII + RO ă â î ș ț and capitals + the tray letters + typography, 160 glyphs); estimates are 4-bit coverage +
12 B/glyph, measured on Nunito at the same sizes and +15 % for Bricolage's wider set:

| Atlas | Face | Size | Use | Flash |
|---|---|---|---|---|
| `kFontTag` | Martian Mono 500 | 18 | ≤ 2-word tags (AI name, rarity) | ≈ 13 KB |
| `kFontSmall2` | Bricolage 500 | 22 | secondary lines, rim titles (drawn 19–20 via the 22 atlas at 0.9) | ≈ 18 KB |
| `kFontBody` | Bricolage 500 | 27 | rows, body | ≈ 25 KB |
| `kFontName` | Bricolage 700 | 30 | the dial's curved name, titles | ≈ 30 KB |
| `kFontTitle` | Bricolage 700 | 36 | big titles, callout | ≈ 42 KB |

≈ 130 KB of flash in total (the 16 MB flash has room); keep Nunito digits 88 or regenerate them in Bricolage 700
(≈ 9 KB for 13 glyphs). Commands:

```
# instance the variable fonts first (fonttools): fonttools varLib.instancer BricolageGrotesque.ttf wght=500 opsz=24 -o Bricolage-500.ttf
#                                               fonttools varLib.instancer BricolageGrotesque.ttf wght=700 opsz=36 -o Bricolage-700.ttf
python3 firmware/tools/gen_font.py      # with SIZES += ("kFontTag","MartianMono-500.ttf",18,FULL), ("kFontSmall2","Bricolage-500.ttf",22,FULL),
                                        #   ("kFontBody","Bricolage-500.ttf",27,FULL), ("kFontName","Bricolage-700.ttf",30,FULL), ("kFontTitle","Bricolage-700.ttf",36,FULL)
```

Curved text (rim titles, the dial name on r = 120) uses the existing `Canvas::drawTextArc` / `arcTextSpan`: one
rotated blit per glyph (≈ 20 glyphs per frame when the name changes; the dial only redraws it on a detent).

Rule: nothing in Alive needs a blur or an alpha-blended full-screen layer. Every surface is one flat fill plus at
most one edge, so a damage-rect repaint is a few `roundRect`s and a text run. On the web two things are not flat
and stay web-only: the card mask of the round screen (a CSS radial mask) and the breathing scale.

## 9 · The round audit (`tests/alive-audit.mjs`)

46 screens and states (every app, Claude's ask, the AI's listening / thinking / answer, a message, a ringing alarm,
the alarm dial, the keyboard, Control, a game), at device scale. It fails if:

- any visible glyph or control corner lies outside r = 228 device px (rounded corners measured at their 45° point);
- any rim label glyph overlaps a word or a control of the screen;
- any visible text is below 18 device px;
- any control (`[data-act]`, a key, a dial pebble) is below 44 px on its short side;
- the eyes' drawn pixels touch a rim title capsule, a control or a word;
- the "where am I" rim names overlap content.

`node os/tests/alive-audit.mjs [shotsDir]` also writes one still per state and `audit-sheet.png`.
