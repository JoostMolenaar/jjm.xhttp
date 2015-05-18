#!/usr/bin/env python2.7

repo_names = ['xmlist']
dist_names = ['python-dateutil']
static_dirs = ['tests']

import os
import setuptools
import setuptools.command.test

class PyTest(setuptools.command.test.test):
    def initialize_options(self):
        setuptools.command.test.test.initialize_options(self)

    def finalize_options(self):
        setuptools.command.test.test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        pytest.main('tests --cov-report html --cov-report term --cov xhttp --cov-config .coveragerc'.split())

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

    'data_files': [ (root, [ root + '/' + fn for fn in files ])
                    for src_dir in static_dirs
                    for (root, dirs, files) in os.walk(src_dir) ],

    'install_requires': ['xmlist', 'python-dateutil'],
    'tests_require': ['pytest', 'pytest-cov'],
    'setup_requires': ['setuptools-version-command', 'setuptools-metadata'],

    'cmdclass':  {
        'test': PyTest
    },

    'custom_metadata': {
        'x_static_dirs': static_dirs
    }
})
