"""SoulOS apps in SOUL Cloud (docs/11-MAPS.md, os/APPS.md): maps (location, tiles -> SMB1, places, routes, handoff),
weather (Open-Meteo), the calendar agenda (ICS), find my phone, the device and owner HTTP routes, and the
`navigate_on_soul` connector tool. Every provider is a fake: no network, no keys.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.applications import Starlette

from _gateway_kit import DEV, Env
from suflet_ai import apps as apps_mod
from suflet_ai import maps as M
from suflet_ai.apps import (AppsHub, CalendarService, EcbRates, OpenMeteo, PhoneRing, check_ics_url, parse_ics, weather_for_device,
                            wmo_icon)
from suflet_ai.apps_routes import build_apps_router, where_routes
from suflet_ai.maps import MapsError

BUC = (44.4355, 26.1025)
T0 = dt.datetime(2026, 10, 3, 10, 0, tzinfo=ZoneInfo("Europe/Bucharest")).timestamp()


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


class FakeHttp:
    """Scripted (status, body) per URL prefix; records every request."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, method, url, body=None, headers=None, timeout=8.0):
        self.calls.append((method, url, body, headers))
        for prefix, resp in self.routes.items():
            if url.startswith(prefix):
                return resp(method, url, body) if callable(resp) else resp
        return 599, b""


# ================================================================== geo math ==

def test_mercator_round_trip_and_distances():
    for z in (3, 10, 16, 18):
        x, y = M.world_px(*BUC, z)
        la, lo = M.lat_lon(x, y, z)
        assert abs(la - BUC[0]) < 1e-9 and abs(lo - BUC[1]) < 1e-9
    assert M.world_px(0, 0, 0) == (128.0, 128.0)
    assert abs(M.haversine(44.4355, 26.1025, 44.4268, 26.1025) - 967) < 5  # ~0.0087 deg north-south
    assert abs(M.bearing(44.0, 26.0, 45.0, 26.0) - 0) < 0.01
    assert abs(M.bearing(44.0, 26.0, 44.0, 27.0) - 90) < 1


def test_polyline_matches_googles_example():
    pts = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
    assert M.encode_polyline(pts) == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    back = M.decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert all(abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6 for a, b in zip(pts, back))
    six = M.encode_polyline(pts, 6)
    assert M.decode_polyline(six, 6)[2] == pytest.approx(pts[2], abs=1e-6)
    with pytest.raises(ValueError):
        M.decode_polyline("_p~iF~ps|U_")


def test_simplify_and_clip():
    line = [(0, 0), (1, 0.1), (2, -0.1), (3, 0), (4, 5)]
    s = M.simplify(line, 0.5)
    assert s[0] == (0, 0) and s[-1] == (4, 5) and (3, 0) in s and (1, 0.1) not in s
    runs = M.clip_line([(-10, 5), (5, 5), (20, 5)], 0, 0, 10, 10)
    assert runs == [[(0, 5), (5, 5), (10, 5)]]
    two = M.clip_line([(-5, 5), (5, 5), (5, 20), (6, 20), (6, 5), (15, 5)], 0, 0, 10, 10)
    assert len(two) == 2
    poly = M.clip_poly([(-5, -5), (5, -5), (5, 5), (-5, 5)], 0, 0, 10, 10)
    assert sorted(poly) == sorted([(0, 0), (5, 0), (5, 5), (0, 5)])


# ================================================================== location ==

@pytest.mark.parametrize("text,lat,lon,label", [
    ("https://www.google.com/maps/place/Ateneul+Rom%C3%A2n/@44.4413,26.0973,17z/data=!3m1!4b1!4m6!3m5!1s0x0:0x0!8m2!3d44.4412!4d26.0975",
     44.4412, 26.0975, "Ateneul Român"),
    ("look: https://maps.google.com/?q=44.4268,26.1025 !", 44.4268, 26.1025, ""),
    ("https://www.google.com/maps/search/?api=1&query=47.5951518,-122.3316393", 47.5951518, -122.3316393, ""),
    ("https://maps.apple.com/?ll=44.4268,26.1025&q=Lipscani", 44.4268, 26.1025, "Lipscani"),
    ("https://maps.apple.com/?daddr=44.43,26.1", 44.43, 26.1, ""),
    ("geo:44.4268,26.1025?q=Cafe", 44.4268, 26.1025, "Cafe"),
    ("https://www.openstreetmap.org/#map=17/44.43512/26.10209", 44.43512, 26.10209, ""),
    ("https://www.openstreetmap.org/?mlat=44.4&mlon=26.1#map=15/44.4/26.1", 44.4, 26.1, ""),
    ("44.4355, 26.1025", 44.4355, 26.1025, ""),
])
def test_share_links_from_phones(text, lat, lon, label):
    fix, q = M.parse_share_link(text)
    assert fix is not None, q
    assert (fix.lat, fix.lon) == pytest.approx((lat, lon)) and fix.source == "link"
    assert fix.label == label


