// Draws the SOUL eyes (eyes.js render(): eyeFrame, silhouette, drawEye,
// drawPupilShape, drawOverlays) into an RGB565 Canvas with the anti-aliased
// Raster. Flat vector shapes only; every special effect of the collection is
// drawn (shimmer, rainbow, chrome, aurora, starfield, folk, glitter, outline,
// halo), simplified only where a canvas-2D trick has no cheap equivalent
// (starfield dots are culled to the pupil instead of clipped).
//
// The glass, bezel and sheen are not drawn: on the device the real glass is
// in front of the panel (eyes.js opts glass:false, as SoulOS uses it).
#pragma once
#include "Canvas.h"
#include "EyeMotion.h"
#include "EyeRig.h"
#include "Raster.h"

namespace suflet {
namespace eyes {

struct EyeGeom {
  float x = 0, y = 0, rx = 0, ry = 0, b = 0, side = 0, sq = 0, k = 0;
};

struct RenderOpts {
  bool hetero = true;     // false: the left pupil colour for both eyes
  bool overlays = true;   // ? ! … zzz hearts tears …
  float alpha = 1;        // global fade (dim / sleep)
  const MotionPose* motion = nullptr;  // IMU behaviours (level keeping, marble pupils, ...)
};

class EyeRenderer {
 public:
  bool begin(int canvasW, int canvasH);
  // cx, cy: centre of the face; D: the face diameter (eyes.js D).
  // parts (optional): the rectangles each eye and the overlays touched
  void render(Canvas& cv, const EyeRig& rig, const Design& d, float cx, float cy, float D,
              const RenderOpts& o = RenderOpts(), RectList* parts = nullptr);
  const EyeGeom& eye(int i) const { return eyes_[i]; }
  Raster& raster() { return ras_; }

 private:
  struct Info {
    float gx = 0.34f, gy = -0.46f, gs = 1;
    bool none = false;
  };
  EyeGeom frame(const EyeRig& rig, const Design& d, float side, float cx, float cy, float D, float sx,
                float sy) const;
  void drawEye(Canvas& cv, const EyeRig& rig, const Design& d, float side, float cx, float cy, float D,
               float sx, float sy, const Xform& G, const RenderOpts& o);
  Info pupilShape(Canvas& cv, const Design& d, Pupil type, float px, float py, float prx, float pry,
                  Rgb color, float t, float side, const EyeRig& rig, const Xform& X, const Mask* clip,
                  float alpha);
  void overlays(Canvas& cv, const EyeRig& rig, const Design& d, float cx, float cy, float D, const Xform& G,
                float alpha);
  void drop(Canvas& cv, const Xform& G, float x, float y, float r, float a);
  void glint(Canvas& cv, const Design& d, float x, float y, float rx, float ry, float rot, const Xform& X,
             const Mask* clip, float alpha);

  Raster ras_;
  Path p_;
  Mask body_;
  EyeGeom eyes_[2];
};

// helpers shared with the UI glyphs
void superPath(Path& p, float x, float y, float rx, float ry, float rot, float n);
void starPath(Path& p, float x, float y, float r, int n, float inner, float rot);
void heartPath(Path& p, float x, float y, float s, float rot);
Rgb hsl(float h, float s, float l);  // h in degrees, s/l in percent (CSS hsl())

}  // namespace eyes
}  // namespace suflet
