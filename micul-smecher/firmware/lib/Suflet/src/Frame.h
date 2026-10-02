// One frame of SOUL's screen, the same on the device and in the simulator.
//
// The canvas is persistent (a PSRAM framebuffer that always holds the last
// picture). Each frame only the parts that change are touched:
//   1. repair = where the eyes were last frame + what the UI says changed;
//      under a clip, clear it and redraw the UI layer there
//   2. draw the eyes (and the rim rings) on top, wherever they are now
//   3. changed = repair + where the eyes are now -> pushed to the panel
// Pixels outside `repair` never held last frame's eyes, so they are already
// correct: the result is identical to a full redraw (unit-tested), at a
// fraction of the cost (the eyes cover ~30 % of the glass).
#pragma once
#include "Canvas.h"
#include "Os.h"

namespace suflet {

struct FrameStats {
  Rect repair, eyes, changed;
  uint32_t repairPx = 0, changedPx = 0;
};

class FrameComposer {
 public:
  explicit FrameComposer(Canvas* cv = nullptr) : cv_(cv) {}
  void setCanvas(Canvas* cv) { cv_ = cv; }
  // Draws the frame; returns the rectangle that changed on the canvas.
  Rect compose(Os& os, bool fullRedraw = false);
  const FrameStats& stats() const { return st_; }
  void invalidateAll() { full_ = true; }

 private:
  Canvas* cv_;
  Rect prevEyes_;
  bool full_ = true;
  FrameStats st_;
};

}  // namespace suflet
