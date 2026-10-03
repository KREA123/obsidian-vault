// Native simulator: runs the exact device stack (lib/Suflet: Brain, SoulOS,
// the SOUL eyes, the frame composer) on the PC with a scripted finger, a
// fake clock and a fake network, and records what the 480 px glass shows.
//
//   .pio/build/sim/program <out_dir> [scenario|all] [chip-id hex] [466|480]
//   .pio/build/sim/program <out_dir> keys ["key string"]   drive the IMU by hand (keysMode)
//
// Each scenario writes <out_dir>/<name>.rgb (raw RGB888 frames) + <name>.json
// (frame count, fps, marked stills). tools/frames_to_media.py turns them
// into PNG stills / GIF / MP4. The AI answers come from recorded API bodies
// (the same JSON api.anthropic.com returns), parsed by the real protocol code.
// It also reports the frame cost on this PC and how much of the glass each
// frame touches (the device numbers scale from these, see BRINGUP.md).
#include <chrono>
#include <cmath>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

#include "AiProtocol.h"
#include "Alarms.h"
#include "CloudLink.h"
#include "Brain.h"
#include "EyeMotion.h"
#include "EyeRig.h"
#include "Frame.h"
#include "Geometry.h"
#include "Gestures.h"
#include "Os.h"
#include "Personality.h"
#include <openssl/rand.h>

#include "BridgeLink.h"
#include "sim_cloud.h"
#include "sim_lan.h"

