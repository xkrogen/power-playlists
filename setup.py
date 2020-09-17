#!/usr/bin/env python

from __future__ import absolute_import, print_function

from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

setup(
    name='spotify-dynamic-playlists',
    version='0.1',
    description='TODO',
    long_description='TODO',
    author='Erik Krogen',
    author_email='erikkrogen@gmail.com',
    url='TODO',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    project_urls={
    },
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    python_requires='>=3.7',
    install_requires=[
        'Click>=7.1,<8',
        'pytest>=6.0,<7',
        'PyYAML>=5.3,<6',
        'setuptools>=50.1,<51',
        'spotipy>=2.14.0,<3',
    ],
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
    },
    entry_points='''
        [console_scripts]
        spotify-dynamic-playlists=dynamicplaylist.main:cli
    '''
    )
