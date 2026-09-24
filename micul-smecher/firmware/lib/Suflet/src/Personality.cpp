#include "Personality.h"

#include "Rng.h"

namespace suflet {

namespace {
struct Tint {
  const char* name;
  Rgb day;
  Rgb night;
  Rarity rarity;
  float weight;  // share of units, sums to 100
};
// Collectible rarity without blind boxes: the tint is fixed at birth.
const Tint kTints[] = {
    {"Cream", Rgb::hex(0xFFF0C8), Rgb::hex(0xFFC96B), Rarity::Common, 58.0f},
    {"Ice", Rgb::hex(0xD8F0FF), Rgb::hex(0xFFC96B), Rarity::Common, 16.0f},
    {"Mint", Rgb::hex(0xD2FFE6), Rgb::hex(0xFFC96B), Rarity::Rare, 10.0f},
    {"Peach", Rgb::hex(0xFFDCC8), Rgb::hex(0xFFB88A), Rarity::Rare, 9.0f},
    {"Lilac", Rgb::hex(0xE6DAFF), Rgb::hex(0xFFC0D8), Rarity::VeryRare, 6.0f},
    {"Gold", Rgb::hex(0xFFD76B), Rgb::hex(0xFFB347), Rarity::Legendary, 1.0f},
};
constexpr int kTintCount = sizeof(kTints) / sizeof(kTints[0]);
}  // namespace

Personality Personality::fromSeed(uint64_t seed) {
  Personality p;
  p.seed = seed;
  Rng r(seed ^ 0x5EEDC0FFEEull);

  float roll = r.uniform() * 100.0f;
  int t = 0;
  for (; t < kTintCount - 1; ++t) {
    if (roll < kTints[t].weight) break;
    roll -= kTints[t].weight;
  }
  p.tint = (uint8_t)t;
  p.eyeDay = kTints[t].day;
  p.eyeNight = kTints[t].night;
  p.rarity = kTints[t].rarity;

  p.shyness = r.range(0.1f, 0.95f);
  p.curiosity = r.range(0.15f, 0.95f);
  p.sleepiness = r.range(0.1f, 0.9f);
  const float blink = r.range(0.8f, 1.25f);
  p.blinkMin = 2.2f * blink;
  p.blinkMax = 6.0f * blink;
  // micro-variance of the face: +-5 %, visible side by side, never ugly
  p.eyeW = 0.12f * r.range(0.95f, 1.05f);
  p.eyeH = 0.19f * r.range(0.95f, 1.05f);
  p.spacing = 0.19f * r.range(0.96f, 1.04f);
  p.lidTilt = 0.16f * r.range(0.8f, 1.25f);
  p.favRare = (uint8_t)r.irange(0, 2);
  return p;
}

const char* Personality::tintName() const { return kTints[tint < kTintCount ? tint : 0].name; }

const char* Personality::rarityName() const {
  switch (rarity) {
    case Rarity::Common: return "Common";
    case Rarity::Rare: return "Rare";
    case Rarity::VeryRare: return "Very rare";
    case Rarity::Legendary: return "Legendary";
  }
  return "Common";
}

const char* Personality::archetypeRo() const {
  // The dominant trait names the character on its birth card.
  if (shyness > 0.75f && curiosity < 0.5f) return "Timidul";
  if (curiosity > 0.75f && shyness < 0.4f) return "Obraznicul";
  if (curiosity > 0.7f) return "Curiosul";
  if (sleepiness > 0.72f) return "Somnorosul";
  if (shyness > 0.7f) return "Sfiosul";
  if (sleepiness < 0.25f) return "Neastâmpăratul";
  return "Șmecherul";
}

float Personality::sleepAfterSeconds() const {
  // 20 s (sleepy) .. 60 s (restless) of complete stillness
  return 60.0f - 40.0f * sleepiness;
}

}  // namespace suflet
