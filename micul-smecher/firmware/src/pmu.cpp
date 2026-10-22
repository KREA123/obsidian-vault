// pmu.h: the AXP2101 set-up, each register named (X-Powers AXP2101 datasheet register map; the names are
// XPowersLib's, lewisxhe, MIT) and the reason for each value. Values marked [xiaozhi] are those of the MIT
// xiaozhi-esp32 board support for this board, kept; [SOUL] are ours.
#include "pmu.h"

#if HAS_PMU
#include <Arduino.h>
#include <Wire.h>

namespace pmu {

namespace {
// registers
constexpr uint8_t STATUS1 = 0x00;          // bit 5 VBUS good, bit 3 battery present
constexpr uint8_t STATUS2 = 0x01;          // bits 7:5 current direction (1 = charging), 2:0 charger state
constexpr uint8_t COMMON_CONFIG = 0x10;    // bit 0: soft power off
constexpr uint8_t CHARGE_GAUGE_WDT = 0x18; // bit 3 fuel gauge enable, bit 1 charger enable
constexpr uint8_t PWROFF_EN = 0x22;        // power-off sources
constexpr uint8_t IRQ_OFF_ON_LEVEL = 0x27; // PWR key timings
constexpr uint8_t ADC_CHANNEL = 0x30;      // bit 0 VBAT, 2 VBUS, 3 VSYS, 4 die temperature
constexpr uint8_t VBAT_H = 0x34, VBUS_H = 0x38, VSYS_H = 0x3A;  // ADC results, mV (H then L)
constexpr uint8_t IPRECHG = 0x61;          // pre-charge current, 25 mA steps
constexpr uint8_t ICC_CHG = 0x62;          // constant charge current: 0..8 = 0..200 mA (25 mA), 9.. = 300 mA + 100 mA
constexpr uint8_t ITERM = 0x63;            // termination current [3:0] 25 mA steps, bit 4 termination enable
constexpr uint8_t CV_CHG = 0x64;           // charge voltage: 1 = 4.0 V, 2 = 4.1 V, 3 = 4.2 V, 4 = 4.35 V, 5 = 4.4 V
constexpr uint8_t BAT_DET = 0x68;          // bit 0: battery detection
constexpr uint8_t DC_ONOFF = 0x80, DC1_VOL = 0x82;          // DCDC1: the board's 3.3 V
constexpr uint8_t LDO_ONOFF0 = 0x90, LDO_ONOFF1 = 0x91, ALDO1_VOL = 0x92;  // ALDO1: the 3.3 V of the peripherals
constexpr uint8_t BAT_PERCENT = 0xA4;      // the fuel gauge, 0..100

bool wr(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(PMU_ADDR);
  Wire.write(reg);
  Wire.write(v);
  return Wire.endTransmission() == 0;
}
bool rd(uint8_t reg, uint8_t* buf, size_t n) {
  Wire.beginTransmission(PMU_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)PMU_ADDR, (int)n) != (int)n) return false;
  for (size_t i = 0; i < n; ++i) buf[i] = Wire.read();
  return true;
}
int rd8(uint8_t reg) {
  uint8_t v;
  return rd(reg, &v, 1) ? v : -1;
}
bool setBits(uint8_t reg, uint8_t mask) {
  const int v = rd8(reg);
  return v >= 0 && wr(reg, (uint8_t)(v | mask));
}
int adcMv(uint8_t hi, uint8_t bits) {  // the ADC pairs: H holds the top `bits` bits
  uint8_t b[2];
  if (!rd(hi, b, 2)) return 0;
  return ((b[0] & ((1 << bits) - 1)) << 8) | b[1];
}
constexpr uint8_t cvCode() { return SUFLET_PMU_CV_MV >= 4200 ? 3 : SUFLET_PMU_CV_MV >= 4100 ? 2 : 1; }
}  // namespace

