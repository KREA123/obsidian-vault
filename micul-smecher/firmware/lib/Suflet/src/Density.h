// SoulOS Alive · the density layer (firmware/SOUL-S.md): one design, two glasses.
//
// SoulOS was drawn on SOUL M's glass: the Waveshare 2.8C, 480 px over a Ø70.13 mm lit disc (6.84 px/mm), every
// layout in "design px" of the web's 466 grid (DisplayGeometry: x 1.03 to the panel). The product is SOUL S
// (decision 2026-10-20): the Waveshare AMOLED-1.75, 466 px over Ø43.76 mm (10.65 px/mm). Scaled by the pixel count
// alone the same screen would be 36 % smaller in the hand: an 18 px tag 1.7 mm tall, a 44 px button 4.1 mm wide.
//
// So the tokens that are about a human (the type floor, a finger) are kept in MILLIMETRES, and the rest is fitted
// to the glass:
//
//   physical   type floor 18 px on M = 2.63 mm -> 28 px on S; secondary words 20 px = 2.92 mm -> 31 px;
//              a touch target 44 px = 6.43 mm -> 68 px on S (dial pebbles, buttons, the wheel's neighbours)
//   type ramp  above the floor the sizes are compressed: s = round(28 * (m / 18) ^ 0.7) -> tag 28, caption 32,
//              body 37, name 40, title 45 (fonts::TypeRamp::S, tools/gen_font_alive.py s); ts = 37 / 27 is the
//              "type scale" every box that holds words grows by (a wheel row, a line pitch, a pebble's padding)
//   fitted     what is about the round glass stays a fraction of it (the safe circle r 221 of 233, the rim);
//              what has to fit is solved from the tokens above (the dial's orbit from its focused pebble, the
//              angle between pebbles from their width, so fewer of them show: 7 on S, 9-11 on M)
//
// Density::forGlass(SOUL M) returns exactly the 1.9.0 numbers (every field's default below): the 2.8C build draws
// pixel-identical frames (tools/perf_bench.py --hashes / --check). Units: design px of the 466 grid unless a name
// says Px (panel px) or Mm.
#pragma once
#include "Alive.h"
#include "Font.h"
#include "Geometry.h"

namespace suflet {

struct Density {
  // ---- the glass ----------------------------------------------------------------------------------------
  float pxPerMm = 480.0f / 70.13f;  // panel px per mm (the lit disc)
  float sigma = 1;                  // design px here per design px on M at the same size in the hand (S: 1.60)
  float ts = 1;                     // the type scale: body here / body on M (S: 37 / 27)
  float cs = 1;                     // the caption scale: caption here / caption on M (S: 32 / 22)
  bool reference = true;            // SOUL M: every token is the 1.9.0 value
  bool emissive = false;            // AMOLED: black is off, a still picture can burn in (BurnIn below)
  fonts::TypeRamp ramp = fonts::TypeRamp::M;
  // ---- the human tokens (panel px; mm in the comments) ---------------------------------------------------
  float typeFloorPx = 18;   // 2.63 mm: tags, the smallest word anywhere
  float secondaryPx = 20;   // 2.92 mm: anything secondary
  float targetPx = 44;      // 6.43 mm: a control's short side
  float designToPanel = 480.0f / 466.0f;  // DisplayGeometry::k()
  float targetDesign() const { return targetPx / designToPanel; }
  float safeR = 228.0f / (480.0f / 466.0f);  // the safe circle (no word or control corner past it), design px
  // ---- the eyes' layouts (Alive.h §1) -----------------------------------------------------------------------
  alive::Slot card = alive::kCard, peek = alive::kPeek, apps = alive::kApps, think = alive::kThink,
              keyboard = alive::kKeyboard;
  // ---- the rim -----------------------------------------------------------------------------------------------
  float rimR = 205;        // the words' middle on the rim (titles, hints, the banner)
  float rimHalf = 16;      // a rim capsule's half thickness
  float rimPad = 30;       // a rim capsule: words + this (both sides)
  float toastHalf = 19, toastPad = 36, toastW = 330;  // the notification banner
  float ringR = 216, ringW = 8;                       // rim rings (the wheel's scroll arc)
  // ---- pills (every button) --------------------------------------------------------------------------------
  float pillMinH = 48, pillPad = 44, pillMaxW = 330;
  // ---- the dial, the wheels ----------------------------------------------------------------------------------
  alive::DialSpec dial;
  alive::WheelSpec wheel;
  // ---- speech (§5) -------------------------------------------------------------------------------------------
  float speechW = 340, speechDialW = 200;  // the bubble's widest
  float speechLine = 25, speechPadY = 14, speechTextY = 7, speechPadX = 24, speechWPad = 26;
  float speechGap = 12, speechDialGap = 4;  // under the eyes
  // ---- the AI's answer: a round pebble under the eyes (§4) ------------------------------------------------------
  struct Answer {
    float cy = 268, rx = 172, ry = 112;  // the pebble
    float srcY = 186, srcW = 230;        // the source line on top
    float textY = 218, bigShift = 6;     // the first line (+ bigShift with the big face)
    float bigLine = 33, line = 26;       // line pitches: name face (short answers), caption face
    float pad = 44, chipW = 230, chip = 26, chipTick = 12, chipX = 9;
    int smallLines = 6;
  } answer;
  // ---- Claude asks (§4): the command on an amber-edged pebble, Allow / Deny, the shortcut line ------------------
  struct Ask {
    float x0 = 92, y0 = 160, x1 = 374, y1 = 256, r = 26;  // the pebble
    float toolY = 186, hintY1 = 222, hintY2 = 214, hintLine = 28, textW = 250;
    float btnY = 322, btnW = 132, btnH = 66, btnDx = 69;  // Allow at 233 - dx, Deny at 233 + dx
    float holdY = 384;                                    // "Hold = yes · 2× = no"
    float tick = 14, tickSize = 15;
  } ask;
  // ---- the wheel's rows (OsScreens.cpp drawWheelRow), the type scale applied ---------------------------------
  float toggleW = 76, toggleH = 48, knobR = 17;
  float valueShare = 0.42f;  // a row's value (on the right) takes at most this share of the row

