import unittest
import os

from jjm import xhttp

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
            "content-length": 13
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
            "content-length": 13
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
            "x-content": ["OK\n"],
            "allowed": "GET HEAD OPTIONS",
            "content-type": "text/plain",
            "content-length": 3
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
            "content-length": 13
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

