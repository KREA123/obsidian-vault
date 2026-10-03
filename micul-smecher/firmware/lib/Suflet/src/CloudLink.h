// SOUL Cloud, device side of protocol v1 (docs/07-CONNECT-AI.md §6, rev. 2:
// the contract ai/suflet_ai/{devices,gateway}.py implement). Transport-free:
// this file builds the HTTPS bodies and the WebSocket frames and reads the
// cloud's answers; CloudSession keeps the state, the device / the simulator
// do the I/O. Everything here is testable on the PC.
//
//   identity  device_id = "soul-" + 12 lowercase hex digits of the eFuse MAC;
//             an ECDSA P-256 key made on the device (DeviceKey), pub = b64u
//             of the 65-byte uncompressed point (87 chars)
//   auth      POST /v1/device/challenge {device_id} -> {nonce}
//             sign "soul-auth-v1\n{host}\n{device_id}\n{nonce}" (raw r||s, b64u)
//             POST /v1/device/auth {device_id,pub,nonce,sig,fw,hw,reset} -> token (24 h, RAM only)
//   socket    wss://{BASE}/v1/device/ws, Bearer token, subprotocol soul.v1
//   frames    {"v":1,"t":<type>,...}
//             up:   hello ask abort ack item.add item.state inbox.add pair.ok pair.no
//                   connectors sleep status
//             down: welcome pairing pair.confirm paired unpaired replay.done resync reply
//                   say.delta push added inbox.state config error (ota: must-ignore)
//
// Must-ignore: unknown fields are ignored; unknown types are Msg::Unknown; a
// push with an unknown action is acked ok:false "unsupported". Pushes are
// validated into typed actions: a prompt-injected connector call can at worst
// add a note, a card, a reminder or an alarm the user can see and delete.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

#include "AiProtocol.h"

namespace suflet {

// What /v1/device/challenge and /v1/device/auth answered (§6.2).
struct CloudAuth {
  int status = 0;
  std::string code;   // error.code when status != 200 (bad_nonce, bad_signature, not_enrolled, key_revoked, rate_limited...)
  int retryMs = -1;   // error.retry_ms / Retry-After
  std::string nonce;  // challenge
  std::string token, wsUrl, state, owner;  // auth; state = unpaired | paired | pending
  uint32_t expiresIn = 0, serverTime = 0;
  int trialLeft = -1;
};

struct CloudPush {
  enum Kind : uint8_t { Act, Card, Delete, Unsupported, Invalid } kind = Invalid;
  uint32_t seq = 0;
  std::string action, itemId;
  std::string source;  // origin.kind: connector | shortcut | app | turn | device
  std::string app;     // origin.app: claude | chatgpt | other ("" = none)
  std::string by;      // origin.by: a first name ("" = none)
  std::string say;
  std::string title, body;  // answer.show
  bool missed = false, priv = false, needsAccept = false;
  uint32_t expiresAt = 0;
  AiAction act;  // for Act: the validated action
};

struct CloudReply {
  std::string re, conv;
  AiReply reply;  // say (<= 400), face (the ten faces or ""), no actions: they come as pushes
  std::string provider, brain, title, body, note;
  std::vector<std::string> chips;
  std::vector<uint32_t> seqs;
  int allowanceLeft = -1;
  std::string allowanceUnit;
};

struct CloudError {
  std::string re, code, msg, cid;
  int retryMs = -1;
  AiErr err = AiErr::Upstream;
};

struct CloudWelcome {
  uint32_t serverTime = 0;
  std::string tz, posixTz, state, owner, brain, voice, lang, quietFrom, quietTo, modelClaude, modelOpenai;
  bool connectorsPaused = false;
  int askPerMin = -1, askPerDay = -1, framesPerS = -1;
  int allowanceLeft = -1, trialLeft = -1;
  std::string allowanceRenews;
};

// `config` (and the settings part of `welcome`): only the fields that came
struct CloudConfig {
  bool hasBrain = false, hasVoice = false, hasLang = false, hasName = false, hasTz = false, hasQuiet = false,
       hasModels = false;
  std::string brain, voice, lang, name, tz, posixTz, quietFrom, quietTo, modelClaude, modelOpenai;
};

struct CloudPairing {
  std::string code, url;  // 8 Crockford base32 characters; https://{BASE}/pair#c=...&d=...
  uint32_t expiresIn = 0;
};

struct CloudConfirm {
  std::string pid, name, hint;  // "Pair with {name} ({hint})?"
  uint32_t expiresIn = 0;
};

// what hello says about this SOUL
struct CloudHello {
  std::string fw, hw, lang = "en", brainLocal = "none", power = "usb", tzPosix;
  std::vector<std::string> caps;  // empty = the base SKU set
  uint32_t after = 0;
};

class CloudLink {
 public:
  enum class Msg : uint8_t {
    None, Welcome, Pairing, PairConfirm, Paired, Unpaired, ReplayDone, Resync, Reply, SayDelta, Push, Added,
    InboxState, Config, Error, Unknown, Bad
  };

