#include "EyeMotion.h"

#include <math.h>

#include "EyeRig.h"

namespace suflet {
namespace eyes {

static constexpr float kPi = 3.14159265f;
static constexpr float kTau = 6.28318531f;

static inline float clampf_(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
static inline float smoothf(float t) {
  t = clampf_(t, 0, 1);
  return t * t * (3 - 2 * t);
}
static inline float approach(float v, float t, float rate, float dt) { return v + (t - v) * (1 - expf(-rate * dt)); }

const char* motionCueName(MotionCue c) {
  static const char* const kNames[] = {"None",       "DizzyStart", "Ufff",   "OnBack", "FaceDown", "FaceUp",
                                       "UpsideDown", "Upright",    "Calm",   "TapTap", "NodYes",   "NodNo"};
  static_assert(sizeof(kNames) / sizeof(kNames[0]) == (unsigned)MotionCue::Count, "cue names");
  const unsigned i = (unsigned)c;
  return i < (unsigned)MotionCue::Count ? kNames[i] : "?";
}

float wrapPi(float a) {
  a = fmodf(a + kPi, kTau);
  if (a <= 0) a += kTau;
  return a - kPi;
}

float levelAngle(float gx, float gy, float gz, float* weight) {
  const float planar = sqrtf(gx * gx + gy * gy), n = sqrtf(gx * gx + gy * gy + gz * gz);
  if (weight) *weight = smoothf((planar / (n > 1e-6f ? n : 1e-6f) - 0.3f) / 0.3f);
  return atan2f(gx, gy);
}

float softClampRoll(float a) {
  const float k0 = 2.0943951f, L = 2.6179939f;  // 120 deg linear, 150 deg max
  const float m = fabsf(a);
  if (m <= k0) return a;
  const float u = clampf_((m - k0) / (kPi - k0), 0, 1);
  const float v = k0 + (L - k0) * (1 - (1 - u) * (1 - u));  // slope 1 at 120 deg, 0 at 180
  return a < 0 ? -v : v;
}

// ------------------------------------------------------------- taps ---

bool TapDetector::update(float hp, float dt, bool busy) {
  since1_ += dt;
  since2_ += dt;
  if (busy) {
    n_ = 0;
    above_ = false;
    return false;
  }
  if (!above_) {
    if (hp > tapG) {
      above_ = true;
      aboveT_ = 0;
    }
  } else {
    aboveT_ += dt;
    if (hp < tapG * 0.5f) {  // the spike is over: was it a tap?
      above_ = false;
      if (aboveT_ <= maxTapS) {
        const float gap = since1_ - aboveT_;  // from the first tap's start to this one's
        if (n_ == 1 && gap < minGapS) {
          // the same tap ringing
        } else if (n_ == 1 && gap <= maxGapS) {
          n_ = 2;
          since2_ = aboveT_;
        } else if (n_ == 2) {
          n_ = 0;  // a third: handling, not a double tap
        } else {
          n_ = 1;
          since1_ = aboveT_;
        }
      } else {
        n_ = 0;  // a long push
      }
    }
  }
  if (n_ == 1 && since1_ > maxGapS + maxTapS) n_ = 0;
  if (n_ == 2 && !above_ && since2_ >= quietS) {
    n_ = 0;
    return true;
  }
  return false;
}

// ------------------------------------------------------------- nods ---

int NodDetector::update(float gx, float gy, float gz, float dt) {
  cool_ -= dt;
  const float r[2] = {gx, fabsf(gy) > fabsf(gz) ? gy : gz};
  const float o[2] = {fmaxf(fabsf(gy), fabsf(gz)), fabsf(gx)};
  for (int c = 0; c < 2; ++c) {
    age_[c] += dt;
    span_[c] += dt;
    const float a = fabsf(r[c]);
    const int sg = r[c] > 0 ? 1 : -1;
    if (in_[c] && (a < rate * 0.4f || sg != last_[c])) in_[c] = false;  // the swing is over (or turned)
    if (!in_[c] && a > rate && a > dom * o[c]) {
      in_[c] = true;
      if (n_[c] == 0 || age_[c] > gapS || sg == last_[c]) {
        n_[c] = 1;
        span_[c] = 0;
      } else {
        ++n_[c];
      }
      last_[c] = sg;
      age_[c] = 0;
      if (n_[c] >= swings && span_[c] <= windowS && cool_ <= 0) {
        n_[0] = n_[1] = 0;
        cool_ = coolS;
        return c == 0 ? 1 : -1;
      }
    }
  }
  return 0;
}

void SpinMeter::update(float w, float dt) {
  level += fmaxf(0, w - dead) * dt;
  level -= level * dt / (tau + dt);
}

// --------------------------------------------------------- pose IMU ---

ImuSample PoseImu::sample(float roll, float pitch, float yaw, float dt) {
  // M = Ry(yaw) * Rx(pitch) * Rz(roll); world: X right, Y up, Z toward you
  const float cr = cosf(roll), sr = sinf(roll), cp = cosf(pitch), sp = sinf(pitch), cy = cosf(yaw), sy = sinf(yaw);
  const float Rz[9] = {cr, -sr, 0, sr, cr, 0, 0, 0, 1};
  const float Rx[9] = {1, 0, 0, 0, cp, -sp, 0, sp, cp};
  const float Ry[9] = {cy, 0, sy, 0, 1, 0, -sy, 0, cy};
  float t[9], n[9];
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) {
      t[i * 3 + j] = Rx[i * 3] * Rz[j] + Rx[i * 3 + 1] * Rz[3 + j] + Rx[i * 3 + 2] * Rz[6 + j];
    }
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) n[i * 3 + j] = Ry[i * 3] * t[j] + Ry[i * 3 + 1] * t[3 + j] + Ry[i * 3 + 2] * t[6 + j];
  if (!init) {
    for (int i = 0; i < 9; ++i) m[i] = n[i];
    init = true;
  }
  // body rates: M_prev^T * M_new = I + [w]x dt
  float d[9];
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) d[i * 3 + j] = m[i] * n[j] + m[3 + i] * n[3 + j] + m[6 + i] * n[6 + j];
  ImuSample s;
  const float k = dt > 0 ? 0.5f / dt : 0;
  s.gx = (d[7] - d[5]) * k;
  s.gy = (d[2] - d[6]) * k;
  s.gz = (d[3] - d[1]) * k;
  // the accelerometer reads "up" (the world's +Y) in the device frame, plus any linear acceleration
  s.ax = n[3] + lin[0];
  s.ay = n[4] + lin[1];
  s.az = n[5] + lin[2];
  for (int i = 0; i < 9; ++i) m[i] = n[i];
  return s;
}

