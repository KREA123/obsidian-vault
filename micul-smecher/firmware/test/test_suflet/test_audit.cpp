// SoulOS Alive · the round audit on the device (os/DESIGN-ALIVE.md §9; the web's os/tests/alive-audit.mjs).
// Every screen in sim/alive_states.h (the web audit's states + the device's own), drawn by the real Os on EACH
// glass (SOUL M: the 2.8C, 480 px over Ø70.13 mm; SOUL S: the AMOLED-1.75, 466 px over Ø43.76 mm), measured from
// what was drawn: every glyph (Canvas::probe) and every control (Os::controls) and the eyes' own pixels. The floors
// are millimetres, the same on both glasses (Density.h): type 2.63 mm (18 px on M, 28 on S), secondary words
// 2.92 mm (20 / 31 px), targets 6.43 mm (44 / 68 px), the safe circle 0.95 of the lit disc (r 228 / 221). It fails if:
//   cut     any visible glyph corner or control corner (a rounded corner at its 45° point) is past the safe circle
//   type    any visible glyph is below the type floor (and anything under 80 % opacity below the secondary floor)
//   target  any control is under the target on its short side (a keyboard key: under 5 mm, its pitch)
//   rim     a word on the rim touches a word or a control of the screen
//   eyes    the eyes' drawn pixels touch a control or a word, or leave the safe circle (the eye slot)
//   contrast (1.9) a glyph whose colour, at its opacity, stands out from what is drawn under it by less than
//           2:1 (WCAG luminance ratio) over most of its box: a word on a colour of its own lightness (the 1.8
//           time picker's pale blue "6" and "18" on its blue ring). Measured at the glyph's opacity but never
//           below 75 %: fading is the design's own de-emphasis (a wheel's neighbours at half strength, the digit
//           not being set at 34 %), a word painted on its own colour is not
// And (the S screens step, 2026-10-20: what the first S stills showed and the checks above did not see):
//   words   two lines of words touch (glyph boxes of different lines overlap by more than 1 px)
//   overlap two controls overlap without one holding the other (two pills drawn over each other)
//   spill   a word straddles a control's edge (a label longer than its pill, a line running into a button)
//   trunc   a line cut to almost nothing: "…" after fewer than 3 characters ("W…", "T…"); and (2026-10-22) a
//           number or a unit cut by "…" ("↑2…" for ↑24°, "↓…", "12 k…")
// Plus the wheels (§4) and Claude's ask (two 68 px buttons, the "Hold = yes · 2× = no" line at >= 22 px).
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <unity.h>

#include <algorithm>
#include <string>
#include <vector>

#include "../../sim/alive_states.h"

using namespace suflet;

namespace {

struct Quad {
  float p[8];
  int px;
  float a;
  bool arc;
  Rgb c;
  uint32_t cp;  // the code point
  int run;      // the line of words it belongs to (one drawText / drawTextArc call)
  float minX() const { return std::min(std::min(p[0], p[2]), std::min(p[4], p[6])); }
  float maxX() const { return std::max(std::max(p[0], p[2]), std::max(p[4], p[6])); }
  float minY() const { return std::min(std::min(p[1], p[3]), std::min(p[5], p[7])); }
  float maxY() const { return std::max(std::max(p[1], p[3]), std::max(p[5], p[7])); }
};

struct Probe : TextProbe {
  std::vector<Quad> q;
  void glyph(const Font& f, const float* quad, float alpha, bool arc, Rgb c) override {
    if (alpha < 0.05f) return;  // invisible (fading out): not on the glass
    Quad g;
    for (int i = 0; i < 8; ++i) g.p[i] = quad[i];
    g.px = f.px;
    g.a = alpha;
    g.arc = arc;
    g.c = c;
    g.cp = cp;
    g.run = run;
    q.push_back(g);
  }
};

// a convex quad against an axis-aligned box (separating axes), shrunk by `pad` px (touching = overlapping by more)
bool quadHitsBox(const Quad& g, float x0, float y0, float x1, float y1, float pad = 0.5f) {
  x0 += pad, y0 += pad, x1 -= pad, y1 -= pad;
  if (g.maxX() <= x0 || g.minX() >= x1 || g.maxY() <= y0 || g.minY() >= y1) return false;
  const float bx[4] = {x0, x1, x1, x0}, by[4] = {y0, y0, y1, y1};
  for (int e = 0; e < 4; ++e) {  // the quad's own edges as axes
    const float ex = g.p[(2 * e + 2) % 8] - g.p[2 * e], ey = g.p[(2 * e + 3) % 8] - g.p[2 * e + 1];
    const float nx = -ey, ny = ex;
    float qa = 1e9f, qb = -1e9f, ba = 1e9f, bb = -1e9f;
    for (int k = 0; k < 4; ++k) {
      const float v = g.p[2 * k] * nx + g.p[2 * k + 1] * ny, w = bx[k] * nx + by[k] * ny;
      qa = std::min(qa, v), qb = std::max(qb, v), ba = std::min(ba, w), bb = std::max(bb, w);
    }
    if (qb <= ba || bb <= qa) return false;
  }
  return true;
}

bool quadsHit(const Quad& a, const Quad& b) {  // two glyphs: their boxes (the rim's are small and nearly upright)
  return quadHitsBox(a, b.minX(), b.minY(), b.maxX(), b.maxY(), 1.0f);
}

double lin(double v) {
  v /= 255.0;
  return v <= 0.04045 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4);
}
double luminance(double r, double g, double b) { return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b); }
// the share of a glyph's box where its ink (its colour at its opacity over what is under it) is below 2:1
float lowContrastShare(const Quad& g, const std::vector<uint16_t>& under, int W, int H) {
  const int x0 = std::max(0, (int)floorf(g.minX())), x1 = std::min(W, (int)ceilf(g.maxX()));
  const int y0 = std::max(0, (int)floorf(g.minY())), y1 = std::min(H, (int)ceilf(g.maxY()));
  int n = 0, low = 0;
  for (int y = y0; y < y1; ++y)
    for (int x = x0; x < x1; ++x) {
      const Rgb b = Rgb::from565(under[(size_t)y * W + x]);
      const double a = std::max(g.a, 0.75f);
      const double ir = b.r + (g.c.r - b.r) * a, ig = b.g + (g.c.g - b.g) * a, ib = b.b + (g.c.b - b.b) * a;
      const double l1 = luminance(ir, ig, ib), l2 = luminance(b.r, b.g, b.b);
      const double ratio = (std::max(l1, l2) + 0.05) / (std::min(l1, l2) + 0.05);
      ++n;
      low += ratio < 2.0;
    }
  return n ? (float)low / n : 0.0f;
}

