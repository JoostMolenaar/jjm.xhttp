import unittest
import os
import os.path

from StringIO import StringIO

from jjm import xhttp

class TestDecorator(unittest.TestCase):
    class dec(xhttp.decorator):
        def __call__(self, *a, **k):
            return self.func(*a, **k)

    def test_func(self):
        @TestDecorator.dec
        def albatross(x):
            return 2 * x
        self.assertEqual(albatross(23), 46)

    def test_method(self):
        class Albatross(object):
            @TestDecorator.dec
            def spam(self, x):
                return 3 * x
        albatross = Albatross()
        self.assertEqual(albatross.spam(23), 69)

        
    def test_func_path(self):
        class C(object):
            @TestDecorator.dec
            def spam(self, x):
                return 4 * x
        # XXX Can't really find a real-world scenario where the 2nd argument to __get__ is None!
        obj = C() 
        spam = C.__dict__["spam"].__get__(obj, None)
        self.assertEqual(spam(obj, 23), 92)

class TestQlist(unittest.TestCase):
    def test_parse(self):
        qlist = xhttp.qlist("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        self.assertIsNotNone(qlist)
        self.assertEquals(
            [ v for (_, _, v) in qlist.items ], 
            ["text/html", "application/xhtml+xml", "application/xml", "*/*"])

    def test_roundtrip(self):
        s1 = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        qlist = xhttp.qlist(s1)
        s2 = str(qlist)
        self.assertEqual(s2, s1)

    def test_negotiate_exact_match(self):
        qlist = xhttp.qlist("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        result = qlist.negotiate_mime(["application/xml", "image/png"])
        self.assertEqual(result, "application/xml")

    def test_negotiate_any_match(self):
        qlist = xhttp.qlist("text/html,application/xhtml+xml,application/xml;q=0.9,text/*;q=0.85,*/*;q=0.8")
        result = qlist.negotiate_mime(["foo/bar"])
        self.assertEqual(result, "foo/bar")

    def test_negotiate_partial_match(self):
        qlist = xhttp.qlist("application/xhtml+xml,application/xml;q=0.9,text/*;q=0.95,*/*;q=0.8")
        result = qlist.negotiate_mime(["application/xml", "text/plain"])
        self.assertEqual(result, "text/plain")

    def test_negotiate_no_match(self):
        qlist = xhttp.qlist("text/*;q=0.95,application/xhtml+xml,application/xml;q=0.9,text/*;q=0.85")
        result = qlist.negotiate_mime(["image/png", "audio/mpeg"])
        self.assertEqual(result, None)

    def test_negotiate_bad_header(self):
        qlist = xhttp.qlist("text/plain;q=albatross")
        result = qlist.negotiate_mime(["image/png", "audio/mpeg"])
        self.assertEqual(qlist.items, [])
        self.assertEqual(result, None)

    def test_repr(self):
        qlist = xhttp.qlist("text/plain;q=0.9, application/xhtml+xml")
        result = repr(qlist)
        self.assertEquals(result, "qlist('text/plain;q=0.9,application/xhtml+xml')")

class TestDate(unittest.TestCase):
    def test_epoch(self):
        date = xhttp.date("Thu, 01 Jan 1970 00:00:00 GMT")
        self.assertEqual(date.timestamp, 0)
        self.assertEqual(str(date), "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_my_birthday_gmt(self):
        date = xhttp.date("Tue, 08 Jun 1982 23:11:00 GMT")
        self.assertEqual(date.timestamp, 392425860)
        self.assertEqual(str(date), "Tue, 08 Jun 1982 23:11:00 GMT")

    def test_my_birthday_in_my_timezone(self):
        date = xhttp.date("Wed, 09 Jun 1982 01:11:00 +0200")
        self.assertEqual(date.timestamp, 392425860)
        self.assertEqual(str(date), "Tue, 08 Jun 1982 23:11:00 GMT")

    def test_epoch_to_str(self):
        date = xhttp.date(0)
        self.assertEqual(str(date), "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_my_birthday_in_gmt_to_str(self):
        date = xhttp.date(392425860)
        self.assertEqual(str(date), "Tue, 08 Jun 1982 23:11:00 GMT")

    def test_wrong_input(self):
        with self.assertRaises(ValueError) as ex:
            xhttp.date(None)
        self.assertEqual(type(ex.exception), ValueError)
        self.assertEqual(ex.exception.message, "Unsupported type NoneType")

    def test_repr(self):
        date = xhttp.date("Wed, 09 Jun 1982 01:11:00 +0200")
        result = repr(date)
        self.assertEqual(result, "date('Tue, 08 Jun 1982 23:11:00 GMT')")

    def test_cmp(self):
        date1 = xhttp.date("Wed, 09 Jun 1982 01:11:00 +0200")
        date1b = xhttp.date("Wed, 09 Jun 1982 01:11:00 +0200")
        date2 = xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
        self.assertTrue(date1 == date1b)
        self.assertTrue(date1 < date2)
        self.assertTrue(date2 > date1)

def test_environ(method, request_uri, headers):
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

class TestHTTPException(unittest.TestCase):
    def test_without_detail(self):
        ex = xhttp.HTTPException(xhttp.status.BAD_REQUEST)
        self.assertEqual(str(ex), "Bad Request")
        self.assertEqual(ex.response(), {
            "x-status": 400,
            "x-content": ["Bad Request\n"],
            "content-type": "text/plain",
            "content-length": 12
        })

    def test_with_detail(self):
        ex = xhttp.HTTPException(xhttp.status.BAD_REQUEST, { "x-detail": "Just because" })
        self.assertEqual(str(ex), "Bad Request")
        self.assertEqual(ex.response(), {
            "x-status": 400,
            "x-content": ["Bad Request: Just because\n"],
            "content-type": "text/plain",
            "content-length": 26
        })

class TestXhttpAppDecorator(unittest.TestCase):
    def test_1(self):
        @xhttp.xhttp_app
        def app(request):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain"
            }

        def start_response(status, headers):
            self.assertEqual(status, "200 OK")
            self.assertEqual(headers, [("Content-Type", "text/plain")])

        environ = test_environ("GET", "/", {})

        result = app(environ, start_response)

        self.assertEquals(result, ["Hello, world!\n"])

class HelloWorld(xhttp.Resource):
    def GET(self, request):
        return {
            "x-status": xhttp.status.OK,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14
        }

    def PUT(self, request):
        return {
            "x-status": xhttp.status.NO_CONTENT
        }

class TestResource(unittest.TestCase):
    def test_get(self):
        app = HelloWorld()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd()
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14
        })

    def test_options(self):
        app = HelloWorld()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "OPTIONS",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 200,
            "x-content": ["OK: GET HEAD OPTIONS PUT\n"],
            "allowed": "GET HEAD OPTIONS PUT",
            "content-type": "text/plain",
            "content-length": 25 
        })

    def test_head(self):
        app = HelloWorld()
        response = app({
            "x-request-method": "HEAD",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd()
        })
        self.assertEqual(response, {
            "x-status": 200,
            "content-type": "text/plain",
            "content-length": 14
        })

    def test_head_with_no_get(self):
        app = xhttp.Resource()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "HEAD",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 405,
            "x-content": ["Method Not Allowed: GET\n"],
            "content-type": "text/plain",
            "content-length": 24 
        })
        
    def test_unknown_method(self):
        app = HelloWorld()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "FOO",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 400,
            "x-content": ["Bad Request: FOO\n"],
            "content-type": "text/plain",
            "content-length": 17 
        })

    def test_method_not_allowed(self):
        app = HelloWorld()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "POST",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 405,
            "x-content": ["Method Not Allowed: POST\n"],
            "content-type": "text/plain",
            "content-length": 25 
        })

