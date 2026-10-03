// The simulator's SOUL Cloud transport: the device's own CloudDriver /
// CloudSession / CloudLink / DeviceKey code over a small host HTTP + WebSocket
// client (POSIX sockets, OpenSSL for SHA-1 and P-256). Plain http:// / ws://
// to a loopback test cloud only (127.0.0.1 / localhost): the device itself
// speaks TLS with certificate checks (src/cloud.cpp) and never plain text.
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

#include "CloudSession.h"

class HostCloud : public suflet::CloudDriver {
 public:
  HostCloud();
  ~HostCloud() override;
  // the device key: kept (hex, mode 0600) in `path` so a re-run is the same SOUL; "" = a fresh one each run
  bool loadOrMakeKey(const std::string& path);
  std::string pub() const;
  bool verbose = true;
  int framesIn = 0, framesOut = 0;
  std::vector<std::string> recorded;  // every text frame received (for --record)

  int httpPost(const std::string& url, const std::string& body, std::string& resp, int& retryAfterS) override;
  bool supportsPoll() override { return true; }
  int httpGetAuth(const std::string& url, const std::string& bearer, std::string& resp, uint32_t timeoutMs) override;
  int httpPostAuth(const std::string& url, const std::string& bearer, const std::string& body, std::string& resp,
                   uint32_t timeoutMs) override;
  bool noWs = false;  // pretend the socket cannot open (the long-poll fallback)
  int wsOpen(const std::string& url, const std::string& bearer) override;
  bool wsSend(const std::string& text) override;
  Rd wsRead(std::string& text, int& closeCode, uint32_t waitMs) override;
  void wsClose() override;
  void wsPing() override;
  bool keyReady() override { return keyOk_; }
  std::string pubB64() override;
  std::string signB64(const std::string& msg) override;
  void log(const char* line) override;

 private:
  bool sendFrame(uint8_t opcode, const std::string& payload);
  int request(const char* method, const std::string& url, const std::string& bearer, const std::string& body,
              std::string& resp, int& retryAfterS, uint32_t timeoutMs);
  bool fill(size_t want, int waitMs);
  int fd_ = -1;
  std::string rx_;
  uint8_t priv_[32] = {0}, pub_[65] = {0};
  bool keyOk_ = false;
};
