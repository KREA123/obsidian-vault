// SoulOS apps: what each app screen shows, in the Glass language
// (os/DESIGN-GLASS.md): the words on frosted glass over the aura, titles in a
// capsule on the top rim, actions as glass pills and orbs, one light at a
// time (cream info, ice listening, amber needs you, mint done). Breathe, the
// rhythm game and eye memory are face moments: pure black behind the eyes.
// Layout in design px of the 466 disc (DisplayGeometry scales it).
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "Os.h"
#include "QrImage.h"
#include "Raster.h"

namespace suflet {

using namespace eyes;

static const Rgb kCream = Rgb::hex(0xFFF0C8), kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4),
                 kIce = Rgb::hex(0x9FC6FF), kDark = Rgb::hex(0x05050A);
static const float kDim = 0.62f, kFaint = 0.42f;
static constexpr float kPi = 3.14159265f;

// the same ids as OsApps.cpp
enum : int {
  AStart = 200, AStop, APause, ASkip, ANext, APrev, APhone, AEnd, APlus, AMinus, ACenter, ARetry, ANew, ASwap,
  AQty, AFrom, ATo, AValue, ARing, AFound, AMode, ALap, AReset, AWifi, AGo, AAgain, AMenu, APattern, ADur,
  AStartNav, AClose, ASound, ASleepT, AWhereQr, AAi, AAuto,
  AGame = 260, AReply = 280, ATile = 300, ARow = 400, AUp = 500,
};

static std::string fit(const Font& f, const std::string& s, float maxW) {
  if (Canvas::measureText(f, s.c_str()) <= maxW) return s;
  std::string out;
  const char* p = s.c_str();
  const char* end = p + s.size();
  while (p < end) {
    const char* q = p;
    utf8::next(q, end);
    if (Canvas::measureText(f, (out + std::string(p, q - p) + "\xE2\x80\xA6").c_str()) > maxW) break;
    out.append(p, q - p);
    p = q;
  }
  return out + "\xE2\x80\xA6";
}

static std::string hm(uint32_t t) {
  char b[8];
  snprintf(b, sizeof b, "%02u:%02u", (unsigned)(t % 86400 / 3600), (unsigned)(t % 3600 / 60));
  return b;
}

static std::string upper(const std::string& s) {
  std::string o;
  const char* p = s.c_str();
  const char* e = p + s.size();
  while (p < e) {
    char b[4];
    const int n = utf8::encode(utf8::upper(utf8::next(p, e)), b);
    o.append(b, n);
  }
  return o;
}

static const char* dayName(uint32_t t, bool ro) {
  static const char* const en[] = {"Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"};
  static const char* const r[] = {"Jo", "Vi", "Sâ", "Du", "Lu", "Ma", "Mi"};
  return (ro ? r : en)[(t / 86400) % 7];
}

static std::string ago(uint32_t now, uint32_t at, bool ro) {
  if (!at || now < at) return "";
  const uint32_t m = (now - at) / 60;
  char b[32];
  if (m < 2) return ro ? "acum" : "now";
  if (m < 60) snprintf(b, sizeof b, ro ? "acum %u min" : "%u min ago", (unsigned)m);
  else snprintf(b, sizeof b, ro ? "acum %u h" : "%u h ago", (unsigned)(m / 60));
  return b;
}

static bool cloudOk(const NetInfo& n) { return n.relay && n.paired; }
// a habit's name gets what its streak label leaves
static float st_w(const apps::Habit& h, uint32_t today) { return h.streak(today) > 0 ? 160.0f : 220.0f; }

// ---------------------------------------------------------------- facts ---

std::string Os::appFact(AppId a) const {
  const bool R = ro();
  const AppsState& A = apps_;
  char b[64];
  switch (a) {
    case AppId::Talk:
      return aiMode() == AiMode::None ? (R ? "Fără AI" : "No AI") : aiMode() == AiMode::Cloud ? "SOUL Cloud"
             : aiMode() == AiMode::Claude ? "Claude" : aiMode() == AiMode::Bridge ? (R ? "Claude (calculator)" : "Claude (computer)")
                                                                                   : "ChatGPT";
    case AppId::Today: return std::string(dayName(now_, R)) + " \xC2\xB7 " + hm(now_);
    case AppId::Maps:
      if (A.navOn) return A.route.to;
      if (A.haveFix) return A.fixLabel.empty() ? (R ? "aici" : "here") + std::string(" · ~") + std::to_string((int)A.fix.accM) + " m" : A.fixLabel;
      return R ? "unde ești?" : "where are you?";
    case AppId::Weather:
      if (!A.weather.ok) return R ? "atinge ca să afli" : "tap to see";
      snprintf(b, sizeof b, "%d\xC2\xB0 \xC2\xB7 %s", A.weather.t, A.weather.word.c_str());
      return b;
    case AppId::Calendar: {
      const int i = A.agenda.ok ? A.agenda.next(now_) : -1;
      if (i < 0) return A.agenda.ok ? (R ? "liber" : "nothing next") : (R ? "agenda ta" : "your agenda");
      return (A.agenda.events[i].allDay ? std::string("") : hm(A.agenda.events[i].start) + " ") + A.agenda.events[i].title;
    }
    case AppId::Alarms: {
      const std::string s = nextAlarmText();
      return s.empty() ? (R ? "nicio alarmă" : "no alarms") : s;
    }
    case AppId::Timer:
      if (timerRun_) {
        snprintf(b, sizeof b, "%d:%02d", timerLeft() / 60, timerLeft() % 60);
        return b;
      }
      return "1 \xC2\xB7 3 \xC2\xB7 5 \xC2\xB7 10 \xC2\xB7 25 min";
    case AppId::Stopwatch: return apps::Stopwatch::format(A.sw.acc, false);
    case AppId::Focus:
      if (A.pomo.phase() != apps::Pomodoro::Phase::Idle) return apps::Stopwatch::format(A.pomo.left(), false);
      return R ? "25 min cu ochii" : "25 min, with the eyes";
    case AppId::Breathe: return R ? apps::breathPatterns()[A.breathPat].nameRo : apps::breathPatterns()[A.breathPat].name;
    case AppId::Habits: {
      int d = 0;
      for (const apps::Habit& h : A.habits) d += h.doneOn(now_ / 86400);
      snprintf(b, sizeof b, R ? "%d din %d azi" : "%d of %d today", d, (int)A.habits.size());
      return b;
    }
    case AppId::Notes: return std::to_string(notes_.size()) + (R ? " notițe" : " notes");
    case AppId::Music: return A.playing ? SoundGen::name(A.sound.kind(), R) : (A.speaker ? (R ? "sunete de focus" : "focus sounds") : (R ? "fără difuzor" : "no speaker"));
    case AppId::Games: snprintf(b, sizeof b, R ? "record %d" : "best %d", A.best[0] > A.best[2] ? A.best[0] : A.best[2]); return b;
    case AppId::WorldClock: {
      if (A.clocks.empty()) return "";
      apps::PosixTz here, there;
      here.parse(A.tz.c_str());
      there.parse(apps::cities()[A.clocks[0]].tz);
      const int64_t utc = (int64_t)now_ - here.offsetAt((int64_t)now_ - here.stdOff);
      return std::string(R ? apps::cities()[A.clocks[0]].nameRo : apps::cities()[A.clocks[0]].name) + " " +
             hm((uint32_t)(utc + there.offsetAt(utc)));
    }
    case AppId::Convert: return R ? "unități · valută" : "units · currency";
    case AppId::FindPhone: return R ? "sună-l" : "ring it";
    case AppId::Claude:
      return claude_.prompt ? (R ? "te așteaptă" : "needs you") : claude_.busy ? (R ? "lucrează" : "working")
             : claude_.linked ? (R ? "conectat" : "connected") : (R ? "neconectat" : "not connected");
    case AppId::Device:
      if (power_.batPct >= 0) return std::to_string(power_.batPct) + "%" + (power_.charging ? (R ? " · se încarcă" : " · charging") : "");
      return "USB";
    case AppId::MySoul: return kDesigns[face_.design()].name;
    default: return set_.name;
  }
}

// ---------------------------------------------------------------- items ---

