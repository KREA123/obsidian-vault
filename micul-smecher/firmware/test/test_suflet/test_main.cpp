// Unit tests for the soul engine. Run on the PC: pio test -e native
#include <unity.h>

#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "Alarms.h"
#include "Brain.h"
#include "ClaudeLink.h"
#include "Face.h"
#include "Font.h"
#include "Gestures.h"
#include "Keyboard.h"
#include "Personality.h"
#include "Predictor.h"
#include "Shell.h"
#include "TextField.h"
#include "TimePicker.h"

using namespace suflet;

void setUp() {}
void tearDown() {}

static constexpr float kDt = 1.0f / 30.0f;

// ------------------------------------------------------------- helpers ---

struct Rig {
  Brain b;
  Inputs in;
  explicit Rig(uint64_t seed = 42) : b(Personality::fromSeed(seed), seed) { in.hour = 14.0f; }
  void run(float s, bool still = false) {
    for (int i = 0; i < (int)(s * 30.0f + 0.5f); ++i) {
      in.stillFor = still ? in.stillFor + kDt : 0.0f;
      b.update(kDt, in);
    }
  }
  bool hasCue(Cue want) {
    Cue c;
    bool found = false;
    while (b.popCue(c))
      if (c == want) found = true;
    return found;
  }
};

static std::vector<Ev> drainMotion(MotionDetector& m) {
  std::vector<Ev> v;
  Ev e;
  while (m.poll(e)) v.push_back(e);
  return v;
}
static bool has(const std::vector<Ev>& v, Ev e) {
  for (Ev x : v)
    if (x == e) return true;
  return false;
}

// --------------------------------------------------------- personality ---

void test_personality_is_deterministic() {
  const Personality a = Personality::fromSeed(123), b = Personality::fromSeed(123);
  TEST_ASSERT_EQUAL_FLOAT(a.shyness, b.shyness);
  TEST_ASSERT_EQUAL(a.tint, b.tint);
  const Personality c = Personality::fromSeed(124);
  TEST_ASSERT_TRUE(a.shyness != c.shyness || a.curiosity != c.curiosity);
}

void test_rarity_distribution() {
  int gold = 0, common = 0;
  const int n = 100000;
  for (int i = 0; i < n; ++i) {
    const Personality p = Personality::fromSeed((uint64_t)i * 2654435761ull + 17);
    if (p.rarity == Rarity::Legendary) ++gold;
    if (p.rarity == Rarity::Common) ++common;
  }
  // 1 % legendary gold, 74 % common (58 cream + 16 ice)
  TEST_ASSERT_INT_WITHIN(250, 1000, gold);
  TEST_ASSERT_INT_WITHIN(1500, 74000, common);
}

// ---------------------------------------------------------------- touch ---

void test_touch_tap_and_double_tap() {
  TouchGestures t;
  Ev e;
  t.update(true, 200, 200, kDt);
  for (int i = 0; i < 3; ++i) t.update(true, 201, 200, kDt);
  t.update(false, 0, 0, kDt);
  TEST_ASSERT_TRUE(t.poll(e));
  TEST_ASSERT_EQUAL(Ev::Tap, e);
  for (int i = 0; i < 4; ++i) t.update(false, 0, 0, kDt);
  t.update(true, 200, 200, kDt);
  t.update(true, 200, 200, kDt);
  t.update(false, 0, 0, kDt);
  TEST_ASSERT_TRUE(t.poll(e));
  TEST_ASSERT_EQUAL(Ev::DoubleTap, e);
}

void test_touch_hold_and_stroke() {
  TouchGestures t;
  Ev e;
  for (int i = 0; i < 30; ++i) t.update(true, 233, 233, kDt);  // 1 s resting finger
  TEST_ASSERT_TRUE(t.poll(e));
  TEST_ASSERT_EQUAL(Ev::HoldStart, e);
  t.update(false, 0, 0, kDt);
  TEST_ASSERT_TRUE(t.poll(e));
  TEST_ASSERT_EQUAL(Ev::HoldEnd, e);

  for (int i = 0; i < 12; ++i) t.update(true, 150.0f + i * 8.0f, 233, kDt);  // rubbing
  TEST_ASSERT_TRUE(t.poll(e));
  TEST_ASSERT_EQUAL(Ev::StrokeStart, e);
  t.update(false, 0, 0, kDt);
  TEST_ASSERT_TRUE(t.poll(e));
  TEST_ASSERT_EQUAL(Ev::StrokeEnd, e);
}

// --------------------------------------------------------------- motion ---

static void feedRest(MotionDetector& m, float s, float ax = 0, float ay = 0, float az = 1) {
  for (int i = 0; i < (int)(s * 100); ++i) m.update(ax, ay, az, 0.01f);
}

void test_motion_pickup_after_rest() {
  MotionDetector m;
  feedRest(m, 3.0f);
  TEST_ASSERT_TRUE(m.stillFor() > 2.5f);
  for (int i = 0; i < 60; ++i) {  // 0.6 s of handling
    const float t = i * 0.01f;
    m.update(0.25f * std::sin(t * 20), 0.2f * std::cos(t * 15), 1.0f + 0.2f * std::sin(t * 9), 0.01f);
  }
  const auto ev = drainMotion(m);
  TEST_ASSERT_TRUE(has(ev, Ev::PickUp));
  TEST_ASSERT_FALSE(has(ev, Ev::Knock));
}

void test_motion_knock_keeps_rest() {
  MotionDetector m;
  feedRest(m, 3.0f);
  m.update(0.5f, 0.0f, 1.3f, 0.01f);  // one sharp bump
  m.update(0.2f, 0.0f, 1.1f, 0.01f);
  feedRest(m, 0.4f);
  const auto ev = drainMotion(m);
  TEST_ASSERT_TRUE(has(ev, Ev::Knock));
  TEST_ASSERT_FALSE(has(ev, Ev::PickUp));
  TEST_ASSERT_TRUE(m.stillFor() > 2.5f);
  TEST_ASSERT_TRUE(m.knockX() > 0.5f);
}

void test_motion_shake() {
  MotionDetector m;
  feedRest(m, 1.0f);
  for (int i = 0; i < 100; ++i) {  // 1 s, ~6 Hz, +-2 g
    m.update(2.0f * std::sin(i * 0.01f * 2 * 3.14159f * 6), 0, 1, 0.01f);
  }
  TEST_ASSERT_TRUE(has(drainMotion(m), Ev::Shake));
}

void test_motion_free_fall_and_orientation() {
  MotionDetector m;
  feedRest(m, 1.0f);
  for (int i = 0; i < 15; ++i) m.update(0, 0, 0.05f, 0.01f);
  TEST_ASSERT_TRUE(has(drainMotion(m), Ev::FreeFall));
  feedRest(m, 2.0f, 0, 0, -1);  // face down
  auto ev = drainMotion(m);
  TEST_ASSERT_TRUE(has(ev, Ev::FaceDown));
  TEST_ASSERT_TRUE(m.faceDown());
  feedRest(m, 2.0f, 0, -1, 0);  // standing on its head
  ev = drainMotion(m);
  TEST_ASSERT_TRUE(has(ev, Ev::FaceUp));
  TEST_ASSERT_TRUE(has(ev, Ev::UpsideDown));
}

// ---------------------------------------------------------------- brain ---

void test_brain_boop_and_shy() {
  Rig r;
  r.run(1.0f);
  r.b.event(Ev::Tap);
  TEST_ASSERT_EQUAL(Reaction::Boop, r.b.reaction());
  TEST_ASSERT_TRUE(r.hasCue(Cue::Click));
  r.run(2.0f);
  TEST_ASSERT_EQUAL(Reaction::None, r.b.reaction());
  bool shy = false;
  for (int i = 0; i < 7 && !shy; ++i) {
    r.b.event(Ev::Tap);
    shy = r.b.reaction() == Reaction::Shy;
    r.run(0.3f);
  }
  TEST_ASSERT_TRUE(shy);
}

void test_brain_dizzy_then_sulks() {
  Rig r;
  r.run(0.5f);
  r.b.event(Ev::Shake);
  TEST_ASSERT_EQUAL(Reaction::Dizzy, r.b.reaction());
  r.run(4.0f);
  TEST_ASSERT_TRUE(r.b.mood().grumpyFor > 0);
  r.b.event(Ev::Tap);
  TEST_ASSERT_EQUAL(Reaction::Hmph, r.b.reaction());
}