struct Audit {
  std::vector<std::string> fails;
  int glyphs = 0, controls = 0;
};

// the glass audited and its floors, in millimetres (Density.h): SOUL M (480 px: 18 / 20 px words, 44 px targets,
// r 228) or SOUL S (466 px: 28 / 31 px words, 68 px targets, r 221)
constexpr float kFloorMm = 18.0f / (480.0f / 70.13f), kSecondaryMm = 20.0f / (480.0f / 70.13f),
                kTargetMm = 44.0f / (480.0f / 70.13f);  // 2.63 mm, 2.92 mm, 6.43 mm
// a keyboard's key (controls 2000-2999): its pitch, a row of them with no gaps between; >= 5 mm (os/DESIGN-ALIVE.md
// §S: the S keyboard decision; 34 px on M, whose QWERTY keys are 6.6 mm; 53 px on S, whose keys are 5.1 mm)
constexpr float kKeyMm = 5.0f;
struct Glass {
  DisplayGeometry g = displays::kLcd28;
  float floorPx = 18, secondaryPx = 20, targetPx = 44, keyPx = 34, R = 228;
  const char* name = "M";
  static Glass of(const DisplayGeometry& g, const char* name) {
    Glass a;
    a.g = g;
    a.name = name;
    a.floorPx = roundf(kFloorMm * g.pxPerMm());
    a.secondaryPx = floorf(kSecondaryMm * g.pxPerMm() + 0.01f);
    a.targetPx = floorf(kTargetMm * g.pxPerMm() + 0.01f);
    a.keyPx = floorf(kKeyMm * g.pxPerMm());
    a.R = 0.95f * g.w * 0.5f;
    return a;
  }
};

