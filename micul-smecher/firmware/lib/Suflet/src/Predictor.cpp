#include "Predictor.h"

#include <string.h>

#include <algorithm>

#include "Font.h"
#include "WordListData.h"

namespace suflet {

namespace {

constexpr size_t kLex = sizeof(words::kLexicon) / sizeof(words::kLexicon[0]);
constexpr size_t kAutoN = sizeof(words::kAuto) / sizeof(words::kAuto[0]);
constexpr size_t kNextN = sizeof(words::kNext) / sizeof(words::kNext[0]);

std::string lowerStr(const std::string& w) {
  std::string out;
  const char* p = w.c_str();
  while (*p) {
    char b[4];
    out.append(b, (size_t)utf8::encode(utf8::lower(utf8::next(p)), b));
  }
  return out;
}

bool startsWith(const char* s, const std::string& pre) { return strncmp(s, pre.c_str(), pre.size()) == 0; }

}  // namespace

std::string Predictor::fold(const std::string& w) {
  std::string out;
  const char* p = w.c_str();
  while (*p) {
    const uint32_t cp = utf8::next(p);
    if (cp == '-' || cp == '\'' || cp == 0x2019) continue;
    char b[4];
    out.append(b, (size_t)utf8::encode(utf8::fold(cp), b));
  }
  return out;
}

std::string Predictor::matchCase(const std::string& w, const std::string& like) {
  if (like.empty() || w.empty()) return w;
  const char* p = like.c_str();
  const uint32_t c0 = utf8::next(p);
  if (utf8::lower(c0) == c0) return w;  // typed in lower case
  const char* q = w.c_str();
  const uint32_t w0 = utf8::next(q);
  char b[4];
  std::string out(b, (size_t)utf8::encode(utf8::upper(w0), b));
  out += q;
  return out;
}

bool Predictor::inLang(const std::string& f, Lang l) const {
  for (size_t i = 0; i < kLex; ++i)
    if (words::kLexicon[i].lang == (uint8_t)l && f == words::kLexicon[i].fold) return true;
  return false;
}

bool Predictor::roExact(const std::string& lw) const {
  for (size_t i = 0; i < kLex; ++i) {
    const WordEntry& e = words::kLexicon[i];
    if (e.lang == (uint8_t)Lang::Ro && e.exact && lw == e.word) return true;
  }
  return false;
}

bool Predictor::isWord(const std::string& w) const {
  const std::string lw = lowerStr(w);
  for (size_t i = 0; i < kLex; ++i)
    if (lw == words::kLexicon[i].word) return true;
  return false;
}

const char* Predictor::autoFor(const std::string& f) const {
  for (size_t i = 0; i < kAutoN; ++i)
    if (f == words::kAuto[i].fold) return words::kAuto[i].surface;
  return nullptr;
}

void Predictor::lock(const std::string& word) {
  const std::string f = fold(word);
  if (!locked(f)) locked_.push_back(f);
}

bool Predictor::locked(const std::string& word) const {
  const std::string f = fold(word);
  return std::find(locked_.begin(), locked_.end(), f) != locked_.end();
}

LangScore Predictor::score(const std::vector<std::string>& prev) const {
  LangScore s;
  const size_t from = prev.size() > 6 ? prev.size() - 6 : 0;
  for (size_t i = from; i < prev.size(); ++i) {
    const std::string f = fold(prev[i]);
    // English UI: only words that are unmistakably Romanian count ("la",
    // "mâine"), not diacritic-less look-alikes ("sa", "si").
    const bool r = uiLang == Lang::En ? roExact(lowerStr(prev[i])) : inLang(f, Lang::Ro);
    const bool e = inLang(f, Lang::En);
    if (r && !e) ++s.ro;
    if (e && !r) ++s.en;
  }
  s.pref = s.ro > s.en ? Lang::Ro : (s.en > s.ro ? Lang::En : uiLang);
  return s;
}

std::vector<std::string> Predictor::candidates(const std::string& word,
                                               const std::vector<std::string>& prev,
                                               size_t max) const {
  std::vector<std::pair<float, std::string>> out;
  const std::string f = fold(word);
  if (f.empty()) return {};
  const Lang pref = score(prev).pref;
  const char* a = autoFor(f);
  for (size_t i = 0; i < kLex; ++i) {
    const WordEntry& e = words::kLexicon[i];
    if (!startsWith(e.fold, f)) continue;
    float sc = 1.0f / (float)(e.rank + 8) * (e.lang == (uint8_t)pref ? 1.0f : 0.5f);
    if (f == e.fold) sc *= 3;
    if (a && strcmp(a, e.word) == 0) sc *= 5;
    const std::string w = matchCase(e.word, word);
    bool merged = false;
    for (auto& o : out)
      if (o.second == w) {
        if (sc > o.first) o.first = sc;
        merged = true;
      }
    if (!merged) out.push_back({sc, w});
  }
  std::stable_sort(out.begin(), out.end(),
                   [](const std::pair<float, std::string>& x, const std::pair<float, std::string>& y) {
                     return x.first > y.first;
                   });
  std::vector<std::string> r;
  for (size_t i = 0; i < out.size() && r.size() < max; ++i) r.push_back(out[i].second);
  return r;
}

std::string Predictor::autoForm(const std::string& word, const std::vector<std::string>& prev) const {
  if (word.empty()) return "";
  for (char c : word)  // plain ASCII letters only: never touch what has accents, digits, '-'
    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))) return "";
  const std::string f = fold(word);
  const char* a = autoFor(f);
  if (!a || locked(f)) return "";
  const LangScore s = score(prev);
  if (strchr(a, '\'')) {  // English contractions: dont -> don't, im -> I'm
    if (s.ro > s.en) return "";
    return strcmp(a, "I'm") == 0 ? std::string(a) : matchCase(a, word);
  }
  if (s.en > s.ro) return "";  // an English sentence: leave plain letters alone
  // no Romanian evidence yet: only in a Romanian UI, and never for words
  // that are English too ("in", "a")
  if (s.ro == 0 && (uiLang == Lang::En || inLang(f, Lang::En))) return "";
  return matchCase(a, word);
}

