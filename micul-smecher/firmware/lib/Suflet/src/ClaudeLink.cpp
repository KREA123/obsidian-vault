#include "ClaudeLink.h"

#include <ArduinoJson.h>
#include <string.h>

namespace suflet {

void ClaudeLink::pushOut(const std::string& s) {
  if (outCount_ == 8) {  // drop the oldest; the desktop re-polls anyway
    outHead_ = (outHead_ + 1) % 8;
    --outCount_;
  }
  out_[(outHead_ + outCount_) % 8] = s;
  ++outCount_;
}

bool ClaudeLink::popOutgoing(std::string& line) {
  if (!outCount_) return false;
  line = out_[outHead_];
  outHead_ = (outHead_ + 1) % 8;
  --outCount_;
  return true;
}

void ClaudeLink::ack(const char* cmd, bool ok, uint32_t n, const char* error) {
  JsonDocument o;
  o["ack"] = cmd;
  o["ok"] = ok;
  o["n"] = n;
  if (error) o["error"] = error;
  char buf[160];
  size_t len = serializeJson(o, buf, sizeof(buf) - 2);
  buf[len++] = '\n';
  pushOut(std::string(buf, len));
}

void ClaudeLink::feed(const uint8_t* data, size_t n) {
  for (size_t i = 0; i < n; ++i) {
    const char c = (char)data[i];
    if (c == '\n') {
      if (!rx_.empty()) handleLine(rx_.data(), rx_.size());
      rx_.clear();
    } else if (c != '\r') {
      if (rx_.size() < 8192) rx_.push_back(c);  // turn events are capped at 4 KB
    }
  }
}

void ClaudeLink::setTransportConnected(bool up) {
  transport_ = up;
  if (!up) sinceSnapshot_ = 1e9f;  // tick() tears the state down
}

void ClaudeLink::tick(float dt) {
  clock_ += dt;
  sinceSnapshot_ += dt;
  promptAge_ += dt;
  if (alive_ && sinceSnapshot_ > 30.0f) {  // spec: no snapshot for ~30 s = dead
    alive_ = false;
    if (running_ > 0) q_.push(Ev::ClaudeBusyEnd);
    running_ = total_ = waiting_ = 0;
    if (!promptId_.empty()) {
      promptId_.clear();
      q_.push(Ev::ClaudePromptGone);
    }
    q_.push(Ev::ClaudeDown);
  }
}

float ClaudeLink::localHour() const {
  if (!timeValid_) return -1.0f;
  const int64_t local = epochNow() + tz_;
  const int64_t sod = ((local % 86400) + 86400) % 86400;
  return (float)sod / 3600.0f;
}

bool ClaudeLink::decide(bool approve) {
  if (promptId_.empty()) return false;
  JsonDocument o;
  o["cmd"] = "permission";
  o["id"] = promptId_.c_str();
  o["decision"] = approve ? "once" : "deny";
  char buf[200];
  size_t len = serializeJson(o, buf, sizeof(buf) - 2);
  buf[len++] = '\n';
  pushOut(std::string(buf, len));
  if (approve) {
    ++approvals_;
    if (promptAge_ < 5.0f) q_.push(Ev::ClaudeQuickApprove);  // the buddy's "heart"
  } else {
    ++denials_;
  }
  promptId_.clear();
  q_.push(Ev::ClaudePromptGone);
  return true;
}

void ClaudeLink::handleLine(const char* line, size_t n) {
  JsonDocument doc;
  if (deserializeJson(doc, line, n)) return;  // ignore garbage, keep the link
  if (!doc.is<JsonObject>()) return;

  // ---- one-shot: time sync ----------------------------------------------
  JsonArrayConst t = doc["time"].as<JsonArrayConst>();
  if (!t.isNull() && t.size() >= 2) {
    epoch_ = t[0].as<int64_t>() - (int64_t)clock_;
    tz_ = t[1].as<int32_t>();
    timeValid_ = true;
    return;
  }

  // ---- commands (each expects an ack) -------------------------------------
  const char* cmd = doc["cmd"] | (const char*)nullptr;
  if (cmd) {
    if (!strcmp(cmd, "status")) {
      JsonDocument o;
      o["ack"] = "status";
      o["ok"] = true;
      JsonObject d = o["data"].to<JsonObject>();
      d["name"] = name_.c_str();
      d["sec"] = status.secure;
      if (status.batPct >= 0) {
        JsonObject b = d["bat"].to<JsonObject>();
        b["pct"] = status.batPct;
        b["mV"] = status.batMv;
        b["usb"] = status.usb;
      }
      JsonObject sys = d["sys"].to<JsonObject>();
      sys["up"] = status.uptimeS;
      sys["heap"] = status.heap;
      JsonObject st = d["stats"].to<JsonObject>();
      st["appr"] = approvals_;
      st["deny"] = denials_;
      st["nap"] = status.naps;
      st["lvl"] = level();
      char buf[400];
      size_t len = serializeJson(o, buf, sizeof(buf) - 2);
      buf[len++] = '\n';
      pushOut(std::string(buf, len));
    } else if (!strcmp(cmd, "name")) {
      const char* v = doc["name"] | "";
      if (*v) name_ = v;
      ack("name", *v != 0);
    } else if (!strcmp(cmd, "owner")) {
      const char* v = doc["name"] | "";
      owner_ = v;
      ack("owner", true);
    } else if (!strcmp(cmd, "unpair")) {
      unpair_ = true;
      ack("unpair", true);
    } else if (!strcmp(cmd, "char_begin") || !strcmp(cmd, "file") || !strcmp(cmd, "chunk") ||
               !strcmp(cmd, "file_end") || !strcmp(cmd, "char_end")) {
      // Folder push is not supported in v0: per spec, don't ack char_begin
      // and the desktop tells the user it failed.
    } else {
      ack(cmd, false, 0, "unsupported");
    }
    return;
  }

  // ---- turn events: nothing to show on an eyes-only face (yet) ----------
  if (doc["evt"].is<const char*>()) return;

  // ---- heartbeat snapshot ----------------------------------------------------
  if (!doc["total"].is<int>() && !doc["running"].is<int>()) return;
  sinceSnapshot_ = 0;
  if (!alive_) {
    alive_ = true;
    q_.push(Ev::ClaudeUp);
  }
  const int running = doc["running"] | 0;
  if (running_ == 0 && running > 0) q_.push(Ev::ClaudeBusyStart);
  if (running_ > 0 && running == 0) q_.push(Ev::ClaudeBusyEnd);
  running_ = running;
  total_ = doc["total"] | 0;
  waiting_ = doc["waiting"] | 0;
  msg_ = doc["msg"] | "";

  JsonObjectConst p = doc["prompt"].as<JsonObjectConst>();
  if (!p.isNull()) {
    const char* id = p["id"] | "";
    if (*id && promptId_ != id) {
      promptId_ = id;
      promptTool_ = p["tool"] | "";
      promptHint_ = p["hint"] | "";
      promptAge_ = 0;
      q_.push(Ev::ClaudePrompt);
    }
  } else if (!promptId_.empty()) {  // answered on the desktop
    promptId_.clear();
    q_.push(Ev::ClaudePromptGone);
  }

  if (doc["tokens"].is<uint64_t>()) {
    const uint64_t tok = doc["tokens"].as<uint64_t>();
    if (haveTokens_ && tok / kTokensPerLevel > tokens_ / kTokensPerLevel) q_.push(Ev::ClaudeLevelUp);
    tokens_ = tok;
    haveTokens_ = true;
  }
  tokensToday_ = doc["tokens_today"] | tokensToday_;
}

}  // namespace suflet
