#!/usr/bin/env python2.7

repo_names = ['xmlist']
dist_names = ['python-dateutil']
static_dirs = []

import os
from setuptools import setup

try:
    with open('xhttp.egg-info/version.txt', 'r') as f:
        version = f.read()
except:
    version = None

setup(
    name='xhttp',
    version=version,
    version_command=('git describe', 'pep440-git-dev'),
    py_modules=['xhttp'],
    author='Joost Molenaar',
    author_email='j.j.molenaar@gmail.com',
    url='https://github.com/j0057/xhttp',
    data_files=[ (root, [ root + '/' + fn for fn in files ])
                 for src_dir in static_dirs
                 for (root, dirs, files) in os.walk(src_dir) ],
    install_requires=dist_names+repo_names,
    custom_metadata={
        'x_repo_names': repo_names,
        'x_dist_names': dist_names,
        'x_static_dirs': static_dirs
    })
