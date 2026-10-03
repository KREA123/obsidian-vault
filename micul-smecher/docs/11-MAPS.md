# 11 · Maps on SOUL

SOUL M has no GPS and no magnetometer (the QMI8658 is accelerometer + gyro only); it talks to the world over 2.4 GHz
Wi-Fi. Maps therefore splits the work: **the phone (or Wi-Fi) says where SOUL is, SOUL Cloud does the heavy map work,
SOUL draws a small dark map on glass and walks you through the turns.**

Code: `ai/suflet_ai/maps.py` (geo, tiles, routing, the location book), `ai/suflet_ai/apps_routes.py` (HTTP),
`firmware/lib/Suflet/src/MapCore.*` (decode, project, paint, navigate), `OsApps*.cpp` (the screens), the web twin in
`os/index.html` (`window.SoulApps`). Tests: `ai/tests/test_apps_maps.py`, `firmware/test/test_suflet/test_apps.cpp`,
`os/tests/apps.test.mjs`. Pictures: `firmware/sim/shots/apps/`, `os/screenshots/apps/`.

## 1 · Where is SOUL?

| Source | How | Accuracy | Status |
|---|---|---|---|
| **The owner's phone** (primary) | `/me/where` page (signed in, CSRF-protected): *Share my location* uses the browser Geolocation API once; or paste a share link (Google Maps, Apple Maps, OpenStreetMap, `geo:`) — short `maps.app.goo.gl` / `goo.gl` links are expanded by the cloud, other hosts are refused | the phone's (5–30 m outdoors) | built + tested |
| **Wi-Fi geolocation** (opt-in per SOUL on `/me/where`) | SOUL scans; it sends BSSIDs + RSSI, never SSIDs; networks ending `_nomap` and locally administered (random) MACs are dropped; at least 2 APs, like the services require | 15–150 m in cities, nothing where coverage is thin | built + tested with mocked providers |
| IP geolocation | not used: city-level at best, wrong on mobile hotspots | – | rejected |

A fix lives 24 h in the cloud's `LocationBook` (SQLite) and on SOUL (NVS), and is shown with its age and source.

**Wi-Fi provider choice.** Mozilla Location Service closed in 2024. Options checked:

- **beaconDB** (`api.beacondb.net`, MLS-compatible API, no key): free, fair use, *small* deployments (< ~1k users)
  welcome; coverage is being rebuilt from scratch, so many places return "not found". **Pilot default.**
- **Google Geolocation API**: global coverage; 10,000 requests/month free, then about $5 per 1,000; the terms allow
  caching lat/lng for at most 30 days, and Google Maps Platform content is meant to be shown with Google maps — check
  the current Service Specific Terms with counsel before production (we only use the coordinates for routing and our
  own OSM-based map). **Production candidate.**
- Ichnaea self-hosted (`SOUL_WIFI_GEO=ichnaea:https://…`): needs your own observation data; HERE Positioning: same
  request shape, own key. Combain discontinued outdoor Wi-Fi positioning in 2020.

## 2 · The map

- **Data**: OpenStreetMap via a **self-hosted Protomaps PMTiles** basemap (`SOUL_PMTILES=/data/….pmtiles`; one file,
  range reads, no tile server). ODbL: attribution "© OpenStreetMap contributors" is sent in `X-Map-Attribution` and
  drawn on the rim ("map data: OpenStreetMap"). **Never `tile.openstreetmap.org`** (its usage policy forbids
  apps like this); SOUL itself never talks to any tile server. MapTiler / Stadia hosted tiles are alternatives (MapTiler's
  free plan is non-commercial; commercial starts with the Flex plan).
- **The bundle** (`GET /v1/device/maps/view?lat&lon&z`, `application/x-soul-map`): the cloud reads the vector tiles
  (MVT) around the point, keeps water, parks, roads (3 classes), paths, rail, buildings (z ≥ 17), place and POI
  labels, clips them to a 960 × 960 px square, simplifies (Douglas–Peucker, 0.7 px) and writes **SMB1**:
  `"SMB1"`, u8 version 1, u8 z, u16 count, u32 originX, u32 originY, u16 w, u16 h (20 bytes, LE), then per feature
  u8 class, u8 kind (1 line, 2 polygon, 3 point), u16 points, zig-zag varint deltas; points carry u8 length + UTF-8
  label. Limits: ≤ 24 KB, ≤ 600 features (minor roads and buildings go first). The demo city is 0.2–1.7 KB.
