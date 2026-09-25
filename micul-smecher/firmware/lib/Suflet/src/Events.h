#pragma once
#include <stdint.h>

namespace suflet {

// Everything the character can perceive. Sensors (touch, IMU, clock) and
// the AI link all speak this language, so the Brain never touches hardware.
enum class Ev : uint8_t {
  None,
  Tap,
  DoubleTap,
  HoldStart,    // finger resting on the stone: talk (AI) or purr (offline)
  HoldEnd,
  StrokeStart,  // finger moving on the stone: petting
  StrokeEnd,
  PickUp,
  Shake,
  FreeFall,
  Knock,  // a tap on the table next to it
  FaceDown,
  FaceUp,
  UpsideDown,
  Upright,
  // AI link (voice)
  AiThinking,  // the server received the question
  AiSpeakStart,
  AiSpeakEnd,
  // Claude desktop link (Hardware Buddy protocol)
  ClaudeUp,
  ClaudeDown,
  ClaudeBusyStart,  // a Claude Code / Cowork session is generating
  ClaudeBusyEnd,
  ClaudePrompt,  // Claude is waiting for a permission decision
  ClaudePromptGone,
  ClaudeLevelUp,       // every 50K output tokens
  ClaudeQuickApprove,  // approved within 5 s
  // raw touch stream (TouchGestures in Text mode) - carries x/y in TouchEv
  TouchDown,
  TouchMove,
  TouchUp,
  // SoulOS services
  TextCommit,  // the text input finished; the app reads the committed text
  TextCancel,
  AlarmDue,    // an alarm (or its snooze) is ringing now
  Count
};

inline const char* evName(Ev e) {
  static const char* const kNames[] = {
      "None",         "Tap",          "DoubleTap",     "HoldStart",   "HoldEnd",
      "StrokeStart",  "StrokeEnd",    "PickUp",        "Shake",       "FreeFall",
      "Knock",        "FaceDown",     "FaceUp",        "UpsideDown",  "Upright",
      "AiThinking",   "AiSpeakStart", "AiSpeakEnd",    "ClaudeUp",    "ClaudeDown",
      "ClaudeBusyStart", "ClaudeBusyEnd", "ClaudePrompt", "ClaudePromptGone", "ClaudeLevelUp",
      "ClaudeQuickApprove", "TouchDown",  "TouchMove",   "TouchUp",       "TextCommit",
      "TextCancel",   "AlarmDue"};
  static_assert(sizeof(kNames) / sizeof(kNames[0]) == (unsigned)Ev::Count, "event names");
  const unsigned i = (unsigned)e;
  return i < (unsigned)Ev::Count ? kNames[i] : "?";
}

// A touch event with where it happened (display pixels) and when (seconds
// since the gesture detector started). Tap/Hold/... all carry the point.
struct TouchEv {
  Ev e = Ev::None;
  int16_t x = 0, y = 0;
  float t = 0;
};

template <int N, class T = Ev>
struct EvQueue {
  T buf[N];
  int head = 0, count = 0;
  void push(const T& e) {
    if (count == N) {  // drop the oldest
      head = (head + 1) % N;
      --count;
    }
    buf[(head + count) % N] = e;
    ++count;
  }
  bool pop(T& e) {
    if (!count) return false;
    e = buf[head];
    head = (head + 1) % N;
    --count;
    return true;
  }
};

}  // namespace suflet