void auditState(const alive_states::State& st, Audit& out, const Glass& gl = Glass()) {
  fonts::setRamp(fonts::TypeRamp::M);  // (Os::begin sets the glass's own)
  alive_states::Rig s(st.booted, -1, gl.g);
  TEST_ASSERT_TRUE_MESSAGE(alive_states::setup(s, st.name), st.name);
  const int W = gl.g.w, H = gl.g.h;
  const float cx = W * 0.5f, cy = H * 0.5f, R = gl.R;
  std::vector<uint16_t> buf((size_t)W * H, 0);
  Canvas cv(W, H, buf.data());
  Probe probe;
  Canvas::probe = &probe;
  s.os.render(cv);
  // what is under the words: the same screen drawn again without them
  std::vector<uint16_t> under((size_t)W * H, 0);
  {
    Canvas uc(W, H, under.data());
    Probe skip;
    Canvas::probe = &skip;
    Canvas::probeOnly = true;
    s.os.render(uc);
    Canvas::probeOnly = false;
  }
  Canvas::probe = nullptr;
  std::vector<Os::Control> cs;
  s.os.controls(cs);
  // the eyes alone: their drawn pixels
  std::fill(buf.begin(), buf.end(), 0);
  s.os.face().renderEyes(cv);
  out.glyphs += (int)probe.q.size();
  out.controls += (int)cs.size();
  char m[256];
  auto fail = [&](const char* what) {
    if (out.fails.size() < 60) out.fails.push_back(std::string(st.name) + ": " + what);
  };
  int cut = 0, small = 0, rim = 0, eyes = 0, tiny = 0, faint = 0;
  for (const Quad& g : probe.q) {
    for (int k = 0; k < 4 && !cut; ++k)
      if (hypotf(g.p[2 * k] - cx, g.p[2 * k + 1] - cy) > R) {
        snprintf(m, sizeof m, "cut: a %d px glyph at (%.0f, %.0f), r %.1f > %.0f", g.px, g.p[2 * k], g.p[2 * k + 1],
                 hypotf(g.p[2 * k] - cx, g.p[2 * k + 1] - cy), R);
        fail(m);
        ++cut;
      }
    if (!faint) {
      const float share = lowContrastShare(g, under, W, H);
      if (share > 0.5f) {
        snprintf(m, sizeof m, "contrast: a %d px glyph at (%.0f, %.0f), #%02X%02X%02X at %.0f%%: under 2:1 over %.0f%% of it", g.px,
                 g.p[0], g.p[1], g.c.r, g.c.g, g.c.b, g.a * 100, share * 100);
        fail(m);
        ++faint;
      }
    }
    if ((g.px < gl.floorPx || (g.a < 0.8f && g.px < gl.secondaryPx)) && !small) {
      snprintf(m, sizeof m, "type: a %d px glyph at %.0f%% (floor %.0f px, %.0f px under 80 %%) at (%.0f, %.0f)", g.px, g.a * 100,
               gl.floorPx, gl.secondaryPx, g.p[0], g.p[1]);
      fail(m);
      ++small;
    }
  }
  for (const Os::Control& c : cs) {
    const float w = (float)c.r.w(), h = (float)c.r.h();
    const float need = c.id >= 2000 && c.id < 3000 ? gl.keyPx : gl.targetPx;
    if (std::min(w, h) < need - 0.5f && !tiny) {
      snprintf(m, sizeof m, "target: control %d is %.0f x %.0f px (< %.0f)", c.id, w, h, need);
      fail(m);
      ++tiny;
    }
    const float k = std::min(c.radius, std::min(w, h) * 0.5f) * 0.2929f;
    const float xs[2] = {c.r.x0 + k, c.r.x1 - k}, ys[2] = {c.r.y0 + k, c.r.y1 - k};
    for (float x : xs)
      for (float y : ys)
        if (hypotf(x - cx, y - cy) > R + 0.5f && !cut) {
          snprintf(m, sizeof m, "cut: control %d corner (%.0f, %.0f) at r %.1f > %.0f", c.id, x, y, hypotf(x - cx, y - cy), R);
          fail(m);
          ++cut;
        }
  }
  // the rim's words never touch the screen's words or controls
  for (const Quad& r : probe.q) {
    if (!r.arc || rim) continue;
    for (const Quad& g : probe.q)
      if (!g.arc && quadsHit(r, g) && !rim) {
        snprintf(m, sizeof m, "rim: a rim glyph at (%.0f, %.0f) touches a word at (%.0f, %.0f)", r.p[0], r.p[1], g.p[0], g.p[1]);
        fail(m);
        ++rim;
      }
    for (const Os::Control& c : cs)
      if (quadHitsBox(r, (float)c.r.x0, (float)c.r.y0, (float)c.r.x1, (float)c.r.y1) && !rim) {
        snprintf(m, sizeof m, "rim: a rim glyph at (%.0f, %.0f) touches control %d", r.p[0], r.p[1], c.id);
        fail(m);
        ++rim;
      }
  }
  // two lines of words never touch (the glyphs of one line may: kerning)
  int words = 0, overlap = 0, spill = 0, trunc = 0;
  for (size_t i = 0; i < probe.q.size() && !words; ++i)
    for (size_t j = i + 1; j < probe.q.size(); ++j) {
      const Quad &a = probe.q[i], &b = probe.q[j];
      if (a.run == b.run || (a.arc && b.arc)) continue;
      if (a.arc || b.arc) continue;  // (the rim check above)
      const float ox = std::min(a.maxX(), b.maxX()) - std::max(a.minX(), b.minX());
      const float oy = std::min(a.maxY(), b.maxY()) - std::max(a.minY(), b.minY());
      if (ox > 1.5f && oy > 1.5f) {
        snprintf(m, sizeof m, "words: a %d px glyph at (%.0f, %.0f) touches a %d px glyph of another line at (%.0f, %.0f)", a.px,
                 a.minX(), a.minY(), b.px, b.minX(), b.minY());
        fail(m);
        ++words;
        break;
      }
    }
  // two controls never overlap, unless one holds the other (a wheel row's ↑ disc)
  for (size_t i = 0; i < cs.size() && !overlap; ++i)
    for (size_t j = i + 1; j < cs.size(); ++j) {
      const Rect &a = cs[i].r, &b = cs[j].r;
      const int ox = std::min(a.x1, b.x1) - std::max(a.x0, b.x0), oy = std::min(a.y1, b.y1) - std::max(a.y0, b.y0);
      if (ox <= 1 || oy <= 1) continue;
      const bool aInB = a.x0 >= b.x0 && a.x1 <= b.x1 && a.y0 >= b.y0 && a.y1 <= b.y1;
      const bool bInA = b.x0 >= a.x0 && b.x1 <= a.x1 && b.y0 >= a.y0 && b.y1 <= a.y1;
      if (aInB || bInA) continue;
      snprintf(m, sizeof m, "overlap: control %d (%d,%d-%d,%d) and control %d (%d,%d-%d,%d)", cs[i].id, a.x0, a.y0, a.x1, a.y1,
               cs[j].id, b.x0, b.y0, b.x1, b.y1);
      fail(m);
      ++overlap;
      break;
    }
  // a word is in a control or out of it, never across its edge
  for (const Quad& g : probe.q) {
    if (g.arc || spill) continue;
    const float x0 = g.minX() + 1, y0 = g.minY() + 1, x1 = g.maxX() - 1, y1 = g.maxY() - 1;
    for (const Os::Control& c : cs) {
      if (c.id >= 1000 && c.id < 2000) continue;  // the dial's pebbles: their names ride the focused one's rim
      const bool touches = x1 > c.r.x0 && x0 < c.r.x1 && y1 > c.r.y0 && y0 < c.r.y1;
      const bool inside = x0 >= c.r.x0 && x1 <= c.r.x1 && y0 >= c.r.y0 && y1 <= c.r.y1;
      if (touches && !inside) {
        snprintf(m, sizeof m, "spill: a %d px glyph (%.0f,%.0f-%.0f,%.0f) across the edge of control %d (%d,%d-%d,%d)", g.px, g.minX(),
                 g.minY(), g.maxX(), g.maxY(), c.id, c.r.x0, c.r.y0, c.r.x1, c.r.y1);
        fail(m);
        ++spill;
        break;
      }
    }
  }
  // "…" after fewer than 3 characters
  for (size_t i = 0; i < probe.q.size() && !trunc; ++i) {
    if (probe.q[i].cp != 0x2026) continue;
    int before = 0;
    for (size_t j = 0; j < i; ++j) before += probe.q[j].run == probe.q[i].run && probe.q[j].cp != ' ';
    if (before < 3) {
      snprintf(m, sizeof m, "trunc: a line cut to %d character(s) + \u2026 at (%.0f, %.0f)", before, probe.q[i].minX(), probe.q[i].minY());
      fail(m);
      ++trunc;
      continue;
    }
    // (the S firmware critic, 2026-10-22) a number or a unit is never what "…" cuts: "↑2…" for ↑24°, "↓…" for the
    // low, "12 k…" for 12 km. The cut word is what stands right before "…"; the one before it decides a unit.
    // the line's glyphs before "…", split into words where a space was (the probe sees no glyph for a space:
    // a gap wider than 0.15 em between two glyphs is one)
    std::vector<std::vector<uint32_t>> toks(1);
    const Quad* last = nullptr;
    for (size_t j = 0; j < i; ++j) {
      const Quad& g = probe.q[j];
      if (g.run != probe.q[i].run) continue;
      if (g.cp == ' ' || (last && g.minX() - last->maxX() > 0.15f * g.px)) {
        if (!toks.back().empty()) toks.emplace_back();
      }
      if (g.cp != ' ') toks.back().push_back(g.cp);
      last = &g;
    }
    if (last && probe.q[i].minX() - last->maxX() > 0.15f * probe.q[i].px && !toks.back().empty()) toks.emplace_back();
    const std::vector<uint32_t> cutTok = toks.back();
    const std::vector<uint32_t> prevTok = toks.size() > 1 ? toks[toks.size() - 2] : std::vector<uint32_t>();
    auto numeric = [](uint32_t c) { return (c >= '0' && c <= '9') || c == 0xB0 || c == '%' || c == 0x2191 || c == 0x2193; };
    bool numCut = false, prevNumber = !prevTok.empty();
    for (uint32_t c : cutTok) numCut |= numeric(c);
    for (uint32_t c : prevTok) prevNumber &= (c >= '0' && c <= '9') || c == '.' || c == ',';
    if (numCut || (prevNumber && cutTok.size() < 3)) {  // a cut number, or a number whose unit was cut ("5.8 M…")
      snprintf(m, sizeof m, "trunc: a number or a unit cut by \u2026 at (%.0f, %.0f)", probe.q[i].minX(), probe.q[i].minY());
      fail(m);
      ++trunc;
    }
  }
  // the eyes' pixels never touch a control or a word (the dial's pebbles orbit them: the dial is the eyes' own)
  for (int y = 0; y < H && !eyes; ++y)
    for (int x = 0; x < W && !eyes; ++x) {
      if (!buf[(size_t)y * W + x]) continue;
      const float px = x + 0.5f, py = y + 0.5f;
      if (hypotf(px - cx, py - cy) > gl.g.w * 0.5f) {  // (the lit disc: the eyes may fill it, never leave it)
        snprintf(m, sizeof m, "eyes: an eye pixel (%d, %d) off the glass", x, y);
        fail(m);
        ++eyes;
        break;
      }
      for (const Os::Control& c : cs)
        if (c.id < 1000 && px > c.r.x0 + 1 && px < c.r.x1 - 1 && py > c.r.y0 + 1 && py < c.r.y1 - 1) {
          snprintf(m, sizeof m, "eyes: an eye pixel (%d, %d) on control %d", x, y, c.id);
          fail(m);
          ++eyes;
          break;
        }
      if (eyes) break;
      for (const Quad& g : probe.q)
        if (px > g.minX() + 1 && px < g.maxX() - 1 && py > g.minY() + 1 && py < g.maxY() - 1) {
          snprintf(m, sizeof m, "eyes: an eye pixel (%d, %d) on a %d px glyph", x, y, g.px);
          fail(m);
          ++eyes;
          break;
        }
    }
}

}  // namespace

