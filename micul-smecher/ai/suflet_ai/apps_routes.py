"""HTTP side of the SoulOS apps (apps.py, maps.py; docs/11-MAPS.md §5, os/APPS.md §4).

Device (Bearer device token, the same as /v1/device/poll):

    GET  /v1/device/apps/weather              -> weather_for_device(...)            (no_location 409, config 501)
    GET  /v1/device/apps/agenda               -> {"events": [...], "tz"}             (no_calendar 404)
    POST /v1/device/apps/findphone            -> {"ringing", "reach": page|push|none}
    GET  /v1/device/maps/where                -> {"fix": {lat, lon, acc, src, age, label}} | {"fix": null}
    POST /v1/device/maps/wifi   {"aps": [{"mac","rssi","ssid"}]} -> {"fix"}         (opt-in on /me/where)
    GET  /v1/device/maps/view?lat=&lon=&z=    -> application/x-soul-map (SMB1)      (config 501)
    POST /v1/device/maps/route  {"to"| "lat","lon"; "mode"} -> route.device_json()
    GET  /v1/device/maps/route                -> the current route (after a nav.start push) or 404
    DELETE /v1/device/maps/route              -> ended
    POST /v1/device/maps/send                 -> {"links": {...}}  (shown on /me/where; SOUL also draws a QR)

Owner (session cookie + CSRF header, like /v1/me/pair/claim):

    GET  /me/where?d=soul-…                   the page: Share my location · paste a link · calendar · find my phone
    POST /v1/me/location        {"device_id","lat","lon","acc"}
    POST /v1/me/location/link   {"device_id","text"}
    POST /v1/me/wifi-location   {"device_id","on"}
    POST /v1/me/calendar        {"device_id","url"}   ·  DELETE /v1/me/calendar {"device_id"}
    GET  /v1/me/ring?d=…        -> {"ring": bool, "handoffs": [...]}   ·  POST /v1/me/ring/found
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from starlette.responses import HTMLResponse
from starlette.routing import Route

from . import apps as apps_mod
from .devices import GatewayError
from .maps import MapsError

log = logging.getLogger("suflet_ai.apps_routes")

_DEV = re.compile(r"^soul-[0-9a-f]{12}$")
NO_STORE = {"Cache-Control": "no-store"}


def _maps_error(e: MapsError) -> JSONResponse:
    return JSONResponse({"error": {"code": e.code, "msg": e.msg}}, status_code=e.status, headers=NO_STORE)


def build_apps_router(get_gw: Callable[[], Any], get_hub: Callable[[], apps_mod.AppsHub] = apps_mod.hub) -> APIRouter:
    r = APIRouter()

    def device(request: Request) -> tuple:
        gw = get_gw()
        ctx = gw.store.device_from_token(request.headers.get("authorization"))
        d = gw.store.get_device(ctx.device_id) or {}
        return ctx.device_id, (d.get("lang") or "en"), (d.get("tz") or "Europe/Bucharest"), d

    async def body(request: Request, limit: int = 4096) -> dict:
        raw = await request.body()
        if len(raw) > limit:
            raise MapsError("too_big", f"body over {limit} bytes", 413)
        import json
        try:
            b = json.loads(raw or b"{}")
        except ValueError:
            raise MapsError("bad_request", "body is not JSON", 400)
        if not isinstance(b, dict):
            raise MapsError("bad_request", "body must be an object", 400)
        return b

    def guarded(fn):
        async def wrapper(request: Request):
            try:
                return await fn(request)
            except GatewayError as e:
                return JSONResponse(status_code=e.status, content=e.body())
            except MapsError as e:
                return _maps_error(e)
        wrapper.__name__ = fn.__name__
        return wrapper

    @r.get("/v1/device/apps/weather")
    @guarded
    async def weather(request: Request):
        dev, lang, tz, _ = device(request)
        return JSONResponse(get_hub().weather_for(dev, lang, tz), headers=NO_STORE)

    @r.get("/v1/device/apps/agenda")
    @guarded
    async def agenda(request: Request):
        dev, _, tz, _ = device(request)
        return JSONResponse({"events": get_hub().calendar.agenda(dev, tz), "tz": tz}, headers=NO_STORE)

    @r.post("/v1/device/apps/findphone")
    @guarded
    async def findphone(request: Request):
        dev, _, _, d = device(request)
        acc = d.get("account_id")
        if not acc:
            raise MapsError("not_paired", "pair SOUL with your account first", 409)
        return JSONResponse(get_hub().ring.ring(acc, d.get("name") or "SOUL"), headers=NO_STORE)

    @r.get("/v1/device/maps/where")
    @guarded
    async def where(request: Request):
        dev, _, _, _ = device(request)
        h = get_hub()
        f = h.maps.where(dev)
        return JSONResponse({"fix": f.to_json(h.clock()) if f else None}, headers=NO_STORE)

    @r.post("/v1/device/maps/wifi")
    @guarded
    async def wifi(request: Request):
        dev, _, _, _ = device(request)
        b = await body(request, 4096)
        aps = b.get("aps")
        if not isinstance(aps, list) or len(aps) > 40:
            raise MapsError("bad_request", "aps must be a list of at most 40", 422)
        h = get_hub()
        f = h.maps.wifi_fix(dev, aps)
        return JSONResponse({"fix": f.to_json(h.clock()) if f else None}, headers=NO_STORE)

    @r.get("/v1/device/maps/view")
    @guarded
    async def view(request: Request):
        device(request)
        q = request.query_params
        try:
            lat, lon = float(q.get("lat", "x")), float(q.get("lon", "x"))
        except ValueError:
            raise MapsError("bad_request", "lat and lon are numbers", 422)
        b = get_hub().maps.view(lat, lon, apps_mod.zoom_of(q.get("z", "16")))
        return Response(b, media_type="application/x-soul-map",
                        headers={"Cache-Control": "private, max-age=86400", "X-Map-Attribution": "(c) OpenStreetMap contributors"})

    @r.post("/v1/device/maps/route")
    @guarded
    async def route_new(request: Request):
        dev, lang, _, _ = device(request)
        b = await body(request, 2048)
        to = str(b.get("to") or "")[:200]
        rt = get_hub().maps.plan(dev, to, b.get("lat"), b.get("lon"), str(b.get("mode") or "walk"), lang,
                                 str(b.get("name") or "")[:60])
        return JSONResponse(rt.device_json(), headers=NO_STORE)

    @r.get("/v1/device/maps/route")
    @guarded
    async def route_get(request: Request):
        dev, _, _, _ = device(request)
        rt = get_hub().maps.current_route(dev)
        if rt is None:
            raise MapsError("no_route", "no route", 404)
        return JSONResponse(rt.device_json(), headers=NO_STORE)

    @r.delete("/v1/device/maps/route")
    @guarded
    async def route_end(request: Request):
        dev, _, _, _ = device(request)
        get_hub().maps.end_route(dev)
        return JSONResponse({"ok": True}, headers=NO_STORE)

    @r.post("/v1/device/maps/send")
    @guarded
    async def send(request: Request):
        dev, _, _, _ = device(request)
        return JSONResponse(get_hub().maps.send_to_phone(dev), headers=NO_STORE)

    return r


# ====================================================================== owner side ==

def where_routes(rc: Any, headers: Dict[str, str], get_hub: Callable[[], apps_mod.AppsHub] = apps_mod.hub) -> List[Route]:
    """The /me/where page and its JSON calls, mounted next to /me (web_me.py) on the remote app."""
    from .accounts import AuthError, require_csrf

    accounts, gw = rc.accounts, rc.gateway

    async def owned(request: Request, device_id: str):
        session = accounts.current_session(request)
        if session is None:
            return None, JSONResponse({"error": {"code": "unauthenticated", "msg": "sign in first"}}, 401)
        if request.method != "GET":
            try:
                require_csrf(request, None, session)
            except AuthError:
                return None, JSONResponse({"error": {"code": "csrf", "msg": "csrf"}}, 403)
        if not _DEV.match(device_id or ""):
            return None, JSONResponse({"error": {"code": "not_found", "msg": "no such SOUL"}}, 404)
        info = await gw.device_info(device_id)
        if not info or info.get("account_id") != session.account_id or info.get("revoked"):
            return None, JSONResponse({"error": {"code": "not_found", "msg": "no such SOUL"}}, 404)
        return session, None

    async def jbody(request: Request) -> dict:
        try:
            b = await request.json()
        except Exception:  # noqa: BLE001
            return {}
        return b if isinstance(b, dict) else {}

    def guard(fn):
        async def w(request: Request):
            try:
                return await fn(request)
            except MapsError as e:
                return _maps_error(e)
        return w

    @guard
    async def location(request: Request):
        b = await jbody(request)
        s, err = await owned(request, str(b.get("device_id", "")))
        if err:
            return err
        h = get_hub()
        f = h.maps.set_phone_fix(b["device_id"], b.get("lat"), b.get("lon"), b.get("acc", 50))
        return JSONResponse({"fix": f.to_json(h.clock())}, headers=NO_STORE)

    @guard
    async def location_link(request: Request):
        b = await jbody(request)
        s, err = await owned(request, str(b.get("device_id", "")))
        if err:
            return err
        h = get_hub()
        out = h.maps.set_from_link(b["device_id"], str(b.get("text", ""))[:2000])
        return JSONResponse({"fix": out["fix"].to_json(h.clock())}, headers=NO_STORE)

    @guard
    async def wifi_optin(request: Request):
        b = await jbody(request)
        s, err = await owned(request, str(b.get("device_id", "")))
        if err:
            return err
        get_hub().maps.book.set_wifi_allowed(b["device_id"], bool(b.get("on")))
        return JSONResponse({"ok": True, "on": bool(b.get("on"))}, headers=NO_STORE)

    @guard
    async def calendar(request: Request):
        b = await jbody(request)
        s, err = await owned(request, str(b.get("device_id", "")))
        if err:
            return err
        cal = get_hub().calendar
        if request.method == "DELETE":
            cal.forget(b["device_id"])
            return JSONResponse({"ok": True, "linked": False}, headers=NO_STORE)
        cal.set_link(b["device_id"], str(b.get("url", "")))
        return JSONResponse({"ok": True, "linked": True}, headers=NO_STORE)

    @guard
    async def ring(request: Request):
        dev = request.query_params.get("d", "")
        s, err = await owned(request, dev)
        if err:
            return err
        h = get_hub()
        return JSONResponse({"ring": h.ring.poll(s.account_id), "handoffs": h.maps.take_handoffs(dev)},
                            headers=NO_STORE)

    @guard
    async def ring_found(request: Request):
        b = await jbody(request)
        s, err = await owned(request, str(b.get("device_id", "")))
        if err:
            return err
        get_hub().ring.found(s.account_id)
        return JSONResponse({"ok": True}, headers=NO_STORE)

    async def page(request: Request):
        session = accounts.current_session(request)
        dev = request.query_params.get("d", "")
        if session is None:
            from urllib.parse import quote
            return Response(status_code=303, headers={"Location": "/login?next=" + quote(f"/me/where?d={dev}", safe=""),
                                                      "Cache-Control": "no-store"})
        devices = [d for d in await gw.devices_of(session.account_id)
                   if d.get("account_id") == session.account_id and not d.get("revoked")]
        if not dev and devices:
            dev = devices[0]["device_id"]
        if not any(d["device_id"] == dev for d in devices):
            return HTMLResponse("<!doctype html><p>No such SOUL.</p>", 404, headers=headers)
        h = get_hub()
        f = h.maps.where(dev)
        html = _WHERE.replace("{{DEV}}", dev).replace("{{CSRF}}", session.csrf).replace(
            "{{FIX}}", "none" if f is None else f"{f.source} · ±{int(f.acc_m)} m").replace(
            "{{CAL}}", "linked" if h.calendar.has_link(dev) else "not linked").replace(
            "{{WIFI}}", "checked" if h.maps.book.wifi_allowed(dev) else "")
        return HTMLResponse(html, headers=headers)

    async def js(request: Request):
        return Response(_WHERE_JS, media_type="application/javascript",
                        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})

    return [
        Route("/me/where", page, methods=["GET"]),
        Route("/static/soul-where.js", js, methods=["GET"]),
        Route("/v1/me/location", location, methods=["POST"]),
        Route("/v1/me/location/link", location_link, methods=["POST"]),
        Route("/v1/me/wifi-location", wifi_optin, methods=["POST"]),
        Route("/v1/me/calendar", calendar, methods=["POST", "DELETE"]),
        Route("/v1/me/ring", ring, methods=["GET"]),
        Route("/v1/me/ring/found", ring_found, methods=["POST"]),
    ]


# the page: no inline script (CSP default-src 'self'); everything it does is in /static/soul-where.js
_WHERE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>SOUL · where</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/static/soul-web.css">
</head><body data-dev="{{DEV}}" data-csrf="{{CSRF}}"><main class="wrap">
<header class="top"><a href="/me" class="home">SOUL</a></header>
<h1>Where is SOUL?</h1>
<p class="small">SOUL has no GPS. It uses your phone's place, only when you share it here. Kept 24 hours.</p>
<section class="card"><h2>Share my location</h2>
<p class="small">Now: <b id="fix">{{FIX}}</b></p>
<button class="btn" id="share" type="button">Share my location</button>
<label class="small"><input type="checkbox" id="follow"> keep sharing while this page is open</label>
<p class="small" id="share-st" role="status"></p></section>
<section class="card"><h2>Or paste a link</h2>
<p class="small">From Google Maps or Apple Maps: Share › Copy link. Coordinates work too.</p>
<input id="link" type="url" inputmode="url" placeholder="https://maps.app.goo.gl/…">
<button class="btn" id="link-go" type="button">Use this place</button><p class="small" id="link-st" role="status"></p></section>
<section class="card"><h2>Find SOUL by Wi-Fi</h2>
<p class="small">When you allow it, SOUL sends the names of nearby Wi-Fi access points (never their traffic) to a
location service to guess where it is. Off by default.</p>
<label><input type="checkbox" id="wifi" {{WIFI}}> allow</label></section>
<section class="card"><h2>Calendar</h2>
<p class="small">Your calendar's private address in iCal format (Google: Settings › your calendar › Secret address
in iCal format; Apple: Share calendar › Public; Outlook: Publish calendar › ICS). SOUL only reads it. Now: <b>{{CAL}}</b></p>
<input id="ics" type="url" placeholder="https://…/basic.ics"><button class="btn" id="ics-go" type="button">Link</button>
<button class="btn" id="ics-off" type="button">Unlink</button><p class="small" id="ics-st" role="status"></p></section>
<section class="card" id="find"><h2>Find my phone</h2>
<p class="small">Keep this page open (or add it to your home screen): when SOUL looks for your phone, it rings here.</p>
<p id="ring-st" class="small" role="status">Listening…</p><button class="btn" id="found" type="button" hidden>Found it</button>
<div id="handoffs"></div></section>
<p class="small">Map data © OpenStreetMap contributors · Weather by Open-Meteo.com (CC BY 4.0)</p>
</main><script src="/static/soul-where.js"></script></body></html>"""

