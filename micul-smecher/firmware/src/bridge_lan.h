// SOUL Bridge on the home network (docs/08-OWN-CLAUDE.md §4, LAN transport): while the brain is
// "My Claude on my computer", SOUL serves ws://soul-xxxx.local:8765/bridge (ESP-IDF esp_http_server with
// WebSocket support, mDNS name soul-xxxx + service _soul._tcp) and the owner's SOUL Bridge connects to it.
// The protocol is lib/Suflet/src/BridgeLink.* (transport-free, tested on the PC); this file is the transport.
//
// Only SHA-256 hashes of the bridge tokens are kept (NVS namespace "soulbridge", key "tok"). Plain ws:// on the
// home network only: the bridge refuses ws:// to anything but .local / private addresses. Nothing here is a
// Claude credential.
#pragma once
#include <stdint.h>

#include <string>

#include "AiProtocol.h"
#include "Os.h"

void bridgeLanBegin(const std::string& deviceId, const char* hostName);  // once, at boot (does not listen yet)
// listen while `on` (brain = Bridge and Wi-Fi up), stop otherwise; call often (the render loop)
void bridgeLanTick(bool on, const std::string& name, bool ro, const std::string& posixTz);
void bridgeLanNewCode();  // a 6-digit pairing code for `soul-bridge pair`, 120 s
void bridgeLanForget();   // every paired computer goes
void bridgeLanFill(suflet::NetInfo& n);
bool bridgeLanOnline();
bool bridgeLanAsk(const suflet::AiJob& job, bool ro, uint32_t localNow);
bool bridgeLanPollAnswer(suflet::AiOutcome& out);
