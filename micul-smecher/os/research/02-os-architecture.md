# SoulOS — OS architecture research (02)

*24 Sep 2026 · scope: how real OSes are layered, what transfers to SOUL on ESP32-S3, and a recommended SoulOS structure.*
Tags: **[V]** checked this session (vendor docs, repos, local files) · **[K]** prior knowledge, not re-checked · **[E]** estimate or inference.

## 0. Short version
- SoulOS should be a **single signed firmware image on ESP-IDF/FreeRTOS**, split into **services with one owner each**, a **shell/compositor that owns the screen**, and **apps that declare intents**. It should not copy iOS literally. Apple's lessons that fit a microcontroller are: the system owns input, text, notifications and background time, and apps only describe what they want.
- **Typing is a system service (TextInput).** Apps ask for text and never draw a keyboard. The input methods are voice, the on-screen keyboard (EN/RO with diacritic-aware prediction), the phone keyboard over BLE and quick replies.
- **Intents are the API.** `alarm.set`, `note.create`, `reminder.create` and similar intents are declared once. The UI, the keyboard, voice, the Claude connector, the ChatGPT app and API-key mode all call the same ones.
- **No third-party native code in v1.** Phase 2 runs user apps as **Moddable XS "mods" in SES Compartments**, the same path PebbleOS took in 2025–26 with "Alloy". WAMR is the fallback option.
- **Keep our SDF Canvas** and add layers, a compositor and a text engine. Don't add LVGL.
- **Leave the stock Arduino core:** its prebuilt ESP-IDF has power management, PSRAM XIP, anti-rollback and NVS encryption turned off [V local sdkconfig].

## 1. Constraints that shape the OS

| Item | Fact | Consequence |
|---|---|---|
| SoC | ESP32-S3R8: 2× Xtensa LX7 @ 240 MHz, 512 KB SRAM, 8 MB octal PSRAM, 16 MB flash [V hw note 02, research 06; platformio.ini `qio_opi`, 16MB] | 2 cores: radios+audio on core 0, UI on core 1. Internal SRAM (BLE, DMA, stacks) is the scarce resource; PSRAM holds framebuffers and VM heaps |
| MMU/MPU | No per-process MMU. ESP Privilege Separation (World/Permission Controller) supports C3 and S3 but is **beta** [V] | No hardware app isolation in v1; sandbox third-party code in a VM |
| Display | 466×466 CO5300 over QSPI, RGB565; a full frame is 434 KB [V board.h, SPEC §8.2] | Dirty-rect compositing. Full-frame transitions need a DMA double buffer |
| Touch | 1.75: CST9217, INT = GPIO11. 1.43: FT3168, no INT (polled) [V board.h, hw note] | On 1.75 touch can wake the chip from light sleep. On 1.43 it cannot |
| IMU / RTC | QMI8658; PCF85063. On 1.75 the IMU_INT and RTC_INT pins are unmapped (−1) in board.h [V local] | **Check the schematic** before promising lift-to-wake and alarm wake from deep sleep |
| PMU | AXP2101 with PWR key [V research 06] | Power button and "off" state go through the PMU IRQ |
| Audio | ES8311 DAC + ES7210 2-mic ADC, I2S [V board.h] | Voice pipeline gets its own task and internal-RAM buffers |
| Current fw | ~800 KB `firmware.bin` for amoled175 [V local]. Arduino core 3.3.12 = IDF 5.5.5. Its libs have `PM_ENABLE` off, `SPIRAM_XIP_FROM_PSRAM` off, `APP_ANTI_ROLLBACK` off, `NVS_ENCRYPTION` off; NimBLE on with internal alloc, max 3 conns; `APP_ROLLBACK_ENABLE` on [V local sdkconfig] | Must build with a custom sdkconfig (pioarduino `framework = arduino, espidf` or pure IDF) |
| Offline voice | ESP-SR MultiNet offline commands support EN/CN only [K] | Romanian offline = keyboard and touch. **The keyboard is required, not optional** |

## 2. Apple iOS / watchOS: lessons that transfer

