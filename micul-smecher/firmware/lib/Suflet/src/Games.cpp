// Three tiny games: rules and physics. See Games.h.
#include "Games.h"

#include <math.h>

namespace suflet {
namespace games {

// ------------------------------------------------------------ tilt ball ---

void TiltBall::start(uint32_t seed) {
  r_.s = seed ? seed : 1;
  x_ = y_ = vx_ = vy_ = 0;
  score_ = 0;
  lives_ = 3;
  left_ = kTime;
  safe_ = 1.0f;
  run_ = true;
  over_ = false;
  holes_.clear();
  for (int i = 0; i < 2; ++i) {
    const float a = r_.uniform(0, 6.2831853f) + i * 3.14159f, rr = r_.uniform(95, 140);
    holes_.push_back({rr * cosf(a), rr * sinf(a)});
  }
  placeStar();
}

void TiltBall::placeStar() {
  for (int k = 0; k < 40; ++k) {
    const float a = r_.uniform(0, 6.2831853f), rr = r_.uniform(40, kArena - kStar - 12);
    const float sx = rr * cosf(a), sy = rr * sinf(a);
    bool ok = hypotf(sx - x_, sy - y_) > 90;
    for (const Hole& h : holes_)
      if (hypotf(sx - h.x, sy - h.y) < kHole + kStar + 18) ok = false;
    if (ok) {
      star_ = {sx, sy};
      return;
    }
  }
  star_ = {-x_ * 0.5f, -y_ * 0.5f};
}

float TiltBall::speed() const { return hypotf(vx_, vy_); }

uint8_t TiltBall::step(float dt, float gx, float gy) {
  if (!run_) return None;
  uint8_t ev = None;
  if (dt > 0.05f) dt = 0.05f;
  left_ -= dt;
  if (safe_ > 0) safe_ -= dt;
  // a rolling marble: the screen-plane gravity accelerates it, rolling friction slows it
  const float G = 1150.0f;  // design px / s^2 per g (a marble rolls at 5/7 g; tuned for a 45 mm disc)
  vx_ += gx * G * dt;
  vy_ += gy * G * dt;
  const float drag = expf(-0.9f * dt);
  vx_ *= drag;
  vy_ *= drag;
  x_ += vx_ * dt;
  y_ += vy_ * dt;
  // the rim: reflect the radial part with some loss
  const float R = kArena - kBall, d = hypotf(x_, y_);
  if (d > R) {
    const float nx = x_ / d, ny = y_ / d, vn = vx_ * nx + vy_ * ny;
    if (vn > 0) {
      vx_ -= 1.55f * vn * nx;  // restitution 0.55
      vy_ -= 1.55f * vn * ny;
      if (vn > 60) ev |= Bump;
    }
    x_ = nx * R;
    y_ = ny * R;
  }
  if (hypotf(x_ - star_.x, y_ - star_.y) < kBall + kStar - 2) {
    ++score_;
    ev |= Got;
    placeStar();
  }
  if (safe_ <= 0)
    for (const Hole& h : holes_)
      if (hypotf(x_ - h.x, y_ - h.y) < kHole - kBall * 0.3f) {
        --lives_;
        ev |= Fell;
        x_ = y_ = vx_ = vy_ = 0;
        safe_ = 1.0f;
        break;
      }
  if (left_ <= 0 || lives_ <= 0) {
    if (left_ < 0) left_ = 0;
    run_ = false;
    over_ = true;
    ev |= Over;
  }
  return ev;
}

// --------------------------------------------------------------- rhythm ---

void Rhythm::start(uint32_t seed, float bpm) {
  Rand r;
  r.s = seed ? seed : 7;
  beats_.clear();
  done_.clear();
  const float beat = 60.0f / bpm;
  float t = kTravel + 0.6f;
  while ((int)beats_.size() < kBeats) {
    beats_.push_back(t);
    // mostly quarter notes, some eighths, an occasional rest
    const uint32_t k = r.next() % 10;
    t += k < 6 ? beat : k < 9 ? beat * 0.5f : beat * 1.5f;
  }
  done_.assign(beats_.size(), 0);
  t_ = 0;
  score_ = combo_ = bestCombo_ = perfects_ = misses_ = 0;
  run_ = true;
  over_ = false;
  last_ = NoBeat;
}

int Rhythm::step(float dt) {
  if (!run_) return 0;
  t_ += dt;
  int missed = 0;
  for (size_t i = 0; i < beats_.size(); ++i)
    if (!done_[i] && t_ > beats_[i] + kGood) {
      done_[i] = 1;
      ++missed;
      ++misses_;
      combo_ = 0;
      last_ = Miss;
    }
  if (t_ > beats_.back() + 1.0f) {
    run_ = false;
    over_ = true;
  }
  return missed;
}

Rhythm::Judge Rhythm::tap() {
  if (!run_) return NoBeat;
  int best = -1;
  float bd = 1e9f;
  for (size_t i = 0; i < beats_.size(); ++i) {
    if (done_[i]) continue;
    const float d = fabsf(t_ - beats_[i]);
    if (d < bd) {
      bd = d;
      best = (int)i;
    }
  }
  if (best < 0 || bd > 0.35f) return NoBeat;  // nothing near: a stray tap costs nothing
  done_[best] = 1;
  if (bd <= kPerfect) {
    score_ += 100 + 10 * combo_;
    ++combo_;
    ++perfects_;
    last_ = Perfect;
  } else if (bd <= kGood) {
    score_ += 50 + 5 * combo_;
    ++combo_;
    last_ = Good;
  } else {
    combo_ = 0;
    ++misses_;
    last_ = Miss;
  }
  if (combo_ > bestCombo_) bestCombo_ = combo_;
  return last_;
}

int Rhythm::visible(float* fr, int max) const {
  int n = 0;
  for (size_t i = 0; i < beats_.size() && n < max; ++i) {
    if (done_[i]) continue;
    const float f = 1.0f - (beats_[i] - t_) / kTravel;
    if (f >= 0 && f <= 1.1f) fr[n++] = f;
  }
  return n;
}

// ----------------------------------------------------------- eye memory ---

void EyeMemory::start(uint32_t seed) {
  r_.s = seed ? seed : 3;
  seq_.clear();
  score_ = 0;
  grow();
}

void EyeMemory::grow() {
  uint8_t k = (uint8_t)(r_.next() % kSpots);
  if (seq_.size() >= 2 && seq_[seq_.size() - 1] == k && seq_[seq_.size() - 2] == k) k = (uint8_t)((k + 1) % kSpots);
  seq_.push_back(k);
  pos_ = 0;
  t_ = -0.6f;  // a breath before the show
  phase_ = Phase::Show;
}

void EyeMemory::step(float dt) {
  if (phase_ != Phase::Show) return;
  t_ += dt;
  if (t_ >= seq_.size() * (kOn + kGap)) phase_ = Phase::Input;
}

int EyeMemory::cue() const {
  if (phase_ != Phase::Show || t_ < 0) return -1;
  const int i = (int)(t_ / (kOn + kGap));
  if (i >= (int)seq_.size()) return -1;
  return fmodf(t_, kOn + kGap) < kOn ? seq_[i] : -1;
}

bool EyeMemory::input(int spot) {
  if (phase_ != Phase::Input) return false;
  if (spot != seq_[pos_]) {
    phase_ = Phase::Over;
    return false;
  }
  if (++pos_ >= (int)seq_.size()) {
    score_ = (int)seq_.size();
    grow();
  }
  return true;
}

int EyeMemory::spotAt(float dx, float dy) {
  if (fabsf(dx) > fabsf(dy)) return dx > 0 ? 1 : 3;
  return dy > 0 ? 2 : 0;
}

}  // namespace games
}  // namespace suflet
