#include "cloud.h"

#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_crt_bundle.h>
#include <esp_heap_caps.h>
#include <esp_random.h>
#include <esp_transport.h>
#include <esp_transport_ssl.h>
#include <esp_transport_ws.h>
#include <freertos/semphr.h>

#include <deque>
#include <vector>

#include "board.h"
#include "net.h"

using namespace suflet;

#ifndef SUFLET_CLOUD_BASE
#define SUFLET_CLOUD_BASE ""  // e.g. -DSUFLET_CLOUD_BASE=\"https://soul.example.eu\"; the portal can set it too
#endif

namespace {

constexpr uint32_t kPingMs = 25000;     // docs/07 §2.3
constexpr uint32_t kSilentMs = 70000;   // the server closes a socket silent this long; so do we
constexpr uint32_t kHelloMs = 15000;    // welcome must come back by then
constexpr uint32_t kAskMs = 25000;      // one turn, then give up (abort)
constexpr uint32_t kStatusMs = 600000;  // status at least every 10 min
constexpr size_t kMaxMessage = 16384;   // server frames are <= 8 KB
constexpr size_t kMaxQueue = 50, kQueueBytes = 4096;

SemaphoreHandle_t mtx = nullptr;
struct Lock {
  Lock() { xSemaphoreTake(mtx, portMAX_DELAY); }
  ~Lock() { xSemaphoreGive(mtx); }
};

void wipe(std::string& s) {
  for (char& c : s) c = 0;
  s.clear();
}

// ---- shared state (guarded by mtx) ----------------------------------------
std::string base = SUFLET_CLOUD_BASE, deviceId, fw, hw, brainName = "none", lang = "en", tzs;
int battery = -1;
bool awake = true, statusDirty = true, baseChanged = false;
bool welcomed = false, paired = false, needUpdate = false, refused = false;
std::string owner, pairCode, pairUrl;
std::string token, wsUrl;  // secret: never printed
CloudLink link;
uint32_t savedSeq = 0;
std::deque<std::string> up;    // frames to send now (acks, ask, abort, status)
std::deque<std::string> outq;  // item.add / inbox.add until sent (NVS soulid/outq while offline)
std::string savedOutq;
std::deque<CloudPush> pushes;  // for SoulOS
std::vector<uint32_t> inFlight;
bool answerReady = false;
AiOutcome answer;
bool askPending = false;
std::string askId;
uint32_t askAt = 0, askSeq = 0;
bool configReady = false;
CloudConfigMsg config;
bool tzReady = false;
std::string tzNew;
int waitMs = 0;  // from error.retry_ms, for a 4429 close

// ---- the socket (cloud task only) -------------------------------------------
esp_transport_handle_t sslT = nullptr, wsT = nullptr;
int closeCode = 0;
uint32_t lastRx = 0;

// ------------------------------------------------------------------ NVS ---

void saveSeqLocked() {
  if (link.lastSeq == savedSeq) return;
  Preferences p;
  p.begin("soulid", false);
  p.putUInt("seq", link.lastSeq);
  p.end();
  savedSeq = link.lastSeq;
  link.seqSaved(millis());
  soulFlashWritten();
}

void saveQueueLocked() {
  std::string s;
  for (auto it = outq.rbegin(); it != outq.rend(); ++it) {  // newest first, up to 4 KB
    if (s.size() + it->size() + 1 > kQueueBytes) break;
    s = *it + (s.empty() ? "" : "\n") + s;
  }
  if (s == savedOutq) return;
  Preferences p;
  p.begin("soulid", false);
  if (s.empty()) p.remove("outq");
  else p.putString("outq", s.c_str());
  p.end();
  savedOutq = s;
  soulFlashWritten();
}

void loadState() {
  Preferences p;
  p.begin("soulid", false);
  token = p.getString("tok", "").c_str();
  link.lastSeq = savedSeq = p.getUInt("seq", 0);
  savedOutq = p.getString("outq", "").c_str();
  p.end();
  size_t i = 0;
  while (i < savedOutq.size()) {
    size_t e = savedOutq.find('\n', i);
    if (e == std::string::npos) e = savedOutq.size();
    if (e > i) outq.push_back(savedOutq.substr(i, e - i));
    i = e + 1;
  }
  link.seqSaved(millis());
}

// The identity secret: 32 random bytes, made once (with the radio on, so the
// hardware RNG is a true RNG), never printed. Returned base64url for /auth.
bool secretB64(std::string& out) {
  uint8_t sec[32];
  Preferences p;
  p.begin("soulid", false);
  size_t n = p.getBytesLength("sec") == sizeof sec ? p.getBytes("sec", sec, sizeof sec) : 0;
  if (n != sizeof sec) {
    if (WiFi.status() != WL_CONNECTED) {
      p.end();
      return false;
    }
    esp_fill_random(sec, sizeof sec);
    n = p.putBytes("sec", sec, sizeof sec);
    soulFlashWritten();
  }
  p.end();
  out = n == sizeof sec ? CloudLink::base64url(sec, sizeof sec) : std::string();
  volatile uint8_t* v = sec;
  for (size_t i = 0; i < sizeof sec; ++i) v[i] = 0;
  return !out.empty();
}

void dropToken() {
  Lock l;
  wipe(token);
  wsUrl.clear();
  Preferences p;
  p.begin("soulid", false);
  p.remove("tok");
  p.end();
  soulFlashWritten();
}

// ----------------------------------------------------------------- auth ---

enum class Auth : uint8_t { Ok, Retry, Refused };

Auth authenticate() {
  std::string b, id;
  {
    Lock l;
    b = base;
    id = deviceId;
  }
  std::string sec;
  if (!secretB64(sec)) return Auth::Retry;
  HttpRequest rq;
  rq.url = b + "/v1/device/auth";
  rq.headers = {{"content-type", "application/json"}};
  rq.body = CloudLink::authBody(id, sec, fw.c_str(), hw.c_str());
  rq.timeoutMs = 15000;
  wipe(sec);
  std::string body;
  AiErr err;
  const int status = netHttpsPost(rq, body, err);
  wipe(rq.body);
  CloudAuth a;
  const bool ok = CloudLink::parseAuth(status, body.data(), body.size(), a);
  wipe(body);
  if (!ok) {
    Serial.printf("[cloud] auth: HTTP %d (%s)\n", status, aiErrCode(err));
    if (status == 401 || status == 409) {  // not our secret / id claimed by another one: a person must look
      Lock l;
      refused = true;
      return Auth::Refused;
    }
    return Auth::Retry;
  }
  Lock l;
  refused = false;
  if (a.token != token) {
    token = a.token;
    Preferences p;
    p.begin("soulid", false);
    p.putString("tok", token.c_str());
    p.end();
    soulFlashWritten();
  }
  wipe(a.token);
  wsUrl = a.wsUrl;
  paired = a.paired;
  owner = a.owner;
  if (a.pairCode.size() == 6 && a.pairCode.find_first_not_of("0123456789") == std::string::npos) pairCode = a.pairCode;
  if (a.pairUrl.compare(0, 8, "https://") == 0 && a.pairUrl.size() <= 200) pairUrl = a.pairUrl;
  Serial.printf("[cloud] device token ok, %s\n", paired ? "paired" : "not paired yet");
  return Auth::Ok;
}

// --------------------------------------------------------------- socket ---

bool parseWss(const std::string& url, std::string& host, int& port, std::string& path) {
  if (url.compare(0, 6, "wss://") != 0) return false;  // TLS only
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

void closeSocket() {
  if (wsT) {
    esp_transport_close(wsT);
    esp_transport_destroy(wsT);
    wsT = nullptr;
  }
  if (sslT) {
    esp_transport_destroy(sslT);
    sslT = nullptr;
  }
  Lock l;
  if (welcomed) Serial.println("[cloud] socket closed");
  welcomed = false;
  if (askPending) {  // the turn is lost: the render loop falls back to the rules
    askPending = false;
    answer = AiOutcome();
    answer.err = AiErr::Network;
    answerReady = true;
  }
  for (uint32_t s : inFlight) (void)s;  // SoulOS still acks them; the acks wait in `up` for the next socket
}

// 0 = open; else the HTTP status of a refused upgrade, or -1
int openSocket() {
  std::string url, auth, b;
  {
    Lock l;
    b = base;
    url = wsUrl;
    auth = "Bearer " + token;
  }
  if (url.empty() && b.compare(0, 8, "https://") == 0) url = "wss://" + b.substr(8) + "/v1/device/ws";
  std::string host, path;
  int port = 443;
  if (!parseWss(url, host, port, path)) {
    wipe(auth);
    return -1;
  }
  sslT = esp_transport_ssl_init();
  if (!sslT) {
    wipe(auth);
    return -1;
  }
  esp_transport_ssl_crt_bundle_attach(sslT, esp_crt_bundle_attach);  // verified TLS, never insecure
  wsT = esp_transport_ws_init(sslT);
  if (!wsT) {
    wipe(auth);
    closeSocket();
    return -1;
  }
  const std::string ua = "SOUL/" + fw;
  esp_transport_ws_config_t c = {};
  c.ws_path = path.c_str();
  c.sub_protocol = "soul.v1";
  c.user_agent = ua.c_str();
  c.auth = auth.c_str();  // the token travels in the Authorization header, never in the URL
  c.propagate_control_frames = true;  // we see PING/CLOSE (close codes matter)
  esp_transport_ws_set_config(wsT, &c);
  wipe(auth);
  const int r = esp_transport_connect(wsT, host.c_str(), port, 10000);
  if (r < 0) {
    const int status = esp_transport_ws_get_upgrade_request_status(wsT);
    closeSocket();
    return status > 0 ? status : -1;
  }
  lastRx = millis();
  return 0;
}

bool sendFrame(std::string s, ws_transport_opcodes_t op = WS_TRANSPORT_OPCODES_TEXT) {
  if (!wsT) return false;
  // the ws layer masks the payload in place (and restores it): hand it a copy
  const int r = esp_transport_ws_send_raw(wsT, (ws_transport_opcodes_t)(op | WS_TRANSPORT_OPCODES_FIN),
                                          s.empty() ? nullptr : &s[0], (int)s.size(), 5000);
  return r >= 0;
}

AiOutcome outcomeFromReply(const CloudReply& r) {
  AiOutcome o;
  o.httpStatus = 200;
  o.reply.say = r.reply.say;
  o.reply.face = r.reply.face;
  if (!r.body.empty()) o.reply.say += (o.reply.say.empty() ? "" : "\n") + r.body;  // a card under the words
  o.raw = r.reply.say;
  return o;
}

void handlePushLocked() {
  const CloudPush& p = link.push;
  if (link.alreadyApplied(p.seq)) {  // a replay: ack again, do not apply
    up.push_back(link.ack(p.seq, true));
    return;
  }
  for (uint32_t s : inFlight)
    if (s == p.seq) return;  // SoulOS has it already
  if (p.kind == CloudPush::Unsupported || p.kind == CloudPush::Invalid) {
    up.push_back(link.ack(p.seq, false, p.kind == CloudPush::Unsupported ? "unsupported" : "invalid"));
    link.applied(p.seq);
    Serial.printf("[cloud] push %lu %s: %s\n", (unsigned long)p.seq, p.action.c_str(),
                  p.kind == CloudPush::Unsupported ? "unsupported" : "invalid");
    return;
  }
  if (pushes.size() >= 16) return;  // SoulOS is behind: no ack, the cloud sends it again
  pushes.push_back(p);
  inFlight.push_back(p.seq);
  Serial.printf("[cloud] push %lu %s from %s\n", (unsigned long)p.seq, p.action.c_str(), p.source.c_str());
}

void dispatch(const std::string& m) {
  Lock l;
  switch (link.feed(m.data(), m.size())) {
    case CloudLink::Msg::Welcome:
      welcomed = true;
      paired = link.paired;
      owner = link.owner;
      statusDirty = true;
      if (!link.posixTz.empty() && link.posixTz != tzs && link.posixTz.size() < 64) {
        tzNew = link.posixTz;
        tzReady = true;
      }
      Serial.printf("[cloud] welcome, %s\n", paired ? "paired" : "not paired");
      break;
    case CloudLink::Msg::Pairing:
      pairCode = link.pairCode;
      pairUrl = link.pairUrl;
      paired = false;
      Serial.println("[cloud] pairing code received");  // the code is on the screen, not in the log
      break;
    case CloudLink::Msg::Paired:
      paired = true;
      owner = link.owner;
      pairCode.clear();
      pairUrl.clear();
      Serial.println("[cloud] paired");
      break;
    case CloudLink::Msg::Unpaired:
      paired = false;
      owner.clear();
      Serial.println("[cloud] unpaired");
      break;
    case CloudLink::Msg::Reply:
      if (askPending && link.reply.re == askId) {
        answer = outcomeFromReply(link.reply);
        answerReady = true;
        askPending = false;
      }
      break;
    case CloudLink::Msg::Error:
      Serial.printf("[cloud] error %s\n", link.error.code.c_str());
      if (askPending && link.error.re == askId) {
        answer = AiOutcome();
        answer.err = link.error.code == "unpaired" ? AiErr::NoKey : link.error.err;
        answerReady = true;
        askPending = false;
      }
      if (link.error.code == "unpaired") paired = false;
      if (link.error.retryMs > 0) waitMs = link.error.retryMs;
      break;
    case CloudLink::Msg::Push: handlePushLocked(); break;
    case CloudLink::Msg::Config:
      config.brain = link.brain;
      config.lang = link.lang;
      config.name = link.name;
      config.modelClaude = link.modelClaude;
      config.modelOpenai = link.modelOpenai;
      configReady = true;
      break;
    case CloudLink::Msg::Bad: Serial.printf("[cloud] unreadable frame (%u B)\n", (unsigned)m.size()); break;
    default: break;  // must-ignore: unknown types (say.delta: we did not ask for streaming)
  }
}

// One message (control frames are answered here). false = the socket is done.
bool readMessage() {
  std::string msg;
  char buf[1024];
  for (;;) {
    int r = esp_transport_read(wsT, buf, sizeof buf, 2000);
    if (r < 0) return false;
    const ws_transport_opcodes_t op = esp_transport_ws_get_read_opcode(wsT);
    if (op == WS_TRANSPORT_OPCODES_NONE) return msg.empty();  // nothing arrived after all
    const int len = esp_transport_ws_get_read_payload_len(wsT);
    if (len < 0 || (size_t)len > kMaxMessage) return false;
    std::string payload(buf, (size_t)r);
    while ((int)payload.size() < len) {
      const size_t want = (size_t)len - payload.size();
      r = esp_transport_read(wsT, buf, want < sizeof buf ? (int)want : (int)sizeof buf, 5000);
      if (r <= 0) return false;
      payload.append(buf, (size_t)r);
    }
    lastRx = millis();
    switch (op) {
      case WS_TRANSPORT_OPCODES_PING: sendFrame(payload, WS_TRANSPORT_OPCODES_PONG); return true;
      case WS_TRANSPORT_OPCODES_PONG: return true;
      case WS_TRANSPORT_OPCODES_CLOSE:
        closeCode = payload.size() >= 2 ? ((uint8_t)payload[0] << 8 | (uint8_t)payload[1]) : 1005;
        sendFrame(payload.substr(0, 2), WS_TRANSPORT_OPCODES_CLOSE);
        return false;
      case WS_TRANSPORT_OPCODES_TEXT:
      case WS_TRANSPORT_OPCODES_CONT:
        msg += payload;
        if (msg.size() > kMaxMessage) return false;
        if (!esp_transport_ws_get_fin_flag(wsT)) continue;  // more fragments follow
        dispatch(msg);
        return true;
      default:  // binary (Phase 2 audio): not spoken here
        if (!esp_transport_ws_get_fin_flag(wsT)) continue;
        return true;
    }
  }
}

// --------------------------------------------------------------- the task ---

uint32_t jitterBackoff(int attempt) { return CloudLink::backoffMs(attempt, (float)(esp_random() % 1000) / 1000.0f); }

void cloudTask(void*) {
  loadState();
  int attempt = 0;
  uint32_t retryAt = 0, openedAt = 0, lastPing = 0, helloAt = 0, lastStatus = 0, lastSave = 0;
  bool waiting = false;
  for (;;) {
    const uint32_t now = millis();
    bool off, changed;
    {
      Lock l;
      off = base.empty();
      changed = baseChanged;
      baseChanged = false;
    }
    if (changed && wsT) closeSocket();
    if (off || WiFi.status() != WL_CONNECTED) {
      if (wsT) closeSocket();
      attempt = 0;
      waiting = false;
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    if (waiting && (int32_t)(retryAt - now) > 0) {
      vTaskDelay(pdMS_TO_TICKS(200));
      continue;
    }
    waiting = false;
    auto retryIn = [&](uint32_t ms) {
      retryAt = millis() + ms;
      waiting = true;
    };

    if (!wsT) {
      bool haveToken;
      {
        Lock l;
        haveToken = !token.empty();
      }
      if (!haveToken) {
        const Auth a = authenticate();
        if (a == Auth::Refused) {
          retryIn(30u * 60u * 1000u);  // a person must look at the account page; try again later
          continue;
        }
        if (a == Auth::Retry) {
          retryIn(jitterBackoff(++attempt));
          continue;
        }
      }
      const int st = openSocket();
      if (st != 0) {
        Serial.printf("[cloud] socket refused: %d\n", st);
        if (st == 401 || st == 403) {  // the token is no good (expired / revoked): enrol again
          dropToken();
          if (st == 403) {
            Lock l;
            paired = false;
          }
          retryIn(st == 401 ? 500 : jitterBackoff(++attempt));
        } else if (st == 426) {
          Lock l;
          needUpdate = true;
          retryIn(3600u * 1000u);
        } else {
          retryIn(jitterBackoff(++attempt));
        }
        continue;
      }
      openedAt = lastPing = helloAt = lastStatus = millis();
      closeCode = 0;
      std::string hello;
      {
        Lock l;
        needUpdate = false;
        hello = link.hello(fw.c_str(), hw.c_str(), brainName.c_str(), lang.c_str(), tzs.c_str());
      }
      if (!sendFrame(hello)) {
        closeSocket();
        retryIn(jitterBackoff(++attempt));
        continue;
      }
      Serial.println("[cloud] socket open, hello sent");
    }

    // ---- connected ---------------------------------------------------------
    bool alive = true;
    for (int i = 0; alive && i < 8; ++i) {  // what arrived (several frames may wait in the TLS buffer)
      const int p = esp_transport_poll_read(wsT, i ? 0 : 30);
      if (p < 0) alive = false;
      else if (p == 0) break;
      else alive = readMessage();
    }
    const uint32_t t = millis();
    if (alive) {
      std::string f;
      bool isQueued = false;
      for (;;) {  // frames up: acks / ask / status first, then the queue once welcomed
        {
          Lock l;
          if (!up.empty()) {
            f = up.front();
            up.pop_front();
            isQueued = false;
          } else if (welcomed && !outq.empty()) {
            f = outq.front();
            isQueued = true;
          } else {
            break;
          }
        }
        if (!sendFrame(f)) {
          alive = false;
          if (!isQueued) {
            Lock l;
            up.push_front(f);  // try again on the next socket
          }
          break;
        }
        if (isQueued) {
          Lock l;
          if (!outq.empty() && outq.front() == f) outq.pop_front();
        }
      }
    }
    if (alive && t - lastPing > kPingMs) {
      lastPing = t;
      alive = sendFrame(std::string(), WS_TRANSPORT_OPCODES_PING);
    }
    {
      Lock l;
      if (alive && !welcomed && t - helloAt > kHelloMs) {
        Serial.println("[cloud] no welcome");
        alive = false;
      }
      if (askPending && t - askAt > kAskMs) {  // too slow: drop it, the rules answer
        up.push_back(link.abort(askId));
        askPending = false;
        answer = AiOutcome();
        answer.err = AiErr::Timeout;
        answerReady = true;
      }
      if (welcomed && (statusDirty || t - lastStatus > kStatusMs)) {
        statusDirty = false;
        lastStatus = t;
        up.push_back(link.status(battery, WiFi.RSSI(), awake, fw.c_str(),
                                 (uint32_t)heap_caps_get_free_size(MALLOC_CAP_INTERNAL)));
      }
      if (link.seqSaveDue(t)) saveSeqLocked();
      if (t - lastSave > 60000) {  // the offline queue, batched like the seq
        lastSave = t;
        saveQueueLocked();
      }
    }
    if (alive && t - lastRx > kSilentMs) {
      Serial.println("[cloud] silent socket");
      alive = false;
    }
    if (!alive) {
      const int code = closeCode;
      closeSocket();
      int wait = 0;
      {
        Lock l;
        wait = waitMs;
        waitMs = 0;
      }
      switch (CloudLink::onClose(code)) {
        case CloudLink::CloseAction::Reauth:
          dropToken();
          retryIn(500);
          break;
        case CloudLink::CloseAction::Unpaired: {
          dropToken();
          Lock l;
          paired = false;
          retryIn(jitterBackoff(++attempt));
          break;
        }
        case CloudLink::CloseAction::Update: {
          Lock l;
          needUpdate = true;
          retryIn(3600u * 1000u);
          break;
        }
        case CloudLink::CloseAction::Wait: retryIn(wait > 0 ? (uint32_t)wait : 60000u); break;
        default: retryIn(jitterBackoff(++attempt)); break;
      }
      if (code) Serial.printf("[cloud] closed by the server: %d\n", code);
      continue;
    }
    if (openedAt && t - openedAt > 60000) {  // a minute up: the next drop starts the backoff again
      attempt = 0;
      openedAt = 0;
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

std::string cid() {
  char b[20];
  snprintf(b, sizeof b, "%08lx%08lx", (unsigned long)esp_random(), (unsigned long)esp_random());
  return b;
}

}  // namespace

void cloudBegin(const uint8_t mac[6], const char* fwv, const char* hwv) {
  mtx = xSemaphoreCreateMutex();
  deviceId = CloudLink::deviceId(mac);
  fw = fwv;
  hw = hwv;
  // core 0 next to Wi-Fi; TLS handshakes need a deep stack
  xTaskCreatePinnedToCore(cloudTask, "soul-cloud", 12288, nullptr, 2, nullptr, 0);
}

void cloudSetBase(const std::string& b) {
  if (!mtx) return;
  Lock l;
  std::string v = b;
  while (!v.empty() && v.back() == '/') v.pop_back();
  if (v.empty() && base.empty()) return;
  if (v.empty() && !std::string(SUFLET_CLOUD_BASE).empty()) v = SUFLET_CLOUD_BASE;
  if (v == base) return;
  base = v;
  wsUrl.clear();
  baseChanged = true;
}

void cloudSetPrefs(AiMode brain, bool ro, const std::string& posixTz) {
  if (!mtx) return;
  Lock l;
  brainName = aiModeName(brain);
  lang = ro ? "ro" : "en";
  tzs = posixTz;
}

void cloudSetStatus(int batteryPct, bool isAwake) {
  if (!mtx) return;
  Lock l;
  if (isAwake != awake) statusDirty = true;
  awake = isAwake;
  battery = batteryPct;
}

void cloudFill(NetInfo& n) {
  if (!mtx) return;
  Lock l;
  n.relay = n.relay || !base.empty();
  n.cloudOnline = welcomed;
  n.paired = paired;
  n.owner = owner;
  n.pairCode = paired ? std::string() : pairCode;
  n.pairUrl = paired ? std::string() : pairUrl;
  n.cloudUpdate = needUpdate;
  n.cloudRefused = refused;
}

bool cloudReady() {
  if (!mtx) return false;
  Lock l;
  return welcomed;
}

bool cloudAsk(const AiJob& job, bool ro) {
  if (!mtx) return false;
  Lock l;
  if (!welcomed || askPending) return false;
  askId = "a" + std::to_string(++askSeq);
  up.push_back(link.ask(askId, job.text, ro ? "ro" : "en", job.ctx));
  askPending = true;
  askAt = millis();
  return true;
}

bool cloudPollAnswer(AiOutcome& out) {
  if (!mtx) return false;
  Lock l;
  if (!answerReady) return false;
  out = answer;
  answer = AiOutcome();
  answerReady = false;
  return true;
}

bool cloudPollPush(CloudPush& p) {
  if (!mtx) return false;
  Lock l;
  if (pushes.empty()) return false;
  p = pushes.front();
  pushes.pop_front();
  return true;
}

void cloudAck(uint32_t seq, bool ok, const char* err) {
  if (!mtx) return;
  Lock l;
  up.push_back(link.ack(seq, ok, err));
  link.applied(seq);
  for (size_t i = 0; i < inFlight.size(); ++i)
    if (inFlight[i] == seq) {
      inFlight.erase(inFlight.begin() + (long)i);
      break;
    }
}

void cloudSend(const CloudOut& o) {
  if (!mtx) return;
  Lock l;
  if (base.empty()) return;
  outq.push_back(o.kind == CloudOut::Inbox ? link.inboxAdd(cid(), o.text, "claude") : link.itemAdd(cid(), o.act, o.created));
  while (outq.size() > kMaxQueue) outq.pop_front();  // the items stay on SOUL either way
}

bool cloudPollConfig(CloudConfigMsg& c) {
  if (!mtx) return false;
  Lock l;
  if (!configReady) return false;
  c = config;
  configReady = false;
  return true;
}

bool cloudPollTz(std::string& tz) {
  if (!mtx) return false;
  Lock l;
  if (!tzReady) return false;
  tz = tzNew;
  tzs = tzNew;
  tzReady = false;
  return true;
}

std::string cloudToken() {
  if (!mtx) return std::string();
  Lock l;
  return token;
}

void cloudSleep() {
  if (!mtx) return;
  Lock l;
  saveSeqLocked();
  saveQueueLocked();
}

void cloudForget() {
  if (!mtx) return;
  Lock l;
  wipe(token);
  wsUrl.clear();
  link.lastSeq = savedSeq = 0;
  outq.clear();
  savedOutq.clear();
  paired = false;
  owner.clear();
  Preferences p;
  p.begin("soulid", false);
  p.remove("tok");
  p.remove("seq");
  p.remove("outq");
  p.end();  // "sec" stays: it is this SOUL's identity (a new one would be refused as a stranger)
}
