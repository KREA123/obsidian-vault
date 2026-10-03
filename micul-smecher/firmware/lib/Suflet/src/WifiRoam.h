// SOUL on the go (docs/09-EVERYWHERE.md): several saved Wi-Fi networks (home,
// work, the phone's hotspot...) with a priority, automatic roaming between
// them, a fast search when the phone's hotspot may have just appeared, and a
// check that the joined network really reaches the internet (a hotel's login
// page is told apart from "online" and from "no internet").
//
// Hardware-free and clock-free (the caller passes millis): src/net.cpp drives
// it with the ESP32 Wi-Fi driver, the tests drive it with scripted scans.
//
//   WifiBook    the saved networks (max kMax), a versioned binary blob for NVS
//   WifiRoamer  the state machine: tick() says what to do next (scan, join a
//               network, probe the internet, leave), the driver reports back
//               with scanDone() / joinFailed() / probed()
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace suflet {

enum class WifiKind : uint8_t { Home, Work, Hotspot, Other };
const char* wifiKindName(WifiKind k, bool ro);
uint8_t wifiDefaultPrio(WifiKind k);  // Home 8, Work 7, Other 5, Hotspot 3 (data on a phone costs; home first)

struct WifiNet {
  std::string ssid, pass;  // pass empty = an open network
  WifiKind kind = WifiKind::Other;
  uint8_t prio = 5;        // 1 (last resort) .. 9 (always first)
};

// iPhone hotspots are named after the phone with a typographic apostrophe
// ("Ana’s iPhone"), which nobody types on a round keyboard: a saved name
// matches a seen one exactly, or after folding ’ ‘ ʼ ` to ' , ASCII case and
// trailing spaces. 0 = no match, 1 = folded match, 2 = exact.
int ssidMatch(const std::string& saved, const std::string& seen);

class WifiBook {
 public:
  static constexpr int kMax = 8;
  int count() const { return (int)nets_.size(); }
  const WifiNet& at(int i) const { return nets_[(size_t)i]; }
  int find(const std::string& ssid) const;  // exact, -1 = none
  // Adds or updates (same SSID: an empty password keeps the old one). Returns
  // the index, -1 when the name or password is invalid (SSID 1..32 bytes,
  // WPA2 password empty or 8..63) or the book is full.
  int add(const WifiNet& n);
  bool remove(int i);
  bool setPrio(int i, uint8_t prio);
  void clear() { nets_.clear(); }
  int topPrio() const;
  // "WB" + version + count, then per network: kind, prio, ssid len + bytes, pass len + bytes
  std::string save() const;
  bool load(const std::string& blob);

 private:
  std::vector<WifiNet> nets_;
};

struct ScanHit {
  std::string ssid;
  int rssi = -100;
};

enum class NetState : uint8_t {
  NoNetworks,  // nothing saved
  Searching,   // scanning for a saved network
  Joining,     // associating + DHCP
  Checking,    // joined: is the internet really there?
  Online,
  Captive,     // a login page (hotel, train, café): SOUL cannot click through it
  NoInternet,  // joined, but nothing gets out (a phone hotspot without mobile data, a dead router)
};
const char* netStateName(NetState s);

enum class ProbeResult : uint8_t { Online, Captive, NoInternet };
// The connectivity check: GET http://connectivitycheck.gstatic.com/generate_204
// without following redirects. status -1 = no answer at all.
ProbeResult classifyProbe(int status, size_t bodyLen);

enum class JoinFail : uint8_t { None, NotFound, BadPassword, Timeout, Other };

struct RoamCmd {
  enum Kind : uint8_t { None, Scan, Join, Probe, Leave } kind = None;
  int net = -1;      // Join: the book index
  std::string ssid;  // Join: the SSID exactly as seen on the air (may differ from the saved one, see ssidMatch)
};

class WifiRoamer {
 public:
  // timings (ms) and thresholds
  static constexpr uint32_t kFastScanMs = 4000;      // just lost / just kicked: the hotspot is joined in seconds
  static constexpr uint32_t kFastWindowMs = 180000;  // ... for 3 minutes
  static constexpr uint32_t kSlowScanMs = 20000;     // then every 20 s up to 10 minutes
  static constexpr uint32_t kSlowWindowMs = 600000;
  static constexpr uint32_t kIdleScanMs = 60000;     // then once a minute (battery)
  static constexpr uint32_t kJoinTimeoutMs = 15000;
  static constexpr uint32_t kProbeTimeoutMs = 12000;
  static constexpr uint32_t kRecheckMs = 30000;      // captive / no internet: probe again, look for another network
  static constexpr uint32_t kRoamScanMs = 120000;    // online on a weak or second-choice network: look around
  static constexpr int kMinRssi = -86;               // below this a network is not tried
  static constexpr int kRoamRssi = -72;              // a better network must be at least this strong to move
  static constexpr int kWeakRssi = -80;              // the current network is weak below this

  void setBook(const WifiBook* b) { book_ = b; }
  // The book changed (added, removed, re-prioritised). `currentSsid`: the
  // network joined now ("" = none). Clears the back-offs and searches fast.
  void bookChanged(uint32_t now, const std::string& currentSsid);
  // At boot: try the network that worked last time straight away, before any
  // scan (a wake-poll from deep sleep has ~12 s; a scan costs ~1.5 s). If it is
  // not there the driver says so in ~2 s and the normal search follows.
  void preferFirst(int net);
  // Search fast again: a network was added, SOUL was picked up, a question waits.
  void kick(uint32_t now);
  // Call every loop. linkUp = associated with an IP; rssi of the current network.
  RoamCmd tick(uint32_t now, bool linkUp, int rssi);
  void scanDone(uint32_t now, const std::vector<ScanHit>& hits);
  void joinFailed(uint32_t now, JoinFail why);
  void probed(uint32_t now, ProbeResult r);

  NetState state() const;
  int current() const { return cur_; }        // the book index joined / being joined, -1 = none
  JoinFail lastFail() const { return fail_; }  // the last failure (for the screen), None once online
  int lastFailNet() const { return failNet_; }
  bool scanning() const { return scanning_; }
  bool fast(uint32_t now) const { return now - kickT_ < kFastWindowMs; }
  int scansDone() const { return scans_; }

 private:
  struct Back {
    uint32_t until = 0;
    uint8_t fails = 0;
  };
  uint32_t searchInterval(uint32_t now) const;
  int pick(uint32_t now, const std::vector<ScanHit>& hits, int exclude, int* rssiOut, std::string* seenOut) const;
  void backoff(uint32_t now, int i, uint32_t ms);
  void startSearch(uint32_t now);

  const WifiBook* book_ = nullptr;
  NetState st_ = NetState::Searching;
  int cur_ = -1, failNet_ = -1, pendNet_ = -1, scans_ = 0;
  std::string pendSsid_;
  JoinFail fail_ = JoinFail::None;
  bool scanning_ = false, started_ = false, leave_ = false, probeOut_ = false;
  uint32_t kickT_ = 0, nextScan_ = 0, joinT_ = 0, probeT_ = 0, nextProbe_ = 0, scanT_ = 0;
  Back back_[WifiBook::kMax];
};

// The offline question queue: what was asked with no internet, sent when SOUL
// is back online. Capped (kMax, the oldest goes), de-duplicated, and stale
// questions (older than kMaxAgeS) are dropped instead of answered late.
class AskQueue {
 public:
  static constexpr int kMax = 5;
  static constexpr float kMaxAgeS = 6 * 3600.0f;
  struct Item {
    std::string text;
    float t = 0;    // the caller's monotonic seconds
    int tries = 0;  // sent before and lost on the way
  };
  bool push(const std::string& text, float now, int tries = 0);  // false = a duplicate (still queued once)
  bool pop(float now, Item& out);                 // the oldest fresh one
  int size() const { return (int)q_.size(); }
  void clear() { q_.clear(); }
  int dropped() const { return dropped_; }

 private:
  std::vector<Item> q_;
  int dropped_ = 0;
};

}  // namespace suflet
