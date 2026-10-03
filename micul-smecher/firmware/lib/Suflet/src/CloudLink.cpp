#include "CloudLink.h"

#include <ArduinoJson.h>
#include <stdio.h>
#include <string.h>

namespace suflet {

namespace {

const char* const kCrockford = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
const char* const kDays[] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"};
const char* const kFaces[] = {"happy", "love", "wink", "excited", "thinking", "confused", "sad", "surprised", "smug", "shy"};

void envelope(JsonDocument& d, const char* t) {
  d["v"] = 1;
  d["t"] = t;
}

std::string dump(const JsonDocument& d) {
  std::string s;
  serializeJson(d, s);  // non-ASCII stays raw UTF-8 (§6.4: never \u escapes)
  return s;
}

// cut at `maxCp` code points without splitting a UTF-8 sequence (no other cleaning: user text)
std::string cutCp(const std::string& s, size_t maxCp) {
  size_t cp = 0, i = 0;
  while (i < s.size()) {
    if (cp == maxCp) return s.substr(0, i);
    const unsigned char c = (unsigned char)s[i];
    i += c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 1;
    ++cp;
  }
  return s;
}

std::string stamp(uint32_t t) {
  char b[40];
  const uint32_t days = t / 86400;
  // civil from days (Howard Hinnant)
  const int z = (int)days + 719468, era = (z >= 0 ? z : z - 146096) / 146097;
  const unsigned doe = (unsigned)(z - era * 146097);
  const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
  const int y = (int)yoe + era * 400;
  const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
  const unsigned mp = (5 * doy + 2) / 153;
  const unsigned dd = doy - (153 * mp + 2) / 5 + 1;
  const unsigned mm = mp < 10 ? mp + 3 : mp - 9;
  snprintf(b, sizeof b, "%04d-%02u-%02uT%02u:%02u", y + (mm <= 2), mm, dd, (unsigned)(t % 86400 / 3600),
           (unsigned)(t % 3600 / 60));
  return b;
}

// a card body keeps its lines ("1. flour\n2. eggs"); each line is cleaned
std::string cleanLines(const char* s, size_t maxCp, int maxLines) {
  std::string out, line;
  int n = 0;
  size_t total = 0;
  for (const char* p = s ? s : "";; ++p) {
    if (*p == '\n' || *p == 0) {
      const std::string c = cleanText(line.c_str(), maxCp);
      if (!c.empty() && n < maxLines && total + c.size() <= maxCp * 4) {
        if (n++) out += '\n';
        out += c;
        total += c.size();
      }
      line.clear();
      if (!*p) break;
    } else {
      line += *p;
    }
  }
  return out;
}

bool isCrockford(const char* s, size_t n) {
  if (strlen(s) != n) return false;
  for (size_t i = 0; i < n; ++i)
    if (!strchr(kCrockford, s[i]) || !s[i]) return false;
  return true;
}

// a number in [lo, hi] (JSON integers only)
bool intIn(JsonVariantConst v, long lo, long hi, long& out) {
  if (!v.is<long>()) return false;
  out = v.as<long>();
  return out >= lo && out <= hi;
}

bool mapPush(const char* action, JsonVariantConst args, CloudPush& p) {
  AiAction& a = p.act;
  if (!args.is<JsonObjectConst>()) return false;
  if (!strcmp(action, "alarm.set")) {
    int h, m;
    if (!parseHhmm(args["hhmm"] | "", h, m)) return false;
    a.type = AiAction::AlarmSet;
    a.hour = (uint8_t)h;
    a.minute = (uint8_t)m;
    a.days = 0;
    JsonVariantConst days = args["days"];
    if (!days.isNull() && !days.is<JsonArrayConst>()) return false;
    for (JsonVariantConst d : days.as<JsonArrayConst>()) {
      if (!d.is<const char*>()) return false;
      int k = -1;
      for (int i = 0; i < 7; ++i)
        if (!strcmp(d.as<const char*>(), kDays[i])) k = i;
      if (k < 0) return false;
      a.days |= (uint8_t)(1 << k);  // bit 0 = Monday, as AiAction.days
    }
    a.text = cleanText(args["label"] | "", 60);
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "reminder.create")) {
    const uint32_t when = parseLocalStamp(args["when"] | "");  // local wall time, may be days ahead
    const std::string text = cleanText(args["text"] | "", 300);
    if (!when || text.empty()) return false;
    a.type = AiAction::ReminderCreate;
    a.when = when;
    a.hour = (uint8_t)(when % 86400 / 3600);
    a.minute = (uint8_t)(when % 3600 / 60);
    a.text = text;
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "note.create")) {
    a.type = AiAction::NoteCreate;
    a.text = cleanText(args["text"] | "", 2000);
    if (a.text.empty()) return false;
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "timer.start")) {
    long v;
    if (!intIn(args["seconds"], 1, 24 * 3600, v)) return false;
    a.type = AiAction::TimerStart;
    a.seconds = (uint32_t)v;
    a.minutes = (uint16_t)((a.seconds + 59) / 60);
    a.text = cleanText(args["label"] | "", 60);
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "focus.start")) {
    long v;
    if (!intIn(args["minutes"], 1, 240, v)) return false;
    a.type = AiAction::FocusStart;
    a.minutes = (uint16_t)v;
    a.text = cleanText(args["label"] | "", 60);
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "answer.show")) {
    p.title = cleanText(args["title"] | "", 60);
    p.body = cleanLines(args["body"] | "", 600, 12);
    const std::string sayArg = cleanText(args["say"] | "", 200);  // older relays put it in args
    if (p.say.empty()) p.say = sayArg;
    if (p.title.empty() && p.body.empty() && p.say.empty()) return false;
    p.kind = CloudPush::Card;
    return true;
  }
  if (!strcmp(action, "item.delete")) {
    p.itemId = cleanText(args["item_id"] | "", 32);
    if (p.itemId.empty()) return false;
    p.kind = CloudPush::Delete;
    return true;
  }
  p.kind = CloudPush::Unsupported;
  return true;
}

}  // namespace

