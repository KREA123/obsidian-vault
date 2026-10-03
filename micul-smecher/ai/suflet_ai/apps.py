"""SOUL Cloud for SoulOS apps (os/APPS.md): weather, the calendar agenda, find my phone, and the hub that ties them to
maps (maps.py). Each one has a compact device format: SOUL's screen is 480 px round and its frames <= 8 KB.

    weather   Open-Meteo forecast (CC BY 4.0 data). The free endpoint is for non-commercial use only, so a SOUL
              that is sold uses the customer endpoint with an API key (Standard plan, 1 M calls/month): one call
              per SOUL per 30 minutes at most, cached per ~5 km cell for all SOULs there.
    calendar  the owner's secret ICS address (Google / Apple / Outlook "private address in iCal format"), pasted
              on /me/where; fetched over HTTPS (no private addresses, <= 2 MB, <= every 15 min), expanded
              (RRULE daily / weekly / monthly / yearly, EXDATE, all-day, TZID) into the next 7 days. Read-only.
    find      "Find my phone": SOUL asks, the cloud rings every open /me page of the owner (the browser plays a
              loud tone and vibrates) and, when the owner allowed it, sends a Web Push to the phone; an email is the
              fallback. Nothing is sent without the owner having opened /me/where once on that phone.

Nothing here logs a place, an event title or a URL.
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import json
import re
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse
from zoneinfo import ZoneInfo

from .maps import Fix, Http, MapsError, MapsService, clamp, urllib_http, valid_lat_lon

# ============================================================================ weather ==

# WMO weather codes (Open-Meteo `weather_code`) -> SOUL's six icons and a word
WMO_ICON = {0: "sun", 1: "sun", 2: "part", 3: "cloud", 45: "fog", 48: "fog"}
for _c in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
    WMO_ICON[_c] = "rain"
for _c in (71, 73, 75, 77, 85, 86):
    WMO_ICON[_c] = "snow"
for _c in (95, 96, 99):
    WMO_ICON[_c] = "storm"
ICONS = ("sun", "part", "cloud", "rain", "snow", "storm", "fog")
WORDS = {
    "en": {"sun": "Clear", "part": "Partly cloudy", "cloud": "Cloudy", "rain": "Rain", "snow": "Snow",
           "storm": "Storm", "fog": "Fog"},
    "ro": {"sun": "Senin", "part": "Parțial noros", "cloud": "Înnorat", "rain": "Ploaie", "snow": "Ninsoare",
           "storm": "Furtună", "fog": "Ceață"},
}


def wmo_icon(code: Any) -> str:
    try:
        return WMO_ICON.get(int(code), "cloud")
    except (TypeError, ValueError):
        return "cloud"


class OpenMeteo:
    """https://api.open-meteo.com/v1/forecast (free, non-commercial) or customer-api.open-meteo.com + apikey."""

    def __init__(self, key: str = "", http: Http = urllib_http, clock: Callable[[], float] = time.time):
        self.key, self.http, self.clock = key, http, clock
        self.base = "https://customer-api.open-meteo.com" if key else "https://api.open-meteo.com"
        self._cache: Dict[Tuple[float, float, str], Tuple[float, dict]] = {}
        self._lock = threading.Lock()
        self.calls = 0

    def forecast(self, lat: float, lon: float, tz: str = "auto") -> dict:
        cell = (round(lat * 20) / 20, round(lon * 20) / 20, tz)  # ~5 km
        now = self.clock()
        with self._lock:
            hit = self._cache.get(cell)
            if hit and now - hit[0] < 1800:
                return hit[1]
        q = {"latitude": f"{cell[0]:.2f}", "longitude": f"{cell[1]:.2f}", "timezone": tz,
             "current": "temperature_2m,weather_code,apparent_temperature,wind_speed_10m,precipitation",
             "hourly": "temperature_2m,weather_code,precipitation_probability",
             "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
             "forecast_days": "4", "forecast_hours": "13"}
        if self.key:
            q["apikey"] = self.key
        st, raw = self.http("GET", f"{self.base}/v1/forecast?{urlencode(q)}", None, {"user-agent": "SOUL-Cloud/0.4"}, 6.0)
        self.calls += 1
        if st != 200:
            raise MapsError("provider", f"weather answered {st}", 502)
        try:
            j = json.loads(raw)
        except ValueError:
            raise MapsError("provider", "weather sent something unreadable", 502)
        with self._lock:
            self._cache[cell] = (now, j)
            if len(self._cache) > 2000:
                self._cache.pop(next(iter(self._cache)))
        return j


