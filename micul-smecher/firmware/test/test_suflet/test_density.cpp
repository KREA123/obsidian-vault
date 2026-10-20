// The density layer (lib/Suflet/src/Density.h, firmware/SOUL-S.md): SOUL M keeps every 1.9.0 number, SOUL S
// gets the same millimetres where a human is concerned (the type floor, a fingertip) and a fitted layout elsewhere;
// AMOLED burn-in care. The pictures of both glasses are pinned elsewhere: tools/perf_bench.py --hashes / --check
// (M pixel-identical to 1.9.0) and the S audit in test_audit.cpp.
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <unity.h>

#include <vector>

#include "../../sim/alive_states.h"
#include "Density.h"

using namespace suflet;

namespace {
// the eyes' drawn height per unit of layout k (fraction of the glass): Density.cpp's kEyeH
constexpr float kEyeH = 50.0f / (480.0f * 0.30f);
}  // namespace

static void test_density_m_is_the_reference_glass() {
  const Density d = Density::forGlass(displays::kLcd28);
  TEST_ASSERT_TRUE(d.reference);
  TEST_ASSERT_FALSE(d.emissive);
  TEST_ASSERT_EQUAL_FLOAT(1, d.sigma);
  TEST_ASSERT_EQUAL_FLOAT(1, d.ts);
  TEST_ASSERT_EQUAL_FLOAT(1, d.cs);
  TEST_ASSERT_EQUAL_INT((int)fonts::TypeRamp::M, (int)d.ramp);
  // every token is the 1.9.0 constant, bit for bit (the 2.8C draws the frames it drew)
  const Density ref;
  const alive::DialSpec dial0;
  const alive::WheelSpec wheel0;
  TEST_ASSERT_EQUAL_MEMORY(&dial0, &d.dial, sizeof dial0);
  TEST_ASSERT_EQUAL_MEMORY(&wheel0, &d.wheel, sizeof wheel0);
  TEST_ASSERT_EQUAL_MEMORY(&ref.answer, &d.answer, sizeof ref.answer);
  TEST_ASSERT_EQUAL_MEMORY(&ref.ask, &d.ask, sizeof ref.ask);
  TEST_ASSERT_EQUAL_FLOAT(205, d.rimR);
  TEST_ASSERT_EQUAL_FLOAT(48, d.pillMinH);
  TEST_ASSERT_EQUAL_FLOAT(alive::kCard.k, d.card.k);
  TEST_ASSERT_EQUAL_FLOAT(alive::kCard.cy, d.card.cy);
  TEST_ASSERT_EQUAL_FLOAT(alive::kApps.cy, d.apps.cy);
  TEST_ASSERT_EQUAL_FLOAT(alive::Dial::kR, d.dial.r);
  TEST_ASSERT_EQUAL_FLOAT(alive::Wheel::kY, d.wheel.y);
  // the physical sizes it stands for: 18 px = 2.63 mm, 44 px = 6.43 mm on the Ø70.13 mm disc
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 2.63f, 18 / d.pxPerMm);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 6.43f, 44 / d.pxPerMm);
  // an Os on the 2.8C: M's ramp, M's dial and wheel
  alive_states::Rig s;
  TEST_ASSERT_EQUAL_INT((int)fonts::TypeRamp::M, (int)fonts::ramp());
  TEST_ASSERT_EQUAL_INT(22, fonts::caption().px);
  TEST_ASSERT_EQUAL_FLOAT(170, s.os.dial().spec().r);
  TEST_ASSERT_EQUAL_FLOAT(290, s.os.wheel().spec().y);
}

