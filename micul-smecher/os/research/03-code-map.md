# SoulOS: code map (03)

*Audit of `firmware/` and `os/`, 2026-09-24. Paths are relative to the project root. `f:N` means line N and `N-M` a range. Companion to `02-os-architecture.md` (§6 text input, §11 memory).*

## 0. Baseline
- `pio test -e native` gives **24/24 PASS**. Incremental run: 2.7 s wall (Unity 2.2 s). Clean build + test: 4.2 s (scratch copy). Clean `pio run -e sim`: 3.7 s. Sim scene `idle` renders 270 frames in 0.8 s but writes **176 MB** of raw RGB888 (650 KB per frame).
- Last amoled175 build (09:02): `firmware.bin` is 796 KB in a 6.25 MB `app0` (OTA pair, 0x640000 each). Static DRAM: 19.8 KB data + 15.9 KB bss. IRAM text: 101 KB. No code uses `spiffs` (3.4 MB @0xC90000). NVS: 20 KB.
- Environments (platformio.ini): `amoled143` (default) and `amoled175` use esp32-s3-devkitc-1 with qio_opi PSRAM, 16 MB flash, -O2, GFX 1.6.8, ArduinoJson 7 and SensorLib 0.4.1. `sim` is native and builds only `sim/sim_main.cpp` plus the library. `native` builds the tests with `test_build_src = no`, so `src/` is never compiled on the PC. The board comes from `-D…_BOARD_AMOLED143/175=1`, which selects the pin map in `src/board.h`.

## 1. Library `firmware/lib/Suflet/src`: portable, no hardware, one C++17 namespace
| File (lines) | Responsibility | Public API |
|---|---|---|
| Canvas.h/.cpp (145/142) | RGB565 software renderer over an external buffer. SDF anti-aliased shapes with a glow halo. Dirty-rect union. | `Rect{x0,y0,x1,y1}` half-open, `add/empty/w/h`. `Canvas(w,h,buf)`. `fill` (marks dirty), `fillRect` (**does not mark dirty**), `dirty/resetDirty/markDirty/clip`. `blend(x,y,Rgb,a)` (**no bounds check**). `fillSdf(bx0,by0,bx1,by1,sdf,c,alpha,glowR,glowA)` h:83-115. `ellipse/ring/segment/arc/heart/star` h:117-130. Static `sdEllipse/sdSegment/sdArc/sdHeart/sdStar5`. No text, no images, no rounded box. |
| Color.h (48) | `Rgb` (`hex/to565/from565/scaled/lerp`). `pal::` holds kEyeDay FFF0C8, kEyeNight, kBlush, kHeart, kWhite, kMint, kIce, kGold. | — |
| Events.h (74) | `enum class Ev : uint8_t` with 26 values: touch, motion, `Ai*`, `Claude*`. **Events carry no payload** (no x/y, no text). `evName()` has a static_assert against the enum. `EvQueue<N>` is a ring that drops the oldest event. | add new values before `Count` (h:37) and update `kNames` (h:41-47) |
| Gestures.h/.cpp (76/178) | `TouchGestures::update(down,x,y,dt)` cpp:9-53 emits Tap/DoubleTap/HoldStart/HoldEnd/StrokeStart/StrokeEnd. Tunables h:17-21: tapMaxS .35, holdAfterS .5, moveSlopPx 25, strokePx 45, doubleTapS .40. `x()/y()/isDown()`. `MotionDetector::update(ax,ay,az,dt)` cpp:59-176 emits PickUp/Shake/FreeFall/Knock/FaceDown/FaceUp/UpsideDown/Upright. `tiltX/Y, stillFor, faceDown, knockX/Y`. | — |
| Face.h/.cpp (73/213) | Parametric eyes: `Face{Eye L,R; gx,gy,spacing,eyeW,eyeH,cy,bright,glow,color,style,styleAmt,happy,blush,overlays,overlayT,spin,mouth,level,progress}`, `EyeStyle`, and the `ov::` bitmask (Zzz…Progress, 12 of 16 bits). `renderFace(Canvas&, const Face&)` h:71 / cpp:114-211 sizes by min(w,h) and **always centres the face. It has no scale or layout parameter** (the prototype has `lay{k,cy}`). | — |
| Brain.h/.cpp (208/1085) | Character state machine: mood, idle life, 24 reactions, sleep modes, Claude approve/deny. | `Brain(Personality,seed)`, `event(Ev)` cpp:259-419, `trigger(Reaction)`, `boot()`, `update(dt,Inputs)` cpp:472-551, `setDay/setAbsence/setAiLink/setTone`, `face() body() mode() reaction() mood() memory() claudePrompt() claudeBusy() approveProgress() frameRateHint()` (30/20/12/2 fps), `popCue(Cue&)`. Enums `Reaction`, `Mode`, `Cue` (h:51-69, incl. ListenOn/Off, Nudge, ClaudeApprove/Deny) and `Tone`. Structs `Inputs{tiltX,tiltY,stillFor,faceDown,knockX,knockY,hour,audioLevel}` h:81, `Memory` (NVS blob) h:96, `Mood`, `BodyLight`. Reaction table `kR` cpp:20-34. `applyReaction` 555-918. `compose` 920-1083. |
| Personality.h/.cpp (33/86) | Chip MAC seed becomes tint, rarity and traits. | `fromSeed`, `tintName`, `rarityName`, `archetypeRo`, `sleepAfterSeconds` |
| ClaudeLink.h/.cpp (93/203) | Transport-free Hardware Buddy protocol (JSON lines over NUS). | `feed(bytes)`, `tick(dt)` (30 s link timeout), `setTransportConnected`, `poll(Ev&)`, `popOutgoing(line)`, `decide(bool)` cpp:77-96. Getters: `hasPrompt promptTool promptHint msg owner tokensToday level timeValid epochNow tzOffset localHour`. `status` (DeviceStatus). Time sync cpp:103-110. Commands status/name/owner/unpair 113-159. `evt` turn events are ignored (162); so is folder push. **The device can send only permission decisions and acks. There is no path for typed text to reach Claude.** |
| Rng.h (37) | `mix64`, `Rng` xorshift64* (`uniform/range/chance/irange/sign`) | — |

