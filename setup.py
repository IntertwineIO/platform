#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Platform: Intertwine.io's website

Untangle the world's problems

Created by Intertwine
Copyright (c) 2015, 2016

License:  Proprietary.
'''
import re

from setuptools import setup

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
    'libsass >= 0.6.0',
]

# Identifies what is needed to run this package
install_requires = [
    'flask',
    'flask-bootstrap',
    'flask-security',
    'flask-sqlalchemy',
    'flask-wtf',
    'future',
    'titlecase',
    'urlnorm',
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
    'detox',
    'flask-debugtoolbar',
    'pytest',
    'pytest-cov',
    'pytest-flake8',
    'pytest-xdist',
    'tox',
]


# Identifies what is needed for deployment
deploy_requires = [
]


# Identifies what is used for debugging
debug_requires = [
    'ipython',
    'ipdb',
    'pdbpp'
]

# Identifies what is needed for generating documentation
doc_requires = [
    'sphinx',
]

extras_requires = {
    'dev': (install_requires +
            script_requires +
            dev_requires +
            testing_requires +
            debug_requires +
            deploy_requires),
    'docs': doc_requires,
    'deploy': deploy_requires,
    'script': script_requires,
    'tests': testing_requires,
}

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
)
