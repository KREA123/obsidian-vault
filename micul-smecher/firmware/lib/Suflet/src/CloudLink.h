// SOUL Cloud, device side of protocol v1 (docs/07-CONNECT-AI.md §2 and §6).
// Transport-free like ClaudeLink: the device's network task feeds it the
// text frames it receives on the WebSocket (or from the long-poll fallback)
// and sends the frames it builds. Everything here is testable on the PC.
//
//   identity  device_id = "soul-" + 12 lowercase hex digits of the eFuse MAC
//   auth      POST {BASE}/v1/device/auth {device_id, secret, fw, hw} -> token
//   socket    wss://{BASE}/v1/device/ws, Bearer token, subprotocol soul.v1
//   frames    {"v":1,"t":<type>,...}: hello / ask / ack / abort / item.add /
//             inbox.add / status up; welcome / pairing / paired / unpaired /
//             reply / say.delta / push / config / error down
//
// Must-ignore: unknown fields are ignored; unknown types are reported as
// Msg::Unknown; a push with an unknown action is acked ok:false "unsupported".
// Pushes are applied once (deduplicated by seq) and only as the typed,
// validated actions below: a prompt-injected connector call can at worst add
// a note, a card, a reminder or an alarm the user can see and delete.
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

#include "AiProtocol.h"

namespace suflet {

struct CloudPush {
  enum Kind : uint8_t { Act, Card, Delete, Unsupported, Invalid } kind = Invalid;
  uint32_t seq = 0;
  std::string action, itemId, source, say;
  std::string title, body;  // answer.show / an optional card
  bool missed = false;
  AiAction act;  // for Act: the validated action
};

struct CloudReply {
  std::string re;
  AiReply reply;  // say, face (the ten faces or ""), no actions: they come as pushes
  std::string provider, brain, title, body, note;
  std::vector<uint32_t> seqs;
  int allowanceLeft = -1;
  std::string allowanceUnit;
};

struct CloudError {
  std::string re, code, msg;
  int retryMs = -1;
  AiErr err = AiErr::Upstream;
};

struct CloudAuth {
  std::string token, wsUrl, owner, pairCode, pairUrl;
  uint32_t expiresIn = 0, serverTime = 0, pairExpires = 0;
  bool paired = false;
};

class CloudLink {
 public:
  enum class Msg : uint8_t { None, Welcome, Pairing, Paired, Unpaired, Reply, SayDelta, Push, Config, Error, Unknown, Bad };

  // ---- identity / auth (HTTPS) -------------------------------------------
  static std::string deviceId(const uint8_t mac[6]);
  static std::string authBody(const std::string& deviceId, const std::string& secretB64, const char* fw,
                              const char* hw);
  // false: no token (status says why: 401 wrong secret, 409 claimed, 429)
  static bool parseAuth(int status, const char* body, size_t n, CloudAuth& out);
  static std::string base64url(const uint8_t* data, size_t n);

  // ---- frames up ---------------------------------------------------------
  std::string hello(const char* fw, const char* hw, const char* brain, const char* lang, const char* tz) const;
  std::string ask(const std::string& id, const std::string& text, const char* lang, const AiContext& ctx) const;
  std::string ack(uint32_t seq, bool ok, const char* err = nullptr) const;
  std::string abort(const std::string& re) const;
  std::string status(int battery, int rssi, bool awake, const char* fw, uint32_t freeHeap) const;
  std::string itemAdd(const std::string& cid, const AiAction& a, uint32_t createdLocal) const;
  std::string inboxAdd(const std::string& cid, const std::string& text, const char* to) const;

  // ---- frames down -------------------------------------------------------
  Msg feed(const char* json, size_t n);
  // what the last frame carried
  uint32_t serverTime = 0;
  std::string tz, posixTz, owner, brain, lang, name, modelClaude, modelOpenai;
  bool paired = false;
  std::string pairCode, pairUrl;
  uint32_t pairExpires = 0;
  CloudReply reply;
  std::string deltaRe, deltaText;
  CloudPush push;
  CloudError error;
  int limitAskPerMin = -1;

  // ---- ordering ----------------------------------------------------------
  uint32_t lastSeq = 0;           // highest applied push seq (persist it, batched)
  bool alreadyApplied(uint32_t seq) const;  // a replayed push: ack it again, do not apply
  void applied(uint32_t seq);
  // NVS soulid/seq is written batched (every 10 pushes or 60 s, and before
  // sleep), never per push: flash writes stall the RGB panel on this board
  bool seqSaveDue(uint32_t nowMs) const;
  void seqSaved(uint32_t nowMs);

  // ---- close codes -------------------------------------------------------
  enum class CloseAction : uint8_t { Reconnect, Reauth, Unpaired, Update, Wait };
  static CloseAction onClose(int code);
  // reconnect backoff: 1, 2, 4 ... 60 s (+ 0..30 % jitter from `rnd` 0..1)
  static uint32_t backoffMs(int attempt, float rnd);

  static AiErr errFromCode(const std::string& code);

 private:
  uint32_t sinceSave_ = 0, savedAtMs_ = 0;
};

}  // namespace suflet