void Predictor::suggest(const std::string& word, const std::vector<std::string>& prev,
                        Suggestion out[3]) const {
  for (int i = 0; i < 3; ++i) out[i] = Suggestion();
  auto set = [&](int i, const std::string& v, bool bold, const std::string& label = "") {
    if (v.empty()) return;
    out[i].value = v;
    out[i].label = label.empty() ? v : label;
    out[i].bold = bold;
  };
  if (!word.empty()) {
    const std::vector<std::string> c = candidates(word, prev, 5);
    const std::string a = autoForm(word, prev);
    std::vector<std::string> rest;
    for (const std::string& x : c)
      if (x != word && x != a) rest.push_back(x);
    const std::string best = !a.empty() ? a : (isWord(word) ? word : (rest.empty() ? word : rest[0]));
    if (best == word) {
      set(0, rest.size() > 1 ? rest[1] : "", false);
      set(1, word, true);
      set(2, rest.empty() ? "" : rest[0], false);
    } else {
      set(0, word, false, "\xE2\x80\x9C" + word + "\xE2\x80\x9D");  // “literal”
      set(1, best, true);
      for (const std::string& x : rest)
        if (x != best) {
          set(2, x, false);
          break;
        }
    }
    return;
  }
  const Lang pref = score(prev).pref;
  const std::string last = prev.empty() ? std::string() : lowerStr(prev.back());
  const NextEntry* hit = nullptr;
  const NextEntry* dflt = nullptr;
  for (size_t i = 0; i < kNextN; ++i) {
    const NextEntry& n = words::kNext[i];
    if (n.lang != (uint8_t)pref) continue;
    if (!*n.prev) dflt = &n;
    else if (last == n.prev) hit = &n;
  }
  if (!hit) hit = dflt;
  if (!hit) return;
  set(0, hit->w[1], false);
  set(1, hit->w[0], true);
  set(2, hit->w[2], false);
}

}  // namespace suflet
