from __future__ import division, absolute_import, print_function
#rom __future__ import unicode_literals

import collections
import sys

if sys.version_info[0] == 2:
    import httplib as status
elif sys.version_info[0] == 3:
    import http.client as status

if sys.version_info[0] == 2:
    bytes, str = str, unicode

from .headers import *
from .exc import *
from .utils import *
from .types import *
from .utils import *
from .forms import *
from .negotiation import *
from .conditional import *
from .decorators import *

__author__ = 'Joost Molenaar <j.j.molenaar@gmail.com>'


# XXX: for negotiating accept-charset, everything should be unicode objects. or else assume us-ascii
# XXX: be more flexible about x-content having to be iterable? if it's str/basestring/unicode, put it inside a list?

#
# @xhttp_app
#

class xhttp_app(decorator):
    def parse_request(self, environment):
        request = { name[5:].lower().replace('_', '-'): value 
                    for (name, value) in environment.items() 
                    if name.startswith("HTTP_") }

        request.update({ target: get(environment)
                         for (target, get) in self.ENVIRONMENT.items() })

        request.update({ name: parse(request[name])
                         for (name, parse) in self.PARSERS.items()
                         if name in request })

        return request

    def create_content(self, response):
        content = response.pop("x-content", b"")
        if callable(content):
            content = content()
        if isinstance(content, str):
            raise Exception("Need to use @accept_charset to send Unicode to client")
        if isinstance(content, bytes):
            response["content-length"] = len(content)
            content = [content]
        return content

    def __call__(self, environment, start_response):
        request = self.parse_request(environment)

        response = self.func(request)

        response_code = response.pop("x-status")
        response_code = "{0} {1}".format(response_code, status.responses[response_code])

        content = self.create_content(response)

        header_type = str if sys.version_info[0] == 3 else bytes
        headers = [ (key.title(), header_type(response[key]))
                    for key in sorted(response.keys()) ]

        start_response(response_code, headers)
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
            attrs.update({ k: v for (k, v) in C.__dict__.items() if isinstance(v, collections.Callable) })
            new_class = super(extended_with, cls).__new__(cls, name, bases, attrs)
            return new_class
    return extended_with


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
    print('Serving on {0}:{1}'.format(ip, port))
    import wsgiref.simple_server
    wsgiref.simple_server.make_server(ip, port, app).serve_forever()

