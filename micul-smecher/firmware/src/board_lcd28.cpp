// Waveshare ESP32-S3-Touch-LCD-2.8C board support. Pins, the ST7701 init
// sequence and the panel timings come from the vendor's ESP-IDF demo
// "ESP32-S3-Touch-LCD-2.8C-Test" (main/LCD_Driver/ST7701S.c,
// EXIO/TCA9554PWR.c, Touch_Driver/GT911.c, Buzzer/Buzzer.c), read 2026-09-25.
//
// Display pipeline (no tearing, low CPU):
//   SoulOS draws into its own persistent PSRAM canvas (only the parts that
//   change). displayPresent() copies the changed rectangles into the back
//   one of two esp_lcd frame buffers and asks the driver to switch to it; the
//   switch happens on a frame boundary. The buffer that was shown becomes the
//   back buffer only after the panel has finished two more frames from the
//   new one, so the CPU never writes into memory being scanned out. The RGB
//   peripheral reads the frame buffer through two small SRAM bounce buffers
//   (vendor option: keeps the picture stable when PSRAM/flash are busy).
#include "board_lcd28.h"

#if defined(SUFLET_BOARD_LCD28)
#include <Arduino.h>
#include <Wire.h>
#include <esp_cache.h>
#include <esp_heap_caps.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_rgb.h>
#include <esp_timer.h>
#include <freertos/semphr.h>
#include <string.h>

#ifndef LCD_BOUNCE_LINES
#define LCD_BOUNCE_LINES 10
#endif
#ifndef LCD_ISR_CORE
#define LCD_ISR_CORE 0  // the bounce-buffer ISR runs on core 0 (Wi-Fi/BLE); rendering owns core 1
#endif
#ifndef LCD_PCLK_SLEEP_HZ
#define LCD_PCLK_SLEEP_HZ 6000000
#endif

