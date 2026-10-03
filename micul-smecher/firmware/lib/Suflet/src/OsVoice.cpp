// SoulOS on the device: offline voice commands and the offline personality lines (docs/10-SOUL-MEMORY.md
// §7-8). Os::voiceCommand runs what ESP-SR MultiNet recognised on the device (VoiceCommands.h), with no AI and
// no internet; Os::offlineChat answers small talk from Lines.h when there is no AI to ask.
//
// Safety: a spoken "yes" never approves a Claude permission request, a pairing or a connector's Accept
// (those stay a touch / hold on SOUL, docs/07 §6.16); a spoken "no" may decline them.
#include <stdio.h>
#include <time.h>

#include "Lines.h"
#include "Os.h"
#include "VoiceCommands.h"

namespace suflet {

using namespace eyes;

namespace {
const Rgb kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4), kCream = Rgb::hex(0xFFF0C8);
// Os.cpp's item ids on the Ringing screen (Snooze / Stop)
constexpr int kIdSnooze = 4, kIdStop = 5;
}  // namespace

bool Os::offlineChat(const std::string& text) {
  const bool offline = aiMode() == AiMode::None || !net_.connected || (aiMode() == AiMode::Bridge && !net_.bridgeOnline);
  if (!offline) return false;
  std::string say, face;
  uint32_t seed = now_ ^ (uint32_t)(t_ * 1000);
  for (char c : text) seed = seed * 31u + (uint8_t)c;
  if (!smallTalk(text, ro(), now_ ? (int)(now_ % 86400 / 3600) : -1, seed, say, face)) return false;
  AiReply r;
  r.say = say;
  r.face = face;
  showAnswer(r, AiErr::None, ro() ? "SOUL · pe device" : "SOUL · on the device");
  return true;
}

