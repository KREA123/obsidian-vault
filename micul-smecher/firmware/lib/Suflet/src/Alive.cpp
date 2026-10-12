#include "Alive.h"

#include "EyeTables.h"

namespace suflet {
namespace alive {

using namespace eyes;

// os/DESIGN-ALIVE.md §6, row by row (the web's RX / MOOD_OF / soul.react calls)
static const Reaction kTable[(int)Event::Count] = {
    /* Tap           */ {-1, 0, 1, false, 0, 0, 0, false},
    /* FingerDown    */ {-1, 0, 0, true, 0, 0, 2.2f, false},
    /* DialTurn      */ {-1, 0, 0, true, 0, 0.85f, 0.25f, false},
    /* DialSettle    */ {-1, 0, 0, true, 0, 0.95f, 0.4f, false},
    /* ListTurn      */ {-1, 0, 0, true, 0, 0.6f, 0.5f, false},
    /* OpenApp       */ {-1, 0, 1, false, 0, 0, 0, true},
    /* CloseApp      */ {-1, 0, 1, false, 0, 0, 0, true},
    /* Thinking      */ {X_thinking, 0.7f, 0, false, 0, 0, 0, false},
    /* ClaudeWorking */ {X_working, 0, 0, false, 0, 0, 0, false},
    /* Notify        */ {X_surprised, 0.9f, 0, true, 0, -0.9f, 0.9f, false},
    /* ClaudeNeeds   */ {X_shocked, 0, 0, true, 0, 0, 1.5f, false},
    /* Success       */ {X_approve, 0, 0, false, 0, 0, 0, false},
    /* Failure       */ {X_sad, 2.6f, 0, false, 0, 0, 0, false},
    /* Cancel        */ {X_confused, 1.4f, 0, false, 0, 0, 0, false},
    /* Night         */ {X_sleepy, 0, 0, false, 0, 0, 0, false},
    /* Shake         */ {X_dizzy, 2.2f, 0, false, 0, 0, 0, false},
    /* Listening     */ {X_listening, 0, 0, false, 0, 0, 0, false},
};

const Reaction& reaction(Event e) { return kTable[(unsigned)e < (unsigned)Event::Count ? (int)e : 0]; }

const char* eventName(Event e) {
  static const char* const k[] = {"tap",     "finger",  "dial-turn", "dial-settle", "list-turn", "open",
                                  "close",   "thinking", "claude-working", "notify", "claude-needs", "success",
                                  "failure", "cancel",  "night",     "shake",       "listening"};
  static_assert(sizeof(k) / sizeof(k[0]) == (unsigned)Event::Count, "event names");
  return (unsigned)e < (unsigned)Event::Count ? k[(int)e] : "?";
}

}  // namespace alive
}  // namespace suflet
