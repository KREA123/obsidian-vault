// SOUL Cloud session: the device side of docs/07-CONNECT-AI.md §6 as a
// transport-free state machine (one per SOUL). The device (src/cloud.cpp) and
// the simulator (sim/sim_cloud.cpp) run the same code: they do the HTTPS and
// the WebSocket, CloudDriver sequences auth -> socket -> reconnect, and this
// class decides every frame.
//
//   socket     onOpen() -> hello; onText(frame); nextFrame() -> what to send now
//              (frame budget: 10 burst / welcome.limits.frames_per_s, acks apart);
//              onClose(code) -> when and how to come back (§6.4 close codes)
//   pushes     replays (seq <= the applied seq) are acked again, never re-applied;
//              unknown actions acked unsupported, bad ones invalid; connector and
//              shortcut pushes while connectors are paused acked "paused" (§6.7 rule 5);
//              the rest go to SoulOS, which applies them and calls ackPush()
//   outq       item.add / inbox.add / item.state, in order, only while paired; an
//              item.add / inbox.add leaves on `added` (or on an error that names its
//              cid: invalid, too_big); kept across reboots (NVS soulsync/outq, <= 8 KB)
//   turns      ask (25 s, then abort + timeout), conv kept 10 min, unsynced items in ctx; a turn handed to the
//              owner's computer (SOUL Bridge, brain "bridge", docs/08 §4) waits 125 s and reports
//              ask.state waiting -> thinking; bridge_offline / its timeout fall back to the offline rules
//   bridge     the one-time code for `soul-bridge pair`, the computer's presence (bridge.state)
//   long-poll  the same frames over GET /v1/device/poll + POST /v1/device/send when the socket cannot
//              open (CloudDriver switches by itself, §6.4), and the deep-sleep wake-polls of §6.11
//   pairing    the code + URL for the screen; pair.confirm waits for a touch
//              (pairAnswer), no touch within expires_in = pair.no
//   time zone  welcome / config posix_tz always win (hello.tz_posix is a hint)
//
// Thread-free: the device holds its mutex around every call.
#pragma once
#include <stdint.h>

#include <deque>
#include <functional>
#include <string>
#include <vector>

#include "CloudLink.h"
#include "Os.h"

namespace suflet {

class CloudSession {
 public:
  // ---- what this SOUL says about itself (set by the device) --------------
  CloudHello prefs;  // fw, hw, lang, brainLocal, power, tzPosix, caps (after = lastSeq)
  std::function<uint32_t()> rng;  // cids and ask ids (esp_random on the device)

  // ---- persisted (NVS soulsync) -------------------------------------------
  uint32_t lastSeq = 0;           // the highest applied push seq
  bool connectorsPaused = false;  // the owner's choice on SOUL wins over the cloud's echo
  bool seqSaveDue(uint32_t nowMs) const;  // every 10 pushes or 60 s (flash writes stall the panel)
  void seqSaved(uint32_t nowMs);
  std::string saveOutq() const;  // frames, one per line, newest kept within 8 KB
  void loadOutq(const std::string& s);
  bool outqDirty = false, pausedDirty = false;

  // ---- the socket -----------------------------------------------------------
  std::string onOpen(uint32_t nowMs);
  CloudLink::Msg onText(const char* s, size_t n, uint32_t nowMs);
  bool nextFrame(std::string& out, uint32_t nowMs);
  struct Retry {
    enum Kind : uint8_t { Reconnect, Reauth, Update } kind = Reconnect;
    uint32_t waitMs = 0;
  };
  Retry onClose(int code, uint32_t nowMs, float rnd);
  void tick(uint32_t nowMs);
  bool open() const { return open_; }
  bool welcomed() const { return welcomed_; }

