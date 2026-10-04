// SoulOS on the device: state, navigation, gestures, AI, persistence.
// Drawing lives in OsDraw.cpp.
#include "Os.h"

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

namespace suflet {

using namespace eyes;

static const Rgb kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4), kRose = Rgb::hex(0xFF8FAB);

enum KbCtx : int { KbTalk = 1, KbNote, KbNoteEdit, KbName, KbKey, KbAlarmLabel, KbInbox, KbWifiName, KbWifiPass };

// item ids: 1.. per screen; rows use 100 + index
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
  IdHotspot,      // Wi-Fi: "Add my phone's hotspot" (the how-to page)
  IdHotspotType,  // ... "Type its name on SOUL"
  IdRow = 100,
};

static constexpr float kFadeS = 0.18f;  // screens fade in, well inside the 250 ms budget

// the orbit's apps: AppsState::order minus the hidden ones (OsApps.cpp)
View Os::appView(int i) const { return viewOf(appAt(i)); }

const char* viewName(View v) {
  static const char* const k[] = {"boot",  "home",   "launcher", "today",    "talk",   "answer", "alarms",
                                  "dial",  "ringing", "timer",   "notes",    "note",   "claude", "settings",
                                  "aimode", "wifi",  "mysoul",   "about",    "pair",   "keyboard", "bridge",
                                  "memory", "control", "weather", "maps", "calendar", "music", "games", "focus",
                                  "breathe", "habits", "stopwatch", "worldclock", "convert", "findphone", "device",
                                  "appssettings"};
  static_assert(sizeof(k) / sizeof(k[0]) == (unsigned)View::Count, "view names");
  return (unsigned)v < (unsigned)View::Count ? k[(int)v] : "?";
}

void Os::begin(const DisplayGeometry& g, const BirthInfo& b) {
  g_ = g;
  birth_ = b;
  kb_.setGeometry(g);
  tp_.setGeometry(g);
  glass().begin(g.w, g.h, !deferGlass_);  // the aura + frosted buffers (PSRAM); without them the glass falls back to black
  glass().setOn(false);
  glass().setLevel(0);
  face_.begin(g.w, g.h);
  face_.setSeed(b.seed);
  face_.setDesign(b.design, true);
  if (!set_.booted) {
    view_ = View::Boot;
    bootStep_ = BootStep::Birth;
    face_.hide();
    face_.react(kDesigns[b.design].rarity >= eyes::Rarity::Epic ? X_excited : X_hello, 2.0f);
  } else {
    view_ = View::Home;
    face_.react(X_wake);
  }
  appsBegin();
  face_.snapLayout(layoutFor(view_));
  invalidate();
}

// ------------------------------------------------------------- layout ---

FaceLayoutT Os::layoutFor(View v) const {
  FaceLayoutT l;
  if (appsLayout(v, l)) return l;
  switch (v) {
    case View::Boot:
      if (bootStep_ == BootStep::Name || bootStep_ == BootStep::Brain) l = {0.3f, 0, -0.33f};
      else l = {0.62f, 0, -0.08f};
      break;
    case View::Home: l = {1, 0, 0}; break;
    case View::Launcher: l = {0.46f, 0, -0.21f}; break;
    case View::Today: l = {0.25f, 0, -0.35f}; break;
    case View::Talk: l = {0.62f, 0, -0.11f}; break;
    case View::Answer: l = {0.42f, 0, -0.26f}; break;
    case View::Ringing: l = {0.44f, 0, -0.2f}; break;
    case View::Dial: l = {0.19f, 0, -0.268f}; break;
    case View::Keyboard: l = {0.2f, 0, -0.414f}; break;
    case View::MySoul: l = {0.5f, 0, -0.12f}; break;
    case View::Timer: l = {0.28f, 0, -0.34f}; break;
    case View::Pair: l = {0.22f, 0, -0.3f}; break;
    case View::Bridge: l = {0.22f, 0, -0.3f}; break;
    case View::Wifi: l = net_.portal ? FaceLayoutT{0.15f, 0, -0.36f} : FaceLayoutT{0.3f, 0, -0.33f}; break;
    default: l = {0.3f, 0, -0.33f}; break;
  }
  return l;
}

// ----------------------------------------------------------- navigation ---

void Os::go(View v) {
  if (v == view_) return;
  if (view_ == View::Keyboard && v != View::Keyboard) kb_.close();
  if (view_ == View::Dial && v != View::Dial) tp_.close();
  view_ = v;
  viewT_ = 0;
  fade_ = 0;
  page_ = 0;
  holdItem_ = -1;
  invalidate();
  appOpened(v);  // an app asks SOUL Cloud for what it shows (weather, the agenda, where SOUL is...)
}

void Os::home() {
  if (view_ == View::Boot) return;
  if (view_ == View::Ringing) return;  // a ringing alarm needs Stop / Snooze
  go(View::Home);
}

void Os::back() {
  if (view_ != View::Keyboard && view_ != View::Dial && appsBack()) return;
  switch (view_) {
    case View::Boot:
      bootPrev();
      return;
    case View::Keyboard: {
      // the draft is kept (the keyboard remembers it until the next open)
      kb_.cancel();
      KbResult r;
      kb_.poll(r);
      go(kbReturn_);
      return;
    }
    case View::Dial:
      tp_.cancel();
      go(View::Alarms);
      return;
    case View::NoteView: go(View::Notes); return;
    case View::Wifi:
      if (page_ == 1) {
        page_ = 0;
        invalidate();
        return;
      }
      go(View::Settings);
      return;
    case View::AiMode:
    case View::MySoul:
    case View::About: go(View::Settings); return;
    case View::Bridge: go(View::AiMode); return;
    case View::Memory:  // SOUL Memory: a fact -> the list -> Settings
      if (!memoryBack()) go(View::Settings);
      return;
    case View::Pair:
      pairDoneT_ = -1;
      go(pairReturn_ == View::Pair ? View::Settings : pairReturn_);
      return;
    case View::Answer:
      if (acceptMode_) {  // closed without Accept: the item is not armed (§6.7 rule 3)
        answerAccept(false);
        return;
      }
      cardHidden_ = false;
      go(answerReturn_ == View::Answer ? View::Home : answerReturn_);
      return;
    case View::Ringing: return;
    case View::Home: return;
    default: go(View::Home); return;
  }
}

void Os::restartBoot() {
  set_.booted = 0;
  bootStep_ = BootStep::Birth;
  go(View::Boot);
  face_.hide();
  face_.react(X_hello);
  pushCmd(OsCmd::SaveSettings);
}

void Os::bootNext() {
  switch (bootStep_) {
    case BootStep::Birth: bootStep_ = BootStep::Name; break;
    case BootStep::Name: bootStep_ = BootStep::Brain; break;
    case BootStep::Brain: bootStep_ = BootStep::Hold; break;
    case BootStep::Hold:
    case BootStep::Done:
      bootStep_ = BootStep::Done;
      set_.booted = 1;
      if (!set_.born && now_) set_.born = now_;
      pushCmd(OsCmd::SaveSettings);
      if (net_.portal) pushCmd(OsCmd::StopPortal);
      view_ = View::Boot;  // force the change below
      go(View::Home);
      face_.react(X_happy, 1.6f);
      toast(tr("Hi! I'm ", "Bună! Sunt ") + set_.name, kMint);
      return;
  }
  viewT_ = 0;
  fade_ = 0;
  invalidate();
}

void Os::bootPrev() {
  if (bootStep_ == BootStep::Birth) return;
  bootStep_ = (BootStep)((int)bootStep_ - 1);
  viewT_ = 0;
  fade_ = 0;
  invalidate();
}

void Os::toast(const std::string& text, Rgb color, float seconds) {
  // Quiet (Control): what arrives while you are not using SOUL waits; amber (needs you) still shows
  if (apps_.dnd && view_ == View::Home && !(color == Rgb::hex(0xFFB347)) && peekT_ <= 0) return;
  toast_ = text;
  toastColor_ = color;
  toastLeft_ = seconds;
  invalidate();
}

void Os::pushCmd(OsCmd c) {
  for (int i = 0; i < cmdCount_; ++i)  // saving twice in one frame is one save
    if (cmds_[(cmdHead_ + i) % 16] == c && c != OsCmd::SetKey) return;
  if (cmdCount_ == 16) return;
  cmds_[(cmdHead_ + cmdCount_) % 16] = c;
  ++cmdCount_;
}

bool Os::popCmd(OsCmd& c) {
  if (!cmdCount_) return false;
  c = cmds_[cmdHead_];
  cmdHead_ = (cmdHead_ + 1) % 16;
  --cmdCount_;
  return true;
}

bool Os::popCloudOut(CloudOut& o) {
  if (outs_.empty()) return false;
  o = outs_.front();
  outs_.erase(outs_.begin());
  return true;
}

bool Os::popAiJob(AiJob& j) {
  if (jobs_.empty()) return false;
  j = jobs_.front();
  jobs_.erase(jobs_.begin());
  return true;
}

void Os::clearPendingWifi() {
  for (char& c : pendingWifi_.pass) c = 0;
  pendingWifi_ = WifiNet();
}

void Os::clearPendingKey() {
  // overwrite before freeing: the key should not linger in RAM
  for (char& c : pendingKey_) c = 0;
  pendingKey_.clear();
}

// ---------------------------------------------------------------- inputs ---

