// Native simulator: runs the exact device stack (lib/Suflet: Brain, SoulOS,
// the SOUL eyes, the frame composer) on the PC with a scripted finger, a
// fake clock and a fake network, and records what the 480 px glass shows.
//
//   .pio/build/sim/program <out_dir> [scenario|all] [chip-id hex] [466|480]
//
// Each scenario writes <out_dir>/<name>.rgb (raw RGB888 frames) + <name>.json
// (frame count, fps, marked stills). tools/frames_to_media.py turns them
// into PNG stills / GIF / MP4. The AI answers come from recorded API bodies
// (the same JSON api.anthropic.com returns), parsed by the real protocol code.
// It also reports the frame cost on this PC and how much of the glass each
// frame touches (the device numbers scale from these, see BRINGUP.md).
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

#include "AiProtocol.h"
#include "Alarms.h"
#include "Brain.h"
#include "EyeRig.h"
#include "Frame.h"
#include "Geometry.h"
#include "Gestures.h"
#include "Os.h"
#include "Personality.h"

using namespace suflet;

namespace {

DisplayGeometry gGeom = displays::kLcd28;
int W = 480, H = 480;
inline float P(float designPx) { return gGeom.s(designPx); }
constexpr float kFps = 30.0f;
uint8_t gMac[6] = {0xC0, 0xFF, 0xEE, 0x12, 0x34, 0x56};

struct Recorder {
  std::string dir, name;
  FILE* f = nullptr;
  int frames = 0;
  std::vector<int> stills;
  void open() {
    f = fopen((dir + "/" + name + ".rgb").c_str(), "wb");
    if (!f) {
      perror("open");
      exit(1);
    }
  }
  void frame(const Canvas& cv) {
    static std::vector<uint8_t> rgb;
    rgb.resize((size_t)W * H * 3);
    for (int i = 0; i < W * H; ++i) {
      const Rgb p = Rgb::from565(cv.data()[i]);
      rgb[i * 3] = p.r;
      rgb[i * 3 + 1] = p.g;
      rgb[i * 3 + 2] = p.b;
    }
    fwrite(rgb.data(), 1, rgb.size(), f);
    ++frames;
  }
  void close(const char* caption) {
    fclose(f);
    std::string st, body;
    for (size_t i = 0; i < stills.size(); ++i) st += (i ? "," : "") + std::to_string(stills[i]);
    for (int i = 0; i < frames; ++i) body += i ? ",[0,0,0,0]" : "[0,0,0,0]";
    FILE* j = fopen((dir + "/" + name + ".json").c_str(), "wb");
    fprintf(j, "{\"name\":\"%s\",\"w\":%d,\"h\":%d,\"fps\":%.0f,\"frames\":%d,\"caption\":\"%s\",\"stills\":[%s],\"body\":[%s]}\n",
            name.c_str(), W, H, kFps, frames, caption, st.c_str(), body.c_str());
    fclose(j);
  }
};

// A recorded Claude Messages API answer whose text block is `json`.
std::string claudeBody(const std::string& json) {
  std::string esc;
  for (char c : json) {
    if (c == '"' || c == '\\') esc += '\\';
    esc += c;
  }
  return "{\"id\":\"msg_sim\",\"type\":\"message\",\"role\":\"assistant\",\"model\":\"claude-opus-5-5\",\"content\":["
         "{\"type\":\"thinking\",\"thinking\":\"\",\"signature\":\"sim\"},{\"type\":\"text\",\"text\":\"" + esc +
         "\"}],\"stop_reason\":\"end_turn\",\"usage\":{\"input_tokens\":1200,\"output_tokens\":64}}";
}

struct Sim {
  Brain brain;
  Alarms alarms;
  Os os{&alarms};
  TouchGestures touch;
  MotionDetector motion;
  std::vector<uint16_t> fb = std::vector<uint16_t>((size_t)W * H);
  Canvas cv{W, H, fb.data()};
  FrameComposer comp{&cv};
  Recorder* rec = nullptr;
  bool finger = false;
  float fx = 0, fy = 0;
  uint32_t clock = 1790359080u;  // 2026-09-26 18:38 local
  float clockFrac = 0;
  Inputs in;
  AiConfig ai;
  NetInfo net;
  ClaudeInfo claude;
  // the fake network: answers arrive after `aiDelay` seconds
  std::vector<std::pair<float, AiOutcome>> pending;
  std::function<std::pair<int, std::string>(const AiJob&)> aiServer;
  float aiDelay = 1.3f;
  double composeMs = 0;
  uint64_t changedPx = 0;
  int composed = 0;

