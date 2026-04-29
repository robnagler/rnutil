"""WWOZ livewire music calendar scraper

:copyright: Copyright (c) 2026 Robert Nagler.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc
from pykern import pkjson, pkinspect
import contextlib
import datetime
import inspect
import re
import requests
import zoneinfo

_TZ = zoneinfo.ZoneInfo("America/Chicago")
_URL = "https://wwoz.org/calendar/livewire-music"


def livewire(date=None, table=False):
    """Fetch and print WWOZ livewire music calendar.

    Args:
        date (str): YYYY-MM-DD, defaults to today Chicago time
        table (bool): print as text table instead of JSON
    """
    if date is None:
        date = datetime.datetime.now(tz=_TZ).strftime("%Y-%m-%d")
    html = requests.get(f"{_URL}?date={date}").text
    events = parse(html)
    print(as_table(events) if table else pkjson.dump_pretty(events))


def as_table(events):
    if not events:
        return ""

    def _fmt_time(iso):
        t = datetime.time.fromisoformat(iso[11:19])
        return f"{t.hour:02d}:{t.minute:02d}"

    times = [_fmt_time(e.time) for e in events]
    tw = max(len(t) for t in times)
    vw = max(len(e.venue) for e in events)
    bw = max(len(e.band) for e in events)
    fmt = f"{{:<{tw}}}  {{:<{vw}}}  {{}}"
    lines = [fmt.format("time", "venue", "band")]
    lines.append("-" * (tw + 2 + vw + 2 + bw))
    for t, e in zip(times, events):
        lines.append(fmt.format(t, e.venue, e.band))
    return "\n".join(lines)


def parse(html):
    return _Parser(html).result


class _Parser:
    def __init__(self, html):
        self._lines = html.splitlines()
        self._lineno = 0
        self._xpath = _XPath()
        try:
            self._find_calendar()
            date = self._date_from_widget()
            events = []
            while (venue := self._find_venue()) is not None:
                with self._path(venue):
                    while (event := self._find_event(date)) is not None:
                        events.append(event.pkupdate(venue=venue))
            events.sort(key=lambda e: e.time)
            self.result = events
        except Exception as e:
            pkinspect.append_exception_reason(e, self._xpath.stack_as_str())
            raise

    @contextlib.contextmanager
    def _path(self, element):
        self._xpath.push(element)
        pkdc("{}", element)
        yield
        self._xpath.pop()

    def _pop(self):
        self._lineno += 1
        return self._lines.pop(0)

    def _find_calendar(self):
        while self._lines and "livewire-calendar-widget" not in self._lines[0]:
            self._pop()

    def _date_from_widget(self):
        text = self._lines[0] + (self._lines[1] if len(self._lines) > 1 else "")
        m = re.search(r'data-current-date="(\d{4}-\d{2}-\d{2})"', text)
        if m:
            return datetime.date.fromisoformat(m.group(1))
        return datetime.datetime.now(tz=_TZ).date()

    def _find_venue(self):
        while self._lines:
            l = self._pop()
            if "</section>" in l:
                return None
            if "/organizations/" in l:
                return self._lines[0].replace("</a>", "").strip()
        return None

    def _find_event(self, date):
        while self._lines:
            l = self._pop()
            if "/organizations/" in l or "</section" in l:
                self._lines.insert(0, l)
                self._lineno -= 1
                return None
            if "/events/" in l:
                band = self._lines[0].replace("</a>", "").strip()
                with self._path(band):
                    t = self._find_time(date)
                return PKDict(band=band, time=t.isoformat())
        return None

    def _find_time(self, date):
        while self._lines:
            m = re.search(r"(\d+):(\d+)(am|pm)", self._lines[0])
            if m:
                self._pop()
                h = int(m.group(1))
                mins = int(m.group(2))
                if m.group(3) == "pm":
                    h = h % 12 + 12
                else:
                    h = h % 12
                return datetime.datetime(
                    date.year, date.month, date.day, h, mins,
                    tzinfo=_TZ,
                )
            self._pop()
        raise ValueError(f"time not found at line {self._lineno}")


class _XPath:
    def __init__(self):
        self._stack = []

    def push(self, key):
        f = inspect.currentframe().f_back.f_back.f_back
        self._stack.append(PKDict(key=key, func=f.f_code.co_name, line=f.f_lineno))

    def pop(self):
        self._stack.pop()

    def __str__(self):
        return "/".join(str(e.key) for e in self._stack)

    def stack_as_str(self):
        res = f"xpath={self}\n"
        for e in self._stack:
            res += f"  {e.func}:{e.line} {str(e.key):.100}\n"
        return res