void Os::buildAppsItems(std::vector<Item>& out) const {
  const bool R = ro();
  const AppsState& A = apps_;
  auto add = [&](int id, float x, float y, float w, float h, const std::string& label, Rgb c, int font, bool pill,
                 float alpha = 1) {
    Item it;
    it.id = id;
    it.x = x;
    it.y = y;
    it.w = w;
    it.h = h;
    it.label = label;
    it.color = c;
    it.font = (uint8_t)font;
    it.underline = pill;
    it.alpha = alpha;
    out.push_back(it);
  };
  switch (view_) {
    case View::Answer:
      if (!thinking_ && !acceptMode_ && !cardHidden_ && !cardTitle_.empty() && net_.paired) {
        add(AReply + 0, 128, 392, 96, 48, "OK", kCream, 0, true);
        add(AReply + 1, 233, 392, 120, 48, R ? "Vin acum" : "On my way", kCream, 0, true);
        add(AReply + 2, 338, 392, 100, 48, R ? "Mai târziu" : "Later", kCream, 0, true);
        add(AReply + 3, 233, 438, 120, 40, R ? "Scrie…" : "Type…", kCream, 0, true, kDim);
      }
      break;
    case View::Control:
      add(ATile + 0, 180, 200, 100, 84, "", kCream, 0, false);
      add(ATile + 1, 286, 200, 100, 84, "", kCream, 0, false);
      add(ATile + 2, 180, 296, 100, 84, "", kCream, 0, false);
      add(ATile + 3, 286, 296, 100, 84, "", kCream, 0, false);
      add(AAi, 233, 404, 230, 44, "", kCream, 0, false);
      add(AAuto, 98, 372, 74, 40, "Auto", set_.bright == 0 ? kAmber : kCream, 0, true, set_.bright == 0 ? 1 : kDim);
      break;
    case View::Weather:
      if (!A.weather.ok && !A.wxWait && cloudOk(net_) && A.wxErr != 409)
        add(ARetry, 233, 372, 160, 48, R ? "Încearcă iar" : "Try again", kCream, 0, true);
      break;
    case View::Calendar:
      if (A.calSel < 0 && A.agenda.ok) {
        const int n = (int)A.agenda.events.size(), pages = n > 3 ? (n + 2) / 3 : 1, p = A.calPage % pages;
        for (int i = p * 3; i < n && i < p * 3 + 3; ++i) add(ARow + i, 233, 164 + (i - p * 3) * 76, 330, 70, "", kCream, 0, false);
      } else if (!A.agenda.ok && !A.calWait && cloudOk(net_) && A.calErr != 404) {
        add(ARetry, 233, 372, 160, 48, R ? "Încearcă iar" : "Try again", kCream, 0, true);
      }
      break;
    case View::Maps:
      if (A.sendSheet) {
        add(AClose, 233, 412, 130, 44, R ? "Gata" : "Done", kCream, 0, true);
      } else if (!A.haveFix && !A.preview && !A.navOn) {
        if (cloudOk(net_)) add(AWifi, 233, 404, 200, 44, R ? "Află prin Wi-Fi" : "Use Wi-Fi", kCream, 0, true, kDim);
      } else if (A.navOn) {
        add(APhone, 166, 372, 110, 40, R ? "Telefon" : "Phone", kCream, 0, true, kDim);
        add(AEnd, 300, 372, 110, 40, R ? "Stop" : "End", kAmber, 0, true, kDim);
        add(APrev, 92, 168, 56, 56, "\xE2\x80\xB9", kCream, 1, false, kDim);
        add(ANext, 374, 168, 56, 56, "\xE2\x80\xBA", kCream, 1, false, kDim);
      } else if (A.preview) {
        add(AStartNav, 233, 358, 150, 52, R ? "Pornește" : "Start", kMint, 1, true);
        add(APhone, 138, 410, 116, 42, R ? "Telefon" : "Phone", kCream, 0, true, kDim);
        add(AMode, 328, 410, 116, 42, A.routeMode == "walk" ? (R ? "pe jos" : "walk") : A.routeMode == "bike" ? (R ? "bicicletă" : "bike") : (R ? "mașină" : "car"),
            kCream, 0, true, kDim);
      } else {
        add(AGo, 233, 408, 150, 48, R ? "Unde mergem?" : "Where to?", kCream, 0, true);
        add(AMinus, 40, 233, 52, 52, "-", kCream, 1, false);
        add(APlus, 426, 233, 52, 52, "+", kCream, 1, false);
        add(ACenter, 96, 352, 54, 54, "", kCream, 0, false);
      }
      break;
    case View::Music:
      add(APrev, 140, 300, 64, 64, "", kCream, 0, false);
      add(AStart, 233, 300, 84, 84, "", kCream, 0, false);
      add(ANext, 326, 300, 64, 64, "", kCream, 0, false);
      if (A.speaker) {
        std::string s = A.sleepMin ? (R ? "Se oprește în " : "Stops in ") + std::to_string((int)ceilf(A.sleepLeft / 60)) + " min"
                                   : (R ? "Fără oprire" : "No sleep timer");
        add(ASleepT, 233, 392, 220, 44, s, kCream, 0, true, kDim);
      }
      break;
    case View::Games:
      if (A.game < 0) {
        for (int i = 0; i < 3; ++i) add(AGame + i, 233, 170 + i * 76, 330, 68, "", kCream, 0, false);
      } else {
        const bool over = (A.game == 0 && A.tilt.over()) || (A.game == 1 && A.rhythm.over()) ||
                          (A.game == 2 && A.memory.phase() == games::EyeMemory::Phase::Over);
        if (over) {
          add(AAgain, 160, 330, 130, 50, R ? "Încă o dată" : "Again", kMint, 1, true);
          add(AMenu, 306, 330, 120, 50, R ? "Jocuri" : "Games", kCream, 1, true);
        }
      }
      break;
    case View::Focus: {
      const bool idle = A.pomo.phase() == apps::Pomodoro::Phase::Idle;
      add(AStart, 233, 340, 78, 78, "", kCream, 0, false);
      if (!idle) {
        add(ASkip, 128, 400, 100, 42, R ? "Sari" : "Skip", kCream, 0, true, kDim);
        add(AStop, 338, 400, 100, 42, "Stop", kAmber, 0, true, kDim);
      }
      break;
    }
    case View::Breathe:
      if (!A.breathing) {
        const apps::BreathPattern& p = apps::breathPatterns()[A.breathPat];
        add(APattern, 233, 346, 220, 46, R ? p.nameRo : p.name, kCream, 0, true);
        add(ADur, 233, 398, 120, 40, std::to_string(A.breathMin) + " min", kCream, 0, true, kDim);
      }
      break;
    case View::Habits: {
      const int n = (int)A.habits.size(), pages = n > 3 ? (n + 2) / 3 : 1, p = A.habitPage % pages;
      for (int i = p * 3; i < n && i < p * 3 + 3; ++i) add(ARow + i, 233, 160 + (i - p * 3) * 76, 330, 70, "", kCream, 0, false);
      add(ANew, 233, 400, 150, 46, R ? "+ Nou" : "+ New", kCream, 0, true);
      break;
    }
    case View::Stopwatch:
      add(ALap, 150, 352, 72, 72, "", kCream, 0, false);
      add(AStart, 316, 352, 72, 72, "", kCream, 0, false);
      break;
    case View::WorldClock:
      for (int i = 0; i < (int)A.clocks.size(); ++i) add(ARow + i, 233, 138 + i * 66, 330, 60, "", kCream, 0, false);
      if (A.clocks.size() < 4) add(ANew, 233, 138 + (int)A.clocks.size() * 66 + 8, 120, 44, R ? "+ Oraș" : "+ City", kCream, 0, true, kDim);
      break;
    case View::Convert: {
      const std::vector<apps::Unit>& u = apps::units((apps::Quantity)A.q);
      add(AQty, 233, 110, 230, 44, std::string(apps::quantityName((apps::Quantity)A.q, R)) + " \xE2\x80\xBA", kCream, 0, true);
      add(AValue, 200, 184, 230, 64, "", kCream, 0, false);
      add(AFrom, 360, 184, 84, 46, u[A.from].label, kCream, 0, true);
      add(ASwap, 233, 250, 56, 56, "", kCream, 0, false);
      add(ATo, 360, 318, 84, 46, u[A.to].label, kMint, 0, true);
      break;
    }
    case View::FindPhone:
      add(ARing, 233, 318, 150, 120, "", kAmber, 0, false);
      break;
    case View::AppsSettings: {
      const int n = (int)A.order.size(), pages = (n + 3) / 4, p = A.setPage % pages;
      for (int i = p * 4; i < n && i < p * 4 + 4; ++i) {
        add(ARow + i, 262, 150 + (i - p * 4) * 64, 260, 58, "", kCream, 0, false);
        if (i > 0) add(AUp + i, 104, 150 + (i - p * 4) * 64, 52, 52, "", kCream, 0, false);
      }
      break;
    }
    default: break;
  }
}

// ---------------------------------------------------------------- glyphs ---

void Os::drawGlyph(Canvas& cv, AppId a, float cx, float cy, float size, Rgb c, float alpha) {
  static Path p;
  if (!p.reserve(1024)) return;
  p.clear();
  const float s = g_.s(size) / 24.0f, ox = g_.s(cx) - 12 * s, oy = g_.s(cy) - 12 * s, w = 2.0f * fmaxf(1.0f, s * 0.9f);
  auto L = [&](std::initializer_list<float> xy) {
    float b[32];
    int n = 0;
    for (float v : xy) {
      if (n >= 32) break;
      b[n] = (n % 2 == 0 ? ox : oy) + v * s;
      ++n;
    }
    p.stroke(b, n / 2, w);
  };
  auto C = [&](float x, float y, float r, float a0 = 0, float a1 = 2 * kPi) { p.strokeArc(ox + x * s, oy + y * s, r * s, a0, a1, w); };
  switch (a) {
    case AppId::Talk: C(12, 12, 4.4f, -1.0f, 1.0f); C(12, 12, 8.4f, -0.9f, 0.9f); C(12, 12, 4.4f, kPi - 1.0f, kPi + 1.0f); C(12, 12, 8.4f, kPi - 0.9f, kPi + 0.9f); C(12, 12, 0.9f); break;
    case AppId::Today: L({3, 18, 21, 18}); C(12, 18, 5, kPi, 2 * kPi); L({12, 7.2f, 12, 9.5f}); L({5.7f, 10.6f, 7.3f, 12.2f}); L({18.3f, 10.6f, 16.7f, 12.2f}); break;
    case AppId::Maps: L({12, 21, 6.5f, 12.5f}); L({12, 21, 17.5f, 12.5f}); C(12, 9.5f, 6, kPi * 0.82f, kPi * 2.18f); C(12, 9.5f, 2.2f); break;
    case AppId::Weather: C(9, 9, 3.6f); L({9, 3, 9, 4}); L({3, 9, 4, 9}); C(14, 15, 4.6f, kPi * 1.05f, kPi * 1.95f); L({7.5f, 19.5f, 18.5f, 19.5f}); C(18.5f, 16.5f, 3, -kPi / 2, kPi / 2); C(7.5f, 17, 2.5f, kPi / 2, kPi * 1.5f); break;
    case AppId::Calendar: p.strokeRoundRect(ox + 4 * s, oy + 5.5f * s, 16 * s, 14.5f * s, 2.5f * s, w); L({4, 10, 20, 10}); L({8.5f, 3.5f, 8.5f, 7}); L({15.5f, 3.5f, 15.5f, 7}); C(9, 14.5f, 0.6f); C(15, 14.5f, 0.6f); break;
    case AppId::Alarms: C(12, 13, 7.3f); L({12, 9.2f, 12, 13, 14.7f, 14.8f}); L({3.8f, 6.7f, 6.8f, 4.1f}); L({20.2f, 6.7f, 17.2f, 4.1f}); break;
    case AppId::Timer: C(12, 13.6f, 7.1f); L({12, 13.6f, 12, 9.9f}); L({9.8f, 2.9f, 14.2f, 2.9f}); L({12, 2.9f, 12, 6.5f}); break;
    case AppId::Stopwatch: C(12, 13.6f, 7.1f); L({12, 13.6f, 15, 10.5f}); L({9.8f, 2.9f, 14.2f, 2.9f}); L({18.1f, 6.6f, 19.5f, 5.2f}); break;
    case AppId::Focus: C(12, 12, 8.6f); C(12, 12, 4.3f); C(12, 12, 0.6f); break;
    case AppId::Breathe: C(12, 12, 3); C(12, 12, 6.2f, -0.6f, 0.6f); C(12, 12, 6.2f, kPi - 0.6f, kPi + 0.6f); C(12, 12, 9.4f, -0.5f, 0.5f); C(12, 12, 9.4f, kPi - 0.5f, kPi + 0.5f); break;
    case AppId::Habits: L({4, 7.6f, 5.9f, 9.5f, 9.3f, 6}); L({4, 16.6f, 5.9f, 18.5f, 9.3f, 15}); L({12.8f, 7.8f, 20, 7.8f}); L({12.8f, 16.8f, 20, 16.8f}); break;
    case AppId::Notes: L({6, 3.5f, 14.5f, 3.5f, 18, 7, 18, 20.5f, 6, 20.5f, 6, 3.5f}); L({9, 11.5f, 15, 11.5f}); L({9, 14.8f, 15, 14.8f}); break;
    case AppId::Music: L({9, 17.5f, 9, 6.2f, 19.5f, 4, 19.5f, 15.5f}); C(6.6f, 17.5f, 2.4f); C(17.1f, 15.5f, 2.4f); break;
    case AppId::Games: L({12, 3.5f, 14.6f, 8.9f, 20.5f, 9.7f, 16.2f, 13.8f, 17.2f, 19.6f, 12, 16.8f, 6.8f, 19.6f, 7.8f, 13.8f, 3.5f, 9.7f, 9.4f, 8.9f, 12, 3.5f}); break;
    case AppId::WorldClock: C(12, 12, 8.5f); L({3.5f, 12, 20.5f, 12}); C(12, 12, 3.6f, -kPi / 2, kPi / 2); C(12, 12, 3.6f, kPi / 2, kPi * 1.5f); break;
    case AppId::Convert: L({4, 8, 19, 8, 15, 4}); L({20, 16, 5, 16, 9, 20}); break;
    case AppId::FindPhone: p.strokeRoundRect(ox + 7.5f * s, oy + 3 * s, 9 * s, 18 * s, 2 * s, w); L({11, 17.5f, 13, 17.5f}); C(12, 10, 6.5f, -0.5f, 0.5f); C(12, 10, 6.5f, kPi - 0.5f, kPi + 0.5f); break;
    case AppId::Claude: L({4.5f, 7, 9.5f, 12, 4.5f, 17}); L({12, 17.5f, 19.5f, 17.5f}); break;
    case AppId::Device: p.strokeRoundRect(ox + 3 * s, oy + 7.5f * s, 16 * s, 9 * s, 2 * s, w); L({21, 10.5f, 21, 13.5f}); L({6, 12, 11, 12}); break;
    case AppId::MySoul: C(12, 12, 9.5f); C(9, 12.4f, 1.8f); C(15, 12.4f, 1.8f); break;
    default: C(12, 12, 7.6f); L({12, 12, 15.9f, 8.1f}); L({12, 1.6f, 12, 3.2f}); L({22.4f, 12, 20.8f, 12}); L({12, 22.4f, 12, 20.8f}); L({1.6f, 12, 3.2f, 12}); break;
  }
  face_.raster().fill(cv, p, c, alpha * fade_);
}