  // The tokens for a glass. SOUL M (and any glass within 2 % of its density) gets the reference values.
  static Density forGlass(const DisplayGeometry& g);
  // the S ramp's size for an M size (m >= 18): round(floor * (m / 18) ^ 0.7), floor = 18 px on M in mm here
  static int rampPx(float mPx, float floorPx);
  // the glass the design was drawn on
  static const DisplayGeometry& reference_glass() { return displays::kLcd28; }
};

// ---- AMOLED burn-in care (firmware/SOUL-S.md §3) ----------------------------------------------------------
// Standby on SOUL S is the eyes alone on true black: the black costs nothing (the pixels are off), the eyes'
// whites are the only lit pixels and they would sit still for hours. Four things keep them moving or dark:
//   drift       the whole face wanders on a slow Lissajous, ±kDriftPx panel px, periods 7 and 11 min: no pixel
//               is lit in the same place for long (the eyes' saccades and blinks already move the pupils and lids)
//   night       the glow levels of Os::backlight (0.35 at night, 0.06 asleep at night)
//   lights out  asleep for kOffAfterS (night) / kOffAfterDayS (day): the panel goes dark (brightness 0); a touch,
//               a pick-up or a voice wakes it as before (the Brain wakes on any of them)
//   no static   nothing else stays on standby (no clock, no rings: DESIGN-ALIVE §1)
namespace burnin {
constexpr float kDriftPx = 6.0f;
constexpr float kDriftPeriodX = 420.0f, kDriftPeriodY = 660.0f;  // s
constexpr float kOffAfterS = 20 * 60.0f, kOffAfterDayS = 60 * 60.0f;
// the face's offset now (fractions of the glass of side S): 0 on an LCD
inline void drift(double t, float S, bool emissive, float& dx, float& dy) {
  if (!emissive || S <= 0) {
    dx = dy = 0;
    return;
  }
  const double tw = 6.283185307179586;
  // whole pixels: the eyes move one pixel every ~10 s at most, never a sub-pixel repaint in between
  dx = roundf((float)(kDriftPx * sin(tw * t / kDriftPeriodX))) / S;
  dy = roundf((float)(kDriftPx * sin(tw * t / kDriftPeriodY + 1.0))) / S;
}
}  // namespace burnin

}  // namespace suflet
