// SoulOS Alive (os/DESIGN-ALIVE.md, Alive.h, Palette.h, OsAlive.cpp): the born palette against the web for every
// birth x body, the pebble outline, the dial's maths, the lid wipe's timing and geometry, the eye-reaction table,
// speech, and the OS wiring (the eye slot, the lids over the glass, the dial, the reactions, Look).
#include <unity.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <string>
#include <vector>

#include "Alive.h"
#include "Frame.h"
#include "Gestures.h"
#include "Memory.h"
#include "Os.h"
#include "Palette.h"
#include "PsramAlloc.h"
#include "StoneData.h"
#include "palette_fixture.h"

using namespace suflet;

namespace {

const uint32_t kNow = 1790359080u;  // a Friday, 18:38 local

uint32_t hex(Rgb c) { return (uint32_t)c.r << 16 | (uint32_t)c.g << 8 | c.b; }

struct Dev {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  Os os{&alarms};
  TouchGestures tg;
  DisplayGeometry g = displays::kLcd28;
  std::vector<uint16_t> fb = std::vector<uint16_t>(480 * 480);
  Canvas cv{480, 480, fb.data()};
  FrameComposer comp{&cv};
  bool finger = false;
  float fx = 0, fy = 0;
  uint32_t clock = kNow;
  float frac = 0;
  Inputs in;
  bool render = true;
  eyes::ImuSample imu;  // fed every frame: flat on the table unless a test leans it

  explicit Dev(int design = 5, bool reduced = false) {
    os.settings().booted = 1;
    os.settings().ai = (uint8_t)AiMode::Claude;
    os.settings().reduceMotion = reduced ? 1 : 0;
    BirthInfo b;
    b.design = design;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = 1234;
    os.begin(g, b);
    NetInfo n;
    n.configured = n.connected = true;
    n.keyClaude = true;
    n.ssid = "home";
    os.setNet(n);
    tg.setMode(TouchMode::Text);
    os.setClock(clock);
    in.hour = 18.6f;
  }
  void step(float dt = 1.0f / 30) {
    frac += dt;
    while (frac >= 1) {
      frac -= 1;
      ++clock;
    }
    os.setClock(clock);
    os.imu(dt, imu);
    tg.update(finger, fx, fy, dt);
    TouchEv e;
    while (tg.poll(e)) os.touch(e);
    os.update(dt, brain);
    brain.update(dt, in);
    if (render) comp.compose(os);
  }
  void run(float s) {
    for (int i = 0; i < (int)(s * 30 + 0.5f); ++i) step();
  }
  void tap(float x, float y, float after = 0.5f) {  // design px
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(0.08f);
    finger = false;
    run(after);
  }
  void swipe(float x0, float y0, float x1, float y1, int steps = 6) {
    finger = true;
    for (int i = 0; i <= steps; ++i) {
      fx = g.s(x0 + (x1 - x0) * i / steps);
      fy = g.s(y0 + (y1 - y0) * i / steps);
      step();
    }
    finger = false;
    run(0.4f);
  }
  // the face's centre on the glass now (panel px), from its layout spring
  float eyesY() const {
    FaceLayoutT l = os.faceInputs(brain).layout;
    return 240 + l.cy * 480;
  }
  int fullDiff() {  // the incremental canvas vs the same state drawn whole
    std::vector<uint16_t> ref(480 * 480, 0);
    Canvas rc(480, 480, ref.data());
    os.render(rc);
    os.face().render(rc);
    RectList lids;
    os.renderOverlay(rc, RectList(), lids);
    int d = 0;
    for (size_t i = 0; i < ref.size(); ++i)
      if (ref[i] != fb[i]) ++d;
    return d;
  }
};

}  // namespace

// ------------------------------------------------------------------ palette ---

static void test_alive_palette_matches_the_web_for_every_birth_and_body() {
  int bad = 0;
  for (const PaletteCase& k : kPaletteCases) {
    const BornPalette P = bornPaletteFor(k.design, (Body)k.body);
    const uint32_t got[9] = {hex(P.e1), hex(P.e2), hex(P.b1), hex(P.peb), hex(P.peb2), hex(P.pebe), hex(P.on1), hex(P.on2), hex(P.onb)};
    const uint32_t want[9] = {k.e1, k.e2, k.b1, k.peb, k.peb2, k.pebe, k.on1, k.on2, k.onb};
    for (int i = 0; i < 9; ++i)
      if (got[i] != want[i]) ++bad;
  }
  TEST_ASSERT_EQUAL_INT(600, (int)(sizeof kPaletteCases / sizeof kPaletteCases[0]));
  TEST_ASSERT_EQUAL_INT(0, bad);
}

static void test_alive_palette_examples_bodies_and_ink() {
  // DESIGN-ALIVE.md §2's table
  BornPalette P = bornPaletteFor(0, Body::Silver);  // #001 Original
  TEST_ASSERT_EQUAL_HEX32(0xFFF0C8, hex(P.e1));
  TEST_ASSERT_EQUAL_HEX32(0xFF5A1F, hex(P.e2));
  TEST_ASSERT_EQUAL_HEX32(0xCBCDCF, hex(P.b1));
  TEST_ASSERT_EQUAL_HEX32(0x24221C, hex(P.peb));
  TEST_ASSERT_EQUAL_HEX32(0x3B372E, hex(P.peb2));
  TEST_ASSERT_EQUAL_HEX32(0x666050, hex(P.pebe));
  P = bornPaletteFor(12, Body::Midnight);  // #013 Sunday Toast: brown pupils -> e1's opposite hue
  TEST_ASSERT_EQUAL_HEX32(0xFFD23A, hex(P.e1));
  TEST_ASSERT_EQUAL_HEX32(0x3D95F5, hex(P.e2));
  TEST_ASSERT_EQUAL_HEX32(0x587BC7, hex(P.b1));  // Midnight lifted for black
  P = bornPaletteFor(97, Body::Silver);  // #098 Lollipop: a pink pupil next to pink eyes clashes -> blue
  TEST_ASSERT_EQUAL_HEX32(0x4D64FF, hex(P.e2));
  // the bodies and their lifted b1
  const uint32_t lifted[5] = {0xCBCDCF, 0x7C7F85, 0x587BC7, 0xD2622C, 0xD8C3A2};
  for (int b = 0; b < (int)Body::Count; ++b) TEST_ASSERT_EQUAL_HEX32(lifted[b], hex(bornPaletteFor(0, (Body)b).b1));
  TEST_ASSERT_EQUAL_STRING("Graphite", bodyInfo(Body::Graphite).name);
  // ink: dark on a light accent, Warm White on a dark one; every accent readable on black
  for (int d = 0; d < 120; ++d) {
    const BornPalette Q = bornPaletteFor(d, Body::Graphite);
    double c1[3] = {(double)Q.e1.r, (double)Q.e1.g, (double)Q.e1.b}, c2[3] = {(double)Q.e2.r, (double)Q.e2.g, (double)Q.e2.b};
    TEST_ASSERT_TRUE(palette::luminance(c1) >= 0.29);
    TEST_ASSERT_TRUE(palette::luminance(c2) >= 0.16);
    TEST_ASSERT_EQUAL_HEX32(palette::luminance(c1) > 0.3 ? 0x0B0B0C : 0xFBF4E3, hex(Q.on1));
  }
  // the HSL round trip the lift is built on
  const double c[3] = {210, 98, 44};
  const palette::Hsl h = palette::toHsl(c);
  double o[3];
  palette::fromHsl(h.h, h.s, h.l, o);
  for (int i = 0; i < 3; ++i) TEST_ASSERT_FLOAT_WITHIN(0.01, c[i], o[i]);
}

