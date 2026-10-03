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

#include <atomic>
#include <vector>

#include "WifiRoam.h"
#include "board.h"
#include "cloud.h"

using namespace suflet;

#ifndef SUFLET_DEFAULT_TZ
#define SUFLET_DEFAULT_TZ "EET-2EEST,M3.5.0/3,M10.5.0/4"  // Romania (POSIX TZ)
#endif
#ifndef SUFLET_VOICE
#define SUFLET_VOICE 0
#endif
// the internet check after every join (docs/09 §1.3): plain HTTP, answers 204 when the internet is there
#ifndef SUFLET_PROBE_URL
#define SUFLET_PROBE_URL "http://connectivitycheck.gstatic.com/generate_204"
#endif

namespace {

constexpr size_t kMaxBody = 96 * 1024;
constexpr uint32_t kTimeoutMs = 25000;

SemaphoreHandle_t mtx = nullptr;
QueueHandle_t jobs = nullptr;
NetInfo info;
std::string apName, apPass, deviceId;
bool portalWanted = false, portalUp = false, forget = false;
bool answerReady = false;
AiOutcome answer;
std::string portalName;
bool portalNameReady = false;
volatile bool busy = false;

// secrets and Wi-Fi (loaded on the network task; never printed)
std::string tz = SUFLET_DEFAULT_TZ;
AiConfig cfg;

// On the go (docs/09-EVERYWHERE.md): the saved networks and the roamer. Owned by
// the network task; other tasks hand it networks through `adds` under the lock.
WifiBook book;
WifiRoamer roamer;
std::vector<WifiNet> adds;               // networks typed on SOUL, waiting for the network task
std::vector<ScanHit> portalHits;         // the portal's scan: answers the roamer while the access point is up
std::atomic<bool> kickWanted{false};     // search fast now (OsCmd::WifiKick)
std::atomic<bool> online{false};         // joined AND the internet answers (cloud.cpp waits for it)
std::atomic<int> discReason{0};          // the last disconnect reason from the Wi-Fi driver (event task)
std::string joinedSsid;                  // the SSID joined now, as on the air
std::string lastGood;                    // the saved network that last reached the internet (NVS "wlast")

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

void saveBook() {
  const std::string b = book.save();
  Preferences p;
  p.begin("soulkey", false);
  p.putBytes("wifis", b.data(), b.size());
  p.remove("ssid");  // 1.4: one network in "ssid" / "pass", moved into the book
  p.remove("pass");
  p.end();
  soulFlashWritten();
}

void loadSecrets() {
  Preferences p;
  p.begin("soulkey", true);
  bool migrate = false;
  {
    const size_t n = p.getBytesLength("wifis");
    std::string b(n, '\0');
    if (n) p.getBytes("wifis", &b[0], n);
    if (!n || !book.load(b)) {
      WifiNet old;  // firmware 1.4 kept one network: it becomes "Home"
      old.ssid = p.getString("ssid", "").c_str();
      old.pass = p.getString("pass", "").c_str();
      old.kind = WifiKind::Home;
      old.prio = wifiDefaultPrio(WifiKind::Home);
      migrate = book.add(old) >= 0;
      wipe(old.pass);
    }
    wipe(b);
  }
  lastGood = p.getString("wlast", "").c_str();
  tz = p.getString("tz", SUFLET_DEFAULT_TZ).c_str();
  cfg.anthropicKey = p.getString("claude", "").c_str();
  cfg.openaiKey = p.getString("openai", "").c_str();
  cfg.relayUrl = p.getString("cloud", "").c_str();
  cfg.claudeModel = p.getString("cmodel", "claude-opus-5-5").c_str();
  cfg.openaiModel = p.getString("omodel", "gpt-6-luna").c_str();
  cfg.mode = (AiMode)p.getUChar("mode", 0);
  p.end();
  cfg.deviceId = deviceId;
  cloudSetBase(cfg.relayUrl);
  if (migrate) saveBook();
}

std::string savedList() {  // the names, best first: "Home · Ana’s iPhone"
  std::vector<int> ix;
  for (int i = 0; i < book.count(); ++i) ix.push_back(i);
  for (size_t a = 1; a < ix.size(); ++a)
    for (size_t b = a; b > 0 && book.at(ix[b]).prio > book.at(ix[b - 1]).prio; --b) std::swap(ix[b], ix[b - 1]);
  std::string o;
  for (int i : ix) o += (o.empty() ? "" : " \u00B7 ") + book.at(i).ssid;
  return o;
}

void publish() {  // what the UI may know (never the secrets themselves)
  Lock l;
  const bool link = WiFi.status() == WL_CONNECTED;
  const NetState st = roamer.state();
  const int cur = roamer.current();
  info.configured = book.count() > 0;
  info.saved = book.count();
  info.savedList = savedList();
  info.linkUp = link;
  info.connected = link && (st == NetState::Online || st == NetState::Checking);
  info.connecting = st == NetState::Joining || st == NetState::Checking;
  info.searching = st == NetState::Searching;
  info.captive = link && st == NetState::Captive;
  info.noInternet = link && st == NetState::NoInternet;
  info.hotspot = cur >= 0 && cur < book.count() && book.at(cur).kind == WifiKind::Hotspot;
  info.ssid = link ? joinedSsid : (cur >= 0 && cur < book.count() ? book.at(cur).ssid : std::string());
  info.ip = link ? WiFi.localIP().toString().c_str() : "";
  info.rssi = link ? WiFi.RSSI() : 0;
  info.wifiFail = (int)roamer.lastFail();
  info.failSsid = roamer.lastFailNet() >= 0 && roamer.lastFailNet() < book.count() ? book.at(roamer.lastFailNet()).ssid : "";
  online = info.connected && st == NetState::Online;
  info.portal = portalUp;
  info.apName = apName;
  info.apPass = portalUp ? apPass : std::string();
  info.portalUrl = "http://192.168.4.1";
  info.keyClaude = !cfg.anthropicKey.empty();
  info.keyOpenai = !cfg.openaiKey.empty();
  info.relay = !cfg.relayUrl.empty();  // cloudFill() adds a built-in SOUL Cloud address
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
  c.method = rq.get ? HTTP_METHOD_GET : HTTP_METHOD_POST;
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
  if (!rq.get) esp_http_client_set_post_field(h, rq.body.data(), (int)rq.body.size());
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

// SOUL Cloud turns go over its WebSocket (src/cloud.cpp, docs/07 §6.6). This
// backend only runs when that socket is not up: SOUL Cloud has no HTTPS turn
// endpoint (the legacy /v1/ask relay is dev-only), so with a key of your own
// on SOUL it takes the survival path (B1), else it says "network" and SoulOS's
// on-device rules answer (§4.3).
struct CloudBackend : DirectBackend {
  const char* name() const override { return "cloud"; }
  AiOutcome ask(const AiConfig& c, const AiJob& job, uint32_t now) override {
    if (!c.anthropicKey.empty() || !c.openaiKey.empty()) {
      AiConfig conf = c;
      conf.mode = !c.anthropicKey.empty() ? AiMode::Claude : AiMode::ChatGpt;
      return DirectBackend::ask(conf, job, now);
    }
    AiOutcome o;
    o.err = AiErr::Network;
    return o;
  }
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

std::string scanned;  // the networks around, scanned before the access point starts

std::string scanOptions() {
  if (!scanned.empty()) return scanned;
  std::string o;
  portalHits.clear();
  const int n = WiFi.scanNetworks(false, false);
  for (int i = 0; i < n; ++i) {
    const std::string s = WiFi.SSID(i).c_str();
    if (s.empty()) continue;
    portalHits.push_back({s, (int)WiFi.RSSI(i)});
    if (i < 20) o += "<option value=\"" + htmlEsc(s) + "\">" + htmlEsc(s) + " (" + std::to_string(WiFi.RSSI(i)) + " dBm)</option>";
  }
  WiFi.scanDelete();
  scanned = o;
  return o;
}

const char* kStyle =
    "<style>body{font-family:system-ui,sans-serif;background:#000;color:#FFF0C8;max-width:30em;margin:auto;padding:1em}"
    "h1{font-weight:600}h2{font-weight:600;font-size:1.1em;margin-top:1.6em}label{display:block;margin:.9em 0 .2em;color:#c8bd9e}"
    "input,select{width:100%;box-sizing:border-box;"
    "padding:.7em;border-radius:.5em;border:1px solid #555;background:#111;color:#FFF0C8;font-size:1em}"
    "button,.btn{display:block;text-align:center;text-decoration:none;margin-top:1.2em;width:100%;padding:.9em;border:0;"
    "border-radius:2em;background:#FFB347;color:#000;font-size:1.05em;font-weight:600;box-sizing:border-box}"
    "small{color:#8a8270}.r{display:flex;gap:.6em;align-items:center}.r input{width:auto}"
    ".net{display:flex;gap:.5em;align-items:center;padding:.5em 0;border-bottom:1px solid #222}.net b{flex:1}"
    ".net select{width:auto}.net input{width:auto}.card{border:1px solid #333;border-radius:.8em;padding:.2em 1em;margin:1em 0}"
    "li{margin:.5em 0}</style>";

const char* kKindNames[4] = {"Home", "Work", "My phone's hotspot", "Other"};

std::string kindOptions(int sel) {
  std::string o;
  for (int k = 0; k < 4; ++k)
    o += "<option value=\"" + std::to_string(k) + "\"" + (k == sel ? " selected" : "") + ">" + kKindNames[k] + "</option>";
  return o;
}

std::string prioOptions(int prio) {
  static const int v[3] = {9, 5, 2};
  static const char* const n[3] = {"first", "normal", "last"};
  const int sel = prio >= 7 ? 0 : prio >= 4 ? 1 : 2;
  std::string o;
  for (int k = 0; k < 3; ++k)
    o += "<option value=\"" + std::to_string(v[k]) + "\"" + (k == sel ? " selected" : "") + ">" + n[k] + "</option>";
  return o;
}

std::string head(const char* title) {
  return std::string("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1\">"
                     "<title>") + title + "</title>" + kStyle + "</head><body>";
}

void pageRoot() {
  const std::string opts = scanOptions();
  const char* modes[] = {"No AI (offline, on the device)", "Your Anthropic key (advanced)", "Your OpenAI key (advanced)",
                         "SOUL Cloud (recommended)"};
  std::string mode;
  for (int i = 0; i < 4; ++i) {
    static const int order[4] = {3, 1, 2, 0};
    const int m = order[i];
    mode += "<option value=\"" + std::to_string(m) + "\"" + ((int)cfg.mode == m ? " selected" : "") + ">" + modes[m] + "</option>";
  }
  std::string nets;
  for (int i = 0; i < book.count(); ++i) {
    const WifiNet& n = book.at(i);
    const std::string k = std::to_string(i);
    nets += "<div class=net><b>" + htmlEsc(n.ssid) + "<br><small>" + kKindNames[(int)n.kind] +
            (n.pass.empty() ? std::string(" · open") : std::string()) +
            (joinedSsid == n.ssid && WiFi.status() == WL_CONNECTED ? " · joined now" : "") + "</small></b><select name=p" + k +
            " aria-label=priority>" + prioOptions(n.prio) + "</select><label class=r><input type=checkbox name=f" + k +
            ">forget</label></div>";
  }
  std::string page =
      head("SOUL setup") + "<h1>SOUL setup</h1>"
      "<h2>Wi-Fi networks SOUL knows</h2>" +
      (book.count() ? "<form method=post action=/nets>" + nets +
                          "<button>Save the order</button></form><p><small>SOUL joins the one marked <b>first</b> when it is "
                          "in reach, else the next it finds, and moves back by itself.</small></p>"
                    : std::string("<p><small>None yet.</small></p>")) +
      "<a class=btn href=/hotspot>Add my phone's hotspot (SOUL on the go)</a>"
      "<h2>Add a Wi-Fi network</h2><form method=post action=/save>"
      "<label>Wi-Fi network</label><select name=ssid><option value=\"\">choose…</option>" + opts +
      "</select><label>or type its name</label><input name=ssid2 autocomplete=off maxlength=32>"
      "<label>Wi-Fi password <small>(empty for an open network)</small></label><input name=pass type=password autocomplete=off>"
      "<label>It is…</label><select name=kind>" + kindOptions(0) + "</select>"
      "<button>Add this network</button></form>"
      "<h2>Who helps SOUL think?</h2><form method=post action=/save><select name=mode>" + mode +
      "</select><details" + std::string(cfg.mode == AiMode::Claude || cfg.mode == AiMode::ChatGpt ? " open" : "") +
      "><summary>Advanced: an API key kept on this SOUL</summary><label>Anthropic API key <small>" + (cfg.anthropicKey.empty() ? std::string("not set") : "set: " + htmlEsc(maskKey(cfg.anthropicKey))) +
      "</small></label><input name=claude type=password autocomplete=off placeholder=\"sk-ant-…\">"
      "<label>OpenAI API key <small>" + (cfg.openaiKey.empty() ? std::string("not set") : "set: " + htmlEsc(maskKey(cfg.openaiKey))) +
      "</small></label><input name=openai type=password autocomplete=off placeholder=\"sk-…\"></details>"
      "<label>SOUL Cloud address <small>(dev builds; SOUL signs in with its own key)</small></label><input name=cloud value=\"" +
      htmlEsc(cfg.relayUrl) + "\" placeholder=\"https://…\"><label>Time zone <small>(POSIX TZ)</small></label><input name=tz value=\"" + htmlEsc(tz) +
      "\"><label>SOUL's name <small>(optional)</small></label><input name=name maxlength=16>"
      "<div class=r><input type=checkbox name=forget id=f><label for=f>Forget the stored API keys</label></div>"
      "<button>Save</button></form><p><small>With SOUL Cloud, keys and your account live at the cloud's account page, "
      "not here. Keys typed above are kept on this SOUL only and are sent only to the AI you chose. "
      "This page never shows them back, nor any Wi-Fi password.</small></p></body></html>";
  server.send(200, "text/html; charset=utf-8", page.c_str());
}

// SOUL on the go: the phone's hotspot, step by step (docs/09 §1)
void pageHotspot() {
  std::string page =
      head("SOUL on the go") + "<h1>SOUL on the go</h1><p>Away from your Wi-Fi, SOUL uses your phone's hotspot. Save it once; "
      "SOUL then joins it by itself whenever it is on, and goes back to your home Wi-Fi when you are home.</p>"
      "<div class=card><h2>iPhone</h2><ol>"
      "<li><b>Settings › Personal Hotspot</b>: turn on <b>Allow Others to Join</b>.</li>"
      "<li>Turn on <b>Maximize Compatibility</b> (SOUL only speaks 2.4 GHz Wi-Fi).</li>"
      "<li>The hotspot's name is your iPhone's name (<b>Settings › General › About › Name</b>, e.g. “Ana’s iPhone”); "
      "the password is on the Personal Hotspot screen.</li>"
      "<li>Out and about: if SOUL does not join within a minute, open <b>Settings › Personal Hotspot</b> and keep that screen "
      "open for a few seconds (iPhone then shows the hotspot to new devices), and pick SOUL up: it looks again right away.</li></ol></div>"
      "<div class=card><h2>Android</h2><ol>"
      "<li><b>Settings › Network &amp; internet › Hotspot &amp; tethering › Wi-Fi hotspot</b> (the names differ a little by brand).</li>"
      "<li>Note the <b>hotspot name</b> and <b>password</b>; set the band to <b>2.4 GHz</b> (or “2.4 and 5 GHz” / “Extend compatibility”).</li>"
      "<li>Turn off <b>Turn off hotspot automatically</b> if you want SOUL to stay online while your phone is in your pocket.</li></ol></div>"
      "<form method=post action=/save><input type=hidden name=kind value=2>"
      "<label>Hotspot name <small>(exactly as on the phone; a ’ or ' both work)</small></label><input name=ssid2 autocomplete=off maxlength=32 required>"
      "<label>Hotspot password</label><input name=pass type=password autocomplete=off minlength=8 maxlength=63 required>"
      "<button>Save my hotspot</button></form>"
      "<p><small>Your phone's data plan pays for what SOUL sends: a typed question and its answer are a few tens of KB; "
      "a spoken one about 100 KB. Hotel or train Wi-Fi with a login page does not work for SOUL (it cannot click “I agree”): "
      "use the hotspot there.</small></p><p><a href=/>Back to setup</a></p></body></html>";
  server.send(200, "text/html; charset=utf-8", page.c_str());
}

void bookEdited() {  // after any change to the saved networks: store, re-plan, search fast
  saveBook();
  roamer.bookChanged(millis(), WiFi.status() == WL_CONNECTED ? joinedSsid : std::string());
}

void pageNets() {
  for (int i = book.count() - 1; i >= 0; --i) {
    const std::string k = std::to_string(i);
    if (server.hasArg(("f" + k).c_str())) {
      book.remove(i);
      continue;
    }
    const int p = server.arg(("p" + k).c_str()).toInt();
    if (p >= 1 && p <= 9) book.setPrio(i, (uint8_t)p);
  }
  bookEdited();
  server.sendHeader("Location", "http://192.168.4.1/");
  server.send(303, "text/plain", "");
  publish();
}

void pageSave() {
  Preferences p;
  p.begin("soulkey", false);
  std::string s = server.arg("ssid2").c_str();
  if (s.empty()) s = server.arg("ssid").c_str();
  bool netAdded = false, netBad = false;
  if (!s.empty()) {
    WifiNet n;
    n.ssid = s;
    n.pass = server.arg("pass").c_str();
    const int k = server.hasArg("kind") ? server.arg("kind").toInt() : 0;
    n.kind = (WifiKind)(k >= 0 && k <= 3 ? k : 3);
    n.prio = wifiDefaultPrio(n.kind);
    const int i = book.find(s);
    if (i >= 0) n.prio = book.at(i).prio;  // re-typed: keep its place
    netAdded = book.add(n) >= 0;
    netBad = !netAdded;
    wipe(n.pass);
    if (netAdded) bookEdited();
  }
  if (server.hasArg("mode")) {
    const int mode = server.arg("mode").toInt();
    if (mode >= 0 && mode <= 3) {
      cfg.mode = (AiMode)mode;
      p.putUChar("mode", (uint8_t)mode);
    }
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
  if (server.hasArg("cloud")) {
    const std::string url = server.arg("cloud").c_str();
    if (url.empty() || url.compare(0, 8, "https://") == 0) {
      cfg.relayUrl = url;
      p.putString("cloud", url.c_str());
      cloudSetBase(url);
    }
  }
  p.remove("ctoken");  // rev. 1's shared cloud token: never stored again (§6.16)
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
  soulFlashWritten();
  const std::string nm = server.arg("name").c_str();
  if (!nm.empty()) {
    Lock l;
    portalName = nm.substr(0, 16);
    portalNameReady = true;
  }
  const char* msg = netBad    ? "<h1>Not saved</h1><p>A Wi-Fi name has 1 to 32 characters and a password 8 to 63 (or none for an "
                                "open network). SOUL keeps 8 networks at most: forget one first.</p><p><a href=/>Back</a></p>"
                    : netAdded ? "<h1>Saved</h1><p>SOUL knows this network now and joins it whenever it is in reach. You can add "
                                 "another one, or close this page and go back to your usual Wi-Fi.</p><p><a href=/>Back to setup</a></p>"
                               : "<h1>Saved</h1><p>You can close this page and go back to your usual Wi-Fi.</p><p><a href=/>Back</a></p>";
  server.send(200, "text/html; charset=utf-8", (head("SOUL setup") + msg + "</body></html>").c_str());
  publish();
}

void portalStart() {
  if (portalUp) return;
  char pw[9];
  snprintf(pw, sizeof pw, "%08lu", (unsigned long)(esp_random() % 100000000UL));
  apPass = pw;
  scanned.clear();
  WiFi.mode(WIFI_STA);
  scanOptions();  // scan first: with the AP up, scans are slow and phones drop the captive page
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apName.c_str(), apPass.c_str());
  dns.start(53, "*", WiFi.softAPIP());
  server.on("/", HTTP_GET, pageRoot);
  server.on("/save", HTTP_POST, pageSave);
  server.on("/nets", HTTP_POST, pageNets);
  server.on("/hotspot", HTTP_GET, pageHotspot);
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

// ------------------------------------------------------------ roaming ---
// The WifiRoamer (lib/Suflet/src/WifiRoam.*) decides; this does it with the
// ESP32 driver: async scans, joins, the internet check (docs/09 §2).

bool scanRunning = false, timeStarted = false;

esp_err_t onProbe(esp_http_client_event_t* e) {
  if (e->event_id == HTTP_EVENT_ON_DATA && e->user_data) *(size_t*)e->user_data += (size_t)e->data_len;
  return ESP_OK;
}

// GET http://connectivitycheck.gstatic.com/generate_204, redirects not followed:
// 204 = online, a page or a redirect = a login page (captive portal), nothing = no internet.
// Plain HTTP on purpose: a login page can only answer an unencrypted request.
int probeInternet(size_t& bodyLen) {
  bodyLen = 0;
  esp_http_client_config_t c = {};
  c.url = SUFLET_PROBE_URL;
  c.method = HTTP_METHOD_GET;
  c.timeout_ms = 6000;
  c.disable_auto_redirect = true;
  c.event_handler = onProbe;
  c.user_data = &bodyLen;
  esp_http_client_handle_t h = esp_http_client_init(&c);
  if (!h) return -1;
  const esp_err_t e = esp_http_client_perform(h);
  const int status = e == ESP_OK ? esp_http_client_get_status_code(h) : -1;
  esp_http_client_cleanup(h);
  return status;
}

JoinFail failFromReason(int r) {
  switch (r) {
    case WIFI_REASON_AUTH_FAIL:
    case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT:
    case WIFI_REASON_HANDSHAKE_TIMEOUT: return JoinFail::BadPassword;
    case WIFI_REASON_NO_AP_FOUND:
    case WIFI_REASON_NO_AP_FOUND_W_COMPATIBLE_SECURITY: return JoinFail::NotFound;
    default: return JoinFail::Other;
  }
}

void roamStep() {
  const uint32_t now = millis();
  {  // networks typed on SOUL (the phone's hotspot)
    std::vector<WifiNet> add;
    {
      Lock l;
      add.swap(adds);
    }
    if (!add.empty()) {
      for (WifiNet& n : add) {
        const int i = book.find(n.ssid);
        if (i >= 0) n.prio = book.at(i).prio;
        if (book.add(n) < 0) Serial.println("[net] could not save the network (invalid or 8 already saved)");
        wipe(n.pass);
      }
      bookEdited();
    }
  }
  if (kickWanted.exchange(false)) roamer.kick(now);
  const bool link = WiFi.status() == WL_CONNECTED;
  static bool wasLink = false;
  if (wasLink && !link) Serial.printf("[net] link lost (\"%s\"): searching\n", joinedSsid.c_str());
  wasLink = link;
  if (roamer.state() == NetState::Joining && !link) {  // the driver gave up on this join: why
    const int r = discReason.exchange(0);
    if (r && r != WIFI_REASON_ASSOC_LEAVE) {
      roamer.joinFailed(now, failFromReason(r));
      Serial.printf("[net] join failed: reason %d\n", r);
    }
  }
  if (scanRunning) {
    const int16_t n = WiFi.scanComplete();
    if (n == WIFI_SCAN_RUNNING) return;
    scanRunning = false;
    std::vector<ScanHit> hits;
    for (int i = 0; i < n; ++i) {
      const std::string s = WiFi.SSID(i).c_str();
      if (!s.empty()) hits.push_back({s, (int)WiFi.RSSI(i)});
    }
    WiFi.scanDelete();
    roamer.scanDone(now, hits);
  }
  const RoamCmd c = roamer.tick(now, link, link ? (int)WiFi.RSSI() : 0);
  switch (c.kind) {
    case RoamCmd::Scan:
      if (portalUp) {  // a scan would drop the phone on SOUL's access point: the portal's own scan answers
        roamer.scanDone(now, portalHits);
      } else if (WiFi.scanNetworks(true, false, false, 120) == WIFI_SCAN_FAILED) {
        roamer.scanDone(now, std::vector<ScanHit>());
      } else {
        scanRunning = true;
      }
      break;
    case RoamCmd::Join: {
      const WifiNet& n = book.at(c.net);
      WiFi.mode(portalUp ? WIFI_AP_STA : WIFI_STA);
      WiFi.setSleep(true);  // modem sleep between beacons (also required with BLE)
      WiFi.setAutoReconnect(false);  // the roamer decides where to go
      if (link) WiFi.disconnect(false);
      discReason = 0;
      joinedSsid = c.ssid;
      WiFi.begin(c.ssid.c_str(), n.pass.empty() ? nullptr : n.pass.c_str());
      timeStarted = false;
      Serial.printf("[net] joining \"%s\" (%s, priority %d)\n", c.ssid.c_str(), wifiKindName(n.kind, false), n.prio);
      break;
    }
    case RoamCmd::Probe: {
      size_t len = 0;
      const int st = probeInternet(len);
      roamer.probed(millis(), classifyProbe(st, len));
      const int cur = roamer.current();
      if (roamer.state() == NetState::Online && cur >= 0 && book.at(cur).ssid != lastGood) {
        lastGood = book.at(cur).ssid;  // written only when it changes (flash writes glitch the RGB panel)
        Preferences p;
        p.begin("soulkey", false);
        p.putString("wlast", lastGood.c_str());
        p.end();
        soulFlashWritten();
      }
      Serial.printf("[net] internet check on \"%s\": %d (%u B) -> %s\n", joinedSsid.c_str(), st, (unsigned)len,
                    netStateName(roamer.state()));
      break;
    }
    case RoamCmd::Leave:
      WiFi.disconnect(false);
      joinedSsid.clear();
      break;
    default: break;
  }
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
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);
  WiFi.onEvent(
      [](arduino_event_id_t, arduino_event_info_t i) { discReason = (int)i.wifi_sta_disconnected.reason; },
      ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
  roamer.setBook(&book);
  roamer.preferFirst(book.find(lastGood));
  uint32_t lastPublish = 0;
  for (;;) {
    if (portalWanted && !portalUp) portalStart();
    if (!portalWanted && portalUp) portalStop();
    if (portalUp) {
      dns.processNextRequest();
      server.handleClient();
    }
    if (forget) {  // every saved network
      forget = false;
      WiFi.disconnect(false);
      joinedSsid.clear();
      while (book.count()) book.remove(0);
      bookEdited();
    }
    roamStep();
    if (!timeStarted && online) {
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
void netWifiKick() { kickWanted = true; }
bool netOnline() { return online; }

bool netAddWifi(const WifiNet& n) {
  if (n.ssid.empty() || n.ssid.size() > 32 || (!n.pass.empty() && (n.pass.size() < 8 || n.pass.size() > 63))) return false;
  Lock l;
  if (adds.size() >= 4) return false;
  adds.push_back(n);
  return true;
}

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
  soulFlashWritten();
}

void netForgetKeys() {
  Preferences p;
  p.begin("soulkey", false);
  p.remove("claude");
  p.remove("openai");
  p.end();
  soulFlashWritten();
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
  soulFlashWritten();
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

int netHttpsPost(const HttpRequest& rq, std::string& body, AiErr& err) { return httpsPost(rq, body, err); }

std::string netTz() {
  Lock l;
  return tz;
}

void netSetTz(const std::string& z) {
  if (z.empty() || z.size() >= 64) return;
  {
    Lock l;
    if (z == tz) return;
    tz = z;
  }
  Preferences p;
  p.begin("soulkey", false);
  p.putString("tz", z.c_str());
  p.end();
  soulFlashWritten();
  setenv("TZ", z.c_str(), 1);
  tzset();
}

void netSetModels(const std::string& claudeModel, const std::string& openaiModel) {
  bool changed = false;
  {
    Lock l;
    if (!claudeModel.empty() && claudeModel.size() < 64 && claudeModel != cfg.claudeModel) {
      cfg.claudeModel = claudeModel;
      changed = true;
    }
    if (!openaiModel.empty() && openaiModel.size() < 64 && openaiModel != cfg.openaiModel) {
      cfg.openaiModel = openaiModel;
      changed = true;
    }
  }
  if (!changed) return;
  Preferences p;
  p.begin("soulkey", false);
  p.putString("cmodel", cfg.claudeModel.c_str());
  p.putString("omodel", cfg.openaiModel.c_str());
  p.end();
  soulFlashWritten();
}

void netFactoryReset() {
  Preferences p;
  p.begin("soulkey", false);
  p.clear();
  p.end();
  Lock l;
  wipe(cfg.anthropicKey);
  wipe(cfg.openaiKey);
  wipe(cfg.relayToken);
  // the saved networks were in "soulkey" too; the device restarts right after (ESP.restart)
}