def test_share_links_queries_short_links_and_other_hosts():
    fix, q = M.parse_share_link("https://maps.apple.com/?address=Strada%20Lipscani%2012,%20Bucure%C8%99ti")
    assert fix is None and q == "Strada Lipscani 12, București"
    fix, q = M.parse_share_link("https://evil.example/@44.4,26.1")
    assert fix is None and q == ""  # only map hosts are read
    seen = []

    def resolve(u):
        seen.append(u)
        return "https://www.google.com/maps/place/X/@44.5,26.2,15z"
    fix, _ = M.parse_share_link("https://maps.app.goo.gl/AbCdEf123", resolve)
    assert seen == ["https://maps.app.goo.gl/AbCdEf123"] and (fix.lat, fix.lon) == (44.5, 26.2)
    fix, _ = M.parse_share_link("https://maps.app.goo.gl/AbCdEf123")  # no resolver: nothing
    assert fix is None
    fix, q = M.parse_share_link("Piața Unirii")
    assert fix is None and q == "Piața Unirii"
    assert M.parse_share_link("0,0")[0] is None  # null island is not a place


def test_location_book_keeps_the_better_fix_and_forgets_after_a_day(tmp_path):
    c = Clock()
    book = M.LocationBook(str(tmp_path / "m.sqlite"), clock=c)
    book.put(DEV, M.Fix(44.43, 26.10, 12, "phone"))
    kept = book.put(DEV, M.Fix(44.50, 26.20, 300, "wifi"))  # coarse, 0 s later: the phone fix stays
    assert kept.source == "phone" and book.get(DEV).lat == 44.43
    c.t += 700
    assert book.put(DEV, M.Fix(44.50, 26.20, 300, "wifi")).source == "wifi"
    c.t += 25 * 3600
    assert book.get(DEV) is None
    assert book.db.execute("SELECT COUNT(*) FROM fixes").fetchone()[0] == 0
    assert not book.wifi_allowed(DEV)
    book.set_wifi_allowed(DEV, True)
    assert book.wifi_allowed(DEV)


def test_wifi_geolocation_filters_and_parses():
    aps = [{"mac": "a4:2b:b0:11:22:33", "rssi": -50, "ssid": "Home"},
           {"mac": "f2:11:22:33:44:55", "rssi": -40, "ssid": "Ana's iPhone"},  # locally administered: a hotspot
           {"mac": "00:1a:2b:3c:4d:5e", "rssi": -70, "ssid": "Cafe_nomap"},     # opted out
           {"mac": "00:1a:2b:3c:4d:5f", "rssi": -65, "ssid": "Office"},
           {"mac": "nonsense", "rssi": -60}]
    u = M.usable_aps(aps)
    assert [a["macAddress"] for a in u] == ["a4:2b:b0:11:22:33", "00:1a:2b:3c:4d:5f"]
    http = FakeHttp({"https://api.beacondb.net": (200, b'{"location":{"lat":44.44,"lng":26.09},"accuracy":40}')})
    g = M.WifiGeolocator(http=http)
    f = g.locate(aps)
    assert (f.lat, f.lon, f.acc_m, f.source) == (44.44, 26.09, 40, "wifi")
    sent = json.loads(http.calls[0][2])
    assert sent["considerIp"] is False and len(sent["wifiAccessPoints"]) == 2
    assert "ssid" not in json.dumps(sent)  # names never leave
    with pytest.raises(M.MapsError) as e:
        g.locate(aps[:2])
    assert e.value.code == "too_few_aps"
    assert M.WifiGeolocator(http=FakeHttp({"https://": (404, b"{}")})).locate(aps) is None
    google = M.WifiGeolocator("https://www.googleapis.com/geolocation/v1/geolocate", "KEY", FakeHttp(
        {"https://www.googleapis.com/geolocation/v1/geolocate?key=KEY": (200, b'{"location":{"lat":1.5,"lng":2.5},"accuracy":20}')}))
    assert google.locate(aps).lat == 1.5
    with pytest.raises(M.MapsError):
        M.WifiGeolocator(http=FakeHttp({"https://": (500, b"")})).locate(aps)


# ===================================================================== tiles ==

def test_mvt_and_pmtiles_round_trip():
    layers = {"roads": [{"type": 2, "geom": [[(0, 0), (100, 50), (200, -10)]], "props": {"kind": "major_road", "name": "Calea"}}],
              "water": [{"type": 3, "geom": [[(10, 10), (60, 10), (60, 60), (10, 60), (10, 10)]], "props": {"kind": "water", "n": -3, "f": 1.5}}],
              "places": [{"type": 1, "geom": [[(5, 7)]], "props": {"name": "Lipscani", "v": True}}]}
    t = M.decode_mvt(M.encode_mvt(layers))
    assert t["roads"]["features"][0]["geom"] == [[(0, 0), (100, 50), (200, -10)]]
    assert t["roads"]["features"][0]["props"] == {"kind": "major_road", "name": "Calea"}
    w = t["water"]["features"][0]
    assert w["type"] == 3 and w["geom"][0][0] == w["geom"][0][-1] and w["props"]["n"] == -3 and w["props"]["f"] == 1.5
    assert t["places"]["features"][0]["props"]["v"] is True
    archive = M.write_pmtiles({(15, 18568, 11780): b"A" * 10, (15, 18569, 11780): b"BB", (14, 9284, 5890): b"CCC"})
    pm = M.PMTiles(lambda off, n: archive[off:off + n])
    assert pm.tile(15, 18569, 11780) == b"BB" and pm.tile(14, 9284, 5890) == b"CCC"
    assert pm.tile(15, 1, 1) is None and pm.max_z == 15
    assert M.zxy_to_tileid(0, 0, 0) == 0 and M.zxy_to_tileid(1, 0, 0) == 1 and M.zxy_to_tileid(1, 1, 1) == 3
    with pytest.raises(M.MapsError):
        M.PMTiles(lambda off, n: b"nope" * 40)


