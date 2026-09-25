"""Run a SOUL action: validate, store, confirm (in the user's language).

Every mode ends here. The dispatcher never raises for bad input from a model
or a user; it returns ActionResult(ok=False, error=...) so an LLM can read the
error as a tool result and correct itself.
"""
from __future__ import annotations

import datetime as dt
from typing import Callable, List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError

from .actions import ACTIONS, DAYS, TOOL_TO_ACTION
from .state import StateStore

Lang = str  # "ro" | "en"

DAY_WORDS = {
    "ro": ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}


class ActionResult(BaseModel):
    ok: bool
    action: str
    id: Optional[int] = None
    say: str = ""
    card: Optional[dict] = None  # {title, body, icon} for the round screen
    data: dict = Field(default_factory=dict)
    error: str = ""


def _t(lang: Lang, ro: str, en: str) -> str:
    return ro if lang == "ro" else en


def _dur(seconds: int, lang: Lang) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    parts = []
    if h:
        parts.append(_t(lang, f"{h} {'oră' if h == 1 else 'ore'}", f"{h} {'hour' if h == 1 else 'hours'}"))
    if m:
        parts.append(_t(lang, f"{m} {'minut' if m == 1 else 'minute'}", f"{m} {'minute' if m == 1 else 'minutes'}"))
    if s:
        parts.append(_t(lang, f"{s} {'secundă' if s == 1 else 'secunde'}", f"{s} {'second' if s == 1 else 'seconds'}"))
    return _t(lang, " și ", " and ").join(parts)


