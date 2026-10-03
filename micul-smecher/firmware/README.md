# Firmware „Suflet” v0 — sufletul companionului

Ochii vii, dispoziția, cele 24 de reacții, personalitatea născută din cip și legătura
„works with Claude”. Rulează pe plăcile Waveshare cu AMOLED rotund 466×466.

| Placă | Mediu PlatformIO | Ce are |
|---|---|---|
| ESP32-S3-Touch-AMOLED-1.43 | `amoled143` | ecran, touch FT3168, IMU, RTC — fără sunet |
| ESP32-S3-Touch-AMOLED-1.75 | `amoled175` | + 2 microfoane, difuzor, PMU AXP2101, buton de pornire |
| ESP32-S3-Touch-LCD-2.8C (SOUL M) | `lcd28` | IPS 2,8″ 480×480, touch GT911, IMU, RTC, buzzer — vezi secțiunea „SOUL M” (engleză) |

```bash
pio run -e amoled143 -t upload      # sau amoled175 / lcd28
pio device monitor -b 115200        # tastezi ? pentru comenzi
pio test -e native                  # 55 de teste pe PC
pio run -e sim && .pio/build/sim/program /tmp/out all   # simulatorul (cadre brute)
python3 tools/frames_to_media.py /tmp/out ../media --mp4 --gif --sheet
```

## Structura
- `lib/Suflet/src/` — **sufletul, fără hardware** (C++17): `Canvas` (randare SDF anti-aliased),
  `Face` (ochi parametrici), `Brain` (dispoziție, atenție, reacții, moduri), `Personality`
  (semința din cip → nuanță, rarități, temperament), `Gestures` (tap/ținere/mângâiere, ridicare,
  scuturare, cădere, ciocănit, orientare), `EyeMotion` (ochii simt IMU-ul: rămân la nivel, pupile ca
  niște bile, amețesc la rotire, dublu-tap pe carcasă, da/nu din cap — aceeași matematică ca `eyes.js`),
  `ClaudeLink` (protocolul Hardware Buddy al Claude Desktop).
- `src/` — placa: `main.cpp` (bucla, ecran cu randare parțială, touch, IMU, ceas, baterie, memorie
  NVS, comenzi seriale, bucla demo), `board.h` (pini), `ble_link.cpp` (Bluetooth securizat, adaptat
  din anthropics/claude-desktop-buddy, MIT).
- `sim/` — simulatorul pe PC: aceleași fișiere din `lib/Suflet`, evenimente scriptate → cadre.
- `test/` — teste Unity pe PC.

## Legarea cu Claude
Claude Desktop → Help → Troubleshooting → **Enable Developer Mode** → Developer → **Open Hardware
Buddy…** → Connect → „Claude-Suflet-XXXX” → codul de 6 cifre de pe ecran.
Ține degetul 1,2 s = aprobă · dublu-tap = refuză · tap simplu = doar boop.

## De calibrat pe placa reală (5 minute)
- Panou SH8601 în loc de CO5300 → `-DSUFLET_PANEL_SH8601`.
- Imagine rotită → `-DSUFLET_ROTATION=90|180|270`.
- Touch oglindit → `TOUCH_MIRROR_X/Y` în `board.h`.
- Axele IMU → `IMU_MAP` în `board.h` (comanda serială `i`: fața în sus ≈ (0,0,+1); giroscopul pe
  aceleași axe — BRINGUP.md §3b).

## Neverificat încă pe hardware
Codul compilează pentru ambele plăci și logica e testată pe PC, dar placa fizică n-a fost încă în
mână: orientarea ecranului, sensul touch-ului/IMU, luminozitatea și împerecherea BLE cu Claude
Desktop se confirmă la primul flash.

## SoulOS v1 modules (English)
The first real SoulOS pieces live in `lib/Suflet/src`, hardware-free and unit-tested:

- **Touch with coordinates** — `TouchGestures` emits `TouchEv{e, x, y, t}`. `TouchMode::Text`
  reports raw `TouchDown/Move/Up` + `HoldStart` (380 ms, 12 px) with no double-tap merge, so fast
  typing never loses a key; switching mode mid-touch swallows that touch.