#if defined(__unix__) || defined(__APPLE__)
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#define SIM_TTY 1
#endif

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
  std::string extra;  // more JSON fields (",\"pose\":[...]")
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
    fprintf(j, "{\"name\":\"%s\",\"w\":%d,\"h\":%d,\"fps\":%.0f,\"frames\":%d,\"caption\":\"%s\",\"stills\":[%s],\"body\":[%s]%s}\n",
            name.c_str(), W, H, kFps, frames, caption, st.c_str(), body.c_str(), extra.c_str());
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
  std::function<bool(const AiJob&)> cloudAsk;  // cloud mode: turns go to SOUL Cloud over the real socket
  std::function<void(OsCmd)> onCmd;            // lan mode: the SOUL Bridge commands (a new code, forget)
  float aiDelay = 1.3f;
  double composeMs = 0;
  uint64_t changedPx = 0;
  int composed = 0;
  // the device in space (EyeMotion): roll in the glass plane (+ = counter-clockwise),
  // pitch (+ = top toward you, 90 = face down), yaw (+ = turned to its right), radians.
  // Every frame the IMU is read 3 times (90 Hz) along the way from the last pose.
  eyes::PoseImu imu;
  float roll = 0, pitch = 0, yaw = 0, pRoll = 0, pPitch = 0, pYaw = 0;
  float rollV = 0, rollFriction = 2.0f;  // a flick: spins on, slowing down
  bool tremor = false;  // held in a hand
  int tapNow = 0;       // a tap on the case this frame
  double imuT = 0;
  std::string poseJson;             // per recorded frame: [roll, pitch, yaw, tap]

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
    // the IMU
    roll += rollV * dt;
    rollV *= expf(-rollFriction * dt);
    if (fabsf(rollV) < 0.05f) rollV = 0;
    for (int k = 1; k <= 3; ++k) {
      const float q = k / 3.0f, h = dt / 3;
      imu.lin[2] = (tapNow && k == 1) ? -0.7f : 0.0f;
      eyes::ImuSample smp = imu.sample(pRoll + (roll - pRoll) * q, pPitch + (pitch - pPitch) * q, pYaw + (yaw - pYaw) * q, h);
      imuT += h;
      if (tremor) {
        smp.gx += 0.05f * (float)sin(imuT * 57);
        smp.gy += 0.04f * (float)sin(imuT * 43 + 1);
        smp.gz += 0.03f * (float)sin(imuT * 71 + 2);
      }
      motion.update(smp.ax, smp.ay, smp.az, h);  // the Brain's gestures, as on the device
      os.imu(h, smp);
    }
    tapNow = 0;
    pRoll = roll;
    pPitch = pitch;
    pYaw = yaw;
    {
      Ev me;
      while (motion.poll(me)) os.motion(me);
    }
    touch.update(finger, fx, fy, dt);
    TouchEv te;
    while (touch.poll(te)) os.touch(te);
    // the network
    AiJob job;
    while (os.popAiJob(job)) {
      if (cloudAsk) {
        if (!cloudAsk(job)) {  // the socket is not up: what the device does (rules)
          AiOutcome o;
          o.err = AiErr::Network;
          pending.push_back({0.1f, o});
        }
        continue;
      }
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
      if (onCmd) onCmd(c);
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
    if (render && rec) {
      rec->frame(cv);
      char b[160];
      snprintf(b, sizeof b, "%s[%.4f,%.4f,%.4f,%d,%.3f,\"%s\"]", poseJson.empty() ? "" : ",", roll, pitch, yaw, lastTap,
               os.face().motionPose().dizzy, label);
      poseJson += b;
      lastTap = 0;
    }
  }
  int lastTap = 0;
  const char* label = "";  // a caption for the demo clip (tools/motion_clip.py)
  // ease the device to a pose over `s` seconds (smoothstep), then hold `hold`
  void move(float r, float p, float y, float s, float hold = 0) {
    const int n = (int)(s * kFps + 0.5f);
    const float r0 = roll, p0 = pitch, y0 = yaw;
    for (int i = 1; i <= n; ++i) {
      float q = (float)i / n;
      q = q * q * (3 - 2 * q);
      roll = r0 + (r - r0) * q;
      pitch = p0 + (p - p0) * q;
      yaw = y0 + (y - y0) * q;
      step(true);
    }
    run(hold);
  }
  void caseTap() {
    tapNow = 1;
    lastTap = 1;
  }
  void run(float s, bool render = true) {
    const int n = (int)(s * kFps + 0.5f);
    for (int i = 0; i < n; ++i) step(render);
  }
  void mark() {
    if (rec && rec->frames) rec->stills.push_back(rec->frames - 1);
    if (getenv("SIM_VERBOSE")) fprintf(stderr, "  still %d: view %s\n", rec ? rec->frames - 1 : -1, viewName(os.view()));
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
      {"cloud", "SOUL Cloud: the pairing code + QR, paired, a reminder and a card from your Claude, Wi-Fi join QR", true,
       [](Sim& s) {
         s.net.relay = s.net.cloudOnline = true;
         s.net.pairCode = "7KQ3M9XD";
         s.net.pairUrl = "https://soul.example/pair#c=7KQ3M9XD&d=soul-c0ffee123456";
         s.os.setNet(s.net);
         s.run(0.4f);
         s.os.go(View::AiMode);
         s.run(0.5f);
         s.tap(233, 150, 1.0f);  // SOUL Cloud -> the pairing screen
         s.mark();
         s.net.paired = true;
         s.net.owner = "Ana";
         s.net.pairCode.clear();
         s.net.pairUrl.clear();
         s.os.setNet(s.net);
         s.run(1.0f);
         s.mark();  // paired: hi Ana
         s.run(2.5f);
         s.os.go(View::Home);
         s.run(1.0f);
         CloudLink link;
         std::string err;
         const char* rem = "{\"v\":1,\"t\":\"push\",\"seq\":412,\"action\":\"reminder.create\",\"args\":{\"when\":"
                           "\"2026-09-27T18:00\",\"text\":\"Call the bank\"},\"item_id\":\"r_412\",\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"},"
                           "\"say\":\"Tomorrow at 18:00: call the bank.\"}";
         link.feed(rem, strlen(rem));
         s.os.cloudPush(link.push, err);
         s.run(0.5f);
         s.mark();  // surprised
         s.run(1.0f);
         s.mark();  // happy + toast
         const char* card = "{\"v\":1,\"t\":\"push\",\"seq\":413,\"action\":\"answer.show\",\"args\":{\"title\":\"Pancakes\","
                            "\"body\":\"1. 200 g flour, 2 eggs\\n2. 300 ml milk, a pinch of salt\\n3. rest 10 min\\n4. hot pan, a "
                            "little butter\"},\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"}}";
         link.feed(card, strlen(card));
         s.os.cloudPush(link.push, err);
         s.run(1.2f);
         s.mark();  // the card
         s.net.portal = true;
         s.net.apName = "SOUL-3456";
         s.net.apPass = "40718263";
         s.os.setNet(s.net);
         s.os.go(View::Wifi);
         s.run(1.0f);
         s.mark();  // the Wi-Fi join QR
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
         s.tap(233, 330, 0.6f);  // set up from a phone
         s.mark();
         s.os.go(View::Home);
         s.run(55.0f, false);  // the 1 min timer rings
         s.run(0.6f);
         s.mark();
       }},
      {"everywhere", "On the go: home Wi-Fi lost, the hotspot saved on SOUL, a question kept offline, a hotel login page, back online", true,
       [](Sim& s) {
         s.aiServer = [](const AiJob& j) {
           return std::make_pair(200, claudeBody(std::string("{\"say\":\"") +
                                                 (j.text.find("train") != std::string::npos ? "The 18:40 to Brasov is on time."
                                                                                            : "Hi! I'm here.") +
                                                 "\",\"face\":\"happy\",\"actions\":[]}"));
         };
         s.net.saved = 1;
         s.net.savedList = "Acasa";
         s.net.linkUp = true;
         s.os.setNet(s.net);
         s.run(1.0f);
         // out of the door: home is gone, SOUL looks for a network it knows
         s.net.connected = s.net.linkUp = false;
         s.net.searching = true;
         s.net.ssid.clear();
         s.net.ip.clear();
         s.os.setNet(s.net);
         s.run(12.0f, false);
         s.tap(233, 330, 0.3f);  // somebody walks by: awake
         s.run(10.0f, false);
         s.run(1.4f);
         s.mark();  // 01 standby offline: heavier lids, a glance around now and then
         s.tap(233, 330, 0.3f);
         s.os.go(View::Wifi);
         s.run(0.6f);
         s.mark();  // 02 Wi-Fi: looking for a known network
         s.tap(233, 270, 0.6f);
         s.mark();  // 03 the phone's hotspot: how to switch it on (iPhone / Android)
         s.tap(233, 336, 0.5f);
         s.type("ana iphone");
         s.typeDone();
         s.run(0.4f);
         s.mark();  // 04 its password on the round keyboard
         s.type("pinecone");
         s.typeDone();
         s.run(0.6f);
         s.net.saved = 2;
         s.net.savedList = "Acasa \u00B7 ana iphone";
         s.os.setNet(s.net);
         s.run(0.6f);
         s.mark();  // 05 saved: "I'll join it when it's on"
         s.os.go(View::Home);
         s.run(0.4f);
         s.os.ask("is my train on time?");
         s.run(1.0f);
         s.mark();  // 06 offline: the question is kept
         // a hotel Wi-Fi with a login page
         s.net.linkUp = s.net.captive = true;
         s.net.searching = false;
         s.net.ssid = "Hotel Guest";
         s.os.setNet(s.net);
         s.os.go(View::Wifi);
         s.run(1.2f);
         s.mark();  // 07 "Wi-Fi wants a login page": try the hotspot
         // the hotspot comes on: online, the kept question goes out by itself
         s.net.captive = false;
         s.net.connected = s.net.hotspot = true;
         s.net.ssid = "Ana\u2019s iPhone";
         s.net.ip = "172.20.10.4";
         s.os.setNet(s.net);
         s.run(1.0f);
         s.mark();  // 08 on the phone's hotspot
         s.os.go(View::Home);
         s.run(4.5f);
         s.mark();  // 09 "You asked earlier": the answer
         s.run(2.0f);
       }},
      {"glass", "SoulOS 5 Glass: standby = the eyes alone; touch, apps, keyboard, Claude, alarms, settings on frosted glass", true,
       [](Sim& s) {
         s.aiServer = [](const AiJob&) {
           return std::make_pair(200, claudeBody("{\"say\":\"Done: I'll wake you at 6:45. Sleep well!\",\"face\":\"happy\","
                                                 "\"actions\":[{\"type\":\"alarm.set\",\"time\":\"06:45\",\"label\":\"Wake up\","
                                                 "\"repeat\":\"weekdays\"}]}"));
         };
         s.run(2.0f);
         s.mark();  // 01 standby: the eyes alone on black
         s.tap(233, 330, 0.5f);
         s.mark();  // 02 a touch peeks: clock capsule over the aura
         s.run(4.6f);
         s.swipe(330, 240, 150, 240, 0.7f);
         s.mark();  // 03 launcher
         s.os.go(View::Notes);
         s.run(0.4f);
         s.tap(233, 360, 0.6f);
         s.type("buy figs for ana");
         s.run(0.3f);
         s.mark();  // 04 keyboard
         s.typeDone();
         s.os.go(View::Talk);
         s.run(0.6f);
         s.press(233, 260, 0.8f, 0.0f, true);  // 05 listening (ice)
         s.finger = false;
         s.run(0.3f);
         s.os.go(View::Home);
         s.run(0.5f);
         s.os.ask("wake me at 6:45 on weekdays");
         s.run(0.5f);
         s.mark();  // 06 thinking
         s.run(1.5f);
         s.mark();  // 07 the answer, mint
         s.os.go(View::Home);
         s.run(0.6f);
         s.claude.linked = true;
         s.claude.prompt = true;
         s.claude.tool = "Bash";
         s.claude.hint = "npm run build";
         s.os.setClaude(s.claude);
         s.brain.event(Ev::ClaudePrompt);
         s.run(1.0f);
         s.mark();  // 08 Claude needs you: amber capsule on the rim
         s.os.go(View::Claude);
         s.run(0.6f);
         s.mark();  // 09 the approval sheet
         s.claude.prompt = false;
         s.os.setClaude(s.claude);
         s.os.go(View::Home);
         s.run(5.5f);
         s.os.toast("Ana: dinner at 8? I'll bring figs", Rgb::hex(0xFFF0C8), 4.0f);
         s.run(0.6f);
         s.mark();  // 10 a notification capsule
         s.os.go(View::Alarms);
         s.run(0.6f);
         s.mark();  // 11 alarms
         s.tap(233, 376, 0.8f);
         s.mark();  // 12 the glass dial
         s.tap(233, 350, 0.6f);
         s.os.alarmDue(0);
         s.run(1.2f);
         s.mark();  // 13 ringing
         s.os.go(View::Timer);
         s.run(0.4f);
         s.tap(233, 200, 1.4f);
         s.mark();  // 14 timer
         s.os.stopTimer();
         s.os.go(View::Today);
         s.run(0.6f);
         s.mark();  // 15 today
         s.os.go(View::Settings);
         s.run(0.6f);
         s.mark();  // 16 settings
         s.os.go(View::AiMode);
         s.run(0.6f);
         s.mark();  // 17 AI
         s.os.go(View::About);
         s.run(0.6f);
         s.mark();  // 18 about
         s.os.go(View::Home);
         s.run(2.0f);
         s.mark();  // 19 back to the eyes alone
       }},
      {"glassboot", "SoulOS 5 Glass: first boot on glass", false,
       [](Sim& s) {
         s.run(2.2f);
         s.mark();
         s.tap(233, 250, 0.7f);
         s.mark();
         s.tap(233, 212, 0.7f);
         s.mark();
       }},
      // frame-cost benches (callgrind: --toggle-collect='suflet::FrameComposer::compose*', see BRINGUP.md §4)
      {"bench_standby", "Bench: standby, nobody touches it (10 s)", true, [](Sim& s) { s.run(10.0f); }},
      {"bench_screen", "Bench: Settings open, nobody touches it (10 s)", true,
       [](Sim& s) {
         s.os.go(View::Settings);
         s.run(10.0f);
       }},
      {"bench_typing", "Bench: typing on the round keyboard", true,
       [](Sim& s) {
         s.os.go(View::Notes);
         s.run(0.4f);
         s.tap(233, 360, 0.6f);
         s.type("the quick brown fox jumps over the lazy dog and then some more words");
         s.run(1.0f);
       }},
      {"bench_nav", "Bench: open and close screens every second (fades)", true,
       [](Sim& s) {
         for (int i = 0; i < 5; ++i) {
           s.os.go(i % 2 ? View::Alarms : View::Settings);
           s.run(1.0f);
           s.os.go(View::Home);
           s.run(1.0f);
         }
       }},
      {"motion", "Motion: level keeping, marble pupils, a spin (dizzy, ufff), double tap, a nod", true,
       [](Sim& s) {
         constexpr float D = 3.14159265f / 180;
         s.run(0.8f);
         s.label = "Turn it: the eyes stay level";
         s.move(50 * D, 0, 0, 0.7f, 0.5f);  // turned in the glass plane: the eyes stay level
         s.mark();
         s.move(-40 * D, 0, 0, 0.6f, 0.5f);
         s.move(0, 0, 0, 0.5f, 0.2f);
         s.label = "Spin it: dizzy";
         s.rollV = 13.0f;  // spun round: two turns a second ...
         s.rollFriction = 0.1f;
         s.run(1.5f);
         s.mark();  // dizzy: spiral pupils, the eyes give up keeping level
         s.rollFriction = 2.5f;  // ... then it slows down
         while (s.rollV != 0) s.step(true);
         const float back = roundf(s.roll / 6.2831853f) * 6.2831853f;
         s.label = "... ufff";
         s.move(back, 0, 0, 0.6f, 0.0f);  // it comes to rest upright ...
         s.roll = s.pRoll = 0;  // (same pose)
         s.run(0.9f);
         s.mark();  // ... ufff
         s.label = "Tip it: marble pupils";
         s.move(0, -35 * D, 12 * D, 0.5f, 0.4f);  // tipped back and to the side: marble pupils
         s.mark();
         s.label = "Double tap the case: yes?";
         s.caseTap();
         s.run(0.25f);
         s.caseTap();
         s.run(0.5f);
         s.mark();  // double tap: yes!
         s.label = "Nod: yes";
         for (int i = 0; i < 24; ++i) {  // a nod
           s.pitch = -35 * D + 18 * D * sinf(i / 30.0f * 6.2831853f * 2.2f);
           s.step(true);
         }
         s.move(0, 0, 0, 0.6f, 0.6f);
       }},
  };
}

