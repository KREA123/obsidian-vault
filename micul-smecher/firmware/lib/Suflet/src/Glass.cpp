#include "Glass.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "Raster.h"  // blend565

namespace suflet {

namespace {

// 4x4 Bayer matrix: the ordered dither that keeps the dark gradients of the
// aura from banding in RGB565
constexpr uint8_t kBayer[4][4] = {{0, 8, 2, 10}, {12, 4, 14, 6}, {3, 11, 1, 9}, {15, 7, 13, 5}};

struct Glow {
  float fx, fy, fr;  // centre and radius as fractions of the screen
  Rgb c;
  float a;
};

// The aura, in the same places as the web's #aura (os/index.html, os/DESIGN-GLASS.md §2).
constexpr Rgb kBase = Rgb(5, 5, 10);
constexpr Glow kGlows[3] = {
    {0.240f, 0.863f, 0.382f, Rgb(255, 138, 61), 0.50f},   // ember, lower left
    {0.798f, 0.219f, 0.425f, Rgb(39, 71, 184), 0.72f},    // night blue, upper right
    {0.777f, 0.820f, 0.298f, Rgb(154, 127, 224), 0.42f},  // lilac, lower right
};
constexpr Glow kToneGlow = {0.444f, 0.240f, 0.335f, Rgb(), 0.40f};  // the state, behind the eyes

inline uint16_t pack565(int r5, int g6, int b5) { return (uint16_t)((r5 << 11) | (g6 << 5) | b5); }
inline int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }

// separable box blur of radius r over a 3-channel uint16 image, `passes` times (a running sum;
// the edges repeat the border pixel). stride = distance between neighbours, n = samples on the line.
void blurLine(const uint16_t* in, uint16_t* out, int n, int stride, int r) {
  const uint32_t div = (uint32_t)(2 * r + 1), mul = (65536u + div / 2) / div;  // x / div ~= x * mul >> 16
  for (int c = 0; c < 3; ++c) {
    const uint16_t* p = in + c;
    uint16_t* o = out + c;
    uint32_t acc = (uint32_t)p[0] * (uint32_t)(r + 1);
    for (int k = 1; k <= r; ++k) acc += p[(k < n ? k : n - 1) * stride];
    for (int x = 0; x < n; ++x) {
      o[x * stride] = (uint16_t)(((uint64_t)acc * mul) >> 16);
      const int add = x + r + 1, sub = x - r;
      acc += p[(add < n ? add : n - 1) * stride];
      acc -= p[(sub > 0 ? sub : 0) * stride];
    }
  }
}

void boxBlur(uint16_t* img, uint16_t* tmp, int w, int h, int r, int passes) {
  for (int p = 0; p < passes; ++p) {
    for (int y = 0; y < h; ++y) blurLine(img + (size_t)y * w * 3, tmp + (size_t)y * w * 3, w, 3, r);
    for (int x = 0; x < w; ++x) blurLine(tmp + x * 3, img + x * 3, h, w * 3, r);
  }
}

}  // namespace

GlassLayer& glass() {
  static GlassLayer g;
  return g;
}

GlassLayer::~GlassLayer() {
  free(aura_);
  free(frost_);
  free(backA_);
  free(backF_);
  free(lo_);
}

Rgb GlassLayer::toneColor(GlassTone t) {
  switch (t) {
    case GlassTone::Ice:
      return Rgb(127, 178, 255);
    case GlassTone::Amber:
      return Rgb(255, 162, 58);
    case GlassTone::Mint:
      return Rgb(127, 227, 192);
    default:
      return Rgb(255, 179, 71);
  }
}

