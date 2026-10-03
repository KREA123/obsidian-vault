// SoulOS apps on the device (os/APPS.md): the state of the app suite that
// Os owns (Os::apps_), the launcher's app list, and the requests the apps
// make to SOUL Cloud. The screens live in OsApps.cpp (logic) and
// OsAppsDraw.cpp (drawing), as Os member functions.
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

#include "AppKit.h"
#include "Games.h"
#include "MapCore.h"
#include "SoundGen.h"

namespace suflet {

// Everything the launcher (the orbit) can open. The order here is the factory order of the orbit; Settings ›
// Apps reorders and hides them (saved in the apps blob).
enum class AppId : uint8_t {
  Talk, Today, Maps, Weather, Calendar, Alarms, Timer, Stopwatch, Focus, Breathe, Habits, Notes, Music, Games,
  WorldClock, Convert, FindPhone, Claude, Device, MySoul, Settings, Count
};

// What an app asks SOUL Cloud for (docs/11-MAPS.md §5, ai/suflet_ai/apps_routes.py). The device services it
// over HTTPS with the device token (src/cloud.cpp) and gives the answer back through Os::appData().
enum class Fetch : uint8_t {
  None, Weather, Agenda, Rates, Where, MapView, RoutePlan, RouteGet, RouteEnd, RouteSend, FindPhone, WifiLocate, Count
};
const char* fetchName(Fetch f);

struct AppFetch {
  Fetch kind = Fetch::None;
  bool post = false, del = false;
  std::string path;  // "/v1/device/apps/weather"
  std::string body;  // JSON (POST); WifiLocate: the device fills in the scan
};

// what the device knows about its storage (the Device app)
struct StorageInfo {
  uint32_t flashKb = 0, appKb = 0, appMaxKb = 0, nvsUsed = 0, nvsTotal = 0, heapKb = 0, psramKb = 0, psramTotalKb = 0;
  std::string fw = "1.7.0", board;
  int rssi = 0;
};

struct AppsState {
  // ---- the launcher -------------------------------------------------------
  std::vector<uint8_t> order;  // AppId values, all of them, in orbit order
  uint32_t hidden = 0;         // bit per AppId
  int setPage = 0;             // Settings › Apps page
  AppId last = AppId::Talk;    // the app opened last (the orbit opens on it)
  // ---- control ------------------------------------------------------------
  bool dnd = false;
  float volume = 0.7f;
  int dial = -1;  // the rim dial being dragged: 0 brightness, 1 volume
  // ---- today stack --------------------------------------------------------
  int card = 0;
  // ---- cloud data ---------------------------------------------------------
  apps::Weather weather;
  apps::Agenda agenda;
  apps::Rates rates;
  int wxPage = 0, calSel = -1, calPage = 0;
  int wxErr = 0, calErr = 0, mapErr = 0;  // HTTP status of the last failure (409 no location, 404, 501 not set up, -1 offline)
  std::string calErrCode, mapErrCode, mapErrMsg;
  float wxAsked = -100, calAsked = -100, whereAsked = -100, ratesAsked = -1e9f, viewAsked = -100;
  bool wxWait = false, calWait = false, whereWait = false, viewWait = false, routeWait = false;
  // ---- maps ---------------------------------------------------------------
  maps::MapBundle bundle;
  maps::MapView view;
  maps::RouteData route;
  maps::NavState nav;
  bool haveFix = false, followMe = true, navOn = false, preview = false, sendSheet = false;
  maps::NavFix fix;
  std::string fixSrc, fixLabel;
  uint32_t fixAge = 0;          // seconds old when it came
  uint32_t mapAt = 0;           // when the bundle came (local epoch)
  std::string dest, sendUrl;    // what was asked for; the Google Maps link (QR)
  std::string routeMode = "walk";
  bool mapDirty = true;         // the cached map layer must be repainted
  int viewZ = 0;                // the zoom of the bundle being fetched
  double viewLat = 0, viewLon = 0;
  float rimA = 0;               // rim zoom: the angle at the last move
  bool dragging = false, rimDrag = false, rimArmed = false;  // a touch on the rim zooms once it moves
  float dragX = 0, dragY = 0, downX = 0, downY = 0, downT = 0;
  bool arrivedShown = false;
  float navAsked = -100;
  // ---- music --------------------------------------------------------------
  SoundGen sound;
  bool playing = false;
  int sleepMin = 0;
  float sleepLeft = 0;
  bool speaker = false, mic = false;
  // ---- games --------------------------------------------------------------
  int game = -1;  // -1 menu, 0 tilt, 1 rhythm, 2 memory
  games::TiltBall tilt;
  games::Rhythm rhythm;
  games::EyeMemory memory;
  int best[3] = {0, 0, 0};
  bool newBest = false;
  float judgeT = 0, cueGlow = 0;
  int lastTap = -1;
  float tapGlow = 0;
  uint32_t seed = 1;
  // ---- focus / breathe / stopwatch ----------------------------------------
  apps::Pomodoro pomo;
  int breathPat = 0, breathMin = 2;
  bool breathing = false;
  float breathT = 0;
  int breathCycles = 0;
  apps::Stopwatch sw;
  // ---- habits -------------------------------------------------------------
  std::vector<apps::Habit> habits;
  int habitPage = 0;
  // ---- world clock --------------------------------------------------------
  std::vector<uint8_t> clocks;  // indexes into apps::cities()
  std::string tz = "EET-2EEST,M3.5.0/3,M10.5.0/4";
  // ---- convert ------------------------------------------------------------
  int q = 0, from = 0, to = 1;
  double value = 1;
  // ---- find my phone / device --------------------------------------------
  int findState = 0;  // 0 idle, 1 asking, 2 ringing on a page, 3 push only, 4 nobody listening, 5 error
  float findT = 0;
  StorageInfo storage;
  // ---- quick replies ------------------------------------------------------
  int replied = -1;
  // ---- requests -----------------------------------------------------------
  std::vector<AppFetch> fetches;
};

}  // namespace suflet
