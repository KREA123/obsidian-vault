// board_amoled.h: the QSPI AMOLED panel, tear-free strips, the TE line and a power switch that never blocks.
#include "board_amoled.h"

#if !LCD_IS_RGB
#include <Arduino.h>
#include <Arduino_GFX_Library.h>
#include <driver/gpio.h>
#include <esp_heap_caps.h>
#include <esp_timer.h>

#include "TearSync.h"

#ifndef LCD_TE
#define LCD_TE -1
#endif

namespace amoled {

namespace {
// CO5300 commands (Arduino_CO5300.h names; the MIPI DCS numbers)
constexpr uint8_t kSlpIn = 0x10, kSlpOut = 0x11, kDispOff = 0x28, kDispOn = 0x29, kTeOn = 0x35, kBright = 0x51;
// the datasheet-style waits of Arduino_CO5300 (CO5300_SLPIN_DELAY / CO5300_SLPOUT_DELAY), kept without delay()
constexpr uint32_t kSlpOutMs = 120, kSlpInMs = 120;
// dark this long (face down, the night, Mode Off) before the panel goes to sleep-in [estimare: the panel's own
// draw dark vs asleep is to measure, BRINGUP §S]; a pick-up within it is only a brightness change
constexpr uint32_t kSleepAfterMs = 60 * 1000;
constexpr int kBouncePx = 8192;  // 16 KB of internal RAM: 17 rows of 466 px

Arduino_DataBus* bus = nullptr;
Arduino_OLED* panel = nullptr;
uint16_t* canvasBuf = nullptr;
uint16_t* bounce = nullptr;
DisplayStats st;
suflet::ScanModel model;
uint8_t sentLevel = 255, wantLevel = 255;
uint32_t darkSinceMs = 0, slpInAtMs = 0, slpOutAtMs = 0, wakeStartMs = 0;
bool pendingFull = false;

// TE: the ISR keeps integer times only (no FPU in an interrupt); the model is updated in the loop
volatile int64_t teRiseUs = 0, tePrevRiseUs = 0, teFallUs = 0;
volatile uint32_t teEdges = 0;
void ARDUINO_ISR_ATTR teIsr() {
  const int64_t now = esp_timer_get_time();
  if (gpio_get_level((gpio_num_t)LCD_TE)) {
    tePrevRiseUs = teRiseUs;
    teRiseUs = now;
    teEdges = teEdges + 1;
  } else {
    teFallUs = now;
  }
}

void sendBrightness(uint8_t v) {
  if (v == sentLevel) return;
  sentLevel = v;
  panel->setBrightness(v);
}

// the TE model from the last edges: period, V-blank (TE high), and whether the line is alive at all
void updateModel() {
#if LCD_TE >= 0
  const int64_t now = esp_timer_get_time(), rise = teRiseUs, prev = tePrevRiseUs, fall = teFallUs;
  st.edges = teEdges;
  st.teSeen = rise && now - rise < 100000;
  if (!st.teSeen) return;
  const int64_t p = rise - prev;
  if (prev && p > 5000 && p < 50000) {  // 20-200 Hz: anything else is a missed or doubled edge
    st.periodUs = st.periodUs > 0 ? st.periodUs * 0.9f + (float)p * 0.1f : (float)p;
    model.periodUs = st.periodUs;
  }
  const int64_t v = fall - prev;  // the last complete high pulse: the previous rise to the fall after it
  if (prev && fall > prev && v > 0 && v < 5000) {
    st.vblankUs = st.vblankUs > 0 ? st.vblankUs * 0.9f + (float)v * 0.1f : (float)v;
    model.offsetUs = st.vblankUs;
    model.activeUs = model.periodUs - model.offsetUs;
  }
#endif
}

void waitUs(double us) {
  const int64_t until = esp_timer_get_time() + (int64_t)us;
  if (us > 2500) vTaskDelay(pdMS_TO_TICKS((uint32_t)((us - 1500) / 1000)));  // the other tasks run meanwhile
  while (esp_timer_get_time() < until) {
  }
}

// rows [y0, y0 + h) of columns [x0, x0 + w) from the canvas, in even strips through the bounce buffer
void pushRows(int x0, int y0, int w, int h) {
  int per = kBouncePx / w;
  per &= ~1;  // CO5300: even rows
  if (per < 2) per = 2;
  for (int y = y0; y < y0 + h; y += per) {
    const int n = y0 + h - y < per ? y0 + h - y : per;
    for (int r = 0; r < n; ++r) memcpy(bounce + r * w, canvasBuf + (size_t)(y + r) * LCD_W + x0, (size_t)w * 2);
    panel->draw16bitRGBBitmap(x0, y, bounce, w, n);
  }
}

void pushRect(const suflet::Rect& r) {
  const int w = r.w();
  int y = r.y0;
  while (y < r.y1) {
    updateModel();
    if (!st.sync || !st.teSeen) {
      pushRows(r.x0, y, w, r.y1 - y);
      return;
    }
    const double t = (double)(esp_timer_get_time() - teRiseUs);
    const suflet::TearBand b = suflet::tearNextBand(model, w, y, r.y1, t);
    if (b.waitUs > 0) {
      waitUs(b.waitUs);
      ++st.waits;
      st.waitMs += (float)(b.waitUs / 1000.0);
    }
    const int64_t s = esp_timer_get_time();
    pushRows(r.x0, b.y0, w, b.y1 - b.y0);
    const int64_t e = esp_timer_get_time();
    const int px = w * (b.y1 - b.y0);
    if (px >= 4096 && e - s > model.setupUs) {  // the write rate the next bands are planned with
      const double rate = px / ((double)(e - s) - model.setupUs);
      model.pxPerUs = model.pxPerUs * 0.8 + rate * 0.2;
      st.pxPerUs = (float)model.pxPerUs;
    }
    ++st.bands;
    y = b.y1;
  }
}

void pushAll() {
  suflet::Rect all;
  all.x0 = all.y0 = 0;
  all.x1 = LCD_W;
  all.y1 = LCD_H;
  pushRect(all);
}
}  // namespace

bool displayInit() {
  bus = new Arduino_ESP32QSPI(LCD_CS, LCD_SCLK, LCD_D0, LCD_D1, LCD_D2, LCD_D3);
#if defined(SUFLET_PANEL_SH8601)
  panel = new Arduino_SH8601(bus, LCD_RST, 0, LCD_W, LCD_H);
#else
  panel = new Arduino_CO5300(bus, LCD_RST, 0, LCD_W, LCD_H, LCD_COL_OFFSET, 0, LCD_COL_OFFSET, 0);
#endif
  const bool ok = panel->begin(40000000);
  // the tearing-effect line, V-blank only (mode 0); Arduino_GFX 1.6.8 leaves it commented out
  bus->beginWrite();
  bus->writeC8D8(kTeOn, 0x00);
  bus->endWrite();
#if LCD_TE >= 0
  pinMode(LCD_TE, INPUT);
  attachInterrupt(LCD_TE, teIsr, CHANGE);
#endif
  panel->fillScreen(0);
  sentLevel = 0;  // (forces the first level out)
  sendBrightness(255);
  canvasBuf = (uint16_t*)heap_caps_calloc((size_t)LCD_W * LCD_H, 2, MALLOC_CAP_SPIRAM);
  bounce = (uint16_t*)heap_caps_malloc(kBouncePx * 2, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  st.pxPerUs = (float)model.pxPerUs;
  return ok && canvasBuf && bounce;
}

uint16_t* displayCanvas() { return canvasBuf; }

void displayPresent(const suflet::RectList& list) {
  const int64_t t0 = esp_timer_get_time();
  uint32_t px = 0;
  if (st.state >= 2) {  // asleep or waking: the canvas keeps the frame, it goes out whole with DISPON
    pendingFull = true;
    return;
  }
  for (int i = 0; i < list.n; ++i) {  // each changed rectangle on its own (the panel keeps the rest)
    suflet::Rect r = list.r[i];
    r.x0 &= ~1;  // CO5300 wants even start/size
    r.y0 &= ~1;
    r.x1 = (r.x1 + 1) & ~1;
    r.y1 = (r.y1 + 1) & ~1;
    if (r.x1 > LCD_W) r.x1 = LCD_W;
    if (r.y1 > LCD_H) r.y1 = LCD_H;
    if (r.empty()) continue;
    pushRect(r);
    px += (uint32_t)(r.w() * r.h());
  }
  st.pushedPx = px;
  st.pushMs = (esp_timer_get_time() - t0) / 1000.0f;
}

void backlight(float v) {
  wantLevel = (uint8_t)(v <= 0 ? 0 : v >= 1 ? 255 : v * 255);
  if (st.state == 0) sendBrightness(wantLevel);
}

void displayPower(bool on) {
  const uint32_t now = millis();
  if (on) {
    if (st.state == 1) {
      st.state = 0;  // it was only dark: the level eases back up (main.cpp), the frame is already there
      st.lastWakeMs = 0;
    } else if (st.state == 2) {
      st.state = 3;  // SLPOUT goes out from displayTick, DISPON 120 ms after it
      slpOutAtMs = 0;
      wakeStartMs = now;
    }
  } else if (st.state == 0) {
    st.state = 1;
    darkSinceMs = now;
    sendBrightness(0);
  }
}

void displayTick(uint32_t now) {
  if (st.state == 1 && now - darkSinceMs >= kSleepAfterMs) {  // dark for a while: sleep-in (the panel's lowest)
    bus->sendCommand(kDispOff);
    bus->sendCommand(kSlpIn);
    slpInAtMs = now;
    st.state = 2;
  } else if (st.state == 3) {
    if (!slpOutAtMs) {
      if (now - slpInAtMs >= kSlpInMs) {  // a sleep-in needs 120 ms before the next sleep-out
        bus->sendCommand(kSlpOut);
        slpOutAtMs = now | 1;
      }
    } else if (now - slpOutAtMs >= kSlpOutMs) {
      if (pendingFull) pushAll();  // the frame first, then the light: never a stale picture
      pendingFull = false;
      bus->sendCommand(kDispOn);
      st.state = 0;
      sentLevel = 0;
      sendBrightness(wantLevel);
      st.lastWakeMs = millis() - wakeStartMs;
    }
  }
}

void displaySleepNow() {
  sendBrightness(0);
  if (st.state == 2) return;  // already asleep
  bus->sendCommand(kDispOff);
  bus->sendCommand(kSlpIn);
  delay(kSlpInMs);  // deep sleep follows: nothing else runs
  st.state = 2;
}

void setTearSync(bool on) { st.sync = on; }

DisplayStats& displayStats() { return st; }

void displayReport() {
  updateModel();
  Serial.printf("[te] %s, %lu edges, period %.0f us (%.1f Hz), V-blank %.0f us; write %.2f px/us (%.1f MB/s); tear sync %s\n",
                st.teSeen ? "seen" : (LCD_TE >= 0 ? "NOT SEEN (check LCD_TE in board.h)" : "no TE pin"), (unsigned long)st.edges, st.periodUs,
                st.periodUs > 0 ? 1e6f / st.periodUs : 0.0f, st.vblankUs, st.pxPerUs, st.pxPerUs * 2.0f, st.sync ? "on" : "off");
  Serial.printf("[te] since the last E: %lu bands, %lu waited, %.1f ms waiting; last push %.1f ms (%lu px); panel %s, last wake %lu ms\n",
                (unsigned long)st.bands, (unsigned long)st.waits, st.waitMs, st.pushMs, (unsigned long)st.pushedPx,
                st.state == 0 ? "on" : st.state == 1 ? "dark" : st.state == 2 ? "sleep-in" : "waking", (unsigned long)st.lastWakeMs);
  st.bands = st.waits = 0;
  st.waitMs = 0;
}

}  // namespace amoled

#endif
