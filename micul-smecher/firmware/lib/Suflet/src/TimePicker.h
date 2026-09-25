// "Rim-Dial" time picker (research/04 §13): set a time with no letters.
// Hours sit on a 24 h sundial ring (0 at the bottom, 6 left, 12 top, 18
// right); lifting the finger moves on to the minutes, a normal clock face
// (00 at the top) that snaps to 5 minutes when you drag fast. A touch on
// the rim sets the value by absolute angle; tap the hour or the minutes to
// switch; ✓ confirms. Draws on the Canvas; the eyes sit inside the ring.
#pragma once
#include <stdint.h>

#include "Canvas.h"
#include "Events.h"
#include "Geometry.h"
#include "Keyboard.h"  // KbResult
#include "Predictor.h"  // Lang

namespace suflet {

enum class DialMode : uint8_t { Hours, Minutes };

class TimePicker {
 public:
  // Everything below is laid out in design pixels on the 466 px disc and
  // scaled to the panel here (the ring, the digits, the ✓, the hit areas).
  TimePicker() { setGeometry(DisplayGeometry{}); }
  void setGeometry(const DisplayGeometry& g);
  const DisplayGeometry& geometry() const { return g_; }

  void open(int hour, int minute);
  void close() { open_ = false; }
  bool isOpen() const { return open_; }
  void setLang(Lang l) {
    lang_ = l;
    changed_ = true;
  }
  void setNow(uint32_t localEpoch);  // 0 = clock unknown (no "rings in" line)

  bool touch(const TouchEv& e);
  void update(float dt);
  bool poll(KbResult& r) {
    r = result_;
    result_ = KbResult::None;
    return r != KbResult::None;
  }
  void cancel();

  int hour() const { return h_; }
  int minute() const { return m_; }
  DialMode mode() const { return mode_; }
  void setMode(DialMode m);
  void set(int h, int m);

  // Geometry, screen angles in degrees (0 = right, 90 = down, clockwise).
  static int hourAt(float deg);
  static int minuteAt(float deg, bool fast);
  static float hourAngle(int h) { return 90.0f + 15.0f * h; }
  static float minuteAngle(int m) { return -90.0f + 6.0f * m; }
  float knobAngle() const { return mode_ == DialMode::Hours ? hourAngle(h_) : minuteAngle(m_); }
  // Minutes until the picked time next comes round (0 if the clock is unknown).
  uint32_t minutesUntil() const;

  bool changed() const { return changed_; }
  // True if redrawing is needed after `r` was cleared (it covers our pixels).
  bool overlaps(const Rect& r) const;
  void render(Canvas& cv);  // clears its own areas (not the eyes) and draws

  // Design pixels (466 px disc): centre, ring radius and ring width.
  static constexpr float kCx = 233, kCy = 233, kR = 205, kTrack = 30;
  // The same, in panel pixels.
  float cx() const { return cx_; }
  float cy() const { return cy_; }
  float ringR() const { return r_; }

 private:
  void setFromPoint(float x, float y, float t);
  void polar(float deg, float r, float& x, float& y) const;
  float S(float designPx) const { return g_.s(designPx); }
  DisplayGeometry g_;
  float cx_ = kCx, cy_ = kCy, r_ = kR, track_ = kTrack;
  Rect title_, digits_, rel_, ok_;
  float clear0_ = 0, clear1_ = 0;
  bool open_ = false, changed_ = true, dragging_ = false, okDown_ = false;
  int h_ = 7, m_ = 0;
  DialMode mode_ = DialMode::Hours;
  Lang lang_ = Lang::En;
  uint32_t now_ = 0;
  float advanceIn_ = -1;  // countdown to the minutes after lifting in hours mode
  float lastDeg_ = 0, lastT_ = -1;
  KbResult result_ = KbResult::None;
};

}  // namespace suflet
