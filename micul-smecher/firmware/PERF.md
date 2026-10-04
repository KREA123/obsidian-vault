# SOUL firmware performance: 1.7.0 → 1.8.0

*Measured 2026-10-04 on the PC (the simulator runs the device's own `lib/Suflet`). Nothing here has run on a
board yet: the ESP32-S3 milliseconds and milliamps are estimates from instruction counts and datasheet
currents. [`BRINGUP.md`](BRINGUP.md) §5 measures them on the 2.8C; write the real numbers there.*

## Headline

| | 1.7.0 | 1.8.0 | |
|---|---:|---:|---|
| Standby (the eyes alone, the spiral design the sim is born with) | 5.06 M instr/frame | **3.56 M** | −30 %; est. 15.0 → 11.5 ms a frame at 24 fps |
| Worst of the 120 designs in standby (#107 laser-show) | 8.28 M | **5.86 M** | −29 %; median design 1.42 → 1.17 M |
| Typing on the round keyboard | 6.36 M, 148 K px pushed | **3.24 M, 67 K px** | −49 % / −55 %; est. 21.5 → 11.1 ms |
| Maps (pan, zoom, route, walking) | 9.34 M | **4.86 M** | −48 %; est. 21 → 30 fps |
| Games (tilt ball + rhythm) | 8.56 M | **5.02 M** | −41 %; est. 21 → 30 fps |
| Every frame scenario (14) | | | −14 … −49 %; every one now at its asked fps (est.) |
| A question with 200 facts in SOUL Memory | 23.6 M instr | **7.0 M** | −70 %; est. 54 → 16 ms |
| Boot: eyes on the glass | est. ~1.5–1.8 s from power-on | **est. ~0.6–0.7 s** | the panel's init beside the app's, the aura deferred, radios after the first frame |
| Screen off (face down, night, Mode Off) | 240 MHz, gyro on | **80 MHz, gyro asleep** | est. −10 mA |
| Static RAM (`lcd28`) | 114,212 B | **113,172 B** | −1.0 KB; the glass LUTs (8 KB) moved to PSRAM |
| App image (`lcd28`) | 2,462,559 B | **2,394,603 B** | −68 KB (`-fno-exceptions` −102 KB, `-O3` on 3 files +18 KB) |
| Pixels | | | 31,455 frames hashed: identical to 1.7 except 68 frames / 266 px, all where 1.7 differed from a full redraw (see *Exactness*) |

## Method (reproducible)

```bash
pio run -e sim                                   # the simulator (builds -O2, as the lcd28 firmware)
python3 tools/perf_bench.py --designs --json x.json   # every scenario + all 120 designs under callgrind (4 cores: ~3 min)
python3 tools/perf_bench.py --compare perf/1.7.0.json perf/1.8.0.json   # the tables below
python3 tools/perf_bench.py --hashes DIR          # one hash per frame of every scenario, design and app still
python3 tools/perf_bench.py --check DIR_A DIR_B   # pixel-identical?
python3 tools/perf_bench.py --verify              # every incremental frame vs the same state drawn whole
```

- **Instructions** are callgrind's `Ir` collected inside `FrameComposer::compose` (frames) or the
  `suflet_bench_*` functions (`sim/sim_bench.cpp`: cloud JSON, memory search, Wi-Fi roam, boot), divided by the
  frames / operations. Same counting as BRINGUP §4–§4e, so 1.4–1.7 numbers there compare directly.
- **est. render ms** = instructions × 2.3 ns: BRINGUP §4b's calibration (6.3 M ≈ 11–18 ms on the S3 at 240 MHz,
  1.75–2.9 ns per sim instruction; the middle). **est. push ms** = pixels copied into the 2.8C's back frame
  buffer × 2 B at 50 MB/s PSRAM→PSRAM (an assumption: the `[perf]` line now prints the real copy time).
  **est. fps** applies `main.cpp`'s adaptive cap (frame + 1 ms of loop ≤ 1/1.6 of the period, floor 12 fps).
- **px copied** follows the device: this frame's changed rectangles + the previous frame's (double buffering),
  now as rectangle lists (`presentPlan()`, shared by the sim and `board_lcd28.cpp`).
- The scenarios are the simulator's (`sim/sim_main.cpp`, `sim/sim_apps.cpp`); 1.8 adds `bench_eyes` (standby,
  `SIM_DESIGN=<0..119>`), `bench_notify`, `bench_drift` and the four micro benches. The raw numbers:
  [`perf/1.7.0.json`](perf/1.7.0.json), [`perf/1.8.0.json`](perf/1.8.0.json),
  [`perf/1.8.0-without-O3.json`](perf/1.8.0-without-O3.json).

