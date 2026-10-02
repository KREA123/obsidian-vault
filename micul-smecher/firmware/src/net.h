// SOUL's network side, on its own FreeRTOS task (core 0): Wi-Fi, the setup
// portal, the clock (NTP), and the AI calls. The render loop never blocks on
// the network: it posts a question and polls for the answer.
//
// Setup without a phone app: SOUL opens a WPA2 access point "SOUL-xxxx"
// (password shown on its screen) with a captive page where you pick the
// Wi-Fi, the AI (SOUL Cloud / your Claude key / your OpenAI key / no AI),
// paste a key and set the time zone. Secrets go to NVS (namespace
// "soulkey"), are never printed, and the page never shows them back (only
// masked: "sk-ant-…a1B2").
//
// AI backends (AiBackend): "direct" calls api.anthropic.com / api.openai.com
// with the key on the device; "cloud" talks to SOUL Cloud (today: the relay
// POST /v1/ask of micul-smecher/ai). The cloud contract (pairing code,
// device token, WebSocket pushes) plugs in as another AiBackend.
#pragma once
#include <stdint.h>

#include <string>

#include "AiProtocol.h"
#include "Os.h"

void netBegin(const char* apName, const std::string& deviceId);
suflet::NetInfo netInfo();  // a snapshot (thread-safe)
void netStartPortal();
void netStopPortal();
void netForgetWifi();
void netSetKey(suflet::AiMode mode, const std::string& key);
void netForgetKeys();
void netSetMode(suflet::AiMode mode);

// AI: one question at a time. false = busy.
bool netAsk(const suflet::AiJob& job);
bool netPollAnswer(suflet::AiOutcome& out);

// The local time from NTP (seconds, "local epoch" like the RTC), 0 = not yet.
uint32_t netLocalTime();
// Portal: the page asked SOUL to change the name / language (applied by main).
bool netPollPortalSettings(std::string& name);

// Voice (SUFLET_VOICE=1, needs the INMP441 mic and an OpenAI key or SOUL
// Cloud): transcribe 16 kHz mono PCM. The answer arrives on netPollVoice.
bool netTranscribe(const int16_t* pcm, size_t samples, bool ro);
bool netPollVoice(std::string& text, suflet::AiErr& err);

struct AiBackend {
  virtual ~AiBackend() {}
  virtual const char* name() const = 0;
  // Blocking (runs on the network task). Fills the outcome, never throws.
  virtual suflet::AiOutcome ask(const suflet::AiConfig& cfg, const suflet::AiJob& job, uint32_t localNow) = 0;
};
