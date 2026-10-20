// SoulOS Alive, every screen on the device (os/DESIGN-ALIVE.md §4): the simulator's stills of the states in
// sim/alive_states.h (the same ones the native round audit checks, test/test_suflet/test_audit.cpp).
//
//   .pio/build/sim/program <out_dir> screens     <out_dir>/NN-name.ppm + shots.txt (name, the web still)
//   python3 tools/alive_sheet.py <out_dir> sim/shots/alive   PNGs + the device-vs-web sheet
#include <cstdio>
#include <string>
#include <vector>

#include "alive_states.h"

using namespace suflet;

int screensMode(const std::string& dir) {
  FILE* manifest = fopen((dir + "/shots.txt").c_str(), "wb");
  for (int i = 0; i < alive_states::kStateCount; ++i) {
    const alive_states::State& st = alive_states::kStates[i];
    alive_states::Rig s(st.booted);
    if (!alive_states::setup(s, st.name)) {
      fprintf(stderr, "unknown state %s\n", st.name);
      continue;
    }
    char fn[512];
    snprintf(fn, sizeof fn, "%s/%02d-%s.ppm", dir.c_str(), i + 1, st.name);
    FILE* f = fopen(fn, "wb");
    if (!f) return 1;
    fprintf(f, "P6\n%d %d\n255\n", s.W, s.H);
    for (int k = 0; k < s.W * s.H; ++k) {
      const Rgb c = Rgb::from565(s.fb[(size_t)k]);
      fputc(c.r, f);
      fputc(c.g, f);
      fputc(c.b, f);
    }
    fclose(f);
    if (manifest) fprintf(manifest, "%02d-%s %s %s\n", i + 1, st.name, st.web[0] ? st.web : "-", viewName(s.os.view()));
    printf("  %02d %-16s view %s\n", i + 1, st.name, viewName(s.os.view()));
  }
  if (manifest) fclose(manifest);
  return 0;
}

// SOUL S (the product, decision 2026-10-20): every screen on the AMOLED-1.75's 466 px glass, drawn with the
// density layer (Density.h), and the same states on SOUL M's 2.8C for the side-by-side sheet. The same states the
// round audit checks on both glasses (test_audit.cpp: test_audit_every_screen_on_both_glasses).
//
//   .pio/build/sim/program <out_dir> alive-s     <out_dir>/s-NN-name.ppm, m-NN-name.ppm + shots.txt
//   python3 tools/alive_s_sheet.py <out_dir> sim/shots/alive-s     PNGs + the S-vs-M sheets at true size
int sScreensMode(const std::string& dir) {
  FILE* manifest = fopen((dir + "/shots.txt").c_str(), "wb");
  // standby first (not in kStates: the audit's states start awake), then every state
  std::vector<alive_states::State> all;
  all.push_back({"standby", "", true});
  for (int i = 0; i < alive_states::kStateCount; ++i) all.push_back(alive_states::kStates[i]);
  const int n = (int)all.size();
  for (int glass = 0; glass < 2; ++glass) {
    const DisplayGeometry& g = glass == 0 ? displays::kAmoled175 : displays::kLcd28;
    for (int i = 0; i < n; ++i) {
      alive_states::Rig s(all[(size_t)i].booted, -1, g);
      if (!alive_states::setup(s, all[(size_t)i].name)) {
        fprintf(stderr, "unknown state %s\n", all[(size_t)i].name);
        continue;
      }
      char fn[512];
      snprintf(fn, sizeof fn, "%s/%c-%02d-%s.ppm", dir.c_str(), glass == 0 ? 's' : 'm', i + 1, all[(size_t)i].name);
      FILE* f = fopen(fn, "wb");
      if (!f) return 1;
      fprintf(f, "P6\n%d %d\n255\n", s.W, s.H);
      for (int k = 0; k < s.W * s.H; ++k) {
        const Rgb c = Rgb::from565(s.fb[(size_t)k]);
        fputc(c.r, f);
        fputc(c.g, f);
        fputc(c.b, f);
      }
      fclose(f);
      if (manifest)
        fprintf(manifest, "%c-%02d-%s %s %.3f\n", glass == 0 ? 's' : 'm', i + 1, all[(size_t)i].name, viewName(s.os.view()),
                g.activeMm);
      printf("  %c %02d %-16s view %s\n", glass == 0 ? 'S' : 'M', i + 1, all[(size_t)i].name, viewName(s.os.view()));
    }
  }
  if (manifest) fclose(manifest);
  return 0;
}