bool GlassLayer::begin(int w, int h) {
  if (aura_ && w == w_ && h == h_) return true;
  free(aura_);
  free(frost_);
  free(backA_);
  free(backF_);
  free(lo_);
  aura_ = frost_ = backA_ = backF_ = nullptr;
  lo_ = nullptr;
  building_ = false;
  w_ = w;
  h_ = h;
  bw_ = w + 2 * kMargin;
  bh_ = h + 2 * kMargin;
  lw_ = (bw_ + kDiv - 1) / kDiv + 2;
  lh_ = (bh_ + kDiv - 1) / kDiv + 2;
  aura_ = (uint16_t*)malloc((size_t)bw_ * bh_ * 2);
  frost_ = (uint16_t*)malloc((size_t)bw_ * bh_ * 2);
  lo_ = (uint8_t*)malloc((size_t)lw_ * lh_ * 3 * 2 * 3 + (size_t)lw_ * 3 * 4 * 2 + 4);  // 3 planes + 2 rows
  if (!aura_ || !frost_ || !lo_) {
    free(aura_);
    free(frost_);
    free(lo_);
    aura_ = frost_ = nullptr;
    lo_ = nullptr;
    return false;
  }
  backA_ = (uint16_t*)malloc((size_t)bw_ * bh_ * 2);  // optional: lets tone changes build in the background
  backF_ = (uint16_t*)malloc((size_t)bw_ * bh_ * 2);
  if (!backA_ || !backF_) {
    free(backA_);
    free(backF_);
    backA_ = backF_ = nullptr;
  }
  dirty_ = true;
  rebuild();
  return true;
}

bool GlassLayer::setOn(bool on) {
  if (on == on_) return false;
  on_ = on;
  return true;
}

bool GlassLayer::setTone(GlassTone t) {
  if (t == tone_) return false;
  tone_ = t;
  dirty_ = true;
  return true;
}

bool GlassLayer::setOffset(int dx, int dy) {
  dx = clampi(dx, -kMargin, kMargin);
  dy = clampi(dy, -kMargin, kMargin);
  if (dx == dx_ && dy == dy_) return false;
  dx_ = dx;
  dy_ = dy;
  return on_;
}

bool GlassLayer::setLevel(float a) {
  const int l = clampi((int)lroundf(a * 16), 0, 16);
  if (l == level16_) return false;
  level16_ = l;
  return on_;
}

bool GlassLayer::step(int rows) {
  if (!aura_) return false;
  if (!backA_) return rebuild();
  if (dirty_) {  // (re)start: the low-res field in 3 frames, then the full-size rows
    dirty_ = false;
    building_ = true;
    buildPhase_ = 0;
    buildRow_ = 0;
  }
  if (!building_) return false;
  if (buildPhase_ < 3) {
    buildLow(buildPhase_++);
    return false;
  }
  const int y1 = buildRow_ + rows < bh_ ? buildRow_ + rows : bh_;
  upscale(buildRow_, y1, backA_, backF_);
  buildRow_ = y1;
  if (buildRow_ < bh_) return false;
  uint16_t* t = aura_;  // swap the new aura in
  aura_ = backA_;
  backA_ = t;
  t = frost_;
  frost_ = backF_;
  backF_ = t;
  building_ = false;
  ++rebuilds;
  return true;
}

bool GlassLayer::rebuild() {
  if (!dirty_ || !aura_) return false;
  buildLow(-1);
  upscale(0, bh_, aura_, frost_);
  dirty_ = false;
  building_ = false;
  ++rebuilds;
  return true;
}

// ------------------------------------------------------------ the aura ---

void GlassLayer::buildLow(int phase) {
  const size_t plane = (size_t)lw_ * lh_ * 3;
  uint16_t* A = (uint16_t*)lo_;  // aura, 8.8 fixed point per channel
  uint16_t* F = A + plane;       // frosted
  uint16_t* T = F + plane;       // blur scratch
  Glow glows[4] = {kGlows[0], kGlows[1], kGlows[2], kToneGlow};
  glows[3].c = toneColor(tone_);
  const float W = (float)w_, H = (float)h_, S = W < H ? W : H;
  if (phase < 0 || phase == 0) {
    for (int j = 0; j < lh_; ++j) {
      for (int i = 0; i < lw_; ++i) {
        // the centre of this low-res pixel, in screen pixels
        const float x = (i - 1) * kDiv + kDiv * 0.5f - 0.5f - kMargin,
                    y = (j - 1) * kDiv + kDiv * 0.5f - 0.5f - kMargin;
        float r = kBase.r, g = kBase.g, b = kBase.b;
        for (const Glow& gl : glows) {
          const float dx = x - gl.fx * W, dy = y - gl.fy * H, R = gl.fr * S;
          const float q = 1.0f - (dx * dx + dy * dy) / (R * R);
          if (q <= 0) continue;
          const float a = gl.a * q * q;
          r += (gl.c.r - r) * a;
          g += (gl.c.g - g) * a;
          b += (gl.c.b - b) * a;
        }
        uint16_t* p = A + ((size_t)j * lw_ + i) * 3;
        p[0] = (uint16_t)(r * 256);
        p[1] = (uint16_t)(g * 256);
        p[2] = (uint16_t)(b * 256);
      }
    }
  }
  if (phase < 0 || phase == 1) boxBlur(A, T, lw_, lh_, 2, 3);  // "blurred once per aura change"
  if (phase < 0 || phase == 2) {
    memcpy(F, A, plane * 2);
    boxBlur(F, T, lw_, lh_, 3, 3);  // the frosted copy: blurred further, a little greyer
  }
  if (phase >= 0 && phase != 2) return;
  for (size_t k = 0; k < plane; k += 3) {
    const uint32_t l = (F[k] * 77u + F[k + 1] * 150u + F[k + 2] * 29u) >> 8;
    for (int c = 0; c < 3; ++c) F[k + c] = (uint16_t)((F[k + c] * 217u + l * 39u) >> 8);
  }
}

