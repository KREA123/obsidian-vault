"""SOUL Maps, cloud side (docs/11-MAPS.md): where SOUL is, a map it can draw, places and routes.

SOUL has no GPS and no compass (QMI8658 = accelerometer + gyroscope), only Wi-Fi. So:

    location   1. the owner's phone: /me/where "Share my location" (the browser Geolocation API, while the page is
                  open) or a share link from Google / Apple Maps pasted there (parse_share_link)
               2. Wi-Fi geolocation (opt-in, per device): the access points SOUL sees, sent to an MLS-compatible
                  service (beaconDB by default for the pilot; Google Geolocation API for production coverage)
               3. none: the map opens on the last place, says how old it is, and never pretends
    map        the cloud reads OpenStreetMap vector tiles (a self-hosted Protomaps PMTiles basemap: ODbL, no tile
               server, never tile.openstreetmap.org), keeps what a 480 px disc can show (water, parks, roads by
               rank, rail, a few place names), simplifies it to the pixel and packs it as "SMB1" (a few KB)
    places     a Photon-compatible geocoder (komoot Photon, self-hosted; the public one is fair-use only)
    routes     Valhalla (self-hosted, MIT) or OpenRouteService (API key, 2,000 directions a day free; paid plans for
               commercial use) or OSRM; one Route model; the device gets the shape (polyline5) + up to 40 steps
    handoff    deep links for Google Maps / Apple Maps ("Send to phone"): a QR on SOUL + a card on /me

Every provider is an object with one method and an injected `http` function, so the tests run with fakes and no
keys. Nothing here logs a coordinate, an access point or a destination.
"""
from __future__ import annotations

import dataclasses
import gzip
import json
import math
import re
import sqlite3
import struct
import threading
import time
import zlib
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

# ============================================================================ geo math ==

EARTH_R = 6371008.8
TILE = 256
MIN_Z, MAX_Z = 3, 18


def clamp(v: float, a: float, b: float) -> float:
    return a if v < a else b if v > b else v


def world_px(lat: float, lon: float, z: float) -> Tuple[float, float]:
    """Web Mercator: lat/lon -> pixel at zoom z (the world is 256 * 2^z px wide)."""
    lat = clamp(lat, -85.05112878, 85.05112878)
    n = TILE * (2.0 ** z)
    x = (lon + 180.0) / 360.0 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def lat_lon(x: float, y: float, z: float) -> Tuple[float, float]:
    n = TILE * (2.0 ** z)
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(a)))


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing in degrees, 0 = north, clockwise."""
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def encode_polyline(points: Sequence[Tuple[float, float]], precision: int = 5) -> str:
    """Google's encoded polyline (lat, lon pairs)."""
    f = 10 ** precision
    out, plat, plon = [], 0, 0
    for lat, lon in points:
        ilat, ilon = int(round(lat * f)), int(round(lon * f))
        for d in (ilat - plat, ilon - plon):
            v = ~(d << 1) if d < 0 else d << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            out.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(out)


def decode_polyline(s: str, precision: int = 5) -> List[Tuple[float, float]]:
    f = 10 ** precision
    pts, i, lat, lon = [], 0, 0, 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = res = 0
            while True:
                if i >= len(s):
                    raise ValueError("truncated polyline")
                b = ord(s[i]) - 63
                i += 1
                res |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            vals.append(~(res >> 1) if res & 1 else res >> 1)
        lat += vals[0]
        lon += vals[1]
        pts.append((lat / f, lon / f))
    return pts


def simplify(pts: List[Tuple[float, float]], tol: float) -> List[Tuple[float, float]]:
    """Douglas-Peucker (iterative), in the units of the points."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    t2 = tol * tol
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if L2 == 0:
                d2 = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = clamp(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
                d2 = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d2 > best:
                best, bi = d2, i
        if best > t2 and bi > 0:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]


def clip_line(pts: List[Tuple[float, float]], x0: float, y0: float, x1: float, y1: float) -> List[List[Tuple[float, float]]]:
    """Cohen-Sutherland per segment; returns the runs inside the box."""
    def code(x, y):
        return (x < x0) | (x > x1) << 1 | (y < y0) << 2 | (y > y1) << 3

    runs: List[List[Tuple[float, float]]] = []
    cur: List[Tuple[float, float]] = []
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        ca, cb = code(ax, ay), code(bx, by)
        sx, sy, ex, ey = ax, ay, bx, by
        ok = False
        while True:
            if not (ca | cb):
                ok = True
                break
            if ca & cb:
                break
            c = ca or cb
            if c & 8:
                x, y = sx + (ex - sx) * (y1 - sy) / (ey - sy), y1
            elif c & 4:
                x, y = sx + (ex - sx) * (y0 - sy) / (ey - sy), y0
            elif c & 2:
                x, y = x1, sy + (ey - sy) * (x1 - sx) / (ex - sx)
            else:
                x, y = x0, sy + (ey - sy) * (x0 - sx) / (ex - sx)
            if c == ca:
                sx, sy, ca = x, y, code(x, y)
            else:
                ex, ey, cb = x, y, code(x, y)
        if not ok:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
            continue
        if not cur or cur[-1] != (sx, sy):
            if len(cur) > 1:
                runs.append(cur)
            cur = [(sx, sy)]
        cur.append((ex, ey))
        if (ex, ey) != (bx, by):  # left the box
            runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)
    return runs


def clip_poly(pts: List[Tuple[float, float]], x0: float, y0: float, x1: float, y1: float) -> List[Tuple[float, float]]:
    """Sutherland-Hodgman against the box."""
    def cut(poly, inside, inter):
        out = []
        for i in range(len(poly)):
            p, q = poly[i - 1], poly[i]
            if inside(q):
                if not inside(p):
                    out.append(inter(p, q))
                out.append(q)
            elif inside(p):
                out.append(inter(p, q))
        return out

    def ix(xc):
        return lambda p, q: (xc, p[1] + (q[1] - p[1]) * (xc - p[0]) / ((q[0] - p[0]) or 1e-9))

    def iy(yc):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (yc - p[1]) / ((q[1] - p[1]) or 1e-9), yc)

    poly = list(pts)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not poly:
            break
        poly = cut(poly, inside, inter)
    return poly


# ============================================================================ errors ==

class MapsError(Exception):
    """A user-facing failure with a stable code (no_location, no_route, not_found, provider, config, bad_request)."""

    def __init__(self, code: str, msg: str = "", status: int = 400):
        super().__init__(msg or code)
        self.code, self.msg, self.status = code, msg or code, status


Http = Callable[..., Tuple[int, bytes]]  # http(method, url, body=None, headers=None, timeout=8.0) -> (status, bytes)


def urllib_http(method: str, url: str, body: Optional[bytes] = None, headers: Optional[dict] = None,
                timeout: float = 8.0, max_bytes: int = 4 << 20) -> Tuple[int, bytes]:
    """The real transport (production). Bounded size, no redirects followed to other hosts by callers that care."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - https URLs built here
            return r.status, r.read(max_bytes + 1)[:max_bytes]
    except urllib.error.HTTPError as e:
        return e.code, e.read(65536)
    except Exception:  # noqa: BLE001 - the caller maps it to "provider"
        return -1, b""


UA = "SOUL-Cloud/0.4 (+https://soul.example/about; maps)"

# ========================================================================= location ==


@dataclasses.dataclass
class Fix:
    lat: float
    lon: float
    acc_m: float = 50.0
    source: str = "phone"  # phone | link | wifi | manual
    at: float = 0.0
    label: str = ""

    def to_json(self, now: float) -> dict:
        return {"lat": round(self.lat, 6), "lon": round(self.lon, 6), "acc": int(round(self.acc_m)),
                "src": self.source, "age": max(0, int(now - self.at)), "label": self.label[:60]}


def valid_lat_lon(lat: Any, lon: Any) -> bool:
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= la <= 90 and -180 <= lo <= 180 and math.isfinite(la) and math.isfinite(lo) and not (la == 0 and lo == 0)


_NUM = r"(-?\d{1,3}(?:\.\d+)?)"
_LINK_HOSTS = ("google.com", "www.google.com", "maps.google.com", "goo.gl", "maps.app.goo.gl", "maps.apple.com",
               "www.openstreetmap.org", "openstreetmap.org", "osm.org")
