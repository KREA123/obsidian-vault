// SOUL Cloud protocol v1, device side (docs/07-CONNECT-AI.md §6, rev. 2):
// the device key against the cloud's test vector, frames out, frames in,
// the push -> action mapping, the session (dedupe, acks, outq, pairing,
// time zone, close codes, frame budget) and a replay of frames recorded
// from the running cloud (cloud_frames.h, made by ai/tools/record_frames.py).
#include <ArduinoJson.h>
#include <unity.h>

#include <cstring>
#include <string>

#include "CloudLink.h"
#include "CloudSession.h"
#include "DeviceKey.h"
#include "cloud_frames.h"

using namespace suflet;

static CloudLink::Msg feed(CloudLink& c, const char* s) { return c.feed(s, strlen(s)); }
static CloudLink::Msg feed(CloudSession& s, const char* f, uint32_t now = 1000) { return s.onText(f, strlen(f), now); }

static JsonDocument parse(const std::string& s) {
  JsonDocument d;
  TEST_ASSERT_FALSE(deserializeJson(d, s));
  return d;
}

static std::vector<uint8_t> unhex(const char* h) {
  std::vector<uint8_t> v;
  for (size_t i = 0; h[i] && h[i + 1]; i += 2) {
    char b[3] = {h[i], h[i + 1], 0};
    v.push_back((uint8_t)strtoul(b, nullptr, 16));
  }
  return v;
}

// ai/tests/vectors/device_auth.json (TEST KEY ONLY: the private scalar is public)
static const char* kVecPriv = "4e068ae165a9aa91f41560ed9d5a5943e376f1239fb1ca776c7a915cfc38dafd";
static const char* kVecPub = "BD7vEwPfrnUCzqtw8_0wtw21_xPeEKP8p4ngjvBonfNW2XnGuPlDig3hF_Y4nPVAqNLc--ZN4lktLFu7yaQKLM4";
static const char* kVecNonce = "q2X0nJ8Wf3n2v2nOQhV1C0xg5Hkq1oS6c2zq0iYq3pA";
static const char* kVecMsgHex =
    "736f756c2d617574682d76310a736f756c2e6578616d706c650a736f756c2d6131623263336434653566360a713258306e4a385766336e3276"
    "326e4f516856314330786735486b71316f533663327a7130695971337041";
static const char* kVecSig = "W5-qH6aDbOBzo6HaL4250RV_rvQ70GyVs_t5rt3T0F87DwjlGWtDOkQ0JhvwyoK1QKcIOBHIVjbbqtb9sCj8ig";
static const char* kVecSigOtherHost =
    "pdJx2Vhjy9bHH0WR_V8a7eqUP81w3mldEkqfCIRfbxUc_xIlOcN7RAeDDMSlwi5S3YyKy4NaO7QanMpy0IaEQg";

static void test_cloud_device_key_matches_the_cloud_vector() {
  const uint8_t mac[6] = {0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6};
  TEST_ASSERT_EQUAL_STRING("soul-a1b2c3d4e5f6", CloudLink::deviceId(mac).c_str());
  // the exact bytes the device signs
  const std::string msg = CloudLink::authMessage(CloudLink::hostOf("https://SOUL.example:443/"), "soul-a1b2c3d4e5f6",
                                                 kVecNonce);
  const std::vector<uint8_t> want = unhex(kVecMsgHex);
  TEST_ASSERT_EQUAL_INT((int)want.size(), (int)msg.size());
  TEST_ASSERT_EQUAL_MEMORY(want.data(), msg.data(), want.size());
  TEST_ASSERT_EQUAL_STRING("127.0.0.1:8790", CloudLink::hostOf("http://127.0.0.1:8790").c_str());

  // the public key from the private scalar, b64u (87 chars)
  std::vector<uint8_t> priv = unhex(kVecPriv);
  uint8_t pub[65];
  TEST_ASSERT_TRUE(DeviceKey::publicFrom(priv.data(), pub));
  TEST_ASSERT_EQUAL_STRING(kVecPub, DeviceKey::pubB64(pub).c_str());
  TEST_ASSERT_EQUAL_INT(87, (int)DeviceKey::pubB64(pub).size());

  // the cloud's signature verifies; the one made for another host does not
  std::vector<uint8_t> sig;
  TEST_ASSERT_TRUE(CloudLink::base64urlDecode(kVecSig, sig));
  TEST_ASSERT_EQUAL_INT(64, (int)sig.size());
  TEST_ASSERT_TRUE(DeviceKey::verify(pub, (const uint8_t*)msg.data(), msg.size(), sig.data()));
  TEST_ASSERT_TRUE(CloudLink::base64urlDecode(kVecSigOtherHost, sig));
  TEST_ASSERT_FALSE(DeviceKey::verify(pub, (const uint8_t*)msg.data(), msg.size(), sig.data()));

  // our own signature: raw r||s, b64u 86 chars, verifies
  const std::string mine = DeviceKey::signB64(priv.data(), msg);
  TEST_ASSERT_EQUAL_INT(86, (int)mine.size());
  TEST_ASSERT_TRUE(CloudLink::base64urlDecode(mine, sig));
  TEST_ASSERT_TRUE(DeviceKey::verify(pub, (const uint8_t*)msg.data(), msg.size(), sig.data()));
  std::string tampered = msg;
  tampered[tampered.size() - 1] ^= 1;
  TEST_ASSERT_FALSE(DeviceKey::verify(pub, (const uint8_t*)tampered.data(), tampered.size(), sig.data()));

  // a fresh key pair works end to end
  uint8_t p2[32], q2[65];
  TEST_ASSERT_TRUE(DeviceKey::generate(p2, q2));
  TEST_ASSERT_EQUAL_HEX8(0x04, q2[0]);
  TEST_ASSERT_TRUE(CloudLink::base64urlDecode(DeviceKey::signB64(p2, "hello"), sig));
  TEST_ASSERT_TRUE(DeviceKey::verify(q2, (const uint8_t*)"hello", 5, sig.data()));
  DeviceKey::wipe(p2, sizeof p2);
  TEST_ASSERT_EQUAL_HEX8(0, p2[7]);

  // base64url: unpadded both ways, garbage refused
  const uint8_t man[3] = {'M', 'a', 'n'};
  TEST_ASSERT_EQUAL_STRING("TWFu", CloudLink::base64url(man, 3).c_str());
  TEST_ASSERT_EQUAL_STRING("TWE", CloudLink::base64url(man, 2).c_str());
  const uint8_t ff[2] = {0xFB, 0xFF};
  TEST_ASSERT_EQUAL_STRING("-_8", CloudLink::base64url(ff, 2).c_str());
  std::vector<uint8_t> back;
  TEST_ASSERT_TRUE(CloudLink::base64urlDecode("-_8", back));
  TEST_ASSERT_EQUAL_INT(2, (int)back.size());
  TEST_ASSERT_EQUAL_HEX8(0xFB, back[0]);
  TEST_ASSERT_FALSE(CloudLink::base64urlDecode("a+b/", back));
}

