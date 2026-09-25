"""No-AI mode: an offline rule-based parser for common EN/RO commands.

It needs no account, no key and no internet, and maps what it understands to
the very same actions the LLMs call. It is deliberately small and predictable:
if it is not sure, it asks ("La ce oră?") or offers to save the text as a note,
it never guesses a wrong time silently.

    amintește-mi la 5 să sun la bancă     -> reminder.create (17:00 if it is afternoon)
    pune alarma la 7:30                   -> alarm.set 07:30
    notează: idee breloc                  -> note.create
    remind me at 5 to call the bank       -> reminder.create
    timer 10 minutes / cronometru 10 minute, focus 25, add milk to the shopping list,
    adaugă lapte și ouă pe lista de cumpărături, scrie-i lui Ana că întârzii ...

Matching runs on a diacritic-free lowercase copy of the text that has exactly
the same length as the original, so extracted text keeps its diacritics.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base import AskContext, AskResult, summarize

# --------------------------------------------------------------- helpers --

_RO_CHARS = set("ăâîșțşţĂÂÎȘȚŞŢ")
_RO_WORDS = re.compile(
    r"\b(aminteste|adu-mi|noteaza|pune|alarma|trezeste|maine|poimaine|azi|astazi|diseara|peste|adauga|lista|"
    r"scrie|scrie-i|trimite-i|cronometru|minutar|minute|secunde|ore|ora|sa|si|ca|la|pe|de|seara|dimineata)\b"
)
_EN_WORDS = re.compile(r"\b(remind|me|note|set|alarm|wake|timer|minutes|add|to|the|list|at|tomorrow|today)\b")


def fold(text: str) -> str:
    """Lowercase, strip diacritics, keep the length (one char in, one char out)."""
    out = []
    for c in text:
        base = unicodedata.normalize("NFD", c)[0] if c else c
        out.append(base.lower() if len(base.lower()) == 1 else c)
    return "".join(out)


def detect_lang(text: str) -> str:
    if any(c in _RO_CHARS for c in text):
        return "ro"
    f = fold(text)
    ro = len(_RO_WORDS.findall(f))
    en = len(_EN_WORDS.findall(f))
    return "ro" if ro > en else "en"


_NUM_WORDS = {
    "o": 1, "un": 1, "una": 1, "unu": 1, "a": 1, "an": 1, "one": 1,
    "doua": 2, "doi": 2, "two": 2, "trei": 3, "three": 3, "patru": 4, "four": 4,
    "cinci": 5, "five": 5, "sase": 6, "six": 6, "sapte": 7, "seven": 7, "opt": 8, "eight": 8,
    "noua": 9, "nine": 9, "zece": 10, "ten": 10, "cincisprezece": 15, "fifteen": 15,
    "douazeci": 20, "twenty": 20, "treizeci": 30, "thirty": 30, "patruzeci": 40, "forty": 40,
}
_NUM = r"(\d{1,3}|" + "|".join(sorted(_NUM_WORDS, key=len, reverse=True)) + r")"


def _num(s: str) -> int:
    return int(s) if s.isdigit() else _NUM_WORDS[s]


_UNIT_SECONDS = [
    (re.compile(r"^(sec|secunda|secunde|second|seconds|s)$"), 1),
    (re.compile(r"^(min|mins|minut|minute|minutes|m)$"), 60),
    (re.compile(r"^(h|ora|ore|hour|hours|ceas|ceasuri)$"), 3600),
]
_UNITS = r"(secunde|secunda|seconds|second|sec|minute|minutes|minut|mins|min|ore|ora|hours|hour|h)"


def _unit_seconds(u: str) -> int:
    for rx, s in _UNIT_SECONDS:
        if rx.match(u):
            return s
    return 60


# Time of day: "la 5", "la ora 17:30", "at 5pm", "at 7.30 am", "la 5 și jumătate", "la 9 dimineața"
_PART = (r"(dimineata|dimineața|seara|diseara|dupa-amiaza|dupa amiaza|dupa-masa|noaptea|"
         r"in the morning|in the evening|in the afternoon|tonight|at night)")
_AT_TIME = re.compile(
    r"\b(?:la ora|pe la|la|at|around|by)\s+(\d{1,2})(?:[:.h](\d{2}))?"
    r"(\s*(?:si jumatate|si un sfert|fara un sfert))?"
    r"(?:\s*(am|pm|a\.m\.|p\.m\.)(?![a-z]))?"
    r"(?:\s+" + _PART + r")?(?![\d:])"
)
_BARE_TIME = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?\b")  # "7:30" with no "la"/"at"
_RELATIVE = re.compile(r"\b(?:peste|in|after|dupa)\s+" + _NUM + r"\s*(?:de\s+)?" + _UNITS + r"\b")
_HALF_HOUR = re.compile(r"\b(?:peste|in)\s+(?:o\s+)?(?:jumatate de ora|half an hour)\b")
_DAY = re.compile(r"\b(azi|astazi|today|maine|tomorrow|poimaine|diseara|tonight)\b")


@dataclass
class TimeHit:
    when: Optional[dt.datetime]
    span: Tuple[int, int]
    spans: List[Tuple[int, int]] = field(default_factory=list)


def apply_part(h: int, ampm: str, part: str) -> Tuple[int, bool]:
    """Apply am/pm or a part of day ("seara", "dimineața", "noaptea"...). Returns (hour, was_explicit)."""
    part = part or ""
    if "noaptea" in part or "at night" in part:
        return (0 if h == 12 else h + 12 if 9 <= h < 12 else h), True
    if ampm.startswith("p") or any(p in part for p in ("seara", "diseara", "dupa", "evening", "afternoon", "tonight")):
        return (h + 12 if h < 12 else h), True
    if ampm.startswith("a") or "dimineata" in part or "morning" in part:
        return (0 if h == 12 else h), True
    return h, False


def _resolve_hour(h: int, m: int, ampm: str, part: str, day_offset: Optional[int], now: dt.datetime,
                  prefer_future: bool = True) -> dt.datetime:
    h, explicit = apply_part(h, ampm, part)
    pm = am = explicit
    base = now.replace(second=0, microsecond=0)
    if day_offset == 0:  # "azi la 5" / "tonight at 9": the soonest reading that is still today
        cands = [base.replace(hour=h, minute=m)]
        if not (pm or am) and 1 <= h < 12:
            cands.append(base.replace(hour=h + 12, minute=m))
        future = [c for c in cands if c > now]
        return min(future) if future else cands[0]
    if day_offset is not None:
        day = (base + dt.timedelta(days=day_offset)).replace(hour=0, minute=0)
        if not (pm or am) and 1 <= h <= 6:
            h += 12  # "mâine la 5" means 17:00; nobody sets 5 a.m. reminders by accident
        return day.replace(hour=h, minute=m)
    cands = [base.replace(hour=h, minute=m)]
    if not (pm or am) and 1 <= h < 12:
        cands.append(base.replace(hour=h + 12, minute=m))
    cands += [c + dt.timedelta(days=1) for c in cands]
    future = [c for c in cands if c > now] if prefer_future else cands
    return min(future) if future else cands[0]


def find_time(f: str, now: dt.datetime) -> Optional[TimeHit]:
    """Find one time expression in folded text; return the local datetime and the spans to cut."""
    spans: List[Tuple[int, int]] = []
    day_offset = None
    dm = _DAY.search(f)
    if dm:
        w = dm.group(1)
        day_offset = {"azi": 0, "astazi": 0, "today": 0, "diseara": 0, "tonight": 0,
                      "maine": 1, "tomorrow": 1, "poimaine": 2}[w]
        spans.append(dm.span())

    hm = _HALF_HOUR.search(f)
    if hm:
        spans.append(hm.span())
        return TimeHit(now + dt.timedelta(minutes=30), hm.span(), spans)
    rm = _RELATIVE.search(f)
    if rm:
        secs = _num(rm.group(1)) * _unit_seconds(rm.group(2))
        spans.append(rm.span())
        return TimeHit((now + dt.timedelta(seconds=secs)).replace(microsecond=0), rm.span(), spans)

    am_ = _AT_TIME.search(f)
    if am_:
        h = int(am_.group(1))
        m = int(am_.group(2) or 0)
        frac = (am_.group(3) or "").strip()
        if frac == "si jumatate":
            m = 30
        elif frac == "si un sfert":
            m = 15
        elif frac == "fara un sfert":
            h, m = (h - 1) % 24, 45
        if h > 23 or m > 59:
            return None
        part = am_.group(5) or ""
        if dm and dm.group(1) in ("diseara", "tonight"):
            part = part or "seara"
        spans.append(am_.span())
        return TimeHit(_resolve_hour(h, m, am_.group(4) or "", part, day_offset, now), am_.span(), spans)
    bm = _BARE_TIME.search(f)
    if bm:
        h, m = int(bm.group(1)), int(bm.group(2))
        if h > 23 or m > 59:
            return None
        spans.append(bm.span())
        return TimeHit(_resolve_hour(h, m, bm.group(3) or "", "", day_offset, now), bm.span(), spans)
    if dm:
        return TimeHit(None, dm.span(), spans)  # a day but no hour: ask
    return None


def _cut(text: str, spans: List[Tuple[int, int]]) -> str:
    keep = list(text)
    for a, b in spans:
        for i in range(a, b):
            keep[i] = "\0"
    return re.sub(r"\s{2,}", " ", "".join(keep).replace("\0", " ")).strip()


def _tidy(s: str) -> str:
    return s.strip(" \t\n,.;:!-–—\"'")


def _strip_lead(s: str, words: str) -> str:
    return re.sub(r"^(?:" + words + r")\b\s*", "", s, flags=re.IGNORECASE).strip()


def _split_items(s: str) -> List[str]:
    parts = re.split(r",|;|\bsi\b|\bși\b|\band\b|\bplus\b", s)
    return [p.strip(" .") for p in parts if p.strip(" .")]


# --------------------------------------------------------------- patterns --

_NOTE = re.compile(
    r"^\s*(?:noteaza(?:-ti|-mi)?|noteaza-ti|nota|scrie(?:-ti)?(?: undeva)?|salveaza(?: o notita)?|"
    r"tine minte|take a note|make a note|write down|note down|note|save a note|jot down)\b"
    r"(?:\s+(?:ca|that))?\s*[:,\-–]?\s*(.+)$",
    re.S,
)
_MSG = re.compile(
    r"^\s*(?:scrie-i|trimite-i|zi-i|spune-i)\s+(?:un mesaj\s+)?(?:lui|la|pentru)?\s*([\w\-]+)\s*"
    r"(?:ca|sa|:|,)?\s*(.+)$"
    r"|^\s*(?:text|message|tell|send a message to|draft a message to|write to)\s+(?!me\b|us\b|you\b)([\w\-]+)\s*"
    r"(?:that|saying|:|,)?\s*(.+)$",
    re.S,
)
_LIST = re.compile(
    r"^\s*(?:adauga|pune|baga|scrie)\s+(.+?)\s+(?:pe|in|la)\s+lista(?:\s+(?:de|mea de|cu))?\s*([\w\-]+)?\s*$"
    r"|^\s*(?:add|put)\s+(.+?)\s+(?:to|on)\s+(?:my\s+|the\s+)?([\w\-]+)\s+list\s*$",
    re.S,
)
_ALARM = re.compile(
    r"^\s*(?:(?:pune|seteaza|fa|pune-mi|seteaza-mi)\s+(?:o\s+)?alarma|alarma|trezeste-ma|scoala-ma|"
    r"(?:set|make)\s+(?:an?\s+)?alarm|alarm|wake me(?: up)?)\b(.*)$",
    re.S,
)
_TIMER = re.compile(
    r"^\s*(?:(?:pune|porneste|seteaza|start|set|pune-mi)\s+(?:un\s+|a\s+)?)?(?:cronometru|minutar|timer|countdown)"
    r"\s*(?:de|pentru|for|of)?\s*" + _NUM + r"\s*(?:de\s+)?" + _UNITS + r"\b"
    r"|^\s*(?:(?:set|start)\s+)?(?:a\s+)?" + _NUM + r"[\s-]*" + _UNITS + r"\s+timer\b",
    re.S,
)
_FOCUS = re.compile(
    r"^\s*(?:(?:start|porneste|incepe|pune)\s+(?:un\s+|a\s+)?)?(?:focus|mod(?:ul)? focus|concentrare|pomodoro)"
    r"(?:\s*(?:de|for|pentru)?\s*" + _NUM + r"\s*(?:de\s+)?(?:minute|minutes|min)?)?\s*$",
    re.S,
)
_REMIND = re.compile(
    r"^\s*(?:aminteste-mi|aminteste mi|aminteste-ne|adu-mi aminte|fa-mi un memento|pune(?:-mi)? un memento|"
    r"memento|remind me|reminder|set a reminder)\b\s*(.*)$",
    re.S,
)

_DAYS_ALL = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_ALARM_DAYS = [
    (re.compile(r"\b(zilnic|in fiecare zi|every day|everyday|daily)\b"), _DAYS_ALL),
    (re.compile(r"\b(in zilele lucratoare|zilele lucratoare|in timpul saptamanii|luni(?:-| pana | - )vineri|"
                r"weekdays|on weekdays|monday to friday)\b"), _DAYS_ALL[:5]),
    (re.compile(r"\b(in weekend|weekendul|on weekends|weekends|weekend)\b"), ["sat", "sun"]),
]
_DAY_NAMES = {
    "lunea": "mon", "martea": "tue", "miercurea": "wed", "joia": "thu", "vinerea": "fri", "sambata": "sat",
    "duminica": "sun", "mondays": "mon", "tuesdays": "tue", "wednesdays": "wed", "thursdays": "thu",
    "fridays": "fri", "saturdays": "sat", "sundays": "sun",
}


@dataclass
class Parsed:
    action: Optional[str] = None
    args: dict = field(default_factory=dict)
    ask: str = ""  # a clarifying question instead of an action


def parse(text: str, now: dt.datetime, lang: str) -> Optional[Parsed]:
    """Map one utterance to one action, a clarifying question, or None."""
    t = text.strip()
    f = fold(t)
    ro = lang == "ro"

    m = _REMIND.match(f)
    if m:
        start = m.start(1)
        rest_f, rest = f[start:], t[start:]
        hit = find_time(rest_f, now)
        what = _tidy(_strip_lead(_cut(rest, hit.spans if hit else []), r"sa|să|ca|că|de|despre|to|that|about|of"))
        if not hit or hit.when is None:
            return Parsed(ask=("La ce oră să-ți amintesc?" if ro else "What time should I remind you?")
                          + (f" ({what})" if what else ""))
        if not what:
            return Parsed(ask="Ce să-ți amintesc?" if ro else "What should I remind you about?")
        return Parsed("reminder.create", {"when": hit.when.strftime("%Y-%m-%dT%H:%M"), "text": what})

    m = _ALARM.match(f)
    if m:
        rest_f = m.group(1)
        days: List[str] = []
        for rx, ds in _ALARM_DAYS:
            if rx.search(rest_f):
                days = list(ds)
                break
        if not days:
            days = [d for w, d in _DAY_NAMES.items() if re.search(r"\b" + w + r"\b", rest_f)]
            days = [d for d in _DAYS_ALL if d in days]
        bare = re.sub(r"^\s*(?:for|pentru)\s+", "", rest_f)
        am_ = _AT_TIME.search(rest_f) or _AT_TIME.search("la " + bare.strip())
        bm = None if am_ else _BARE_TIME.search(rest_f)
        if not am_ and not bm:
            return Parsed(ask="La ce oră pun alarma?" if ro else "What time should the alarm ring?")
        if am_:
            h, mi = int(am_.group(1)), int(am_.group(2) or 0)
            frac = (am_.group(3) or "").strip()
            mi = 30 if frac == "si jumatate" else 15 if frac == "si un sfert" else mi
            if frac == "fara un sfert":
                h, mi = (h - 1) % 24, 45
            ampm, part = am_.group(4) or "", am_.group(5) or ""
        else:
            h, mi, ampm, part = int(bm.group(1)), int(bm.group(2)), bm.group(3) or "", ""
        h, _ = apply_part(h, ampm, part)
        if h > 23 or mi > 59:
            return Parsed(ask="Ora nu pare validă. La ce oră?" if ro else "That time looks wrong. What time?")
        return Parsed("alarm.set", {"hhmm": f"{h:02d}:{mi:02d}", "days": days, "label": ""})

    m = _TIMER.match(f)
    if m:
        n, u = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        return Parsed("timer.start", {"seconds": _num(n) * _unit_seconds(u), "label": ""})

    m = _FOCUS.match(f)
    if m:
        return Parsed("focus.start", {"minutes": _num(m.group(1)) if m.group(1) else 25, "label": ""})

    m = _LIST.match(f)
    if m:
        if m.group(1):
            items_span, name = m.span(1), m.group(2) or ("cumparaturi" if ro else "shopping")
        else:
            items_span, name = m.span(3), m.group(4)
        items = _split_items(t[items_span[0]:items_span[1]])
        if name in ("cumparaturi", "shopping", "groceries"):
            name = "cumpărături" if ro else "shopping"
        return Parsed("list.add", {"list": name, "items": items})

    m = _MSG.match(f)
    if m:
        if m.group(1):
            to_span, body_span = m.span(1), m.span(2)
        else:
            to_span, body_span = m.span(3), m.span(4)
        to = t[to_span[0]:to_span[1]]
        body = _tidy(t[body_span[0]:body_span[1]])
        if body:
            return Parsed("message.draft", {"to": to[:1].upper() + to[1:], "text": body, "channel": "any"})

    m = _NOTE.match(f)
    if m:
        body = _tidy(t[m.start(1):])
        if body:
            return Parsed("note.create", {"text": body, "tags": []})
    return None


class RulesProvider:
    """No AI: the offline parser. Always available; the other providers fall back to it."""

    name = "rules"

    def ask(self, ctx: AskContext) -> AskResult:
        p = parse(ctx.text, ctx.now, ctx.lang)
        ro = ctx.lang == "ro"
        if p is None:
            say = ("Fără AI înțeleg doar comenzi simple: notițe, mementouri, alarme, cronometre, liste. "
                   "Îl salvez ca notiță?") if ro else \
                  ("Without AI I only understand simple commands: notes, reminders, alarms, timers, lists. "
                   "Save it as a note?")
            chips = ["Salvează ca notiță", "Anulează"] if ro else ["Save as note", "Cancel"]
            return AskResult(say=say, provider=self.name, mode=ctx.mode, face="confused", chips=chips)
        if p.ask:
            return AskResult(say=p.ask, provider=self.name, mode=ctx.mode, face="surprised")
        r = ctx.run(p.action, p.args, source=self.name)
        if not r.ok:
            say = ("N-am putut: " if ro else "I couldn't: ") + r.error
            return AskResult(say=say, provider=self.name, mode=ctx.mode, face="confused", actions=[r])
        return summarize(self.name, ctx.mode, r.say, [r])