def test_bundle_from_the_demo_city_is_small_and_drawable():
    tiles = M.demo_city_tiles(*BUC, z=15)
    src = M.DemoTiles(tiles, 15)
    b = M.build_bundle(src, *BUC, 16)  # one zoom past the data: over-zoomed
    assert b[:4] == b"SMB1" and len(b) <= M.BUNDLE_MAX_BYTES
    d = M.decode_bundle(b)
    assert d["z"] == 16 and d["w"] == d["h"] == M.BUNDLE_SIZE
    cx, cy = M.world_px(*BUC, 16)
    assert abs(d["origin"][0] + 480 - cx) <= 1 and abs(d["origin"][1] + 480 - cy) <= 1
    classes = {f["cls"] for f in d["features"]}
    assert {M.C_WATER, M.C_PARK, M.C_ROAD_MAJOR, M.C_ROAD_MINOR, M.C_PLACE} <= classes
    order = [f["cls"] for f in d["features"]]
    assert order.index(M.C_WATER) < order.index(M.C_ROAD_MAJOR) < order.index(M.C_PLACE)  # labels drawn last
    for f in d["features"]:
        for x, y in f["pts"]:
            assert -3 <= x <= 963 and -3 <= y <= 963
    labels = {f["label"] for f in d["features"] if f["kind"] == M.K_POINT}
    assert "Lipscani" in labels
    low = M.decode_bundle(M.build_bundle(src, *BUC, 13))
    assert M.C_ROAD_MINOR not in {f["cls"] for f in low["features"]}  # minor streets only from z 14


def test_bundle_caps_size_and_cuts_labels_cleanly():
    many = [M.MapFeature(M.C_ROAD_MINOR, M.K_LINE, [(i, 0), (i, 900), (i + 3, 450)]) for i in range(5000)]
    b = M.encode_bundle(16, 0, 0, 960, 960, many)
    assert len(b) <= M.BUNDLE_MAX_BYTES and 100 < M.decode_bundle(b)["features"].__len__() < 5000
    lbl = M.encode_bundle(16, 0, 0, 960, 960, [M.MapFeature(M.C_PLACE, M.K_POINT, [(10, 10)], "Ș" * 30)])
    assert M.decode_bundle(lbl)["features"][0]["label"] == "Ș" * 20  # 40 bytes, whole characters


def test_view_needs_map_data_and_caches():
    svc = M.MapsService(clock=Clock())
    with pytest.raises(M.MapsError) as e:
        svc.view(*BUC, 16)
    assert e.value.code == "config" and e.value.status == 501
    calls = []

    class Counting(M.DemoTiles):
        def tile(self, z, x, y):
            calls.append((z, x, y))
            return super().tile(z, x, y)
    svc.tiles = Counting(M.demo_city_tiles(*BUC), 15)
    a = svc.view(*BUC, 16)
    n = len(calls)
    b = svc.view(BUC[0] + 0.00001, BUC[1], 16)  # a step away: the same cached bundle
    assert a == b and len(calls) == n


# ===================================================================== routes ==

VALHALLA = {"trip": {"legs": [{"shape": M.encode_polyline([(44.4355, 26.1025), (44.4360, 26.1025), (44.4360, 26.1040),
                                                             (44.4370, 26.1040)], 6),
                               "summary": {"length": 0.31, "time": 230},
                               "maneuvers": [{"type": 1, "length": 0.055, "begin_shape_index": 0, "street_names": ["Calea Victoriei"]},
                                             {"type": 10, "length": 0.12, "begin_shape_index": 1, "street_names": ["Strada Lipscani"]},
                                             {"type": 15, "length": 0.11, "begin_shape_index": 2},
                                             {"type": 4, "length": 0, "begin_shape_index": 3}]}]}}
ORS = {"features": [{"geometry": {"coordinates": [[26.1025, 44.4355], [26.1025, 44.4360], [26.1040, 44.4360]]},
                     "properties": {"summary": {"distance": 180.5, "duration": 130},
                                    "segments": [{"distance": 180.5, "duration": 130, "steps": [
                                        {"type": 11, "distance": 55, "way_points": [0, 1], "name": "Calea Victoriei"},
                                        {"type": 1, "distance": 125.5, "way_points": [1, 2], "name": "-"},
                                        {"type": 10, "distance": 0, "way_points": [2, 2], "name": "-"}]}]}}]}
