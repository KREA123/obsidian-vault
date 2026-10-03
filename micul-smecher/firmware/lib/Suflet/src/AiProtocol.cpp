#include "AiProtocol.h"

#include <ArduinoJson.h>
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "Font.h"  // utf8 helpers

namespace suflet {

// ------------------------------------------------------------- names ---

const char* aiModeName(AiMode m) {
  switch (m) {
    case AiMode::Claude: return "claude";
    case AiMode::ChatGpt: return "chatgpt";
    case AiMode::Cloud: return "cloud";
    case AiMode::Bridge: return "bridge";
    default: return "none";
  }
}

AiMode aiModeFrom(const char* s) {
  if (!s) return AiMode::None;
  if (!strcmp(s, "claude") || !strcmp(s, "api")) return AiMode::Claude;
  if (!strcmp(s, "chatgpt")) return AiMode::ChatGpt;
  if (!strcmp(s, "cloud") || !strcmp(s, "relay")) return AiMode::Cloud;
  if (!strcmp(s, "bridge")) return AiMode::Bridge;
  return AiMode::None;
}

const char* aiErrCode(AiErr e) {
  static const char* const k[] = {"",        "no_key",  "bad_key", "rate_limited", "quota",    "refused",
                                  "offline", "network", "timeout", "upstream",     "truncated", "bridge_offline"};
  static_assert(sizeof(k) / sizeof(k[0]) == (unsigned)AiErr::Count, "codes");
  return (unsigned)e < (unsigned)AiErr::Count ? k[(int)e] : "?";
}

const char* aiErrText(AiErr e, bool ro) {
  switch (e) {
    case AiErr::NoKey: return ro ? "Pune întâi cheia API: Setări › AI." : "Add your API key first: Settings › AI.";
    case AiErr::BadKey: return ro ? "Cheia API a fost respinsă." : "That API key was rejected.";
    case AiErr::RateLimited: return ro ? "Prea multe întrebări. Mai încearcă peste un minut." : "Too many questions. Try again in a minute.";
    case AiErr::Quota: return ro ? "Contul AI nu mai are credit." : "The AI account is out of credit.";
    case AiErr::Refused: return ro ? "AI-ul a refuzat asta." : "The AI declined that one.";
    case AiErr::Offline: return ro ? "Nu am Wi-Fi acum." : "No Wi-Fi right now.";
    case AiErr::Network: return ro ? "Nu ajung la AI. Verifică Wi-Fi-ul." : "Can't reach the AI. Check the Wi-Fi.";
    case AiErr::Timeout: return ro ? "AI-ul a răspuns prea încet. Mai încearcă." : "The AI took too long. Try again.";
    case AiErr::Upstream: return ro ? "AI-ul nu a răspuns. Mai încearcă." : "The AI didn't answer. Try again.";
    case AiErr::Truncated: return ro ? "Răspunsul a fost tăiat. Întreabă mai scurt." : "The answer was cut off. Ask something shorter.";
    case AiErr::BridgeOffline:
      return ro ? "Calculatorul tău e offline: deschide Start SOUL." : "Your computer is offline: open Start SOUL.";
    default: return "";
  }
}

// ------------------------------------------------------- string helpers ---

static bool isWs(uint32_t cp) { return cp == ' ' || cp == '\t' || cp == '\n' || cp == '\r' || cp == 0xA0; }

// web cleanStr(): control chars -> space, collapse whitespace, trim, cut at max code points
static std::string cleanStr(const char* s, size_t maxCp) {
  std::string out;
  if (!s) return out;
  bool space = false;
  size_t cps = 0;
  const char* p = s;
  while (*p && cps < maxCp) {
    uint32_t cp = utf8::next(p);
    if (cp < 0x20 || cp == 0x7F) cp = ' ';
    if (isWs(cp)) {
      space = !out.empty();
      continue;
    }
    if (space) {
      out += ' ';
      ++cps;
      space = false;
      if (cps >= maxCp) break;
    }
    char buf[4];
    const int n = utf8::encode(utf8::normalizeRo(cp), buf);
    out.append(buf, n);
    ++cps;
  }
  return out;
}

// lower-case ASCII with the Romanian (and Latin-1) diacritics folded away
static std::string foldAscii(const std::string& s) {
  std::string o;
  o.reserve(s.size());
  const char* p = s.c_str();
  const char* end = p + s.size();
  while (p < end && *p) {
    const uint32_t cp = utf8::fold(utf8::next(p, end));
    o += cp < 0x80 ? (char)cp : '?';
  }
  return o;
}

static inline bool isAl(char c) { return isalnum((unsigned char)c) != 0; }

// does the word w start at i (word boundary before; `whole`: boundary after too)
static bool wordAt(const std::string& f, size_t i, const char* w, bool whole = true) {
  const size_t n = strlen(w);
  if (i + n > f.size() || f.compare(i, n, w) != 0) return false;
  if (i > 0 && isAl(f[i - 1])) return false;
  if (whole && i + n < f.size() && isAl(f[i + n])) return false;
  return true;
}
static bool hasWord(const std::string& f, const char* w, bool whole = true) {
  for (size_t i = 0; i < f.size(); ++i)
    if (wordAt(f, i, w, whole)) return true;
  return false;
}
// a run of 1..maxD digits at i (boundary before), value in v, length returned (0 = none)
static int digitsAt(const std::string& f, size_t i, int maxD, int& v) {
  if (i >= f.size() || !isdigit((unsigned char)f[i])) return 0;
  if (i > 0 && isAl(f[i - 1])) return 0;
  int n = 0;
  v = 0;
  while (i + n < f.size() && isdigit((unsigned char)f[i + n])) {
    if (n >= maxD) return 0;  // too many digits for \d{1,maxD}\b
    v = v * 10 + (f[i + n] - '0');
    ++n;
  }
  return n;
}
static size_t skipSpaces(const std::string& f, size_t i) {
  while (i < f.size() && f[i] == ' ') ++i;
  return i;
}

static std::string hm(int h, int m) {
  char b[16];
  snprintf(b, sizeof b, "%02d:%02d", h, m);
  return b;
}

// --------------------------------------------------------- the protocol ---

static const char* const kFaces[] = {"happy", "love", "wink", "excited", "thinking", "confused", "sad", "surprised", "smug", "shy"};

static bool timeOk(const char* s, int& h, int& m) {
  if (!s) return false;
  while (*s == ' ') ++s;
  int i = 0, hh = 0, digits = 0;
  while (isdigit((unsigned char)s[i]) && digits < 3) {
    hh = hh * 10 + (s[i] - '0');
    ++i;
    ++digits;
  }
  if (digits < 1 || digits > 2 || s[i] != ':') return false;
  ++i;
  if (!isdigit((unsigned char)s[i]) || !isdigit((unsigned char)s[i + 1])) return false;
  const int mm = (s[i] - '0') * 10 + (s[i + 1] - '0');
  i += 2;
  while (s[i] == ' ') ++i;
  if (s[i] != 0) return false;
  if (hh > 23 || mm > 59) return false;
  if (digits == 2 && s[0] > '2') return false;  // ([01]?\d|2[0-3])
  h = hh;
  m = mm;
  return true;
}

static bool validAction(JsonVariantConst a, AiAction& out) {
  if (!a.is<JsonObjectConst>()) return false;
  JsonObjectConst o = a.as<JsonObjectConst>();
  const char* type = o["type"].is<const char*>() ? o["type"].as<const char*>() : nullptr;
  if (!type) return false;
  struct Spec {
    const char* type;
    AiAction::Type t;
    const char* req[3];
    const char* opt[3];
  };
  static const Spec kSpec[] = {
      {"alarm.set", AiAction::AlarmSet, {"time", nullptr, nullptr}, {"label", "repeat", nullptr}},
      {"timer.start", AiAction::TimerStart, {"minutes", nullptr, nullptr}, {nullptr, nullptr, nullptr}},
      {"reminder.create", AiAction::ReminderCreate, {"time", "text", nullptr}, {"day", nullptr, nullptr}},
      {"note.create", AiAction::NoteCreate, {"text", nullptr, nullptr}, {nullptr, nullptr, nullptr}},
      {"focus.start", AiAction::FocusStart, {"minutes", nullptr, nullptr}, {nullptr, nullptr, nullptr}},
  };
  const Spec* sp = nullptr;
  for (const Spec& s : kSpec)
    if (!strcmp(s.type, type)) sp = &s;
  if (!sp) return false;
  // exactly these keys
  for (JsonPairConst kv : o) {
    const char* k = kv.key().c_str();
    if (!strcmp(k, "type")) continue;
    bool ok = false;
    for (const char* r : sp->req)
      if (r && !strcmp(r, k)) ok = true;
    for (const char* r : sp->opt)
      if (r && !strcmp(r, k)) ok = true;
    if (!ok) return false;
  }
  for (const char* r : sp->req)
    if (r && o[r].isNull()) return false;
  AiAction act;
  act.type = sp->t;
  if (o["time"].is<const char*>() || !o["time"].isNull()) {
    int h, m;
    if (!o["time"].is<const char*>() || !timeOk(o["time"].as<const char*>(), h, m)) return false;
    act.hour = (uint8_t)h;
    act.minute = (uint8_t)m;
  }
  if (!o["minutes"].isNull()) {
    JsonVariantConst n = o["minutes"];
    if (!(n.is<double>() || n.is<long>())) return false;
    const double v = n.as<double>();
    const double lo = act.type == AiAction::FocusStart ? 5 : 1, hi = act.type == AiAction::FocusStart ? 120 : 180;
    if (!isfinite(v) || v < lo || v > hi) return false;
    act.minutes = (uint16_t)lround(v);
  }
  if (!o["text"].isNull()) {
    if (!o["text"].is<const char*>()) return false;
    act.text = cleanStr(o["text"].as<const char*>(), act.type == AiAction::NoteCreate ? 300 : 80);
    if (act.text.empty()) return false;
  }
  if (!o["label"].isNull()) {
    if (!o["label"].is<const char*>()) return false;
    act.text = cleanStr(o["label"].as<const char*>(), 40);
  }
  if (!o["repeat"].isNull()) {
    const char* r = o["repeat"].is<const char*>() ? o["repeat"].as<const char*>() : "";
    if (!strcmp(r, "once")) act.days = 0;
    else if (!strcmp(r, "daily")) act.days = 0x7F;
    else if (!strcmp(r, "weekdays")) act.days = 0x1F;
    else if (!strcmp(r, "weekend")) act.days = 0x60;
    else return false;
  }
  if (!o["day"].isNull()) {
    const char* d = o["day"].is<const char*>() ? o["day"].as<const char*>() : "";
    if (!strcmp(d, "today")) act.tomorrow = false;
    else if (!strcmp(d, "tomorrow")) act.tomorrow = true;
    else return false;
  }
  out = act;
  return true;
}

// {"type": "memory.remember", "text", "kind"?, "importance"?} / {"type": "memory.forget", "text"}: exactly
// these keys, a real fact (<= 120 chars) or keyword (>= 3 chars), never a secret
static bool validMemOp(JsonVariantConst a, MemOp& out) {
  if (!a.is<JsonObjectConst>()) return false;
  JsonObjectConst o = a.as<JsonObjectConst>();
  const char* type = o["type"] | "";
  MemOp op;
  op.forget = !strcmp(type, "memory.forget");
  if (!op.forget && strcmp(type, "memory.remember")) return false;
  for (JsonPairConst kv : o) {
    const char* k = kv.key().c_str();
    if (strcmp(k, "type") && strcmp(k, "text") && (op.forget || (strcmp(k, "kind") && strcmp(k, "importance"))))
      return false;
  }
  if (!o["text"].is<const char*>()) return false;
  const char* raw = o["text"].as<const char*>();
  if (strlen(raw) > (op.forget ? 80u : 400u)) return false;  // a fact, not an essay
  op.text = cleanStr(raw, op.forget ? 80 : SoulMemory::kTextMax);
  if (op.forget ? SoulMemory::fold(op.text).size() < 3 : op.text.empty()) return false;
  if (!op.forget && SoulMemory::looksSecret(op.text)) return false;
  if (!o["kind"].isNull()) {
    if (!o["kind"].is<const char*>() || !factKindFrom(o["kind"].as<const char*>(), op.kind)) return false;
  }
  if (!o["importance"].isNull()) {
    JsonVariantConst n = o["importance"];
    if (!(n.is<long>() || n.is<double>())) return false;
    const double v = n.as<double>();
    if (!isfinite(v) || v < 1 || v > 5) return false;
    op.importance = (uint8_t)lround(v);
  }
  out = op;
  return true;
}

static bool parseObject(const char* p, size_t n, JsonDocument& doc) {
  if (!p || !n) return false;
  const DeserializationError e = deserializeJson(doc, p, n, DeserializationOption::NestingLimit(8));
  return !e && doc.is<JsonObject>();
}

AiReply parseReply(const char* raw, size_t n) {
  AiReply r;
  std::string s(raw ? raw : "", raw ? n : 0);
  // trim
  size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
  s = a == std::string::npos ? std::string() : s.substr(a, b - a + 1);
  JsonDocument doc;
  bool ok = parseObject(s.data(), s.size(), doc);
  if (!ok) {
    std::string body = s;
    const size_t f = s.find("```");
    if (f != std::string::npos) {
      size_t start = f + 3;
      if (s.compare(start, 4, "json") == 0) start += 4;
      const size_t endf = s.find("```", start);
      if (endf != std::string::npos) body = s.substr(start, endf - start);
    }
    const size_t o0 = body.find('{'), o1 = body.rfind('}');
    if (o0 != std::string::npos && o1 != std::string::npos && o1 > o0) {
      doc.clear();
      ok = parseObject(body.data() + o0, o1 - o0 + 1, doc);
    }
  }
  const char* say = ok && doc["say"].is<const char*>() ? doc["say"].as<const char*>() : nullptr;
  std::string sayClean = say ? cleanStr(say, 280) : std::string();
  if (!ok || sayClean.empty()) {
    std::string plain = s;
    for (char& c : plain)
      if (c == '{' || c == '}' || c == '"' || c == '[' || c == ']' || c == '`') c = ' ';
    r.say = cleanStr(plain.c_str(), 280);
    if (r.say.empty()) r.say = "\xE2\x80\xA6";  // …
    r.loose = true;
    if (ok && doc["actions"].is<JsonArray>()) r.rejected = (int)doc["actions"].size();
    return r;
  }
  r.say = sayClean;
  if (doc["face"].is<const char*>()) {
    const char* f = doc["face"].as<const char*>();
    for (const char* k : kFaces)
      if (!strcmp(k, f)) r.face = f;
  }
  JsonVariantConst acts = doc["actions"];
  int total = 0;
  int memTotal = 0;
  auto take = [&](JsonVariantConst v) {
    const char* t = v["type"].is<const char*>() ? v["type"].as<const char*>() : "";
    if (!strncmp(t, "memory.", 7)) {  // SOUL Memory: its own budget of three, apart from the actions
      ++memTotal;
      MemOp op;
      if (memTotal <= 3 && validMemOp(v, op)) r.memory.push_back(op);
      else ++r.rejected;
      return;
    }
    ++total;
    if (r.actions.size() >= 3 || total > 3) return;
    AiAction act;
    if (validAction(v, act)) r.actions.push_back(act);
  };
  if (acts.is<JsonArrayConst>()) {
    for (JsonVariantConst v : acts.as<JsonArrayConst>()) take(v);
  } else if (!acts.isNull()) {
    take(acts);
  }
  r.rejected += total - (int)r.actions.size();
  return r;
}

// ----------------------------------------------------------- the prompt ---

static const char* const kWdEn[] = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"};
static const char* const kWdRo[] = {"luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"};
static const char* const kMoEn[] = {"January", "February", "March",     "April",   "May",      "June",
                                    "July",    "August",   "September", "October", "November", "December"};
static const char* const kMoRo[] = {"ianuarie", "februarie", "martie",     "aprilie", "mai",      "iunie",
                                    "iulie",    "august",    "septembrie", "octombrie", "noiembrie", "decembrie"};

std::string formatNow(uint32_t now, bool ro) {
  if (!now) return ro ? "ora necunoscută" : "time unknown";
  time_t t = (time_t)now;
  struct tm tm;
  gmtime_r(&t, &tm);
  const int wd = (tm.tm_wday + 6) % 7;
  char b[96];
  if (ro)
    snprintf(b, sizeof b, "%s, %d %s %d, %02d:%02d", kWdRo[wd], tm.tm_mday, kMoRo[tm.tm_mon], tm.tm_year + 1900,
             tm.tm_hour, tm.tm_min);
  else
    snprintf(b, sizeof b, "%s %d %s %d, %02d:%02d", kWdEn[wd], tm.tm_mday, kMoEn[tm.tm_mon], tm.tm_year + 1900,
             tm.tm_hour, tm.tm_min);
  return b;
}

std::string systemPrompt(const AiContext& c) {
  std::string s;
  s.reserve(2000);
  s += "You are " + c.name +
       ", a SOUL: a small round companion device with two living eyes on a round 480 px screen, held in one "
       "hand. You answer on that screen, so keep it short: one or two plain sentences, at most 200 characters, "
       "no markdown, no emoji, no lists. Reply in ";
  s += c.ro ? "Romanian" : "English";
  s += " unless the user writes in another language.\nRight now: " + formatNow(c.now, c.ro) +
       ". Alarms: " + (c.alarms.empty() ? std::string("none") : c.alarms) +
       ". Reminders: " + (c.reminders.empty() ? std::string("none") : c.reminders) + ". Countdown timer: ";
  if (c.timerLeftMin >= 0) s += std::to_string(c.timerLeftMin) + " min left";
  else s += "none";
  s += ". Notes: " + std::to_string(c.notes) + ".\n";
  s += "You can act on the device. Reply with ONLY one JSON object and nothing else:\n"
       "{\"say\": \"<what you say>\", \"face\": \"<optional, one of: happy, love, wink, excited, thinking, confused, "
       "sad, surprised, smug, shy>\", \"actions\": [<zero to three actions>]}\n"
       "The only actions (24-hour times, exactly these keys):\n"
       "{\"type\": \"alarm.set\", \"time\": \"HH:MM\", \"label\": \"<up to 40 chars>\", \"repeat\": \"once\" | "
       "\"daily\" | \"weekdays\" | \"weekend\"}\n"
       "{\"type\": \"timer.start\", \"minutes\": <1-180>}\n"
       "{\"type\": \"reminder.create\", \"time\": \"HH:MM\", \"day\": \"today\" | \"tomorrow\", \"text\": \"<up to 80 "
       "chars>\"}\n"
       "{\"type\": \"note.create\", \"text\": \"<up to 300 chars>\"}\n"
       "{\"type\": \"focus.start\", \"minutes\": <5-120>}\n"
       "Add an action only when the user asks for one, and confirm it in \"say\". You cannot send messages, browse, "
       "call or control other devices; if asked, say so briefly. You are an AI and say so plainly if asked.\n"
       "SOUL keeps the owner's memory on the device and gives it to whichever AI is connected. Two more actions "
       "(they do not count against the three):\n"
       "{\"type\": \"memory.remember\", \"text\": \"<one durable fact, up to 120 chars, in the owner's words: 'My sister "
       "is Ana'>\", \"kind\": \"person\" | \"preference\" | \"plan\" | \"place\" | \"note\" | \"summary\" | "
       "\"other\", \"importance\": <1-5>}\n"
       "{\"type\": \"memory.forget\", \"text\": \"<a keyword of the fact to forget>\"}\n"
       "Remember only what is worth keeping (people and pets, birthdays, preferences, ongoing plans), at most one or "
       "two per answer, nothing already known. Never remember passwords, codes, card or ID numbers, health, religion, "
       "politics or sexuality unless the owner explicitly asks for that exact thing. SOUL shows \"Remembered: ...\" "
       "and the owner can undo it.";
  if (!c.memory.empty()) s += "\n" + c.memory;
  return s;
}

// The JSON schema of the reply (Claude structured outputs). Every object
// lists all its keys as required and forbids extra ones.
static void addSchema(JsonObject fmt) {
  fmt["type"] = "json_schema";
  JsonObject sc = fmt["schema"].to<JsonObject>();
  sc["type"] = "object";
  sc["additionalProperties"] = false;
  JsonObject props = sc["properties"].to<JsonObject>();
  props["say"]["type"] = "string";
  JsonObject face = props["face"].to<JsonObject>();
  face["type"] = "string";
  JsonArray fe = face["enum"].to<JsonArray>();
  for (const char* f : kFaces) fe.add(f);
  fe.add("none");
  JsonObject acts = props["actions"].to<JsonObject>();
  acts["type"] = "array";
  JsonArray any = acts["items"]["anyOf"].to<JsonArray>();
  auto variant = [&](const char* type, std::initializer_list<std::pair<const char*, const char*>> keys) {
    JsonObject v = any.add<JsonObject>();
    v["type"] = "object";
    v["additionalProperties"] = false;
    JsonObject p = v["properties"].to<JsonObject>();
    p["type"]["const"] = type;
    JsonArray req = v["required"].to<JsonArray>();
    req.add("type");
    for (const auto& k : keys) {
      req.add(k.first);
      if (!strcmp(k.second, "integer")) p[k.first]["type"] = "integer";
      else if (!strcmp(k.second, "repeat")) {
        p[k.first]["type"] = "string";
        JsonArray e = p[k.first]["enum"].to<JsonArray>();
        for (const char* x : {"once", "daily", "weekdays", "weekend"}) e.add(x);
      } else if (!strcmp(k.second, "day")) {
        p[k.first]["type"] = "string";
        JsonArray e = p[k.first]["enum"].to<JsonArray>();
        e.add("today");
        e.add("tomorrow");
      } else p[k.first]["type"] = "string";
    }
  };
  variant("alarm.set", {{"time", "string"}, {"label", "string"}, {"repeat", "repeat"}});
  variant("timer.start", {{"minutes", "integer"}});
  variant("reminder.create", {{"time", "string"}, {"day", "day"}, {"text", "string"}});
  variant("note.create", {{"text", "string"}});
  variant("focus.start", {{"minutes", "integer"}});
  {  // SOUL Memory
    JsonObject v = any.add<JsonObject>();
    v["type"] = "object";
    v["additionalProperties"] = false;
    JsonObject p = v["properties"].to<JsonObject>();
    p["type"]["const"] = "memory.remember";
    p["text"]["type"] = "string";
    p["kind"]["type"] = "string";
    JsonArray e = p["kind"]["enum"].to<JsonArray>();
    for (int i = 0; i < (int)FactKind::Count; ++i) e.add(factKindName((FactKind)i));
    p["importance"]["type"] = "integer";
    JsonArray req = v["required"].to<JsonArray>();
    for (const char* k : {"type", "text", "kind", "importance"}) req.add(k);
  }
  variant("memory.forget", {{"text", "string"}});
  JsonArray req = sc["required"].to<JsonArray>();
  req.add("say");
  req.add("face");
  req.add("actions");
}

AiErr buildRequest(const AiConfig& cfg, const AiContext& ctx, const std::vector<ChatTurn>& history,
                   const std::string& text, HttpRequest& out) {
  out = HttpRequest();
  JsonDocument doc;
  const size_t histN = history.size() > 8 ? 8 : history.size();
  const size_t h0 = history.size() - histN;
  switch (cfg.mode) {
    case AiMode::Claude: {
      if (cfg.anthropicKey.empty()) return AiErr::NoKey;
      out.url = "https://api.anthropic.com/v1/messages";
      out.headers = {{"content-type", "application/json"},
                     {"x-api-key", cfg.anthropicKey},
                     {"anthropic-version", "2023-06-01"},
                     {"anthropic-beta", "server-side-fallback-2026-07-01"}};
      doc["model"] = cfg.claudeModel;
      doc["max_tokens"] = cfg.maxTokens;
      JsonObject oc = doc["output_config"].to<JsonObject>();
      oc["effort"] = cfg.claudeEffort;
      if (cfg.useSchema) addSchema(oc["format"].to<JsonObject>());
      doc["fallbacks"] = "default";
      doc["system"] = systemPrompt(ctx);
      JsonArray msgs = doc["messages"].to<JsonArray>();
      for (size_t i = h0; i < history.size(); ++i) {
        JsonObject m = msgs.add<JsonObject>();
        m["role"] = history[i].user ? "user" : "assistant";
        m["content"] = history[i].text;
      }
      JsonObject m = msgs.add<JsonObject>();
      m["role"] = "user";
      m["content"] = text;
      break;
    }
    case AiMode::ChatGpt: {
      if (cfg.openaiKey.empty()) return AiErr::NoKey;
      out.url = "https://api.openai.com/v1/chat/completions";
      out.headers = {{"content-type", "application/json"}, {"authorization", "Bearer " + cfg.openaiKey}};
      doc["model"] = cfg.openaiModel;
      doc["response_format"]["type"] = "json_object";
      doc["max_completion_tokens"] = cfg.maxTokens;
      JsonArray msgs = doc["messages"].to<JsonArray>();
      JsonObject sys = msgs.add<JsonObject>();
      sys["role"] = "system";
      sys["content"] = systemPrompt(ctx);
      for (size_t i = h0; i < history.size(); ++i) {
        JsonObject m = msgs.add<JsonObject>();
        m["role"] = history[i].user ? "user" : "assistant";
        m["content"] = history[i].text;
      }
      JsonObject m = msgs.add<JsonObject>();
      m["role"] = "user";
      m["content"] = text;
      break;
    }
    case AiMode::Cloud: {
      if (cfg.relayUrl.empty()) return AiErr::NoKey;
      std::string base = cfg.relayUrl;
      while (!base.empty() && base.back() == '/') base.pop_back();
      out.url = base + "/v1/ask";
      out.headers = {{"content-type", "application/json"}};
      if (!cfg.relayToken.empty()) out.headers.push_back({"authorization", "Bearer " + cfg.relayToken});
      doc["device_id"] = cfg.deviceId.empty() ? std::string("soul") : cfg.deviceId;
      doc["text"] = text.size() > 2000 ? text.substr(0, 2000) : text;
      doc["lang"] = ctx.ro ? "ro" : "en";
      if (!ctx.memory.empty()) doc["memory"] = ctx.memory;
      break;
    }
    default: return AiErr::NoKey;
  }
  serializeJson(doc, out.body);
  return AiErr::None;
}

// --------------------------------------------------------- the answers ---

static AiErr statusErr(int status) {
  if (status == 401 || status == 403) return AiErr::BadKey;
  if (status == 402) return AiErr::Quota;
  if (status == 408) return AiErr::Timeout;
  if (status == 429) return AiErr::RateLimited;
  return AiErr::Upstream;
}

// "YYYY-MM-DDTHH:MM[:SS]" (local, naive) -> epoch-like seconds; 0 if unreadable
static uint32_t parseStamp(const char* s) {
  if (!s) return 0;
  int Y, M, D, h, m, sec = 0;
  if (sscanf(s, "%d-%d-%dT%d:%d:%d", &Y, &M, &D, &h, &m, &sec) < 5) return 0;
  if (Y < 2020 || Y > 2100 || M < 1 || M > 12 || D < 1 || D > 31 || h < 0 || h > 23 || m < 0 || m > 59 || sec < 0 ||
      sec > 59)
    return 0;
  // timegm without the GNU extension: days from civil
  const int y = Y - (M <= 2), era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (M + (M > 2 ? -3 : 9)) + 2) / 5 + D - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  const long days = era * 146097L + (long)doe - 719468L;
  return (uint32_t)(days * 86400L + h * 3600L + m * 60L + sec);
}

