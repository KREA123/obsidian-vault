// SOUL Cloud protocol v1, device side (docs/07-CONNECT-AI.md §2 and §6):
// recorded frames in, frames out, the push -> action mapping, dedupe,
// close codes and backoff. Transport-free, like the AI protocol tests.
#include <ArduinoJson.h>
#include <unity.h>

#include <cstring>
#include <string>

#include "CloudLink.h"

using namespace suflet;

static CloudLink::Msg feed(CloudLink& c, const char* s) { return c.feed(s, strlen(s)); }

static JsonDocument parse(const std::string& s) {
  JsonDocument d;
  TEST_ASSERT_FALSE(deserializeJson(d, s));
  return d;
}

static void test_cloud_identity_and_auth() {
  const uint8_t mac[6] = {0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6};
  TEST_ASSERT_EQUAL_STRING("soul-a1b2c3d4e5f6", CloudLink::deviceId(mac).c_str());

  uint8_t sec[32];
  for (int i = 0; i < 32; ++i) sec[i] = (uint8_t)(i * 37 + 11);
  const std::string b = CloudLink::base64url(sec, 32);
  TEST_ASSERT_EQUAL_INT(43, (int)b.size());  // unpadded base64url of 32 bytes
  for (char ch : b) TEST_ASSERT_TRUE(isalnum((unsigned char)ch) || ch == '-' || ch == '_');
  const uint8_t man[3] = {'M', 'a', 'n'};
  TEST_ASSERT_EQUAL_STRING("TWFu", CloudLink::base64url(man, 3).c_str());
  TEST_ASSERT_EQUAL_STRING("TWE", CloudLink::base64url(man, 2).c_str());
  const uint8_t ff[2] = {0xFB, 0xFF};
  TEST_ASSERT_EQUAL_STRING("-_8", CloudLink::base64url(ff, 2).c_str());

  JsonDocument body = parse(CloudLink::authBody("soul-a1b2c3d4e5f6", b, "0.5.0", "lcd28"));
  TEST_ASSERT_EQUAL_STRING("soul-a1b2c3d4e5f6", body["device_id"]);
  TEST_ASSERT_EQUAL_STRING(b.c_str(), body["secret"]);
  TEST_ASSERT_EQUAL_STRING("lcd28", body["hw"]);

  const char* ok =
      "{\"token\":\"sdt_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG\",\"expires_in\":2592000,"
      "\"ws_url\":\"wss://soul.example.eu/v1/device/ws\",\"server_time\":1790460000,\"paired\":false,\"owner\":\"\","
      "\"pairing\":{\"code\":\"482913\",\"expires_in\":600,\"url\":\"https://soul.example.eu/pair?d=soul-a1&c=482913\"},"
      "\"future_field\":[1,2,3]}";
  CloudAuth a;
  TEST_ASSERT_TRUE(CloudLink::parseAuth(200, ok, strlen(ok), a));
  TEST_ASSERT_EQUAL_STRING("wss://soul.example.eu/v1/device/ws", a.wsUrl.c_str());
  TEST_ASSERT_EQUAL_UINT32(2592000u, a.expiresIn);
  TEST_ASSERT_EQUAL_STRING("482913", a.pairCode.c_str());
  TEST_ASSERT_FALSE(a.paired);
  TEST_ASSERT_TRUE(a.token.compare(0, 4, "sdt_") == 0);

  // a plain ws:// socket, a token that is not a device token, errors
  const char* plain = "{\"token\":\"sdt_abcdefghijklmnopqrstuvwxyz\",\"ws_url\":\"ws://soul.example.eu/v1/device/ws\"}";
  TEST_ASSERT_FALSE(CloudLink::parseAuth(200, plain, strlen(plain), a));
  const char* other = "{\"token\":\"sk-ant-abcdefghijklmnopqrstuv\",\"ws_url\":\"wss://soul.example.eu/ws\"}";
  TEST_ASSERT_FALSE(CloudLink::parseAuth(200, other, strlen(other), a));
  TEST_ASSERT_TRUE(a.token.empty());
  TEST_ASSERT_FALSE(CloudLink::parseAuth(401, "{\"detail\":\"bad secret\"}", 23, a));
  TEST_ASSERT_FALSE(CloudLink::parseAuth(200, "<html>", 6, a));
}

