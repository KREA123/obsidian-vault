"""Client ID Metadata Documents (CIMD): an SSRF-safe fetcher (docs/07-CONNECT-AI.md §3.7, MCP authorization spec).

With CIMD an OAuth client has no registration at SOUL: its `client_id` is an https URL, and the document at
that URL describes the client (`client_id`, `client_name`, `redirect_uris`, ...). claude.ai's connector dialog
offers it as "Use Claude's published identity"; ChatGPT uses `https://chatgpt.com/oauth/client.json`.
`oauth.SoulOAuthProvider.get_client` calls `fetch_client_metadata(client_id)` for an https `client_id`, then
checks the document's redirect URIs with the same rules as DCR and caches the client for 5 minutes.

Fetching a URL chosen by a stranger is a server-side request forgery risk, so the rules are strict:

- the URL: `https`, port 443 (or none), a non-root path, no userinfo, no fragment, <= 512 characters;
- DNS is resolved once, and **every** address must be public: loopback, private, link-local, CGNAT
  (100.64/10), `169.254/16` (cloud metadata), unique-local `fc00::/7`, `fe80::/10`, multicast, reserved,
  unspecified and IPv4-mapped private addresses are refused;
- the TCP connection goes to that pinned address (no second lookup, so no DNS rebinding), TLS is checked
  against the system CAs with SNI and hostname = the URL's host;
- no redirects (any 3xx is a refusal), 3 s for the whole exchange, <= 16 KB of body, JSON object only;
- the document's `client_id` must equal the URL exactly; it must list `redirect_uris`.

Nothing is logged except the host and the reason of a refusal.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import logging
import socket
import ssl
import time
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlsplit

log = logging.getLogger("suflet_ai.cimd")

TIMEOUT_S = 3.0
MAX_BYTES = 16 * 1024
MAX_URL = 512
USER_AGENT = "SOUL-Cloud-CIMD/1"

# Not covered by `is_global` on every Python version, or worth naming explicitly.
_BLOCKED = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.0.0.0/24", "192.0.2.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
    "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32",
    "::/128", "::1/128", "fc00::/7", "fe80::/10", "ff00::/8", "64:ff9b::/96", "2001:db8::/32",
)]


class CimdRejected(Exception):
    """The client_id URL or its document is not acceptable. `reason` is safe to log."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def check_url(url: str) -> Tuple[str, str]:
    """-> (host, path_with_query) or raise CimdRejected."""
    if not isinstance(url, str) or len(url) > MAX_URL:
        raise CimdRejected("client_id is not a short string")
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        raise CimdRejected("client_id is not a URL") from None
    if u.scheme != "https":
        raise CimdRejected("client_id must be an https URL")
    if u.username is not None or u.password is not None or "@" in u.netloc:
        raise CimdRejected("client_id must not carry userinfo")
    if u.fragment or url.endswith("#"):
        raise CimdRejected("client_id must not have a fragment")
    if port not in (None, 443):
        raise CimdRejected("client_id must use port 443")
    host = (u.hostname or "").lower()
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise CimdRejected("client_id host is not public")
    if not u.path or u.path == "/":
        raise CimdRejected("client_id must have a path")
    return host, u.path + (f"?{u.query}" if u.query else "")


def ip_allowed(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped is not None:
        a = a.ipv4_mapped
    if any(a in n for n in _BLOCKED if n.version == a.version):
        return False
    return bool(a.is_global) and not (a.is_multicast or a.is_reserved or a.is_link_local or a.is_loopback
                                      or a.is_private or a.is_unspecified)


def resolve(host: str) -> List[str]:
    """Every address the host resolves to (once)."""
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise CimdRejected("client_id host does not resolve") from None
    return list(dict.fromkeys(i[4][0] for i in infos))


class _PinnedHTTPS(http.client.HTTPSConnection):
    """HTTPS to a fixed IP address, with SNI and certificate checks for `host`."""

    def __init__(self, host: str, ip: str, timeout: float, context: ssl.SSLContext):
        super().__init__(host, 443, timeout=timeout, context=context)
        self._ip = ip

    def connect(self) -> None:
        sock = socket.create_connection((self._ip, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def https_get(ip: str, host: str, path: str, timeout: float) -> Tuple[int, str, bytes]:
    """One GET to the pinned address: -> (status, content-type, body <= MAX_BYTES + 1)."""
    conn = _PinnedHTTPS(host, ip, timeout, ssl.create_default_context())
    try:
        conn.request("GET", path, headers={"Host": host, "Accept": "application/json", "User-Agent": USER_AGENT,
                                           "Connection": "close"})
        r = conn.getresponse()
        length = r.getheader("Content-Length")
        if length and length.isdigit() and int(length) > MAX_BYTES:
            return r.status, r.getheader("Content-Type") or "", b"x" * (MAX_BYTES + 1)
        return r.status, r.getheader("Content-Type") or "", r.read(MAX_BYTES + 1)
    finally:
        conn.close()


def fetch_client_metadata(url: str, *, resolver: Callable[[str], List[str]] = resolve,
                          get: Callable[[str, str, str, float], Tuple[int, str, bytes]] = https_get,
                          timeout: float = TIMEOUT_S) -> dict:
    """Fetch and check the Client ID Metadata Document at `url`. Raises CimdRejected."""
    host, path = check_url(url)
    start = time.monotonic()
    ips = resolver(host)
    if not ips:
        raise CimdRejected("client_id host does not resolve")
    bad = [ip for ip in ips if not ip_allowed(ip)]
    if bad:  # one private answer is enough to refuse: the attacker controls which one a client would use
        log.warning("CIMD refused for %s: non-public address", host)
        raise CimdRejected("client_id host resolves to a non-public address")
    try:
        status, ctype, body = get(ips[0], host, path, timeout)
    except (OSError, ssl.SSLError, http.client.HTTPException) as e:
        log.warning("CIMD fetch failed for %s: %s", host, type(e).__name__)
        raise CimdRejected("client metadata document could not be fetched") from None
    if time.monotonic() - start > timeout:
        raise CimdRejected("client metadata document took too long")
    if 300 <= status < 400:
        raise CimdRejected("client metadata document redirects (not followed)")
    if status != 200:
        raise CimdRejected(f"client metadata document answered HTTP {status}")
    if len(body) > MAX_BYTES:
        raise CimdRejected("client metadata document is over 16 KB")
    if ctype and "json" not in ctype.lower():
        raise CimdRejected("client metadata document is not JSON")
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CimdRejected("client metadata document is not JSON") from None
    if not isinstance(doc, dict):
        raise CimdRejected("client metadata document is not a JSON object")
    if doc.get("client_id") != url:
        raise CimdRejected("client_id in the document differs from its URL")
    uris = doc.get("redirect_uris")
    if not isinstance(uris, list) or not uris or not all(isinstance(u, str) for u in uris):
        raise CimdRejected("client metadata document lists no redirect_uris")
    if "client_secret" in doc or doc.get("token_endpoint_auth_method", "none") not in ("none",):
        raise CimdRejected("CIMD clients are public: no client secret")
    return doc


def make_fetcher(resolver: Optional[Callable[[str], List[str]]] = None,
                 get: Optional[Callable[[str, str, str, float], Tuple[int, str, bytes]]] = None) -> Callable[[str], dict]:
    """A `cimd_fetch` for `create_app` / `create_remote_app` with injected network parts (tests, e2e)."""
    def fetch(url: str) -> dict:
        return fetch_client_metadata(url, resolver=resolver or resolve, get=get or https_get)
    return fetch