class HelloWorldRouter(xhttp.Router):
    def __init__(self):
        super(HelloWorldRouter, self).__init__(
            (r'^/hello/$', HelloWorld())
        )

class TestRouter(unittest.TestCase):
    def test_not_found(self):
        app = HelloWorldRouter()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "GET",
                "x-request-uri": "/foo",
                "x-path-info": "/foo",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 404,
            "x-content": ["Not Found: /foo\n"],
            "content-type": "text/plain",
            "content-length": 16 
        })

    def test_not_found_2(self):
        app = HelloWorldRouter()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "GET",
                "x-request-uri": "/foo/",
                "x-path-info": "/foo/",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 404,
            "x-content": ["Not Found: /foo/\n"],
            "content-type": "text/plain",
            "content-length": 17 
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
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14 
        })

    def test_redirect_get(self):
        app = HelloWorldRouter()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "GET",
                "x-request-uri": "/hello",
                "x-path-info": "/hello",
                "x-query-string": "",
                "x-document-root": os.getcwd()
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 303,
            "x-content": ["See Other: /hello/\n"],
            "content-type": "text/plain",
            "content-length": 19,
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

class HelloContentNegotiatingWorld(xhttp.Resource):
    @xhttp.negotiate
    def GET(self, req):
        greeting = { 
            "message": "Hello, world!" 
        }
        greeting_view = {
            "text/plain"            : lambda m: m["message"] + "\n",
            "text/html"             : lambda m: ["p", m["message"]],
            "application/json"      : lambda m: m,
            "application/xhtml+xml" : lambda m: ["p", ("xmlns", "http://www.w3.org/1999/xhtml"), m["message"]],
            "application/xml"       : lambda m: ["message", m["message"]] 
        }
        result = {
            "x-status"       : 200,
            "x-content"      : greeting,
            "x-content-view" : greeting_view
        }
        return result

