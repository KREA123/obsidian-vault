// Motion (IMU) behaviours for the SOUL eyes: the same math as eyes.js Motion
// (keep the two in step; the constants and the order of operations match).
//
//   level keeping   the eye pair counter-rotates against roll in the glass
//                   plane so the eyes stay level with gravity (a spring with
//                   a little lag and overshoot; eased to +-150 deg near
//                   upside down; off when lying flat, where "up" is unknown,
//                   and given up while too dizzy to keep up)
//   marble pupils   tilting rolls the pupils to the low side ("down" in the
//                   eyes' levelled frame against a slow neutral, plus the gyro
//                   as inertia), on an under-damped spring; then they come back
//   spin -> dizzy   the gyro rate is integrated in a leaky bucket: the eyes
//                   wobble and the pupils orbit in proportion; a strong spin
//                   plays the dizzy mood (spiral pupils) until it settles,
//                   then an "ufff" (droopy lids, slow double blink, sag)
//   orientation     on its back -> looks up at you; face down -> grumbles
//                   and dims, lids half shut; upside down -> shocked; held
//                   still in a hand -> calm (softer lids, wider pupils)
//   gestures        double tap on the case (two short accel spikes);
//                   nod (pitch, yes) / tilt left-right (roll or yaw, no)
//
// Device frame (as Gestures.h): +X right, +Y up (to the ring), +Z out of the
// glass. Accel in g (lying face up reads 0,0,+1), gyro in rad/s, right-handed.
// Canvas frame (what the renderer uses): +x right, +y down, + angle = clockwise.
//
// Cost: ~150 float ops per sample (100-200 Hz) + a few springs; no heap.
#pragma once
#include <stdint.h>

namespace suflet {
namespace eyes {

class EyeRig;

struct ImuSample {
  float ax = 0, ay = 0, az = 1;  // g
  float gx = 0, gy = 0, gz = 0;  // rad/s
  bool gyro = true;              // false: accelerometer only (no dizzy from gyro, no nods)
};

// What the renderer reads (all neutral = the eyes draw exactly as without motion).
struct MotionPose {
  float roll = 0;              // extra rotation of the eye pair, rad (canvas, + = clockwise)
  float px = 0, py = 0;        // left pupil offset, gaze units (-1..1), in the eyes' own frame
  float pxR = 0, pyR = 0;      // right pupil (a beat behind)
  float lid = 0;               // extra lid closure 0..1
  float pupil = 1;             // pupil scale
  float dim = 1;               // alpha multiplier
  float look = 0;              // 0..1 pull of the gaze to the centre ("looks up at you")
  float dizzy = 0;             // 0..~1.2, for the UI and tests
};

enum class MotionCue : uint8_t {
  None,
  DizzyStart,  // a strong spin: dizzy mood (spiral pupils) until it settles
  Ufff,        // the spin is over: relief
  OnBack,      // laid on its back: looks up at you
  FaceDown,    // put on its face: grumbles, dims
  FaceUp,      // turned back over
  UpsideDown,  // standing on its head: shocked
  Upright,
  Calm,        // held still in a hand
  TapTap,      // double tap on the case: "yes?" / acknowledge
  NodYes,      // nodded (pitch back and forth)
  NodNo,       // tilted left-right (roll or yaw back and forth)
  Count
};
const char* motionCueName(MotionCue c);

// ---- the pieces (pure functions / small state machines, unit-tested) -----

float wrapPi(float a);  // to (-pi, pi]
// The canvas rotation that keeps the eyes level for an "up" vector (gx, gy, gz)
// in the device frame (|g| ~ 1), and how much to trust it (0 flat .. 1 upright).
float levelAngle(float gx, float gy, float gz, float* weight);
// Linear up to +-120 deg, then eased to +-150 deg at 180 (and held beyond).
float softClampRoll(float a);

class TapDetector {
 public:
  // hp: |high-passed accel| (g); busy: the case is being moved a lot.
  bool update(float hp, float dt, bool busy);
  float tapG = 0.25f;      // spike threshold
  float maxTapS = 0.07f;   // a tap is short
  float minGapS = 0.09f;   // ringing of the same tap is ignored
  float maxGapS = 0.5f;    // the second tap comes within this
  float quietS = 0.22f;    // and nothing after it (a third = handling)

