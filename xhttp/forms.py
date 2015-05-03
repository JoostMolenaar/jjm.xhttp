import itertools
import re
import sys

from . import exc
from .utils import decorator

if sys.version_info[0] == 2:
    from urllib import unquote, unquote_plus
elif sys.version_info[0] == 3:
    from urllib.parse import unquote, unquote_plus

__all__ = [ 'get', 'post', 'cookie' ]

#
# @get / @post / @cookie
#

def _parse_x_www_form_urlencoded(parsertype, variables, sep="&"):
    for (key, pattern) in list(variables.items()):
        cardinality = "1"
        if key[-1] in ["?", "+", "*"]:
            del variables[key]
            key, cardinality = key[:-1], key[-1]
        #variables[key] = (cardinality, pattern)
        variables[key] = (cardinality, re.compile(pattern))

    def parse(s):
        items = [ item.split("=", 2) for item in s.split(sep) ] if s else []
        result = { key: list(v[-1] for v in val) for (key, val) in itertools.groupby(items, key=lambda item: item[0]) }

        # make sure all keys exist in result
        for (key, _) in variables.items():
            if key not in result:
                result[key] = []

        # check all keys have an acceptable number of values
        for (key, (cardinality, _)) in variables.items():
            if cardinality == "1" and len(result[key]) != 1:
                raise exc.HTTPBadRequest(detail="{0} parameter {1!r} should occur exactly once".format(parsertype, key))
            elif cardinality == "?" and len(result[key]) > 1:
                raise exc.HTTPBadRequest(detail="{0} parameter {1!r} should occur at most once".format(parsertype, key))
            elif cardinality == "+" and len(result[key]) < 1:
                raise exc.HTTPBadRequest(detail="{0} parameter {1!r} should occur at least once".format(parsertype, key))

        # check that all keys are known
        for (key, values) in result.items():
            if key not in variables:
                raise exc.HTTPBadRequest(detail="Unknown {0} parameter {1!r}".format(parsertype, key))

        # urldecode values
        for (key, values) in result.items():
            if sys.version_info[0] == 3:
                result[key] = [ unquote_plus(value) for value in values ]
            elif sys.version_info[0] == 2:
                result[key] = [ unquote_plus(value).decode("utf8", errors="replace") for value in values ]

        # check that all values comply with regex pattern
        for (key, (_, pattern)) in variables.items():
            for value in result[key]:
                if not pattern.match(value):
                    raise exc.HTTPBadRequest(detail="{0} parameter {1!r} has bad value {2!r}".format(parsertype, key, value))

        # if cardinality is 1 or ?, store single value instead of list of values
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
