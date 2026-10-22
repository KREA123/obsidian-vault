// SoulOS Alive on the device (os/DESIGN-ALIVE.md, approved 2026-10-11): the core the screens stand on.
//
//   the born palette   Palette.h: e1 / e2 from the eye design this SOUL was born with, b1 from its body
//   the eye slot       awake, the eyes glide up and shrink into one slot (k 0.30, centre y 118 px) above every
//                      app screen, drawn over the content on a black disc
//   the lid wipe       opening an app is a blink of the whole glass: two black lids close (80 ms), the app is
//                      behind them, they open again (170 ms, out-back); closing it, the same the other way
//   the home dial      MĂRGĂRITAR pebbles (StoneData.h) orbiting the eyes: turned by a swipe (it coasts to a
//                      detent), by a tap on a neighbour, by the device's tilt; the focused one grows, fills with
//                      its colour, its name rides the arc above it, the eyes look down at it; one short fact
//   speech             the offline lines (Lines.h) in an e1 bubble under the eyes, on the face and the dial
//   reactions          the eye-reaction table (Alive.h §6)
//   Look               Settings › My SOUL: preview the other births, pick the body colour
//
// Every surface is flat (GlassLayer in flat mode): one fill, at most one edge, no blur, no aura.
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "Os.h"
#include "Raster.h"
#include "StoneData.h"

