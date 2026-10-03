// SoulOS on the device: the flows of the web SoulOS v4, driven by a simulated
// finger through the real gesture code, plus the frame pipeline.
#include <unity.h>

#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "CloudLink.h"
#include "Frame.h"
#include "Gestures.h"
#include "Os.h"

using namespace suflet;

namespace {

const uint32_t kNow = 1790359080u;  // a Friday, 18:38 local

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
  bool render = false;

  explicit Dev(bool booted, AiMode mode = AiMode::Claude, bool connected = true) {
    os.settings().booted = booted;
    os.settings().ai = (uint8_t)mode;
    BirthInfo b;
    b.design = 5;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = 1234;
    os.begin(g, b);
    NetInfo n;
    n.configured = n.connected = connected;
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
  void tap(float x, float y) {  // design px
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(0.08f);
    finger = false;
    run(0.5f);
  }
  void hold(float x, float y, float s) {
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(s);
    finger = false;
    run(0.3f);
  }
  void swipe(float x0, float y0, float x1, float y1) {
    finger = true;
    for (int i = 0; i <= 6; ++i) {
      fx = g.s(x0 + (x1 - x0) * i / 6);
      fy = g.s(y0 + (y1 - y0) * i / 6);
      step();
    }
    finger = false;
    run(0.4f);
  }
  void type(const char* text) {  // on the round keyboard, key by key
    const char* p = text;
    while (*p) {
      const uint32_t cp = utf8::next(p);
      float x, y;
      if (!os.keyboard().keyCenter(utf8::lower(cp), x, y)) continue;
      fx = x + 1;
      fy = y + 2;
      finger = true;
      run(0.1f);
      finger = false;
      run(0.07f);
    }
    float x, y;
    os.keyboard().keyCenter(KeyId::Done, x, y);
    fx = x;
    fy = y;
    finger = true;
    run(0.1f);
    finger = false;
    run(0.3f);
  }
  bool hasCmd(OsCmd want) {
    OsCmd c;
    bool found = false;
    while (os.popCmd(c))
      if (c == want) found = true;
    return found;
  }
};

}  // namespace

static void test_os_first_boot_birth_name_brain_hold() {
  Dev d(false, AiMode::None);
  TEST_ASSERT_EQUAL_INT((int)View::Boot, (int)d.os.view());
  TEST_ASSERT_EQUAL_INT((int)BootStep::Birth, (int)d.os.bootStep());
  d.run(1.6f);
  d.tap(233, 250);
  TEST_ASSERT_EQUAL_INT((int)BootStep::Name, (int)d.os.bootStep());
  d.tap(233, 212);  // the first suggested name
  TEST_ASSERT_EQUAL_INT((int)BootStep::Brain, (int)d.os.bootStep());
  TEST_ASSERT_TRUE(strlen(d.os.settings().name) > 1);
  d.tap(233, 186 + 46 * 3);  // "No AI"
  TEST_ASSERT_EQUAL_INT((int)AiMode::None, (int)d.os.aiMode());
  d.tap(233, 420);  // Next
  TEST_ASSERT_EQUAL_INT((int)BootStep::Hold, (int)d.os.bootStep());
  d.hold(233, 233, 0.8f);  // hold the glass, let go
  TEST_ASSERT_EQUAL_INT((int)View::Home, (int)d.os.view());
  TEST_ASSERT_EQUAL_INT(1, d.os.settings().booted);
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::SaveSettings));
}

static void test_os_boot_brain_step_opens_the_setup_portal_when_a_key_is_missing() {
  Dev d(false, AiMode::None, false);
  d.run(1.6f);
  d.tap(233, 250);
  d.tap(233, 212);
  d.hasCmd(OsCmd::None);
  d.tap(233, 232);  // "Claude · your key", no key, no Wi-Fi
  TEST_ASSERT_EQUAL_INT((int)AiMode::Claude, (int)d.os.aiMode());
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::StartPortal));
}