## 2. Device layer `firmware/src` (Arduino, single-threaded `loop()`)
- **board.h:** pins per board. 1.75: CST9217 at 0x5A, `TOUCH_INT` 11, `RTC_INT -1`, PMU 0x34, I2S pins, `HAS_AUDIO 1`. 1.43: FT3168 at 0x38, `RTC_INT` GPIO15, `HAS_AUDIO 0`. Also `LCD_W/H 466`, `BOOT_BUTTON 0`, the software rotation macro (0/90/180/270), `IMU_MAP`.
- **ble_link.h/.cpp:** NUS server with LE Secure Connections passkey. Offers `bleInit/Connected/Secure/Passkey/ClearBonds/Available/Read/Write`, a 4 KB RX ring and a 180 B notify chunk.
- **main.cpp map:**
  - Setup: globals 33-65, i2c 69-83, `pmuInit` 88-101 (1.75 only; the AXP2101 PWR key is set to power off after a 4 s hold), `readBattery` 104-118, `readTouch` 122-139, `touchInit` 141-149.
  - Drawing: `displayInit` 153-169, `rot` 172-186, `pushRect` 189-211, `drawCentered` 213-220, `renderFrame` 222-263.
  - Clock: `clockValid` 267, `localEpoch` 272-283, `setClockLocal` 285-291, `hourNow` 293-297, `updateCalendar` 299-313.
  - Storage and debug: `saveMemory/loadMemory` 317-331 (Preferences namespace keys: mem, seen, naps, born), `serialCommands` 344-398, `demoTick` 400-410.
  - Entry points: `setup` 414-456, `loop` 458-548.
- **`loop()` order:**
  1. Touch (465-467).
  2. IMU at 100 Hz (469-479).
  3. BLE to ClaudeLink, plus a one-time RTC sync from desktop time (481-493).
  4. **Event dispatch** (495-498): `touch.poll`, then `motion.poll`, then `claude.poll`, each into `brain->event`.
  5. `Inputs` (500-506), then `brain->update` (509).
  6. Cues (512-517): ClaudeApprove/Deny call `claude.decide`. The other cues are dropped (no haptic or audio yet).
  7. BLE TX (518-519) and status every 2 s (521-533).
  8. `renderFrame` (535), serial (536), NVS save every 60 s (538-542).
  9. Frame pacing with `delay` (544-547).
- **Not in the code:** Wi-Fi, audio/I2S, haptics, side-button handling (BOOT is read only at boot to start the demo loop, 449-450), LittleFS, OTA, sleep modes.