void test_brain_falls_asleep_and_turns_off_face_down() {
  Rig r;
  r.run(r.b.personality().sleepAfterSeconds() + 1.0f, true);
  TEST_ASSERT_EQUAL(Mode::Drowsy, r.b.mode());
  r.run(7.0f, true);
  TEST_ASSERT_EQUAL(Mode::Asleep, r.b.mode());
  TEST_ASSERT_EQUAL(EyeStyle::Closed, r.b.face().style);
  r.in.faceDown = true;
  r.run(9.0f, true);
  TEST_ASSERT_EQUAL(Mode::Off, r.b.mode());
  TEST_ASSERT_TRUE(r.b.displayOff());
  r.in.faceDown = false;
  r.b.event(Ev::FaceUp);
  TEST_ASSERT_EQUAL(Mode::Awake, r.b.mode());
  TEST_ASSERT_EQUAL(Reaction::WakeUp, r.b.reaction());
}

void test_brain_missed_you_after_absence() {
  Rig r;
  r.run(80.0f, true);  // asleep
  TEST_ASSERT_EQUAL(Mode::Asleep, r.b.mode());
  r.b.setAbsence(9.0f);
  r.b.event(Ev::PickUp);
  TEST_ASSERT_EQUAL(Reaction::WakeUp, r.b.reaction());
  r.run(2.0f);
  TEST_ASSERT_EQUAL(Reaction::MissedYou, r.b.reaction());
}

void test_brain_hold_purrs_offline_listens_online() {
  Rig r;
  r.run(0.5f);
  r.b.event(Ev::HoldStart);
  TEST_ASSERT_EQUAL(Reaction::Purr, r.b.reaction());
  r.b.event(Ev::HoldEnd);
  r.run(2.0f);
  TEST_ASSERT_EQUAL(Reaction::None, r.b.reaction());

  r.b.setAiLink(true);
  r.b.event(Ev::HoldStart);
  TEST_ASSERT_EQUAL(Reaction::Listen, r.b.reaction());
  TEST_ASSERT_TRUE(r.hasCue(Cue::ListenOn));
  r.b.event(Ev::HoldEnd);
  TEST_ASSERT_EQUAL(Reaction::Think, r.b.reaction());
  TEST_ASSERT_TRUE(r.hasCue(Cue::ListenOff));
  r.b.event(Ev::AiSpeakStart);
  TEST_ASSERT_EQUAL(Reaction::Speak, r.b.reaction());
  r.b.event(Ev::AiSpeakEnd);
  r.run(1.0f);
  TEST_ASSERT_EQUAL(Reaction::None, r.b.reaction());
}

void test_brain_claude_approve_needs_full_hold() {
  Rig r;
  r.run(0.5f);
  r.b.event(Ev::ClaudePrompt);
  TEST_ASSERT_TRUE(r.b.claudePrompt());
  r.hasCue(Cue::None);  // drain
  // let go after 0.6 s: nothing is sent
  r.b.event(Ev::HoldStart);
  r.run(0.6f);
  TEST_ASSERT_TRUE(r.b.approveProgress() > 0.3f);
  r.b.event(Ev::HoldEnd);
  TEST_ASSERT_FALSE(r.hasCue(Cue::ClaudeApprove));
  TEST_ASSERT_TRUE(r.b.claudePrompt());
  // full hold approves
  r.b.event(Ev::HoldStart);
  r.run(1.4f);
  TEST_ASSERT_TRUE(r.hasCue(Cue::ClaudeApprove));
  TEST_ASSERT_FALSE(r.b.claudePrompt());
}

void test_brain_claude_double_tap_denies_and_tap_does_not() {
  Rig r;
  r.run(0.5f);
  r.b.event(Ev::ClaudePrompt);
  r.b.event(Ev::Tap);  // a boop is never a decision
  TEST_ASSERT_TRUE(r.b.claudePrompt());
  TEST_ASSERT_FALSE(r.hasCue(Cue::ClaudeApprove));
  r.run(2.0f);
  r.b.event(Ev::DoubleTap);
  TEST_ASSERT_TRUE(r.hasCue(Cue::ClaudeDeny));
  TEST_ASSERT_EQUAL(Reaction::Nope, r.b.reaction());
}

void test_brain_stays_awake_while_claude_works() {
  Rig r;
  r.b.event(Ev::ClaudeBusyStart);
  r.run(r.b.personality().sleepAfterSeconds() + 10.0f, true);
  TEST_ASSERT_EQUAL(Mode::Awake, r.b.mode());
  r.b.event(Ev::ClaudeBusyEnd);
  r.run(r.b.personality().sleepAfterSeconds() + 8.0f, true);
  TEST_ASSERT_TRUE(r.b.mode() != Mode::Awake);
}

void test_brain_night_colour() {
  Rig r;
  r.in.hour = 23.0f;
  r.run(1.0f);
  TEST_ASSERT_TRUE(r.b.face().color == r.b.personality().eyeNight);
}

// ----------------------------------------------------------- claude link ---

static void feedLine(ClaudeLink& c, const char* s) {
  c.feed((const uint8_t*)s, strlen(s));
  c.feed((const uint8_t*)"\n", 1);
}
static std::vector<Ev> drainLink(ClaudeLink& c) {
  std::vector<Ev> v;
  Ev e;
  while (c.poll(e)) v.push_back(e);
  return v;
}

void test_claude_snapshot_events() {
  ClaudeLink c;
  feedLine(c, "{\"total\":1,\"running\":1,\"waiting\":0,\"msg\":\"working\",\"tokens\":49000}");
  auto ev = drainLink(c);
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeUp));
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeBusyStart));
  TEST_ASSERT_TRUE(c.busy());
  // split across two BLE packets, with a prompt and a level-up
  const char* part1 = "{\"total\":1,\"running\":0,\"waiting\":1,\"msg\":\"approve: Bash\",\"tokens\":51000,";
  const char* part2 = "\"prompt\":{\"id\":\"req_9\",\"tool\":\"Bash\",\"hint\":\"npm test\"}}\n";
  c.feed((const uint8_t*)part1, strlen(part1));
  TEST_ASSERT_EQUAL(0, (int)drainLink(c).size());
  c.feed((const uint8_t*)part2, strlen(part2));
  ev = drainLink(c);
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeBusyEnd));
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudePrompt));
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeLevelUp));
  TEST_ASSERT_EQUAL_STRING("Bash", c.promptTool().c_str());
  TEST_ASSERT_EQUAL_STRING("npm test", c.promptHint().c_str());
}

void test_claude_permission_decision_wire_format() {
  ClaudeLink c;
  feedLine(c, "{\"total\":1,\"running\":0,\"waiting\":1,\"prompt\":{\"id\":\"req_abc123\",\"tool\":\"Bash\",\"hint\":\"ls\"}}");
  drainLink(c);
  TEST_ASSERT_TRUE(c.decide(true));
  std::string line;
  TEST_ASSERT_TRUE(c.popOutgoing(line));
  TEST_ASSERT_EQUAL_STRING("{\"cmd\":\"permission\",\"id\":\"req_abc123\",\"decision\":\"once\"}\n", line.c_str());
  auto ev = drainLink(c);
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeQuickApprove));
  TEST_ASSERT_FALSE(c.hasPrompt());
  TEST_ASSERT_FALSE(c.decide(false));  // nothing pending any more
}

void test_claude_commands_and_acks() {
  ClaudeLink c;
  c.status.batPct = 87;
  c.status.batMv = 4012;
  feedLine(c, "{\"cmd\":\"owner\",\"name\":\"Andu\"}");
  feedLine(c, "{\"cmd\":\"status\"}");
  feedLine(c, "{\"cmd\":\"char_begin\",\"name\":\"bufo\",\"total\":10}");
  feedLine(c, "{\"cmd\":\"teleport\"}");
  feedLine(c, "{\"cmd\":\"unpair\"}");
  std::string a, b, d, e;
  TEST_ASSERT_TRUE(c.popOutgoing(a));
  TEST_ASSERT_EQUAL_STRING("{\"ack\":\"owner\",\"ok\":true,\"n\":0}\n", a.c_str());
  TEST_ASSERT_TRUE(c.popOutgoing(b));
  TEST_ASSERT_TRUE(b.find("\"ack\":\"status\"") != std::string::npos);
  TEST_ASSERT_TRUE(b.find("\"pct\":87") != std::string::npos);
  TEST_ASSERT_TRUE(c.popOutgoing(d));  // char_begin is NOT acked (not supported)
  TEST_ASSERT_TRUE(d.find("teleport") != std::string::npos);
  TEST_ASSERT_TRUE(d.find("\"ok\":false") != std::string::npos);
  TEST_ASSERT_TRUE(c.popOutgoing(e));
  TEST_ASSERT_TRUE(e.find("unpair") != std::string::npos);
  TEST_ASSERT_TRUE(c.unpairRequested());
  TEST_ASSERT_EQUAL_STRING("Andu", c.owner().c_str());
}