void Os::setNet(const NetInfo& n) {
  const bool was = net_.connected, wasPaired = net_.paired;
  const std::string oldConfirm = net_.confirmPid;
  const bool changed = n.connected != net_.connected || n.portal != net_.portal || n.ssid != net_.ssid ||
                       n.connecting != net_.connecting || n.keyClaude != net_.keyClaude ||
                       n.keyOpenai != net_.keyOpenai || n.relay != net_.relay || n.cloudOnline != net_.cloudOnline ||
                       n.paired != net_.paired || n.pairCode != net_.pairCode || n.pairUrl != net_.pairUrl ||
                       n.owner != net_.owner || n.cloudUpdate != net_.cloudUpdate || n.cloudRefused != net_.cloudRefused ||
                       n.apPass != net_.apPass || n.confirmPid != net_.confirmPid ||
                       n.connectorsPaused != net_.connectorsPaused || n.cloudProblem != net_.cloudProblem ||
                       n.trialLeft != net_.trialLeft || n.cloudHost != net_.cloudHost ||
                       n.bridgeOnline != net_.bridgeOnline || n.bridgePaired != net_.bridgePaired ||
                       n.bridgeName != net_.bridgeName || n.bridgeCode != net_.bridgeCode ||
                       n.bridgeCmd != net_.bridgeCmd || n.bridgeLan != net_.bridgeLan || n.askState != net_.askState ||
                       n.captive != net_.captive || n.noInternet != net_.noInternet || n.searching != net_.searching ||
                       n.saved != net_.saved || n.savedList != net_.savedList || n.wifiFail != net_.wifiFail ||
                       n.linkUp != net_.linkUp || n.hotspot != net_.hotspot;
  const bool wasCaptive = net_.captive, wasNoNet = net_.noInternet;
  const bool bridgeWas = net_.bridgeOnline;
  net_ = n;
  if (changed) invalidate();
  if (!n.confirmPid.empty() && n.confirmPid != oldConfirm) {  // "Pair with Ana?": only a touch answers it
    if (view_ == View::Keyboard) kb_.cancel();
    if (view_ != View::Pair) pairReturn_ = (view_ == View::Boot || view_ == View::Answer) ? View::Home : view_;
    if (view_ != View::Boot) go(View::Pair);
    face_.react(X_surprised, 1.2f);
    brainEvents_.push_back(Ev::AlarmDue);  // wakes the face
  }
  if (netKnown_ && !was && n.connected && set_.booted)
    toast(askQ_.size() ? tr("Online again", "Din nou online") : n.hotspot ? tr("On your phone's hotspot", "Pe hotspotul telefonului")
                                                                          : tr("Wi-Fi connected", "Wi-Fi conectat"),
          kMint, 2.0f);
  if (netKnown_ && set_.booted && n.captive && !wasCaptive)  // a hotel / train Wi-Fi with a login page
    toast(tr("Wi-Fi needs a login: use the hotspot", "Wi-Fi cu login: folosește hotspotul"), kAmber, 5.0f);
  if (netKnown_ && set_.booted && n.noInternet && !wasNoNet)
    toast(n.hotspot ? tr("Your phone has no mobile data", "Telefonul n-are date mobile")
                    : tr("Wi-Fi joined, but no internet", "Wi-Fi conectat, dar fără internet"),
          kAmber, 4.0f);
  if (netKnown_ && !wasPaired && n.paired) {  // the account claimed this SOUL: greet the owner
    face_.react(X_love, 1.6f);
    reactAfter_ = X_happy;
    reactAfterT_ = 1.6f;
    toast(n.owner.empty() ? tr("Paired!", "Legat de cont!") : tr("Hi, ", "Bună, ") + n.owner + "!", kMint, 3.0f);
    if (view_ == View::Pair) pairDoneT_ = 2.6f;
  }
  if (netKnown_ && !bridgeWas && n.bridgeOnline && aiMode() == AiMode::Bridge) {  // the computer is here
    face_.react(X_happy, 1.4f);
    toast(tr("Your computer is connected", "Calculatorul tău e conectat"), kMint, 3.0f);
  }
  netKnown_ = true;
}

void Os::setClaude(const ClaudeInfo& c) {
  const bool changed = c.linked != claude_.linked || c.busy != claude_.busy || c.prompt != claude_.prompt ||
                       c.passkey != claude_.passkey || c.tool != claude_.tool || c.hint != claude_.hint ||
                       c.msg != claude_.msg;
  // Claude needs you: a glass capsule on the rim for a few seconds (an event), then the eyes alone say it
  if (c.prompt && !claude_.prompt) {
    claude_ = c;
    toast(tr("Claude needs you · hold = yes", "Claude te așteaptă · ține = da"), Rgb::hex(0xFFB347), 5.0f);
  }
  claude_ = c;
  if (changed) invalidate();
}

void Os::button(bool down) {
  if (down && !buttonDown_) {
    buttonDown_ = true;
    buttonT_ = 0;
    if (ringing()) silence_ = true;
    return;
  }
  if (!down && buttonDown_) {
    buttonDown_ = false;
    if (view_ == View::Ringing) {  // the side button stops a ringing alarm
      if (ringingAlarm_ >= 0 && alarms_) alarms_->dismiss(ringingAlarm_);
      ringingAlarm_ = -1;
      timerRinging_ = false;
      pushCmd(OsCmd::SaveAlarms);
      go(View::Home);
      return;
    }
    if (view_ == View::Boot) {  // during first boot the button skips a step
      bootNext();
      return;
    }
    if (buttonT_ > 1.5f) home();
    else back();
  }
}

void Os::motion(Ev e) {
  switch (e) {
    case Ev::PickUp:  // wake + the eyes look at you
      lookUntil_ = t_ + 1.5f;
      lookX_ = 0;
      lookY_ = -0.15f;
      if (net_.saved > 0 && !net_.connected) pushCmd(OsCmd::WifiKick);  // the phone's hotspot may be on now
      break;
    case Ev::Shake:  // dismisses an answer or a toast (dizzy is the Brain's)
      if (view_ == View::Answer && !thinking_) back();
      toastLeft_ = 0;
      break;
    case Ev::FaceDown:  // face down on a ringing alarm = snooze
      if (view_ == View::Ringing && ringingAlarm_ >= 0 && alarms_) {
        alarms_->snooze(ringingAlarm_, now_);
        ringingAlarm_ = -1;
        pushCmd(OsCmd::SaveAlarms);
        silence_ = true;
        go(View::Home);
      }
      break;
    default: break;
  }
  brainEvents_.push_back(e);
}

void Os::touch(const TouchEv& e) {
  idleT_ = 0;
  if (e.e == Ev::TouchDown && view_ == View::Home) {  // standby: a touch shows the clock for a moment
    if (peekT_ <= 0) invalidate();
    peekT_ = kPeekS;
  }
  // the keyboard and the dial take the raw stream
  if (view_ == View::Keyboard) {
    kb_.touch(e);
    // pulling the text field down closes it (the web: drag the field down)
    if (e.e == Ev::TouchDown) {
      dx0_ = e.x;
      dy0_ = e.y;
      downT_ = t_;
      down_ = true;
    } else if (e.e == Ev::TouchUp) {
      down_ = false;
      if (dy0_ < g_.s(130) && e.y - dy0_ > g_.s(90) && fabsf(e.x - dx0_) < g_.s(60) && t_ - downT_ < 0.6f) back();
    }
    setDirtyFromKeyboard();
    return;
  }
  if (appsTouch(e)) return;  // maps (pan, rim zoom), control (rim dials)
  if (view_ == View::Dial) {
    if (e.e == Ev::TouchDown) {
      dx0_ = e.x;
      dy0_ = e.y;
      downT_ = t_;
    }
    tp_.touch(e);
    if (tp_.changed()) invalidate();
    return;
  }
  const float x = e.x, y = e.y;
  switch (e.e) {
    case Ev::TouchDown:
      down_ = true;
      holding_ = stroking_ = false;
      dx0_ = dx_ = x;
      dy0_ = dy_ = y;
      downT_ = t_;
      lookUntil_ = t_ + 2.2f;  // every touch: the eyes glance at the finger
      lookX_ = (x / g_.w - 0.5f) * 2.4f;
      lookY_ = (y / g_.h - 0.5f) * 2.4f;
      break;
    case Ev::TouchMove: {
      if (!down_) break;
      dx_ = x;
      dy_ = y;
      lookUntil_ = t_ + 2.2f;
      lookX_ = (x / g_.w - 0.5f) * 2.4f;
      lookY_ = (y / g_.h - 0.5f) * 2.4f;
      const float dist = hypotf(x - dx0_, y - dy0_);
      if (view_ == View::Launcher) {
        orbitDrag_ = (x - dx0_) / g_.s(140);
        invalidate();
      }
      // a slow, long touch that moves = petting (the Brain purrs), on the face only
      if (view_ == View::Home && !holding_ && !stroking_ && dist > g_.s(45) && t_ - downT_ > 0.45f) {
        stroking_ = true;
        brainEvents_.push_back(Ev::StrokeStart);
      }
      break;
    }
    case Ev::HoldStart:
      if (!down_ || stroking_) break;
      holding_ = true;
      onHoldStart(x, y);
      break;
    case Ev::TouchUp: {
      if (!down_) break;
      down_ = false;
      const float dur = t_ - downT_;
      const float ddx = x - dx0_, ddy = y - dy0_, dist = hypotf(ddx, ddy);
      if (view_ == View::Launcher && fabsf(orbitDrag_) > 0.001f) {
        orbitDrag_ = 0;
        invalidate();
      }
      if (holding_) {
        holding_ = false;
        onHoldEnd();
        break;
      }
      if (stroking_) {
        stroking_ = false;
        brainEvents_.push_back(Ev::StrokeEnd);
        break;
      }
      if (dist > g_.s(55) && dur < 0.7f) {
        if (fabsf(ddx) > fabsf(ddy)) onSwipe(ddx < 0 ? 0 : 1);
        else onSwipe(ddy < 0 ? 2 : 3);
        break;
      }
      if (dist < g_.s(24) && dur < 0.45f) {
        if (t_ - lastTapT_ < 0.38f && hypotf(x - lastTapX_, y - lastTapY_) < g_.s(50)) {
          lastTapT_ = -10;
          onDoubleTap(x, y);
        } else {
          lastTapT_ = t_;
          lastTapX_ = x;
          lastTapY_ = y;
          onTap(x, y);
        }
      }
      break;
    }
    default: break;
  }
}

void Os::setDirtyFromKeyboard() {
  RectList d;  // only what looks different (a key, the field, the bar): 1.7 repainted all 35 glass caps
  kb_.takeDamage(d);
  for (int i = 0; i < d.n; ++i) invalidate(d.r[i]);
}

static bool claudeHoldView(View v) {
  return v == View::Home || v == View::Today || v == View::Claude || v == View::Launcher || v == View::Talk;
}

void Os::onHoldStart(float x, float y) {
  if (claude_.prompt && claudeHoldView(view_)) {  // hold the glass = approve (1.2 s, mint arc)
    brainHold_ = true;
    brainEvents_.push_back(Ev::HoldStart);
    return;
  }
  if (appsHold(x, y)) return;
  switch (view_) {
    case View::Boot:
      if (bootStep_ == BootStep::Hold) {
        listening_ = true;
        invalidate();
      }
      return;
    case View::Home:
    case View::Talk:
      if (aiMode() == AiMode::None && view_ == View::Home) {  // no AI: holding the stone = purr
        brainHold_ = true;
        brainEvents_.push_back(Ev::HoldStart);
        return;
      }
      listening_ = true;  // hold = talk (voice when a mic is fitted, else the keyboard after)
      if (voice_) {
        voiceFrom_ = view_;
        pushCmd(OsCmd::VoiceStart);
      }
      invalidate();
      return;
    case View::Notes:  // on Notes, hold = dictate a note (kept on the device, no AI round trip)
      if (voice_) {
        listening_ = true;
        voiceFrom_ = view_;
        pushCmd(OsCmd::VoiceStart);
        invalidate();
        return;
      }
      {
        const int id = hitItem(x, y);
        if (id >= 0) {
          holdItem_ = id;
          holdItemT_ = 0;
          invalidate();
        }
      }
      return;
    case View::Alarms:
    case View::NoteView:
    case View::Wifi:
    case View::AiMode:
    case View::Memory:
    case View::Settings: {
      const int id = hitItem(x, y);
      if (id >= 0) {
        holdItem_ = id;
        holdItemT_ = 0;
        invalidate();
      }
      return;
    }
    default: return;
  }
}

void Os::onHoldEnd() {
  if (brainHold_) {
    brainHold_ = false;
    brainEvents_.push_back(Ev::HoldEnd);
    return;
  }
  if (listening_) {
    listening_ = false;
    invalidate();
    if (view_ == View::Boot && bootStep_ == BootStep::Hold) {
      face_.react(X_approve);
      bootNext();
      return;
    }
    // No microphone on this build: after "hold the glass", the round keyboard
    // takes the question (voice uses the same path when SUFLET_VOICE is on).
    if (voice_) {
      pushCmd(OsCmd::VoiceStop);
      voiceWait_ = true;
      thinking_ = false;
      return;
    }
    openKeyboard(KbTalk);
    return;
  }
  holdItem_ = -1;
  invalidate();
}