void GlassLayer::upscale(int y0, int y1, uint16_t* oaBuf, uint16_t* ofBuf) const {
  const size_t plane = (size_t)lw_ * lh_ * 3;
  const uint16_t* A = (const uint16_t*)lo_;
  const uint16_t* F = A + plane;
  // bilinear upscale with an ordered dither into the two 565 buffers. With kDiv = 4 every output
  // pixel sits at 1/8, 3/8, 5/8 or 7/8 between two low-res samples: 3-bit weights, 32-bit math.
  static_assert(kDiv == 4, "the weights below assume 1/4 resolution");
  uint32_t* ra = (uint32_t*)(lo_ + ((plane * 2 * 3 + 3) & ~(size_t)3));  // the two interpolated low-res rows
  uint32_t* rf = ra + lw_ * 3;
  for (int Y = y0; Y < y1; ++Y) {
    const int v = 2 * Y + 5;  // low-res y in eighths (+1 pad row)
    const int j0 = clampi(v >> 3, 0, lh_ - 2);
    const uint32_t wy = (uint32_t)(v - (j0 << 3)) > 8 ? 8u : (uint32_t)(v - (j0 << 3));
    const uint16_t* a0 = A + (size_t)j0 * lw_ * 3;
    const uint16_t* a1 = a0 + lw_ * 3;
    const uint16_t* f0 = F + (size_t)j0 * lw_ * 3;
    const uint16_t* f1 = f0 + lw_ * 3;
    for (int k = 0; k < lw_ * 3; ++k) {
      ra[k] = a0[k] * (8 - wy) + a1[k] * wy;  // 8.8 x 8
      rf[k] = f0[k] * (8 - wy) + f1[k] * wy;
    }
    uint16_t* oa = oaBuf + (size_t)Y * bw_;
    uint16_t* of = ofBuf + (size_t)Y * bw_;
    const uint8_t* bay = kBayer[Y & 3];
    // output pixel X sits at (2X + 5) / 8 in low-res units: pixel 4i - 2 + k is at weight 1, 3, 5, 7 / 8
    // between samples i - 1 and i, so each run of 4 is a start value + 3 equal steps (no multiplies)
    for (int i = 1; i < lw_; ++i) {
      const uint32_t* p0 = ra + (i - 1) * 3;
      const uint32_t* q0 = rf + (i - 1) * 3;
      int32_t c[6], st[6];
      for (int ch = 0; ch < 3; ++ch) {  // value in 8.8 x 64 at weight 1/8, step = 2/8 of the difference
        const int32_t a0v = (int32_t)p0[ch] * 8, a1v = (int32_t)p0[ch + 3] * 8;
        const int32_t f0v = (int32_t)q0[ch] * 8, f1v = (int32_t)q0[ch + 3] * 8;
        c[ch] = a0v + (a1v - a0v) / 8;
        st[ch] = (a1v - a0v) / 4;
        c[ch + 3] = f0v + (f1v - f0v) / 8;
        st[ch + 3] = (f1v - f0v) / 4;
      }
      for (int k = 0; k < 4; ++k) {
        const int X = 4 * i - 6 + k;
        if (X >= 0 && X < bw_) {
          const int32_t B = bay[X & 3], t5 = (B * 128 + 64) << 6, t6 = (B * 64 + 32) << 6;
          int r5 = (c[0] + t5) >> 17, g6 = (c[1] + t6) >> 16, b5 = (c[2] + t5) >> 17;
          oa[X] = pack565(r5 > 31 ? 31 : r5, g6 > 63 ? 63 : g6, b5 > 31 ? 31 : b5);
          r5 = (c[3] + t5) >> 17;
          g6 = (c[4] + t6) >> 16;
          b5 = (c[5] + t5) >> 17;
          of[X] = pack565(r5 > 31 ? 31 : r5, g6 > 63 ? 63 : g6, b5 > 31 ? 31 : b5);
        }
        for (int ch = 0; ch < 6; ++ch) c[ch] += st[ch];
      }
    }
  }
}

