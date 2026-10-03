#include "cloud.h"

#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_crt_bundle.h>
#include <esp_heap_caps.h>
#include <bootloader_random.h>
#include <esp_random.h>
#include <esp_transport.h>
#include <esp_transport_ssl.h>
#include <esp_transport_ws.h>
#include <freertos/semphr.h>
#include <nvs_flash.h>
#include <time.h>

#include "CloudSession.h"
#include "DeviceKey.h"
#include "board.h"
#include "net.h"

using namespace suflet;

#ifndef SUFLET_CLOUD_BASE
#define SUFLET_CLOUD_BASE ""  // e.g. -DSUFLET_CLOUD_BASE=\"https://soul.example\"; dev builds: the portal can set it
#endif

namespace {

constexpr const char* kIdPart = "soulid";  // its own NVS partition: a factory reset never erases it (§6.1)
constexpr size_t kMaxMessage = 16384;      // server frames are <= 8 KB

SemaphoreHandle_t mtx = nullptr;
struct Lock {
  Lock() { xSemaphoreTake(mtx, portMAX_DELAY); }
  ~Lock() { xSemaphoreGive(mtx); }
};

void wipe(std::string& s) {
  for (char& c : s) c = 0;
  s.clear();
}

uint32_t epochNow() {
  const time_t t = time(nullptr);
  return t > 1700000000 ? (uint32_t)t : 0;  // 0 until NTP (or the cloud) set the clock
}

// ------------------------------------------------------------- the key ---

struct Key {
  uint8_t priv[32] = {0};
  uint8_t pub[65] = {0};
  bool ready = false;
  bool resetFlag = false;  // soulid/rst: a factory reset the cloud has not heard of

  void load() {
    Preferences p;
    if (!p.begin("soulid", true, kIdPart)) return;
    ready = p.getBytesLength("priv") == 32 && p.getBytesLength("pub") == 65 && p.getBytes("priv", priv, 32) == 32 &&
            p.getBytes("pub", pub, 65) == 65 && pub[0] == 0x04;
    resetFlag = p.getUChar("rst", 0) == 1;
    p.end();
  }
  // made once, after Wi-Fi is up (the RNG is a true RNG with the radio on) or on the factory station's
  // SOULKEY GEN (bootloader entropy source); never printed
  bool make(bool factory = false) {
    if (ready) return true;
    const bool radio = WiFi.status() == WL_CONNECTED;
    if (!radio && !factory) return false;
    if (!radio) bootloader_random_enable();
    const bool made = DeviceKey::generate(priv, pub);
    if (!radio) bootloader_random_disable();
    if (!made) return false;
    Preferences p;
    if (!p.begin("soulid", false, kIdPart)) return false;
    const bool ok = p.putBytes("priv", priv, 32) == 32 && p.putBytes("pub", pub, 65) == 65;
    p.end();
    soulFlashWritten();
    ready = ok;
    if (ok) Serial.println("[cloud] device key made (P-256)");
    return ok;
  }
  void setReset(bool v) {
    resetFlag = v;
    Preferences p;
    if (!p.begin("soulid", false, kIdPart)) return;
    p.putUChar("rst", v ? 1 : 0);
    p.end();
    soulFlashWritten();
  }
};

Key key;

// --------------------------------------------------------- the transport ---

class EspDriver : public CloudDriver {
 public:
  esp_transport_handle_t sslT = nullptr, wsT = nullptr;
  std::string ua;

  // (public: the task closes the socket itself when the cloud address changes)
  int httpPost(const std::string& url, const std::string& body, std::string& resp, int& retryAfterS) override {
    HttpRequest rq;
    rq.url = url;
    rq.headers = {{"content-type", "application/json"}};
    rq.body = body;
    rq.timeoutMs = 15000;
    AiErr err;
    const int st = netHttpsPost(rq, resp, err);
    wipe(rq.body);
    retryAfterS = -1;
    return st;
  }

