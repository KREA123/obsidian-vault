// Tear-free writes into the CO5300 (lib/Suflet/src/TearSync.h, src/board_amoled.cpp; the S firmware critic,
// 2026-10-22: changed rectangles were written with no tearing sync). The planner is checked against a brute-force
// model of the panel: every row of a planned band is written between two scans of that row, never across one.
#include <math.h>
#include <stdio.h>
#include <unity.h>

#include <initializer_list>

#include "TearSync.h"

using namespace suflet;

namespace {
// brute force: row r of a band [y0, y1) w px wide, the band started at t (µs after a TE edge). The write of row r
// lasts from a(r) to b(r); the scans of row r are at offset + r rowUs + k period. Safe = no scan of any row falls
// inside [a(r) - margin, b(r) + margin] AND every row's write sits in the same scan period relative to its scan
// (the scan never passes the write pointer: no row shows new while a row above it in the band still shows old).
bool bruteSafe(const ScanModel& m, int w, int y0, int y1, double t, double margin) {
  const double rowWrite = w / m.pxPerUs;
  long period0 = 0;
  for (int r = y0; r < y1; ++r) {
    const double a = t + m.setupUs + (r - y0) * rowWrite, b = a + rowWrite;
    const double scan = m.offsetUs + r * m.rowUs();
    // the scan period this row's write falls in
    const long k = (long)floor((a - scan) / m.periodUs);
    if (r == y0) period0 = k;
    if (k != period0) return false;
    // the next and previous scans keep their distance
    const double prev = scan + k * m.periodUs, next = prev + m.periodUs;
    if (a - prev < margin || next - b < margin) return false;
  }
  return true;
}
ScanModel measured(double hz, double vblankUs, double mbps) {
  ScanModel m;
  m.periodUs = 1e6 / hz;
  m.offsetUs = vblankUs;
  m.activeUs = m.periodUs - vblankUs;
  m.pxPerUs = mbps / 2.0;  // MB/s of RGB565 -> px per µs
  return m;
}
}  // namespace

static void test_tear_bands_are_even_and_fit_a_period() {
  for (double hz : {50.0, 60.0, 75.0})
    for (double mbps : {8.0, 12.0, 16.0, 30.0}) {
      const ScanModel m = measured(hz, 600, mbps);
      for (int w : {2, 60, 166, 300, 466}) {
        const int n = tearMaxRows(m, w);
        TEST_ASSERT_EQUAL_INT(0, n % 2);  // CO5300: even rows
        TEST_ASSERT_TRUE(n >= 2 && n <= m.rows);
        // a band of n rows (its first row's start to its last row's end) drifts against the scan by less than a
        // period minus the margins (unless it is the 2-row minimum)
        const double drift = fabs((n - 1) * (w / m.pxPerUs - m.rowUs())) + w / m.pxPerUs;
        TEST_ASSERT_TRUE(n == 2 || drift <= m.periodUs - 2 * m.marginUs);
      }
    }
}

// every rectangle of every size, started at any phase of the scan, comes out in bands that are each safe when they
// start (brute force), in order, covering every row once; the waits stay under one period
static void test_tear_planned_bands_never_cross_the_scan() {
  int bands = 0, waited = 0, rects = 0;
  double worstWait = 0;
  for (double hz : {55.0, 60.0, 70.0})
    for (double mbps : {10.0, 16.0, 24.0}) {
      const ScanModel m = measured(hz, 700, mbps);
      for (int w : {40, 166, 330, 466})
        for (int y0 = 0; y0 < 466; y0 += 58)
          for (int h : {2, 40, 160, 466}) {
            const int y1 = y0 + h > 466 ? 466 : y0 + h;
            for (double t0 = 0; t0 < m.periodUs * 2; t0 += m.periodUs / 7.3) {
              ++rects;
              double t = t0;
              int y = y0;
              while (y < y1) {
                const TearBand b = tearNextBand(m, w, y, y1, t);
                TEST_ASSERT_EQUAL_INT(y, b.y0);
                TEST_ASSERT_TRUE(b.y1 > b.y0 && b.y1 <= y1);
                TEST_ASSERT_TRUE(b.waitUs >= 0 && b.waitUs < m.periodUs);
                worstWait = fmax(worstWait, b.waitUs);
                waited += b.waitUs > 0;
                const double start = t + b.waitUs;
                TEST_ASSERT_TRUE(tearSafe(m, w, b.y0, b.y1, start));
                TEST_ASSERT_TRUE(bruteSafe(m, w, b.y0, b.y1, start, m.marginUs * 0.99));
                t = start + m.writeUs(b.y1 - b.y0, w);
                y = b.y1;
                ++bands;
              }
            }
          }
    }
  printf("  tear sync: %d rectangles, %d bands, %d waited, the longest wait %.1f ms\n", rects, bands, waited, worstWait / 1000);
  TEST_ASSERT_TRUE(bands > rects);
}

// the brute force itself: a whole frame written at once from row 0 crosses the scan (the 1.9.0 write); the same
// rows in the planner's bands, each at its planned start, do not
static void test_tear_brute_force_sees_a_shear() {
  const ScanModel m = measured(60, 700, 16);
  TEST_ASSERT_FALSE(bruteSafe(m, 466, 0, 466, 0, 0));  // 27 ms of writing against a 16.7 ms scan
  TEST_ASSERT_FALSE(tearSafe(m, 466, 0, 466, 0));
  double t = 0;
  int y = 0, n = 0;
  while (y < 466) {
    const TearBand b = tearNextBand(m, 466, y, 466, t);
    TEST_ASSERT_TRUE(bruteSafe(m, 466, b.y0, b.y1, t + b.waitUs, m.marginUs * 0.99));
    t += b.waitUs + m.writeUs(b.y1 - b.y0, 466);
    y = b.y1;
    ++n;
  }
  TEST_ASSERT_TRUE(n >= 1);
  printf("  tear sync: a whole frame at 60 Hz, 16 MB/s: %d bands, %.1f ms (written straight: %.1f ms)\n", n, t / 1000,
         m.writeUs(466, 466) / 1000);
}

void runTearTests() {
  RUN_TEST(test_tear_bands_are_even_and_fit_a_period);
  RUN_TEST(test_tear_planned_bands_never_cross_the_scan);
  RUN_TEST(test_tear_brute_force_sees_a_shear);
}
