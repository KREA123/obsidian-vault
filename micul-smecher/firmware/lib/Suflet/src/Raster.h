// A small, fast vector rasterizer for the eyes and the UI glyphs.
//
//   Path      polygons (any number of closed contours), built through an
//             affine transform; strokes become unions of quads + round caps.
//   Mask      8-bit coverage of a path over its bounding box.
//   Raster    path -> Mask with anti-aliasing: 4 sub-scanlines per pixel row
//             and exact horizontal coverage (fixed point), nonzero or
//             even-odd fill. Then Mask -> RGB565 Canvas with an optional clip
//             mask, solid or linear-gradient paint, a global alpha, and a
//             5-bit alpha blend done in integer math.
//
// All buffers are allocated once (reserve()) and reused every frame: no heap
// traffic in the frame loop. On the ESP32-S3 the big ones land in PSRAM (the
// allocator puts anything above 4 KB there).
#pragma once
#include <math.h>
#include <stdint.h>

#include "Canvas.h"

namespace suflet {

struct Xform {
  float a = 1, b = 0, c = 0, d = 1, e = 0, f = 0;  // x' = a x + c y + e, y' = b x + d y + f
  void apply(float x, float y, float& ox, float& oy) const {
    ox = a * x + c * y + e;
    oy = b * x + d * y + f;
  }
  static Xform translate(float x, float y) {
    Xform t;
    t.e = x;
    t.f = y;
    return t;
  }
  // this * o (apply o first, then this)
  Xform mul(const Xform& o) const {
    Xform r;
    r.a = a * o.a + c * o.b;
    r.b = b * o.a + d * o.b;
    r.c = a * o.c + c * o.d;
    r.d = b * o.c + d * o.d;
    r.e = a * o.e + c * o.f + e;
    r.f = b * o.e + d * o.f + f;
    return r;
  }
  Xform translated(float x, float y) const { return mul(translate(x, y)); }
  Xform rotated(float rad) const {
    Xform r;
    const float cs = cosf(rad), sn = sinf(rad);
    r.a = cs;
    r.b = sn;
    r.c = -sn;
    r.d = cs;
    return mul(r);
  }
  Xform scaled(float sx, float sy) const {
    Xform r;
    r.a = sx;
    r.d = sy;
    return mul(r);
  }
  float scale() const { return sqrtf(fabsf(a * d - b * c)); }
};

class Path {
 public:
  struct Edge {
    float x0, y0, x1, y1;  // y0 < y1
    float dxdy;
    int8_t dir;
  };

  bool reserve(int maxEdges);
  void clear();
  Xform xf;  // applied to every point added

  // contour building (points in local coordinates)
  void moveTo(float x, float y);
  void lineTo(float x, float y);
  void close();

  // shapes; `cw` normalises the winding so unions work with the nonzero rule
  void ellipse(float cx, float cy, float rx, float ry, float rot = 0);
  void circle(float cx, float cy, float r) { ellipse(cx, cy, r, r); }
  void roundRect(float x, float y, float w, float h, float r);
  void polygon(const float* xy, int n);  // n points, closed
  // A stroke of a polyline: one quad per segment, a round disc per vertex.
  void stroke(const float* xy, int n, float width, bool closed = false);
  void strokeArc(float cx, float cy, float r, float a0, float a1, float width);
  void strokeRoundRect(float x, float y, float w, float h, float r, float width);

  int edgeCount() const { return n_; }
  const Edge* edges() const { return e_; }
  bool overflow() const { return overflow_; }
  // bounding box of everything added (device pixels)
  float bx0 = 1e9f, by0 = 1e9f, bx1 = -1e9f, by1 = -1e9f;

  int segmentsFor(float radiusPx) const;  // polygon resolution for a curve