def weather_for_device(j: dict, lang: str = "en", place: str = "") -> dict:
    """Open-Meteo JSON -> what SOUL draws (< 1 KB):
        {"t": 21, "feels": 20, "icon": "part", "word": "Partly cloudy", "hi": 24, "lo": 13, "rain": 30, "wind": 12,
         "place": "Bucharest", "hours": [["14", 21, "part", 10], ...6], "days": [["Sat", 24, 13, "part"], ...3],
         "src": "Open-Meteo"}"""
    L = WORDS.get(lang, WORDS["en"])
    try:
        cur = j["current"]
        daily = j["daily"]
        hourly = j.get("hourly", {})
        icon = wmo_icon(cur.get("weather_code"))
        out = {"t": int(round(cur["temperature_2m"])), "feels": int(round(cur.get("apparent_temperature", cur["temperature_2m"]))),
               "icon": icon, "word": L[icon], "hi": int(round(daily["temperature_2m_max"][0])),
               "lo": int(round(daily["temperature_2m_min"][0])),
               "rain": int(daily.get("precipitation_probability_max", [0])[0] or 0),
               "wind": int(round(cur.get("wind_speed_10m", 0) or 0)), "place": place[:40], "src": "Open-Meteo"}
    except (KeyError, TypeError, IndexError, ValueError):
        raise MapsError("provider", "weather sent something unreadable", 502)
    hours = []
    for i, (tm, t, c) in enumerate(zip(hourly.get("time", []), hourly.get("temperature_2m", []),
                                       hourly.get("weather_code", []))):
        if i % 2 or len(hours) >= 6:
            continue
        p = (hourly.get("precipitation_probability") or [0] * 99)[i] or 0
        hours.append([tm[11:13], int(round(t)), wmo_icon(c), int(p)])
    days = []
    names = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "ro": ["Lu", "Ma", "Mi", "Jo", "Vi", "Sâ", "Du"]}
    for i in range(1, min(4, len(daily.get("time", [])))):
        try:
            d = dt.date.fromisoformat(daily["time"][i])
            days.append([names.get(lang, names["en"])[d.weekday()], int(round(daily["temperature_2m_max"][i])),
                         int(round(daily["temperature_2m_min"][i])), wmo_icon(daily["weather_code"][i])])
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    out["hours"], out["days"] = hours, days
    return out


# =========================================================================== calendar ==

class FetchError(Exception):
    pass


def _public_host(host: str, resolver: Callable[[str], List[str]]) -> bool:
    """SSRF guard: only hosts whose every address is public (no loopback, private, link-local, metadata)."""
    if not host or host.lower() in ("localhost",) or host.endswith((".local", ".internal", ".lan")):
        return False
    try:
        addrs = resolver(host)
    except OSError:
        return False
    if not addrs:
        return False
    for a in addrs:
        ip = ipaddress.ip_address(a)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
    return True


def _resolve(host: str) -> List[str]:
    return list({ai[4][0] for ai in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})


def check_ics_url(url: str, resolver: Callable[[str], List[str]] = _resolve) -> str:
    url = (url or "").strip()
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname or u.username or u.password or (u.port not in (None, 443)):
        raise MapsError("bad_request", "the calendar address must be an https:// (or webcal://) link", 422)
    if len(url) > 2000:
        raise MapsError("bad_request", "that address is too long", 422)
    if not _public_host(u.hostname, resolver):
        raise MapsError("bad_request", "that address is not on the public internet", 422)
    return url