void Os::voiceCommand(int id) {
  const VoiceAction a = voiceAction(id);
  listening_ = false;
  voiceWait_ = false;
  if (a.kind == VoiceAction::None) return;
  chips_.clear();
  turnChips_.clear();
  cardTitle_.clear();
  const char* src = ro() ? "Voce · pe device" : "Voice · on the device";
  AiReply r;
  auto say = [&](const std::string& s) {
    r.say = s;
    showAnswer(r, AiErr::None, src);
  };
  switch (a.kind) {
    case VoiceAction::SayTime: {
      if (!now_) {
        say(tr("I don't know the time yet.", "Nu știu încă ora."));
        break;
      }
      say(tr("It's ", "E ora ") + hhmm((int)(now_ % 86400 / 3600), (int)(now_ % 3600 / 60)) + ".");
      break;
    }
    case VoiceAction::SayDate: {
      const std::string d = formatNow(now_, ro());
      say(now_ ? tr("Today is ", "Azi e ") + d.substr(0, d.rfind(',')) + "." : tr("I don't know the date yet.", "Nu știu încă data."));
      break;
    }
    case VoiceAction::OpenView:
      if ((View)a.arg == View::Dial) {
        go(View::Alarms);
        tp_.open(7, 0);
        go(View::Dial);
      } else if ((View)a.arg == View::Memory) {
        memoryOpen();
      } else {
        page_ = 0;
        go((View)a.arg);
      }
      face_.react(X_happy, 0.8f);
      break;
    case VoiceAction::AlarmAt:
      addAlarm(a.arg, 0, 0, tr("Alarm", "Alarmă"));
      chips_.push_back(tr("Alarm ", "Alarmă ") + hhmm(a.arg, 0));
      r.actions.resize(1);  // the approving face
      say(tr("Alarm set for ", "Alarmă pusă la ") + hhmm(a.arg, 0) + ".");
      break;
    case VoiceAction::StopRinging:
      if (view_ == View::Ringing) activate(kIdStop);
      else if (timerRinging_) stopTimer();
      else say(tr("Nothing is ringing.", "Nu sună nimic."));
      break;
    case VoiceAction::Snooze:
      if (view_ == View::Ringing) activate(kIdSnooze);
      else say(tr("Nothing to snooze.", "Nimic de amânat."));
      break;
    case VoiceAction::TimerStart:
    case VoiceAction::Focus:
      startTimer(a.arg * 60, a.kind == VoiceAction::Focus);
      chips_.push_back((a.kind == VoiceAction::Focus ? std::string("Focus ") : tr("Timer ", "Minutar ")) +
                       std::to_string(a.arg) + " min");
      r.actions.resize(1);
      say(a.kind == VoiceAction::Focus ? tr("Focus: 25 minutes. Go.", "Focus: 25 de minute. Start.")
                                       : tr("Timer: ", "Minutar: ") + std::to_string(a.arg) + tr(" min. Go.", " min. Start."));
      break;
    case VoiceAction::TimerStop:
      if (timerRun_ || timerRinging_) {
        stopTimer();
        toast(tr("Timer stopped", "Minutar oprit"), kAmber);
      } else {
        say(tr("No timer is running.", "Nu merge niciun minutar."));
      }
      break;
    case VoiceAction::TimerPause:
      if (timerRun_) {
        timerPaused_ = !timerPaused_;
        toast(timerPaused_ ? tr("Timer paused", "Minutar pe pauză") : tr("Timer running", "Minutar pornit"), kCream);
      }
      break;
    case VoiceAction::Note:
      go(View::Notes);
      openKeyboard(2 /* Os.cpp KbNote */);
      break;
    case VoiceAction::Volume: {  // the same volume as the Control dial (apps_.volume, 0..1)
      float& v = apps_.volume;
      v = a.arg == 0 ? 0.0f : a.arg > 0 ? (v + 0.2f > 1.0f ? 1.0f : v + 0.2f) : (v - 0.2f < 0.1f ? 0.1f : v - 0.2f);
      toast(v > 0 ? tr("Volume ", "Volum ") + std::to_string((int)(v * 100 + 0.5f)) + "%" : tr("Muted", "Fără sunet"), kCream);
      break;
    }
    case VoiceAction::Brightness: {
      const int b = set_.bright == 0 ? 2 : set_.bright;
      set_.bright = (uint8_t)(a.arg > 0 ? (b < 3 ? b + 1 : 3) : (b > 1 ? b - 1 : 1));
      pushCmd(OsCmd::SaveSettings);
      toast(a.arg > 0 ? tr("Brighter", "Mai luminos") : tr("Dimmer", "Mai întunecat"), kCream);
      break;
    }
    case VoiceAction::Sleep:
      go(View::Home);
      sleepReq_ = true;
      brainEvents_.push_back(Ev::FaceDown);  // the good-night reaction, then the eyes doze
      break;
    case VoiceAction::Wake:
      brainEvents_.push_back(Ev::PickUp);
      face_.react(X_wake);
      if (view_ != View::Home) go(View::Home);
      break;
    case VoiceAction::Answer:
      if (claude_.prompt) {
        if (a.arg) toast(tr("Hold the glass to approve", "Ține apăsat ca să aprobi"), kAmber, 3.0f);
        else pushCmd(OsCmd::ClaudeDeny);
      } else if (acceptMode_) {
        if (a.arg) toast(tr("Tap Accept to confirm", "Atinge Acceptă ca să confirmi"), kAmber, 3.0f);
        else answerAccept(false);
      } else {
        face_.react(a.arg ? X_happy : X_wink, 1.0f);
        toast(a.arg ? tr("Okay!", "Bine!") : tr("Okay, no.", "Bine, nu."), kMint, 1.6f);
      }
      break;
    case VoiceAction::Home: home(); break;
    case VoiceAction::Back: back(); break;
    case VoiceAction::Remember: {
      MemoryAnswer m;
      if (mem_ && memoryAct(*mem_, ro() ? "ce știi despre mine?" : "what do you know about me?", now_, ro(), false, m)) say(m.say);
      else say(tr("I don't remember anything yet.", "Încă nu țin minte nimic."));
      break;
    }
    case VoiceAction::Chat: {
      r.face = (LineTopic)a.arg == LineTopic::Joke ? "excited" : "happy";
      say(pickLine((LineTopic)a.arg, ro(), now_ ^ (uint32_t)(t_ * 997), now_ && (now_ % 86400 / 3600 >= 22 || now_ % 86400 / 3600 < 6) ? 2 : 1));
      break;
    }
    default: break;
  }
  invalidate();
}

}  // namespace suflet
