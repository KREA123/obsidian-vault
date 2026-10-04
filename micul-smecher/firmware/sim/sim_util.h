// Shared by the simulator's modes: the frame hash (SIM_HASH=1, pixel-exact before/after checks) and what the
// 2.8C's display pipeline copies per frame (firmware/PERF.md).
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "Canvas.h"
#include "Frame.h"


namespace suflet {

// The pixels the 2.8C's displayPresent() copies from the canvas into the back frame buffer for a frame
// that changed `ch` (the back buffer also misses what the previous frame changed): presentPlan(), as there.
inline uint64_t presentCost(const RectList& ch, RectList& last) { return (uint64_t)presentPlan(ch, last).pixels(); }


// SIM_HASH=1: write one 64-bit FNV-1a hash of the RGB565 canvas per frame (<name>.hash) instead of the raw
// frames: a pixel-exact before/after check of every scenario (tools/perf_bench.py --check) in a few KB.
inline uint64_t frameHash(const uint16_t* px, size_t n) {
  uint64_t h = 1469598103934665603ull;
  for (size_t i = 0; i < n; ++i) {
    h = (h ^ (px[i] & 0xFF)) * 1099511628211ull;
    h = (h ^ (px[i] >> 8)) * 1099511628211ull;
  }
  return h;
}

// SIM_DUMP="12,40": write those frame numbers as <prefix>-<n>.ppm (to look at a frame the hashes flag)
inline void dumpPpm(const Canvas& cv, const char* prefix, int frame) {
  const char* want = getenv("SIM_DUMP");
  if (!want) return;
  bool hit = false;
  for (const char* p = want; *p;) {
    if (atoi(p) == frame) hit = true;
    while (*p && *p != ',') ++p;
    if (*p == ',') ++p;
  }
  if (!hit) return;
  char fn[512];
  snprintf(fn, sizeof fn, "%s-%d.ppm", prefix, frame);
  FILE* f = fopen(fn, "wb");
  if (!f) return;
  fprintf(f, "P6\n%d %d\n255\n", cv.width(), cv.height());
  for (int i = 0; i < cv.width() * cv.height(); ++i) {
    const Rgb c = Rgb::from565(cv.data()[i]);
    fputc(c.r, f);
    fputc(c.g, f);
    fputc(c.b, f);
  }
  fclose(f);
}

}  // namespace suflet
