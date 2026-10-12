// SoulOS Alive (os/DESIGN-ALIVE.md): the hardware-free logic of the design language the founder approved on
// 2026-10-11, shared by SoulOS (Os*.cpp) and the native tests. "The eyes are the OS": standby is the eyes alone;
// awake, they glide up into one slot above every screen; opening an app is a blink of the whole glass (the lid
// wipe); the home is a dial of MĂRGĂRITAR pebbles orbiting the eyes; the eyes react to everything.
//
//   LidWipe     the open / close transition: two flat black lids close in 80 ms (in-quad), the screen changes
//               behind them, they hold 40 ms and open in 170 ms (out-back 1.8). Pure timing + geometry.
//   Dial        the home dial's maths: rotation (drag, fling coasting to a detent, nudges, tilt steps, spin to a
//               pebble and open it), the opening spread, each pebble's place / scale / fade, where the eyes look.
//   Reactions   the eye-reaction table (§6): event -> expression, hold, blinks, gaze.
//   Speech      when SOUL says one of its offline lines (Lines.h) under the eyes, and the bubble's rise.
//   Wheel       every list (§4): one big focused row, the neighbours at 0.9 and half strength, rows as wide as the
//               circle allows; turned on the eyes' spring by a drag, a swipe, the crown, a lean.
//
// Units: the dial works in the web's 466 px design grid (DisplayGeometry scales it to the 480 px glass); the
// lids in panel pixels. Nothing here allocates or draws.
#pragma once
#include <math.h>
#include <stdint.h>

#include "Lines.h"

namespace suflet {
namespace alive {

// ---- the eyes' layouts (§1): scale k of the face and its centre offset, fractions of the screen ----------
struct Slot {
  float k, cx, cy;
};
constexpr Slot kStandby{1.0f, 0, 0};
constexpr Slot kPeek{0.52f, 0, -0.17f};   // a touch on the face: the eyes glide up, the clock rises
constexpr Slot kApps{0.44f, 0, -0.07f};   // the home dial
constexpr Slot kCard{0.30f, 0, -0.254f};  // THE slot of every app screen: centre y = 118 px on the 480 px glass
constexpr Slot kThink{0.60f, 0, -0.05f};
constexpr Slot kKeyboard{0.24f, 0, -0.43f};
constexpr float kMinK = 0.24f;            // never smaller (a face, not a logo)
constexpr float kSpringK = 260, kSpringZeta = 0.78f;  // the layout spring (≈ 0.35 s), Soul.update on the web

// the eye slot's black disc (drawn over the content, under the eyes): centre and radii in panel px for a
// square glass of side S (the eyes of kCard are 107 x 50 px at 480; the disc leaves a few px around them)
inline void slotDisc(float S, float& cx, float& cy, float& rx, float& ry) {
  cx = S * 0.5f;
  cy = S * (0.5f + kCard.cy);
  rx = S * 0.13f;
  ry = S * 0.056f;
}

// breathing idle (§3): the eyes swell 1.2 % over 5.5 s (the sleeping eyes' period); 1 with reduced motion
inline float breath(float t, bool reducedMotion) {
  return reducedMotion ? 1.0f : 1.0f + 0.012f * sinf(t * 6.2831853f / 5.5f);
}

// ---- the lid wipe (§3) ------------------------------------------------------------------------------------
class LidWipe {
 public:
  static constexpr float kClose = 0.08f, kHold = 0.04f, kOpen = 0.17f;
  static constexpr float kTotal = kClose + kHold + kOpen;  // 290 ms
  void start() {
    t_ = 0;
    on_ = true;
    midFired_ = false;
  }
  void cancel() { on_ = false; }
  bool active() const { return on_; }
  // advance; true exactly once, on the update where the lids are shut (the screen changes behind them)
  bool update(float dt) {
    if (!on_) return false;
    t_ += dt;
    bool mid = false;
    if (!midFired_ && t_ >= kClose) {
      midFired_ = true;
      mid = true;
    }
    if (t_ >= kTotal) on_ = false;
    return mid;
  }
  bool closing() const { return on_ && !midFired_; }  // the old screen is still behind the lids
  float time() const { return t_; }
  // how shut the lids are: 0 open (off the glass) .. 1 shut; the out-back opening overshoots below 0
  float cover() const { return on_ ? coverAt(t_) : 0.0f; }
  static float coverAt(float t) {
    if (t < 0) return 0;
    if (t < kClose) return (t / kClose) * (t / kClose);  // in-quad
    if (t < kClose + kHold) return 1;
    if (t < kTotal) return 1 - outBack((t - kClose - kHold) / kOpen);
    return 0;
  }
  static float outBack(float t) {  // eyes.js out-back with c = 1.8
    const float c = 1.8f, c3 = c + 1, u = t - 1;
    return 1 + c3 * u * u * u + c * u * u;
  }
  // The lids for cover c on a W x H glass: two ellipses 160 % x 62 % of it (the web's #lids), the upper one
  // sliding down from above, the lower one up from below. rx, ry, and the two centres' y.
  static void geometry(float W, float H, float c, float& rx, float& ry, float& cyUp, float& cyLo) {
    rx = 0.8f * W;
    ry = 0.31f * H;
    const float off = (1.01f - 1.01f * c) * 0.62f * H;
    cyUp = ry - off;
    cyLo = H - ry + off;
  }
  // the rows [y0, y1) where the lids leave the glass visible somewhere (outside them, every pixel is black)
  static void openBand(float W, float H, float c, int& y0, int& y1) {
    float rx, ry, u, l;
    geometry(W, H, c, rx, ry, u, l);
    // the lowest row the upper lid covers everywhere across the glass is where its edge is highest: x = 0 / W
    const float dx = 0.5f * W / rx, sag = ry * (1 - sqrtf(1 - dx * dx));
    y0 = (int)floorf(u + ry - sag);
    y1 = (int)ceilf(l - ry + sag);
    if (y0 < 0) y0 = 0;
    if (y1 > (int)H) y1 = (int)H;
    if (y1 < y0) y1 = y0;
  }

