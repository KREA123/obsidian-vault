#include "audio.h"

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <math.h>

#include "AlarmTone.h"
#include "SoundGen.h"
#include "board.h"
#if defined(SUFLET_BOARD_LCD28)
#include "board_lcd28.h"
#endif

#if SUFLET_MIC_INMP441 || SUFLET_SPK_MAX98357 || SUFLET_SPK_ES8311
#include <ESP_I2S.h>
static I2SClass i2s;
static bool i2sOk = false;
static constexpr uint32_t kRate = 16000;
#endif
#if SUFLET_SPK_ES8311
#include <Wire.h>
static bool codecOk = false;
#endif

static float level = 0;
static int16_t* rec = nullptr;
static size_t recN = 0;
static bool recOn = false;
static constexpr size_t kRecMax = 16000 * 8;
static volatile bool srOwns = false;  // ESP-SR's feed task reads the mic (voice_sr.cpp)

void audioSetSrOwner(bool on) { srOwns = on; }

// SoulOS Music: focus sounds made on SOUL (SoundGen.h), when nothing rings
static suflet::SoundGen* focusGen = nullptr;
void audioSetFocus(suflet::SoundGen* g) { focusGen = g; }

// serial `A` (BRINGUP §S): a 1 kHz tone at -12 dBFS for `ms`
static uint32_t testUntilMs = 0;
void audioTestTone(uint32_t ms) { testUntilMs = millis() + ms; }

#if SUFLET_MIC_INMP441
// one block of 32-bit I2S samples -> the recording and the loudness level
static void takeSamples(const int32_t* buf, size_t n) {
  if (recOn)
    for (size_t i = 0; i < n && recN < kRecMax; ++i) rec[recN++] = (int16_t)(buf[i] >> 16);
  if (!n) return;
  double acc = 0;
  for (size_t i = 0; i < n; ++i) {
    const double s = (buf[i] >> 8) / 8388608.0;  // 24-bit sample -> -1..1
    acc += s * s;
  }
  const float rms = sqrtf((float)(acc / n)) + 1e-9f;
  const float db = 20.0f * log10f(rms);                              // dBFS
  const float target = constrain((db + 60.0f) / 40.0f, 0.0f, 1.0f);  // -60..-20 dBFS -> 0..1
  level += (target - level) * (target > level ? 0.5f : 0.1f);        // fast attack, slow release
}
#endif