  static bool parseWss(const std::string& url, std::string& host, int& port, std::string& path) {
    if (url.compare(0, 6, "wss://") != 0) return false;  // TLS only on the device
    const size_t slash = url.find('/', 6);
    const std::string hp = url.substr(6, slash == std::string::npos ? std::string::npos : slash - 6);
    path = slash == std::string::npos ? "/" : url.substr(slash);
    const size_t colon = hp.rfind(':');
    if (colon != std::string::npos && hp.find(']') == std::string::npos) {
      host = hp.substr(0, colon);
      port = atoi(hp.c_str() + colon + 1);
    } else {
      host = hp;
      port = 443;
    }
    return !host.empty() && port > 0 && port < 65536;
  }

  int wsOpen(const std::string& url, const std::string& bearer) override {
    std::string host, path;
    int port = 443;
    if (!parseWss(url, host, port, path)) return -1;
    sslT = esp_transport_ssl_init();
    if (!sslT) return -1;
    esp_transport_ssl_crt_bundle_attach(sslT, esp_crt_bundle_attach);  // verified TLS, never insecure
    wsT = esp_transport_ws_init(sslT);
    if (!wsT) {
      wsClose();
      return -1;
    }
    ua = "SOUL/" + fw;
    esp_transport_ws_config_t c = {};
    c.ws_path = path.c_str();
    c.sub_protocol = "soul.v1";
    c.user_agent = ua.c_str();
    c.auth = bearer.c_str();  // the token travels in the Authorization header, never in the URL
    c.propagate_control_frames = true;  // we see PING / CLOSE (close codes matter)
    esp_transport_ws_set_config(wsT, &c);
    if (esp_transport_connect(wsT, host.c_str(), port, 10000) < 0) {
      const int status = esp_transport_ws_get_upgrade_request_status(wsT);
      wsClose();
      return status > 0 ? status : -1;
    }
    return 0;
  }

  bool sendRaw(const std::string& s, ws_transport_opcodes_t op) {
    if (!wsT) return false;
    std::string copy = s;  // the ws layer masks the payload in place
    const int r = esp_transport_ws_send_raw(wsT, (ws_transport_opcodes_t)(op | WS_TRANSPORT_OPCODES_FIN),
                                            copy.empty() ? nullptr : &copy[0], (int)copy.size(), 5000);
    return r >= 0;
  }

  bool wsSend(const std::string& text) override {
    if (text.size() > CloudLink::kMaxOut) {  // never: the builders keep frames under 10 KB
      Serial.printf("[cloud] frame of %u B not sent\n", (unsigned)text.size());
      return true;
    }
    return sendRaw(text, WS_TRANSPORT_OPCODES_TEXT);
  }

  void wsPing() override { sendRaw(std::string(), WS_TRANSPORT_OPCODES_PING); }

  // long-poll (§6.4 fallback, §6.11 wake-polls): the same HTTPS client as /auth, Bearer in the header
  bool supportsPoll() override { return true; }
  int httpGetAuth(const std::string& url, const std::string& bearer, std::string& resp, uint32_t timeoutMs) override {
    HttpRequest rq;
    rq.url = url;
    rq.get = true;
    rq.headers = {{"authorization", bearer}};
    rq.timeoutMs = timeoutMs;
    AiErr err;
    const int st = netHttpsPost(rq, resp, err);
    wipe(rq.headers[0].second);
    return st;
  }
  int httpPostAuth(const std::string& url, const std::string& bearer, const std::string& body, std::string& resp,
                   uint32_t timeoutMs) override {
    HttpRequest rq;
    rq.url = url;
    rq.headers = {{"content-type", "application/json"}, {"authorization", bearer}};
    rq.body = body;
    rq.timeoutMs = timeoutMs;
    AiErr err;
    const int st = netHttpsPost(rq, resp, err);
    wipe(rq.headers[1].second);
    return st;
  }