static void test_cloud_auth_bodies_and_answers() {
  JsonDocument ch = parse(CloudLink::challengeBody("soul-a1b2c3d4e5f6"));
  TEST_ASSERT_EQUAL_STRING("soul-a1b2c3d4e5f6", ch["device_id"]);
  JsonDocument b = parse(CloudLink::authBody("soul-a1b2c3d4e5f6", kVecPub, kVecNonce, kVecSig, "1.2.0", "lcd28", true));
  TEST_ASSERT_EQUAL_STRING(kVecPub, b["pub"]);
  TEST_ASSERT_EQUAL_STRING(kVecNonce, b["nonce"]);
  TEST_ASSERT_EQUAL_STRING(kVecSig, b["sig"]);
  TEST_ASSERT_TRUE(b["reset"].as<bool>());
  TEST_ASSERT_TRUE(b["secret"].isNull());  // rev. 1's shared secret is gone

  CloudAuth a;
  const char* nonce = "{\"nonce\":\"q2X0nJ8Wf3n2v2nOQhV1C0xg5Hkq1oS6c2zq0iYq3pA\",\"expires_in\":60}";
  TEST_ASSERT_TRUE(CloudLink::parseChallenge(200, nonce, strlen(nonce), a));
  TEST_ASSERT_EQUAL_STRING(kVecNonce, a.nonce.c_str());
  const char* rl = "{\"error\":{\"code\":\"rate_limited\",\"msg\":\"slow\",\"retry_ms\":5000}}";
  TEST_ASSERT_FALSE(CloudLink::parseChallenge(429, rl, strlen(rl), a));
  TEST_ASSERT_EQUAL_STRING("rate_limited", a.code.c_str());
  TEST_ASSERT_EQUAL_INT(5000, a.retryMs);
  const char* odd = "{\"nonce\":\"a\\\"b\"}";
  TEST_ASSERT_FALSE(CloudLink::parseChallenge(200, odd, strlen(odd), a));

  const char* ok =
      "{\"token\":\"sdt_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG\",\"expires_in\":86400,"
      "\"ws_url\":\"wss://soul.example/v1/device/ws\",\"server_time\":1790980000,\"state\":\"unpaired\",\"owner\":\"\","
      "\"trial\":{\"left\":30,\"unit\":\"turns\"},\"future_field\":[1,2,3]}";
  TEST_ASSERT_TRUE(CloudLink::parseAuth(200, ok, strlen(ok), a));
  TEST_ASSERT_EQUAL_STRING("wss://soul.example/v1/device/ws", a.wsUrl.c_str());
  TEST_ASSERT_EQUAL_UINT32(86400u, a.expiresIn);
  TEST_ASSERT_EQUAL_STRING("unpaired", a.state.c_str());
  TEST_ASSERT_EQUAL_INT(30, a.trialLeft);
  // a plain ws:// socket only for the simulator's loopback cloud; never a non-device token
  const char* plain = "{\"token\":\"sdt_abcdefghijklmnopqrstuvwxyz\",\"ws_url\":\"ws://127.0.0.1:8790/v1/device/ws\"}";
  TEST_ASSERT_FALSE(CloudLink::parseAuth(200, plain, strlen(plain), a));
  TEST_ASSERT_TRUE(CloudLink::parseAuth(200, plain, strlen(plain), a, true));
  const char* evil = "{\"token\":\"sdt_abcdefghijklmnopqrstuvwxyz\",\"ws_url\":\"ws://evil.example/ws\"}";
  TEST_ASSERT_FALSE(CloudLink::parseAuth(200, evil, strlen(evil), a, true));
  const char* other = "{\"token\":\"sk-ant-abcdefghijklmnopqrstuv\",\"ws_url\":\"wss://soul.example/ws\"}";
  TEST_ASSERT_FALSE(CloudLink::parseAuth(200, other, strlen(other), a));
  TEST_ASSERT_TRUE(a.token.empty());

  // the §6.2 error table
  const char* ne = "{\"error\":{\"code\":\"not_enrolled\",\"msg\":\"this SOUL is not registered\"}}";
  TEST_ASSERT_FALSE(CloudLink::parseAuth(403, ne, strlen(ne), a));
  CloudLink::AuthRetry r = CloudLink::authRetry(a, 1, 0);
  TEST_ASSERT_EQUAL_INT(CloudLink::AuthRetry::NotEnrolled, r.kind);
  TEST_ASSERT_EQUAL_UINT32(6u * 3600u * 1000u, r.waitMs);
  const char* kr = "{\"error\":{\"code\":\"key_revoked\",\"msg\":\"x\"}}";
  CloudLink::parseAuth(403, kr, strlen(kr), a);
  TEST_ASSERT_EQUAL_INT(CloudLink::AuthRetry::KeyRevoked, CloudLink::authRetry(a, 1, 0).kind);
  const char* bn = "{\"error\":{\"code\":\"bad_nonce\",\"msg\":\"x\"}}";
  CloudLink::parseAuth(400, bn, strlen(bn), a);
  TEST_ASSERT_EQUAL_INT(CloudLink::AuthRetry::NewChallenge, CloudLink::authRetry(a, 1, 0).kind);  // once
  TEST_ASSERT_EQUAL_INT(CloudLink::AuthRetry::Backoff, CloudLink::authRetry(a, 2, 0).kind);
  const char* bs = "{\"error\":{\"code\":\"bad_signature\",\"msg\":\"x\"}}";
  CloudLink::parseAuth(401, bs, strlen(bs), a);
  r = CloudLink::authRetry(a, 1, 0);
  TEST_ASSERT_EQUAL_UINT32(60000u, r.waitMs);  // 1 -> 60 min
  TEST_ASSERT_FALSE(r.showProblem);
  r = CloudLink::authRetry(a, 3, 0);
  TEST_ASSERT_EQUAL_UINT32(240000u, r.waitMs);
  TEST_ASSERT_TRUE(r.showProblem);  // "Can't sign in to SOUL Cloud" after 3 tries
  TEST_ASSERT_EQUAL_UINT32(3600000u, CloudLink::authRetry(a, 30, 0).waitMs);
  CloudLink::parseAuth(429, rl, strlen(rl), a);
  r = CloudLink::authRetry(a, 1, 0);
  TEST_ASSERT_EQUAL_INT(CloudLink::AuthRetry::Wait, r.kind);
  TEST_ASSERT_EQUAL_UINT32(5000u, r.waitMs);
}