static void relayActions(JsonArrayConst acts, uint32_t now, AiReply& r) {
  for (JsonObjectConst a : acts) {
    if (r.actions.size() >= 3) break;
    if (!a["ok"].as<bool>()) continue;
    const char* name = a["action"] | "";
    AiAction act;
    if (!strcmp(name, "alarm.set")) {
      int h, m;
      if (!timeOk(a["card"]["title"] | "", h, m)) {
        ++r.rejected;
        continue;
      }
      act.type = AiAction::AlarmSet;
      act.hour = (uint8_t)h;
      act.minute = (uint8_t)m;
      static const char* const kD[] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"};
      for (JsonVariantConst d : a["data"]["days"].as<JsonArrayConst>())
        for (int i = 0; i < 7; ++i)
          if (d.is<const char*>() && !strcmp(d.as<const char*>(), kD[i])) act.days |= (uint8_t)(1 << i);
      act.text = cleanStr(a["card"]["body"] | "", 40);
    } else if (!strcmp(name, "timer.start") || !strcmp(name, "focus.start")) {
      const uint32_t ends = parseStamp(a["data"]["ends_at"] | "");
      if (!ends || !now || ends <= now) {
        ++r.rejected;
        continue;
      }
      act.type = !strcmp(name, "timer.start") ? AiAction::TimerStart : AiAction::FocusStart;
      act.minutes = (uint16_t)((ends - now + 59) / 60);
      if (act.minutes > 180) act.minutes = 180;
    } else if (!strcmp(name, "reminder.create")) {
      const uint32_t when = parseStamp(a["data"]["when"] | "");
      if (!when) {
        ++r.rejected;
        continue;
      }
      act.type = AiAction::ReminderCreate;
      act.hour = (uint8_t)(when % 86400 / 3600);
      act.minute = (uint8_t)(when % 3600 / 60);
      act.tomorrow = now && when / 86400 > now / 86400;
      act.text = cleanStr(a["card"]["body"] | "", 80);
      if (act.text.empty()) act.text = "Reminder";
    } else if (!strcmp(name, "note.create")) {
      act.type = AiAction::NoteCreate;
      act.text = cleanStr(a["card"]["body"] | "", 300);
      if (act.text.empty()) {
        ++r.rejected;
        continue;
      }
    } else {
      continue;  // drafts, lists, answer cards: nothing to do on the device
    }
    r.actions.push_back(act);
  }
}

