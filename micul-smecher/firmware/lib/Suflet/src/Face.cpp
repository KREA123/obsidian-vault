#include "Face.h"

#include <math.h>

namespace suflet {

static constexpr float kPi = 3.14159265f;

static float hash01(uint32_t i) {
  i ^= i >> 16;
  i *= 0x7feb352dU;
  i ^= i >> 15;
  i *= 0x846ca68bU;
  i ^= i >> 16;
  return (float)(i & 0xFFFFFF) / 16777216.0f;
}

static void drawZ(Canvas& cv, float x, float y, float s, float th, Rgb c, float a) {
  cv.segment(x, y, x + s, y, th, c, a);
  cv.segment(x + s, y, x, y + s, th, c, a);
  cv.segment(x, y + s, x + s, y + s, th, c, a);
}

static void drawEye(Canvas& cv, const Face& f, const Eye& e, int side, float S, float cx0,
                    float cy0, Rgb col) {
  const float par = 1.0f - 0.07f * f.gx * (float)side;  // far eye is a bit smaller
  const float ex = cx0 + ((float)side * f.spacing + f.gx * 0.055f + e.dx) * S;
  const float ey = cy0 + (f.cy + f.gy * 0.06f + e.dy) * S;
  const float rx = f.eyeW * e.scale * e.sx * par * S;
  const float ry0 = f.eyeH * e.scale * e.sy * par * S;  // full height
  // Morphing into ^ ^ or a special style squints the normal eye shut first,
  // so transitions read as an expression change rather than a cross-fade.
  const float squint = 1.0f - 0.85f * (f.happy > f.styleAmt ? f.happy : f.styleAmt);
  const float ry = ry0 * (e.open < 0 ? 0 : e.open) * squint;
  const float glowR = 0.05f * S, glowA = 0.34f * f.glow;

  const float wNormal = (1.0f - f.happy) * (1.0f - f.styleAmt);
  if (wNormal > 0.01f && ry > 0.6f) {
    const float k = tanf(e.lidTilt) * (float)(-side);
    const float inv = 1.0f / sqrtf(1.0f + k * k);
    const float yTop = ey + (-1.0f + 2.0f * e.lidTop) * ry;
    const float yBot = ey + (1.0f - 2.0f * e.lidBot) * ry;
    const bool bot = e.lidBot > 0.001f;
    auto body = [=](float px, float py) {
      float d = Canvas::sdEllipse(px, py, ex, ey, rx, ry);
      const float dt = (yTop + k * (px - ex) - py) * inv;
      if (dt > d) d = dt;
      if (bot) {
        const float db = py - yBot;
        if (db > d) d = db;
      }
      return d;
    };
    cv.fillSdf(ex - rx, ey - ry, ex + rx, ey + ry, body, col, wNormal, glowR, glowA);
    // specular highlight, clipped by the lids
    const float hx = ex + rx * 0.22f, hy = ey - ry * 0.12f, hrx = rx * 0.34f, hry = ry * 0.46f;
    if (hry > 0.8f) {
      auto hl = [=](float px, float py) {
        float d = Canvas::sdEllipse(px, py, hx, hy, hrx, hry);
        const float dt = (yTop + k * (px - ex) - py) * inv;
        return d > dt ? d : dt;
      };
      cv.fillSdf(hx - hrx, hy - hry, hx + hrx, hy + hry, hl, pal::kWhite.scaled(f.bright),
                 0.45f * wNormal);
    }
  }

  const float th = 0.042f * S;
  if (f.happy > 0.01f) {
    const float a = f.happy * (1.0f - f.styleAmt);
    cv.arc(ex, ey + ry0 * 0.45f, rx * 1.0f, kPi + 0.35f, 2 * kPi - 0.35f, th, col, a, glowR, glowA);
  }
  if (f.styleAmt > 0.01f) {
    const float a = f.styleAmt;
    switch (f.style) {
      case EyeStyle::Closed:
        cv.arc(ex, ey - ry0 * 0.25f, rx * 0.95f, 0.35f, kPi - 0.35f, th * 0.85f, col, a, glowR,
               glowA);
        break;
      case EyeStyle::Squeeze: {
        const float s = -(float)side;  // left eye: ">", right eye: "<"
        const float tipX = ex + s * rx * 0.55f, backX = ex - s * rx * 0.7f;
        cv.segment(backX, ey - ry0 * 0.45f, tipX, ey, th, col, a, glowR, glowA);
        cv.segment(tipX, ey, backX, ey + ry0 * 0.45f, th, col, a, glowR, glowA);
        break;
      }
      case EyeStyle::Heart: {
        const float pulse = 1.0f + 0.08f * sinf(f.overlayT * 2.0f * kPi * 2.0f);
        cv.heart(ex, ey, rx * 2.1f * pulse, pal::kHeart.scaled(f.bright), a, glowR, glowA);
        break;
      }
      case EyeStyle::Star:
        cv.star(ex, ey, rx * 1.3f, f.spin * (float)side, pal::kGold.scaled(f.bright), a, glowR,
                glowA);
        break;
      case EyeStyle::Spiral:
        for (int i = 0; i < 3; ++i) {
          const float a0 = f.spin * (float)side + (float)i * 2.1f;
          cv.arc(ex, ey, rx * (0.32f + 0.3f * (float)i), a0, a0 + 3.9f, th * 0.7f, col, a);
        }
        break;
      case EyeStyle::Normal:
        break;
    }
  }

  if (f.blush > 0.01f) {
    cv.ellipse(ex + (float)side * rx * 0.25f, ey + f.eyeH * S * 1.02f, rx * 0.85f,
               f.eyeH * S * 0.24f, pal::kBlush.scaled(f.bright), 0.55f * f.blush, 0.03f * S,
               0.25f);
  }
}

void renderFace(Canvas& cv, const Face& f) { renderFace(cv, f, FaceLayout{}); }

void renderFace(Canvas& cv, const Face& f, const FaceLayout& lay) {
  if (lay.k <= 0.01f) return;
  const float S = (float)(cv.width() < cv.height() ? cv.width() : cv.height()) * lay.k;
  const float cx0 = cv.width() * 0.5f * (1.0f + lay.cx), cy0 = cv.height() * 0.5f * (1.0f + lay.cy);
  const Rgb col = f.color.scaled(f.bright);
  if (f.bright <= 0.01f) return;

  drawEye(cv, f, f.L, -1, S, cx0, cy0, col);
  drawEye(cv, f, f.R, +1, S, cx0, cy0, col);

  const float t = f.overlayT;
  const float th = 0.018f * S;
  if (f.overlays & ov::Zzz) {
    const float drift = fmodf(t * 0.25f, 1.0f);
    const float a = 0.55f + 0.45f * sinf(t * 2.0f);
    drawZ(cv, cx0 + 0.27f * S, cy0 - (0.20f + 0.04f * drift) * S, 0.065f * S, th, col, a);
    drawZ(cv, cx0 + 0.35f * S, cy0 - (0.30f + 0.04f * drift) * S, 0.045f * S, th * 0.8f, col,
          a * 0.8f);
  }
  if (f.overlays & ov::Hearts) {
    for (int i = 0; i < 3; ++i) {
      const float p = t / 1.4f - (float)i * 0.22f;
      if (p <= 0 || p >= 1) continue;
      const float x = cx0 + (hash01(i + 11) - 0.5f) * 0.36f * S;
      const float y = cy0 + (0.26f - 0.55f * p) * S;
      const float a = p < 0.2f ? p / 0.2f : 1.0f - (p - 0.2f) / 0.8f;
      cv.heart(x, y, (0.05f + 0.02f * hash01(i + 3)) * S, pal::kHeart.scaled(f.bright), a,
               0.02f * S, 0.3f);
    }
  }
  if (f.overlays & ov::Orbit) {
    for (int i = 0; i < 3; ++i) {
      const float ang = t * 3.2f + (float)i * 2.094f;
      cv.star(cx0 + cosf(ang) * 0.13f * S, cy0 - 0.31f * S + sinf(ang) * 0.035f * S, 0.024f * S,
              t * 4, pal::kGold.scaled(f.bright), 0.9f);
    }
  }
  if (f.overlays & ov::Question) {
    const float qx = cx0 + 0.30f * S, qy = cy0 - 0.30f * S, r = 0.04f * S;
    cv.arc(qx, qy, r, kPi, 2 * kPi + 1.3f, th, col, 0.9f);
    const float ax = qx + r * cosf(1.3f), ay = qy + r * sinf(1.3f);
    cv.segment(ax, ay, qx, qy + 0.075f * S, th, col, 0.9f);
    cv.ellipse(qx, qy + 0.115f * S, th * 0.7f, th * 0.7f, col, 0.9f);
  }
  if (f.overlays & ov::Sweat) {
    const float sx = cx0 + 0.33f * S, sy = cy0 - 0.1f * S + fmodf(t * 0.05f, 0.05f) * S;
    cv.ellipse(sx, sy, 0.022f * S, 0.024f * S, pal::kIce.scaled(f.bright), 0.9f);
    cv.segment(sx, sy - 0.045f * S, sx, sy - 0.005f * S, 0.012f * S, pal::kIce.scaled(f.bright),
               0.9f);
  }
  if ((f.overlays & ov::Yawn) && f.mouth > 0.02f) {
    const float mx = cx0, my = cy0 + 0.24f * S;
    const float rx = 0.055f * S * f.mouth, ry = 0.065f * S * f.mouth, h = 0.015f * S;
    cv.fillSdf(
        mx - rx, my - ry, mx + rx, my + ry,
        [=](float px, float py) { return fabsf(Canvas::sdEllipse(px, py, mx, my, rx, ry)) - h; },
        col, 0.9f);
  }
  if (f.overlays & ov::Zigzag) {
    const float y0 = cy0 + 0.22f * S, x0 = cx0 - 0.08f * S, stp = 0.027f * S, amp = 0.018f * S;
    for (int i = 0; i < 6; ++i) {
      const float ya = y0 + ((i % 2) ? -amp : amp), yb = y0 + ((i % 2) ? amp : -amp);
      cv.segment(x0 + stp * (float)i, ya, x0 + stp * (float)(i + 1), yb, th * 1.4f, col, 0.9f);
    }
  }
  if (f.overlays & ov::Confetti) {
    static const Rgb kC[5] = {pal::kHeart, pal::kGold, pal::kMint, pal::kIce, pal::kBlush};
    for (int i = 0; i < 22; ++i) {
      const float x = cx0 + (hash01(i * 7 + 1) - 0.5f) * 0.8f * S;
      const float spd = 0.12f + 0.1f * hash01(i * 7 + 2);
      const float y = cy0 + (-0.45f + fmodf(hash01(i * 7 + 3) + t * spd, 0.9f)) * S;
      cv.ellipse(x, y, 0.011f * S, 0.016f * S, kC[i % 5].scaled(f.bright), 0.85f);
    }
  }
  if (f.overlays & ov::Listen) {
    const float pulse = 0.5f + 0.5f * sinf(t * 3.0f);
    const float thick = 0.010f * S + 0.022f * S * f.level;
    cv.ring(cx0, cy0, 0.465f * S - thick * 0.5f, thick, pal::kIce.scaled(f.bright),
            0.25f + 0.35f * pulse + 0.4f * f.level, 0.03f * S, 0.25f);
  }
  if (f.overlays & ov::Alert) {
    const float pulse = 0.5f + 0.5f * sinf(t * 5.0f);
    const float thick = 0.014f * S + 0.01f * S * pulse;
    cv.ring(cx0, cy0, 0.465f * S - thick * 0.5f, thick, Rgb::hex(0xFFB347).scaled(f.bright),
            0.35f + 0.5f * pulse, 0.035f * S, 0.3f);
  }
  if ((f.overlays & ov::Progress) && f.progress > 0.005f) {
    const float r = 0.44f * S, a0 = -kPi * 0.5f;
    cv.arc(cx0, cy0, r, a0, a0 + 2.0f * kPi * (f.progress > 0.999f ? 0.999f : f.progress),
           0.03f * S, pal::kMint.scaled(f.bright), 0.95f, 0.03f * S, 0.35f);
  }
  if (f.overlays & ov::Think) {
    for (int i = 0; i < 3; ++i) {
      const float b = sinf(t * 6.0f - (float)i * 0.9f);
      cv.ellipse(cx0 + (-0.06f + 0.06f * (float)i) * S, cy0 + (0.25f - 0.012f * (b > 0 ? b : 0)) * S,
                 0.016f * S, 0.016f * S, col, 0.5f + 0.5f * (b > 0 ? b : 0));
    }
  }
}

}  // namespace suflet
