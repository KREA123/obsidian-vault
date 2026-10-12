// SoulOS Alive, every screen on the device (os/DESIGN-ALIVE.md §4): the simulator's stills of the states in
// sim/alive_states.h (the same ones the native round audit checks, test/test_suflet/test_audit.cpp).
//
//   .pio/build/sim/program <out_dir> screens     <out_dir>/NN-name.ppm + shots.txt (name, the web still)
//   python3 tools/alive_sheet.py <out_dir> sim/shots/alive   PNGs + the device-vs-web sheet
#include <cstdio>
#include <string>

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