  Rd wsRead(std::string& text, int& closeCode, uint32_t waitMs) override {
    if (!wsT) return Rd::Closed;
    const int p = esp_transport_poll_read(wsT, (int)waitMs);
    if (p < 0) {
      closeCode = 1006;
      return Rd::Closed;
    }
    if (p == 0) return Rd::Nothing;
    std::string msg;
    char buf[1024];
    for (;;) {
      int r = esp_transport_read(wsT, buf, sizeof buf, 2000);
      if (r < 0) {
        closeCode = 1006;
        return Rd::Closed;
      }
      const ws_transport_opcodes_t op = esp_transport_ws_get_read_opcode(wsT);
      if (op == WS_TRANSPORT_OPCODES_NONE) return msg.empty() ? Rd::Nothing : Rd::Control;
      const int len = esp_transport_ws_get_read_payload_len(wsT);
      if (len < 0 || (size_t)len > kMaxMessage) {
        closeCode = 1009;
        return Rd::Closed;
      }
      std::string payload(buf, (size_t)r);
      while ((int)payload.size() < len) {
        const size_t want = (size_t)len - payload.size();
        r = esp_transport_read(wsT, buf, want < sizeof buf ? (int)want : (int)sizeof buf, 5000);
        if (r <= 0) {
          closeCode = 1006;
          return Rd::Closed;
        }
        payload.append(buf, (size_t)r);
      }
      switch (op) {
        case WS_TRANSPORT_OPCODES_PING: sendRaw(payload, WS_TRANSPORT_OPCODES_PONG); return Rd::Control;
        case WS_TRANSPORT_OPCODES_PONG: return Rd::Control;
        case WS_TRANSPORT_OPCODES_CLOSE:
          closeCode = payload.size() >= 2 ? ((uint8_t)payload[0] << 8 | (uint8_t)payload[1]) : 1005;
          sendRaw(payload.substr(0, 2), WS_TRANSPORT_OPCODES_CLOSE);
          return Rd::Closed;
        case WS_TRANSPORT_OPCODES_TEXT:
        case WS_TRANSPORT_OPCODES_CONT:
          msg += payload;
          if (msg.size() > kMaxMessage) {
            closeCode = 1009;
            return Rd::Closed;
          }
          if (!esp_transport_ws_get_fin_flag(wsT)) continue;  // more fragments follow
          text.swap(msg);
          return Rd::Text;
        default:  // binary (Phase 2 audio): not spoken here
          if (!esp_transport_ws_get_fin_flag(wsT)) continue;
          return Rd::Control;
      }
    }
  }

  void wsClose() override {
    if (wsT) {
      esp_transport_close(wsT);
      esp_transport_destroy(wsT);
      wsT = nullptr;
    }
    if (sslT) {
      esp_transport_destroy(sslT);
      sslT = nullptr;
    }
  }

