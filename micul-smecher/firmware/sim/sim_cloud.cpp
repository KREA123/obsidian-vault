#include "sim_cloud.h"

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#include <chrono>
#include <cstdio>
#include <cstring>

#include "CloudLink.h"
#include "DeviceKey.h"

using namespace suflet;

namespace {

uint32_t msNow() {
  using namespace std::chrono;
  return (uint32_t)duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

// "http://127.0.0.1:8790/x" -> host, port, path. Loopback only: this is a test client.
bool splitUrl(const std::string& url, std::string& host, int& port, std::string& path) {
  size_t p = url.find("://");
  if (p == std::string::npos) return false;
  const std::string scheme = url.substr(0, p);
  if (scheme != "http" && scheme != "ws") return false;
  std::string rest = url.substr(p + 3);
  const size_t slash = rest.find('/');
  path = slash == std::string::npos ? "/" : rest.substr(slash);
  const std::string hp = rest.substr(0, slash);
  const size_t colon = hp.rfind(':');
  host = colon == std::string::npos ? hp : hp.substr(0, colon);
  port = colon == std::string::npos ? 80 : atoi(hp.c_str() + colon + 1);
  return (host == "127.0.0.1" || host == "localhost") && port > 0 && port < 65536;
}

int dial(const std::string& host, int port) {
  const int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) return -1;
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_port = htons((uint16_t)port);
  a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  (void)host;
  if (connect(fd, (sockaddr*)&a, sizeof a) != 0) {
    close(fd);
    return -1;
  }
  int one = 1;
  setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
  return fd;
}

bool writeAll(int fd, const char* d, size_t n) {
  while (n) {
    const ssize_t w = send(fd, d, n, MSG_NOSIGNAL);
    if (w <= 0) return false;
    d += w;
    n -= (size_t)w;
  }
  return true;
}

std::string b64(const uint8_t* d, size_t n) {  // standard base64 with padding (Sec-WebSocket-Key / Accept)
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

std::string lower(std::string s) {
  for (char& c : s) c = (char)tolower((unsigned char)c);
  return s;
}

// the value of header `name` (lowercase) in a raw HTTP head, or ""
std::string header(const std::string& head, const char* name) {
  const std::string l = lower(head);
  const std::string n = std::string("\r\n") + name + ":";
  const size_t p = l.find(n);
  if (p == std::string::npos) return "";
  size_t s = p + n.size();
  while (s < head.size() && head[s] == ' ') ++s;
  const size_t e = head.find("\r\n", s);
  return head.substr(s, e == std::string::npos ? std::string::npos : e - s);
}

}  // namespace

HostCloud::HostCloud() = default;
HostCloud::~HostCloud() {
  wsClose();
  DeviceKey::wipe(priv_, sizeof priv_);
}

bool HostCloud::loadOrMakeKey(const std::string& path) {
  if (!path.empty()) {
    if (FILE* f = fopen(path.c_str(), "rb")) {
      char hex[65] = {0};
      const size_t n = fread(hex, 1, 64, f);
      fclose(f);
      if (n == 64) {
        for (int i = 0; i < 32; ++i) {
          char b[3] = {hex[2 * i], hex[2 * i + 1], 0};
          priv_[i] = (uint8_t)strtoul(b, nullptr, 16);
        }
        keyOk_ = DeviceKey::publicFrom(priv_, pub_);
        if (keyOk_) return true;
      }
    }
  }
  keyOk_ = DeviceKey::generate(priv_, pub_);
  if (keyOk_ && !path.empty()) {
    const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd >= 0) {
      char hex[65];
      for (int i = 0; i < 32; ++i) snprintf(hex + 2 * i, 3, "%02x", priv_[i]);
      (void)!write(fd, hex, 64);
      close(fd);
    }
  }
  return keyOk_;
}

std::string HostCloud::pub() const { return DeviceKey::pubB64(pub_); }
std::string HostCloud::pubB64() { return DeviceKey::pubB64(pub_); }
std::string HostCloud::signB64(const std::string& msg) { return DeviceKey::signB64(priv_, msg); }

void HostCloud::log(const char* line) {
  if (verbose) fprintf(stderr, "%s\n", line);
}

// ------------------------------------------------------------------ HTTP ---

int HostCloud::httpPost(const std::string& url, const std::string& body, std::string& resp, int& retryAfterS) {
  return request("POST", url, std::string(), body, resp, retryAfterS, 15000);
}

int HostCloud::httpGetAuth(const std::string& url, const std::string& bearer, std::string& resp, uint32_t timeoutMs) {
  int ra = -1;
  return request("GET", url, bearer, std::string(), resp, ra, timeoutMs);
}

