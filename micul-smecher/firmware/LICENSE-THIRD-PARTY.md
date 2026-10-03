# Third-party code

## anthropics/claude-desktop-buddy — `src/ble_link.cpp` is adapted from `src/ble_bridge.cpp`
Wire protocol: https://github.com/anthropics/claude-desktop-buddy/blob/main/REFERENCE.md

MIT License — Copyright 2026 Anthropic, PBC.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## 78/xiaozhi-esp32 (MIT) — register values only
`src/main.cpp` `pmuInit()` uses the AXP2101 register values and `src/board.h` the pin map of the
Waveshare AMOLED-1.75 board support in https://github.com/78/xiaozhi-esp32 (MIT License,
Copyright (c) 2025 Shenzhen Xinzhi Future Technology Co., Ltd.).

## Inigo Quilez — 2D SDF functions (MIT)
`sdHeart` and `sdStar5` in `lib/Suflet/src/Canvas.cpp` follow https://iquilezles.org/articles/distfunctions2d/ (MIT).

## Nunito — SIL Open Font License 1.1
`lib/Suflet/src/FontData.h` holds glyph bitmaps rasterised by `tools/gen_font.py` from Nunito
SemiBold/Bold (`tools/fonts/*.ttf`, from Google Fonts). Copyright 2014 The Nunito Project Authors
(https://github.com/googlefonts/nunito). Full licence: `tools/fonts/OFL.txt`.

## Keyboard word lists — not third-party
`tools/words/*.txt` (→ `lib/Suflet/src/WordListData.h`) were written by hand for this project and
are not derived from FrequencyWords (CC-BY-SA) or any other corpus; see `tools/words/README.md`.

## Libraries (fetched by PlatformIO, not vendored)
GFX Library for Arduino (BSD), SensorLib (MIT), ArduinoJson (MIT), Unity (MIT).

## ricmoo/QRCode (MIT) — `lib/Suflet/src/QrEncode.{h,c}`
Vendored with three small changes: the header name (ESP-IDF ships its own `qrcode.h`), compiled as C++ (no C `bool` typedef), `#pragma mark` lines turned into comments and an always-false unsigned `< 0` test removed (warning-free with -Wall -Wextra).
https://github.com/ricmoo/QRCode — MIT License, Copyright (c) 2017 Richard Moore (full text at the top of the files).
Used for the pairing QR and the setup Wi-Fi QR on the round screen.

## Espressif ESP-SR — ESPRESSIF MIT License (only in the `lcd28_voice` build)
The offline voice commands (`src/voice_sr.cpp`, docs/10-SOUL-MEMORY.md §7) link esp-sr 2.5.3 (AFE, WakeNet9,
MultiNet7 English, flite g2p) as shipped precompiled in Arduino-ESP32 3.3 (`framework-arduinoespressif32-libs`), and
use its `srmodels.bin` in the `model` partition. Copyright (c) Espressif Systems (Shanghai) Co. Ltd. The ESPRESSIF MIT
License grants MIT-style rights **for use on Espressif Systems products only**; the notice must be kept in copies
(https://github.com/espressif/esp-sr/blob/master/LICENSE). The default `lcd28` image does not contain it.
