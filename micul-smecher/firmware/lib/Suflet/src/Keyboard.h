// SoulOS Keys v1: the "Round QWERTY" system keyboard (research/04 §1-12),
// drawn on the Canvas. Pure logic + rendering, no hardware: it takes touch
// events with coordinates (TouchGestures in Text mode) and gives back the
// committed text. The layout is specified in design pixels on the 466 px
// disc (below) and scaled to the real panel by its DisplayGeometry
// (setGeometry; 480 px on the 2.8" IPS board, where a key is ~6.6 mm wide).
//
//   y  64-128  text field (2 lines, caret line at the bottom)
//   y 134-180  suggestion bar [ left | bold middle | right ]
//   y 184-340  three rows of keys; y 346-398 ?123 | , | space | done
//
// v1 has: tap typing (commit on lift, slide to fix), shift / caps lock /
// auto-capitals, ?123 and #+= layers, long-press variant tray (a -> ă first),
// ⌫ with hold-repeat and word delete, ⌫-reverts-auto-change, undo, double
// space = ". ", EN+RO prediction chips and RO auto-diacritics.
// Not yet: swipe typing, the Gaussian tap decoder, trackpad, dictation.
#pragma once
#include <stdint.h>

#include <string>

#include "Canvas.h"
#include "Events.h"
#include "Geometry.h"
#include "Predictor.h"
#include "TextField.h"

namespace suflet {

enum class KbLayer : uint8_t { Abc, Num, Sym };
enum class KbShift : uint8_t { Off, Once, Lock };
enum class KbAction : uint8_t { Send, Save };  // amber ↑ or mint ✓
enum class KbResult : uint8_t { None, Commit, Cancel };

enum class KeyId : uint8_t { Char, Shift, Bksp, Layer, SymLayer, Space, Done };

struct Key {
  KeyId id = KeyId::Char;
  uint32_t cp = 0;         // Char: the character (lower case on the abc layer)
  int16_t cx = 0, x0 = 0, x1 = 0, y0 = 0;  // panel px; hit area [x0, x1) x [y0, y0 + rowH())
};

struct KbConfig {
  KbAction action = KbAction::Save;
  Lang uiLang = Lang::En;
  size_t maxChars = 500;
  const char* placeholder = "";
  const char* chips[3] = {nullptr, nullptr, nullptr};  // context chips for an empty field
  const char* undoLabel = "\xE2\x86\xB6 Undo";         // "↶ Undo"
};

class Keyboard {
 public:
  // Design-pixel constants (466 px disc); use the accessors for panel px.
  static constexpr int kRowH = 52;
  static constexpr int kFieldBottom = 130, kSugBottom = 182;

  void setGeometry(const DisplayGeometry& g);
  const DisplayGeometry& geometry() const { return g_; }
  int rowH() const { return rowH_; }

  void open(const KbConfig& cfg, const std::string& initial = "");
  void close() { open_ = false; }
  bool isOpen() const { return open_; }

  // ---- input -------------------------------------------------------------
  // Touch events in screen pixels (TouchDown / TouchMove / HoldStart /
  // TouchUp). Returns true when consumed (everything, while open).
  bool touch(const TouchEv& e);
  void update(float dt);  // hold-repeat, caret blink, fades
  bool poll(KbResult& r) {
    r = result_;
    result_ = KbResult::None;
    return r != KbResult::None;
  }
  const std::string& committed() const { return committed_; }
  void cancel();  // side button: keep the draft, report Cancel

  // ---- editing (what a tap on a key does; public for tests and scripts) --
  void typeChar(uint32_t cp);
  void typeText(const char* utf8);
  void backspace();
  void deleteWord();
  bool undo();
  void pressShift();
  void setLayer(KbLayer l);
  void pickSuggestion(int i);
  void done();

  // ---- queries -------------------------------------------------------------
  const TextField& field() const { return field_; }
  const std::string& text() const { return field_.text(); }
  KbShift shift() const { return shift_; }
  KbLayer layer() const { return layer_; }
  const Suggestion& suggestion(int i) const { return sug_[i]; }
  int keyCount() const { return nKeys_; }
  const Key& key(int i) const { return keys_[i]; }
  int hitKey(float x, float y) const;        // -1 outside the key rows
  int hitSuggestion(float x, float y) const;  // -1 outside the bar
  // Centre of the key that types cp on the current layer (case-insensitive).
  bool keyCenter(uint32_t cp, float& x, float& y) const;
  bool keyCenter(KeyId id, float& x, float& y) const;
  bool trayOpen() const { return tray_.open; }
  int traySelection() const { return tray_.sel; }
  const Predictor& predictor() const { return pred_; }
  Predictor& predictor() { return pred_; }

  // ---- rendering -----------------------------------------------------------
  Rect bounds() const { return g_.rect(0, 60, (int)DisplayGeometry::kDesignPx, 402); }
  bool changed() const { return changed_; }
  void render(Canvas& cv);  // clears bounds() and draws everything

 private:
  struct Tray {
    bool open = false;
    int n = 0, sel = -1, left = 0, top = 0;
    std::string items[6];
  };
  struct AutoChange {
    bool active = false;
    std::string before, orig, repl, after;
    size_t pos = 0;
    float t = 0;
  };
  void layout();
  void refresh();  // suggestions + layout after an edit
  void autoShift();
  void applyAuto();
  void activate(const Key& k);
  bool openTray(const Key& k);
  void trackTray(float x, float y);
  void touched() { blinkT_ = 0; changed_ = true; }
  // drawing helpers
  void drawField(Canvas& cv);
  void drawSuggestions(Canvas& cv);
  void drawKey(Canvas& cv, int i);
  void drawCallout(Canvas& cv, const Key& k);
  void drawTray(Canvas& cv);

  float S(float designPx) const { return g_.s(designPx); }
  int SI(float designPx) const { return g_.si(designPx); }

  DisplayGeometry g_;
  int rowH_ = kRowH, fieldBottom_ = kFieldBottom, sugBottom_ = kSugBottom;
  KbConfig cfg_;
  TextField field_;
  Predictor pred_;
  bool open_ = false;
  KbLayer layer_ = KbLayer::Abc;
  KbShift shift_ = KbShift::Off;
  Key keys_[40];
  int nKeys_ = 0;
  Suggestion sug_[3];
  KbResult result_ = KbResult::None;
  std::string committed_;
  AutoChange auto_;
  Tray tray_;
  // touch state
  enum class Zone : uint8_t { None, Field, Sug, Key } zone_ = Zone::None;
  int pressed_ = -1, sugDown_ = -1;
  bool bkspHeld_ = false, bkspRepeated_ = false;
  float bkspT_ = 0, bkspNext_ = 0;
  // time
  float t_ = 0, lastSpaceT_ = -10, lastShiftT_ = -10, blinkT_ = 0, undoChipUntil_ = -1;
  bool changed_ = true, caretOn_ = true;
};

}  // namespace suflet