static void test_cloud_frames_up() {
  CloudHello h;
  h.fw = "1.2.0";
  h.hw = "lcd28";
  h.lang = "ro";
  h.brainLocal = "cloud";
  h.tzPosix = "EET-2EEST,M3.5.0/3,M10.5.0/4";
  h.after = 411;
  JsonDocument he = parse(CloudLink::hello(h));
  TEST_ASSERT_EQUAL_INT(1, he["v"].as<int>());
  TEST_ASSERT_EQUAL_STRING("hello", he["t"]);
  TEST_ASSERT_EQUAL_INT(1, he["proto"][0].as<int>());
  TEST_ASSERT_EQUAL_UINT32(411u, he["after"].as<uint32_t>());
  TEST_ASSERT_EQUAL_STRING("cloud", he["brain_local"]);
  TEST_ASSERT_EQUAL_STRING("usb", he["power"]);
  TEST_ASSERT_EQUAL_STRING("EET-2EEST,M3.5.0/3,M10.5.0/4", he["tz_posix"]);
  bool confirm = false;
  for (JsonVariant v : he["caps"].as<JsonArray>())
    if (!strcmp(v.as<const char*>(), "confirm")) confirm = true;
  TEST_ASSERT_TRUE(confirm);  // this SOUL shows pair.confirm

  // ask: <= 2000 code points (raw UTF-8, never \u escapes), conv null, unsynced items in ctx
  std::string ro;
  for (int i = 0; i < 2100; ++i) ro += "\xC8\x9B";  // ț
  AiAction n;
  n.type = AiAction::NoteCreate;
  n.text = "lapte";
  std::vector<std::string> un = {CloudLink::itemAdd("c0ffee0011223344", n, 1790460000u),
                                 CloudLink::itemState("it_7", "", "rang", 1790980000u)};
  const std::string askF = CloudLink::ask("a17", ro, "ro", "", 4, un);
  TEST_ASSERT_TRUE(askF.size() <= CloudLink::kMaxOut);
  TEST_ASSERT_TRUE(askF.find("\\u") == std::string::npos);
  JsonDocument q = parse(askF);
  TEST_ASSERT_EQUAL_STRING("ask", q["t"]);
  TEST_ASSERT_EQUAL_INT(4000, (int)strlen(q["text"]));  // 2000 x 2 bytes
  TEST_ASSERT_TRUE(q["conv"].isNull());
  TEST_ASSERT_EQUAL_INT(4, q["ctx"]["timer_left_min"].as<int>());
  TEST_ASSERT_EQUAL_INT(1, (int)q["ctx"]["unsynced"].size());  // the note, not the state change
  TEST_ASSERT_EQUAL_STRING("note.create", q["ctx"]["unsynced"][0]["action"]);
  JsonDocument q2 = parse(CloudLink::ask("a18", "hi", "en", "c_9", -1, {}));
  TEST_ASSERT_EQUAL_STRING("c_9", q2["conv"]);
  TEST_ASSERT_TRUE(q2["ctx"]["timer_left_min"].isNull());

  JsonDocument k = parse(CloudLink::ack(412, true));
  TEST_ASSERT_TRUE(k["ok"].as<bool>());
  TEST_ASSERT_TRUE(k["err"].isNull());
  TEST_ASSERT_EQUAL_STRING("paused", parse(CloudLink::ack(413, false, "paused"))["err"]);
  TEST_ASSERT_EQUAL_STRING("a17", parse(CloudLink::abort("a17"))["re"]);
  JsonDocument st = parse(CloudLink::status(-61, -1, "usb", "1.2.0", 123456, true));
  TEST_ASSERT_TRUE(st["battery"].isNull());  // the 2.8C has no fuel gauge
  TEST_ASSERT_EQUAL_INT(-61, st["rssi"].as<int>());
  TEST_ASSERT_EQUAL_STRING("usb", st["power"]);

  // item.add: alarm with a weekday mask, reminder with an absolute local date
  AiAction al;
  al.type = AiAction::AlarmSet;
  al.hour = 7;
  al.minute = 5;
  al.days = 0x1F;  // Mon..Fri
  al.text = "Gym";
  const uint32_t created = 1790460000u;  // 2026-09-26 22:00 local
  JsonDocument ia = parse(CloudLink::itemAdd("c0ffee0011223344", al, created));
  TEST_ASSERT_EQUAL_STRING("item.add", ia["t"]);
  TEST_ASSERT_EQUAL_STRING("alarm.set", ia["action"]);
  TEST_ASSERT_EQUAL_STRING("07:05", ia["args"]["hhmm"]);
  TEST_ASSERT_EQUAL_INT(5, (int)ia["args"]["days"].size());
  TEST_ASSERT_EQUAL_STRING("fri", ia["args"]["days"][4]);
  TEST_ASSERT_EQUAL_STRING("2026-09-26T22:00", ia["created"]);
  AiAction rm;
  rm.type = AiAction::ReminderCreate;
  rm.hour = 9;
  rm.minute = 30;
  rm.text = "Call mom";  // 09:30 is already past at 22:00 -> tomorrow
  TEST_ASSERT_EQUAL_STRING("2026-09-27T09:30", parse(CloudLink::itemAdd("c0ffee0011223345", rm, created))["args"]["when"]);
  rm.when = parseLocalStamp("2026-10-03T18:00");
  TEST_ASSERT_EQUAL_STRING("2026-10-03T18:00", parse(CloudLink::itemAdd("c0ffee0011223346", rm, created))["args"]["when"]);
  AiAction tm;
  tm.type = AiAction::TimerStart;
  tm.minutes = 10;
  TEST_ASSERT_EQUAL_UINT32(600u, parse(CloudLink::itemAdd("c0ffee0011223347", tm, created))["args"]["seconds"].as<uint32_t>());
  // a 2000-character note of 4-byte characters still fits a 10 KB frame
  AiAction big;
  big.type = AiAction::NoteCreate;
  for (int i = 0; i < 2500; ++i) big.text += "\xF0\x9F\x98\x80";
  const std::string bf = CloudLink::itemAdd("c0ffee0011223349", big, created);
  TEST_ASSERT_TRUE(bf.size() <= CloudLink::kMaxOut);
  TEST_ASSERT_EQUAL_INT(8000, (int)strlen(parse(bf)["args"]["text"]));

  JsonDocument is = parse(CloudLink::itemState("it_42", "", "accepted", 1790980000u));
  TEST_ASSERT_EQUAL_STRING("item.state", is["t"]);
  TEST_ASSERT_EQUAL_STRING("it_42", is["item_id"]);
  TEST_ASSERT_EQUAL_STRING("accepted", is["state"]);
  TEST_ASSERT_TRUE(is["cid"].isNull());
  JsonDocument in = parse(CloudLink::inboxAdd("c0ffee0011223348", std::string(1200, 'q'), "claude"));
  TEST_ASSERT_EQUAL_INT(1000, (int)strlen(in["text"]));
  TEST_ASSERT_EQUAL_STRING("claude", in["to"]);
  TEST_ASSERT_EQUAL_STRING("any", parse(CloudLink::inboxAdd("c0ffee0011223348", "x", "siri"))["to"]);
  TEST_ASSERT_EQUAL_STRING("pair.ok", parse(CloudLink::pairAnswer("p_1", true))["t"]);
  TEST_ASSERT_EQUAL_STRING("pair.no", parse(CloudLink::pairAnswer("p_1", false))["t"]);
  TEST_ASSERT_TRUE(parse(CloudLink::connectors(true))["paused"].as<bool>());
  TEST_ASSERT_EQUAL_UINT32(1790990000u, parse(CloudLink::sleep(1790990000u))["wake_at"].as<uint32_t>());
  TEST_ASSERT_EQUAL_STRING("0000002a0000ffff", CloudLink::cid(42, 0xffff).c_str());
}

