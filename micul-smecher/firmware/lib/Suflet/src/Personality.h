// Every unit is born with a seed (its chip ID). The seed decides the eye
// tint, blink rhythm, shyness, curiosity... No two are the same, and the
// seed cannot be re-rolled — that is what makes each one "someone".
#pragma once
#include <stdint.h>

#include "Color.h"

namespace suflet {

enum class Rarity : uint8_t { Common, Rare, VeryRare, Legendary };

struct Personality {
  uint64_t seed = 0;
  float blinkMin = 2.2f, blinkMax = 6.0f;  // seconds between blinks
  float shyness = 0.5f;                    // 0..1: how fast it gets shy
  float curiosity = 0.5f;                  // 0..1: how much it looks around
  float sleepiness = 0.5f;                 // 0..1: how soon it dozes off
  float eyeW = 0.12f, eyeH = 0.19f, spacing = 0.19f;
  float lidTilt = 0.16f;  // the signature cheeky lid angle
  Rgb eyeDay = pal::kEyeDay, eyeNight = pal::kEyeNight;
  Rarity rarity = Rarity::Common;
  uint8_t tint = 0;     // index into the tint table
  uint8_t favRare = 0;  // favourite rare reaction (0..2), twice as likely

  static Personality fromSeed(uint64_t seed);
  const char* tintName() const;      // e.g. "Cream"
  const char* rarityName() const;    // e.g. "Rare"
  const char* archetypeRo() const;   // e.g. "Curiosul" (for the birth card)
  float sleepAfterSeconds() const;   // stillness before dozing off
};

}  // namespace suflet
