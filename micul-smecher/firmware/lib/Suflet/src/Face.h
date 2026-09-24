// The face: a fully parametric description of what the eyes look like in
// one frame. The Brain writes a Face every frame; renderFace() draws it.
// All sizes are fractions of the display diameter, so the same Face works
// on 240x240 (1.28"), 390x390 (1.2") and 466x466 (1.43") screens.
#pragma once
#include <stdint.h>

#include "Canvas.h"
#include "Color.h"

namespace suflet {

enum class EyeStyle : uint8_t {
  Normal,   // soft glowing ellipse with the signature cheeky lid
  Closed,   // content closed lids (sleep, purring)
  Squeeze,  // > <  (laughing, sneezing)
  Heart,    // heart eyes
  Star,     // star eyes (birthday, rare)
  Spiral,   // dizzy
};

namespace ov {
enum : uint16_t {
  Zzz = 1 << 0,
  Hearts = 1 << 1,
  Orbit = 1 << 2,     // dizzy stars
  Question = 1 << 3,  // "?"
  Sweat = 1 << 4,
  Yawn = 1 << 5,
  Zigzag = 1 << 6,  // wobbly mouth (cold / grumpy)
  Confetti = 1 << 7,
  Listen = 1 << 8,    // AI: listening ring
  Think = 1 << 9,     // AI: thinking dots
  Alert = 1 << 10,    // Claude needs you: pulsing amber ring
  Progress = 1 << 11, // hold-to-approve progress arc
};
}

struct Eye {
  float open = 1;         // vertical openness multiplier (0 = closed)
  float scale = 1;        // uniform size
  float sx = 1, sy = 1;   // squash & stretch
  float lidTop = 0.19f;   // fraction of eye height hidden by the top lid
  float lidTilt = 0.16f;  // radians; + = inner corner lower (cheeky), - = sad
  float lidBot = 0;       // fraction hidden by the bottom lid
  float dx = 0, dy = 0;   // per-eye offset
};

struct Face {
  Eye L, R;
  float gx = 0, gy = 0;      // gaze, -1..1
  float spacing = 0.19f;     // eye centre offset from the middle
  float eyeW = 0.12f;        // eye half-width
  float eyeH = 0.19f;        // eye half-height
  float cy = 0.02f;          // vertical position of the eyes
  float bright = 1;          // global brightness (fade in/out, sleep dim)
  float glow = 1;            // halo strength
  Rgb color = pal::kEyeDay;  // eye colour
  EyeStyle style = EyeStyle::Normal;
  float styleAmt = 0;  // 0 = Normal .. 1 = style
  float happy = 0;     // ^ ^ arcs
  float blush = 0;
  uint16_t overlays = 0;
  float overlayT = 0;  // seconds since the overlay started (animations)
  float spin = 0;      // rotation for spiral / star eyes
  float mouth = 0;     // yawn opening 0..1
  float level = 0;     // AI audio level 0..1 (listening / speaking)
  float progress = 0;  // 0..1 for ov::Progress
};

void renderFace(Canvas& cv, const Face& f);

}  // namespace suflet
