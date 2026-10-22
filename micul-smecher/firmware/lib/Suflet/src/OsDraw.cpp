// SoulOS on the device: what each screen shows. Design language "SoulOS Alive" (os/DESIGN-ALIVE.md, 1.9):
// standby is the eyes alone on pure black; every app screen has the eyes in one slot at the top and its content
// in the safe circle under them, round-native: flat pebbles in the born palette, pills, lists as wheels
// (OsScreens.cpp), titles in a capsule on the rim, the brand faces (Bricolage Grotesque, Martian Mono tags).
// State colours keep their meaning (mint done, amber Claude / needs you, ice listening). Layout in design pixels
// of the 466 px disc, scaled by DisplayGeometry to the 480 px panel.
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "TextFit.h"
#include "Os.h"
#include "QrImage.h"

namespace suflet {

using namespace eyes;

static const Rgb kCream = Rgb::hex(0xFBF4E3), kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4),
                 kIce = Rgb::hex(0x9FC6FF);
static const float kDim = 0.82f, kFaint = 0.66f;  // SoulOS Alive: ink2 / ink3 (what you must read is >= 80 %)

enum : int {
  IdNext = 1,
  IdType,
  IdNew,
  IdSnooze,
  IdStop,
  IdPause,
  IdDelete,
  IdSetup,
  IdStopSetup,
  IdForget,
  IdName,
  IdLater,
  IdCenter,
  IdInbox,
  IdAccept,
  IdReject,
  IdHotspot,
  IdHotspotType,
  IdLook,         // My SOUL: Look (the births, the bodies)
  IdAllow,        // Claude asks: Allow / Deny (68 px buttons)
  IdDeny,
  IdRow = 100,
};

static const char* const kNames[] = {"Pixel", "Miso", "Luna", "Bobo", "Nori", "Kiki", "Tofu", "Zuzu",
                                     "Mochi", "Iris", "Pip",  "Sol",  "Dodo", "Fifi", "Mura", "Bean"};

static const Font& fontOf(int i, bool large) {
  if (large) ++i;
  switch (i) {
    case 0: return fonts::caption();
    case 1: return fonts::body();
    default: return fonts::title();
  }
}

static std::string ellipsize(const Font& f, const std::string& s, float maxW) { return ellipsizeWords(f, s, maxW); }

static std::string upperAscii(const std::string& s) {  // Martian Mono tags: RARE · #098 / 120
  std::string o = s;
  for (char& c : o)
    if (c >= 'a' && c <= 'z') c = (char)(c - 32);
  return o;
}

static std::string daysText(uint8_t d, bool ro) {
  if (d == 0) return ro ? "o dată" : "once";
  if (d == 0x7F) return ro ? "zilnic" : "daily";
  if (d == 0x1F) return ro ? "în zilele lucrătoare" : "weekdays";
  if (d == 0x60) return ro ? "în weekend" : "weekend";
  static const char* const en[] = {"Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"};
  static const char* const r[] = {"L", "Ma", "Mi", "J", "V", "S", "D"};
  std::string s;
  for (int i = 0; i < 7; ++i)
    if (d & (1 << i)) s += std::string(s.empty() ? "" : " ") + (ro ? r[i] : en[i]);
  return s;
}

// the days in as few letters as they can be said (SOUL S's alarm rows): Mo–Fr, Sa–Su, daily, once, Mo We Fr
static std::string daysShort(uint8_t d, bool ro) {
  if (d == 0x1F) return ro ? "L\xE2\x80\x93V" : "Mo\xE2\x80\x93" "Fr";
  if (d == 0x60) return ro ? "S\xE2\x80\x93" "D" : "Sa\xE2\x80\x93Su";
  return daysText(d, ro);
}

// ---------------------------------------------------------------- items ---

void Os::buildItems(std::vector<Item>& out) const {
  out.clear();
  const bool R = ro();
  auto add = [&](int id, float x, float y, float w, float h, const std::string& label, Rgb c, int font, bool ul,
                 float alpha = 1) {
    Item it;
    it.id = id;
    it.x = x;
    it.y = y;
    it.w = w;
    it.h = h;
    it.label = label;
    it.color = c;
    it.font = (uint8_t)font;
    it.underline = ul;
    it.alpha = alpha;
    out.push_back(it);
  };
  switch (view_) {
    case View::Boot:
      if (bootStep_ == BootStep::Name) {
        add(-1, 233, L(170, 166), 0, 0, R ? "Cum mă cheamă?" : "What's my name?", kCream, 1, false);
        for (int i = 0; i < 3; ++i) {
          const int k = (int)(((birth_.seed >> (i * 5)) + (uint32_t)i * 5u) % 16u);
          if (sGlass()) add(IdRow + i, 233 + (i - 1) * 120.0f, 244, 100, 50, kNames[k], kCream, 1, true);  // S: one row
          else add(IdRow + i, 233, 226 + i * 56, 220, 50, kNames[k], kCream, 1, true);
        }
        add(IdType, 233, L(394, 330), 230, 48, R ? "Scrie un nume" : "Type a name", kCream, 0, true, kDim);
      } else if (bootStep_ == BootStep::Brain) {
        add(-1, 233, 146, 0, 0, R ? "Cine mă ajută să gândesc?" : "Who helps me think?", kCream, 1, false);
        static const AiMode kModes[] = {AiMode::Cloud, AiMode::Claude, AiMode::ChatGpt, AiMode::None};
        const char* labels[] = {R ? "Conectează Claude" : "Connect Claude", R ? "Claude · cheia ta" : "Claude · your key",
                                R ? "ChatGPT · cheia ta" : "ChatGPT · your key", R ? "Fără AI" : "No AI"};
        // SOUL S: the four as a 2 x 2 grid of shorter words (four 68 px rows do not fit under the question)
        const char* labelsS[] = {R ? "Claude-ul tău" : "Your Claude", R ? "Cheie Claude" : "Claude key",
                                 R ? "Cheie ChatGPT" : "ChatGPT key", R ? "Fără AI" : "No AI"};
        for (int i = 0; i < 4; ++i) {
          const bool sel = aiMode() == kModes[i];
          if (sGlass()) add(IdRow + i, 233 + (i % 2 ? 100.0f : -100.0f), 222 + (i / 2) * 78.0f, 180, 46, labelsS[i], sel ? kMint : kCream, 0, true, sel ? 1 : kDim);
          else add(IdRow + i, 233, 186 + i * 50, 290, 46, labels[i], sel ? kMint : kCream, 0, true, sel ? 1 : kDim);
        }
        add(IdNext, 233, L(412, 402), 150, 48, R ? "Mai departe ›" : "Next ›", kCream, 0, true);
      }
      break;
    case View::Launcher: break;  // SoulOS Alive: the dial's pebbles take the taps (Os::dialTap)
    case View::Talk:
      if (!listening_) add(IdType, 233, 350, 240, 52, aiMode() == AiMode::None ? (R ? "Scrie" : "Type") : (R ? "Scrie-i lui " : "Write to ") + std::string(aiMode() == AiMode::ChatGpt ? "ChatGPT" : aiMode() == AiMode::Cloud || aiMode() == AiMode::Claude || aiMode() == AiMode::Bridge ? "Claude" : "SOUL"), kCream, 0, true);
      break;
    case View::Alarms:
    case View::Notes:
    case View::Settings:
    case View::AiMode: break;  // wheels (OsScreens.cpp): every row, "+ New" and "Forget keys" too
    case View::Ringing:
      if (timerRinging_) {
        add(IdStop, 233, L(376, 340), 150, 56, R ? "Oprește" : "Stop", kMint, 1, true);
      } else {  // (S: higher and in the caption face, inside the ringing ring at r 214)
        add(IdSnooze, 162, L(376, 340), 132, 56, R ? "Amână 5" : "Snooze 5", kCream, sGlass() ? 0 : 1, true);
        add(IdStop, 306, L(376, 340), 124, 56, R ? "Oprește" : "Stop", kMint, sGlass() ? 0 : 1, true);
      }
      break;
    case View::Timer:
      if (timerRun_) {
        add(IdPause, 164, 334, 128, 52, timerPaused_ ? (R ? "Pornește" : "Resume") : (R ? "Pauză" : "Pause"), kCream, 0, true, kDim);
        add(IdStop, 302, 334, 128, 52, R ? "Oprește" : "Stop", kAmber, 0, true);
      } else {
        static const char* const kP[] = {"1", "3", "5", "10", "25"};
        // the presets: 58 px discs on M; S: a 6.4 mm target each (Density.h), 76 px apart
        const float d = L(58, dens_.targetDesign()), step = L(66, d + 8);
        for (int i = 0; i < 5; ++i) add(IdRow + i, 233 + (i - 2) * step, 300, d, d, kP[i], kCream, 1, false);
      }
      break;
    case View::NoteView:
      add(IdType, 164, L(352, 356), 128, 52, R ? "Editează" : "Edit", kCream, 0, true);
      add(IdDelete, 302, L(352, 356), 128, 52, R ? "Șterge" : "Delete", kAmber, 0, true);
      break;
    case View::Bridge:
      add(IdNew, 166, L(376, 372), 128, 52, R ? "Cod nou" : "New code", kCream, 0, true);
      if (net_.bridgePaired || net_.bridgeOnline) add(IdForget, 302, L(376, 372), 120, 52, R ? "Uită" : "Forget", kAmber, 0, true);
      break;
    case View::Wifi:
      if (net_.portal) {
        add(IdStopSetup, 233, L(406, 398), 130, 48, R ? "Gata" : "Done", kCream, 0, true);
      } else if (page_ == 1) {  // the phone's hotspot: how-to, then type it here or use the phone page
        add(IdHotspotType, 156, L(352, 342), 120, 50, R ? "Scrie-l" : "Type it", kCream, 0, true);
        add(IdSetup, 312, L(352, 342), 150, 50, R ? "Din telefon" : "From phone", kCream, 0, true, kDim);
      } else if (sGlass()) {  // SOUL S: three 68 px pills under the state, in shorter words
        add(IdHotspot, 233, 254, 300, 50, R ? "Hotspotul telefonului" : "Phone hotspot", kAmber, 0, true);
        add(IdSetup, 233, 328, 260, 50, R ? "Din telefon" : "Set up by phone", kCream, 0, true);
        if (net_.configured) add(IdForget, 233, 402, 186, 48, R ? "Uită (ține)" : "Forget (hold)", kAmber, 0, true, kDim);
      } else {
        add(IdHotspot, 233, 300, 300, 50, R ? "Adaugă hotspotul telefonului" : "Add my phone's hotspot", kAmber, 0, true);
        add(IdSetup, 233, 354, 260, 50, R ? "Configurează din telefon" : "Set up from a phone", kCream, 0, true);
        if (net_.configured)
          add(IdForget, 233, 406, 186, 48, R ? "Uită Wi-Fi (ține)" : "Forget Wi-Fi (hold)", kAmber, 0, true, kDim);
      }
      break;
    case View::MySoul:
      if (page_ == 1) break;  // Look (OsAlive.cpp: lookTap)
      add(IdName, 233, L(214, 196), 260, L(46, dens_.targetDesign()), set_.name, kCream, 2, false);
      add(IdLook, 172, L(326, 358), 110, 52, R ? "Privire" : "Look", kCream, 0, true);
      add(IdType, 300, L(326, 358), 128, 52, R ? "Redenumește" : "Rename", kCream, 0, true, kDim);
      break;
    case View::Claude:
      if (claude_.prompt && !claude_.passkey) {  // Claude asks: two big buttons, 68 px
        const Density::Ask& q = dens_.ask;
        add(IdAllow, 233 - q.btnDx, q.btnY, q.btnW, q.btnH, R ? "Da" : "Allow", kMint, 1, true);
        add(IdDeny, 233 + q.btnDx, q.btnY, q.btnW, q.btnH, R ? "Nu" : "Deny", kAmber, 1, true);
      } else if (net_.relay && !claude_.passkey) {
        add(IdInbox, 233, 318, 250, 52, R ? "Scrie-i lui Claude" : "Write to Claude", kCream, 0, true);
      }
      break;
    case View::Pair:
      if (!net_.confirmPid.empty() && !net_.paired) {  // "Pair with Ana?" answered by a touch only
        add(IdAccept, 164, L(330, 336), 128, 54, R ? "Da, leagă" : "Yes, pair", kMint, 0, true);
        add(IdReject, 302, L(330, 336), 120, 54, R ? "Nu" : "No", kAmber, 0, true);
      } else if (!net_.configured || (!net_.connected && !net_.connecting)) {
        add(IdSetup, 233, 330, 260, 52, R ? "Configurează din telefon" : "Set up from a phone", kCream, 0, true);
      }
      break;
    case View::Memory: buildMemoryItems(out); break;  // OsMemory.cpp
    case View::Answer:
      if (acceptMode_) {
        add(IdAccept, 164, L(356, 350), 128, 52, R ? "Acceptă" : "Accept", kMint, 0, true);
        add(IdReject, 302, L(356, 350), 120, 52, R ? "Nu" : "No", kAmber, 0, true);
      } else {
        buildAppsItems(out);  // quick replies on a card from an app / your AI
      }
      break;
    default: buildAppsItems(out); break;
  }
  wheelItems(out);  // a list: its rows (OsScreens.cpp)
  // a pill is as big as its words (+ 22 px a side) and never under 48 px (44 on the glass; S: 68 px = 6.4 mm,
  // Density.h): its hit box = what is drawn
  for (Item& it : out) {
    if (!it.underline) continue;
    const Font& f = fontOf(it.font, set_.largeText);
    const float tw = (float)Canvas::measureText(f, it.label.c_str()) / g_.k();
    it.w = fmaxf(it.w, fminf(tw + dens_.pillPad, dens_.pillMaxW));
    it.h = fmaxf(it.h, dens_.pillMinH);
  }
  fitRows(out);  // SOUL S: rows of pills centred and inside the circle (OsScreens.cpp); nothing on M
}

