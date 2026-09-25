// Native simulator: runs the exact firmware "soul" (lib/Suflet) on the PC,
// drives it with scripted sensor events and writes the frames it draws.
//
//   ./suflet_sim <out_dir> [scenario] [seed] [466|480]
//
// The last argument picks the display: 466 (AMOLED, default) or 480 (the
// 2.8" IPS "SOUL M"); scene coordinates are design pixels scaled to it.
// Each scenario writes <out_dir>/<name>.rgb (raw RGB888 frames, W x H)
// plus <name>.json (frame count, fps, body-light per frame, marked stills).
// The Python script tools/frames_to_media.py turns them into GIF/MP4/contact
// sheets, or PNG stills (--png). The soulos_* scenes drive the SoulOS Shell
// (keyboard, time picker) with simulated finger touches at screen points.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

#include "Brain.h"
#include "ClaudeLink.h"
#include "Face.h"
#include "Geometry.h"
#include "Gestures.h"
#include "Personality.h"
#include "Shell.h"

using namespace suflet;

namespace {

DisplayGeometry gGeom;  // set from argv before any scene runs
int W = 466, H = 466;
// design pixels (466 px disc) -> this display
inline float P(float designPx) { return gGeom.s(designPx); }
constexpr float kFps = 30.0f;

struct Recorder {
  std::string dir, name;
  FILE* f = nullptr;
  int frames = 0;
  std::string bodyJson;
  std::vector<int> stills;
  std::vector<uint16_t> fb = std::vector<uint16_t>(W * H);
  Canvas cv{W, H, fb.data()};