bool memOpFrom(const char* op, const char* text, const char* kind, int importance, MemOp& out) {
  // the cloud's form {"op": "remember"|"forget", "text", "kind"?, "importance"?} -> the device protocol's
  JsonDocument d;
  const bool forget = op && !strcmp(op, "forget");
  d["type"] = forget ? "memory.forget" : op && !strcmp(op, "remember") ? "memory.remember" : "";
  if (text) d["text"] = text;
  if (kind && *kind && !forget) d["kind"] = kind;
  if (importance > 0 && !forget) d["importance"] = importance;
  return validMemOp(d.as<JsonVariantConst>(), out);
}

static void relayMemory(JsonVariantConst ops, AiReply& r) {
  if (!ops.is<JsonArrayConst>()) return;
  int n = 0;
  for (JsonObjectConst o : ops.as<JsonArrayConst>()) {
    if (++n > 3) break;
    MemOp m;
    if (memOpFrom(o["op"] | "", o["text"].is<const char*>() ? o["text"].as<const char*>() : nullptr, o["kind"] | "",
                  o["importance"] | 0, m))
      r.memory.push_back(m);
    else
      ++r.rejected;
  }
}

AiOutcome parseResponse(const AiConfig& cfg, int status, const char* body, size_t n, AiErr netErr, uint32_t now) {
  AiOutcome o;
  o.httpStatus = status;
  if (netErr != AiErr::None || status < 0) {
    o.err = netErr != AiErr::None ? netErr : AiErr::Network;
    return o;
  }
  JsonDocument doc;
  const bool json = body && n && !deserializeJson(doc, body, n, DeserializationOption::NestingLimit(12));
  if (status != 200) {
    o.err = statusErr(status);
    if (json && cfg.mode == AiMode::ChatGpt) {
      const char* code = doc["error"]["code"] | "";
      const char* type = doc["error"]["type"] | "";
      if (!strcmp(code, "insufficient_quota") || !strcmp(type, "insufficient_quota")) o.err = AiErr::Quota;
    }
    if (status == 400 && cfg.mode == AiMode::Claude && cfg.useSchema && json) {
      const char* msg = doc["error"]["message"] | "";
      if (strstr(msg, "output_config") || strstr(msg, "format") || strstr(msg, "schema")) o.schemaRejected = true;
    }
    return o;
  }
  if (!json) {
    o.err = AiErr::Upstream;
    return o;
  }
  switch (cfg.mode) {
    case AiMode::Claude: {
      const char* stop = doc["stop_reason"] | "";
      if (!strcmp(stop, "refusal")) {
        o.err = AiErr::Refused;
        return o;
      }
      for (JsonObjectConst b : doc["content"].as<JsonArrayConst>())
        if (!strcmp(b["type"] | "", "text")) o.raw += b["text"] | "";
      o.reply = parseReply(o.raw);
      if (!strcmp(stop, "max_tokens") && o.reply.loose) o.err = AiErr::Truncated;
      break;
    }
    case AiMode::ChatGpt: {
      JsonObjectConst msg = doc["choices"][0]["message"];
      if (msg["refusal"].is<const char*>() && *(msg["refusal"].as<const char*>())) {
        o.err = AiErr::Refused;
        return o;
      }
      o.raw = msg["content"] | "";
      o.reply = parseReply(o.raw);
      if (!strcmp(doc["choices"][0]["finish_reason"] | "", "length") && o.reply.loose) o.err = AiErr::Truncated;
      break;
    }
    case AiMode::Cloud: {
      const char* say = doc["say"] | "";
      o.reply.say = cleanStr(say, 280);
      static const char* const kTone[][2] = {{"happy", "happy"}, {"sad", "sad"}, {"surprised", "surprised"},
                                              {"cheeky", "smug"}, {"love", "love"}, {"sleepy", ""}};
      const char* face = doc["face"] | "";
      for (const auto& t : kTone)
        if (!strcmp(face, t[0])) o.reply.face = t[1];
      relayActions(doc["actions"].as<JsonArrayConst>(), now, o.reply);
      relayMemory(doc["memory"], o.reply);
      o.raw = "{\"say\":\"" + o.reply.say + "\"}";
      if (o.reply.say.empty()) o.err = AiErr::Upstream;
      break;
    }
    default: o.err = AiErr::NoKey; break;
  }
  if (o.err == AiErr::None && o.reply.say.empty()) o.err = AiErr::Upstream;
  return o;
}