void Os::onSwipe(int dir) {
  if (appsSwipe(dir)) return;
  switch (view_) {
    case View::Boot:
      if (dir == 3) bootPrev();
      else if (dir == 0 && bootStep_ == BootStep::Birth) bootNext();
      return;
    case View::Home:
      if (dir == 0 || dir == 1) {
        go(View::Launcher);
        face_.react(X_happy, 0.8f);
      } else if (dir == 2) {
        go(View::Today);
      }
      return;
    case View::Launcher:
      if (dir == 0) orbit_ = (orbit_ + 1) % appCount();
      else if (dir == 1) orbit_ = (orbit_ + appCount() - 1) % appCount();
      else if (dir == 3) back();
      else if (dir == 2) go(View::Today);
      invalidate();
      return;
    case View::Alarms:
    case View::Notes:
    case View::Settings:
    case View::Memory:
      if (dir == 2) {  // swipe up: the next page
        ++page_;
        invalidate();
        return;
      }
      if (dir == 3 || dir == 1) back();
      return;
    case View::Ringing: return;
    default:
      if (dir == 3 || dir == 1) back();
      return;
  }
}

void Os::onDoubleTap(float x, float y) {
  if (claude_.prompt && claudeHoldView(view_)) {  // 2x = deny
    brainEvents_.push_back(Ev::DoubleTap);
    return;
  }
  if (view_ == View::Home) {
    brainEvents_.push_back(Ev::DoubleTap);
    return;
  }
  onTap(x, y);  // elsewhere a double tap is two taps
}

void Os::onTap(float x, float y) {
  if (claude_.prompt && claudeHoldView(view_) && view_ != View::Talk) return;  // on a Claude request a single tap does nothing
  if (toastLeft_ > 0 && y < g_.s(70)) {
    if (memoryToastTap()) return;  // "Remembered: … · tap to undo"
    toastLeft_ = 0;
    invalidate();
    return;
  }
  if (appsTap(x, y)) return;  // the apps' own taps, and quick replies on a card
  switch (view_) {
    case View::Home: brainEvents_.push_back(Ev::Tap); return;
    case View::Answer:
      if (thinking_) return;
      if (acceptMode_) {  // only the two buttons answer it
        const int id = hitItem(x, y);
        if (id == IdAccept || id == IdReject) answerAccept(id == IdAccept);
        return;
      }
      if (cardHidden_) {  // a private card: the text shows after a tap
        cardHidden_ = false;
        reply_.say = privateBody_;
        privateBody_.clear();
        answerT_ = 0;
        invalidate();
        return;
      }
      back();
      return;
    case View::Boot:
      if (bootStep_ == BootStep::Birth) {
        bootNext();
        return;
      }
      break;
    default: break;
  }
  const int id = hitItem(x, y);
  if (id >= 0) activate(id);
}

// ---------------------------------------------------------- the actions ---

void Os::activate(int id) {
  invalidate();
  switch (view_) {
    case View::Boot:
      if (bootStep_ == BootStep::Name) {
        if (id == IdType) {
          openKeyboard(KbName);
          return;
        }
        if (id >= IdRow) {
          buildItems(items_);
          for (const Item& it : items_)
            if (it.id == id) snprintf(set_.name, sizeof set_.name, "%s", it.label.c_str());
          face_.react(X_happy, 1.2f);
          bootNext();
        }
      } else if (bootStep_ == BootStep::Brain) {
        if (id >= IdRow && id < IdRow + 4) {
          static const AiMode kModes[] = {AiMode::Cloud, AiMode::Claude, AiMode::ChatGpt, AiMode::None};
          set_.ai = (uint8_t)kModes[id - IdRow];
          pushCmd(OsCmd::SaveSettings);
          if (needsSetup() && !net_.portal) pushCmd(OsCmd::StartPortal);
          face_.react(aiMode() == AiMode::None ? X_smug : X_excited, 1.2f);
          if (aiMode() == AiMode::Cloud && !needsSetup() && !net_.paired) {  // show the pairing code
            pairReturn_ = View::Boot;
            go(View::Pair);
          }
        } else if (id == IdNext || id == IdLater) {
          bootNext();
        }
      }
      return;
    case View::Launcher:
      // the chosen app, or a neighbour straight away: the first three apps are two gestures from the eyes
      if (id == IdCenter) {
        openApp(appAt(orbit_));
      } else if (id == IdRow) {
        orbit_ = (orbit_ + appCount() - 1) % appCount();
        openApp(appAt(orbit_));
      } else if (id == IdRow + 1) {
        orbit_ = (orbit_ + 1) % appCount();
        openApp(appAt(orbit_));
      }
      return;
    case View::Talk:
      if (id == IdType) openKeyboard(KbTalk);
      return;
    case View::Alarms:
      if (id == IdNew) {
        if (alarms_ && alarms_->count() >= Alarms::kMax) {
          toast(tr("16 alarms is the limit", "Maximum 16 alarme"), kAmber);
          return;
        }
        const int h = now_ ? (localclock::hour(now_) + 1) % 24 : 7;
        tp_.setLang(ro() ? Lang::Ro : Lang::En);
        tp_.setNow(now_);
        tp_.open(alarms_ && alarms_->count() == 0 ? 7 : h, 0);
        go(View::Dial);
      } else if (id >= IdRow && alarms_) {
        const int i = id - IdRow;
        if (i < alarms_->count()) {
          Alarm& a = alarms_->at(i);
          a.enabled = !a.enabled;
          a.snoozeUntil = 0;
          pushCmd(OsCmd::SaveAlarms);
          face_.react(a.enabled ? X_approve : X_bored, a.enabled ? 0 : 1.0f);
        }
      }
      return;
    case View::Ringing:
      if (id == IdSnooze && ringingAlarm_ >= 0 && alarms_) {
        alarms_->snooze(ringingAlarm_, now_);
        toast(tr("Snoozed 5 min", "Amânată 5 min"), kAmber);
      } else if (id == IdStop) {
        if (ringingAlarm_ >= 0 && alarms_) alarms_->dismiss(ringingAlarm_);
        face_.react(X_happy, 1.2f);
      } else {
        return;
      }
      ringingAlarm_ = -1;
      timerRinging_ = false;
      silence_ = true;
      pushCmd(OsCmd::SaveAlarms);
      go(View::Home);
      return;
    case View::Timer:
      if (id >= IdRow) {
        static const int kMin[] = {1, 3, 5, 10, 25};
        const int m = kMin[(id - IdRow) % 5];
        startTimer(m * 60, m == 25);
      } else if (id == IdPause) {
        timerPaused_ = !timerPaused_;
      } else if (id == IdStop) {
        stopTimer();
      }
      return;
    case View::Notes:
      if (id == IdNew) {
        openKeyboard(KbNote);
      } else if (id >= IdRow) {
        noteSel_ = id - IdRow;
        go(View::NoteView);
      }
      return;
    case View::NoteView:
      if (id == IdType && noteSel_ >= 0 && noteSel_ < (int)notes_.size()) openKeyboard(KbNoteEdit, notes_[noteSel_].text);
      return;
    case View::Memory: memoryActivate(id); return;  // SOUL Memory (OsMemory.cpp)
    case View::Settings:
      switch (id) {
        case IdRow + 0:
          set_.bright = (uint8_t)((set_.bright + 1) % 4);
          break;
        case IdRow + 1: go(View::AiMode); return;
        case IdRow + 2: go(View::Wifi); return;
        case IdRow + 3:
          set_.lang = set_.lang ? 0 : 1;
          break;
        case IdRow + 4: go(View::MySoul); return;
        case IdRow + 5:
          set_.largeText = !set_.largeText;
          break;
        case IdRow + 6: go(View::About); return;
        case IdRow + 7:
          set_.debug = !set_.debug;
          break;
        case IdRow + 8:
          set_.nightOff = !set_.nightOff;
          break;
        case IdRow + 11: memoryOpen(); return;  // SOUL Memory
        case IdRow + 12: go(View::AppsSettings); return;  // Settings › Apps: order and hide
        case IdRow + 9: {  // pause connectors: a user-only switch, never from the cloud or an AI
          if (!net_.paired) {
            toast(tr("Pair with your account first", "Leagă-mă întâi de cont"), kAmber);
            return;
          }
          CloudOut o;
          o.kind = CloudOut::Connectors;
          o.paused = !net_.connectorsPaused;
          net_.connectorsPaused = o.paused;
          outs_.push_back(o);
          toast(o.paused ? tr("Claude & co. paused", "Claude & co. pe pauză") : tr("Claude & co. back on", "Claude & co. pornite"),
                o.paused ? kAmber : kMint);
          invalidate();
          return;
        }
        default: return;
      }
      pushCmd(OsCmd::SaveSettings);
      return;
    case View::AiMode:
      if (id >= IdRow && id < IdRow + 5) {
        static const AiMode kModes[] = {AiMode::Cloud, AiMode::Claude, AiMode::ChatGpt, AiMode::Bridge, AiMode::None};
        const AiMode was = aiMode();
        set_.ai = (uint8_t)kModes[id - IdRow];
        pushCmd(OsCmd::SaveSettings);
        history_.clear();
        face_.react(aiMode() == AiMode::None ? X_smug : X_excited, 1.2f);
        if (net_.paired && (aiMode() == AiMode::Bridge || (was == AiMode::Bridge && aiMode() == AiMode::None))) {
          CloudOut o;  // the account keeps what was picked here (a touch), so a reconnect does not undo it
          o.kind = CloudOut::Brain;
          o.text = aiMode() == AiMode::Bridge ? "bridge" : "none";
          outs_.push_back(o);
        }
        if (aiMode() == AiMode::Bridge && net_.configured) {
          bridgeOpen();
        } else if (needsSetup()) {
          toast(tr("Add it on your phone: Wi-Fi setup", "Pune-o din telefon: Wi-Fi"), kAmber, 3);
          if (!net_.portal) pushCmd(OsCmd::StartPortal);
          go(View::Wifi);
        } else if (aiMode() == AiMode::Cloud) {  // the pairing code, or once paired the "Connect Claude" QR
          pairReturn_ = View::AiMode;
          go(View::Pair);
        }
      } else if (id == IdForget) {
        pushCmd(OsCmd::ForgetKeys);
        toast(tr("Keys forgotten", "Cheile au fost uitate"), kAmber);
      }
      return;
    case View::Claude:
      if (id == IdInbox) {
        if (!net_.paired) {
          pairReturn_ = View::Claude;
          go(View::Pair);
        } else {
          openKeyboard(KbInbox);
        }
      }
      return;
    case View::Bridge:
      if (id == IdNew) {
        bridgeOpen();
        toast(tr("New code", "Cod nou"), kMint);
      } else if (id == IdForget) {
        pushCmd(OsCmd::BridgeForget);
        if (net_.paired) {
          CloudOut o;
          o.kind = CloudOut::BridgeForget;
          outs_.push_back(o);
        }
        net_.bridgeOnline = net_.bridgePaired = false;
        net_.bridgeName.clear();
        toast(tr("Computers forgotten", "Calculatoare uitate"), kAmber);
        face_.react(X_bored, 1.0f);
      }
      return;
    case View::Pair:
      if ((id == IdAccept || id == IdReject) && !net_.confirmPid.empty()) {
        CloudOut o;  // a touch on SOUL: the only way to answer pair.confirm (§6.3)
        o.kind = id == IdAccept ? CloudOut::PairOk : CloudOut::PairNo;
        o.pid = net_.confirmPid;
        outs_.push_back(o);
        net_.confirmPid.clear();
        face_.react(id == IdAccept ? X_happy : X_smug, 1.0f);
        if (id == IdReject) toast(tr("Not paired", "Nu m-am legat"), kAmber);
        invalidate();
      } else if (id == IdSetup) {
        pushCmd(OsCmd::StartPortal);
        go(View::Wifi);
      }
      return;
    case View::Wifi:
      if (id == IdSetup) {
        pushCmd(OsCmd::StartPortal);
        page_ = 0;
      } else if (id == IdStopSetup) {
        pushCmd(OsCmd::StopPortal);
      } else if (id == IdType) {
        openKeyboard(KbKey);
      } else if (id == IdHotspot) {
        page_ = 1;  // how to switch the hotspot on (iPhone / Android), then type its name here or use the phone page
        invalidate();
      } else if (id == IdHotspotType) {
        pendingWifi_ = WifiNet();
        pendingWifi_.kind = WifiKind::Hotspot;
        pendingWifi_.prio = wifiDefaultPrio(WifiKind::Hotspot);
        openKeyboard(KbWifiName);
      }
      return;
    case View::MySoul:
      if (id == IdName) openKeyboard(KbName, set_.name);
      return;
    default: appsActivate(id); return;
  }
}