uint16_t GlassLayer::auraAt(int x, int y) const {
  if (!aura_ || (unsigned)x >= (unsigned)w_ || (unsigned)y >= (unsigned)h_) return 0;
  return aura_[(size_t)(y + kMargin + dy_) * bw_ + x + kMargin + dx_];
}

uint16_t GlassLayer::frostAt(int x, int y) const {
  if (!frost_ || (unsigned)x >= (unsigned)w_ || (unsigned)y >= (unsigned)h_) return 0;
  return frost_[(size_t)(y + kMargin + dy_) * bw_ + x + kMargin + dx_];
}

// ------------------------------------------------------------ painting ---

void GlassLayer::background(Canvas& cv, Rect r) const {
  r = cv.clip(r);
  if (r.empty()) return;
  cv.markDirty(r);
  uint16_t* buf = cv.data();
  const int cw = cv.width();
  const bool show = on_ && aura_ && cv.width() == w_ && cv.height() == h_ && level16_ > 0;
  for (int y = r.y0; y < r.y1; ++y) {
    uint16_t* row = buf + (size_t)y * cw;
    if (!show) {
      memset(row + r.x0, 0, (size_t)r.w() * 2);
      continue;
    }
    const uint16_t* src = aura_ + (size_t)(y + kMargin + dy_) * bw_ + kMargin + dx_;
    if (level16_ >= 16) {
      memcpy(row + r.x0, src + r.x0, (size_t)r.w() * 2);
    } else {
      const uint32_t a = (uint32_t)level16_ * 2;
      for (int x = r.x0; x < r.x1; ++x) row[x] = blend565(0, src[x], a);
    }
  }
}

void GlassLayer::backgroundRing(Canvas& cv, float cx, float cy, float ri, float ro) const {
  Rect box{(int)floorf(cx - ro - 1), (int)floorf(cy - ro - 1), (int)ceilf(cx + ro + 1), (int)ceilf(cy + ro + 1)};
  box = cv.clip(box);
  for (int y = box.y0; y < box.y1; ++y) {
    const float dy = y + 0.5f - cy;
    const float o2 = (ro + 1) * (ro + 1) - dy * dy;
    if (o2 <= 0) continue;
    const float xo = sqrtf(o2);
    const float i2 = (ri - 1) * (ri - 1) - dy * dy;
    const float xi = i2 > 0 ? sqrtf(i2) : -1;
    const int a0 = (int)floorf(cx - xo), a1 = (int)ceilf(cx + xo);
    if (xi < 0) {
      background(cv, Rect{a0, y, a1, y + 1});
    } else {
      background(cv, Rect{a0, y, (int)ceilf(cx - xi), y + 1});
      background(cv, Rect{(int)floorf(cx + xi), y, a1, y + 1});
    }
  }
}