// the contrast check catches what the critic saw on the 1.8 time picker (screen-37 of 1.9's first shots: its hour
// labels, cream at 60 %, on its saturated blue ring) and passes the Alive picker (the labels on a black notch
// cut into the 8 px ring, in the born palette)
static int rimLabelsUnreadable(const std::vector<Quad>& q, const std::vector<uint16_t>& under) {
  int bad = 0;
  for (const Quad& g : q)
    if (hypotf((g.minX() + g.maxX()) * 0.5f - 240, (g.minY() + g.maxY()) * 0.5f - 240) > 190)  // on the rim
      bad += lowContrastShare(g, under, 480, 480) > 0.5f;
  return bad;
}

static void test_audit_contrast_catches_the_old_time_picker() {
  std::vector<uint16_t> buf((size_t)480 * 480, 0), under((size_t)480 * 480, 0);
  {  // 1.8 as shot: "6" and "18" (cream, 60 %) on the 40 px blue ring at r 211
    Canvas cv(480, 480, buf.data()), uc(480, 480, under.data());
    for (Canvas* c : {&cv, &uc}) c->ring(240, 240, 211, 40, Rgb::hex(0x6EB4FF));
    Probe probe;
    Canvas::probe = &probe;
    const Font& f = fonts::small();
    cv.drawText(f, 28, 248, "6", pal::kEyeDay, 0.6f, Align::Center);
    cv.drawText(f, 452, 248, "18", pal::kEyeDay, 0.6f, Align::Center);
    Canvas::probe = nullptr;
    TEST_ASSERT_EQUAL_INT(3, rimLabelsUnreadable(probe.q, under));  // the glyphs 6, 1, 8
  }
  // 1.9: the Alive picker, drawn by TimePicker itself
  TimePicker tp;
  tp.setGeometry(displays::kLcd28);  // 480 px
  tp.setAlive(Rgb::hex(0xFFB3E6), Rgb::hex(0x4D64FF), Rgb::hex(0x1A0F18));
  tp.open(7, 0);
  std::fill(buf.begin(), buf.end(), 0);
  std::fill(under.begin(), under.end(), 0);
  Canvas cv(480, 480, buf.data()), uc(480, 480, under.data());
  Probe probe, skip;
  Canvas::probe = &probe;
  tp.render(cv);
  Canvas::probe = &skip;
  Canvas::probeOnly = true;
  tp.render(uc);
  Canvas::probeOnly = false;
  Canvas::probe = nullptr;
  int rim = 0;
  for (const Quad& g : probe.q) rim += hypotf((g.minX() + g.maxX()) * 0.5f - 240, (g.minY() + g.maxY()) * 0.5f - 240) > 190;
  TEST_ASSERT_GREATER_THAN(4, rim);  // 0 6 12 18 and the knob's 07
  TEST_ASSERT_EQUAL_INT(0, rimLabelsUnreadable(probe.q, under));
  for (const Quad& g : probe.q) TEST_ASSERT_TRUE(g.px >= 22);  // Bricolage, nothing under 22 px
}

