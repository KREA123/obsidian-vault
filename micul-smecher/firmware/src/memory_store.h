// SOUL Memory on the board (docs/10-SOUL-MEMORY.md): the `soulmem` flash partition (128 KB, two A/B
// slots, lib/Suflet/src/Memory.h MemoryFlash) under the SoulMemory the OS uses. Writes are batched
// (SoulMemory::saveDue: 4 s quiet, at most once every 20 s, at most 2 min dirty) and never while SOUL is
// listening, thinking or ringing; each write is followed by soulFlashWritten() (the RGB panel resyncs at
// the next VSYNC, as for every NVS write).
#pragma once
#include <stdint.h>

#include "Memory.h"

bool memoryStoreBegin(suflet::SoulMemory& m);  // false: no partition (an old table) or nothing stored yet
// call every loop; busy = do not touch the flash now
void memoryStoreTick(suflet::SoulMemory& m, uint32_t nowMs, bool busy);
bool memoryStoreSaveNow(suflet::SoulMemory& m);  // serial `Y save`, before a restart / deep sleep
bool memoryStoreReady();
uint32_t memoryStoreWrites();