static void test_cloud_frames_up() {
  CloudLink c;
  c.lastSeq = 411;
  JsonDocument h = parse(c.hello("0.5.0", "lcd28", "cloud", "ro", "EET-2EEST,M3.5.0/3,M10.5.0/4"));
  TEST_ASSERT_EQUAL_INT(1, h["v"].as<int>());
  TEST_ASSERT_EQUAL_STRING("hello", h["t"]);
  TEST_ASSERT_EQUAL_INT(1, h["proto"][0].as<int>());
  TEST_ASSERT_EQUAL_UINT32(411u, h["after"].as<uint32_t>());
  TEST_ASSERT_EQUAL_STRING("cloud", h["brain"]);
  bool inbox = false;
  for (JsonVariant v : h["caps"].as<JsonArray>())
    if (!strcmp(v.as<const char*>(), "inbox")) inbox = true;
  TEST_ASSERT_TRUE(inbox);

  AiContext ctx;
  ctx.alarms = "07:00 weekdays on";
  ctx.timerLeftMin = 4;
  ctx.notes = 3;
  JsonDocument q = parse(c.ask("a17", std::string(2500, 'x'), "ro", ctx));
  TEST_ASSERT_EQUAL_STRING("ask", q["t"]);
  TEST_ASSERT_EQUAL_STRING("a17", q["id"]);
  TEST_ASSERT_EQUAL_INT(2000, (int)strlen(q["text"]));  // the protocol's limit
  TEST_ASSERT_EQUAL_INT(4, q["ctx"]["timer_left_min"].as<int>());
  TEST_ASSERT_EQUAL_STRING("07:00 weekdays on", q["ctx"]["alarms"]);

  JsonDocument k = parse(c.ack(412, true));
  TEST_ASSERT_EQUAL_STRING("ack", k["t"]);
  TEST_ASSERT_EQUAL_UINT32(412u, k["seq"].as<uint32_t>());
  TEST_ASSERT_TRUE(k["ok"].as<bool>());
  TEST_ASSERT_TRUE(k["err"].isNull());
  JsonDocument k2 = parse(c.ack(413, false, "unsupported"));
  TEST_ASSERT_EQUAL_STRING("unsupported", k2["err"]);

  JsonDocument ab = parse(c.abort("a17"));
  TEST_ASSERT_EQUAL_STRING("abort", ab["t"]);
  TEST_ASSERT_EQUAL_STRING("a17", ab["re"]);

  JsonDocument st = parse(c.status(-1, -61, true, "0.5.0", 123456));
  TEST_ASSERT_TRUE(st["battery"].isNull());  // the 2.8C has no fuel gauge
  TEST_ASSERT_EQUAL_INT(-61, st["rssi"].as<int>());

  // item.add: alarm with a weekday mask, reminder with an absolute local date
  AiAction al;
  al.type = AiAction::AlarmSet;
  al.hour = 7;
  al.minute = 5;
  al.days = 0x1F;  // Mon..Fri
  al.text = "Gym";
  const uint32_t created = 1790460000u;  // 2026-09-26 22:00 local
  JsonDocument ia = parse(c.itemAdd("c0ffee0011223344", al, created));
  TEST_ASSERT_EQUAL_STRING("item.add", ia["t"]);
  TEST_ASSERT_EQUAL_STRING("alarm.set", ia["action"]);
  TEST_ASSERT_EQUAL_STRING("07:05", ia["args"]["hhmm"]);
  TEST_ASSERT_EQUAL_INT(5, (int)ia["args"]["days"].size());
  TEST_ASSERT_EQUAL_STRING("mon", ia["args"]["days"][0]);
  TEST_ASSERT_EQUAL_STRING("fri", ia["args"]["days"][4]);
  TEST_ASSERT_EQUAL_STRING("2026-09-26T22:00", ia["created"]);

  AiAction rm;
  rm.type = AiAction::ReminderCreate;
  rm.hour = 9;
  rm.minute = 30;
  rm.text = "Call mom";  // 09:30 is already past at 22:00 -> tomorrow
  JsonDocument ir = parse(c.itemAdd("c0ffee0011223345", rm, created));
  TEST_ASSERT_EQUAL_STRING("2026-09-27T09:30", ir["args"]["when"]);
  rm.when = parseLocalStamp("2026-10-03T18:00");
  JsonDocument ir2 = parse(c.itemAdd("c0ffee0011223346", rm, created));
  TEST_ASSERT_EQUAL_STRING("2026-10-03T18:00", ir2["args"]["when"]);

  AiAction tm;
  tm.type = AiAction::TimerStart;
  tm.minutes = 10;
  JsonDocument it = parse(c.itemAdd("c0ffee0011223347", tm, created));
  TEST_ASSERT_EQUAL_UINT32(600u, it["args"]["seconds"].as<uint32_t>());

  JsonDocument in = parse(c.inboxAdd("c0ffee0011223348", std::string(1200, 'q'), "claude"));
  TEST_ASSERT_EQUAL_STRING("inbox.add", in["t"]);
  TEST_ASSERT_EQUAL_INT(1000, (int)strlen(in["text"]));
  TEST_ASSERT_EQUAL_STRING("claude", in["to"]);
}

