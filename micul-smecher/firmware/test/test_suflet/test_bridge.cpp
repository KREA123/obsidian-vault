// SOUL Bridge (docs/08-OWN-CLAUDE.md §4) on the device: the LAN server (BridgeServer) and the cloud transport
// (bridge.code / bridge.state / ask.state in CloudSession); and the long-poll transport of SOUL Cloud (§6.4
// fallback) plus the deep-sleep wake-polls (§6.11), with a scripted fake cloud behind a CloudDriver.
#include <ArduinoJson.h>
#include <unity.h>

#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "BridgeLink.h"
#include "CloudLink.h"
#include "CloudSession.h"
#include "DeviceKey.h"

using namespace suflet;

namespace {

JsonDocument parse(const std::string& s) {
  JsonDocument d;
  TEST_ASSERT_FALSE_MESSAGE(deserializeJson(d, s), s.c_str());
  return d;
}

std::vector<BridgeOut> outs(BridgeServer& b) {
  std::vector<BridgeOut> v;
  BridgeOut o;
  while (b.nextOut(o)) v.push_back(o);
  return v;
}

void text(BridgeServer& b, int conn, const std::string& s, uint32_t now) { b.onText(conn, s.data(), s.size(), now); }

const char* kWelcome =
    "{\"v\":1,\"t\":\"welcome\",\"server_time\":1790980000,\"tz\":\"Europe/Bucharest\",\"posix_tz\":\"EET-2EEST,M3.5.0/3,"
    "M10.5.0/4\",\"state\":\"paired\",\"owner\":\"Ana\",\"brain\":\"none\",\"voice\":\"claude\",\"lang\":\"en\","
    "\"connectors_paused\":false,\"limits\":{\"frames_per_s\":2},\"allowance\":null,\"trial\":null,\"models\":{}}";

std::vector<std::string> drain(CloudSession& s, uint32_t now) {
  std::vector<std::string> v;
  std::string f;
  s.tick(now);
  while (s.nextFrame(f, now)) v.push_back(f);
  return v;
}

int count(const std::vector<std::string>& v, const char* type) {
  int n = 0;
  const std::string needle = std::string("\"t\":\"") + type + "\"";
  for (const std::string& f : v) n += f.find(needle) != std::string::npos;
  return n;
}

}  // namespace

// ------------------------------------------------------------ the LAN server ---