OSRM = {"code": "Ok", "routes": [{"distance": 180, "duration": 140,
                                  "geometry": M.encode_polyline([(44.4355, 26.1025), (44.4360, 26.1025), (44.4360, 26.1040)]),
                                  "legs": [{"steps": [
                                      {"distance": 55, "name": "Calea Victoriei", "maneuver": {"type": "depart", "location": [26.1025, 44.4355]}},
                                      {"distance": 125, "name": "Lipscani", "maneuver": {"type": "turn", "modifier": "right", "location": [26.1025, 44.4360]}},
                                      {"distance": 0, "name": "", "maneuver": {"type": "arrive", "location": [26.1040, 44.4360]}}]}]}]}


def test_three_routers_one_route_model():
    v = M.ValhallaRouter("https://valhalla.local", http=FakeHttp({"https://valhalla.local/route": (200, json.dumps(VALHALLA).encode())}))
    r = v.route(BUC, (44.437, 26.104), "walk")
    assert [s.turn for s in r.steps] == ["depart", "right", "left", "arrive"]
    assert r.dist_m == pytest.approx(310) and r.dur_s == 230 and r.steps[1].street == "Strada Lipscani"
    assert json.loads(v.http.calls[0][2])["costing"] == "pedestrian"
    o = M.OrsRouter("KEY", http=FakeHttp({"https://api.openrouteservice.org/v2/directions/foot-walking": (200, json.dumps(ORS).encode())}))
    r2 = o.route(BUC, (44.436, 26.104), "walk")
    assert [s.turn for s in r2.steps] == ["depart", "right", "arrive"] and r2.steps[1].street == ""
    assert o.http.calls[0][3]["authorization"] == "KEY"
    s = M.OsrmRouter("https://osrm.local", http=FakeHttp({"https://osrm.local": (200, json.dumps(OSRM).encode())}))
    r3 = s.route(BUC, (44.436, 26.104), "bike")
    assert [x.turn for x in r3.steps] == ["depart", "right", "arrive"] and r3.steps[1].idx == 1
    assert "/bike/" in s.http.calls[0][1]
    with pytest.raises(M.MapsError) as e:
        M.OrsRouter("K", http=FakeHttp({"https://": (429, b"")})).route(BUC, BUC, "walk")
    assert e.value.code == "provider" and e.value.status == 503
    with pytest.raises(M.MapsError) as e:
        M.ValhallaRouter("https://v", http=FakeHttp({"https://": (400, b"{}")})).route(BUC, BUC, "walk")
    assert e.value.code == "no_route"


def test_device_json_keeps_the_turns_on_the_simplified_shape():
    pts = [(44.4355 + i * 0.00001, 26.1025) for i in range(60)] + [(44.4361, 26.1025 + i * 0.00002) for i in range(1, 60)]
    steps = [M.Step("depart", 66, 0, "A"), M.Step("right", 130, 60, "B"), M.Step("arrive", 0, len(pts) - 1)]
    r = M.Route(pts, 196, 150, steps, "walk", "Cafe", pts[-1][0], pts[-1][1], "test", "rt1")
    j = r.device_json()
    shape = M.decode_polyline(j["shape"])
    assert len(shape) < 10  # two straight runs: a handful of points
    turn_pt = shape[j["steps"][1][2]]
    assert turn_pt == pytest.approx(pts[60], abs=1e-5)
    assert j["steps"][1][:2] == [M.TURNS.index("right"), 130] and j["steps"][1][3] == "B"
    assert j["dest"] == [round(pts[-1][0], 6), round(pts[-1][1], 6)] and len(json.dumps(j)) < 600


class FakeGeo:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def search(self, text, near=None, lang="en", limit=5):
        self.calls.append((text, near))
        return [M.Place(*h) for h in self.hits.get(text, [])]


class FakeRouter:
    def __init__(self):
        self.calls = []

    def route(self, a, b, mode, lang="en"):
        self.calls.append((a, b, mode))
        return M.Route([a, b], M.haversine(*a, *b), 600, [M.Step("depart", 100, 0), M.Step("arrive", 0, 1)], mode)


def test_plan_routes_from_where_soul_is_and_hands_off_to_the_phone():
    c = Clock()
    geo, rt = FakeGeo({"Ateneu": [("Ateneul Român", 44.4413, 26.0973, "Str. Benjamin Franklin")]}), FakeRouter()
    svc = M.MapsService(clock=c, router=rt, geocoder=geo)
    with pytest.raises(M.MapsError) as e:
        svc.plan(DEV, "Ateneu")
    assert e.value.code == "no_location" and e.value.status == 409
    svc.set_phone_fix(DEV, *BUC, 15)
    r = svc.plan(DEV, "Ateneu", mode="walk")
    assert r.to == "Ateneul Român" and rt.calls[0][1] == (44.4413, 26.0973) and geo.calls[0][1].source == "phone"
    assert svc.current_route(DEV) is r and r.id.startswith("rt")
    r2 = svc.plan(DEV, "https://maps.apple.com/?ll=44.43,26.11&q=Cafe")  # a pasted link: no search
    assert r2.to == "Cafe" and len(geo.calls) == 1
    with pytest.raises(M.MapsError) as e:
        svc.plan(DEV, "Nowhere")
    assert e.value.code == "not_found"
    with pytest.raises(M.MapsError) as e:
        svc.plan(DEV, "", lat=48.85, lon=2.35, mode="walk")  # Paris on foot
    assert e.value.code == "too_far"
    h = svc.send_to_phone(DEV)
    assert h["links"]["google"].startswith("https://www.google.com/maps/dir/?api=1&destination=44.430000%2C26.110000")
    assert "travelmode=walking" in h["links"]["google"] and h["links"]["apple"].startswith("https://maps.apple.com/?daddr=")
    assert svc.take_handoffs(DEV)[0]["to"] == "Cafe"
    c.t += 7 * 3600
    assert svc.current_route(DEV) is None


