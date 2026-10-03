// SoulOS on the device: the screens and flows of the web SoulOS v4
// (os/index.html, os/SPEC.md, os/UX-REVIEW.md), for the round 480 px glass.
//
//   first boot   birth (the chip id types out, the eyes open) -> name -> brain
//                (SOUL Cloud / your Claude or OpenAI key / no AI) -> "hold the glass"
//                (SOUL Cloud shows its pairing code + QR first, docs/07 §2.2)
//   home         the face. tap = boop, 2x = laugh, hold = talk (or approve a
//                Claude request), stroke = purr, swipe <-/-> = the orbit of
//                apps, swipe up = Today
//   apps         Talk, Alarms, Timer, Notes, Today, Claude (+ "Ask my Claude"),
//                Settings (+ AI, pairing, Wi-Fi with a join QR, My SOUL)
//   back         swipe down (or ->) and the side button: always up one level
//
// The eyes are the UI: every state is said by the eyes first (SoulFace), then
// by a few words. Hardware-free and transport-free: the device (src/main.cpp)
// and the simulator feed it touches, the clock, Wi-Fi / Claude / battery
// state and AI answers, and service what it asks for (AI jobs, saving,
// starting the Wi-Fi setup portal...).
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

#include "AiProtocol.h"
#include "Alarms.h"
#include "CloudLink.h"
#include "Brain.h"
#include "Canvas.h"
#include "Events.h"
#include "EyeTables.h"
#include "Geometry.h"
#include "Keyboard.h"
#include "SoulFace.h"
#include "TimePicker.h"

namespace suflet {

enum class View : uint8_t {
  Boot,      // first boot, steps in bootStep()
  Home,
  Launcher,  // the orbit of apps
  Today,
  Talk,
  Answer,
  Alarms,
  Dial,      // the Rim-Dial time picker for a new alarm
  Ringing,
  Timer,
  Notes,
  NoteView,
  Claude,
  Settings,
  AiMode,
  Wifi,
  MySoul,
  About,
  Pair,      // SOUL Cloud: the XXXX-XXXX code + QR, "Pair with Ana?" ✓ / ✗, then "paired with <owner>"
  Keyboard,  // the system keyboard (over any screen)
  Count
};
const char* viewName(View v);

enum class BootStep : uint8_t { Birth, Name, Brain, Hold, Done };

// What the OS asks the device to do.
enum class OsCmd : uint8_t {
  None,
  SaveSettings,
  SaveAlarms,
  SaveNotes,
  SaveReminders,
  StartPortal,  // Wi-Fi + AI setup on a phone: SoftAP + captive page
  StopPortal,
  ForgetWifi,
  SetKey,       // pendingKey() for aiMode(): typed on the round keyboard
  ForgetKeys,
  ClaudeApprove,
  ClaudeDeny,
  VoiceStart,   // start recording (the glass is held, a mic is fitted)
  VoiceStop,    // stop and transcribe; the text comes back via voiceText()
  Restart,
  FactoryReset,
  SaveCloudRefs,  // saveCloudRefs(): which cloud item ids made which local items
  Count
};

struct OsSettings {  // persisted as a versioned blob
  static constexpr uint8_t kVersion = 3;
  uint8_t version = kVersion;
  char name[17] = "SOUL";
  uint8_t lang = 0;       // 0 English, 1 Romanian
  uint8_t bright = 0;     // 0 auto (time of day), 1 low, 2 mid, 3 high
  uint8_t ai = 0;         // AiMode
  uint8_t booted = 0;     // first boot done
  uint8_t largeText = 0;
  uint8_t debug = 0;      // fps / CPU overlay
  uint8_t nightOff = 1;   // at night, asleep for long: screen off (deep sleep if docked)
  uint32_t born = 0;      // local epoch of the first boot with a clock
};

struct NetInfo {
  bool configured = false;  // an SSID is stored
  bool connected = false;
  bool connecting = false;
  bool portal = false;      // the setup access point is up
  std::string ssid, ip, apName = "SOUL-SETUP", apPass, portalUrl = "http://192.168.4.1";
  int rssi = 0;
  bool keyClaude = false, keyOpenai = false, relay = false;  // what is configured (never the secrets)
  std::string maskClaude, maskOpenai;
  // SOUL Cloud (relay = its address is set): the account link, never the token
  bool cloudOnline = false;  // the socket is up and the cloud said welcome
  bool paired = false;
  bool cloudUpdate = false;  // the cloud wants a newer SOUL (close 4426)
  bool cloudRefused = false; // the cloud refused this SOUL's identity (see cloudProblem)
  int cloudProblem = 0;      // 0 none, 1 can't sign in, 2 not registered, 3 belongs to another account
  std::string owner, pairCode, pairUrl;  // pairCode: 8 Crockford characters, shown XXXX-XXXX
  std::string confirmPid, confirmName, confirmHint;  // a pair.confirm waiting for a touch
  bool connectorsPaused = false;
  int trialLeft = -1, inboxPending = 0;
};

struct ClaudeInfo {
  bool linked = false, busy = false, prompt = false, secure = false;
  std::string tool, hint, msg, bleName;
  uint32_t passkey = 0, approvals = 0, denials = 0, tokensToday = 0;
};

struct PowerInfo {
  int batPct = -1;
  bool charging = false;
};

struct BirthInfo {
  int design = 0;
  std::string chip;  // "A1:B2:C3:D4:E5:F6"
  uint32_t seed = 7;
};

struct Note {
  std::string text;
  uint32_t t = 0;
};

// Something made on SOUL that SOUL Cloud should know about (item.add), or a
// question left for the owner's own Claude (inbox.add, "Ask my Claude").
// Also what only a touch on SOUL may send: the pairing answer and the pause
// switch for connectors (docs/07 §6.16: never from the cloud, BLE or an LLM).
struct CloudOut {
  enum Kind : uint8_t { Item, Inbox, State, PairOk, PairNo, Connectors } kind = Item;
  AiAction act;
  std::string text;        // Inbox
  uint32_t created = 0;    // Item: local epoch
  std::string itemId;      // State: the cloud's item id
  std::string state;       // State: rang | dismissed | done | deleted | accepted | rejected ...
  std::string pid;         // PairOk / PairNo
  bool paused = false;     // Connectors
};

struct Reminder {
  uint32_t when = 0;  // local epoch
  std::string text;
};

struct AiJob {
  std::string text;
  AiContext ctx;
  std::vector<ChatTurn> history;
};

class Os {
 public:
  explicit Os(Alarms* alarms) : alarms_(alarms) {}
  void begin(const DisplayGeometry& g, const BirthInfo& birth);

