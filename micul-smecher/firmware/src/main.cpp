// SOUL firmware: SoulOS on the Waveshare round boards — the 2.8" IPS
// LCD-2.8C ("SOUL M", the main target) and the AMOLED-1.43 / 1.75 (size S).
//
// Two tasks:
//   core 1  this loop: touch, IMU, the Claude Desktop link (BLE), the Brain,
//           SoulOS and the frame (only what changed is drawn and pushed)
//   core 0  the network task (src/net.cpp): Wi-Fi, the setup portal, NTP and
//           the AI calls (HTTPS); the SOUL Cloud task (src/cloud.cpp): the
//           device WebSocket; plus the panel's bounce-buffer interrupt
// The loop never waits on the network: questions are posted and answers polled.
//
// Serial (115200): '?' lists the commands (bring-up without a finger).
#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <nvs.h>
#include <Preferences.h>
#include <SensorPCF85063.hpp>
#include <SensorQMI8658.hpp>
#include <Wire.h>
#include <esp_heap_caps.h>
#include <esp_mac.h>
#include <esp_sleep.h>
#include <esp_timer.h>

#include "AiProtocol.h"
#include "AlarmTone.h"
#include "Alarms.h"
#include "Brain.h"
#include "ClaudeLink.h"
#include "EyeRig.h"
#include "Frame.h"
#include "Geometry.h"
#include "Gestures.h"
#include "Os.h"
#include "Personality.h"
#include "audio.h"
#include "ble_link.h"
#include "board.h"
#include "bridge_lan.h"
#include "cloud.h"
#include "memory_store.h"
#include "voice_sr.h"
#include "VoiceCommands.h"
#include "net.h"
#if defined(SUFLET_BOARD_LCD28)
#include "board_lcd28.h"
#else
#include <Arduino_GFX_Library.h>
#endif
#if TOUCH_CST9217
#include <touch/TouchDrvCST92xx.h>
#endif

#ifndef SUFLET_VOICE
#define SUFLET_VOICE 0
#endif
#define FW_VERSION "1.7.0"

using namespace suflet;

// ------------------------------------------------------------------ state --

static const DisplayGeometry kGeom = DISPLAY_GEOMETRY;
static_assert(LCD_W == DISPLAY_GEOMETRY.w && LCD_H == DISPLAY_GEOMETRY.h, "board.h size vs geometry");

static Canvas* cv = nullptr;
static FrameComposer composer;
static float backlightNow = 0;
static bool displayOn = true;

static SensorQMI8658 imu;
static bool imuOk = false, imuGyro = false;
static SensorPCF85063 rtc;
static bool rtcOk = false;
#if TOUCH_CST9217
static TouchDrvCST92xx touchDrv;
#endif
static bool touchOk = false;

static Preferences prefs;
static Brain* brain = nullptr;
static Alarms alarms;
static Os os(&alarms);
static SoulMemory soulMem;  // SOUL Memory (docs/10): the `soulmem` partition, handed to every AI
static TouchGestures touch;
static MotionDetector motion;
static ClaudeLink claude;
static AlarmTone alarmTone;
static Inputs in;

static uint32_t lastSaveMs = 0, lastStatusMs = 0, lastNetMs = 0, lastPerfMs = 0;
static int64_t lastFrameUs = 0;
static float imuAcc = 0;
static bool rtcSynced = false;
static uint32_t bornDay = 0, naps = 0, lastNtpSync = 0;
static bool demo = false;
static float demoT = 0;
static int demoIdx = 0;
static uint32_t offSinceMs = 0;
static bool aiBusy = false;
static int lastBatPct = -1;

// perf (the debug overlay and the serial log)
static double accFrameMs = 0, accRenderMs = 0, accPushMs = 0, accBusyMs = 0;
static int accFrames = 0;
static int64_t perfWallStartUs = 0;

// ------------------------------------------------------------------- I2C ---

[[maybe_unused]] static bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

[[maybe_unused]] static bool i2cRead(uint8_t addr, uint8_t reg, uint8_t* buf, size_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)addr, (int)n) != (int)n) return false;
  for (size_t i = 0; i < n; ++i) buf[i] = Wire.read();
  return true;
}

#if HAS_PMU
// AXP2101 set-up, same values as the xiaozhi-esp32 board support (MIT).
static void pmuInit() {
  i2cWrite(PMU_ADDR, 0x22, 0b110);
  i2cWrite(PMU_ADDR, 0x27, 0x10);
  i2cWrite(PMU_ADDR, 0x80, 0x01);
  i2cWrite(PMU_ADDR, 0x90, 0x00);
  i2cWrite(PMU_ADDR, 0x91, 0x00);
  i2cWrite(PMU_ADDR, 0x82, (3300 - 1500) / 100);
  i2cWrite(PMU_ADDR, 0x92, (3300 - 500) / 100);
  i2cWrite(PMU_ADDR, 0x90, 0x01);
  i2cWrite(PMU_ADDR, 0x64, 0x02);
  i2cWrite(PMU_ADDR, 0x61, 0x02);
  i2cWrite(PMU_ADDR, 0x62, 0x08);
  i2cWrite(PMU_ADDR, 0x63, 0x01);
}
#endif

static void readBattery(int& pct, int& mv, bool& usb) {
  pct = -1;
  mv = 0;
  usb = false;
#if HAS_PMU
  uint8_t v = 0;
  if (i2cRead(PMU_ADDR, 0xA4, &v, 1) && v <= 100) pct = v;
  uint8_t st = 0;
  if (i2cRead(PMU_ADDR, 0x00, &st, 1)) usb = st & 0x20;
#elif BAT_ADC_PIN >= 0
  mv = analogReadMilliVolts(BAT_ADC_PIN) * 3;  // 200k/100k divider
#if BAT_USB_SENSE
  usb = mv > 4500;
#endif
  // The 2.8C divider sits on the cell behind the ETA6098 charger: while
  // charging this reads the charge voltage (reads high). No VBUS sense.
  if (!usb) pct = constrain(map(mv, 3300, 4150, 0, 100), 0, 100);
#endif
}

// --------------------------------------------------------------- display ---