void test_claude_time_and_timeout() {
  ClaudeLink c;
  feedLine(c, "{\"time\":[1790246400,10800]}");  // 10:40 UTC, +3 h = 13:40 local
  TEST_ASSERT_TRUE(c.timeValid());
  TEST_ASSERT_FLOAT_WITHIN(0.02f, 13.6667f, c.localHour());
  feedLine(c, "{\"total\":1,\"running\":1}");
  drainLink(c);
  for (int i = 0; i < 31 * 30; ++i) c.tick(kDt);
  auto ev = drainLink(c);
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeDown));
  TEST_ASSERT_TRUE(has(ev, Ev::ClaudeBusyEnd));
  TEST_ASSERT_FALSE(c.alive());
}

void test_claude_ignores_garbage() {
  ClaudeLink c;
  feedLine(c, "not json {");
  feedLine(c, "[1,2,3]");
  feedLine(c, "{\"evt\":\"turn\",\"role\":\"assistant\",\"content\":[]}");
  TEST_ASSERT_EQUAL(0, (int)drainLink(c).size());
  std::string s;
  TEST_ASSERT_FALSE(c.popOutgoing(s));
}

// ---------------------------------------------------------------- render ---

void test_render_draws_eyes_inside_dirty_rect() {
  std::vector<uint16_t> fb(240 * 240, 0);
  Canvas cv(240, 240, fb.data());
  Face f;
  renderFace(cv, f);
  const Rect d = cv.dirty();
  TEST_ASSERT_FALSE(d.empty());
  int lit = 0, outside = 0;
  for (int y = 0; y < 240; ++y)
    for (int x = 0; x < 240; ++x)
      if (fb[y * 240 + x]) {
        ++lit;
        if (x < d.x0 || x >= d.x1 || y < d.y0 || y >= d.y1) ++outside;
      }
  TEST_ASSERT_TRUE(lit > 1500);
  TEST_ASSERT_EQUAL(0, outside);
  // symmetric face: left and right halves light up about the same
  int left = 0, right = 0;
  for (int y = 0; y < 240; ++y)
    for (int x = 0; x < 240; ++x)
      if (fb[y * 240 + x]) (x < 120 ? left : right)++;
  TEST_ASSERT_INT_WITHIN(lit / 5, left, right);
}

void test_render_off_draws_nothing() {
  std::vector<uint16_t> fb(120 * 120, 0);
  Canvas cv(120, 120, fb.data());
  Face f;
  f.bright = 0;
  renderFace(cv, f);
  for (uint16_t p : fb) TEST_ASSERT_EQUAL_UINT16(0, p);
}


// =============================================================== SoulOS ===

static std::vector<TouchEv> drainTouch(TouchGestures& t) {
  std::vector<TouchEv> v;
  TouchEv e;
  while (t.poll(e)) v.push_back(e);
  return v;
}
static int countEv(const std::vector<TouchEv>& v, Ev e) {
  int n = 0;
  for (const TouchEv& x : v)
    if (x.e == e) ++n;
  return n;
}

// ------------------------------------------------------- touch with x/y ---

void test_touch_events_carry_position() {
  TouchGestures t;
  t.update(true, 120, 300, kDt);
  t.update(true, 121, 301, kDt);
  t.update(false, 0, 0, kDt);  // controllers report 0,0 on release: keep the last point
  std::vector<TouchEv> v = drainTouch(t);
  TEST_ASSERT_EQUAL(1, (int)v.size());
  TEST_ASSERT_EQUAL(Ev::Tap, v[0].e);
  TEST_ASSERT_EQUAL(121, v[0].x);
  TEST_ASSERT_EQUAL(301, v[0].y);
}

void test_touch_text_mode_keeps_every_fast_tap() {
  TouchGestures t;
  t.setMode(TouchMode::Text);
  for (int i = 0; i < 6; ++i) {  // 6 taps at 15 taps/s: face mode would merge them
    t.update(true, 40.0f + 44 * i, 210, kDt);
    t.update(false, 0, 0, kDt);
  }
  std::vector<TouchEv> v = drainTouch(t);
  TEST_ASSERT_EQUAL(6, countEv(v, Ev::TouchDown));
  TEST_ASSERT_EQUAL(6, countEv(v, Ev::TouchUp));
  TEST_ASSERT_EQUAL(0, countEv(v, Ev::DoubleTap));
  TEST_ASSERT_EQUAL(260, v.back().x);  // the last key, where it was lifted

  // face mode, same input: the second tap of each pair becomes a DoubleTap
  TouchGestures f;
  for (int i = 0; i < 2; ++i) {
    f.update(true, 100, 100, kDt);
    f.update(false, 0, 0, kDt);
  }
  std::vector<TouchEv> w = drainTouch(f);
  TEST_ASSERT_EQUAL(1, countEv(w, Ev::DoubleTap));
}

void test_touch_text_mode_hold_move_and_long_press_timing() {
  TouchGestures t;
  t.setMode(TouchMode::Text);
  t.update(true, 200, 260, kDt);
  for (int i = 0; i < 10; ++i) t.update(true, 201, 260, kDt);  // 0.37 s: not yet
  std::vector<TouchEv> v = drainTouch(t);
  TEST_ASSERT_EQUAL(0, countEv(v, Ev::HoldStart));
  t.update(true, 201, 261, kDt);
  t.update(true, 201, 261, kDt);
  v = drainTouch(t);
  TEST_ASSERT_EQUAL(1, countEv(v, Ev::HoldStart));  // ~380 ms still = variants
  t.update(true, 240, 262, kDt);  // slide
  v = drainTouch(t);
  TEST_ASSERT_EQUAL(1, countEv(v, Ev::TouchMove));
  TEST_ASSERT_EQUAL(240, v[0].x);
  t.update(false, 0, 0, kDt);
  v = drainTouch(t);
  TEST_ASSERT_EQUAL(Ev::HoldEnd, v[0].e);
  TEST_ASSERT_EQUAL(Ev::TouchUp, v[1].e);
}

void test_touch_mode_switch_swallows_the_opening_touch() {
  TouchGestures t;
  for (int i = 0; i < 20; ++i) t.update(true, 233, 233, kDt);
  std::vector<TouchEv> v = drainTouch(t);
  TEST_ASSERT_EQUAL(Ev::HoldStart, v[0].e);
  t.setMode(TouchMode::Text);  // the long press opened the keyboard
  t.update(true, 233, 233, kDt);
  t.update(false, 0, 0, kDt);
  TEST_ASSERT_EQUAL(0, (int)drainTouch(t).size());  // lifting does not type 'g'
  t.update(true, 35, 210, kDt);
  TEST_ASSERT_EQUAL(Ev::TouchDown, drainTouch(t)[0].e);
}

void test_touch_text_mode_jump_is_a_new_finger() {
  TouchGestures t;
  t.setMode(TouchMode::Text);
  t.update(true, 45, 262, kDt);
  t.update(true, 300, 262, kDt);  // rollover: next key pressed before the release was seen
  t.update(false, 0, 0, kDt);
  std::vector<TouchEv> v = drainTouch(t);
  TEST_ASSERT_EQUAL(2, countEv(v, Ev::TouchDown));
  TEST_ASSERT_EQUAL(2, countEv(v, Ev::TouchUp));
  TEST_ASSERT_EQUAL(45, v[1].x);  // first TouchUp at the first key
}

// ---------------------------------------------------------- font / text ---