// ----------------------------------------------------------- motion ---

void EyeMotion::push(MotionCue c) {
  if (qCount_ == 8) {
    qHead_ = (qHead_ + 1) % 8;
    --qCount_;
  }
  q_[(qHead_ + qCount_) % 8] = c;
  ++qCount_;
}

bool EyeMotion::poll(MotionCue& c) {
  if (!qCount_) return false;
  c = q_[qHead_];
  qHead_ = (qHead_ + 1) % 8;
  --qCount_;
  return true;
}

void EyeMotion::springs(float dt) {
  int n = (int)ceilf(dt * 240.0f);
  if (n < 1) n = 1;
  const float h = dt / n;
  const float kR = 80, cR = 2 * sqrtf(kR) * 0.5f;  // level: a little lag, ~16 % overshoot
  static const float kM[2] = {60, 48}, cM[2] = {2 * 7.745967f * 0.35f, 2 * 6.928203f * 0.32f};  // marble
  for (int i = 0; i < n; ++i) {
    rollV_ += (kR * (rollT_ - roll_) - cR * rollV_) * h;
    roll_ += rollV_ * h;
    for (int e = 0; e < 2; ++e) {
      mvx_[e] += (kM[e] * (mtx_ - mx_[e]) - cM[e] * mvx_[e] + fx_) * h;
      mvy_[e] += (kM[e] * (mty_ - my_[e]) - cM[e] * mvy_[e] + fy_) * h;
      mx_[e] += mvx_[e] * h;
      my_[e] += mvy_[e] * h;
    }
  }
}

