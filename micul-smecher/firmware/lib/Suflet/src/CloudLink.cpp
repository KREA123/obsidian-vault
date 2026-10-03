#include "CloudLink.h"

#include <ArduinoJson.h>
#include <stdio.h>
#include <string.h>

namespace suflet {

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
  return o;  // unpadded, like the cloud expects (43 chars for 32 bytes)
}

std::string CloudLink::authBody(const std::string& id, const std::string& secret, const char* fw, const char* hw) {
  JsonDocument d;
  d["device_id"] = id;
  d["secret"] = secret;
  d["fw"] = fw;
  d["hw"] = hw;
  std::string s;
  serializeJson(d, s);
  return s;
}

bool CloudLink::parseAuth(int status, const char* body, size_t n, CloudAuth& out) {
  out = CloudAuth();
  if (status != 200 || !body || !n) return false;
  JsonDocument d;
  if (deserializeJson(d, body, n, DeserializationOption::NestingLimit(6)) || !d.is<JsonObject>()) return false;
  const char* tok = d["token"] | "";
  if (strncmp(tok, "sdt_", 4) != 0 || strlen(tok) < 20 || strlen(tok) > 200) return false;
  out.token = tok;
  out.wsUrl = d["ws_url"] | "";
  out.expiresIn = d["expires_in"] | 0u;
  out.serverTime = d["server_time"] | 0u;
  out.paired = d["paired"] | false;
  out.owner = cleanText(d["owner"] | "", 40);
  if (d["pairing"].is<JsonObject>()) {
    out.pairCode = d["pairing"]["code"] | "";
    out.pairUrl = d["pairing"]["url"] | "";
    out.pairExpires = d["pairing"]["expires_in"] | 0u;
  }
  return out.wsUrl.compare(0, 6, "wss://") == 0;  // never a plain-text socket
}

// ------------------------------------------------------------ frames up ---

static void envelope(JsonDocument& d, const char* t) {
  d["v"] = 1;
  d["t"] = t;
}
static std::string dump(const JsonDocument& d) {
  std::string s;
  serializeJson(d, s);
  return s;
}

std::string CloudLink::hello(const char* fw, const char* hw, const char* brainName, const char* lng, const char* tzs) const {
  JsonDocument d;
  envelope(d, "hello");
  d["proto"].to<JsonArray>().add(1);
  d["fw"] = fw;
  d["hw"] = hw;
  JsonArray caps = d["caps"].to<JsonArray>();
  for (const char* c : {"text", "cards", "alarms", "reminders", "notes", "timers", "focus", "inbox"}) caps.add(c);
  d["after"] = lastSeq;
  d["brain"] = brainName;
  d["lang"] = lng;
  d["tz"] = tzs;
  return dump(d);
}

std::string CloudLink::ask(const std::string& id, const std::string& text, const char* lng, const AiContext& c) const {
  JsonDocument d;
  envelope(d, "ask");
  d["id"] = id;
  d["text"] = text.size() > 2000 ? text.substr(0, 2000) : text;
  d["lang"] = lng;
  JsonObject ctx = d["ctx"].to<JsonObject>();
  ctx["alarms"] = c.alarms;
  ctx["reminders"] = c.reminders;
  ctx["timer_left_min"] = c.timerLeftMin;
  ctx["notes"] = c.notes;
  return dump(d);
}

std::string CloudLink::ack(uint32_t seq, bool ok, const char* err) const {
  JsonDocument d;
  envelope(d, "ack");
  d["seq"] = seq;
  d["ok"] = ok;
  if (err) d["err"] = err;
  return dump(d);
}

std::string CloudLink::abort(const std::string& re) const {
  JsonDocument d;
  envelope(d, "abort");
  d["re"] = re;
  return dump(d);
}

std::string CloudLink::status(int battery, int rssi, bool awake, const char* fw, uint32_t freeHeap) const {
  JsonDocument d;
  envelope(d, "status");
  if (battery >= 0) d["battery"] = battery;
  d["rssi"] = rssi;
  d["awake"] = awake;
  d["fw"] = fw;
  d["free_heap"] = freeHeap;
  return dump(d);
}

