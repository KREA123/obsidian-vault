// SOUL on the go (docs/09-EVERYWHERE.md): saved networks, roaming, the phone's
// hotspot, captive portals and the offline question queue.
#include <unity.h>

#include <cstring>
#include <string>
#include <vector>

#include "Gestures.h"
#include "Os.h"
#include "WifiRoam.h"

using namespace suflet;

namespace {

WifiNet net(const char* ssid, WifiKind k, const char* pass = "password1") {
  WifiNet n;
  n.ssid = ssid;
  n.pass = pass;
  n.kind = k;
  n.prio = wifiDefaultPrio(k);
  return n;
}

// A scripted radio around the roamer: what is on the air, whether joins work,
// what the internet check says. Runs the roamer in 100 ms steps.
struct Air {
  WifiBook book;
  WifiRoamer r;
  std::vector<ScanHit> hits;
  uint32_t now = 1000;
  bool link = false;
  int rssi = 0;
  std::string joined;       // the SSID joined (as sent by the roamer)
  std::string badPass;      // joining this one fails with a wrong password
  ProbeResult probe = ProbeResult::Online;
  std::string captiveSsid;  // this one has a login page
  int scans = 0, joins = 0, probes = 0, leaves = 0;
  Air() { r.setBook(&book); }
  int rssiOf(const std::string& s) const {
    for (const ScanHit& h : hits)
      if (h.ssid == s) return h.rssi;
    return 0;
  }
  void step() {
    now += 100;
    if (link && !rssiOf(joined)) {  // the network went away
      link = false;
      joined.clear();
    }
    RoamCmd c = r.tick(now, link, link ? rssiOf(joined) : 0);
    switch (c.kind) {
      case RoamCmd::Scan:
        ++scans;
        r.scanDone(now, hits);
        break;
      case RoamCmd::Join:
        ++joins;
        link = false;
        if (c.ssid == badPass) {
          r.joinFailed(now, JoinFail::BadPassword);
        } else if (rssiOf(c.ssid)) {
          joined = c.ssid;
          link = true;
        }
        break;
      case RoamCmd::Probe:
        ++probes;
        r.probed(now, joined == captiveSsid ? ProbeResult::Captive : probe);
        break;
      case RoamCmd::Leave:
        ++leaves;
        link = false;
        joined.clear();
        break;
      default: break;
    }
  }
  void run(float s) {
    for (int i = 0; i < (int)(s * 10 + 0.5f); ++i) step();
  }
};

}  // namespace