// Keys: drive the device by hand. Live in a terminal (one key = one nudge), or
// from a string of keys (one key per frame, '.' = nothing), e.g.
//   program out keys "aaaaaaaa..........x..............................t.......t"
//   a/d turn left/right (in the glass plane)   w/s tip top toward you / away
//   q/e turn to its left/right (yaw)           x  flick: spin it
//   t   tap the case (twice = double tap)      n  nod yes     h  shake no
//   b   lay it on its back   f  face down      u  upside down r  upright, reset
//   c   held in a hand (tremor) on/off         Esc / Ctrl-D: quit (live)
static void keysMode(Sim& s, const char* script) {
  constexpr float D = 3.14159265f / 180;
  int nod = 0, shake = 0;
  float tr = 0, tp = 0, ty = 0;  // where the hand is taking it (the device eases there)
  auto key = [&](int c) {
    switch (tolower(c)) {
      case 'a': tr += 8 * D; break;
      case 'd': tr -= 8 * D; break;
      case 'w': tp += 8 * D; break;
      case 's': tp -= 8 * D; break;
      case 'q': ty -= 8 * D; break;
      case 'e': ty += 8 * D; break;
      case 'x':
        s.rollV = 16;
        s.rollFriction = 1.0f;
        break;
      case 't': s.caseTap(); break;
      case 'n': nod = 30; break;
      case 'h': shake = 30; break;
      case 'b': tp = -90 * D; break;
      case 'f': tp = 90 * D; break;
      case 'u': tr = 180 * D; tp = 0; break;
      case 'r':  // upright the short way round (a full turn reads the same)
        s.roll = s.pRoll = remainderf(s.roll, 6.2831853f);
        tr = tp = ty = 0;
        s.rollV = 0;
        break;
      case 'c': s.tremor = !s.tremor; break;
      default: break;
    }
  };
  int lastCues = 0;
  auto frame = [&](const char* script) {
    if (s.rollV != 0) {  // spinning: the hand follows wherever it stops
      tr = s.roll + s.rollV / kFps;
    } else {
      const float k = 1 - expf(-10.0f / kFps);
      s.roll += (tr - s.roll) * k;
      s.pitch += (tp - s.pitch) * k;
      s.yaw += (ty - s.yaw) * k;
    }
    const float wig = 18 * D * sinf((30 - (nod > 0 ? nod : shake)) / 30.0f * 6.2831853f * 2.2f);
    if (nod > 0) --nod;
    if (shake > 0) --shake;
    const float p0 = s.pitch, y0 = s.yaw;
    if (nod > 0) s.pitch += wig;
    if (shake > 0) s.yaw += wig;
    s.step(true);
    s.pitch = p0;
    s.yaw = y0;
    const eyes::MotionPose& p = s.os.face().motionPose();
    const int n = s.os.face().motionCueCount();
    if (script && n == lastCues) return;  // from a string: only what happened
    printf("\r roll %5.0f pitch %4.0f yaw %4.0f | eyes level %5.0f deg  pupils %+.2f %+.2f  dizzy %.2f  lid %.2f dim %.2f%s %-12s",
           s.roll / D, s.pitch / D, s.yaw / D, p.roll / D, p.px, p.py, p.dizzy, p.lid, p.dim, s.tremor ? " hand" : "",
           n != lastCues ? eyes::motionCueName(s.os.face().lastMotionCue()) : "");
    if (n != lastCues) printf("\n");
    lastCues = n;
    fflush(stdout);
  };
  if (script) {
    for (const char* c = script; *c; ++c) {
      if (*c != '.') key(*c);
      frame(script);
    }
    printf("\n");
    return;
  }
#ifdef SIM_TTY
  termios old{}, raw{};
  const bool tty = isatty(0) && tcgetattr(0, &old) == 0;
  if (tty) {
    raw = old;
    raw.c_lflag &= ~(ICANON | ECHO);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    tcsetattr(0, TCSANOW, &raw);
  }
  fprintf(stderr, "keys: a/d turn  w/s tip  q/e yaw  x spin  t tap  n nod  h shake  b back  f face down  u upside down  r reset  c hand  Esc quit\n");
  for (;;) {
    unsigned char c;
    bool quit = false;
    while (read(0, &c, 1) == 1) {
      if (c == 27 || c == 4) quit = true;
      else key(c);
    }
    if (quit || (!tty && feof(stdin))) break;
    frame(nullptr);
    usleep((useconds_t)(1e6f / kFps));
  }
  if (tty) tcsetattr(0, TCSANOW, &old);
  printf("\n");
#else
  fprintf(stderr, "keys: live mode needs a terminal; pass a key string\n");
#endif
}


