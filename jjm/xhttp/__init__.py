#!/usr/bin/env python

import httplib
import re
import urllib
import json
import datetime
import itertools

import httplib as status

import dateutil
import dateutil.parser

from .. import xml as xml

# TODO : extract core.xml
# TODO : extract core.run_server

#
# @decorator 
#

class decorator(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls=None):
        if cls is None:
            return self
        new_func = self.func.__get__(obj, cls)
        return self.__class__(new_func)

#
# qlist
# 

class qlist(object):
    def __init__(self, s):
        try: 
            items = re.split(r"\s*,\s*", s.lower())
            items = [ re.split(r"\s*;\s*", item) for item in items ]
            items = [ t if len(t) == 2 else (t + ["q=1.0"]) for t in items ]
            items = [ (m, q.split('=')[1]) for (m, q) in items ] 
            items = [ (float(q), i, m) for (i, (m, q)) in enumerate(items) ]
            self.items = sorted(items, key=lambda (q, i, v): (1-q, i, v))
        except:
            self.items = []

    def __str__(self):
        return ",".join((v + (";q={0}".format(q) if q != 1.0 else ""))
                        for (q, i, v) in sorted(self.items, key=lambda (q, i, v): i))

    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, repr(str(self)))

    def negotiate(self, keys):
        for v in self:
            if v in keys:
                return v

    def negotiate_mime(self, keys):
        for (_, _, v) in self.items:
            # match anything
            if (v == "*/*") and keys:
                return keys[0]
            # match exactly
            for k in keys:
                if k == v:
                    return k
            # match partially
            for k in keys:
                s = k.split("/")[0] + "/*"
                if s == v:
                    return k
        return None

#
# date
#

class date(object):
    WEEKDAYS = 'Mon Tue Wed Thu Fri Sat Sun'.split()
    MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    TZ_UTC = dateutil.tz.tzutc()

    def __init__(self, x, tz=TZ_UTC):
        self.tz = tz 
        if isinstance(x, str):
            self.timestamp = self.parse(x)
        elif isinstance(x, int):
            self.timestamp = x
        else:
            raise ValueError("Unsupported type {0}".format(type(x).__name__))

    def __str__(self):
        dt = datetime.datetime.utcfromtimestamp(self.timestamp)
        return "{0}, {1:02} {2} {3} {4:02}:{5:02}:{6:02} GMT".format(
            date.WEEKDAYS[dt.weekday()], 
            dt.day,
            date.MONTHS[dt.month-1],
            dt.year,
            dt.hour,
            dt.minute,
            dt.second)

    def parse(self, s):
        dt = dateutil.parser.parse(s).astimezone(date.TZ_UTC)
        ts = dt - datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=date.TZ_UTC)
        return int(ts.total_seconds())

#
# @xhttp_app
#

class xhttp_app(decorator):
    def __call__(self, environment, start_response):
        request = { name[5:].lower().replace('_', '-'): value 
                    for (name, value) in environment.items() 
                    if name.startswith("HTTP_") }

        request.update({ target: get(environment)
                         for (target, get) in self.ENVIRONMENT.items() })

        request.update({ ("-" + name): request[name]
                         for name in self.PARSERS
                         if name in request })

        request.update({ name: parse(request[name])
                         for (name, parse) in self.PARSERS.items()
                         if name in request })

        response = self.func(request)

        status = response.pop("x-status")
        status = str(status) + " " + httplib.responses[status]

        content = response.pop("x-content") if "x-content" in response else [""]
        headers = [ (header.title(), str(value)) 
                    for (header, value) in response.items() ]

        start_response(status, headers)
        return content

    PARSERS = {
        "accept"            : qlist,
        "accept-charset"    : qlist,
        "accept-encoding"   : qlist,
        "accept-language"   : qlist,
        "if-modified-since" : date
    }

    ENVIRONMENT = {
        "x-document-root"  : lambda env: env["DOCUMENT_ROOT"],
        "x-request-uri"    : lambda env: env["REQUEST_URI"],
        "x-request-method" : lambda env: env["REQUEST_METHOD"],
        "x-path-info"      : lambda env: env["PATH_INFO"],
        "x-query-string"   : lambda env: env["QUERY_STRING"],
        "x-env"            : lambda env: env
    }
        
