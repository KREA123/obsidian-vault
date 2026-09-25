// Micul Șmecher — firmware v0 for the Waveshare round AMOLED dev boards.
//
// Hardware in, Events out: touch + IMU + clock + the Claude desktop link
// feed the portable "soul" (lib/Suflet); the Brain returns one Face per
// frame, which we draw into a PSRAM framebuffer and push to the panel
// (only the part that changed).
//
// SoulOS v1 hook: a small Shell sees every touch first. A long press on the
// face opens a note field (the round keyboard); serial 'A' opens the Rim-Dial
// time picker to set an alarm; BOOT (GPIO0) goes back. Alarms are kept in
// NVS and ring through the Brain (no speaker/haptic on the dev boards yet).
//
// Serial (115200) commands, for filming and debugging — type '?' for help.
#include <Arduino.h>
#include <Arduino_GFX_Library.h>
#include <Preferences.h>
#include <SensorPCF85063.hpp>
#include <SensorQMI8658.hpp>
#include <Wire.h>
#include <esp_mac.h>

#include "Alarms.h"
#include "Brain.h"
#include "ClaudeLink.h"
#include "Face.h"
#include "Gestures.h"
#include "Personality.h"
#include "Shell.h"
#include "ble_link.h"
#include "board.h"

#if TOUCH_CST9217
#include <touch/TouchDrvCST92xx.h>
#endif

using namespace suflet;

// ------------------------------------------------------------------ state --

static Arduino_DataBus* bus = nullptr;
static Arduino_OLED* panel = nullptr;
static Arduino_Canvas* gcanvas = nullptr;  // owns the framebuffer, draws text
static Canvas* cv = nullptr;               // our SDF renderer on the same buffer
static uint16_t* pushBuf = nullptr;
static Rect prevDirty;
static bool displayIsOff = false;
static uint8_t brightness = 0;

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
static TouchGestures touch;
static MotionDetector motion;
static ClaudeLink claude;
static Inputs in;
static Alarms alarms;
static Shell shell(&alarms);
static int shownAlarm = -1;
static bool bootWasDown = true;  // wait for the first release after power-on
static uint32_t bootDownMs = 0;

static uint32_t lastMs = 0, lastSaveMs = 0, lastStatusMs = 0;
static float imuAcc = 0;
static bool demo = false;
static float demoT = 0;
static int demoIdx = 0;
static bool rtcSynced = false;
static uint32_t bornDay = 0;  // days since epoch of the first boot with a valid clock
static uint32_t naps = 0;

// ------------------------------------------------------------------- I2C ---

static bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

static bool i2cRead(uint8_t addr, uint8_t reg, uint8_t* buf, size_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)addr, (int)n) != (int)n) return false;
  for (size_t i = 0; i < n; ++i) buf[i] = Wire.read();
  return true;
}

#if HAS_PMU
// AXP2101 set-up, same register values as the xiaozhi-esp32 board support
// for this board (MIT): 3.3 V rails, 4 s hold to power off, 400 mA charge.
static void pmuInit() {
  i2cWrite(PMU_ADDR, 0x22, 0b110);                // PWRON > OFFLEVEL as power-off source
  i2cWrite(PMU_ADDR, 0x27, 0x10);                 // hold 4 s to power off
  i2cWrite(PMU_ADDR, 0x80, 0x01);                 // DCDC1 on
  i2cWrite(PMU_ADDR, 0x90, 0x00);                 // LDOs off...
  i2cWrite(PMU_ADDR, 0x91, 0x00);
  i2cWrite(PMU_ADDR, 0x82, (3300 - 1500) / 100);  // DCDC1 3.3 V
  i2cWrite(PMU_ADDR, 0x92, (3300 - 500) / 100);   // ALDO1 3.3 V
  i2cWrite(PMU_ADDR, 0x90, 0x01);                 // ...then ALDO1 on
  i2cWrite(PMU_ADDR, 0x64, 0x02);                 // charge to 4.1 V (gentler on the cell)
  i2cWrite(PMU_ADDR, 0x61, 0x02);                 // precharge 50 mA
  i2cWrite(PMU_ADDR, 0x62, 0x08);                 // charge 200 mA (safe for 400-500 mAh)
  i2cWrite(PMU_ADDR, 0x63, 0x01);                 // termination 25 mA
}
#endif

