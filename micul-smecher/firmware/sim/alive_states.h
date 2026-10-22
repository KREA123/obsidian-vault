// SoulOS Alive, every screen (os/DESIGN-ALIVE.md §4, §9): one harness that brings the real device stack (Os, the
// apps, the eyes, the frame composer) into each state the web audit checks (os/tests/alive-audit.mjs), plus the
// screens only the device has. Shared by the simulator's stills (sim_screens.cpp: `program <dir> screens`) and the
// native round audit (test/test_suflet/test_audit.cpp), so the pictures and the checks are the same screens.
//
// Header-only on purpose: the simulator and the tests are separate programs; the fake SOUL Cloud answers with
// sim/app_fixtures.h (what the real cloud code makes).
#pragma once
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <string>
#include <vector>

#include "Alarms.h"
#include "Brain.h"
#include "Frame.h"
#include "Gestures.h"
#include "Memory.h"
#include "Os.h"
#include "Personality.h"
#include "app_fixtures.h"

namespace alive_states {

using namespace suflet;

struct Rig {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  Os os{&alarms};
  SoulMemory mem;
  TouchGestures touch;
  DisplayGeometry g;  // SOUL M's 2.8C by default; displays::kAmoled175 = SOUL S (Density.h)
  int W, H;
  std::vector<uint16_t> fb;
  Canvas cv;
  FrameComposer comp{&cv};
  bool finger = false;
  float fx = 0, fy = 0;
  uint32_t clock = 1790359080u;  // Fri 2026-09-26 18:38 local
  float frac = 0;
  Inputs in;
  NetInfo net;
  ClaudeInfo claude;
  struct Pending {
    float t;
    Fetch kind;
    std::string path;
  };
  std::vector<Pending> pending;
  std::vector<OsCmd> cmds;  // everything the OS asked the device to do
  bool haveFix = true, render = true;
  static inline bool silentAlarms = false;  // a board with no speaker and no buzzer (test_audit.cpp)

  explicit Rig(bool booted = true, int design = -1, const DisplayGeometry& geo = displays::kLcd28)
      : g(geo), W(geo.w), H(geo.h), fb((size_t)geo.w * geo.h), cv(geo.w, geo.h, fb.data()) {
    os.settings().booted = booted ? 1 : 0;
    os.settings().ai = (uint8_t)AiMode::Cloud;
    snprintf(os.settings().name, sizeof os.settings().name, "Miso");
    os.settings().born = clock - 86400 * 18;
    BirthInfo b;
    const uint8_t mac[6] = {0xC0, 0xFF, 0xEE, 0x12, 0x34, 0x56};
    const eyes::RollResult r = eyes::rollFromMac(mac);
    b.design = design >= 0 ? design : r.design;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = eyes::hashStr(eyes::kDesigns[b.design].id) ^ 0x5eed;
    os.setMemory(&mem);
    os.begin(g, b);
    net.configured = net.connected = net.linkUp = true;
    net.relay = net.paired = net.cloudOnline = true;
    net.owner = "Ana";
    net.cloudHost = "soul.example";
    net.ssid = "Acasa";
    net.saved = 1;
    os.setNet(net);
    PowerInfo pw;
    pw.batPct = 78;
    os.setPower(pw);
    StorageInfo si;
    si.fw = "1.9.0";
    si.board = geo.w == 480 ? "lcd28" : "amoled175";
    si.appKb = 2570;
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
    os.setAlarmSound(!silentAlarms);
    os.density().tuneTouch(touch);  // the glass's gesture thresholds, in millimetres (SOUL M: the defaults)
    touch.setMode(TouchMode::Text);
    in.hour = 18.6f;
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
        snprintf(b, sizeof b, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":%d,\"src\":\"phone\",\"age\":6,\"label\":\"\"}}", kFixLat, kFixLon, 14);
        return b;
      case Fetch::MapView: {
        const size_t z = path.find("z=");
        const int zz = z == std::string::npos ? 16 : atoi(path.c_str() + z + 2);
        if (zz <= 15) return std::string((const char*)kFixBundle15, sizeof kFixBundle15);
        if (zz >= 17) return std::string((const char*)kFixBundle17, sizeof kFixBundle17);
        return std::string((const char*)kFixBundle16, sizeof kFixBundle16);
      }
      case Fetch::RoutePlan: return kFixRoute;
      case Fetch::RouteGet:
        st = 404;
        return "{\"error\":{\"code\":\"no_route\"}}";
      case Fetch::FindPhone: return "{\"ringing\":true,\"reach\":\"page\"}";
      default: return "{}";
    }
  }

