"""SOUL accounts: email one-time codes, browser sessions, CSRF and re-auth (07-CONNECT-AI §3.1, §3.3).

What is here (Phase 0):
- Email sign-in with a 6-digit code: 10 minutes, stored as an HMAC (never in clear), single use,
  at most 5 attempts per code (then the code dies), constant-time comparison, at most 10 codes per
  email and 30 per IP per hour. Unknown emails get the same answer as known ones. Every successful
  sign-in sends a "new sign-in to SOUL" email.
- Sessions: cookie `__Host-soul_session` (Secure; HttpOnly; SameSite=Lax; Path=/), 30 days sliding,
  stored as SHA-256. CSRF: double submit, cookie `__Host-soul_csrf` (not HttpOnly) + the same value
  in the `X-CSRF-Token` header or a `csrf` form field.
- Fresh re-auth (`reauth_at` within 10 minutes) for sensitive steps, e.g. approving a non-allowlisted
  OAuth client.
- Apple / Google sign-in: Phase 1 launch gate, not here.

Never logged: codes, session ids, CSRF values, email bodies. Logs carry `safety_id(account_id)` only.
The JSON routes `/v1/auth/*` belong to api_me.py; this module is the logic they (and the consent
pages in mcp_remote.py) call.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, List, Optional, Tuple

log = logging.getLogger("soul.accounts")

SESSION_COOKIE = "__Host-soul_session"
CSRF_COOKIE = "__Host-soul_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_DAYS = 30
CODE_TTL_S = 10 * 60
CODE_MAX_TRIES = 5
CODES_PER_EMAIL_HOUR = 10
CODES_PER_IP_HOUR = 30
VERIFY_PER_IP_HOUR = 60
REAUTH_WINDOW_S = 10 * 60

_EMAIL = re.compile(r"^[^@\s<>\"']{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")


# --------------------------------------------------------------------------- errors --

class AuthError(Exception):
    """An error with a stable code from §3.13 and the HTTP status it maps to."""

    status = 400

    def __init__(self, code: str, msg: str = "", retry_ms: Optional[int] = None):
        super().__init__(msg or code)
        self.code = code
        self.msg = msg or code
        self.retry_ms = retry_ms


class RateLimited(AuthError):
    status = 429

    def __init__(self, retry_ms: int):
        super().__init__("rate_limited", "too many attempts, try again later", retry_ms=retry_ms)


class LoginFailed(AuthError):
    status = 401


class ReauthRequired(AuthError):
    status = 401

    def __init__(self):
        super().__init__("reauth_required", "sign in again to confirm it is you")


class CsrfError(AuthError):
    status = 403

    def __init__(self):
        super().__init__("csrf", "the form expired, reload the page")


# ------------------------------------------------------------------------- database --

class Database:
    """One SQLite connection shared by accounts.py, oauth.py and mcp_remote.py (db.py replaces it later).

    ":memory:" for tests, a file path for the service. All access goes through `lock`.
    """

    def __init__(self, path: str = ":memory:"):
        self.path = path
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.execute("PRAGMA foreign_keys=ON")
            if path != ":memory:":
                self.conn.execute("PRAGMA journal_mode=WAL")

    def script(self, sql: str) -> None:
        with self.lock:
            self.conn.executescript(sql)

    def exec(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.conn.execute(sql, args)

    def one(self, sql: str, args: tuple = ()) -> Optional[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, args).fetchone()

    def all(self, sql: str, args: tuple = ()) -> List[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, args).fetchall()


# --------------------------------------------------------------------- small helpers --

def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load_pepper() -> bytes:
    """SOUL_ID_PEPPER (hex or text); a random per-process value in dev (ids then change on restart)."""
    raw = os.environ.get("SOUL_ID_PEPPER", "")
    if raw:
        try:
            return bytes.fromhex(raw)
        except ValueError:
            return raw.encode()
    return secrets.token_bytes(32)


def safety_id(account_id: str, pepper: bytes) -> str:
    """The only account identifier that may appear in logs or leave the service (§3.1)."""
    return hmac.new(pepper, account_id.encode(), hashlib.sha256).hexdigest()[:32]


def normalize_email(email: str) -> str:
    e = (email or "").strip().lower()
    if len(e) > 254 or not _EMAIL.match(e):
        raise AuthError("invalid", "that does not look like an email address")
    return e


def account_hint(email: str) -> str:
    """'ana.pop@gmail.com' -> 'a***@gmail.com' (shown on SOUL's pair-confirm screen)."""
    local, _, domain = (email or "").partition("@")
    return f"{local[:1]}***@{domain}" if local and domain else "***"


class SlidingWindow:
    """In-process sliding-window counter (ratelimit.py replaces it with shared buckets)."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, per_s: int) -> None:
        now = self._clock()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= now - per_s:
                q.popleft()
            if len(q) >= limit:
                raise RateLimited(int((q[0] + per_s - now) * 1000) + 1)
            q.append(now)


Mailer = Callable[[str, str, str], None]  # (to, subject, body)


class DevMailbox:
    """Dev/test mailer: keeps messages in memory (and optionally appends them to a 0600 file).

    Production must pass a real EU transactional mailer (notify.py); `Accounts` refuses this one
    when SOUL_ENV=production.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.messages: List[Tuple[str, str, str]] = []

    def __call__(self, to: str, subject: str, body: str) -> None:
        self.messages.append((to, subject, body))
        if self.path:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(f"To: {to}\nSubject: {subject}\n\n{body}\n---\n")

    def last_code(self, to: str) -> Optional[str]:
        for t, _s, body in reversed(self.messages):
            if t == to:
                m = re.search(r"\b(\d{6})\b", body)
                if m:
                    return m.group(1)
        return None


_TEXT = {
    "code_subject": {"ro": "Codul tău SOUL: {code}", "en": "Your SOUL code: {code}"},
    "code_body": {
        "ro": "Codul tău de conectare la SOUL este {code}. Expiră în 10 minute.\n"
              "Dacă nu tu ai cerut codul, ignoră acest email.",
        "en": "Your SOUL sign-in code is {code}. It expires in 10 minutes.\n"
              "If you did not ask for it, ignore this email.",
    },
    "signin_subject": {"ro": "Conectare nouă la SOUL", "en": "New sign-in to SOUL"},
    "signin_body": {
        "ro": "Cineva (sperăm că tu) s-a conectat acum în contul tău SOUL. Dacă nu ai fost tu, "
              "deschide pagina contului și deconectează aplicațiile pe care nu le recunoști.",
        "en": "Someone (hopefully you) just signed in to your SOUL account. If it was not you, "
              "open your account page and disconnect any app you do not recognise.",
    },
}


def _t(key: str, lang: str, **kw) -> str:
    return _TEXT[key]["ro" if lang == "ro" else "en"].format(**kw)


# -------------------------------------------------------------------------- accounts --

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    first_name  TEXT NOT NULL DEFAULT '',
    lang        TEXT NOT NULL DEFAULT 'ro',
    tz          TEXT NOT NULL DEFAULT 'Europe/Bucharest',
    created     INTEGER NOT NULL,
    deleted     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS login_codes (
    email      TEXT NOT NULL,
    code_hash  TEXT NOT NULL,
    expires    INTEGER NOT NULL,
    tries      INTEGER NOT NULL DEFAULT 0,
    used       INTEGER NOT NULL DEFAULT 0,
    ip         TEXT NOT NULL DEFAULT '',
    created    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS login_codes_email ON login_codes(email, created);
CREATE TABLE IF NOT EXISTS web_sessions (
    id_hash    TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    csrf       TEXT NOT NULL,
    created    INTEGER NOT NULL,
    last_seen  INTEGER NOT NULL,
    reauth_at  INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass
class Account:
    id: str
    email: str
    first_name: str
    lang: str
    tz: str
    new: bool = False

    @property
    def hint(self) -> str:
        return account_hint(self.email)

    @property
    def display_name(self) -> str:
        return self.first_name or self.email.partition("@")[0][:24]


@dataclass
class Session:
    account: Account
    id_hash: str
    csrf: str
    reauth_at: int
    token: Optional[str] = None  # the raw cookie value; set only right after sign-in

    @property
    def account_id(self) -> str:
        return self.account.id


class Accounts:
    def __init__(self, db: Optional[Database] = None, mailer: Optional[Mailer] = None,
                 clock: Callable[[], float] = time.time, pepper: Optional[bytes] = None):
        self.db = db or Database()
        self.db.script(_SCHEMA)
        if mailer is None:
            if os.environ.get("SOUL_ENV") == "production":
                raise RuntimeError("production needs a real mailer for sign-in codes")
            mailer = DevMailbox()
        self.mailer = mailer
        self.clock = clock
        self.pepper = pepper or load_pepper()
        self.limits = SlidingWindow(clock)

    def now(self) -> int:
        return int(self.clock())

    def _code_hash(self, email: str, code: str) -> str:
        return hmac.new(self.pepper, f"login|{email}|{code}".encode(), hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------ sign-in --
    def start_email_login(self, email: str, lang: str = "ro", ip: str = "") -> None:
        """Send a 6-digit code. Same outcome for known and unknown emails (no account probing)."""
        email = normalize_email(email)
        lang = "ro" if lang == "ro" else "en"
        self.limits.hit(f"code-ip:{ip}", CODES_PER_IP_HOUR, 3600)
        self.limits.hit(f"code-email:{email}", CODES_PER_EMAIL_HOUR, 3600)
        code = f"{secrets.randbelow(10 ** 6):06d}"
        now = self.now()
        with self.db.lock:
            # a new code replaces any older one for this email
            self.db.exec("UPDATE login_codes SET used=1 WHERE email=? AND used=0", (email,))
            self.db.exec("INSERT INTO login_codes(email, code_hash, expires, ip, created) VALUES (?,?,?,?,?)",
                         (email, self._code_hash(email, code), now + CODE_TTL_S, ip[:64], now))
        self.mailer(email, _t("code_subject", lang, code=code), _t("code_body", lang, code=code))
        log.info("login code sent (email hash %s)", sha256_hex(email)[:12])

    def verify_email_login(self, email: str, code: str, ip: str = "", lang: str = "ro",
                           first_name: str = "", session: Optional[Session] = None) -> Session:
        """Check the code. Returns a new session, or refreshes `reauth_at` on `session` (re-auth)."""
        email = normalize_email(email)
        code = re.sub(r"\D", "", code or "")[:6]
        self.limits.hit(f"verify-ip:{ip}", VERIFY_PER_IP_HOUR, 3600)
        now = self.now()
        with self.db.lock:
            row = self.db.one("SELECT rowid, * FROM login_codes WHERE email=? AND used=0 "
                              "ORDER BY created DESC LIMIT 1", (email,))
            if row is None:
                raise LoginFailed("bad_code", "that code is not valid; ask for a new one")
            if row["expires"] < now:
                self.db.exec("UPDATE login_codes SET used=1 WHERE rowid=?", (row["rowid"],))
                raise LoginFailed("code_expired", "that code has expired; ask for a new one")
            tries = row["tries"] + 1
            ok = len(code) == 6 and hmac.compare_digest(row["code_hash"], self._code_hash(email, code))
            if not ok:
                dead = tries >= CODE_MAX_TRIES
                self.db.exec("UPDATE login_codes SET tries=?, used=? WHERE rowid=?",
                             (tries, 1 if dead else 0, row["rowid"]))
                raise LoginFailed("bad_code", "too many wrong codes; ask for a new one" if dead
                                  else "wrong code, try again")
            self.db.exec("UPDATE login_codes SET used=1, tries=? WHERE rowid=?", (tries, row["rowid"]))
            account = self._get_or_create(email, lang, first_name)
        if session is not None:
            if session.account.id != account.id:
                raise LoginFailed("forbidden", "sign in with the same account")
            self.db.exec("UPDATE web_sessions SET reauth_at=? WHERE id_hash=?", (now, session.id_hash))
            session.reauth_at = now
            out = session
        else:
            out = self._new_session(account)
        try:
            self.mailer(email, _t("signin_subject", account.lang), _t("signin_body", account.lang))
        except Exception:  # a mail outage must not block sign-in
            log.warning("sign-in notice email failed")
        log.info("sign-in ok (account %s)", safety_id(account.id, self.pepper))
        return out

    def _get_or_create(self, email: str, lang: str, first_name: str) -> Account:
        row = self.db.one("SELECT * FROM accounts WHERE email=? AND deleted=0", (email,))
        if row:
            return self._account(row)
        aid = "a_" + secrets.token_hex(12)
        name = re.sub(r"[\x00-\x1f<>]", "", (first_name or "").strip())[:40]
        self.db.exec("INSERT INTO accounts(id, email, first_name, lang, created) VALUES (?,?,?,?,?)",
                     (aid, email, name, "ro" if lang == "ro" else "en", self.now()))
        acc = self._account(self.db.one("SELECT * FROM accounts WHERE id=?", (aid,)))
        acc.new = True
        return acc

    @staticmethod
    def _account(row: sqlite3.Row) -> Account:
        return Account(id=row["id"], email=row["email"], first_name=row["first_name"], lang=row["lang"],
                       tz=row["tz"])

    def get_account(self, account_id: str) -> Optional[Account]:
        row = self.db.one("SELECT * FROM accounts WHERE id=? AND deleted=0", (account_id,))
        return self._account(row) if row else None

    def set_profile(self, account_id: str, first_name: Optional[str] = None, lang: Optional[str] = None,
                    tz: Optional[str] = None) -> None:
        if first_name is not None:
            self.db.exec("UPDATE accounts SET first_name=? WHERE id=?",
                         (re.sub(r"[\x00-\x1f<>]", "", first_name.strip())[:40], account_id))
        if lang in ("ro", "en"):
            self.db.exec("UPDATE accounts SET lang=? WHERE id=?", (lang, account_id))
        if tz:
            self.db.exec("UPDATE accounts SET tz=? WHERE id=?", (tz[:64], account_id))

    # ----------------------------------------------------------------- sessions --
    def _new_session(self, account: Account) -> Session:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        now = self.now()
        h = sha256_hex(token)
        self.db.exec("INSERT INTO web_sessions(id_hash, account_id, csrf, created, last_seen, reauth_at) "
                     "VALUES (?,?,?,?,?,?)", (h, account.id, csrf, now, now, now))
        return Session(account=account, id_hash=h, csrf=csrf, reauth_at=now, token=token)

    def session_from_token(self, token: Optional[str]) -> Optional[Session]:
        if not token or len(token) > 128:
            return None
        h = sha256_hex(token)
        now = self.now()
        row = self.db.one("SELECT * FROM web_sessions WHERE id_hash=?", (h,))
        if row is None:
            return None
        if row["last_seen"] < now - SESSION_DAYS * 86400:
            self.db.exec("DELETE FROM web_sessions WHERE id_hash=?", (h,))
            return None
        account = self.get_account(row["account_id"])
        if account is None:
            return None
        if now - row["last_seen"] > 60:  # sliding expiry, written at most once a minute
            self.db.exec("UPDATE web_sessions SET last_seen=? WHERE id_hash=?", (now, h))
        return Session(account=account, id_hash=h, csrf=row["csrf"], reauth_at=row["reauth_at"])

    def current_session(self, request) -> Optional[Session]:
        """The signed-in session of a Starlette/FastAPI request, or None."""
        return self.session_from_token(request.cookies.get(SESSION_COOKIE))

    def logout(self, session: Session) -> None:
        self.db.exec("DELETE FROM web_sessions WHERE id_hash=?", (session.id_hash,))

    def require_reauth(self, session: Session, within_s: int = REAUTH_WINDOW_S) -> None:
        if self.now() - int(session.reauth_at or 0) > within_s:
            raise ReauthRequired()

    def is_fresh(self, session: Session, within_s: int = REAUTH_WINDOW_S) -> bool:
        return self.now() - int(session.reauth_at or 0) <= within_s


# ----------------------------------------------------------------- cookies and CSRF --

def set_session_cookies(response, session: Session) -> None:
    """Set both cookies after sign-in (needs `session.token`)."""
    if session.token:
        response.set_cookie(SESSION_COOKIE, session.token, max_age=SESSION_DAYS * 86400, path="/",
                            secure=True, httponly=True, samesite="lax")
    response.set_cookie(CSRF_COOKIE, session.csrf, max_age=SESSION_DAYS * 86400, path="/",
                        secure=True, httponly=False, samesite="lax")


def clear_session_cookies(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=True, samesite="lax")


def ensure_csrf_cookie(request, response) -> str:
    """Pre-session double-submit token (login forms). Returns the value the form must echo."""
    value = request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(24)
    response.set_cookie(CSRF_COOKIE, value, max_age=SESSION_DAYS * 86400, path="/", secure=True,
                        httponly=False, samesite="lax")
    return value


def require_csrf(request, submitted: Optional[str], session: Optional[Session] = None) -> None:
    """Double submit: the cookie, and the header or form value, must match (and the session's, if any)."""
    cookie = request.cookies.get(CSRF_COOKIE) or ""
    given = submitted or request.headers.get(CSRF_HEADER) or ""
    if not cookie or not given or not hmac.compare_digest(cookie, given):
        raise CsrfError()
    if session is not None and not hmac.compare_digest(session.csrf, given):
        raise CsrfError()