def test_photon_geocoder_parses_and_biases():
    body = {"features": [{"geometry": {"coordinates": [26.0973, 44.4413]},
                          "properties": {"name": "Ateneul Român", "street": "Strada Benjamin Franklin", "city": "București"}},
                         {"geometry": {"coordinates": [999, 999]}, "properties": {"name": "bad"}}]}
    http = FakeHttp({"https://photon.local/api/": (200, json.dumps(body).encode())})
    g = M.PhotonGeocoder("https://photon.local", http)
    hits = g.search("ateneu", M.Fix(*BUC), "ro")
    assert len(hits) == 1 and hits[0].name == "Ateneul Român" and hits[0].detail == "Strada Benjamin Franklin, București"
    assert "lat=44.4355" in http.calls[0][1] and "lang=default" in http.calls[0][1]


# ==================================================================== weather ==

OM = {"current": {"temperature_2m": 21.4, "weather_code": 2, "apparent_temperature": 20.2, "wind_speed_10m": 11.6},
      "hourly": {"time": [f"2026-10-03T{h:02d}:00" for h in range(10, 23)], "temperature_2m": [20 + i * 0.5 for i in range(13)],
                 "weather_code": [2, 2, 3, 61, 61, 3, 1, 0, 0, 0, 0, 0, 0], "precipitation_probability": [10] * 13},
      "daily": {"time": ["2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06"], "weather_code": [2, 61, 0, 71],
                "temperature_2m_max": [24.2, 18, 20, 3], "temperature_2m_min": [13, 11, 9, -2],
                "precipitation_probability_max": [30, 80, 0, 60]}}


def test_weather_for_device_and_codes():
    w = weather_for_device(OM, "ro", "București")
    assert (w["t"], w["icon"], w["word"], w["hi"], w["lo"], w["rain"]) == (21, "part", "Parțial noros", 24, 13, 30)
    assert w["hours"][0] == ["10", 20, "part", 10] and len(w["hours"]) == 6 and w["hours"][2][2] == "rain"
    assert w["days"] == [["Du", 18, 11, "rain"], ["Lu", 20, 9, "sun"], ["Ma", 3, -2, "snow"]]
    assert len(json.dumps(w)) < 700 and w["src"] == "Open-Meteo"
    assert wmo_icon(95) == "storm" and wmo_icon(45) == "fog" and wmo_icon("x") == "cloud"
    with pytest.raises(M.MapsError):
        weather_for_device({"current": {}}, "en")


def test_open_meteo_free_vs_commercial_and_cache():
    c = Clock()
    http = FakeHttp({"https://": (200, json.dumps(OM).encode())})
    free = OpenMeteo(http=http, clock=c)
    free.forecast(*BUC)
    free.forecast(BUC[0] + 0.01, BUC[1])  # same ~5 km cell: cached
    assert free.calls == 1 and http.calls[0][1].startswith("https://api.open-meteo.com/v1/forecast?")
    c.t += 1801
    free.forecast(*BUC)
    assert free.calls == 2
    paid = OpenMeteo("OMKEY", http=http, clock=c)
    paid.forecast(*BUC)
    assert http.calls[-1][1].startswith("https://customer-api.open-meteo.com/v1/forecast?") and "apikey=OMKEY" in http.calls[-1][1]


# =================================================================== calendar ==

ICS = """BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:1\r
SUMMARY:Dentist\\, Dr. Pop\r
LOCATION:Str. Lipscani 5\r
DTSTART;TZID=Europe/Bucharest:20261003T150000\r
DTEND;TZID=Europe/Bucharest:20261003T153000\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:2\r
SUMMARY:Standup\r
DTSTART:20260928T060000Z\r
DURATION:PT15M\r
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR\r
EXDATE:20261005T060000Z\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:3\r
SUMMARY:Ana's birthday\r
DTSTART;VALUE=DATE:20261004\r
DTEND;VALUE=DATE:20261005\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:4\r
SUMMARY:Book club\r
DTSTART:20260101T190000\r
RRULE:FREQ=MONTHLY;BYDAY=2TU\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:5\r
SUMMARY:Cancelled thing\r
STATUS:CANCELLED\r
DTSTART:20261004T100000Z\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:6\r
SUMMARY:Long ago\r
DTSTART:20250101T100000Z\r
RRULE:FREQ=DAILY;UNTIL=20250110T000000Z\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:7\r
SUMMARY:A very long title that keeps going on and on and on far beyond anything a round screen could ever show at once\r
 folded\r
DTSTART:20261009T080000Z\r
END:VEVENT\r
END:VCALENDAR\r
"""