static void test_os_swipe_opens_the_orbit_and_back_is_one_level() {
  Dev d(true);
  d.run(0.5f);
  d.swipe(330, 240, 150, 240);
  TEST_ASSERT_EQUAL_INT((int)View::Launcher, (int)d.os.view());
  d.swipe(330, 330, 150, 330);  // spin: the next app
  TEST_ASSERT_EQUAL_INT(1, d.os.launcherIndex());
  d.os.go(View::AiMode);
  d.run(0.3f);
  d.swipe(233, 200, 233, 380);  // swipe down = back: up one level
  TEST_ASSERT_EQUAL_INT((int)View::Settings, (int)d.os.view());
  d.os.button(true);
  d.run(0.1f);
  d.os.button(false);
  TEST_ASSERT_EQUAL_INT((int)View::Home, (int)d.os.view());
  d.swipe(233, 380, 233, 150);  // swipe up from the face: Today
  TEST_ASSERT_EQUAL_INT((int)View::Today, (int)d.os.view());
}

static void test_os_alarm_in_three_touches() {
  Dev d(true);
  d.os.go(View::Alarms);
  d.run(0.3f);
  d.tap(233, 376);  // + New: the Rim-Dial
  TEST_ASSERT_EQUAL_INT((int)View::Dial, (int)d.os.view());
  // drag the hour from 7 (first alarm) to 6 on the rim, let go
  const float a0 = TimePicker::hourAngle(7), a1 = TimePicker::hourAngle(6);
  d.finger = true;
  for (int i = 0; i <= 10; ++i) {
    const float a = (a0 + (a1 - a0) * i / 10) * 3.14159265f / 180;
    d.fx = d.g.s(233 + 205 * cosf(a));
    d.fy = d.g.s(233 + 205 * sinf(a));
    d.step();
  }
  d.finger = false;
  d.run(0.8f);
  d.tap(233, 350);  // ✓: saved at once
  TEST_ASSERT_EQUAL_INT((int)View::Alarms, (int)d.os.view());
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  TEST_ASSERT_EQUAL_INT(6, d.alarms.at(0).hour);
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::SaveAlarms));
  d.tap(233, 168);  // tap the row: off
  TEST_ASSERT_FALSE(d.alarms.at(0).enabled);
  d.hold(233, 168, 1.4f);  // hold the row: deleted
  TEST_ASSERT_EQUAL_INT(0, d.alarms.count());
}

static void test_os_ask_claude_round_trip_runs_the_actions() {
  Dev d(true, AiMode::Claude);
  d.os.ask("wake me at 6:30 on weekdays");
  TEST_ASSERT_TRUE(d.os.thinking());
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());
  AiJob job;
  TEST_ASSERT_TRUE(d.os.popAiJob(job));
  TEST_ASSERT_EQUAL_STRING("wake me at 6:30 on weekdays", job.text.c_str());
  TEST_ASSERT_EQUAL_UINT32(kNow, job.ctx.now);
  AiOutcome o;
  o.reply = parseReply(
      "{\"say\":\"Weekdays at 6:30.\",\"actions\":[{\"type\":\"alarm.set\",\"time\":\"06:30\",\"label\":\"Up\",\"repeat\":\"weekdays\"}]}");
  o.raw = "{...}";
  d.os.aiResult(o);
  TEST_ASSERT_FALSE(d.os.thinking());
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  TEST_ASSERT_EQUAL_HEX8(0x1F, d.alarms.at(0).days);
  TEST_ASSERT_EQUAL_STRING("Weekdays at 6:30.", d.os.lastReply().say.c_str());
  // the next question carries the conversation
  d.os.ask("and a timer for 5 minutes");
  TEST_ASSERT_TRUE(d.os.popAiJob(job));
  TEST_ASSERT_EQUAL_INT(2, (int)job.history.size());  // the earlier question + answer; the new text travels apart
  TEST_ASSERT_TRUE(job.ctx.alarms.find("06:30 weekdays") != std::string::npos);
}

