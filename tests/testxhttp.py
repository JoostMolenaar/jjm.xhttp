import unittest

import jjm.xhttp

class Test_http_qlist(unittest.TestCase):
    def test_parse(self):
        qlist = jjm.xhttp.http_qlist("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        self.assertIsNotNone(qlist)
        self.assertEquals(
            [ v for (_, _, v) in qlist.items ], 
            ["text/html", "application/xhtml+xml", "application/xml", "*/*"])

    def test_roundtrip(self):
        s1 = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        qlist = jjm.xhttp.http_qlist(s1)
        s2 = str(qlist)
        self.assertEqual(s2, s1)

    def test_negotiate_exact_match(self):
        qlist = jjm.xhttp.http_qlist("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        result = qlist.negotiate_mime(["application/xml", "image/png"])
        self.assertEqual(result, "application/xml")

    def test_negotiate_any_match(self):
        qlist = jjm.xhttp.http_qlist("text/html,application/xhtml+xml,application/xml;q=0.9,text/*;q=0.85,*/*;q=0.8")
        result = qlist.negotiate_mime(["foo/bar"])
        self.assertEqual(result, "foo/bar")

    def test_negotiate_partial_match(self):
        qlist = jjm.xhttp.http_qlist("application/xhtml+xml,application/xml;q=0.9,text/*;q=0.95,*/*;q=0.8")
        result = qlist.negotiate_mime(["application/xml", "text/plain"])
        self.assertEqual(result, "text/plain")

    def test_negotiate_no_match(self):
        qlist = jjm.xhttp.http_qlist("text/*;q=0.95,application/xhtml+xml,application/xml;q=0.9,text/*;q=0.85")
        result = qlist.negotiate_mime(["image/png", "audio/mpeg"])
        self.assertEqual(result, None)

    def test_negotiate_bad_header(self):
        qlist = jjm.xhttp.http_qlist("text/plain;q=albatross")
        result = qlist.negotiate_mime(["image/png", "audio/mpeg"])
        self.assertEqual(qlist.items, [])
        self.assertEqual(result, None)