static void test_wifi_book_adds_updates_and_survives_a_roundtrip() {
  WifiBook b;
  TEST_ASSERT_EQUAL_INT(0, b.add(net("home", WifiKind::Home)));
  TEST_ASSERT_EQUAL_INT(1, b.add(net("Ana\xE2\x80\x99s iPhone", WifiKind::Hotspot, "hotspot99")));
  TEST_ASSERT_EQUAL_INT(2, b.add(net("cafe", WifiKind::Other, "")));  // an open network
  TEST_ASSERT_EQUAL_INT(-1, b.add(net("short", WifiKind::Work, "1234567")));  // WPA2 needs 8..63
  TEST_ASSERT_EQUAL_INT(-1, b.add(net("", WifiKind::Work)));
  TEST_ASSERT_EQUAL_INT(-1, b.add(net("123456789012345678901234567890123", WifiKind::Work)));  // 33 bytes
  // the same name updates it; an empty password keeps the old one
  WifiNet again = net("home", WifiKind::Home, "");
  again.prio = 9;
  TEST_ASSERT_EQUAL_INT(0, b.add(again));
  TEST_ASSERT_EQUAL_STRING("password1", b.at(0).pass.c_str());
  TEST_ASSERT_EQUAL_INT(9, b.at(0).prio);
  TEST_ASSERT_EQUAL_INT(9, b.topPrio());
  TEST_ASSERT_EQUAL_INT(3, b.at(1).prio);  // a hotspot comes after the fixed networks by default
  const std::string blob = b.save();
  WifiBook c;
  TEST_ASSERT_TRUE(c.load(blob));
  TEST_ASSERT_EQUAL_INT(3, c.count());
  TEST_ASSERT_EQUAL_STRING("Ana\xE2\x80\x99s iPhone", c.at(1).ssid.c_str());
  TEST_ASSERT_EQUAL_STRING("hotspot99", c.at(1).pass.c_str());
  TEST_ASSERT_EQUAL_INT((int)WifiKind::Hotspot, (int)c.at(1).kind);
  TEST_ASSERT_EQUAL_STRING("", c.at(2).pass.c_str());
  // corrupt or truncated blobs are refused and change nothing
  TEST_ASSERT_FALSE(c.load(blob.substr(0, blob.size() - 1)));
  TEST_ASSERT_FALSE(c.load(blob + "x"));
  std::string bad = blob;
  bad[2] = 9;
  TEST_ASSERT_FALSE(c.load(bad));
  TEST_ASSERT_EQUAL_INT(3, c.count());
  // full at kMax
  WifiBook f;
  for (int i = 0; i < WifiBook::kMax; ++i) TEST_ASSERT_EQUAL_INT(i, f.add(net(("n" + std::to_string(i)).c_str(), WifiKind::Other)));
  TEST_ASSERT_EQUAL_INT(-1, f.add(net("one more", WifiKind::Other)));
  TEST_ASSERT_TRUE(f.remove(0));
  TEST_ASSERT_EQUAL_INT(WifiBook::kMax - 1, f.add(net("one more", WifiKind::Other)));
}

static void test_wifi_iphone_names_match_without_the_curly_apostrophe() {
  TEST_ASSERT_EQUAL_INT(2, ssidMatch("Ana\xE2\x80\x99s iPhone", "Ana\xE2\x80\x99s iPhone"));
  TEST_ASSERT_EQUAL_INT(1, ssidMatch("Ana's iPhone", "Ana\xE2\x80\x99s iPhone"));  // typed on SOUL vs on the air
  TEST_ASSERT_EQUAL_INT(1, ssidMatch("ana's iphone ", "Ana\xE2\x80\x99s iPhone"));
  TEST_ASSERT_EQUAL_INT(0, ssidMatch("Ana iPhone", "Ana\xE2\x80\x99s iPhone"));
  TEST_ASSERT_EQUAL_INT(0, ssidMatch("", "x"));
  // the roamer joins the name exactly as it is on the air
  Air a;
  a.book.add(net("ana's iphone", WifiKind::Hotspot));
  a.hits = {{"Ana\xE2\x80\x99s iPhone", -50}};
  a.run(1);
  TEST_ASSERT_EQUAL_STRING("Ana\xE2\x80\x99s iPhone", a.joined.c_str());
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)a.r.state());
}

static void test_wifi_roamer_picks_by_priority_then_signal() {
  Air a;
  a.book.add(net("phone", WifiKind::Hotspot));
  a.book.add(net("home", WifiKind::Home));
  a.book.add(net("office", WifiKind::Work));
  a.hits = {{"phone", -40}, {"office", -60}, {"home", -84}, {"neighbour", -30}};
  a.run(1);
  TEST_ASSERT_EQUAL_STRING("home", a.joined.c_str());  // home first, even weaker (above kMinRssi)
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)a.r.state());
  TEST_ASSERT_EQUAL_INT(1, a.probes);
  // too weak to try: the next one
  Air b;
  b.book.add(net("home", WifiKind::Home));
  b.book.add(net("office", WifiKind::Work));
  b.hits = {{"home", -90}, {"office", -70}};
  b.run(1);
  TEST_ASSERT_EQUAL_STRING("office", b.joined.c_str());
  // at boot the last good network is tried before any scan
  Air w;
  w.book.add(net("home", WifiKind::Home));
  w.book.add(net("phone", WifiKind::Hotspot));
  w.hits = {{"phone", -50}};
  w.r.preferFirst(1);
  w.run(0.5f);
  TEST_ASSERT_EQUAL_STRING("phone", w.joined.c_str());
  TEST_ASSERT_EQUAL_INT(0, w.scans);
  // nothing saved: no scans, nothing to do
  Air c;
  c.run(5);
  TEST_ASSERT_EQUAL_INT(0, c.scans);
  TEST_ASSERT_EQUAL_INT((int)NetState::NoNetworks, (int)c.r.state());
}

