// SOUL Cloud on the device (docs/07-CONNECT-AI.md §6, protocol v1 rev. 2, as
// implemented by ai/suflet_ai/{devices,gateway}.py): its own FreeRTOS task on
// core 0 keeps one WebSocket to SOUL Cloud while Wi-Fi is up and a cloud
// address is set, whatever the brain (the connector side channel: "your Claude
// puts things on SOUL" works on every brain, even No AI).
//
// The protocol itself is transport-free and tested on the PC
// (lib/Suflet/src/CloudSession.*, CloudLink.*, DeviceKey.*); the simulator
// runs the same code against a real local cloud (sim/sim_cloud.cpp). This
// file is only the ESP transport:
//
//   identity  device_id "soul-<12 hex of the eFuse MAC>"; an ECDSA P-256 key
//             made on the device once Wi-Fi is up (hardware RNG with the radio
//             on), NVS partition `soulid` (priv, pub, rst), never erased by a
//             factory reset, the private key never printed (serial 'K' prints pub)
//   auth      challenge -> signature -> device token, kept in RAM only (24 h)
//   socket    wss://{BASE}/v1/device/ws, Bearer token, subprotocol soul.v1,
//             TLS checked against the ESP certificate bundle, ping every 25 s
//   state     NVS `soulsync`: seq (batched: 10 pushes / 60 s / before sleep),
//             outq (<= 8 KB), conn (connectors paused)
//   fallback  when the socket will not open (3 tries; a proxy that drops upgrades), the same frames go over
//             GET /v1/device/poll + POST /v1/device/send; the socket is tried again every 10 minutes
//   sleep     a paired SOUL in deep sleep wakes every <= 15 minutes for one poll (cloudWakePoll, §6.11)
//
// The render loop never waits on any of this: it posts and polls. Tokens and
// keys are never printed; the log carries frame types, codes and sizes.
#pragma once
#include <stdint.h>

#include <string>

#include "AiProtocol.h"
#include "CloudLink.h"
#include "Os.h"

void cloudBegin(const uint8_t mac[6], const char* fw, const char* hw);
// "https://host" (dev builds: the portal's "SOUL Cloud address"), "" = SOUL Cloud off
void cloudSetBase(const std::string& base);
// what hello says: the device's brain, language and POSIX TZ (a hint; the cloud's zone wins)
void cloudSetPrefs(suflet::AiMode brain, bool ro, const std::string& posixTz);
void cloudSetStatus(int batteryPct, bool awake);
// the account link for the UI (never the token)
void cloudFill(suflet::NetInfo& n);
bool cloudReady();  // welcomed on the socket: a turn can go over it

// one turn over the socket (false: not ready or one is running). viaBridge: brain "bridge" — the cloud hands
// it to the owner's computer (SOUL Bridge, docs/08 §4): 125 s, ask.state waiting -> thinking
bool cloudAsk(const suflet::AiJob& job, bool ro, int timerLeftMin, bool viaBridge = false);
bool cloudPaired();  // signed in and paired with an account
bool cloudPollAnswer(suflet::AiOutcome& out);
// pushes for SoulOS; ack each one after applying it
bool cloudPollPush(suflet::CloudPush& p);
void cloudAck(uint32_t seq, bool ok, const char* err);
// made on SOUL, "Ask my Claude", the pairing answer, the pause switch (touches only)
void cloudSend(const suflet::CloudOut& o, uint32_t localNow, uint32_t epochNow);
bool cloudPollConfig(suflet::CloudConfig& c);
bool cloudPollTz(std::string& posixTz);  // welcome / config posix_tz, when it differs
bool cloudPollTime(uint32_t& epoch);     // welcome.server_time (UTC epoch)

std::string cloudPubKey();  // b64u public key, for the factory station / support (never the private key)
std::string cloudDeviceId();
// SOULKEY GEN (the factory station): make the device key now if there is none. Hardware RNG with the
// bootloader entropy source when Wi-Fi is off. 1 = made, 0 = there already, -1 = failed.
int cloudKeyGenerate();
void cloudSleep(uint32_t wakeAtEpoch);  // before deep sleep: `sleep`, save seq + queue
// §6.11 wake-poll: this boot is a deep-sleep timer wake. Sign in, GET /v1/device/poll once (no socket, no
// hello); the pushes reach SoulOS through cloudPollPush; after the acks, one POST with the acks, the queue and
// `sleep {nextWakeEpoch}`. Done (or failed) -> cloudWakePollDone().
void cloudWakePoll(uint32_t nextWakeEpoch);
bool cloudWakePollDone();
void cloudWakePollAgain(uint32_t nextWakeEpoch);  // an alarm arrived: the next wake moves earlier
void cloudWakePollCancel();                       // a touch woke SOUL: back to the socket
void cloudForget();  // factory reset: seq, queue and token go, soulid/rst = 1; the key stays
