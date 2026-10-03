// SoulOS on the device: what each screen shows. Design language "Orbit"
// (os/SPEC.md §11): true black, one light at a time, words instead of
// buttons (an action is a word with a line under it), the rim carries the
// title, the clock and hints. Layout in design pixels of the 466 px disc,
// scaled by DisplayGeometry to the 480 px panel.
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "Os.h"
#include "QrImage.h"

namespace suflet {

using namespace eyes;

static const Rgb kCream = Rgb::hex(0xFFF0C8), kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4),
                 kIce = Rgb::hex(0x9FC6FF);
static const float kDim = 0.62f, kFaint = 0.42f;

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
  IdRow = 100,
};

static const char* const kNames[] = {"Pixel", "Miso", "Luna", "Bobo", "Nori", "Kiki", "Tofu", "Zuzu",
                                     "Mochi", "Iris", "Pip",  "Sol",  "Dodo", "Fifi", "Mura", "Bean"};

static const Font& fontOf(int i, bool large) {
  if (large) ++i;
  switch (i) {
    case 0: return fonts::small();
    case 1: return fonts::text();
    default: return fonts::large();
  }
}

static std::string ellipsize(const Font& f, const std::string& s, float maxW) {
  if (Canvas::measureText(f, s.c_str()) <= maxW) return s;
  std::string out;
  const char* p = s.c_str();
  const char* end = p + s.size();
  while (p < end) {
    const char* q = p;
    utf8::next(q, end);
    std::string t = out + std::string(p, q - p) + "\xE2\x80\xA6";
    if (Canvas::measureText(f, t.c_str()) > maxW) break;
    out.append(p, q - p);
    p = q;
  }
  return out + "\xE2\x80\xA6";
}

