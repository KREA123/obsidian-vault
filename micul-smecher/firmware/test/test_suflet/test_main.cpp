// Unit tests for the soul engine. Run on the PC: pio test -e native
#include <unity.h>

#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "Brain.h"
#include "ClaudeLink.h"
#include "Face.h"
#include "Gestures.h"
#include "Personality.h"

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
  return UNITY_END();
}
