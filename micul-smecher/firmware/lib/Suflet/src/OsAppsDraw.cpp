// SoulOS apps: what each app screen shows, in SoulOS Alive (os/DESIGN-ALIVE.md §4): the eyes in the one slot,
// flat pebbles and pills in the born palette, lists as wheels (OsScreens.cpp), Today one widget at a time, 8 px
// rings on the rim. Breathe, the games and Control are face moments: pure black behind the eyes.
// Layout in design px of the 466 disc (DisplayGeometry scales it).
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <new>

#include "Os.h"
#include "QrImage.h"
#include "Raster.h"

namespace suflet {

using namespace eyes;

static const Rgb kCream = Rgb::hex(0xFBF4E3), kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4),
                 kIce = Rgb::hex(0x9FC6FF), kDark = Rgb::hex(0x05050A);
static const float kDim = 0.82f, kFaint = 0.66f;  // SoulOS Alive: ink2 / ink3 (what you must read is >= 80 %)
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

// ---------------------------------------------------- SOUL S layouts ---
// The screens below that place discs, tiles and fields of their own (not rows of pills: OsScreens.cpp fitRows)
// take their numbers from these: SOUL M's 1.9.0 literals, or SOUL S's (Density.h: 68 px = 6.4 mm targets, the S
// type, the 221 px safe circle). firmware/SOUL-S.md §5.
namespace {
struct ControlSpec {  // pulled down from the eyes: the light / volume capsules, four tiles, the AI line
  float capX[2] = {96, 370}, capY = 182, capW = 84, capH = 58, capR = 20, capCapDy = -12, capValDy = 13;
  float tileX[2] = {180, 286}, tileY[2] = {238, 330}, tileW = 100, tileH = 84, tileR = 24, iconDy = -13, labelDy = 20, labelW = 94;
  float aiY = 402, aiW = 230, aiH = 44, aiTextDy = -2, iconK = 1;
  // the light capsule's hit box: inside the drawn capsule, clear of the first tile (the 1.9.0 box overlapped it by
  // 8 px; the AI line's was 180 px for 190 px of words: the round audit's overlap / spill, 2026-10-20)
  float autoX = 92, autoW = 72;
};
ControlSpec controlSpecFor(const Density& d) {
  ControlSpec c;
  if (d.reference) return c;
  const float t = d.targetDesign();
  c.capX[0] = 88, c.capX[1] = 378, c.capY = 158, c.capW = 92, c.capH = 70, c.capCapDy = -15, c.capValDy = 15;
  c.tileX[0] = 233 - 67, c.tileX[1] = 233 + 67, c.tileY[0] = 236, c.tileY[1] = 318, c.tileW = 124, c.tileH = 76;
  c.iconDy = -15, c.labelDy = 17, c.labelW = 116;
  c.aiY = 392, c.aiW = 236, c.aiH = t, c.aiTextDy = 0, c.iconK = 1.25f;
  c.autoX = c.capX[0], c.autoW = c.capW;
  return c;
}
struct MusicSpec {  // prev / play / next, the sleep timer pill
  float y = 296, dx = 93, side = 64, play = 86, pillY = 378, nameY = 182, wordsY = 216, tri = 10, icon = 14;
};
MusicSpec musicSpecFor(const Density& d) {
  MusicSpec m;
  if (d.reference) return m;
  m.y = 276, m.dx = 112, m.side = 72, m.play = 92, m.pillY = 362, m.nameY = 158, m.wordsY = 196, m.tri = 12, m.icon = 16;
  return m;
}
struct ConvertSpec {  // SOUL S only (M keeps its literals): the number field, the result field, the swap disc
  float qtyY = 164, x0 = 112, x1 = 392, fromY = 238, toY = 318, ctlH = 68.5f, fieldH = 72, swapX = 70, swapY = 278,
        swap = 68.5f, footY = 380, pillPad = 60;
  float unitWidth(const std::string& label) const {
    return fmaxf(ctlH, (float)Canvas::measureText(fonts::caption(), label.c_str()) + pillPad);
  }
  float unitX(float w) const { return x1 - 4 - w * 0.5f; }
};
ConvertSpec convertSpecFor(const Density& d) {
  ConvertSpec c;
  c.ctlH = c.swap = d.targetDesign();
  c.pillPad = d.pillPad;
  return c;
}
}  // namespace

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
      if (!thinking_ && !acceptMode_ && !cardHidden_ && !cardTitle_.empty() && net_.paired) {  // a message: its replies
        // (S: two rows of 68 px pills under the card, OsDraw.cpp drawAnswer)
        add(AReply + 0, 152, L(306, 320), 96, 50, "OK", kCream, 0, true);
        add(AReply + 1, 290, L(306, 320), 160, 50, R ? "Vin acum" : "On my way", kCream, 0, true);
        add(AReply + 2, 166, L(360, 392), 128, 50, R ? "Mai târziu" : "Later", kCream, 0, true, kDim);
        add(AReply + 3, 300, L(360, 392), 116, 50, R ? "Scrie…" : "Type…", kCream, 0, true, kDim);
      }
      break;
    case View::Control: {
      const ControlSpec c = controlSpecFor(dens_);
      for (int i = 0; i < 4; ++i) add(ATile + i, c.tileX[i % 2], c.tileY[i / 2], c.tileW, c.tileH, "", kCream, 0, false);
      add(AAuto, c.autoX, c.capY, c.autoW, c.capH, "", kCream, 0, false);  // the light's capsule: a tap = auto
      add(AAi, 233, c.aiY, c.aiW, c.aiH, "", kCream, 0, false);
      break;
    }
    case View::Weather:
      if (!A.weather.ok && !A.wxWait && cloudOk(net_) && A.wxErr != 409)
        add(ARetry, 233, 330, 170, 50, R ? "Încearcă iar" : "Try again", kCream, 0, true);
      break;
    case View::Calendar:
      if (!A.agenda.ok && !A.calWait && cloudOk(net_) && A.calErr != 404)
        add(ARetry, 233, 330, 170, 50, R ? "Încearcă iar" : "Try again", kCream, 0, true);
      break;  // the events: a wheel (OsScreens.cpp)
    case View::Maps:
      // (SOUL S: every disc a 6.4 mm target, the ones on the rim moved in so they stay inside the circle)
      if (A.sendSheet) {
        add(AClose, 233, L(404, 398), 130, 48, R ? "Gata" : "Done", kCream, 0, true);
      } else if (!A.haveFix && !A.preview && !A.navOn) {
        if (cloudOk(net_)) add(AWifi, 233, L(386, 380), 170, 50, R ? "Prin Wi-Fi" : "Use Wi-Fi", kCream, 0, true, kDim);
      } else if (A.navOn) {
        const float d = L(56, dens_.targetDesign());
        add(APhone, 166, L(372, 364), 120, 50, R ? "Telefon" : "Phone", kCream, 0, true, kDim);
        add(AEnd, 300, L(372, 364), 110, 50, R ? "Stop" : "End", kAmber, 0, true);
        add(APrev, L(64, 52), L(208, 216), d, d, "\xE2\x80\xB9", kCream, 1, false);
        add(ANext, L(402, 414), L(208, 216), d, d, "\xE2\x80\xBA", kCream, 1, false);
      } else if (A.preview) {
        add(AStartNav, 233, L(326, 290), 150, 52, R ? "Pornește" : "Start", kMint, 1, true);
        add(APhone, 166, L(384, 366), 120, 48, R ? "Telefon" : "Phone", kCream, 0, true, kDim);
        add(AMode, 300, L(384, 366), 120, 48, A.routeMode == "walk" ? (R ? "pe jos" : "walk") : A.routeMode == "bike" ? (R ? "bicicletă" : "bike") : (R ? "mașină" : "car"),
            kCream, 0, true, kDim);
      } else {
        const float d = L(52, dens_.targetDesign());
        add(AGo, 233, L(322, 314), 160, 52, R ? "Unde mergem?" : "Where to?", kCream, 0, true);
        add(AMinus, L(50, 52), 233, d, d, "-", kCream, 1, false);
        add(APlus, L(416, 414), 233, d, d, "+", kCream, 1, false);
        add(ACenter, L(100, 96), L(344, 314), L(54, d), L(54, d), "", kCream, 0, false);  // (S: in Where to?'s row)
      }
      break;
    case View::Music: {
      const MusicSpec m = musicSpecFor(dens_);
      add(APrev, 233 - m.dx, m.y, m.side, m.side, "", kCream, 0, false);
      add(AStart, 233, m.y, m.play, m.play, "", kCream, 0, false);
      add(ANext, 233 + m.dx, m.y, m.side, m.side, "", kCream, 0, false);
      if (A.speaker) {
        std::string s = A.sleepMin ? (R ? "Se oprește în " : "Stops in ") + std::to_string((int)ceilf(A.sleepLeft / 60)) + " min"
                                   : (R ? "Fără oprire" : "No sleep timer");
        add(ASleepT, 233, m.pillY, 220, 48, s, kCream, 0, true, kDim);
      }
      break;
    }
    case View::Games:
      if (A.game >= 0) {  // (the menu is a wheel)
        const bool over = (A.game == 0 && A.tilt.over()) || (A.game == 1 && A.rhythm.over()) ||
                          (A.game == 2 && A.memory.phase() == games::EyeMemory::Phase::Over);
        if (over) {
          add(AAgain, 164, L(336, 334), 132, 52, R ? "Încă o dată" : "Again", kMint, 0, true);
          add(AMenu, 304, L(336, 334), 116, 52, R ? "Jocuri" : "Games", kCream, 0, true, kDim);
        }
      }
      break;
    case View::Focus: {
      const bool idle = A.pomo.phase() == apps::Pomodoro::Phase::Idle;
      add(AStart, 233, 326, 78, 78, "", kCream, 0, false);
      if (!idle) {
        add(ASkip, 118, 326, 100, 48, R ? "Sari" : "Skip", kCream, 0, true, kDim);
        add(AStop, 348, 326, 100, 48, "Stop", kAmber, 0, true);
      }
      break;
    }
    case View::Breathe:
      if (!A.breathing) {
        const apps::BreathPattern& p = apps::breathPatterns()[A.breathPat];
        add(APattern, 176, 362, 150, 52, R ? p.nameRo : p.name, kCream, 0, true);
        add(ADur, 312, 362, 100, 52, std::to_string(A.breathMin) + " min", kCream, 0, true, kDim);
      }
      break;
    case View::Stopwatch:
      add(ALap, 170, L(352, 346), L(68, 72), L(68, 72), "", kCream, 0, false);
      add(AStart, 296, L(352, 346), L(68, 72), L(68, 72), "", kCream, 0, false);
      break;
    case View::Convert: {
      const std::vector<apps::Unit>& u = apps::units((apps::Quantity)A.q);
      const std::string qty = std::string(apps::quantityName((apps::Quantity)A.q, R)) + " \xE2\x80\xBA";
      if (sGlass()) {  // SOUL S (ConvertSpec): two 68 px fields, the unit pills at their right end, the swap disc left
        const ConvertSpec c = convertSpecFor(dens_);
        const size_t first = out.size();
        const float fromW = c.unitWidth(u[A.from].label), toW = c.unitWidth(u[A.to].label);
        add(AQty, 233, c.qtyY, 190, 48, qty, kCream, 0, true);
        add(AValue, (c.x0 + c.unitX(fromW) - fromW * 0.5f - 6) * 0.5f, c.fromY, c.unitX(fromW) - fromW * 0.5f - 6 - c.x0, c.ctlH, "", kCream, 0, false);
        add(AFrom, c.unitX(fromW), c.fromY, fromW, c.ctlH, u[A.from].label, kCream, 0, true);
        add(ASwap, c.swapX, c.swapY, c.swap, c.swap, "", kCream, 0, false);
        add(ATo, c.unitX(toW), c.toY, toW, c.ctlH, u[A.to].label, kMint, 0, true);
        for (size_t i = first + 1; i < out.size(); ++i) out[i].fixed = true;  // (placed here, not by fitRows)
        break;
      }
      add(AQty, 233, 174, 190, 48, qty, kCream, 0, true);
      add(AValue, 190, 232, 232, 50, "", kCream, 0, false);
      add(AFrom, 342, 232, 72, 44, u[A.from].label, kCream, 0, true);
      add(ASwap, 112, 280, 48, 48, "", kCream, 0, false);
      add(ATo, 342, 328, 72, 44, u[A.to].label, kMint, 0, true);
      break;
    }
    case View::FindPhone:
      add(ARing, 233, 300, 112, 112, "", kAmber, 0, false);
      break;
    default: break;  // Habits, World clock, Settings › Apps: wheels
  }
}

