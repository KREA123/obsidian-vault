// Parity tests of the C++ eyes engine against the web engine (eyes.js).
// The fixture is produced by node from eyes.js: tools/gen_eye_fixture.js.
#include <unity.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

#include "EyeRender.h"
#include "EyeRig.h"
#include "eye_fixture.h"

using namespace suflet;
using namespace suflet::eyes;

static void test_eyes_birth_roll_matches_eyes_js() {
  for (const RollCase& c : kRollCases) {
    const RollResult r = rollFromMac(c.mac);
    TEST_ASSERT_EQUAL_INT(c.design, r.design);
    TEST_ASSERT_EQUAL_INT(c.rarity, (int)r.rarity);
    TEST_ASSERT_EQUAL_INT(c.rarity, (int)kDesigns[r.design].rarity);
  }
}

static void test_eyes_roll_rates_follow_the_table() {
  int counts[(int)Rarity::Count] = {0};
  uint32_t s = 99;
  const int n = 200000;
  for (int i = 0; i < n; ++i) {
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    const uint32_t lo = s;
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    ++counts[(int)roll(s & 0xFFFF, lo).rarity];
  }
  for (int i = 0; i < (int)Rarity::Count; ++i) {
    const double p = (double)counts[i] / n;
    TEST_ASSERT_FLOAT_WITHIN((float)(kRarityRate[i] * 0.12 + 0.0008), (float)kRarityRate[i], (float)p);
  }
}

static void test_eyes_tables_cover_the_collection() {
  TEST_ASSERT_EQUAL_INT(120, kDesignCount);
  TEST_ASSERT_EQUAL_INT(31, (int)X_Count);
  TEST_ASSERT_EQUAL_STRING("original", kDesigns[0].id);
  TEST_ASSERT_EQUAL_INT(X_smirk, exprByName("smirk"));
  TEST_ASSERT_EQUAL_INT(X_wake, exprByName("wake"));
  TEST_ASSERT_EQUAL_INT(-1, exprByName("nope"));
  TEST_ASSERT_EQUAL_STRING("laugh", exprName(X_laugh));
}

static void test_eyes_rig_matches_eyes_js_traces() {
  for (const RigTrace& tr : kTraces) {
    EyeRig rig(tr.seed);
    const int steps = (int)lroundf(tr.secs * 32);
    int ei = 0, si = 0;
    for (int i = 0; i < steps; ++i) {
      const float t = i / 32.0f;
      while (ei < tr.nEv && tr.ev[ei].t <= t + 1e-6f) {
        const RigEvent& e = tr.ev[ei++];
        switch (e.kind) {
          case 0: rig.setExpression(e.name); break;
          case 1: rig.react(exprByName(e.name), e.a); break;
          case 2: rig.lookAt(e.a, e.b); break;
          case 3: rig.lookNone(); break;
          case 4: rig.blink((int)e.a); break;
          case 5: rig.hop(); break;
          default: break;
        }
      }
      rig.update(1.0f / 32);
      if (i % 4 != 3) continue;
      const float* want = tr.samples + si * kTraceFields;
      const float got[] = {rig.ch(Ch_scale), rig.ch(Ch_sy),     rig.ch(Ch_lidL),  rig.ch(Ch_lidR),
                           rig.ch(Ch_smileL), rig.ch(Ch_pupilL), rig.ch(Ch_altL), rig.ch(Ch_shift),
                           rig.ch(Ch_bob),   rig.ch(Ch_rot),    rig.ch(Ch_zzz),  rig.pupilL(0),
                           rig.pupilL(1),    rig.pupilR(0),     rig.eyeGaze(0),  rig.closed(),
                           rig.level()};
      static_assert(sizeof(got) / sizeof(got[0]) == kTraceFields, "fields");
      for (int k = 0; k < kTraceFields; ++k) {
        if (fabsf(got[k] - want[k]) > 2e-3f + 2e-3f * fabsf(want[k])) {
          char msg[96];
          snprintf(msg, sizeof msg, "%s t=%.3f field %d: c++ %.5f js %.5f", tr.name, (i + 1) / 32.0, k, got[k], want[k]);
          TEST_FAIL_MESSAGE(msg);
        }
      }
      ++si;
    }
    TEST_ASSERT_EQUAL_INT(tr.nSamples, si);
  }
}

static void test_eyes_reaction_returns_to_the_mood() {
  EyeRig rig(5);
  rig.setExpression(X_happy);
  rig.update(0.5f);
  rig.setExpression(X_laugh);
  TEST_ASSERT_TRUE(rig.reacting());
  TEST_ASSERT_EQUAL_INT(X_laugh, rig.expression());
  for (int i = 0; i < 80; ++i) rig.update(1.0f / 32);  // 2.5 s > laugh 1.9 s
  TEST_ASSERT_FALSE(rig.reacting());
  TEST_ASSERT_EQUAL_INT(X_happy, rig.expression());
  rig.react(X_love, 1.0f);  // a mood as a one-shot
  TEST_ASSERT_EQUAL_INT(X_love, rig.expression());
  for (int i = 0; i < 48; ++i) rig.update(1.0f / 32);
  TEST_ASSERT_EQUAL_INT(X_happy, rig.expression());
}

static void test_eyes_render_every_design_and_expression_inside_the_disc() {
  const int W = 240, H = 240;
  std::vector<uint16_t> fb(W * H);
  Canvas cv(W, H, fb.data());
  EyeRenderer r;
  TEST_ASSERT_TRUE(r.begin(W, H));
  for (int d = 0; d < kDesignCount; ++d) {
    EyeRig rig(hashStr(kDesigns[d].id) ^ 0x5eed);
    rig.setExpression(d % X_Count);
    for (int i = 0; i < 24; ++i) rig.update(1.0f / 32);
    std::fill(fb.begin(), fb.end(), 0);
    cv.resetDirty();
    r.render(cv, rig, kDesigns[d], 120, 120, 200);
    int lit = 0;
    for (int y = 0; y < H; ++y)
      for (int x = 0; x < W; ++x) {
        if (!fb[y * W + x]) continue;
        ++lit;
        const float dx = x + 0.5f - 120, dy = y + 0.5f - 120;
        TEST_ASSERT_TRUE_MESSAGE(dx * dx + dy * dy <= 101.0f * 101.0f, kDesigns[d].id);  // clipped to D/2
        TEST_ASSERT_TRUE(x >= cv.dirty().x0 && x < cv.dirty().x1 && y >= cv.dirty().y0 && y < cv.dirty().y1);
      }
    if (d % X_Count != X_goodbye) TEST_ASSERT_TRUE_MESSAGE(lit > 200, kDesigns[d].id);
  }
}

static void test_eyes_blink_closes_and_reopens() {
  EyeRig rig(9);
  rig.update(0.1f);
  rig.blink(1);
  float maxC = 0;
  for (int i = 0; i < 40; ++i) {
    rig.update(1.0f / 120);
    maxC = fmaxf(maxC, rig.closed());
  }
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.0f, maxC);
  rig.update(0.5f);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, rig.closed());
}

void runEyeTests() {
  RUN_TEST(test_eyes_tables_cover_the_collection);
  RUN_TEST(test_eyes_birth_roll_matches_eyes_js);
  RUN_TEST(test_eyes_roll_rates_follow_the_table);
  RUN_TEST(test_eyes_rig_matches_eyes_js_traces);
  RUN_TEST(test_eyes_reaction_returns_to_the_mood);
  RUN_TEST(test_eyes_blink_closes_and_reopens);
  RUN_TEST(test_eyes_render_every_design_and_expression_inside_the_disc);
}
