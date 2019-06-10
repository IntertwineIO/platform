#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loads user data into python

Usage:
    load ([-v]... | [-q]...) [options] [<path>]

Options:
    -v --verbose          More messages
    -q --quiet            Fewer messages
    -x --exclude PATTERN  Exclude files from being processed
"""
from fnmatch import fnmatch as fn
import os

import json
import yaml

from intertwine import create_app
from intertwine.config import DevConfig
from intertwine.auth import auth_db
from intertwine.auth.models import User, Role

app = create_app(config=DevConfig)


def read_data(path, exclude=None):
    """
    Reads a file or folder and return the python object based on the
    files found.  Exclude pattern can remove a set of files from
    processing.
    """
    data = {}
    if os.path.exists(path):
        if os.path.isdir(path):
            for root, folders, files in os.walk(path):
                for filename in files:
                    valid_ext = ('yaml', 'json')
                    if not filename.endswith(valid_ext):
                        continue
                    filepath = os.path.join(root, filename)
                    if exclude is not None:
                        if fn(filepath, exclude):
                            continue
                    new_data = load(filepath)
                    if isinstance(new_data, dict):
                        data.update(new_data)
        else:
            with open(path, 'r') as fd:
                file_data = fd.read()
            if path.endswith('yaml'):
                data.update(yaml.load(file_data))
            elif path.endswith('json'):
                data.update(json.loads(file_data))
    else:
        raise ValueError('Could not open: {}'.format(path))
    return data


def load(path, exclude=None):
    data = read_data(path, exclude=None)
    # Create user data within database
    users = {}
    for user_data in data.get('users', {}):
        user = User(**user_data)
        users[user_data['username']] = user
    roles = {}
    for role_data in data.get('roles', {}):
        role = Role(**role_data)
        roles[role_data['name']] = role
    session = auth_db.session()


if __name__ == '__main__':
    import logging
    from docopt import docopt

    def fix(o):
        o = o.lstrip('-')
        o = o.lstrip('<').rstrip('>')
        o = o.replace('-', '_')
        return o

    options = {fix(k): v for k, v in docopt(__doc__).items()}

    # Handle verbosity settings
    verbosity = options.pop('verbose')
    quietness = options.pop('quiet')
    if verbosity:
        if verbosity > 2:
            logging.basicConfig(level=logging.NOTSET)
        elif verbosity > 1:
            logging.basicConfig(level=logging.DEBUG)
        elif verbosity > 0:
            logging.basicConfig(level=logging.INFO)
    elif quietness:
        if quietness > 1:
            logging.basicConfig(level=logging.CRITICAL)
        elif quietness > 0:
            logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.WARNING)
    path = options['path']
    options['path'] = os.path.abspath(path) if path else os.path.abspath(os.getcwd())
    load(**options)
