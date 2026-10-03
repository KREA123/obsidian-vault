#include "BridgeLink.h"

#include <ArduinoJson.h>
#include <stdio.h>
#include <string.h>

#include "CloudLink.h"
#include "DeviceKey.h"

namespace suflet {

namespace {

std::string dump(const JsonDocument& d) {
  std::string s;
  serializeJson(d, s);
  return s;
}

AiErr errOf(const char* code) {
  if (!strcmp(code, "timeout")) return AiErr::Timeout;
  if (!strcmp(code, "claude_unavailable")) return AiErr::BridgeOffline;
  if (!strcmp(code, "busy")) return AiErr::RateLimited;
  return AiErr::Upstream;
}

}  // namespace

uint32_t BridgeServer::rand32() {
  if (rng) return rng();
  rngState_ ^= rngState_ << 13;  // tests only: the device passes its hardware RNG
  rngState_ ^= rngState_ >> 17;
  rngState_ ^= rngState_ << 5;
  return rngState_;
}

std::string BridgeServer::randomToken() {
  uint8_t b[32];
  for (int i = 0; i < 32; i += 4) {
    const uint32_t r = rand32();
    for (int k = 0; k < 4; ++k) b[i + k] = (uint8_t)(r >> (8 * k));
  }
  std::string t = "sbt_" + CloudLink::base64url(b, sizeof b);
  DeviceKey::wipe(b, sizeof b);
  return t;
}

// ------------------------------------------------------------ persistence ---

std::string BridgeServer::saveTokens() const {
  std::string s;
  for (const std::string& h : hashes_) s += h + "\n";
  return s;
}

void BridgeServer::loadTokens(const std::string& s) {
  hashes_.clear();
  size_t i = 0;
  while (i < s.size() && hashes_.size() < kMaxTokens) {
    size_t e = s.find('\n', i);
    if (e == std::string::npos) e = s.size();
    const std::string h = s.substr(i, e - i);
    if (h.size() == 64) hashes_.push_back(h);
    i = e + 1;
  }
  tokensDirty = false;
}

// ---------------------------------------------------------------- pairing ---

std::string BridgeServer::newCode(uint32_t nowMs) {
  char b[8];
  snprintf(b, sizeof b, "%06lu", (unsigned long)(rand32() % 1000000u));
  code_ = b;
  codeUntil_ = nowMs + kCodeMs;
  codeTries_ = 0;
  return code_;
}

std::string BridgeServer::code(uint32_t nowMs) const {
  return !code_.empty() && (int32_t)(codeUntil_ - nowMs) > 0 ? code_ : std::string();
}

void BridgeServer::forget() {
  hashes_.clear();
  tokensDirty = true;
  code_.clear();
  if (active_ >= 0) {
    deny(active_, "forgotten on SOUL: pair again");
    active_ = -1;
    computer_.clear();
  }
  if (!askId_.empty()) finish(AiErr::BridgeOffline);
}

// -------------------------------------------------------------- transport ---

void BridgeServer::onOpen(int conn, uint32_t nowMs) {
  if (conns_.size() >= kMaxConns) {  // a flood of half-open connections: refuse the newcomer
    close(conn);
    return;
  }
  Conn c;
  c.id = conn;
  c.openedAt = nowMs;
  conns_.push_back(c);
}

void BridgeServer::onClose(int conn) {
  for (size_t i = 0; i < conns_.size(); ++i)
    if (conns_[i].id == conn) {
      conns_.erase(conns_.begin() + (long)i);
      break;
    }
  if (conn == active_) {
    active_ = -1;
    computer_.clear();
    if (!askId_.empty()) finish(AiErr::BridgeOffline);
  }
}

void BridgeServer::deny(int conn, const char* reason) {
  JsonDocument d;
  d["t"] = "bridge.denied";
  d["reason"] = reason;
  send(conn, dump(d));
  close(conn);
}

void BridgeServer::onText(int conn, const char* s, size_t n, uint32_t nowMs) {
  Conn* c = nullptr;
  for (Conn& x : conns_)
    if (x.id == conn) c = &x;
  if (!c) return;
  JsonDocument d;
  if (!s || !n || n > kMaxFrame || deserializeJson(d, s, n, DeserializationOption::NestingLimit(6)) ||
      !d.is<JsonObject>()) {
    if (!c->hello) close(conn);
    return;
  }
  const char* t = d["t"] | "";
  if (!c->hello) {  // the first frame: pair or hello, nothing else
    if (!strcmp(t, "bridge.pair")) {
      const std::string want = code(nowMs);
      const char* got = d["code"] | "";
      if (want.empty()) {
        deny(conn, "no code on SOUL: open Settings > AI > My Claude on my computer");
        return;
      }
      if (want != got) {
        if (++codeTries_ >= 5) code_.clear();  // 5 tries, then a new code is needed
        deny(conn, "wrong code");
        return;
      }
      code_.clear();
      std::string token = randomToken();
      if (hashes_.size() >= kMaxTokens) hashes_.erase(hashes_.begin());  // the oldest computer goes
      hashes_.push_back(DeviceKey::sha256Hex(token));
      tokensDirty = true;
      JsonDocument r;
      r["t"] = "bridge.paired";
      r["token"] = token;
      r["device_id"] = deviceId;
      r["name"] = name;
      send(conn, dump(r));
      DeviceKey::wipe(&token[0], token.size());
      close(conn);
      return;
    }
    if (!strcmp(t, "bridge.hello")) {
      const char* tok = d["token"] | "";
      const std::string h = strncmp(tok, "sbt_", 4) == 0 && strlen(tok) <= 128 ? DeviceKey::sha256Hex(tok) : "";
      bool known = false;
      for (const std::string& x : hashes_) known = known || (!h.empty() && x == h);
      if (!known) {
        deny(conn, "unknown bridge: pair again");
        return;
      }
      c->hello = true;
      if (active_ >= 0 && active_ != conn) {
        close(active_);  // one bridge per SOUL: the newest wins
        if (!askId_.empty()) finish(AiErr::BridgeOffline);
      }
      active_ = conn;
      computer_ = cleanText(d["label"] | (d["bridge"] | "computer"), 40);  // the bridge's host name, if it says
      JsonDocument w;
      w["t"] = "bridge.welcome";
      w["device_id"] = deviceId;
      w["name"] = name;
      w["lang"] = lang;
      w["tz"] = tz;
      send(conn, dump(w));
      return;
    }
    close(conn);
    return;
  }
  if (conn != active_) return;
  const char* id = d["id"] | "";
  if (askId_.empty() || askId_ != id) return;  // an answer for a turn that ended: ignore
  if (!strcmp(t, "ask.ack")) {
    askState_ = 2;
    return;
  }
  if (!strcmp(t, "answer.error")) {
    finish(errOf(d["code"] | ""));
    return;
  }
  if (strcmp(t, "answer") != 0) return;
  AiOutcome o;
  o.httpStatus = 200;
  o.reply.say = cleanText(d["text"] | "", 1200);
  o.raw = o.reply.say;
  int bad = 0;
  for (JsonVariantConst a : d["actions"].as<JsonArrayConst>()) {
    if (o.reply.actions.size() >= 5) break;
    std::string type = a["type"] | "";
    std::string args;
    serializeJson(a["args"], args);
    if (type == "list.add") {  // no list on the device: a note, like the cloud does
      JsonDocument nd;
      std::string text = std::string(a["args"]["list"] | "list") + ":";
      for (JsonVariantConst it : a["args"]["items"].as<JsonArrayConst>()) text += std::string(" ") + (it | "");
      nd["text"] = text;
      type = "note.create";
      args = dump(nd);
    }
    if (type == "answer.show" || type == "message.draft") {  // the answer text already shows: a card body adds to it
      const std::string body = cleanText(a["args"]["body"] | (a["args"]["text"] | ""), 600);
      if (!body.empty() && o.reply.say.find(body) == std::string::npos) o.reply.say += "\n" + body;
      continue;
    }
    CloudPush p;
    if (CloudLink::mapActionJson(type, args, p) && p.kind == CloudPush::Act) o.reply.actions.push_back(p.act);
    else ++bad;
  }
  o.reply.rejected = bad;
  if (o.reply.say.empty()) o.reply.say = "…";
  o.reply.face = o.reply.actions.empty() ? "" : "happy";
  JsonDocument ack;
  ack["t"] = "answer.ack";
  ack["id"] = askId_;
  ack["shown"] = true;
  send(conn, dump(ack));
  askId_.clear();
  askState_ = 0;
  answer_ = o;
  ready_ = true;
}

bool BridgeServer::nextOut(BridgeOut& o) {
  if (out_.empty()) return false;
  o = out_.front();
  out_.pop_front();
  return true;
}

void BridgeServer::tick(uint32_t nowMs) {
  for (const Conn& c : conns_)
    if (!c.hello && nowMs - c.openedAt > kFirstFrameMs) close(c.id);
  if (!askId_.empty() && nowMs - askAt_ > kAnswerMs) {
    if (active_ >= 0) {
      JsonDocument d;
      d["t"] = "ask.cancel";
      d["id"] = askId_;
      send(active_, dump(d));
    }
    finish(AiErr::Timeout);
  }
}

// ------------------------------------------------------------------ turns ---

bool BridgeServer::ask(const std::string& text, bool ro, const std::string& nowLocal, uint32_t nowMs) {
  if (active_ < 0 || !askId_.empty()) return false;
  char id[24];
  snprintf(id, sizeof id, "q%lu%04lx", (unsigned long)++askSeq_, (unsigned long)(rand32() & 0xffff));
  askId_ = id;
  askAt_ = nowMs;
  askState_ = 1;
  ready_ = false;
  JsonDocument d;
  d["t"] = "ask";
  d["id"] = askId_;
  d["text"] = text.substr(0, 2000);
  d["lang"] = ro ? "ro" : "en";
  d["now"] = nowLocal;
  d["tz"] = tz;
  d["from"] = "keyboard";
  send(active_, dump(d));
  return true;
}

void BridgeServer::finish(AiErr err) {
  askId_.clear();
  askState_ = 0;
  answer_ = AiOutcome();
  answer_.err = err;
  ready_ = true;
}

bool BridgeServer::pollAnswer(AiOutcome& out) {
  if (!ready_) return false;
  out = answer_;
  answer_ = AiOutcome();
  ready_ = false;
  return true;
}

}  // namespace suflet
