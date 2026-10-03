// The eyes' motion (IMU) behaviours: filter math, level angle, marble
// pupils, spin -> dizzy, orientation, tap and nod detectors, and the parity
// of the C++ port with eyes.js Motion (fixture made by tools/gen_motion_fixture.js).
#include <unity.h>

#include <cmath>
#include <cstdio>
#include <vector>

#include "Brain.h"
#include "EyeMotion.h"
#include "EyeRender.h"
#include "EyeRig.h"
#include "Personality.h"
#include "motion_fixture.h"

using namespace suflet;
using namespace suflet::eyes;

static constexpr float kPiF = 3.14159265f;
static constexpr float kH = 0.01f;  // 100 Hz, like the device

static float deg(float d) { return d * kPiF / 180.0f; }

struct Drive {
  EyeMotion m;
  PoseImu imu;
  float roll = 0, pitch = 0, yaw = 0;
  std::vector<MotionCue> cues;
  // move linearly to (r, p, y) over `s` seconds, then hold
  void to(float r, float p, float y, float s, float hold = 0, const ImuSample* noise = nullptr) {
    const int n = (int)(s / kH + 0.5f), nh = (int)(hold / kH + 0.5f);
    const float r0 = roll, p0 = pitch, y0 = yaw;
    for (int i = 1; i <= n + nh; ++i) {
      const float q = i >= n ? 1.0f : (float)i / n;
      roll = r0 + (r - r0) * q;
      pitch = p0 + (p - p0) * q;
      yaw = y0 + (y - y0) * q;
      feed(noise);
    }
  }
  void feed(const ImuSample* noise = nullptr) {
    ImuSample s = imu.sample(roll, pitch, yaw, kH);
    if (noise) {
      s.gx += noise->gx;
      s.gy += noise->gy;
      s.gz += noise->gz;
    }
    m.update(kH, s);
    MotionCue c;
    while (m.poll(c)) cues.push_back(c);
  }
  bool saw(MotionCue c) const {
    for (MotionCue x : cues)
      if (x == c) return true;
    return false;
  }
};

static void test_motion_level_angle_and_soft_clamp() {
  float w = 0;
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, levelAngle(0, 1, 0, &w));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, w);
  // turned 90 deg counter-clockwise: "up" is the device's +X -> the eyes turn 90 deg clockwise
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, kPiF / 2, levelAngle(1, 0, 0, &w));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, -kPiF / 2, levelAngle(-1, 0, 0, &w));
  levelAngle(0, 0.05f, 1, &w);  // lying flat: gravity says nothing about roll
  TEST_ASSERT_EQUAL_FLOAT(0.0f, w);
  levelAngle(0, 0.45f, 0.89f, &w);  // half way
  TEST_ASSERT_TRUE(w > 0.2f && w < 0.8f);
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.0f, softClampRoll(1.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, -2.0f, softClampRoll(-2.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, deg(150), softClampRoll(kPiF));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, -deg(150), softClampRoll(-kPiF - 0.4f));
  // smooth at 120 deg (slope 1) and monotonic up to 180
  const float a = deg(120);
  TEST_ASSERT_FLOAT_WITHIN(2e-4f, 0.01f, softClampRoll(a + 0.01f) - softClampRoll(a));
  float prev = 0;
  for (float x = 0; x <= kPiF; x += 0.01f) {
    TEST_ASSERT_TRUE(softClampRoll(x) >= prev);
    prev = softClampRoll(x);
  }
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.5f, wrapPi(0.5f + 6.28318531f));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, -3.0f, wrapPi(3.28318531f));
}

static void test_motion_pose_imu_reads_gravity_and_rates() {
  PoseImu p;
  ImuSample s = p.sample(0, 0, 0, kH);
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, s.ay);  // standing upright: +Y up
  s = p.sample(0, deg(-90), 0, kH);             // on its back: +Z up
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, s.az);
  PoseImu q;
  q.sample(0, 0, 0, kH);
  s = q.sample(0.02f, 0, 0, kH);  // turning counter-clockwise at 2 rad/s
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 2.0f, s.gz);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, s.gx);
}

