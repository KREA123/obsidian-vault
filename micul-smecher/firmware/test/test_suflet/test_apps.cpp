// SoulOS apps (os/APPS.md, docs/11-MAPS.md): the map bundle, projection, routes and walking them with no GPS
// and no compass; weather / agenda / rates as SOUL Cloud sends them (fixtures made by ai/tools/gen_app_fixtures.py
// from the real cloud code); time zones, the converter, habits, pomodoro, breathing, the stopwatch; the games'
// physics and rules; focus sounds; and the app screens driven through Os like a finger would.
#include <unity.h>

#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "../../sim/app_fixtures.h"
#include "AppKit.h"
#include "CloudLink.h"
#include "Frame.h"
#include "Games.h"
#include "Gestures.h"
#include "MapCore.h"
#include "Os.h"
#include "SoundGen.h"

using namespace suflet;

// Unity is built without double support here: compare doubles by hand
#define DWITHIN(d, e, a) TEST_ASSERT_TRUE_MESSAGE(std::fabs((double)(e) - (double)(a)) <= (double)(d), #a)

namespace {

const uint32_t kNow = 1790359080u;  // Fri 2026-09-26 18:38 local (Bucharest)

struct Dev {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  Os os{&alarms};
  TouchGestures tg;
  DisplayGeometry g = displays::kLcd28;
  std::vector<uint16_t> fb = std::vector<uint16_t>(480 * 480);
  Canvas cv{480, 480, fb.data()};
  FrameComposer comp{&cv};
  bool finger = false;
  float fx = 0, fy = 0;
  uint32_t clock = kNow;
  float frac = 0;
  Inputs in;
  bool render = true;
  std::vector<AppFetch> fetched;

  explicit Dev(bool paired = true) {
    os.settings().booted = 1;
    os.settings().ai = (uint8_t)AiMode::Cloud;
    BirthInfo b;
    b.design = 5;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = 1234;
    os.begin(g, b);
    NetInfo n;
    n.configured = n.connected = true;
    n.relay = true;
    n.paired = paired;
    n.cloudOnline = true;
    n.cloudHost = "soul.example";
    n.ssid = "home";
    os.setNet(n);
    tg.setMode(TouchMode::Text);
    os.setClock(clock);
    in.hour = 18.6f;
  }
  void step(float dt = 1.0f / 30) {
    frac += dt;
    while (frac >= 1) {
      frac -= 1;
      ++clock;
    }
    os.setClock(clock);
    tg.update(finger, fx, fy, dt);
    TouchEv e;
    while (tg.poll(e)) os.touch(e);
    os.update(dt, brain);
    brain.update(dt, in);
    OsCmd c;
    while (os.popCmd(c))
      if (c == OsCmd::AppFetch) {
        AppFetch f;
        while (os.popAppFetch(f)) fetched.push_back(f);
      }
    if (render) comp.compose(os);
  }
  void run(float s) {
    for (int i = 0; i < (int)(s * 30 + 0.5f); ++i) step();
  }
  void tap(float x, float y) {
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(0.08f);
    finger = false;
    run(0.5f);
  }
  void swipe(float x0, float y0, float x1, float y1) {
    finger = true;
    for (int i = 0; i <= 6; ++i) {
      fx = g.s(x0 + (x1 - x0) * i / 6);
      fy = g.s(y0 + (y1 - y0) * i / 6);
      step();
    }
    finger = false;
    run(0.5f);
  }
  bool asked(Fetch k) const {
    for (const AppFetch& f : fetched)
      if (f.kind == k) return true;
    return false;
  }
  const AppFetch* last(Fetch k) const {
    for (int i = (int)fetched.size() - 1; i >= 0; --i)
      if (fetched[i].kind == k) return &fetched[i];
    return nullptr;
  }
};

std::string bin(const unsigned char* b, size_t n) { return std::string((const char*)b, n); }

}  // namespace

// ======================================================================= maps ==

static void test_maps_projection_matches_the_cloud() {
  double x, y;
  maps::worldPx(44.4355, 26.1025, 16, x, y);
  // the same numbers as ai/suflet_ai/maps.world_px (Web Mercator, 256 px tiles)
  DWITHIN(0.001, 9605072.6684, x);
  DWITHIN(0.001, 6072207.7319, y);
  double la, lo;
  maps::latLon(x, y, 16, la, lo);
  DWITHIN(1e-9, 44.4355, la);
  DWITHIN(1e-9, 26.1025, lo);
  DWITHIN(5, 967, maps::haversine(44.4355, 26.1025, 44.4268, 26.1025));
  DWITHIN(0.5, 90, maps::bearing(44, 26, 44, 27));
  DWITHIN(0.05, 1.71, maps::metresPerPx(44.4355, 16));
  std::vector<double> pts;
  TEST_ASSERT_TRUE(maps::decodePolyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@", pts));
  TEST_ASSERT_EQUAL_INT(6, (int)pts.size());
  DWITHIN(1e-6, 38.5, pts[0]);
  DWITHIN(1e-6, -126.453, pts[5]);
  TEST_ASSERT_FALSE(maps::decodePolyline("_p~iF~ps|U_", pts));
}

static void test_maps_bundle_decodes_the_clouds_smb1_and_rejects_garbage() {
  maps::MapBundle b;
  TEST_ASSERT_TRUE(b.decode(kFixBundle16, sizeof kFixBundle16));
  TEST_ASSERT_EQUAL_INT(16, b.z);
  TEST_ASSERT_EQUAL_INT(960, b.w);
  int water = 0, roads = 0, places = 0;
  for (const maps::Feature& f : b.feats) {
    water += f.cls == maps::Water;
    roads += f.cls == maps::RoadMajor || f.cls == maps::RoadMinor;
    if (f.kind == maps::Point) {
      ++places;
      TEST_ASSERT_TRUE(f.labelLen > 0);
    }
  }
  TEST_ASSERT_TRUE(water >= 1 && roads >= 10 && places >= 1);
  double x, y;
  maps::worldPx(kFixLat, kFixLon, 16, x, y);
  TEST_ASSERT_TRUE(b.covers(16, x - 240, y - 240, x + 240, y + 240));
  TEST_ASSERT_FALSE(b.covers(16, x + 2000, y, x + 2400, y + 10));
  TEST_ASSERT_TRUE(b.covers(15, x / 2 - 100, y / 2 - 100, x / 2 + 100, y / 2 + 100));  // a zoom out still inside
  // truncated anywhere, a wrong magic, absurd sizes: refused, never a crash
  for (size_t n : {(size_t)0, (size_t)19, (size_t)25, sizeof kFixBundle16 / 2, sizeof kFixBundle16 - 1})
    TEST_ASSERT_FALSE(b.decode(kFixBundle16, n));
  std::vector<uint8_t> bad(kFixBundle16, kFixBundle16 + sizeof kFixBundle16);
  bad[0] = 'X';
  TEST_ASSERT_FALSE(b.decode(bad.data(), bad.size()));
  TEST_ASSERT_TRUE(b.empty());
}

static void test_maps_view_pans_and_zooms_on_the_rim() {
  maps::MapView v;
  v.z = 16;
  v.centerOn(kFixLat, kFixLon);
  const double cx = v.cx;
  v.pan(100, 0);  // the map follows the finger: the centre moves west
  DWITHIN(1e-6, cx - 100, v.cx);
  float sx, sy;
  v.toScreen(v.cx, v.cy, sx, sy);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 240, sx);
  const double lat = v.lat();
  v.zoomBy(1.5f);
  TEST_ASSERT_EQUAL_INT(16, v.z);
  v.zoomBy(1.5f);  // 2.25: one whole level carried over
  TEST_ASSERT_EQUAL_INT(17, v.z);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 1.125f, v.scale);
  DWITHIN(1e-7, lat, v.lat());  // zooming keeps the centre
  for (int i = 0; i < 20; ++i) v.zoomBy(2);
  TEST_ASSERT_EQUAL_INT(maps::kMaxZ, v.z);
  TEST_ASSERT_TRUE(v.scale <= 2.0f);
  for (int i = 0; i < 40; ++i) v.zoomBy(0.5f);
  TEST_ASSERT_EQUAL_INT(maps::kMinZ, v.z);
}

