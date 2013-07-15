#!/usr/bin/env python

import datetime
import gzip
import hashlib
import httplib
import itertools
import json
import os
import os.path
import re
import StringIO
import traceback
import urllib

import httplib as status

import dateutil
import dateutil.parser

import xmlist

# XXX: for negotiating accept-charset, everything should be unicode objects. or else assume us-ascii
# XXX: be more flexible about x-content having to be iterable? if it's str/basestring/unicode, put it inside a list?

#
# @decorator 
#

class decorator(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls=None):
        # XXX: don't know how to hit this branch in a sane way
        if cls is None:
            return self
        new_func = self.func.__get__(obj, cls)
        return self.__class__(new_func)

#
# QListHeader
# 

class QListHeader(object):
    def __init__(self, s):
        try: 
            items = re.split(r"\s*,\s*", s)
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
        for (_, _, v) in self.items:
            if any(v.lower() == k.lower() for k in keys):
                return v
        return None

    def negotiate_language(self, tags):
        pass

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

    def __cmp__(self, other):
        return cmp(self.timestamp, other.timestamp)

    def parse(self, s):
        dt = dateutil.parser.parse(s).astimezone(DateHeader.TZ_UTC)
        ts = dt - datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=DateHeader.TZ_UTC)
        return int(ts.total_seconds())

#
# RangeHeader 
#

class RangeHeader(object):
    def __init__(self, s):
        self.unit, self.start, self.stop = self.parse(s)

    def __repr__(self):
        return "{0}({1}, {2}, {3})".format(type(self).__name__, self.unit, self.start, self.stop)

    def parse(self, s):
        unit, ranges = s.split("=", 1)
        if len(ranges.split(",")) > 1:
            raise HTTPException(httplib.NOT_IMPLEMENTED, { "x-detail": "Multiple ranges not implemented" })
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

        request.update({ name: parse(request[name])
                         for (name, parse) in self.PARSERS.items()
                         if name in request })

        response = self.func(request)

        status = response.pop("x-status")
        status = str(status) + " " + httplib.responses[status]

        content = response.pop("x-content", "")
        if isinstance(content, str):
            response["content-length"] = len(content)
            content = [content]

        headers = [ (key.title(), str(response[key]))
                    for key in sorted(response.keys()) ]

        start_response(status, headers)
        return content

    PARSERS = {
        "accept"            : QListHeader,
        "accept-charset"    : QListHeader,
        "accept-encoding"   : QListHeader,
        "accept-language"   : QListHeader,
        "if-modified-since" : DateHeader,
        "range"             : RangeHeader
    }

    ENVIRONMENT = {
        "content-length"   : lambda env: env.get("CONTENT_LENGTH", None),
        "content-type"     : lambda env: env.get("CONTENT_TYPE", None),
        "x-document-root"  : lambda env: env.get("DOCUMENT_ROOT", None),
        "x-path-info"      : lambda env: env.get("PATH_INFO", None),
        "x-query-string"   : lambda env: env.get("QUERY_STRING", None),
        "x-remote-addr"    : lambda env: env.get("REMOTE_ADDR", None),
        "x-remote-port"    : lambda env: env.get("REMOTE_PORT", None),
        "x-request-uri"    : lambda env: env.get("REQUEST_URI", None),
        "x-request-method" : lambda env: env.get("REQUEST_METHOD", None),
        "x-server-name"    : lambda env: env.get("SERVER_NAME", None),
        "x-server-port"    : lambda env: env.get("SERVER_PORT", None),
        "x-server-protocol": lambda env: env.get("SERVER_PROTOCOL", None),
        "x-wsgi-input"     : lambda env: env.get("wsgi.input", None)
        #x-env"            : lambda env: env
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
    EMPTY = [ httplib.NOT_MODIFIED ]

    def __init__(self, status, headers={}):
        self.status = status
        self.headers = headers
        super(HTTPException, self).__init__(httplib.responses[status])

    def response(self):
        if self.status in HTTPException.EMPTY:
            res = { "x-status": self.status }
            res.update(self.headers)
            return res
        else:
            message = self.message
            if "x-detail" in self.headers:
                message += ": "
                message += self.headers.pop("x-detail")
            message += "\n"
            result = {
                "x-status": self.status,
                "x-content": message,
                "content-type": "text/plain"
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
            res.pop("x-content", None)
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
# @accept
#

def custom_accept(serializers):
    class accept(decorator):
        def __call__(self, req, *a, **k):
            res = self.func(req, *a, **k)
            accept = req["accept"] if "accept" in req else QListHeader("*/*")
            content_view = res.pop("x-content-view")
            content_type = accept.negotiate_mime(content_view.keys())
            if content_type:
                generate_obj = content_view[content_type]
                res["x-content"] = generate_obj(res["x-content"])
                res["content-type"] = content_type
                if content_type in serializers:
                    serialize_obj = serializers[content_type]
                    res["x-content"] = serialize_obj(res["x-content"])
                return res
            else:
                raise HTTPException(httplib.NOT_ACCEPTABLE)
    return accept 

accept = custom_accept({ 
    "application/xml"       : lambda content: xmlist.serialize(content),
    "application/xhtml+xml" : lambda content: xmlist.serialize(content),
    "text/html"             : lambda content: xmlist.serialize(content),
    "application/json"      : lambda content: json.dumps(obj=content, sort_keys=1, ensure_ascii=False, indent=4),
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
                traceback.print_exc(e)
                detail = "{0} ({1})".format(type(e).__name__, e.message)
                raise HTTPException(httplib.INTERNAL_SERVER_ERROR, { "x-detail": detail })
        except HTTPException as e:
            return e.response()

#
# @get / @post / @cookie
#

def _parse_x_www_form_urlencoded(parsertype, variables, sep="&"):
    for (key, pattern) in variables.items():
        cardinality = "1"
        if key[-1] in ["?", "+", "*"]:
            del variables[key]
            key, cardinality = key[:-1], key[-1]
        variables[key] = (cardinality, pattern)

    def parse(s):
        items = [ item.split("=", 2) for item in s.split(sep) ] if s else []
        result = { key: list(v[-1] for v in val) for (key, val) in itertools.groupby(items, key=lambda item: item[0]) }

        for (key, _) in variables.items():
            if key not in result:
                result[key] = []

        for (key, (cardinality, _)) in variables.items():
            if cardinality == "1" and len(result[key]) != 1:
                raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "{0} parameter {1!r} should occur exactly once".format(parsertype, key) })
            elif cardinality == "?" and len(result[key]) > 1:
                raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "{0} parameter {1!r} should occur at most once".format(parsertype, key) })
            elif cardinality == "+" and len(result[key]) < 1:
                raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "{0} parameter {1!r} should occur at least once".format(parsertype, key) })

        for (key, (_, pattern)) in variables.items():
            for value in result[key]:
                if not re.match(pattern, value):
                    raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "{0} parameter {1!r} has bad value {2!r}".format(parsertype, key, value) })

        for (key, values) in result.items():
            if key not in variables:
                raise HTTPException(httplib.BAD_REQUEST, { "x-detail": "Unknown {0} parameter {1!r}".format(parsertype, key) })

        for (key, values) in result.items():
            result[key] = [ urllib.unquote_plus(value).decode("utf8", errors="replace") for value in values ]

        for (key, (cardinality, _)) in variables.items():
            if cardinality in ["1", "?"]:
                result[key] = result[key][0] if result[key] else None

        return result

    return parse