int Os::hitItem(float x, float y) const {
  buildItems(items_);
  const float k = g_.k();
  const float px = x / k, py = y / k;
  for (const Item& it : items_) {
    if (it.id < 0 || it.w <= 0) continue;
    if (fabsf(px - it.x) <= it.w * 0.5f && fabsf(py - it.y) <= it.h * 0.5f) return it.id;
  }
  return -1;
}

// ---------------------------------------------------------------- drawing ---

void Os::textAt(Canvas& cv, const Font& f, float x, float y, const std::string& s, Rgb c, float alpha, Align a) {
  const int base = (int)lroundf(g_.s(y) + (f.ascent - f.descent) * 0.5f);
  cv.drawText(f, g_.s(x), base, s.c_str(), c, alpha * fade_, a);
}

static constexpr float kHalfPi = 1.5707963f;
// the rim's words (titles, hints, the banner) ride r 205 on M: the capsule spans 189-221 (DESIGN-ALIVE.md §2
// zones), so no glyph reaches past r 228 on the glass (Density.h: rimR / rimHalf / rimPad; S: r 200, its words 32 px)

// a glass capsule on the rim, as wide as the words + 15 px each side
static void rimCapsule(Canvas& cv, const DisplayGeometry& g, const Density& d, const std::string& s, float r, bool top,
                       const GlassStyle& st) {
  const float span = Canvas::arcTextSpan(fonts::caption(), r, s.c_str(), 1.0f) + g.s(d.rimPad) / r;
  const float a = top ? -kHalfPi : kHalfPi;
  glass().capsuleArc(cv, g.cx(), g.cy(), r, g.s(d.rimHalf), a - span * 0.5f, a + span * 0.5f, st);
}

void Os::rimTop(Canvas& cv, const std::string& s, Rgb c, float alpha) {
  if (toastLeft_ > 0 && !toast_.empty()) return;  // the notification capsule has the rim
  if (s.empty()) return;
  alpha = fmaxf(alpha, 0.84f);  // SoulOS Alive: what you must read is >= 80 %
  rimCapsule(cv, g_, dens_, s, g_.s(dens_.rimR), true, gs(alpha));
  cv.drawTextArc(fonts::caption(), g_.cx(), g_.cy(), g_.s(dens_.rimR), -kHalfPi, s.c_str(), c, alpha * fade_, false, 1.0f);
}

// Rim manners (DESIGN-ALIVE.md §4): a bottom-rim hint is drawn only if none of its glyphs would touch a control
// of the screen; otherwise it is dropped (the content wins)
bool Os::rimBottomFits(const std::string& s) const {
  const float r = dens_.rimR, half = Canvas::arcTextSpan(fonts::caption(), g_.s(r), s.c_str(), 1.0f) * 0.5f + 0.06f;
  const float inner = r - dens_.rimHalf;  // the glyphs' inner edge (design px)
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id < 0 || it.w <= 0) continue;
    const float x0 = it.x - it.w * 0.5f, x1 = it.x + it.w * 0.5f, y1 = it.y + it.h * 0.5f;
    // the arc's band under the item's box: its corners are inside the band's inner circle, or it clears
    for (float x : {x0, x1, it.x}) {
      const float dx = x - 233, dy = y1 - 233;
      if (dy <= 0) continue;
      const float ang = atan2f(dx, dy);  // 0 = straight down
      if (fabsf(ang) <= half && hypotf(dx, dy) >= inner - 4) return false;
    }
  }
  return true;
}

void Os::rimBottom(Canvas& cv, const std::string& s, Rgb c, float alpha) {
  alpha = fmaxf(alpha, 0.7f);  // a secondary hint, 22 px
  if (!rimBottomFits(s)) return;
  cv.drawTextArc(fonts::caption(), g_.cx(), g_.cy(), g_.s(dens_.rimR), kHalfPi, s.c_str(), c, alpha * fade_, true, 1.0f);
}

void Os::rimBottomCap(Canvas& cv, const std::string& s, Rgb c, float alpha, bool glow) {
  rimCapsule(cv, g_, dens_, s, g_.s(dens_.rimR), false, glow ? gsAccent(c, 0.4f, 0.1f) : gs(alpha));
  cv.drawTextArc(fonts::caption(), g_.cx(), g_.cy(), g_.s(dens_.rimR), kHalfPi, s.c_str(), c, alpha * fade_, true, 1.0f);
}

void Os::glassPanel(Canvas& cv, float x0, float y0, float x1, float y1, float r, const GlassStyle& st) {
  glass().panel(cv, g_.s(x0), g_.s(y0), g_.s(x1), g_.s(y1), g_.s(r), st);
}

void Os::glassPill(Canvas& cv, float cx, float cy, float w, float h, Rgb c, bool pressed) {
  const bool tone = c == kMint || c == kAmber || c == kIce;
  GlassStyle st = tone ? gsAccent(c, 0.32f, 0.1f) : gs();
  if (pressed) st = st.pressed();
  glassPanel(cv, cx - w * 0.5f, cy - h * 0.5f, cx + w * 0.5f, cy + h * 0.5f, h * 0.5f, st);
}

// a glass track with a light in it (Alarms: on / off)
void Os::glassToggle(Canvas& cv, float cx, float cy, bool on) {
  glassPanel(cv, cx - 29, cy - 16, cx + 29, cy + 16, 16, on ? gsAccent(kMint, 0.3f, 0.3f) : gs());
  const float kx = g_.s(on ? cx + 13 : cx - 13), ky = g_.s(cy);
  cv.ellipse(kx, ky, g_.s(11.5f), g_.s(11.5f), on ? kMint : kCream, (on ? 1.0f : 0.32f) * fade_);
}

