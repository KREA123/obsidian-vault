// Offline voice commands (VoiceCommands.h: the MultiNet phrase table and command -> action mapping, run by
// Os::voiceCommand) and the offline personality lines (Lines.h).
#include <unity.h>

#include <cctype>
#include <cstdio>
#include <cstring>
#include <set>
#include <string>

#include "Lines.h"
#include "Os.h"
#include "VoiceCommands.h"

using namespace suflet;

namespace {

const uint32_t kNow = 1790359080u;  // a Friday, 17:58 local

struct Dev {
  Brain brain{Personality::fromSeed(0xC0FFEE), 7};
  Alarms alarms;
  SoulMemory mem;
  Os os{&alarms};
  explicit Dev(AiMode mode = AiMode::Claude, bool connected = true) {
    os.settings().booted = 1;
    os.settings().ai = (uint8_t)mode;
    BirthInfo b;
    b.design = 5;
    b.chip = "C0:FF:EE:12:34:56";
    b.seed = 1234;
    os.setMemory(&mem);
    os.begin(displays::kLcd28, b);
    NetInfo n;
    n.configured = n.connected = connected;
    n.keyClaude = true;
    os.setNet(n);
    os.setClock(kNow);
  }
  void run(float s) {
    for (int i = 0; i < (int)(s * 30 + 0.5f); ++i) os.update(1.0f / 30, brain);
  }
  bool hasCmd(OsCmd want) {
    OsCmd c;
    bool found = false;
    while (os.popCmd(c))
      if (c == want) found = true;
    return found;
  }
};

bool has(const std::string& s, const char* part) { return s.find(part) != std::string::npos; }

}  // namespace

static void test_voice_phrase_table_fits_multinet() {
  size_t n = 0;
  const VoicePhrase* p = voicePhrases(n);
  TEST_ASSERT_TRUE(n >= 30 && n <= 200);  // MultiNet7: up to 200 phrases
  std::set<std::string> seen;
  std::set<int> cmds;
  for (size_t i = 0; i < n; ++i) {
    const std::string t = p[i].text;
    TEST_ASSERT_TRUE_MESSAGE(seen.insert(t).second, t.c_str());  // no duplicate phrase
    cmds.insert((int)p[i].cmd);
    int words = 1;
    for (char c : t) {
      TEST_ASSERT_TRUE_MESSAGE(islower((unsigned char)c) || c == ' ' || c == '\'', t.c_str());  // plain English for g2p
      words += c == ' ';
    }
    TEST_ASSERT_TRUE(words <= 6);
  }
  // every command can be said, the ids are the enum (MultiNet command id = (int)VoiceCmd)
  TEST_ASSERT_EQUAL_INT((int)VoiceCmd::Count - 1, (int)cmds.size());
  TEST_ASSERT_TRUE((int)VoiceCmd::Count - 1 >= 30);
  TEST_ASSERT_EQUAL_STRING("timer_10", voiceCmdName(VoiceCmd::Timer10));
}

static void test_voice_commands_map_to_actions() {
  for (int i = 1; i < (int)VoiceCmd::Count; ++i)
    TEST_ASSERT_TRUE_MESSAGE(voiceAction(i).kind != VoiceAction::None, voiceCmdName((VoiceCmd)i));
  TEST_ASSERT_EQUAL_INT(VoiceAction::None, voiceAction(0).kind);
  TEST_ASSERT_EQUAL_INT(VoiceAction::None, voiceAction(999).kind);
  TEST_ASSERT_EQUAL_INT(VoiceAction::TimerStart, voiceAction(VoiceCmd::Timer10).kind);
  TEST_ASSERT_EQUAL_INT(10, voiceAction(VoiceCmd::Timer10).arg);
  TEST_ASSERT_EQUAL_INT(7, voiceAction(VoiceCmd::AlarmAt7).arg);
  TEST_ASSERT_EQUAL_INT((int)View::Memory, voiceAction(VoiceCmd::OpenMemory).arg);
  TEST_ASSERT_EQUAL_INT(VoiceAction::Answer, voiceAction(VoiceCmd::No).kind);
  TEST_ASSERT_EQUAL_INT(0, voiceAction(VoiceCmd::Mute).arg);
  TEST_ASSERT_EQUAL_INT((int)LineTopic::Joke, voiceAction(VoiceCmd::TellJoke).arg);
  TEST_ASSERT_TRUE(kVoiceSrPsramNeed > 3u * 1024u * 1024u && kVoiceSrPsramNeed < 6u * 1024u * 1024u);
}

