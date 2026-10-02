#include "net.h"

#include <Arduino.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_crt_bundle.h>
#include <esp_http_client.h>
#include <esp_random.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <time.h>

#include <vector>

using namespace suflet;

#ifndef SUFLET_DEFAULT_TZ
#define SUFLET_DEFAULT_TZ "EET-2EEST,M3.5.0/3,M10.5.0/4"  // Romania (POSIX TZ)
#endif
#ifndef SUFLET_VOICE
#define SUFLET_VOICE 0
#endif

namespace {

constexpr size_t kMaxBody = 96 * 1024;
constexpr uint32_t kTimeoutMs = 25000;

SemaphoreHandle_t mtx = nullptr;
QueueHandle_t jobs = nullptr;
NetInfo info;
std::string apName, apPass, deviceId;
bool portalWanted = false, portalUp = false, reconnect = false, forget = false;
bool answerReady = false;
AiOutcome answer;
std::string portalName;
bool portalNameReady = false;
volatile bool busy = false;

// secrets and Wi-Fi (loaded on the network task; never printed)
std::string ssid, pass, tz = SUFLET_DEFAULT_TZ;
AiConfig cfg;

DNSServer dns;
WebServer server(80);

struct Lock {
  Lock() { xSemaphoreTake(mtx, portMAX_DELAY); }
  ~Lock() { xSemaphoreGive(mtx); }
};

void wipe(std::string& s) {
  for (char& c : s) c = 0;
  s.clear();
}

void loadSecrets() {
  Preferences p;
  p.begin("soulkey", true);
  ssid = p.getString("ssid", "").c_str();
  pass = p.getString("pass", "").c_str();
  tz = p.getString("tz", SUFLET_DEFAULT_TZ).c_str();
  cfg.anthropicKey = p.getString("claude", "").c_str();
  cfg.openaiKey = p.getString("openai", "").c_str();
  cfg.relayUrl = p.getString("cloud", "").c_str();
  cfg.relayToken = p.getString("ctoken", "").c_str();
  cfg.claudeModel = p.getString("cmodel", "claude-opus-5-5").c_str();
  cfg.openaiModel = p.getString("omodel", "gpt-6.1-sol").c_str();
  cfg.mode = (AiMode)p.getUChar("mode", 0);
  p.end();
  cfg.deviceId = deviceId;
}

void publish() {  // what the UI may know (never the secrets themselves)
  Lock l;
  info.configured = !ssid.empty();
  info.ssid = ssid;
  info.connected = WiFi.status() == WL_CONNECTED;
  info.connecting = info.configured && !info.connected;
  info.ip = info.connected ? WiFi.localIP().toString().c_str() : "";
  info.rssi = info.connected ? WiFi.RSSI() : 0;
  info.portal = portalUp;
  info.apName = apName;
  info.apPass = portalUp ? apPass : std::string();
  info.portalUrl = "http://192.168.4.1";
  info.keyClaude = !cfg.anthropicKey.empty();
  info.keyOpenai = !cfg.openaiKey.empty();
  info.relay = !cfg.relayUrl.empty();
  info.maskClaude = maskKey(cfg.anthropicKey);
  info.maskOpenai = maskKey(cfg.openaiKey);
}

// ------------------------------------------------------------- HTTPS ---

struct Resp {
  std::string body;
  bool overflow = false;
};

esp_err_t onHttp(esp_http_client_event_t* e) {
  if (e->event_id == HTTP_EVENT_ON_DATA && e->user_data) {
    Resp* r = (Resp*)e->user_data;
    if (r->body.size() + e->data_len <= kMaxBody) r->body.append((const char*)e->data, e->data_len);
    else r->overflow = true;
  }
  return ESP_OK;
}

// POST with TLS verified against the ESP-IDF certificate bundle.
int httpsPost(const HttpRequest& rq, std::string& body, AiErr& err) {
  err = AiErr::None;
  if (WiFi.status() != WL_CONNECTED) {
    err = AiErr::Offline;
    return -1;
  }
  Resp resp;
  esp_http_client_config_t c = {};
  c.url = rq.url.c_str();
  c.method = HTTP_METHOD_POST;
  c.timeout_ms = (int)rq.timeoutMs;
  c.crt_bundle_attach = esp_crt_bundle_attach;
  c.event_handler = onHttp;
  c.user_data = &resp;
  c.buffer_size = 4096;
  c.buffer_size_tx = 2048;
  esp_http_client_handle_t h = esp_http_client_init(&c);
  if (!h) {
    err = AiErr::Network;
    return -1;
  }
  for (const auto& hd : rq.headers) esp_http_client_set_header(h, hd.first.c_str(), hd.second.c_str());
  esp_http_client_set_post_field(h, rq.body.data(), (int)rq.body.size());
  const esp_err_t e = esp_http_client_perform(h);
  const int status = e == ESP_OK ? esp_http_client_get_status_code(h) : -1;
  esp_http_client_cleanup(h);
  if (e != ESP_OK) {
    err = (e == ESP_ERR_HTTP_EAGAIN || e == ESP_ERR_TIMEOUT) ? AiErr::Timeout : AiErr::Network;
    Serial.printf("[ai] %s: %s\n", rq.url.c_str(), esp_err_to_name(e));  // the URL only: never headers
    return -1;
  }
  if (resp.overflow) {
    err = AiErr::Upstream;
    return -1;
  }
  body.swap(resp.body);
  return status;
}

// ----------------------------------------------------------- backends ---

struct DirectBackend : AiBackend {
  const char* name() const override { return "direct"; }
  AiOutcome ask(const AiConfig& c, const AiJob& job, uint32_t now) override {
    AiConfig conf = c;
    AiOutcome o;
    for (int attempt = 1;; ++attempt) {
      HttpRequest rq;
      const AiErr be = buildRequest(conf, job.ctx, job.history, job.text, rq);
      if (be != AiErr::None) {
        o = AiOutcome();
        o.err = be;
        return o;
      }
      rq.timeoutMs = kTimeoutMs;
      std::string body;
      AiErr ne;
      const uint32_t t0 = millis();
      const int status = httpsPost(rq, body, ne);
      for (auto& hd : rq.headers)  // the key headers do not outlive the request
        if (hd.first == "x-api-key" || hd.first == "authorization") wipe(hd.second);
      o = parseResponse(conf, status, body.data(), body.size(), ne, now);
      Serial.printf("[ai] %s %s -> %d %s in %lu ms\n", aiModeName(conf.mode), name(), status, aiErrCode(o.err),
                    (unsigned long)(millis() - t0));
      if (o.schemaRejected && conf.useSchema) {  // structured outputs refused: same question, prompt-only JSON
        conf.useSchema = false;
        continue;
      }
      const int delayMs = retryDelayMs(o, attempt);
      if (delayMs < 0) return o;
      vTaskDelay(pdMS_TO_TICKS(delayMs));
    }
  }
};

// SOUL Cloud. Today: the relay of micul-smecher/ai (POST /v1/ask, Bearer
// token). The pairing / WebSocket contract (docs/07-CONNECT-AI.md) replaces
// this class without touching the UI: SoulOS only sees AiJob -> AiOutcome.
struct CloudBackend : DirectBackend {
  const char* name() const override { return "cloud"; }
};

DirectBackend direct;
CloudBackend cloud;

AiBackend& backendFor(AiMode m) { return m == AiMode::Cloud ? (AiBackend&)cloud : (AiBackend&)direct; }

// ------------------------------------------------------------- portal ---

std::string htmlEsc(const std::string& s) {
  std::string o;
  for (char c : s) {
    switch (c) {
      case '<': o += "&lt;"; break;
      case '>': o += "&gt;"; break;
      case '&': o += "&amp;"; break;
      case '"': o += "&quot;"; break;
      default: o += c;
    }
  }
  return o;
}

std::string scanOptions() {
  std::string o;
  const int n = WiFi.scanNetworks(false, false);
  for (int i = 0; i < n && i < 20; ++i) {
    const std::string s = WiFi.SSID(i).c_str();
    if (s.empty()) continue;
    o += "<option value=\"" + htmlEsc(s) + "\">" + htmlEsc(s) + " (" + std::to_string(WiFi.RSSI(i)) + " dBm)</option>";
  }
  WiFi.scanDelete();
  return o;
}

const char* kStyle =
    "<style>body{font-family:system-ui,sans-serif;background:#000;color:#FFF0C8;max-width:30em;margin:auto;padding:1em}"
    "h1{font-weight:600}label{display:block;margin:.9em 0 .2em;color:#c8bd9e}input,select{width:100%;box-sizing:border-box;"
    "padding:.7em;border-radius:.5em;border:1px solid #555;background:#111;color:#FFF0C8;font-size:1em}"
    "button{margin-top:1.2em;width:100%;padding:.9em;border:0;border-radius:2em;background:#FFB347;color:#000;font-size:1.05em;"
    "font-weight:600}small{color:#8a8270}.r{display:flex;gap:.6em;align-items:center}.r input{width:auto}</style>";

void pageRoot() {
  const std::string opts = scanOptions();
  const char* modes[] = {"No AI (on the device)", "Claude (your Anthropic key)", "ChatGPT (your OpenAI key)", "SOUL Cloud"};
  std::string mode;
  for (int i = 0; i < 4; ++i) {
    static const int order[4] = {3, 1, 2, 0};
    const int m = order[i];
    mode += "<option value=\"" + std::to_string(m) + "\"" + ((int)cfg.mode == m ? " selected" : "") + ">" + modes[m] + "</option>";
  }
  std::string page =
      "<!doctype html><html><head><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1\">"
      "<title>SOUL setup</title>" + std::string(kStyle) +
      "</head><body><h1>SOUL setup</h1><form method=post action=/save>"
      "<label>Wi-Fi network</label><select name=ssid><option value=\"\">" +
      (ssid.empty() ? std::string("choose…") : "keep: " + htmlEsc(ssid)) + "</option>" + opts +
      "</select><label>or type its name</label><input name=ssid2 autocomplete=off>"
      "<label>Wi-Fi password</label><input name=pass type=password autocomplete=off placeholder=\"" +
      (pass.empty() ? std::string("") : "unchanged") +
      "\"><label>Who helps SOUL think?</label><select name=mode>" + mode +
      "</select><label>Anthropic API key <small>" + (cfg.anthropicKey.empty() ? std::string("not set") : "set: " + htmlEsc(maskKey(cfg.anthropicKey))) +
      "</small></label><input name=claude type=password autocomplete=off placeholder=\"sk-ant-…\">"
      "<label>OpenAI API key <small>" + (cfg.openaiKey.empty() ? std::string("not set") : "set: " + htmlEsc(maskKey(cfg.openaiKey))) +
      "</small></label><input name=openai type=password autocomplete=off placeholder=\"sk-…\">"
      "<label>SOUL Cloud address and token <small>(optional)</small></label><input name=cloud value=\"" + htmlEsc(cfg.relayUrl) +
      "\" placeholder=\"https://…\"><input name=ctoken type=password autocomplete=off placeholder=\"" +
      (cfg.relayToken.empty() ? std::string("token") : "token: unchanged") +
      "\"><label>Time zone <small>(POSIX TZ)</small></label><input name=tz value=\"" + htmlEsc(tz) +
      "\"><label>SOUL's name <small>(optional)</small></label><input name=name maxlength=16>"
      "<div class=r><input type=checkbox name=forget id=f><label for=f>Forget the stored API keys</label></div>"
      "<button>Save</button></form><p><small>Keys are kept on this SOUL only and are sent only to the AI you chose. "
      "This page never shows them back.</small></p></body></html>";
  server.send(200, "text/html; charset=utf-8", page.c_str());
}

void pageSave() {
  Preferences p;
  p.begin("soulkey", false);
  std::string s = server.arg("ssid2").c_str();
  if (s.empty()) s = server.arg("ssid").c_str();
  if (!s.empty() && s.size() <= 32) {
    ssid = s;
    p.putString("ssid", ssid.c_str());
    std::string pw = server.arg("pass").c_str();
    if (!pw.empty() && pw.size() <= 63) {
      pass = pw;
      p.putString("pass", pass.c_str());
    }
    wipe(pw);
    reconnect = true;
  }
  const int mode = server.arg("mode").toInt();
  if (mode >= 0 && mode <= 3) {
    cfg.mode = (AiMode)mode;
    p.putUChar("mode", (uint8_t)mode);
  }
  std::string k = server.arg("claude").c_str();
  if (keyLooksValid(AiMode::Claude, k)) {
    cfg.anthropicKey = k;
    p.putString("claude", k.c_str());
  }
  wipe(k);
  k = server.arg("openai").c_str();
  if (keyLooksValid(AiMode::ChatGpt, k)) {
    cfg.openaiKey = k;
    p.putString("openai", k.c_str());
  }
  wipe(k);
  const std::string url = server.arg("cloud").c_str();
  if (url.empty() || url.compare(0, 8, "https://") == 0) {
    cfg.relayUrl = url;
    p.putString("cloud", url.c_str());
  }
  k = server.arg("ctoken").c_str();
  if (!k.empty() && k.size() < 200) {
    cfg.relayToken = k;
    p.putString("ctoken", k.c_str());
  }
  wipe(k);
  const std::string z = server.arg("tz").c_str();
  if (!z.empty() && z.size() < 64) {
    tz = z;
    p.putString("tz", tz.c_str());
  }
  if (server.hasArg("forget")) {
    wipe(cfg.anthropicKey);
    wipe(cfg.openaiKey);
    p.remove("claude");
    p.remove("openai");
  }
  p.end();
  const std::string nm = server.arg("name").c_str();
  if (!nm.empty()) {
    Lock l;
    portalName = nm.substr(0, 16);
    portalNameReady = true;
  }
  server.send(200, "text/html; charset=utf-8",
              (std::string("<!doctype html><meta charset=utf-8><meta name=viewport content=\"width=device-width\">") + kStyle +
               "<h1>Saved</h1><p>SOUL is joining your Wi-Fi now. You can close this page and go back to your usual Wi-Fi.</p>")
                  .c_str());
  publish();
}

void portalStart() {
  if (portalUp) return;
  char pw[9];
  snprintf(pw, sizeof pw, "%08lu", (unsigned long)(esp_random() % 100000000UL));
  apPass = pw;
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apName.c_str(), apPass.c_str());
  dns.start(53, "*", WiFi.softAPIP());
  server.on("/", HTTP_GET, pageRoot);
  server.on("/save", HTTP_POST, pageSave);
  server.onNotFound([] {  // captive portal: every URL leads to the form
    server.sendHeader("Location", "http://192.168.4.1/");
    server.send(302, "text/plain", "");
  });
  server.begin();
  portalUp = true;
  Serial.printf("[net] setup portal: Wi-Fi %s (password on the screen), http://192.168.4.1\n", apName.c_str());
}

