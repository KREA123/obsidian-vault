// SoulOS on the device: SOUL Memory (docs/10-SOUL-MEMORY.md). Everything memory does inside the OS lives
// here, apart from the screens and flows in Os.cpp / OsDraw.cpp, which only call these hooks:
//
//   ask()        "remember that…" / "forget…" / "când e ziua Anei?" -> memoryAsk() (on the device, any brain)
//   sendJob()    every AI job carries memoryBlock(): "What SOUL knows about you" (~300 tokens)
//   aiResult()   the AI's memory.remember / memory.forget -> memoryApply() + "Remembered: … · tap to undo"
//   Settings     › Memory: the facts on glass slabs (newest first), search on the round keyboard, a fact
//                opens, hold = forget it; "Forget everything" needs a hold; Backup (off by default) sends an
//                export to the owner's SOUL Cloud account, where /me shows it, exports it and deletes it
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "Os.h"

namespace suflet {

using namespace eyes;

namespace {
const Rgb kCream = Rgb::hex(0xFFF0C8), kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4);
constexpr float kDim = 0.62f, kFaint = 0.42f;
constexpr int kKbMemSearch = 40;  // a keyboard context of its own (Os.cpp's KbCtx stop below 20)
enum : int { IdMemSearch = 60, IdMemBackup, IdMemWipe, IdMemForget, IdMemRow = 100 };
constexpr int kPerPage = 3;
constexpr float kBackupEveryS = 30.0f;  // the cloud backup follows changes, at most this often

std::string cutTo(const Font& f, const std::string& s, float maxW) {
  if (Canvas::measureText(f, s.c_str()) <= maxW) return s;
  std::string out;
  const char* p = s.c_str();
  const char* end = p + s.size();
  while (p < end) {
    const char* q = p;
    utf8::next(q, end);
    const std::string t = out + std::string(p, q - p) + "\xE2\x80\xA6";
    if (Canvas::measureText(f, t.c_str()) > maxW) break;
    out.append(p, q - p);
    p = q;
  }
  return out + "\xE2\x80\xA6";
}

const char* kindLabel(FactKind k, bool ro) {
  static const char* const en[] = {"person", "preference", "plan", "place", "note", "summary", "other"};
  static const char* const r[] = {"persoană", "preferință", "plan", "loc", "notiță", "rezumat", "altceva"};
  return (unsigned)k < (unsigned)FactKind::Count ? (ro ? r[(int)k] : en[(int)k]) : "";
}

const char* srcLabel(FactSrc s, bool ro) {
  switch (s) {
    case FactSrc::User: return ro ? "de la tine" : "from you";
    case FactSrc::Ai: return ro ? "propus de AI" : "from the AI";
    case FactSrc::Rule: return ro ? "auzit de mine" : "picked up by me";
    case FactSrc::Cloud: return "SOUL Cloud";
    default: return ro ? "importat" : "imported";
  }
}
}  // namespace

// ---------------------------------------------------------------- the hooks ---

bool Os::memoryAsk(const std::string& text) {
  if (!mem_) return offlineChat(text);
  // offline (or no AI): the rules also keep simple facts said in passing and answer more from memory
  const bool offline = aiMode() == AiMode::None || !net_.connected || (aiMode() == AiMode::Bridge && !net_.bridgeOnline);
  MemoryAnswer a;
  if (!memoryAct(*mem_, text, now_, ro(), offline, a)) return offlineChat(text);  // or a personality line (OsVoice.cpp)
  AiReply r;
  r.say = a.say;
  showAnswer(r, AiErr::None, ro() ? "Memoria SOUL · pe device" : "SOUL Memory · on the device");
  if (a.remembered) {
    memUndoId_ = a.remembered;
    face_.react(X_approve);
    toast(tr("Remembered \xC2\xB7 tap here to undo", "Ținut minte \xC2\xB7 atinge aici: anulează"), kMint, 5.0f);
  } else if (a.forgotten) {
    face_.react(X_wink, 1.0f);
  }
  return true;
}

std::string Os::memoryBlock(const std::string& q) { return mem_ ? mem_->contextBlock(q, now_, ro()) : std::string(); }

void Os::memoryApply(const std::vector<MemOp>& ops, FactSrc src) {
  if (!mem_ || ops.empty()) return;
  std::string kept;
  int id = 0, forgot = 0;
  for (const MemOp& op : ops) {
    const int r = mem_->apply(op, src, now_, &forgot);
    if (r) {
      id = r;
      if (const Fact* f = mem_->find(r)) kept = f->text;
    }
  }
  if (id) {
    memUndoId_ = id;
    chips_.push_back(tr("Remembered", "Ținut minte"));
    toast(tr("Remembered: ", "Ținut minte: ") + kept + tr(" \xC2\xB7 tap to undo", " \xC2\xB7 atinge: anulează"), kMint, 6.0f);
  } else if (forgot) {
    chips_.push_back(tr("Forgotten", "Uitat"));
    toast(tr("Forgotten", "Uitat"), kAmber, 2.4f);
  }
  invalidate();
}