static void test_density_s_keeps_the_millimetres() {
  const DisplayGeometry& g = displays::kAmoled175;
  const Density d = Density::forGlass(g);
  TEST_ASSERT_FALSE(d.reference);
  TEST_ASSERT_TRUE(d.emissive);
  // 466 px over Ø43.76 mm vs 480 over Ø70.13: 10.65 vs 6.84 px/mm; one design px is 1.60x bigger in px on S
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 10.65f, d.pxPerMm);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.60f, d.sigma);
  // the floors in mm: the same on both glasses
  const Density m = Density::forGlass(displays::kLcd28);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, m.typeFloorPx / m.pxPerMm, d.typeFloorPx / d.pxPerMm);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, m.targetPx / m.pxPerMm, d.targetPx / d.pxPerMm);
  TEST_ASSERT_EQUAL_INT(28, (int)lroundf(d.typeFloorPx));
  TEST_ASSERT_EQUAL_INT(68, (int)lroundf(d.targetPx));
  // the S type ramp: s = round(28 (m / 18)^0.7); nothing under the floor, the hierarchy kept
  TEST_ASSERT_EQUAL_INT((int)fonts::TypeRamp::S, (int)d.ramp);
  TEST_ASSERT_EQUAL_INT(28, Density::rampPx(18, 28));
  TEST_ASSERT_EQUAL_INT(32, Density::rampPx(22, 28));
  TEST_ASSERT_EQUAL_INT(37, Density::rampPx(27, 28));
  TEST_ASSERT_EQUAL_INT(40, Density::rampPx(30, 28));
  TEST_ASSERT_EQUAL_INT(45, Density::rampPx(36, 28));
  fonts::setRamp(fonts::TypeRamp::S);
  TEST_ASSERT_EQUAL_INT(28, fonts::tag().px);
  TEST_ASSERT_EQUAL_INT(32, fonts::caption().px);
  TEST_ASSERT_EQUAL_INT(37, fonts::body().px);
  TEST_ASSERT_EQUAL_INT(40, fonts::name().px);
  TEST_ASSERT_EQUAL_INT(45, fonts::title().px);
  TEST_ASSERT_TRUE(fonts::tag().px >= d.typeFloorPx - 0.5f);
  TEST_ASSERT_TRUE(fonts::caption().px >= d.secondaryPx);
  TEST_ASSERT_TRUE(fonts::tag().px < fonts::caption().px && fonts::caption().px < fonts::body().px &&
                   fonts::body().px < fonts::name().px && fonts::name().px < fonts::title().px);
  fonts::setRamp(fonts::TypeRamp::M);
  TEST_ASSERT_EQUAL_INT(18, fonts::tag().px);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 37.0f / 27.0f, d.ts);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 32.0f / 22.0f, d.cs);
}

static void test_density_s_dial_pebbles_are_fingertips() {
  const Density d = Density::forGlass(displays::kAmoled175);
  const alive::DialSpec& s = d.dial;
  const float k = displays::kAmoled175.k();
  // a pebble's short side is the target (6.4 mm), the focused one 1.5x; the stone keeps its 52 : 58
  TEST_ASSERT_TRUE(s.w * k >= d.targetPx - 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 58.0f / 52.0f, s.h / s.w);
  // the focused pebble's foot inside the safe circle
  TEST_ASSERT_TRUE(s.r + 6 + s.h * 1.5f * 0.5f <= d.safeR + 0.01f);
  // neighbours never touch: the focused half + a pebble's half + 12 px between the centres
  alive::Dial dial;
  dial.setSpec(s);
  dial.reset(18, 0, false);
  const alive::Dial::Pebble f = dial.place(0), n1 = dial.place(1);
  TEST_ASSERT_TRUE(hypotf(f.x - n1.x, f.y - n1.y) >= s.w * 1.5f * 0.5f + s.w * 0.5f + 11.9f);
  // how many show: 7 on S (fewer, bigger), 9+ on M
  auto shown = [](const alive::DialSpec& sp) {
    alive::Dial dl;
    dl.setSpec(sp);
    dl.reset(18, 0, false);
    int n = 0;
    for (int i = 0; i < 18; ++i) n += dl.place(i).alpha >= 0.3f;
    return n;
  };
  TEST_ASSERT_EQUAL_INT(7, shown(s));
  TEST_ASSERT_TRUE(shown(alive::DialSpec()) >= 9);
  // and none of them reaches the clock capsule at the top: every shown pebble's box is below the capsule
  for (int i = 0; i < 18; ++i) {
    const alive::Dial::Pebble p = dial.place(i);
    if (p.alpha < 0.02f) continue;
    const float top = p.y - s.h * p.scale * 0.5f;
    TEST_ASSERT_TRUE_MESSAGE(top > 233 - (d.rimR - d.rimHalf) || fabsf(p.x - 233) > 110, "pebble under the clock capsule");
  }
  // the finger: a drag of one pebble's arc moves one pebble
  dial.grab();
  dial.drag(-s.dragPx);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, dial.rot());
  // the fact under the eyes, the name above the focused pebble, the eyes above the fact
  TEST_ASSERT_TRUE(s.factY < 233 + s.nameR);
  TEST_ASSERT_TRUE(s.nameR < s.r + 6 - s.h * 0.75f);
  const float eyesBottom = 233 + d.apps.cy * 466 + kEyeH * 466 * d.apps.k * 0.5f;
  TEST_ASSERT_TRUE(eyesBottom < s.factY);
}