// ---------------------------------------------------------------- glyphs ---

Path& Os::scratchPath() {  // one path for the glyphs, the dial's pebbles and the speech tail (4 KB of contour buffer)
  // made once in PSRAM (1.9: a static Path was 4 KB of internal RAM); its edges are PSRAM too (Path::reserve)
  static Path* p = new (psramAlloc(sizeof(Path))) Path();
  return *p;
}

void Os::drawGlyph(Canvas& cv, AppId a, float cx, float cy, float size, Rgb c, float alpha, float stroke) {
  Path& p = scratchPath();
  if (!p.reserve(1024)) return;
  p.clear();
  const float s = g_.s(size) / 24.0f, ox = g_.s(cx) - 12 * s, oy = g_.s(cy) - 12 * s, w = stroke > 0 ? stroke : 2.0f * fmaxf(1.0f, s * 0.9f);
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
        Path& p = scratchPath();  // (1.9: was a static Path, 4 KB of internal RAM)
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
  Path& p = scratchPath();  // (1.9: was a static Path, 4 KB of internal RAM)
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
  if (power_.batPct >= 0) top += " \xC2\xB7 " + std::to_string(power_.batPct) + "%";
  if (A.dnd) top += R ? " \xC2\xB7 liniște" : " \xC2\xB7 quiet";
  rimTop(cv, top, kCream);
  // the two rim dials (8 px, round caps): light up the left rim, volume up the right rim
  const float b0 = 128 * kPi / 180, b1 = 232 * kPi / 180;  // light: bottom-left (low) up to top-left (high)
  rimRing(cv, 214, b0, b1, pal_.peb2, 1, 8);
  const float bv = set_.bright == 0 ? 0.5f : (set_.bright - 1) / 2.0f;
  const float bk = b0 + (b1 - b0) * bv;
  rimRing(cv, 214, b0, bk, set_.bright == 0 ? kAmber : pal_.e1, 1, 8);
  cv.ellipse(g_.cx() + g_.s(214) * cosf(bk), g_.cy() + g_.s(214) * sinf(bk), g_.s(9), g_.s(9), kCream, fade_);
  const float v0 = 52 * kPi / 180, v1 = -52 * kPi / 180;  // volume: bottom-right (low) to top-right (high)
  rimRing(cv, 214, v1, v0, pal_.peb2, 1, 8);
  const float vk = v0 - (v0 - v1) * A.volume;
  if (A.volume > 0.01f) rimRing(cv, 214, vk, v0, pal_.e2, 1, 8);
  cv.ellipse(g_.cx() + g_.s(214) * cosf(vk), g_.cy() + g_.s(214) * sinf(vk), g_.s(9), g_.s(9), kCream, fade_);
  static const char* const kBr[2][4] = {{"auto", "low", "mid", "high"}, {"auto", "mică", "medie", "mare"}};
  const ControlSpec C = controlSpecFor(dens_);
  for (int k = 0; k < 2; ++k) {  // the light's capsule (a tap = auto), the volume's
    const float x = C.capX[k];
    pebRect(cv, x - C.capW * 0.5f, C.capY - C.capH * 0.5f, x + C.capW * 0.5f, C.capY + C.capH * 0.5f, C.capR, pal_.peb, pal_.pebe, 0);
    textAt(cv, fonts::caption(), x, C.capY + C.capCapDy, k ? std::string("vol") : std::string(R ? "lumină" : "light"), kCream, kDim);
    if (k) textAt(cv, fonts::body(), x, C.capY + C.capValDy, std::to_string((int)lroundf(A.volume * 100)), pal_.e2);
    else textAt(cv, fonts::body(), x, C.capY + C.capValDy, kBr[R][set_.bright % 4], set_.bright == 0 ? kAmber : kCream);
  }
  // four tiles (SOUL S: shorter words, so they are whole on its 124 px tiles)
  struct T {
    const char* en;
    const char* ro;
    const char* enS;
    const char* roS;
    bool on;
    Rgb c;
  } tiles[4] = {{"Quiet", "Liniște", "Quiet", "Liniște", A.dnd, kAmber},
                {"Large text", "Text mare", "Big text", "Mărit", set_.largeText != 0, kMint},
                {"Find phone", "Telefonul", "Phone", "Telefon", A.findState == 1 || A.findState == 2, kAmber},
                {"Sleep", "Somn", "Sleep", "Somn", false, kCream}};
  const float ik = C.iconK;
  for (int i = 0; i < 4; ++i) {
    const T& t = tiles[i];
    const float kx = C.tileX[i % 2], ky = C.tileY[i / 2], iy = ky + C.iconDy;
    const Rgb ink = t.on ? (t.c == kMint ? Rgb::hex(0x06231B) : Rgb::hex(0x2A1700)) : kCream;
    pebRect(cv, kx - C.tileW * 0.5f, ky - C.tileH * 0.5f, kx + C.tileW * 0.5f, ky + C.tileH * 0.5f, C.tileR, t.on ? t.c : pal_.peb, pal_.pebe, 0);
    if (i == 0) {  // a crescent
      cv.ellipse(g_.s(kx), g_.s(iy), g_.s(10 * ik), g_.s(10 * ik), ink, fade_);
      cv.ellipse(g_.s(kx + 5 * ik), g_.s(iy - 4 * ik), g_.s(9 * ik), g_.s(9 * ik), t.on ? t.c : pal_.peb, fade_);
    } else if (i == 1) {
      textAt(cv, fonts::name(), kx, iy, "Aa", ink, 1);
    } else if (i == 2) {
      drawGlyph(cv, AppId::FindPhone, kx, iy, 24 * ik, ink, 1, g_.s(3 * ik));
    } else {
      cv.arc(g_.s(kx - 7 * ik), g_.s(iy - 4 * ik), g_.s(5 * ik), 0.2f, kPi - 0.2f, g_.s(3 * ik), ink, fade_);
      cv.arc(g_.s(kx + 7 * ik), g_.s(iy - 4 * ik), g_.s(5 * ik), 0.2f, kPi - 0.2f, g_.s(3 * ik), ink, fade_);
    }
    const char* label = sGlass() ? (R ? t.roS : t.enS) : (R ? t.ro : t.en);
    textAt(cv, fonts::caption(), kx, ky + C.labelDy, fit(fonts::caption(), label, g_.s(C.labelW)), ink, 1);
  }
  const std::string ai = std::string("AI \xC2\xB7 ") +
                         (aiMode() == AiMode::None ? (R ? "fără" : "none") : aiMode() == AiMode::Cloud ? "SOUL Cloud"
                          : aiMode() == AiMode::ChatGpt ? "ChatGPT" : "Claude");
  // (M: the body face, wider than its 180 px hit box; S: the caption face, inside its 236 px one)
  const Font& af = sGlass() ? fonts::caption() : fonts::body();
  textAt(cv, af, 233, C.aiY + C.aiTextDy, ai, aiMode() == AiMode::None ? kCream : kAmber);
}

// ------------------------------------------------------------- today ---