  // ---- inputs -----------------------------------------------------------
  void touch(const TouchEv& e);  // raw touches (TouchMode::Text)
  void button(bool down);        // the side button (BOOT): press = back, hold 1.5 s = home
  void motion(Ev e);             // PickUp, Shake, FaceDown, FaceUp... and TapTap / NodYes / NodNo
  // One IMU sample (device frame, accel in g, gyro in rad/s) for the eyes'
  // motion behaviours; their gestures come back through motion(Ev).
  void imu(float dt, const eyes::ImuSample& s) { face_.imu(dt, s); }
  void setClock(uint32_t localNow) { now_ = localNow; }
  void setNet(const NetInfo& n);
  void setClaude(const ClaudeInfo& c);
  void setPower(const PowerInfo& p) { power_ = p; }
  void setVoiceAvailable(bool v) { voice_ = v; }
  void aiResult(const AiOutcome& o);
  // SOUL Cloud pushed something (docs/07 §2.6): apply it once. false + err
  // for the ack (ok:false). Replays (an item id seen before) are ok, not re-applied.
  bool cloudPush(const CloudPush& p, std::string& err);
  // the account page changed a setting ("config")
  void cloudConfig(const std::string& brain, const std::string& lang, const std::string& name);
  void voiceText(const std::string& text, AiErr err);  // a transcription (voice builds)
  void alarmDue(int index);      // an alarm rings now
  void update(float dt, Brain& brain);

  // ---- outputs ----------------------------------------------------------
  bool popAiJob(AiJob& j);
  bool popCmd(OsCmd& c);
  bool popCloudOut(CloudOut& o);
  const std::string& pendingKey() const { return pendingKey_; }
  void clearPendingKey();
  FaceInputs faceInputs(const Brain& b) const;
  SoulFace& face() { return face_; }
  // Draw the UI layer (below the eyes) under the canvas clip.
  void render(Canvas& cv);
  // The part of the UI that changed since the last call (redraw + push it).
  Rect takeDirty();
  bool wantsTextTouch() const { return true; }
  float fpsHint(const Brain& b) const;
  float backlight(float hour, const Brain& b) const;  // 0..1
  bool ringing() const { return view_ == View::Ringing || timerRinging_; }
  bool silenceRequested() { bool r = silence_; silence_ = false; return r; }

