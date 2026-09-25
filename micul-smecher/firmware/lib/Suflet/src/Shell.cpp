#include "Shell.h"

#include <math.h>

namespace suflet {

void Shell::go(Screen s) { screen_ = s; }

void Shell::setGeometry(const DisplayGeometry& g) {
  g_ = g;
  fx_ = g.cx();
  fy_ = g.cy();
  kb_.setGeometry(g);
  tp_.setGeometry(g);
}

void Shell::openNote(const std::string& initial) {
  KbConfig c;
  c.action = KbAction::Save;
  c.uiLang = lang;
  c.maxChars = 2000;
  if (lang == Lang::Ro) {
    c.placeholder = "Notiță nouă…";
    c.chips[0] = "Cumpără lapte";
    c.chips[1] = "Idee:";
    c.chips[2] = "Sună-o pe mama";
    c.undoLabel = "↶ Anulează";
  } else {
    c.placeholder = "New note…";
    c.chips[0] = "Buy milk";
    c.chips[1] = "Idea:";
    c.chips[2] = "Call mom";
  }
  kb_.open(c, initial.empty() ? draft_ : initial);
  go(Screen::Note);
}

void Shell::openTimePicker(int hour, int minute) {
  tp_.setLang(lang);
  tp_.setNow(now_);
  tp_.open(hour, minute);
  go(Screen::TimePicker);
}

void Shell::back() {
  if (screen_ == Screen::Note) {
    draft_ = kb_.text();  // the draft is kept
    kb_.cancel();
    KbResult r;
    kb_.poll(r);
    q_.push(Ev::TextCancel);
  } else if (screen_ == Screen::TimePicker) {
    tp_.cancel();
    KbResult r;
    tp_.poll(r);
  }
  go(Screen::Face);
}

bool Shell::event(const TouchEv& e) {
  if (e.e == Ev::TouchDown || e.e == Ev::TouchMove) {
    down_ = true;
    fx_ = e.x;
    fy_ = e.y;
  } else if (e.e == Ev::TouchUp) {
    down_ = false;
  }
  switch (screen_) {
    case Screen::Face:
      if (e.e == Ev::HoldStart && holdOpensNote) {
        openNote();
        return true;
      }
      return false;
    case Screen::Note:
      return kb_.touch(e);
    case Screen::TimePicker:
      return tp_.touch(e);
  }
  return false;
}

void Shell::update(float dt, uint32_t localNow) {
  now_ = localNow;
  if (screen_ == Screen::Note) {
    kb_.update(dt);
    KbResult r;
    if (kb_.poll(r)) {
      if (r == KbResult::Commit) {
        notes_.push_back(kb_.committed());
        if (notes_.size() > 8) notes_.erase(notes_.begin());
        draft_.clear();
        q_.push(Ev::TextCommit);
      } else {
        q_.push(Ev::TextCancel);
      }
      go(Screen::Face);
    }
  } else if (screen_ == Screen::TimePicker) {
    tp_.setNow(localNow);
    tp_.update(dt);
    KbResult r;
    if (tp_.poll(r)) {
      if (r == KbResult::Commit && alarms_) {
        Alarm a;
        a.hour = (uint8_t)tp_.hour();
        a.minute = (uint8_t)tp_.minute();
        a.setLabel(lang == Lang::Ro ? "Alarmă" : "Alarm");
        lastAlarm_ = alarms_->add(a, localNow);
      }
      go(Screen::Face);
    }
  }
}

FaceLayout Shell::faceLayout() const {
  FaceLayout l;
  if (screen_ == Screen::Note) {  // eyes in the header, centre y 36
    l.k = 0.2f;
    l.cy = -0.845f;
  } else if (screen_ == Screen::TimePicker) {  // inside the ring, above the digits
    l.k = 0.16f;
    l.cy = -0.54f;
  }
  return l;
}

void Shell::adjustFace(Face& f) const {
  if (screen_ == Screen::Note) {
    f.gx = down_ ? clampf((fx_ - g_.cx()) / g_.cx() * 0.6f, -1, 1) : 0;
    f.gy = 0.6f;  // looking down at the keys
  } else if (screen_ == Screen::TimePicker) {
    const float a = tp_.knobAngle() * 3.14159265f / 180.0f;
    f.gx = 0.8f * cosf(a);
    f.gy = 0.8f * sinf(a);
  }
}

bool Shell::render(Canvas& cv, const Rect& cleared) {
  bool force = false;
  if (drawn_ != screen_) {  // leaving a screen: wipe what it left behind
    if (!drawnRect_.empty()) {
      cv.fillRect(drawnRect_, pal::kBlack);
      cv.markDirty(drawnRect_);
    }
    drawnRect_ = Rect{};
    drawn_ = screen_;
    force = true;
  }
  switch (screen_) {
    case Screen::Face:
      return force;
    case Screen::Note: {
      const Rect b = kb_.bounds();
      const bool hit = !cleared.empty() && cleared.x0 < b.x1 && b.x0 < cleared.x1 && cleared.y0 < b.y1 &&
                       b.y0 < cleared.y1;
      if (!(force || kb_.changed() || hit)) return false;
      kb_.render(cv);
      drawnRect_ = b;
      return true;
    }
    case Screen::TimePicker:
      if (!(force || tp_.overlaps(cleared))) return false;
      tp_.render(cv);
      drawnRect_ = Rect{0, 0, cv.width(), cv.height()};
      return true;
  }
  return false;
}

}  // namespace suflet