static void test_voice_commands_run_on_the_device_without_ai() {
  Dev d(AiMode::Claude, false);  // offline
  d.os.voiceCommand((int)VoiceCmd::WhatTime);
  char hm[8];
  snprintf(hm, sizeof hm, "%02u:%02u", (unsigned)(kNow % 86400 / 3600), (unsigned)(kNow % 3600 / 60));
  TEST_ASSERT_TRUE(has(d.os.lastReply().say, hm));
  TEST_ASSERT_FALSE(d.os.thinking());
  d.os.voiceCommand((int)VoiceCmd::WhatDay);
  TEST_ASSERT_TRUE(has(d.os.lastReply().say, "2026"));
  d.os.voiceCommand((int)VoiceCmd::Timer5);
  TEST_ASSERT_EQUAL_INT(300, d.os.timerLeft());
  d.os.voiceCommand((int)VoiceCmd::StopTimer);
  TEST_ASSERT_EQUAL_INT(-1, d.os.timerLeft());
  d.os.voiceCommand((int)VoiceCmd::AlarmAt7);
  TEST_ASSERT_EQUAL_INT(1, d.alarms.count());
  TEST_ASSERT_EQUAL_INT(7, d.alarms.at(0).hour);
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::SaveAlarms));
  // the alarm rings: "stop the alarm"
  d.os.alarmDue(0);
  TEST_ASSERT_EQUAL_INT((int)View::Ringing, (int)d.os.view());
  d.os.voiceCommand((int)VoiceCmd::StopAlarm);
  TEST_ASSERT_EQUAL_INT((int)View::Home, (int)d.os.view());
  // volume and brightness
  const float v = d.os.volume();
  d.os.voiceCommand((int)VoiceCmd::VolumeDown);
  TEST_ASSERT_TRUE(d.os.volume() < v);
  d.os.voiceCommand((int)VoiceCmd::VolumeUp);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, v, d.os.volume());
  d.os.voiceCommand((int)VoiceCmd::Mute);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, d.os.volume());
  d.os.voiceCommand((int)VoiceCmd::Brighter);
  TEST_ASSERT_EQUAL_INT(3, d.os.settings().bright);
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::SaveSettings));
  // open apps, back, home
  d.os.voiceCommand((int)VoiceCmd::OpenMemory);
  TEST_ASSERT_EQUAL_INT((int)View::Memory, (int)d.os.view());
  d.os.voiceCommand((int)VoiceCmd::GoBack);
  TEST_ASSERT_EQUAL_INT((int)View::Settings, (int)d.os.view());
  d.os.voiceCommand((int)VoiceCmd::NewAlarm);
  TEST_ASSERT_EQUAL_INT((int)View::Dial, (int)d.os.view());
  d.os.voiceCommand((int)VoiceCmd::GoHome);
  TEST_ASSERT_EQUAL_INT((int)View::Home, (int)d.os.view());
  d.os.voiceCommand((int)VoiceCmd::Sleep);
  TEST_ASSERT_TRUE(d.os.sleepRequested());
  TEST_ASSERT_FALSE(d.os.sleepRequested());
  // a joke offline, from the hand-written lines
  d.os.voiceCommand((int)VoiceCmd::TellJoke);
  TEST_ASSERT_TRUE(d.os.lastReply().say.size() > 10);
  // what do you remember: the memory, said briefly
  d.mem.remember("My sister is Ana", FactKind::Person, FactSrc::User, kNow);
  d.os.voiceCommand((int)VoiceCmd::WhatDoYouRemember);
  TEST_ASSERT_TRUE(has(d.os.lastReply().say, "My sister is Ana"));
}