void Os::drawSky(Canvas& cv, apps::Sky sky, float cx, float cy, float size, float alpha) {
  const float s = g_.s(size) / 24.0f, x = g_.s(cx), y = g_.s(cy);
  const float a = alpha * fade_;
  const Rgb sun = Rgb::hex(0xFFD58A), cloud = kCream;
  auto drawSun = [&](float sx, float sy, float r) {
    cv.ellipse(sx, sy, r, r, sun, a, r * 1.4f, 0.25f);
    for (int i = 0; i < 8; ++i) {
      const float t = i * kPi / 4;
      cv.segment(sx + cosf(t) * r * 1.45f, sy + sinf(t) * r * 1.45f, sx + cosf(t) * r * 1.9f, sy + sinf(t) * r * 1.9f,
                 fmaxf(1.6f, s * 1.4f), sun, a);
    }
  };
  auto drawCloud = [&](float sx, float sy, float k, float al) {
    cv.ellipse(sx - 4.5f * s * k, sy + 1.5f * s * k, 4.2f * s * k, 3.6f * s * k, cloud, al);
    cv.ellipse(sx + 0.5f * s * k, sy - 1.5f * s * k, 5.6f * s * k, 5.2f * s * k, cloud, al);
    cv.ellipse(sx + 5.5f * s * k, sy + 1.6f * s * k, 4.0f * s * k, 3.5f * s * k, cloud, al);
    cv.roundRect(sx - 8.6f * s * k, sy + 1.2f * s * k, sx + 9.4f * s * k, sy + 5.1f * s * k, 2.0f * s * k, cloud, al);
  };
  switch (sky) {
    case apps::Sky::Sun: drawSun(x, y, 5.2f * s); break;
    case apps::Sky::Part:
      drawSun(x - 4 * s, y - 4 * s, 4.0f * s);
      drawCloud(x + 2 * s, y + 3 * s, 0.85f, a * 0.95f);
      break;
    case apps::Sky::Cloud: drawCloud(x, y, 1.0f, a * 0.9f); break;
    case apps::Sky::Rain:
    case apps::Sky::Snow:
    case apps::Sky::Storm:
      drawCloud(x, y - 3 * s, 1.0f, a * 0.9f);
      for (int i = 0; i < 3; ++i) {
        const float dx = (i - 1) * 4.6f * s;
        if (sky == apps::Sky::Rain) cv.segment(x + dx + 0.8f * s, y + 5 * s, x + dx - 0.6f * s, y + 9 * s, fmaxf(1.6f, 1.3f * s), kIce, a);
        else if (sky == apps::Sky::Snow) cv.ellipse(x + dx, y + 7.5f * s, 1.3f * s, 1.3f * s, pal::kWhite, a);
      }
      if (sky == apps::Sky::Storm) {
        static Path p;
        if (p.reserve(64)) {
          p.clear();
          const float pts[] = {x + 1 * s, y + 3 * s, x - 2.5f * s, y + 8.5f * s, x + 0.2f * s, y + 8.5f * s, x - 1.2f * s, y + 12 * s,
                               x + 3.2f * s, y + 6.5f * s, x + 0.6f * s, y + 6.5f * s};
          p.polygon(pts, 6);
          face_.raster().fill(cv, p, kAmber, a);
        }
      }
      break;
    case apps::Sky::Fog:
      for (int i = 0; i < 3; ++i) cv.segment(x - 8 * s + i * s, y - 3 * s + i * 3.5f * s, x + 8 * s - i * s, y - 3 * s + i * 3.5f * s, fmaxf(1.6f, 1.4f * s), cloud, a * 0.8f);
      break;
  }
}

void Os::drawArrow(Canvas& cv, float cx, float cy, float size, float deg, Rgb c, float alpha) {
  // "walk along the line, then turn this way": a stem up from the bottom, then the turn, then the head
  static Path p;
  if (!p.reserve(512)) return;
  p.clear();
  const float s = g_.s(size), x = g_.s(cx), y = g_.s(cy), w = s * 0.14f;
  const float t = deg * kPi / 180.0f;
  const float jx = x, jy = y + s * 0.05f;  // the turn point
  const float L = s * 0.42f;
  const float ex = jx + sinf(t) * L, ey = jy - cosf(t) * L;
  const float stem[] = {x, y + s * 0.48f, jx, jy, ex, ey};
  p.stroke(stem, 3, w);
  // the head
  const float hx = sinf(t), hy = -cosf(t), nx = -hy, ny = hx, hl = s * 0.22f, hw = s * 0.2f;
  const float head[] = {ex + hx * hl * 0.9f, ey + hy * hl * 0.9f, ex + nx * hw - hx * hl * 0.25f, ey + ny * hw - hy * hl * 0.25f,
                        ex - nx * hw - hx * hl * 0.25f, ey - ny * hw - hy * hl * 0.25f};
  p.polygon(head, 3);
  face_.raster().fill(cv, p, c, alpha * fade_);
}

// ------------------------------------------------------------- dispatch ---

bool Os::appsDraw(Canvas& cv) {
  switch (view_) {
    case View::Control: drawControl(cv); return true;
    case View::Weather: drawWeather(cv); return true;
    case View::Maps: drawMaps(cv); return true;
    case View::Calendar: drawCalendar(cv); return true;
    case View::Music: drawMusic(cv); return true;
    case View::Games: drawGames(cv); return true;
    case View::Focus: drawFocus(cv); return true;
    case View::Breathe: drawBreathe(cv); return true;
    case View::Habits: drawHabits(cv); return true;
    case View::Stopwatch: drawStopwatch(cv); return true;
    case View::WorldClock: drawWorldClock(cv); return true;
    case View::Convert: drawConvert(cv); return true;
    case View::FindPhone: drawFindPhone(cv); return true;
    case View::Device: drawDevice(cv); return true;
    case View::AppsSettings: drawAppsSettings(cv); return true;
    default: return false;
  }
}

// a "needs" card with an optional QR (the /me/where page) — never a dead end
static std::string meWhere(const NetInfo& n, const std::string& chip) {
  std::string id = "soul-";
  for (char c : chip)
    if (c != ':') id += (char)(c >= 'A' && c <= 'F' ? c - 'A' + 'a' : c);
  return "https://" + (n.cloudHost.empty() ? std::string("soul.example") : n.cloudHost) + "/me/where?d=" + id;
}

// ---------------------------------------------------------------- control ---

void Os::drawControl(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  std::string top = hm(now_);
  if (power_.batPct >= 0) top += "  \xC2\xB7  " + std::to_string(power_.batPct) + "%";
  if (A.dnd) top += R ? "  \xC2\xB7  liniște" : "  \xC2\xB7  quiet";
  rimTop(cv, top, kCream, kDim);
  // the two rim dials: light up the left rim, volume up the right rim
  const float cx = g_.cx(), cy = g_.cy(), r = g_.s(212);
  const float b0 = 128 * kPi / 180, b1 = 232 * kPi / 180;  // light: bottom-left (low) up to top-left (high)
  glass().capsuleArc(cv, cx, cy, r, g_.s(13), b0, b1, gs());
  const float bv = set_.bright == 0 ? 0.5f : (set_.bright - 1) / 2.0f;
  const float bk = b0 + (b1 - b0) * bv;
  face_.raster().ring(cv, cx, cy, r, g_.s(5), kCream, (set_.bright == 0 ? 0.45f : 0.9f) * fade_, b0, bk);
  cv.ellipse(cx + r * cosf(bk), cy + r * sinf(bk), g_.s(9), g_.s(9), set_.bright == 0 ? kAmber : kCream, fade_, 6, 0.4f);
  const float v0 = 52 * kPi / 180, v1 = -52 * kPi / 180;  // volume: bottom-right (low) to top-right (high)
  glass().capsuleArc(cv, cx, cy, r, g_.s(13), v1, v0, gs());
  const float vk = v0 - (v0 - v1) * A.volume;
  if (A.volume > 0.01f) face_.raster().ring(cv, cx, cy, r, g_.s(5), kIce, 0.9f * fade_, vk, v0);
  cv.ellipse(cx + r * cosf(vk), cy + r * sinf(vk), g_.s(9), g_.s(9), kIce, fade_, 6, 0.4f);
  static const char* const kBr[2][4] = {{"auto", "low", "mid", "high"}, {"auto", "mică", "medie", "mare"}};
  textAt(cv, fonts::small(), 74, 196, R ? "lumină" : "light", kCream, kFaint);
  textAt(cv, fonts::small(), 74, 222, kBr[R][set_.bright % 4], kCream, kDim);
  textAt(cv, fonts::small(), 392, 196, "vol", kIce, kFaint);
  textAt(cv, fonts::small(), 392, 222, std::to_string((int)lroundf(A.volume * 100)), kIce, kDim);
  // four tiles
  struct T {
    const char* en;
    const char* ro;
    bool on;
    Rgb c;
    AppId g;
  } tiles[4] = {{"Quiet", "Liniște", A.dnd, kAmber, AppId::Today},
                {"Large text", "Text mare", set_.largeText != 0, kMint, AppId::Notes},
                {"Find phone", "Telefonul", A.findState == 1 || A.findState == 2, kAmber, AppId::FindPhone},
                {"Sleep", "Somn", false, kCream, AppId::MySoul}};
  static const float kx[] = {180, 286, 180, 286}, ky[] = {200, 200, 296, 296};
  for (int i = 0; i < 4; ++i) {
    const T& t = tiles[i];
    glassPanel(cv, kx[i] - 48, ky[i] - 40, kx[i] + 48, ky[i] + 40, 24, t.on ? gsAccent(t.c, 0.35f, 0.16f) : gs());
    if (i == 0) {  // a crescent
      cv.ellipse(g_.s(kx[i]), g_.s(ky[i] - 12), g_.s(10), g_.s(10), t.on ? kAmber : kCream, fade_);
      cv.ellipse(g_.s(kx[i] + 5), g_.s(ky[i] - 16), g_.s(9), g_.s(9), kDark, fade_);
    } else if (i == 1) {
      textAt(cv, fonts::large(), kx[i], ky[i] - 12, "Aa", t.on ? kMint : kCream, 1);
    } else if (i == 2) {
      drawGlyph(cv, AppId::FindPhone, kx[i], ky[i] - 12, 24, t.on ? kAmber : kCream, 1);
    } else {
      cv.arc(g_.s(kx[i] - 7), g_.s(ky[i] - 16), g_.s(5), 0.2f, kPi - 0.2f, g_.s(2.2f), kCream, fade_);
      cv.arc(g_.s(kx[i] + 7), g_.s(ky[i] - 16), g_.s(5), 0.2f, kPi - 0.2f, g_.s(2.2f), kCream, fade_);
    }
    textAt(cv, fonts::small(), kx[i], ky[i] + 20, R ? t.ro : t.en, t.on ? t.c : kCream, t.on ? 1 : kDim);
  }
  buildItems(items_);
  for (const Item& it : items_)
    if (it.id == AAuto) {
      std::vector<Item> one(1, it);
      drawItems(cv, one);
    }
  const std::string ai = std::string("AI \xC2\xB7 ") +
                         (aiMode() == AiMode::None ? (R ? "fără" : "none") : aiMode() == AiMode::Cloud ? "SOUL Cloud"
                          : aiMode() == AiMode::ChatGpt ? "ChatGPT" : "Claude");
  rimBottomCap(cv, ai, aiMode() == AiMode::None ? kCream : kAmber, aiMode() == AiMode::None ? kDim : 1, false);
}

// ------------------------------------------------------------- today stack ---