- **Text on the Canvas** — `Canvas::drawText` / `measureText` (UTF-8, left/centre/right, clipped,
  anti-aliased 4-bit glyphs) and `roundRect`. `tools/gen_font.py` rasterises Nunito (OFL,
  `tools/fonts/`) into `FontData.h`: 22/26/36 px (ASCII, ă â î ș ț Ă Â Î Ș Ț, keyboard variants,
  „ ” … – € …) + 88 px digits, **84.8 KB of flash**. Cedilla ş ţ render as comma ș ț.
- **Keyboard** (`Keyboard`, `TextField`, `Predictor`) — the Round QWERTY of
  `os/research/04` §1–12: spec geometry and hit-testing (edge keys own the rim), shift / caps lock /
  auto-capitals, `?123` and `#+=`, long-press variant tray (RO letter first), ⌫ hold-repeat and
  word delete, undo, double space = ". ", EN+RO suggestions (`tools/gen_words.py`, hand-made lists,
  see `tools/words/README.md`) and RO auto-diacritics only in Romanian sentences (⌫ reverts and
  locks). Not yet: swipe typing, the Gaussian decoder, trackpad, dictation.
- **TimePicker** — the Rim-Dial: 24 h sundial hours → minutes (5-min snap when fast), live
  "rings in 9 h 12 min", ✓.
- **Alarms** — hour, minute, weekday mask, label, enabled, snooze; `nextFire`/`poll` from local
  time (midnight, week wrap, one-shot, grace window) and a versioned binary blob for NVS.
- **Shell** — a minimal router: long-press the face → note field; serial `A` → time picker (the
  alarm is saved to NVS key `alarms`), `N` note, `L` list alarms, BOOT = back. Keyboard/picker
  screens are a persistent layer redrawn only when changed.

Flash on `amoled143`: 785,035 → 920,919 B (+136 KB: fonts 85 KB, code + word list ~51 KB);
static RAM 35,876 → 38,564 B.

```bash
python3 tools/gen_font.py && python3 tools/gen_words.py      # regenerate the headers
.pio/build/sim/program /tmp/out keyboard && .pio/build/sim/program /tmp/out timepicker
python3 tools/frames_to_media.py /tmp/out ../media --png --prefix soulos_fw_ --only keyboard,timepicker
```

## SOUL M: Waveshare ESP32-S3-Touch-LCD-2.8C (`lcd28`)
Size M from `../research/12-ecran-mai-mare.md`: a round **2.8" IPS, 480×480** (active disc ≈ 70 mm)
instead of the 1.75" AMOLED. Same OS, same library; only the board layer and the display
geometry differ. On this disc a keyboard key is **~6.6 mm wide and ~7.9 mm tall** (6.7 mm if the lit disc is the full 71 mm; 4.1 × 4.9 mm on S).

**Flash without tools:** <https://espressif.github.io/esptool-js/> → Connect → address `0x0` →
`release/SOUL-2.8C-install.bin` → Program (see `release/README.md`). **First 15 minutes on a board:
[`BRINGUP.md`](BRINGUP.md)** (what to check, expected fps/current, the serial perf log).

**Build, test, flash**
```bash
pio test -e native                  # 131 native tests (eyes + motion parity, SoulOS flows, AI + SOUL Cloud + SOUL Bridge);
                                    # needs OpenSSL's libcrypto on the PC (the device key; apt install libssl-dev)
pio run -e sim && .pio/build/sim/program /tmp/out all   # the simulator (stills: sim/shots/)
.pio/build/sim/program /tmp/out cloud http://127.0.0.1:8790 /tmp/key.hex   # a live local SOUL Cloud (see below)
SIM_NO_WS=1 .pio/build/sim/program /tmp/out cloud http://127.0.0.1:8790     # ... with the socket blocked: long-poll
.pio/build/sim/program /tmp/out lan 0                    # SOUL Bridge on the LAN: serves ws://127.0.0.1:<port>/bridge
.pio/build/sim/program /tmp/out keys                     # drive the IMU from the keyboard: a/d turn, w/s tip,
                                                         # q/e yaw, x spin, t tap, n nod, h shake, b/f/u/r poses
pio check -e lcd28                  # cppcheck on our code (clean)
pio run -e lcd28                    # build (-Wall -Wextra on our code: zero warnings)
pio run -e lcd28 -t upload          # flash over USB-C (native USB, CDC serial)
pio device monitor -b 115200        # '?' lists the serial commands; 'F' = perf overlay
```
If the upload does not start: hold **BOOT**, tap **RESET**, release BOOT, upload again.

