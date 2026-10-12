// SoulOS Alive, the round-native screens (os/DESIGN-ALIVE.md §4, approved 2026-10-11): the pieces every screen
// is made of, ported from the web prototype (os/index.html: wheelize / wheelPlace / wheelTo, .pill, .tg).
//
//   wheels    every list (Settings, Your AI, Alarms, Notes, Games, Calendar, Habits, World clock, Settings › Apps,
//             Memory) is a wheel: one big focused row at y 290 under the eyes (74 px, a 3 px e1 edge), the row
//             above and the row below at 0.9 and half strength, the rest off the glass; each row as wide as the
//             circle allows at its height, so nothing is cut. A drag turns it (one row per 56 px), so do the
//             crown and a lean of the device; a tap on a neighbour turns it there and acts; pulling down past the
//             first row is back. "+ New" / "+ City" are its last row. A thick e1 arc on the right rim says where
//             you are when there are more than 3 rows.
//   pills     every button: a capsule, ≥ 48 design px tall (≥ 44 device px), e1 filled (primary), mint (done /
//             allow), amber-edged (Claude / careful), outlined (secondary)
//   toggles   78 x 50 device px; rings on the rim 8 px with round caps
//
// Layout in design px of the 466 grid (DisplayGeometry scales to the 480 px glass). Every surface is a flat fill
// with at most one edge: a wheel turning repaints only its band.
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "Os.h"
#include "Raster.h"

namespace suflet {

using namespace eyes;

namespace {
const Rgb kInk = Rgb::hex(0xFBF4E3), kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4), kIce = Rgb::hex(0x9FC6FF);
const Rgb kOnMint = Rgb::hex(0x06231B), kOnAmber = Rgb::hex(0x2A1700);
constexpr float kPi = 3.14159265f;
constexpr uint8_t kWheelItem = 9;  // Item::font of a wheel row's hit box (drawn by drawWheel, not drawItems)

std::string fitText(const Font& f, const std::string& s, float maxW) {
  if (maxW <= 0) return "";
  if (Canvas::measureText(f, s.c_str()) <= maxW) return s;
  std::string out;
  const char* p = s.c_str();
  const char* end = p + s.size();
  while (p < end) {
    const char* q = p;
    utf8::next(q, end);
    if (Canvas::measureText(f, (out + std::string(p, q - p) + "\xE2\x80\xA6").c_str()) > maxW) break;
    out.append(p, q - p);
    p = q;
  }
  return out + "\xE2\x80\xA6";
}
}  // namespace

// ------------------------------------------------------------- pieces ---

void Os::pebRect(Canvas& cv, float x0, float y0, float x1, float y1, float r, Rgb fill, Rgb edge, float edgeW, float alpha) {
  const float a = alpha * fade_;
  if (a <= 0.004f) return;
  const float X0 = g_.s(x0), Y0 = g_.s(y0), X1 = g_.s(x1), Y1 = g_.s(y1), R = g_.s(r);
  if (edgeW > 0) {
    const float e = g_.s(edgeW);
    cv.roundRect(X0, Y0, X1, Y1, R, edge, a);
    cv.roundRect(X0 + e, Y0 + e, X1 - e, Y1 - e, R > e ? R - e : 0, fill, a);
  } else {
    cv.roundRect(X0, Y0, X1, Y1, R, fill, a);
  }
  // the only nod to the real glass: a 2 px specular highlight along the top edge
  const float rr = fminf(R, fminf((X1 - X0) * 0.5f, (Y1 - Y0) * 0.5f));
  if (X1 - X0 > 2 * rr + 8) cv.roundRect(X0 + rr, Y0 + 1, X1 - rr, Y0 + 3, 1, pal::kWhite, 0.075f * a);
}

void Os::pill(Canvas& cv, float cx, float cy, float w, float h, const std::string& label, PillStyle st, const Font& f,
              float alpha, bool pressed) {
  Rgb fill = pal_.e1, edge = pal_.e1, ink = pal_.on1;
  float ew = 0;
  switch (st) {
    case PillStyle::Primary: break;
    case PillStyle::Mint: fill = kMint, ink = kOnMint; break;
    case PillStyle::Amber: fill = pal_.peb2, edge = kAmber, ew = 4, ink = kInk; break;
    case PillStyle::Outline: fill = pal_.peb2, edge = pal_.e1, ew = 3, ink = kInk; break;
    case PillStyle::Ghost: fill = pal_.peb, ink = kInk; break;
  }
  if (pressed) fill = fill.scaled(0.72f);
  pebRect(cv, cx - w * 0.5f, cy - h * 0.5f, cx + w * 0.5f, cy + h * 0.5f, h * 0.5f, fill, edge, ew, alpha);
  if (!label.empty()) textAt(cv, f, cx, cy, fitText(f, label, g_.s(w - 28)), ink, alpha);
}