int Os::wrapLines(const Font& f, const std::string& text, float maxW, std::string* lines, int maxLines) const {
  if (text.find('\n') != std::string::npos) {  // paragraphs (cards: "1. flour\n2. eggs")
    int n = 0;
    size_t i = 0;
    while (i <= text.size() && n < maxLines) {
      size_t e = text.find('\n', i);
      if (e == std::string::npos) e = text.size();
      const std::string para = text.substr(i, e - i);
      if (!para.empty()) n += wrapLines(f, para, maxW, lines + n, maxLines - n);
      i = e + 1;
    }
    return n;
  }
  const std::string& s = text;
  int n = 0;
  std::string cur;
  size_t i = 0;
  while (i < s.size()) {
    size_t j = s.find(' ', i);
    if (j == std::string::npos) j = s.size();
    const std::string word = s.substr(i, j - i);
    const std::string trial = cur.empty() ? word : cur + " " + word;
    if (Canvas::measureText(f, trial.c_str()) <= maxW || cur.empty()) {
      cur = trial;
    } else {
      if (n == maxLines - 1) {
        lines[n++] = ellipsize(f, trial, maxW);
        return n;
      }
      lines[n++] = cur;
      cur = word;
    }
    i = j + 1;
  }
  if (!cur.empty() && n < maxLines) lines[n++] = ellipsize(f, cur, maxW);
  return n;
}

void Os::drawItems(Canvas& cv, const std::vector<Item>& items) {
  for (const Item& it : items) {
    if (it.font > 2) continue;  // a wheel row's hit box: drawWheel draws the row
    const Font& f = fontOf(it.font, set_.largeText);
    const bool held = holdItem_ == it.id && it.id >= 0;
    if (it.underline) {  // an action: a pill (SoulOS Alive: flat, filled e1 / mint, amber-edged, outlined)
      pill(cv, it.x, it.y, it.w, it.h, it.label, pillOf(it), f, 1, held);
    } else {
      textAt(cv, f, it.x, it.y, it.label, it.color, it.alpha);
    }
    if (held) {  // hold progress under it
      const float w = g_.s(it.w) * 0.8f * (holdItemT_ > 1 ? 1 : holdItemT_);
      const float y = g_.s(it.y + it.h * 0.5f) + 5;
      cv.roundRect(g_.s(it.x) - w * 0.5f, y, g_.s(it.x) + w * 0.5f, y + 3.0f, 1.5f, kAmber, 0.9f);
    }
  }
}

void Os::render(Canvas& cv) {
  if (lidsActive()) {  // SoulOS Alive: the lid wipe (the lids themselves are drawn over the eyes: renderOverlay)
    if (lids_.closing()) {  // the old screen stays; only the eyes' last place is repaired (black under them)
      glass().background(cv);
      return;
    }
    int y0, y1;  // opening: the new screen only between the lids, black where they cover every pixel
    alive::LidWipe::openBand((float)g_.w, (float)g_.h, lids_.cover(), y0, y1);
    const Rect keep = cv.clipRect();
    if (keep.y0 < y0) cv.fillRect(Rect{keep.x0, keep.y0, keep.x1, y0 < keep.y1 ? y0 : keep.y1}, pal::kBlack);
    if (keep.y1 > y1) cv.fillRect(Rect{keep.x0, y1 > keep.y0 ? y1 : keep.y0, keep.x1, keep.y1}, pal::kBlack);
    const Rect mid{keep.x0, keep.y0 > y0 ? keep.y0 : y0, keep.x1, keep.y1 < y1 ? keep.y1 : y1};
    if (mid.empty()) return;
    cv.setClip(mid);
    renderContent(cv);
    cv.setClip(keep);
    return;
  }
  renderContent(cv);
}

void Os::renderContent(Canvas& cv) {
  glass().background(cv);  // under the clip only: pure black (SoulOS Alive; the frosted aura is retired)
  switch (view_) {
    case View::Keyboard: kb_.render(cv); break;
    case View::Dial: tp_.render(cv); break;
    case View::Boot: drawBoot(cv); break;
    case View::Home: drawHome(cv); break;
    case View::Launcher: drawDial(cv); break;  // SoulOS Alive: the home dial (OsAlive.cpp)
    case View::Today: drawTodayStack(cv); break;
    case View::Talk: drawTalk(cv); break;
    case View::Answer: drawAnswer(cv); break;
    case View::Alarms: drawAlarms(cv); break;
    case View::Ringing: drawRinging(cv); break;
    case View::Timer: drawTimer(cv); break;
    case View::Notes: drawNotes(cv); break;
    case View::NoteView: drawNoteView(cv); break;
    case View::Claude: drawClaude(cv); break;
    case View::Settings: drawSettings(cv); break;
    case View::AiMode: drawAiMode(cv); break;
    case View::Wifi: drawWifi(cv); break;
    case View::MySoul: drawMySoul(cv); break;
    case View::About: drawAbout(cv); break;
    case View::Pair: drawPair(cv); break;
    case View::Bridge: drawBridge(cv); break;
    case View::Memory: drawMemory(cv); break;  // OsMemory.cpp
    default: appsDraw(cv); break;              // OsAppsDraw.cpp
  }
  drawSlotDisc(cv);  // an app screen: the eyes' black disc over the content (the eyes go on top)
  drawSpeech(cv);    // the face and the dial: a line under the eyes
  if (view_ != View::Keyboard && view_ != View::Dial) drawToast(cv);
  if (set_.debug) drawPerf(cv);
  drawnView_ = view_;
}

void Os::drawToast(Canvas& cv) {
  if (toastLeft_ <= 0 || toast_.empty()) return;
  // a glass capsule along the top rim (the title steps aside while it shows)
  // SoulOS Alive: a solid banner on the top rim, e1 (or amber / mint / ice), with dark words
  const std::string s = ellipsize(fonts::caption(), toast_, g_.s(dens_.toastW));
  const bool tone = toastColor_ == kAmber || toastColor_ == kMint || toastColor_ == kIce;
  const Rgb fill = tone ? toastColor_ : pal_.e1;
  const Rgb ink = toastColor_ == kAmber ? Rgb::hex(0x2A1700) : toastColor_ == kMint ? Rgb::hex(0x06231B)
                  : toastColor_ == kIce ? Rgb::hex(0x071A33) : pal_.on1;
  const float r = g_.s(dens_.rimR), span = Canvas::arcTextSpan(fonts::caption(), r, s.c_str(), 1.0f) + g_.s(dens_.toastPad) / r;
  glass().flatArc(cv, g_.cx(), g_.cy(), r, g_.s(dens_.toastHalf), -kHalfPi - span * 0.5f, -kHalfPi + span * 0.5f, fill, 1.0f);
  cv.drawTextArc(fonts::caption(), g_.cx(), g_.cy(), r, -kHalfPi, s.c_str(), ink, 1.0f, false, 1.0f);
}

void Os::drawPerf(Canvas& cv) {
  char a[64], b[64];
  snprintf(a, sizeof a, "%.0f fps  %.1f ms  cpu %.0f%%", perf.fps, perf.frameMs, perf.cpu * 100);
  snprintf(b, sizeof b, "draw %.1f  push %.1f  heap %u K  ps %u K", perf.renderMs, perf.pushMs, (unsigned)perf.heapKb,
           (unsigned)perf.psramKb);
  cv.fillRect(g_.rect(110, 404, 356, 452), pal::kBlack);
  cv.drawText(fonts::caption(), g_.cx(), (int)g_.s(424), a, kIce, 0.9f, Align::Center);
  cv.drawText(fonts::caption(), g_.cx(), (int)g_.s(446), b, kIce, 0.7f, Align::Center);
}

static std::string clockText(uint32_t now) {
  if (!now) return "--:--";
  char b[16];
  snprintf(b, sizeof b, "%02d:%02d", (int)(now % 86400 / 3600), (int)(now % 3600 / 60));
  return b;
}

void Os::drawBoot(Canvas& cv) {
  const bool R = ro();
  switch (bootStep_) {
    case BootStep::Birth: {
      const Design& d = kDesigns[birth_.design];
      const int shown = (int)(viewT_ * 14);
      const std::string chip = birth_.chip.substr(0, shown < (int)birth_.chip.size() ? (size_t)shown : birth_.chip.size());
      rimTop(cv, chip, kAmber, 0.9f);
      const float a = viewT_ < 1.0f ? 0 : (viewT_ - 1.0f) / 0.5f;
      const float al = a > 1 ? 1 : a;
      if (al > 0) {
        textAt(cv, fonts::title(), 233, L(330, 290), d.name, kCream, al);
        char b[64];
        snprintf(b, sizeof b, "%s · #%03d / %d", kRarityName[(int)d.rarity], d.num, kDesignCount);
        textAt(cv, fonts::tag(), 233, L(366, 326), upperAscii(b), Rgb::hex(kRarityColor[(int)d.rarity]), al);
        int cnt = 0;
        for (int i = 0; i < kDesignCount; ++i)
          if (kDesigns[i].rarity == d.rarity) ++cnt;
        snprintf(b, sizeof b, R ? "1 din %d" : "1 in %d", (int)lround(cnt / kRarityRate[(int)d.rarity]));
        textAt(cv, fonts::caption(), 233, L(394, 358), b, kCream, al * kDim);
        rimBottom(cv, R ? "atinge ca să ne cunoaștem" : "tap to meet me", kCream, kDim * al);
      }
      return;
    }
    case BootStep::Name:
    case BootStep::Brain:
      buildItems(items_);
      drawItems(cv, items_);
      if (bootStep_ == BootStep::Brain) {
        std::string line;
        Rgb c = kCream;
        if (aiMode() != AiMode::None) {
          const bool needs = needsSetup();
          if (needs && net_.portal) {
            line = (R ? "Pe telefon: Wi-Fi " : "On your phone: Wi-Fi ") + net_.apName + " · " + net_.apPass;
            c = kAmber;
          } else if (!needs) {
            line = R ? "Gata de vorbă" : "Ready to talk";
            c = kMint;
          }
        } else {
          line = R ? "Ore, alarme, minutare: pe device" : "Times, alarms, timers: on the device";
        }
        if (!line.empty()) textAt(cv, fonts::caption(), 233, L(370, 350), ellipsize(fonts::caption(), line, g_.s(330)), c, kDim);
        rimTop(cv, "2 / 3", kCream, kFaint);
      } else {
        rimTop(cv, "1 / 3", kCream, kFaint);
      }
      return;
    case BootStep::Hold:
      textAt(cv, fonts::title(), 233, L(346, 290), R ? "Ține degetul pe sticlă" : "Hold the glass", listening_ ? kIce : kCream);
      textAt(cv, fonts::caption(), 233, L(384, 328), R ? "așa îmi vorbești" : sGlass() ? "how you talk to me" : "that's how you talk to me", kCream, kDim);
      rimTop(cv, "3 / 3", kCream, kFaint);
      rimBottom(cv, R ? "butonul: sari peste" : "button: skip", kCream, kFaint);
      return;
    default: return;
  }
}

