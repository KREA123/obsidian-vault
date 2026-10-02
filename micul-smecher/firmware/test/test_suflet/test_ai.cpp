// The AI protocol: the same cases the web SoulOS tests (os/tests/soulos.test.mjs
// "strict protocol validation"), plus request building, answers and errors of
// the Claude / OpenAI / relay APIs, and the on-device rules.
#include <ArduinoJson.h>
#include <unity.h>

#include <cstring>
#include <string>

#include "AiProtocol.h"

using namespace suflet;

static const uint32_t kNow = 1790460000u;  // 2026-09-26 22:00 (local)

static void test_ai_protocol_strict_validation_like_the_web() {
  AiReply a = parseReply(
      "{\"say\":\"ok\",\"actions\":[{\"type\":\"timer.start\",\"minutes\":10},{\"type\":\"note.create\",\"text\":\"milk\"},"
      "{\"type\":\"alarm.set\",\"time\":\"25:00\"},{\"type\":\"alarm.set\",\"time\":\"7:05\",\"label\":\"x\",\"extra\":1},"
      "{\"type\":\"timer.start\",\"minutes\":999},{\"type\":\"rm -rf\"}]}");
  TEST_ASSERT_EQUAL_INT(2, (int)a.actions.size());
  TEST_ASSERT_EQUAL_INT(4, a.rejected);
  TEST_ASSERT_EQUAL_INT(AiAction::TimerStart, a.actions[0].type);
  TEST_ASSERT_EQUAL_INT(10, a.actions[0].minutes);
  TEST_ASSERT_EQUAL_INT(AiAction::NoteCreate, a.actions[1].type);

  AiReply b = parseReply(
      "Sure! Here you go: {\"say\":\"Done\",\"actions\":[{\"type\":\"reminder.create\",\"time\":\"09:30\",\"day\":"
      "\"tomorrow\",\"text\":\"Call mom\"}]} hope that helps");
  TEST_ASSERT_EQUAL_STRING("Done", b.say.c_str());
  TEST_ASSERT_EQUAL_INT(1, (int)b.actions.size());
  TEST_ASSERT_TRUE(b.actions[0].tomorrow);
  TEST_ASSERT_EQUAL_INT(9, b.actions[0].hour);
  TEST_ASSERT_EQUAL_INT(30, b.actions[0].minute);

  AiReply c = parseReply("I am not JSON at all");
  TEST_ASSERT_TRUE(c.loose);
  TEST_ASSERT_EQUAL_INT(0, (int)c.actions.size());
  TEST_ASSERT_EQUAL_STRING("I am not JSON at all", c.say.c_str());

  AiReply d = parseReply("{\"say\":\"x\",\"actions\":[{\"type\":\"alarm.set\",\"time\":\"07:00\",\"repeat\":\"sometimes\"}]}");
  TEST_ASSERT_EQUAL_INT(0, (int)d.actions.size());
  TEST_ASSERT_EQUAL_INT(1, d.rejected);

  AiReply e = parseReply("{\"say\":\"Doing it\",\"actions\":[{\"type\":\"alarm.set\",\"time\":\"99:99\"},{\"type\":\"messages.send\",\"to\":\"all\"}]}");
  TEST_ASSERT_EQUAL_INT(0, (int)e.actions.size());
  TEST_ASSERT_EQUAL_INT(2, e.rejected);
}

