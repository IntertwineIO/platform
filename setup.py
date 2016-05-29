#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Platform: Intertwine.io's website

Untangle the world's problems

Created by Intertwine
Copyright (c) 2015, 2016

License:  Proprietary.
'''

import os
import re
from setuptools import setup, find_packages


project_name = 'intertwine'

classifiers = [
    'Intended Audience :: Developers',
    'License :: Other/Proprietary License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: PyPy'
]

###############################################################################
#  Requirements
###############################################################################
requirements = {
    # Identifies what is needed to prior to running setup
    'setup': [
        'pip',
        'pytest-runner',
        'libsass >= 0.6.0',
    ],

    # Identifies what is needed to run this package
    'install': [
        'alchy>2.0.1',
        'docopt',
        'flask',
        'flask-bootstrap',
        'flask-security',
        'flask-sqlalchemy',
        'flask-wtf',
        'future',
        'titlecase',
        'urlnorm',
    ],

    # Identifies what is needed to run this package as a developer
    'debug': [
        'flask-debugtoolbar',
        'ipython',
        'ipdb',
    ],

    # Identifies what is needed for generating documentation
    'doc': [
        'sphinx',
    ],

    # Identifies what is needed for docker runs
    'docker': [
        'docker-py',
        'GitPython',
    ],

    # Identifies what is needed to run the scripts included
    'script': [
        'pyyaml',
    ],

    # Identifies what is needed for tests to run
    'tests': [
        'detox',
        'flask-debugtoolbar',
        'pytest',
        'pytest-cov',
        'pytest-flake8',
        'pytest-xdist',
        'tox',
    ],
}

# Developers should probably run:  pip install .[dev]
requirements['dev'] = [
    r for k, reqs in requirements.items() for r in reqs
    if k not in ['install']
]

# All is for usability:  pip install .[all]
requirements['all'] = [
    r for k, reqs in requirements.items() for r in reqs
]

# Find package files
packages = find_packages()
cwd = os.path.abspath(os.path.dirname(__file__))

# Capture project metadata
engine = re.compile(r"^__(?P<key>(.*?))__ = '(?P<value>([^']*))'")
with open(os.path.join(cwd, project_name, '__init__.py'), 'r') as fd:
    metadata = {
        data['key']: data['value']
        for line in fd
        for data in [m.groupdict() for m in engine.finditer(line)]
    }

# Read License for setup
with open(os.path.join(cwd, 'LICENSE.txt'), 'rb') as fd:
    lic = fd.read()
    # Decode didn't chain with read
    lic = lic.decode('utf-8')

# Setup README documentation in RST format if pypandoc exists
with open('README.rst', 'r') as fd:
    long_description = fd.read()

# Build static sass
sass_manifests = {
    metadata.get('title'): (
        'static/sass', 'static/css', '/static/css'
    )
}

setup(
    name=metadata.get('title'),
    version=metadata.get('version'),
    author=metadata.get('author'),
    author_email=metadata.get('email'),
    description=metadata.get('shortdesc'),
    long_description=long_description,
    license=metadata.get('license'),
    url=metadata.get('url'),
    packages=[project_name],
    package_data={},
    classifiers=classifiers,
    install_requires=requirements['install'],
    setup_requires=requirements['setup'],
    sass_manifests=sass_manifests,
    extras_require=requirements,
    tests_require=requirements['tests'],
    test_suite='tests',
    include_package_data=True,
    zip_safe=False,
    dependency_links=[
        'git+https://git@github.com/intertwine/urlnorm.git',
    ],
)