void test_utf8_decode_encode_and_invalid_bytes() {
  const char* s = "aș€\xFF" "b";
  const char* p = s;
  TEST_ASSERT_EQUAL_UINT32('a', utf8::next(p));
  TEST_ASSERT_EQUAL_UINT32(0x219, utf8::next(p));
  TEST_ASSERT_EQUAL_UINT32(0x20AC, utf8::next(p));
  TEST_ASSERT_EQUAL_UINT32(0xFFFD, utf8::next(p));  // invalid byte: replaced, loop goes on
  TEST_ASSERT_EQUAL_UINT32('b', utf8::next(p));
  char b[4];
  TEST_ASSERT_EQUAL(2, utf8::encode(0x103, b));  // ă
  TEST_ASSERT_EQUAL_UINT8(0xC4, (uint8_t)b[0]);
  TEST_ASSERT_EQUAL_UINT8(0x83, (uint8_t)b[1]);
  TEST_ASSERT_EQUAL(5, (int)utf8::count("țară", strlen("țară")) + 1);
  TEST_ASSERT_EQUAL_UINT32(0x218, utf8::upper(0x219));
  TEST_ASSERT_EQUAL_UINT32('s', utf8::fold(0x15F));  // ş (cedilla) folds too
  TEST_ASSERT_EQUAL_UINT32('a', utf8::fold(0xC2));   // Â
}

void test_font_has_romanian_glyphs_and_fallbacks() {
  const Font* all[] = {&fonts::small(), &fonts::text(), &fonts::large()};
  for (const Font* f : all) {
    for (uint32_t cp : {0x103u, 0xE2u, 0xEEu, 0x219u, 0x21Bu, 0x102u, 0xC2u, 0xCEu, 0x218u, 0x21Au}) {
      const Glyph* g = f->find(cp);
      TEST_ASSERT_NOT_NULL(g);
      TEST_ASSERT_EQUAL_UINT32(cp, g->cp);
      TEST_ASSERT_TRUE(g->w > 0 && g->h > 0);
    }
    TEST_ASSERT_EQUAL_PTR(f->find(0x219), f->find(0x15F));  // ş -> ș
    TEST_ASSERT_EQUAL_UINT32('?', f->find(0x4E2D)->cp);      // missing -> '?'
  }
  TEST_ASSERT_EQUAL_UINT32('7', fonts::digits().find('7')->cp);
  // ș has its comma below the baseline
  const Glyph* s = fonts::text().find(0x219);
  TEST_ASSERT_TRUE(s->y + s->h > 3);
}

void test_draw_text_antialiased_inside_dirty_and_clipped() {
  std::vector<uint16_t> fb(200 * 80, 0);
  Canvas cv(200, 80, fb.data());
  const int w = cv.drawText(fonts::text(), 100, 50, "Șapte ață", pal::kWhite, 1, Align::Center);
  TEST_ASSERT_EQUAL(Canvas::measureText(fonts::text(), "Șapte ață"), w);
  const Rect d = cv.dirty();
  int lit = 0, outside = 0, partial = 0;
  for (int y = 0; y < 80; ++y)
    for (int x = 0; x < 200; ++x) {
      const uint16_t p = fb[y * 200 + x];
      if (!p) continue;
      ++lit;
      if (p != 0xFFFF) ++partial;  // anti-aliased edge pixels
      if (x < d.x0 || x >= d.x1 || y < d.y0 || y >= d.y1) ++outside;
    }
  TEST_ASSERT_TRUE(lit > 300);
  TEST_ASSERT_TRUE(partial > 50);
  TEST_ASSERT_EQUAL(0, outside);
  TEST_ASSERT_INT_WITHIN(3, 100 - w / 2, d.x0);  // centred
  TEST_ASSERT_TRUE(d.y1 > 50);                    // the ș / ț commas go below the baseline
  // off the canvas: clipped, no crash, nothing drawn
  Canvas c2(200, 80, fb.data());
  c2.drawText(fonts::large(), -500, -100, "Hello", pal::kWhite);
  c2.drawText(fonts::large(), 190, 90, "Hello", pal::kWhite);
  TEST_ASSERT_TRUE(c2.dirty().empty() || c2.dirty().y1 <= 80);
}

void test_text_alignment_and_measure() {
  const Font& f = fonts::small();
  const int a = Canvas::measureText(f, "ab"), b = Canvas::measureText(f, "abab");
  TEST_ASSERT_INT_WITHIN(1, 2 * a, b);  // sub-pixel advances don't drift
  TEST_ASSERT_EQUAL(Canvas::measureText(f, "ab"), Canvas::measureText(f, "abcd", 2));
  std::vector<uint16_t> fb(300 * 60, 0);
  Canvas cv(300, 60, fb.data());
  cv.drawText(f, 280, 40, "right", pal::kWhite, 1, Align::Right);
  TEST_ASSERT_INT_WITHIN(3, 280, cv.dirty().x1);
}

// ------------------------------------------------------------- TextField ---

void test_textfield_deletes_code_points_and_undoes() {
  TextField t(100);
  t.insert("mâine ș");
  TEST_ASSERT_EQUAL(7, (int)t.length());
  TEST_ASSERT_TRUE(t.backspace());  // ș is 2 bytes, one press
  TEST_ASSERT_EQUAL_STRING("mâine ", t.text().c_str());
  t.backspace();
  t.backspace();
  TEST_ASSERT_EQUAL_STRING("mâin", t.text().c_str());
  TEST_ASSERT_TRUE(t.undo());
  TEST_ASSERT_EQUAL_STRING("mâine", t.text().c_str());
  t.insert(0x15F);  // cedilla ş arrives -> stored as comma ș
  TEST_ASSERT_EQUAL_STRING("mâineș", t.text().c_str());
  t.clear();
  TEST_ASSERT_TRUE(t.empty());
  t.undo();
  TEST_ASSERT_EQUAL_STRING("mâineș", t.text().c_str());
  TEST_ASSERT_EQUAL(t.text().size(), t.caret());  // caret at the end
}

void test_textfield_limit_words_and_undo_depth() {
  TextField t(5);
  TEST_ASSERT_TRUE(t.insert("ăăăăăăă"));
  TEST_ASSERT_EQUAL(5, (int)t.length());  // stops at 5 code points, not bytes
  TEST_ASSERT_FALSE(t.insert('x'));
  TextField w(200);
  w.insert("Ce faci, ana? bine");
  TEST_ASSERT_EQUAL_STRING("bine", w.currentWord().c_str());
  std::vector<std::string> p = w.previousWords();
  TEST_ASSERT_EQUAL(3, (int)p.size());
  TEST_ASSERT_EQUAL_STRING("ana", p[2].c_str());
  w.deleteWord();
  TEST_ASSERT_EQUAL_STRING("Ce faci, ana? ", w.text().c_str());
  TextField u(500);
  for (int i = 0; i < 40; ++i) u.insert('a');
  int undos = 0;
  while (u.undo()) ++undos;
  TEST_ASSERT_EQUAL((int)TextField::kUndo, undos);
}

// ------------------------------------------------------------- Predictor ---

void test_predictor_ro_diacritics_only_in_romanian_sentences() {
  Predictor p;
  p.uiLang = Lang::Ro;
  TEST_ASSERT_EQUAL_STRING("să", p.autoForm("sa", {"vreau"}).c_str());
  TEST_ASSERT_EQUAL_STRING("Mâine", p.autoForm("Maine", {}).c_str());  // keeps the capital
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("sa", {"i", "want", "the"}).c_str());  // English sentence
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("in", {}).c_str());  // "in" is English too: no evidence
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("vreau", {}).c_str());  // nothing to restore
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("să", {}).c_str());     // already has diacritics
  p.lock("sa");
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("sa", {"vreau"}).c_str());  // reverted once: left alone
}

void test_predictor_english_ui_needs_romanian_evidence() {
  Predictor p;  // EN is the default UI language
  TEST_ASSERT_EQUAL(Lang::En, p.uiLang);
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("sa", {}).c_str());
  TEST_ASSERT_EQUAL_STRING("", p.autoForm("sa", {"the"}).c_str());  // English evidence
  TEST_ASSERT_EQUAL_STRING("să", p.autoForm("sa", {"mâine"}).c_str());  // exact RO word: evidence
  TEST_ASSERT_EQUAL_STRING("don't", p.autoForm("dont", {"i"}).c_str());  // EN contraction
  TEST_ASSERT_EQUAL_STRING("I'm", p.autoForm("im", {}).c_str());
  const LangScore s = p.score({"remind", "me", "la", "mâine"});
  TEST_ASSERT_EQUAL(2, s.ro);
  TEST_ASSERT_EQUAL(2, s.en);
}