// ------------------------------------------------------------------- stone ---

static void test_alive_stone_is_the_margaritar_outline() {
  const int n = stone::kPoints;
  float minY = 1, maxY = -1, widest = 0, widestY = 0, baseL = 0, baseR = 0;
  for (int i = 0; i < n; ++i) {
    const float x = stone::kXY[2 * i], y = stone::kXY[2 * i + 1];
    TEST_ASSERT_TRUE(fabsf(x) <= 0.5001f && fabsf(y) <= 0.5001f);
    minY = fminf(minY, y);
    maxY = fmaxf(maxY, y);
    if (fabsf(x) > widest) widest = fabsf(x), widestY = y;
    if (y > 0.4999f) (x > 0 ? baseR : baseL) = x;
  }
  TEST_ASSERT_FLOAT_WITHIN(0.002f, -0.5f, minY);  // the domed crown at the top
  TEST_ASSERT_FLOAT_WITHIN(0.002f, 0.5f, maxY);   // the flat sitting base
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, widest);
  TEST_ASSERT_TRUE(widestY < 0.05f && widestY > -0.2f);  // the shoulders: the widest point just above the middle
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.30f, baseR);         // the base: 60 % of the width
  TEST_ASSERT_FLOAT_WITHIN(0.01f, -0.30f, baseL);
  for (int i = 0; i < n; ++i) {  // mirror-symmetric: (x, y) has (-x, y)
    const float x = stone::kXY[2 * i], y = stone::kXY[2 * i + 1];
    float best = 1;
    for (int j = 0; j < n; ++j)
      best = fminf(best, fabsf(stone::kXY[2 * j] + x) + fabsf(stone::kXY[2 * j + 1] - y));
    TEST_ASSERT_TRUE(best < 0.004f);
  }
}

// -------------------------------------------------------------------- dial ---

static void test_alive_dial_drag_fling_and_detents() {
  alive::Dial d;
  d.reset(18, 2, false);
  TEST_ASSERT_EQUAL_INT(2, d.focused());
  d.grab();
  d.drag(-88);  // one pebble of finger to the left: the next pebble comes to the bottom
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 3.0f, d.rot());
  TEST_ASSERT_EQUAL_INT(3, d.focused());
  d.release(-880);  // a fling: v = 10 pebbles / s, it lands on round(rot + v / 3.2)
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 10.0f, d.velocity());
  TEST_ASSERT_EQUAL_INT(6, d.target());
  d.release(-88000);  // the speed is capped at 16
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 16.0f, d.velocity());
  d.release(0);  // let go still: the nearest detent
  TEST_ASSERT_EQUAL_INT(3, d.target());
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);  // the snap spring (95 / 17) settles
  TEST_ASSERT_FALSE(d.settling());
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 3.0f, d.rot());
  // a loose drag between detents finds its own way to one
  d.grab();
  d.drag(-40);
  d.release(0);
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_EQUAL_INT(3, d.focused());
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 3.0f, d.rot());
  // nudges (a swipe / the side button) and the wrap around the ring
  d.nudge(-1);
  d.nudge(-1);
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_EQUAL_INT(1, d.focused());
  d.nudge(-1);
  d.nudge(-1);
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_EQUAL_INT(17, d.focused());
  TEST_ASSERT_TRUE(d.rot() >= 0 && d.rot() < 18);  // it lands wrapped
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, -9.0f, d.wrapU(9));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 8.0f, d.wrapU(-10));
  // reduced motion: it snaps
  d.nudge(1);
  d.update(1.0f / 30, true);
  TEST_ASSERT_EQUAL_INT(0, d.focused());
  TEST_ASSERT_FALSE(d.settling());
}