Os::PillStyle Os::pillOf(const Item& it) const {
  if (it.color == kMint) return PillStyle::Mint;
  if (it.color == kAmber) return PillStyle::Amber;
  if (it.alpha < 0.9f) return PillStyle::Outline;
  return PillStyle::Primary;
}

void Os::toggleAt(Canvas& cv, float cx, float cy, bool on, float alpha) {
  // 76 x 48 design px (78 x 50 on the glass): the track, the knob
  const float w = 76, h = 48;
  pebRect(cv, cx - w * 0.5f, cy - h * 0.5f, cx + w * 0.5f, cy + h * 0.5f, h * 0.5f, on ? pal_.e1 : pal_.peb2, pal_.pebe,
          on ? 0 : 3, alpha);
  const float kx = on ? cx + w * 0.5f - h * 0.5f : cx - w * 0.5f + h * 0.5f;
  cv.ellipse(g_.s(kx), g_.s(cy), g_.s(17), g_.s(17), on ? pal_.on1 : kInk.scaled(0.55f), alpha * fade_);
}

void Os::rimRing(Canvas& cv, float r, float a0, float a1, Rgb c, float alpha, float w) {
  if (a1 - a0 < 3.0f) {  // a short arc (the wheel's scroll arc, a dial): a stroked polygon over its own box only
    const float R = g_.s(r), cx = g_.cx(), cy = g_.cy(), h = g_.s(w) * 0.5f + 2;
    float bx0 = 1e9f, by0 = 1e9f, bx1 = -1e9f, by1 = -1e9f;
    for (int i = 0; i <= 8; ++i) {
      const float a = a0 + (a1 - a0) * i / 8;
      bx0 = fminf(bx0, cx + R * cosf(a)), bx1 = fmaxf(bx1, cx + R * cosf(a));
      by0 = fminf(by0, cy + R * sinf(a)), by1 = fmaxf(by1, cy + R * sinf(a));
    }
    const Rect box{(int)(bx0 - h), (int)(by0 - h), (int)(bx1 + h) + 1, (int)(by1 + h) + 1};
    const Rect& cl = cv.clipRect();
    if (box.x1 <= cl.x0 || box.x0 >= cl.x1 || box.y1 <= cl.y0 || box.y0 >= cl.y1) return;
    Path& p = scratchPath();
    if (!p.reserve(1024)) return;
    p.clear();
    p.strokeArc(cx, cy, R, a0, a1, g_.s(w));
    face_.raster().fill(cv, p, c, alpha * fade_);
    return;
  }
  face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(r), g_.s(w), c, alpha * fade_, a0, a1);
}

void Os::checkMark(Canvas& cv, float cx, float cy, float size, Rgb c, float alpha) {
  Path& p = scratchPath();
  if (!p.reserve(256)) return;
  p.clear();
  const float x = g_.s(cx), y = g_.s(cy), k = g_.s(size) * 0.5f;
  const float pts[] = {x - k, y, x - k * 0.25f, y + k * 0.75f, x + k, y - k * 0.8f};
  p.stroke(pts, 3, fmaxf(2.6f, g_.s(size) * 0.17f));
  face_.raster().fill(cv, p, c, alpha * fade_);
}

void Os::plusMark(Canvas& cv, float cx, float cy, float size, Rgb c, float alpha) {
  const float x = g_.s(cx), y = g_.s(cy), k = g_.s(size) * 0.5f, t = fmaxf(2.6f, g_.s(size) * 0.17f);
  cv.segment(x - k, y, x + k, y, t, c, alpha * fade_);
  cv.segment(x, y - k, x, y + k, t, c, alpha * fade_);
}

