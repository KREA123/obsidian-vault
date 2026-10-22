// TextFit.h: cutting a line of words, never through a number.
#include "TextFit.h"

#include <string.h>

#include <vector>

#include "Canvas.h"

namespace suflet {

bool numberPart(uint32_t c) { return (c >= '0' && c <= '9') || c == 0xB0 || c == '%' || c == 0x2191 || c == 0x2193; }

namespace {
struct Cp {
  uint32_t c;
  size_t at;  // byte offset of the code point
};
bool isDigitish(uint32_t c) { return (c >= '0' && c <= '9') || c == '.' || c == ','; }
}  // namespace

std::string ellipsizeWords(const Font& f, const std::string& s, float maxW) {
  if (Canvas::measureText(f, s.c_str()) <= maxW) return s;
  // the plain cut: as many code points as fit with "…"
  std::string out;
  const char* p = s.c_str();
  const char* end = p + s.size();
  while (p < end) {
    const char* q = p;
    utf8::next(q, end);
    if (Canvas::measureText(f, (out + std::string(p, q - p) + "\xE2\x80\xA6").c_str()) > maxW) break;
    out.append(p, q - p);
    p = q;
  }
  const size_t cut = out.size();
  // the code points, to look at the words around the cut
  std::vector<Cp> cps;
  for (const char* r = s.c_str(); r < end;) {
    const size_t at = (size_t)(r - s.c_str());
    cps.push_back({utf8::next(r, end), at});
  }
  size_t k = 0;  // index of the first code point dropped
  while (k < cps.size() && cps[k].at < cut) ++k;
  auto space = [&](size_t i) { return cps[i].c == ' '; };
  // the word the cut is in (or the one right before it, when the cut is at a space)
  size_t ws = k;  // start of the last word kept (partly or wholly)
  while (ws > 0 && !space(ws - 1)) --ws;
  const bool inWord = k > 0 && k < cps.size() && !space(k - 1) && !space(k);
  size_t back = cut;  // where to cut instead
  bool move = false;
  if (inWord) {
    // the whole word (as written in s) holds a number: never show part of it
    size_t we = k;
    while (we < cps.size() && !space(we)) ++we;
    for (size_t i = ws; i < we; ++i) move |= numberPart(cps[i].c);
    if (move) back = cps[ws].at;
  }
  if (!move) {
    // a whole number kept, its unit (or the word after it) cut to under 3 letters: "5.8 M…", "5.8 …"
    const size_t keptOfWord = inWord ? k - ws : 0;
    size_t numEnd = inWord ? ws : k;  // the number word ends before this (spaces skipped)
    while (numEnd > 0 && space(numEnd - 1)) --numEnd;
    size_t numStart = numEnd;
    while (numStart > 0 && !space(numStart - 1)) --numStart;
    bool number = numEnd > numStart;
    for (size_t i = numStart; i < numEnd; ++i) number &= isDigitish(cps[i].c);
    if (number && keptOfWord < 3 && numEnd < k) {
      move = true;
      back = cps[numStart].at;
    }
  }
  if (move) {
    // drop the words from `back` on, then any number-holding word or separator left at the end: what followed
    // them was cut, so they would read as the whole value ("↑24°…" without its low)
    std::string head = s.substr(0, back);
    for (;;) {
      while (!head.empty() && head.back() == ' ') head.pop_back();
      const size_t sp = head.rfind(' ');
      const std::string last = sp == std::string::npos ? head : head.substr(sp + 1);
      bool drop = last == "\xC2\xB7" || last == "-" || last == "\xE2\x80\x94" || last == "|";
      for (const char* r = last.c_str(); !drop && *r;) drop = numberPart(utf8::next(r, last.c_str() + last.size()));
      if (!drop || sp == std::string::npos) break;
      head.erase(sp);
    }
    while (!head.empty() && (head.back() == ',' || head.back() == ':' || head.back() == ' ')) head.pop_back();
    if (utf8::count(head.c_str(), head.size()) >= 3) return head + "\xE2\x80\xA6";
  }
  return out + "\xE2\x80\xA6";
}

std::string firstThatFits(const Font& f, std::initializer_list<std::string> candidates, float maxW) {
  const std::string* last = nullptr;
  for (const std::string& c : candidates) {
    if (Canvas::measureText(f, c.c_str()) <= maxW) return c;
    last = &c;
  }
  return last ? ellipsizeWords(f, *last, maxW) : std::string();
}

}  // namespace suflet
