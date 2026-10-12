// SoulOS Alive: the born palette (os/DESIGN-ALIVE.md §2). Every SOUL's OS takes its colours from the eye design
// it was born with (EyeTables.h kDesigns, chosen from the chip id) and from its aluminium body colour:
//
//   e1   the eye colour, lifted until its relative luminance is >= 0.30     primary fills, the focused pebble
//   e2   the most colourful pupil (or, when the pupils are near-black / grey or clash with e1, e1's opposite
//        hue), lifted to >= 0.17                                             every 2nd dial pebble, checks
//   b1   the body colour lifted to >= 0.20                                  every 3rd dial pebble
//   on1 / on2 / onb   the ink on a filled accent (near-black on light colours, Warm White on dark ones)
//   peb / peb2 / pebe   e1 mixed into black at 14 / 23 / 40 %                surfaces, pressed, 3 px edges
//
// A line-by-line port of bornPalette() in os/index.html (the same doubles, the same rounding), checked against
// the web for all 120 designs x 5 bodies (test/test_suflet/palette_fixture.h, tools/gen_palette_fixture.js).
// Computed once at birth and whenever the body or the previewed birth changes; never per frame.
#pragma once
#include <stdint.h>

#include "Color.h"

namespace suflet {

// the five aluminium bodies (brand/logo/README.md, aluminium sRGB), in the order of the Look swatches
enum class Body : uint8_t { Silver, Graphite, Midnight, Ember, Champagne, Count };
struct BodyInfo {
  const char* name;
  uint32_t hex;
};
const BodyInfo& bodyInfo(Body b);

struct BornPalette {
  Rgb e1, e2, b1, b0;    // b0 = the raw body colour (the Look swatch)
  Rgb on1, on2, onb;     // ink on e1 / e2 / b1
  Rgb peb, peb2, pebe;   // surfaces
  // the dial's three pebble colours, in turn (e1, e2, b1) and the ink on each
  Rgb accent(int i) const { return i % 3 == 0 ? e1 : i % 3 == 1 ? e2 : b1; }
  Rgb ink(int i) const { return i % 3 == 0 ? on1 : i % 3 == 1 ? on2 : onb; }
};

// eye colour + the two pupil colours (EyeTables.h Design::white / pupilL / pupilR) + the body
BornPalette bornPalette(uint32_t eyeWhite, uint32_t pupilL, uint32_t pupilR, Body body);
BornPalette bornPaletteFor(int design, Body body);  // kDesigns[design]

namespace palette {  // the colour maths, exposed for the tests
struct Hsl {
  double h, s, l;
};
double luminance(const double c[3]);           // WCAG relative luminance of 0..255 sRGB
Hsl toHsl(const double c[3]);
void fromHsl(double h, double s, double l, double out[3]);  // 0..255, not rounded
void lift(const double c[3], double minLum, double out[3]);  // raise HSL lightness until luminance >= minLum
Rgb round(const double c[3]);
}  // namespace palette

}  // namespace suflet