## 3. Text rendering today
- **Canvas cannot render text.** The only text path is `drawCentered` (main.cpp:213-220). It uses the Arduino_GFX `Arduino_Canvas` built-in 5×7 glcdfont at integer `setTextSize`, so text is blocky, not anti-aliased and limited to ASCII/CP437. It computes width as `strlen*6*size`, which mis-measures UTF-8. It draws into the shared framebuffer, then calls `markDirty`. Callers: the BLE passkey and the Claude tool/hint (renderFrame 244-257). GFX is not in the native environments, so **this text never appears in sim renders or tests**.
- GFX has `U8G2_FONT_SUPPORT` and `setUTF8Print`. Its bundled unifont is 16 px 1-bpp: it has ș ț, but it is ~1.5 mm tall on this panel and has no anti-aliasing. Use it for debug only.
- **Glyph check** (Google Fonts, today): Fredoka has â Â î Î but **lacks ă Ă ș Ș ț Ț** (and cedilla ş ţ). Nunito latin-ext has ă Ă ș Ș ț Ț. Pillow 12.3 with FreeType 2.14 is installed and can rasterise both.
- **What text needs:** a new `Font` + `Text` module in the library (hardware-free, so it can be tested and simulated):
  - Offline generator `firmware/tools/make_font.py`: TTF to 4-bpp (or A8) glyph bitmaps + advance/bearing (+ optional kerning), emitted as `const` arrays in flash rodata.
  - A UTF-8 decoder.
  - `drawText(Canvas&, x, y, utf8, font, Rgb, alpha, align)`, `measure()` and `wrap(maxW, maxLines, ellipsis)`, drawing through `Canvas::blend` + `markDirty`.
  - Coverage: U+0020-007E, U+00A0-00FF, U+0102-0103, U+0218-021B, and „ ” ’ … – · ✓ → ⇄ ⌫ ⏎. Map U+015E/F and U+0162/3 to the comma forms.
  - Fallback: Fredoka first, Nunito for ăĂșȘțȚ, or synthesise the breve/comma as SDF on Fredoka a/s/t so the weight matches.
  - Sizes 22/27/34 plus 104 px digits: ~180 KB flash (SPEC §8.1).

## 4. Touch, gestures and events
1. `readTouch` (main.cpp:122) reads raw registers (FT3168) or `TouchDrvCST92xx` (CST9217), applies the mirror, and returns one point (single-touch).
2. `TouchGestures::update` runs **once per frame** (30 Hz awake, 12 Hz asleep). It is polled, not driven by an interrupt, even though the 1.75 has `TOUCH_INT` 11.
3. Events go to `EvQueue<8>`, then `brain->event(e)`. **Everything goes to the Brain; there is no Shell or router yet.**
- **Tap fires on release.** `x_/y_` keep the last pressed position, so the tap point is available through `touch.x()/y()` but is not carried in the `Ev`.
- **DoubleTap swallows the second tap** (cpp:42-48), which breaks fast typing.
- **Hold at 0.5 s means Listen or Purr** in `Brain::event` 304-312.
- **There are no directional swipes:** a stroke is any motion over 45 px.
- The prototype uses hold 380 ms, double-tap 330 ms and a 14 px slop; SPEC says hold ≥ 380 ms. **The firmware and the prototype disagree on these timings.**

## 5. Time and RTC
- The PCF85063 is read through SensorLib `rtc` (main.cpp:44). It stores **local** time. `clockValid()` requires year ≥ 2025. `localEpoch()` returns local seconds (mktime with TZ = UTC). `setClockLocal()` sets it. `hourNow()` falls back to `claude.localHour()`.
- **Time sources:** the ClaudeLink `{"time":[epoch,tz]}` message (one sync, 489-493) and the serial `T<epoch>` command (377-385). **There is no NTP or phone sync.**
- The library only sees `Inputs.hour` (float) and `Brain::setDay(day, birthday)` / `setAbsence(h)`. It has no minute-level clock interface. The sim and tests hard-code `in.hour` (14.5 and 14).
- **Hardware alarm:** the PCF85063 alarm INT reaches GPIO15 on the 1.43 only. `RTC_INT` is -1 on the 1.75, so check the schematic. Otherwise use a software check plus an esp_timer / deep-sleep timer wake.