// ---------------------------------------------------------- identity ---

std::string CloudLink::deviceId(const uint8_t mac[6]) {
  char b[24];
  snprintf(b, sizeof b, "soul-%02x%02x%02x%02x%02x%02x", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return b;
}

std::string CloudLink::base64url(const uint8_t* d, size_t n) {
  static const char* const k = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  std::string o;
  for (size_t i = 0; i < n; i += 3) {
    const uint32_t v = (uint32_t)d[i] << 16 | (i + 1 < n ? (uint32_t)d[i + 1] << 8 : 0) | (i + 2 < n ? d[i + 2] : 0);
    o += k[(v >> 18) & 63];
    o += k[(v >> 12) & 63];
    if (i + 1 < n) o += k[(v >> 6) & 63];
    if (i + 2 < n) o += k[v & 63];
  }
  return o;  // unpadded: 43 chars for 32 bytes, 86 for a signature, 87 for a public key
}

bool CloudLink::base64urlDecode(const std::string& s, std::vector<uint8_t>& out) {
  out.clear();
  if (s.size() % 4 == 1) return false;
  uint32_t acc = 0;
  int bits = 0;
  for (char c : s) {
    int v;
    if (c >= 'A' && c <= 'Z') v = c - 'A';
    else if (c >= 'a' && c <= 'z') v = c - 'a' + 26;
    else if (c >= '0' && c <= '9') v = c - '0' + 52;
    else if (c == '-') v = 62;
    else if (c == '_') v = 63;
    else return false;
    acc = acc << 6 | (uint32_t)v;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out.push_back((uint8_t)(acc >> bits));
    }
  }
  return true;
}