void Os::drawHome(Canvas& cv) {
  const bool R = ro();
  if (claude_.passkey) {  // pairing with Claude Desktop: the code has to be read (an event, not standby)
    char b[12];
    snprintf(b, sizeof b, "%06lu", (unsigned long)claude_.passkey);
    glassPanel(cv, 128, 362, 338, 422, 30, gsAccent(kAmber, 0.4f, 0.08f));
    textAt(cv, fonts::title(), 233, 392, b, kAmber);
    rimBottom(cv, R ? "codul pentru Claude Desktop" : "pairing code for Claude Desktop", kCream, kDim);
    return;
  }
  if (peekT_ <= 0) return;  // standby: the eyes alone, nothing else on the glass
  std::string top = clockText(now_);
  if (timerRun_) {
    const int s = timerLeft();
    char b[24];
    snprintf(b, sizeof b, "  ·  %d:%02d", s / 60, s % 60);
    top += b;
  }
  if (power_.batPct >= 0) top += "  ·  " + std::to_string(power_.batPct) + "%";
  rimTop(cv, top, kCream, kDim);
  if (claude_.prompt) {
    rimBottomCap(cv, R ? "Claude te așteaptă · ține = da · 2× = nu" : "Claude needs you · hold = yes · 2× = no", kAmber, 1, true);
  } else if (thinking_) {
    rimBottom(cv, R ? "mă gândesc…" : "thinking…", kAmber, kDim);
  } else {
    rimBottom(cv, R ? "glisează: aplicații · ține: vorbește" : "swipe: apps · hold: talk", kCream, kFaint);
  }
}

void Os::drawToday(Canvas& cv) { drawTodayStack(cv); }  // the stack of glass cards (OsAppsDraw.cpp)

// Talk (a face moment): the AI's name as a tag, what to do, one button. Hold the glass = listen: an ice ring.
void Os::drawTalk(Canvas& cv) {
  const bool R = ro();
  const char* who = aiMode() == AiMode::None ? (R ? "FĂRĂ AI" : "NO AI")
                    : aiMode() == AiMode::Cloud ? (R ? "CLAUDE-UL TĂU" : "YOUR CLAUDE")
                    : aiMode() == AiMode::Claude ? (R ? "CLAUDE · CHEIA TA" : "CLAUDE · YOUR KEY")
                    : aiMode() == AiMode::Bridge ? (R ? "CLAUDE · CALCULATOR" : "CLAUDE · COMPUTER")
                                                 : (R ? "CHATGPT · CHEIA TA" : "CHATGPT · YOUR KEY");
  if (listening_) {
    rimRing(cv, 216, 0, 2 * 3.14159265f, kIce, 0.85f, 8);
    if (voice_) rimTop(cv, R ? "Ascult…" : "Listening…", kIce, 1);
  }
  textAt(cv, fonts::tag(), 233, 262, who, kIce);
  std::string hint;
  if (listening_) hint = voice_ ? (R ? "Ascult…" : "Listening…") : (R ? "Dă drumul și scrie" : "Let go, then type");
  else if (aiMode() != AiMode::None && !net_.connected) hint = R ? "Fără Wi-Fi: doar ore și minutare" : "No Wi-Fi: times and timers only";
  else if (aiMode() == AiMode::None) hint = R ? "Ore, alarme, minutare" : "Times, alarms and timers";
  else hint = voice_ ? (R ? "Ține sticla și întreabă" : "Hold the glass and ask") : (R ? "Ține sticla, sau scrie" : "Hold, or type");
  const Font& hf = Canvas::measureText(fonts::body(), hint.c_str()) <= g_.s(330) ? fonts::body() : fonts::caption();
  textAt(cv, hf, 233, 296, ellipsize(hf, hint, g_.s(340)), listening_ ? kIce : kCream);
  buildItems(items_);
  drawItems(cv, items_);
}

// the answer. Thinking is a face moment (the eyes squint, an amber arc, the question); the answer sits on a round
// pebble under the eyes (mint edge when something was done, amber when it failed); a message (a card from SOUL
// Cloud, your AI or an app) is a card with its quick replies.
void Os::drawAnswer(Canvas& cv) {
  const bool R = ro();
  if (thinking_) {
    const char* who = aiMode() == AiMode::Claude || aiMode() == AiMode::Bridge || aiMode() == AiMode::Cloud ? "Claude"
                      : aiMode() == AiMode::ChatGpt ? "ChatGPT" : "SOUL";
    const float a0 = 3.14159265f * 0.62f;  // the amber arc on the left rim (still: the eyes squint, they are the motion)
    rimRing(cv, 216, a0, a0 + 0.62f, kAmber, 0.9f, 8);
    if (aiMode() == AiMode::Bridge && net_.askState != 2)  // on its way to the computer, Claude Code has not taken it yet
      rimTop(cv, R ? "trimit calculatorului…" : "sending to your computer…", kAmber, 1);
    else
      rimTop(cv, std::string(who) + (R ? " se gândește…" : " is thinking…"), kAmber, 1);
    std::string lines[2];
    const int n = wrapLines(fonts::caption(), "\xE2\x80\x9C" + reply_.say + "\xE2\x80\x9D", g_.s(300), lines, 2);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(310, 294) + i * L(26, 34), lines[i], kCream, kDim);
    textAt(cv, fonts::caption(), 233, L(384, 374), who, kAmber);
    return;
  }
  const bool card = !cardTitle_.empty() || acceptMode_;
  const bool err = lastErr_ != AiErr::None, done = !reply_.actions.empty() || !chips_.empty();
  if (card) {  // the message: a card, its title, its words, the replies under them
    rimTop(cv, answerSrc_, kCream, kFaint);
    buildItems(items_);
    bool replies = false;
    for (const Item& it : items_) replies |= it.underline;
    if (sGlass()) {  // SOUL S: the card holds the words, the replies are pills under it (OsAppsDraw.cpp)
      std::string tl[2], bl[5];
      const int nt = cardTitle_.empty() ? 0 : wrapLines(fonts::name(), cardTitle_, g_.s(300), tl, 2);
      const int maxL = replies ? (nt > 1 ? 1 : 2) : (nt ? 4 : 5);
      const int nb = cardHidden_ || reply_.say.empty() ? 0 : wrapLines(fonts::caption(), reply_.say, g_.s(300), bl, maxL);
      const float top = 130, bot = replies ? top + 30 + nt * 42 + (cardHidden_ ? 34 : nb * 34) + 4 : 390;
      pebRect(cv, 70, top, 396, bot, 30, pal_.peb, pal_.pebe, 0);
      float y = top + 32;
      for (int i = 0; i < nt; ++i, y += 42) textAt(cv, fonts::name(), 233, y, tl[i], kCream);
      if (cardHidden_) textAt(cv, fonts::caption(), 233, y, R ? "Privat · atinge ca să vezi" : "Private · tap to show", kCream, kDim);
      for (int i = 0; i < nb; ++i, y += 34) textAt(cv, fonts::caption(), 233, y - 6, bl[i], kCream, kDim);
      drawItems(cv, items_);
      if (acceptMode_) rimBottom(cv, R ? "nu sună până nu accepți" : "it won't ring unless you accept", kCream, kFaint);
      return;
    }
    const float top = 152, bot = replies ? 392 : 380;
    pebRect(cv, 84, top, 382, bot, 30, pal_.peb, pal_.pebe, 0);
    std::string tl[2];
    const int nt = cardTitle_.empty() ? 0 : wrapLines(fonts::name(), cardTitle_, g_.s(270), tl, 2);
    float y = 184;
    for (int i = 0; i < nt; ++i, y += 32) textAt(cv, fonts::name(), 233, y, tl[i], kCream);
    if (nt) y += 4;
    if (cardHidden_) {
      textAt(cv, fonts::caption(), 233, y + 6, R ? "Privat · atinge ca să vezi" : "Private · tap to show", kCream, kDim);
    } else {
      std::string bl[7];
      const int maxL = replies ? (nt > 1 ? 1 : 2) : (nt ? 6 : 7);
      const int nb = reply_.say.empty() ? 0 : wrapLines(fonts::caption(), reply_.say, g_.s(262), bl, maxL);
      for (int i = 0; i < nb; ++i, y += 26) textAt(cv, fonts::caption(), 233, y, bl[i], kCream, kDim);
    }
    drawItems(cv, items_);
    if (acceptMode_) rimBottom(cv, R ? "nu sună până nu accepți" : "it won't ring unless you accept", kCream, kFaint);
    return;
  }
  // the round pebble (350 x 236 on the glass) under the eyes (Density.h: S's fills the glass under the slot)
  const Density::Answer& A = dens_.answer;
  const float cx = 233, cy = A.cy, rx = A.rx, ry = A.ry;
  const Rgb edge = err && !done ? kAmber : done ? kMint : pal_.pebe;
  cv.ellipse(g_.s(cx), g_.s(cy), g_.s(rx), g_.s(ry), edge, fade_);
  cv.ellipse(g_.s(cx), g_.s(cy), g_.s(rx - 4), g_.s(ry - 4), pal_.peb, fade_);
  // the source on top: ice; an on-device fallback says so in amber (a note, not a sad face)
  std::string src = answerSrc_;
  Rgb srcC = kIce;
  if (err && done) {
    src = R ? "Făcut pe SOUL · AI offline" : "Done on SOUL · AI offline";
    srcC = kAmber;
  } else if (err) {
    src = aiErrText(lastErr_, R);
    srcC = kAmber;
  }
  if (!src.empty()) textAt(cv, fonts::caption(), cx, A.srcY, ellipsize(fonts::caption(), src, g_.s(A.srcW)), srcC);
  const bool big = reply_.say.size() <= 64 && chips_.size() <= 2;
  const Font& f = big ? fonts::name() : fonts::caption();
  const float lh = big ? A.bigLine : A.line;
  const int extra = (int)chips_.size() + (reply_.rejected > 0 ? 1 : 0);
  const int maxLines = big ? 3 : (extra ? A.smallLines - extra : A.smallLines);
  // each line as wide as the pebble at its height
  float widths[7];
  const float y0 = A.textY + (big ? A.bigShift : 0);
  for (int i = 0; i < 7; ++i) {
    const float yy = y0 + i * lh, dy = fmaxf(fabsf(yy - lh * 0.5f - cy), fabsf(yy + lh * 0.5f - cy)) / ry;
    widths[i] = g_.s(dy < 1 ? 2 * rx * sqrtf(1 - dy * dy) - A.pad : 0);
  }
  std::string lines[7];
  const int n = reply_.say.empty() ? 0 : wrapShaped(f, reply_.say, widths, lines, maxLines > 1 ? maxLines : 1);
  float y = y0;
  for (int i = 0; i < n; ++i, y += lh) textAt(cv, f, cx, y, lines[i], kCream, err && !done ? kDim : 1.0f);
  y += 2;
  for (const std::string& c : chips_) {  // ✓ what was done, in mint
    const Font& cf = fonts::caption();
    const std::string t = ellipsize(cf, c, g_.s(A.chipW));
    const float tw = (float)Canvas::measureText(cf, t.c_str()) / g_.k();
    checkMark(cv, cx - tw * 0.5f - A.chipTick, y, 13 * dens_.ts, kMint);
    textAt(cv, cf, cx + A.chipX, y, t, kMint);
    y += A.chip;
  }
  if (reply_.rejected > 0) {
    char b[48];
    snprintf(b, sizeof b, R ? "%d acțiuni ignorate" : "%d action%s ignored", reply_.rejected, (!R && reply_.rejected > 1) ? "s" : "");
    textAt(cv, fonts::caption(), cx, y, b, kCream, kFaint);
  }
  rimBottom(cv, R ? "atinge ca să închizi" : "tap to close", kCream, kFaint);
}