## 6. Memory budget (from code)
- **Framebuffer:** 466×466×2 = 434,312 B. `Arduino_Canvas::begin` allocates it with `aligned_alloc` (it is too large for internal RAM, so it lands in PSRAM; verify with `heap_caps` on the board). `Canvas` wraps it (main.cpp:160-162).
- **`pushBuf`:** another 434,312 B, `ps_malloc` (163). Total **~848 KB of 8 MB PSRAM**.
- Internal RAM: 36 KB static. The BLE RX ring is 4 KB and ClaudeLink `rx_` can reach 8 KB. Free heap has not been measured (no board yet); `ESP.getFreeHeap()` is reported to the desktop (531).
- **Frame cost:**
  - `renderFrame` clears `prevDirty` to black, redraws the face, then pushes union(prev, cur).
  - `pushRect` copies pixel by pixel with rotation, then calls a blocking `draw16bitRGBBitmap`. There is **no DMA and no double buffer**.
  - The QSPI runs at 40 MHz (`begin(40000000)`, 161), about 20 MB/s: a full frame takes ~22 ms and a keyboard half takes ~11 ms.
  - **Any UI layer must redraw inside the dirty union each frame, or cache itself in a third PSRAM layer (434 KB).**

## 7. Simulator and native tests
- **`sim/sim_main.cpp`:**
  - `Recorder` 30-71: `frame()` 45-62 does fill black, then `renderFace`, then RGB888 to `<name>.rgb`, and writes body light to `<name>.json`.
  - `Sim` 74-111: `step/run/skip/ev/feed`. There is no `TouchGestures` and no coordinates; events are injected directly.
  - `scenarios()` 119-240 holds 10 scenes: idle, boop, purr, dizzy, sleep, missed_you, rare, ai_talk, claude_buddy, night.
  - Usage: `program <out> [name|all] [seed]`.
  - **To add a scene:** append `{"name","caption",[](Sim& s){…}}` to `scenarios()`. For UI, give `Sim` a `TouchGestures` + `tap(x,y)` / `type("text")` and call `shell.render(cv)` in `Recorder::frame`. Keep scenes short (650 KB per frame), or add a `--png` stills mode.
  - `tools/frames_to_media.py <sim_out> <media> [--gif --mp4 --sheet --only a,b]` composites into a 540 px frosted-body shot. The sheet uses frames at 15/45/75%. ffmpeg is available.
- **`test/test_suflet/test_main.cpp`** (Unity):
  - Helpers: `Rig` 24-41 (Brain + Inputs, `run(s, still)`, `hasCue`), `drainMotion/has` 43-53, `feedRest` 116, `feedLine/drainLink` 303-313.
  - Groups: personality 57-76, touch 80-114, motion 116-170, brain 172-301, claude 314-397, render 399-430 (pixel checks against the dirty rect on a 240×240 `std::vector` buffer).
  - **To add a test:** write `void test_x()` before `main` (432) and add `RUN_TEST(test_x)` to the list 434-457. **New modules must live in `lib/Suflet/src` and stay hardware-free** (the native env has ArduinoJson only; std::string is OK).

## 8. Web prototype `os/index.html` (1185 lines, one file, no build step)
- **CSS 6-210:**
  - Tokens `:root` 7-19 with dark copies 20-38. Device colours `--cream/--amber/--mint/--ice`. Fonts `--display` (Fredoka, Nunito), `--body`, `--mono`.
  - Device UI lives in a 466 px space 89-181: card transitions `.in-*/.out-*` 91-101, `.c/.lbl/.t1 34px/.t2 27px/.t3 22px` 102-107, `.chip` (52 px tall) 114-118, `.pill` 126-133, `.list/.row/.set`, `.caret` 179.
  - Panel 182-208. Reduced-motion guard 209 (plus the `RM` flag in JS, 387).
- **HTML 212-261:** `#screen` (466 px, scaled by `size()` 1136) contains `canvas#face`, `#cards`, `#dots` and `#pill`. The side button is `#side`. The panel holds `#say #screens #ctrl #sens`.
- **Strings:** `STR.ro` 267-322 and `STR.en` 324-379 have identical keys. Values may be functions (`thinking`, `setMemV`, `homeFocus`). Always read them through `T()` at render time. The language toggle (1127-1131) persists `soulos-lang` and calls `renderPanel()` + `refresh()`.
  - A ring app needs `STR.*[v]` (its name) and `STR.*.d[v]` (its panel description).
  - Data such as `rems`, `notesInit` and `diaryInit` is keyed by index. `remText/noteText/diaryText` (661-663) look the text up by key, so **user-typed text needs a `text` field**.