#
# class WSGIAdapter
#

class WSGIAdapter(object):
    @xhttp_app
    def __call__(self, *a, **k):
        return super(WSGIAdapter, self)(req, *a, **k)

#
# metaclass as_wsgi_app 
#

class as_wsgi_app(type):
    def __new__(cls, name, bases, attrs):
        C = super(as_wsgi_app, cls).__new__(cls, name, bases, attrs)
        C.__call__ = lambda self, *a, **k: super(C, self).__call__(*a, **k)
        C.__call__ = xhttp_app(C.__call__)
        return C

#
# metametaclass extended_with 
#

def extended_with(C):
    class extended_with(type):
        def __new__(cls, name, bases, attrs):
            attrs.update({ k: v for (k, v) in C.__dict__.items() if callable(v) })
            new_class = super(extended_with, cls).__new__(cls, name, bases, attrs)
            return new_class
    return extended_with

#
# class HTTPException
#

class HTTPException(Exception):
    def __init__(self, status, headers={}):
        self.status = status
        self.headers = headers
        super(HTTPException, self).__init__(httplib.responses[status])

    def response(self):
        message = self.message
        if "x-detail" in self.headers:
            message += ": "
            message += self.headers.pop("x-detail")
        message += "\n"
        result = {
            "x-status": self.status,
            "x-content": [message],
            "content-type": "text/plain",
            "content-length": len(message)
        }
        result.update(self.headers)
        return result
        
#
# class Resource
#

class Resource(object):
    def HEAD(self, req, *a, **k):
        if hasattr(self, "GET"):
            res = self.GET(req, *a, **k)
            if "x-content" in res:
                del res["x-content"]
            return res
        else:
            raise HTTPException(httplib.METHOD_NOT_ALLOWED, { "x-detail": "GET" })

    def OPTIONS(self, req, *a, **k):
        allowed = " ".join(sorted(m for m in self.METHODS if hasattr(self, m)))
        raise HTTPException(httplib.OK, { "allowed": allowed, "x-detail": allowed })

    def __call__(self, req, *a, **k):
        if not req["x-request-method"] in Resource.METHODS:
            raise HTTPException(httplib.BAD_REQUEST, { "x-detail": req["x-request-method"] })
        if hasattr(self, req["x-request-method"]):
            return getattr(self, req["x-request-method"])(req, *a, **k)
        else:
            raise HTTPException(httplib.METHOD_NOT_ALLOWED, { "x-detail": req["x-request-method"] })

    # XXX not very pluggable ------- i could just stick it into request?
    METHODS = "HEAD GET PUT POST DELETE OPTIONS".split()


#
# class Router
#

class Router(object):
    def __init__(self, *dispatch):
        self.dispatch = [ (re.compile(pattern), handler) 
                          for (pattern, handler) in dispatch ]

    def find(self, path):
        for (pattern, handler) in self.dispatch:
            match = pattern.match(path)
            if match:
                return (handler, tuple(urllib.unquote(arg) for arg in match.groups()))
        return (None, None)


    def __call__(self, request, *a, **k):
        path = request["x-path-info"]
        handler, args = self.find(path)
        if handler:
            return handler(request, *(a + args))
        elif not path.endswith("/"):
            handler, args = self.find(path + "/")
            if handler:
                if request["x-request-method"] in ["GET", "HEAD"]:
                    location = path + "/"
                    location += ("?" + request["x-query-string"]) if request["x-query-string"] else ""
                    raise HTTPException(httplib.SEE_OTHER, { "location": location, "x-detail": location })
                else:
                    return handler(request, *(a + args))
        raise HTTPException(httplib.NOT_FOUND, { "x-detail": request["x-request-uri"] })

