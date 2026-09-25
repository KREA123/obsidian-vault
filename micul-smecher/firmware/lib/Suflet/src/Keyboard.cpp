#include "Keyboard.h"

#include <math.h>
#include <string.h>

#include <vector>

namespace suflet {

namespace {

// ---- look (research/04 §11) -------------------------------------------------
constexpr Rgb kCream = pal::kEyeDay;
constexpr Rgb kCapLetter = Rgb::hex(0x1A1813);
constexpr Rgb kCapFn = Rgb::hex(0x26231B);
constexpr Rgb kCapPressed = Rgb::hex(0x4A4434);
constexpr Rgb kCallout = Rgb::hex(0x2E2A20);
constexpr Rgb kSugBest = Rgb::hex(0x1D1B16);
constexpr Rgb kAmber = Rgb::hex(0xFFB347);
constexpr Rgb kInk = Rgb::hex(0x16130C);  // glyphs on amber / mint caps

constexpr int kSlotX[3] = {26, 156, 316};
constexpr int kSlotW[3] = {124, 154, 124};
constexpr int kFieldW = 300;        // line width that fits the upper text line chord
constexpr int kBase1 = 89, kBase2 = 121;  // baselines of the two text lines
constexpr int kSugBase = 165;

// Long-press variants (research/04 §2); the Romanian letter comes first.
struct Variants {
  uint32_t cp;
  const char* items[6];
};
const Variants kVariants[] = {
    {'a', {"ă", "â", "à", "á", "ä", nullptr}},
    {'i', {"î", "8", "í", "ï", nullptr, nullptr}},
    {'s', {"ș", "š", "ß", nullptr, nullptr, nullptr}},
    {'t', {"ț", "5", nullptr, nullptr, nullptr, nullptr}},
    {'e', {"3", "é", "è", "ê", "ë", nullptr}},
    {'o', {"9", "ö", "ó", "ô", nullptr, nullptr}},
    {'u', {"7", "ü", "ú", nullptr, nullptr, nullptr}},
    {'c', {"ç", "č", "ć", nullptr, nullptr, nullptr}},
    {'n', {"ñ", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'q', {"1", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'w', {"2", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'r', {"4", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'y', {"6", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'p', {"0", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'.', {"…", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'-', {"–", nullptr, nullptr, nullptr, nullptr, nullptr}},
    {'"', {"„", "”", "«", "»", nullptr, nullptr}},
    {'\'', {"’", nullptr, nullptr, nullptr, nullptr, nullptr}},
};
const char* const kPunctTray[6] = {".", ",", "?", "!", "'", "-"};

std::string cpStr(uint32_t cp) {
  char b[4];
  return std::string(b, (size_t)utf8::encode(cp, b));
}

bool isLetter(uint32_t cp) {
  const uint32_t f = utf8::fold(cp);
  return f >= 'a' && f <= 'z';
}

// Baseline that centres a glyph on cy: lower-case letters on the x-height,
// everything else on the cap height, so a row of keys looks even.
int baselineFor(const Font& f, uint32_t cp, float cy) {
  const bool lowerLetter = isLetter(cp) && utf8::lower(cp) == cp;
  const Glyph* g = f.find(lowerLetter ? 'x' : 'H');
  return (int)lroundf(cy - (g->y + g->h * 0.5f));
}

// Signed distance to a polygon (Inigo Quilez, MIT), negative inside.
struct Poly {
  float v[16];
  int n = 0;
  void add(float x, float y) {
    v[2 * n] = x;
    v[2 * n + 1] = y;
    ++n;
  }
  float sd(float px, float py) const {
    float dx = px - v[0], dy = py - v[1];
    float d = dx * dx + dy * dy, s = 1;
    for (int i = 0, j = n - 1; i < n; j = i, ++i) {
      const float ex = v[2 * j] - v[2 * i], ey = v[2 * j + 1] - v[2 * i + 1];
      const float wx = px - v[2 * i], wy = py - v[2 * i + 1];
      const float h = clampf((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1);
      const float bx = wx - ex * h, by = wy - ey * h;
      const float bb = bx * bx + by * by;
      if (bb < d) d = bb;
      const bool c1 = py >= v[2 * i + 1], c2 = py < v[2 * j + 1], c3 = ex * wy > ey * wx;
      if ((c1 && c2 && c3) || (!c1 && !c2 && !c3)) s = -s;
    }
    return s * sqrtf(d);
  }
  void draw(Canvas& cv, bool filled, float th, Rgb c, float a) const {
    float x0 = v[0], y0 = v[1], x1 = v[0], y1 = v[1];
    for (int i = 1; i < n; ++i) {
      x0 = fminf(x0, v[2 * i]);
      x1 = fmaxf(x1, v[2 * i]);
      y0 = fminf(y0, v[2 * i + 1]);
      y1 = fmaxf(y1, v[2 * i + 1]);
    }
    const Poly p = *this;
    const float h = th * 0.5f;
    cv.fillSdf(
        x0 - h, y0 - h, x1 + h, y1 + h,
        [p, filled, h](float px, float py) { return filled ? p.sd(px, py) : fabsf(p.sd(px, py)) - h; }, c, a);
  }
};

// Greedy word wrap into lines no wider than maxW. Spaces stay with the word
// before them, a word longer than a line is broken between code points.
void wrap(const Font& f, const std::string& s, int maxW, std::vector<std::pair<size_t, size_t>>& lines) {
  lines.clear();
  size_t lineStart = 0, i = 0;
  int lineW16 = 0;
  const char* base = s.c_str();
  while (i < s.size()) {
    // next word: non-spaces followed by spaces
    size_t j = i;
    int w16 = 0;
    bool inSpaces = false;
    while (j < s.size()) {
      const char* p = base + j;
      const uint32_t cp = utf8::next(p);
      if (cp == ' ') inSpaces = true;
      else if (inSpaces) break;
      if (cp == '\n') {
        j = (size_t)(p - base);
        break;
      }
      w16 += f.find(cp)->adv16;
      j = (size_t)(p - base);
    }
    if (lineW16 > 0 && (lineW16 + w16) > maxW * 16) {
      lines.push_back({lineStart, i});
      lineStart = i;
      lineW16 = 0;
    }
    if (w16 > maxW * 16) {  // break a very long word
      size_t k = i;
      while (k < j) {
        const char* p = base + k;
        const uint32_t cp = utf8::next(p);
        const int a = f.find(cp)->adv16;
        if (lineW16 > 0 && lineW16 + a > maxW * 16) {
          lines.push_back({lineStart, k});
          lineStart = k;
          lineW16 = 0;
        }
        lineW16 += a;
        k = (size_t)(p - base);
      }
    } else {
      lineW16 += w16;
    }
    if (j > 0 && s[j - 1] == '\n') {
      lines.push_back({lineStart, j - 1});
      lineStart = j;
      lineW16 = 0;
    }
    i = j;
  }
  lines.push_back({lineStart, s.size()});
}

std::string fitText(const Font& f, const std::string& s, int maxW) {
  if (Canvas::measureText(f, s.c_str()) <= maxW) return s;
  const int ell = Canvas::measureText(f, "…");
  size_t n = s.size();
  while (n > 0 && Canvas::measureText(f, s.c_str(), (int)n) + ell > maxW) n = utf8::prevStart(s.c_str(), n);
  return s.substr(0, n) + "…";
}

}  // namespace

// ------------------------------------------------------------------ setup ---

void Keyboard::open(const KbConfig& cfg, const std::string& initial) {
  cfg_ = cfg;
  field_ = TextField(cfg.maxChars);
  field_.set(initial, false);
  pred_.uiLang = cfg.uiLang;
  pred_.clearLocks();
  open_ = true;
  layer_ = KbLayer::Abc;
  shift_ = KbShift::Off;
  result_ = KbResult::None;
  committed_.clear();
  auto_ = AutoChange();
  tray_ = Tray();
  zone_ = Zone::None;
  pressed_ = sugDown_ = -1;
  bkspHeld_ = bkspRepeated_ = false;
  lastSpaceT_ = lastShiftT_ = -10;
  undoChipUntil_ = -1;
  autoShift();
  refresh();
}

void Keyboard::layout() {
  nKeys_ = 0;
  auto put = [&](KeyId id, uint32_t cp, int cx, int y0, int w) {
    Key& k = keys_[nKeys_++];
    k.id = id;
    k.cp = cp;
    k.cx = (int16_t)cx;
    k.x0 = (int16_t)(cx - w / 2);
    k.x1 = (int16_t)(cx + w / 2);
    k.y0 = (int16_t)y0;
  };
  auto chars = [&](const char* s, int y0, int x0, int pitch) {
    int i = 0;
    const char* p = s;
    while (*p) put(KeyId::Char, utf8::next(p), x0 + pitch * i++, y0, pitch);
  };
  if (layer_ == KbLayer::Abc) {
    chars("qwertyuiop", 184, 35, 44);
    chars("asdfghjkl", 236, 45, 47);
    put(KeyId::Shift, 0, 56, 288, 46);
    chars("zxcvbnm", 288, 101, 44);
    put(KeyId::Bksp, 0, 410, 288, 46);
  } else if (layer_ == KbLayer::Num) {
    chars("1234567890", 184, 35, 44);
    chars("-/:;()€&@\"", 236, 35, 44);
    put(KeyId::SymLayer, 0, 64, 288, 58);
    chars(".,?!'", 288, 121, 56);
    put(KeyId::Bksp, 0, 402, 288, 58);
  } else {
    chars("[]{}#%^*+=", 184, 35, 44);
    chars("_\\|~<>$£„”", 236, 35, 44);
    put(KeyId::SymLayer, 0, 64, 288, 58);
    chars("…·°–«", 288, 121, 56);
    put(KeyId::Bksp, 0, 402, 288, 58);
  }
  put(KeyId::Layer, 0, 108, 346, 62);
  put(KeyId::Char, ',', 166, 346, 54);  // the mic slot is ',' until dictation lands
  put(KeyId::Space, ' ', 257, 346, 128);
  put(KeyId::Done, 0, 355, 346, 68);
}

void Keyboard::refresh() {
  if (undoChipUntil_ > t_) {
    for (int i = 0; i < 3; ++i) sug_[i] = Suggestion();
    sug_[1].undo = true;
    sug_[1].bold = true;
    sug_[1].label = cfg_.undoLabel;
  } else if (field_.blank()) {
    for (int i = 0; i < 3; ++i) {
      sug_[i] = Suggestion();
      if (cfg_.chips[i]) sug_[i].value = sug_[i].label = cfg_.chips[i];
    }
  } else {
    pred_.suggest(field_.currentWord(), field_.previousWords(), sug_);
  }
  layout();
  touched();
}

void Keyboard::autoShift() {
  if (shift_ == KbShift::Lock) return;
  const uint32_t a = field_.last(0), b = field_.last(1);
  if (field_.empty() || (a == ' ' && (b == '.' || b == '?' || b == '!'))) shift_ = KbShift::Once;
}

// ---------------------------------------------------------------- editing ---

void Keyboard::applyAuto() {
  const std::string w = field_.currentWord();
  if (w.empty()) return;
  const std::string a = pred_.autoForm(w, field_.previousWords());
  if (a.empty() || a == w) return;
  auto_.before = field_.text();
  field_.replaceTail(w.size(), a, false);
  auto_.active = true;
  auto_.orig = w;
  auto_.repl = a;
  auto_.pos = field_.text().size() - a.size();
  auto_.t = t_;
}

void Keyboard::typeChar(uint32_t cp) {
  if (!cp || field_.length() >= field_.maxChars()) return;
  const bool sep = TextField::isSeparator(cp);
  if (cp == ' ') {
    // two spaces within 450 ms after a word: ". " and a capital (iOS)
    const uint32_t a = field_.last(0), b = field_.last(1);
    if (t_ - lastSpaceT_ < 0.45f && a == ' ' && b && !TextField::isSeparator(b)) {
      field_.replaceTail(1, ". ");
      lastSpaceT_ = -10;
      auto_.active = false;
      autoShift();
      refresh();
      return;
    }
    lastSpaceT_ = t_;
  } else {
    lastSpaceT_ = -10;
  }
  field_.snapshot();  // one undo step per keystroke (auto-change included)
  auto_.active = false;
  if (sep) applyAuto();
  field_.insert(cp, false);
  if (auto_.active) auto_.after = field_.text();
  if (!sep && shift_ == KbShift::Once) shift_ = KbShift::Off;
  undoChipUntil_ = -1;
  autoShift();
  refresh();
}

void Keyboard::typeText(const char* s) {
  const char* p = s;
  while (*p) typeChar(utf8::next(p));
}

void Keyboard::backspace() {
  if (auto_.active && auto_.after == field_.text()) {
    // ⌫ right after an automatic change restores exactly what was typed,
    // and that word is not changed again this session
    const std::string rest = field_.text().substr(auto_.pos + auto_.repl.size());
    field_.set(auto_.before + rest);
    pred_.lock(auto_.orig);
    auto_.active = false;
    refresh();
    return;
  }
  if (field_.empty()) return;
  field_.backspace();
  auto_.active = false;
  if (shift_ == KbShift::Once && !field_.empty()) shift_ = KbShift::Off;
  autoShift();
  refresh();
}

void Keyboard::deleteWord() {
  if (!field_.deleteWord()) return;
  auto_.active = false;
  undoChipUntil_ = t_ + 5.0f;
  autoShift();
  refresh();
}

bool Keyboard::undo() {
  const bool ok = field_.undo();
  auto_.active = false;
  undoChipUntil_ = -1;
  autoShift();
  refresh();
  return ok;
}

void Keyboard::pressShift() {
  if (shift_ == KbShift::Off) {
    shift_ = KbShift::Once;
    lastShiftT_ = t_;
  } else if (shift_ == KbShift::Once) {
    shift_ = (t_ - lastShiftT_ < 0.3f) ? KbShift::Lock : KbShift::Off;
    lastShiftT_ = -10;
  } else {
    shift_ = KbShift::Off;
  }
  touched();
}

void Keyboard::setLayer(KbLayer l) {
  layer_ = l;
  layout();
  touched();
}

void Keyboard::pickSuggestion(int i) {
  if (i < 0 || i > 2 || sug_[i].empty()) return;
  const Suggestion s = sug_[i];
  if (s.undo) {
    undo();
    return;
  }
  auto_.active = false;
  if (field_.blank()) {  // a context chip
    field_.insert(s.value.c_str());
  } else {
    const std::string w = field_.currentWord();
    if (s.value == w) pred_.lock(w);  // picking the literal keeps it as typed
    field_.replaceTail(w.size(), s.value + " ");
  }
  if (shift_ == KbShift::Once) shift_ = KbShift::Off;
  autoShift();
  refresh();
}

void Keyboard::done() {
  if (field_.blank()) return;  // the done key is disabled while empty
  if (!TextField::isSeparator(field_.last(0))) {
    field_.snapshot();
    applyAuto();
  }
  std::string t = field_.text();
  while (!t.empty() && (t.back() == ' ' || t.back() == '\n')) t.pop_back();
  size_t b = 0;
  while (b < t.size() && (t[b] == ' ' || t[b] == '\n')) ++b;
  committed_ = t.substr(b);
  result_ = KbResult::Commit;
  open_ = false;
}

void Keyboard::cancel() {
  result_ = KbResult::Cancel;
  open_ = false;
}

// ------------------------------------------------------------------ touch ---

int Keyboard::hitKey(float x, float y) const {
  if (y < kSugBottom) return -1;
  const int rowY = y >= 342 ? 346 : (y >= 288 ? 288 : (y >= 236 ? 236 : 184));
  int best = -1;
  float bd = 1e9f;
  for (int i = 0; i < nKeys_; ++i) {
    const Key& k = keys_[i];
    if (k.y0 != rowY) continue;
    // the first and last key of a row own the hit area out to the rim
    const float d = x < k.x0 ? k.x0 - x : (x >= k.x1 ? x - k.x1 + 1 : 0);
    if (d < bd) {
      bd = d;
      best = i;
    }
  }
  return best;
}

int Keyboard::hitSuggestion(float x, float y) const {
  if (y < kFieldBottom || y >= kSugBottom) return -1;
  return x < 153 ? 0 : (x < 312 ? 1 : 2);
}

bool Keyboard::keyCenter(uint32_t cp, float& x, float& y) const {
  const uint32_t l = utf8::lower(cp);
  for (int i = 0; i < nKeys_; ++i) {
    const Key& k = keys_[i];
    if ((k.id == KeyId::Char || k.id == KeyId::Space) && utf8::lower(k.cp) == l) {
      x = k.cx;
      y = k.y0 + kRowH * 0.5f;
      return true;
    }
  }
  return false;
}

bool Keyboard::keyCenter(KeyId id, float& x, float& y) const {
  for (int i = 0; i < nKeys_; ++i) {
    if (keys_[i].id == id) {
      x = keys_[i].cx;
      y = keys_[i].y0 + kRowH * 0.5f;
      return true;
    }
  }
  return false;
}

void Keyboard::activate(const Key& k) {
  switch (k.id) {
    case KeyId::Char:
      typeChar(layer_ == KbLayer::Abc && shift_ != KbShift::Off ? utf8::upper(k.cp) : k.cp);
      break;
    case KeyId::Space: typeChar(' '); break;
    case KeyId::Shift: pressShift(); break;
    case KeyId::Bksp: backspace(); break;
    case KeyId::Layer: setLayer(layer_ == KbLayer::Abc ? KbLayer::Num : KbLayer::Abc); break;
    case KeyId::SymLayer: setLayer(layer_ == KbLayer::Num ? KbLayer::Sym : KbLayer::Num); break;
    case KeyId::Done: done(); break;
  }
}

bool Keyboard::openTray(const Key& k) {
  const char* const* items = nullptr;
  if (k.id == KeyId::Layer) {
    items = kPunctTray;
  } else if (k.id == KeyId::Char) {
    for (const Variants& v : kVariants)
      if (v.cp == k.cp) items = v.items;
  }
  if (!items) return false;
  Tray t;
  const bool up = layer_ == KbLayer::Abc && shift_ != KbShift::Off;
  std::string ro[6], other[6];
  int nro = 0, nother = 0;
  for (int i = 0; i < 6 && items[i]; ++i) {
    std::string s = items[i];
    if (up) {
      const char* p = s.c_str();
      s = cpStr(utf8::upper(utf8::next(p)));
    }
    const char* p = s.c_str();
    if (utf8::isRoDiacritic(utf8::next(p))) ro[nro++] = s;
    else other[nother++] = s;
  }
  // typing English: ă î ș ț move to the end of the tray
  const bool en = pred_.score(field_.previousWords()).pref == Lang::En && k.id == KeyId::Char;
  std::string ordered[6];
  int n = 0;
  if (en) {
    for (int i = 0; i < nother; ++i) ordered[n++] = other[i];
    for (int i = 0; i < nro; ++i) ordered[n++] = ro[i];
  } else {
    for (int i = 0; i < nro; ++i) ordered[n++] = ro[i];
    for (int i = 0; i < nother; ++i) ordered[n++] = other[i];
  }
  // The tray grows toward the centre; its first item sits under the finger.
  const bool right = k.cx <= 233;
  t.n = n;
  t.top = k.y0 - 64;
  int left = right ? k.cx - 22 : k.cx - 22 - 44 * (n - 1);
  if (left < 16) left = 16;
  if (left + 44 * n > 450) left = 450 - 44 * n;
  t.left = left;
  for (int i = 0; i < n; ++i) t.items[right ? i : n - 1 - i] = ordered[i];
  t.sel = right ? 0 : n - 1;
  t.open = true;
  tray_ = t;
  touched();
  return true;
}

void Keyboard::trackTray(float x, float y) {
  int sel = (int)floorf((x - tray_.left) / 44.0f);
  if (sel < 0) sel = 0;
  if (sel >= tray_.n) sel = tray_.n - 1;
  // lifting far away from the tray cancels
  const float cy = tray_.top + 31.0f;
  if (fabsf(y - cy) > 95.0f || x < tray_.left - 40 || x > tray_.left + 44 * tray_.n + 40) sel = -1;
  if (sel != tray_.sel) {
    tray_.sel = sel;
    touched();
  }
}

bool Keyboard::touch(const TouchEv& e) {
  if (!open_) return false;
  const float x = e.x, y = e.y;
  switch (e.e) {
    case Ev::TouchDown:
      tray_.open = false;
      pressed_ = sugDown_ = -1;
      bkspHeld_ = bkspRepeated_ = false;
      if (y < kFieldBottom) {
        zone_ = Zone::Field;
      } else if (y < kSugBottom) {
        zone_ = Zone::Sug;
        sugDown_ = hitSuggestion(x, y);
      } else {
        zone_ = Zone::Key;
        pressed_ = hitKey(x, y);
        if (pressed_ >= 0 && keys_[pressed_].id == KeyId::Bksp) {
          bkspHeld_ = true;
          bkspT_ = 0;
          bkspNext_ = 0.45f;
        }
      }
      touched();
      return true;
    case Ev::TouchMove:
      if (tray_.open) {
        trackTray(x, y);
      } else if (zone_ == Zone::Key) {
        const int k = y >= kSugBottom ? hitKey(x, y) : -1;  // slide to fix the key
        if (k != pressed_) {
          pressed_ = k;
          if (k < 0 || keys_[k].id != KeyId::Bksp) bkspHeld_ = false;
          touched();
        }
      }
      return true;
    case Ev::HoldStart:
      if (zone_ == Zone::Key && pressed_ >= 0 && !tray_.open) openTray(keys_[pressed_]);
      return true;
    case Ev::TouchUp: {
      if (tray_.open) {
        if (tray_.sel >= 0) {
          auto_.active = false;
          typeText(tray_.items[tray_.sel].c_str());
        }
        tray_.open = false;
      } else if (zone_ == Zone::Key && pressed_ >= 0) {
        const Key k = keys_[pressed_];
        if (!(k.id == KeyId::Bksp && bkspRepeated_)) activate(k);
      } else if (zone_ == Zone::Sug) {
        const int s = hitSuggestion(x, y);
        if (s >= 0 && s == sugDown_) pickSuggestion(s);
      }
      zone_ = Zone::None;
      pressed_ = sugDown_ = -1;
      bkspHeld_ = false;
      touched();
      return true;
    }
    default:
      return true;  // taps, holds, strokes over the keyboard are all ours
  }
}

void Keyboard::update(float dt) {
  t_ += dt;
  blinkT_ += dt;
  const bool on = fmodf(blinkT_, 1.0f) < 0.5f;
  if (on != caretOn_) {
    caretOn_ = on;
    changed_ = true;
  }
  if (bkspHeld_ && pressed_ >= 0 && keys_[pressed_].id == KeyId::Bksp) {
    // hold ⌫: repeat at 12/s after 450 ms, whole words at 6/s after 1.2 s
    bkspT_ += dt;
    while (bkspT_ >= bkspNext_) {
      bkspRepeated_ = true;
      if (bkspT_ < 1.2f) {
        backspace();
        bkspNext_ += 1.0f / 12.0f;
      } else {
        deleteWord();
        bkspNext_ += 1.0f / 6.0f;
      }
    }
  }
  if (auto_.active && t_ - auto_.t < 1.1f) changed_ = true;  // underline fade
  if (undoChipUntil_ > 0 && t_ >= undoChipUntil_) {
    undoChipUntil_ = -1;
    refresh();
  }
}

// -------------------------------------------------------------- rendering ---

void Keyboard::drawField(Canvas& cv) {
  const Font& f = fonts::text();
  const std::string& s = field_.text();
  int caretX, caretBase = kBase2;
  if (s.empty()) {
    const int w = Canvas::measureText(f, cfg_.placeholder);
    cv.drawText(f, 233.0f + 3, kBase2, cfg_.placeholder, kCream, 0.38f, Align::Center);
    caretX = 233 - w / 2 - 3;
  } else {
    std::vector<std::pair<size_t, size_t>> lines;
    wrap(f, s, kFieldW, lines);
    const int n = (int)lines.size();
    int lx[2] = {0, 0};
    for (int k = 0; k < 2 && k < n; ++k) {
      const auto& L = lines[n - 1 - k];
      const int base = k == 0 ? kBase2 : kBase1;
      const int w = Canvas::measureText(f, s.c_str() + L.first, (int)(L.second - L.first));
      lx[k] = 233 - w / 2;
      cv.drawText(f, (float)lx[k], base, s.c_str() + L.first, kCream, 0.95f, Align::Left, nullptr,
                  (int)(L.second - L.first));
      if (k == 0) caretX = lx[0] + w + 1;
      // the mint underline under an automatic change (fades over 600 ms)
      if (auto_.active && auto_.after == s && auto_.pos >= L.first && auto_.pos < L.second) {
        const float age = t_ - auto_.t;
        const float a = age < 0.4f ? 1.0f : 1.0f - (age - 0.4f) / 0.6f;
        if (a > 0) {
          const int ux0 = lx[k] + Canvas::measureText(f, s.c_str() + L.first, (int)(auto_.pos - L.first));
          const int ux1 = ux0 + Canvas::measureText(f, auto_.repl.c_str());
          cv.roundRect((float)ux0, base + 5.0f, (float)ux1, base + 7.0f, 1, pal::kMint, a);
        }
      }
    }
  }
  if (caretOn_) cv.roundRect((float)caretX, caretBase - 22.0f, caretX + 3.0f, caretBase + 6.0f, 1.5f, pal::kIce);
}

void Keyboard::drawSuggestions(Canvas& cv) {
  const Font& f = fonts::small();
  const bool chips = field_.blank() && !(undoChipUntil_ > t_);
  for (int i = 0; i < 3; ++i) {
    const Suggestion& sg = sug_[i];
    if (sg.empty()) continue;
    const float x0 = (float)kSlotX[i], x1 = x0 + kSlotW[i];
    if (sg.bold || chips) cv.roundRect(x0 + 2, 137, x1 - 2, 179, 20, kSugBest);
    const std::string label = fitText(f, sg.label, kSlotW[i] - 14);
    const Rgb mint = pal::kMint;
    cv.drawText(f, (x0 + x1) * 0.5f, kSugBase, label.c_str(), kCream, sg.bold || chips ? 1.0f : 0.72f,
                Align::Center, sg.undo ? nullptr : &mint);
  }
  if (!chips && !(undoChipUntil_ > t_)) {
    cv.segment(153, 147, 153, 169, 1.5f, kCream, 0.18f);
    cv.segment(312, 147, 312, 169, 1.5f, kCream, 0.18f);
  }
}

void Keyboard::drawKey(Canvas& cv, int i) {
  const Key& k = keys_[i];
  const float x0 = k.x0 + 2.0f, x1 = k.x1 - 2.0f, y0 = k.y0 + 3.0f, y1 = k.y0 + kRowH - 3.0f;
  const float cx = k.cx, cy = (y0 + y1) * 0.5f;
  const bool pressed = i == pressed_ && !tray_.open;
  const bool fn = k.id != KeyId::Char;
  const bool empty = field_.blank();
  Rgb cap = pressed ? kCapPressed : (fn ? kCapFn : kCapLetter);
  if (k.id == KeyId::Done && !empty) cap = cfg_.action == KbAction::Send ? kAmber : pal::kMint;
  if (k.id == KeyId::Shift && shift_ != KbShift::Off && !pressed) cap = kCapPressed;
  cv.roundRect(x0, y0, x1, y1, 9, cap);
  const Font& tf = fonts::text();
  const Font& sf = fonts::small();
  switch (k.id) {
    case KeyId::Char: {
      const uint32_t cp = layer_ == KbLayer::Abc && shift_ != KbShift::Off ? utf8::upper(k.cp) : k.cp;
      const std::string s = cpStr(cp);
      cv.drawText(tf, cx, baselineFor(tf, cp, cy), s.c_str(), kCream, 0.95f, Align::Center);
      break;
    }
    case KeyId::Space: {
      const char* label = cfg_.uiLang == Lang::Ro ? "RO · EN" : "EN · RO";
      cv.drawText(sf, cx, baselineFor(sf, 'H', cy), label, kCream, 0.38f, Align::Center);
      break;
    }
    case KeyId::Layer:
    case KeyId::SymLayer: {
      const char* label = k.id == KeyId::Layer ? (layer_ == KbLayer::Abc ? "?123" : "ABC")
                                               : (layer_ == KbLayer::Num ? "#+=" : "123");
      cv.drawText(sf, cx, baselineFor(sf, 'H', cy), label, kCream, 0.8f, Align::Center);
      break;
    }
    case KeyId::Shift: {
      Poly p;  // ⇧
      p.add(cx, cy - 11);
      p.add(cx + 10, cy);
      p.add(cx + 5, cy);
      p.add(cx + 5, cy + 8);
      p.add(cx - 5, cy + 8);
      p.add(cx - 5, cy);
      p.add(cx - 10, cy);
      p.draw(cv, shift_ != KbShift::Off, 2.2f, kCream, shift_ != KbShift::Off ? 1.0f : 0.8f);
      if (shift_ == KbShift::Lock) cv.roundRect(cx - 6, cy + 11, cx + 6, cy + 13.5f, 1, kCream);
      break;
    }
    case KeyId::Bksp: {
      Poly p;  // ⌫
      p.add(cx - 14, cy);
      p.add(cx - 6, cy - 9);
      p.add(cx + 13, cy - 9);
      p.add(cx + 13, cy + 9);
      p.add(cx - 6, cy + 9);
      p.draw(cv, false, 2.2f, kCream, 0.8f);
      cv.segment(cx - 1, cy - 4, cx + 7, cy + 4, 2.2f, kCream, 0.8f);
      cv.segment(cx - 1, cy + 4, cx + 7, cy - 4, 2.2f, kCream, 0.8f);
      break;
    }
    case KeyId::Done: {
      const Rgb ink = empty ? kCream : kInk;
      const float a = empty ? 0.3f : 1.0f;
      if (cfg_.action == KbAction::Send) {  // ↑
        cv.segment(cx, cy + 10, cx, cy - 9, 3.2f, ink, a);
        cv.segment(cx - 8, cy - 1, cx, cy - 10, 3.2f, ink, a);
        cv.segment(cx + 8, cy - 1, cx, cy - 10, 3.2f, ink, a);
      } else {  // ✓
        cv.segment(cx - 10, cy + 1, cx - 3, cy + 8, 3.2f, ink, a);
        cv.segment(cx - 3, cy + 8, cx + 10, cy - 7, 3.2f, ink, a);
      }
      break;
    }
  }
}

void Keyboard::drawCallout(Canvas& cv, const Key& k) {
  const float x = clampf(k.cx - 29.0f, 30.0f, 378.0f), y = k.y0 - 64.0f;
  cv.roundRect(x - 1.5f, y - 1.5f, x + 59.5f, y + 67.5f, 13, kCream.scaled(0.35f));
  cv.roundRect(x, y, x + 58, y + 66, 12, kCallout);
  const uint32_t cp = layer_ == KbLayer::Abc && shift_ != KbShift::Off ? utf8::upper(k.cp) : k.cp;
  const Font& lf = fonts::large();
  cv.drawText(lf, x + 29, baselineFor(lf, cp, y + 33), cpStr(cp).c_str(), kCream, 1.0f, Align::Center);
}

void Keyboard::drawTray(Canvas& cv) {
  const float x0 = tray_.left - 6.0f, x1 = tray_.left + 44.0f * tray_.n + 6, y0 = (float)tray_.top,
              y1 = tray_.top + 62.0f;
  cv.roundRect(x0 - 1.5f, y0 - 1.5f, x1 + 1.5f, y1 + 1.5f, 15, kCream.scaled(0.35f));
  cv.roundRect(x0, y0, x1, y1, 14, kCallout);
  const Font& lf = fonts::large();
  for (int i = 0; i < tray_.n; ++i) {
    const float cx = tray_.left + 44.0f * i + 22;
    if (i == tray_.sel) cv.roundRect(cx - 21, y0 + 5, cx + 21, y1 - 5, 10, kCapPressed);
    const char* p = tray_.items[i].c_str();
    const uint32_t cp = utf8::next(p);
    cv.drawText(lf, cx, baselineFor(lf, cp, (y0 + y1) * 0.5f), tray_.items[i].c_str(), kCream, 1.0f,
                Align::Center);
  }
}

void Keyboard::render(Canvas& cv) {
  const Rect b = bounds();
  cv.fillRect(b, pal::kBlack);
  cv.markDirty(b);
  drawField(cv);
  drawSuggestions(cv);
  for (int i = 0; i < nKeys_; ++i) drawKey(cv, i);
  if (tray_.open) drawTray(cv);
  else if (pressed_ >= 0 && keys_[pressed_].id == KeyId::Char && zone_ == Zone::Key)
    drawCallout(cv, keys_[pressed_]);
  changed_ = false;
}

}  // namespace suflet
