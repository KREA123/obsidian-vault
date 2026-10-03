#include "sim_lan.h"

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <openssl/sha.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstring>

namespace {

std::string b64(const uint8_t* d, size_t n) {
  static const char* k = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string o;
  for (size_t i = 0; i < n; i += 3) {
    const uint32_t v = (uint32_t)d[i] << 16 | (i + 1 < n ? (uint32_t)d[i + 1] << 8 : 0) | (i + 2 < n ? d[i + 2] : 0);
    o += k[(v >> 18) & 63];
    o += k[(v >> 12) & 63];
    o += i + 1 < n ? k[(v >> 6) & 63] : '=';
    o += i + 2 < n ? k[v & 63] : '=';
  }
  return o;
}

std::string header(const std::string& head, const char* name) {
  std::string l = head;
  for (char& c : l) c = (char)tolower((unsigned char)c);
  const std::string n = std::string("\r\n") + name + ":";
  const size_t p = l.find(n);
  if (p == std::string::npos) return "";
  size_t s = p + n.size();
  while (s < head.size() && head[s] == ' ') ++s;
  const size_t e = head.find("\r\n", s);
  return head.substr(s, e == std::string::npos ? std::string::npos : e - s);
}

bool writeAll(int fd, const char* d, size_t n) {
  while (n) {
    const ssize_t w = ::send(fd, d, n, MSG_NOSIGNAL);
    if (w <= 0) return false;
    d += w;
    n -= (size_t)w;
  }
  return true;
}

bool frame(int fd, uint8_t op, const std::string& p) {  // a server frame: never masked
  std::string f;
  f += (char)(0x80 | op);
  if (p.size() < 126) {
    f += (char)p.size();
  } else {
    f += (char)126;
    f += (char)(p.size() >> 8);
    f += (char)(p.size() & 0xff);
  }
  f += p;
  return writeAll(fd, f.data(), f.size());
}

}  // namespace

HostWsServer::~HostWsServer() {
  for (Client& c : clients_) ::close(c.fd);
  if (fd_ >= 0) ::close(fd_);
}

bool HostWsServer::listen(int port) {
  fd_ = socket(AF_INET, SOCK_STREAM, 0);
  if (fd_ < 0) return false;
  int one = 1;
  setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_port = htons((uint16_t)port);
  a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);  // loopback only
  if (bind(fd_, (sockaddr*)&a, sizeof a) != 0 || ::listen(fd_, 4) != 0) return false;
  socklen_t len = sizeof a;
  getsockname(fd_, (sockaddr*)&a, &len);
  port_ = ntohs(a.sin_port);
  fcntl(fd_, F_SETFL, fcntl(fd_, F_GETFL, 0) | O_NONBLOCK);
  return true;
}

void HostWsServer::drop(size_t i, const std::function<void(int)>& onClose) {
  const int fd = clients_[i].fd;
  const bool ws = clients_[i].ws;
  ::close(fd);
  clients_.erase(clients_.begin() + (long)i);
  if (ws) onClose(fd);
}

void HostWsServer::poll(int waitMs, const std::function<void(int)>& onOpen,
                        const std::function<void(int, const std::string&)>& onText,
                        const std::function<void(int)>& onClose) {
  std::vector<pollfd> p;
  p.push_back({fd_, POLLIN, 0});
  for (const Client& c : clients_) p.push_back({c.fd, POLLIN, 0});
  if (::poll(p.data(), p.size(), waitMs) <= 0) return;
  if (p[0].revents & POLLIN) {
    const int c = accept(fd_, nullptr, nullptr);
    if (c >= 0) clients_.push_back({c, false, std::string()});
  }
  for (size_t i = clients_.size(); i-- > 0;) {
    if (i + 1 >= p.size() || !(p[i + 1].revents & (POLLIN | POLLHUP | POLLERR))) continue;
    Client& c = clients_[i];
    char buf[4096];
    const ssize_t n = recv(c.fd, buf, sizeof buf, 0);
    if (n <= 0) {
      drop(i, onClose);
      continue;
    }
    c.rx.append(buf, (size_t)n);
    if (!c.ws) {  // the HTTP upgrade
      const size_t eoh = c.rx.find("\r\n\r\n");
      if (eoh == std::string::npos) continue;
      const std::string head = c.rx.substr(0, eoh + 2);
      c.rx.erase(0, eoh + 4);
      const std::string key = header(head, "sec-websocket-key");
      if (head.compare(0, 12, "GET /bridge ") != 0 || key.empty()) {
        static const char* const k404 = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n";
        writeAll(c.fd, k404, strlen(k404));
        drop(i, onClose);
        continue;
      }
      const std::string g = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
      uint8_t sha[SHA_DIGEST_LENGTH];
      SHA1((const unsigned char*)g.data(), g.size(), sha);
      const std::string r = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                            "Sec-WebSocket-Accept: " + b64(sha, sizeof sha) + "\r\n\r\n";
      writeAll(c.fd, r.data(), r.size());
      c.ws = true;
      onOpen(c.fd);
    }
    for (;;) {  // whole frames only (a client masks every frame)
      if (c.rx.size() < 2) break;
      const uint8_t b0 = (uint8_t)c.rx[0], b1 = (uint8_t)c.rx[1];
      size_t len = b1 & 0x7f, off = 2;
      if (len == 126) {
        if (c.rx.size() < 4) break;
        len = (size_t)(uint8_t)c.rx[2] << 8 | (uint8_t)c.rx[3];
        off = 4;
      } else if (len == 127) {
        drop(i, onClose);  // nothing that big here
        break;
      }
      const bool masked = b1 & 0x80;
      if (c.rx.size() < off + (masked ? 4 : 0) + len) break;
      std::string pl = c.rx.substr(off + (masked ? 4 : 0), len);
      if (masked)
        for (size_t k = 0; k < len; ++k) pl[k] ^= c.rx[off + (k % 4)];
      c.rx.erase(0, off + (masked ? 4 : 0) + len);
      const uint8_t op = b0 & 0x0f;
      if (op == 0x8) {  // close
        frame(c.fd, 0x8, pl.substr(0, 2));
        drop(i, onClose);
        break;
      }
      if (op == 0x9) frame(c.fd, 0xA, pl);
      if (op == 0x1) onText(c.fd, pl);
    }
  }
}

bool HostWsServer::send(int conn, const std::string& text) {
  for (const Client& c : clients_)
    if (c.fd == conn && c.ws) return frame(c.fd, 0x1, text);
  return false;
}

void HostWsServer::close(int conn) {
  for (const Client& c : clients_)
    if (c.fd == conn) {
      frame(c.fd, 0x8, std::string("\x03\xe8", 2));
      shutdown(c.fd, SHUT_WR);  // the peer closes; poll() then drops it
    }
}