 private:
  float t_ = 0;
  bool on_ = false, midFired_ = false;
};

// ---- the home dial (§4) ----------------------------------------------------------------------------------
class Dial {
 public:
  static constexpr float kR = 170, kStepDeg = 28, kW = 52, kH = 58, kGrow = 0.5f, kFade0 = 132, kFade1 = 158;
  static constexpr float kDragPx = 88;      // design px of finger travel per pebble
  static constexpr float kCoast = 3.2f;     // a fling lands on round(rot + vr / kCoast)
  static constexpr float kSnapK = 95, kSnapC = 17;    // the snap spring
  static constexpr float kOpenK = 300, kOpenC = 32;   // the opening spread
  static constexpr float kTiltG = 0.3f;     // ~17° of lean
  static constexpr float kTiltEvery = 0.45f;

  void reset(int n, int focus, bool spread) {
    n_ = n > 0 ? n : 1;
    rot_ = (float)wrapIndex(focus);
    vr_ = 0;
    hasTgt_ = false;
    after_ = -1;
    dragging_ = false;
    open_ = spread ? 0.0f : 1.0f;
    ov_ = 0;
  }
  int count() const { return n_; }
  float rot() const { return rot_; }
  float velocity() const { return vr_; }
  float openness() const { return open_; }
  bool dragging() const { return dragging_; }
  bool settling() const { return hasTgt_; }
  int target() const { return tgt_; }
  // the pebble in focus (at the bottom)
  int focused() const { return wrapIndex((int)lroundf(rot_)); }
  bool moving() const { return dragging_ || fabsf(vr_) > 0.3f; }
  // the finger
  void grab() {
    dragging_ = true;
    dragRot_ = rot_;
    vr_ = 0;
    hasTgt_ = false;
    after_ = -1;
  }
  void drag(float dxDesign) {
    if (!dragging_) grab();
    rot_ = dragRot_ - dxDesign / kDragPx;
  }
  // let go with the finger's speed (design px / s): coast, then land on the detent the coasting would reach
  void release(float vxDesign) {
    dragging_ = false;
    vr_ = clampf(-vxDesign / kDragPx, -16, 16);
    tgt_ = (int)lroundf(rot_ + vr_ / kCoast);
    hasTgt_ = true;
  }
  // one pebble on (+1 = the next one comes to the bottom from the right, as a swipe to the left)
  void nudge(int dir) {
    const int b = hasTgt_ ? tgt_ : (int)lroundf(rot_);
    tgt_ = b + (dir > 0 ? 1 : -1);
    hasTgt_ = true;
    after_ = -1;
  }
  // turn the shortest way to pebble i; open = open it once it lands
  void spinTo(int i, bool open, bool reducedMotion) {
    tgt_ = (int)lroundf(rot_) + (int)lroundf(wrapU((float)i - (float)lroundf(rot_)));
    hasTgt_ = true;
    vr_ = 0;
    after_ = open ? wrapIndex(i) : -1;
    if (reducedMotion) rot_ = (float)tgt_;
  }
  // the gravity's sideways lean (g): past ~17° it steps one pebble every 0.45 s; true when it stepped
  bool tilt(float gx, double now) {
    if (fabsf(gx) < kTiltG || hasTgt_ || dragging_ || now - lastTilt_ < kTiltEvery) return false;
    lastTilt_ = now;
    tgt_ = (int)lroundf(rot_) + (gx > 0 ? 1 : -1);
    hasTgt_ = true;
    after_ = -1;
    return true;
  }
  // advance; returns the pebble to open (spinTo(.., true) landed) or -1
  int update(float dt, bool reducedMotion) {
    if (reducedMotion) {
      open_ = 1;
      ov_ = 0;
    } else if (open_ != 1 || ov_ != 0) {
      stepSpring(open_, ov_, 1.0f, kOpenK, kOpenC, dt);
      if (fabsf(1 - open_) < 0.001f && fabsf(ov_) < 0.01f) open_ = 1, ov_ = 0;
    }
    if (dragging_ || dt <= 0) return -1;
    if (hasTgt_) {
      if (reducedMotion) {
        rot_ = (float)tgt_;
        vr_ = 0;
      } else {
        stepSpring(rot_, vr_, (float)tgt_, kSnapK, kSnapC, dt);
      }
      if (fabsf(tgt_ - rot_) < 0.002f && fabsf(vr_) < 0.02f) {
        rot_ = (float)wrapIndex(tgt_);
        vr_ = 0;
        hasTgt_ = false;
        const int a = after_;
        after_ = -1;
        return a;
      }
    } else if (fabsf(vr_) > 0.01f || fabsf(rot_ - roundf(rot_)) > 0.001f) {
      tgt_ = (int)lroundf(rot_ + vr_ / kCoast);
      hasTgt_ = true;
    }
    return -1;
  }
  // where pebble i is drawn (design px of the 466 grid), its scale (1 .. 1.5 focused), its opacity
  struct Pebble {
    float x, y, scale, alpha, u;
    bool focus;
  };
  Pebble place(int i) const {
    const float op = clampf(open_, 0, 1);
    const float u = wrapU((float)i - rot_);
    const float a = u * kStepDeg * (1 + (1 - op) * 0.6f), aa = fabsf(a);
    const float wb = clampf(1 - fabsf(u) * 1.35f, 0, 1);
    Pebble p;
    p.u = u;
    p.scale = (1 + kGrow * wb) * (0.55f + 0.45f * op);
    p.alpha = clampf((kFade1 - aa) / (kFade1 - kFade0), 0, 1) * op;
    const float r = a * 3.14159265f / 180, R = kR + 6 * wb;
    p.x = 233 + R * sinf(r);
    p.y = 233 + R * cosf(r);
    p.focus = fabsf(u) < 0.5f;
    return p;
  }
  // where the eyes look: sideways toward the incoming pebble while turning, down at the focused one at rest
  void gaze(float& x, float& y) const {
    if (moving()) {
      const float fr = rot_ - roundf(rot_);
      x = clampf(-fr * 1.6f - vr_ * 0.06f, -0.9f, 0.9f);
      y = 0.85f;
    } else {
      x = 0;
      y = 0.95f;
    }
  }
  // the pebble under a touch (design px), -1 if none (only those visible enough to be pressed)
  int hit(float x, float y) const {
    int best = -1;
    float bd = 1e9f;
    for (int i = 0; i < n_; ++i) {
      const Pebble p = place(i);
      if (p.alpha < 0.3f) continue;
      const float r = (kH * 0.5f + 4) * p.scale, d = hypotf(x - p.x, y - p.y);
      if (d <= r && d < bd) bd = d, best = i;
    }
    return best;
  }
  float wrapU(float u) const {  // the web's orbWrap: into [-n/2, n/2)
    const float n = (float)n_;
    u = fmodf(fmodf(u, n) + n, n);
    return u >= n / 2 ? u - n : u;
  }
  int wrapIndex(int i) const { return ((i % n_) + n_) % n_; }