static void test_os_errors_say_what_to_do_and_local_rules_still_act() {
  Dev d(true, AiMode::Claude);
  d.os.ask("set a timer for 10 minutes");
  AiJob job;
  d.os.popAiJob(job);
  AiOutcome bad;
  bad.err = AiErr::BadKey;
  d.os.aiResult(bad);
  TEST_ASSERT_EQUAL_INT((int)AiErr::BadKey, (int)d.os.lastError());
  TEST_ASSERT_EQUAL_INT(600, d.os.timerLeft());  // the on-device rules still started it
  FaceInputs fi = d.os.faceInputs(d.brain);
  TEST_ASSERT_EQUAL_INT((int)FaceState::Error, (int)fi.state);  // the eyes: confused
  // offline: no request at all
  Dev off(true, AiMode::Claude, false);
  off.os.ask("wake me at 7");
  TEST_ASSERT_FALSE(off.os.popAiJob(job));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Offline, (int)off.os.lastError());
  TEST_ASSERT_EQUAL_INT(1, off.alarms.count());
  // and a hung network times out by itself
  Dev slow(true, AiMode::Claude);
  slow.os.ask("hello?");
  slow.run(46);
  TEST_ASSERT_FALSE(slow.os.thinking());
  TEST_ASSERT_EQUAL_INT((int)AiErr::Timeout, (int)slow.os.lastError());
}

static void test_os_no_ai_mode_keeps_working_on_the_device() {
  Dev d(true, AiMode::None);
  d.os.ask("remind me to call the bank at 5");
  AiJob job;
  TEST_ASSERT_FALSE(d.os.popAiJob(job));
  TEST_ASSERT_EQUAL_INT(1, (int)d.os.reminders().size());
  TEST_ASSERT_EQUAL_UINT32(17u, d.os.reminders()[0].when % 86400 / 3600);
  d.os.ask("the meaning of life");
  TEST_ASSERT_EQUAL_INT(1, (int)d.os.notes().size());  // kept in Notes
}

static void test_os_hold_the_glass_approves_a_claude_request() {
  Dev d(true);
  ClaudeInfo ci;
  ci.linked = ci.prompt = true;
  ci.tool = "Bash";
  d.os.setClaude(ci);
  d.brain.event(Ev::ClaudePrompt);
  d.run(0.3f);
  TEST_ASSERT_EQUAL_INT((int)FaceState::Wait, (int)d.os.faceInputs(d.brain).state);
  TEST_ASSERT_TRUE(d.os.faceInputs(d.brain).alert);
  d.fx = d.g.s(233);
  d.fy = d.g.s(260);
  d.finger = true;
  bool approved = false, progressed = false;
  for (int i = 0; i < 60; ++i) {
    d.step();
    if (d.brain.approveProgress() > 0.5f) progressed = true;
    Cue c;
    while (d.brain.popCue(c))
      if (c == Cue::ClaudeApprove) approved = true;
  }
  d.finger = false;
  d.run(0.2f);
  TEST_ASSERT_TRUE(progressed);
  TEST_ASSERT_TRUE(approved);
}

static void test_os_timer_rings_and_stop_goes_home() {
  Dev d(true);
  d.os.startTimer(2, false);
  d.run(2.3f);
  TEST_ASSERT_EQUAL_INT((int)View::Ringing, (int)d.os.view());
  TEST_ASSERT_TRUE(d.os.ringing());
  d.tap(233, 400);  // Stop (centred for a timer)
  d.tap(316, 400);
  TEST_ASSERT_FALSE(d.os.ringing());
  TEST_ASSERT_EQUAL_INT((int)View::Home, (int)d.os.view());
}