static void test_wifi_hotspot_is_joined_within_seconds_when_it_appears() {
  Air a;
  a.book.add(net("home", WifiKind::Home));
  a.book.add(net("phone", WifiKind::Hotspot));
  a.hits = {{"home", -55}};
  a.run(2);
  TEST_ASSERT_EQUAL_STRING("home", a.joined.c_str());
  // out of the door: home is gone
  a.hits.clear();
  a.run(30);
  TEST_ASSERT_EQUAL_INT((int)NetState::Searching, (int)a.r.state());
  TEST_ASSERT_TRUE(a.r.fast(a.now));
  TEST_ASSERT_EQUAL_INT((int)JoinFail::NotFound, (int)a.r.lastFail());
  // the hotspot is switched on: joined within one fast scan (4 s) + the join
  a.hits = {{"phone", -45}};
  const uint32_t on = a.now;
  while (a.joined.empty() && a.now - on < 20000) a.step();
  TEST_ASSERT_EQUAL_STRING("phone", a.joined.c_str());
  TEST_ASSERT_TRUE(a.now - on <= WifiRoamer::kFastScanMs + 500);
  a.run(1);
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)a.r.state());
  // after 10 minutes without anything, the search slows down to once a minute (battery)
  a.hits.clear();
  a.run(1);
  const int s0 = a.scans;
  a.run(600);
  const int s1 = a.scans;
  a.run(120);
  TEST_ASSERT_TRUE(s1 - s0 > 40);        // fast, then every 20 s
  TEST_ASSERT_TRUE(a.scans - s1 <= 3);   // then about once a minute
  // a kick (SOUL picked up, a question waits) makes it fast again
  a.r.kick(a.now);
  const int s2 = a.scans;
  a.run(20);
  TEST_ASSERT_TRUE(a.scans - s2 >= 4);
}

static void test_wifi_roams_home_from_the_hotspot_and_away_from_a_weak_network() {
  Air a;
  a.book.add(net("home", WifiKind::Home));
  a.book.add(net("phone", WifiKind::Hotspot));
  a.hits = {{"phone", -50}};
  a.run(2);
  TEST_ASSERT_EQUAL_STRING("phone", a.joined.c_str());
  // back home: on the next look-around (every 2 min on a second choice) it moves to home
  a.hits = {{"phone", -50}, {"home", -60}};
  a.run(125);
  TEST_ASSERT_EQUAL_STRING("home", a.joined.c_str());
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)a.r.state());
  // on home, strong: no more scanning while online
  const int s = a.scans;
  a.run(300);
  TEST_ASSERT_EQUAL_INT(s, a.scans);
  // a weak home next to a strong network of the same priority: moves
  Air b;
  b.book.add(net("a", WifiKind::Home));
  b.book.add(net("b", WifiKind::Home));
  b.hits = {{"a", -60}};
  b.run(2);
  TEST_ASSERT_EQUAL_STRING("a", b.joined.c_str());
  b.hits = {{"a", -84}, {"b", -58}};
  b.run(125);
  TEST_ASSERT_EQUAL_STRING("b", b.joined.c_str());
  // a better network that is too weak to be worth it: stays
  Air c;
  c.book.add(net("home", WifiKind::Home));
  c.book.add(net("phone", WifiKind::Hotspot));
  c.hits = {{"phone", -50}};
  c.run(2);
  c.hits.push_back({"home", -78});
  c.run(130);
  TEST_ASSERT_EQUAL_STRING("phone", c.joined.c_str());
}

