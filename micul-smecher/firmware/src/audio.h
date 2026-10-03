// Sound in and out for the boards that can: the optional I2S parts on the
// 2.8C (INMP441 mic, MAX98357A amp; build flags in board.h) and its
// buzzer. The AMOLED-1.75's ES8311/ES7210 codecs are not driven yet.
#pragma once
#include <stddef.h>
#include <stdint.h>

void audioInit();
// Call every loop. `alarmOn`: the alarm pattern wants sound right now.
void audioTick(bool alarmOn);
// Microphone loudness 0..1 (0 without a mic), for Brain Inputs.audioLevel.
float audioLevel();
bool audioHasMic();
bool audioHasSpeaker();  // an I2S amp; otherwise the alarm uses the buzzer (if any)

// SoulOS Music (os/APPS.md): focus sounds through the I2S amp while `g` is set (null = silence); an alarm wins
namespace suflet {
class SoundGen;
}
void audioSetFocus(suflet::SoundGen* g);

// Voice capture (INMP441 builds): 16 kHz mono 16-bit PCM into PSRAM, up to
// 8 s, while the glass is held. audioRecord(false) stops; audioTake() hands
// out the buffer until the next start.
void audioRecord(bool on);
bool audioRecording();
const int16_t* audioTake(size_t& samples);

// Offline voice commands (voice_sr.cpp, SUFLET_VOICE_SR builds): once ESP-SR runs, its feed task owns the
// mic: audioSrFill() hands it 16 kHz mono 16-bit samples (and keeps the level and the recording going);
// audioTick() stops reading the mic itself. Returns the samples written (0 = timeout / no mic).
void audioSetSrOwner(bool on);
size_t audioSrFill(int16_t* out, size_t samples, uint32_t timeoutMs);
