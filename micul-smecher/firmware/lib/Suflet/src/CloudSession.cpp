#include "CloudSession.h"

#include <ArduinoJson.h>
#include <stdio.h>
#include <string.h>

namespace suflet {

namespace {
constexpr uint32_t kAskMs = 25000;       // §6.6: give up after 25 s
constexpr uint32_t kBridgeAskMs = 125000;  // docs/08 §4: the computer answers within 120 s (+ the way back)
constexpr uint32_t kPollWaitIdleS = 8;     // long-poll: how long one poll may hang when nothing goes up
constexpr uint32_t kPollRetryWsMs = 600000;  // long-poll: try the socket again every 10 min
constexpr uint32_t kConvMs = 600000;     // reuse `conv` for 10 min
constexpr uint32_t kStatusMs = 600000;   // status at least every 10 min
constexpr size_t kOutqMax = 50, kOutqBytes = 8192;
constexpr size_t kPushesMax = 32;

bool isItemAdd(const std::string& f) { return f.find("\"t\":\"item.add\"") != std::string::npos; }
bool isState(const std::string& f) { return f.find("\"t\":\"item.state\"") != std::string::npos; }
}  // namespace

// ------------------------------------------------------------- budgets ---

bool CloudSession::Bucket::take(uint32_t nowMs) {
  tokens += (float)(nowMs - at) / 1000.0f * perS;
  if (tokens > cap) tokens = cap;
  at = nowMs;
  if (tokens < 1.0f) return false;
  tokens -= 1.0f;
  return true;
}

uint32_t CloudSession::rand32() {
  if (rng) return rng();
  rngState_ ^= rngState_ << 13;  // only when the device gave no RNG (tests)
  rngState_ ^= rngState_ >> 17;
  rngState_ ^= rngState_ << 5;
  return rngState_;
}

// --------------------------------------------------------- persistence ---

bool CloudSession::seqSaveDue(uint32_t nowMs) const {
  return sinceSave_ && (sinceSave_ >= 10 || nowMs - savedAtMs_ >= 60000u);
}

void CloudSession::seqSaved(uint32_t nowMs) {
  sinceSave_ = 0;
  savedAtMs_ = nowMs;
}

void CloudSession::applied(uint32_t seq) {
  if (seq > lastSeq) lastSeq = seq;
  ++sinceSave_;
}

std::string CloudSession::saveOutq() const {
  std::string s;
  for (auto it = outq_.rbegin(); it != outq_.rend(); ++it) {  // newest first, within 8 KB
    if (s.size() + it->frame.size() + 1 > kOutqBytes) break;
    s = it->frame + (s.empty() ? "" : "\n") + s;
  }
  return s;
}

void CloudSession::loadOutq(const std::string& s) {
  outq_.clear();
  size_t i = 0;
  while (i < s.size() && outq_.size() < kOutqMax) {
    size_t e = s.find('\n', i);
    if (e == std::string::npos) e = s.size();
    const std::string f = s.substr(i, e - i);
    i = e + 1;
    JsonDocument d;
    if (f.empty() || deserializeJson(d, f) || !d.is<JsonObject>()) continue;
    Out o;
    o.frame = f;
    o.cid = d["cid"] | "";
    o.state = isState(f);
    if (o.cid.empty() && !o.state) continue;
    outq_.push_back(o);
  }
  outqDirty = false;
}

void CloudSession::dropOut(const std::string& cid) {
  if (cid.empty()) return;
  for (auto it = outq_.begin(); it != outq_.end(); ++it)
    if (!it->state && it->cid == cid) {
      outq_.erase(it);
      outqDirty = true;
      return;
    }
}

std::vector<std::string> CloudSession::unsynced() const {
  std::vector<std::string> v;
  for (const Out& o : outq_)
    if (v.size() < 10 && isItemAdd(o.frame)) v.push_back(o.frame);
  return v;
}

// -------------------------------------------------------------- socket ---

std::string CloudSession::onOpen(uint32_t nowMs) {
  open_ = true;
  wake_ = false;
  welcomed_ = replayDone_ = false;
  openedAt_ = helloAt_ = nowMs;
  ctl_.clear();
  for (Out& o : outq_) o.sent = false;
  frames_ = Bucket();
  frames_.cap = 10;
  frames_.perS = 2;
  frames_.tokens = 9;  // the hello takes one
  frames_.at = nowMs;
  ackBudget_ = Bucket();
  ackBudget_.cap = ackBudget_.tokens = 120;  // a replay burst is <= 50 pushes
  ackBudget_.perS = 20;
  ackBudget_.at = nowMs;
  CloudHello h = prefs;
  h.after = lastSeq;
  return CloudLink::hello(h);
}

void CloudSession::beginWakePoll(uint32_t nowMs) {
  onOpen(nowMs);  // budgets and a fresh outq round; the hello it builds is not sent (§6.11: no hello)
  wake_ = true;
}

void CloudSession::endWakePoll() {
  wake_ = false;
  open_ = false;
  ctl_.clear();
}

void CloudSession::answerError(AiErr e, bool noLocal) {
  askPending_ = false;
  askState_ = 0;
  answer_ = AiOutcome();
  answer_.err = e;
  answer_.noLocal = noLocal;
  answerReady_ = true;
}

CloudLink::Msg CloudSession::onText(const char* s, size_t n, uint32_t nowMs) {
  const CloudLink::Msg m = link_.feed(s, n);
  switch (m) {
    case CloudLink::Msg::Welcome: {
      const CloudWelcome& w = link_.welcome;
      welcomed_ = true;
      state = w.state;
      owner = state == "paired" ? w.owner : std::string();
      trialLeft = w.trialLeft;
      allowanceLeft = w.allowanceLeft;
      if (!w.quietFrom.empty() && !w.quietTo.empty()) {
        quietFrom = w.quietFrom;
        quietTo = w.quietTo;
      }
      if (w.framesPerS > 0) frames_.perS = (float)w.framesPerS;
      if (!w.posixTz.empty() && w.posixTz != prefs.tzPosix) {  // the cloud's time zone always wins (§6.7)
        tzNew_ = w.posixTz;
        tzReady_ = true;
        prefs.tzPosix = w.posixTz;
      }
      if (w.serverTime) {
        serverTime_ = w.serverTime;
        timeReady_ = true;
      }
      config_ = CloudConfig();
      if (state == "paired") {  // the account page is the source of truth once paired
        // ... except right after the owner picked a brain on SOUL itself: that wins until the cloud has it
        if (!brainWanted.empty() && w.brain != brainWanted) {
          queue(CloudLink::brain(brainWanted.c_str()));
        } else {
          brainWanted.clear();
          config_.hasBrain = !w.brain.empty();
          config_.brain = w.brain;
        }
        config_.hasVoice = !w.voice.empty();
        config_.voice = w.voice;
        config_.hasLang = !w.lang.empty();
        config_.lang = w.lang;
      }
      config_.hasModels = !w.modelClaude.empty() || !w.modelOpenai.empty();
      config_.modelClaude = w.modelClaude;
      config_.modelOpenai = w.modelOpenai;
      configReady_ = true;
      if (state == "paired" && w.connectorsPaused != connectorsPaused)
        queue(CloudLink::connectors(connectorsPaused));  // the device's own switch wins
      statusDirty_ = true;
      break;
    }
    case CloudLink::Msg::Pairing:
      pairCode = link_.pairing.code;
      pairUrl = link_.pairing.url;
      if (state == "paired") state = "unpaired";
      confirm = CloudConfirm();
      break;
    case CloudLink::Msg::PairConfirm:
      if (confirm.pid != link_.confirm.pid) {  // the same pid after a reconnect is the same request
        confirm = link_.confirm;
        confirmUntil_ = nowMs + (confirm.expiresIn ? confirm.expiresIn : 120) * 1000u;
      }
      break;
    case CloudLink::Msg::Paired:
      state = "paired";
      owner = link_.owner;
      pairCode.clear();
      pairUrl.clear();
      confirm = CloudConfirm();
      trialLeft = -1;
      break;
    case CloudLink::Msg::Unpaired:
      state = "unpaired";  // local items stay (§6.3)
      owner.clear();
      conv.clear();
      confirm = CloudConfirm();
      break;
    case CloudLink::Msg::ReplayDone: replayDone_ = true; break;
    case CloudLink::Msg::Resync:  // the cloud was restored from a backup: its last seq is ours now
      lastSeq = link_.last;
      sinceSave_ = 10;
      break;
    case CloudLink::Msg::Reply: {
      const CloudReply& r = link_.reply;
      if (!r.conv.empty()) {
        conv = r.conv;
        convAt_ = nowMs;
      }
      if (r.allowanceLeft >= 0) allowanceLeft = r.allowanceLeft;
      if (!askPending_ || r.re != askId_) break;  // an aborted turn: ignore
      askPending_ = false;
      askState_ = 0;
      answer_ = AiOutcome();
      answer_.httpStatus = 200;
      answer_.reply.say = r.reply.say;
      answer_.reply.face = r.reply.face;
      if (!r.body.empty()) answer_.reply.say += (answer_.reply.say.empty() ? "" : "\n") + r.body;
      answer_.raw = r.reply.say;
      if (!r.note.empty()) answer_.note = CloudLink::errFromCode(r.note);
      answerReady_ = true;
      break;
    }
    case CloudLink::Msg::Push: {
      const CloudPush& p = link_.push;
      if (p.seq <= lastSeq) {  // a replay of something applied: ack again, never apply twice
        acks_.push_back(CloudLink::ack(p.seq, true));
        break;
      }
      bool inFlight = false;
      for (uint32_t q : inFlight_) inFlight = inFlight || q == p.seq;
      if (inFlight) break;  // SoulOS has it; its ack follows
      const bool fromOutside = p.source == "connector" || p.source == "shortcut";
      const char* err = p.kind == CloudPush::Unsupported ? "unsupported"
                        : p.kind == CloudPush::Invalid    ? "invalid"
                        : (connectorsPaused && fromOutside) ? "paused"
                                                            : nullptr;
      if (err) {
        acks_.push_back(CloudLink::ack(p.seq, false, err));
        applied(p.seq);
        break;
      }
      if (pushes_.size() >= kPushesMax) break;  // SoulOS is behind: no ack, replayed on the next socket
      pushes_.push_back(p);
      inFlight_.push_back(p.seq);
      if (p.seq > seenSeq_) seenSeq_ = p.seq;
      break;
    }
    case CloudLink::Msg::Added: dropOut(link_.addedCid); break;
    case CloudLink::Msg::InboxState: inboxPending = link_.inboxPending; break;
    case CloudLink::Msg::Config: {
      const CloudConfig& c = link_.config;
      config_ = c;
      if (c.hasBrain) brainWanted.clear();  // the account page changed it after: it wins
      configReady_ = true;
      if (c.hasTz && c.posixTz != prefs.tzPosix) {
        tzNew_ = c.posixTz;
        tzReady_ = true;
        prefs.tzPosix = c.posixTz;
      }
      if (c.hasQuiet && !c.quietFrom.empty()) {
        quietFrom = c.quietFrom;
        quietTo = c.quietTo;
      }
      break;
    }
    case CloudLink::Msg::BridgeCode:
      bridgeCode = link_.bridgeCode.code;
      bridgeCmd = link_.bridgeCode.cmd;
      bridgeCodeUntil_ = nowMs + link_.bridgeCode.expiresIn * 1000u;
      break;
    case CloudLink::Msg::BridgeState:
      bridgePaired = link_.bridgeState.paired;
      bridgeOnline = link_.bridgeState.online;
      bridgeName = link_.bridgeState.name;
      if (bridgeOnline) {  // a computer took the code: it is spent
        bridgeCode.clear();
        bridgeCmd.clear();
      }
      break;
    case CloudLink::Msg::AskState:
      if (askPending_ && link_.askStateRe == askId_) askState_ = link_.askState == "thinking" ? 2 : 1;
      break;
    case CloudLink::Msg::Error: {
      const CloudError& e = link_.error;
      // timeout: what a cloud turn did still arrives as pushes (no rules on top); a bridge turn runs nothing
      // until its answer, so the offline rules may answer instead
      if (askPending_ && !e.re.empty() && e.re == askId_) answerError(e.err, e.code == "timeout" && !askBridge_);
      if (e.code == "rate_limited" && e.retryMs > 0) waitMs_ = e.retryMs;
      if (!e.cid.empty()) {
        if (e.code == "invalid" || e.code == "too_big") {
          dropOut(e.cid);  // never resend what the cloud cannot take
        } else {  // rate_limited / unpaired: keep it, send it again later
          for (Out& o : outq_)
            if (o.cid == e.cid) o.sent = false;
          holdOutqUntil_ = nowMs + (e.retryMs > 0 ? (uint32_t)e.retryMs : 30000u);
        }
      }
      if (e.code == "unpaired" && state == "paired") state = "unpaired";
      break;
    }
    default: break;  // say.delta (we did not ask for streaming), ota, unknown: must-ignore
  }
  return m;
}

bool CloudSession::nextFrame(std::string& out, uint32_t nowMs) {
  if (!open_) return false;
  if (!acks_.empty()) {
    if (!ackBudget_.take(nowMs)) return false;
    out = acks_.front();
    acks_.pop_front();
    return true;
  }
  if (!ctl_.empty()) {
    if (!frames_.take(nowMs)) return false;
    out = ctl_.front();
    ctl_.pop_front();
    return true;
  }
  if (!(welcomed_ || wake_) || state != "paired" || (int32_t)(nowMs - holdOutqUntil_) < 0) return false;
  for (auto it = outq_.begin(); it != outq_.end(); ++it) {
    if (it->sent) continue;
    if (it->frame.size() > CloudLink::kMaxOut) {  // cannot happen with our builders; never resend it
      outq_.erase(it);
      outqDirty = true;
      return false;
    }
    if (!frames_.take(nowMs)) return false;
    out = it->frame;
    if (it->state) {
      outq_.erase(it);  // item.state is fire and forget
      outqDirty = true;
    } else {
      it->sent = true;  // leaves on `added`
    }
    return true;
  }
  return false;
}

CloudSession::Retry CloudSession::onClose(int code, uint32_t nowMs, float rnd) {
  if (welcomed_ && nowMs - openedAt_ >= 60000) attempt_ = 0;  // a minute up: the backoff starts again
  open_ = welcomed_ = replayDone_ = false;
  ctl_.clear();
  if (askPending_) answerError(AiErr::Network, false);
  Retry r;
  switch (CloudLink::onClose(code)) {
    case CloudLink::CloseAction::Restart: r.waitMs = 1000 + (uint32_t)(rnd * 4000); break;
    case CloudLink::CloseAction::Reauth:
      r.kind = Retry::Reauth;
      r.waitMs = 500;
      break;
    case CloudLink::CloseAction::Replaced: r.waitMs = 60000; break;
    case CloudLink::CloseAction::Update:
      r.kind = Retry::Update;
      needUpdate = true;
      r.waitMs = 24u * 3600u * 1000u;
      break;
    case CloudLink::CloseAction::Wait: r.waitMs = waitMs_ > 0 ? (uint32_t)waitMs_ : 30000u; break;
    default: r.waitMs = CloudLink::backoffMs(++attempt_, rnd); break;
  }
  waitMs_ = 0;
  return r;
}

void CloudSession::tick(uint32_t nowMs) {
  if (askPending_ && nowMs - askAt_ > (askBridge_ ? kBridgeAskMs : kAskMs)) {  // too slow: tell the cloud
    queue(CloudLink::abort(askId_));
    answerError(AiErr::Timeout, !askBridge_);  // a cloud turn may still have acted; a bridge turn did nothing
  }
  if (!bridgeCode.empty() && (int32_t)(nowMs - bridgeCodeUntil_) > 0) {
    bridgeCode.clear();
    bridgeCmd.clear();
  }
  if (!confirm.pid.empty() && (int32_t)(nowMs - confirmUntil_) > 0) {  // no touch in time = no
    queue(CloudLink::pairAnswer(confirm.pid, false));
    confirm = CloudConfirm();
  }
  if (welcomed_ && (statusDirty_ || nowMs - statusAt_ > kStatusMs)) {
    statusDirty_ = false;
    statusAt_ = nowMs;
    queue(CloudLink::status(rssi_, battery_, power_.c_str(), prefs.fw.c_str(), freeHeap_, awake_));
  }
}

// ----------------------------------------------------------------- app ---

bool CloudSession::ask(const std::string& text, bool ro, int timerLeftMin, uint32_t nowMs, bool viaBridge) {
  if (!welcomed_ || askPending_) return false;
  askBridge_ = viaBridge;
  askState_ = viaBridge ? 1 : 0;
  char id[24];
  snprintf(id, sizeof id, "a%lu%04lx", (unsigned long)++askSeq_, (unsigned long)(rand32() & 0xffff));
  askId_ = id;
  const std::string c = (!conv.empty() && nowMs - convAt_ < kConvMs) ? conv : std::string();
  queue(CloudLink::ask(askId_, text, ro ? "ro" : "en", c, timerLeftMin, unsynced()));
  askPending_ = true;
  answerReady_ = false;
  askAt_ = nowMs;
  return true;
}

bool CloudSession::pollAnswer(AiOutcome& out) {
  if (!answerReady_) return false;
  out = answer_;
  answer_ = AiOutcome();
  answerReady_ = false;
  return true;
}

bool CloudSession::pollPush(CloudPush& p) {
  if (pushes_.empty()) return false;
  p = pushes_.front();
  pushes_.pop_front();
  return true;
}

void CloudSession::ackPush(uint32_t seq, bool ok, const char* err) {
  acks_.push_back(CloudLink::ack(seq, ok, err));
  applied(seq);
  for (size_t i = 0; i < inFlight_.size(); ++i)
    if (inFlight_[i] == seq) {
      inFlight_.erase(inFlight_.begin() + (long)i);
      break;
    }
}

void CloudSession::trimOutq() {
  while (outq_.size() >= kOutqMax) {  // drop the oldest item.state, never an item.add (§6.10)
    bool dropped = false;
    for (auto it = outq_.begin(); it != outq_.end(); ++it)
      if (it->state) {
        outq_.erase(it);
        dropped = true;
        break;
      }
    if (!dropped) return;
  }
}

void CloudSession::send(const CloudOut& o, uint32_t localNow, uint32_t epochNow) {
  switch (o.kind) {
    case CloudOut::PairOk:
    case CloudOut::PairNo:
      if (confirm.pid.empty() || confirm.pid != o.pid) return;  // expired or answered already
      queue(CloudLink::pairAnswer(o.pid, o.kind == CloudOut::PairOk));
      confirm = CloudConfirm();
      return;
    case CloudOut::Connectors:
      if (connectorsPaused != o.paused) pausedDirty = true;
      connectorsPaused = o.paused;
      if (welcomed_) queue(CloudLink::connectors(o.paused));
      return;
    case CloudOut::BridgeCode:
      if (welcomed_ && state == "paired") queue(CloudLink::bridgeCodeGet());
      return;
    case CloudOut::BridgeForget:
      if (welcomed_ && state == "paired") queue(CloudLink::bridgeForget());
      bridgePaired = bridgeOnline = false;
      bridgeName.clear();
      return;
    case CloudOut::Brain:
      if (o.text != "bridge" && o.text != "none") return;
      brainWanted = o.text;
      if (welcomed_ && state == "paired") queue(CloudLink::brain(o.text.c_str()));
      return;
    default: break;
  }
  trimOutq();
  if (outq_.size() >= kOutqMax) return;  // full of item.add: this one stays on SOUL only
  Out e;
  if (o.kind == CloudOut::State) {
    if (o.itemId.empty() || o.state.empty()) return;
    e.frame = CloudLink::itemState(o.itemId, std::string(), o.state.c_str(), epochNow);
    e.state = true;
  } else {
    const uint32_t r1 = rand32(), r2 = rand32();  // in this order (argument order is unspecified)
    e.cid = CloudLink::cid(r1, r2);
    e.frame = o.kind == CloudOut::Inbox ? CloudLink::inboxAdd(e.cid, o.text, "claude")
                                        : CloudLink::itemAdd(e.cid, o.act, o.created ? o.created : localNow);
  }
  outq_.push_back(e);
  outqDirty = true;
}

bool CloudSession::pollConfig(CloudConfig& c) {
  if (!configReady_) return false;
  c = config_;
  configReady_ = false;
  return true;
}

bool CloudSession::pollTz(std::string& tz) {
  if (!tzReady_) return false;
  tz = tzNew_;
  tzReady_ = false;
  return true;
}

bool CloudSession::pollTime(uint32_t& epoch) {
  if (!timeReady_) return false;
  epoch = serverTime_;
  timeReady_ = false;
  return true;
}

void CloudSession::setStatus(int rssi, int battery, const char* power, uint32_t freeHeap, bool awake) {
  if (awake != awake_ || (battery >= 0) != (battery_ >= 0) || std::string(power ? power : "usb") != power_)
    statusDirty_ = true;
  rssi_ = rssi;
  battery_ = battery;
  power_ = power ? power : "usb";
  freeHeap_ = freeHeap;
  awake_ = awake;
}

void CloudSession::sleep(uint32_t wakeAt) {
  if ((welcomed_ || wake_) && wakeAt) queue(CloudLink::sleep(wakeAt));
}

void CloudSession::fill(NetInfo& n) const {
  n.cloudOnline = welcomed_;
  n.paired = state == "paired";
  n.owner = n.paired ? owner : std::string();
  n.pairCode = n.paired ? std::string() : pairCode;
  n.pairUrl = n.paired ? std::string() : pairUrl;
  n.cloudUpdate = needUpdate;
  n.confirmPid = confirm.pid;
  n.confirmName = confirm.name;
  n.confirmHint = confirm.hint;
  n.connectorsPaused = connectorsPaused;
  n.trialLeft = trialLeft;
  n.inboxPending = inboxPending;
  if (n.paired) {  // the cloud's bridge (the LAN one, if any, is filled in by the device)
    n.bridgeOnline = n.bridgeOnline || bridgeOnline;
    n.bridgePaired = n.bridgePaired || bridgePaired;
    if (bridgeOnline) n.bridgeName = bridgeName;
    if (!bridgeCode.empty()) {
      n.bridgeCode = bridgeCode;
      n.bridgeCmd = bridgeCmd;
    }
  }
  n.askState = askState_;
}

// ============================================================== driver ===

void CloudDriver::forgetToken() {
  Guard g(this);
  for (char& c : token_) c = 0;
  token_.clear();
  tokenUntil_ = 0;
}

void CloudDriver::reconnectNow() {
  waiting_ = false;
  retryAt_ = 0;
}

bool CloudDriver::needToken(uint32_t nowMs) const {
  return token_.empty() || forceReauth_ || (int32_t)(nowMs - tokenUntil_) > 0;
}

std::string CloudDriver::bearer() {
  Guard g(this);
  return "Bearer " + token_;
}

bool CloudDriver::feedMessages(const std::string& body, uint32_t nowMs, bool* more) {
  std::vector<std::string> frames;
  if (!CloudLink::splitMessages(body.data(), body.size(), frames, more)) return false;
  Guard g(this);
  for (const std::string& f : frames) session.onText(f.data(), f.size(), nowMs);
  return true;
}

// POST /v1/device/send with what is waiting; true = sent (the answers are fed to the session)
bool CloudDriver::postFrames(std::vector<std::string>& frames, uint32_t nowMs) {
  if (frames.empty()) return true;
  size_t used = 0;
  const std::string body = CloudLink::sendBody(frames, &used);
  std::string resp, auth = bearer();
  const int st = httpPostAuth(base + "/v1/device/send", auth, body, resp, 30000);
  for (char& c : auth) c = 0;
  if (st == 401) {
    forgetToken();
    forceReauth_ = true;
    return false;
  }
  if (st != 200) return false;
  frames.erase(frames.begin(), frames.begin() + (long)used);
  feedMessages(resp, nowMs);
  return true;
}

// The long-poll transport (§6.4 fallback): hello and everything else go up with POST /send, pushes and the
// rest come down with GET /poll. A turn's reply comes back on the POST that carried the ask (the cloud holds
// it <= 25 s); a SOUL Bridge turn's reply comes with a later poll.
uint32_t CloudDriver::stepPoll(uint32_t nowMs, float rnd) {
  if ((int32_t)(nowMs - pollUntil_) > 0) {  // every 10 minutes: is the socket possible again?
    Guard g(this);
    if (!session.askPending()) {
      pollMode_ = false;
      session.onClose(1000, nowMs, rnd);
      pollOut_.clear();
      log("[cloud] long-poll: trying the socket again");
      return 0;
    }
  }
  if (!keyReady()) {
    retryAt_ = nowMs + 2000;
    waiting_ = true;
    return 200;
  }
  if (needToken(nowMs) && !authenticate(nowMs, rnd)) return 50;
  {
    Guard g(this);
    if (!session.open()) {
      pollOut_.clear();
      pollOut_.push_back(session.onOpen(nowMs));  // the first send carries hello; its answer carries welcome
    }
    session.tick(nowMs);
    std::string f;
    while (pollOut_.size() < 40 && session.nextFrame(f, nowMs)) pollOut_.push_back(f);
  }
  bool ok = postFrames(pollOut_, nowMs);
  bool more = false;
  if (ok) {
    bool pending;
    {
      Guard g(this);
      pending = !pollOut_.empty();
    }
    const int wait = pending ? 0 : (int)kPollWaitIdleS;
    std::string resp, auth = bearer();
    const int st = httpGetAuth(CloudLink::pollUrl(base, session.pollAfter(), wait), auth, resp, (wait + 10) * 1000u);
    for (char& c : auth) c = 0;
    if (st == 200) {
      lastRx_ = nowMs;
      ok = feedMessages(resp, nowMs, &more);
    } else {
      if (st == 401) {
        forgetToken();
        forceReauth_ = true;
      }
      ok = false;
    }
  }
  if (!ok) {
    Guard g(this);
    const CloudSession::Retry r = session.onClose(forceReauth_ ? 4401 : 1006, nowMs, rnd);
    retryAt_ = nowMs + (forceReauth_ ? 500 : CloudLink::backoffMs(++pollFails_, rnd));
    (void)r;
    waiting_ = true;
    return 50;
  }
  pollFails_ = 0;
  return more ? 0 : 10;
}

bool CloudDriver::wakePoll(uint32_t nowMs, float rnd) {
  if (!keyReady() || !supportsPoll()) return false;
  if (needToken(nowMs) && !authenticate(nowMs, rnd)) return false;
  {
    Guard g(this);
    session.beginWakePoll(nowMs);
  }
  for (int page = 0; page < 6; ++page) {  // <= 50 pushes a page; more = at once again
    std::string resp, auth = bearer();
    const int st = httpGetAuth(CloudLink::pollUrl(base, session.pollAfter(), 0), auth, resp, 10000);
    for (char& c : auth) c = 0;
    if (st == 401) {
      forgetToken();
      forceReauth_ = true;
    }
    if (st != 200) return false;
    bool more = false;
    if (!feedMessages(resp, nowMs, &more)) return false;
    if (!more) break;
  }
  return true;
}

bool CloudDriver::wakePollFinish(uint32_t nowMs, uint32_t wakeAt) {
  std::vector<std::string> frames;
  {
    Guard g(this);
    if (!session.wakePolling()) return false;
    session.sleep(wakeAt);
    std::string f;
    while (frames.size() < 40 && session.nextFrame(f, nowMs + 60000)) frames.push_back(f);  // budgets: one burst
  }
  bool ok = true;
  while (ok && !frames.empty()) ok = postFrames(frames, nowMs);
  Guard g(this);
  session.endWakePoll();
  return ok;
}

bool CloudDriver::authenticate(uint32_t nowMs, float rnd) {
  const std::string host = CloudLink::hostOf(base);
  std::string resp;
  int retryAfter = -1;
  CloudAuth a;
  int st = httpPost(base + "/v1/device/challenge", CloudLink::challengeBody(deviceId), resp, retryAfter);
  bool ok = CloudLink::parseChallenge(st, resp.data(), resp.size(), a);
  if (ok) {
    const std::string nonce = a.nonce;
    std::string sig = signB64(CloudLink::authMessage(host, deviceId, nonce));
    const bool reset = resetPending();
    std::string body = CloudLink::authBody(deviceId, pubB64(), nonce, sig, fw.c_str(), hw.c_str(), reset);
    resp.clear();
    retryAfter = -1;
    st = httpPost(base + "/v1/device/auth", body, resp, retryAfter);
    ok = !sig.empty() && CloudLink::parseAuth(st, resp.data(), resp.size(), a, allowPlainWs);
    for (char& c : resp) c = 0;  // it held the token
    if (ok && reset) resetReported();
  }
  if (!ok) {
    if (a.retryMs < 0 && retryAfter > 0) a.retryMs = retryAfter * 1000;
    const std::string kind = std::to_string(a.status) + a.code;
    authFails_ = kind == lastAuthCode_ ? authFails_ + 1 : 1;
    lastAuthCode_ = kind;
    const CloudLink::AuthRetry r = CloudLink::authRetry(a, authFails_, rnd);
    if (r.kind == CloudLink::AuthRetry::NotEnrolled) problem = Problem::NotEnrolled;
    else if (r.kind == CloudLink::AuthRetry::KeyRevoked) problem = Problem::KeyRevoked;
    else if (r.showProblem) problem = Problem::CannotSignIn;
    char line[96];
    snprintf(line, sizeof line, "[cloud] auth: HTTP %d %s, again in %lu s", a.status, a.code.c_str(),
             (unsigned long)(r.waitMs / 1000));
    log(line);
    retryAt_ = nowMs + r.waitMs;
    waiting_ = r.waitMs > 0;
    return false;
  }
  authFails_ = 0;
  lastAuthCode_.clear();
  problem = Problem::None;
  forceReauth_ = false;
  {
    Guard g(this);
    token_ = a.token;
    for (char& c : a.token) c = 0;
    wsUrl_ = a.wsUrl;
    // renew 5 minutes before the 24 h are up
    tokenUntil_ = nowMs + (a.expiresIn > 600 ? a.expiresIn - 300 : 300) * 1000u;
    if (!a.state.empty()) session.state = a.state;
    if (a.state == "paired") session.owner = a.owner;
    session.trialLeft = a.trialLeft;
  }
  log(a.state == "paired" ? "[cloud] signed in (paired)" : "[cloud] signed in (not paired yet)");
  return true;
}

void CloudDriver::closed(int code, uint32_t nowMs, float rnd) {
  connected_ = false;
  CloudSession::Retry r;
  {
    Guard g(this);
    r = session.onClose(code, nowMs, rnd);
  }
  if (r.kind == CloudSession::Retry::Reauth) forceReauth_ = true;
  char line[64];
  snprintf(line, sizeof line, "[cloud] socket closed (%d), again in %lu s", code, (unsigned long)(r.waitMs / 1000));
  log(line);
  retryAt_ = nowMs + r.waitMs;
  waiting_ = r.waitMs > 0;
}

uint32_t CloudDriver::step(uint32_t nowMs, float rnd) {
  if (waiting_ && (int32_t)(retryAt_ - nowMs) > 0) {
    const uint32_t left = retryAt_ - nowMs;
    return left < 200 ? left : 200;
  }
  waiting_ = false;
  if (pollMode_) return stepPoll(nowMs, rnd);
  if (!connected_) {
    if (!keyReady()) {
      retryAt_ = nowMs + 2000;
      waiting_ = true;
      return 200;
    }
    if (token_.empty() || forceReauth_ || (int32_t)(nowMs - tokenUntil_) > 0) {
      if (!authenticate(nowMs, rnd)) return 50;
    }
    std::string url = wsUrl_;
    if (allowPlainWs && base.compare(0, 7, "http://") == 0) url = "ws://" + CloudLink::hostOf(base) + "/v1/device/ws";
    if (url.empty()) url = "wss://" + CloudLink::hostOf(base) + "/v1/device/ws";
    std::string bearer;
    {
      Guard g(this);
      bearer = "Bearer " + token_;
    }
    const int st = wsOpen(url, bearer);
    for (char& c : bearer) c = 0;
    if (st != 0) {
      char line[64];
      snprintf(line, sizeof line, "[cloud] socket refused: %d", st);
      log(line);
      uint32_t wait;
      if (st == 401 || st == 403) {  // the token is no good: sign in again
        forgetToken();
        forceReauth_ = true;
        wait = sockFails_++ ? CloudLink::backoffMs(sockFails_, rnd) : 500;
      } else if (st == 426) {
        Guard g(this);
        session.needUpdate = true;
        wait = 24u * 3600u * 1000u;
      } else {
        wait = CloudLink::backoffMs(++sockFails_, rnd);
        if (sockFails_ >= 3 && supportsPoll()) {  // the socket is blocked here (a proxy?): long-poll (§6.4)
          sockFails_ = 0;
          pollMode_ = true;
          pollUntil_ = nowMs + kPollRetryWsMs;
          log("[cloud] the socket will not open: long-poll");
          return 0;
        }
      }
      retryAt_ = nowMs + wait;
      waiting_ = true;
      return 50;
    }
    sockFails_ = 0;
    connected_ = true;
    lastRx_ = lastPing_ = helloAt_ = nowMs;
    std::string hello;
    {
      Guard g(this);
      session.needUpdate = false;
      hello = session.onOpen(nowMs);
    }
    if (!wsSend(hello)) {
      wsClose();
      closed(1006, nowMs, rnd);
    }
    return 0;
  }
  // ---- connected: what arrived (several frames may wait in the buffers)
  for (int i = 0; i < 8; ++i) {
    std::string text;
    int code = 0;
    const Rd r = wsRead(text, code, i ? 0 : 20);
    if (r == Rd::Nothing) break;
    lastRx_ = nowMs;
    if (r == Rd::Control) continue;  // a ping (answered) or a pong
    if (r == Rd::Closed) {
      wsClose();
      closed(code, nowMs, rnd);
      return 0;
    }
    Guard g(this);
    session.onText(text.data(), text.size(), nowMs);
  }
  // ---- what goes up
  for (int i = 0; i < 64; ++i) {
    std::string f;
    {
      Guard g(this);
      session.tick(nowMs);
      if (!session.nextFrame(f, nowMs)) break;
    }
    if (!wsSend(f)) {
      wsClose();
      closed(1006, nowMs, rnd);
      return 0;
    }
  }
  if (nowMs - lastPing_ >= 25000) {  // §6.4: ping every 25 s
    lastPing_ = nowMs;
    wsPing();
  }
  bool welcomed;
  {
    Guard g(this);
    welcomed = session.welcomed();
  }
  if ((!welcomed && nowMs - helloAt_ > 15000) || nowMs - lastRx_ > 70000) {  // no welcome / a silent socket
    log(welcomed ? "[cloud] silent socket" : "[cloud] no welcome");
    wsClose();
    closed(1006, nowMs, rnd);
    return 0;
  }
  if (tokenUntil_ && (int32_t)(nowMs - tokenUntil_) > 0) authenticate(nowMs, rnd);  // a fresh token for the next socket
  return 10;
}

}  // namespace suflet
