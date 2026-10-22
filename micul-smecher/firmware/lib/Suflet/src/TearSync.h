// Tear-free writes into a panel that keeps its own frame (the CO5300 AMOLED of SOUL S, firmware/SOUL-S.md §6).
//
// The panel scans its frame memory top to bottom once a refresh; the firmware writes changed rectangles into the
// same memory over QSPI. A write the scan crosses shows half old, half new on the glass for one refresh: a shear
// across a saccade, a blink, the lid wipe or a wheel scroll. The CO5300's tearing-effect line (TE, GPIO13 on the
// Waveshare AMOLED-1.75, schematic p.1) rises at the start of each V-blank when it is switched on (0x35 0x00).
//
// The model: row r is scanned at  offsetUs + r * activeUs / rows  after each TE rising edge, every periodUs
// (offsetUs = the V-blank, activeUs = periodUs - V-blank; all measured on the board from the TE edges). Row r of
// a band is written from a(r) to a(r) + w / pxPerUs. The band is safe when every row's write sits between two
// consecutive scans of that row, at least marginUs from both: then the scan never passes the write pointer and no
// refresh shows part of the band new and part old. The write and the scan are both straight lines in time, so the
// band's first and last rows decide (one window for the first row's phase). A band whose write drifts against the
// scan by more than a period cannot be made safe in one go: it is split into smaller bands, each started in its
// window (waiting for it when needed).
//
// Pure logic, no hardware: unit-tested on the PC against a brute-force panel (test_tear.cpp); src/board_amoled.cpp
// measures the model on the board (TE edges, the write rate) and waits for each band's start.
#pragma once

namespace suflet {

struct ScanModel {
  double periodUs = 16667;  // one refresh, between TE rising edges [estimare until measured: CO5300 not published]
  double offsetUs = 0;      // TE rising edge -> row 0 scanned (the V-blank: TE high time)
  double activeUs = 16667;  // row 0 -> the last row
  int rows = 466;
  double pxPerUs = 6;       // the write rate (px per µs), measured on every band; 12 MB/s to start [estimare]
  double setupUs = 40;      // per band: the address window + the first transaction
  double marginUs = 500;    // kept clear of the scanline at both ends of a band (timer jitter, model error)
  double rowUs() const { return activeUs / rows; }
  // the time a band of `rows` rows `w` px wide takes to write
  double writeUs(int nRows, int w) const { return setupUs + (double)nRows * w / pxPerUs; }
};

struct TearBand {
  int y0 = 0, y1 = 0;  // rows [y0, y1)
  double waitUs = 0;   // from the planning time to the band's start (0 = now)
};

// The most rows of a band `w` px wide that one scan period can hold (always >= 2, even).
int tearMaxRows(const ScanModel& m, int w);

// Plans the next band of a rectangle w px wide, rows [y0, y1): its rows (from y0, at most tearMaxRows) and how long
// to wait before writing it, given `t` = µs since the last TE rising edge (any value >= 0; periods past the edge
// are fine). The band is then safe to write at t + waitUs.
TearBand tearNextBand(const ScanModel& m, int w, int y0, int y1, double t);

// Is a band rows [y0, y1), w px wide, written starting at `t` µs after a TE rising edge, clear of the scan?
bool tearSafe(const ScanModel& m, int w, int y0, int y1, double t);

}  // namespace suflet