def _unfold(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        elif raw:
            lines.append(raw)
    return lines


def _prop(line: str) -> Tuple[str, Dict[str, str], str]:
    # NAME;PARAM=V;PARAM2="x:y":VALUE  (the first ':' outside quotes)
    q, i = False, 0
    for i, ch in enumerate(line):
        if ch == '"':
            q = not q
        elif ch == ":" and not q:
            break
    else:
        return line.upper(), {}, ""
    head, value = line[:i], line[i + 1:]
    parts = head.split(";")
    params = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.upper()] = v.strip('"')
    return parts[0].upper(), params, value


def _unescape(s: str) -> str:
    return s.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\").strip()


def _parse_dt(value: str, params: Dict[str, str], tz: ZoneInfo) -> Tuple[dt.datetime, bool]:
    """-> (aware datetime in `tz`, all_day)"""
    v = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", v):
        d = dt.datetime.strptime(v[:8], "%Y%m%d")
        return d.replace(tzinfo=tz), True
    m = re.fullmatch(r"(\d{8}T\d{6})(Z?)", v)
    if not m:
        raise ValueError("bad date")
    naive = dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
    if m.group(2) == "Z":
        return naive.replace(tzinfo=dt.timezone.utc).astimezone(tz), False
    zone = params.get("TZID")
    if zone:
        try:
            return naive.replace(tzinfo=ZoneInfo(zone)).astimezone(tz), False
        except (KeyError, ValueError):
            pass
    return naive.replace(tzinfo=tz), False  # floating time: the device's zone


_DAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _duration(v: str) -> dt.timedelta:
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", v.strip())
    if not m:
        return dt.timedelta(hours=1)
    w, d, h, mi, s = (int(x or 0) for x in m.groups()[1:])
    td = dt.timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)
    return -td if m.group(1) == "-" else td


def _occurrences(start: dt.datetime, rule: str, until_window: dt.datetime, exdates: set,
                 limit: int = 400) -> List[dt.datetime]:
    """RRULE expansion for what calendars really send: FREQ=DAILY|WEEKLY|MONTHLY|YEARLY, INTERVAL, COUNT, UNTIL,
    BYDAY (weekly: a list of days; monthly: one day like 2TU / -1FR), BYMONTHDAY (monthly). Others: just DTSTART."""
    r = dict(p.split("=", 1) for p in rule.split(";") if "=" in p)
    freq = r.get("FREQ", "")
    interval = max(1, int(r.get("INTERVAL", "1") or 1))
    count = int(r["COUNT"]) if r.get("COUNT", "").isdigit() else None
    until = None
    if r.get("UNTIL"):
        try:
            until, _ = _parse_dt(r["UNTIL"], {}, start.tzinfo)  # type: ignore[arg-type]
        except ValueError:
            until = None
    out: List[dt.datetime] = []
    n = 0

    def take(t: dt.datetime) -> bool:
        nonlocal n
        if until and t > until:
            return False
        if count is not None and n >= count:
            return False
        n += 1
        if t.replace(tzinfo=None) not in exdates:
            out.append(t)
        return t <= until_window

    if freq == "DAILY":
        t = start
        while len(out) < limit and take(t):
            t = t + dt.timedelta(days=interval)
    elif freq == "WEEKLY":
        days = sorted(_DAYS[d[-2:]] for d in r.get("BYDAY", "").split(",") if d[-2:] in _DAYS) or [start.weekday()]
        week0 = start - dt.timedelta(days=start.weekday())
        w = 0
        go = True
        while go and len(out) < limit and w < 600:
            for d in days:
                t = week0 + dt.timedelta(weeks=w * interval, days=d)
                if t < start:
                    continue
                if not take(t):
                    go = False
                    break
            w += 1
    elif freq in ("MONTHLY", "YEARLY"):
        by = r.get("BYDAY", "")
        mday = r.get("BYMONTHDAY", "")
        k = 0
        while len(out) < limit and k < 1200:
            months = k * interval * (12 if freq == "YEARLY" else 1)
            y, m = start.year + (start.month - 1 + months) // 12, (start.month - 1 + months) % 12 + 1
            k += 1
            day = None
            if by and freq == "MONTHLY":
                mm = re.fullmatch(r"([+-]?\d)?(MO|TU|WE|TH|FR|SA|SU)", by.split(",")[0])
                if mm:
                    nth, wd = int(mm.group(1) or 1), _DAYS[mm.group(2)]
                    if nth > 0:
                        first = dt.date(y, m, 1)
                        day = 1 + (wd - first.weekday()) % 7 + (nth - 1) * 7
                    else:
                        nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
                        last = nxt - dt.timedelta(days=1)
                        day = last.day - (last.weekday() - wd) % 7 + (nth + 1) * 7
            else:
                day = int(mday) if mday.lstrip("-").isdigit() else start.day
            try:
                t = start.replace(year=y, month=m, day=day)
            except ValueError:
                continue  # 31 Feb: no occurrence that month
            if t < start:
                continue
            if not take(t):
                break
    else:
        take(start)
    return out


