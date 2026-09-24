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

## Libraries (fetched by PlatformIO, not vendored)
GFX Library for Arduino (BSD), SensorLib (MIT), ArduinoJson (MIT), Unity (MIT).
