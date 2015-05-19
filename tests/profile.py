import cProfile
from testxhttp import * # pragma: no flakes

cProfile.run("unittest.main(verbosity=2)", sort='time')