static void test_cloud_frames_down() {
  CloudLink c;
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Welcome,
                        (int)feed(c, "{\"v\":1,\"t\":\"welcome\",\"server_time\":1790980000,\"tz\":\"Europe/Bucharest\","
                                     "\"posix_tz\":\"EET-2EEST,M3.5.0/3,M10.5.0/4\",\"state\":\"paired\",\"owner\":\"Ana\","
                                     "\"brain\":\"cloud\",\"voice\":\"claude\",\"lang\":\"ro\",\"quiet\":{\"from\":\"22:00\","
                                     "\"to\":\"07:00\"},\"connectors_paused\":false,\"limits\":{\"ask_per_min\":20,"
                                     "\"ask_per_day\":600,\"frames_per_s\":2},\"allowance\":{\"left\":296,\"unit\":\"turns\","
                                     "\"renews\":\"2026-11-01\"},\"trial\":null,\"models\":{\"claude\":\"claude-haiku-4-5\","
                                     "\"openai\":\"gpt-6-luna\"},\"new_thing\":{\"x\":1}}"));
  TEST_ASSERT_EQUAL_UINT32(1790980000u, c.welcome.serverTime);
  TEST_ASSERT_EQUAL_STRING("EET-2EEST,M3.5.0/3,M10.5.0/4", c.welcome.posixTz.c_str());
  TEST_ASSERT_EQUAL_STRING("paired", c.welcome.state.c_str());
  TEST_ASSERT_EQUAL_INT(2, c.welcome.framesPerS);
  TEST_ASSERT_EQUAL_INT(296, c.welcome.allowanceLeft);
  TEST_ASSERT_EQUAL_INT(-1, c.welcome.trialLeft);
  TEST_ASSERT_EQUAL_STRING("claude-haiku-4-5", c.welcome.modelClaude.c_str());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Pairing,
                        (int)feed(c, "{\"v\":1,\"t\":\"pairing\",\"code\":\"7KQ3M9XD\",\"expires_in\":600,"
                                     "\"url\":\"https://soul.example/pair#c=7KQ3M9XD&d=soul-a1b2c3d4e5f6\"}"));
  TEST_ASSERT_EQUAL_STRING("7KQ3M9XD", c.pairing.code.c_str());
  TEST_ASSERT_EQUAL_STRING("https://soul.example/pair#c=7KQ3M9XD&d=soul-a1b2c3d4e5f6", c.pairing.url.c_str());
  // not 8 Crockford characters (I, L, O, U are not in the alphabet; rev. 1's 6 digits): never shown
  for (const char* b : {"{\"v\":1,\"t\":\"pairing\",\"code\":\"482913\"}", "{\"v\":1,\"t\":\"pairing\",\"code\":\"7KQ3M9XU\"}",
                        "{\"v\":1,\"t\":\"pairing\",\"code\":\"7kq3m9xd\"}"})
    TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, b));
  feed(c, "{\"v\":1,\"t\":\"pairing\",\"code\":\"AAAABBBB\",\"url\":\"http://evil.example/pair\"}");
  TEST_ASSERT_TRUE(c.pairing.url.empty());  // a non-https QR link is dropped

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::PairConfirm,
                        (int)feed(c, "{\"v\":1,\"t\":\"pair.confirm\",\"pid\":\"p_abc\",\"name\":\"Ana\\nMaria\","
                                     "\"account_hint\":\"a***@gmail.com\",\"expires_in\":120}"));
  TEST_ASSERT_EQUAL_STRING("p_abc", c.confirm.pid.c_str());
  TEST_ASSERT_EQUAL_STRING("Ana Maria", c.confirm.name.c_str());  // control characters cleaned
  TEST_ASSERT_EQUAL_STRING("a***@gmail.com", c.confirm.hint.c_str());
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"pair.confirm\"}"));

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Paired,
                        (int)feed(c, "{\"v\":1,\"t\":\"paired\",\"owner\":\"Ana\",\"account_hint\":\"a***@gmail.com\"}"));
  TEST_ASSERT_EQUAL_STRING("Ana", c.owner.c_str());
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Unpaired, (int)feed(c, "{\"v\":1,\"t\":\"unpaired\",\"reason\":\"user\"}"));
  TEST_ASSERT_EQUAL_STRING("user", c.unpairedReason.c_str());
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::ReplayDone, (int)feed(c, "{\"v\":1,\"t\":\"replay.done\",\"last\":17}"));
  TEST_ASSERT_EQUAL_UINT32(17u, c.last);
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Resync, (int)feed(c, "{\"v\":1,\"t\":\"resync\",\"last\":9}"));
  TEST_ASSERT_EQUAL_UINT32(9u, c.last);

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Reply,
                        (int)feed(c, "{\"v\":1,\"t\":\"reply\",\"re\":\"a17\",\"conv\":\"c_1\",\"say\":\"Gata, te trezesc "
                                     "la 7.\",\"face\":\"happy\",\"chips\":[\"07:00\"],\"provider\":\"claude\",\"brain\":"
                                     "\"cloud\",\"seqs\":[413],\"allowance\":{\"left\":295,\"unit\":\"turns\"}}"));
  TEST_ASSERT_EQUAL_STRING("c_1", c.reply.conv.c_str());
  TEST_ASSERT_EQUAL_STRING("happy", c.reply.reply.face.c_str());
  TEST_ASSERT_EQUAL_UINT32(413u, c.reply.seqs[0]);
  TEST_ASSERT_EQUAL_STRING("07:00", c.reply.chips[0].c_str());
  TEST_ASSERT_EQUAL_INT(0, (int)c.reply.reply.actions.size());  // state changes come as pushes only
  feed(c, "{\"v\":1,\"t\":\"reply\",\"re\":\"a18\",\"say\":\"\",\"face\":\"evil\",\"card\":{\"title\":\"Plan\","
          "\"body\":\"1. eggs\\n2. pan\"},\"note\":\"bad_key\",\"provider\":\"rules\"}");
  TEST_ASSERT_EQUAL_STRING("", c.reply.reply.face.c_str());
  TEST_ASSERT_EQUAL_STRING("Plan", c.reply.reply.say.c_str());
  TEST_ASSERT_EQUAL_STRING("bad_key", c.reply.note.c_str());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Added,
                        (int)feed(c, "{\"v\":1,\"t\":\"added\",\"cid\":\"c0ffee0011223344\",\"item_id\":\"it_5\"}"));
  TEST_ASSERT_EQUAL_STRING("it_5", c.addedItemId.c_str());
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::InboxState, (int)feed(c, "{\"v\":1,\"t\":\"inbox.state\",\"pending\":2,\"answered\":1}"));
  TEST_ASSERT_EQUAL_INT(2, c.inboxPending);

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Config,
                        (int)feed(c, "{\"v\":1,\"t\":\"config\",\"tz\":\"Europe/London\",\"posix_tz\":\"GMT0BST,M3.5.0/1,M10.5.0\"}"));
  TEST_ASSERT_TRUE(c.config.hasTz);
  TEST_ASSERT_FALSE(c.config.hasBrain);
  TEST_ASSERT_EQUAL_STRING("GMT0BST,M3.5.0/1,M10.5.0", c.config.posixTz.c_str());
  feed(c, "{\"v\":1,\"t\":\"config\",\"brain\":\"claude\",\"models\":{\"claude\":\"claude-haiku-4-5\"},\"name\":\"Bubu\"}");
  TEST_ASSERT_TRUE(c.config.hasBrain && c.config.hasModels && c.config.hasName && !c.config.hasTz);
  TEST_ASSERT_EQUAL_STRING("Bubu", c.config.name.c_str());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Error,
                        (int)feed(c, "{\"v\":1,\"t\":\"error\",\"code\":\"too_big\",\"msg\":\"frame over 10 KB\","
                                     "\"re\":\"x1\",\"cid\":\"c0ffee0011223344\"}"));
  TEST_ASSERT_EQUAL_STRING("too_big", c.error.code.c_str());
  TEST_ASSERT_EQUAL_STRING("c0ffee0011223344", c.error.cid.c_str());
  TEST_ASSERT_EQUAL_STRING("x1", c.error.re.c_str());
  TEST_ASSERT_EQUAL_INT((int)AiErr::Quota, (int)CloudLink::errFromCode("allowance"));
  TEST_ASSERT_EQUAL_INT((int)AiErr::NoKey, (int)CloudLink::errFromCode("unpaired"));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Upstream, (int)CloudLink::errFromCode("something_new"));

  // must-ignore: unknown types; garbage and other versions are rejected
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Unknown, (int)feed(c, "{\"v\":1,\"t\":\"ota\",\"version\":\"9\"}"));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":2,\"t\":\"welcome\"}"));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "[1,2,3]"));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"reply\""));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)c.feed(nullptr, 0));
}

