// SoulOS apps in the simulator (os/APPS.md, docs/11-MAPS.md): the real device stack (Os, the apps, the glass,
// the eyes, the frame composer) with a scripted finger, a tilted IMU, and a fake SOUL Cloud that answers the
// apps' calls with what the real cloud code makes (sim/app_fixtures.h, ai/tools/gen_app_fixtures.py).
//
//   program <out_dir> apps            stills of every app: <out_dir>/NN-name.ppm (+ shots.txt); then
//                                     python3 tools/app_shots.py <out_dir> sim/shots/apps
//   program <out_dir> bench_maps      10 s on the map: panning, zooming, walking a route (frame cost)
//   program <out_dir> bench_games     10 s of tilt ball and rhythm (frame cost)
//   valgrind --tool=callgrind --toggle-collect='suflet::FrameComposer::compose*' program out bench_maps
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "Alarms.h"
#include "Brain.h"
#include "EyeMotion.h"
#include "Frame.h"
#include "Gestures.h"
#include "Os.h"
#include "Personality.h"
#include "app_fixtures.h"

using namespace suflet;

namespace {

struct AppSim {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  Os os{&alarms};
  TouchGestures touch;
  DisplayGeometry g;
  int W, H;
  std::vector<uint16_t> fb;
  Canvas cv;
  FrameComposer comp{&cv};
  bool finger = false;
  float fx = 0, fy = 0;
  uint32_t clock = 1790359080u;  // Fri 2026-09-26 18:38 local
  float frac = 0;
  Inputs in;
  eyes::PoseImu imu;
  float roll = 0, pitch = 0, yaw = 0;
  struct Pending {
    float t;
    Fetch kind;
    std::string path, body;
  };
  std::vector<Pending> pending;
  bool cloudUp = true, haveFix = true, speaker = true;
  double composeMs = 0;
  int composed = 0;
  std::string dir;
  int shot = 0;
  FILE* manifest = nullptr;

  explicit AppSim(const DisplayGeometry& geo, const std::string& out)
      : g(geo), W(geo.w), H(geo.h), fb((size_t)geo.w * geo.h), cv(geo.w, geo.h, fb.data()), dir(out) {
    os.settings().booted = 1;
    os.settings().ai = (uint8_t)AiMode::Cloud;
    snprintf(os.settings().name, sizeof os.settings().name, "Miso");
    os.settings().born = clock - 86400 * 9;
    BirthInfo b;
    const uint8_t mac[6] = {0xC0, 0xFF, 0xEE, 0x12, 0x34, 0x56};
    const eyes::RollResult r = eyes::rollFromMac(mac);
    b.design = r.design;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = eyes::hashStr(eyes::kDesigns[r.design].id) ^ 0x5eed;
    os.begin(g, b);
    NetInfo n;
    n.configured = n.connected = n.linkUp = true;
    n.relay = n.paired = n.cloudOnline = true;
    n.owner = "Ana";
    n.cloudHost = "soul.example";
    n.ssid = "Acasa";
    os.setNet(n);
    PowerInfo pw;
    pw.batPct = 78;
    os.setPower(pw);
    StorageInfo si;
    si.fw = "1.7.0";
    si.board = "lcd28";
    si.appKb = 2404;
    si.appMaxKb = 6400;
    si.flashKb = 16384;
    si.heapKb = 186;
    si.psramKb = 5980;
    si.psramTotalKb = 8192;
    si.nvsUsed = 61;
    si.nvsTotal = 630;
    si.rssi = -54;
    os.setStorage(si);
    os.setAudio(true, false);
    touch.setMode(TouchMode::Text);
    in.hour = 18.6f;
    manifest = fopen((dir + "/shots.txt").c_str(), "wb");
  }
  ~AppSim() {
    if (manifest) fclose(manifest);
  }