#if !LCD_IS_RGB
// AMOLED (QSPI): our canvas in PSRAM, the changed rectangle pushed through Arduino_GFX.
static Arduino_DataBus* bus = nullptr;
static Arduino_OLED* panel = nullptr;
static uint16_t* canvasBuf = nullptr;
static uint16_t* pushBuf = nullptr;
static void displayInit() {
  bus = new Arduino_ESP32QSPI(LCD_CS, LCD_SCLK, LCD_D0, LCD_D1, LCD_D2, LCD_D3);
#if defined(SUFLET_PANEL_SH8601)
  panel = new Arduino_SH8601(bus, LCD_RST, 0, LCD_W, LCD_H);
#else
  panel = new Arduino_CO5300(bus, LCD_RST, 0, LCD_W, LCD_H, LCD_COL_OFFSET, 0, LCD_COL_OFFSET, 0);
#endif
  panel->begin(40000000);
  panel->fillScreen(0);
  panel->setBrightness(255);
  canvasBuf = (uint16_t*)heap_caps_calloc(LCD_W * LCD_H, 2, MALLOC_CAP_SPIRAM);
  pushBuf = (uint16_t*)heap_caps_malloc(LCD_W * LCD_H * 2, MALLOC_CAP_SPIRAM);
  cv = new Canvas(LCD_W, LCD_H, canvasBuf);
}
static void displayPresent(const RectList& list) {
  for (int i = 0; i < list.n; ++i) {  // each changed rectangle on its own (the panel keeps the rest)
    Rect r = list.r[i];
    r.x0 &= ~1;  // CO5300 wants even start/size
    r.y0 &= ~1;
    r.x1 = min((r.x1 + 1) & ~1, LCD_W);
    r.y1 = min((r.y1 + 1) & ~1, LCD_H);
    if (r.empty()) continue;
    for (int y = r.y0; y < r.y1; ++y) memcpy(pushBuf + (y - r.y0) * r.w(), canvasBuf + y * LCD_W + r.x0, r.w() * 2);
    panel->draw16bitRGBBitmap(r.x0, r.y0, pushBuf, r.w(), r.h());
  }
}
static void backlight(float v) { panel->setBrightness((uint8_t)(v * 255)); }
static void displayPower(bool on) {
  if (on) panel->displayOn();
  else panel->displayOff();
}
#else
static void displayInit() {
  lcd28::backlightInit();
  if (!lcd28::displayInit()) Serial.println("[lcd] display init FAILED");
  cv = new Canvas(LCD_W, LCD_H, lcd28::displayCanvas());
}
static void displayPresent(const RectList& r) { lcd28::displayPresent(r); }
static void backlight(float v) { lcd28::backlight(v); }
static void displayPower(bool on) { lcd28::displayPower(on); }
#endif

// ----------------------------------------------------------------- touch ---

static bool readTouch(float& x, float& y) {
  if (!touchOk) return false;
#if TOUCH_FT3168
  uint8_t b[5];
  if (!i2cRead(TOUCH_ADDR, 0x02, b, 5)) return false;
  if ((b[0] & 0x0F) == 0) return false;
  x = (float)(((b[1] & 0x0F) << 8) | b[2]);
  y = (float)(((b[3] & 0x0F) << 8) | b[4]);
#elif TOUCH_CST9217
  const TouchPoints& tp = touchDrv.getTouchPoints();
  if (tp.getPointCount() == 0) return false;
  x = tp.getPoint(0).x;
  y = tp.getPoint(0).y;
#elif TOUCH_GT911
  if (!lcd28::touchRead(x, y)) return false;
#endif
  if (TOUCH_MIRROR_X) x = LCD_W - 1 - x;
  if (TOUCH_MIRROR_Y) y = LCD_H - 1 - y;
  return true;
}

static void touchInit() {
#if TOUCH_FT3168
  touchOk = i2cWrite(TOUCH_ADDR, 0x00, 0x00);
#elif TOUCH_CST9217
  touchDrv.setPins(TOUCH_RST, TOUCH_INT);
  touchOk = touchDrv.begin(Wire, TOUCH_ADDR, I2C_SDA, I2C_SCL);
#elif TOUCH_GT911
  touchOk = lcd28::touchInit();
#endif
  Serial.printf("[touch] %s\n", touchOk ? "ok" : "NOT FOUND");
}

// ----------------------------------------------------------------- clock ---

static bool clockValid() { return rtcOk && rtc.getDateTime().getYear() >= 2025; }

static uint32_t localEpoch() {  // the RTC keeps local time
  if (!clockValid()) return 0;
  RTC_DateTime d = rtc.getDateTime();
  // days from civil (no mktime: the process TZ stays the POSIX TZ that NTP's
  // localtime_r needs; changing it here once made NTP set the RTC to UTC)
  const int Y = d.getYear(), M = d.getMonth(), D = d.getDay();
  const int y = Y - (M <= 2), era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (M + (M > 2 ? -3 : 9)) + 2) / 5 + D - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  const long days = era * 146097L + (long)doe - 719468L;
  return (uint32_t)(days * 86400L + d.getHour() * 3600L + d.getMinute() * 60L + d.getSecond());
}

void soulFlashWritten() {
#if defined(SUFLET_BOARD_LCD28)
  lcd28::displayResync();
#endif
}

static void setClockLocal(uint32_t localSecs) {
  if (!rtcOk) return;
  time_t tt = (time_t)localSecs;
  struct tm t;
  gmtime_r(&tt, &t);
  rtc.setDateTime(t.tm_year + 1900, t.tm_mon + 1, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec);
}

// The RTC over I2C once a second; millis() in between.
static uint32_t localNow() {
  static uint32_t base = 0, baseMs = 0;
  const uint32_t ms = millis();
  if (!base || ms - baseMs >= 1000) {
    base = localEpoch();
    baseMs = ms;
    return base;
  }
  return base + (ms - baseMs) / 1000;
}

static float hourNow() {
  const uint32_t n = localNow();
  if (!n) return claude.localHour();
  return (n % 86400) / 3600.0f;
}

static void updateCalendar() {
  const uint32_t now = localNow();
  if (!now) return;
  const uint32_t day = now / 86400;
  if (!bornDay) {
    bornDay = day;
    prefs.putUInt("born", bornDay);
  }
  time_t b = (time_t)bornDay * 86400, n = (time_t)now;
  struct tm tb, tn;
  gmtime_r(&b, &tb);
  gmtime_r(&n, &tn);
  brain->setDay((int32_t)day, day != bornDay && tb.tm_mon == tn.tm_mon && tb.tm_mday == tn.tm_mday);
}

// ----------------------------------------------------------- persistence ---

static void saveAlarms() {
  uint8_t buf[Alarms::kMaxBlob];
  const size_t n = alarms.serialize(buf, sizeof buf);
  if (n) prefs.putBytes("alarms", buf, n);
  soulFlashWritten();
}