#
# @negotiate
#

def custom_negotiate(serializers):
    class negotiate(decorator):
        def __call__(self, req, *a, **k):
            res = self.func(req, *a, **k)   
            content_view = res.pop("x-content-view")
            content_type = req["accept"].negotiate_mime(content_view.keys())
            if content_type:
                generate_obj = content_view[content_type]
                res["x-content"] = generate_obj(res["x-content"])
                res["content-type"] = content_type
                if content_type in serializers:
                    serialize_obj = serializers[content_type]
                    res["x-content"] = serialize_obj(res["x-content"])
                res["content-length"] = sum(len(chunk) for chunk in res["x-content"])
                return res
            else:
                raise HTTPException(httplib.NOT_ACCEPTABLE)
    return negotiate

negotiate = custom_negotiate({ 
    "application/xml"       : lambda content: [xml.serialize(content).encode("utf8")],
    "application/xhtml+xml" : lambda content: [xml.serialize(content).encode("utf8")],
    "text/html"             : lambda content: [xml.serialize(content).encode("utf8")],
    "application/json"      : lambda content: [json.dumps(obj=content, sort_keys=1)],
    "text/plain"            : lambda content: [content]
})

#
# @catcher
#

class catcher(decorator):
    def __call__(self, req, *a, **k):
        try:
            try:
                return self.func(req, *a, **k)
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                detail = type(e).__name__
                detail += "\n\n"
                detail += e.message
                raise HTTPException(httplib.INTERNAL_SERVER_ERROR, { "x-detail": detail })
        except HTTPException as e:
            return e.response()

#
# @get
#

def get(variables):
    for (key, pattern) in variables.items():
        cardinality = "1"
        if key[-1] in ["?", "+", "*"]:
            del variables[key]
            key, cardinality = key[:-1], key[-1]
        variables[key] = (cardinality, pattern)

    class get_dec(decorator):
        def __call__(self, req, *a, **k):
            items = [ item.split("=", 2) for item in req["x-query-string"].split("&") ]
            result = { key: list(v[1] for v in val) for (key, val) in itertools.groupby(items, key=lambda item: item[0]) }

            for (key, _) in variables.items():
                if key not in result:
                    result[key] = []

            for (key, (cardinality, _)) in variables.items():
                if cardinality == "1" and len(result[key]) != 1:
                    raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "Incorrect number of occurrences for GET parameter {0!r}".format(key) })
                elif cardinality == "+" and len(result[key]) == 0:
                    raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "Incorrect number of occurrences for GET parameter {0!r}".format(key) })

            for (key, (_, pattern)) in variables.items():
                for value in result[key]:
                    if not re.match(pattern, value):
                        raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "Bad value {0!r} for GET parameter {1!r}".format(value, key) })

            for (key, values) in result.items():
                if key not in variables:
                    raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "GET parameter {0!r} is not allowed".format(key) })

            for (key, values) in result.items():
                result[key] = [ urllib.unquote(value).decode('utf8') for value in values ]

            for (key, (cardinality, _)) in variables.items():
                if cardinality in ["1", "?"]:
                    result[key] = result[key][0] if result[key] else None

            req["x-get"] = result
            return self.func(req, *a, **k)
                
    return get_dec

#
# @post
#

def post(**variables):
    class post(decorator):
        pass
    return post

#
# @last_modified
#

class last_modified(decorator):
    pass

#
# @etag
#

class etag(decorator):
    pass

#
# @gzipped
#

class gzipped(decorator):
    pass

#
# @ranged
#

class ranged(decorator):
    pass

#
# @cache_control
#

def cache_control(*x):
    class cache_control(decorator):
        pass
    return cache_control

#
# @app_cached
#

def app_cached(n):
    class app_cached(decorator):
        def __call__(req, *a, **k):
            return self.func(req, *a, **k)
    return app_cached