// a paragraph wrapped into lines of different widths (the answer's round pebble: wider in the middle)
int Os::wrapShaped(const Font& f, const std::string& s, const float* widths, std::string* lines, int maxLines) const {
  int n = 0;
  std::string cur;
  size_t i = 0;
  while (i < s.size() && n < maxLines) {
    size_t j = s.find(' ', i);
    if (j == std::string::npos) j = s.size();
    const std::string word = s.substr(i, j - i);
    const std::string trial = cur.empty() ? word : cur + " " + word;
    if (Canvas::measureText(f, trial.c_str()) <= widths[n] || cur.empty()) {
      cur = trial;
    } else {
      if (n == maxLines - 1) {
        lines[n] = fitText(f, trial + " " + s.substr(j < s.size() ? j + 1 : j), widths[n]);
        return n + 1;
      }
      lines[n++] = cur;
      cur = word;
    }
    i = j + 1;
  }
  if (!cur.empty() && n < maxLines) {
    lines[n] = fitText(f, cur, widths[n]);
    ++n;
  }
  return n;
}

// ------------------------------------------------------------- wheels ---

bool Os::wheelView() const {
  switch (view_) {
    case View::Settings:
    case View::AiMode:
    case View::Alarms:
    case View::Notes:
    case View::Habits:
    case View::WorldClock:
    case View::AppsSettings: return true;
    case View::Games: return apps_.game < 0;
    case View::Calendar: return apps_.agenda.ok && !apps_.agenda.events.empty() && apps_.calSel < 0;
    case View::Memory: return mem_ != nullptr && memSel_ < 0;
    default: return false;
  }
}

void Os::buildWheel(std::vector<WheelRow>& out) const {
  out.clear();
  if (!wheelView()) return;
  if (buildCoreWheel(out)) return;
  if (buildAppsWheel(out)) return;
  buildMemoryWheel(out);
}

int Os::wheelCount() const {
  buildWheel(rows_);
  return (int)rows_.size();
}

float Os::wheelY() const { return alive::Wheel::kY; }

// the row in focus when a wheel opens: the chosen one (Your AI), else the second (the web's min(1, n - 1))
int Os::wheelDefault() const {
  if (view_ == View::Memory && mem_ && mem_->list(memFilter_).empty()) return 0;  // Search, under "I remember nothing"
  buildWheel(rows_);
  for (size_t i = 0; i < rows_.size(); ++i)
    if (rows_[i].kind == RowSel) return (int)i;
  return rows_.size() > 1 ? 1 : 0;
}

void Os::wheelSync() {
  if (wheelFor_ == View::Count) {
    static_assert((int)View::Count < 64, "wheel memory");
  }
  if (!wheelView()) {
    if (wheelFor_ != View::Count) wheelMem_[(int)wheelFor_] = wheel_.focused();
    wheelFor_ = View::Count;
    return;
  }
  const int n = wheelCount();
  if (wheelFor_ != view_) {
    if (wheelFor_ != View::Count) wheelMem_[(int)wheelFor_] = wheel_.focused();
    wheelFor_ = view_;
    const int m = wheelMem_[(int)view_];
    wheel_.reset(n, m >= 0 ? m : wheelDefault());
    wheelShownPos_ = -1;
    invalidate();
    return;
  }
  if (n != wheel_.count()) {
    wheel_.resize(n);
    invalidateWheel();
  }
}

void Os::invalidateWheel() {
  // the wheel's band: every place a row can be while it turns (|d| <= 1.6 rows from the focus) and the scroll arc
  invalidate(g_.rect(0, 128, 466, 452));
}

void Os::wheelUpdate(float dt) {
  wheelSync();
  if (wheelFor_ == View::Count) return;
  const eyes::EyeMotion& m = face_.motion();
  if (m.active() && gravInit_ && !down_ && wheel_.tilt(m.gravY() - gLp_[1], t_, reducedMotion())) react(alive::Event::ListTurn);
  wheel_.update(dt);
  if (wheel_.pos() != wheelShownPos_) {
    invalidateWheel();
    wheelShownPos_ = wheel_.pos();
  }
}

void Os::wheelTurn(int d) {
  wheelSync();
  if (wheelFor_ == View::Count) return;
  if (wheel_.turn(d, reducedMotion())) {
    react(alive::Event::ListTurn);
    lookUntil_ = t_ + 0.6f;
    lookX_ = 0;
    lookY_ = d > 0 ? 0.6f : -0.2f;
  }
}

int Os::wheelRowOf(int id) const {
  if (!wheelView()) return -1;
  buildWheel(rows_);
  for (size_t i = 0; i < rows_.size(); ++i)
    if (rows_[i].id == id || rows_[i].id2 == id) return (int)i;
  return -1;
}