 private:
  static float clampf(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
  static void stepSpring(float& x, float& v, float tgt, float k, float c, float dt) {
    float h = dt;
    while (h > 0) {  // the web integrates once per animation frame; small steps keep 24-30 fps stable
      const float s = h > 1.0f / 120 ? 1.0f / 120 : h;
      v += (k * (tgt - x) - c * v) * s;
      x += v * s;
      h -= s;
    }
  }
  int n_ = 1;
  float rot_ = 0, vr_ = 0, dragRot_ = 0, open_ = 1, ov_ = 0;
  double lastTilt_ = -10;
  int tgt_ = 0, after_ = -1;
  bool hasTgt_ = false, dragging_ = false;
};

// ---- the wheel (§4: every list) ---------------------------------------------------------------------------
// One big focused row in the middle of the space under the eyes, the row above and the row below at 0.9 scale
// and half strength, the rest off the glass. Each row is as wide as the circle allows at its height (r 212), so
// nothing is cut. Turned by a swipe or a drag (one row per 56 px), the crown, the device's tilt; a tap on a
// neighbour turns it there (and acts). Rows move on the eyes' spring. Design px of the 466 grid.
class Wheel {
 public:
  static constexpr float kY = 290, kH = 74, kGap = 10, kSn = 0.9f, kR = 212, kMaxW = 336, kDragPx = 56;
  static constexpr float kSpringK = 260, kSpringC = 25;  // ≈ the web's cubic-bezier(.34,1.56,.64,1) in 0.34 s
  static constexpr float kTiltG = 0.3f, kTiltEvery = 0.45f;
  void reset(int n, int focus) {
    n_ = n > 0 ? n : 0;
    f_ = clampi(focus, 0, n_ - 1);
    pos_ = (float)f_;
    v_ = 0;
  }
  // the count changed under it (a row added or removed): keep the focus where it can be
  void resize(int n) {
    if (n == n_) return;
    n_ = n > 0 ? n : 0;
    f_ = clampi(f_, 0, n_ - 1);
    if (pos_ > n_ - 1) pos_ = (float)(n_ > 0 ? n_ - 1 : 0);
  }
  int count() const { return n_; }
  int focused() const { return f_; }
  float pos() const { return pos_; }
  bool moving() const { return fabsf(pos_ - f_) > 0.002f || fabsf(v_) > 0.02f; }
  // turn to row i (clamped); false if it is already there
  bool turnTo(int i, bool reducedMotion) {
    const int t = clampi(i, 0, n_ - 1);
    if (t == f_) return false;
    f_ = t;
    if (reducedMotion) pos_ = (float)f_, v_ = 0;
    return true;
  }
  bool turn(int d, bool reducedMotion) { return turnTo(f_ + d, reducedMotion); }
  // the forward / back lean (g): past ~17° it steps one row every 0.45 s; true when it stepped
  bool tilt(float gy, double now, bool reducedMotion) {
    if (fabsf(gy) < kTiltG || now - lastTilt_ < kTiltEvery) return false;
    lastTilt_ = now;
    return turn(gy > 0 ? 1 : -1, reducedMotion);
  }
  // advance the rows' spring; true while they move
  bool update(float dt) {
    if (!moving()) {
      pos_ = (float)f_;
      v_ = 0;
      return false;
    }
    float h = dt;
    while (h > 0) {
      const float s = h > 1.0f / 120 ? 1.0f / 120 : h;
      v_ += (kSpringK * ((float)f_ - pos_) - kSpringC * v_) * s;
      pos_ += v_ * s;
      h -= s;
    }
    if (!moving()) pos_ = (float)f_, v_ = 0;
    return true;
  }
  // where row i is (centre y, its box height and width, scale and opacity); y0 = the focused row's centre
  struct Place {
    float y, h, w, scale, alpha;
    bool visible;
  };
  static float step() { return kH * 0.5f + kGap + kH * kSn * 0.5f; }
  Place place(int i, float y0 = kY) const { return placeAt((float)i - pos_, y0); }
  static Place placeAt(float d, float y0 = kY) {
    const float ad = fabsf(d), s = d < 0 ? -1.0f : 1.0f;
    Place p;
    p.scale = 1 - (1 - kSn) * (ad < 1 ? ad : 1);
    p.alpha = ad <= 1 ? 1 - 0.5f * ad : 0.5f * clampf((1.6f - ad) / 0.6f, 0, 1);
    p.y = ad <= 1 ? y0 + d * step() : y0 + s * (step() + (ad - 1) * (kH * kSn + kGap));
    p.h = kH * p.scale;
    // the chord of the circle (r 212) at the row's far edge, 8 px in
    const float dy = fmaxf(fabsf(p.y - p.h * 0.5f - 233), fabsf(p.y + p.h * 0.5f - 233));
    const float chord = dy < kR ? 2 * sqrtf(kR * kR - dy * dy) - 8 : 0;
    p.w = fminf(kMaxW * p.scale, chord);
    p.visible = p.alpha > 0.02f && p.w > 40;
    return p;
  }
  // the row under a touch (design px): the focused one or a visible neighbour, -1 if none
  int hit(float x, float y, float y0 = kY) const {
    for (int i = f_ - 1; i <= f_ + 1; ++i) {
      if (i < 0 || i >= n_) continue;
      const Place p = place(i, y0);
      if (!p.visible || p.alpha < 0.3f) continue;
      if (fabsf(x - 233) <= p.w * 0.5f && fabsf(y - p.y) <= p.h * 0.5f + kGap * 0.5f) return i;
    }
    return -1;
  }