void test_predictor_suggestions_and_next_words() {
  Predictor p;
  Suggestion s[3];
  p.suggest("Hel", {}, s);
  TEST_ASSERT_EQUAL_STRING("Hello", s[1].value.c_str());  // completes, keeps the capital
  TEST_ASSERT_TRUE(s[1].bold);
  TEST_ASSERT_EQUAL_STRING("\xE2\x80\x9CHel\xE2\x80\x9D", s[0].label.c_str());  // “Hel” literal
  p.suggest("", {"Hello"}, s);
  TEST_ASSERT_EQUAL_STRING("there", s[1].value.c_str());
  p.uiLang = Lang::Ro;
  p.suggest("", {"vreau", "să"}, s);
  TEST_ASSERT_EQUAL_STRING("sun", s[1].value.c_str());
  std::vector<std::string> c = p.candidates("intr", {});
  bool found = false;
  for (const std::string& w : c) found |= w == "într-o";
  TEST_ASSERT_TRUE(found);  // folded: "intr" finds "într-o"
}

// -------------------------------------------------------------- Keyboard ---

static Keyboard openKb(Lang l = Lang::En) {
  Keyboard kb;
  KbConfig c;
  c.uiLang = l;
  c.placeholder = "New note…";
  kb.open(c);
  return kb;
}
static void tapAt(Keyboard& kb, float x, float y) {
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)x, (int16_t)y, 0});
}
static void tapKey(Keyboard& kb, uint32_t cp) {
  float x, y;
  TEST_ASSERT_TRUE(kb.keyCenter(cp, x, y));
  tapAt(kb, x, y);
  kb.update(0.1f);
}
static void tapKey(Keyboard& kb, KeyId id) {
  float x, y;
  TEST_ASSERT_TRUE(kb.keyCenter(id, x, y));
  tapAt(kb, x, y);
  kb.update(0.1f);
}
static uint32_t keyAt(const Keyboard& kb, float x, float y) {
  const int i = kb.hitKey(x, y);
  return i < 0 ? 0 : (kb.key(i).id == KeyId::Char ? kb.key(i).cp : 0x100 + (uint32_t)kb.key(i).id);
}

void test_keyboard_hit_test_matches_the_spec_geometry() {
  Keyboard kb = openKb();
  const int row1[] = {35, 79, 123, 167, 211, 255, 299, 343, 387, 431};
  const char* r1 = "qwertyuiop";
  for (int i = 0; i < 10; ++i) TEST_ASSERT_EQUAL_UINT32((uint32_t)r1[i], keyAt(kb, row1[i], 210));
  const char* r2 = "asdfghjkl";
  for (int i = 0; i < 9; ++i) TEST_ASSERT_EQUAL_UINT32((uint32_t)r2[i], keyAt(kb, 45 + 47 * i, 262));
  TEST_ASSERT_EQUAL_UINT32(0x100 + (uint32_t)KeyId::Shift, keyAt(kb, 56, 314));
  TEST_ASSERT_EQUAL_UINT32('z', keyAt(kb, 101, 314));
  TEST_ASSERT_EQUAL_UINT32('m', keyAt(kb, 365, 314));
  TEST_ASSERT_EQUAL_UINT32(0x100 + (uint32_t)KeyId::Bksp, keyAt(kb, 410, 314));
  TEST_ASSERT_EQUAL_UINT32(0x100 + (uint32_t)KeyId::Layer, keyAt(kb, 108, 372));
  TEST_ASSERT_EQUAL_UINT32(0x100 + (uint32_t)KeyId::Space, keyAt(kb, 257, 372));
  TEST_ASSERT_EQUAL_UINT32(0x100 + (uint32_t)KeyId::Done, keyAt(kb, 355, 372));
  // edge taps outside a cap but inside the rim belong to the end keys
  TEST_ASSERT_EQUAL_UINT32('q', keyAt(kb, 4, 200));
  TEST_ASSERT_EQUAL_UINT32('l', keyAt(kb, 462, 250));
  TEST_ASSERT_EQUAL_UINT32(0x100 + (uint32_t)KeyId::Done, keyAt(kb, 440, 440));  // below the action row
  // row borders, suggestion bar and text field
  TEST_ASSERT_EQUAL_UINT32('a', keyAt(kb, 45, 236));
  TEST_ASSERT_EQUAL_UINT32('q', keyAt(kb, 35, 235));
  TEST_ASSERT_EQUAL(-1, kb.hitKey(200, 150));
  TEST_ASSERT_EQUAL(0, kb.hitSuggestion(60, 150));
  TEST_ASSERT_EQUAL(1, kb.hitSuggestion(233, 170));
  TEST_ASSERT_EQUAL(2, kb.hitSuggestion(400, 140));
  TEST_ASSERT_EQUAL(-1, kb.hitSuggestion(233, 100));
}

void test_keyboard_types_hello_with_auto_capital() {
  Keyboard kb = openKb();
  TEST_ASSERT_EQUAL(KbShift::Once, kb.shift());  // empty field: capital first
  for (const char* p = "hello"; *p; ++p) tapKey(kb, (uint32_t)*p);
  TEST_ASSERT_EQUAL_STRING("Hello", kb.text().c_str());
  TEST_ASSERT_EQUAL(KbShift::Off, kb.shift());
  // slide to fix: press on 'q', slide to 'w', lift -> 'w'
  kb.touch(TouchEv{Ev::TouchDown, 35, 210, 0});
  kb.touch(TouchEv{Ev::TouchMove, 79, 212, 0});
  kb.touch(TouchEv{Ev::TouchUp, 79, 212, 0});
  TEST_ASSERT_EQUAL_STRING("Hellow", kb.text().c_str());
  tapKey(kb, KeyId::Bksp);
  tapKey(kb, (uint32_t)' ');
  TEST_ASSERT_EQUAL_STRING("there", kb.suggestion(1).value.c_str());  // next-word hint
  kb.pickSuggestion(1);
  TEST_ASSERT_EQUAL_STRING("Hello there ", kb.text().c_str());
}

void test_keyboard_shift_caps_lock_and_number_layers() {
  Keyboard kb = openKb();
  tapKey(kb, KeyId::Shift);  // auto Once -> Off
  TEST_ASSERT_EQUAL(KbShift::Off, kb.shift());
  tapKey(kb, 'a');
  TEST_ASSERT_EQUAL_STRING("a", kb.text().c_str());
  float x, y;
  kb.keyCenter(KeyId::Shift, x, y);
  tapAt(kb, x, y);
  kb.update(0.1f);  // second tap within 300 ms = caps lock
  tapAt(kb, x, y);
  TEST_ASSERT_EQUAL(KbShift::Lock, kb.shift());
  tapKey(kb, 'b');
  tapKey(kb, 'c');
  TEST_ASSERT_EQUAL_STRING("aBC", kb.text().c_str());
  tapKey(kb, KeyId::Layer);  // ?123
  TEST_ASSERT_EQUAL(KbLayer::Num, kb.layer());
  TEST_ASSERT_EQUAL_UINT32('1', keyAt(kb, 35, 210));
  TEST_ASSERT_EQUAL_UINT32(0x20AC, keyAt(kb, 299, 262));  // €
  tapKey(kb, '7');
  tapKey(kb, KeyId::SymLayer);  // #+=
  TEST_ASSERT_EQUAL(KbLayer::Sym, kb.layer());
  tapKey(kb, 0x201E);  // „
  tapKey(kb, KeyId::Layer);  // ABC
  TEST_ASSERT_EQUAL(KbLayer::Abc, kb.layer());
  TEST_ASSERT_EQUAL_STRING("aBC7„", kb.text().c_str());
}

void test_keyboard_long_press_tray_gives_the_romanian_letter() {
  Keyboard kb = openKb(Lang::Ro);
  tapKey(kb, KeyId::Shift);  // lower case
  float x, y;
  kb.keyCenter('a', x, y);
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::HoldStart, (int16_t)x, (int16_t)y, 0});
  TEST_ASSERT_TRUE(kb.trayOpen());
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)x, (int16_t)y, 0});  // press-hold-lift
  TEST_ASSERT_EQUAL_STRING("ă", kb.text().c_str());
  // the t key is on the right half: the tray grows left, ț still under the finger
  kb.keyCenter('t', x, y);
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::HoldStart, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::TouchMove, (int16_t)(x + 44), (int16_t)y, 0});  // slide to the next one
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)(x + 44), (int16_t)y, 0});
  TEST_ASSERT_EQUAL_STRING("ă5", kb.text().c_str());
  // lifting far away cancels
  kb.keyCenter('s', x, y);
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::HoldStart, (int16_t)x, (int16_t)y, 0});
  kb.touch(TouchEv{Ev::TouchMove, (int16_t)x, 420, 0});
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)x, 420, 0});
  TEST_ASSERT_EQUAL_STRING("ă5", kb.text().c_str());
}