void Os::drawTodayStack(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, std::string(R ? "AZI \xC2\xB7 " : "TODAY \xC2\xB7 ") + upper(dayName(now_, R)) + " \xC2\xB7 " + hm(now_), kCream, kDim);
  const int n = 6, c = A.card % n;
  // the card under it peeks out, smaller (a teleprompter of glass)
  if (c + 1 < n) glassPanel(cv, 104, 334, 362, 366, 18, gs(0.5f));
  glassPanel(cv, 66, 150, 400, 330, 30, gs());
  // which card is it: dots on the left rim
  for (int i = 0; i < n; ++i) {
    const float a = kPi + (i - (n - 1) / 2.0f) * 0.1f;
    cv.ellipse(g_.cx() + g_.s(214) * cosf(a), g_.cy() + g_.s(214) * sinf(a), g_.s(i == c ? 4.5f : 3), g_.s(i == c ? 4.5f : 3),
               kCream, (i == c ? 0.95f : 0.35f) * fade_);
  }
  char b[96];
  std::string label, big, sub;
  switch (c) {
    case 0: {  // now
      label = R ? "ACUM" : "NOW";
      big = hm(now_);
      const std::string na = nextAlarmText();
      sub = na.empty() ? (R ? "nicio alarmă" : "no alarm set") : (R ? "alarmă " : "alarm ") + na;
      textAt(cv, fonts::small(), 233, 178, label, kCream, kFaint);
      textAt(cv, fonts::digits(), 233, 242, big, kCream);
      textAt(cv, fonts::small(), 233, 300, fit(fonts::small(), sub, g_.s(300)), kCream, kDim);
      break;
    }
    case 1: {  // weather
      textAt(cv, fonts::small(), 233, 178, R ? "VREMEA" : "WEATHER", kCream, kFaint);
      if (A.weather.ok) {
        drawSky(cv, A.weather.sky, 176, 238, 52, 1);
        snprintf(b, sizeof b, "%d\xC2\xB0", A.weather.t);
        textAt(cv, fonts::large(), 270, 236, b, kCream);
        snprintf(b, sizeof b, "%s \xC2\xB7 %d\xC2\xB0 / %d\xC2\xB0", A.weather.word.c_str(), A.weather.hi, A.weather.lo);
        textAt(cv, fonts::small(), 233, 300, fit(fonts::small(), b, g_.s(300)), kCream, kDim);
      } else {
        textAt(cv, fonts::text(), 233, 236, A.wxWait ? (R ? "Întreb cerul…" : "Asking the sky…") : (R ? "Atinge pentru vreme" : "Tap for the weather"), kCream, kDim);
      }
      break;
    }
    case 2: {  // the next event
      textAt(cv, fonts::small(), 233, 178, R ? "URMEAZĂ" : "NEXT", kCream, kFaint);
      const int i = A.agenda.ok ? A.agenda.next(now_) : -1;
      if (i >= 0) {
        const apps::Event& e = A.agenda.events[i];
        textAt(cv, fonts::large(), 233, 230, e.allDay ? (R ? "toată ziua" : "all day") : hm(e.start), kCream);
        textAt(cv, fonts::text(), 233, 274, fit(fonts::text(), e.title, g_.s(300)), kCream);
        if (!e.place.empty()) textAt(cv, fonts::small(), 233, 304, fit(fonts::small(), e.place, g_.s(290)), kCream, kFaint);
      } else {
        textAt(cv, fonts::text(), 233, 236, A.agenda.ok ? (R ? "Nimic în calendar" : "Nothing on the calendar") : (R ? "Calendarul tău" : "Your calendar"), kCream, kDim);
        if (!A.agenda.ok) textAt(cv, fonts::small(), 233, 276, R ? "îl legi din /me/where" : "link it on /me/where", kCream, kFaint);
      }
      break;
    }
    case 3: {  // focus / timer / a reminder
      textAt(cv, fonts::small(), 233, 178, "FOCUS", kCream, kFaint);
      if (A.pomo.phase() != apps::Pomodoro::Phase::Idle) {
        textAt(cv, fonts::digits(), 233, 242, apps::Stopwatch::format(A.pomo.left(), false), kCream);
        snprintf(b, sizeof b, R ? "runda %d din %d" : "round %d of %d", A.pomo.round(), A.pomo.rounds);
        textAt(cv, fonts::small(), 233, 300, b, kCream, kDim);
      } else if (timerRun_) {
        snprintf(b, sizeof b, "%d:%02d", timerLeft() / 60, timerLeft() % 60);
        textAt(cv, fonts::digits(), 233, 242, b, kCream);
        textAt(cv, fonts::small(), 233, 300, R ? "minutar" : "timer", kCream, kDim);
      } else if (!rems_.empty()) {
        textAt(cv, fonts::large(), 233, 230, hm(rems_.front().when), kCream);
        textAt(cv, fonts::text(), 233, 276, fit(fonts::text(), rems_.front().text, g_.s(300)), kCream, kDim);
      } else {
        textAt(cv, fonts::text(), 233, 236, R ? "25 de minute de liniște?" : "25 quiet minutes?", kCream, kDim);
        textAt(cv, fonts::small(), 233, 276, R ? "atinge: Focus" : "tap: Focus", kCream, kFaint);
      }
      break;
    }
    case 4: {  // habits
      textAt(cv, fonts::small(), 233, 178, R ? "OBICEIURI" : "HABITS", kCream, kFaint);
      int d = 0;
      for (const apps::Habit& h : A.habits) d += h.doneOn(now_ / 86400);
      snprintf(b, sizeof b, "%d / %d", d, (int)A.habits.size());
      textAt(cv, fonts::large(), 233, 232, b, d == (int)A.habits.size() && d ? kMint : kCream);
      const int total = (int)A.habits.size();
      for (int i = 0; i < total; ++i) {
        const float x = 233 + (i - (total - 1) / 2.0f) * 30;
        const bool on = A.habits[i].doneOn(now_ / 86400);
        cv.ellipse(g_.s(x), g_.s(282), g_.s(8), g_.s(8), on ? kMint : kCream, (on ? 1.0f : 0.25f) * fade_, on ? 5 : 0, 0.35f);
      }
      break;
    }
    default: {  // SOUL itself
      textAt(cv, fonts::small(), 233, 178, "SOUL", kCream, kFaint);
      if (power_.batPct >= 0) snprintf(b, sizeof b, "%d%%%s", power_.batPct, power_.charging ? "+" : "");
      else snprintf(b, sizeof b, "USB");
      textAt(cv, fonts::large(), 233, 230, b, power_.charging ? kMint : kCream);
      const std::string s = claude_.prompt ? (R ? "Claude te așteaptă" : "Claude needs you")
                            : net_.connected ? (R ? "Wi-Fi " : "Wi-Fi ") + net_.ssid : (R ? "fără Wi-Fi" : "no Wi-Fi");
      textAt(cv, fonts::small(), 233, 280, fit(fonts::small(), s, g_.s(290)), claude_.prompt ? kAmber : kCream, kDim);
      break;
    }
  }
  rimBottom(cv, c == 0 ? (R ? "glisează în sus · atinge = deschide" : "swipe up · tap to open") : (R ? "atinge = deschide" : "tap to open"),
            kCream, kFaint);
}

// ---------------------------------------------------------------- weather ---

void Os::drawWeather(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const apps::Weather& W = A.weather;
  if (!W.ok) {
    rimTop(cv, R ? "VREMEA" : "WEATHER", kCream, kDim);
    if (!cloudOk(net_)) {
      glassPanel(cv, 70, 160, 396, 320, 30, gs());
      textAt(cv, fonts::text(), 233, 196, R ? "Vremea vine prin SOUL Cloud" : "Weather comes via SOUL Cloud", kCream);
      std::string l[3];
      const int n = wrapLines(fonts::small(), R ? "Leagă SOUL de contul tău: Setări › AI › SOUL Cloud." : "Pair SOUL with your account: Settings › AI › SOUL Cloud.", g_.s(300), l, 3);
      for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 240 + i * 26, l[i], kCream, kDim);
    } else if (A.wxWait) {
      const float pulse = 0.55f + 0.35f * sinf(t_ * 3.0f);
      drawSky(cv, apps::Sky::Part, 233, 240, 64, pulse);
      textAt(cv, fonts::text(), 233, 316, R ? "Întreb cerul…" : "Asking the sky…", kCream, pulse);
    } else if (A.wxErr == 409) {  // no location yet
      textAt(cv, fonts::text(), 233, 130, R ? "Unde ești?" : "Where are you?", kCream);
      textAt(cv, fonts::small(), 233, 158, R ? "SOUL n-are GPS: spune-i din telefon" : "SOUL has no GPS: tell it from your phone", kCream, kDim);
      drawQr(cv, meWhere(net_, birth_.chip), 233, 262, 150);
      rimBottom(cv, R ? "scanează: Trimite locația" : "scan: Share my location", kCream, kFaint);
    } else {
      glassPanel(cv, 70, 170, 396, 330, 30, gsAccent(kAmber, 0.2f, 0.04f));
      textAt(cv, fonts::text(), 233, 204, A.wxErr == 501 ? (R ? "Vremea nu e pornită în cloud" : "Weather isn't set up in the cloud")
                                       : A.wxErr < 0 ? (R ? "Fără internet" : "No internet") : (R ? "Vremea nu răspunde" : "No answer from the weather"),
             kAmber);
      textAt(cv, fonts::small(), 233, 240, A.wxErr < 0 ? (R ? "încerc când revin online" : "I'll try when I'm back online") : (R ? "mai încerc puțin mai târziu" : "I'll try again in a bit"), kCream, kDim);
      buildItems(items_);
      drawItems(cv, items_);
    }
    return;
  }
  std::string top = upper(W.place.empty() ? std::string(R ? "aici" : "here") : W.place);
  const std::string age = now_ - W.at > 1800 ? ago(now_, W.at, R) : "";
  if (!age.empty()) top += " \xC2\xB7 " + age;
  rimTop(cv, top, kCream, kDim);
  char b[64];
  if (A.wxPage == 0) {
    drawSky(cv, W.sky, 166, 196, 64, 1);
    snprintf(b, sizeof b, "%d", W.t);
    const int tw = Canvas::measureText(fonts::digits(), b);
    textAt(cv, fonts::digits(), 284, 196, b, kCream);
    cv.ring(g_.s(284) + tw * 0.5f + g_.s(10), g_.s(166), g_.s(6), g_.s(2.5f), kCream, fade_);  // the degree sign
    snprintf(b, sizeof b, "%s \xC2\xB7 %d\xC2\xB0 / %d\xC2\xB0", W.word.c_str(), W.hi, W.lo);
    textAt(cv, fonts::text(), 233, 262, fit(fonts::text(), b, g_.s(330)), kCream);
    snprintf(b, sizeof b, R ? "se simte %d\xC2\xB0 \xC2\xB7 ploaie %d%% \xC2\xB7 vânt %d km/h" : "feels %d\xC2\xB0 \xC2\xB7 rain %d%% \xC2\xB7 wind %d km/h", W.feels, W.rain, W.wind);
    textAt(cv, fonts::small(), 233, 292, fit(fonts::small(), b, g_.s(320)), kCream, kDim);
    // the next hours on a glass band
    glassPanel(cv, 60, 316, 406, 404, 30, gs());
    const int n = (int)W.hours.size();
    for (int i = 0; i < n; ++i) {
      const float x = 233 + (i - (n - 1) / 2.0f) * 54;
      textAt(cv, fonts::small(), x, 334, W.hours[i].hh, kCream, kFaint);
      drawSky(cv, W.hours[i].sky, x, 360, 18, 0.95f);
      snprintf(b, sizeof b, "%d\xC2\xB0", W.hours[i].t);
      textAt(cv, fonts::small(), x, 388, b, kCream);
    }
  } else {
    textAt(cv, fonts::small(), 233, 118, R ? "ZILELE URMĂTOARE" : "THE NEXT DAYS", kCream, kFaint);
    for (int i = 0; i < (int)W.days.size(); ++i) {
      const float y = 170 + i * 72;
      glassPanel(cv, 70, y - 30, 396, y + 30, 22, gs());
      textAt(cv, fonts::text(), 112, y, W.days[i].name, kCream, 1, Align::Left);
      drawSky(cv, W.days[i].sky, 222, y, 30, 1);
      snprintf(b, sizeof b, "%d\xC2\xB0 / %d\xC2\xB0", W.days[i].hi, W.days[i].lo);
      textAt(cv, fonts::text(), 370, y, b, kCream, 1, Align::Right);
    }
  }
  rimBottom(cv, std::string(A.wxPage ? (R ? "‹ azi" : "‹ today") : (R ? "zilele ›" : "days ›")) + "  \xC2\xB7  Open-Meteo", kCream, kFaint);
}

