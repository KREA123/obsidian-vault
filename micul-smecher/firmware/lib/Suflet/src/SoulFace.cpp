#include "SoulFace.h"

#include <math.h>

namespace suflet {

using namespace eyes;

static inline float approach(float v, float t, float rate, float dt) { return v + (t - v) * (1 - expf(-rate * dt)); }

bool SoulFace::begin(int w, int h) {
  W_ = w;
  H_ = h;
  return ren_.begin(w, h);
}

void SoulFace::setSeed(uint32_t seed) { rig_ = EyeRig(seed); }

void SoulFace::setDesign(int index, bool instant) {
  if (index < 0 || index >= kDesignCount) return;
  if (instant) {
    design_ = index;
    pendingDesign_ = -1;
    return;
  }
  pendingDesign_ = index;
  swapIn_ = 0.11f;  // eyes.js setDesign: blink, swap 110 ms later (eyes shut)
  rig_.blink(1);
}

void SoulFace::flash(Rgb c, float seconds) {
  flashCol_ = c;
  flashLeft_ = seconds;
}

void SoulFace::snapLayout(const FaceLayoutT& l) {
  lay_[0] = layT_[0] = l.k;
  lay_[1] = layT_[1] = l.cx;
  lay_[2] = layT_[2] = l.cy;
  layV_[0] = layV_[1] = layV_[2] = 0;
}

// the web SoulOS: RX (reaction words -> expressions)
static void reactionExpr(Reaction r, int& expr, float& hold) {
  hold = 0;
  switch (r) {
    case Reaction::WakeUp: expr = X_wake; break;
    case Reaction::Boop: expr = X_happy, hold = 1.3f; break;
    case Reaction::Hmph: expr = X_suspicious, hold = 1.5f; break;
    case Reaction::Laugh: expr = X_laugh; break;
    case Reaction::Shy: expr = X_shy, hold = 1.6f; break;
    case Reaction::Purr: expr = X_happy, hold = 2.2f; break;
    case Reaction::Dizzy: expr = X_startled; break;
    case Reaction::Scared: expr = X_shocked; break;
    case Reaction::Confused: expr = X_confused, hold = 2.0f; break;
    case Reaction::Yawn: expr = X_sleepy, hold = 2.0f; break;
    case Reaction::Sneeze: expr = X_sneeze; break;
    case Reaction::Hiccup: expr = X_surprised, hold = 0.6f; break;
    case Reaction::Love: expr = X_love, hold = 2.2f; break;
    case Reaction::Birthday: expr = X_excited, hold = 2.5f; break;
    case Reaction::MissedYou: expr = X_love, hold = 2.0f; break;
    case Reaction::Lonely: expr = X_sad, hold = 2.5f; break;
    case Reaction::Startle: expr = X_shocked; break;
    case Reaction::GoodNight: expr = X_goodbye; break;
    case Reaction::Hello: expr = X_hello; break;
    case Reaction::Celebrate: expr = X_excited, hold = 2.2f; break;
    case Reaction::Nope: expr = X_confused, hold = 1.4f; break;
    default: expr = -1; break;  // Listen / Think / Speak are states, not one-shots
  }
}

int SoulFace::moodFor(const FaceInputs& in) const {
  if (in.mode == Mode::Asleep || in.mode == Mode::Off || in.state == FaceState::Sleep) return X_sleepy;
  switch (in.state) {
    case FaceState::Listen: return X_listening;
    case FaceState::Think: return X_thinking;
    case FaceState::Error: return X_confused;
    case FaceState::Busy: return X_working;
    case FaceState::Wait: return X_surprised;
    case FaceState::Low: return X_hungry;
    case FaceState::Charge: return X_charging;
    default: break;
  }
  if (in.mode == Mode::Drowsy) return X_bored;
  return X_neutral;
}

void SoulFace::update(float dt, const FaceInputs& in) {
  t_ += dt;
  mode_ = in.mode;
  // one-shot reactions from the Brain
  if (in.reaction != lastReaction_) {
    lastReaction_ = in.reaction;
    int e;
    float hold;
    reactionExpr(in.reaction, e, hold);
    if (e >= 0) rig_.react(e, hold);
  }
  // state edges: Claude needs you -> shocked first; done / error flashes
  if (in.state != lastState_) {
    if (in.state == FaceState::Wait) {
      rig_.react(X_shocked);
      waitT_ = 0;
    }
    if (in.state == FaceState::Error && lastState_ != FaceState::Error) rig_.react(X_confused, 2.6f);
    lastState_ = in.state;
  }
  const int mood = moodFor(in);
  if (rig_.reacting()) rig_.setBack(mood);
  else if (rig_.mood() != mood) rig_.setExpression(mood);
  if (in.mode == Mode::Asleep || in.mode == Mode::Off) {  // asleep: lids shut over the sleepy mood
    rig_.target(Ch_lidL, 0.96f);
    rig_.target(Ch_lidR, 0.96f);
  }
  if (in.state == FaceState::Speak && t_ > talkNext_) {  // talking: little bobs, like a voice
    rig_.hop();
    talkNext_ = t_ + 0.24f + 0.26f * (float)h01((int64_t)(t_ * 10));
  }
  if (in.look) rig_.lookAt(in.lookX, in.lookY);
  else rig_.lookNone();
  if (in.level >= 0) rig_.setLevel(in.level);
  else rig_.clearLevel();
  if (pendingDesign_ >= 0) {
    swapIn_ -= dt;
    if (swapIn_ <= 0) {
      design_ = pendingDesign_;
      pendingDesign_ = -1;
    }
  }
  rig_.update(dt);
  // layout springs (the web OS: k 560, damping ~0.85 critical: lands in ~200 ms)
  layT_[0] = in.layout.k;
  layT_[1] = in.layout.cx;
  layT_[2] = in.layout.cy;
  const float K = 560, C = 2 * sqrtf(K) * 0.85f;
  for (int i = 0; i < 3; ++i) {
    float h = dt;
    while (h > 0) {
      const float s = h > 1.0f / 240 ? 1.0f / 240 : h;
      layV_[i] += (K * (layT_[i] - lay_[i]) - C * layV_[i]) * s;
      lay_[i] += layV_[i] * s;
      h -= s;
    }
  }
  // the rim lights
  fListen_ = approach(fListen_, in.state == FaceState::Listen ? 1.0f : 0.0f, 10, dt);
  fAlert_ = approach(fAlert_, in.alert ? 1.0f : 0.0f, 10, dt);
  fThink_ = approach(fThink_, in.state == FaceState::Think ? 1.0f : 0.0f, 8, dt);
  flashLeft_ -= dt;
  fFlash_ = approach(fFlash_, flashLeft_ > 0 ? 1.0f : 0.0f, 9, dt);
  progress_ = in.progress;
}

bool SoulFace::ringsActive() const {
  return fListen_ > 0.01f || fAlert_ > 0.01f || fThink_ > 0.01f || fFlash_ > 0.01f || progress_ > 0.005f;
}

void SoulFace::render(Canvas& cv) {
  const float S = (float)(W_ < H_ ? W_ : H_);
  const float D = S * lay_[0];
  const float cx = W_ * 0.5f + lay_[1] * S, cy = H_ * 0.5f + lay_[2] * S;
  RenderOpts o;
  o.hetero = hetero;
  o.alpha = dim;
  if (D > 2) ren_.render(cv, rig_, kDesigns[design_], cx, cy, D, o);
  if (!ringsActive()) return;
  // one light at a time on the rim (no glow on the device: flat rings)
  Raster& ras = ren_.raster();
  static Path p;
  if (!p.edgeCount() && !p.reserve(2048)) return;
  const float R = S * 0.5f, t = t_;
  auto ring = [&](Rgb c, float a, float w, float a0 = 0, float a1 = 6.2831853f) {
    if (a <= 0.01f) return;
    p.clear();
    p.strokeArc(R, R, 0.47f * S - w * 0.5f, a0, a1, w);
    ras.fill(cv, p, c, a > 1 ? 1 : a);
  };
  const float lv = rig_.level();
  if (fListen_ > 0.01f) ring(Rgb::hex(0x9FC6FF), (0.3f + 0.3f * (0.5f + 0.5f * sinf(t * 3)) + 0.35f * lv) * fListen_, 0.01f * S + 0.02f * S * lv);
  if (fAlert_ > 0.01f) {
    const float pz = 0.5f + 0.5f * sinf(t * 5);
    ring(Rgb::hex(0xFFB347), (0.3f + 0.45f * pz) * fAlert_, 0.012f * S + 0.008f * S * pz);
  }
  if (fThink_ > 0.01f) {
    const float a = t * 2.4f - 1.5707963f;
    ring(Rgb::hex(0xFFB347), 0.85f * fThink_, 0.012f * S, a, a + 0.9f);
  }
  if (fFlash_ > 0.01f) ring(flashCol_, 0.55f * fFlash_, 0.012f * S);
  if (progress_ > 0.005f) {
    const float a0 = -1.5707963f;
    ring(Rgb::hex(0xC9F2E4), 0.95f, 0.028f * S, a0, a0 + 6.2831853f * (progress_ < 0.999f ? progress_ : 0.999f));
  }
}

}  // namespace suflet
