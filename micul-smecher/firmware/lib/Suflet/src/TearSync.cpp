// TearSync.h: the band planner for tear-free writes into a scanning panel.
#include "TearSync.h"

#include <math.h>

namespace suflet {

namespace {
// phase of row r written at time tw: how far behind row r's last scan the write is, in [0, period)
double phaseOf(const ScanModel& m, int r, double tw) {
  const double p = tw - (m.offsetUs + r * m.rowUs());
  double f = fmod(p, m.periodUs);
  if (f < 0) f += m.periodUs;
  return f;
}
// A band of n rows w px wide. Row r (from the band's first, i = 0..n-1) starts at phase f0 + i * slope and ends rw
// later; every row must start >= margin after its last scan and end >= margin before its next one. The phase is
// linear in i, so the first and the last row decide: the window for f0 is [lo, hi].
struct Window {
  double lo, hi;
};
Window windowOf(const ScanModel& m, int n, int w) {
  const double rw = w / m.pxPerUs, slope = rw - m.rowUs(), d = (n - 1) * slope;
  Window win;
  win.lo = m.marginUs + (d < 0 ? -d : 0);
  win.hi = m.periodUs - m.marginUs - rw - (d > 0 ? d : 0);
  return win;
}
}  // namespace

int tearMaxRows(const ScanModel& m, int w) {
  const double rw = w / m.pxPerUs;
  const double perRow = fabs(rw - m.rowUs());  // the phase drift per row
  const double room = m.periodUs - 2 * m.marginUs - rw - 4;  // (4 µs: the planner aims inside the window)
  int n = perRow <= 1e-9 ? m.rows : 1 + (int)floor(room / perRow);
  if (n > m.rows) n = m.rows;
  n &= ~1;  // CO5300: even rows
  return n < 2 ? 2 : n;
}

bool tearSafe(const ScanModel& m, int w, int y0, int y1, double t) {
  if (y1 <= y0) return true;
  const double f0 = phaseOf(m, y0, t + m.setupUs);  // the first pixel lands after the window is set
  const Window win = windowOf(m, y1 - y0, w);
  return f0 >= win.lo && f0 <= win.hi;
}

TearBand tearNextBand(const ScanModel& m, int w, int y0, int y1, double t) {
  TearBand b;
  b.y0 = y0;
  const int most = tearMaxRows(m, w);
  b.y1 = y1 - y0 > most ? y0 + most : y1;
  if (tearSafe(m, w, b.y0, b.y1, t)) return b;
  // the earliest start whose first row's phase is in the window (1 µs inside it: no rounding at its edge)
  const Window win = windowOf(m, b.y1 - b.y0, w);
  const double f0 = phaseOf(m, b.y0, t + m.setupUs);
  const double aim = win.hi - win.lo > 2 ? win.lo + 1.0 : (win.lo + win.hi) * 0.5;
  b.waitUs = f0 < aim ? aim - f0 : m.periodUs - f0 + aim;  // past the window this period: the next one
  if (b.waitUs >= m.periodUs) b.waitUs -= m.periodUs;
  return b;
}

}  // namespace suflet
