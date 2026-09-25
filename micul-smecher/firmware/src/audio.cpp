#include "audio.h"

#include <Arduino.h>
#include <math.h>

#include "AlarmTone.h"
#include "board.h"
#if defined(SUFLET_BOARD_LCD28)
#include "board_lcd28.h"
#endif

#if SUFLET_MIC_INMP441 || SUFLET_SPK_MAX98357
#include <ESP_I2S.h>
static I2SClass i2s;
static bool i2sOk = false;
static constexpr uint32_t kRate = 16000;
#endif

static float level = 0;
static constexpr float AlarmToneHz = suflet::AlarmTone::kToneHz;

void audioInit() {
#if SUFLET_MIC_INMP441 || SUFLET_SPK_MAX98357
  // One standard-mode I2S port, 32-bit slots (INMP441 sends 24 bits
  // left-justified in 32; the MAX98357A takes 16..32 bit). Mono = left slot:
  // tie the INMP441 L/R pin to GND. BCLK/WS are shared when both are fitted.
  const int8_t dout = SUFLET_SPK_MAX98357 ? AUDIO_SPK_DOUT : -1;
  const int8_t din = SUFLET_MIC_INMP441 ? AUDIO_MIC_DIN : -1;
  i2s.setPins(AUDIO_I2S_BCLK, AUDIO_I2S_WS, dout, din);
  i2s.setTimeout(0);  // never block the frame loop
  i2sOk = i2s.begin(I2S_MODE_STD, kRate, I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO);
  Serial.printf("[audio] I2S %s (mic %s, speaker %s)\n", i2sOk ? "ok" : "FAILED",
                SUFLET_MIC_INMP441 ? "on" : "off", SUFLET_SPK_MAX98357 ? "on" : "off");
#endif
}

bool audioHasMic() {
#if SUFLET_MIC_INMP441
  return i2sOk;
#else
  return false;
#endif
}

bool audioHasSpeaker() {
#if SUFLET_SPK_MAX98357
  return i2sOk;
#else
  return false;
#endif
}

float audioLevel() { return level; }

void audioTick(bool alarmOn) {
#if SUFLET_MIC_INMP441
  if (i2sOk) {
    int32_t buf[256];
    const size_t n = i2s.readBytes((char*)buf, sizeof buf) / sizeof(int32_t);
    if (n) {
      double acc = 0;
      for (size_t i = 0; i < n; ++i) {
        const double s = (buf[i] >> 8) / 8388608.0;  // 24-bit sample -> -1..1
        acc += s * s;
      }
      const float rms = sqrtf((float)(acc / n)) + 1e-9f;
      const float db = 20.0f * log10f(rms);                      // dBFS
      const float target = constrain((db + 60.0f) / 40.0f, 0.0f, 1.0f);  // -60..-20 dBFS -> 0..1
      level += (target - level) * (target > level ? 0.5f : 0.1f);        // fast attack, slow release
    }
  }
#endif

  bool speakerUsed = false;
#if SUFLET_SPK_MAX98357
  if (i2sOk) {
    speakerUsed = true;
    if (alarmOn) {
      // Keep the DMA topped up with a 2 kHz tone at -12 dBFS (up to 64 ms
      // per call, never blocking). When the pattern turns the sound off we
      // stop writing; the driver clears the buffers it has played (silence).
      static float phase = 0;
      int32_t buf[128];
      const float step = 2.0f * (float)M_PI * AlarmToneHz / kRate;
      for (int chunk = 0; chunk < 8; ++chunk) {
        for (int i = 0; i < 128; ++i) {
          buf[i] = (int32_t)(sinf(phase) * 0.25f * 2147483647.0f);
          phase += step;
          if (phase > 2.0f * (float)M_PI) phase -= 2.0f * (float)M_PI;
        }
        if (i2s.write((const uint8_t*)buf, sizeof buf) < sizeof buf) break;  // DMA full
      }
    }
  }
#endif

#if HAS_BUZZER
  lcd28::buzzer(alarmOn && !speakerUsed);
#else
  (void)speakerUsed;
#endif
}