static std::string appName(View v, bool ro) {
  switch (v) {
    case View::Talk: return ro ? "Vorbește" : "Talk";
    case View::Alarms: return ro ? "Alarme" : "Alarms";
    case View::Timer: return ro ? "Minutar" : "Timer";
    case View::Notes: return ro ? "Notițe" : "Notes";
    case View::Today: return ro ? "Azi" : "Today";
    case View::Claude: return "Claude";
    case View::Settings: return ro ? "Setări" : "Settings";
    default: return "";
  }
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
        add(-1, 233, 150, 0, 0, R ? "Cum mă cheamă?" : "What's my name?", kCream, 1, false);
        for (int i = 0; i < 3; ++i) {
          const int k = (int)(((birth_.seed >> (i * 5)) + (uint32_t)i * 5u) % 16u);
          add(IdRow + i, 233, 212 + i * 54, 220, 52, kNames[k], kCream, 2, true);
        }
        add(IdType, 233, 382, 220, 46, R ? "Scrie un nume" : "Type a name", kCream, 0, true, kDim);
      } else if (bootStep_ == BootStep::Brain) {
        add(-1, 233, 138, 0, 0, R ? "Cine mă ajută să gândesc?" : "Who helps me think?", kCream, 1, false);
        static const AiMode kModes[] = {AiMode::Cloud, AiMode::Claude, AiMode::ChatGpt, AiMode::None};
        const char* labels[] = {R ? "Conectează Claude" : "Connect Claude", R ? "Claude · cheia ta" : "Claude · your key",
                                R ? "ChatGPT · cheia ta" : "ChatGPT · your key", R ? "Fără AI" : "No AI"};
        for (int i = 0; i < 4; ++i) {
          const bool sel = aiMode() == kModes[i];
          add(IdRow + i, 233, 186 + i * 46, 300, 44, labels[i], sel ? kMint : kCream, 1, sel, sel ? 1 : kDim);
        }
        add(IdNext, 233, 420, 160, 50, R ? "Mai departe ›" : "Next ›", kCream, 1, true);
      }
      break;
    case View::Launcher: {
      add(IdCenter, 233, 336, 300, 72, appName(appView(orbit_), R), kCream, 2, false);
      add(IdRow, 138, 398, 120, 60, "‹ " + appName(appView(orbit_ - 1), R), kCream, 0, false, kDim);
      add(IdRow + 1, 328, 398, 120, 60, appName(appView(orbit_ + 1), R) + " ›", kCream, 0, false, kDim);
      break;
    }
    case View::Talk:
      add(IdType, 233, 410, 180, 54, R ? "Scrie" : "Type", kCream, 1, true);
      break;
    case View::Alarms: {
      const int n = alarms_ ? alarms_->count() : 0;
      const int pages = n > 3 ? (n + 2) / 3 : 1;
      const int p = page_ % pages;
      for (int i = p * 3; i < n && i < p * 3 + 3; ++i) {
        const Alarm& a = alarms_->at(i);
        char b[16];
        snprintf(b, sizeof b, "%02u:%02u", a.hour, a.minute);
        add(IdRow + i, 233, 168 + (i - p * 3) * 66, 330, 62, b, kCream, 2, false, a.enabled ? 1 : kFaint);
      }
      add(IdNew, 233, 376, 180, 50, R ? "+ Nouă" : "+ New", kCream, 1, true);
      break;
    }
    case View::Ringing:
      add(IdSnooze, 150, 400, 150, 60, R ? "Amână" : "Snooze", kAmber, 1, true);
      add(IdStop, 316, 400, 150, 60, R ? "Oprește" : "Stop", kCream, 1, true);
      break;
    case View::Timer:
      if (timerRun_) {
        add(IdPause, 160, 378, 150, 56, timerPaused_ ? (R ? "Pornește" : "Resume") : (R ? "Pauză" : "Pause"), kCream, 1, true);
        add(IdStop, 306, 378, 150, 56, R ? "Oprește" : "Stop", kAmber, 1, true);
      } else {
        static const char* const kP[] = {"1", "3", "5", "10", "25"};
        static const float kX[] = {150, 233, 316, 190, 276}, kY[] = {200, 200, 200, 268, 268};
        for (int i = 0; i < 5; ++i) add(IdRow + i, kX[i], kY[i], 76, 64, kP[i], kCream, 2, true);
      }
      break;
    case View::Notes: {
      const int n = (int)notes_.size();
      const int pages = n > 3 ? (n + 2) / 3 : 1;
      const int p = page_ % pages;
      for (int i = p * 3; i < n && i < p * 3 + 3; ++i)
        add(IdRow + i, 233, 172 + (i - p * 3) * 58, 330, 54, ellipsize(fontOf(1, set_.largeText), notes_[i].text, g_.s(300)), kCream, 1, false);
      add(IdNew, 233, 360, 180, 50, R ? "+ Nouă" : "+ New", kCream, 1, true);
      break;
    }
    case View::NoteView:
      add(IdType, 160, 404, 140, 56, R ? "Editează" : "Edit", kCream, 1, true);
      add(IdDelete, 306, 404, 140, 56, R ? "Șterge" : "Delete", kAmber, 1, true);
      break;
    case View::Settings: {
      static const int kRows = 11;
      const int pages = (kRows + 3) / 4;
      const int p = page_ % pages;
      static const char* const kBr[2][4] = {{"Auto", "Low", "Mid", "High"}, {"Auto", "Mică", "Medie", "Mare"}};
      for (int i = p * 4; i < kRows && i < p * 4 + 4; ++i) {
        std::string v;
        switch (i) {
          case 0: v = kBr[R][set_.bright % 4]; break;
          case 1:
            v = aiMode() == AiMode::Cloud ? "SOUL Cloud" : aiMode() == AiMode::Claude ? "Claude" : aiMode() == AiMode::ChatGpt ? "ChatGPT" : (R ? "Fără AI" : "No AI");
            break;
          case 2: v = net_.connected ? net_.ssid : net_.configured ? (R ? "Neconectat" : "Not connected") : (R ? "Nesetat" : "Not set"); break;
          case 3: v = R ? "Română" : "English"; break;
          case 4: v = std::string(set_.name) + " ›"; break;
          case 5: v = set_.largeText ? (R ? "Mare" : "Large") : (R ? "Normal" : "Normal"); break;
          case 6: v = R ? "Sunt un AI ›" : "I'm an AI ›"; break;
          case 7: v = set_.debug ? (R ? "Pornit" : "On") : (R ? "Oprit" : "Off"); break;
          case 8: v = set_.nightOff ? (R ? "Pornit" : "On") : (R ? "Oprit" : "Off"); break;
          case 9:
            v = !net_.paired ? (R ? "Nelegat" : "Not paired") : net_.connectorsPaused ? (R ? "Pe pauză" : "Paused") : (R ? "Pornite" : "On");
            break;
          default: v = R ? "Ține apăsat" : "Hold"; break;
        }
        add(IdRow + i, 233, 172 + (i - p * 4) * 62, 330, 60, ellipsize(fontOf(1, set_.largeText), v, g_.s(280)), kCream, 1, false);
      }
      break;
    }
    case View::AiMode: {
      static const AiMode kModes[] = {AiMode::Cloud, AiMode::Claude, AiMode::ChatGpt, AiMode::None};
      const char* labels[] = {R ? "Conectează Claude" : "Connect Claude", R ? "Claude · cheia ta" : "Claude · your key",
                              R ? "ChatGPT · cheia ta" : "ChatGPT · your key", R ? "Fără AI" : "No AI"};
      for (int i = 0; i < 4; ++i) {
        const bool sel = aiMode() == kModes[i];
        add(IdRow + i, 233, 136 + i * 60, 320, 58, labels[i], sel ? kMint : kCream, 1, sel);
      }
      if (net_.keyClaude || net_.keyOpenai) add(IdForget, 233, 378, 200, 40, R ? "Uită cheile" : "Forget keys", kAmber, 0, true, kDim);
      break;
    }
    case View::Wifi:
      if (net_.portal) add(IdStopSetup, 233, 404, 200, 50, R ? "Gata" : "Done", kCream, 1, true);
      else add(IdSetup, 233, 300, 260, 56, R ? "Configurează din telefon" : "Set up from a phone", kCream, 1, true);
      if (net_.configured && !net_.portal) add(IdForget, 233, 384, 220, 50, R ? "Uită Wi-Fi (ține)" : "Forget Wi-Fi (hold)", kAmber, 0, true, kDim);
      break;
    case View::MySoul:
      add(IdName, 233, 312, 300, 56, set_.name, kCream, 2, false);
      break;
    case View::Claude:
      if (net_.relay && !claude_.passkey && !claude_.prompt)
        add(IdInbox, 233, 396, 260, 52, R ? "Întreabă-l pe Claude ›" : "Ask my Claude ›", kCream, 1, true);
      break;
    case View::Pair:
      if (!net_.confirmPid.empty() && !net_.paired) {  // "Pair with Ana?" answered by a touch only
        add(IdAccept, 160, 372, 150, 60, R ? "Da, leagă" : "Yes, pair", kMint, 1, true);
        add(IdReject, 306, 372, 150, 60, R ? "Nu" : "No", kAmber, 1, true);
      } else if (!net_.configured || (!net_.connected && !net_.connecting)) {
        add(IdSetup, 233, 330, 260, 56, R ? "Configurează din telefon" : "Set up from a phone", kCream, 1, true);
      }
      break;
    case View::Answer:
      if (acceptMode_) {
        add(IdAccept, 160, 392, 150, 58, R ? "Acceptă" : "Accept", kMint, 1, true);
        add(IdReject, 306, 392, 150, 58, R ? "Nu" : "No", kAmber, 1, true);
      }
      break;
    default: break;
  }
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

void Os::rimTop(Canvas& cv, const std::string& s, Rgb c, float alpha) {
  cv.drawTextArc(fonts::small(), g_.cx(), g_.cy(), g_.s(212), -1.5707963f, s.c_str(), c, alpha, false, 1.0f);
}

