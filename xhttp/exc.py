import sys

if sys.version_info[0] == 2:
    import httplib as status
elif sys.version_info[0] == 3:
    import http.client as status

if sys.version_info[0] == 2:
    bytes, str = str, unicode

__all__ = [
    'HTTPException',
    'HTTPMovedPermanently',
    'HTTPFound',
    'HTTPSeeOther',
    'HTTPNotModified',
    'HTTPBadRequest',
    'HTTPUnauthorized',
    'HTTPForbidden',
    'HTTPNotFound',
    'HTTPMethodNotAllowed',
    'HTTPNotAcceptable',
    'HTTPInternalServerError',
    'HTTPNotImplemented'
]

class HTTPException(Exception):
    EMPTY = [ status.NOT_MODIFIED ]

    def __init__(self, response_code, headers={}):
        self.status = response_code
        self.headers = headers
        super(HTTPException, self).__init__(status.responses[response_code])

    def response(self):
        detail = self.headers.pop("x-detail") if "x-detail" in self.headers else None
        if self.status in HTTPException.EMPTY:
            res = { "x-status": self.status }
            res.update(self.headers)
            return res
        else:
            message = self.args[0]
            if detail:
                message += ": " + detail 
            message += "\n"
            result = {
                "x-status": self.status,
                "x-content": message,
                "content-type": "text/plain"
            }
            result.update(self.headers)
            return result

class HTTPMovedPermanently(HTTPException):
    def __init__(self, location, detail=None):
        super(HTTPMovedPermanently, self).__init__(status.MOVED_PERMANENTLY,
            { "x-detail": detail, "location": location })

class HTTPFound(HTTPException):
    def __init__(self, location, detail=None):
        super(HTTPFound, self).__init__(status.FOUND, 
            { "x-detail": detail or location, "location": location })

class HTTPSeeOther(HTTPException):
    def __init__(self, location, detail=None):
        super(HTTPSeeOther, self).__init__(status.SEE_OTHER, 
            { "x-detail": detail or location, "location": location })

class HTTPNotModified(HTTPException):
    def __init__(self, detail=None):
        super(HTTPNotModified, self).__init__(status.NOT_MODIFIED, { "x-detail": detail })

class HTTPBadRequest(HTTPException):
    def __init__(self, detail=None):
        super(HTTPBadRequest, self).__init__(status.BAD_REQUEST, { "x-detail": detail })

class HTTPUnauthorized(HTTPException):
    def __init__(self, detail=None):
        super(HTTPUnauthorized, self).__init__(status.UNAUTHORIZED, { "x-detail": detail })

class HTTPForbidden(HTTPException):
    def __init__(self, detail=None):
        super(HTTPForbidden, self).__init__(status.FORBIDDEN, { "x-detail": detail })

class HTTPNotFound(HTTPException):
    def __init__(self, detail=None):
        super(HTTPNotFound, self).__init__(status.NOT_FOUND, { "x-detail": detail })

class HTTPMethodNotAllowed(HTTPException):
    def __init__(self, allowed, detail=None):
        super(HTTPMethodNotAllowed, self).__init__(status.METHOD_NOT_ALLOWED, 
            { "x-detail": detail or allowed, "allowed": allowed})
    
class HTTPNotAcceptable(HTTPException):
    def __init__(self, detail=None):
        super(HTTPNotAcceptable, self).__init__(status.NOT_ACCEPTABLE, { "x-detail": detail })

class HTTPInternalServerError(HTTPException):
    def __init__(self, detail=None):
        super(HTTPInternalServerError, self).__init__(status.INTERNAL_SERVER_ERROR, 
            { "x-detail": detail })        

class HTTPNotImplemented(HTTPException):
    def __init__(self, detail=None):
        super(HTTPNotImplemented, self).__init__(status.NOT_IMPLEMENTED, { "x-detail": detail })