| Apple layer [K] | What it does | SoulOS equivalent |
|---|---|---|
| Core OS: XNU (Mach+BSD), launchd, IOKit drivers, Secure Enclave, sandbox kernel ext. | scheduling, memory, drivers, process isolation, boot chain | FreeRTOS (IDF) + BSP drivers + Secure Boot v2/flash encryption. **No process isolation** (see §1) |
| Core Services: Foundation, Core Data, CloudKit, networking | data types, persistence, sync | `Store` (document records + sync), `Link` (BLE/Wi-Fi), `Time` |
| Media: Core Graphics, Core Text, Core Animation (render server), AVFoundation | drawing, text, compositing out of the app's thread, audio | Canvas SDF + TextEngine + Compositor (in the Shell) + Voice/Audio |
| Cocoa Touch: UIKit/SwiftUI, UserNotifications, App Intents, WidgetKit | app model, controls, notifications, actions exposed to Siri/AI, timelines | SoulKit (cards, widgets), Notify, **Intents**, Today timeline |
| SpringBoard / backboardd | home screen as a system app; event routing | Shell (home = face) + Input service |

- **Lifecycle is owned by the system** [K]. iOS apps move through not-running → inactive → active → background → suspended, and they can be killed at any time, so they save state on every transition. watchOS goes back to the watch face after about 2 min and wakes apps only for budgeted background refreshes. *SoulOS:* cards get `enter/exit/suspend` callbacks and must persist to `Store`. The Shell can drop any card at any time and returns home after a timeout (SPEC §4.6).
- **Sandbox and entitlements** [K]. Capabilities are declared in a signed manifest (entitlements, Info.plist background modes). Sensitive access goes through a system consent prompt with a purpose string. The mic/camera indicator dot is drawn by the OS, never by the app. *SoulOS:* every app manifest lists `caps` (mic, notify, net.host:x, store:notes, alarm). The OS draws the ice mic ring below the app layer (SPEC §7.2), the same pattern as Apple's indicator dot.
- **Text input system** [K]. Apps implement `UITextInput`, and the keyboard runs out of process. Third-party keyboards are app extensions with **no network unless the user grants "Full Access"**, and secure fields force the system keyboard. On watchOS an app calls one API, the system offers dictation, Scribble, a QWERTY/QuickPath keyboard or the **iPhone keyboard via a notification** [V Apple support], and the app gets back a string. *SoulOS:* copy this exactly: `text.request()` returns a string (§6).
- **Notifications** [K]. A central service handles delivery. Categories carry actions, and interruption levels are passive, active, time-sensitive and critical. Focus modes filter by level. The watch shows a short look, then a long look. *SoulOS:* map cream to passive/active, amber to time-sensitive, and alarm to critical (the only level that bypasses do-not-disturb). The phone forwards and the device renders.
- **Background modes are declared, not taken** [K]. Examples are audio, bluetooth-central and background fetch, each with budgets. *SoulOS:* apps declare **triggers** (time, alarm, BLE message, intent). The OS wakes them, gives them a slice of time, then suspends them. No app polls.
- **Timelines and declarative widgets** [K]. WidgetKit complications render from precomputed timeline entries without running the app. *SoulOS:* Today rows and the home label come from timeline entries pushed by apps or the phone.
- **App Intents** [K]. Apps expose typed actions to Siri, Shortcuts and Apple Intelligence. *SoulOS:* intents are the single action surface for the UI, voice and every AI (decision D6).
- **The watchOS path** [K]. watchOS 1 ran app logic on the iPhone. watchOS 2 moved it onto the watch, and watchOS 6 added independent apps and an on-watch store. *SoulOS:* start with logic on the phone or cloud and declarative cards on the device, then move logic on-device once there is a sandbox.

## 3. Watch and embedded OSes

