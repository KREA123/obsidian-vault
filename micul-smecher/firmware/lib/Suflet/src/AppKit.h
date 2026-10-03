// The logic of SoulOS's small apps (os/APPS.md), apart from their screens:
// what SOUL Cloud sends (weather, the agenda, exchange rates), time zones
// for the world clock (POSIX TZ rules, offline), the unit converter, habits,
// the pomodoro cycle, breathing patterns, the stopwatch and the launcher's
// order. Transport-free, tested on the PC (test/test_suflet/test_apps.cpp).
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {
namespace apps {

// ------------------------------------------------------------- weather ---
enum class Sky : uint8_t { Sun, Part, Cloud, Rain, Snow, Storm, Fog };
Sky skyFrom(const char* icon);
struct WeatherHour {
  std::string hh;
  int t = 0, rain = 0;
  Sky sky = Sky::Cloud;
};
struct WeatherDay {
  std::string name;
  int hi = 0, lo = 0;
  Sky sky = Sky::Cloud;
};
struct Weather {
  bool ok = false;
  int t = 0, feels = 0, hi = 0, lo = 0, rain = 0, wind = 0;
  Sky sky = Sky::Cloud;
  std::string word, place, src;
  std::vector<WeatherHour> hours;  // <= 6
  std::vector<WeatherDay> days;    // <= 3
  uint32_t at = 0;                 // when it was fetched (local epoch)
  bool parse(const char* json, size_t n, uint32_t now);
};

// -------------------------------------------------------------- agenda ---
struct Event {
  uint32_t start = 0, end = 0;  // local epoch
  std::string title, place;
  bool allDay = false;
};
struct Agenda {
  bool ok = false;
  std::vector<Event> events;  // soonest first, <= 12
  uint32_t at = 0;
  bool parse(const char* json, size_t n, uint32_t now);
  // the first event that has not ended (all-day ones count for their day); -1 none
  int next(uint32_t now) const;
};
// "2026-10-03T15:00" -> local epoch (0 on a bad string)
uint32_t parseLocal(const char* s);

// --------------------------------------------------------------- rates ---
struct Rates {
  std::string date = "2026-10-01";  // the built-in table (ECB reference rates); replaced from the cloud
  std::vector<std::pair<std::string, double>> perEur;
  bool fromCloud = false;
  Rates();
  bool parse(const char* json, size_t n);  // {"base":"EUR","date":"…","rates":{"USD":1.09,...}}
  double rate(const std::string& code) const;  // units per EUR (EUR = 1); 0 = unknown
};

// ---------------------------------------------------------- time zones ---
// A POSIX TZ rule ("EET-2EEST,M3.5.0/3,M10.5.0/4"): offset (seconds east of UTC) at a UTC time.
struct PosixTz {
  int stdOff = 0, dstOff = 0;  // seconds east of UTC
  bool hasDst = false;
  struct Rule {
    int month = 0, week = 0, wday = 0, secs = 7200;  // Mm.w.d/time
  } start, end;
  std::string stdName, dstName;
  bool parse(const char* s);
  int offsetAt(int64_t utc) const;
  bool dstAt(int64_t utc) const;
};
struct City {
  const char* name;
  const char* nameRo;
  const char* tz;  // POSIX
};
const std::vector<City>& cities();  // 16 cities, alphabetical; tests and the world clock

// ----------------------------------------------------------- converter ---
enum class Quantity : uint8_t { Length, Weight, Temperature, Volume, Speed, Currency, Count };
struct Unit {
  const char* id;
  const char* label;
  double k, off;  // to base: base = v * k + off (temperature); currency ignores these
};
const std::vector<Unit>& units(Quantity q);
const char* quantityName(Quantity q, bool ro);
// from -> to; currency through EUR with `rates`
double convert(Quantity q, int from, int to, double v, const Rates& rates);
std::string formatNumber(double v);  // 0.000123 · 12.5 · 1 234 · 1.2e9

// --------------------------------------------------------------- habits ---
struct Habit {
  std::string name;
  uint32_t bits = 0;     // bit 0 = the day `day`, bit k = k days before
  uint32_t day = 0;      // the local day number (epoch / 86400) bit 0 stands for
  void shiftTo(uint32_t today);
  bool doneOn(uint32_t date) const;
  void toggle(uint32_t today);
  int streak(uint32_t today) const;  // days in a row ending today (or yesterday, if today is still open)
  int lastWeek(uint32_t today) const;  // of the last 7 days
};

// ------------------------------------------------------------ pomodoro ---
class Pomodoro {
 public:
  enum class Phase : uint8_t { Idle, Focus, Short, Long };
  int focusMin = 25, shortMin = 5, longMin = 15, rounds = 4;
  void start();
  void stop();
  void pause(bool p) { paused_ = p; }
  bool paused() const { return paused_; }
  // advances the clock; returns true when a phase just ended (the next one starts at once)
  bool tick(float dt);
  Phase phase() const { return phase_; }
  Phase ended() const { return ended_; }  // the phase that ended on the last true tick()
  float left() const { return left_; }
  float total() const;
  int round() const { return round_; }  // 1..rounds
  int done() const { return done_; }    // focus blocks finished since start()

 private:
  Phase phase_ = Phase::Idle, ended_ = Phase::Idle;
  float left_ = 0;
  int round_ = 1, done_ = 0;
  bool paused_ = false;
};

// ------------------------------------------------------------- breathe ---
struct BreathPattern {
  const char* name;
  const char* nameRo;
  float in, hold1, out, hold2;  // seconds
  float cycle() const { return in + hold1 + out + hold2; }
};
const std::vector<BreathPattern>& breathPatterns();
struct BreathPoint {
  int phase = 0;      // 0 in, 1 hold (full), 2 out, 3 hold (empty)
  float progress = 0; // 0..1 inside the phase
  float size = 0;     // 0 (empty) .. 1 (full lungs): what the eyes and the ring follow
  int cycle = 0;
};
BreathPoint breathAt(const BreathPattern& p, float t);

// ----------------------------------------------------------- stopwatch ---
struct Stopwatch {
  bool run = false;
  double acc = 0;  // seconds
  std::vector<double> laps;  // split times
  void tick(float dt) {
    if (run) acc += dt;
  }
  void toggle() { run = !run; }
  void lap() {
    if (run && laps.size() < 99) laps.push_back(acc);
  }
  void reset() {
    run = false;
    acc = 0;
    laps.clear();
  }
  static std::string format(double s, bool tenths = true);  // 01:02.3 · 1:02:03
};

// ------------------------------------------------------------ prefs blob ---
// key=value lines, the same idea as the notes blob (Os.cpp): forward compatible, unknown keys ignored.
std::string kvGet(const std::string& blob, const char* key, const char* def = "");
void kvSet(std::string& blob, const char* key, const std::string& value);

}  // namespace apps
}  // namespace suflet