static void readBattery(int& pct, int& mv, bool& usb) {
  pct = -1;
  mv = 0;
  usb = false;
#if HAS_PMU
  uint8_t v = 0;
  if (i2cRead(PMU_ADDR, 0xA4, &v, 1) && v <= 100) pct = v;  // fuel gauge %
  uint8_t st = 0;
  if (i2cRead(PMU_ADDR, 0x00, &st, 1)) usb = st & 0x20;     // VBUS good
#elif BAT_ADC_PIN >= 0
  mv = analogReadMilliVolts(BAT_ADC_PIN) * 3;  // 200k/100k divider
  usb = mv > 4500;                             // measures VCC: ~4.7 V on USB
  if (!usb) pct = constrain(map(mv, 3300, 4150, 0, 100), 0, 100);
#endif
}

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
#endif
  if (TOUCH_MIRROR_X) x = LCD_W - 1 - x;
  if (TOUCH_MIRROR_Y) y = LCD_H - 1 - y;
  return true;
}

static void touchInit() {
#if TOUCH_FT3168
  touchOk = i2cWrite(TOUCH_ADDR, 0x00, 0x00);  // normal operating mode
#elif TOUCH_CST9217
  touchDrv.setPins(TOUCH_RST, TOUCH_INT);
  touchOk = touchDrv.begin(Wire, TOUCH_ADDR, I2C_SDA, I2C_SCL);
#endif
  Serial.printf("[touch] %s\n", touchOk ? "ok" : "NOT FOUND");
}

// --------------------------------------------------------------- display ---

static void displayInit() {
  bus = new Arduino_ESP32QSPI(LCD_CS, LCD_SCLK, LCD_D0, LCD_D1, LCD_D2, LCD_D3);
#if defined(SUFLET_PANEL_SH8601)
  panel = new Arduino_SH8601(bus, LCD_RST, 0, LCD_W, LCD_H);
#else
  panel = new Arduino_CO5300(bus, LCD_RST, 0, LCD_W, LCD_H, LCD_COL_OFFSET, 0, LCD_COL_OFFSET, 0);
#endif
  gcanvas = new Arduino_Canvas(LCD_W, LCD_H, panel);
  if (!gcanvas->begin(40000000)) Serial.println("[lcd] begin FAILED");
  cv = new Canvas(LCD_W, LCD_H, gcanvas->getFramebuffer());
  pushBuf = (uint16_t*)ps_malloc(LCD_W * LCD_H * sizeof(uint16_t));
  cv->fill(pal::kBlack);
  panel->fillScreen(0);
  brightness = 255;
  panel->setBrightness(brightness);
  prevDirty = Rect{};
}

// Rotate a point of the logical picture into panel coordinates.
static inline void rot(int x, int y, int& px, int& py) {
#if SUFLET_ROTATION == 90
  px = LCD_W - 1 - y;
  py = x;
#elif SUFLET_ROTATION == 180
  px = LCD_W - 1 - x;
  py = LCD_H - 1 - y;
#elif SUFLET_ROTATION == 270
  px = y;
  py = LCD_H - 1 - x;
#else
  px = x;
  py = y;
#endif
}

// Push only the changed rectangle (CO5300 wants even start/size).
static void pushRect(Rect r) {
  r.x0 &= ~1;
  r.y0 &= ~1;
  r.x1 = (r.x1 + 1) & ~1;
  r.y1 = (r.y1 + 1) & ~1;
  if (r.x1 > LCD_W) r.x1 = LCD_W;
  if (r.y1 > LCD_H) r.y1 = LCD_H;
  if (r.empty()) return;
  const uint16_t* fb = cv->data();
  int ax, ay, bx, by;
  rot(r.x0, r.y0, ax, ay);
  rot(r.x1 - 1, r.y1 - 1, bx, by);
  const int px0 = min(ax, bx), py0 = min(ay, by);
  const int pw = abs(bx - ax) + 1, ph = abs(by - ay) + 1;
  for (int y = r.y0; y < r.y1; ++y) {
    for (int x = r.x0; x < r.x1; ++x) {
      int px, py;
      rot(x, y, px, py);
      pushBuf[(py - py0) * pw + (px - px0)] = fb[y * LCD_W + x];
    }
  }
  panel->draw16bitRGBBitmap(px0, py0, pushBuf, pw, ph);
}