// ------------------------------------------------------------------- maps ---

// the map lives in its own layer (PSRAM): painted only when the view moves, blitted under any clip
static std::vector<uint16_t> gMapLayer;
static bool gMapLayerOk = false;

void Os::mapsPaintLayer(Canvas& cv) {
  AppsState& A = apps_;
  const int W = cv.width(), H = cv.height();
  if (gMapLayer.size() != (size_t)W * H) {
    gMapLayer.assign((size_t)W * H, 0);
    gMapLayerOk = false;
  }
  if (A.mapDirty || !gMapLayerOk) {
    Canvas layer(W, H, gMapLayer.data());
    static maps::MapPainter painter;
    A.view.screenW = W;
    A.view.screenH = H;
    painter.paint(layer, A.bundle, A.view, &fonts::small());
    A.mapDirty = false;
    gMapLayerOk = true;
  }
  const Rect& c = cv.clipRect();
  for (int y = c.y0; y < c.y1; ++y)
    memcpy(cv.data() + y * W + c.x0, gMapLayer.data() + y * W + c.x0, (size_t)(c.x1 - c.x0) * 2);
  cv.markDirty(c);
}

void Os::drawMaps(Canvas& cv) {
  const bool R = ro();
  AppsState& A = apps_;
  char b[96];
  if (!A.haveFix && A.bundle.empty()) {  // SOUL does not know where it is: say how to tell it
    rimTop(cv, R ? "HĂRȚI" : "MAPS", kCream, kDim);
    if (!cloudOk(net_)) {
      glassPanel(cv, 66, 150, 400, 330, 30, gs());
      textAt(cv, fonts::text(), 233, 184, R ? "Hărțile vin prin SOUL Cloud" : "Maps come via SOUL Cloud", kCream);
      std::string l[4];
      const int n = wrapLines(fonts::small(), R ? "SOUL n-are GPS. Leagă-l de cont (Setări › AI › SOUL Cloud) și trimite-i locația din telefon."
                                                : "SOUL has no GPS. Pair it (Settings › AI › SOUL Cloud), then share your location from your phone.",
                              g_.s(300), l, 4);
      for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 224 + i * 26, l[i], kCream, kDim);
      return;
    }
    textAt(cv, fonts::text(), 233, 128, A.whereWait ? (R ? "Unde sunt?…" : "Where am I?…") : (R ? "Unde ești?" : "Where are you?"), kCream);
    textAt(cv, fonts::small(), 233, 156, R ? "N-am GPS: telefonul tău îmi spune" : "No GPS here: your phone tells me", kCream, kDim);
    drawQr(cv, meWhere(net_, birth_.chip), 233, 258, 146);
    buildItems(items_);
    drawItems(cv, items_);
    rimBottom(cv, R ? "scanează · Trimite locația" : "scan · Share my location", kCream, kFaint);
    return;
  }
  mapsPaintLayer(cv);
  const maps::MapView& v = A.view;
  // the route
  static maps::MapPainter mp;
  if (A.route.valid() && (A.navOn || A.preview)) {
    int from = 0;
    if (A.navOn) {
      const double along = A.nav.alongM();
      while (from < A.route.points() - 1 && A.route.cum[from + 1] <= along) ++from;
    }
    mp.paintRoute(cv, A.route, v, A.navOn ? from : -1, fade_);
  }
  // you
  if (A.haveFix) {
    double wx, wy;
    double la = A.fix.lat, lo = A.fix.lon;
    if (A.navOn && !A.nav.offRoute() && A.nav.hasFix()) A.nav.position(la, lo);
    maps::worldPx(la, lo, v.z, wx, wy);
    float sx, sy;
    v.toScreen(wx, wy, sx, sy);
    const float accPx = (float)(A.fix.accM / maps::metresPerPx(la, v.z) * v.scale);
    mp.paintYou(cv, sx, sy, accPx, t_);
  }
  // a soft vignette at the rim keeps the glass readable over the map
  face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(226), g_.s(22), kDark, 0.55f);
  if (A.sendSheet) {  // "Send to phone": a QR that opens Google Maps
    glassPanel(cv, 80, 70, 386, 396, 40, gs());
    textAt(cv, fonts::text(), 233, 106, R ? "Pe telefon" : "On your phone", kCream);
    drawQr(cv, A.sendUrl, 233, 236, 196);
    textAt(cv, fonts::small(), 233, 364, R ? "scanează: se deschide Google Maps" : "scan: opens Google Maps", kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    return;
  }
  if (A.navOn && A.route.valid()) {
    const int s = A.nav.step();
    const maps::Step& st = A.route.steps[s < (int)A.route.steps.size() ? s : (int)A.route.steps.size() - 1];
    const bool off = A.nav.offRoute(), arrived = A.nav.arrived();
    // the step card: the arrow (relative to the line you walk: SOUL has no compass), the distance, the street
    glassPanel(cv, 118, 92, 348, 238, 34, arrived ? gsAccent(kMint, 0.4f, 0.12f) : off ? gsAccent(kAmber, 0.4f, 0.1f) : gs());
    if (arrived) {
      textAt(cv, fonts::large(), 233, 150, R ? "Ai ajuns" : "You're there", kMint);
      textAt(cv, fonts::small(), 233, 192, fit(fonts::small(), A.route.to, g_.s(210)), kCream, kDim);
    } else if (off) {
      textAt(cv, fonts::text(), 233, 140, R ? "Ai ieșit de pe traseu" : "Off the route", kAmber);
      textAt(cv, fonts::small(), 233, 172, R ? "întoarce-te la linia portocalie" : "head back to the amber line", kCream, kDim);
      textAt(cv, fonts::small(), 233, 198, R ? "sau ține apăsat: oprește" : "or hold: end it", kCream, kFaint);
    } else {
      drawArrow(cv, 180, 162, 62, A.route.turnAngle(s), kCream, 1);
      const int d = (int)A.nav.toTurnM();
      if (d >= 1000) snprintf(b, sizeof b, "%.1f km", d / 1000.0);
      else snprintf(b, sizeof b, "%d m", (d + 5) / 10 * 10);
      textAt(cv, fonts::large(), 282, 140, b, kCream);
      textAt(cv, fonts::small(), 282, 176, maps::turnWord(st.turn, R), kCream, kDim);
      const std::string street = st.street.empty() ? std::string() : st.street;
      if (!street.empty()) textAt(cv, fonts::small(), 233, 214, fit(fonts::small(), street, g_.s(210)), kCream, kFaint);
    }
    buildItems(items_);
    drawItems(cv, items_);
    const int eta = A.nav.etaS();
    const uint32_t at = now_ + (uint32_t)eta;
    const float left = A.nav.leftM();
    if (left >= 1000) snprintf(b, sizeof b, "%s %s \xC2\xB7 %.1f km", R ? "ajungi la" : "there at", hm(at).c_str(), left / 1000.0f);
    else snprintf(b, sizeof b, "%s %s \xC2\xB7 %d m", R ? "ajungi la" : "there at", hm(at).c_str(), (int)left);
    rimBottom(cv, b, kCream, kDim);
    if (!A.nav.hasFix()) rimTop(cv, R ? "atinge cardul la fiecare viraj" : "tap the card at each turn", kCream, kFaint);
    return;
  }
  if (A.preview && A.route.valid()) {
    glassPanel(cv, 92, 74, 374, 150, 30, gs());
    textAt(cv, fonts::text(), 233, 98, fit(fonts::text(), A.route.to, g_.s(250)), kCream);
    const int min = (A.route.durS + 59) / 60;
    snprintf(b, sizeof b, "%.1f km \xC2\xB7 %d min \xC2\xB7 %s", A.route.distM / 1000.0, min, hm(now_ + (uint32_t)A.route.durS).c_str());
    textAt(cv, fonts::small(), 233, 128, b, kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    return;
  }
  // browsing: the zoom on the rim, the place, where to
  std::string top;
  if (A.whereWait && !A.haveFix) top = R ? "unde sunt?…" : "where am I?…";
  else if (A.mapErr < 0) top = (R ? "offline · hartă de la " : "offline · map from ") + hm(A.mapAt);
  else if (A.mapErr == 501) top = R ? "fără date de hartă în cloud" : "no map data in the cloud";
  else if (!A.fixLabel.empty()) top = A.fixLabel;
  else if (A.haveFix) {
    const uint32_t age = now_ > A.fix.at ? now_ - A.fix.at : 0;
    snprintf(b, sizeof b, "%s \xC2\xB7 ~%d m%s%s", A.fixSrc == "wifi" ? "Wi-Fi" : (R ? "telefon" : "phone"), (int)A.fix.accM,
             age > 300 ? " \xC2\xB7 " : "", age > 300 ? ago(now_, A.fix.at, R).c_str() : "");
    top = b;
  }
  if (!top.empty()) rimTop(cv, top, A.mapErr ? kAmber : kCream, kDim);
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id == APlus || it.id == AMinus || it.id == ACenter) {
      glass().orb(cv, g_.s(it.x), g_.s(it.y), g_.s(it.w * 0.5f), gs());
      if (it.id == ACenter) {
        cv.ring(g_.s(it.x), g_.s(it.y), g_.s(9), g_.s(2.2f), A.followMe ? kIce : kCream, fade_);
        cv.ellipse(g_.s(it.x), g_.s(it.y), g_.s(3), g_.s(3), A.followMe ? kIce : kCream, fade_);
      } else {
        textAt(cv, fonts::text(), it.x, it.y - 2, it.label, kCream);
      }
    }
  }
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  drawItems(cv, pills);
  snprintf(b, sizeof b, "z%d", v.z);
  textAt(cv, fonts::small(), 396, 300, b, kCream, kFaint);
  rimBottom(cv, "map data: OpenStreetMap", kCream, 0.34f);  // ODbL attribution
}

// --------------------------------------------------------------- calendar ---