static void test_maps_route_parses_and_turns_are_relative_to_the_line() {
  maps::RouteData r;
  TEST_ASSERT_TRUE(r.parse(kFixRoute, strlen(kFixRoute)));
  TEST_ASSERT_EQUAL_STRING("Ateneul Român", r.to.c_str());
  TEST_ASSERT_EQUAL_INT(4, (int)r.steps.size());
  TEST_ASSERT_EQUAL_INT((int)maps::Turn::Right, (int)r.steps[1].turn);
  TEST_ASSERT_EQUAL_INT((int)maps::Turn::Arrive, (int)r.steps.back().turn);
  DWITHIN(30, r.distM, r.cum.back());
  // north, then east: a right turn of about 90 degrees; then north again: a left one
  TEST_ASSERT_FLOAT_WITHIN(20, 90, r.turnAngle(1));
  TEST_ASSERT_FLOAT_WITHIN(20, -90, r.turnAngle(2));
  TEST_ASSERT_EQUAL_FLOAT(0, r.turnAngle(3));
  TEST_ASSERT_FALSE(r.parse("{\"shape\":\"\",\"steps\":[]}", 26));
  TEST_ASSERT_FALSE(r.parse("nope", 4));
}

static void test_maps_walking_a_route_with_coarse_fixes() {
  maps::RouteData r;
  TEST_ASSERT_TRUE(r.parse(kFixRoute, strlen(kFixRoute)));
  maps::NavState n;
  n.start(&r, kNow);
  TEST_ASSERT_EQUAL_INT(1, n.step());
  TEST_ASSERT_FLOAT_WITHIN(5, (float)r.cum[r.steps[1].idx], n.toTurnM());
  const int walkEta = n.etaS();
  TEST_ASSERT_INT_WITHIN(5, (int)(r.cum.back() / 1.35), walkEta);
  auto at = [&](int idx, double t = 0, double dLat = 0, float acc = 15) {  // between shape points idx and idx + 1
    const int j = idx + 1 < r.points() ? idx + 1 : idx;
    maps::NavFix f;
    f.lat = r.shape[2 * idx] + (r.shape[2 * j] - r.shape[2 * idx]) * t + dLat;
    f.lon = r.shape[2 * idx + 1] + (r.shape[2 * j + 1] - r.shape[2 * idx + 1]) * t;
    f.accM = acc;
    n.fix(f);
  };
  at(r.steps[1].idx, 0.5);  // past the first turn
  TEST_ASSERT_EQUAL_INT(2, n.step());
  TEST_ASSERT_FALSE(n.offRoute());
  at(0, 0.1);  // a stale fix from far back: never more than one step backwards
  TEST_ASSERT_TRUE(n.step() >= 1 && n.alongM() >= (float)r.cum[r.steps[0].idx]);
  at(r.steps[2].idx, 0.5);
  TEST_ASSERT_EQUAL_INT(3, n.step());
  at(r.steps[2].idx, 0.5, 0.003);  // 330 m north of the line: off the route
  TEST_ASSERT_TRUE(n.offRoute());
  const int keep = n.step();
  TEST_ASSERT_EQUAL_INT(keep, n.step());
  at(r.points() - 1);
  TEST_ASSERT_TRUE(n.arrived());
  TEST_ASSERT_EQUAL_INT(0, (int)n.leftM());
  // by hand ("I'm at the turn"), without any fix
  maps::NavState h;
  h.start(&r, kNow);
  h.next();
  TEST_ASSERT_EQUAL_INT(2, h.step());
  h.prev();
  TEST_ASSERT_EQUAL_INT(1, h.step());
  for (int i = 0; i < 10; ++i) h.next();
  TEST_ASSERT_TRUE(h.arrived());
}