static void test_alive_dial_places_grows_fades_and_hits() {
  alive::Dial d;
  d.reset(18, 0, false);
  alive::Dial::Pebble f = d.place(0);
  TEST_ASSERT_TRUE(f.focus);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 233, f.x);  // at the bottom, on r = 170 + 6
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 233 + 176, f.y);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.5f, f.scale);  // the focused one grows x1.5
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, f.alpha);
  const alive::Dial::Pebble r = d.place(1), l = d.place(17);
  TEST_ASSERT_FALSE(r.focus);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 233 + 170 * sinf(28 * 3.14159265f / 180), r.x);  // every 28°, the next to the right
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 233 - 170 * sinf(28 * 3.14159265f / 180), l.x);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, r.scale);
  // the top stays free for the clock: fading out past 132-158°
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, d.place(4).alpha);  // 112°
  TEST_ASSERT_TRUE(d.place(5).alpha > 0 && d.place(5).alpha < 1);  // 140°
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, d.place(6).alpha);  // 168°
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, d.place(9).alpha);
  // half way between two detents both are 1.16x, neither focused-filled at exactly 0.5
  d.grab();
  d.drag(-44);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 1 + 0.5f * (1 - 0.5f * 1.35f), d.place(0).scale);
  d.release(0);  // (exactly half way rounds on to the next one)
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_EQUAL_INT(1, d.focused());
  d.reset(18, 0, false);
  // hits: the focused pebble, a neighbour, nothing in the faded top, nothing far away
  TEST_ASSERT_EQUAL_INT(0, d.hit(233, 409));
  TEST_ASSERT_EQUAL_INT(1, d.hit(r.x + 10, r.y - 10));
  TEST_ASSERT_EQUAL_INT(-1, d.hit(233, 233 - 170));
  TEST_ASSERT_EQUAL_INT(-1, d.hit(233, 233));
  // the opening: the pebbles spread from the bottom (small, faint), then sit
  d.reset(18, 0, true);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, d.openness());
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, d.place(2).alpha);
  for (int i = 0; i < 4; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_TRUE(d.openness() > 0.3f && d.place(0).scale < 1.5f);
  for (int i = 0; i < 40; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, d.openness());
  // where the eyes look: down at the focused one at rest, sideways while it turns
  float gx, gy;
  d.gaze(gx, gy);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, gx);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.95f, gy);
  d.grab();
  d.drag(-30);
  d.gaze(gx, gy);
  TEST_ASSERT_TRUE(gx < -0.3f && gy > 0.8f);  // the next pebble comes from the right... the eyes meet it
}

static void test_alive_dial_spins_to_a_pebble_opens_it_and_follows_the_tilt() {
  alive::Dial d;
  d.reset(18, 0, false);
  d.spinTo(16, true, false);  // the shortest way: -2, not +16
  TEST_ASSERT_EQUAL_INT(-2, d.target());
  int opened = -1;
  for (int i = 0; i < 90 && opened < 0; ++i) opened = d.update(1.0f / 30, false);
  TEST_ASSERT_EQUAL_INT(16, opened);  // landed -> open it
  TEST_ASSERT_EQUAL_INT(16, d.focused());
  // the tilt: past ~17° (0.3 g) it steps once every 0.45 s, toward the lean; not while a finger is on it
  TEST_ASSERT_FALSE(d.tilt(0.2f, 10.0f));
  TEST_ASSERT_TRUE(d.tilt(0.5f, 10.0f));
  TEST_ASSERT_EQUAL_INT(17, d.target());
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);
  TEST_ASSERT_FALSE(d.tilt(0.5f, 10.2f));  // too soon
  TEST_ASSERT_TRUE(d.tilt(-0.5f, 10.5f));
  TEST_ASSERT_EQUAL_INT(16, d.target());
  for (int i = 0; i < 60; ++i) d.update(1.0f / 30, false);
  d.grab();
  TEST_ASSERT_FALSE(d.tilt(0.6f, 20.0f));
}

// --------------------------------------------------------------- lid wipe ---

static void test_alive_lid_wipe_timing_and_geometry() {
  using alive::LidWipe;
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.29f, LidWipe::kTotal);
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, LidWipe::coverAt(0));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.25f, LidWipe::coverAt(0.04f));  // in-quad
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, LidWipe::coverAt(0.08f));   // shut
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, LidWipe::coverAt(0.11f));   // held 40 ms
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, LidWipe::coverAt(0.29f));
  float lo = 1;
  for (float t = 0.12f; t < 0.29f; t += 0.001f) lo = fminf(lo, LidWipe::coverAt(t));
  TEST_ASSERT_TRUE(lo < -0.05f && lo > -0.2f);  // the out-back 1.8 opening overshoots a little
  // the screen changes exactly once, when they are shut
  LidWipe w;
  w.start();
  int mids = 0, frames = 0;
  float atMid = 0;
  while (w.active() && frames < 100) {
    const bool closing = w.closing();
    if (w.update(1.0f / 30)) {
      ++mids;
      atMid = w.cover();
      TEST_ASSERT_TRUE(closing);
    }
    ++frames;
  }
  TEST_ASSERT_EQUAL_INT(1, mids);
  TEST_ASSERT_TRUE(atMid >= 0.99f);
  TEST_ASSERT_TRUE(frames >= 8 && frames <= 10);  // ~9 frames at 30 fps
  // shut: every pixel of the round glass is under a lid; open: none
  float rx, ry, u, l;
  LidWipe::geometry(480, 480, 1, rx, ry, u, l);
  for (int a = 0; a < 360; a += 5)
    for (float r = 0; r <= 240; r += 20) {
      const float x = 240 + r * cosf(a * 0.0174533f) - 240, y = 240 + r * sinf(a * 0.0174533f);
      const float k = sqrtf(fmaxf(0.0f, 1 - (x / rx) * (x / rx)));
      TEST_ASSERT_TRUE(y <= u + ry * k + 0.5f || y >= l - ry * k - 0.5f);
    }
  int y0, y1;
  LidWipe::openBand(480, 480, 1, y0, y1);
  TEST_ASSERT_EQUAL_INT(y0, y1);  // nothing of the screen shows
  LidWipe::openBand(480, 480, 0, y0, y1);
  TEST_ASSERT_EQUAL_INT(0, y0);
  TEST_ASSERT_EQUAL_INT(480, y1);
  LidWipe::openBand(480, 480, 0.5f, y0, y1);
  TEST_ASSERT_TRUE(y0 > 0 && y1 < 480 && y0 < 240 && y1 > 240);
}

// --------------------------------------------------------------- reactions ---