bool begin() {
  bool ok = true;
  ok &= wr(PWROFF_EN, 0b110);          // [xiaozhi] the PWR key held past OFF level powers off; PWROK low restarts
  ok &= wr(IRQ_OFF_ON_LEVEL, 0x10);    // [xiaozhi] PWR key: on 128 ms, off after 4 s held, IRQ at 1.5 s
  ok &= wr(DC_ONOFF, 0x01);            // [xiaozhi] DCDC1 on, DCDC2-5 off (unused on this board)
  ok &= wr(LDO_ONOFF0, 0x00);          // [xiaozhi] every LDO off while the voltages are set
  ok &= wr(LDO_ONOFF1, 0x00);
  ok &= wr(DC1_VOL, (3300 - 1500) / 100);  // [xiaozhi] DCDC1 = 3.3 V (1.5 V + 100 mV steps)
  ok &= wr(ALDO1_VOL, (3300 - 500) / 100);  // [xiaozhi] ALDO1 = 3.3 V (0.5 V + 100 mV steps)
  ok &= wr(LDO_ONOFF0, 0x01);          // [xiaozhi] ALDO1 on
  ok &= wr(CV_CHG, cvCode());          // [SOUL] SUFLET_PMU_CV_MV (pmu.h): 4.2 V, the cell's rating (xiaozhi: 4.1 V)
  ok &= wr(IPRECHG, 0x02);             // [xiaozhi] pre-charge 50 mA
  ok &= wr(ICC_CHG, 0x08);             // [xiaozhi] 200 mA: 0.27 C for the 750 mAh 603040, safe for any cell >= 400 mAh
                                       //  (the dev board takes whatever LiPo is plugged in); ~4 h to full [estimare]
  ok &= wr(ITERM, 0x10 | 0x01);        // [SOUL] stop at 25 mA (C/30), termination ON (xiaozhi's 0x01 cleared bit 4)
  ok &= setBits(BAT_DET, 0x01);        // [SOUL] battery detection: STATUS1 bit 3 means something
  ok &= setBits(CHARGE_GAUGE_WDT, 0x08 | 0x02);  // [SOUL] fuel gauge on (0xA4 is valid), charger on
  ok &= setBits(ADC_CHANNEL, 0x01 | 0x04 | 0x08);  // [SOUL] measure VBAT, VBUS, VSYS
  // AXP_IRQ reaches the S3 only through the board's TCA9554 (EXIO5, Waveshare schematic): not wired up; SOUL polls
  // the status every 2 s instead (main.cpp), which is enough for VBUS in / out and the low-battery shutdown
  const int cv = rd8(CV_CHG), it = rd8(ITERM);
  Serial.printf("[pmu] AXP2101 %s: charge %d mV (0x64=%02X), 200 mA, term 25 mA (0x63=%02X), gauge + detection on\n",
                ok ? "ok" : "FAILED", SUFLET_PMU_CV_MV, cv, it);
  return ok;
}

bool read(State& s) {
  uint8_t st[2];
  s.ok = rd(STATUS1, st, 2);
  if (!s.ok) return false;
  s.vbus = st[0] & 0x20;
  s.battery = st[0] & 0x08;
  s.chg = st[1] & 0x07;
  s.charging = ((st[1] >> 5) & 0x03) == 1;
  s.full = s.chg == 4;
  s.vbatMv = s.battery ? adcMv(VBAT_H, 5) : 0;
  s.vbusMv = adcMv(VBUS_H, 6);
  s.vsysMv = adcMv(VSYS_H, 6);
  const int pct = s.battery ? rd8(BAT_PERCENT) : -1;
  s.pct = pct >= 0 && pct <= 100 ? pct : -1;
  return true;
}

void report() {
  State s;
  read(s);
  Serial.printf("[pmu] %s, battery %s %d%% %d mV, VBUS %s %d mV, VSYS %d mV, charger %s (state %u)\n", s.ok ? "ok" : "NOT FOUND",
                s.battery ? "yes" : "NO", s.pct, s.vbatMv, s.vbus ? "good" : "none", s.vbusMv, s.vsysMv,
                s.full ? "done" : s.charging ? "charging" : "idle", (unsigned)s.chg);
  static const uint8_t regs[] = {STATUS1, STATUS2, CHARGE_GAUGE_WDT, PWROFF_EN, IRQ_OFF_ON_LEVEL, ADC_CHANNEL, IPRECHG,
                                 ICC_CHG, ITERM, CV_CHG, BAT_DET, DC_ONOFF, DC1_VOL, LDO_ONOFF0, ALDO1_VOL, BAT_PERCENT};
  Serial.print("[pmu] regs");
  for (uint8_t r : regs) Serial.printf(" %02X=%02X", r, rd8(r) & 0xFF);
  Serial.println();
}

void powerOff() {
  Serial.println("[pmu] power off");
  Serial.flush();
  setBits(COMMON_CONFIG, 0x01);
}

}  // namespace pmu
#endif
