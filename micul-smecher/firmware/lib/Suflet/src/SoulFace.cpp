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
    // the motion layer already answers being put face down (grumble, dim) and
    // upside down (shocked): don't let the Brain's goodbye / confused fight it
    if (motion_.active() && ((in.reaction == Reaction::GoodNight && motion_.gravZ() < -0.6f) ||
                             (in.reaction == Reaction::Confused && motion_.gravY() < -0.5f)))
      e = -1;
    if (e >= 0) rig_.react(e, hold);
  }
  // motion cues: the eyes answer (as eyes.js), the gestures go on to SoulOS
  {
    MotionCue c;
    while (motion_.poll(c)) {
      if (in.mode != Mode::Off) motion_.apply(c, rig_);
      ++cueN_;
      lastCue_ = c;
      if (c == MotionCue::TapTap) motionEv_.push(Ev::TapTap);
      if (c == MotionCue::NodYes) motionEv_.push(Ev::NodYes);
      if (c == MotionCue::NodNo) motionEv_.push(Ev::NodNo);
    }
  }
  // state edges: Claude needs you -> shocked first; done / error flashes
  const bool leftOffline = lastState_ == FaceState::Offline && in.state != FaceState::Offline;
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
  else if (rig_.mood() != mood || leftOffline) rig_.setExpression(mood);  // back online: the lids too
  if (in.mode == Mode::Asleep || in.mode == Mode::Off) {  // asleep: lids shut over the sleepy mood
    rig_.target(Ch_lidL, 0.96f);
    rig_.target(Ch_lidR, 0.96f);
  }
  else if (in.state == FaceState::Offline && !rig_.reacting()) {  // no internet: a little heavier lids, nothing more
    rig_.target(Ch_lidL, 0.2f);
    rig_.target(Ch_lidR, 0.2f);
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
  // the motion pose: level keeping and the dizzy wobble only while the eyes
  // fill the glass (small above a screen they would swing over the UI)
  if (motion_.active()) {
    pose_ = motion_.pose();
    const float k = lay_[0] < 0.55f ? 0.0f : (lay_[0] > 0.85f ? 1.0f : (lay_[0] - 0.55f) / 0.3f);
    pose_.roll *= k * k * (3 - 2 * k);
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

bool SoulFace::ringRefreshDue() const {
  const bool now = ringsActive();
  if (!now && !look_.any()) return false;
  if (now != look_.any()) return true;  // a ring appears or the last one goes away
  if (fabsf(progress_ - look_.progress) > 0.004f) return true;  // the approve arc: every frame
  return t_ - look_.t >= 1.0f / 12.0f;
}

void SoulFace::renderEyes(Canvas& cv, RectList* parts) {
  const float S = (float)(W_ < H_ ? W_ : H_);
  const float D = S * lay_[0];
  const float cx = W_ * 0.5f + lay_[1] * S, cy = H_ * 0.5f + lay_[2] * S;
  RenderOpts o;
  o.hetero = hetero;
  o.alpha = dim;
  if (motion_.active() && motionOn) o.motion = &pose_;
  if (D > 2) ren_.render(cv, rig_, kDesigns[design_], cx, cy, D, o, parts);
}

void SoulFace::renderRings(Canvas& cv, const RectList* repair, bool refresh) {
  if (refresh) {
    look_.listen = fListen_;
    look_.alert = fAlert_;
    look_.think = fThink_;
    look_.flash = fFlash_;
    look_.progress = progress_;
    look_.t = t_;
    look_.level = rig_.level();
    look_.flashCol = flashCol_;
  }
  if (!look_.any()) return;
  // one light at a time on the rim (no glow on the device: flat rings)
  const float S = (float)(W_ < H_ ? W_ : H_);
  Raster& ras = ren_.raster();
  const float R = S * 0.5f, t = look_.t;
  auto ring = [&](Rgb c, float a, float w, float a0 = 0, float a1 = 6.2831853f) {
    if (a <= 0.01f) return;
    ras.ring(cv, R, R, 0.47f * S - w * 0.5f, w, c, a > 1 ? 1 : a, a0, a1);
  };
  auto draw = [&]() {
    const float lv = look_.level;
    if (look_.listen > 0.01f) ring(Rgb::hex(0x9FC6FF), (0.3f + 0.3f * (0.5f + 0.5f * sinf(t * 3)) + 0.35f * lv) * look_.listen, 0.01f * S + 0.02f * S * lv);
    if (look_.alert > 0.01f) {
      const float pz = 0.5f + 0.5f * sinf(t * 5);
      ring(Rgb::hex(0xFFB347), (0.3f + 0.45f * pz) * look_.alert, 0.012f * S + 0.008f * S * pz);
    }
    if (look_.think > 0.01f) {
      const float a = t * 2.4f - 1.5707963f;
      ring(Rgb::hex(0xFFB347), 0.85f * look_.think, 0.012f * S, a, a + 0.9f);
    }
    if (look_.flash > 0.01f) ring(look_.flashCol, 0.55f * look_.flash, 0.012f * S);
    if (look_.progress > 0.005f) {
      const float a0 = -1.5707963f;
      ring(Rgb::hex(0xC9F2E4), 0.95f, 0.028f * S, a0, a0 + 6.2831853f * (look_.progress < 0.999f ? look_.progress : 0.999f));
    }
  };
  if (refresh || !repair) {
    draw();
  } else {
    for (int i = 0; i < repair->n; ++i) {  // the last look again, inside each repaired rectangle
      if (repair->r[i].empty()) continue;
      cv.setClip(repair->r[i]);
      draw();
    }
  }
  cv.clearClip();
}

}  // namespace suflet
