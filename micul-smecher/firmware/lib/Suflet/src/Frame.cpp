#include "Frame.h"

namespace suflet {

Rect FrameComposer::compose(Os& os, bool fullRedraw) {
  Canvas& cv = *cv_;
  Rect repair = os.takeDirty();
  repair.add(prevEyes_);
  if (full_ || fullRedraw) repair = Rect{0, 0, cv.width(), cv.height()};
  full_ = false;
  repair = cv.clip(repair);
  if (!repair.empty()) {
    cv.setClip(repair);
    os.render(cv);
    cv.clearClip();
  }
  cv.resetDirty();
  os.face().render(cv);
  const Rect eyes = cv.dirty();
  Rect changed = repair;
  changed.add(eyes);
  prevEyes_ = eyes;
  st_.repair = repair;
  st_.eyes = eyes;
  st_.changed = changed;
  st_.repairPx = repair.empty() ? 0 : (uint32_t)(repair.w() * repair.h());
  st_.changedPx = changed.empty() ? 0 : (uint32_t)(changed.w() * changed.h());
  return changed;
}

}  // namespace suflet