void Os::drawCalendar(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, std::string(R ? "AGENDA · " : "AGENDA · ") + upper(dayName(now_, R)), kCream, kDim);
  if (!A.agenda.ok) {
    if (A.calWait) {
      const float pulse = 0.55f + 0.35f * sinf(t_ * 3.0f);
      textAt(cv, fonts::text(), 233, 240, R ? "Citesc calendarul…" : "Reading your calendar…", kCream, pulse);
    } else if (!cloudOk(net_) || A.calErr == 404) {
      textAt(cv, fonts::text(), 233, 132, R ? "Leagă-ți calendarul" : "Link your calendar", kCream);
      textAt(cv, fonts::small(), 233, 160, R ? "pe telefon: adresa ICS, doar citire" : "on your phone: its ICS address, read-only", kCream, kDim);
      if (cloudOk(net_)) drawQr(cv, meWhere(net_, birth_.chip), 233, 262, 146);
      else textAt(cv, fonts::small(), 233, 230, R ? "întâi: Setări › AI › SOUL Cloud" : "first: Settings › AI › SOUL Cloud", kAmber);
    } else {
      textAt(cv, fonts::text(), 233, 220, A.calErr < 0 ? (R ? "Fără internet" : "No internet") : (R ? "Calendarul nu răspunde" : "The calendar didn't answer"), kAmber);
      buildItems(items_);
      drawItems(cv, items_);
    }
    return;
  }
  if (A.agenda.events.empty()) {
    glassPanel(cv, 80, 190, 386, 290, 30, gs());
    textAt(cv, fonts::text(), 233, 226, R ? "Nimic în 7 zile" : "Nothing in 7 days", kCream);
    textAt(cv, fonts::small(), 233, 258, R ? "zile libere" : "free days", kMint, kDim);
    return;
  }
  if (A.calSel >= 0 && A.calSel < (int)A.agenda.events.size()) {
    const apps::Event& e = A.agenda.events[A.calSel];
    std::string l[3];
    const int n = wrapLines(fonts::text(), e.title, g_.s(300), l, 3);
    glassPanel(cv, 66, 120, 400, 196 + n * 32 + (e.place.empty() ? 0 : 30), 32, gs());
    std::string when = std::string(dayName(e.start, R)) + " " + (e.allDay ? (R ? "toată ziua" : "all day") : hm(e.start) + "\xE2\x80\x93" + hm(e.end));
    textAt(cv, fonts::small(), 233, 148, when, kCream, kDim);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::text(), 233, 186 + i * 32, l[i], kCream);
    if (!e.place.empty()) textAt(cv, fonts::small(), 233, 190 + n * 32, fit(fonts::small(), e.place, g_.s(300)), kCream, kFaint);
    rimBottom(cv, R ? "atinge: înapoi" : "tap: back", kCream, kFaint);
    return;
  }
  buildItems(items_);
  const uint32_t today = now_ / 86400;
  for (const Item& it : items_) {
    if (it.id < ARow) continue;
    const apps::Event& e = A.agenda.events[it.id - ARow];
    const bool soon = !e.allDay && e.start > now_ && e.start - now_ < 3600;
    glassPanel(cv, 66, it.y - 33, 400, it.y + 33, 22, soon ? gsAccent(kAmber, 0.25f, 0.06f) : gs());
    const uint32_t d = e.start / 86400;
    const std::string day = d == today ? std::string() : dayName(e.start, R);
    textAt(cv, fonts::text(), 128, it.y - 9, e.allDay ? (R ? "zi" : "day") : hm(e.start), soon ? kAmber : kCream, 1);
    textAt(cv, fonts::small(), 128, it.y + 17, day, kCream, kFaint);
    textAt(cv, fonts::small(), 178, it.y - 9, fit(fonts::small(), e.title, g_.s(205)), kCream, 1, Align::Left);
    if (!e.place.empty()) textAt(cv, fonts::small(), 178, it.y + 17, fit(fonts::small(), e.place, g_.s(200)), kCream, kFaint, Align::Left);
  }
  rimBottom(cv, A.agenda.events.size() > 3 ? (R ? "glisează în sus: mai multe" : "swipe up: more") : (R ? "doar citire · din telefonul tău" : "read-only · from your phone"),
            kCream, kFaint);
}

// ------------------------------------------------------------------ music ---

void Os::drawMusic(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, R ? "SUNETE DE FOCUS" : "FOCUS SOUNDS", kCream, kDim);
  if (!A.speaker) {
    glassPanel(cv, 66, 138, 400, 352, 32, gs());
    textAt(cv, fonts::text(), 233, 170, R ? "SOUL-ul ăsta n-are difuzor" : "This SOUL has no speaker", kCream);
    std::string l[6];
    const int n = wrapLines(fonts::small(),
                            R ? "Pe SOUL M se adaugă amplificatorul I2S (MAX98357A). Muzica de pe telefon: vine cu aplicația SOUL "
                                "(iPhone: Apple Media Service prin Bluetooth)."
                              : "SOUL M takes an I2S amp (MAX98357A). Your phone's music: coming with the SOUL app "
                                "(iPhone: Apple Media Service over Bluetooth).",
                            g_.s(310), l, 6);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 212 + i * 26, l[i], kCream, kDim);
    return;
  }
  const char* name = SoundGen::name(A.sound.kind(), R);
  textAt(cv, fonts::large(), 233, 170, name, A.playing ? kMint : kCream);
  static const char* const en[] = {"on a window, far thunder", "deep and even", "slow waves", "a crackling fire"};
  static const char* const r[] = {"pe geam, tunet departe", "adânc și egal", "valuri încete", "un foc care trosnește"};
  textAt(cv, fonts::small(), 233, 210, (R ? r : en)[A.sound.kind() % 4], kCream, kFaint);
  // prev / play / next as glass orbs
  glass().orb(cv, g_.s(140), g_.s(300), g_.s(30), gs());
  glass().orb(cv, g_.s(233), g_.s(300), g_.s(42), A.playing ? gsAccent(kMint, 0.4f, 0.14f) : gs());
  glass().orb(cv, g_.s(326), g_.s(300), g_.s(30), gs());
  static Path p;
  if (p.reserve(256)) {
    p.clear();
    const float x = g_.s(233), y = g_.s(300), s = g_.s(14);
    if (A.playing) {
      p.roundRect(x - s * 0.8f, y - s, s * 0.55f, s * 2, s * 0.15f);
      p.roundRect(x + s * 0.25f, y - s, s * 0.55f, s * 2, s * 0.15f);
    } else {
      const float tri[] = {x - s * 0.6f, y - s, x + s, y, x - s * 0.6f, y + s};
      p.polygon(tri, 3);
    }
    const float a = g_.s(140), c = g_.s(326), k = g_.s(9);
    const float pv[] = {a + k * 0.7f, y - k, a - k * 0.6f, y, a + k * 0.7f, y + k};
    const float nx[] = {c - k * 0.7f, y - k, c + k * 0.6f, y, c - k * 0.7f, y + k};
    p.polygon(pv, 3);
    p.polygon(nx, 3);
    face_.raster().fill(cv, p, A.playing ? kMint : kCream, fade_);
  }
  // the volume on the right rim (set it in Control)
  const float v0 = 52 * kPi / 180, vk = v0 - 104 * kPi / 180 * A.volume;
  face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(214), g_.s(3), kIce, 0.25f * fade_, -52 * kPi / 180, v0);
  if (A.volume > 0.01f) face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(214), g_.s(4), kIce, 0.85f * fade_, vk, v0);
  buildItems(items_);
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  drawItems(cv, pills);
  rimBottom(cv, R ? "glisează: alt sunet · volumul în Control" : "swipe: another sound · volume in Control", kCream, kFaint);
}

// ------------------------------------------------------------------ games ---

// The games' glass arena (a full annulus, ~6 M instructions to shade) only changes with the aura, so it is shaded
// once over the background into a PSRAM layer and copied in afterwards (bench_games: 14.6 M -> see BRINGUP §4e).
static std::vector<uint16_t> gArena;
static uint64_t gArenaKey = ~0ull;

static void arenaLayer(Canvas& cv, const GlassLayer& gl, uint64_t key, float cx, float cy, float rm, float hw, const GlassStyle& st) {
  const int W = cv.width(), H = cv.height();
  if (gArena.size() != (size_t)W * H) {
    gArena.assign((size_t)W * H, 0);
    gArenaKey = ~0ull;
  }
  if (key != gArenaKey) {
    Canvas layer(W, H, gArena.data());
    gl.background(layer);
    gl.band(layer, cx, cy, rm, hw, st);
    gArenaKey = key;
  }
  const Rect& c = cv.clipRect();
  for (int y = c.y0; y < c.y1; ++y)
    memcpy(cv.data() + y * W + c.x0, gArena.data() + y * W + c.x0, (size_t)(c.x1 - c.x0) * 2);
  cv.markDirty(c);
}

// back to the eyes: give the two 460 KB layers back to PSRAM (the voice build needs it); the next open repaints them
void appsReleaseLayers() {
  std::vector<uint16_t>().swap(gMapLayer);
  std::vector<uint16_t>().swap(gArena);
  gMapLayerOk = false;
  gArenaKey = ~0ull;
}

void Os::drawGames(Canvas& cv) {
  const bool R = ro();
  AppsState& A = apps_;
  char b[64];
  if (A.game < 0) {
    rimTop(cv, R ? "JOCURI" : "GAMES", kCream, kDim);
    static const char* const en[3][2] = {{"Tilt ball", "tilt SOUL, catch the stars"}, {"Rhythm", "tap when a ring hits the rim"}, {"Eye memory", "follow where the eyes look"}};
    static const char* const ro_[3][2] = {{"Bila", "înclină SOUL, prinde stelele"}, {"Ritm", "atinge când inelul ajunge la margine"}, {"Memoria ochilor", "repetă unde se uită ochii"}};
    for (int i = 0; i < 3; ++i) {
      const float y = 170 + i * 76;
      glassPanel(cv, 66, y - 32, 400, y + 32, 22, gs());
      textAt(cv, fonts::text(), 104, y - 9, R ? ro_[i][0] : en[i][0], kCream, 1, Align::Left);
      textAt(cv, fonts::small(), 104, y + 17, R ? ro_[i][1] : en[i][1], kCream, kFaint, Align::Left);
      snprintf(b, sizeof b, "%d", A.best[i]);
      textAt(cv, fonts::text(), 370, y - 2, A.best[i] ? b : "-", kMint, A.best[i] ? 0.9f : 0.4f, Align::Right);
    }
    rimBottom(cv, R ? "recordurile, în dreapta" : "your bests on the right", kCream, kFaint);
    return;
  }
  const float cx = g_.cx(), cy = g_.cy();
  bool over = false;
  int score = 0;
  if (A.game == 0) {
    const games::TiltBall& T = A.tilt;
    arenaLayer(cv, glass(), arenaKey(0), cx, cy, g_.s(games::TiltBall::kArena + 6), g_.s(8), gs());
    for (const games::TiltBall::Hole& h : T.holes()) {
      cv.ellipse(cx + g_.s(h.x), cy + g_.s(h.y), g_.s(games::TiltBall::kHole), g_.s(games::TiltBall::kHole), kDark, fade_);
      cv.ring(cx + g_.s(h.x), cy + g_.s(h.y), g_.s(games::TiltBall::kHole), g_.s(2.5f), kAmber, 0.55f * fade_, 6, 0.3f);
    }
    if (T.running()) cv.star(cx + g_.s(T.star().x), cy + g_.s(T.star().y), g_.s(games::TiltBall::kStar), t_ * 1.5f, Rgb::hex(0xFFD76B), fade_, 10, 0.4f);
    glass().orb(cv, cx + g_.s(T.x()), cy + g_.s(T.y()), g_.s(games::TiltBall::kBall), gsAccent(kCream, 0.35f, 0.25f));
    cv.ellipse(cx + g_.s(T.x() - 5), cy + g_.s(T.y() - 6), g_.s(4), g_.s(3), pal::kWhite, 0.7f * fade_);
    if (T.running())
      rimTop(cv, std::to_string(T.score()) + (R ? " stele · " : " stars · ") + std::to_string((int)ceilf(T.left())) + " s · " +
                     std::to_string(T.lives()) + (R ? " vieți" : " lives"), kCream, kDim);
    over = T.over();
    score = T.score();
  } else if (A.game == 1) {
    const games::Rhythm& Ry = A.rhythm;
    // the target: the rim; the beats swell out from the eyes
    arenaLayer(cv, glass(), arenaKey(1), cx, cy, g_.s(206), g_.s(10), gs(0.9f));
    float fr[8];
    const int n = Ry.visible(fr, 8);
    for (int i = 0; i < n; ++i) {
      const float rr = 60 + fr[i] * 146;
      const float a = fr[i] > 0.92f ? 1.0f : 0.35f + 0.55f * fr[i];
      cv.ring(cx, cy, g_.s(rr), g_.s(3), fr[i] > 0.97f ? kMint : kCream, a, 6, 0.3f);
    }
    if (A.judgeT > 0) {
      const games::Rhythm::Judge j = Ry.lastJudge();
      const char* w = j == games::Rhythm::Perfect ? (R ? "Perfect!" : "Perfect!") : j == games::Rhythm::Good ? (R ? "Bine" : "Good") : (R ? "Ratat" : "Miss");
      textAt(cv, fonts::text(), 233, 360, w, j == games::Rhythm::Perfect ? kMint : j == games::Rhythm::Good ? kCream : kAmber, fminf(1, A.judgeT * 3));
    }
    if (Ry.running()) {
      snprintf(b, sizeof b, "%d  \xC2\xB7  x%d", Ry.score(), Ry.combo());
      rimTop(cv, b, kCream, kDim);
    }
    over = Ry.over();
    score = Ry.score();
  } else {
    const games::EyeMemory& M = A.memory;
    static const float kx[] = {0, 1, 0, -1}, ky[] = {-1, 0, 1, 0};
    const int cue = M.cue();
    for (int i = 0; i < 4; ++i) {
      const float x = cx + g_.s(180 * kx[i]), y = cy + g_.s(180 * ky[i]);
      const bool lit = cue == i || (A.tapGlow > 0 && A.lastTap == i);
      glass().orb(cv, x, y, g_.s(24), lit ? gsAccent(cue == i ? kIce : kMint, 0.6f, 0.4f) : gs(0.8f));
    }
    if (M.phase() == games::EyeMemory::Phase::Show) snprintf(b, sizeof b, R ? "runda %d · privește" : "round %d · watch", M.round());
    else if (M.phase() == games::EyeMemory::Phase::Input) snprintf(b, sizeof b, R ? "runda %d · rândul tău %d/%d" : "round %d · your turn %d/%d", M.round(), M.progress() + 1, M.round());
    else b[0] = 0;
    if (b[0]) rimTop(cv, b, kCream, kDim);  // the bottom spot sits where rim words would
    over = M.phase() == games::EyeMemory::Phase::Over;
    score = M.score();
  }
  if (over) {
    glassPanel(cv, 86, 168, 380, 362, 36, A.newBest ? gsAccent(kMint, 0.45f, 0.12f) : gs());
    textAt(cv, fonts::small(), 233, 196, R ? "GATA" : "GAME OVER", kCream, kFaint);
    textAt(cv, fonts::digits(), 233, 250, std::to_string(score), A.newBest ? kMint : kCream);
    snprintf(b, sizeof b, A.newBest ? (R ? "record nou!" : "new best!") : (R ? "recordul: %d" : "best: %d"), A.best[A.game]);
    textAt(cv, fonts::small(), 233, 290, b, A.newBest ? kMint : kCream, A.newBest ? 1 : kDim);
    buildItems(items_);
    drawItems(cv, items_);
  }
}