- **On SOUL**: decoded into flat arrays, projected Web-Mercator, painted dark (water deep blue, parks dark green,
  roads cream by class, anti-aliased lines, 4× sub-sampled polygons) into a 480 × 480 PSRAM layer that is repainted
  only when the view moves; the route, "you" and the glass are drawn over it each frame. Drag = pan; slide along the
  rim = zoom (zoom between bundle levels scales the layer, a new bundle is asked when the view leaves the area);
  `+`/`-`, *centre*. The last bundle stays in RAM until a restart; the last fix survives one.

## 3 · Routes

`POST /v1/device/maps/route {"to" | "lat","lon"; "mode": walk|bike|car}` → geocode (Photon) → route → the device JSON
`{id, to, mode, dist, dur, shape (polyline5), steps: [[turn, dist, idx, street, exit]], dest, src}` with turns
`depart, straight, slight_left, left, sharp_left, slight_right, right, sharp_right, uturn, roundabout, arrive, ferry`.

| Router | Terms | Use |
|---|---|---|
| **Valhalla** (self-hosted, MIT) | unlimited, our hardware; the FOSSGIS demo is for testing | **production default** (`SOUL_ROUTER=valhalla:https://…`) |
| OpenRouteService | free key: 2,000 directions/day, 40/min; commercial volume = paid plan or self-host | pilot (`ors:<key>`) |
| OSRM | self-hosted BSD-2; the public demo is 1 req/s, not for products | alternative (`osrm:https://…`) |

Geocoder: **Photon** (Apache 2.0, OSM data), self-hosted; `photon.komoot.io` is fair use only. Results are biased
to SOUL's last place; a destination farther than 60 km on foot or 400 km by bike / car is refused (`too_far`: send it to the phone). No location → `409 no_location`
("share your location from your phone"). Ways in: *Where to?* typed on the round keyboard; the AI action
`{"type": "navigate", "to", "mode"}` (web + device answer flow); the Claude connector tool `navigate_on_soul`, which
plans in the cloud and pushes `nav.start` (expires in 1 h) so Maps opens on SOUL with the route.

## 4 · Navigating without a compass

- The **step card** shows the distance to the next turn, the turn word and the street; the **arrow is relative to
  the route line** (the bearing change between ±20 m of route before and after the turn), not to north or the body.
- SOUL cannot see you walk: the owner **taps the card at each turn** (or *‹ ›*); a fresh phone fix snaps onto the
  route (≤ 45 m + accuracy, else "off route") and never moves more than one step back. ETA = distance left / mode
  speed (walk 1.35 m/s, bike 4.2 m/s, car: the router's average).
- **Send to phone**: a QR of `https://www.google.com/maps/dir/?api=1&destination=…&travelmode=…` (works offline on
  SOUL) and the same links (Google, Apple, `geo:`) on `/me/where`.

## 5 · API (all `Authorization: Bearer <device token>`)

| | |
|---|---|
| `GET /v1/device/maps/where` | `{"fix": {lat, lon, acc, src, age, label} \| null}` |
| `POST /v1/device/maps/wifi {"aps": [{mac, rssi, ssid?}]}` | `{"fix"}`; `403 not_allowed` until opted in; `422 too_few_aps` |
| `GET /v1/device/maps/view` | SMB1; `501` when no PMTiles is configured |
| `POST/GET /v1/device/maps/route`, `POST /v1/device/maps/route/end` (`DELETE` too) | plan / the pushed route / end |
| `POST /v1/device/maps/send` | `{"links": {"google", "apple", "geo"}}` |
| Owner: `/me/where`, `POST /v1/me/location`, `/v1/me/location/link`, `/v1/me/wifi-location` | session cookie + `x-csrf-token` |

## 6 · Real vs. demo

Real and tested (with recorded / mocked provider answers, no keys in the repo): the share-link parser, the location
book, Wi-Fi request building and privacy filtering, MVT decode → SMB1 encode, the PMTiles v3 reader, Valhalla / ORS /
OSRM / Photon adapters, routing JSON, the device decoder, painter, step logic, and every screen.
**Not configured anywhere yet**: a production PMTiles extract, a Valhalla and Photon server, a Wi-Fi provider key.
The simulator, the web prototype and the tests use `demo_city_tiles()`: a synthetic city (river, park, street grid,
place names around Bucharest's centre) clipped into real MVT tiles. **It is not OpenStreetMap data.**

## 7 · Costs at 1,000 SOULs (estimate)

PMTiles regional extract on object storage: < $5/month. Valhalla + Photon for one country on one 8 GB VM: ~$20–40/
month. Wi-Fi: beaconDB free (pilot); Google at ~5 Wi-Fi fixes per SOUL per day ≈ 150k/month ≈ $700/month — keep it
opt-in, cache fixes, prefer the phone.
