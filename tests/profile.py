import cProfile
from testxhttp import *

cProfile.run("unittest.main(verbosity=2)", sort='time')