void portalStop() {
  if (!portalUp) return;
  server.stop();
  dns.stop();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_STA);
  portalUp = false;
}

void connectSta() {
  if (ssid.empty()) return;
  WiFi.mode(portalUp ? WIFI_AP_STA : WIFI_STA);
  WiFi.setSleep(true);  // modem sleep between beacons (also required with BLE)
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid.c_str(), pass.c_str());
  Serial.printf("[net] joining Wi-Fi \"%s\"\n", ssid.c_str());
}

// ------------------------------------------------------------- voice ---

#if SUFLET_VOICE
}  // namespace
#include <ArduinoJson.h>
namespace {
struct VoiceJob {
  std::vector<int16_t> pcm;
  bool ro;
};
QueueHandle_t voiceQ = nullptr;
bool voiceReady = false;
std::string voiceText;
AiErr voiceErr = AiErr::None;

void transcribe(VoiceJob* v) {
  AiErr err = AiErr::None;
  std::string text;
  if (cfg.openaiKey.empty()) {
    err = AiErr::NoKey;
  } else {
    // multipart/form-data: model + a WAV file (16 kHz, 16-bit, mono)
    const std::string b = "----soul" + std::to_string(esp_random());
    std::string body;
    body += "--" + b + "\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\ngpt-transcribe\r\n";
    body += "--" + b + "\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\n" + (v->ro ? "ro" : "en") + "\r\n";
    body += "--" + b + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"soul.wav\"\r\nContent-Type: audio/wav\r\n\r\n";
    const uint32_t data = (uint32_t)(v->pcm.size() * 2);
    const uint8_t hdr[44] = {'R', 'I', 'F', 'F', (uint8_t)(data + 36), (uint8_t)((data + 36) >> 8), (uint8_t)((data + 36) >> 16),
                             (uint8_t)((data + 36) >> 24), 'W', 'A', 'V', 'E', 'f', 'm', 't', ' ', 16, 0, 0, 0, 1, 0, 1, 0,
                             0x80, 0x3E, 0, 0, 0x00, 0x7D, 0, 0, 2, 0, 16, 0, 'd', 'a', 't', 'a', (uint8_t)data,
                             (uint8_t)(data >> 8), (uint8_t)(data >> 16), (uint8_t)(data >> 24)};
    body.append((const char*)hdr, 44);
    body.append((const char*)v->pcm.data(), data);
    body += "\r\n--" + b + "--\r\n";
    HttpRequest rq;
    rq.url = "https://api.openai.com/v1/audio/transcriptions";
    rq.headers = {{"content-type", "multipart/form-data; boundary=" + b}, {"authorization", "Bearer " + cfg.openaiKey}};
    rq.body.swap(body);
    rq.timeoutMs = 20000;
    std::string resp;
    const int st = httpsPost(rq, resp, err);
    wipe(rq.headers[1].second);
    if (err == AiErr::None) {
      if (st != 200) err = st == 401 ? AiErr::BadKey : st == 429 ? AiErr::RateLimited : AiErr::Upstream;
      else {
        JsonDocument d;
        if (!deserializeJson(d, resp)) text = d["text"] | "";
      }
    }
  }
  delete v;
  Lock l;
  voiceText = text;
  voiceErr = err;
  voiceReady = true;
}
#endif

// --------------------------------------------------------------- task ---

void netTask(void*) {
  loadSecrets();
  WiFi.persistent(false);  // we keep the credentials ourselves
  connectSta();
  bool timeStarted = false;
  uint32_t lastPublish = 0;
  for (;;) {
    if (portalWanted && !portalUp) portalStart();
    if (!portalWanted && portalUp) portalStop();
    if (portalUp) {
      dns.processNextRequest();
      server.handleClient();
    }
    if (forget) {
      forget = false;
      WiFi.disconnect(true);
      wipe(pass);
      ssid.clear();
      Preferences p;
      p.begin("soulkey", false);
      p.remove("ssid");
      p.remove("pass");
      p.end();
    }
    if (reconnect) {
      reconnect = false;
      WiFi.disconnect(false);
      connectSta();
      timeStarted = false;
    }
    if (!timeStarted && WiFi.status() == WL_CONNECTED) {
      configTzTime(tz.c_str(), "pool.ntp.org", "time.cloudflare.com");
      timeStarted = true;
    }
    AiJob* job = nullptr;
    if (xQueueReceive(jobs, &job, 0) == pdTRUE && job) {
      busy = true;
      AiConfig c;
      {
        Lock l;
        c = cfg;
      }
      AiOutcome o = backendFor(c.mode).ask(c, *job, netLocalTime());
      wipe(c.anthropicKey);
      wipe(c.openaiKey);
      delete job;
      {
        Lock l;
        answer = o;
        answerReady = true;
      }
      busy = false;
    }
#if SUFLET_VOICE
    VoiceJob* vj = nullptr;
    if (voiceQ && xQueueReceive(voiceQ, &vj, 0) == pdTRUE && vj) transcribe(vj);
#endif
    if (millis() - lastPublish > 500) {
      lastPublish = millis();
      publish();
    }
    vTaskDelay(pdMS_TO_TICKS(portalUp ? 5 : 40));
  }
}

}  // namespace