// Today: one widget at a time, centred in the safe circle under the eyes; the next one waits off the glass
// (swipe up / the crown). Where you are: dots on the left rim.
void Os::drawTodayStack(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, std::string(R ? "Azi \xC2\xB7 " : "Today \xC2\xB7 ") + dayName(now_, R) + " " + hm(now_), kCream);
  const int n = 6, c = A.card % n;
  pebRect(cv, 76, 160, 390, 326, 30, pal_.peb, pal_.pebe, 0);
  for (int i = 0; i < n; ++i) {  // which widget: dashes on the left rim, this one in e1
    const float a = kPi + (i - (n - 1) / 2.0f) * 0.11f;
    rimRing(cv, 214, a - 0.03f, a + 0.03f, i == c ? pal_.e1 : pal_.peb2, 1, 6);
  }
  char b[96];
  switch (c) {
    case 0: {  // now
      textAt(cv, fonts::caption(), 233, 186, R ? "Acum" : "Now", kCream, kDim);
      textAt(cv, fonts::digits(), 233, 246, hm(now_), kCream);
      const std::string na = nextAlarmText();
      textAt(cv, fonts::caption(), 233, 300, fit(fonts::caption(), na.empty() ? (R ? "nicio alarmă" : "no alarm set") : (R ? "alarmă " : "alarm ") + na, g_.s(280)), kCream, kDim);
      break;
    }
    case 1: {  // weather
      const std::string place = A.weather.place.empty() ? std::string() : " \xC2\xB7 " + A.weather.place;
      textAt(cv, fonts::caption(), 233, 186, fit(fonts::caption(), std::string(R ? "Vremea" : "Weather") + place, g_.s(280)), kCream, kDim);
      if (A.weather.ok) {
        drawSky(cv, A.weather.sky, 180, 244, 52, 1);
        snprintf(b, sizeof b, "%d", A.weather.t);
        textAt(cv, fonts::digits(), 274, 244, b, kCream);
        cv.ring(g_.s(274) + Canvas::measureText(fonts::digits(), b) * 0.5f + g_.s(10), g_.s(216), g_.s(6), g_.s(3.5f), kCream, fade_);
        snprintf(b, sizeof b, "%s \xC2\xB7 \xE2\x86\x91%d\xC2\xB0 \xE2\x86\x93%d\xC2\xB0", A.weather.word.c_str(), A.weather.hi, A.weather.lo);
        textAt(cv, fonts::caption(), 233, 300, fit(fonts::caption(), b, g_.s(280)), kCream, kDim);
      } else {
        textAt(cv, fonts::body(), 233, 244, A.wxWait ? (R ? "Întreb cerul…" : "Asking the sky…") : (R ? "Atinge pentru vreme" : "Tap for the weather"), kCream, kDim);
      }
      break;
    }
    case 2: {  // the next event
      textAt(cv, fonts::caption(), 233, 186, R ? "Urmează" : "Next", kCream, kDim);
      const int i = A.agenda.ok ? A.agenda.next(now_) : -1;
      if (i >= 0) {
        const apps::Event& e = A.agenda.events[i];
        textAt(cv, fonts::title(), 233, 228, e.allDay ? (R ? "toată ziua" : "all day") : hm(e.start), kCream);
        textAt(cv, fonts::body(), 233, 268, fit(fonts::body(), e.title, g_.s(280)), kCream);
        if (!e.place.empty()) textAt(cv, fonts::caption(), 233, 300, fit(fonts::caption(), e.place, g_.s(280)), kCream, kDim);
      } else {
        textAt(cv, fonts::body(), 233, 244, A.agenda.ok ? (R ? "Nimic în calendar" : "Nothing on the calendar") : (R ? "Calendarul tău" : "Your calendar"), kCream, kDim);
        if (!A.agenda.ok) textAt(cv, fonts::caption(), 233, 284, R ? "îl legi din /me/where" : "link it on /me/where", kCream, kDim);
      }
      break;
    }
    case 3: {  // focus / timer / a reminder
      textAt(cv, fonts::caption(), 233, 186, "Focus", kCream, kDim);
      if (A.pomo.phase() != apps::Pomodoro::Phase::Idle) {
        textAt(cv, fonts::digits(), 233, 246, apps::Stopwatch::format(A.pomo.left(), false), kCream);
        snprintf(b, sizeof b, R ? "runda %d din %d" : "round %d of %d", A.pomo.round(), A.pomo.rounds);
        textAt(cv, fonts::caption(), 233, 300, b, kCream, kDim);
      } else if (timerRun_) {
        snprintf(b, sizeof b, "%d:%02d", timerLeft() / 60, timerLeft() % 60);
        textAt(cv, fonts::digits(), 233, 246, b, kCream);
        textAt(cv, fonts::caption(), 233, 300, R ? "minutar" : "timer", kCream, kDim);
      } else if (!rems_.empty()) {
        textAt(cv, fonts::title(), 233, 236, hm(rems_.front().when), kCream);
        textAt(cv, fonts::body(), 233, 280, fit(fonts::body(), rems_.front().text, g_.s(280)), kCream, kDim);
      } else {
        textAt(cv, fonts::body(), 233, 240, R ? "25 de minute de liniște?" : "25 quiet minutes?", kCream);
        textAt(cv, fonts::caption(), 233, 280, R ? "atinge: Focus" : "tap: Focus", kCream, kDim);
      }
      break;
    }
    case 4: {  // habits
      textAt(cv, fonts::caption(), 233, 186, R ? "Obiceiuri" : "Habits", kCream, kDim);
      int d = 0;
      for (const apps::Habit& h : A.habits) d += h.doneOn(now_ / 86400);
      snprintf(b, sizeof b, "%d / %d", d, (int)A.habits.size());
      textAt(cv, fonts::title(), 233, 236, b, d == (int)A.habits.size() && d ? kMint : kCream);
      const int total = (int)A.habits.size();
      for (int i = 0; i < total; ++i) {
        const float x = 233 + (i - (total - 1) / 2.0f) * 30;
        const bool on = A.habits[i].doneOn(now_ / 86400);
        cv.ellipse(g_.s(x), g_.s(286), g_.s(8), g_.s(8), on ? kMint : pal_.peb2, fade_);
      }
      break;
    }
    default: {  // SOUL itself
      textAt(cv, fonts::caption(), 233, 186, "SOUL", kCream, kDim);
      if (power_.batPct >= 0) snprintf(b, sizeof b, "%d%%%s", power_.batPct, power_.charging ? "+" : "");
      else snprintf(b, sizeof b, "USB");
      textAt(cv, fonts::title(), 233, 236, b, power_.charging ? kMint : kCream);
      const std::string s = claude_.prompt ? (R ? "Claude te așteaptă" : "Claude needs you")
                            : net_.connected ? "Wi-Fi " + net_.ssid : (R ? "fără Wi-Fi" : "no Wi-Fi");
      textAt(cv, fonts::caption(), 233, 284, fit(fonts::caption(), s, g_.s(280)), claude_.prompt ? kAmber : kCream, kDim);
      break;
    }
  }
  rimBottom(cv, c + 1 < n ? (R ? "glisează în sus · atinge = deschide" : "swipe up · tap to open") : (R ? "atinge = deschide" : "tap to open"),
            kCream, kFaint);
}

// ---------------------------------------------------------------- weather ---