- **Face:** `drawFace(ctx,S,f,lay)` 464-524 is a port of Face.cpp with a layout `{k,cy}`. `class Soul` 527-634 has states `st` = idle/sleep/listen/think/speak/focus/busy, `react(name)` (durations in `DUR` 526), `lookAt(x,y,dur)`, `follow`, `alert`, `prog/progCol` and `lay`.
- **OS state 637-672:**
  - `RING` 640 is the swipe circle; `OVERLAY` 641 lists screens outside it; `LAYOUT` 642-646 sets face size per view.
  - The single state object is `S` (647-654), with `initData` 655.
  - Timers are `after(ms, fn, tag)` / `cancel(tag)` 670-672. Tags: voice, answer, pill, hold, khold, shold, claude, msg, sync.
- **Screens:** `cardHTML(v)` 684-778 has one `case` per view and returns an HTML string. Use absolute positions, `.lbl` at top 136, `.c` with an inline `top`, `data-act` for tap targets, and `data-live` for per-second in-place updates (`frame` 1159-1167).
  - `go(v, dir)` 803-828 builds the new card, animates the old one out, moves the eyes, and calls `applyFaceState` (786-797) and `renderDots`.
  - `refresh()` 829 re-renders the current card. `back()` 830.
- **Cards and pills:** `showPill({kind:""|amber|mint, who, text, act, dur})` 833-841, `hidePill` 842, `buzz` 843 (shakes the device body).
- **Voice demo:**
  - Phrases are `{q, a, chips:[[kind,text]], tool, fx}` in `STR.*.phrases` (306-313 / 363-370), plus `notePhrase` and `trPhrase`.
  - `startVoice(kind, preset)` 852-867 types the transcript into `.t2` with a caret. `endListen` 868 moves to think for 1.4 s. `answer` 874-892 runs the `fx` side effects (rem/note/note2/msg/light/focus) and returns to the destination after 6.5 s. `runPhrase(i)` 893.
- **Claude:** `claudeArrive` 902 (auto after 20 s, 1184), `claudeDecide(ok)` 910. Hold-to-approve progress (1.2 s) is in `frame` 1149-1157.
- **Input:**
  - `holdStart/holdEnd` 921-936. `tap(target)` 938-958: **a second tap within 330 ms becomes `doubleTap()`**. `act(a, el)` 963-979 is the `data-act` switch. `swipe(dir)` 980-990. `sideButton` 991. `imu` 1003.
  - Pointer handling 1016-1045: hold at 380 ms, swipe threshold max(22 px, 10% of width), 14 px slop.
  - Side button 1047-1064.
  - **Global keys** 1067-1090: arrows mean swipe, Space means hold/tap, Enter means tap, `d` means double-tap, Esc/Backspace mean the side button.
- **Conventions:** vanilla JS in `"use strict"`, `$()`, template strings passed through `esc()`, no frameworks. Minimum text 22 px, chips ≥ 52 px, 68 px side safe area, nothing interactive below y = 410. Handle `RM`. Mirror each change in RO and EN.

## 9. Exact insertion points
**Firmware** (names follow the TextInput service in 02 §6):
1. **Events:** in Events.h, add before `Count` (h:37) `SwipeL/R/U/D`, `ButtonPress/Hold/Release/Double`, `TextCommit/TextCancel`, `AlarmDue` and `AlarmDismiss`, and extend `kNames`. Payload options: add `struct InputEv{Ev e; int16_t x,y;}` to the `EvQueue`, or expose `TouchGestures::tapX/tapY()` recorded in the release branch (Gestures.cpp:36-52). Add swipes by velocity at the stroke check (cpp:26-29). Add a `ButtonGestures` class to Gestures.h after `TouchGestures` (h:8-28), fed by BOOT/GPIO0 on the 1.43 and by the AXP2101 PWR-key IRQ on the 1.75 (pmuInit 88-101).
2. **Shell and routing:** add new `Shell.h/.cpp` and `Card.h` in the library. In main.cpp:495-498 change dispatch to `if (!shell.event(e)) brain->event(e)`. In renderFrame, replace line 242 with `renderFace(*cv, face, shell.faceLayout())` followed by `shell.render(*cv)`. Add a `FaceLayout{k,cy}` overload of `renderFace` (Face.h:71, Face.cpp:114-116).
3. **Keyboard:** new `Keyboard.h/.cpp` (pure logic, a later step after Text). It handles layout data (EN, RO), hit-testing on the round screen, shift and the 123 layer, long-press variants (a→ă â, i→î, s→ș, t→ț), backspace and done. It outputs UTF-8 and redraws only dirty keys. While it is open, set `touch.doubleTapS = 0` (h:21) and make Hold mean variants, not voice.
4. **TextField:** new `TextField.h/.cpp` with a UTF-8 buffer, a caret by codepoint, `wrap()` and 1–3 visible lines. Render the caret in `pal::kIce`.
5. **Alarms:** new `Alarms.h/.cpp` holding `{hhmm, daysMask, label[48], enabled, snoozeUntil}`, `next(localEpoch)` and `poll(localEpoch)`, which emits `AlarmDue`. Hook `localEpoch()` (main.cpp:272) into the loop after 493. Persist with Preferences key `alarms` in `saveMemory/loadMemory` 317-331 (or LittleFS on `spiffs`). Handle it in `Brain::event` (cpp:259) with a new `Cue::AlarmRing` (Brain.h:68) that drives the speaker/haptic in the 512-517 loop.
6. **Claude typing:** ClaudeLink cannot carry text (cpp:77-96 is the only message the device sends). Add a new transport-free `PhoneLink` modelled on ClaudeLink that sends `{"cmd":"ask","text":…}` and receives `{say, card, face, chips}` (SPEC §5.2). `ClaudeCard` opens TextInput and, on `TextCommit`, calls `phone.ask()`. Show replies with `Text`.
7. **Notes:** new `Notes.h/.cpp` holding a ring of UTF-8 notes with a sync flag. `NotesCard` opens TextInput. Store notes on LittleFS and sync them over PhoneLink.
8. **Tests and sim:** Keyboard hit-test, diacritic long-press, UTF-8 wrap/measure, Alarms next/due across midnight and DST offsets, and Shell routing. Add them as `test_*` before main (test_main.cpp:432). Add a sim scene `keyboard` that types "Salut, ce faci? ășțâî" and renders stills.

