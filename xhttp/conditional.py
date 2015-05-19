import sys

from . import exc
from .utils import decorator

if sys.version_info[0] == 2:
    import httplib as status
elif sys.version_info[0] == 3:
    import http.client as status

__all__ = ['if_modified_since', 'if_none_match', 'ranged']

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
        if res["x-status"] != status.OK:
            return res
        raise exc.HTTPNotModified()

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
        if res["x-status"] != status.OK:
            return res
        raise exc.HTTPNotModified()

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
        content = res["x-content"]
        if callable(content):
            content = content()
        length = len(content)
        start = req["range"].start
        stop = req["range"].stop if req["range"].stop is not None else (length - 1)
        content = content[start:stop+1]
        res.update({
            "x-status": status.PARTIAL_CONTENT,
            "x-content": content,
            "content-range": "bytes {0}-{1}/{2}".format(start, stop, length)
        })
        return res