  // ---- identity / auth (HTTPS, §6.1-6.2) ---------------------------------
  static std::string deviceId(const uint8_t mac[6]);
  static std::string base64url(const uint8_t* data, size_t n);
  static bool base64urlDecode(const std::string& s, std::vector<uint8_t>& out);
  // "https://Soul.Example:443/x" -> "soul.example"; "http://127.0.0.1:8790" -> "127.0.0.1:8790"
  // (lowercase, no scheme, no path, :port only if not 443): the {host} the device signs for
  static std::string hostOf(const std::string& base);
  static std::string authMessage(const std::string& host, const std::string& deviceId, const std::string& nonce);
  static std::string challengeBody(const std::string& deviceId);
  static bool parseChallenge(int status, const char* body, size_t n, CloudAuth& out);
  static std::string authBody(const std::string& deviceId, const std::string& pub, const std::string& nonce,
                              const std::string& sig, const char* fw, const char* hw, bool reset);
  // `allowPlainWs`: the simulator talks to a loopback test cloud over ws://; the device never does
  static bool parseAuth(int status, const char* body, size_t n, CloudAuth& out, bool allowPlainWs = false);

  // What to do after a failed challenge / auth (§6.2 error table).
  struct AuthRetry {
    enum Kind : uint8_t { NewChallenge, Backoff, NotEnrolled, KeyRevoked, Wait } kind = Backoff;
    uint32_t waitMs = 0;
    bool showProblem = false;  // "Can't sign in to SOUL Cloud" (after 3 bad signatures)
  };
  // `failures` counts consecutive failures of this kind (1 = the first)
  static AuthRetry authRetry(const CloudAuth& a, int failures, float rnd);

  // ---- frames up (§6.6) --------------------------------------------------
  static std::string hello(const CloudHello& h);
  // conv "" = null; unsynced: item.add frames still in the queue (<= 10 used)
  static std::string ask(const std::string& id, const std::string& text, const char* lang, const std::string& conv,
                         int timerLeftMin, const std::vector<std::string>& unsynced);
  static std::string ack(uint32_t seq, bool ok, const char* err = nullptr);
  static std::string abort(const std::string& re);
  static std::string status(int rssi, int battery, const char* power, const char* fw, uint32_t freeHeap, bool awake);
  static std::string itemAdd(const std::string& cid, const AiAction& a, uint32_t createdLocal);
  // itemId or cid ("" = absent); state rang|dismissed|snoozed|done|deleted|accepted|rejected
  static std::string itemState(const std::string& itemId, const std::string& cid, const char* state, uint32_t at);
  static std::string inboxAdd(const std::string& cid, const std::string& text, const char* to);
  static std::string pairAnswer(const std::string& pid, bool ok);
  static std::string connectors(bool paused);
  static std::string sleep(uint32_t wakeAt);
  static std::string cid(uint32_t r1, uint32_t r2);  // 16 lowercase hex

  // ---- frames down (§6.7) ------------------------------------------------
  Msg feed(const char* json, size_t n);
  // what the last frame carried (one field set per message type)
  CloudWelcome welcome;
  CloudPairing pairing;
  CloudConfirm confirm;
  std::string owner, ownerHint, unpairedReason;
  uint32_t last = 0;  // replay.done / resync
  CloudReply reply;
  std::string deltaRe, deltaText;
  CloudPush push;
  std::string addedCid, addedItemId;
  int inboxPending = 0, inboxAnswered = 0;
  CloudConfig config;
  CloudError error;

  static AiErr errFromCode(const std::string& code);

  // ---- close codes (§6.4) -------------------------------------------------
  enum class CloseAction : uint8_t { Reconnect, Restart, Reauth, Replaced, Update, Wait };
  static CloseAction onClose(int code);
  // reconnect backoff: 1, 2, 4 ... 60 s (+ 0..30 % jitter from `rnd` 0..1)
  static uint32_t backoffMs(int attempt, float rnd);

  // frame limits: cloud -> device <= 8 KB (we accept 16 KB); device -> cloud <= 10 KB of UTF-8
  static constexpr size_t kMaxIn = 16384, kMaxOut = 10240;
};

}  // namespace suflet