def test_ics_agenda_expands_recurrence_and_respects_zones():
    now = dt.datetime(2026, 10, 3, 10, 0, tzinfo=ZoneInfo("Europe/Bucharest"))
    ev = parse_ics(ICS, "Europe/Bucharest", now)
    titles = [(e["s"], e["t"]) for e in ev]
    assert titles[0] == ("2026-10-03T15:00", "Dentist, Dr. Pop") and ev[0]["l"] == "Str. Lipscani 5"
    assert ("2026-10-04T00:00", "Ana's birthday") in titles and next(e for e in ev if e["t"] == "Ana's birthday")["a"]
    standups = [s for s, t in titles if t == "Standup"]
    assert standups == ["2026-10-07T09:00", "2026-10-09T09:00"]  # Mon 5th is an EXDATE; 06:00Z = 09:00 local
    assert ("2026-10-13T19:00", "Book club") not in titles  # 2nd Tuesday of October is the 13th: outside 7 days
    assert all(t not in ("Cancelled thing", "Long ago") for _, t in titles)
    long = next(e for e in ev if e["s"] == "2026-10-09T11:00")
    assert len(long["t"]) == 80 and long["t"].startswith("A very long title")
    ev14 = parse_ics(ICS, "Europe/Bucharest", now, days=14)
    assert ("2026-10-13T19:00", "Book club") in [(e["s"], e["t"]) for e in ev14]
    assert len(parse_ics(ICS, "Europe/Bucharest", now, days=60, limit=12)) == 12


def test_ics_address_rules_block_ssrf():
    pub = lambda h: ["142.250.185.110"]  # noqa: E731
    assert check_ics_url("webcal://calendar.google.com/x/basic.ics", pub) == "https://calendar.google.com/x/basic.ics"
    for bad in ("http://calendar.google.com/x.ics", "https://user:pw@cal.example/x.ics", "https://cal.example:8443/x",
                "ftp://x/y", "https://localhost/x.ics", "https://printer.local/x.ics"):
        with pytest.raises(M.MapsError):
            check_ics_url(bad, pub)
    for addr in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "192.168.1.1", "::1", "fd00::1"):
        with pytest.raises(M.MapsError):
            check_ics_url("https://cal.example/x.ics", lambda h, a=addr: [a])


def test_calendar_service_fetches_at_most_every_15_minutes():
    c = Clock()
    http = FakeHttp({"https://cal.example/": (200, ICS.encode())})
    cal = CalendarService(http=http, clock=c, resolver=lambda h: ["93.184.216.34"])
    with pytest.raises(M.MapsError) as e:
        cal.agenda(DEV, "Europe/Bucharest")
    assert e.value.code == "no_calendar"
    cal.set_link(DEV, "https://cal.example/basic.ics")
    a = cal.agenda(DEV, "Europe/Bucharest")
    cal.agenda(DEV, "Europe/Bucharest")
    assert a[0]["t"] == "Dentist, Dr. Pop" and len(http.calls) == 1
    c.t += 901
    cal.agenda(DEV, "Europe/Bucharest")
    assert len(http.calls) == 2
    cal2 = CalendarService(http=FakeHttp({"https://": (200, b"<html>nope</html>")}), clock=c, resolver=lambda h: ["93.184.216.34"])
    cal2.set_link(DEV, "https://cal.example/x")
    with pytest.raises(M.MapsError):
        cal2.agenda(DEV, "Europe/Bucharest")


def test_find_my_phone_reaches_an_open_page():
    c = Clock()
    pushed = []
    r = PhoneRing(clock=c, push=lambda acc, msg: pushed.append((acc, msg)) or 1)
    assert r.ring("acc_1")["reach"] == "push"
    assert r.poll("acc_1") is True  # the page hears it
    out = r.ring("acc_1", "Miso")
    assert out["reach"] == "page" and "Miso" in pushed[-1][1]["title"]
    r.found("acc_1")
    assert r.poll("acc_1") is False
    r.ring("acc_1")
    c.t += 61
    assert r.poll("acc_1") is False


# ================================================================= HTTP routes ==

ECB_XML = (b'<?xml version="1.0" encoding="UTF-8"?><gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" '
           b'xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><Cube><Cube time=\'2026-09-25\'>'
           b"<Cube currency='USD' rate='1.0912'/><Cube currency='JPY' rate='161.42'/><Cube currency='RON' rate='4.9746'/>"
           b"<Cube currency='GBP' rate='0.8391'/></Cube></Cube></gesmes:Envelope>")


def test_ecb_rates_parse_cache_and_fallback():
    c = Clock()
    http = FakeHttp({"https://www.ecb.europa.eu/": (200, ECB_XML)})
    e = EcbRates(http=http, clock=c)
    j = e.latest()
    assert j == {"base": "EUR", "date": "2026-09-25", "rates": {"USD": 1.0912, "JPY": 161.42, "RON": 4.9746, "GBP": 0.8391},
                 "source": "ECB"}
    e.latest()
    assert e.calls == 1  # cached for 6 h
    c.t += 7 * 3600
    http.routes["https://www.ecb.europa.eu/"] = (503, b"")
    assert e.latest()["date"] == "2026-09-25"  # yesterday's rates beat none
    with pytest.raises(MapsError):
        EcbRates(http=FakeHttp({"https://": (200, b"<html>maintenance</html>")}), clock=c).latest()