class TestNegotiate(unittest.TestCase):
    def test_not_acceptable(self):
        app = HelloContentNegotiatingWorld()
        with self.assertRaises(xhttp.HTTPException) as ex:
            response = app({
                "x-request-method": "GET",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd(),
                "accept": xhttp.qlist("image/png")
            })
        self.assertEqual(ex.exception.response(), {
            "x-status": 406,
            "x-content": ["Not Acceptable\n"],
            "content-type": "text/plain",
            "content-length": 15
        })

    def test_text_plain(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "accept": xhttp.qlist("text/plain")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14
        })

    def test_text_html(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "accept": xhttp.qlist("text/html")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["<p>Hello, world!</p>"],
            "content-type": "text/html",
            "content-length": 20
        })

    def test_application_json(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "accept": xhttp.qlist("application/json")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["{\"message\": \"Hello, world!\"}"],
            "content-type": "application/json",
            "content-length": 28
        })

    def test_application_xhtml_xml(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "accept": xhttp.qlist("application/xhtml+xml")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["<p xmlns=\"http://www.w3.org/1999/xhtml\">Hello, world!</p>"],
            "content-type": "application/xhtml+xml",
            "content-length": 57
        })

    def test_application_xml(self):
        app = HelloContentNegotiatingWorld()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "accept": xhttp.qlist("application/xml")
        })
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["<message>Hello, world!</message>"],
            "content-type": "application/xml",
            "content-length": 32
        })

class ExceptionalResource(xhttp.Resource):
    @xhttp.catcher
    def GET(self, req):
        raise Exception("foo")

    @xhttp.catcher
    def PUT(self, req):
        location = "/somewhere-else"
        raise xhttp.HTTPException(xhttp.status.SEE_OTHER, { "location": location, "x-detail": location })