  bool keyReady() override { return key.ready || key.make(); }
  std::string pubB64() override { return DeviceKey::pubB64(key.pub); }
  std::string signB64(const std::string& msg) override { return DeviceKey::signB64(key.priv, msg); }
  bool resetPending() override { return key.resetFlag; }
  void resetReported() override { key.setReset(false); }
  void lock() override { xSemaphoreTake(mtx, portMAX_DELAY); }
  void unlock() override { xSemaphoreGive(mtx); }
  void log(const char* line) override { Serial.println(line); }
};

EspDriver drv;  // its session is shared with the render loop under `mtx`
bool off = true, baseChanged = false;
// §6.11: this boot is a timer wake from deep sleep: poll once, let SoulOS apply, report, sleep again
enum class Wake : uint8_t { None, Polling, Applying, Done } wake = Wake::None;
uint32_t wakeAtEpoch = 0, wakeStartMs = 0;
std::string savedOutq;
uint32_t savedSeq = 0;
bool savedConn = false;
// SoulOS apps (os/APPS.md): HTTPS calls to SOUL Cloud with the device token, one per loop turn, off the render loop
struct AppResult {
  suflet::Fetch kind;
  int status;
  std::string body;
};
std::vector<suflet::AppFetch> appQ;
std::vector<AppResult> appDone;

// ------------------------------------------------------------------ NVS ---

void loadSync() {
  Preferences p;
  p.begin("soulsync", true);
  drv.session.lastSeq = savedSeq = p.getUInt("seq", 0);
  savedOutq = p.getString("outq", "").c_str();
  drv.session.connectorsPaused = savedConn = p.getUChar("conn", 0) == 1;
  p.end();
  drv.session.loadOutq(savedOutq);
  drv.session.seqSaved(millis());
}

// batched: flash writes stall the RGB panel on this board (§6.1): every 10 pushes or 60 s, before sleep
uint32_t outqSavedAt = 0;
void saveSyncLocked(bool force) {
  CloudSession& s = drv.session;
  const uint32_t now = millis();
  const bool seqDue = s.lastSeq != savedSeq && (force || s.seqSaveDue(now));
  const bool outqDue = s.outqDirty && (force || now - outqSavedAt >= 60000u);
  const bool connDue = s.pausedDirty || s.connectorsPaused != savedConn;  // the owner's switch: at once
  if (!seqDue && !outqDue && !connDue) return;
  Preferences p;
  p.begin("soulsync", false);
  if (seqDue) {
    p.putUInt("seq", s.lastSeq);
    savedSeq = s.lastSeq;
    s.seqSaved(now);
  }
  if (outqDue) {
    const std::string q = s.saveOutq();
    if (q != savedOutq) {
      if (q.empty()) p.remove("outq");
      else p.putString("outq", q.c_str());
      savedOutq = q;
    }
    s.outqDirty = false;
    outqSavedAt = now;
  }
  if (connDue) {
    p.putUChar("conn", s.connectorsPaused ? 1 : 0);
    savedConn = s.connectorsPaused;
    s.pausedDirty = false;
  }
  p.end();
  soulFlashWritten();
}

// --------------------------------------------------------------- the task ---

void cloudTask(void*) {
  key.load();
  {
    Lock l;
    loadSync();
  }
  uint32_t lastSave = 0;
  for (;;) {
    bool isOff, changed;
    {
      Lock l;
      isOff = off;
      changed = baseChanged;
      baseChanged = false;
    }
    if (changed) {
      if (drv.connected()) drv.wsClose();
      drv.forgetToken();
      drv.reconnectNow();
    }
    if (isOff || !netOnline()) {  // joined AND the internet answers: not on a hotel's login page
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    Wake w;
    {
      Lock l;
      w = wake;
    }
    if (w == Wake::Polling) {  // one GET, no socket (§6.11)
      const bool ok = drv.wakePoll(millis(), (float)(esp_random() % 1000) / 1000.0f);
      Lock l;
      wake = ok ? Wake::Applying : Wake::Done;
      if (!ok) Serial.println("[cloud] wake-poll failed");
      continue;
    }
    if (w == Wake::Applying) {  // SoulOS applies the pushes (the render loop), then the acks go up at once
      bool settled;
      {
        Lock l;
        settled = drv.session.pushesWaiting() == 0;
      }
      if (settled || millis() - wakeStartMs > 8000) {
        uint32_t at;
        {
          Lock l;
          at = wakeAtEpoch;
        }
        drv.wakePollFinish(millis(), at);
        Lock l;
        saveSyncLocked(true);
        wake = Wake::Done;
      }
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    if (w == Wake::Done) {
      vTaskDelay(pdMS_TO_TICKS(200));
      continue;
    }
    {  // one app request per turn (weather, the map, a route...): never while holding the lock
      suflet::AppFetch f;
      bool have = false;
      {
        Lock l;
        if (!appQ.empty() && drv.haveToken()) {
          f = appQ.front();
          appQ.erase(appQ.begin());
          have = true;
        }
      }
      if (have) {
        std::string resp;
        const int st = drv.appFetch(f.path, f.post, f.body, resp);
        if (resp.size() > 64 * 1024) resp.clear();  // a map bundle is <= 24 KB: anything bigger is not ours
        Serial.printf("[cloud] app %s -> %d (%u B)\n", suflet::fetchName(f.kind), st, (unsigned)resp.size());
        Lock l;
        if (appDone.size() >= 8) appDone.erase(appDone.begin());
        appDone.push_back({f.kind, st, std::move(resp)});
      }
    }
    const uint32_t waitMs = drv.step(millis(), (float)(esp_random() % 1000) / 1000.0f);
    const uint32_t now = millis();
    if (now - lastSave > 1000) {
      lastSave = now;
      Lock l;
      saveSyncLocked(false);
    }
    vTaskDelay(pdMS_TO_TICKS(waitMs ? waitMs : 1));
  }
}

}  // namespace

void cloudBegin(const uint8_t mac[6], const char* fwv, const char* hwv) {
  mtx = xSemaphoreCreateMutex();
  if (nvs_flash_init_partition(kIdPart) != ESP_OK) Serial.println("[cloud] no soulid partition: the key cannot be kept");
  drv.deviceId = CloudLink::deviceId(mac);
  drv.fw = fwv;
  drv.hw = hwv;
  drv.base = SUFLET_CLOUD_BASE;
  off = drv.base.empty();
  drv.session.prefs.fw = fwv;
  drv.session.prefs.hw = hwv;
  drv.session.rng = []() { return (uint32_t)esp_random(); };
  // core 0 next to Wi-Fi; TLS handshakes and P-256 need a deep stack
  xTaskCreatePinnedToCore(cloudTask, "soul-cloud", 16384, nullptr, 2, nullptr, 0);
}

void cloudSetBase(const std::string& b) {
  if (!mtx) return;
  Lock l;
  std::string v = b;
  while (!v.empty() && v.back() == '/') v.pop_back();
  if (v.empty() && !std::string(SUFLET_CLOUD_BASE).empty()) v = SUFLET_CLOUD_BASE;
  if (v == drv.base && !off == !v.empty()) return;
  drv.base = v;
  off = v.empty();
  baseChanged = true;
}

void cloudSetPrefs(AiMode brain, bool ro, const std::string& posixTz) {
  if (!mtx) return;
  Lock l;
  CloudHello& h = drv.session.prefs;
  h.brainLocal = brain == AiMode::Cloud    ? "cloud"
                 : brain == AiMode::None   ? "none"
                 : brain == AiMode::Bridge ? "bridge"
                                           : "direct";  // B1: the key is here
  h.lang = ro ? "ro" : "en";
  if (!posixTz.empty()) h.tzPosix = posixTz;
}

void cloudSetStatus(int batteryPct, bool isAwake) {
  if (!mtx) return;
  Lock l;
  drv.session.setStatus(WiFi.RSSI(), batteryPct, "usb", (uint32_t)heap_caps_get_free_size(MALLOC_CAP_INTERNAL), isAwake);
}

void cloudFill(NetInfo& n) {
  if (!mtx) return;
  Lock l;
  n.relay = n.relay || !off;
  drv.session.fill(n);
  if (drv.base.compare(0, 8, "https://") == 0) n.cloudHost = CloudLink::hostOf(drv.base);
  switch (drv.problem) {
    case CloudDriver::Problem::CannotSignIn: n.cloudProblem = 1; break;
    case CloudDriver::Problem::NotEnrolled: n.cloudProblem = 2; break;
    case CloudDriver::Problem::KeyRevoked: n.cloudProblem = 3; break;
    default: n.cloudProblem = 0; break;
  }
  n.cloudRefused = n.cloudProblem != 0;
}

bool cloudReady() {
  if (!mtx) return false;
  Lock l;
  return drv.session.welcomed();
}

bool cloudAsk(const AiJob& job, bool ro, int timerLeftMin, bool viaBridge) {
  if (!mtx) return false;
  Lock l;
  return drv.session.ask(job.text, ro, timerLeftMin, millis(), viaBridge, job.ctx.memory);
}

bool cloudPaired() {
  if (!mtx) return false;
  Lock l;
  return !off && drv.session.state == "paired";
}

void cloudWakePoll(uint32_t nextWakeEpoch) {
  if (!mtx) return;
  Lock l;
  wake = off ? Wake::Done : Wake::Polling;
  wakeAtEpoch = nextWakeEpoch;
  wakeStartMs = millis();
}

bool cloudWakePollDone() {
  if (!mtx) return true;
  Lock l;
  return wake == Wake::Done;
}

void cloudWakePollAgain(uint32_t nextWakeEpoch) {
  if (!mtx) return;
  Lock l;
  wakeAtEpoch = nextWakeEpoch;
}

void cloudWakePollCancel() {  // the owner woke SOUL up during the poll: back to the socket
  if (!mtx) return;
  Lock l;
  if (drv.session.wakePolling()) drv.session.endWakePoll();
  wake = Wake::None;
}

bool cloudPollAnswer(AiOutcome& out) {
  if (!mtx) return false;
  Lock l;
  return drv.session.pollAnswer(out);
}

bool cloudPollPush(CloudPush& p) {
  if (!mtx) return false;
  Lock l;
  return drv.session.pollPush(p);
}

void cloudAck(uint32_t seq, bool ok, const char* err) {
  if (!mtx) return;
  Lock l;
  drv.session.ackPush(seq, ok, err);
}

void cloudSend(const CloudOut& o, uint32_t localNow, uint32_t epoch) {
  if (!mtx) return;
  Lock l;
  if (off && o.kind != CloudOut::Connectors) return;
  drv.session.send(o, localNow, epoch ? epoch : epochNow());
}

bool cloudPollConfig(CloudConfig& c) {
  if (!mtx) return false;
  Lock l;
  return drv.session.pollConfig(c);
}

bool cloudPollTz(std::string& tz) {
  if (!mtx) return false;
  Lock l;
  return drv.session.pollTz(tz);
}

bool cloudPollTime(uint32_t& epoch) {
  if (!mtx) return false;
  Lock l;
  return drv.session.pollTime(epoch);
}

std::string cloudDeviceId() { return drv.deviceId; }

int cloudKeyGenerate() {
  if (!key.ready) key.load();
  if (key.ready) return 0;
  if (!mtx) return -1;
  Lock l;
  return key.make(true) ? 1 : -1;
}

std::string cloudPubKey() {
  if (!key.ready) key.load();
  return key.ready ? DeviceKey::pubB64(key.pub) : std::string();
}

void cloudSleep(uint32_t wakeAt) {
  if (!mtx) return;
  {
    Lock l;
    drv.session.sleep(wakeAt);
    saveSyncLocked(true);
  }
  vTaskDelay(pdMS_TO_TICKS(150));  // let the task send `sleep` (best effort)
}

void cloudForget() {
  if (!mtx) return;
  Lock l;
  drv.session.lastSeq = savedSeq = 0;
  drv.session.loadOutq(std::string());
  drv.session.connectorsPaused = savedConn = false;
  savedOutq.clear();
  Preferences p;
  p.begin("soulsync", false);
  p.clear();
  p.end();
  key.setReset(true);  // the next auth says reset: true, the cloud unpairs and tells the old owner
}

// ------------------------------------------------------------- SoulOS apps ---

void cloudAppFetch(const suflet::AppFetch& f) {
  Lock l;
  if (off || !netOnline()) {  // no SOUL Cloud or no internet: say so at once (the app shows its offline state)
    appDone.push_back({f.kind, -1, std::string()});
    return;
  }
  if (appQ.size() >= 8) appQ.erase(appQ.begin());
  appQ.push_back(f);
}

bool cloudPollAppData(suflet::Fetch& kind, int& status, std::string& body) {
  Lock l;
  if (appDone.empty()) return false;
  kind = appDone.front().kind;
  status = appDone.front().status;
  body.swap(appDone.front().body);
  appDone.erase(appDone.begin());
  return true;
}
