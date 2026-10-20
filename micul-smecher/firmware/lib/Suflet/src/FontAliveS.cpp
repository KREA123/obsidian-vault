// The SoulOS Alive atlases at SOUL S's sizes (the 1.75" AMOLED: tag 28, caption 32, body 37, name 40, title 45 px;
// tools/gen_font_alive.py s -> FontAliveSData.h, Density.h). A build for the 2.8C (SOUL M) does not link them
// (≈ 194 KB of flash): rampS() is then null and fonts:: stays on the M ramp.
#include "Font.h"

#if !defined(SUFLET_BOARD_LCD28)
#include "FontAliveSData.h"
#endif

namespace suflet {
namespace fonts {
const Font* rampS(int role) {
#if defined(SUFLET_BOARD_LCD28)
  (void)role;
  return nullptr;
#else
  switch (role) {
    case 0: return &fontalive_s::kTag;
    case 1: return &fontalive_s::kSmall2;
    case 2: return &fontalive_s::kBody;
    case 3: return &fontalive_s::kName;
    case 4: return &fontalive_s::kTitle;
    default: return nullptr;
  }
#endif
}
}  // namespace fonts
}  // namespace suflet
