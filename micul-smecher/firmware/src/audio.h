// Sound in and out for the boards that can: the optional I2S parts on the
// 2.8C (INMP441 mic, MAX98357A amp; build flags in board.h) and its
// buzzer. The AMOLED-1.75's ES8311/ES7210 codecs are not driven yet.
#pragma once
#include <stdint.h>

void audioInit();
// Call every loop. `alarmOn`: the alarm pattern wants sound right now.
void audioTick(bool alarmOn);
// Microphone loudness 0..1 (0 without a mic), for Brain Inputs.audioLevel.
float audioLevel();
bool audioHasMic();
bool audioHasSpeaker();  // an I2S amp; otherwise the alarm uses the buzzer (if any)
