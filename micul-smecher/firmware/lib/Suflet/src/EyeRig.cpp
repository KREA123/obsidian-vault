#include "EyeRig.h"

#include <math.h>
#include <string.h>

namespace suflet {
namespace eyes {

static constexpr double kTau = 6.283185307179586;

uint32_t mix32(uint32_t x) {
  x = (x ^ (x >> 16)) * 0x7feb352du;
  x = (x ^ (x >> 15)) * 0x846ca68bu;
  return x ^ (x >> 16);
}

double h01(int64_t i) {
  // JS: mix32(i * 2654435761 + 12345) with ToUint32 (wraps modulo 2^32)
  const uint32_t x = (uint32_t)(uint64_t)(i * (int64_t)2654435761LL + 12345);
  return mix32(x) / 4294967296.0;
}

uint32_t hashStr(const char* s) {
  uint32_t h = 2166136261u;
  // JS iterates UTF-16 code units; every id/name used as a seed is ASCII.
  for (; s && *s; ++s) {
    h ^= (uint8_t)*s;
    h *= 16777619u;
  }
  return h;
}

double Mulberry::next() {
  a += 0x6d2b79f5u;
  uint32_t t = (a ^ (a >> 15)) * (1u | a);
  t = (t + ((t ^ (t >> 7)) * (61u | t))) ^ t;
  return (t ^ (t >> 14)) / 4294967296.0;
}

void Spring::init(float val, float kk, float z) {
  x = t = val;
  v = 0;
  k = kk;
  c = 2.0f * sqrtf(kk) * z;
}

static inline float clampf_(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
static inline double inQuad(double t) { return t * t; }
static inline double outBack(double t, double s) {
  const double u = t - 1;
  return 1 + (s + 1) * u * u * u + s * u * u;
}

int exprByName(const char* name) {
  if (!name) return -1;
  for (int i = 0; i < kMoodCount; ++i)
    if (!strcmp(kMoods[i].name, name)) return i;
  for (int i = 0; i < kReactionCount; ++i)
    if (!strcmp(kReactions[i].name, name)) return kMoodCount + i;
  return -1;
}

const char* exprName(int e) {
  if (e >= 0 && e < kMoodCount) return kMoods[e].name;
  if (e >= kMoodCount && e < X_Count) return kReactions[e - kMoodCount].name;
  return "?";
}

bool isMood(int e) { return e >= 0 && e < kMoodCount; }

// ------------------------------------------------------------------ rig ---

EyeRig::EyeRig(uint32_t seed, bool loop) : rng_(seed ? seed : 7u), seed_(seed ? seed : 7u), loop_(loop) {
  for (int i = 0; i < Ch_Count; ++i) s_[i].init(kBase[i], kSpringK[i], kSpringZ[i]);
  for (int i = 0; i < 2; ++i) {
    pL_[i].init(0, 900, 0.52f);
    pR_[i].init(0, 760, 0.46f);
    eyeG_[i].init(0, 140, 0.75f);
  }
  // same order of RNG draws as the eyes.js constructor
  nextBlink_ = 1.8 + r() * 1.5;
  nextHop_ = 4 + r() * 4;
  nextRandom_ = 3 + r() * 4;
}

void EyeRig::targets(const KV* kv, int n) {
  for (int i = 0; i < n; ++i) s_[kv[i].ch].t = kv[i].v;
}
void EyeRig::kicks(const KV* kv, int n) {
  for (int i = 0; i < n; ++i) s_[kv[i].ch].v += kv[i].v;
}
void EyeRig::snaps(const KV* kv, int n) {
  for (int i = 0; i < n; ++i) {
    Spring& s = s_[kv[i].ch];
    s.x = s.t = kv[i].v;
    s.v = 0;
  }
}

void EyeRig::applyKey(const Key& k) {
  snaps(k.snap, k.nSnap);
  targets(k.set, k.nSet);
  kicks(k.kick, k.nKick);
  if (k.alt != Pupil::None) altType_ = k.alt;
  if (k.hasGaze) {
    base_[0] = k.gx;
    base_[1] = k.gy;
  }
  if (k.mode != GazeMode::Keep) gmode_ = k.mode;
  if (k.shakeF > 0) shakeF_ = k.shakeF;
  if (k.blink) blink(k.blink);
}

void EyeRig::goMood(int mi, bool changed) {
  const MoodDef& m = kMoods[mi];
  for (int i = 0; i < Ch_Count; ++i) s_[i].t = m.targets[i];
  if (changed) kicks(m.kick, m.nKick);
  base_[0] = m.gx;
  base_[1] = m.gy;
  gmode_ = m.mode;
  if (m.alt != Pupil::None) altType_ = m.alt;
  shakeF_ = m.shakeF;
  moodBlinkSlow_ = m.blinkSlow;
  blinkEvery_ = m.blinkEvery;
  pending_ = false;
}

void EyeRig::setExpression(int e) {
  if (e >= kMoodCount && e < X_Count) {
    react(e);
    return;
  }
  if (e < 0 || e >= kMoodCount) e = X_neutral;
  const MoodDef& m = kMoods[e];
  const bool changed = e != mood_ || reaction_;
  reaction_ = false;
  mood_ = e;
  moodT_ = 0;
  moodKeysDone_ = 0;
  if (changed && m.anticD > 0) {
    targets(m.antic, m.nAntic);
    if (m.anticHasGaze) {
      base_[0] = m.anticGx;
      base_[1] = m.anticGy;
    }
    pending_ = true;
    pendingAt_ = t_ + m.anticD;
    pendingMood_ = e;
    pendingChanged_ = changed;
  } else {
    goMood(e, changed);
  }
  if (changed && m.blink) blink(m.blink);
}

bool EyeRig::setExpression(const char* name) {
  const int e = exprByName(name);
  if (e < 0) return false;
  setExpression(e);
  return true;
}

void EyeRig::react(int e, float hold) {
  if (isMood(e)) {  // a mood as a one-shot: hold it, then go back
    const int back = mood_ == e ? (int)X_neutral : (mood_ < 0 ? (int)X_neutral : mood_);
    setExpression(e);
    reaction_ = true;
    reactExpr_ = e;
    reactT0_ = t_;
    reactDur_ = hold > 0 ? hold : 2.4f;
    reactKeys_ = nullptr;
    reactNKeys_ = 0;
    reactDone_ = 0;
    reactBack_ = back;
    return;
  }
  if (e < kMoodCount || e >= X_Count) return;
  const ReactionDef& rd = kReactions[e - kMoodCount];
  pending_ = false;
  const int cur = mood_ >= 0 ? mood_ : (int)X_neutral;
  for (int i = 0; i < Ch_Count; ++i) s_[i].t = kMoods[cur].targets[i];
  reaction_ = true;
  reactExpr_ = e;
  reactT0_ = t_;
  reactDur_ = hold > 0 ? hold : rd.dur;
  reactKeys_ = rd.keys;
  reactNKeys_ = rd.nKeys;
  reactDone_ = 0;
  reactBack_ = mood_ >= 0 ? mood_ : (int)X_neutral;
}

void EyeRig::lookAt(float x, float y) {
  look_ = true;
  lookXY_[0] = clampf_(x, -1, 1);
  lookXY_[1] = clampf_(y, -1, 1);
}

void EyeRig::blink(int n, float slow) {
  blinkAt_ = t_;
  blinkN_ = n > 0 ? n : 1;
  blinkSlow_ = slow > 0 ? slow : (moodBlinkSlow_ > 0 ? moodBlinkSlow_ : 1);
}

void EyeRig::hop() {
  s_[Ch_bob].v -= 0.55f;
  s_[Ch_sy].v += 2.2f;
  s_[Ch_sx].v -= 1.2f;
}

void EyeRig::hide() {
  reaction_ = false;
  snap(Ch_scale, 0);
}

void EyeRig::setLevel(float v) {
  levelExt_ = true;
  levelV_ = clampf_(v, 0, 1);
}

void EyeRig::setRandomMood(bool on) {
  randomMood_ = on;
  nextRandom_ = t_ + 0.5;
}

void EyeRig::setLoop(bool on) {
  loop_ = on;
  if (on) lt_ = kLoopSeconds - 0.3;
  setExpression(X_neutral);
}

float EyeRig::closed() const {
  const double k = blinkSlow_, c = 0.08 * k, h = 0.04 * k, o = 0.17 * k, q0 = t_ - blinkAt_;
  auto one = [&](double q) -> double {
    if (q < 0) return 0;
    if (q < c) return inQuad(q / c);
    if (q < c + h) return 1;
    if (q < c + h + o) return 1 - outBack((q - c - h) / o, 1.8);
    return 0;
  };
  double v = one(q0);
  if (blinkN_ > 1) {
    const double v2 = one(q0 - (c + h + o * 0.7));
    if (fabs(v2) > fabs(v)) v = v2;
  }
  return (float)v;
}

void EyeRig::update(float dt) {
  if (!(dt > 0)) return;
  int n = (int)ceil(dt / (1.0 / 240.0));
  if (n < 1) n = 1;
  if (n > 240) n = 240;  // never more than 1 s of catch-up in one call
  const float h = dt / n;
  for (int i = 0; i < n; ++i) step(h);
}

void EyeRig::gaze() {
  const double t = t_;
  const float* b = base_;
  if (look_) {
    gazeT_[0] = lookXY_[0];
    gazeT_[1] = lookXY_[1];
    return;
  }
  switch (gmode_) {
    case GazeMode::Still:
      gazeT_[0] = b[0];
      gazeT_[1] = b[1];
      return;
    case GazeMode::Spin:
      gazeT_[0] = (float)(cos(t * 6.5) * 0.62);
      gazeT_[1] = (float)(sin(t * 6.5) * 0.48);
      return;
    case GazeMode::Rattle: {
      const int64_t q = (int64_t)floor(t * 14);
      gazeT_[0] = (float)((h01(q) - 0.5) * 1.4);
      gazeT_[1] = (float)((h01(q + 99) - 0.5) * 1.0);
      return;
    }
    case GazeMode::Sway:
      gazeT_[0] = (float)(sin(t * 1.15) * 0.72);
      gazeT_[1] = 0.06f;
      return;
    case GazeMode::Drift:
      gazeT_[0] = (float)(b[0] + sin(t * 0.9) * 0.12);
      gazeT_[1] = (float)(b[1] + sin(t * 1.3) * 0.06);
      return;
    case GazeMode::Wobble:
      gazeT_[0] = (float)(b[0] + sin(t * 9) * 0.03);
      gazeT_[1] = b[1];
      return;
    case GazeMode::Scan: {  // reading: small saccades along a line, snap back, next line
      const double line = 1.25, q = fmod(t, line * 3) / line;
      const double li = floor(q), f = q - li;
      const double x = f < 0.85 ? -0.6 + floor(f / 0.85 * 6) / 5 * 1.2 : -0.6;
      gazeT_[0] = (float)x;
      gazeT_[1] = (float)(-0.25 + li * 0.22);
      return;
    }
    default:
      break;
  }
  if (t > nextGlance_) {
    const double a = r(), c = r();
    gazeT_[0] = (float)(b[0] + (a * 2 - 1) * 0.8);
    gazeT_[1] = (float)(b[1] + (c * 2 - 1) * 0.5);
    glanceUntil_ = t + 0.6 + r() * 1.3;
    nextGlance_ = t + 2 + r() * 3.5;
    if (r() < 0.3) blink(1);
  } else if (glanceUntil_ > 0 && t > glanceUntil_) {
    gazeT_[0] = b[0];
    gazeT_[1] = b[1];
    glanceUntil_ = -1;
  } else if (t > nextMicro_) {
    const float gx = glanceUntil_ > 0 ? gazeT_[0] : b[0];
    const float gy = glanceUntil_ > 0 ? gazeT_[1] : b[1];
    const double a = r(), c = r();
    gazeT_[0] = (float)(gx + (a * 2 - 1) * 0.09);
    gazeT_[1] = (float)(gy + (c * 2 - 1) * 0.06);
    nextMicro_ = t + 0.3 + r() * 1.1;
  } else if (glanceUntil_ < 0 && hypot(gazeT_[0] - b[0], gazeT_[1] - b[1]) > 0.25) {
    gazeT_[0] = b[0];
    gazeT_[1] = b[1];
  }
}

void EyeRig::step(float dt) {
  const double prev = lt_;
  t_ += dt;
  moodT_ += dt;
  const double t = t_;
  if (pending_ && t >= pendingAt_) goMood(pendingMood_, pendingChanged_);
  // mood timelines
  if (mood_ >= 0 && !reaction_) {
    const MoodDef& m = kMoods[mood_];
    while (moodKeysDone_ < m.nKeys && m.keys[moodKeysDone_].t <= moodT_) applyKey(m.keys[moodKeysDone_++]);
  }
  // reaction timeline
  if (reaction_) {
    const double q = t - reactT0_;
    while (reactDone_ < reactNKeys_ && reactKeys_[reactDone_].t <= q) applyKey(reactKeys_[reactDone_++]);
    if (q >= reactDur_) {
      reaction_ = false;
      const int back = reactBack_;
      mood_ = -1;
      setExpression(back);
    }
  }
  if (loop_) {
    lt_ = fmod(lt_ + dt, (double)kLoopSeconds);
    const bool wrapped = lt_ < prev;
    for (const ScriptEv& e : kScript) {
      const bool hit = wrapped ? (e.t > prev || e.t <= lt_) : (e.t > prev && e.t <= lt_);
      if (!hit) continue;
      if (e.mood >= 0) setExpression(e.mood);
      if (e.look) {
        base_[0] = e.lx;
        base_[1] = e.ly;
      }
      if (e.blink) blink(e.blink, e.slow);
      if (e.hop) hop();
    }
    const int64_t slot = (int64_t)floor(lt_ / 0.55);
    const bool quiet = lt_ > 14.1 || lt_ < 0.3 || mood_ == X_sleepy || mood_ == X_love || mood_ == X_smirk;
    float mx = 0, my = 0;
    if (!quiet) {
      mx = (float)((h01(slot * 2 + 1) - 0.5) * 0.16);
      my = (float)((h01(slot * 2 + 2) - 0.5) * 0.1);
    }
    if (look_) {
      gazeT_[0] = lookXY_[0];
      gazeT_[1] = lookXY_[1];
    } else {
      gazeT_[0] = base_[0] + mx;
      gazeT_[1] = base_[1] + my;
    }
  } else {
    if (randomMood_ && !reaction_ && t > nextRandom_) {
      const int n = (int)(sizeof(kRandomPool) / sizeof(kRandomPool[0]));
      int pi = (int)floor(r() * n);
      if (pi >= n) pi = n - 1;
      const int pick = kRandomPool[pi];
      const float hold = isMood(pick) ? (float)(2.2 + r() * 1.5) : 0.0f;
      react(pick, hold);
      nextRandom_ = t + 3.2 + r() * (6.7 - 3.2);
    }
    gaze();
    if (t > nextBlink_) {
      if (s_[Ch_smileL].x < 0.4f && s_[Ch_altL].x < 0.5f && s_[Ch_squeezeL].x < 0.3f && s_[Ch_scale].x > 0.5f)
        blink(r() < 0.22 ? 2 : 1, moodBlinkSlow_);
      nextBlink_ = t + blinkEvery_ + r() * 3.6;
    }
    if (t > nextHop_) {
      if (mood_ == X_neutral && !reaction_ && r() < 0.6) hop();
      nextHop_ = t + 3.5 + r() * 5;
    }
  }
  // levels: listening (voice-ish), charging (fills up)
  if (levelExt_) {
    level_ = levelV_;
    charge_ = levelV_;
  } else {
    const double lv = 0.45 + 0.3 * sin(t * 7.1) * sin(t * 2.3 + 1) + 0.25 * sin(t * 13.7 + sin(t * 3));
    level_ = clampf_((float)lv, 0, 1);
    charge_ = (float)fmod(moodT_ * 0.28, 1.25);
  }
  // gaze springs: the right pupil follows 45 ms later
  if (gqLen_ == kGq) {  // full: drop the oldest
    gqHead_ = (gqHead_ + 1) % kGq;
    --gqLen_;
  }
  gq_[(gqHead_ + gqLen_) % kGq] = GazeSample{t, gazeT_[0], gazeT_[1]};
  ++gqLen_;
  while (gqLen_ > 2 && gq_[(gqHead_ + 1) % kGq].t <= t - 0.045) {
    gqHead_ = (gqHead_ + 1) % kGq;
    --gqLen_;
  }
  const GazeSample& late = gq_[gqHead_];
  pL_[0].t = gazeT_[0];
  pL_[1].t = gazeT_[1];
  pR_[0].t = late.x;
  pR_[1].t = late.y;
  eyeG_[0].t = gazeT_[0];
  eyeG_[1].t = gazeT_[1];
  for (int i = 0; i < 2; ++i) {
    pL_[i].step(dt);
    pR_[i].step(dt);
    eyeG_[i].step(dt);
  }
  for (int i = 0; i < Ch_Count; ++i) s_[i].step(dt);
}

// --------------------------------------------------------------- roll ---

RollResult roll(uint32_t seedHi, uint32_t seedLo) {
  const uint32_t h = mix32(seedLo ^ mix32(seedHi ^ 0x534F554Cu));
  const double u = mix32(h) / 4294967296.0;
  double acc = 0;
  int tier = (int)Rarity::Count - 1;
  for (int i = 0; i < (int)Rarity::Count; ++i) {
    acc += kRarityRate[i];
    if (u < acc) {
      tier = i;
      break;
    }
  }
  int count = 0;
  for (int i = 0; i < kDesignCount; ++i)
    if ((int)kDesigns[i].rarity == tier) ++count;
  RollResult res;
  res.rarity = (Rarity)tier;
  if (!count) return res;
  const int k = (int)floor(mix32(h ^ 0x9E3779B9u) / 4294967296.0 * count);
  int seen = 0;
  for (int i = 0; i < kDesignCount; ++i) {
    if ((int)kDesigns[i].rarity != tier) continue;
    if (seen++ == k) {
      res.design = i;
      break;
    }
  }
  res.odds = kRarityRate[tier] / count;
  return res;
}

RollResult rollFromMac(const uint8_t m[6]) {
  const uint32_t hi = ((uint32_t)m[0] << 8) | m[1];
  const uint32_t lo = ((uint32_t)m[2] << 24) | ((uint32_t)m[3] << 16) | ((uint32_t)m[4] << 8) | m[5];
  return roll(hi, lo);
}

}  // namespace eyes
}  // namespace suflet