  void open() {
    f = fopen((dir + "/" + name + ".rgb").c_str(), "wb");
    if (!f) {
      perror("open");
      exit(1);
    }
  }
  void frame(const Brain& b, Shell* shell) {
    cv.fill(pal::kBlack);
    Face face = b.face();
    if (shell) {
      shell->render(cv, Rect{0, 0, W, H});
      shell->adjustFace(face);
      renderFace(cv, face, shell->faceLayout());
    } else {
      renderFace(cv, face);
    }
    static std::vector<uint8_t> rgb(W * H * 3);
    for (int i = 0; i < W * H; ++i) {
      const Rgb p = Rgb::from565(fb[i]);
      rgb[i * 3] = p.r;
      rgb[i * 3 + 1] = p.g;
      rgb[i * 3 + 2] = p.b;
    }
    fwrite(rgb.data(), 1, rgb.size(), f);
    const BodyLight bl = b.body();
    char buf[96];
    snprintf(buf, sizeof buf, "%s[%d,%d,%d,%.3f]", frames ? "," : "", bl.color.r, bl.color.g,
             bl.color.b, bl.level);
    bodyJson += buf;
    ++frames;
  }
  void close(const char* caption) {
    fclose(f);
    std::string st;
    for (size_t i = 0; i < stills.size(); ++i) st += (i ? "," : "") + std::to_string(stills[i]);
    FILE* j = fopen((dir + "/" + name + ".json").c_str(), "wb");
    fprintf(j, "{\"name\":\"%s\",\"w\":%d,\"h\":%d,\"fps\":%.0f,\"frames\":%d,\"caption\":\"%s\",\"stills\":[%s],\"body\":[%s]}\n",
            name.c_str(), W, H, kFps, frames, caption, st.c_str(), bodyJson.c_str());
    fclose(j);
    printf("%-18s %4d frames  %s\n", name.c_str(), frames, caption);
  }
};

// A tiny scripting layer: advance time, fire events, keep sensors in a state.
struct Sim {
  Brain brain;
  ClaudeLink claude;
  Inputs in;
  Recorder* rec = nullptr;
  float still = 0;
  bool moving = false;
  // SoulOS: the screen router, fed by a simulated finger
  Alarms alarms;
  Shell shell{&alarms};
  TouchGestures touch;
  bool useShell = false, finger = false;
  float fx = P(233), fy = P(233);
  uint32_t clock = 1790374680u;  // 2026-09-25 22:18 local
  float clockFrac = 0;
  explicit Sim(uint64_t seed) : brain(Personality::fromSeed(seed), seed * 7 + 1) {
    in.hour = 14.5f;
    shell.setGeometry(gGeom);
  }
  void step(bool render) {
    const float dt = 1.0f / kFps;
    still = moving ? 0 : still + dt;
    in.stillFor = still;
    clockFrac += dt;
    while (clockFrac >= 1.0f) {
      clockFrac -= 1.0f;
      ++clock;
    }
    if (useShell) {
      touch.update(finger, fx, fy, dt);
      TouchEv te;
      while (touch.poll(te))
        if (!shell.event(te)) brain.event(te.e);
      touch.setMode(shell.wantsTextTouch() ? TouchMode::Text : TouchMode::Face);
      shell.update(dt, clock);
      Ev se;
      while (shell.poll(se)) brain.event(se);
    }
    brain.update(dt, in);
    Cue c;
    while (brain.popCue(c)) {
      if (c == Cue::ClaudeApprove || c == Cue::ClaudeDeny) claude.decide(c == Cue::ClaudeApprove);
    }
    std::string line;
    while (claude.popOutgoing(line)) {
    }
    Ev e;
    while (claude.poll(e)) brain.event(e);
    if (render && rec) rec->frame(brain, useShell ? &shell : nullptr);
  }
  void run(float seconds, bool render = true) {
    const int n = (int)(seconds * kFps + 0.5f);
    for (int i = 0; i < n; ++i) step(render);
  }
  // fast-forward without rendering (for long waits)
  void skip(float seconds) { run(seconds, false); }
  void ev(Ev e) { brain.event(e); }
  void feed(const char* json) {
    claude.feed((const uint8_t*)json, strlen(json));
    claude.feed((const uint8_t*)"\n", 1);
  }
  // mark the last rendered frame as a still for --png
  void mark() {
    if (rec && rec->frames) rec->stills.push_back(rec->frames - 1);
  }
  // a finger: press at (x, y) for `holdS`, then lift and wait `gapS`
  void press(float x, float y, float holdS, float gapS, bool markWhileDown = false) {
    fx = x;
    fy = y;
    finger = true;
    run(holdS);
    if (markWhileDown) mark();
    finger = false;
    run(gapS);
  }
  void drag(float x0, float y0, float x1, float y1, float seconds) {
    const int n = (int)(seconds * kFps + 0.5f);
    finger = true;
    for (int i = 0; i <= n; ++i) {
      const float t = n ? (float)i / n : 1.0f;
      fx = x0 + (x1 - x0) * t;
      fy = y0 + (y1 - y0) * t;
      step(true);
    }
  }
  void lift(float gapS) {
    finger = false;
    run(gapS);
  }
  // type with fast, human-ish taps (~5 keys/s), marking the key named `markCp`
  void type(const char* text, uint32_t markCp = 0) {
    const char* p = text;
    while (*p) {
      const uint32_t cp = utf8::next(p);
      float x, y;
      if (!shell.keyboard().keyCenter(cp, x, y)) continue;
      press(x + 2, y + 3, 0.1f, 0.067f, cp == markCp);
    }
  }
};

struct Scenario {
  const char* name;
  const char* caption;
  std::function<void(Sim&)> script;
};

std::vector<Scenario> scenarios() {
  return {
      {"idle", "Alive on its own: breathes, blinks, glances around",
       [](Sim& s) { s.run(9.0f); }},
      {"boop", "Tap = boop. Double tap = laugh. Too many taps = shy",
       [](Sim& s) {
         s.run(0.8f);
         s.ev(Ev::Tap);
         s.run(1.8f);
         s.ev(Ev::DoubleTap);
         s.run(2.2f);
         for (int i = 0; i < 5; ++i) {
           s.ev(Ev::Tap);
           s.run(0.35f);
         }
         s.run(3.0f);
       }},
      {"purr", "Stroke the stone and it purrs",
       [](Sim& s) {
         s.run(0.6f);
         s.ev(Ev::StrokeStart);
         s.run(3.5f);
         s.ev(Ev::StrokeEnd);
         s.run(1.8f);
       }},
      {"dizzy", "Shake it: dizzy, then it sulks for a bit",
       [](Sim& s) {
         s.run(0.6f);
         s.moving = true;
         s.ev(Ev::Shake);
         s.run(0.6f);
         s.moving = false;
         s.run(3.2f);
         s.ev(Ev::Tap);
         s.run(2.0f);
       }},
      {"sleep", "Leave it still: it gets drowsy and falls asleep",
       [](Sim& s) {
         s.run(1.0f);
         s.skip(s.brain.personality().sleepAfterSeconds() - 2.0f);
         s.run(9.0f);
       }},
      {"missed_you", "Pick it up after 8 hours: it wakes up and missed you",
       [](Sim& s) {
         s.skip(70.0f);  // asleep
         s.run(1.0f);
         s.brain.setAbsence(8.0f);
         s.moving = true;
         s.ev(Ev::PickUp);
         s.run(0.4f);
         s.moving = false;
         s.run(5.6f);
       }},
      {"rare", "Rare moments: sneeze, hiccups, heart eyes, birthday",
       [](Sim& s) {
         s.run(0.5f);
         s.brain.trigger(Reaction::Sneeze);
         s.run(2.2f);
         s.brain.trigger(Reaction::Hiccup);
         s.run(2.8f);
         s.brain.trigger(Reaction::Love);
         s.run(3.0f);
         s.brain.trigger(Reaction::Birthday);
         s.run(4.6f);
       }},
      {"ai_talk", "Hold to talk: it listens, thinks, answers with feeling",
       [](Sim& s) {
         s.brain.setAiLink(true);
         s.run(0.6f);
         s.ev(Ev::HoldStart);
         for (int i = 0; i < 75; ++i) {  // 2.5 s of speech
           const float t = i / kFps;
           s.in.audioLevel = 0.5f + 0.45f * std::sin(t * 17.0f) * std::sin(t * 3.1f);
           s.step(true);
         }
         s.in.audioLevel = 0;
         s.ev(Ev::HoldEnd);
         s.run(1.3f);
         s.brain.setTone(Tone::Happy);
         s.ev(Ev::AiSpeakStart);
         for (int i = 0; i < 90; ++i) {
           const float t = i / kFps;
           s.in.audioLevel = 0.35f + 0.35f * std::fabs(std::sin(t * 11.0f)) * (0.6f + 0.4f * std::sin(t * 2.3f));
           s.step(true);
         }
         s.in.audioLevel = 0;
         s.ev(Ev::AiSpeakEnd);
         s.run(1.2f);
       }},
      {"claude_buddy", "Works with Claude: busy while Claude works, asks you to approve",
       [](Sim& s) {
         s.feed("{\"time\":[1790246400,10800]}");
         s.feed("{\"cmd\":\"owner\",\"name\":\"Andu\"}");
         s.run(0.8f);
         s.feed("{\"total\":1,\"running\":1,\"waiting\":0,\"msg\":\"writing code\",\"tokens\":12000,\"tokens_today\":12000}");
         s.run(3.0f);
         s.feed("{\"total\":1,\"running\":0,\"waiting\":1,\"msg\":\"approve: Bash\",\"tokens\":14000,\"tokens_today\":14000,"
                "\"prompt\":{\"id\":\"req_1\",\"tool\":\"Bash\",\"hint\":\"npm test\"}}");
         s.run(2.2f);
         s.ev(Ev::HoldStart);  // hold to approve
         s.run(1.5f);
         s.ev(Ev::HoldEnd);
         s.run(0.3f);
         s.feed("{\"total\":1,\"running\":1,\"waiting\":0,\"msg\":\"running tests\",\"tokens\":52000,\"tokens_today\":52000}");
         s.run(3.5f);
         s.feed("{\"total\":1,\"running\":0,\"waiting\":0,\"msg\":\"done\",\"tokens\":52400,\"tokens_today\":52400}");
         s.run(2.0f);
       }},
      {"keyboard", "SoulOS: long-press the face, type Hello on the round keyboard, save the note",
       [](Sim& s) {
         s.useShell = true;
         s.run(0.6f);
         s.press(P(233), P(250), 0.75f, 0.6f);  // long press: the note field opens
         s.mark();                          // empty field + context chips
         s.type("Hell");
         s.type("o", 'o');                  // the key callout while pressed
         s.run(0.5f);
         s.mark();                          // "Hello" + suggestions
         float x, y;
         s.shell.keyboard().keyCenter((uint32_t)' ', x, y);
         s.press(x, y, 0.1f, 0.3f);
         s.shell.keyboard().keyCenter((uint32_t)'a', x, y);
         s.press(x, y, 0.7f, 0.0f, true);  // long-press a: the variant tray
         s.finger = true;
         s.fx = x + P(44);  // slide to the next variant
         s.run(0.2f);
         s.mark();
         s.lift(0.4f);
         s.shell.keyboard().keyCenter(KeyId::Bksp, x, y);
         s.press(x, y, 0.1f, 0.3f);
         s.shell.keyboard().keyCenter(KeyId::Bksp, x, y);
         s.press(x, y, 0.1f, 0.3f);  // back to "Hello"
         s.mark();
         s.shell.keyboard().keyCenter(KeyId::Done, x, y);
         s.press(x, y, 0.1f, 1.4f);  // done: the note is saved, eyes celebrate
         s.mark();
       }},
      {"timepicker", "SoulOS: Rim-Dial time picker, drag the hour ring then the minutes to 07:30",
       [](Sim& s) {
         s.useShell = true;
         s.shell.openTimePicker(23, 0);  // next whole hour
         s.run(0.6f);
         s.mark();
         // drag on the rim from 23 h round to 7 h (bottom-left)
         for (int i = 0; i <= 24; ++i) {
           const float a = TimePicker::hourAngle(23) - (360.0f - 8 * 15.0f) * i / 24.0f;
           s.fx = P(233) + P(205) * cosf(a * 3.14159265f / 180);
           s.fy = P(233) + P(205) * sinf(a * 3.14159265f / 180);
           s.finger = true;
           s.step(true);
         }
         s.run(0.2f);
         s.mark();  // hours, knob on 07
         s.lift(0.7f);
         s.mark();  // switched to minutes
         for (int i = 0; i <= 90; ++i) {  // slow drag (60°/s): 1-minute steps
           const float a = TimePicker::minuteAngle(0) + 180.0f * i / 90.0f;
           s.fx = P(233) + P(200) * cosf(a * 3.14159265f / 180);
           s.fy = P(233) + P(200) * sinf(a * 3.14159265f / 180);
           s.finger = true;
           s.step(true);
         }
         s.run(0.2f);
         s.mark();  // 07:30, "rings in 9 h 12 min"
         s.lift(0.5f);
         s.press(P(233), P(350), 0.1f, 1.2f);  // ✓
         s.mark();
       }},
      {"night", "At night: warm amber eyes, sleepy, a night light",
       [](Sim& s) {
         s.in.hour = 23.2f;
         s.skip(120.0f);  // mood settles to night energy
         s.moving = true;
         s.skip(0.1f);
         s.moving = false;
         s.run(3.0f);
         s.brain.trigger(Reaction::Yawn);
         s.run(3.0f);
         s.skip(8.0f);
         s.run(4.0f);
       }},
  };
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <out_dir> [scenario|all] [seed] [466|480]\n", argv[0]);
    return 2;
  }
  const std::string dir = argv[1];
  const std::string which = argc > 2 ? argv[2] : "all";
  const uint64_t seed = argc > 3 ? strtoull(argv[3], nullptr, 0) : 0xC0FFEEull;
  const int px = argc > 4 ? atoi(argv[4]) : 466;
  if (px == 480) gGeom = displays::kLcd28;
  else if (px != 466) {
    fprintf(stderr, "display must be 466 or 480\n");
    return 2;
  }
  W = gGeom.w;
  H = gGeom.h;

  const Personality p = Personality::fromSeed(seed);
  printf("seed %llx: %s, eyes %s (%s), shy %.2f, curious %.2f, sleepy %.2f\n",
         (unsigned long long)seed, p.archetypeRo(), p.tintName(), p.rarityName(), p.shyness,
         p.curiosity, p.sleepiness);

  for (const Scenario& sc : scenarios()) {
    if (which != "all" && which != sc.name) continue;
    Recorder rec;
    rec.dir = dir;
    rec.name = sc.name;
    rec.open();
    Sim s(seed);
    s.rec = &rec;
    sc.script(s);
    rec.close(sc.caption);
  }
  return 0;
}