bool Os::memoryToastTap() {
  if (!mem_ || !memUndoId_) return false;
  bool ok;
  if (mem_->lastRemembered() == memUndoId_) ok = mem_->undoLast();
  else ok = mem_->forgetId(memUndoId_);
  memUndoId_ = 0;
  if (ok) {
    toast(tr("Undone: not kept", "Anulat: nu l-am păstrat"), kAmber, 2.0f);
    face_.react(X_wink, 1.0f);
  } else {
    toastLeft_ = 0;
  }
  invalidate();
  return true;
}

void Os::memoryBackupTick() {
  if (!mem_) return;
  const bool on = mem_->backup && net_.paired;
  if (!mem_->backup && memBackupWas_) {  // switched off on SOUL: the cloud deletes its copy
    memBackupWas_ = false;
    if (net_.paired) {
      CloudOut o;
      o.kind = CloudOut::MemoryBackup;
      o.paused = true;
      outs_.push_back(o);
    }
    return;
  }
  if (!on) return;
  memBackupWas_ = true;
  if (mem_->generation() == memBackupGen_ || t_ - memBackupT_ < kBackupEveryS) return;
  memBackupGen_ = mem_->generation();
  memBackupT_ = t_;
  CloudOut o;
  o.kind = CloudOut::MemoryBackup;
  o.text = mem_->exportJson();
  o.created = memBackupGen_;
  for (size_t i = 0; i < outs_.size(); ++i)  // only the newest copy waits
    if (outs_[i].kind == CloudOut::MemoryBackup) outs_.erase(outs_.begin() + (long)i--);
  outs_.push_back(o);
}

// ------------------------------------------------------------- the screen ---

void Os::memoryOpen() {
  memSel_ = -1;
  memFilter_.clear();
  page_ = 0;
  go(View::Memory);
}

bool Os::memoryBack() {
  if (memSel_ >= 0) {
    memSel_ = -1;
    invalidate();
    return true;
  }
  if (!memFilter_.empty()) {
    memFilter_.clear();
    page_ = 0;
    invalidate();
    return true;
  }
  return false;
}

bool Os::memoryKbCommit(int ctx, const std::string& text) {
  if (ctx != kKbMemSearch) return false;
  memFilter_ = text;
  memSel_ = -1;
  page_ = 0;
  view_ = View::Memory;
  invalidate();
  return true;
}

void Os::buildMemoryItems(std::vector<Item>& out) const {
  if (!mem_) return;
  const bool R = ro();
  auto add = [&](int id, float x, float y, float w, float h, const std::string& label, Rgb c, int font, bool pill,
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
    it.underline = pill;
    it.alpha = alpha;
    out.push_back(it);
  };
  if (memSel_ >= 0) {
    if (mem_->find(memSel_)) add(IdMemForget, 233, 396, 160, 54, R ? "Uită" : "Forget", kAmber, 1, true);
    return;
  }
  const std::vector<int> rows = mem_->list(memFilter_);
  const int n = (int)rows.size();
  const int pages = n > kPerPage ? (n + kPerPage - 1) / kPerPage : 1;
  const int p = page_ % pages;
  const Font& f = set_.largeText ? fonts::text() : fonts::small();
  for (int i = p * kPerPage; i < n && i < p * kPerPage + kPerPage; ++i)
    add(IdMemRow + i, 233, 160 + (i - p * kPerPage) * 58, 330, 54,
        cutTo(f, mem_->at((size_t)rows[(size_t)i]).text, g_.s(296)), kCream, 0, false);
  add(IdMemSearch, 160, 344, 130, 48, memFilter_.empty() ? (R ? "Caută" : "Search") : (R ? "Toate" : "All"), kCream, 0, true);
  add(IdMemBackup, 306, 344, 150, 48,
      std::string(R ? "Backup: " : "Backup: ") + (mem_->backup ? (R ? "da" : "on") : (R ? "nu" : "off")),
      mem_->backup ? kMint : kCream, 0, true, mem_->backup ? 1.0f : kDim);
  if (mem_->size()) add(IdMemWipe, 233, 398, 230, 40, R ? "Uită tot (ține)" : "Forget all (hold)", kAmber, 0, true, kDim);
}

