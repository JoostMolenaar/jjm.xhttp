from __future__ import division, absolute_import, print_function#, unicode_literals

import unittest
import os
import os.path
import sys

if sys.version_info[0] == 3:
    import io
    assert io
if sys.version_info[0] == 2:
    import StringIO as io
    assert io

import xhttp

#
# TestQlist
#

class TestQlist(unittest.TestCase):
    def test_parse(self):
        qlist = xhttp.headers.QListHeader("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        self.assertIsNotNone(qlist)
        self.assertEqual(
            [ v for (_, _, v) in qlist.items ],
            ["text/html", "application/xhtml+xml", "application/xml", "*/*"])

    def test_roundtrip(self):
        s1 = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        qlist = xhttp.headers.QListHeader(s1)
        s2 = str(qlist)
        self.assertEqual(s2, s1)

    def test_negotiate_exact_match(self):
        qlist = xhttp.headers.QListHeader("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        result = qlist.negotiate_mime(["application/xml", "image/png"])
        self.assertEqual(result, "application/xml")

    def test_negotiate_any_match(self):
        qlist = xhttp.headers.QListHeader("text/html,application/xhtml+xml,application/xml;q=0.9,text/*;q=0.85,*/*;q=0.8")
        result = qlist.negotiate_mime(["foo/bar"])
        self.assertEqual(result, "foo/bar")

    def test_negotiate_partial_match(self):
        qlist = xhttp.headers.QListHeader("application/xhtml+xml,application/xml;q=0.9,text/*;q=0.95,*/*;q=0.8")
        result = qlist.negotiate_mime(["application/xml", "text/plain"])
        self.assertEqual(result, "text/plain")

    def test_negotiate_no_match(self):
        qlist = xhttp.headers.QListHeader("text/*;q=0.95,application/xhtml+xml,application/xml;q=0.9,text/*;q=0.85")
        result = qlist.negotiate_mime(["image/png", "audio/mpeg"])
        self.assertEqual(result, None)

    def test_negotiate_bad_header(self):
        qlist = xhttp.headers.QListHeader("text/plain;q=albatross")
        result = qlist.negotiate_mime(["image/png", "audio/mpeg"])
        self.assertEqual(qlist.items, [])
        self.assertEqual(result, None)

    def test_repr(self):
        qlist = xhttp.headers.QListHeader("text/plain;q=0.9, application/xhtml+xml")
        result = repr(qlist)
        if sys.version_info[0] == 3:
            self.assertEqual(result, "QListHeader('text/plain;q=0.9,application/xhtml+xml')")
        elif sys.version_info[0] == 2:
            self.assertEqual(result, "QListHeader(u'text/plain;q=0.9,application/xhtml+xml')")

    def test_negotiiate_other(self):
        qlist = xhttp.headers.QListHeader("gzip,deflate,sdch")
        result = qlist.negotiate(["gzip"])
        self.assertEqual(result, "gzip")

    def test_negotiate_other_returning_none(self):
        qlist = xhttp.headers.QListHeader("deflate,sdch")
        result = qlist.negotiate(["gzip"])
        self.assertEqual(result, None)

#
# TestDateHeader
#

class TestDateHeader(unittest.TestCase):
    def test_epoch(self):
        date = xhttp.headers.DateHeader("Thu, 01 Jan 1970 00:00:00 GMT")
        self.assertEqual(date.timestamp, 0)
        self.assertEqual(str(date), "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_my_birthday_gmt(self):
        date = xhttp.headers.DateHeader("Tue, 08 Jun 1982 23:11:00 GMT")
        self.assertEqual(date.timestamp, 392425860)
        self.assertEqual(str(date), "Tue, 08 Jun 1982 23:11:00 GMT")

    def test_my_birthday_in_my_timezone(self):
        date = xhttp.headers.DateHeader("Wed, 09 Jun 1982 01:11:00 +0200")
        self.assertEqual(date.timestamp, 392425860)
        self.assertEqual(str(date), "Tue, 08 Jun 1982 23:11:00 GMT")

    def test_epoch_to_str(self):
        date = xhttp.headers.DateHeader(0)
        self.assertEqual(str(date), "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_my_birthday_in_gmt_to_str(self):
        date = xhttp.headers.DateHeader(392425860)
        self.assertEqual(str(date), "Tue, 08 Jun 1982 23:11:00 GMT")

    def test_wrong_input(self):
        with self.assertRaises(ValueError) as ex:
            xhttp.headers.DateHeader(None)
        self.assertEqual(type(ex.exception), ValueError)
        self.assertEqual(ex.exception.args[0], "Unsupported type NoneType")

    def test_repr(self):
        date = xhttp.headers.DateHeader("Wed, 09 Jun 1982 01:11:00 +0200")
        result = repr(date)
        if sys.version_info[0] == 3:
            self.assertEqual(result, "DateHeader('Tue, 08 Jun 1982 23:11:00 GMT')")
        elif sys.version_info[0] == 2:
            self.assertEqual(result, "DateHeader(u'Tue, 08 Jun 1982 23:11:00 GMT')")

    def test_cmp(self):
        date1 = xhttp.headers.DateHeader("Wed, 09 Jun 1982 01:11:00 +0200")
        date1b = xhttp.headers.DateHeader("Wed, 09 Jun 1982 01:11:00 +0200")
        date2 = xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
        self.assertTrue(date1 == date1b)
        self.assertTrue(date1 < date2)
        self.assertTrue(date2 > date1)
        self.assertTrue(date1 <= date1b)
        self.assertTrue(date1 <= date2)
        self.assertTrue(date1 >= date1b)
        self.assertTrue(date2 >= date1)
        self.assertTrue(date1 != date2)

#
# TestRangeHeader
#

class TestRangeHeader(unittest.TestCase):
    def test_range_1(self):
        r = xhttp.headers.RangeHeader("bytes=0-13")
        self.assertEqual(r.unit, "bytes")
        self.assertEqual(r.start, 0)
        self.assertEqual(r.stop, 13)

    def test_annoying_range(self):
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            xhttp.headers.RangeHeader("bytes=0-13,17-19")
        self.assertEqual(ex.exception.status, 501)

    def test_no_start(self):
        r = xhttp.headers.RangeHeader("bytes=-13")
        self.assertEqual(r.unit, "bytes")
        self.assertEqual(r.start, None)
        self.assertEqual(r.stop, 13)

    def test_no_stop(self):
        r = xhttp.headers.RangeHeader("bytes=0-")
        self.assertEqual(r.unit, "bytes")
        self.assertEqual(r.start, 0)
        self.assertEqual(r.stop, None)

    def test_repr(self):
        r = xhttp.headers.RangeHeader("bytes=11-13")
        self.assertEqual(repr(r), "RangeHeader('bytes', 11, 13)")

#
# TestHTTPException
#

class TestHTTPException(unittest.TestCase):
    def test_without_detail(self):
        ex = xhttp.exc.HTTPException(xhttp.status.BAD_REQUEST)
        self.assertEqual(str(ex), "Bad Request")
        self.assertEqual(ex.response(), {
            "x-status": 400,
            "x-content": "Bad Request\n",
            "content-type": "text/plain"
        })

    def test_with_detail(self):
        ex = xhttp.exc.HTTPException(xhttp.status.BAD_REQUEST, { "x-detail": "Just because" })
        self.assertEqual(str(ex), "Bad Request")
        self.assertEqual(ex.response(), {
            "x-status": 400,
            "x-content": "Bad Request: Just because\n",
            "content-type": "text/plain"
        })

#
# TestXhttpAppDecorator
#

def gen_environ(method, request_uri, headers):
    request_uri_parts = request_uri.split("?", 1)
    (path_info, query_string) = request_uri_parts if len(request_uri_parts) == 2 else (request_uri, "")
    result = {
        "REQUEST_METHOD": method,
        "REQUEST_URI": request_uri,
        "PATH_INFO": path_info,
        "QUERY_STRING": query_string,
        "DOCUMENT_ROOT": os.getcwd()
    }
    result.update({ "HTTP_" + (k.upper().replace("-", "_")): v for (k, v) in headers.items() })
    return result

class TestXhttpAppDecorator(unittest.TestCase):
    def test_str(self):
        @xhttp.xhttp_app
        def app(request):
            return {
                "x-status": xhttp.status.OK,
                "x-content": b"Hello, world!\n",
                "content-type": "text/plain"
            }
        def start_response(status, headers):
            self.assertEqual(status, "200 OK")
            self.assertEqual(headers, [
                ("Content-Length", "14"),
                ("Content-Type", "text/plain")
            ])
        environ = gen_environ("GET", "/", {})
        result = app(environ, start_response)
        self.assertEqual(result, [b"Hello, world!\n"])

    def test_unicode(self):
        @xhttp.xhttp_app
        def app(request):
            return {
                "x-status": xhttp.status.OK,
                "x-content": u"Hello, w\u00f6rld!\n",
                "content-type": "text/plain" }
        def start_response(status, headers):
            self.assertEqual(status, "200 OK")
            self.assertEqual(headers, [
                ("Content-Length", "14"),
                ("Content-Type", "text/plain")
            ])
        environ = gen_environ("GET", "/", {})
        with self.assertRaises(Exception):
            app(environ, start_response)

    def test_iterator(self):
        @xhttp.xhttp_app
        def app(request):
            return {
                "x-status": xhttp.status.OK,
                "x-content": [b"Hello,", b" ", b"world!", b"\n"],
                "content-type": "text/plain",
                "content-length": 14 }
        def start_response(status, headers):
            self.assertEqual(status, "200 OK")
            self.assertEqual(headers, [
                ("Content-Length", "14"),
                ("Content-Type", "text/plain")
            ])
        environ = gen_environ("GET", "/", {})
        result = app(environ, start_response)
        self.assertEqual(result, [b"Hello,", b" ", b"world!", b"\n"])

    def test_callable(self):
        @xhttp.xhttp_app
        def app(request):
            return {
                "x-status": xhttp.status.OK,
                "x-content": lambda: b"Hello, world!\n",
                "content-type": "text/plain" }
        def start_response(status, headers):
            self.assertEqual(status, "200 OK")
            self.assertEqual(headers, [
                ("Content-Length", "14"),
                ("Content-Type", "text/plain") ])
        environ = gen_environ("GET", "/", {})
        result = app(environ, start_response)
        self.assertEqual(result, [b"Hello, world!\n"])


#
# TestResource
#

class HelloWorld(xhttp.Resource):
    def GET(self, request):
        return {
            "x-status": xhttp.status.OK,
            "x-content": "Hello, world!\n",
            "content-type": "text/plain"
        }

    def PUT(self, request):
        return {
            "x-status": xhttp.status.NO_CONTENT
        }

class TestResource(unittest.TestCase):
    def test_get(self):
        app = HelloWorld()
        response = app({ "x-request-method": "GET" })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": "Hello, world!\n",
            "content-type": "text/plain"
        })

    def test_options(self):
        app = HelloWorld()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-request-method": "OPTIONS" })
            assert not ex
        self.assertEqual(ex.exception.response(), {
            "x-status": 200,
            "x-content": "OK: GET HEAD OPTIONS PUT\n",
            "allowed": "GET HEAD OPTIONS PUT",
            "content-type": "text/plain"
        })

    def test_head(self):
        app = HelloWorld()
        response = app({ "x-request-method": "HEAD" })
        self.assertEqual(response, {
            "x-status": 200,
            "content-type": "text/plain"
        })

    def test_head_with_no_get(self):
        app = xhttp.Resource()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-request-method": "HEAD" })
            assert not ex
        self.assertEqual(ex.exception.response(), {
            "x-status": 405,
            "x-content": "Method Not Allowed: GET\n",
            "content-type": "text/plain",
            "allowed": "OPTIONS"
        })

    def test_unknown_method(self):
        app = HelloWorld()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method": "FOO",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
            assert not ex
        self.assertEqual(ex.exception.response(), {
            "x-status": 400,
            "x-content": "Bad Request: FOO\n",
            "content-type": "text/plain"
        })

    def test_method_not_allowed(self):
        app = HelloWorld()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-request-method": "POST" })
            assert not ex
        self.assertEqual(ex.exception.response(), {
            "x-status": 405,
            "x-content": "Method Not Allowed: POST\n",
            "content-type": "text/plain",
            "allowed": "GET HEAD OPTIONS PUT"
        })

#
# TestRouter
#

class HelloWorldRouter(xhttp.Router):
    def __init__(self):
        super(HelloWorldRouter, self).__init__(
            (r'^/hello/$', HelloWorld())
        )

class TestRouter(unittest.TestCase):
    def test_not_found(self):
        app = HelloWorldRouter()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method": "GET",
                "x-request-uri": "/foo",
                "x-path-info": "/foo",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 404,
            "x-content": "Not Found: /foo\n",
            "content-type": "text/plain"
        })

    def test_not_found_2(self):
        app = HelloWorldRouter()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method": "GET",
                "x-request-uri": "/foo/",
                "x-path-info": "/foo/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 404,
            "x-content": "Not Found: /foo/\n",
            "content-type": "text/plain"
        })

    def test_found(self):
        app = HelloWorldRouter()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/hello/",
            "x-path-info": "/hello/",
            "x-query-string": "",
            "x-document-root": os.getcwd()
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": "Hello, world!\n",
            "content-type": "text/plain"
        })

    def test_redirect_get(self):
        app = HelloWorldRouter()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method": "GET",
                "x-request-uri": "/hello",
                "x-path-info": "/hello",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
            assert ex
        self.assertEqual(ex.exception.response(), {
            "x-status": 303,
            "x-content": "See Other: /hello/\n",
            "content-type": "text/plain",
            "location": "/hello/"
        })

    def test_redirect_put(self):
        app = HelloWorldRouter()
        response = app({
            "x-request-method": "PUT",
            "x-request-uri": "/hello",
            "x-path-info": "/hello",
            "x-query-string": "",
            "x-document-root": os.getcwd()
        })
        self.assertEqual(response, {
            "x-status": 204
        })

