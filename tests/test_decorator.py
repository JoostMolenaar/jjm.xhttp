import xhttp

class dec(xhttp.utils.decorator):
    def __call__(self, *a, **k):
        return 2 * self.func(*a, **k)

def test_func():
    @dec
    def albatross(x):
        return 2 * x
    assert albatross(23) == 92

def test_method():
    class Albatross(object):
        @dec
        def spam(self, x):
            return 3 * x
    albatross = Albatross()
    assert albatross.spam(23) == 138

def test_classmethod():
    class Albatross(object):
        @dec
        @classmethod
        def spam(cls, x):
            return 4 * x
    assert Albatross.spam(23) == 184

def test_staticmethod():
    class Albatross(object):
        @dec
        @staticmethod
        def spam(x):
            return 5 * x
    assert Albatross.spam(23) == 230

def test_func_path():
    class C(object):
        @dec
        def spam(self, x):
            return 6 * x
    # XXX Can't really find a real-world scenario where the 2nd argument to __get__ is None!
    obj = C()
    spam = C.__dict__["spam"].__get__(obj)
    assert spam(obj, 23) == 276
