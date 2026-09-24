// Pin maps for the supported dev boards. Values come from Waveshare's
// schematics / demo code (1.43) and the MIT-licensed xiaozhi-esp32 board
// config (1.75). See ../research/02-hardware-2026-09-24.md.
#pragma once

#if defined(SUFLET_BOARD_AMOLED143)
// Waveshare ESP32-S3-Touch-AMOLED-1.43 (no audio). FT3168 touch, QMI8658.
#define BOARD_NAME "AMOLED-1.43"
#define LCD_CS 9
#define LCD_SCLK 10
#define LCD_D0 11
#define LCD_D1 12
#define LCD_D2 13
#define LCD_D3 14
#define LCD_RST 21
#define LCD_COL_OFFSET 6  // CO5300 panels; SH8601 panels use 0 (build with -DSUFLET_PANEL_SH8601)
#define I2C_SDA 47
#define I2C_SCL 48
#define TOUCH_FT3168 1
#define TOUCH_ADDR 0x38
#define TOUCH_RST -1
#define TOUCH_INT -1
#define TOUCH_MIRROR_X 0  // flip if taps land on the wrong side
#define TOUCH_MIRROR_Y 0
#define IMU_ADDR 0x6B
#define IMU_INT 8
#define RTC_INT 15
#define BAT_ADC_PIN 4  // divider x3
#define HAS_AUDIO 0
#define HAS_PMU 0

#elif defined(SUFLET_BOARD_AMOLED175)
// Waveshare ESP32-S3-Touch-AMOLED-1.75: CST9217 touch, QMI8658, AXP2101 PMU,
// ES8311 + ES7210 codecs with two mics and a speaker (audio used in v1).
#define BOARD_NAME "AMOLED-1.75"
#define LCD_CS 12
#define LCD_SCLK 38
#define LCD_D0 4
#define LCD_D1 5
#define LCD_D2 6
#define LCD_D3 7
#define LCD_RST 39
#define LCD_COL_OFFSET 6  // xiaozhi: esp_lcd_panel_set_gap(panel, 0x06, 0)
#define I2C_SDA 15
#define I2C_SCL 14
#define TOUCH_CST9217 1
#define TOUCH_ADDR 0x5A
#define TOUCH_RST 40
#define TOUCH_INT 11
#define TOUCH_MIRROR_X 1  // xiaozhi config: mirror_x = mirror_y = 1
#define TOUCH_MIRROR_Y 1
#define IMU_ADDR 0x6B
#define IMU_INT -1
#define RTC_INT -1
#define BAT_ADC_PIN -1
#define HAS_AUDIO 1
#define HAS_PMU 1
#define PMU_ADDR 0x34
#define AUDIO_I2S_MCLK 42
#define AUDIO_I2S_WS 45
#define AUDIO_I2S_BCLK 9
#define AUDIO_I2S_DIN 10
#define AUDIO_I2S_DOUT 8
#define AUDIO_PA_PIN 46

#else
#error "Pick a board: -DSUFLET_BOARD_AMOLED143=1 or -DSUFLET_BOARD_AMOLED175=1"
#endif

#define LCD_W 466
#define LCD_H 466
#define BOOT_BUTTON 0

// Software rotation of the whole picture: 0, 90, 180 or 270 degrees.
// The native "up" edge of these panels is not documented; set it once.
#ifndef SUFLET_ROTATION
#define SUFLET_ROTATION 0
#endif

// Accelerometer axes -> device frame (+X right, +Y up to the ring, +Z out
// of the screen). Check with the serial command 'i' lying face-up (0,0,+1)
// and standing on its bottom edge (0,+1,0), then adjust.
#ifndef IMU_MAP
#define IMU_MAP(ax, ay, az, X, Y, Z) \
  do {                               \
    X = (ax);                        \
    Y = (ay);                        \
    Z = (az);                        \
  } while (0)
#endif