  std::string answer(Fetch k, const std::string& path, int& st) {
    st = 200;
    char b[256];
    switch (k) {
      case Fetch::Weather: return kFixWeather;
      case Fetch::Agenda: return kFixAgenda;
      case Fetch::Rates: return kFixRates;
      case Fetch::Where:
      case Fetch::WifiLocate:
        if (!haveFix) return "{\"fix\":null}";
        snprintf(b, sizeof b, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":%d,\"src\":\"%s\",\"age\":6,\"label\":\"\"}}", kFixLat, kFixLon,
                 k == Fetch::WifiLocate ? 60 : 14, k == Fetch::WifiLocate ? "wifi" : "phone");
        return b;
      case Fetch::MapView: {
        const size_t z = path.find("z=");
        const int zz = z == std::string::npos ? 16 : atoi(path.c_str() + z + 2);
        if (zz <= 15) return std::string((const char*)kFixBundle15, sizeof kFixBundle15);
        if (zz >= 17) return std::string((const char*)kFixBundle17, sizeof kFixBundle17);
        return std::string((const char*)kFixBundle16, sizeof kFixBundle16);
      }
      case Fetch::RoutePlan: return kFixRoute;
      case Fetch::RouteGet:  // no route was planned by an AI: 404, as the cloud says
        st = 404;
        return "{\"error\":{\"code\":\"no_route\"}}";
      case Fetch::RouteSend: return "{\"to\":\"Ateneul Român\",\"links\":{}}";
      case Fetch::FindPhone: return "{\"ringing\":true,\"reach\":\"page\"}";
      default: return "{}";
    }
  }