// lookup tables: frosted channel -> glass channel, for 8 steps of the fill gradient (cached per style)
const GlassLayer::Lut& GlassLayer::lutFor(const GlassStyle& s) const {
  const float key[6] = {s.fillTop, s.fillBottom, (float)s.tint.r, (float)s.tint.g, (float)s.tint.b, s.tintA};
  for (const Lut& l : lut_)
    if (memcmp(l.key, key, sizeof key) == 0) return l;
  Lut& L = lut_[lutNext_];
  lutNext_ = (lutNext_ + 1) % 4;
  memcpy(L.key, key, sizeof key);
  for (int k = 0; k < 8; ++k) {
    const float f = s.fillTop + (s.fillBottom - s.fillTop) * k / 7.0f;
    for (int v = 0; v < 64; ++v) {
      const float v8g = (float)((v << 2) | (v >> 4));
      float og = v8g + (255 - v8g) * f;
      og += (s.tint.g - og) * s.tintA;
      L.g[k][v] = (uint8_t)clampi((int)(og * (63.0f / 255.0f) + 0.5f), 0, 63);
      if (v < 32) {
        const float v8 = (float)((v << 3) | (v >> 2));
        float orr = v8 + (255 - v8) * f, ob = orr;
        orr += (s.tint.r - orr) * s.tintA;
        ob += (s.tint.b - ob) * s.tintA;
        L.r[k][v] = (uint8_t)clampi((int)(orr * (31.0f / 255.0f) + 0.5f), 0, 31);
        L.b[k][v] = (uint8_t)clampi((int)(ob * (31.0f / 255.0f) + 0.5f), 0, 31);
      }
    }
  }
  return L;
}

