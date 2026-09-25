// Alarms (SoulOS "Time & Alarms" service, v1): hour, minute, weekday mask,
// label, enabled and snooze; when each one rings next, computed from local
// time (the RTC keeps local time, research/03 §5); and a compact versioned
// binary form for NVS (Preferences key "alarms"). Pure logic, no clock of
// its own: the caller passes the local epoch (seconds, as if TZ were UTC).
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace suflet {

namespace days {
enum : uint8_t {
  Mon = 1 << 0,
  Tue = 1 << 1,
  Wed = 1 << 2,
  Thu = 1 << 3,
  Fri = 1 << 4,
  Sat = 1 << 5,
  Sun = 1 << 6,
  Weekdays = 0x1F,
  Weekend = 0x60,
  Every = 0x7F,
  Once = 0,  // no weekday: rings once, then switches itself off
};
}

struct Alarm {
  uint8_t hour = 7, minute = 0;
  uint8_t days = days::Once;  // bit 0 = Monday ... bit 6 = Sunday
  bool enabled = true;
  uint8_t snoozeMin = 5;
  uint32_t snoozeUntil = 0;  // local epoch; 0 = not snoozed
  uint32_t lastFired = 0;    // scheduled time of the last ring (never rings twice)
  char label[49] = {0};      // UTF-8, at most 48 bytes, cut on a code point

  void setLabel(const char* s);
};

namespace localclock {
inline uint32_t dayStart(uint32_t t) { return t - t % 86400u; }
// 0 = Monday ... 6 = Sunday (1970-01-01 was a Thursday)
inline int weekday(uint32_t t) { return (int)((t / 86400u + 3u) % 7u); }
inline int hour(uint32_t t) { return (int)(t % 86400u / 3600u); }
inline int minute(uint32_t t) { return (int)(t % 3600u / 60u); }
}  // namespace localclock

class Alarms {
 public:
  static constexpr int kMax = 16;
  static constexpr size_t kRecord = 14;  // fixed part of one serialised alarm
  static constexpr size_t kMaxBlob = 4 + kMax * (kRecord + 48);

  int count() const { return n_; }
  Alarm& at(int i) { return a_[i]; }
  const Alarm& at(int i) const { return a_[i]; }
  // Adds an alarm set at local time `now` (so a time that already passed
  // today does not ring right away). Returns its index, -1 when full.
  int add(const Alarm& a, uint32_t now);
  bool remove(int i);
  void clear() { n_ = 0; }

  // Next ring strictly after `now` (the snooze counts), 0 = never.
  static uint32_t nextFire(const Alarm& a, uint32_t now);
  // The soonest alarm: its index (-1 = none) and time.
  int next(uint32_t now, uint32_t& when) const;
  // Call often (every loop is fine). Returns the index of an alarm that
  // rings now, -1 otherwise. An alarm rings once per scheduled minute, up to
  // `graceS` late (the loop or a light sleep can be slow); a one-shot alarm
  // switches itself off when it rings.
  int poll(uint32_t now, uint32_t graceS = 90);
  void snooze(int i, uint32_t now);  // ring again in snoozeMin minutes
  void dismiss(int i);               // stop ringing, cancel the snooze

  // Versioned little-endian blob: "SA", version, count, then per alarm
  // hour, minute, days, flags, snoozeMin, snoozeUntil u32, lastFired u32,
  // label length u8, label bytes. Returns the size written, 0 if cap is too
  // small. deserialize() leaves the list untouched on any error.
  size_t serialize(uint8_t* buf, size_t cap) const;
  bool deserialize(const uint8_t* buf, size_t n);

 private:
  Alarm a_[kMax];
  int n_ = 0;
};

}  // namespace suflet