static void test_voice_yes_never_approves_claude_but_no_declines() {
  Dev d(AiMode::Claude);
  ClaudeInfo ci;
  ci.linked = true;
  ci.prompt = true;
  ci.tool = "Bash";
  d.os.setClaude(ci);
  d.run(0.2f);
  d.hasCmd(OsCmd::None);
  d.os.voiceCommand((int)VoiceCmd::Yes);
  TEST_ASSERT_FALSE(d.hasCmd(OsCmd::ClaudeApprove));  // a voice in the room is not the owner's touch
  d.os.voiceCommand((int)VoiceCmd::No);
  TEST_ASSERT_TRUE(d.hasCmd(OsCmd::ClaudeDeny));
}

static void test_lines_cover_every_topic_in_both_languages() {
  TEST_ASSERT_TRUE(lineCount() >= 110);  // x 2 languages: a few hundred lines
  for (int t = 0; t < (int)LineTopic::Count; ++t) {
    TEST_ASSERT_TRUE(lineCount((LineTopic)t, false) >= 3);
    TEST_ASSERT_TRUE(lineCount((LineTopic)t, true) >= 3);
  }
  // deterministic for a seed, varied across seeds, short enough for the round screen
  TEST_ASSERT_EQUAL_STRING(pickLine(LineTopic::Joke, false, 7), pickLine(LineTopic::Joke, false, 7));
  std::set<std::string> v;
  for (uint32_t s = 0; s < 50; ++s) {
    const std::string l = pickLine(LineTopic::Hello, true, s, 1);
    TEST_ASSERT_TRUE(l.size() < 120);
    v.insert(l);
  }
  TEST_ASSERT_TRUE(v.size() >= 4);
  std::string say, face;
  TEST_ASSERT_TRUE(smallTalk("Bună!", true, 14, 3, say, face));
  TEST_ASSERT_TRUE(smallTalk("thank you!", false, 14, 3, say, face));
  TEST_ASSERT_EQUAL_STRING("love", face.c_str());
  TEST_ASSERT_TRUE(smallTalk("Noapte bună", true, 23, 3, say, face));
  TEST_ASSERT_TRUE(smallTalk("ce faci?", true, 14, 3, say, face));
  TEST_ASSERT_TRUE(smallTalk("I'm sad", false, 14, 3, say, face));
  TEST_ASSERT_EQUAL_STRING("sad", face.c_str());
  TEST_ASSERT_TRUE(smallTalk("are you an AI?", false, 14, 3, say, face));
  TEST_ASSERT_TRUE(has(say, "AI"));
  TEST_ASSERT_FALSE(smallTalk("why is the sky blue?", false, 14, 3, say, face));
  TEST_ASSERT_FALSE(smallTalk("thanks, now please explain to me how the moon causes the tides", false, 14, 3, say, face));
}

static void test_lines_answer_small_talk_offline_but_not_online() {
  Dev off(AiMode::None);
  off.os.ask("hello");
  TEST_ASSERT_FALSE(off.os.lastReply().say.empty());
  TEST_ASSERT_EQUAL_INT(0, (int)off.os.notes().size());  // small talk is not kept as a note
  off.os.ask("the meaning of life");                     // anything else still is (No AI)
  TEST_ASSERT_EQUAL_INT(1, (int)off.os.notes().size());
  Dev on(AiMode::Claude);
  on.os.ask("hello");
  TEST_ASSERT_TRUE(on.os.thinking());  // online: Claude answers
}

void runVoiceTests() {
  RUN_TEST(test_voice_phrase_table_fits_multinet);
  RUN_TEST(test_voice_commands_map_to_actions);
  RUN_TEST(test_voice_commands_run_on_the_device_without_ai);
  RUN_TEST(test_voice_yes_never_approves_claude_but_no_declines);
  RUN_TEST(test_lines_cover_every_topic_in_both_languages);
  RUN_TEST(test_lines_answer_small_talk_offline_but_not_online);
}
