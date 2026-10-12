#include "PsramAlloc.h"

#if defined(ESP_PLATFORM)
#include <esp_heap_caps.h>
#endif

namespace suflet {

namespace {
PsramStats gStats;
}

const PsramStats& psramStats() { return gStats; }

void* psramAlloc(size_t bytes) {
  if (!bytes) bytes = 1;
#if defined(ESP_PLATFORM)
  void* p = heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!p) {
    p = malloc(bytes);
    if (p) ++gStats.fallbacks;
  }
#else
  void* p = malloc(bytes);
#endif
  if (p) {
    ++gStats.allocs;
    gStats.bytes += bytes;
  }
  return p;
}

void* psramRealloc(void* old, size_t bytes) {
  if (!old) return psramAlloc(bytes);
  if (!bytes) bytes = 1;
#if defined(ESP_PLATFORM)
  void* p = heap_caps_realloc(old, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!p) {
    p = realloc(old, bytes);
    if (p) ++gStats.fallbacks;
  }
#else
  void* p = realloc(old, bytes);
#endif
  if (p) {
    ++gStats.allocs;
    gStats.bytes += bytes;
  }
  return p;
}

void psramFree(void* p) {
  free(p);  // heap_caps memory is freed by free() on ESP-IDF
}

}  // namespace suflet