void Os::rimBottom(Canvas& cv, const std::string& s, Rgb c, float alpha) {
  cv.drawTextArc(fonts::small(), g_.cx(), g_.cy(), g_.s(210), 1.5707963f, s.c_str(), c, alpha, true, 1.0f);
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
    const Font& f = fontOf(it.font, set_.largeText);
    textAt(cv, f, it.x, it.y, it.label, it.color, it.alpha);
    if (it.underline) {
      const float w = (float)Canvas::measureText(f, it.label.c_str());
      const float y = g_.s(it.y) + (f.ascent - f.descent) * 0.5f + 5;
      cv.roundRect(g_.s(it.x) - w * 0.5f, y, g_.s(it.x) + w * 0.5f, y + 2.0f, 1.0f, it.color, it.alpha * fade_ * 0.9f);
    }
    if (holdItem_ == it.id && it.id >= 0) {  // hold progress under the word
      const float w = g_.s(it.w) * 0.8f * (holdItemT_ > 1 ? 1 : holdItemT_);
      const float y = g_.s(it.y) + (f.ascent - f.descent) * 0.5f + 9;
      cv.roundRect(g_.s(it.x) - w * 0.5f, y, g_.s(it.x) + w * 0.5f, y + 3.0f, 1.5f, kAmber, 0.9f);
    }
  }
}

void Os::render(Canvas& cv) {
  cv.fill(pal::kBlack);  // under the clip only
  switch (view_) {
    case View::Keyboard: kb_.render(cv); break;
    case View::Dial: tp_.render(cv); break;
    case View::Boot: drawBoot(cv); break;
    case View::Home: drawHome(cv); break;
    case View::Launcher: drawLauncher(cv); break;
    case View::Today: drawToday(cv); break;
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
    default: break;
  }
  if (view_ != View::Keyboard && view_ != View::Dial) drawToast(cv);
  if (set_.debug) drawPerf(cv);
  drawnView_ = view_;
}

void Os::drawToast(Canvas& cv) {
  if (toastLeft_ <= 0 || toast_.empty()) return;
  // over the top rim (it hides the title while it shows)
  cv.fillRect(g_.rect(60, 0, 406, 62), pal::kBlack);
  rimTop(cv, ellipsize(fonts::small(), toast_, g_.s(330)), toastColor_);
}

void Os::drawPerf(Canvas& cv) {
  char a[64], b[64];
  snprintf(a, sizeof a, "%.0f fps  %.1f ms  cpu %.0f%%", perf.fps, perf.frameMs, perf.cpu * 100);
  snprintf(b, sizeof b, "draw %.1f  push %.1f  heap %u K  ps %u K", perf.renderMs, perf.pushMs, (unsigned)perf.heapKb,
           (unsigned)perf.psramKb);
  cv.fillRect(g_.rect(110, 404, 356, 452), pal::kBlack);
  cv.drawText(fonts::small(), g_.cx(), (int)g_.s(424), a, kIce, 0.9f, Align::Center);
  cv.drawText(fonts::small(), g_.cx(), (int)g_.s(446), b, kIce, 0.7f, Align::Center);
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
        textAt(cv, fonts::large(), 233, 338, d.name, kCream, al);
        char b[64];
        snprintf(b, sizeof b, "%s · #%03d / %d", kRarityName[(int)d.rarity], d.num, kDesignCount);
        textAt(cv, fonts::small(), 233, 374, b, Rgb::hex(kRarityColor[(int)d.rarity]), al);
        int cnt = 0;
        for (int i = 0; i < kDesignCount; ++i)
          if (kDesigns[i].rarity == d.rarity) ++cnt;
        snprintf(b, sizeof b, R ? "1 din %d" : "1 in %d", (int)lround(cnt / kRarityRate[(int)d.rarity]));
        textAt(cv, fonts::small(), 233, 400, b, kCream, al * kFaint);
        rimBottom(cv, R ? "atinge ca să ne cunoaștem" : "tap to meet me", kCream, kDim * al);
      }
      return;
    }
    case BootStep::Name:
    case BootStep::Brain:
      buildItems(items_);
      drawItems(cv, items_);
      if (bootStep_ == BootStep::Brain) {
        if (aiMode() != AiMode::None) {
          const bool needs = needsSetup();
          if (needs && net_.portal) {
            textAt(cv, fonts::small(), 233, 370, (R ? "Pe telefon: Wi-Fi " : "On your phone: Wi-Fi ") + net_.apName + " · " + net_.apPass, kAmber);
            textAt(cv, fonts::small(), 233, 394, (R ? "apoi deschide " : "then open ") + net_.portalUrl.substr(7), kAmber, kDim);
          } else if (!needs) {
            textAt(cv, fonts::small(), 233, 380, R ? "Gata de vorbă" : "Ready to talk", kMint);
          }
        } else {
          textAt(cv, fonts::small(), 233, 380, R ? "Ore, alarme, minutare: pe device" : "Times, alarms, timers: on the device", kCream, kDim);
        }
        rimTop(cv, R ? "2 / 3" : "2 / 3", kCream, kFaint);
      } else {
        rimTop(cv, "1 / 3", kCream, kFaint);
      }
      return;
    case BootStep::Hold:
      textAt(cv, fonts::large(), 233, 352, R ? "Ține degetul pe sticlă" : "Hold the glass", listening_ ? kIce : kCream);
      textAt(cv, fonts::small(), 233, 390, R ? "așa îmi vorbești" : "that's how you talk to me", kCream, kDim);
      rimTop(cv, "3 / 3", kCream, kFaint);
      rimBottom(cv, R ? "butonul: sari peste" : "button: skip", kCream, kFaint);
      return;
    default: return;
  }
}

