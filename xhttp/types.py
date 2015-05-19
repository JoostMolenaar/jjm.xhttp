import os
import re
import sys

from . import exc
from . import utils
from . import conditional

if sys.version_info[0] == 2:
    from urllib import unquote
elif sys.version_info[0] == 3:
    from urllib.parse import unquote

if sys.version_info[0] == 2:
    import httplib as status
elif sys.version_info[0] == 3:
    import http.client as status

__all__ = [ 'Resource', 'Router', 'FileServer', 'Redirector' ]

#
# class Resource
#

class Resource(object):
    @property
    def allowed(self):
        methods = { m for m in self.METHODS if hasattr(self, m) }
        if not "GET" in methods:
            methods.discard("HEAD")
        return " ".join(sorted(methods))

    def HEAD(self, req, *a, **k):
        if hasattr(self, "GET"):
            res = self.GET(req, *a, **k)
            res.pop("x-content", None)
            return res
        else:
            raise exc.HTTPMethodNotAllowed(self.allowed, detail="GET")

    def OPTIONS(self, req, *a, **k):
        raise exc.HTTPException(status.OK, { "allowed": self.allowed, "x-detail": self.allowed })

    def __call__(self, req, *a, **k):
        if not req["x-request-method"] in Resource.METHODS:
            raise exc.HTTPBadRequest(detail=req["x-request-method"])
        if hasattr(self, req["x-request-method"]):
            return getattr(self, req["x-request-method"])(req, *a, **k)
        raise exc.HTTPMethodNotAllowed(self.allowed, detail=req["x-request-method"])

    # XXX not very pluggable ------- i could just stick it into request?
    METHODS = "HEAD GET PUT POST DELETE OPTIONS".split()

#
# class Router
#

class Router(object):
    def __init__(self, *dispatch, **kwargs):
        self.dispatch = [ (re.compile(pattern), handler) 
                          for (pattern, handler) in dispatch ]
        self.prefix = kwargs.get('prefix', '/')
        self.prefix_re = re.compile('^' + self.prefix + '/*')

    def find(self, path):
        for (pattern, handler) in self.dispatch:
            match = pattern.match(path)
            if match:
                return (handler, tuple(unquote(arg) for arg in match.groups()))
        return (None, None)

    def __call__(self, request, *a, **k):
        path = self.prefix_re.sub('/', request["x-path-info"])
        handler, args = self.find(path)
        if handler:
            return handler(request, *(a + args))
        elif not path.endswith("/"):
            handler, args = self.find(path + "/")
            if handler:
                if request["x-request-method"] in ["GET", "HEAD"]:
                    location = path + "/"
                    location += ("?" + request["x-query-string"]) if request["x-query-string"] else ""
                    raise exc.HTTPSeeOther(location)
                else:
                    return handler(request, *(a + args))
        raise exc.HTTPNotFound(detail=request["x-request-uri"])

#
# FileServer
#

class FileServer(Resource):
    def __init__(self, path, content_type, last_modified=True, etag=False):
        self.path = path
        self.content_type = content_type
        self.last_modified = last_modified
        self.etag = etag
  
    @conditional.if_modified_since
    @conditional.if_none_match
    @conditional.ranged
    def GET(self, req, filename):
        fullname = os.path.join(self.path, filename)
        if not os.path.abspath(fullname).startswith(os.path.abspath(self.path) + os.sep):
            raise exc.HTTPForbidden()
        return utils.serve_file(fullname, self.content_type, self.last_modified, self.etag)

#
# Redirector
#

class Redirector(Resource):
    def __init__(self, location):
        self.location = location

    def GET(self, req):
        raise exc.HTTPSeeOther(self.location)
