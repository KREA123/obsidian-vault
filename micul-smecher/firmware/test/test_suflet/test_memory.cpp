// SOUL Memory (docs/10-SOUL-MEMORY.md): the store, retrieval, the offline rules, the A/B flash slots,
// the AI protocol's memory.remember / memory.forget and the OS hooks (Settings › Memory, the undo toast).
#include <ArduinoJson.h>
#include <unity.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "BridgeLink.h"
#include "CloudLink.h"
#include "Gestures.h"
#include "Memory.h"
#include "Os.h"

using namespace suflet;

namespace {

const uint32_t kNow = 1790359080u;  // Friday 25 September 2026, 17:58 local (as in test_os)
const uint32_t kDay = 86400u;

struct RamFlash : FlashIo {
  std::vector<uint8_t> mem;
  size_t cutAfter = (size_t)-1;  // simulate a power cut: writes stop after this many bytes
  size_t written = 0;
  int erases = 0;
  explicit RamFlash(size_t n) : mem(n, 0xFF) {}
  size_t size() const override { return mem.size(); }
  bool read(size_t off, void* dst, size_t n) override {
    if (off + n > mem.size()) return false;
    memcpy(dst, mem.data() + off, n);
    return true;
  }
  bool erase(size_t off, size_t n) override {
    if (off % MemoryFlash::kSector || n % MemoryFlash::kSector || off + n > mem.size()) return false;
    memset(mem.data() + off, 0xFF, n);
    erases += (int)(n / MemoryFlash::kSector);
    return true;
  }
  bool write(size_t off, const void* src, size_t n) override {
    if (off + n > mem.size()) return false;
    for (size_t i = 0; i < n; ++i) {
      if (written >= cutAfter) return false;
      mem[off + i] &= ((const uint8_t*)src)[i];  // NOR flash: bits only go 1 -> 0
      ++written;
    }
    return true;
  }
};

struct Dev {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  SoulMemory mem;
  Os os{&alarms};
  TouchGestures tg;
  DisplayGeometry g = displays::kLcd28;
  bool finger = false;
  float fx = 0, fy = 0;
  Inputs in;
  explicit Dev(AiMode mode = AiMode::Claude, bool connected = true) {
    os.settings().booted = 1;
    os.settings().ai = (uint8_t)mode;
    BirthInfo b;
    b.design = 5;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = 1234;
    os.setMemory(&mem);
    os.begin(g, b);
    NetInfo n;
    n.configured = n.connected = connected;
    n.keyClaude = true;
    os.setNet(n);
    tg.setMode(TouchMode::Text);
    os.setClock(kNow);
    in.hour = 18.6f;
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
  void hold(float x, float y, float s) {
    fx = g.s(x);
    fy = g.s(y);
    finger = true;
    run(s);
    finger = false;
    run(0.3f);
  }
};

bool has(const std::string& s, const char* part) { return s.find(part) != std::string::npos; }

}  // namespace

// ------------------------------------------------------------------ the store ---

static void test_memory_remember_dedupes_refuses_secrets_and_caps() {
  SoulMemory m;
  const int a = m.remember("My sister is Ana", FactKind::Person, FactSrc::User, kNow, 4, "Ana");
  TEST_ASSERT_TRUE(a > 0);
  TEST_ASSERT_EQUAL_INT(a, m.remember("my  sister is ANA.", FactKind::Person, FactSrc::Ai, kNow + 5));  // the same fact
  TEST_ASSERT_EQUAL_INT(1, (int)m.size());
  TEST_ASSERT_TRUE(m.at(0).pinned);  // the owner said it: no decay
  // secrets never go in
  TEST_ASSERT_EQUAL_INT(0, m.remember("My wifi password is hunter22", FactKind::Other, FactSrc::User, kNow));
  TEST_ASSERT_EQUAL_INT(0, m.remember("PIN 4512 for the card", FactKind::Other, FactSrc::User, kNow));
  TEST_ASSERT_EQUAL_INT(0, m.remember("card 4111 1111 1111 1111", FactKind::Other, FactSrc::User, kNow));
  TEST_ASSERT_EQUAL_INT(0, m.remember("key sk-ant-api03-abcdefghij", FactKind::Other, FactSrc::User, kNow));
  TEST_ASSERT_EQUAL_INT(0, m.remember("   ", FactKind::Other, FactSrc::User, kNow));
  TEST_ASSERT_FALSE(SoulMemory::looksSecret("Ana's phone is in the kitchen"));
  // a new date for the same person's day corrects the one kept
  const int b = m.remember("Ana's birthday is on 12 May", FactKind::Person, FactSrc::Rule, kNow, 4, "Ana", 512);
  TEST_ASSERT_EQUAL_INT(b, m.remember("Ana's birthday is on 13 May", FactKind::Person, FactSrc::Rule, kNow, 4, "Ana", 513));
  TEST_ASSERT_EQUAL_UINT16(513, m.find(b)->mmdd);
  // long text is cut on a code point, at most 120 bytes
  std::string longer;
  for (int i = 0; i < 40; ++i) longer += "ăbc ";
  const int c = m.remember(longer, FactKind::Note, FactSrc::Ai, kNow);
  TEST_ASSERT_TRUE(m.find(c)->text.size() <= SoulMemory::kTextMax);
  // the cap: 512 facts at most, the least worth keeping goes first, the pinned ones stay
  for (int i = 0; i < 600; ++i)
    m.remember("trivia number " + std::to_string(i), FactKind::Other, FactSrc::Ai, kNow - 200 * kDay + i, 1);
  TEST_ASSERT_EQUAL_INT((int)SoulMemory::kMax, (int)m.size());
  TEST_ASSERT_NOT_NULL(m.find(a));
  TEST_ASSERT_NOT_NULL(m.find(b));
  // forget: by keyword (>= 3 chars), by id, undo, wipe
  TEST_ASSERT_EQUAL_INT(0, m.forgetMatching("a"));
  TEST_ASSERT_EQUAL_INT(1, m.forgetMatching("sister"));
  TEST_ASSERT_NULL(m.find(a));
  const int d = m.remember("I like tea without sugar", FactKind::Preference, FactSrc::Ai, kNow);
  TEST_ASSERT_TRUE(m.undoLast());
  TEST_ASSERT_NULL(m.find(d));
  m.clear();
  TEST_ASSERT_EQUAL_INT(0, (int)m.size());
}

static void test_memory_retrieval_ranks_with_synonyms_recency_and_budget() {
  SoulMemory m;
  m.remember("My sister is Ana", FactKind::Person, FactSrc::User, kNow - 30 * kDay, 4, "Ana");
  m.remember("Ana's birthday is on 12 May", FactKind::Person, FactSrc::Rule, kNow - 10 * kDay, 4, "Ana", 512);
  m.remember("I like tea without sugar", FactKind::Preference, FactSrc::User, kNow);
  m.remember("I work at the bakery on Monday mornings", FactKind::Place, FactSrc::Ai, kNow - kDay);
  m.remember("My Wi-Fi is called Pisicuta", FactKind::Place, FactSrc::Rule, kNow, 3, "wifi");
  // RO question, EN facts: "ziua" ~ birthday, "Anei" ~ Ana
  std::vector<int> r = m.rank("când e ziua Anei?", kNow, 1, false);
  TEST_ASSERT_EQUAL_INT(1, (int)r.size());
  TEST_ASSERT_TRUE(has(m.at((size_t)r[0]).text, "birthday"));
  r = m.rank("ce ceai îmi place?", kNow, 1, false);
  TEST_ASSERT_TRUE(has(m.at((size_t)r[0]).text, "tea"));
  r = m.rank("cum se numește rețeaua mea?", kNow, 1, false);
  TEST_ASSERT_TRUE(has(m.at((size_t)r[0]).text, "Wi-Fi"));
  r = m.rank("who is my sister", kNow, 1, false);
  TEST_ASSERT_TRUE(has(m.at((size_t)r[0]).text, "sister"));
  TEST_ASSERT_EQUAL_INT(0, (int)m.rank("quantum physics", kNow, 3, false).size());
  TEST_ASSERT_EQUAL_INT(3, (int)m.rank("quantum physics", kNow, 3, true).size());  // general: the profile
  // the block for the AI: header, facts, within the budget (~300 tokens), birthdays carry the date
  const std::string block = m.contextBlock("is it Ana's birthday soon?", kNow, false);
  TEST_ASSERT_TRUE(has(block, "What SOUL knows about you"));
  TEST_ASSERT_TRUE(has(block, "12 May"));
  TEST_ASSERT_TRUE(block.size() <= SoulMemory::kBudgetChars + 200);
  for (int i = 0; i < 100; ++i)
    m.remember("Filler fact number " + std::to_string(i) + " about something long enough to take room", FactKind::Other,
               FactSrc::Ai, kNow, 1);
  const std::string big = m.contextBlock("Ana", kNow, true);
  TEST_ASSERT_TRUE(big.size() <= SoulMemory::kBudgetChars + 200);
  TEST_ASSERT_TRUE(has(big, "My sister is Ana"));  // the matching facts come first
  TEST_ASSERT_EQUAL_STRING("", SoulMemory().contextBlock("x", kNow, false).c_str());
}

static void test_memory_dates_parse_en_ro_and_numeric() {
  TEST_ASSERT_EQUAL_UINT16(512, parseDayMonth("Ana's birthday is May 12"));
  TEST_ASSERT_EQUAL_UINT16(512, parseDayMonth("on the 12th of May"));
  TEST_ASSERT_EQUAL_UINT16(512, parseDayMonth("ziua Anei e pe 12 mai"));
  TEST_ASSERT_EQUAL_UINT16(1103, parseDayMonth("3 noiembrie"));
  TEST_ASSERT_EQUAL_UINT16(512, parseDayMonth("12.05"));
  TEST_ASSERT_EQUAL_UINT16(531, parseDayMonth("05/31"));
  TEST_ASSERT_EQUAL_UINT16(229, parseDayMonth("Feb 29th"));
  TEST_ASSERT_EQUAL_UINT16(0, parseDayMonth("mai târziu la 12:30"));
  TEST_ASSERT_EQUAL_UINT16(0, parseDayMonth("31 February"));
  TEST_ASSERT_EQUAL_STRING("12 mai", dayMonthText(512, true).c_str());
  TEST_ASSERT_EQUAL_STRING("3 November", dayMonthText(1103, false).c_str());
}

static void test_memory_binary_and_json_roundtrip() {
  SoulMemory m;
  m.remember("Ziua Anei e pe 12 mai", FactKind::Person, FactSrc::Rule, kNow, 4, "Ana", 512);
  m.remember("I like tea", FactKind::Preference, FactSrc::User, kNow + 1);
  m.setBackup(true);
  const std::vector<uint8_t> b = m.serialize();
  SoulMemory n;
  TEST_ASSERT_TRUE(n.deserialize(b.data(), b.size()));
  TEST_ASSERT_EQUAL_INT(2, (int)n.size());
  TEST_ASSERT_TRUE(n.backup);
  TEST_ASSERT_EQUAL_STRING("Ziua Anei e pe 12 mai", n.at(0).text.c_str());
  TEST_ASSERT_EQUAL_UINT16(512, n.at(0).mmdd);
  TEST_ASSERT_EQUAL_STRING("Ana", n.at(0).subject.c_str());
  // corrupt / truncated blobs are refused and leave the memory as it was
  std::vector<uint8_t> bad = b;
  bad.resize(bad.size() - 3);
  TEST_ASSERT_FALSE(n.deserialize(bad.data(), bad.size()));
  bad = b;
  bad[12] = 99;  // a kind that does not exist
  TEST_ASSERT_FALSE(n.deserialize(bad.data(), bad.size()));
  TEST_ASSERT_EQUAL_INT(2, (int)n.size());
  // JSON: what the owner downloads (and the cloud backup); import skips secrets and junk
  const std::string j = m.exportJson();
  JsonDocument d;
  TEST_ASSERT_FALSE(deserializeJson(d, j));
  TEST_ASSERT_EQUAL_STRING("person", d["facts"][0]["kind"]);
  TEST_ASSERT_EQUAL_STRING("05-12", d["facts"][0]["date"]);
  SoulMemory k;
  TEST_ASSERT_EQUAL_INT(2, k.importJson(j, kNow, true));
  TEST_ASSERT_EQUAL_UINT16(512, k.at(0).mmdd);
  TEST_ASSERT_EQUAL_INT(1, k.importJson("{\"facts\":[{\"text\":\"My password is x1\"},{\"text\":42},{\"text\":\"Likes jazz\","
                                        "\"kind\":\"preference\",\"importance\":9}]}",
                                        kNow, false));
  TEST_ASSERT_EQUAL_INT(3, (int)k.size());
  TEST_ASSERT_EQUAL_INT(-1, k.importJson("not json", kNow, false));
}

static void test_memory_flash_ab_slots_survive_a_power_cut() {
  RamFlash io(128 * 1024);
  MemoryFlash fl(&io);
  TEST_ASSERT_EQUAL_INT(64 * 1024 - (int)MemoryFlash::kHeader, (int)fl.capacity());
  SoulMemory m;
  SoulMemory none;
  TEST_ASSERT_FALSE(fl.load(none));  // blank flash
  m.remember("My sister is Ana", FactKind::Person, FactSrc::User, kNow);
  TEST_ASSERT_TRUE(fl.save(m));
  TEST_ASSERT_EQUAL_INT(0, fl.slot());
  TEST_ASSERT_EQUAL_INT(1, io.erases);  // a small memory erases one 4 KB sector, not the whole slot
  m.remember("I like tea", FactKind::Preference, FactSrc::User, kNow);
  TEST_ASSERT_TRUE(fl.save(m));
  TEST_ASSERT_EQUAL_INT(1, fl.slot());  // the copies alternate (wear on two halves)
  {
    MemoryFlash again(&io);
    SoulMemory r;
    TEST_ASSERT_TRUE(again.load(r));
    TEST_ASSERT_EQUAL_INT(2, (int)r.size());
    TEST_ASSERT_EQUAL_INT(1, again.slot());
  }
  // a power cut in the middle of the next save: the blob is half written, the header never is
  m.remember("I work at the bakery", FactKind::Place, FactSrc::User, kNow);
  io.written = 0;
  io.cutAfter = 20;
  TEST_ASSERT_FALSE(fl.save(m));
  io.cutAfter = (size_t)-1;
  {
    MemoryFlash again(&io);
    SoulMemory r;
    TEST_ASSERT_TRUE(again.load(r));
    TEST_ASSERT_EQUAL_INT(2, (int)r.size());  // the last good copy
  }
  // a flipped bit in the newest copy: its CRC fails, the older one loads
  TEST_ASSERT_TRUE(fl.save(m));
  const size_t base = fl.slot() * 64 * 1024 + MemoryFlash::kHeader + 12;
  io.mem[base] ^= 0x01;
  {
    MemoryFlash again(&io);
    SoulMemory r;
    TEST_ASSERT_TRUE(again.load(r));
    TEST_ASSERT_TRUE(r.size() == 2 || r.size() == 3);
  }
  // a memory full of the longest facts still fits one slot (the byte budget evicts sooner than 512)
  SoulMemory full;
  std::string t(110, 'x');
  for (int i = 0; i < 600; ++i) full.remember(t + std::to_string(i), FactKind::Other, FactSrc::Ai, kNow, 2, "subject" + std::to_string(i));
  TEST_ASSERT_TRUE(full.size() < SoulMemory::kMax && full.size() > 300);
  TEST_ASSERT_EQUAL_INT((int)full.bytes(), (int)full.serialize().size());
  TEST_ASSERT_TRUE(full.serialize().size() <= fl.capacity());
  TEST_ASSERT_TRUE(fl.save(full));
  SoulMemory typical;  // 512 facts of a typical length fit the count cap
  for (int i = 0; i < 512; ++i) typical.remember("Fact number " + std::to_string(i) + " about the owner", FactKind::Other, FactSrc::Ai, kNow, 2);
  TEST_ASSERT_EQUAL_INT(512, (int)typical.size());
}

static void test_memory_saves_in_batches() {
  SoulMemory m;
  m.setClockMs(1000);
  TEST_ASSERT_FALSE(m.saveDue(1000));
  m.remember("a fact worth keeping", FactKind::Other, FactSrc::User, kNow);
  TEST_ASSERT_TRUE(m.dirty());
  TEST_ASSERT_FALSE(m.saveDue(2000));  // still talking: wait for 4 s of quiet
  TEST_ASSERT_TRUE(m.saveDue(5000));
  m.markSaved(5000);
  m.setClockMs(6000);
  m.remember("another fact", FactKind::Other, FactSrc::User, kNow);
  TEST_ASSERT_FALSE(m.saveDue(11000));  // quiet, but saved less than 20 s ago
  TEST_ASSERT_TRUE(m.saveDue(25001));
  // a burst of changes, never quiet: still written within 2 minutes
  m.markSaved(25001);
  for (uint32_t t = 30000; t < 160000; t += 1000) {
    m.setClockMs(t);
    m.remember("burst " + std::to_string(t), FactKind::Other, FactSrc::Ai, kNow);
  }
  TEST_ASSERT_TRUE(m.saveDue(160000));
}

// ------------------------------------------------------------ the offline rules ---

static void test_memory_rules_remember_forget_and_answer_offline() {
  SoulMemory m;
  MemoryAnswer a;
  TEST_ASSERT_TRUE(memoryAct(m, "Ține minte că ziua Anei e pe 12 mai", kNow, true, false, a));
  TEST_ASSERT_TRUE(a.remembered > 0);
  TEST_ASSERT_TRUE(has(a.say, "Am ținut minte"));
  TEST_ASSERT_EQUAL_UINT16(512, m.find(a.remembered)->mmdd);
  TEST_ASSERT_EQUAL_STRING("Ana", m.find(a.remembered)->subject.c_str());
  // "când e ziua Anei?" answered from memory, with the days left
  TEST_ASSERT_TRUE(memoryAct(m, "când e ziua Anei?", kNow, true, true, a));
  TEST_ASSERT_TRUE(a.question);
  TEST_ASSERT_TRUE(has(a.say, "Ana își serbează ziua pe 12 mai"));
  TEST_ASSERT_TRUE(memoryAct(m, "When is Ana's birthday?", kNow, false, false, a));
  TEST_ASSERT_TRUE(has(a.say, "12 May"));
  // offline, statements in passing are kept (implicit); online they go to the AI
  TEST_ASSERT_FALSE(memoryAct(m, "my brother is Mihai", kNow, false, false, a));
  TEST_ASSERT_TRUE(memoryAct(m, "my brother is Mihai", kNow, false, true, a));
  TEST_ASSERT_TRUE(has(a.say, "Remembered: My brother is Mihai"));
  TEST_ASSERT_TRUE(memoryAct(m, "who is Mihai?", kNow, false, true, a));
  TEST_ASSERT_TRUE(has(a.say, "brother"));
  TEST_ASSERT_TRUE(memoryAct(m, "My birthday is on the 3rd of November", kNow, false, true, a));
  TEST_ASSERT_TRUE(memoryAct(m, "when is my birthday?", kNow, false, true, a));
  TEST_ASSERT_TRUE(has(a.say, "Your birthday is on 3 November"));
  TEST_ASSERT_TRUE(memoryAct(m, "mă numesc Andu", kNow, true, true, a));
  TEST_ASSERT_TRUE(memoryAct(m, "cum mă cheamă?", kNow, true, true, a));
  TEST_ASSERT_TRUE(has(a.say, "Andu"));
  TEST_ASSERT_TRUE(memoryAct(m, "remember that my wifi is called Pisicuta5G", kNow, false, false, a));
  TEST_ASSERT_TRUE(memoryAct(m, "what's my wifi name?", kNow, false, false, a));
  TEST_ASSERT_TRUE(has(a.say, "Pisicuta5G"));
  // no secrets, ever
  TEST_ASSERT_TRUE(memoryAct(m, "what's my wifi password?", kNow, false, true, a));
  TEST_ASSERT_TRUE(has(a.say, "password manager"));
  const size_t n = m.size();
  TEST_ASSERT_TRUE(memoryAct(m, "remember that my PIN is 4512", kNow, false, false, a));
  TEST_ASSERT_EQUAL_INT((int)n, (int)m.size());
  // "remember to…" is a reminder, not a fact; "forget everything" needs Settings and a hold
  TEST_ASSERT_FALSE(memoryAct(m, "remember to buy milk", kNow, false, false, a));
  TEST_ASSERT_TRUE(memoryAct(m, "forget everything", kNow, false, false, a));
  TEST_ASSERT_EQUAL_INT((int)n, (int)m.size());
  TEST_ASSERT_TRUE(memoryAct(m, "uită ziua Anei", kNow, true, false, a));
  TEST_ASSERT_EQUAL_INT(1, a.forgotten);
  TEST_ASSERT_TRUE(memoryAct(m, "forget that my brother is Mihai", kNow, false, false, a));
  TEST_ASSERT_EQUAL_INT(1, a.forgotten);
  TEST_ASSERT_TRUE(memoryAct(m, "ce știi despre mine?", kNow, true, false, a));
  TEST_ASSERT_TRUE(has(a.say, "Țin minte"));
  // not about memory at all: the other rules / the AI take it
  TEST_ASSERT_FALSE(memoryAct(m, "set a timer for 10 minutes", kNow, false, true, a));
  TEST_ASSERT_FALSE(memoryAct(m, "what's the weather tomorrow?", kNow, false, false, a));
}

// ------------------------------------------------------------- the AI protocol ---

static void test_memory_ai_protocol_remember_forget_validated() {
  AiReply r = parseReply(
      "{\"say\":\"Nice, noted.\",\"actions\":[{\"type\":\"memory.remember\",\"text\":\"Ana is the owner's sister\","
      "\"kind\":\"person\",\"importance\":4},{\"type\":\"timer.start\",\"minutes\":5},{\"type\":\"memory.forget\","
      "\"text\":\"coffee\"},{\"type\":\"note.create\",\"text\":\"a\"},{\"type\":\"focus.start\",\"minutes\":25}]}");
  TEST_ASSERT_EQUAL_INT(3, (int)r.actions.size());  // memory ops do not use up the three actions
  TEST_ASSERT_EQUAL_INT(2, (int)r.memory.size());
  TEST_ASSERT_FALSE(r.memory[0].forget);
  TEST_ASSERT_EQUAL_INT((int)FactKind::Person, (int)r.memory[0].kind);
  TEST_ASSERT_EQUAL_INT(4, r.memory[0].importance);
  TEST_ASSERT_TRUE(r.memory[1].forget);
  TEST_ASSERT_EQUAL_INT(0, r.rejected);
  // extra keys, secrets, a blank forget, a bad kind / importance: dropped and counted
  r = parseReply(
      "{\"say\":\"x\",\"actions\":[{\"type\":\"memory.remember\",\"text\":\"x\",\"to\":\"all\"},{\"type\":\"memory.remember\","
      "\"text\":\"Password is hunter2\"},{\"type\":\"memory.forget\",\"text\":\"a\"},{\"type\":\"memory.remember\","
      "\"text\":\"ok\",\"kind\":\"secret\"},{\"type\":\"memory.remember\",\"text\":\"ok\",\"importance\":9}]}");
  TEST_ASSERT_EQUAL_INT(0, (int)r.memory.size());
  TEST_ASSERT_EQUAL_INT(5, r.rejected);
  // the prompt teaches the two actions and carries the block; the schema allows them
  AiConfig cfg;
  cfg.mode = AiMode::Claude;
  cfg.anthropicKey = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz";
  AiContext ctx;
  ctx.memory = "What SOUL knows about you (...):\n- My sister is Ana";
  HttpRequest rq;
  TEST_ASSERT_EQUAL_INT((int)AiErr::None, (int)buildRequest(cfg, ctx, {}, "hi", rq));
  JsonDocument d;
  TEST_ASSERT_FALSE(deserializeJson(d, rq.body, DeserializationOption::NestingLimit(24)));
  const char* sys = d["system"];
  TEST_ASSERT_NOT_NULL(strstr(sys, "memory.remember"));
  TEST_ASSERT_NOT_NULL(strstr(sys, "My sister is Ana"));
  TEST_ASSERT_TRUE(has(rq.body, "\"const\":\"memory.forget\""));
  cfg.mode = AiMode::ChatGpt;
  cfg.openaiKey = "sk-proj-abcdefghijklmnopqrstuvwxyz";
  buildRequest(cfg, ctx, {}, "hi", rq);
  TEST_ASSERT_TRUE(has(rq.body, "My sister is Ana"));
  // SOUL Cloud's and SOUL Bridge's form {"op","text"} -> the same validated ops
  MemOp op;
  TEST_ASSERT_TRUE(memOpFrom("remember", "Mihai is the owner's brother", "person", 3, op));
  TEST_ASSERT_FALSE(memOpFrom("remember", "my pin is 1234", "", 0, op));
  TEST_ASSERT_FALSE(memOpFrom("erase", "x", "", 0, op));
  CloudLink link;
  const char* reply =
      "{\"v\":1,\"t\":\"reply\",\"re\":\"a1\",\"say\":\"Got it.\",\"memory\":[{\"op\":\"remember\",\"text\":\"Likes jazz\","
      "\"kind\":\"preference\"},{\"op\":\"forget\",\"text\":\"tea\"}]}";
  TEST_ASSERT_EQUAL_INT((int)CloudLink::Msg::Reply, (int)link.feed(reply, strlen(reply)));
  TEST_ASSERT_EQUAL_INT(2, (int)link.reply.reply.memory.size());
  // the ask frame carries the block in ctx.memory
  const std::string ask = CloudLink::ask("a1", "hi", "en", "", -1, {}, "What SOUL knows about you:\n- Likes jazz");
  TEST_ASSERT_TRUE(has(ask, "\"memory\":\"What SOUL knows"));
  // the backup goes up in parts, each a valid frame under 10 KB
  std::string big = "{\"v\":1,\"facts\":[";
  for (int i = 0; i < 300; ++i) big += std::string(i ? "," : "") + "{\"text\":\"fact ăîș " + std::to_string(i) + "\"}";
  big += "]}";
  const std::vector<std::string> parts = CloudLink::memoryBackup(big, 7, false);
  TEST_ASSERT_TRUE(parts.size() >= 2);
  std::string joined;
  for (const std::string& p : parts) {
    TEST_ASSERT_TRUE(p.size() < CloudLink::kMaxOut);
    JsonDocument pd;
    TEST_ASSERT_FALSE(deserializeJson(pd, p));
    TEST_ASSERT_EQUAL_STRING("memory.backup", pd["t"]);
    joined += pd["data"].as<const char*>();
  }
  TEST_ASSERT_EQUAL_STRING(big.c_str(), joined.c_str());
  TEST_ASSERT_TRUE(has(CloudLink::memoryBackup("", 0, true)[0], "\"off\":true"));
}

// ------------------------------------------------------------------ the OS hooks ---

static void test_memory_os_remembers_with_undo_and_feeds_every_ai() {
  Dev d(AiMode::Claude);
  d.os.ask("remember that my sister is Ana");
  TEST_ASSERT_FALSE(d.os.thinking());  // on the device: no AI round trip
  TEST_ASSERT_EQUAL_INT(1, (int)d.mem.size());
  TEST_ASSERT_TRUE(has(d.os.lastReply().say, "Remembered: My sister is Ana"));
  TEST_ASSERT_EQUAL_STRING("Ana", d.mem.at(0).subject.c_str());
  d.tap(233, 30);  // the toast on the top rim: undo
  TEST_ASSERT_EQUAL_INT(0, (int)d.mem.size());
  d.os.ask("remember that my sister is Ana");
  d.run(6.0f);  // the toast is gone: a tap up there no longer undoes
  d.os.back();
  // the next question to Claude carries what SOUL knows
  d.os.ask("plan a gift for my sister");
  AiJob job;
  TEST_ASSERT_TRUE(d.os.popAiJob(job));
  TEST_ASSERT_TRUE(has(job.ctx.memory, "My sister is Ana"));
  TEST_ASSERT_TRUE(has(systemPrompt(job.ctx), "My sister is Ana"));
  // the AI proposes a fact: kept, chip + toast with undo
  AiOutcome o;
  o.reply = parseReply(
      "{\"say\":\"A scarf?\",\"actions\":[{\"type\":\"memory.remember\",\"text\":\"Ana likes green scarves\","
      "\"kind\":\"preference\"}]}");
  o.raw = "{}";
  d.os.aiResult(o);
  TEST_ASSERT_EQUAL_INT(2, (int)d.mem.size());
  TEST_ASSERT_EQUAL_INT((int)FactSrc::Ai, (int)d.mem.at(1).src);
  d.tap(233, 30);
  TEST_ASSERT_EQUAL_INT(1, (int)d.mem.size());
  // offline: answered from memory, at once
  NetInfo n;
  n.configured = true;
  n.connected = false;
  n.saved = 1;
  d.os.setNet(n);
  d.os.ask("Ana's birthday is May 12");
  TEST_ASSERT_EQUAL_INT(2, (int)d.mem.size());
  d.os.ask("when is Ana's birthday?");
  TEST_ASSERT_TRUE(has(d.os.lastReply().say, "12 May"));
  TEST_ASSERT_EQUAL_INT(0, d.os.queuedAsks());
}

static void test_memory_settings_screen_lists_searches_forgets_and_backs_up() {
  Dev d(AiMode::Claude);
  d.mem.remember("My sister is Ana", FactKind::Person, FactSrc::User, kNow - 10, 4, "Ana");
  d.mem.remember("I like tea", FactKind::Preference, FactSrc::User, kNow - 5);
  d.mem.remember("I work at the bakery", FactKind::Place, FactSrc::Ai, kNow);
  d.mem.remember("Mihai is my brother", FactKind::Person, FactSrc::Rule, kNow + 1, 4, "Mihai");
  d.os.go(View::Settings);
  d.run(0.3f);
  for (int i = 0; i < 2; ++i) {  // Memory is the last row (page 3)
    d.fx = d.g.s(233);
    d.finger = true;
    for (int k = 0; k <= 6; ++k) {
      d.fy = d.g.s(380 - 230.0f * k / 6);
      d.step();
    }
    d.finger = false;
    d.run(0.4f);
  }
  d.tap(233, 172 + 3 * 62);
  TEST_ASSERT_EQUAL_INT((int)View::Memory, (int)d.os.view());
  TEST_ASSERT_EQUAL_STRING("memory", viewName(View::Memory));
  // it draws inside the disc
  std::vector<uint16_t> fb(480 * 480, 0);
  Canvas cv(480, 480, fb.data());
  auto draw = [&](int& outside) {  // the words and glass stay inside the round panel (as on Settings)
    std::fill(fb.begin(), fb.end(), 0);
    d.os.render(cv);
    int lit = 0;
    outside = 0;
    for (int y = 0; y < 480; ++y)
      for (int x = 0; x < 480; ++x)
        if (fb[(size_t)y * 480 + x]) {
          ++lit;
          const float dx = x - 239.5f, dy = y - 239.5f;
          if (dx * dx + dy * dy > 236.0f * 236.0f) ++outside;
        }
    return lit;
  };
  int outM = 0, outS = 0;
  TEST_ASSERT_TRUE(draw(outM) > 1000);
  d.os.go(View::Settings);
  draw(outS);
  char msg[64];
  snprintf(msg, sizeof msg, "memory %d / settings %d px on the rim", outM, outS);
  TEST_MESSAGE(msg);
  TEST_ASSERT_TRUE(outM <= outS + 200);
  d.os.go(View::Memory);
  d.run(0.3f);
  // newest first: tap the first row -> the fact; hold Forget -> gone
  d.tap(233, 160);
  d.os.render(cv);
  d.hold(233, 396, 1.4f);
  TEST_ASSERT_EQUAL_INT(3, (int)d.mem.size());
  TEST_ASSERT_NULL(d.mem.find(4));
  TEST_ASSERT_EQUAL_INT((int)View::Memory, (int)d.os.view());
  // search on the round keyboard
  d.tap(160, 344);
  TEST_ASSERT_EQUAL_INT((int)View::Keyboard, (int)d.os.view());
  // backup needs a paired account; once on, an export goes to the cloud
  d.os.go(View::Memory);
  d.run(0.3f);
  d.tap(306, 344);
  TEST_ASSERT_FALSE(d.mem.backup);
  NetInfo n;
  n.configured = n.connected = true;
  n.relay = n.paired = true;
  d.os.setNet(n);
  d.tap(306, 344);
  TEST_ASSERT_TRUE(d.mem.backup);
  d.run(0.2f);
  CloudOut co;
  bool sent = false;
  while (d.os.popCloudOut(co))
    if (co.kind == CloudOut::MemoryBackup && !co.paused && has(co.text, "My sister is Ana")) sent = true;
  TEST_ASSERT_TRUE(sent);
  d.tap(306, 344);  // off: the cloud copy is deleted
  d.run(0.2f);
  sent = false;
  while (d.os.popCloudOut(co))
    if (co.kind == CloudOut::MemoryBackup && co.paused) sent = true;
  TEST_ASSERT_TRUE(sent);
  // hold "Forget all": wiped
  d.hold(233, 398, 1.4f);
  TEST_ASSERT_EQUAL_INT(0, (int)d.mem.size());
}

static void test_memory_bridge_carries_the_block_and_returns_ops() {
  BridgeServer b;
  b.deviceId = "soul-a1b2c3d4e5f6";
  const std::string code = b.newCode(0);
  b.onOpen(1, 0);
  const std::string pair = "{\"t\":\"bridge.pair\",\"v\":1,\"code\":\"" + code + "\"}";
  b.onText(1, pair.data(), pair.size(), 10);
  BridgeOut out;
  std::string token;
  while (b.nextOut(out)) {
    JsonDocument d;
    if (!out.frame.empty() && !deserializeJson(d, out.frame) && d["token"].is<const char*>()) token = d["token"].as<const char*>();
  }
  b.onClose(1);
  b.onOpen(2, 20);
  const std::string hello = "{\"t\":\"bridge.hello\",\"v\":1,\"token\":\"" + token + "\"}";
  b.onText(2, hello.data(), hello.size(), 20);
  while (b.nextOut(out)) {
  }
  TEST_ASSERT_TRUE(b.online());
  TEST_ASSERT_TRUE(b.ask("plan a gift", false, "2026-09-25T18:38", 20, "What SOUL knows about you:\n- My sister is Ana"));
  std::string id;
  while (b.nextOut(out)) {
    JsonDocument d;
    deserializeJson(d, out.frame);
    if (!strcmp(d["t"] | "", "ask")) {
      id = d["id"].as<const char*>();
      TEST_ASSERT_TRUE(has(d["memory"].as<const char*>(), "My sister is Ana"));
    }
  }
  TEST_ASSERT_FALSE(id.empty());
  const std::string ans = "{\"t\":\"answer\",\"id\":\"" + id +
                          "\",\"text\":\"A scarf.\",\"actions\":[],\"memory\":[{\"op\":\"remember\",\"text\":\"Ana likes "
                          "scarves\"},{\"op\":\"remember\",\"text\":\"my password is x\"}]}";
  b.onText(2, ans.data(), ans.size(), 30);
  AiOutcome o;
  TEST_ASSERT_TRUE(b.pollAnswer(o));
  TEST_ASSERT_EQUAL_INT(1, (int)o.reply.memory.size());
  TEST_ASSERT_EQUAL_INT(1, o.reply.rejected);
}

void runMemoryTests() {
  RUN_TEST(test_memory_remember_dedupes_refuses_secrets_and_caps);
  RUN_TEST(test_memory_retrieval_ranks_with_synonyms_recency_and_budget);
  RUN_TEST(test_memory_dates_parse_en_ro_and_numeric);
  RUN_TEST(test_memory_binary_and_json_roundtrip);
  RUN_TEST(test_memory_flash_ab_slots_survive_a_power_cut);
  RUN_TEST(test_memory_saves_in_batches);
  RUN_TEST(test_memory_rules_remember_forget_and_answer_offline);
  RUN_TEST(test_memory_ai_protocol_remember_forget_validated);
  RUN_TEST(test_memory_os_remembers_with_undo_and_feeds_every_ai);
  RUN_TEST(test_memory_settings_screen_lists_searches_forgets_and_backs_up);
  RUN_TEST(test_memory_bridge_carries_the_block_and_returns_ops);
}