// every screen on one glass; AUDIT_ALL=1 .pio/build/native/program prints each screen's result
static void auditGlass(const Glass& gl, int minGlyphs) {
  Audit a;
  const bool each = getenv("AUDIT_ALL") != nullptr;
  for (int i = -1; i < alive_states::kStateCount; ++i) {
    static const alive_states::State kStandby = {"standby", "", true};
    const alive_states::State& st = i < 0 ? kStandby : alive_states::kStates[i];
    Audit one;
    auditState(st, one, gl);
    a.glyphs += one.glyphs;
    a.controls += one.controls;
    for (const std::string& f : one.fails) a.fails.push_back(f);
    if (each) printf("  %s %-16s %s\n", gl.name, st.name, one.fails.empty() ? "ok" : "FAIL");
  }
  for (const std::string& f : a.fails) printf("  AUDIT %s %s\n", gl.name, f.c_str());
  printf("  audit %s: %d screens, %d glyphs, %d controls, %d failures (type >= %.0f px, targets >= %.0f px, r %.0f)\n", gl.name,
         alive_states::kStateCount + 1, a.glyphs, a.controls, (int)a.fails.size(), gl.floorPx, gl.targetPx, gl.R);
  TEST_ASSERT_GREATER_THAN(40, alive_states::kStateCount);
  TEST_ASSERT_GREATER_THAN(minGlyphs, a.glyphs);
  TEST_ASSERT_EQUAL_INT(0, (int)a.fails.size());
  fonts::setRamp(fonts::TypeRamp::M);  // (the next tests draw SOUL M)
}