 private:
  void addEdge(float x0, float y0, float x1, float y1);
  void flushContour();
  Edge* e_ = nullptr;
  int n_ = 0, cap_ = 0;
  bool overflow_ = false;
  // the contour being built, in device coordinates
  static constexpr int kMaxContour = 512;
  float cx_[kMaxContour] = {}, cy_[kMaxContour] = {};
  int cn_ = 0;
  bool forceCcw_ = false;
  friend class Raster;
};

// 8-bit coverage over a bounding box, stored as spans: for each row,
// [lo, hi) is where coverage may be non-zero (canvas x) and [f0, f1) a run
// known to be fully covered (255). Only the edge pixels [lo, f0) and
// [f1, hi) are stored in `data`; the solid run is never written or read
// per pixel, which is what makes big flat eyes cheap.
struct Mask {
  struct Row {
    int16_t lo = 0, hi = 0, f0 = 0, f1 = 0;
  };
  int x0 = 0, y0 = 0, w = 0, h = 0;  // bounding box in canvas pixels
  uint8_t* data = nullptr;
  Row* rows = nullptr;
  int cap = 0, rowCap = 0;
  bool empty() const { return w <= 0 || h <= 0; }
  uint8_t at(int x, int y) const {
    if ((unsigned)(x - x0) >= (unsigned)w || (unsigned)(y - y0) >= (unsigned)h) return 0;
    const Row& r = rows[y - y0];
    if (x < r.lo || x >= r.hi) return 0;
    if (x >= r.f0 && x < r.f1) return 255;
    return data[(y - y0) * w + (x - x0)];
  }
  bool reserve(int bytes, int nRows = 0);
};

struct Paint {
  enum Kind : uint8_t { Solid, Linear } kind = Solid;
  Rgb color;
  // linear gradient: t = projection onto p0->p1, stops at t in [0,1]
  float x0 = 0, y0 = 0, x1 = 1, y1 = 0;
  static constexpr int kMaxStops = 8;
  uint8_t nStops = 0;
  float st[kMaxStops];
  Rgb sc[kMaxStops];
  static Paint solid(Rgb c) {
    Paint p;
    p.color = c;
    return p;
  }
  void addStop(float t, Rgb c) {
    if (nStops < kMaxStops) {
      st[nStops] = t;
      sc[nStops] = c;
      ++nStops;
    }
  }
  Rgb sample(float t) const;
};

enum class FillRule : uint8_t { NonZero, EvenOdd };

class Raster {
 public:
  // maxW: widest canvas row; also reserves the default edge pool.
  bool begin(int canvasW, int canvasH);

  // Rasterize `p` into `m` (bbox = path bbox clipped to the canvas).
  void cover(const Path& p, Mask& m, FillRule rule = FillRule::NonZero);
  // Blend paint through `shape` (x clip) into the canvas; marks it dirty.
  void composite(Canvas& cv, const Mask& shape, const Paint& paint, float alpha = 1,
                 const Mask* clip = nullptr);
  // Convenience: cover into the scratch mask and composite.
  void fill(Canvas& cv, const Path& p, const Paint& paint, float alpha = 1, const Mask* clip = nullptr,
            FillRule rule = FillRule::NonZero);
  void fill(Canvas& cv, const Path& p, Rgb c, float alpha = 1, const Mask* clip = nullptr,
            FillRule rule = FillRule::NonZero) {
    fill(cv, p, Paint::solid(c), alpha, clip, rule);
  }
  Mask& scratch() { return scratch_; }
  // A ring (or an arc from a0 to a1 clockwise, radians, round caps) of
  // radius r and width w, drawn analytically over each row's two short
  // annulus spans only: cheap even when it circles the whole glass.
  void ring(Canvas& cv, float cx, float cy, float r, float w, Rgb c, float alpha, float a0 = 0,
            float a1 = 6.2831853f);
  // An anti-aliased circular clip applied to every composite (the glass disc).
  void setDiscClip(float cx, float cy, float r) {
    disc_ = true;
    dcx_ = cx;
    dcy_ = cy;
    dr_ = r;
  }
  void clearDiscClip() { disc_ = false; }

  // statistics (debug overlay)
  uint32_t pixelsCovered = 0, pixelsBlended = 0;

 private:
  int W_ = 0, H_ = 0;
  int16_t* acc_ = nullptr;   // partial coverage per pixel of the current row
  int16_t* run_ = nullptr;   // full-coverage run deltas (prefix-summed)
  uint16_t* order_ = nullptr;  // edges sorted by y0
  int orderCap_ = 0;
  uint16_t* active_ = nullptr;
  struct Cross {  // 8 bytes: two 512-entry arrays stay at 4 KB each (internal RAM on the S3, not PSRAM)
    float x;
    uint32_t p;  // the edge (bits 0-12), its slot in the active list = the tie order (13-22), dir < 0 (23)
    uint32_t id() const { return p & 0x1FFFu; }
    uint32_t k() const { return (p >> 13) & 0x3FFu; }
    int dir() const { return (p >> 23) & 1u ? -1 : 1; }
  };
  Cross* cross_ = nullptr;
  Cross* cross2_ = nullptr;      // the previous sub-scanline's crossings, sorted (cover() swaps the two)
  uint16_t* slotOf_ = nullptr;   // edge -> its slot in active_ (0xFFFF: finished)
  uint16_t* new_ = nullptr;      // edges that became active on this sub-scanline
  int crossCap_ = 0;
  Mask scratch_;
  bool disc_ = false;
  float dcx_ = 0, dcy_ = 0, dr_ = 0;
};

// RGB565 blend with a 0..32 alpha (integer, no float).
static inline uint16_t blend565(uint16_t bg, uint16_t fg, uint32_t a32) {
  uint32_t b = (bg | ((uint32_t)bg << 16)) & 0x07E0F81Fu;
  uint32_t f = (fg | ((uint32_t)fg << 16)) & 0x07E0F81Fu;
  uint32_t r = ((((f - b) * a32) >> 5) + b) & 0x07E0F81Fu;
  return (uint16_t)(r | (r >> 16));
}

}  // namespace suflet
