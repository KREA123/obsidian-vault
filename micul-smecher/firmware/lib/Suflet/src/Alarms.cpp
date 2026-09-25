#include "Alarms.h"

#include <string.h>

#include "Font.h"

namespace suflet {

void Alarm::setLabel(const char* s) {
  size_t n = s ? strlen(s) : 0;
  if (n > sizeof(label) - 1) n = utf8::prevStart(s, sizeof(label));  // don't split a code point
  if (n > sizeof(label) - 1) n = sizeof(label) - 1;
  if (n) memcpy(label, s, n);
  label[n] = 0;
}

namespace {
bool onDay(const Alarm& a, uint32_t t) { return a.days == days::Once || (a.days >> localclock::weekday(t)) & 1; }
uint32_t hm(const Alarm& a) { return a.hour * 3600u + a.minute * 60u; }
}  // namespace

int Alarms::add(const Alarm& a, uint32_t now) {
  if (n_ >= kMax) return -1;
  a_[n_] = a;
  a_[n_].lastFired = now;
  return n_++;
}

bool Alarms::remove(int i) {
  if (i < 0 || i >= n_) return false;
  for (int k = i + 1; k < n_; ++k) a_[k - 1] = a_[k];
  --n_;
  return true;
}

uint32_t Alarms::nextFire(const Alarm& a, uint32_t now) {
  uint32_t best = 0;
  if (a.enabled) {
    const uint32_t d0 = localclock::dayStart(now);
    for (uint32_t d = 0; d <= 7; ++d) {  // today .. the same weekday next week
      const uint32_t t = d0 + d * 86400u + hm(a);
      if (t <= now || !onDay(a, t)) continue;
      best = t;
      break;
    }
  }
  if (a.snoozeUntil > now && (!best || a.snoozeUntil < best)) best = a.snoozeUntil;
  return best;
}

int Alarms::next(uint32_t now, uint32_t& when) const {
  int idx = -1;
  when = 0;
  for (int i = 0; i < n_; ++i) {
    const uint32_t t = nextFire(a_[i], now);
    if (t && (!when || t < when)) {
      when = t;
      idx = i;
    }
  }
  return idx;
}

int Alarms::poll(uint32_t now, uint32_t graceS) {
  for (int i = 0; i < n_; ++i) {
    Alarm& a = a_[i];
    if (a.snoozeUntil && now >= a.snoozeUntil) {
      a.snoozeUntil = 0;
      return i;
    }
    if (!a.enabled) continue;
    // the latest scheduled time at or before now
    const uint32_t d0 = localclock::dayStart(now);
    uint32_t prev = 0;
    for (uint32_t d = 0; d <= 7 && d0 >= d * 86400u; ++d) {
      const uint32_t t = d0 - d * 86400u + hm(a);
      if (t > now || !onDay(a, t)) continue;
      prev = t;
      break;
    }
    if (prev && prev > a.lastFired && now - prev <= graceS) {
      a.lastFired = prev;
      if (a.days == days::Once) a.enabled = false;
      return i;
    }
  }
  return -1;
}

void Alarms::snooze(int i, uint32_t now) {
  if (i < 0 || i >= n_) return;
  a_[i].snoozeUntil = now + (a_[i].snoozeMin ? a_[i].snoozeMin : 5) * 60u;
}

void Alarms::dismiss(int i) {
  if (i < 0 || i >= n_) return;
  a_[i].snoozeUntil = 0;
  if (a_[i].days == days::Once) a_[i].enabled = false;
}

// -------------------------------------------------------------- storage ---

namespace {
void put32(uint8_t* p, uint32_t v) {
  p[0] = (uint8_t)v;
  p[1] = (uint8_t)(v >> 8);
  p[2] = (uint8_t)(v >> 16);
  p[3] = (uint8_t)(v >> 24);
}
uint32_t get32(const uint8_t* p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
constexpr uint8_t kVersion = 1;
}  // namespace

size_t Alarms::serialize(uint8_t* buf, size_t cap) const {
  size_t need = 4;
  for (int i = 0; i < n_; ++i) need += kRecord + strlen(a_[i].label);
  if (!buf || cap < need) return 0;
  uint8_t* p = buf;
  *p++ = 'S';
  *p++ = 'A';
  *p++ = kVersion;
  *p++ = (uint8_t)n_;
  for (int i = 0; i < n_; ++i) {
    const Alarm& a = a_[i];
    const size_t ln = strlen(a.label);
    *p++ = a.hour;
    *p++ = a.minute;
    *p++ = a.days;
    *p++ = a.enabled ? 1 : 0;
    *p++ = a.snoozeMin;
    put32(p, a.snoozeUntil);
    p += 4;
    put32(p, a.lastFired);
    p += 4;
    *p++ = (uint8_t)ln;
    memcpy(p, a.label, ln);
    p += ln;
  }
  return (size_t)(p - buf);
}

bool Alarms::deserialize(const uint8_t* buf, size_t n) {
  if (!buf || n < 4 || buf[0] != 'S' || buf[1] != 'A' || buf[2] != kVersion || buf[3] > kMax) return false;
  Alarm tmp[kMax];
  const int cnt = buf[3];
  size_t o = 4;
  for (int i = 0; i < cnt; ++i) {
    if (o + kRecord > n) return false;
    const uint8_t* p = buf + o;
    Alarm& a = tmp[i];
    a.hour = p[0];
    a.minute = p[1];
    a.days = p[2];
    a.enabled = p[3] & 1;
    a.snoozeMin = p[4];
    a.snoozeUntil = get32(p + 5);
    a.lastFired = get32(p + 9);
    const uint8_t ln = p[13];
    if (a.hour > 23 || a.minute > 59 || a.days > days::Every || (p[3] & ~1u) || ln > 48 ||
        o + kRecord + ln > n)
      return false;
    memcpy(a.label, p + 14, ln);
    a.label[ln] = 0;
    o += kRecord + ln;
  }
  if (o != n) return false;
  for (int i = 0; i < cnt; ++i) a_[i] = tmp[i];
  n_ = cnt;
  return true;
}

}  // namespace suflet