void Os::openKeyboard(int ctx, const std::string& initial) {
  KbConfig c;
  c.uiLang = ro() ? Lang::Ro : Lang::En;
  c.action = ctx == KbTalk ? KbAction::Send : KbAction::Save;
  c.maxChars = ctx == KbNote || ctx == KbNoteEdit ? 300 : ctx == KbName ? 16 : ctx == KbKey ? 220 : 280;
  // keys, network names and passwords are typed exactly: no auto-capital, no auto-diacritics, no ". "
  c.verbatim = ctx == KbKey || ctx == KbWifiName || ctx == KbWifiPass;
  switch (ctx) {
    case KbTalk:
      c.placeholder = ro() ? "Întreabă ceva…" : "Ask something…";
      c.chips[0] = ro() ? "Trezește-mă la 7" : "Wake me at 7";
      c.chips[1] = ro() ? "Minutar 10 min" : "Timer 10 min";
      c.chips[2] = ro() ? "Ce vreme e?" : "Tell me a joke";
      break;
    case KbNote:
    case KbNoteEdit:
      c.placeholder = ro() ? "Notiță nouă…" : "New note…";
      c.chips[0] = ro() ? "Cumpără lapte" : "Buy milk";
      c.chips[1] = ro() ? "Idee:" : "Idea:";
      c.chips[2] = ro() ? "Sună-o pe mama" : "Call mom";
      break;
    case KbName:
      c.placeholder = ro() ? "Numele meu…" : "My name…";
      break;
    case KbKey:
      c.placeholder = aiMode() == AiMode::ChatGpt ? "sk-…" : "sk-ant-…";
      break;
    case KbWifiName:
      c.maxChars = 32;
      c.placeholder = ro() ? "Numele hotspotului…" : "Hotspot name…";
      c.chips[0] = "iPhone";
      c.chips[1] = "AndroidAP";
      break;
    case KbWifiPass:
      c.maxChars = 63;
      c.placeholder = ro() ? "Parola hotspotului…" : "Hotspot password…";
      break;
    case KbInbox:
      c.action = KbAction::Send;
      c.maxChars = 500;
      c.placeholder = ro() ? "Întrebarea pentru Claude…" : "A question for your Claude…";
      c.chips[0] = ro() ? "Planul de mâine?" : "Plan my tomorrow";
      c.chips[1] = ro() ? "Rețetă rapidă" : "Quick recipe idea";
      c.chips[2] = ro() ? "Explică-mi" : "Explain";
      break;
    default: break;
  }
  if (ro()) c.undoLabel = "\xE2\x86\xB6 Anulează";
  appsKbConfig(ctx, c);
  kbCtx_ = ctx;
  kbReturn_ = view_ == View::Keyboard ? kbReturn_ : view_;
  kb_.open(c, initial);
  view_ = View::Keyboard;
  viewT_ = 0;
  fade_ = 0;
  invalidate();
}

void Os::kbCommit(const std::string& text) {
  const int ctx = kbCtx_;
  view_ = kbReturn_;
  viewT_ = 0;
  fade_ = 0;
  invalidate();
  if (appsKbCommit(ctx, text)) return;
  switch (ctx) {
    case KbTalk:
      if (!text.empty()) ask(text);
      break;
    case KbNote:
      if (!text.empty()) {
        addNote(text);
        face_.react(X_approve);
        toast(tr("Note saved", "Notiță salvată"), kMint);
      }
      break;
    case KbNoteEdit:
      if (noteSel_ >= 0 && noteSel_ < (int)notes_.size()) {
        if (text.empty()) notes_.erase(notes_.begin() + noteSel_);
        else notes_[noteSel_].text = text;
        pushCmd(OsCmd::SaveNotes);
        view_ = View::Notes;
      }
      break;
    case KbName:
      if (!text.empty()) {
        snprintf(set_.name, sizeof set_.name, "%s", text.c_str());
        pushCmd(OsCmd::SaveSettings);
        face_.react(X_happy, 1.2f);
        if (view_ == View::Boot && bootStep_ == BootStep::Name) bootNext();
      }
      break;
    case KbInbox:
      if (!text.empty()) {
        CloudOut o;
        o.kind = CloudOut::Inbox;
        o.text = text;
        o.created = now_;
        if (outs_.size() < 50) outs_.push_back(o);
        face_.react(X_wink, 1.4f);
        toast(tr("Left for your Claude: say \u201Ccheck my SOUL\u201D", "Lăsat lui Claude: spune-i \u201Evezi SOUL\u201D"), kMint, 4.5f);
      }
      break;
    case KbWifiName:
      if (!text.empty() && text.size() <= 32) {
        pendingWifi_.ssid = text;
        openKeyboard(KbWifiPass);
      }
      break;
    case KbWifiPass:
      if (pendingWifi_.ssid.empty()) break;
      if (!text.empty() && (text.size() < 8 || text.size() > 63)) {
        toast(tr("A hotspot password has 8 to 63 characters", "Parola are între 8 și 63 de caractere"), kAmber, 3.5f);
        face_.react(X_confused, 1.4f);
        openKeyboard(KbWifiPass);
        break;
      }
      pendingWifi_.pass = text;
      pushCmd(OsCmd::AddWifi);
      page_ = 0;
      toast(tr("Saved: I'll join it when it's on", "Salvat: mă conectez când e pornit"), kMint, 3.5f);
      face_.react(X_approve);
      break;
    case KbKey:
      if (keyLooksValid(aiMode(), text)) {
        pendingKey_ = text;
        pushCmd(OsCmd::SetKey);
        toast(tr("Key saved on this SOUL", "Cheie salvată pe SOUL"), kMint);
        face_.react(X_approve);
      } else {
        toast(tr("That doesn't look like a key", "Nu pare o cheie"), kAmber);
        face_.react(X_confused, 1.4f);
      }
      break;
    default: memoryKbCommit(ctx, text); break;  // SOUL Memory's search field
  }
}

// ------------------------------------------------------------------- AI ---

AiContext Os::context() const {
  AiContext c;
  c.name = set_.name;
  c.ro = ro();
  c.now = now_;
  if (alarms_) {
    static const char* const kRep[] = {"once", "daily", "weekdays", "weekend"};
    for (int i = 0; i < alarms_->count(); ++i) {
      const Alarm& a = alarms_->at(i);
      const char* rep = a.days == 0 ? kRep[0] : a.days == 0x7F ? kRep[1] : a.days == 0x1F ? kRep[2] : a.days == 0x60 ? kRep[3] : "some days";
      char b[96];
      snprintf(b, sizeof b, "%s%02u:%02u %s \"%s\" %s", c.alarms.empty() ? "" : "; ", a.hour, a.minute, rep, a.label,
               a.enabled ? "on" : "off");
      c.alarms += b;
    }
  }
  int n = 0;
  for (const Reminder& r : rems_) {
    if (n++ >= 5) break;
    char b[128];
    const bool tomorrow = now_ && r.when / 86400 > now_ / 86400;
    snprintf(b, sizeof b, "%s%02d:%02d%s \"%s\"", c.reminders.empty() ? "" : "; ", (int)(r.when % 86400 / 3600),
             (int)(r.when % 3600 / 60), tomorrow ? " tomorrow" : "", r.text.c_str());
    c.reminders += b;
  }
  c.timerLeftMin = timerRun_ ? (int)ceilf(timerLeft_ / 60.0f) : -1;
  c.notes = (int)notes_.size();
  return c;
}

void Os::bridgeOpen() {
  pushCmd(OsCmd::BridgePair);  // the 6-digit code of SOUL's own LAN server
  if (net_.paired) {           // and SOUL Cloud's 8-character one, which works from any network
    CloudOut o;
    o.kind = CloudOut::BridgeCode;
    outs_.push_back(o);
  }
  go(View::Bridge);
}

void Os::ask(const std::string& text) {
  answerReturn_ = view_ == View::Answer || view_ == View::Keyboard ? View::Home : view_;
  if (answerReturn_ == View::Boot) answerReturn_ = View::Home;
  chips_.clear();
  turnChips_.clear();
  cardTitle_.clear();
  reply_ = AiReply();
  lastErr_ = AiErr::None;
  if (memoryAsk(text)) return;  // SOUL Memory: "remember that…", "forget…", answered from memory (OsMemory.cpp)
  if (aiMode() == AiMode::None) {
    AiReply r = localReply(text, now_, ro(), true);
    runActions(r.actions, &chips_);
    showAnswer(r, AiErr::None, ro() ? "Fără AI · pe device" : "No AI · on the device");
    return;
  }
  if (!net_.connected) {
    AiReply r;
    if (localAct(text, now_, ro(), r)) {  // the on-device rules did it (an alarm, a timer, a note...)
      runActions(r.actions, &chips_);
      showAnswer(r, AiErr::Offline, "");
      return;
    }
    // nothing the rules can do: kept for when SOUL is back online (capped, docs/09 §2)
    askQ_.push(text, t_);
    if (net_.saved > 0) pushCmd(OsCmd::WifiKick);
    const std::string n = std::to_string(askQ_.size());
    if (net_.captive)
      r.say = tr("This Wi-Fi wants a login page I can't open. Your phone's hotspot works. I'll ask when I'm online (",
                 "Wi-Fi-ul ăsta cere o pagină de login pe care n-o pot deschide. Hotspotul telefonului merge. Întreb când "
                 "sunt online (") + n + tr(" waiting).", " în așteptare).");
    else if (net_.saved == 0)
      r.say = tr("I have no Wi-Fi yet: Settings \u203A Wi-Fi. I'll ask once I'm online (", "N-am Wi-Fi încă: Setări \u203A Wi-Fi. "
                 "Întreb când sunt online (") + n + tr(" waiting).", " în așteptare).");
    else
      r.say = tr("No internet right now. I'll ask as soon as I'm back online (", "N-am internet acum. Întreb imediat ce revin "
                 "online (") + n + tr(" waiting).", " în așteptare).");
    showAnswer(r, AiErr::None, ro() ? "Fără internet · păstrat" : "Offline · kept");
    face_.react(X_wink, 1.2f);
    return;
  }
  if (aiMode() == AiMode::Bridge && !net_.bridgeOnline) {  // the computer is off: the rules do what they can
    AiReply r;
    if (localAct(text, now_, ro(), r)) runActions(r.actions, &chips_);
    else r.say.clear();
    showAnswer(r, AiErr::BridgeOffline, ro() ? "Fără calculator · pe device" : "No computer · on the device");
    return;
  }
  deferred_ = false;
  sendJob(text);
}