int retryDelayMs(const AiOutcome& o, int attempt) {
  switch (o.err) {
    case AiErr::Upstream:
      if (o.httpStatus >= 400 && o.httpStatus < 500 && o.httpStatus != 408) return -1;  // our request is wrong
      return attempt <= 2 ? (attempt == 1 ? 1000 : 3000) : -1;
    case AiErr::RateLimited: return attempt == 1 ? 2500 : -1;
    case AiErr::Timeout:
    case AiErr::Network: return attempt == 1 ? 800 : -1;
    default: return -1;
  }
}

// ------------------------------------------------------- on-device rules ---

struct TimeHit {
  int h = -1, m = 0;
  bool tomorrow = false, alarm = false;
};

static bool parseTime(const std::string& text, uint32_t now, TimeHit& out) {
  const std::string f = " " + foldAscii(text) + " ";
  TimeHit t;
  t.tomorrow = hasWord(f, "maine") || hasWord(f, "tomorrow");
  bool hint = false, found = false;
  // 1. H:MM or H.MM
  for (size_t i = 0; i < f.size() && !found; ++i) {
    int v;
    const int nd = digitsAt(f, i, 2, v);
    if (!nd) continue;
    const size_t j = i + nd;
    if (j + 2 < f.size() && (f[j] == ':' || f[j] == '.') && isdigit((unsigned char)f[j + 1]) &&
        isdigit((unsigned char)f[j + 2]) && !isAl(f[j + 3])) {
      t.h = v;
      t.m = (f[j + 1] - '0') * 10 + (f[j + 2] - '0');
      found = true;
    }
  }
  // 2. H am / pm
  for (size_t i = 0; i < f.size() && !found; ++i) {
    int v;
    const int nd = digitsAt(f, i, 2, v);
    if (!nd) continue;
    const size_t j = skipSpaces(f, i + nd);
    if (j + 2 <= f.size() && (f.compare(j, 2, "am") == 0 || f.compare(j, 2, "pm") == 0) && !isAl(f[j + 2])) {
      t.h = v % 12 + (f[j] == 'p' ? 12 : 0);
      t.m = 0;
      found = true;
    }
  }
  // 3. la / at / ora H [si jumatate | thirty]
  for (size_t i = 0; i < f.size() && !found; ++i) {
    const char* w = wordAt(f, i, "la") ? "la" : wordAt(f, i, "at") ? "at" : wordAt(f, i, "ora") ? "ora" : nullptr;
    if (!w) continue;
    size_t j = i + strlen(w);
    if (j >= f.size() || f[j] != ' ') continue;
    j = skipSpaces(f, j);
    int v;
    const int nd = digitsAt(f, j, 2, v);
    if (!nd || isAl(f[j + nd])) continue;
    t.h = v;
    t.m = 0;
    size_t k = skipSpaces(f, j + nd);
    if (wordAt(f, k, "si")) k = skipSpaces(f, k + 2);
    if (wordAt(f, k, "jumatate") || wordAt(f, k, "thirty")) t.m = 30;
    hint = true;
    found = true;
  }
  // 4. in / peste N min
  for (size_t i = 0; i < f.size() && !found; ++i) {
    const char* w = wordAt(f, i, "in") ? "in" : wordAt(f, i, "peste") ? "peste" : nullptr;
    if (!w) continue;
    size_t j = i + strlen(w);
    if (j >= f.size() || f[j] != ' ') continue;
    j = skipSpaces(f, j);
    int v;
    const int nd = digitsAt(f, j, 3, v);
    if (!nd) continue;
    const size_t k = skipSpaces(f, j + nd);
    if (!(wordAt(f, k, "min") || wordAt(f, k, "minute") || wordAt(f, k, "minutes"))) continue;
    if (!now) return false;
    const uint32_t at = now + (uint32_t)v * 60u;
    out.h = (int)(at % 86400 / 3600);
    out.m = (int)(at % 3600 / 60);
    out.tomorrow = at / 86400 != now / 86400;
    out.alarm = false;
    return true;
  }
  if (!found && (hasWord(f, "diseara") || hasWord(f, "tonight"))) {
    t.h = 20;
    t.m = 0;
    found = true;
  }
  if (!found || t.h < 0 || t.h > 23 || t.m > 59) return false;
  t.alarm = hasWord(f, "alarm", false) || hasWord(f, "trezeste", false) || hasWord(f, "trezesc", false) ||
            hasWord(f, "wake", false);
  if (hint && !t.alarm && t.h >= 1 && t.h <= 7 && !hasWord(f, "dimineata") && !hasWord(f, "morning")) t.h += 12;
  out = t;
  return true;
}