void test_keyboard_auto_diacritics_and_backspace_revert() {
  Keyboard kb = openKb(Lang::Ro);
  kb.typeText("vreau sa ");  // typeText types exactly (no shift), like a script
  TEST_ASSERT_EQUAL_STRING("vreau să ", kb.text().c_str());
  kb.backspace();  // right after the automatic change: restore what was typed
  TEST_ASSERT_EQUAL_STRING("vreau sa ", kb.text().c_str());
  kb.typeText("sa ");  // locked for the session: not changed again
  TEST_ASSERT_EQUAL_STRING("vreau sa sa ", kb.text().c_str());
  kb.backspace();  // a normal delete now
  TEST_ASSERT_EQUAL_STRING("vreau sa sa", kb.text().c_str());
  kb.typeText(" maine,");  // punctuation finishes a word too
  TEST_ASSERT_EQUAL_STRING("vreau sa sa mâine,", kb.text().c_str());
  // English UI, English sentence: never
  Keyboard en = openKb(Lang::En);
  en.typeText("i want sa ");
  TEST_ASSERT_EQUAL_STRING("i want sa ", en.text().c_str());
  en.undo();
  TEST_ASSERT_EQUAL_STRING("i want sa", en.text().c_str());
}

void test_keyboard_double_space_done_and_hold_delete() {
  Keyboard kb = openKb();
  kb.typeText("hi");
  kb.typeChar(' ');
  kb.update(0.2f);
  kb.typeChar(' ');  // two spaces within 450 ms
  TEST_ASSERT_EQUAL_STRING("hi. ", kb.text().c_str());
  TEST_ASSERT_EQUAL(KbShift::Once, kb.shift());  // new sentence
  kb.typeText("ok this is a longer note here");
  // hold ⌫ for 1.5 s: 12 characters/s after 450 ms, whole words after 1.2 s
  float x, y;
  kb.keyCenter(KeyId::Bksp, x, y);
  kb.touch(TouchEv{Ev::TouchDown, (int16_t)x, (int16_t)y, 0});
  for (int i = 0; i < 10; ++i) kb.update(kDt);
  TEST_ASSERT_EQUAL(33, (int)kb.text().size());  // nothing before 450 ms
  for (int i = 0; i < 35; ++i) kb.update(kDt);
  kb.touch(TouchEv{Ev::TouchUp, (int16_t)x, (int16_t)y, 0});
  const size_t left = kb.text().size();
  TEST_ASSERT_TRUE(left < 33 - 10);
  TEST_ASSERT_EQUAL(0, (int)kb.text().rfind("hi. ok this", 0));
  TEST_ASSERT_TRUE(kb.suggestion(1).undo);  // "↶ Undo" chip after deleting words
  kb.pickSuggestion(1);
  TEST_ASSERT_TRUE(kb.text().size() > left);
  // done: disabled while empty, commits trimmed text otherwise
  Keyboard k2 = openKb();
  k2.done();
  KbResult r;
  TEST_ASSERT_FALSE(k2.poll(r));
  k2.typeText("  buy milk ");
  k2.update(1.0f);
  k2.typeChar(' ');  // a slow second space stays a space
  tapKey(k2, KeyId::Done);
  TEST_ASSERT_TRUE(k2.poll(r));
  TEST_ASSERT_EQUAL(KbResult::Commit, r);
  TEST_ASSERT_EQUAL_STRING("buy milk", k2.committed().c_str());
  TEST_ASSERT_FALSE(k2.isOpen());
}

void test_keyboard_renders_inside_its_bounds() {
  std::vector<uint16_t> fb(466 * 466, 0);
  Canvas cv(466, 466, fb.data());
  Keyboard kb = openKb();
  kb.typeText("Salut ășțâî");
  TEST_ASSERT_TRUE(kb.changed());
  kb.render(cv);
  TEST_ASSERT_FALSE(kb.changed());
  const Rect b = Keyboard::bounds();
  int lit = 0, outside = 0;
  for (int y = 0; y < 466; ++y)
    for (int x = 0; x < 466; ++x)
      if (fb[y * 466 + x]) {
        ++lit;
        if (x < b.x0 || x >= b.x1 || y < b.y0 || y >= b.y1) ++outside;
      }
  TEST_ASSERT_TRUE(lit > 20000);
  TEST_ASSERT_EQUAL(0, outside);
  // the q cap is drawn where the spec puts it, in the letter-cap colour
  TEST_ASSERT_EQUAL_UINT16(Rgb::hex(0x1A1813).to565(), fb[190 * 466 + 18]);
}

// ------------------------------------------------------------ TimePicker ---

void test_timepicker_sundial_and_clock_angles() {
  TEST_ASSERT_EQUAL(0, TimePicker::hourAt(90));    // bottom
  TEST_ASSERT_EQUAL(6, TimePicker::hourAt(180));   // left
  TEST_ASSERT_EQUAL(12, TimePicker::hourAt(-90));  // top
  TEST_ASSERT_EQUAL(18, TimePicker::hourAt(0));    // right
  TEST_ASSERT_EQUAL(23, TimePicker::hourAt(80));   // just before the bottom
  TEST_ASSERT_EQUAL(0, TimePicker::hourAt(97));    // 0/24 wrap
  for (int h = 0; h < 24; ++h) TEST_ASSERT_EQUAL(h, TimePicker::hourAt(TimePicker::hourAngle(h)));
  TEST_ASSERT_EQUAL(0, TimePicker::minuteAt(-90, false));  // 00 at the top
  TEST_ASSERT_EQUAL(15, TimePicker::minuteAt(0, false));
  TEST_ASSERT_EQUAL(59, TimePicker::minuteAt(-96, false));
  TEST_ASSERT_EQUAL(0, TimePicker::minuteAt(-93, false));  // 59/0 wrap rounds up to 00
  TEST_ASSERT_EQUAL(23, TimePicker::minuteAt(TimePicker::minuteAngle(23), false));
  TEST_ASSERT_EQUAL(25, TimePicker::minuteAt(TimePicker::minuteAngle(23), true));  // fast: 5-min snap
  TEST_ASSERT_EQUAL(0, TimePicker::minuteAt(TimePicker::minuteAngle(58), true));
}

static void rimTouch(TimePicker& tp, Ev e, float deg, float t, float r = 205) {
  const float a = deg * 3.14159265f / 180.0f;
  tp.touch(TouchEv{e, (int16_t)lroundf(233 + r * cosf(a)), (int16_t)lroundf(233 + r * sinf(a)), t});
}

void test_timepicker_drag_advances_to_minutes_and_confirms() {
  TimePicker tp;
  tp.open(8, 0);
  tp.setNow(1790374680u);  // 22:18
  rimTouch(tp, Ev::TouchDown, TimePicker::hourAngle(7), 0);
  rimTouch(tp, Ev::TouchMove, TimePicker::hourAngle(7) + 2, 0.1f, 150);  // drifting inward still works
  TEST_ASSERT_EQUAL(7, tp.hour());
  rimTouch(tp, Ev::TouchUp, TimePicker::hourAngle(7), 0.2f);
  TEST_ASSERT_EQUAL(DialMode::Hours, tp.mode());
  tp.update(0.3f);
  TEST_ASSERT_EQUAL(DialMode::Hours, tp.mode());
  tp.update(0.2f);  // 400 ms after lifting: minutes
  TEST_ASSERT_EQUAL(DialMode::Minutes, tp.mode());
  float t = 1;
  for (int m = 0; m <= 30; ++m, t += 0.1f) rimTouch(tp, m ? Ev::TouchMove : Ev::TouchDown, TimePicker::minuteAngle(m), t);
  rimTouch(tp, Ev::TouchUp, TimePicker::minuteAngle(30), t);
  TEST_ASSERT_EQUAL(30, tp.minute());
  TEST_ASSERT_EQUAL((uint32_t)(9 * 60 + 12), tp.minutesUntil());  // "rings in 9 h 12 min"
  tp.touch(TouchEv{Ev::TouchDown, 233, 190, t});  // tap the hour digits
  tp.touch(TouchEv{Ev::TouchUp, 233 - 60, 190, t});
  TEST_ASSERT_EQUAL(DialMode::Minutes, tp.mode());  // x 233 is the minutes half
  tp.touch(TouchEv{Ev::TouchDown, 150, 200, t});
  TEST_ASSERT_EQUAL(DialMode::Hours, tp.mode());
  tp.touch(TouchEv{Ev::TouchDown, 233, 350, t});  // ✓
  tp.touch(TouchEv{Ev::TouchUp, 233, 350, t});
  KbResult r;
  TEST_ASSERT_TRUE(tp.poll(r));
  TEST_ASSERT_EQUAL(KbResult::Commit, r);
  TEST_ASSERT_EQUAL(7, tp.hour());
  TEST_ASSERT_EQUAL(30, tp.minute());
}