void Os::sendJob(const std::string& text) {
  AiJob j;
  j.text = text;
  j.ctx = context();
  j.ctx.memory = memoryBlock(text);  // SOUL Memory: what SOUL knows about you, for whichever AI answers
  j.history = history_;
  jobs_.push_back(j);
  history_.push_back({true, text});
  thinking_ = true;
  thinkT_ = 0;
  reply_.say = text;  // shown dim while thinking
  go(View::Answer);
}

bool Os::needsInternet() const { return set_.booted && aiMode() != AiMode::None; }

void Os::aiResult(const AiOutcome& o) {
  if (!thinking_) return;  // cancelled
  thinking_ = false;
  chips_.clear();
  const char* src = aiMode() == AiMode::Claude ? (ro() ? "Claude · cheia ta" : "Claude · your key")
                    : aiMode() == AiMode::ChatGpt ? (ro() ? "ChatGPT · cheia ta" : "ChatGPT · your key")
                    : aiMode() == AiMode::Bridge  ? (ro() ? "Claude · calculatorul tău" : "Claude · your computer")
                                                  : "SOUL Cloud";
  const std::string question = history_.empty() ? std::string() : history_.back().text;
  const bool wasDeferred = deferred_;
  deferred_ = false;
  if (o.err != AiErr::None && wasDeferred && deferredTries_ < 2 &&
      (o.err == AiErr::Offline || o.err == AiErr::Network || o.err == AiErr::Timeout)) {
    if (!history_.empty() && history_.back().user) history_.pop_back();
    askQ_.push(deferredText_, t_, deferredTries_ + 1);  // the link dropped again: it waits for the next time
    onT_ = 0;
    showAnswer(AiReply(), o.err, src);
    return;
  }
  if (o.err != AiErr::None) {
    if (!history_.empty() && history_.back().user) history_.pop_back();
    // the on-device rules still do what they can (an alarm, a reminder, a timer)
    AiReply r;
    if (!o.noLocal && localAct(question, now_, ro(), r)) runActions(r.actions, &chips_);
    else r.say.clear();
    if (aiMode() == AiMode::Cloud && net_.relay && !net_.paired && (o.err == AiErr::NoKey || o.err == AiErr::BadKey) &&
        r.actions.empty())
      r.say = tr("Pair me with your account first: Settings \u203A AI \u203A SOUL Cloud.",
                 "Leagă-mă întâi de cont: Setări \u203A AI \u203A SOUL Cloud.");
    showAnswer(r, o.err, src);
    return;
  }
  history_.push_back({false, o.raw.size() > 1200 ? o.raw.substr(0, 1200) : o.raw});
  while (history_.size() > 12) history_.erase(history_.begin());
  chips_ = turnChips_;  // a cloud turn's actions arrived as pushes just before
  turnChips_.clear();
  runActions(o.reply.actions, &chips_);
  showAnswer(o.reply, AiErr::None, src);
  memoryApply(o.reply.memory, aiMode() == AiMode::Cloud ? FactSrc::Cloud : FactSrc::Ai);  // + "Remembered: …"
  if (o.note != AiErr::None) {  // SOUL Cloud answered with its rules: say why (bad key, allowance used...)
    toast(aiErrText(o.note, ro()), kAmber, 6.0f);
    face_.flash(kRose, 1.2f);
  }
}

void Os::voiceText(const std::string& text, AiErr err) {
  if (!voiceWait_) return;
  voiceWait_ = false;
  if (err != AiErr::None || text.empty()) {
    AiReply r;
    if (err == AiErr::None) r.say = tr("I didn't catch that.", "N-am prins ce ai spus.");
    showAnswer(r, err, "");
    return;
  }
  if (voiceFrom_ == View::Notes) {  // dictated note: saved here, no AI call
    addNote(text);
    face_.react(X_approve);
    toast(tr("Note saved", "Notiță salvată"), kMint);
    return;
  }
  ask(text);
}

void Os::showAnswer(const AiReply& r, AiErr err, const char* src) {
  if (acceptMode_) answerAccept(false);  // a question that was not answered is not armed
  cardHidden_ = false;
  privateBody_.clear();
  cardTitle_.clear();
  reply_ = r;
  lastErr_ = err;
  answerSrc_ = src ? src : "";
  answerT_ = 0;
  const size_t len = r.say.size() + (err != AiErr::None ? 40 : 0);
  answerFor_ = 6.5f + (len > 80 ? (len - 80) * 0.03f : 0.0f);
  if (answerFor_ > 14) answerFor_ = 14;
  if (err != AiErr::None) {
    face_.flash(kRose, 1.2f);  // the face goes "confused" through FaceState::Error
  } else if (!r.actions.empty()) {
    face_.react(X_approve);
    face_.flash(kMint, 1.4f);
  } else {
    const int e = exprByName(r.face.c_str());
    if (e >= 0) face_.react(e, 2.0f);
  }
  if (view_ != View::Answer) go(View::Answer);
  invalidate();
}

void Os::runActions(const std::vector<AiAction>& acts, std::vector<std::string>* chips) {
  for (const AiAction& a : acts) {
    std::string chip;
    switch (a.type) {
      case AiAction::AlarmSet:
        addAlarm(a.hour, a.minute, a.days, a.text.empty() ? tr("Alarm", "Alarmă") : a.text);
        chip = tr("Alarm ", "Alarmă ") + hhmm(a.hour, a.minute);
        break;
      case AiAction::TimerStart:
      case AiAction::FocusStart: {
        const int secs = a.seconds ? (int)a.seconds : a.minutes * 60;
        startTimer(secs, a.type == AiAction::FocusStart);
        chip = (a.type == AiAction::FocusStart ? std::string("Focus ") : tr("Timer ", "Minutar ")) +
               (secs % 60 ? std::to_string(secs) + " s" : std::to_string(secs / 60) + " min");
        break;
      }
      case AiAction::ReminderCreate:
        if (a.when) {  // an absolute local date (SOUL Cloud): maybe days ahead
          addReminderAt(a.when, a.text);
          const uint32_t days = now_ && a.when / 86400 > now_ / 86400 ? a.when / 86400 - now_ / 86400 : 0;
          char d[24] = "";
          if (days == 1) {
            snprintf(d, sizeof d, "%s", ro() ? "mâine " : "tomorrow ");
          } else if (days > 1) {  // day.month
            const time_t t = (time_t)a.when;
            struct tm tm;
            gmtime_r(&t, &tm);
            snprintf(d, sizeof d, "%d.%02d ", tm.tm_mday, tm.tm_mon + 1);
          }
          chip = tr("Reminder ", "Memento ") + d + hhmm(a.hour, a.minute);
        } else {
          addReminder(a.hour, a.minute, a.tomorrow, a.text);
          chip = tr("Reminder ", "Memento ") + (a.tomorrow ? tr("tomorrow ", "mâine ") : std::string()) + hhmm(a.hour, a.minute);
        }
        break;
      case AiAction::NoteCreate:
        addNote(a.text);
        chip = tr("Note saved", "Notiță salvată");
        break;
    }
    if (chips) chips->push_back(chip);
  }
}

// ------------------------------------------------------------ the data ---

std::string Os::hhmm(int h, int m) const {
  char b[16];
  snprintf(b, sizeof b, "%02d:%02d", h, m);
  return b;
}

void Os::addAlarm(int h, int m, uint8_t days, const std::string& label) {
  if (!alarms_) return;
  Alarm a;
  a.hour = (uint8_t)h;
  a.minute = (uint8_t)m;
  a.days = days;
  a.enabled = true;
  a.setLabel(label.c_str());
  if (alarms_->add(a, now_) < 0) return;
  pushCmd(OsCmd::SaveAlarms);
  AiAction o;
  o.type = AiAction::AlarmSet;
  o.hour = (uint8_t)h;
  o.minute = (uint8_t)m;
  o.days = days;
  o.text = label;
  outItem(o);
}

// made on SOUL (not pushed by the cloud): tell SOUL Cloud (item.add), if one is set
void Os::outItem(const AiAction& a) {
  if (applyingCloud_ || !net_.relay) return;
  CloudOut o;
  o.kind = CloudOut::Item;
  o.act = a;
  o.created = now_;
  if (outs_.size() >= 50) outs_.erase(outs_.begin());
  outs_.push_back(o);
}

void Os::addNote(const std::string& text) {
  Note n;
  n.text = text;
  n.t = now_;
  notes_.insert(notes_.begin(), n);
  if (notes_.size() > 24) notes_.pop_back();
  pushCmd(OsCmd::SaveNotes);
  AiAction o;
  o.type = AiAction::NoteCreate;
  o.text = text;
  outItem(o);
}

void Os::addReminder(int h, int m, bool tomorrow, const std::string& text) {
  if (!now_) return;
  uint32_t when = localclock::dayStart(now_) + (uint32_t)h * 3600u + (uint32_t)m * 60u;
  if (tomorrow || when <= now_) when += 86400u;  // a time already passed moves to tomorrow
  addReminderAt(when, text);
}

void Os::addReminderAt(uint32_t when, const std::string& text) {
  Reminder r;
  r.when = when;
  r.text = text.empty() ? tr("Reminder", "Memento") : text;
  rems_.push_back(r);
  if (rems_.size() > 24) rems_.erase(rems_.begin());
  pushCmd(OsCmd::SaveReminders);
  AiAction o;
  o.type = AiAction::ReminderCreate;
  o.when = when;
  o.hour = (uint8_t)(when % 86400 / 3600);
  o.minute = (uint8_t)(when % 3600 / 60);
  o.text = r.text;
  outItem(o);
}

void Os::startTimer(int seconds, bool focus) {
  timerRun_ = true;
  timerPaused_ = false;
  timerRinging_ = false;
  timerFocus_ = focus;
  timerTotal_ = seconds;
  timerLeft_ = (float)seconds;
  invalidate();
}

void Os::stopTimer() {
  timerRun_ = timerPaused_ = timerRinging_ = false;
  silence_ = true;
  invalidate();
}

int Os::timerLeft() const { return timerRun_ ? (int)ceilf(timerLeft_) : -1; }

void Os::tickTimer(float dt) {
  if (!timerRun_ || timerPaused_) return;
  timerLeft_ -= dt;
  const int s = (int)ceilf(timerLeft_);
  if (s != lastTimerSec_) {
    lastTimerSec_ = s;
    if (view_ == View::Timer || view_ == View::Home || view_ == View::Today) invalidate();
  }
  if (timerLeft_ <= 0) {
    timerRun_ = false;
    timerRinging_ = true;
    ringingAlarm_ = -1;
    face_.react(X_excited, 2.4f);
    brainEvents_.push_back(Ev::AlarmDue);  // wakes the Brain whatever its mode
    go(View::Ringing);
  }
}