| OS | Base / HW | UI | Apps | Take-away |
|---|---|---|---|---|
| **PebbleOS** (Google open-sourced it Jan 2025 at github.com/google/pebble; continued by Core Devices at github.com/coredevices/PebbleOS) [V] | FreeRTOS on Cortex-M. Now **NimBLE**; fixed tasks KernelMain, KernelBackground, App, Worker, BT, NewTimers [V]. Pebble Time 2 and Round 2 use a SiFli SF32LB52J (2× M33, 240 MHz + 24 MHz, ~512 KB RAM) [V] | own graphics + compositor, PFS filesystem [V] | Native C apps run **unprivileged, MPU-fenced**; `sys_*` syscalls via `DEFINE_SYSCALL` [V]. One foreground App + one background Worker. JS: Rocky.js on JerryScript (2016) [V], now **"Alloy" = Moddable XS** on Time 2 and Round 2, with a 32 KB static XS machine per app [V issue #1621]. AppMessage key/value to phone; PebbleKit JS ran on the phone [V/K] | Closest analogue to SOUL: 512 KB-class MCU, single app plus worker, the phone does the networking. **They moved from JerryScript to XS** |
| **Flipper Zero** [V/K] | FreeRTOS + "Furi" core on STM32WB55 (256 KB RAM) [K] | ViewPort/ViewDispatcher/SceneManager over the `gui` service [K] | Services register **records** (`furi_record_open("gui")`, "storage", "notification") [K]. External **.fap** = ELF + metadata, copied to RAM, relocated, symbols resolved from `api_symbols.csv` with **major.minor API versioning** [V]. mJS scripting [K] | Named service registry. A stable, versioned API table is what makes third-party apps survive OS updates |
| **InfiniTime** (PineTime) [V] | FreeRTOS + LVGL + NimBLE + LittleFS + MCUBoot on nRF52832 (64 KB RAM, 4 MB SPI NOR) [V/K] | LVGL | compiled-in only | Tiny RAM still runs a usable watch. OTA must be **validated by the user or self-test**, otherwise MCUBoot reverts [K] |
| **ZSWatch** [V] | Zephyr on nRF5340 (512 KB RAM, 1 MB flash) | LVGL 9 | Self-registering built-in apps; App Manager states ACTIVE / INACTIVE / NOT_WORN_STATIONARY [V] | **zbus pub/sub** channels decouple sensors, BLE, managers and apps. iOS **ANCS/AMS/CTS** work without a companion app; Android goes through Gadgetbridge [V] |
| **Tizen wearable** | Linux, EFL; native + web apps [K] | EFL | Samsung moved to Wear OS in 2021 [K] | A custom OS lives or dies on ecosystem cost. Keep the API tiny and stable |
| **Wear OS** | Android, ≥1–2 GB RAM [K] | Compose | **Tiles** (declarative layouts rendered by the system), complications, and the **Watch Face Format** (declarative XML, no code) [K] | Declarative surfaces save power and need no app code running. Same idea as our JSON cards |

## 4. App runtimes on ESP32-S3 (for phase-2 user apps)

| Runtime | Flash | RAM (min) | Speed [E] | Sandbox | License | Fit for SOUL |
|---|---|---|---|---|---|---|
| **Moddable XS** (mods) | host engine a few hundred KB [E]; mods run **in place from flash** as `.xsa` bytecode [V] | 32 KB machine on Pebble [V]; InfoQ 2018: "<32 KB" [V] | good interpreter | **SES Compartments**: module map + globals whitelist, frozen primordials [V] | XS core Apache-2.0 (Marvell); Moddable-modified runtime files LGPLv3, tools GPLv3; commercial licence available [V] | **Best fit.** Modern JS (the language LLMs write best, and the one our web prototype uses), built for user-installed mods, 256 KB "xs" partition on ESP32 [V], Pebble precedent. The LGPLv3 relink duty clashes with locked secure boot, so buy a commercial license or ship relink info [E] |
| **WAMR** | ~56–59 KB interp, ~29 KB AOT runtime (Cortex-M4) [V] | tens of KB + linear memory [E] | interp medium; AOT near-native [K] | linear-memory bounds; host decides imports | Apache-2.0 [K] | Strong fallback: any language (C, Rust, Zig, AssemblyScript), Espressif component exists [V]. AOT for Xtensa is possible, but executable memory handling on S3 needs work [E] |
| wasm3 | ~64 KB | ~10 KB [V] | fastest pure interpreter [V claim] | same as Wasm | MIT [K] | **Minimal maintenance** since 2022 [V]. Avoid for a product |
| JerryScript | ~160 KB | <64 KB [V] | slow–medium | realm only, weak | Apache-2.0 [K] | ES5.1 era. Pebble moved off it. Skip |
| MicroPython | ~1.6 MB | ~64 KB initial heap, grows [V] | slow | none between apps | MIT [K] | Great for prototyping, poor for untrusted apps |
| Lua 5.4 / Berry | ~100–200 KB / ~40 KB ROM [K]; Berry ~10 KB RAM [V] | small | medium (Lua fastest of scripts) [K] | env restriction + allocator caps [K] | MIT [K] | Berry is proven in Tasmota with LVGL bindings [V]. Weaker developer and LLM story than JS |
| Toit | full VM | — | ~20× MicroPython (vendor claim) [V] | **containers**, install/remove at runtime [V] | [K?] | Nice design but niche language. Reference for the container lifecycle |

Verdict: v1 ships **no user code**. Phase 2 adds **XS mods in Compartments**, each with a capability-mapped module set (`soul/store` scoped to its own collection, `soul/net` restricted to its declared hosts, `soul/ui` = SoulKit cards only), a 32–64 KB machine in PSRAM, a CPU watchdog per slice and API versioning on the Flipper model.

## 5. Graphics and text: our Canvas vs LVGL

| | Canvas SDF + SoulKit (ours) | LVGL 9 |
|---|---|---|
| Face | already built: anti-aliased SDF, halo, dirty rects [V local Canvas.h] | must be ported into a custom widget, or run as a second pipeline |
| Footprint | ~60 KB code + fonts [E, SPEC] | >64 KB flash (180 KB recommended), heap >48 KB recommended [V] |
| Text | to build: 4bpp atlases, UTF-8, per-glyph font fallback, kerning, round-aware wrap, caret/selection | mature: `lv_font_conv` subsets 1–4 bpp [V], Tiny TTF (stb_truetype, kern/GPOS) [V], font `fallback` chain [K], textarea + keyboard widgets |
| Verdict | **Keep.** SoulOS screens have at most 3 rows, and a single pipeline keeps the face and the cards in one compositor | Fallback only if on-device Settings grows complex |

Text engine requirements (all testable in `sim`):
- **Romanian:** Ă ă Â â Î î (Latin-1/Ext-A), **Ș ș Ț ț comma-below U+0218–U+021B**, the quotes „ ” and «». Normalize incoming cedilla ş ţ (U+015E/F, U+0162/3) to comma-below, and store text as UTF-8 NFC [K].
- **Fallback chain Fredoka → Nunito**, applied per glyph, because Fredoka lacks some of these glyphs (SPEC §8.1).
- **Budget:** about 130 glyphs × 4 sizes (22/27/34/104-digits) ≈ 180 KB, memory-mapped from the app image [E, SPEC §8.2].
- **Round layout:** each line's width = the chord at its y, 2·√(r²−y²), minus the margin, so text fills the circle instead of the 330 px inscribed square.

## 6. Text input as a system service (keyboard, notes, alarms, writing to Claude)
Architecture (Apple watchOS model + Android IME split) [E]:
```
app/card ──text.request({kind:text|number|time|date, prompt, initial, lang:auto|ro|en,
                         suggestions[], maxLen, secure}) ──► TextInput service (system)
   ▲                                                         ├─ Compose sheet (overlay card; face shrinks to header)
   │  Ev::TextCommit{string} / Ev::TextCancel                ├─ Methods: 1 Voice (Voice→STT, cloud)  2 Keyboard (on-screen)
   └─────────────────────────────────────────────────────────┤           3 Phone keyboard (companion app pushes text over BLE)
                                                             │           4 Quick replies (app + AI suggestions)  5 BT HID keyboard (later; NimBLE central role is on [V local])
                                                             ├─ Layout engine: pluggable layouts (EN, RO) from data files
                                                             ├─ Predictor: per-language frequency DAWG in flash (mmap), user dict in LittleFS
                                                             └─ Pickers for kind=time|date (wheel/ring, not letters) → alarms need no typing
```
- **Apps never see keystrokes**, only committed text, as with iOS secure fields and keyboard extensions. The IME has no network. Prediction is on-device. Nothing typed leaves the device unless the requesting app's intent sends it.
- **Round-screen keyboard maths** [E]: 466 px / 43.76 mm = **10.65 px/mm**. Inscribed square = 329 px (30.9 mm), so a 10-key QWERTY row has 3.1 mm pitch there and ~4.4 mm (46 px) on the centre chord. Apple Watch 41 mm is 352 px wide at 326 ppi ≈ 27.4 mm, i.e. ~2.7 mm pitch [K+E], and Apple makes it work with **QuickPath swipe + prediction**. A 3×3 zone layout (T9-style) gives ~10 mm keys but needs dictionary disambiguation, which old RO feature phones shipped [K]. The engine must support both layouts. Pick one through user tests (UX doc).
- **Romanian diacritics without extra keys:** index the dictionary on diacritic-folded keys (s = ș, t = ț, a = ă/â, i = î). Typing "sa" offers "să", "șa", "sa" ranked by frequency. Long-press on a/i/s/t opens a mini-ring of variants. Estimate for 40–60k words per language ≈ 200–500 KB flash each (check word-list licences) [E].
- **Notes and alarms offline:** `alarm.set` uses the time picker (no letters) plus an optional label typed with the keyboard. `note.create` uses the keyboard or dictation. "Write to Claude" uses the same Compose sheet and sends through the AI broker when a link exists, otherwise queues in `Store` (outbox).

## 7. Storage
- **Filesystems** [K]: LittleFS is power-loss-safe with dynamic wear levelling, the right choice for user documents. FAT needs the wear-levelling layer and isn't power-safe for metadata. SPIFFS is legacy. NVS is for small key/value data (settings, BLE bonds, tokens) and is encrypted separately (flash encryption can't cover it [V]).
- **Flash write stalls:** flash erase/write suspends the cache, so non-IRAM tasks stall and the UI stutters [K]. The S3 option `SPIRAM_XIP_FROM_PSRAM` keeps code running from PSRAM during writes [K; off in stock libs, V local]. `Store` batches writes and flushes when the screen is idle or before sleep.
- **Data model** [E]: collections `notes/ reminders/ alarms/ diary/ outbox/ settings`, one CBOR record per item `{id(ULID), rev, updated_at, deleted, body}`. Last-writer-wins sync with the phone by `rev`. Alarms are stored as **local wall time + recurrence + POSIX TZ** (Romania EET/EEST DST), and the next fire time is computed in UTC.
- **Proposed 16 MB partition map** [E] (the current map is the Arduino `default_16MB.csv`: 2×6.25 MB app + 3.4 MB SPIFFS [V local]):