template <class Sdf, class Inner>
void GlassLayer::shade(Canvas& cv, float bx0, float by0, float bx1, float by1, Sdf sdf, Inner inner,
                       const GlassStyle& s) const {
  if (s.alpha <= 0.004f) return;
  const float kShadowR = s.shadow > 0.01f ? s.shadowR : 0.0f, kShadowDy = s.shadowDy;
  constexpr float kEdgeW = 1.5f;
  const float glowR = s.glowA > 0 ? 15.0f : 0.0f;
  const float pad = (glowR > kShadowR + kShadowDy ? glowR : kShadowR + kShadowDy) + 1;
  Rect r{(int)floorf(bx0 - pad), (int)floorf(by0 - pad), (int)ceilf(bx1 + pad), (int)ceilf(by1 + pad)};
  const int fullX0 = r.x0 > 0 ? r.x0 : 0;  // the left edge with no clip but the canvas
  r = cv.clip(r);
  if (r.empty()) return;
  cv.markDirty(r);
  const Lut& L = lutFor(s);
  const auto& lr = L.r;
  const auto& lg = L.g;
  const auto& lb = L.b;
  const bool see = on_ && frost_ && cv.width() == w_ && cv.height() == h_ && level16_ > 0;
  const uint32_t lvl = (uint32_t)level16_ * 2;
  const uint16_t glow565 = s.glow.to565();
  const float gdx = 0.42f, gdy = 0.91f;  // the 155 deg fill gradient
  const float glen = (bx1 - bx0) * gdx + (by1 - by0) * gdy;
  const float ginv = glen > 1 ? 7.99f / glen : 0;
  const float edgeLo = 0.07f;
  uint16_t* buf = cv.data();
  const int cw = cv.width();
  uint32_t shaded = 0;
  for (int y = r.y0; y < r.y1; ++y) {
    const float py = y + 0.5f;
    uint16_t* row = buf + (size_t)y * cw;
    const uint16_t* fr = see ? frost_ + (size_t)(y + kMargin + dy_) * bw_ + kMargin + dx_ : nullptr;
    // the solid middle of the row: straight through the LUTs (most of a panel's pixels)
    float fxa = 0, fxb = -1;
    int ia = 0, ib = 0, iaFull = 0;
    if (inner(py, fxa, fxb) && s.alpha >= 0.999f) {
      ia = (int)ceilf(fxa - 0.5f);
      ib = (int)floorf(fxb - 0.5f) + 1;
      // where an unclipped paint starts the run: the gradient is stepped from there, so a paint under a
      // smaller clip (one rectangle of a frame's repair) gives exactly the same pixels as a whole one
      iaFull = ia < fullX0 ? fullX0 : ia;
      if (ia < r.x0) ia = r.x0;
      if (ib > r.x1) ib = r.x1;
    }
    const float growBase = (py - by0) * gdy - bx0 * gdx;
    for (int x = r.x0; x < r.x1; ++x) {
      if (x == ia && ib > ia) {
        const uint8_t* bay = kBayer[y & 3];
        // the gradient step in 16.16 fixed point, stepped along the row (+ the dither)
        const int32_t inc = (int32_t)(gdx * ginv * 65536.0f);
        int32_t acc = (int32_t)((((iaFull + 0.5f) * gdx + growBase) * ginv) * 65536.0f) + (x - iaFull) * inc;
        for (; x < ib; ++x, acc += inc) {
          uint16_t f = fr ? fr[x] : 0;
          if (fr && lvl < 32) f = blend565(0, f, lvl);
          int step = (acc + (bay[x & 3] << 12)) >> 16;
          step = step < 0 ? 0 : (step > 7 ? 7 : step);
          row[x] = pack565(lr[step][f >> 11], lg[step][(f >> 5) & 63], lb[step][f & 31]);
        }
        shaded += (uint32_t)(ib - ia);
        if (x >= r.x1) break;
      }
      const float px = x + 0.5f;
      const float d = sdf(px, py);
      if (d >= 0.5f) {  // outside: the shadow (offset down) and the accent glow
        if (d >= pad) continue;
        uint16_t bg = row[x];
        const float ds = kShadowR > 0 ? sdf(px, py - kShadowDy) : 1e9f;
        if (ds < kShadowR) {
          const float q = 1.0f - (ds > 0 ? ds : 0) / kShadowR;
          const uint32_t k = (uint32_t)(s.shadow * q * q * s.alpha * 32.0f);
          if (k) bg = blend565(bg, 0, k);
        }
        if (glowR > 0 && d < glowR) {
          const float q = 1.0f - d / glowR;
          const uint32_t k = (uint32_t)(s.glowA * q * q * s.alpha * 32.0f);
          if (k) bg = blend565(bg, glow565, k);
        }
        row[x] = bg;
        continue;
      }
      ++shaded;
      // inside: the frosted aura through the fill
      uint16_t f = fr ? fr[x] : 0;
      if (fr && lvl < 32) f = blend565(0, f, lvl);
      int step = (int)(((px - bx0) * gdx + (py - by0) * gdy) * ginv +
                       kBayer[y & 3][x & 3] * (1.0f / 16));  // dithered: no bands
      step = step < 0 ? 0 : (step > 7 ? 7 : step);
      uint16_t c = pack565(lr[step][f >> 11], lg[step][(f >> 5) & 63], lb[step][f & 31]);
      // the 1.5 px rim, lit from the top-left
      if (d > -kEdgeW) {
        const float nx = sdf(px + 0.5f, py) - sdf(px - 0.5f, py), ny = sdf(px, py + 0.5f) - sdf(px, py - 0.5f);
        const float nl = sqrtf(nx * nx + ny * ny);
        const float light = nl > 1e-4f ? -(nx + ny) * 0.70710678f / nl : 0;
        const float e = edgeLo + (s.edge - edgeLo) * (light > 0 ? light : 0);
        const float w = 1.0f - (d < 0 ? -d : 0) / kEdgeW;
        const uint32_t k = (uint32_t)(e * w * 32.0f);
        if (k) c = blend565(c, 0xFFFF, k);
      }
      const float cov = (d > -0.5f ? 0.5f - d : 1.0f) * s.alpha;
      row[x] = cov >= 0.999f ? c : blend565(row[x], c, (uint32_t)(cov * 32.0f + 0.5f));
    }
  }
  const_cast<GlassLayer*>(this)->panelPixels += shaded;
}

void GlassLayer::panel(Canvas& cv, float x0, float y0, float x1, float y1, float r, const GlassStyle& s) const {
  if (x1 <= x0 || y1 <= y0) return;
  const float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f, hw = (x1 - x0) * 0.5f, hh = (y1 - y0) * 0.5f;
  const float rr = r > hw ? hw : (r > hh ? hh : r);
  auto sdf = [=](float px, float py) {  // the rounded box, inlined (this runs per pixel)
    const float qx = fabsf(px - cx) - hw + rr, qy = fabsf(py - cy) - hh + rr;
    if (qx <= 0 || qy <= 0) return (qx > qy ? qx : qy) - rr;  // beside a straight side: no root
    return sqrtf(qx * qx + qy * qy) - rr;
  };
  constexpr float kIn = 1.6f;  // deeper than the edge band and the anti-aliasing
  auto inner = [=](float py, float& xa, float& xb) {
    const float dy = fabsf(py - cy);
    if (dy > hh - kIn) return false;
    float half = hw - kIn;
    const float q = dy - (hh - rr);
    if (q > 0) {
      const float ri = rr - kIn;
      if (ri <= 0 || q >= ri) return false;
      half = (hw - rr) + sqrtf(ri * ri - q * q);
    }
    xa = cx - half;
    xb = cx + half;
    return half > 0;
  };
  shade(cv, x0, y0, x1, y1, sdf, inner, s);
}

