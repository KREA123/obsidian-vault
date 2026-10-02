// SOUL firmware: SoulOS on the Waveshare round boards — the 2.8" IPS
// LCD-2.8C ("SOUL M", the main target) and the AMOLED-1.43 / 1.75 (size S).
//
// Two tasks:
//   core 1  this loop: touch, IMU, the Claude Desktop link (BLE), the Brain,
//           SoulOS and the frame (only what changed is drawn and pushed)
//   core 0  the network task (src/net.cpp): Wi-Fi, the setup portal, NTP and
//           the AI calls (HTTPS), plus the panel's bounce-buffer interrupt
// The loop never waits on the network: questions are posted and answers polled.
//
// Serial (115200): '?' lists the commands (bring-up without a finger).
#include <Arduino.h>
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
#define FW_VERSION "1.0.0"

using namespace suflet;

// ------------------------------------------------------------------ state --

static const DisplayGeometry kGeom = DISPLAY_GEOMETRY;
static_assert(LCD_W == DISPLAY_GEOMETRY.w && LCD_H == DISPLAY_GEOMETRY.h, "board.h size vs geometry");

static Canvas* cv = nullptr;
static FrameComposer composer;
static float backlightNow = 0;
static bool displayOn = true;

static SensorQMI8658 imu;
static bool imuOk = false;
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
static void displayPresent(Rect r) {
  r.x0 &= ~1;  // CO5300 wants even start/size
  r.y0 &= ~1;
  r.x1 = min((r.x1 + 1) & ~1, LCD_W);
  r.y1 = min((r.y1 + 1) & ~1, LCD_H);
  if (r.empty()) return;
  for (int y = r.y0; y < r.y1; ++y) memcpy(pushBuf + (y - r.y0) * r.w(), canvasBuf + y * LCD_W + r.x0, r.w() * 2);
  panel->draw16bitRGBBitmap(r.x0, r.y0, pushBuf, r.w(), r.h());
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
static void displayPresent(const Rect& r) { lcd28::displayPresent(r); }
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
  struct tm t = {};
  t.tm_year = d.getYear() - 1900;
  t.tm_mon = d.getMonth() - 1;
  t.tm_mday = d.getDay();
  t.tm_hour = d.getHour();
  t.tm_min = d.getMinute();
  t.tm_sec = d.getSecond();
  setenv("TZ", "UTC0", 1);  // mktime on a UTC process = our "local seconds"
  tzset();
  const uint32_t v = (uint32_t)mktime(&t);
  return v;
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
}

static void saveSettings() {
  uint8_t buf[sizeof(OsSettings)];
  const size_t n = os.saveSettings(buf, sizeof buf);
  if (n) prefs.putBytes("os", buf, n);
}

static void saveMemory() {
  prefs.putBytes("mem", &brain->memory(), sizeof(Memory));
  const uint32_t now = localNow();
  if (now) prefs.putUInt("seen", now);
  prefs.putUInt("naps", naps);
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
      "  F   perf overlay on/off      p   perf line now        i  IMU raw   t  time\n"
      "  T<local epoch>  set clock    P   personality + design U  unpair Claude\n"
      "  W   Wi-Fi setup portal       w   stop the portal      B  re-run first boot\n"
      "  e<name>  play an expression (e.g. elaugh)              D  demo loop on/off\n"
      "  a<text>  ask the AI (like typing on the glass)         h  home    ?  help");
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
      case 'i': {
        float x = 0, y = 0, z = 0;
        if (imuOk) imu.getAccelerometer(x, y, z);
        Serial.printf("accel raw %.2f %.2f %.2f  still %.1fs\n", x, y, z, motion.stillFor());
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
static void maybeDeepSleep(uint32_t nowMs) {
  const float hour = hourNow();
  const bool night = hour >= 0 && (hour >= 23.0f || hour < 6.0f);
  if (!os.settings().nightOff || !night || brain->mode() != Mode::Off || bleConnected() || os.ringing()) {
    offSinceMs = 0;
    return;
  }
  if (!offSinceMs) offSinceMs = nowMs;
  if (nowMs - offSinceMs < 10u * 60u * 1000u) return;
  const uint32_t now = localNow();
  uint32_t wakeIn = 6 * 3600;
  uint32_t when = 0;
  if (now && alarms.next(now, when) >= 0 && when > now + 120) wakeIn = min<uint32_t>(wakeIn, when - now - 60);
  if (now) {
    const uint32_t seven = (now / 86400) * 86400 + 7 * 3600 + (hour >= 7 ? 86400 : 0);
    if (seven > now) wakeIn = min<uint32_t>(wakeIn, seven - now);
  }
  Serial.printf("[power] deep sleep for %lu s (night, screen off)\n", (unsigned long)wakeIn);
  saveMemory();
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

  os.setVoiceAvailable(SUFLET_VOICE && audioHasMic());
  os.begin(kGeom, birth);
  composer.setCanvas(cv);
  touch.setMode(TouchMode::Text);

  char name[32];
  snprintf(name, sizeof name, "Claude-Suflet-%02X%02X", mac[4], mac[5]);
  claude.setName(name);
  bleInit(name);
  char ap[16];
  snprintf(ap, sizeof ap, "SOUL-%02X%02X", mac[4], mac[5]);
  char devId[16];
  snprintf(devId, sizeof devId, "SOUL-%02X%02X%02X", mac[3], mac[4], mac[5]);
  netBegin(ap, devId);
  netSetMode(os.aiMode());

  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_UNDEFINED && digitalRead(BOOT_BUTTON) == LOW) demo = true;
  help();
  lastSaveMs = lastStatusMs = millis();
  lastFrameUs = esp_timer_get_time();
  perfWallStartUs = lastFrameUs;
}

