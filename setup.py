#!/usr/bin/env python2.7

repo_names = ['xmlist']
package_names = ['python-dateutil']
static_dirs = []

import sys
if len(sys.argv) == 2 and sys.argv[1] == '--install-requires':
    print '\n'.join(package_names + repo_names)
elif len(sys.argv) == 2 and sys.argv[1] == '--repo-names':
    print '\n'.join(repo_names)
elif len(sys.argv) == 2 and sys.argv[1] == '--package-names':
    print '\n'.join(package_names)
elif len(sys.argv) == 2 and sys.argv[1] == '--static-dirs':
    print '\n'.join(static_dirs)
else:
    import os
    import setuptools
    setuptools.setup(
        author='Joost Molenaar',
        author_email='j.j.molenaar@gmail.com',
        name='xhttp',
        py_modules=['xhttp'],
        url='https://github.com/j0057/xhttp',
        version='0.1.0',
        data_files=[ (root, map(lambda f: root + '/' + f, files))
                     for src_dir in static_dirs
                     for (root, dirs, files) in os.walk(src_dir) ],
        install_requires=package_names + repo_names
    )
