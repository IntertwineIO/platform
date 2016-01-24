#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Platform: Intertwine.io's website

A platform to create a community

Created by Intertwine
Copyright (c) 2015, 2016

License:  Proprietary.  All rights reserved.
'''
import os
import re
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

package_name = 'intertwine'
# Grab package information without importing
with open('{}/__init__.py'.format(package_name), 'r') as fd:
    pattern = '^__(?P<key>[0-9_A-Za-z]+)__\s+\=\s+[\'"]?(?P<value>.*)[\'"]?$'
    eng = re.compile(pattern)
    data = {}
    for line in fd:
        if eng.search(line):
            group_data = [m.groupdict() for m in eng.finditer(line)][0]
            key = group_data['key']
            value = group_data['value']
            if value.endswith("'"):
                value = value.rstrip("'")
            data[key] = value

# Setup README documentation in RST format if pypandoc exists
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except ImportError:
    with open('README.md', 'r') as fd:
        long_description = fd.read()


###############################################################################
#  Requirements
###############################################################################
# Identifies what is needed to prior to running setup
setup_requires = [
    'pip',
    'pytest-runner',
]

# Identifies what is needed to run this package
install_requires = [
    'flask',
    'flask-bootstrap',
    'flask-login',
    'flask-sqlalchemy',
    'flask-security',
    'flask-wtf',
    'future'
]

# Identifies what is needed to run this package as a developer
dev_requires = [
    'flask-debugtoolbar',
]

# Identifies what is needed to run the scripts included
script_requires = [
    'docopt',
    'pyyaml',
]

# Identifies what is needed for tests to run
testing_requires = [
    'pytest',
    'pytest-cov',
    'pytest-flake8',
    'pytest-xdist',
]


# Identifies what is needed for deployment
deploy_requires = [
]


# Identifies what is needed for generating documentation
doc_requires = [
    'pypandoc',
    'sphinx'
]

extras_requires = {
    'dev': (install_requires +
            script_requires +
            dev_requires +
            testing_requires +
            deploy_requires),
    'docs': doc_requires,
    'deploy': deploy_requires,
    'script': script_requires,
    'testing': testing_requires,
}


###############################################################################
#  Commands
###############################################################################
# Setup test installation
class PyTest(TestCommand):
    test_package_name = package_name

    def finalize_options(self):
        TestCommand.finalize_options(self)
        _test_args = [
            '--verbose',
            '--ignore=build',
            '--cov={0}'.format(self.test_package_name),
            '--cov-report=term-missing',
            '--pep8',
            '--flake8',
            '--norecursedirs'
        ]
        extra_args = os.environ.get('PYTEST_EXTRA_ARGS')
        if extra_args is not None:
            _test_args.extend(extra_args.split())
        self.test_args = _test_args
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name=data.get('title'),
    version=data.get('version'),
    author=data.get('author'),
    author_email=data.get('email'),
    description=data.get('shortdesc'),
    long_description=long_description,
    license=data.get('license'),
    url=data.get('url'),
    packages=[package_name],
    package_data={},
    classifiers=[
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    install_requires=install_requires,
    setup_requires=setup_requires,
    extras_require=extras_requires,
    tests_require=testing_requires,
    test_suite='tests',
    cmdclass={'test': PyTest},
)