static void test_bridge_lan_pairing_hello_and_tokens() {
  BridgeServer b;
  b.deviceId = "soul-a1b2c3d4e5f6";
  b.name = "Miso";
  b.tz = "EET-2EEST";
  // no code on the screen: a pair attempt is refused
  b.onOpen(1, 0);
  text(b, 1, "{\"t\":\"bridge.pair\",\"v\":1,\"code\":\"123456\"}", 10);
  std::vector<BridgeOut> o = outs(b);
  TEST_ASSERT_EQUAL_STRING("bridge.denied", parse(o[0].frame)["t"]);
  TEST_ASSERT_TRUE(o[1].close);
  b.onClose(1);
  const std::string code = b.newCode(1000);
  TEST_ASSERT_EQUAL_INT(6, (int)code.size());
  TEST_ASSERT_EQUAL_STRING(code.c_str(), b.code(1000).c_str());
  // four wrong tries leave the code alive; the fifth kills it
  for (int i = 0; i < 4; ++i) {
    b.onOpen(2, 1100);
    text(b, 2, "{\"t\":\"bridge.pair\",\"code\":\"000000x\"}", 1100);
    outs(b);
    b.onClose(2);
  }
  TEST_ASSERT_EQUAL_STRING(code.c_str(), b.code(1200).c_str());
  b.onOpen(3, 1300);
  text(b, 3, "{\"t\":\"bridge.pair\",\"v\":1,\"code\":\"" + code + "\",\"bridge\":\"soul-bridge/0.2.0\"}", 1300);
  o = outs(b);
  JsonDocument p = parse(o[0].frame);
  TEST_ASSERT_EQUAL_STRING("bridge.paired", p["t"]);
  const std::string token = p["token"].as<std::string>();
  TEST_ASSERT_TRUE(token.rfind("sbt_", 0) == 0 && token.size() == 47);
  TEST_ASSERT_EQUAL_STRING("soul-a1b2c3d4e5f6", p["device_id"]);
  TEST_ASSERT_TRUE(o[1].close);
  TEST_ASSERT_TRUE(b.code(1400).empty());  // single use
  b.onClose(3);
  // only the hash is kept, and it survives a restart
  TEST_ASSERT_TRUE(b.tokensDirty);
  const std::string saved = b.saveTokens();
  TEST_ASSERT_TRUE(saved.find(token) == std::string::npos);
  TEST_ASSERT_TRUE(saved.find(DeviceKey::sha256Hex(token)) != std::string::npos);
  BridgeServer b2;
  b2.deviceId = b.deviceId;
  b2.loadTokens(saved);
  TEST_ASSERT_EQUAL_INT(1, (int)b2.tokenCount());
  // hello: a wrong token is denied, the right one welcomed
  b2.onOpen(4, 0);
  text(b2, 4, "{\"t\":\"bridge.hello\",\"token\":\"sbt_nope\"}", 0);
  o = outs(b2);
  TEST_ASSERT_EQUAL_STRING("bridge.denied", parse(o[0].frame)["t"]);
  b2.onClose(4);
  b2.onOpen(5, 0);
  text(b2, 5, "{\"t\":\"bridge.hello\",\"v\":1,\"token\":\"" + token + "\",\"bridge\":\"soul-bridge/0.2.0\",\"label\":\"anas-mac\"}", 0);
  o = outs(b2);
  TEST_ASSERT_EQUAL_STRING("bridge.welcome", parse(o[0].frame)["t"]);
  TEST_ASSERT_TRUE(b2.online());
  TEST_ASSERT_EQUAL_STRING("anas-mac", b2.computer().c_str());
  // a second bridge with the same token takes over; the first is closed
  b2.onOpen(6, 10);
  text(b2, 6, "{\"t\":\"bridge.hello\",\"token\":\"" + token + "\"}", 10);
  o = outs(b2);
  TEST_ASSERT_TRUE(o[0].close && o[0].conn == 5);
  b2.onClose(5);
  TEST_ASSERT_TRUE(b2.online());
  // a connection that says nothing for 10 s is closed; forget closes the bridge and kills its token
  b2.onOpen(7, 100);
  b2.tick(10200);
  o = outs(b2);
  TEST_ASSERT_TRUE(o.size() == 1 && o[0].conn == 7 && o[0].close);
  b2.forget();
  o = outs(b2);
  TEST_ASSERT_EQUAL_STRING("bridge.denied", parse(o[0].frame)["t"]);
  TEST_ASSERT_EQUAL_INT(0, (int)b2.tokenCount());
}

static BridgeServer* connected(BridgeServer& b, int conn) {
  b.deviceId = "soul-a1b2c3d4e5f6";
  b.tz = "EET-2EEST";
  const std::string code = b.newCode(0);
  b.onOpen(1, 0);
  text(b, 1, "{\"t\":\"bridge.pair\",\"code\":\"" + code + "\"}", 0);
  const std::string token = parse(outs(b)[0].frame)["token"].as<std::string>();
  b.onClose(1);
  b.onOpen(conn, 0);
  text(b, conn, "{\"t\":\"bridge.hello\",\"token\":\"" + token + "\"}", 0);
  outs(b);
  return &b;
}