| Name | Type | Size | Purpose |
|---|---|---|---|
| nvs | data/nvs | 64 KB | settings, BLE bonds, session tokens (encrypted) |
| nvs_keys | data/nvs_keys | 4 KB | NVS encryption keys (if the flash-encryption scheme is used) |
| otadata | data/ota | 8 KB | A/B selector + rollback state |
| ota_0 / ota_1 | app | 4 MB each | firmware + fonts + dictionaries + sounds, updated atomically together |
| mods | data (custom) | 1 MB | phase-2 XS mods (.xsa, run in place) |
| store | data/littlefs | ~6.8 MB | user documents, user dictionary, logs, caches |
| coredump | data/coredump | 64 KB | crash reports uploaded via the phone |

## 8. OTA, secure boot, flash encryption
- **A/B OTA** [V]. `ota_0`/`ota_1` plus `otadata`. With rollback enabled, a new image boots as *pending verify*. It must call `esp_ota_mark_app_valid_cancel_rollback()`, otherwise the bootloader reverts on the next reset. **Self-test before marking valid:** panel ID read, touch responds, Store mounts, BLE advertising, 30 s without a panic.
- **Anti-rollback** (`secure_version` in eFuse) [V] refuses older images, but the eFuse bits run out. Bump it only for security fixes. It requires a partition table with no factory partition [V].
- **Delivery:** the phone downloads a signed image and streams it over BLE (L2CAP CoC or GATT with a large MTU) [K], resumable in 4 KB chunks. Wi-Fi OTA is optional.
- **Secure Boot v2 on S3 = RSA-3072 (RSA-PSS) only.** Up to **3 keys**, revocable. Verified at every boot **and on each OTA** [V].
- **Flash encryption:** XTS-AES-128 or 256 [V]. With it enabled, **PSRAM traffic through the cache is encrypted too** [V]. Release mode means UART can't write plaintext and only OTA can update [V]. Pair it with Secure Boot to close the TOCTOU swap [V]. NVS needs its own encryption (HMAC-based on S3 [K]).
- **Policy** [E]: dev kits stay open. Production units get keys burned at the factory (signing key in an HSM), JTAG disabled and secure download mode. Any LGPL component needs a relink path or a commercial licence (see §4).