static void drawCentered(const char* s, int y, int size, uint16_t color) {
  const int w = (int)strlen(s) * 6 * size;
  gcanvas->setTextSize(size);
  gcanvas->setTextColor(color);
  gcanvas->setCursor((LCD_W - w) / 2, y);
  gcanvas->print(s);
  cv->markDirty(Rect{(LCD_W - w) / 2 - 2, y - 2, (LCD_W + w) / 2 + 2, y + 8 * size + 2});
}

static void renderFrame() {
  if (brain->displayOff()) {
    if (!displayIsOff) {
      panel->displayOff();
      displayIsOff = true;
    }
    return;
  }
  if (displayIsOff) {
    panel->displayOn();
    displayIsOff = false;
    prevDirty = Rect{0, 0, LCD_W, LCD_H};
  }
  const uint8_t want = brain->mode() == Mode::Asleep ? 110 : 255;
  if (want != brightness) {
    brightness = want;
    panel->setBrightness(brightness);
  }
  // prevDirty is what the face and text drew last frame: clear it. The
  // Shell's screen is a persistent layer: it redraws only when it changed or
  // when that clear wiped part of it, and before the face (eyes on top).
  cv->fillRect(prevDirty, pal::kBlack);
  cv->resetDirty();
  shell.render(*cv, prevDirty);
  const Rect uiDirty = cv->dirty();
  cv->resetDirty();
  Face face = brain->face();
  shell.adjustFace(face);
  renderFace(*cv, face, shell.faceLayout());

  // text overlays: BLE passkey while pairing, the Claude request while pending
  const uint32_t pk = blePasskey();
  if (shell.screen() != Screen::Face) {
    // the keyboard / time picker own the screen: no text overlays
  } else if (pk) {
    char buf[8];
    snprintf(buf, sizeof buf, "%06lu", (unsigned long)pk);
    drawCentered(buf, 60, 5, RGB565(255, 240, 200));
  } else if (brain->claudePrompt()) {
    char tool[24], hint[34];
    snprintf(tool, sizeof tool, "%.20s?", claude.promptTool().c_str());
    snprintf(hint, sizeof hint, "%.30s", claude.promptHint().c_str());
    drawCentered(tool, 70, 3, RGB565(255, 196, 110));
    drawCentered(hint, 356, 2, RGB565(200, 205, 215));
    drawCentered("hold = yes   2x tap = no", 392, 1, RGB565(140, 145, 155));
  }

  Rect r = cv->dirty();
  const Rect dyn = r;
  r.add(prevDirty);
  r.add(uiDirty);
  pushRect(r);
  prevDirty = dyn;
}

// ----------------------------------------------------------------- clock ---

static bool clockValid() {
  if (!rtcOk) return false;
  return rtc.getDateTime().getYear() >= 2025;
}

static uint32_t localEpoch() {  // RTC keeps local time
  if (!clockValid()) return 0;
  RTC_DateTime d = rtc.getDateTime();
  struct tm t = {};
  t.tm_year = d.getYear() - 1900;
  t.tm_mon = d.getMonth() - 1;
  t.tm_mday = d.getDay();
  t.tm_hour = d.getHour();
  t.tm_min = d.getMinute();
  t.tm_sec = d.getSecond();
  return (uint32_t)mktime(&t);  // TZ is UTC on the device, so this is "local seconds"
}

static void setClockLocal(uint32_t localSecs) {
  if (!rtcOk) return;
  time_t tt = (time_t)localSecs;
  struct tm t;
  gmtime_r(&tt, &t);
  rtc.setDateTime(t.tm_year + 1900, t.tm_mon + 1, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec);
}

// localEpoch() reads the RTC over I2C; the UI wants it every frame, so keep
// a copy and refresh it once a second.
static uint32_t localNowCached() {
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
  if (!clockValid()) return claude.localHour();
  RTC_DateTime d = rtc.getDateTime();
  return d.getHour() + d.getMinute() / 60.0f;
}