void GlassLayer::capsuleArc(Canvas& cv, float cx, float cy, float rm, float hw, float a0, float a1,
                            const GlassStyle& s) const {
  if (a1 <= a0) return;
  const float e0x = cosf(a0), e0y = sinf(a0), e1x = cosf(a1), e1y = sinf(a1);
  const float p0x = cx + e0x * rm, p0y = cy + e0y * rm, p1x = cx + e1x * rm, p1y = cy + e1y * rm;
  float bx0 = 1e9f, by0 = 1e9f, bx1 = -1e9f, by1 = -1e9f;
  for (int i = 0; i <= 16; ++i) {
    const float a = a0 + (a1 - a0) * i / 16.0f, x = cx + cosf(a) * rm, y = cy + sinf(a) * rm;
    bx0 = fminf(bx0, x);
    by0 = fminf(by0, y);
    bx1 = fmaxf(bx1, x);
    by1 = fmaxf(by1, y);
  }
  auto sdf = [=](float px, float py) {
    const float vx = px - cx, vy = py - cy;
    if (e0x * vy - e0y * vx >= 0 && vx * e1y - vy * e1x >= 0) return fabsf(sqrtf(vx * vx + vy * vy) - rm) - hw;
    const float d0 = sqrtf((px - p0x) * (px - p0x) + (py - p0y) * (py - p0y));
    const float d1 = sqrtf((px - p1x) * (px - p1x) + (py - p1y) * (py - p1y));
    return (d0 < d1 ? d0 : d1) - hw;
  };
  shade(cv, bx0 - hw, by0 - hw, bx1 + hw, by1 + hw, sdf, [](float, float&, float&) { return false; }, s);
}

void GlassLayer::band(Canvas& cv, float cx, float cy, float rm, float hw, const GlassStyle& s) const {
  // the annulus in four quadrant strips, so the empty middle is never visited
  const float ro = rm + hw, ri = rm - hw, inner = ri * 0.70710678f - 14;  // the square inside the hole
  auto sdf = [=](float px, float py) {
    const float dx = px - cx, dy = py - cy;
    return fabsf(sqrtf(dx * dx + dy * dy) - rm) - hw;
  };
  const Rect keep = cv.clipRect();
  const Rect strips[4] = {
      {(int)floorf(cx - ro - 30), (int)floorf(cy - ro - 30), (int)ceilf(cx + ro + 30), (int)floorf(cy - inner)},
      {(int)floorf(cx - ro - 30), (int)ceilf(cy + inner), (int)ceilf(cx + ro + 30), (int)ceilf(cy + ro + 30)},
      {(int)floorf(cx - ro - 30), (int)floorf(cy - inner), (int)floorf(cx - inner), (int)ceilf(cy + inner)},
      {(int)ceilf(cx + inner), (int)floorf(cy - inner), (int)ceilf(cx + ro + 30), (int)ceilf(cy + inner)},
  };
  for (const Rect& st : strips) {
    Rect c = st;
    if (c.x0 < keep.x0) c.x0 = keep.x0;
    if (c.y0 < keep.y0) c.y0 = keep.y0;
    if (c.x1 > keep.x1) c.x1 = keep.x1;
    if (c.y1 > keep.y1) c.y1 = keep.y1;
    if (c.empty()) continue;
    cv.setClip(c);
    // the gradient spans the whole ring, so the fill matches across the strips
    shade(cv, cx - ro, cy - ro, cx + ro, cy + ro, sdf, [](float, float&, float&) { return false; }, s);
  }
  cv.setClip(keep);
}

}  // namespace suflet
