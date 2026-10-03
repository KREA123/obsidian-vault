// SoulOS 5 "Glass": the aura, the frosted buffer and the glass primitives (Glass.h).
#include <unity.h>

#include <cstdlib>
#include <vector>

#include "Canvas.h"
#include "Glass.h"

using namespace suflet;

static Rgb px(const std::vector<uint16_t>& fb, int w, int x, int y) { return Rgb::from565(fb[(size_t)y * w + x]); }
static int lum(Rgb c) { return c.r * 3 + c.g * 6 + c.b; }

static GlassLayer& fresh(GlassTone t = GlassTone::Default) {
  static GlassLayer g;
  TEST_ASSERT_TRUE(g.begin(480, 480));
  g.setTone(t);
  g.rebuild();
  g.setOn(true);
  g.setLevel(1);
  g.setOffset(0, 0);
  return g;
}

static void test_glass_aura_has_the_soul_colours_and_stays_dark() {
  GlassLayer& g = fresh();
  const Rgb ember = Rgb::from565(g.auraAt((int)(0.24f * 480), (int)(0.86f * 480)));
  const Rgb night = Rgb::from565(g.auraAt((int)(0.80f * 480), (int)(0.22f * 480)));
  const Rgb mid = Rgb::from565(g.auraAt(240, 240));
  TEST_ASSERT_TRUE(ember.r > ember.b + 40);  // warm, lower left
  TEST_ASSERT_TRUE(night.b > night.r + 40);  // blue, upper right
  TEST_ASSERT_TRUE(lum(mid) < 10 * 90);      // deep near-black between the glows
  // the frosted copy is the same field, blurred further: close to the aura, never identical everywhere
  int diff = 0;
  for (int y = 0; y < 480; y += 7)
    for (int x = 0; x < 480; x += 7) {
      const Rgb a = Rgb::from565(g.auraAt(x, y)), f = Rgb::from565(g.frostAt(x, y));
      TEST_ASSERT_TRUE(abs(a.r - f.r) < 70 && abs(a.b - f.b) < 70);
      if (g.auraAt(x, y) != g.frostAt(x, y)) ++diff;
    }
  TEST_ASSERT_TRUE(diff > 100);
}

static void test_glass_tone_changes_the_state_glow_and_rebuilds_once() {
  GlassLayer& g = fresh(GlassTone::Default);
  const uint32_t n0 = g.rebuilds;
  TEST_ASSERT_FALSE(g.rebuild());  // nothing changed: no work
  const Rgb before = Rgb::from565(g.auraAt(213, 115));
  TEST_ASSERT_TRUE(g.setTone(GlassTone::Ice));
  TEST_ASSERT_TRUE(g.rebuild());
  TEST_ASSERT_FALSE(g.rebuild());
  TEST_ASSERT_EQUAL_UINT32(n0 + 1, g.rebuilds);
  const Rgb ice = Rgb::from565(g.auraAt(213, 115));
  TEST_ASSERT_TRUE(ice.b > before.b + 20 && ice.r < before.r);  // the glow behind the eyes turned ice
  g.setTone(GlassTone::Default);
  g.rebuild();
}

static void test_glass_background_is_black_when_off_and_honours_the_clip() {
  GlassLayer& g = fresh();
  std::vector<uint16_t> fb(480 * 480, 0x1234);
  Canvas cv(480, 480, fb.data());
  cv.setClip(Rect{100, 100, 200, 160});
  g.background(cv);
  TEST_ASSERT_EQUAL_UINT16(0x1234, fb[50 * 480 + 50]);  // outside the clip: untouched
  TEST_ASSERT_EQUAL_UINT16(g.auraAt(150, 130), fb[130 * 480 + 150]);
  g.setOn(false);
  g.background(cv);
  TEST_ASSERT_EQUAL_UINT16(0, fb[130 * 480 + 150]);  // standby: true black
  g.setOn(true);
  // drift / tilt move the read window, nothing is re-rendered
  const uint32_t n = g.rebuilds;
  const uint16_t right = g.auraAt(153, 130);
  TEST_ASSERT_TRUE(g.setOffset(3, 0));
  TEST_ASSERT_EQUAL_UINT16(right, g.auraAt(150, 130));
  TEST_ASSERT_EQUAL_UINT32(n, g.rebuilds);
  TEST_ASSERT_TRUE(g.setOffset(99, -99) && g.offsetX() == GlassLayer::kMargin && g.offsetY() == -GlassLayer::kMargin);
  g.setOffset(0, 0);
  // the fade: half level is about half as bright
  g.setLevel(0.5f);
  g.background(cv);
  const Rgb half = px(fb, 480, 150, 130), full = Rgb::from565(g.auraAt(150, 130));
  TEST_ASSERT_TRUE(lum(half) <= lum(full) / 2 + 40);
  g.setLevel(1);
}