static void test_alive_reaction_table() {
  using alive::Event;
  using alive::reaction;
  TEST_ASSERT_EQUAL_INT(1, reaction(Event::Tap).blinks);  // any tap on a control: blink x1
  TEST_ASSERT_EQUAL_INT(-1, reaction(Event::Tap).expr);
  TEST_ASSERT_TRUE(reaction(Event::FingerDown).look);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.95f, reaction(Event::DialSettle).lookY);  // down at the focused pebble
  TEST_ASSERT_TRUE(reaction(Event::OpenApp).lids && reaction(Event::OpenApp).blinks == 1);
  TEST_ASSERT_TRUE(reaction(Event::CloseApp).lids && reaction(Event::CloseApp).blinks == 1);
  TEST_ASSERT_EQUAL_INT(eyes::X_thinking, reaction(Event::Thinking).expr);  // squint while waiting for the AI
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.7f, reaction(Event::Thinking).hold);
  TEST_ASSERT_EQUAL_INT(eyes::X_working, reaction(Event::ClaudeWorking).expr);
  TEST_ASSERT_EQUAL_INT(eyes::X_surprised, reaction(Event::Notify).expr);  // widen on a notification
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.9f, reaction(Event::Notify).hold);
  TEST_ASSERT_TRUE(reaction(Event::Notify).look && reaction(Event::Notify).lookY < 0);  // up at the banner
  TEST_ASSERT_EQUAL_INT(eyes::X_shocked, reaction(Event::ClaudeNeeds).expr);
  TEST_ASSERT_EQUAL_INT(eyes::X_approve, reaction(Event::Success).expr);  // happy on success
  TEST_ASSERT_EQUAL_INT(eyes::X_sad, reaction(Event::Failure).expr);      // sad only on a real failure
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 2.6f, reaction(Event::Failure).hold);
  TEST_ASSERT_EQUAL_INT(eyes::X_confused, reaction(Event::Cancel).expr);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.4f, reaction(Event::Cancel).hold);
  TEST_ASSERT_EQUAL_INT(eyes::X_sleepy, reaction(Event::Night).expr);
  TEST_ASSERT_EQUAL_INT(eyes::X_dizzy, reaction(Event::Shake).expr);  // dizzy on shake
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 2.2f, reaction(Event::Shake).hold);
  TEST_ASSERT_EQUAL_INT(eyes::X_listening, reaction(Event::Listening).expr);
  for (int e = 0; e < (int)Event::Count; ++e) TEST_ASSERT_TRUE(strcmp(alive::eventName((Event)e), "?") != 0);
  // night: 23-06 h
  TEST_ASSERT_TRUE(alive::isNight(23) && alive::isNight(0) && alive::isNight(5));
  TEST_ASSERT_FALSE(alive::isNight(6) || alive::isNight(22) || alive::isNight(12));
}

static void test_alive_speech_topics_timing_and_breath() {
  TEST_ASSERT_EQUAL_INT((int)LineTopic::Morning, (int)alive::greetingTopic(7));
  TEST_ASSERT_EQUAL_INT((int)LineTopic::Night, (int)alive::greetingTopic(23));
  TEST_ASSERT_EQUAL_INT((int)LineTopic::Night, (int)alive::greetingTopic(3));
  TEST_ASSERT_EQUAL_INT((int)LineTopic::Hello, (int)alive::greetingTopic(15));
  alive::Speech s;
  s.say("Hi!", 2.5f, 0.3f);
  TEST_ASSERT_FALSE(s.showing());  // the eyes settle first
  TEST_ASSERT_TRUE(s.pending());
  s.update(0.31f);
  TEST_ASSERT_TRUE(s.showing() && s.rising());
  TEST_ASSERT_TRUE(s.rise(false) < 0.5f);
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, s.rise(true));  // reduced motion: no rise
  s.update(0.4f);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, s.rise(false));
  s.update(2.2f);
  TEST_ASSERT_FALSE(s.showing());
  TEST_ASSERT_TRUE(s.greetDue(0));
  s.greeted(5);
  TEST_ASSERT_FALSE(s.greetDue(20));
  TEST_ASSERT_TRUE(s.greetDue(25.1f));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, alive::breath(1.375f, true));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.012f, alive::breath(1.375f, false));  // a quarter of 5.5 s: the top
}

// -------------------------------------------------------------------- the OS ---

static void test_alive_os_eye_slot_on_every_app_screen() {
  Dev d;
  d.run(0.5f);
  TEST_ASSERT_FLOAT_WITHIN(0.015f, 1.0f, d.os.faceInputs(d.brain).layout.k);  // standby: full size (breathing ±1.2 %)
  const View apps[] = {View::Settings, View::Alarms, View::Notes, View::Today, View::Weather, View::Maps,
                       View::Claude, View::Convert, View::AppsSettings, View::Memory, View::Timer};
  for (View v : apps) {
    d.os.go(v);
    d.run(0.7f);
    const FaceLayoutT l = d.os.faceInputs(d.brain).layout;
    TEST_ASSERT_FLOAT_WITHIN_MESSAGE(1e-4f, 0.30f, l.k, viewName(v));
    TEST_ASSERT_FLOAT_WITHIN_MESSAGE(0.5f, 118.0f, d.eyesY(), viewName(v));  // centre y = 118 px on the 480 glass
    TEST_ASSERT_FLOAT_WITHIN_MESSAGE(0.01f, 0.30f, d.os.face().layoutK(), viewName(v));  // the spring got there
    // the black disc under the eyes, over the content (a pixel beside the eyes, inside the disc)
    TEST_ASSERT_EQUAL_UINT16_MESSAGE(0, d.fb[120 * 480 + 240 - 58], viewName(v));
  }
  // face moments keep big eyes
  d.os.go(View::Talk);
  d.run(0.6f);
  TEST_ASSERT_TRUE(d.os.faceInputs(d.brain).layout.k > 0.6f);
  // the keyboard: small but never below k 0.24
  d.os.openKeyboard(1);
  d.run(0.6f);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, alive::kMinK, d.os.faceInputs(d.brain).layout.k);
}