static void test_os_notes_settings_and_reminders_survive_a_restart() {
  Dev a(true);
  a.os.ask("x");  // a note via the no-AI path would need mode None; add directly
  a.os.notes().clear();
  Note n1;
  n1.text = "buy oat milk";
  n1.t = 5;
  Note n2;
  n2.text = "idea:\ttabs\nand lines";
  n2.t = 6;
  a.os.notes() = {n1, n2};
  Reminder r;
  r.when = kNow + 600;
  r.text = "oven";
  a.os.reminders() = {r};
  snprintf(a.os.settings().name, sizeof a.os.settings().name, "Miso");
  a.os.settings().lang = 1;
  uint8_t buf[sizeof(OsSettings)];
  const size_t n = a.os.saveSettings(buf, sizeof buf);
  Dev b(true);
  TEST_ASSERT_TRUE(b.os.loadSettings(buf, n));
  b.os.loadNotes(a.os.saveNotes());
  b.os.loadReminders(a.os.saveReminders());
  TEST_ASSERT_EQUAL_STRING("Miso", b.os.settings().name);
  TEST_ASSERT_TRUE(b.os.ro());
  TEST_ASSERT_EQUAL_INT(2, (int)b.os.notes().size());
  TEST_ASSERT_EQUAL_STRING("idea: tabs and lines", b.os.notes()[1].text.c_str());
  TEST_ASSERT_EQUAL_UINT32(kNow + 600, b.os.reminders()[0].when);
  buf[0] = 99;  // another version: refused, defaults kept
  TEST_ASSERT_FALSE(b.os.loadSettings(buf, n));
  b.os.loadNotes(std::string("garbage without tabs\n\n\t\n123\tok\n"));
  TEST_ASSERT_EQUAL_INT(1, (int)b.os.notes().size());
}

static void test_frame_pipeline_equals_a_full_redraw() {
  // Draw only what changes (repair under the old eyes + the UI's dirty
  // rects), then compare with a from-scratch render of the same state.
  Dev d(true);
  d.render = true;
  std::vector<uint16_t> ref(480 * 480);
  Canvas rc(480, 480, ref.data());
  auto check = [&](const char* when) {
    std::fill(ref.begin(), ref.end(), 0);
    rc.clearClip();
    d.os.render(rc);
    d.os.face().render(rc);
    int diff = 0;
    for (size_t i = 0; i < ref.size(); ++i)
      if (ref[i] != d.fb[i]) ++diff;
    TEST_ASSERT_EQUAL_INT_MESSAGE(0, diff, when);
  };
  d.run(1.0f);
  check("home");
  d.os.face().react(eyes::X_laugh);
  d.run(0.7f);
  check("laugh");
  d.swipe(330, 240, 150, 240);
  d.run(0.4f);
  check("launcher");
  d.os.go(View::Alarms);
  d.run(0.1f);
  check("fading in");
  d.run(0.5f);
  check("alarms");
  d.os.go(View::Talk);
  d.run(0.5f);
  d.os.ask("what time is it?");
  d.run(0.6f);
  check("thinking ring");
  d.os.go(View::Home);
  d.run(1.2f);
  check("home again");
}

static void test_frame_pipeline_touches_little_of_the_glass_when_idle() {
  Dev d(true);
  d.render = true;
  d.run(1.5f);
  uint64_t px = 0;
  for (int i = 0; i < 60; ++i) {
    d.step();
    px += d.comp.stats().changedPx;
  }
  const double frac = px / (60.0 * 480 * 480);
  TEST_ASSERT_TRUE_MESSAGE(frac < 0.45, "idle frames should touch less than half the glass");
}


static NetInfo cloudNet(bool paired) {
  NetInfo n;
  n.configured = n.connected = true;
  n.ssid = "home";
  n.relay = n.cloudOnline = true;
  n.paired = paired;
  n.owner = paired ? "Ana" : "";
  n.pairCode = paired ? "" : "7KQ3M9XD";
  n.pairUrl = paired ? "" : "https://soul.example/pair#c=7KQ3M9XD&d=soul-c0ffee123456";
  return n;
}