void Os::drawHome(Canvas& cv) {
  const bool R = ro();
  std::string top = clockText(now_);
  if (timerRun_) {
    const int s = timerLeft();
    char b[24];
    snprintf(b, sizeof b, "  ·  %d:%02d", s / 60, s % 60);
    top += b;
  }
  rimTop(cv, top, kCream, kDim);
  if (claude_.passkey) {
    char b[12];
    snprintf(b, sizeof b, "%06lu", (unsigned long)claude_.passkey);
    textAt(cv, fonts::large(), 233, 392, b, kAmber);
    rimBottom(cv, R ? "codul pentru Claude Desktop" : "pairing code for Claude Desktop", kCream, kDim);
  } else if (claude_.prompt) {
    rimBottom(cv, R ? "Claude te așteaptă · ține = da · 2× = nu" : "Claude needs you · hold = yes · 2× = no", kAmber);
  } else if (thinking_) {
    rimBottom(cv, R ? "mă gândesc…" : "thinking…", kAmber, kDim);
  }
}

void Os::drawLauncher(Canvas& cv) {
  const bool R = ro();
  buildItems(items_);
  drawItems(cv, items_);
  // one live fact under the word
  std::string fact;
  switch (appView(orbit_)) {
    case View::Talk:
      fact = aiMode() == AiMode::None ? (R ? "Fără AI" : "No AI") : aiMode() == AiMode::Cloud ? "SOUL Cloud" : aiMode() == AiMode::Claude ? "Claude" : "ChatGPT";
      break;
    case View::Alarms: fact = nextAlarmText(); if (fact.empty()) fact = R ? "nicio alarmă" : "no alarms"; break;
    case View::Timer: {
      if (timerRun_) {
        char b[16];
        snprintf(b, sizeof b, "%d:%02d", timerLeft() / 60, timerLeft() % 60);
        fact = b;
      } else fact = R ? "1 · 3 · 5 · 10 · 25 min" : "1 · 3 · 5 · 10 · 25 min";
      break;
    }
    case View::Notes: fact = std::to_string(notes_.size()) + (R ? " notițe" : " notes"); break;
    case View::Today: fact = formatNow(now_, R).substr(0, formatNow(now_, R).find(',')); break;
    case View::Claude: fact = claude_.prompt ? (R ? "te așteaptă" : "needs you") : claude_.busy ? (R ? "lucrează" : "working") : claude_.linked ? (R ? "conectat" : "connected") : (R ? "neconectat" : "not connected"); break;
    case View::Settings: fact = set_.name; break;
    default: break;
  }
  textAt(cv, fonts::small(), 233, 372, fact, kCream, kDim);
  rimTop(cv, clockText(now_), kCream, kFaint);
}

void Os::drawToday(Canvas& cv) {
  const bool R = ro();
  textAt(cv, fonts::digits(), 233, 196, clockText(now_), kCream);
  std::string date = formatNow(now_, R);
  const size_t comma = date.rfind(',');
  if (comma != std::string::npos) date = date.substr(0, comma);
  textAt(cv, fonts::small(), 233, 250, date, kCream, kDim);
  std::string rows[4];
  int n = 0;
  const std::string na = nextAlarmText();
  rows[n++] = na.empty() ? (R ? "Nicio alarmă" : "No alarm set") : (R ? "Alarmă " : "Alarm ") + na;
  if (timerRun_) {
    char b[32];
    snprintf(b, sizeof b, "%s %d:%02d", timerFocus_ ? "Focus" : (R ? "Minutar" : "Timer"), timerLeft() / 60, timerLeft() % 60);
    rows[n++] = b;
  } else if (!rems_.empty()) {
    rows[n++] = clockText(rems_.front().when) + " " + rems_.front().text;
  }
  rows[n++] = claude_.prompt ? (R ? "Claude te așteaptă" : "Claude needs you")
              : claude_.busy ? (R ? "Claude lucrează" : "Claude is working")
              : claude_.linked ? (R ? "Claude conectat" : "Claude connected") : (R ? "Claude neconectat" : "Claude not connected");
  char b[48];
  const char* wifi = net_.connected ? (R ? "pornit" : "on") : (R ? "oprit" : "off");
  if (power_.batPct >= 0) snprintf(b, sizeof b, "%s %d%%%s  ·  Wi-Fi %s", R ? "Baterie" : "Battery", power_.batPct, power_.charging ? "+" : "", wifi);
  else snprintf(b, sizeof b, "Wi-Fi %s", wifi);
  rows[n++] = b;
  for (int i = 0; i < n; ++i)
    textAt(cv, fonts::small(), 233, 292 + i * 32, ellipsize(fonts::small(), rows[i], g_.s(320)), i == 1 && claude_.prompt ? kAmber : kCream, i == 0 ? 1.0f : kDim);
}

void Os::drawTalk(Canvas& cv) {
  const bool R = ro();
  const char* src = aiMode() == AiMode::None ? (R ? "Fără AI · pe device" : "No AI · on the device")
                    : aiMode() == AiMode::Cloud ? "SOUL Cloud"
                    : aiMode() == AiMode::Claude ? (R ? "Claude · cheia ta" : "Claude · your key")
                                                 : (R ? "ChatGPT · cheia ta" : "ChatGPT · your key");
  rimTop(cv, src, kCream, kDim);
  std::string hint;
  if (listening_) hint = voice_ ? (R ? "Ascult…" : "Listening…") : (R ? "Dă drumul și scrie" : "Let go, then type");
  else if (aiMode() != AiMode::None && !net_.connected) hint = R ? "Nu am Wi-Fi: înțeleg doar ore și minutare" : "No Wi-Fi: I only get times and timers";
  else if (aiMode() == AiMode::None) hint = R ? "Fără AI: ore, alarme, minutare" : "No AI: times, alarms and timers";
  else hint = voice_ ? (R ? "Ține sticla și întreabă" : "Hold the glass and ask") : (R ? "Ține sticla sau scrie" : "Hold the glass, or type");
  textAt(cv, fonts::small(), 233, 364, hint, listening_ ? kIce : kCream, listening_ ? 1 : kDim);
  buildItems(items_);
  drawItems(cv, items_);
}