static void test_bridge_lan_turns_answers_errors_and_timeouts() {
  BridgeServer b;
  connected(b, 2);
  TEST_ASSERT_TRUE(b.ask("Trezește-mă mâine la 7", true, "2026-10-03T18:02", 1000));
  TEST_ASSERT_FALSE(b.ask("again", true, "2026-10-03T18:02", 1000));  // one at a time
  JsonDocument q = parse(outs(b)[0].frame);
  TEST_ASSERT_EQUAL_STRING("ask", q["t"]);
  TEST_ASSERT_EQUAL_STRING("ro", q["lang"]);
  TEST_ASSERT_EQUAL_STRING("2026-10-03T18:02", q["now"]);
  const std::string id = q["id"].as<std::string>();
  TEST_ASSERT_EQUAL_INT(1, b.askState());
  text(b, 2, "{\"t\":\"ask.ack\",\"id\":\"" + id + "\",\"state\":\"thinking\"}", 1500);
  TEST_ASSERT_EQUAL_INT(2, b.askState());
  text(b, 2, "{\"t\":\"answer\",\"id\":\"other\",\"text\":\"x\",\"actions\":[]}", 1600);  // not ours: ignored
  AiOutcome out;
  TEST_ASSERT_FALSE(b.pollAnswer(out));
  text(b, 2,
       "{\"t\":\"answer\",\"id\":\"" + id + "\",\"text\":\"Gata, la 07:00.\",\"actions\":["
       "{\"type\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":[],\"label\":\"\"}},"
       "{\"type\":\"list.add\",\"args\":{\"list\":\"shopping\",\"items\":[\"milk\",\"eggs\"]}},"
       "{\"type\":\"answer.show\",\"args\":{\"say\":\"\",\"title\":\"T\",\"body\":\"Take an umbrella\"}},"
       "{\"type\":\"alarm.set\",\"args\":{\"hhmm\":\"25:99\"}}]}",
       2000);
  JsonDocument ack = parse(outs(b)[0].frame);
  TEST_ASSERT_EQUAL_STRING("answer.ack", ack["t"]);
  TEST_ASSERT_TRUE(b.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)out.err);
  TEST_ASSERT_EQUAL_STRING("Gata, la 07:00.\nTake an umbrella", out.reply.say.c_str());
  TEST_ASSERT_EQUAL_INT(2, (int)out.reply.actions.size());
  TEST_ASSERT_EQUAL_INT((int)AiAction::AlarmSet, (int)out.reply.actions[0].type);
  TEST_ASSERT_EQUAL_INT(7, out.reply.actions[0].hour);
  TEST_ASSERT_EQUAL_INT((int)AiAction::NoteCreate, (int)out.reply.actions[1].type);
  TEST_ASSERT_EQUAL_STRING("shopping: milk eggs", out.reply.actions[1].text.c_str());
  TEST_ASSERT_EQUAL_INT(1, out.reply.rejected);
  // Claude Code not running on the computer
  b.ask("hi", false, "2026-10-03T18:05", 3000);
  std::string id2 = parse(outs(b)[0].frame)["id"].as<std::string>();
  text(b, 2, "{\"t\":\"answer.error\",\"id\":\"" + id2 + "\",\"code\":\"claude_unavailable\"}", 3100);
  TEST_ASSERT_TRUE(b.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::BridgeOffline, (int)out.err);
  // no answer in 125 s: cancelled on the computer, Timeout on SOUL
  b.ask("slow", false, "2026-10-03T18:06", 4000);
  id2 = parse(outs(b)[0].frame)["id"].as<std::string>();
  b.tick(4000 + 126000);
  JsonDocument cancel = parse(outs(b)[0].frame);
  TEST_ASSERT_EQUAL_STRING("ask.cancel", cancel["t"]);
  TEST_ASSERT_EQUAL_STRING(id2.c_str(), cancel["id"]);
  TEST_ASSERT_TRUE(b.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Timeout, (int)out.err);
  // the computer goes away mid-turn
  b.ask("bye", false, "2026-10-03T18:09", 200000);
  outs(b);
  b.onClose(2);
  TEST_ASSERT_FALSE(b.online());
  TEST_ASSERT_TRUE(b.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::BridgeOffline, (int)out.err);
  TEST_ASSERT_FALSE(b.ask("nobody", false, "", 200100));
}

// ------------------------------------------------ the cloud transport (doc 08) ---

