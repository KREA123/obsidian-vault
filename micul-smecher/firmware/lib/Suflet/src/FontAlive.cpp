// The SoulOS Alive atlases (Bricolage Grotesque, Martian Mono), kept in their own translation unit so the
// generated data is compiled once (FontAliveData.h, tools/gen_font_alive.py).
#include "FontAliveData.h"

namespace suflet {
namespace fonts {
const Font& tag() { return fontalive::kTag; }
const Font& caption() { return fontalive::kSmall2; }
const Font& body() { return fontalive::kBody; }
const Font& name() { return fontalive::kName; }
const Font& title() { return fontalive::kTitle; }
}  // namespace fonts
}  // namespace suflet