static void test_density_s_wheel_slot_and_ask_fit() {
  const Density d = Density::forGlass(displays::kAmoled175);
  const float k = displays::kAmoled175.k(), C = 233;
  // the eye slot sits right under the rim capsule, a little bigger than M's
  const float eyesH = kEyeH * 466 * d.card.k, eyesTop = C + d.card.cy * 466 - eyesH * 0.5f;
  TEST_ASSERT_TRUE(d.card.k > alive::kCard.k && d.card.k >= alive::kMinK);
  TEST_ASSERT_TRUE(eyesTop >= C - (d.rimR - d.rimHalf) + 4);
  const float slotBottom = eyesTop + eyesH;
  // the wheel: focused row and its neighbours are targets, the upper one clears the slot, all inside r 212
  alive::Wheel w;
  w.setSpec(d.wheel);
  w.reset(10, 4);
  const alive::Wheel::Place f = w.place(4), up = w.place(3), dn = w.place(5);
  TEST_ASSERT_TRUE(up.h * k >= d.targetPx - 0.5f && dn.h * k >= d.targetPx - 0.5f);
  TEST_ASSERT_TRUE(up.y - up.h * 0.5f >= slotBottom + 8);
  TEST_ASSERT_TRUE(f.visible && up.visible && dn.visible);
  TEST_ASSERT_TRUE(dn.w > 200);  // the row under the focus is still a readable width
  for (const alive::Wheel::Place& p : {f, up, dn}) {
    const float r = 22 * d.ts * p.scale * 0.2929f;
    for (int sx = -1; sx <= 1; sx += 2)
      for (int sy = -1; sy <= 1; sy += 2)
        TEST_ASSERT_TRUE(hypotf(sx * (p.w * 0.5f - r), p.y + sy * (p.h * 0.5f - r) - C) <= d.wheel.r + 0.5f);
  }
  TEST_ASSERT_EQUAL_INT(5, w.hit(C, dn.y));
  // the band a turning wheel repaints holds every row it can draw
  TEST_ASSERT_TRUE(d.wheel.band0 <= up.y - up.h * 0.5f && d.wheel.band1 >= dn.y + dn.h * 0.5f);
  // Claude asks: two target-sized buttons whose corners are inside the amber ring (r 218 - 4), the shortcut line
  // under them, the pebble under the slot
  const Density::Ask& q = d.ask;
  TEST_ASSERT_TRUE(q.btnH * k >= d.targetPx - 0.5f);
  TEST_ASSERT_TRUE(q.y0 >= slotBottom + 4);
  const float bx = q.btnDx + q.btnW * 0.5f - q.btnH * 0.5f * 0.2929f, by = q.btnY + q.btnH * 0.5f * (1 - 0.2929f) - C;
  TEST_ASSERT_TRUE(hypotf(bx, by) <= 214);
  TEST_ASSERT_TRUE(q.holdY > q.btnY + q.btnH * 0.5f && q.holdY < C + 140);
  // the answer pebble: under the slot, above the bottom rim's words
  TEST_ASSERT_TRUE(d.answer.cy - d.answer.ry >= slotBottom + 4);
  TEST_ASSERT_TRUE(d.answer.cy + d.answer.ry <= C + d.rimR - 16);
  // pills: never under the target
  TEST_ASSERT_TRUE(d.pillMinH * k >= d.targetPx - 0.01f);
}

static void test_density_s_os_on_the_amoled() {
  alive_states::Rig s(true, -1, displays::kAmoled175);
  TEST_ASSERT_EQUAL_INT((int)fonts::TypeRamp::S, (int)fonts::ramp());
  TEST_ASSERT_TRUE(s.os.density().emissive);
  TEST_ASSERT_FALSE(s.os.density().reference);
  // the dial on S: 7 pebbles show, a tap on the focused one opens it
  TEST_ASSERT_TRUE(alive_states::setup(s, "apps"));
  TEST_ASSERT_EQUAL_INT(View::Launcher, s.os.view());
  std::vector<Os::Control> cs;
  s.os.controls(cs);
  int pebbles = 0;
  for (const Os::Control& c : cs) pebbles += c.id >= 1000 && c.id < 2000;
  TEST_ASSERT_EQUAL_INT(7, pebbles);
  const alive::Dial::Pebble f = s.os.dial().place(s.os.dial().focused());
  s.tap(f.x, f.y, 1.0f);
  TEST_ASSERT_TRUE(s.os.view() != View::Launcher);
  fonts::setRamp(fonts::TypeRamp::M);
}

