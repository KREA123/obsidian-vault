#include "Frame.h"

namespace suflet {

Rect FrameComposer::compose(Os& os, bool fullRedraw) {
  Canvas& cv = *cv_;
  RectList want;
  os.takeDirty(want);
  want.add(prevEyes_);
  const bool ringRefresh = os.face().ringRefreshDue();
  if (!ringRefresh && os.face().ringsShown()) {
    // rings on the rim (see below): where the eyes touch the rim, repair a little around last frame's
    // place, so this frame's eyes land inside the repair and need no second pass
    for (int i = 0; i < prevEyes_.n; ++i) {
      const Rect& e = prevEyes_.r[i];
      const Rect m{e.x0 - kEyeSlack, e.y0 - kEyeSlack, e.x1 + kEyeSlack, e.y1 + kEyeSlack};
      if (os.face().ringMayTouch(m)) want.add(m);
    }
  }
  if (full_ || fullRedraw || ringRefresh) {
    want.clear();
    want.add(Rect{0, 0, cv.width(), cv.height()});
  }
  full_ = false;
  RectList repair;
  for (int i = 0; i < want.n; ++i) repair.add(cv.clip(want.r[i]));
  for (int i = 0; i < repair.n; ++i) {
    cv.setClip(repair.r[i]);
    os.render(cv);
    cv.clearClip();
  }
  cv.resetDirty();
  RectList eyes;
  os.face().renderEyes(cv, &eyes);
  if (!ringRefresh && os.face().ringsShown()) {
    // The rim rings go on top of everything, and the last look is redrawn only inside `repair`. Where the
    // eyes (an overlay: the "!" beside the right eye) just landed on the rim outside it, the old ring is
    // under them instead of over them: those rectangles get the UI and the eyes again, then the rings.
    RectList need = repair;
    for (int i = 0; i < eyes.n; ++i) {
      const Rect& e = eyes.r[i];
      bool inside = false;
      for (int j = 0; j < repair.n && !inside; ++j)
        inside = e.x0 >= repair.r[j].x0 && e.y0 >= repair.r[j].y0 && e.x1 <= repair.r[j].x1 && e.y1 <= repair.r[j].y1;
      if (!inside && os.face().ringMayTouch(e)) need.add(e);
    }
    for (int i = 0; i < need.n; ++i) {
      bool known = false;
      for (int j = 0; j < repair.n && !known; ++j)
        known = need.r[i].x0 == repair.r[j].x0 && need.r[i].y0 == repair.r[j].y0 && need.r[i].x1 == repair.r[j].x1 &&
                need.r[i].y1 == repair.r[j].y1;
      if (known) continue;
      ++st_.ringPasses;
      cv.setClip(need.r[i]);
      os.render(cv);
      os.face().renderEyes(cv);
      cv.clearClip();
    }
    repair = need;
  }
  // the rim rings: a fresh look on refresh frames (the whole glass was
  // repaired), else the last look again, only where we just repaired
  os.face().renderRings(cv, &repair, ringRefresh);
  RectList changed = repair;
  changed.add(eyes);
  prevEyes_ = eyes;
  st_.repairList = repair;
  st_.eyesList = eyes;
  st_.changedList = changed;
  st_.repair = repair.bounds();
  st_.eyes = eyes.bounds();
  st_.changed = changed.bounds();
  st_.repairPx = (uint32_t)repair.pixels();
  st_.changedPx = (uint32_t)changed.pixels();
  return st_.changed;
}

}  // namespace suflet
