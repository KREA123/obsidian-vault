#include "VoiceCommands.h"

#include "Lines.h"
#include "Os.h"  // View

namespace suflet {

namespace {

using C = VoiceCmd;

// Phrases MultiNet7 listens for. Plain words, 2..6 of them work best (esp-sr docs: avoid one-syllable
// commands; similar phrases for one command help); at most 200 phrases / 300 commands per model.
const VoicePhrase kPhrases[] = {
    {C::WhatTime, "what time is it"},
    {C::WhatTime, "tell me the time"},
    {C::WhatDay, "what day is it"},
    {C::WhatDay, "what is the date today"},
    {C::NewAlarm, "set an alarm"},
    {C::NewAlarm, "new alarm"},
    {C::AlarmAt6, "wake me up at six"},
    {C::AlarmAt7, "wake me up at seven"},
    {C::AlarmAt8, "wake me up at eight"},
    {C::StopAlarm, "stop the alarm"},
    {C::StopAlarm, "turn it off"},
    {C::Snooze, "snooze"},
    {C::Snooze, "five more minutes"},
    {C::Timer1, "timer one minute"},
    {C::Timer3, "timer three minutes"},
    {C::Timer5, "timer five minutes"},
    {C::Timer10, "timer ten minutes"},
    {C::Timer15, "timer fifteen minutes"},
    {C::Timer30, "timer thirty minutes"},
    {C::StopTimer, "stop the timer"},
    {C::StopTimer, "cancel the timer"},
    {C::PauseTimer, "pause the timer"},
    {C::Focus25, "start focus"},
    {C::Focus25, "focus mode"},
    {C::TakeNote, "take a note"},
    {C::TakeNote, "new note"},
    {C::VolumeUp, "volume up"},
    {C::VolumeUp, "louder please"},
    {C::VolumeDown, "volume down"},
    {C::VolumeDown, "quieter please"},
    {C::Mute, "mute the sound"},
    {C::Brighter, "brighter screen"},
    {C::Dimmer, "dimmer screen"},
    {C::Sleep, "go to sleep"},
    {C::Sleep, "good night soul"},
    {C::Wake, "wake up soul"},
    {C::Wake, "good morning soul"},
    {C::Yes, "yes please"},
    {C::Yes, "yes do it"},
    {C::No, "no thank you"},
    {C::No, "no don't"},
    {C::GoHome, "go home"},
    {C::GoBack, "go back"},
    {C::OpenAlarms, "open alarms"},
    {C::OpenTimer, "open timer"},
    {C::OpenNotes, "open notes"},
    {C::OpenNotes, "read my notes"},
    {C::OpenToday, "open today"},
    {C::OpenToday, "what is my day"},
    {C::OpenSettings, "open settings"},
    {C::OpenMemory, "open memory"},
    {C::WhatDoYouRemember, "what do you remember"},
    {C::HowAreYou, "how are you"},
    {C::ThankYou, "thank you soul"},
    {C::TellJoke, "tell me a joke"},
};

}  // namespace

const VoicePhrase* voicePhrases(size_t& n) {
  n = sizeof(kPhrases) / sizeof(kPhrases[0]);
  return kPhrases;
}

const char* voiceCmdName(VoiceCmd c) {
  static const char* const k[] = {"none",        "what_time",   "what_day",   "new_alarm",   "alarm_6",   "alarm_7",
                                  "alarm_8",     "stop_alarm",  "snooze",     "timer_1",     "timer_3",   "timer_5",
                                  "timer_10",    "timer_15",    "timer_30",   "stop_timer",  "pause_timer", "focus_25",
                                  "take_note",   "volume_up",   "volume_down", "mute",       "brighter",  "dimmer",
                                  "sleep",       "wake",        "yes",        "no",          "home",      "back",
                                  "open_alarms", "open_timer",  "open_notes", "open_today",  "open_settings",
                                  "open_memory", "what_do_you_remember", "how_are_you", "thank_you", "tell_joke"};
  static_assert(sizeof(k) / sizeof(k[0]) == (unsigned)VoiceCmd::Count, "voice command names");
  return (unsigned)c < (unsigned)VoiceCmd::Count ? k[(int)c] : "?";
}

VoiceAction voiceAction(VoiceCmd c) {
  VoiceAction a;
  using K = VoiceAction;
  auto mk = [](VoiceAction::Kind k, int arg = 0) {
    VoiceAction v;
    v.kind = k;
    v.arg = arg;
    return v;
  };
  switch (c) {
    case C::WhatTime: return mk(K::SayTime);
    case C::WhatDay: return mk(K::SayDate);
    case C::NewAlarm: return mk(K::OpenView, (int)View::Dial);
    case C::AlarmAt6: return mk(K::AlarmAt, 6);
    case C::AlarmAt7: return mk(K::AlarmAt, 7);
    case C::AlarmAt8: return mk(K::AlarmAt, 8);
    case C::StopAlarm: return mk(K::StopRinging);
    case C::Snooze: return mk(K::Snooze);
    case C::Timer1: return mk(K::TimerStart, 1);
    case C::Timer3: return mk(K::TimerStart, 3);
    case C::Timer5: return mk(K::TimerStart, 5);
    case C::Timer10: return mk(K::TimerStart, 10);
    case C::Timer15: return mk(K::TimerStart, 15);
    case C::Timer30: return mk(K::TimerStart, 30);
    case C::StopTimer: return mk(K::TimerStop);
    case C::PauseTimer: return mk(K::TimerPause);
    case C::Focus25: return mk(K::Focus, 25);
    case C::TakeNote: return mk(K::Note);
    case C::VolumeUp: return mk(K::Volume, 1);
    case C::VolumeDown: return mk(K::Volume, -1);
    case C::Mute: return mk(K::Volume, 0);
    case C::Brighter: return mk(K::Brightness, 1);
    case C::Dimmer: return mk(K::Brightness, -1);
    case C::Sleep: return mk(K::Sleep);
    case C::Wake: return mk(K::Wake);
    case C::Yes: return mk(K::Answer, 1);
    case C::No: return mk(K::Answer, 0);
    case C::GoHome: return mk(K::Home);
    case C::GoBack: return mk(K::Back);
    case C::OpenAlarms: return mk(K::OpenView, (int)View::Alarms);
    case C::OpenTimer: return mk(K::OpenView, (int)View::Timer);
    case C::OpenNotes: return mk(K::OpenView, (int)View::Notes);
    case C::OpenToday: return mk(K::OpenView, (int)View::Today);
    case C::OpenSettings: return mk(K::OpenView, (int)View::Settings);
    case C::OpenMemory: return mk(K::OpenView, (int)View::Memory);
    case C::WhatDoYouRemember: return mk(K::Remember);
    case C::HowAreYou: return mk(K::Chat, (int)LineTopic::HowAreYou);
    case C::ThankYou: return mk(K::Chat, (int)LineTopic::Thanks);
    case C::TellJoke: return mk(K::Chat, (int)LineTopic::Joke);
    default: return a;
  }
}

}  // namespace suflet
