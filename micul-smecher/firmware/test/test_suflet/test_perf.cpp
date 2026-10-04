// The 1.8 performance pass (firmware/PERF.md): every fast path is checked against the implementation it
// replaced (kept here, verbatim, as the reference) on random inputs, and must give the same pixels.
#include <unity.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

#include "Canvas.h"
#include "Raster.h"
#include "Rng.h"

using namespace suflet;

namespace {

// ------------------------------------------------- the 1.7 rasterizer ---

// Raster::cover as it was in 1.7.0 (insertion sort of the crossings in gather order; the interior's run
// summed pixel by pixel). Same inputs, its own buffers.
struct RefCover {
  int W, H;
  std::vector<int16_t> acc, run;
  std::vector<uint16_t> order, active;
  struct Cross {
    float x;
    int8_t dir;
  };
  std::vector<Cross> cross;
  RefCover(int w, int h) : W(w), H(h), acc(w + 4), run(w + 4), order(4096), active(4096), cross(512) {}

  struct Out {
    int x0 = 0, y0 = 0, w = 0, h = 0;
    std::vector<uint8_t> data;
    std::vector<Mask::Row> rows;
  };

  Out cover(const Path& p, FillRule rule) {
    Out m;
    const int n = p.edgeCount() < 4096 ? p.edgeCount() : 4096;
    if (n < 2) return m;
    int x0 = (int)floorf(p.bx0), y0 = (int)floorf(p.by0);
    int x1 = (int)ceilf(p.bx1) + 1, y1 = (int)ceilf(p.by1) + 1;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > W) x1 = W;
    if (y1 > H) y1 = H;
    if (x1 <= x0 || y1 <= y0) return m;
    const int w = x1 - x0, h = y1 - y0;
    m.x0 = x0;
    m.y0 = y0;
    m.w = w;
    m.h = h;
    m.data.assign((size_t)w * h, 0);
    m.rows.assign(h, Mask::Row());
    const Path::Edge* E = p.edges();
    for (int i = 0; i < n; ++i) order[i] = (uint16_t)i;
    std::sort(order.begin(), order.begin() + n, [E](uint16_t a, uint16_t b) { return E[a].y0 < E[b].y0; });
    int next = 0, nActive = 0;
    const float fx0 = (float)x0;
    const bool nonzero = rule == FillRule::NonZero;
    for (int row = 0; row < h; ++row) {
      const int y = y0 + row;
      int lo = w, hi = 0, fullLo = 0, fullHi = w, subs = 0;
      bool single = true;
      for (int s = 0; s < 4; ++s) {
        const float sy = y + (s + 0.5f) / 4;
        while (next < n && E[order[next]].y0 <= sy) active[nActive++] = order[next++];
        int nc = 0;
        for (int i = 0; i < nActive;) {
          const Path::Edge& e = E[active[i]];
          if (e.y1 <= sy) {
            active[i] = active[--nActive];
            continue;
          }
          if (e.y0 <= sy && nc < 512) {
            cross[nc].x = e.x0 + (sy - e.y0) * e.dxdy - fx0;
            cross[nc].dir = e.dir;
            ++nc;
          }
          ++i;
        }
        if (nc < 2) {
          single = false;
          continue;
        }
        for (int i = 1; i < nc; ++i) {
          const Cross c = cross[i];
          int j = i - 1;
          while (j >= 0 && cross[j].x > c.x) {
            cross[j + 1] = cross[j];
            --j;
          }
          cross[j + 1] = c;
        }
        int wind = 0, spans = 0;
        float start = 0;
        for (int i = 0; i < nc; ++i) {
          const bool was = nonzero ? wind != 0 : (wind & 1);
          wind += cross[i].dir;
          const bool is = nonzero ? wind != 0 : (wind & 1);
          if (!was && is) {
            start = cross[i].x;
          } else if (was && !is) {
            float xa = start, xb = cross[i].x;
            if (xa < 0) xa = 0;
            if (xb > (float)w) xb = (float)w;
            if (xb <= xa) continue;
            const int fa = (int)(xa * 256.0f), fb = (int)(xb * 256.0f);
            const int ia = fa >> 8, ib = fb >> 8;
            ++spans;
            if (ia < lo) lo = ia;
            if (ib + 1 > hi) hi = ib + 1;
            if (ia == ib) {
              acc[ia] += (int16_t)((fb - fa) >> 2);
            } else {
              acc[ia] += (int16_t)((256 - (fa & 255)) >> 2);
              run[ia + 1] += 64;
              run[ib] -= 64;
              acc[ib] += (int16_t)((fb & 255) >> 2);
            }
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
      int f0 = hi, f1 = hi;
      if (single && subs == 4 && fullHi > fullLo) {
        f0 = fullLo;
        f1 = fullHi;
      }
      uint8_t* out = m.data.data() + (size_t)row * w;
      int r = 0;
      for (int x = lo; x < f0; ++x) {
        r += run[x];
        const int v = r + acc[x];
        out[x] = (uint8_t)(v > 255 ? 255 : (v < 0 ? 0 : v));
        run[x] = acc[x] = 0;
      }
      if (f1 > f0) {
        for (int x = f0; x < f1; ++x) r += run[x];
        for (int x = f0; x < f1; ++x) run[x] = acc[x] = 0;
      }
      for (int x = f1 > f0 ? f1 : f0; x < hi; ++x) {
        r += run[x];
        const int v = r + acc[x];
        out[x] = (uint8_t)(v > 255 ? 255 : (v < 0 ? 0 : v));
        run[x] = acc[x] = 0;
      }
      run[hi] = acc[hi] = 0;
      if (hi + 1 <= w + 1) run[hi + 1] = acc[hi + 1] = 0;
      R.lo = (int16_t)(x0 + lo);
      R.hi = (int16_t)(x0 + hi);
      R.f0 = (int16_t)(x0 + f0);
      R.f1 = (int16_t)(x0 + (f1 > f0 ? f1 : f0));
    }
    return m;
  }
};

float frand(Rng& r, float a, float b) { return a + (b - a) * r.uniform(); }

// One random path of the kinds the eyes and the UI draw.
void randomPath(Rng& r, Path& p, int kind) {
  p.clear();
  const float cx = frand(r, -40, 520), cy = frand(r, -40, 520), s = frand(r, 4, 160);
  switch (kind % 7) {
    case 0:  // ellipses, overlapping
      for (int i = 0, n = 1 + (int)(r.uniform() * 4); i < n; ++i)
        p.ellipse(cx + frand(r, -s, s) * 0.5f, cy + frand(r, -s, s) * 0.5f, frand(r, 1, s), frand(r, 1, s), frand(r, 0, 3));
      break;
    case 1: {  // a spiral stroke (the Lollipop pupil): 60+ crossings a row
      float pts[2 * 91];
      const float rot = frand(r, 0, 6.28f);
      for (int i = 0; i <= 90; ++i) {
        const float q = i / 90.0f, a = rot + q * 6.2831853f * 2.3f;
        pts[2 * i] = cx + cosf(a) * q * s;
        pts[2 * i + 1] = cy + sinf(a) * q * s * frand(r, 0.8f, 1.0f);
      }
      p.stroke(pts, 91, frand(r, 1, s * 0.2f));
      break;
    }
    case 2: {  // rectangles sharing edges exactly (ties in x between crossings)
      const float x = floorf(cx), y = floorf(cy), w = floorf(s * 0.5f) + 1;
      for (int i = 0; i < 4; ++i) {
        const float pts[8] = {x + i * w, y, x + (i + 1) * w, y, x + (i + 1) * w, y + w * (1 + i % 2), x + i * w, y + w * (1 + i % 2)};
        p.polygon(pts, 4);
      }
      break;
    }
    case 3:  // a ring (even-odd hole) and a crescent
      p.ellipse(cx, cy, s, s * 0.8f);
      p.ellipse(cx + frand(r, -s, s) * 0.3f, cy, s * 0.5f, s * 0.5f);
      break;
    case 4: {  // a random star polygon, self-intersecting
      const int n = 3 + (int)(r.uniform() * 30);
      std::vector<float> pts(2 * n);
      for (int i = 0; i < n; ++i) {
        pts[2 * i] = cx + frand(r, -s, s);
        pts[2 * i + 1] = cy + frand(r, -s, s);
      }
      p.polygon(pts.data(), n);
      break;
    }
    case 5: {  // the folk stitches: many tiny crossing strokes
      for (int j = 0; j < 9; ++j)
        for (int i = 0; i < 9; ++i) {
          const float x = cx + (i - 4) * s * 0.1f, y = cy + (j - 4) * s * 0.1f, q = s * 0.036f;
          const float a[4] = {x - q, y - q, x + q, y + q}, b[4] = {x + q, y - q, x - q, y + q};
          p.stroke(a, 2, s * 0.04f + 0.3f);
          p.stroke(b, 2, s * 0.04f + 0.3f);
        }
      break;
    }
    default:  // round rects on integer and half-integer edges
      p.roundRect(floorf(cx) + (kind & 8 ? 0.5f : 0), floorf(cy), floorf(s) + 1, floorf(s * 0.6f) + 1, frand(r, 0, s * 0.3f));
      p.roundRect(floorf(cx) + floorf(s) + 1, floorf(cy), floorf(s * 0.5f) + 1, floorf(s * 0.6f) + 1, 0);
      break;
  }
  p.close();
}

}  // namespace

void test_perf_cover_matches_the_17_rasterizer() {
  Raster ras;
  TEST_ASSERT_TRUE(ras.begin(480, 480));
  RefCover ref(480, 480);
  Path p;
  TEST_ASSERT_TRUE(p.reserve(4096));
  Mask m;
  Rng rng(0x5EED18);
  int shapes = 0, pixels = 0;
  for (int it = 0; it < 1500; ++it) {
    randomPath(rng, p, it);
    const FillRule rule = (it / 7) % 3 == 1 ? FillRule::EvenOdd : FillRule::NonZero;
    ras.cover(p, m, rule);
    const RefCover::Out o = ref.cover(p, rule);
    TEST_ASSERT_EQUAL_INT(o.w, m.w);
    TEST_ASSERT_EQUAL_INT(o.h, m.h);
    if (o.w <= 0 || o.h <= 0) continue;
    TEST_ASSERT_EQUAL_INT(o.x0, m.x0);
    TEST_ASSERT_EQUAL_INT(o.y0, m.y0);
    ++shapes;
    for (int row = 0; row < o.h; ++row) {
      const Mask::Row &a = o.rows[row], &b = m.rows[row];
      TEST_ASSERT_TRUE(a.lo == b.lo && a.hi == b.hi && a.f0 == b.f0 && a.f1 == b.f1);
      for (int x = a.lo; x < a.hi; ++x) {
        if (x >= a.f0 && x < a.f1) continue;  // the solid run is never stored
        TEST_ASSERT_EQUAL_UINT8(o.data[(size_t)row * o.w + (x - o.x0)], m.data[(size_t)row * m.w + (x - m.x0)]);
        ++pixels;
      }
    }
  }
  TEST_ASSERT_TRUE(shapes > 1000);
  TEST_ASSERT_TRUE(pixels > 100000);
}

void runPerfTests() { RUN_TEST(test_perf_cover_matches_the_17_rasterizer); }