static int parseTimerMinutes(const std::string& text) {
  const std::string f = " " + foldAscii(text) + " ";
  static const char* const kw[] = {"timer", "minutar", "countdown", "cronometreaza"};
  for (size_t i = 0; i < f.size(); ++i) {
    for (const char* w : kw) {
      if (!wordAt(f, i, w)) continue;
      for (size_t j = i + strlen(w); j < f.size(); ++j)
        if (isdigit((unsigned char)f[j])) {
          int v = 0, n = 0;
          while (n < 3 && isdigit((unsigned char)f[j + n])) v = v * 10 + (f[j + n++] - '0');
          return v;
        }
    }
  }
  // "10 min timer"
  for (size_t i = 0; i < f.size(); ++i) {
    int v;
    const int nd = digitsAt(f, i, 3, v);
    if (!nd) continue;
    size_t k = skipSpaces(f, i + nd);
    if (f.compare(k, 3, "min") != 0) continue;
    while (k < f.size() && isalpha((unsigned char)f[k])) ++k;
    if (k >= f.size() || f[k] != ' ') continue;
    k = skipSpaces(f, k);
    for (const char* w : {"timer", "minutar", "countdown"})
      if (wordAt(f, k, w)) return v;
  }
  return -1;
}

std::string cleanLabel(const std::string& text) {
  // split into words, keep the originals, match on folded copies
  std::vector<std::string> w;
  {
    size_t i = 0;
    while (i < text.size()) {
      while (i < text.size() && isspace((unsigned char)text[i])) ++i;
      size_t j = i;
      while (j < text.size() && !isspace((unsigned char)text[j])) ++j;
      if (j > i) w.push_back(text.substr(i, j - i));
      i = j;
    }
  }
  std::vector<std::string> f;
  for (const std::string& x : w) {
    std::string y = foldAscii(x);
    while (!y.empty() && strchr(",.:;!?", y.back())) y.pop_back();
    f.push_back(y);
  }
  std::vector<bool> drop(w.size(), false);
  size_t i = 0;
  auto is = [&](size_t k, std::initializer_list<const char*> opts) {
    if (k >= f.size()) return false;
    for (const char* o : opts)
      if (f[k] == o) return true;
    return false;
  };
  // leading "remind me" / "wake me up" / "amintește-mi" / "trezește-mă"
  if (is(0, {"aminteste-mi", "aminteste", "trezeste-ma"})) drop[i++] = true;
  else if (is(0, {"remind"}) && is(1, {"me"})) drop[0] = drop[1] = true, i = 2;
  else if (is(0, {"wake"}) && is(1, {"me"})) {
    drop[0] = drop[1] = true;
    i = 2;
    if (is(2, {"up"})) drop[2] = true, i = 3;
  }
  // leading "set an alarm" / "pune o alarmă"
  {
    size_t k = i;
    if (is(k, {"pune-mi", "pune", "set", "seteaza", "fa-mi", "make"})) ++k;
    if (is(k, {"o", "an", "a"})) ++k;
    if (is(k, {"alarma", "alarm"})) {
      for (size_t q = i; q <= k; ++q) drop[q] = true;
    }
  }
  auto isNum = [](const std::string& s) {
    if (s.empty() || s.size() > 5) return false;
    int colon = 0;
    for (char c : s) {
      if (c == ':' || c == '.') ++colon;
      else if (!isdigit((unsigned char)c)) return false;
    }
    return colon <= 1 && isdigit((unsigned char)s[0]);
  };
  for (size_t k = 0; k < f.size(); ++k) {
    // "la 7", "at 7:30 pm", "ora 7 și jumătate"
    if (is(k, {"la", "at", "ora"}) && k + 1 < f.size() && isNum(f[k + 1])) {
      drop[k] = drop[k + 1] = true;
      size_t q = k + 2;
      if (is(q, {"am", "pm"})) drop[q++] = true;
      if (is(q, {"si"}) && is(q + 1, {"jumatate"})) drop[q] = drop[q + 1] = true;
      else if (is(q, {"jumatate"})) drop[q] = true;
      continue;
    }
    const std::string& s = f[k];
    if (s.find(':') != std::string::npos && isNum(s)) drop[k] = true;
    if (s.size() >= 3 && (s.compare(s.size() - 2, 2, "am") == 0 || s.compare(s.size() - 2, 2, "pm") == 0) &&
        isNum(s.substr(0, s.size() - 2)))
      drop[k] = true;
    if (isNum(s) && is(k + 1, {"am", "pm"})) drop[k] = drop[k + 1] = true;
    if (is(k, {"maine", "tomorrow", "azi", "today", "diseara", "tonight"})) drop[k] = true;
  }
  std::string out;
  bool first = true;
  for (size_t k = 0; k < w.size(); ++k) {
    if (drop[k]) continue;
    if (first && (f[k] == "sa" || f[k] == "to")) continue;
    if (!out.empty()) out += ' ';
    out += w[k];
    first = false;
  }
  // trim punctuation at both ends
  while (!out.empty() && strchr(",.:; ", out.front())) out.erase(out.begin());
  while (!out.empty() && strchr(",.:; ", out.back())) out.pop_back();
  if (!out.empty()) {
    const char* p = out.c_str();
    const uint32_t cp = utf8::next(p);
    char b[4];
    const int n = utf8::encode(utf8::upper(cp), b);
    out = std::string(b, n) + out.substr(p - out.c_str());
  }
  return out;
}

