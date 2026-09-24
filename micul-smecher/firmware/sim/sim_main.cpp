// Native simulator: runs the exact firmware "soul" (lib/Suflet) on the PC,
// drives it with scripted sensor events and writes the frames it draws.
//
//   ./suflet_sim <out_dir> [scenario] [seed]
//
// Each scenario writes <out_dir>/<name>.rgb (raw RGB888 frames, 466x466)
// plus <name>.json (frame count, fps, body-light per frame). The Python
// script tools/frames_to_media.py turns them into GIF/MP4/contact sheets.
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
#include "Gestures.h"
#include "Personality.h"

using namespace suflet;

namespace {

constexpr int W = 466, H = 466;
constexpr float kFps = 30.0f;

struct Recorder {
  std::string dir, name;
  FILE* f = nullptr;
  int frames = 0;
  std::string bodyJson;
  std::vector<uint16_t> fb = std::vector<uint16_t>(W * H);
  Canvas cv{W, H, fb.data()};

  void open() {
    f = fopen((dir + "/" + name + ".rgb").c_str(), "wb");
    if (!f) {
      perror("open");
      exit(1);
    }
  }
  void frame(const Brain& b) {
    cv.fill(pal::kBlack);
    renderFace(cv, b.face());
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
    FILE* j = fopen((dir + "/" + name + ".json").c_str(), "wb");
    fprintf(j, "{\"name\":\"%s\",\"w\":%d,\"h\":%d,\"fps\":%.0f,\"frames\":%d,\"caption\":\"%s\",\"body\":[%s]}\n",
            name.c_str(), W, H, kFps, frames, caption, bodyJson.c_str());
    fclose(j);
    printf("%-16s %4d frames  %s\n", name.c_str(), frames, caption);
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
  explicit Sim(uint64_t seed) : brain(Personality::fromSeed(seed), seed * 7 + 1) {
    in.hour = 14.5f;
  }
  void step(bool render) {
    const float dt = 1.0f / kFps;
    still = moving ? 0 : still + dt;
    in.stillFor = still;
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
    if (render && rec) rec->frame(brain);
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
    fprintf(stderr, "usage: %s <out_dir> [scenario|all] [seed]\n", argv[0]);
    return 2;
  }
  const std::string dir = argv[1];
  const std::string which = argc > 2 ? argv[2] : "all";
  const uint64_t seed = argc > 3 ? strtoull(argv[3], nullptr, 0) : 0xC0FFEEull;

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