namespace suflet {

using namespace eyes;

namespace {
constexpr float kPi = 3.14159265f;
const Rgb kInk = Rgb::hex(0xFBF4E3);  // brand Warm White: words on black
constexpr int kOrbitDots = 77;

std::string clockOf(uint32_t now) {
  if (!now) return "--:--";
  char b[16];
  snprintf(b, sizeof b, "%02d:%02d", (int)(now % 86400 / 3600), (int)(now % 3600 / 60));
  return b;
}

bool faceOrDial(View v) { return v == View::Home || v == View::Launcher; }
bool overlaps(const Rect& a, const Rect& b) { return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }
}  // namespace

// ------------------------------------------------------------ palette ---

void Os::applyPalette() {
  if (set_.body >= (uint8_t)Body::Count) set_.body = 0;
  pal_ = bornPaletteFor(shownDesign(), (Body)set_.body);
  ++palGen_;  // the dial's sprites are rebuilt in the new colours
  sprites_.clear();
  glass().setFlatColors(pal_.peb, pal_.peb2, pal_.pebe);
  tp_.setAlive(pal_.e1, pal_.e2, pal_.on1);  // the alarm's time picker in the born palette (1.9)
  invalidate();
}

void Os::aliveBegin() {
  if (set_.reduceMotion > 1) set_.reduceMotion = 0;
  for (int& m : wheelMem_) m = -1;
  applyPalette();
  dial_.reset(appCount(), orbit_, false);
  lastDialFocus_ = -1;
  for (PebShown& p : peb_) p = PebShown();
}

void Os::setBody(Body b) {
  if ((unsigned)b >= (unsigned)Body::Count) return;
  set_.body = (uint8_t)b;
  applyPalette();
  pushCmd(OsCmd::SaveSettings);
  face_.react(X_happy, 1.0f);
}

void Os::lookStep(int dir) {
  const int n = kDesignCount;
  const int i = ((shownDesign() + dir) % n + n) % n;
  lookDesign_ = i == birth_.design ? -1 : i;
  face_.setDesign(shownDesign());  // the eyes swap during a blink
  applyPalette();
  lookUntil_ = t_ + 0.5f;
  lookX_ = dir * 0.8f;
  lookY_ = 0.2f;
}

void Os::lookReset() {
  if (lookDesign_ < 0) return;
  lookDesign_ = -1;
  face_.setDesign(birth_.design);
  applyPalette();
  face_.react(X_hello);
}

// ---------------------------------------------------------- the slot ---

bool Os::appScreen(View v) const {
  switch (v) {
    case View::Boot:
    case View::Home:
    case View::Launcher:
    case View::Keyboard:
    case View::Dial:      // the alarm's time picker: the eyes watch the knob
    case View::Talk:      // a face moment: the eyes are the content
    case View::Ringing:
    case View::MySoul:    // Look: the eyes are big, they are what you look at
    case View::Breathe:
    case View::Control:   // pulled down over the eyes, its own layout
      return false;
    case View::Answer: return !thinking_;  // thinking is a face moment
    case View::Games: return apps_.game < 0;  // the menu (a wheel); a game is the eyes' own
    default: return true;
  }
}

void Os::drawSlotDisc(Canvas& cv) {
  if (!appScreen(view_)) return;
  float cx, cy, rx, ry;
  alive::slotDisc((float)g_.w, cx, cy, rx, ry, dens_.card);
  const Rect box{(int)(cx - rx - 2), (int)(cy - ry - 2), (int)(cx + rx + 3), (int)(cy + ry + 3)};
  if (!overlaps(box, cv.clipRect())) return;
  cv.ellipse(cx, cy, rx, ry, pal::kBlack);
}

// ---------------------------------------------------------- reactions ---

void Os::react(alive::Event e) {
  const alive::Reaction& r = alive::reaction(e);
  if (r.blinks) face_.rig().blink(r.blinks);
  if (r.expr >= 0) face_.react(r.expr, r.hold);
  if (r.look) {
    lookUntil_ = t_ + r.lookFor;
    lookX_ = r.lookX;
    lookY_ = r.lookY;
  }
}

void Os::aliveGo(View from, View to) {
  // an app the owner opens or closes (an answer or a pairing code that comes by itself is no app opening)
  auto app = [&](View v) { return appScreen(v) && v != View::Answer && v != View::Pair; };
  const bool open = faceOrDial(from) && app(to), close = app(from) && faceOrDial(to);
  if ((open || close) && set_.booted) {
    react(open ? alive::Event::OpenApp : alive::Event::CloseApp);  // the eyes blink
    if (!reducedMotion()) {
      lids_.start();  // ... and so does the glass
      lidsShown_ = true;
      wipeFrom_ = from;
    }
  }
  if (to == View::Launcher && from != View::Launcher) {
    dial_.reset(appCount(), orbit_, !reducedMotion() && from == View::Home);  // the pebbles spread from the bottom
    dialIdleT_ = 0;
    dialBored_ = false;
    lastDialFocus_ = -1;
    for (PebShown& p : peb_) p = PebShown();
  }
  if (!faceOrDial(to)) speech_.hide();
}

// ------------------------------------------------------------- speech ---

void Os::say(LineTopic t, float secs) {
  if (!faceOrDial(view_) || asleep_ || lidsActive()) return;
  if (view_ == View::Home && peekT_ <= 0) return;  // standby is the eyes alone
  const uint32_t seed = birth_.seed ^ (uint32_t)(uint64_t)(t_ * 1000.0) ^ ((uint32_t)t << 24);
  const int hour = now_ ? localclock::hour(now_) : -1;
  const char* line = pickLine(t, ro(), seed, hour >= 0 && alive::isNight(hour) ? 2 : 0);
  if (!line || !*line) return;
  speech_.say(line, secs, 0.3f);  // the eyes' spring settles first (≈ 0.35 s): the bubble rises under them
}

bool Os::speechRect(Rect& r) const {
  const char* line = speech_.line();
  if (!line || !faceOrDial(view_)) return false;
  const bool dial = view_ == View::Launcher;
  const FaceLayoutT l = layoutFor(view_);
  const float S = (float)g_.w;
  const float top = S * 0.5f + l.cy * S + 0.25f * l.k * S + (dial ? dens_.speechDialGap : dens_.speechGap);
  const float maxW = dial ? dens_.speechDialW : dens_.speechW;
  std::string lines[2];
  const int n = wrapLines(fonts::caption(), line, maxW - dens_.speechPadX, lines, 2);
  float w = 60;
  for (int i = 0; i < n; ++i) w = fmaxf(w, (float)Canvas::measureText(fonts::caption(), lines[i].c_str()) + dens_.speechWPad);
  const float h = n * dens_.speechLine + dens_.speechPadY;
  if (dial && sGlass()) {  // SOUL S: over the eyes (under them it would cover the pebbles beside the focused one)
    const float bottom = S * 0.5f + l.cy * S - 0.25f * l.k * S - 8;
    r = Rect{(int)floorf(S * 0.5f - w * 0.5f), (int)floorf(bottom - h), (int)ceilf(S * 0.5f + w * 0.5f), (int)ceilf(bottom)};
    return true;
  }
  r = Rect{(int)floorf(S * 0.5f - w * 0.5f), (int)floorf(top), (int)ceilf(S * 0.5f + w * 0.5f), (int)ceilf(top + h)};
  return true;
}

void Os::drawSpeech(Canvas& cv) {
  Rect r;
  if (!speechRect(r)) return;
  const float rise = speech_.rise(reducedMotion());
  const float off = (1 - rise) * 14, a = fminf(1.0f, fmaxf(0.0f, rise * 1.4f));
  const Rect shown{r.x0 - 2, r.y0 - 10, r.x1 + 2, r.y1 + (sGlass() && view_ == View::Launcher ? 24 : 16)};  // (S dial: the tail under it)
  if (!overlaps(shown, cv.clipRect()) || a <= 0.01f) return;
  const float x0 = (float)r.x0, y0 = r.y0 + off, x1 = (float)r.x1, y1 = r.y1 + off, cx = (x0 + x1) * 0.5f;
  cv.roundRect(x0, y0, x1, y1, 18, pal_.e1, a);
  {  // the tail: a 45° square under the bubble's top edge, pointing up at the eyes (S's dial: down, from over them)
    Path& p = scratchPath();
    if (p.reserve(1024)) {
      p.clear();
      const bool above = view_ == View::Launcher && sGlass();
      const float ty = above ? y1 - 2 : y0 + 2, d = above ? -1.0f : 1.0f;
      const float xy[8] = {cx - 8, ty, cx, ty - 8 * d, cx + 8, ty, cx, ty + 8 * d};
      p.polygon(xy, 4);
      face_.raster().fill(cv, p, pal_.e1, a);
    }
  }
  std::string lines[2];
  const int n = wrapLines(fonts::caption(), speech_.line(), (view_ == View::Launcher ? dens_.speechDialW : dens_.speechW) - dens_.speechPadX, lines, 2);
  const Font& f = fonts::caption();
  const float lh = dens_.speechLine;
  for (int i = 0; i < n; ++i) {
    const int base = (int)lroundf(y0 + dens_.speechTextY + i * lh + (lh + f.ascent - f.descent) * 0.5f);
    cv.drawText(f, cx, base, lines[i].c_str(), pal_.on1, a, Align::Center);
  }
}

// ---------------------------------------------------------------- lids ---

void Os::renderOverlay(Canvas& cv, const RectList&, RectList& painted) {
  if (!lidsActive()) return;
  const float c = lids_.cover();
  if (c <= 0) return;
  const int W = cv.width(), H = cv.height();
  // per column: the upper lid's lower edge, the lower lid's upper edge (made once, in PSRAM: PsramAlloc.h)
  static float* yu = nullptr;
  static float* yl = nullptr;
  static int cap = 0;
  if (cap < W) {
    psramFree(yu);
    psramFree(yl);
    yu = (float*)psramAlloc(sizeof(float) * W);
    yl = (float*)psramAlloc(sizeof(float) * W);
    cap = yu && yl ? W : 0;
    if (!cap) return;
  }
  float rx, ry, cu, cl;
  alive::LidWipe::geometry((float)W, (float)H, c, rx, ry, cu, cl);
  float uMin = 1e9f, uMax = -1e9f, lMin = 1e9f, lMax = -1e9f;
  for (int x = 0; x < W; ++x) {
    const float dx = (x + 0.5f - W * 0.5f) / rx, k = dx * dx < 1 ? sqrtf(1 - dx * dx) : 0.0f;
    // (above the upper lid's lower edge everything inside the round glass is lid: its top is off the glass)
    yu[x] = k > 0 ? cu + ry * k : -1e9f;
    yl[x] = k > 0 ? cl - ry * k : 1e9f;
    uMin = fminf(uMin, yu[x]);
    uMax = fmaxf(uMax, yu[x]);
    lMin = fminf(lMin, yl[x]);
    lMax = fmaxf(lMax, yl[x]);
  }
  uint16_t* buf = cv.data();
  for (int y = 0; y < H; ++y) {
    uint16_t* row = buf + (size_t)y * W;
    if (y + 1 <= uMin || y >= lMax) {  // the whole row is lid
      memset(row, 0, (size_t)W * 2);
      continue;
    }
    if (y >= uMax && y + 1 <= lMin) continue;  // between the lids: the screen shows
    for (int x = 0; x < W; ++x) {
      const float cov = fminf(1.0f, fmaxf(0.0f, yu[x] - y) + fmaxf(0.0f, y + 1 - yl[x]));
      if (cov >= 0.999f) row[x] = 0;
      else if (cov > 0.004f) row[x] = Rgb::from565(row[x]).scaled(1 - cov).to565();
    }
  }
  if (uMax > 0) painted.add(Rect{0, 0, W, (int)ceilf(fminf(uMax, (float)H))});
  if (lMin < H) painted.add(Rect{0, (int)floorf(fmaxf(lMin, 0.0f)), W, H});
}

// ---------------------------------------------------------------- dial ---

void Os::drawPebble(Canvas& cv, float cx, float cy, float w, float h, Rgb edge, Rgb fill, float alpha) {
  Path& p = scratchPath();
  if (!p.reserve(1024)) return;
  // a point every ~4 px of outline is plenty for the anti-aliasing (the table has 175 for the largest sizes)
  const int stride = (int)fmaxf(1.0f, floorf(stone::kPoints / fmaxf(24.0f, 3.6f * fmaxf(w, h) / 4.0f)));
  auto contour = [&](float ww, float hh) {
    for (int i = 0; i < stone::kPoints; i += stride) p.lineTo(cx + stone::kXY[2 * i] * ww, cy + stone::kXY[2 * i + 1] * hh);
    const int last = stone::kPoints - 1;  // the base's left corner (the flat base closes the outline)
    if (last % stride) p.lineTo(cx + stone::kXY[2 * last] * ww, cy + stone::kXY[2 * last + 1] * hh);
    p.close();
  };
  Raster& ras = face_.raster();
  p.clear();
  contour(w, h);
  ras.fill(cv, p, fill, alpha);  // the stone (black for an outline pebble: it hides the orbit's dots)
  if (edge == fill) return;
  const float t = g_.s(4) * (w / g_.s(alive::Dial::kW));  // the 4 px edge, grown with the pebble (M's pebble: Look too)
  if (w <= 2 * t || h <= 2 * t) return;
  p.clear();
  contour(w, h);
  contour(w - 2 * t, h - 2 * t);
  ras.fill(cv, p, edge, alpha, nullptr, FillRule::EvenOdd);
}

const Os::PebSprite* Os::pebbleSprite(int i, float scale, bool focus, float alpha) {
  // the size in 1/32 steps at rest; while the dial opens (the spread grows every pebble at once) in 1/8 steps,
  // while it turns in 1/16, both rounded down so the sprite never outgrows the pebble's damage box
  int q = (int)lroundf(scale * 32);
  if (dial_.openness() < 0.999f) q = (int)floorf(scale * 8) * 4;
  else if (dial_.moving()) q = (int)floorf(scale * 16) * 2;
  if (q < 4) q = 4;
  const uint32_t base = (palGen_ & 0x3FFFu) << 18 | (uint32_t)(i & 0xFF) << 10 | (focus ? 1u : 0u);
  const uint32_t key = base | (uint32_t)(q & 0x1FF) << 1;
  ++spriteTick_;
  for (PebSprite& sp : sprites_)
    if (sp.key == key) {
      sp.used = spriteTick_;
      return &sp;
    }
  // over this frame's build budget: the nearest smaller one already built stands in for a frame, and a pebble
  // still faint (the opening spread's first frames) waits a frame; both are drawn right on the next frames
  if (spriteBuildsFrame_ >= kSpriteBuildsPerFrame) {
    PebSprite* best = nullptr;
    for (PebSprite& sp : sprites_)
      if ((sp.key & ~(0x1FFu << 1)) == base && sp.q <= q && (!best || sp.q > best->q)) best = &sp;
    if (best || alpha < 0.35f) spriteShort_ = true;
    if (best) {
      best->used = spriteTick_;
      return best;
    }
    if (alpha < 0.35f) return nullptr;
  }
  ++spriteBuildsFrame_;
  ++spriteBuilds_;
  // the slot: a new one, or the least recently used one's (its PSRAM buffers are reused)
  if (sprites_.capacity() < (size_t)kSprites) sprites_.reserve(kSprites);
  size_t slot = sprites_.size();
  if (sprites_.size() >= (size_t)kSprites) {
    slot = 0;
    for (size_t k = 1; k < sprites_.size(); ++k)
      if (sprites_[k].used < sprites_[slot].used) slot = k;
  } else {  // a new slot: its buffers made once at the largest pebble's size, so reusing it never reallocates
    sprites_.emplace_back();
    const size_t most = (size_t)((((int)ceilf(g_.s(dial_.spec().w) * 1.6f) + 6) & ~1) * (((int)ceilf(g_.s(dial_.spec().h) * 1.6f) + 6) & ~1));
    sprites_.back().col.reserve(most);
    sprites_.back().a.reserve(most);
  }
  PebSprite& sp = sprites_[slot];
  // build it: the stone (and its glyph) drawn on black in a small canvas, and the stone's coverage (white)
  const float sc = q / 32.0f, w = g_.s(dial_.spec().w) * sc, h = g_.s(dial_.spec().h) * sc;
  const float gs = dial_.spec().w / alive::Dial::kW;  // the glyph grows with the pebble (1 on M)
  sp.key = key;
  sp.q = q;
  sp.used = spriteTick_;
  sp.w = ((int)ceilf(w) + 6) & ~1;  // even: the stone's centre falls on a pixel corner
  sp.h = ((int)ceilf(h) + 6) & ~1;
  const size_t n = (size_t)sp.w * sp.h;
  sp.col.assign(n, 0);
  spriteCov_.assign(n, 0);
  Canvas tc(sp.w, sp.h, sp.col.data()), mc(sp.w, sp.h, spriteCov_.data());
  const Rgb c = pal_.accent(i);
  const float cx = sp.w * 0.5f, cy = sp.h * 0.5f;
  if (focus) drawPebble(tc, cx, cy, w, h, c, c, 1);  // the focused stone: filled with its colour
  else drawPebble(tc, cx, cy, w, h, c, pal::kBlack, 1);
  const float f = fade_;
  fade_ = 1;  // (drawGlyph applies the screen's fade: the sprite is drawn whole, the blit fades it)
  drawGlyph(tc, appAt(i), cx / g_.k(), cy / g_.k(), 24 * gs * sc, focus ? pal_.ink(i) : c, 1, fmaxf(2.6f, g_.s(4) * gs * sc));
  fade_ = f;
  drawPebble(mc, cx, cy, w, h, pal::kWhite, pal::kWhite, 1);
  sp.a.resize(n);
  for (size_t k = 0; k < n; ++k) sp.a[k] = (uint8_t)(((spriteCov_[k] >> 5) & 0x3F) * 255 / 63);
  return &sp;
}

void Os::drawDialPebble(Canvas& cv, int i, float x, float y, float scale, bool focus, float alpha) {
  const PebSprite* spp = pebbleSprite(i, scale, focus, alpha);
  if (!spp) return;
  const PebSprite& sp = *spp;
  const int x0 = (int)lroundf(x - sp.w * 0.5f), y0 = (int)lroundf(y - sp.h * 0.5f);
  const Rect r = cv.clip(Rect{x0, y0, x0 + sp.w, y0 + sp.h});
  if (r.empty()) return;
  cv.markDirty(r);
  const uint32_t ga = (uint32_t)lroundf(fminf(1.0f, fmaxf(0.0f, alpha)) * 256);
  uint16_t* buf = cv.data();
  const int W = cv.width();
  for (int yy = r.y0; yy < r.y1; ++yy) {
    const uint16_t* sc = sp.col.data() + (size_t)(yy - y0) * sp.w - x0;
    const uint8_t* sa = sp.a.data() + (size_t)(yy - y0) * sp.w - x0;
    uint16_t* d = buf + (size_t)yy * W;
    for (int xx = r.x0; xx < r.x1; ++xx) {
      const uint32_t a = sa[xx];
      if (!a) continue;
      if (a == 255 && ga >= 256) {
        d[xx] = sc[xx];
        continue;
      }
      // premultiplied over: out = src * ga + dst * (1 - a * ga)
      const Rgb s = Rgb::from565(sc[xx]), b = Rgb::from565(d[xx]);
      const uint32_t k = 256 - ((a * ga) >> 8);
      d[xx] = Rgb((uint8_t)((s.r * ga + b.r * k) >> 8), (uint8_t)((s.g * ga + b.g * k) >> 8), (uint8_t)((s.b * ga + b.b * k) >> 8))
                  .to565();
    }
  }
}

void Os::drawDial(Canvas& cv) {
  const Rect clip = cv.clipRect();
  const float cx = g_.cx(), cy = g_.cy();
  // the only track: a dotted e1 orbit (3 px dots, 55 %)
  const alive::DialSpec& sp = dial_.spec();
  const float R = g_.s(sp.r), dr = 1.6f;
  const int dots = sp.dots > 0 ? sp.dots : kOrbitDots;
  for (int i = 0; i < dots; ++i) {
    const float a = i * 2 * kPi / dots, x = cx + R * cosf(a), y = cy + R * sinf(a);
    const Rect d{(int)(x - 4), (int)(y - 4), (int)(x + 5), (int)(y + 5)};
    if (overlaps(d, clip)) cv.ellipse(x, y, dr, dr, pal_.e1, 0.55f * fade_);
  }
  // the pebbles: the focused one last (on top)
  const int n = dial_.count(), f = dial_.focused();
  for (int pass = 0; pass < 2; ++pass)
    for (int i = 0; i < n; ++i) {
      if ((i == f) != (pass == 1)) continue;
      const alive::Dial::Pebble pb = dial_.place(i);
      const float a = pb.alpha * fade_;
      if (a < 0.02f) continue;
      const float w = g_.s(sp.w) * pb.scale, h = g_.s(sp.h) * pb.scale;
      const float px = g_.s(pb.x), py = g_.s(pb.y);
      const Rect box{(int)(px - w * 0.5f - 3), (int)(py - h * 0.5f - 3), (int)(px + w * 0.5f + 4), (int)(py + h * 0.5f + 4)};
      if (!overlaps(box, clip)) continue;
      drawDialPebble(cv, i, px, py, pb.scale, pb.focus, a);
    }
  // the name on the arc above the focused pebble, the fact under the eyes (they step aside for speech)
  if (!speech_.showing()) {
    const std::string name = appName(appAt(f));
    cv.drawTextArc(fonts::name(), cx, cy, g_.s(sp.nameR), kPi * 0.5f, name.c_str(), pal_.e1, fade_ * dial_.openness(), true, 0.5f);
    std::string fact = appFact(appAt(f));
    if (Canvas::measureText(fonts::caption(), fact.c_str()) > g_.s(sp.factW)) {
      std::string l[1];
      wrapLines(fonts::caption(), fact, g_.s(sp.factW), l, 1);
      fact = l[0];
    }
    textAt(cv, fonts::caption(), 233, sp.factY, fact, kInk, 0.84f * dial_.openness());
  }
  // (SOUL S: the speech bubble sits over the eyes, where the clock's capsule is: the clock steps aside for it)
  if (!(sGlass() && speech_.showing()))
    rimTop(cv, clockOf(now_) + (previewing() ? (ro() ? " · previzualizare" : " · preview") : ""), kInk, 0.82f);
}

void Os::invalidateDial() {
  // name + fact (the middle band under the eyes, down to the arc)
  const alive::DialSpec& sp = dial_.spec();
  invalidate(Rect{(int)g_.s(sp.dmgX0), (int)g_.s(sp.dmgY0), (int)g_.s(sp.dmgX1), (int)g_.s(sp.dmgY1)});
}

void Os::dialTap(float x, float y) {
  const float px = x / g_.k(), py = y / g_.k();
  const int i = dial_.hit(px, py);
  if (i >= 0) {
    react(alive::Event::Tap);
    if (i == dial_.focused() && !dial_.settling()) openApp(appAt(i));
    else dial_.spinTo(i, true, reducedMotion());  // a neighbour: spin there, then open it
    dialIdleT_ = 0;
    return;
  }
  if (hypotf(px - 233, py - 233) < dial_.spec().tapR) {  // the middle (the eyes, the fact): the focused one
    react(alive::Event::Tap);
    openApp(appAt(dial_.focused()));
  }
}

void Os::dialTouch(const TouchEv& e) {
  const float x = e.x;
  switch (e.e) {
    case Ev::TouchDown:
      dialGrab_ = false;
      dragVx_ = 0;
      lastMoveX_ = x;
      lastMoveT_ = t_;
      dialIdleT_ = 0;
      break;
    case Ev::TouchMove: {
      const float ddx = x - dx0_, ddy = e.y - dy0_;
      if (!dialGrab_ && fabsf(ddx) > g_.s(dens_.dialGrab) && fabsf(ddx) > fabsf(ddy)) {
        dialGrab_ = true;
        dial_.grab();
      }
      if (dialGrab_) {
        dial_.drag(ddx / g_.k());
        const float dt = t_ - lastMoveT_;
        if (dt > 1e-4f) {
          const float v = (x - lastMoveX_) / g_.k() / dt;
          dragVx_ = dragVx_ * 0.4f + v * 0.6f;
          lastMoveX_ = x;
          lastMoveT_ = t_;
        }
      }
      break;
    }
    default: break;
  }
}

// ---------------------------------------------------------------- Look ---

// Look's layout: SOUL M's 1.9.0 numbers; SOUL S (Density.h) has 68 px targets (6.4 mm) for ‹ ›, the five bodies
// (a row across the widest part of the glass) and Back, under smaller eyes
namespace {
struct LookSpec {
  float prevX = 103, nextX = 363, y = 214, tagY = 248, swatchY = 342, backY = 284;
  float arrowW = 60, arrowH = 52, swatchW = 50, swatchH = 52, swatchStep = 52, backH = 48, bodyW = 40, bodyH = 44;
  float swatchX(int i) const { return 233 + (i - 2) * swatchStep; }
};
LookSpec lookSpec(const Density& d) {
  LookSpec l;
  if (d.reference) return l;
  const float t = d.targetDesign();
  l.prevX = 233 - 150, l.nextX = 233 + 150, l.y = 200, l.tagY = 252, l.swatchY = 302, l.backY = 376;
  l.arrowW = l.arrowH = l.swatchW = l.swatchH = l.backH = t;
  l.swatchStep = t + 6;
  l.bodyW = 54, l.bodyH = 60;
  return l;
}
}  // namespace

void Os::lookControls(std::vector<Control>& out) const {  // the round audit: Look's targets, panel px
  const float k = g_.k();
  const LookSpec L = lookSpec(dens_);
  auto add = [&](float cx, float cy, float w, float h, float r, int id) {
    Control c;
    c.r = Rect{(int)lroundf((cx - w * 0.5f) * k), (int)lroundf((cy - h * 0.5f) * k), (int)lroundf((cx + w * 0.5f) * k),
               (int)lroundf((cy + h * 0.5f) * k)};
    c.radius = r * k;
    c.id = id;
    out.push_back(c);
  };
  add(L.prevX, L.y, L.arrowW, L.arrowH, L.arrowH * 0.5f, 3000);
  add(L.nextX, L.y, L.arrowW, L.arrowH, L.arrowH * 0.5f, 3001);
  for (int i = 0; i < (int)Body::Count; ++i) add(L.swatchX(i), L.swatchY, L.swatchW, L.swatchH, 20, 3010 + i);
  if (previewing()) add(233, L.backY, 260, L.backH, L.backH * 0.5f, 3002);
}

bool Os::lookTap(float x, float y) {
  const float px = x / g_.k(), py = y / g_.k();
  const LookSpec L = lookSpec(dens_);
  if (fabsf(py - L.y) <= L.arrowH * 0.5f) {  // 52 x 60 px targets (S: 68 x 68)
    if (fabsf(px - L.prevX) <= L.arrowW * 0.5f) {
      react(alive::Event::Tap);
      lookStep(-1);
      return true;
    }
    if (fabsf(px - L.nextX) <= L.arrowW * 0.5f) {
      react(alive::Event::Tap);
      lookStep(1);
      return true;
    }
  }
  if (fabsf(py - L.swatchY) <= L.swatchH * 0.5f)
    for (int i = 0; i < (int)Body::Count; ++i)
      if (fabsf(px - L.swatchX(i)) <= L.swatchW * 0.5f) {
        react(alive::Event::Tap);
        setBody((Body)i);
        return true;
      }
  if (previewing() && fabsf(py - L.backY) <= L.backH * 0.5f && fabsf(px - 233) <= 130) {  // Back to {name}
    react(alive::Event::Tap);
    lookReset();
    return true;
  }
  return false;
}

void Os::drawLook(Canvas& cv) {
  const bool R = ro();
  const Design& d = kDesigns[shownDesign()];
  const LookSpec L = lookSpec(dens_);
  rimTop(cv, R ? "Privire" : "Look", kInk, 0.9f);
  // ‹ the birth ›
  const Font& nf = fonts::caption();
  for (int side = -1; side <= 1; side += 2) {  // chunky chevrons, 4 px round strokes like the glyphs
    const float x = g_.s(side < 0 ? L.prevX : L.nextX), y = g_.s(L.y), d = g_.s(7 * dens_.ts), t = g_.s(4 * dens_.ts);
    cv.segment(x - side * d * 0.5f, y - d * 1.4f, x + side * d * 0.9f, y, t, pal_.e1, fade_);  // the point outward
    cv.segment(x + side * d * 0.9f, y, x - side * d * 0.5f, y + d * 1.4f, t, pal_.e1, fade_);
  }
  textAt(cv, fonts::body(), 233, L.y, d.name, kInk);
  char b[96];
  snprintf(b, sizeof b, "%s · #%03d · %s", kRarityName[(int)d.rarity], d.num,
           previewing() ? (R ? "PREVIZUALIZARE" : "PREVIEW") : (R ? "AL TĂU" : "YOURS"));
  for (char* c = b; *c; ++c)
    if (*c >= 'a' && *c <= 'z') *c = (char)(*c - 32);
  textAt(cv, fonts::tag(), 233, L.tagY, b, Rgb::hex(kRarityColor[(int)d.rarity]));
  if (previewing()) {  // Back to {its own birth}
    const std::string back = std::string(R ? "Înapoi la " : "Back to ") + kDesigns[birth_.design].name;
    const float tw = (float)Canvas::measureText(nf, back.c_str()) / g_.k();
    pill(cv, 233, L.backY, fminf(tw + 44 * dens_.ts, 300 * dens_.cs), L.backH, back, PillStyle::Mint, nf);
  } else {  // the three palette colours it was born with
    const Rgb chips[3] = {pal_.e1, pal_.e2, pal_.b1};
    const float cw = 14 * dens_.ts, ch = 5 * dens_.ts, step = 34 * dens_.ts;
    for (int i = 0; i < 3; ++i) cv.roundRect(g_.s(233 + (i - 1) * step - cw), g_.s(L.backY - ch), g_.s(233 + (i - 1) * step + cw), g_.s(L.backY + ch), g_.s(ch), chips[i], fade_);
  }
  // the five bodies, drawn as the stone
  for (int i = 0; i < (int)Body::Count; ++i) {
    const Rgb c = Rgb::hex(bodyInfo((Body)i).hex);
    const float x = g_.s(L.swatchX(i)), y = g_.s(L.swatchY), w = g_.s(L.bodyW), h = g_.s(L.bodyH);
    if (i == (int)set_.body) drawPebble(cv, x, y, w + g_.s(10), h + g_.s(10), kInk, pal::kBlack, fade_);
    drawPebble(cv, x, y, w, h, c, c, fade_);
  }
  // (S: Back sits where the rim's words would: the body's name shows when it is not previewing)
  if (!(sGlass() && previewing())) rimBottom(cv, std::string(bodyInfo(body()).name) + (R ? " · corp" : " · body"), kInk, 0.7f);
}

// --------------------------------------------------------------- update ---

void Os::aliveUpdate(float dt) {
  face_.reducedMotion = reducedMotion();
  spriteBuildsFrame_ = 0;
  // the lid wipe: the new screen appears behind the shut lids, then every frame of the opening
  if (lids_.active()) {
    const bool mid = lids_.update(dt);
    if (mid || !lids_.closing()) invalidate();
    if (!lids_.active()) lidsShown_ = false;
  } else {
    lidsShown_ = false;
  }
  // speech: standby is the eyes alone; the bubble belongs to the face and the dial
  if (!faceOrDial(view_) || (view_ == View::Home && peekT_ <= 0) || asleep_) speech_.hide();
  speech_.update(dt);
  {
    Rect r;
    const bool now = speechRect(r);
    if (now) {
      const Rect shown{r.x0 - 2, r.y0 - 10, r.x1 + 2, r.y1 + (sGlass() && view_ == View::Launcher ? 24 : 16)};  // (S dial: the tail under it)
      if (!speechWas_ || speech_.rising()) invalidate(shown);
      if (speechWas_ && (shown.x0 != speechLast_.x0 || shown.y0 != speechLast_.y0 || shown.x1 != speechLast_.x1 ||
                         shown.y1 != speechLast_.y1))
        invalidate(speechLast_);
      speechLast_ = shown;
      if (view_ == View::Launcher && !speechWas_) invalidateDial();  // the fact and the name step aside
      if (view_ == View::Launcher && !speechWas_ && sGlass()) invalidate();  // (S: and the clock)
    } else if (speechWas_) {
      invalidate(speechLast_);
      if (view_ == View::Launcher) invalidateDial();
      if (view_ == View::Launcher && sGlass()) invalidate();  // (S: the clock comes back)
    }
    speechWas_ = now;
  }
  if (view_ != View::Launcher) return;
  // the dial
  if (dial_.count() != appCount()) dial_.reset(appCount(), orbit_, false);
  if (spriteShort_) {  // last frame drew a stand-in sprite somewhere: draw the pebbles again with the right ones
    spriteShort_ = false;
    for (int i = 0; i < dial_.count() && i < (int)AppId::Count; ++i) invalidate(peb_[i].r);
  }
  const eyes::EyeMotion& m = face_.motion();
  // the sideways lean against how SOUL is held (1.9: the absolute gravity spun the dial for as long as SOUL was
  // held at an angle); the sign of the board's X axis: BRINGUP.md §5f
  const float lean = leanX_.value();
  if (m.active() && leanX_.ready() && !down_ && dial_.tilt(lean, t_)) {
    leanX_.stepped(lean > 0 ? 1 : -1);
    dialIdleT_ = 0;
  }
  const int open = dial_.update(dt, reducedMotion());
  orbit_ = dial_.focused();
  // damage: each pebble whose place, size, opacity or focus changed (old and new box)
  for (int i = 0; i < dial_.count() && i < (int)AppId::Count; ++i) {
    const alive::Dial::Pebble pb = dial_.place(i);
    PebShown s;
    if (pb.alpha * fade_ >= 0.02f) {
      const float w = g_.s(dial_.spec().w) * pb.scale * 0.5f + 4, h = g_.s(dial_.spec().h) * pb.scale * 0.5f + 4;
      const float px = g_.s(pb.x), py = g_.s(pb.y);
      s.r = Rect{(int)floorf(px - w), (int)floorf(py - h), (int)ceilf(px + w), (int)ceilf(py + h)};
      s.a = (uint8_t)lroundf(pb.alpha * fade_ * 255);
      s.f = pb.focus;
      s.qx = px;
      s.qy = py;
      s.qs = pb.scale;
    }
    PebShown& o = peb_[i];
    if (s.a != o.a || s.f != o.f || s.qx != o.qx || s.qy != o.qy || s.qs != o.qs) {
      invalidate(o.r);
      invalidate(s.r);
      o = s;
    }
  }
  const bool moving = dial_.moving();
  if (dial_.focused() != lastDialFocus_ || moving != lastDialMoving_ || dial_.openness() != lastDialOpen_) invalidateDial();
  lastDialOpen_ = dial_.openness();
  lastDialFocus_ = dial_.focused();
  lastDialMoving_ = moving;
  // left alone 11 s: bored
  dialIdleT_ = down_ ? 0 : dialIdleT_ + dt;
  if (dialIdleT_ > alive::Speech::kBoredAfter && !dialBored_) {
    dialBored_ = true;
    say(LineTopic::Bored, 3.2f);
  }
  if (open >= 0) openApp(appAt(open));
}

}  // namespace suflet