static void test_motion_level_keeping_springs_to_the_roll_with_overshoot() {
  Drive d;
  d.to(0, 0, 0, 0.5f);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, d.m.pose().roll);
  float maxRoll = 0;
  const int n = (int)(0.3f / kH);
  for (int i = 1; i <= n + 200; ++i) {  // turn 60 deg counter-clockwise in 0.3 s, hold 2 s
    d.roll = deg(60) * (i >= n ? 1.0f : (float)i / n);
    d.feed();
    maxRoll = fmaxf(maxRoll, d.m.pose().roll);
    if (i == n) TEST_ASSERT_TRUE(d.m.pose().roll < deg(55));  // it lags ...
  }
  TEST_ASSERT_TRUE(maxRoll > deg(61));         // ... overshoots a little ...
  TEST_ASSERT_TRUE(maxRoll < deg(60) * 1.3f);
  TEST_ASSERT_FLOAT_WITHIN(deg(1.5f), deg(60), d.m.pose().roll);  // ... and settles level
  // laid flat on its back: no "up" in the glass plane, the eyes go back to straight
  d.to(deg(60), deg(-90), 0, 0.5f, 2.0f);
  TEST_ASSERT_FLOAT_WITHIN(deg(2), 0.0f, d.m.pose().roll);
}

static void test_motion_upside_down_eases_to_150_and_shocks() {
  Drive d;
  d.to(0, 0, 0, 0.3f);
  float maxAbs = 0;
  for (int i = 0; i <= 300; ++i) {  // slowly round to 200 deg
    d.roll = deg(200) * i / 300.0f;
    d.feed();
    maxAbs = fmaxf(maxAbs, fabsf(d.m.levelTarget()));
  }
  TEST_ASSERT_TRUE(maxAbs <= deg(150) + 1e-3f);
  TEST_ASSERT_TRUE(d.saw(MotionCue::UpsideDown));
  d.to(0, 0, 0, 1.0f, 0.5f);
  TEST_ASSERT_TRUE(d.saw(MotionCue::Upright));
}

static void test_motion_marble_rolls_to_the_low_side_and_returns() {
  Drive d;
  d.to(0, deg(-90), 0, 0.1f, 10.0f);  // lying on its back (the neutral pose settles)
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 0.0f, d.m.pose().py);
  d.to(0, deg(-70), 0, 0.25f, 0.3f);  // lift the top edge 20 deg: the bottom is the low side
  const float py = d.m.pose().py;
  TEST_ASSERT_TRUE_MESSAGE(py > 0.3f, "pupils roll to the low side");
  TEST_ASSERT_TRUE(fabsf(d.m.pose().px) < 0.1f);
  TEST_ASSERT_TRUE(py <= 1.05f);  // inside the unit disc
  d.to(0, deg(-70), 0, 0, 8.0f);  // held: the neutral pose catches up, they come back
  TEST_ASSERT_TRUE(fabsf(d.m.pose().py) < 0.08f);
  // standing, turned a quarter counter-clockwise: in the eyes' own (levelled)
  // frame the pupils swing too, then settle
  Drive u;
  u.to(0, 0, 0, 0.1f, 1.0f);
  u.to(deg(90), 0, 0, 0.3f, 0.2f);
  TEST_ASSERT_TRUE(hypotf(u.m.pose().px, u.m.pose().py) > 0.3f);
  u.to(deg(90), 0, 0, 0, 8.0f);
  TEST_ASSERT_TRUE(hypotf(u.m.pose().px, u.m.pose().py) < 0.08f);
}

static void test_motion_spin_makes_dizzy_then_ufff() {
  Drive d;
  d.to(0, 0, 0, 0.5f);
  // a mild spin: wobble, no spiral
  d.to(10.5f, 0, 0, 3.0f);  // turned in the glass plane at 3.5 rad/s for 3 s
  TEST_ASSERT_TRUE(d.m.pose().dizzy > 0.05f);
  TEST_ASSERT_FALSE(d.saw(MotionCue::DizzyStart));
  d.to(d.roll, 0, 0, 0, 5.0f);
  d.cues.clear();
  // a strong one: 2 turns a second for 2.5 s (around its vertical axis, like a chair)
  d.to(d.roll, 0, 12.566f * 2.5f, 2.5f);
  TEST_ASSERT_TRUE(d.saw(MotionCue::DizzyStart));
  TEST_ASSERT_TRUE(d.m.pose().dizzy > 0.75f);
  TEST_ASSERT_TRUE(d.m.dizzyStrong());
  TEST_ASSERT_FALSE(d.saw(MotionCue::Ufff));
  d.to(d.roll, 0, d.yaw, 0, 7.0f);  // stop: it settles, then "ufff"
  TEST_ASSERT_TRUE(d.saw(MotionCue::Ufff));
  TEST_ASSERT_TRUE(d.m.pose().dizzy < 0.15f);
  TEST_ASSERT_FALSE(d.m.dizzyStrong());
}