  void step(bool render = true) {
    const float dt = 1.0f / 30;
    frac += dt;
    while (frac >= 1) {
      frac -= 1;
      ++clock;
    }
    os.setClock(clock);
    for (int k = 0; k < 3; ++k) os.imu(dt / 3, imu.sample(roll, pitch, yaw, dt / 3));
    touch.update(finger, fx, fy, dt);
    TouchEv e;
    while (touch.poll(e)) os.touch(e);
    OsCmd c;
    while (os.popCmd(c))
      if (c == OsCmd::AppFetch) {
        AppFetch f;
        while (os.popAppFetch(f)) pending.push_back({0.45f, f.kind, f.path, f.body});
      }
    for (size_t i = 0; i < pending.size();) {
      pending[i].t -= dt;
      if (pending[i].t <= 0) {
        int st;
        const std::string body = cloudUp ? answer(pending[i].kind, pending[i].path, st) : (st = -1, std::string());
        os.appData(pending[i].kind, st, body);
        pending.erase(pending.begin() + (long)i);
      } else {
        ++i;
      }
    }
    in.hour = (clock % 86400) / 3600.0f;
    os.update(dt, brain);
    brain.update(dt, in);
    if (!render) return;
    const auto t0 = std::chrono::high_resolution_clock::now();
    comp.compose(os);
    composeMs += std::chrono::duration<double, std::milli>(std::chrono::high_resolution_clock::now() - t0).count();
    ++composed;
  }
  void run(float s) {
    for (int i = 0; i < (int)(s * 30 + 0.5f); ++i) step();
  }
  void tap(float x, float y, float gap = 0.6f) {
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(0.08f);
    finger = false;
    run(gap);
  }
  void swipe(float x0, float y0, float x1, float y1, float gap = 0.6f) {
    finger = true;
    for (int i = 0; i <= 6; ++i) {
      fx = g.s(x0 + (x1 - x0) * i / 6);
      fy = g.s(y0 + (y1 - y0) * i / 6);
      step();
    }
    finger = false;
    run(gap);
  }
  void snap(const char* name) {
    char fn[512];
    snprintf(fn, sizeof fn, "%s/%02d-%s.ppm", dir.c_str(), ++shot, name);
    FILE* f = fopen(fn, "wb");
    if (!f) return;
    fprintf(f, "P6\n%d %d\n255\n", W, H);
    std::vector<uint8_t> rgb((size_t)W * H * 3);
    for (int i = 0; i < W * H; ++i) {
      const Rgb p = Rgb::from565(fb[i]);
      rgb[i * 3] = p.r;
      rgb[i * 3 + 1] = p.g;
      rgb[i * 3 + 2] = p.b;
    }
    fwrite(rgb.data(), 1, rgb.size(), f);
    fclose(f);
    if (manifest) fprintf(manifest, "%02d-%s %s\n", shot, name, viewName(os.view()));
    printf("  %02d %-22s view %s\n", shot, name, viewName(os.view()));
  }
};

void allApps(AppSim& s) {
  s.run(1.5f);
  s.swipe(233, 120, 233, 330);  // pull down from the eyes
  s.run(0.5f);
  s.snap("control");
  s.swipe(233, 420, 233, 300);
  s.run(1.0f);
  s.swipe(233, 380, 233, 150);  // swipe up: Today
  s.run(1.0f);
  s.snap("today-now");
  s.swipe(233, 380, 233, 200);
  s.run(0.6f);
  s.snap("today-weather");
  s.os.go(View::Home);
  s.run(1.0f);
  s.os.openApp(AppId::Talk);
  s.os.go(View::Home);
  s.run(0.5f);
  s.os.apps().order = {(uint8_t)AppId::Talk, (uint8_t)AppId::Maps, (uint8_t)AppId::Weather};
  for (int i = 0; i < (int)AppId::Count; ++i)
    if (i != (int)AppId::Talk && i != (int)AppId::Maps && i != (int)AppId::Weather) s.os.apps().order.push_back((uint8_t)i);
  s.swipe(330, 240, 150, 240, 0.2f);  // the orbit
  s.swipe(330, 330, 150, 330, 0.8f);  // one step: Maps
  s.snap("launcher-maps");
  // Maps, before SOUL knows where it is
  s.haveFix = false;
  s.tap(233, 336, 1.2f);
  s.snap("maps-where-are-you");
  s.haveFix = true;  // the owner shared the place on /me/where
  s.os.go(View::Home);
  s.run(9.0f);
  s.os.openApp(AppId::Maps);
  s.run(1.6f);
  s.tap(40, 233, 1.2f);  // "-" on the left rim: one level out
  s.snap("maps-here");
  s.os.appData(Fetch::RoutePlan, 200, kFixRoute);
  s.run(1.2f);
  s.snap("maps-route-preview");
  s.tap(233, 358, 0.8f);  // Start
  {
    const maps::RouteData& r = s.os.apps().route;
    const int i = r.steps[1].idx;
    char fix[200];
    snprintf(fix, sizeof fix, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":12,\"src\":\"phone\",\"age\":2}}",
             r.shape[2 * i] * 0.3 + r.shape[2 * i - 2] * 0.7, r.shape[2 * i + 1] * 0.3 + r.shape[2 * i - 1] * 0.7);
    s.os.appData(Fetch::Where, 200, fix);
  }
  s.run(0.8f);
  s.snap("maps-next-turn");
  s.tap(166, 372, 0.8f);  // send to phone
  s.snap("maps-send-to-phone");
  s.os.back();
  s.run(0.3f);
  s.os.apps().navOn = false;
  s.os.go(View::Home);
  s.run(0.5f);
  s.os.openApp(AppId::Weather);
  s.run(1.4f);
  s.snap("weather");
  s.swipe(330, 260, 150, 260, 0.8f);
  s.snap("weather-days");
  s.os.openApp(AppId::Calendar);
  s.run(1.4f);
  s.snap("calendar");
  s.tap(233, 164, 0.7f);
  s.snap("calendar-event");
  s.os.openApp(AppId::Music);
  s.run(0.6f);
  s.tap(233, 300, 0.8f);
  s.snap("music-focus-sounds");
  s.tap(233, 300, 0.3f);
  s.os.openApp(AppId::Games);
  s.run(0.8f);
  s.snap("games");
  s.tap(233, 170, 0.3f);  // tilt ball, the device tipped right and toward you
  s.roll = -0.25f;
  s.pitch = 0.35f;
  s.run(1.4f);
  s.snap("game-tilt-ball");
  s.roll = s.pitch = 0;
  s.swipe(233, 40, 233, 300, 0.3f);
  s.tap(233, 246, 0.2f);  // rhythm
  s.run(2.25f);
  s.snap("game-rhythm");
  s.swipe(233, 40, 233, 300, 0.3f);
  s.tap(233, 322, 0.2f);  // eye memory
  s.run(0.85f);
  s.snap("game-eye-memory");
  {
    const games::EyeMemory& m = s.os.apps().memory;
    int guard = 0;
    while (m.phase() == games::EyeMemory::Phase::Show && guard++ < 300) s.step();
    static const float kx[] = {233, 413, 233, 53}, ky[] = {53, 233, 413, 233};
    const int wrong = (m.sequence()[0] + 2) % 4;
    s.tap(kx[wrong], ky[wrong], 1.2f);
  }
  s.snap("game-over");
  s.os.openApp(AppId::Focus);
  s.run(0.4f);
  s.tap(233, 340, 0.4f);
  s.run(3.0f);
  s.snap("focus-pomodoro");
  s.os.apps().pomo.stop();
  s.os.openApp(AppId::Breathe);
  s.run(0.6f);
  s.snap("breathe");
  s.tap(233, 233, 0.2f);
  s.run(3.6f);
  s.snap("breathe-in");
  s.os.apps().breathing = false;
  s.os.openApp(AppId::Habits);
  s.run(0.5f);
  s.tap(233, 160, 0.5f);
  s.tap(233, 236, 0.8f);
  s.snap("habits");
  s.os.openApp(AppId::Stopwatch);
  s.run(0.4f);
  s.tap(316, 352, 0.2f);
  s.run(1.6f);
  s.tap(150, 352, 0.2f);
  s.run(1.2f);
  s.snap("stopwatch");
  s.os.apps().sw.reset();
  s.os.openApp(AppId::WorldClock);
  s.run(0.8f);
  s.snap("world-clock");
  s.os.openApp(AppId::Convert);
  s.run(0.6f);
  s.os.apps().q = 5;  // currency: 50 EUR in RON
  s.os.apps().from = 0;
  s.os.apps().to = 1;
  s.os.apps().value = 50;
  s.os.openApp(AppId::Talk);
  s.os.openApp(AppId::Convert);
  s.run(1.0f);
  s.snap("convert-currency");
  s.os.openApp(AppId::FindPhone);
  s.run(0.4f);
  s.tap(233, 318, 1.4f);
  s.snap("find-my-phone");
  s.os.openApp(AppId::Device);
  s.run(0.8f);
  s.snap("device");
  s.os.go(View::AppsSettings);
  s.run(0.8f);
  s.snap("settings-apps");
  s.os.go(View::Home);
  s.run(0.6f);
  {
    CloudPush p;
    p.kind = CloudPush::Card;
    p.source = "connector";
    p.app = "claude";
    p.by = "Ana";
    p.title = "Dinner at 8?";
    p.body = "Ana asks if 8 works. I'll bring figs.";
    std::string err;
    s.os.cloudPush(p, err);
  }
  s.run(1.2f);
  s.snap("quick-replies");
  s.os.go(View::Home);
  s.run(5.5f);
  s.snap("standby-eyes-only");
}

void benchMaps(AppSim& s) {
  s.os.openApp(AppId::Maps);
  s.run(1.5f);
  s.composeMs = 0;
  s.composed = 0;
  for (int k = 0; k < 3; ++k) {  // drag the map about
    s.finger = true;
    for (int i = 0; i <= 30; ++i) {
      s.fx = s.g.s(233 + 80 * sinf(i * 0.2f));
      s.fy = s.g.s(260 + 60 * cosf(i * 0.2f));
      s.step();
    }
    s.finger = false;
    s.run(0.5f);
  }
  s.os.appData(Fetch::RoutePlan, 200, kFixRoute);
  s.run(0.5f);
  s.tap(233, 358, 0.2f);
  s.run(4.0f);  // walking: the step card, the eyes, the pulse of "you"
}

void benchGames(AppSim& s) {
  s.os.openApp(AppId::Games);
  s.run(0.6f);
  s.tap(233, 170, 0.1f);
  s.composeMs = 0;
  s.composed = 0;
  for (int i = 0; i < 150; ++i) {
    s.roll = 0.3f * sinf(i * 0.05f);
    s.pitch = 0.3f * cosf(i * 0.04f);
    s.step();
  }
  s.swipe(233, 40, 233, 300, 0.1f);
  s.tap(233, 246, 0.1f);
  s.run(5.0f);
}

}  // namespace

int appsMode(const std::string& dir, const std::string& which, int px) {
  const DisplayGeometry g = px == 466 ? displays::kAmoled175 : displays::kLcd28;
  AppSim s(g, dir);
  if (which == "bench_maps") benchMaps(s);
  else if (which == "bench_games") benchGames(s);
  else allApps(s);
  printf("%s: %d frames, compose %.2f ms/frame on this PC\n", which.c_str(), s.composed, s.composeMs / (s.composed ? s.composed : 1));
  return 0;
}