 private:
  static int clampi(int v, int a, int b) { return v < a ? a : (v > b ? b : v); }
  static float clampf(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
  int n_ = 0, f_ = 0;
  float pos_ = 0, v_ = 0;
  double lastTilt_ = -10;
};

// ---- the lean (1.9): what turns the dial and the wheels ----------------------------------------------------
// One axis of gravity (g) against how SOUL is being held: the difference from a slow average (2.5 s). A steady
// grip at any angle reads as no lean (the average catches up), so only a change of angle turns anything.
// Coming back from a lean is not a lean the other way: while the device returns toward the pose it had before
// the lean (`home`), the opposite direction reads 0, and once it is back within kHome the average snaps to it.
// Leaning on past home, the other way, is a new lean.
class Lean {
 public:
  static constexpr float kTau = 2.5f, kHome = 0.12f;
  void reset() { init_ = false, dir_ = 0; }
  void update(float g, float dt) {
    if (!init_) {
      avg_ = home_ = g;
      init_ = true;
    }
    avg_ += (g - avg_) * (dt / kTau > 1 ? 1 : (dt > 0 ? dt / kTau : 0));
    g_ = g;
    if (dir_ != 0) {
      const float still = (g - home_) * (float)dir_;  // how far it still leans the way it stepped
      if (still < kHome) {
        dir_ = 0;
        if (still > -kHome) avg_ = g;  // back home: the lean is over
      }
    }
  }
  bool ready() const { return init_; }
  float average() const { return avg_; }
  // the lean now (g); 0 while it is only coming back from the last one
  float value() const {
    if (!init_) return 0;
    const float v = g_ - avg_;
    if (dir_ != 0 && v * (float)dir_ < 0) return 0;
    return v;
  }
  // the dial / wheel stepped on this lean (dir = +1 / -1): remember where it came from
  void stepped(int dir) {
    if (dir_ == 0) home_ = avg_;
    dir_ = dir > 0 ? 1 : -1;
  }