bool Os::wheelReveal(int id) {
  wheelSync();
  const int i = wheelRowOf(id);
  if (i < 0) return false;
  wheel_.turnTo(i, true);
  wheel_.update(0);
  invalidate();
  return true;
}

bool Os::wheelFocusRow(int row) {
  wheelSync();
  if (wheelFor_ == View::Count || row < 0 || row >= wheel_.count()) return false;
  wheel_.turnTo(row, true);
  wheel_.update(0);
  invalidate();
  return true;
}

void Os::wheelItems(std::vector<Item>& out) const {
  if (!wheelView() || wheelFor_ != view_) return;
  std::vector<WheelRow> rows;
  buildWheel(rows);
  const float Y = wheelY();
  for (int i = 0; i < (int)rows.size(); ++i) {
    if (abs(i - wheel_.focused()) > 1) continue;
    const alive::Wheel::Place p = wheel_.place(i, Y);
    if (!p.visible || p.alpha < 0.3f) continue;
    const WheelRow& r = rows[(size_t)i];
    Item it;
    it.font = kWheelItem;
    if (r.id2 >= 0) {  // the row's second control (↑): a 48 px disc on its left, hit first
      it.id = r.id2;
      it.x = 233 - p.w * 0.5f + 10 + 24 * p.scale;
      it.y = p.y;
      it.w = it.h = 48 * p.scale;
      out.push_back(it);
    }
    it.id = r.id;
    it.x = 233;
    it.y = p.y;
    it.w = p.w;
    it.h = p.h;
    out.push_back(it);
  }
}

bool Os::wheelTap(float x, float y) {
  if (!wheelView()) return false;
  wheelSync();
  const float px = x / g_.k(), py = y / g_.k();
  const int row = wheel_.hit(px, py, wheelY());
  if (row < 0) return false;
  buildWheel(rows_);
  if (row >= (int)rows_.size()) return false;
  const WheelRow r = rows_[(size_t)row];
  int id = r.id;
  if (r.id2 >= 0) {
    const int h = hitItem(x, y);
    if (h == r.id2) id = h;
  }
  if (row != wheel_.focused()) {  // a neighbour: the wheel turns there, and it acts
    wheel_.turnTo(row, reducedMotion());
    lookUntil_ = t_ + 0.6f;
    lookX_ = 0;
    lookY_ = row > wheel_.focused() ? 0.6f : -0.2f;
  }
  if (id >= 0) activate(id);
  return true;
}

bool Os::wheelTouch(const TouchEv& e) {
  if (!wheelView()) {
    wheelDragged_ = false;
    return false;
  }
  const float k = g_.k();
  switch (e.e) {
    case Ev::TouchDown:
      wheelDragged_ = false;
      wheelSync();
      wheelGrab_ = wheel_.focused();
      return false;
    case Ev::TouchMove: {
      if (!down_ || holding_) return false;
      const float dx = (e.x - dx0_) / k, dy = (e.y - dy0_) / k;
      if (!wheelDragged_ && fabsf(dy) > 14 && fabsf(dy) > fabsf(dx) * 1.2f) wheelDragged_ = true;
      if (wheelDragged_) {
        const int t = wheelGrab_ + (int)lroundf(-dy / alive::Wheel::kDragPx);
        if (wheel_.turnTo(t, reducedMotion())) {
          react(alive::Event::ListTurn);
          lookUntil_ = t_ + 0.6f;
          lookX_ = 0;
          lookY_ = dy < 0 ? 0.6f : -0.2f;
        }
        holdItem_ = -1;
      }
      return wheelDragged_;
    }
    case Ev::TouchUp: {
      if (!wheelDragged_) return false;
      wheelDragged_ = false;
      down_ = false;
      const float dy = (e.y - dy0_) / k;
      if (wheelGrab_ == 0 && wheel_.focused() == 0 && dy > 100) back();  // pulled down past the first row: back
      return true;
    }
    default: return wheelDragged_;
  }
}

