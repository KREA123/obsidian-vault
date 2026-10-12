#include "Palette.h"

#include <math.h>

#include "EyeTables.h"

namespace suflet {

static const BodyInfo kBodies[(int)Body::Count] = {
    {"Silver", 0xCBCDCF}, {"Graphite", 0x55575B}, {"Midnight", 0x26324C}, {"Ember", 0xD2622C}, {"Champagne", 0xD8C3A2}};

const BodyInfo& bodyInfo(Body b) { return kBodies[(unsigned)b < (unsigned)Body::Count ? (int)b : 0]; }

namespace palette {

static double lin(double v) {
  v /= 255;
  return v <= 0.04045 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4);
}

double luminance(const double c[3]) { return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]); }

Hsl toHsl(const double c[3]) {
  const double r = c[0] / 255, g = c[1] / 255, b = c[2] / 255;
  const double mx = fmax(r, fmax(g, b)), mn = fmin(r, fmin(g, b)), l = (mx + mn) / 2, d = mx - mn;
  if (d == 0) return {0, 0, l};
  const double s = d / (1 - fabs(2 * l - 1));
  double h = mx == r ? fmod((g - b) / d, 6.0) : mx == g ? (b - r) / d + 2 : (r - g) / d + 4;
  return {fmod(h * 60 + 360, 360.0), s, l};
}

void fromHsl(double h, double s, double l, double out[3]) {
  const double c = (1 - fabs(2 * l - 1)) * s, x = c * (1 - fabs(fmod(h / 60, 2.0) - 1)), m = l - c / 2;
  double r, g, b;
  if (h < 60) r = c, g = x, b = 0;
  else if (h < 120) r = x, g = c, b = 0;
  else if (h < 180) r = 0, g = c, b = x;
  else if (h < 240) r = 0, g = x, b = c;
  else if (h < 300) r = x, g = 0, b = c;
  else r = c, g = 0, b = x;
  out[0] = (r + m) * 255;
  out[1] = (g + m) * 255;
  out[2] = (b + m) * 255;
}

void lift(const double c[3], double minLum, double out[3]) {
  Hsl q = toHsl(c);
  out[0] = c[0], out[1] = c[1], out[2] = c[2];
  for (int i = 0; i < 40 && luminance(out) < minLum; ++i) {
    q.l = fmin(0.92, q.l + 0.02);
    if (q.s > 0.12) q.s = fmax(q.s, 0.5);
    fromHsl(q.h, q.s, q.l, out);
  }
}

static uint8_t ch(double v) {  // Math.round(clamp(v, 0, 255))
  v = v < 0 ? 0 : v > 255 ? 255 : v;
  return (uint8_t)floor(v + 0.5);
}

Rgb round(const double c[3]) { return Rgb(ch(c[0]), ch(c[1]), ch(c[2])); }

}  // namespace palette

using namespace palette;

static void unpack(uint32_t v, double c[3]) {
  c[0] = (v >> 16) & 255;
  c[1] = (v >> 8) & 255;
  c[2] = v & 255;
}

static Rgb inkOn(const double c[3]) { return luminance(c) > 0.3 ? Rgb::hex(0x0B0B0C) : Rgb::hex(0xFBF4E3); }

BornPalette bornPalette(uint32_t eyeWhite, uint32_t pupilL, uint32_t pupilR, Body body) {
  double w[3], e1[3], e2[3];
  unpack(eyeWhite, w);
  lift(w, 0.3, e1);
  // the most colourful pupil: saturation x (1 - |lightness - 0.5|); a stable sort keeps L first on a tie
  double pl[3], pr[3];
  unpack(pupilL, pl);
  unpack(pupilR, pr);
  const Hsl hl = toHsl(pl), hr = toHsl(pr);
  const double sl = hl.s * (1 - fabs(hl.l - 0.5)), sr = hr.s * (1 - fabs(hr.l - 0.5));
  const double* best = sr > sl ? pr : pl;
  const double bestS = sr > sl ? sr : sl;
  const double h1 = toHsl(e1).h;
  if (bestS > 0.22) e2[0] = best[0], e2[1] = best[1], e2[2] = best[2];
  else fromHsl(fmod(h1 + 165, 360.0), 0.9, 0.6, e2);
  const double h2 = toHsl(e2).h;
  const double ch1 = (fmax(e1[0], fmax(e1[1], e1[2])) - fmin(e1[0], fmin(e1[1], e1[2]))) / 255;
  const double dh = fabs(h1 - h2);
  if (ch1 >= 0.35 && fmin(dh, 360 - dh) < 28) fromHsl(fmod(h1 + 165, 360.0), 0.9, 0.6, e2);  // a clash: the opposite
  double e2l[3];
  lift(e2, 0.17, e2l);
  double b0[3], b1[3];
  unpack(bodyInfo(body).hex, b0);
  lift(b0, 0.2, b1);
  BornPalette P;
  P.e1 = round(e1);
  P.e2 = round(e2l);
  P.b1 = round(b1);
  P.b0 = round(b0);
  P.on1 = inkOn(e1);
  P.on2 = inkOn(e2l);
  P.onb = inkOn(b1);
  const double k[3][3] = {{e1[0] * 0.14, e1[1] * 0.14, e1[2] * 0.14},
                          {e1[0] * 0.23, e1[1] * 0.23, e1[2] * 0.23},
                          {e1[0] * 0.40, e1[1] * 0.40, e1[2] * 0.40}};
  P.peb = round(k[0]);
  P.peb2 = round(k[1]);
  P.pebe = round(k[2]);
  return P;
}

BornPalette bornPaletteFor(int design, Body body) {
  if (design < 0 || design >= eyes::kDesignCount) design = 0;
  const eyes::Design& d = eyes::kDesigns[design];
  return bornPalette(d.white, d.pupilL, d.pupilR, body);
}

}  // namespace suflet