int HostCloud::httpPostAuth(const std::string& url, const std::string& bearer, const std::string& body, std::string& resp,
                            uint32_t timeoutMs) {
  int ra = -1;
  return request("POST", url, bearer, body, resp, ra, timeoutMs);
}

int HostCloud::request(const char* method, const std::string& url, const std::string& bearer, const std::string& body,
                       std::string& resp, int& retryAfterS, uint32_t timeoutMs) {
  std::string host, path;
  int port = 0;
  retryAfterS = -1;
  resp.clear();
  if (!splitUrl(url, host, port, path)) return -1;
  const int fd = dial(host, port);
  if (fd < 0) return -1;
  std::string head = std::string(method) + " " + path + " HTTP/1.1\r\nHost: " + host + ":" + std::to_string(port) +
                     "\r\nUser-Agent: SOUL-sim/" + fw + "\r\nConnection: close\r\n";
  if (!bearer.empty()) head += "Authorization: " + bearer + "\r\n";  // never in the URL
  if (strcmp(method, "GET") != 0)
    head += "Content-Type: application/json\r\nContent-Length: " + std::to_string(body.size()) + "\r\n";
  head += "\r\n";
  int status = -1;
  if (writeAll(fd, head.data(), head.size()) && writeAll(fd, body.data(), body.size())) {
    std::string in;
    char buf[4096];
    const uint32_t t0 = msNow();
    for (;;) {
      pollfd p{fd, POLLIN, 0};
      const int left = (int)timeoutMs - (int)(msNow() - t0);
      if (left <= 0 || poll(&p, 1, left) <= 0) break;
      const ssize_t r = recv(fd, buf, sizeof buf, 0);
      if (r <= 0) break;
      in.append(buf, (size_t)r);
      if (in.size() > 65536) break;
    }
    const size_t eoh = in.find("\r\n\r\n");
    if (in.compare(0, 9, "HTTP/1.1 ") == 0 && eoh != std::string::npos) {
      status = atoi(in.c_str() + 9);
      const std::string h = in.substr(0, eoh + 2);
      const std::string ra = header(h, "retry-after");
      if (!ra.empty()) retryAfterS = atoi(ra.c_str());
      resp = in.substr(eoh + 4);
      if (lower(header(h, "transfer-encoding")) == "chunked") {  // uvicorn answers with Content-Length; just in case
        std::string out;
        size_t i = 0;
        while (i < resp.size()) {
          const size_t e = resp.find("\r\n", i);
          if (e == std::string::npos) break;
          const size_t n = strtoul(resp.c_str() + i, nullptr, 16);
          if (!n) break;
          out += resp.substr(e + 2, n);
          i = e + 2 + n + 2;
        }
        resp = out;
      }
    }
  }
  close(fd);
  return status;
}

// ------------------------------------------------------------- WebSocket ---

int HostCloud::wsOpen(const std::string& url, const std::string& bearer) {
  if (noWs) return -1;  // SIM_NO_WS=1: a network that drops WebSocket upgrades (long-poll then)
  std::string host, path;
  int port = 0;
  if (!splitUrl(url, host, port, path)) return -1;
  fd_ = dial(host, port);
  if (fd_ < 0) return -1;
  uint8_t nonce[16];
  RAND_bytes(nonce, sizeof nonce);
  const std::string key = b64(nonce, sizeof nonce);
  const std::string req = "GET " + path + " HTTP/1.1\r\nHost: " + host + ":" + std::to_string(port) +
                          "\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
                          "\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: soul.v1\r\nAuthorization: " + bearer +
                          "\r\nUser-Agent: SOUL-sim/" + fw + "\r\n\r\n";
  if (!writeAll(fd_, req.data(), req.size())) {
    wsClose();
    return -1;
  }
  rx_.clear();
  const uint32_t t0 = msNow();
  size_t eoh;
  while ((eoh = rx_.find("\r\n\r\n")) == std::string::npos) {
    if (msNow() - t0 > 10000 || !fill(rx_.size() + 1, 1000)) {
      wsClose();
      return -1;
    }
  }
  const std::string head = rx_.substr(0, eoh + 2);
  rx_.erase(0, eoh + 4);
  const int status = head.compare(0, 9, "HTTP/1.1 ") == 0 ? atoi(head.c_str() + 9) : -1;
  if (status != 101) {
    wsClose();
    return status > 0 ? status : -1;
  }
  // RFC 6455: Accept = base64(SHA-1(key + GUID)); and the server must pick soul.v1 (§6.4)
  const std::string g = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
  uint8_t sha[SHA_DIGEST_LENGTH];
  SHA1((const unsigned char*)g.data(), g.size(), sha);
  if (header(head, "sec-websocket-accept") != b64(sha, sizeof sha) || header(head, "sec-websocket-protocol") != "soul.v1") {
    log("[sim] the server did not accept soul.v1 properly");
    wsClose();
    return -1;
  }
  return 0;
}

