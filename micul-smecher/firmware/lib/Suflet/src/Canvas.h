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

// A few disjoint rectangles: what changed on the glass this frame (the two eyes and a key apart are two
// small rectangles, not one box over the whole face). add() merges a rectangle into any it touches, and
// into a neighbour when one box would cost little more than the two (each rectangle is one more pass of
// the UI under a clip); with no room left the cheapest pair is merged. Drawing every rectangle in turn
// gives the same pixels as drawing their bounding box once (each pass clears and redraws its area).
struct RectList {
  static constexpr int kMax = 6;
  Rect r[kMax];
  int n = 0;
  bool empty() const { return n == 0; }
  void clear() { n = 0; }
  static int64_t area(const Rect& a) { return a.empty() ? 0 : (int64_t)a.w() * a.h(); }
  static Rect hull(Rect a, const Rect& b) {
    a.add(b);
    return a;
  }
  // worth one box: they touch, or the box wastes at most a quarter of it plus a strip of 2K px
  static bool mergeable(const Rect& a, const Rect& b) {
    const int64_t u = area(hull(a, b));
    return (a.x0 <= b.x1 && b.x0 <= a.x1 && a.y0 <= b.y1 && b.y0 <= a.y1) || u - area(a) - area(b) <= u / 16 + 512;
  }
  Rect bounds() const {
    Rect b;
    for (int i = 0; i < n; ++i) b.add(r[i]);
    return b;
  }
  int64_t pixels() const {
    int64_t s = 0;
    for (int i = 0; i < n; ++i) s += area(r[i]);
    return s;
  }
  void add(Rect a) {
    if (a.empty()) return;
    for (int i = 0; i < n;) {
      if (mergeable(r[i], a)) {
        a = hull(a, r[i]);
        r[i] = r[--n];
        i = 0;  // the bigger box may now reach another one
        continue;
      }
      ++i;
    }
    if (n < kMax) {
      r[n++] = a;
      return;
    }
    int bi = 0;
    int64_t best = -1;
    for (int i = 0; i < n; ++i) {
      const int64_t grow = area(hull(r[i], a)) - area(r[i]);
      if (best < 0 || grow < best) best = grow, bi = i;
    }
    const Rect m = hull(r[bi], a);
    r[bi] = r[--n];
    add(m);
  }
  void add(const RectList& o) {
    for (int i = 0; i < o.n; ++i) add(o.r[i]);
  }
};

inline float clampf(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }

class Canvas {
 public:
  Canvas(int w, int h, uint16_t* buf) : w_(w), h_(h), buf_(buf), clip_{0, 0, w, h} {}

  int width() const { return w_; }
  int height() const { return h_; }
  uint16_t* data() { return buf_; }
  const uint16_t* data() const { return buf_; }
  uint16_t at(int x, int y) const { return buf_[y * w_ + x]; }

  void fill(Rgb c) {
    if (clip_.x0 > 0 || clip_.y0 > 0 || clip_.x1 < w_ || clip_.y1 < h_) {
      fillRect(clip_, c);
      markDirty(clip_);
      return;
    }
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
  // Everything drawn is limited to the clip rectangle (the whole canvas by
  // default). The frame loop uses it to repair the UI under the moving eyes.
  Rect clip(Rect r) const {
    if (r.x0 < clip_.x0) r.x0 = clip_.x0;
    if (r.y0 < clip_.y0) r.y0 = clip_.y0;
    if (r.x1 > clip_.x1) r.x1 = clip_.x1;
    if (r.y1 > clip_.y1) r.y1 = clip_.y1;
    return r;
  }
  void setClip(Rect r) {
    if (r.x0 < 0) r.x0 = 0;
    if (r.y0 < 0) r.y0 = 0;
    if (r.x1 > w_) r.x1 = w_;
    if (r.y1 > h_) r.y1 = h_;
    clip_ = r;
  }
  void clearClip() { clip_ = Rect{0, 0, w_, h_}; }
  const Rect& clipRect() const { return clip_; }

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
    fillSdfSpans(bx0, by0, bx1, by1, sdf, [](float, int& a0, int& a1, int& b0, int& b1) {
      a0 = -(1 << 30), a1 = 1 << 30, b0 = b1 = 0;
    }, c, alpha, glowR, glowA);
  }
  // The same, visiting per row only x in [a0, a1) and [b0, b1) (spans(py, a0, a1, b0, b1)): the caller
  // promises every pixel left out would draw nothing (a ring's hole and the corners around it).
  template <class F, class Spans>
  void fillSdfSpans(float bx0, float by0, float bx1, float by1, F sdf, Spans spans, Rgb c, float alpha,
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
      int sp[4];
      spans(py, sp[0], sp[1], sp[2], sp[3]);
      for (int k = 0; k < 4; k += 2) {
        const int xa = sp[k] > r.x0 ? sp[k] : r.x0, xb = sp[k + 1] < r.x1 ? sp[k + 1] : r.x1;
        for (int x = xa; x < xb; ++x) {
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
            const float k2 = 1.0f - d * invG;
            a = glowA * k2 * k2;
          } else {
            continue;
          }
          blend(x, y, c, a * alpha);
        }
      }
    }
  }
  // fillSdfSpans' spans for anything drawn within `reach` px of a circle of radius r around (cx, cy)
  // (rings, arcs, their glow): the annulus of each row, with a pixel to spare on every side.
  static void annulusSpans(float py, float cx, float cy, float r, float reach, int& a0, int& a1, int& b0, int& b1) {
    const float dy = py - cy, ro = r + reach + 1, ri = r - reach - 1;
    a0 = a1 = b0 = b1 = 0;
    if (fabsf(dy) >= ro) return;
    const float xo = sqrtf(ro * ro - dy * dy);
    a0 = (int)floorf(cx - xo) - 1;
    b1 = (int)ceilf(cx + xo) + 1;
    if (ri > 1 && fabsf(dy) < ri - 1) {
      const float xi = sqrtf(ri * ri - dy * dy) - 1;  // inside the hole by more than a pixel
      a1 = (int)ceilf(cx - xi) + 1;
      b0 = (int)floorf(cx + xi) - 1;
      if (b0 < a1) a1 = b0 = b1;  // no real hole on this row
    } else {
      a1 = b0 = b1;
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
  // Text along a circle (the rim). The run is centred on angle `a` (radians,
  // 0 = right, +pi/2 = down) at radius r, measured to the text's middle.
  // bottom = false: reads clockwise over the top; true: reads left to right
  // along the bottom, upright for the viewer. `tracking` adds px per glyph.
  void drawTextArc(const Font& f, float cx, float cy, float r, float a, const char* s, Rgb c, float alpha = 1,
                   bool bottom = false, float tracking = 0);
  static float arcTextSpan(const Font& f, float r, const char* s, float tracking = 0);  // radians

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
  Rect clip_;
};

}  // namespace suflet