// ---------------------------------------------------------------- Alarms ---

static uint32_t at(int dayOffset, int h, int m, int s = 0) {
  // 2026-09-21 is a Monday
  return 1789948800u + (uint32_t)dayOffset * 86400u + h * 3600u + m * 60u + s;
}

void test_alarm_next_fire_across_midnight_and_week() {
  TEST_ASSERT_EQUAL(0, localclock::weekday(at(0, 12, 0)));  // Monday
  TEST_ASSERT_EQUAL(6, localclock::weekday(at(6, 12, 0)));  // Sunday
  Alarm a;
  a.hour = 7;
  a.minute = 30;
  TEST_ASSERT_EQUAL_UINT32(at(1, 7, 30), Alarms::nextFire(a, at(0, 22, 18)));  // over midnight
  TEST_ASSERT_EQUAL_UINT32(at(0, 7, 30), Alarms::nextFire(a, at(0, 6, 0)));    // later today
  TEST_ASSERT_EQUAL_UINT32(at(1, 7, 30), Alarms::nextFire(a, at(0, 7, 30)));   // exactly now: next one
  a.days = days::Weekdays;
  TEST_ASSERT_EQUAL_UINT32(at(7, 7, 30), Alarms::nextFire(a, at(4, 8, 0)));  // Fri after -> Mon
  a.days = days::Mon;
  TEST_ASSERT_EQUAL_UINT32(at(7, 7, 30), Alarms::nextFire(a, at(0, 7, 31)));  // a full week
  a.days = days::Sun;
  TEST_ASSERT_EQUAL_UINT32(at(6, 7, 30), Alarms::nextFire(a, at(5, 23, 59)));
  a.enabled = false;
  TEST_ASSERT_EQUAL_UINT32(0, Alarms::nextFire(a, at(0, 0, 0)));
  Alarms list;
  Alarm b;
  b.hour = 6;
  list.add(a, at(0, 0, 0));
  list.add(b, at(0, 0, 0));
  uint32_t when = 0;
  TEST_ASSERT_EQUAL(1, list.next(at(0, 22, 0), when));
  TEST_ASSERT_EQUAL_UINT32(at(1, 6, 0), when);
}

void test_alarm_rings_once_and_one_shot_switches_off() {
  Alarms list;
  Alarm a;
  a.hour = 7;
  a.minute = 0;
  list.add(a, at(0, 7, 0, 20));  // set at 07:00:20 for 07:00: must not ring now
  TEST_ASSERT_EQUAL(-1, list.poll(at(0, 7, 0, 30)));
  TEST_ASSERT_EQUAL(-1, list.poll(at(1, 6, 59, 59)));
  TEST_ASSERT_EQUAL(0, list.poll(at(1, 7, 0, 1)));  // next morning
  TEST_ASSERT_EQUAL(-1, list.poll(at(1, 7, 0, 30)));  // only once
  TEST_ASSERT_FALSE(list.at(0).enabled);               // one-shot: done
  TEST_ASSERT_EQUAL(-1, list.poll(at(2, 7, 0, 1)));
  // a repeating alarm, and a late loop still within the grace window
  Alarm d;
  d.hour = 23;
  d.minute = 59;
  d.days = days::Every;
  list.add(d, at(0, 0, 0));
  TEST_ASSERT_EQUAL(1, list.poll(at(2, 23, 59, 50)));
  TEST_ASSERT_EQUAL(-1, list.poll(at(3, 0, 0, 40)));  // already rung
  TEST_ASSERT_EQUAL(1, list.poll(at(4, 0, 0, 20)));   // loop 80 s late, past midnight: still rings
  TEST_ASSERT_EQUAL(-1, list.poll(at(5, 0, 5, 0)));   // 6 min late: missed, not rung late
}

void test_alarm_snooze_and_dismiss() {
  Alarms list;
  Alarm a;
  a.hour = 7;
  a.minute = 0;
  a.days = days::Weekdays;
  list.add(a, at(0, 0, 0));
  TEST_ASSERT_EQUAL(0, list.poll(at(0, 7, 0, 2)));
  list.snooze(0, at(0, 7, 0, 30));
  uint32_t when;
  list.next(at(0, 7, 1), when);
  TEST_ASSERT_EQUAL_UINT32(at(0, 7, 5, 30), when);  // snooze 5 min
  TEST_ASSERT_EQUAL(-1, list.poll(at(0, 7, 5, 0)));
  TEST_ASSERT_EQUAL(0, list.poll(at(0, 7, 5, 31)));
  list.snooze(0, at(0, 7, 6));
  list.dismiss(0);
  TEST_ASSERT_EQUAL(-1, list.poll(at(0, 7, 12)));
  TEST_ASSERT_TRUE(list.at(0).enabled);  // repeating alarms stay on
  list.next(at(0, 8, 0), when);
  TEST_ASSERT_EQUAL_UINT32(at(1, 7, 0), when);
}

void test_alarm_binary_roundtrip_and_rejects_corrupt_data() {
  Alarms list;
  Alarm a;
  a.hour = 6;
  a.minute = 45;
  a.days = days::Weekend;
  a.setLabel("Trezirea ăîșț");
  a.snoozeMin = 9;
  list.add(a, at(0, 1, 2));
  Alarm b;
  b.hour = 23;
  b.minute = 5;
  b.enabled = false;
  list.add(b, at(0, 1, 2));
  list.snooze(1, at(0, 3, 0));
  uint8_t buf[Alarms::kMaxBlob];
  const size_t n = list.serialize(buf, sizeof buf);
  TEST_ASSERT_EQUAL(4 + 2 * Alarms::kRecord + strlen(a.label), n);
  Alarms back;
  TEST_ASSERT_TRUE(back.deserialize(buf, n));
  TEST_ASSERT_EQUAL(2, back.count());
  TEST_ASSERT_EQUAL(6, back.at(0).hour);
  TEST_ASSERT_EQUAL(45, back.at(0).minute);
  TEST_ASSERT_EQUAL(days::Weekend, back.at(0).days);
  TEST_ASSERT_EQUAL(9, back.at(0).snoozeMin);
  TEST_ASSERT_EQUAL_STRING("Trezirea ăîșț", back.at(0).label);
  TEST_ASSERT_EQUAL_UINT32(at(0, 1, 2), back.at(0).lastFired);
  TEST_ASSERT_FALSE(back.at(1).enabled);
  TEST_ASSERT_EQUAL_UINT32(at(0, 3, 5), back.at(1).snoozeUntil);
  // corrupt copies are refused and the list stays as it was
  uint8_t bad[Alarms::kMaxBlob];
  memcpy(bad, buf, n);
  bad[4] = 24;  // hour 24
  TEST_ASSERT_FALSE(back.deserialize(bad, n));
  TEST_ASSERT_FALSE(back.deserialize(buf, n - 1));  // truncated
  bad[4] = buf[4];
  bad[2] = 9;  // unknown version
  TEST_ASSERT_FALSE(back.deserialize(bad, n));
  TEST_ASSERT_EQUAL(2, back.count());
  TEST_ASSERT_EQUAL(0, (int)list.serialize(buf, 10));  // too small
  Alarms empty;
  TEST_ASSERT_EQUAL(4, (int)empty.serialize(buf, sizeof buf));
}

void test_alarm_label_is_cut_on_a_code_point() {
  Alarm a;
  std::string s;
  for (int i = 0; i < 30; ++i) s += "ș";  // 60 bytes
  a.setLabel(s.c_str());
  TEST_ASSERT_EQUAL(48, (int)strlen(a.label));
  TEST_ASSERT_EQUAL(24, (int)utf8::count(a.label, strlen(a.label)));
  a.setLabel(("x" + s).c_str());  // odd offset: 47 bytes, never half a ș
  TEST_ASSERT_EQUAL(47, (int)strlen(a.label));
  a.setLabel(nullptr);
  TEST_ASSERT_EQUAL_STRING("", a.label);
}

// ----------------------------------------------------------------- Shell ---

