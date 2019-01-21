#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import pkg_resources
import pytest
import sys

from tests.decorators import license


@license
@pytest.mark.license
def test_licenses(**options):
    """
    Checks for licenses minus those that have been identified to
    be ignored.
    """
    meta_files_to_check = ['METADATA', 'PKG-INFO']

    known_ignores = [

        # Python standard packages
        'filelock',          # Unlicense
        'speaklater',        # BSD - Python3.6 standard package

        # Pip packages added
        'pip',               # MIT
        'setuptools',        # PSF

        # Deployment packages
        'ansible',           # GPL v3
        'click',             # BSD
        'docker-py',         # Apache 2.0
        'uWSGI',             # GPL2

        # Debug packages
        'entrypoints',       # MIT <- nbconvert <- jupyter
        'gnureadline',       # GPL 2 - TODO: Alternatives? not in Py3
        'prompt-toolkit',    # BSD
        'ptyprocess',        # ISC
        'pandocfilters',     # BSD 3-Clause <- nbconvert <- jupyter
        'terminado',         # BSD <- notebook <- jupyter
        'testpath',          # MIT <- nbconvert <- jupyter

        # Virtualenv packages added
        'wheel',             # MIT

        # Test packages added
        'ansi2html',         # GPLv3+ - only used by tox? not in Py3
        'apipkg',            # MIT
        'astroid',           # LGPL - python linter package; not in Py3
        'autopep8',          # Expat
        'backports-abc',     # PSF
        'coverage',          # Apache 2.0
        'detox',             # MIT
        'eventlet',          # MIT
        'execnet',           # MIT
        'flake8',            # MIT
        'greenlet',          # MIT
        'mccabe',            # Expat
        'ordereddict',       # MIT
        'pbr',               # BSD
        'pep8',              # Expat
        'pluggy',            # MIT
        'py',                # MIT
        'pycodestyle',       # Expat license
        'pyflakes',          # MIT
        'pytest',            # MIT
        'pytest-cache',      # MIT
        'pytest-cov',        # MIT
        'pytest-flake8',     # BSD
        'pytest-html',       # Mozilla Public License 2.0 (MPL 2.0)
        'pytest-runner',     # MIT
        'pytest-xdist',      # MIT
        'text-unidecode',    # Artistic-Perl-1.0 - used by Faker
        'tox',               # MIT
        'virtualenv',        # MIT

        # Docs
        'alabaster',         # BSD  - From Sphinx

        # Nagios: Zope Public License 2.1, a BSD-style Open Source license
        # Nagios plugin dependencies:
        'inotify',           # GPL 2 - TODO: Alternatives? not in Py3
        'graphitesend',      # Apache

        # Unknown - where did they come from?
        'aniso8601',         # Nonstandard/permissive: https://goo.gl/0kTVx3

        # Known licenses that do not register with this test
        'chardet',           # LGPL <- requests <- ? - TODO: Alternatives?
        'dominate',          # LGPL <- Flask-Bootstrap - TODO: Alternatives?
        'itsdangerous',      # BSD
        'mock',              # BSD
        'pbr',               # Apache 2.0
        'pendulum',          # MIT
        'python-dateutil',   # Simplified BSD <- pendulum, jupyter-client, Faker
        'stevedore',         # Apache 2.0
        'tzlocal',           # MIT
        'url-normalize',     # "Python" (PSF) License
        'websocket-client',  # LGPL - TODO: Alternatives? not in Py3

        # Company owned licenses
        'intertwine',        # Proprietary
    ]

    accepted_licenses = [
        'BSD',  # original 4-clause BSD
        'BSD 2.0', 'Revised BSD', 'New BSD', 'Modified BSD License',  # 3-clause BSD
        'Simplified BSD', 'FreeBSD',  # 2-clause BSD
        'MIT', 'Expat',
        'ZPL', 'Zope',
        'MPL', 'Mozilla Public License',
        'ASL', 'Apache', 'Apache 2.0',
        'PSF', 'Python Software Foundation',
        'DSF', 'Django Software Foundation',
        'ISC', 'ISCL', 'Internet Software Consortium',
        'Artistic-Perl-1.0',  # opensource.org/licenses/Artistic-Perl-1.0
        'Artistic-2.0',  # opensource.org/licenses/Artistic-2.0
        'Unlicense'  # http://unlicense.org/
    ]

    for installed_distribution in pkg_resources.working_set:
        found_license = None
        found_valid = None
        skip = False
        severity = ' ? '
        license = 'Found no license information'
        project_name = 'unknown'
        message = '{severity} {project_name}: {license}'
        for metafile in meta_files_to_check:
            if not installed_distribution.has_metadata(metafile):
                continue
            for line in installed_distribution.get_metadata_lines(metafile):
                if 'License: ' in line:
                    found_license = True
                    (k, license) = line.split(': ', 1)
                    project_name = installed_distribution.project_name
                    if project_name in known_ignores:
                        skip = True
                    file = sys.stdout
                    license = license.strip()
                    if not any(lic.lower() in license.lower()
                               for lic in accepted_licenses):
                        severity = '!!!'
                        file = sys.stderr
                        found_valid = False
                    elif 'unknown' in license.lower():
                        found_valid = False
                    else:
                        severity = '   '
                        found_valid = True
                    break
            if found_license:
                break
        if skip:
            continue
        if not found_license or not found_valid:
            file = sys.stderr
        msg = message.format(
            severity=severity,
            project_name=project_name,
            license=license
        )
        print(msg, file=file)
        assert found_license is True
        if project_name not in known_ignores:
            assert found_valid is True