 private:
  float aboveT_ = 0, since1_ = 10, since2_ = 10;  // ages, so long uptimes keep precision
  bool above_ = false;
  int n_ = 0;
};

class NodDetector {
 public:
  // +1 yes (pitch: rotation about X), -1 no (rotation about Y or Z), 0 nothing.
  int update(float gx, float gy, float gz, float dt);
  float rate = 1.3f;     // rad/s that counts as a swing
  float dom = 1.6f;      // the swing axis must beat the others by this much
  int swings = 3;        // alternating swings ...
  float windowS = 1.6f;  // ... within this
  float gapS = 0.7f;     // max time between two swings
  float coolS = 1.2f;

 private:
  float cool_ = 0;
  bool in_[2] = {false, false};
  int n_[2] = {0, 0}, last_[2] = {0, 0};
  float age_[2] = {10, 10}, span_[2] = {0, 0};  // since the last swing / the first one
};

// Leaky bucket of rotation: steady state = (rate - dead) * tau.
struct SpinMeter {
  float level = 0, dead = 0.8f, tau = 1.3f;
  void update(float w, float dt);
};

// A device pose -> what the IMU reads (the simulator, tests and the demo clip).
// roll: turned in the glass plane (+ = counter-clockwise as you look at it);
// pitch: top edge toward you (+90 = face down, -90 = on its back);
// yaw: turned to its right. Standing upright facing you = 0, 0, 0.
struct PoseImu {
  float m[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};  // device axes in the world (columns), row-major
  float lin[3] = {0, 0, 0};                  // extra linear acceleration (g, device frame): taps
  bool init = false;
  ImuSample sample(float roll, float pitch, float yaw, float dt);
};

// ---- the whole thing ------------------------------------------------------

class EyeMotion {
 public:
  void reset() { *this = EyeMotion(); }
  // Feed every IMU sample (100-200 Hz), or once per frame with the latest one.
  void update(float dt, const ImuSample& s);
  bool poll(MotionCue& c);
  const MotionPose& pose() const { return pose_; }
  bool active() const { return init_; }

  // The face's answer to a cue (the same in eyes.js): one-shot reactions that
  // keep the mood they return to.
  void apply(MotionCue c, EyeRig& rig);

  // state (tests, the simulator, the serial log)
  float gravX() const { return g_[0]; }
  float gravY() const { return g_[1]; }
  float gravZ() const { return g_[2]; }
  float levelTarget() const { return rollT_; }
  float spin() const { return spin_.level; }
  bool onBack() const { return onBack_; }
  bool faceDown() const { return faceDown_; }
  bool upsideDown() const { return upside_; }
  bool calm() const { return calm_; }
  bool dizzyStrong() const { return strong_; }
  float gyroBias(int i) const { return bias_[i]; }

  // tuning
  float marbleGain = 2.4f;   // gaze units per unit of gravity change
  float marbleGyro = 8.0f;   // inertia from the gyro (gaze units/s^2 per rad/s)
  float spinMild = 2.5f;     // bucket level where the wobble starts
  float spinStrong = 7.0f;   // ... and where it is full (spiral pupils past 0.75 of it)

 private:
  void push(MotionCue c);
  void springs(float dt);

  bool init_ = false;
  float t_ = 0;
  float g_[3] = {0, 1, 0}, lp_[3] = {0, 1, 0};
  float n_[2] = {0, 1};  // neutral "down" in the eyes' frame
  float bias_[3] = {0, 0, 0};
  // level keeping
  bool rollValid_ = false;
  float rollU_ = 0, rollT_ = 0, roll_ = 0, rollV_ = 0, prevRollU_ = 0;
  // marble (left, right)
  float mx_[2] = {0, 0}, my_[2] = {0, 0}, mvx_[2] = {0, 0}, mvy_[2] = {0, 0};
  float mtx_ = 0, mty_ = 0, fx_ = 0, fy_ = 0;
  // dizzy
  SpinMeter spin_;
  float dizzy_ = 0, peak_ = 0, wNoGyro_ = 0;
  bool strong_ = false;
  // orientation
  bool onBack_ = false, faceDown_ = false, upside_ = false, calm_ = false;
  float backT_ = 0, downT_ = 0, upsT_ = 0, calmT_ = 0, lookLeft_ = 0;
  float gyroLP_ = 0, dynLP_ = 0;
  // gestures
  TapDetector tap_;
  NodDetector nod_;
  // smoothed pose bits
  float lid_ = 0, dim_ = 1, pupil_ = 1, look_ = 0;
  MotionPose pose_;
  // cues
  MotionCue q_[8] = {};
  int qHead_ = 0, qCount_ = 0;
  bool dizzyOn_ = false;
};

}  // namespace eyes
}  // namespace suflet