static void saveSettings() {
  uint8_t buf[sizeof(OsSettings)];
  const size_t n = os.saveSettings(buf, sizeof buf);
  if (n) prefs.putBytes("os", buf, n);
  soulFlashWritten();
}

static void saveMemory() {
  prefs.putBytes("mem", &brain->memory(), sizeof(Memory));
  const uint32_t now = localNow();
  if (now) prefs.putUInt("seen", now);
  prefs.putUInt("naps", naps);
  soulFlashWritten();
}

static void loadAll() {
  uint8_t buf[Alarms::kMaxBlob];
  size_t n = prefs.getBytes("alarms", buf, sizeof buf);
  if (n && !alarms.deserialize(buf, n)) Serial.println("[alarms] stored data unreadable, ignored");
  uint8_t sb[sizeof(OsSettings)];
  n = prefs.getBytes("os", sb, sizeof sb);
  if (n && !os.loadSettings(sb, n)) Serial.println("[os] settings from an older version, defaults used");
  os.loadNotes(prefs.getString("notes", "").c_str());
  os.loadReminders(prefs.getString("rems", "").c_str());
  os.loadCloudRefs(prefs.getString("crefs", "").c_str());
  os.loadApps(prefs.getString("apps", "").c_str());  // SoulOS apps: the orbit's order, habits, clocks, bests
  Memory m;
  if (prefs.getBytes("mem", &m, sizeof m) == sizeof m) brain->memory() = m;
  bornDay = prefs.getUInt("born", 0);
  naps = prefs.getUInt("naps", 0);
  Serial.printf("[store] %d alarms, %d notes, %d reminders\n", alarms.count(), (int)os.notes().size(),
                (int)os.reminders().size());
}

// ---------------------------------------------------------------- serial ---

static void help() {
  Serial.println(
      "SOUL " FW_VERSION " serial commands:\n"
      "  F   perf overlay on/off      p   perf line now        i  IMU + eyes motion   t  time\n"
      "  M   eyes motion (level keeping, marble pupils, dizzy, nods) on/off\n"
      "  T<local epoch>  set clock    P   personality + design U  unpair Claude\n"
      "  W   Wi-Fi setup portal       w   stop the portal      B  re-run first boot\n"
      "  e<name>  play an expression (e.g. elaugh)              D  demo loop on/off\n"
      "  a<text>  ask the AI (like typing on the glass)         h  home    ?  help\n"
      "  V   offline voice commands (ESP-SR) status\n"
      "  Y   SOUL Memory: facts + flash writes   Yexport  the memory as JSON   Ysave  write it now\n"
      "  K   SOULKEY PUB: this SOUL's public device key (for the factory list; never the private key)\n"
      "  SOULKEY GEN / SOULKEY PUB   the factory station (tools/factory_enrol.py): make the device key once\n"
      "      (hardware RNG), print the public key as `SOULKEY PUB soul-<id> <b64u>`; there is no command for the private key");
}

static std::string readLine() {
  std::string s;
  const uint32_t t0 = millis();
  while (millis() - t0 < 200) {
    while (Serial.available()) {
      const int c = Serial.read();
      if (c == '\n' || c == '\r') return s;
      s += (char)c;
    }
    delay(1);
  }
  return s;
}

static void serialCommands() {
  while (Serial.available()) {
    const int c = Serial.read();
    switch (c) {
      case 'F': os.settings().debug = !os.settings().debug; break;
      case 'p': lastPerfMs = 0; break;
      case 'M':
        os.face().motionOn = !os.face().motionOn;
        Serial.printf("eyes motion %s\n", os.face().motionOn ? "on" : "off");
        break;
      case 'i': {  // BRINGUP.md "IMU axes": face up ~ (0,0,+1), standing ~ (0,+1,0), turning left = +gz
        float x = 0, y = 0, z = 0, gx = 0, gy = 0, gz = 0;
        if (imuOk) imu.getAccelerometer(x, y, z);
        if (imuGyro) imu.getGyroscope(gx, gy, gz);
        const eyes::EyeMotion& m = os.face().motion();
        const eyes::MotionPose& p = m.pose();
        Serial.printf("accel raw %.2f %.2f %.2f g  gyro %.1f %.1f %.1f dps%s  still %.1fs\n", x, y, z, gx, gy, gz,
                      imuGyro ? "" : " (NO GYRO)", motion.stillFor());
        Serial.printf("eyes: up %.2f %.2f %.2f  level %.0f deg  pupils %.2f %.2f  dizzy %.2f  bias %.3f %.3f %.3f%s%s%s%s\n",
                      m.gravX(), m.gravY(), m.gravZ(), p.roll * 57.29578f, p.px, p.py, p.dizzy, m.gyroBias(0),
                      m.gyroBias(1), m.gyroBias(2), m.onBack() ? "  on its back" : "", m.faceDown() ? "  face down" : "",
                      m.upsideDown() ? "  upside down" : "", m.calm() ? "  calm" : "");
        break;
      }
      case 't':
        Serial.printf("clock %s, hour %.2f, mode %s, view %s\n", clockValid() ? "ok" : "unset", hourNow(),
                      modeName(brain->mode()), viewName(os.view()));
        break;
      case 'T': {
        const uint32_t v = Serial.parseInt();
        if (v > 1700000000UL) {
          setClockLocal(v);
          updateCalendar();
          Serial.println("clock set");
        }
        break;
      }
      case 'P': {
        const Personality& p = brain->personality();
        const eyes::Design& d = eyes::kDesigns[os.face().design()];
        Serial.printf("'%s' - design #%03d %s (%s); shy %.2f, curious %.2f, sleepy %.2f\n", os.settings().name, d.num,
                      d.name, eyes::kRarityName[(int)d.rarity], p.shyness, p.curiosity, p.sleepiness);
        break;
      }
      case 'U': bleClearBonds(); break;
      case 'W': netStartPortal(); break;
      case 'w': netStopPortal(); break;
      case 'B': os.restartBoot(); break;
      case 'h': os.home(); break;
      case 'D': demo = !demo; break;
      case 'e': {
        const std::string name = readLine();
        const int e = eyes::exprByName(name.c_str());
        if (e >= 0) os.face().react(e, 2.4f);
        else Serial.println("unknown expression");
        break;
      }
      case 'a': {
        const std::string q = readLine();
        if (!q.empty()) os.ask(q);
        break;
      }
      case 'K': {
        const std::string pub = cloudPubKey();
        Serial.printf("SOULKEY PUB %s\n", pub.empty() ? "(none yet: made once Wi-Fi is up)" : pub.c_str());
        break;
      }
      case 'S': {  // the factory station (docs/07 §6.1): "SOULKEY GEN" / "SOULKEY PUB"
        const std::string rest = readLine();
        if (rest == "OULKEY GEN" || rest == "OULKEY PUB") {
          const bool gen = rest == "OULKEY GEN";
          const int made = gen ? cloudKeyGenerate() : 0;  // 1 made now, 0 already there, -1 failed
          const std::string pub = cloudPubKey();
          if (pub.empty()) Serial.printf("SOULKEY ERR %s\n", made < 0 ? "generate failed" : "no key yet: SOULKEY GEN");
          else Serial.printf("SOULKEY PUB %s %s%s\n", cloudDeviceId().c_str(), pub.c_str(), made > 0 ? " new" : "");
        } else {
          Serial.println("SOULKEY ERR unknown command");
        }
        break;
      }
      case 'V': Serial.printf("[voice] offline commands: %s\n", voiceSrStatus()); break;
      case 'Y': {  // SOUL Memory
        const std::string rest = readLine();
        if (rest == "export") {
          Serial.println(soulMem.exportJson().c_str());
        } else if (rest == "save") {
          memoryStoreSaveNow(soulMem);
        } else {
          Serial.printf("[memory] %u / %u facts, %s, %lu flash writes, backup %s\n", (unsigned)soulMem.size(),
                        (unsigned)SoulMemory::kMax, soulMem.dirty() ? "unsaved changes" : "saved",
                        (unsigned long)memoryStoreWrites(), soulMem.backup ? "on" : "off");
          for (size_t i = 0; i < soulMem.size() && i < 20; ++i)
            Serial.printf("  #%u %s: %s\n", soulMem.at(i).id, factKindName(soulMem.at(i).kind), soulMem.at(i).text.c_str());
        }
        break;
      }
      case '?': help(); break;
      default: break;
    }
  }
}

