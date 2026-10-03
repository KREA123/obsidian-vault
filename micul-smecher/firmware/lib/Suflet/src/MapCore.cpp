// SOUL Maps on the device: bundle decoding, the view, routes and walking them,
// and the painter. See MapCore.h.
#include "MapCore.h"

#include <ArduinoJson.h>
#include <math.h>
#include <string.h>

#include <algorithm>

namespace suflet {
namespace maps {

static constexpr double kPi = 3.14159265358979323846;
static constexpr double kEarthR = 6371008.8;

void worldPx(double lat, double lon, int z, double& x, double& y) {
  if (lat > 85.05112878) lat = 85.05112878;
  if (lat < -85.05112878) lat = -85.05112878;
  const double n = kTile * ldexp(1.0, z);
  x = (lon + 180.0) / 360.0 * n;
  const double s = sin(lat * kPi / 180.0);
  y = (0.5 - log((1 + s) / (1 - s)) / (4 * kPi)) * n;
}

void latLon(double x, double y, int z, double& lat, double& lon) {
  const double n = kTile * ldexp(1.0, z);
  lon = x / n * 360.0 - 180.0;
  lat = atan(sinh(kPi * (1 - 2 * y / n))) * 180.0 / kPi;
}

double haversine(double lat1, double lon1, double lat2, double lon2) {
  const double p1 = lat1 * kPi / 180, p2 = lat2 * kPi / 180, dp = p2 - p1, dl = (lon2 - lon1) * kPi / 180;
  const double a = sin(dp / 2) * sin(dp / 2) + cos(p1) * cos(p2) * sin(dl / 2) * sin(dl / 2);
  return 2 * kEarthR * asin(fmin(1.0, sqrt(a)));
}

double bearing(double lat1, double lon1, double lat2, double lon2) {
  const double p1 = lat1 * kPi / 180, p2 = lat2 * kPi / 180, dl = (lon2 - lon1) * kPi / 180;
  const double y = sin(dl) * cos(p2), x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl);
  double b = atan2(y, x) * 180 / kPi;
  return b < 0 ? b + 360 : b;
}

double metresPerPx(double lat, int z) { return cos(lat * kPi / 180) * 2 * kPi * kEarthR / (kTile * ldexp(1.0, z)); }

bool decodePolyline(const char* s, std::vector<double>& out, int precision) {
  out.clear();
  if (!s) return false;
  const double f = pow(10.0, precision);
  long lat = 0, lon = 0;
  const char* p = s;
  while (*p) {
    long v[2];
    for (int k = 0; k < 2; ++k) {
      long res = 0;
      int shift = 0, b;
      do {
        if (!*p || shift > 30) return false;
        b = *p++ - 63;
        if (b < 0 || b > 63) return false;
        res |= (long)(b & 0x1F) << shift;
        shift += 5;
      } while (b >= 0x20);
      v[k] = (res & 1) ? ~(res >> 1) : (res >> 1);
    }
    lat += v[0];
    lon += v[1];
    out.push_back(lat / f);
    out.push_back(lon / f);
  }
  return !out.empty();
}

// ------------------------------------------------------------------ bundle --

static bool uvarint(const uint8_t* b, size_t n, size_t& i, uint32_t& v) {
  v = 0;
  for (int shift = 0; shift < 35; shift += 7) {
    if (i >= n) return false;
    const uint8_t c = b[i++];
    v |= (uint32_t)(c & 0x7F) << shift;
    if (c < 0x80) return true;
  }
  return false;
}
static inline int32_t unzig(uint32_t v) { return (int32_t)(v >> 1) ^ -(int32_t)(v & 1); }

void MapBundle::clear() {
  feats.clear();
  pts.clear();
  labels.clear();
  z = 0;
  w = h = 0;
}

bool MapBundle::decode(const uint8_t* b, size_t n) {
  clear();
  if (!b || n < 20 || memcmp(b, "SMB1", 4) != 0 || b[4] != 1) return false;
  const uint8_t zz = b[5];
  const uint16_t cnt = (uint16_t)(b[6] | b[7] << 8);
  const uint32_t ox = (uint32_t)b[8] | (uint32_t)b[9] << 8 | (uint32_t)b[10] << 16 | (uint32_t)b[11] << 24;
  const uint32_t oy = (uint32_t)b[12] | (uint32_t)b[13] << 8 | (uint32_t)b[14] << 16 | (uint32_t)b[15] << 24;
  const uint16_t ww = (uint16_t)(b[16] | b[17] << 8), hh = (uint16_t)(b[18] | b[19] << 8);
  if (zz < kMinZ || zz > kMaxZ || !ww || !hh || ww > 4096 || hh > 4096) return false;
  size_t i = 20;
  feats.reserve(cnt);
  for (int k = 0; k < cnt; ++k) {
    if (i + 4 > n) {
      clear();
      return false;
    }
    Feature f;
    f.cls = b[i];
    f.kind = b[i + 1];
    f.count = (uint16_t)(b[i + 2] | b[i + 3] << 8);
    i += 4;
    if (f.kind < Line || f.kind > Point || !f.count || pts.size() / 2 + f.count > 60000) {
      clear();
      return false;
    }
    f.first = (uint32_t)(pts.size() / 2);
    int32_t x = 0, y = 0;
    for (int p = 0; p < f.count; ++p) {
      uint32_t dx, dy;
      if (!uvarint(b, n, i, dx) || !uvarint(b, n, i, dy)) {
        clear();
        return false;
      }
      x += unzig(dx);
      y += unzig(dy);
      if (x < -32768 || x > 32767 || y < -32768 || y > 32767) {
        clear();
        return false;
      }
      pts.push_back((int16_t)x);
      pts.push_back((int16_t)y);
    }
    if (f.kind == Point) {
      if (i >= n || i + 1 + b[i] > n) {
        clear();
        return false;
      }
      f.labelLen = b[i];
      f.label = (uint16_t)labels.size();
      labels.append((const char*)b + i + 1, f.labelLen);
      i += 1 + f.labelLen;
    }
    feats.push_back(f);
  }
  z = zz;
  this->ox = ox;
  this->oy = oy;
  w = ww;
  h = hh;
  return true;
}

bool MapBundle::covers(int vz, double x0, double y0, double x1, double y1) const {
  if (!w) return false;
  const double f = ldexp(1.0, z - vz);  // view px -> bundle-zoom px
  return x0 * f >= ox && y0 * f >= oy && x1 * f <= (double)ox + w && y1 * f <= (double)oy + h;
}

// -------------------------------------------------------------------- view --

void MapView::centerOn(double lat, double lon) { worldPx(lat, lon, z, cx, cy); }

void MapView::toScreen(double wx, double wy, float& sx, float& sy) const {
  sx = (float)((wx - cx) * scale) + screenW * 0.5f;
  sy = (float)((wy - cy) * scale) + screenH * 0.5f;
}

void MapView::toWorld(float sx, float sy, double& wx, double& wy) const {
  wx = cx + (sx - screenW * 0.5f) / scale;
  wy = cy + (sy - screenH * 0.5f) / scale;
}

void MapView::pan(float dx, float dy) {
  cx -= dx / scale;
  cy -= dy / scale;
  const double n = kTile * ldexp(1.0, z);
  if (cy < 0) cy = 0;
  if (cy > n) cy = n;
  cx = fmod(fmod(cx, n) + n, n);
}

void MapView::zoomBy(float f) {
  scale *= f;
  while (scale >= 2.0f && z < kMaxZ) {
    scale *= 0.5f;
    ++z;
    cx *= 2;
    cy *= 2;
  }
  while (scale < 1.0f && z > kMinZ) {
    scale *= 2.0f;
    --z;
    cx *= 0.5;
    cy *= 0.5;
  }
  if (z == kMaxZ && scale > 2.0f) scale = 2.0f;
  if (z == kMinZ && scale < 1.0f) scale = 1.0f;
}

double MapView::lat() const {
  double la, lo;
  latLon(cx, cy, z, la, lo);
  return la;
}
double MapView::lon() const {
  double la, lo;
  latLon(cx, cy, z, la, lo);
  return lo;
}

// ------------------------------------------------------------------ routes --

const char* turnWord(Turn t, bool ro) {
  static const char* const en[] = {"Start",        "Straight on", "Slight left",  "Turn left",    "Sharp left",
                                   "Slight right", "Turn right",  "Sharp right",  "Turn around",  "Roundabout",
                                   "You're there", "Ferry"};
  static const char* const r[] = {"Pornește",        "Înainte",          "Ușor la stânga", "La stânga",
                                  "Brusc la stânga", "Ușor la dreapta",  "La dreapta",     "Brusc la dreapta",
                                  "Întoarce-te",     "Sensul giratoriu", "Ai ajuns",       "Feribot"};
  const int i = (int)t;
  if (i < 0 || i > (int)Turn::Ferry) return ro ? r[1] : en[1];
  return ro ? r[i] : en[i];
}

bool RouteData::parse(const char* json, size_t n) {
  *this = RouteData();
  JsonDocument doc;
  if (deserializeJson(doc, json, n)) return false;
  JsonObjectConst o = doc.as<JsonObjectConst>();
  if (o.isNull()) return false;
  id = o["id"] | "";
  to = o["to"] | "";
  mode = o["mode"] | "walk";
  src = o["src"] | "";
  distM = o["dist"] | 0;
  durS = o["dur"] | 0;
  if (o["dest"].is<JsonArrayConst>() && o["dest"].size() == 2) {
    destLat = o["dest"][0] | 0.0;
    destLon = o["dest"][1] | 0.0;
  }
  if (!decodePolyline(o["shape"] | "", shape) || shape.size() < 4 || shape.size() > 8000) {
    *this = RouteData();
    return false;
  }
  const int np = points();
  for (JsonArrayConst s : o["steps"].as<JsonArrayConst>()) {
    if (steps.size() >= 60) break;
    Step st;
    const int t = s[0] | 1;
    st.turn = (t >= 0 && t <= (int)Turn::Ferry) ? (Turn)t : Turn::Straight;
    st.distM = s[1] | 0;
    st.idx = s[2] | 0;
    if (st.idx < 0) st.idx = 0;
    if (st.idx >= np) st.idx = np - 1;
    st.street = s[3] | "";
    if (st.street.size() > 40) st.street.resize(40);
    st.exit = s[4] | 0;
    steps.push_back(st);
  }
  if (steps.empty()) {
    *this = RouteData();
    return false;
  }
  if (steps.back().turn != Turn::Arrive) {  // the last maneuver is always "you're there" at the end of the line
    Step a;
    a.turn = Turn::Arrive;
    a.idx = np - 1;
    steps.push_back(a);
  }
  cum.assign(np, 0);
  for (int i = 1; i < np; ++i)
    cum[i] = cum[i - 1] + haversine(shape[2 * i - 2], shape[2 * i - 1], shape[2 * i], shape[2 * i + 1]);
  if (!destLat && !destLon) {
    destLat = shape[2 * (np - 1)];
    destLon = shape[2 * (np - 1) + 1];
  }
  if (!distM) distM = (int)lround(cum.back());
  return true;
}

float RouteData::turnAngle(int i) const {
  if (i <= 0 || i >= (int)steps.size() || !valid()) return 0;
  const Step& s = steps[i];
  if (s.turn == Turn::Arrive || s.turn == Turn::Depart) return 0;
  const int np = points(), m = s.idx;
  int a = m, b = m;
  while (a > 0 && cum[m] - cum[a] < 20) --a;
  while (b < np - 1 && cum[b] - cum[m] < 20) ++b;
  if (a == m || b == m) {
    // no geometry on one side: the words decide
    switch (s.turn) {
      case Turn::SlightLeft: return -35;
      case Turn::Left: return -90;
      case Turn::SharpLeft: return -135;
      case Turn::SlightRight: return 35;
      case Turn::Right: return 90;
      case Turn::SharpRight: return 135;
      case Turn::UTurn: return 180;
      default: return 0;
    }
  }
  const double in = bearing(shape[2 * a], shape[2 * a + 1], shape[2 * m], shape[2 * m + 1]);
  const double out = bearing(shape[2 * m], shape[2 * m + 1], shape[2 * b], shape[2 * b + 1]);
  double d = out - in;
  while (d > 180) d -= 360;
  while (d < -180) d += 360;
  return (float)d;
}

void NavState::start(const RouteData* r, uint32_t now) {
  route_ = r && r->valid() ? r : nullptr;
  step_ = route_ && route_->steps.size() > 1 ? 1 : 0;
  along_ = 0;
  off_ = arrived_ = hasFix_ = false;
  last_ = NavFix();
  last_.at = now;
}

float NavState::toTurnM() const {
  if (!route_) return 0;
  const Step& s = route_->steps[step_ < (int)route_->steps.size() ? step_ : (int)route_->steps.size() - 1];
  const float d = (float)route_->cum[s.idx] - along_;
  return d > 0 ? d : 0;
}

float NavState::leftM() const {
  if (!route_) return 0;
  const float d = (float)route_->cum.back() - along_;
  return d > 0 ? d : 0;
}

int NavState::etaS() const {
  if (!route_) return 0;
  float v = 1.35f;
  if (route_->mode == "bike") v = 4.2f;
  else if (route_->mode == "car") v = route_->durS > 0 ? (float)route_->distM / route_->durS : 9.0f;
  return (int)lroundf(leftM() / v);
}

void NavState::position(double& lat, double& lon) const {
  lat = lon = 0;
  if (!route_) return;
  const RouteData& r = *route_;
  const int np = r.points();
  int i = 0;
  while (i < np - 2 && r.cum[i + 1] < along_) ++i;
  const double seg = r.cum[i + 1] - r.cum[i];
  const double t = seg > 0 ? (along_ - r.cum[i]) / seg : 0;
  const double tt = t < 0 ? 0 : t > 1 ? 1 : t;
  lat = r.shape[2 * i] + (r.shape[2 * i + 2] - r.shape[2 * i]) * tt;
  lon = r.shape[2 * i + 1] + (r.shape[2 * i + 3] - r.shape[2 * i + 1]) * tt;
}

void NavState::fix(const NavFix& f) {
  if (!route_) return;
  const RouteData& r = *route_;
  hasFix_ = true;
  last_ = f;
  // snap: nearest point on the shape, on a local plane around the fix (metres)
  const double kx = cos(f.lat * kPi / 180) * 111320.0, ky = 110540.0;
  const int np = r.points();
  double best = 1e18, bestAlong = along_;
  for (int i = 0; i < np - 1; ++i) {
    const double ax = (r.shape[2 * i + 1] - f.lon) * kx, ay = (r.shape[2 * i] - f.lat) * ky;
    const double bx = (r.shape[2 * i + 3] - f.lon) * kx, by = (r.shape[2 * i + 2] - f.lat) * ky;
    const double dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
    double t = L2 > 0 ? -(ax * dx + ay * dy) / L2 : 0;
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    const double px = ax + t * dx, py = ay + t * dy, d2 = px * px + py * py;
    if (d2 < best) {
      best = d2;
      bestAlong = r.cum[i] + t * (r.cum[i + 1] - r.cum[i]);
    }
  }
  const double dist = sqrt(best);
  off_ = dist > 45.0 + f.accM;
  if (off_) return;  // keep the progress; the screen says "off the route" and offers a new one
  // never more than one step backwards: a coarse fix does not undo progress
  const int prevIdx = step_ >= 2 ? r.steps[step_ - 2].idx : 0;
  const double floorAlong = r.cum[prevIdx];
  along_ = (float)(bestAlong < floorAlong ? floorAlong : bestAlong);
  int s = 1;
  while (s < (int)r.steps.size() - 1 && r.cum[r.steps[s].idx] <= along_ + 8.0) ++s;
  step_ = s;
  arrived_ = leftM() < 25.0f + (f.accM > 30 ? 15.0f : 0.0f);
  if (arrived_) step_ = (int)r.steps.size() - 1;
}

void NavState::next() {
  if (!route_) return;
  if (step_ < (int)route_->steps.size() - 1) {
    along_ = (float)route_->cum[route_->steps[step_].idx];
    ++step_;
  } else {
    along_ = (float)route_->cum.back();
    arrived_ = true;
  }
  off_ = false;
}

void NavState::prev() {
  if (!route_ || step_ <= 1) return;
  --step_;
  along_ = step_ >= 2 ? (float)route_->cum[route_->steps[step_ - 1].idx] : 0.0f;
  arrived_ = false;
}

// ---------------------------------------------------------------- painting --

static inline void plot(Canvas& cv, const Rect& clip, int x, int y, Rgb c, float a) {
  if (x < clip.x0 || x >= clip.x1 || y < clip.y0 || y >= clip.y1 || a <= 0.01f) return;
  cv.blend(x, y, c, a > 1 ? 1 : a);
}

void MapPainter::line(Canvas& cv, float x0, float y0, float x1, float y1, float w, Rgb c, float alpha) {
  const Rect& clip = cv.clipRect();
  const float hw = w * 0.5f, reach = hw + 1.0f;
  // reject outside the clip quickly
  if (fmaxf(x0, x1) + reach < clip.x0 || fminf(x0, x1) - reach >= clip.x1 || fmaxf(y0, y1) + reach < clip.y0 ||
      fminf(y0, y1) - reach >= clip.y1)
    return;
  const float dx = x1 - x0, dy = y1 - y0, L = sqrtf(dx * dx + dy * dy);
  if (L < 0.01f) {
    const int xi = (int)floorf(x0), yi = (int)floorf(y0);
    for (int y = yi - (int)reach; y <= yi + (int)reach; ++y)
      for (int x = xi - (int)reach; x <= xi + (int)reach; ++x) {
        const float d = hypotf(x + 0.5f - x0, y + 0.5f - y0);
        plot(cv, clip, x, y, c, (hw + 0.5f - d) * alpha);
      }
    return;
  }
  const float ux = dx / L, uy = dy / L;
  auto cover = [&](int x, int y) {
    const float px = x + 0.5f - x0, py = y + 0.5f - y0;
    float t = px * ux + py * uy;
    t = t < 0 ? 0 : t > L ? L : t;
    const float qx = px - t * ux, qy = py - t * uy;
    const float d = sqrtf(qx * qx + qy * qy);
    const float a = hw + 0.5f - d;
    if (a > 0) plot(cv, clip, x, y, c, (a > 1 ? 1 : a) * alpha);
  };
  if (fabsf(dx) >= fabsf(dy)) {  // walk the columns
    const float xa = fminf(x0, x1) - reach, xb = fmaxf(x0, x1) + reach;
    const int ia = (int)floorf(fmaxf(xa, (float)clip.x0)), ib = (int)ceilf(fminf(xb, (float)clip.x1));
    const float span = reach / fmaxf(fabsf(ux), 0.3f) + 1;
    const float slope = dy / dx;
    for (int x = ia; x < ib; ++x) {
      float xc = x + 0.5f;
      xc = xc < fminf(x0, x1) ? fminf(x0, x1) : xc > fmaxf(x0, x1) ? fmaxf(x0, x1) : xc;
      const float yc = y0 + (xc - x0) * slope;
      const int ya = (int)floorf(yc - span), yb = (int)ceilf(yc + span);
      for (int y = ya < clip.y0 ? clip.y0 : ya; y <= yb && y < clip.y1; ++y) cover(x, y);
    }
  } else {  // walk the rows
    const float ya = fminf(y0, y1) - reach, yb = fmaxf(y0, y1) + reach;
    const int ia = (int)floorf(fmaxf(ya, (float)clip.y0)), ib = (int)ceilf(fminf(yb, (float)clip.y1));
    const float span = reach / fmaxf(fabsf(uy), 0.3f) + 1;
    const float slope = dx / dy;
    for (int y = ia; y < ib; ++y) {
      float yc = y + 0.5f;
      yc = yc < fminf(y0, y1) ? fminf(y0, y1) : yc > fmaxf(y0, y1) ? fmaxf(y0, y1) : yc;
      const float xc = x0 + (yc - y0) * slope;
      const int xa = (int)floorf(xc - span), xb = (int)ceilf(xc + span);
      for (int x = xa < clip.x0 ? clip.x0 : xa; x <= xb && x < clip.x1; ++x) cover(x, y);
    }
  }
  cv.markDirty(Rect{(int)floorf(fminf(x0, x1) - reach), (int)floorf(fminf(y0, y1) - reach),
                    (int)ceilf(fmaxf(x0, x1) + reach) + 1, (int)ceilf(fmaxf(y0, y1) + reach) + 1});
}

void MapPainter::polygon(Canvas& cv, const float* xy, int n, Rgb c, float alpha) {
  if (n < 3) return;
  const Rect& clip = cv.clipRect();
  float bx0 = 1e9f, by0 = 1e9f, bx1 = -1e9f, by1 = -1e9f;
  for (int i = 0; i < n; ++i) {
    bx0 = fminf(bx0, xy[2 * i]);
    bx1 = fmaxf(bx1, xy[2 * i]);
    by0 = fminf(by0, xy[2 * i + 1]);
    by1 = fmaxf(by1, xy[2 * i + 1]);
  }
  const int ry0 = (int)fmaxf(floorf(by0), (float)clip.y0), ry1 = (int)fminf(ceilf(by1), (float)clip.y1);
  const int rx0 = (int)fmaxf(floorf(bx0), (float)clip.x0), rx1 = (int)fminf(ceilf(bx1), (float)clip.x1);
  if (ry0 >= ry1 || rx0 >= rx1) return;
  ++polys;
  const int W = rx1 - rx0;
  scratch_.assign((size_t)W, 0.0f);
  for (int y = ry0; y < ry1; ++y) {
    std::fill(scratch_.begin(), scratch_.end(), 0.0f);
    bool any = false;
    for (int sub = 0; sub < 4; ++sub) {  // 4 sub-scanlines, exact horizontal coverage at the span ends
      const float sy = y + 0.125f + sub * 0.25f;
      xs_.clear();
      for (int i = 0, j = n - 1; i < n; j = i++) {
        const float yi = xy[2 * i + 1], yj = xy[2 * j + 1];
        if ((yi > sy) != (yj > sy)) xs_.push_back(xy[2 * i] + (sy - yi) * (xy[2 * j] - xy[2 * i]) / (yj - yi));
      }
      if (xs_.size() < 2) continue;
      std::sort(xs_.begin(), xs_.end());
      for (size_t k = 0; k + 1 < xs_.size(); k += 2) {
        float a = xs_[k] - rx0, b = xs_[k + 1] - rx0;
        if (b <= 0 || a >= W) continue;
        a = a < 0 ? 0 : a;
        b = b > W ? (float)W : b;
        const int ia = (int)a, ib = (int)b;
        any = true;
        if (ia == ib) {
          scratch_[ia] += (b - a) * 0.25f;
          continue;
        }
        scratch_[ia] += (ia + 1 - a) * 0.25f;
        for (int x = ia + 1; x < ib; ++x) scratch_[x] += 0.25f;
        if (ib < W) scratch_[ib] += (b - ib) * 0.25f;
      }
    }
    if (!any) continue;
    for (int x = 0; x < W; ++x)
      if (scratch_[x] > 0.01f) cv.blend(rx0 + x, y, c, (scratch_[x] > 1 ? 1 : scratch_[x]) * alpha);
  }
  cv.markDirty(Rect{rx0, ry0, rx1, ry1});
}

void MapPainter::paint(Canvas& cv, const MapBundle& b, const MapView& v, const Font* font) {
  segments = polys = 0;
  cv.fillRect(cv.clipRect(), style.land);
  cv.markDirty(cv.clipRect());
  if (b.empty()) return;
  const double f = ldexp(1.0, v.z - b.z) * v.scale;  // bundle px -> screen px
  const float ox = (float)(((double)b.ox * ldexp(1.0, v.z - b.z) - v.cx) * v.scale + v.screenW * 0.5);
  const float oy = (float)(((double)b.oy * ldexp(1.0, v.z - b.z) - v.cy) * v.scale + v.screenH * 0.5);
  const float k = (float)f;
  const float zf = (float)(v.z + log2(v.scale > 0 ? v.scale : 1));
  // road widths grow with the zoom (screen px)
  auto width = [&](uint8_t cls) -> float {
    const float g = zf - 13.0f;
    switch (cls) {
      case RoadMajor: return fmaxf(1.6f, 1.8f + g * 0.9f);
      case RoadMid: return fmaxf(1.2f, 1.2f + g * 0.7f);
      case RoadMinor: return fmaxf(0.9f, 0.6f + g * 0.5f);
      case Path: return 1.0f;
      case Rail: return 1.2f;
      default: return 1.0f;
    }
  };
  auto color = [&](uint8_t cls) -> Rgb {
    switch (cls) {
      case Water: return style.water;
      case Park: return style.park;
      case Building: return style.building;
      case RoadMajor: return style.major;
      case RoadMid: return style.mid;
      case RoadMinor: return style.minor;
      case Path: return style.path;
      case Rail: return style.rail;
      default: return style.label;
    }
  };
  const Rect& clip = cv.clipRect();
  for (const Feature& ft : b.feats) {
    if (ft.kind == Point) continue;
    const int16_t* p = b.pts.data() + 2 * ft.first;
    // bbox reject
    float x0 = 1e9f, y0 = 1e9f, x1 = -1e9f, y1 = -1e9f;
    for (int i = 0; i < ft.count; ++i) {
      const float x = ox + p[2 * i] * k, y = oy + p[2 * i + 1] * k;
      x0 = fminf(x0, x);
      x1 = fmaxf(x1, x);
      y0 = fminf(y0, y);
      y1 = fmaxf(y1, y);
    }
    if (x1 + 4 < clip.x0 || x0 - 4 >= clip.x1 || y1 + 4 < clip.y0 || y0 - 4 >= clip.y1) continue;
    if (ft.kind == Poly) {
      xs_.reserve(64);
      std::vector<float> xy((size_t)ft.count * 2);
      for (int i = 0; i < ft.count; ++i) {
        xy[2 * i] = ox + p[2 * i] * k;
        xy[2 * i + 1] = oy + p[2 * i + 1] * k;
      }
      polygon(cv, xy.data(), ft.count, color(ft.cls), ft.cls == Building ? 0.8f : 1.0f);
      if (ft.cls == Water)  // a faint lit edge, like glass over water
        for (int i = 1; i < ft.count; ++i)
          line(cv, xy[2 * i - 2], xy[2 * i - 1], xy[2 * i], xy[2 * i + 1], 1.0f, Rgb::hex(0x2A4F86), 0.5f);
      continue;
    }
    const float w = width(ft.cls);
    const Rgb c = color(ft.cls);
    const float a = ft.cls == RoadMajor ? 0.95f : ft.cls == RoadMid ? 0.85f : 0.8f;
    for (int i = 1; i < ft.count; ++i) {
      line(cv, ox + p[2 * i - 2] * k, oy + p[2 * i - 1] * k, ox + p[2 * i] * k, oy + p[2 * i + 1] * k, w, c, a);
      ++segments;
    }
  }
  if (!font) return;
  // labels last, never on top of each other
  struct Box {
    float x0, y0, x1, y1;
  };
  std::vector<Box> placed;
  for (const Feature& ft : b.feats) {
    if (ft.kind != Point || !ft.labelLen) continue;
    if (ft.cls == Poi && zf < 16.5f) continue;
    const float x = ox + b.pts[2 * ft.first] * k, y = oy + b.pts[2 * ft.first + 1] * k;
    const std::string s = b.labelOf(ft);
    const float tw = (float)Canvas::measureText(*font, s.c_str());
    const Box bx{x - tw / 2 - 4, y - font->ascent - 2, x + tw / 2 + 4, y + font->descent + 2};
    if (bx.x1 < clip.x0 || bx.x0 >= clip.x1 || bx.y1 < clip.y0 || bx.y0 >= clip.y1) continue;
    bool clash = false;
    for (const Box& o : placed)
      if (!(bx.x1 < o.x0 || bx.x0 > o.x1 || bx.y1 < o.y0 || bx.y0 > o.y1)) clash = true;
    if (clash) continue;
    placed.push_back(bx);
    // a soft dark halo, then the cream words
    for (int dy = -1; dy <= 1; ++dy)
      for (int dx = -1; dx <= 1; ++dx)
        if (dx || dy) cv.drawText(*font, x + dx, (int)lroundf(y) + dy, s.c_str(), style.land, 0.7f, Align::Center);
    cv.drawText(*font, x, (int)lroundf(y), s.c_str(), style.label, ft.cls == Place ? 0.92f : 0.7f, Align::Center);
  }
}

void MapPainter::paintRoute(Canvas& cv, const RouteData& r, const MapView& v, int fromPoint, float alpha) {
  if (!r.valid()) return;
  const int np = r.points();
  float px = 0, py = 0;
  bool have = false;
  for (int i = 0; i < np; ++i) {
    double wx, wy;
    worldPx(r.shape[2 * i], r.shape[2 * i + 1], v.z, wx, wy);
    float sx, sy;
    v.toScreen(wx, wy, sx, sy);
    if (have) {
      const bool done = i <= fromPoint;
      // a glow under the line, then the line (walked part dimmer)
      line(cv, px, py, sx, sy, 9.0f, style.route, (done ? 0.08f : 0.22f) * alpha);
      line(cv, px, py, sx, sy, 4.0f, style.route, (done ? 0.35f : 1.0f) * alpha);
    }
    px = sx;
    py = sy;
    have = true;
  }
  // the destination: a ring + a dot
  double wx, wy;
  worldPx(r.destLat, r.destLon, v.z, wx, wy);
  float sx, sy;
  v.toScreen(wx, wy, sx, sy);
  cv.ring(sx, sy, 9.0f, 3.0f, style.route, alpha, 8, 0.25f);
  cv.ellipse(sx, sy, 3.5f, 3.5f, style.route, alpha);
}

void MapPainter::paintYou(Canvas& cv, float sx, float sy, float accPx, float t) {
  if (accPx > 12) cv.ellipse(sx, sy, accPx, accPx, style.you, 0.12f);
  const float pulse = 0.5f + 0.5f * sinf(t * 3.0f);
  cv.ring(sx, sy, 11.0f + 3.0f * pulse, 2.0f, style.you, 0.35f * (1 - pulse * 0.5f));
  cv.ellipse(sx, sy, 7.0f, 7.0f, pal::kWhite, 1.0f);
  cv.ellipse(sx, sy, 5.0f, 5.0f, style.you, 1.0f, 6, 0.5f);
}

}  // namespace maps
}  // namespace suflet