## 9. BLE: services to phone and desktop
One NimBLE host (PebbleOS and InfiniTime use NimBLE too [V]). Each client gets its own GATT service:

| Service | Role | Content |
|---|---|---|
| **SoulOS Link** (custom 128-bit) | peripheral | `ctrl_rx` (write-no-rsp) / `ctrl_tx` (notify): versioned **CBOR** frames (intent calls, cards, timeline, sync, text from phone keyboard). `audio_up` (notify, Opus 16 kb/s) / `audio_down` (TTS). `bulk` for OTA and sync (L2CAP CoC preferred) |
| **Claude Buddy** (NUS UUIDs, JSON lines, passkey) | peripheral | existing `ClaudeLink` + `ble_link` [V local]. Keep the protocol untouched |
| Battery 0x180F, Device Info 0x180A | peripheral | standard [K] |
| **ANCS / AMS / CTS clients** (iOS) | GATT client over the same link | iPhone notifications, media control and time **without our app** [V ZSWatch] → Music card and notifications work on day 1 |
| HID host (later) | central | pair a Bluetooth keyboard for long texts |

- **Security:** LE Secure Connections with **numeric comparison** (the device has a screen) and bonding stored in encrypted NVS. Use 2M PHY + DLE + MTU 247–512 for audio and OTA [K].
- **Transports behind one `Link` API:** BLE → phone (default), BLE → desktop (Claude), and later Wi-Fi → SOUL cloud for home use without the phone. AI keys never sit on the device, only short-lived session tokens (SPEC §7.6).

