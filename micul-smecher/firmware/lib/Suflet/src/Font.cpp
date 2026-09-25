#include "Font.h"

#include "FontData.h"

namespace suflet {

namespace fonts {
const Font& small() { return fontdata::kSmall; }
const Font& text() { return fontdata::kText; }
const Font& large() { return fontdata::kLarge; }
const Font& digits() { return fontdata::kDigits; }
}  // namespace fonts

const Glyph* Font::find(uint32_t cp) const {
  cp = utf8::normalizeRo(cp);
  for (int pass = 0; pass < 3; ++pass) {
    int lo = 0, hi = (int)count - 1;
    while (lo <= hi) {
      const int mid = (lo + hi) >> 1;
      const uint16_t c = glyphs[mid].cp;
      if (c == cp) return &glyphs[mid];
      if (c < cp) lo = mid + 1;
      else hi = mid - 1;
    }
    // missing: try the plain letter (e.g. an accent this size lacks), then '?'
    const uint32_t f = utf8::fold(cp);
    cp = (pass == 0 && f != cp) ? f : (uint32_t)'?';
  }
  return count ? &glyphs[0] : nullptr;
}

namespace utf8 {

uint32_t next(const char*& p, const char* end) {
  const uint8_t* s = (const uint8_t*)p;
  auto avail = [&](int n) {
    for (int i = 1; i < n; ++i) {
      if ((end && (const char*)s + i >= end) || (s[i] & 0xC0) != 0x80) return false;
    }
    return true;
  };
  const uint8_t c = s[0];
  if (c < 0x80) {
    p += 1;
    return c;
  }
  int n = 0;
  uint32_t cp = 0;
  if ((c & 0xE0) == 0xC0) {
    n = 2;
    cp = c & 0x1F;
  } else if ((c & 0xF0) == 0xE0) {
    n = 3;
    cp = c & 0x0F;
  } else if ((c & 0xF8) == 0xF0) {
    n = 4;
    cp = c & 0x07;
  }
  if (!n || !avail(n)) {
    p += 1;
    return 0xFFFD;
  }
  for (int i = 1; i < n; ++i) cp = (cp << 6) | (s[i] & 0x3F);
  p += n;
  // reject overlong forms and surrogates
  if ((n == 2 && cp < 0x80) || (n == 3 && cp < 0x800) || (n == 4 && (cp < 0x10000 || cp > 0x10FFFF)) ||
      (cp >= 0xD800 && cp <= 0xDFFF))
    return 0xFFFD;
  return cp;
}

int encode(uint32_t cp, char* o) {
  if (cp < 0x80) {
    o[0] = (char)cp;
    return 1;
  }
  if (cp < 0x800) {
    o[0] = (char)(0xC0 | (cp >> 6));
    o[1] = (char)(0x80 | (cp & 0x3F));
    return 2;
  }
  if (cp < 0x10000) {
    o[0] = (char)(0xE0 | (cp >> 12));
    o[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
    o[2] = (char)(0x80 | (cp & 0x3F));
    return 3;
  }
  o[0] = (char)(0xF0 | (cp >> 18));
  o[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
  o[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
  o[3] = (char)(0x80 | (cp & 0x3F));
  return 4;
}

size_t count(const char* s, size_t n) {
  size_t k = 0;
  const char* p = s;
  const char* e = s + n;
  while (p < e) {
    next(p, e);
    ++k;
  }
  return k;
}

size_t prevStart(const char* s, size_t n) {
  if (!n) return 0;
  size_t i = n - 1;
  // step back over at most 3 continuation bytes
  for (int k = 0; k < 3 && i > 0 && ((uint8_t)s[i] & 0xC0) == 0x80; ++k) --i;
  return i;
}

uint32_t normalizeRo(uint32_t cp) {
  switch (cp) {
    case 0x015E: return 0x0218;  // Ş -> Ș
    case 0x015F: return 0x0219;  // ş -> ș
    case 0x0162: return 0x021A;  // Ţ -> Ț
    case 0x0163: return 0x021B;  // ţ -> ț
    default: return cp;
  }
}

uint32_t lower(uint32_t cp) {
  if (cp >= 'A' && cp <= 'Z') return cp + 32;
  if (cp >= 0xC0 && cp <= 0xDE && cp != 0xD7) return cp + 32;
  if (cp >= 0x100 && cp <= 0x137) return cp | 1;
  if (cp >= 0x139 && cp <= 0x148) return (cp & 1) ? cp + 1 : cp;
  if (cp >= 0x14A && cp <= 0x177) return cp | 1;
  if (cp >= 0x218 && cp <= 0x21B) return cp | 1;
  return cp;
}

uint32_t upper(uint32_t cp) {
  if (cp >= 'a' && cp <= 'z') return cp - 32;
  if (cp >= 0xE0 && cp <= 0xFE && cp != 0xF7) return cp - 32;
  if (cp >= 0x100 && cp <= 0x137) return cp & ~1u;
  if (cp >= 0x139 && cp <= 0x148) return (cp & 1) ? cp : cp - 1;
  if (cp >= 0x14A && cp <= 0x177) return cp & ~1u;
  if (cp >= 0x218 && cp <= 0x21B) return cp & ~1u;
  return cp;
}

uint32_t fold(uint32_t cp) {
  const uint32_t l = lower(normalizeRo(cp));
  if (l < 0x80) return l;
  // Latin-1 lower-case letters 0xE0..0xFF
  static const char kLatin1[] = "aaaaaaaceeeeiiiidnooooo/ouuuuyty";
  if (l >= 0xE0 && l <= 0xFF) return l == 0xF7 ? l : (uint32_t)kLatin1[l - 0xE0];
  if (l == 0xDF) return 's';  // ß
  switch (l) {
    case 0x0101: case 0x0103: case 0x0105: return 'a';
    case 0x0107: case 0x0109: case 0x010B: case 0x010D: return 'c';
    case 0x0113: case 0x0115: case 0x0117: case 0x0119: case 0x011B: return 'e';
    case 0x0129: case 0x012B: case 0x012D: case 0x012F: case 0x0131: return 'i';
    case 0x0144: case 0x0146: case 0x0148: return 'n';
    case 0x014D: case 0x014F: case 0x0151: return 'o';
    case 0x015B: case 0x015D: case 0x015F: case 0x0161: case 0x0219: return 's';
    case 0x0163: case 0x0165: case 0x021B: return 't';
    case 0x0169: case 0x016B: case 0x016D: case 0x016F: case 0x0171: case 0x0173: return 'u';
    case 0x017A: case 0x017C: case 0x017E: return 'z';
    default: return l;
  }
}

bool isRoDiacritic(uint32_t cp) {
  switch (lower(normalizeRo(cp))) {
    case 0x0103: case 0x00E2: case 0x00EE: case 0x0219: case 0x021B: return true;
    default: return false;
  }
}

}  // namespace utf8
}  // namespace suflet