static void test_ai_protocol_normalises_and_bounds_fields() {
  AiReply r = parseReply(
      "```json\n{\"say\":\"  Alarm\\n set  \",\"face\":\"wink\",\"actions\":[{\"type\":\"alarm.set\",\"time\":\"7:05\","
      "\"label\":\"Gym\",\"repeat\":\"weekdays\"},{\"type\":\"focus.start\",\"minutes\":2},{\"type\":\"focus.start\","
      "\"minutes\":25.4}]}\n```");
  TEST_ASSERT_EQUAL_STRING("Alarm set", r.say.c_str());
  TEST_ASSERT_EQUAL_STRING("wink", r.face.c_str());
  TEST_ASSERT_EQUAL_INT(2, (int)r.actions.size());
  TEST_ASSERT_EQUAL_INT(7, r.actions[0].hour);
  TEST_ASSERT_EQUAL_INT(5, r.actions[0].minute);
  TEST_ASSERT_EQUAL_HEX8(0x1F, r.actions[0].days);
  TEST_ASSERT_EQUAL_STRING("Gym", r.actions[0].text.c_str());
  TEST_ASSERT_EQUAL_INT(25, r.actions[1].minutes);
  TEST_ASSERT_EQUAL_INT(1, r.rejected);
  // an unknown face is ignored, a non-string say makes the reply loose
  TEST_ASSERT_EQUAL_STRING("", parseReply("{\"say\":\"hi\",\"face\":\"evil\"}").face.c_str());
  TEST_ASSERT_TRUE(parseReply("{\"say\":42}").loose);
  // strings are cut on a code point, control characters become spaces
  std::string longNote = "{\"say\":\"ok\",\"actions\":[{\"type\":\"note.create\",\"text\":\"";
  for (int i = 0; i < 400; ++i) longNote += "\xC8\x99";  // ș
  longNote += "\"}]}";
  AiReply n = parseReply(longNote);
  TEST_ASSERT_EQUAL_INT(1, (int)n.actions.size());
  TEST_ASSERT_EQUAL_INT(600, (int)n.actions[0].text.size());  // 300 code points x 2 bytes
  // numbers as strings and nested junk are refused, an action object (not array) is read
  TEST_ASSERT_EQUAL_INT(0, (int)parseReply("{\"say\":\"x\",\"actions\":[{\"type\":\"timer.start\",\"minutes\":\"10\"}]}").actions.size());
  TEST_ASSERT_EQUAL_INT(1, (int)parseReply("{\"say\":\"x\",\"actions\":{\"type\":\"note.create\",\"text\":\"a\"}}").actions.size());
  TEST_ASSERT_TRUE(parseReply("").loose);
  TEST_ASSERT_TRUE(parseReply("{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{").loose);
}

static void test_ai_claude_request_shape() {
  AiConfig cfg;
  cfg.mode = AiMode::Claude;
  AiContext ctx;
  ctx.name = "Pixel";
  ctx.now = kNow;
  ctx.alarms = "07:30 weekdays \"Gym\" on";
  HttpRequest rq;
  TEST_ASSERT_EQUAL_INT((int)AiErr::NoKey, (int)buildRequest(cfg, ctx, {}, "hi", rq));
  cfg.anthropicKey = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz";
  std::vector<ChatTurn> hist = {{true, "earlier"}, {false, "{\"say\":\"ok\"}"}};
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)buildRequest(cfg, ctx, hist, "Wake me at 6:30", rq));
  TEST_ASSERT_EQUAL_STRING("https://api.anthropic.com/v1/messages", rq.url.c_str());
  bool key = false, ver = false, beta = false;
  for (auto& h : rq.headers) {
    if (h.first == "x-api-key") key = h.second == cfg.anthropicKey;
    if (h.first == "anthropic-version") ver = h.second == "2023-06-01";
    if (h.first == "anthropic-beta") beta = h.second == "server-side-fallback-2026-07-01";
  }
  TEST_ASSERT_TRUE(key && ver && beta);
  JsonDocument d;
  TEST_ASSERT_FALSE(deserializeJson(d, rq.body, DeserializationOption::NestingLimit(24)));
  TEST_ASSERT_EQUAL_STRING("claude-opus-5-5", d["model"]);
  TEST_ASSERT_EQUAL_STRING("low", d["output_config"]["effort"]);
  TEST_ASSERT_EQUAL_STRING("json_schema", d["output_config"]["format"]["type"]);
  TEST_ASSERT_EQUAL_STRING("default", d["fallbacks"]);
  TEST_ASSERT_TRUE(d["thinking"].isNull());     // Opus 5.5: thinking cannot be disabled; effort controls it
  TEST_ASSERT_TRUE(d["tool_choice"].isNull());  // no forced tool use on Opus 5.5
  TEST_ASSERT_EQUAL_INT(3, (int)d["messages"].size());
  TEST_ASSERT_EQUAL_STRING("assistant", d["messages"][1]["role"]);
  TEST_ASSERT_EQUAL_STRING("Wake me at 6:30", d["messages"][2]["content"]);
  const char* sys = d["system"];
  TEST_ASSERT_NOT_NULL(strstr(sys, "You are Pixel"));
  TEST_ASSERT_NOT_NULL(strstr(sys, "07:30 weekdays"));
  TEST_ASSERT_NOT_NULL(strstr(sys, "alarm.set"));
  // the key never ends up in the body
  TEST_ASSERT_NULL(strstr(rq.body.c_str(), "sk-ant"));
  cfg.useSchema = false;
  buildRequest(cfg, ctx, hist, "x", rq);
  TEST_ASSERT_NULL(strstr(rq.body.c_str(), "json_schema"));
}

