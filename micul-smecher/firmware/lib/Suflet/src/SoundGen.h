// Focus sounds made on SOUL, no files, no network (os/APPS.md §Music): what
// the Music app plays through the I2S speaker (MAX98357A on the 2.8C) when
// the phone's media cannot be controlled. Four textures: rain, brown noise,
// ocean waves and a soft "fire" crackle. 16 kHz mono, int16, cheap enough to
// fill the I2S buffer from the audio task (a few multiplies per sample).
//
// Transport-free and deterministic (a seeded LCG), tested on the PC.
#pragma once
#include <math.h>
#include <stdint.h>

namespace suflet {

class SoundGen {
 public:
  enum Kind : uint8_t { Rain, Brown, Ocean, Fire, Count };
  static const char* name(Kind k, bool ro) {
    static const char* const en[] = {"Rain", "Brown noise", "Ocean", "Fireplace"};
    static const char* const r[] = {"Ploaie", "Zgomot maro", "Ocean", "Șemineu"};
    return (int)k < (int)Count ? (ro ? r[k] : en[k]) : "";
  }
  void set(Kind k, float volume) {
    kind_ = k;
    vol_ = volume < 0 ? 0 : volume > 1 ? 1 : volume;
  }
  Kind kind() const { return kind_; }
  float volume() const { return vol_; }
  // fill n samples at `rate` Hz
  void fill(int16_t* out, int n, int rate = 16000) {
    const float dt = 1.0f / rate;
    for (int i = 0; i < n; ++i) {
      const float w = white();
      // Paul Kellet's economical pink filter
      b0_ = 0.99765f * b0_ + w * 0.0990460f;
      b1_ = 0.96300f * b1_ + w * 0.2965164f;
      b2_ = 0.57000f * b2_ + w * 1.0526913f;
      const float pink = (b0_ + b1_ + b2_ + w * 0.1848f) * 0.11f;
      brown_ = (brown_ + 0.02f * w) / 1.02f;
      float s = 0;
      switch (kind_) {
        case Rain: {
          s = pink * 0.55f;
          if ((rand_() & 0x7FF) == 0) drop_ = 0.9f;  // a drop now and then
          s += drop_ * w * 0.6f;
          drop_ *= 0.996f;
          break;
        }
        case Brown: s = brown_ * 3.2f; break;
        case Ocean: {
          phase_ += dt * 6.2831853f / 9.0f;  // a wave every ~9 s
          const float swell = 0.25f + 0.75f * powf(0.5f + 0.5f * sinf(phase_), 2.0f);
          lp_ += (pink - lp_) * (0.08f + 0.25f * swell);
          s = lp_ * swell * 1.6f;
          break;
        }
        default: {  // fire: low rumble + crackles
          s = brown_ * 1.8f;
          if ((rand_() & 0x3FF) == 0) crack_ = 1.0f;
          s += crack_ * w * 0.8f;
          crack_ *= 0.985f;
          break;
        }
      }
      // smooth volume changes (no clicks)
      gain_ += (vol_ - gain_) * 0.0005f;
      float v = s * gain_ * 0.6f;
      v = v > 1 ? 1 : v < -1 ? -1 : v;
      out[i] = (int16_t)(v * 32000.0f);
    }
  }
  void reset(uint32_t seed = 12345) {
    s_ = seed;
    b0_ = b1_ = b2_ = brown_ = lp_ = drop_ = crack_ = phase_ = gain_ = 0;
  }

 private:
  uint32_t rand_() {
    s_ = s_ * 1664525u + 1013904223u;
    return s_ >> 8;
  }
  float white() { return ((rand_() & 0xFFFF) / 32767.5f) - 1.0f; }
  Kind kind_ = Rain;
  float vol_ = 0.5f, gain_ = 0;
  uint32_t s_ = 12345;
  float b0_ = 0, b1_ = 0, b2_ = 0, brown_ = 0, lp_ = 0, drop_ = 0, crack_ = 0, phase_ = 0;
};

}  // namespace suflet
