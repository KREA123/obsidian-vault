// Board support for the Waveshare ESP32-S3-Touch-LCD-2.8C ("SOUL M"):
// the TCA9554 IO expander (LCD/touch reset, LCD chip select, buzzer), the
// ST7701 RGB panel, the backlight PWM and the GT911 touch controller.
// Only compiled for -DSUFLET_BOARD_LCD28=1.
#pragma once
#include "board.h"

#if defined(SUFLET_BOARD_LCD28)
#include <Arduino_GFX_Library.h>

namespace lcd28 {

bool exioInit();                   // expander: pins, safe levels; false if not found
void exioWrite(uint8_t bit, bool high);
void buzzer(bool on);

// ST7701: hardware reset, init sequence over 9-bit SPI (CS on the
// expander), then the RGB panel. Returns the display (Arduino_GFX), or
// nullptr if the framebuffer could not be allocated.
Arduino_GFX* displayCreate();
bool displayBegin(Arduino_GFX* gfx);

// Backlight 0..1 (perceptual: squared), 0 = fully off.
void backlightInit();
void backlight(float level);

bool touchInit();  // GT911 reset with address select, then probe
bool touchRead(float& x, float& y);

}  // namespace lcd28

#endif