static void test_bridge_cloud_frames_and_session() {
  TEST_ASSERT_EQUAL_STRING("bridge.code.get", parse(CloudLink::bridgeCodeGet())["t"]);
  TEST_ASSERT_EQUAL_STRING("bridge.forget", parse(CloudLink::bridgeForget())["t"]);
  TEST_ASSERT_EQUAL_STRING("bridge", parse(CloudLink::brain("bridge"))["brain"]);
  CloudLink l;
  const char* bad = "{\"v\":1,\"t\":\"bridge.code\",\"code\":\"7kq3\",\"expires_in\":300}";
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)l.feed(bad, strlen(bad)));
  const char* st = "{\"v\":1,\"t\":\"ask.state\",\"re\":\"a1\",\"state\":\"dancing\"}";
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)l.feed(st, strlen(st)));

  CloudSession s;
  s.onOpen(0);
  s.onText(kWelcome, strlen(kWelcome), 0);
  drain(s, 0);
  // the owner picks "My Claude on my computer" on SOUL: the brain and a code go up
  CloudOut o;
  o.kind = CloudOut::Brain;
  o.text = "bridge";
  s.send(o, 0, 0);
  o.kind = CloudOut::BridgeCode;
  s.send(o, 0, 0);
  std::vector<std::string> up = drain(s, 1000);
  TEST_ASSERT_EQUAL_INT(1, count(up, "brain"));
  TEST_ASSERT_EQUAL_INT(1, count(up, "bridge.code.get"));
  const char* code = "{\"v\":1,\"t\":\"bridge.code\",\"code\":\"7KQ3M9XD\",\"expires_in\":300,"
                     "\"cmd\":\"soul-bridge pair 7KQ3-M9XD --cloud soul.example\"}";
  s.onText(code, strlen(code), 2000);
  NetInfo n;
  n.paired = true;
  s.fill(n);
  TEST_ASSERT_EQUAL_STRING("7KQ3M9XD", n.bridgeCode.c_str());
  TEST_ASSERT_EQUAL_STRING("soul-bridge pair 7KQ3-M9XD --cloud soul.example", n.bridgeCmd.c_str());
  const char* on = "{\"v\":1,\"t\":\"bridge.state\",\"paired\":true,\"online\":true,\"name\":\"Ana's Mac\"}";
  s.onText(on, strlen(on), 3000);
  n = NetInfo();
  n.paired = true;
  s.fill(n);
  TEST_ASSERT_TRUE(n.bridgeOnline && n.bridgePaired);
  TEST_ASSERT_EQUAL_STRING("Ana's Mac", n.bridgeName.c_str());
  TEST_ASSERT_TRUE(n.bridgeCode.empty());  // taken: gone from the screen
  // a reconnect: the account still says "none", the choice made on SOUL is sent again and not undone
  s.onClose(1006, 4000, 0);
  s.onOpen(5000);
  s.onText(kWelcome, strlen(kWelcome), 5000);
  CloudConfig cc;
  TEST_ASSERT_TRUE(s.pollConfig(cc));
  TEST_ASSERT_FALSE(cc.hasBrain);
  TEST_ASSERT_EQUAL_INT(1, count(drain(s, 6000), "brain"));
  // a turn through the computer: waiting -> thinking -> reply
  TEST_ASSERT_TRUE(s.ask("plan my day", false, -1, 10000, true));
  up = drain(s, 10000);
  const std::string id = parse(up.back())["id"].as<std::string>();
  TEST_ASSERT_EQUAL_INT(1, s.askState());
  std::string f = "{\"v\":1,\"t\":\"ask.state\",\"re\":\"" + id + "\",\"state\":\"thinking\"}";
  s.onText(f.data(), f.size(), 11000);
  TEST_ASSERT_EQUAL_INT(2, s.askState());
  n = NetInfo();
  s.fill(n);
  TEST_ASSERT_EQUAL_INT(2, n.askState);
  s.tick(60000);  // a bridge turn is not given up after 25 s
  AiOutcome out;
  TEST_ASSERT_FALSE(s.pollAnswer(out));
  f = "{\"v\":1,\"t\":\"reply\",\"re\":\"" + id + "\",\"say\":\"Busy day.\",\"provider\":\"claude\",\"brain\":\"bridge\",\"seqs\":[]}";
  s.onText(f.data(), f.size(), 70000);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_STRING("Busy day.", out.reply.say.c_str());
  TEST_ASSERT_EQUAL_INT(0, s.askState());
  // the computer is off: bridge_offline, and the offline rules may answer (noLocal false)
  s.ask("hi", false, -1, 80000, true);
  std::string id2 = parse(drain(s, 80000).back())["id"].as<std::string>();
  f = "{\"v\":1,\"t\":\"error\",\"re\":\"" + id2 + "\",\"code\":\"bridge_offline\",\"msg\":\"offline\"}";
  s.onText(f.data(), f.size(), 80100);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::BridgeOffline, (int)out.err);
  TEST_ASSERT_FALSE(out.noLocal);
  // the cloud's 120 s are up (timeout): a bridge turn did nothing, so the rules may answer
  s.ask("slow", false, -1, 90000, true);
  id2 = parse(drain(s, 90000).back())["id"].as<std::string>();
  f = "{\"v\":1,\"t\":\"error\",\"re\":\"" + id2 + "\",\"code\":\"timeout\"}";
  s.onText(f.data(), f.size(), 210000);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_FALSE(out.noLocal);
  // and SOUL's own 125 s: abort
  s.ask("slower", false, -1, 300000, true);
  drain(s, 300000);
  up = drain(s, 300000 + 126000);
  TEST_ASSERT_EQUAL_INT(1, count(up, "abort"));
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Timeout, (int)out.err);
  TEST_ASSERT_FALSE(out.noLocal);
  // forget: goes up, and the screen forgets at once
  o.kind = CloudOut::BridgeForget;
  s.send(o, 0, 0);
  TEST_ASSERT_EQUAL_INT(1, count(drain(s, 500000), "bridge.forget"));
  TEST_ASSERT_FALSE(s.bridgeOnline || s.bridgePaired);
}

