// Scratch buffers that must not live in the ESP32-S3's internal RAM (1.9, firmware/PERF.md "Memory").
//
// pioarduino's sdkconfig puts every malloc() of <= 4096 B in internal RAM (CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL
// = 4096, RESERVE_INTERNAL = 0): small UI buffers made there compete with Wi-Fi, BLE, TLS and the task stacks,
// and churn fragments that heap. psramAlloc() asks for PSRAM explicitly (heap_caps_malloc(MALLOC_CAP_SPIRAM)),
// falling back to the normal heap when PSRAM is full or absent; on the PC it is malloc(). PsramAllocator<T>
// is the same for std::vector. The counters are for the tests and the serial `[perf]` line.
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

namespace suflet {

void* psramAlloc(size_t bytes);
void* psramRealloc(void* p, size_t bytes);
void psramFree(void* p);

struct PsramStats {
  uint32_t allocs = 0;      // psramAlloc / psramRealloc calls that returned memory
  uint32_t fallbacks = 0;   // ... of them served by the internal heap (PSRAM full / absent; never on the PC)
  uint64_t bytes = 0;       // bytes asked for, in all
};
const PsramStats& psramStats();

template <class T>
struct PsramAllocator {
  using value_type = T;
  PsramAllocator() = default;
  template <class U>
  PsramAllocator(const PsramAllocator<U>&) {}
  T* allocate(size_t n) {
    void* p = psramAlloc(n * sizeof(T));
    if (!p) abort();  // as std::allocator does under -fno-exceptions
    return static_cast<T*>(p);
  }
  void deallocate(T* p, size_t) { psramFree(p); }
  template <class U>
  bool operator==(const PsramAllocator<U>&) const { return true; }
  template <class U>
  bool operator!=(const PsramAllocator<U>&) const { return false; }
};

}  // namespace suflet