// a board with no speaker and no buzzer (SOUL S until its ES8311 path is proven, SOUL-S.md §4): the Alarms list
// and the ringing screen say so, on both glasses, and still pass the audit
static std::string wordsOn(alive_states::Rig& s) {
  std::vector<uint16_t> buf((size_t)s.W * s.H, 0);
  Canvas cv(s.W, s.H, buf.data());
  Probe probe;
  Canvas::probe = &probe;
  s.os.render(cv);
  Canvas::probe = nullptr;
  std::string out;
  for (const Quad& g : probe.q) {
    char b[4];
    out.append(b, (size_t)utf8::encode(g.cp, b));
  }
  return out;
}

static void test_alarms_say_when_they_are_silent() {
  for (int glass = 0; glass < 2; ++glass) {
    const Glass gl = glass ? Glass::of(displays::kAmoled175, "S") : Glass::of(displays::kLcd28, "M");
    for (const char* name : {"alarms", "alarm-ring"}) {
      const alive_states::State st = {name, "", true};
      for (int silent = 0; silent < 2; ++silent) {
        alive_states::Rig::silentAlarms = silent != 0;
        Audit a;
        auditState(st, a, gl);
        for (const std::string& f : a.fails) printf("  AUDIT %s silent %d %s\n", gl.name, silent, f.c_str());
        TEST_ASSERT_EQUAL_INT(0, (int)a.fails.size());
        alive_states::Rig s(true, -1, gl.g);
        TEST_ASSERT_TRUE(alive_states::setup(s, name));
        const std::string words = wordsOn(s);
        const bool says = words.find("silent") != std::string::npos;
        TEST_ASSERT_EQUAL_MESSAGE(silent != 0, says, name);
      }
    }
  }
  alive_states::Rig::silentAlarms = false;
  fonts::setRamp(fonts::TypeRamp::M);
}

// The grey secondary words on the capsules at night (the S critic, 2026-10-22): cream at ink2 (82 %) and ink3 (66 %)
// on every born palette's capsule (peb, peb2: e1 into black at 14 / 23 %), all 120 designs x 5 bodies, at the
// panel's level by day (1.0) and at night (Os::backlight 0.35). On an emissive glass dimming scales the words and
// the capsule alike; what changes the ratio is the room's light reflected off the glass, added to both. Model
// [estimare, to measure on the board, BRINGUP §S]: 700 cd/m² at 0x51 = 255 (Waveshare), linear in the level;
// reflected light 1 cd/m² at night (a dim room), 10 cd/m² by day. Floors: ink2 (what you must read) >= 4.5:1,
// ink3 (hints) >= 3:1, and ink2 itself >= 50 cd/m² at night.
static void test_secondary_words_on_capsules_at_night() {
  const Rgb cream = Rgb::hex(0xFBF4E3);
  double worstDim = 1e9, worstFaint = 1e9, darkest = 1e9;
  for (int d = 0; d < eyes::kDesignCount; ++d)
    for (int b = 0; b < (int)Body::Count; ++b) {
      const BornPalette p = bornPaletteFor(d, (Body)b);
      for (Rgb bg : {p.peb, p.peb2}) {
        const double lb = luminance(bg.r, bg.g, bg.b);
        for (int night = 0; night < 2; ++night) {
          const double level = night ? 0.35 : 1.0, peak = 700.0 * level, room = night ? 1.0 : 10.0;
          for (float a : {0.82f, 0.66f}) {
            const double ir = bg.r + (cream.r - bg.r) * a, ig = bg.g + (cream.g - bg.g) * a, ib = bg.b + (cream.b - bg.b) * a;
            const double lt = luminance(ir, ig, ib);
            const double ratio = (lt * peak + room) / (lb * peak + room);
            if (a > 0.8f) worstDim = std::min(worstDim, ratio);
            else worstFaint = std::min(worstFaint, ratio);
            if (a > 0.8f && night) darkest = std::min(darkest, lt * peak);
          }
        }
      }
    }
  printf("  secondary words on capsules: ink2 >= %.1f:1, ink3 >= %.1f:1, ink2 at night >= %.0f cd/m2 [estimare]\n", worstDim,
         worstFaint, darkest);
  TEST_ASSERT_TRUE(worstDim >= 4.5);
  TEST_ASSERT_TRUE(worstFaint >= 3.0);
  TEST_ASSERT_TRUE(darkest >= 50.0);
}

// SOUL M, the prototype: the 2.8C at 480 px
static void test_audit_every_screen_on_soul_m() {
  const Glass gl = Glass::of(displays::kLcd28, "M");
  TEST_ASSERT_EQUAL_FLOAT(18, gl.floorPx);
  TEST_ASSERT_EQUAL_FLOAT(20, gl.secondaryPx);
  TEST_ASSERT_EQUAL_FLOAT(44, gl.targetPx);
  TEST_ASSERT_EQUAL_FLOAT(34, gl.keyPx);
  TEST_ASSERT_EQUAL_FLOAT(228, gl.R);
  auditGlass(gl, 2000);
}

