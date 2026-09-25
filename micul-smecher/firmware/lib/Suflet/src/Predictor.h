// On-device EN + RO word prediction and Romanian auto-diacritics
// (research/04 §5-6), v1: a small generated lexicon (tools/gen_words.py),
// prefix completion ranked by frequency and sentence language, next-word
// hints, and confident diacritic restoration (sa -> să, maine -> mâine) that
// only fires when the sentence is Romanian. No network, no learning yet.
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {

enum class Lang : uint8_t { En = 0, Ro = 1 };

struct WordEntry {
  const char* word;
  const char* fold;  // lower case, no diacritics, no hyphen/apostrophe
  uint16_t rank;     // 0 = most frequent
  uint8_t lang;      // Lang
  uint8_t exact;     // typing it exactly is evidence of Romanian (RO only)
};
struct AutoEntry {
  const char* fold;
  const char* surface;
};
struct NextEntry {
  uint8_t lang;
  const char* prev;  // "" = start of sentence / unknown
  const char* w[3];  // best first
};

struct Suggestion {
  std::string label;  // what the chip shows ("“helo”" for a literal non-word)
  std::string value;  // what picking it inserts ("" = empty slot)
  bool bold = false;  // what space will insert
  bool undo = false;  // the "↶ Undo" chip
  bool empty() const { return value.empty() && !undo; }
};

struct LangScore {
  int ro = 0, en = 0;
  Lang pref = Lang::En;
};

class Predictor {
 public:
  Lang uiLang = Lang::En;  // tie-break (EN is the default UI language)

  static std::string fold(const std::string& w);
  static std::string matchCase(const std::string& w, const std::string& like);

  // Language of the last 6 words.
  LangScore score(const std::vector<std::string>& prev) const;
  // Completions of a partial word, best first.
  std::vector<std::string> candidates(const std::string& word, const std::vector<std::string>& prev,
                                      size_t max = 4) const;
  // Replacement applied when the word is finished (space / punctuation), or
  // "" to leave it as typed. RO diacritics only for Romanian sentences.
  std::string autoForm(const std::string& word, const std::vector<std::string>& prev) const;
  // Three chips: [left, middle(bold), right] for the word being typed, or
  // next-word hints after a space.
  void suggest(const std::string& word, const std::vector<std::string>& prev, Suggestion out[3]) const;
  bool isWord(const std::string& w) const;  // in the lexicon, as written (lower case)

  // A word the user reverted once is never auto-changed again this session.
  void lock(const std::string& word);
  bool locked(const std::string& word) const;
  void clearLocks() { locked_.clear(); }

 private:
  bool inLang(const std::string& folded, Lang l) const;
  bool roExact(const std::string& lowerWord) const;
  const char* autoFor(const std::string& folded) const;
  std::vector<std::string> locked_;
};

}  // namespace suflet