void test_shell_long_press_opens_note_and_commit_goes_home() {
  Alarms alarms;
  Shell sh(&alarms);
  TouchGestures t;
  auto frame = [&](bool down, float x, float y) {
    t.update(down, x, y, kDt);
    TouchEv e;
    int toBrain = 0;
    while (t.poll(e))
      if (!sh.event(e)) ++toBrain;
    t.setMode(sh.wantsTextTouch() ? TouchMode::Text : TouchMode::Face);
    sh.update(kDt, 1790374680u);
    return toBrain;
  };
  TEST_ASSERT_EQUAL(0, frame(true, 233, 233));
  TEST_ASSERT_EQUAL(1, frame(false, 233, 233));  // a tap is the Brain's (boop)
  for (int i = 0; i < 20; ++i) frame(true, 233, 233);  // long press
  TEST_ASSERT_EQUAL(Screen::Note, sh.screen());
  TEST_ASSERT_EQUAL(TouchMode::Text, t.mode());
  frame(false, 233, 233);
  TEST_ASSERT_EQUAL_STRING("", sh.keyboard().text().c_str());  // the lift typed nothing
  float x, y;
  for (const char* p = "hi"; *p; ++p) {
    sh.keyboard().keyCenter((uint32_t)*p, x, y);
    frame(true, x, y);
    frame(false, x, y);
  }
  TEST_ASSERT_EQUAL_STRING("Hi", sh.keyboard().text().c_str());
  sh.keyboard().keyCenter(KeyId::Done, x, y);
  frame(true, x, y);
  frame(false, x, y);
  TEST_ASSERT_EQUAL(Screen::Face, sh.screen());
  Ev e;
  TEST_ASSERT_TRUE(sh.poll(e));
  TEST_ASSERT_EQUAL(Ev::TextCommit, e);
  TEST_ASSERT_EQUAL_STRING("Hi", sh.notes().back().c_str());
  // no note while Claude waits for a decision
  sh.holdOpensNote = false;
  frame(false, 0, 0);
  for (int i = 0; i < 20; ++i) TEST_ASSERT_TRUE(frame(true, 233, 233) >= 0);
  TEST_ASSERT_EQUAL(Screen::Face, sh.screen());
}

void test_shell_time_picker_adds_an_alarm_and_draws() {
  Alarms alarms;
  Shell sh(&alarms);
  sh.update(kDt, 1790374680u);
  sh.openTimePicker(7, 30);
  std::vector<uint16_t> fb(466 * 466, 0);
  Canvas cv(466, 466, fb.data());
  TEST_ASSERT_TRUE(sh.render(cv, Rect{}));
  TEST_ASSERT_FALSE(sh.render(cv, Rect{}));                 // nothing changed: no redraw
  TEST_ASSERT_FALSE(sh.render(cv, Rect{200, 90, 260, 125}));  // the eyes' spot is not ours
  TEST_ASSERT_FALSE(sh.render(cv, Rect{0, 0, 40, 40}));      // a corner outside the ring
  TEST_ASSERT_TRUE(sh.render(cv, Rect{0, 200, 40, 260}));    // the rim was cleared: redraw
  const FaceLayout l = sh.faceLayout();
  TEST_ASSERT_TRUE(l.k < 0.3f && l.cy < -0.4f);  // eyes inside the ring, above the digits
  sh.event(TouchEv{Ev::TouchDown, 233, 350, 0});
  sh.event(TouchEv{Ev::TouchUp, 233, 350, 0});
  sh.update(kDt, 1790374680u);
  TEST_ASSERT_EQUAL(Screen::Face, sh.screen());
  TEST_ASSERT_EQUAL(1, alarms.count());
  TEST_ASSERT_EQUAL(7, alarms.at(0).hour);
  TEST_ASSERT_EQUAL(30, alarms.at(0).minute);
  TEST_ASSERT_TRUE(sh.render(cv, Rect{}));  // leaving: the picker is wiped
  int lit = 0;
  for (uint16_t p : fb) lit += p != 0;
  TEST_ASSERT_EQUAL(0, lit);
}

void test_face_layout_shrinks_eyes_into_the_header() {
  std::vector<uint16_t> fb(466 * 466, 0);
  Canvas cv(466, 466, fb.data());
  Face f;
  FaceLayout l;
  l.k = 0.2f;
  l.cy = -0.845f;
  renderFace(cv, f, l);
  const Rect d = cv.dirty();
  TEST_ASSERT_FALSE(d.empty());
  TEST_ASSERT_TRUE(d.y1 <= Keyboard::bounds().y0 + 2);  // clear of the text field
  TEST_ASSERT_TRUE(d.x0 > 150 && d.x1 < 316);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_personality_is_deterministic);
  RUN_TEST(test_rarity_distribution);
  RUN_TEST(test_touch_tap_and_double_tap);
  RUN_TEST(test_touch_hold_and_stroke);
  RUN_TEST(test_motion_pickup_after_rest);
  RUN_TEST(test_motion_knock_keeps_rest);
  RUN_TEST(test_motion_shake);
  RUN_TEST(test_motion_free_fall_and_orientation);
  RUN_TEST(test_brain_boop_and_shy);
  RUN_TEST(test_brain_dizzy_then_sulks);
  RUN_TEST(test_brain_falls_asleep_and_turns_off_face_down);
  RUN_TEST(test_brain_missed_you_after_absence);
  RUN_TEST(test_brain_hold_purrs_offline_listens_online);
  RUN_TEST(test_brain_claude_approve_needs_full_hold);
  RUN_TEST(test_brain_claude_double_tap_denies_and_tap_does_not);
  RUN_TEST(test_brain_stays_awake_while_claude_works);
  RUN_TEST(test_brain_night_colour);
  RUN_TEST(test_claude_snapshot_events);
  RUN_TEST(test_claude_permission_decision_wire_format);
  RUN_TEST(test_claude_commands_and_acks);
  RUN_TEST(test_claude_time_and_timeout);
  RUN_TEST(test_claude_ignores_garbage);
  RUN_TEST(test_render_draws_eyes_inside_dirty_rect);
  RUN_TEST(test_render_off_draws_nothing);
  // SoulOS
  RUN_TEST(test_touch_events_carry_position);
  RUN_TEST(test_touch_text_mode_keeps_every_fast_tap);
  RUN_TEST(test_touch_text_mode_hold_move_and_long_press_timing);
  RUN_TEST(test_touch_mode_switch_swallows_the_opening_touch);
  RUN_TEST(test_touch_text_mode_jump_is_a_new_finger);
  RUN_TEST(test_utf8_decode_encode_and_invalid_bytes);
  RUN_TEST(test_font_has_romanian_glyphs_and_fallbacks);
  RUN_TEST(test_draw_text_antialiased_inside_dirty_and_clipped);
  RUN_TEST(test_text_alignment_and_measure);
  RUN_TEST(test_textfield_deletes_code_points_and_undoes);
  RUN_TEST(test_textfield_limit_words_and_undo_depth);
  RUN_TEST(test_predictor_ro_diacritics_only_in_romanian_sentences);
  RUN_TEST(test_predictor_english_ui_needs_romanian_evidence);
  RUN_TEST(test_predictor_suggestions_and_next_words);
  RUN_TEST(test_keyboard_hit_test_matches_the_spec_geometry);
  RUN_TEST(test_keyboard_types_hello_with_auto_capital);
  RUN_TEST(test_keyboard_shift_caps_lock_and_number_layers);
  RUN_TEST(test_keyboard_long_press_tray_gives_the_romanian_letter);
  RUN_TEST(test_keyboard_auto_diacritics_and_backspace_revert);
  RUN_TEST(test_keyboard_double_space_done_and_hold_delete);
  RUN_TEST(test_keyboard_renders_inside_its_bounds);
  RUN_TEST(test_timepicker_sundial_and_clock_angles);
  RUN_TEST(test_timepicker_drag_advances_to_minutes_and_confirms);
  RUN_TEST(test_alarm_next_fire_across_midnight_and_week);
  RUN_TEST(test_alarm_rings_once_and_one_shot_switches_off);
  RUN_TEST(test_alarm_snooze_and_dismiss);
  RUN_TEST(test_alarm_binary_roundtrip_and_rejects_corrupt_data);
  RUN_TEST(test_alarm_label_is_cut_on_a_code_point);
  RUN_TEST(test_shell_long_press_opens_note_and_commit_goes_home);
  RUN_TEST(test_shell_time_picker_adds_an_alarm_and_draws);
  RUN_TEST(test_face_layout_shrinks_eyes_into_the_header);
  return UNITY_END();
}