// SOUL S, the product (decision 2026-10-20): every screen on the 1.75" AMOLED at the same millimetres
static void test_audit_every_screen_on_soul_s() {
  const Glass gl = Glass::of(displays::kAmoled175, "S");
  TEST_ASSERT_EQUAL_FLOAT(28, gl.floorPx);
  TEST_ASSERT_EQUAL_FLOAT(31, gl.secondaryPx);
  TEST_ASSERT_EQUAL_FLOAT(68, gl.targetPx);
  TEST_ASSERT_EQUAL_FLOAT(53, gl.keyPx);
  TEST_ASSERT_EQUAL_FLOAT(221.35f, gl.R);
  // the floors are the Density layer's (what the screens are laid out with)
  const Density d = Density::forGlass(displays::kAmoled175);
  TEST_ASSERT_EQUAL_FLOAT(roundf(d.typeFloorPx), gl.floorPx);
  TEST_ASSERT_EQUAL_FLOAT(floorf(d.targetPx), gl.targetPx);
  auditGlass(gl, 1500);
}

static void test_wheel_rows_fit_the_circle_and_turn_on_the_spring() {
  alive::Wheel w;
  w.reset(14, 1);
  TEST_ASSERT_EQUAL_INT(1, w.focused());
  const alive::Wheel::Place f = w.place(1), up = w.place(0), dn = w.place(2), off = w.place(5);
  TEST_ASSERT_EQUAL_FLOAT(290, f.y);
  TEST_ASSERT_EQUAL_FLOAT(1, f.scale);
  TEST_ASSERT_EQUAL_FLOAT(0.9f, up.scale);
  TEST_ASSERT_EQUAL_FLOAT(0.5f, dn.alpha);
  TEST_ASSERT_FALSE(off.visible);
  TEST_ASSERT_TRUE(f.h >= 74);
  for (const alive::Wheel::Place& p : {f, up, dn}) {  // every corner of every visible row inside r 212
    const float r = 22 * p.scale * 0.2929f;
    for (int sx = -1; sx <= 1; sx += 2)
      for (int sy = -1; sy <= 1; sy += 2) {
        const float x = 233 + sx * (p.w * 0.5f - r), y = p.y + sy * (p.h * 0.5f - r);
        TEST_ASSERT_TRUE(hypotf(x - 233, y - 233) <= 212.5f);
      }
    TEST_ASSERT_TRUE(p.h * 1.03f >= 44);  // a neighbour is still a 44 px target
  }
  TEST_ASSERT_TRUE(up.y < f.y && f.y < dn.y);
  TEST_ASSERT_EQUAL_INT(0, w.hit(233, up.y));
  TEST_ASSERT_EQUAL_INT(2, w.hit(233, dn.y));
  TEST_ASSERT_EQUAL_INT(-1, w.hit(233, 120));
  // a turn moves on the spring and settles (with a little overshoot), clamped at the ends
  TEST_ASSERT_TRUE(w.turn(1, false));
  TEST_ASSERT_TRUE(w.moving());
  float most = 0;
  for (int i = 0; i < 60; ++i) {
    w.update(1.0f / 30);
    most = std::max(most, w.pos());
  }
  TEST_ASSERT_FALSE(w.moving());
  TEST_ASSERT_EQUAL_FLOAT(2, w.pos());
  TEST_ASSERT_TRUE(most > 2.0f && most < 2.15f);
  TEST_ASSERT_FALSE(w.turnTo(-3, false) && w.focused() != 0);
  TEST_ASSERT_EQUAL_INT(0, w.focused());
  w.turnTo(99, true);  // reduced motion: snaps
  TEST_ASSERT_EQUAL_INT(13, w.focused());
  TEST_ASSERT_FALSE(w.moving());
  // the tilt: past ~17° one row every 0.45 s
  w.reset(5, 2);
  TEST_ASSERT_FALSE(w.tilt(0.1f, 1.0f, true));
  TEST_ASSERT_TRUE(w.tilt(0.4f, 1.0f, true));
  TEST_ASSERT_FALSE(w.tilt(0.4f, 1.2f, true));
  TEST_ASSERT_TRUE(w.tilt(-0.4f, 1.5f, true));
  TEST_ASSERT_EQUAL_INT(2, w.focused());
  w.resize(1);
  TEST_ASSERT_EQUAL_INT(0, w.focused());
}