// AMOLED burn-in: on standby the face wanders a few px over minutes (whole px: no extra repaints in between); an
// LCD's does not; after 20 min asleep at night the AMOLED goes dark
static void test_density_burn_in_care() {
  float dx, dy;
  burnin::drift(1234.0, 466, false, dx, dy);
  TEST_ASSERT_EQUAL_FLOAT(0, dx);
  TEST_ASSERT_EQUAL_FLOAT(0, dy);
  float most = 0, moved = 0, px0 = 0;
  for (int t = 0; t < 3600; t += 5) {
    burnin::drift(t, 466, true, dx, dy);
    most = fmaxf(most, fmaxf(fabsf(dx), fabsf(dy)) * 466);
    if (t) moved = fmaxf(moved, fabsf(dx * 466 - px0));
    px0 = dx * 466;
    TEST_ASSERT_FLOAT_WITHIN(1e-3f, roundf(dx * 466), dx * 466);  // whole pixels
  }
  TEST_ASSERT_TRUE(most >= burnin::kDriftPx - 0.01f && most <= burnin::kDriftPx + 0.01f);
  TEST_ASSERT_TRUE(moved <= 1.01f);  // at most a pixel every 5 s
  // the standby layout on S drifts, on M it does not
  alive_states::Rig s(true, -1, displays::kAmoled175), m;
  s.os.setUptimeForTest(200);
  m.os.setUptimeForTest(200);
  TEST_ASSERT_EQUAL_INT(View::Home, s.os.view());
  const FaceLayoutT ls = s.os.faceInputs(s.brain).layout, lm = m.os.faceInputs(m.brain).layout;
  TEST_ASSERT_TRUE(fabsf(ls.cx) > 0 || fabsf(ls.cy) > 0);
  TEST_ASSERT_EQUAL_FLOAT(0, lm.cx);
  TEST_ASSERT_EQUAL_FLOAT(0, lm.cy);
  // lights out: asleep long enough at night -> 0 on the AMOLED, the night glow on the LCD
  TEST_ASSERT_EQUAL_FLOAT(0, s.os.backlightAsleep(2.0f, burnin::kOffAfterS + 1));
  TEST_ASSERT_TRUE(s.os.backlightAsleep(2.0f, burnin::kOffAfterS - 60) > 0);
  TEST_ASSERT_TRUE(s.os.backlightAsleep(14.0f, burnin::kOffAfterS + 1) > 0);  // daytime: an hour first
  TEST_ASSERT_EQUAL_FLOAT(0, s.os.backlightAsleep(14.0f, burnin::kOffAfterDayS + 1));
  TEST_ASSERT_TRUE(m.os.backlightAsleep(2.0f, burnin::kOffAfterS * 10) > 0);
  fonts::setRamp(fonts::TypeRamp::M);
}


// ---- the S screens step (SOUL-S.md §5, os/DESIGN-ALIVE.md §S) ------------------------------------------------

static void sTap(Keyboard& kb, float x, float y) {
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)x, (int16_t)y, 0});
  kb.update(0.1f);
}

