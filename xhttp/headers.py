from __future__ import division, absolute_import, print_function

import datetime
import re
import sys

import dateutil
import dateutil.parser

from . import exc

if sys.version_info[0] == 2:
    bytes, str = str, unicode # pragma: no flakes

__all__ = [ 'QListHeader', 'DateHeader', 'RangeHeader' ]

#
# QListHeader
# 

class QListHeader(object):
    _comma = re.compile(r"\s*,\s*")
    _semicolon = re.compile(r"\s*;\s*")

    def __init__(self, s):
        try: 
            items = self._comma.split(s)
            items = [ self._semicolon.split(item) for item in items ]
            items = [ t if len(t) == 2 else (t + ["q=1.0"]) for t in items ]
            items = [ (m, q.split('=')[1]) for (m, q) in items ] 
            items = [ (float(q), i, m) for (i, (m, q)) in enumerate(items) ]
            self.items = sorted(items, key=lambda qiv: (1-qiv[0], qiv[1], qiv[2]))
        except:
            self.items = []

    def __str__(self):
        return ",".join((v + (";q={0}".format(q) if q != 1.0 else ""))
                        for (q, i, v) in sorted(self.items, key=lambda qiv: qiv[1]))

    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, repr(str(self)))

    def negotiate(self, keys):
        for (_, _, v) in self.items:
            if any(v.lower() == k.lower() for k in keys):
                return v
        return None

    def negotiate_language(self, tags):
        pass
        # TODO: implement this

    def negotiate_mime(self, keys):
        for (_, _, v) in self.items:
            # match anything
            if (v == "*/*") and keys:
                return keys[0]
            # match exactly
            for k in keys:
                if k.lower() == v.lower():
                    return k
            # match partially
            for k in keys:
                s = k.split("/")[0] + "/*"
                if s.lower() == v.lower():
                    return k
        return None

#
# DateHeader
#

class DateHeader(object):
    WEEKDAYS = 'Mon Tue Wed Thu Fri Sat Sun'.split()
    MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    TZ_UTC = dateutil.tz.tzutc()

    def __init__(self, x, tz=TZ_UTC):
        self.tz = tz 
        if isinstance(x, bytes):
            x = x.decode('us-ascii')
        if isinstance(x, str):
            self.timestamp = self.parse(x)
        elif isinstance(x, int):
            self.timestamp = x
        elif isinstance(x, float):
            self.timestamp = int(x)
        else:
            raise ValueError("Unsupported type {0}".format(type(x).__name__))

    def __str__(self):
        dt = datetime.datetime.utcfromtimestamp(self.timestamp)
        return "{0}, {1:02} {2} {3} {4:02}:{5:02}:{6:02} GMT".format(
            DateHeader.WEEKDAYS[dt.weekday()], 
            dt.day,
            DateHeader.MONTHS[dt.month-1],
            dt.year,
            dt.hour,
            dt.minute,
            dt.second)

    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, repr(str(self)))

    def __eq__(self, other):
        return not self < other and not other < self

    def __ne__(self, other):
        return self < other or other < self

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return not self < other

    def __le__(self, other):
        return not other < self

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def parse(self, s):
        dt = dateutil.parser.parse(s).astimezone(DateHeader.TZ_UTC)
        ts = dt - datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=DateHeader.TZ_UTC)
        return int(ts.total_seconds())

#
# RangeHeader 
#

class RangeHeader(object):
    __slots__ = ["unit", "start", "stop"]

    def __init__(self, s):
        self.unit, self.start, self.stop = self.parse(s)

    def __repr__(self):
        return "{0}({1!r}, {2!r}, {3!r})".format(type(self).__name__, self.unit, self.start, self.stop)

    def parse(self, s):
        unit, ranges = s.split("=", 1)
        if len(ranges.split(",")) > 1:
            raise exc.HTTPNotImplemented(detail="Multiple ranges are not implemented")
        start, stop = ranges.split("-", 1)
        try:
            start = int(start)
        except:
            start = None
        try:
            stop = int(stop)
        except:
            stop = None
        return unit, start, stop