static void test_ai_claude_answers_and_errors() {
  AiConfig cfg;
  cfg.mode = AiMode::Claude;
  const char* ok =
      "{\"id\":\"msg_1\",\"type\":\"message\",\"role\":\"assistant\",\"content\":[{\"type\":\"thinking\",\"thinking\":\"\","
      "\"signature\":\"abc\"},{\"type\":\"text\",\"text\":\"{\\\"say\\\":\\\"Alarm at 6:30.\\\",\\\"face\\\":\\\"happy\\\","
      "\\\"actions\\\":[{\\\"type\\\":\\\"alarm.set\\\",\\\"time\\\":\\\"06:30\\\",\\\"label\\\":\\\"\\\",\\\"repeat\\\":"
      "\\\"once\\\"}]}\"}],\"stop_reason\":\"end_turn\",\"usage\":{\"input_tokens\":900,\"output_tokens\":60}}";
  AiOutcome o = parseResponse(cfg, 200, ok, strlen(ok));
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)o.err);
  TEST_ASSERT_EQUAL_STRING("Alarm at 6:30.", o.reply.say.c_str());
  TEST_ASSERT_EQUAL_INT(1, (int)o.reply.actions.size());
  TEST_ASSERT_EQUAL_INT(6, o.reply.actions[0].hour);
  const char* refusal = "{\"content\":[],\"stop_reason\":\"refusal\",\"stop_details\":{\"type\":\"refusal\",\"category\":\"cyber\"}}";
  TEST_ASSERT_EQUAL_INT((int)AiErr::Refused, (int)parseResponse(cfg, 200, refusal, strlen(refusal)).err);
  const char* bad = "{\"type\":\"error\",\"error\":{\"type\":\"authentication_error\",\"message\":\"invalid x-api-key\"}}";
  TEST_ASSERT_EQUAL_INT((int)AiErr::BadKey, (int)parseResponse(cfg, 401, bad, strlen(bad)).err);
  const char* over = "{\"type\":\"error\",\"error\":{\"type\":\"overloaded_error\",\"message\":\"Overloaded\"}}";
  AiOutcome ov = parseResponse(cfg, 529, over, strlen(over));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Upstream, (int)ov.err);
  TEST_ASSERT_EQUAL_INT(1000, retryDelayMs(ov, 1));
  TEST_ASSERT_EQUAL_INT(3000, retryDelayMs(ov, 2));
  TEST_ASSERT_EQUAL_INT(-1, retryDelayMs(ov, 3));
  AiOutcome rl = parseResponse(cfg, 429, over, strlen(over));
  TEST_ASSERT_EQUAL_INT((int)AiErr::RateLimited, (int)rl.err);
  TEST_ASSERT_EQUAL_INT(-1, retryDelayMs(rl, 2));
  const char* sch = "{\"type\":\"error\",\"error\":{\"type\":\"invalid_request_error\",\"message\":\"output_config.format: bad schema\"}}";
  AiOutcome s = parseResponse(cfg, 400, sch, strlen(sch));
  TEST_ASSERT_TRUE(s.schemaRejected);
  TEST_ASSERT_EQUAL_INT(-1, retryDelayMs(s, 1));
  TEST_ASSERT_EQUAL_INT((int)AiErr::Upstream, (int)parseResponse(cfg, 200, "<html>", 6).err);
  TEST_ASSERT_EQUAL_INT((int)AiErr::Timeout, (int)parseResponse(cfg, -1, "", 0, AiErr::Timeout).err);
  const char* cut = "{\"content\":[{\"type\":\"text\",\"text\":\"{\\\"say\\\":\\\"Long\"}],\"stop_reason\":\"max_tokens\"}";
  TEST_ASSERT_EQUAL_INT((int)AiErr::Truncated, (int)parseResponse(cfg, 200, cut, strlen(cut)).err);
}