// ----------------------------------------------- long-poll and wake-polls (§6.4, §6.11) ---

namespace {

// A scripted SOUL Cloud behind the CloudDriver transport: auth always works, the socket never opens, and
// /v1/device/poll + /v1/device/send answer from queues the test fills.
struct FakeCloud : CloudDriver {
  int wsTries = 0, auths = 0;
  bool poll = true;
  std::vector<std::string> gets, posts;      // URLs / bodies seen
  std::vector<std::string> pollReplies;      // bodies for the next polls ("" = {"messages":[]})
  std::vector<int> pollStatus;               // statuses for the next polls (200 if empty)
  std::map<std::string, std::string> onSend; // a frame type in the send -> extra messages answered

  FakeCloud() {
    base = "https://soul.example";
    deviceId = "soul-a1b2c3d4e5f6";
    fw = "1.3.0";
    hw = "lcd28";
  }
  int httpPost(const std::string& url, const std::string& body, std::string& resp, int& retryAfterS) override {
    (void)body;
    retryAfterS = -1;
    if (url.find("/challenge") != std::string::npos) {
      resp = "{\"nonce\":\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\",\"expires_in\":60}";
      return 200;
    }
    ++auths;
    resp = "{\"token\":\"sdt_0123456789abcdefghijklmnop\",\"expires_in\":86400,\"ws_url\":\"wss://soul.example/v1/device/ws\","
           "\"server_time\":1790980000,\"state\":\"paired\",\"owner\":\"Ana\",\"trial\":null}";
    return 200;
  }
  int wsOpen(const std::string&, const std::string&) override {
    ++wsTries;
    return -1;  // a proxy that drops upgrades
  }
  bool wsSend(const std::string&) override { return false; }
  Rd wsRead(std::string&, int& code, uint32_t) override {
    code = 1006;
    return Rd::Closed;
  }
  void wsClose() override {}
  bool keyReady() override { return true; }
  std::string pubB64() override { return std::string(87, 'A'); }
  std::string signB64(const std::string&) override { return std::string(86, 'B'); }
  bool supportsPoll() override { return poll; }
  int httpGetAuth(const std::string& url, const std::string& bearer, std::string& resp, uint32_t) override {
    TEST_ASSERT_TRUE(bearer == "Bearer sdt_0123456789abcdefghijklmnop");
    TEST_ASSERT_TRUE(url.find("sdt_") == std::string::npos);  // the token never travels in a URL
    gets.push_back(url);
    int st = 200;
    if (!pollStatus.empty()) {
      st = pollStatus.front();
      pollStatus.erase(pollStatus.begin());
    }
    if (!pollReplies.empty()) {
      resp = pollReplies.front();
      pollReplies.erase(pollReplies.begin());
    } else {
      resp = "{\"messages\":[],\"more\":false}";
    }
    return st;
  }
  int httpPostAuth(const std::string& url, const std::string&, const std::string& body, std::string& resp,
                   uint32_t) override {
    TEST_ASSERT_TRUE(url == "https://soul.example/v1/device/send");
    posts.push_back(body);
    std::string msgs;
    for (const auto& kv : onSend)
      if (body.find("\"t\":\"" + kv.first + "\"") != std::string::npos) msgs += (msgs.empty() ? "" : ",") + kv.second;
    resp = "{\"messages\":[" + msgs + "]}";
    return 200;
  }
};

const char* kPush4 = "{\"v\":1,\"t\":\"push\",\"seq\":4,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":[],"
                     "\"label\":\"\"},\"item_id\":\"it_4\",\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"}}";