static void test_cloud_pushes_map_to_actions() {
  CloudLink c;
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Push,
                        (int)feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":412,\"action\":\"reminder.create\",\"args\":{\"when\":"
                                     "\"2026-10-03T18:00\",\"text\":\"Call the bank\"},\"item_id\":\"it_412\",\"origin\":"
                                     "{\"kind\":\"connector\",\"app\":\"claude\",\"by\":\"Ana\"},\"say\":\"From Claude: "
                                     "tomorrow at 18:00.\",\"private\":true,\"needs_accept\":true}"));
  TEST_ASSERT_EQUAL_INT(CloudPush::Act, c.push.kind);
  TEST_ASSERT_EQUAL_STRING("it_412", c.push.itemId.c_str());
  TEST_ASSERT_EQUAL_STRING("connector", c.push.source.c_str());
  TEST_ASSERT_EQUAL_STRING("claude", c.push.app.c_str());
  TEST_ASSERT_EQUAL_STRING("Ana", c.push.by.c_str());
  TEST_ASSERT_TRUE(c.push.priv && c.push.needsAccept);
  TEST_ASSERT_EQUAL_INT(AiAction::ReminderCreate, c.push.act.type);
  TEST_ASSERT_EQUAL_UINT32(parseLocalStamp("2026-10-03T18:00"), c.push.act.when);

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":413,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":[\"mon\","
          "\"tue\",\"wed\",\"thu\",\"fri\"],\"label\":\"\"},\"item_id\":\"it_413\",\"origin\":{\"kind\":\"turn\"}}");
  TEST_ASSERT_EQUAL_INT(0x1F, c.push.act.days);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":414,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"09:15\",\"days\":[\"sat\",\"sun\"]}}");
  TEST_ASSERT_EQUAL_INT(0x60, c.push.act.days);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":416,\"action\":\"note.create\",\"args\":{\"text\":\"buy batteries\",\"tags\":[\"shop\"]}}");
  TEST_ASSERT_EQUAL_STRING("buy batteries", c.push.act.text.c_str());
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":417,\"action\":\"timer.start\",\"args\":{\"seconds\":90,\"label\":\"tea\"}}");
  TEST_ASSERT_EQUAL_UINT32(90u, c.push.act.seconds);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":418,\"action\":\"focus.start\",\"args\":{\"minutes\":25,\"label\":\"write\"}}");
  TEST_ASSERT_EQUAL_INT(25, c.push.act.minutes);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":419,\"action\":\"answer.show\",\"args\":{\"title\":\"Pancakes\",\"body\":"
          "\"1. flour\\n2. eggs\"},\"say\":\"Here are the steps\",\"expires_at\":1791001600,\"origin\":{\"kind\":\"connector\"}}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Card, c.push.kind);
  TEST_ASSERT_EQUAL_STRING("1. flour\n2. eggs", c.push.body.c_str());  // the card keeps its lines
  TEST_ASSERT_EQUAL_STRING("Here are the steps", c.push.say.c_str());
  TEST_ASSERT_EQUAL_UINT32(1791001600u, c.push.expiresAt);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":420,\"action\":\"item.delete\",\"args\":{\"item_id\":\"it_413\"}}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Delete, c.push.kind);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":421,\"action\":\"lights.on\",\"args\":{\"room\":\"all\"}}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Unsupported, c.push.kind);

  const char* bad[] = {
      "{\"v\":1,\"t\":\"push\",\"seq\":430,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"25:00\"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":431,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":[\"funday\"]}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":432,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":\"mon\"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":433,\"action\":\"reminder.create\",\"args\":{\"when\":\"tomorrow\",\"text\":\"x\"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":434,\"action\":\"reminder.create\",\"args\":{\"when\":\"2026-13-03T18:00\",\"text\":\"x\"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":435,\"action\":\"reminder.create\",\"args\":{\"when\":\"2026-10-03T18:00\",\"text\":\"\"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":436,\"action\":\"timer.start\",\"args\":{\"seconds\":0}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":437,\"action\":\"timer.start\",\"args\":{\"seconds\":\"60\"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":438,\"action\":\"focus.start\",\"args\":{\"minutes\":999}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":439,\"action\":\"note.create\",\"args\":{\"text\":\"   \"}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":440,\"action\":\"note.create\",\"args\":\"text\"}",
      "{\"v\":1,\"t\":\"push\",\"seq\":441,\"action\":\"item.delete\",\"args\":{}}",
      "{\"v\":1,\"t\":\"push\",\"seq\":442,\"action\":\"answer.show\",\"args\":{}}",
  };
  for (const char* b : bad) {
    TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Push, (int)feed(c, b));
    TEST_ASSERT_EQUAL_INT_MESSAGE(CloudPush::Invalid, c.push.kind, b);
  }
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"push\",\"action\":\"note.create\"}"));
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":450,\"action\":\"reminder.create\",\"args\":{\"when\":\"2026-10-01T08:00\","
          "\"text\":\"Pills\"},\"missed\":true}");
  TEST_ASSERT_TRUE(c.push.missed);
}

// drain what the session wants to send now
static std::vector<std::string> drain(CloudSession& s, uint32_t now) {
  std::vector<std::string> v;
  std::string f;
  s.tick(now);
  while (s.nextFrame(f, now)) v.push_back(f);
  return v;
}

static int count(const std::vector<std::string>& v, const char* type) {
  int n = 0;
  const std::string needle = std::string("\"t\":\"") + type + "\"";
  for (const std::string& f : v) n += f.find(needle) != std::string::npos;
  return n;
}

static const char* kWelcomePaired =
    "{\"v\":1,\"t\":\"welcome\",\"server_time\":1790980000,\"tz\":\"Europe/London\",\"posix_tz\":\"GMT0BST,M3.5.0/1,"
    "M10.5.0\",\"state\":\"paired\",\"owner\":\"Ana\",\"brain\":\"cloud\",\"voice\":\"claude\",\"lang\":\"en\","
    "\"quiet\":{\"from\":\"23:00\",\"to\":\"07:00\"},\"connectors_paused\":true,\"limits\":{\"frames_per_s\":2},"
    "\"allowance\":null,\"trial\":null,\"models\":{\"claude\":\"claude-haiku-4-5\",\"openai\":\"gpt-6-luna\"}}";

static void test_cloud_session_hello_welcome_time_zone() {
  CloudSession s;
  s.prefs.fw = "1.2.0";
  s.prefs.hw = "lcd28";
  s.prefs.tzPosix = "EET-2EEST,M3.5.0/3,M10.5.0/4";
  s.lastSeq = 41;
  JsonDocument h = parse(s.onOpen(1000));
  TEST_ASSERT_EQUAL_UINT32(41u, h["after"].as<uint32_t>());
  TEST_ASSERT_EQUAL_STRING("EET-2EEST,M3.5.0/3,M10.5.0/4", h["tz_posix"]);  // a hint only
  TEST_ASSERT_FALSE(s.welcomed());
  std::string f;
  TEST_ASSERT_FALSE(s.ask("hi", false, -1, 1000));  // not before welcome
  feed(s, kWelcomePaired);
  TEST_ASSERT_TRUE(s.welcomed());
  TEST_ASSERT_EQUAL_STRING("paired", s.state.c_str());
  TEST_ASSERT_EQUAL_STRING("Ana", s.owner.c_str());
  TEST_ASSERT_EQUAL_STRING("23:00", s.quietFrom.c_str());
  std::string tz;
  TEST_ASSERT_TRUE(s.pollTz(tz));  // the cloud's zone always wins over the device's own
  TEST_ASSERT_EQUAL_STRING("GMT0BST,M3.5.0/1,M10.5.0", tz.c_str());
  TEST_ASSERT_FALSE(s.pollTz(tz));
  uint32_t t = 0;
  TEST_ASSERT_TRUE(s.pollTime(t));
  TEST_ASSERT_EQUAL_UINT32(1790980000u, t);
  CloudConfig c;
  TEST_ASSERT_TRUE(s.pollConfig(c));
  TEST_ASSERT_TRUE(c.hasBrain);
  TEST_ASSERT_EQUAL_STRING("cloud", c.brain.c_str());
  TEST_ASSERT_EQUAL_STRING("claude-haiku-4-5", c.modelClaude.c_str());
  // the cloud's echo says paused, the switch on SOUL says not: SOUL wins and tells it
  const std::vector<std::string> up = drain(s, 1100);
  TEST_ASSERT_EQUAL_INT(1, count(up, "connectors"));
  TEST_ASSERT_TRUE(up[0].find("\"paused\":false") != std::string::npos);
  TEST_ASSERT_EQUAL_INT(1, count(up, "status"));
  // a config tz change later
  feed(s, "{\"v\":1,\"t\":\"config\",\"tz\":\"Europe/Berlin\",\"posix_tz\":\"CET-1CEST,M3.5.0,M10.5.0/3\"}");
  TEST_ASSERT_TRUE(s.pollTz(tz));
  TEST_ASSERT_EQUAL_STRING("CET-1CEST,M3.5.0,M10.5.0/3", tz.c_str());
  TEST_ASSERT_EQUAL_STRING("CET-1CEST,M3.5.0,M10.5.0/3", s.prefs.tzPosix.c_str());  // the next hello says it

  // unpaired: settings of an unpaired welcome never switch the brain
  CloudSession u;
  u.onOpen(0);
  feed(u, "{\"v\":1,\"t\":\"welcome\",\"state\":\"pending\",\"brain\":\"none\",\"posix_tz\":\"\",\"trial\":{\"left\":3}}");
  TEST_ASSERT_TRUE(u.pollConfig(c));
  TEST_ASSERT_FALSE(c.hasBrain);
  TEST_ASSERT_EQUAL_INT(3, u.trialLeft);
  TEST_ASSERT_FALSE(u.pollTz(tz));
}