static void test_wifi_wrong_password_backs_off_and_tries_the_next() {
  Air a;
  a.book.add(net("home", WifiKind::Home));
  a.book.add(net("phone", WifiKind::Hotspot));
  a.hits = {{"home", -50}, {"phone", -50}};
  a.badPass = "home";
  a.run(10);
  TEST_ASSERT_EQUAL_STRING("phone", a.joined.c_str());
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)a.r.state());
  // the hotspot goes: home is not retried with the wrong password, even after a kick
  a.hits = {{"home", -50}};
  const int j = a.joins;
  a.r.kick(a.now);
  a.run(60);
  TEST_ASSERT_EQUAL_INT(j, a.joins);
  TEST_ASSERT_EQUAL_INT((int)JoinFail::BadPassword, (int)a.r.lastFail());
  // the password is fixed (the book changed): joined
  a.badPass.clear();
  a.r.bookChanged(a.now, "");
  a.run(6);
  TEST_ASSERT_EQUAL_STRING("home", a.joined.c_str());
  TEST_ASSERT_EQUAL_INT((int)JoinFail::None, (int)a.r.lastFail());
  // a join that never completes times out and is backed off
  WifiBook book;
  book.add(net("ghost", WifiKind::Home));
  WifiRoamer r;
  r.setBook(&book);
  uint32_t t = 0;
  RoamCmd cmd = r.tick(t, false, 0);
  TEST_ASSERT_EQUAL_INT(RoamCmd::Scan, cmd.kind);
  r.scanDone(t, {{"ghost", -40}});
  cmd = r.tick(t += 100, false, 0);
  TEST_ASSERT_EQUAL_INT(RoamCmd::Join, cmd.kind);
  for (t += 100; t < 15000; t += 100) TEST_ASSERT_EQUAL_INT(RoamCmd::None, r.tick(t, false, 0).kind);
  cmd = r.tick(t += 200, false, 0);
  TEST_ASSERT_EQUAL_INT(RoamCmd::Leave, cmd.kind);
  TEST_ASSERT_EQUAL_INT((int)JoinFail::Timeout, (int)r.lastFail());
  TEST_ASSERT_EQUAL_INT((int)NetState::Searching, (int)r.state());
}

static void test_wifi_captive_portal_is_told_apart_and_left_for_a_better_network() {
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::Online, (int)classifyProbe(204, 0));
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::Online, (int)classifyProbe(200, 0));
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::Captive, (int)classifyProbe(302, 0));
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::Captive, (int)classifyProbe(200, 1830));  // the hotel's login page
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::Captive, (int)classifyProbe(511, 10));
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::NoInternet, (int)classifyProbe(-1, 0));
  TEST_ASSERT_EQUAL_INT((int)ProbeResult::NoInternet, (int)classifyProbe(503, 0));
  // a hotel Wi-Fi alone: SOUL stays on it (the LAN still works) and keeps checking
  Air a;
  a.book.add(net("Hotel Guest", WifiKind::Other, ""));
  a.book.add(net("phone", WifiKind::Hotspot));
  a.hits = {{"Hotel Guest", -50}};
  a.captiveSsid = "Hotel Guest";
  a.run(2);
  TEST_ASSERT_EQUAL_INT((int)NetState::Captive, (int)a.r.state());
  TEST_ASSERT_EQUAL_STRING("Hotel Guest", a.joined.c_str());
  const int p = a.probes;
  a.run(65);
  TEST_ASSERT_TRUE(a.probes - p >= 2);  // every 30 s
  // the phone's hotspot comes on: SOUL moves to it within one re-check
  a.hits.push_back({"phone", -60});
  a.run(31);
  TEST_ASSERT_EQUAL_STRING("phone", a.joined.c_str());
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)a.r.state());
  // a hotspot without mobile data: "no internet"
  Air b;
  b.book.add(net("phone", WifiKind::Hotspot));
  b.hits = {{"phone", -40}};
  b.probe = ProbeResult::NoInternet;
  b.run(2);
  TEST_ASSERT_EQUAL_INT((int)NetState::NoInternet, (int)b.r.state());
  b.probe = ProbeResult::Online;  // data back on
  b.run(31);
  TEST_ASSERT_EQUAL_INT((int)NetState::Online, (int)b.r.state());
}

