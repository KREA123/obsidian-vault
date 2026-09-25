#include "Canvas.h"

namespace suflet {

static constexpr float kTau = 6.28318531f;

float Canvas::sdEllipse(float px, float py, float cx, float cy, float rx, float ry) {
  // First-order distance: (f - 1) / |grad f|. Exact for circles, very close
  // to the true distance near the outline of an ellipse (where it matters).
  const float ex = px - cx, ey = py - cy;
  const float nx = ex / rx, ny = ey / ry;
  const float f = sqrtf(nx * nx + ny * ny);
  if (f < 1e-5f) return -(rx < ry ? rx : ry);
  const float gx = nx / (rx * f), gy = ny / (ry * f);
  const float g = sqrtf(gx * gx + gy * gy);
  return (f - 1.0f) / g;
}

float Canvas::sdSegment(float px, float py, float x0, float y0, float x1, float y1) {
  const float pax = px - x0, pay = py - y0, bax = x1 - x0, bay = y1 - y0;
  const float bb = bax * bax + bay * bay;
  const float h = bb > 1e-9f ? clampf((pax * bax + pay * bay) / bb, 0, 1) : 0;
  const float dx = pax - bax * h, dy = pay - bay * h;
  return sqrtf(dx * dx + dy * dy);
}

float Canvas::sdArc(float px, float py, float cx, float cy, float r, float a0, float a1) {
  const float dx = px - cx, dy = py - cy;
  float span = a1 - a0;
  if (span < 0) span += kTau;
  float rel = atan2f(dy, dx) - a0;
  rel = fmodf(rel, kTau);
  if (rel < 0) rel += kTau;
  if (rel <= span) return fabsf(sqrtf(dx * dx + dy * dy) - r);
  const float e0x = cx + r * cosf(a0), e0y = cy + r * sinf(a0);
  const float e1x = cx + r * cosf(a1), e1y = cy + r * sinf(a1);
  const float d0 = sqrtf((px - e0x) * (px - e0x) + (py - e0y) * (py - e0y));
  const float d1 = sqrtf((px - e1x) * (px - e1x) + (py - e1y) * (py - e1y));
  return d0 < d1 ? d0 : d1;
}

float Canvas::sdHeart(float x, float y) {
  // Inigo Quilez, "2D distance functions" (MIT). Tip at origin, y up.
  x = fabsf(x);
  if (y + x > 1.0f) {
    const float dx = x - 0.25f, dy = y - 0.75f;
    return sqrtf(dx * dx + dy * dy) - 0.35355339f;
  }
  const float d1 = x * x + (y - 1.0f) * (y - 1.0f);
  const float m = 0.5f * fmaxf(x + y, 0.0f);
  const float d2 = (x - m) * (x - m) + (y - m) * (y - m);
  const float d = sqrtf(fminf(d1, d2));
  return (x - y) > 0 ? d : -d;
}

float Canvas::sdStar5(float x, float y, float r) {
  // Inigo Quilez sdStar5 (MIT), y up, one point facing up, inner ratio 0.5.
  const float k1x = 0.809016994f, k1y = -0.587785252f;
  const float k2x = -k1x, k2y = k1y;
  x = fabsf(x);
  float d = fmaxf(k1x * x + k1y * y, 0.0f);
  x -= 2.0f * d * k1x;
  y -= 2.0f * d * k1y;
  d = fmaxf(k2x * x + k2y * y, 0.0f);
  x -= 2.0f * d * k2x;
  y -= 2.0f * d * k2y;
  x = fabsf(x);
  y -= r;
  const float rf = 0.5f;
  const float bax = rf * -k1y - 0.0f, bay = rf * k1x - 1.0f;
  const float h = clampf((x * bax + y * bay) / (bax * bax + bay * bay), 0.0f, r);
  const float qx = x - bax * h, qy = y - bay * h;
  const float len = sqrtf(qx * qx + qy * qy);
  return (y * bax - x * bay) > 0 ? len : -len;
}

void Canvas::ellipse(float cx, float cy, float rx, float ry, Rgb c, float alpha, float glowR,
                     float glowA) {
  if (rx < 0.3f || ry < 0.3f) return;
  fillSdf(
      cx - rx, cy - ry, cx + rx, cy + ry,
      [=](float px, float py) { return sdEllipse(px, py, cx, cy, rx, ry); }, c, alpha, glowR,
      glowA);
}

void Canvas::ring(float cx, float cy, float r, float thick, Rgb c, float alpha, float glowR,
                  float glowA) {
  const float h = thick * 0.5f;
  fillSdf(
      cx - r - h, cy - r - h, cx + r + h, cy + r + h,
      [=](float px, float py) {
        const float dx = px - cx, dy = py - cy;
        return fabsf(sqrtf(dx * dx + dy * dy) - r) - h;
      },
      c, alpha, glowR, glowA);
}

void Canvas::segment(float x0, float y0, float x1, float y1, float thick, Rgb c, float alpha,
                     float glowR, float glowA) {
  const float h = thick * 0.5f;
  fillSdf(
      fminf(x0, x1) - h, fminf(y0, y1) - h, fmaxf(x0, x1) + h, fmaxf(y0, y1) + h,
      [=](float px, float py) { return sdSegment(px, py, x0, y0, x1, y1) - h; }, c, alpha, glowR,
      glowA);
}

void Canvas::arc(float cx, float cy, float r, float a0, float a1, float thick, Rgb c, float alpha,
                 float glowR, float glowA) {
  const float h = thick * 0.5f;
  fillSdf(
      cx - r - h, cy - r - h, cx + r + h, cy + r + h,
      [=](float px, float py) { return sdArc(px, py, cx, cy, r, a0, a1) - h; }, c, alpha, glowR,
      glowA);
}

void Canvas::heart(float cx, float cy, float size, Rgb c, float alpha, float glowR, float glowA) {
  if (size < 1) return;
  const float inv = 1.0f / size;
  fillSdf(
      cx - 0.65f * size, cy - 0.62f * size, cx + 0.65f * size, cy + 0.55f * size,
      [=](float px, float py) {
        return sdHeart((px - cx) * inv, (cy - py) * inv + 0.5f) * size;
      },
      c, alpha, glowR, glowA);
}

void Canvas::star(float cx, float cy, float r, float rot, Rgb c, float alpha, float glowR,
                  float glowA) {
  if (r < 1) return;
  const float cr = cosf(rot), sr = sinf(rot);
  const float round = r * 0.12f;
  fillSdf(
      cx - r - round, cy - r - round, cx + r + round, cy + r + round,
      [=](float px, float py) {
        const float x = px - cx, y = py - cy;
        const float lx = x * cr + y * sr, ly = -x * sr + y * cr;
        return sdStar5(lx, -ly, r - round) - round;
      },
      c, alpha, glowR, glowA);
}

float Canvas::sdRoundBox(float px, float py, float cx, float cy, float hw, float hh, float r) {
  const float qx = fabsf(px - cx) - hw + r, qy = fabsf(py - cy) - hh + r;
  const float ox = qx > 0 ? qx : 0, oy = qy > 0 ? qy : 0;
  const float in = qx > qy ? qx : qy;
  return sqrtf(ox * ox + oy * oy) + (in < 0 ? in : 0) - r;
}

void Canvas::roundRect(float x0, float y0, float x1, float y1, float r, Rgb c, float alpha,
                       float glowR, float glowA) {
  if (x1 - x0 < 0.5f || y1 - y0 < 0.5f) return;
  const float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f;
  const float hw = (x1 - x0) * 0.5f, hh = (y1 - y0) * 0.5f;
  const float rr = fminf(r, fminf(hw, hh));
  fillSdf(
      x0, y0, x1, y1, [=](float px, float py) { return sdRoundBox(px, py, cx, cy, hw, hh, rr); },
      c, alpha, glowR, glowA);
}

// ------------------------------------------------------------------ text ---

int Canvas::measureText(const Font& f, const char* s, int nBytes) {
  if (!s) return 0;
  const char* end = nBytes < 0 ? nullptr : s + nBytes;
  int adv16 = 0;
  const char* p = s;
  while ((end ? p < end : *p != 0) && *p) {
    const Glyph* g = f.find(utf8::next(p, end));
    if (g) adv16 += g->adv16;
  }
  return (adv16 + 8) >> 4;
}

int Canvas::drawText(const Font& f, float x, int y, const char* s, Rgb c, float alpha, Align align,
                     const Rgb* accent, int nBytes) {
  if (!s || alpha <= 0.004f) return 0;
  const int width = measureText(f, s, nBytes);
  if (align == Align::Center) x -= width * 0.5f;
  else if (align == Align::Right) x -= (float)width;
  const char* end = nBytes < 0 ? nullptr : s + nBytes;
  int pen16 = (int)lroundf(x * 16.0f);
  Rect touched;
  const char* p = s;
  while ((end ? p < end : *p != 0) && *p) {
    const uint32_t cp = utf8::next(p, end);
    const Glyph* g = f.find(cp);
    if (!g) continue;
    const int gx = ((pen16 + 8) >> 4) + g->x, gy = y + g->y;
    pen16 += g->adv16;
    if (!g->w || !g->h) continue;
    const Rect box = clip(Rect{gx, gy, gx + g->w, gy + g->h});
    if (box.empty()) continue;
    touched.add(box);
    const Rgb col = (accent && utf8::isRoDiacritic(cp)) ? *accent : c;
    const uint16_t solid = col.to565();
    for (int py = box.y0; py < box.y1; ++py) {
      for (int px = box.x0; px < box.x1; ++px) {
        const uint8_t k = f.cov(*g, px - gx, py - gy);
        if (!k) continue;
        if (k == 15 && alpha >= 0.999f) buf_[py * w_ + px] = solid;
        else blend(px, py, col, k * (1.0f / 15.0f) * alpha);
      }
    }
  }
  markDirty(touched);
  return width;
}

}  // namespace suflet
