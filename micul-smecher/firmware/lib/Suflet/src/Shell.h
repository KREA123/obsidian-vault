// A minimal SoulOS screen router (v1). The face is home; a long press on it
// opens a note field (the system keyboard), and the time picker can be
// opened to set an alarm. The Shell sees every touch first: while a screen
// is open it consumes them (and asks for Text-mode touch, so fast typing
// never becomes a double-tap), otherwise they go on to the Brain.
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

#include "Alarms.h"
#include "Canvas.h"
#include "Events.h"
#include "Face.h"
#include "Keyboard.h"
#include "TimePicker.h"

namespace suflet {

enum class Screen : uint8_t { Face, Note, TimePicker };

class Shell {
 public:
  explicit Shell(Alarms* alarms = nullptr) : alarms_(alarms) {}

  Lang lang = Lang::En;              // EN is the default UI language
  bool holdOpensNote = true;         // main.cpp turns it off while Claude asks for approval

  Screen screen() const { return screen_; }
  void openNote(const std::string& initial = "");
  void openTimePicker(int hour, int minute);
  void back();  // side button: keep the draft, go home

  // Returns true when the event was used here (don't give it to the Brain).
  bool event(const TouchEv& e);
  bool wantsTextTouch() const { return screen_ != Screen::Face; }
  void update(float dt, uint32_t localNow);
  bool poll(Ev& e) { return q_.pop(e); }  // TextCommit / TextCancel for the Brain

  FaceLayout faceLayout() const;
  void adjustFace(Face& f) const;  // the eyes watch the finger / the dial knob

  // Draws the open screen if it changed, or if `cleared` wiped part of it.
  // Call before renderFace (the eyes sit on top). Returns true if it drew.
  bool render(Canvas& cv, const Rect& cleared);

  const std::vector<std::string>& notes() const { return notes_; }
  Keyboard& keyboard() { return kb_; }
  TimePicker& picker() { return tp_; }
  int lastAlarm() const { return lastAlarm_; }  // index added by the picker, -1 = none

 private:
  void go(Screen s);
  Alarms* alarms_;
  Screen screen_ = Screen::Face, drawn_ = Screen::Face;
  Rect drawnRect_;
  Keyboard kb_;
  TimePicker tp_;
  std::string draft_;
  std::vector<std::string> notes_;
  EvQueue<4> q_;
  uint32_t now_ = 0;
  int lastAlarm_ = -1;
  bool down_ = false;
  float fx_ = 233, fy_ = 233;
};

}  // namespace suflet
