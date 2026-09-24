// Deterministic RNG + hashing. Same seed -> same personality, same idle
// behaviour in tests and in the simulator.
#pragma once
#include <stdint.h>

namespace suflet {

inline uint64_t mix64(uint64_t z) {
  z += 0x9E3779B97F4A7C15ull;
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
  return z ^ (z >> 31);
}

struct Rng {
  uint64_t s;
  explicit Rng(uint64_t seed = 1) : s(mix64(seed) | 1ull) {}
  uint64_t next() {  // xorshift64*
    s ^= s >> 12;
    s ^= s << 25;
    s ^= s >> 27;
    return s * 2685821657736338717ull;
  }
  // [0, 1)
  float uniform() { return (float)(next() >> 40) * (1.0f / 16777216.0f); }
  float range(float a, float b) { return a + (b - a) * uniform(); }
  bool chance(float p) { return uniform() < p; }
  // [a, b] inclusive
  int irange(int a, int b) {
    int n = b - a + 1;
    int v = a + (int)(uniform() * (float)n);
    return v > b ? b : v;
  }
  float sign() { return (next() & 1) ? 1.0f : -1.0f; }
};

}  // namespace suflet