def parse_ics(text: str, tz: str, now: dt.datetime, days: int = 7, limit: int = 12) -> List[dict]:
    """Events overlapping [now, now + days) in the device's zone, soonest first:
        {"s": "YYYY-MM-DDTHH:MM", "e": ..., "t": title, "l": location, "a": all_day}"""
    z = ZoneInfo(tz)
    now = now.astimezone(z)
    end_window = now + dt.timedelta(days=days)
    events: List[dict] = []
    cur: Optional[dict] = None
    for line in _unfold(text):
        name, params, value = _prop(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            cur = {"ex": set()}
        elif name == "END" and value.upper() == "VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None:
            if name == "SUMMARY":
                cur["t"] = _unescape(value)[:80]
            elif name == "LOCATION":
                cur["l"] = _unescape(value)[:60]
            elif name in ("DTSTART", "DTEND"):
                try:
                    cur[name] = _parse_dt(value, params, z)
                except ValueError:
                    cur["bad"] = True
            elif name == "DURATION":
                cur["dur"] = _duration(value)
            elif name == "RRULE":
                cur["rr"] = value
            elif name == "EXDATE":
                for v in value.split(","):
                    try:
                        cur["ex"].add(_parse_dt(v, params, z)[0].replace(tzinfo=None))
                    except ValueError:
                        pass
            elif name == "STATUS" and value.upper() == "CANCELLED":
                cur["bad"] = True
            elif name == "RECURRENCE-ID":
                cur["bad"] = True  # moved single occurrences: shown via their own VEVENT is beyond Phase 1; skip
    out = []
    for e in events:
        if e.get("bad") or "DTSTART" not in e:
            continue
        start, allday = e["DTSTART"]
        if "DTEND" in e:
            dur = e["DTEND"][0] - start
        else:
            dur = e.get("dur", dt.timedelta(days=1) if allday else dt.timedelta(hours=1))
        if dur.total_seconds() < 0:
            dur = dt.timedelta(0)
        starts = _occurrences(start, e["rr"], end_window, e["ex"]) if e.get("rr") else [start]
        for s in starts:
            en = s + dur
            if en <= now and not (allday and s.date() == now.date()):
                continue
            if s >= end_window:
                continue
            out.append({"s": s.strftime("%Y-%m-%dT%H:%M"), "e": en.strftime("%Y-%m-%dT%H:%M"),
                        "t": e.get("t") or "(busy)", "l": e.get("l", ""), "a": allday})
    out.sort(key=lambda x: (x["s"], not x["a"]))
    return out[:limit]


class CalendarService:
    """The owner's ICS link per device (sealed at rest when a sealer is given), fetched at most every 15 min."""

    MAX_BYTES = 2 << 20

    def __init__(self, http: Http = urllib_http, clock: Callable[[], float] = time.time,
                 resolver: Callable[[str], List[str]] = _resolve, seal: Callable[[str], str] = lambda s: s,
                 unseal: Callable[[str], str] = lambda s: s):
        self.http, self.clock, self.resolver = http, clock, resolver
        self.seal, self.unseal = seal, unseal
        self.links: Dict[str, str] = {}
        self._cache: Dict[str, Tuple[float, str]] = {}

    def set_link(self, device_id: str, url: str) -> None:
        self.links[device_id] = self.seal(check_ics_url(url, self.resolver))
        self._cache.pop(device_id, None)

    def forget(self, device_id: str) -> None:
        self.links.pop(device_id, None)
        self._cache.pop(device_id, None)

    def has_link(self, device_id: str) -> bool:
        return device_id in self.links

    def agenda(self, device_id: str, tz: str, now: Optional[dt.datetime] = None, days: int = 7) -> List[dict]:
        if device_id not in self.links:
            raise MapsError("no_calendar", "no calendar linked: add its private ICS address on /me/where", 404)
        t = self.clock()
        hit = self._cache.get(device_id)
        if hit and t - hit[0] < 900:
            text = hit[1]
        else:
            url = check_ics_url(self.unseal(self.links[device_id]), self.resolver)  # re-checked: DNS may change
            st, raw = self.http("GET", url, None, {"user-agent": "SOUL-Cloud/0.4 (calendar)", "accept": "text/calendar"}, 8.0)
            if st != 200:
                raise MapsError("provider", f"the calendar answered {st}", 502)
            if len(raw) > self.MAX_BYTES:
                raise MapsError("provider", "the calendar is too big (> 2 MB)", 502)
            text = raw.decode("utf-8", "replace")
            if "BEGIN:VCALENDAR" not in text[:4096].upper():
                raise MapsError("provider", "that address does not give a calendar", 502)
            self._cache[device_id] = (t, text)
        when = now or dt.datetime.fromtimestamp(t, ZoneInfo(tz))
        return parse_ics(text, tz, when, days)


# ======================================================================= find my phone ==

class EcbRates:
    """Euro foreign exchange reference rates of the European Central Bank (published once a day around 16:00 CET on
    working days; free to reuse with the source named: "Source: ECB"). The device converts offline with the last set it
    got (AppKit Rates); this only refreshes it. https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"""

    URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    _CUBE = re.compile(r"<Cube\s+currency=['\"]([A-Z]{3})['\"]\s+rate=['\"]([0-9.]+)['\"]")
    _TIME = re.compile(r"<Cube\s+time=['\"](\d{4}-\d{2}-\d{2})['\"]")

    def __init__(self, http: Http = urllib_http, clock: Callable[[], float] = time.time, ttl: float = 6 * 3600):
        self.http, self.clock, self.ttl = http, clock, ttl
        self._cache: Optional[Tuple[float, dict]] = None
        self._lock = threading.Lock()
        self.calls = 0

    @classmethod
    def parse(cls, xml: str) -> dict:
        rates = {c: float(v) for c, v in cls._CUBE.findall(xml) if float(v) > 0}
        m = cls._TIME.search(xml)
        if not rates or not m:
            raise MapsError("provider", "the ECB sent something unreadable", 502)
        return {"base": "EUR", "date": m.group(1), "rates": rates, "source": "ECB"}

    def latest(self) -> dict:
        now = self.clock()
        with self._lock:
            if self._cache and now - self._cache[0] < self.ttl:
                return self._cache[1]
        st, raw = self.http("GET", self.URL, None, {"user-agent": "SOUL-Cloud/0.4"}, 6.0)
        self.calls += 1
        if st != 200:
            with self._lock:
                if self._cache:  # yesterday's rates beat none
                    return self._cache[1]
            raise MapsError("provider", f"the ECB answered {st}", 502)
        j = self.parse(raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw))
        with self._lock:
            self._cache = (now, j)
        return j


