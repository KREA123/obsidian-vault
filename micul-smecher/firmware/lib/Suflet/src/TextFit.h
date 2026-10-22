// One way to cut a line of words that does not fit: "…" at the end, never through a number or a unit
// (the S firmware critic, 2026-10-22: "↑2…" for ↑24°, "↓…" for the low, "PSRAM 5.8 …", "25.09…").
//
// The line is cut at the last code point that still fits with "…". If that cut lands inside a word that holds a
// number (a digit, °, %, ↑ or ↓), or right after a whole number whose unit is then cut to under 3 letters
// ("5.8 M…", "5.8 …"), the cut moves back to before that word, and past any number or separator left at the end
// (what followed them was cut): "PSRAM…", "Read…", "Partly cloudy…". It stays where it was when moving back would
// leave fewer than 3 letters. The round audit (test_audit.cpp, trunc) checks
// the same rule on every screen of both glasses.
#pragma once
#include <initializer_list>
#include <string>

#include "Font.h"

namespace suflet {

// `s` if it fits in maxW px of font f; otherwise its longest number-safe prefix + "…" (see above)
std::string ellipsizeWords(const Font& f, const std::string& s, float maxW);
// the first of `candidates` that fits whole; if none does, the last one cut by ellipsizeWords
std::string firstThatFits(const Font& f, std::initializer_list<std::string> candidates, float maxW);
// is code point c part of a number ("24", "↑24°", "5.8", "50%")?
bool numberPart(uint32_t c);

}  // namespace suflet
