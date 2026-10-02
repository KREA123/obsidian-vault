#include "EyeRender.h"

#include <math.h>

namespace suflet {
namespace eyes {

static constexpr float kPi = 3.14159265f;
static constexpr float kTau = 6.28318531f;

static inline float clampf_(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
static inline float smooth(float t) {
  t = clampf_(t, 0, 1);
  return t * t * (3 - 2 * t);
}
static inline float outBackf(float t, float s) {
  const float u = t - 1;
  return 1 + (s + 1) * u * u * u + s * u * u;
}
static inline float fmodPos(double a, double m) {
  double r = fmod(a, m);
  if (r < 0) r += m;
  return (float)r;
}
static inline Rgb hexc(uint32_t v) { return Rgb::hex(v); }
static inline Rgb mixc(Rgb a, Rgb b, float t) {
  t = clampf_(t, 0, 1);
  return Rgb((uint8_t)lroundf(a.r + (b.r - a.r) * t), (uint8_t)lroundf(a.g + (b.g - a.g) * t),
             (uint8_t)lroundf(a.b + (b.b - a.b) * t));
}

Rgb hsl(float h, float s, float l) {
  h = fmodPos(h, 360.0) / 360.0f;
  s /= 100.0f;
  l /= 100.0f;
  auto hue = [](float p, float q, float t) {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1.0f / 6) return p + (q - p) * 6 * t;
    if (t < 0.5f) return q;
    if (t < 2.0f / 3) return p + (q - p) * (2.0f / 3 - t) * 6;
    return p;
  };
  const float q = l < 0.5f ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  return Rgb((uint8_t)lroundf(hue(p, q, h + 1.0f / 3) * 255), (uint8_t)lroundf(hue(p, q, h) * 255),
             (uint8_t)lroundf(hue(p, q, h - 1.0f / 3) * 255));
}

void superPath(Path& p, float x, float y, float rx, float ry, float rot, float n) {
  const float c = cosf(rot), s = sinf(rot), e = 2.0f / n;
  p.moveTo(x + rx * c, y + rx * s);
  for (int i = 1; i < 40; ++i) {
    const float a = (float)i / 40 * kTau, ca = cosf(a), sa = sinf(a);
    const float ux = copysignf(powf(fabsf(ca), e), ca) * rx, uy = copysignf(powf(fabsf(sa), e), sa) * ry;
    p.lineTo(x + ux * c - uy * s, y + ux * s + uy * c);
  }
  p.close();
}

void starPath(Path& p, float x, float y, float r, int n, float inner, float rot) {
  for (int i = 0; i < n * 2; ++i) {
    const float a = rot - kPi / 2 + (float)i / (n * 2) * kTau, rr = (i % 2) ? r * inner : r;
    if (i) p.lineTo(x + cosf(a) * rr, y + sinf(a) * rr);
    else p.moveTo(x + cosf(a) * rr, y + sinf(a) * rr);
  }
  p.close();
}

void heartPath(Path& p, float x, float y, float s, float rot) {
  const float c = cosf(rot), sn = sinf(rot);
  for (int i = 0; i < 72; ++i) {  // eyes.js uses 73 points, the last one closes the loop
    const float a = (float)i / 72 * kTau, si = sinf(a);
    const float hx = (16 * si * si * si) / 16.5f * s;
    const float hy = ((-(13 * cosf(a) - 5 * cosf(2 * a) - 2 * cosf(3 * a) - cosf(4 * a)) + 2.5f) / 15) * s;
    const float px = x + hx * c - hy * sn, py = y + hx * sn + hy * c;
    if (i) p.lineTo(px, py);
    else p.moveTo(px, py);
  }
  p.close();
}

// quadratic Bézier, flattened (start point already in the contour)
static void quadTo(Path& p, float x0, float y0, float cx, float cy, float x1, float y1, int n = 8) {
  for (int i = 1; i <= n; ++i) {
    const float t = (float)i / n, u = 1 - t;
    p.lineTo(u * u * x0 + 2 * u * t * cx + t * t * x1, u * u * y0 + 2 * u * t * cy + t * t * y1);
  }
}

// Sutherland–Hodgman: clip polygon `in` (n points) by the convex polygon `cl`
static int clipConvex(const float* in, int n, const float* cl, int m, float* out, int cap) {
  static float tmp[2 * 128];
  float* src = tmp;
  int ns = n < 128 ? n : 128;
  for (int i = 0; i < 2 * ns; ++i) src[i] = in[i];
  // orientation of the clip polygon
  float area = 0;
  for (int i = 0, j = m - 1; i < m; j = i++) area += cl[2 * j] * cl[2 * i + 1] - cl[2 * i] * cl[2 * j + 1];
  const float sgn = area >= 0 ? 1.0f : -1.0f;
  int no = 0;
  for (int e = 0; e < m; ++e) {
    const float ax = cl[2 * e], ay = cl[2 * e + 1];
    const float bx = cl[2 * ((e + 1) % m)], by = cl[2 * ((e + 1) % m) + 1];
    auto inside = [&](float x, float y) { return sgn * ((bx - ax) * (y - ay) - (by - ay) * (x - ax)) >= 0; };
    no = 0;
    for (int i = 0; i < ns; ++i) {
      const float px = src[2 * i], py = src[2 * i + 1];
      const float qx = src[2 * ((i + 1) % ns)], qy = src[2 * ((i + 1) % ns) + 1];
      const bool pin = inside(px, py), qin = inside(qx, qy);
      if (pin && no < cap) {
        out[2 * no] = px;
        out[2 * no + 1] = py;
        ++no;
      }
      if (pin != qin && no < cap) {
        const float d1 = (bx - ax) * (py - ay) - (by - ay) * (px - ax);
        const float d2 = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax);
        const float t = d1 / (d1 - d2);
        out[2 * no] = px + (qx - px) * t;
        out[2 * no + 1] = py + (qy - py) * t;
        ++no;
      }
    }
    if (!no) return 0;
    ns = no < 128 ? no : 128;
    for (int i = 0; i < 2 * ns; ++i) src[i] = out[i];
  }
  return no;
}

bool EyeRenderer::begin(int w, int h) {
  return ras_.begin(w, h) && p_.reserve(4096) && body_.reserve(64 * 64);
}

EyeGeom EyeRenderer::frame(const EyeRig& rig, const Design& d, float side, float cx, float cy, float D, float sx,
                           float sy) const {
  const float ex0 = rig.eyeGaze(0), ey0 = rig.eyeGaze(1);
  const float b = rig.closed();
  const float breath = (float)sin(rig.time() * kTau / 3.6 + side * 0.4);
  const float par = 1 - 0.07f * ex0 * side;
  const float sq = clampf_(side < 0 ? rig.ch(Ch_squeezeL) : rig.ch(Ch_squeezeR), 0, 1.2f);
  const float k = fmaxf(0, rig.ch(Ch_scale)) * par * (side < 0 ? rig.ch(Ch_sizeL) : rig.ch(Ch_sizeR));
  EyeGeom g;
  g.rx = d.rx * D * k * sx * (1 + 0.06f * fmaxf(0, b)) * (1 + 0.006f * breath) * (1 - 0.5f * sq);
  g.ry = d.ry * D * k * sy * (1 - 0.12f * b) * (1 + 0.012f * breath) * fmaxf(0, 1 - sq);
  g.x = cx + (side * d.spacing + ex0 * 0.028f + rig.ch(Ch_shift)) * D;
  g.y = cy + (d.y + ey0 * 0.022f + rig.ch(Ch_bob) + rig.ch(Ch_lift) + 0.016f * fmaxf(0, b) + 0.002f * breath) * D;
  g.b = b;
  g.side = side;
  g.sq = sq;
  g.k = k;
  return g;
}

void EyeRenderer::glint(Canvas& cv, const Design& d, float x, float y, float rx, float ry, float rot,
                        const Xform& X, const Mask* clip, float alpha) {
  p_.clear();
  p_.xf = X;
  superPath(p_, x, y, rx, ry, rot, 2.6f);
  ras_.fill(cv, p_, hexc(d.glintColor), alpha, clip);
}

EyeRenderer::Info EyeRenderer::pupilShape(Canvas& cv, const Design& /*d*/, Pupil type, float px, float py, float prx,
                                          float pry, Rgb color, float t, float side, const EyeRig& rig,
                                          const Xform& X, const Mask* clip, float alpha) {
  Info info;
  p_.clear();
  p_.xf = X;
  FillRule rule = FillRule::NonZero;
  switch (type) {
    case Pupil::Slit:
      p_.ellipse(px, py, prx * clampf_(0.5f * rig.slitW, 0.3f, 1.05f), pry * 1.08f);
      info.gx = 0.4f;
      break;
    case Pupil::Plus: {
      const float w = fminf(prx, pry) * 0.62f;
      p_.roundRect(px - prx, py - w / 2, prx * 2, w, w / 2);
      p_.roundRect(px - w / 2, py - pry, w, pry * 2, w / 2);
      info.gx = 0.55f;
      info.gy = 0.2f;
      info.gs = 0.6f;
      break;
    }
    case Pupil::Star:
      starPath(p_, px, py, fmaxf(prx, pry) * 1.12f, 5, 0.5f, sinf(t * 1.2f) * 0.15f);
      info.gs = 0.7f;
      break;
    case Pupil::Heart:
      heartPath(p_, px, py + pry * 0.05f, fmaxf(prx, pry) * 1.15f, side * 0.08f);
      info.gx = -0.4f;
      info.gy = -0.3f;
      info.gs = 0.7f;
      break;
    case Pupil::Ring:
      p_.ellipse(px, py, prx, pry);
      p_.ellipse(px, py, prx * 0.5f, pry * 0.5f);
      rule = FillRule::EvenOdd;
      info.gx = 0.45f;
      info.gs = 0.6f;
      break;
    case Pupil::Double:
      p_.ellipse(px - prx * 0.1f, py - pry * 0.18f, prx * 0.78f, pry * 0.68f);
      p_.ellipse(px + prx * 0.55f, py + pry * 0.62f, prx * 0.32f, pry * 0.27f);
      info.gs = 0.75f;
      info.gy = -0.6f;
      break;
    case Pupil::Pebble:
      superPath(p_, px, py, prx * 1.04f, pry * 0.9f, side * -0.18f, 2.6f);
      break;
    case Pupil::Crescent:
      p_.ellipse(px, py, prx, pry);
      p_.ellipse(px + prx * 0.55f * -side, py - pry * 0.18f, prx * 0.82f, pry * 0.84f);
      rule = FillRule::EvenOdd;
      info.none = true;
      break;
    case Pupil::Diamond: {
      const float pts[8] = {px, py - pry * 1.12f, px + prx * 0.95f, py, px, py + pry * 1.12f, px - prx * 0.95f, py};
      p_.polygon(pts, 4);
      info.gs = 0.65f;
      break;
    }
    case Pupil::Spiral: {
      const float rot = t * 5 * side, R = fmaxf(prx, pry) * 1.15f, ky = pry / fmaxf(prx, pry);
      float pts[2 * 91];
      for (int i = 0; i <= 90; ++i) {
        const float q = i / 90.0f, a = rot + q * kTau * 2.3f, rr = q * R;
        pts[2 * i] = px + cosf(a) * rr;
        pts[2 * i + 1] = py + sinf(a) * rr * ky;
      }
      p_.stroke(pts, 91, fminf(prx, pry) * 0.34f);
      info.none = true;
      break;
    }
    case Pupil::Battery: {
      const float w = prx * 1.6f, h = pry * 1.3f, lw = fminf(w, h) * 0.16f;
      p_.strokeRoundRect(px - w / 2, py - h / 2 + lw * 0.6f, w, h - lw * 0.6f, lw, lw);
      p_.roundRect(px - w * 0.18f, py - h / 2 - lw * 0.7f, w * 0.36f, lw * 1.3f, lw * 0.4f);
      ras_.fill(cv, p_, color, alpha, clip);
      if (sinf(t * 6) > -0.2f) {
        p_.clear();
        p_.xf = X;
        p_.roundRect(px - w / 2 + lw * 1.1f, py + h / 2 - lw * 1.1f - h * 0.18f, w - lw * 2.2f, h * 0.18f, lw * 0.4f);
        ras_.fill(cv, p_, hexc(0xFF3B3B), alpha, clip);
      }
      info.none = true;
      return info;
    }
    case Pupil::Level: {
      const float w = prx * 1.5f, h = pry * 1.45f, lw = fminf(w, h) * 0.15f, lv = clampf_(rig.charge(), 0, 1);
      p_.strokeRoundRect(px - w / 2, py - h / 2, w, h, w * 0.32f, lw);
      ras_.fill(cv, p_, color, alpha, clip);
      // the liquid: a wavy top, clipped to the inner rounded box
      const float ix = px - w / 2 + lw, iy = py - h / 2 + lw, iw = w - lw * 2, ih = h - lw * 2;
      const float ir = fminf(w * 0.24f, fminf(iw, ih) * 0.5f);
      float box[2 * 4 * 5];
      int nb = 0;
      const float cxs[4] = {ix + iw - ir, ix + iw - ir, ix + ir, ix + ir};
      const float cys[4] = {iy + ir, iy + ih - ir, iy + ih - ir, iy + ir};
      for (int c = 0; c < 4; ++c)
        for (int i = 0; i < 5; ++i) {
          const float a = -kPi / 2 + c * kPi / 2 + (kPi / 2) * i / 4;
          box[2 * nb] = cxs[c] + cosf(a) * ir;
          box[2 * nb + 1] = cys[c] + sinf(a) * ir;
          ++nb;
        }
      const float top = py + h / 2 - lw - (h - lw * 2) * lv;
      float wave[2 * 15];
      int nw = 0;
      wave[2 * nw] = px - w;
      wave[2 * nw + 1] = py + h;
      ++nw;
      for (int i = 0; i <= 12; ++i) {
        wave[2 * nw] = px - w / 2 + (i / 12.0f) * w;
        wave[2 * nw + 1] = top + sinf(i * 0.9f + t * 6) * h * 0.025f;
        ++nw;
      }
      wave[2 * nw] = px + w;
      wave[2 * nw + 1] = py + h;
      ++nw;
      float out[2 * 128];
      const int no = clipConvex(wave, nw, box, nb, out, 128);
      if (no >= 3) {
        p_.clear();
        p_.xf = X;
        p_.polygon(out, no);
        ras_.fill(cv, p_, color, alpha, clip);
      }
      info.none = true;
      return info;
    }
    case Pupil::Round:
    default:
      p_.ellipse(px, py, prx, pry);
      break;
  }
  ras_.fill(cv, p_, color, alpha, clip, rule);
  return info;
}

static const char* const kMotif[9] = {"....1....", ".1..1..1.", "..1.2.1..", "...121...", "112121211",
                                      "...121...", "..1.2.1..", ".1..1..1.", "....1...."};

void EyeRenderer::drawEye(Canvas& cv, const EyeRig& rig, const Design& d, float side, float cx, float cy, float D,
                          float sx, float sy, const Xform& G, const RenderOpts& o) {
  const EyeGeom g = frame(rig, d, side, cx, cy, D, sx, sy);
  eyes_[side < 0 ? 0 : 1] = g;
  const float t = (float)fmod(rig.time(), 3600.0);  // phases: keep float precision over long uptimes
  const double td = rig.time();
  const bool L = side < 0;
  const float A = o.alpha;
  if (g.k <= 0.004f) return;
  if (g.ry > 0.3f) {
    // the silhouette (eyes.js silhouette(), 120 points)
    const float lean = -side * d.lean, cl = cosf(lean), sl = sinf(lean);
    const float lid0 = clampf_(L ? rig.ch(Ch_lidL) : rig.ch(Ch_lidR), 0, 0.98f);
    const float tilt = L ? rig.ch(Ch_tiltL) : rig.ch(Ch_tiltR);
    const float bb = clampf_(g.b, 0, 1);
    const float lid = lid0 + (1 - lid0) * bb;
    const float kT = tanf(tilt) * -side * (1 - bb);
    const float thick = 0.024f * D * fmaxf(0.35f, g.k);
    const float bow = 0.1f * g.ry * fminf(1, lid0 * 4) * (1 - bb);
    const float rx = g.rx, ry = g.ry;
    const float smile = clampf_(L ? rig.ch(Ch_smileL) : rig.ch(Ch_smileR), 0, 1);
    const float cutCy = ry * (2.2f - 1.78f * smile), cutA = rx * 1.42f, cutB = ry * 1.1f;
    const Xform X = G.translated(g.x, g.y);
    static float pts[2 * 120];
    const int N = 120;
    for (int i = 0; i < N; ++i) {
      const float a = (float)i / N * kTau, ca = cosf(a), sa = sinf(a);
      float ux, uy;
      switch (d.shape) {
        case Shape::Squircle: {
          const float e = 2.0f / d.n;
          ux = copysignf(powf(fabsf(ca), e), ca) * rx;
          uy = copysignf(powf(fabsf(sa), e), sa) * ry;
          break;
        }
        case Shape::Almond:
          ux = ca * rx;
          uy = sa * powf(fabsf(sa), d.q) * ry;
          uy -= d.flick * ry * fmaxf(0, -ca * side) * (ca * side < 0 ? 1 : 0) * fabsf(ca);
          break;
        case Shape::Drop: {
          const float tip = fmaxf(0, -sa);
          ux = ca * rx * (1 - 0.55f * powf(tip, 1.6f));
          uy = sa * ry * (sa < 0 ? 1.12f : 0.92f) + ry * 0.06f;
          break;
        }
        case Shape::Crescent: {
          ux = ca * rx;
          uy = sa * ry;
          const float dip = -ry + d.dip * ry * 2 * (1 - (ux / rx) * (ux / rx));
          if (uy < dip) uy = dip;
          break;
        }
        case Shape::Egg:
        default:
          ux = ca * rx * (1 - d.egg * fmaxf(0, -sa));
          uy = sa * ry;
          break;
      }
      const float x = ux * cl - uy * sl;
      float y = ux * sl + uy * cl;
      if (lid > 0.003f) {
        const float q = fminf(1, (x / rx) * (x / rx));
        const float ly = -ry + lid * (2 * ry - thick) + kT * x + bow * (1 - q);
        if (y < ly) y = ly;
      }
      if (smile > 0.003f) {
        const float q = 1 - (x / cutA) * (x / cutA);
        if (q > 0) {
          const float cy2 = cutCy - cutB * sqrtf(q);
          if (y > cy2) y = cy2;
        }
      }
      pts[2 * i] = x;
      pts[2 * i + 1] = y;
    }
    p_.clear();
    p_.xf = X;
    p_.polygon(pts, N);
    ras_.cover(p_, body_);
    const float gx = L ? rig.pupilL(0) : rig.pupilR(0), gy = L ? rig.pupilL(1) : rig.pupilR(1);
    // the white: solid, rainbow, chrome or aurora
    const Rgb col = hexc(L ? d.white : d.whiteR);
    Paint paint = Paint::solid(col);
    if (d.fx & fx::Rainbow) {
      paint = Paint::solid(hsl((float)fmod(td * 40, 360.0) + side * 30 + d.hue, 95, 66));
    } else if (d.fx & fx::Chrome) {
      paint.kind = Paint::Linear;
      X.apply(-rx - gx * rx * 0.8f, -ry, paint.x0, paint.y0);
      X.apply(rx - gx * rx * 0.8f, ry, paint.x1, paint.y1);
      const Rgb W = hexc(0xFFFFFF), K = hexc(0x2A2C33);
      auto tone = [&](float k) { return mixc(col, k > 0 ? W : K, fabsf(k)); };
      paint.addStop(0, tone(0.7f));
      paint.addStop(0.38f, tone(-0.35f));
      paint.addStop(0.52f, tone(0.85f));
      paint.addStop(0.66f, tone(-0.55f));
      paint.addStop(1, tone(0.4f));
    } else if (d.fx & fx::Aurora) {
      paint.kind = Paint::Linear;
      X.apply(-rx, ry, paint.x0, paint.y0);
      X.apply(rx, -ry, paint.x1, paint.y1);
      for (int i = 0; i <= 6; ++i) {
        const int na = d.nAurora ? d.nAurora : 3;
        const float p = fmodPos(i / 6.0 + td * 0.12, 1.0), k = p * na;
        const int ki = (int)floorf(k);
        paint.addStop(i / 6.0f, mixc(hexc(d.aurora[ki % na]), hexc(d.aurora[(ki + 1) % na]), k - ki));
      }
    }
    if (d.fx & fx::Outline) {
      p_.clear();
      p_.xf = X;
      p_.stroke(pts, N, D * 0.022f * g.k, true);
      ras_.fill(cv, p_, paint, A);
    } else {
      ras_.composite(cv, body_, paint, A);
    }
    const Mask* clip = &body_;
    if (d.fx & fx::Shimmer) {  // a crisp light band sweeping across
      const float p = fmodPos(td + (L ? 0 : 0.12), 3.4) / 0.8f;
      if (p < 1) {
        p_.clear();
        p_.xf = X.rotated(0.45f);
        const float x = -rx * 2 + (rx * 4) * p;
        const float r1[8] = {x, -ry * 2, x + rx * 0.28f, -ry * 2, x + rx * 0.28f, ry * 2, x, ry * 2};
        const float x2 = x + rx * 0.38f;
        const float r2[8] = {x2, -ry * 2, x2 + rx * 0.1f, -ry * 2, x2 + rx * 0.1f, ry * 2, x2, ry * 2};
        p_.polygon(r1, 4);
        p_.polygon(r2, 4);
        ras_.fill(cv, p_, hexc(0xFFFFFF), 0.42f * A, clip);
      }
    }
    // the pupil
    const Rgb pc = hexc(!o.hetero ? d.pupilL : (L ? d.pupilL : d.pupilR));
    const float ps = fmaxf(0, L ? rig.ch(Ch_pupilL) : rig.ch(Ch_pupilR));
    const float listen = rig.ch(Ch_listen);
    const float pulse = listen > 0.02f ? 1 + 0.28f * rig.level() * clampf_(listen, 0, 1) : 1;
    const float wob = rig.gazeMode() == GazeMode::Wobble ? sinf(t * 13 + side) * 0.025f : 0;
    const float px = (-side * d.inset + gx * d.travel + wob) * rx, py = (gy * d.travel * 0.78f + 0.04f) * ry;
    const float syv = sy != 0 ? sy : 1;
    const float prx = d.prx * rx * ps * pulse;
    const float pry = (d.pry * ry * ps * pulse) / syv / fmaxf(0.3f, 1 - 0.12f * clampf_(g.b, 0, 1)) * 0.98f;
    if (ps > 0.01f) {
      Info info;
      if (d.fx & (fx::Starfield | fx::Galaxy)) {
        info = pupilShape(cv, d, d.pupil, px, py, prx, pry, pc, t, side, rig, X, clip, A);
        p_.clear();
        p_.xf = X;
        const float mr = fmaxf(prx, pry);
        // dots of light drifting out of the pupil (culled to it instead of clipped)
        for (int i = 0; i < 18; ++i) {
          const float z = fmodPos(h01(i + (int)side * 50) + td * 0.25, 1.0);
          const float a = (float)h01(i * 7 + 3) * kTau, rr = z * mr * 1.2f;
          const float dx = cosf(a) * rr, dy = sinf(a) * rr;
          if ((dx / prx) * (dx / prx) + (dy / pry) * (dy / pry) > 0.92f) continue;
          Path& pp = p_;
          pp.clear();
          pp.xf = X;
          pp.circle(px + dx, py + dy, fmaxf(0.6f, prx * 0.06f * z));
          ras_.fill(cv, pp, hexc(0xFFFFFF), (0.3f + 0.7f * z) * A, clip);
        }
      } else if (d.fx & fx::Folk) {
        const float fr = fminf(prx, pry);
        p_.clear();
        p_.xf = X;
        p_.circle(px, py, fr * 1.08f);
        ras_.fill(cv, p_, pc, A, clip);
        p_.clear();
        p_.xf = X;
        p_.circle(px, py, fr * 0.9f);
        ras_.fill(cv, p_, hexc(d.folkBase), A, clip);
        const int n = 9;
        const float cell = (fr * 1.62f) / n, q = cell * 0.36f, lw = cell * 0.42f;
        for (int pass = 0; pass < 2; ++pass) {  // '1' stitches in the pupil colour, '2' in the thread
          p_.clear();
          p_.xf = X;
          for (int j = 0; j < n; ++j)
            for (int i = 0; i < n; ++i) {
              const char ch = kMotif[j][i];
              if (ch == '.' || (ch == '1') != (pass == 0)) continue;
              const float x = px + (i - 4) * cell, y = py + (j - 4) * cell;
              const float s1[4] = {x - q, y - q, x + q, y + q}, s2[4] = {x + q, y - q, x - q, y + q};
              p_.stroke(s1, 2, lw);
              p_.stroke(s2, 2, lw);
            }
          ras_.fill(cv, p_, pass == 0 ? pc : hexc(d.folkThread), A, clip);
        }
        info.gs = 0.5f;
        info.gx = 0.55f;
        info.gy = -0.62f;
      } else {
        info = pupilShape(cv, d, d.pupil, px, py, prx, pry, pc, t, side, rig, X, clip, A);
      }
      if (d.glint && !info.none) {
        const float gs = fminf(prx, pry) * d.glintSize * info.gs;
        glint(cv, d, px + info.gx * prx, py + info.gy * pry, 0.3f * gs, 0.2f * gs, -0.55f, X, clip, A);
      }
    }
    // alternate pupils (heart / star / spiral / battery / level) burst in with overshoot
    const float av = L ? rig.ch(Ch_altL) : rig.ch(Ch_altR);
    if (av > 0.01f) {
      const Pupil at = rig.altType();
      const float k = fmaxf(0, av);
      const float beat = at == Pupil::Heart ? 1 + 0.09f * powf(fmaxf(0, sinf(t * kTau * 1.3f)), 8) : 1;
      const Rgb ac = at == Pupil::Heart ? hexc(0xFF2E63) : (at == Pupil::Star ? hexc(0xFFD23A) : pc);
      const float ar = 0.42f * rx * 1.05f * k * beat, ary = 0.5f * ry * 0.95f * k * beat;
      const float ax = px * 0.5f, ay = py * 0.5f - ry * 0.03f;
      const Info inf = pupilShape(cv, d, at, ax, ay, ar, ary, ac, t, side, rig, X, clip, A);
      if (!inf.none && d.glint) glint(cv, d, ax - ar * 0.4f, ay - ary * 0.45f, ar * 0.17f, ar * 0.11f, -0.6f, X, clip, A);
    }
  }
  // >< squeeze
  if (g.sq > 0.02f) {
    const float sqc = clampf_(g.sq, 0, 1.3f);
    const float w = d.rx * D * fmaxf(0, rig.ch(Ch_scale)) * 0.85f * sqc, h = d.ry * D * 0.45f * sqc;
    Rgb c = hexc(side > 0 ? d.whiteR : d.white);
    if (d.fx & fx::Rainbow) c = hsl((float)fmod(td * 40, 360.0), 95, 66);
    const float dir = -side;
    const float pts[6] = {-dir * w * 0.5f, -h, dir * w * 0.55f, 0, -dir * w * 0.5f, h};
    p_.clear();
    p_.xf = G.translated(g.x, g.y);
    p_.stroke(pts, 3, D * 0.032f);
    ras_.fill(cv, p_, c, A);
  }
}

void EyeRenderer::drop(Canvas& cv, const Xform& G, float x, float y, float r, float a) {
  if (a <= 0.004f || r <= 0.1f) return;
  p_.clear();
  p_.xf = G;
  p_.moveTo(x, y - r * 1.7f);
  quadTo(p_, x, y - r * 1.7f, x + r * 1.05f, y - r * 0.2f, x, y + r);
  quadTo(p_, x, y + r, x - r * 1.05f, y - r * 0.2f, x, y - r * 1.7f);
  p_.close();
  ras_.fill(cv, p_, hexc(0x6FC3FF), a);
  p_.clear();
  p_.xf = G;
  p_.ellipse(x - r * 0.3f, y - r * 0.15f, r * 0.22f, r * 0.32f, -0.3f);
  ras_.fill(cv, p_, hexc(0xE6F6FF), a);
}

void EyeRenderer::overlays(Canvas& cv, const EyeRig& rig, const Design& d, float cx, float cy, float D,
                           const Xform& G, float A0) {
  const float t = (float)fmod(rig.time(), 3600.0);
  const double td = rig.time();
  const Rgb ink = hexc(d.white);
  auto A = [](float v) { return clampf_(v, 0, 1); };
  auto begin = [&](const Xform& X) {
    p_.clear();
    p_.xf = X;
  };
  // blush: flat ovals with three little strokes
  const float blush = rig.ch(Ch_blush);
  if (blush > 0.02f)
    for (const EyeGeom& g : eyes_) {
      const float x = g.x + g.side * d.rx * D * 0.35f, y = g.y + d.ry * D * 0.98f;
      begin(G);
      p_.ellipse(x, y, D * 0.06f, D * 0.026f);
      ras_.fill(cv, p_, hexc(0xFF6F9C), 0.55f * A(blush) * A0);
      begin(G);
      for (int i = -1; i <= 1; ++i) {
        const float s[4] = {x + i * D * 0.022f - D * 0.006f, y + D * 0.01f, x + i * D * 0.022f + D * 0.006f, y - D * 0.01f};
        p_.stroke(s, 2, D * 0.006f);
      }
      ras_.fill(cv, p_, hexc(0xFF9DBC), 0.9f * A(blush) * A0);
    }
  // tears
  const float tears = rig.ch(Ch_tears);
  if (tears > 0.02f) {
    const EyeGeom& g = eyes_[1];
    const float per = 2.2f, p = fmodPos(td, per) / per;
    const float x = g.x + g.rx * 0.55f, y0 = g.y + g.ry * 0.75f;
    const float grow = smooth(p / 0.45f), fall = p > 0.45f ? powf((p - 0.45f) / 0.55f, 2) : 0;
    drop(cv, G, x, y0 + fall * D * 0.32f, D * 0.017f * (0.4f + 0.6f * grow), A(tears) * (1 - smooth((fall - 0.7f) / 0.3f)) * A0);
  }
  const float cry = rig.ch(Ch_cry);
  if (cry > 0.02f)
    for (const EyeGeom& g : eyes_) {
      const float a = A(cry), x0 = g.x + g.side * g.rx * 0.45f, y0 = g.y + g.ry * 0.5f, w = D * 0.034f;
      float pts[2 * 26];
      int n = 0;
      for (int i = 0; i <= 12; ++i, ++n) {
        pts[2 * n] = x0 - w / 2 + sinf(i * 0.9f - t * 9) * D * 0.006f;
        pts[2 * n + 1] = y0 + (i / 12.0f) * D * 0.5f;
      }
      for (int i = 12; i >= 0; --i, ++n) {
        pts[2 * n] = x0 + w / 2 + sinf(i * 0.9f - t * 9 + 1) * D * 0.006f;
        pts[2 * n + 1] = y0 + (i / 12.0f) * D * 0.5f;
      }
      begin(G);
      p_.polygon(pts, n);
      ras_.fill(cv, p_, hexc(0x6FC3FF), 0.85f * a * A0);
      for (int i = 0; i < 3; ++i) {
        const float p = fmodPos(td * 1.6 + i / 3.0, 1.0);
        drop(cv, G, x0 + sinf(i * 3.0f) * w * 0.2f, y0 + p * D * 0.45f, D * 0.012f, a * (1 - p * 0.3f) * A0);
      }
    }
  // ? and ! and …
  const float q = rig.ch(Ch_q);
  if (q > 0.03f) {
    const float k = clampf_(q, 0, 1.3f), x = cx + 0.3f * D, y = cy - 0.27f * D + sinf(t * 2.5f) * D * 0.008f;
    const float r = D * 0.032f * k;
    const Xform X = G.translated(x, y).rotated(0.18f + sinf(t * 2) * 0.08f);
    float pts[2 * 40];
    int n = 0;
    const float a0 = kPi * 1.05f, a1 = kPi * 2.35f;
    for (int i = 0; i <= 24; ++i, ++n) {
      const float a = a0 + (a1 - a0) * i / 24;
      pts[2 * n] = cosf(a) * r;
      pts[2 * n + 1] = sinf(a) * r;
    }
    const float sx = pts[2 * (n - 1)], sy = pts[2 * (n - 1) + 1];
    for (int i = 1; i <= 8; ++i, ++n) {
      const float tt = i / 8.0f, u = 1 - tt;
      pts[2 * n] = u * u * sx + 2 * u * tt * 0 + tt * tt * 0;
      pts[2 * n + 1] = u * u * sy + 2 * u * tt * (r * 0.9f) + tt * tt * (r * 1.5f);
    }
    begin(X);
    p_.stroke(pts, n, D * 0.016f * k);
    p_.circle(0, r * 2.35f, D * 0.01f * k);
    ras_.fill(cv, p_, ink, A0);
  }
  const float bang = rig.ch(Ch_bang);
  if (bang > 0.03f) {
    const float k = clampf_(bang, 0, 1.4f);
    const Xform X = G.translated(cx + 0.31f * D, cy - 0.3f * D).rotated(0.15f);
    const float pts[8] = {-D * 0.014f * k, -D * 0.05f * k, D * 0.014f * k, -D * 0.05f * k,
                          D * 0.006f * k, D * 0.012f * k, -D * 0.006f * k, D * 0.012f * k};
    begin(X);
    p_.polygon(pts, 4);
    p_.circle(0, D * 0.032f * k, D * 0.01f * k);
    ras_.fill(cv, p_, ink, A0);
  }
  const float dots = rig.ch(Ch_dots);
  if (dots > 0.03f)
    for (int i = 0; i < 3; ++i) {
      const float bnc = fmaxf(0, sinf(t * 5 - i * 0.9f));
      begin(G);
      p_.circle(cx + (0.2f + i * 0.05f) * D, cy - (0.3f + i * 0.03f) * D - bnc * 0.012f * D, D * (0.012f + i * 0.003f));
      ras_.fill(cv, p_, ink, A(dots) * (0.4f + 0.6f * bnc) * A0);
    }
  const float zzz = rig.ch(Ch_zzz);
  if (zzz > 0.05f)
    for (int i = 0; i < 2; ++i) {
      const float p = fmodPos(td * 0.36 + i * 0.5, 1.0);
      const float x = cx + (0.3f + p * 0.05f) * D, y = cy - (0.25f + p * 0.1f) * D;
      const float z = D * (0.05f - i * 0.016f) * (0.65f + 0.35f * p);
      const float pts[8] = {x, y, x + z, y, x, y + z, x + z, y + z};
      begin(G);
      p_.stroke(pts, 4, D * 0.013f);
      ras_.fill(cv, p_, ink, sinf(p * kPi) * A(zzz) * A0);
    }
  const float hearts = rig.ch(Ch_hearts);
  if (hearts > 0.02f) {
    static const float kHx[3] = {-0.08f, 0.12f, 0.02f};
    for (int i = 0; i < 3; ++i) {
      const float per = 1.9f, p = fmodPos(td + i * 0.63, per) / per;
      const float x = cx + kHx[i] * D + sinf(t * 2.4f + i) * 0.012f * D, y = cy + (0.3f - 0.42f * p) * D;
      const float pop = p < 0.18f ? outBackf(p / 0.18f, 2.4f) : 1 - smooth((p - 0.75f) / 0.25f);
      if (pop > 0.01f) {
        begin(G);
        heartPath(p_, x, y, D * 0.034f * pop * A(hearts), sinf(t * 3 + i) * 0.25f);
        ras_.fill(cv, p_, hexc(0xFF2E63), A0);
      }
    }
  }
  const float spark = rig.ch(Ch_spark);
  if (spark > 0.02f)
    for (int i = 0; i < 6; ++i) {
      const float per = 1.1f + (float)h01(i) * 0.6f;
      const float p = fmodPos(td + h01(i + 9) * per, per) / per, a = sinf(p * kPi);
      const float ang = (i / 6.0f) * kTau + 0.4f, rr = 0.33f + 0.05f * (float)h01(i + 3);
      const float r = D * 0.024f * a * A(spark);
      if (r < 0.3f) continue;
      begin(G);
      starPath(p_, cx + cosf(ang) * rr * D * 1.05f, cy + sinf(ang) * rr * D * 0.85f, r, 4, 0.3f, p);
      ras_.fill(cv, p_, (i % 2) ? hexc(0xFFD23A) : ink, A0);
    }
  const float spray = rig.ch(Ch_spray);
  if (spray > 0.02f)
    for (int i = 0; i < 12; ++i) {
      const float p = clampf_(fmodPos(td * 2.2 + h01(i), 1.0), 0, 1);
      const float ang = -kPi / 2 + ((float)h01(i + 5) - 0.5f) * 2.6f, rr = (0.08f + p * 0.38f) * D;
      begin(G);
      p_.circle(cx + cosf(ang) * rr, cy + 0.12f * D + sinf(ang) * rr * 0.6f, D * (0.006f + 0.006f * (float)h01(i + 2)));
      ras_.fill(cv, p_, (i % 3) ? hexc(0xBFE8FF) : ink, A(spray) * (1 - p) * A0);
    }
  const float check = rig.ch(Ch_check);
  if (check > 0.02f) {
    const float k = clampf_(check, 0, 1.3f), x = cx, y = cy + 0.31f * D;
    const float pts[6] = {x - 0.045f * D * k, y, x - 0.012f * D * k, y + 0.03f * D * k, x + 0.055f * D * k, y - 0.04f * D * k};
    begin(G);
    p_.stroke(pts, 3, D * 0.026f);
    ras_.fill(cv, p_, hexc(0x4DFFB0), A(check) * A0);
    const float p = fmodPos(td, 1.2) / 1.2f;
    begin(G);
    p_.strokeArc(cx, cy, D * (0.42f + 0.06f * p), 0, kTau, D * 0.008f);
    ras_.fill(cv, p_, hexc(0x4DFFB0), A(check) * (1 - p) * 0.8f * A0);
  }
  const float listen = rig.ch(Ch_listen);
  if (listen > 0.02f) {
    const float a = A(listen), lv = rig.level();
    for (int i = 0; i < 3; ++i) {
      const float r = D * (0.05f + i * 0.035f) * (0.9f + 0.2f * lv);
      begin(G);
      p_.strokeArc(cx + 0.34f * D, cy + 0.02f * D, r, -0.6f, 0.6f, D * 0.012f);
      p_.strokeArc(cx - 0.34f * D, cy + 0.02f * D, r, kPi - 0.6f, kPi + 0.6f, D * 0.012f);
      ras_.fill(cv, p_, ink, a * (0.9f - i * 0.25f) * (0.5f + 0.5f * lv) * A0);
    }
  }
  const float bolt = rig.ch(Ch_bolt);
  if (bolt > 0.02f) {
    const float k = clampf_(bolt, 0, 1.3f), x = cx, y = cy - 0.32f * D + sinf(t * 3) * D * 0.006f;
    const float pts[12] = {x + 0.01f * D * k, y - 0.05f * D * k, x - 0.03f * D * k, y + 0.006f * D * k,
                           x - 0.002f * D * k, y + 0.006f * D * k, x - 0.012f * D * k, y + 0.05f * D * k,
                           x + 0.03f * D * k, y - 0.008f * D * k, x + 0.002f * D * k, y - 0.008f * D * k};
    begin(G);
    p_.polygon(pts, 6);
    ras_.fill(cv, p_, hexc(0xFFD23A), A0);
  }
  if (d.fx & fx::Halo) {
    begin(G);
    for (int i = 0; i < 14; ++i) {
      const float a = (i / 14.0f) * kTau + (float)fmod(td * 0.25, (double)kTau);
      const float tw = 0.5f + 0.5f * sinf(t * 2.2f + i * 1.7f);
      starPath(p_, cx + cosf(a) * D * 0.43f, cy + sinf(a) * D * 0.43f, D * (0.008f + 0.01f * tw), 4, 0.3f, a);
    }
    ras_.fill(cv, p_, hexc(d.halo), A0);
  }
  if (d.fx & fx::Glitter) {
    begin(G);
    for (int i = 0; i < 6; ++i) {
      const float per = 2 + (float)h01(i + 1) * 2;
      const float p = fmodPos(td + h01(i) * per, per) / per, a = sinf(p * kPi);
      const float ang = (float)h01(i * 3) * kTau, rr = 0.24f + 0.2f * (float)h01(i * 5);
      const float r = D * 0.016f * a;
      if (r < 0.3f) continue;
      starPath(p_, cx + cosf(ang) * rr * D, cy + sinf(ang) * rr * D * 0.85f, r, 4, 0.3f, 0);
    }
    ras_.fill(cv, p_, hexc(d.glitter), A0);
  }
}

void EyeRenderer::render(Canvas& cv, const EyeRig& rig, const Design& d, float cx, float cy, float D,
                         const RenderOpts& o) {
  if (D < 2) return;
  const double td = rig.time();
  const float shk = rig.ch(Ch_shake), bnc = clampf_(rig.ch(Ch_bounce), 0, 1.5f);
  const float ox = shk * D * (float)sin(td * kTau * rig.shakeF());
  const float oy = shk * D * 0.4f * (float)sin(td * kTau * rig.shakeF() * 1.3 + 1);
  const float hopP = fabsf((float)sin(td * kTau * 1.6));
  const float by = -bnc * 0.03f * D * hopP;
  const Xform G = Xform::translate(cx + ox, cy + oy + by).rotated(rig.ch(Ch_rot)).translated(-cx, -cy);
  float sx = rig.ch(Ch_sx), sy = rig.ch(Ch_sy);
  if (bnc > 0.01f) {
    const float sq = 1 + bnc * 0.06f * (hopP - 0.5f);
    sy *= sq;
    sx /= sq;
  }
  ras_.setDiscClip(cx, cy, D * 0.5f);  // eyes.js clips everything to the glass disc
  drawEye(cv, rig, d, -1, cx, cy, D, sx, sy, G, o);
  drawEye(cv, rig, d, 1, cx, cy, D, sx, sy, G, o);
  if (o.overlays) overlays(cv, rig, d, cx, cy, D, G, o.alpha);
  ras_.clearDiscClip();
}

}  // namespace eyes
}  // namespace suflet