static std::string stamp(uint32_t t) {
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

std::string CloudLink::itemAdd(const std::string& cid, const AiAction& a, uint32_t created) const {
  JsonDocument d;
  envelope(d, "item.add");
  d["cid"] = cid;
  JsonObject args = d["args"].to<JsonObject>();
  static const char* const kD[] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"};
  char hm[8];
  snprintf(hm, sizeof hm, "%02u:%02u", a.hour, a.minute);
  switch (a.type) {
    case AiAction::AlarmSet: {
      d["action"] = "alarm.set";
      args["hhmm"] = hm;
      JsonArray days = args["days"].to<JsonArray>();
      for (int i = 0; i < 7; ++i)
        if (a.days & (1 << i)) days.add(kD[i]);
      args["label"] = a.text;
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
      args["text"] = a.text;
      break;
    }
    case AiAction::NoteCreate:
      d["action"] = "note.create";
      args["text"] = a.text;
      args["tags"].to<JsonArray>();
      break;
    case AiAction::TimerStart:
      d["action"] = "timer.start";
      args["seconds"] = a.seconds ? a.seconds : a.minutes * 60u;
      args["label"] = a.text;
      break;
    case AiAction::FocusStart:
      d["action"] = "focus.start";
      args["minutes"] = a.minutes;
      args["label"] = a.text;
      break;
  }
  d["created"] = stamp(created);
  return dump(d);
}

std::string CloudLink::inboxAdd(const std::string& cid, const std::string& text, const char* to) const {
  JsonDocument d;
  envelope(d, "inbox.add");
  d["cid"] = cid;
  d["text"] = text.size() > 1000 ? text.substr(0, 1000) : text;
  d["to"] = to;
  return dump(d);
}

// ---------------------------------------------------------- frames down ---

AiErr CloudLink::errFromCode(const std::string& c) {
  if (c == "bad_key" || c == "unpaired") return AiErr::BadKey;
  if (c == "rate_limited") return AiErr::RateLimited;
  if (c == "quota" || c == "allowance") return AiErr::Quota;
  if (c == "refused") return AiErr::Refused;
  if (c == "no_key") return AiErr::NoKey;
  if (c == "timeout") return AiErr::Timeout;
  if (c == "offline") return AiErr::Offline;
  if (c == "network") return AiErr::Network;
  if (c == "truncated") return AiErr::Truncated;
  return AiErr::Upstream;
}

// a card body keeps its lines ("1. flour\n2. eggs"); each line is cleaned
static std::string cleanLines(const char* s, size_t maxCp, int maxLines) {
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

static const char* const kFaces[] = {"happy", "love", "wink", "excited", "thinking", "confused", "sad", "surprised", "smug", "shy"};

static bool mapPush(const char* action, JsonVariantConst args, CloudPush& p) {
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
    static const char* const kD[] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"};
    for (JsonVariantConst d : days.as<JsonArrayConst>()) {
      if (!d.is<const char*>()) return false;
      int k = -1;
      for (int i = 0; i < 7; ++i)
        if (!strcmp(d.as<const char*>(), kD[i])) k = i;
      if (k < 0) return false;
      a.days |= (uint8_t)(1 << k);
    }
    a.text = cleanText(args["label"] | "", 40);
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "reminder.create")) {
    const uint32_t when = parseLocalStamp(args["when"] | "");
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
    JsonVariantConst s = args["seconds"];
    if (!(s.is<long>() || s.is<double>())) return false;
    const double v = s.as<double>();
    if (!(v >= 1 && v <= 24 * 3600)) return false;
    a.type = AiAction::TimerStart;
    a.seconds = (uint32_t)v;
    a.minutes = (uint16_t)((a.seconds + 59) / 60);
    a.text = cleanText(args["label"] | "", 60);
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "focus.start")) {
    JsonVariantConst s = args["minutes"];
    if (!(s.is<long>() || s.is<double>())) return false;
    const double v = s.as<double>();
    if (!(v >= 1 && v <= 240)) return false;
    a.type = AiAction::FocusStart;
    a.minutes = (uint16_t)v;
    a.text = cleanText(args["label"] | "", 60);
    p.kind = CloudPush::Act;
    return true;
  }
  if (!strcmp(action, "answer.show")) {
    p.say = cleanText(args["say"] | "", 400);
    p.title = cleanText(args["title"] | "", 60);
    p.body = cleanLines(args["body"] | "", 600, 12);
    if (p.say.empty() && p.title.empty() && p.body.empty()) return false;
    p.kind = CloudPush::Card;
    return true;
  }
  if (!strcmp(action, "item.delete")) {
    p.itemId = cleanText(args["item_id"] | "", 64);
    if (p.itemId.empty()) return false;
    p.kind = CloudPush::Delete;
    return true;
  }
  p.kind = CloudPush::Unsupported;
  return true;
}

