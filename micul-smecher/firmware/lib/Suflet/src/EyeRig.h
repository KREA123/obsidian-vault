// The SOUL eyes animation rig: a faithful C++ port of eyes.js v2.1 (Rig).
//
// Every look is a set of spring targets (After Effects grammar: an
// anticipation move, then the action on a damped spring that overshoots and
// settles). Moods hold; reactions play a timeline once and fall back to the
// mood. Idle life: glances, micro-saccades, blinks (sometimes double), hops.
// The right pupil follows the left ~45 ms later.
//
// Determinism: the rig only advances through update(dt) and its seeded RNG
// (the same mulberry32 as eyes.js), so the same seed + the same calls give
// the same motion as the web engine (checked by a parity test against a
// fixture produced by node from eyes.js itself).
//
// Cost: ~45 springs stepped at 240 Hz (float), a handful of double ops for
// the clock. No heap allocation after construction.
#pragma once
#include <stdint.h>

#include "EyeTables.h"

namespace suflet {
namespace eyes {

uint32_t mix32(uint32_t x);
double h01(int64_t i);           // eyes.js h01: a hash of an integer to [0, 1)
uint32_t hashStr(const char* s);  // FNV-1a, eyes.js hashStr

// eyes.js rng(): mulberry32-style, returns [0, 1) as a double.
struct Mulberry {
  uint32_t a;
  explicit Mulberry(uint32_t seed = 1) : a(seed ? seed : 1u) {}
  double next();
};

struct Spring {
  float x = 0, t = 0, v = 0, k = 0, c = 0;
  void init(float val, float kk, float z);
  void step(float dt) {
    v += (-k * (x - t) - c * v) * dt;
    x += v * dt;
  }
};

class EyeRig {
 public:
  explicit EyeRig(uint32_t seed = 7, bool loop = false);

  // ---- control (eyes.js instance API) ----------------------------------
  void setExpression(int expr);           // a mood holds; a reaction plays once
  bool setExpression(const char* name);   // false if the name is unknown
  void react(int expr, float hold = 0);   // one-shot; a mood is held `hold` s (default 2.4)
  void lookAt(float x, float y);          // -1..1 each
  void lookNone() { look_ = false; }
  bool looking() const { return look_; }
  void blink(int n = 1, float slow = 0);
  void hop();
  void hide();                            // snap to nothing; follow with react(X_hello)
  void setLevel(float v);                 // listening pulse / charging fill from real data
  void clearLevel() { levelExt_ = false; }
  void setRandomMood(bool on);
  void setLoop(bool on);

  // Extensions for the device (not in eyes.js): hold a channel target, nudge
  // it, or jump it. Used for "asleep" (lids shut) on top of the sleepy mood.
  void target(int ch, float v) { s_[ch].t = v; }
  void kick(int ch, float dv) { s_[ch].v += dv; }
  void snap(int ch, float v) {
    s_[ch].x = v;
    s_[ch].t = v;
    s_[ch].v = 0;
  }

  // The mood a playing reaction falls back to (web SoulOS: rig.reaction.back).
  void setBack(int moodExpr) {
    if (reaction_ && moodExpr >= 0 && moodExpr < kMoodCount) reactBack_ = moodExpr;
  }
  // The mood the eyes are in, or return to after the playing reaction.
  int backMood() const { return reaction_ ? reactBack_ : (mood_ >= 0 ? mood_ : (int)X_neutral); }

  void update(float dt);  // substeps at 240 Hz, like eyes.js update()

  // ---- state for the renderer -------------------------------------------
  float ch(int c) const { return s_[c].x; }
  float pupilL(int axis) const { return pL_[axis].x; }
  float pupilR(int axis) const { return pR_[axis].x; }
  float eyeGaze(int axis) const { return eyeG_[axis].x; }
  float closed() const;  // blink amount: 0 open, 1 shut, < 0 = wider (overshoot)
  double time() const { return t_; }
  float level() const { return level_; }
  float charge() const { return charge_; }
  Pupil altType() const { return altType_; }
  GazeMode gazeMode() const { return gmode_; }
  float shakeF() const { return shakeF_; }
  int mood() const { return mood_; }
  int expression() const { return reaction_ ? reactExpr_ : mood_; }  // eyes.js .expression
  bool reacting() const { return reaction_; }
  double loopTime() const { return lt_; }
  float slitW = 1;  // eyes.js rig.slitW (slit pupils)

 private:
  struct GazeSample {
    double t;
    float x, y;
  };
  void step(float dt);
  void gaze();
  void targets(const KV* kv, int n);
  void kicks(const KV* kv, int n);
  void snaps(const KV* kv, int n);
  void applyKey(const Key& k);
  void goMood(int m, bool changed);
  double r() { return rng_.next(); }

  Mulberry rng_;
  uint32_t seed_;
  double t_ = 0, lt_ = 0, moodT_ = 0;
  bool loop_ = false;
  int mood_ = X_neutral;  // -1 = "__" (between a reaction and its mood)

  // the reaction being played
  bool reaction_ = false;
  int reactExpr_ = -1;
  double reactT0_ = 0;
  float reactDur_ = 0;
  const Key* reactKeys_ = nullptr;
  int reactNKeys_ = 0, reactDone_ = 0;
  int reactBack_ = X_neutral;

  // a mood waiting for its anticipation to finish
  bool pending_ = false;
  double pendingAt_ = 0;
  int pendingMood_ = 0;
  bool pendingChanged_ = false;

  Spring s_[Ch_Count];
  Spring pL_[2], pR_[2], eyeG_[2];
  static constexpr int kGq = 64;
  GazeSample gq_[kGq] = {};
  int gqHead_ = 0, gqLen_ = 0;
  float gazeT_[2] = {0, 0}, base_[2] = {0, 0};
  bool look_ = false;
  float lookXY_[2] = {0, 0};
  GazeMode gmode_ = GazeMode::Idle;
  Pupil altType_ = Pupil::Heart;
  float shakeF_ = 20;
  double blinkAt_ = -10;
  int blinkN_ = 1;
  float blinkSlow_ = 1, blinkEvery_ = 2, moodBlinkSlow_ = 1;
  double nextMicro_ = 0.4, nextGlance_ = 1.5, glanceUntil_ = -1, nextBlink_ = 0, nextHop_ = 0;
  float level_ = 0, charge_ = 0;
  bool levelExt_ = false;
  float levelV_ = 0;
  bool randomMood_ = false;
  double nextRandom_ = 0;
  int moodKeysDone_ = 0;
};

// ---- the birth roll (eyes.js roll / rollFromChipId) ----------------------
struct RollResult {
  int design = 0;  // index into kDesigns
  Rarity rarity = Rarity::Common;
  double odds = 0;  // probability of this exact design
};
RollResult roll(uint32_t seedHi, uint32_t seedLo);
// The 48-bit chip id (eFuse MAC, first byte = most significant) as eyes.js
// rollFromChipId('AABBCCDDEEFF') sees it: hi = 0x0000AABB, lo = 0xCCDDEEFF.
RollResult rollFromMac(const uint8_t mac[6]);
int exprByName(const char* name);  // -1 if unknown
const char* exprName(int expr);
bool isMood(int expr);

}  // namespace eyes
}  // namespace suflet