#
# TestAccept
#

class HelloContentNegotiatingWorld(xhttp.Resource):
    @xhttp.accept_charset
    @xhttp.accept
    def GET(self, req):
        greeting = {
            "message": u'Hell\u00f8, world! ">_<"'
        }
        greeting_view = {
            "text/plain"            : lambda m: m["message"] + "\n",
            "text/html"             : lambda m: ["p", m["message"]],
            "application/json"      : lambda m: m,
            "application/xhtml+xml" : lambda m: ["p", ("xmlns", "http://www.w3.org/1999/xhtml"), m["message"]],
            "application/xml"       : lambda m: ["message", m["message"]]
        }
        return {
            "x-status"       : 200,
            "x-content"      : greeting,
            "x-content-view" : greeting_view
        }

    @xhttp.accept_charset
    def PUT(self, req):
        return { "x-status": xhttp.status.NO_CONTENT }

    @xhttp.accept_charset
    def POST(self, req):
        return {
            "x-status": xhttp.status.CREATED,
            "x-content": b"Created\n",
            "content-type": "text/plain"
        }

class TestAccept(unittest.TestCase):
    def test_not_acceptable(self):
        app = HelloContentNegotiatingWorld()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method": "GET",
                "accept": xhttp.headers.QListHeader("image/png")
            })
            assert ex
        self.assertEqual(ex.exception.response(), {
            "x-status": 406,
            "x-content": "Not Acceptable\n",
            "content-type": "text/plain"
        })

    def test_unacceptable_charset(self):
        app = HelloContentNegotiatingWorld()
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method" : "GET",
                "accept"           : xhttp.headers.QListHeader("text/plain"),
                "accept-charset"   : xhttp.headers.QListHeader("ISO-8859-15")
            })
            assert ex
        self.assertEqual(ex.exception.response(), {
            "x-status"     : 406,
            "x-content"    : "Not Acceptable: No supported charset requested\n",
            "content-type" : "text/plain"
        })

    def test_no_content(self):
        app = HelloContentNegotiatingWorld()
        response = app({ "x-request-method": "PUT" })
        self.assertEqual(response, { "x-status": 204 })

    def test_bytes(self):
        app = HelloContentNegotiatingWorld()
        response = app({ "x-request-method": "POST" })
        self.assertEqual(response, {
            "x-status": 201,
            "x-content": b"Created\n",
            "content-type": "text/plain"
        })

    def test_text_plain(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "accept": xhttp.headers.QListHeader("text/plain"),
            "accept-charset": xhttp.headers.QListHeader("UTF-8,UTF-16")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": b"Hell\xc3\xb8, world! \">_<\"\n",
            "content-type": "text/plain; charset=UTF-8"
        })

    def test_text_html(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "accept": xhttp.headers.QListHeader("text/html"),
            "accept-charset": xhttp.headers.QListHeader("UTF-8,UTF-16")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": b"<p>Hell\xc3\xb8, world! &quot;&gt;_&lt;&quot;</p>",
            "content-type": "text/html; charset=UTF-8",
        })

    def test_application_json(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "accept": xhttp.headers.QListHeader("application/json"),
            "accept-charset": xhttp.headers.QListHeader("UTF-8,UTF-16")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": b"{\n    \"message\": \"Hell\xc3\xb8, world! \\\">_<\\\"\"\n}",
            "content-type": "application/json; charset=UTF-8",
        })

    def test_application_xhtml_xml(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "accept": xhttp.headers.QListHeader("application/xhtml+xml"),
            "accept-charset": xhttp.headers.QListHeader("UTF-8,UTF-16")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": b"<p xmlns=\"http://www.w3.org/1999/xhtml\">Hell\xc3\xb8, world! &quot;&gt;_&lt;&quot;</p>",
            "content-type": "application/xhtml+xml; charset=UTF-8",
        })

    def test_application_xml(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "accept": xhttp.headers.QListHeader("application/xml"),
            "accept-charset": xhttp.headers.QListHeader("UTF-8,UTF-16")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": b"<message>Hell\xc3\xb8, world! &quot;&gt;_&lt;&quot;</message>",
            "content-type": "application/xml; charset=UTF-8",
        })

