// The logic of SoulOS's small apps. See AppKit.h.
#include "AppKit.h"

#include <ArduinoJson.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace suflet {
namespace apps {

// ------------------------------------------------------------- weather ---

Sky skyFrom(const char* s) {
  if (!s) return Sky::Cloud;
  if (!strcmp(s, "sun")) return Sky::Sun;
  if (!strcmp(s, "part")) return Sky::Part;
  if (!strcmp(s, "rain")) return Sky::Rain;
  if (!strcmp(s, "snow")) return Sky::Snow;
  if (!strcmp(s, "storm")) return Sky::Storm;
  if (!strcmp(s, "fog")) return Sky::Fog;
  return Sky::Cloud;
}

static std::string cut(const char* s, size_t n) {
  std::string r = s ? s : "";
  if (r.size() > n) r.resize(n);
  return r;
}

bool Weather::parse(const char* json, size_t n, uint32_t now) {
  JsonDocument doc;
  if (deserializeJson(doc, json, n)) return false;
  JsonObjectConst o = doc.as<JsonObjectConst>();
  if (o.isNull() || !o["t"].is<int>() || !o["icon"].is<const char*>()) return false;
  Weather w;
  w.t = o["t"];
  w.feels = o["feels"] | w.t;
  w.hi = o["hi"] | w.t;
  w.lo = o["lo"] | w.t;
  w.rain = o["rain"] | 0;
  w.wind = o["wind"] | 0;
  w.sky = skyFrom(o["icon"]);
  w.word = cut(o["word"] | "", 24);
  w.place = cut(o["place"] | "", 40);
  w.src = cut(o["src"] | "", 24);
  for (JsonArrayConst h : o["hours"].as<JsonArrayConst>()) {
    if (w.hours.size() >= 6) break;
    WeatherHour x;
    x.hh = cut(h[0] | "", 2);
    x.t = h[1] | 0;
    x.sky = skyFrom(h[2] | "cloud");
    x.rain = h[3] | 0;
    w.hours.push_back(x);
  }
  for (JsonArrayConst d : o["days"].as<JsonArrayConst>()) {
    if (w.days.size() >= 3) break;
    WeatherDay x;
    x.name = cut(d[0] | "", 6);
    x.hi = d[1] | 0;
    x.lo = d[2] | 0;
    x.sky = skyFrom(d[3] | "cloud");
    w.days.push_back(x);
  }
  w.ok = true;
  w.at = now;
  *this = w;
  return true;
}

// -------------------------------------------------------------- agenda ---

static int64_t daysFromCivil(int y, unsigned m, unsigned d) {  // Howard Hinnant
  y -= m <= 2;
  const int64_t era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return era * 146097 + (int64_t)doe - 719468;
}

uint32_t parseLocal(const char* s) {
  int y, mo, d, h = 0, mi = 0;
  if (!s || sscanf(s, "%4d-%2d-%2dT%2d:%2d", &y, &mo, &d, &h, &mi) < 3) return 0;
  if (y < 2000 || y > 2100 || mo < 1 || mo > 12 || d < 1 || d > 31 || h < 0 || h > 23 || mi < 0 || mi > 59) return 0;
  return (uint32_t)(daysFromCivil(y, (unsigned)mo, (unsigned)d) * 86400 + h * 3600 + mi * 60);
}

bool Agenda::parse(const char* json, size_t n, uint32_t now) {
  JsonDocument doc;
  if (deserializeJson(doc, json, n)) return false;
  JsonArrayConst arr = doc["events"].as<JsonArrayConst>();
  if (arr.isNull()) return false;
  Agenda a;
  for (JsonObjectConst e : arr) {
    if (a.events.size() >= 12) break;
    Event x;
    x.start = parseLocal(e["s"] | "");
    x.end = parseLocal(e["e"] | "");
    if (!x.start) continue;
    if (x.end < x.start) x.end = x.start;
    x.title = cut(e["t"] | "", 80);
    x.place = cut(e["l"] | "", 60);
    x.allDay = e["a"] | false;
    a.events.push_back(x);
  }
  a.ok = true;
  a.at = now;
  *this = a;
  return true;
}

int Agenda::next(uint32_t now) const {
  for (size_t i = 0; i < events.size(); ++i) {
    const Event& e = events[i];
    if (e.allDay ? e.end > now || e.start / 86400 == now / 86400 : e.end > now) return (int)i;
  }
  return -1;
}

// --------------------------------------------------------------- rates ---

Rates::Rates() {
  // built in: approximate euro reference rates, only until SOUL Cloud sends the ECB's daily table
  static const struct {
    const char* c;
    double r;
  } k[] = {{"USD", 1.09}, {"GBP", 0.84}, {"RON", 4.98}, {"CHF", 0.94}, {"HUF", 395.0}, {"PLN", 4.28},
           {"CZK", 25.1}, {"SEK", 11.2}, {"NOK", 11.6}, {"DKK", 7.46}, {"BGN", 1.9558}, {"TRY", 37.5},
           {"JPY", 162.0}, {"CNY", 7.8}, {"CAD", 1.49}, {"AUD", 1.62}, {"INR", 91.0}};
  perEur.push_back({"EUR", 1.0});
  for (const auto& x : k) perEur.push_back({x.c, x.r});
}

bool Rates::parse(const char* json, size_t n) {
  JsonDocument doc;
  if (deserializeJson(doc, json, n)) return false;
  JsonObjectConst r = doc["rates"].as<JsonObjectConst>();
  if (r.isNull() || strcmp(doc["base"] | "", "EUR") != 0) return false;
  std::vector<std::pair<std::string, double>> out;
  out.push_back({"EUR", 1.0});
  for (JsonPairConst kv : r) {
    const double v = kv.value() | 0.0;
    const char* c = kv.key().c_str();
    if (v > 0 && strlen(c) == 3 && out.size() < 40) out.push_back({c, v});
  }
  if (out.size() < 2) return false;
  perEur = out;
  date = cut(doc["date"] | "", 10);
  fromCloud = true;
  return true;
}

double Rates::rate(const std::string& code) const {
  for (const auto& p : perEur)
    if (p.first == code) return p.second;
  return 0;
}

// ---------------------------------------------------------- time zones ---

static const char* tzName(const char* p, std::string& out) {
  out.clear();
  if (*p == '<') {
    ++p;
    while (*p && *p != '>') out += *p++;
    return *p == '>' ? p + 1 : nullptr;
  }
  while (*p && ((*p >= 'A' && *p <= 'Z') || (*p >= 'a' && *p <= 'z'))) out += *p++;
  return out.size() >= 3 ? p : nullptr;
}

static const char* tzOffset(const char* p, int& secs) {  // [+-]hh[:mm[:ss]]; POSIX: west of UTC is positive
  int sign = 1;
  if (*p == '+' || *p == '-') sign = *p++ == '-' ? -1 : 1;
  if (*p < '0' || *p > '9') return nullptr;
  int h = 0, m = 0, s = 0;
  while (*p >= '0' && *p <= '9') h = h * 10 + (*p++ - '0');
  if (*p == ':') {
    ++p;
    while (*p >= '0' && *p <= '9') m = m * 10 + (*p++ - '0');
    if (*p == ':') {
      ++p;
      while (*p >= '0' && *p <= '9') s = s * 10 + (*p++ - '0');
    }
  }
  secs = sign * (h * 3600 + m * 60 + s);
  return p;
}

static const char* tzRule(const char* p, PosixTz::Rule& r) {
  if (*p != 'M') return nullptr;  // only the Mm.w.d form (what every zone of the world clock uses)
  ++p;
  r.month = (int)strtol(p, (char**)&p, 10);
  if (*p++ != '.') return nullptr;
  r.week = (int)strtol(p, (char**)&p, 10);
  if (*p++ != '.') return nullptr;
  r.wday = (int)strtol(p, (char**)&p, 10);
  r.secs = 7200;
  if (*p == '/') {
    int s;
    p = tzOffset(p + 1, s);
    if (!p) return nullptr;
    r.secs = s;
  }
  if (r.month < 1 || r.month > 12 || r.week < 1 || r.week > 5 || r.wday < 0 || r.wday > 6) return nullptr;
  return p;
}

bool PosixTz::parse(const char* s) {
  *this = PosixTz();
  if (!s) return false;
  const char* p = tzName(s, stdName);
  if (!p) return false;
  int off;
  p = tzOffset(p, off);
  if (!p) return false;
  stdOff = -off;
  if (!*p) return true;
  p = tzName(p, dstName);
  if (!p) return false;
  dstOff = stdOff + 3600;
  if (*p && *p != ',') {
    p = tzOffset(p, off);
    if (!p) return false;
    dstOff = -off;
  }
  if (*p != ',') return false;
  p = tzRule(p + 1, start);
  if (!p || *p != ',') return false;
  p = tzRule(p + 1, end);
  if (!p) return false;
  hasDst = true;
  return true;
}

static int64_t ruleUtc(const PosixTz::Rule& r, int year, int offsetBefore) {
  static const int mdays[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
  const int64_t first = daysFromCivil(year, (unsigned)r.month, 1);
  const int wdFirst = (int)(((first % 7) + 11) % 7);  // 1970-01-01 was a Thursday (4)
  int day = 1 + (r.wday - wdFirst + 7) % 7 + (r.week - 1) * 7;
  int dim = mdays[r.month - 1] + (r.month == 2 && ((year % 4 == 0 && year % 100) || year % 400 == 0));
  while (day > dim) day -= 7;
  return (first + day - 1) * 86400 + r.secs - offsetBefore;
}

bool PosixTz::dstAt(int64_t utc) const {
  if (!hasDst) return false;
  const int64_t days = (utc + stdOff) / 86400 - (utc + stdOff < 0 ? 1 : 0);
  // year of that local day
  int64_t z = days + 719468;
  const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
  const unsigned doe = (unsigned)(z - era * 146097);
  const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const unsigned mp = (5 * doy + 2) / 153;
  const unsigned m = mp + (mp < 10 ? 3 : -9);
  const int year = (int)(yoe + era * 400 + (m <= 2));
  const int64_t s = ruleUtc(start, year, stdOff), e = ruleUtc(end, year, dstOff);
  return s < e ? (utc >= s && utc < e) : !(utc >= e && utc < s);  // southern hemisphere: DST spans New Year
}

int PosixTz::offsetAt(int64_t utc) const { return dstAt(utc) ? dstOff : stdOff; }

const std::vector<City>& cities() {
  static const std::vector<City> k = {
      {"Auckland", "Auckland", "NZST-12NZDT,M9.5.0,M4.1.0/3"},
      {"Berlin", "Berlin", "CET-1CEST,M3.5.0,M10.5.0/3"},
      {"Bucharest", "București", "EET-2EEST,M3.5.0/3,M10.5.0/4"},
      {"Chicago", "Chicago", "CST6CDT,M3.2.0,M11.1.0"},
      {"Chisinau", "Chișinău", "EET-2EEST,M3.5.0,M10.5.0/3"},
      {"Dubai", "Dubai", "<+04>-4"},
      {"Hong Kong", "Hong Kong", "HKT-8"},
      {"Lisbon", "Lisabona", "WET0WEST,M3.5.0/1,M10.5.0"},
      {"London", "Londra", "GMT0BST,M3.5.0/1,M10.5.0"},
      {"Los Angeles", "Los Angeles", "PST8PDT,M3.2.0,M11.1.0"},
      {"Mumbai", "Mumbai", "IST-5:30"},
      {"New York", "New York", "EST5EDT,M3.2.0,M11.1.0"},
      {"Paris", "Paris", "CET-1CEST,M3.5.0,M10.5.0/3"},
      {"Sao Paulo", "São Paulo", "<-03>3"},
      {"Sydney", "Sydney", "AEST-10AEDT,M10.1.0,M4.1.0/3"},
      {"Tokyo", "Tokyo", "JST-9"},
  };
  return k;
}

// ----------------------------------------------------------- converter ---

const std::vector<Unit>& units(Quantity q) {
  static const std::vector<Unit> length = {{"m", "m", 1, 0},          {"km", "km", 1000, 0},     {"cm", "cm", 0.01, 0},
                                           {"mm", "mm", 0.001, 0},    {"mi", "mi", 1609.344, 0}, {"ft", "ft", 0.3048, 0},
                                           {"in", "in", 0.0254, 0},   {"yd", "yd", 0.9144, 0}};
  static const std::vector<Unit> weight = {{"kg", "kg", 1, 0}, {"g", "g", 0.001, 0}, {"lb", "lb", 0.45359237, 0},
                                           {"oz", "oz", 0.028349523125, 0}, {"st", "st", 6.35029318, 0}};
  static const std::vector<Unit> temp = {{"C", "\xC2\xB0" "C", 1, 0}, {"F", "\xC2\xB0" "F", 5.0 / 9.0, -32.0 * 5.0 / 9.0},
                                         {"K", "K", 1, -273.15}};
  static const std::vector<Unit> volume = {{"l", "l", 1, 0},         {"ml", "ml", 0.001, 0},
                                           {"gal", "gal", 3.785411784, 0}, {"cup", "cup", 0.2365882365, 0},
                                           {"floz", "fl oz", 0.0295735295625, 0}, {"tbsp", "tbsp", 0.01478676478125, 0},
                                           {"tsp", "tsp", 0.00492892159375, 0}};
  static const std::vector<Unit> speed = {{"kmh", "km/h", 1.0 / 3.6, 0}, {"ms", "m/s", 1, 0}, {"mph", "mph", 0.44704, 0},
                                          {"kn", "kn", 0.514444, 0}};
  static const std::vector<Unit> money = {{"EUR", "EUR", 0, 0}, {"RON", "RON", 0, 0}, {"USD", "USD", 0, 0},
                                          {"GBP", "GBP", 0, 0}, {"CHF", "CHF", 0, 0}, {"HUF", "HUF", 0, 0},
                                          {"PLN", "PLN", 0, 0}, {"JPY", "JPY", 0, 0}, {"TRY", "TRY", 0, 0}};
  switch (q) {
    case Quantity::Length: return length;
    case Quantity::Weight: return weight;
    case Quantity::Temperature: return temp;
    case Quantity::Volume: return volume;
    case Quantity::Speed: return speed;
    default: return money;
  }
}

const char* quantityName(Quantity q, bool ro) {
  static const char* const en[] = {"Length", "Weight", "Temperature", "Volume", "Speed", "Currency"};
  static const char* const r[] = {"Lungime", "Greutate", "Temperatură", "Volum", "Viteză", "Valută"};
  const int i = (int)q < 6 ? (int)q : 0;
  return ro ? r[i] : en[i];
}

double convert(Quantity q, int from, int to, double v, const Rates& rates) {
  const std::vector<Unit>& u = units(q);
  if (from < 0 || to < 0 || from >= (int)u.size() || to >= (int)u.size()) return NAN;
  if (q == Quantity::Currency) {
    const double a = rates.rate(u[from].id), b = rates.rate(u[to].id);
    if (a <= 0 || b <= 0) return NAN;
    return v / a * b;
  }
  const double base = v * u[from].k + u[from].off;
  return (base - u[to].off) / u[to].k;
}

std::string formatNumber(double v) {
  if (isnan(v) || isinf(v)) return "\xE2\x80\x94";
  char b[48];
  const double a = fabs(v);
  if (a != 0 && (a >= 1e9 || a < 1e-4)) {
    snprintf(b, sizeof b, "%.3g", v);
    return b;
  }
  const int dec = a >= 1000 ? 0 : a >= 100 ? 1 : a >= 1 ? 2 : 4;
  snprintf(b, sizeof b, "%.*f", dec, v);
  std::string s = b;
  if (s.find('.') != std::string::npos) {  // trim trailing zeros
    while (!s.empty() && s.back() == '0') s.pop_back();
    if (!s.empty() && s.back() == '.') s.pop_back();
  }
  // thin spaces between thousands: 12 345
  const size_t dot = s.find('.');
  const size_t intEnd = dot == std::string::npos ? s.size() : dot;
  const size_t intStart = s[0] == '-' ? 1 : 0;
  std::string out = s.substr(0, intStart);
  for (size_t i = intStart; i < intEnd; ++i) {
    out += s[i];
    const size_t left = intEnd - i - 1;
    if (left && left % 3 == 0) out += " ";
  }
  out += s.substr(intEnd);
  if (out == "-0") out = "0";
  return out;
}

// --------------------------------------------------------------- habits ---

void Habit::shiftTo(uint32_t today) {
  if (today <= day) return;
  const uint32_t d = today - day;
  bits = d >= 32 ? 0 : bits << d;
  day = today;
}

bool Habit::doneOn(uint32_t date) const {
  if (date > day || day - date >= 32) return false;  // bit k = k days before `day`
  return (bits >> (day - date)) & 1u;
}

void Habit::toggle(uint32_t today) {
  shiftTo(today);
  bits ^= 1u;
}

int Habit::streak(uint32_t today) const {
  Habit h = *this;
  h.shiftTo(today);
  int k = (h.bits & 1u) ? 0 : 1;  // today still open: count from yesterday
  int n = 0;
  for (; k < 32 && (h.bits >> k) & 1u; ++k) ++n;
  return n;
}

int Habit::lastWeek(uint32_t today) const {
  Habit h = *this;
  h.shiftTo(today);
  int n = 0;
  for (int k = 0; k < 7; ++k) n += (h.bits >> k) & 1u;
  return n;
}

// ------------------------------------------------------------ pomodoro ---

void Pomodoro::start() {
  phase_ = Phase::Focus;
  left_ = focusMin * 60.0f;
  round_ = 1;
  done_ = 0;
  paused_ = false;
  ended_ = Phase::Idle;
}

void Pomodoro::stop() {
  phase_ = Phase::Idle;
  left_ = 0;
  paused_ = false;
}

float Pomodoro::total() const {
  switch (phase_) {
    case Phase::Focus: return focusMin * 60.0f;
    case Phase::Short: return shortMin * 60.0f;
    case Phase::Long: return longMin * 60.0f;
    default: return 1;
  }
}

bool Pomodoro::tick(float dt) {
  if (phase_ == Phase::Idle || paused_) return false;
  left_ -= dt;
  if (left_ > 0) return false;
  ended_ = phase_;
  const float spill = -left_;
  if (phase_ == Phase::Focus) {
    ++done_;
    if (round_ >= rounds) {
      phase_ = Phase::Long;
      left_ = longMin * 60.0f;
    } else {
      phase_ = Phase::Short;
      left_ = shortMin * 60.0f;
    }
  } else {
    if (phase_ == Phase::Long) round_ = 1;
    else ++round_;
    phase_ = Phase::Focus;
    left_ = focusMin * 60.0f;
  }
  left_ -= spill;
  return true;
}

// ------------------------------------------------------------- breathe ---

const std::vector<BreathPattern>& breathPatterns() {
  static const std::vector<BreathPattern> k = {
      {"Calm 4-6", "Calm 4-6", 4, 0, 6, 0},
      {"Box 4-4-4-4", "Pătrat 4-4-4-4", 4, 4, 4, 4},
      {"Sleep 4-7-8", "Somn 4-7-8", 4, 7, 8, 0},
      {"Coherent 5.5", "Coerent 5,5", 5.5f, 0, 5.5f, 0},
  };
  return k;
}

BreathPoint breathAt(const BreathPattern& p, float t) {
  BreathPoint b;
  const float c = p.cycle();
  if (c <= 0 || t < 0) return b;
  b.cycle = (int)(t / c);
  float u = fmodf(t, c);
  const float d[4] = {p.in, p.hold1, p.out, p.hold2};
  for (int i = 0; i < 4; ++i) {
    if (d[i] <= 0) continue;
    if (u < d[i]) {
      b.phase = i;
      b.progress = u / d[i];
      break;
    }
    u -= d[i];
    b.phase = (i + 1) % 4;
    b.progress = 0;
  }
  // eased: lungs fill and empty smoothly (sine ease in-out)
  const float e = 0.5f - 0.5f * cosf(b.progress * 3.14159265f);
  b.size = b.phase == 0 ? e : b.phase == 1 ? 1.0f : b.phase == 2 ? 1.0f - e : 0.0f;
  return b;
}

// ----------------------------------------------------------- stopwatch ---

std::string Stopwatch::format(double s, bool tenths) {
  if (s < 0) s = 0;
  const long t10 = (long)(s * 10.0 + 1e-6);
  const long secs = t10 / 10, h = secs / 3600 % 1000, m = secs / 60 % 60, ss = secs % 60;
  char b[48];
  if (h) snprintf(b, sizeof b, "%ld:%02ld:%02ld", h, m, ss);
  else if (tenths) snprintf(b, sizeof b, "%02ld:%02ld.%ld", m, ss, t10 % 10);
  else snprintf(b, sizeof b, "%02ld:%02ld", m, ss);
  return b;
}

// ------------------------------------------------------------ prefs blob ---

std::string kvGet(const std::string& blob, const char* key, const char* def) {
  const std::string k = std::string(key) + "=";
  size_t i = 0;
  while (i < blob.size()) {
    size_t e = blob.find('\n', i);
    if (e == std::string::npos) e = blob.size();
    if (blob.compare(i, k.size(), k) == 0) return blob.substr(i + k.size(), e - i - k.size());
    i = e + 1;
  }
  return def;
}

void kvSet(std::string& blob, const char* key, const std::string& value) {
  const std::string k = std::string(key) + "=";
  std::string v;
  for (char c : value) v += (c == '\n' || c == '\r') ? ' ' : c;
  size_t i = 0;
  while (i < blob.size()) {
    size_t e = blob.find('\n', i);
    if (e == std::string::npos) e = blob.size();
    if (blob.compare(i, k.size(), k) == 0) {
      blob.replace(i, e - i, k + v);
      return;
    }
    i = e + 1;
  }
  if (!blob.empty() && blob.back() != '\n') blob += '\n';
  blob += k + v + "\n";
}

}  // namespace apps
}  // namespace suflet