void Os::drawWheelRow(Canvas& cv, const WheelRow& r, const alive::Wheel::Place& p, bool focus) {
  const float s = p.scale, a = p.alpha;
  const float x0 = 233 - p.w * 0.5f, x1 = 233 + p.w * 0.5f, y0 = p.y - p.h * 0.5f, y1 = p.y + p.h * 0.5f;
  const bool sel = r.kind == RowSel;
  const bool pressed = holdItem_ == r.id && r.id >= 0;
  Rgb fill = sel ? pal_.e1 : pressed ? pal_.peb2 : pal_.peb;
  const Rgb ink = sel ? pal_.on1 : kInk;
  pebRect(cv, x0, y0, x1, y1, 22 * s, fill, sel ? pal_.on1 : pal_.e1, focus ? 3 : 0, a);
  const float pad = 22 * s;
  float tx = x0 + pad, rx = x1 - pad;  // the words between tx and rx
  const float ta = a * r.dim;
  // left: the ↑ disc, a glyph, a check
  if (r.id2 >= 0) {
    const float cx = x0 + 10 + 24 * s, R = 22 * s;
    cv.ellipse(g_.s(cx), g_.s(p.y), g_.s(R), g_.s(R), pal_.peb2, a * fade_);
    cv.ring(g_.s(cx), g_.s(p.y), g_.s(R - 1.5f), g_.s(3), pal_.pebe, a * fade_);
    const float k = 8 * s;
    cv.segment(g_.s(cx), g_.s(p.y + k), g_.s(cx), g_.s(p.y - k), g_.s(3), kInk, a * fade_);
    cv.segment(g_.s(cx - k * 0.8f), g_.s(p.y - k * 0.2f), g_.s(cx), g_.s(p.y - k), g_.s(3), kInk, a * fade_);
    cv.segment(g_.s(cx + k * 0.8f), g_.s(p.y - k * 0.2f), g_.s(cx), g_.s(p.y - k), g_.s(3), kInk, a * fade_);
    tx = cx + R + 12;
  }
  if (r.glyph >= 0) {
    drawGlyph(cv, (AppId)r.glyph, tx + 12, p.y, 22, sel ? pal_.on1 : pal_.e1, ta, g_.s(3));
    tx += 34;
  }
  const bool twoLines = !r.sub.empty() || r.dots;
  const float yT = twoLines ? p.y - 11 * s : p.y, yS = p.y + 17 * s;
  if (sel) {  // the chosen one: ✓ in front of it
    checkMark(cv, tx + 9, yT, 15, pal_.on1, a);
    tx += 28;
  }
  if (r.kind == RowCheck) {
    const float cx = tx + 12, cy = twoLines ? yT : p.y;
    cv.ring(g_.s(cx), g_.s(cy), g_.s(11), g_.s(3), r.on ? kMint : pal_.e1, ta * fade_);
    if (r.on) checkMark(cv, cx, cy, 12, kMint, ta);
    tx += 34;
  }
  // right: a toggle, a check (done), or the value
  if (r.kind == RowToggle) {
    toggleAt(cv, rx - 38, p.y, r.on, a);
    rx -= 76 + 12;
  }
  const float rxSub = rx;
  if (r.kind != RowToggle && !r.value.empty()) {
    const Font& vf = r.bigTag ? fonts::name() : fonts::caption();
    const std::string v = fitText(vf, r.value, g_.s(p.w * 0.42f));
    textAt(cv, vf, rx, r.bigTag ? p.y : (twoLines ? yT : p.y), v, sel ? pal_.on1 : r.valueC, ta, Align::Right);
    rx -= (float)Canvas::measureText(vf, v.c_str()) / g_.k() + 12;
  }
  if (r.kind == RowNew) {  // "+ New": its words in the middle, in e1
    textAt(cv, fonts::body(), 233, p.y, r.title, pal_.e1, a);
    return;
  }
  // the tag (a time) in front of the title; the second line starts under the first word
  const float subX = tx;
  if (!r.tag.empty()) {
    const Font& tf = r.bigTag ? fonts::name() : fonts::body();
    textAt(cv, tf, tx, yT, r.tag, ink, ta, Align::Left);
    tx += (float)Canvas::measureText(tf, r.tag.c_str()) / g_.k() + 12;
  }
  if (!r.title.empty()) {
    const std::string t = fitText(fonts::body(), r.title, g_.s(rx - tx));
    textAt(cv, fonts::body(), tx, yT, t, ink, ta, Align::Left);
    if (r.strike) {
      const float w = (float)Canvas::measureText(fonts::body(), t.c_str());
      cv.roundRect(g_.s(tx), g_.s(yT) - 1, g_.s(tx) + w, g_.s(yT) + 1.5f, 1, ink, ta * 0.8f * fade_);
    }
  }
  if (!r.sub.empty())
    textAt(cv, fonts::caption(), subX, yS, fitText(fonts::caption(), r.sub, g_.s((r.bigTag ? rx : rxSub) - subX)), ink, ta * 0.72f, Align::Left);
  if (r.dots) {  // habits: the last 7 days, today last
    for (int k = 0; k < 7; ++k) {
      const bool on = r.dots >> (6 - k) & 1;
      cv.ellipse(g_.s(subX + 5 + k * 15), g_.s(yS), g_.s(4.5f), g_.s(4.5f), on ? kMint : pal_.e1, (on ? 1.0f : 0.35f) * ta * fade_);
    }
  }
}