// ------------------------------------------------------------------ focus ---

void Os::drawFocus(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const apps::Pomodoro& P = A.pomo;
  const bool idle = P.phase() == apps::Pomodoro::Phase::Idle, rest = P.phase() == apps::Pomodoro::Phase::Short || P.phase() == apps::Pomodoro::Phase::Long;
  char b[64];
  if (idle) snprintf(b, sizeof b, "%s", R ? "FOCUS · 25 + 5" : "FOCUS · 25 + 5");
  else if (rest) snprintf(b, sizeof b, "%s", P.phase() == apps::Pomodoro::Phase::Long ? (R ? "PAUZĂ LUNGĂ" : "LONG BREAK") : (R ? "PAUZĂ" : "BREAK"));
  else snprintf(b, sizeof b, R ? "FOCUS · %d DIN %d" : "FOCUS · %d OF %d", P.round(), P.rounds);
  rimTop(cv, b, rest ? kMint : kCream, kDim);
  glass().band(cv, g_.cx(), g_.cy(), g_.s(214), g_.s(13), gs());
  const float frac = idle ? 1.0f : P.left() / P.total();
  if (frac > 0.002f) face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(214), g_.s(6), rest ? kMint : kCream, 0.9f * fade_, -kPi / 2, -kPi / 2 + 2 * kPi * frac);
  textAt(cv, fonts::digits(), 233, 252, apps::Stopwatch::format(idle ? P.focusMin * 60.0f : P.left(), false), P.paused() ? kAmber : rest ? kMint : kCream);
  // rounds as dots
  for (int i = 0; i < P.rounds; ++i) {
    const bool done = i < (P.done() % P.rounds) || (!idle && i < P.round() - 1);
    cv.ellipse(g_.s(233 + (i - 1.5f) * 22), g_.s(296), g_.s(5), g_.s(5), kCream, (done ? 0.95f : 0.25f) * fade_);
  }
  glass().orb(cv, g_.s(233), g_.s(340), g_.s(36), idle ? gsAccent(kMint, 0.4f, 0.12f) : gs());
  static Path p;
  if (p.reserve(128)) {
    p.clear();
    const float x = g_.s(233), y = g_.s(340), s = g_.s(13);
    if (!idle && !P.paused()) {
      p.roundRect(x - s * 0.8f, y - s, s * 0.55f, s * 2, s * 0.15f);
      p.roundRect(x + s * 0.25f, y - s, s * 0.55f, s * 2, s * 0.15f);
    } else {
      const float tri[] = {x - s * 0.6f, y - s, x + s, y, x - s * 0.6f, y + s};
      p.polygon(tri, 3);
    }
    face_.raster().fill(cv, p, idle ? kMint : kCream, fade_);
  }
  buildItems(items_);
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  drawItems(cv, pills);
}

// ---------------------------------------------------------------- breathe ---

void Os::drawBreathe(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const apps::BreathPattern& p = apps::breathPatterns()[A.breathPat];
  if (!A.breathing) {  // black behind the eyes (a face moment): only the words and two capsules
    rimTop(cv, R ? "RESPIRĂ" : "BREATHE", kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    rimBottom(cv, R ? "atinge ochii ca să începi" : "tap the eyes to begin", kCream, kFaint);
    return;
  }
  const apps::BreathPoint b = apps::breathAt(p, A.breathT);
  // a ring that breathes with the eyes
  const float r = g_.s(150 + 60 * b.size);
  cv.ring(g_.cx(), g_.cy() - g_.s(8), r, g_.s(2.5f), b.phase == 0 || b.phase == 1 ? kIce : kMint, 0.35f + 0.3f * b.size, 10, 0.25f);
  static const char* const en[] = {"Breathe in", "Hold", "Breathe out", "Hold"};
  static const char* const ro_[] = {"Inspiră", "Ține", "Expiră", "Ține"};
  const float d[4] = {p.in, p.hold1, p.out, p.hold2};
  const int left = (int)ceilf(d[b.phase] * (1 - b.progress));
  rimBottomCap(cv, std::string(R ? ro_[b.phase] : en[b.phase]) + " \xC2\xB7 " + std::to_string(left), b.phase == 2 ? kMint : kIce, 1, true);
  const int total = A.breathMin * 60, rest = total - (int)A.breathT;
  char t[24];
  snprintf(t, sizeof t, "%d:%02d", rest / 60, rest % 60);
  rimTop(cv, t, kCream, kFaint);
}

// ----------------------------------------------------------------- habits ---

void Os::drawHabits(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const uint32_t today = now_ / 86400;
  int d = 0;
  for (const apps::Habit& h : A.habits) d += h.doneOn(today);
  char b[48];
  snprintf(b, sizeof b, R ? "OBICEIURI · %d DIN %d AZI" : "HABITS · %d OF %d TODAY", d, (int)A.habits.size());
  rimTop(cv, b, d == (int)A.habits.size() && d ? kMint : kCream, kDim);
  if (A.habits.empty()) textAt(cv, fonts::text(), 233, 230, R ? "Niciun obicei încă" : "No habits yet", kCream, kDim);
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id < ARow) continue;
    const apps::Habit& h = A.habits[it.id - ARow];
    const bool done = h.doneOn(today);
    glassPanel(cv, 66, it.y - 33, 400, it.y + 33, 22, holdItem_ == it.id ? gs().pressed() : done ? gsAccent(kMint, 0.2f, 0.08f) : gs());
    // the check
    cv.ring(g_.s(104), g_.s(it.y - 6), g_.s(13), g_.s(2.2f), done ? kMint : kCream, (done ? 1 : 0.5f) * fade_);
    if (done) {
      static Path p;
      if (p.reserve(64)) {
        p.clear();
        const float x = g_.s(104), y = g_.s(it.y - 6), k = g_.s(6);
        const float pts[] = {x - k, y, x - k * 0.25f, y + k * 0.75f, x + k, y - k * 0.8f};
        p.stroke(pts, 3, g_.s(2.4f));
        face_.raster().fill(cv, p, kMint, fade_);
      }
    }
    textAt(cv, fonts::text(), 132, it.y - 8, fit(fonts::text(), h.name, g_.s(st_w(h, today))), kCream, 1, Align::Left);
    // the last 7 days
    for (int k = 0; k < 7; ++k) {
      const bool on = h.doneOn(today - (6 - k));
      cv.ellipse(g_.s(138 + k * 15), g_.s(it.y + 18), g_.s(4), g_.s(4), on ? kMint : kCream, (on ? 0.95f : 0.22f) * fade_);
    }
    const int st = h.streak(today);
    if (st > 0) {
      snprintf(b, sizeof b, R ? "%d zile" : "%d day%s", st, (!R && st > 1) ? "s" : "");
      textAt(cv, fonts::small(), 372, it.y + 2, b, st >= 3 ? kMint : kCream, st >= 3 ? 1 : kDim, Align::Right);
    }
    if (holdItem_ == it.id) {
      const float w = g_.s(260) * (holdItemT_ > 1 ? 1 : holdItemT_);
      cv.roundRect(g_.cx() - w / 2, g_.s(it.y + 36), g_.cx() + w / 2, g_.s(it.y + 36) + 3, 1.5f, kAmber, 0.9f);
    }
  }
  for (const Item& it : items_)
    if (it.id == ANew) {
      std::vector<Item> one(1, it);
      drawItems(cv, one);
    }
  rimBottom(cv, R ? "atinge = făcut azi · ține = șterge" : "tap = done today · hold = remove", kCream, kFaint);
}

// -------------------------------------------------------------- stopwatch ---

void Os::drawStopwatch(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, R ? "CRONOMETRU" : "STOPWATCH", kCream, kDim);
  const std::string s = apps::Stopwatch::format(A.sw.acc, true);
  const size_t dot = s.find('.');
  const std::string main = dot == std::string::npos ? s : s.substr(0, dot), tenth = dot == std::string::npos ? "" : s.substr(dot);
  const int mw = Canvas::measureText(fonts::digits(), main.c_str()), tw = Canvas::measureText(fonts::large(), tenth.c_str());
  const float x0 = g_.cx() - (mw + tw) * 0.5f;
  cv.drawText(fonts::digits(), x0, (int)g_.s(232), main.c_str(), A.sw.run ? kCream : kCream, (A.sw.run ? 1 : 0.85f) * fade_, Align::Left);
  cv.drawText(fonts::large(), x0 + mw, (int)g_.s(232), tenth.c_str(), kCream, kDim * fade_, Align::Left);
  const int n = (int)A.sw.laps.size();
  for (int k = 0; k < 2 && k < n; ++k) {
    const int i = n - 1 - k;
    const double split = A.sw.laps[i] - (i ? A.sw.laps[i - 1] : 0);
    char b[48];
    snprintf(b, sizeof b, R ? "tura %d   %s" : "lap %d   %s", i + 1, apps::Stopwatch::format(split, true).c_str());
    textAt(cv, fonts::small(), 233, 270 + k * 24, b, kCream, k ? kFaint : kDim);
  }
  glass().orb(cv, g_.s(150), g_.s(352), g_.s(34), gs());
  glass().orb(cv, g_.s(316), g_.s(352), g_.s(34), A.sw.run ? gsAccent(kAmber, 0.4f, 0.12f) : gsAccent(kMint, 0.4f, 0.12f));
  textAt(cv, fonts::small(), 150, 352, A.sw.run ? (R ? "Tură" : "Lap") : (R ? "Zero" : "Reset"), kCream, A.sw.acc > 0 || A.sw.run ? 1 : 0.4f);
  textAt(cv, fonts::small(), 316, 352, A.sw.run ? (R ? "Pauză" : "Pause") : "Start", A.sw.run ? kAmber : kMint);
}