const char* kPush5 = "{\"v\":1,\"t\":\"push\",\"seq\":5,\"action\":\"note.create\",\"args\":{\"text\":\"milk\",\"tags\":[]},"
                     "\"item_id\":\"it_5\",\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"}}";

}  // namespace

static void test_cloud_long_poll_fallback_when_the_socket_will_not_open() {
  TEST_ASSERT_EQUAL_STRING("https://soul.example/v1/device/poll?after=7&wait=25",
                           CloudLink::pollUrl("https://soul.example/", 7, 60).c_str());
  std::vector<std::string> fr;
  bool more = false;
  const char* body = "{\"messages\":[{\"v\":1,\"t\":\"resync\",\"last\":3},7,{\"v\":1,\"t\":\"x\"}],\"more\":true}";
  TEST_ASSERT_TRUE(CloudLink::splitMessages(body, strlen(body), fr, &more));
  TEST_ASSERT_EQUAL_INT(2, (int)fr.size());
  TEST_ASSERT_TRUE(more);
  size_t used = 0;
  const std::string sb = CloudLink::sendBody(std::vector<std::string>(25, "{\"v\":1,\"t\":\"ack\",\"seq\":1,\"ok\":true}"), &used);
  TEST_ASSERT_EQUAL_INT(20, (int)used);  // <= 20 a send
  TEST_ASSERT_EQUAL_INT(20, (int)parse(sb)["messages"].size());

  FakeCloud c;
  c.onSend["hello"] = kWelcome;
  uint32_t t = 0;
  for (int i = 0; i < 400 && !c.pollMode(); ++i) {
    c.step(t, 0);
    t += 5000;
  }
  TEST_ASSERT_TRUE(c.pollMode());
  TEST_ASSERT_EQUAL_INT(3, c.wsTries);
  // the first send carries hello, its answer the welcome; then a poll brings a push
  c.pollReplies.push_back(std::string("{\"messages\":[") + kPush4 + "],\"more\":false}");
  c.step(t, 0);
  TEST_ASSERT_TRUE(c.posts[0].find("\"t\":\"hello\"") != std::string::npos);
  TEST_ASSERT_TRUE(c.session.welcomed());
  TEST_ASSERT_EQUAL_STRING("https://soul.example/v1/device/poll?after=0&wait=8", c.gets.back().c_str());
  CloudPush p;
  TEST_ASSERT_TRUE(c.session.pollPush(p));
  TEST_ASSERT_EQUAL_UINT32(4u, p.seq);
  c.session.ackPush(4, true, nullptr);
  // the ack goes up with the next send; a turn's reply comes back on the send that carried the ask
  TEST_ASSERT_TRUE(c.session.ask("hi", false, -1, t));
  c.onSend["ask"] = "{\"v\":1,\"t\":\"reply\",\"re\":\"" + std::string("?") + "\",\"say\":\"x\"}";
  t += 100;
  c.step(t, 0);
  const std::string& sent = c.posts.back();
  TEST_ASSERT_TRUE(sent.find("\"t\":\"ack\"") != std::string::npos && sent.find("\"seq\":4") != std::string::npos);
  TEST_ASSERT_TRUE(sent.find("\"t\":\"ask\"") != std::string::npos);
  TEST_ASSERT_TRUE(c.gets.back().find("after=4") != std::string::npos);
  // the token dies: sign in again, then carry on
  const int authsBefore = c.auths;
  c.pollStatus.push_back(401);
  c.step(t += 100, 0);
  for (int i = 0; i < 20 && c.auths == authsBefore; ++i) c.step(t += 1000, 0);
  TEST_ASSERT_EQUAL_INT(authsBefore + 1, c.auths);
  // after 10 minutes the socket is tried again
  for (int i = 0; i < 200 && c.pollMode(); ++i) c.step(t += 10000, 0);
  TEST_ASSERT_FALSE(c.pollMode());
  // without long-poll support the driver keeps retrying the socket
  FakeCloud ws;
  ws.poll = false;
  for (uint32_t u = 0; u < 3600000; u += 5000) ws.step(u, 0);
  TEST_ASSERT_FALSE(ws.pollMode());
  TEST_ASSERT_TRUE(ws.wsTries > 3);
}