void Os::drawWeather(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const apps::Weather& W = A.weather;
  if (!W.ok) {
    rimTop(cv, R ? "Vremea" : "Weather", kCream);
    if (!cloudOk(net_)) {
      textAt(cv, fonts::body(), 233, 186, R ? "Vremea vine prin" : "Weather comes via", kCream);
      textAt(cv, fonts::body(), 233, 218, "SOUL Cloud", pal_.e1);
      std::string l[3];
      const int n = wrapLines(fonts::caption(), R ? "Leagă SOUL de contul tău: Setări › AI › SOUL Cloud." : "Pair SOUL with your account: Settings › AI › SOUL Cloud.", g_.s(L(290, 340)), l, 3);
      for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(260, 250) + i * L(26, 34), l[i], kCream, kDim);
    } else if (A.wxWait) {
      const float pulse = 0.6f + 0.35f * sinf(animT() * 3.0f);
      drawSky(cv, apps::Sky::Part, 233, 236, 64, pulse);
      textAt(cv, fonts::body(), 233, 306, R ? "Întreb cerul…" : "Asking the sky…", kCream, pulse);
    } else if (A.wxErr == 409) {  // no location yet
      textAt(cv, fonts::body(), 233, L(168, 156), R ? "Unde ești?" : "Where are you?", kCream);
      textAt(cv, fonts::caption(), 233, L(196, 192), sGlass() ? (R ? "N-am GPS: spune-mi din telefon" : "No GPS: tell me from your phone")
                                                            : (R ? "SOUL n-are GPS: spune-i din telefon" : "No GPS here: tell me from your phone"), kCream, kDim);
      drawQr(cv, meWhere(net_, birth_.chip), 233, L(292, 290), L(128, 116));
      rimBottom(cv, R ? "scanează: Trimite locația" : "scan: Share my location", kCream, kFaint);
    } else {
      textAt(cv, fonts::body(), 233, 214, A.wxErr == 501 ? (R ? "Vremea nu e pornită" : "Weather isn't set up")
                                       : A.wxErr < 0 ? (R ? "Fără internet" : "No internet") : (R ? "Vremea nu răspunde" : "No answer from the weather"),
             kAmber);
      textAt(cv, fonts::caption(), 233, 248, A.wxErr < 0 ? (R ? "încerc când revin online" : "I'll try when I'm back online") : (R ? "mai încerc puțin mai târziu" : "I'll try again in a bit"), kCream, kDim);
      buildItems(items_);
      drawItems(cv, items_);
    }
    return;
  }
  std::string top = std::string(R ? "Azi" : "Today") + " \xC2\xB7 " + (W.place.empty() ? std::string(R ? "aici" : "here") : W.place);
  const std::string age = now_ - W.at > 1800 ? ago(now_, W.at, R) : "";
  if (!age.empty()) top += " \xC2\xB7 " + age;
  rimTop(cv, top, kCream);
  char b[64];
  if (A.wxPage == 0) {
    // (SOUL S: everything 20 px higher and the hours' pebble wider, clear of the bottom rim's words)
    const float ty = L(206, 176);
    drawSky(cv, W.sky, L(162, 150), ty, L(58, 64), 1);
    snprintf(b, sizeof b, "%d", W.t);
    const int tw = Canvas::measureText(fonts::digits(), b);
    textAt(cv, fonts::digits(), 274, ty, b, kCream);
    cv.ring(g_.s(274) + tw * 0.5f + g_.s(10), g_.s(ty - 28), g_.s(6), g_.s(3.5f), kCream, fade_);  // the degree sign
    snprintf(b, sizeof b, "%s \xC2\xB7 \xE2\x86\x91%d\xC2\xB0 \xE2\x86\x93%d\xC2\xB0", W.word.c_str(), W.hi, W.lo);
    textAt(cv, fonts::body(), 233, L(270, 240), fit(fonts::body(), b, g_.s(L(320, 380))), kCream);
    // the next hours on a pebble
    pebRect(cv, L(84, 88), L(296, 264), L(382, 378), L(392, 360), 30, pal_.peb, pal_.pebe, 0);
    const int n = (int)W.hours.size() < 5 ? (int)W.hours.size() : 5;
    for (int i = 0; i < n; ++i) {
      const float x = 233 + (i - (n - 1) / 2.0f) * L(54, 58);
      textAt(cv, fonts::caption(), x, L(316, 284), W.hours[i].hh, kCream, kDim);
      drawSky(cv, W.hours[i].sky, x, L(343, 312), L(20, 24), 1);
      snprintf(b, sizeof b, "%d\xC2\xB0", W.hours[i].t);
      textAt(cv, fonts::caption(), x, L(372, 340), b, kCream);
    }
  } else {
    for (int i = 0; i < (int)W.days.size() && i < 3; ++i) {
      const float y = 194 + i * 70;
      pebRect(cv, 86, y - 30, 380, y + 30, 22, pal_.peb, pal_.pebe, 0);
      textAt(cv, fonts::body(), 110, y, W.days[i].name, kCream, 1, Align::Left);
      drawSky(cv, W.days[i].sky, 214, y, 30, 1);
      snprintf(b, sizeof b, "%d\xC2\xB0 / %d\xC2\xB0", W.days[i].hi, W.days[i].lo);
      textAt(cv, fonts::body(), 358, y, b, kCream, 1, Align::Right);
    }
  }
  rimBottom(cv, std::string(A.wxPage ? (R ? "‹ azi" : "‹ today") : (R ? "zilele ›" : "days ›")) + " \xC2\xB7 Open-Meteo", kCream, kFaint);
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
    TextProbe* const probe = Canvas::probe;  // the map's own labels are the map (not the screen's words): not audited
    Canvas::probe = nullptr;
    static maps::MapPainter painter;
    A.view.screenW = W;
    A.view.screenH = H;
    painter.paint(layer, A.bundle, A.view, &fonts::caption());
    Canvas::probe = probe;
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
    rimTop(cv, R ? "Hărți" : "Maps", kCream);
    if (!cloudOk(net_)) {
      textAt(cv, fonts::body(), 233, L(186, 160), R ? "Hărțile vin prin" : "Maps come via", kCream);
      textAt(cv, fonts::body(), 233, L(218, 202), "SOUL Cloud", pal_.e1);
      std::string l[4];
      const int n = wrapLines(fonts::caption(), R ? "SOUL n-are GPS. Leagă-l de cont (Setări › AI › SOUL Cloud) și trimite-i locația din telefon."
                                                  : "SOUL has no GPS. Pair it (Settings › AI › SOUL Cloud), then share your location from your phone.",
                              g_.s(L(290, 340)), l, 4);
      for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(258, 244) + i * L(26, 34), l[i], kCream, kDim);
      return;
    }
    // (SOUL S: the hint in fewer words, the QR a little smaller, so the pill under it keeps 68 px)
    textAt(cv, fonts::body(), 233, L(168, 156), A.whereWait ? (R ? "Unde sunt?…" : "Where am I?…") : (R ? "Unde ești?" : "Where are you?"), kCream);
    textAt(cv, fonts::caption(), 233, L(196, 192), sGlass() ? (R ? "N-am GPS: îmi spune telefonul" : "No GPS: your phone tells me")
                                                          : (R ? "N-am GPS: telefonul tău îmi spune" : "No GPS here: your phone tells me"), kCream, kDim);
    drawQr(cv, meWhere(net_, birth_.chip), 233, L(280, 276), L(116, 104));
    buildItems(items_);
    drawItems(cv, items_);
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
    mp.paintYou(cv, sx, sy, accPx, animT());
  }
  // a dark band at the rim keeps the words on the rim readable over the map
  face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(226), g_.s(22), kDark, 0.55f);
  if (A.sendSheet) {  // "Send to phone": a QR that opens Google Maps
    pebRect(cv, 96, 150, 370, 360, 30, pal_.peb, pal_.pebe, 0);
    textAt(cv, fonts::body(), 233, 172, R ? "Pe telefon" : "On your phone", kCream);
    drawQr(cv, A.sendUrl, 233, 266, 140);
    textAt(cv, fonts::caption(), 233, 344, R ? "se deschide Google Maps" : "opens Google Maps", kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    return;
  }
  if (A.navOn && A.route.valid()) {
    const int s = A.nav.step();
    const maps::Step& st = A.route.steps[s < (int)A.route.steps.size() ? s : (int)A.route.steps.size() - 1];
    const bool off = A.nav.offRoute(), arrived = A.nav.arrived();
    // the step card under the eyes: the arrow (relative to the line you walk: SOUL has no compass), the distance, the street
    // (SOUL S: the card between the 68 px ‹ › discs, its three lines 34 px apart)
    const float cx0 = L(100, 92), cx1 = L(366, 374), cy0 = L(154, 132), cy1 = L(262, 290), tx = L(270, 268), tw = L(170, 196);
    pebRect(cv, cx0, cy0, cx1, cy1, 28, arrived ? Rgb::lerp(pal_.peb, kMint, 0.25f) : pal_.peb, arrived ? kMint : off ? kAmber : pal_.pebe,
            arrived || off ? 3 : 0);
    if (arrived) {
      textAt(cv, fonts::title(), 233, L(196, 180), R ? "Ai ajuns" : "You're there", kMint);
      textAt(cv, fonts::caption(), 233, L(234, 230), fit(fonts::caption(), A.route.to, g_.s(L(230, 250))), kCream, kDim);
    } else if (off) {
      textAt(cv, fonts::body(), 233, L(186, 170), R ? "Ai ieșit de pe traseu" : "Off the route", kAmber);
      textAt(cv, fonts::caption(), 233, L(216, 212), fit(fonts::caption(), R ? "înapoi la linia portocalie" : "back to the amber line", g_.s(L(260, 260))), kCream, kDim);
      textAt(cv, fonts::caption(), 233, L(242, 246), R ? "sau ține apăsat: oprește" : "or hold: end it", kCream, kDim);
    } else {
      drawArrow(cv, L(156, 140), L(208, 212), L(58, 64), A.route.turnAngle(s), kCream, 1);
      const int d = (int)A.nav.toTurnM();
      if (d >= 1000) snprintf(b, sizeof b, "%.1f km", d / 1000.0);
      else snprintf(b, sizeof b, "%d m", (d + 5) / 10 * 10);
      textAt(cv, fonts::title(), tx, L(190, 172), b, kCream);
      textAt(cv, fonts::caption(), tx, L(222, 214), fit(fonts::caption(), maps::turnWord(st.turn, R), g_.s(tw)), kCream, kDim);
      if (!st.street.empty()) textAt(cv, fonts::caption(), tx, L(246, 248), fit(fonts::caption(), st.street, g_.s(tw)), kCream, kDim);
    }
    buildItems(items_);
    std::vector<Item> pills;
    for (const Item& it : items_)
      if (it.id == APrev || it.id == ANext) {  // ‹ › discs (their own chevron: not the item's label as well)
        cv.ellipse(g_.s(it.x), g_.s(it.y), g_.s(it.w * 0.5f), g_.s(it.w * 0.5f), pal_.peb2, fade_);
        textAt(cv, fonts::name(), it.x, it.y - 2, it.label, kCream);
      } else if (it.underline) {
        pills.push_back(it);
      }
    drawItems(cv, pills);
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
    pebRect(cv, L(86, 70), L(154, 134), L(380, 396), L(240, 246), 28, pal_.peb, pal_.pebe, 0);
    textAt(cv, fonts::body(), 233, L(182, 166), fit(fonts::body(), A.route.to, g_.s(L(260, 300))), kCream);
    const int min = (A.route.durS + 59) / 60;
    snprintf(b, sizeof b, "%.1f km \xC2\xB7 %d min \xC2\xB7 %s", A.route.distM / 1000.0, min, hm(now_ + (uint32_t)A.route.durS).c_str());
    textAt(cv, fonts::caption(), 233, L(214, 210), sGlass() ? fit(fonts::caption(), b, g_.s(300)) : std::string(b), kCream, kDim);
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
    snprintf(b, sizeof b, "%s \xC2\xB7 ~%d m%s%s \xC2\xB7 z%d", A.fixSrc == "wifi" ? "Wi-Fi" : (R ? "telefon" : "phone"), (int)A.fix.accM,
             age > 300 ? " \xC2\xB7 " : "", age > 300 ? ago(now_, A.fix.at, R).c_str() : "", v.z);
    top = b;
  }
  if (!top.empty()) rimTop(cv, top, A.mapErr ? kAmber : kCream, kDim);
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id == APlus || it.id == AMinus || it.id == ACenter) {
      cv.ellipse(g_.s(it.x), g_.s(it.y), g_.s(it.w * 0.5f), g_.s(it.w * 0.5f), pal_.peb, fade_);
      cv.ring(g_.s(it.x), g_.s(it.y), g_.s(it.w * 0.5f - 1.5f), g_.s(3), pal_.pebe, fade_);
      if (it.id == ACenter) {
        cv.ring(g_.s(it.x), g_.s(it.y), g_.s(9), g_.s(3), A.followMe ? kIce : kCream, fade_);
        cv.ellipse(g_.s(it.x), g_.s(it.y), g_.s(3.5f), g_.s(3.5f), A.followMe ? kIce : kCream, fade_);
      } else {
        if (it.id == APlus) plusMark(cv, it.x, it.y, 18, kCream);
        else cv.segment(g_.s(it.x - 9), g_.s(it.y), g_.s(it.x + 9), g_.s(it.y), fmaxf(2.6f, g_.s(3)), kCream, fade_);
      }
    }
  }
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  drawItems(cv, pills);
  rimBottom(cv, R ? "date hartă: OpenStreetMap" : "map data: OpenStreetMap", kCream, kFaint);  // ODbL attribution
}