void Os::drawAlarms(Canvas& cv) {
  const bool R = ro();
  const int n = alarms_ ? alarms_->count() : 0;
  // no speaker and no buzzer: said where alarms are set (amber title), never an alarm ringing in silence unannounced
  if (!alarmAudible_) rimTop(cv, R ? "Alarme · fără sunet" : "Alarms · silent", kAmber);
  else rimTop(cv, n ? (R ? "Alarme · " : "Alarms · ") + std::to_string(n) : std::string(R ? "Alarme" : "Alarms"), kCream);
  if (!n && wheel_.focused() == 0) textAt(cv, fonts::caption(), 233, 200, R ? "Nicio alarmă încă" : "No alarms yet", kCream, kDim);
  drawWheel(cv);
  if (!alarmAudible_) rimBottom(cv, R ? "fără difuzor: alarmele nu sună" : "no speaker: alarms are silent", kAmber);  // (when it fits)
}

void Os::drawRinging(Canvas& cv) {
  const bool R = ro();
  std::string label;
  if (timerRinging_) label = timerFocus_ ? (R ? "Focus gata" : "Focus done") : (R ? "Minutar gata" : "Timer done");
  else if (ringingAlarm_ >= 0 && alarms_ && ringingAlarm_ < alarms_->count()) label = alarms_->at(ringingAlarm_).label;
  const Rgb c = timerRinging_ ? kMint : kAmber;
  rimRing(cv, 218, 0, 2 * 3.14159265f, c, 0.8f, 8);  // (the eyes and the tone are what pulse)
  if (!alarmAudible_) rimTop(cv, timerRinging_ ? (R ? "Minutar · fără sunet" : "Timer · silent") : (R ? "Alarmă · fără sunet" : "Alarm · silent"), c, 1);
  else rimTop(cv, timerRinging_ ? (R ? "Minutar" : "Timer") : (R ? "Alarmă" : "Alarm"), c, 1);
  textAt(cv, fonts::digits(), 233, L(254, 218), clockText(now_), kCream);
  if (!label.empty()) textAt(cv, fonts::body(), 233, L(318, 276), ellipsize(fonts::body(), label, g_.s(300)), kCream);
  buildItems(items_);
  drawItems(cv, items_);
}

void Os::drawTimer(Canvas& cv) {
  const bool R = ro();
  buildItems(items_);
  if (timerRun_) {
    const int s = timerLeft();
    char b[16];
    snprintf(b, sizeof b, "%d:%02d", s / 60, s % 60);
    textAt(cv, fonts::digits(), 233, 236, b, timerPaused_ ? kAmber : kCream);
    // the countdown on the rim: an 8 px e1 ring on a peb2 track, from the top, clockwise
    rimRing(cv, 216, 0, 2 * 3.14159265f, pal_.peb2, 1, 8);
    const float frac = timerTotal_ > 0 ? timerLeft_ / timerTotal_ : 0;
    if (frac > 0.002f) rimRing(cv, 216, -1.5707963f, -1.5707963f + 6.2831853f * frac, timerPaused_ ? kAmber : pal_.e1, 1, 8);
    rimTop(cv, timerFocus_ ? "Focus" : (R ? "Minutar" : "Timer"), kCream);
    drawItems(cv, items_);
    return;
  }
  rimTop(cv, R ? "Minutar" : "Timer", kCream);
  textAt(cv, fonts::digits(), 233, 222, "0:00", kCream, 0.4f);
  for (const Item& it : items_) {  // the presets: 58 px discs, minutes in them (25 = focus, in e1)
    if (it.id < IdRow) continue;
    const bool focus = it.id - IdRow == 4;
    const float r = it.w * 0.5f;  // 29 on M
    cv.ellipse(g_.s(it.x), g_.s(it.y), g_.s(r), g_.s(r), focus ? pal_.e1 : pal_.peb2, fade_);
    if (!focus) cv.ring(g_.s(it.x), g_.s(it.y), g_.s(r - 1.5f), g_.s(3), pal_.pebe, fade_);
    textAt(cv, fonts::body(), it.x, it.y, it.label, focus ? pal_.on1 : kCream);
  }
  textAt(cv, fonts::caption(), 233, L(356, 368), R ? "minute · 25 = focus" : "minutes · 25 = focus", kCream, kDim);
}

void Os::drawNotes(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, (R ? "Notițe · " : "Notes · ") + std::to_string(notes_.size()), kCream);
  if (wheel_.focused() == 0)
    textAt(cv, fonts::caption(), 233, 200,
           notes_.empty() ? (R ? "Nicio notiță încă" : "No notes yet")
                          : voice_ ? (R ? "Ține apăsat și dictează" : "Hold and dictate") : (R ? "Ține un rând = șterge" : "Hold a row = delete"),
           kCream, kDim);
  drawWheel(cv);
}

void Os::drawNoteView(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "Notiță" : "Note", kCream);
  if (noteSel_ < 0 || noteSel_ >= (int)notes_.size()) return;
  std::string lines[4];
  // (S: three lines of the S body face, 44 px apart, on a wider pebble)
  const float lp = L(32, 44), top = L(152, 138), x0 = L(84, 64);
  const int n = wrapLines(fonts::body(), notes_[noteSel_].text, g_.s(L(270, 300)), lines, sGlass() ? 3 : 4);
  pebRect(cv, x0, top, 466 - x0, top + 24 + n * lp + 8, 28, pal_.peb, pal_.pebe, 0);
  for (int i = 0; i < n; ++i) textAt(cv, fonts::body(), 233, top + 28 + i * lp + L(0, 6), lines[i], kCream);
  buildItems(items_);
  drawItems(cv, items_);
  rimBottom(cv, R ? "ține Șterge ca să ștergi" : "hold Delete to delete", kCream, kFaint);
}