  explicit Sim(bool booted) : brain(Personality::fromSeed(0xC0FFEE), 7) {
    const eyes::RollResult r = eyes::rollFromMac(gMac);
    BirthInfo b;
    b.design = r.design;
    char chip[24];
    snprintf(chip, sizeof chip, "%02X:%02X:%02X:%02X:%02X:%02X", gMac[0], gMac[1], gMac[2], gMac[3], gMac[4], gMac[5]);
    b.chip = chip;
    b.seed = eyes::hashStr(eyes::kDesigns[r.design].id) ^ 0x5eed;
    os.settings().booted = booted ? 1 : 0;
    os.settings().ai = (uint8_t)AiMode::Claude;
    snprintf(os.settings().name, sizeof os.settings().name, "Miso");
    os.settings().born = clock - 86400 * 9;
    os.begin(gGeom, b);
    in.hour = 18.6f;
    ai.mode = AiMode::Claude;
    ai.anthropicKey = "sk-ant-sim-0000000000000000000000";
    net.configured = net.connected = true;
    net.ssid = "Acasa";
    net.ip = "192.168.1.42";
    net.keyClaude = true;
    net.maskClaude = maskKey(ai.anthropicKey);
    net.apName = "SOUL-3456";
    os.setNet(net);
    claude.bleName = "Claude-Suflet-3456";
    os.setClaude(claude);
    PowerInfo pw;
    pw.batPct = 78;
    os.setPower(pw);
    touch.setMode(TouchMode::Text);
    aiServer = [](const AiJob&) {
      return std::make_pair(200, claudeBody("{\"say\":\"Hi! I'm here.\",\"face\":\"happy\",\"actions\":[]}"));
    };
  }

