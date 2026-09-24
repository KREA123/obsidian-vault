// The Brain: mood + attention + reactions -> one Face per frame.
//
// It is alive with zero connectivity (idle breathing, blinking, glances,
// dozing off, reacting to touch and motion). The AI link only adds states
// on top (listening / thinking / speaking with a tone); if the server
// disappears, nothing about its life breaks.
#pragma once
#include <stdint.h>

#include "Events.h"
#include "Face.h"
#include "Personality.h"
#include "Rng.h"

namespace suflet {

enum class Reaction : uint8_t {
  None,
  WakeUp,
  Boop,
  Hmph,  // boop while grumpy
  Laugh,
  Shy,
  Purr,
  Dizzy,
  Scared,
  Confused,
  Yawn,
  Sneeze,
  Hiccup,
  Love,
  Birthday,
  MissedYou,
  Lonely,
  Startle,
  GoodNight,
  Listen,  // AI: finger on the stone, it listens
  Think,   // AI: waiting for the answer
  Speak,   // AI: talking, eyes follow the voice
  Hello,      // Claude desktop connected
  Celebrate,  // Claude level up (every 50K tokens)
  Nope,       // you denied a Claude request: little head shake
  Count
};
const char* reactionName(Reaction r);

enum class Mode : uint8_t { Awake, Drowsy, Asleep, Off };
const char* modeName(Mode m);

// Haptic / sound cues for the device layer (ignored if it has no actuator).
enum class Cue : uint8_t {
  None,
  Click,
  Triplet,
  PurrOn,
  PurrOff,
  Buzz,
  Chirp,
  DoubleChirp,
  Hmm,
  Sneeze,
  Hic,
  Yawn,
  ListenOn,   // start streaming the microphone to the AI link
  ListenOff,  // stop streaming
  Nudge,      // gentle haptic: Claude is waiting for you
  ClaudeApprove,  // send {"decision":"once"} for the pending prompt
  ClaudeDeny,     // send {"decision":"deny"}
};

// Emotional tone the AI attaches to its answer.
enum class Tone : uint8_t { Neutral, Happy, Sad, Surprised, Cheeky, Sleepy, Love };

struct Mood {
  float energy = 0.2f;     // -1 sleepy .. +1 hyper
  float valence = 0.3f;    // -1 grumpy .. +1 happy
  float attention = 0.2f;  // need for attention 0..1 (grows when ignored)
  float grumpyFor = 0;     // seconds left of sulking (after being shaken)
};

struct Inputs {
  float tiltX = 0, tiltY = 0;    // from MotionDetector
  float stillFor = 0;            // seconds without motion
  bool faceDown = false;         // lying on its face (put to bed)
  float knockX = 0, knockY = 0;  // direction of the last knock
  float hour = -1;               // local hour 0..24, <0 = unknown
  float audioLevel = 0;          // AI voice / mic level 0..1
};

struct BodyLight {
  Rgb color;
  float level = 0;  // 0..1
};

// What survives power cycles (the device stores it in NVS).
struct Memory {
  uint32_t boopsTotal = 0;
  uint16_t boopsToday = 0;
  int32_t day = -1;  // days since epoch, -1 = unknown
  int32_t rareDay[3] = {-1, -1, -1};
  int32_t loveDay = -1;
};

class Brain {
 public:
  explicit Brain(const Personality& p, uint64_t rngSeed = 0);

  void event(Ev e);
  void trigger(Reaction r);  // demo mode / serial commands
  // Power-on: eyes light up as if waking (missed-you / birthday / yawn
  // follow when setAbsence() / setDay() say so). Call once after setup.
  void boot() {
    mode_ = Mode::Asleep;
    wake(true);
  }
  void update(float dt, const Inputs& in);

  // Calendar: call on boot and at midnight.
  void setDay(int32_t day, bool birthday);
  // Hours since the last interaction (from the RTC at boot).
  void setAbsence(float hours) { absenceH_ = hours; }
  // AI link availability (Wi-Fi up + account). Offline: hold = purr.
  void setAiLink(bool up) { aiLink_ = up; }
  void setTone(Tone t) { tone_ = t; }

  const Face& face() const { return face_; }
  BodyLight body() const { return body_; }
  bool popCue(Cue& c);
  Mode mode() const { return mode_; }
  Reaction reaction() const { return cur_; }
  const Mood& mood() const { return mood_; }
  const Personality& personality() const { return p_; }
  Memory& memory() { return mem_; }
  bool displayOff() const { return mode_ == Mode::Off; }
  float frameRateHint() const;  // fps the device should render at
  bool claudePrompt() const { return promptActive_; }
  bool claudeBusy() const { return claudeBusy_; }
  float approveProgress() const { return approveHold_ ? approveT_ / kApproveHoldS : 0.0f; }
  static constexpr float kApproveHoldS = 1.2f;  // hold this long to approve
  float time() const { return t_; }

 private:
  struct Spring {
    float x = 0, v = 0;
    void step(float target, float dt, float w, float z) {
      while (dt > 0) {
        const float h = dt > (1.0f / 240.0f) ? (1.0f / 240.0f) : dt;
        v += (w * w * (target - x) - 2.0f * z * w * v) * h;
        x += v * h;
        dt -= h;
      }
    }
  };

  void start(Reaction r);
  void finish();
  void release();  // end of a held reaction
  void wake(bool ceremony);
  void afterInteraction(bool tap);
  bool rollRare(int idx, float p);
  void updateMood(float dt, const Inputs& in);
  void updateIdle(float dt, const Inputs& in);
  void compose(const Inputs& in, float dt = 0);
  void applyReaction(Face& f, float rt, float& tx, float& ty);
  void pushCue(Cue c);
  bool night() const { return hour_ >= 22.0f || (hour_ >= 0 && hour_ < 6.0f); }
  bool morning() const { return hour_ >= 6.0f && hour_ < 10.0f; }

  Personality p_;
  Rng rng_;
  Memory mem_;
  Mood mood_;
  Face face_;
  BodyLight body_;
  Mode mode_ = Mode::Awake;
  Reaction cur_ = Reaction::None, queued_ = Reaction::None;
  float t_ = 0, rt_ = 0, dur_ = 0;
  bool held_ = false;
  float releaseTail_ = 0;
  float hour_ = -1;
  float modeT_ = 0;  // seconds in current mode
  float asleepFor_ = 0;
  float absenceH_ = 0;
  bool birthday_ = false, birthdayShown_ = false;
  bool aiLink_ = false;
  Tone tone_ = Tone::Neutral;
  float audio_ = 0;

  // idle life
  float nextBlink_ = 1.5f, blinkT_ = -1, blinkDur_ = 0.13f, nextSaccade_ = 1.0f;
  float gazeTX_ = 0, gazeTY_ = 0;
  Spring gx_, gy_, bounce_;
  float sideSign_ = 1;  // which way it looks away / hops
  float lastTapT_ = -100, lastInteractT_ = 0;
  int tapBurst_ = 0;
  float lonelyCool_ = 0;
  float knockX_ = 0, knockY_ = 0;
  uint8_t cueMask_ = 0;  // one-shot cues inside a reaction

  // Claude desktop link: background activities (shown when no reaction plays)
  bool claudeBusy_ = false, promptActive_ = false, approveHold_ = false;
  float approveT_ = 0, activityT_ = 0, nudgeT_ = 0;

  Cue cues_[8];
  int cueHead_ = 0, cueCount_ = 0;
};

}  // namespace suflet