static void test_cloud_session_pairing_needs_a_touch() {
  CloudSession s;
  s.onOpen(0);
  feed(s, "{\"v\":1,\"t\":\"welcome\",\"state\":\"pending\"}");
  feed(s, "{\"v\":1,\"t\":\"pairing\",\"code\":\"7KQ3M9XD\",\"expires_in\":600,\"url\":\"https://soul.example/pair#c=7KQ3M9XD&d=soul-a1b2c3d4e5f6\"}");
  NetInfo n;
  s.fill(n);
  TEST_ASSERT_EQUAL_STRING("7KQ3M9XD", n.pairCode.c_str());
  TEST_ASSERT_FALSE(n.paired);
  feed(s, "{\"v\":1,\"t\":\"pair.confirm\",\"pid\":\"p_1\",\"name\":\"Ana\",\"account_hint\":\"a***@gmail.com\",\"expires_in\":120}", 1000);
  s.fill(n);
  TEST_ASSERT_EQUAL_STRING("p_1", n.confirmPid.c_str());
  TEST_ASSERT_EQUAL_STRING("Ana", n.confirmName.c_str());
  drain(s, 1000);
  // nothing is answered by itself while the touch may still come; the same pid again keeps its deadline
  feed(s, "{\"v\":1,\"t\":\"pair.confirm\",\"pid\":\"p_1\",\"name\":\"Ana\",\"account_hint\":\"a***@gmail.com\",\"expires_in\":120}", 90000);
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 119000), "pair.no"));
  // an answer for another pid does nothing
  CloudOut o;
  o.kind = CloudOut::PairOk;
  o.pid = "p_other";
  s.send(o, 0, 0);
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 119500), "pair.ok"));
  // the touch
  o.pid = "p_1";
  s.send(o, 0, 0);
  std::vector<std::string> up = drain(s, 120000);
  TEST_ASSERT_EQUAL_INT(1, count(up, "pair.ok"));
  TEST_ASSERT_TRUE(up.back().find("\"pid\":\"p_1\"") != std::string::npos);
  s.send(o, 0, 0);  // a second tap: once only
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 120100), "pair.ok"));
  feed(s, "{\"v\":1,\"t\":\"paired\",\"owner\":\"Ana\",\"account_hint\":\"a***@gmail.com\"}");
  s.fill(n);
  TEST_ASSERT_TRUE(n.paired);
  TEST_ASSERT_TRUE(n.pairCode.empty() && n.confirmPid.empty());
  TEST_ASSERT_EQUAL_STRING("Ana", n.owner.c_str());

  // no touch within expires_in: pair.no
  CloudSession t;
  t.onOpen(0);
  feed(t, "{\"v\":1,\"t\":\"welcome\",\"state\":\"unpaired\"}");
  feed(t, "{\"v\":1,\"t\":\"pair.confirm\",\"pid\":\"p_2\",\"name\":\"X\",\"account_hint\":\"x***@x.ro\",\"expires_in\":120}", 5000);
  TEST_ASSERT_EQUAL_INT(0, count(drain(t, 124000), "pair.no"));
  TEST_ASSERT_EQUAL_INT(1, count(drain(t, 125500), "pair.no"));
  NetInfo m;
  t.fill(m);
  TEST_ASSERT_TRUE(m.confirmPid.empty());
  // unpaired later: back to the code, local items stay
  feed(s, "{\"v\":1,\"t\":\"unpaired\",\"reason\":\"user\"}");
  s.fill(n);
  TEST_ASSERT_FALSE(n.paired);
  TEST_ASSERT_TRUE(n.owner.empty());
}

static void test_cloud_session_pushes_acks_and_dedupe() {
  CloudSession s;
  s.lastSeq = 10;
  s.onOpen(0);
  feed(s, kWelcomePaired);
  drain(s, 10);
  // a replay of an applied push: acked again, never handed to SoulOS
  feed(s, "{\"v\":1,\"t\":\"push\",\"seq\":9,\"action\":\"note.create\",\"args\":{\"text\":\"old\"},\"item_id\":\"it_9\",\"origin\":{\"kind\":\"connector\"}}");
  CloudPush p;
  TEST_ASSERT_FALSE(s.pollPush(p));
  std::vector<std::string> up = drain(s, 20);
  TEST_ASSERT_EQUAL_INT(1, count(up, "ack"));
  TEST_ASSERT_TRUE(up[0].find("\"seq\":9,\"ok\":true") != std::string::npos);
  // a new one: to SoulOS, acked once applied
  const char* n11 = "{\"v\":1,\"t\":\"push\",\"seq\":11,\"action\":\"note.create\",\"args\":{\"text\":\"milk\"},\"item_id\":\"it_11\",\"origin\":{\"kind\":\"turn\"}}";
  feed(s, n11);
  feed(s, n11);  // twice on the wire (at-least-once): once to SoulOS
  TEST_ASSERT_TRUE(s.pollPush(p));
  TEST_ASSERT_FALSE(s.pollPush(p));
  TEST_ASSERT_EQUAL_UINT32(11u, p.seq);
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 30), "ack"));  // not before it is stored
  s.ackPush(11, true, nullptr);
  TEST_ASSERT_EQUAL_INT(1, count(drain(s, 40), "ack"));
  TEST_ASSERT_EQUAL_UINT32(11u, s.lastSeq);
  // unknown action / bad args: acked ok:false by the session itself
  feed(s, "{\"v\":1,\"t\":\"push\",\"seq\":12,\"action\":\"lights.on\",\"args\":{},\"item_id\":\"it_12\",\"origin\":{\"kind\":\"connector\"}}");
  feed(s, "{\"v\":1,\"t\":\"push\",\"seq\":13,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"99:99\"},\"item_id\":\"it_13\",\"origin\":{\"kind\":\"connector\"}}");
  up = drain(s, 50);
  TEST_ASSERT_EQUAL_INT(2, count(up, "ack"));
  TEST_ASSERT_TRUE(up[0].find("\"err\":\"unsupported\"") != std::string::npos);
  TEST_ASSERT_TRUE(up[1].find("\"err\":\"invalid\"") != std::string::npos);
  TEST_ASSERT_FALSE(s.pollPush(p));
  // connectors paused on SOUL: connector and shortcut pushes acked "paused", the turn's still applied
  CloudOut pause;
  pause.kind = CloudOut::Connectors;
  pause.paused = true;
  s.send(pause, 0, 0);
  TEST_ASSERT_TRUE(s.pausedDirty);
  up = drain(s, 60);
  TEST_ASSERT_EQUAL_INT(1, count(up, "connectors"));
  feed(s, "{\"v\":1,\"t\":\"push\",\"seq\":14,\"action\":\"note.create\",\"args\":{\"text\":\"spam\"},\"item_id\":\"it_14\",\"origin\":{\"kind\":\"connector\",\"app\":\"claude\"}}");
  feed(s, "{\"v\":1,\"t\":\"push\",\"seq\":15,\"action\":\"note.create\",\"args\":{\"text\":\"spam\"},\"item_id\":\"it_15\",\"origin\":{\"kind\":\"shortcut\"}}");
  feed(s, "{\"v\":1,\"t\":\"push\",\"seq\":16,\"action\":\"note.create\",\"args\":{\"text\":\"mine\"},\"item_id\":\"it_16\",\"origin\":{\"kind\":\"turn\"}}");
  up = drain(s, 70);
  TEST_ASSERT_EQUAL_INT(2, count(up, "ack"));
  TEST_ASSERT_TRUE(up[0].find("\"err\":\"paused\"") != std::string::npos);
  TEST_ASSERT_TRUE(s.pollPush(p));
  TEST_ASSERT_EQUAL_UINT32(16u, p.seq);
  // resync: the cloud was restored and is behind us
  feed(s, "{\"v\":1,\"t\":\"resync\",\"last\":5}");
  TEST_ASSERT_EQUAL_UINT32(5u, s.lastSeq);
  TEST_ASSERT_TRUE(s.seqSaveDue(80));

  // batched seq writes: every 10 pushes or 60 s, never per push
  CloudSession b;
  b.seqSaved(1000);
  TEST_ASSERT_FALSE(b.seqSaveDue(2000));
  for (uint32_t q = 1; q <= 9; ++q) b.ackPush(q, true, nullptr);
  TEST_ASSERT_FALSE(b.seqSaveDue(5000));
  b.ackPush(10, true, nullptr);
  TEST_ASSERT_TRUE(b.seqSaveDue(5000));
  b.seqSaved(5000);
  b.ackPush(11, true, nullptr);
  TEST_ASSERT_FALSE(b.seqSaveDue(30000));
  TEST_ASSERT_TRUE(b.seqSaveDue(65001));
}