 private:
  float avg_ = 0, home_ = 0, g_ = 0;
  int dir_ = 0;
  bool init_ = false;
};

// ---- the eye reactions (§6) ------------------------------------------------------------------------------
enum class Event : uint8_t {
  Tap,           // any tap on a control: blink x1
  FingerDown,    // look toward the finger
  DialTurn,      // look sideways toward the incoming pebble
  DialSettle,    // look down at the focused pebble
  ListTurn,      // look at the focused row
  OpenApp,       // the lids close over the glass (+ a blink)
  CloseApp,      // the same, the other way
  Thinking,      // squint (thinking), at least 700 ms
  ClaudeWorking, // reading scan
  Notify,        // a notification: surprised 0.9 s, look up at the banner
  ClaudeNeeds,   // shocked, then wide eyes looking at you
  Success,       // approve at once, happy held
  Failure,       // sad 2.6 s: only a failure that did nothing
  Cancel,        // misfire / cancel: confused 1.4 s
  Night,         // 23-06 h at rest on the face: sleepy
  Shake,         // dizzy 2.2 s (spiral pupils)
  Listening,     // hold the glass
  Count
};
struct Reaction {
  int8_t expr;       // eyes::Expr, -1 = no expression change
  float hold;        // s the expression is held (0 = its own length)
  uint8_t blinks;    // blinks at once
  bool look;         // a gaze goes with it
  float lookX, lookY, lookFor;  // fixed gaze (the finger / dial / list ones are computed by the caller)
  bool lids;         // the lid wipe
};
const Reaction& reaction(Event e);
const char* eventName(Event e);
// 23-06 h: the night mood on the face
inline bool isNight(int hour) { return hour >= 23 || (hour >= 0 && hour < 6); }

// ---- speech (§5) -----------------------------------------------------------------------------------------
// the topic of a greeting when the eyes wake: morning 05-11 h, night 23-06 h, hello otherwise
inline LineTopic greetingTopic(int hour) {
  if (isNight(hour)) return LineTopic::Night;
  if (hour >= 5 && hour < 11) return LineTopic::Morning;
  return LineTopic::Hello;
}
class Speech {
 public:
  static constexpr float kGreetEvery = 20, kBoredAfter = 11, kRise = 0.32f;
  // show a line for `secs` (2.2-3.2 s), after `delay` s (the eyes first settle into their new place)
  void say(const char* line, float secs, float delay = 0) {
    line_ = line;
    left_ = secs;
    shownFor_ = -delay;
  }
  void hide() { left_ = 0; }
  bool pending() const { return left_ > 0 && line_ && shownFor_ < 0; }
  bool showing() const { return left_ > 0 && line_ && shownFor_ >= 0; }
  const char* line() const { return showing() ? line_ : nullptr; }
  void update(float dt) {
    if (left_ <= 0) return;
    shownFor_ += dt;
    if (shownFor_ > 0) left_ -= fminf(dt, shownFor_);
  }
  // the rise (0 -> 1 on the eyes' spring curve, 0.32 s); 1 at once with reduced motion
  float rise(bool reducedMotion) const {
    if (reducedMotion) return 1;
    const float t = shownFor_ / kRise;
    if (t >= 1) return 1;
    const float c = 1.56f, u = t - 1;  // cubic-bezier(.34,1.56,.64,1) ≈ out-back
    return 1 + (c + 1) * u * u * u + c * u * u;
  }
  bool rising() const { return showing() && shownFor_ < kRise + 0.1f; }  // (+ the frames that land it exactly)
  // a greeting at most once every 20 s
  bool greetDue(double now) const { return now - lastGreet_ >= kGreetEvery; }
  void greeted(double now) { lastGreet_ = now; }

 private:
  const char* line_ = nullptr;
  float left_ = 0, shownFor_ = 0;
  double lastGreet_ = -1e9;
};

}  // namespace alive
}  // namespace suflet