void Os::drawAnswer(Canvas& cv) {
  const bool R = ro();
  if (thinking_) {
    const char* who = aiMode() == AiMode::Claude ? "Claude" : aiMode() == AiMode::ChatGpt ? "ChatGPT" : "SOUL";
    rimTop(cv, std::string(who) + (R ? " se gândește…" : " is thinking…"), kAmber, 0.9f);
    std::string lines[3];
    const int n = wrapLines(fonts::small(), reply_.say, g_.s(320), lines, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 250 + i * 28, lines[i], kCream, kDim);
    return;
  }
  rimTop(cv, answerSrc_, kCream, kFaint);
  const bool card = !cardTitle_.empty();
  const bool big = !card && reply_.say.size() <= 120;
  const Font& f = big ? fontOf(1, set_.largeText) : fonts::small();
  const float lh = big ? 32.0f : 27.0f;
  std::string lines[7];
  const int n = reply_.say.empty() ? 0 : wrapLines(f, reply_.say, g_.s(big ? 330 : 350), lines, big ? 4 : card ? 7 : 6);
  float y = 236;
  if (card) {  // a card pushed by SOUL Cloud / your Claude: a title, then the text as written
    textAt(cv, fonts::text(), 233, 196, ellipsize(fonts::text(), cardTitle_, g_.s(320)), kMint);
    y = 232;
  }
  if (lastErr_ != AiErr::None) {  // what went wrong, in one line that says what to do
    std::string el[3];
    const int m = wrapLines(fonts::text(), aiErrText(lastErr_, R), g_.s(320), el, 3);
    for (int i = 0; i < m; ++i, y += 32) textAt(cv, fonts::text(), 233, y, el[i], kAmber);
    y += 4;
  }
  for (int i = 0; i < n; ++i, y += lh) textAt(cv, f, 233, y, lines[i], kCream, lastErr_ != AiErr::None ? kDim : 1.0f);
  y += 6;
  if (acceptMode_) {  // "Claude wants to set 03:00": armed only after Accept
    buildItems(items_);
    drawItems(cv, items_);
    rimBottom(cv, R ? "nu sună până nu accepți" : "it won't ring unless you accept", kCream, kFaint);
    return;
  }
  if (cardHidden_) {
    textAt(cv, fonts::small(), 233, y + 8, R ? "Privat · atinge ca să vezi" : "Private · tap to show", kCream, kDim);
    rimBottom(cv, R ? "atinge ca să vezi" : "tap to show", kCream, kFaint);
    return;
  }
  for (const std::string& c : chips_) {  // a drawn tick (Nunito has no ✓) + the chip text
    const Font& f = fonts::small();
    const float tw = (float)Canvas::measureText(f, c.c_str()), tick = 18;
    const float x0 = g_.cx() - (tw + tick + 8) * 0.5f, cyp = g_.s(y);
    static Path p;
    if (p.reserve(256)) {
      p.clear();
      const float pts[6] = {x0, cyp, x0 + tick * 0.38f, cyp + tick * 0.36f, x0 + tick, cyp - tick * 0.42f};
      p.stroke(pts, 3, 3.2f);
      face_.raster().fill(cv, p, kMint, fade_);
    }
    cv.drawText(f, x0 + tick + 8, (int)lroundf(cyp + (f.ascent - f.descent) * 0.5f), c.c_str(), kMint, fade_, Align::Left);
    y += 27;
  }
  if (reply_.rejected > 0) {
    char b[48];
    snprintf(b, sizeof b, R ? "%d acțiuni ignorate" : "%d action%s ignored", reply_.rejected, (!R && reply_.rejected > 1) ? "s" : "");
    textAt(cv, fonts::small(), 233, y, b, kCream, kFaint);
  }
  rimBottom(cv, R ? "atinge ca să închizi" : "tap to close", kCream, kFaint);
}

void Os::drawAlarms(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "ALARME" : "ALARMS", kCream, kDim);
  buildItems(items_);
  const int n = alarms_ ? alarms_->count() : 0;
  if (!n) textAt(cv, fonts::small(), 233, 250, R ? "Nicio alarmă încă" : "No alarms yet", kCream, kDim);
  for (const Item& it : items_) {
    if (it.id < IdRow) continue;
    const Alarm& a = alarms_->at(it.id - IdRow);
    // time on the left of centre, the state word on the right, days + label under
    textAt(cv, fonts::large(), 205, it.y - 8, it.label, kCream, it.alpha);
    textAt(cv, fonts::small(), 318, it.y - 8, a.enabled ? (R ? "PORNIT" : "ON") : (R ? "OPRIT" : "OFF"), a.enabled ? kMint : kCream,
           a.enabled ? 1 : kFaint);
    std::string sub = daysText(a.days, R);
    if (a.label[0]) sub += std::string(" · ") + a.label;
    textAt(cv, fonts::small(), 233, it.y + 20, ellipsize(fonts::small(), sub, g_.s(300)), kCream, kFaint);
    if (holdItem_ == it.id) {
      const float w = g_.s(260) * (holdItemT_ > 1 ? 1 : holdItemT_);
      cv.roundRect(g_.cx() - w / 2, g_.s(it.y + 34), g_.cx() + w / 2, g_.s(it.y + 34) + 3, 1.5f, kAmber, 0.9f);
    }
  }
  for (const Item& it : items_)
    if (it.id == IdNew) {
      std::vector<Item> one(1, it);
      drawItems(cv, one);
    }
  if (n > 3) rimBottom(cv, R ? "glisează în sus: mai multe · ține = șterge" : "swipe up: more · hold = delete", kCream, kFaint);
  else if (n) rimBottom(cv, R ? "atinge = pornit/oprit · ține = șterge" : "tap = on/off · hold = delete", kCream, kFaint);
}