## 10. Power management

| State | Display | CPU | Radios | Wake by |
|---|---|---|---|---|
| Active | on, face 30 fps | 240 MHz | BLE conn interval 15–30 ms | — |
| Idle / dim | face asleep 5–10 fps, 110/255 brightness [V main.cpp] | DFS 80–160 MHz | BLE 50–100 ms | touch, button, event |
| Screen off | panel SLPIN (0x10) [V hw note] | **auto light sleep** (tickless idle) | BLE kept, interval ≥ 200 ms [V] | touch INT (1.75), PMU key IRQ, RTC/alarm timer, BLE, IMU INT if wired |
| Off / ship | off | deep sleep or PMU off | off | PMU key, RTC alarm |

- **Chip numbers** [K datasheet]: light sleep ≈ 240 µA, deep sleep ≈ 7–8 µA. The AMOLED is the largest load, and black pixels draw ~0.
- **Auto light sleep needs `PM_ENABLE` + `FREERTOS_USE_TICKLESS_IDLE`** [V], both off in the stock Arduino libs [V local]. Keeping BLE alive in light sleep needs a precise low-power clock: an external 32 kHz crystal or the main XTAL kept on [K]. **Check whether the board has a 32 kHz crystal.**
- **Alarms must fire from every state:** keep the next alarm in RTC memory, set the PCF85063 alarm and an ESP RTC timer wake, and let the PMU keep the rail. Ring with speaker + haptic (LRA + DRV2605L is in the BOM plan, research 06) even with DND on (critical level).
- **Frame pacing is already in the firmware:** 30 fps awake, fewer asleep, stopped face-down (SPEC §8.2).

## 11. Tasks, cores, memory

| Task | Core | Prio [E] | Stack/heap | Notes |
|---|---|---|---|---|
| NimBLE host + controller | 0 | high | internal | IDF-pinned |
| Audio (I2S in/out, VAD, Opus) | 0 | highest app | internal ~40 KB (SPEC) | real-time, never blocks on flash |
| Link / protocol (CBOR, OTA writer) | 0 | mid | internal | owns BLE queues |
| **UI: Shell + Brain + cards + compositor** | 1 | mid-high | PSRAM framebuffers | the only task that touches Canvas and panel (like iOS main thread / Pebble App task) |
| App VM (phase 2) | 1 | below UI | PSRAM 32–64 KB/mod | time-sliced, watchdog |
| Store / sync / log | 0 | low | internal small | batches flash writes |
| Power / housekeeping | 0 | low | tiny | sleep decisions, battery |

- **Event bus:** grow today's `Ev` enum + `EvQueue` [V local Events.h] into a typed `Msg{topic, payload}` pub/sub, like zbus [V] or Flipper records. Each service owns its state, and others talk to it only through messages or its API.
- **Keep native portability:** every service except BSP, radio and audio compiles in `env:native`/`sim` with Unity tests (the 24 existing tests are the pattern).