static void test_ai_openai_request_and_answers() {
  AiConfig cfg;
  cfg.mode = AiMode::ChatGpt;
  cfg.openaiKey = "sk-proj-abcdefghijklmnopqrstuvwx";
  HttpRequest rq;
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)buildRequest(cfg, AiContext(), {}, "hello", rq));
  TEST_ASSERT_EQUAL_STRING("https://api.openai.com/v1/chat/completions", rq.url.c_str());
  JsonDocument d;
  deserializeJson(d, rq.body);
  TEST_ASSERT_EQUAL_STRING("json_object", d["response_format"]["type"]);
  TEST_ASSERT_EQUAL_STRING("system", d["messages"][0]["role"]);
  TEST_ASSERT_EQUAL_STRING("hello", d["messages"][1]["content"]);
  const char* ok =
      "{\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\",\"content\":\"{\\\"say\\\":\\\"Timer on.\\\","
      "\\\"actions\\\":[{\\\"type\\\":\\\"timer.start\\\",\\\"minutes\\\":5}]}\",\"refusal\":null},\"finish_reason\":\"stop\"}]}";
  AiOutcome o = parseResponse(cfg, 200, ok, strlen(ok));
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)o.err);
  TEST_ASSERT_EQUAL_INT(5, o.reply.actions[0].minutes);
  const char* quota = "{\"error\":{\"message\":\"You exceeded your current quota\",\"type\":\"insufficient_quota\",\"code\":\"insufficient_quota\"}}";
  TEST_ASSERT_EQUAL_INT((int)AiErr::Quota, (int)parseResponse(cfg, 429, quota, strlen(quota)).err);
  const char* refuse = "{\"choices\":[{\"message\":{\"content\":null,\"refusal\":\"I can't help with that.\"}}]}";
  TEST_ASSERT_EQUAL_INT((int)AiErr::Refused, (int)parseResponse(cfg, 200, refuse, strlen(refuse)).err);
}

static void test_ai_relay_request_and_action_mapping() {
  AiConfig cfg;
  cfg.mode = AiMode::Relay;
  cfg.relayUrl = "https://soul.example.eu/";
  cfg.relayToken = "tok";
  cfg.deviceId = "SOUL-A1B2";
  HttpRequest rq;
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)buildRequest(cfg, AiContext(), {}, "wake me at 7", rq));
  TEST_ASSERT_EQUAL_STRING("https://soul.example.eu/v1/ask", rq.url.c_str());
  const char* ok =
      "{\"say\":\"Alarm set for 07:00, weekdays.\",\"provider\":\"claude\",\"mode\":\"claude\",\"face\":\"happy\",\"actions\":["
      "{\"ok\":true,\"action\":\"alarm.set\",\"id\":3,\"say\":\"\",\"card\":{\"title\":\"07:00\",\"body\":\"weekdays\",\"icon\":\"alarm\"},"
      "\"data\":{\"next\":\"2026-09-28T07:00\",\"days\":[\"mon\",\"tue\",\"wed\",\"thu\",\"fri\"]}},"
      "{\"ok\":true,\"action\":\"timer.start\",\"card\":{\"title\":\"10 minutes\",\"body\":\"\"},\"data\":{\"ends_at\":\"2026-09-26T22:10:00\"}},"
      "{\"ok\":false,\"action\":\"note.create\",\"error\":\"x\"}]}";
  AiOutcome o = parseResponse(cfg, 200, ok, strlen(ok), AiErr::None, kNow);
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)o.err);
  TEST_ASSERT_EQUAL_STRING("happy", o.reply.face.c_str());
  TEST_ASSERT_EQUAL_INT(2, (int)o.reply.actions.size());
  TEST_ASSERT_EQUAL_HEX8(0x1F, o.reply.actions[0].days);
  TEST_ASSERT_EQUAL_INT(10, o.reply.actions[1].minutes);
  TEST_ASSERT_EQUAL_INT((int)AiErr::BadKey, (int)parseResponse(cfg, 401, "{\"detail\":\"bad token\"}", 22).err);
}