void Os::drawRinging(Canvas& cv) {
  const bool R = ro();
  std::string label;
  if (timerRinging_) label = timerFocus_ ? (R ? "Focus gata" : "Focus done") : (R ? "Minutar gata" : "Timer done");
  else if (ringingAlarm_ >= 0 && alarms_ && ringingAlarm_ < alarms_->count()) label = alarms_->at(ringingAlarm_).label;
  textAt(cv, fonts::digits(), 233, 300, clockText(now_), kCream);
  textAt(cv, fonts::text(), 233, 348, label, timerRinging_ ? kMint : kAmber);
  buildItems(items_);
  if (timerRinging_) {
    for (const Item& it : items_)
      if (it.id == IdStop) {
        Item c = it;
        c.x = 233;
        std::vector<Item> one(1, c);
        drawItems(cv, one);
      }
  } else {
    drawItems(cv, items_);
  }
}

void Os::drawTimer(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, timerFocus_ && timerRun_ ? "FOCUS" : (R ? "MINUTAR" : "TIMER"), kCream, kDim);
  buildItems(items_);
  if (timerRun_) {
    const int s = timerLeft();
    char b[16];
    snprintf(b, sizeof b, "%d:%02d", s / 60, s % 60);
    textAt(cv, fonts::digits(), 233, 262, b, timerPaused_ ? kAmber : kCream);
    // progress on the rim (cream arc, from the top, clockwise)
    const float frac = timerTotal_ > 0 ? timerLeft_ / timerTotal_ : 0;
    if (frac > 0.002f) {
      const float a0 = -1.5707963f;
      face_.raster().ring(cv, g_.cx(), g_.cy(), g_.s(226), g_.s(6), kCream, 0.85f * fade_, a0, a0 + 6.2831853f * frac);
    }
  } else {
    textAt(cv, fonts::small(), 233, 316, R ? "minute · 25 = focus" : "minutes · 25 = focus", kCream, kFaint);
  }
  drawItems(cv, items_);
}

void Os::drawNotes(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "NOTIȚE" : "NOTES", kCream, kDim);
  if (notes_.empty()) textAt(cv, fonts::small(), 233, 236, R ? "Nicio notiță încă" : "No notes yet", kCream, kDim);
  buildItems(items_);
  drawItems(cv, items_);
  if (notes_.size() > 3) rimBottom(cv, R ? "glisează în sus: mai vechi" : "swipe up: older", kCream, kFaint);
  else if (!notes_.empty()) rimBottom(cv, R ? "ține = șterge" : "hold = delete", kCream, kFaint);
}

void Os::drawNoteView(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "NOTIȚĂ" : "NOTE", kCream, kDim);
  if (noteSel_ < 0 || noteSel_ >= (int)notes_.size()) return;
  std::string lines[7];
  const int n = wrapLines(fonts::small(), notes_[noteSel_].text, g_.s(330), lines, 7);
  for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 150 + i * 28, lines[i], kCream);
  buildItems(items_);
  drawItems(cv, items_);
  rimBottom(cv, R ? "ține Șterge ca să ștergi" : "hold Delete to delete", kCream, kFaint);
}

void Os::drawClaude(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, "CLAUDE", kCream, kDim);
  if (claude_.passkey) {
    char b[12];
    snprintf(b, sizeof b, "%06lu", (unsigned long)claude_.passkey);
    textAt(cv, fonts::small(), 233, 180, R ? "Codul de pe ecran, în Claude:" : "Type this code in Claude:", kCream, kDim);
    textAt(cv, fonts::digits(), 233, 260, b, kAmber);
    return;
  }
  if (claude_.prompt) {
    textAt(cv, fonts::small(), 233, 168, R ? "Claude cere voie" : "Claude asks", kAmber);
    textAt(cv, fonts::large(), 233, 214, ellipsize(fonts::large(), claude_.tool, g_.s(330)), kCream);
    std::string lines[3];
    const int n = wrapLines(fonts::small(), claude_.hint, g_.s(330), lines, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 256 + i * 26, lines[i], kCream, kDim);
    rimBottom(cv, R ? "ține = da · 2× = nu" : "hold = yes · 2× = no", kAmber);
    return;
  }
  if (!claude_.linked) {
    textAt(cv, fonts::text(), 233, 176, R ? "Neconectat" : "Not connected", kCream);
    textAt(cv, fonts::small(), 233, 222, "Claude Desktop › Developer ›", kCream, kDim);
    textAt(cv, fonts::small(), 233, 248, R ? "Hardware Buddy… › Conectează" : "Open Hardware Buddy… › Connect", kCream, kDim);
    textAt(cv, fonts::small(), 233, 290, claude_.bleName, kAmber);
    rimBottom(cv, R ? "aprobi cu degetul pe sticlă" : "approve with a finger on the glass", kCream, kFaint);
    buildItems(items_);
    drawItems(cv, items_);
    return;
  }
  textAt(cv, fonts::text(), 233, 176, claude_.busy ? (R ? "Claude lucrează" : "Claude is working") : (R ? "Conectat" : "Connected"), claude_.busy ? kAmber : kMint);
  if (!claude_.msg.empty()) {
    std::string lines[2];
    const int n = wrapLines(fonts::small(), claude_.msg, g_.s(320), lines, 2);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 220 + i * 26, lines[i], kCream, kDim);
  }
  char b[64];
  snprintf(b, sizeof b, R ? "%lu aprobate · %lu refuzate" : "%lu approved · %lu denied", (unsigned long)claude_.approvals,
           (unsigned long)claude_.denials);
  textAt(cv, fonts::small(), 233, 300, b, kCream, kFaint);
  buildItems(items_);
  drawItems(cv, items_);
}

void Os::drawSettings(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "SETĂRI" : "SETTINGS", kCream, kDim);
  static const char* const kLabels[2][11] = {
      {"Brightness", "AI", "Wi-Fi", "Language", "My SOUL", "Text size", "About", "Debug overlay", "Screen off at night",
       "Claude & ChatGPT on me", "Start over"},
      {"Luminozitate", "AI", "Wi-Fi", "Limba", "SOUL-ul meu", "Mărimea textului", "Despre", "Depanare", "Ecran stins noaptea",
       "Claude & ChatGPT pe mine", "De la capăt"}};
  buildItems(items_);
  for (const Item& it : items_) {
    if (it.id < IdRow) continue;
    textAt(cv, fonts::small(), 233, it.y - 18, kLabels[R][it.id - IdRow], kCream, kFaint);
  }
  // values a little lower than the item centre
  std::vector<Item> vals = items_;
  for (Item& it : vals) it.y += 10;
  drawItems(cv, vals);
  rimBottom(cv, R ? "glisează în sus: mai multe" : "swipe up: more", kCream, kFaint);
}

