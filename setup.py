#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Platform: Intertwine.io's website

Untangle the world's problems

Created by Intertwine
Copyright (c) 2015-2018

License:  Proprietary.
'''
from __future__ import unicode_literals

import datetime
import os
import re
import sys
from collections import namedtuple

from setuptools import find_packages, setup


def setup_project():
    '''Sets up project as needed.

    This function should be manually updated as needed.  Placed at the
    top of the file for better grokking.

    When developing, simply run (from within a virtualenv):

        $ pip install .[all]

    Returns:
        package_requires(list): List of required packages
        links(list): list of private package links
        classifiers(list): standard python package classifiers
    '''
    # Whatever dependencies package requires
    package_requires = [
        'alchy==2.2.2',  # was 2.0.1
        'docopt==0.6.2',
        # 'enum34==1.1.6',
        'Faker==0.8.13',
        'flask==1.0.2',
        'flask-bootstrap==3.3.7.1',
        'flask-restful==0.3.6',
        'flask-security==3.0.0',
        'flask-sqlalchemy==2.3.2',
        'flask-wtf==0.14.2',
        'future==0.16.0',
        # 'mock==2.0.0',
        'pendulum==2.0.1',  # was 1.2.5
        'SQLAlchemy==1.2.7',  # was 1.1.14
        'timezonefinder==2.1.2',
        'titlecase==0.12.0',
        'url-normalize==1.3.3',
    ]

    return package_requires


# ----------------------------------------------------------------------
# Generally, only edit above this line
# ----------------------------------------------------------------------
def get_package_metadata(project_name=None):
    '''Captures metadata information for package

    Providing the project name will reduce the search/install time.

    Args:
        project_name: top project folder and project name

    Returns:
        dict: package metdata
    '''
    top_folder = os.path.abspath(os.path.dirname(__file__))
    required_fields = ['version', 'license', 'url', 'description', 'project']
    metadata = {}
    missing_message = []
    package_names = [p for p in find_packages() if '.' not in p]
    for root, folder, files in os.walk(top_folder):
        if not any(root.endswith(p) for p in package_names):
            continue
        for filename in files:
            if filename == '__metadata__.py':
                filepath = os.path.join(root, filename)
                relpath = filepath.replace(top_folder, '').lstrip('/')
                with open(os.path.join(filepath)) as fd:
                    exec(fd.read(), metadata)
                if 'package_metadata' in metadata:
                    metadata = metadata.get('package_metadata', {})
                if not all(field in metadata for field in required_fields):
                    missing = ', '.join(
                        field
                        for field in sorted(required_fields)
                        if field not in metadata
                    )
                    missing_message.append('{} is missing: {}'.format(relpath, missing))
                    metadata = {}
            if metadata:
                break
        if metadata:
            break
    if not metadata:
        print('Required package fields: {}'.format(', '.join(sorted(required_fields))))
        print('\n'.join(missing_message))
        raise Exception('Could not find package')
    return metadata


def get_package_requirements(package_requires, required=None):
    '''Convenience function to wrap package_requires

    Args:
        required(list): list of required packages to run
    Returns:
        dict: A better format of requirements
    '''
    required = package_requires if not required else required
    requirements = {
        # Debug probably is only necessary for development environments
        'debug': [
            'flask-debugtoolbar',
            'ipdb',
            'ipython',
            'jupyter',
        ],

        # Deploy identifies upgrades to local system prior to deployment
        'deploy': [
            'tornado==3.2',
            'ansible >= 2',
            'chaussette',
            'circus',
            'circus-web',
            'gitpython',
            'uwsgi',
        ],

        # Docs should probably only be necessary in Continuous Integration
        'docs': [
            'coverage',
            'sphinx',
            'sphinx_rtd_theme',
            'sphinxcontrib-napoleon',
        ],

        # Examples probably is only necessary for development environments
        'examples': [
            'docopt',
            'pyyaml',
        ],

        # Monitoring identifies upgrades to remote system mostly for nagios
        'monitoring': [
            'inotify',
            'psutil',
            'graphitesend',
        ],

        # Requirements is the basic needs for this package
        'requirements': required,

        # Required for installation
        'setup': [
            'pip',
            # 'pytest-runner',
            # 'libsass >= 0.6.0',
        ],

        # Required for running scripts folder
        'scripts': [
            'GitPython',
            'docker-py',
            'python-magic',
            'pyyaml',
        ],

        # Tests are needed in a local and CI environments for py.test and tox
        # Note:  To run the tox environment for docs, docs must also be installed
        'tests': [
            'detox',
            'flask-debugtoolbar',
            'pdbpp',
            'pytest',
            'pytest-cov',
            'pytest-flake8',
            'pytest-html',
            'pytest-xdist',
            'tox',
        ],

    }

    # Developers should probably run:  pip install .[dev]
    requirements['dev'] = [
        r for k, reqs in requirements.items() for r in reqs
        if k not in ['requirements']
    ]

    # All is for usability:  pip install .[all]
    requirements['all'] = [
        r for k, reqs in requirements.items() for r in reqs
    ]

    return requirements


def get_sass_manifests(metadata):
    '''Sets up static sass conversion on an install.

    Args:
        metadata(dict): project metadata

    Returns:
        dict: sass locations for project
    '''
    SassPath = namedtuple('SassPath', ('sass', 'css', 'endpoint'))
    project_name = metadata['project']
    project_folder = os.path.abspath(os.path.dirname(__file__))
    top_folder = os.path.join(project_folder, project_name)
    sass_files = {}
    css_files = {}
    for root, folders, files in os.walk(top_folder):
        common_path = '/'.join(root.split('/')[:-1])
        common_rel_path = common_path.replace(top_folder, '').lstrip('/')
        rel_path = root.replace(top_folder, '')
        project = common_rel_path.replace('/', '.')
        if not project.endswith('static'):
            continue
        project = '.'.join(project.split('.')[:-1])
        project = '.'.join((project_name, project)).rstrip('.')
        folders = [folder for folder in folders if 'static' in folder]
        for filename in files:
            data = ((project, common_rel_path))
            if filename.endswith('.sass'):
                sass_files.setdefault(data, {}).setdefault(rel_path, []).append(filename)
            elif filename.endswith('.css'):
                css_files.setdefault(data, {}).setdefault(rel_path, []).append(filename)

    sass_paths = {}
    for key in sass_files:
        name, endpoint = key
        if key in css_files:
            sass = [k.lstrip('/') for k in sass_files[key]][0]
            css = [k.lstrip('/') for k in css_files[key]][0]
            path = SassPath(sass, css, endpoint)
            sass_paths[name] = path

    return sass_paths


def get_console_scripts(metadata):
    '''Convenience function to wrap console scripts.

    Expects that all command-line scripts are found within the
    __main__.py file and that they are functions.

    Args:
        metadata(dict): project metadata

    Returns:
        list: scripts listed in format required by setup
    '''
    scripts = []
    project_name = metadata['project']
    project_folder = os.path.abspath(os.path.dirname(__file__))
    filepath = '{project_folder}/{project_name}/__main__.py'
    filepath = filepath.format(project_folder=project_folder, project_name=project_name)
    engine = re.compile(r"^def (?P<func>(.*?))\((?P<args>(.*?))\)\:$")
    template = '{script} = {project_name}.__main__:{func_name}'
    if os.path.exists(filepath):
        with open(filepath, 'r') as fd:
            for line in fd:
                for data in [m.groupdict() for m in engine.finditer(line)]:
                    func_name = data['func']
                    script = func_name.replace('_', '-')
                    scripts.append(template.format(script=script, project_name=project_name, func_name=func_name))
    return scripts


def main():
    '''Sets up the package'''
    metadata = get_package_metadata()
    package_requires = setup_project()
    requirements = get_package_requirements(package_requires=package_requires)
    project_name = metadata['project']
    classifiers = metadata.get('classifiers')
    extras = {k: v for k, v in requirements.items() if k != 'requirements'}
    year = metadata.get('copyright_years') or datetime.datetime.now().year
    lic = metadata.get('license') or 'Copyright {year} - all rights reserved'.format(year=year)
    sass_manifests = get_sass_manifests(metadata)
    # import pdb; pdb.set_trace()
    links = []
    if sys.platform.startswith('3'):
        links = [
            'git+git://github.com/tomassedovic/tornadio2.git@python3#tornadIO2-0.0.3'
        ]

    # Run setup
    setup(
        # Package metadata information
        name=project_name,
        version=metadata.get('versionstr') or 'unknown',
        description=metadata.get('shortdoc') or project_name,
        long_description=metadata.get('doc') or metadata.get('shortdoc') or project_name,
        url=metadata.get('url') or '',
        license=lic,
        author=metadata.get('author') or 'unknown',
        author_email=metadata.get('email') or 'unknown',

        # Package Properties
        packages=find_packages(),
        include_package_data=True,

        # Requirements
        setup_requires=requirements.get('setup') or [],
        install_requires=requirements['requirements'],
        extras_require=extras,
        dependency_links=links,
        tests_require=requirements.get('tests') or [],
        entry_points={
            'console_scripts': get_console_scripts(metadata),
        },
        platforms=['any'],
        classifiers=classifiers,
        zip_safe=False,

        # Extras
        sass_manifests=sass_manifests,
    )


if __name__ == '__main__':
    main()