void netBegin(const char* ap, const std::string& id) {
  apName = ap;
  deviceId = id;
  mtx = xSemaphoreCreateMutex();
  jobs = xQueueCreate(2, sizeof(AiJob*));
#if SUFLET_VOICE
  voiceQ = xQueueCreate(1, sizeof(void*));
#endif
  // core 0, next to the Wi-Fi/BLE stacks; TLS needs a big stack
  xTaskCreatePinnedToCore(netTask, "soul-net", 12288, nullptr, 3, nullptr, 0);
}

NetInfo netInfo() {
  Lock l;
  NetInfo n = info;
  return n;
}

void netStartPortal() { portalWanted = true; }
void netStopPortal() { portalWanted = false; }
void netForgetWifi() { forget = true; }

void netSetKey(AiMode mode, const std::string& key) {
  Preferences p;
  p.begin("soulkey", false);
  Lock l;
  if (mode == AiMode::Claude) {
    cfg.anthropicKey = key;
    p.putString("claude", key.c_str());
  } else if (mode == AiMode::ChatGpt) {
    cfg.openaiKey = key;
    p.putString("openai", key.c_str());
  }
  p.end();
}

void netForgetKeys() {
  Preferences p;
  p.begin("soulkey", false);
  p.remove("claude");
  p.remove("openai");
  p.end();
  Lock l;
  wipe(cfg.anthropicKey);
  wipe(cfg.openaiKey);
}