static void test_os_cloud_pairing_shows_the_code_then_greets_the_owner() {
  Dev d(true, AiMode::Claude);
  d.os.setNet(cloudNet(false));
  d.render = true;
  d.os.go(View::AiMode);
  d.run(0.3f);
  d.tap(233, 150);  // SOUL Cloud
  TEST_ASSERT_EQUAL_INT((int)AiMode::Cloud, (int)d.os.aiMode());
  TEST_ASSERT_EQUAL_INT((int)View::Pair, (int)d.os.view());
  d.run(0.4f);
  // the QR card is drawn under the code: light pixels around (233, 330) design px
  int light = 0;
  for (int y = (int)d.g.s(290); y < (int)d.g.s(370); y += 2)
    for (int x = (int)d.g.s(193); x < (int)d.g.s(273); x += 2)
      if (Rgb::from565(d.cv.at(x, y)).r > 200) ++light;
  TEST_ASSERT_TRUE(light > 200);
  d.os.setNet(cloudNet(true));  // the owner typed the code on the account page
  d.run(0.5f);
  TEST_ASSERT_EQUAL_INT((int)View::Pair, (int)d.os.view());  // "Paired · Ana" for a moment
  d.run(3.0f);
  TEST_ASSERT_EQUAL_INT((int)View::AiMode, (int)d.os.view());
  // Settings › AI › Connect Claude once paired: a QR to this SOUL's page on the phone (paste the Claude key)
  NetInfo n = cloudNet(true);
  n.cloudHost = "soul.example";
  d.os.setNet(n);
  d.tap(233, 136);
  TEST_ASSERT_EQUAL_INT((int)View::Pair, (int)d.os.view());
  d.run(0.5f);
  int qr = 0;
  for (int y = (int)d.g.s(250); y < (int)d.g.s(350); y += 2)
    for (int x = (int)d.g.s(183); x < (int)d.g.s(283); x += 2)
      if (Rgb::from565(d.cv.at(x, y)).r > 200) ++qr;
  TEST_ASSERT_TRUE(qr > 200);
}

static void test_os_cloud_pushes_apply_once_and_can_be_deleted() {
  Dev d(true, AiMode::Cloud);
  d.os.setNet(cloudNet(true));
  CloudLink link;
  std::string err;
  auto push = [&](const char* json) {
    TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Push, (int)link.feed(json, strlen(json)));
    err.clear();
    const bool ok = d.os.cloudPush(link.push, err);
    d.run(0.1f);
    return ok;
  };
  // a reminder from the Claude phone app, a week ahead
  const char* rem = "{\"v\":1,\"t\":\"push\",\"seq\":412,\"action\":\"reminder.create\",\"args\":{\"when\":\"2026-10-03T18:00\","
                    "\"text\":\"Call the bank\"},\"item_id\":\"r_412\",\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"},\"say\":\"I'll remind you.\"}";
  TEST_ASSERT_TRUE(push(rem));
  TEST_ASSERT_EQUAL_INT(1, (int)d.os.reminders().size());
  TEST_ASSERT_EQUAL_UINT32(parseLocalStamp("2026-10-03T18:00"), d.os.reminders()[0].when);
  TEST_ASSERT_TRUE(push(rem));  // the same item again (a replay after a lost ack): not twice
  TEST_ASSERT_EQUAL_INT(1, (int)d.os.reminders().size());
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::SaveCloudRefs));

  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":413,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":"
                        "[\"mon\",\"tue\",\"wed\",\"thu\",\"fri\"],\"label\":\"Gym\"},\"item_id\":\"a_413\",\"origin\":{\"kind\":\"turn\"}}"));
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  TEST_ASSERT_EQUAL_INT(0x1F, d.alarms.at(0).days);
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":414,\"action\":\"note.create\",\"args\":{\"text\":\"buy batteries\"},"
                        "\"item_id\":\"n_414\",\"origin\":{\"kind\":\"connector\"}}"));
  TEST_ASSERT_EQUAL_STRING("buy batteries", d.os.notes()[0].text.c_str());
  CloudOut out;
  TEST_ASSERT_FALSE(d.os.popCloudOut(out));  // pushed items are not echoed back as item.add

  // the refs survive a restart: delete still finds them
  const std::string refs = d.os.saveCloudRefs();
  Dev d2(true, AiMode::Cloud);
  d2.os.loadCloudRefs(refs);
  TEST_ASSERT_EQUAL_STRING(refs.c_str(), d2.os.saveCloudRefs().c_str());

  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":415,\"action\":\"item.delete\",\"args\":{\"item_id\":\"a_413\"}}"));
  TEST_ASSERT_EQUAL_INT(0, d.alarms.count());
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":416,\"action\":\"item.delete\",\"args\":{\"item_id\":\"r_412\"}}"));
  TEST_ASSERT_EQUAL_INT(0, (int)d.os.reminders().size());
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":417,\"action\":\"item.delete\",\"args\":{\"item_id\":\"n_414\"}}"));
  TEST_ASSERT_EQUAL_INT(0, (int)d.os.notes().size());
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":418,\"action\":\"item.delete\",\"args\":{\"item_id\":\"gone\"}}"));

  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":419,\"action\":\"timer.start\",\"args\":{\"seconds\":90}}"));
  TEST_ASSERT_TRUE(d.os.timerLeft() >= 88 && d.os.timerLeft() <= 90);
  // too late to ring: said once, not stored
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":420,\"action\":\"reminder.create\",\"args\":{\"when\":\"2026-09-20T08:00\","
                        "\"text\":\"Pills\"},\"item_id\":\"r_420\",\"missed\":true}"));
  TEST_ASSERT_EQUAL_INT(0, (int)d.os.reminders().size());
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":421,\"action\":\"answer.show\",\"args\":{\"title\":\"Pancakes\","
                        "\"body\":\"1. flour\\n2. eggs\\n3. pan\"},\"origin\":{\"kind\":\"connector\"}}"));
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());
  TEST_ASSERT_FALSE(push("{\"v\":1,\"t\":\"push\",\"seq\":422,\"action\":\"lights.on\",\"args\":{}}"));
  TEST_ASSERT_EQUAL_STRING("unsupported", err.c_str());
  TEST_ASSERT_FALSE(push("{\"v\":1,\"t\":\"push\",\"seq\":423,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"31:00\"}}"));
  TEST_ASSERT_EQUAL_STRING("invalid", err.c_str());
}