static void test_alive_os_lid_wipe_opens_and_closes_apps_inside_the_frame() {
  Dev d;
  d.run(0.5f);
  d.swipe(330, 240, 150, 240);  // the dial
  d.run(0.6f);
  TEST_ASSERT_EQUAL_INT((int)View::Launcher, (int)d.os.view());
  // the dial opens on Talk (a face moment, no lids): one pebble on, to Today
  d.finger = true;
  for (int k = 0; k <= 22; ++k) {
    d.fx = d.g.s(300 - 4.0f * k);
    d.fy = d.g.s(330);
    d.step();
  }
  for (int k = 0; k < 6; ++k) d.step();
  d.finger = false;
  d.run(1.0f);
  const View want = d.os.appView(d.os.launcherIndex());
  TEST_ASSERT_EQUAL_INT((int)View::Today, (int)want);
  // open the focused app: a tap in the middle
  d.fx = d.g.s(233);
  d.fy = d.g.s(300);
  d.finger = true;
  d.step();
  d.step();
  d.finger = false;
  int frames = 0, black = 0;
  bool sawShut = false, sawWipe = false;
  while (frames < 30) {
    d.step();
    ++frames;
    if (d.os.lidsActive()) sawWipe = true;
    if (d.os.lidCover() >= 0.999f) {
      sawShut = true;
      int lit = 0;
      for (int i = 0; i < 480 * 480; i += 7)
        if (d.fb[i]) ++lit;
      black = lit;
      TEST_ASSERT_EQUAL_INT((int)want, (int)d.os.view());  // the app is there, behind the shut lids
    }
    if (sawWipe && !d.os.lidsActive()) break;
  }
  TEST_ASSERT_TRUE(sawWipe && sawShut);
  TEST_ASSERT_EQUAL_INT(0, black);  // shut: the whole glass is black (the eyes under the lids too)
  TEST_ASSERT_TRUE(frames <= 12);   // 290 ms
  TEST_ASSERT_EQUAL_INT(0, d.fullDiff());  // after: exactly what a full redraw shows
  // closing it: the same, the other way
  d.run(0.5f);
  d.os.back();
  TEST_ASSERT_TRUE(d.os.lidsActive());
  d.run(0.4f);
  TEST_ASSERT_FALSE(d.os.lidsActive());
  // between apps there are no lids; reduced motion: none at all (the blink stays: it is information)
  d.os.go(View::Settings);
  d.run(0.4f);
  d.os.go(View::AiMode);
  TEST_ASSERT_FALSE(d.os.lidsActive());
  Dev r(5, true);
  r.run(0.3f);
  r.os.go(View::Alarms);
  TEST_ASSERT_FALSE(r.os.lidsActive());
}

static void test_alive_os_dial_by_swipe_tap_and_tilt() {
  Dev d;
  d.run(0.4f);
  d.swipe(330, 240, 150, 240);
  d.run(0.8f);
  const int start = d.os.launcherIndex();
  // a slow drag of one pebble's width: one step
  d.finger = true;
  for (int k = 0; k <= 22; ++k) {
    d.fx = d.g.s(300 - 4.0f * k);
    d.fy = d.g.s(330);
    d.step();
  }
  for (int k = 0; k < 6; ++k) d.step();  // held still: no fling
  d.finger = false;
  d.run(1.0f);
  TEST_ASSERT_EQUAL_INT((start + 1) % d.os.appCount(), d.os.launcherIndex());
  // the eyes look down at the focused pebble
  FaceInputs in = d.os.faceInputs(d.brain);
  TEST_ASSERT_TRUE(in.look && in.lookY > 0.9f);
  // the tilt: lean it right (0.5 g sideways) and the dial steps toward the lean, about twice a second
  d.imu.ax = 0.5f;
  d.imu.az = 0.866f;
  const int before = d.os.launcherIndex();
  d.run(1.2f);
  d.imu.ax = 0;
  d.imu.az = 1;
  d.run(1.5f);
  const int steps = (d.os.launcherIndex() - before + d.os.appCount()) % d.os.appCount();
  TEST_ASSERT_TRUE(steps >= 1 && steps <= 3);
  // a tap on the left neighbour: it spins there and opens it
  const int target = (d.os.launcherIndex() + d.os.appCount() - 1) % d.os.appCount();
  const View want = d.os.appView(target);
  const alive::Dial::Pebble pb = d.os.dial().place(target);
  d.tap(pb.x, pb.y, 1.2f);
  TEST_ASSERT_EQUAL_INT((int)want, (int)d.os.view());
}

// 1.9 (critic): a lean turns a list's wheel through the whole OS (it never did: the gravity average that the
// lean is measured against was only fed on the frosted glass, and SoulOS Alive's glass is flat)
static void test_alive_os_a_lean_turns_the_settings_wheel() {
  Dev d;
  d.run(0.5f);
  d.os.go(View::Settings);
  d.run(1.0f);
  TEST_ASSERT_TRUE(d.os.wheelView());
  const int f0 = d.os.wheel().focused();
  // tip it forward 37° (0.6 g) and hold it for 2 s: the focused row moves on
  d.imu.ay = 0.6f;
  d.imu.az = 0.8f;
  d.run(2.0f);
  const int f1 = d.os.wheel().focused();
  TEST_ASSERT_TRUE(f1 != f0);
  TEST_ASSERT_TRUE(abs(f1 - f0) <= 5);  // one row every 0.45 s while the lean lasts (~1.7 s for 0.6 g)
  // held there: it stops (the lean is against how SOUL is held); level again: it does not turn back
  d.run(4.0f);
  const int f2 = d.os.wheel().focused();
  d.imu.ay = 0;
  d.imu.az = 1;
  d.run(3.0f);
  TEST_ASSERT_EQUAL_INT(f2, d.os.wheel().focused());
}

// 1.9 (critic): held steadily at an angle (a normal grip, 20° sideways = 0.35 g), the home dial moves at most once
// (the absolute gravity spun it one pebble every 0.45 s for as long as SOUL was held); level again, it stays
static int dialSteps(const Dev& d, int from) { return (d.os.launcherIndex() - from + d.os.appCount()) % d.os.appCount(); }

static void test_alive_os_a_steady_grip_does_not_spin_the_dial() {
  Dev d;
  d.run(0.4f);
  d.swipe(330, 240, 150, 240);
  d.run(0.8f);
  TEST_ASSERT_EQUAL_INT((int)View::Launcher, (int)d.os.view());
  const int start = d.os.launcherIndex();
  d.imu.ax = 0.35f;
  d.imu.az = 0.937f;
  int moves = 0, last = start;
  for (int i = 0; i < 300; ++i) {  // 10 s
    d.step();
    if (d.os.launcherIndex() != last) ++moves, last = d.os.launcherIndex();
  }
  TEST_ASSERT_TRUE(moves <= 1);
  d.imu.ax = 0;
  d.imu.az = 1;
  for (int i = 0; i < 90; ++i) {
    d.step();
    if (d.os.launcherIndex() != last) ++moves, last = d.os.launcherIndex();
  }
  TEST_ASSERT_TRUE(moves <= 1);
  // a deliberate lean the other way (past level) still steps the dial that way
  d.imu.ax = -0.5f;
  d.imu.az = 0.866f;
  const int before = d.os.launcherIndex();
  d.run(0.6f);
  TEST_ASSERT_TRUE(dialSteps(d, before) >= d.os.appCount() - 2 && dialSteps(d, before) != 0);
}