static void test_motion_orientation_cues_and_pose() {
  Drive d;
  d.to(0, 0, 0, 0.5f);
  d.to(0, deg(-90), 0, 0.4f, 1.0f);  // laid on its back: looks up at you
  TEST_ASSERT_TRUE(d.saw(MotionCue::OnBack));
  TEST_ASSERT_TRUE(d.m.pose().look > 0.8f);
  TEST_ASSERT_TRUE(d.m.pose().pupil > 1.05f);
  d.to(0, deg(-90), 0, 0, 3.0f);  // then life goes on
  TEST_ASSERT_TRUE(d.m.pose().look < 0.1f);
  d.to(0, deg(90), 0, 0.6f, 2.0f);  // face down: grumble, dim, lids half shut
  TEST_ASSERT_TRUE(d.saw(MotionCue::FaceDown));
  TEST_ASSERT_TRUE(d.m.pose().dim < 0.55f);
  TEST_ASSERT_TRUE(d.m.pose().lid > 0.4f);
  d.to(0, 0, 0, 0.6f, 1.5f);
  TEST_ASSERT_TRUE(d.saw(MotionCue::FaceUp));
  TEST_ASSERT_TRUE(d.m.pose().dim > 0.95f);
}

static void test_motion_calm_in_a_hand_not_on_a_stand() {
  Drive d;
  d.to(0, deg(-25), 0, 0.3f);
  ImuSample tremor;
  for (int i = 0; i < 300; ++i) {  // 3 s held: ~0.05 rad/s of hand tremor
    const float t = i * kH;
    tremor.gx = 0.05f * sinf(t * 57);
    tremor.gy = 0.04f * sinf(t * 43 + 1);
    tremor.gz = 0.03f * sinf(t * 71 + 2);
    d.feed(&tremor);
  }
  TEST_ASSERT_TRUE(d.saw(MotionCue::Calm));
  TEST_ASSERT_TRUE(d.m.calm());
  TEST_ASSERT_TRUE(d.m.pose().lid > 0.08f);
  Drive s;  // on its stand: the gyro is dead still
  s.to(0, deg(-25), 0, 0.3f, 4.0f);
  TEST_ASSERT_FALSE(s.saw(MotionCue::Calm));
}

static void test_motion_gyro_bias_is_learned_at_rest() {
  Drive d;
  ImuSample bias;
  bias.gx = 0.03f;  // ~1.7 deg/s zero-rate offset
  bias.gz = -0.02f;
  d.to(0, deg(-90), 0, 0, 20.0f, &bias);
  TEST_ASSERT_FLOAT_WITHIN(0.004f, 0.03f, d.m.gyroBias(0));
  TEST_ASSERT_FLOAT_WITHIN(0.004f, -0.02f, d.m.gyroBias(2));
  TEST_ASSERT_FALSE(d.saw(MotionCue::Calm));
}

static int tapRun(TapDetector& t, const std::vector<float>& spikesAt, float len, float total) {
  int fired = 0;
  for (int i = 0; i < (int)(total / kH); ++i) {
    const float tt = i * kH;
    float hp = 0.01f;
    for (float s : spikesAt)
      if (tt >= s && tt < s + len) hp = 0.8f;
    if (t.update(hp, kH, false)) ++fired;
  }
  return fired;
}

static void test_motion_tap_detector() {
  TapDetector a, b, c, d, e;
  TEST_ASSERT_EQUAL_INT(1, tapRun(a, {0.2f, 0.45f}, 0.02f, 1.5f));        // double tap
  TEST_ASSERT_EQUAL_INT(0, tapRun(b, {0.2f}, 0.02f, 1.5f));               // one
  TEST_ASSERT_EQUAL_INT(0, tapRun(c, {0.2f, 0.4f, 0.55f}, 0.02f, 1.5f));  // three: handling
  TEST_ASSERT_EQUAL_INT(0, tapRun(d, {0.2f, 0.45f}, 0.2f, 1.5f));         // long pushes
  TEST_ASSERT_EQUAL_INT(0, tapRun(e, {0.2f, 0.9f}, 0.02f, 1.5f));         // too far apart
  // through the whole filter: two 0.7 g jolts on the case, 0.25 s apart
  Drive m;
  m.to(0, deg(-20), 0, 0.2f, 1.0f);
  for (int k = 0; k < 2; ++k) {
    m.imu.lin[2] = -0.7f;
    m.feed();
    m.imu.lin[2] = 0;
    m.to(m.roll, m.pitch, m.yaw, 0, 0.24f);
  }
  m.to(m.roll, m.pitch, m.yaw, 0, 0.5f);
  TEST_ASSERT_TRUE(m.saw(MotionCue::TapTap));
}