static void test_maps_painter_draws_water_roads_and_labels_inside_the_clip() {
  maps::MapBundle b;
  TEST_ASSERT_TRUE(b.decode(kFixBundle15, sizeof kFixBundle15));
  maps::MapView v;
  v.z = 15;
  v.centerOn(kFixLat, kFixLon);
  std::vector<uint16_t> px(480 * 480, 0xFFFF);
  Canvas cv(480, 480, px.data());
  maps::MapPainter p;
  p.paint(cv, b, v, &fonts::small());
  int land = 0, water = 0, bright = 0;
  for (uint16_t c : px) {
    const Rgb q = Rgb::from565(c);
    land += c == p.style.land.to565();
    water += q.b > q.r + 30 && q.b > 60;
    bright += q.r > 180 && q.g > 160;
  }
  TEST_ASSERT_TRUE(land > 60000);
  TEST_ASSERT_TRUE(water > 2000);
  TEST_ASSERT_TRUE(bright > 400);  // roads and labels
  TEST_ASSERT_TRUE(p.segments > 20);
  // a clipped repaint touches nothing outside the clip
  std::vector<uint16_t> q(480 * 480, 0x1234);
  Canvas c2(480, 480, q.data());
  c2.setClip(Rect{100, 100, 200, 160});
  p.paint(c2, b, v, &fonts::small());
  for (int y = 0; y < 480; ++y)
    for (int x = 0; x < 480; ++x)
      if (x < 100 || x >= 200 || y < 100 || y >= 160) TEST_ASSERT_EQUAL_HEX16(0x1234, q[y * 480 + x]);
}

// ===================================================================== app kit ==

static void test_appkit_weather_agenda_and_rates_from_the_cloud() {
  apps::Weather w;
  TEST_ASSERT_TRUE(w.parse(kFixWeather, strlen(kFixWeather), kNow));
  TEST_ASSERT_EQUAL_INT(21, w.t);
  TEST_ASSERT_EQUAL_INT((int)apps::Sky::Part, (int)w.sky);
  TEST_ASSERT_EQUAL_INT(6, (int)w.hours.size());
  TEST_ASSERT_EQUAL_INT(3, (int)w.days.size());
  TEST_ASSERT_EQUAL_STRING("București", w.place.c_str());
  TEST_ASSERT_FALSE(w.parse("{\"t\":\"x\"}", 9, kNow));
  apps::Agenda a;
  TEST_ASSERT_TRUE(a.parse(kFixAgenda, strlen(kFixAgenda), kNow));
  TEST_ASSERT_TRUE(a.events.size() >= 3);
  TEST_ASSERT_EQUAL_STRING("Coffee with Ana", a.events[0].title.c_str());
  TEST_ASSERT_EQUAL_UINT32(apps::parseLocal("2026-09-26T19:30"), a.events[0].start);
  TEST_ASSERT_EQUAL_INT(0, a.next(kNow));
  TEST_ASSERT_EQUAL_INT(1, a.next(apps::parseLocal("2026-09-26T20:31")));
  bool allDay = false;
  for (const apps::Event& e : a.events) allDay |= e.allDay;
  TEST_ASSERT_TRUE(allDay);
  apps::Rates r;
  TEST_ASSERT_FALSE(r.fromCloud);
  TEST_ASSERT_TRUE(r.rate("RON") > 4);
  TEST_ASSERT_TRUE(r.parse(kFixRates, strlen(kFixRates)));
  TEST_ASSERT_TRUE(r.fromCloud);
  TEST_ASSERT_EQUAL_STRING("2026-09-25", r.date.c_str());
  DWITHIN(1e-5, 4.9746, r.rate("RON"));
  DWITHIN(0, 0, r.rate("XXX"));
  TEST_ASSERT_FALSE(r.parse("{\"base\":\"USD\",\"rates\":{\"EUR\":1}}", 33));
}

static void test_appkit_posix_time_zones_both_hemispheres() {
  apps::PosixTz b, ny, syd, mum, dub;
  TEST_ASSERT_TRUE(b.parse("EET-2EEST,M3.5.0/3,M10.5.0/4"));
  TEST_ASSERT_TRUE(ny.parse("EST5EDT,M3.2.0,M11.1.0"));
  TEST_ASSERT_TRUE(syd.parse("AEST-10AEDT,M10.1.0,M4.1.0/3"));
  TEST_ASSERT_TRUE(mum.parse("IST-5:30"));
  TEST_ASSERT_TRUE(dub.parse("<+04>-4"));
  TEST_ASSERT_FALSE(b.parse("garbage"));
  b.parse("EET-2EEST,M3.5.0/3,M10.5.0/4");
  // Bucharest: summer time from 2026-03-29 01:00 UTC to 2026-10-25 01:00 UTC
  const int64_t mar29 = 1774746000, oct25 = 1792890000;  // 01:00 UTC on those days
  TEST_ASSERT_EQUAL_INT(2 * 3600, b.offsetAt(mar29 - 1));
  TEST_ASSERT_EQUAL_INT(3 * 3600, b.offsetAt(mar29));
  TEST_ASSERT_EQUAL_INT(3 * 3600, b.offsetAt(oct25 - 1));
  TEST_ASSERT_EQUAL_INT(2 * 3600, b.offsetAt(oct25));
  // New York: 2026-03-08 07:00 UTC .. 2026-11-01 06:00 UTC
  TEST_ASSERT_EQUAL_INT(-5 * 3600, ny.offsetAt(1772953200 - 1));
  TEST_ASSERT_EQUAL_INT(-4 * 3600, ny.offsetAt(1772953200));
  TEST_ASSERT_EQUAL_INT(-5 * 3600, ny.offsetAt(1793512800));
  // Sydney: summer across New Year
  TEST_ASSERT_EQUAL_INT(11 * 3600, syd.offsetAt(1767225600));  // 2026-01-01
  TEST_ASSERT_EQUAL_INT(10 * 3600, syd.offsetAt(1782864000));  // 2026-07-01
  TEST_ASSERT_EQUAL_INT(5 * 3600 + 1800, mum.offsetAt(1782864000));
  TEST_ASSERT_EQUAL_INT(4 * 3600, dub.offsetAt(1782864000));
  for (const apps::City& c : apps::cities()) {
    apps::PosixTz z;
    TEST_ASSERT_TRUE_MESSAGE(z.parse(c.tz), c.name);
  }
}