_SHORT_HOSTS = ("goo.gl", "maps.app.goo.gl")


def parse_share_link(text: str, resolve: Optional[Callable[[str], Optional[str]]] = None) -> Tuple[Optional[Fix], str]:
    """A place shared from a phone: returns (fix or None, a place query or "").

    Google Maps:  .../@44.43,26.10,15z  ·  ?q=44.43,26.10  ·  ?query=..  ·  !3d44.43!4d26.10  ·  /place/<name>/@..
    Apple Maps:   maps.apple.com/?ll=44.43,26.10&q=Name  ·  ?daddr=  ·  ?address=
    OSM:          openstreetmap.org/#map=15/44.43/26.10  ·  ?mlat=&mlon=
    geo: URIs:    geo:44.43,26.10?q=...
    Short links (maps.app.goo.gl/…) need one redirect: `resolve(url)` returns the Location header (only those two
    hosts are ever fetched; the result is parsed, never fetched again)."""
    s = (text or "").strip()
    m = re.search(r"(geo:[^\s]+|https?://[^\s]+)", s)
    if not m:
        m2 = re.fullmatch(rf"\s*{_NUM}\s*,\s*{_NUM}\s*", s)
        if m2 and valid_lat_lon(m2.group(1), m2.group(2)):
            return Fix(float(m2.group(1)), float(m2.group(2)), 30, "link"), ""
        return None, s[:120]
    url = m.group(1).rstrip(").,;")
    if url.startswith("geo:"):
        g = re.match(rf"geo:{_NUM},{_NUM}", url)
        q = parse_qs(urlparse(url.replace("geo:", "geo://", 1)).query).get("q", [""])[0]
        if g and valid_lat_lon(g.group(1), g.group(2)):
            return Fix(float(g.group(1)), float(g.group(2)), 30, "link", label=_label_of(q)), ""
        return None, _label_of(q)
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in _LINK_HOSTS):
        return None, ""
    if host in _SHORT_HOSTS:
        if resolve is None:
            return None, ""
        nxt = resolve(url)
        if not nxt or nxt == url:
            return None, ""
        return parse_share_link(nxt, None)
    full = unquote(url)
    qs = parse_qs(u.query)
    label = ""
    pm = re.search(r"/place/([^/@]+)", u.path)
    if pm:
        label = _label_of(pm.group(1))
    for key in ("ll", "q", "query", "daddr", "destination", "sll", "center"):
        v = qs.get(key, [""])[0]
        c = re.fullmatch(rf"\s*{_NUM}\s*,\s*{_NUM}\s*", v)
        if c and valid_lat_lon(c.group(1), c.group(2)):
            name = _label_of(qs.get("q", [""])[0]) if key != "q" else label
            return Fix(float(c.group(1)), float(c.group(2)), 30, "link", label=name or label), ""
    if "mlat" in qs and "mlon" in qs and valid_lat_lon(qs["mlat"][0], qs["mlon"][0]):
        return Fix(float(qs["mlat"][0]), float(qs["mlon"][0]), 30, "link", label=label), ""
    d = re.search(rf"!3d{_NUM}!4d{_NUM}", full)
    if d and valid_lat_lon(d.group(1), d.group(2)):
        return Fix(float(d.group(1)), float(d.group(2)), 30, "link", label=label), ""
    a = re.search(rf"@{_NUM},{_NUM}", full)
    if a and valid_lat_lon(a.group(1), a.group(2)):
        return Fix(float(a.group(1)), float(a.group(2)), 60, "link", label=label), ""
    o = re.search(rf"#map=\d+/{_NUM}/{_NUM}", full)
    if o and valid_lat_lon(o.group(1), o.group(2)):
        return Fix(float(o.group(1)), float(o.group(2)), 60, "link", label=label), ""
    for key in ("q", "address", "daddr", "destination", "query"):
        v = qs.get(key, [""])[0]
        if v:
            return None, _label_of(v)
    return None, label


def _label_of(s: str) -> str:
    return re.sub(r"\s+", " ", unquote(s or "").replace("+", " ")).strip()[:80]


class LocationBook:
    """The last known place of each SOUL. One row per device, kept 24 h (then forgotten: a place is personal).
    A new fix replaces an older one unless it is much less precise and the old one is fresh."""

    TTL = 24 * 3600

    def __init__(self, path: str = ":memory:", clock: Callable[[], float] = time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS fixes(device_id TEXT PRIMARY KEY, lat REAL, lon REAL, acc REAL, "
                        "src TEXT, at REAL, label TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS wifi_optin(device_id TEXT PRIMARY KEY, on_ INTEGER)")
        self.db.commit()

    def put(self, device_id: str, fix: Fix) -> Fix:
        fix.at = fix.at or self.clock()
        with self.lock:
            old = self.get(device_id)
            if old and old.acc_m * 4 < fix.acc_m and fix.at - old.at < 600:
                return old  # a Wi-Fi guess does not overwrite a fresh phone fix
            self.db.execute("INSERT OR REPLACE INTO fixes VALUES (?,?,?,?,?,?,?)",
                            (device_id, fix.lat, fix.lon, fix.acc_m, fix.source, fix.at, fix.label[:80]))
            self.db.commit()
        return fix

    def get(self, device_id: str, max_age: Optional[float] = None) -> Optional[Fix]:
        r = self.db.execute("SELECT lat, lon, acc, src, at, label FROM fixes WHERE device_id=?", (device_id,)).fetchone()
        if not r:
            return None
        age = self.clock() - r[4]
        if age > self.TTL or (max_age is not None and age > max_age):
            if age > self.TTL:
                self.forget(device_id)
            return None
        return Fix(r[0], r[1], r[2], r[3], r[4], r[5] or "")

    def forget(self, device_id: str) -> None:
        self.db.execute("DELETE FROM fixes WHERE device_id=?", (device_id,))
        self.db.commit()

    def wifi_allowed(self, device_id: str) -> bool:
        r = self.db.execute("SELECT on_ FROM wifi_optin WHERE device_id=?", (device_id,)).fetchone()
        return bool(r and r[0])

    def set_wifi_allowed(self, device_id: str, on: bool) -> None:
        self.db.execute("INSERT OR REPLACE INTO wifi_optin VALUES (?,?)", (device_id, 1 if on else 0))
        self.db.commit()


# ------------------------------------------------------------------ Wi-Fi geolocation --

_MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")


def usable_aps(aps: Iterable[dict]) -> List[dict]:
    """The access points a geolocation service may be asked about: real (globally administered) MACs, not the
    owner's opted-out networks (SSID ending in _nomap), not hidden/phone hotspots; strongest 12."""
    out = []
    for a in aps or []:
        if not isinstance(a, dict):
            continue
        mac = str(a.get("mac", "")).lower().replace("-", ":")
        ssid = str(a.get("ssid", ""))
        if not _MAC.match(mac) or int(mac[:2], 16) & 0x02 or ssid.endswith("_nomap") or mac == "00:00:00:00:00:00":
            continue
        try:
            rssi = int(a.get("rssi", -90))
        except (TypeError, ValueError):
            continue
        out.append({"macAddress": mac, "signalStrength": max(-120, min(0, rssi))})
    out.sort(key=lambda x: -x["signalStrength"])
    return out[:12]


class WifiGeolocator:
    """The Google Geolocation API request format, which Ichnaea / beaconDB / Google all accept.

        beaconDB (pilot default):  https://api.beacondb.net/v1/geolocate          (no key; fair use, < 1k users;
                                    experimental coverage — it rebuilds Mozilla's retired MLS from scratch)
        Google (production):       https://www.googleapis.com/geolocation/v1/geolocate?key=…   (10k/month free,
                                    then $5 per 1,000; lat/lng may be cached at most 30 days)
    Combain stopped outdoor Wi-Fi positioning in 2020; HERE Positioning works the same way with its own key."""

    def __init__(self, url: str = "https://api.beacondb.net/v1/geolocate", key: str = "", http: Http = urllib_http,
                 name: str = "beacondb"):
        self.url, self.key, self.http, self.name = url, key, http, name

    def locate(self, aps: Iterable[dict]) -> Optional[Fix]:
        wifi = usable_aps(aps)
        if len(wifi) < 2:  # the services refuse one AP on purpose (privacy): so do we
            raise MapsError("too_few_aps", "SOUL needs to see at least two Wi-Fi networks to guess a place", 422)
        url = self.url + (("&" if "?" in self.url else "?") + "key=" + quote(self.key) if self.key else "")
        body = json.dumps({"considerIp": False, "wifiAccessPoints": wifi}).encode()
        st, raw = self.http("POST", url, body, {"content-type": "application/json", "user-agent": UA}, 6.0)
        if st == 404:
            return None  # "not found": no idea where these networks are
        if st != 200:
            raise MapsError("provider", f"Wi-Fi location service answered {st}", 502)
        try:
            j = json.loads(raw)
            lat, lon = j["location"]["lat"], j["location"]["lng"]
            acc = float(j.get("accuracy", 150))
        except (ValueError, KeyError, TypeError):
            raise MapsError("provider", "Wi-Fi location service sent something unreadable", 502)
        if not valid_lat_lon(lat, lon):
            return None
        return Fix(float(lat), float(lon), acc, "wifi")


# ============================================================================== tiles ==
# ---- protobuf (just what Mapbox Vector Tiles need) --------------------------------------

def _varint(b: bytes, i: int) -> Tuple[int, int]:
    shift = res = 0
    while True:
        if i >= len(b):
            raise ValueError("truncated varint")
        c = b[i]
        i += 1
        res |= (c & 0x7F) << shift
        if c < 0x80:
            return res, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


def _fields(b: bytes) -> Iterable[Tuple[int, int, Any]]:
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 2:
            n, i = _varint(b, i)
            if i + n > len(b):
                raise ValueError("truncated field")
            v, i = b[i:i + n], i + n
        elif wt == 1:
            v, i = b[i:i + 8], i + 8
        elif wt == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"wire type {wt}")
        yield f, wt, v


