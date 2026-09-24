#pragma once
#include <stdint.h>

namespace suflet {

struct Rgb {
  uint8_t r = 0, g = 0, b = 0;
  constexpr Rgb() = default;
  constexpr Rgb(uint8_t r_, uint8_t g_, uint8_t b_) : r(r_), g(g_), b(b_) {}
  static constexpr Rgb hex(uint32_t v) {
    return Rgb((uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v);
  }
  uint16_t to565() const {
    return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
  }
  static Rgb from565(uint16_t c) {
    uint8_t r5 = (c >> 11) & 0x1F, g6 = (c >> 5) & 0x3F, b5 = c & 0x1F;
    return Rgb((uint8_t)((r5 << 3) | (r5 >> 2)), (uint8_t)((g6 << 2) | (g6 >> 4)),
               (uint8_t)((b5 << 3) | (b5 >> 2)));
  }
  Rgb scaled(float k) const {
    if (k <= 0) return Rgb();
    if (k >= 1) return *this;
    return Rgb((uint8_t)(r * k), (uint8_t)(g * k), (uint8_t)(b * k));
  }
  static Rgb lerp(Rgb a, Rgb b, float t) {
    if (t <= 0) return a;
    if (t >= 1) return b;
    return Rgb((uint8_t)(a.r + (b.r - a.r) * t), (uint8_t)(a.g + (b.g - a.g) * t),
               (uint8_t)(a.b + (b.b - a.b) * t));
  }
  bool operator==(const Rgb& o) const { return r == o.r && g == o.g && b == o.b; }
};

// Palette (from the concept artifact v0.9.3).
namespace pal {
constexpr Rgb kBlack = Rgb(0, 0, 0);
constexpr Rgb kEyeDay = Rgb::hex(0xFFF0C8);    // warm cream
constexpr Rgb kEyeNight = Rgb::hex(0xFFC96B);  // amber, night-light
constexpr Rgb kBlush = Rgb::hex(0xFF7A9A);
constexpr Rgb kHeart = Rgb::hex(0xFF6B8A);
constexpr Rgb kWhite = Rgb::hex(0xFFFFFF);
constexpr Rgb kMint = Rgb::hex(0xC9F2E4);
constexpr Rgb kIce = Rgb::hex(0x9FC6FF);
constexpr Rgb kGold = Rgb::hex(0xFFD76B);
}  // namespace pal

}  // namespace suflet
