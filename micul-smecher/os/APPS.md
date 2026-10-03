# SoulOS apps

The app suite of SoulOS, the same on the web prototype (`os/index.html` = `site/os.html`, `window.SoulApps`) and on
the device (firmware 1.7.0: `firmware/lib/Suflet/src/OsApps.cpp` logic, `OsAppsDraw.cpp` drawing, `AppKit`, `Games`,
`MapCore`, `SoundGen`). Design rules: `DESIGN-GLASS.md` — the eyes always sit on pure black; glass screens with the
aura only where the eyes are not the subject; standby is the eyes alone. Maps in depth: `../docs/11-MAPS.md`.

Pictures: `screenshots/apps/soulos-apps-sheet-web.png` (web, 28 screens) and
`../firmware/sim/shots/apps/soulos-apps-sheet-device.png` (the firmware's own pixels, 31 screens).

## 1 · Getting around (the same everywhere)

| Gesture | Does |
|---|---|
| Swipe → on the face | the orbit (launcher), opened on the last app; Maps and Weather sit next to Talk: **two gestures** to the top apps |
| Turn the orbit (drag / crown / arrows), tap the word | open the app (it grows out of the eyes) |
| Swipe ↑ on the face | Today: a stack of cards (now, weather, next event, focus / timer / reminder, habits); tap opens the app |
| Swipe ↓ on the face | Control: quiet, large text, find phone, sleep; the left rim = brightness, the right rim = volume |
| Side button, or swipe ↓ inside an app | back one level (a sheet or a game closes first, then the app) |
| Pull down from the top edge | back, where the middle of the screen is a map or a game |
| Leave it alone 15 s | back to the eyes alone — not while navigating, breathing, playing, timing, playing sounds or ringing the phone |
| Settings › Apps | reorder the orbit (↑) and hide apps; Settings itself can't be hidden; kept on the device (NVS) / in the browser |

## 2 · The apps

| App | What it does | Data from | Real / demo |
|---|---|---|---|
| **Talk / Claude** | the AI; the answer offers **quick replies** (OK · On my way · Later · Type…) to a message | your AI | existing |
| **Today** | the card stack above | on SOUL + cloud | real |
| **Control** | toggles + rim dials | on SOUL | real |
| **Maps** | where am I (phone / Wi-Fi), the dark glass map, pan, rim zoom, *Where to?*, route preview, step card, *Send to phone* (QR), end | SOUL Cloud: location book, PMTiles, Photon, Valhalla/ORS/OSRM | code real + tested; providers not deployed; maps in the demo are a synthetic city (not OSM) |
| **Weather** | now, 12 hours, 3 days, place | SOUL Cloud → Open-Meteo, cached 30 min per ~5 km | real code; mocked in tests; the web shows demo days |
| **Calendar** | the next 7 days, tap = the event | an ICS link pasted on `/me/where` (Google / iCloud / Outlook "secret address"), parsed by the cloud (RRULE, EXDATE, all-day, time zones) | real code; fixture agenda in sim/web |
| **Alarms, Timer, Reminders, Notes** | as before | on SOUL | existing |
| **Stopwatch** | laps; on the web it is the Timer's stopwatch tab | on SOUL | real |
| **Focus** | Pomodoro 25/5 with long breaks | on SOUL | real |
| **Breathe** | the eyes grow and shrink with the breath (Calm 4-6, Box, 4-7-8, Coherent 5.5) on pure black | on SOUL | real |
| **Habits** | up to 6, tap = done today, 7-day dots, streaks | on SOUL (NVS) / browser | real |
| **Music** | **focus sounds made on SOUL** (rain, brown noise, ocean, fire) on the I2S speaker, sleep timer | on SOUL | real; now-playing for the phone (Apple Media Service over BLE) is future work |
| **Games** | Catch the star (web), **Tilt ball** (gyro; drag on the web), **Rhythm** (tap as the rings hit the rim), **Eye memory** (repeat where the eyes look); bests kept | on SOUL | real |
| **World clock** | up to 4 of 16 cities, day offset, summer time from POSIX TZ rules | on SOUL | real |
| **Convert** | length, weight, temperature, volume, speed offline; currency with the **ECB reference rates** via the cloud (built-in approximate table until then) | on SOUL + cloud | real |
| **Find my phone** | rings `/me/where` if it is open on the phone (even on silent), or says no one is listening | SOUL Cloud | real code; web is simulated |
| **Device** | battery, firmware, flash / NVS / heap / PSRAM, Wi-Fi | on SOUL | real (web: the browser's storage) |
| **My SOUL, Memory, Settings, About** | as before (+ Settings › Apps) | on SOUL | existing |

## 3 · The AI and the apps

The answer JSON gained one action, validated like the others:
`{"type": "navigate", "to": "<place, ≤ 80 chars>", "mode": "walk" | "bike" | "car"}` — Maps opens with the route.
The on-device rules catch "take me to …" / "navigate to …" / "du-mă la …" / "cum ajung la …" without any AI.
Claude (through SOUL Cloud's connector) has `navigate_on_soul(destination, mode)`; the cloud plans and pushes
`nav.start` to SOUL.

## 4 · SOUL Cloud endpoints (device token)

`GET /v1/device/apps/weather` · `GET /v1/device/apps/agenda` · `GET /v1/device/apps/rates` ·
`POST /v1/device/apps/findphone` · the maps endpoints in `../docs/11-MAPS.md` §5. The device asks through one queue
(`OsCmd::AppFetch` → `src/cloud.cpp`, paths must start with `/v1/device/`, GET or POST only) and gets the answer in
`Os::appData()`; offline it is status `-1` and every app says so calmly and keeps the last data it had.
Owner side: `/me/where` (location, Wi-Fi opt-in, calendar link, find-my-phone ringer, route links).

| Provider | Terms that matter | Configured by |
|---|---|---|
| Open-Meteo | free API is **non-commercial**; a product needs the customer API + key (Standard from ~$29/month); CC BY 4.0 attribution "Weather data by Open-Meteo.com" | `SOUL_OPEN_METEO_KEY` (or `SOUL_WEATHER=open-meteo-free` for a non-commercial pilot) |
| ECB reference rates | free, daily ~16:00 CET on working days, cite "Source: ECB"; informational, not for transactions | built in |
| Maps providers | see `../docs/11-MAPS.md` | `SOUL_PMTILES`, `SOUL_ROUTER`, `SOUL_GEOCODER`, `SOUL_WIFI_GEO` |

Without configuration the endpoints answer `501` and the apps show a "not set up" panel — nothing breaks.

## 5 · Tests and numbers

- Web: `node os/tests/apps.test.mjs` (56 checks: every app opens, its core flow, back by side button / swipe, standby
  still eyes-only, Romanian, zero console errors; writes the stills + sheet) and `soulos.test.mjs` (237) and
  `memory.test.mjs` (18), all green.
- Cloud: `ai/tests/test_apps_maps.py` (33 tests, mocked providers, no keys).
- Device: 194 native tests (map projection, SMB1 decode, polyline, route parse, turn angles, nav steps, weather /
  agenda / rates parse, time zones, units, habits, Pomodoro, breathing, stopwatch, the three games' physics and
  scoring, every app's screen flow); `pio run -e sim` + `program <dir> apps` makes the stills.
- Frame cost (callgrind, PC): maps 10.8 M instructions per frame, games 9.2 M, an idle screen 2.6 M
  (`firmware/BRINGUP.md` §4e). lcd28 image: app 2.46 MB of 6.25 MB, static RAM 114 KB of 320 KB; Maps and Games each
  keep one 460 KB PSRAM layer while open (released back on the eyes).

## 6 · Not done / open

- The map data in every demo is synthetic; a real PMTiles extract, Valhalla and Photon are not deployed.
- No compass: the step card trusts the owner's taps and the phone's fixes; there is no live position while walking.
- Wi-Fi geolocation coverage (beaconDB) is patchy; Google's terms need a legal check before production.
- Music cannot show or control the phone's media yet (AMS / AVRCP need BLE work).
- Nothing here has run on the board yet: `firmware/BRINGUP.md` §4e.