static void updateCalendar() {
  const uint32_t now = localEpoch();
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
  const bool birthday = day != bornDay && tb.tm_mon == tn.tm_mon && tb.tm_mday == tn.tm_mday;
  brain->setDay((int32_t)day, birthday);
}

// ----------------------------------------------------------- persistence ---

static void saveMemory() {
  prefs.putBytes("mem", &brain->memory(), sizeof(Memory));
  const uint32_t now = localEpoch();
  if (now) prefs.putUInt("seen", now);
  prefs.putUInt("naps", naps);
}

static void saveAlarms() {
  uint8_t buf[Alarms::kMaxBlob];
  const size_t n = alarms.serialize(buf, sizeof buf);
  if (n) prefs.putBytes("alarms", buf, n);
}

static void loadAlarms() {
  uint8_t buf[Alarms::kMaxBlob];
  const size_t n = prefs.getBytes("alarms", buf, sizeof buf);
  if (n && !alarms.deserialize(buf, n)) Serial.println("[alarms] stored data unreadable, ignored");
  Serial.printf("[alarms] %d loaded\n", alarms.count());
}

static void listAlarms() {
  const uint32_t now = localNowCached();
  for (int i = 0; i < alarms.count(); ++i) {
    const Alarm& a = alarms.at(i);
    const uint32_t nf = now ? Alarms::nextFire(a, now) : 0;
    Serial.printf("  %d  %02u:%02u  days %02X  %s  '%s'  next in %lu min\n", i, a.hour, a.minute, a.days,
                  a.enabled ? "on " : "off", a.label, nf ? (unsigned long)((nf - now + 59) / 60) : 0UL);
  }
  if (!alarms.count()) Serial.println("  no alarms");
}

static void loadMemory() {
  Memory m;
  if (prefs.getBytes("mem", &m, sizeof m) == sizeof m) brain->memory() = m;
  bornDay = prefs.getUInt("born", 0);
  naps = prefs.getUInt("naps", 0);
  const uint32_t seen = prefs.getUInt("seen", 0), now = localEpoch();
  if (seen && now > seen) brain->setAbsence((now - seen) / 3600.0f);
}

// ---------------------------------------------------------------- serial ---

static void help() {
  Serial.println(
      "Micul Smecher v0 - serial commands:\n"
      "  b boop   l laugh  s shy     p purr on/off d dizzy   f scared  c confused\n"
      "  y yawn   n sneeze h hiccup  v love     r birthday m missed-you o lonely\n"
      "  k startle g good-night w wake  z sleep  D demo loop on/off\n"
      "  i imu raw  t time  T<epoch_local> set clock  P personality  U unpair  ? help\n"
      "  SoulOS: N note field  A alarm time picker  L list alarms  X delete alarms  (BOOT = back)");
}