CloudLink::Msg CloudLink::feed(const char* json, size_t n) {
  if (!json || !n || n > 16384) return Msg::Bad;  // the server promises <= 8 KB frames
  JsonDocument d;
  if (deserializeJson(d, json, n, DeserializationOption::NestingLimit(8)) || !d.is<JsonObject>()) return Msg::Bad;
  if ((d["v"] | 0) != 1) return Msg::Bad;
  const char* t = d["t"] | "";
  if (!strcmp(t, "welcome")) {
    serverTime = d["server_time"] | 0u;
    tz = d["tz"] | "";
    posixTz = d["posix_tz"] | "";
    paired = d["paired"] | false;
    owner = cleanText(d["owner"] | "", 40);
    brain = d["brain"] | "";
    limitAskPerMin = d["limits"]["ask_per_min"] | -1;
    return Msg::Welcome;
  }
  if (!strcmp(t, "pairing")) {
    const char* code = d["code"] | "";
    // 6 digits only: this is shown big on the screen
    if (strlen(code) != 6) return Msg::Bad;
    for (int i = 0; i < 6; ++i)
      if (code[i] < '0' || code[i] > '9') return Msg::Bad;
    pairCode = code;
    pairUrl = d["url"] | "";
    if (pairUrl.compare(0, 8, "https://") != 0 || pairUrl.size() > 200) pairUrl.clear();
    pairExpires = d["expires_in"] | 0u;
    paired = false;
    return Msg::Pairing;
  }
  if (!strcmp(t, "paired")) {
    paired = true;
    owner = cleanText(d["owner"] | "", 40);
    pairCode.clear();
    return Msg::Paired;
  }
  if (!strcmp(t, "unpaired")) {
    paired = false;
    owner.clear();
    return Msg::Unpaired;
  }
  if (!strcmp(t, "reply")) {
    reply = CloudReply();
    reply.re = d["re"] | "";
    reply.reply.say = cleanText(d["say"] | "", 280);
    const char* face = d["face"] | "";
    for (const char* f : kFaces)
      if (!strcmp(face, f)) reply.reply.face = f;
    reply.provider = d["provider"] | "";
    reply.brain = d["brain"] | "";
    reply.note = cleanText(d["note"] | "", 120);
    if (d["card"].is<JsonObject>()) {
      reply.title = cleanText(d["card"]["title"] | "", 60);
      reply.body = cleanLines(d["card"]["body"] | "", 600, 12);
    }
    for (JsonVariantConst s : d["seqs"].as<JsonArrayConst>())
      if (reply.seqs.size() < 8) reply.seqs.push_back(s.as<uint32_t>());
    if (d["allowance"].is<JsonObject>()) {
      reply.allowanceLeft = d["allowance"]["left"] | -1;
      reply.allowanceUnit = d["allowance"]["unit"] | "";
    }
    if (reply.reply.say.empty() && !reply.title.empty()) reply.reply.say = reply.title;
    return Msg::Reply;
  }
  if (!strcmp(t, "say.delta")) {
    deltaRe = d["re"] | "";
    deltaText = cleanText(d["text"] | "", 280);
    return Msg::SayDelta;
  }
  if (!strcmp(t, "push")) {
    push = CloudPush();
    push.seq = d["seq"] | 0u;
    push.action = d["action"] | "";
    push.itemId = cleanText(d["item_id"] | "", 64);
    push.source = d["source"] | "";
    push.missed = d["missed"] | false;
    if (!push.seq || push.action.empty()) return Msg::Bad;
    const std::string sayTop = cleanText(d["say"] | "", 280);
    if (!mapPush(push.action.c_str(), d["args"], push)) push.kind = CloudPush::Invalid;
    if (push.say.empty()) push.say = sayTop;
    if (d["card"].is<JsonObject>() && push.title.empty()) {
      push.title = cleanText(d["card"]["title"] | "", 60);
      push.body = cleanLines(d["card"]["body"] | "", 600, 12);
    }
    return Msg::Push;
  }
  if (!strcmp(t, "config")) {
    brain = d["brain"] | brain.c_str();
    lang = d["lang"] | "";
    name = cleanText(d["name"] | "", 16);
    modelClaude = d["models"]["claude"] | "";
    modelOpenai = d["models"]["openai"] | "";
    return Msg::Config;
  }
  if (!strcmp(t, "error")) {
    error = CloudError();
    error.re = d["re"] | "";
    error.code = d["code"] | "";
    error.msg = cleanText(d["msg"] | "", 120);
    error.retryMs = d["retry_ms"] | -1;
    error.err = errFromCode(error.code);
    return Msg::Error;
  }
  return Msg::Unknown;
}

// ------------------------------------------------------------ ordering ---

bool CloudLink::alreadyApplied(uint32_t seq) const {
  // seqs are per-device monotonic and hello.after = lastSeq, so anything at
  // or below lastSeq was applied (a replay after a lost ack: ack it again)
  return seq <= lastSeq;
}

void CloudLink::applied(uint32_t seq) {
  if (seq > lastSeq) lastSeq = seq;
  ++sinceSave_;
}

bool CloudLink::seqSaveDue(uint32_t nowMs) const {
  return sinceSave_ && (sinceSave_ >= 10 || nowMs - savedAtMs_ >= 60000u);
}

void CloudLink::seqSaved(uint32_t nowMs) {
  sinceSave_ = 0;
  savedAtMs_ = nowMs;
}

CloudLink::CloseAction CloudLink::onClose(int code) {
  switch (code) {
    case 4401: return CloseAction::Reauth;
    case 4403: return CloseAction::Unpaired;
    case 4426: return CloseAction::Update;
    case 4429: return CloseAction::Wait;
    default: return CloseAction::Reconnect;
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