  void step(bool render) {
    const float dt = 1.0f / kFps;
    clockFrac += dt;
    while (clockFrac >= 1.0f) {
      clockFrac -= 1.0f;
      ++clock;
    }
    os.setClock(clock);
    touch.update(finger, fx, fy, dt);
    TouchEv te;
    while (touch.poll(te)) os.touch(te);
    // the network
    AiJob job;
    while (os.popAiJob(job)) {
      HttpRequest rq;
      AiErr e = buildRequest(ai, job.ctx, job.history, job.text, rq);
      AiOutcome o;
      if (e != AiErr::None) {
        o.err = e;
      } else {
        const auto resp = aiServer(job);
        o = parseResponse(ai, resp.first, resp.second.data(), resp.second.size(), resp.first < 0 ? AiErr::Network : AiErr::None, clock);
      }
      pending.push_back({aiDelay, o});
    }
    for (size_t i = 0; i < pending.size();) {
      pending[i].first -= dt;
      if (pending[i].first <= 0) {
        os.aiResult(pending[i].second);
        pending.erase(pending.begin() + i);
      } else {
        ++i;
      }
    }
    OsCmd c;
    while (os.popCmd(c)) {
      if (c == OsCmd::StartPortal) {
        net.portal = true;
        os.setNet(net);
      } else if (c == OsCmd::StopPortal) {
        net.portal = false;
        os.setNet(net);
      }
    }
    const int due = alarms.poll(clock);
    if (due >= 0) os.alarmDue(due);
    in.stillFor += dt;
    in.hour = (clock % 86400) / 3600.0f;
    os.update(dt, brain);
    brain.update(dt, in);
    Cue cue;
    while (brain.popCue(cue)) {
      if (cue == Cue::ClaudeApprove || cue == Cue::ClaudeDeny) {
        claude.prompt = false;
        if (cue == Cue::ClaudeApprove) ++claude.approvals;
        else ++claude.denials;
        os.setClaude(claude);
        brain.event(Ev::ClaudePromptGone);
      }
    }
    const auto t0 = std::chrono::high_resolution_clock::now();
    const Rect ch = comp.compose(os);
    composeMs += std::chrono::duration<double, std::milli>(std::chrono::high_resolution_clock::now() - t0).count();
    changedPx += ch.empty() ? 0 : (uint64_t)ch.w() * ch.h();
    ++composed;
    if (render && rec) rec->frame(cv);
  }
  void run(float s, bool render = true) {
    const int n = (int)(s * kFps + 0.5f);
    for (int i = 0; i < n; ++i) step(render);
  }
  void mark() {
    if (rec && rec->frames) rec->stills.push_back(rec->frames - 1);
  }
  // design px -> panel px
  void press(float x, float y, float holdS, float gapS, bool markWhileDown = false) {
    fx = P(x);
    fy = P(y);
    finger = true;
    run(holdS);
    if (markWhileDown) mark();
    finger = false;
    run(gapS);
  }
  void tap(float x, float y, float gap = 0.5f) { press(x, y, 0.08f, gap); }
  void swipe(float x0, float y0, float x1, float y1, float gap = 0.5f) {
    const int n = 6;
    finger = true;
    for (int i = 0; i <= n; ++i) {
      fx = P(x0 + (x1 - x0) * i / n);
      fy = P(y0 + (y1 - y0) * i / n);
      step(true);
    }
    finger = false;
    run(gap);
  }
  void type(const char* text) {
    const char* p = text;
    while (*p) {
      const uint32_t cp = utf8::next(p);
      float x, y;
      if (!os.keyboard().keyCenter(cp == ' ' ? (uint32_t)' ' : utf8::lower(cp), x, y)) continue;
      fx = x + 1;
      fy = y + 2;
      finger = true;
      run(0.1f);
      finger = false;
      run(0.07f);
    }
  }
  void typeDone() {
    float x, y;
    os.keyboard().keyCenter(KeyId::Done, x, y);
    fx = x;
    fy = y;
    finger = true;
    run(0.1f);
    finger = false;
    run(0.2f);
  }
};

struct Scenario {
  const char* name;
  const char* caption;
  bool booted;
  std::function<void(Sim&)> script;
};

std::vector<Scenario> scenarios() {
  return {
      {"boot", "First boot: birth from the chip id, name, brain, hold the glass", false,
       [](Sim& s) {
         s.run(2.2f);
         s.mark();  // the design is revealed
         s.tap(233, 250, 0.6f);
         s.mark();  // name
         s.tap(233, 212, 0.7f);
         s.mark();  // brain
         s.tap(233, 232, 0.6f);  // Claude · your key
         s.mark();
         s.tap(233, 420, 0.6f);  // Next
         s.mark();               // hold the glass
         s.press(233, 233, 1.2f, 0.0f, true);  // holding: listening, ice rim
         s.run(1.5f);
         s.mark();  // home
       }},
      {"home", "Home: the eyes are the UI. Boop, laugh, look at the finger", true,
       [](Sim& s) {
         s.run(2.0f);
         s.mark();
         s.tap(233, 240, 0.25f);
         s.tap(233, 240, 1.2f);  // double tap: laugh
         s.mark();
         s.press(120, 120, 0.3f, 0.0f, true);  // a touch: the eyes glance at the finger
         s.run(1.5f);
       }},
      {"expressions", "All 31 expressions on this SOUL's design", true,
       [](Sim& s) {
         s.run(0.5f);
         for (int e = 0; e < eyes::X_Count; ++e) {
           s.os.face().react(e, 1.6f);
           s.run(e == eyes::X_hello || e == eyes::X_goodbye ? 1.0f : 0.9f);
           s.mark();
           s.run(0.4f);
         }
       }},
      {"launcher", "Swipe from the face: the orbit of apps, open Alarms, set one in 3 touches", true,
       [](Sim& s) {
         s.run(0.8f);
         s.swipe(330, 240, 150, 240);
         s.mark();  // launcher: Talk
         s.swipe(330, 330, 150, 330);
         s.mark();  // Alarms
         s.tap(233, 336, 0.6f);
         s.mark();  // alarms list
         s.tap(233, 376, 0.8f);  // + New: the Rim-Dial
         s.mark();
         // drag the hour ring round to 06 (bottom-left), let go: minutes come up, then ✓
         const float a0 = TimePicker::hourAngle((localclock::hour(s.clock) + 1) % 24);
         const float a1 = TimePicker::hourAngle(6) + 360.0f;
         s.finger = true;
         for (int i = 0; i <= 24; ++i) {
           float a = a0 + (a1 - a0) * i / 24.0f;
           while (a > 360) a -= 360;
           s.fx = P(233) + P(205) * cosf(a * 3.14159265f / 180);
           s.fy = P(233) + P(205) * sinf(a * 3.14159265f / 180);
           s.step(true);
         }
         s.finger = false;
         s.run(0.8f);
         s.mark();
         s.tap(233, 350, 1.0f);  // ✓: saved at once
         s.mark();
       }},
      {"talk", "Talk to Claude: type on the round keyboard, it thinks, it sets the alarm", true,
       [](Sim& s) {
         s.aiServer = [](const AiJob& j) {
           (void)j;
           return std::make_pair(200, claudeBody("{\"say\":\"Done: I'll wake you at 6:30. Sleep well!\",\"face\":\"happy\","
                                                 "\"actions\":[{\"type\":\"alarm.set\",\"time\":\"06:30\",\"label\":\"Wake up\","
                                                 "\"repeat\":\"weekdays\"}]}"));
         };
         s.run(0.6f);
         s.press(233, 260, 0.8f, 0.4f, true);  // hold the glass: listening; let go: the keyboard
         s.mark();
         s.type("wake me at 6");
         s.mark();
         s.typeDone();
         s.run(0.6f);
         s.mark();  // thinking
         s.run(1.4f);
         s.mark();  // the answer
         s.run(2.0f);
       }},
      {"errors", "When it fails, the eyes say it: bad key, offline", true,
       [](Sim& s) {
         s.aiServer = [](const AiJob&) {
           return std::make_pair(401, std::string("{\"type\":\"error\",\"error\":{\"type\":\"authentication_error\",\"message\":\"invalid x-api-key\"}}"));
         };
         s.os.ask("what's the weather tomorrow?");
         s.run(1.0f);
         s.run(1.0f);
         s.mark();
         s.run(1.0f);
         s.net.connected = false;
         s.os.setNet(s.net);
         s.os.ask("set a timer for 5 minutes");
         s.run(1.2f);
         s.mark();
       }},
      {"claude", "Claude Code asks: shocked, then wide eyes on you; hold the glass = yes", true,
       [](Sim& s) {
         s.run(0.6f);
         s.claude.linked = true;
         s.claude.busy = true;
         s.claude.msg = "editing src/main.cpp";
         s.os.setClaude(s.claude);
         s.brain.event(Ev::ClaudeUp);
         s.brain.event(Ev::ClaudeBusyStart);
         s.run(2.0f);
         s.mark();  // working: the reading scan
         s.claude.busy = false;
         s.claude.prompt = true;
         s.claude.tool = "Bash";
         s.claude.hint = "npm test -- --watch=false";
         s.os.setClaude(s.claude);
         s.brain.event(Ev::ClaudeBusyEnd);
         s.brain.event(Ev::ClaudePrompt);
         s.run(0.4f);
         s.mark();  // shocked
         s.run(1.6f);
         s.mark();  // wide eyes, amber rim
         s.press(233, 260, 1.6f, 0.0f);
         s.mark();  // the mint arc is full
         s.finger = false;
         s.run(1.4f);
         s.mark();
       }},
      {"apps", "Timer, notes, Today, Settings, My SOUL", true,
       [](Sim& s) {
         s.run(0.4f);
         s.os.go(View::Timer);
         s.run(0.5f);
         s.mark();
         s.tap(150, 200, 1.0f);  // 1 min
         s.mark();
         s.os.go(View::Notes);
         s.run(0.4f);
         s.tap(233, 360, 0.6f);  // + New
         s.type("buy oat milk");
         s.typeDone();
         s.run(0.6f);
         s.mark();
         s.os.go(View::Today);
         s.run(0.6f);
         s.mark();
         s.os.go(View::Settings);
         s.run(0.6f);
         s.mark();
         s.os.go(View::MySoul);
         s.run(1.0f);
         s.mark();
         s.os.go(View::AiMode);
         s.run(0.6f);
         s.mark();
         s.os.go(View::Wifi);
         s.tap(233, 300, 0.6f);  // set up from a phone
         s.mark();
         s.os.go(View::Home);
         s.run(55.0f, false);  // the 1 min timer rings
         s.run(0.6f);
         s.mark();
       }},
  };
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <out_dir> [scenario|all] [chip-id hex, 12 digits] [466|480]\n", argv[0]);
    return 2;
  }
  const std::string dir = argv[1];
  const std::string which = argc > 2 ? argv[2] : "all";
  if (argc > 3 && strlen(argv[3]) == 12) {
    for (int i = 0; i < 6; ++i) {
      char b[3] = {argv[3][2 * i], argv[3][2 * i + 1], 0};
      gMac[i] = (uint8_t)strtoul(b, nullptr, 16);
    }
  }
  const int px = argc > 4 ? atoi(argv[4]) : 480;
  if (px == 466) gGeom = displays::kAmoled175;
  W = gGeom.w;
  H = gGeom.h;
  const eyes::RollResult r = eyes::rollFromMac(gMac);
  printf("chip %02X%02X%02X%02X%02X%02X: design #%03d %s (%s), 1 in %.0f\n", gMac[0], gMac[1], gMac[2], gMac[3], gMac[4],
         gMac[5], eyes::kDesigns[r.design].num, eyes::kDesigns[r.design].name, eyes::kRarityName[(int)r.rarity], 1.0 / r.odds);
  for (const Scenario& sc : scenarios()) {
    if (which != "all" && which != sc.name) continue;
    Recorder rec;
    rec.dir = dir;
    rec.name = sc.name;
    rec.open();
    Sim s(sc.booted);
    s.rec = &rec;
    sc.script(s);
    rec.close(sc.caption);
    printf("%-12s %4d frames  compose %.2f ms/frame on this PC, %.0f%% of the glass changed per frame  %s\n", sc.name,
           rec.frames, s.composeMs / (s.composed ? s.composed : 1),
           100.0 * s.changedPx / ((double)W * H * (s.composed ? s.composed : 1)), sc.caption);
  }
  return 0;
}