void Os::tickReminders() {
  if (!now_) return;
  for (size_t i = 0; i < rems_.size(); ++i) {
    if (rems_[i].when <= now_) {
      if (now_ - rems_[i].when < 600) {  // say it (missed by more than 10 min: just drop it)
        toast(rems_[i].text, kAmber, 6.0f);
        face_.react(X_surprised, 1.6f);
        brainEvents_.push_back(Ev::AlarmDue);
      }
      for (size_t k = 0; k < refs_.size(); ++k)  // one SOUL Cloud put here: keep its list truthful
        if (refs_[k].kind == 1 && refs_[k].k1 == rems_[i].when && refs_[k].k2 == hashStr(rems_[i].text.c_str())) {
          CloudOut o;
          o.kind = CloudOut::State;
          o.itemId = refs_[k].id;
          o.state = "rang";
          outs_.push_back(o);
          refs_.erase(refs_.begin() + (long)k);
          pushCmd(OsCmd::SaveCloudRefs);
          break;
        }
      rems_.erase(rems_.begin() + i);
      pushCmd(OsCmd::SaveReminders);
      return;
    }
  }
}

void Os::alarmDue(int index) {
  ringingAlarm_ = index;
  if (view_ == View::Keyboard) kb_.cancel();
  view_ = View::Home;  // make the change below a real one
  go(View::Ringing);
  brainEvents_.push_back(Ev::AlarmDue);
  face_.react(X_wake);
}

std::string Os::nextAlarmText() const {
  if (!alarms_ || !now_) return "";
  uint32_t when = 0;
  const int i = alarms_->next(now_, when);
  if (i < 0) return "";
  const uint32_t mins = (when - now_ + 59) / 60;
  char b[64];
  if (mins < 60) snprintf(b, sizeof b, "%02u:%02u · %s %u min", alarms_->at(i).hour, alarms_->at(i).minute, ro() ? "în" : "in", (unsigned)mins);
  else snprintf(b, sizeof b, "%02u:%02u · %s %u h %u min", alarms_->at(i).hour, alarms_->at(i).minute, ro() ? "în" : "in", (unsigned)(mins / 60), (unsigned)(mins % 60));
  return b;
}

// --------------------------------------------------------------- update ---

void Os::update(float dt, Brain& brain) {
  t_ += dt;
  viewT_ += dt;
  if (buttonDown_) buttonT_ += dt;
  if (fade_ < 1) {
    fade_ = viewT_ / kFadeS;
    if (fade_ > 1) fade_ = 1;
    invalidate();
  }
  if (toastLeft_ > 0) {
    toastLeft_ -= dt;
    if (toastLeft_ <= 0) {
      memUndoId_ = 0;  // the undo goes with the toast
      invalidate();
    }
  }
  memoryBackupTick();
  // SoulOS 5: the peek fades back to the eyes; a screen left alone goes back to them too
  if (peekT_ > 0) {
    peekT_ -= dt;
    if (peekT_ <= 0 || view_ != View::Home) {
      peekT_ = 0;
      invalidate();
    }
  }
  if (!down_) idleT_ += dt;
  if (idleT_ > kAppIdleS && idleReturns()) home();
  if (view_ == View::Keyboard) {
    kb_.update(dt);
    setDirtyFromKeyboard();
    KbResult r;
    if (kb_.poll(r)) {
      if (r == KbResult::Commit) kbCommit(kb_.committed());
      else go(kbReturn_);
    }
  } else if (view_ == View::Dial) {
    tp_.setNow(now_);
    tp_.update(dt);
    if (tp_.changed()) invalidate();
    KbResult r;
    if (tp_.poll(r)) {
      if (r == KbResult::Commit) {  // saved at once (3 touches: +, drag the hour, ✓)
        addAlarm(tp_.hour(), tp_.minute(), 0, tr("Alarm", "Alarmă"));
        toast(tr("Alarm set ", "Alarmă pusă ") + hhmm(tp_.hour(), tp_.minute()), kMint);
        face_.react(X_approve);
      }
      go(View::Alarms);
    }
  }
  if (holdItem_ >= 0) {  // hold a row: delete (alarms, notes) / forget (Wi-Fi, keys) / start over
    holdItemT_ += dt;
    invalidate();
    if (holdItemT_ >= 1.0f) {
      const int id = holdItem_;
      holdItem_ = -1;
      if (view_ == View::Alarms && id >= IdRow && alarms_ && id - IdRow < alarms_->count()) {
        alarms_->remove(id - IdRow);
        pushCmd(OsCmd::SaveAlarms);
        toast(tr("Alarm deleted", "Alarmă ștearsă"), kAmber);
        face_.react(X_sad, 1.0f);
      } else if (view_ == View::Notes && id >= IdRow && id - IdRow < (int)notes_.size()) {
        notes_.erase(notes_.begin() + (id - IdRow));
        pushCmd(OsCmd::SaveNotes);
        toast(tr("Note deleted", "Notiță ștearsă"), kAmber);
      } else if (view_ == View::NoteView && id == IdDelete && noteSel_ >= 0 && noteSel_ < (int)notes_.size()) {
        notes_.erase(notes_.begin() + noteSel_);
        pushCmd(OsCmd::SaveNotes);
        toast(tr("Note deleted", "Notiță ștearsă"), kAmber);
        go(View::Notes);
      } else if (view_ == View::Wifi && id == IdForget) {
        pushCmd(OsCmd::ForgetWifi);
        toast(tr("Wi-Fi forgotten", "Wi-Fi uitat"), kAmber);
      } else if (view_ == View::AiMode && id >= IdRow && id <= IdRow + 2) {
        if (id == IdRow + 1 || id == IdRow + 2) {
          set_.ai = (uint8_t)(id == IdRow + 1 ? AiMode::Claude : AiMode::ChatGpt);
          openKeyboard(KbKey);  // type the key on the round keyboard (masked on screen)
        }
      } else if (view_ == View::Settings && id == IdRow + 10) {
        restartBoot();
      } else if (view_ == View::Memory) {
        memoryHoldDone(id);
      } else {
        appsHoldDone(id);  // habits, world clock: hold a row = remove it
      }
    }
  }
  if (reactAfter_ >= 0) {
    reactAfterT_ -= dt;
    if (reactAfterT_ <= 0) {
      face_.react(reactAfter_, 1.4f);
      reactAfter_ = -1;
    }
  }
  if (pairDoneT_ > 0) {  // paired: show "hi <owner>" a moment, then carry on
    pairDoneT_ -= dt;
    if (pairDoneT_ <= 0) {
      pairDoneT_ = -1;
      if (view_ == View::Pair) {
        if (pairReturn_ == View::Boot) {
          go(View::Boot);
          bootNext();
        } else {
          back();
        }
      }
    }
  }
  if (view_ == View::Answer && !thinking_) {
    answerT_ += dt;
    if (answerT_ > answerFor_ && !down_) back();
  }
  if (thinking_) {
    thinkT_ += dt;
    if (thinkT_ > (aiMode() == AiMode::Bridge ? 130.0f : 45.0f)) {  // the device never waits forever
      AiOutcome o;
      o.err = AiErr::Timeout;
      aiResult(o);
    }
  }
  tickTimer(dt);
  appsUpdate(dt);
  tickReminders();
  // on the go: how long without / with the internet, and the questions kept while offline
  if (net_.connected) {
    onT_ += dt;
    offT_ = 0;
  } else {
    onT_ = 0;
    offT_ += dt;
  }
  {
    const bool brainReady = aiMode() == AiMode::Cloud    ? net_.cloudOnline
                            : aiMode() == AiMode::Bridge ? net_.bridgeOnline
                                                         : true;
    const bool calm = view_ == View::Home || view_ == View::Launcher || view_ == View::Today ||
                      (view_ == View::Answer && answerT_ > 3.0f && !acceptMode_);
    AskQueue::Item it;
    if (askQ_.size() && needsInternet() && net_.connected && onT_ > 3.0f && brainReady && calm && !thinking_ &&
        !listening_ && !voiceWait_ && jobs_.empty() && !down_ && askQ_.pop(t_, it)) {
      answerReturn_ = view_ == View::Answer ? answerReturn_ : view_;
      if (answerReturn_ == View::Answer || answerReturn_ == View::Boot) answerReturn_ = View::Home;
      chips_.clear();
      turnChips_.clear();
      cardTitle_.clear();
      reply_ = AiReply();
      lastErr_ = AiErr::None;
      deferred_ = true;
      deferredText_ = it.text;
      deferredTries_ = it.tries;
      sendJob(it.text);
      toast(tr("You asked earlier", "Ai întrebat mai devreme"), kMint, 2.5f);
      brainEvents_.push_back(Ev::AlarmDue);  // wakes the face for the answer
    }
  }
  // the clock on the rim
  const int minute = now_ ? (int)(now_ / 60) : -1;
  if (minute != lastMinute_) {
    lastMinute_ = minute;
    if (view_ == View::Home || view_ == View::Today || view_ == View::Talk || view_ == View::Launcher) invalidate();
  }
  if (view_ == View::Boot && bootStep_ == BootStep::Birth && viewT_ < 2.0f) invalidate();  // the chip id types out
  if (set_.debug && (int)(t_ * 2) != (int)((t_ - dt) * 2)) invalidate(g_.rect(130, 400, 336, 460));
  // the eyes' IMU gestures (double tap on the case, nod yes / no)
  {
    Ev me;
    while (face_.pollEvent(me)) motion(me);
  }
  // what the Brain hears
  brain.setAiLink(aiMode() != AiMode::None);
  for (Ev e : brainEvents_) brain.event(e);
  brainEvents_.clear();
  glassUpdate(dt, brain);
  face_.update(dt, faceInputs(brain));
}

// ------------------------------------------------------------- glass ---

bool Os::uiOn() const {
  if (view_ != View::Home) return true;
  if (asleep_) return false;
  return peekT_ > 0 || toastLeft_ > 0 || claude_.passkey != 0;
}

bool Os::faceMoment() const {
  if (asleep_) return true;
  bool fm;
  if (appsFaceMoment(fm)) return fm;  // breathe, eye memory, rhythm: the eyes are the subject (black)
  switch (view_) {
    case View::Home:
    case View::Talk:
    case View::Answer:
    case View::Ringing: return true;
    case View::Claude: return claude_.prompt;
    case View::Boot: return bootStep_ == BootStep::Birth || bootStep_ == BootStep::Hold;
    default: return false;
  }
}

GlassTone Os::glassTone() const {
  if (listening_) return GlassTone::Ice;
  if (view_ == View::Ringing && !timerRinging_) return GlassTone::Amber;
  if (claude_.prompt && (view_ == View::Claude || view_ == View::Home || view_ == View::Today)) return GlassTone::Amber;
  if (timerRinging_) return GlassTone::Mint;  // (a toast tints only its own capsule: no aura rebuild for it)
  if (view_ == View::Answer && !thinking_ && lastErr_ == AiErr::None) return GlassTone::Mint;
  return GlassTone::Default;
}