static void demoTick(float dt) {
  demoT += dt;
  if (demoT > 4.0f) {
    demoT = 0;
    os.face().react(demoIdx++ % eyes::X_Count, 2.2f);
  }
}

// ------------------------------------------------------------------ power ---

// Deep sleep only when it is useless to be awake: night, the screen off
// (face down or asleep long enough), no Claude session. Wakes on the side
// button, a touch (GT911 INT, if it idles high) or a timer a minute before
// the next alarm / at 07:00.
RTC_DATA_ATTR static uint8_t rtcPollWake = 0;  // the next timer wake is a §6.11 wake-poll, not the morning
static bool wakePolling = false;                // this boot is that wake-poll: screen off, poll, sleep again
static uint32_t wakePollStartMs = 0;

// The seconds until the next wake: an alarm (a minute early), 07:00, and for a paired SOUL at most 15 minutes
// (docs/07 §6.11: a paired SOUL is never unreachable for longer). `poll` says whether it is a wake-poll.
static uint32_t nextWake(bool& poll) {
  const float hour = hourNow();
  const uint32_t now = localNow();
  uint32_t wakeIn = 6 * 3600;
  uint32_t when = 0;
  if (now && alarms.next(now, when) >= 0 && when > now + 120) wakeIn = min<uint32_t>(wakeIn, when - now - 60);
  if (now) {
    const uint32_t seven = (now / 86400) * 86400 + 7 * 3600 + (hour >= 7 ? 86400 : 0);
    if (seven > now) wakeIn = min<uint32_t>(wakeIn, seven - now);
  }
  poll = cloudPaired() && wakeIn > 15 * 60;
  if (poll) wakeIn = 15 * 60;
  return wakeIn;
}

static void deepSleepNow(uint32_t wakeIn, bool poll) {
  Serial.printf("[power] deep sleep for %lu s (%s)\n", (unsigned long)wakeIn, poll ? "then a SOUL Cloud wake-poll" : "night, screen off");
  rtcPollWake = poll ? 1 : 0;
  if (!wakePolling) cloudSleep(time(nullptr) > 1735689600 ? (uint32_t)time(nullptr) + wakeIn : 0);
  saveMemory();
  if (soulMem.dirty()) memoryStoreSaveNow(soulMem);  // SOUL Memory: nothing learnt is lost to deep sleep
  saveAlarms();
  backlight(0);
  displayPower(false);
  esp_sleep_enable_timer_wakeup((uint64_t)wakeIn * 1000000ULL);
  uint64_t mask = 1ULL << BOOT_BUTTON;
#if TOUCH_INT >= 0
  if (digitalRead(TOUCH_INT) == HIGH) mask |= 1ULL << TOUCH_INT;  // only if the line idles high
#endif
  esp_sleep_enable_ext1_wakeup(mask, ESP_EXT1_WAKEUP_ANY_LOW);
  Serial.flush();
  esp_deep_sleep_start();
}

// §6.11: woken by the timer for a wake-poll. The screen stays off; when the poll is done (or 12 s passed) SOUL
// sleeps again, unless an alarm is due within 15 minutes or someone touched it.
static void wakePollTick(uint32_t nowMs, bool touched) {
  if (!wakePolling) return;
  if (touched) {  // a person: wake up properly
    wakePolling = false;
    cloudWakePollCancel();
    rtcPollWake = 0;
    return;
  }
  if (!cloudWakePollDone() && nowMs - wakePollStartMs < 12000) return;
  bool poll = false;
  const uint32_t wakeIn = nextWake(poll);
  if (wakeIn < 15 * 60 && !poll) {  // an alarm soon: stay up (the night rules put it back to sleep after)
    wakePolling = false;
    return;
  }
  deepSleepNow(wakeIn, poll);
}

static void maybeDeepSleep(uint32_t nowMs) {
  const float hour = hourNow();
  const bool night = hour >= 0 && (hour >= 23.0f || hour < 6.0f);
  if (!os.settings().nightOff || !night || brain->mode() != Mode::Off || bleConnected() || os.ringing()) {
    offSinceMs = 0;
    return;
  }
  if (!offSinceMs) offSinceMs = nowMs;
  if (nowMs - offSinceMs < 10u * 60u * 1000u) return;
  bool poll = false;
  const uint32_t wakeIn = nextWake(poll);
  deepSleepNow(wakeIn, poll);
}

// ------------------------------------------------------------ setup/loop ---