  void step() {
    const float dt = 1.0f / 30;
    frac += dt;
    while (frac >= 1) {
      frac -= 1;
      ++clock;
    }
    os.setClock(clock);
    touch.update(finger, fx, fy, dt);
    TouchEv e;
    while (touch.poll(e)) os.touch(e);
    OsCmd c;
    while (os.popCmd(c)) {
      cmds.push_back(c);
      if (c == OsCmd::AppFetch) {
        AppFetch f;
        while (os.popAppFetch(f)) pending.push_back({0.3f, f.kind, f.path});
      }
    }
    for (size_t i = 0; i < pending.size();) {
      pending[i].t -= dt;
      if (pending[i].t <= 0) {
        int st;
        const std::string body = answer(pending[i].kind, pending[i].path, st);
        os.appData(pending[i].kind, st, body);
        pending.erase(pending.begin() + (long)i);
      } else {
        ++i;
      }
    }
    in.hour = (clock % 86400) / 3600.0f;
    os.update(dt, brain);
    brain.update(dt, in);
    if (render) comp.compose(os);
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
  // a tap on control `id` (Os::controls): SOUL M taps where 1.9.0 always tapped (mx, my: its stills stay the same
  // pixels); any other glass taps the control's centre, wherever its layout put it (SOUL S, Density.h)
  void tapControl(int id, float mx, float my, float gap = 0.6f) {
    if (g.w == 480) {
      tap(mx, my, gap);
      return;
    }
    std::vector<Os::Control> cs;
    os.controls(cs);
    for (const Os::Control& c : cs)
      if (c.id == id) {
        tap((c.r.x0 + c.r.x1) * 0.5f / g.k(), (c.r.y0 + c.r.y1) * 0.5f / g.k(), gap);
        return;
      }
    tap(mx, my, gap);
  }
  void tapRow(int row, float gap = 0.6f) {
    os.wheelFocusRow(row);
    run(0.05f);
    tap(233, os.wheel().spec().y, gap);  // the focused row (y 290 on M)
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
  void addAlarm(int h, int m, uint8_t days, const char* label, bool on = true) {
    Alarm a;
    a.hour = (uint8_t)h;
    a.minute = (uint8_t)m;
    a.days = days;
    a.enabled = on;
    a.setLabel(label);
    alarms.add(a, clock);
  }
  void push(const char* title, const char* body) {  // a card from the owner's Claude (a connector), with replies
    CloudPush p;
    p.kind = CloudPush::Card;
    p.source = "connector";
    p.app = "claude";
    p.by = "Mom";
    p.title = title;
    p.body = body;
    std::string err;
    os.cloudPush(p, err);
  }
};

struct State {
  const char* name;
  const char* web;  // the web audit's still (os/tests/alive-audit.mjs), "" = only on the device
  bool booted;
};

// every state, in the web audit's order first (its number in the name), then the device's own screens
static const State kStates[] = {
    {"home-peek", "01-home-peek", true},       {"apps", "02-apps", true},
    {"today", "03-today", true},               {"talk", "04-talk", true},
    {"weather", "05-weather", true},           {"alarms", "07-alarms", true},
    {"notes", "08-notes", true},               {"focus", "09-focus", true},
    {"timer", "10-timer", true},               {"timer-countdown", "11-timer-countdown", true},
    {"claude", "12-claude", true},             {"claude-ask", "13-claude-ask", true},
    {"music", "16-music", true},               {"soul", "17-soul", true},
    {"games", "18-games", true},               {"settings", "19-settings", true},
    {"memory", "20-memory", true},             {"about", "21-about", true},
    {"aimode", "22-aimode", true},             {"mysoul", "23-mysoul", true},
    {"look", "24-look", true},                 {"maps", "25-maps", true},
    {"maps-here", "26-maps-here", true},       {"calendar", "27-calendar", true},
    {"breathe", "28-breathe", true},           {"habits", "29-habits", true},
    {"worldclock", "30-worldclock", true},     {"convert", "31-convert", true},
    {"findphone", "32-findphone", true},       {"device", "33-device", true},
    {"appsset", "34-appsset", true},           {"voice-listen", "35-voice-listen", true},
    {"voice-think", "36-voice-think", true},   {"voice-answer", "37-voice-answer", true},
    {"msg", "38-msg", true},                   {"alarm-ring", "39-alarm-ring", true},
    {"alarm-set", "40-alarm-set", true},       {"keyboard", "41-keyboard", true},
    {"control", "42-control", true},           {"game-star", "43-game-star", true},
    // the device's own screens
    {"notification", "", true},                {"stopwatch", "", true},
    {"weather-days", "", true},                {"calendar-event", "", true},
    {"note", "", true},                        {"memory-fact", "", true},
    {"answer-error", "", true},                {"maps-route", "", true},
    {"maps-walking", "", true},                {"game-over", "", true},
    {"wifi", "", true},                        {"wifi-hotspot", "", true},
    {"pair-code", "", true},                   {"bridge", "", true},
    {"boot-birth", "", false},                 {"boot-name", "", false},
    {"boot-brain", "", false},                 {"boot-hold", "", false},
};
static const int kStateCount = (int)(sizeof kStates / sizeof kStates[0]);

// Bring a fresh rig (Rig(kStates[i].booted)) into state `name`; false if unknown. Leaves it settled (springs,
// fades, the lid wipe done), except where the state is a moment (listening: the finger is still on the glass).
inline bool setup(Rig& s, const std::string& n) {
  Os& os = s.os;
  s.run(1.2f);
  auto open = [&](AppId a, float t = 1.2f) {
    os.openApp(a);
    s.run(t);
  };
  if (n == "standby") {  // the eyes alone (nothing to do: the rig has run 1.2 s)
  } else if (n == "home-peek") {
    s.tap(233, 300, 0.1f);
    s.run(1.0f);
  } else if (n == "apps") {
    s.swipe(330, 240, 150, 240, 0.0f);
    s.run(2.5f);
  } else if (n == "today") {
    s.swipe(233, 380, 233, 150, 0.4f);
    s.swipe(233, 380, 233, 200, 0.4f);
    s.run(1.0f);
  } else if (n == "talk") {
    open(AppId::Talk);
  } else if (n == "weather") {
    open(AppId::Weather, 1.6f);
  } else if (n == "weather-days") {
    open(AppId::Weather, 1.6f);
    s.swipe(330, 260, 150, 260, 0.8f);
  } else if (n == "alarms") {
    s.addAlarm(7, 0, 0x1F, "Wake up");
    s.addAlarm(9, 30, 0x60, "Slow coffee", false);
    open(AppId::Alarms);
    os.wheelFocusRow(1);
    s.run(0.6f);
  } else if (n == "notes" || n == "note") {
    os.notes().push_back({"Gift for dad: thermos", s.clock - 3600 * 5});
    os.notes().push_back({"Cat name: Fluff", s.clock - 600});
    open(AppId::Notes);
    os.wheelFocusRow(0);
    s.run(0.6f);
    if (n == "note") s.tap(233, os.wheel().spec().y, 1.0f);
  } else if (n == "focus") {
    open(AppId::Focus);
  } else if (n == "timer") {
    open(AppId::Timer);
  } else if (n == "timer-countdown") {
    open(AppId::Timer);
    os.startTimer(180, false);
    s.run(3.0f);
  } else if (n == "claude" || n == "claude-ask") {
    s.claude.linked = true;
    s.claude.busy = n == "claude";
    s.claude.msg = n == "claude" ? "project \xE2\x80\x9Csite\xE2\x80\x9D \xC2\xB7 3 approvals today" : "";
    s.claude.approvals = 3;
    if (n == "claude-ask") {
      s.claude.prompt = true;
      s.claude.tool = "site \xC2\xB7 Bash";
      s.claude.hint = "npm run build";
    }
    os.setClaude(s.claude);
    open(AppId::Claude, n == "claude-ask" ? 5.6f : 1.2f);  // (after the "Claude needs you" banner)
  } else if (n == "music") {
    open(AppId::Music);
    s.tapControl(200, 233, 296, 0.6f);  // play
  } else if (n == "soul" || n == "mysoul") {
    open(AppId::MySoul);
  } else if (n == "look") {
    open(AppId::MySoul);
    s.tapControl(19, 172, 326, 0.8f);    // Look
    s.tapControl(3001, 363, 214, 0.8f);  // ›: preview the next birth
  } else if (n == "games") {
    open(AppId::Games);
  } else if (n == "game-star") {
    open(AppId::Games);
    s.tapRow(0, 1.5f);
  } else if (n == "game-over") {
    open(AppId::Games);
    s.tapRow(2, 0.2f);
    const games::EyeMemory& m = os.apps().memory;
    int guard = 0;
    while (m.phase() == games::EyeMemory::Phase::Show && guard++ < 300) s.step();
    static const float kx[] = {233, 413, 233, 53}, ky[] = {53, 233, 413, 233};
    const int wrong = (m.sequence()[0] + 2) % 4;
    s.tap(kx[wrong], ky[wrong], 1.4f);
  } else if (n == "settings") {
    os.go(View::Settings);
    s.run(1.2f);
  } else if (n == "memory" || n == "memory-fact") {
    if (n == "memory-fact") {
      os.ask("remember that my sister's birthday is on 14 March");
      s.run(1.0f);
    }
    os.go(View::Home);
    s.run(0.4f);
    os.go(View::Settings);
    s.run(0.4f);
    os.wheelReveal(100 + 11);
    s.tap(233, os.wheel().spec().y, 1.2f);
    if (n == "memory-fact") s.tapRow(1, 1.0f);
  } else if (n == "about") {
    os.go(View::About);
    s.run(1.2f);
  } else if (n == "aimode") {
    os.go(View::AiMode);
    s.run(1.2f);
  } else if (n == "maps") {
    s.haveFix = false;
    open(AppId::Maps, 1.6f);
  } else if (n == "maps-here" || n == "maps-route" || n == "maps-walking") {
    open(AppId::Maps, 1.8f);
    if (n != "maps-here") {
      os.appData(Fetch::RoutePlan, 200, kFixRoute);
      s.run(1.2f);
    }
    if (n == "maps-walking") {
      s.tapControl(229, 233, 326, 0.8f);  // Start
      const maps::RouteData& r = os.apps().route;
      const int i = r.steps[1].idx;
      char fix[200];
      snprintf(fix, sizeof fix, "{\"fix\":{\"lat\":%.6f,\"lon\":%.6f,\"acc\":12,\"src\":\"phone\",\"age\":2}}",
               r.shape[2 * i] * 0.3 + r.shape[2 * i - 2] * 0.7, r.shape[2 * i + 1] * 0.3 + r.shape[2 * i - 1] * 0.7);
      os.appData(Fetch::Where, 200, fix);
      s.run(1.0f);
    }
  } else if (n == "calendar" || n == "calendar-event") {
    open(AppId::Calendar, 1.6f);
    if (n == "calendar-event") s.tapRow(1, 1.0f);
  } else if (n == "breathe") {
    open(AppId::Breathe);
  } else if (n == "habits") {
    open(AppId::Habits);
    s.tapRow(1, 2.6f);  // (after the eyes' approve)
  } else if (n == "worldclock") {
    open(AppId::WorldClock);
  } else if (n == "convert") {
    open(AppId::Convert);
  } else if (n == "findphone") {
    open(AppId::FindPhone);
  } else if (n == "device") {
    open(AppId::Device);
  } else if (n == "appsset") {
    os.go(View::AppsSettings);
    s.run(0.4f);
    os.wheelFocusRow(2);
    s.run(1.0f);
  } else if (n == "voice-listen") {
    open(AppId::Talk);
    s.fx = s.g.s(233);
    s.fy = s.g.s(200);
    s.finger = true;
    s.run(1.2f);  // (the finger stays on the glass)
  } else if (n == "voice-think" || n == "voice-answer" || n == "answer-error") {
    open(AppId::Talk, 0.6f);
    os.ask("Remind me at 5 to call the bank");
    s.run(1.2f);
    AiJob j;
    while (os.popAiJob(j)) {
    }
    if (n != "voice-think") {
      AiOutcome o;
      if (n == "answer-error") {
        o.err = AiErr::Network;
      } else {
        o.reply = parseReply(std::string("{\"say\":\"Done. I'll ping you at 5:00 PM.\",\"actions\":[{\"type\":\"reminder.create\","
                                         "\"time\":\"17:00\",\"text\":\"call the bank\"}]}"));
      }
      os.aiResult(o);
      s.run(1.6f);
    }
  } else if (n == "msg") {
    s.push("Home for dinner at 6?", "Dad is cooking. Tell me if you're late.");
    s.run(1.4f);
  } else if (n == "alarm-ring") {
    s.addAlarm(7, 0, 0x7F, "Wake up");
    os.alarmDue(0);
    s.run(1.5f);
  } else if (n == "alarm-set") {
    open(AppId::Alarms);
    s.tapRow(0, 1.2f);  // + New: the Rim-Dial
  } else if (n == "keyboard") {
    open(AppId::Notes);
    s.tapRow(0, 1.2f);  // + New: the keyboard
  } else if (n == "control") {
    s.swipe(233, 120, 233, 330, 0.2f);
    s.run(1.0f);
  } else if (n == "notification") {
    os.toast("Ana: home for dinner at 6?", Rgb::hex(0xFFF0C8), 4.0f);
    s.run(0.6f);
  } else if (n == "stopwatch") {
    open(AppId::Stopwatch);
    s.tapControl(200, 296, 352, 0.2f);  // start
    s.run(1.6f);
    s.tapControl(221, 170, 352, 0.2f);  // lap
    s.run(1.0f);
  } else if (n == "wifi" || n == "wifi-hotspot") {
    os.go(View::Settings);
    s.run(0.3f);
    os.go(View::Wifi);
    s.run(1.0f);
    if (n == "wifi-hotspot") s.tapControl(17, 233, 300, 1.0f);  // Add my phone's hotspot
  } else if (n == "pair-code") {
    s.net.paired = false;
    s.net.pairCode = "K7Q2M9XD";
    s.net.pairUrl = "https://soul.example/pair?c=K7Q2M9XD";
    os.setNet(s.net);
    os.go(View::Pair);
    s.run(1.2f);
  } else if (n == "bridge") {
    s.net.bridgeCode = "482913";
    s.net.ip = "192.168.1.42";
    s.net.paired = false;
    os.setNet(s.net);
    os.go(View::Bridge);
    s.run(1.2f);
  } else if (n == "boot-birth") {
    s.run(2.6f);
  } else if (n == "boot-name" || n == "boot-brain" || n == "boot-hold") {
    s.run(2.0f);
    s.tap(233, 250, 1.0f);  // tap to meet me
    if (n != "boot-name") {
      s.tapControl(100, 233, 226, 1.0f);  // the first name
      if (n == "boot-hold") {
        s.tapControl(103, 233, 336, 0.6f);  // No AI
        s.tapControl(1, 233, 412, 1.0f);    // Next
      }
    }
    s.run(0.6f);
  } else {
    return false;
  }
  return true;
}

}  // namespace alive_states