static void test_appkit_converter_habits_pomodoro_breath_stopwatch() {
  apps::Rates r;
  r.parse(kFixRates, strlen(kFixRates));
  using apps::Quantity;
  DWITHIN(1e-9, 1.609344, apps::convert(Quantity::Length, 4, 1, 1, r));   // mi -> km
  DWITHIN(1e-9, 212, apps::convert(Quantity::Temperature, 0, 1, 100, r));  // C -> F
  DWITHIN(1e-9, -40, apps::convert(Quantity::Temperature, 1, 0, -40, r));
  DWITHIN(1e-9, 273.15, apps::convert(Quantity::Temperature, 0, 2, 0, r));
  DWITHIN(1e-4, 4.9746 / 1.0912 * 10, apps::convert(Quantity::Currency, 2, 1, 10, r));  // 10 USD -> RON
  TEST_ASSERT_TRUE(std::isnan(apps::convert(Quantity::Length, 0, 99, 1, r)));
  TEST_ASSERT_EQUAL_STRING("1.61", apps::formatNumber(1.609344).c_str());
  TEST_ASSERT_EQUAL_STRING("12 345", apps::formatNumber(12345.4).c_str());
  TEST_ASSERT_EQUAL_STRING("0.0001", apps::formatNumber(0.0001).c_str());
  TEST_ASSERT_EQUAL_STRING("-3.5", apps::formatNumber(-3.5).c_str());
  // habits: a streak across days, today still open
  apps::Habit h;
  const uint32_t d0 = 20000;
  for (uint32_t d = d0; d < d0 + 5; ++d) h.toggle(d);
  TEST_ASSERT_EQUAL_INT(5, h.streak(d0 + 4));
  TEST_ASSERT_EQUAL_INT(5, h.streak(d0 + 5));  // not done yet today: yesterday's streak stands
  TEST_ASSERT_EQUAL_INT(0, h.streak(d0 + 7));
  TEST_ASSERT_TRUE(h.doneOn(d0 + 2));
  TEST_ASSERT_FALSE(h.doneOn(d0 + 5));
  h.toggle(d0 + 4);
  TEST_ASSERT_FALSE(h.doneOn(d0 + 4));
  TEST_ASSERT_EQUAL_INT(4, h.lastWeek(d0 + 4));
  // pomodoro: 4 x (25 + 5) then a long break
  apps::Pomodoro p;
  p.start();
  int focus = 0, longBreaks = 0;
  for (int i = 0; i < 4 * 30 * 60 + 15 * 60 + 10; ++i)
    if (p.tick(1.0f)) {
      if (p.ended() == apps::Pomodoro::Phase::Focus) ++focus;
      if (p.phase() == apps::Pomodoro::Phase::Long) ++longBreaks;
    }
  TEST_ASSERT_EQUAL_INT(4, focus);
  TEST_ASSERT_EQUAL_INT(1, longBreaks);
  TEST_ASSERT_EQUAL_INT((int)apps::Pomodoro::Phase::Focus, (int)p.phase());
  TEST_ASSERT_EQUAL_INT(1, p.round());
  // breath: box 4-4-4-4
  const apps::BreathPattern& box = apps::breathPatterns()[1];
  TEST_ASSERT_EQUAL_INT(0, apps::breathAt(box, 1).phase);
  TEST_ASSERT_EQUAL_FLOAT(1, apps::breathAt(box, 5).size);
  TEST_ASSERT_EQUAL_INT(2, apps::breathAt(box, 9).phase);
  TEST_ASSERT_EQUAL_FLOAT(0, apps::breathAt(box, 13).size);
  TEST_ASSERT_EQUAL_INT(1, apps::breathAt(box, 17).cycle);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, apps::breathAt(box, 2).size);
  // stopwatch and the prefs blob
  TEST_ASSERT_EQUAL_STRING("01:02.3", apps::Stopwatch::format(62.34).c_str());
  TEST_ASSERT_EQUAL_STRING("1:00:05", apps::Stopwatch::format(3605).c_str());
  std::string kv;
  apps::kvSet(kv, "a", "1");
  apps::kvSet(kv, "b", "two\nlines");
  apps::kvSet(kv, "a", "3");
  TEST_ASSERT_EQUAL_STRING("3", apps::kvGet(kv, "a").c_str());
  TEST_ASSERT_EQUAL_STRING("two lines", apps::kvGet(kv, "b").c_str());
  TEST_ASSERT_EQUAL_STRING("d", apps::kvGet(kv, "c", "d").c_str());
}

// ======================================================================= games ==

static void test_games_tilt_ball_rolls_bounces_and_scores() {
  games::TiltBall t;
  t.start(42);
  for (int i = 0; i < 15; ++i) t.step(1.0f / 30, 0.5f, 0);  // tilted right: it rolls right
  TEST_ASSERT_TRUE(t.x() > 40 && t.vx() > 0);
  float maxR = 0;
  for (int i = 0; i < 300; ++i) {
    t.step(1.0f / 30, 0.9f, 0.4f);
    maxR = fmaxf(maxR, hypotf(t.x(), t.y()));
  }
  TEST_ASSERT_TRUE(maxR <= games::TiltBall::kArena - games::TiltBall::kBall + 0.01f);  // the rim holds it
  // energy is lost at the rim: flung outward with no tilt, it comes back slower
  games::TiltBall b;
  b.start(7);
  for (int i = 0; i < 4; ++i) b.step(1.0f / 30, 3.0f, 0);
  float before = 0, after = 0;
  for (int i = 0; i < 60; ++i) {
    const float s = b.speed();
    const uint8_t ev = b.step(1.0f / 30, 0, 0);
    if (ev & games::TiltBall::Bump) {
      before = s;
      after = b.speed();
      break;
    }
  }
  TEST_ASSERT_TRUE(before > 0 && after < before);
  // rolling onto the star scores; time runs out
  games::TiltBall s;
  s.start(3);
  int got = 0;
  for (int i = 0; i < 45 * 30 + 10; ++i) {
    const float dx = s.star().x - s.x(), dy = s.star().y - s.y(), d = hypotf(dx, dy) + 1e-3f;
    const uint8_t ev = s.step(1.0f / 30, dx / d * 0.6f - s.vx() * 0.004f, dy / d * 0.6f - s.vy() * 0.004f);
    if (ev & games::TiltBall::Got) ++got;
  }
  TEST_ASSERT_TRUE(got >= 3);
  TEST_ASSERT_TRUE(s.over());
  TEST_ASSERT_EQUAL_INT(got, s.score());
}

