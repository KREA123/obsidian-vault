// Pin maps for the supported dev boards. Values come from Waveshare's
// schematics / demo code (1.43, 2.8C) and the MIT-licensed xiaozhi-esp32
// board config (1.75). See ../research/02-hardware-2026-09-24.md and
// ../research/12-ecran-mai-mare.md (size M).
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
#define DISPLAY_GEOMETRY suflet::displays::kAmoled143

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
#define DISPLAY_GEOMETRY suflet::displays::kAmoled175

#elif defined(SUFLET_BOARD_LCD28)
// Waveshare ESP32-S3-Touch-LCD-2.8C ("SOUL M"): round 2.8" IPS 480x480,
// ST7701 on a 16-bit RGB565 parallel bus (init over 3-wire 9-bit SPI),
// GT911 touch, QMI8658 IMU, PCF85063 RTC, TCA9554 IO expander, ETA6098
// Li-ion charger (MX1.25), a buzzer, a TF slot. ESP32-S3R8: 8 MB PSRAM,
// 16 MB flash. No PMU, no codec, no microphones, no speaker.
// Source: Waveshare wiki + the vendor ESP-IDF demo (LCD_Driver/ST7701S.*,
// EXIO/TCA9554PWR.*, Touch_Driver/GT911.c, BAT_Driver) + schematic,
// all read 2026-09-25.
#define BOARD_NAME "LCD-2.8C"
#define LCD_IS_RGB 1
#define LCD_W 480
#define LCD_H 480
// RGB bus (vendor EXAMPLE_PIN_NUM_*). Vendor data0..15 = B0-4, G0-5, R0-4.
#define LCD_DE 40
#define LCD_VSYNC 39
#define LCD_HSYNC 38
#define LCD_PCLK 41
#define LCD_R0 46
#define LCD_R1 3
#define LCD_R2 8
#define LCD_R3 18
#define LCD_R4 17
#define LCD_G0 14
#define LCD_G1 13
#define LCD_G2 12
#define LCD_G3 11
#define LCD_G4 10
#define LCD_G5 9
#define LCD_B0 5
#define LCD_B1 45
#define LCD_B2 48
#define LCD_B3 47
#define LCD_B4 21
#define LCD_PCLK_HZ 18000000  // vendor EXAMPLE_LCD_PIXEL_CLOCK_HZ
// vendor timings: hsync back 10 / front 50 / pulse 8, vsync back 18 / front 8 / pulse 2, pclk rising
#define LCD_HSYNC_FRONT 50
#define LCD_HSYNC_PULSE 8
#define LCD_HSYNC_BACK 10
#define LCD_VSYNC_FRONT 8
#define LCD_VSYNC_PULSE 2
#define LCD_VSYNC_BACK 18
#define LCD_BOUNCE_PX (LCD_W * 10)  // vendor's optional bounce buffer: keeps the scan stable under BLE/flash load
// ST7701 init SPI: MOSI/SCK are GPIOs (shared with the TF slot's CMD/CLK),
// CS and RESET sit on the IO expander.
#define LCD_SPI_MOSI 1
#define LCD_SPI_SCK 2
#define LCD_BL 6  // backlight PWM, active high (vendor LEDC 5 kHz, 13 bit)
#define LCD_BL_FREQ 5000
#define LCD_BL_BITS 13
#define I2C_SDA 15
#define I2C_SCL 7
// TCA9554PWR at 0x20. EXIO1..8 = bit 0..7.
#define EXIO_ADDR 0x20
#define EXIO_LCD_RST 0  // EXIO1
#define EXIO_TP_RST 1   // EXIO2
#define EXIO_LCD_CS 2   // EXIO3
#define EXIO_SD_CS 3    // EXIO4 (TF card D3/CS; the TF slot is not used)
#define EXIO_RTC_INT 6  // EXIO7 (PCF85063 INT, open drain: kept an input here)
#define EXIO_BUZZER 7   // EXIO8, high = beep (vendor Buzzer_On)
#define TOUCH_GT911 1
#define TOUCH_ADDR 0x5D  // INT held low while reset is released (vendor); 0x14 is tried too
#define TOUCH_RST -1     // on the expander (EXIO2)
#define TOUCH_INT 16
#define TOUCH_MIRROR_X 0  // vendor: swap_xy = mirror_x = mirror_y = 0
#define TOUCH_MIRROR_Y 0
#define IMU_ADDR 0x6B
#define IMU_INT -1  // TODO(lcd28): QMI8658 INT1/INT2 routing not confirmed; we poll
#define RTC_INT -1  // on the expander (EXIO7), not a GPIO
#define BAT_ADC_PIN 4  // 200k/100k divider: x3 (vendor BAT_Driver, schematic R5/R9)
#define BAT_USB_SENSE 0  // no VBUS sense on this board: "on USB" is unknown
#define HAS_AUDIO 0  // no codec: only the buzzer (and the optional I2S parts below)
#define HAS_PMU 0
#define HAS_BUZZER 1
#define DISPLAY_GEOMETRY suflet::displays::kLcd28

// Optional I2S audio on the free pins (see README "SOUL M wiring"). The
// only GPIOs left on the 2.8C are 43/44 (UART0, on the 12-pin header),
// 42 (TF slot D0; leave the slot empty) and 0 (BOOT) / 19-20 (USB).
//   -DSUFLET_MIC_INMP441=1   INMP441 mic: SCK 43, WS 44, SD 42, L/R to GND
//   -DSUFLET_SPK_MAX98357=1  MAX98357A amp: BCLK 43, LRC 44, DIN 42
// Both at once share BCLK/WS and need a 4th data pin: set AUDIO_SPK_DOUT
// yourself (e.g. -DAUDIO_SPK_DOUT=0; TODO(lcd28): GPIO0 is a strapping pin,
// check that the amp's DIN does not pull it low at reset before using it).
#define AUDIO_I2S_BCLK 43
#define AUDIO_I2S_WS 44
#ifndef AUDIO_MIC_DIN
#define AUDIO_MIC_DIN 42
#endif
#ifndef AUDIO_SPK_DOUT
#if defined(SUFLET_MIC_INMP441) && SUFLET_MIC_INMP441
#define AUDIO_SPK_DOUT -1
#else
#define AUDIO_SPK_DOUT 42
#endif
#endif
#if defined(SUFLET_SPK_MAX98357) && SUFLET_SPK_MAX98357 && AUDIO_SPK_DOUT < 0
#error "Mic + speaker on the 2.8C need a 4th pin: build with -DAUDIO_SPK_DOUT=<gpio> (see README)"
#endif

#else
#error "Pick a board: -DSUFLET_BOARD_AMOLED143=1, -DSUFLET_BOARD_AMOLED175=1 or -DSUFLET_BOARD_LCD28=1"
#endif

#ifndef LCD_W
#define LCD_W 466
#define LCD_H 466
#endif
#ifndef LCD_IS_RGB
#define LCD_IS_RGB 0
#endif
#ifndef HAS_BUZZER
#define HAS_BUZZER 0
#endif
#ifndef BAT_USB_SENSE
#define BAT_USB_SENSE 1
#endif
#ifndef SUFLET_MIC_INMP441
#define SUFLET_MIC_INMP441 0
#endif
#ifndef SUFLET_SPK_MAX98357
#define SUFLET_SPK_MAX98357 0
#endif
#define BOOT_BUTTON 0

// Software rotation of the whole picture: 0, 90, 180 or 270 degrees.
// The native "up" edge of these panels is not documented; set it once.
// (TODO(lcd28): the 2.8C's up edge vs. its USB connector, check on the board.)
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