// --------------------------------------------------------------- calendar ---

void Os::drawCalendar(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, std::string(R ? "Agenda · " : "Agenda · ") + dayName(now_, R), kCream);
  if (!A.agenda.ok) {
    if (A.calWait) {
      const float pulse = 0.6f + 0.35f * sinf(animT() * 3.0f);
      textAt(cv, fonts::body(), 233, 240, R ? "Citesc calendarul…" : "Reading your calendar…", kCream, pulse);
    } else if (!cloudOk(net_) || A.calErr == 404) {
      textAt(cv, fonts::body(), 233, 168, R ? "Leagă-ți calendarul" : "Link your calendar", kCream);
      textAt(cv, fonts::caption(), 233, 196, R ? "pe telefon: adresa ICS, doar citire" : "on your phone: its ICS address, read-only", kCream, kDim);
      if (cloudOk(net_)) drawQr(cv, meWhere(net_, birth_.chip), 233, 296, 128);
      else textAt(cv, fonts::caption(), 233, 240, R ? "întâi: Setări › AI › SOUL Cloud" : "first: Settings › AI › SOUL Cloud", kAmber);
    } else {
      textAt(cv, fonts::body(), 233, 236, A.calErr < 0 ? (R ? "Fără internet" : "No internet") : (R ? "Calendarul nu răspunde" : "The calendar didn't answer"), kAmber);
      buildItems(items_);
      drawItems(cv, items_);
    }
    return;
  }
  if (A.agenda.events.empty()) {
    textAt(cv, fonts::body(), 233, 236, R ? "Nimic în 7 zile" : "Nothing in 7 days", kCream);
    textAt(cv, fonts::caption(), 233, 268, R ? "zile libere" : "free days", kMint);
    return;
  }
  if (A.calSel >= 0 && A.calSel < (int)A.agenda.events.size()) {
    const apps::Event& e = A.agenda.events[A.calSel];
    std::string l[3];
    const float lp = L(32, 44), x0 = L(84, 66), top = L(152, 136);  // (S: the S body face, 44 px a line)
    const int n = wrapLines(fonts::body(), e.title, g_.s(L(270, 300)), l, 3);
    pebRect(cv, x0, top, 466 - x0, top + 62 + n * lp + (e.place.empty() ? 0 : L(28, 38)), 30, pal_.peb, pal_.e1, 3);
    std::string when = std::string(dayName(e.start, R)) + " " + (e.allDay ? (R ? "toată ziua" : "all day") : hm(e.start) + "\xE2\x80\x93" + hm(e.end));
    textAt(cv, fonts::caption(), 233, top + 26, when, kCream, kDim);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::body(), 233, top + 58 + i * lp + L(0, 8), l[i], kCream);
    if (!e.place.empty()) textAt(cv, fonts::caption(), 233, top + 58 + n * lp + L(0, 4), fit(fonts::caption(), e.place, g_.s(L(270, 300))), kCream, kDim);
    rimBottom(cv, R ? "atinge: înapoi" : "tap: back", kCream, kFaint);
    return;
  }
  drawWheel(cv);
}

// ------------------------------------------------------------------ music ---

void Os::drawMusic(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, R ? "Sunete de focus" : "Focus sounds", kCream);
  if (!A.speaker) {
    textAt(cv, fonts::body(), 233, 176, R ? "SOUL-ul ăsta n-are difuzor" : "This SOUL has no speaker", kCream);
    std::string l[6];
    const int n = wrapLines(fonts::caption(),
                            R ? "Pe SOUL M se adaugă amplificatorul I2S (MAX98357A). Muzica de pe telefon: vine cu aplicația SOUL "
                                "(iPhone: Apple Media Service prin Bluetooth)."
                              : "SOUL M takes an I2S amp (MAX98357A). Your phone's music: coming with the SOUL app "
                                "(iPhone: Apple Media Service over Bluetooth).",
                            g_.s(290), l, 6);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, 214 + i * 26, l[i], kCream, kDim);
    return;
  }
  const char* name = SoundGen::name(A.sound.kind(), R);
  const MusicSpec M = musicSpecFor(dens_);
  textAt(cv, fonts::name(), 233, M.nameY, name, kCream);
  static const char* const en[] = {"on a window, far thunder", "deep and even", "slow waves", "a crackling fire"};
  static const char* const r[] = {"pe geam, tunet departe", "adânc și egal", "valuri încete", "un foc care trosnește"};
  textAt(cv, fonts::caption(), 233, M.wordsY, (R ? r : en)[A.sound.kind() % 4], kCream, kDim);
  // prev / play / next: discs (play filled e1)
  const float px0 = 233 - M.dx, px1 = 233 + M.dx, sr = M.side * 0.5f - 1;
  cv.ellipse(g_.s(px0), g_.s(M.y), g_.s(sr), g_.s(sr), pal_.peb2, fade_);
  cv.ring(g_.s(px0), g_.s(M.y), g_.s(sr - 1.5f), g_.s(3), pal_.pebe, fade_);
  cv.ellipse(g_.s(px1), g_.s(M.y), g_.s(sr), g_.s(sr), pal_.peb2, fade_);
  cv.ring(g_.s(px1), g_.s(M.y), g_.s(sr - 1.5f), g_.s(3), pal_.pebe, fade_);
  cv.ellipse(g_.s(233), g_.s(M.y), g_.s(M.play * 0.5f), g_.s(M.play * 0.5f), A.playing ? pal_.e1 : kMint, fade_);
  Path& p = scratchPath();
  if (p.reserve(256)) {
    p.clear();
    const float x = g_.s(233), y = g_.s(M.y), s = g_.s(M.icon);
    if (A.playing) {
      p.roundRect(x - s * 0.8f, y - s, s * 0.55f, s * 2, s * 0.15f);
      p.roundRect(x + s * 0.25f, y - s, s * 0.55f, s * 2, s * 0.15f);
    } else {
      const float tri[] = {x - s * 0.6f, y - s, x + s, y, x - s * 0.6f, y + s};
      p.polygon(tri, 3);
    }
    face_.raster().fill(cv, p, A.playing ? pal_.on1 : Rgb::hex(0x06231B), fade_);
    p.clear();
    const float a = g_.s(px0), c = g_.s(px1), k = g_.s(M.tri);
    const float pv[] = {a + k * 0.7f, y - k, a - k * 0.6f, y, a + k * 0.7f, y + k};
    const float nx[] = {c - k * 0.7f, y - k, c + k * 0.6f, y, c - k * 0.7f, y + k};
    p.polygon(pv, 3);
    p.polygon(nx, 3);
    face_.raster().fill(cv, p, kCream, fade_);
  }
  // the volume on the right rim (set it in Control)
  const float v0 = 52 * kPi / 180, vk = v0 - 104 * kPi / 180 * A.volume;
  rimRing(cv, 214, -52 * kPi / 180, v0, pal_.peb2, 1, 8);
  if (A.volume > 0.01f) rimRing(cv, 214, vk, v0, pal_.e2, 1, 8);
  buildItems(items_);
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  drawItems(cv, pills);
}

// ------------------------------------------------------------------ games ---

// The games' arena (a flat ring) only changes with the palette, so it is drawn once into a PSRAM layer and
// copied in afterwards (bench_games, BRINGUP §4e).
static std::vector<uint16_t> gArena;
static uint64_t gArenaKey = ~0ull;

