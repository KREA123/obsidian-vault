#include "Brain.h"

#include <math.h>

#include <initializer_list>

namespace suflet {

namespace {
constexpr float kPi = 3.14159265f;

struct RInfo {
  const char* name;
  float dur;     // seconds (ignored while held)
  uint8_t prio;  // a reaction interrupts another of equal or lower priority
  bool held;     // lasts until released (finger lifted, turned back...)
  float tail;    // fade-out after release
};

const RInfo kR[] = {
    {"none", 0, 0, false, 0},           {"wake_up", 1.8f, 3, false, 0},
    {"boop", 1.4f, 2, false, 0},        {"hmph", 1.6f, 2, false, 0},
    {"laugh", 1.8f, 2, false, 0},       {"shy", 3.0f, 2, false, 0},
    {"purr", 0, 3, true, 1.2f},         {"dizzy", 3.5f, 4, false, 0},
    {"scared", 1.6f, 5, false, 0},      {"confused", 0, 3, true, 0.6f},
    {"yawn", 2.6f, 2, false, 0},        {"sneeze", 1.9f, 2, false, 0},
    {"hiccup", 2.6f, 2, false, 0},      {"love", 2.8f, 3, false, 0},
    {"birthday", 4.5f, 3, false, 0},    {"missed_you", 3.2f, 3, false, 0},
    {"lonely", 4.5f, 1, false, 0},      {"startle", 1.2f, 4, false, 0},
    {"good_night", 2.2f, 3, false, 0},  {"listen", 0, 6, true, 0},
    {"think", 10.0f, 6, false, 0},  // gives up if the server never answers
    {"speak", 0, 6, true, 0.4f},        {"hello", 1.4f, 2, false, 0},
    {"celebrate", 3.0f, 3, false, 0},   {"nope", 1.2f, 3, false, 0},
};
static_assert(sizeof(kR) / sizeof(kR[0]) == (unsigned)Reaction::Count, "reaction table");

float sm(float x) {
  x = x < 0 ? 0 : (x > 1 ? 1 : x);
  return x * x * (3 - 2 * x);
}
// 0 before a, 1 after b, smooth in between
float ramp(float t, float a, float b) { return sm((t - a) / (b - a)); }
// up between a..b, down between c..d
float bump(float t, float a, float b, float c, float d) { return ramp(t, a, b) * (1.0f - ramp(t, c, d)); }
float lerpf(float a, float b, float t) { return a + (b - a) * t; }
float clamp1(float v) { return v < -1 ? -1.0f : (v > 1 ? 1.0f : v); }
float clamp01(float v) { return v < 0 ? 0.0f : (v > 1 ? 1.0f : v); }

Rgb hsv(float h, float s, float v) {
  h = fmodf(h, 1.0f);
  if (h < 0) h += 1.0f;
  const float i = floorf(h * 6.0f), f = h * 6.0f - i;
  const float p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  float r = v, g = t, b = p;
  switch ((int)i % 6) {
    case 0: r = v; g = t; b = p; break;
    case 1: r = q; g = v; b = p; break;
    case 2: r = p; g = v; b = t; break;
    case 3: r = p; g = q; b = v; break;
    case 4: r = t; g = p; b = v; break;
    default: r = v; g = p; b = q; break;
  }
  return Rgb((uint8_t)(r * 255), (uint8_t)(g * 255), (uint8_t)(b * 255));
}

bool isUserEvent(Ev e) {
  switch (e) {
    case Ev::AiThinking:
    case Ev::AiSpeakStart:
    case Ev::AiSpeakEnd:
    case Ev::ClaudeUp:
    case Ev::ClaudeDown:
    case Ev::ClaudeBusyStart:
    case Ev::ClaudeBusyEnd:
    case Ev::ClaudePrompt:
    case Ev::ClaudePromptGone:
    case Ev::ClaudeLevelUp:
    case Ev::ClaudeQuickApprove:
    case Ev::AlarmDue:
    case Ev::None:
    case Ev::Count:
      return false;
    default:
      return true;
  }
}
}  // namespace

const char* reactionName(Reaction r) {
  const unsigned i = (unsigned)r;
  return i < (unsigned)Reaction::Count ? kR[i].name : "?";
}

const char* modeName(Mode m) {
  switch (m) {
    case Mode::Awake: return "awake";
    case Mode::Drowsy: return "drowsy";
    case Mode::Asleep: return "asleep";
    case Mode::Off: return "off";
  }
  return "?";
}

Brain::Brain(const Personality& p, uint64_t rngSeed)
    : p_(p), rng_(rngSeed ? rngSeed : (p.seed ^ 0xB4A1B4A1ull)) {
  nextBlink_ = rng_.range(p_.blinkMin, p_.blinkMax) * 0.5f;
  compose(Inputs{});
}

void Brain::pushCue(Cue c) {
  if (cueCount_ == 8) {
    cueHead_ = (cueHead_ + 1) % 8;
    --cueCount_;
  }
  cues_[(cueHead_ + cueCount_) % 8] = c;
  ++cueCount_;
}

bool Brain::popCue(Cue& c) {
  if (!cueCount_) return false;
  c = cues_[cueHead_];
  cueHead_ = (cueHead_ + 1) % 8;
  --cueCount_;
  return true;
}

void Brain::setDay(int32_t day, bool birthday) {
  if (day != mem_.day) mem_.boopsToday = 0;
  mem_.day = day;
  if (birthday && !birthday_) birthdayShown_ = false;
  birthday_ = birthday;
}

float Brain::frameRateHint() const {
  switch (mode_) {
    case Mode::Off: return 2;
    case Mode::Asleep: return 12;
    case Mode::Drowsy: return 20;
    case Mode::Awake: return 30;
  }
  return 30;
}

// ------------------------------------------------------------- reactions --

void Brain::start(Reaction r) {
  if (r == Reaction::None) return;
  if (cur_ != Reaction::None && kR[(int)r].prio < kR[(int)cur_].prio) {
    if (kR[(int)r].prio >= 2 && queued_ == Reaction::None) queued_ = r;
    return;
  }
  if (cur_ == Reaction::Purr && r != Reaction::Purr) pushCue(Cue::PurrOff);
  if (cur_ == Reaction::Listen && r != Reaction::Listen) pushCue(Cue::ListenOff);
  cur_ = r;
  rt_ = 0;
  dur_ = kR[(int)r].dur;
  held_ = kR[(int)r].held;
  cueMask_ = 0;
  sideSign_ = rng_.sign();

  switch (r) {
    case Reaction::WakeUp: pushCue(Cue::Chirp); bounce_.v -= 4; break;
    case Reaction::Boop: pushCue(Cue::Click); bounce_.v -= 9; break;
    case Reaction::Hmph: pushCue(Cue::Hmm); break;
    case Reaction::Laugh: pushCue(Cue::Triplet); bounce_.v -= 6; break;
    case Reaction::Purr: pushCue(Cue::PurrOn); break;
    case Reaction::Dizzy: pushCue(Cue::Buzz); break;
    case Reaction::Scared: pushCue(Cue::Chirp); bounce_.v += 7; break;
    case Reaction::Yawn: pushCue(Cue::Yawn); break;
    case Reaction::Love: pushCue(Cue::DoubleChirp); bounce_.v -= 5; break;
    case Reaction::Birthday: pushCue(Cue::DoubleChirp); break;
    case Reaction::MissedYou: pushCue(Cue::DoubleChirp); break;
    case Reaction::Startle: pushCue(Cue::Click); bounce_.v += 6; break;
    case Reaction::Listen: pushCue(Cue::ListenOn); break;
    default: break;
  }
}

void Brain::release() {
  if (cur_ == Reaction::None || !held_) return;
  held_ = false;
  if (cur_ == Reaction::Purr) pushCue(Cue::PurrOff);
  if (cur_ == Reaction::Listen) pushCue(Cue::ListenOff);
  dur_ = rt_ + kR[(int)cur_].tail;
  if (kR[(int)cur_].tail <= 0) finish();
}

void Brain::finish() {
  const Reaction prev = cur_;
  cur_ = Reaction::None;
  rt_ = 0;
  held_ = false;
  if (prev == Reaction::Dizzy) {  // it didn't enjoy that
    mood_.valence -= 0.5f;
    mood_.grumpyFor = 10.0f;
  }
  if (prev == Reaction::GoodNight) {
    mode_ = Mode::Asleep;
    modeT_ = 0;
    asleepFor_ = 0;
  }
  if (prev == Reaction::Speak) tone_ = Tone::Neutral;
  if (queued_ != Reaction::None) {
    const Reaction q = queued_;
    queued_ = Reaction::None;
    start(q);
  }
}

bool Brain::rollRare(int idx, float p) {
  if (mem_.day >= 0 && mem_.rareDay[idx] == mem_.day) return false;  // once a day
  if (p_.favRare == idx) p *= 2.0f;
  if (!rng_.chance(p)) return false;
  mem_.rareDay[idx] = mem_.day;
  return true;
}

void Brain::afterInteraction(bool tap) {
  if (queued_ != Reaction::None) return;
  if (tap && mem_.boopsToday == 20 && mem_.loveDay != mem_.day) {
    mem_.loveDay = mem_.day;
    queued_ = Reaction::Love;  // the 20th boop of the day
    return;
  }
  if (rollRare(0, 1.0f / 50.0f)) queued_ = Reaction::Sneeze;
  else if (rollRare(1, 1.0f / 500.0f)) queued_ = Reaction::Hiccup;
  else if (rollRare(2, 1.0f / 5000.0f)) queued_ = Reaction::Love;
}

void Brain::wake(bool ceremony) {
  const bool wasDeep = mode_ == Mode::Asleep || mode_ == Mode::Off;
  mode_ = Mode::Awake;
  modeT_ = 0;
  if (!wasDeep) return;
  if (ceremony) start(Reaction::WakeUp);
  if (birthday_ && !birthdayShown_) {
    birthdayShown_ = true;
    queued_ = Reaction::Birthday;
  } else if (absenceH_ >= 4.0f) {
    queued_ = Reaction::MissedYou;
  } else if (morning() && asleepFor_ > 3.0f * 3600.0f) {
    queued_ = Reaction::Yawn;
  }
  absenceH_ = 0;
  asleepFor_ = 0;
}

void Brain::trigger(Reaction r) {
  lastInteractT_ = t_;
  if (mode_ != Mode::Awake) wake(false);
  if (cur_ != Reaction::None) {  // demo: always show what was asked for
    const Reaction q = queued_;
    queued_ = Reaction::None;
    cur_ = Reaction::None;
    queued_ = q;
  }
  start(r);
}

void Brain::event(Ev e) {
  if (isUserEvent(e)) {
    lastInteractT_ = t_;
    mood_.attention = clamp01(mood_.attention - 0.25f);
  }
  const bool deep = mode_ == Mode::Asleep || mode_ == Mode::Off;
  switch (e) {
    case Ev::Tap:
      if (deep) {  // a tap on a sleeping one wakes it, it's not a boop
        wake(true);
        break;
      }
      if (mode_ == Mode::Drowsy) wake(false);
      ++mem_.boopsTotal;
      ++mem_.boopsToday;
      tapBurst_ = (t_ - lastTapT_ < 3.0f) ? tapBurst_ + 1 : 1;
      lastTapT_ = t_;
      if (tapBurst_ >= 3 + (int)((1.0f - p_.shyness) * 3.0f)) {
        tapBurst_ = 0;
        start(Reaction::Shy);
      } else if (mood_.grumpyFor > 0 || mood_.valence < -0.35f) {
        start(Reaction::Hmph);
      } else {
        start(Reaction::Boop);
      }
      mood_.valence = clamp1(mood_.valence + 0.08f);
      mood_.energy = clamp1(mood_.energy + 0.05f);
      afterInteraction(true);
      break;
    case Ev::DoubleTap:
      if (promptActive_ && !deep) {  // deny the pending Claude request
        pushCue(Cue::ClaudeDeny);
        promptActive_ = approveHold_ = false;
        start(Reaction::Nope);
        break;
      }
      if (deep) {
        wake(true);
        break;
      }
      if (mode_ == Mode::Drowsy) wake(false);
      start(mood_.grumpyFor > 0 ? Reaction::Hmph : Reaction::Laugh);
      mood_.valence = clamp1(mood_.valence + 0.1f);
      afterInteraction(true);
      break;
    case Ev::HoldStart:
      if (mode_ != Mode::Awake) wake(false);
      if (promptActive_) {  // hold to approve (progress ring)
        approveHold_ = true;
        approveT_ = 0;
        break;
      }
      start(aiLink_ ? Reaction::Listen : Reaction::Purr);
      break;
    case Ev::HoldEnd:
      if (approveHold_) {  // let go too early: nothing is sent
        approveHold_ = false;
        approveT_ = 0;
        break;
      }
      if (cur_ == Reaction::Listen) {
        release();
        start(Reaction::Think);
      } else if (cur_ == Reaction::Purr) {
        release();
      }
      break;
    case Ev::StrokeStart:
      if (mode_ != Mode::Awake) wake(false);
      start(Reaction::Purr);
      mood_.valence = clamp1(mood_.valence + 0.15f);
      break;
    case Ev::StrokeEnd:
      if (cur_ == Reaction::Purr) release();
      break;
    case Ev::PickUp:
      if (mode_ != Mode::Awake) {
        wake(deep);
      } else {
        mood_.energy = clamp1(mood_.energy + 0.1f);
      }
      break;
    case Ev::Shake:
      wake(false);
      start(Reaction::Dizzy);
      break;
    case Ev::FreeFall:
      wake(false);
      start(Reaction::Scared);
      break;
    case Ev::Knock:
      if (deep) {
        wake(true);
      } else {
        if (mode_ == Mode::Drowsy) wake(false);
        start(Reaction::Startle);
      }
      break;
    case Ev::FaceDown:
      if (cur_ == Reaction::Listen || cur_ == Reaction::Speak) release();
      if (mode_ == Mode::Awake || mode_ == Mode::Drowsy) {
        mode_ = Mode::Awake;
        start(Reaction::GoodNight);
      }
      break;
    case Ev::FaceUp:
      if (mode_ == Mode::Off) wake(true);
      break;
    case Ev::UpsideDown:
      if (mode_ != Mode::Awake) wake(false);
      start(Reaction::Confused);
      break;
    case Ev::Upright:
      if (cur_ == Reaction::Confused) release();
      break;
    case Ev::AiThinking:
      if (cur_ != Reaction::Think) start(Reaction::Think);
      break;
    case Ev::AiSpeakStart:
      if (mode_ != Mode::Awake) wake(false);
      start(Reaction::Speak);
      break;
    case Ev::AiSpeakEnd:
      if (cur_ == Reaction::Speak) release();
      break;
    case Ev::ClaudeUp:
      if (mode_ == Mode::Awake) start(Reaction::Hello);
      break;
    case Ev::ClaudeDown:
      claudeBusy_ = promptActive_ = approveHold_ = false;
      break;
    case Ev::ClaudeBusyStart:
      claudeBusy_ = true;
      activityT_ = 0;
      break;
    case Ev::ClaudeBusyEnd:
      claudeBusy_ = false;
      break;
    case Ev::ClaudePrompt:
      promptActive_ = true;
      approveHold_ = false;
      activityT_ = 0;
      nudgeT_ = 0;
      if (mode_ != Mode::Awake) wake(false);  // it needs you: wake up
      pushCue(Cue::Nudge);
      bounce_.v += 6;
      break;
    case Ev::ClaudePromptGone:
      promptActive_ = approveHold_ = false;
      break;
    case Ev::ClaudeLevelUp:
      start(Reaction::Celebrate);
      break;
    case Ev::ClaudeQuickApprove:
      start(Reaction::Love);  // approved within 5 s: hearts
      break;
    case Ev::AlarmDue:  // an alarm rings: wake up, whatever the mode
      if (deep) wake(false);
      start(Reaction::Startle);
      break;
    case Ev::TextCommit:  // you wrote something: a little celebration
      if (deep) wake(false);
      start(Reaction::Celebrate);
      break;
    case Ev::TouchDown:  // raw touches belong to the text input, not the face
    case Ev::TouchMove:
    case Ev::TouchUp:
    case Ev::TextCancel:
    case Ev::None:
    case Ev::Count:
      break;
  }
}

// ---------------------------------------------------------------- update --

void Brain::updateMood(float dt, const Inputs& in) {
  (void)in;
  float base = 0.35f;
  if (hour_ >= 0) {
    if (night()) base = -0.6f;
    else if (hour_ < 9.0f) base = lerpf(-0.2f, 0.35f, (hour_ - 6.0f) / 3.0f);
    else if (hour_ >= 19.0f) base = lerpf(0.35f, -0.3f, (hour_ - 19.0f) / 3.0f);
  }
  mood_.energy += (base - mood_.energy) * dt / 90.0f;
  mood_.valence += (0.3f - mood_.valence) * dt / 240.0f;
  mood_.attention += (mode_ == Mode::Awake ? dt / 600.0f : -dt / 1200.0f);
  mood_.energy = clamp1(mood_.energy);
  mood_.valence = clamp1(mood_.valence);
  mood_.attention = clamp01(mood_.attention);
  if (mood_.grumpyFor > 0) mood_.grumpyFor -= dt;
}

void Brain::updateIdle(float dt, const Inputs& in) {
  (void)in;
  // blinking
  if (blinkT_ >= 0) {
    blinkT_ += dt;
    if (blinkT_ > blinkDur_) blinkT_ = -1;
  } else if (t_ >= nextBlink_ && (mode_ == Mode::Awake || mode_ == Mode::Drowsy)) {
    blinkT_ = 0;
    blinkDur_ = mode_ == Mode::Drowsy ? 0.35f : (mood_.energy < -0.3f ? 0.22f : 0.13f);
    const float gap = rng_.range(p_.blinkMin, p_.blinkMax) * (mood_.energy < -0.3f ? 1.4f : 1.0f);
    nextBlink_ = t_ + (rng_.chance(0.12f) ? 0.3f : gap);  // sometimes a double blink
  }
  // glances (saccades)
  if (t_ >= nextSaccade_) {
    const float act = 0.5f * (mood_.energy + 1.0f);
    const float interval = lerpf(3.8f, 1.0f, p_.curiosity * 0.6f + act * 0.4f) * rng_.range(0.6f, 1.4f);
    nextSaccade_ = t_ + interval;
    if (rng_.chance(0.3f)) {  // back to you
      gazeTX_ = 0;
      gazeTY_ = 0;
    } else {
      const float rx = 0.35f + 0.45f * p_.curiosity;
      gazeTX_ = rng_.range(-rx, rx);
      gazeTY_ = rng_.range(-0.35f, 0.45f);
    }
    if (fabsf(gazeTX_ - gx_.x) > 0.6f && blinkT_ < 0 && rng_.chance(0.35f)) {
      blinkT_ = 0;
      blinkDur_ = 0.13f;
    }
  }
}

void Brain::update(float dt, const Inputs& in) {
  if (dt <= 0) return;
  if (dt > 0.5f) dt = 0.5f;
  t_ += dt;
  hour_ = in.hour;
  audio_ = clamp01(in.audioLevel);
  knockX_ = in.knockX;
  knockY_ = in.knockY;
  updateMood(dt, in);

  modeT_ += dt;
  switch (mode_) {
    case Mode::Awake: {
      const float sleepAfter = night() ? 12.0f : p_.sleepAfterSeconds();
      if (cur_ == Reaction::None && queued_ == Reaction::None && in.stillFor > sleepAfter &&
          t_ - lastInteractT_ > sleepAfter) {
        mode_ = Mode::Drowsy;
        modeT_ = 0;
      }
      break;
    }
    case Mode::Drowsy:
      if (in.stillFor < 0.5f || cur_ != Reaction::None) {
        mode_ = Mode::Awake;
        modeT_ = 0;
        blinkT_ = 0;  // "hm? I'm awake"
      } else if (modeT_ > 6.0f) {
        mode_ = Mode::Asleep;
        modeT_ = 0;
        asleepFor_ = 0;
      }
      break;
    case Mode::Asleep:
      asleepFor_ += dt;
      if (in.faceDown && modeT_ > 8.0f) {
        mode_ = Mode::Off;
        modeT_ = 0;
      }
      break;
    case Mode::Off:
      asleepFor_ += dt;
      break;
  }

  if (cur_ != Reaction::None) {
    rt_ += dt;
    if (!held_ && rt_ >= dur_) finish();
  }

  activityT_ += dt;
  if (promptActive_ || claudeBusy_) lastInteractT_ = t_;  // stays awake while Claude works
  if (approveHold_) {
    approveT_ += dt;
    if (approveT_ >= kApproveHoldS) {
      approveHold_ = false;
      promptActive_ = false;
      pushCue(Cue::ClaudeApprove);
      pushCue(Cue::Click);
      start(Reaction::Boop);
    }
  }
  if (promptActive_ && mode_ == Mode::Awake) {
    nudgeT_ += dt;
    if (nudgeT_ > 8.0f) {  // gentle reminder, never nagging faster than this
      nudgeT_ = 0;
      pushCue(Cue::Nudge);
      bounce_.v += 4;
    }
  }

  lonelyCool_ -= dt;
  if (mode_ == Mode::Awake && cur_ == Reaction::None && mood_.attention > 0.85f &&
      in.stillFor < 2.0f && lonelyCool_ <= 0) {
    start(Reaction::Lonely);
    lonelyCool_ = 600.0f;
  }

  updateIdle(dt, in);
  compose(in, dt);
}

// --------------------------------------------------------------- compose --

void Brain::applyReaction(Face& f, float rt, float& tx, float& ty) {
  Eye* eyes[2] = {&f.L, &f.R};
  const float tail = kR[(int)cur_].tail;
  // 0..1 envelope for held reactions: fade in, hold, fade out after release
  const float heldK = held_ ? ramp(rt, 0, 0.3f) : 1.0f - ramp(rt, dur_ - tail, dur_);

  switch (cur_) {
    case Reaction::None:
      break;

    case Reaction::WakeUp: {
      f.bright *= 0.15f + 0.85f * ramp(rt, 0, 0.7f);
      const float op = lerpf(0.08f, 1.0f, ramp(rt, 0.1f, 0.9f));
      const float bl = bump(rt, 1.05f, 1.12f, 1.16f, 1.3f);
      for (Eye* e : eyes) e->open *= op * (1.0f - 0.9f * bl);
      if (rt > 0.9f && rt < 1.3f) {
        tx = -0.6f * sideSign_;
        ty = -0.1f;
      } else if (rt >= 1.3f && rt < 1.6f) {
        tx = 0.6f * sideSign_;
        ty = -0.1f;
      } else {
        tx = ty = 0;
      }
      break;
    }

    case Reaction::Boop:
      f.happy = bump(rt, 0, 0.08f, 1.05f, 1.35f);
      f.blush = 0.7f * bump(rt, 0, 0.15f, 1.0f, 1.4f);
      f.overlays |= ov::Hearts;
      f.overlayT = rt;
      tx = ty = 0;
      break;

    case Reaction::Hmph: {
      const float k = bump(rt, 0, 0.2f, 1.2f, 1.6f);
      for (Eye* e : eyes) {
        e->lidTop += 0.3f * k;
        e->lidTilt += 0.25f * k;
        e->open *= 1.0f - 0.1f * k;
      }
      tx = 0.85f * sideSign_;
      ty = -0.15f;
      break;
    }

    case Reaction::Laugh: {
      const float k = bump(rt, 0, 0.08f, 1.4f, 1.8f);
      f.style = EyeStyle::Squeeze;
      f.styleAmt = bump(rt, 0.0f, 0.06f, 1.0f, 1.2f);
      f.happy = bump(rt, 0.95f, 1.15f, 1.5f, 1.8f);
      const float jig = 0.014f * sinf(rt * 2 * kPi * 9) * k;
      for (Eye* e : eyes) e->dy += jig;
      f.blush = 0.5f * k;
      tx = ty = 0;
      break;
    }

    case Reaction::Shy: {
      const float k = bump(rt, 0, 0.35f, 2.4f, 3.0f);
      for (Eye* e : eyes) {
        e->open *= 1.0f - 0.35f * k;
        e->lidTop += 0.08f * k;
        e->lidTilt -= 0.2f * k;
      }
      f.blush = k;
      tx = 0.3f * sideSign_;
      ty = 0.85f;
      break;
    }

    case Reaction::Purr: {
      f.happy = heldK;
      f.blush = 0.45f * heldK;
      const float br = 1.0f + 0.04f * sinf(rt * 2 * kPi / 2.2f) * heldK;
      for (Eye* e : eyes) e->sy *= br;
      tx = 0;
      ty = 0.1f;
      break;
    }

    case Reaction::Dizzy: {
      const float k = bump(rt, 0, 0.15f, 3.0f, 3.5f);
      f.style = EyeStyle::Spiral;
      f.styleAmt = k;
      f.spin = rt * 7.0f;
      f.overlays |= ov::Orbit;
      f.overlayT = rt;
      f.L.dx += 0.02f * cosf(rt * 5.0f) * k;
      f.R.dx += 0.02f * cosf(rt * 5.0f + 1.0f) * k;
      tx = ty = 0;
      break;
    }

    case Reaction::Scared: {
      const float k = bump(rt, 0, 0.06f, 1.1f, 1.6f);
      for (Eye* e : eyes) {
        e->scale *= 1.0f + 0.16f * k;
        e->lidTop = lerpf(e->lidTop, 0.0f, k);
        e->lidTilt *= 1.0f - k;
      }
      f.overlays |= ov::Sweat;
      f.overlayT = rt;
      f.happy = 0.6f * bump(rt, 1.2f, 1.35f, 1.45f, 1.6f);  // phew
      tx = 0;
      ty = -0.3f * k;
      break;
    }

    case Reaction::Confused: {
      const float k = heldK;
      f.L.open *= 1.0f + 0.18f * k;
      f.R.open *= 1.0f - 0.3f * k;
      f.L.lidTop *= 1.0f - 0.6f * k;
      f.L.dy -= 0.02f * k;  // head tilt
      f.R.dy += 0.02f * k;
      f.overlays |= ov::Question;
      f.overlayT = rt;
      tx = 0.2f;
      ty = -0.6f * k;
      break;
    }

    case Reaction::Yawn: {
      const float m = bump(rt, 0.3f, 0.9f, 1.6f, 2.1f);
      f.overlays |= ov::Yawn;
      f.mouth = m;
      for (Eye* e : eyes) {
        e->open *= 1.0f - 0.75f * m;
        e->dy -= 0.015f * m;
      }
      tx = 0;
      ty = -0.2f * m;
      break;
    }

    case Reaction::Sneeze: {
      const float build = ramp(rt, 0.0f, 0.85f);
      if (rt < 0.9f) {  // a-a-a...
        for (Eye* e : eyes) {
          e->open *= 1.0f - 0.45f * build;
          e->lidTop += 0.1f * build;
          e->dy += 0.004f * sinf(rt * 60.0f) * build;
        }
        ty = -0.5f * build;
        tx = 0;
      } else {
        tx = ty = 0;
      }
      f.style = EyeStyle::Squeeze;
      f.styleAmt = bump(rt, 0.8f, 0.9f, 1.15f, 1.3f);
      if (rt >= 0.9f && !(cueMask_ & 1)) {  // ...CHOO
        cueMask_ |= 1;
        pushCue(Cue::Sneeze);
        bounce_.v += 10;
      }
      const float wide = bump(rt, 1.3f, 1.4f, 1.7f, 1.9f);
      for (Eye* e : eyes) e->scale *= 1.0f + 0.1f * wide;
      break;
    }

    case Reaction::Hiccup: {
      const float hops[3] = {0.25f, 1.1f, 2.0f};
      for (int i = 0; i < 3; ++i) {
        const float h = hops[i];
        const float b = bump(rt, h, h + 0.05f, h + 0.12f, h + 0.3f);
        for (Eye* e : eyes) {
          e->dy -= 0.035f * b;
          e->open *= 1.0f + 0.15f * b;
        }
        if (rt >= h && !(cueMask_ & (1 << i))) {
          cueMask_ |= (uint8_t)(1 << i);
          pushCue(Cue::Hic);
          bounce_.v += 5;
        }
      }
      for (Eye* e : eyes) e->lidTop *= 0.6f;
      break;
    }

    case Reaction::Love: {
      const float k = bump(rt, 0, 0.2f, 2.3f, 2.8f);
      f.style = EyeStyle::Heart;
      f.styleAmt = k;
      f.overlayT = rt;
      f.blush = 0.8f * k;
      f.overlays |= ov::Hearts;
      tx = ty = 0;
      break;
    }

    case Reaction::Birthday: {
      const float k = bump(rt, 0, 0.3f, 3.8f, 4.5f);
      f.style = EyeStyle::Star;
      f.styleAmt = k;
      f.spin = rt * 1.5f;
      f.overlays |= ov::Confetti;
      f.overlayT = rt;
      tx = ty = 0;
      break;
    }

    case Reaction::MissedYou: {
      const float k = bump(rt, 0, 0.1f, 2.7f, 3.2f);
      f.happy = k;
      f.blush = k;
      f.overlays |= ov::Hearts;
      f.overlayT = fmodf(rt, 1.6f);
      const float hops[3] = {0.0f, 0.6f, 1.2f};
      for (int i = 0; i < 3; ++i) {
        if (rt >= hops[i] && !(cueMask_ & (1 << i))) {
          cueMask_ |= (uint8_t)(1 << i);
          bounce_.v -= 7;
        }
      }
      tx = ty = 0;
      break;
    }

    case Reaction::Lonely: {
      if (rt < 2.6f) {  // looking for you
        tx = sinf(rt * 2.4f) * 0.8f;
        ty = -0.1f;
      } else {
        tx = 0;
        ty = 0.35f;
      }
      const float sad = bump(rt, 2.6f, 3.0f, 4.0f, 4.5f);
      for (Eye* e : eyes) {
        e->lidTilt -= 0.45f * sad;
        e->lidTop += 0.15f * sad;
      }
      break;
    }

    case Reaction::Startle: {
      const float shut = bump(rt, 0, 0.03f, 0.06f, 0.1f);
      const float k = bump(rt, 0.08f, 0.14f, 0.8f, 1.2f);
      for (Eye* e : eyes) {
        e->open *= 1.0f - 0.9f * shut;
        e->scale *= 1.0f + 0.14f * k;
        e->lidTop *= 1.0f - k;
      }
      tx = clamp1(knockX_ * 0.9f);
      ty = clamp1(-knockY_ * 0.9f);  // device +Y is up, screen +y is down
      break;
    }

    case Reaction::GoodNight:
      f.happy = bump(rt, 0, 0.2f, 0.9f, 1.3f);
      f.style = EyeStyle::Closed;
      f.styleAmt = ramp(rt, 1.1f, 1.6f);
      f.bright *= 1.0f - 0.5f * ramp(rt, 1.2f, 2.2f);
      tx = ty = 0;
      break;

    case Reaction::Listen: {
      const float k = ramp(rt, 0, 0.25f);
      for (Eye* e : eyes) {
        e->scale *= 1.0f + 0.06f * k;
        e->lidTop = lerpf(e->lidTop, 0.04f, k);
        e->lidTilt *= 1.0f - 0.7f * k;
        e->dy -= 0.01f * audio_;  // tiny nods on loud syllables
      }
      f.overlays |= ov::Listen;
      f.overlayT = rt;
      f.level = audio_;
      tx = 0;
      ty = -0.05f;
      break;
    }

    case Reaction::Think:
      for (Eye* e : eyes) e->lidTop += 0.08f;
      f.overlays |= ov::Think;
      f.overlayT = rt;
      tx = -0.55f * sideSign_;
      ty = -0.6f;
      break;

    case Reaction::Speak: {
      const float k = heldK;
      const float a = audio_ * k;
      for (Eye* e : eyes) {
        e->sy *= 1.0f + 0.10f * a;
        e->dy -= 0.012f * a;
      }
      switch (tone_) {
        case Tone::Happy:  // smiling eyes: the lower lid pushes up
          for (Eye* e : eyes) e->lidBot = 0.22f * k;
          f.blush = 0.3f * k;
          break;
        case Tone::Sad:
          for (Eye* e : eyes) {
            e->lidTilt -= 0.35f * k;
            e->lidTop += 0.1f * k;
          }
          ty = 0.3f;
          break;
        case Tone::Surprised:
          for (Eye* e : eyes) {
            e->scale *= 1.0f + 0.1f * k;
            e->lidTop = lerpf(e->lidTop, 0.03f, k);
          }
          break;
        case Tone::Cheeky:
          for (Eye* e : eyes) {
            e->lidTilt += 0.15f * k;
            e->lidTop += 0.1f * k;
          }
          tx = 0.35f * sideSign_;
          break;
        case Tone::Sleepy:
          for (Eye* e : eyes) e->open *= 1.0f - 0.4f * k;
          break;
        case Tone::Love:
          for (Eye* e : eyes) e->lidBot = 0.18f * k;
          f.blush = 0.8f * k;
          break;
        case Tone::Neutral:
          break;
      }
      break;
    }

    case Reaction::Hello: {
      f.happy = bump(rt, 0, 0.1f, 1.0f, 1.4f);
      if (rt < 0.05f && !(cueMask_ & 1)) {
        cueMask_ |= 1;
        bounce_.v -= 6;
      }
      tx = ty = 0;
      break;
    }

    case Reaction::Celebrate: {
      const float k = bump(rt, 0, 0.1f, 2.5f, 3.0f);
      f.happy = k;
      f.overlays |= ov::Confetti;
      f.overlayT = rt;
      const float hops[3] = {0.0f, 0.5f, 1.0f};
      for (int i = 0; i < 3; ++i) {
        if (rt >= hops[i] && !(cueMask_ & (1 << i))) {
          cueMask_ |= (uint8_t)(1 << i);
          bounce_.v -= 7;
        }
      }
      tx = ty = 0;
      break;
    }

    case Reaction::Nope: {
      const float k = bump(rt, 0, 0.1f, 0.9f, 1.2f);
      tx = 0.7f * sinf(rt * 2.0f * kPi * 2.5f) * k;
      ty = 0.1f;
      for (Eye* e : eyes) e->lidTop += 0.12f * k;
      break;
    }

    case Reaction::Count:
      break;
  }
}

void Brain::compose(const Inputs& in, float dt) {
  Face f;
  f.spacing = p_.spacing;
  f.eyeW = p_.eyeW;
  f.eyeH = p_.eyeH;
  f.color = night() ? p_.eyeNight : p_.eyeDay;
  const float e = mood_.energy, v = mood_.valence;
  float lidTop = 0.19f + 0.2f * fmaxf(0, -e) - 0.07f * fmaxf(0, v - 0.5f);
  float tilt = p_.lidTilt + 0.3f * fmaxf(0, -v) - 0.1f * fmaxf(0, v - 0.5f);
  if (mood_.grumpyFor > 0) {
    lidTop += 0.12f;
    tilt += 0.18f;
  }
  for (Eye* eye : {&f.L, &f.R}) {
    eye->lidTop = lidTop;
    eye->lidTilt = tilt;
    eye->scale = 1.0f + 0.04f * e;
  }
  f.glow = 0.85f + 0.15f * fmaxf(0, e);
  f.bright = night() ? 0.8f : 1.0f;

  float tx = gazeTX_ + in.tiltX * 0.6f;
  float ty = gazeTY_ + in.tiltY * 0.6f;

  applyReaction(f, rt_, tx, ty);

  if (cur_ == Reaction::None && mode_ == Mode::Awake) {
    if (promptActive_) {  // Claude needs a decision: wide eyes on you
      for (Eye* eye : {&f.L, &f.R}) {
        eye->lidTop = 0.04f;
        eye->lidTilt *= 0.3f;
        eye->scale *= 1.08f;
      }
      f.overlays |= ov::Alert;
      f.overlayT = activityT_;
      tx = 0.12f * sinf(activityT_ * 0.9f);
      ty = -0.05f;
    } else if (claudeBusy_) {  // Claude is working: focused, reading lines
      for (Eye* eye : {&f.L, &f.R}) {
        eye->lidTop += 0.12f;
        eye->lidTilt += 0.08f;
      }
      const float line = fmodf(activityT_ * 0.55f, 1.0f);
      tx = line < 0.85f ? lerpf(-0.55f, 0.55f, line / 0.85f) : lerpf(0.55f, -0.55f, (line - 0.85f) / 0.15f);
      ty = 0.3f;
      if (fmodf(activityT_, 9.0f) > 7.5f) {
        f.overlays |= ov::Sweat;
        f.overlayT = activityT_;
      }
    }
  }
  if (approveHold_) {
    f.overlays |= ov::Progress;
    f.progress = approveT_ / kApproveHoldS;
  }

  if (cur_ == Reaction::None) {
    switch (mode_) {
      case Mode::Drowsy: {
        const float k = ramp(modeT_, 0, 6.0f);
        for (Eye* eye : {&f.L, &f.R}) {
          eye->open *= lerpf(1.0f, 0.15f, k);
          eye->lidTop += 0.1f * k;
        }
        f.bright *= lerpf(1.0f, 0.7f, k);
        tx *= 1.0f - k;
        ty = lerpf(ty, 0.3f, k);
        break;
      }
      case Mode::Asleep:
        f.style = EyeStyle::Closed;
        f.styleAmt = 1.0f;
        f.overlays |= ov::Zzz;
        f.overlayT = modeT_;
        f.bright *= night() ? 0.35f : 0.5f;
        tx = 0;
        ty = 0.3f;
        break;
      case Mode::Off:
        f.bright = 0;
        break;
      case Mode::Awake:
        break;
    }
  }

  // springs: glances with a touch of overshoot, squash & stretch
  gx_.step(clamp1(tx), dt, 26.0f, 0.62f);
  gy_.step(clamp1(ty), dt, 26.0f, 0.62f);
  bounce_.step(0.0f, dt, 18.0f, 0.35f);
  f.gx = clamp1(gx_.x);
  f.gy = clamp1(gy_.x);

  // blink (only the normal eye shape is affected)
  if (blinkT_ >= 0) {
    const float p = blinkT_ / blinkDur_;
    const float c = p < 0.4f ? p / 0.4f : 1.0f - (p - 0.4f) / 0.6f;
    for (Eye* eye : {&f.L, &f.R}) eye->open *= 1.0f - 0.95f * clamp01(c);
  }
  // breathing: 2 % on a 4 s cycle awake, slower asleep
  const float period = mode_ == Mode::Asleep ? 6.0f : 4.0f;
  const float br = 1.0f + 0.02f * sinf(t_ * 2 * kPi / period);
  // bounce: squash when pressed, stretch on the rebound
  const float b = bounce_.x * 0.12f;
  for (Eye* eye : {&f.L, &f.R}) {
    eye->sy *= br * (1.0f - 0.16f * b);
    eye->sx *= 1.0f + 0.10f * b;
    eye->dy += 0.02f * b;
  }

  // body light (LEDs in the frosted core; the sim draws it as a halo)
  BodyLight bl{Rgb(), 0};
  switch (cur_) {
    case Reaction::Boop:
    case Reaction::Love:
    case Reaction::MissedYou:
      bl = {Rgb::hex(0xFFB8C8), 0.25f};
      break;
    case Reaction::Shy:
      bl = {Rgb::hex(0xFF7FA0), 0.28f + 0.05f * sinf(rt_ * 4)};
      break;
    case Reaction::Purr:
      bl = {Rgb::hex(0xFFB8A0), (0.18f + 0.06f * sinf(rt_ * 2.8f))};
      break;
    case Reaction::Dizzy:
      bl = {pal::kMint, 0.12f + 0.08f * sinf(rt_ * 9)};
      break;
    case Reaction::Scared:
    case Reaction::Startle:
      bl = {pal::kWhite, 1.0f - ramp(rt_, 0, 0.5f)};
      break;
    case Reaction::Laugh:
      bl = {pal::kWhite, (rt_ < 0.12f || (rt_ > 0.25f && rt_ < 0.37f)) ? 0.8f : 0.05f};
      break;
    case Reaction::Birthday:
      bl = {hsv(rt_ * 0.5f, 0.6f, 1.0f), 0.5f};
      break;
    case Reaction::WakeUp:
      bl = {Rgb::lerp(Rgb::hex(0xFF8A3D), Rgb::hex(0xFFF3D6), ramp(rt_, 0, 1.8f)), 0.1f + 0.3f * ramp(rt_, 0, 1.2f)};
      break;
    case Reaction::Listen:
      bl = {pal::kIce, 0.25f + 0.5f * audio_};
      break;
    case Reaction::Think:
      bl = {pal::kIce, 0.15f + 0.1f * sinf(rt_ * 5)};
      break;
    case Reaction::Speak:
      bl = {pal::kIce, 0.15f + 0.4f * audio_};
      break;
    case Reaction::Celebrate:
      bl = {hsv(rt_ * 0.8f, 0.6f, 1.0f), 0.5f};
      break;
    default:
      if (promptActive_ && mode_ == Mode::Awake) bl = {Rgb::hex(0xFFB347), 0.25f + 0.25f * sinf(activityT_ * 5)};
      else if (claudeBusy_ && mode_ == Mode::Awake) bl = {pal::kIce, 0.12f + 0.06f * sinf(activityT_ * 2)};
      else if (mode_ == Mode::Asleep && night()) bl = {Rgb::hex(0xFFB070), 0.38f};  // night light
      else if (mode_ == Mode::Drowsy) bl = {Rgb::hex(0xFFB070), 0.08f};
      break;
  }
  if (bl.level < 0) bl.level = 0;
  if (mode_ == Mode::Off) bl.level = 0;
  body_ = bl;
  face_ = f;
}

}  // namespace suflet