static void serialCommands() {
  while (Serial.available()) {
    const int c = Serial.read();
    switch (c) {
      case 'b': brain->trigger(Reaction::Boop); break;
      case 'l': brain->trigger(Reaction::Laugh); break;
      case 's': brain->trigger(Reaction::Shy); break;
      case 'p': brain->event(brain->reaction() == Reaction::Purr ? Ev::StrokeEnd : Ev::StrokeStart); break;
      case 'd': brain->trigger(Reaction::Dizzy); break;
      case 'f': brain->trigger(Reaction::Scared); break;
      case 'c': brain->trigger(Reaction::Confused); break;
      case 'y': brain->trigger(Reaction::Yawn); break;
      case 'n': brain->trigger(Reaction::Sneeze); break;
      case 'h': brain->trigger(Reaction::Hiccup); break;
      case 'v': brain->trigger(Reaction::Love); break;
      case 'r': brain->trigger(Reaction::Birthday); break;
      case 'm': brain->trigger(Reaction::MissedYou); break;
      case 'o': brain->trigger(Reaction::Lonely); break;
      case 'k': brain->trigger(Reaction::Startle); break;
      case 'g': brain->event(Ev::FaceDown); break;
      case 'w': brain->event(Ev::PickUp); break;
      case 'z': brain->trigger(Reaction::GoodNight); break;
      case 'D': demo = !demo; Serial.printf("demo %s\n", demo ? "on" : "off"); break;
      case 'i': {
        float x = 0, y = 0, z = 0;
        if (imuOk) imu.getAccelerometer(x, y, z);
        Serial.printf("accel raw %.2f %.2f %.2f  still %.1fs\n", x, y, z, motion.stillFor());
        break;
      }
      case 't':
        Serial.printf("clock %s, hour %.2f, mode %s, reaction %s\n", clockValid() ? "ok" : "unset",
                      hourNow(), modeName(brain->mode()), reactionName(brain->reaction()));
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
        Serial.printf("I am '%s' - eyes %s (%s), shy %.2f, curious %.2f, sleepy %.2f, boops %lu\n",
                      p.archetypeRo(), p.tintName(), p.rarityName(), p.shyness, p.curiosity,
                      p.sleepiness, (unsigned long)brain->memory().boopsTotal);
        break;
      }
      case 'U': bleClearBonds(); break;
      case 'N': shell.openNote(); break;
      case 'A': shell.openTimePicker(((int)hourNow() + 1) % 24, 0); break;  // the next whole hour
      case 'L': listAlarms(); break;
      case 'X':
        alarms.clear();
        saveAlarms();
        Serial.println("alarms deleted");
        break;
      case '?': help(); break;
      default: break;
    }
  }
}

static void demoTick(float dt) {
  static const Reaction kLoop[] = {Reaction::Boop,    Reaction::Laugh,    Reaction::Shy,
                                   Reaction::Dizzy,   Reaction::Sneeze,   Reaction::Love,
                                   Reaction::Confused, Reaction::Hiccup,  Reaction::Birthday,
                                   Reaction::Yawn,    Reaction::MissedYou};
  demoT += dt;
  if (demoT > 5.0f) {
    demoT = 0;
    brain->trigger(kLoop[demoIdx++ % (sizeof(kLoop) / sizeof(kLoop[0]))]);
  }
}

// ------------------------------------------------------------ setup/loop ---

void setup() {
  Serial.begin(115200);
  delay(200);
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
#if HAS_PMU
  pmuInit();
#endif
  displayInit();
  touchInit();

  imuOk = imu.begin(Wire, IMU_ADDR, I2C_SDA, I2C_SCL);
  if (imuOk) {
    imu.configAccelerometer(SensorQMI8658::ACC_RANGE_4G, SensorQMI8658::ACC_ODR_125Hz,
                            SensorQMI8658::LPF_MODE_0);
    imu.enableAccelerometer();
  }
  rtcOk = rtc.begin(Wire, I2C_SDA, I2C_SCL);
  Serial.printf("[imu] %s  [rtc] %s\n", imuOk ? "ok" : "NOT FOUND", rtcOk ? "ok" : "NOT FOUND");

  // Birth: the chip's unique MAC is the seed of its personality.
  uint8_t mac[6];
  esp_efuse_mac_get_default(mac);
  uint64_t seed = 0;
  for (int i = 0; i < 6; ++i) seed = (seed << 8) | mac[i];
  brain = new Brain(Personality::fromSeed(seed));
  prefs.begin("suflet", false);
  loadMemory();
  loadAlarms();
  updateCalendar();
  brain->boot();

  char name[32];
  snprintf(name, sizeof name, "Claude-Suflet-%02X%02X", mac[4], mac[5]);
  claude.setName(name);
  bleInit(name);

  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  if (digitalRead(BOOT_BUTTON) == LOW) demo = true;  // hold BOOT at power-on = demo loop

  help();
  const Personality& p = brain->personality();
  Serial.printf("[soul] %s, eyes %s (%s)\n", p.archetypeRo(), p.tintName(), p.rarityName());
  lastMs = lastSaveMs = lastStatusMs = millis();
}

