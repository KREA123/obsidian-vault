// The simulator's side of SOUL Bridge on the home network (docs/08 §4): a tiny WebSocket server on 127.0.0.1
// (POSIX sockets, OpenSSL SHA-1 for the handshake) carrying lib/Suflet's BridgeServer, like the device's
// esp_http_server does (src/bridge_lan.cpp). Loopback only: a test server, never on a real network.
#pragma once
#include <stdint.h>

#include <functional>
#include <string>
#include <vector>

class HostWsServer {
 public:
  ~HostWsServer();
  bool listen(int port);  // 0 = any free port
  int port() const { return port_; }
  // one round: accept, read whatever arrived (onOpen after the handshake, onText per text frame, onClose)
  void poll(int waitMs, const std::function<void(int)>& onOpen,
            const std::function<void(int, const std::string&)>& onText, const std::function<void(int)>& onClose);
  bool send(int conn, const std::string& text);
  void close(int conn);

 private:
  struct Client {
    int fd = -1;
    bool ws = false;
    std::string rx;
  };
  void drop(size_t i, const std::function<void(int)>& onClose);
  int fd_ = -1, port_ = 0;
  std::vector<Client> clients_;
};