_WHERE_JS = r"""(() => {
  const B = document.body, dev = B.dataset.dev, csrf = B.dataset.csrf, $ = id => document.getElementById(id);
  const post = (url, body, method = "POST") => fetch(url, { method, headers: { "content-type": "application/json",
    "x-csrf-token": csrf }, credentials: "same-origin", body: JSON.stringify(Object.assign({ device_id: dev }, body)) })
    .then(r => r.json().then(j => ({ ok: r.ok, j })));
  const say = (id, t) => { $(id).textContent = t; };
  let watch = null;
  const send = p => post("/v1/me/location", { lat: p.coords.latitude, lon: p.coords.longitude, acc: p.coords.accuracy })
    .then(({ ok, j }) => { say("share-st", ok ? "Shared (±" + Math.round(p.coords.accuracy) + " m)" : j.error.msg); if (ok) say("fix", "phone"); });
  const fail = e => say("share-st", e.code === 1 ? "Location is blocked for this site in your browser settings" : "No location: " + e.message);
  $("share").onclick = () => { if (!navigator.geolocation) return say("share-st", "This browser has no location");
    say("share-st", "Asking your phone…"); navigator.geolocation.getCurrentPosition(send, fail, { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 }); };
  $("follow").onchange = e => { if (watch !== null) { navigator.geolocation.clearWatch(watch); watch = null; }
    if (e.target.checked) watch = navigator.geolocation.watchPosition(send, fail, { enableHighAccuracy: true, maximumAge: 20000 }); };
  $("link-go").onclick = () => post("/v1/me/location/link", { text: $("link").value }).then(({ ok, j }) => say("link-st", ok ? "SOUL is here now" : j.error.msg));
  $("wifi").onchange = e => post("/v1/me/wifi-location", { on: e.target.checked });
  $("ics-go").onclick = () => post("/v1/me/calendar", { url: $("ics").value }).then(({ ok, j }) => say("ics-st", ok ? "Linked" : j.error.msg));
  $("ics-off").onclick = () => post("/v1/me/calendar", {}, "DELETE").then(() => say("ics-st", "Unlinked"));
  let ctx = null, osc = null;
  const ring = on => { $("found").hidden = !on; say("ring-st", on ? "SOUL is looking for your phone!" : "Listening…");
    if (on && !osc) { try { ctx = ctx || new AudioContext(); osc = ctx.createOscillator(); const g = ctx.createGain(); g.gain.value = 0.4;
      osc.type = "square"; osc.frequency.value = 880; osc.connect(g).connect(ctx.destination); osc.start();
      const t = setInterval(() => { if (!osc) return clearInterval(t); osc.frequency.value = osc.frequency.value === 880 ? 660 : 880; }, 300); } catch (e) {}
      if (navigator.vibrate) navigator.vibrate([400, 200, 400, 200, 400]); }
    if (!on && osc) { osc.stop(); osc = null; } };
  $("found").onclick = () => { ring(false); post("/v1/me/ring/found", {}); };
  const poll = () => fetch("/v1/me/ring?d=" + encodeURIComponent(dev), { credentials: "same-origin" }).then(r => r.json()).then(j => {
    ring(!!j.ring);
    $("handoffs").innerHTML = "";
    (j.handoffs || []).forEach(h => { const p = document.createElement("p"); p.className = "small"; p.append("From SOUL: " + h.to + " · ");
      [["Google Maps", h.links.google], ["Apple Maps", h.links.apple]].forEach(([n, u], i) => { const a = document.createElement("a"); a.href = u; a.textContent = n; a.rel = "noopener"; if (i) p.append(" · "); p.append(a); });
      $("handoffs").append(p); });
  }).catch(() => {}).finally(() => setTimeout(poll, document.hidden ? 15000 : 4000));
  poll();
})();"""
