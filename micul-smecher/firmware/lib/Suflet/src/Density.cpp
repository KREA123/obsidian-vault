// The density layer (Density.h): SOUL M's 1.9.0 tokens, and every other glass's solved from millimetres.
#include "Density.h"

#include <math.h>

namespace suflet {

namespace {
// the eyes' drawn height per unit of layout k, as a fraction of the glass (the slot's eyes: 50 px at k 0.30 on 480)
constexpr float kEyeH = 50.0f / (480.0f * 0.30f);
float clampRange(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
}  // namespace

int Density::rampPx(float mPx, float floorPx) { return (int)lroundf(floorPx * powf(mPx / 18.0f, 0.7f)); }

Density Density::forGlass(const DisplayGeometry& g) {
  Density d;
  const DisplayGeometry& m = reference_glass();
  // design px per mm here and on M: the physical scale between the two glasses
  const float physHere = g.pxPerMm() / g.k(), physM = m.pxPerMm() / m.k();
  d.sigma = physHere / physM;
  d.pxPerMm = g.pxPerMm();
  d.designToPanel = g.k();
  d.safeR = 0.95f * DisplayGeometry::kDesignPx * 0.5f;  // 228 of 240 on M: the same fraction of any disc
  d.emissive = g.emissive;
  if (fabsf(d.sigma - 1) < 0.02f) {  // SOUL M: the reference glass, every token as drawn in 1.9.0
    d.sigma = 1;
    d.safeR = 228.0f / g.k();
    return d;
  }
  d.reference = false;
  const float ppmRatio = g.pxPerMm() / m.pxPerMm();  // panel px here per panel px on M, same size in the hand
  // ---- the human tokens: kept in millimetres ----
  d.typeFloorPx = 18 * ppmRatio;  // 2.63 mm
  d.secondaryPx = 20 * ppmRatio;  // 2.92 mm
  d.targetPx = 44 * ppmRatio;     // 6.43 mm
  // ---- the type ramp (the atlases exist for S only: a glass denser than M uses them) ----
  d.ramp = d.sigma > 1.25f && fonts::hasRamp(fonts::TypeRamp::S) ? fonts::TypeRamp::S : fonts::TypeRamp::M;
  if (d.ramp == fonts::TypeRamp::S) {
    const float floorPx = roundf(d.typeFloorPx);
    d.ts = (float)rampPx(27, floorPx) / 27.0f;
    d.cs = (float)rampPx(22, floorPx) / 22.0f;
  }
  const float ts = d.ts, cs = d.cs, k = g.k(), S = DisplayGeometry::kDesignPx, C = S * 0.5f;
  const float tgt = d.targetDesign();
  // caption's and name's half heights in design px (the rim's words are centred on rimR)
  const fonts::TypeRamp was = fonts::ramp();
  fonts::setRamp(d.ramp);
  const float capHalf = (fonts::caption().ascent + fonts::caption().descent) * 0.5f / k;
  const float nameHalf = (fonts::name().ascent + fonts::name().descent) * 0.5f / k;
  fonts::setRamp(was);
  // ---- the rim ----
  d.rimR = floorf(d.safeR - capHalf - 1.5f);
  d.rimHalf = 16 * cs;
  d.rimPad = 30 * cs;
  d.toastHalf = 19 * cs;
  d.toastPad = 36 * cs;
  d.ringW = 8 * ts;
  d.ringR = d.safeR - d.ringW * 0.5f - 1;
  // ---- pills ----
  d.pillMinH = fmaxf(48, tgt);
  d.pillPad = 44 * ts;
  d.pillMaxW = fminf(330 * ts, 400);
  // ---- the eye slot of every app screen: a little bigger than M's k 0.30 (the type grew), right under the
  //      rim capsule ----
  const float rimInner = C - (d.rimR - d.rimHalf);  // the capsule's lowest point at the top (y)
  d.card.k = alive::kCard.k * sqrtf(ts);
  {
    const float h = kEyeH * S * d.card.k, cy = rimInner + 12 + h * 0.5f;  // (+12: wide eyes, the slot disc)
    d.card.cy = (cy - C) / S;
  }
  const float slotBottom = C + d.card.cy * S + kEyeH * S * d.card.k * 0.5f;
  // ---- the keyboard's eyes: smaller, over its one-line field (Keyboard::setDense) ----
  d.keyboard.k = 0.2f;
  d.keyboard.cy = -0.43f;
  // ---- the dial: pebbles at the touch target, the orbit solved from the focused one ----
  alive::DialSpec& dl = d.dial;
  const alive::DialSpec m0;
  dl.w = fmaxf(m0.w, tgt);
  dl.h = dl.w * m0.h / m0.w;
  const float grow = 1 + alive::Dial::kGrow;
  dl.r = d.safeR - 6 - dl.h * grow * 0.5f - 1;
  {  // two neighbours' centres far enough apart for the focused one's half, a pebble's half and a 12 px gap
    const float chord = dl.w * grow * 0.5f + dl.w * 0.5f + 12;
    dl.stepDeg = ceilf(2 * asinf(clampRange(chord / (2 * dl.r), 0.0f, 1.0f)) * 180 / 3.14159265f * 2) / 2;
  }
  {  // they fade out before the top, where the clock capsule is (≈ 220 px wide)
    const float capHalfDeg = 110.0f / d.rimR * 180 / 3.14159265f, pebHalfDeg = dl.w * 0.5f / dl.r * 180 / 3.14159265f;
    dl.fade1 = 180 - capHalfDeg - pebHalfDeg;
    dl.fade0 = dl.fade1 - 26;
  }
  dl.dragPx = m0.dragPx * (dl.r * dl.stepDeg) / (m0.r * m0.stepDeg);  // the pebble follows the finger
  const float focusTop = dl.r + 6 - dl.h * grow * 0.5f;                // the focused pebble's top (from the centre)
  dl.nameR = focusTop - (m0.r + 6 - m0.h * grow * 0.5f - m0.nameR) * ts;
  dl.factY = C + dl.nameR - nameHalf - 10 - capHalf;
  const float inner = dl.r - dl.w * 0.5f - 6, fdy = dl.factY - C;
  dl.factW = fminf(m0.factW, 2 * sqrtf(fmaxf(0, inner * inner - fdy * fdy)));
  dl.tapR = dl.r - dl.w * 0.5f;
  dl.dmgX0 = C - dl.nameR - nameHalf - 4;
  dl.dmgX1 = C + dl.nameR + nameHalf + 4;
  dl.dmgY0 = dl.factY - capHalf - 6;
  dl.dmgY1 = C + dl.nameR + nameHalf + 6;
  dl.dots = (int)lroundf(m0.dots * dl.r / m0.r);
  // the dial's eyes: above the fact, inside the pebbles
  d.apps.k = 0.40f;
  {
    const float h = kEyeH * S * d.apps.k, cy = dl.factY - capHalf - 10 - h * 0.5f;
    d.apps.cy = (cy - C) / S;
  }
  // ---- the wheels: rows for the S type (two lines: body + caption), the neighbours (x 0.9) still a target;
  //      the focused row as high as the slot allows, so the row under it still has a wide chord ----
  alive::WheelSpec& w = d.wheel;
  const alive::WheelSpec w0;
  w.h = fmaxf(w0.h * sqrtf(ts), tgt / w0.sn);
  w.gap = w0.gap * ts;
  w.r = w0.r;
  w.maxW = fminf(w0.maxW * ts, 2 * w.r);
  w.dragPx = w0.dragPx * ts;
  const float step = w.h * 0.5f + w.gap + w.h * w.sn * 0.5f;
  w.y = slotBottom + 10 + w.h * w.sn * 0.5f + step;
  const float reach = step + 0.6f * (w.h * w.sn + w.gap) + w.h * w.sn * 0.5f + 2;
  w.band0 = fmaxf(0, w.y - reach);
  w.band1 = fminf(S, w.y + reach);
  d.toggleW = fmaxf(76 * ts, tgt * 76 / 48);
  d.toggleH = fmaxf(48 * ts, tgt);
  d.knobR = 17 * d.toggleH / 48;
  d.valueShare = 0.5f;
  // ---- speech ----
  d.speechLine = 25 * cs;
  d.speechPadY = 14 * cs;
  d.speechTextY = 7 * cs;
  d.speechPadX = 24 * cs;
  d.speechWPad = 26 * cs;
  d.speechW = fminf(340 * cs, 380);
  d.speechDialW = 224;  // two lines over the eyes, clear of the pebbles at the sides (OsAlive.cpp speechRect)
  d.speechDialGap = 0;
  // ---- the answer pebble: from under the slot to above the bottom rim's words ----
  Answer& a = d.answer;
  const float top = slotBottom + 8, bottom = C + d.rimR - capHalf - 8;
  a.cy = (top + bottom) * 0.5f;
  a.ry = (bottom - top) * 0.5f;
  a.rx = fminf(196, d.safeR - 25);
  a.srcY = top + (186 - 156) * cs;
  a.textY = top + (218 - 156) * ts;
  a.bigShift = 6 * ts;
  a.bigLine = 33 * ts;
  a.line = 26 * cs;
  a.pad = 44 * ts;
  a.srcW = 280;
  a.chipW = 300;
  a.chip = 26 * cs;
  a.chipTick = 12 * ts;
  a.chipX = 9 * ts;
  a.smallLines = 5;
  // ---- Claude asks: packed so the shortcut line still clears the amber ring (r 218) ----
  Ask& q = d.ask;
  // (the words' visual half heights, M's 13.5 / 11 px scaled: a line's ink, not its ascent + descent)
  const float bodyHalf = 13.5f * ts, capInk = 11 * cs;
  q.y0 = slotBottom + 10;
  q.x0 = 64;
  q.x1 = S - 64;
  q.r = 26 * ts;
  q.toolY = q.y0 + capInk + 8;
  q.hintLine = 28 * ts;
  q.hintY2 = q.toolY + capInk + 2 + bodyHalf;
  q.y1 = q.hintY2 + q.hintLine + bodyHalf + 8;
  q.hintY1 = (q.toolY + capInk + q.y1) * 0.5f;
  q.textW = q.x1 - q.x0 - 40;
  q.btnH = fmaxf(66, tgt);
  q.btnW = fminf(132 * ts, 172);
  q.btnDx = q.btnW * 0.5f + 6;
  q.btnY = q.y1 + 12 + q.btnH * 0.5f;
  q.holdY = q.btnY + q.btnH * 0.5f + 8 + capInk;
  q.tick = 14 * ts;
  q.tickSize = 15 * ts;
  return d;
}

}  // namespace suflet
