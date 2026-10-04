// SoulOS 5 "Glass" on the device (os/DESIGN-GLASS.md): the aura behind the
// screens and the frosted glass panels on it.
//
// A real-time blur of whatever is under a panel is far too expensive for the
// S3, so the glass is built the other way round:
//   1. the aura (deep near-black + three big soft glows in SOUL's colours +
//      one glow for the state) is rendered at 1/4 resolution, box-blurred
//      (3 passes; 6 for the "frosted" copy), then upscaled bilinearly with a
//      4x4 ordered dither into two RGB565 buffers in PSRAM: `aura` (what the
//      screen shows) and `frost` (what a panel shows through). This happens
//      only when the tone changes (a few times a minute at most).
//   2. the buffers are (W + 2M) square: drift and the IMU tilt only move the
//      read window by up to M px (a cheap translate, rate-limited by SoulOS).
//   3. background() copies aura rows under the canvas clip. A panel evaluates
//      a cheap signed distance per pixel and maps the frosted pixel through
//      per-panel lookup tables (white fill, 8 gradient steps, an optional
//      tint), adds a 1.5 px edge lit from the top-left, an outer shadow and
//      an optional accent glow. No heap traffic per frame.
#pragma once
#include <stdint.h>

#include "Canvas.h"
#include "Color.h"

namespace suflet {

enum class GlassTone : uint8_t { Default, Ice, Amber, Mint };

struct GlassStyle {
  float fillTop = 0.15f, fillBottom = 0.06f;  // white over the frosted aura (155 deg gradient)
  float edge = 0.46f;                         // the rim light at the top-left (0.07 floor elsewhere)
  float shadow = 0.5f;                        // darkening just outside the panel
  float shadowR = 9, shadowDy = 4;            // its reach and its drop, px (small parts: smaller)
  Rgb tint;                                   // a tinted fill (selected, a toggle on, a dark knob)
  float tintA = 0;
  Rgb glow;  // an accent glow outside (amber / mint / ice)
  float glowA = 0;
  float alpha = 1;  // the whole panel (screens fade in)
  static GlassStyle plain(float alpha = 1) {
    GlassStyle s;
    s.alpha = alpha;
    return s;
  }
  static GlassStyle accent(Rgb c, float glowA = 0.42f, float tintA = 0.12f, float alpha = 1) {
    GlassStyle s;
    s.glow = c;
    s.glowA = glowA;
    s.tint = c;
    s.tintA = tintA;
    s.alpha = alpha;
    return s;
  }
  GlassStyle pressed() const {
    GlassStyle s = *this;
    s.fillTop += 0.09f;
    s.fillBottom += 0.05f;
    return s;
  }
};

class GlassLayer {
 public:
  static constexpr int kMargin = 12;  // drift / tilt room on each side, px
  static constexpr int kDiv = 4;      // the aura is built at 1/4 resolution

  ~GlassLayer();
  // Allocates the two buffers (about 1 MB at 480 px: PSRAM on the device).
  // false = out of memory: everything falls back to black (the old look).
  // buildNow = false (the device's boot, 1.8): the first aura is built by step() over the next frames
  // instead of now (~55 M instructions, ~125 ms before the eyes could show); until then it is black.
  bool begin(int w, int h, bool buildNow = true);
  bool ready() const { return aura_ != nullptr && built_; }
  int width() const { return w_; }
  int height() const { return h_; }

  // The look. Each returns true when the screen must be repainted.
  bool setOn(bool on);             // the aura shows (a screen is open) or not (standby: black)
  bool setTone(GlassTone t);       // re-renders the aura on the next rebuild()
  bool setOffset(int dx, int dy);  // drift + tilt, clamped to +-kMargin
  bool setLevel(float a);          // 0..1 brightness of the aura (fade in / out), quantised to 1/16
  bool rebuild();                  // re-renders the buffers now if the tone changed; true if it did
  // The same, spread over frames (SoulOS calls it every frame): the new aura is built into a second
  // pair of buffers, `rows` rows a call, while the old one stays on screen; true on the frame it
  // swaps in (repaint then). Without memory for the second pair it falls back to rebuild().
  bool step(int rows = 64);
  bool building() const { return building_; }
  bool on() const { return on_; }
  GlassTone tone() const { return tone_; }
  float level() const { return level16_ / 16.0f; }
  int offsetX() const { return dx_; }
  int offsetY() const { return dy_; }