Build size (2026-10-03, 1.4.0): `lcd28` flash ~2.14 MB (33 % of the 6.25 MB app slot), static RAM 84 KB (26 %);
the Glass buffers take ~2 MB of PSRAM at boot (`Glass.h`).
PSRAM holds our persistent canvas and the panel's two frame buffers (3 × 460,800 B ≈ 1.4 MB of 8 MB).

**How it runs** (`src/main.cpp`)

| Core | Task | What |
|---|---|---|
| 1 | the loop | touch, IMU, BLE (Hardware Buddy), Brain, SoulOS, the frame |
| 0 | `soul-net` | Wi-Fi, setup portal, NTP, AI turns over HTTPS (your Claude / OpenAI key; the survival path when SOUL Cloud is unreachable) |
| 0 | `soul-cloud` | the SOUL Cloud WebSocket (docs/07 §6): pairing, pushes, turns, item/inbox sync; long-poll when the socket will not open; the deep-sleep wake-polls |
| 0 | `httpd` | only with the brain "My Claude on my computer": the SOUL Bridge server `ws://soul-xxxx.local:8765/bridge` (`src/bridge_lan.cpp`, docs/08 §4) |
| 0 | LCD ISR | refills the two 10-line SRAM bounce buffers from the PSRAM frame buffer |

The render loop never blocks on the network: it posts questions and polls answers. A frame redraws
only what changed (`FrameComposer`: UI dirty rect ∪ last eyes rect into a persistent PSRAM canvas, then
the eyes, then the rim rings at 12 Hz), copies the changed rectangle into the back frame buffer and
swaps at the next frame boundary (`displayPresent`). No heap allocation per frame. The loop asks
30 fps when something moves, 24 calm, 15/10 dozing, 4 with the screen off, and lowers its own cap
if frames get expensive.