void EyeMotion::update(float dt, const ImuSample& s) {
  if (!(dt > 0)) return;
  if (dt > 0.1f) dt = 0.1f;
  const float a[3] = {s.ax, s.ay, s.az};
  const float am = sqrtf(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
  if (!init_) {
    if (am < 0.3f) return;
    for (int i = 0; i < 3; ++i) g_[i] = lp_[i] = a[i] / am;
    float w;
    const float raw = levelAngle(g_[0], g_[1], g_[2], &w);
    rollValid_ = sqrtf(g_[0] * g_[0] + g_[1] * g_[1]) > 0.2f;
    rollU_ = prevRollU_ = rollValid_ ? raw : 0;
    roll_ = rollT_ = rollValid_ ? softClampRoll(rollU_) * w : 0;
    const float c = cosf(roll_), sn = sinf(roll_);  // "down" in the eyes' frame, as step 4
    n_[0] = -g_[0] * c + g_[1] * sn;
    n_[1] = g_[0] * sn + g_[1] * c;
    init_ = true;
  }
  t_ += dt;
  if (t_ > 3600) t_ -= 3600;

  // 1. gravity ("up" in the device frame): gyro prediction + accel correction
  float w[3] = {0, 0, 0};
  if (s.gyro) {
    w[0] = s.gx - bias_[0];
    w[1] = s.gy - bias_[1];
    w[2] = s.gz - bias_[2];
    // a world-fixed vector seen from a body turning at w: dg/dt = g x w
    const float cx = g_[1] * w[2] - g_[2] * w[1], cy = g_[2] * w[0] - g_[0] * w[2], cz = g_[0] * w[1] - g_[1] * w[0];
    g_[0] += cx * dt;
    g_[1] += cy * dt;
    g_[2] += cz * dt;
  }
  if (am > 0.3f) {
    const float trust = clampf_(1 - fabsf(am - 1) / 0.5f, 0, 1);  // linear acceleration: trust less
    const float tau = s.gyro ? 0.45f : 0.07f;
    const float k = dt / (tau + dt) * trust;
    for (int i = 0; i < 3; ++i) g_[i] += (a[i] / am - g_[i]) * k;
  }
  {
    const float gn = sqrtf(g_[0] * g_[0] + g_[1] * g_[1] + g_[2] * g_[2]);
    if (gn > 1e-6f)
      for (int i = 0; i < 3; ++i) g_[i] /= gn;
  }
  float hp2 = 0, dyn2 = 0;
  for (int i = 0; i < 3; ++i) {
    const float h = a[i] - lp_[i];
    hp2 += h * h;
    lp_[i] += h * (dt / (0.08f + dt));
    const float d = a[i] - g_[i];
    dyn2 += d * d;
  }
  const float hp = sqrtf(hp2), dyn = sqrtf(dyn2);
  const float wm = sqrtf(w[0] * w[0] + w[1] * w[1] + w[2] * w[2]);
  gyroLP_ += (wm - gyroLP_) * (dt / (0.3f + dt));
  dynLP_ += (dyn - dynLP_) * (dt / (0.3f + dt));
  if (s.gyro && dynLP_ < 0.03f && wm < 0.15f) {  // resting: learn the gyro's zero-rate offset
    const float kb = dt / (3.0f + dt);
    bias_[0] += (s.gx - bias_[0]) * kb;
    bias_[1] += (s.gy - bias_[1]) * kb;
    bias_[2] += (s.gz - bias_[2]) * kb;
  }

  // 2. level keeping: unwrap the roll so it can pass 180 deg without a jump
  const float planar = sqrtf(g_[0] * g_[0] + g_[1] * g_[1]);
  float wgt = 0;
  const float raw = levelAngle(g_[0], g_[1], g_[2], &wgt);
  if (planar > 0.2f) {
    if (!rollValid_) {
      rollU_ = prevRollU_ = raw;
      rollValid_ = true;
    } else {
      rollU_ += wrapPi(raw - wrapPi(rollU_));
      if (rollU_ > kPi + 0.6f) rollU_ -= kTau;  // well past upside down: swing round the other way
      else if (rollU_ < -kPi - 0.6f) rollU_ += kTau;
    }
  } else {
    rollValid_ = false;
  }
  // too dizzy to keep up: the eyes turn with the glass, and swing back level when it stops
  const float keep = 1 - smoothf((dizzy_ - 0.3f) / 0.5f);
  rollT_ = rollValid_ ? softClampRoll(rollU_) * wgt * keep : 0;

  // 3. spin -> dizzy (accel only: the roll rate stands in for the gyro)
  float wSpin = wm;
  if (!s.gyro) {
    const float rr = rollValid_ ? fabsf(wrapPi(rollU_ - prevRollU_)) / dt : 0;
    wNoGyro_ += (rr - wNoGyro_) * (dt / (0.1f + dt));
    wSpin = wNoGyro_;
  }
  prevRollU_ = rollU_;
  spin_.update(wSpin, dt);
  const float dzT = clampf_((spin_.level - spinMild) / (spinStrong - spinMild), 0, 1.2f);
  dizzy_ = approach(dizzy_, dzT, dzT > dizzy_ ? 5.0f : 0.9f, dt);
  if (dizzy_ > peak_) peak_ = dizzy_;
  if (!strong_ && dizzy_ > 0.75f) {
    strong_ = true;
    push(MotionCue::DizzyStart);
  }
  if (peak_ > 0.45f && dizzy_ < 0.15f) {
    peak_ = 0;
    strong_ = false;
    push(MotionCue::Ufff);
  }

  // 4. marble pupils: "down" in the eyes' own (levelled) frame against a slow
  // neutral: tipping the glass, or the eyes not level yet, rolls them to the
  // low side; the gyro pushes them like inertia
  {
    const float c = cosf(roll_), sn = sinf(roll_);
    const float dx = -g_[0], dy = g_[1];  // down, canvas axes
    const float ex0 = dx * c + dy * sn, ey0 = -dx * sn + dy * c;
    const float kn = dt / (2.2f + dt);  // the neutral follows in ~2 s
    n_[0] += (ex0 - n_[0]) * kn;
    n_[1] += (ey0 - n_[1]) * kn;
    float ex = (ex0 - n_[0]) * marbleGain, ey = (ey0 - n_[1]) * marbleGain;
    const float m = sqrtf(ex * ex + ey * ey);
    if (m > 1e-6f) {
      const float k = tanhf(m) / m;  // soft limit to the unit disc
      ex *= k;
      ey *= k;
    }
    mtx_ = ex;
    mty_ = ey;
    const float ix = -w[1] * marbleGyro, iy = -w[0] * marbleGyro;  // the glass turns, the pupils lag
    fx_ = ix * c + iy * sn;
    fy_ = -ix * sn + iy * c;
  }
  springs(dt);

  // 5. orientation
  const float gz = g_[2], gy = g_[1];
  const bool backNow = gz > (onBack_ ? 0.8f : 0.9f);
  backT_ = backNow ? backT_ + dt : 0;
  if (!onBack_ && backT_ > 0.35f) {
    onBack_ = true;
    lookLeft_ = 2.5f;
    push(MotionCue::OnBack);
  } else if (onBack_ && !backNow) {
    onBack_ = false;
  }
  lookLeft_ -= dt;
  const bool downNow = gz < (faceDown_ ? -0.6f : -0.8f);
  downT_ = downNow ? downT_ + dt : 0;
  if (!faceDown_ && downT_ > 0.5f) {
    faceDown_ = true;
    push(MotionCue::FaceDown);
  } else if (faceDown_ && !downNow) {
    faceDown_ = false;
    push(MotionCue::FaceUp);
  }
  const bool upsNow = gy < (upside_ ? -0.5f : -0.75f);
  upsT_ = upsNow ? upsT_ + dt : 0;
  if (!upside_ && upsT_ > 0.25f) {
    upside_ = true;
    push(MotionCue::UpsideDown);
  } else if (upside_ && !upsNow) {
    upside_ = false;
    push(MotionCue::Upright);
  }
  // calm: a hand's tremor (on a stand the gyro is dead still), no big moves
  const bool held = s.gyro && gyroLP_ > 0.012f && gyroLP_ < 0.3f && dynLP_ < 0.06f && fabsf(gz) < 0.9f;
  calmT_ = held ? calmT_ + dt : 0;
  if (!calm_ && calmT_ > 1.5f) {
    calm_ = true;
    push(MotionCue::Calm);
  } else if (calm_ && (gyroLP_ > 0.6f || dynLP_ > 0.15f || gyroLP_ < 0.006f || fabsf(gz) > 0.95f)) {
    calm_ = false;
  }

  // 6. gestures
  if (tap_.update(hp, dt, wm > 2.5f)) push(MotionCue::TapTap);
  if (s.gyro && dizzy_ < 0.3f) {
    const int r = nod_.update(w[0], w[1], w[2], dt);
    if (r > 0) push(MotionCue::NodYes);
    else if (r < 0) push(MotionCue::NodNo);
  }

  // 7. the pose
  const bool lookUp = onBack_ && lookLeft_ > 0;
  lid_ = approach(lid_, faceDown_ ? 0.5f : (calm_ ? 0.14f : 0.0f), 6, dt);
  dim_ = approach(dim_, faceDown_ ? 0.4f : 1.0f, 4, dt);
  look_ = approach(look_, lookUp ? 1.0f : 0.0f, 7, dt);
  pupil_ = approach(pupil_, lookUp ? 1.12f : (calm_ ? 1.07f : 1.0f), 5, dt);
  const float mw = 1 - 0.7f * look_, orbit = dizzy_ * 0.55f, ph = t_ * 8.5f;
  pose_.roll = roll_ + dizzy_ * 0.16f * sinf(t_ * 7.3f);
  pose_.px = mx_[0] * mw + orbit * cosf(ph);
  pose_.py = my_[0] * mw + orbit * 0.8f * sinf(ph);
  pose_.pxR = mx_[1] * mw + orbit * cosf(ph - 0.5f);
  pose_.pyR = my_[1] * mw + orbit * 0.8f * sinf(ph - 0.5f);
  pose_.lid = lid_;
  pose_.dim = dim_;
  pose_.pupil = pupil_;
  pose_.look = look_;
  pose_.dizzy = dizzy_;
}

// a one-shot that returns to the mood the eyes were in (not to a motion mood)
static void oneShot(EyeRig& rig, int e, float hold) {
  const int b = rig.backMood();
  rig.react(e, hold);
  rig.setBack(b);
}

void EyeMotion::apply(MotionCue c, EyeRig& rig) {
  switch (c) {
    case MotionCue::DizzyStart:
      if (rig.expression() != X_dizzy) oneShot(rig, X_dizzy, 30);
      dizzyOn_ = true;
      break;
    case MotionCue::Ufff:  // relief: droopy lids, a slow double blink, a sag
      oneShot(rig, X_bored, 1.1f);
      rig.blink(2, 1.6f);
      rig.kick(Ch_bob, 0.35f);
      rig.kick(Ch_sy, -1.2f);
      dizzyOn_ = false;
      break;
    case MotionCue::OnBack:
      rig.blink(1);
      rig.hop();
      break;
    case MotionCue::FaceDown: oneShot(rig, X_suspicious, 0.9f); break;  // grumble (then the pose dims it)
    case MotionCue::FaceUp: rig.blink(2); break;
    case MotionCue::UpsideDown: oneShot(rig, X_shocked, 0); break;
    case MotionCue::Upright: rig.blink(1); break;
    case MotionCue::Calm: rig.blink(1, 2.2f); break;
    case MotionCue::TapTap:
    case MotionCue::NodYes: oneShot(rig, X_approve, 0); break;
    case MotionCue::NodNo: oneShot(rig, X_confused, 1.2f); break;
    default: break;
  }
}

}  // namespace eyes
}  // namespace suflet
