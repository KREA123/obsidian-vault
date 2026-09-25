#include "TimePicker.h"

#include <math.h>
#include <stdio.h>

#include "Alarms.h"

namespace suflet {

namespace {

constexpr float kPi = 3.14159265f;
constexpr Rgb kCream = pal::kEyeDay;
constexpr Rgb kTrackCol = Rgb::hex(0x1A1813);
constexpr Rgb kInk = Rgb::hex(0x16130C);

// Areas the picker owns (the eyes live in the hole between them).
constexpr Rect kTitle{110, 44, 356, 84};
constexpr Rect kDigits{56, 146, 410, 274};
constexpr Rect kRel{70, 280, 396, 314};
constexpr Rect kOk{150, 318, 316, 384};
constexpr float kClear0 = 166, kClear1 = 244;  // annulus cleared before redrawing the ring

bool hitRect(const Rect& r, float x, float y) { return x >= r.x0 && x < r.x1 && y >= r.y0 && y < r.y1; }
bool intersects(const Rect& a, const Rect& b) {
  return !a.empty() && !b.empty() && a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
}

inline float wrapDeg(float d) {
  d = fmodf(d, 360.0f);
  return d < 0 ? d + 360.0f : d;
}

// Anti-aliased ring sector [r0, r1] x [a0, a0 + span] (degrees, clockwise),
// visiting only the pixels of the ring instead of its whole bounding box.
// The sector edges use two half-planes (no atan2 per pixel). With `bottom`
// set, the lower half (y > cy) is drawn in that colour instead.
void annulus(Canvas& cv, float cx, float cy, float r0, float r1, float a0, float span, Rgb c,
             float alpha, bool clear = false, const Rgb* bottom = nullptr) {
  const bool full = span >= 359.99f;
  const float s0 = a0 * kPi / 180.0f, s1 = (a0 + span) * kPi / 180.0f;
  const float ux0 = cosf(s0), uy0 = sinf(s0), ux1 = cosf(s1), uy1 = sinf(s1);
  const bool wide = span > 180.0f;
  const int ya = (int)floorf(cy - r1 - 1), yb = (int)ceilf(cy + r1 + 1);
  Rect touched;
  for (int y = ya < 0 ? 0 : ya; y < yb && y < cv.height(); ++y) {
    const float dy = y + 0.5f - cy;
    const float ro = r1 + 1.0f, ri = r0 - 1.0f;
    if (dy * dy >= ro * ro) continue;
    const Rgb col = (bottom && dy > 0) ? *bottom : c;
    const float ox = sqrtf(ro * ro - dy * dy);
    const float ix = (ri > 0 && dy * dy < ri * ri) ? sqrtf(ri * ri - dy * dy) : -1.0f;
    for (int part = 0; part < 2; ++part) {
      float xa, xb;
      if (ix < 0) {
        if (part) break;
        xa = cx - ox;
        xb = cx + ox;
      } else if (part == 0) {
        xa = cx - ox;
        xb = cx - ix;
      } else {
        xa = cx + ix;
        xb = cx + ox;
      }
      int x0 = (int)floorf(xa), x1 = (int)ceilf(xb);
      if (x0 < 0) x0 = 0;
      if (x1 > cv.width()) x1 = cv.width();
      if (x1 <= x0) continue;
      touched.add(Rect{x0, y, x1, y + 1});
      for (int x = x0; x < x1; ++x) {
        if (clear) {
          cv.data()[y * cv.width() + x] = 0;
          continue;
        }
        const float dx = x + 0.5f - cx;
        const float d = sqrtf(dx * dx + dy * dy);
        float cov = clampf(r1 - d + 0.5f, 0, 1) * clampf(d - r0 + 0.5f, 0, 1);
        if (cov <= 0) continue;
        if (!full) {  // perpendicular distances to the two edge rays
          const float d0 = ux0 * dy - uy0 * dx, d1 = dx * uy1 - dy * ux1;
          const float e = wide ? fmaxf(d0, d1) : fminf(d0, d1);
          cov *= clampf(0.5f + e, 0, 1);
          if (cov <= 0) continue;
        }
        cv.blend(x, y, col, cov * alpha);
      }
    }
  }
  cv.markDirty(touched);
}

void polar(float deg, float r, float& x, float& y) {
  const float a = deg * kPi / 180.0f;
  x = TimePicker::kCx + r * cosf(a);
  y = TimePicker::kCy + r * sinf(a);
}

int centreBase(const Font& f, float cy) {
  const Glyph* g = f.find('0');
  return (int)lroundf(cy - (g->y + g->h * 0.5f));
}

}  // namespace

void TimePicker::open(int hour, int minute) {
  open_ = true;
  set(hour, minute);
  mode_ = DialMode::Hours;
  dragging_ = okDown_ = false;
  advanceIn_ = -1;
  result_ = KbResult::None;
  changed_ = true;
}

void TimePicker::set(int h, int m) {
  h_ = ((h % 24) + 24) % 24;
  m_ = ((m % 60) + 60) % 60;
  changed_ = true;
}

void TimePicker::setNow(uint32_t t) {
  // the relative line only changes once a minute
  if (t / 60 != now_ / 60) changed_ = true;
  now_ = t;
}

void TimePicker::setMode(DialMode m) {
  if (m != mode_) changed_ = true;
  mode_ = m;
  advanceIn_ = -1;
}

void TimePicker::cancel() {
  result_ = KbResult::Cancel;
  open_ = false;
}

int TimePicker::hourAt(float deg) { return (int)lroundf(wrapDeg(deg - 90.0f) / 15.0f) % 24; }

int TimePicker::minuteAt(float deg, bool fast) {
  const float raw = wrapDeg(deg + 90.0f) / 6.0f;
  const int m = fast ? (int)lroundf(raw / 5.0f) * 5 : (int)lroundf(raw);
  return m % 60;
}

uint32_t TimePicker::minutesUntil() const {
  if (!now_) return 0;
  Alarm a;
  a.hour = (uint8_t)h_;
  a.minute = (uint8_t)m_;
  const uint32_t t = Alarms::nextFire(a, now_);
  return t ? (t - now_ + 59) / 60 : 0;
}

void TimePicker::setFromPoint(float x, float y, float t) {
  const float deg = atan2f(y - kCy, x - kCx) * (180.0f / kPi);
  bool fast = false;
  if (lastT_ >= 0 && t > lastT_) {
    float dd = fabsf(deg - lastDeg_);
    if (dd > 180) dd = 360 - dd;
    fast = dd / (t - lastT_) > 90.0f;  // above 90°/s: 5-minute steps
  }
  lastDeg_ = deg;
  lastT_ = t;
  if (mode_ == DialMode::Hours) {
    const int h = hourAt(deg);
    if (h != h_) changed_ = true;
    h_ = h;
  } else {
    const int m = minuteAt(deg, fast);
    if (m != m_) changed_ = true;
    m_ = m;
  }
}

bool TimePicker::touch(const TouchEv& e) {
  if (!open_) return false;
  const float x = e.x, y = e.y;
  const float r = sqrtf((x - kCx) * (x - kCx) + (y - kCy) * (y - kCy));
  switch (e.e) {
    case Ev::TouchDown:
      advanceIn_ = -1;
      okDown_ = hitRect(kOk, x, y) && r < 150;
      if (r >= 150) {  // the rim: absolute angle, and the drag is captured
        dragging_ = true;
        lastT_ = -1;
        setFromPoint(x, y, e.t);
      } else if (hitRect(kDigits, x, y)) {
        setMode(x < kCx ? DialMode::Hours : DialMode::Minutes);
      }
      return true;
    case Ev::TouchMove:
      if (dragging_) setFromPoint(x, y, e.t);
      return true;
    case Ev::TouchUp:
      if (dragging_) {
        dragging_ = false;
        if (mode_ == DialMode::Hours) advanceIn_ = 0.4f;  // then on to the minutes
      } else if (okDown_ && hitRect(kOk, x, y)) {
        result_ = KbResult::Commit;
        open_ = false;
      }
      okDown_ = false;
      return true;
    default:
      return true;
  }
}

void TimePicker::update(float dt) {
  if (advanceIn_ >= 0) {
    advanceIn_ -= dt;
    if (advanceIn_ < 0) setMode(DialMode::Minutes);
  }
}

bool TimePicker::overlaps(const Rect& r) const {
  if (changed_) return true;
  if (intersects(r, kTitle) || intersects(r, kDigits) || intersects(r, kRel) || intersects(r, kOk))
    return true;
  if (r.empty()) return false;
  // nearest and farthest distance from the centre to the rect vs. the ring
  const float nx = clampf(kCx, (float)r.x0, (float)r.x1), ny = clampf(kCy, (float)r.y0, (float)r.y1);
  const float fx = fmaxf(fabsf(r.x0 - kCx), fabsf(r.x1 - kCx)), fy = fmaxf(fabsf(r.y0 - kCy), fabsf(r.y1 - kCy));
  const float dn = sqrtf((nx - kCx) * (nx - kCx) + (ny - kCy) * (ny - kCy)), df = sqrtf(fx * fx + fy * fy);
  return dn <= kClear1 && df >= kClear0;
}

void TimePicker::render(Canvas& cv) {
  // clear what we own (not the middle, where the eyes are)
  for (const Rect& r : {kTitle, kDigits, kRel, kOk}) {
    cv.fillRect(r, pal::kBlack);
    cv.markDirty(r);
  }
  annulus(cv, kCx, kCy, kClear0, kClear1, 0, 360, pal::kBlack, 1, true);

  const bool H = mode_ == DialMode::Hours;
  const float r0 = kR - kTrack * 0.5f, r1 = kR + kTrack * 0.5f;
  if (H) {  // sundial: day (06-18, top) tinted cream, night ice, in one pass
    const Rgb day = Rgb::lerp(kTrackCol, kCream, 0.16f), night = Rgb::lerp(kTrackCol, pal::kIce, 0.16f);
    annulus(cv, kCx, kCy, r0, r1, 0, 360, day, 1, false, &night);
  } else {
    annulus(cv, kCx, kCy, r0, r1, 0, 360, kTrackCol, 1);
  }
  if (!H && m_ > 0) {  // sweep from 00 to the knob
    annulus(cv, kCx, kCy, r0, r1, 270, 6.0f * m_, kCream, 0.22f);
  }
  const int N = H ? 24 : 60;
  for (int i = 0; i < N; ++i) {
    const float deg = H ? hourAngle(i) : minuteAngle(i);
    const bool major = H ? i % 6 == 0 : i % 5 == 0;
    float ax, ay, bx, by;
    polar(deg, major ? 223.0f : 225.0f, ax, ay);
    polar(deg, 230.5f, bx, by);
    cv.segment(ax, ay, bx, by, major ? 2.6f : 1.8f, kCream, major ? 0.6f : 0.25f);
  }
  const Font& sf = fonts::small();
  for (int k = 0; k < 4; ++k) {
    const int v = H ? k * 6 : k * 15;
    char buf[4];
    snprintf(buf, sizeof buf, H ? "%d" : "%02d", v);
    float x, y;
    polar(H ? hourAngle(v) : minuteAngle(v), kR, x, y);
    cv.drawText(sf, x, centreBase(sf, y), buf, kCream, 0.6f, Align::Center);
  }
  // the knob
  float kx, ky;
  polar(knobAngle(), kR, kx, ky);
  cv.ellipse(kx, ky, 27, 27, kCream, 1, 9, 0.35f);
  char val[4];
  snprintf(val, sizeof val, "%02d", H ? h_ : m_);
  cv.drawText(sf, kx, centreBase(sf, ky), val, kInk, 1, Align::Center);

  // title
  cv.drawText(sf, kCx, centreBase(sf, 64), lang_ == Lang::Ro ? "ALARMĂ" : "ALARM", kCream, 0.6f,
              Align::Center);
  // big digits: the active part bright and underlined
  const Font& df = fonts::digits();
  char hh[4], mm[4];
  snprintf(hh, sizeof hh, "%02d", h_);
  snprintf(mm, sizeof mm, "%02d", m_);
  const int wh = Canvas::measureText(df, hh), wc = Canvas::measureText(df, ":"), wm = Canvas::measureText(df, mm);
  const float x0 = kCx - (wh + wc + wm) * 0.5f;
  const int base = centreBase(df, 206);
  cv.drawText(df, x0, base, hh, kCream, H ? 1.0f : 0.38f);
  cv.drawText(df, x0 + wh, base - 4, ":", kCream, 0.38f);
  cv.drawText(df, x0 + wh + wc, base, mm, kCream, H ? 0.38f : 1.0f);
  const float ux = H ? x0 : x0 + wh + wc, uw = H ? wh : wm;
  cv.roundRect(ux + 6, base + 12.0f, ux + uw - 6, base + 15.5f, 1.5f, kCream, 0.9f);

  // "rings in 9 h 12 min" keeps the two halves of the day apart
  const uint32_t mins = minutesUntil();
  if (mins) {
    char rel[48];
    const char* pre = lang_ == Lang::Ro ? "sună în" : "rings in";
    if (mins >= 60) snprintf(rel, sizeof rel, "%s %u h %u min", pre, (unsigned)(mins / 60), (unsigned)(mins % 60));
    else snprintf(rel, sizeof rel, "%s %u min", pre, (unsigned)mins);
    cv.drawText(sf, kCx, centreBase(sf, 297), rel, kCream, 0.55f, Align::Center);
  }
  // ✓
  cv.roundRect(173, 324, 293, 376, 26, pal::kMint);
  cv.segment(221, 351, 229, 359, 3.4f, kInk);
  cv.segment(229, 359, 245, 342, 3.4f, kInk);
  changed_ = false;
}

}  // namespace suflet
