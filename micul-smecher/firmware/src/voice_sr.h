// Offline voice commands on the board (docs/10-SOUL-MEMORY.md §7): Espressif ESP-SR (esp-sr 2.5.x, shipped
// precompiled in Arduino-ESP32 3.3) with MultiNet7 English (quantised) and, optionally, the WakeNet9
// "Hi ESP" wake word, fed by the INMP441 on I2S. Built only with -DSUFLET_VOICE_SR=1 (env `lcd28_voice`) and
// the speech models flashed to the `model` partition (srmodels.bin at 0xcb0000, see release/README.md).
//
// Push-to-talk by default: the recogniser sleeps (sr_pause: no CPU) until the glass is held, listens while it
// is held and ~1 s after, and SoulOS runs the command (Os::voiceCommand) with no internet. With
// -DSUFLET_VOICE_WAKE=1 it also listens for the wake word all the time (~20 % of one core).
// Fallback: no model in flash, or less free PSRAM than kVoiceSrPsramNeed -> voiceSrReady() is false and voice
// stays what it was (the cloud transcription when online, the round keyboard otherwise).
#pragma once
#include <stdint.h>

bool voiceSrBegin();            // after audioInit(); false = the fallback (see voiceSrStatus())
bool voiceSrReady();
void voiceSrListen(bool on);    // the glass is held / let go
bool voiceSrTake(int& cmdId);   // a command heard (MultiNet id = (int)suflet::VoiceCmd)
bool voiceSrWakeHeard();        // the wake word (SUFLET_VOICE_WAKE builds)
void voiceSrTick(uint32_t nowMs);
const char* voiceSrStatus();    // "on", "off (not built)", "off (no model)", "off (PSRAM)", "off (start failed)"