// Claude: pairing (the code), Claude asks (the command + Allow / Deny), working / connected
void Os::drawClaude(Canvas& cv) {
  const bool R = ro();
  if (claude_.passkey) {
    rimTop(cv, "Claude", kCream);
    char b[12];
    snprintf(b, sizeof b, "%06lu", (unsigned long)claude_.passkey);
    textAt(cv, fonts::caption(), 233, 186, R ? "Codul ăsta, în Claude:" : "Type this code in Claude:", kCream, kDim);
    textAt(cv, fonts::digits(), 233, 262, b, kAmber);
    return;
  }
  if (claude_.prompt) {  // Claude asks: an amber ring, the command on an amber-edged pebble, Allow / Deny
    const Density::Ask& q = dens_.ask;
    rimRing(cv, 218, 0, 2 * 3.14159265f, kAmber, 0.8f, 8);
    rimTop(cv, R ? "Claude cere voie" : "Claude asks", kAmber, 1);
    pebRect(cv, q.x0, q.y0, q.x1, q.y1, q.r, pal_.peb, kAmber, 4);
    textAt(cv, fonts::caption(), 233, q.toolY, ellipsize(fonts::caption(), claude_.tool.empty() ? std::string("Claude") : claude_.tool, g_.s(q.textW)), kCream, kDim);
    std::string lines[2];
    const int n = wrapLines(fonts::body(), claude_.hint.empty() ? claude_.tool : claude_.hint, g_.s(q.textW), lines, 2);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::body(), 233, (n == 1 ? q.hintY1 : q.hintY2) + i * q.hintLine, lines[i], kCream);
    buildItems(items_);
    drawItems(cv, items_);
    for (const Item& it : items_)  // ✓ on Allow
      if (it.id == IdAllow) {
        const float tw = (float)Canvas::measureText(fonts::body(), it.label.c_str()) / g_.k();
        // (S: kept inside the pill when the word is wide)
        checkMark(cv, fmaxf(it.x - tw * 0.5f - q.tick, it.x - it.w * 0.5f + q.tickSize * 1.2f), it.y, q.tickSize, Rgb::hex(0x06231B));
      }
    textAt(cv, fonts::caption(), 233, q.holdY, R ? "Ține = da · 2× = nu" : "Hold = yes · 2× = no", kCream);
    return;
  }
  rimTop(cv, "Claude", kCream);
  // >_ : the Claude glyph, in e1
  drawGlyph(cv, AppId::Claude, 233, 176, 30, pal_.e1, 1, g_.s(4));
  if (!claude_.linked) {
    textAt(cv, fonts::name(), 233, 218, R ? "Neconectat" : "Not connected", kCream);
    textAt(cv, fonts::caption(), 233, 252, R ? "Claude Desktop › Developer ›" : "Claude Desktop › Developer ›", kCream, kDim);
    textAt(cv, fonts::caption(), 233, L(276, 286), R ? "Hardware Buddy › Conectează" : "Hardware Buddy › Connect", kCream, kDim);
    if (!claude_.bleName.empty() && !net_.relay) textAt(cv, fonts::caption(), 233, L(310, 322), claude_.bleName, kAmber);
  } else {
    textAt(cv, fonts::name(), 233, 218, claude_.busy ? (R ? "Claude lucrează" : "Claude is working") : (R ? "Conectat" : "Connected"),
           claude_.busy ? kAmber : kCream);
    char b[64];
    snprintf(b, sizeof b, R ? "%lu aprobate · %lu refuzate" : "%lu approved · %lu denied", (unsigned long)claude_.approvals,
             (unsigned long)claude_.denials);
    textAt(cv, fonts::caption(), 233, 254, claude_.msg.empty() ? std::string(b) : ellipsize(fonts::caption(), claude_.msg, g_.s(320)), kCream, kDim);
  }
  buildItems(items_);
  drawItems(cv, items_);
}

void Os::drawSettings(Canvas& cv) {
  rimTop(cv, ro() ? "Setări" : "Settings", kCream);
  drawWheel(cv);
}

void Os::drawAiMode(Canvas& cv) {
  rimTop(cv, ro() ? "AI-ul tău" : "Your AI", kCream);
  drawWheel(cv);
}

// "My Claude on my computer" (SOUL Bridge, docs/08 §4): the code to type in `soul-bridge pair`, then the
// computer's name once it is connected. SOUL Cloud's 8-character code (any network) when SOUL is paired, else
// the 6-digit code of SOUL's own server on this Wi-Fi.
void Os::drawBridge(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "Claude de pe calculator" : "Claude on my computer", kCream);
  if (net_.bridgeOnline) {
    textAt(cv, fonts::title(), 233, L(190, 166), R ? "Conectat" : "Connected", kMint);
    textAt(cv, fonts::body(), 233, L(232, 208), net_.bridgeName.empty() ? std::string("PC") : net_.bridgeName, kCream);
    std::string l[3];
    const int n = wrapLines(fonts::caption(), R ? "Întreabă-mă orice: îți răspunde Claude Code-ul tău, de pe calculator."
                                                : "Ask me anything: your own Claude Code answers, on your computer.",
                            g_.s(L(300, 340)), l, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(270, 246) + i * L(26, 34), l[i], kCream, kDim);
  } else if (!net_.connected) {
    textAt(cv, fonts::body(), 233, 220, R ? "Întâi Wi-Fi-ul" : "Wi-Fi first", kCream);
  } else if (net_.bridgeCode.empty()) {
    const float pulse = 0.6f + 0.35f * sinf(animT() * 3.0f);
    textAt(cv, fonts::body(), 233, 220, R ? "Fac un cod…" : "Making a code…", kCream, pulse);
  } else {
    const bool cloud = net_.bridgeCode.size() == 8;
    // (SOUL S: the same steps in fewer words, one line each, so the pills keep their 68 px)
    textAt(cv, fonts::caption(), 233, L(168, 154), sGlass() ? (R ? "În terminal:" : "In a terminal:")
                                                          : (R ? "Pe calculator, în terminal:" : "On your computer, in a terminal:"), kCream, kDim);
    textAt(cv, fonts::tag(), 233, L(196, 188), "soul-bridge pair", pal_.e1);
    textAt(cv, fonts::title(), 233, L(236, 228), cloud ? net_.bridgeCode.substr(0, 4) + "-" + net_.bridgeCode.substr(4) : net_.bridgeCode, kAmber);
    std::string tail;
    if (cloud && !net_.cloudHost.empty()) tail = "--cloud " + net_.cloudHost;
    else if (!cloud && !net_.ip.empty()) tail = R ? "(sau --soul " + net_.ip + ")" : "(or --soul " + net_.ip + ")";
    if (!tail.empty()) textAt(cv, fonts::caption(), 233, L(272, 266), ellipsize(fonts::caption(), tail, g_.s(L(320, 360))), kCream);
    std::string l[2];
    const int n = sGlass() ? wrapLines(fonts::caption(), net_.bridgePaired ? (R ? "Pornește Start SOUL pe el" : "Open Start SOUL on it")
                                                                            : (R ? "Apoi: soul-bridge setup" : "Then: soul-bridge setup"),
                                       g_.s(370), l, 1)
                           : wrapLines(fonts::caption(), net_.bridgePaired ? (R ? "Un calculator e legat, dar oprit: deschide Start SOUL."
                                                                                : "A computer is paired but off: open Start SOUL.")
                                                                           : (R ? "Apoi: soul-bridge setup și Start SOUL."
                                                                                : "Then: soul-bridge setup, and Start SOUL."),
                                       g_.s(300), l, 2);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(302, 302) + i * 24, l[i], kCream, kDim);
  }
  buildItems(items_);
  drawItems(cv, items_);
}

void Os::drawWifi(Canvas& cv) {
  const bool R = ro();
  if (net_.portal) {
    rimTop(cv, "Wi-Fi", kCream);
    // the phone camera joins SOUL's own Wi-Fi from this QR (iOS 11+, Android 10+)
    textAt(cv, fonts::caption(), 233, L(166, 150), sGlass() ? (R ? "Scanează cu telefonul" : "Scan with your phone")
                                                          : (R ? "Scanează cu camera telefonului" : "Scan with your phone's camera"), kCream, kDim);
    if (!net_.apPass.empty()) drawQr(cv, "WIFI:T:WPA;S:" + net_.apName + ";P:" + net_.apPass + ";;", 233, L(254, 228), L(128, 104));
    textAt(cv, fonts::body(), 233, L(338, 304), ellipsize(fonts::body(), net_.apName + (net_.apPass.empty() ? std::string() : "  ·  " + net_.apPass), g_.s(330)), kAmber);
    textAt(cv, fonts::caption(), 233, L(368, 340), (R ? "apoi deschide " : "then open ") + net_.portalUrl.substr(7), kCream, kDim);
  } else if (page_ == 1) {
    // the phone's hotspot (docs/09 §1): what to switch on, per phone
    rimTop(cv, R ? "Hotspotul telefonului" : "Phone hotspot", kAmber, 1);
    const char* body[2] = {
        R ? "iPhone: Hotspot personal › Permite altora + Maximizează compatibilitatea. Ține ecranul deschis."
          : "iPhone: Personal Hotspot › Allow Others to Join + Maximize Compatibility. Keep it open.",
        R ? "Android: Hotspot › nume, parolă, 2,4 GHz." : "Android: Hotspot › name, password, 2.4 GHz."};
    // SOUL S: the same in fewer words, 33 px a line (the S caption face), over the 68 px pills
    const char* bodyS[2] = {R ? "iPhone: Hotspot personal › Permite altora + Maximizează compatibilitatea."
                              : "iPhone: Personal Hotspot › Allow Others + Maximize Compatibility.",
                            R ? "Android: Hotspot › 2,4 GHz." : "Android: Hotspot › 2.4 GHz."};
    const float wS[2] = {360, 400};
    float y = L(172, 148);
    for (int k = 0; k < 2; ++k) {
      std::string lines[4];
      const int n = sGlass() ? wrapLines(fonts::caption(), bodyS[k], g_.s(wS[k]), lines, k ? 1 : 3)
                             : wrapLines(fonts::caption(), body[k], g_.s(k ? 300 : 320), lines, k ? 2 : 4);
      for (int i = 0; i < n; ++i, y += L(25, 32)) textAt(cv, fonts::caption(), 233, y, lines[i], kCream, k ? kDim : 1.0f);
      y += L(8, 4);
    }
  } else {
    rimTop(cv, "Wi-Fi", kCream);
    // where SOUL is: online / looking for a network / a login page / no internet, and what it knows
    std::string st;
    Rgb c = kCream;
    if (net_.captive) {
      st = R ? "Wi-Fi cu pagină de login" : "Wi-Fi wants a login page";
      c = kAmber;
    } else if (net_.noInternet) {
      st = net_.hotspot ? (R ? "Telefonul n-are date" : "The phone has no data") : (R ? "Fără internet" : "No internet");
      c = kAmber;
    } else if (net_.connected) {
      st = net_.hotspot ? (R ? "Pe hotspotul telefonului" : "On the phone's hotspot") : (R ? "Conectat" : "Connected");
      c = kMint;
    } else if (net_.saved == 0 && !net_.configured) {
      st = R ? "Niciun Wi-Fi salvat" : "No Wi-Fi saved";
    } else if (net_.wifiFail == 2) {
      st = R ? "Parolă greșită" : "Wrong password";
      c = kAmber;
    } else if (net_.linkUp || net_.connecting) {
      st = R ? "Mă conectez…" : "Connecting…";
    } else {
      st = R ? "Caut o rețea cunoscută…" : "Looking for a known network…";
    }
    textAt(cv, fonts::body(), 233, L(176, 158), ellipsize(fonts::body(), st, g_.s(320)), c);
    std::string sub;
    if (net_.captive) sub = R ? "Folosește hotspotul telefonului" : "Use your phone's hotspot";
    else if (net_.wifiFail == 2 && !net_.failSsid.empty()) sub = net_.failSsid;
    else if (net_.linkUp || net_.connected) sub = net_.ssid + (net_.ip.empty() || sGlass() ? std::string() : "  ·  " + net_.ip);
    else if (!net_.savedList.empty()) sub = (R ? "Știu: " : "I know: ") + net_.savedList;
    if (sGlass() && askQ_.size()) sub.clear();  // (S: one line under the state: the questions waiting win)
    if (!sub.empty()) textAt(cv, fonts::caption(), 233, L(208, 194), ellipsize(fonts::caption(), sub, g_.s(L(320, 340))), kCream, kDim);
    if (askQ_.size()) {
      char b[48];
      snprintf(b, sizeof b, R ? "%d întrebări așteaptă internetul" : "%d questions wait for the internet", askQ_.size());
      const std::string q = askQ_.size() == 1 ? (R ? "1 întrebare așteaptă internetul" : "1 question waits for the internet") : std::string(b);
      textAt(cv, fonts::caption(), 233, L(238, 194), sGlass() ? ellipsize(fonts::caption(), q, g_.s(340)) : q, kAmber, kDim);
    }
  }
  buildItems(items_);
  drawItems(cv, items_);
}

