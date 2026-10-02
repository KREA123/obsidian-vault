// SoulFace: the device's face, as the web SoulOS draws it (os/index.html,
// class Soul). It owns the eyes rig + renderer and turns what is going on
// (the Brain's mood and reactions, what SoulOS is doing) into expressions:
//
//   listening -> listening + ice rim      thinking -> thinking + amber comet
//   Claude working -> working (reading)   Claude needs you -> shocked, then
//   wide surprised eyes + amber rim       done -> approve      error -> confused
//   low battery -> hungry                 asleep -> sleepy, lids shut
//
// The OS only adds a layout (scale k and offset of the face, on a spring) so
// the same eyes can fill the glass or sit small above a screen, and the rim
// rings (one light per state). No heap allocation per frame.
#pragma once
#include "Brain.h"
#include "Canvas.h"
#include "EyeRender.h"
#include "EyeRig.h"

namespace suflet {

enum class FaceState : uint8_t { Idle, Listen, Think, Speak, Error, Busy, Wait, Low, Charge, Sleep };

struct FaceLayoutT {
  float k = 1, cx = 0, cy = 0;  // scale of the face and its centre offset, as fractions of the screen
};

struct FaceInputs {
  Mode mode = Mode::Awake;
  Reaction reaction = Reaction::None;  // the Brain's current reaction
  FaceState state = FaceState::Idle;
  bool alert = false;         // amber rim: Claude needs you / alarm
  float progress = 0;         // hold-to-approve arc 0..1
  bool look = false;          // look at a point (finger, the dial, you)
  float lookX = 0, lookY = 0;
  float level = -1;           // listening / charging level, -1 = synthetic
  FaceLayoutT layout;
};

class SoulFace {
 public:
  bool begin(int w, int h);
  void setDesign(int index, bool instant = false);  // swaps during a blink unless instant
  int design() const { return design_; }
  void setSeed(uint32_t seed);

  void react(int expr, float hold = 0) { rig_.react(expr, hold); }
  void flash(Rgb c, float seconds = 1.4f);  // a rim flash (mint = done)
  void hide() { rig_.hide(); }
  void snapLayout(const FaceLayoutT& l);

  void update(float dt, const FaceInputs& in);
  // Draws the eyes and the rim rings; marks the canvas dirty where it drew.
  void render(Canvas& cv) {
    renderEyes(cv);
    renderRings(cv, nullptr, false);
  }
  void renderEyes(Canvas& cv);
  // The rim rings change at most 12 times a second (or every frame while
  // the approve arc fills). refresh = draw the current look everywhere (the
  // caller repaired the whole glass); otherwise redraw the last look inside
  // `repair` only (nullptr = everywhere), so the moving eyes don't erase it.
  void renderRings(Canvas& cv, const Rect* repair, bool refresh);
  bool ringRefreshDue() const;
  bool ringsActive() const;  // a ring is lit now
  Raster& raster() { return ren_.raster(); }
  const eyes::EyeRig& rig() const { return rig_; }
  eyes::EyeRig& rig() { return rig_; }
  float layoutK() const { return lay_[0]; }
  bool hetero = true;
  float dim = 1;  // eyes alpha (sleep dimming on panels with a black level)

 private:
  int moodFor(const FaceInputs& in) const;
  eyes::EyeRig rig_;
  eyes::EyeRenderer ren_;
  int design_ = 0, pendingDesign_ = -1;
  float swapIn_ = 0;
  int W_ = 0, H_ = 0;
  Reaction lastReaction_ = Reaction::None;
  FaceState lastState_ = FaceState::Idle;
  bool lastAlert_ = false;
  float lay_[3] = {1, 0, 0}, layV_[3] = {0, 0, 0}, layT_[3] = {1, 0, 0};
  float fListen_ = 0, fAlert_ = 0, fThink_ = 0, fFlash_ = 0, progress_ = 0;
  struct RingLook {
    float listen = 0, alert = 0, think = 0, flash = 0, progress = 0, t = 0, level = 0;
    Rgb flashCol;
    bool any() const { return listen > 0.01f || alert > 0.01f || think > 0.01f || flash > 0.01f || progress > 0.005f; }
  } look_;  // what was last drawn
  Rgb flashCol_ = Rgb::hex(0xC9F2E4);
  float flashLeft_ = 0, t_ = 0, waitT_ = 0, talkNext_ = 0;
  Mode mode_ = Mode::Awake;
};

}  // namespace suflet
