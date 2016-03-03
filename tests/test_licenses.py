#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import sys

from pip.utils import get_installed_distributions

from decorators import license


@license
@pytest.mark.license
def test_licenses(**options):
    '''
    Checks for licenses minus those that have been identified to
    be ignored.
    '''
    meta_files_to_check = ['PKG-INFO', 'METADATA']

    known_ignores = [
        # Pip packages added
        'pip',            # MIT
        'setuptools',     #

        # Virtualenv packages added
        'wheel',          # MIT

        # Test packages added
        'apipkg',         # MIT
        'coverage',       # Apache 2.0
        'detox',          # MIT
        'eventlet',       # MIT
        'execnet',        # MIT
        'flake8',         # MIT
        'greenlet',       # MIT
        'mccabe',         # Expat
        'pep8',           # Expat
        'pluggy',         # MIT
        'py',             # MIT
        'pyflakes',       # MIT
        'pytest',         # MIT
        'pytest-cache',   # MIT
        'pytest-cov',     # MIT
        'pytest-flake8',  # BSD
        'pytest-xdist'    # MIT
        'tox',            # MIT
        'virtualenv',     # MIT

        # Known licenses that do not register with this test
        'itsdangerous',   # BSD
        'intertwine',     # Proprietary
        # 'dominate',       # LGPL
    ]

    accepted_licenses = [
        'BSD',
        'MIT',
        'Apache 2.0',
        'PSF',
        'DSF'
    ]

    for installed_distribution in get_installed_distributions():
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
                    if not any(lic in license for lic in accepted_licenses):
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
