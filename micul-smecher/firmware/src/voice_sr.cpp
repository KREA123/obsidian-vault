#include "voice_sr.h"

#include <Arduino.h>

#ifndef SUFLET_VOICE_SR
#define SUFLET_VOICE_SR 0
#endif
#ifndef SUFLET_VOICE_WAKE
#define SUFLET_VOICE_WAKE 0
#endif

#if SUFLET_VOICE_SR
#include <esp_heap_caps.h>
#include <esp_partition.h>

#include "VoiceCommands.h"
#include "audio.h"
#include "esp32-hal-sr.h"

namespace {

const char* status = "off";
bool ready = false, listening = false;
uint32_t releasedMs = 0;
volatile int heard = -1;
volatile bool wake = false;

esp_err_t fill(void*, void* out, size_t len, size_t* got, uint32_t timeoutMs) {
  *got = audioSrFill((int16_t*)out, len / sizeof(int16_t), timeoutMs) * sizeof(int16_t);
  return *got ? ESP_OK : ESP_FAIL;
}

void onEvent(void*, sr_event_t e, int cmd, int) {
  switch (e) {
    case SR_EVENT_WAKEWORD:
      wake = true;
      sr_set_mode(SR_MODE_COMMAND);
      break;
    case SR_EVENT_COMMAND:
      heard = cmd;
      if (SUFLET_VOICE_WAKE) sr_set_mode(SR_MODE_WAKEWORD);
      break;
    case SR_EVENT_TIMEOUT:
      if (SUFLET_VOICE_WAKE) sr_set_mode(SR_MODE_WAKEWORD);
      break;
    default: break;
  }
}

bool modelFlashed() {
  const esp_partition_t* p = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "model");
  if (!p) return false;
  uint8_t head[16];
  if (esp_partition_read(p, 0, head, sizeof head) != ESP_OK) return false;
  for (uint8_t b : head)
    if (b != 0xFF) return true;  // srmodels.bin is there (an erased partition reads all 0xFF)
  return false;
}

}  // namespace

bool voiceSrBegin() {
  if (!audioHasMic()) {
    status = "off (no mic)";
    return false;
  }
  if (!modelFlashed()) {
    status = "off (no model: flash srmodels.bin at 0xcb0000)";
    return false;
  }
  const size_t freePs = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
  if (freePs < suflet::kVoiceSrPsramNeed) {  // the glass buffers come first: voice stays cloud-only
    status = "off (PSRAM)";
    Serial.printf("[voice] %u KB PSRAM free, MultiNet needs %u KB: offline commands off\n", (unsigned)(freePs / 1024),
                  (unsigned)(suflet::kVoiceSrPsramNeed / 1024));
    return false;
  }
  size_t n = 0;
  const suflet::VoicePhrase* ph = suflet::voicePhrases(n);
  sr_cmd_t* cmds = (sr_cmd_t*)heap_caps_calloc(n, sizeof(sr_cmd_t), MALLOC_CAP_SPIRAM);
  if (!cmds) {
    status = "off (PSRAM)";
    return false;
  }
  for (size_t i = 0; i < n; ++i) {
    cmds[i].command_id = (int)ph[i].cmd;
    strlcpy(cmds[i].str, ph[i].text, sizeof cmds[i].str);
  }
  const uint32_t t0 = millis();
  const esp_err_t e = sr_start(fill, nullptr, SR_CHANNELS_MONO, SUFLET_VOICE_WAKE ? SR_MODE_WAKEWORD : SR_MODE_COMMAND,
                               "MN", cmds, n, onEvent, nullptr);
  heap_caps_free(cmds);  // MultiNet keeps its own phoneme copies
  if (e != ESP_OK) {
    status = "off (start failed)";
    Serial.printf("[voice] ESP-SR start failed: %s\n", esp_err_to_name(e));
    return false;
  }
  if (!SUFLET_VOICE_WAKE) sr_pause();  // push-to-talk: asleep until the glass is held
  ready = true;
  status = "on";
  Serial.printf("[voice] ESP-SR MultiNet7 EN: %u phrases in %lu ms, %u KB PSRAM left, %s\n", (unsigned)n,
                (unsigned long)(millis() - t0), (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024),
                SUFLET_VOICE_WAKE ? "wake word \"Hi ESP\"" : "push-to-talk");
  return true;
}

bool voiceSrReady() { return ready; }

void voiceSrListen(bool on) {
  if (!ready) return;
  if (on) {
    heard = -1;
    listening = true;
    sr_set_mode(SR_MODE_COMMAND);
    if (!SUFLET_VOICE_WAKE) sr_resume();
  } else if (listening) {
    listening = false;
    releasedMs = millis();  // a command said right at the end still lands
  }
}

void voiceSrTick(uint32_t nowMs) {
  if (!ready || SUFLET_VOICE_WAKE || listening || !releasedMs) return;
  if (nowMs - releasedMs > 1200) {
    releasedMs = 0;
    sr_pause();
  }
}

bool voiceSrTake(int& cmdId) {
  const int h = heard;
  if (h < 0) return false;
  heard = -1;
  cmdId = h;
  return true;
}

bool voiceSrWakeHeard() {
  const bool w = wake;
  wake = false;
  return w;
}

const char* voiceSrStatus() { return status; }

#else

bool voiceSrBegin() { return false; }
bool voiceSrReady() { return false; }
void voiceSrListen(bool) {}
bool voiceSrTake(int&) { return false; }
bool voiceSrWakeHeard() { return false; }
void voiceSrTick(uint32_t) {}
const char* voiceSrStatus() { return "off (not built: env lcd28_voice)"; }

#endif