void Os::drawWheel(Canvas& cv) {
  wheelSync();
  buildWheel(rows_);
  const std::vector<WheelRow> rows = rows_;
  const int n = (int)rows.size(), f = wheel_.focused();
  const float Y = wheelY();
  const Rect clip = cv.clipRect();
  // the neighbours first, the focused row on top (it may overlap them while it turns)
  for (int pass = 0; pass < 2; ++pass)
    for (int i = 0; i < n; ++i) {
      if ((i == f) != (pass == 1)) continue;
      const alive::Wheel::Place p = wheel_.place(i, Y);
      if (!p.visible) continue;
      const Rect box = g_.rect((int)(233 - p.w * 0.5f) - 2, (int)(p.y - p.h * 0.5f) - 2, (int)(233 + p.w * 0.5f) + 3,
                               (int)(p.y + p.h * 0.5f) + 3);
      if (box.x1 <= clip.x0 || box.x0 >= clip.x1 || box.y1 <= clip.y0 || box.y0 >= clip.y1) continue;
      drawWheelRow(cv, rows[(size_t)i], p, i == f);
    }
  if (n > 3) {  // where you are: a thick e1 arc on the right rim
    const float d2r = kPi / 180;
    rimRing(cv, 216, -26 * d2r, 26 * d2r, pal_.peb2, 1, 8);
    const float t = -22 + 44 * (wheel_.pos() / (float)(n - 1));
    rimRing(cv, 216, (t - 4) * d2r, (t + 4) * d2r, pal_.e1, 1, 8);
  }
}

// --------------------------------------------------------- the audit ---

void Os::controls(std::vector<Control>& out) const {
  out.clear();
  buildItems(items_);
  const float k = g_.k();
  for (const Item& it : items_) {
    if (it.id < 0 || it.w <= 0 || it.h <= 0) continue;
    Control c;
    c.id = it.id;
    c.r = Rect{(int)lroundf((it.x - it.w * 0.5f) * k), (int)lroundf((it.y - it.h * 0.5f) * k), (int)lroundf((it.x + it.w * 0.5f) * k),
               (int)lroundf((it.y + it.h * 0.5f) * k)};
    const bool disc = fabsf(it.w - it.h) < 1;
    c.radius = (it.underline || disc ? fminf(it.w, it.h) * 0.5f : it.font == kWheelItem ? 22.0f : 24.0f) * k;
    out.push_back(c);
  }
  if (view_ == View::Launcher) {  // the dial's pebbles
    for (int i = 0; i < dial_.count(); ++i) {
      const alive::Dial::Pebble p = dial_.place(i);
      if (p.alpha < 0.3f) continue;
      const float w = alive::Dial::kW * p.scale * k, h = alive::Dial::kH * p.scale * k;
      Control c;
      c.id = 1000 + i;
      c.r = Rect{(int)lroundf(p.x * k - w * 0.5f), (int)lroundf(p.y * k - h * 0.5f), (int)lroundf(p.x * k + w * 0.5f),
                 (int)lroundf(p.y * k + h * 0.5f)};
      c.radius = w * 0.3f;
      out.push_back(c);
    }
  }
  if (view_ == View::MySoul && page_ == 1) lookControls(out);
  if (view_ == View::Keyboard) {  // every key at its full pitch
    for (int i = 0; i < kb_.keyCount(); ++i) {
      const suflet::Key& kk = kb_.key(i);
      Control c;
      c.id = 2000 + i;
      c.r = Rect{kk.x0, kk.y0, kk.x1, kk.y0 + kb_.rowH()};  // the full pitch (no gaps in the hit test)
      c.radius = 16;  // (drawKey: the cap sits 2 / 3 px inside the pitch with r 12: its corner is further in)
      out.push_back(c);
    }
  }
}

bool Os::controlCenter(int id, float& x, float& y) const {
  buildItems(items_);
  for (const Item& it : items_)
    if (it.id == id && it.w > 0) {
      x = it.x;
      y = it.y;
      return true;
    }
  return false;
}

}  // namespace suflet
