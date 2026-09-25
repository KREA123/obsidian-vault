// The text being written: a UTF-8 buffer with the caret at the end, delete
// by code point (so ș is one key press, not two bytes) and undo.
// Hardware-free, used by the Keyboard and unit-tested on the PC.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {

class TextField {
 public:
  explicit TextField(size_t maxChars = 500) : max_(maxChars) {}

  const std::string& text() const { return s_; }
  size_t length() const { return len_; }  // in code points
  size_t maxChars() const { return max_; }
  void setMaxChars(size_t n) { max_ = n; }
  bool empty() const { return s_.empty(); }
  bool blank() const;  // empty or only spaces
  size_t caret() const { return s_.size(); }  // byte index; always at the end (v1)

  // Every edit below records an undo step (up to kUndo) unless snap=false.
  bool insert(uint32_t cp, bool snap = true);             // false when full
  bool insert(const char* utf8, bool snap = true);        // cedilla ş ţ -> ș ț
  bool backspace(bool snap = true);                       // one code point
  bool deleteWord(bool snap = true);                      // trailing spaces + word
  void replaceTail(size_t bytes, const std::string& with, bool snap = true);
  void set(const std::string& s, bool snap = true);
  void clear(bool snap = true) { set(std::string(), snap); }
  bool undo();
  bool canUndo() const { return !undo_.empty(); }
  void snapshot();

  // The word being typed (after the last separator) and the words before it.
  std::string currentWord() const;
  std::vector<std::string> previousWords(size_t max = 6) const;
  // Last code point (0 when empty) and the one before it.
  uint32_t last(int back = 0) const;

  static bool isSeparator(uint32_t cp);
  static constexpr size_t kUndo = 32;

 private:
  void recount();
  std::string s_;
  size_t len_ = 0, max_;
  std::vector<std::string> undo_;
};

}  // namespace suflet