static void test_games_rhythm_judges_taps_and_counts_misses() {
  games::Rhythm r;
  r.start(5, 100);
  float fr[8];
  int hits = 0, guard = 0;
  while (r.running() && guard++ < 3000) {
    r.step(1.0f / 120);
    const int n = r.visible(fr, 8);
    for (int i = 0; i < n; ++i)
      if (fr[i] >= 0.999f && fr[i] < 1.0f + 1.0f / 120 / games::Rhythm::kTravel && hits < 10) {
        if (r.tap() == games::Rhythm::Perfect) ++hits;
        break;
      }
  }
  TEST_ASSERT_TRUE(r.over());
  TEST_ASSERT_EQUAL_INT(10, r.perfects());
  TEST_ASSERT_EQUAL_INT(games::Rhythm::kBeats - 10, r.misses());
  TEST_ASSERT_TRUE(r.best() >= 10);
  games::Rhythm s;
  s.start(5);
  TEST_ASSERT_EQUAL_INT(games::Rhythm::NoBeat, s.tap());  // nothing near: a stray tap costs nothing
  TEST_ASSERT_EQUAL_INT(0, s.misses());
}

static void test_games_eye_memory_grows_and_ends_on_a_mistake() {
  games::EyeMemory m;
  m.start(9);
  TEST_ASSERT_EQUAL_INT(1, m.round());
  for (int round = 1; round <= 4; ++round) {
    std::vector<int> seen;
    int lastCue = -1;
    while (m.phase() == games::EyeMemory::Phase::Show) {
      m.step(0.02f);
      const int c = m.cue();
      if (c >= 0 && c != lastCue) seen.push_back(c);
      lastCue = c;
    }
    TEST_ASSERT_EQUAL_INT(round, (int)m.sequence().size());
    for (int k : m.sequence()) TEST_ASSERT_TRUE(m.input(k));
  }
  TEST_ASSERT_EQUAL_INT(4, m.score());
  while (m.phase() == games::EyeMemory::Phase::Show) m.step(0.05f);
  TEST_ASSERT_FALSE(m.input((m.sequence()[0] + 1) % 4));
  TEST_ASSERT_EQUAL_INT((int)games::EyeMemory::Phase::Over, (int)m.phase());
  TEST_ASSERT_EQUAL_INT(0, games::EyeMemory::spotAt(0, -50));
  TEST_ASSERT_EQUAL_INT(1, games::EyeMemory::spotAt(60, 10));
  TEST_ASSERT_EQUAL_INT(2, games::EyeMemory::spotAt(-5, 70));
  TEST_ASSERT_EQUAL_INT(3, games::EyeMemory::spotAt(-80, 30));
}

static void test_focus_sounds_are_bounded_deterministic_and_distinct() {
  SoundGen a, b;
  a.reset(1);
  b.reset(1);
  std::vector<int16_t> x(16000), y(16000);
  double energy[SoundGen::Count] = {};
  for (int k = 0; k < SoundGen::Count; ++k) {
    a.set((SoundGen::Kind)k, 0.8f);
    a.reset(1);
    a.fill(x.data(), (int)x.size());
    for (int16_t v : x) energy[k] += (double)v * v;
    TEST_ASSERT_TRUE(energy[k] > 0);
  }
  a.set(SoundGen::Rain, 0.8f);
  b.set(SoundGen::Rain, 0.8f);
  a.reset(9);
  b.reset(9);
  a.fill(x.data(), 4000);
  b.fill(y.data(), 4000);
  TEST_ASSERT_EQUAL_MEMORY(x.data(), y.data(), 8000);
  SoundGen q;
  q.set(SoundGen::Brown, 0);
  q.fill(x.data(), 4000);
  for (int i = 0; i < 4000; ++i) TEST_ASSERT_EQUAL_INT16(0, x[i]);
  TEST_ASSERT_TRUE(energy[SoundGen::Brown] != energy[SoundGen::Rain]);
}

// =================================================================== the screens ==

static void test_apps_every_app_opens_draws_and_goes_back_to_the_eyes() {
  Dev d;
  d.run(0.5f);
  TEST_ASSERT_EQUAL_INT((int)AppId::Count, d.os.visibleApps());
  for (int i = 0; i < (int)AppId::Count; ++i) {
    const AppId a = (AppId)i;
    d.os.openApp(a);
    d.run(0.4f);
    d.os.render(d.cv);  // a full redraw of every screen, every state it opens in
    TEST_ASSERT_TRUE_MESSAGE(d.os.view() != View::Home, std::to_string(i).c_str());
    d.os.button(true);
    d.run(0.05f);
    d.os.button(false);
    d.run(0.3f);
    if (d.os.view() != View::Home) d.os.back();  // Settings sub-screens: one level more
    d.run(0.2f);
    TEST_ASSERT_EQUAL_INT_MESSAGE((int)View::Home, (int)d.os.view(), std::to_string(i).c_str());
  }
}

static void test_apps_launcher_order_hide_and_two_gestures() {
  Dev d;
  d.run(0.4f);
  d.swipe(330, 240, 150, 240);  // the orbit
  TEST_ASSERT_EQUAL_INT((int)View::Launcher, (int)d.os.view());
  d.tap(328, 398);  // the right neighbour opens at once: two gestures from the eyes
  TEST_ASSERT_EQUAL_INT((int)View::Today, (int)d.os.view());
  d.os.go(View::Home);
  d.run(0.3f);
  d.swipe(330, 240, 150, 240);
  TEST_ASSERT_EQUAL_INT((int)AppId::Today, (int)d.os.appAt(d.os.launcherIndex()));  // it opens on the last app
  // Settings › Apps: hide Talk, move Maps first; it survives a restart
  d.os.go(View::AppsSettings);
  d.run(0.3f);
  d.tap(262, 150);  // row 0 (Talk): hide
  TEST_ASSERT_EQUAL_INT((int)AppId::Count - 1, d.os.visibleApps());
  d.tap(104, 278);  // row 2 (Maps): up
  d.tap(104, 214);  // row 1 now Maps: up again
  TEST_ASSERT_EQUAL_INT((int)AppId::Maps, (int)d.os.apps().order[0]);
  const std::string blob = d.os.saveApps();
  Dev e;
  e.os.loadApps(blob);
  TEST_ASSERT_EQUAL_INT((int)AppId::Maps, (int)e.os.appAt(0));
  TEST_ASSERT_EQUAL_INT((int)AppId::Count - 1, e.os.visibleApps());
  // Settings can never be hidden
  e.os.go(View::AppsSettings);
  e.run(0.2f);
  e.os.apps().setPage = 5;
  e.run(0.1f);
  e.tap(262, 150);  // the last page's first row is Settings
  TEST_ASSERT_TRUE(!(e.os.apps().hidden >> (int)AppId::Settings & 1u));
}

