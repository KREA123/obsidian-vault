// The SoulOS Alive atlases (Bricolage Grotesque, Martian Mono), kept in their own translation unit so the
// generated data is compiled once (FontAliveData.h, tools/gen_font_alive.py). The S ramp lives in FontAliveS.cpp.
#include "FontAliveData.h"

namespace suflet {
namespace fonts {
// FontAliveS.cpp: the S ramp's atlas for a role (0 tag, 1 caption, 2 body, 3 name, 4 title), null if not built
const Font* rampS(int role);

namespace {
TypeRamp gRamp = TypeRamp::M;
inline const Font& pick(int role, const Font& m) {
  if (gRamp == TypeRamp::S) {
    const Font* f = rampS(role);
    if (f) return *f;
  }
  return m;
}
}  // namespace

void setRamp(TypeRamp r) { gRamp = r == TypeRamp::S && rampS(0) ? TypeRamp::S : TypeRamp::M; }
TypeRamp ramp() { return gRamp; }
bool hasRamp(TypeRamp r) { return r == TypeRamp::M || rampS(0) != nullptr; }
const Font& tag() { return pick(0, fontalive::kTag); }
const Font& caption() { return pick(1, fontalive::kSmall2); }
const Font& body() { return pick(2, fontalive::kBody); }
const Font& name() { return pick(3, fontalive::kName); }
const Font& title() { return pick(4, fontalive::kTitle); }
const Font& bigDigits() { return fontalive::kDigits2; }
}  // namespace fonts
}  // namespace suflet