#
# TestCatcher
#

class ExceptionalResource(xhttp.Resource):
    @xhttp.catcher
    def GET(self, req):
        raise Exception("foo")

    @xhttp.catcher
    def PUT(self, req):
        location = "/somewhere-else"
        raise xhttp.exc.HTTPException(xhttp.status.SEE_OTHER, { "location": location, "x-detail": location })

class TestCatcher(unittest.TestCase):
    def test_exception(self):
        app = ExceptionalResource()
        response = app({ "x-request-method": "GET" })
        self.assertEqual(response, {
            "x-status": 500,
            "x-content": "Internal Server Error: Exception (foo)\n",
            "content-type": "text/plain"
        })

    def test_http_exception(self):
        app = ExceptionalResource()
        response = app({ "x-request-method": "PUT" })
        self.assertEqual(response, {
            "x-status": 303,
            "x-content": "See Other: /somewhere-else\n",
            "content-type": "text/plain",
            "location": "/somewhere-else"
        })

#
# TestGet
#

class TestGet(unittest.TestCase):
    def test_present(self):
        @xhttp.get({
            "required": "^spam$",
             "optional?": "^albatross$",
             "list1+": "^\d+$",
             "list2*": "^[a-z]+$" })
        def app(req):
            self.assertEqual(req["x-get"], {
                "required": "spam",
                "optional": "albatross",
                "list1": ["23", "46"],
                "list2": ["aa"]
            })
        app({ "x-query-string": "required=spam&optional=albatross&list1=23&list1=46&list2=aa" })

    def test_missing_single(self):
        app = xhttp.get({
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-query-string": "optional=albatross&list1=23&list1=46&list2=aa" })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, { "x-detail": "GET parameter 'required' should occur exactly once" })

    def test_multiple_optional(self):
        app = xhttp.get({
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-query-string": "required=required&optional=albatross&optional=albatross&list1=23&list1=46&list2=aa" })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, { "x-detail": "GET parameter 'optional' should occur at most once" })

    def test_missing_multiple(self):
        app = xhttp.get({
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-query-string": "required=spam&optional=albatross&list2=aa" })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, { "x-detail": "GET parameter 'list1' should occur at least once" })

    def test_forbidden_parameter(self):
        app = xhttp.get({ "foo": "^bar$" })(None)
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-query-string": "foo=bar&spam=albatross" })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, { "x-detail": "Unknown GET parameter 'spam'" })

    def test_wrong_value(self):
        app = xhttp.get({
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-query-string": "required=spam&optional=albatross&list1=23&list1=ALBATROSS&list2=aa" })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, {
            "x-detail": "GET parameter 'list1' has bad value u'ALBATROSS'"
                        if sys.version_info[0] == 2 else
                        "GET parameter 'list1' has bad value 'ALBATROSS'"
        })

    def test_utf8(self):
        @xhttp.get({ "message": "^.+$" })
        def app(req):
            self.assertEqual(req["x-get"]["message"], u"hej, v\u00e4rld")
        app({ "x-query-string": "message=hej%2C%20v%C3%A4rld" })

    def test_bad_utf8(self):
        @xhttp.get({ "message": "^.+$" })
        def app(req):
            self.assertEqual(req["x-get"]["message"], u"hej, v\ufffdrld")
        app({ "x-query-string": "message=hej%2C%20v%E4rld" })

    def test_single_1(self):
        @xhttp.get({ "small?": "^(true|false)$" })
        def app(req):
            return req["x-get"]["small"]
        self.assertEqual(app({ "x-query-string": "" }), None)
        self.assertEqual(app({ "x-query-string": "small=true" }), "true")
        self.assertEqual(app({ "x-query-string": "small=false" }), "false")
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-query-string": "small=foo" })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, {
            "x-detail": "GET parameter 'small' has bad value u'foo'"
                        if sys.version_info[0] == 2 else
                        "GET parameter 'small' has bad value 'foo'"
        })
#
# TestPost
#

class TestPost(unittest.TestCase):
    def test_post(self):
        @xhttp.post({ "spam": "^albatross$" })
        def app(req):
            self.assertEqual(req["x-post"]["spam"], "albatross")
        content = "spam=albatross"
        app({
            "content-length": len(content),
            "x-wsgi-input": io.StringIO(content)
        })

    def test_post_with_bad_content_length(self):
        app = xhttp.post({ "spam": "^albatross$" })(None)
        content = "spam=albatross"
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "content-length": "evil!",
                "x-wsgi-input": io.StringIO(content)
            })
        self.assertEqual(ex.exception.status, 400)
        self.assertEqual(ex.exception.args[0], "Bad Request")
        self.assertEqual(ex.exception.headers, { "x-detail": "POST parameter 'spam' should occur exactly once" })

#
# TestIfModifiedSince
#

class TestIfModifiedSince(unittest.TestCase):
    def test_no_req_header(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 13
            }
        res = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
        })
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 13
        })

    def test_no_last_modified_header(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 13
            }
        res = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "if-modified-since": xhttp.headers.DateHeader("Wed, 09 Jun 1982 01:11:00 +0200")
        })
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 13
        })

    def test_modified(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 13,
                "last-modified": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
            }
        res = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "if-modified-since": xhttp.headers.DateHeader("Wed, 09 Jun 1982 01:11:00 +0200")
        })
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 13,
            "last-modified": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
        })

    def test_not_modified(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 13,
                "last-modified": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
            }
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({
                "x-request-method": "GET",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd(),
                "if-modified-since": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
            })
        self.assertEqual(ex.exception.status, 304)
        self.assertEqual(ex.exception.response(), { "x-status": 304 })

    def test_non_200(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.NO_CONTENT,
                "last-modified": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
            }
        res = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "if-modified-since": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
        })
        self.assertEqual(res, {
            "x-status": 204,
            "last-modified": xhttp.headers.DateHeader("Mon, 23 Jul 2012 20:00:00 +0200")
        })