  // ---- the app (SoulOS through the device) ------------------------------------
  // one text turn; false when the socket is not welcomed or a turn is running.
  // viaBridge: the cloud hands it to the owner's computer (125 s, ask.state)
  bool ask(const std::string& text, bool ro, int timerLeftMin, uint32_t nowMs, bool viaBridge = false);
  bool askPending() const { return askPending_; }
  int askState() const { return askState_; }  // 0 none, 1 waiting (sent to the computer), 2 thinking
  bool pollAnswer(AiOutcome& out);
  bool pollPush(CloudPush& p);
  void ackPush(uint32_t seq, bool ok, const char* err);
  // made on SOUL (item.add / inbox.add / item.state), a pairing answer or the pause toggle
  void send(const CloudOut& o, uint32_t localNow, uint32_t epochNow);
  bool pollConfig(CloudConfig& c);
  bool pollTz(std::string& posixTz);
  bool pollTime(uint32_t& epoch);  // server_time of the last welcome (set the clock if NTP has not)
  void setStatus(int rssi, int battery, const char* power, uint32_t freeHeap, bool awake);
  void sleep(uint32_t wakeAtEpoch);  // best effort, just before deep sleep (§6.11)
  void fill(NetInfo& n) const;  // what the screens show (never a token)
  // a deep-sleep wake-poll (§6.11): no socket and no hello, only pushes in and acks / outq / sleep out
  void beginWakePoll(uint32_t nowMs);
  void endWakePoll();
  bool wakePolling() const { return wake_; }
  uint32_t pollAfter() const { return seenSeq_ > lastSeq ? seenSeq_ : lastSeq; }  // paging while acks wait

  // state (also for tests)
  std::string state;  // "" (not known yet) | unpaired | paired | pending
  std::string owner, pairCode, pairUrl, conv;
  CloudConfirm confirm;  // pid != "" while a pair.confirm waits for a touch
  int trialLeft = -1, allowanceLeft = -1, inboxPending = 0;
  bool needUpdate = false;
  std::string quietFrom = "22:00", quietTo = "07:00";
  // SOUL Bridge through the cloud (docs/08 §4)
  std::string bridgeCode, bridgeCmd, bridgeName;
  bool bridgePaired = false, bridgeOnline = false;
  std::string brainWanted;  // the brain picked on SOUL ("bridge" / "none") until the cloud echoes it
  size_t outqSize() const { return outq_.size(); }
  size_t pushesWaiting() const { return pushes_.size(); }

 private:
  struct Out {
    std::string frame, cid;
    bool state = false;  // item.state: fire and forget
    bool sent = false;   // sent on this socket
  };
  struct Bucket {
    float tokens = 0, cap = 0, perS = 0;
    uint32_t at = 0;
    bool take(uint32_t nowMs);
  };
  void queue(const std::string& f) { ctl_.push_back(f); }
  void applied(uint32_t seq);
  void answerError(AiErr e, bool noLocal);
  void dropOut(const std::string& cid);
  void trimOutq();
  uint32_t rand32();
  std::vector<std::string> unsynced() const;

  CloudLink link_;
  bool open_ = false, welcomed_ = false, replayDone_ = false, wake_ = false;
  uint32_t seenSeq_ = 0, bridgeCodeUntil_ = 0;
  int askState_ = 0;
  bool askBridge_ = false;
  uint32_t openedAt_ = 0, helloAt_ = 0, statusAt_ = 0, confirmUntil_ = 0;
  int attempt_ = 0, waitMs_ = 0;
  std::deque<std::string> acks_, ctl_;
  std::deque<Out> outq_;
  std::deque<CloudPush> pushes_;
  std::vector<uint32_t> inFlight_;
  Bucket frames_, ackBudget_;
  uint32_t holdOutqUntil_ = 0;
  // the turn
  bool askPending_ = false, answerReady_ = false;
  std::string askId_;
  uint32_t askAt_ = 0, convAt_ = 0, askSeq_ = 0;
  AiOutcome answer_;
  // for the app
  bool configReady_ = false, tzReady_ = false, timeReady_ = false;
  CloudConfig config_;
  std::string tzNew_;
  uint32_t serverTime_ = 0;
  // status
  int rssi_ = 0, battery_ = -1;
  std::string power_ = "usb";
  uint32_t freeHeap_ = 0;
  bool awake_ = true, statusDirty_ = true;
  // seq persistence
  uint32_t sinceSave_ = 0, savedAtMs_ = 0;
  uint32_t rngState_ = 0x9e3779b9u;
};

// Auth -> socket -> reconnect, over a transport the device or the simulator
// provides. step() never blocks longer than the transport's own timeouts.
class CloudDriver {
 public:
  virtual ~CloudDriver() {}
  CloudSession session;
  std::string base;  // "https://host[:port]" (the simulator: "http://127.0.0.1:port")
  std::string deviceId, fw, hw;
  bool allowPlainWs = false;  // the simulator only