bool HostCloud::fill(size_t want, int waitMs) {
  char buf[8192];
  while (rx_.size() < want) {
    pollfd p{fd_, POLLIN, 0};
    const int r = poll(&p, 1, waitMs);
    if (r <= 0) return false;
    const ssize_t n = recv(fd_, buf, sizeof buf, 0);
    if (n <= 0) {
      return false;
    }
    rx_.append(buf, (size_t)n);
  }
  return true;
}

bool HostCloud::sendFrame(uint8_t opcode, const std::string& payload) {
  if (fd_ < 0) return false;
  std::string f;
  f += (char)(0x80 | opcode);
  const size_t n = payload.size();
  if (n < 126) {
    f += (char)(0x80 | n);
  } else if (n < 65536) {
    f += (char)(0x80 | 126);
    f += (char)(n >> 8);
    f += (char)(n & 0xff);
  } else {
    f += (char)(0x80 | 127);
    for (int i = 7; i >= 0; --i) f += (char)((uint64_t)n >> (8 * i) & 0xff);
  }
  uint8_t mask[4];
  RAND_bytes(mask, 4);  // a client masks every frame
  f.append((const char*)mask, 4);
  for (size_t i = 0; i < n; ++i) f += (char)(payload[i] ^ mask[i % 4]);
  return writeAll(fd_, f.data(), f.size());
}

bool HostCloud::wsSend(const std::string& text) {
  if (text.size() > CloudLink::kMaxOut) {
    log("[sim] frame over 10 KB not sent");
    return true;
  }
  ++framesOut;
  return sendFrame(0x1, text);
}

void HostCloud::wsPing() { sendFrame(0x9, "soul"); }

CloudDriver::Rd HostCloud::wsRead(std::string& text, int& closeCode, uint32_t waitMs) {
  if (fd_ < 0) {
    closeCode = 1006;
    return Rd::Closed;
  }
  std::string msg;
  for (;;) {
    if (rx_.size() < 2 && !fill(2, msg.empty() ? (int)waitMs : 5000)) {
      if (msg.empty() && rx_.empty()) {
        pollfd p{fd_, POLLIN, 0};  // nothing yet, or a closed peer?
        if (poll(&p, 1, 0) > 0) {
          char c;
          if (recv(fd_, &c, 1, MSG_PEEK) == 0) {
            closeCode = 1006;
            return Rd::Closed;
          }
        }
        return Rd::Nothing;
      }
      if (rx_.size() < 2) {
        closeCode = 1006;
        return Rd::Closed;
      }
    }
    const uint8_t b0 = (uint8_t)rx_[0], b1 = (uint8_t)rx_[1];
    size_t len = b1 & 0x7f, off = 2;
    if (len == 126) {
      if (!fill(4, 5000)) return closeCode = 1006, Rd::Closed;
      len = (size_t)(uint8_t)rx_[2] << 8 | (uint8_t)rx_[3];
      off = 4;
    } else if (len == 127) {
      if (!fill(10, 5000)) return closeCode = 1006, Rd::Closed;
      len = 0;
      for (int i = 0; i < 8; ++i) len = len << 8 | (uint8_t)rx_[2 + i];
      off = 10;
    }
    if (len > CloudLink::kMaxIn) {
      closeCode = 1009;
      return Rd::Closed;
    }
    if (!fill(off + len, 5000)) {
      closeCode = 1006;
      return Rd::Closed;
    }
    const std::string payload = rx_.substr(off, len);
    rx_.erase(0, off + len);
    const uint8_t op = b0 & 0x0f;
    const bool fin = b0 & 0x80;
    if (op == 0x9) {  // ping: pong with the same payload
      sendFrame(0xA, payload);
      return Rd::Control;
    }
    if (op == 0xA) return Rd::Control;
    if (op == 0x8) {
      closeCode = payload.size() >= 2 ? ((uint8_t)payload[0] << 8 | (uint8_t)payload[1]) : 1005;
      sendFrame(0x8, payload.substr(0, 2));
      return Rd::Closed;
    }
    if (op == 0x1 || op == 0x0) {
      msg += payload;
      if (!fin) continue;
      text.swap(msg);
      ++framesIn;
      recorded.push_back(text);
      return Rd::Text;
    }
    if (fin) return Rd::Control;  // binary: Phase 2 audio
  }
}

void HostCloud::wsClose() {
  if (fd_ >= 0) {
    close(fd_);
    fd_ = -1;
  }
  rx_.clear();
}