// 1.9 (critic): the OS clock is a double: after 12 days of uptime a float clock stopped advancing (1/30 s rounded
// to 0), and from ~1 day the fling's speed came out wrong. Start at 1e6 s (11.6 days) and everything still works.
static void test_alive_os_works_after_weeks_of_uptime() {
  Dev d;
  d.os.setUptimeForTest(1.0e6);
  d.tg.setClockForTest(1.0e6);
  d.brain.setClockForTest(1.0e6);
  d.run(0.4f);
  const double t0 = d.os.uptime();
  d.run(1.0f);
  TEST_ASSERT_TRUE(fabs(d.os.uptime() - t0 - 1.0) < 0.01);
  d.swipe(330, 240, 150, 240);
  d.run(0.8f);
  TEST_ASSERT_EQUAL_INT((int)View::Launcher, (int)d.os.view());
  // a fling: a fast drag of ~2 pebbles' width, let go at speed, coasts further than the finger went
  const int start = d.os.launcherIndex();
  d.finger = true;
  for (int k = 0; k <= 5; ++k) {
    d.fx = d.g.s(380 - 36.0f * k);
    d.fy = d.g.s(330);
    d.step();
  }
  d.finger = false;
  d.run(1.5f);
  TEST_ASSERT_TRUE(dialSteps(d, start) >= 3 && dialSteps(d, start) <= 8);
  // the tilt's rate limit still lets it step
  const int before = d.os.launcherIndex();
  d.imu.ax = 0.5f;
  d.imu.az = 0.866f;
  d.run(1.0f);
  TEST_ASSERT_TRUE(dialSteps(d, before) >= 1);
  // a double tap on the face (the touch gestures' own clock)
  TouchGestures tg;
  tg.setMode(TouchMode::Face);
  tg.setClockForTest(1.0e6);
  bool dbl = false;
  for (int k = 0; k < 2; ++k) {
    for (int i = 0; i < 2; ++i) tg.update(true, 240, 240, 1.0f / 30);
    for (int i = 0; i < 3; ++i) tg.update(false, 240, 240, 1.0f / 30);
  }
  TouchEv e;
  while (tg.poll(e)) dbl |= e.e == Ev::DoubleTap;
  TEST_ASSERT_TRUE(dbl);
}

// 1.9 (critic): the dial's pebble sprites are made in PSRAM (PsramAlloc.h), reuse evicted buffers and are built
// a few at a time: opening the dial built 68 (11 in one frame) and four flings 130 more
static void test_alive_dial_sprites_are_few_and_in_psram() {
  Dev d;
  d.run(0.4f);
  const uint64_t psram0 = psramStats().bytes;
  const uint32_t b0 = d.os.spriteBuilds();
  d.swipe(330, 240, 150, 240);
  d.run(1.0f);
  const uint32_t opening = d.os.spriteBuilds() - b0;
  TEST_ASSERT_TRUE(opening > 0 && opening <= 40);
  TEST_ASSERT_TRUE(psramStats().bytes - psram0 > 40000);  // the sprites' buffers went through psramAlloc
  TEST_ASSERT_TRUE(d.os.spriteCount() <= 40);
  uint32_t worst = 0;
  const uint32_t b1 = d.os.spriteBuilds(), a1 = psramStats().allocs;
  for (int f = 0; f < 4; ++f) {  // four flings, alternating
    d.finger = true;
    for (int k = 0; k <= 5; ++k) {
      d.fx = d.g.s(f % 2 ? 90 + 36.0f * k : 380 - 36.0f * k);
      d.fy = d.g.s(330);
      const uint32_t b = d.os.spriteBuilds();
      d.step();
      worst = std::max(worst, d.os.spriteBuilds() - b);
    }
    d.finger = false;
    for (int i = 0; i < 45; ++i) {
      const uint32_t b = d.os.spriteBuilds();
      d.step();
      worst = std::max(worst, d.os.spriteBuilds() - b);
    }
  }
  const uint32_t flings = d.os.spriteBuilds() - b1, allocs = psramStats().allocs - a1;
  printf("  sprites: opening %u, 4 flings %u (%u allocations), worst frame %u\n", (unsigned)opening, (unsigned)flings,
         (unsigned)allocs, (unsigned)worst);
  TEST_ASSERT_TRUE(flings <= 100);
  TEST_ASSERT_TRUE(allocs <= 12);  // an evicted sprite's buffers are reused: no heap churn once the 40 slots exist
  TEST_ASSERT_TRUE(worst <= 6);
  // and the screen at rest is exactly what a full redraw draws (no stand-in left behind)
  d.run(1.0f);
  TEST_ASSERT_EQUAL_INT(0, d.fullDiff());
}

