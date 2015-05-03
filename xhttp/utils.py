import gzip
import hashlib
import os
import sys

from .headers import DateHeader
from . import exc

if sys.version_info[0] == 2:
    import httplib as status
elif sys.version_info[0] == 3:
    import http.client as status

if sys.version_info[0] == 2:
    import StringIO as io
    io.BytesIO = io.StringIO
elif sys.version_info[0] == 3:
    import io

__all__ = [
    'decorator',
    'serve_file',
    'gzip_encode',
    'gzip_decode'
]

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
# serve_file
#

def serve_file(filename, content_type, last_modified=True, etag=False):
    try:
        with open(filename, "rb") as f:
            content = f.read()
    except IOError as e:
        raise exc.HTTPNotFound(detail=e.strerror)
    result = {
        "x-status": status.OK,
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
# gzip_encode/gzip_decode
#

def gzip_encode(s):
    z = io.BytesIO() 
    with gzip.GzipFile(fileobj=z, mode="wb") as f:
        f.write(s)
    z.seek(0)
    return z.read()

def gzip_decode(z):
    return gzip.GzipFile(fileobj=io.BytesIO(z), mode="rb").read()