**Prototype (os/index.html):**
1. **Keyboard CSS:** add after `.caret` (179), for example `.kb .key` with a key height of 44–52 px.
2. **Keyboard layer:** add a `#kb` div inside `#screen` after `#pill` (228) so it survives `refresh()`.
3. **Keyboard JS:** add a new section before "input: gestures" (919). It holds `S.kb = {target, text, shift, layer, lang}` in `S` (647), plus `kbOpen(target, onDone)`, `kbHTML()`, and a `LAYOUT.kb` entry (642) that moves the face into the header.
4. **Input guards while `S.kb` is open:**
   - `tap` 938: skip the double-tap merge.
   - `holdStart` 921: show variants, not voice.
   - `act` 963: add cases `key`, `shift`, `bksp`, `done`.
   - The keydown handler 1068: send printable keys to the text and **do not** fire Space/Enter/d/Backspace.
5. **Text field:** add a `fieldHTML(text)` helper near `cardHTML` (684), using `.t2` + `.caret`.
6. **Alarms:**
   - Add `"alarms"` to `RING` (640), after `reminders`.
   - Add `alarms`, `d.alarms` and labels to both `STR` blocks.
   - Add `S.alarms` + `initData` (655).
   - Add `case "alarms"` in `cardHTML`.
   - Add `act` cases toggle/add/time picker.
   - Check due alarms in `frame`, where `lastSec` ticks (1159). On a hit, show an amber pill, `buzz`, and `soul.react("wake")`.
   - Add a next-alarm row to Today (693-704).
7. **Claude typing:** in `cardHTML` "claude" (729-733) and "talk" (705-709), add a chip with `data-act="type-claude"`. On done, create `S.voice={kind:"ask", p:{q:text,…}, phase:"think"}` and run the existing `answer()` path (874).
8. **Notes typing:** in `cardHTML` "notes" (716-721), add a chip with `data-act="type-note"`. Push `{key:"t"+n, text, sync:false, fresh:true}` and make `noteText` (662) return `n.text` when present.

## 10. Gotchas and naming
- **Timings to align in one spec:** hold 0.5 s in the firmware vs 380 ms in the prototype and SPEC; double-tap 0.40 s vs 330 ms.
- **Round-screen key pitch:** ~3.1 mm in the inscribed square, ~4.4 mm on the centre chord (02 §6). Plan prediction or a zone layout, not a bare QWERTY.
- **Legacy product name in user-visible strings; rename to SOUL:**
  - BLE name `Claude-<legacy>-XXXX` (main.cpp:445, ClaudeLink.h:84). The desktop pairing UI shows it.
  - The serial help banner (main.cpp:337) and the platformio.ini/main.cpp header comments.
  - The legacy id, class and JS variable on the prototype's device-body element (index.html:222, CSS 58-83, JS 638).
  - Internal names can stay: the library folder, namespace, board macros and NVS namespace.
