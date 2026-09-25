// RGB565 software canvas with anti-aliased signed-distance-field shapes.
// Everything the face draws goes through fillSdf(): coverage from the SDF
// gives smooth edges, and an optional halo makes the eyes glow on the
// black AMOLED like they sit behind frosted glass.
#pragma once
#include <math.h>
#include <stdint.h>

#include "Color.h"
#include "Font.h"

namespace suflet {

struct Rect {
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;  // half-open [x0, x1) x [y0, y1)
  bool empty() const { return x1 <= x0 || y1 <= y0; }
  int w() const { return x1 - x0; }
  int h() const { return y1 - y0; }
  void add(const Rect& r) {
    if (r.empty()) return;
    if (empty()) {
      *this = r;
      return;
    }
    if (r.x0 < x0) x0 = r.x0;
    if (r.y0 < y0) y0 = r.y0;
    if (r.x1 > x1) x1 = r.x1;
    if (r.y1 > y1) y1 = r.y1;
  }
};

inline float clampf(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }

class Canvas {
 public:
  Canvas(int w, int h, uint16_t* buf) : w_(w), h_(h), buf_(buf) {}

  int width() const { return w_; }
  int height() const { return h_; }
  uint16_t* data() { return buf_; }
  const uint16_t* data() const { return buf_; }
  uint16_t at(int x, int y) const { return buf_[y * w_ + x]; }

  void fill(Rgb c) {
    const uint16_t v = c.to565();
    for (int i = 0; i < w_ * h_; ++i) buf_[i] = v;
    markDirty(Rect{0, 0, w_, h_});
  }
  void fillRect(Rect r, Rgb c) {
    r = clip(r);
    const uint16_t v = c.to565();
    for (int y = r.y0; y < r.y1; ++y) {
      uint16_t* row = buf_ + y * w_;
      for (int x = r.x0; x < r.x1; ++x) row[x] = v;
    }
  }

  // Area touched since resetDirty(); the display layer pushes only this.
  const Rect& dirty() const { return dirty_; }
  void resetDirty() { dirty_ = Rect{}; }
  void markDirty(const Rect& r) { dirty_.add(clip(r)); }
  Rect clip(Rect r) const {
    if (r.x0 < 0) r.x0 = 0;
    if (r.y0 < 0) r.y0 = 0;
    if (r.x1 > w_) r.x1 = w_;
    if (r.y1 > h_) r.y1 = h_;
    return r;
  }

  inline void blend(int x, int y, Rgb c, float a) {
    uint16_t& px = buf_[y * w_ + x];
    if (a >= 0.999f) {
      px = c.to565();
      return;
    }
    const Rgb d = Rgb::from565(px);
    px = Rgb((uint8_t)(d.r + (c.r - d.r) * a), (uint8_t)(d.g + (c.g - d.g) * a),
             (uint8_t)(d.b + (c.b - d.b) * a))
             .to565();
  }

  // sdf(px, py) -> signed distance in pixels, negative inside.
  // glowR > 0 adds a soft halo of strength glowA outside the shape.
  template <class F>
  void fillSdf(float bx0, float by0, float bx1, float by1, F sdf, Rgb c, float alpha,
               float glowR = 0, float glowA = 0) {
    if (alpha <= 0.004f) return;
    const float m = (glowR > 0 && glowA > 0 ? glowR : 0) + 1.5f;
    Rect r{(int)floorf(bx0 - m), (int)floorf(by0 - m), (int)ceilf(bx1 + m), (int)ceilf(by1 + m)};
    r = clip(r);
    if (r.empty()) return;
    markDirty(r);
    const float invG = glowR > 0 ? 1.0f / glowR : 0;
    for (int y = r.y0; y < r.y1; ++y) {
      const float py = y + 0.5f;
      for (int x = r.x0; x < r.x1; ++x) {
        const float d = sdf(x + 0.5f, py);
        float a;
        if (d <= -0.5f) {
          a = 1.0f;
        } else if (d < 0.5f) {
          a = 0.5f - d;
          if (glowA > 0) {
            const float g = glowA;
            if (g > a) a = a + (g - a) * (d + 0.5f);  // smooth join into the halo
          }
        } else if (glowA > 0 && d < glowR) {
          const float k = 1.0f - d * invG;
          a = glowA * k * k;
        } else {
          continue;
        }
        blend(x, y, c, a * alpha);
      }
    }
  }

  // ---- primitives -------------------------------------------------------
  void ellipse(float cx, float cy, float rx, float ry, Rgb c, float alpha = 1, float glowR = 0,
               float glowA = 0);
  void ring(float cx, float cy, float r, float thick, Rgb c, float alpha = 1, float glowR = 0,
            float glowA = 0);
  void segment(float x0, float y0, float x1, float y1, float thick, Rgb c, float alpha = 1,
               float glowR = 0, float glowA = 0);
  // Arc from angle a0 to a1 (radians, screen coords: 0 = right, +pi/2 = down).
  void arc(float cx, float cy, float r, float a0, float a1, float thick, Rgb c, float alpha = 1,
           float glowR = 0, float glowA = 0);
  void heart(float cx, float cy, float size, Rgb c, float alpha = 1, float glowR = 0,
             float glowA = 0);
  void star(float cx, float cy, float r, float rot, Rgb c, float alpha = 1, float glowR = 0,
            float glowA = 0);
  // Filled box with rounded corners (radius r), anti-aliased edges.
  void roundRect(float x0, float y0, float x1, float y1, float r, Rgb c, float alpha = 1,
                 float glowR = 0, float glowA = 0);

  // ---- text -------------------------------------------------------------
  // Draws UTF-8 text with its baseline at y. x is the left edge, the centre
  // or the right edge depending on `align`. Clipped to the canvas, marks the
  // touched area dirty, returns the advance width in pixels. When `accent`
  // is given, the Romanian letters ă â î ș ț use that colour (how the
  // keyboard shows an automatic diacritic).
  int drawText(const Font& f, float x, int y, const char* s, Rgb c, float alpha = 1,
               Align align = Align::Left, const Rgb* accent = nullptr, int nBytes = -1);
  // Width in pixels of the first nBytes of s (-1 = the whole string).
  static int measureText(const Font& f, const char* s, int nBytes = -1);

  // ---- SDF helpers (public so the face renderer can combine them) ------
  static float sdEllipse(float px, float py, float cx, float cy, float rx, float ry);
  static float sdSegment(float px, float py, float x0, float y0, float x1, float y1);
  static float sdArc(float px, float py, float cx, float cy, float r, float a0, float a1);
  static float sdHeart(float x, float y);  // unit heart, tip at (0,0), y up
  static float sdStar5(float x, float y, float r);
  static float sdRoundBox(float px, float py, float cx, float cy, float hw, float hh, float r);

 private:
  int w_, h_;
  uint16_t* buf_;
  Rect dirty_;
};

}  // namespace suflet