  // ---- painting, always limited to the canvas clip ------------------------
  // The aura (if on and ready), else black, over r (default: the clip).
  void background(Canvas& cv) const { background(cv, cv.clipRect()); }
  void background(Canvas& cv, Rect r) const;
  // Only the ring ri..ro around (cx, cy) (the time picker's rim).
  void backgroundRing(Canvas& cv, float cx, float cy, float ri, float ro) const;
  // A rounded rectangle of glass (r = corner radius; r = half the height = a pill).
  void panel(Canvas& cv, float x0, float y0, float x1, float y1, float r, const GlassStyle& s) const;
  void orb(Canvas& cv, float cx, float cy, float r, const GlassStyle& s) const {
    panel(cv, cx - r, cy - r, cx + r, cy + r, r, s);
  }
  // A capsule bent along a circle: centre radius rm, half-width hw, from a0
  // to a1 (radians, 0 = right, +pi/2 = down, a1 > a0, span < pi).
  void capsuleArc(Canvas& cv, float cx, float cy, float rm, float hw, float a0, float a1, const GlassStyle& s) const;
  // A full glass annulus (a dial's track).
  void band(Canvas& cv, float cx, float cy, float rm, float hw, const GlassStyle& s) const;

  // what a panel sees through it / what the screen shows (tests)
  uint16_t frostAt(int x, int y) const;
  uint16_t auraAt(int x, int y) const;
  uint32_t rebuilds = 0;     // how many times the buffers were rendered
  uint32_t panelPixels = 0;  // pixels shaded by panels (statistics)

  static Rgb toneColor(GlassTone t);

 private:
  // `inner(py, xa, xb)` may give a span of the row known to be deep inside the shape (no edge,
  // no anti-aliasing): those pixels skip the distance function and go straight through the LUTs.
  // `rows(py, RowSpans&)` (1.8) narrows each row: `reach` = where a pixel may be touched at all (outside
  // it the distance is surely >= the shadow / glow pad), `deep` = candidates surely 1.6 px inside, which
  // `deepPx(px, py)` confirms; those skip the distance function too but keep the per-pixel gradient.
  struct RowSpans {
    int nReach = 1, nDeep = 0;
    int reachLo[2] = {-(1 << 30), 0}, reachHi[2] = {1 << 30, 0}, deepLo[2] = {0, 0}, deepHi[2] = {0, 0};
  };
  template <class Sdf, class Inner, class Rows, class DeepPx>
  void shade(Canvas& cv, float bx0, float by0, float bx1, float by1, Sdf sdf, Inner inner, Rows rows, DeepPx deepPx,
             const GlassStyle& s) const;
  void buildLow(int phase);  // glows at 1/4 res (0), the aura blur (1), the frosted blur (2); -1 = all
  void upscale(int y0, int y1, uint16_t* oa, uint16_t* of) const;  // rows of the two 565 buffers
  int w_ = 0, h_ = 0, bw_ = 0, bh_ = 0;                            // screen and buffer sizes
  uint16_t* aura_ = nullptr;
  uint16_t* frost_ = nullptr;
  uint16_t* backA_ = nullptr;  // the next aura, being built (step())
  uint16_t* backF_ = nullptr;
  bool building_ = false;
  int buildRow_ = 0, buildPhase_ = 0;
  uint8_t* lo_ = nullptr;  // low-res work: aura RGB, frost RGB, temp
  // the panel lookup tables of the last few styles (a keyboard draws 35 caps in 3 styles)
  struct Lut {
    float key[6] = {-1, -1, -1, -1, -1, -1};
    uint16_t r[8][32] = {}, g[8][64] = {}, b[8][32] = {};  // already in place: pixel = r | g | b
  };
  mutable Lut* lut_ = nullptr;  // 4 slots, allocated on first use (8 KB: PSRAM on the device, not DRAM)
  mutable int lutNext_ = 0, lutSlots_ = 4;
  const Lut& lutFor(const GlassStyle& s) const;
  int lw_ = 0, lh_ = 0;
  bool on_ = false, dirty_ = true, built_ = false;
  GlassTone tone_ = GlassTone::Default;
  int dx_ = 0, dy_ = 0, level16_ = 16;
};

// The one glass layer of the device: SoulOS, the keyboard and the time
// picker all paint on it.
GlassLayer& glass();

}  // namespace suflet
