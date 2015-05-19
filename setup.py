#!/usr/bin/env python2.7

import os
import setuptools
import setuptools.command.test

os.environ['HTTP_PROXY']  = '127.0.0.1:65534'
os.environ['HTTPS_PROXY'] = '127.0.0.1:65535'

class PyTest(setuptools.command.test.test):
    def initialize_options(self):
        setuptools.command.test.test.initialize_options(self)

    def finalize_options(self):
        setuptools.command.test.test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        pytest.main(['-c', 'setup.cfg'])

def try_read_file(filename):
    try:
        with open(filename, 'r') as f: return f.read()
    except: pass

setuptools.setup(**{
    'name': 'xhttp',

    'version': try_read_file('xhttp.egg-info/version.txt'),
    'version_command': ('git describe', 'pep440-git'),

    'url': 'https://github.com/j0057/xhttp',
    'author': 'Joost Molenaar',
    'author_email': 'j.j.molenaar@gmail.com',

    'packages': ['xhttp'],

    'tests_require': ['pytest', 'pytest-cov', 'pytest-flakes'],
    'setup_requires': ['setuptools-version-command', 'setuptools-metadata'],
    'install_requires': ['xmlist', 'python-dateutil'],

    'cmdclass':  {
        'test': PyTest
    }
})