static void test_apps_control_pulls_down_and_quiet_holds_notes() {
  Dev d;
  d.run(0.4f);
  d.swipe(233, 120, 233, 330);  // pull down from the eyes
  TEST_ASSERT_EQUAL_INT((int)View::Control, (int)d.os.view());
  d.tap(180, 200);  // Quiet
  TEST_ASSERT_TRUE(d.os.quiet());
  d.tap(286, 200);  // Large text
  TEST_ASSERT_EQUAL_INT(1, d.os.settings().largeText);
  // the left rim dial: light
  d.finger = true;
  for (int i = 0; i <= 8; ++i) {
    const float a = (128 + i * 13) * 3.14159265f / 180;  // up the left rim: brighter
    d.fx = d.g.s(233 + 212 * cosf(a));
    d.fy = d.g.s(233 + 212 * sinf(a));
    d.step();
  }
  d.finger = false;
  d.run(0.3f);
  TEST_ASSERT_EQUAL_INT(3, d.os.settings().bright);
  d.swipe(233, 420, 233, 300);  // push it back up
  TEST_ASSERT_EQUAL_INT((int)View::Home, (int)d.os.view());
  d.run(5.0f);
  CloudPush p;
  p.kind = CloudPush::Card;
  p.source = "connector";
  p.title = "Ana";
  p.body = "dinner at 8?";
  std::string err;
  d.os.toast("a quiet note", Rgb::hex(0xFFF0C8), 3);
  TEST_ASSERT_FALSE(d.os.uiOn());  // Quiet: the eyes stay alone
}

static void test_apps_maps_where_view_route_and_walk() {
  Dev d;
  d.run(0.3f);
  d.os.openApp(AppId::Maps);
  d.run(0.3f);
  TEST_ASSERT_TRUE(d.asked(Fetch::Where));
  TEST_ASSERT_EQUAL_STRING("/v1/device/maps/where", d.last(Fetch::Where)->path.c_str());
  d.os.appData(Fetch::Where, 200, "{\"fix\":null}");
  d.run(0.2f);
  d.os.render(d.cv);  // "Where are you?" + the /me/where QR
  char fix[160];
  snprintf(fix, sizeof fix, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":15,\"src\":\"phone\",\"age\":4,\"label\":\"\"}}", kFixLat, kFixLon);
  d.os.appData(Fetch::Where, 200, fix);
  d.run(0.2f);
  TEST_ASSERT_TRUE(d.os.apps().haveFix);
  const AppFetch* v = d.last(Fetch::MapView);
  TEST_ASSERT_NOT_NULL(v);
  TEST_ASSERT_TRUE(v->path.find("/v1/device/maps/view?lat=44.43550&lon=26.10250&z=16") == 0);
  d.os.appData(Fetch::MapView, 200, bin(kFixBundle16, sizeof kFixBundle16));
  d.run(0.2f);
  TEST_ASSERT_FALSE(d.os.apps().bundle.empty());
  d.os.render(d.cv);
  // pan with a finger, zoom on the rim
  const double cx = d.os.apps().view.cx;
  d.swipe(233, 260, 300, 260);
  TEST_ASSERT_TRUE(d.os.apps().view.cx < cx - 30);
  TEST_ASSERT_EQUAL_INT((int)View::Maps, (int)d.os.view());
  const int z = d.os.apps().view.z;
  d.finger = true;
  for (int i = 0; i <= 12; ++i) {  // around the rim, clockwise
    const float a = (-40 + i * 8) * 3.14159265f / 180;
    d.fx = d.g.s(233 + 205 * cosf(a));
    d.fy = d.g.s(233 + 205 * sinf(a));
    d.step();
  }
  d.finger = false;
  d.run(0.3f);
  TEST_ASSERT_TRUE(d.os.apps().view.z > z || d.os.apps().view.scale > 1.5f);
  // "Where to?": the cloud plans, a preview, then Start
  d.os.appData(Fetch::RoutePlan, 200, kFixRoute);
  d.run(0.3f);
  TEST_ASSERT_TRUE(d.os.apps().preview);
  d.os.render(d.cv);
  d.tap(233, 358);  // Start
  TEST_ASSERT_TRUE(d.os.apps().navOn);
  TEST_ASSERT_EQUAL_INT(1, d.os.apps().nav.step());
  d.os.render(d.cv);
  // the phone moves past the first turn: the next step
  const maps::RouteData& r = d.os.apps().route;
  const int idx = r.steps[1].idx;  // half way along the street after the first turn
  snprintf(fix, sizeof fix, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":12,\"src\":\"phone\",\"age\":1}}",
           (r.shape[2 * idx] + r.shape[2 * idx + 2]) / 2, (r.shape[2 * idx + 1] + r.shape[2 * idx + 3]) / 2);
  d.os.appData(Fetch::Where, 200, fix);
  d.run(0.2f);
  TEST_ASSERT_EQUAL_INT(2, d.os.apps().nav.step());
  // "Send to phone": a QR of the Google Maps link, offline-capable
  d.tap(150, 420);
  TEST_ASSERT_TRUE(d.os.apps().sendSheet);
  TEST_ASSERT_TRUE(d.os.apps().sendUrl.find("https://www.google.com/maps/dir/?api=1&destination=") == 0);
  TEST_ASSERT_TRUE(d.asked(Fetch::RouteSend));
  d.os.render(d.cv);
  d.os.back();
  TEST_ASSERT_FALSE(d.os.apps().sendSheet);
  // walking keeps the screen on (no idle return)
  d.run(20.0f);
  TEST_ASSERT_EQUAL_INT((int)View::Maps, (int)d.os.view());
  // offline: the map stays, the rim says so
  d.os.appData(Fetch::MapView, -1, "");
  TEST_ASSERT_FALSE(d.os.apps().bundle.empty());
}

