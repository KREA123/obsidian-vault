// The one description of the round display that every screen is laid out
// against. The SoulOS UI (keyboard, time picker, shell, text overlays) was
// designed in "design pixels" on the 466 px disc of the AMOLED boards; on
// another disc everything is scaled uniformly by k = width / 466 (the disc
// is round and the layout is measured from its top-left corner, so a uniform
// scale keeps every chord and margin in proportion). Fonts are fixed pixel
// sizes and are not scaled (at k = 1.03 the difference is invisible).
//
// activeMm is the diameter of the lit area. It does not change any layout;
// it tells us how big the result is in the hand (key pitch in mm, tests).
#pragma once
#include <math.h>

#include "Canvas.h"  // Rect

namespace suflet {

struct DisplayGeometry {
  static constexpr float kDesignPx = 466.0f;  // the disc the UI was drawn on

  int w = 466, h = 466;     // panel pixels
  float activeMm = 43.76f;  // diameter of the active area in millimetres

  float k() const { return (float)w / kDesignPx; }
  float cx() const { return w * 0.5f; }
  float cy() const { return h * 0.5f; }
  // design pixels -> panel pixels
  float s(float designPx) const { return designPx * k(); }
  int si(float designPx) const { return (int)lroundf(designPx * k()); }
  Rect rect(int x0, int y0, int x1, int y1) const { return Rect{si(x0), si(y0), si(x1), si(y1)}; }
  // physical size
  float pxPerMm() const { return (float)w / activeMm; }
  float mm(float px) const { return px / pxPerMm(); }
};

// Known panels. Active diameters: 1.75" CO5300 from the Waveshare spec
// (43.76 mm). 1.43": 1.43" x 25.4 = 36.32 mm (diagonal = diameter; not
// measured). 2.8" ST7701 IPS: 70.13 mm from the bare-panel drawing of the
// same 480x480 round glass (Twoyas); Waveshare does not state it for the
// 2.8C. TODO(lcd28): measure the lit disc on the real board.
namespace displays {
constexpr DisplayGeometry kAmoled143{466, 466, 36.32f};
constexpr DisplayGeometry kAmoled175{466, 466, 43.76f};
constexpr DisplayGeometry kLcd28{480, 480, 70.13f};
}  // namespace displays

}  // namespace suflet