#
# TestIfNoneMatch
#

class TestIfNoneMatch(unittest.TestCase):
    def test_no_etag(self):
        @xhttp.if_none_match
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 14,
            }
        response = app({ "if-none-match": "A" })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14
        })
    def test_no_if_none_match(self):
        @xhttp.if_none_match
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 14,
                "etag": "A"
            }
        response = app({})
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14,
            "etag": "A"
        })
    def test_differing_etag(self):
        @xhttp.if_none_match
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 14,
                "etag": "A"
            }
        response = app({ "if-none-match": "B" })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14,
            "etag": "A"
        })
    def test_non_200(self):
        @xhttp.if_none_match
        def app(req):
            return {
                "x-status": xhttp.status.NO_CONTENT,
                "etag": "A"
            }
        response = app({ "if-none-match": "A" })
        self.assertEqual(response, {
            "x-status": 204,
            "etag": "A"
        })
    def test_not_modified(self):
        @xhttp.if_none_match
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 14,
                "etag": "A"
            }
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "if-none-match": "A" })
        self.assertEqual(ex.exception.status, 304)

#
# TestServeFile
#
# TODO : UTF-8 files
# TODO : Binary files

class TestServeFile(unittest.TestCase):
    def test_existing_file(self):
        result = xhttp.utils.serve_file("tests/data/hello-world.txt", "text/plain", last_modified=False, etag=False)
        self.assertEqual(result, {
            "x-status": 200,
            "x-content": b"Hello, world!\n",
            "content-type": "text/plain",
            "content-length": 14,
        })

    def test_last_modified(self):
        result = xhttp.utils.serve_file("tests/data/hello-world.txt", "text/plain", last_modified=True, etag=False)
        self.assertEqual(result, {
            "x-status": 200,
            "x-content": b"Hello, world!\n",
            "content-type": "text/plain",
            "content-length": 14,
            "last-modified": xhttp.headers.DateHeader(os.path.getmtime("tests/data/hello-world.txt"))
        })

    def test_etag(self):
        result = xhttp.utils.serve_file("tests/data/hello-world.txt", "text/plain", last_modified=False, etag=True)
        self.assertEqual(result, {
            "x-status": 200,
            "x-content": b"Hello, world!\n",
            "content-type": "text/plain",
            "content-length": 14,
            "etag": "d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5"
        })

    def test_not_found(self):
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            xhttp.utils.serve_file("tests/data/albatross.txt", "text/plain")
        self.assertEqual(ex.exception.status, 404)
        self.assertEqual(ex.exception.args[0], "Not Found")
        self.assertEqual(ex.exception.headers, { "x-detail": "No such file or directory" })

    def test_file_read_throws_exception(self):
        class MockOpen(object):
            def __init__(self, filename, mode):
                pass
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_value, traceback):
                pass
            def read(self):
                raise Exception("random exception")
        if isinstance(__builtins__, dict):
            orig_open = __builtins__["open"]
            __builtins__["open"] = MockOpen
        else:
            orig_open = getattr(__builtins__, "open")
            setattr(__builtins__, "open", MockOpen)
        try:
            with self.assertRaises(Exception):
                xhttp.utils.serve_file("tests/data/albatross.txt", "text/plain")
        finally:
            if isinstance(__builtins__, dict):
                __builtins__["open"] = orig_open
            else:
                setattr(__builtins__, "open", orig_open)

