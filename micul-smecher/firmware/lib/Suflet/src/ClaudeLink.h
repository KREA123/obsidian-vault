// "Works with Claude": the Hardware Buddy protocol that Claude for macOS /
// Windows speaks over BLE (Nordic UART Service, one JSON object per line).
// Spec: https://github.com/anthropics/claude-desktop-buddy/blob/main/REFERENCE.md
//
// This class is transport-free: the device feeds it the bytes it receives
// and sends back the lines it produces. It turns Claude's session state
// into Events for the Brain (busy, needs approval, level up...), and the
// user's gesture into a permission decision.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>

#include "Events.h"

namespace suflet {

struct DeviceStatus {  // what we report in the Hardware Buddy stats panel
  bool secure = false;
  int batPct = -1;  // -1 = unknown
  int batMv = 0;
  bool usb = false;
  uint32_t uptimeS = 0;
  uint32_t heap = 0;
  uint32_t naps = 0;
};

class ClaudeLink {
 public:
  static constexpr uint32_t kTokensPerLevel = 50000;

  void feed(const uint8_t* data, size_t n);  // bytes from the BLE RX characteristic
  void tick(float dt);                       // call every frame (link timeout, clock)
  void setTransportConnected(bool up);       // BLE connect / disconnect
  bool poll(Ev& e) { return q_.pop(e); }
  bool popOutgoing(std::string& line);  // newline-terminated JSON to notify on TX

  // The user's decision on the pending permission prompt.
  bool decide(bool approve);

  // ---- state for the UI ------------------------------------------------
  bool alive() const { return alive_; }
  bool busy() const { return running_ > 0; }
  bool hasPrompt() const { return !promptId_.empty(); }
  const std::string& promptTool() const { return promptTool_; }
  const std::string& promptHint() const { return promptHint_; }
  const std::string& msg() const { return msg_; }
  const std::string& owner() const { return owner_; }
  const std::string& deviceName() const { return name_; }
  uint32_t tokensToday() const { return tokensToday_; }
  uint32_t level() const { return (uint32_t)(tokens_ / kTokensPerLevel); }
  bool timeValid() const { return timeValid_; }
  int64_t epochNow() const { return epoch_ + (int64_t)clock_; }
  int32_t tzOffset() const { return tz_; }
  float localHour() const;  // -1 if unknown
  bool unpairRequested() {  // the device must erase its BLE bonds
    const bool r = unpair_;
    unpair_ = false;
    return r;
  }
  uint32_t approvals() const { return approvals_; }
  uint32_t denials() const { return denials_; }

  DeviceStatus status;
  void setName(const std::string& n) { name_ = n; }

 private:
  void handleLine(const char* line, size_t n);
  void pushOut(const std::string& s);
  void ack(const char* cmd, bool ok, uint32_t n = 0, const char* error = nullptr);

  EvQueue<12> q_;
  std::string rx_;
  std::string out_[8];
  int outHead_ = 0, outCount_ = 0;

  bool transport_ = false, alive_ = false;
  float sinceSnapshot_ = 1e9f, clock_ = 0, promptAge_ = 0;
  int total_ = 0, running_ = 0, waiting_ = 0;
  uint64_t tokens_ = 0;
  uint32_t tokensToday_ = 0;
  bool haveTokens_ = false;
  std::string msg_, owner_, name_ = "Claude-Suflet";
  std::string promptId_, promptTool_, promptHint_;
  bool timeValid_ = false;
  int64_t epoch_ = 0;
  int32_t tz_ = 0;
  bool unpair_ = false;
  uint32_t approvals_ = 0, denials_ = 0;
};

}  // namespace suflet