static void test_glass_panel_is_frosted_lit_top_left_and_casts_a_shadow() {
  GlassLayer& g = fresh();
  std::vector<uint16_t> fb(480 * 480, 0);
  Canvas cv(480, 480, fb.data());
  g.background(cv);
  g.panel(cv, 120, 200, 360, 300, 30, GlassStyle::plain());
  // inside: the frosted aura + a white fill = lighter than the frost behind it
  const Rgb in = px(fb, 480, 240, 250), fr = Rgb::from565(g.frostAt(240, 250));
  TEST_ASSERT_TRUE(lum(in) > lum(fr) + 150);
  // the rim catches the light at the top-left, not at the bottom-right
  const Rgb tl = px(fb, 480, 160, 200), br = px(fb, 480, 320, 299);
  TEST_ASSERT_TRUE(lum(tl) > lum(br) + 100);
  // a soft shadow just under the panel, nothing far away
  const Rgb under = px(fb, 480, 240, 304), aura = Rgb::from565(g.auraAt(240, 304));
  TEST_ASSERT_TRUE(lum(under) < lum(aura));
  TEST_ASSERT_EQUAL_UINT16(g.auraAt(240, 340), fb[340 * 480 + 240]);
  // an accent glow tints the outside
  std::vector<uint16_t> fb2(480 * 480, 0);
  Canvas c2(480, 480, fb2.data());
  g.setOn(false);
  g.panel(c2, 120, 200, 360, 300, 30, GlassStyle::accent(Rgb(255, 162, 58), 0.6f, 0.1f));
  const Rgb glow = px(fb2, 480, 240, 194);
  TEST_ASSERT_TRUE(glow.r > glow.b + 20);
  g.setOn(true);
}

static void test_glass_panel_stays_inside_the_clip_and_rim_shapes_skip_the_middle() {
  GlassLayer& g = fresh();
  std::vector<uint16_t> fb(480 * 480, 0);
  Canvas cv(480, 480, fb.data());
  cv.setClip(Rect{0, 0, 480, 240});
  g.panel(cv, 100, 200, 380, 300, 20, GlassStyle::plain());
  for (int y = 240; y < 480; ++y)
    for (int x = 0; x < 480; ++x) TEST_ASSERT_EQUAL_UINT16(0, fb[(size_t)y * 480 + x]);
  cv.clearClip();
  // a capsule bent along the top rim: lit on the arc, nothing at the centre
  std::vector<uint16_t> f2(480 * 480, 0);
  Canvas c2(480, 480, f2.data());
  g.setOn(false);
  g.capsuleArc(c2, 240, 240, 218, 16, -1.9f, -1.24f, GlassStyle::plain());
  TEST_ASSERT_TRUE(lum(px(f2, 480, 240, 22)) > 150);
  TEST_ASSERT_EQUAL_UINT16(0, f2[240 * 480 + 240]);
  TEST_ASSERT_EQUAL_UINT16(0, f2[22 * 480 + 40]);  // beyond the end cap
  // a full glass annulus (the dial's track)
  std::vector<uint16_t> f3(480 * 480, 0);
  Canvas c3(480, 480, f3.data());
  g.band(c3, 240, 240, 211, 12, GlassStyle::plain());
  TEST_ASSERT_TRUE(lum(px(f3, 480, 240, 29)) > 150 && lum(px(f3, 480, 451, 240)) > 150 &&
                   lum(px(f3, 480, 240, 451)) > 150);
  TEST_ASSERT_EQUAL_UINT16(0, f3[240 * 480 + 240]);
  TEST_ASSERT_TRUE(c3.clipRect().x1 == 480 && c3.clipRect().y1 == 480);  // the clip is given back
  g.setOn(true);
}

static void test_glass_tone_change_builds_in_the_background_then_swaps() {
  GlassLayer& g = fresh(GlassTone::Default);
  const uint16_t before = g.auraAt(213, 115);
  const uint32_t n = g.rebuilds;
  g.setTone(GlassTone::Amber);
  int frames = 0;
  bool swapped = false;
  while (!swapped && frames < 100) {
    swapped = g.step(64);
    ++frames;
    if (!swapped) TEST_ASSERT_EQUAL_UINT16(before, g.auraAt(213, 115));  // the old aura stays on screen meanwhile
  }
  TEST_ASSERT_TRUE(swapped);
  TEST_ASSERT_TRUE(frames >= 4 && frames <= 12);  // ~8 slices of 64 rows, never one long stall
  TEST_ASSERT_EQUAL_UINT32(n + 1, g.rebuilds);
  const Rgb amber = Rgb::from565(g.auraAt(213, 115));
  TEST_ASSERT_TRUE(amber.r > amber.b + 30);
  // the same as a one-shot build of that tone
  GlassLayer ref;
  TEST_ASSERT_TRUE(ref.begin(480, 480));
  ref.setTone(GlassTone::Amber);
  ref.rebuild();
  int diff = 0;
  for (int y = 0; y < 480; y += 5)
    for (int x = 0; x < 480; x += 5) diff += g.auraAt(x, y) != ref.auraAt(x, y) || g.frostAt(x, y) != ref.frostAt(x, y);
  TEST_ASSERT_EQUAL_INT(0, diff);
  g.setTone(GlassTone::Default);
  g.rebuild();
}

void runGlassTests() {
  RUN_TEST(test_glass_aura_has_the_soul_colours_and_stays_dark);
  RUN_TEST(test_glass_tone_changes_the_state_glow_and_rebuilds_once);
  RUN_TEST(test_glass_tone_change_builds_in_the_background_then_swaps);
  RUN_TEST(test_glass_background_is_black_when_off_and_honours_the_clip);
  RUN_TEST(test_glass_panel_is_frosted_lit_top_left_and_casts_a_shadow);
  RUN_TEST(test_glass_panel_stays_inside_the_clip_and_rim_shapes_skip_the_middle);
}