void setup() {
  Serial.begin(115200);
  delay(150);
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
#if HAS_PMU
  pmuInit();
#endif
#if defined(SUFLET_BOARD_LCD28)
  if (!lcd28::exioInit()) Serial.println("[exio] TCA9554 NOT FOUND (display/touch will fail)");
#endif
  displayInit();
  touchInit();
  audioInit();
  imuOk = imu.begin(Wire, IMU_ADDR, I2C_SDA, I2C_SCL);
  if (imuOk) {
    imu.configAccelerometer(SensorQMI8658::ACC_RANGE_4G, SensorQMI8658::ACC_ODR_125Hz, SensorQMI8658::LPF_MODE_0);
    imu.enableAccelerometer();
    // the gyro for the eyes' motion behaviours (level keeping, spin -> dizzy, nods)
    imuGyro = imu.configGyroscope(SensorQMI8658::GYR_RANGE_1024DPS, SensorQMI8658::GYR_ODR_112_1Hz,
                                  SensorQMI8658::LPF_MODE_3) &&
              imu.enableGyroscope();
  }
  rtcOk = rtc.begin(Wire, I2C_SDA, I2C_SCL);
  Serial.printf("[board] %s %dx%d  [imu] %s  [rtc] %s  psram %u KB free\n", BOARD_NAME, kGeom.w, kGeom.h,
                imuOk ? "ok" : "NOT FOUND", rtcOk ? "ok" : "NOT FOUND",
                (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024));

  // Birth: the chip's 48-bit eFuse MAC rolls the eye design (eyes.js rollFromChipId)
  // and seeds the personality. A given unit is always the same SOUL.
  uint8_t mac[6];
  esp_efuse_mac_get_default(mac);
  uint64_t seed = 0;
  for (int i = 0; i < 6; ++i) seed = (seed << 8) | mac[i];
  const eyes::RollResult roll = eyes::rollFromMac(mac);
  BirthInfo birth;
  birth.design = roll.design;
  char chip[24];
  snprintf(chip, sizeof chip, "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  birth.chip = chip;
  birth.seed = eyes::hashStr(eyes::kDesigns[roll.design].id) ^ 0x5eed;
  Serial.printf("[soul] chip %s: design #%03d %s (%s, 1 in %.0f)\n", chip, eyes::kDesigns[roll.design].num,
                eyes::kDesigns[roll.design].name, eyes::kRarityName[(int)roll.rarity], 1.0 / roll.odds);

  brain = new Brain(Personality::fromSeed(seed));
  brain->sleepAfterS = 300;      // always-on eyes: doze after 5 min of stillness by day
  brain->nightSleepAfterS = 90;  // sooner at night
  prefs.begin("suflet", false);
  loadAll();
  const uint32_t seen = prefs.getUInt("seen", 0), now = localEpoch();
  if (seen && now > seen) brain->setAbsence((now - seen) / 3600.0f);
  updateCalendar();
  brain->boot();

  memoryStoreBegin(soulMem);
  os.setMemory(&soulMem);
  os.setVoiceAvailable(SUFLET_VOICE && audioHasMic());
  os.begin(kGeom, birth);
  // offline voice commands (ESP-SR MultiNet, SUFLET_VOICE_SR builds): after the glass took its PSRAM
  if (voiceSrBegin()) {
    audioSetSrOwner(true);
    os.setVoiceAvailable(audioHasMic());
  }
  Serial.printf("[voice] offline commands: %s\n", voiceSrStatus());
  composer.setCanvas(cv);
  touch.setMode(TouchMode::Text);

  char name[32];
  snprintf(name, sizeof name, "Claude-Suflet-%02X%02X", mac[4], mac[5]);
  claude.setName(name);
  bleInit(name);
  char ap[16];
  snprintf(ap, sizeof ap, "SOUL-%02X%02X", mac[4], mac[5]);
  // docs/07 §2.1: device_id = "soul-" + the 12 lowercase hex digits of the MAC
  cloudBegin(mac, FW_VERSION, BOARD_HW);
  {
    char mdns[16];  // soul-xxxx.local: the last 4 hex digits of the device id
    snprintf(mdns, sizeof mdns, "soul-%02x%02x", mac[4], mac[5]);
    bridgeLanBegin(CloudLink::deviceId(mac), mdns);
  }
  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_TIMER && rtcPollWake) {  // §6.11 wake-poll
    wakePolling = true;
    wakePollStartMs = millis();
    bool poll = false;
    const uint32_t wakeIn = min<uint32_t>(nextWake(poll), 15 * 60);  // it was paired when it went to sleep
    cloudWakePoll(time(nullptr) > 1735689600 ? (uint32_t)time(nullptr) + wakeIn : 0);
    Serial.println("[power] wake-poll: screen off, one poll, back to sleep");
  }
  rtcPollWake = 0;
  netBegin(ap, CloudLink::deviceId(mac));
  netSetMode(os.aiMode());
  cloudSetPrefs(os.aiMode(), os.ro(), netTz());

  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_UNDEFINED && digitalRead(BOOT_BUTTON) == LOW) demo = true;
  help();
  lastSaveMs = lastStatusMs = millis();
  lastFrameUs = esp_timer_get_time();
  perfWallStartUs = lastFrameUs;
}

// offline voice commands: a command heard runs at once; with none, the recording goes to the cloud
// transcription (SUFLET_VOICE) as before, or SOUL says it did not catch that
static uint32_t voiceStopAtMs = 0;
static void voiceTick(uint32_t nowMs) {
  voiceSrTick(nowMs);
  if (voiceSrWakeHeard()) os.face().react(eyes::X_listening, 5.0f);
  int id;
  if (voiceSrTake(id)) {
    if (audioRecording()) audioRecord(false);
    voiceStopAtMs = 0;
    Serial.printf("[voice] heard: %s\n", voiceCmdName((VoiceCmd)id));
    os.voiceCommand(id);
    return;
  }
  if (voiceStopAtMs && nowMs - voiceStopAtMs > 1000) {
    voiceStopAtMs = 0;
    audioRecord(false);
    size_t n = 0;
    const int16_t* pcm = audioTake(n);
    if (n < 16000 / 3 || !netTranscribe(pcm, n, os.ro())) os.voiceText("", AiErr::None);
  }
  if (os.sleepRequested()) Serial.println("[voice] good night: the eyes doze");
}

// ---- SoulOS apps (os/APPS.md): their calls to SOUL Cloud, the Wi-Fi scan for "Use Wi-Fi", storage facts ----
static AppFetch wifiFetch;
static bool wifiScanning = false;
static uint32_t storageAt = 0;

