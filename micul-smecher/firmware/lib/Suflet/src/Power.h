// The low-battery shutdown of a board with a power manager (SOUL S: the AXP2101, src/pmu.cpp). Pure logic, tested
// on the PC (test_density.cpp). SOUL saves what it knows and asks the PMU to cut the power before the cell is so
// low that the S3 browns out mid-write (an NVS page half written, SOUL Memory's copy torn).
#pragma once

namespace suflet {

struct LowBattery {
  // [estimare] a LiPo at ~3.35 V under SOUL's ~70 mA is in its last few %; the gauge's own 3 % agrees. Three reads
  // in a row (the loop reads every 2 s: 6 s) so a radio burst's dip never turns SOUL off.
  static constexpr int kPct = 3, kMv = 3350, kStrikes = 3;
  int strikes = 0;
  // one PMU read; true when it is time to save and power off (USB power or no cell: never)
  bool update(bool battery, bool vbus, int pct, int mv) {
    const bool low = battery && !vbus && ((pct >= 0 && pct <= kPct) || (mv > 0 && mv < kMv));
    strikes = low ? strikes + 1 : 0;
    return strikes >= kStrikes;
  }
};

}  // namespace suflet