static void test_wifi_ask_queue_caps_dedupes_and_drops_stale_questions() {
  AskQueue q;
  TEST_ASSERT_TRUE(q.push("one", 0));
  TEST_ASSERT_FALSE(q.push("one", 1));  // asked twice: kept once
  for (int i = 2; i <= 6; ++i) q.push("q" + std::to_string(i), (float)i);
  TEST_ASSERT_EQUAL_INT(AskQueue::kMax, q.size());
  TEST_ASSERT_EQUAL_INT(1, q.dropped());  // "one", the oldest, made room
  AskQueue::Item it;
  TEST_ASSERT_TRUE(q.pop(10, it));
  TEST_ASSERT_EQUAL_STRING("q2", it.text.c_str());
  // six hours later the rest is stale: dropped, not answered late
  TEST_ASSERT_FALSE(q.pop(AskQueue::kMaxAgeS + 100, it));
  TEST_ASSERT_EQUAL_INT(0, q.size());
}

// ---------------------------------------------------------------- SoulOS ---

namespace {
struct Dev {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  Os os{&alarms};
  TouchGestures tg;
  DisplayGeometry g = displays::kLcd28;
  bool finger = false;
  float fx = 0, fy = 0;
  Inputs in;
  NetInfo n;
  explicit Dev(bool online) {
    os.settings().booted = 1;
    os.settings().ai = (uint8_t)AiMode::Claude;
    BirthInfo b;
    b.design = 5;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = 1234;
    os.begin(g, b);
    n.configured = true;
    n.saved = 2;
    n.savedList = "home \xC2\xB7 phone";
    n.keyClaude = true;
    setOnline(online);
    tg.setMode(TouchMode::Text);
    os.setClock(1790359080u);
    in.hour = 14;
  }
  void setOnline(bool on) {
    n.connected = n.linkUp = on;
    n.ssid = on ? "phone" : "";
    n.hotspot = on;
    n.searching = !on;
    os.setNet(n);
  }
  void step(float dt = 1.0f / 30) {
    tg.update(finger, fx, fy, dt);
    TouchEv e;
    while (tg.poll(e)) os.touch(e);
    os.update(dt, brain);
    brain.update(dt, in);
  }
  void run(float s) {
    for (int i = 0; i < (int)(s * 30 + 0.5f); ++i) step();
  }
  void tap(float x, float y) {
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(0.08f);
    finger = false;
    run(0.5f);
  }
  void type(const char* text) {
    const char* p = text;
    while (*p) {
      const uint32_t cp = utf8::next(p);
      float x, y;
      if (!os.keyboard().keyCenter(cp, x, y)) continue;
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

static void test_os_offline_questions_wait_and_go_when_back_online() {
  Dev d(false);
  d.os.ask("why is the sky blue?");
  AiJob job;
  TEST_ASSERT_FALSE(d.os.popAiJob(job));
  TEST_ASSERT_EQUAL_INT(1, d.os.queuedAsks());
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)d.os.lastError());  // kept, not an error
  TEST_ASSERT_NOT_NULL(strstr(d.os.lastReply().say.c_str(), "back online (1 waiting)"));
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::WifiKick));  // search fast: the hotspot may be on
  // the offline rules still act at once, nothing queued for them
  d.os.ask("wake me at 7");
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  TEST_ASSERT_EQUAL_INT(1, d.os.queuedAsks());
  // the cap: 5, the oldest goes
  for (int i = 0; i < 6; ++i) d.os.ask("question " + std::to_string(i));
  TEST_ASSERT_EQUAL_INT(AskQueue::kMax, d.os.queuedAsks());
  d.os.home();
  d.run(1);
  // back online: after 3 s, one at a time
  d.setOnline(true);
  d.run(2);
  TEST_ASSERT_FALSE(d.os.popAiJob(job));
  d.run(1.5f);
  TEST_ASSERT_TRUE(d.os.popAiJob(job));
  TEST_ASSERT_EQUAL_STRING("question 1", job.text.c_str());
  TEST_ASSERT_TRUE(d.os.thinking());
  TEST_ASSERT_EQUAL_INT(4, d.os.queuedAsks());
  TEST_ASSERT_FALSE(d.os.popAiJob(job));  // never two in flight
  // the link drops during the turn: the question goes back in the queue
  AiOutcome lost;
  lost.err = AiErr::Network;
  d.os.aiResult(lost);
  TEST_ASSERT_EQUAL_INT(5, d.os.queuedAsks());
  // answered: the next one follows once the answer has been read for a moment
  d.run(4);
  TEST_ASSERT_TRUE(d.os.popAiJob(job));
  AiOutcome ok;
  ok.reply.say = "Pasta.";
  ok.raw = ok.reply.say;
  d.os.aiResult(ok);
  TEST_ASSERT_EQUAL_STRING("Pasta.", d.os.lastReply().say.c_str());
  TEST_ASSERT_EQUAL_INT(4, d.os.queuedAsks());
  d.run(1);
  TEST_ASSERT_FALSE(d.os.popAiJob(job));
  d.run(3);
  TEST_ASSERT_TRUE(d.os.popAiJob(job));
  // a captive portal is "offline" for questions, and says what to do
  Dev h(false);
  h.n.linkUp = true;
  h.n.captive = true;
  h.n.ssid = "Hotel Guest";
  h.os.setNet(h.n);
  h.os.ask("tell me a story");
  TEST_ASSERT_FALSE(h.os.popAiJob(job));
  TEST_ASSERT_NOT_NULL(strstr(h.os.lastReply().say.c_str(), "login page"));
  TEST_ASSERT_NOT_NULL(strstr(h.os.lastReply().say.c_str(), "hotspot"));
}

