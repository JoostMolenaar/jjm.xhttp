import json
import sys

import xmlist

from . import exc
from .headers import *
from .utils import decorator, gzip_encode

if sys.version_info[0] == 2:
    bytes, str = str, unicode

__all__ = [ 'custom_accept', 'accept', 'accept_encoding', 'accept_charset' ]

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
                raise exc.HTTPNotAcceptable()
    return accept 

accept = custom_accept({ 
    "application/xml"       : lambda content: xmlist.serialize(content),
    "application/xhtml+xml" : lambda content: xmlist.serialize(content),
    "text/html"             : lambda content: xmlist.serialize(content),
    "application/json"      : lambda content: json.dumps(obj=content, sort_keys=1, ensure_ascii=False, indent=4),
})

#
# @accept_encoding
# 

class accept_encoding(decorator):
    def __call__(self, req, *a, **k):
        res = self.func(req, *a, **k)
        if "accept-encoding" not in req:
            return res
        if req["accept-encoding"].negotiate(["gzip"]):
            content = gzip_encode(res["x-content"])
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
        if isinstance(res["x-content"], str):
            charsets = req.get("accept-charset", None) or QListHeader("UTF-8")
            charset = charsets.negotiate(["UTF-8", "UTF-16", "UTF-32", "US-ASCII"])
            if charset:
                res["x-content"] = res["x-content"].encode(charset)
                res["content-type"] += "; charset={0}".format(charset)
            else:
                raise exc.HTTPNotAcceptable(detail="No supported charset requested")
        return res