// ------------------------------------------------------------- cloud mode ---
// `program <out_dir> cloud <base> [key_file] [record 0|1]`: this simulated SOUL
// talks to a real SOUL Cloud (a loopback test server) with the device's own
// protocol code (CloudDriver / CloudSession / CloudLink / DeviceKey) over a
// small host WebSocket client (sim/sim_cloud.cpp). SoulOS applies what comes
// and draws it. Lines on stdin drive it like a finger would; lines on stdout
// say what the glass shows (for tools/e2e_sim.py and humans):
//   in:  ask <text> | tap yes | tap no | accept | reject | note <text> | inbox <text> | pause | resume | state |
//        ai bridge | ai none (Settings > AI on the glass) | bridge code | bridge forget | quit
//   out: DEVICE, AUTH, WELCOME, PAIRING, CONFIRM, PAIRED, UNPAIRED, PUSH, REPLY, CONFIG, TZ, SENT, STATE,
//        BRIDGECODE, BRIDGE, ASKSTATE (SOUL Bridge through SOUL Cloud, docs/08 §4), POLLMODE, BYE
uint32_t simMs() {
  using namespace std::chrono;
  return (uint32_t)duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

// UTC epoch -> "local epoch" (local wall time counted as UTC, like the device's RTC) for the current TZ
uint32_t localFromUtc(uint32_t epoch) {
  const time_t t = (time_t)epoch;
  struct tm lt;
  localtime_r(&t, &lt);
  return (uint32_t)((int64_t)epoch + lt.tm_gmtoff);
}

int cloudMode(const std::string& dir, const std::string& base, const std::string& keyPath, bool record) {
  Recorder rec;
  if (record) {
    rec.dir = dir;
    rec.name = "cloud-live";
    rec.open();
  }
  Sim s(true);
  if (record) s.rec = &rec;
  s.os.settings().ai = (uint8_t)AiMode::Cloud;
  s.net.relay = true;
  s.net.keyClaude = false;
  s.os.setNet(s.net);
  setenv("TZ", "EET-2EEST,M3.5.0/3,M10.5.0/4", 1);
  tzset();
  s.clock = localFromUtc((uint32_t)time(nullptr));
  HostCloud hc;
  hc.base = base;
  hc.allowPlainWs = true;  // loopback test cloud only
  hc.deviceId = CloudLink::deviceId(gMac);
  hc.fw = "1.5.0-sim";
  hc.hw = "lcd28";
  hc.session.prefs.fw = hc.fw;
  hc.session.prefs.hw = hc.hw;
  hc.session.prefs.lang = "en";
  hc.session.prefs.brainLocal = "cloud";
  hc.session.prefs.tzPosix = "EET-2EEST,M3.5.0/3,M10.5.0/4";
  hc.session.rng = []() {
    static uint32_t x = (uint32_t)simMs() * 2654435761u ^ 0x5eed;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return x;
  };
  hc.verbose = getenv("SIM_VERBOSE") != nullptr;
  hc.noWs = getenv("SIM_NO_WS") != nullptr;
  if (!hc.loadOrMakeKey(keyPath)) {
    printf("FAIL no device key\n");
    return 1;
  }
  printf("DEVICE %s pub=%s\n", hc.deviceId.c_str(), hc.pub().c_str());
  s.cloudAsk = [&](const AiJob& j) {
    const int left = s.os.timerLeft();
    return hc.session.ask(j.text, s.os.ro(), left >= 0 ? (left + 59) / 60 : -1, simMs(),
                          s.os.aiMode() == AiMode::Bridge);  // brain "bridge": the cloud hands it to the computer
  };
  std::string bridgeCode, bridgeLine;
  int askState = 0;
  bool pollMode = false;
  const int fl = fcntl(0, F_GETFL, 0);
  fcntl(0, F_SETFL, fl | O_NONBLOCK);
  std::string line;
  bool welcomed = false, paired = false, quit = false;
  std::string code, pid, state;
  bool hadToken = false;
  CloudDriver::Problem problem = CloudDriver::Problem::None;
  const uint32_t start = simMs();
  while (!quit) {
    const uint32_t t0 = simMs();
    hc.step(t0, (float)(rand() % 1000) / 1000.0f);
    if (hc.haveToken() && !hadToken) printf("AUTH ok state=%s\n", hc.session.state.empty() ? "?" : hc.session.state.c_str());
    hadToken = hc.haveToken();
    if (hc.problem != problem) {
      problem = hc.problem;
      printf("AUTH problem=%d\n", (int)problem);
    }
    // what the device's render loop does with the session (src/main.cpp)
    NetInfo ni = s.net;
    hc.session.fill(ni);
    ni.cloudProblem = (int)hc.problem;
    ni.cloudHost = CloudLink::hostOf(base);
    s.os.setNet(ni);
    if (hc.session.welcomed() != welcomed) {
      welcomed = hc.session.welcomed();
      if (welcomed) printf("WELCOME state=%s owner=%s trial=%d\n", hc.session.state.c_str(), hc.session.owner.c_str(),
                           hc.session.trialLeft);
    }
    if (ni.pairCode != code) {
      code = ni.pairCode;
      if (!code.empty()) {
        printf("PAIRING code=%s url=%s\n", code.c_str(), ni.pairUrl.c_str());
        s.mark();
      }
    }
    if (ni.confirmPid != pid) {
      pid = ni.confirmPid;
      if (!pid.empty()) {
        printf("CONFIRM pid=%s name=%s hint=%s view=%s\n", pid.c_str(), ni.confirmName.c_str(), ni.confirmHint.c_str(),
               viewName(s.os.view()));
        s.mark();
      }
    }
    if (ni.paired != paired) {
      paired = ni.paired;
      printf(paired ? "PAIRED owner=%s\n" : "UNPAIRED%s\n", paired ? ni.owner.c_str() : "");
    }
    if (ni.bridgeCode != bridgeCode) {
      bridgeCode = ni.bridgeCode;
      if (!bridgeCode.empty()) {
        printf("BRIDGECODE code=%s cmd=%s view=%s\n", bridgeCode.c_str(), ni.bridgeCmd.c_str(), viewName(s.os.view()));
        s.mark();
      }
    }
    {
      char bl[160];
      snprintf(bl, sizeof bl, "BRIDGE paired=%d online=%d name=%s", ni.bridgePaired, ni.bridgeOnline, ni.bridgeName.c_str());
      if (bl != bridgeLine && (ni.bridgePaired || ni.bridgeOnline || !bridgeLine.empty())) {
        bridgeLine = bl;
        printf("%s\n", bl);
        if (ni.bridgeOnline) s.mark();
      }
    }
    if (ni.askState != askState) {
      askState = ni.askState;
      printf("ASKSTATE %s face=%d\n", askState == 1 ? "waiting" : askState == 2 ? "thinking" : "none",
             (int)s.os.faceInputs(s.brain).state);
      if (askState) s.mark();
    }
    if (hc.pollMode() != pollMode) {
      pollMode = hc.pollMode();
      printf("POLLMODE %d\n", pollMode);
    }
    AiOutcome out;
    if (hc.session.pollAnswer(out)) {
      s.os.aiResult(out);
      printf("REPLY err=%s note=%s say=%s\n", out.err == AiErr::None ? "none" : aiErrCode(out.err),
             out.note == AiErr::None ? "none" : aiErrCode(out.note), s.os.lastReply().say.c_str());
    }
    CloudPush p;
    while (hc.session.pollPush(p)) {
      std::string err;
      const bool ok = s.os.cloudPush(p, err);
      hc.session.ackPush(p.seq, ok, ok ? nullptr : err.c_str());
      printf("PUSH seq=%u action=%s from=%s/%s item=%s %s%s view=%s alarms=%d reminders=%d notes=%d\n", (unsigned)p.seq,
             p.action.c_str(), p.source.c_str(), p.app.c_str(), p.itemId.c_str(), ok ? "applied" : "refused:",
             ok ? "" : err.c_str(), viewName(s.os.view()), s.alarms.count(), (int)s.os.reminders().size(),
             (int)s.os.notes().size());
      s.mark();
    }
    CloudOut co;
    while (s.os.popCloudOut(co)) {
      hc.session.send(co, s.clock, (uint32_t)time(nullptr));
      static const char* const kK[] = {"item.add", "inbox.add", "item.state", "pair.ok", "pair.no", "connectors",
                                       "bridge.code.get", "bridge.forget", "brain"};
      printf("SENT %s%s%s\n", kK[co.kind], co.state.empty() ? "" : " ", co.state.c_str());
    }
    CloudConfig cc;
    if (hc.session.pollConfig(cc)) {
      s.os.cloudConfig(cc.hasBrain ? cc.brain : "", cc.hasLang ? cc.lang : "", cc.hasName ? cc.name : "");
      printf("CONFIG brain=%s lang=%s models=%s,%s\n", cc.hasBrain ? cc.brain.c_str() : "-", cc.hasLang ? cc.lang.c_str() : "-",
             cc.modelClaude.c_str(), cc.modelOpenai.c_str());
    }
    std::string tz;
    if (hc.session.pollTz(tz)) {  // the cloud's zone wins: the device would netSetTz()
      setenv("TZ", tz.c_str(), 1);
      tzset();
      s.clock = localFromUtc((uint32_t)time(nullptr));
      printf("TZ %s\n", tz.c_str());
    }
    uint32_t epoch;
    if (hc.session.pollTime(epoch)) s.clock = localFromUtc(epoch);
    // a finger on stdin
    char buf[512];
    ssize_t n;
    while ((n = read(0, buf, sizeof buf)) > 0) line.append(buf, (size_t)n);
    if (n == 0 && line.empty() && !isatty(0)) {
      // stdin closed: keep running until `quit` arrives or 10 minutes pass
    }
    size_t nl;
    while ((nl = line.find('\n')) != std::string::npos) {
      std::string cmd = line.substr(0, nl);
      line.erase(0, nl + 1);
      while (!cmd.empty() && (cmd.back() == '\r' || cmd.back() == ' ')) cmd.pop_back();
      if (cmd == "quit") {
        quit = true;
      } else if (cmd.compare(0, 4, "ask ") == 0) {
        s.os.ask(cmd.substr(4));  // as if typed on the round keyboard
        printf("ASKED %s\n", cmd.substr(4).c_str());
      } else if (cmd == "tap yes" || cmd == "tap no") {  // the buttons of "Pair with Ana?"
        printf("TAP %s on view=%s\n", cmd.c_str() + 4, viewName(s.os.view()));
        s.tap(cmd == "tap yes" ? 160 : 306, 372, 0.2f);
      } else if (cmd == "accept" || cmd == "reject") {  // a connector night alarm card
        s.tap(cmd == "accept" ? 160 : 306, 392, 0.2f);
      } else if (cmd.compare(0, 5, "note ") == 0) {  // a note made on SOUL (offline rules / keyboard)
        AiAction a;
        a.type = AiAction::NoteCreate;
        a.text = cmd.substr(5);
        std::vector<std::string> chips;
        s.os.runActions(std::vector<AiAction>(1, a), &chips);
      } else if (cmd.compare(0, 6, "inbox ") == 0) {  // "Ask my Claude"
        CloudOut o;
        o.kind = CloudOut::Inbox;
        o.text = cmd.substr(6);
        hc.session.send(o, s.clock, (uint32_t)time(nullptr));
        printf("SENT inbox.add\n");
      } else if (cmd == "pause" || cmd == "resume") {
        CloudOut o;
        o.kind = CloudOut::Connectors;
        o.paused = cmd == "pause";
        hc.session.send(o, s.clock, 0);
        printf("SENT connectors %s\n", cmd.c_str());
      } else if (cmd == "ai bridge" || cmd == "ai none") {  // Settings > AI, on the glass
        s.os.go(View::AiMode);
        s.step(false);
        s.tap(233, cmd == "ai bridge" ? 126 + 3 * 52 : 126 + 4 * 52, 0.2f);
        printf("AI mode=%s view=%s\n", aiModeName(s.os.aiMode()), viewName(s.os.view()));
      } else if (cmd == "bridge code") {  // "New code" on the Bridge screen
        if (s.os.view() != View::Bridge) s.os.go(View::Bridge);
        s.step(false);
        s.tap(160, 392, 0.2f);
      } else if (cmd == "bridge forget") {
        if (s.os.view() != View::Bridge) s.os.go(View::Bridge);
        s.step(false);
        s.tap(306, 392, 0.2f);
      } else if (cmd == "state") {
        printf("STATE state=%s view=%s seq=%u alarms=%d reminders=%d notes=%d outq=%u in=%d out=%d ai=%s\n",
               hc.session.state.c_str(), viewName(s.os.view()), (unsigned)hc.session.lastSeq, s.alarms.count(),
               (int)s.os.reminders().size(), (int)s.os.notes().size(), (unsigned)hc.session.outqSize(), hc.framesIn,
               hc.framesOut, aiModeName(s.os.aiMode()));
      } else if (!cmd.empty()) {
        printf("? %s\n", cmd.c_str());
      }
    }
    s.step(record);
    if (simMs() - start > 600000) quit = true;
    const uint32_t spent = simMs() - t0;
    if (spent < 33) usleep((useconds_t)(33 - spent) * 1000);
  }
  if (record) {
    rec.close("SOUL Cloud, live: the simulator paired with a real local cloud");
    printf("RECORD %d frames -> %s/cloud-live.rgb\n", rec.frames, dir.c_str());
  }
  printf("BYE in=%d out=%d seq=%u\n", hc.framesIn, hc.framesOut, (unsigned)hc.session.lastSeq);
  hc.wsClose();
  return 0;
}
// ------------------------------------------------------------------ LAN mode ---
// `program <out_dir> lan [port]`: SOUL Bridge on the home network (docs/08 §4) with the firmware's own
// BridgeServer (lib/Suflet/src/BridgeLink.*) behind a loopback WebSocket server (sim/sim_lan.cpp), as the device
// serves ws://soul-xxxx.local:8765/bridge. The brain is "My Claude on my computer"; SoulOS shows the code, the
// computer, the eyes, and applies the actions an answer carries.
//   in:  ai bridge | code | ask <text> | forget | state | quit
//   out: LAN port=, LANCODE code=, BRIDGE online= name=, ASKSTATE, REPLY err= say=, STATE ..., BYE
int lanMode(const std::string& dir, int port) {
  (void)dir;
  Sim s(true);
  s.os.settings().ai = (uint8_t)AiMode::None;
  s.net.ip = "127.0.0.1";
  s.os.setNet(s.net);
  setenv("TZ", "EET-2EEST,M3.5.0/3,M10.5.0/4", 1);
  tzset();
  s.clock = localFromUtc((uint32_t)time(nullptr));
  HostWsServer ws;
  if (!ws.listen(port)) {
    printf("FAIL cannot listen on 127.0.0.1:%d\n", port);
    return 1;
  }
  BridgeServer b;
  b.deviceId = CloudLink::deviceId(gMac);
  b.name = s.os.settings().name;
  b.tz = "EET-2EEST,M3.5.0/3,M10.5.0/4";
  b.rng = []() {
    uint32_t r;
    RAND_bytes((unsigned char*)&r, sizeof r);
    return r;
  };
  s.onCmd = [&](OsCmd c) {
    if (c == OsCmd::BridgePair) b.newCode(simMs());
    if (c == OsCmd::BridgeForget) b.forget();
  };
  s.cloudAsk = [&](const AiJob& j) {
    char now[48];
    const time_t t = (time_t)s.clock;
    struct tm tm;
    gmtime_r(&t, &tm);
    snprintf(now, sizeof now, "%04d-%02d-%02dT%02d:%02d", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min);
    return b.ask(j.text, s.os.ro(), now, simMs());
  };
  printf("LAN port=%d device=%s\n", ws.port(), b.deviceId.c_str());
  const int fl = fcntl(0, F_GETFL, 0);
  fcntl(0, F_SETFL, fl | O_NONBLOCK);
  std::string line, code, bridgeLine;
  int askState = 0;
  bool quit = false;
  const uint32_t start = simMs();
  while (!quit) {
    const uint32_t t0 = simMs();
    ws.poll(5, [&](int fd) { b.onOpen(fd, simMs()); },
            [&](int fd, const std::string& t) { b.onText(fd, t.data(), t.size(), simMs()); },
            [&](int fd) { b.onClose(fd); });
    b.tick(simMs());
    BridgeOut o;
    while (b.nextOut(o)) {
      if (o.close) ws.close(o.conn);
      else ws.send(o.conn, o.frame);
    }
    NetInfo ni = s.net;
    ni.bridgeLan = true;
    ni.bridgeOnline = b.online();
    ni.bridgeName = b.computer();
    ni.bridgePaired = b.tokenCount() > 0;
    ni.askState = b.askState();
    const std::string c = b.code(simMs());
    if (!c.empty()) {
      ni.bridgeCode = c;
      ni.bridgeCmd = "soul-bridge pair " + c;
    }
    s.os.setNet(ni);
    if (c != code) {
      code = c;
      if (!code.empty()) printf("LANCODE code=%s view=%s\n", code.c_str(), viewName(s.os.view()));
    }
    char bl[160];
    snprintf(bl, sizeof bl, "BRIDGE online=%d name=%s tokens=%d", ni.bridgeOnline, ni.bridgeName.c_str(), (int)b.tokenCount());
    if (bl != bridgeLine) {
      bridgeLine = bl;
      printf("%s\n", bl);
    }
    if (ni.askState != askState) {
      askState = ni.askState;
      printf("ASKSTATE %s face=%d\n", askState == 1 ? "waiting" : askState == 2 ? "thinking" : "none",
             (int)s.os.faceInputs(s.brain).state);
    }
    AiOutcome out;
    if (b.pollAnswer(out)) {
      s.os.aiResult(out);
      printf("REPLY err=%s say=%s alarms=%d notes=%d\n", out.err == AiErr::None ? "none" : aiErrCode(out.err),
             s.os.lastReply().say.c_str(), s.alarms.count(), (int)s.os.notes().size());
    }
    char buf[512];
    ssize_t n;
    while ((n = read(0, buf, sizeof buf)) > 0) line.append(buf, (size_t)n);
    size_t nl;
    while ((nl = line.find('\n')) != std::string::npos) {
      std::string cmd = line.substr(0, nl);
      line.erase(0, nl + 1);
      while (!cmd.empty() && (cmd.back() == '\r' || cmd.back() == ' ')) cmd.pop_back();
      if (cmd == "quit") {
        quit = true;
      } else if (cmd == "ai bridge") {
        s.os.go(View::AiMode);
        s.step(false);
        s.tap(233, 126 + 3 * 52, 0.2f);
        printf("AI mode=%s view=%s\n", aiModeName(s.os.aiMode()), viewName(s.os.view()));
      } else if (cmd == "code") {
        if (s.os.view() != View::Bridge) s.os.go(View::Bridge);
        s.step(false);
        s.tap(160, 392, 0.2f);
      } else if (cmd == "forget") {
        if (s.os.view() != View::Bridge) s.os.go(View::Bridge);
        s.step(false);
        s.tap(306, 392, 0.2f);
      } else if (cmd.compare(0, 4, "ask ") == 0) {
        s.os.ask(cmd.substr(4));
        printf("ASKED %s err=%s\n", cmd.substr(4).c_str(), s.os.thinking() ? "-" : aiErrCode(s.os.lastError()));
      } else if (cmd == "state") {
        printf("STATE ai=%s view=%s alarms=%d notes=%d online=%d\n", aiModeName(s.os.aiMode()), viewName(s.os.view()),
               s.alarms.count(), (int)s.os.notes().size(), b.online());
      } else if (!cmd.empty()) {
        printf("? %s\n", cmd.c_str());
      }
    }
    s.step(false);
    if (simMs() - start > 600000) quit = true;
    const uint32_t spent = simMs() - t0;
    if (spent < 33) usleep((useconds_t)(33 - spent) * 1000);
  }
  printf("BYE\n");
  return 0;
}
}  // namespace