// 1.9 (critic): a list's rows are built when they change, not three times a frame (a 200-fact Memory list copied
// every fact's text each time)
static void test_alive_wheel_rows_are_cached() {
  Dev d;
  SoulMemory mem;
  char t[160];
  for (int i = 0; i < 200; ++i) {
    snprintf(t, sizeof t, "Ana likes %d: coffee with oat milk in the morning", i);
    mem.remember(t, FactKind::Preference, FactSrc::User, 1790000000u + (uint32_t)i * 600);
  }
  d.os.setMemory(&mem);
  d.run(0.4f);
  d.os.go(View::Memory);
  d.run(1.0f);
  TEST_ASSERT_TRUE(d.os.wheelView());
  uint32_t b = d.os.wheelRowsBuilt();
  d.run(3.0f);  // at rest: nothing to rebuild
  TEST_ASSERT_TRUE(d.os.wheelRowsBuilt() - b <= 1);
  b = d.os.wheelRowsBuilt();
  for (int i = 0; i < 6; ++i) d.os.wheelTurn(1), d.run(0.3f);  // turning: the same rows
  TEST_ASSERT_TRUE(d.os.wheelRowsBuilt() - b <= 1);
  TEST_ASSERT_EQUAL_INT(6 + 1, d.os.wheel().focused());  // (Search is row 0, the default focus row 1)
  // a fact forgotten elsewhere (the AI, the phone): the list follows at once
  b = d.os.wheelRowsBuilt();
  const int n = d.os.wheel().count();
  mem.forgetId(mem.at(0).id);
  d.run(0.1f);
  TEST_ASSERT_EQUAL_INT(n - 1, d.os.wheel().count());
  TEST_ASSERT_TRUE(d.os.wheelRowsBuilt() - b >= 1);
  // Settings: its values follow the clock, rebuilt at most about once a second at rest
  d.os.go(View::Settings);
  d.run(1.0f);
  b = d.os.wheelRowsBuilt();
  d.run(3.0f);
  TEST_ASSERT_TRUE(d.os.wheelRowsBuilt() - b <= 4);
  d.os.setMemory(nullptr);
}

static void test_alive_os_reactions_follow_the_table() {
  Dev d;
  d.run(1.0f);
  // a notification: the eyes widen and look up at the banner
  d.os.toast("Ana: home for dinner at 6?", Rgb::hex(0xFFF6E4));
  d.run(0.1f);
  TEST_ASSERT_EQUAL_INT(eyes::X_surprised, d.os.face().rig().expression());
  FaceInputs in = d.os.faceInputs(d.brain);
  TEST_ASSERT_TRUE(in.look && in.lookY < 0);
  // a confirmation is no notification
  d.run(2.0f);
  d.os.toast("Alarm set 07:00", Rgb::hex(0xC9F2E4));
  d.run(0.1f);
  TEST_ASSERT_TRUE(d.os.face().rig().expression() != eyes::X_surprised);
  // a shake: dizzy (the Brain's reaction, the spiral pupils)
  d.run(3.0f);
  d.brain.event(Ev::Shake);
  d.run(0.2f);
  TEST_ASSERT_EQUAL_INT(eyes::X_dizzy, d.os.face().rig().expression());
  // night at rest on the face: sleepy
  Dev n;
  n.clock = kNow - 18 * 3600 - 38 * 60 + 90 * 60;  // 01:30
  n.run(1.5f);
  TEST_ASSERT_EQUAL_INT((int)FaceState::Sleep, (int)n.os.faceInputs(n.brain).state);
  TEST_ASSERT_EQUAL_INT(eyes::X_sleepy, n.os.face().rig().backMood());
  // a tap on a control: one blink
  d.run(3.0f);
  d.os.go(View::Settings);
  d.run(0.5f);
  d.tap(233, 172, 0.0f);  // Brightness
  d.step();
  TEST_ASSERT_TRUE(d.os.face().rig().closed() > 0.05f);
}

static void test_alive_os_look_previews_births_and_keeps_the_body() {
  Dev d(5);
  d.os.go(View::MySoul);
  d.run(0.5f);
  const uint32_t e1 = hex(d.os.palette().e1);
  TEST_ASSERT_FALSE(d.os.previewing());
  TEST_ASSERT_FALSE(d.os.lookOpen());
  d.tap(172, 326, 0.6f);  // My SOUL's card: Look
  TEST_ASSERT_TRUE(d.os.lookOpen());
  d.tap(363, 214, 0.6f);  // › : the next birth
  TEST_ASSERT_TRUE(d.os.previewing());
  TEST_ASSERT_EQUAL_INT(6, d.os.shownDesign());
  TEST_ASSERT_EQUAL_INT(6, d.os.face().design());  // swapped during a blink
  TEST_ASSERT_EQUAL_HEX32(hex(bornPaletteFor(6, Body::Silver).e1), hex(d.os.palette().e1));
  d.tap(103, 214, 0.6f);  // ‹ : back to its own
  TEST_ASSERT_FALSE(d.os.previewing());
  TEST_ASSERT_EQUAL_HEX32(e1, hex(d.os.palette().e1));
  d.tap(103, 214, 0.6f);  // ‹ again, then "Back to {name}"
  TEST_ASSERT_TRUE(d.os.previewing());
  d.tap(233, 284, 0.6f);
  TEST_ASSERT_FALSE(d.os.previewing());
  TEST_ASSERT_EQUAL_INT(5, d.os.face().design());
  // the body: the fourth swatch is Ember; it is the palette's b1 and survives a restart
  d.tap(233 + 52, 342, 0.3f);
  TEST_ASSERT_EQUAL_INT((int)Body::Ember, (int)d.os.body());
  TEST_ASSERT_EQUAL_HEX32(0xD2622C, hex(d.os.palette().b1));
  uint8_t buf[64];
  const size_t n = d.os.saveSettings(buf, sizeof buf);
  TEST_ASSERT_EQUAL_INT(32, (int)n);  // the blob keeps its size: the new bytes were padding
  Dev e(5);
  TEST_ASSERT_TRUE(e.os.loadSettings(buf, n));
  TEST_ASSERT_EQUAL_INT((int)Body::Ember, (int)e.os.body());
  TEST_ASSERT_EQUAL_HEX32(0xD2622C, hex(e.os.palette().b1));
  buf[25] = 77;  // garbage in the old padding: back to Silver, the blob still loads
  TEST_ASSERT_TRUE(e.os.loadSettings(buf, n));
  TEST_ASSERT_EQUAL_INT((int)Body::Silver, (int)e.os.body());
}

