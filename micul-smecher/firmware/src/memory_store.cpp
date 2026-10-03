#include "memory_store.h"

#include <Arduino.h>
#include <esp_partition.h>

#include "board.h"

using namespace suflet;

namespace {

struct PartitionIo : FlashIo {
  const esp_partition_t* p = nullptr;
  size_t size() const override { return p ? p->size : 0; }
  bool read(size_t off, void* dst, size_t n) override { return p && esp_partition_read(p, off, dst, n) == ESP_OK; }
  bool erase(size_t off, size_t n) override { return p && esp_partition_erase_range(p, off, n) == ESP_OK; }
  bool write(size_t off, const void* src, size_t n) override { return p && esp_partition_write(p, off, src, n) == ESP_OK; }
};

PartitionIo io;
MemoryFlash flash(&io);
bool ready = false;

}  // namespace

bool memoryStoreBegin(SoulMemory& m) {
  io.p = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "soulmem");
  ready = io.p != nullptr;
  if (!ready) {
    Serial.println("[memory] no `soulmem` partition (flash the 1.6 image with its partition table): RAM only");
    return false;
  }
  const bool ok = flash.load(m);
  Serial.printf("[memory] %u facts (%s), slot %d seq %lu, %u KB partition\n", (unsigned)m.size(),
                ok ? "loaded" : "none stored yet", flash.slot(), (unsigned long)flash.seq(), (unsigned)(io.p->size / 1024));
  return ok;
}

bool memoryStoreSaveNow(SoulMemory& m) {
  if (!ready) return false;
  const uint32_t t0 = millis();
  const bool ok = flash.save(m);
  soulFlashWritten();
  if (ok) m.markSaved(millis());
  Serial.printf("[memory] saved %u facts in %lu ms (%s, slot %d)\n", (unsigned)m.size(), (unsigned long)(millis() - t0),
                ok ? "ok" : "FAILED", flash.slot());
  return ok;
}

void memoryStoreTick(SoulMemory& m, uint32_t nowMs, bool busy) {
  m.setClockMs(nowMs);
  if (!ready || busy || !m.saveDue(nowMs)) return;
  if (!memoryStoreSaveNow(m)) m.savePostponed(nowMs);  // a failing flash: try again later, not every frame
}

bool memoryStoreReady() { return ready; }
uint32_t memoryStoreWrites() { return flash.writes; }