int main(int argc, char** argv) {
  setvbuf(stdout, nullptr, _IOLBF, 0);  // cloud mode is driven line by line through a pipe
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
  if (which == "cloud") {  // a live SOUL Cloud (see cloudMode)
    if (argc < 4) {
      fprintf(stderr, "usage: %s <out_dir> cloud <http://127.0.0.1:port> [key_file] [record 0|1]\n", argv[0]);
      return 2;
    }
    return cloudMode(dir, argv[3], argc > 4 ? argv[4] : "", argc > 5 && atoi(argv[5]) != 0);
  }
  if (which == "lan") return lanMode(dir, argc > 3 ? atoi(argv[3]) : 0);  // SOUL Bridge on the LAN (see lanMode)
  if (which == "keys") {  // drive it by hand (see keysMode)
    Recorder rec;
    rec.dir = dir;
    rec.name = "keys";
    rec.open();
    Sim s(true);
    s.rec = &rec;
    keysMode(s, argc > 3 && strlen(argv[3]) != 12 ? argv[3] : nullptr);
    rec.extra = ",\"pose\":[" + s.poseJson + "]";
    rec.close("Keys: the device driven by hand");
    printf("keys: %d frames -> %s/keys.rgb\n", rec.frames, dir.c_str());
    return 0;
  }
  for (const Scenario& sc : scenarios()) {
    if (which != "all" && which != sc.name) continue;
    Recorder rec;
    rec.dir = dir;
    rec.name = sc.name;
    rec.open();
    Sim s(sc.booted);
    s.rec = &rec;
    sc.script(s);
    rec.extra = ",\"pose\":[" + s.poseJson + "]";
    rec.close(sc.caption);
    static uint32_t rebuilt = 0;
    printf("%-12s %4d frames  compose %.2f ms/frame on this PC, %.0f%% of the glass changed per frame, %u aura builds  %s\n",
           sc.name, rec.frames, s.composeMs / (s.composed ? s.composed : 1),
           100.0 * s.changedPx / ((double)W * H * (s.composed ? s.composed : 1)), (unsigned)(glass().rebuilds - rebuilt), sc.caption);
    rebuilt = glass().rebuilds;
  }
  return 0;
}