  // one turn of the loop; returns how long the caller may wait before the next
  uint32_t step(uint32_t nowMs, float rnd);
  enum class Problem : uint8_t { None, CannotSignIn, NotEnrolled, KeyRevoked };
  Problem problem = Problem::None;
  bool haveToken() const { return !token_.empty(); }
  bool connected() const { return connected_; }
  bool pollMode() const { return pollMode_; }  // long-poll is the transport (the socket would not open)
  void forgetToken();
  void reconnectNow();
  // §6.11 wake-poll, one shot from deep sleep: sign in, GET /v1/device/poll?wait=0 (all pages); the pushes
  // then wait in `session` for SoulOS; wakePollFinish() sends the acks, the queue and `sleep` in one POST.
  bool wakePoll(uint32_t nowMs, float rnd);
  bool wakePollFinish(uint32_t nowMs, uint32_t wakeAtEpoch);

 protected:
  // ---- the transport --------------------------------------------------------
  // POST a JSON body; returns the HTTP status (< 0: network). `retryAfterS` from the header (or -1).
  virtual int httpPost(const std::string& url, const std::string& body, std::string& resp, int& retryAfterS) = 0;
  // open the socket (Bearer + soul.v1): 0 = open, else the HTTP status of the refused upgrade or -1
  virtual int wsOpen(const std::string& url, const std::string& bearer) = 0;
  virtual bool wsSend(const std::string& text) = 0;
  enum class Rd : uint8_t { Nothing, Text, Control, Closed };
  // wait up to `waitMs` for one frame; pings are answered inside (Control)
  virtual Rd wsRead(std::string& text, int& closeCode, uint32_t waitMs) = 0;
  virtual void wsClose() = 0;
  virtual void wsPing() {}
  // ---- long-poll (optional: a transport without it never leaves the socket) -------------------------------
  virtual bool supportsPoll() { return false; }
  // GET / POST with "Authorization: Bearer ..."; the HTTP status, < 0 network
  virtual int httpGetAuth(const std::string& url, const std::string& bearer, std::string& resp, uint32_t timeoutMs) {
    (void)url, (void)bearer, (void)resp, (void)timeoutMs;
    return -1;
  }
  virtual int httpPostAuth(const std::string& url, const std::string& bearer, const std::string& body, std::string& resp,
                           uint32_t timeoutMs) {
    (void)url, (void)bearer, (void)body, (void)resp, (void)timeoutMs;
    return -1;
  }
  // ---- the key (never leaves the implementation) ------------------------------
  virtual bool keyReady() = 0;  // made / loaded (the device makes it once Wi-Fi is up)
  virtual std::string pubB64() = 0;
  virtual std::string signB64(const std::string& msg) = 0;
  virtual bool resetPending() { return false; }  // soulid/rst
  virtual void resetReported() {}
  virtual void lock() {}
  virtual void unlock() {}
  virtual void log(const char*) {}

 private:
  struct Guard {
    CloudDriver* d;
    explicit Guard(CloudDriver* x) : d(x) { d->lock(); }
    ~Guard() { d->unlock(); }
  };
  bool authenticate(uint32_t nowMs, float rnd);
  void closed(int code, uint32_t nowMs, float rnd);
  uint32_t stepPoll(uint32_t nowMs, float rnd);
  bool needToken(uint32_t nowMs) const;
  std::string bearer();
  bool feedMessages(const std::string& body, uint32_t nowMs, bool* more = nullptr);
  bool postFrames(std::vector<std::string>& frames, uint32_t nowMs);
  bool pollMode_ = false;
  uint32_t pollUntil_ = 0;
  std::vector<std::string> pollOut_;  // frames a failed send keeps for the next round
  std::string token_, wsUrl_;
  uint32_t tokenUntil_ = 0, retryAt_ = 0, lastRx_ = 0, lastPing_ = 0, helloAt_ = 0;
  bool connected_ = false, waiting_ = false, forceReauth_ = false;
  int authFails_ = 0, sockFails_ = 0, pollFails_ = 0;
  std::string lastAuthCode_;
};

}  // namespace suflet
