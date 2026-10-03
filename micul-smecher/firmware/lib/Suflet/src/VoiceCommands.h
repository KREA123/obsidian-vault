// Offline voice commands (docs/10-SOUL-MEMORY.md §7): ~30 English commands recognised ON the device by
// Espressif's ESP-SR MultiNet7 (src/voice_sr.cpp, build `lcd28_voice`), no internet, no cloud. This file is the
// hardware-free part: the phrase table handed to MultiNet (plain lower-case English: the Arduino ESP_SR
// wrapper turns it into phonemes with flite_g2p at start-up) and the command -> action mapping SoulOS runs
// (Os::voiceCommand), unit-tested on the PC.
//
// MultiNet only knows English and Chinese (no Romanian model exists, esp-sr 2.x): Romanian speakers use
// the English commands offline, or talk freely when online (the cloud transcription path).
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace suflet {

enum class VoiceCmd : uint8_t {
  None,
  WhatTime,
  WhatDay,
  NewAlarm,      // opens the Rim-Dial
  AlarmAt6,
  AlarmAt7,
  AlarmAt8,
  StopAlarm,     // stop a ringing alarm / timer
  Snooze,
  Timer1,
  Timer3,
  Timer5,
  Timer10,
  Timer15,
  Timer30,
  StopTimer,
  PauseTimer,
  Focus25,
  TakeNote,      // opens the note field (dictation when online)
  VolumeUp,
  VolumeDown,
  Mute,
  Brighter,
  Dimmer,
  Sleep,
  Wake,
  Yes,
  No,
  GoHome,
  GoBack,
  OpenAlarms,
  OpenTimer,
  OpenNotes,
  OpenToday,
  OpenSettings,
  OpenMemory,
  WhatDoYouRemember,
  HowAreYou,
  ThankYou,
  TellJoke,
  Count
};

struct VoicePhrase {
  VoiceCmd cmd;
  const char* text;  // what MultiNet listens for (several phrases may map to one command)
};

// The whole table (phrases for every command), in a fixed order: the MultiNet command id IS (int)VoiceCmd.
const VoicePhrase* voicePhrases(size_t& n);
const char* voiceCmdName(VoiceCmd c);  // "what_time", ...

// What SoulOS does for a command (Os::voiceCommand runs it).
struct VoiceAction {
  enum Kind : uint8_t {
    None,
    SayTime,
    SayDate,
    OpenView,    // view = the View to open (as an int, Os.h's enum)
    AlarmAt,     // hour (minute 0, once)
    StopRinging,
    Snooze,
    TimerStart,  // minutes
    TimerStop,
    TimerPause,
    Focus,       // minutes
    Note,
    Volume,      // delta: +1 / -1, 0 = mute
    Brightness,  // delta: +1 / -1
    Sleep,
    Wake,
    Answer,      // yes = delta 1, no = delta 0 (a Claude request, an Accept, a pairing question)
    Home,
    Back,
    Remember,    // "what do you remember": the memory, said briefly
    Chat,        // a personality line: topic (LineTopic in Lines.h)
  } kind = None;
  int arg = 0;
};
VoiceAction voiceAction(VoiceCmd c);
inline VoiceAction voiceAction(int id) {
  return id > 0 && id < (int)VoiceCmd::Count ? voiceAction((VoiceCmd)id) : VoiceAction();
}

// Resource budget of the on-device recogniser (esp-sr 2.5.x benchmarks, ESP32-S3 @ 240 MHz), for the
// fallback decision: below this much free PSRAM SOUL does not start MultiNet and keeps voice cloud-only.
constexpr uint32_t kVoiceSrPsramNeed = 4200u * 1024u;  // MultiNet7 ~2.9 MB + AFE low-cost ~0.74 MB + WakeNet9 ~0.32 MB + margin

}  // namespace suflet