std::string CloudLink::hostOf(const std::string& base) {
  std::string h;
  for (char c : base) h += (char)(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  const size_t scheme = h.find("://");
  if (scheme != std::string::npos) h = h.substr(scheme + 3);
  const size_t slash = h.find('/');
  if (slash != std::string::npos) h = h.substr(0, slash);
  if (h.size() > 4 && h.compare(h.size() - 4, 4, ":443") == 0) h.resize(h.size() - 4);
  return h;
}

std::string CloudLink::authMessage(const std::string& host, const std::string& id, const std::string& nonce) {
  return "soul-auth-v1\n" + host + "\n" + id + "\n" + nonce;
}

std::string CloudLink::challengeBody(const std::string& id) {
  JsonDocument d;
  d["device_id"] = id;
  return dump(d);
}

static void readError(const JsonDocument& d, CloudAuth& out) {
  out.code = d["error"]["code"] | "";
  out.retryMs = d["error"]["retry_ms"] | -1;
}

bool CloudLink::parseChallenge(int status, const char* body, size_t n, CloudAuth& out) {
  out = CloudAuth();
  out.status = status;
  JsonDocument d;
  const bool json = body && n && !deserializeJson(d, body, n, DeserializationOption::NestingLimit(4)) &&
                    d.is<JsonObject>();
  if (status != 200) {
    if (json) readError(d, out);
    return false;
  }
  if (!json) return false;
  const char* nonce = d["nonce"] | "";
  const size_t len = strlen(nonce);
  if (len < 16 || len > 64) return false;
  for (size_t i = 0; i < len; ++i) {
    const char c = nonce[i];
    if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_'))
      return false;
  }
  out.nonce = nonce;
  return true;
}

std::string CloudLink::authBody(const std::string& id, const std::string& pub, const std::string& nonce,
                                const std::string& sig, const char* fw, const char* hw, bool reset) {
  JsonDocument d;
  d["device_id"] = id;
  d["pub"] = pub;
  d["nonce"] = nonce;
  d["sig"] = sig;
  d["fw"] = fw;
  d["hw"] = hw;
  d["reset"] = reset;
  return dump(d);
}

bool CloudLink::parseAuth(int status, const char* body, size_t n, CloudAuth& out, bool allowPlainWs) {
  out = CloudAuth();
  out.status = status;
  JsonDocument d;
  const bool json = body && n && !deserializeJson(d, body, n, DeserializationOption::NestingLimit(6)) &&
                    d.is<JsonObject>();
  if (status != 200) {
    if (json) readError(d, out);
    return false;
  }
  if (!json) return false;
  const char* tok = d["token"] | "";
  const size_t tl = strlen(tok);
  if (strncmp(tok, "sdt_", 4) != 0 || tl < 20 || tl > 100) return false;
  out.wsUrl = d["ws_url"] | "";
  const bool wss = out.wsUrl.compare(0, 6, "wss://") == 0;
  const bool loopWs = allowPlainWs && (out.wsUrl.compare(0, 15, "ws://127.0.0.1:") == 0 ||
                                       out.wsUrl.compare(0, 15, "ws://localhost:") == 0);
  if (!wss && !loopWs) {  // never a plain-text socket on a device
    out.wsUrl.clear();
    return false;
  }
  out.token = tok;
  out.expiresIn = d["expires_in"] | 0u;
  out.serverTime = d["server_time"] | 0u;
  out.state = d["state"] | "";
  out.owner = cleanText(d["owner"] | "", 40);
  if (d["trial"].is<JsonObject>()) out.trialLeft = d["trial"]["left"] | -1;
  return true;
}

CloudLink::AuthRetry CloudLink::authRetry(const CloudAuth& a, int failures, float rnd) {
  AuthRetry r;
  if (failures < 1) failures = 1;
  if (a.status == 400) {  // bad_request / bad_nonce: a new challenge once, then back off
    r.kind = failures == 1 ? AuthRetry::NewChallenge : AuthRetry::Backoff;
    r.waitMs = failures == 1 ? 0 : backoffMs(failures, rnd);
    return r;
  }
  if (a.status == 401) {  // bad_signature: back off 1 -> 60 min
    uint32_t mins = 1;
    for (int i = 1; i < failures && mins < 60; ++i) mins *= 2;
    if (mins > 60) mins = 60;
    r.kind = AuthRetry::Backoff;
    r.waitMs = mins * 60000u;
    r.showProblem = failures >= 3;
    return r;
  }
  if (a.status == 403) {  // not_enrolled / key_revoked: brain E / B1, ask again every 6 h
    r.kind = a.code == "key_revoked" ? AuthRetry::KeyRevoked : AuthRetry::NotEnrolled;
    r.waitMs = 6u * 3600u * 1000u;
    r.showProblem = true;
    return r;
  }
  if (a.status == 429) {
    r.kind = AuthRetry::Wait;
    r.waitMs = a.retryMs > 0 ? (uint32_t)a.retryMs : 60000u;
    return r;
  }
  r.kind = AuthRetry::Backoff;  // network, 5xx, an unreadable answer
  r.waitMs = backoffMs(failures, rnd);
  return r;
}

// ------------------------------------------------------------ frames up ---

std::string CloudLink::hello(const CloudHello& h) {
  JsonDocument d;
  envelope(d, "hello");
  d["proto"].to<JsonArray>().add(1);
  d["fw"] = h.fw;
  d["hw"] = h.hw;
  JsonArray caps = d["caps"].to<JsonArray>();
  if (h.caps.empty()) {
    for (const char* c : {"text", "cards", "alarms", "reminders", "notes", "timers", "focus", "inbox", "confirm"})
      caps.add(c);
  } else {
    for (const std::string& c : h.caps) caps.add(c);
  }
  d["after"] = h.after;
  d["lang"] = h.lang == "ro" ? "ro" : "en";
  d["brain_local"] = h.brainLocal;
  d["power"] = h.power == "battery" ? "battery" : "usb";
  if (!h.tzPosix.empty()) d["tz_posix"] = h.tzPosix;
  return dump(d);
}

std::string CloudLink::ask(const std::string& id, const std::string& text, const char* lang, const std::string& conv,
                           int timerLeftMin, const std::vector<std::string>& unsynced) {
  JsonDocument d;
  envelope(d, "ask");
  d["id"] = id.substr(0, 24);
  d["text"] = cutCp(text, 2000);
  d["lang"] = lang;
  if (conv.empty()) d["conv"] = nullptr;
  else d["conv"] = conv;
  JsonObject ctx = d["ctx"].to<JsonObject>();
  if (timerLeftMin >= 0) ctx["timer_left_min"] = timerLeftMin;
  else ctx["timer_left_min"] = nullptr;
  JsonArray un = ctx["unsynced"].to<JsonArray>();
  for (const std::string& f : unsynced) {
    if (un.size() >= 10) break;
    JsonDocument it;
    if (deserializeJson(it, f) || strcmp(it["t"] | "", "item.add") != 0) continue;
    JsonObject o = un.add<JsonObject>();
    o["action"] = it["action"];
    o["args"] = it["args"];
  }
  std::string s = dump(d);
  if (s.size() > kMaxOut) {  // the unsynced context is a nice-to-have: never let it push the turn over 10 KB
    un.clear();
    s = dump(d);
  }
  return s;
}

std::string CloudLink::ack(uint32_t seq, bool ok, const char* err) {
  JsonDocument d;
  envelope(d, "ack");
  d["seq"] = seq;
  d["ok"] = ok;
  if (!ok && err && *err) d["err"] = err;
  return dump(d);
}

std::string CloudLink::abort(const std::string& re) {
  JsonDocument d;
  envelope(d, "abort");
  d["re"] = re;
  return dump(d);
}

std::string CloudLink::status(int rssi, int battery, const char* power, const char* fw, uint32_t freeHeap, bool awake) {
  JsonDocument d;
  envelope(d, "status");
  d["rssi"] = rssi;
  if (battery >= 0 && battery <= 100) d["battery"] = battery;
  d["power"] = power && !strcmp(power, "battery") ? "battery" : "usb";
  d["fw"] = fw;
  d["free_heap"] = freeHeap;
  d["awake"] = awake;
  return dump(d);
}

std::string CloudLink::itemAdd(const std::string& cid, const AiAction& a, uint32_t created) {
  JsonDocument d;
  envelope(d, "item.add");
  d["cid"] = cid;
  JsonObject args = d["args"].to<JsonObject>();
  char hm[8];
  snprintf(hm, sizeof hm, "%02u:%02u", a.hour % 24u, a.minute % 60u);
  switch (a.type) {
    case AiAction::AlarmSet: {
      d["action"] = "alarm.set";
      args["hhmm"] = hm;
      JsonArray days = args["days"].to<JsonArray>();
      for (int i = 0; i < 7; ++i)
        if (a.days & (1 << i)) days.add(kDays[i]);
      args["label"] = cutCp(a.text, 60);
      break;
    }
    case AiAction::ReminderCreate: {
      d["action"] = "reminder.create";
      uint32_t when = a.when;
      if (!when && created) {
        when = created - created % 86400 + a.hour * 3600u + a.minute * 60u;
        if (a.tomorrow || when <= created) when += 86400;
      }
      args["when"] = stamp(when);
      args["text"] = cutCp(a.text, 300);
      break;
    }
    case AiAction::NoteCreate:
      d["action"] = "note.create";
      args["text"] = cutCp(a.text, 2000);
      args["tags"].to<JsonArray>();
      break;
    case AiAction::TimerStart:
      d["action"] = "timer.start";
      args["seconds"] = a.seconds ? a.seconds : a.minutes * 60u;
      args["label"] = cutCp(a.text, 60);
      break;
    case AiAction::FocusStart:
      d["action"] = "focus.start";
      args["minutes"] = a.minutes;
      args["label"] = cutCp(a.text, 60);
      break;
  }
  d["created"] = stamp(created);
  return dump(d);
}

std::string CloudLink::itemState(const std::string& itemId, const std::string& cid, const char* state, uint32_t at) {
  JsonDocument d;
  envelope(d, "item.state");
  if (!itemId.empty()) d["item_id"] = itemId.substr(0, 32);
  else d["cid"] = cid;
  d["state"] = state;
  d["at"] = at;
  return dump(d);
}

std::string CloudLink::inboxAdd(const std::string& cid, const std::string& text, const char* to) {
  JsonDocument d;
  envelope(d, "inbox.add");
  d["cid"] = cid;
  d["text"] = cutCp(text, 1000);
  d["to"] = to && (!strcmp(to, "claude") || !strcmp(to, "chatgpt")) ? to : "any";
  return dump(d);
}

std::string CloudLink::pairAnswer(const std::string& pid, bool ok) {
  JsonDocument d;
  envelope(d, ok ? "pair.ok" : "pair.no");
  d["pid"] = pid;
  return dump(d);
}

std::string CloudLink::connectors(bool paused) {
  JsonDocument d;
  envelope(d, "connectors");
  d["paused"] = paused;
  return dump(d);
}

std::string CloudLink::sleep(uint32_t wakeAt) {
  JsonDocument d;
  envelope(d, "sleep");
  d["wake_at"] = wakeAt;
  return dump(d);
}

std::string CloudLink::cid(uint32_t r1, uint32_t r2) {
  char b[20];
  snprintf(b, sizeof b, "%08lx%08lx", (unsigned long)r1, (unsigned long)r2);
  return b;
}

// ---------------------------------------------------------- frames down ---

AiErr CloudLink::errFromCode(const std::string& c) {
  if (c == "bad_key") return AiErr::BadKey;
  if (c == "no_key" || c == "unpaired") return AiErr::NoKey;
  if (c == "rate_limited") return AiErr::RateLimited;
  if (c == "quota" || c == "allowance") return AiErr::Quota;
  if (c == "refused") return AiErr::Refused;
  if (c == "timeout") return AiErr::Timeout;
  if (c == "offline") return AiErr::Offline;
  if (c == "network") return AiErr::Network;
  if (c == "truncated") return AiErr::Truncated;
  return AiErr::Upstream;  // upstream, invalid, too_big, paused and anything new
}

CloudLink::Msg CloudLink::feed(const char* json, size_t n) {
  if (!json || !n || n > kMaxIn) return Msg::Bad;
  JsonDocument d;
  if (deserializeJson(d, json, n, DeserializationOption::NestingLimit(8)) || !d.is<JsonObject>()) return Msg::Bad;
  if (!d["v"].isNull() && (d["v"] | 0) != 1) return Msg::Bad;
  const char* t = d["t"] | "";
  if (!strcmp(t, "welcome")) {
    welcome = CloudWelcome();
    CloudWelcome& w = welcome;
    w.serverTime = d["server_time"] | 0u;
    w.tz = cleanText(d["tz"] | "", 64);
    w.posixTz = d["posix_tz"] | "";
    if (w.posixTz.size() > 63) w.posixTz.clear();
    w.state = d["state"] | "";
    w.owner = cleanText(d["owner"] | "", 40);
    w.brain = d["brain"] | "";
    w.voice = d["voice"] | "";
    w.lang = d["lang"] | "";
    w.quietFrom = d["quiet"]["from"] | "";
    w.quietTo = d["quiet"]["to"] | "";
    w.connectorsPaused = d["connectors_paused"] | false;
    w.askPerMin = d["limits"]["ask_per_min"] | -1;
    w.askPerDay = d["limits"]["ask_per_day"] | -1;
    w.framesPerS = d["limits"]["frames_per_s"] | -1;
    if (d["allowance"].is<JsonObject>()) {
      w.allowanceLeft = d["allowance"]["left"] | -1;
      w.allowanceRenews = d["allowance"]["renews"] | "";
    }
    if (d["trial"].is<JsonObject>()) w.trialLeft = d["trial"]["left"] | -1;
    w.modelClaude = d["models"]["claude"] | "";
    w.modelOpenai = d["models"]["openai"] | "";
    return Msg::Welcome;
  }
  if (!strcmp(t, "pairing")) {
    const char* code = d["code"] | "";
    if (!isCrockford(code, 8)) return Msg::Bad;  // shown big as XXXX-XXXX
    pairing = CloudPairing();
    pairing.code = code;
    pairing.url = d["url"] | "";
    if (pairing.url.compare(0, 8, "https://") != 0 || pairing.url.size() > 200) pairing.url.clear();
    pairing.expiresIn = d["expires_in"] | 0u;
    return Msg::Pairing;
  }
  if (!strcmp(t, "pair.confirm")) {
    const char* pid = d["pid"] | "";
    if (!*pid || strlen(pid) > 64) return Msg::Bad;
    confirm = CloudConfirm();
    confirm.pid = pid;
    confirm.name = cleanText(d["name"] | "", 40);
    confirm.hint = cleanText(d["account_hint"] | "", 80);
    confirm.expiresIn = d["expires_in"] | 120u;
    return Msg::PairConfirm;
  }
  if (!strcmp(t, "paired")) {
    owner = cleanText(d["owner"] | "", 40);
    ownerHint = cleanText(d["account_hint"] | "", 80);
    return Msg::Paired;
  }
  if (!strcmp(t, "unpaired")) {
    unpairedReason = d["reason"] | "";
    return Msg::Unpaired;
  }
  if (!strcmp(t, "replay.done") || !strcmp(t, "resync")) {
    last = d["last"] | 0u;
    return !strcmp(t, "resync") ? Msg::Resync : Msg::ReplayDone;
  }
  if (!strcmp(t, "reply")) {
    reply = CloudReply();
    reply.re = d["re"] | "";
    reply.conv = d["conv"] | "";
    reply.reply.say = cleanText(d["say"] | "", 400);
    const char* face = d["face"] | "";
    for (const char* f : kFaces)
      if (!strcmp(face, f)) reply.reply.face = f;
    reply.provider = d["provider"] | "";
    reply.brain = d["brain"] | "";
    reply.note = d["note"] | "";
    if (d["card"].is<JsonObject>()) {
      reply.title = cleanText(d["card"]["title"] | "", 60);
      reply.body = cleanLines(d["card"]["body"] | "", 600, 12);
    }
    for (JsonVariantConst c : d["chips"].as<JsonArrayConst>())
      if (reply.chips.size() < 4 && c.is<const char*>()) reply.chips.push_back(cleanText(c.as<const char*>(), 24));
    for (JsonVariantConst s : d["seqs"].as<JsonArrayConst>())
      if (reply.seqs.size() < 16 && s.is<uint32_t>()) reply.seqs.push_back(s.as<uint32_t>());
    if (d["allowance"].is<JsonObject>()) {
      reply.allowanceLeft = d["allowance"]["left"] | -1;
      reply.allowanceUnit = d["allowance"]["unit"] | "";
    }
    if (reply.reply.say.empty() && !reply.title.empty()) reply.reply.say = reply.title;
    return Msg::Reply;
  }
  if (!strcmp(t, "say.delta")) {
    deltaRe = d["re"] | "";
    deltaText = cleanText(d["text"] | "", 400);
    return Msg::SayDelta;
  }
  if (!strcmp(t, "push")) {
    push = CloudPush();
    push.seq = d["seq"] | 0u;
    push.action = d["action"] | "";
    push.itemId = cleanText(d["item_id"] | "", 32);
    if (!push.seq || push.action.empty()) return Msg::Bad;
    JsonVariantConst o = d["origin"];
    push.source = o["kind"] | "";
    push.app = o["app"] | "";
    push.by = cleanText(o["by"] | "", 24);
    push.say = cleanText(d["say"] | "", 200);
    push.priv = d["private"] | false;
    push.needsAccept = d["needs_accept"] | false;
    push.missed = d["missed"] | false;
    push.expiresAt = d["expires_at"] | 0u;
    if (!mapPush(push.action.c_str(), d["args"], push)) push.kind = CloudPush::Invalid;
    return Msg::Push;
  }
  if (!strcmp(t, "added")) {
    addedCid = d["cid"] | "";
    addedItemId = d["item_id"] | "";
    return addedCid.empty() ? Msg::Bad : Msg::Added;
  }
  if (!strcmp(t, "inbox.state")) {
    inboxPending = d["pending"] | 0;
    inboxAnswered = d["answered"] | 0;
    return Msg::InboxState;
  }
  if (!strcmp(t, "config")) {
    config = CloudConfig();
    CloudConfig& c = config;
    if ((c.hasBrain = d["brain"].is<const char*>())) c.brain = d["brain"].as<const char*>();
    if ((c.hasVoice = d["voice"].is<const char*>())) c.voice = d["voice"].as<const char*>();
    if ((c.hasLang = d["lang"].is<const char*>())) c.lang = d["lang"].as<const char*>();
    if ((c.hasName = d["name"].is<const char*>())) c.name = cleanText(d["name"].as<const char*>(), 16);
    if ((c.hasTz = d["posix_tz"].is<const char*>())) {
      c.tz = cleanText(d["tz"] | "", 64);
      c.posixTz = d["posix_tz"].as<const char*>();
      if (c.posixTz.empty() || c.posixTz.size() > 63) c.hasTz = false;
    }
    if ((c.hasQuiet = d["quiet"].is<JsonObject>())) {
      c.quietFrom = d["quiet"]["from"] | "";
      c.quietTo = d["quiet"]["to"] | "";
    }
    if ((c.hasModels = d["models"].is<JsonObject>())) {
      c.modelClaude = d["models"]["claude"] | "";
      c.modelOpenai = d["models"]["openai"] | "";
    }
    return Msg::Config;
  }
  if (!strcmp(t, "error")) {
    error = CloudError();
    error.re = d["re"] | "";
    error.code = d["code"] | "";
    error.msg = cleanText(d["msg"] | "", 120);
    error.cid = d["cid"] | "";
    error.retryMs = d["retry_ms"] | -1;
    error.err = errFromCode(error.code);
    return Msg::Error;
  }
  return Msg::Unknown;  // ota (Phase 2) and anything newer: must-ignore
}

// --------------------------------------------------------- close codes ---

CloudLink::CloseAction CloudLink::onClose(int code) {
  switch (code) {
    case 4000: return CloseAction::Restart;   // server restart: 1-5 s
    case 4401:                                 // token invalid / expired
    case 4403: return CloseAction::Reauth;     // revoked or unknown: the auth answer says which
    case 4409: return CloseAction::Replaced;   // a newer socket of this SOUL: not for 60 s
    case 4426: return CloseAction::Update;     // protocol too old: retry daily
    case 4429: return CloseAction::Wait;       // rate limited: retry_ms of the preceding error
    default: return CloseAction::Reconnect;    // 1000 / 1001 / 4400 / network: backoff
  }
}

uint32_t CloudLink::backoffMs(int attempt, float rnd) {
  uint32_t s = 1;
  for (int i = 1; i < attempt && s < 60; ++i) s *= 2;
  if (s > 60) s = 60;
  if (rnd < 0) rnd = 0;
  if (rnd > 1) rnd = 1;
  return (uint32_t)(s * 1000 * (1.0f + 0.3f * rnd));
}

}  // namespace suflet