void Os::drawAiMode(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, "AI", kCream, kDim);
  buildItems(items_);
  for (Item it : items_) {
    std::vector<Item> one(1, it);
    if (it.id >= IdRow && it.id < IdRow + 4) {
      one[0].y -= 8;
      std::string st;
      switch (it.id - IdRow) {
        case 0:
          st = !net_.relay ? (R ? "adresa se pune din telefon" : "set its address from a phone")
               : net_.cloudUpdate ? (R ? "actualizează SOUL" : "update SOUL")
               : net_.cloudRefused ? (R ? "SOUL nu e acceptat" : "this SOUL was refused")
               : net_.paired ? (net_.owner.empty() ? std::string(R ? "legat de cont" : "paired") : (R ? "legat · " : "paired · ") + net_.owner)
               : (R ? "atinge ca să-l legi" : "tap to pair it");
          break;
        case 1: st = net_.keyClaude ? net_.maskClaude : (R ? "are nevoie de o cheie" : "needs a key"); break;
        case 2: st = net_.keyOpenai ? net_.maskOpenai : (R ? "are nevoie de o cheie" : "needs a key"); break;
        default: st = R ? "ore și minutare pe device" : "times and timers on the device"; break;
      }
      textAt(cv, fonts::small(), 233, it.y + 18, st, kCream, kFaint);
    }
    drawItems(cv, one);
  }
  rimBottom(cv, R ? "ține un rând = scrii cheia" : "hold a row = type the key", kCream, kFaint);
}

void Os::drawWifi(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, "WI-FI", kCream, kDim);
  if (net_.portal) {
    // the phone camera joins SOUL's own Wi-Fi from this QR (iOS 11+, Android 10+)
    textAt(cv, fonts::small(), 233, 124, R ? "Scanează cu camera telefonului" : "Scan with your phone's camera", kCream, kDim);
    if (!net_.apPass.empty()) drawQr(cv, "WIFI:T:WPA;S:" + net_.apName + ";P:" + net_.apPass + ";;", 233, 214, 150);
    textAt(cv, fonts::text(), 233, 306, net_.apName + (net_.apPass.empty() ? std::string() : "  \u00B7  " + net_.apPass), kAmber);
    textAt(cv, fonts::small(), 233, 338, (R ? "apoi deschide " : "then open ") + net_.portalUrl.substr(7), kCream, kDim);
    textAt(cv, fonts::small(), 233, 364, (R ? "S-a închis? Deschide " : "Page closed? Open ") + net_.portalUrl.substr(7), kCream, kFaint);
  } else {
    textAt(cv, fonts::text(), 233, 168, net_.connected ? (R ? "Conectat" : "Connected") : net_.connecting ? (R ? "Mă conectez…" : "Connecting…") : (R ? "Neconectat" : "Not connected"),
           net_.connected ? kMint : kCream);
    if (net_.configured) textAt(cv, fonts::small(), 233, 206, net_.ssid + (net_.connected ? "  ·  " + net_.ip : std::string()), kCream, kDim);
  }
  buildItems(items_);
  drawItems(cv, items_);
}

void Os::drawMySoul(Canvas& cv) {
  const bool R = ro();
  const Design& d = kDesigns[face_.design()];
  rimTop(cv, birth_.chip, kCream, kFaint);
  buildItems(items_);
  drawItems(cv, items_);
  textAt(cv, fonts::text(), 233, 348, d.name, kCream);
  int cnt = 0;
  for (int i = 0; i < kDesignCount; ++i)
    if (kDesigns[i].rarity == d.rarity) ++cnt;
  char b[80];
  snprintf(b, sizeof b, "%s · #%03d / %d · %s %d", kRarityName[(int)d.rarity], d.num, kDesignCount, R ? "1 din" : "1 in",
           (int)lround(cnt / kRarityRate[(int)d.rarity]));
  textAt(cv, fonts::small(), 233, 378, b, Rgb::hex(kRarityColor[(int)d.rarity]));
  if (set_.born) {
    time_t bt = (time_t)set_.born;
    struct tm tm;
    gmtime_r(&bt, &tm);
    static const char* const kMon[2][12] = {{"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"},
                                            {"ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct", "nov", "dec"}};
    char bb[40];
    snprintf(bb, sizeof bb, "%s %d %s %d", R ? "născut" : "born", tm.tm_mday, kMon[R][tm.tm_mon], tm.tm_year + 1900);
    rimBottom(cv, bb, kCream, kFaint);
  }
}