def get(variables):
    parser = _parse_x_www_form_urlencoded("GET", variables, sep="&")
    class get_dec(decorator):
        def __call__(self, req, *a, **k):
            req["x-get"] = parser(req["x-query-string"])
            return self.func(req, *a, **k)
    return get_dec

def post(variables):
    parser = _parse_x_www_form_urlencoded("POST", variables, sep="&")
    class post_dec(decorator):
        def __call__(self, req, *a, **k):
            try:
                content_length = int(req["content-length"])
            except:
                content_length = 0
            wsgi_input = req["x-wsgi-input"].read(content_length)
            req["x-post"] = parser(wsgi_input)
            return self.func(req, *a, **k)
    return post_dec
    
def cookie(variables):
    parser = _parse_x_www_form_urlencoded("Cookie", variables, sep="; ")
    class cookie_dec(decorator):
        def __call__(self, req, *a, **k):
            req["x-cookie"] = parser(req.get("cookie", ""))
            return self.func(req, *a, **k)
    return cookie_dec

#
# @session
#

def session(cookie_key, sessions):
    class session(decorator):
        def __call__(self, request, *a, **k):
            if 'x-cookie' in request and cookie_key in request['x-cookie']:
                session_id = request['x-cookie'][cookie_key]
                if session_id in sessions:
                    request['x-session'] = sessions[session_id]
                    return self.func(request, *a, **k)
            request['x-session'] = None
            return self.func(request, *a, **k)
    return session

#
# @if_modified_since
#

class if_modified_since(decorator):
    def __call__(self, req, *a, **k):
        res = self.func(req, *a, **k)
        if "if-modified-since" not in req:
            return res
        if "last-modified" not in res:
            return res
        if req["if-modified-since"] < res["last-modified"]:
            return res
        if res["x-status"] != httplib.OK:
            return res
        raise HTTPException(httplib.NOT_MODIFIED)

#
# @if_none_match
#

class if_none_match(decorator):
    def __call__(self, req, *a, **k):
        res = self.func(req, *a, **k)
        if "if-none-match" not in req:
            return res
        if "etag" not in res:
            return res
        if req["if-none-match"] != res["etag"]:
            return res
        if res["x-status"] != httplib.OK:
            return res
        raise HTTPException(httplib.NOT_MODIFIED)

#
# @accept_encoding
# 

def _gzip_encode(s):
    z = StringIO.StringIO()
    with gzip.GzipFile(fileobj=z, mode="wb") as f:
        f.write(s)
    z.seek(0)
    return z.buf

def _gzip_decode(z):
    return gzip.GzipFile(fileobj=StringIO.StringIO(z), mode="rb").read()