  // ---- state (also for tests, the simulator and persistence) ------------
  View view() const { return view_; }
  BootStep bootStep() const { return bootStep_; }
  OsSettings& settings() { return set_; }
  const OsSettings& settings() const { return set_; }
  AiMode aiMode() const { return (AiMode)set_.ai; }
  bool ro() const { return set_.lang == 1; }
  std::vector<Note>& notes() { return notes_; }
  std::vector<Reminder>& reminders() { return rems_; }
  Keyboard& keyboard() { return kb_; }
  TimePicker& picker() { return tp_; }
  const AiReply& lastReply() const { return reply_; }
  AiErr lastError() const { return lastErr_; }
  bool thinking() const { return thinking_; }
  int timerLeft() const;  // seconds, -1 = none
  void go(View v);
  void back();
  void home();
  void openKeyboard(int ctx, const std::string& initial = "");
  void ask(const std::string& text);  // typed or spoken, the same path
  void runActions(const std::vector<AiAction>& acts, std::vector<std::string>* chips);
  void startTimer(int seconds, bool focus);
  void stopTimer();
  void restartBoot();
  void toast(const std::string& text, Rgb color, float seconds = 2.4f);
  int launcherIndex() const { return orbit_; }
  static int appCount();
  static View appView(int i);

  // persistence (the device stores these blobs in NVS)
  size_t saveSettings(uint8_t* buf, size_t cap) const;
  bool loadSettings(const uint8_t* buf, size_t n);
  std::string saveNotes() const;  // compact text format, see Os.cpp
  void loadNotes(const std::string& s);
  std::string saveReminders() const;
  void loadReminders(const std::string& s);
  std::string saveCloudRefs() const;
  void loadCloudRefs(const std::string& s);

  // debug overlay (filled by the device)
  struct Perf {
    float fps = 0, frameMs = 0, renderMs = 0, pushMs = 0, cpu = 0;
    uint32_t heapKb = 0, psramKb = 0;
  } perf;

 private:
  struct Item {
    int id = 0;
    float x = 0, y = 0, w = 0, h = 0;  // centre + hit box, design px
    std::string label;
    Rgb color;
    uint8_t font = 0;  // 0 small, 1 text, 2 large
    bool underline = false;
    float alpha = 1;
  };
  enum : int { kNone = -1 };
  void buildItems(std::vector<Item>& out) const;
  int hitItem(float x, float y) const;
  void onTap(float x, float y);
  void onDoubleTap(float x, float y);
  void onHoldStart(float x, float y);
  void onHoldEnd();
  void onSwipe(int dir);  // 0 left, 1 right, 2 up, 3 down
  void activate(int id);
  void kbCommit(const std::string& text);
  void showAnswer(const AiReply& r, AiErr err, const char* src);
  AiContext context() const;
  void invalidate() { dirtyAll_ = true; }
  void invalidate(const Rect& r) { dirty_.add(r); }
  void setDirtyFromKeyboard();
  void pushCmd(OsCmd c);
  void bootNext();
  void bootPrev();
  void addAlarm(int h, int m, uint8_t days, const std::string& label);
  void addNote(const std::string& text);
  void addReminder(int h, int m, bool tomorrow, const std::string& text);
  void addReminderAt(uint32_t when, const std::string& text);
  void outItem(const AiAction& a);
  void showCard(const std::string& title, const std::string& body, const std::string& src);
  bool needsSetup() const;  // the chosen brain lacks Wi-Fi / a key / a cloud address
  void tickTimer(float dt);
  void tickReminders();
  std::string tr(const char* en, const char* ro) const { return set_.lang == 1 ? ro : en; }
  std::string hhmm(int h, int m) const;
  std::string nextAlarmText() const;

  // drawing (OsDraw.cpp)
  void drawItems(Canvas& cv, const std::vector<Item>& items);
  void drawBoot(Canvas& cv);
  void drawHome(Canvas& cv);
  void drawLauncher(Canvas& cv);
  void drawToday(Canvas& cv);
  void drawTalk(Canvas& cv);
  void drawAnswer(Canvas& cv);
  void drawAlarms(Canvas& cv);
  void drawRinging(Canvas& cv);
  void drawTimer(Canvas& cv);
  void drawNotes(Canvas& cv);
  void drawNoteView(Canvas& cv);
  void drawClaude(Canvas& cv);
  void drawSettings(Canvas& cv);
  void drawAiMode(Canvas& cv);
  void drawWifi(Canvas& cv);
  void drawMySoul(Canvas& cv);
  void drawAbout(Canvas& cv);
  void drawPair(Canvas& cv);
  void drawQr(Canvas& cv, const std::string& text, float cx, float cy, float maxPx);
  void drawToast(Canvas& cv);
  void drawPerf(Canvas& cv);
  void rimTop(Canvas& cv, const std::string& s, Rgb c, float alpha = 1);
  void rimBottom(Canvas& cv, const std::string& s, Rgb c, float alpha = 1);
  int wrapLines(const Font& f, const std::string& s, float maxW, std::string* lines, int maxLines) const;
  void textAt(Canvas& cv, const Font& f, float x, float y, const std::string& s, Rgb c, float alpha = 1,
              Align a = Align::Center);
  FaceLayoutT layoutFor(View v) const;