static void test_cloud_session_outq_added_and_errors() {
  CloudSession s;
  uint32_t r = 0;
  s.rng = [&r]() { return ++r; };
  AiAction n;
  n.type = AiAction::NoteCreate;
  n.text = "first";
  CloudOut o;
  o.act = n;
  s.send(o, 1790460000u, 0);  // offline: queued
  o.act.text = "second";
  s.send(o, 1790460000u, 0);
  CloudOut st;
  st.kind = CloudOut::State;
  st.itemId = "it_7";
  st.state = "rang";
  s.send(st, 0, 1790980000u);
  TEST_ASSERT_EQUAL_INT(3, (int)s.outqSize());
  TEST_ASSERT_TRUE(s.outqDirty);
  // survives a reboot (NVS soulsync/outq)
  CloudSession again;
  again.loadOutq(s.saveOutq());
  TEST_ASSERT_EQUAL_INT(3, (int)again.outqSize());

  // not before welcome, not while unpaired
  s.onOpen(0);
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 10), "item.add"));
  feed(s, "{\"v\":1,\"t\":\"welcome\",\"state\":\"unpaired\"}");
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 20), "item.add"));
  feed(s, kWelcomePaired);
  std::vector<std::string> up = drain(s, 30);
  TEST_ASSERT_EQUAL_INT(2, count(up, "item.add"));
  TEST_ASSERT_EQUAL_INT(1, count(up, "item.state"));
  TEST_ASSERT_EQUAL_INT(2, (int)s.outqSize());  // item.state is fire and forget; the adds wait for `added`
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 40), "item.add"));  // once per socket
  // a turn carries what the cloud has not confirmed yet
  TEST_ASSERT_TRUE(s.ask("what's on today?", false, -1, 50));
  up = drain(s, 60);
  JsonDocument q = parse(up.back());
  TEST_ASSERT_EQUAL_INT(2, (int)q["ctx"]["unsynced"].size());
  // `added` takes the first out; too_big with its cid drops the second for good
  feed(s, "{\"v\":1,\"t\":\"added\",\"cid\":\"0000000100000002\",\"item_id\":\"it_20\"}");
  TEST_ASSERT_EQUAL_INT(1, (int)s.outqSize());
  feed(s, "{\"v\":1,\"t\":\"error\",\"code\":\"too_big\",\"msg\":\"frame over 10 KB\",\"cid\":\"0000000300000004\"}");
  TEST_ASSERT_EQUAL_INT(0, (int)s.outqSize());
  // rate_limited with a cid: kept and sent again after retry_ms
  o.act.text = "third";
  s.send(o, 1790460000u, 0);
  up = drain(s, 1000);
  TEST_ASSERT_EQUAL_INT(1, count(up, "item.add"));
  JsonDocument a = parse(up.back());
  const std::string cid = a["cid"].as<const char*>();
  const std::string err = "{\"v\":1,\"t\":\"error\",\"code\":\"rate_limited\",\"msg\":\"x\",\"retry_ms\":4000,\"cid\":\"" + cid + "\"}";
  s.onText(err.data(), err.size(), 1000);
  TEST_ASSERT_EQUAL_INT(0, count(drain(s, 3000), "item.add"));
  TEST_ASSERT_EQUAL_INT(1, count(drain(s, 5100), "item.add"));
  // a reconnect sends everything not `added` again (the cloud dedupes by cid)
  s.onClose(1006, 6000, 0);
  s.onOpen(7000);
  feed(s, kWelcomePaired, 7000);
  TEST_ASSERT_EQUAL_INT(1, count(drain(s, 7100), "item.add"));
  // overflow: the oldest item.state goes, an item.add never; a full queue keeps the item on SOUL only
  CloudSession f;
  for (int i = 0; i < 49; ++i) f.send(o, 1790460000u, 0);
  f.send(st, 0, 1);
  TEST_ASSERT_EQUAL_INT(50, (int)f.outqSize());
  f.send(o, 1790460000u, 0);  // the state change makes room
  TEST_ASSERT_EQUAL_INT(50, (int)f.outqSize());
  f.send(o, 1790460000u, 0);  // nothing left to drop
  TEST_ASSERT_EQUAL_INT(50, (int)f.outqSize());
  TEST_ASSERT_TRUE(f.saveOutq().size() <= 8192);
}

static void test_cloud_session_turns() {
  CloudSession s;
  s.onOpen(0);
  feed(s, kWelcomePaired);
  drain(s, 0);
  TEST_ASSERT_TRUE(s.ask("remind me at 9", false, -1, 1000));
  TEST_ASSERT_FALSE(s.ask("again", false, -1, 1000));  // one at a time
  std::vector<std::string> up = drain(s, 1000);
  JsonDocument a = parse(up.back());
  const std::string id = a["id"].as<const char*>();
  TEST_ASSERT_TRUE(id.size() <= 24);
  TEST_ASSERT_TRUE(a["conv"].isNull());
  // a reply for another turn is ignored; ours answers, with the conversation id kept 10 minutes
  feed(s, "{\"v\":1,\"t\":\"reply\",\"re\":\"zzz\",\"say\":\"no\"}", 2000);
  AiOutcome out;
  TEST_ASSERT_FALSE(s.pollAnswer(out));
  const std::string rep = "{\"v\":1,\"t\":\"reply\",\"re\":\"" + id + "\",\"conv\":\"c_7\",\"say\":\"Done.\",\"face\":\"happy\","
                          "\"chips\":[],\"provider\":\"claude\",\"brain\":\"cloud\",\"seqs\":[3],\"card\":{\"title\":\"T\",\"body\":\"B\"}}";
  s.onText(rep.data(), rep.size(), 2000);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)out.err);
  TEST_ASSERT_EQUAL_STRING("Done.\nB", out.reply.say.c_str());
  TEST_ASSERT_EQUAL_STRING("happy", out.reply.face.c_str());
  TEST_ASSERT_TRUE(s.ask("and at 10?", false, -1, 60000));
  TEST_ASSERT_EQUAL_STRING("c_7", parse(drain(s, 60000).back())["conv"]);
  // timeout: the device gives up after 25 s, aborts and does not run its own rules (the turn may still act)
  s.tick(86000);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Timeout, (int)out.err);
  TEST_ASSERT_TRUE(out.noLocal);
  TEST_ASSERT_EQUAL_INT(1, count(drain(s, 86000), "abort"));
  TEST_ASSERT_TRUE(s.ask("conv expired?", false, -1, 700000));
  TEST_ASSERT_TRUE(parse(drain(s, 700000).back())["conv"].isNull());  // > 10 min after the last reply
}

static void test_cloud_session_errors_for_turns_and_notes() {
  CloudSession s;
  s.onOpen(0);
  feed(s, kWelcomePaired);
  drain(s, 0);
  s.ask("hello", false, -1, 100);
  std::string id = parse(drain(s, 100).back())["id"].as<std::string>();
  std::string e = "{\"v\":1,\"t\":\"error\",\"re\":\"" + id + "\",\"code\":\"allowance\",\"msg\":\"used\"}";
  s.onText(e.data(), e.size(), 200);
  AiOutcome out;
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Quota, (int)out.err);
  TEST_ASSERT_FALSE(out.noLocal);
  s.ask("hello", false, -1, 300);
  id = parse(drain(s, 300).back())["id"].as<std::string>();
  e = "{\"v\":1,\"t\":\"reply\",\"re\":\"" + id + "\",\"say\":\"Rules here.\",\"provider\":\"rules\",\"note\":\"bad_key\"}";
  s.onText(e.data(), e.size(), 400);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)out.err);  // the answer is shown (its actions came as pushes)
  TEST_ASSERT_EQUAL_INT((int)AiErr::BadKey, (int)out.note);  // ... with the reason
  s.ask("hello", false, -1, 500);
  id = parse(drain(s, 500).back())["id"].as<std::string>();
  e = "{\"v\":1,\"t\":\"error\",\"re\":\"" + id + "\",\"code\":\"timeout\",\"msg\":\"slow\"}";
  s.onText(e.data(), e.size(), 600);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_TRUE(out.noLocal);
  // the socket drops mid-turn: network (the rules may answer)
  s.ask("hello", false, -1, 700);
  s.onClose(1006, 800, 0);
  TEST_ASSERT_TRUE(s.pollAnswer(out));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Network, (int)out.err);
}