// ------------------------------------------------------------ world clock ---

void Os::drawWorldClock(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  apps::PosixTz here;
  here.parse(A.tz.c_str());
  int64_t utc = (int64_t)now_ - here.stdOff;
  utc = (int64_t)now_ - here.offsetAt(utc);
  const int myOff = here.offsetAt(utc);
  rimTop(cv, std::string(R ? "ORA LUMII · AICI " : "WORLD CLOCK · HERE ") + hm(now_), kCream, kDim);
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id < ARow) continue;
    const apps::City& c = apps::cities()[A.clocks[it.id - ARow]];
    apps::PosixTz tz;
    tz.parse(c.tz);
    const int off = tz.offsetAt(utc);
    const int64_t local = utc + off;
    const int dayDiff = (int)(local / 86400 - ((int64_t)now_) / 86400);
    glassPanel(cv, 66, it.y - 29, 400, it.y + 29, 22, holdItem_ == it.id ? gs().pressed() : gs());
    textAt(cv, fonts::text(), 98, it.y - 8, R ? c.nameRo : c.name, kCream, 1, Align::Left);
    char b[48];
    const int dh = (off - myOff) / 60;
    snprintf(b, sizeof b, "%s%d%s h%s%s", dh >= 0 ? "+" : "-", abs(dh) / 60, abs(dh) % 60 ? ":30" : "",
             dayDiff > 0 ? (R ? " · mâine" : " · tomorrow") : dayDiff < 0 ? (R ? " · ieri" : " · yesterday") : "",
             tz.dstAt(utc) ? (R ? " · vară" : " · summer") : "");
    textAt(cv, fonts::small(), 98, it.y + 16, b, kCream, kFaint, Align::Left);
    const int lh = (int)(((local % 86400) + 86400) % 86400 / 3600);
    textAt(cv, fonts::large(), 372, it.y, hm((uint32_t)(((local % 86400) + 86400) % 86400)), lh >= 7 && lh < 21 ? kCream : kIce, 1, Align::Right);
  }
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  drawItems(cv, pills);
  rimBottom(cv, R ? "atinge: alt oraș · ține: scoate" : "tap: another city · hold: remove", kCream, kFaint);
}

// ---------------------------------------------------------------- convert ---

void Os::drawConvert(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const apps::Quantity q = (apps::Quantity)A.q;
  const std::vector<apps::Unit>& u = apps::units(q);
  buildItems(items_);
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  glassPanel(cv, 70, 152, 396, 216, 24, gs());
  textAt(cv, fonts::large(), 300, 184, apps::formatNumber(A.value), kCream, 1, Align::Right);
  // the swap orb: two arrows
  glass().orb(cv, g_.s(233), g_.s(250), g_.s(26), gs());
  cv.segment(g_.s(226), g_.s(240), g_.s(226), g_.s(262), g_.s(2.2f), kCream, fade_);
  cv.segment(g_.s(226), g_.s(240), g_.s(221), g_.s(246), g_.s(2.2f), kCream, fade_);
  cv.segment(g_.s(240), g_.s(238), g_.s(240), g_.s(260), g_.s(2.2f), kCream, fade_);
  cv.segment(g_.s(240), g_.s(260), g_.s(245), g_.s(254), g_.s(2.2f), kCream, fade_);
  const double r = apps::convert(q, A.from, A.to, A.value, A.rates);
  glassPanel(cv, 70, 286, 396, 350, 24, gsAccent(kMint, 0.18f, 0.06f));
  textAt(cv, fonts::large(), 300, 318, apps::formatNumber(r), kMint, 1, Align::Right);
  drawItems(cv, pills);
  std::string foot;
  if (q == apps::Quantity::Currency)
    foot = A.rates.fromCloud ? (R ? "cursul BCE din " : "ECB rates of ") + A.rates.date : (R ? "curs aproximativ, fără internet" : "approximate rates, offline");
  else
    foot = std::string("1 ") + u[A.from].label + " = " + apps::formatNumber(apps::convert(q, A.from, A.to, 1, A.rates)) + " " + u[A.to].label;
  textAt(cv, fonts::small(), 233, 380, foot, kCream, kFaint);
  rimBottom(cv, R ? "atinge numărul ca să-l schimbi" : "tap the number to change it", kCream, kFaint);
}

// ------------------------------------------------------------- find phone ---

void Os::drawFindPhone(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, R ? "GĂSEȘTE TELEFONUL" : "FIND MY PHONE", kCream, kDim);
  const bool ringing = A.findState == 1 || A.findState == 2;
  if (ringing) {
    const float ph = fmodf(t_ * 0.8f, 1.0f);
    for (int k = 0; k < 2; ++k) {
      const float f = fmodf(ph + k * 0.5f, 1.0f);
      cv.ring(g_.s(233), g_.s(318), g_.s(62 + f * 90), g_.s(3), kAmber, (1 - f) * 0.6f * fade_);
    }
  }
  glass().orb(cv, g_.s(233), g_.s(318), g_.s(56), gsAccent(kAmber, ringing ? 0.7f : 0.4f, ringing ? 0.22f : 0.1f));
  drawGlyph(cv, AppId::FindPhone, 233, 318, 40, ringing ? kAmber : kCream, 1);
  std::string s, sub;
  switch (A.findState) {
    case 1: s = R ? "Îl sun…" : "Ringing…"; break;
    case 2: s = R ? "Sună pe /me/where" : "Ringing on /me/where"; sub = R ? "atinge „L-am găsit” pe telefon" : "tap “Found it” on the phone"; break;
    case 3: s = R ? "Notificare trimisă" : "Notification sent"; sub = R ? "nicio pagină deschisă acum" : "no page open right now"; break;
    case 4: s = R ? "Niciun telefon nu ascultă" : "No phone is listening"; sub = R ? "deschide o dată /me/where pe telefon" : "open /me/where on your phone once"; break;
    case 5: s = R ? "Nu pot acum" : "Can't right now"; sub = cloudOk(net_) ? (R ? "fără internet?" : "no internet?") : (R ? "are nevoie de SOUL Cloud" : "needs SOUL Cloud"); break;
    default: s = R ? "Atinge ca să-l sun" : "Tap to ring it"; sub = R ? "chiar și pe silențios, dacă pagina e deschisă" : "even on silent, if the page is open"; break;
  }
  textAt(cv, fonts::text(), 233, 160, s, A.findState >= 4 ? kAmber : kCream);
  if (!sub.empty()) textAt(cv, fonts::small(), 233, 192, fit(fonts::small(), sub, g_.s(320)), kCream, kDim);
}

// ----------------------------------------------------------------- device ---

void Os::drawDevice(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const StorageInfo& S = A.storage;
  rimTop(cv, R ? "DISPOZITIV" : "DEVICE", kCream, kDim);
  // the battery as a ring on the rim
  glass().band(cv, g_.cx(), g_.cy(), g_.s(214), g_.s(13), gs());
  const float lvl = power_.batPct >= 0 ? power_.batPct / 100.0f : 1.0f;
  const Rgb bc = power_.charging ? kMint : power_.batPct >= 0 && power_.batPct < 20 ? kAmber : kCream;
  face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(214), g_.s(6), bc, 0.9f * fade_, -kPi / 2, -kPi / 2 + 2 * kPi * lvl);
  char b[96];
  if (power_.batPct >= 0) snprintf(b, sizeof b, "%d%%", power_.batPct);
  else snprintf(b, sizeof b, "USB");
  textAt(cv, fonts::large(), 233, 146, b, bc);
  textAt(cv, fonts::small(), 233, 176, power_.charging ? (R ? "se încarcă" : "charging") : power_.batPct >= 0 ? (R ? "pe baterie" : "on battery") : (R ? "alimentat prin USB" : "powered by USB"),
         kCream, kDim);
  glassPanel(cv, 74, 198, 392, 372, 28, gs());
  std::string rows[5];
  snprintf(b, sizeof b, R ? "%d notițe · %d alarme · %d mementouri" : "%d notes · %d alarms · %d reminders", (int)notes_.size(),
           alarms_ ? alarms_->count() : 0, (int)rems_.size());
  rows[0] = b;
  if (S.appMaxKb) snprintf(b, sizeof b, R ? "firmware %.1f din %.1f MB" : "firmware %.1f of %.1f MB", S.appKb / 1024.0, S.appMaxKb / 1024.0);
  else snprintf(b, sizeof b, "firmware %s", S.fw.c_str());
  rows[1] = b;
  if (S.nvsTotal) snprintf(b, sizeof b, R ? "setări: %u din %u locuri" : "settings: %u of %u slots", (unsigned)S.nvsUsed, (unsigned)S.nvsTotal);
  else snprintf(b, sizeof b, "%s", R ? "setări: în flash" : "settings: in flash");
  rows[2] = b;
  if (S.heapKb) snprintf(b, sizeof b, R ? "RAM liber %u KB · PSRAM %.1f MB" : "free RAM %u KB · PSRAM %.1f MB", (unsigned)S.heapKb, S.psramKb / 1024.0);
  else snprintf(b, sizeof b, "SoulOS %s", S.fw.c_str());
  rows[3] = b;
  rows[4] = "SoulOS " + S.fw + (S.board.empty() ? std::string() : " \xC2\xB7 " + S.board) + "  \xC2\xB7  " + (net_.connected ? "Wi-Fi " + net_.ssid + (S.rssi ? " \xC2\xB7 " + std::to_string(S.rssi) + " dBm" : std::string()) : (R ? "fără Wi-Fi" : "no Wi-Fi"));
  for (int i = 0; i < 5; ++i) textAt(cv, fonts::small(), 233, 224 + i * 32, fit(fonts::small(), rows[i], g_.s(300)), kCream, i ? kDim : 1.0f);

}

// ------------------------------------------------------- settings › apps ---

void Os::drawAppsSettings(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const int n = (int)A.order.size(), pages = (n + 3) / 4, p = A.setPage % pages;
  char b[48];
  snprintf(b, sizeof b, R ? "APLICAȚII · %d/%d" : "APPS · %d/%d", p + 1, pages);
  rimTop(cv, b, kCream, kDim);
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id >= ARow && it.id < ARow + n) {
      const AppId a = (AppId)A.order[it.id - ARow];
      const bool on = !(A.hidden >> (int)a & 1u);
      glassPanel(cv, 134, it.y - 28, 392, it.y + 28, 22, gs());
      drawGlyph(cv, a, 162, it.y, 22, kCream, on ? 0.9f : 0.35f);
      textAt(cv, fonts::small(), 186, it.y, fit(fonts::small(), appName(a), g_.s(120)), kCream, on ? 1 : kFaint, Align::Left);
      glassToggle(cv, 350, it.y, on);
    } else if (it.id >= AUp) {
      glass().orb(cv, g_.s(it.x), g_.s(it.y), g_.s(22), gs());
      cv.segment(g_.s(it.x), g_.s(it.y + 9), g_.s(it.x), g_.s(it.y - 8), g_.s(2.2f), kCream, fade_);
      cv.segment(g_.s(it.x - 7), g_.s(it.y - 2), g_.s(it.x), g_.s(it.y - 9), g_.s(2.2f), kCream, fade_);
      cv.segment(g_.s(it.x + 7), g_.s(it.y - 2), g_.s(it.x), g_.s(it.y - 9), g_.s(2.2f), kCream, fade_);
    }
  }
  rimBottom(cv, R ? "↑ = mai devreme pe orbită · glisează în sus" : "↑ = earlier on the orbit · swipe up: more", kCream, kFaint);
}

// ------------------------------------------------------------ quick replies ---

bool Os::drawQuickReplies(Canvas& cv, float y) {
  (void)y;
  if (thinking_ || acceptMode_ || cardHidden_ || cardTitle_.empty() || !net_.paired) return false;
  std::vector<Item> v;
  buildAppsItems(v);
  drawItems(cv, v);
  return true;
}

}  // namespace suflet