  Alarms* alarms_;
  DisplayGeometry g_;
  BirthInfo birth_;
  SoulFace face_{};
  Keyboard kb_;
  TimePicker tp_;
  OsSettings set_;
  NetInfo net_;
  bool netKnown_ = false;
  ClaudeInfo claude_;
  PowerInfo power_;
  View view_ = View::Home, kbReturn_ = View::Home, answerReturn_ = View::Home;
  BootStep bootStep_ = BootStep::Birth;
  int kbCtx_ = 0;
  uint32_t now_ = 0;
  float t_ = 0, viewT_ = 0, fade_ = 1;
  bool voice_ = false;

  // gestures
  bool down_ = false, holding_ = false, stroking_ = false, swallow_ = false;
  float dx0_ = 0, dy0_ = 0, dx_ = 0, dy_ = 0, downT_ = 0, lastTapT_ = -10, lastTapX_ = 0, lastTapY_ = 0;
  bool brainHold_ = false;
  int holdItem_ = -1;
  float holdItemT_ = 0;
  float lookUntil_ = 0, lookX_ = 0, lookY_ = 0;
  bool buttonDown_ = false;
  float buttonT_ = 0;

  // launcher
  int orbit_ = 0;
  float orbitDrag_ = 0;

  // pages
  int page_ = 0, noteSel_ = -1;

  // AI
  std::vector<AiJob> jobs_;
  std::vector<ChatTurn> history_;
  bool thinking_ = false;
  float thinkT_ = 0;
  AiReply reply_;
  AiErr lastErr_ = AiErr::None;
  std::vector<std::string> chips_;
  std::string answerSrc_;
  float answerT_ = 0, answerFor_ = 6.5f;
  bool listening_ = false, voiceWait_ = false;
  View voiceFrom_ = View::Home;
  std::string pendingKey_;

  // timer
  bool timerRun_ = false, timerPaused_ = false, timerRinging_ = false, timerFocus_ = false;
  float timerLeft_ = 0;
  int timerTotal_ = 0;
  int lastTimerSec_ = -1;

  // ringing
  int ringingAlarm_ = -1;
  bool silence_ = false;

  // data
  std::vector<Note> notes_;
  std::vector<Reminder> rems_;
  std::string reminderDue_;

  // SOUL Cloud
  struct CloudRef {
    std::string id;     // the cloud's item_id
    uint8_t kind = 0;   // 0 alarm, 1 reminder, 2 note
    uint32_t k1 = 0, k2 = 0;  // alarm h<<16|m<<8|days + label hash; reminder when + text hash; note t + text hash
  };
  std::vector<CloudRef> refs_;
  std::vector<CloudOut> outs_;
  bool applyingCloud_ = false;
  std::vector<std::string> turnChips_;  // pushes caused by the cloud turn being answered
  // a connector push that waits for a tap (needs_accept), a private card (title until a tap)
  bool acceptMode_ = false;
  CloudPush pendingAccept_;
  bool cardHidden_ = false;
  std::string privateBody_;
  bool applyCloudAct(const CloudPush& p, std::string& err);
  std::string cloudSource(const CloudPush& p) const;
  void answerAccept(bool ok);
  View pairReturn_ = View::Settings;
  bool pairedShown_ = false;
  float pairDoneT_ = -1;
  int reactAfter_ = -1;
  float reactAfterT_ = 0;
  std::string cardTitle_;

  // toast on the top rim
  std::string toast_;
  Rgb toastColor_;
  float toastLeft_ = 0;

  // output queues
  OsCmd cmds_[16] = {};
  int cmdHead_ = 0, cmdCount_ = 0;
  std::vector<Ev> brainEvents_;

  // dirty tracking
  bool dirtyAll_ = true;
  Rect dirty_;
  int lastMinute_ = -1;
  View drawnView_ = View::Count;
  mutable std::vector<Item> items_;  // scratch for hit-testing
};

}  // namespace suflet
