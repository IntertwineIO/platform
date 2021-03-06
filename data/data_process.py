#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decodes data

Usage:
    data_process.py [options] <json_path>

Options:
    -h --help       This message
    -v --verbose    More information
    -q --quiet      Less information
"""
import io
import json
import logging
import os
import os.path
import sys

from alchy.model import extend_declarative_base
from sqlalchemy import create_engine
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from config import DevConfig
from intertwine import IntertwineModel
from intertwine.trackable import Trackable
from intertwine.auth.models import BaseAuthModel
# from intertwine.communities.models import BaseCommunityModel
# from intertwine.geos.models import BaseGeoModel
from intertwine.problems.models import BaseProblemModel, Problem
from intertwine.problems.exceptions import InvalidJSONPath


class DataSessionManager:
    """
    Base class for managing data sessions

    Takes an optional database configuration string as input (default is
    DevConfig.DATABASE) and returns a session. In the process, the
    engine, tables, session factory, and session are created only if
    they do not already exist. The session returned is a scoped_session
    """
    engine = None
    session_factory = None
    session = None

    def __init__(self, db_config=DevConfig.DATABASE,
                 ModelBases=[BaseAuthModel,
                             # BaseCommunityModel, BaseGeoModel,
                             # BaseProblemModel,
                             IntertwineModel]):
        DSM = DataSessionManager
        if DSM.engine is None:
            DSM.engine = create_engine(db_config)
        # Create tables if they don't exist
        for ModelBase in ModelBases:
            ModelBase.metadata.create_all(DSM.engine)
        if DSM.session_factory is None:
            DSM.session_factory = sessionmaker(bind=DSM.engine)
        if DSM.session is None:
            DSM.session = scoped_session(DSM.session_factory)
        extend_declarative_base(IntertwineModel, session=DSM.session)


def decode_problems(json_data):
    """
    Return entities created from problem JSON data

    Takes as input a list of json data loads, each from a separate JSON
    file and returns a dictionary where the keys are classes and the
    values are corresponding sets of objects updated from the JSON
    file(s).

    Resets tracking of updates via the Trackable metaclass each time it
    is called.
    """
    Trackable.clear_updates()

    for json_data_load in json_data:
        for data_key, data_value in json_data_load.items():
            Problem(name=data_key, **data_value)

    return Trackable.catalog_updates()


def decode(session, json_path, *args, **options):
    """
    Load JSON files within a path and return data structures

    Given a path to a JSON file or a directory containing JSON files,
    returns a dictionary where the keys are classes and the values are
    corresponding sets of objects updated from the JSON file(s).

    Calls another function to actually decode the json_data. This
    other function's name begins with 'decode_' and ends with the last
    directory in the absolute json_path: decode_<dir_name>(json_data)

    Usage:
    >>> json_path = '/data/problems/problems00.json'  # load a JSON file
    >>> u0 = decode(json_path)  # get updates from data load
    >>> json_path = '/data/problems/'  # load all JSON files in a directory
    >>> u1 = decode(json_path)  # get updates from next data load
    >>> u1_problems = u1['Problem']  # get set of updated problems
    >>> u1_connections = u1['ProblemConnection']  # set of updated connections
    >>> u1_ratings = u1['ProblemConnectionRating']  # set of updated ratings
    >>> p0 = Problem('poverty')  # get existing 'Poverty' problem
    >>> p1 = Problem('homelessness')  # get existing 'Homelessness' problem
    >>> p2 = Problem['domestic_violence']  # Problem is subscriptable
    >>> for p in Problem:  # Problem is iterable
    ...    print(p)
    """
    # Gather valid json_paths based on the given file or directory
    json_paths = []
    if os.path.isfile(json_path):
        if (json_path.rsplit('.', 1)[-1].lower() == 'json' and
                'schema' not in os.path.basename(json_path).lower()):
            json_paths.append(json_path)
    elif os.path.isdir(json_path):
        json_paths = [os.path.join(json_path, f) for f in os.listdir(json_path)
                      if (os.path.isfile(os.path.join(json_path, f)) and
                          f.rsplit('.', 1)[-1].lower() == 'json' and
                          'schema' not in f.lower())]
    if len(json_paths) == 0:
        raise InvalidJSONPath(path=json_path)

    # Load raw json_data from each of the json_paths
    json_data = []
    for path in json_paths:
        with io.open(path) as json_file:
            # TODO: May need to change this to load incrementally in the future
            json_data.append(json.load(json_file))

    # Determine the decode function based on directory name and then call it
    if os.path.isfile(json_path):
        dir_name = os.path.abspath(json_path).rsplit('/', 2)[-2]
    else:
        dir_name = os.path.abspath(json_path).rsplit('/', 1)[-1]
    function_name = 'decode_' + dir_name
    module = sys.modules[__name__]
    decode_function = getattr(module, function_name)
    Trackable.register_existing(session)
    return decode_function(json_data)


def erase_data(session, confirm=None):
    """
    Erase all data from database and clear tracking of all instances

    For Trackable classes, erases all data from the database and clears
    tracking of all instances. Prompts the user to confirm by typing
    'ERASE'. Can alternatively take an optional confirm parameter with
    a value of 'ERASE' to proceed without a user prompt.
    """
    if confirm != 'ERASE':
        prompt = ('This will erase *all* data from the database and '
                  'clear tracking of all instances.\n'
                  'Type "ERASE" (all caps) to proceed. '
                  'Anything else will abort.\n>')
        confirm_again = raw_input(prompt)
        if confirm_again != 'ERASE':
            print('Aborting - leaving data untouched.')
            return

    print('Processing...')
    # limit data to Trackable classes with existing tables
    engine = session.bind
    inspector = Inspector.from_engine(engine)
    table_names = set(inspector.get_table_names())
    classes = [x for x in Trackable._classes.values()
               if x.__tablename__ in table_names]
    print('Erase Data classes: ', classes)
    Trackable.register_existing(session, *classes)
    for cls in classes:
        for inst in cls:
            session.delete(inst)
    session.commit()
    Trackable.clear_instances()
    print('Erase data has completed')


if __name__ == '__main__':
    from docopt import docopt

    def fix(option):
        option = option.lstrip('--')
        option = option.lstrip('<').rstrip('>')
        option = option.replace('-', '_')
        return option

    options = {fix(k): v for k, v in docopt(__doc__).items()}
    default_session = DataSessionManager().session
    options['session'] = default_session
    if options.get('verbose'):
        logging.basicConfig(level=logging.DEBUG)
    elif options.get('quiet'):
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    data = decode(**options)
    for updates in data.values():
        options['session'].add_all(updates)
    options['session'].commit()