def _packed(b: bytes) -> List[int]:
    out, i = [], 0
    while i < len(b):
        v, i = _varint(b, i)
        out.append(v)
    return out


def _zz(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def _value(b: bytes) -> Any:
    for f, wt, v in _fields(b):
        if f == 1:
            return v.decode("utf-8", "replace")
        if f == 2:
            return struct.unpack("<f", v)[0]
        if f == 3:
            return struct.unpack("<d", v)[0]
        if f in (4, 5):
            return v
        if f == 6:
            return _zz(v)
        if f == 7:
            return bool(v)
    return None


def _geometry(cmds: List[int]) -> List[List[Tuple[int, int]]]:
    """MVT command stream -> rings / lines / points in tile units."""
    parts: List[List[Tuple[int, int]]] = []
    cur: List[Tuple[int, int]] = []
    x = y = i = 0
    while i < len(cmds):
        c = cmds[i]
        i += 1
        cid, n = c & 7, c >> 3
        if cid == 1:  # MoveTo
            for _ in range(n):
                x += _zz(cmds[i])
                y += _zz(cmds[i + 1])
                i += 2
                if cur:
                    parts.append(cur)
                cur = [(x, y)]
        elif cid == 2:  # LineTo
            for _ in range(n):
                x += _zz(cmds[i])
                y += _zz(cmds[i + 1])
                i += 2
                cur.append((x, y))
        elif cid == 7:  # ClosePath
            if cur:
                cur.append(cur[0])
        else:
            raise ValueError("bad MVT command")
    if cur:
        parts.append(cur)
    return parts


def decode_mvt(data: bytes) -> Dict[str, dict]:
    """A Mapbox Vector Tile -> {layer: {"extent": 4096, "features": [{"type": 1|2|3, "geom": [...], "props": {}}]}}"""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    layers: Dict[str, dict] = {}
    for f, wt, v in _fields(data):
        if f != 3 or wt != 2:
            continue
        name, extent, keys, vals, feats = "", 4096, [], [], []
        for lf, lwt, lv in _fields(v):
            if lf == 1:
                name = lv.decode("utf-8", "replace")
            elif lf == 5:
                extent = lv
            elif lf == 3:
                keys.append(lv.decode("utf-8", "replace"))
            elif lf == 4:
                vals.append(_value(lv))
            elif lf == 2:
                feats.append(lv)
        out = []
        for fb in feats:
            typ, tags, geom = 0, [], []
            for ff, fwt, fv in _fields(fb):
                if ff == 2:
                    tags = _packed(fv)
                elif ff == 3:
                    typ = fv
                elif ff == 4:
                    geom = _packed(fv)
            props = {}
            for k in range(0, len(tags) - 1, 2):
                if tags[k] < len(keys) and tags[k + 1] < len(vals):
                    props[keys[tags[k]]] = vals[tags[k + 1]]
            try:
                out.append({"type": typ, "geom": _geometry(geom), "props": props})
            except (IndexError, ValueError):
                continue
        layers[name] = {"extent": extent, "features": out}
    return layers


# ---- PMTiles v3 (a single-file tile archive read with range requests) -------------------

def zxy_to_tileid(z: int, x: int, y: int) -> int:
    acc = sum(4 ** i for i in range(z))
    n = 1 << z
    d, s, tx, ty = 0, n >> 1, x, y
    while s > 0:
        rx = 1 if tx & s else 0
        ry = 1 if ty & s else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                tx, ty = s - 1 - tx, s - 1 - ty
            tx, ty = ty, tx
        s >>= 1
    return acc + d


def _decompress(b: bytes, kind: int) -> bytes:
    if kind in (0, 1):
        return b
    if kind == 2:
        return gzip.decompress(b)
    raise MapsError("config", "PMTiles compression not supported (use gzip or none)", 500)


class PMTiles:
    """Reads tiles from a PMTiles v3 archive through `read(offset, length) -> bytes` (a local file, or HTTP range
    requests to our own object storage). Directories are cached."""

    def __init__(self, read: Callable[[int, int], bytes]):
        self.read = read
        h = read(0, 127)
        if len(h) < 127 or h[:7] != b"PMTiles" or h[7] != 3:
            raise MapsError("config", "not a PMTiles v3 archive", 500)
        (self.root_off, self.root_len, self.meta_off, self.meta_len, self.leaf_off, self.leaf_len, self.data_off,
         self.data_len) = struct.unpack("<8Q", h[8:72])
        self.internal_comp, self.tile_comp, self.tile_type = h[97], h[98], h[99]
        self.min_z, self.max_z = h[100], h[101]
        self._dirs: Dict[Tuple[int, int], List[Tuple[int, int, int, int]]] = {}

    @staticmethod
    def from_file(path: str) -> "PMTiles":
        f = open(path, "rb")  # noqa: SIM115 - kept open for the life of the process
        lock = threading.Lock()

        def read(off: int, n: int) -> bytes:
            with lock:
                f.seek(off)
                return f.read(n)
        return PMTiles(read)

    def _dir(self, off: int, n: int) -> List[Tuple[int, int, int, int]]:
        key = (off, n)
        if key not in self._dirs:
            b = _decompress(self.read(off, n), self.internal_comp)
            cnt, i = _varint(b, 0)
            ids, runs, lens, offs = [], [], [], []
            last = 0
            for _ in range(cnt):
                v, i = _varint(b, i)
                last += v
                ids.append(last)
            for _ in range(cnt):
                v, i = _varint(b, i)
                runs.append(v)
            for _ in range(cnt):
                v, i = _varint(b, i)
                lens.append(v)
            for k in range(cnt):
                v, i = _varint(b, i)
                offs.append(offs[k - 1] + lens[k - 1] if v == 0 and k > 0 else v - 1)
            self._dirs[key] = list(zip(ids, runs, lens, offs))
            if len(self._dirs) > 256:
                self._dirs.pop(next(iter(self._dirs)))
        return self._dirs[key]

    def tile(self, z: int, x: int, y: int) -> Optional[bytes]:
        tid = zxy_to_tileid(z, x, y)
        off, n = self.root_off, self.root_len
        for _ in range(4):
            entries = self._dir(off, n)
            lo, hi, hit = 0, len(entries) - 1, None
            while lo <= hi:  # the last entry with id <= tid
                mid = (lo + hi) // 2
                if entries[mid][0] <= tid:
                    hit, lo = entries[mid], mid + 1
                else:
                    hi = mid - 1
            if hit is None:
                return None
            eid, run, ln, eoff = hit
            if run == 0:  # a leaf directory
                off, n = self.leaf_off + eoff, ln
                continue
            if tid >= eid + run:
                return None
            return _decompress(self.read(self.data_off + eoff, ln), self.tile_comp)
        return None


def write_pmtiles(tiles: Dict[Tuple[int, int, int], bytes]) -> bytes:
    """A small PMTiles v3 writer (no leaf directories, gzip directories, uncompressed MVT): for tests and for the
    tiny demo extract the simulator ships. Real basemaps come from `pmtiles extract` on the Protomaps build."""
    items = sorted((zxy_to_tileid(z, x, y), b) for (z, x, y), b in tiles.items())
    data, ids, lens, offs = b"", [], [], []
    for tid, b in items:
        ids.append(tid)
        offs.append(len(data))
        lens.append(len(b))
        data += b

    def uv(v: int) -> bytes:
        out = bytearray()
        while v >= 0x80:
            out.append((v & 0x7F) | 0x80)
            v >>= 7
        out.append(v)
        return bytes(out)
    d = bytearray(uv(len(items)))
    last = 0
    for t in ids:
        d += uv(t - last)
        last = t
    for _ in ids:
        d += uv(1)
    for n in lens:
        d += uv(n)
    for o in offs:
        d += uv(o + 1)
    root = gzip.compress(bytes(d))
    meta = gzip.compress(b"{}")
    root_off = 127
    meta_off = root_off + len(root)
    data_off = meta_off + len(meta)
    zs = [k[0] for k in tiles] or [0]
    h = bytearray(b"PMTiles") + bytes([3])
    h += struct.pack("<8Q", root_off, len(root), meta_off, len(meta), 0, 0, data_off, len(data))
    h += struct.pack("<3Q", len(items), len(items), len(items))
    h += bytes([1, 2, 1, 1, min(zs), max(zs)])  # clustered, gzip dirs, no tile compression, MVT
    h += struct.pack("<4i", -1800000000, -850000000, 1800000000, 850000000)
    h += bytes([max(zs)]) + struct.pack("<2i", 0, 0)
    h = bytes(h).ljust(127, b"\0")
    return h + root + meta + data


def encode_mvt(layers: Dict[str, List[dict]], extent: int = 4096) -> bytes:
    """The other half of decode_mvt (tests, demo data): features {"type": 1|2|3, "geom": [[(x, y)...]], "props"}."""
    def uv(v: int) -> bytes:
        out = bytearray()
        while v >= 0x80:
            out.append((v & 0x7F) | 0x80)
            v >>= 7
        out.append(v)
        return bytes(out)

    def fld(f: int, wt: int, payload: Any) -> bytes:
        if wt == 0:
            return uv(f << 3) + uv(payload)
        return uv(f << 3 | 2) + uv(len(payload)) + payload

    def zz(n: int) -> int:
        return (n << 1) ^ (n >> 63)
    tile = b""
    for name, feats in layers.items():
        keys: List[str] = []
        vals: List[Any] = []
        body = fld(15, 0, 2) + fld(1, 2, name.encode()) + fld(5, 0, extent)
        fb_all = b""
        for ft in feats:
            tags = []
            for k, v in (ft.get("props") or {}).items():
                if k not in keys:
                    keys.append(k)
                if v not in vals:
                    vals.append(v)
                tags += [keys.index(k), vals.index(v)]
            cmds, cx, cy = [], 0, 0
            for part in ft["geom"]:
                closed = ft["type"] == 3 and len(part) > 2 and part[0] == part[-1]
                pts = part[:-1] if closed else part
                x, y = pts[0]
                cmds += [1 | 1 << 3, zz(x - cx), zz(y - cy)]
                cx, cy = x, y
                if len(pts) > 1:
                    cmds.append(2 | (len(pts) - 1) << 3)
                    for x, y in pts[1:]:
                        cmds += [zz(x - cx), zz(y - cy)]
                        cx, cy = x, y
                if closed:
                    cmds.append(7 | 1 << 3)
            fb = fld(3, 0, ft["type"]) + fld(2, 2, b"".join(uv(t) for t in tags)) + fld(4, 2, b"".join(uv(c) for c in cmds))
            fb_all += fld(2, 2, fb)
        for k in keys:
            body += fld(3, 2, k.encode())
        for v in vals:
            if isinstance(v, str):
                vb = fld(1, 2, v.encode())
            elif isinstance(v, bool):
                vb = fld(7, 0, int(v))
            elif isinstance(v, int):
                vb = fld(6, 0, zz(v)) if v < 0 else fld(5, 0, v)
            else:
                vb = uv(3 << 3 | 1) + struct.pack("<d", float(v))
            body += fld(4, 2, vb)
        body += fb_all
        tile += fld(3, 2, body)
    return tile


# ---- what SOUL draws ------------------------------------------------------------------

# device classes (firmware MapCore.h keeps the same numbers)
C_WATER, C_PARK, C_ROAD_MAJOR, C_ROAD_MID, C_ROAD_MINOR, C_PATH, C_RAIL, C_BUILDING, C_PLACE, C_POI = range(1, 11)
K_LINE, K_POLY, K_POINT = 1, 2, 3

_MAJOR = {"highway", "motorway", "trunk", "primary"}
_MID = {"major_road", "secondary", "tertiary", "medium_road"}
_MINOR = {"minor_road", "residential", "service", "unclassified", "living_street", "minor"}
_PATH = {"path", "footway", "cycleway", "pedestrian", "steps", "track", "other"}


def classify(layer: str, props: dict, z: int) -> Optional[int]:
    """Protomaps basemap (v4) / OpenMapTiles layer + kind -> one of SOUL's ten classes, or None (left out)."""
    kind = str(props.get("kind") or props.get("class") or props.get("pmap:kind") or "")
    if layer in ("water", "waterway", "ocean"):
        return C_WATER
    if layer in ("landuse", "landcover", "park", "natural"):
        return C_PARK if kind in ("park", "garden", "forest", "wood", "grass", "nature_reserve", "cemetery",
                                  "pitch", "playground", "recreation_ground", "meadow", "national_park") else None
    if layer in ("roads", "transportation", "road"):
        if kind in ("rail", "railway", "transit"):
            return C_RAIL if z >= 12 else None
        if kind in _MAJOR:
            return C_ROAD_MAJOR
        if kind in _MID:
            return C_ROAD_MID if z >= 11 else None
        if kind in _MINOR:
            return C_ROAD_MINOR if z >= 14 else None
        if kind in _PATH:
            return C_PATH if z >= 16 else None
        return C_ROAD_MINOR if z >= 15 else None
    if layer in ("transit",):
        return C_RAIL if z >= 12 else None
    if layer in ("buildings", "building"):
        return C_BUILDING if z >= 17 else None
    if layer in ("places", "place"):
        return C_PLACE
    if layer in ("pois", "poi"):
        return C_POI if z >= 16 else None
    return None


@dataclasses.dataclass
class MapFeature:
    cls: int
    kind: int
    pts: List[Tuple[float, float]]  # bundle pixels
    label: str = ""


BUNDLE_SIZE = 960      # the area sent: the 480 px screen + one screen of panning room in each direction / 2
BUNDLE_MAX_BYTES = 24 * 1024
BUNDLE_MAX_FEATURES = 600


def encode_bundle(z: int, ox: int, oy: int, w: int, h: int, feats: List[MapFeature]) -> bytes:
    """SMB1: the format firmware/lib/Suflet/src/MapCore.cpp decodes.

        "SMB1" u8 version=1 u8 z u16 count u32 originX u32 originY u16 w u16 h       (little endian, 20 bytes)
        per feature: u8 cls u8 kind u16 npts, then npts x (zigzag varint dx, dy) from the previous point
                     (the first from (0, 0)); a point (kind 3) adds u8 len + UTF-8 label
    Coordinates are whole bundle pixels (0..w, 0..h), world pixel = origin + p."""
    out = bytearray(b"SMB1")
    out += struct.pack("<BBHIIHH", 1, z, 0, ox & 0xFFFFFFFF, oy & 0xFFFFFFFF, w, h)

    def uv(v: int) -> None:
        while v >= 0x80:
            out.append((v & 0x7F) | 0x80)
            v >>= 7
        out.append(v)

    n = 0
    for f in feats:
        pts = [(int(round(x)), int(round(y))) for x, y in f.pts]
        dedup = [pts[0]] if pts else []
        for p in pts[1:]:
            if p != dedup[-1]:
                dedup.append(p)
        if (f.kind == K_LINE and len(dedup) < 2) or (f.kind == K_POLY and len(dedup) < 3) or not dedup:
            continue
        if len(dedup) > 65535:
            dedup = dedup[:65535]
        mark = len(out)
        out += struct.pack("<BBH", f.cls, f.kind, len(dedup))
        px = py = 0
        for x, y in dedup:
            dx, dy = x - px, y - py
            uv((dx << 1) ^ (dx >> 31))
            uv((dy << 1) ^ (dy >> 31))
            px, py = x, y
        if f.kind == K_POINT:
            lb = f.label.encode("utf-8")[:40].decode("utf-8", "ignore").encode("utf-8")  # never cut a character
            out.append(len(lb))
            out += lb
        if len(out) > BUNDLE_MAX_BYTES:
            del out[mark:]
            break
        n += 1
    struct.pack_into("<H", out, 6, n)
    return bytes(out)


def decode_bundle(b: bytes) -> dict:
    """The reverse (tests, the web prototype's fixture)."""
    if b[:4] != b"SMB1":
        raise ValueError("not SMB1")
    ver, z, n, ox, oy, w, h = struct.unpack_from("<BBHIIHH", b, 4)
    i, feats = 20, []
    for _ in range(n):
        cls, kind, npts = struct.unpack_from("<BBH", b, i)
        i += 4
        pts, x, y = [], 0, 0
        for _ in range(npts):
            dx, i = _varint(b, i)
            dy, i = _varint(b, i)
            x += _zz(dx)
            y += _zz(dy)
            pts.append((x, y))
        label = ""
        if kind == K_POINT:
            ln = b[i]
            label = b[i + 1:i + 1 + ln].decode("utf-8")
            i += 1 + ln
        feats.append({"cls": cls, "kind": kind, "pts": pts, "label": label})
    return {"v": ver, "z": z, "origin": (ox, oy), "w": w, "h": h, "features": feats}


class TileSource:
    """Where the vector tiles come from: `tile(z, x, y) -> MVT bytes or None`."""

    max_z = 15

    def tile(self, z: int, x: int, y: int) -> Optional[bytes]:  # pragma: no cover - interface
        raise NotImplementedError


class PMTilesSource(TileSource):
    """A self-hosted Protomaps basemap (`pmtiles extract` of the planet build for the regions sold; ODbL:
    "© OpenStreetMap" on the device's map screen and in docs/11)."""

    def __init__(self, archive: PMTiles):
        self.pm = archive
        self.max_z = archive.max_z

    def tile(self, z: int, x: int, y: int) -> Optional[bytes]:
        return self.pm.tile(z, x, y)


def build_bundle(src: TileSource, lat: float, lon: float, z: int, size: int = BUNDLE_SIZE) -> bytes:
    """The SMB1 bundle centred on lat/lon at zoom z (3..18): tiles from `src` (over-zoomed past its max zoom),
    classified, clipped to the area, simplified to 0.7 px, ranked (water and parks first, then roads by rank, places
    last so the device draws labels on top), capped."""
    z = int(clamp(z, MIN_Z, MAX_Z))
    cx, cy = world_px(lat, lon, z)
    ox, oy = int(cx - size / 2), int(cy - size / 2)
    tz = min(z, src.max_z)
    scale = 2 ** (z - tz)                       # world px at z per world px at tz
    tile_px = TILE * scale                       # one source tile in bundle px
    tx0, ty0 = int(ox // tile_px), int(oy // tile_px)
    tx1, ty1 = int((ox + size) // tile_px), int((oy + size) // tile_px)
    n = 1 << tz
    feats: List[MapFeature] = []
    seen_labels = set()
    for ty in range(max(0, ty0), min(n - 1, ty1) + 1):
        for tx in range(tx0, tx1 + 1):
            raw = src.tile(tz, tx % n, ty)
            if not raw:
                continue
            try:
                layers = decode_mvt(raw)
            except (ValueError, OSError):
                continue
            for lname, layer in layers.items():
                k = tile_px / layer["extent"]
                bx, by = tx * tile_px - ox, ty * tile_px - oy
                for ft in layer["features"]:
                    cls = classify(lname, ft["props"], z)
                    if cls is None:
                        continue
                    for part in ft["geom"]:
                        pts = [(bx + x * k, by + y * k) for x, y in part]
                        if ft["type"] == 1 or cls in (C_PLACE, C_POI):
                            if cls not in (C_PLACE, C_POI) or ft["type"] != 1:
                                continue
                            x, y = pts[0]
                            name = str(ft["props"].get("name") or "")
                            if not name or not (0 <= x <= size and 0 <= y <= size) or name in seen_labels:
                                continue
                            seen_labels.add(name)
                            feats.append(MapFeature(cls, K_POINT, [(x, y)], name))
                        elif ft["type"] == 2:
                            for run in clip_line(pts, -2, -2, size + 2, size + 2):
                                run = simplify(run, 0.7)
                                if len(run) >= 2:
                                    feats.append(MapFeature(cls, K_LINE, run))
                        elif ft["type"] == 3:
                            poly = clip_poly(pts, -2, -2, size + 2, size + 2)
                            poly = simplify(poly, 0.7) if len(poly) > 3 else poly
                            if len(poly) >= 3 and _area(poly) > 6:
                                feats.append(MapFeature(cls, K_POLY, poly))
    order = {C_WATER: 0, C_PARK: 1, C_BUILDING: 2, C_PATH: 3, C_ROAD_MINOR: 4, C_RAIL: 5, C_ROAD_MID: 6,
             C_ROAD_MAJOR: 7, C_POI: 8, C_PLACE: 9}
    feats.sort(key=lambda f: order.get(f.cls, 5))
    if len(feats) > BUNDLE_MAX_FEATURES:  # drop the least important first (minor roads, paths, buildings)
        keep = [f for f in feats if f.cls not in (C_PATH, C_BUILDING, C_POI)]
        feats = keep[:BUNDLE_MAX_FEATURES]
    return encode_bundle(z, ox, oy, size, size, feats)


def _area(poly: List[Tuple[float, float]]) -> float:
    a = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2


# ============================================================================ places ==

@dataclasses.dataclass
class Place:
    name: str
    lat: float
    lon: float
    detail: str = ""  # street, city

    def to_json(self) -> dict:
        return {"name": self.name[:60], "lat": round(self.lat, 6), "lon": round(self.lon, 6), "detail": self.detail[:80]}


class PhotonGeocoder:
    """komoot Photon (OSM data, Apache 2.0): self-hosted in production; https://photon.komoot.io is fair use only.
    Results are biased toward SOUL's last place."""

    def __init__(self, base: str = "https://photon.komoot.io", http: Http = urllib_http):
        self.base, self.http = base.rstrip("/"), http

    def search(self, text: str, near: Optional[Fix] = None, lang: str = "en", limit: int = 5) -> List[Place]:
        q = {"q": text[:120], "limit": str(limit), "lang": lang if lang in ("en", "de", "fr", "it") else "default"}
        if near:
            q.update(lat=f"{near.lat:.4f}", lon=f"{near.lon:.4f}")
        st, raw = self.http("GET", f"{self.base}/api/?{urlencode(q)}", None, {"user-agent": UA}, 6.0)
        if st != 200:
            raise MapsError("provider", f"place search answered {st}", 502)
        try:
            j = json.loads(raw)
        except ValueError:
            raise MapsError("provider", "place search sent something unreadable", 502)
        out = []
        for f in j.get("features", [])[:limit]:
            try:
                lon, lat = f["geometry"]["coordinates"][:2]
            except (KeyError, TypeError, ValueError):
                continue
            p = f.get("properties", {})
            name = p.get("name") or " ".join(x for x in (p.get("street"), p.get("housenumber")) if x) or text
            detail = ", ".join(x for x in (p.get("street") if p.get("name") else None, p.get("city") or p.get("county"))
                               if x)
            if valid_lat_lon(lat, lon):
                out.append(Place(str(name), float(lat), float(lon), detail))
        return out


# ============================================================================ routes ==

# maneuver types, shared with the firmware (MapCore.h: NavTurn)
TURNS = ("depart", "straight", "slight_left", "left", "sharp_left", "slight_right", "right", "sharp_right", "uturn",
         "roundabout", "arrive", "ferry")
MODES = ("walk", "bike", "car")


@dataclasses.dataclass
class Step:
    turn: str
    dist_m: float      # from this maneuver to the next
    idx: int           # index into Route.points where the maneuver is
    street: str = ""
    exit: int = 0      # roundabout exit


@dataclasses.dataclass
class Route:
    points: List[Tuple[float, float]]
    dist_m: float
    dur_s: float
    steps: List[Step]
    mode: str = "walk"
    to: str = ""
    to_lat: float = 0.0
    to_lon: float = 0.0
    provider: str = ""
    id: str = ""
    made: float = 0.0

    def device_json(self, max_steps: int = 40) -> dict:
        """What SOUL gets: the shape as polyline5 (simplified to ~3 m), the steps re-indexed onto it."""
        pts = self.points
        if len(pts) > 2:
            # simplify in metres on a local plane, keep every maneuver point
            lat0 = math.radians(pts[0][0])
            proj = [(p[1] * 111320 * math.cos(lat0), p[0] * 110540) for p in pts]
            keep_idx = {s.idx for s in self.steps}
            kept = simplify(proj, 3.0)
            kept_set = set(kept)
            idx_map, out = {}, []
            for i, q in enumerate(proj):
                if q in kept_set or i in keep_idx:
                    idx_map[i] = len(out)
                    out.append(pts[i])
                    kept_set.discard(q)
            steps = []
            for s in self.steps[:max_steps]:
                j = max(k for k in idx_map if k <= s.idx) if idx_map else 0
                steps.append([TURNS.index(s.turn) if s.turn in TURNS else 1, int(round(s.dist_m)), idx_map.get(j, 0),
                              s.street[:40], s.exit])
            pts_out = out
        else:
            pts_out = pts
            steps = [[TURNS.index(s.turn) if s.turn in TURNS else 1, int(round(s.dist_m)), s.idx, s.street[:40], s.exit]
                     for s in self.steps[:max_steps]]
        return {"id": self.id, "to": self.to[:60], "mode": self.mode, "dist": int(round(self.dist_m)),
                "dur": int(round(self.dur_s)), "shape": encode_polyline(pts_out), "steps": steps,
                "dest": [round(self.to_lat, 6), round(self.to_lon, 6)], "src": self.provider}


def _turn_from_modifier(typ: str, mod: str) -> str:
    """OSRM / ORS words -> TURNS."""
    typ, mod = (typ or "").lower(), (mod or "").lower().replace(" ", "_")
    if typ in ("depart",):
        return "depart"
    if typ in ("arrive",):
        return "arrive"
    if "roundabout" in typ or "rotary" in typ:
        return "roundabout"
    if mod in ("uturn", "u-turn"):
        return "uturn"
    if mod in TURNS:
        return mod
    return "straight"


class ValhallaRouter:
    """Valhalla /route (self-hosted, MIT; the FOSSGIS demo at valhalla1.openstreetmap.de is for testing only)."""

    COSTING = {"walk": "pedestrian", "bike": "bicycle", "car": "auto"}
    # Valhalla maneuver type numbers -> TURNS
    TYPE = {1: "depart", 2: "depart", 3: "depart", 4: "arrive", 5: "arrive", 6: "arrive", 7: "straight",
            8: "straight", 9: "slight_right", 10: "right", 11: "sharp_right", 12: "uturn", 13: "uturn",
            14: "sharp_left", 15: "left", 16: "slight_left", 17: "straight", 18: "slight_right", 19: "slight_left",
            20: "slight_right", 21: "slight_left", 22: "straight", 23: "slight_right", 24: "slight_left",
            25: "straight", 26: "roundabout", 27: "roundabout", 28: "ferry", 29: "ferry"}

    def __init__(self, base: str, key: str = "", http: Http = urllib_http):
        self.base, self.key, self.http = base.rstrip("/"), key, http

    def route(self, a: Tuple[float, float], b: Tuple[float, float], mode: str, lang: str = "en") -> Route:
        req = {"locations": [{"lat": a[0], "lon": a[1]}, {"lat": b[0], "lon": b[1]}],
               "costing": self.COSTING.get(mode, "pedestrian"), "units": "kilometers",
               "language": "ro-RO" if lang == "ro" else "en-US", "directions_options": {"units": "kilometers"}}
        url = f"{self.base}/route" + (f"?api_key={quote(self.key)}" if self.key else "")
        st, raw = self.http("POST", url, json.dumps(req).encode(), {"content-type": "application/json",
                                                                    "user-agent": UA}, 10.0)
        if st == 400:
            raise MapsError("no_route", "no route between these places", 404)
        if st != 200:
            raise MapsError("provider", f"routing answered {st}", 502)
        try:
            leg = json.loads(raw)["trip"]["legs"][0]
            pts = decode_polyline(leg["shape"], 6)
            steps = []
            for m in leg["maneuvers"]:
                t = self.TYPE.get(int(m.get("type", 8)), "straight")
                streets = m.get("street_names") or m.get("begin_street_names") or []
                steps.append(Step(t, float(m.get("length", 0)) * 1000, int(m.get("begin_shape_index", 0)),
                                  str(streets[0]) if streets else "", int(m.get("roundabout_exit_count", 0) or 0)))
            summ = leg.get("summary", {})
            return Route(pts, float(summ.get("length", 0)) * 1000, float(summ.get("time", 0)), steps, mode,
                         provider="valhalla")
        except (ValueError, KeyError, TypeError, IndexError):
            raise MapsError("provider", "routing sent something unreadable", 502)


class OrsRouter:
    """OpenRouteService v2 directions (GeoJSON). Free key: 2,000 directions a day, 40 a minute; commercial
    volume needs a paid plan or a self-hosted ORS."""

    PROFILE = {"walk": "foot-walking", "bike": "cycling-regular", "car": "driving-car"}
    # ORS instruction types -> TURNS
    TYPE = {0: "left", 1: "right", 2: "sharp_left", 3: "sharp_right", 4: "slight_left", 5: "slight_right",
            6: "straight", 7: "roundabout", 8: "roundabout", 9: "uturn", 10: "arrive", 11: "depart",
            12: "slight_left", 13: "slight_right"}

    def __init__(self, key: str, base: str = "https://api.openrouteservice.org", http: Http = urllib_http):
        self.key, self.base, self.http = key, base.rstrip("/"), http

    def route(self, a: Tuple[float, float], b: Tuple[float, float], mode: str, lang: str = "en") -> Route:
        body = {"coordinates": [[a[1], a[0]], [b[1], b[0]]], "language": "en", "instructions": True,
                "units": "m"}
        st, raw = self.http("POST", f"{self.base}/v2/directions/{self.PROFILE.get(mode, 'foot-walking')}/geojson",
                            json.dumps(body).encode(), {"content-type": "application/json", "authorization": self.key,
                                                        "user-agent": UA}, 10.0)
        if st == 404:
            raise MapsError("no_route", "no route between these places", 404)
        if st == 429:
            raise MapsError("provider", "routing is busy (daily limit); try again later", 503)
        if st != 200:
            raise MapsError("provider", f"routing answered {st}", 502)
        try:
            f = json.loads(raw)["features"][0]
            pts = [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
            seg = f["properties"]["segments"][0]
            steps = [Step(self.TYPE.get(int(s.get("type", 6)), "straight"), float(s.get("distance", 0)),
                          int(s.get("way_points", [0])[0]), "" if s.get("name") in (None, "-") else str(s.get("name")),
                          int(s.get("exit_number", 0) or 0)) for s in seg.get("steps", [])]
            summ = f["properties"].get("summary", {})
            return Route(pts, float(summ.get("distance", seg.get("distance", 0))),
                         float(summ.get("duration", seg.get("duration", 0))), steps, mode, provider="openrouteservice")
        except (ValueError, KeyError, TypeError, IndexError):
            raise MapsError("provider", "routing sent something unreadable", 502)


class OsrmRouter:
    """OSRM /route/v1 (self-hosted, BSD-2). The public demo is 1 request/s and not for products."""

    PROFILE = {"walk": "foot", "bike": "bike", "car": "driving"}

    def __init__(self, base: str, http: Http = urllib_http):
        self.base, self.http = base.rstrip("/"), http

    def route(self, a: Tuple[float, float], b: Tuple[float, float], mode: str, lang: str = "en") -> Route:
        url = (f"{self.base}/route/v1/{self.PROFILE.get(mode, 'foot')}/{a[1]:.6f},{a[0]:.6f};{b[1]:.6f},{b[0]:.6f}"
               "?overview=full&geometries=polyline&steps=true")
        st, raw = self.http("GET", url, None, {"user-agent": UA}, 10.0)
        if st != 200:
            raise MapsError("provider" if st != 400 else "no_route", f"routing answered {st}", 502 if st != 400 else 404)
        try:
            j = json.loads(raw)
            if j.get("code") != "Ok":
                raise MapsError("no_route", "no route between these places", 404)
            r = j["routes"][0]
            pts = decode_polyline(r["geometry"], 5)
            steps, idx = [], 0
            for s in r["legs"][0]["steps"]:
                m = s.get("maneuver", {})
                loc = m.get("location", [0, 0])
                best, bd = idx, 1e18
                for i in range(idx, len(pts)):  # the shape point at the maneuver
                    d = (pts[i][0] - loc[1]) ** 2 + (pts[i][1] - loc[0]) ** 2
                    if d < bd:
                        best, bd = i, d
                    if d > bd * 4 and bd < 1e-9:
                        break
                idx = best
                steps.append(Step(_turn_from_modifier(m.get("type", ""), m.get("modifier", "")),
                                  float(s.get("distance", 0)), idx, str(s.get("name") or ""),
                                  int(m.get("exit", 0) or 0)))
            return Route(pts, float(r.get("distance", 0)), float(r.get("duration", 0)), steps, mode, provider="osrm")
        except MapsError:
            raise
        except (ValueError, KeyError, TypeError, IndexError):
            raise MapsError("provider", "routing sent something unreadable", 502)


# ============================================================================ handoff ==

def phone_links(lat: float, lon: float, name: str = "", mode: str = "walk") -> dict:
    """Deep links that open the route on the owner's phone (no API key; Google's Maps URLs and Apple Maps links)."""
    gm = {"walk": "walking", "bike": "bicycling", "car": "driving"}.get(mode, "walking")
    am = {"walk": "w", "bike": "w", "car": "d"}.get(mode, "w")
    dest = f"{lat:.6f},{lon:.6f}"
    g = "https://www.google.com/maps/dir/?" + urlencode({"api": "1", "destination": dest, "travelmode": gm})
    a = "https://maps.apple.com/?" + urlencode({"daddr": dest, "dirflg": am, **({"q": name[:60]} if name else {})})
    return {"google": g, "apple": a, "geo": f"geo:{dest}?q={quote(dest + (f'({name[:40]})' if name else ''))}"}


# ============================================================================ service ==

class MapsService:
    """The maps side of SOUL Cloud. Providers are optional: a missing one gives a clear `config` error that the
    device shows as "Maps: not set up on this SOUL Cloud" instead of a broken screen."""

    ROUTE_TTL = 6 * 3600
    VIEW_CACHE = 64

    def __init__(self, book: Optional[LocationBook] = None, tiles: Optional[TileSource] = None,
                 router: Any = None, geocoder: Any = None, wifi: Optional[WifiGeolocator] = None,
                 clock: Callable[[], float] = time.time, resolve_short: Optional[Callable[[str], Optional[str]]] = None):
        self.clock = clock
        self.book = book or LocationBook(clock=clock)
        self.tiles, self.router, self.geocoder, self.wifi = tiles, router, geocoder, wifi
        self.resolve_short = resolve_short
        self.routes: Dict[str, Route] = {}
        self.handoffs: Dict[str, List[dict]] = {}
        self._views: Dict[Tuple[int, int, int], bytes] = {}
        self._lock = threading.Lock()
        self._n = 0

    # ---- location ----
    def where(self, device_id: str) -> Optional[Fix]:
        return self.book.get(device_id)

    def set_phone_fix(self, device_id: str, lat: Any, lon: Any, acc: Any = 50) -> Fix:
        if not valid_lat_lon(lat, lon):
            raise MapsError("bad_request", "lat/lon out of range", 422)
        try:
            a = clamp(float(acc), 3, 5000)
        except (TypeError, ValueError):
            a = 50.0
        return self.book.put(device_id, Fix(float(lat), float(lon), a, "phone", self.clock()))

    def set_from_link(self, device_id: str, text: str, as_destination: bool = False) -> dict:
        """A link / coordinates / a place name pasted on /me: SOUL's place, or (as_destination) where to go."""
        fix, query = parse_share_link(text, self.resolve_short)
        if fix is None and query and self.geocoder is not None:
            near = self.book.get(device_id)
            hits = self.geocoder.search(query, near)
            if hits:
                fix = Fix(hits[0].lat, hits[0].lon, 50, "link", self.clock(), hits[0].name)
        if fix is None:
            raise MapsError("not_found", "no place found in that link", 404)
        if as_destination:
            return {"dest": fix}
        fix.at = self.clock()
        return {"fix": self.book.put(device_id, fix)}

    def wifi_fix(self, device_id: str, aps: List[dict]) -> Optional[Fix]:
        if self.wifi is None:
            raise MapsError("config", "Wi-Fi location is not set up on this SOUL Cloud", 501)
        if not self.book.wifi_allowed(device_id):
            raise MapsError("not_allowed", "the owner has not allowed finding SOUL by Wi-Fi (Settings on /me)", 403)
        f = self.wifi.locate(aps)
        if f is None:
            return None
        f.at = self.clock()
        return self.book.put(device_id, f)

    # ---- the map ----
    def view(self, lat: float, lon: float, z: int) -> bytes:
        if self.tiles is None:
            raise MapsError("config", "no map data on this SOUL Cloud (set SOUL_PMTILES)", 501)
        if not valid_lat_lon(lat, lon):
            raise MapsError("bad_request", "lat/lon out of range", 422)
        z = int(clamp(int(z), MIN_Z, MAX_Z))
        # quantise the centre to 1/4 screen so neighbours share a cached bundle
        cx, cy = world_px(lat, lon, z)
        q = BUNDLE_SIZE // 8
        key = (z, int(cx // q), int(cy // q))
        with self._lock:
            hit = self._views.get(key)
        if hit is not None:
            return hit
        la, lo = lat_lon((key[1] + 0.5) * q, (key[2] + 0.5) * q, z)
        b = build_bundle(self.tiles, la, lo, z)
        with self._lock:
            self._views[key] = b
            while len(self._views) > self.VIEW_CACHE:
                self._views.pop(next(iter(self._views)))
        return b

    # ---- places and routes ----
    def search(self, device_id: str, text: str, lang: str = "en") -> List[Place]:
        if self.geocoder is None:
            raise MapsError("config", "place search is not set up on this SOUL Cloud", 501)
        text = (text or "").strip()
        if not text:
            raise MapsError("bad_request", "say where to", 422)
        return self.geocoder.search(text, self.book.get(device_id), lang)

    def plan(self, device_id: str, to: str = "", lat: Any = None, lon: Any = None, mode: str = "walk",
             lang: str = "en", name: str = "") -> Route:
        """A route from SOUL's last place to `to` (a name, an address, a pasted link) or lat/lon."""
        if self.router is None:
            raise MapsError("config", "routing is not set up on this SOUL Cloud", 501)
        mode = mode if mode in MODES else "walk"
        here = self.book.get(device_id)
        if here is None:
            raise MapsError("no_location", "I don't know where I am: share your location from your phone (/me/where)", 409)
        if lat is not None and lon is not None:
            if not valid_lat_lon(lat, lon):
                raise MapsError("bad_request", "lat/lon out of range", 422)
            dest = Place(name or to or "", float(lat), float(lon))
        else:
            fix, query = parse_share_link(to, self.resolve_short)
            if fix is not None:
                dest = Place(fix.label or name or "", fix.lat, fix.lon)
            else:
                hits = self.search(device_id, query or to, lang)
                if not hits:
                    raise MapsError("not_found", f"I can't find “{(query or to)[:40]}”", 404)
                dest = hits[0]
        if haversine(here.lat, here.lon, dest.lat, dest.lon) > (60_000 if mode == "walk" else 400_000):
            raise MapsError("too_far", "that is too far for this mode; send it to your phone instead", 422)
        r = self.router.route((here.lat, here.lon), (dest.lat, dest.lon), mode, lang)
        r.to, r.to_lat, r.to_lon, r.mode = dest.name or dest.detail or to[:60], dest.lat, dest.lon, mode
        with self._lock:
            self._n += 1
            r.id = f"rt{int(self.clock()) % 100000:05d}{self._n % 1000:03d}"
            r.made = self.clock()
            self.routes[device_id] = r
        return r

    def current_route(self, device_id: str) -> Optional[Route]:
        r = self.routes.get(device_id)
        if r and self.clock() - r.made > self.ROUTE_TTL:
            self.routes.pop(device_id, None)
            return None
        return r

    def end_route(self, device_id: str) -> None:
        self.routes.pop(device_id, None)

    def send_to_phone(self, device_id: str) -> dict:
        r = self.current_route(device_id)
        if r is None:
            raise MapsError("no_route", "no route to send", 404)
        links = phone_links(r.to_lat, r.to_lon, r.to, r.mode)
        item = {"to": r.to, "links": links, "at": int(self.clock())}
        lst = self.handoffs.setdefault(device_id, [])
        lst.insert(0, item)
        del lst[5:]
        return item

    def take_handoffs(self, device_id: str) -> List[dict]:
        now = self.clock()
        return [h for h in self.handoffs.get(device_id, []) if now - h["at"] < 3600]


def maps_from_env(env: Dict[str, str], http: Http = urllib_http, data_dir: str = "",
                  clock: Callable[[], float] = time.time) -> MapsService:
    """SOUL_PMTILES=/data/soul-basemap.pmtiles · SOUL_ROUTER=valhalla:https://… | ors:<key> | osrm:https://…
    SOUL_GEOCODER=photon:https://… · SOUL_WIFI_GEO=beacondb | google:<key> | ichnaea:https://…"""
    import os
    book = LocationBook(os.path.join(data_dir, "maps.sqlite") if data_dir else ":memory:", clock=clock)
    tiles = None
    p = env.get("SOUL_PMTILES", "")
    if p and os.path.exists(p):
        tiles = PMTilesSource(PMTiles.from_file(p))
    router = None
    r = env.get("SOUL_ROUTER", "")
    if r.startswith("valhalla:"):
        router = ValhallaRouter(r[9:], http=http)
    elif r.startswith("ors:"):
        router = OrsRouter(r[4:], http=http)
    elif r.startswith("osrm:"):
        router = OsrmRouter(r[5:], http=http)
    g = env.get("SOUL_GEOCODER", "")
    geocoder = PhotonGeocoder(g[7:], http=http) if g.startswith("photon:") else None
    w = env.get("SOUL_WIFI_GEO", "")
    wifi = None
    if w == "beacondb":
        wifi = WifiGeolocator(http=http)
    elif w.startswith("google:"):
        wifi = WifiGeolocator("https://www.googleapis.com/geolocation/v1/geolocate", w[7:], http, "google")
    elif w.startswith("ichnaea:"):
        wifi = WifiGeolocator(w[8:].rstrip("/") + "/v1/geolocate", "", http, "ichnaea")
    return MapsService(book, tiles, router, geocoder, wifi, clock)


# ======================================================================== demo data ==

def demo_city_tiles(lat: float = 44.4355, lon: float = 26.1025, z: int = 15, radius: int = 1) -> Dict[Tuple[int, int, int], bytes]:
    """A small synthetic city (a river, a park, a grid of streets, two avenues, a rail line, place names) as real
    MVT tiles at zoom z around lat/lon, each clipped to its tile like a real basemap: the simulator, the web
    prototype and the tests use it, so nothing ever hits a tile server. It is not OpenStreetMap data."""
    cx, cy = world_px(lat, lon, z)
    ctx, cty = int(cx // TILE), int(cy // TILE)
    streets = ["Strada Lipscani", "Strada Smârdan", "Strada Doamnei", "Calea Victoriei", "Bulevardul Elisabeta",
               "Strada Academiei", "Strada Ion Câmpineanu", "Strada Brezoianu"]
    world: List[Tuple[str, dict]] = []  # (layer, feature in world px)
    rv = [(cx - 700 + i * 70, cy + 210 + 40 * math.sin(i * 0.6)) for i in range(21)]
    world.append(("water", {"type": 3, "geom": [[(x, y - 14) for x, y in rv] + [(x, y + 14) for x, y in reversed(rv)]],
                            "props": {"kind": "water"}}))
    world.append(("landuse", {"type": 3, "geom": [[(cx - 260, cy - 240), (cx - 120, cy - 250), (cx - 110, cy - 130),
                                                   (cx - 250, cy - 120)]], "props": {"kind": "park"}}))
    for i in range(-6, 7):
        world.append(("roads", {"type": 2, "geom": [[(cx - 700, cy + i * 70 + (i % 3) * 6), (cx + 700, cy + i * 70 - (i % 2) * 8)]],
                                "props": {"kind": "minor_road", "name": streets[(i + 6) % len(streets)]}}))
        world.append(("roads", {"type": 2, "geom": [[(cx + i * 80, cy - 700), (cx + i * 80 + 30, cy + 700)]],
                                "props": {"kind": "minor_road", "name": streets[(i + 9) % len(streets)]}}))
    world.append(("roads", {"type": 2, "geom": [[(cx - 20, cy - 700), (cx + 10, cy - 100), (cx - 30, cy + 700)]],
                            "props": {"kind": "major_road", "name": "Calea Victoriei"}}))
    world.append(("roads", {"type": 2, "geom": [[(cx - 700, cy - 30), (cx + 700, cy + 20)]],
                            "props": {"kind": "highway", "name": "Bulevardul Regina Elisabeta"}}))
    world.append(("roads", {"type": 2, "geom": [[(cx - 700, cy - 420), (cx + 700, cy - 360)]], "props": {"kind": "rail"}}))
    for name, dx, dy in (("Lipscani", 120, 60), ("Cișmigiu", -190, -185), ("Universitate", 230, -60),
                         ("Piața Romană", 40, -560), ("Ateneu", 175, -270)):
        world.append(("places", {"type": 1, "geom": [[(cx + dx, cy + dy)]], "props": {"kind": "neighbourhood", "name": name}}))
    E, k, buf = 4096, 4096 / TILE, 64
    tiles = {}
    for ty in range(cty - radius, cty + radius + 1):
        for tx in range(ctx - radius, ctx + radius + 1):
            ox, oy = tx * TILE, ty * TILE
            layers: Dict[str, List[dict]] = {}
            for lname, ft in world:
                parts = [[((x - ox) * k, (y - oy) * k) for x, y in part] for part in ft["geom"]]
                out = []
                for part in parts:
                    if ft["type"] == 1:
                        x, y = part[0]
                        if 0 <= x < E and 0 <= y < E:
                            out.append([(int(round(x)), int(round(y)))])
                    elif ft["type"] == 2:
                        for run in clip_line(part, -buf, -buf, E + buf, E + buf):
                            out.append([(int(round(x)), int(round(y))) for x, y in run])
                    else:
                        poly = clip_poly(part, -buf, -buf, E + buf, E + buf)
                        if len(poly) >= 3:
                            ring = [(int(round(x)), int(round(y))) for x, y in poly]
                            out.append(ring + [ring[0]])
                if out:
                    layers.setdefault(lname, []).append({"type": ft["type"], "geom": out, "props": ft["props"]})
            tiles[(z, tx, ty)] = encode_mvt(layers)
    return tiles


class DemoTiles(TileSource):
    def __init__(self, tiles: Dict[Tuple[int, int, int], bytes], z: int):
        self.t, self.max_z = tiles, z

    def tile(self, z: int, x: int, y: int) -> Optional[bytes]:
        return self.t.get((z, x, y))
