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
  scuturare, cădere, ciocănit, orientare), `ClaudeLink` (protocolul Hardware Buddy al Claude Desktop).
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
- Axele IMU → `IMU_MAP` în `board.h` (comanda serială `i`: fața în sus ≈ (0,0,+1)).

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

**Build and flash**
```bash
pio run -e lcd28                    # build
pio run -e lcd28 -t upload          # flash over the USB-C port (native USB, CDC serial)
pio device monitor -b 115200        # "[board] LCD-2.8C 480x480, disc 70.1 mm, key pitch 6.6 mm"
.pio/build/sim/program /tmp/out keyboard 0xC0FFEE 480   # the simulator at 480 px
```
If the upload does not start: hold **BOOT**, tap **RESET**, release BOOT, upload again.

Build size (2026-09-25): `lcd28` flash 913,806 B (13.9 % of the 6.25 MB app slot), static RAM 38,668 B;
with both optional I2S parts 944,218 B / 38,812 B. At run time PSRAM holds three 460,800 B buffers
(our Canvas, the push buffer, the panel's scanned framebuffer): ~1.4 MB of 8 MB.

**What the board has** (Waveshare wiki, vendor ESP-IDF demo and schematic, read 2026-09-25)

| Part | Details | Used by the firmware |
|---|---|---|
| MCU | ESP32-S3R8: 8 MB octal PSRAM, 16 MB flash | same `common_esp32` settings as S |
| Display | ST7701, 16-bit RGB565 parallel (PCLK 41, DE 40, VSYNC 39, HSYNC 38, B 5/45/48/47/21, G 14/13/12/11/10/9, R 46/3/8/18/17), 18 MHz pixel clock | Arduino_GFX `Arduino_ESP32RGBPanel` + `Arduino_RGB_Display`, 10-line bounce buffer |
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
full while awake, **35 % at night** (22:00–07:00), at least 60 % while typing or setting an alarm,
and **fully off (PWM 0) as soon as the eyes close** (asleep) or the Brain turns the display off.
It fades up in ~0.3 s and down in ~0.8 s; the PWM curve is squared so the low end has fine steps.
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

### Not verified on the hardware yet (TODO)
Written from the vendor demo and schematic, compiled, not yet run on a physical 2.8C:
- **Active diameter**: 70.13 mm is from the bare 2.8" 480×480 ST7701 panel drawing (Twoyas); Waveshare does not
  state it. It only affects the mm numbers, not the layout.
- **Orientation**: which edge is "up" relative to the USB port; fix with `-DSUFLET_ROTATION=90|180|270`
  and, for touch, `TOUCH_MIRROR_X/Y` (the vendor uses no swap/mirror).
- **IMU axes** (`IMU_MAP`) and the QMI8658 INT pins (not used; the firmware polls).
- **Charge current**: the ETA6098 is set by R7 = 82 kΩ on ISET; check the datasheet against your cell before
  leaving it charging unattended (the lesson from the 1.43). The battery % reads the cell through the charger,
  so it reads high while charging; there is no USB-present signal on this board.
- **Buzzer**: EXIO8 high = sound (vendor `Buzzer_On`), so it is treated as an active buzzer with its own pitch.
- **Scan stability** with BLE busy: the 10-line bounce buffer is the vendor's option for this; if the picture
  drifts, raise `LCD_BOUNCE_PX` or lower `LCD_PCLK_HZ`.
- BLE pairing with Claude Desktop is the same code as on S.