static void arenaLayer(Canvas& cv, Raster& ras, uint64_t key, float cx, float cy, float rm, float w, Rgb c) {
  const int W = cv.width(), H = cv.height();
  if (gArena.size() != (size_t)W * H) {
    gArena.assign((size_t)W * H, 0);
    gArenaKey = ~0ull;
  }
  if (key != gArenaKey) {
    Canvas layer(W, H, gArena.data());
    layer.fill(pal::kBlack);
    ras.ring(layer, cx, cy, rm, w, c, 1.0f);
    gArenaKey = key;
  }
  const Rect& cl = cv.clipRect();
  for (int y = cl.y0; y < cl.y1; ++y)
    memcpy(cv.data() + y * W + cl.x0, gArena.data() + y * W + cl.x0, (size_t)(cl.x1 - cl.x0) * 2);
  cv.markDirty(cl);
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
    rimTop(cv, R ? "Jocuri" : "Games", kCream);
    drawWheel(cv);
    return;
  }
  const float cx = g_.cx(), cy = g_.cy();
  const uint64_t key = (uint64_t)A.game | (uint64_t)palGen_ << 4 | (uint64_t)(int)(fade_ * 64) << 40;
  bool over = false;
  int score = 0;
  if (A.game == 0) {
    const games::TiltBall& T = A.tilt;
    arenaLayer(cv, face_.raster(), key, cx, cy, g_.s(games::TiltBall::kArena + 6), g_.s(8), pal_.e2.scaled(fade_));
    for (const games::TiltBall::Hole& h : T.holes()) {
      cv.ellipse(cx + g_.s(h.x), cy + g_.s(h.y), g_.s(games::TiltBall::kHole), g_.s(games::TiltBall::kHole), pal_.peb, fade_);
      cv.ring(cx + g_.s(h.x), cy + g_.s(h.y), g_.s(games::TiltBall::kHole), g_.s(3), kAmber, 0.8f * fade_);
    }
    if (T.running()) cv.star(cx + g_.s(T.star().x), cy + g_.s(T.star().y), g_.s(games::TiltBall::kStar), animT() * 1.5f, Rgb::hex(0xFFD76B), fade_);
    cv.ellipse(cx + g_.s(T.x()), cy + g_.s(T.y()), g_.s(games::TiltBall::kBall), g_.s(games::TiltBall::kBall), pal_.e1, fade_);
    if (T.running())
      rimTop(cv, std::to_string(T.score()) + (R ? " stele · " : " stars · ") + std::to_string((int)ceilf(T.left())) + " s · " +
                     std::to_string(T.lives()) + (R ? " vieți" : " lives"), kCream);
    over = T.over();
    score = T.score();
  } else if (A.game == 1) {
    const games::Rhythm& Ry = A.rhythm;
    // the target: the rim; the beats swell out from the eyes
    arenaLayer(cv, face_.raster(), key, cx, cy, g_.s(206), g_.s(8), pal_.peb2.scaled(fade_));
    float fr[8];
    const int n = Ry.visible(fr, 8);
    for (int i = 0; i < n; ++i) {
      const float rr = 60 + fr[i] * 146;
      const float a = fr[i] > 0.92f ? 1.0f : 0.35f + 0.55f * fr[i];
      cv.ring(cx, cy, g_.s(rr), g_.s(4), fr[i] > 0.97f ? kMint : pal_.e1, a);
    }
    if (A.judgeT > 0) {
      const games::Rhythm::Judge j = Ry.lastJudge();
      const char* w = j == games::Rhythm::Perfect ? (R ? "Perfect!" : "Perfect!") : j == games::Rhythm::Good ? (R ? "Bine" : "Good") : (R ? "Ratat" : "Miss");
      textAt(cv, fonts::body(), 233, 360, w, j == games::Rhythm::Perfect ? kMint : j == games::Rhythm::Good ? kCream : kAmber, fminf(1, A.judgeT * 3));
    }
    if (Ry.running()) {
      snprintf(b, sizeof b, "%d  \xC2\xB7  x%d", Ry.score(), Ry.combo());
      rimTop(cv, b, kCream);
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
      cv.ellipse(x, y, g_.s(24), g_.s(24), lit ? (cue == i ? kIce : kMint) : pal_.peb2, fade_);
      if (!lit) cv.ring(x, y, g_.s(22.5f), g_.s(3), pal_.pebe, fade_);
    }
    if (M.phase() == games::EyeMemory::Phase::Show) snprintf(b, sizeof b, R ? "runda %d · privește" : "round %d · watch", M.round());
    else if (M.phase() == games::EyeMemory::Phase::Input) snprintf(b, sizeof b, R ? "runda %d · rândul tău %d/%d" : "round %d · your turn %d/%d", M.round(), M.progress() + 1, M.round());
    else b[0] = 0;
    if (b[0]) rimTop(cv, b, kCream);  // the bottom spot sits where rim words would
    over = M.phase() == games::EyeMemory::Phase::Over;
    score = M.score();
  }
  if (over) {
    // (SOUL S: the card taller and higher, the score's lines clear of the 68 px pills, OsAppsDraw items)
    pebRect(cv, L(92, 78), L(170, 130), L(374, 388), L(372, 392), 34, pal_.peb, A.newBest ? kMint : pal_.pebe, A.newBest ? 3 : 0);
    textAt(cv, fonts::caption(), 233, L(194, 158), R ? "Gata" : "Game over", kCream, kDim);
    textAt(cv, fonts::digits(), 233, L(244, 212), std::to_string(score), A.newBest ? kMint : kCream);
    snprintf(b, sizeof b, A.newBest ? (R ? "record nou!" : "new best!") : (R ? "recordul: %d" : "best: %d"), A.best[A.game]);
    textAt(cv, fonts::caption(), 233, L(290, 266), b, A.newBest ? kMint : kCream, A.newBest ? 1 : kDim);
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
  if (idle) snprintf(b, sizeof b, "%s", "Focus · 25 + 5");
  else if (rest) snprintf(b, sizeof b, "%s", P.phase() == apps::Pomodoro::Phase::Long ? (R ? "Pauză lungă" : "Long break") : (R ? "Pauză" : "Break"));
  else snprintf(b, sizeof b, R ? "Focus · %d din %d" : "Focus · %d of %d", P.round(), P.rounds);
  rimRing(cv, 216, 0, 2 * kPi, pal_.peb2, 1, 8);
  const float frac = idle ? 1.0f : P.left() / P.total();
  if (frac > 0.002f) rimRing(cv, 216, -kPi / 2, -kPi / 2 + 2 * kPi * frac, rest ? kMint : pal_.e1, 1, 8);
  rimTop(cv, b, rest ? kMint : kCream);
  textAt(cv, fonts::digits(), 233, 222, apps::Stopwatch::format(idle ? P.focusMin * 60.0f : P.left(), false), P.paused() ? kAmber : rest ? kMint : kCream);
  // rounds as dots
  for (int i = 0; i < P.rounds; ++i) {
    const bool done = i < (P.done() % P.rounds) || (!idle && i < P.round() - 1);
    cv.ellipse(g_.s(233 + (i - 1.5f) * 22), g_.s(270), g_.s(5), g_.s(5), done ? pal_.e1 : pal_.peb2, fade_);
  }
  cv.ellipse(g_.s(233), g_.s(326), g_.s(39), g_.s(39), idle ? kMint : pal_.peb2, fade_);
  if (!idle) cv.ring(g_.s(233), g_.s(326), g_.s(37.5f), g_.s(3), pal_.pebe, fade_);
  Path& p = scratchPath();
  if (p.reserve(128)) {
    p.clear();
    const float x = g_.s(233), y = g_.s(326), s = g_.s(13);
    if (!idle && !P.paused()) {
      p.roundRect(x - s * 0.8f, y - s, s * 0.55f, s * 2, s * 0.15f);
      p.roundRect(x + s * 0.25f, y - s, s * 0.55f, s * 2, s * 0.15f);
    } else {
      const float tri[] = {x - s * 0.6f, y - s, x + s, y, x - s * 0.6f, y + s};
      p.polygon(tri, 3);
    }
    face_.raster().fill(cv, p, idle ? Rgb::hex(0x06231B) : kCream, fade_);
  }
  if (idle) textAt(cv, fonts::caption(), 233, 384, R ? "Atinge = start" : "Tap = start", kCream, kDim);
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
  if (!A.breathing) {  // a face moment: the eyes, two pills, how to begin
    rimTop(cv, R ? "Respiră" : "Breathe", kCream);
    buildItems(items_);
    drawItems(cv, items_);
    rimBottom(cv, R ? "atinge ochii ca să începi" : "tap the eyes to begin", kCream, kFaint);
    return;
  }
  const apps::BreathPoint b = apps::breathAt(p, A.breathT);
  // a ring that breathes with the eyes
  const float r = g_.s(150 + 54 * b.size);
  cv.ring(g_.cx(), g_.cy() - g_.s(8), r, g_.s(8), b.phase == 0 || b.phase == 1 ? kIce : kMint, 0.35f + 0.4f * b.size);
  static const char* const en[] = {"Breathe in", "Hold", "Breathe out", "Hold"};
  static const char* const ro_[] = {"Inspiră", "Ține", "Expiră", "Ține"};
  const float d[4] = {p.in, p.hold1, p.out, p.hold2};
  const int left = (int)ceilf(d[b.phase] * (1 - b.progress));
  rimBottomCap(cv, std::string(R ? ro_[b.phase] : en[b.phase]) + " \xC2\xB7 " + std::to_string(left), b.phase == 2 ? kMint : kIce, 1, true);
  const int total = A.breathMin * 60, rest = total - (int)A.breathT;
  char t[24];
  snprintf(t, sizeof t, "%d:%02d", rest / 60, rest % 60);
  rimTop(cv, t, kCream);
}

// ----------------------------------------------------------------- habits ---

void Os::drawHabits(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const uint32_t today = now_ / 86400;
  int d = 0;
  for (const apps::Habit& h : A.habits) d += h.doneOn(today);
  char b[48];
  snprintf(b, sizeof b, R ? "Obiceiuri · %d din %d azi" : "Habits · %d of %d today", d, (int)A.habits.size());
  rimTop(cv, b, d == (int)A.habits.size() && d ? kMint : kCream);
  if (A.habits.empty() && wheel_.focused() == 0) textAt(cv, fonts::caption(), 233, 200, R ? "Niciun obicei încă" : "No habits yet", kCream, kDim);
  drawWheel(cv);
}

// -------------------------------------------------------------- stopwatch ---