static void test_os_cloud_pair_confirm_needs_a_touch_on_soul() {
  Dev d(true, AiMode::Cloud);
  NetInfo n = cloudNet(false);
  d.os.setNet(n);
  d.os.go(View::Notes);
  d.run(0.3f);
  // someone claimed the code on the phone: SOUL asks, and only a touch answers
  n.confirmPid = "p_1";
  n.confirmName = "Ana";
  n.confirmHint = "a***@gmail.com";
  d.os.setNet(n);
  d.run(0.4f);
  TEST_ASSERT_EQUAL_INT((int)View::Pair, (int)d.os.view());
  CloudOut o;
  TEST_ASSERT_FALSE(d.os.popCloudOut(o));  // nothing by itself
  d.run(5.0f);
  TEST_ASSERT_FALSE(d.os.popCloudOut(o));
  d.tap(160, 372);  // "Yes, pair"
  TEST_ASSERT_TRUE(d.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_INT(CloudOut::PairOk, o.kind);
  TEST_ASSERT_EQUAL_STRING("p_1", o.pid.c_str());
  TEST_ASSERT_FALSE(d.os.popCloudOut(o));  // once
  n.confirmPid.clear();
  n.paired = true;
  n.owner = "Ana";
  n.pairCode.clear();
  d.os.setNet(n);
  d.run(3.5f);
  TEST_ASSERT_EQUAL_INT((int)View::Notes, (int)d.os.view());  // back where it was
  // a second request, refused
  Dev e(true, AiMode::Cloud);
  NetInfo m = cloudNet(false);
  m.confirmPid = "p_2";
  m.confirmName = "Mallory";
  e.os.setNet(m);
  e.run(0.4f);
  e.tap(306, 372);  // "No"
  TEST_ASSERT_TRUE(e.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_INT(CloudOut::PairNo, o.kind);
}

static void test_os_cloud_night_alarm_private_card_and_pause() {
  Dev d(true, AiMode::Cloud);
  d.os.setNet(cloudNet(true));
  d.run(0.2f);
  CloudLink link;
  std::string err;
  auto push = [&](const char* json) {
    TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Push, (int)link.feed(json, strlen(json)));
    err.clear();
    const bool ok = d.os.cloudPush(link.push, err);
    d.run(0.2f);
    return ok;
  };
  // a connector alarm at 03:00 arrives pending: not armed until the owner taps Accept
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":5,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"03:00\",\"days\":[],"
                        "\"label\":\"Flight\"},\"item_id\":\"it_5\",\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"},"
                        "\"needs_accept\":true}"));
  TEST_ASSERT_EQUAL_INT(0, d.alarms.count());
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());
  d.run(30.0f);
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());  // it waits for an answer
  d.tap(233, 250);  // a tap elsewhere does not accept it
  TEST_ASSERT_EQUAL_INT(0, d.alarms.count());
  d.tap(160, 392);  // Accept
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  CloudOut o;
  TEST_ASSERT_TRUE(d.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_INT(CloudOut::State, o.kind);
  TEST_ASSERT_EQUAL_STRING("it_5", o.itemId.c_str());
  TEST_ASSERT_EQUAL_STRING("accepted", o.state.c_str());
  // another one, closed with the side button: rejected, nothing armed
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":6,\"action\":\"reminder.create\",\"args\":{\"when\":\"2030-01-01T02:00\","
                        "\"text\":\"Wake up\"},\"item_id\":\"it_6\",\"origin\":{\"kind\":\"connector\",\"app\":\"chatgpt\"},"
                        "\"needs_accept\":true}"));
  d.os.back();
  TEST_ASSERT_EQUAL_INT(0, (int)d.os.reminders().size());
  TEST_ASSERT_TRUE(d.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_STRING("rejected", o.state.c_str());
  // a private card shows its title only until a tap
  d.run(0.5f);
  TEST_ASSERT_TRUE(push("{\"v\":1,\"t\":\"push\",\"seq\":7,\"action\":\"answer.show\",\"args\":{\"title\":\"Test results\","
                        "\"body\":\"All fine.\"},\"item_id\":\"it_7\",\"private\":true,\"origin\":{\"kind\":\"connector\"}}"));
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());
  TEST_ASSERT_TRUE(d.os.lastReply().say.empty());
  d.tap(233, 250);
  TEST_ASSERT_EQUAL_STRING("All fine.", d.os.lastReply().say.c_str());
  TEST_ASSERT_EQUAL_INT((int)View::Answer, (int)d.os.view());
  d.tap(233, 250);
  // pause connectors: a switch in Settings (a touch), sent up
  d.os.go(View::Settings);
  d.run(0.3f);
  d.swipe(233, 380, 233, 160);  // page 2
  d.swipe(233, 380, 233, 160);  // page 3: night, Claude & ChatGPT on me, Start over
  d.run(0.3f);
  d.tap(233, 234);
  TEST_ASSERT_TRUE(d.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_INT(CloudOut::Connectors, o.kind);
  TEST_ASSERT_TRUE(o.paused);
}

