// SoulOS apps on the device (os/APPS.md): the launcher's list, the apps'
// gestures and logic, and their requests to SOUL Cloud. Drawing is in
// OsAppsDraw.cpp. Every app follows the same rules (os/APPS.md §2):
//   back       swipe down (or ->) and the side button, always one level up;
//              on the map and on Control, a swipe that starts at the top edge
//   open       from the eyes: swipe -> the orbit (it opens on the app used
//              last) -> tap; the two neighbours open with one tap too
//   idle       a screen left alone goes back to the eyes after 15 s, unless
//              something runs on it (a route, a game, a breath, a stopwatch)
//   no dead ends: every empty / offline / not-set-up state says what to do
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <ArduinoJson.h>

#include "Os.h"

namespace suflet {

using namespace eyes;

static const Rgb kAmber = Rgb::hex(0xFFB347), kMint = Rgb::hex(0xC9F2E4), kCream = Rgb::hex(0xFFF0C8),
                 kIce = Rgb::hex(0x9FC6FF);

// item ids of the app screens (Os.cpp / OsDraw.cpp use 1..99 and 100.. for rows)
enum : int {
  AStart = 200, AStop, APause, ASkip, ANext, APrev, APhone, AEnd, APlus, AMinus, ACenter, ARetry, ANew, ASwap,
  AQty, AFrom, ATo, AValue, ARing, AFound, AMode, ALap, AReset, AWifi, AGo, AAgain, AMenu, APattern, ADur,
  AStartNav, AClose, ASound, ASleepT, AWhereQr, AAi, AAuto,
  AGame = 260,   // + 0..2
  AReply = 280,  // + 0..3
  ATile = 300,   // + 0..3 (Control)
  ARow = 400,    // + i
  AUp = 500,     // + i (Settings › Apps: move up)
};

// keyboard contexts of the apps (Os.cpp's own are 1..)
enum : int { KbWhereTo = 40, KbHabitNew, KbConvert, KbReply };

const char* fetchName(Fetch f) {
  static const char* const k[] = {"none", "weather", "agenda", "rates", "where", "mapview", "routeplan",
                                  "routeget", "routeend", "routesend", "findphone", "wifilocate"};
  static_assert(sizeof(k) / sizeof(k[0]) == (unsigned)Fetch::Count, "fetch names");
  return (unsigned)f < (unsigned)Fetch::Count ? k[(int)f] : "?";
}

// ------------------------------------------------------------ the list ---

static const AppId kAll[] = {AppId::Talk,     AppId::Today,      AppId::Maps,    AppId::Weather,   AppId::Calendar,
                             AppId::Alarms,   AppId::Timer,      AppId::Stopwatch, AppId::Focus,   AppId::Breathe,
                             AppId::Habits,   AppId::Notes,      AppId::Music,   AppId::Games,     AppId::WorldClock,
                             AppId::Convert,  AppId::FindPhone,  AppId::Claude,  AppId::Device,    AppId::MySoul,
                             AppId::Settings};
static_assert(sizeof(kAll) / sizeof(kAll[0]) == (unsigned)AppId::Count, "every app in the orbit");

View Os::viewOf(AppId a) const {
  switch (a) {
    case AppId::Talk: return View::Talk;
    case AppId::Today: return View::Today;
    case AppId::Maps: return View::Maps;
    case AppId::Weather: return View::Weather;
    case AppId::Calendar: return View::Calendar;
    case AppId::Alarms: return View::Alarms;
    case AppId::Timer: return View::Timer;
    case AppId::Stopwatch: return View::Stopwatch;
    case AppId::Focus: return View::Focus;
    case AppId::Breathe: return View::Breathe;
    case AppId::Habits: return View::Habits;
    case AppId::Notes: return View::Notes;
    case AppId::Music: return View::Music;
    case AppId::Games: return View::Games;
    case AppId::WorldClock: return View::WorldClock;
    case AppId::Convert: return View::Convert;
    case AppId::FindPhone: return View::FindPhone;
    case AppId::Claude: return View::Claude;
    case AppId::Device: return View::Device;
    case AppId::MySoul: return View::MySoul;
    default: return View::Settings;
  }
}

std::string Os::appName(AppId a) const {
  static const char* const en[] = {"Talk",   "Today",  "Maps",       "Weather", "Calendar",   "Alarms", "Timer",
                                   "Stopwatch", "Focus", "Breathe", "Habits", "Notes",      "Music",  "Games",
                                   "World clock", "Convert", "Find phone", "Claude", "Device", "My SOUL", "Settings"};
  static const char* const r[] = {"Vorbește", "Azi",      "Hărți",      "Vremea",   "Calendar",    "Alarme",
                                  "Minutar",  "Cronometru", "Focus",    "Respiră",  "Obiceiuri",   "Notițe",
                                  "Muzică",   "Jocuri",   "Ora lumii",  "Convertor", "Găsește telefonul", "Claude",
                                  "Dispozitiv", "SOUL-ul meu", "Setări"};
  static_assert(sizeof(en) / sizeof(en[0]) == (unsigned)AppId::Count, "names");
  const int i = (int)a < (int)AppId::Count ? (int)a : 0;
  return ro() ? r[i] : en[i];
}

int Os::visibleApps() const {
  int n = 0;
  for (uint8_t a : apps_.order)
    if (!(apps_.hidden >> a & 1u)) ++n;
  return n ? n : 1;
}

AppId Os::appAt(int i) const {
  const int n = visibleApps();
  i = ((i % n) + n) % n;
  for (uint8_t a : apps_.order) {
    if (apps_.hidden >> a & 1u) continue;
    if (i-- == 0) return (AppId)a;
  }
  return AppId::Settings;
}

void Os::openApp(AppId a) {
  for (int i = 0; i < visibleApps(); ++i)
    if (appAt(i) == a) orbit_ = i;  // the orbit opens on it next time: the last app is one swipe + one tap away
  apps_.last = a;
  idleT_ = 0;  // opening an app is using SoulOS: its idle clock starts now
  const View v = viewOf(a);
  if (v == View::Talk) face_.react(X_happy, 0.8f);
  go(v);  // (go() tells the app it opened: appOpened)
}

void Os::appsBegin() {
  if (apps_.order.size() != (size_t)AppId::Count) {
    apps_.order.clear();
    for (AppId a : kAll) apps_.order.push_back((uint8_t)a);
  }
  if (apps_.clocks.empty()) apps_.clocks = {8, 11, 15};  // London, New York, Tokyo
  if (apps_.habits.empty()) {
    apps_.habits.push_back({ro() ? "Apă, 8 pahare" : "Water, 8 glasses", 0, 0});
    apps_.habits.push_back({ro() ? "Plimbare" : "A walk outside", 0, 0});
    apps_.habits.push_back({ro() ? "Citit 10 min" : "Read 10 min", 0, 0});
  }
  apps_.view.screenW = g_.w;
  apps_.view.screenH = g_.h;
  apps_.sound.set(SoundGen::Rain, apps_.volume);
}

// ----------------------------------------------------------- persistence ---

std::string Os::saveApps() const {
  std::string b;
  std::string ord;
  for (uint8_t a : apps_.order) ord += (char)('a' + a);
  apps::kvSet(b, "order", ord);
  apps::kvSet(b, "hidden", std::to_string(apps_.hidden));
  apps::kvSet(b, "dnd", apps_.dnd ? "1" : "0");
  apps::kvSet(b, "vol", std::to_string((int)lroundf(apps_.volume * 100)));
  std::string cl;
  for (uint8_t c : apps_.clocks) cl += (char)('a' + c);
  apps::kvSet(b, "clocks", cl);
  for (size_t i = 0; i < apps_.habits.size() && i < 6; ++i) {
    char k[8];
    snprintf(k, sizeof k, "h%u", (unsigned)i);
    char v[48];
    snprintf(v, sizeof v, "%lu,%lu,", (unsigned long)apps_.habits[i].day, (unsigned long)apps_.habits[i].bits);
    apps::kvSet(b, k, v + apps_.habits[i].name);
  }
  apps::kvSet(b, "hn", std::to_string(apps_.habits.size()));
  char best[48];
  snprintf(best, sizeof best, "%d,%d,%d", apps_.best[0], apps_.best[1], apps_.best[2]);
  apps::kvSet(b, "best", best);
  apps::kvSet(b, "sound", std::to_string((int)apps_.sound.kind()));
  apps::kvSet(b, "breath", std::to_string(apps_.breathPat));
  char conv[32];
  snprintf(conv, sizeof conv, "%d,%d,%d", apps_.q, apps_.from, apps_.to);
  apps::kvSet(b, "conv", conv);
  if (apps_.haveFix) {  // the last place (24 h, like the cloud): the map can open offline
    char f[96];
    snprintf(f, sizeof f, "%.6f,%.6f,%d,%lu", apps_.fix.lat, apps_.fix.lon, (int)apps_.fix.accM, (unsigned long)apps_.fix.at);
    apps::kvSet(b, "fix", f);
  }
  apps::kvSet(b, "last", std::to_string((int)apps_.last));
  return b;
}

void Os::loadApps(const std::string& b) {
  const std::string ord = apps::kvGet(b, "order");
  if (!ord.empty()) {  // keep the saved order, add apps a newer firmware brought at the end
    std::vector<uint8_t> o;
    uint32_t seen = 0;
    for (char c : ord) {
      const int a = c - 'a';
      if (a >= 0 && a < (int)AppId::Count && !(seen >> a & 1u)) {
        o.push_back((uint8_t)a);
        seen |= 1u << a;
      }
    }
    for (AppId a : kAll)
      if (!(seen >> (int)a & 1u)) o.push_back((uint8_t)a);
    apps_.order = o;
  }
  apps_.hidden = (uint32_t)strtoul(apps::kvGet(b, "hidden", "0").c_str(), nullptr, 10);
  apps_.hidden &= ~(1u << (int)AppId::Settings);  // Settings can never be hidden: no dead end
  apps_.dnd = apps::kvGet(b, "dnd") == "1";
  const int vol = atoi(apps::kvGet(b, "vol", "70").c_str());
  apps_.volume = (vol < 0 ? 0 : vol > 100 ? 100 : vol) / 100.0f;
  const std::string cl = apps::kvGet(b, "clocks");
  if (!cl.empty()) {
    apps_.clocks.clear();
    for (char c : cl)
      if (c - 'a' >= 0 && c - 'a' < (int)apps::cities().size() && apps_.clocks.size() < 4) apps_.clocks.push_back((uint8_t)(c - 'a'));
  }
  const int hn = atoi(apps::kvGet(b, "hn", "-1").c_str());
  if (hn >= 0) {
    apps_.habits.clear();
    for (int i = 0; i < hn && i < 6; ++i) {
      char k[8];
      snprintf(k, sizeof k, "h%d", i);
      const std::string v = apps::kvGet(b, k);
      unsigned long day = 0, bits = 0;
      int used = 0;
      if (sscanf(v.c_str(), "%lu,%lu,%n", &day, &bits, &used) == 2 && used > 0) {
        apps::Habit h;
        h.day = (uint32_t)day;
        h.bits = (uint32_t)bits;
        h.name = v.substr((size_t)used, 40);
        if (!h.name.empty()) apps_.habits.push_back(h);
      }
    }
  }
  sscanf(apps::kvGet(b, "best", "0,0,0").c_str(), "%d,%d,%d", &apps_.best[0], &apps_.best[1], &apps_.best[2]);
  const int snd = atoi(apps::kvGet(b, "sound", "0").c_str());
  apps_.sound.set((SoundGen::Kind)(snd >= 0 && snd < SoundGen::Count ? snd : 0), apps_.volume);
  apps_.breathPat = atoi(apps::kvGet(b, "breath", "0").c_str()) % (int)apps::breathPatterns().size();
  int q = 0, f = 0, t = 1;
  if (sscanf(apps::kvGet(b, "conv", "0,0,1").c_str(), "%d,%d,%d", &q, &f, &t) == 3 && q >= 0 && q < (int)apps::Quantity::Count) {
    const int n = (int)apps::units((apps::Quantity)q).size();
    apps_.q = q;
    apps_.from = f >= 0 && f < n ? f : 0;
    apps_.to = t >= 0 && t < n ? t : 1;
  }
  double la = 0, lo = 0;
  int acc = 50;
  unsigned long at = 0;
  if (sscanf(apps::kvGet(b, "fix").c_str(), "%lf,%lf,%d,%lu", &la, &lo, &acc, &at) == 4 && (la || lo)) {
    apps_.haveFix = true;
    apps_.fix.lat = la;
    apps_.fix.lon = lo;
    apps_.fix.accM = (float)acc;
    apps_.fix.at = (uint32_t)at;
    apps_.fixSrc = "saved";
    apps_.view.centerOn(la, lo);
  }
  const int last = atoi(apps::kvGet(b, "last", "0").c_str());
  if (last >= 0 && last < (int)AppId::Count) apps_.last = (AppId)last;
}

// ---------------------------------------------------------------- fetch ---

void Os::fetch(Fetch k, const std::string& path, const std::string& body, bool post, bool del) {
  for (const AppFetch& f : apps_.fetches)
    if (f.kind == k && k != Fetch::MapView) return;  // one of each in flight (map views replace each other)
  if (apps_.fetches.size() >= 8) apps_.fetches.erase(apps_.fetches.begin());
  AppFetch f;
  f.kind = k;
  f.path = path;
  f.body = body;
  f.post = post;
  f.del = del;
  apps_.fetches.push_back(f);
  pushCmd(OsCmd::AppFetch);
}

bool Os::popAppFetch(AppFetch& f) {
  if (apps_.fetches.empty()) return false;
  f = apps_.fetches.front();
  apps_.fetches.erase(apps_.fetches.begin());
  return true;
}

static bool cloudUsable(const NetInfo& n) { return n.relay && n.paired; }

void Os::mapsAskView(bool force) {
  AppsState& A = apps_;
  if (!cloudUsable(net_)) return;
  const maps::MapView& v = A.view;
  const double hw = v.screenW * 0.5 / v.scale, hh = v.screenH * 0.5 / v.scale;
  const bool covered = !A.bundle.empty() && A.bundle.covers(v.z, v.cx - hw, v.cy - hh, v.cx + hw, v.cy + hh) &&
                       (A.bundle.z == v.z || A.bundle.z == v.z - 1 || A.bundle.z == v.z + 1);
  if (covered && !force) return;
  if (A.viewWait && t_ - A.viewAsked < 6) return;
  char p[96];
  snprintf(p, sizeof p, "/v1/device/maps/view?lat=%.5f&lon=%.5f&z=%d", v.lat(), v.lon(), v.z);
  A.viewWait = true;
  A.viewAsked = t_;
  A.viewZ = v.z;
  fetch(Fetch::MapView, p);
}

void appsReleaseLayers();  // OsAppsDraw.cpp

void Os::appOpened(View v) {
  AppsState& A = apps_;
  if (v == View::Home) appsReleaseLayers();
  const bool cloud = cloudUsable(net_);
  switch (v) {
    case View::Weather:
    case View::Today:
      if (cloud && (!A.weather.ok || now_ - A.weather.at > 900) && t_ - A.wxAsked > 20) {
        A.wxAsked = t_;
        A.wxWait = true;
        fetch(Fetch::Weather, "/v1/device/apps/weather");
      }
      if (v == View::Weather) break;
      [[fallthrough]];
    case View::Calendar:
      if (cloud && (!A.agenda.ok || now_ - A.agenda.at > 900) && t_ - A.calAsked > 20) {
        A.calAsked = t_;
        A.calWait = true;
        fetch(Fetch::Agenda, "/v1/device/apps/agenda");
      }
      A.calSel = -1;
      A.calPage = 0;
      break;
    case View::Maps: mapsOpen(); break;
    case View::Convert:
      if (cloud && t_ - A.ratesAsked > 6 * 3600) {
        A.ratesAsked = t_;
        fetch(Fetch::Rates, "/v1/device/apps/rates");
      }
      break;
    case View::Games:
      A.game = -1;
      break;
    case View::FindPhone:
      if (A.findState >= 2 && t_ - A.findT > 90) A.findState = 0;
      break;
    default: break;
  }
}

void Os::mapsOpen() {
  AppsState& A = apps_;
  A.sendSheet = false;
  if (cloudUsable(net_) && t_ - A.whereAsked > 8) {
    A.whereAsked = t_;
    A.whereWait = true;
    fetch(Fetch::Where, "/v1/device/maps/where");
  }
  if (cloudUsable(net_) && !A.navOn && !A.route.valid() && t_ - A.navAsked > 30) {  // a route planned by your AI
    A.navAsked = t_;
    fetch(Fetch::RouteGet, "/v1/device/maps/route");
  }
  if (A.haveFix) {
    if (A.followMe && !A.navOn && !A.preview) A.view.centerOn(A.fix.lat, A.fix.lon);
    mapsAskView(false);
  }
  A.mapDirty = true;
}

void Os::navStart() {
  AppsState& A = apps_;
  if (!A.route.valid()) return;
  A.nav.start(&A.route, now_);
  A.navOn = true;
  A.preview = false;
  A.arrivedShown = false;
  A.followMe = true;
  if (A.haveFix) A.nav.fix(A.fix);
  face_.react(X_excited, 1.0f);
  toast(tr("Let's go: ", "Hai: ") + A.route.to, kMint, 2.5f);
  A.mapDirty = true;
  invalidate();
}

static void fitRoute(maps::MapView& v, const maps::RouteData& r) {
  double la0 = 90, la1 = -90, lo0 = 180, lo1 = -180;
  for (int i = 0; i < r.points(); ++i) {
    la0 = fmin(la0, r.shape[2 * i]);
    la1 = fmax(la1, r.shape[2 * i]);
    lo0 = fmin(lo0, r.shape[2 * i + 1]);
    lo1 = fmax(lo1, r.shape[2 * i + 1]);
  }
  for (int z = maps::kMaxZ; z >= maps::kMinZ; --z) {  // the biggest zoom where the route fits in ~300 px
    double x0, y0, x1, y1;
    maps::worldPx(la1, lo0, z, x0, y0);
    maps::worldPx(la0, lo1, z, x1, y1);
    if (x1 - x0 <= 290 && y1 - y0 <= 260) {
      v.z = z;
      v.scale = 1;
      v.cx = (x0 + x1) / 2;
      v.cy = (y0 + y1) / 2 + 20;
      return;
    }
  }
}

void Os::appData(Fetch kind, int status, const std::string& body) {
  AppsState& A = apps_;
  invalidate();
  switch (kind) {
    case Fetch::Weather:
      A.wxWait = false;
      if (status == 200 && A.weather.parse(body.data(), body.size(), now_)) A.wxErr = 0;
      else A.wxErr = status ? status : -1;
      break;
    case Fetch::Agenda: {
      A.calWait = false;
      if (status == 200 && A.agenda.parse(body.data(), body.size(), now_)) {
        A.calErr = 0;
        A.calErrCode.clear();
      } else {
        A.calErr = status ? status : -1;
        JsonDocument d;
        if (!deserializeJson(d, body)) A.calErrCode = d["error"]["code"] | "";
      }
      break;
    }
    case Fetch::Rates:
      if (status == 200) A.rates.parse(body.data(), body.size());
      break;
    case Fetch::Where:
    case Fetch::WifiLocate: {
      A.whereWait = false;
      JsonDocument d;
      if (status != 200 || deserializeJson(d, body)) {
        A.mapErr = status ? status : -1;
        if (!deserializeJson(d, body)) {
          A.mapErrCode = d["error"]["code"] | "";
          A.mapErrMsg = d["error"]["msg"] | "";
        }
        if (kind == Fetch::WifiLocate)
          toast(A.mapErrCode == "not_allowed" ? tr("Allow Wi-Fi location on /me/where first", "Permite locația prin Wi-Fi pe /me/where")
                                              : tr("No place from Wi-Fi", "Wi-Fi-ul nu știe unde sunt"),
                kAmber, 3.5f);
        break;
      }
      JsonObjectConst f = d["fix"].as<JsonObjectConst>();
      if (f.isNull()) {
        if (kind == Fetch::WifiLocate) toast(tr("No place from Wi-Fi", "Wi-Fi-ul nu știe unde sunt"), kAmber, 3.0f);
        A.mapErr = 0;
        break;
      }
      A.mapErr = 0;
      const bool first = !A.haveFix;
      A.fix.lat = f["lat"] | 0.0;
      A.fix.lon = f["lon"] | 0.0;
      A.fix.accM = f["acc"] | 50;
      A.fixAge = f["age"] | 0;
      A.fix.at = now_ > A.fixAge ? now_ - A.fixAge : now_;
      A.fixSrc = f["src"] | "phone";
      A.fixLabel = f["label"] | "";
      A.haveFix = true;
      if (A.navOn) {
        const int before = A.nav.step();
        A.nav.fix(A.fix);
        if (A.nav.step() != before) face_.react(X_happy, 0.6f);
      }
      if (A.followMe && !A.preview) A.view.centerOn(A.fix.lat, A.fix.lon);
      if (first) face_.react(X_happy, 0.8f);
      pushCmd(OsCmd::SaveApps);
      mapsAskView(false);
      A.mapDirty = true;
      break;
    }
    case Fetch::MapView:
      A.viewWait = false;
      if (status == 200) {
        maps::MapBundle b;
        if (b.decode((const uint8_t*)body.data(), body.size())) {
          A.bundle = b;
          A.mapAt = now_;
          A.mapErr = 0;
          A.mapDirty = true;
        }
      } else {
        A.mapErr = status ? status : -1;
        JsonDocument d;
        if (!deserializeJson(d, body)) A.mapErrCode = d["error"]["code"] | "";
      }
      break;
    case Fetch::RoutePlan:
    case Fetch::RouteGet: {
      A.routeWait = false;
      if (kind == Fetch::RouteGet && (A.navOn || A.preview)) break;  // already on a route: the new plan wins
      if (status == 200 && A.route.parse(body.data(), body.size())) {
        A.navOn = false;
        A.nav.stop();
        A.preview = true;
        A.followMe = false;
        fitRoute(A.view, A.route);
        mapsAskView(true);
        A.mapDirty = true;
        face_.react(X_happy, 1.0f);
        if (view_ != View::Maps && view_ != View::Keyboard) {
          go(View::Maps);
          apps_.sendSheet = false;
        }
      } else if (kind == Fetch::RoutePlan) {
        JsonDocument d;
        std::string code, msg;
        if (!deserializeJson(d, body)) {
          code = d["error"]["code"] | "";
          msg = d["error"]["msg"] | "";
        }
        if (status < 0) msg = tr("No internet: I'll need it to plan a route", "Fără internet: îmi trebuie ca să fac un traseu");
        if (msg.empty()) msg = tr("No route", "Niciun traseu");
        toast(msg, kAmber, 4.5f);
        face_.react(X_confused, 1.2f);
        A.mapErrCode = code;
      }
      break;
    }
    case Fetch::RouteSend:
      if (status == 200) toast(tr("Also on your phone: /me/where", "Și pe telefon: /me/where"), kMint, 3.0f);
      break;
    case Fetch::FindPhone: {
      JsonDocument d;
      if (status == 200 && !deserializeJson(d, body)) {
        const std::string reach = d["reach"] | "none";
        A.findState = reach == "page" ? 2 : reach == "push" ? 3 : 4;
        face_.react(A.findState == 4 ? X_sad : X_excited, 1.2f);
      } else {
        A.findState = 5;
        face_.react(X_confused, 1.2f);
      }
      A.findT = t_;
      break;
    }
    default: break;
  }
}

// --------------------------------------------------------------- update ---

void Os::navStep(float dt) {
  AppsState& A = apps_;
  (void)dt;
  if (!A.navOn) return;
  // while walking, ask where the phone is every 15 s (the owner keeps /me/where open, or Wi-Fi)
  if (view_ == View::Maps && cloudUsable(net_) && t_ - A.whereAsked > 15) {
    A.whereAsked = t_;
    fetch(Fetch::Where, "/v1/device/maps/where");
  }
  if (A.nav.arrived() && !A.arrivedShown) {
    A.arrivedShown = true;
    face_.react(X_love, 1.6f);
    face_.flash(kMint, 1.4f);
    brainEvents_.push_back(Ev::AlarmDue);
    toast(tr("You're there: ", "Ai ajuns: ") + A.route.to, kMint, 4.0f);
  }
}

void Os::gamesStep(float dt) {
  AppsState& A = apps_;
  if (view_ != View::Games || A.game < 0) return;
  if (A.judgeT > 0) A.judgeT -= dt;
  if (A.tapGlow > 0) A.tapGlow -= dt;
  bool over = false;
  int score = 0;
  switch (A.game) {
    case 0: {
      const eyes::EyeMotion& m = face_.motion();
      const uint8_t ev = A.tilt.step(dt, -m.gravX(), m.gravY());
      if (ev & games::TiltBall::Got) face_.react(X_happy, 0.5f);
      if (ev & games::TiltBall::Fell) {
        face_.react(X_shocked, 0.9f);
        face_.flash(kAmber, 0.8f);
      }
      over = (ev & games::TiltBall::Over) != 0;
      score = A.tilt.score();
      break;
    }
    case 1: {
      if (A.rhythm.step(dt) > 0) A.judgeT = 0.5f;
      over = A.rhythm.over() && !A.newBest && A.rhythm.score() >= 0 && !A.rhythm.running();
      score = A.rhythm.score();
      break;
    }
    default: {
      A.memory.step(dt);
      over = A.memory.phase() == games::EyeMemory::Phase::Over;
      score = A.memory.score();
      break;
    }
  }
  if (over && !A.newBest && A.cueGlow >= 0) {
    A.cueGlow = -1;  // once
    if (score > A.best[A.game]) {
      A.best[A.game] = score;
      A.newBest = true;
      pushCmd(OsCmd::SaveApps);
      face_.react(X_excited, 2.0f);
      face_.flash(kMint, 1.4f);
    } else {
      face_.react(X_happy, 1.2f);
    }
  }
  invalidate();
}

void Os::appsUpdate(float dt) {
  AppsState& A = apps_;
  // stopwatch and pomodoro run whatever the screen
  A.sw.tick(dt);
  if (A.sw.run && view_ == View::Stopwatch && (int)(A.sw.acc * 10) != (int)((A.sw.acc - dt) * 10)) invalidate();
  if (A.pomo.tick(dt)) {
    const bool rest = A.pomo.phase() != apps::Pomodoro::Phase::Focus;
    face_.react(rest ? X_love : X_wake, 1.6f);
    face_.flash(rest ? kMint : kAmber, 1.4f);
    brainEvents_.push_back(Ev::AlarmDue);
    toast(rest ? tr("Focus done: take a break", "Gata focusul: ia o pauză") : tr("Back to focus", "Înapoi la focus"),
          rest ? kMint : kAmber, 3.5f);
  }
  if (A.pomo.phase() != apps::Pomodoro::Phase::Idle && view_ == View::Focus &&
      (int)A.pomo.left() != (int)(A.pomo.left() + dt))
    invalidate();
  // focus sounds: the sleep timer
  if (A.playing && A.sleepMin > 0) {
    A.sleepLeft -= dt;
    if (A.sleepLeft <= 0) {
      A.playing = false;
      A.sleepMin = 0;
      invalidate();
    }
  }
  // breathe
  if (A.breathing) {
    A.breathT += dt;
    const apps::BreathPattern& p = apps::breathPatterns()[A.breathPat];
    const apps::BreathPoint b = apps::breathAt(p, A.breathT);
    if (b.cycle != A.breathCycles) A.breathCycles = b.cycle;
    if (A.breathT >= A.breathMin * 60.0f) {
      A.breathing = false;
      face_.react(X_love, 1.6f);
      face_.flash(kMint, 1.4f);
      toast(tr("Well done. Calm.", "Bravo. Liniște."), kMint, 3.0f);
    }
    if (view_ == View::Breathe) invalidate();
  }
  if (view_ == View::Maps) {
    navStep(dt);
    if (A.whereWait || A.viewWait || A.routeWait || A.nav.active()) invalidate();
    if (!A.haveFix && cloudUsable(net_) && t_ - A.whereAsked > 20) {  // waiting for the phone to share
      A.whereAsked = t_;
      fetch(Fetch::Where, "/v1/device/maps/where");
    }
  } else if (A.navOn) {
    navStep(dt);
  }
  if (view_ == View::Games) gamesStep(dt);
  if (view_ == View::FindPhone && A.findState == 1) invalidate();
  if ((view_ == View::Weather && A.wxWait) || (view_ == View::Calendar && A.calWait) || view_ == View::Today ||
      view_ == View::WorldClock)
    if ((int)(t_ * 2) != (int)((t_ - dt) * 2)) invalidate();
}

// ------------------------------------------------------------- gestures ---

static float angleOf(float x, float y, float cx, float cy) { return atan2f(y - cy, x - cx); }

bool Os::appsTouch(const TouchEv& e) {
  AppsState& A = apps_;
  if (view_ != View::Maps && view_ != View::Control) return false;
  const float k = g_.k(), x = e.x / k, y = e.y / k;  // design px
  const float r = hypotf(x - 233, y - 233);
  switch (e.e) {
    case Ev::TouchDown:
      A.downX = A.dragX = x;
      A.downY = A.dragY = y;
      A.downT = t_;
      A.dragging = false;
      A.rimDrag = A.rimArmed = false;
      A.dial = -1;
      if (view_ == View::Control && r > 168 && y > 40 && y < 430 && fabsf(x - 233) > 110) {
        A.dial = x < 233 ? 0 : 1;  // the left rim is light, the right rim is the volume
        A.rimDrag = true;
      } else if (view_ == View::Maps && r > 186 && A.downY > 70 && !A.sendSheet) {
        A.rimArmed = true;  // around the rim: zoom (once it moves; a still tap is a tap on a pill)
        A.rimA = angleOf(x, y, 233, 233);
      }
      return true;
    case Ev::TouchMove: {
      const float dx = x - A.dragX, dy = y - A.dragY;
      if (A.rimDrag && view_ == View::Control) {
        float a = angleOf(x, y, 233, 233) * 57.29578f;  // degrees, 0 = 3 o'clock, + = clockwise
        if (A.dial == 0) {  // brightness: 128 deg (bottom-left, low) .. 232 deg (top-left, high)
          if (a < 0) a += 360;
          const float v = clampf((a - 128) / 104.0f, 0, 1);
          const uint8_t b = (uint8_t)(1 + (int)lroundf(v * 2));
          if (b != set_.bright) {
            set_.bright = b;
            pushCmd(OsCmd::SaveSettings);
          }
        } else {  // volume: 52 deg (bottom-right, low) .. -52 deg (top-right, high)
          A.volume = clampf((52 - a) / 104.0f, 0, 1);
          A.sound.set(A.sound.kind(), A.volume);
        }
        lookUntil_ = t_ + 1.0f;
        lookX_ = A.dial == 0 ? -0.9f : 0.9f;
        lookY_ = (y - 233) / 200.0f;
        invalidate();
        return true;
      }
      if (A.rimArmed && !A.rimDrag && hypotf(x - A.downX, y - A.downY) > 7) A.rimDrag = true;
      if (A.rimDrag && view_ == View::Maps) {
        const float a = angleOf(x, y, 233, 233);
        float d = a - A.rimA;
        while (d > 3.14159f) d -= 6.28318f;
        while (d < -3.14159f) d += 6.28318f;
        A.rimA = a;
        A.view.zoomBy(expf(d * 1.3f));  // clockwise = in
        A.followMe = false;
        A.mapDirty = true;
        invalidate();
        return true;
      }
      if (view_ == View::Maps && !A.sendSheet && !A.rimArmed) {
        if (!A.dragging && hypotf(x - A.downX, y - A.downY) > 9 && A.downY > 70) A.dragging = true;
        if (A.dragging) {
          A.view.pan(dx * k, dy * k);
          A.followMe = false;
          A.mapDirty = true;
          invalidate();
        }
      }
      A.dragX = x;
      A.dragY = y;
      return true;
    }
    case Ev::TouchUp: {
      const float dist = hypotf(x - A.downX, y - A.downY), dur = t_ - A.downT;
      const bool wasDrag = A.dragging || A.rimDrag;
      A.dragging = false;
      A.rimDrag = A.rimArmed = false;
      A.dial = -1;
      if (wasDrag) {  // a rim dial or the map moved: never also a "back"
        if (view_ == View::Maps) mapsAskView(false);
        else pushCmd(OsCmd::SaveSettings);
        return true;
      }
      if (A.downY < 80 && y - A.downY > 80 && dur < 0.8f) {  // from the top edge, down: back
        back();
        return true;
      }
      if (view_ == View::Control && A.downY > 330 && A.downY - y > 80) {  // Control: push it back up
        back();
        return true;
      }
      if (dist < 24 && dur < 0.45f) {
        if (t_ - lastTapT_ < 0.38f && hypotf(e.x - lastTapX_, e.y - lastTapY_) < g_.s(50) && view_ == View::Maps) {
          lastTapT_ = -10;
          A.view.zoomBy(2.0f);  // double tap: in
          A.followMe = false;
          A.mapDirty = true;
          mapsAskView(false);
          invalidate();
          return true;
        }
        lastTapT_ = t_;
        lastTapX_ = e.x;
        lastTapY_ = e.y;
        const int id = hitItem(e.x, e.y);
        if (id >= 0) activate(id);
        else if (view_ == View::Maps && A.navOn && y < 200) {  // the step card: "I'm at the turn"
          A.nav.next();
          face_.react(X_happy, 0.5f);
          invalidate();
        }
      }
      return true;
    }
    default: return true;
  }
}

bool Os::appsSwipe(int dir) {
  AppsState& A = apps_;
  switch (view_) {
    case View::Home:
      if (dir == 3) {  // pull down from the eyes: Control
        go(View::Control);
        face_.react(X_happy, 0.6f);
        return true;
      }
      return false;
    case View::Today: {
      const int n = 6;
      if (dir == 2) {
        if (A.card < n - 1) ++A.card;
        invalidate();
        return true;
      }
      if (dir == 3) {
        if (A.card > 0) {
          --A.card;
          invalidate();
        } else {
          back();
        }
        return true;
      }
      return false;
    }
    case View::Weather:
      if (dir == 0 || dir == 1) {
        A.wxPage = 1 - A.wxPage;
        lookUntil_ = t_ + 0.8f;
        lookX_ = dir == 0 ? 0.8f : -0.8f;
        lookY_ = -0.3f;
        invalidate();
        return true;
      }
      if (dir == 1 || dir == 3) back();
      return dir == 3;
    case View::Calendar:
      if (dir == 2) {
        ++A.calPage;
        A.calSel = -1;
        invalidate();
        return true;
      }
      if (dir == 3 && A.calSel >= 0) {
        A.calSel = -1;
        invalidate();
        return true;
      }
      return false;
    case View::Music:
      if (dir == 0 || dir == 1) {
        const int k = ((int)A.sound.kind() + (dir == 0 ? 1 : SoundGen::Count - 1)) % SoundGen::Count;
        A.sound.set((SoundGen::Kind)k, A.volume);
        pushCmd(OsCmd::SaveApps);
        invalidate();
        return true;
      }
      return false;
    case View::Breathe:
      if ((dir == 0 || dir == 1) && !A.breathing) {
        const int n = (int)apps::breathPatterns().size();
        A.breathPat = (A.breathPat + (dir == 0 ? 1 : n - 1)) % n;
        pushCmd(OsCmd::SaveApps);
        invalidate();
        return true;
      }
      return false;
    case View::Habits:
      if (dir == 2) {
        ++A.habitPage;
        invalidate();
        return true;
      }
      return false;
    case View::AppsSettings:
      if (dir == 2) {
        ++A.setPage;
        invalidate();
        return true;
      }
      return false;
    case View::Games:
      if (A.game >= 0 && (dir == 3 || dir == 1)) {  // a game: back to the menu first
        A.game = -1;
        invalidate();
        return true;
      }
      return false;
    default: return false;
  }
}

bool Os::appsHold(float x, float y) {
  AppsState& A = apps_;
  const int id = hitItem(x, y);
  switch (view_) {
    case View::Habits:
    case View::WorldClock:
      if (id >= ARow) {
        holdItem_ = id;
        holdItemT_ = 0;
        invalidate();
      }
      return true;
    case View::Maps:
      if (A.navOn) {  // hold on the map while walking: end the route
        A.navOn = false;
        A.nav.stop();
        if (cloudUsable(net_)) fetch(Fetch::RouteEnd, "/v1/device/maps/route/end", "{}", true);
        toast(tr("Route ended", "Traseu oprit"), kAmber, 2.0f);
        A.mapDirty = true;
        invalidate();
      }
      return true;
    case View::Control:
    case View::Weather:
    case View::Calendar:
    case View::Music:
    case View::Games:
    case View::Focus:
    case View::Breathe:
    case View::Stopwatch:
    case View::Convert:
    case View::FindPhone:
    case View::Device:
    case View::AppsSettings:
    case View::Today: return true;  // a hold here is nothing (it never starts talking by accident)
    default: return false;
  }
}

bool Os::appsTap(float x, float y) {
  AppsState& A = apps_;
  const float k = g_.k(), dx = x / k - 233, dy = y / k - 233;
  switch (view_) {
    case View::Answer: {
      if (thinking_ || acceptMode_ || cardHidden_ || cardTitle_.empty() || !net_.paired) return false;
      const int id = hitItem(x, y);
      if (id < AReply || id >= AReply + 4) return false;
      const int r = id - AReply;
      if (r == 3) {  // type a reply
        openKeyboard(KbReply);
        return true;
      }
      static const char* const en[] = {"OK", "On my way", "Later"};
      static const char* const ro[] = {"OK", "Vin acum", "Mai târziu"};
      CloudOut o;
      o.kind = CloudOut::Inbox;
      o.text = "Re: " + cardTitle_ + " \xE2\x80\x94 " + (this->ro() ? ro[r] : en[r]);
      o.created = now_;
      outs_.push_back(o);
      A.replied = r;
      face_.react(X_wink, 1.0f);
      toast(tr("Sent: ", "Trimis: ") + (this->ro() ? ro[r] : en[r]), kMint, 2.4f);
      back();
      return true;
    }
    case View::Today: {
      // a tap on the card opens its app
      static const AppId kCards[] = {AppId::Alarms, AppId::Weather, AppId::Calendar, AppId::Focus, AppId::Habits, AppId::Device};
      if (fabsf(dy) < 110) openApp(kCards[A.card % 6]);
      return true;
    }
    case View::Games:
      if (A.game == 1 && A.rhythm.running()) {
        const games::Rhythm::Judge j = A.rhythm.tap();
        if (j != games::Rhythm::NoBeat) {
          A.judgeT = 0.5f;
          if (j == games::Rhythm::Perfect) face_.react(X_happy, 0.3f);
        }
        return true;
      }
      if (A.game == 2 && A.memory.phase() == games::EyeMemory::Phase::Input) {
        const int s = games::EyeMemory::spotAt(dx, dy);
        A.lastTap = s;
        A.tapGlow = 0.3f;
        const int before = A.memory.round();
        if (!A.memory.input(s)) {
          face_.react(X_shocked, 1.0f);
          face_.flash(kAmber, 1.0f);
        } else if (A.memory.round() > before) {
          face_.react(X_happy, 0.8f);
        }
        invalidate();
        return true;
      }
      return false;
    case View::Breathe: {
      const int id = hitItem(x, y);
      if (id >= 0) return false;
      A.breathing = !A.breathing;
      A.breathT = 0;
      A.breathCycles = 0;
      invalidate();
      return true;
    }
    case View::Calendar:
      if (A.calSel >= 0) {
        A.calSel = -1;
        invalidate();
        return true;
      }
      return false;
    case View::Weather:
      if (hitItem(x, y) < 0) {
        A.wxPage = 1 - A.wxPage;
        invalidate();
        return true;
      }
      return false;
    default: return false;
  }
}

bool Os::appsBack() {
  AppsState& A = apps_;
  switch (view_) {
    case View::Maps:
      if (A.sendSheet) {
        A.sendSheet = false;
        invalidate();
        return true;
      }
      if (A.preview) {  // a planned route not started: drop it, back to the map
        A.preview = false;
        A.followMe = true;
        if (A.haveFix) A.view.centerOn(A.fix.lat, A.fix.lon);
        A.mapDirty = true;
        mapsAskView(false);
        invalidate();
        return true;
      }
      go(View::Home);
      return true;
    case View::Games:
      if (A.game >= 0) {
        A.game = -1;
        invalidate();
        return true;
      }
      go(View::Home);
      return true;
    case View::Calendar:
      if (A.calSel >= 0) {
        A.calSel = -1;
        invalidate();
        return true;
      }
      go(View::Home);
      return true;
    case View::AppsSettings: go(View::Settings); return true;
    case View::Control:
    case View::Weather:
    case View::Music:
    case View::Focus:
    case View::Breathe:
    case View::Habits:
    case View::Stopwatch:
    case View::WorldClock:
    case View::Convert:
    case View::FindPhone:
    case View::Device:
      A.breathing = view_ == View::Breathe ? false : A.breathing;
      go(View::Home);
      return true;
    case View::Today:
      A.card = 0;
      go(View::Home);
      return true;
    default: return false;
  }
}

// ---------------------------------------------------------------- actions ---

void Os::appsActivate(int id) {
  AppsState& A = apps_;
  switch (view_) {
    case View::Control:
      if (id == ATile) {
        A.dnd = !A.dnd;
        toast(A.dnd ? tr("Quiet: notes wait in Today", "Liniște: notificările așteaptă în Azi")
                    : tr("Quiet off", "Liniște oprită"), A.dnd ? kAmber : kMint, 2.4f);
        pushCmd(OsCmd::SaveApps);
      } else if (id == ATile + 1) {
        set_.largeText = !set_.largeText;
        pushCmd(OsCmd::SaveSettings);
      } else if (id == ATile + 2) {
        openApp(AppId::FindPhone);
        activate(ARing);
      } else if (id == ATile + 3) {  // sleep now: the eyes close
        go(View::Home);
        brainEvents_.push_back(Ev::FaceDown);
        face_.react(X_sleepy, 1.6f);
      } else if (id == AAi) {
        go(View::AiMode);
      } else if (id == AAuto) {
        set_.bright = 0;
        pushCmd(OsCmd::SaveSettings);
      }
      return;
    case View::Weather:
    case View::Calendar:
      if (view_ == View::Calendar && id >= ARow && id - ARow < (int)A.agenda.events.size()) {
        A.calSel = id - ARow;  // the event's card
        return;
      }
      if (id == ARetry) {
        if (view_ == View::Weather) A.wxAsked = -100, A.weather.at = 0;
        else A.calAsked = -100, A.agenda.at = 0;
        appOpened(view_);
      }
      return;
    case View::Maps:
      switch (id) {
        case AGo: openKeyboard(KbWhereTo); return;
        case APlus:
          A.view.zoomBy(2.0f);
          A.followMe = false;
          A.mapDirty = true;
          mapsAskView(false);
          return;
        case AMinus:
          A.view.zoomBy(0.5f);
          A.followMe = false;
          A.mapDirty = true;
          mapsAskView(false);
          return;
        case ACenter:
          A.followMe = true;
          if (A.haveFix) A.view.centerOn(A.fix.lat, A.fix.lon);
          A.mapDirty = true;
          mapsAskView(false);
          if (cloudUsable(net_)) {
            A.whereAsked = t_;
            fetch(Fetch::Where, "/v1/device/maps/where");
          }
          return;
        case AWifi:
          fetch(Fetch::WifiLocate, "/v1/device/maps/wifi", "", true);
          A.whereWait = true;
          toast(tr("Asking the Wi-Fi around me…", "Întreb Wi-Fi-urile din jur…"), kIce, 2.0f);
          return;
        case AStartNav: navStart(); return;
        case AMode: {
          A.routeMode = A.routeMode == "walk" ? "bike" : A.routeMode == "bike" ? "car" : "walk";
          if (!A.dest.empty() && cloudUsable(net_)) {
            JsonDocument d;
            d["to"] = A.dest;
            d["mode"] = A.routeMode;
            std::string b;
            serializeJson(d, b);
            A.routeWait = true;
            fetch(Fetch::RoutePlan, "/v1/device/maps/route", b, true);
          }
          return;
        }
        case APhone: {
          // the QR opens Google Maps on the phone (no account, no app needed); the cloud also puts it on /me/where
          char u[200];
          const char* m = A.route.mode == "car" ? "driving" : A.route.mode == "bike" ? "bicycling" : "walking";
          snprintf(u, sizeof u, "https://www.google.com/maps/dir/?api=1&destination=%.6f,%.6f&travelmode=%s", A.route.destLat,
                   A.route.destLon, m);
          A.sendUrl = u;
          A.sendSheet = true;
          if (cloudUsable(net_)) fetch(Fetch::RouteSend, "/v1/device/maps/send", "{}", true);
          invalidate();
          return;
        }
        case AEnd:
          A.navOn = false;
          A.preview = false;
          A.nav.stop();
          A.followMe = true;
          if (cloudUsable(net_)) fetch(Fetch::RouteEnd, "/v1/device/maps/route/end", "{}", true);
          A.mapDirty = true;
          return;
        case ANext: A.nav.next(); return;
        case APrev: A.nav.prev(); return;
        case AClose: A.sendSheet = false; return;
        default: return;
      }
    case View::Music:
      if (id == AStart) {
        if (!A.speaker) {
          toast(tr("This SOUL has no speaker", "SOUL-ul ăsta n-are difuzor"), kAmber, 3.0f);
          return;
        }
        A.playing = !A.playing;
        face_.react(A.playing ? X_love : X_bored, 1.0f);
      } else if (id == ANext || id == APrev) {
        const int k = ((int)A.sound.kind() + (id == ANext ? 1 : SoundGen::Count - 1)) % SoundGen::Count;
        A.sound.set((SoundGen::Kind)k, A.volume);
        pushCmd(OsCmd::SaveApps);
      } else if (id == ASleepT) {
        A.sleepMin = A.sleepMin == 0 ? 15 : A.sleepMin == 15 ? 30 : A.sleepMin == 30 ? 60 : 0;
        A.sleepLeft = A.sleepMin * 60.0f;
      }
      return;
    case View::Games:
      if (id >= AGame && id < AGame + 3) {
        A.game = id - AGame;
        A.newBest = false;
        A.cueGlow = 0;
        A.seed = A.seed * 1664525u + 1013904223u + now_;
        if (A.game == 0) A.tilt.start(A.seed);
        else if (A.game == 1) A.rhythm.start(A.seed);
        else A.memory.start(A.seed);
        face_.react(X_excited, 0.8f);
      } else if (id == AAgain) {
        activate(AGame + A.game);
      } else if (id == AMenu) {
        A.game = -1;
      }
      return;
    case View::Focus:
      if (id == AStart) {
        if (A.pomo.phase() == apps::Pomodoro::Phase::Idle) {
          A.pomo.start();
          face_.react(X_wake, 1.0f);
        } else {
          A.pomo.pause(!A.pomo.paused());
        }
      } else if (id == ASkip) {
        A.pomo.tick(A.pomo.left() + 0.01f);
      } else if (id == AStop) {
        A.pomo.stop();
      }
      return;
    case View::Breathe:
      if (id == APattern) {
        A.breathPat = (A.breathPat + 1) % (int)apps::breathPatterns().size();
        pushCmd(OsCmd::SaveApps);
      } else if (id == ADur) {
        A.breathMin = A.breathMin == 1 ? 2 : A.breathMin == 2 ? 5 : 1;
      }
      return;
    case View::Habits:
      if (id == ANew) {
        if (A.habits.size() >= 6) {
          toast(tr("6 habits is the limit", "Maximum 6 obiceiuri"), kAmber);
          return;
        }
        openKeyboard(KbHabitNew);
      } else if (id >= ARow && id - ARow < (int)A.habits.size()) {
        const uint32_t today = now_ / 86400;
        apps::Habit& h = A.habits[id - ARow];
        h.toggle(today);
        if (h.doneOn(today)) {
          face_.react(h.streak(today) >= 3 ? X_excited : X_approve, 1.0f);
          face_.flash(kMint, 1.0f);
        }
        pushCmd(OsCmd::SaveApps);
      }
      return;
    case View::Stopwatch:
      if (id == AStart) A.sw.toggle();
      else if (id == ALap) {
        if (A.sw.run) A.sw.lap();
        else A.sw.reset();
      }
      return;
    case View::WorldClock:
      if (id == ANew) {
        if (A.clocks.size() >= 4) {
          toast(tr("4 cities fit", "Încap 4 orașe"), kAmber);
          return;
        }
        A.clocks.push_back((uint8_t)((A.clocks.empty() ? 0 : A.clocks.back() + 1) % apps::cities().size()));
        pushCmd(OsCmd::SaveApps);
      } else if (id >= ARow && id - ARow < (int)A.clocks.size()) {  // a tap: the next city
        uint8_t& c = A.clocks[id - ARow];
        c = (uint8_t)((c + 1) % apps::cities().size());
        pushCmd(OsCmd::SaveApps);
      }
      return;
    case View::Convert: {
      const int n = (int)apps::units((apps::Quantity)A.q).size();
      if (id == AQty) {
        A.q = (A.q + 1) % (int)apps::Quantity::Count;
        A.from = 0;
        A.to = 1;
      } else if (id == AFrom) {
        A.from = (A.from + 1) % n;
        if (A.from == A.to) A.from = (A.from + 1) % n;
      } else if (id == ATo) {
        A.to = (A.to + 1) % n;
        if (A.to == A.from) A.to = (A.to + 1) % n;
      } else if (id == ASwap) {
        const int t = A.from;
        A.from = A.to;
        A.to = t;
      } else if (id == AValue) {
        openKeyboard(KbConvert);
        return;
      }
      pushCmd(OsCmd::SaveApps);
      return;
    }
    case View::FindPhone:
      if (id == ARing) {
        if (!cloudUsable(net_)) {
          toast(net_.relay ? tr("Pair me with your account first", "Leagă-mă întâi de cont")
                           : tr("Needs SOUL Cloud", "Are nevoie de SOUL Cloud"),
                kAmber, 3.0f);
          A.findState = 5;
          return;
        }
        A.findState = 1;
        A.findT = t_;
        fetch(Fetch::FindPhone, "/v1/device/apps/findphone", "{}", true);
        face_.react(X_suspicious, 2.0f);
      }
      return;
    case View::AppsSettings: {
      const int n = (int)A.order.size();
      if (id >= ARow && id < ARow + n) {
        const uint8_t a = A.order[id - ARow];
        if ((AppId)a == AppId::Settings) {
          toast(tr("Settings always stays", "Setările rămân mereu"), kAmber);
          return;
        }
        A.hidden ^= 1u << a;
        if (visibleApps() < 1) A.hidden ^= 1u << a;
        orbit_ = 0;
        pushCmd(OsCmd::SaveApps);
      } else if (id >= AUp && id < AUp + n && id - AUp > 0) {
        const int i = id - AUp;
        const uint8_t t = A.order[i - 1];
        A.order[i - 1] = A.order[i];
        A.order[i] = t;
        orbit_ = 0;
        pushCmd(OsCmd::SaveApps);
      }
      return;
    }
    default: return;
  }
}

void Os::appsKbConfig(int ctx, KbConfig& c) const {
  switch (ctx) {
    case KbWhereTo:
      c.action = KbAction::Send;
      c.maxChars = 120;
      c.placeholder = ro() ? "Unde mergem?" : "Where to?";
      c.chips[0] = ro() ? "Cafenea" : "Coffee";
      c.chips[1] = ro() ? "Farmacie" : "Pharmacy";
      c.chips[2] = ro() ? "Acasă" : "Home";
      break;
    case KbHabitNew:
      c.maxChars = 32;
      c.placeholder = ro() ? "Obicei nou…" : "New habit…";
      c.chips[0] = ro() ? "Meditație" : "Meditate";
      c.chips[1] = ro() ? "Fără ecrane la 22" : "No screens at 10pm";
      c.chips[2] = ro() ? "Sport" : "Exercise";
      break;
    case KbConvert:
      c.maxChars = 14;
      c.placeholder = "0";
      c.verbatim = true;
      break;
    case KbReply:
      c.action = KbAction::Send;
      c.maxChars = 200;
      c.placeholder = ro() ? "Răspunsul tău…" : "Your reply…";
      break;
    default: break;
  }
}

bool Os::appsKbCommit(int ctx, const std::string& text) {
  AppsState& A = apps_;
  switch (ctx) {
    case KbWhereTo:
      if (text.empty()) return true;
      A.dest = text;
      if (!cloudUsable(net_)) {
        toast(tr("Routes need SOUL Cloud (Settings › AI)", "Traseele au nevoie de SOUL Cloud (Setări › AI)"), kAmber, 4.0f);
        return true;
      }
      if (!A.haveFix) {
        toast(tr("Share your location first: /me/where", "Trimite-ți întâi locația: /me/where"), kAmber, 4.0f);
        return true;
      }
      {
        JsonDocument d;
        d["to"] = text;
        d["mode"] = A.routeMode;
        std::string b;
        serializeJson(d, b);
        A.routeWait = true;
        fetch(Fetch::RoutePlan, "/v1/device/maps/route", b, true);
      }
      face_.react(X_suspicious, 1.4f);
      return true;
    case KbHabitNew:
      if (!text.empty() && A.habits.size() < 6) {
        apps::Habit h;
        h.name = text.substr(0, 32);
        h.day = now_ / 86400;
        A.habits.push_back(h);
        pushCmd(OsCmd::SaveApps);
        face_.react(X_approve);
      }
      return true;
    case KbConvert: {
      std::string t;
      for (char c : text) t += c == ',' ? '.' : c;
      char* end = nullptr;
      const double v = strtod(t.c_str(), &end);
      if (end && end != t.c_str()) A.value = v;
      else toast(tr("That's not a number", "Nu e un număr"), kAmber);
      return true;
    }
    case KbReply:
      if (!text.empty()) {
        CloudOut o;
        o.kind = CloudOut::Inbox;
        o.text = "Re: " + cardTitle_ + " \xE2\x80\x94 " + text;
        o.created = now_;
        outs_.push_back(o);
        toast(tr("Sent to your Claude", "Trimis lui Claude"), kMint, 2.4f);
        cardTitle_.clear();
        view_ = View::Home;
      }
      return true;
    default: return false;
  }
}

void Os::appsHoldDone(int id) {
  AppsState& A = apps_;
  if (view_ == View::Habits && id >= ARow && id - ARow < (int)A.habits.size()) {
    A.habits.erase(A.habits.begin() + (id - ARow));
    pushCmd(OsCmd::SaveApps);
    toast(tr("Habit removed", "Obicei șters"), kAmber);
  } else if (view_ == View::WorldClock && id >= ARow && id - ARow < (int)A.clocks.size()) {
    A.clocks.erase(A.clocks.begin() + (id - ARow));
    pushCmd(OsCmd::SaveApps);
  }
}

// ------------------------------------------------------- screen behaviour ---

bool Os::appsIdleReturns(bool& out) const {
  const AppsState& A = apps_;
  switch (view_) {
    case View::Maps: out = !A.navOn && !A.preview && !A.dragging; return true;
    case View::Games: out = A.game < 0; return true;
    case View::Breathe: out = !A.breathing; return true;
    case View::Stopwatch: out = !A.sw.run; return true;
    case View::Focus: out = A.pomo.phase() == apps::Pomodoro::Phase::Idle; return true;
    case View::Music: out = !A.playing; return true;
    case View::FindPhone: out = A.findState != 1 && A.findState != 2; return true;
    case View::Control:
    case View::Weather:
    case View::Calendar:
    case View::Habits:
    case View::WorldClock:
    case View::Convert:
    case View::Device:
    case View::AppsSettings: out = holdItem_ < 0; return true;
    default: return false;
  }
}

bool Os::appsFaceMoment(bool& out) const {
  switch (view_) {
    case View::Breathe: out = true; return true;  // the eyes breathe: pure black behind them
    case View::Games: out = apps_.game == 1 || apps_.game == 2; return true;  // rhythm and memory: the eyes play
    default: return false;
  }
}

bool Os::appsLayout(View v, FaceLayoutT& l) const {
  const AppsState& A = apps_;
  switch (v) {
    case View::Control: l = {0.2f, 0, -0.33f}; return true;
    case View::Maps: l = A.navOn ? FaceLayoutT{0.13f, 0, -0.415f} : FaceLayoutT{0.14f, 0, -0.41f}; return true;
    case View::Weather: l = {0.22f, 0, -0.37f}; return true;
    case View::Today: l = {0.2f, 0, -0.34f}; return true;
    case View::Calendar:
    case View::Habits:
    case View::WorldClock:
    case View::AppsSettings: l = {0.18f, 0, -0.335f}; return true;
    case View::Convert: l = {0.22f, 0, -0.37f}; return true;
    case View::Stopwatch: l = {0.24f, 0, -0.35f}; return true;
    case View::Focus: l = {0.3f, 0, -0.27f}; return true;
    case View::Music: l = {0.3f, 0, -0.3f}; return true;
    case View::FindPhone: l = {0.26f, 0, -0.31f}; return true;
    case View::Device: l = {0.22f, 0, -0.37f}; return true;
    case View::Breathe: {
      const apps::BreathPoint b = apps::breathAt(apps::breathPatterns()[A.breathPat], A.breathT);
      const float s = A.breathing ? b.size : 0.35f;
      l = {0.42f + 0.3f * s, 0, -0.04f};
      return true;
    }
    case View::Games:
      if ((A.game == 0 && A.tilt.over()) || (A.game == 1 && A.rhythm.over()) ||
          (A.game == 2 && A.memory.phase() == games::EyeMemory::Phase::Over))
        l = {0.22f, 0, -0.36f};  // the score card has the middle
      else if (A.game == 2) l = {0.5f, 0, 0};
      else if (A.game == 1) l = {0.34f, 0, 0};
      else if (A.game == 0) l = {0.12f, 0, -0.42f};
      else l = {0.24f, 0, -0.36f};
      return true;
    default: return false;
  }
}

void Os::appsFace(FaceInputs& in) const {
  const AppsState& A = apps_;
  switch (view_) {
    case View::Games:
      if (A.game == 0 && A.tilt.running()) {  // the eyes follow the marble
        in.look = true;
        in.lookX = A.tilt.x() / 160.0f;
        in.lookY = A.tilt.y() / 160.0f;
      } else if (A.game == 2) {
        const int c = A.memory.cue();
        if (c >= 0) {
          static const float kx[] = {0, 1, 0, -1}, ky[] = {-1, 0, 1, 0};
          in.look = true;
          in.lookX = kx[c];
          in.lookY = ky[c];
        } else if (A.memory.phase() == games::EyeMemory::Phase::Input) {
          in.look = true;  // your turn: they look at you
          in.lookX = 0;
          in.lookY = 0;
        }
      }
      break;
    case View::Maps:
      if (A.navOn && A.route.valid()) {  // the eyes glance the way of the next turn
        const float ang = A.route.turnAngle(A.nav.step());
        in.look = true;
        in.lookX = clampf(ang / 90.0f, -1, 1) * 0.8f;
        in.lookY = -0.2f;
      }
      if (A.whereWait || A.routeWait) in.state = FaceState::Think;
      break;
    case View::Weather:
    case View::Calendar:
      if ((view_ == View::Weather && A.wxWait) || (view_ == View::Calendar && A.calWait)) in.state = FaceState::Think;
      break;
    case View::FindPhone:
      if (A.findState == 1 || A.findState == 2) {  // looking around for the phone
        in.look = true;
        in.lookX = 0.8f * sinf(t_ * 2.2f);
        in.lookY = 0.2f * cosf(t_ * 1.7f);
      }
      break;
    case View::Breathe:
      if (A.breathing) {
        const apps::BreathPoint b = apps::breathAt(apps::breathPatterns()[A.breathPat], A.breathT);
        in.look = true;
        in.lookX = 0;
        in.lookY = b.phase == 0 ? -0.3f * b.progress : b.phase == 2 ? -0.3f * (1 - b.progress) : (b.phase == 1 ? -0.3f : 0);
      }
      break;
    default: break;
  }
}

}  // namespace suflet