static void test_os_eyes_show_a_tiny_offline_mood() {
  Dev d(false);
  d.run(5);
  TEST_ASSERT_NOT_EQUAL((int)FaceState::Offline, (int)d.os.faceInputs(d.brain).state);  // a short drop: nothing
  d.run(20);
  TEST_ASSERT_EQUAL_INT((int)FaceState::Offline, (int)d.os.faceInputs(d.brain).state);
  bool glanced = false;
  for (int i = 0; i < 30 * 10; ++i) {
    d.step();
    glanced = glanced || d.os.faceInputs(d.brain).look;
  }
  TEST_ASSERT_TRUE(glanced);  // now and then the eyes look around for a signal
  d.setOnline(true);
  d.run(0.5f);
  TEST_ASSERT_NOT_EQUAL((int)FaceState::Offline, (int)d.os.faceInputs(d.brain).state);
  // No AI needs no internet: no offline mood
  Dev n(false);
  n.os.settings().ai = (uint8_t)AiMode::None;
  n.run(30);
  TEST_ASSERT_NOT_EQUAL((int)FaceState::Offline, (int)n.os.faceInputs(n.brain).state);
}

static void test_os_adds_the_phone_hotspot_typed_on_soul() {
  Dev d(false);
  d.os.go(View::Wifi);
  d.run(0.4f);
  d.tap(233, 270);  // "Add my phone's hotspot": the how-to
  d.run(0.3f);
  d.tap(233, 336);  // "Type it on SOUL"
  TEST_ASSERT_EQUAL_INT((int)View::Keyboard, (int)d.os.view());
  d.type("anaphone");  // typed exactly: no auto-capital on a network name
  TEST_ASSERT_EQUAL_INT((int)View::Keyboard, (int)d.os.view());  // now the password
  d.type("short");     // too short for WPA2: asked again
  TEST_ASSERT_EQUAL_INT((int)View::Keyboard, (int)d.os.view());
  TEST_ASSERT_FALSE(d.hasCmd(OsCmd::AddWifi));
  d.type("secretpass");
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::AddWifi));
  TEST_ASSERT_EQUAL_STRING("anaphone", d.os.pendingWifi().ssid.c_str());
  TEST_ASSERT_EQUAL_STRING("secretpass", d.os.pendingWifi().pass.c_str());
  TEST_ASSERT_EQUAL_INT((int)WifiKind::Hotspot, (int)d.os.pendingWifi().kind);
  TEST_ASSERT_EQUAL_INT((int)View::Wifi, (int)d.os.view());
  d.os.clearPendingWifi();
  TEST_ASSERT_TRUE(d.os.pendingWifi().pass.empty());
  // picking SOUL up while offline searches fast
  d.os.motion(Ev::PickUp);
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::WifiKick));
}

