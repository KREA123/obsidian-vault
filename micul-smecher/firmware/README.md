# Firmware „Suflet” v0 — sufletul companionului

Ochii vii, dispoziția, cele 24 de reacții, personalitatea născută din cip și legătura
„works with Claude”. Rulează pe plăcile Waveshare cu AMOLED rotund 466×466.

| Placă | Mediu PlatformIO | Ce are |
|---|---|---|
| ESP32-S3-Touch-AMOLED-1.43 | `amoled143` | ecran, touch FT3168, IMU, RTC — fără sunet |
| ESP32-S3-Touch-AMOLED-1.75 | `amoled175` | + 2 microfoane, difuzor, PMU AXP2101, buton de pornire |

```bash
pio run -e amoled143 -t upload      # sau amoled175
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