def _hub(c):
    tiles = M.DemoTiles(M.demo_city_tiles(*BUC), 15)
    maps = M.MapsService(clock=c, tiles=tiles, router=FakeRouter(),
                         geocoder=FakeGeo({"Ateneu": [("Ateneul Român", 44.4413, 26.0973, "")]}),
                         wifi=M.WifiGeolocator(http=FakeHttp({"https://": (200, b'{"location":{"lat":44.44,"lng":26.09},"accuracy":40}')})))
    return AppsHub(maps, OpenMeteo(http=FakeHttp({"https://": (200, json.dumps(OM).encode())}), clock=c),
                   CalendarService(http=FakeHttp({"https://": (200, ICS.encode())}), clock=c, resolver=lambda h: ["93.184.216.34"]),
                   PhoneRing(clock=c), clock=c, rates=EcbRates(http=FakeHttp({"https://www.ecb.europa.eu/": (200, ECB_XML)}), clock=c))


def test_device_routes_end_to_end(tmp_path):
    env = Env(tmp_path)
    c = Clock()
    h = _hub(c)
    env.app.include_router(build_apps_router(lambda: env.gw, lambda: h))
    d = env.paired_device()
    cl = TestClient(env.app)
    auth = {"authorization": f"Bearer {d.token}"}
    assert cl.get("/v1/device/maps/where").status_code == 401
    assert cl.get("/v1/device/maps/where", headers=auth).json() == {"fix": None}
    w = cl.get("/v1/device/apps/weather", headers=auth)
    assert w.status_code == 409 and w.json()["error"]["code"] == "no_location"
    h.maps.set_phone_fix(DEV, *BUC, 15)
    assert cl.get("/v1/device/maps/where", headers=auth).json()["fix"]["src"] == "phone"
    assert cl.get("/v1/device/apps/weather", headers=auth).json()["icon"] == "part"
    v = cl.get(f"/v1/device/maps/view?lat={BUC[0]}&lon={BUC[1]}&z=16", headers=auth)
    assert v.status_code == 200 and v.content[:4] == b"SMB1" and v.headers["x-map-attribution"] == "(c) OpenStreetMap contributors"
    assert cl.get("/v1/device/maps/view?lat=x&lon=1", headers=auth).status_code == 422
    r = cl.post("/v1/device/maps/route", headers=auth, json={"to": "Ateneu", "mode": "walk"})
    assert r.status_code == 200 and r.json()["to"] == "Ateneul Român" and r.json()["steps"][0][0] == 0
    assert cl.get("/v1/device/maps/route", headers=auth).json()["id"] == r.json()["id"]
    assert cl.post("/v1/device/maps/send", headers=auth).json()["links"]["google"].startswith("https://www.google.com/maps/dir/")
    assert cl.delete("/v1/device/maps/route", headers=auth).json() == {"ok": True}
    assert cl.get("/v1/device/maps/route", headers=auth).status_code == 404
    cl.post("/v1/device/maps/route", headers=auth, json={"to": "Ateneu"})
    assert cl.post("/v1/device/maps/route/end", headers=auth, json={}).json() == {"ok": True}  # the device's POST form
    assert cl.get("/v1/device/maps/route", headers=auth).status_code == 404
    rt = cl.get("/v1/device/apps/rates", headers=auth).json()
    assert rt["base"] == "EUR" and rt["date"] == "2026-09-25" and rt["rates"]["RON"] == 4.9746
    wf = cl.post("/v1/device/maps/wifi", headers=auth, json={"aps": [{"mac": "a4:2b:b0:11:22:33", "rssi": -50},
                                                                     {"mac": "00:1a:2b:3c:4d:5f", "rssi": -60}]})
    assert wf.status_code == 403 and wf.json()["error"]["code"] == "not_allowed"  # opt-in first
    h.maps.book.set_wifi_allowed(DEV, True)
    c.t += 700
    assert cl.post("/v1/device/maps/wifi", headers=auth, json={"aps": [{"mac": "a4:2b:b0:11:22:33", "rssi": -50},
                                                                       {"mac": "00:1a:2b:3c:4d:5f", "rssi": -60}]}).json()["fix"]["src"] == "wifi"
    assert cl.get("/v1/device/apps/agenda", headers=auth).status_code == 404
    h.calendar.set_link(DEV, "https://cal.example/basic.ics")
    ag = cl.get("/v1/device/apps/agenda", headers=auth).json()
    assert ag["tz"] == "Europe/Bucharest" and isinstance(ag["events"], list)
    f = cl.post("/v1/device/apps/findphone", headers=auth).json()
    assert f["ringing"] is True and h.ring.poll("acc_1") is True


class _Sess:
    def __init__(self, acc, csrf="tok"):
        self.account_id, self.csrf = acc, csrf


class _Accounts:
    def __init__(self):
        self.s = None

    def current_session(self, request):
        return self.s