static void test_apps_your_ai_says_take_me_to() {
  Dev d;
  d.run(0.3f);
  CloudPush p;
  TEST_ASSERT_TRUE(CloudLink::mapActionJson("nav.start", "{\"to\":\"Ateneul Român\",\"route\":\"rt00001\",\"mode\":\"walk\"}", p));
  TEST_ASSERT_EQUAL_INT(CloudPush::Nav, p.kind);
  p.source = "connector";
  p.app = "claude";
  std::string err;
  TEST_ASSERT_TRUE(d.os.cloudPush(p, err));
  d.run(0.2f);
  TEST_ASSERT_EQUAL_INT((int)View::Maps, (int)d.os.view());
  TEST_ASSERT_TRUE(d.asked(Fetch::RouteGet));
  d.os.appData(Fetch::RouteGet, 200, kFixRoute);
  d.run(0.2f);
  TEST_ASSERT_TRUE(d.os.apps().preview);
  TEST_ASSERT_FALSE(CloudLink::mapActionJson("nav.start", "{\"route\":\"x\"}", p));  // no destination: refused
}

static void test_apps_weather_calendar_and_their_honest_states() {
  Dev d;
  d.run(0.3f);
  d.os.openApp(AppId::Weather);
  d.run(0.2f);
  TEST_ASSERT_TRUE(d.asked(Fetch::Weather));
  d.os.appData(Fetch::Weather, 409, "{\"error\":{\"code\":\"no_location\"}}");
  d.os.render(d.cv);
  TEST_ASSERT_EQUAL_INT(409, d.os.apps().wxErr);
  d.os.appData(Fetch::Weather, 200, kFixWeather);
  d.os.render(d.cv);
  TEST_ASSERT_TRUE(d.os.apps().weather.ok);
  d.swipe(330, 240, 150, 240);  // the next days
  TEST_ASSERT_EQUAL_INT(1, d.os.apps().wxPage);
  d.os.render(d.cv);
  d.os.openApp(AppId::Calendar);
  d.run(0.2f);
  TEST_ASSERT_TRUE(d.asked(Fetch::Agenda));
  d.os.appData(Fetch::Agenda, 404, "{\"error\":{\"code\":\"no_calendar\"}}");
  d.os.render(d.cv);
  d.os.appData(Fetch::Agenda, 200, kFixAgenda);
  d.os.render(d.cv);
  d.tap(233, 164);  // the first event: its card
  TEST_ASSERT_EQUAL_INT(0, d.os.apps().calSel);
  d.os.render(d.cv);
  // not paired: no requests, a "pair first" card instead of a dead end
  Dev u(false);
  u.run(0.2f);
  u.os.openApp(AppId::Weather);
  u.run(0.2f);
  TEST_ASSERT_FALSE(u.asked(Fetch::Weather));
  u.os.render(u.cv);
}

static void test_apps_focus_breathe_habits_stopwatch_clock_convert_find() {
  Dev d;
  d.run(0.3f);
  d.os.openApp(AppId::Focus);
  d.run(0.2f);
  d.tap(233, 340);
  TEST_ASSERT_EQUAL_INT((int)apps::Pomodoro::Phase::Focus, (int)d.os.apps().pomo.phase());
  d.run(16.0f);
  TEST_ASSERT_EQUAL_INT((int)View::Focus, (int)d.os.view());  // a running focus keeps its screen
  d.os.openApp(AppId::Breathe);
  d.run(0.3f);
  TEST_ASSERT_TRUE(d.os.faceMoment());  // black behind the breathing eyes
  d.tap(233, 233);
  TEST_ASSERT_TRUE(d.os.apps().breathing);
  const float k0 = d.os.faceInputs(d.brain).layout.k;
  d.run(3.5f);
  TEST_ASSERT_TRUE(d.os.faceInputs(d.brain).layout.k > k0 + 0.1f);  // the eyes grow on the in-breath
  d.os.openApp(AppId::Habits);
  d.run(0.3f);
  d.tap(233, 160);
  TEST_ASSERT_TRUE(d.os.apps().habits[0].doneOn(d.clock / 86400));
  d.os.openApp(AppId::Stopwatch);
  d.run(0.2f);
  d.tap(316, 352);
  d.run(2.0f);
  TEST_ASSERT_TRUE(d.os.apps().sw.acc > 1.5);
  d.tap(150, 352);  // lap
  TEST_ASSERT_EQUAL_INT(1, (int)d.os.apps().sw.laps.size());
  d.os.openApp(AppId::WorldClock);
  d.run(0.2f);
  d.os.render(d.cv);
  d.os.openApp(AppId::Convert);
  d.run(0.2f);
  d.tap(233, 110);  // length -> weight
  TEST_ASSERT_EQUAL_INT(1, d.os.apps().q);
  d.os.render(d.cv);
  d.os.openApp(AppId::FindPhone);
  d.run(0.2f);
  d.tap(233, 318);
  TEST_ASSERT_TRUE(d.asked(Fetch::FindPhone));
  d.os.appData(Fetch::FindPhone, 200, "{\"ringing\":true,\"reach\":\"page\"}");
  TEST_ASSERT_EQUAL_INT(2, d.os.apps().findState);
  d.os.render(d.cv);
}