static void test_motion_nod_yes_and_no() {
  NodDetector y, n, one;
  int ry = 0, rn = 0, r1 = 0;
  for (int i = 0; i < 150; ++i) {
    const float t = i * kH, w = 3.5f * sinf(t * 6.28318f * 2.0f);
    const int a = y.update(w, 0.1f * w, 0, kH);  // pitch: nod
    const int b = n.update(0.1f * w, 0, w, kH);  // roll left-right
    const int c = one.update(0, t < 0.5f ? 3.0f : 0, 0, kH);  // a single turn
    if (a) ry = a;
    if (b) rn = b;
    if (c) r1 = c;
  }
  TEST_ASSERT_EQUAL_INT(1, ry);
  TEST_ASSERT_EQUAL_INT(-1, rn);
  TEST_ASSERT_EQUAL_INT(0, r1);
  // through the filter: nodding the device +-20 deg at 2 Hz
  Drive d;
  d.to(0, 0, 0, 0.3f);
  for (int i = 0; i < 150; ++i) {
    d.pitch = deg(20) * sinf(i * kH * 6.28318f * 2.0f);
    d.feed();
  }
  TEST_ASSERT_TRUE(d.saw(MotionCue::NodYes));
  TEST_ASSERT_FALSE(d.saw(MotionCue::NodNo));
}

static void test_motion_face_answers_and_keeps_its_mood() {
  EyeRig rig(5);
  EyeMotion m;
  rig.setExpression(X_happy);
  rig.update(0.5f);
  m.apply(MotionCue::DizzyStart, rig);
  TEST_ASSERT_EQUAL_INT(X_dizzy, rig.expression());
  rig.update(1.0f);
  m.apply(MotionCue::Ufff, rig);
  TEST_ASSERT_EQUAL_INT(X_bored, rig.expression());
  for (int i = 0; i < 60; ++i) rig.update(1.0f / 30);
  TEST_ASSERT_EQUAL_INT(X_happy, rig.expression());  // back to its own mood, not to dizzy
  m.apply(MotionCue::UpsideDown, rig);
  TEST_ASSERT_EQUAL_INT(X_shocked, rig.expression());
  m.apply(MotionCue::TapTap, rig);
  TEST_ASSERT_EQUAL_INT(X_approve, rig.expression());
  for (int i = 0; i < 90; ++i) rig.update(1.0f / 30);
  TEST_ASSERT_EQUAL_INT(X_happy, rig.expression());
}

static void test_motion_neutral_pose_draws_the_same_and_roll_turns_the_eyes() {
  const int W = 160, H = 160;
  std::vector<uint16_t> a(W * H), b(W * H);
  Canvas ca(W, H, a.data()), cb(W, H, b.data());
  EyeRenderer r;
  TEST_ASSERT_TRUE(r.begin(W, H));
  EyeRig rig(3);
  rig.update(0.7f);
  RenderOpts o;
  r.render(ca, rig, kDesigns[0], 80, 80, 150, o);
  const MotionPose neutral;
  o.motion = &neutral;
  r.render(cb, rig, kDesigns[0], 80, 80, 150, o);
  TEST_ASSERT_TRUE(a == b);  // no IMU, no change: the parity with eyes.js holds
  // a quarter turn: the eye pair stands vertical (left eye on top for +90 deg clockwise)
  MotionPose turned;
  turned.roll = kPiF / 2;
  o.motion = &turned;
  std::fill(b.begin(), b.end(), 0);
  r.render(cb, rig, kDesigns[0], 80, 80, 150, o);
  TEST_ASSERT_TRUE(fabsf(r.eye(0).x - r.eye(1).x) > 10);  // geometry is in the rotated frame ...
  long top = 0, bottom = 0, left = 0, right = 0;
  for (int y = 0; y < H; ++y)
    for (int x = 0; x < W; ++x) {
      if (!b[y * W + x]) continue;
      (y < 80 ? top : bottom) += 1;
      (x < 80 ? left : right) += 1;
    }
  TEST_ASSERT_TRUE(top > 300 && bottom > 300);              // ... and on the glass the eyes are one above the other
  TEST_ASSERT_TRUE(labs(left - right) < (left + right) / 3);  // symmetric left/right
}

