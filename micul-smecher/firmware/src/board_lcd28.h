// Board support for the Waveshare ESP32-S3-Touch-LCD-2.8C ("SOUL M"):
// the TCA9554 IO expander (LCD/touch reset, LCD chip select, buzzer), the
// ST7701 RGB panel (3-wire SPI init + esp_lcd RGB with two PSRAM frame
// buffers and SRAM bounce buffers), the backlight PWM and the GT911 touch.
// Only compiled for -DSUFLET_BOARD_LCD28=1.
#pragma once
#include "board.h"

#if defined(SUFLET_BOARD_LCD28)
#include <stdint.h>

#include "Canvas.h"  // suflet::Rect

namespace lcd28 {

bool exioInit();                   // expander: pins, safe levels; false if not found
void exioWrite(uint8_t bit, bool high);
void buzzer(bool on);

// ST7701 reset + init over 9-bit SPI (CS on the expander), then the RGB
// panel. Returns false if the frame buffers could not be allocated.
bool displayInit();
// The persistent canvas SoulOS draws into (PSRAM, LCD_W x LCD_H RGB565).
uint16_t* displayCanvas();
// Push what changed: copies `changed` (+ what the other frame buffer missed)
// from the canvas into the back frame buffer and makes it the shown one at
// the next frame boundary. Never writes into the buffer being scanned out.
void displayPresent(const suflet::Rect& changed);
// Restart the RGB transmission at the next VSYNC (after flash writes).
void displayResync();
// Panel sleep (backlight off, ST7701 sleep-in, slower pixel clock) / wake.
void displayPower(bool on);
struct DisplayStats {
  uint32_t presents = 0, waits = 0, panelFrames = 0;
  float copyMs = 0, waitMs = 0;  // last present
  uint32_t copiedPx = 0;
};
const DisplayStats& displayStats();

// Backlight 0..1 (perceptual curve), 0 = fully off.
void backlightInit();
void backlight(float level);

bool touchInit();  // GT911 reset with address select, then probe
bool touchRead(float& x, float& y);

}  // namespace lcd28

#endif