void loop() {
  const uint32_t now = millis();
  float dt = (now - lastMs) / 1000.0f;
  lastMs = now;
  if (dt > 0.5f) dt = 0.5f;

  // touch
  float tx = 0, ty = 0;
  const bool down = readTouch(tx, ty);
  touch.update(down, tx, ty, dt);

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

  // Claude desktop link
  uint8_t chunk[128];
  size_t n = 0;
  while (bleAvailable() && n < sizeof chunk) chunk[n++] = (uint8_t)bleRead();
  if (n) claude.feed(chunk, n);
  claude.setTransportConnected(bleConnected());
  claude.tick(dt);
  if (claude.unpairRequested()) bleClearBonds();
  if (claude.timeValid() && !rtcSynced) {
    setClockLocal((uint32_t)(claude.epochNow() + claude.tzOffset()));
    rtcSynced = true;
    updateCalendar();
  }

  // BOOT button (GPIO0): back / cancel on SoulOS screens
  const bool bootDown = digitalRead(BOOT_BUTTON) == LOW;
  if (bootDown && !bootWasDown) bootDownMs = now;
  if (!bootDown && bootWasDown && now - bootDownMs < 1500 && shell.screen() != Screen::Face) shell.back();
  bootWasDown = bootDown;

  // touches go to the Shell first; what it doesn't use reaches the Brain
  shell.holdOpensNote = !brain->claudePrompt();
  Ev e;
  TouchEv te;
  while (touch.poll(te))
    if (!shell.event(te)) brain->event(te.e);
  touch.setMode(shell.wantsTextTouch() ? TouchMode::Text : TouchMode::Face);
  const uint32_t localNow = localNowCached();
  shell.update(dt, localNow);
  while (shell.poll(e)) {
    if (e == Ev::TextCommit && !shell.notes().empty())
      Serial.printf("[note] %s\n", shell.notes().back().c_str());
    brain->event(e);
  }
  if (shell.lastAlarm() != shownAlarm) {
    shownAlarm = shell.lastAlarm();
    saveAlarms();
    listAlarms();
  }
  if (localNow) {
    const int due = alarms.poll(localNow);
    if (due >= 0) {
      Serial.printf("[alarm] %02u:%02u '%s' rings\n", alarms.at(due).hour, alarms.at(due).minute,
                    alarms.at(due).label);
      brain->event(Ev::AlarmDue);
      saveAlarms();  // lastFired / one-shot off survive a reboot
    }
  }
  while (motion.poll(e)) brain->event(e);
  while (claude.poll(e)) brain->event(e);

  in.tiltX = motion.tiltX();
  in.tiltY = motion.tiltY();
  in.stillFor = touch.isDown() ? 0.0f : motion.stillFor();
  in.faceDown = motion.faceDown();
  in.knockX = motion.knockX();
  in.knockY = motion.knockY();
  in.hour = hourNow();
  if (demo) demoTick(dt);
  const Mode before = brain->mode();
  brain->update(dt, in);
  if (before != Mode::Asleep && brain->mode() == Mode::Asleep) ++naps;

  Cue c;
  while (brain->popCue(c)) {
    if (c == Cue::ClaudeApprove) claude.decide(true);
    if (c == Cue::ClaudeDeny) claude.decide(false);
    // v0 dev boards have no haptic motor; cues are logged for the sound/haptic pass
  }
  std::string line;
  while (claude.popOutgoing(line)) bleWrite((const uint8_t*)line.data(), line.size());

  if (now - lastStatusMs > 2000) {
    lastStatusMs = now;
    int pct, mv;
    bool usb;
    readBattery(pct, mv, usb);
    claude.status.batPct = pct;
    claude.status.batMv = mv;
    claude.status.usb = usb;
    claude.status.secure = bleSecure();
    claude.status.uptimeS = now / 1000;
    claude.status.heap = ESP.getFreeHeap();
    claude.status.naps = naps;
  }

  renderFrame();
  serialCommands();

  if (now - lastSaveMs > 60000) {
    lastSaveMs = now;
    saveMemory();
    updateCalendar();
  }

  // frame pacing: 30 fps awake, fewer when asleep (saves battery)
  const float fps = shell.screen() != Screen::Face ? 30.0f : brain->frameRateHint();  // typing stays snappy
  const uint32_t frameMs = (uint32_t)(1000.0f / fps);
  const uint32_t spent = millis() - now;
  if (spent < frameMs) delay(frameMs - spent);
}