// the S keyboard: no key under 5 mm, alphabetical rows as wide as each row's chord, inside the circle; it types
static void test_s_keyboard_has_5mm_keys_and_types() {
  fonts::setRamp(fonts::TypeRamp::S);
  Keyboard kb;
  kb.setGeometry(displays::kAmoled175);
  kb.setDense(true);
  KbConfig c;
  c.placeholder = "New note…";
  kb.open(c);
  TEST_ASSERT_TRUE(kb.dense());
  TEST_ASSERT_EQUAL_INT(31, kb.keyCount());  // 26 letters, ⇧ ⌫, 123, space, ✓
  const float pxPerMm = displays::kAmoled175.pxPerMm();
  TEST_ASSERT_TRUE(kb.rowH() / pxPerMm >= 5.0f);
  std::string order;
  for (int i = 0; i < kb.keyCount(); ++i) {
    const Key& k = kb.key(i);
    TEST_ASSERT_TRUE_MESSAGE((k.x1 - k.x0) / pxPerMm >= 5.0f, "a key under 5 mm");
    for (int sx = 0; sx < 2; ++sx)  // its corners (radius 16, the 45° point) inside the safe circle
      for (int sy = 0; sy < 2; ++sy) {
        const float x = (sx ? k.x1 : k.x0) + (sx ? -4.7f : 4.7f), y = k.y0 + (sy ? kb.rowH() - 4.7f : 4.7f);
        TEST_ASSERT_TRUE(hypotf(x - 233, y - 233) <= 221.35f);
      }
    if (k.id == KeyId::Char && k.cp >= 'a' && k.cp <= 'z') order += (char)k.cp;
  }
  TEST_ASSERT_EQUAL_STRING("abcdefghijklmnopqrstuvwxyz", order.c_str());
  // it types: "hi sol" (the auto-capital), a backspace, the 123 layer and back
  for (const char* p = "hi sol"; *p; ++p) {
    float x, y;
    TEST_ASSERT_TRUE(kb.keyCenter((uint32_t)*p, x, y));
    sTap(kb, x, y);
  }
  TEST_ASSERT_EQUAL_STRING("Hi sol", kb.text().c_str());
  float x, y;
  TEST_ASSERT_TRUE(kb.keyCenter(KeyId::Bksp, x, y));
  sTap(kb, x, y);
  TEST_ASSERT_EQUAL_STRING("Hi so", kb.text().c_str());
  TEST_ASSERT_TRUE(kb.keyCenter(KeyId::Layer, x, y));
  sTap(kb, x, y);
  TEST_ASSERT_EQUAL_INT((int)KbLayer::Num, (int)kb.layer());
  TEST_ASSERT_TRUE(kb.keyCenter((uint32_t)'7', x, y));
  sTap(kb, x, y);
  TEST_ASSERT_EQUAL_STRING("Hi so7", kb.text().c_str());
  for (int i = 0; i < kb.keyCount(); ++i) TEST_ASSERT_TRUE((kb.key(i).x1 - kb.key(i).x0) / pxPerMm >= 5.0f);
  // a hold on a: the tray (ă â à á ä: the Romanian letters are a long-press away, as on M; an English sentence
  // puts them after the others)
  TEST_ASSERT_TRUE(kb.keyCenter(KeyId::Layer, x, y));
  sTap(kb, x, y);
  TEST_ASSERT_TRUE(kb.keyCenter((uint32_t)'a', x, y));
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::HoldStart, (int16_t)x, (int16_t)y, 0});
  TEST_ASSERT_TRUE(kb.trayOpen());
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)x, (int16_t)y, 0});
  TEST_ASSERT_EQUAL_STRING("Hi so7\xC3\xA0", kb.text().c_str());  // à
  // and it draws inside its bounds
  std::vector<uint16_t> fb((size_t)466 * 466, 0);
  Canvas cv(466, 466, fb.data());
  kb.render(cv);
  const Rect b = kb.bounds();
  for (int yy = 0; yy < 466; ++yy)
    for (int xx = 0; xx < 466; ++xx)
      if (fb[(size_t)yy * 466 + xx]) TEST_ASSERT_TRUE(xx >= b.x0 && xx < b.x1 && yy >= b.y0 && yy < b.y1);
  fonts::setRamp(fonts::TypeRamp::M);
}

// SOUL M's keyboard is untouched: Round QWERTY, 32 keys, the 1.9.0 geometry
static void test_m_keyboard_unchanged() {
  fonts::setRamp(fonts::TypeRamp::M);
  Keyboard kb;
  kb.setGeometry(displays::kLcd28);
  KbConfig c;
  kb.open(c);
  TEST_ASSERT_FALSE(kb.dense());
  TEST_ASSERT_EQUAL_INT(32, kb.keyCount());
  TEST_ASSERT_EQUAL_INT('q', (int)kb.key(0).cp);
  TEST_ASSERT_EQUAL_INT(54, kb.rowH());  // 52 design px at 480
}