class PhoneRing:
    """SOUL rings the owner's phone: each /me/where page that is open polls /v1/me/ring every few seconds; a ring
    lasts 60 s or until the owner taps "Found it". `push` (optional) sends a Web Push to subscribed phones."""

    def __init__(self, clock: Callable[[], float] = time.time, push: Optional[Callable[[str, dict], int]] = None):
        self.clock, self.push = clock, push
        self.rings: Dict[str, float] = {}  # account_id -> until
        self.seen: Dict[str, float] = {}   # account_id -> last time a page polled (a phone can hear us)

    def ring(self, account_id: str, device_name: str = "SOUL") -> dict:
        now = self.clock()
        self.rings[account_id] = now + 60
        pushed = 0
        if self.push is not None:
            try:
                pushed = int(self.push(account_id, {"title": f"{device_name} is looking for your phone", "tag": "soul-find"}))
            except Exception:  # noqa: BLE001 - push is best effort
                pushed = 0
        listening = now - self.seen.get(account_id, 0) < 30
        return {"ringing": True, "pages": 1 if listening else 0, "pushed": pushed,
                "reach": "page" if listening else "push" if pushed else "none"}

    def poll(self, account_id: str) -> bool:
        now = self.clock()
        self.seen[account_id] = now
        return self.rings.get(account_id, 0) > now

    def found(self, account_id: str) -> None:
        self.rings.pop(account_id, None)