static void handleCmds() {
  OsCmd c;
  while (os.popCmd(c)) {
    switch (c) {
      case OsCmd::SaveSettings:
        saveSettings();
        netSetMode(os.aiMode());
        break;
      case OsCmd::SaveAlarms: saveAlarms(); break;
      case OsCmd::SaveNotes: prefs.putString("notes", os.saveNotes().c_str()); break;
      case OsCmd::SaveReminders: prefs.putString("rems", os.saveReminders().c_str()); break;
      case OsCmd::StartPortal: netStartPortal(); break;
      case OsCmd::StopPortal: netStopPortal(); break;
      case OsCmd::ForgetWifi: netForgetWifi(); break;
      case OsCmd::SetKey:
        netSetKey(os.aiMode(), os.pendingKey());
        os.clearPendingKey();
        break;
      case OsCmd::ForgetKeys: netForgetKeys(); break;
      case OsCmd::ClaudeApprove: claude.decide(true); break;
      case OsCmd::ClaudeDeny: claude.decide(false); break;
      case OsCmd::VoiceStart: audioRecord(true); break;
      case OsCmd::VoiceStop: {
        audioRecord(false);
        size_t n = 0;
        const int16_t* pcm = audioTake(n);
        if (n < 16000 / 3 || !netTranscribe(pcm, n, os.ro())) os.voiceText("", AiErr::None);
        break;
      }
      case OsCmd::Restart: ESP.restart(); break;
      case OsCmd::FactoryReset:
        prefs.clear();
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

  // IMU at ~100 Hz
  imuAcc += dt;
  while (imuOk && imuAcc >= 0.01f) {
    imuAcc -= 0.01f;
    float ax, ay, az, X, Y, Z;
    if (imu.getAccelerometer(ax, ay, az)) {
      IMU_MAP(ax, ay, az, X, Y, Z);
      motion.update(X, Y, Z, 0.01f);
    }
  }
  if (imuAcc > 0.05f) imuAcc = 0;
  Ev e;
  while (motion.poll(e)) os.motion(e);

  // the side button: back (hold = home); it also silences a ringing alarm
  os.button(digitalRead(BOOT_BUTTON) == LOW);

  // Claude Desktop (Hardware Buddy over BLE)
  uint8_t chunk[128];
  size_t n = 0;
  while (bleAvailable() && n < sizeof chunk) chunk[n++] = (uint8_t)bleRead();
  if (n) claude.feed(chunk, n);
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
    os.setNet(netInfo());
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
  AiJob job;
  if (!aiBusy && os.popAiJob(job)) aiBusy = netAsk(job);
  AiOutcome out;
  if (netPollAnswer(out)) {
    aiBusy = false;
    os.aiResult(out);
  }
  std::string heard;
  AiErr verr;
  if (netPollVoice(heard, verr)) os.voiceText(heard, verr);

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

  if (nowMs - lastStatusMs > 2000) {
    lastStatusMs = nowMs;
    int pct, mv;
    bool usb;
    readBattery(pct, mv, usb);
    PowerInfo pw;
    pw.batPct = pct;
    pw.charging = usb;
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
  const float target = os.backlight(in.hour, *brain);
  const float rate = target > backlightNow ? 4.0f : 1.2f;
  const float d = target - backlightNow;
  backlightNow += fabsf(d) < rate * dt ? d : (d > 0 ? rate * dt : -rate * dt);
  backlight(backlightNow);

  // the frame: only what changed is drawn and pushed
  const bool wantOn = brain->mode() != Mode::Off || os.ringing();
  if (wantOn != displayOn) {
    displayOn = wantOn;
    displayPower(wantOn);
    if (wantOn) composer.invalidateAll();
  }
  const int64_t r0 = esp_timer_get_time();
  int64_t r1 = r0, r2 = r0;
  if (displayOn) {
    const Rect changed = composer.compose(os);
    r1 = esp_timer_get_time();
    displayPresent(changed);
    r2 = esp_timer_get_time();
  }
  audioTick(alarmTone.update(dt));
  serialCommands();

  if (nowMs - lastSaveMs > 60000) {
    lastSaveMs = nowMs;
    saveMemory();
    updateCalendar();
  }
  maybeDeepSleep(nowMs);

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
