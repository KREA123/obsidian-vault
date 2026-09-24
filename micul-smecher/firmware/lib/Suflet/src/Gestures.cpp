#include "Gestures.h"

#include <math.h>

namespace suflet {

// ---------------------------------------------------------------- touch ---

void TouchGestures::update(bool down, float x, float y, float dt) {
  t_ += dt;
  if (down && !down_) {  // press
    down_ = true;
    tDown_ = t_;
    x0_ = x_ = x;
    y0_ = y_ = y;
    moved_ = 0;
    holding_ = stroking_ = false;
    return;
  }
  if (down && down_) {  // held
    x_ = x;
    y_ = y;
    const float d = sqrtf((x - x0_) * (x - x0_) + (y - y0_) * (y - y0_));
    if (d > moved_) moved_ = d;
    if (!holding_ && !stroking_) {
      if (moved_ > strokePx) {
        stroking_ = true;
        q_.push(Ev::StrokeStart);
      } else if (t_ - tDown_ >= holdAfterS && moved_ < moveSlopPx) {
        holding_ = true;
        q_.push(Ev::HoldStart);
      }
    }
    return;
  }
  if (!down && down_) {  // release
    down_ = false;
    if (holding_) {
      q_.push(Ev::HoldEnd);
    } else if (stroking_) {
      q_.push(Ev::StrokeEnd);
    } else if (t_ - tDown_ <= tapMaxS && moved_ < moveSlopPx) {
      if (t_ - lastTap_ <= doubleTapS) {
        q_.push(Ev::DoubleTap);
        lastTap_ = -10;  // a third tap starts a new sequence
      } else {
        q_.push(Ev::Tap);
        lastTap_ = t_;
      }
    }
    holding_ = stroking_ = false;
  }
}

// --------------------------------------------------------------- motion ---

static float lp(float prev, float v, float dt, float tau) { return prev + (v - prev) * (dt / (tau + dt)); }

void MotionDetector::update(float ax, float ay, float az, float dt) {
  if (dt <= 0) return;
  t_ += dt;
  if (!init_) {
    gx_ = nx_ = ax;
    gy_ = ny_ = ay;
    gz_ = nz_ = az;
    init_ = true;
  }
  gx_ = lp(gx_, ax, dt, 0.25f);
  gy_ = lp(gy_, ay, dt, 0.25f);
  gz_ = lp(gz_, az, dt, 0.25f);
  nx_ = lp(nx_, gx_, dt, 4.0f);
  ny_ = lp(ny_, gy_, dt, 4.0f);
  nz_ = lp(nz_, gz_, dt, 4.0f);

  const float dx = ax - gx_, dy = ay - gy_, dz = az - gz_;
  const float dyn = sqrtf(dx * dx + dy * dy + dz * dz);
  const float mag = sqrtf(ax * ax + ay * ay + az * az);

  // eyes roll "downhill" when you tilt it, then re-centre as the pose settles
  auto clamp1 = [](float v) { return v < -1 ? -1.0f : (v > 1 ? 1.0f : v); };
  tiltX_ = clamp1(-(gx_ - nx_) * 2.2f);
  tiltY_ = clamp1((gy_ - ny_) * 2.2f);

  // ---- stillness, knock vs pick-up -------------------------------------
  if (!burst_) {
    if (dyn < 0.04f) {
      stillFor_ += dt;
    } else if (dyn > 0.08f) {
      if (stillFor_ > 1.0f) {  // leaving rest: find out what it is
        burst_ = true;
        burstT0_ = t_;
        burstQuiet_ = 0;
        burstPeak_ = dyn;
        burstPx_ = dx;
        burstPy_ = dy;
        stillBefore_ = stillFor_;
      } else {
        stillFor_ = 0;
      }
    }
  } else {
    if (dyn > burstPeak_) {
      burstPeak_ = dyn;
      burstPx_ = dx;
      burstPy_ = dy;
    }
    burstQuiet_ = dyn < 0.06f ? burstQuiet_ + dt : 0;
    const float active = t_ - burstT0_ - burstQuiet_;
    if (burstQuiet_ >= 0.1f) {  // settled again quickly
      burst_ = false;
      if (burstPeak_ >= knockG && active < 0.15f) {
        const float n = sqrtf(burstPx_ * burstPx_ + burstPy_ * burstPy_);
        knockX_ = n > 1e-4f ? burstPx_ / n : 0;
        knockY_ = n > 1e-4f ? burstPy_ / n : 0;
        q_.push(Ev::Knock);
      }
      stillFor_ = stillBefore_ + (t_ - burstT0_);  // a bump doesn't break rest
    } else if (active > 0.2f) {  // sustained motion: someone took it
      burst_ = false;
      stillFor_ = 0;
      q_.push(Ev::PickUp);
    }
  }

  // ---- shake ------------------------------------------------------------
  if (shakeCool_ > 0) shakeCool_ -= dt;
  const bool above = dyn > shakeG;
  if (above && !above_) {
    if (nPeaks_ == 8) {
      for (int i = 1; i < 8; ++i) peaks_[i - 1] = peaks_[i];
      --nPeaks_;
    }
    peaks_[nPeaks_++] = t_;
    int recent = 0;
    for (int i = 0; i < nPeaks_; ++i)
      if (t_ - peaks_[i] <= shakeWindowS) ++recent;
    if (recent >= shakePeaks && shakeCool_ <= 0) {
      q_.push(Ev::Shake);
      shakeCool_ = 2.5f;
      nPeaks_ = 0;
    }
  }
  above_ = above;

  // ---- free fall --------------------------------------------------------
  if (mag < freeFallG) {
    ffT_ += dt;
    if (ffT_ > 0.08f && ffArmed_) {
      q_.push(Ev::FreeFall);
      ffArmed_ = false;
    }
  } else {
    ffT_ = 0;
    if (mag > 0.8f) ffArmed_ = true;
  }

  // ---- orientation (with hysteresis) -------------------------------------
  const float gm = sqrtf(gx_ * gx_ + gy_ * gy_ + gz_ * gz_);
  if (gm > 0.5f) {
    const float zn = gz_ / gm, yn = gy_ / gm;
    if (!faceDown_ && zn < -0.8f) {
      faceDown_ = true;
      q_.push(Ev::FaceDown);
    } else if (faceDown_ && zn > -0.6f) {
      faceDown_ = false;
      q_.push(Ev::FaceUp);
    }
    if (!upside_ && yn < -0.75f) {
      upside_ = true;
      q_.push(Ev::UpsideDown);
    } else if (upside_ && yn > -0.5f) {
      upside_ = false;
      q_.push(Ev::Upright);
    }
  }
}

}  // namespace suflet