static void test_wheel_lists_turn_act_and_end_with_new() {
  alive_states::Rig s;
  s.run(1.0f);
  s.os.go(View::Settings);
  s.run(0.8f);
  TEST_ASSERT_TRUE(s.os.wheelView());
  TEST_ASSERT_EQUAL_INT(14, s.os.wheel().count());
  TEST_ASSERT_EQUAL_INT(1, s.os.wheel().focused());  // AI, under My SOUL
  // a drag up turns it (one row per 56 px), no tap, no swipe
  s.swipe(233, 330, 233, 218, 0.6f);
  TEST_ASSERT_EQUAL_INT(View::Settings, s.os.view());
  TEST_ASSERT_EQUAL_INT(3, s.os.wheel().focused());
  // a tap on the neighbour above: the wheel turns there and it acts (Wi-Fi opens)
  const alive::Wheel::Place up = s.os.wheel().place(2);
  s.tap(233, up.y, 0.8f);
  TEST_ASSERT_EQUAL_INT(View::Wifi, s.os.view());
  s.os.back();
  s.run(0.6f);
  TEST_ASSERT_EQUAL_INT(View::Settings, s.os.view());
  TEST_ASSERT_EQUAL_INT(2, s.os.wheel().focused());  // remembered
  // pulling down past the first row is back
  s.os.wheelFocusRow(0);
  s.run(0.2f);
  s.swipe(233, 220, 233, 380, 0.6f);
  TEST_ASSERT_EQUAL_INT(View::Home, s.os.view());
  // "+ New" / "+ City" are the last row
  for (AppId a : {AppId::Alarms, AppId::Notes, AppId::Habits, AppId::WorldClock}) {
    s.os.openApp(a);
    s.run(0.8f);
    TEST_ASSERT_TRUE(s.os.wheelView());
    const int n = s.os.wheel().count();
    s.os.wheelFocusRow(n - 1);
    s.run(0.3f);
    std::vector<Os::Control> cs;
    s.os.controls(cs);
    bool focusRow = false;
    for (const Os::Control& c : cs) focusRow |= c.r.y0 < 299 && c.r.y1 > 299 && c.r.w() > 200;
    TEST_ASSERT_TRUE(focusRow);
    s.os.go(View::Home);
    s.run(0.4f);
  }
  // a tap on "+ New" in Alarms opens the Rim-Dial
  s.os.openApp(AppId::Alarms);
  s.run(0.6f);
  s.tapRow(s.os.wheel().count() - 1, 0.8f);
  TEST_ASSERT_EQUAL_INT(View::Dial, s.os.view());
}

static void test_claude_asks_with_two_big_buttons() {
  alive_states::Rig s;
  TEST_ASSERT_TRUE(alive_states::setup(s, "claude-ask"));
  TEST_ASSERT_EQUAL_INT(View::Claude, s.os.view());
  std::vector<Os::Control> cs;
  s.os.controls(cs);
  int big = 0;
  float allowX = 0, allowY = 0;
  for (const Os::Control& c : cs)
    if (c.r.h() >= 68) {
      ++big;
      if (!allowX) allowX = (c.r.x0 + c.r.x1) * 0.5f, allowY = (c.r.y0 + c.r.y1) * 0.5f;
    }
  TEST_ASSERT_EQUAL_INT(2, big);  // Allow (mint) and Deny (amber-edged), 68 px on the glass
  // the shortcut line: "Hold = yes · 2× = no", at >= 22 px, inside the circle
  std::vector<uint16_t> buf((size_t)480 * 480, 0);
  Canvas cv(480, 480, buf.data());
  Probe probe;
  Canvas::probe = &probe;
  s.os.render(cv);
  Canvas::probe = nullptr;
  int hint = 0;
  for (const Quad& g : probe.q)
    if (!g.arc && g.minY() > s.g.s(370) && g.maxY() < s.g.s(400)) hint += g.px >= 22;
  TEST_ASSERT_GREATER_THAN(10, hint);
  // a tap on Allow: approved (the device sends {"decision":"once"})
  s.cmds.clear();
  s.tap(allowX / s.g.k(), allowY / s.g.k(), 0.3f);
  bool approved = false;
  for (OsCmd c : s.cmds) approved |= c == OsCmd::ClaudeApprove;
  TEST_ASSERT_TRUE(approved);
}

static void test_today_one_widget_and_the_answer_pebble() {
  alive_states::Rig s;
  TEST_ASSERT_TRUE(alive_states::setup(s, "today"));
  TEST_ASSERT_EQUAL_INT(View::Today, s.os.view());
  TEST_ASSERT_EQUAL_INT(1, s.os.apps().card);  // the second widget: one at a time, the next one off the glass
  alive_states::Rig a;
  TEST_ASSERT_TRUE(alive_states::setup(a, "voice-answer"));
  TEST_ASSERT_EQUAL_INT(View::Answer, a.os.view());
  // the answer sits on a round pebble with a mint edge (something was done): sample the edge left and right
  const Rgb mint = Rgb::hex(0xC9F2E4);
  int edge = 0;
  for (int x = 30; x < 70; ++x) {
    const Rgb p = Rgb::from565(a.fb[(size_t)a.g.si(268) * 480 + x]);
    edge += abs(p.r - mint.r) < 24 && abs(p.g - mint.g) < 24 && abs(p.b - mint.b) < 24;
  }
  TEST_ASSERT_GREATER_THAN(0, edge);
}

void runAuditTests() {
  RUN_TEST(test_audit_every_screen_on_soul_m);
  RUN_TEST(test_audit_every_screen_on_soul_s);
  RUN_TEST(test_audit_contrast_catches_the_old_time_picker);
  RUN_TEST(test_alarms_say_when_they_are_silent);
  RUN_TEST(test_secondary_words_on_capsules_at_night);
  RUN_TEST(test_wheel_rows_fit_the_circle_and_turn_on_the_spring);
  RUN_TEST(test_wheel_lists_turn_act_and_end_with_new);
  RUN_TEST(test_claude_asks_with_two_big_buttons);
  RUN_TEST(test_today_one_widget_and_the_answer_pebble);
}