static void test_os_wifi_screens_render_every_state() {
  Dev d(false);
  std::vector<uint16_t> fb(480 * 480);
  Canvas cv(480, 480, fb.data());
  d.os.go(View::Wifi);
  d.run(0.4f);
  const char* const states[] = {"searching", "captive", "nointernet", "online", "badpass"};
  for (const char* st : states) {
    d.n = NetInfo();
    d.n.configured = true;
    d.n.saved = 2;
    d.n.savedList = "home \xC2\xB7 phone";
    if (!strcmp(st, "captive")) d.n.linkUp = d.n.captive = true;
    if (!strcmp(st, "nointernet")) d.n.linkUp = d.n.noInternet = d.n.hotspot = true;
    if (!strcmp(st, "online")) d.n.linkUp = d.n.connected = true;
    if (!strcmp(st, "badpass")) {
      d.n.wifiFail = 2;
      d.n.failSsid = "home";
    }
    d.os.setNet(d.n);
    d.os.render(cv);
    d.os.takeDirty();
  }
  d.tap(233, 270);
  d.os.render(cv);  // the hotspot how-to
  d.os.back();
  TEST_ASSERT_EQUAL_INT((int)View::Wifi, (int)d.os.view());  // back = the Wi-Fi page first
  d.os.back();
  TEST_ASSERT_EQUAL_INT((int)View::Settings, (int)d.os.view());
}

void runWifiTests() {
  RUN_TEST(test_wifi_book_adds_updates_and_survives_a_roundtrip);
  RUN_TEST(test_wifi_iphone_names_match_without_the_curly_apostrophe);
  RUN_TEST(test_wifi_roamer_picks_by_priority_then_signal);
  RUN_TEST(test_wifi_hotspot_is_joined_within_seconds_when_it_appears);
  RUN_TEST(test_wifi_roams_home_from_the_hotspot_and_away_from_a_weak_network);
  RUN_TEST(test_wifi_wrong_password_backs_off_and_tries_the_next);
  RUN_TEST(test_wifi_captive_portal_is_told_apart_and_left_for_a_better_network);
  RUN_TEST(test_wifi_ask_queue_caps_dedupes_and_drops_stale_questions);
  RUN_TEST(test_os_offline_questions_wait_and_go_when_back_online);
  RUN_TEST(test_os_eyes_show_a_tiny_offline_mood);
  RUN_TEST(test_os_adds_the_phone_hotspot_typed_on_soul);
  RUN_TEST(test_os_wifi_screens_render_every_state);
}