// My SOUL: the card of this SOUL's birth (the name, the rarity, how rare, the days together), Look and Rename;
// Look (page 1, OsAlive.cpp) previews the other births and picks the body colour
void Os::drawMySoul(Canvas& cv) {
  if (page_ == 1) {
    drawLook(cv);
    return;
  }
  const bool R = ro();
  const Design& d = kDesigns[birth_.design];
  rimTop(cv, R ? "SOUL-ul meu" : "My SOUL", kCream);
  buildItems(items_);
  drawItems(cv, items_);
  char b[96];
  snprintf(b, sizeof b, "%s · #%03d / %d", kRarityName[(int)d.rarity], d.num, kDesignCount);
  textAt(cv, fonts::tag(), 233, L(248, 250), upperAscii(b), Rgb::hex(kRarityColor[(int)d.rarity]));
  int cnt = 0;
  for (int i = 0; i < kDesignCount; ++i)
    if (kDesigns[i].rarity == d.rarity) ++cnt;
  std::string line = std::string(d.name) + " · " + (R ? "1 din " : "1 in ") + std::to_string((int)lround(cnt / kRarityRate[(int)d.rarity]));
  if (set_.born && now_ > set_.born) {
    const int days = (int)((now_ - set_.born) / 86400) + 1;
    line += R ? " · " + std::to_string(days) + (days == 1 ? " zi" : " zile") : " · " + std::to_string(days) + (days == 1 ? " day" : " days");
  }
  textAt(cv, fonts::caption(), 233, L(278, 288), ellipsize(fonts::caption(), line, g_.s(L(320, 380))), kCream, kDim);
  rimBottom(cv, "chip " + birth_.chip, kCream, kFaint);
}

void Os::drawAbout(Canvas& cv) {
  const bool R = ro();
  pebRect(cv, L(78, 66), L(152, 134), L(388, 400), L(372, 394), 30, pal_.peb, pal_.pebe, 0);
  {  // ✦ a four-point star
    Path& p = scratchPath();
    if (p.reserve(256)) {
      p.clear();
      const float x = g_.s(233), y = g_.s(L(180, 160)), r = g_.s(L(11, 13)), k = r * 0.28f;
      const float st[] = {x, y - r, x + k, y - k, x + r, y, x + k, y + k, x, y + r, x - k, y + k, x - r, y, x - k, y - k};
      p.polygon(st, 8);
      face_.raster().fill(cv, p, pal_.e1, fade_);
    }
  }
  textAt(cv, fonts::name(), 233, L(216, 196), R ? "Sunt un AI." : "I'm an AI.", kCream);
  const char* body = sGlass() ? (R ? "SOUL e o mașină: fără sentimente adevărate, nu e un om. Ce scrii merge doar la AI-ul ales."
                                   : "SOUL is a machine: no real feelings, not a person. What you type goes only to the AI you chose.")
                   : R ? "SOUL e o mașină. Nu are sentimente adevărate și nu e un om. Ce scrii merge doar la AI-ul ales de tine."
                       : "SOUL is a machine. It has no real feelings and it is not a person. What you type goes only to the AI you chose.";
  std::string lines[5];
  const int n = wrapLines(fonts::caption(), body, g_.s(L(270, 310)), lines, 5);
  for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(250, 234) + i * L(25, 34), lines[i], kCream, kDim);
}


void Os::drawQr(Canvas& cv, const std::string& text, float cx, float cy, float maxPx) {
  static QrImage qr;  // one at a time on screen; rebuilt only when the text changes
  if (!qr.make(text)) return;
  const int n = qr.size(), quiet = 3;
  int mod = (int)(g_.s(maxPx) / (float)(n + 2 * quiet));
  if (mod < 2) mod = 2;
  const int total = (n + 2 * quiet) * mod;
  const int x0 = (int)lroundf(g_.s(cx)) - total / 2, y0 = (int)lroundf(g_.s(cy)) - total / 2;
  // dark modules on a light card: every phone camera reads that way round
  cv.roundRect((float)x0, (float)y0, (float)(x0 + total), (float)(y0 + total), (float)mod * 1.5f, kCream, fade_);
  const Rgb ink = pal::kBlack;  // over the fading card: appears with it
  for (int y = 0; y < n; ++y)
    for (int x = 0; x < n; ++x)
      if (qr.at(x, y)) {
        const int px = x0 + (quiet + x) * mod, py = y0 + (quiet + y) * mod;
        cv.fillRect(Rect{px, py, px + mod, py + mod}, ink);
      }
}

void Os::drawPair(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, "SOUL Cloud", kCream);
  std::string id = "soul-";  // the device id, as the account page knows it
  for (char c : birth_.chip)
    if (c != ':') id += (char)(c >= 'A' && c <= 'F' ? c - 'A' + 'a' : c);
  if (net_.cloudUpdate) {
    textAt(cv, fonts::title(), 233, 196, R ? "Actualizează SOUL" : "Update SOUL", kAmber);
    std::string l[3];
    const int n = wrapLines(fonts::caption(), R ? "SOUL Cloud cere o versiune nouă. Cheia ta și „Fără AI” merg în continuare."
                                                : "SOUL Cloud needs a newer SOUL. Your own key and No AI still work.",
                            g_.s(L(300, 340)), l, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(240, 236) + i * L(26, 34), l[i], kCream, kDim);
    return;
  }
  if (!net_.confirmPid.empty() && !net_.paired) {  // §6.3: "Pair with {name} ({hint})?"
    textAt(cv, fonts::body(), 233, L(182, 160), R ? "Mă leg de contul lui" : "Pair with", kCream, kDim);
    textAt(cv, fonts::title(), 233, L(222, 204), ellipsize(fonts::title(), net_.confirmName + "?", g_.s(320)), kMint);
    textAt(cv, fonts::caption(), 233, L(260, 248), ellipsize(fonts::caption(), net_.confirmHint, g_.s(320)), kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    rimBottom(cv, R ? "doar dacă tu ai scanat codul" : "only if you scanned the code", kCream, kFaint);
    return;
  }
  if (net_.cloudProblem == 2 || net_.cloudProblem == 3 || net_.cloudRefused) {
    const std::string what = net_.cloudProblem == 2 ? (R ? "SOUL nu e înregistrat" : "This SOUL is not registered")
                             : net_.cloudProblem == 3 ? (R ? "SOUL e al altui cont" : "This SOUL belongs to another account")
                                                      : (R ? "SOUL Cloud nu mă acceptă" : "SOUL Cloud won't take me");
    std::string l[2];
    const int n = wrapLines(fonts::body(), what, g_.s(300), l, 2);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::body(), 233, L(186, 166) + i * L(32, 44), l[i], kAmber);
    textAt(cv, fonts::caption(), 233, L(254, 262), R ? "Scrie-ne cu codul acesta:" : "Write to us with this id:", kCream, kDim);
    textAt(cv, fonts::caption(), 233, L(282, 298), id, kCream);
    return;
  }
  if (net_.paired && !net_.cloudHost.empty() && pairDoneT_ <= 0) {
    // "Connect Claude": the phone page where the owner pastes the key of their Claude account
    textAt(cv, fonts::body(), 233, L(168, 152), R ? "Conectează Claude" : "Connect Claude", kMint);
    textAt(cv, fonts::caption(), 233, L(198, 188), R ? "Scanează cu telefonul" : "Scan with your phone", kCream, kDim);
    drawQr(cv, "https://" + net_.cloudHost + "/pair/brain?d=" + id, 233, L(296, 290), L(140, 128));
    rimBottom(cv, net_.owner.empty() ? net_.cloudHost : (R ? "legat de " : "paired with ") + net_.owner, kCream, kFaint);
    return;
  }
  if (net_.paired) {
    textAt(cv, fonts::title(), 233, L(190, 166), R ? "Legat de cont" : "Paired", kMint);
    if (!net_.owner.empty()) textAt(cv, fonts::body(), 233, L(230, 208), net_.owner, kCream);
    std::string l[3];
    const int n = wrapLines(fonts::caption(), R ? "Claude-ul tău poate pune acum notițe, mementouri și alarme pe mine."
                                                : "Your Claude can now put notes, reminders and alarms on me.",
                            g_.s(L(300, 340)), l, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::caption(), 233, L(272, 252) + i * L(26, 34), l[i], kCream, kDim);
    rimBottom(cv, R ? "dezlegi din pagina contului" : "unpair from your account page", kCream, kFaint);
    return;
  }
  if (!net_.configured || !net_.connected) {
    textAt(cv, fonts::body(), 233, 214, R ? "Întâi Wi-Fi-ul" : "Wi-Fi first", kCream);
    textAt(cv, fonts::caption(), 233, 248, net_.connecting ? (R ? "mă conectez…" : "connecting…") : (R ? "apoi apare codul aici" : "then the code shows up here"),
           kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    return;
  }
  if (net_.pairCode.size() != 8) {
    const float pulse = 0.6f + 0.35f * sinf(animT() * 3.0f);
    textAt(cv, fonts::body(), 233, 214, net_.cloudOnline ? (R ? "Aștept codul…" : "Getting a code…") : (R ? "Ajung la SOUL Cloud…" : "Reaching SOUL Cloud…"),
           kCream, pulse);
    textAt(cv, fonts::caption(), 233, 252, id, kCream, kFaint);
    return;
  }
  textAt(cv, fonts::caption(), 233, L(166, 152), R ? "Codul tău de legare" : "Your pairing code", kCream, kDim);
  textAt(cv, fonts::title(), 233, L(204, 192), net_.pairCode.substr(0, 4) + "-" + net_.pairCode.substr(4), kAmber);
  if (net_.trialLeft > 0) {  // a factory unit answers a few questions before it is paired
    char b[64];
    snprintf(b, sizeof b, R ? "%d răspunsuri gratuite până atunci" : "%d free answers until then", net_.trialLeft);
    textAt(cv, fonts::caption(), 233, L(238, 228), b, kCream, kFaint);
  }
  if (!net_.pairUrl.empty()) drawQr(cv, net_.pairUrl, 233, L(322, 314), L(118, 112));
  std::string host = net_.pairUrl.size() > 8 ? net_.pairUrl.substr(8) : std::string();
  host = host.substr(0, host.find('/'));
  rimBottom(cv, host.empty() ? (R ? "scanează sau scrie codul în cont" : "scan, or type the code in your account")
                             : (R ? "scanează sau: " : "scan, or: ") + host + "/pair",
            kCream, kFaint);
}

