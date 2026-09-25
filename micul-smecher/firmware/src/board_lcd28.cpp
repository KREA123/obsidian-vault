// Waveshare ESP32-S3-Touch-LCD-2.8C board support. Every value below is
// taken from the vendor's ESP-IDF demo "ESP32-S3-Touch-LCD-2.8C-Test"
// (main/LCD_Driver/ST7701S.c, EXIO/TCA9554PWR.c, Touch_Driver/GT911.c,
// Buzzer/Buzzer.c), downloaded from the Waveshare wiki on 2026-09-25.
#include "board_lcd28.h"

#if defined(SUFLET_BOARD_LCD28)
#include <Wire.h>

namespace lcd28 {

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
  // line, which is open drain (the vendor makes all 8 outputs).
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

// ------------------------------------------------------------- ST7701 ---

// Vendor ST7701S_screen_init(type 1, "2.8inch"), transcribed 1:1 into
// Arduino_GFX batch operations. 0x3A = 0x66 is what the vendor sends
// (the bus is still 16-bit RGB565; the panel's low bits are tied).
static const uint8_t kSt7701Init[] = {
    BEGIN_WRITE,
    WRITE_C8_BYTES, 0xFF, 5, 0x77, 0x01, 0x00, 0x00, 0x13,
    WRITE_C8_D8, 0xEF, 0x08,
    WRITE_C8_BYTES, 0xFF, 5, 0x77, 0x01, 0x00, 0x00, 0x10,
    WRITE_C8_D16, 0xC0, 0x3B, 0x00,
    WRITE_C8_D16, 0xC1, 0x10, 0x0C,
    WRITE_C8_D16, 0xC2, 0x07, 0x0A,
    WRITE_C8_D8, 0xC7, 0x00,
    WRITE_C8_D8, 0xCC, 0x10,
    WRITE_C8_D8, 0xCD, 0x08,
    WRITE_C8_BYTES, 0xB0, 16,
    0x05, 0x12, 0x98, 0x0E, 0x0F, 0x07, 0x07, 0x09, 0x09, 0x23, 0x05, 0x52, 0x0F, 0x67, 0x2C, 0x11,
    WRITE_C8_BYTES, 0xB1, 16,
    0x0B, 0x11, 0x97, 0x0C, 0x12, 0x06, 0x06, 0x08, 0x08, 0x22, 0x03, 0x51, 0x11, 0x66, 0x2B, 0x0F,
    WRITE_C8_BYTES, 0xFF, 5, 0x77, 0x01, 0x00, 0x00, 0x11,
    WRITE_C8_D8, 0xB0, 0x5D,
    WRITE_C8_D8, 0xB1, 0x3E,
    WRITE_C8_D8, 0xB2, 0x81,
    WRITE_C8_D8, 0xB3, 0x80,
    WRITE_C8_D8, 0xB5, 0x4E,
    WRITE_C8_D8, 0xB7, 0x85,
    WRITE_C8_D8, 0xB8, 0x20,
    WRITE_C8_D8, 0xC1, 0x78,
    WRITE_C8_D8, 0xC2, 0x78,
    WRITE_C8_D8, 0xD0, 0x88,
    WRITE_C8_BYTES, 0xE0, 3, 0x00, 0x00, 0x02,
    WRITE_C8_BYTES, 0xE1, 11, 0x06, 0x30, 0x08, 0x30, 0x05, 0x30, 0x07, 0x30, 0x00, 0x33, 0x33,
    WRITE_C8_BYTES, 0xE2, 12, 0x11, 0x11, 0x33, 0x33, 0xF4, 0x00, 0x00, 0x00, 0xF4, 0x00, 0x00, 0x00,
    WRITE_C8_BYTES, 0xE3, 4, 0x00, 0x00, 0x11, 0x11,
    WRITE_C8_D16, 0xE4, 0x44, 0x44,
    WRITE_C8_BYTES, 0xE5, 16,
    0x0D, 0xF5, 0x30, 0xF0, 0x0F, 0xF7, 0x30, 0xF0, 0x09, 0xF1, 0x30, 0xF0, 0x0B, 0xF3, 0x30, 0xF0,
    WRITE_C8_BYTES, 0xE6, 4, 0x00, 0x00, 0x11, 0x11,
    WRITE_C8_D16, 0xE7, 0x44, 0x44,
    WRITE_C8_BYTES, 0xE8, 16,
    0x0C, 0xF4, 0x30, 0xF0, 0x0E, 0xF6, 0x30, 0xF0, 0x08, 0xF0, 0x30, 0xF0, 0x0A, 0xF2, 0x30, 0xF0,
    WRITE_C8_D16, 0xE9, 0x36, 0x01,
    WRITE_C8_BYTES, 0xEB, 7, 0x00, 0x01, 0xE4, 0xE4, 0x44, 0x88, 0x40,
    WRITE_C8_BYTES, 0xED, 16,
    0xFF, 0x10, 0xAF, 0x76, 0x54, 0x2B, 0xCF, 0xFF, 0xFF, 0xFC, 0xB2, 0x45, 0x67, 0xFA, 0x01, 0xFF,
    WRITE_C8_BYTES, 0xEF, 6, 0x08, 0x08, 0x08, 0x45, 0x3F, 0x54,
    WRITE_C8_BYTES, 0xFF, 5, 0x77, 0x01, 0x00, 0x00, 0x00,
    WRITE_COMMAND_8, 0x11,  // sleep out
    END_WRITE,
    DELAY, 120,
    BEGIN_WRITE,
    WRITE_C8_D8, 0x3A, 0x66,
    WRITE_C8_D8, 0x36, 0x00,
    WRITE_C8_D8, 0x35, 0x00,
    WRITE_COMMAND_8, 0x29,  // display on
    END_WRITE,
};

static Arduino_DataBus* spiBus = nullptr;

Arduino_GFX* displayCreate() {
  // 3-wire SPI, 9-bit (no DC pin); CS is driven through the expander below.
  spiBus = new Arduino_SWSPI(GFX_NOT_DEFINED /* DC */, GFX_NOT_DEFINED /* CS */, LCD_SPI_SCK, LCD_SPI_MOSI);
  auto* rgb = new Arduino_ESP32RGBPanel(
      LCD_DE, LCD_VSYNC, LCD_HSYNC, LCD_PCLK,                               //
      LCD_R0, LCD_R1, LCD_R2, LCD_R3, LCD_R4,                               //
      LCD_G0, LCD_G1, LCD_G2, LCD_G3, LCD_G4, LCD_G5,                       //
      LCD_B0, LCD_B1, LCD_B2, LCD_B3, LCD_B4,                               //
      1 /* hsync idle high, as esp_lcd's default */, LCD_HSYNC_FRONT, LCD_HSYNC_PULSE, LCD_HSYNC_BACK,  //
      1 /* vsync idle high */, LCD_VSYNC_FRONT, LCD_VSYNC_PULSE, LCD_VSYNC_BACK,                       //
      0 /* pclk active on rising edge */, LCD_PCLK_HZ, false /* little endian */, 0, 0, LCD_BOUNCE_PX);
  return new Arduino_RGB_Display(LCD_W, LCD_H, rgb, 0 /* rotation */, true /* auto flush */, spiBus,
                                 GFX_NOT_DEFINED /* reset is on the expander */, kSt7701Init,
                                 sizeof(kSt7701Init));
}

bool displayBegin(Arduino_GFX* gfx) {
  // vendor ST7701S_reset(): EXIO1 low 10 ms, high, then 100 ms before init
  exioWrite(EXIO_LCD_RST, false);
  delay(10);
  exioWrite(EXIO_LCD_RST, true);
  delay(120);
  exioWrite(EXIO_LCD_CS, false);  // vendor ST7701S_CS_EN()
  const bool ok = gfx->begin();   // SW reset + init table + RGB panel/framebuffer
  exioWrite(EXIO_LCD_CS, true);   // vendor ST7701S_CS_Dis(): SPI lines are free again
  return ok;
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
  // squared: the low end gets the fine steps (the night dimming lives there)
  uint32_t duty = (uint32_t)lroundf(level * level * maxDuty);
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
  // vendor touch_gt911_reset(): INT low, reset low 150 ms, reset high,
  // 50 ms, INT high, then INT becomes an input. INT low while the reset is
  // released selects I2C address 0x5D.
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