void Os::memoryActivate(int id) {
  if (!mem_) return;
  if (id == IdMemSearch) {
    if (!memFilter_.empty()) {
      memFilter_.clear();
      page_ = 0;
      invalidate();
      return;
    }
    openKeyboard(kKbMemSearch, memFilter_);
    return;
  }
  if (id == IdMemBackup) {
    if (!mem_->backup && !net_.paired) {
      toast(tr("Pair with your account first", "Leagă-mă întâi de cont"), kAmber);
      return;
    }
    mem_->setBackup(!mem_->backup);  // saved with the memory
    memBackupGen_ = 0;  // a fresh copy goes up at once
    memBackupT_ = -kBackupEveryS;
    toast(mem_->backup ? tr("Backup on: encrypted, in your account", "Backup pornit: criptat, în contul tău")
                       : tr("Backup off: the cloud copy is deleted", "Backup oprit: copia din cloud se șterge"),
          mem_->backup ? kMint : kAmber, 3.0f);
    invalidate();
    return;
  }
  if (id == IdMemWipe) {
    toast(tr("Hold to forget everything", "Ține apăsat ca să uit tot"), kAmber);
    return;
  }
  if (id >= IdMemRow) {
    const std::vector<int> rows = mem_->list(memFilter_);
    const int k = id - IdMemRow;
    if (k >= 0 && k < (int)rows.size()) memSel_ = mem_->at((size_t)rows[(size_t)k]).id;
    invalidate();
  }
}

void Os::memoryHoldDone(int id) {
  if (!mem_) return;
  if (id == IdMemWipe) {
    mem_->clear();
    memUndoId_ = 0;
    memSel_ = -1;
    memFilter_.clear();
    toast(tr("Memory wiped", "Memorie ștearsă"), kAmber);
    face_.react(X_sad, 1.0f);
  } else if (id == IdMemForget && memSel_ >= 0) {
    mem_->forgetId(memSel_);
    memSel_ = -1;
    toast(tr("Forgotten", "Uitat"), kAmber);
  } else if (id >= IdMemRow) {  // hold a row: forget it
    const std::vector<int> rows = mem_->list(memFilter_);
    const int k = id - IdMemRow;
    if (k >= 0 && k < (int)rows.size()) {
      mem_->forgetId(mem_->at((size_t)rows[(size_t)k]).id);
      toast(tr("Forgotten", "Uitat"), kAmber);
    }
  }
  invalidate();
}

void Os::drawMemory(Canvas& cv) {
  const bool R = ro();
  const size_t n = mem_ ? mem_->size() : 0;
  rimTop(cv, (R ? "MEMORIE \xC2\xB7 " : "MEMORY \xC2\xB7 ") + std::to_string(n), kCream, kDim);
  if (!mem_) return;
  buildMemoryItems(items_);
  if (memSel_ >= 0) {
    const Fact* f = mem_->find(memSel_);
    if (!f) return;
    std::string lines[5];
    const int k = wrapLines(fonts::text(), f->text, g_.s(300), lines, 5);
    const float y0 = 132, y1 = 160 + k * 34 + 64;
    glassPanel(cv, 66, y0, 400, y1, 30, gs());
    for (int i = 0; i < k; ++i) textAt(cv, fonts::text(), 233, 162 + i * 34, lines[i], kCream);
    std::string meta = std::string(kindLabel(f->kind, R)) + " \xC2\xB7 " + srcLabel(f->src, R);
    if (f->created) {
      const time_t t = (time_t)f->created;
      struct tm tm;
      gmtime_r(&t, &tm);
      char b[48];
      snprintf(b, sizeof b, " \xC2\xB7 %d.%02d.%d", tm.tm_mday, tm.tm_mon + 1, tm.tm_year + 1900);
      meta += b;
    }
    textAt(cv, fonts::small(), 233, 162 + k * 34 + 8, meta, kCream, kFaint);
    if (f->mmdd) textAt(cv, fonts::small(), 233, 162 + k * 34 + 36, dayMonthText(f->mmdd, R), kMint, kDim);
    drawItems(cv, items_);
    rimBottom(cv, R ? "ține Uită ca să uit" : "hold Forget to forget", kCream, kFaint);
    return;
  }
  const std::vector<int> rows = mem_->list(memFilter_);
  if (rows.empty()) {
    textAt(cv, fonts::small(), 233, 196, memFilter_.empty() ? (R ? "Încă nu țin minte nimic." : "I remember nothing yet.")
                                                            : (R ? "Nimic cu „" : "Nothing with “") + memFilter_ + (R ? "”" : "”"),
           kCream, kDim);
    if (memFilter_.empty())
      textAt(cv, fonts::small(), 233, 232, R ? "Spune „ține minte că…”" : "Say “remember that…”", kCream, kFaint);
  }
  for (const Item& it : items_)
    if (it.id >= IdMemRow) glassPanel(cv, 68, it.y - 26, 398, it.y + 26, 22, holdItem_ == it.id ? gs().pressed() : gs());
  drawItems(cv, items_);
  if (!memFilter_.empty())
    rimBottom(cv, (R ? "căutare: " : "search: ") + memFilter_, kCream, kFaint);
  else if (rows.size() > (size_t)kPerPage)
    rimBottom(cv, R ? "glisează în sus: mai multe \xC2\xB7 ține = uită" : "swipe up: more \xC2\xB7 hold = forget", kCream, kFaint);
  else
    rimBottom(cv, R ? "export: contul tău SOUL › /me" : "export: your SOUL account › /me", kCream, kFaint);
}

}  // namespace suflet