void audioRecord(bool on) {
#if SUFLET_MIC_INMP441
  if (on) {
    if (!rec) rec = (int16_t*)heap_caps_malloc(kRecMax * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    recN = 0;
    recOn = rec != nullptr;
  } else {
    recOn = false;
  }
#else
  (void)on;
#endif
}
bool audioRecording() { return recOn; }
const int16_t* audioTake(size_t& samples) {
  samples = recOn ? 0 : recN;
  return rec;
}
static constexpr float AlarmToneHz = suflet::AlarmTone::kToneHz;

#if SUFLET_SPK_ES8311
// ---- SOUL S: the ES8311 DAC + the speaker amplifier (Waveshare AMOLED-1.75) -------------------------------------
// I2C 0x18; I2S standard (Philips) mode, the S3 the master: MCLK 42 (256 x fs = 4.096 MHz at 16 kHz), BCLK 9,
// WS 45, DOUT 8; the amplifier's enable on GPIO 46 (PA_CTRL in the Waveshare schematic; xiaozhi's config.h has
// the same pins). The register sequence is Espressif's esp_codec_dev es8311.c (Apache-2.0): es8311_open (slave,
// MCLK from the pin), es8311_config_sample for 4.096 MHz / 16 kHz, 16-bit I2S, es8311_start for the DAC only.
// NOT YET RUN ON THE BOARD (BRINGUP §S: serial `A` plays the test tone). Until it is heard, audioHasSpeaker()
// only says the codec answered on I2C.
static bool esW(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(AUDIO_CODEC_ES8311_ADDR);
  Wire.write(reg);
  Wire.write(v);
  return Wire.endTransmission() == 0;
}
static int esR(uint8_t reg) {
  Wire.beginTransmission(AUDIO_CODEC_ES8311_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom((int)AUDIO_CODEC_ES8311_ADDR, 1) != 1) return -1;
  return Wire.read();
}
static bool es8311Init() {
  const int id1 = esR(0xFD), id2 = esR(0xFE);  // chip id: 0x83 0x11
  if (id1 < 0) return false;
  bool ok = true;
  // es8311_open: clocks on, defaults, then the codec as I2S slave with MCLK from its pin
  ok &= esW(0x45, 0x00);
  ok &= esW(0x01, 0x30);
  ok &= esW(0x02, 0x00);
  ok &= esW(0x03, 0x10);
  ok &= esW(0x16, 0x24);
  ok &= esW(0x04, 0x10);
  ok &= esW(0x05, 0x00);
  ok &= esW(0x0B, 0x00);
  ok &= esW(0x0C, 0x00);
  ok &= esW(0x10, 0x1F);
  ok &= esW(0x11, 0x7F);
  ok &= esW(0x00, 0x80);  // power on, slave (bit 6 = 0)
  ok &= esW(0x01, 0x3F);  // every clock on, MCLK from the MCLK pin (bit 7 = 0), not inverted
  int r = esR(0x06);
  ok &= r >= 0 && esW(0x06, (uint8_t)(r & ~0x20));  // SCLK not inverted
  ok &= esW(0x13, 0x10);
  ok &= esW(0x1B, 0x0A);
  ok &= esW(0x1C, 0x6A);
  ok &= esW(0x44, 0x08);  // no DAC loop-back into the ADC (no echo reference: the mics are not used yet)
  // es8311_config_sample: MCLK 4.096 MHz, 16 kHz: pre-div 1, pre-multi x1, ADC/DAC div 1, LRCK 256, BCLK div 4, OSR 16
  r = esR(0x02);
  ok &= r >= 0 && esW(0x02, (uint8_t)(r & 0x07));
  ok &= esW(0x05, 0x00);
  r = esR(0x03);
  ok &= r >= 0 && esW(0x03, (uint8_t)((r & 0x80) | 0x10));
  r = esR(0x04);
  ok &= r >= 0 && esW(0x04, (uint8_t)((r & 0x80) | 0x10));
  r = esR(0x07);
  ok &= r >= 0 && esW(0x07, (uint8_t)(r & 0xC0));
  ok &= esW(0x08, 0xFF);
  r = esR(0x06);
  ok &= r >= 0 && esW(0x06, (uint8_t)((r & 0xE0) | (4 - 1)));
  // 16-bit, I2S (Philips) on the DAC's serial port (0x09) and the ADC's (0x0A, muted below)
  r = esR(0x09);
  ok &= r >= 0 && esW(0x09, (uint8_t)((r & ~0x1C & 0xFC) | 0x0C));
  r = esR(0x0A);
  ok &= r >= 0 && esW(0x0A, (uint8_t)((r & ~0x1C & 0xFC) | 0x0C));
  // es8311_start, DAC only: the DAC's port on (0x09 bit 6 = 0), the ADC's off; analog and DAC powered up
  r = esR(0x09);
  ok &= r >= 0 && esW(0x09, (uint8_t)(r & 0xBF));
  r = esR(0x0A);
  ok &= r >= 0 && esW(0x0A, (uint8_t)(r | 0x40));
  ok &= esW(0x17, 0xBF);
  ok &= esW(0x0E, 0x02);
  ok &= esW(0x12, 0x00);
  ok &= esW(0x14, 0x1A);
  ok &= esW(0x0D, 0x01);
  ok &= esW(0x15, 0x40);
  ok &= esW(0x37, 0x08);
  ok &= esW(0x45, 0x00);
  // the DAC at 0 dB (0xBF; 0.5 dB a step), not muted
  ok &= esW(0x32, 0xBF);
  r = esR(0x31);
  ok &= r >= 0 && esW(0x31, (uint8_t)(r & ~0x60));
  Serial.printf("[audio] ES8311 id %02X %02X: %s\n", id1 & 0xFF, id2 & 0xFF, ok ? "set up" : "a register write FAILED");
  return ok;
}
// the speaker amplifier: on while there is sound, off half a second after (no hiss, ~mA saved [estimare])
static uint32_t paOnUntilMs = 0;
static void paWant(bool sound) {
  static bool on = false;
  const uint32_t now = millis();
  if (sound) paOnUntilMs = now + 500;
  const bool want = sound || (int32_t)(paOnUntilMs - now) > 0;
  if (want != on) {
    on = want;
    digitalWrite(AUDIO_PA_PIN, on ? HIGH : LOW);
  }
}
#endif

// one block of mono 16-bit PCM to the speaker's I2S, never blocking; false = the DMA is full
[[maybe_unused]] static bool spkWrite(const int16_t* pcm, int n) {
#if SUFLET_SPK_ES8311
  return i2s.write((const uint8_t*)pcm, (size_t)n * 2) == (size_t)n * 2;  // 16-bit slots: as is
#elif SUFLET_SPK_MAX98357
  int32_t buf[128];
  for (int i = 0; i < n && i < 128; ++i) buf[i] = (int32_t)pcm[i] << 16;  // 32-bit slots
  return i2s.write((const uint8_t*)buf, (size_t)n * 4) == (size_t)n * 4;
#else
  (void)pcm;
  (void)n;
  return false;
#endif
}

void audioInit() {
#if SUFLET_SPK_ES8311
  pinMode(AUDIO_PA_PIN, OUTPUT);
  digitalWrite(AUDIO_PA_PIN, LOW);
  // MCLK must run before the codec is set up: the I2S first, then the registers
  i2s.setPins(AUDIO_I2S_BCLK, AUDIO_I2S_WS, AUDIO_I2S_DOUT, -1, AUDIO_I2S_MCLK);
  i2s.setTimeout(0);
  i2sOk = i2s.begin(I2S_MODE_STD, kRate, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  codecOk = i2sOk && es8311Init();
  Serial.printf("[audio] I2S %s, ES8311 %s: the speaker %s\n", i2sOk ? "ok" : "FAILED", codecOk ? "ok" : "NOT FOUND",
                codecOk ? "is driven (check it is heard: `A`)" : "is silent, alarms are silent");
  return;
#endif
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

size_t audioSrFill(int16_t* out, size_t samples, uint32_t timeoutMs) {
#if SUFLET_MIC_INMP441
  if (!i2sOk) return 0;
  int32_t buf[256];
  size_t done = 0;
  const uint32_t t0 = millis();
  while (done < samples) {
    const size_t want = samples - done < 256 ? samples - done : 256;
    const size_t n = i2s.readBytes((char*)buf, want * sizeof(int32_t)) / sizeof(int32_t);
    if (!n) {
      if (millis() - t0 > (timeoutMs < 200 ? timeoutMs : 200)) break;
      delay(2);
      continue;
    }
    takeSamples(buf, n);
    for (size_t i = 0; i < n; ++i) out[done + i] = (int16_t)(buf[i] >> 14 > 32767 ? 32767 : buf[i] >> 14 < -32768 ? -32768 : buf[i] >> 14);
    done += n;
  }
  return done;
#else
  (void)out;
  (void)samples;
  (void)timeoutMs;
  return 0;
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
#if SUFLET_SPK_ES8311
  return codecOk;
#elif SUFLET_SPK_MAX98357
  return i2sOk;
#else
  return false;
#endif
}

float audioLevel() { return level; }

void audioTick(bool alarmOn) {
#if SUFLET_MIC_INMP441
  if (i2sOk && !srOwns) {
    int32_t buf[256];
    for (int chunk = 0; chunk < 12; ++chunk) {  // drain the DMA: ~1 frame of audio per call
      const size_t n = i2s.readBytes((char*)buf, sizeof buf) / sizeof(int32_t);
      if (!n) break;
      takeSamples(buf, n);
    }
  }
#endif

  bool speakerUsed = false;
  const bool test = (int32_t)(testUntilMs - millis()) > 0;
#if SUFLET_SPK_MAX98357 || SUFLET_SPK_ES8311
#if SUFLET_SPK_ES8311
  const bool spkOk = codecOk;
#else
  const bool spkOk = i2sOk;
#endif
  if (spkOk) {
    speakerUsed = true;
    if (alarmOn || test) {
      // Keep the DMA topped up with a 2 kHz tone at -12 dBFS (up to 64 ms per call, never blocking). When the
      // pattern turns the sound off we stop writing; the driver clears the buffers it has played (silence).
      static float phase = 0;
      int16_t buf[128];
      const float step = 2.0f * (float)M_PI * (test ? 1000.0f : AlarmToneHz) / kRate;
      for (int chunk = 0; chunk < 8; ++chunk) {
        for (int i = 0; i < 128; ++i) {
          buf[i] = (int16_t)(sinf(phase) * 0.25f * 32767.0f);
          phase += step;
          if (phase > 2.0f * (float)M_PI) phase -= 2.0f * (float)M_PI;
        }
        if (!spkWrite(buf, 128)) break;  // DMA full
      }
    } else if (focusGen) {
      // focus sounds: keep ~64 ms queued, never blocking (the generator is a few multiplies a sample)
      static int16_t pcm[128];
      for (int chunk = 0; chunk < 8; ++chunk) {
        focusGen->fill(pcm, 128, kRate);
        if (!spkWrite(pcm, 128)) break;  // DMA full
      }
    }
#if SUFLET_SPK_ES8311
    paWant(alarmOn || test || focusGen != nullptr);
#endif
  }
#endif

#if HAS_BUZZER
  lcd28::buzzer((alarmOn || test) && !speakerUsed);
#else
  (void)speakerUsed;
  (void)test;
#endif
}