std::string cleanText(const char* s, size_t maxCp) { return cleanStr(s, maxCp); }
bool parseHhmm(const char* s, int& h, int& m) { return timeOk(s, h, m); }
uint32_t parseLocalStamp(const char* s) { return parseStamp(s); }

static std::string t12(const std::string& hhmm, bool ro) {
  if (ro) return hhmm;
  int h = atoi(hhmm.c_str()), m = atoi(hhmm.c_str() + 3);
  char b[16];
  snprintf(b, sizeof b, "%d:%02d %s", h % 12 ? h % 12 : 12, m, h < 12 ? "am" : "pm");
  return b;
}

bool localAct(const std::string& text, uint32_t now, bool ro, AiReply& out) {
  out = AiReply();
  const int n = parseTimerMinutes(text);
  if (n >= 1 && n <= 180) {
    AiAction a;
    a.type = AiAction::TimerStart;
    a.minutes = (uint16_t)n;
    out.actions.push_back(a);
    char b[64];
    snprintf(b, sizeof b, ro ? "Minutar: %d minute. Start." : "Timer: %d minutes. Go.", n);
    out.say = b;
    return true;
  }
  TimeHit tm;
  if (!parseTime(text, now, tm)) return false;
  const std::string t = hm(tm.h, tm.m);
  AiAction a;
  a.hour = (uint8_t)tm.h;
  a.minute = (uint8_t)tm.m;
  const std::string label = cleanLabel(text);
  if (tm.alarm) {
    a.type = AiAction::AlarmSet;
    a.text = label.empty() ? (ro ? "Alarmă" : "Alarm") : cleanStr(label.c_str(), 40);
    out.say = ro ? "Am pus alarma la " + t + ". Somn ușor." : "Alarm set for " + t12(t, false) + ". Sleep well.";
  } else {
    a.type = AiAction::ReminderCreate;
    a.tomorrow = tm.tomorrow;
    a.text = label.empty() ? (ro ? "Memento" : "Reminder") : cleanStr(label.c_str(), 80);
    out.say = ro ? std::string("Gata. Te anunț ") + (tm.tomorrow ? "mâine " : "") + "la " + t + "."
                 : std::string("Done. I'll remind you ") + (tm.tomorrow ? "tomorrow " : "") + "at " + t12(t, false) + ".";
  }
  out.actions.push_back(a);
  return true;
}

