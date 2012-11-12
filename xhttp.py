#!/usr/bin/env python

import httplib
import re
import urllib

import httplib as status

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

    #def __call__(self, *a, **k):
    #    return self.func(*a, **k)

#
# http_qlist 
# 

class http_qlist(list):
    def __init__(self, s):
        try: 
            # XXX evil & has bugs & loses round trip 
            items = re.split(r"\s*,\s*", s.lower())
            items = [ re.split(r"\s*;\s*", item) for item in items ]
            items = [ t if len(t) == 2 else (t + ["q=1.0"]) for t in items ]
            items = [ (m, q.split('=')[1]) for (m, q) in items ] 
            items = [ (float(q), i, m) for (i, (m, q)) in enumerate(items) ]
            items = sorted(items, key=lambda (q, i, v): (1-q, i, v))
            super(http_qlist, self).__init__(v  for (_, _, v) in items)
        except:
            super(http_qlist, self).__init__([])

    def negotiate(self, keys):
        for v in self:
            if v in keys:
                return v

    def negotiate_mime(self, keys):
        for v in self:
            if (v == "*/*") and keys:
                return keys[0]
            for k in keys:
                if k == v:
                    return k
            for k in keys:
                s = k.split("/")[0] + "/*"
                if s == v:
                    return k

#
# @wsgi_app
#

class wsgi_app(decorator):
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
        "accept"          : http_qlist,
        "accept-charset"  : http_qlist,
        "accept-encoding" : http_qlist,
        "accept-language" : http_qlist
    }

    ENVIRONMENT = {
        "x-document-root" : lambda env: env["DOCUMENT_ROOT"],
        "x-request-uri"   : lambda env: env["REQUEST_URI"],
        "x-method"        : lambda env: env["REQUEST_METHOD"],
        "x-path"          : lambda env: env["PATH_INFO"],
        "x-query"         : lambda env: env["QUERY_STRING"],
        "x-env"           : lambda env: env
    }
        
#
# class WSGIAdapter
#

class WSGIAdapter(object):
    @wsgi_app
    def __call__(self, *a, **k):
        return super(WSGIAdapter, self)(req, *a, **k)

#
# metaclass as_wsgi_app 
#

class as_wsgi_app(type):
    def __new__(cls, name, bases, attrs):
        C = super(as_wsgi_app, cls).__new__(cls, name, bases, attrs)
        C.__call__ = lambda self, *a, **k: super(C, self).__call__(*a, **k)
        C.__call__ = wsgi_app(C.__call__)
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
            return {
                "x-status"     : httplib.METHOD_NOT_ALLOWED,
                "x-content"    : "Method Not Allowed\n\n{0} {1} {2}".format(self.__class__.__name__, req["x-method"], req["x-request-uri"]),
                "content-type" : "text/plain" }

    def OPTIONS(self, req, *a, **k):
        allowed = " ".join(m for m in self.__METHODS if hasattr(self, m))
        return {
            "x-status"     : httplib.OK,
            "x-content"    : allowed + "\n",
            "allowed"      : allowed,
            "content-type" : "text/plain" }

    def __call__(self, req, *a, **k):
        if not req["x-method"] in Resource.METHODS:
            return { "x-status": httplib.BAD_REQUEST }
        if hasattr(self, req["x-method"]):
            return getattr(self, req["x-method"])(req, *a, **k)
        else:
            return {
                "x-status"     : httplib.METHOD_NOT_ALLOWED,
                "x-content"    : "Method Not Allowed\n\n{0}({1} {2})".format(self.__class__.__name__, req["method"], req["request-uri"]),
                "content-type" : "text/plain" }

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
                return (handler, [ urllib.unquote(arg) for arg in match.groups() ])
        return (None, None)


    def __call__(self, request, *a, **k):
        path = request["x-path"]
        handler, args = self.find(path)
        if handler:
            return handler(request, *(a + tuple(args)))
        elif not path.endswith("/"):
            handler, args = self.find(path + "/")
            if handler:
                if request["x-method"] in ["GET", "HEAD"]:
                    location = path + "/"
                    location += ("?" + request["x-query"]) if request["x-query"] else ""
                    return {
                        "x-status"     : httplib.SEE_OTHER,
                        "x-content"    : "See other: {0}".format(location),
                        "content-type" : "text/plain",
                        "location"     : location,
                    }
                elif request.method in ["POST", "PUT", "DELETE"]:
                    return handler(request, *(a + args))
        return {
            "x-status"      : httplib.NOT_FOUND,  
            "x-content"     : "Not found: {0} {1}".format(request["x-method"], request["x-request-uri"]),
            "content-type"  : "text/plain"
        }

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
                return res
            else:
                return { "x-status": httplib.NOT_ACCEPTABLE }
    return negotiate

import core
negotiate = custom_negotiate({ 
    "application/xml"       : lambda content: core.xml.serialize_ws(content).encode("utf8"),
    "application/xhtml+xml" : lambda content: core.xml.serialize_ws(content).encode("utf8"),
    "text/html"             : lambda content: core.xml.serialize_ws(content).encode("utf8"),
    "application/json"      : lambda content: json.dumps(obj=content, sort_keys=1, indent=4)
})

#
# @get
#

def get(**variables):
    class get(decorator):
        pass
    return get

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

