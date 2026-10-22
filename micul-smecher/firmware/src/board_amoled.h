// Board support for the QSPI AMOLEDs (SOUL S = the Waveshare ESP32-S3-Touch-AMOLED-1.75, CO5300; and the
// AMOLED-1.43): the panel through Arduino_GFX, written tear-free and without blocking the loop. Only compiled for
// the non-RGB boards (board.h LCD_IS_RGB 0). firmware/SOUL-S.md §6, BRINGUP.md §S.
//
//   present   each changed rectangle goes out in row strips straight from the canvas (PSRAM) through a 16 KB
//             internal-RAM bounce buffer (no full-frame PSRAM copy: 1.9.1 drops 1.9.0's 434 KB pushBuf), in bands
//             timed against the panel's scan (TE line, lib/Suflet/src/TearSync.h) so a write never shears
//   TE        0x35 0x00 after the panel's init; GPIO13 (LCD_TE) rises at each V-blank: an edge interrupt measures
//             the refresh period and the V-blank (the CO5300's refresh is not published: measured, `E`)
//   power     never a delay() in the loop (Arduino_CO5300::displayOn/Off block ~240 ms): a short face-down only
//             darkens the panel (0x51 = 0); after kSleepAfterMs dark it goes to sleep-in (DISPOFF, SLPIN); waking
//             sends SLPOUT and DISPON ≥ 120 ms later while the loop keeps running and the frame waits in the canvas
#pragma once
#include "board.h"

#if !LCD_IS_RGB
#include <stdint.h>

#include "Canvas.h"  // suflet::RectList

namespace amoled {

bool displayInit();          // the panel (blocking ~0.5 s, at boot only), TE on, the canvas in PSRAM
uint16_t* displayCanvas();   // LCD_W x LCD_H RGB565, what the panel shows
void displayPresent(const suflet::RectList& changed);
void backlight(float level);  // 0..1 -> 0x51 (held while the panel wakes, sent with DISPON)
void displayPower(bool on);   // non-blocking (see above)
void displayTick(uint32_t nowMs);  // every loop: the power state machine
void displaySleepNow();       // before deep sleep: DISPOFF + SLPIN, blocking (nothing runs after it anyway)
void setTearSync(bool on);    // serial `X`: off = 1.9.0's unsynchronised writes (to film the difference)

struct DisplayStats {
  bool teSeen = false;           // TE edges arrive (GPIO13)
  bool sync = true;              // tear sync on
  float periodUs = 0, vblankUs = 0;  // measured from the TE edges
  uint32_t edges = 0;
  float pxPerUs = 0;             // the measured write rate (payload, strips and window set-up included)
  uint32_t bands = 0, waits = 0;  // since the last `E`
  float waitMs = 0;              // total waited for the scan since the last `E`
  float pushMs = 0;              // last present
  uint32_t pushedPx = 0;         // last present
  uint8_t state = 0;             // 0 on, 1 dark (brightness 0), 2 sleep-in, 3 waking (SLPOUT sent)
  uint32_t lastWakeMs = 0;       // SLPOUT -> DISPON + first frame, last wake (ms)
};
DisplayStats& displayStats();
void displayReport();  // serial `E`

}  // namespace amoled

#endif
