#!/usr/bin/env python2.7

repo_names = ['xmlist']
dist_names = ['python-dateutil']
static_dirs = []

import os
from setuptools import setup

def read_file(filename):
    try:
        with open(filename, 'r') as f: return f.read()
    except:
        pass

setup(
    name='xhttp',
    version=read_file('xhttp.egg-info/version.txt'),
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