static void test_os_cloud_answers_with_a_reason_and_timeouts_do_not_act_twice() {
  Dev d(true, AiMode::Cloud);
  d.os.setNet(cloudNet(true));
  d.os.ask("set an alarm at 7");
  AiJob j;
  TEST_ASSERT_TRUE(d.os.popAiJob(j));
  AiOutcome o;
  o.err = AiErr::Timeout;
  o.noLocal = true;  // the cloud's turn may still set it: no second alarm from the rules
  d.os.aiResult(o);
  TEST_ASSERT_EQUAL_INT(0, d.alarms.count());
  d.os.ask("set an alarm at 7");
  TEST_ASSERT_TRUE(d.os.popAiJob(j));
  AiOutcome net;
  net.err = AiErr::Network;  // never reached the cloud: the rules do it
  d.os.aiResult(net);
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  d.os.ask("hello");
  TEST_ASSERT_TRUE(d.os.popAiJob(j));
  AiOutcome rules;
  rules.reply.say = "Hi!";
  rules.note = AiErr::BadKey;  // SOUL Cloud answered with its rules: shown, plus why
  d.os.aiResult(rules);
  TEST_ASSERT_EQUAL_STRING("Hi!", d.os.lastReply().say.c_str());
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)d.os.lastError());
}

static void test_os_cloud_items_made_on_soul_and_ask_my_claude_go_up() {
  Dev d(true, AiMode::Cloud);
  d.os.setNet(cloudNet(true));
  d.os.go(View::Notes);
  d.run(0.3f);
  d.tap(233, 360);  // + New
  d.type("milk");
  CloudOut o;
  TEST_ASSERT_TRUE(d.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_INT(CloudOut::Item, o.kind);
  TEST_ASSERT_EQUAL_INT(AiAction::NoteCreate, o.act.type);
  TEST_ASSERT_EQUAL_STRING("Milk", o.act.text.c_str());  // the keyboard capitalises a sentence

  d.os.go(View::Claude);
  d.run(0.3f);
  d.tap(233, 396);  // Ask my Claude
  TEST_ASSERT_EQUAL_INT((int)View::Keyboard, (int)d.os.view());
  d.type("plan my day");
  TEST_ASSERT_TRUE(d.os.popCloudOut(o));
  TEST_ASSERT_EQUAL_INT(CloudOut::Inbox, o.kind);
  TEST_ASSERT_EQUAL_STRING("Plan my day", o.text.c_str());
  TEST_ASSERT_EQUAL_INT((int)View::Claude, (int)d.os.view());

  // unpaired: the same word opens the pairing screen instead
  d.os.setNet(cloudNet(false));
  d.tap(233, 396);
  TEST_ASSERT_EQUAL_INT((int)View::Pair, (int)d.os.view());
  d.os.back();
  TEST_ASSERT_EQUAL_INT((int)View::Claude, (int)d.os.view());

  // the account page changed the brain and the language
  d.os.cloudConfig("chatgpt", "ro", "Bubu");
  TEST_ASSERT_EQUAL_INT((int)AiMode::ChatGpt, (int)d.os.aiMode());
  TEST_ASSERT_TRUE(d.os.ro());
  TEST_ASSERT_EQUAL_STRING("Bubu", d.os.settings().name);
  d.os.cloudConfig("none", "", "");
  TEST_ASSERT_EQUAL_INT((int)AiMode::None, (int)d.os.aiMode());
}

void runOsTests() {
  RUN_TEST(test_os_first_boot_birth_name_brain_hold);
  RUN_TEST(test_os_boot_brain_step_opens_the_setup_portal_when_a_key_is_missing);
  RUN_TEST(test_os_swipe_opens_the_orbit_and_back_is_one_level);
  RUN_TEST(test_os_alarm_in_three_touches);
  RUN_TEST(test_os_ask_claude_round_trip_runs_the_actions);
  RUN_TEST(test_os_errors_say_what_to_do_and_local_rules_still_act);
  RUN_TEST(test_os_no_ai_mode_keeps_working_on_the_device);
  RUN_TEST(test_os_hold_the_glass_approves_a_claude_request);
  RUN_TEST(test_os_timer_rings_and_stop_goes_home);
  RUN_TEST(test_os_notes_settings_and_reminders_survive_a_restart);
  RUN_TEST(test_frame_pipeline_equals_a_full_redraw);
  RUN_TEST(test_frame_pipeline_touches_little_of_the_glass_when_idle);
  RUN_TEST(test_os_cloud_pairing_shows_the_code_then_greets_the_owner);
  RUN_TEST(test_os_cloud_pushes_apply_once_and_can_be_deleted);
  RUN_TEST(test_os_cloud_items_made_on_soul_and_ask_my_claude_go_up);
  RUN_TEST(test_os_cloud_pair_confirm_needs_a_touch_on_soul);
  RUN_TEST(test_os_cloud_night_alarm_private_card_and_pause);
  RUN_TEST(test_os_cloud_answers_with_a_reason_and_timeouts_do_not_act_twice);
}