static void test_cloud_session_frames_down() {
  CloudLink c;
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Welcome,
                        (int)feed(c, "{\"v\":1,\"t\":\"welcome\",\"server_time\":1790460000,\"tz\":\"Europe/Bucharest\","
                                     "\"posix_tz\":\"EET-2EEST,M3.5.0/3,M10.5.0/4\",\"paired\":false,\"owner\":\"\","
                                     "\"brain\":\"cloud\",\"limits\":{\"ask_per_min\":20},\"new_thing\":{\"x\":1}}"));
  TEST_ASSERT_EQUAL_UINT32(1790460000u, c.serverTime);
  TEST_ASSERT_EQUAL_STRING("EET-2EEST,M3.5.0/3,M10.5.0/4", c.posixTz.c_str());
  TEST_ASSERT_EQUAL_STRING("cloud", c.brain.c_str());
  TEST_ASSERT_EQUAL_INT(20, c.limitAskPerMin);
  TEST_ASSERT_FALSE(c.paired);

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Pairing,
                        (int)feed(c, "{\"v\":1,\"t\":\"pairing\",\"code\":\"482913\",\"expires_in\":600,"
                                     "\"url\":\"https://soul.example.eu/pair?d=soul-a1b2c3d4e5f6&c=482913\"}"));
  TEST_ASSERT_EQUAL_STRING("482913", c.pairCode.c_str());
  TEST_ASSERT_EQUAL_STRING("https://soul.example.eu/pair?d=soul-a1b2c3d4e5f6&c=482913", c.pairUrl.c_str());
  TEST_ASSERT_EQUAL_UINT32(600u, c.pairExpires);
  // not six digits: never shown; a non-https QR link is dropped
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"pairing\",\"code\":\"48291\"}"));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"pairing\",\"code\":\"48291a\"}"));
  TEST_ASSERT_EQUAL_STRING("482913", c.pairCode.c_str());
  feed(c, "{\"v\":1,\"t\":\"pairing\",\"code\":\"112233\",\"url\":\"http://evil.example/pair\"}");
  TEST_ASSERT_EQUAL_STRING("112233", c.pairCode.c_str());
  TEST_ASSERT_TRUE(c.pairUrl.empty());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Paired, (int)feed(c, "{\"v\":1,\"t\":\"paired\",\"owner\":\"Ana\\nMaria\"}"));
  TEST_ASSERT_TRUE(c.paired);
  TEST_ASSERT_EQUAL_STRING("Ana Maria", c.owner.c_str());  // control characters cleaned
  TEST_ASSERT_TRUE(c.pairCode.empty());
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Unpaired, (int)feed(c, "{\"v\":1,\"t\":\"unpaired\"}"));
  TEST_ASSERT_FALSE(c.paired);
  TEST_ASSERT_TRUE(c.owner.empty());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Reply,
                        (int)feed(c, "{\"v\":1,\"t\":\"reply\",\"re\":\"a17\",\"say\":\"Gata, te trezesc la 7 \\u00een zilele "
                                     "lucr\\u0103toare.\",\"face\":\"happy\",\"seqs\":[413],\"provider\":\"claude\","
                                     "\"brain\":\"cloud\",\"allowance\":{\"left\":1412,\"unit\":\"turns\"},\"chips\":[\"ok\"]}"));
  TEST_ASSERT_EQUAL_STRING("a17", c.reply.re.c_str());
  TEST_ASSERT_EQUAL_STRING("happy", c.reply.reply.face.c_str());
  TEST_ASSERT_EQUAL_INT(1, (int)c.reply.seqs.size());
  TEST_ASSERT_EQUAL_UINT32(413u, c.reply.seqs[0]);
  TEST_ASSERT_EQUAL_INT(1412, c.reply.allowanceLeft);
  TEST_ASSERT_EQUAL_INT(0, (int)c.reply.reply.actions.size());  // state changes come as pushes only
  TEST_ASSERT_TRUE(c.reply.reply.say.find("Gata") == 0);

  // unknown face -> none; card text kept as plain text; say from the card title
  feed(c, "{\"v\":1,\"t\":\"reply\",\"re\":\"a18\",\"say\":\"\",\"face\":\"evil\",\"card\":{\"title\":\"Plan\","
          "\"body\":\"1. eggs\\n2. pan\"}}");
  TEST_ASSERT_EQUAL_STRING("", c.reply.reply.face.c_str());
  TEST_ASSERT_EQUAL_STRING("Plan", c.reply.title.c_str());
  TEST_ASSERT_EQUAL_STRING("Plan", c.reply.reply.say.c_str());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::SayDelta, (int)feed(c, "{\"v\":1,\"t\":\"say.delta\",\"re\":\"a19\",\"text\":\"Gata\"}"));
  TEST_ASSERT_EQUAL_STRING("a19", c.deltaRe.c_str());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Config,
                        (int)feed(c, "{\"v\":1,\"t\":\"config\",\"brain\":\"claude\",\"lang\":\"en\","
                                     "\"models\":{\"claude\":\"claude-haiku-4-5\",\"openai\":\"gpt-6-luna\"},\"name\":\"Bubu\"}"));
  TEST_ASSERT_EQUAL_STRING("claude", c.brain.c_str());
  TEST_ASSERT_EQUAL_STRING("claude-haiku-4-5", c.modelClaude.c_str());
  TEST_ASSERT_EQUAL_STRING("Bubu", c.name.c_str());

  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Error,
                        (int)feed(c, "{\"v\":1,\"t\":\"error\",\"re\":\"a20\",\"code\":\"rate_limited\",\"retry_ms\":4000,"
                                     "\"msg\":\"slow down\"}"));
  TEST_ASSERT_EQUAL_INT((int)AiErr::RateLimited, (int)c.error.err);
  TEST_ASSERT_EQUAL_INT(4000, c.error.retryMs);
  TEST_ASSERT_EQUAL_STRING("a20", c.error.re.c_str());
  TEST_ASSERT_EQUAL_INT((int)AiErr::Quota, (int)CloudLink::errFromCode("allowance"));
  TEST_ASSERT_EQUAL_INT((int)AiErr::BadKey, (int)CloudLink::errFromCode("bad_key"));
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
  // the doc's example: a reminder from the Claude phone app, days ahead
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Push,
                        (int)feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":412,\"action\":\"reminder.create\",\"args\":{\"when\":"
                                     "\"2026-10-03T18:00\",\"text\":\"Call the bank\"},\"item_id\":\"r_412\",\"source\":"
                                     "\"connector\",\"say\":\"Te anun\\u021b m\\u00e2ine la 18:00.\"}"));
  TEST_ASSERT_EQUAL_INT(CloudPush::Act, c.push.kind);
  TEST_ASSERT_EQUAL_UINT32(412u, c.push.seq);
  TEST_ASSERT_EQUAL_STRING("r_412", c.push.itemId.c_str());
  TEST_ASSERT_EQUAL_STRING("connector", c.push.source.c_str());
  TEST_ASSERT_EQUAL_INT(AiAction::ReminderCreate, c.push.act.type);
  TEST_ASSERT_EQUAL_UINT32(parseLocalStamp("2026-10-03T18:00"), c.push.act.when);
  TEST_ASSERT_EQUAL_INT(18, c.push.act.hour);
  TEST_ASSERT_EQUAL_STRING("Call the bank", c.push.act.text.c_str());
  TEST_ASSERT_TRUE(c.push.say.find("18:00") != std::string::npos);

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":413,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"07:00\",\"days\":[\"mon\","
          "\"tue\",\"wed\",\"thu\",\"fri\"],\"label\":\"\"},\"item_id\":\"a_413\",\"source\":\"turn\"}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Act, c.push.kind);
  TEST_ASSERT_EQUAL_INT(AiAction::AlarmSet, c.push.act.type);
  TEST_ASSERT_EQUAL_INT(7, c.push.act.hour);
  TEST_ASSERT_EQUAL_INT(0x1F, c.push.act.days);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":414,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"09:15\",\"days\":[\"sat\",\"sun\"]}}");
  TEST_ASSERT_EQUAL_INT(0x60, c.push.act.days);
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":415,\"action\":\"alarm.set\",\"args\":{\"hhmm\":\"06:45\",\"days\":[]}}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Act, c.push.kind);
  TEST_ASSERT_EQUAL_INT(0, c.push.act.days);  // once

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":416,\"action\":\"note.create\",\"args\":{\"text\":\"buy batteries\",\"tags\":[\"shop\"]}}");
  TEST_ASSERT_EQUAL_INT(AiAction::NoteCreate, c.push.act.type);
  TEST_ASSERT_EQUAL_STRING("buy batteries", c.push.act.text.c_str());

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":417,\"action\":\"timer.start\",\"args\":{\"seconds\":90,\"label\":\"tea\"}}");
  TEST_ASSERT_EQUAL_INT(AiAction::TimerStart, c.push.act.type);
  TEST_ASSERT_EQUAL_UINT32(90u, c.push.act.seconds);
  TEST_ASSERT_EQUAL_INT(2, c.push.act.minutes);

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":418,\"action\":\"focus.start\",\"args\":{\"minutes\":25,\"label\":\"write\"}}");
  TEST_ASSERT_EQUAL_INT(AiAction::FocusStart, c.push.act.type);
  TEST_ASSERT_EQUAL_INT(25, c.push.act.minutes);

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":419,\"action\":\"answer.show\",\"args\":{\"say\":\"Here are the steps\","
          "\"title\":\"Pancakes\",\"body\":\"1. flour\\n2. eggs\"},\"source\":\"connector\"}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Card, c.push.kind);
  TEST_ASSERT_EQUAL_STRING("Pancakes", c.push.title.c_str());
  TEST_ASSERT_EQUAL_STRING("Here are the steps", c.push.say.c_str());

  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":420,\"action\":\"item.delete\",\"args\":{\"item_id\":\"a_413\"}}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Delete, c.push.kind);
  TEST_ASSERT_EQUAL_STRING("a_413", c.push.itemId.c_str());

  // an action this firmware does not know: acked ok:false "unsupported"
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":421,\"action\":\"lights.on\",\"args\":{\"room\":\"all\"}}");
  TEST_ASSERT_EQUAL_INT(CloudPush::Unsupported, c.push.kind);

  // invalid arguments are never applied
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
    TEST_ASSERT_TRUE(c.push.seq >= 430);  // still acked (ok:false) by its seq
  }
  // no seq / no action: cannot even be acked
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"push\",\"action\":\"note.create\"}"));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Bad, (int)feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":9}"));

  // a reminder that arrives late is flagged
  feed(c, "{\"v\":1,\"t\":\"push\",\"seq\":450,\"action\":\"reminder.create\",\"args\":{\"when\":\"2026-10-01T08:00\","
          "\"text\":\"Pills\"},\"missed\":true}");
  TEST_ASSERT_TRUE(c.push.missed);
}