void Os::drawAbout(Canvas& cv) {
  const bool R = ro();
  rimTop(cv, R ? "DESPRE" : "ABOUT", kCream, kDim);
  textAt(cv, fonts::large(), 233, 160, R ? "Sunt un AI." : "I'm an AI.", kCream);
  const char* body = R ? "SOUL e o mașină. Nu are sentimente adevărate și nu e un om. Ce scrii merge doar la AI-ul ales de tine."
                       : "SOUL is a machine. It has no real feelings and it is not a person. What you type goes only to the AI you chose.";
  std::string lines[5];
  const int n = wrapLines(fonts::small(), body, g_.s(320), lines, 5);
  for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 210 + i * 27, lines[i], kCream, kDim);
  rimBottom(cv, "SoulOS 1.0 · " + std::string(viewName(view_)), kCream, kFaint);
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
  rimTop(cv, "SOUL CLOUD", kCream, kDim);
  std::string id = "soul-";  // the device id, as the account page knows it
  for (char c : birth_.chip)
    if (c != ':') id += (char)(c >= 'A' && c <= 'F' ? c - 'A' + 'a' : c);
  if (net_.cloudUpdate) {
    textAt(cv, fonts::large(), 233, 196, R ? "Actualizează SOUL" : "Update SOUL", kAmber);
    std::string l[3];
    const int n = wrapLines(fonts::small(), R ? "SOUL Cloud cere o versiune nouă. Cheia ta și „Fără AI” merg în continuare."
                                              : "SOUL Cloud needs a newer SOUL. Your own key and No AI still work.",
                            g_.s(320), l, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 240 + i * 27, l[i], kCream, kDim);
    return;
  }
  if (!net_.confirmPid.empty() && !net_.paired) {  // §6.3: "Pair with {name} ({hint})?"
    textAt(cv, fonts::text(), 233, 180, R ? "Mă leg de contul lui" : "Pair with", kCream, kDim);
    textAt(cv, fonts::large(), 233, 226, ellipsize(fonts::large(), net_.confirmName + "?", g_.s(330)), kMint);
    textAt(cv, fonts::small(), 233, 272, net_.confirmHint, kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    rimBottom(cv, R ? "doar dacă tu ai scanat codul" : "only if you scanned the code", kCream, kFaint);
    return;
  }
  if (net_.cloudProblem == 2 || net_.cloudProblem == 3) {
    textAt(cv, fonts::text(), 233, 196,
           net_.cloudProblem == 2 ? (R ? "SOUL nu e înregistrat" : "This SOUL is not registered")
                                  : (R ? "SOUL e al altui cont" : "This SOUL belongs to another account"),
           kAmber);
    textAt(cv, fonts::small(), 233, 236, R ? "Scrie-ne cu codul acesta:" : "Write to us with this id:", kCream, kDim);
    textAt(cv, fonts::small(), 233, 264, id, kCream);
    return;
  }
  if (net_.cloudRefused) {
    textAt(cv, fonts::text(), 233, 196, R ? "SOUL Cloud nu mă acceptă" : "SOUL Cloud won't take me", kAmber);
    textAt(cv, fonts::small(), 233, 236, R ? "Scrie-ne cu codul acesta:" : "Write to us with this id:", kCream, kDim);
    textAt(cv, fonts::small(), 233, 264, id, kCream);
    return;
  }
  if (net_.paired && !net_.cloudHost.empty() && pairDoneT_ <= 0) {
    // "Connect Claude": the phone page where the owner pastes the key of their Claude account
    textAt(cv, fonts::text(), 233, 150, R ? "Conectează Claude" : "Connect Claude", kMint);
    textAt(cv, fonts::small(), 233, 186, R ? "Scanează cu telefonul" : "Scan with your phone", kCream, kDim);
    drawQr(cv, "https://" + net_.cloudHost + "/pair/brain?d=" + id, 233, 300, 150);
    rimBottom(cv, net_.owner.empty() ? net_.cloudHost : (R ? "legat de " : "paired with ") + net_.owner, kCream, kFaint);
    return;
  }
  if (net_.paired) {
    textAt(cv, fonts::large(), 233, 192, R ? "Legat de cont" : "Paired", kMint);
    if (!net_.owner.empty()) textAt(cv, fonts::text(), 233, 234, net_.owner, kCream);
    std::string l[3];
    const int n = wrapLines(fonts::small(), R ? "Claude-ul tău poate pune acum notițe, mementouri și alarme pe mine."
                                              : "Your Claude can now put notes, reminders and alarms on me.",
                            g_.s(320), l, 3);
    for (int i = 0; i < n; ++i) textAt(cv, fonts::small(), 233, 280 + i * 27, l[i], kCream, kDim);
    rimBottom(cv, R ? "dezlegi din pagina contului" : "unpair from your account page", kCream, kFaint);
    return;
  }
  if (!net_.configured || !net_.connected) {
    textAt(cv, fonts::text(), 233, 200, R ? "Întâi Wi-Fi-ul" : "Wi-Fi first", kCream);
    textAt(cv, fonts::small(), 233, 240, net_.connecting ? (R ? "mă conectez…" : "connecting…") : (R ? "apoi apare codul aici" : "then the code shows up here"),
           kCream, kDim);
    buildItems(items_);
    drawItems(cv, items_);
    return;
  }
  if (net_.pairCode.size() != 8) {
    const float pulse = 0.55f + 0.35f * sinf(t_ * 3.0f);
    textAt(cv, fonts::text(), 233, 200, net_.cloudOnline ? (R ? "Aștept codul…" : "Getting a code…") : (R ? "Mă conectez la SOUL Cloud…" : "Reaching SOUL Cloud…"),
           kCream, pulse);
    textAt(cv, fonts::small(), 233, 244, id, kCream, kFaint);
    return;
  }
  textAt(cv, fonts::small(), 233, 146, R ? "Codul tău de legare" : "Your pairing code", kCream, kDim);
  textAt(cv, fonts::large(), 233, 200, net_.pairCode.substr(0, 4) + "-" + net_.pairCode.substr(4), kAmber);
  if (net_.trialLeft > 0) {  // a factory unit answers a few questions before it is paired
    char b[64];
    snprintf(b, sizeof b, R ? "%d răspunsuri gratuite până atunci" : "%d free answers until then", net_.trialLeft);
    textAt(cv, fonts::small(), 233, 240, b, kCream, kFaint);
  }
  if (!net_.pairUrl.empty()) drawQr(cv, net_.pairUrl, 233, 330, 136);
  std::string host = net_.pairUrl.size() > 8 ? net_.pairUrl.substr(8) : std::string();
  host = host.substr(0, host.find('/'));
  rimBottom(cv, host.empty() ? (R ? "scanează sau scrie codul în cont" : "scan, or type the code in your account")
                             : (R ? "scanează sau: " : "scan, or: ") + host + "/pair",
            kCream, kFaint);
}

}  // namespace suflet
