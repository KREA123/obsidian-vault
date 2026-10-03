#include "WifiRoam.h"

namespace suflet {

const char* wifiKindName(WifiKind k, bool ro) {
  switch (k) {
    case WifiKind::Home: return ro ? "Acasă" : "Home";
    case WifiKind::Work: return ro ? "Birou" : "Work";
    case WifiKind::Hotspot: return ro ? "Hotspot telefon" : "Phone hotspot";
    default: return ro ? "Altă rețea" : "Other";
  }
}

uint8_t wifiDefaultPrio(WifiKind k) {
  switch (k) {
    case WifiKind::Home: return 8;
    case WifiKind::Work: return 7;
    case WifiKind::Hotspot: return 3;
    default: return 5;
  }
}

const char* netStateName(NetState s) {
  static const char* const k[] = {"no-networks", "searching", "joining", "checking", "online", "captive", "no-internet"};
  return (unsigned)s < sizeof(k) / sizeof(k[0]) ? k[(int)s] : "?";
}

// ------------------------------------------------------------ SSID match ---

static std::string fold(const std::string& s) {
  std::string o;
  o.reserve(s.size());
  for (size_t i = 0; i < s.size(); ++i) {
    const unsigned char c = (unsigned char)s[i];
    // U+2018 / U+2019 (E2 80 98 / 99), U+02BC (CA BC), U+00B4 (C2 B4), ` -> '
    if (c == 0xE2 && i + 2 < s.size() && (unsigned char)s[i + 1] == 0x80 &&
        ((unsigned char)s[i + 2] == 0x98 || (unsigned char)s[i + 2] == 0x99)) {
      o += '\'';
      i += 2;
    } else if ((c == 0xCA && i + 1 < s.size() && (unsigned char)s[i + 1] == 0xBC) ||
               (c == 0xC2 && i + 1 < s.size() && (unsigned char)s[i + 1] == 0xB4)) {
      o += '\'';
      i += 1;
    } else if (c == '`') {
      o += '\'';
    } else {
      o += (c >= 'A' && c <= 'Z') ? (char)(c + 32) : (char)c;
    }
  }
  while (!o.empty() && o.back() == ' ') o.pop_back();
  return o;
}

int ssidMatch(const std::string& saved, const std::string& seen) {
  if (saved.empty() || seen.empty()) return 0;
  if (saved == seen) return 2;
  return fold(saved) == fold(seen) ? 1 : 0;
}

// --------------------------------------------------------------- WifiBook ---

int WifiBook::find(const std::string& ssid) const {
  for (int i = 0; i < count(); ++i)
    if (nets_[(size_t)i].ssid == ssid) return i;
  return -1;
}

int WifiBook::add(const WifiNet& n) {
  if (n.ssid.empty() || n.ssid.size() > 32) return -1;
  if (!n.pass.empty() && (n.pass.size() < 8 || n.pass.size() > 63)) return -1;
  WifiNet m = n;
  if (m.prio < 1) m.prio = 1;
  if (m.prio > 9) m.prio = 9;
  const int i = find(n.ssid);
  if (i >= 0) {
    if (m.pass.empty()) m.pass = nets_[(size_t)i].pass;
    nets_[(size_t)i] = m;
    return i;
  }
  if (count() >= kMax) return -1;
  nets_.push_back(m);
  return count() - 1;
}

bool WifiBook::remove(int i) {
  if (i < 0 || i >= count()) return false;
  for (char& c : nets_[(size_t)i].pass) c = 0;  // the password does not linger in RAM
  nets_.erase(nets_.begin() + i);
  return true;
}

bool WifiBook::setPrio(int i, uint8_t prio) {
  if (i < 0 || i >= count() || prio < 1 || prio > 9) return false;
  nets_[(size_t)i].prio = prio;
  return true;
}

int WifiBook::topPrio() const {
  int p = 0;
  for (const WifiNet& n : nets_)
    if (n.prio > p) p = n.prio;
  return p;
}

static constexpr uint8_t kBookVersion = 1;

std::string WifiBook::save() const {
  std::string b = "WB";
  b += (char)kBookVersion;
  b += (char)count();
  for (const WifiNet& n : nets_) {
    b += (char)n.kind;
    b += (char)n.prio;
    b += (char)n.ssid.size();
    b += n.ssid;
    b += (char)n.pass.size();
    b += n.pass;
  }
  return b;
}

bool WifiBook::load(const std::string& s) {
  const size_t n = s.size();
  if (n < 4 || s[0] != 'W' || s[1] != 'B' || (uint8_t)s[2] != kBookVersion || (uint8_t)s[3] > kMax) return false;
  std::vector<WifiNet> out;
  size_t p = 4;
  for (int k = 0; k < (uint8_t)s[3]; ++k) {
    if (p + 3 > n) return false;
    WifiNet w;
    const uint8_t kind = (uint8_t)s[p], prio = (uint8_t)s[p + 1], sl = (uint8_t)s[p + 2];
    p += 3;
    if (kind > (uint8_t)WifiKind::Other || prio < 1 || prio > 9 || sl < 1 || sl > 32 || p + sl + 1 > n) return false;
    w.kind = (WifiKind)kind;
    w.prio = prio;
    w.ssid = s.substr(p, sl);
    p += sl;
    const uint8_t pl = (uint8_t)s[p++];
    if (pl > 63 || p + pl > n) return false;
    w.pass = s.substr(p, pl);
    p += pl;
    out.push_back(w);
  }
  if (p != n) return false;
  nets_.swap(out);
  return true;
}

// ------------------------------------------------------------- the probe ---

ProbeResult classifyProbe(int status, size_t bodyLen) {
  if (status < 0) return ProbeResult::NoInternet;
  if (status == 204) return ProbeResult::Online;
  if (status == 200 && bodyLen == 0) return ProbeResult::Online;  // some transparent proxies answer 200, empty
  // a redirect to a login page, a page instead of "nothing", 511 Network Authentication Required
  if ((status >= 300 && status < 400) || status == 200 || status == 511) return ProbeResult::Captive;
  return ProbeResult::NoInternet;  // 403 / 5xx from a firewall or a broken proxy
}

// ------------------------------------------------------------- WifiRoamer ---

static bool before(uint32_t now, uint32_t t) { return (int32_t)(now - t) < 0; }

NetState WifiRoamer::state() const {
  if (!book_ || book_->count() == 0) return NetState::NoNetworks;
  return st_;
}

void WifiRoamer::startSearch(uint32_t now) {
  st_ = NetState::Searching;
  cur_ = -1;
  pendNet_ = -1;
  probeOut_ = false;
  nextScan_ = now;
}

void WifiRoamer::preferFirst(int net) {
  if (!book_ || net < 0 || net >= book_->count() || st_ != NetState::Searching || pendNet_ >= 0) return;
  pendNet_ = net;
  pendSsid_ = book_->at(net).ssid;
}

void WifiRoamer::kick(uint32_t now) {
  kickT_ = now;
  for (Back& b : back_)
    if (b.fails < 100) b = Back();  // a wrong password (fails >= 100) keeps waiting until the book changes
  if (st_ == NetState::Searching && !scanning_) nextScan_ = now;
  if (st_ == NetState::Captive || st_ == NetState::NoInternet) nextProbe_ = now;
}

void WifiRoamer::bookChanged(uint32_t now, const std::string& currentSsid) {
  for (Back& b : back_) b = Back();
  fail_ = JoinFail::None;
  failNet_ = -1;
  pendNet_ = -1;
  const int c = book_ && !currentSsid.empty() ? book_->find(currentSsid) : -1;
  if (st_ == NetState::Joining || st_ == NetState::Searching || st_ == NetState::NoNetworks) {
    if (st_ == NetState::Joining) leave_ = true;  // re-plan from a fresh scan
    startSearch(now);
  } else if (c < 0) {
    leave_ = true;  // the network we are on was forgotten
    startSearch(now);
  } else {
    cur_ = c;
    nextScan_ = now;  // a new, better network may be in reach
  }
  kick(now);
}

uint32_t WifiRoamer::searchInterval(uint32_t now) const {
  const uint32_t since = now - kickT_;
  return since < kFastWindowMs ? kFastScanMs : since < kSlowWindowMs ? kSlowScanMs : kIdleScanMs;
}

void WifiRoamer::backoff(uint32_t now, int i, uint32_t ms) {
  if (i < 0 || i >= WifiBook::kMax) return;
  back_[i].until = now + ms;
}

int WifiRoamer::pick(uint32_t now, const std::vector<ScanHit>& hits, int exclude, int* rssiOut,
                     std::string* seenOut) const {
  int best = -1, bestPrio = -1, bestRssi = -200, bestExact = 0;
  std::string bestSeen;
  for (int i = 0; book_ && i < book_->count(); ++i) {
    if (i == exclude || before(now, back_[i].until)) continue;
    const WifiNet& n = book_->at(i);
    int r = -200, ex = 0;
    std::string seen;
    for (const ScanHit& h : hits) {
      const int m = ssidMatch(n.ssid, h.ssid);
      if (!m || h.rssi < kMinRssi) continue;
      if (m > ex || (m == ex && h.rssi > r)) {
        ex = m;
        r = h.rssi;
        seen = h.ssid;
      }
    }
    if (!ex) continue;
    if (n.prio > bestPrio || (n.prio == bestPrio && (r > bestRssi || (r == bestRssi && ex > bestExact)))) {
      best = i;
      bestPrio = n.prio;
      bestRssi = r;
      bestExact = ex;
      bestSeen = seen;
    }
  }
  if (best >= 0) {
    if (rssiOut) *rssiOut = bestRssi;
    if (seenOut) *seenOut = bestSeen;
  }
  return best;
}

RoamCmd WifiRoamer::tick(uint32_t now, bool linkUp, int rssi) {
  RoamCmd cmd;
  if (!started_) {
    started_ = true;
    kickT_ = now;
    nextScan_ = now;
  }
  if (!book_ || book_->count() == 0) {
    st_ = NetState::Searching;
    cur_ = -1;
    if (linkUp) cmd.kind = RoamCmd::Leave;
    return cmd;
  }
  if (leave_) {
    leave_ = false;
    cmd.kind = RoamCmd::Leave;
    return cmd;
  }
  if (scanning_) {
    if (!before(now, scanT_ + 15000)) scanning_ = false;  // a scan that never reported: try again
    return cmd;
  }
  switch (st_) {
    case NetState::NoNetworks:
    case NetState::Searching:
      if (pendNet_ >= 0) {
        st_ = NetState::Joining;
        cur_ = pendNet_;
        joinT_ = now;
        cmd.kind = RoamCmd::Join;
        cmd.net = pendNet_;
        cmd.ssid = pendSsid_;
        pendNet_ = -1;
        return cmd;
      }
      if (!before(now, nextScan_)) {
        scanning_ = true;
        scanT_ = now;
        cmd.kind = RoamCmd::Scan;
      }
      return cmd;
    case NetState::Joining:
      if (linkUp) {
        st_ = NetState::Checking;
        probeOut_ = true;
        probeT_ = now;
        cmd.kind = RoamCmd::Probe;
        return cmd;
      }
      if (!before(now, joinT_ + kJoinTimeoutMs)) {
        joinFailed(now, JoinFail::Timeout);
        cmd.kind = RoamCmd::Leave;
      }
      return cmd;
    case NetState::Checking:
      if (!linkUp) break;
      if (!before(now, probeT_ + kProbeTimeoutMs)) probed(now, ProbeResult::NoInternet);  // the driver never answered
      return cmd;
    case NetState::Online:
    case NetState::Captive:
    case NetState::NoInternet: {
      if (!linkUp) break;
      if (pendNet_ >= 0) {  // a better network: move (the driver leaves the current one first)
        st_ = NetState::Joining;
        cur_ = pendNet_;
        joinT_ = now;
        cmd.kind = RoamCmd::Join;
        cmd.net = pendNet_;
        cmd.ssid = pendSsid_;
        pendNet_ = -1;
        return cmd;
      }
      if (st_ != NetState::Online && !probeOut_ && !before(now, nextProbe_)) {
        probeOut_ = true;
        probeT_ = now;
        nextProbe_ = now + kRecheckMs;
        cmd.kind = RoamCmd::Probe;
        return cmd;
      }
      if (st_ != NetState::Online && probeOut_ && !before(now, probeT_ + kProbeTimeoutMs)) probeOut_ = false;
      const bool secondChoice = cur_ >= 0 && book_->at(cur_).prio < book_->topPrio();
      const bool weak = rssi != 0 && rssi < kWeakRssi;
      const uint32_t every = st_ != NetState::Online ? kRecheckMs : (secondChoice || weak) ? kRoamScanMs : 0;
      if (every && book_->count() > 1 && !before(now, nextScan_)) {
        scanning_ = true;
        scanT_ = now;
        nextScan_ = now + every;
        cmd.kind = RoamCmd::Scan;
      }
      return cmd;
    }
  }
  // the link went away: search again, fast (the hotspot was switched off, we walked out of range)
  kickT_ = now;
  startSearch(now);
  return cmd;
}

void WifiRoamer::scanDone(uint32_t now, const std::vector<ScanHit>& hits) {
  scanning_ = false;
  ++scans_;
  int rssi = -200;
  std::string seen;
  if (st_ == NetState::Searching || st_ == NetState::NoNetworks) {
    nextScan_ = now + searchInterval(now);
    const int i = pick(now, hits, -1, &rssi, &seen);
    if (i >= 0) {
      pendNet_ = i;
      pendSsid_ = seen;
    } else if (book_ && book_->count() > 0) {
      // nothing we can join: a network in reach with a wrong password says so; else "looking for…"
      int bad = -1;
      for (int k = 0; k < book_->count() && bad < 0; ++k)
        if (back_[k].fails >= 100)
          for (const ScanHit& h : hits)
            if (ssidMatch(book_->at(k).ssid, h.ssid)) bad = k;
      if (bad >= 0) {
        fail_ = JoinFail::BadPassword;
        failNet_ = bad;
      } else if (fail_ == JoinFail::None) {
        fail_ = JoinFail::NotFound;
        failNet_ = -1;
      }
    }
    return;
  }
  if (cur_ < 0 || !book_) return;
  const int i = pick(now, hits, cur_, &rssi, &seen);
  if (i < 0) return;
  const WifiNet& cand = book_->at(i);
  const WifiNet& here = book_->at(cur_);
  int hereRssi = -200;
  for (const ScanHit& h : hits)
    if (ssidMatch(here.ssid, h.ssid) && h.rssi > hereRssi) hereRssi = h.rssi;
  bool move = false;
  if (st_ == NetState::Captive || st_ == NetState::NoInternet) move = true;  // anything that works beats this
  else if (st_ == NetState::Online)
    move = (cand.prio > here.prio && rssi >= kRoamRssi) ||
           (hereRssi < kWeakRssi && cand.prio >= here.prio && rssi >= hereRssi + 10);
  if (move) {
    pendNet_ = i;
    pendSsid_ = seen;
  }
}

void WifiRoamer::joinFailed(uint32_t now, JoinFail why) {
  const int i = cur_;
  fail_ = why;
  failNet_ = i;
  if (i >= 0 && i < WifiBook::kMax) {
    Back& b = back_[i];
    if (why == JoinFail::BadPassword) {
      b.fails = 100;
      b.until = now + 30u * 60u * 1000u;  // until the book changes or 30 min pass (the router may have been reset)
    } else {
      if (b.fails < 6) ++b.fails;
      uint32_t ms = 15000u << (b.fails - 1);  // 15 s, 30 s, 1 min ... 8 min
      if (ms > 8u * 60u * 1000u) ms = 8u * 60u * 1000u;
      b.until = now + ms;
    }
  }
  startSearch(now);
}

void WifiRoamer::probed(uint32_t now, ProbeResult r) {
  probeOut_ = false;
  if (cur_ < 0) return;
  if (st_ != NetState::Checking && st_ != NetState::Online && st_ != NetState::Captive && st_ != NetState::NoInternet)
    return;
  nextProbe_ = now + kRecheckMs;
  switch (r) {
    case ProbeResult::Online:
      st_ = NetState::Online;
      fail_ = JoinFail::None;
      failNet_ = -1;
      back_[cur_] = Back();
      nextScan_ = now + kRoamScanMs;
      break;
    case ProbeResult::Captive:
      if (st_ != NetState::Captive) nextScan_ = now;  // look for another network right away
      st_ = NetState::Captive;
      backoff(now, cur_, 10u * 60u * 1000u);         // and don't come back to it first
      break;
    case ProbeResult::NoInternet:
      if (st_ != NetState::NoInternet) nextScan_ = now;
      st_ = NetState::NoInternet;
      backoff(now, cur_, 3u * 60u * 1000u);
      break;
  }
}

// --------------------------------------------------------------- AskQueue ---

bool AskQueue::push(const std::string& text, float now, int tries) {
  if (text.empty()) return false;
  for (const Item& it : q_)
    if (it.text == text) return false;
  if ((int)q_.size() >= kMax) {
    q_.erase(q_.begin());
    ++dropped_;
  }
  q_.push_back({text, now, tries});
  return true;
}

bool AskQueue::pop(float now, Item& out) {
  while (!q_.empty()) {
    Item it = q_.front();
    q_.erase(q_.begin());
    if (now - it.t <= kMaxAgeS) {
      out = it;
      return true;
    }
    ++dropped_;
  }
  return false;
}

}  // namespace suflet