## Before: 1.7.0

| Scenario | M instr / frame | est. render ms | px copied / frame | est. push ms | est. fps (asked) |
|---|---:|---:|---:|---:|---:|
| Standby: the eyes alone, nobody touches it (Lollipop, spiral pupils) (`bench_standby`) | 5.06 | 11.6 | 57,856 | 2.3 | 24 (24) |
| Home: boop, laugh, look at the finger (`home`) | 2.74 | 6.3 | 45,567 | 1.8 | 30 (30) |
| All 31 expressions / reactions (`expressions`) | 4.64 | 10.7 | 75,438 | 3.0 | 30 (30) |
| IMU motion: level keeping, spin (dizzy), marble pupils, nod (`motion`) | 6.42 | 14.8 | 94,878 | 3.8 | 30 (30) |
| Notifications: a capsule on standby every 1.5 s (`bench_notify`) | 5.15 | 11.8 | 72,374 | 2.9 | 30 (30) |
| Launcher orbit: swipe, open Alarms, set one (`launcher`) | 3.72 | 8.6 | 74,751 | 3.0 | 30 (30) |
| Keyboard typing (35 glass caps) (`bench_typing`) | 6.36 | 14.6 | 147,840 | 5.9 | 29 (30) |
| Glass screen open, idle (Settings, aura on) (`bench_screen`) | 2.58 | 5.9 | 31,583 | 1.3 | 30 (30) |
| Glass screen, device tilted (aura drift / tilt repaints) (`bench_drift`) | 3.07 | 7.1 | 52,837 | 2.1 | 30 (30) |
| Screens opened and closed every second (aura fades on/off) (`bench_nav`) | 6.05 | 13.9 | 121,530 | 4.9 | 30 (30) |
| Talk: keyboard, thinking, the answer (`talk`) | 6.43 | 14.8 | 139,110 | 5.6 | 29 (30) |
| Claude asks: shocked, wide eyes, rim rings (`claude`) | 6.64 | 15.3 | 130,037 | 5.2 | 29 (30) |
| Maps: pan, rim zoom, route preview, walking (`bench_maps`) | 9.34 | 21.5 | 192,420 | 7.7 | 21 (30) |
| Games: tilt ball + rhythm (`bench_games`) | 8.56 | 19.7 | 226,380 | 9.1 | 21 (30) |

| Work | instr / op | est. ESP32 ms / op |
|---|---:|---:|
| Cloud JSON: the recorded SOUL Cloud session (33 frames) + a Claude answer (`bench_json`, per session) | 0.82 M | 1.88 |
| SOUL Memory: rank + context block over 200 facts (`bench_memory`, per question) | 23.59 M | 54.27 |
| Wi-Fi roam: a scan of 30 APs against 8 saved networks (`bench_wifi`, per scan) | 0.18 M | 0.40 |
| Boot: SoulOS begin (the glass aura built) + the first frame (`bench_boot`) | 55.41 M | 127.44 |

All 120 designs, standby (`bench_eyes`, 4 s): median 1.42 M, 90th percentile 2.84 M, max 8.28 M instructions /
frame. The ten heaviest: #107 laser-show 8.28, #093 neon-sign 7.82, #094 wireframe 7.72 (the outline designs: a
120-segment stroke per eye), #108 vortex 5.80, #120 sanziana 5.78 (chrome + folk + halo), #117 altita 5.41,
#097 hypno-toad 5.00, #098 lollipop 4.95 (spiral pupils), #109 ie-cobalt / #110 ie-rosie 4.64 (folk stitches).

