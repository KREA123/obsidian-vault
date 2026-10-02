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
  // round joins and caps; the disc gets fewer sides than a big circle
  const int sides = segmentsFor(hw);
  for (int i = 0; i < n; ++i) {
    flushContour();
    for (int k = 0; k < sides; ++k) {
      const float a = (float)k / sides * 2 * kPi;
      lineTo(xy[2 * i] + cosf(a) * hw, xy[2 * i + 1] + sinf(a) * hw);
    }
    flushContour();
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

bool Mask::reserve(int bytes) {
  if (bytes <= cap) return true;
  uint8_t* nd = (uint8_t*)realloc(data, bytes);
  if (!nd) return false;
  data = nd;
  cap = bytes;
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
  return acc_ && run_ && cross_ && order_ && active_ && scratch_.reserve(64 * 64);
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
  if (!m.reserve(w * h)) return;
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

  for (int row = 0; row < h; ++row) {
    const int y = y0 + row;
    bool any = false;
    for (int s = 0; s < kSub; ++s) {
      const float sy = y + (s + 0.5f) / kSub;
      while (next < n && E[order_[next]].y0 <= sy) active_[nActive++] = order_[next++];
      int nc = 0;
      for (int i = 0; i < nActive;) {
        const Path::Edge& e = E[active_[i]];
        if (e.y1 <= sy) {  // finished: remove (order does not matter)
          active_[i] = active_[--nActive];
          continue;
        }
        if (e.y0 <= sy && nc < crossCap_) {
          cross_[nc].x = e.x0 + (sy - e.y0) * e.dxdy - fx0;
          cross_[nc].dir = e.dir;
          ++nc;
        }
        ++i;
      }
      if (nc < 2) continue;
      // insertion sort: crossings are few and nearly sorted row to row
      for (int i = 1; i < nc; ++i) {
        const Cross c = cross_[i];
        int j = i - 1;
        while (j >= 0 && cross_[j].x > c.x) {
          cross_[j + 1] = cross_[j];
          --j;
        }
        cross_[j + 1] = c;
      }
      int wind = 0;
      float start = 0;
      for (int i = 0; i < nc; ++i) {
        const bool was = nonzero ? wind != 0 : (wind & 1);
        wind += cross_[i].dir;
        const bool is = nonzero ? wind != 0 : (wind & 1);
        if (!was && is) {
          start = cross_[i].x;
        } else if (was && !is) {
          float xa = start, xb = cross_[i].x;
          if (xa < 0) xa = 0;
          if (xb > (float)w) xb = (float)w;
          if (xb <= xa) continue;
          const int fa = (int)(xa * 256.0f), fb = (int)(xb * 256.0f);
          const int ia = fa >> 8, ib = fb >> 8;
          any = true;
          if (ia == ib) {
            acc_[ia] += (int16_t)((fb - fa) >> 2);
          } else {
            acc_[ia] += (int16_t)((256 - (fa & 255)) >> 2);
            run_[ia + 1] += 64;
            run_[ib] -= 64;
            acc_[ib] += (int16_t)((fb & 255) >> 2);
          }
        }
      }
    }
    uint8_t* out = m.data + row * w;
    if (!any) {
      memset(out, 0, w);
      continue;
    }
    int r = 0;
    for (int x = 0; x < w; ++x) {
      r += run_[x];
      int v = r + acc_[x];
      out[x] = (uint8_t)(v > 255 ? 255 : (v < 0 ? 0 : v));
      run_[x] = 0;
      acc_[x] = 0;
    }
    run_[w] = run_[w + 1] = 0;
    acc_[w] = acc_[w + 1] = 0;
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
  if (disc_) {  // rows and columns outside the disc never draw
    const int dy0 = (int)floorf(dcy_ - dr_), dy1 = (int)ceilf(dcy_ + dr_);
    const int dx0 = (int)floorf(dcx_ - dr_), dx1 = (int)ceilf(dcx_ + dr_);
    if (y0 < dy0) y0 = dy0;
    if (y1 > dy1) y1 = dy1;
    if (x0 < dx0) x0 = dx0;
    if (x1 > dx1) x1 = dx1;
    if (x1 <= x0 || y1 <= y0) return;
  }
  int minX = x1, maxX = x0, minY = y1, maxY = y0;
  for (int y = y0; y < y1; ++y) {
    // the disc: the inside span of this row, with a 1 px soft edge
    float dl = -1e9f, dr = 1e9f;
    if (disc_) {
      const float dy = y + 0.5f - dcy_, q = dr_ * dr_ - dy * dy;
      if (q <= 0) continue;
      const float half = sqrtf(q);
      dl = dcx_ - half;
      dr = dcx_ + half;
    }
    const uint8_t* srow = sm.data + (y - sm.y0) * sm.w - sm.x0;
    const uint8_t* crow = clip ? clip->data + (y - clip->y0) * clip->w - clip->x0 : nullptr;
    uint16_t* drow = fb + y * W;
    float gt = 0;
    if (!solid) gt = ((x0 + 0.5f - paint.x0) * gdx + (y + 0.5f - paint.y0) * gdy) * gk;
    const float gstep = gdx * gk;
    bool rowAny = false;
    for (int x = x0; x < x1; ++x, gt += gstep) {
      uint32_t a = srow[x];
      if (!a) continue;
      if (crow) {
        a = (a * crow[x] + 128) >> 8;
        if (!a) continue;
      }
      a = (a * ga) >> 8;
      if (disc_) {
        const float xc = x + 0.5f;
        if (xc < dl + 0.5f || xc > dr - 0.5f) {
          float k = xc < dl + 0.5f ? xc - dl + 0.5f : dr - xc + 0.5f;
          if (k <= 0) continue;
          if (k < 1) a = (uint32_t)(a * k);
        }
      }
      uint16_t c = fg;
      if (!solid) {
        int gi = (int)gt;
        gi = gi < 0 ? 0 : (gi > 63 ? 63 : gi);
        c = lut[gi];
      }
      const uint32_t a32 = (a * 33) >> 8;  // 0..255 -> 0..32
      if (a32 >= 32) {
        drow[x] = c;
      } else if (a32) {
        drow[x] = blend565(drow[x], c, a32);
        ++pixelsBlended;
      } else {
        continue;
      }
      ++pixelsCovered;
      rowAny = true;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
    }
    if (rowAny) {
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  if (maxX >= minX && maxY >= minY) cv.markDirty(Rect{minX, minY, maxX + 1, maxY + 1});
}

void Raster::fill(Canvas& cv, const Path& p, const Paint& paint, float alpha, const Mask* clip, FillRule rule) {
  cover(p, scratch_, rule);
  composite(cv, scratch_, paint, alpha, clip);
}

}  // namespace suflet