static void test_motion_nod_answers_a_claude_request() {
  Brain b(Personality::fromSeed(1), 7);
  b.update(0.1f, Inputs());
  b.event(Ev::NodYes);  // nobody asked: nothing
  Cue c;
  bool approved = false;
  while (b.popCue(c)) approved |= c == Cue::ClaudeApprove;
  TEST_ASSERT_FALSE(approved);
  b.event(Ev::ClaudePrompt);
  b.event(Ev::NodYes);
  while (b.popCue(c)) approved |= c == Cue::ClaudeApprove;
  TEST_ASSERT_TRUE(approved);
  bool denied = false;
  b.event(Ev::ClaudePrompt);
  b.event(Ev::NodNo);
  while (b.popCue(c)) denied |= c == Cue::ClaudeDeny;
  TEST_ASSERT_TRUE(denied);
}

// eyes.js Motion and this port, fed the same IMU trace, give the same pose
static void test_motion_matches_eyes_js() {
  EyeMotion m;
  int k = 0, cueI = 0;
  for (int i = 0; i < kMotionTraceN; ++i) {
    const MotionTraceIn& in = kMotionTrace[i];
    ImuSample s;
    s.ax = in.a[0];
    s.ay = in.a[1];
    s.az = in.a[2];
    s.gx = in.g[0];
    s.gy = in.g[1];
    s.gz = in.g[2];
    m.update(in.dt, s);
    MotionCue c;
    while (m.poll(c)) {
      TEST_ASSERT_TRUE(cueI < kMotionCuesN);
      TEST_ASSERT_EQUAL_INT_MESSAGE(kMotionCues[cueI].cue, (int)c, motionCueName(c));
      TEST_ASSERT_INT_WITHIN(2, kMotionCues[cueI].i, i);  // float vs double: a sample either way
      ++cueI;
    }
    if (k < kMotionPosesN && kMotionPoses[k].i == i) {
      const MotionPoseOut& o = kMotionPoses[k++];
      const MotionPose& p = m.pose();
      char msg[48];
      snprintf(msg, sizeof msg, "sample %d", i);
      // float (device) vs double (web): a sample either way at a threshold, a tenth of a pixel on the glass
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(5e-3f, o.roll, p.roll, msg);
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(1e-2f, o.px, p.px, msg);
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(1e-2f, o.py, p.py, msg);
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(2e-2f, o.lid, p.lid, msg);
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(2e-2f, o.dim, p.dim, msg);
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(1e-2f, o.dizzy, p.dizzy, msg);
    }
  }
  TEST_ASSERT_EQUAL_INT(kMotionPosesN, k);
  TEST_ASSERT_EQUAL_INT(kMotionCuesN, cueI);
}

void runMotionTests() {
  RUN_TEST(test_motion_level_angle_and_soft_clamp);
  RUN_TEST(test_motion_pose_imu_reads_gravity_and_rates);
  RUN_TEST(test_motion_level_keeping_springs_to_the_roll_with_overshoot);
  RUN_TEST(test_motion_upside_down_eases_to_150_and_shocks);
  RUN_TEST(test_motion_marble_rolls_to_the_low_side_and_returns);
  RUN_TEST(test_motion_spin_makes_dizzy_then_ufff);
  RUN_TEST(test_motion_orientation_cues_and_pose);
  RUN_TEST(test_motion_calm_in_a_hand_not_on_a_stand);
  RUN_TEST(test_motion_gyro_bias_is_learned_at_rest);
  RUN_TEST(test_motion_tap_detector);
  RUN_TEST(test_motion_nod_yes_and_no);
  RUN_TEST(test_motion_face_answers_and_keeps_its_mood);
  RUN_TEST(test_motion_neutral_pose_draws_the_same_and_roll_turns_the_eyes);
  RUN_TEST(test_motion_nod_answers_a_claude_request);
  RUN_TEST(test_motion_matches_eyes_js);
}
