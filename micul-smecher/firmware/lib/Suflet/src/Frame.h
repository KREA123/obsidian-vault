// One frame of SOUL's screen, the same on the device and in the simulator.
//
// The canvas is persistent (a PSRAM framebuffer that always holds the last
// picture). Each frame only the parts that change are touched:
//   1. repair = where the eyes were last frame + what the UI says changed,
//      a few disjoint rectangles (RectList: each eye, a key, a capsule);
//      under each one's clip, clear it and redraw the UI layer there
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
  Rect repair, eyes, changed;                 // bounding boxes
  RectList repairList, eyesList, changedList;  // what was really touched
  uint32_t repairPx = 0, changedPx = 0;       // pixels in the lists
  uint32_t ringPasses = 0;                    // second passes for eyes under the rim rings (all frames)
};

class FrameComposer {
 public:
  explicit FrameComposer(Canvas* cv = nullptr) : cv_(cv) {}
  void setCanvas(Canvas* cv) { cv_ = cv; }
  // Draws the frame; returns the bounding box of what changed on the canvas
  // (changedList() has the rectangles themselves).
  Rect compose(Os& os, bool fullRedraw = false);
  const RectList& changedList() const { return st_.changedList; }
  const FrameStats& stats() const { return st_; }
  void invalidateAll() { full_ = true; }

 private:
  static constexpr int kEyeSlack = 10;  // px the eyes may move in a frame (rim rings shown)
  Canvas* cv_;
  RectList prevEyes_;
  bool full_ = true;
  FrameStats st_;
};

// What a double-buffered panel must copy from the canvas for a frame that changed `now`: the back buffer
// still misses the previous frame's changes too. Updates `last` to `now`; returns the rectangles to copy.
inline RectList presentPlan(const RectList& now, RectList& last) {
  RectList copy = now;
  copy.add(last);
  if (!now.empty()) last = now;
  return now.empty() ? RectList() : copy;
}

}  // namespace suflet