# =============================================================================== hub ==

class AppsHub:
    def __init__(self, maps: Optional[MapsService] = None, weather: Optional[OpenMeteo] = None,
                 calendar: Optional[CalendarService] = None, ring: Optional[PhoneRing] = None,
                 clock: Callable[[], float] = time.time, rates: Optional[EcbRates] = None):
        self.clock = clock
        self.rates = rates or EcbRates(clock=clock)
        self.maps = maps or MapsService(clock=clock)
        self.weather = weather
        self.calendar = calendar or CalendarService(clock=clock)
        self.ring = ring or PhoneRing(clock=clock)

    def weather_for(self, device_id: str, lang: str, tz: str) -> dict:
        if self.weather is None:
            raise MapsError("config", "weather is not set up on this SOUL Cloud", 501)
        fix: Optional[Fix] = self.maps.where(device_id)
        if fix is None:
            raise MapsError("no_location", "I don't know where I am: share your location from your phone (/me/where)", 409)
        j = self.weather.forecast(fix.lat, fix.lon, tz or "auto")
        return weather_for_device(j, lang, fix.label)


_hub: Optional[AppsHub] = None
_hub_lock = threading.Lock()


def hub() -> AppsHub:
    """The process-wide hub (configured from the environment on first use)."""
    global _hub
    with _hub_lock:
        if _hub is None:
            import os
            from .maps import maps_from_env
            data = os.environ.get("SOUL_DATA_DIR", "")
            key = os.environ.get("SOUL_OPEN_METEO_KEY", "")
            weather = OpenMeteo(key) if (key or os.environ.get("SOUL_WEATHER") == "open-meteo-free") else None
            _hub = AppsHub(maps_from_env(dict(os.environ), data_dir=data), weather)
        return _hub


def set_hub(h: Optional[AppsHub]) -> None:
    global _hub
    with _hub_lock:
        _hub = h


def valid_point(lat: Any, lon: Any) -> Tuple[float, float]:
    if not valid_lat_lon(lat, lon):
        raise MapsError("bad_request", "lat/lon out of range", 422)
    return float(lat), float(lon)


def zoom_of(z: Any) -> int:
    try:
        return int(clamp(int(z), 3, 18))
    except (TypeError, ValueError):
        return 16
