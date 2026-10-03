// SOUL Bridge on the home network (docs/08-OWN-CLAUDE.md §4, LAN transport): SOUL is the WebSocket server
// (ws://soul-xxxx.local:8765/bridge, mDNS), SOUL Bridge on the owner's computer is the client, and the owner's
// own Claude Code (signed in by the owner, on that computer) answers the questions typed on SOUL.
// Transport-free: the device (src/bridge_lan.cpp, esp_http_server) and the simulator feed it connections and
// text frames and send what nextOut() gives them.
//
//   pairing  a 6-digit code on SOUL's screen, valid 120 s, 5 tries; the bridge sends bridge.pair {code}, SOUL
//            answers bridge.paired {token: "sbt_...", device_id, name} and keeps only SHA-256(token) (<= 3)
//   hello    the first frame of every other connection: bridge.hello {token} -> bridge.welcome / bridge.denied;
//            one active bridge (the newest wins), anything else within 10 s closes the connection
//   turns    ask {id, text, lang, now, tz, from} -> ask.ack (thinking) -> answer {text, actions} or
//            answer.error {code}; 125 s at most; actions validated with SOUL's own push rules (CloudLink)
//
// Nothing here is a Claude credential: the token is SOUL's own, issued at pairing, and lets one computer
// hand answers to this SOUL, nothing more.
#pragma once
#include <stdint.h>

#include <deque>
#include <functional>
#include <string>
#include <vector>

#include "AiProtocol.h"

namespace suflet {

struct BridgeOut {
  int conn = -1;
  std::string frame;  // "" with close = true: just close
  bool close = false;
};

class BridgeServer {
 public:
  std::string deviceId, name = "SOUL", lang = "en", tz;
  std::function<uint32_t()> rng;  // esp_random on the device: tokens and codes

  // ---- persisted: the hashes of the issued tokens (NVS) ---------------------------------------
  std::string saveTokens() const;  // one hex hash per line
  void loadTokens(const std::string& s);
  bool tokensDirty = false;
  size_t tokenCount() const { return hashes_.size(); }

  // ---- pairing ---------------------------------------------------------------------------------
  std::string newCode(uint32_t nowMs);  // 6 digits, 120 s, 5 tries
  std::string code(uint32_t nowMs) const;  // "" when none is valid
  void forget();  // every paired computer: its token dies, a connected one is closed

  // ---- the transport ---------------------------------------------------------------------------
  void onOpen(int conn, uint32_t nowMs);
  void onClose(int conn);
  void onText(int conn, const char* s, size_t n, uint32_t nowMs);
  bool nextOut(BridgeOut& o);
  void tick(uint32_t nowMs);

  // ---- turns -----------------------------------------------------------------------------------
  bool online() const { return active_ >= 0; }
  const std::string& computer() const { return computer_; }  // what the bridge calls itself
  // false when no bridge is connected or a turn is running. nowLocal "YYYY-MM-DDTHH:MM"
  bool ask(const std::string& text, bool ro, const std::string& nowLocal, uint32_t nowMs, const std::string& memory = "");
  bool askPending() const { return !askId_.empty(); }
  int askState() const { return askState_; }  // 0 none, 1 waiting, 2 thinking
  bool pollAnswer(AiOutcome& out);

  static constexpr uint32_t kCodeMs = 120000, kFirstFrameMs = 10000, kAnswerMs = 125000;
  static constexpr size_t kMaxFrame = 16384, kMaxTokens = 3, kMaxConns = 4;

 private:
  struct Conn {
    int id = -1;
    uint32_t openedAt = 0;
    bool hello = false;
  };
  void send(int conn, const std::string& f) { out_.push_back({conn, f, false}); }
  void close(int conn) { out_.push_back({conn, std::string(), true}); }
  void deny(int conn, const char* reason);
  void finish(AiErr err);
  uint32_t rand32();
  std::string randomToken();

  std::vector<std::string> hashes_;
  std::vector<Conn> conns_;
  std::deque<BridgeOut> out_;
  int active_ = -1;
  std::string computer_;
  std::string code_;
  uint32_t codeUntil_ = 0;
  int codeTries_ = 0;
  std::string askId_;
  uint32_t askAt_ = 0, askSeq_ = 0;
  int askState_ = 0;
  bool ready_ = false;
  AiOutcome answer_;
  uint32_t rngState_ = 0x2545F491u;
};

}  // namespace suflet