static void test_ai_local_rules_understand_times_and_timers() {
  AiReply r;
  TEST_ASSERT_TRUE(localAct("wake me at 6:30", kNow, false, r));
  TEST_ASSERT_EQUAL_INT(AiAction::AlarmSet, r.actions[0].type);
  TEST_ASSERT_EQUAL_INT(6, r.actions[0].hour);
  TEST_ASSERT_EQUAL_INT(30, r.actions[0].minute);
  TEST_ASSERT_TRUE(localAct("remind me to call the bank at 5", kNow, false, r));
  TEST_ASSERT_EQUAL_INT(AiAction::ReminderCreate, r.actions[0].type);
  TEST_ASSERT_EQUAL_INT(17, r.actions[0].hour);  // "at 5" = 17:00
  TEST_ASSERT_EQUAL_STRING("Call the bank", r.actions[0].text.c_str());
  TEST_ASSERT_TRUE(localAct("Amintește-mi mâine la 9 și jumătate să sun la bancă", kNow, true, r));
  TEST_ASSERT_TRUE(r.actions[0].tomorrow);
  TEST_ASSERT_EQUAL_INT(9, r.actions[0].hour);
  TEST_ASSERT_EQUAL_INT(30, r.actions[0].minute);
  TEST_ASSERT_TRUE(localAct("set an alarm for 7am", kNow, false, r));
  TEST_ASSERT_EQUAL_INT(7, r.actions[0].hour);
  TEST_ASSERT_TRUE(localAct("timer 10 minutes", kNow, false, r));
  TEST_ASSERT_EQUAL_INT(AiAction::TimerStart, r.actions[0].type);
  TEST_ASSERT_EQUAL_INT(10, r.actions[0].minutes);
  TEST_ASSERT_TRUE(localAct("pune un minutar de 3 minute", kNow, true, r));
  TEST_ASSERT_EQUAL_INT(3, r.actions[0].minutes);
  TEST_ASSERT_TRUE(localAct("in 15 minutes check the oven", kNow, false, r));
  TEST_ASSERT_EQUAL_INT(22, r.actions[0].hour);
  TEST_ASSERT_EQUAL_INT(15, r.actions[0].minute);
  TEST_ASSERT_FALSE(localAct("what is the meaning of life", kNow, false, r));
  AiReply n = localReply("what is the meaning of life", kNow, false, true);
  TEST_ASSERT_EQUAL_INT(AiAction::NoteCreate, n.actions[0].type);
  TEST_ASSERT_EQUAL_STRING("Wake me up at 7:30", ("Wake me up at 7:30"));
  TEST_ASSERT_EQUAL_STRING("Gym", cleanLabel("set an alarm at 7:30 gym").c_str());
}

static void test_ai_keys_are_masked_and_checked() {
  TEST_ASSERT_EQUAL_STRING("sk-ant-\xE2\x80\xA6wxyz", maskKey("sk-ant-api03-abcdefghijklmnopqrstuvwxyz").c_str());
  TEST_ASSERT_TRUE(keyLooksValid(AiMode::Claude, "sk-ant-api03-abcdefghijklmnop"));
  TEST_ASSERT_FALSE(keyLooksValid(AiMode::Claude, "sk-proj-abcdefghijklmnopqrst"));
  TEST_ASSERT_FALSE(keyLooksValid(AiMode::Claude, "sk-ant-short"));
  TEST_ASSERT_TRUE(keyLooksValid(AiMode::ChatGpt, "sk-proj-abcdefghijklmnopqrst"));
  TEST_ASSERT_FALSE(keyLooksValid(AiMode::ChatGpt, "sk-ant has space and stuff"));
  TEST_ASSERT_EQUAL_STRING("bad_key", aiErrCode(AiErr::BadKey));
  TEST_ASSERT_TRUE(strlen(aiErrText(AiErr::Offline, true)) > 3);
}

void runAiTests() {
  RUN_TEST(test_ai_protocol_strict_validation_like_the_web);
  RUN_TEST(test_ai_protocol_normalises_and_bounds_fields);
  RUN_TEST(test_ai_claude_request_shape);
  RUN_TEST(test_ai_claude_answers_and_errors);
  RUN_TEST(test_ai_openai_request_and_answers);
  RUN_TEST(test_ai_relay_request_and_action_mapping);
  RUN_TEST(test_ai_local_rules_understand_times_and_timers);
  RUN_TEST(test_ai_keys_are_masked_and_checked);
}