// ------------------------------------------------------------- the wheels ---

bool Os::buildCoreWheel(std::vector<WheelRow>& out) const {
  const bool R = ro();
  auto row = [&](int id, const std::string& title) -> WheelRow& {
    WheelRow r;
    r.id = id;
    r.title = title;
    r.valueC = pal_.e1;
    out.push_back(r);
    return out.back();
  };
  auto addNew = [&](int id, const char* en, const char* ro_) {
    WheelRow& r = row(id, R ? ro_ : en);
    r.kind = RowNew;
  };
  switch (view_) {
    case View::Settings: {
      static const char* const kLabels[2][14] = {
          {"Brightness", "AI", "Wi-Fi", "Language", "My SOUL", "Text size", "About", "Debug overlay", "Screen off at night",
           "Claude & ChatGPT on me", "Start over", "Memory", "Apps", "Reduce motion"},
          {"Luminozitate", "AI", "Wi-Fi", "Limba", "SOUL-ul meu", "Mărimea textului", "Despre", "Depanare", "Ecran stins noaptea",
           "Claude & ChatGPT pe mine", "De la capăt", "Memorie", "Aplicații", "Mai puțină mișcare"}};
      static const int kOrder[14] = {4, 1, 2, 11, 12, 0, 5, 3, 13, 8, 9, 6, 7, 10};
      static const char* const kBr[2][4] = {{"Auto", "Low", "Mid", "High"}, {"Auto", "Mică", "Medie", "Mare"}};
      const Rgb state = kCream.scaled(0.74f);
      for (int k : kOrder) {
        std::string v;
        Rgb c = state;
        switch (k) {
          case 0: v = kBr[R][set_.bright % 4]; break;
          case 1:
            v = (aiMode() == AiMode::Cloud ? "SOUL Cloud" : aiMode() == AiMode::Claude ? "Claude" : aiMode() == AiMode::ChatGpt ? "ChatGPT"
                 : aiMode() == AiMode::Bridge ? (R ? "Calculator" : "Computer") : (R ? "Fără" : "None")) + std::string(" \xE2\x80\xBA");
            c = aiMode() == AiMode::None ? state : kAmber;
            break;
          case 2:
            v = (net_.connected ? net_.ssid : net_.configured ? (R ? "Neconectat" : "Not connected") : (R ? "Nesetat" : "Not set")) + " \xE2\x80\xBA";
            c = pal_.e1;
            break;
          case 3: v = R ? "Română" : "English"; break;
          case 4: v = std::string(set_.name) + " \xE2\x80\xBA"; c = pal_.e2; break;
          case 5: v = set_.largeText ? (R ? "mare" : "large") : (R ? "normal" : "normal"); break;
          case 6: v = "\xE2\x80\xBA"; c = pal_.e1; break;
          case 7: v = set_.debug ? (R ? "Pornit" : "On") : (R ? "Oprit" : "Off"); break;
          case 8: v = set_.nightOff ? (R ? "Pornit" : "On") : (R ? "Oprit" : "Off"); break;
          case 9:
            v = !net_.paired ? (R ? "Nelegat" : "Not paired") : net_.connectorsPaused ? (R ? "Pe pauză" : "Paused") : (R ? "Pornite" : "On");
            break;
          case 10: v = R ? "ține" : "hold"; c = kAmber; break;
          case 11: v = std::to_string(mem_ ? mem_->size() : 0) + " \xE2\x80\xBA"; c = pal_.e1; break;  // SOUL Memory
          case 12: v = std::to_string(visibleApps()) + " \xE2\x80\xBA"; c = pal_.e1; break;  // Settings › Apps
          default: v = set_.reduceMotion ? (R ? "Pornit" : "On") : (R ? "Oprit" : "Off"); break;  // 13: reduce motion
        }
        WheelRow& r = row(IdRow + k, kLabels[R][k]);
        r.value = v;
        r.valueC = c;
      }
      return true;
    }
    case View::AiMode: {
      static const AiMode kModes[] = {AiMode::Cloud, AiMode::Claude, AiMode::ChatGpt, AiMode::Bridge, AiMode::None};
      const char* labels[] = {R ? "Claude-ul tău" : "Your Claude", R ? "Claude · cheia ta" : "Claude · your key",
                              R ? "ChatGPT · cheia ta" : "ChatGPT · your key", R ? "Claude de pe calculator" : "Claude on my computer",
                              R ? "Fără AI" : "No AI"};
      for (int i = 0; i < 5; ++i) {
        std::string st;
        switch (i) {
          case 0:
            st = !net_.relay ? (R ? "adresa se pune din telefon" : "set its address from a phone")
                 : net_.cloudUpdate ? (R ? "actualizează SOUL" : "update SOUL")
                 : net_.cloudRefused ? (R ? "SOUL nu e acceptat" : "this SOUL was refused")
                 : net_.paired ? (net_.owner.empty() ? std::string(R ? "prin SOUL Cloud" : "via SOUL Cloud") : (R ? "legat · " : "paired · ") + net_.owner)
                 : (R ? "atinge ca să-l legi" : "tap to pair it");
            break;
          case 1: st = net_.keyClaude ? net_.maskClaude : (R ? "are nevoie de o cheie" : "needs a key"); break;
          case 2: st = net_.keyOpenai ? net_.maskOpenai : (R ? "are nevoie de o cheie" : "needs a key"); break;
          case 3:
            st = net_.bridgeOnline ? (R ? "conectat · " : "connected · ") + (net_.bridgeName.empty() ? std::string("PC") : net_.bridgeName)
                 : net_.bridgePaired ? (R ? "calculatorul e oprit" : "the computer is off")
                                     : (R ? "Claude Code-ul tău" : "your own Claude Code");
            break;
          default: st = R ? "ore și minutare pe device" : "times and timers on the device"; break;
        }
        WheelRow& r = row(IdRow + i, labels[i]);
        r.sub = st;
        if (aiMode() == kModes[i]) r.kind = RowSel;
      }
      if (net_.keyClaude || net_.keyOpenai) {
        WheelRow& r = row(IdForget, R ? "Uită cheile" : "Forget keys");
        r.value = R ? "ține" : "tap";
        r.valueC = kAmber;
      }
      return true;
    }
    case View::Alarms: {
      const int n = alarms_ ? alarms_->count() : 0;
      for (int i = 0; i < n; ++i) {
        const Alarm& a = alarms_->at(i);
        char b[16];
        snprintf(b, sizeof b, "%02u:%02u", a.hour, a.minute);
        WheelRow& r = row(IdRow + i, "");
        r.tag = b;
        r.bigTag = true;
        r.kind = RowToggle;
        r.on = a.enabled;
        r.dim = a.enabled ? 1.0f : 0.55f;
        r.sub = daysText(a.days, R) + (a.label[0] ? std::string(" · ") + a.label : std::string());
        // SOUL S (the critic, 2026-10-22: "weekdays …" lost the label): when that does not fit, the label first and
        // the days in their short form ("Wake up · Mo–Fr"); the label alone if even that is too long
        if (sGlass() && a.label[0]) r.subShort = std::string(a.label) + " \xC2\xB7 " + daysShort(a.days, R);
      }
      addNew(IdNew, "+ New", "+ Nouă");
      return true;
    }
    case View::Notes: {
      for (int i = 0; i < (int)notes_.size(); ++i) {
        WheelRow& r = row(IdRow + i, notes_[(size_t)i].text);
        const uint32_t t = notes_[(size_t)i].t;
        if (t && now_) {
          char b[32];
          const bool today = t / 86400 == now_ / 86400;
          static const char* const en[] = {"Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"};
          static const char* const rr[] = {"Jo", "Vi", "Sâ", "Du", "Lu", "Ma", "Mi"};
          snprintf(b, sizeof b, "%s %02u:%02u", today ? (R ? "azi" : "today") : (R ? rr : en)[(t / 86400) % 7], (unsigned)(t % 86400 / 3600),
                   (unsigned)(t % 3600 / 60));
          r.sub = b;
        }
      }
      addNew(IdNew, "+ New", "+ Nouă");
      return true;
    }
    default: return false;
  }
}

}  // namespace suflet
