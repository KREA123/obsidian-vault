// Turns raw touch and accelerometer samples into Events. Pure logic, no
// hardware: unit-tested on the PC with synthetic sensor traces.
#pragma once
#include "Events.h"

namespace suflet {

class TouchGestures {
 public:
  // x, y in display pixels; call every frame.
  void update(bool down, float x, float y, float dt);
  bool poll(Ev& e) { return q_.pop(e); }
  bool isDown() const { return down_; }
  float x() const { return x_; }
  float y() const { return y_; }

  float tapMaxS = 0.35f;     // longer than this is not a tap
  float holdAfterS = 0.5f;   // finger resting this long = HoldStart
  float moveSlopPx = 25.0f;  // below this the finger "didn't move"
  float strokePx = 45.0f;    // beyond this it's a stroke
  float doubleTapS = 0.40f;

 private:
  EvQueue<8> q_;
  float t_ = 0, tDown_ = 0, lastTap_ = -10;
  float x0_ = 0, y0_ = 0, x_ = 0, y_ = 0, moved_ = 0;
  bool down_ = false, holding_ = false, stroking_ = false;
};

// Device frame: +X right on the screen, +Y up (towards the ring),
// +Z out of the screen. Accel in g. Lying face-up reads (0, 0, +1).
class MotionDetector {
 public:
  void update(float ax, float ay, float az, float dt);
  bool poll(Ev& e) { return q_.pop(e); }

  float tiltX() const { return tiltX_; }  // -1..1, for "eyes roll downhill"
  float tiltY() const { return tiltY_; }
  float stillFor() const { return stillFor_; }
  bool faceDown() const { return faceDown_; }
  bool upsideDown() const { return upside_; }
  float knockX() const { return knockX_; }  // direction of the last knock
  float knockY() const { return knockY_; }

  float shakeG = 1.0f;       // dynamic accel peak that counts as a shake stroke
  int shakePeaks = 4;        // strokes within shakeWindowS
  float shakeWindowS = 1.2f;
  float freeFallG = 0.35f;
  float knockG = 0.28f;

 private:
  EvQueue<8> q_;
  float t_ = 0;
  bool init_ = false;
  float gx_ = 0, gy_ = 0, gz_ = 1;  // fast gravity (tau 0.25 s)
  float nx_ = 0, ny_ = 0, nz_ = 1;  // neutral pose (tau 4 s)
  float tiltX_ = 0, tiltY_ = 0;
  float stillFor_ = 0;
  // burst tracking (knock vs pick-up)
  bool burst_ = false;
  float burstT0_ = 0, burstQuiet_ = 0, burstPeak_ = 0, burstPx_ = 0, burstPy_ = 0,
        stillBefore_ = 0;
  // shake
  float peaks_[8] = {0};
  int nPeaks_ = 0;
  bool above_ = false;
  float shakeCool_ = 0;
  // free fall
  float ffT_ = 0;
  bool ffArmed_ = true;
  // orientation
  bool faceDown_ = false, upside_ = false;
  float knockX_ = 0, knockY_ = 0;
};

}  // namespace suflet