static void test_cloud_dedupe_close_and_backoff() {
  CloudLink c;
  c.lastSeq = 410;  // from NVS
  TEST_ASSERT_TRUE(c.alreadyApplied(405));
  TEST_ASSERT_TRUE(c.alreadyApplied(410));
  TEST_ASSERT_FALSE(c.alreadyApplied(411));
  c.applied(411);
  TEST_ASSERT_TRUE(c.alreadyApplied(411));
  TEST_ASSERT_EQUAL_UINT32(411u, c.lastSeq);

  // batched NVS writes: not per push
  c.seqSaved(1000);
  TEST_ASSERT_FALSE(c.seqSaveDue(2000));
  for (uint32_t s = 412; s < 420; ++s) c.applied(s);
  TEST_ASSERT_FALSE(c.seqSaveDue(5000));  // 8 pushes, 4 s
  c.applied(420);
  c.applied(421);
  TEST_ASSERT_TRUE(c.seqSaveDue(5000));  // 10 pushes
  c.seqSaved(5000);
  c.applied(422);
  TEST_ASSERT_FALSE(c.seqSaveDue(30000));
  TEST_ASSERT_TRUE(c.seqSaveDue(65001));  // 60 s

  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reauth, (int)CloudLink::onClose(4401));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Unpaired, (int)CloudLink::onClose(4403));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Update, (int)CloudLink::onClose(4426));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Wait, (int)CloudLink::onClose(4429));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reconnect, (int)CloudLink::onClose(4000));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reconnect, (int)CloudLink::onClose(4409));
  TEST_ASSERT_EQUAL_INT((int)CloudLink::CloseAction::Reconnect, (int)CloudLink::onClose(1006));

  TEST_ASSERT_EQUAL_UINT32(1000u, CloudLink::backoffMs(1, 0));
  TEST_ASSERT_EQUAL_UINT32(2000u, CloudLink::backoffMs(2, 0));
  TEST_ASSERT_EQUAL_UINT32(4000u, CloudLink::backoffMs(3, 0));
  TEST_ASSERT_EQUAL_UINT32(60000u, CloudLink::backoffMs(7, 0));
  TEST_ASSERT_EQUAL_UINT32(60000u, CloudLink::backoffMs(50, 0));
  TEST_ASSERT_EQUAL_UINT32(78000u, CloudLink::backoffMs(50, 1));  // + 30 % jitter at most
  TEST_ASSERT_EQUAL_UINT32(1300u, CloudLink::backoffMs(1, 5));    // jitter clamped
}

void runCloudTests() {
  RUN_TEST(test_cloud_identity_and_auth);
  RUN_TEST(test_cloud_frames_up);
  RUN_TEST(test_cloud_session_frames_down);
  RUN_TEST(test_cloud_pushes_map_to_actions);
  RUN_TEST(test_cloud_dedupe_close_and_backoff);
}