static void test_apps_games_play_on_the_device() {
  Dev d;
  d.run(0.3f);
  d.os.openApp(AppId::Games);
  d.run(0.3f);
  d.tap(233, 246);  // Rhythm
  TEST_ASSERT_EQUAL_INT(1, d.os.apps().game);
  TEST_ASSERT_TRUE(d.os.faceMoment());
  d.run(3.0f);
  d.os.render(d.cv);
  d.swipe(233, 200, 233, 380);  // back to the games
  TEST_ASSERT_EQUAL_INT(-1, d.os.apps().game);
  d.tap(233, 322);  // Eye memory
  TEST_ASSERT_EQUAL_INT(2, d.os.apps().game);
  const games::EyeMemory& m = d.os.apps().memory;
  int guard = 0;
  while (m.phase() == games::EyeMemory::Phase::Show && guard++ < 200) d.step();
  static const float kx[] = {233, 413, 233, 53}, ky[] = {53, 233, 413, 233};
  const int s = m.sequence()[0];
  d.tap(kx[s] + (s == 1 ? -60 : s == 3 ? 60 : 0), ky[s] + (s == 0 ? 60 : s == 2 ? -60 : 0));
  TEST_ASSERT_EQUAL_INT(1, m.score());
  d.tap(kx[(m.sequence()[0] + 2) % 4], ky[(m.sequence()[0] + 2) % 4]);  // wrong spot (after the next show)
  guard = 0;
  while (m.phase() == games::EyeMemory::Phase::Show && guard++ < 200) d.step();
  d.tap(kx[(m.sequence()[0] + 2) % 4], ky[(m.sequence()[0] + 2) % 4]);
  d.run(0.3f);
  TEST_ASSERT_EQUAL_INT((int)games::EyeMemory::Phase::Over, (int)m.phase());
  TEST_ASSERT_EQUAL_INT(1, d.os.apps().best[2]);
  d.os.render(d.cv);
  d.tap(306, 330);  // Games
  TEST_ASSERT_EQUAL_INT(-1, d.os.apps().game);
  d.tap(233, 170);  // Tilt ball
  TEST_ASSERT_EQUAL_INT(0, d.os.apps().game);
  d.run(1.0f);
  d.os.render(d.cv);
}

static void test_apps_quick_replies_on_a_card() {
  Dev d;
  d.run(0.3f);
  CloudPush p;
  p.kind = CloudPush::Card;
  p.source = "connector";
  p.app = "claude";
  p.by = "Ana";
  p.title = "Dinner at 8?";
  p.body = "I'll bring figs";
  std::string err;
  TEST_ASSERT_TRUE(d.os.cloudPush(p, err));
  d.run(0.3f);
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());
  d.os.render(d.cv);
  d.tap(233, 392);  // "On my way"
  CloudOut o;
  bool sent = false;
  while (d.os.popCloudOut(o))
    if (o.kind == CloudOut::Inbox) {
      sent = true;
      TEST_ASSERT_EQUAL_STRING("Re: Dinner at 8? \xE2\x80\x94 On my way", o.text.c_str());
    }
  TEST_ASSERT_TRUE(sent);
  TEST_ASSERT_TRUE(d.os.view() != View::Answer);
}

static void test_apps_today_stack_walks_cards_and_opens_them() {
  Dev d;
  d.run(0.3f);
  d.swipe(233, 380, 233, 150);  // swipe up from the eyes
  TEST_ASSERT_EQUAL_INT((int)View::Today, (int)d.os.view());
  for (int i = 0; i < 6; ++i) {
    d.os.render(d.cv);
    d.swipe(233, 380, 233, 200);
  }
  TEST_ASSERT_EQUAL_INT(5, d.os.apps().card);
  d.swipe(233, 200, 233, 380);
  TEST_ASSERT_EQUAL_INT(4, d.os.apps().card);
  d.tap(233, 240);
  TEST_ASSERT_EQUAL_INT((int)View::Habits, (int)d.os.view());
}

static void test_apps_frame_pipeline_equals_a_full_redraw_on_the_map_and_a_game() {
  for (int which = 0; which < 2; ++which) {
    Dev d;
    d.run(0.3f);
    if (which == 0) {
      d.os.openApp(AppId::Maps);
      char fix[128];
      snprintf(fix, sizeof fix, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":15,\"src\":\"phone\"}}", kFixLat, kFixLon);
      d.os.appData(Fetch::Where, 200, fix);
      d.os.appData(Fetch::MapView, 200, bin(kFixBundle16, sizeof kFixBundle16));
      d.os.appData(Fetch::RoutePlan, 200, kFixRoute);
    } else {
      d.os.openApp(AppId::Games);
      d.run(0.3f);
      d.tap(233, 170);
    }
    d.run(1.5f);
    std::vector<uint16_t> full(480 * 480);
    Canvas fc(480, 480, full.data());
    FrameComposer fcomp(&fc);
    // what the incremental frames left on the glass == one full redraw of the same state
    d.render = false;
    d.comp.compose(d.os);
    fcomp.compose(d.os, true);
    int diff = 0;
    for (int i = 0; i < 480 * 480; ++i) diff += d.fb[i] != full[i];
    TEST_ASSERT_TRUE_MESSAGE(diff < 480 * 480 / 200, which ? "game" : "map");
  }
}

void runAppsTests() {
  RUN_TEST(test_maps_projection_matches_the_cloud);
  RUN_TEST(test_maps_bundle_decodes_the_clouds_smb1_and_rejects_garbage);
  RUN_TEST(test_maps_view_pans_and_zooms_on_the_rim);
  RUN_TEST(test_maps_route_parses_and_turns_are_relative_to_the_line);
  RUN_TEST(test_maps_walking_a_route_with_coarse_fixes);
  RUN_TEST(test_maps_painter_draws_water_roads_and_labels_inside_the_clip);
  RUN_TEST(test_appkit_weather_agenda_and_rates_from_the_cloud);
  RUN_TEST(test_appkit_posix_time_zones_both_hemispheres);
  RUN_TEST(test_appkit_converter_habits_pomodoro_breath_stopwatch);
  RUN_TEST(test_games_tilt_ball_rolls_bounces_and_scores);
  RUN_TEST(test_games_rhythm_judges_taps_and_counts_misses);
  RUN_TEST(test_games_eye_memory_grows_and_ends_on_a_mistake);
  RUN_TEST(test_focus_sounds_are_bounded_deterministic_and_distinct);
  RUN_TEST(test_apps_every_app_opens_draws_and_goes_back_to_the_eyes);
  RUN_TEST(test_apps_launcher_order_hide_and_two_gestures);
  RUN_TEST(test_apps_control_pulls_down_and_quiet_holds_notes);
  RUN_TEST(test_apps_maps_where_view_route_and_walk);
  RUN_TEST(test_apps_your_ai_says_take_me_to);
  RUN_TEST(test_apps_weather_calendar_and_their_honest_states);
  RUN_TEST(test_apps_focus_breathe_habits_stopwatch_clock_convert_find);
  RUN_TEST(test_apps_games_play_on_the_device);
  RUN_TEST(test_apps_quick_replies_on_a_card);
  RUN_TEST(test_apps_today_stack_walks_cards_and_opens_them);
  RUN_TEST(test_apps_frame_pipeline_equals_a_full_redraw_on_the_map_and_a_game);
}