static void test_cloud_close_codes_and_budget() {
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reauth, (int)CloudLink::onClose(4401));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reauth, (int)CloudLink::onClose(4403));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Replaced, (int)CloudLink::onClose(4409));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Update, (int)CloudLink::onClose(4426));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Wait, (int)CloudLink::onClose(4429));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Restart, (int)CloudLink::onClose(4000));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reconnect, (int)CloudLink::onClose(4400));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reconnect, (int)CloudLink::onClose(1006));
  TEST_ASSERT_EQUAL_UINT32(1000u, CloudLink::backoffMs(1, 0));
  TEST_ASSERT_EQUAL_UINT32(4000u, CloudLink::backoffMs(3, 0));
  TEST_ASSERT_EQUAL_UINT32(60000u, CloudLink::backoffMs(50, 0));
  TEST_ASSERT_EQUAL_UINT32(78000u, CloudLink::backoffMs(50, 1));  // + 30 % jitter at most

  CloudSession s;
  s.onOpen(0);
  CloudSession::Retry r = s.onClose(1006, 100, 0);
  TEST_ASSERT_EQUAL_UINT32(1000u, r.waitMs);
  s.onOpen(1200);
  r = s.onClose(1006, 1300, 0);
  TEST_ASSERT_EQUAL_UINT32(2000u, r.waitMs);  // backing off
  s.onOpen(4000);
  feed(s, kWelcomePaired, 4000);
  r = s.onClose(1000, 70000, 0);
  TEST_ASSERT_EQUAL_UINT32(1000u, r.waitMs);  // up a minute: the backoff starts again
  s.onOpen(0);
  TEST_ASSERT_EQUAL_INT(CloudSession::Retry::Reauth, s.onClose(4401, 1, 0).kind);
  s.onOpen(0);
  TEST_ASSERT_EQUAL_UINT32(60000u, s.onClose(4409, 1, 0).waitMs);  // replaced: not for a minute
  s.onOpen(0);
  r = s.onClose(4000, 1, 1);
  TEST_ASSERT_TRUE(r.waitMs >= 1000 && r.waitMs <= 5000);
  s.onOpen(0);
  feed(s, "{\"v\":1,\"t\":\"error\",\"code\":\"rate_limited\",\"msg\":\"x\",\"retry_ms\":45000}");
  TEST_ASSERT_EQUAL_UINT32(45000u, s.onClose(4429, 1, 0).waitMs);
  s.onOpen(0);
  TEST_ASSERT_EQUAL_UINT32(30000u, s.onClose(4429, 1, 0).waitMs);
  s.onOpen(0);
  r = s.onClose(4426, 1, 0);
  TEST_ASSERT_EQUAL_INT(CloudSession::Retry::Update, r.kind);
  TEST_ASSERT_TRUE(s.needUpdate);

  // frame budget: 10 burst then 2/s; acks have their own (a replay burst of 50 pushes)
  CloudSession b;
  b.onOpen(0);  // hello used one
  for (int i = 0; i < 20; ++i) b.send([] {
      CloudOut o;
      o.kind = CloudOut::State;
      o.itemId = "it_1";
      o.state = "rang";
      return o;
    }(), 0, 0);
  feed(b, kWelcomePaired);
  std::vector<std::string> up = drain(b, 0);
  TEST_ASSERT_EQUAL_INT(9, (int)up.size());  // connectors + status + 7 states: 9 tokens after the hello
  TEST_ASSERT_EQUAL_INT(0, (int)drain(b, 100).size());
  TEST_ASSERT_EQUAL_INT(2, (int)drain(b, 1100).size());  // 2 per second
  for (uint32_t q = 1; q <= 50; ++q) b.ackPush(q, true, nullptr);
  TEST_ASSERT_EQUAL_INT(50, count(drain(b, 1100), "ack"));
}

// Every frame recorded from the running cloud (ai/tools/record_frames.py) parses, and
// a session fed the whole recording ends where the cloud's own device ended.
static void test_cloud_replay_recorded_frames() {
  CloudLink c;
  int n = 0;
  for (const RecordedFrame& f : kRecordedFrames) {
    const CloudLink::Msg m = c.feed(f.json, strlen(f.json));
    TEST_ASSERT_NOT_EQUAL_MESSAGE((int)CloudLink::Msg::Bad, (int)m, f.json);
    if (strcmp(f.t, "ota") != 0) TEST_ASSERT_NOT_EQUAL_MESSAGE((int)CloudLink::Msg::Unknown, (int)m, f.json);
    if (!strcmp(f.t, "push")) {
      TEST_ASSERT_TRUE_MESSAGE(c.push.kind == CloudPush::Act || c.push.kind == CloudPush::Card ||
                                   c.push.kind == CloudPush::Delete,
                               f.json);
      TEST_ASSERT_FALSE_MESSAGE(c.push.source.empty(), f.json);
    }
    if (!strcmp(f.t, "pairing")) TEST_ASSERT_EQUAL_INT_MESSAGE(8, (int)c.pairing.code.size(), f.json);
    ++n;
  }
  TEST_ASSERT_TRUE(n >= kRecordedMin);
  // the types the cloud sent in the recorded story, each one understood
  for (const char* t : kRecordedTypes) {
    bool seen = false;
    for (const RecordedFrame& f : kRecordedFrames) seen = seen || !strcmp(f.t, t);
    TEST_ASSERT_TRUE_MESSAGE(seen, t);
  }
  // the whole story through one session, applying every push like SoulOS does
  CloudSession s;
  s.onOpen(0);
  uint32_t now = 0;
  int pushes = 0;
  for (const RecordedFrame& f : kRecordedFrames) {
    if (f.socket_start && now) {  // the recorder reconnected here
      s.onClose(1000, now, 0);
      s.onOpen(now);
    }
    now += 50;
    s.onText(f.json, strlen(f.json), now);
    CloudPush p;
    while (s.pollPush(p)) {
      s.ackPush(p.seq, true, nullptr);
      ++pushes;
    }
    std::string out;
    while (s.nextFrame(out, now + 100000)) {
    }
  }
  TEST_ASSERT_EQUAL_STRING(kRecordedFinalState, s.state.c_str());
  TEST_ASSERT_EQUAL_UINT32(kRecordedLastSeq, s.lastSeq);
  TEST_ASSERT_TRUE(pushes >= kRecordedMinPushes);
}

void runCloudTests() {
  RUN_TEST(test_cloud_device_key_matches_the_cloud_vector);
  RUN_TEST(test_cloud_auth_bodies_and_answers);
  RUN_TEST(test_cloud_frames_up);
  RUN_TEST(test_cloud_frames_down);
  RUN_TEST(test_cloud_pushes_map_to_actions);
  RUN_TEST(test_cloud_session_hello_welcome_time_zone);
  RUN_TEST(test_cloud_session_pairing_needs_a_touch);
  RUN_TEST(test_cloud_session_pushes_acks_and_dedupe);
  RUN_TEST(test_cloud_session_outq_added_and_errors);
  RUN_TEST(test_cloud_session_turns);
  RUN_TEST(test_cloud_session_errors_for_turns_and_notes);
  RUN_TEST(test_cloud_close_codes_and_budget);
  RUN_TEST(test_cloud_replay_recorded_frames);
}