namespace lcd28 {

using suflet::Rect;

// ------------------------------------------------------------ TCA9554 ---

static uint8_t exioOut = 0;
static bool exioOk = false;

static bool exioReg(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(EXIO_ADDR);
  Wire.write(reg);
  Wire.write(v);
  return Wire.endTransmission() == 0;
}

bool exioInit() {
  // Outputs high first (both resets released, LCD and TF deselected,
  // buzzer off), then directions: everything an output except the RTC INT
  // line, which is open drain.
  exioOut = (1 << EXIO_LCD_RST) | (1 << EXIO_TP_RST) | (1 << EXIO_LCD_CS) | (1 << EXIO_SD_CS);
  exioOk = exioReg(0x01, exioOut) && exioReg(0x03, (uint8_t)(1 << EXIO_RTC_INT));
  return exioOk;
}

void exioWrite(uint8_t bit, bool high) {
  if (high) exioOut |= (uint8_t)(1 << bit);
  else exioOut &= (uint8_t)~(1 << bit);
  if (exioOk) exioReg(0x01, exioOut);
}

void buzzer(bool on) {
  if (!!(exioOut & (1 << EXIO_BUZZER)) != on) exioWrite(EXIO_BUZZER, on);
}

// --------------------------------------------------- ST7701 over 3-wire ---

struct InitCmd {
  uint8_t cmd, len;
  uint8_t data[16];
  uint16_t delayMs;
};

// Vendor ST7701S_screen_init(type 1, "2.8inch"), 1:1. 0x3A = 0x66 is what
// the vendor sends (the bus is still 16-bit RGB565; the panel's low bits are tied).
static const InitCmd kInit[] = {
    {0xFF, 5, {0x77, 0x01, 0x00, 0x00, 0x13}, 0},
    {0xEF, 1, {0x08}, 0},
    {0xFF, 5, {0x77, 0x01, 0x00, 0x00, 0x10}, 0},
    {0xC0, 2, {0x3B, 0x00}, 0},
    {0xC1, 2, {0x10, 0x0C}, 0},
    {0xC2, 2, {0x07, 0x0A}, 0},
    {0xC7, 1, {0x00}, 0},
    {0xCC, 1, {0x10}, 0},
    {0xCD, 1, {0x08}, 0},
    {0xB0, 16, {0x05, 0x12, 0x98, 0x0E, 0x0F, 0x07, 0x07, 0x09, 0x09, 0x23, 0x05, 0x52, 0x0F, 0x67, 0x2C, 0x11}, 0},
    {0xB1, 16, {0x0B, 0x11, 0x97, 0x0C, 0x12, 0x06, 0x06, 0x08, 0x08, 0x22, 0x03, 0x51, 0x11, 0x66, 0x2B, 0x0F}, 0},
    {0xFF, 5, {0x77, 0x01, 0x00, 0x00, 0x11}, 0},
    {0xB0, 1, {0x5D}, 0},
    {0xB1, 1, {0x3E}, 0},
    {0xB2, 1, {0x81}, 0},
    {0xB3, 1, {0x80}, 0},
    {0xB5, 1, {0x4E}, 0},
    {0xB7, 1, {0x85}, 0},
    {0xB8, 1, {0x20}, 0},
    {0xC1, 1, {0x78}, 0},
    {0xC2, 1, {0x78}, 0},
    {0xD0, 1, {0x88}, 0},
    {0xE0, 3, {0x00, 0x00, 0x02}, 0},
    {0xE1, 11, {0x06, 0x30, 0x08, 0x30, 0x05, 0x30, 0x07, 0x30, 0x00, 0x33, 0x33}, 0},
    {0xE2, 12, {0x11, 0x11, 0x33, 0x33, 0xF4, 0x00, 0x00, 0x00, 0xF4, 0x00, 0x00, 0x00}, 0},
    {0xE3, 4, {0x00, 0x00, 0x11, 0x11}, 0},
    {0xE4, 2, {0x44, 0x44}, 0},
    {0xE5, 16, {0x0D, 0xF5, 0x30, 0xF0, 0x0F, 0xF7, 0x30, 0xF0, 0x09, 0xF1, 0x30, 0xF0, 0x0B, 0xF3, 0x30, 0xF0}, 0},
    {0xE6, 4, {0x00, 0x00, 0x11, 0x11}, 0},
    {0xE7, 2, {0x44, 0x44}, 0},
    {0xE8, 16, {0x0C, 0xF4, 0x30, 0xF0, 0x0E, 0xF6, 0x30, 0xF0, 0x08, 0xF0, 0x30, 0xF0, 0x0A, 0xF2, 0x30, 0xF0}, 0},
    {0xE9, 2, {0x36, 0x01}, 0},
    {0xEB, 7, {0x00, 0x01, 0xE4, 0xE4, 0x44, 0x88, 0x40}, 0},
    {0xED, 16, {0xFF, 0x10, 0xAF, 0x76, 0x54, 0x2B, 0xCF, 0xFF, 0xFF, 0xFC, 0xB2, 0x45, 0x67, 0xFA, 0x01, 0xFF}, 0},
    {0xEF, 6, {0x08, 0x08, 0x08, 0x45, 0x3F, 0x54}, 0},
    {0xFF, 5, {0x77, 0x01, 0x00, 0x00, 0x00}, 0},
    {0x11, 0, {0}, 120},  // sleep out
    {0x3A, 1, {0x66}, 0},
    {0x36, 1, {0x00}, 0},
    {0x35, 1, {0x00}, 0},
    {0x29, 0, {0}, 0},  // display on
};

// 9-bit words: D/C bit (0 command, 1 data), then 8 bits MSB first, sampled
// on the rising edge of SCK (SPI mode 0). ~200 kHz with digitalWrite: the
// whole table takes a few ms.
static void spi9(bool data, uint8_t v) {
  digitalWrite(LCD_SPI_SCK, LOW);
  digitalWrite(LCD_SPI_MOSI, data ? HIGH : LOW);
  delayMicroseconds(1);
  digitalWrite(LCD_SPI_SCK, HIGH);
  delayMicroseconds(1);
  for (int i = 7; i >= 0; --i) {
    digitalWrite(LCD_SPI_SCK, LOW);
    digitalWrite(LCD_SPI_MOSI, (v >> i) & 1 ? HIGH : LOW);
    delayMicroseconds(1);
    digitalWrite(LCD_SPI_SCK, HIGH);
    delayMicroseconds(1);
  }
}

static void st7701Cmd(uint8_t cmd, const uint8_t* d, uint8_t n) {
  exioWrite(EXIO_LCD_CS, false);
  spi9(false, cmd);
  for (uint8_t i = 0; i < n; ++i) spi9(true, d[i]);
  exioWrite(EXIO_LCD_CS, true);
}

static void spiPins(bool on) {
  if (on) {
    pinMode(LCD_SPI_SCK, OUTPUT);
    pinMode(LCD_SPI_MOSI, OUTPUT);
    digitalWrite(LCD_SPI_SCK, LOW);
  } else {  // shared with the TF slot (CLK/CMD): leave them floating-safe
    pinMode(LCD_SPI_SCK, INPUT_PULLUP);
    pinMode(LCD_SPI_MOSI, INPUT_PULLUP);
  }
}

static void st7701Init() {
  // vendor ST7701S_reset(): EXIO1 low 10 ms, high, then 120 ms
  exioWrite(EXIO_LCD_RST, false);
  delay(10);
  exioWrite(EXIO_LCD_RST, true);
  delay(120);
  spiPins(true);
  st7701Cmd(0x01, nullptr, 0);  // software reset
  delay(120);
  for (const InitCmd& c : kInit) {
    st7701Cmd(c.cmd, c.data, c.len);
    if (c.delayMs) delay(c.delayMs);
  }
  spiPins(false);
}

// ---------------------------------------------------------- RGB panel ---

static esp_lcd_panel_handle_t panel = nullptr;
static uint16_t* fb[2] = {nullptr, nullptr};
static uint16_t* canvas = nullptr;
static int front = 0;                  // the buffer being shown
static volatile uint32_t frames = 0;   // frames the panel finished reading
static uint32_t switchedAt = 0;        // `frames` when we last switched
static SemaphoreHandle_t frameSem = nullptr;
static Rect lastChanged{0, 0, LCD_W, LCD_H};  // what the back buffer still misses
static DisplayStats stats;
static bool panelOn = true;

static bool IRAM_ATTR onFrameDone(esp_lcd_panel_handle_t, const esp_lcd_rgb_panel_event_data_t*, void*) {
  frames = frames + 1;
  BaseType_t woke = pdFALSE;
  xSemaphoreGiveFromISR(frameSem, &woke);
  return woke == pdTRUE;
}

static bool createPanel() {
  esp_lcd_rgb_panel_config_t cfg = {};
  cfg.clk_src = LCD_CLK_SRC_DEFAULT;
  cfg.timings.pclk_hz = LCD_PCLK_HZ;
  cfg.timings.h_res = LCD_W;
  cfg.timings.v_res = LCD_H;
  cfg.timings.hsync_pulse_width = LCD_HSYNC_PULSE;
  cfg.timings.hsync_back_porch = LCD_HSYNC_BACK;
  cfg.timings.hsync_front_porch = LCD_HSYNC_FRONT;
  cfg.timings.vsync_pulse_width = LCD_VSYNC_PULSE;
  cfg.timings.vsync_back_porch = LCD_VSYNC_BACK;
  cfg.timings.vsync_front_porch = LCD_VSYNC_FRONT;
  cfg.timings.flags.pclk_active_neg = 0;  // vendor: data latched on the rising edge
  cfg.data_width = 16;
  cfg.bits_per_pixel = 16;
  cfg.num_fbs = 2;
  cfg.bounce_buffer_size_px = LCD_W * LCD_BOUNCE_LINES;
  cfg.dma_burst_size = 64;
  cfg.hsync_gpio_num = LCD_HSYNC;
  cfg.vsync_gpio_num = LCD_VSYNC;
  cfg.de_gpio_num = LCD_DE;
  cfg.pclk_gpio_num = LCD_PCLK;
  cfg.disp_gpio_num = -1;
  // vendor data0..15 = B0-4, G0-5, R0-4
  const int pins[16] = {LCD_B0, LCD_B1, LCD_B2, LCD_B3, LCD_B4, LCD_G0, LCD_G1, LCD_G2,
                        LCD_G3, LCD_G4, LCD_G5, LCD_R0, LCD_R1, LCD_R2, LCD_R3, LCD_R4};
  for (int i = 0; i < 16; ++i) cfg.data_gpio_nums[i] = pins[i];
  cfg.flags.fb_in_psram = 1;
  if (esp_lcd_new_rgb_panel(&cfg, &panel) != ESP_OK) return false;
  esp_lcd_rgb_panel_event_callbacks_t cbs = {};
  if (LCD_BOUNCE_LINES > 0) cbs.on_frame_buf_complete = onFrameDone;  // the whole buffer was read
  else cbs.on_vsync = onFrameDone;
  esp_lcd_rgb_panel_register_event_callbacks(panel, &cbs, nullptr);
  if (esp_lcd_panel_reset(panel) != ESP_OK || esp_lcd_panel_init(panel) != ESP_OK) return false;
  void *a = nullptr, *b = nullptr;
  if (esp_lcd_rgb_panel_get_frame_buffer(panel, 2, &a, &b) != ESP_OK || !a || !b) return false;
  fb[0] = (uint16_t*)a;
  fb[1] = (uint16_t*)b;
  return true;
}

// The panel's interrupt is allocated on the core that creates it.
static volatile bool createdOk = false;
static void createTask(void* done) {
  createdOk = createPanel();
  xSemaphoreGive((SemaphoreHandle_t)done);
  vTaskDelete(nullptr);
}

bool displayInit() {
  frameSem = xSemaphoreCreateBinary();
  st7701Init();
  SemaphoreHandle_t done = xSemaphoreCreateBinary();
  xTaskCreatePinnedToCore(createTask, "lcd-init", 4096, done, 5, nullptr, LCD_ISR_CORE);
  xSemaphoreTake(done, portMAX_DELAY);
  vSemaphoreDelete(done);
  if (!createdOk) {
    Serial.println("[lcd] RGB panel FAILED (PSRAM?)");
    return false;
  }
  canvas = (uint16_t*)heap_caps_aligned_alloc(64, LCD_W * LCD_H * 2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!canvas) return false;
  memset(canvas, 0, LCD_W * LCD_H * 2);
  memset(fb[0], 0, LCD_W * LCD_H * 2);
  memset(fb[1], 0, LCD_W * LCD_H * 2);
  esp_cache_msync(fb[0], LCD_W * LCD_H * 2, ESP_CACHE_MSYNC_FLAG_DIR_C2M);
  esp_cache_msync(fb[1], LCD_W * LCD_H * 2, ESP_CACHE_MSYNC_FLAG_DIR_C2M);
  front = 0;
  esp_lcd_panel_draw_bitmap(panel, 0, 0, LCD_W, LCD_H, fb[0]);
  Serial.printf("[lcd] ST7701 480x480 RGB565, 2 PSRAM frame buffers, %d-line bounce buffers, pclk %.1f MHz\n",
                LCD_BOUNCE_LINES, LCD_PCLK_HZ / 1e6);
  return true;
}

uint16_t* displayCanvas() { return canvas; }
const DisplayStats& displayStats() {
  stats.panelFrames = frames;
  return stats;
}

static inline void mapPx(int x, int y, int& px, int& py) {
#if SUFLET_ROTATION == 90
  px = LCD_W - 1 - y;
  py = x;
#elif SUFLET_ROTATION == 180
  px = LCD_W - 1 - x;
  py = LCD_H - 1 - y;
#elif SUFLET_ROTATION == 270
  px = y;
  py = LCD_H - 1 - x;
#else
  px = x;
  py = y;
#endif
}

static void copyRect(uint16_t* dst, const Rect& r) {
#if SUFLET_ROTATION == 0
  const size_t n = (size_t)r.w() * 2;
  for (int y = r.y0; y < r.y1; ++y) memcpy(dst + y * LCD_W + r.x0, canvas + y * LCD_W + r.x0, n);
  if (LCD_BOUNCE_LINES == 0) {  // the DMA reads PSRAM directly: write the cache back
    uintptr_t a = (uintptr_t)(dst + r.y0 * LCD_W) & ~(uintptr_t)63;
    uintptr_t e = ((uintptr_t)(dst + r.y1 * LCD_W) + 63) & ~(uintptr_t)63;
    esp_cache_msync((void*)a, e - a, ESP_CACHE_MSYNC_FLAG_DIR_C2M);
  }
#else
  for (int y = r.y0; y < r.y1; ++y)
    for (int x = r.x0; x < r.x1; ++x) {
      int px, py;
      mapPx(x, y, px, py);
      dst[py * LCD_W + px] = canvas[y * LCD_W + x];
    }
  if (LCD_BOUNCE_LINES == 0) esp_cache_msync(dst, LCD_W * LCD_H * 2, ESP_CACHE_MSYNC_FLAG_DIR_C2M);
#endif
}

void displayPresent(const Rect& changedIn) {
  if (!panel || !canvas || changedIn.empty()) return;
  Rect changed = changedIn;
  Rect copy = changed;
  copy.add(lastChanged);
  const int64_t t0 = esp_timer_get_time();
  // the back buffer may still be scanned out right after a switch: wait
  // until the panel finished two frames from the new front buffer
  while ((uint32_t)(frames - switchedAt) < 2) {
    ++stats.waits;
    if (xSemaphoreTake(frameSem, pdMS_TO_TICKS(60)) != pdTRUE) break;  // the panel stopped: don't hang
  }
  const int64_t t1 = esp_timer_get_time();
  const int back = front ^ 1;
  copyRect(fb[back], copy);
  esp_lcd_panel_draw_bitmap(panel, 0, 0, LCD_W, LCD_H, fb[back]);  // a frame buffer: switch, no copy
  front = back;
  switchedAt = frames;
  lastChanged = changed;
  const int64_t t2 = esp_timer_get_time();
  stats.waitMs = (t1 - t0) / 1000.0f;
  stats.copyMs = (t2 - t1) / 1000.0f;
  stats.copiedPx = (uint32_t)(copy.w() * copy.h());
  ++stats.presents;
}

void displayPower(bool on) {
  if (on == panelOn || !panel) return;
  panelOn = on;
  spiPins(true);
  if (on) {
    esp_lcd_rgb_panel_set_pclk(panel, LCD_PCLK_HZ);
    st7701Cmd(0x11, nullptr, 0);  // sleep out
    delay(120);
    st7701Cmd(0x29, nullptr, 0);
  } else {
    backlight(0);
    st7701Cmd(0x28, nullptr, 0);  // display off
    st7701Cmd(0x10, nullptr, 0);  // sleep in
    esp_lcd_rgb_panel_set_pclk(panel, LCD_PCLK_SLEEP_HZ);  // fewer bounce interrupts, less PSRAM traffic
  }
  spiPins(false);
}

// ---------------------------------------------------------- backlight ---

void backlightInit() {
  ledcAttach(LCD_BL, LCD_BL_FREQ, LCD_BL_BITS);
  ledcWrite(LCD_BL, 0);
}

void backlight(float level) {
  if (level < 0) level = 0;
  if (level > 1) level = 1;
  const uint32_t maxDuty = (1u << LCD_BL_BITS) - 1;
  // gamma 2.2: equal steps of the slider look like equal steps of light, and
  // the low end (night) gets fine resolution
  uint32_t duty = (uint32_t)lroundf(powf(level, 2.2f) * maxDuty);
  if (level > 0 && duty == 0) duty = 1;
  ledcWrite(LCD_BL, duty);
}

// --------------------------------------------------------------- GT911 ---

static uint8_t tpAddr = TOUCH_ADDR;

static bool gtWrite(uint16_t reg, uint8_t v) {
  Wire.beginTransmission(tpAddr);
  Wire.write(reg >> 8);
  Wire.write(reg & 0xFF);
  Wire.write(v);
  return Wire.endTransmission() == 0;
}

static bool gtRead(uint16_t reg, uint8_t* buf, size_t n) {
  Wire.beginTransmission(tpAddr);
  Wire.write(reg >> 8);
  Wire.write(reg & 0xFF);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)tpAddr, (int)n) != (int)n) return false;
  for (size_t i = 0; i < n; ++i) buf[i] = Wire.read();
  return true;
}