## 12. Recommended SoulOS layer diagram
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ L5 EXPERIENCES  Home=Face · Today · Talk · Notes · Reminders/Alarms · Focus ·  │
│                 Claude · Diary · Translate · Music · Settings   (+ P2: mods)   │
├──────────────────────────────────────────────────────────────────────────────┤
│ L4 SOULKIT (app framework)  manifest{id, caps, intents, triggers} · Card       │
│    lifecycle enter/exit/suspend · widgets Text/TextField/Chip/List/Ring/Picker │
│    · text.request · notify.post · timeline.push · intents registry → tool JSON │
│    runtimes: native C++ (system apps) │ XS Compartments (P2, capability-mapped)│
├──────────────────────────────────────────────────────────────────────────────┤
│ L3 SYSTEM SERVICES (one owner each, talk via bus)                             │
│  Shell+Compositor · Brain(character) · Input(touch/gesture/button/IMU) ·      │
│  TextInput(IME, predictor, pickers) · Voice(I2S/VAD/Opus) · Notify(levels,DND)│
│  · Time/Alarm · Store(records+sync+outbox) · Link(SoulOS Link, Claude Buddy,  │
│  ANCS/AMS/CTS) · AI broker(route intents+voice: SOUL voice | own key | Claude │
│  connector | ChatGPT app | offline) · Power · Update(OTA) · Settings · Crash  │
├──────────────────────────────────────────────────────────────────────────────┤
│ L2 CORE  Canvas SDF + TextEngine(4bpp, fallback, round wrap) · Msg bus ·      │
│          PSRAM/internal allocators · LittleFS · NVS(enc) · NimBLE · esp_pm ·  │
│          esp_ota · mbedTLS · CBOR/JSON                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ L1 BSP   CO5300 QSPI · CST9217/FT3168 · QMI8658 · PCF85063 · AXP2101 ·        │
│          ES8311/ES7210 · button · LRA/DRV2605L · (board profile 1.43 / 1.75)  │
├──────────────────────────────────────────────────────────────────────────────┤
│ L0 BOOT  ROM → 2nd-stage bootloader (Secure Boot v2, flash encryption,        │
│          A/B + rollback) → ESP-IDF 5.5 / FreeRTOS SMP                         │
└──────────────────────────────────────────────────────────────────────────────┘
Phone app (iOS/Android): relay (audio, AI, net), tools (reminders, messages, calendar), phone keyboard,
OTA download, backup/sync, settings, app catalogue.   Cloud: STT/LLM/TTS, memory, MCP connector (Claude), ChatGPT app.
```

## 13. Architecture decisions
1. **D1 · ESP-IDF 5.5 + FreeRTOS as the kernel, with our own sdkconfig.** *Why:* power management, PSRAM XIP, NVS encryption and anti-rollback are all off in the stock Arduino libs [V]. Migrate via pioarduino `arduino, espidf` and drop Arduino APIs as each service is rewritten. Arduino_GFX can stay until `esp_lcd` replaces it.
2. **D2 · One signed monolithic image, no hardware process isolation in v1.** *Why:* S3 Privilege Separation is beta [V]. Pebble got isolation from the Cortex-M MPU, which the S3 doesn't offer the same way. Safety comes from service ownership + review + a VM sandbox for anything third-party.
3. **D3 · Single UI owner on core 1; radios, audio and storage on core 0; typed pub/sub bus.** *Why:* this avoids locks around Canvas and panel and mirrors iOS main thread, Pebble App task and ZSWatch zbus [V]. Audio never waits on flash writes.
4. **D4 · Keep the SDF Canvas; add Compositor (layers: face, card, overlay, keyboard, system rings) and TextEngine; no LVGL.** *Why:* one pipeline for the face and the UI, ~60 KB vs ≥180 KB recommended for LVGL [V], and the face is the product. RO glyph and round-wrap tests are mandatory in `sim`.
5. **D5 · TextInput is a system service with 5 methods (voice, on-screen, phone keyboard, quick replies, BT keyboard later) and time/date pickers.** *Why:* this is the watchOS model [V/K]. Offline RO voice isn't feasible [K], so typing must work with no phone and no AI. Apps get only committed text, which protects privacy.
6. **D6 · Intents are the one API.** Each app manifest declares typed intents (`alarm.set{time,label,repeat}`, `note.create{text}`, `reminder.create`, `timer.focus`, `claude.reply`…). The UI, keyboard flows, voice, the Claude connector (MCP), the ChatGPT app and API-key mode all call them, and LLM tool schemas are generated from the manifests. *Why:* App Intents lesson [K]. It keeps "works without AI" and the four AI modes identical in behaviour and testable offline.
7. **D7 · v1 apps = built-in native cards + declarative JSON/CBOR cards and timelines from phone or cloud. Phase 2 = Moddable XS mods in Compartments; WAMR is the backup.** *Why:* the Tiles/WidgetKit/watchOS 1 path costs no runtime. XS mods run in place from flash with SES capability control [V], and PebbleOS uses them on 512 KB-class watches [V]. Settle the LGPLv3 vs secure boot question (commercial licence) before shipping [V/E].
8. **D8 · Storage = LittleFS document store (CBOR records, rev-based sync, outbox) + encrypted NVS for small secrets. Assets live inside the app image.** *Why:* power-loss safety, atomic A/B updates of code + fonts + dictionaries, simple phone sync. Flash writes are batched to avoid UI stalls.
9. **D9 · A/B OTA with rollback + on-device self-test before marking valid; the phone streams signed images over BLE; eFuse anti-rollback only for security fixes.** *Why:* this is the InfiniTime/MCUBoot lesson [K]. IDF gives it natively [V]. eFuse bits are finite [V].
10. **D10 · Production security = Secure Boot v2 (RSA-3072, 3 revocable keys) + flash encryption release mode (covers PSRAM) + NVS encryption + JTAG off. No AI keys on the device.** *Why:* it's all verified S3 capability [V]. It protects notes, diary and bonds on a lost device and matches SPEC §7.
11. **D11 · One NimBLE stack running SoulOS Link (CBOR, versioned), Claude Buddy (unchanged), DIS/BAS, and ANCS/AMS/CTS clients; LE Secure Connections with numeric comparison.** *Why:* iOS notifications, music and time work without our app [V]. The Claude buddy protocol is fixed by Anthropic's reference. Versioned frames let the phone and device update independently (the Flipper API-version lesson [V]).
12. **D12 · Power state machine (Active / Idle / Screen-off auto-light-sleep / Off) owned by the Power service; alarms are guaranteed from every state.** *Why:* the AMOLED dominates the budget and light sleep keeps BLE [V]. Alarms are a promised feature. **Open hardware checks for the 1.75:** IMU INT and RTC INT routing, 32 kHz crystal, haptic driver.

## Sources
- PebbleOS: opensource.googleblog.com/2025/01/see-code-that-powered-pebble-smartwatches.html · betanews.com/2025/01/28/google-pebble-source-code-release-rebble · pebbleos-core.readthedocs.io/en/latest/architecture/ · …/development/moddable.html · github.com/coredevices/pebbleos/issues/1621 · developer.repebble.com/guides/alloy/watchfaces · cnx-software.com/2025/05/14/sifli-sf32lb52j…core-time-2 · liliputing.com (Pebble Round 2)
- Flipper: developer.flipper.net/flipperzero/doxygen/apps_on_sd_card.html · github.com/flipperdevices/flipperzero-firmware/blob/dev/documentation/AppsOnSDCard.md
- InfiniTime: github.com/InfiniTimeOrg/InfiniTime · ZSWatch: zswatch.dev/docs/development/architecture · github.com/ZSWatch/ZSWatch
- Runtimes: github.com/wasm-micro-runtime/wasm-micro-runtime · components.espressif.com/components/espressif/wasm-micro-runtime · github.com/wasm3/wasm3 · github.com/jerryscript-project/jerryscript · Moddable-OpenSource/moddable documentation/xs/mods.md · moddable.com/license · infoq.com/news/2018/11/moddable-iot-javascript-engine · micropython.org/download/ESP32_GENERIC_S3 · tasmota.github.io/docs/Berry · toit.io
- LVGL: docs.lvgl.io/master/introduction/requirements.html · github.com/lvgl/lv_font_conv · lvgl.io/docs/open/9.3/details/libs/tiny_ttf
- Espressif: docs.espressif.com/projects/esp-idf/en/stable/esp32s3/security/secure-boot-v2.html · …/esp32s3/security/flash-encryption.html · …/api-reference/system/ota.html · …/esp32s3/api-reference/system/sleep_modes.html · github.com/espressif/esp-privilege-separation
- Apple: support.apple.com/guide/watch/enter-text-apdaf7837856/watchos · macrumors.com/2022/06/07/apple-watch-quicktype
- Local: firmware/platformio.ini, src/board.h, src/main.cpp, src/ble_link.cpp, lib/Suflet/src/{Canvas,Events}.h, ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig (IDF 5.5.5), os/SPEC.md, research/02, research/06