class _Gw:
    def __init__(self, owner="acc_1"):
        self.owner = owner

    async def device_info(self, dev):
        return {"device_id": dev, "account_id": self.owner, "revoked": False} if dev == DEV else None

    async def devices_of(self, acc):
        return [{"device_id": DEV, "account_id": self.owner}] if acc == self.owner else []


def test_owner_routes_need_the_owner_and_csrf():
    c = Clock()
    h = _hub(c)
    acc = _Accounts()
    rc = type("RC", (), {"accounts": acc, "gateway": _Gw()})()
    app = Starlette(routes=where_routes(rc, {"Content-Security-Policy": "default-src 'self'"}, lambda: h))
    cl = TestClient(app)
    hdr = {"x-csrf-token": "tok", "cookie": "__Host-soul_csrf=tok"}
    assert cl.post("/v1/me/location", json={"device_id": DEV, "lat": 44.4, "lon": 26.1}).status_code == 401
    acc.s = _Sess("acc_1")
    assert cl.post("/v1/me/location", json={"device_id": DEV, "lat": 44.4, "lon": 26.1}).status_code == 403  # no CSRF
    r = cl.post("/v1/me/location", json={"device_id": DEV, "lat": 44.4, "lon": 26.1, "acc": 9}, headers=hdr)
    assert r.status_code == 200 and h.maps.where(DEV).acc_m == 9
    assert cl.post("/v1/me/location", json={"device_id": DEV, "lat": 144, "lon": 26.1}, headers=hdr).status_code == 422
    assert cl.post("/v1/me/location/link", json={"device_id": DEV, "text": "https://maps.apple.com/?ll=44.43,26.11&q=Cafe"},
                   headers=hdr).json()["fix"]["label"] == "Cafe"
    assert cl.post("/v1/me/wifi-location", json={"device_id": DEV, "on": True}, headers=hdr).json()["on"] is True
    assert h.maps.book.wifi_allowed(DEV)
    assert cl.post("/v1/me/calendar", json={"device_id": DEV, "url": "http://x/y"}, headers=hdr).status_code == 422
    assert cl.post("/v1/me/calendar", json={"device_id": DEV, "url": "https://cal.example/basic.ics"}, headers=hdr).json()["linked"]
    assert cl.request("DELETE", "/v1/me/calendar", json={"device_id": DEV}, headers=hdr).json()["linked"] is False
    h.ring.ring("acc_1")
    assert cl.get(f"/v1/me/ring?d={DEV}").json()["ring"] is True
    cl.post("/v1/me/ring/found", json={"device_id": DEV}, headers=hdr)
    assert cl.get(f"/v1/me/ring?d={DEV}").json()["ring"] is False
    page = cl.get(f"/me/where?d={DEV}")
    assert page.status_code == 200 and "Share my location" in page.text and "<script src=\"/static/soul-where.js\">" in page.text
    assert "<script>" not in page.text and "© OpenStreetMap" in page.text
    assert cl.get("/static/soul-where.js").text.startswith("(() =>")
    acc.s = _Sess("acc_intruder")
    assert cl.post("/v1/me/location", json={"device_id": DEV, "lat": 1, "lon": 2}, headers=hdr).status_code == 404
    assert cl.get("/me/where?d=" + DEV).status_code == 404


def test_navigate_tool_plans_and_pushes_nav_start(tmp_path, monkeypatch):
    from mcp.client import Client
    from _connector_kit import StubGateway, FakeClock, make_service
    from suflet_ai.accounts import Database
    from suflet_ai.mcp_remote import ConnectorCaps, ConnectorCtx, GatewayAdapter, build_connector
    c = Clock()
    h = _hub(c)
    monkeypatch.setattr(apps_mod, "_hub", h)
    clock = FakeClock()
    svc = make_service(tmp_path, clock)
    gw = StubGateway()
    gw.add_device(DEV, "a_owner", lang="en")
    ctx = ConnectorCtx(account_id="a_owner", device_id=DEV, scopes=("soul.read", "soul.write"), client_app="claude")
    server = build_connector(svc, lambda: ctx, GatewayAdapter(gw), caps=ConnectorCaps(Database(), clock))

    async def go(args):
        async with Client(server) as cl:
            return await cl.call_tool("navigate_on_soul", args)
    r = asyncio.run(go({"destination": "Ateneu"}))
    out = json.loads(r.content[0].text)
    assert out["ok"] and "share your location" in out["tell_user"]  # no place yet: Maps opens, waits
    assert gw.pushes[-1]["action"] == "nav.start" and gw.pushes[-1]["args"] == {"to": "Ateneu", "mode": "walk"}
    h.maps.set_phone_fix(DEV, *BUC, 15)
    out = json.loads(asyncio.run(go({"destination": "Ateneu", "mode": "bike"})).content[0].text)
    assert out["distance_m"] > 0 and gw.pushes[-1]["args"]["route"].startswith("rt") and gw.pushes[-1]["args"]["mode"] == "bike"
    bad = asyncio.run(go({"destination": "Nowhere at all"}))
    assert bad.is_error and bad.content[0].text.startswith("not_found")