static void appsRequest(const AppFetch& f) {
  if (f.kind == Fetch::WifiLocate) {  // the access points around (names never leave SOUL: maps.py drops them)
    if (!wifiScanning && WiFi.scanNetworks(true, false) == WIFI_SCAN_RUNNING) {
      wifiScanning = true;
      wifiFetch = f;
    }
    return;
  }
  cloudAppFetch(f);
}

static void appsTick(uint32_t nowMs) {
  Fetch k;
  int st;
  std::string body;
  while (cloudPollAppData(k, st, body)) {
    Serial.printf("[apps] %s -> %d (%u B)\n", fetchName(k), st, (unsigned)body.size());  // never the body: it may hold places
    os.appData(k, st, body);
  }
  if (wifiScanning) {
    const int n = WiFi.scanComplete();
    if (n >= 0 || n == WIFI_SCAN_FAILED) {
      wifiScanning = false;
      JsonDocument d;
      JsonArray aps = d["aps"].to<JsonArray>();
      for (int i = 0; i < n && i < 20; ++i) {
        JsonObject a = aps.add<JsonObject>();
        a["mac"] = WiFi.BSSIDstr(i);
        a["rssi"] = WiFi.RSSI(i);
        if (WiFi.SSID(i).endsWith("_nomap")) a["ssid"] = "_nomap";  // the opt-out is all the cloud needs to know
      }
      WiFi.scanDelete();
      serializeJson(d, wifiFetch.body);
      Serial.printf("[apps] wifi scan: %d access points\n", n < 0 ? 0 : n);
      cloudAppFetch(wifiFetch);
    }
  }
  if (nowMs - storageAt > 5000) {  // the Device app and the world clock
    storageAt = nowMs;
    StorageInfo si;
    si.fw = FW_VERSION;
    si.board = BOARD_HW;
    si.appKb = ESP.getSketchSize() / 1024;
    si.appMaxKb = (ESP.getSketchSize() + ESP.getFreeSketchSpace()) / 1024;
    si.flashKb = ESP.getFlashChipSize() / 1024;
    si.heapKb = ESP.getFreeHeap() / 1024;
    si.psramKb = ESP.getFreePsram() / 1024;
    si.psramTotalKb = ESP.getPsramSize() / 1024;
    nvs_stats_t ns;
    if (nvs_get_stats(nullptr, &ns) == ESP_OK) {
      si.nvsUsed = ns.used_entries;
      si.nvsTotal = ns.total_entries;
    }
    si.rssi = WiFi.isConnected() ? WiFi.RSSI() : 0;
    os.setStorage(si);
    os.setTz(netTz());
    os.setAudio(audioHasSpeaker(), audioHasMic());
  }
}

static void handleCmds() {
  OsCmd c;
  while (os.popCmd(c)) {
    switch (c) {
      case OsCmd::AppFetch: {
        AppFetch f;
        while (os.popAppFetch(f)) appsRequest(f);
        break;
      }
      case OsCmd::SaveApps:
        prefs.putString("apps", os.saveApps().c_str());
        soulFlashWritten();
        break;
      case OsCmd::SaveSettings:
        saveSettings();
        netSetMode(os.aiMode());
        cloudSetPrefs(os.aiMode(), os.ro(), netTz());
        break;
      case OsCmd::SaveAlarms: saveAlarms(); break;
      case OsCmd::SaveNotes:
        prefs.putString("notes", os.saveNotes().c_str());
        soulFlashWritten();
        break;
      case OsCmd::SaveReminders:
        prefs.putString("rems", os.saveReminders().c_str());
        soulFlashWritten();
        break;
      case OsCmd::SaveCloudRefs:
        prefs.putString("crefs", os.saveCloudRefs().c_str());
        soulFlashWritten();
        break;
      case OsCmd::BridgePair: bridgeLanNewCode(); break;
      case OsCmd::BridgeForget: bridgeLanForget(); break;
      case OsCmd::StartPortal: netStartPortal(); break;
      case OsCmd::StopPortal: netStopPortal(); break;
      case OsCmd::ForgetWifi: netForgetWifi(); break;
      case OsCmd::AddWifi:  // the phone's hotspot, typed on SOUL
        if (!netAddWifi(os.pendingWifi())) os.toast("Could not save that network", Rgb::hex(0xFFB347));
        os.clearPendingWifi();
        break;
      case OsCmd::WifiKick: netWifiKick(); break;
      case OsCmd::SetKey:
        netSetKey(os.aiMode(), os.pendingKey());
        os.clearPendingKey();
        break;
      case OsCmd::ForgetKeys: netForgetKeys(); break;
      case OsCmd::ClaudeApprove: claude.decide(true); break;
      case OsCmd::ClaudeDeny: claude.decide(false); break;
      case OsCmd::VoiceStart:
        audioRecord(true);
        voiceSrListen(true);
        voiceStopAtMs = 0;
        break;
      case OsCmd::VoiceStop: {
        if (voiceSrReady()) {  // the recogniser gets ~1 s more to land a command said at the very end
          voiceSrListen(false);
          voiceStopAtMs = millis() | 1;
          break;
        }
        audioRecord(false);
        size_t n = 0;
        const int16_t* pcm = audioTake(n);
        if (n < 16000 / 3 || !netTranscribe(pcm, n, os.ro())) os.voiceText("", AiErr::None);
        break;
      }
      case OsCmd::Restart: ESP.restart(); break;
      case OsCmd::FactoryReset:  // a user-only action: everything but the identity secret
        prefs.clear();
        netFactoryReset();
        cloudForget();
        ESP.restart();
        break;
      default: break;
    }
  }
}