**Wi-Fi and the AI.** Settings → Wi-Fi → *Set up from a phone*: SOUL scans, opens the WPA2 access point
`SOUL-XXXX` (random 8-digit password) and shows a **join QR**; the captive page sets the Wi-Fi, the
brain, the time zone and, under *Advanced*, an Anthropic or OpenAI key (NVS `soulkey`, never printed,
only shown masked). Brains (Settings → AI): **SOUL Cloud** (pair with the `XXXX-XXXX` code + QR; the account
page decides who answers: your own Anthropic / OpenAI key kept encrypted in the cloud, or the offline rules —
SOUL includes no AI paid by us, so the cloud's built-in brain is off unless `SOUL_BUILTIN_AI=1`), **your Claude
key** on SOUL (`claude-opus-5-5`, effort low, structured JSON output), **your OpenAI key** on SOUL (`gpt-6-luna`),
**My Claude on my computer** (SOUL Bridge, docs/08: the owner's own Claude Code on a computer that is on; SOUL shows
`soul-bridge pair XXXX-XXXX --cloud …` when paired with an account, else a 6-digit code for the bridge on the same
Wi-Fi; the eyes wait while the question travels and think once Claude Code took it; computer off → the offline rules
and "Your computer is offline: open Start SOUL"), **No AI** (on-device RO/EN rules). Your own Claude / ChatGPT app
reaches SOUL through the connector whatever the brain. Models can be changed from the portal or by SOUL Cloud's `config` message. Every brain falls back to the
on-device rules when the network or the key fails, and the eyes say what happened.

**SOUL Cloud**, protocol v1 **rev. 2**, the one `../ai/suflet_ai/{devices,gateway}.py` implement
(`../docs/07-CONNECT-AI.md` §6). Transport-free and tested on the PC: `lib/Suflet/src/CloudLink.*` (frames,
auth bodies, the §6.2 error table, close codes), `CloudSession.*` (the state machine: dedupe, acks, outq,
pairing, turns, time zone, frame budget) and `CloudDriver` (auth → socket → reconnect over a transport),
`DeviceKey.*` (P-256: mbedTLS on the device, OpenSSL on the PC). `src/cloud.*` is only the ESP transport
(esp_transport TLS + WebSocket, NVS); `sim/sim_cloud.*` is the same for the simulator (POSIX sockets).
- **Identity**: device id `soul-<12 hex>`; an ECDSA P-256 key made on the device once Wi-Fi is up, kept in its
  own NVS partition `soulid` (`priv`, `pub`, `rst`; *Start over* never erases it). Serial `K` prints the public
  key (`SOULKEY PUB …`), never the private one.
- **Sign-in**: `POST /v1/device/challenge` → sign `soul-auth-v1\n{host}\n{device_id}\n{nonce}` (raw r‖s) →
  `POST /v1/device/auth` (`reset: true` after a factory reset) → a 24 h device token **in RAM only**, renewed
  5 min before it ends. 400 → a new challenge once; 401 → back off 1 → 60 min ("Can't sign in" after 3);
  403 `not_enrolled` / `key_revoked` → the matching screen, retry every 6 h; 429 → `Retry-After`.
- **Socket**: `wss://…/v1/device/ws`, Bearer + `soul.v1`, `hello` (proto, caps, `after`, `brain_local`, `power`,
  `tz_posix` as a hint) → `welcome` (the cloud's `posix_tz` always wins; `server_time` sets the clock if NTP has
  not). Ping 25 s, silent 70 s, backoff 1–60 s + jitter reset after a minute up; close 4000 (1–5 s), 4401/4403
  (sign in again), 4409 (not for 60 s), 4426 ("Update SOUL", daily), 4429 (`retry_ms`). Frames ≤ 10 KB of raw
  UTF-8, at most 10 burst / 2 per s (acks apart).
- **Pairing**: the 8-character code shown `XXXX-XXXX` + QR of `https://{BASE}/pair#c=…&d=…`; `pair.confirm`
  shows "Pair with Ana?" and only a touch answers it (no touch in `expires_in` = no).
- **Pushes** (`note.create`, `reminder.create` with an absolute date, `alarm.set` with any weekday set,
  `timer.start`, `focus.start`, `answer.show`, `item.delete`): replays acked again and never re-applied; unknown
  actions `unsupported`, bad ones `invalid`; while *Settings › Claude & ChatGPT on me* is paused, connector and
  shortcut pushes are acked `paused`. A source badge (Claude / ChatGPT / App + who), night alarms with
  `needs_accept` wait for *Accept* (then `item.state accepted|rejected`), private cards show the title until a
  tap, reminders from the cloud report `item.state rang`.
- **Up**: `item.add` / `inbox.add` / `item.state` in an offline queue (≤ 50, NVS `soulsync/outq` ≤ 8 KB), sent in
  order only while paired, removed on `added` (or on `invalid` / `too_big` naming their `cid`), kept on
  `rate_limited`. Turns: `ask` with `conv` (10 min) and the unsynced items, 25 s then `abort`; a cloud `timeout`
  never makes the on-device rules act twice. The last seq is saved batched (10 pushes / 60 s / before sleep),
  `sleep {wake_at}` before deep sleep.
- **Proof**: 13 native tests in `test/test_suflet/test_cloud.cpp` incl. the cloud's auth test vector and a replay
  of 32 frames + 4 HTTP answers recorded from the running cloud (`test/test_suflet/cloud_frames.h`, made by
  `../ai/tools/record_frames.py`); and the simulator in cloud mode runs the same code over real sockets against a
  local cloud (`../ai/tools/e2e_sim.py`, step 3 of `../ai/tools/e2e_demo.sh`): pairs via `/pair` + a tap on the
  simulated glass, receives connector pushes, talks through the relay, sends items and inbox questions.
- **Long-poll** (§6.4): after 3 socket refusals that are not 401/403/426, `CloudDriver` carries the same frames over
  `GET /v1/device/poll` + `POST /v1/device/send` (hello in the first send, `wait=8` idle), and tries the socket
  again every 10 minutes. **Wake-polls** (§6.11): a paired SOUL sleeps at most 15 minutes; on that timer wake the
  screen stays off, it signs in, polls once (all pages, `wait=0`, no hello), SoulOS applies the pushes, one send
  carries the acks, the queue and the next `sleep`, and it sleeps again within 12 s (unless an alarm is due within
  15 minutes or someone touched it). **Factory**: serial `SOULKEY GEN` / `SOULKEY PUB` answer
  `SOULKEY PUB soul-<id> <pub>` for `../ai/tools/factory_enrol.py`.
- **SOUL Bridge** (docs/08 §4): through the cloud (`bridge.code` / `bridge.state` / `ask.state`, brain `bridge`,
  125 s turns) and on the LAN (`lib/Suflet/src/BridgeLink.*`: 6-digit code, token hashes in NVS `soulbridge`,
  hello, turns; `src/bridge_lan.cpp`: `esp_http_server` WebSocket + mDNS `soul-xxxx` / `_soul._tcp`).
  Proof: `test/test_suflet/test_bridge.cpp` (LAN server, cloud frames and session, long-poll and wake-poll against a
  scripted cloud) and `../ai/tools/e2e_bridge.py` (simulator → cloud → the real `soul-bridge` → a mocked Claude
  Code → alarm on SOUL; and on the LAN).
- **Not yet**: flash + NVS encryption. Never run on the board against a deployed cloud; the LAN server, mDNS and
  the wake-polls are compiled, not run on hardware.
Without a cloud address none of this runs and the direct-key and No-AI brains work alone.

**What the board has** (Waveshare wiki, vendor ESP-IDF demo and schematic, read 2026-09-25)

| Part | Details | Used by the firmware |
|---|---|---|
| MCU | ESP32-S3R8: 8 MB octal PSRAM, 16 MB flash | same `common_esp32` settings as S |
| Display | ST7701, 16-bit RGB565 parallel (PCLK 41, DE 40, VSYNC 39, HSYNC 38, B 5/45/48/47/21, G 14/13/12/11/10/9, R 46/3/8/18/17), 18 MHz pixel clock | ESP-IDF `esp_lcd` RGB panel: 2 PSRAM frame buffers, 10-line SRAM bounce buffers, swap at the frame boundary |
| Display init | 3-wire 9-bit SPI: MOSI 1, SCK 2, **CS = expander EXIO3, RESET = EXIO1** | the vendor's "2.8inch" init table, copied 1:1 into `src/board_lcd28.cpp` |
| Backlight | GPIO6, PWM, active high (vendor: LEDC 5 kHz, 13 bit) | see "Backlight" below |
| Touch | GT911 on I2C (SDA 15, SCL 7), INT 16, RESET = EXIO2, address 0x5D | raw register reads, single point |
| IO expander | TCA9554PWR at 0x20 | LCD/touch reset, LCD CS, TF CS, buzzer |
| IMU | QMI8658 at 0x6B | SensorLib, as on S |
| RTC | PCF85063A at 0x51; INT on EXIO7 | SensorLib, as on S (INT unused) |
| Battery | MX1.25 Li-ion, ETA6098 charger, ADC on GPIO4 through 200k/100k (×3) | voltage → % |
| Buttons | BOOT (GPIO0), RESET, a battery power switch (hardware only) | BOOT = back / silence alarm |
| Sound | an on/off **buzzer** on EXIO8 | alarm beeps |
| Not on the board | PMU, codec, microphones, speaker | optional I2S parts below |

The TF slot (CLK 2, CMD 1, D0 42, D3 = EXIO4) is not used; its CS is held high.

**Backlight (IPS has no true black).** A black pixel still lets the backlight through, so the disc glows grey in a
dark room. The firmware draws pure black everywhere it can and follows the face with the backlight:
full while awake (70 % early/late), **35 % at night** (22:00–07:00), at least 60 % while typing or setting an
alarm, a 6–18 % glow while the eyes sleep, and **fully off (PWM 0, panel sleep-in, slower pixel clock)**
when the Brain turns the display off. It fades up in ~0.25 s and down in ~0.8 s on a gamma-2.2 curve.
At night, docked or off for 10 minutes, it deep-sleeps until the next alarm, 07:00, BOOT or a touch.
A touch wakes the face and the light comes back.

**Alarm sound.** When an alarm rings the Brain startles awake and an `AlarmTone` pattern plays
(4 × 100 ms beeps, 0.6 s pause, repeating; it stops by itself after 60 s). On the 2.8C it drives the
buzzer on EXIO8; with the optional amplifier it plays a 2 kHz tone on the speaker instead. A touch or
BOOT silences it. (The AMOLED-1.75 has a speaker behind an ES8311 codec that is not driven yet.)

### SOUL M wiring: optional microphone and speaker
The 2.8C has no microphone and no speaker, and almost no free GPIO: everything is taken by the RGB
bus, the TF slot and PSRAM. What is left: **GPIO43 / GPIO44** (UART0 TX/RX on the 12-pin header;
serial logging uses native USB, so they are free after boot), **GPIO42** (TF-slot D0: leave the slot
empty), GPIO0 (BOOT, a strapping pin) and GPIO19/20 (USB). One I2S port on 43/44/42:

| Signal | ESP32-S3 | INMP441 mic | MAX98357A amp |
|---|---|---|---|
| Bit clock | GPIO43 (header TXD) | SCK | BCLK |
| Word select | GPIO44 (header RXD) | WS | LRC |
| Data | GPIO42 (TF D0, test pad or slot pin) | SD | DIN |
| Power | 3V3 / GND | VDD, GND, **L/R → GND** | VIN (3V3 or VBAT), GND, SD_MODE open (L+R/2) |

Build flags (add to `build_flags` of `[env:lcd28]`):
- `-DSUFLET_MIC_INMP441=1`: the mic. Its loudness goes to the Brain as `audioLevel` (the listening ring).
- `-DSUFLET_SPK_MAX98357=1`: the amp. Alarms then sound on the speaker instead of the buzzer.
- Both at once share BCLK/WS but need a fourth data pin: build with `-DAUDIO_SPK_DOUT=<gpio>`
  (the build stops with an error otherwise). The only candidate without losing USB is GPIO0.
  **TODO:** check that the amp's DIN does not pull GPIO0 low at reset (that would boot into download mode).

The pins can be overridden with `-DAUDIO_MIC_DIN=…` / `-DAUDIO_SPK_DOUT=…`; the clocks are
`AUDIO_I2S_BCLK` / `AUDIO_I2S_WS` in `src/board.h`. I2S runs at 16 kHz, 32-bit slots, mono (left).
The ESP32 boot ROM prints on GPIO43 for a moment at power-on; the mic/amp just see noise then.

### Resolution-aware UI
Every screen is laid out once, in "design pixels" on the 466 px disc, and scaled by a single
`DisplayGeometry` (`lib/Suflet/src/Geometry.h`: `w`, `h`, `activeMm`, `k() = w/466`, `s()`, `rect()`,
`mm()`). `main.cpp` builds it from `DISPLAY_GEOMETRY` in `board.h` and hands it to the `Shell`, which passes it
to the `Keyboard` and `TimePicker`. Key rectangles, hit-testing rows, the variant tray, the suggestion bar, the
Rim-Dial ring, its hit areas and the ✓ all scale; fonts keep their pixel sizes (3 % smaller relative to the disc
at 480 px, physically 1.5× larger). The face was already relative to the screen size. At 466 px the output is
pixel-identical to before (the committed `media/soulos_fw_*` stills were re-rendered and compared).
Native tests cover the 480 px geometry: keyboard hit-testing (every key, the rim, row borders, a pixel scan with
no holes, key size in mm), typing and the variant tray, rendering inside the bounds and inside the round glass,
the Rim-Dial and the alarm tone pattern (61 tests).

### Not verified on the hardware yet

Everything compiles warning-free and the logic is tested on the PC; nothing has run on a physical 2.8C.
The checklist is [`BRINGUP.md`](BRINGUP.md). Open risks:
- **Panel timing / bounce buffers** (vendor values; drift → `LCD_BOUNCE_LINES`, `LCD_PCLK_HZ`).
- **NVS writes stall the RGB DMA** (flash and PSRAM share the cache). The firmware restarts the panel at
  the next VSYNC after each write and batches writes; the real fix is `CONFIG_SPIRAM_XIP_FROM_PSRAM` +
  `CONFIG_LCD_RGB_ISR_IRAM_SAFE` (a pioarduino `custom_sdkconfig` rebuild of the framework, not done).
- **Internal RAM with TLS + BLE**: mbedTLS allocates internally in this framework build; a SOUL Cloud
  socket plus a direct HTTPS turn plus BLE is the peak. Watch `min` heap in the perf log.
- **GT911 INT polarity** for touch-wake from deep sleep (armed only if the line idles high).
- **SOUL Cloud on the board**: the protocol code is tested on the PC (recorded frames) and end to end in the
  simulator against a live local cloud, but the ESP transport (`src/cloud.cpp`: esp_transport TLS + WebSocket,
  mbedTLS P-256) is compile-checked only; the `esp_transport_ws` read semantics (opcode after a timeout) are from
  the IDF sources as remembered. First board test: serial `K`, then watch `[cloud]` lines while pairing.
- **Keys and the device key sit in plain NVS** until production turns on flash + NVS encryption.
- Orientation, IMU axes, charge current (R7 = 82 kΩ), buzzer polarity: see BRINGUP.md.
