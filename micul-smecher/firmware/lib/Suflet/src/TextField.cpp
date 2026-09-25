#include "TextField.h"

#include "Font.h"

namespace suflet {

bool TextField::isSeparator(uint32_t cp) {
  switch (cp) {
    case ' ': case '\n': case '\t': case '.': case ',': case '?': case '!': case ';': case ':':
    case '(': case ')': case '"': case 0x201E: case 0x201D: case 0x201C: case 0x2026:
      return true;
    default:
      return false;
  }
}

bool TextField::blank() const {
  for (char c : s_)
    if (c != ' ' && c != '\n') return false;
  return true;
}

void TextField::recount() { len_ = utf8::count(s_.data(), s_.size()); }

void TextField::snapshot() {
  if (undo_.size() >= kUndo) undo_.erase(undo_.begin());
  undo_.push_back(s_);
}

bool TextField::undo() {
  if (undo_.empty()) return false;
  s_ = undo_.back();
  undo_.pop_back();
  recount();
  return true;
}

bool TextField::insert(uint32_t cp, bool snap) {
  if (len_ >= max_ || cp == 0) return false;
  cp = utf8::normalizeRo(cp);
  if (snap) snapshot();
  char b[4];
  s_.append(b, (size_t)utf8::encode(cp, b));
  ++len_;
  return true;
}

bool TextField::insert(const char* s, bool snap) {
  if (!s || !*s) return false;
  bool first = true, any = false;
  const char* p = s;
  while (*p) {
    const uint32_t cp = utf8::next(p);
    if (!insert(cp, snap && first)) break;
    first = false;
    any = true;
  }
  return any;
}

bool TextField::backspace(bool snap) {
  if (s_.empty()) return false;
  if (snap) snapshot();
  s_.resize(utf8::prevStart(s_.data(), s_.size()));
  --len_;
  return true;
}

bool TextField::deleteWord(bool snap) {
  if (s_.empty()) return false;
  if (snap) snapshot();
  size_t n = s_.size();
  while (n && (s_[n - 1] == ' ' || s_[n - 1] == '\n')) --n;
  while (n && s_[n - 1] != ' ' && s_[n - 1] != '\n') n = utf8::prevStart(s_.data(), n);
  s_.resize(n);
  recount();
  return true;
}

void TextField::replaceTail(size_t bytes, const std::string& with, bool snap) {
  if (bytes > s_.size()) bytes = s_.size();
  if (snap) snapshot();
  s_.resize(s_.size() - bytes);
  s_ += with;
  recount();
}

void TextField::set(const std::string& s, bool snap) {
  if (snap) snapshot();
  s_.clear();
  len_ = 0;
  const char* p = s.c_str();
  while (*p && len_ < max_) {
    char b[4];
    s_.append(b, (size_t)utf8::encode(utf8::normalizeRo(utf8::next(p)), b));
    ++len_;
  }
}

uint32_t TextField::last(int back) const {
  size_t n = s_.size();
  for (int i = 0; i < back && n; ++i) n = utf8::prevStart(s_.data(), n);
  if (!n) return 0;
  const char* p = s_.data() + utf8::prevStart(s_.data(), n);
  return utf8::next(p, s_.data() + n);
}

std::string TextField::currentWord() const {
  size_t n = s_.size();
  while (n) {
    const size_t st = utf8::prevStart(s_.data(), n);
    const char* p = s_.data() + st;
    if (isSeparator(utf8::next(p, s_.data() + n))) break;
    n = st;
  }
  return s_.substr(n);
}

std::vector<std::string> TextField::previousWords(size_t max) const {
  const std::string w = currentWord();
  const size_t end = s_.size() - w.size();
  std::vector<std::string> out;
  std::string cur;
  const char* p = s_.data();
  const char* e = s_.data() + end;
  while (p < e) {
    const char* q = p;
    const uint32_t cp = utf8::next(p, e);
    if (isSeparator(cp)) {
      if (!cur.empty()) out.push_back(cur);
      cur.clear();
    } else {
      cur.append(q, (size_t)(p - q));
    }
  }
  if (!cur.empty()) out.push_back(cur);
  if (out.size() > max) out.erase(out.begin(), out.end() - (long)max);
  return out;
}

}  // namespace suflet
