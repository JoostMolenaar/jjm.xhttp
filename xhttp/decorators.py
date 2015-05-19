import traceback

from . import exc
from .utils import decorator

__all__ = ['catcher', 'session', 'cache_control', 'vary', 'app_cached']

#
# @catcher
#

class catcher(decorator):
    def __call__(self, req, *a, **k):
        try:
            try:
                return self.func(req, *a, **k)
            except Exception as e:
                if isinstance(e, exc.HTTPException):
                    raise
                print("")
                traceback.print_exc()
                detail = "{0} ({1})".format(type(e).__name__, e.args[0])
                raise exc.HTTPInternalServerError(detail=detail)
        except exc.HTTPException as e:
            return e.response()

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
# @cache_control
#

def cache_control(*directives):
    class cache_control(decorator):
        def __call__(self, req, *a, **k):
            try:
                res = self.func(req, *a, **k)
                res.update({ "cache-control": ", ".join(directives) })
                return res
            except exc.HTTPException as e:
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
            except exc.HTTPException as e:
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

