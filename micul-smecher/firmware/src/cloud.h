// SOUL Cloud on the device (docs/07-CONNECT-AI.md §6, protocol v1): its own
// FreeRTOS task on core 0 keeps one WebSocket to SOUL Cloud while Wi-Fi is up
// and a cloud address is set, whatever the brain (the connector side channel:
// "your Claude puts things on SOUL" works on every brain, even No AI).
//
//   identity  device_id "soul-<12 hex of the eFuse MAC>"; a 32-byte secret made
//             on first use after Wi-Fi is up (the RNG is a true RNG with the
//             radio on), NVS soulid/sec; the device token in soulid/tok
//   socket    wss://{BASE}/v1/device/ws, Bearer token, subprotocol soul.v1,
//             TLS checked against the ESP certificate bundle, ping every 25 s,
//             reconnect 1..60 s + jitter, close codes 4401/4403/4426/4429
//   pushes    deduplicated by seq, handed to the render loop, acked after
//             SoulOS applied them; last seq saved batched (10 pushes / 60 s)
//   up        ask (one turn, 25 s), item.add (things made on SOUL, queued
//             offline, NVS soulid/outq), inbox.add ("Ask my Claude"), status
//
// The render loop never waits on any of this: it posts and polls. Tokens and
// secrets are never printed; the log carries frame types, codes and sizes.
#pragma once
#include <stdint.h>

#include <string>

#include "AiProtocol.h"
#include "CloudLink.h"
#include "Os.h"

struct CloudConfigMsg {
  std::string brain, lang, name, modelClaude, modelOpenai;
};

void cloudBegin(const uint8_t mac[6], const char* fw, const char* hw);
// "https://host" (the portal's "SOUL Cloud address"), "" = SOUL Cloud off
void cloudSetBase(const std::string& base);
// what hello says: the device's brain, language and POSIX TZ
void cloudSetPrefs(suflet::AiMode brain, bool ro, const std::string& posixTz);
void cloudSetStatus(int batteryPct, bool awake);
// the account link for the UI (never the token)
void cloudFill(suflet::NetInfo& n);
bool cloudReady();  // welcomed on the socket: a turn can go over it

// one turn over the socket (false: not ready or one is running)
bool cloudAsk(const suflet::AiJob& job, bool ro);
bool cloudPollAnswer(suflet::AiOutcome& out);
// pushes for SoulOS; ack each one after applying it
bool cloudPollPush(suflet::CloudPush& p);
void cloudAck(uint32_t seq, bool ok, const char* err);
// made on SOUL / "Ask my Claude"
void cloudSend(const suflet::CloudOut& o);
bool cloudPollConfig(CloudConfigMsg& c);
bool cloudPollTz(std::string& posixTz);  // welcome.posix_tz, when it differs

// the device token for the legacy POST /v1/ask fallback (net task). Callers
// wipe their copy after the request. Empty when there is none.
std::string cloudToken();
void cloudSleep();   // before deep sleep: save seq + queue, close the socket
void cloudForget();  // factory reset: token, seq and queue go; the identity secret stays