static void test_cloud_wake_poll_from_deep_sleep() {
  FakeCloud c;
  c.session.lastSeq = 3;
  CloudOut note;  // made on SOUL before it slept: goes up with the acks
  note.kind = CloudOut::Item;
  note.act.type = AiAction::NoteCreate;
  note.act.text = "from the night";
  c.session.send(note, 1790000000, 1790000000);
  c.pollReplies.push_back(std::string("{\"messages\":[") + kPush4 + "],\"more\":true}");
  c.pollReplies.push_back(std::string("{\"messages\":[") + kPush5 + "],\"more\":false}");
  TEST_ASSERT_TRUE(c.wakePoll(0, 0));
  TEST_ASSERT_EQUAL_INT(1, c.auths);  // the token lived in RAM only: a fresh sign-in
  TEST_ASSERT_EQUAL_INT(2, (int)c.gets.size());
  TEST_ASSERT_EQUAL_STRING("https://soul.example/v1/device/poll?after=3&wait=0", c.gets[0].c_str());
  TEST_ASSERT_EQUAL_STRING("https://soul.example/v1/device/poll?after=4&wait=0", c.gets[1].c_str());  // the next page
  TEST_ASSERT_TRUE(c.session.wakePolling());
  CloudPush p;
  int n = 0;
  while (c.session.pollPush(p)) {
    c.session.ackPush(p.seq, true, nullptr);
    ++n;
  }
  TEST_ASSERT_EQUAL_INT(2, n);
  TEST_ASSERT_TRUE(c.wakePollFinish(100, 1790000900));
  TEST_ASSERT_EQUAL_INT(1, (int)c.posts.size());
  JsonDocument d = parse(c.posts[0]);
  std::string types;
  for (JsonVariantConst m : d["messages"].as<JsonArrayConst>()) types += std::string(m["t"] | "") + " ";
  TEST_ASSERT_EQUAL_STRING("ack ack sleep item.add ", types.c_str());  // no hello in a wake-poll
  TEST_ASSERT_EQUAL_UINT32(1790000900u, d["messages"][2]["wake_at"].as<uint32_t>());
  TEST_ASSERT_EQUAL_UINT32(5u, c.session.lastSeq);
  TEST_ASSERT_FALSE(c.session.wakePolling());
  TEST_ASSERT_EQUAL_INT(0, c.wsTries);  // the socket is never opened in a wake-poll
}

void runBridgeTests() {
  RUN_TEST(test_bridge_lan_pairing_hello_and_tokens);
  RUN_TEST(test_bridge_lan_turns_answers_errors_and_timeouts);
  RUN_TEST(test_bridge_cloud_frames_and_session);
  RUN_TEST(test_cloud_long_poll_fallback_when_the_socket_will_not_open);
  RUN_TEST(test_cloud_wake_poll_from_deep_sleep);
}