void loop() {
  const int64_t frameStartUs = esp_timer_get_time();
  float dt = (frameStartUs - lastFrameUs) / 1e6f;
  lastFrameUs = frameStartUs;
  if (dt > 0.25f) dt = 0.25f;
  const uint32_t nowMs = millis();

  // touch -> SoulOS (raw stream; SoulOS recognises taps, holds, swipes, petting)
  float tx = 0, ty = 0;
  const bool down = readTouch(tx, ty);
  touch.update(down, tx, ty, dt);
  TouchEv te;
  while (touch.poll(te)) os.touch(te);

  // IMU at ~100 Hz: the Brain's gestures (MotionDetector) and the eyes' motion (SoulFace)
  imuAcc += dt;
  while (imuOk && imuAcc >= 0.01f) {
    imuAcc -= 0.01f;
    float ax, ay, az, X, Y, Z;
    if (imu.getAccelerometer(ax, ay, az)) {
      IMU_MAP(ax, ay, az, X, Y, Z);
      motion.update(X, Y, Z, 0.01f);
      eyes::ImuSample s;
      s.ax = X;
      s.ay = Y;
      s.az = Z;
      float gx, gy, gz;
      s.gyro = imuGyro && imu.getGyroscope(gx, gy, gz);
      if (s.gyro) {  // deg/s -> rad/s, same axes as the accelerometer
        constexpr float kRad = 0.017453293f;
        IMU_MAP(gx * kRad, gy * kRad, gz * kRad, s.gx, s.gy, s.gz);
      }
      os.imu(0.01f, s);
    }
  }
  if (imuAcc > 0.05f) imuAcc = 0;
  Ev e;
  while (motion.poll(e)) os.motion(e);

  // the side button: back (hold = home); it also silences a ringing alarm
  os.button(digitalRead(BOOT_BUTTON) == LOW);

  // Claude Desktop (Hardware Buddy over BLE)
  // drain everything waiting (a turn event can be 4 KB; at 2 fps face down a
  // 128-byte drain overflowed the BLE ring), in 256-byte bites
  for (int bites = 0; bites < 32 && bleAvailable(); ++bites) {
    uint8_t chunk[256];
    size_t n = 0;
    while (bleAvailable() && n < sizeof chunk) chunk[n++] = (uint8_t)bleRead();
    if (n) claude.feed(chunk, n);
  }
  claude.setTransportConnected(bleConnected());
  claude.tick(dt);
  if (claude.unpairRequested()) bleClearBonds();
  while (claude.poll(e)) brain->event(e);
  {
    ClaudeInfo ci;
    ci.linked = claude.alive();
    ci.busy = claude.busy();
    ci.prompt = claude.hasPrompt();
    ci.tool = claude.promptTool();
    ci.hint = claude.promptHint();
    ci.msg = claude.msg();
    ci.bleName = claude.deviceName();
    ci.passkey = blePasskey();
    ci.secure = bleSecure();
    ci.approvals = claude.approvals();
    ci.denials = claude.denials();
    os.setClaude(ci);
  }

  // the clock: Claude Desktop or NTP set the RTC (which keeps local time)
  if (claude.timeValid() && !rtcSynced) {
    setClockLocal((uint32_t)(claude.epochNow() + claude.tzOffset()));
    rtcSynced = true;
    updateCalendar();
  }
  if (nowMs - lastNetMs > 500) {
    lastNetMs = nowMs;
    NetInfo ni = netInfo();
    bridgeLanTick(os.aiMode() == AiMode::Bridge && !wakePolling, os.settings().name, os.ro(), netTz());
    bridgeLanFill(ni);  // SOUL Bridge on this Wi-Fi; SOUL Cloud's bridge (any network) fills over it
    cloudFill(ni);
    os.setNet(ni);
    cloudSetStatus(lastBatPct, brain->mode() != Mode::Off);
    const uint32_t ntp = netLocalTime();
    if (ntp && (!lastNtpSync || nowMs - lastNtpSync > 3600000u)) {
      const uint32_t rtcNow = localEpoch();
      if (!rtcNow || (rtcNow > ntp ? rtcNow - ntp : ntp - rtcNow) > 2) setClockLocal(ntp);
      lastNtpSync = nowMs;
      updateCalendar();
    }
    std::string nm;
    if (netPollPortalSettings(nm)) {
      snprintf(os.settings().name, sizeof os.settings().name, "%s", nm.c_str());
      saveSettings();
    }
  }
  const uint32_t local = localNow();
  os.setClock(local);

  // the AI: questions go to the network task, answers come back here
  // (SOUL Cloud: over its socket when it is up, else HTTPS to the relay)
  AiJob job;
  if (!aiBusy && os.popAiJob(job)) {
    const int timerMin = os.timerLeft() >= 0 ? (os.timerLeft() + 59) / 60 : -1;
    if (os.aiMode() == AiMode::Bridge) {  // the owner's computer: on this Wi-Fi first, else through SOUL Cloud
      aiBusy = bridgeLanOnline() ? bridgeLanAsk(job, os.ro(), local)
                                 : cloudReady() && cloudAsk(job, os.ro(), timerMin, true);
      if (!aiBusy) {
        AiOutcome off;
        off.err = AiErr::BridgeOffline;
        os.aiResult(off);
      }
    } else {
      aiBusy = (os.aiMode() == AiMode::Cloud && cloudReady()) ? cloudAsk(job, os.ro(), timerMin) : netAsk(job);
    }
  }
  AiOutcome out;
  if (netPollAnswer(out) || cloudPollAnswer(out) || bridgeLanPollAnswer(out)) {
    aiBusy = false;
    os.aiResult(out);
  }
  // SOUL Cloud: what your Claude (or the account page) put on SOUL, applied
  // once and acked; what was made here goes up
  CloudPush push;
  while (cloudPollPush(push)) {
    std::string perr;
    const bool ok = os.cloudPush(push, perr);
    cloudAck(push.seq, ok, ok ? nullptr : perr.c_str());
  }
  CloudOut co;
  while (os.popCloudOut(co)) cloudSend(co, local, 0);
  appsTick(nowMs);
  CloudConfig cc;
  if (cloudPollConfig(cc)) {
    os.cloudConfig(cc.hasBrain ? cc.brain : "", cc.hasLang ? cc.lang : "", cc.hasName ? cc.name : "");
    if (cc.hasModels) netSetModels(cc.modelClaude, cc.modelOpenai);
  }
  std::string ctz;
  if (cloudPollTz(ctz)) netSetTz(ctz);  // the cloud's time zone always wins (§6.7)
  uint32_t cloudEpoch = 0;
  if (cloudPollTime(cloudEpoch) && time(nullptr) < 1735689600 && cloudEpoch > 1735689600) {
    timeval tv = {(time_t)cloudEpoch, 0};  // no NTP yet: SOUL Cloud's clock (the NTP block sets the RTC)
    settimeofday(&tv, nullptr);
  }
  std::string heard;
  AiErr verr;
  if (netPollVoice(heard, verr)) os.voiceText(heard, verr);
  voiceTick(nowMs);

  // alarms (SoulOS shows the ringing screen; the tone plays here)
  if (local) {
    const int due = alarms.poll(local);
    if (due >= 0) {
      Serial.printf("[alarm] %02u:%02u '%s'\n", alarms.at(due).hour, alarms.at(due).minute, alarms.at(due).label);
      os.alarmDue(due);
      saveAlarms();
    }
  }
  if (os.ringing() && !alarmTone.ringing()) alarmTone.start();
  if (os.silenceRequested() || (!os.ringing() && alarmTone.ringing())) alarmTone.stop();

  // the Brain and SoulOS
  in.tiltX = motion.tiltX();
  in.tiltY = motion.tiltY();
  in.stillFor = touch.isDown() ? 0.0f : motion.stillFor();
  in.faceDown = motion.faceDown();
  in.knockX = motion.knockX();
  in.knockY = motion.knockY();
  in.hour = hourNow();
  if (audioHasMic()) in.audioLevel = audioLevel();
  if (demo) demoTick(dt);
  os.update(dt, *brain);
  const Mode before = brain->mode();
  brain->update(dt, in);
  if (before != Mode::Asleep && brain->mode() == Mode::Asleep) ++naps;
  Cue c;
  while (brain->popCue(c)) {
    if (c == Cue::ClaudeApprove) claude.decide(true);
    if (c == Cue::ClaudeDeny) claude.decide(false);
  }
  std::string line;
  while (claude.popOutgoing(line)) bleWrite((const uint8_t*)line.data(), line.size());
  handleCmds();
  // SOUL Memory: batched writes, never while listening, thinking or ringing
  memoryStoreTick(soulMem, nowMs, os.thinking() || os.ringing() || audioRecording());

  if (nowMs - lastStatusMs > 2000) {
    lastStatusMs = nowMs;
    int pct, mv;
    bool usb;
    readBattery(pct, mv, usb);
    PowerInfo pw;
    pw.batPct = pct;
    pw.charging = usb;
    lastBatPct = pct;
    os.setPower(pw);
    claude.status.batPct = pct;
    claude.status.batMv = mv;
    claude.status.usb = usb;
    claude.status.secure = bleSecure();
    claude.status.uptimeS = nowMs / 1000;
    claude.status.heap = ESP.getFreeHeap();
    claude.status.naps = naps;
  }

  // backlight: eases toward what SoulOS wants (~0.25 s up, ~0.8 s down)
  const float target = wakePolling ? 0.0f : os.backlight(in.hour, *brain);
  const float rate = target > backlightNow ? 4.0f : 1.2f;
  const float d = target - backlightNow;
  backlightNow += fabsf(d) < rate * dt ? d : (d > 0 ? rate * dt : -rate * dt);
  backlight(backlightNow);

  // the frame: only what changed is drawn and pushed
  const bool wantOn = !wakePolling && (brain->mode() != Mode::Off || os.ringing());
  if (wantOn != displayOn) {
    displayOn = wantOn;
    displayPower(wantOn);
    if (wantOn) composer.invalidateAll();
  }
  const int64_t r0 = esp_timer_get_time();
  int64_t r1 = r0, r2 = r0;
  if (displayOn) {
    composer.compose(os);
    r1 = esp_timer_get_time();
    displayPresent(composer.changedList());
    r2 = esp_timer_get_time();
  }
  audioSetFocus(os.soundOn() && !os.ringing() ? &os.sound() : nullptr);  // Music: focus sounds
  audioTick(alarmTone.update(dt));
  serialCommands();

  if (nowMs - lastSaveMs > 60000) {
    lastSaveMs = nowMs;
    saveMemory();
    updateCalendar();
  }
  wakePollTick(nowMs, down || digitalRead(BOOT_BUTTON) == LOW);
  if (!wakePolling) maybeDeepSleep(nowMs);

  // perf: frame time, CPU share of this loop, memory
  const int64_t endUs = esp_timer_get_time();
  accFrameMs += (endUs - frameStartUs) / 1000.0;
  accRenderMs += (r1 - r0) / 1000.0;
  accPushMs += (r2 - r1) / 1000.0;
  accBusyMs += (endUs - frameStartUs) / 1000.0;
  ++accFrames;
  if (nowMs - lastPerfMs > 5000) {
    const double wallMs = (endUs - perfWallStartUs) / 1000.0;
    os.perf.fps = (float)(accFrames * 1000.0 / wallMs);
    os.perf.frameMs = (float)(accFrameMs / accFrames);
    os.perf.renderMs = (float)(accRenderMs / accFrames);
    os.perf.pushMs = (float)(accPushMs / accFrames);
    os.perf.cpu = (float)(accBusyMs / wallMs);
    os.perf.heapKb = (uint32_t)(heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024);
    os.perf.psramKb = (uint32_t)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024);
    Serial.printf("[perf] %.1f fps (asked %.0f), frame %.1f ms (draw %.1f, push %.1f), loop cpu %.0f%%, view %s, "
                  "mode %s, heap %u K (min %u K), psram %u K\n",
                  os.perf.fps, os.fpsHint(*brain), os.perf.frameMs, os.perf.renderMs, os.perf.pushMs, os.perf.cpu * 100,
                  viewName(os.view()), modeName(brain->mode()), (unsigned)os.perf.heapKb,
                  (unsigned)(heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL) / 1024), (unsigned)os.perf.psramKb);
    lastPerfMs = nowMs;
    accFrameMs = accRenderMs = accPushMs = accBusyMs = 0;
    accFrames = 0;
    perfWallStartUs = endUs;
  }

  // pacing: 30 fps when something moves, 24 calm, 10-15 dozing, 4 with the screen off.
  // The idle task runs WFI between frames (the CPU sleeps; the panel keeps scanning).
  float fps = os.fpsHint(*brain);
  // adaptive cap: if frames cost more than expected, lower the rate instead of
  // running flat out (the loop stays under ~60 % of a core: cool and frugal)
  static float avgMs = 8;
  avgMs += ((endUs - frameStartUs) / 1000.0f - avgMs) * 0.05f;
  const float capFps = 1000.0f / (avgMs * 1.6f);
  if (fps > capFps) fps = capFps < 12 ? 12 : capFps;
  if (!displayOn) fps = 4;
  const int64_t frameUs = (int64_t)(1e6f / (fps < 1 ? 1 : fps));
  const int64_t spent = esp_timer_get_time() - frameStartUs;
  if (spent < frameUs) vTaskDelay(pdMS_TO_TICKS((frameUs - spent) / 1000 ? (frameUs - spent) / 1000 : 1));
}