static void test_alive_os_speech_on_wake_and_standby_is_the_eyes_alone() {
  Dev d;
  d.run(1.0f);
  TEST_ASSERT_NULL(d.os.speechLine());
  d.tap(233, 330, 0.6f);  // a touch on the face: the eyes glide up, a line under them
  TEST_ASSERT_TRUE(d.os.peeking());
  TEST_ASSERT_FLOAT_WITHIN(0.01f, alive::kPeek.k, d.os.faceInputs(d.brain).layout.k);  // (breathing ±1.2 %)
  TEST_ASSERT_NOT_NULL(d.os.speechLine());
  d.run(Os::kPeekS + 0.5f);  // back to standby: nothing but the eyes
  TEST_ASSERT_FALSE(d.os.peeking());
  TEST_ASSERT_NULL(d.os.speechLine());
  std::vector<uint16_t> ref(480 * 480, 0);
  Canvas rc(480, 480, ref.data());
  d.os.render(rc);
  int lit = 0;
  for (uint16_t v : ref)
    if (v) ++lit;
  TEST_ASSERT_EQUAL_INT(0, lit);
  // a second wake within 20 s: no new greeting
  d.tap(233, 330, 0.6f);
  TEST_ASSERT_NULL(d.os.speechLine());
  // every 3rd boop: a compliment
  d.tap(233, 330, 0.5f);
  d.tap(233, 330, 0.6f);
  TEST_ASSERT_NOT_NULL(d.os.speechLine());
}

static void test_alive_flat_surfaces_and_the_fast_round_rect() {
  // Canvas::roundRect's span path draws exactly the pixels of the distance-field fill it replaced
  std::vector<uint16_t> a(200 * 160), b(200 * 160);
  Canvas ca(200, 160, a.data()), cb(200, 160, b.data());
  srand(7);
  for (int k = 0; k < 300; ++k) {
    const float x0 = rand() % 180 - 10 + (rand() % 100) / 100.0f, y0 = rand() % 140 - 10 + (rand() % 100) / 100.0f;
    const float x1 = x0 + 1 + rand() % 120 + (rand() % 100) / 100.0f, y1 = y0 + 1 + rand() % 90;
    const float r = (rand() % 400) / 10.0f, al = k % 3 ? 1.0f : 0.5f;
    const Rgb c(rand() & 255, rand() & 255, rand() & 255);
    if (k % 5 == 0) {
      const Rect cl{rand() % 100, rand() % 80, 100 + rand() % 100, 80 + rand() % 80};
      ca.setClip(cl);
      cb.setClip(cl);
    } else {
      ca.clearClip();
      cb.clearClip();
    }
    ca.roundRect(x0, y0, x1, y1, r, c, al);
    const float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f, hw = (x1 - x0) * 0.5f, hh = (y1 - y0) * 0.5f;
    const float rr = fminf(r, fminf(hw, hh));
    cb.fillSdf(x0, y0, x1, y1, [=](float px, float py) { return Canvas::sdRoundBox(px, py, cx, cy, hw, hh, rr); }, c, al);
  }
  TEST_ASSERT_EQUAL_MEMORY(b.data(), a.data(), a.size() * 2);
  // SoulOS Alive's glass: flat, no aura buffers, pure black behind, a panel = one fill + the 2 px highlight
  TEST_ASSERT_TRUE(glass().flat());
  TEST_ASSERT_FALSE(glass().ready());
  Dev d;
  d.os.go(View::Settings);
  d.run(0.8f);
  const BornPalette& P = d.os.palette();
  TEST_ASSERT_EQUAL_HEX16(P.peb.to565(), d.fb[(int)d.g.s(316) * 480 + (int)d.g.s(120)]);  // inside the focused row's pebble
  TEST_ASSERT_EQUAL_UINT16(0, d.fb[240 * 480 + 12]);                                       // pure black beside it
}

static void test_alive_frame_pipeline_dial_and_lids_equal_a_full_redraw() {
  Dev d;
  d.run(0.5f);
  d.swipe(330, 240, 150, 240);
  int worst = 0;
  for (int i = 0; i < 20; ++i) {  // the dial opening and a fling settling
    d.step();
    worst = std::max(worst, d.fullDiff());
  }
  d.swipe(330, 330, 180, 330);
  for (int i = 0; i < 40; ++i) {
    d.step();
    worst = std::max(worst, d.fullDiff());
  }
  TEST_ASSERT_EQUAL_INT(0, worst);
  // the lid wipe opening: every frame after the lids shut equals a full redraw (lids included)
  d.tap(233, 300, 0.0f);
  for (int i = 0; i < 12; ++i) {
    d.step();
    if (!d.os.lidsClosing()) worst = std::max(worst, d.fullDiff());
  }
  TEST_ASSERT_EQUAL_INT(0, worst);
}

void runAliveTests() {
  RUN_TEST(test_alive_palette_matches_the_web_for_every_birth_and_body);
  RUN_TEST(test_alive_palette_examples_bodies_and_ink);
  RUN_TEST(test_alive_stone_is_the_margaritar_outline);
  RUN_TEST(test_alive_dial_drag_fling_and_detents);
  RUN_TEST(test_alive_dial_places_grows_fades_and_hits);
  RUN_TEST(test_alive_dial_spins_to_a_pebble_opens_it_and_follows_the_tilt);
  RUN_TEST(test_alive_lid_wipe_timing_and_geometry);
  RUN_TEST(test_alive_reaction_table);
  RUN_TEST(test_alive_speech_topics_timing_and_breath);
  RUN_TEST(test_alive_os_eye_slot_on_every_app_screen);
  RUN_TEST(test_alive_os_lid_wipe_opens_and_closes_apps_inside_the_frame);
  RUN_TEST(test_alive_os_dial_by_swipe_tap_and_tilt);
  RUN_TEST(test_alive_os_a_lean_turns_the_settings_wheel);
  RUN_TEST(test_alive_os_a_steady_grip_does_not_spin_the_dial);
  RUN_TEST(test_alive_os_works_after_weeks_of_uptime);
  RUN_TEST(test_alive_dial_sprites_are_few_and_in_psram);
  RUN_TEST(test_alive_wheel_rows_are_cached);
  RUN_TEST(test_alive_os_reactions_follow_the_table);
  RUN_TEST(test_alive_os_look_previews_births_and_keeps_the_body);
  RUN_TEST(test_alive_os_speech_on_wake_and_standby_is_the_eyes_alone);
  RUN_TEST(test_alive_flat_surfaces_and_the_fast_round_rect);
  RUN_TEST(test_alive_frame_pipeline_dial_and_lids_equal_a_full_redraw);
}