// rows of pills on S: never overlapping, inside the circle (inside the ring, when one rings the rim)
static void test_s_rows_of_pills_fit() {
  for (const char* st : {"alarm-ring", "note", "game-over", "msg", "soul", "breathe", "timer-countdown", "claude-ask", "boot-name",
                         "boot-brain", "maps-route", "wifi-hotspot"}) {
    alive_states::Rig s(strncmp(st, "boot", 4) != 0, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE_MESSAGE(alive_states::setup(s, st), st);
    std::vector<Os::Control> cs;
    s.os.controls(cs);
    const bool ring = !strcmp(st, "alarm-ring") || !strcmp(st, "timer-countdown") || !strcmp(st, "claude-ask");
    int pills = 0;
    for (size_t i = 0; i < cs.size(); ++i) {
      const Rect& a = cs[i].r;
      if (a.h() >= 68) ++pills;
      const float k = fminf(cs[i].radius, fminf((float)a.w(), (float)a.h()) * 0.5f) * 0.2929f;
      for (float x : {a.x0 + k, a.x1 - k})
        for (float y : {a.y0 + k, a.y1 - k}) TEST_ASSERT_TRUE_MESSAGE(hypotf(x - 233, y - 233) <= (ring ? 212.5f : 221.35f), st);
      for (size_t j = i + 1; j < cs.size(); ++j) {
        const Rect& b = cs[j].r;
        const bool apart = a.x1 <= b.x0 + 1 || b.x1 <= a.x0 + 1 || a.y1 <= b.y0 + 1 || b.y1 <= a.y0 + 1;
        TEST_ASSERT_TRUE_MESSAGE(apart, st);
      }
    }
    TEST_ASSERT_GREATER_THAN_MESSAGE(0, pills, st);
  }
  fonts::setRamp(fonts::TypeRamp::M);
}

// S's own layouts still work: Look's › previews the next birth, the Control tiles toggle, Convert's swap swaps
static void test_s_screens_still_act() {
  {
    alive_states::Rig s(true, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE(alive_states::setup(s, "look"));
    TEST_ASSERT_TRUE(s.os.lookOpen());
    TEST_ASSERT_TRUE(s.os.previewing());
  }
  {
    alive_states::Rig s(true, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE(alive_states::setup(s, "maps-walking"));
    TEST_ASSERT_TRUE(s.os.apps().navOn);
  }
  {
    alive_states::Rig s(true, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE(alive_states::setup(s, "wifi-hotspot"));
    std::vector<Os::Control> cs;
    s.os.controls(cs);
    TEST_ASSERT_EQUAL_INT(2, (int)cs.size());  // the hotspot page: Type it, From phone
  }
  {
    alive_states::Rig s(true, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE(alive_states::setup(s, "control"));
    const bool was = s.os.apps().dnd;
    s.tapControl(300, 0, 0, 0.6f);  // Quiet
    TEST_ASSERT_TRUE(s.os.apps().dnd != was);
  }
  {
    alive_states::Rig s(true, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE(alive_states::setup(s, "convert"));
    const int from = s.os.apps().from, to = s.os.apps().to;
    s.tapControl(213, 0, 0, 0.6f);  // the swap disc
    TEST_ASSERT_EQUAL_INT(to, s.os.apps().from);
    TEST_ASSERT_EQUAL_INT(from, s.os.apps().to);
  }
  {  // the boot on S: a name from the row of three, No AI from the 2 x 2 grid, Next: "hold the glass"
    alive_states::Rig s(false, -1, displays::kAmoled175);
    TEST_ASSERT_TRUE(alive_states::setup(s, "boot-hold"));
    TEST_ASSERT_EQUAL_INT((int)BootStep::Hold, (int)s.os.bootStep());
    TEST_ASSERT_EQUAL_INT((int)AiMode::None, (int)s.os.aiMode());
  }
  fonts::setRamp(fonts::TypeRamp::M);
}

void runDensityTests() {
  RUN_TEST(test_density_m_is_the_reference_glass);
  RUN_TEST(test_density_s_keeps_the_millimetres);
  RUN_TEST(test_density_s_dial_pebbles_are_fingertips);
  RUN_TEST(test_density_s_wheel_slot_and_ask_fit);
  RUN_TEST(test_density_s_os_on_the_amoled);
  RUN_TEST(test_density_burn_in_care);
  RUN_TEST(test_s_keyboard_has_5mm_keys_and_types);
  RUN_TEST(test_m_keyboard_unchanged);
  RUN_TEST(test_s_rows_of_pills_fit);
  RUN_TEST(test_s_screens_still_act);
}
