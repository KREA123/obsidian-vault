#include "bridge_lan.h"

#include <Arduino.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_http_server.h>
#include <esp_random.h>
#include <freertos/semphr.h>
#include <lwip/sockets.h>

#include "BridgeLink.h"
#include "board.h"

using namespace suflet;

namespace {

constexpr uint16_t kPort = 8765;
constexpr size_t kMaxFrame = 16384;

SemaphoreHandle_t mtx = nullptr;
struct Lock {
  Lock() { xSemaphoreTake(mtx, portMAX_DELAY); }
  ~Lock() { xSemaphoreGive(mtx); }
};

BridgeServer srv;
httpd_handle_t httpd = nullptr;
std::string host;  // soul-xxxx (mDNS)
bool mdnsUp = false;

// localNow (RTC wall time counted as UTC) -> "YYYY-MM-DDTHH:MM"
std::string stamp(uint32_t t) {
  const time_t tt = (time_t)t;
  struct tm tm;
  gmtime_r(&tt, &tm);
  char b[48];
  snprintf(b, sizeof b, "%04d-%02d-%02dT%02d:%02d", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min);
  return b;
}

void saveTokensLocked() {
  if (!srv.tokensDirty) return;
  Preferences p;
  p.begin("soulbridge", false);
  p.putString("tok", srv.saveTokens().c_str());
  p.end();
  soulFlashWritten();
  srv.tokensDirty = false;
}

struct Work {
  int fd;
  std::string frame;
  bool close;
};

void sendWork(void* arg) {  // on the httpd task (httpd_queue_work): the only place frames are written
  Work* w = (Work*)arg;
  if (w->close) {
    httpd_sess_trigger_close(httpd, w->fd);
  } else {
    httpd_ws_frame_t f = {};
    f.final = true;
    f.type = HTTPD_WS_TYPE_TEXT;
    f.payload = (uint8_t*)w->frame.data();
    f.len = w->frame.size();
    httpd_ws_send_frame_async(httpd, w->fd, &f);
  }
  delete w;
}

void flushLocked() {
  BridgeOut o;
  while (srv.nextOut(o)) {
    if (!httpd) continue;
    Work* w = new Work{o.conn, o.frame, o.close};
    if (httpd_queue_work(httpd, sendWork, w) != ESP_OK) delete w;
  }
}

esp_err_t onWs(httpd_req_t* req) {
  const int fd = httpd_req_to_sockfd(req);
  if (req->method == HTTP_GET) {  // the handshake is done: a new connection
    Lock l;
    srv.onOpen(fd, millis());
    flushLocked();
    return ESP_OK;
  }
  httpd_ws_frame_t f = {};
  f.type = HTTPD_WS_TYPE_TEXT;
  esp_err_t e = httpd_ws_recv_frame(req, &f, 0);  // the length first
  if (e != ESP_OK) return e;
  if (f.type != HTTPD_WS_TYPE_TEXT || f.len == 0 || f.len > kMaxFrame) return ESP_OK;  // ignore (binary, empty, huge)
  std::string buf(f.len, '\0');
  f.payload = (uint8_t*)&buf[0];
  e = httpd_ws_recv_frame(req, &f, f.len);
  if (e != ESP_OK) return e;
  Lock l;
  srv.onText(fd, buf.data(), buf.size(), millis());
  saveTokensLocked();
  flushLocked();
  return ESP_OK;
}

void onClose(httpd_handle_t, int fd) {
  {
    Lock l;
    srv.onClose(fd);
  }
  close(fd);
}

void start() {
  httpd_config_t c = HTTPD_DEFAULT_CONFIG();
  c.server_port = kPort;
  c.ctrl_port = kPort + 1;
  c.max_open_sockets = 4;
  c.lru_purge_enable = true;
  c.close_fn = onClose;
  c.stack_size = 6144;
  c.core_id = 0;
  if (httpd_start(&httpd, &c) != ESP_OK) {
    httpd = nullptr;
    Serial.println("[bridge] could not listen on :8765");
    return;
  }
  httpd_uri_t u = {};
  u.uri = "/bridge";
  u.method = HTTP_GET;
  u.handler = onWs;
  u.is_websocket = true;
  httpd_register_uri_handler(httpd, &u);
  if (!mdnsUp && MDNS.begin(host.c_str())) {  // soul-xxxx.local
    MDNS.addService("soul", "tcp", kPort);
    mdnsUp = true;
  }
  Serial.printf("[bridge] listening: ws://%s.local:%u/bridge\n", host.c_str(), (unsigned)kPort);
}

void stop() {
  if (!httpd) return;
  httpd_stop(httpd);
  httpd = nullptr;
  Serial.println("[bridge] stopped");
}

}  // namespace

void bridgeLanBegin(const std::string& deviceId, const char* hostName) {
  mtx = xSemaphoreCreateMutex();
  host = hostName;
  srv.deviceId = deviceId;
  srv.rng = []() { return (uint32_t)esp_random(); };  // tokens and codes from the hardware RNG
  Preferences p;
  p.begin("soulbridge", true);
  srv.loadTokens(p.getString("tok", "").c_str());
  p.end();
}

void bridgeLanTick(bool on, const std::string& name, bool ro, const std::string& posixTz) {
  if (!mtx) return;
  const bool want = on && WiFi.status() == WL_CONNECTED;
  if (want && !httpd) start();
  if (!want && httpd) stop();
  Lock l;
  srv.name = name;
  srv.lang = ro ? "ro" : "en";
  srv.tz = posixTz;
  srv.tick(millis());
  flushLocked();
}

void bridgeLanNewCode() {
  if (!mtx) return;
  Lock l;
  srv.newCode(millis());
}

void bridgeLanForget() {
  if (!mtx) return;
  Lock l;
  srv.forget();
  saveTokensLocked();
  flushLocked();
}

void bridgeLanFill(NetInfo& n) {
  if (!mtx) return;
  Lock l;
  n.bridgeLan = httpd != nullptr;
  if (srv.online()) {
    n.bridgeOnline = true;
    n.bridgeName = srv.computer();
    n.askState = srv.askState();
  }
  n.bridgePaired = n.bridgePaired || srv.tokenCount() > 0;
  const std::string code = srv.code(millis());
  if (!code.empty()) {
    n.bridgeCode = code;
    n.bridgeCmd = "soul-bridge pair " + code;
  }
}

bool bridgeLanOnline() {
  if (!mtx) return false;
  Lock l;
  return srv.online();
}

bool bridgeLanAsk(const AiJob& job, bool ro, uint32_t localNow) {
  if (!mtx) return false;
  Lock l;
  const bool ok = srv.ask(job.text, ro, stamp(localNow), millis());
  flushLocked();
  return ok;
}

bool bridgeLanPollAnswer(AiOutcome& out) {
  if (!mtx) return false;
  Lock l;
  const bool r = srv.pollAnswer(out);
  flushLocked();
  return r;
}