#
# TestFileServer
#

class TestFileServer(unittest.TestCase):
    def test_found(self):
        app = xhttp.FileServer("tests/data", "text/plain", last_modified=False, etag=False)
        response = app({ "x-request-method": "GET" }, "hello-world.txt")
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": b"Hello, world!\n",
            "accept-ranges": "bytes",
            "content-type": "text/plain",
            "content-length": 14
        })

    def test_bad_filename(self):
        app = xhttp.FileServer("tests/data", "text/plain", last_modified=False, etag=False)
        with self.assertRaises(xhttp.exc.HTTPException) as ex:
            app({ "x-request-method": "GET" }, "../testxhttp.py")
        self.assertEqual(ex.exception.status, 403)

#
# TestAcceptEncoding
#

class TestAcceptEncoding(unittest.TestCase):
    def test_gzip_encode_decode(self):
        text = b"Hello, world!\n"
        compressed = xhttp.utils.gzip_encode(text)
        decompressed = xhttp.utils.gzip_decode(compressed)
        self.assertNotEqual(compressed, "")
        self.assertEqual(decompressed, text)

    def test_no_encoding(self):
        @xhttp.accept_encoding
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 14
            }
        res = app({})
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14
        })

    def test_gzip_encoding(self):
        @xhttp.accept_encoding
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": b"Hello, world!\n",
                "content-type": "text/plain"
            }
        content = xhttp.utils.gzip_encode(b"Hello, world!\n")
        res = app({ "accept-encoding": xhttp.headers.QListHeader("gzip,deflate,sdch") })
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": content,
            "content-type": "text/plain",
            "content-length": len(content),
            "content-encoding": "gzip"
        })

    def test_unacceptable_encoding(self):
        @xhttp.accept_encoding
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": b"Hello, world!\n",
                "content-type": "text/plain"
            }
        res = app({ "accept-encoding": xhttp.headers.QListHeader("some-unknown-method") })
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": b"Hello, world!\n",
            "content-type": "text/plain"
        })


