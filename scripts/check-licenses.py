#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys

from pip.utils import get_installed_distributions


def check_package_licenses(**options):
    meta_files_to_check = ['PKG-INFO', 'METADATA']

    for installed_distribution in get_installed_distributions():
        found_license = None
        found_valid = None
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
                    file = sys.stdout
                    if 'gpl' in license.lower():
                        severity = '!!!'
                        file = sys.stderr
                        found_valid = True
                    elif 'unknown' in license.lower():
                        found_valid = False
                    else:
                        severity = '   '
                        found_valid = True
                    break
            if found_license:
                break
        if not found_license or not found_valid:
            file = sys.stderr
        msg = message.format(
            severity=severity,
            project_name=project_name,
            license=license
        )
        print(msg, file=file)


if __name__ == "__main__":
    check_package_licenses()