Where the time went (callgrind, 1.7): standby 74 % in `Raster::cover` (an insertion sort of the crossings,
quadratic for a spiral's 60+ crossings a sub-scanline: 0.5 G of 1.5 G instructions); typing 68 % in
`GlassLayer::panel` (all 35 caps re-shaded for every key press); games 40 % in `Canvas::ring` (a distance and
a square root for every pixel of each ring's square box, the hole included); maps: glass panels, rim capsules,
the rim vignette ring, all repainted every frame for the pulse around "you"; SOUL Memory 36 % in `strlen` (each
fact word looked up in ~250 synonyms for every query word).

## After: 1.8.0

| Scenario | 1.7 M instr | 1.8 M instr | Δ | 1.7 px copied | 1.8 px copied | est. frame ms 1.7 → 1.8 | est. fps 1.7 → 1.8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Standby: the eyes alone, nobody touches it (Lollipop, spiral pupils) | 5.06 | 3.56 | −30 % | 57,856 | 56,951 | 15.0 → 11.5 | 24 → 24 |
| Home: boop, laugh, look at the finger | 2.74 | 2.01 | −27 % | 45,567 | 44,683 | 9.1 → 7.4 | 30 → 30 |
| All 31 expressions / reactions | 4.64 | 3.45 | −26 % | 75,438 | 61,510 | 14.7 → 11.4 | 30 → 30 |
| IMU motion: level keeping, spin (dizzy), marble pupils, nod | 6.42 | 4.75 | −26 % | 94,878 | 91,318 | 19.6 → 15.6 | 30 → 30 |
| Notifications: a capsule on standby every 1.5 s | 5.15 | 3.64 | −29 % | 72,374 | 71,520 | 15.7 → 12.2 | 30 → 30 |
| Launcher orbit: swipe, open Alarms, set one | 3.72 | 3.12 | −16 % | 74,751 | 74,097 | 12.5 → 11.1 | 30 → 30 |
| Keyboard typing (35 glass caps) | 6.36 | 3.24 | −49 % | 147,840 | 66,552 | 21.5 → 11.1 | 29 → 30 |
| Glass screen open, idle (Settings, aura on) | 2.58 | 2.21 | −15 % | 31,583 | 31,583 | 8.2 → 7.3 | 30 → 30 |
| Glass screen, device tilted (aura drift / tilt repaints) | 3.07 | 2.62 | −14 % | 52,837 | 52,837 | 10.2 → 9.1 | 30 → 30 |
| Screens opened and closed every second (aura fades on/off) | 6.05 | 4.47 | −26 % | 121,530 | 121,302 | 19.8 → 16.1 | 30 → 30 |
| Talk: keyboard, thinking, the answer | 6.43 | 4.92 | −23 % | 139,110 | 117,487 | 21.3 → 17.0 | 29 → 30 |
| Claude asks: shocked, wide eyes, rim rings | 6.64 | 5.46 | −18 % | 130,037 | 130,669 | 21.5 → 18.8 | 29 → 30 |
| Maps: pan, rim zoom, route preview, walking | 9.34 | 4.86 | −48 % | 192,420 | 109,556 | 30.2 → 16.6 | 21 → 30 |
| Games: tilt ball + rhythm | 8.56 | 5.02 | −41 % | 226,380 | 162,026 | 29.7 → 19.0 | 21 → 30 |

| Work | 1.7 instr / op | 1.8 | Δ | est. ESP32 ms 1.7 → 1.8 |
|---|---:|---:|---:|---:|
| Cloud JSON: the recorded SOUL Cloud session (33 frames) + a Claude answer (per session) | 0.82 M | 0.82 M | 0 % | 1.9 → 1.9 |
| SOUL Memory: rank + context block over 200 facts (per question) | 23.59 M | 6.98 M | −70 % | 54 → 16 |
| Wi-Fi roam: a scan of 30 APs against 8 saved networks (per scan) | 0.18 M | 0.18 M | 0 % | 0.4 → 0.4 |
| Boot: SoulOS begin + the first frame (1.7: the aura built first; 1.8: deferred) | 55.41 M | 3.72 M | −93 % | 127 → 9 |

All 120 designs (standby): median 1.42 → 1.17 M, 90th percentile 2.84 → 2.53 M, worst 8.28 → 5.86 M
instructions / frame. The ten heaviest of 1.7: laser-show 8.28 → 5.86 (−29 %), neon-sign 7.82 → 5.59 (−29 %),
wireframe 7.72 → 5.35 (−31 %), vortex 5.80 → 4.46 (−23 %), sanziana 5.78 → 4.98 (−14 %), altita 5.41 → 4.70
(−13 %), hypno-toad 5.00 → 3.65 (−27 %), lollipop 4.95 → 3.50 (−29 %), ie-cobalt / ie-rosie 4.64 → 3.90 (−16 %).

**Without the `-O3` pragmas** (`perf/1.8.0-without-O3.json`: what the algorithms alone bought; on x86 part of
`-O3`'s gain is auto-vectorisation, which the S3's compiler does not do, so the device lands between the two):
standby 5.06 → 4.07 (−20 %), typing −46 %, maps −45 %, games −38 %, talk −15 %, Claude −12 %, settings idle −7 %,
designs median 1.42 → 1.33 / worst 8.28 → 6.82. Every scenario is at its asked fps either way (est.).

The aura's first build (~50 M instructions, 1.7 did it inside `Os::begin`) now runs in the background over the
first ~11 frames after boot (3 low-res phases ≤ 7 M + 8 slices of 64 rows ~4 M, as a tone change always did): the
eyes are on the glass meanwhile; a screen opened in that first ~0.4 s shows black glass until it is ready.

## What each change bought

Measured one after the other (the column is the scenario it was aimed at; every step re-ran the full table and
the pixel check). Kept only what won; the rejected ones are listed below.

| # | Change (files) | Measured effect |
|---|---|---|
| 1 | **Crossing sort from the previous sub-scanline** (`Raster::cover`): the crossings are re-evaluated in the last sub-scanline's x order (slots tracked through the active list's swap-removals) and insertion-sorted by (x, active slot) — exactly 1.7's order (ties included), a fraction of the moves. A solid interior's running sum comes from `256 − acc` instead of a walk | standby 5.06 → 4.22 (−17 %), home −13 %, outline designs −15 % |
| 2 | **Rectangle lists** (`Canvas.h RectList`, `Frame.*`, `Os` dirty list, `EyeRenderer` per-eye parts, `presentPlan()` on the 2.8C and the AMOLED): repair / push a few disjoint rectangles instead of one box | expressions 75 K → 62 K px pushed (−18 %); the base for #3, #9, #10 |
| 3 | **Keyboard damage** (`Keyboard::takeDamage`): a snapshot of what each region shows (field, bar, keys, pressed key, callout, tray); only what looks different is repainted | typing 6.38 → 3.53 M (−44 %), 148 K → 67 K px |
| 4 | **Rings and glass tables**: `Canvas::ring`/`arc` visit only the annulus (`fillSdfSpans`), `Raster::ring` fills a full ring's solid middle without a square root, the glass LUTs pre-shifted to RGB565 (and moved to PSRAM) with the level branch hoisted | games 8.55 → 6.76 M (−21 %), maps −6 %, typing −4 % |
| 5 | **Glass rows** (`GlassLayer::shade`): a rim capsule / band visits only its annulus (± the shadow pad); pixels surely 1.6 px inside skip the distance function (same per-pixel gradient) | Claude 6.38 → 5.93 M (−7 %), launcher −2 % |
| 6 | **Solid ring runs in one loop** (`Raster::ring`) | maps 8.83 → 8.52 M (−3 %) |
| 7 | **SOUL Memory** (`Memory.cpp`): synonym groups from a compile-time sorted table (flash) by binary search, looked up once per fact word | 23.6 → 7.0 M per question (−70 %); the same ranks and context blocks for 16 queries × 180 facts (diffed against 1.7) |
| 8 | **`-O3` on the three pixel files** (`#pragma` in `Raster.cpp`, `Glass.cpp`, `Canvas.cpp`) | −5 … −16 % in the sim (x86); +18 KB flash. On the S3: measure (BRINGUP §5) |
| 9 | **Skip crossings already in place** (the sort's common case) | standby 3.74 → 3.50 M (−6 %) |
| 10 | **Tilt ball / eye memory** (`Os::gamesInvalidate`): a signature of what the game shows; if only the ball and the star moved, only their squares are repainted; eye memory repaints only on a change | games 6.18 → 5.03 M (−19 %), 226 K → 162 K px |
| 11 | **Map pulse** (`Os::mapsInvalidate`): while navigating or waiting, if nothing but the pulse around "you" changed, only its square | maps 8.09 → 4.94 M (−39 %), 192 K → 110 K px |
| 12 | **Boot**: the aura deferred (`GlassLayer::begin(.., false)`, `Os::setDeferGlass`), the ST7701 init in a task on core 0 beside the app's, touch / audio / BLE / SOUL Cloud / Wi-Fi after the first frame | first frame 55.4 → 3.7 M; est. eyes ~1 s sooner (see *Boot*) |
| 13 | **8-byte crossings** (`Raster::Cross` packed): two 512-entry arrays of exactly 4 KB, so the S3's allocator keeps them in internal RAM (12-byte ones would have gone to PSRAM) | +1–2 % in the sim (bit unpacking); avoids PSRAM latency in the hottest loop on the device |
| 14 | **`-fno-exceptions`** (all device envs): nothing catches; a library throw still aborts as before | −102 KB flash |
| 15 | **Power**: 80 MHz + gyro asleep with the screen off; BLE adverts every 152–211 ms | est. −10 mA screen off, −0.5 mA always (see *Power*) |

Correctness fixes found on the way (the new `--verify` compares every incremental frame with the same state
drawn whole): **(a)** a new overlay that landed on a lit rim ring outside the repair (the "!" beside the right eye
under Claude's amber ring) showed the old ring under it instead of over it — the composer now repairs a little
around the eyes when a ring is shown (`kEyeSlack`) and re-renders what still lands outside; **(b)** a glass panel's
gradient and an eye's chrome / aurora gradient were stepped from the clip's edge, so a partial repaint could
differ by one level from a full one — they now step from where an unclipped draw starts (tested).

**Tried and dropped** (no win): rim rings refreshed through four edge strips instead of the whole glass (0 %: those
frames repaint everything for other reasons), integer disc bounds in `Raster::composite` (+1 %), the deep-span
path on opaque panels (+2 %: the LUT run already covers them; kept for panels fading in), looser rectangle merging
(`u/4 + 2 K`: fewer, bigger rectangles, more pixels pushed).

## Exactness (the look did not change)

- **Frames**: 31,455 frames hashed (every scenario at 480 and 466 px, the 120 designs, the app stills, maps and
  games). Identical to 1.7.0 except **68 frames, 266 pixels in all** (worst frame: mean |Δ| 0.0038 / 255 per
  channel, 38 px): claude 11 frames, cloud 11, everywhere 32, apps (the main sim scene) 12, glass 1, talk 1 —
  every one a frame where 1.7's incremental picture differed from a full redraw (fix (a) and (b) above) — plus the
  Device app's "1.8.0".
- **Stills**: all 110 marked stills of the simulator: 108 identical, 2 differ by 1–2 pixels (mean 0.00002 / 255);
  the 31 app stills: identical to `sim/shots/apps/` except `28-device` (the version text, 146 px). The sheets
  stand (`sim/shots/apps/` regenerated for the version).
- **Incremental = full** (`--verify`): 476 frames differed from a full redraw in 1.7, 360 in 1.8; the 360 are all
  1.7's too, unchanged: the timer's rim arc and the find-phone / focus pulses advance between their 1 s
  invalidations, the map's pulse in browse mode is not animated (1.7 behaviour, kept), and the dial's day / night
  tint draws differently on a fresh canvas than over the last frame (the device shows what 1.7 showed).
- **Tests**: 194 → 198 native tests: the 1.7 rasterizer kept verbatim as the reference for 1,500 random paths
  (spirals, stitches, shared edges = ties, even-odd), `Raster::ring` vs 1.7's on 400 random rings / arcs / clips,
  `Canvas::ring`/`arc` vs the full-box version, clipped vs unclipped draws (gradients, panels, capsules, bands).

## Memory

| | 1.7.0 | 1.8.0 |
|---|---:|---:|
| Static RAM (`.data` + `.bss`, `lcd28`) | 114,212 B | 113,172 B |
| Glass LUTs (4 styles) | 4 KB in `.bss` (DRAM) | 8 KB, PSRAM, on first use |
| Rasterizer work arrays | order + active 16 KB (PSRAM), crossings 4 KB (DRAM) | + edge slots, new edges 2 × 8 KB (PSRAM); crossings 2 × 4 KB (DRAM, +4 KB heap) |
| Frame bookkeeping | 2 rectangles | 3 lists of ≤ 10 rectangles (~0.5 KB) |
| Synonym table | in flash | sorted at compile time, in flash |

No allocation per frame was added (the lists are on the stack, the rasterizer's arrays are reserved once). Heap
high-water marks, fragmentation and every task's stack head-room are now on the serial monitor: `m` prints each
task's unused stack (bytes) and CPU share since the last `m`, and the internal / PSRAM heaps (free, lowest ever,
largest block). The `[perf]` line adds the copy and wait times of the last present, the CPU clock and the loop
task's stack head-room. Measure them on the board (BRINGUP §5c): the PC cannot.

## Power (estimates; BRINGUP §5d measures)

Model: ESP32-S3 datasheet, modem-sleep currents: both cores idle (WAITI) ≈ 33 mA at 240 MHz, ≈ 22 mA at 80 MHz;
one core running adds ≈ 29 mA at 240 MHz. Core 1's duty = (render + push + 1 ms) × fps.

| State | 1.7.0 | 1.8.0 | Δ (est.) |
|---|---|---|---|
| Standby, awake (24 fps) | 15.0 ms × 24 = 36 % → ~43 mA CPU | 11.5 ms × 24 = 28 % → ~41 mA | **−2.5 mA** |
| Typing (30 fps) | 64 % → ~52 mA | 33 % → ~43 mA | **−9 mA** while typing |
| Claude's ask, rim ring (30 fps) | 64 % | 56 % | −2 mA |
| Maps / games | CPU-bound at ~21 fps (63 %) | 30 fps at 50 % / 57 % | −2 mA *and* +40 % frame rate |
| Screen off (4 fps; face down, night) | 240 MHz, gyro on | 80 MHz, gyro off | **−10 to −11 mA** (CPU −10, gyro ~−0.5) |
| BLE advertising (no Claude Desktop connected) | ~30–60 ms interval | 152–211 ms | ~−0.5 mA |

Against BRINGUP §4's board totals (backlight dominates): awake ~180–230 → ~177–227 mA; screen off ~45–70 →
**~35–60 mA**. Wi-Fi was already in modem sleep (`WIFI_PS_MIN_MODEM`, `net.cpp`); the backlight curve (gamma 2.2)
and the fps tiers (30 moving, 24 calm, 15 drowsy, 10 asleep, 4 screen off) were already what this pass would
set, so they stay. Light sleep with the screen on is not possible with an RGB panel (the DMA must keep scanning),
and `esp_pm` dynamic frequency scaling is not enabled in Arduino-ESP32's prebuilt libraries (and the RGB driver
holds a max-frequency lock while scanning); the screen-off clock change uses `setCpuFrequencyMhz()` instead.

## Boot (estimate; BRINGUP §5b measures)

| Step | 1.7.0 | 1.8.0 |
|---|---|---|
| ROM + 2nd-stage bootloader + app load (16 MB QIO 80 MHz, PSRAM init) | ~0.2–0.3 s | same |
| `delay(150)` after `Serial.begin` | 150 ms | none (USB CDC needs none) |
| ST7701: reset 10 + 120, soft reset 120, sleep-out 120 ms, panel + 3 × 460 KB memsets | ~385 ms | the same, **in a task on core 0 beside the next row** |
| IMU, RTC, NVS, Brain, SOUL Memory, `Os::begin` | ~70 ms + 127 ms (the aura) | ~70 ms + ~1 ms (the aura deferred) |
| GT911 reset (150 + 150 + 50 + 50 ms) | 400 ms, before the first frame | in a task, after the first frame |
| BLE, SOUL Cloud, mDNS, Wi-Fi task | ~150–250 ms, before the first frame | after the first frame |
| First frame: compose + copy, backlight | in `loop()`, backlight ramps up ~0.25 s | at the end of the parallel init, backlight straight on |
| **Eyes on the glass** | **~1.5–1.8 s** | **~0.6–0.7 s** (the panel's 385 ms is the floor) |

`-DLCD_SKIP_SWRESET=1` drops the ST7701 soft reset after the hard one (−120 ms → ~0.5 s): a board-day experiment,
off by default (the vendor sends both). The serial log prints `[boot] eyes on the glass at N ms` and
`[boot] radios started at N ms` (from the app's start; the ROM + bootloader time is not in `millis()`).

## Not done here (needs the board, or out of reach on this PC)

- **Every millisecond and milliamp above**: estimates. BRINGUP §5 has the steps; the `[perf]` line, `m`, and a
  USB meter turn them into numbers. If the S3's ns per instruction differs from 2.3, every est. column scales.
- **PSRAM XIP + IRAM-safe LCD ISR** (the real fix for flash writes starving the panel): `env:lcd28_xip` in
  `platformio.ini` sets `CONFIG_SPIRAM_XIP_FROM_PSRAM`, `CONFIG_LCD_RGB_ISR_IRAM_SAFE` and
  `CONFIG_LCD_RGB_RESTART_IN_VSYNC` through pioarduino's `custom_sdkconfig` and turns the VSYNC-restart workaround
  off (`SUFLET_LCD_XIP`). It needs pioarduino's hybrid compile (ESP-IDF download, ~15 min, ~3 GB): **not built**
  here (the build machine had ~2 GB of disk free). Risk: code then runs from PSRAM, whose bandwidth the panel shares; a boot loop or a
  slower frame means stay on `lcd28`. BRINGUP §5e.
- **ESP32-S3 PIE SIMD (`ee.*`, esp-dsp) for fills / blends**: no S3 to verify bit-exact results or speed; the
  pixel loops are now short (the solid runs are `memcpy`/32-bit stores already) and most time is in coverage, not
  blending. **GDMA `esp_async_memcpy`** for the present copy: would overlap the copy with the next frame's logic
  but the canvas must not change during it; worth it only if §5 shows push ≫ 3 ms.
- **`-O3` on Xtensa**: measured on x86 only. **LTO**: not tried (the prebuilt Arduino libraries are not LTO
  objects; ESP-IDF's linker-script placement and LTO are a known bad mix). **IRAM_ATTR on the pixel loops**: they fit
  the 32 KB instruction cache; IRAM is better spent on the LCD ISR (the XIP env).
- **The aura's drift / tilt repaint** (`bench_drift`): every glass pixel shows the frosted aura at the new offset,
  so it stays a full repaint (≤ 4 a second, as designed); slowing it would change the look.
- **TLS buffers in PSRAM, smaller records**: mbedTLS's allocator is fixed in the prebuilt libraries
  (`CONFIG_MBEDTLS_EXTERNAL_MEM_ALLOC` needs the hybrid compile, as XIP); `m` shows whether internal heap is short
  during a cloud turn with BLE on before anything is changed.