bool Os::idleReturns() const {
  bool r;
  if (appsIdleReturns(r)) return r;
  switch (view_) {
    case View::Launcher:
    case View::Today:
    case View::Alarms:
    case View::Notes:
    case View::NoteView:
    case View::Settings:
    case View::AiMode:
    case View::MySoul:
    case View::Memory:
    case View::About: return holdItem_ < 0;
    case View::Wifi: return !net_.portal;
    case View::Claude: return !claude_.prompt && !claude_.passkey;
    case View::Talk: return !listening_ && !thinking_ && !voiceWait_;
    case View::Timer: return !timerRun_;
    default: return false;  // the keyboard, the dial, ringing, answers (their own timer), pairing codes, first boot
  }
}

void Os::glassUpdate(float dt, const Brain& brain) {
  GlassLayer& G = glass();
  asleep_ = brain.mode() == Mode::Asleep || brain.mode() == Mode::Off;
  // the aura (never behind the eyes on a face moment); when a screen opens from the eyes it waits 0.2 s for
  // them to step back, so it never rises behind the big eyes
  const bool on = auraOn() && (auraLevel_ > 0 || viewT_ >= 0.2f);
  G.setTone(glassTone());
  if (G.step() && G.on()) invalidate();  // a new tone: built in the background over ~8 frames, then swapped in
  if (on && !G.on()) {
    G.setOn(true);
    auraLevel_ = 0;
    G.setLevel(0);
    invalidate();
  }
  const float target = on ? 1.0f : 0.0f;
  if (auraLevel_ != target) {  // the aura fades in / out in ~300 ms (16 steps)
    auraLevel_ += (target > auraLevel_ ? dt : -dt) / 0.3f;
    auraLevel_ = auraLevel_ < 0 ? 0 : (auraLevel_ > 1 ? 1 : auraLevel_);
    if (G.setLevel(auraLevel_)) invalidate();
    if (!on && auraLevel_ <= 0 && G.on()) {
      G.setOn(false);
      invalidate();
    }
  }
  // the read window: a slow drift + a lean against the tilt (the IMU), at most 4 times a second
  const eyes::EyeMotion& m = face_.motion();
  const float gv[3] = {m.gravX(), m.gravY(), m.gravZ()};
  for (int i = 0; i < 3; ++i) {
    if (!gravInit_) gLp_[i] = gv[i];
    gLp_[i] += (gv[i] - gLp_[i]) * (dt / 2.5f > 1 ? 1 : dt / 2.5f);
  }
  gravInit_ = true;
  offsetT_ += dt;
  if (offsetT_ >= 0.25f && G.on()) {
    offsetT_ = 0;
    const float M = (float)GlassLayer::kMargin;
    const float tx = clampf((gv[0] - gLp_[0]) * 40.0f, -0.5f * M, 0.5f * M);
    const float ty = clampf(-(gv[1] - gLp_[1]) * 40.0f, -0.5f * M, 0.5f * M);
    const float dx = 0.5f * M * sinf(t_ * 6.2831853f / 31.0f) + tx, dy = 0.5f * M * sinf(t_ * 6.2831853f / 37.0f + 1.0f) + ty;
    if (G.setOffset((int)lroundf(dx), (int)lroundf(dy))) invalidate();
  }
}

FaceInputs Os::faceInputs(const Brain& b) const {
  FaceInputs in;
  in.mode = b.mode();
  in.reaction = b.reaction();
  in.layout = layoutFor(view_);
  if (view_ == View::Keyboard) {
    in.look = true;  // the eyes watch the keys
    in.lookX = down_ ? (dx_ / g_.w - 0.5f) * 1.2f : 0;
    in.lookY = 0.6f;
  } else if (view_ == View::Dial) {
    const float a = tp_.knobAngle() * 3.14159265f / 180.0f;
    in.look = true;
    in.lookX = 0.8f * cosf(a);
    in.lookY = 0.8f * sinf(a);
  } else if (t_ < lookUntil_) {
    in.look = true;
    in.lookX = lookX_;
    in.lookY = lookY_;
  }
  if (listening_) in.state = FaceState::Listen;
  // a turn handed to the owner's computer: waiting (on its way) until Claude Code has it, then thinking
  else if (thinking_ && aiMode() == AiMode::Bridge && net_.askState == 1) in.state = FaceState::Wait;
  else if (thinking_ || voiceWait_) in.state = FaceState::Think;
  else if (view_ == View::Answer && lastErr_ != AiErr::None) in.state = FaceState::Error;
  else if (claude_.prompt) in.state = FaceState::Wait;
  else if (claude_.busy) in.state = FaceState::Busy;
  else if (power_.charging) in.state = FaceState::Charge;
  else if (power_.batPct >= 0 && power_.batPct < 10) in.state = FaceState::Low;
  else if (needsInternet() && net_.saved > 0 && offT_ > 20.0f && (view_ == View::Home || view_ == View::Launcher)) {
    // no internet for a while: heavier lids, and now and then a glance around, looking for a signal
    in.state = FaceState::Offline;
    const float ph = fmodf(t_, 9.0f);
    if (!in.look && ph < 1.6f) {
      in.look = true;
      in.lookX = 0.6f * sinf(ph / 1.6f * 6.2831853f);
      in.lookY = -0.35f;
    }
  }
  // standby (home, nothing showing): no rim light, the eyes alone say it (wide, looking at you)
  in.alert = (claude_.prompt && uiOn()) || view_ == View::Ringing;
  in.progress = b.approveProgress();
  if (power_.charging && power_.batPct >= 0) in.level = power_.batPct / 100.0f;
  if (view_ == View::Boot && bootStep_ == BootStep::Hold && !listening_) in.state = FaceState::Idle;
  appsFace(in);  // the apps' eyes: breathing, the games, the map's turn
  return in;
}

float Os::fpsHint(const Brain& b) const {
  if (view_ == View::Keyboard || view_ == View::Dial || down_ || fade_ < 1) return 30;
  if ((view_ == View::Games && apps_.game >= 0) || view_ == View::Breathe || (view_ == View::Maps && apps_.dragging)) return 30;
  if (b.mode() == Mode::Off) return 0;
  if (b.mode() == Mode::Asleep) return 10;
  if (b.mode() == Mode::Drowsy) return 15;
  if (thinking_ || listening_ || claude_.prompt || view_ == View::Ringing || b.reaction() != Reaction::None) return 30;
  return 24;  // calm and awake: the springs still look smooth at 24
}

float Os::backlight(float hour, const Brain& b) const {
  if (b.mode() == Mode::Off) return 0;
  const bool night = hour >= 0 && (hour >= 22.0f || hour < 7.0f);
  float level;
  switch (set_.bright) {
    case 1: level = 0.4f; break;
    case 2: level = 0.7f; break;
    case 3: level = 1.0f; break;
    default: level = night ? 0.35f : (hour >= 0 && (hour < 8.5f || hour >= 20.5f) ? 0.7f : 1.0f); break;
  }
  if (b.mode() == Mode::Asleep) level = night ? 0.06f : 0.18f;  // always-on, but only a glow
  else if (b.mode() == Mode::Drowsy) level *= 0.6f;
  if (view_ == View::Keyboard || view_ == View::Dial) level = fmaxf(level, 0.6f);  // typing needs light
  if (view_ == View::Ringing || claude_.prompt) level = 1.0f;
  return level;
}

Rect Os::takeDirty() {
  RectList l;
  takeDirty(l);
  return l.bounds();
}

void Os::takeDirty(RectList& out) {
  out = dirty_;
  if (dirtyAll_) {
    out.clear();
    out.add(Rect{0, 0, g_.w, g_.h});
  }
  dirtyAll_ = false;
  dirty_.clear();
}

// ------------------------------------------------------------ persistence ---

size_t Os::saveSettings(uint8_t* buf, size_t cap) const {
  if (cap < sizeof(OsSettings)) return 0;
  memcpy(buf, &set_, sizeof(OsSettings));
  return sizeof(OsSettings);
}

bool Os::loadSettings(const uint8_t* buf, size_t n) {
  if (n != sizeof(OsSettings) || buf[0] != OsSettings::kVersion) return false;
  OsSettings s;
  memcpy(&s, buf, sizeof s);
  s.name[sizeof s.name - 1] = 0;
  if (s.lang > 1 || s.bright > 3 || s.ai > 3) return false;
  set_ = s;
  return true;
}

// notes: one per line, "<epoch>\t<text>" (tabs and newlines in the text become spaces)
std::string Os::saveNotes() const {
  std::string s;
  for (const Note& n : notes_) {
    s += std::to_string(n.t) + "\t";
    for (char c : n.text) s += (c == '\n' || c == '\t' || c == '\r') ? ' ' : c;
    s += '\n';
  }
  return s;
}

void Os::loadNotes(const std::string& s) {
  notes_.clear();
  size_t i = 0;
  while (i < s.size() && notes_.size() < 24) {
    size_t e = s.find('\n', i);
    if (e == std::string::npos) e = s.size();
    const size_t tab = s.find('\t', i);
    if (tab != std::string::npos && tab < e) {
      Note n;
      n.t = (uint32_t)strtoul(s.substr(i, tab - i).c_str(), nullptr, 10);
      n.text = s.substr(tab + 1, e - tab - 1);
      if (n.text.size() > 1200) n.text.resize(1200);
      if (!n.text.empty()) notes_.push_back(n);
    }
    i = e + 1;
  }
}

std::string Os::saveReminders() const {
  std::string s;
  for (const Reminder& r : rems_) {
    s += std::to_string(r.when) + "\t";
    for (char c : r.text) s += (c == '\n' || c == '\t') ? ' ' : c;
    s += '\n';
  }
  return s;
}

void Os::loadReminders(const std::string& s) {
  rems_.clear();
  size_t i = 0;
  while (i < s.size() && rems_.size() < 24) {
    size_t e = s.find('\n', i);
    if (e == std::string::npos) e = s.size();
    const size_t tab = s.find('\t', i);
    if (tab != std::string::npos && tab < e) {
      Reminder r;
      r.when = (uint32_t)strtoul(s.substr(i, tab - i).c_str(), nullptr, 10);
      r.text = s.substr(tab + 1, e - tab - 1);
      if (r.when) rems_.push_back(r);
    }
    i = e + 1;
  }
}


// ------------------------------------------------------------ SOUL Cloud ---

bool Os::needsSetup() const {
  switch (aiMode()) {
    case AiMode::Claude: return !net_.keyClaude || !net_.configured;
    case AiMode::ChatGpt: return !net_.keyOpenai || !net_.configured;
    case AiMode::Cloud: return !net_.relay || !net_.configured;
    case AiMode::Bridge: return !net_.configured;
    default: return false;
  }
}

static uint32_t textHash(const std::string& s) { return hashStr(s.c_str()); }

void Os::showCard(const std::string& title, const std::string& body, const std::string& src) {
  AiReply r;
  r.say = body;
  showAnswer(r, AiErr::None, src.c_str());
  cardTitle_ = title;
  answerFor_ = 8.0f + (float)body.size() * 0.035f;  // a card stays longer: it is read, not heard
  if (answerFor_ > 24) answerFor_ = 24;
}