void netSetMode(AiMode mode) {
  {
    Lock l;
    if (cfg.mode == mode) return;
    cfg.mode = mode;
  }
  Preferences p;
  p.begin("soulkey", false);
  p.putUChar("mode", (uint8_t)mode);
  p.end();
}

bool netAsk(const AiJob& job) {
  if (!jobs || busy) return false;
  AiJob* j = new AiJob(job);
  if (xQueueSend(jobs, &j, 0) != pdTRUE) {
    delete j;
    return false;
  }
  return true;
}

bool netPollAnswer(AiOutcome& out) {
  Lock l;
  if (!answerReady) return false;
  out = answer;
  answer = AiOutcome();
  answerReady = false;
  return true;
}

bool netPollPortalSettings(std::string& name) {
  Lock l;
  if (!portalNameReady) return false;
  name = portalName;
  portalNameReady = false;
  return true;
}

uint32_t netLocalTime() {
  const time_t now = time(nullptr);
  if (now < 1735689600) return 0;  // before 2025: NTP has not answered yet
  struct tm lt;
  localtime_r(&now, &lt);
  // "local epoch": the local wall time counted as if it were UTC (like the RTC)
  const int Y = lt.tm_year + 1900, M = lt.tm_mon + 1, D = lt.tm_mday;
  const int y = Y - (M <= 2), era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (M + (M > 2 ? -3 : 9)) + 2) / 5 + D - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  const long days = era * 146097L + (long)doe - 719468L;
  return (uint32_t)(days * 86400L + lt.tm_hour * 3600L + lt.tm_min * 60L + lt.tm_sec);
}

bool netTranscribe(const int16_t* pcm, size_t samples, bool ro) {
#if SUFLET_VOICE
  if (!voiceQ || !samples) return false;
  VoiceJob* v = new VoiceJob();
  v->pcm.assign(pcm, pcm + samples);
  v->ro = ro;
  if (xQueueSend(voiceQ, &v, 0) != pdTRUE) {
    delete v;
    return false;
  }
  return true;
#else
  (void)pcm;
  (void)samples;
  (void)ro;
  return false;
#endif
}

bool netPollVoice(std::string& text, AiErr& err) {
#if SUFLET_VOICE
  Lock l;
  if (!voiceReady) return false;
  text = voiceText;
  err = voiceErr;
  voiceReady = false;
  return true;
#else
  (void)text;
  (void)err;
  return false;
#endif
}