class TestRanged(unittest.TestCase):
    @xhttp.ranged
    @staticmethod
    def app(req):
        if req["x-request-method"] == "POST":
            return { "x-status": xhttp.status.NO_CONTENT }
        else:
            return {
                "x-status": xhttp.status.OK,
                "x-content": "Hello, world!\n",
                "content-type": "text/plain"
            }

    def test_no_range(self):
        response = self.app({ "x-request-method": "GET" })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": "Hello, world!\n",
            "accept-ranges": "bytes",
            "content-type": "text/plain"
        })

    def test_range(self):
        response = self.app({
            "x-request-method": "GET",
            "range": xhttp.headers.RangeHeader("bytes=0-4") })
        self.assertEqual(response, {
            "x-status": 206,
            "x-content": "Hello",
            "accept-ranges": "bytes",
            "content-type": "text/plain",
            "content-range": "bytes 0-4/14"
        })

    def test_no_content(self):
        response = self.app({
            "x-request-method": "POST",
            "range": xhttp.headers.RangeHeader("bytes=0-4") })
        self.assertEqual(response, {
            "x-status": 204,
            "accept-ranges": "bytes"
        })


class TestAppCached(unittest.TestCase):
    @xhttp.app_cached(1)
    @staticmethod
    def app(req, key):
        return {
            "x-status": xhttp.status.OK,
            "x-content": "Hello, world!\n",
            "content-type": "text/plain"
        }

    def test_cache(self):
        response_1 = self.app({}, "a") # miss
        response_2 = self.app({}, "a") # hit
        response_3 = self.app({}, "b") # miss
        response_4 = self.app({}, "b") # hit
        response_5 = self.app({}, "a") # miss
        response_6 = self.app({}, "a") # hit
        self.assertEqual(response_1["x-cache"], "MISS")
        self.assertEqual(response_2["x-cache"], "HIT")
        self.assertEqual(response_3["x-cache"], "MISS")
        self.assertEqual(response_4["x-cache"], "HIT")
        self.assertEqual(response_5["x-cache"], "MISS")
        self.assertEqual(response_6["x-cache"], "HIT")

class TestCacheControl(unittest.TestCase):
    @xhttp.cache_control('must-revalidate')
    @staticmethod
    def app(req):
        return {
            'x-status': xhttp.status.OK,
            'x-content': 'Hello, world!',
            'content-type': 'text/plain',
            'etag': 'A'
        }

    def test_cache_control(self):
        response = self.app({ 'whatever': 'whatever' })
        self.assertEqual(response, {
            'x-status': 200,
            'x-content': 'Hello, world!',
            'content-type': 'text/plain',
            'etag': 'A',
            'cache-control': 'must-revalidate' })

class TestRedirector(unittest.TestCase):
    def test_redirector(self):
        redirector = xhttp.Redirector('/test')
        with self.assertRaises(xhttp.exc.HTTPException) as e:
            redirector.GET({})
        self.assertEqual(e.exception.status, 303)
        self.assertEqual(e.exception.headers, {
            'location': '/test',
            'x-detail': '/test' })

if __name__ == '__main__':
    unittest.main()