// "Claude", "ChatGPT", "App", "Shortcut" (+ " · Ana"): the source badge of §6.7 rule 1
std::string Os::cloudSource(const CloudPush& p) const {
  std::string s;
  if (p.source == "connector") s = p.app == "chatgpt" ? "ChatGPT" : p.app == "claude" ? "Claude" : tr("An app", "O aplicație");
  else if (p.source == "shortcut") s = tr("Shortcut", "Scurtătură");
  else if (p.source == "app") s = tr("Account page", "Pagina contului");
  else return "SOUL Cloud";
  if (!p.by.empty()) s += " · " + p.by;
  return s;
}

// store one validated action from SOUL Cloud (dedupe by item id; refs kept for item.delete)
bool Os::applyCloudAct(const CloudPush& p, std::string& err) {
  if (!p.itemId.empty())
    for (const CloudRef& r : refs_)
      if (r.id == p.itemId) return true;  // a replay: already here
  const AiAction& a = p.act;
  CloudRef ref;
  ref.id = p.itemId;
  if (a.type == AiAction::AlarmSet && alarms_ && alarms_->count() >= Alarms::kMax) {
    err = "full";
    return false;
  }
  if (a.type == AiAction::ReminderCreate && (p.missed || (now_ && a.when <= now_))) {
    // too late to ring: say it once, keep nothing
    toast(tr("Missed: ", "Ratat: ") + a.text, kAmber, 6.0f);
    face_.react(X_sad, 1.2f);
    return true;
  }
  std::vector<std::string> chips;
  applyingCloud_ = true;
  runActions(std::vector<AiAction>(1, a), &chips);
  applyingCloud_ = false;
  switch (a.type) {
    case AiAction::AlarmSet:
      ref.kind = 0;
      ref.k1 = (uint32_t)a.hour << 16 | (uint32_t)a.minute << 8 | a.days;
      {
        Alarm tmp;  // hash the label as stored (cut to 48 bytes)
        tmp.setLabel((a.text.empty() ? tr("Alarm", "Alarmă") : a.text).c_str());
        ref.k2 = textHash(tmp.label);
      }
      break;
    case AiAction::ReminderCreate:
      ref.kind = 1;
      ref.k1 = a.when;
      ref.k2 = textHash(a.text.empty() ? tr("Reminder", "Memento") : a.text);
      break;
    case AiAction::NoteCreate:
      ref.kind = 2;
      ref.k1 = now_;
      ref.k2 = textHash(a.text);
      break;
    default: ref.id.clear(); break;  // timers and focus are not kept
  }
  if (!ref.id.empty()) {
    refs_.push_back(ref);
    if (refs_.size() > 48) refs_.erase(refs_.begin());
    pushCmd(OsCmd::SaveCloudRefs);
  }
  const std::string chip = chips.empty() ? std::string() : chips[0];
  if (thinking_ && p.source == "turn") {  // part of the answer being written: shown with it
    turnChips_.push_back(chip);
    return true;
  }
  const int hour = now_ ? localclock::hour(now_) : 12;
  if (!(hour >= 22 || hour < 7)) brainEvents_.push_back(Ev::AlarmDue);  // wakes the face (not at night)
  face_.react(X_surprised, 0.9f);  // surprised -> happy (docs/07 §4.3)
  reactAfter_ = X_happy;
  reactAfterT_ = 0.9f;
  face_.flash(kMint, 1.2f);
  const std::string from = p.source == "turn" || p.source == "device" ? std::string() : cloudSource(p) + ": ";
  toast(p.say.empty() ? from + chip : p.say, kMint, 4.0f);
  return true;
}

void Os::answerAccept(bool ok) {
  if (!acceptMode_) return;
  acceptMode_ = false;
  CloudOut o;
  o.kind = CloudOut::State;
  o.itemId = pendingAccept_.itemId;
  o.state = ok ? "accepted" : "rejected";
  if (ok) {
    CloudPush p = pendingAccept_;
    p.needsAccept = false;
    std::string err;
    if (!applyCloudAct(p, err)) {
      o.state = "rejected";
      toast(tr("No room for it", "Nu mai e loc"), kAmber);
    }
  } else {
    toast(tr("Not set", "Nu am setat"), kAmber);
  }
  if (!o.itemId.empty()) outs_.push_back(o);
  pendingAccept_ = CloudPush();
  cardTitle_.clear();
  go(answerReturn_ == View::Answer ? View::Home : answerReturn_);
}

bool Os::cloudPush(const CloudPush& p, std::string& err) {
  const std::string src = cloudSource(p);
  switch (p.kind) {
    case CloudPush::Act: {
      if (p.needsAccept && (p.source == "connector" || p.source == "shortcut")) {
        // §6.7 rule 3: stored as pending, armed only after a tap ("Claude wants to set 03:00")
        if (!p.itemId.empty())
          for (const CloudRef& r : refs_)
            if (r.id == p.itemId) return true;
        if (acceptMode_ && pendingAccept_.itemId == p.itemId) return true;
        if (acceptMode_) answerAccept(false);  // one question at a time: the older one is not armed
        pendingAccept_ = p;
        char hm[8];
        snprintf(hm, sizeof hm, "%02u:%02u", p.act.hour, p.act.minute);
        AiReply r;
        r.say = p.act.text;
        showAnswer(r, AiErr::None, src.c_str());
        cardTitle_ = src + tr(" wants to set ", " vrea să pună ") + hm;
        acceptMode_ = true;
        answerFor_ = 3600.0f;
        face_.react(X_surprised, 1.0f);
        brainEvents_.push_back(Ev::AlarmDue);
        invalidate();
        return true;
      }
      return applyCloudAct(p, err);
    }
    case CloudPush::Card:
      if (thinking_ && p.source == "turn") {
        turnChips_.push_back(p.title.empty() ? tr("Card", "Card") : p.title);
        return true;
      }
      if (acceptMode_) return true;  // the question on screen stays; the card was stored (acked) anyway
      if (!(now_ && (localclock::hour(now_) >= 22 || localclock::hour(now_) < 7))) brainEvents_.push_back(Ev::AlarmDue);
      face_.react(X_surprised, 0.9f);
      reactAfter_ = X_happy;
      reactAfterT_ = 0.9f;
      if (p.priv) {  // §6.7 rule 4: the title only, until a tap
        showCard(p.title.empty() ? tr("Private", "Privat") : p.title, std::string(), src);
        privateBody_ = p.body.empty() ? p.say : p.body;
        cardHidden_ = !privateBody_.empty();
      } else {
        showCard(p.title, p.body.empty() ? p.say : p.body, src);
      }
      return true;
    case CloudPush::Delete: {
      for (size_t i = 0; i < refs_.size(); ++i) {
        const CloudRef r = refs_[i];
        if (r.id != p.itemId) continue;
        refs_.erase(refs_.begin() + (long)i);
        pushCmd(OsCmd::SaveCloudRefs);
        if (r.kind == 0 && alarms_) {
          for (int k = 0; k < alarms_->count(); ++k) {
            const Alarm& al = alarms_->at(k);
            if (((uint32_t)al.hour << 16 | (uint32_t)al.minute << 8 | al.days) == r.k1 && textHash(al.label) == r.k2) {
              alarms_->remove(k);
              pushCmd(OsCmd::SaveAlarms);
              break;
            }
          }
        } else if (r.kind == 1) {
          for (size_t k = 0; k < rems_.size(); ++k)
            if (rems_[k].when == r.k1 && textHash(rems_[k].text) == r.k2) {
              rems_.erase(rems_.begin() + (long)k);
              pushCmd(OsCmd::SaveReminders);
              break;
            }
        } else if (r.kind == 2) {
          for (size_t k = 0; k < notes_.size(); ++k)
            if (textHash(notes_[k].text) == r.k2) {
              notes_.erase(notes_.begin() + (long)k);
              pushCmd(OsCmd::SaveNotes);
              break;
            }
        }
        invalidate();
        return true;
      }
      if (acceptMode_ && pendingAccept_.itemId == p.itemId) {  // withdrawn before the tap
        acceptMode_ = false;
        pendingAccept_ = CloudPush();
        back();
      }
      return true;  // already gone: deleting is idempotent
    }
    case CloudPush::Nav: {  // "take me to …": Maps opens on the route (or asks for it once SOUL knows where it is)
      apps_.dest = p.title;
      apps_.routeMode = p.say.empty() ? "walk" : p.say;
      if (view_ == View::Keyboard) kb_.cancel();
      apps_.preview = apps_.navOn = false;  // the new destination replaces any route on screen
      apps_.nav.stop();
      apps_.navAsked = -100;
      go(View::Maps);
      if (!p.body.empty()) fetch(Fetch::RouteGet, "/v1/device/maps/route");
      face_.react(X_excited, 1.0f);
      brainEvents_.push_back(Ev::AlarmDue);
      toast(cloudSource(p) + ": " + p.title, kMint, 3.5f);
      return true;
    }
    case CloudPush::Unsupported: err = "unsupported"; return false;
    default: err = "invalid"; return false;
  }
}

void Os::cloudConfig(const std::string& brain, const std::string& lang, const std::string& name) {
  bool changed = false;
  if (!brain.empty()) {
    const AiMode m = brain == "none" ? AiMode::None : aiModeFrom(brain.c_str());
    if ((brain == "none" || m != AiMode::None) && m != aiMode()) {
      set_.ai = (uint8_t)m;
      history_.clear();
      changed = true;
    }
  }
  if (lang == "ro" || lang == "en") {
    const uint8_t l = lang == "ro" ? 1 : 0;
    if (l != set_.lang) {
      set_.lang = l;
      changed = true;
    }
  }
  if (!name.empty() && name != set_.name) {
    snprintf(set_.name, sizeof set_.name, "%s", name.c_str());
    changed = true;
  }
  if (!changed) return;
  pushCmd(OsCmd::SaveSettings);
  toast(tr("Settings updated from your account", "Setări schimbate din cont"), kMint, 3.0f);
  invalidate();
}

// "kind\tk1\tk2\tid" per line
std::string Os::saveCloudRefs() const {
  std::string s;
  for (const CloudRef& r : refs_) {
    char b[48];
    snprintf(b, sizeof b, "%u\t%lu\t%lu\t", (unsigned)r.kind, (unsigned long)r.k1, (unsigned long)r.k2);
    s += b;
    for (char c : r.id) s += (c == '\n' || c == '\t') ? '_' : c;
    s += '\n';
  }
  return s;
}

void Os::loadCloudRefs(const std::string& s) {
  refs_.clear();
  size_t i = 0;
  while (i < s.size() && refs_.size() < 48) {
    size_t e = s.find('\n', i);
    if (e == std::string::npos) e = s.size();
    const std::string line = s.substr(i, e - i);
    unsigned kind = 0;
    unsigned long k1 = 0, k2 = 0;
    int used = 0;
    if (sscanf(line.c_str(), "%u\t%lu\t%lu\t%n", &kind, &k1, &k2, &used) == 3 && used > 0 && kind <= 2 &&
        (size_t)used < line.size()) {
      CloudRef r;
      r.kind = (uint8_t)kind;
      r.k1 = (uint32_t)k1;
      r.k2 = (uint32_t)k2;
      r.id = line.substr((size_t)used, 64);
      refs_.push_back(r);
    }
    i = e + 1;
  }
}

}  // namespace suflet
