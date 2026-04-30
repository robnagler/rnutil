"""WWOZ livewire music calendar scraper

:copyright: Copyright (c) 2026 Robert Nagler.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkio, pkjson, pkinspect
import contextlib
import datetime
import inspect
import re
import requests
import zoneinfo

_TZ = zoneinfo.ZoneInfo("America/Chicago")
_URL = "https://wwoz.org/calendar/livewire-music"


def livewire(date=None, table=False, html_file=None):
    """Fetch and print WWOZ livewire music calendar.

    Args:
        date (str): YYYY-MM-DD, defaults to today Chicago time
        table (bool): print as text table instead of JSON
        html_file (str): read HTML from this file instead of fetching
    """

    def _html():
        if html_file:
            return pkio.read_text(html_file)
        d = date or datetime.datetime.now(tz=_TZ).strftime("%Y-%m-%d")
        return requests.get(f"{_URL}?date={d}").text

    return _Output(table, _parse(_html())).as_str()


def visitors(days=60, html_dir=None):
    """Find out-of-town acts appearing on at most 2 dates over the next N days.

    Args:
        days (int): how many days ahead to search [60]
        html_dir (str): read HTML files from this directory instead of fetching
    """

    def _sources():
        if html_dir:
            for p in pkio.sorted_glob(f"{html_dir}/*.html"):
                yield pkio.read_text(p)
        else:
            t = datetime.datetime.now(tz=_TZ).date()
            for i in range(int(days)):
                d = t + datetime.timedelta(days=i)
                pkdlog("{}", d)
                yield requests.get(f"{_URL}?date={d}").text

    def _fetch():
        r = PKDict()
        for html in _sources():
            for e in _parse(html):
                r.setdefault(e.band, []).append(e)
        return r

    def _filter(by_band):
        for v in by_band.values():
            if len(set(x.date for x in v)) <= 2:
                yield from v

    return _Output(True, _filter(_fetch())).as_str()


class _Output:
    def __init__(self, table, events):
        self._events = list(events)
        self._table = table

    def as_str(self):
        if not self._table:
            return pkjson.dump_pretty(self._events)
        if not self._events:
            return ""
        return self._build(self._widths())

    def _build(self, widths):
        r = [self._row(widths, "date" if widths.date else "", "time", "venue", "band")]
        r.append(
            "-"
            * (
                (widths.date + 2 if widths.date else 0)
                + widths.time
                + 2
                + widths.venue
                + 2
                + widths.band
            )
        )
        for e in sorted(self._events, key=lambda x: (x.date, x.time)):
            r.append(
                self._row(
                    widths,
                    e.date if widths.date else "",
                    self._fmt_time(e.time),
                    e.venue,
                    e.band,
                )
            )
        return "\n".join(r) + "\n"

    def _fmt_time(self, hhmm):
        hhmm = hhmm % 2400
        return f"{hhmm // 100:02d}:{hhmm % 100:02d}"

    def _row(self, widths, date, time, venue, band):
        return (
            f"{date:<{widths.date}}  " if widths.date else ""
        ) + f"{time:<{widths.time}}  {venue:<{widths.venue}}  {band}"

    def _widths(self):
        return PKDict(
            date=len(self._events[0].date) if hasattr(self._events[0], "date") else 0,
            time=max(len(self._fmt_time(e.time)) for e in self._events),
            venue=max(len(e.venue) for e in self._events),
            band=max(len(e.band) for e in self._events),
        )


class _Parser:
    def __init__(self, html):
        self._lines = html.splitlines()
        self._lineno = 0
        self._xpath = _XPath()
        try:
            self._find_calendar()
            self._date = self._date_from_widget()
            self.result = self._build()
        except Exception as e:
            pkinspect.append_exception_reason(e, self._xpath.stack_as_str())
            raise

    def _build(self):
        r = []
        while v := self._find_venue():
            with self._path(v):
                while e := self._find_event():
                    r.append(e.pkupdate(venue=v, date=str(self._date)))
        r.sort(key=lambda e: e.time)
        return r

    def _date_from_widget(self):
        t = self._lines[0] + (self._lines[1] if len(self._lines) > 1 else "")
        if m := re.search(r'data-current-date="(\d{4}-\d{2}-\d{2})"', t):
            return datetime.date.fromisoformat(m.group(1))
        return datetime.datetime.now(tz=_TZ).date()

    def _find_calendar(self):
        while self._lines and "livewire-calendar-widget" not in self._lines[0]:
            self._pop()

    def _find_event(self):
        while self._lines:
            l = self._pop()
            if "/organizations/" in l or "</section" in l:
                self._lines.insert(0, l)
                self._lineno -= 1
                return None
            if "/events/" in l:
                b = self._lines[0].replace("</a>", "").strip()
                with self._path(b):
                    t = self._find_time()
                return PKDict(band=b, time=t)
        return None

    def _find_time(self):
        while self._lines:
            if m := re.search(r"(\d+):(\d+)(am|pm)", self._lines[0]):
                self._pop()
                h = int(m.group(1))
                n = int(m.group(2))
                h = h % 12 + (12 if m.group(3) == "pm" else 0)
                t = h * 100 + n
                return t + 2400 if t < 400 else t
            self._pop()
        raise ValueError(f"time not found at line {self._lineno}")

    def _find_venue(self):
        while self._lines:
            l = self._pop()
            if "</section>" in l:
                return None
            if "/organizations/" in l:
                return self._lines[0].replace("</a>", "").strip()
        return None

    @contextlib.contextmanager
    def _path(self, element):
        self._xpath.push(element)
        pkdc("{}", element)
        yield
        self._xpath.pop()

    def _pop(self):
        self._lineno += 1
        return self._lines.pop(0)


class _XPath:
    def __init__(self):
        self._stack = []

    def __str__(self):
        return "/".join(str(e.key) for e in self._stack)

    def pop(self):
        self._stack.pop()

    def push(self, key):
        f = inspect.currentframe().f_back.f_back.f_back
        self._stack.append(PKDict(key=key, func=f.f_code.co_name, line=f.f_lineno))

    def stack_as_str(self):
        r = f"xpath={self}\n"
        for e in self._stack:
            r += f"  {e.func}:{e.line} {str(e.key):.100}\n"
        return r


def _parse(html):
    return _Parser(html).result