AiReply localReply(const std::string& text, uint32_t now, bool ro, bool noAiMode) {
  AiReply r;
  if (localAct(text, now, ro, r)) {
    if (noAiMode)
      r.say = ro ? "Fără AI, dar ora am înțeles-o aici, pe device." : "No AI, but I understood the time right here, on the device.";
    return r;
  }
  r = AiReply();
  r.say = ro ? "Sunt pe „Fără AI”. Am păstrat mesajul în Notițe." : "I'm on \xE2\x80\x9CNo AI\xE2\x80\x9D. I kept your message in Notes.";
  AiAction a;
  a.type = AiAction::NoteCreate;
  a.text = cleanStr(text.c_str(), 300);
  if (!a.text.empty()) r.actions.push_back(a);
  return r;
}

std::string maskKey(const std::string& k) {
  if (k.empty()) return "";
  if (k.size() <= 10) return "\xE2\x80\xA2\xE2\x80\xA2\xE2\x80\xA2\xE2\x80\xA2";
  const size_t pre = k.compare(0, 7, "sk-ant-") == 0 ? 7 : (k.compare(0, 3, "sk-") == 0 ? 3 : 0);
  return k.substr(0, pre) + "\xE2\x80\xA6" + k.substr(k.size() - 4);
}

bool keyLooksValid(AiMode m, const std::string& k) {
  auto tail = [&](size_t from) {
    if (k.size() < from + 16) return false;
    for (size_t i = from; i < k.size(); ++i)
      if (!(isalnum((unsigned char)k[i]) || k[i] == '_' || k[i] == '-')) return false;
    return true;
  };
  if (m == AiMode::Claude) return k.compare(0, 7, "sk-ant-") == 0 && tail(7);
  if (m == AiMode::ChatGpt) return k.compare(0, 3, "sk-") == 0 && tail(3);
  return !k.empty();
}

}  // namespace suflet