class accept_encoding(decorator):
    def __call__(self, req, *a, **k):
        res = self.func(req, *a, **k)
        if "accept-encoding" not in req:
            return res
        if req["accept-encoding"].negotiate(["gzip"]):
            content = _gzip_encode(res["x-content"])
            res.update({
                "x-content": content,
                "content-encoding": "gzip",
                "content-length": len(content)
            })
        return res

#
# @accept_charset 
#

class accept_charset(decorator):
    def __call__(self, req, *a, **k):
        res = self.func(req, *a, **k)
        if "x-content" not in res:
            return res
        if isinstance(res["x-content"], unicode):
            charsets = req.get("accept-charset", None) or QListHeader("UTF-8")
            charset = charsets.negotiate(["UTF-8", "UTF-16", "US-ASCII"])
            if charset:
                res["x-content"] = res["x-content"].encode(charset)
                res["content-type"] += "; charset={0}".format(charset)
            else:
                raise HTTPException(httplib.NOT_ACCEPTABLE, { "x-detail": "No supported charset requested" })
        return res

#
# @ranged
#

class ranged(decorator):
    def __call__(self, req, *a, **k):
        res = self.func(req, *a, **k)
        res.update({ "accept-ranges": "bytes" })
        if "range" not in req:
            return res
        if "x-content" not in res:
            return res
        length = len(res["x-content"])
        start = req["range"].start
        stop = req["range"].stop if req["range"].stop is not None else (length - 1)
        res.update({
            "x-status": httplib.PARTIAL_CONTENT,
            "x-content": res["x-content"][start:stop+1],
            "content-range": "bytes {0}-{1}/{2}".format(start, stop, length)
        })
        return res

#
# @cache_control
#

def cache_control(*directives):
    class cache_control(decorator):
        def __call__(self, req, *a, **k):
            try:
                res = self.func(req, *a, **k)
                res.update({ "cache-control": ", ".join(directives) })
                return res
            except HTTPException as e:
                e.headers.update({ "cache-control": ", ".join(directives) })
                raise
    return cache_control

#
# @vary
#

def vary(*headers):
    class vary(decorator):
        def __call__(self, req, *a, **k):
            try:
                res = self.func(req, *a, **k)
                res.update({ "vary": ", ".join(headers) })
                return res
            except HTTPException as e:
                e.headers.update({ "vary": ", ".join(headers) })
                raise
    return vary

#
# @app_cached
#

def app_cached(size):
    def cache_closure(cache, cache_keys): 
        class app_cached(decorator):
            def __call__(self, req, *a, **k):
                hit = a in cache
                if not hit:
                    cache[a] = self.func(req, *a, **k)
                    cache_keys.append(a)
                    if len(cache_keys) > size:
                        del cache[cache_keys.pop(0)]
                response = cache[a].copy()
                response.update({ "x-cache": "HIT" if hit else "MISS" })
                return response
        return app_cached
    return cache_closure(dict(), list())

#
# serve_file
#

def serve_file(filename, content_type, last_modified=True, etag=False):
    try:
        with open(filename, "rb") as f:
            content = f.read()
    except IOError as e:
        raise HTTPException(httplib.NOT_FOUND, { "x-detail": e.strerror })
    result = {
        "x-status": httplib.OK,
        "x-content": content,
        "content-type": content_type,
        "content-length": len(content)
    }
    if last_modified:
        result["last-modified"] = DateHeader(os.path.getmtime(filename))
    if etag:
        result["etag"] = hashlib.sha256(content).hexdigest()
    return result

#
# FileServer
#

class FileServer(Resource):
    def __init__(self, path, content_type, last_modified=True, etag=False):
        self.path = path
        self.content_type = content_type
        self.last_modified = last_modified
        self.etag = etag
        
    def GET(self, req, filename):
        fullname = os.path.join(self.path, filename)
        if not os.path.abspath(fullname).startswith(os.path.abspath(self.path) + os.sep):
            raise HTTPException(httplib.FORBIDDEN)
        return serve_file(fullname, self.content_type, self.last_modified, self.etag)

#
# Redirector
#

class Redirector(Resource):
    def __init__(self, location):
        self.location = location

    def GET(self, req):
        raise HTTPException(httplib.SEE_OTHER, { "location": self.location })

#
# run_server
#

def run_server(app, ip='', port=8000):
    def fix_wsgiref(app):
        def fixed_app(environ, start_response):
            # add REQUEST_URI
            if 'REQUEST_URI' not in environ:
                environ['REQUEST_URI'] = environ['PATH_INFO']
                if environ['QUERY_STRING']:
                    environ['REQUEST_URI'] += '?'
                    environ['REQUEST_URI'] += environ['QUERY_STRING']
            # add DOCUMENT_ROOT
            import os
            environ['DOCUMENT_ROOT'] = os.getcwd()
            # do it
            return app(environ, start_response)
        return fixed_app

    app = fix_wsgiref(app)
    print 'Serving on {0}:{1}'.format(ip, port)
    import wsgiref.simple_server
    wsgiref.simple_server.make_server(ip, port, app).serve_forever()

