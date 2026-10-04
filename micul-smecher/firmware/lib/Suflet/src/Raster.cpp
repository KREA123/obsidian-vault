#pragma GCC optimize("O3")  // 1.8: the pixel loops (firmware/PERF.md: -5..-16 % instructions in the sim, +18 KB flash)
#include "Raster.h"

#include <stdlib.h>
#include <string.h>

#include <algorithm>

namespace suflet {

static constexpr float kPi = 3.14159265f;
static constexpr int kSub = 4;  // sub-scanlines per pixel row

// ------------------------------------------------------------------ Path ---

bool Path::reserve(int maxEdges) {
  if (maxEdges <= cap_) return true;
  Edge* ne = (Edge*)realloc(e_, sizeof(Edge) * maxEdges);
  if (!ne) return false;
  e_ = ne;
  cap_ = maxEdges;
  return true;
}

void Path::clear() {
  n_ = 0;
  cn_ = 0;
  overflow_ = false;
  bx0 = by0 = 1e9f;
  bx1 = by1 = -1e9f;
  xf = Xform();
}

void Path::addEdge(float x0, float y0, float x1, float y1) {
  if (y0 == y1) return;  // horizontal edges never cross a scanline
  if (n_ >= cap_) {
    overflow_ = true;
    return;
  }
  Edge& e = e_[n_++];
  if (y0 < y1) {
    e.x0 = x0, e.y0 = y0, e.x1 = x1, e.y1 = y1, e.dir = 1;
  } else {
    e.x0 = x1, e.y0 = y1, e.x1 = x0, e.y1 = y0, e.dir = -1;
  }
  e.dxdy = (e.x1 - e.x0) / (e.y1 - e.y0);
}

void Path::moveTo(float x, float y) {
  flushContour();
  lineTo(x, y);
}

void Path::lineTo(float x, float y) {
  if (cn_ >= kMaxContour) {
    overflow_ = true;
    return;
  }
  float px, py;
  xf.apply(x, y, px, py);
  if (!(px == px) || !(py == py)) return;  // NaN guard
  cx_[cn_] = px;
  cy_[cn_] = py;
  ++cn_;
  if (px < bx0) bx0 = px;
  if (px > bx1) bx1 = px;
  if (py < by0) by0 = py;
  if (py > by1) by1 = py;
}

void Path::close() { flushContour(); }

void Path::flushContour() {
  if (cn_ >= 3) {
    // normalise the winding (positive area) so overlapping pieces union
    // under the nonzero rule; even-odd does not care
    float area = 0;
    for (int i = 0, j = cn_ - 1; i < cn_; j = i++) area += cx_[j] * cy_[i] - cx_[i] * cy_[j];
    if (area >= 0) {
      for (int i = 0, j = cn_ - 1; i < cn_; j = i++) addEdge(cx_[j], cy_[j], cx_[i], cy_[i]);
    } else {
      for (int i = 0, j = cn_ - 1; i < cn_; j = i++) addEdge(cx_[i], cy_[i], cx_[j], cy_[j]);
    }
  }
  cn_ = 0;
}

int Path::segmentsFor(float r) const {
  r *= xf.scale();
  if (r < 1) return 8;
  const float c = 1.0f - 0.2f / r;
  int n = (int)ceilf(kPi / acosf(c < -1 ? -1 : c));
  if (n < 8) n = 8;
  if (n > 128) n = 128;
  return n;
}

void Path::ellipse(float cx, float cy, float rx, float ry, float rot) {
  if (rx <= 0 || ry <= 0) return;
  const int n = segmentsFor(rx > ry ? rx : ry);
  const float cr = cosf(rot), sr = sinf(rot);
  flushContour();
  for (int i = 0; i < n; ++i) {
    const float a = (float)i / n * 2 * kPi;
    const float ux = cosf(a) * rx, uy = sinf(a) * ry;
    lineTo(cx + ux * cr - uy * sr, cy + ux * sr + uy * cr);
  }
  flushContour();
}

void Path::roundRect(float x, float y, float w, float h, float r) {
  if (w <= 0 || h <= 0) return;
  if (r > w * 0.5f) r = w * 0.5f;
  if (r > h * 0.5f) r = h * 0.5f;
  if (r < 0) r = 0;
  flushContour();
  const int q = r > 0.3f ? (segmentsFor(r) + 3) / 4 : 0;
  const float cxs[4] = {x + w - r, x + w - r, x + r, x + r};
  const float cys[4] = {y + r, y + h - r, y + h - r, y + r};
  const float a0s[4] = {-kPi / 2, 0, kPi / 2, kPi};
  for (int c = 0; c < 4; ++c) {
    if (q == 0) {
      lineTo(c == 0 || c == 1 ? x + w : x, c == 1 || c == 2 ? y + h : y);
      continue;
    }
    for (int i = 0; i <= q; ++i) {
      const float a = a0s[c] + (kPi / 2) * i / q;
      lineTo(cxs[c] + cosf(a) * r, cys[c] + sinf(a) * r);
    }
  }
  flushContour();
}

void Path::polygon(const float* xy, int n) {
  flushContour();
  for (int i = 0; i < n; ++i) lineTo(xy[2 * i], xy[2 * i + 1]);
  flushContour();
}

void Path::stroke(const float* xy, int n, float width, bool closedPath) {
  if (n < 1 || width <= 0) return;
  const float hw = width * 0.5f;
  const int segs = closedPath ? n : n - 1;
  // one quad per segment
  for (int i = 0; i < segs; ++i) {
    const float x0 = xy[2 * i], y0 = xy[2 * i + 1];
    const int j = (i + 1) % n;
    const float x1 = xy[2 * j], y1 = xy[2 * j + 1];
    const float dx = x1 - x0, dy = y1 - y0, len = sqrtf(dx * dx + dy * dy);
    if (len < 1e-4f) continue;
    const float nx = -dy / len * hw, ny = dx / len * hw;
    flushContour();
    lineTo(x0 + nx, y0 + ny);
    lineTo(x1 + nx, y1 + ny);
    lineTo(x1 - nx, y1 - ny);
    lineTo(x0 - nx, y0 - ny);
    flushContour();
  }
  // round joins: fill only the wedge on the outer side of each turn (a
  // triangle for gentle turns, a small fan for sharp ones) instead of a disc
  auto dir = [&](int i, int j, float& ux, float& uy) {
    ux = xy[2 * j] - xy[2 * i];
    uy = xy[2 * j + 1] - xy[2 * i + 1];
    const float l = sqrtf(ux * ux + uy * uy);
    if (l < 1e-4f) return false;
    ux /= l;
    uy /= l;
    return true;
  };
  const int first = closedPath ? 0 : 1, last = closedPath ? n : n - 1;
  for (int i = first; i < last; ++i) {
    const int ip = (i + n - 1) % n, in = (i + 1) % n;
    float ax, ay, bx, by;
    if (!dir(ip, i, ax, ay) || !dir(i, in, bx, by)) continue;
    const float cross = ax * by - ay * bx, dot = ax * bx + ay * by;
    const float ang = atan2f(fabsf(cross), dot);
    if (ang < 0.02f) continue;
    // the outer side of the turn (y-down screen coordinates)
    const float s = cross > 0 ? -1.0f : 1.0f;
    const float px = xy[2 * i], py = xy[2 * i + 1];
    const float a0 = atan2f(s * ax, -s * ay);  // angle of the outer normal before the turn
    const int k = ang < 0.6f ? 1 : (int)ceilf(ang / 0.35f);
    flushContour();
    lineTo(px, py);
    const float sweep = cross > 0 ? ang : -ang;  // y-down: cross > 0 turns clockwise
    for (int q = 0; q <= k; ++q) {
      const float t = a0 + sweep * q / k;
      lineTo(px + cosf(t) * hw, py + sinf(t) * hw);
    }
    flushContour();
  }
  // round caps at the open ends
  if (!closedPath) {
    const int sides = segmentsFor(hw);
    const int ends[2] = {0, n - 1};
    for (int e = 0; e < (n > 1 ? 2 : 1); ++e) {
      const int i = ends[e];
      flushContour();
      for (int q = 0; q < sides; ++q) {
        const float a = (float)q / sides * 2 * kPi;
        lineTo(xy[2 * i] + cosf(a) * hw, xy[2 * i + 1] + sinf(a) * hw);
      }
      flushContour();
    }
  }
}

void Path::strokeArc(float cx, float cy, float r, float a0, float a1, float width) {
  const float span = a1 - a0;
  int n = (int)(segmentsFor(r) * fabsf(span) / (2 * kPi)) + 2;
  if (n > 64) n = 64;
  float pts[2 * 65];
  for (int i = 0; i <= n - 1; ++i) {
    const float a = a0 + span * i / (n - 1);
    pts[2 * i] = cx + cosf(a) * r;
    pts[2 * i + 1] = cy + sinf(a) * r;
  }
  stroke(pts, n, width, false);
}

void Path::strokeRoundRect(float x, float y, float w, float h, float r, float width) {
  if (r > w * 0.5f) r = w * 0.5f;
  if (r > h * 0.5f) r = h * 0.5f;
  const int q = 4;
  float pts[2 * 4 * (q + 1)];
  int k = 0;
  const float cxs[4] = {x + w - r, x + w - r, x + r, x + r};
  const float cys[4] = {y + r, y + h - r, y + h - r, y + r};
  const float a0s[4] = {-kPi / 2, 0, kPi / 2, kPi};
  for (int c = 0; c < 4; ++c)
    for (int i = 0; i <= q; ++i) {
      const float a = a0s[c] + (kPi / 2) * i / q;
      pts[2 * k] = cxs[c] + cosf(a) * r;
      pts[2 * k + 1] = cys[c] + sinf(a) * r;
      ++k;
    }
  stroke(pts, k, width, true);
}

// ------------------------------------------------------------------ Mask ---

bool Mask::reserve(int bytes, int nRows) {
  if (bytes > cap) {
    uint8_t* nd = (uint8_t*)realloc(data, bytes);
    if (!nd) return false;
    data = nd;
    cap = bytes;
  }
  if (nRows > rowCap) {
    Row* nr = (Row*)realloc(rows, sizeof(Row) * nRows);
    if (!nr) return false;
    rows = nr;
    rowCap = nRows;
  }
  return true;
}

// ----------------------------------------------------------------- Paint ---

Rgb Paint::sample(float t) const {
  if (kind == Solid || nStops == 0) return color;
  if (t <= st[0]) return sc[0];
  for (int i = 1; i < nStops; ++i)
    if (t <= st[i]) {
      const float span = st[i] - st[i - 1];
      return Rgb::lerp(sc[i - 1], sc[i], span > 1e-6f ? (t - st[i - 1]) / span : 1.0f);
    }
  return sc[nStops - 1];
}

// ---------------------------------------------------------------- Raster ---

bool Raster::begin(int w, int h) {
  W_ = w;
  H_ = h;
  acc_ = (int16_t*)calloc(w + 4, sizeof(int16_t));
  run_ = (int16_t*)calloc(w + 4, sizeof(int16_t));
  crossCap_ = 512;
  cross_ = (Cross*)malloc(sizeof(Cross) * crossCap_);
  orderCap_ = 4096;
  order_ = (uint16_t*)malloc(sizeof(uint16_t) * orderCap_);
  active_ = (uint16_t*)malloc(sizeof(uint16_t) * orderCap_);
  cross2_ = (Cross*)malloc(sizeof(Cross) * crossCap_);
  slotOf_ = (uint16_t*)malloc(sizeof(uint16_t) * orderCap_);
  new_ = (uint16_t*)malloc(sizeof(uint16_t) * orderCap_);
  return acc_ && run_ && cross_ && order_ && active_ && cross2_ && slotOf_ && new_ && scratch_.reserve(64 * 64);
}

void Raster::cover(const Path& p, Mask& m, FillRule rule) {
  m.w = m.h = 0;
  const int n = p.n_ < orderCap_ ? p.n_ : orderCap_;
  if (n < 2 || !acc_) return;
  int x0 = (int)floorf(p.bx0), y0 = (int)floorf(p.by0);
  int x1 = (int)ceilf(p.bx1) + 1, y1 = (int)ceilf(p.by1) + 1;
  if (x0 < 0) x0 = 0;
  if (y0 < 0) y0 = 0;
  if (x1 > W_) x1 = W_;
  if (y1 > H_) y1 = H_;
  if (x1 <= x0 || y1 <= y0) return;
  const int w = x1 - x0, h = y1 - y0;
  if (!m.reserve(w * h, h)) return;
  m.x0 = x0;
  m.y0 = y0;
  m.w = w;
  m.h = h;

  const Path::Edge* E = p.e_;
  for (int i = 0; i < n; ++i) order_[i] = (uint16_t)i;
  std::sort(order_, order_ + n, [E](uint16_t a, uint16_t b) { return E[a].y0 < E[b].y0; });
  int next = 0, nActive = 0;
  const float fx0 = (float)x0;
  const bool nonzero = rule == FillRule::NonZero;
  // The crossings of each sub-scanline in x order, ties in the order the active list holds the edges
  // (1.7 gathered them in that order and insertion-sorted them stably; the tie order decides whether a
  // span closes and reopens at a shared x, which can move a pixel by one level, so it is kept). With
  // many edges (a spiral pupil: 60+ crossings) the active order is far from x order, so instead the
  // previous sub-scanline's sorted crossings are re-evaluated in that order (nearly sorted already) and
  // sorted by (x, slot in the active list): exactly the 1.7 order, at a fraction of the moves.
  Cross* cur = cross_;
  Cross* prev = cross2_;
  int prevN = 0;
  bool warm = false;
  constexpr uint16_t kGone = 0xFFFF;

  for (int row = 0; row < h; ++row) {
    const int y = y0 + row;
    int lo = w, hi = 0;          // touched pixel range (mask-local)
    int fullLo = 0, fullHi = w;  // pixels fully inside on every sub-scanline
    bool single = true;          // every sub-scanline was one span (then the interior is solid)
    int subs = 0;
    for (int s = 0; s < kSub; ++s) {
      const float sy = y + (s + 0.5f) / kSub;
      int nNew = 0;
      while (next < n && E[order_[next]].y0 <= sy) {
        const uint16_t id = order_[next++];
        slotOf_[id] = (uint16_t)nActive;
        active_[nActive++] = id;
        new_[nNew++] = id;
      }
      for (int i = 0; i < nActive;) {  // finished edges leave; the last one takes the slot (as in 1.7)
        const uint16_t id = active_[i];
        if (E[id].y1 <= sy) {
          slotOf_[id] = kGone;
          if (i < --nActive) {
            active_[i] = active_[nActive];
            slotOf_[active_[i]] = (uint16_t)i;
          }
          continue;
        }
        ++i;
      }
      int nc = 0;
      bool nan = false;
      auto put = [&](uint16_t id, uint16_t k) {
        const Path::Edge& e = E[id];
        const float cx = e.x0 + (sy - e.y0) * e.dxdy - fx0;
        Cross& c = cur[nc++];
        c.x = cx;
        c.p = (uint32_t)id | ((uint32_t)k << 13) | (e.dir < 0 ? 1u << 23 : 0u);
        nan |= !(cx == cx);
      };
      if (nActive > crossCap_) {  // more than 1.7 kept (it dropped the rest in slot order): 1.7's way
        for (int i = 0; i < crossCap_; ++i) put(active_[i], (uint16_t)i);
        nan = true;
      } else if (warm) {
        for (int i = 0; i < prevN; ++i) {
          const uint16_t id = (uint16_t)prev[i].id(), k = slotOf_[id];
          if (k != kGone) put(id, k);
        }
        for (int i = 0; i < nNew; ++i)
          if (slotOf_[new_[i]] != kGone) put(new_[i], slotOf_[new_[i]]);
      } else {
        for (int i = 0; i < nActive; ++i) put(active_[i], (uint16_t)i);
      }
      if (nan) {  // NaN (never from lineTo, which drops NaN points) or overflow: 1.7's sort, verbatim
        for (int i = 0; i < nc; ++i) prev[cur[i].k()] = cur[i];
        Cross* t = cur;
        cur = prev;
        prev = t;
        for (int i = 1; i < nc; ++i) {
          const Cross c = cur[i];
          int j = i - 1;
          while (j >= 0 && cur[j].x > c.x) {
            cur[j + 1] = cur[j];
            --j;
          }
          cur[j + 1] = c;
        }
        warm = false;
      } else {
        auto after = [](const Cross& a, const Cross& b) { return a.x > b.x || (a.x == b.x && a.k() > b.k()); };
        for (int i = 1; i < nc; ++i) {
          if (!after(cur[i - 1], cur[i])) continue;  // already in place (most of them)
          const Cross c = cur[i];
          int j = i - 1;
          do {
            cur[j + 1] = cur[j];
            --j;
          } while (j >= 0 && after(cur[j], c));
          cur[j + 1] = c;
        }
        warm = true;
      }
      // this order is the next sub-scanline's starting point
      Cross* const C = cur;
      cur = prev;
      prev = C;
      prevN = nc;
      if (nc < 2) {
        single = false;
        continue;
      }
      int wind = 0, spans = 0;
      float start = 0;
      for (int i = 0; i < nc; ++i) {
        const bool was = nonzero ? wind != 0 : (wind & 1);
        wind += C[i].dir();
        const bool is = nonzero ? wind != 0 : (wind & 1);
        if (!was && is) {
          start = C[i].x;
        } else if (was && !is) {
          float xa = start, xb = C[i].x;
          if (xa < 0) xa = 0;
          if (xb > (float)w) xb = (float)w;
          if (xb <= xa) continue;
          const int fa = (int)(xa * 256.0f), fb = (int)(xb * 256.0f);
          const int ia = fa >> 8, ib = fb >> 8;
          ++spans;
          if (ia < lo) lo = ia;
          if (ib + 1 > hi) hi = ib + 1;
          if (ia == ib) {
            acc_[ia] += (int16_t)((fb - fa) >> 2);
          } else {
            acc_[ia] += (int16_t)((256 - (fa & 255)) >> 2);
            run_[ia + 1] += 64;
            run_[ib] -= 64;
            acc_[ib] += (int16_t)((fb & 255) >> 2);
          }
          // the whole pixels this span covers: [ia + (fa & 255 ? 1 : 0), ib)
          const int c0 = ia + ((fa & 255) ? 1 : 0), c1 = ib;
          if (c0 > fullLo) fullLo = c0;
          if (c1 < fullHi) fullHi = c1;
        }
      }
      if (spans != 1) single = false;
      ++subs;
    }
    Mask::Row& R = m.rows[row];
    if (hi > w) hi = w;
    if (lo >= hi) {
      R.lo = R.hi = R.f0 = R.f1 = (int16_t)(x0);
      continue;
    }
    // a solid interior: only when every sub-scanline was exactly one span
    int f0 = hi, f1 = hi;
    if (single && subs == kSub && fullHi > fullLo) {
      f0 = fullLo;
      f1 = fullHi;
    }
    uint8_t* out = m.data + row * w;
    int r = 0;
    for (int x = lo; x < f0; ++x) {
      r += run_[x];
      const int v = r + acc_[x];
      out[x] = (uint8_t)(v > 255 ? 255 : (v < 0 ? 0 : v));
      run_[x] = 0;
      acc_[x] = 0;
    }
    if (f1 > f0) {
      // a single-span interior: every sub-scanline covers each of its pixels fully (64 each, from the
      // run or, where a span starts exactly on the pixel, from acc), so coverage there is exactly 256
      // and the running sum after it is 256 - acc at its last pixel: no need to walk the run
      r = 256 - acc_[f1 - 1];
      memset(run_ + f0, 0, sizeof(int16_t) * (size_t)(f1 - f0));
      memset(acc_ + f0, 0, sizeof(int16_t) * (size_t)(f1 - f0));
    }
    for (int x = f1 > f0 ? f1 : f0; x < hi; ++x) {
      r += run_[x];
      const int v = r + acc_[x];
      out[x] = (uint8_t)(v > 255 ? 255 : (v < 0 ? 0 : v));
      run_[x] = 0;
      acc_[x] = 0;
    }
    run_[hi] = acc_[hi] = 0;
    if (hi + 1 <= w + 1) run_[hi + 1] = acc_[hi + 1] = 0;
    R.lo = (int16_t)(x0 + lo);
    R.hi = (int16_t)(x0 + hi);
    R.f0 = (int16_t)(x0 + f0);
    R.f1 = (int16_t)(x0 + (f1 > f0 ? f1 : f0));
  }
}

void Raster::composite(Canvas& cv, const Mask& sm, const Paint& paint, float alpha, const Mask* clip) {
  if (sm.empty() || alpha <= 0.004f) return;
  int x0 = sm.x0, y0 = sm.y0, x1 = sm.x0 + sm.w, y1 = sm.y0 + sm.h;
  if (clip) {
    if (clip->empty()) return;
    if (clip->x0 > x0) x0 = clip->x0;
    if (clip->y0 > y0) y0 = clip->y0;
    if (clip->x0 + clip->w < x1) x1 = clip->x0 + clip->w;
    if (clip->y0 + clip->h < y1) y1 = clip->y0 + clip->h;
  }
  const Rect& cr = cv.clipRect();
  if (x0 < cr.x0) x0 = cr.x0;
  if (y0 < cr.y0) y0 = cr.y0;
  if (x1 > cr.x1) x1 = cr.x1;
  if (y1 > cr.y1) y1 = cr.y1;
  // the left edge with no clip but the canvas: a gradient run is stepped from where an unclipped
  // composite starts it, so drawing under a smaller clip gives exactly the same pixels (1.8)
  int xFull0 = sm.x0;
  if (clip && clip->x0 > xFull0) xFull0 = clip->x0;
  if (xFull0 < 0) xFull0 = 0;
  if (disc_) {  // rows and columns outside the disc never draw
    const int dy0 = (int)floorf(dcy_ - dr_), dy1 = (int)ceilf(dcy_ + dr_);
    const int dx0 = (int)floorf(dcx_ - dr_), dx1 = (int)ceilf(dcx_ + dr_);
    if (y0 < dy0) y0 = dy0;
    if (y1 > dy1) y1 = dy1;
    if (x0 < dx0) x0 = dx0;
    if (x1 > dx1) x1 = dx1;
    if (xFull0 < dx0) xFull0 = dx0;
  }
  if (x1 <= x0 || y1 <= y0) return;
  const uint32_t ga = (uint32_t)(alpha >= 1 ? 256 : alpha * 256.0f);  // 0..256
  uint16_t* fb = cv.data();
  const int W = cv.width();
  const bool solid = paint.kind == Paint::Solid || paint.nStops == 0;
  const uint16_t fg = paint.color.to565();
  // gradient: a 64-entry colour ramp, sampled by the projection on p0->p1
  uint16_t lut[64];
  float gdx = 0, gdy = 0, gk = 0;
  if (!solid) {
    for (int i = 0; i < 64; ++i) lut[i] = paint.sample(i / 63.0f).to565();
    gdx = paint.x1 - paint.x0;
    gdy = paint.y1 - paint.y0;
    const float l2 = gdx * gdx + gdy * gdy;
    gk = l2 > 1e-6f ? 63.0f / l2 : 0;
  }
  const float gstep = gdx * gk;
  const uint32_t fullA32 = (255u * ga) >> 8;  // coverage 255 with the global alpha
  const uint32_t fullA = (fullA32 * 33) >> 8;
  int minX = x1, maxX = x0 - 1, minY = y1, maxY = y0 - 1;
  for (int y = y0; y < y1; ++y) {
    const Mask::Row& sr = sm.rows[y - sm.y0];
    int lo = sr.lo > x0 ? sr.lo : x0, hi = sr.hi < x1 ? sr.hi : x1;
    int loFull = sr.lo > xFull0 ? sr.lo : xFull0;
    int f0 = sr.f0, f1 = sr.f1;
    const uint8_t* srow = sm.data + (y - sm.y0) * sm.w - sm.x0;
    const Mask::Row* crw = nullptr;
    const uint8_t* crow = nullptr;
    if (clip) {
      crw = &clip->rows[y - clip->y0];
      if (crw->lo > lo) lo = crw->lo;
      if (crw->lo > loFull) loFull = crw->lo;
      if (crw->hi < hi) hi = crw->hi;
      if (crw->f0 > f0) f0 = crw->f0;  // solid where both are solid
      if (crw->f1 < f1) f1 = crw->f1;
      crow = clip->data + (y - clip->y0) * clip->w - clip->x0;
    }
    // the disc: this row's inside span; 1 px soft edge
    float dl = -1e9f, dr = 1e9f;
    if (disc_) {
      const float dy = y + 0.5f - dcy_, q = dr_ * dr_ - dy * dy;
      if (q <= 0) continue;
      const float half = sqrtf(q);
      dl = dcx_ - half;
      dr = dcx_ + half;
      const int il = (int)ceilf(dl + 0.5f), ir = (int)floorf(dr - 0.5f);
      if (il > f0) f0 = il;
      if (ir < f1) f1 = ir;
      const int l2 = (int)floorf(dl - 0.5f), r2 = (int)ceilf(dr + 0.5f);
      if (l2 > lo) lo = l2;
      if (l2 > loFull) loFull = l2;
      if (r2 < hi) hi = r2;
    }
    const int f0Full = f0 > loFull ? f0 : loFull;  // where an unclipped composite starts the solid run
    if (hi <= lo) continue;
    if (f0 < lo) f0 = lo;
    if (f0 > hi) f0 = hi;  // never read past the row's coverage
    if (f1 > hi) f1 = hi;
    if (f1 < f0) f1 = f0;
    uint16_t* drow = fb + y * W;
    bool rowAny = false;
    // edge pixels (and anything not provably solid): the general path
    auto px = [&](int x) {
      uint32_t a = (x >= sr.f0 && x < sr.f1) ? 255u : srow[x];
      if (!a) return;
      if (crow) {
        const uint32_t c = (x >= crw->f0 && x < crw->f1) ? 255u : crow[x];
        a = (a * c + 128) >> 8;
        if (!a) return;
      }
      a = (a * ga) >> 8;
      if (disc_) {
        const float xc = x + 0.5f;
        if (xc < dl + 0.5f || xc > dr - 0.5f) {
          const float k = xc < dl + 0.5f ? xc - dl + 0.5f : dr - xc + 0.5f;
          if (k <= 0) return;
          if (k < 1) a = (uint32_t)(a * k);
        }
      }
      uint16_t c = fg;
      if (!solid) {
        int gi = (int)(((x + 0.5f - paint.x0) * gdx + (y + 0.5f - paint.y0) * gdy) * gk);
        c = lut[gi < 0 ? 0 : (gi > 63 ? 63 : gi)];
      }
      const uint32_t a32 = (a * 33) >> 8;  // 0..255 -> 0..32
      if (a32 >= 32) drow[x] = c;
      else if (a32) {
        drow[x] = blend565(drow[x], c, a32);
        ++pixelsBlended;
      } else {
        return;
      }
      ++pixelsCovered;
      rowAny = true;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
    };
    for (int x = lo; x < f0; ++x) px(x);
    if (f1 > f0) {  // the solid run: no mask reads, no per-pixel tests
      rowAny = true;
      if (f0 < minX) minX = f0;
      if (f1 - 1 > maxX) maxX = f1 - 1;
      pixelsCovered += (uint32_t)(f1 - f0);
      if (solid && fullA >= 32) {
        uint16_t* d = drow + f0;
        int k = f1 - f0;
        if (k > 1 && ((uintptr_t)d & 2)) {
          *d++ = fg;
          --k;
        }
        uint32_t* d32 = (uint32_t*)d;
        const uint32_t two = (uint32_t)fg | ((uint32_t)fg << 16);
        for (int i = 0; i < (k >> 1); ++i) d32[i] = two;
        if (k & 1) d[k - 1] = fg;
      } else if (solid) {
        for (int x = f0; x < f1; ++x) drow[x] = blend565(drow[x], fg, fullA);
      } else {
        float gt = ((f0Full + 0.5f - paint.x0) * gdx + (y + 0.5f - paint.y0) * gdy) * gk;
        for (int x = f0Full; x < f0; ++x) gt += gstep;  // the same steps as an unclipped run (1.8)
        for (int x = f0; x < f1; ++x, gt += gstep) {
          int gi = (int)gt;
          const uint16_t c = lut[gi < 0 ? 0 : (gi > 63 ? 63 : gi)];
          drow[x] = fullA >= 32 ? c : blend565(drow[x], c, fullA);
        }
      }
    }
    for (int x = f1 > f0 ? f1 : f0; x < hi; ++x) px(x);
    if (rowAny) {
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  if (maxX >= minX && maxY >= minY) cv.markDirty(Rect{minX, minY, maxX + 1, maxY + 1});
}

void Raster::ring(Canvas& cv, float cx, float cy, float r, float w, Rgb c, float alpha, float a0, float a1) {
  if (alpha <= 0.004f || w <= 0 || r <= 0) return;
  const float hw = w * 0.5f;
  const bool full = a1 - a0 >= 6.2831f;
  float span = a1 - a0;
  if (span < 0) span = 0;
  const float e0x = cx + cosf(a0) * r, e0y = cy + sinf(a0) * r;
  const float e1x = cx + cosf(a1) * r, e1y = cy + sinf(a1) * r;
  const Rect& cr = cv.clipRect();
  const float ro = r + hw + 1.0f, ri = r - hw - 1.0f;
  int y0 = (int)floorf(cy - ro), y1 = (int)ceilf(cy + ro);
  if (y0 < cr.y0) y0 = cr.y0;
  if (y1 > cr.y1) y1 = cr.y1;
  const uint16_t fg = c.to565();
  const uint32_t ga = (uint32_t)(alpha >= 1 ? 256 : alpha * 256.0f);
  const uint32_t solidA32 = (((255u * ga) >> 8) * 33) >> 8;  // what a fully covered pixel gets (cov = 1)
  uint16_t* fb = cv.data();
  const int W = cv.width();
  int minX = cr.x1, maxX = cr.x0 - 1, minY = y1, maxY = y0 - 1;
  for (int y = y0; y < y1; ++y) {
    const float dy = y + 0.5f - cy;
    if (fabsf(dy) >= ro) continue;
    const float xo = sqrtf(ro * ro - dy * dy);
    const float xi = (ri > 0 && fabsf(dy) < ri) ? sqrtf(ri * ri - dy * dy) : 0;
    // two spans (left and right of the hole), or one through the middle
    float sx[2][2] = {{cx - xo, cx - xi}, {cx + xi, cx + xo}};
    const int nspan = xi > 0 ? 2 : 1;
    if (nspan == 1) sx[0][1] = cx + xo;
    uint16_t* drow = fb + y * W;
    bool any = false;
    // a full ring: the pixels at least half a pixel (+ a safety margin) inside both edges are fully
    // covered (cov >= 1): one constant blend, no square root (the map's rim vignette: 36 K px a frame)
    int sl0 = 1, sl1 = 0, sr0 = 1, sr1 = 0;  // [sl0, sl1] and [sr0, sr1]: solid on the left / right
    if (full && solidA32) {
      const double ra = r - hw + 0.5 + 0.25, rb = r + hw - 0.5 - 0.25, dd = (double)dy * dy;
      if (ra < rb && dd < rb * rb) {
        const double ob = sqrt(rb * rb - dd), ia = ra > 0 && ra * ra > dd ? sqrt(ra * ra - dd) : 0.0;
        sr0 = (int)ceil(cx + ia - 0.5) + 1;
        sr1 = (int)floor(cx + ob - 0.5) - 1;
        sl0 = (int)ceil(cx - ob - 0.5) + 1;
        sl1 = (int)floor(cx - ia - 0.5) - 1;
        if (ia == 0.0) {  // the row crosses the hole's top or bottom: one solid run through the middle
          sl1 = sr1;
          sr0 = 1, sr1 = 0;
        }
      }
    }
    for (int k = 0; k < nspan; ++k) {
      int xa = (int)floorf(sx[k][0]), xb = (int)ceilf(sx[k][1]);
      if (xa < cr.x0) xa = cr.x0;
      if (xb > cr.x1) xb = cr.x1;
      for (int x = xa; x < xb; ++x) {
        if ((x >= sl0 && x <= sl1) || (x >= sr0 && x <= sr1)) {  // the solid run: one tight loop to its end
          const int e = x >= sl0 && x <= sl1 ? sl1 : sr1, last = e < xb - 1 ? e : xb - 1;
          if (solidA32 >= 32) {
            for (int q = x; q <= last; ++q) drow[q] = fg;
          } else {
            for (int q = x; q <= last; ++q) drow[q] = blend565(drow[q], fg, solidA32);
          }
          any = true;
          if (x < minX) minX = x;
          if (last > maxX) maxX = last;
          x = last;
          continue;
        }
        const float dx = x + 0.5f - cx;
        const float d = sqrtf(dx * dx + dy * dy);
        float cov = hw + 0.5f - fabsf(d - r);
        if (!full) {
          float ang = atan2f(dy, dx) - a0;
          while (ang < 0) ang += 6.2831853f;
          while (ang >= 6.2831853f) ang -= 6.2831853f;
          if (ang > span) {  // outside the arc: only the round caps
            const float d0 = sqrtf((x + 0.5f - e0x) * (x + 0.5f - e0x) + (y + 0.5f - e0y) * (y + 0.5f - e0y));
            const float d1 = sqrtf((x + 0.5f - e1x) * (x + 0.5f - e1x) + (y + 0.5f - e1y) * (y + 0.5f - e1y));
            cov = hw + 0.5f - (d0 < d1 ? d0 : d1);
          }
        }
        if (cov <= 0) continue;
        if (cov > 1) cov = 1;
        const uint32_t a = ((uint32_t)(cov * 255.0f) * ga) >> 8;
        const uint32_t a32 = (a * 33) >> 8;
        if (!a32) continue;
        drow[x] = a32 >= 32 ? fg : blend565(drow[x], fg, a32);
        any = true;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
      }
    }
    if (any) {
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  if (maxX >= minX && maxY >= minY) cv.markDirty(Rect{minX, minY, maxX + 1, maxY + 1});
}

void Raster::fill(Canvas& cv, const Path& p, const Paint& paint, float alpha, const Mask* clip, FillRule rule) {
  // nothing of it inside the canvas clip (a frame repairs a few rectangles, drawing the UI under each one's
  // clip): composite() would draw nothing, so skip the coverage too (1.8)
  const Rect& cr = cv.clipRect();
  if (p.bx1 + 1 < cr.x0 || p.bx0 - 1 > cr.x1 || p.by1 + 1 < cr.y0 || p.by0 - 1 > cr.y1 || p.bx1 < p.bx0) {
    scratch_.w = scratch_.h = 0;
    return;
  }
  cover(p, scratch_, rule);
  composite(cv, scratch_, paint, alpha, clip);
}

}  // namespace suflet
