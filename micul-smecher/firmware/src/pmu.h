// The AXP2101 power manager of the Waveshare AMOLED-1.75 (SOUL S), register by register (no XPowersLib: every value
// is written and documented here, firmware/SOUL-S.md §8). HAS_PMU boards only.
#pragma once
#include "board.h"

#if HAS_PMU
#include <stdint.h>

#ifndef SUFLET_PMU_CV_MV
// The charge voltage, chosen on purpose (2026-10-22): 4200 mV, the 603040 cell's rated charge voltage
// (docs/12-SIZE-S.md §2.4: A&S Power, 4.2 V charge). xiaozhi's 4100 mV gives up ~10 % of the capacity [estimare]
// for a longer cycle life; build with -DSUFLET_PMU_CV_MV=4100 for that. Allowed: 4000, 4100, 4200.
#define SUFLET_PMU_CV_MV 4200
#endif

namespace pmu {

struct State {
  bool ok = false;        // the AXP2101 answered
  bool battery = false;   // a cell is connected (battery detection on)
  bool vbus = false;      // USB power is good
  bool charging = false;  // the charger is charging (pre / constant current / constant voltage)
  bool full = false;      // charge done
  int pct = -1;           // the fuel gauge, 0..100 (-1: no battery / not ready)
  int vbatMv = 0, vbusMv = 0, vsysMv = 0;
  uint8_t chg = 0;        // STATUS2[2:0]: 0 trickle, 1 pre, 2 CC, 3 CV, 4 done, 5 not charging
};

bool begin();             // the set-up below, read back; false if the PMU does not answer
bool read(State& s);      // ~1 ms of I2C
void report();            // serial `G`: every register written + what it reads now
void powerOff();          // the PMU cuts the power (COMMON_CONFIG bit 0); a press of PWR turns SOUL on again

}  // namespace pmu
#endif