bool touchInit() {
  // vendor touch_gt911_reset(): INT low, reset low, reset high, 50 ms, INT
  // high, then INT becomes an input. INT low while the reset is released
  // selects I2C address 0x5D.
  pinMode(TOUCH_INT, OUTPUT);
  digitalWrite(TOUCH_INT, LOW);
  delay(150);
  exioWrite(EXIO_TP_RST, false);
  delay(150);
  exioWrite(EXIO_TP_RST, true);
  delay(50);
  digitalWrite(TOUCH_INT, HIGH);
  pinMode(TOUCH_INT, INPUT);
  delay(50);
  uint8_t id[4] = {0};
  for (uint8_t a : {(uint8_t)TOUCH_ADDR, (uint8_t)0x14}) {
    tpAddr = a;
    if (gtRead(0x8140, id, 3)) {  // product id, ASCII "911"
      Serial.printf("[touch] GT%c%c%c at 0x%02X\n", id[0], id[1], id[2], a);
      return true;
    }
  }
  return false;
}

bool touchRead(float& x, float& y) {
  uint8_t st = 0;
  if (!gtRead(0x814E, &st, 1)) return false;
  static bool down = false;
  static float lx = 0, ly = 0;
  if (!(st & 0x80)) {  // no new report since the last read: keep the last state
    x = lx;
    y = ly;
    return down;
  }
  const int n = st & 0x0F;
  if (n > 0) {
    uint8_t p[4];
    if (gtRead(0x8150, p, 4)) {  // point 1: x lo, x hi, y lo, y hi
      lx = (float)(p[0] | (p[1] << 8));
      ly = (float)(p[2] | (p[3] << 8));
    }
  }
  gtWrite(0x814E, 0);  // hand the buffer back to the controller
  down = n > 0;
  x = lx;
  y = ly;
  return down;
}

}  // namespace lcd28

#endif