class Dispatcher:
    def __init__(self, state: StateStore, timezone: str = "Europe/Bucharest",
                 clock: Optional[Callable[[], dt.datetime]] = None):
        self.state = state
        self.tz = ZoneInfo(timezone)
        self._clock = clock

    def now(self) -> dt.datetime:
        return self._clock() if self._clock else dt.datetime.now(self.tz)

    @staticmethod
    def stamp(t: dt.datetime) -> str:
        return t.strftime("%Y-%m-%dT%H:%M")

    # ------------------------------------------------------------------------
    def dispatch(self, device: str, name: str, args: dict, lang: Lang = "en", source: str = "app",
                 now: Optional[dt.datetime] = None) -> ActionResult:
        name = TOOL_TO_ACTION.get(name, name)
        spec = ACTIONS.get(name)
        if spec is None:
            return ActionResult(ok=False, action=name, error=f"unknown action '{name}'")
        if not isinstance(args, dict):
            return ActionResult(ok=False, action=name, error="arguments must be an object")
        try:
            a = spec.model.model_validate(args)
        except ValidationError as e:
            msg = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors())
            return ActionResult(ok=False, action=name, error=f"invalid arguments: {msg}")
        now = now or self.now()
        handler = getattr(self, "_" + name.replace(".", "_"))
        try:
            return handler(device, a, lang, source, now)
        except ValueError as e:  # bad device id or a semantic check
            return ActionResult(ok=False, action=name, error=str(e))

    # ------------------------------------------------------------- handlers --
    def _note_create(self, device, a, lang, source, now) -> ActionResult:
        i = self.state.add(device, "note", {"text": a.text, "tags": a.tags}, self.stamp(now), source=source)
        return ActionResult(ok=True, action="note.create", id=i, say=_t(lang, "Am notat.", "Noted."),
                            card={"title": _t(lang, "Notiță", "Note"), "body": a.text, "icon": "note"})

    def _reminder_create(self, device, a, lang, source, now) -> ActionResult:
        when = dt.datetime.strptime(a.when, "%Y-%m-%dT%H:%M").replace(tzinfo=self.tz)
        if when < now.replace(second=0, microsecond=0):
            raise ValueError(f"that time has already passed (now is {self.stamp(now)})")
        i = self.state.add(device, "reminder", {"text": a.text}, self.stamp(now), due=a.when, source=source)
        day = self._day_word(when.date(), now.date(), lang)
        hm = when.strftime("%H:%M")
        return ActionResult(
            ok=True, action="reminder.create", id=i,
            say=_t(lang, f"Gata, îți amintesc {day} la {hm}: {a.text}.", f"Done, I'll remind you {day} at {hm}: {a.text}."),
            card={"title": f"{day} {hm}".strip(), "body": a.text, "icon": "reminder"},
            data={"when": a.when},
        )

    def _alarm_set(self, device, a, lang, source, now) -> ActionResult:
        nxt = self.next_alarm(a.hhmm, a.days, now)
        days = [d for d in DAYS if d in a.days]
        i = self.state.add(device, "alarm", {"hhmm": a.hhmm, "days": days, "label": a.label},
                           self.stamp(now), due=self.stamp(nxt), source=source)
        if not days:
            rep = self._day_word(nxt.date(), now.date(), lang)
        elif len(days) == 7:
            rep = _t(lang, "în fiecare zi", "every day")
        elif days == DAYS[:5]:
            rep = _t(lang, "în zilele lucrătoare", "on weekdays")
        else:
            rep = ", ".join(DAY_WORDS[lang if lang == "ro" else "en"][DAYS.index(d)] for d in days)
        return ActionResult(
            ok=True, action="alarm.set", id=i,
            say=_t(lang, f"Alarmă pusă la {a.hhmm}, {rep}.", f"Alarm set for {a.hhmm}, {rep}."),
            card={"title": a.hhmm, "body": a.label or rep, "icon": "alarm"},
            data={"next": self.stamp(nxt), "days": days},
        )

    def _timer_start(self, device, a, lang, source, now) -> ActionResult:
        ends = now + dt.timedelta(seconds=a.seconds)
        i = self.state.add(device, "timer", {"seconds": a.seconds, "label": a.label,
                                             "ends_at": ends.isoformat(timespec="seconds")},
                           self.stamp(now), due=self.stamp(ends), source=source)
        d = _dur(a.seconds, lang)
        return ActionResult(ok=True, action="timer.start", id=i,
                            say=_t(lang, f"Cronometru pornit: {d}.", f"Timer started: {d}."),
                            card={"title": d, "body": a.label, "icon": "timer"},
                            data={"ends_at": ends.isoformat(timespec="seconds")})

    def _focus_start(self, device, a, lang, source, now) -> ActionResult:
        ends = now + dt.timedelta(minutes=a.minutes)
        i = self.state.add(device, "focus", {"minutes": a.minutes, "label": a.label,
                                             "ends_at": ends.isoformat(timespec="seconds")},
                           self.stamp(now), due=self.stamp(ends), source=source)
        return ActionResult(ok=True, action="focus.start", id=i,
                            say=_t(lang, f"Focus {a.minutes} de minute. Te las în pace.",
                                   f"Focus for {a.minutes} minutes. I'll keep quiet."),
                            card={"title": f"Focus {a.minutes}'", "body": a.label, "icon": "focus"},
                            data={"ends_at": ends.isoformat(timespec="seconds")})

    def _message_draft(self, device, a, lang, source, now) -> ActionResult:
        i = self.state.add(device, "draft", {"to": a.to, "text": a.text, "channel": a.channel},
                           self.stamp(now), source=source)
        return ActionResult(ok=True, action="message.draft", id=i,
                            say=_t(lang, f"Am pregătit mesajul pentru {a.to}. Îl trimiți din telefon.",
                                   f"Drafted a message to {a.to}. Send it from your phone."),
                            card={"title": _t(lang, f"Către {a.to}", f"To {a.to}"), "body": a.text, "icon": "message"})

    def _list_add(self, device, a, lang, source, now) -> ActionResult:
        items = [x.strip() for x in a.items if x.strip()]
        if not items:
            raise ValueError("no items to add")
        ids = [self.state.add(device, "list_item", {"list": a.list.lower(), "item": x}, self.stamp(now), source=source)
               for x in items]
        what = ", ".join(items)
        return ActionResult(ok=True, action="list.add", id=ids[-1],
                            say=_t(lang, f"Am adăugat pe lista {a.list}: {what}.", f"Added to your {a.list} list: {what}."),
                            card={"title": a.list, "body": "\n".join(items), "icon": "list"},
                            data={"ids": ids})

    def _answer_show(self, device, a, lang, source, now) -> ActionResult:
        card = {"title": a.title, "body": a.body, "icon": "answer"} if (a.title or a.body) else None
        i = self.state.add(device, "card", {"say": a.say, "title": a.title, "body": a.body}, self.stamp(now), source=source)
        return ActionResult(ok=True, action="answer.show", id=i, say=a.say, card=card)

    # ---------------------------------------------------------------- utils --
    def next_alarm(self, hhmm: str, days: List[str], now: dt.datetime) -> dt.datetime:
        h, m = map(int, hhmm.split(":"))
        base = now.replace(hour=h, minute=m, second=0, microsecond=0)
        for add in range(8):
            cand = base + dt.timedelta(days=add)
            if cand <= now:
                continue
            if not days or DAYS[cand.weekday()] in days:
                return cand
        return base + dt.timedelta(days=1)  # unreachable with valid days

    @staticmethod
    def _day_word(d: dt.date, today: dt.date, lang: Lang) -> str:
        delta = (d - today).days
        if delta == 0:
            return _t(lang, "azi", "today")
        if delta == 1:
            return _t(lang, "mâine", "tomorrow")
        if delta == 2 and lang == "ro":
            return "poimâine"
        return d.strftime("%d.%m") if lang == "ro" else d.strftime("%b %d")