class TestCatcher(unittest.TestCase):
    def test_exception(self):
        app = ExceptionalResource()
        response = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
        })
        self.assertEqual(response, {
            "x-status": 500,
            "x-content": ["Internal Server Error: Exception\n\nfoo\n"],
            "content-type": "text/plain",
            "content-length": 38
        }) 

    def test_http_exception(self):
        app = ExceptionalResource()
        response = app({
            "x-request-method": "PUT",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
        })
        self.assertEqual(response, {
            "x-status": 303,
            "x-content": ["See Other: /somewhere-else\n"],
            "content-type": "text/plain",
            "content-length": 27,
            "location": "/somewhere-else"
        })
        self.assertEqual(sum(len(chunk) for chunk in response["x-content"]), response["content-length"])

class TestGet(unittest.TestCase):
    def test_present(self):
        @xhttp.get({ 
            "required": "^spam$",
             "optional?": "^albatross$",
             "list1+": "^\d+$",
             "list2*": "^[a-z]+$" })
        def app(req):
            self.assertEquals(req["x-get"], {
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
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({ "x-query-string": "optional=albatross&list1=23&list1=46&list2=aa" }) 
        self.assertEquals(ex.exception.status, 400)
        self.assertEquals(ex.exception.message, "Bad Request")
        self.assertEquals(ex.exception.headers, { "x-detail": "GET parameter 'required' should occur exactly once" })

    def test_multiple_optional(self):
        app = xhttp.get({ 
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({ "x-query-string": "required=required&optional=albatross&optional=albatross&list1=23&list1=46&list2=aa" }) 
        self.assertEquals(ex.exception.status, 400)
        self.assertEquals(ex.exception.message, "Bad Request")
        self.assertEquals(ex.exception.headers, { "x-detail": "GET parameter 'optional' should occur at most once" })

    def test_missing_multiple(self):
        app = xhttp.get({ 
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({ "x-query-string": "required=spam&optional=albatross&list2=aa" }) 
        self.assertEquals(ex.exception.status, 400)
        self.assertEquals(ex.exception.message, "Bad Request")
        self.assertEquals(ex.exception.headers, { "x-detail": "GET parameter 'list1' should occur at least once" })

    def test_forbidden_parameter(self):
        app = xhttp.get({ "foo": "^bar$" })(None)
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({ "x-query-string": "foo=bar&spam=albatross" })
        self.assertEquals(ex.exception.status, 400)
        self.assertEquals(ex.exception.message, "Bad Request")
        self.assertEquals(ex.exception.headers, { "x-detail": "Unknown GET parameter 'spam'" })

    def test_wrong_value(self):
        app = xhttp.get({ 
            "required": "^spam$",
            "optional?": "^albatross$",
            "list1+": "^\d+$",
            "list2*": "^[a-z]+$" })(None)
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({ "x-query-string": "required=spam&optional=albatross&list1=23&list1=ALBATROSS&list2=aa" }) 
        self.assertEquals(ex.exception.status, 400)
        self.assertEquals(ex.exception.message, "Bad Request")
        self.assertEquals(ex.exception.headers, { "x-detail": "GET parameter 'list1' has bad value 'ALBATROSS'" })

    def test_utf8(self):
        @xhttp.get({ "message": "^.+$" })
        def app(req):
            self.assertEqual(req["x-get"]["message"], u"hej, v\u00e4rld")
        app({ "x-query-string": "message=hej%2C%20v%C3%A4rld" })

    def test_bad_utf8(self):
        @xhttp.get({ "message": "^.+$" })
        def app(req):
            self.assertEquals(req["x-get"]["message"], u"hej, v\ufffdrld")
        app({ "x-query-string": "message=hej%2C%20v%E4rld" })

class TestPost(unittest.TestCase):
    def test_post(self):
        @xhttp.post({ "spam": "^albatross$" })
        def app(req):
            self.assertEquals(req["x-post"]["spam"], "albatross")
        content = "spam=albatross"
        app({
            "content-length": len(content),
            "x-wsgi-input": StringIO(content)
        })

    def test_post_with_bad_content_length(self):
        app = xhttp.post({ "spam": "^albatross$" })(None)
        content = "spam=albatross"
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({
                "content-length": "evil!",
                "x-wsgi-input": StringIO(content)
            })
        self.assertEquals(ex.exception.status, 400)
        self.assertEquals(ex.exception.message, "Bad Request")
        self.assertEquals(ex.exception.headers, { "x-detail": "POST parameter 'spam' should occur exactly once" })

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
            "if-modified-since": xhttp.date("Wed, 09 Jun 1982 01:11:00 +0200")
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
                "last-modified": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
            }
        res = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "if-modified-since": xhttp.date("Wed, 09 Jun 1982 01:11:00 +0200")
        })
        self.assertEqual(res, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 13,
            "last-modified": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
        })

    def test_not_modified(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.OK,
                "x-content": ["Hello, world!\n"],
                "content-type": "text/plain",
                "content-length": 13,
                "last-modified": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
            }
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({
                "x-request-method": "GET",
                "x-request-uri": "/",
                "x-path-info": "/",
                "x-query-string": "",
                "x-document-root": os.getcwd(),
                "if-modified-since": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
            })
        self.assertEquals(ex.exception.status, 304)
        self.assertEquals(ex.exception.response(), { "x-status": 304 })

    def test_non_200(self):
        @xhttp.if_modified_since
        def app(req):
            return {
                "x-status": xhttp.status.NO_CONTENT,
                "last-modified": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
            }
        res = app({
            "x-request-method": "GET",
            "x-request-uri": "/",
            "x-path-info": "/",
            "x-query-string": "",
            "x-document-root": os.getcwd(),
            "if-modified-since": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
        })
        self.assertEquals(res, {
            "x-status": 204,
            "last-modified": xhttp.date("Mon, 23 Jul 2012 20:00:00 +0200")
        })

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
        with self.assertRaises(xhttp.HTTPException) as ex:
            app({ "if-none-match": "A" })
        self.assertEqual(ex.exception.status, 304)

class TestServeFile(unittest.TestCase):
    def test_existing_file(self):
        result = xhttp.serve_file("data/hello-world.txt", "text/plain", last_modified=False, etag=False)
        self.assertEqual(result, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14,
        })

    def test_last_modified(self):
        result = xhttp.serve_file("data/hello-world.txt", "text/plain", last_modified=True, etag=False)
        self.assertEqual(result, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14,
            "last-modified": xhttp.date(os.path.getmtime("data/hello-world.txt"))
        })

    def test_etag(self):
        result = xhttp.serve_file("data/hello-world.txt", "text/plain", last_modified=False, etag=True)
        self.assertEqual(result, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14,
            "etag": "d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5"
        })

    def test_not_found(self):
        with self.assertRaises(xhttp.HTTPException) as ex:
            xhttp.serve_file("data/albatross.txt", "text/plain")
        self.assertEquals(ex.exception.status, 404)
        self.assertEquals(ex.exception.message, "Not Found")
        self.assertEquals(ex.exception.headers, { "x-detail": "No such file or directory" })

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
        orig_open = __builtins__["open"]
        __builtins__["open"] = MockOpen
        try:
            with self.assertRaises(Exception) as ex:
                xhttp.serve_file("data/albatross.txt", "text/plain")
        finally:
            __builtins__["open"] = orig_open

class TestFileServer(unittest.TestCase):
    def test_found(self):
        app = xhttp.FileServer("data", "text/plain", last_modified=False, etag=False)
        response = app({ "x-request-method": "GET" }, "hello-world.txt")
        self.assertEqual(response, {
            "x-status": 200,
            "x-content": ["Hello, world!\n"],
            "content-type": "text/plain",
            "content-length": 14
        })

    def test_bad_filename(self):
        app = xhttp.FileServer("data", "text/plain", last_modified=False, etag=False)
        with self.assertRaises(xhttp.HTTPException) as ex: 
            app({ "x-request-method": "GET" }, "../testxhttp.py")
        self.assertEquals(ex.exception.status, 403)

if __name__ == '__main__':
    unittest.main()