void Os::drawStopwatch(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, R ? "Cronometru" : "Stopwatch", kCream);
  const std::string s = apps::Stopwatch::format(A.sw.acc, true);
  const size_t dot = s.find('.');
  const std::string main = dot == std::string::npos ? s : s.substr(0, dot), tenth = dot == std::string::npos ? "" : s.substr(dot);
  const int mw = Canvas::measureText(fonts::digits(), main.c_str()), tw = Canvas::measureText(fonts::title(), tenth.c_str());
  const float x0 = g_.cx() - (mw + tw) * 0.5f;
  cv.drawText(fonts::digits(), x0, (int)g_.s(232), main.c_str(), kCream, fade_, Align::Left);
  cv.drawText(fonts::title(), x0 + mw, (int)g_.s(232), tenth.c_str(), kCream, kDim * fade_, Align::Left);
  const int n = (int)A.sw.laps.size();
  for (int k = 0; k < 2 && k < n; ++k) {
    const int i = n - 1 - k;
    const double split = A.sw.laps[i] - (i ? A.sw.laps[i - 1] : 0);
    char b[48];
    snprintf(b, sizeof b, R ? "tura %d   %s" : "lap %d   %s", i + 1, apps::Stopwatch::format(split, true).c_str());
    textAt(cv, fonts::caption(), 233, 268 + k * L(24, 34), b, kCream, kDim);
  }
  // lap / reset: a peb2 disc; start / pause: mint / amber (S: 72 px discs, 6 px higher, Density.h)
  const bool any = A.sw.acc > 0 || A.sw.run;
  const float by = L(352, 346), br = L(34, 36), dy = by - 352;
  cv.ellipse(g_.s(170), g_.s(by), g_.s(br), g_.s(br), pal_.peb2, fade_);
  cv.ring(g_.s(170), g_.s(by), g_.s(br - 1.5f), g_.s(3), pal_.pebe, fade_);
  if (A.sw.run) {  // a flag: lap
    cv.segment(g_.s(163), g_.s(342 + dy), g_.s(163), g_.s(364 + dy), g_.s(3), kCream, fade_);
    cv.roundRect(g_.s(163), g_.s(341 + dy), g_.s(178), g_.s(352 + dy), 2, kCream, fade_);
  } else {  // ↺ reset
    cv.arc(g_.s(170), g_.s(by), g_.s(10), -2.4f, 2.0f, g_.s(3), kCream, (any ? 1.0f : 0.5f) * fade_);
    cv.segment(g_.s(161), g_.s(340 + dy), g_.s(162), g_.s(346 + dy), g_.s(3), kCream, (any ? 1.0f : 0.5f) * fade_);
  }
  cv.ellipse(g_.s(296), g_.s(by), g_.s(br), g_.s(br), A.sw.run ? kAmber : kMint, fade_);
  Path& p = scratchPath();
  if (p.reserve(128)) {
    p.clear();
    const float x = g_.s(296), y = g_.s(by), k = g_.s(11);
    if (A.sw.run) {
      p.roundRect(x - k * 0.8f, y - k, k * 0.55f, k * 2, k * 0.15f);
      p.roundRect(x + k * 0.25f, y - k, k * 0.55f, k * 2, k * 0.15f);
    } else {
      const float tri[] = {x - k * 0.6f, y - k, x + k, y, x - k * 0.6f, y + k};
      p.polygon(tri, 3);
    }
    face_.raster().fill(cv, p, A.sw.run ? Rgb::hex(0x2A1700) : Rgb::hex(0x06231B), fade_);
  }
}

// ------------------------------------------------------------ world clock ---

void Os::drawWorldClock(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, std::string(R ? "Ora lumii · " : "World clock · ") + hm(now_), kCream);
  drawWheel(cv);
}

// ---------------------------------------------------------------- convert ---

void Os::drawConvert(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const apps::Quantity q = (apps::Quantity)A.q;
  const std::vector<apps::Unit>& u = apps::units(q);
  rimTop(cv, R ? "Convertor" : "Convert", kCream);
  buildItems(items_);
  std::vector<Item> pills;
  for (const Item& it : items_)
    if (it.underline) pills.push_back(it);
  if (sGlass()) {  // SOUL S (ConvertSpec): 72 px fields, the unit pills at their right end, the swap disc on the left
    const ConvertSpec c = convertSpecFor(dens_);
    const double r = apps::convert(q, A.from, A.to, A.value, A.rates);
    float valueX1 = c.x1;
    for (const Item& it : items_)
      if (it.id == AFrom) valueX1 = it.x - it.w * 0.5f - 12;
    const float hh = c.fieldH * 0.5f;
    pebRect(cv, c.x0, c.fromY - hh, c.x1, c.fromY + hh, hh, pal_.peb2, pal_.pebe, 0);
    textAt(cv, fonts::title(), valueX1, c.fromY, fit(fonts::title(), apps::formatNumber(A.value), g_.s(valueX1 - c.x0 - 24)), kCream, 1, Align::Right);
    float resultX1 = c.x1;
    for (const Item& it : items_)
      if (it.id == ATo) resultX1 = it.x - it.w * 0.5f - 12;
    pebRect(cv, c.x0, c.toY - hh, c.x1, c.toY + hh, hh, Rgb::lerp(pal_.peb, kMint, 0.12f), kMint, 3);
    textAt(cv, fonts::title(), resultX1, c.toY, fit(fonts::title(), apps::formatNumber(r), g_.s(resultX1 - c.x0 - 24)), kMint, 1, Align::Right);
    const float sx = c.swapX, sy = c.swapY, sr = c.swap * 0.5f - 1, k = 1.35f;
    cv.ellipse(g_.s(sx), g_.s(sy), g_.s(sr), g_.s(sr), pal_.peb2, fade_);
    cv.ring(g_.s(sx), g_.s(sy), g_.s(sr - 1.5f), g_.s(3), pal_.pebe, fade_);
    cv.segment(g_.s(sx - 7 * k), g_.s(sy - 10 * k), g_.s(sx - 7 * k), g_.s(sy + 10 * k), g_.s(3 * k), kCream, fade_);
    cv.segment(g_.s(sx - 7 * k), g_.s(sy - 10 * k), g_.s(sx - 12 * k), g_.s(sy - 4 * k), g_.s(3 * k), kCream, fade_);
    cv.segment(g_.s(sx + 7 * k), g_.s(sy - 10 * k), g_.s(sx + 7 * k), g_.s(sy + 10 * k), g_.s(3 * k), kCream, fade_);
    cv.segment(g_.s(sx + 7 * k), g_.s(sy + 10 * k), g_.s(sx + 12 * k), g_.s(sy + 4 * k), g_.s(3 * k), kCream, fade_);
    drawItems(cv, pills);
    std::string foot;
    if (q == apps::Quantity::Currency)
      foot = A.rates.fromCloud ? (R ? "curs BCE " : "ECB ") + A.rates.date : (R ? "curs aproximativ" : "approximate rates");
    else
      foot = std::string("1 ") + u[A.from].label + " = " + apps::formatNumber(apps::convert(q, A.from, A.to, 1, A.rates)) + " " + u[A.to].label;
    textAt(cv, fonts::caption(), 233, c.footY, fit(fonts::caption(), foot, g_.s(280)), kCream, kDim);
    return;
  }
  // the number you type (a tap: the keyboard), then the result on a mint-edged field
  pebRect(cv, 74, 206, 392, 258, 26, pal_.peb2, pal_.pebe, 0);
  textAt(cv, fonts::title(), 296, 232, fit(fonts::title(), apps::formatNumber(A.value), g_.s(200)), kCream, 1, Align::Right);
  const double r = apps::convert(q, A.from, A.to, A.value, A.rates);
  pebRect(cv, 74, 302, 392, 354, 26, Rgb::lerp(pal_.peb, kMint, 0.12f), kMint, 3);
  textAt(cv, fonts::title(), 296, 328, fit(fonts::title(), apps::formatNumber(r), g_.s(200)), kMint, 1, Align::Right);
  // the swap disc between them, on the left
  cv.ellipse(g_.s(112), g_.s(280), g_.s(24), g_.s(24), pal_.peb2, fade_);
  cv.ring(g_.s(112), g_.s(280), g_.s(22.5f), g_.s(3), pal_.pebe, fade_);
  cv.segment(g_.s(105), g_.s(270), g_.s(105), g_.s(290), g_.s(3), kCream, fade_);
  cv.segment(g_.s(105), g_.s(270), g_.s(100), g_.s(276), g_.s(3), kCream, fade_);
  cv.segment(g_.s(119), g_.s(270), g_.s(119), g_.s(290), g_.s(3), kCream, fade_);
  cv.segment(g_.s(119), g_.s(290), g_.s(124), g_.s(284), g_.s(3), kCream, fade_);
  drawItems(cv, pills);
  std::string foot;
  if (q == apps::Quantity::Currency)
    foot = A.rates.fromCloud ? (R ? "cursul BCE din " : "ECB rates of ") + A.rates.date : (R ? "curs aproximativ, fără internet" : "approximate rates, offline");
  else
    foot = std::string("1 ") + u[A.from].label + " = " + apps::formatNumber(apps::convert(q, A.from, A.to, 1, A.rates)) + " " + u[A.to].label;
  textAt(cv, fonts::caption(), 233, 382, fit(fonts::caption(), foot, g_.s(280)), kCream, kDim);
}

// ------------------------------------------------------------- find phone ---

void Os::drawFindPhone(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  rimTop(cv, R ? "Găsește telefonul" : "Find my phone", kCream);
  const bool ringing = A.findState == 1 || A.findState == 2;
  if (ringing) {
    const float ph = fmodf(animT() * 0.8f, 1.0f);
    for (int k = 0; k < 2; ++k) {
      const float f = fmodf(ph + k * 0.5f, 1.0f);
      cv.ring(g_.s(233), g_.s(300), g_.s(60 + f * 60), g_.s(4), pal_.e1, (1 - f) * 0.7f * fade_);
    }
  }
  cv.ellipse(g_.s(233), g_.s(300), g_.s(56), g_.s(56), ringing ? kAmber : pal_.e1, fade_);
  drawGlyph(cv, AppId::FindPhone, 233, 300, 40, ringing ? Rgb::hex(0x2A1700) : pal_.on1, 1, g_.s(4));
  std::string s, sub;
  switch (A.findState) {
    case 1: s = R ? "Îl sun…" : "Ringing…"; break;
    case 2: s = R ? "Sună pe /me/where" : "Ringing on /me/where"; sub = R ? "atinge „L-am găsit” pe telefon" : "tap “Found it” on the phone"; break;
    case 3: s = R ? "Notificare trimisă" : "Notification sent"; sub = R ? "nicio pagină deschisă acum" : "no page open right now"; break;
    case 4: s = R ? "Niciun telefon nu ascultă" : "No phone is listening"; sub = R ? "deschide o dată /me/where pe telefon" : "open /me/where on your phone once"; break;
    case 5: s = R ? "Nu pot acum" : "Can't right now"; sub = cloudOk(net_) ? (R ? "fără internet?" : "no internet?") : (R ? "are nevoie de SOUL Cloud" : "needs SOUL Cloud"); break;
    default: s = R ? "Atinge ca să-l sun" : "Tap to ring it"; sub = R ? "chiar și pe silențios, dacă /me/where e deschis" : "even on silent, if /me/where is open"; break;
  }
  textAt(cv, fonts::body(), 233, L(168, 156), fit(fonts::body(), s, g_.s(320)), A.findState >= 4 ? kAmber : kCream);
  std::string sl[2];
  const int ns = sub.empty() ? 0 : wrapLines(fonts::caption(), sub, g_.s(L(280, 340)), sl, 2);
  for (int i = 0; i < ns; ++i) textAt(cv, fonts::caption(), 233, L(198, 192) + i * L(24, 33), sl[i], kCream, kDim);
}

// ----------------------------------------------------------------- device ---

void Os::drawDevice(Canvas& cv) {
  const bool R = ro();
  const AppsState& A = apps_;
  const StorageInfo& S = A.storage;
  // the battery as a ring on the rim
  rimRing(cv, 216, 0, 2 * kPi, pal_.peb2, 1, 8);
  const float lvl = power_.batPct >= 0 ? power_.batPct / 100.0f : 1.0f;
  const Rgb bc = power_.charging ? kMint : power_.batPct >= 0 && power_.batPct < 20 ? kAmber : pal_.e1;
  rimRing(cv, 216, -kPi / 2, -kPi / 2 + 2 * kPi * lvl, bc, 1, 8);
  rimTop(cv, R ? "Dispozitiv" : "Device", kCream);
  char b[96];
  if (power_.batPct >= 0) snprintf(b, sizeof b, "%d%%", power_.batPct);
  else snprintf(b, sizeof b, "USB");
  textAt(cv, fonts::name(), 233, L(176, 154), b, power_.charging ? kMint : kCream);
  textAt(cv, fonts::caption(), 233, L(206, 188), power_.charging ? (R ? "se încarcă" : "charging") : power_.batPct >= 0 ? (R ? "pe baterie" : "on battery") : (R ? "prin USB" : "powered by USB"),
         kCream, kDim);
  pebRect(cv, L(86, 70), L(230, 210), L(380, 396), L(382, 396), 28, pal_.peb, pal_.pebe, 0);
  std::string rows[5];
  snprintf(b, sizeof b, R ? "%d notițe · %d alarme" : "%d notes · %d alarms", (int)notes_.size(), alarms_ ? alarms_->count() : 0);
  rows[0] = b;
  if (S.appMaxKb) snprintf(b, sizeof b, R ? "firmware %.1f din %.1f MB" : "firmware %.1f of %.1f MB", S.appKb / 1024.0, S.appMaxKb / 1024.0);
  else snprintf(b, sizeof b, "firmware %s", S.fw.c_str());
  rows[1] = b;
  if (S.nvsTotal) snprintf(b, sizeof b, R ? "%d mementouri · NVS %u/%u" : "%d reminders · NVS %u/%u", (int)rems_.size(), (unsigned)S.nvsUsed, (unsigned)S.nvsTotal);
  else snprintf(b, sizeof b, R ? "%d mementouri" : "%d reminders", (int)rems_.size());
  rows[2] = b;
  if (S.heapKb) snprintf(b, sizeof b, "RAM %u KB · PSRAM %.1f MB", (unsigned)S.heapKb, S.psramKb / 1024.0);
  else snprintf(b, sizeof b, "SoulOS %s", S.fw.c_str());
  rows[3] = b;
  rows[4] = "SoulOS " + S.fw + (S.board.empty() ? std::string() : " \xC2\xB7 " + S.board);
  // (S: 34 px a line, as wide as the circle allows at each line)
  for (int i = 0; i < 5; ++i)
    textAt(cv, fonts::caption(), 233, L(254, 236) + i * L(26, 34),
           fit(fonts::caption(), rows[i], g_.s(sGlass() ? (i == 0 || i == 4 ? 290 : 320) : (i == 0 || i == 4 ? 256 : 286))), kCream, i ? kDim : 1.0f);
}

// ------------------------------------------------------- settings › apps ---

void Os::drawAppsSettings(Canvas& cv) {
  const bool R = ro();
  char b[48];
  snprintf(b, sizeof b, R ? "Aplicații · %d" : "Apps · %d", visibleApps());
  rimTop(cv, b, kCream);
  drawWheel(cv);
}

// ------------------------------------------------------------- the wheels ---

bool Os::buildAppsWheel(std::vector<WheelRow>& out) const {
  const bool R = ro();
  const AppsState& A = apps_;
  auto row = [&](int id, const std::string& title) -> WheelRow& {
    WheelRow r;
    r.id = id;
    r.title = title;
    r.valueC = pal_.e1;
    out.push_back(r);
    return out.back();
  };
  switch (view_) {
    case View::Games: {
      static const char* const en[3][2] = {{"Tilt ball", "tilt SOUL, catch the stars"}, {"Rhythm", "tap when a ring hits the rim"}, {"Eye memory", "follow where the eyes look"}};
      static const char* const ro_[3][2] = {{"Bila", "înclină SOUL, prinde stelele"}, {"Ritm", "atinge când inelul ajunge la margine"}, {"Memoria ochilor", "repetă unde se uită ochii"}};
      for (int i = 0; i < 3; ++i) {
        WheelRow& r = row(AGame + i, R ? ro_[i][0] : en[i][0]);
        r.sub = R ? ro_[i][1] : en[i][1];
        r.value = A.best[i] ? std::to_string(A.best[i]) : "\xE2\x80\x93";
        r.valueC = A.best[i] ? kMint : kCream.scaled(0.6f);
      }
      return true;
    }
    case View::Calendar: {
      const uint32_t today = now_ / 86400;
      for (int i = 0; i < (int)A.agenda.events.size(); ++i) {
        const apps::Event& e = A.agenda.events[(size_t)i];
        WheelRow& r = row(ARow + i, e.title);
        r.tag = e.allDay ? (R ? "toată ziua" : "all day") : hm(e.start);
        const uint32_t d = e.start / 86400;
        r.sub = (d == today ? std::string() : std::string(dayName(e.start, R)) + (e.place.empty() ? "" : " \xC2\xB7 ")) + e.place;
        if (!e.allDay && e.start > now_ && e.start - now_ < 3600) r.valueC = kAmber, r.value = R ? "curând" : "soon";
      }
      return true;
    }
    case View::Habits: {
      const uint32_t today = now_ / 86400;
      for (int i = 0; i < (int)A.habits.size(); ++i) {
        const apps::Habit& h = A.habits[(size_t)i];
        WheelRow& r = row(ARow + i, h.name);
        r.kind = RowCheck;
        r.on = h.doneOn(today);
        for (int k = 0; k < 7; ++k)
          if (h.doneOn(today - (6 - k))) r.dots |= (uint8_t)(1 << (6 - k));
        if (!r.dots) r.dots = 0x80;  // (a row of empty dots: bit 7 is not drawn)
        const int st = h.streak(today);
        if (st > 0) {
          char b[24];
          snprintf(b, sizeof b, R ? "%d zile" : "%d day%s", st, (!R && st > 1) ? "s" : "");
          r.value = b;
          r.valueC = st >= 3 ? kMint : kCream.scaled(0.75f);
        }
      }
      WheelRow& n = row(ANew, R ? "+ Nou" : "+ New");
      n.kind = RowNew;
      return true;
    }
    case View::WorldClock: {
      apps::PosixTz here;
      here.parse(A.tz.c_str());
      int64_t utc = (int64_t)now_ - here.stdOff;
      utc = (int64_t)now_ - here.offsetAt(utc);
      const int myOff = here.offsetAt(utc);
      for (int i = 0; i < (int)A.clocks.size(); ++i) {
        const apps::City& c = apps::cities()[A.clocks[(size_t)i]];
        apps::PosixTz tz;
        tz.parse(c.tz);
        const int off = tz.offsetAt(utc);
        const int64_t local = utc + off;
        const int dayDiff = (int)(local / 86400 - ((int64_t)now_) / 86400);
        WheelRow& r = row(ARow + i, R ? c.nameRo : c.name);
        char b[48];
        const int dh = (off - myOff) / 60;
        snprintf(b, sizeof b, "%s%d%s h%s", dh >= 0 ? "+" : "-", abs(dh) / 60, abs(dh) % 60 ? ":30" : "",
                 dayDiff > 0 ? (R ? " · mâine" : " · tomorrow") : dayDiff < 0 ? (R ? " · ieri" : " · yesterday") : "");
        r.sub = b;
        const int lh = (int)(((local % 86400) + 86400) % 86400 / 3600);
        r.value = hm((uint32_t)(((local % 86400) + 86400) % 86400));
        r.bigTag = true;
        r.valueC = lh >= 7 && lh < 21 ? kCream : kIce;
      }
      if (A.clocks.size() < 4) {
        WheelRow& n = row(ANew, R ? "+ Oraș" : "+ City");
        n.kind = RowNew;
      }
      return true;
    }
    case View::AppsSettings: {
      for (int i = 0; i < (int)A.order.size(); ++i) {
        const AppId a = (AppId)A.order[(size_t)i];
        WheelRow& r = row(ARow + i, appName(a));
        r.kind = RowToggle;
        r.on = !(A.hidden >> (int)a & 1u);
        r.dim = r.on ? 1.0f : 0.6f;
        if (i > 0) r.id2 = AUp + i;
        else r.glyph = (int)a;
      }
      return true;
    }
    default: return false;
  }
}

}  // namespace suflet
