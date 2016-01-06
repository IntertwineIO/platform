#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Decodes data

Usage:
    data_process.py [options] <json_path>

Options:
    -h --help       This message
    -v --verbose    More information
    -q --quiet      Less information
'''
from __future__ import print_function

import json
import logging
from os import listdir
from os.path import isdir, isfile, join, abspath
import sys
from titlecase import titlecase

log = logging.getLogger('data_process')


class DataProcessException(Exception):
    '''Data Process exception'''

    def __init__(self, message=None, *args, **kwds):
        if message is not None:
            message = message.format(**kwds) if kwds else message
        else:
            message = self.__doc__.format(**kwds) if kwds else self.__doc__
        log.error(message)
        Exception.__init__(self, message)


class InvalidJSONPath(DataProcessException):
    '''No JSON files found in path {path}.'''


class MissingRequiredField(DataProcessException):
    '''Required field "{field}" on {classname!r} is missing.'''


class FieldCollision(DataProcessException):
    '''Field "{field}" on {entity!r} has already been set.'''


# TODO: implement check for this
class AsymmetricConnection(DataProcessException):
    '''{problem_a!r} defines {problem_b!r} as {connected_type_a}, but
    {problem_b!r} does not define {problem_a!r} as {not_connected_type_b}.'''


class InvalidConnectionType(DataProcessException):
    '''Connection type "{connection_type}" is not valid.'''


class CircularConnection(DataProcessException):
    '''"{problem!r}" cannot be connected to itself.'''


class RatingOutOfBounds(DataProcessException):
    '''Rating of {rating} is out of bounds on {connection!r}.'''


class ProblemConnectionRating(object):
    '''Base class for problem connection ratings

    Problem connection ratings are input by users and are scoped by
    geo, organization, AND problem context. It is perfectly valid
    for the same user to provide a different rating of A -> B from
    the context of problem A vs. problem B because the perceived
    importance of B as an impact of A may be quite different from
    the perceived importance of A as a driver of B.
    '''

    def __init__(self, rating, user_id, connection,
                 problem_scope, geo_scope=None, org_scope=None):
        if rating < 0 or rating > 4:
            raise RatingOutOfBounds(rating, connection)
        self.rating = rating
        # TODO: assign user based on user_id
        self.user = user_id
        self.connection = connection
        self.problem_scope = problem_scope
        # TODO: make geo and org entities rather than strings
        self.geo_scope = geo_scope
        self.org_scope = org_scope

    def __repr__(self):
        cname = self.__class__.__name__
        s = '<{cname}: {rating!r}\n'.format(cname=cname, rating=self.rating)
        s += '  user: {user!r}\n'.format(user=self.user)
        s += '  connection: {conn!r}\n'.format(conn=self.connection)
        s += '  problem_scope: {prob!r}\n'.format(prob=self.problem_scope)
        s += '  geo_scope: {geo!r}\n'.format(geo=self.geo_scope)
        s += '  org_scope: {org!r}\n'.format(org=self.org_scope)
        s += '>'
        return s

    def __str__(self):
        cname = self.__class__.__name__
        prob = self.problem_scope.name
        if prob == self.connection.problem_a:
            conn = str(self.connection).replace(prob, '*'+prob+'*', 1)
        else:
            conn = ('*'+prob+'*').join(str(self.connection).rsplit(prob, 1))
        rating = self.rating_data
        user = self.user
        org = self.org_scope
        geo = self.geo_scope
        s = '{cname}: {rating} by {user}\n'.format(cname=cname, rating=rating, user=user)
        s += '  on {conn}\n'.format(conn=conn)
        s += '  at {org} '.format(org=org) if org is not None else '  '
        # TODO: convert to more friendly geo
        s += 'in {geo}'.format(geo=geo) if geo is not None else '(globally)'
        return s


class ProblemConnection(object):
    '''Base class for problem connections

    There are four ways in which problems can be connected:

                               broader
                                  |
                    drivers -> problem -> impacts
                                  |
                               narrower

    Drivers/impacts are causal type connections while broader/narrower
    are scope type connections. In causal connections, the driver is
    always listed first, while in scope connections, the broader is
    always listed first. A problem connection is uniquely definied by
    its type, first problem, and second problem.
    '''

    # keeps track of all instances
    _registry = {}

    def __new__(cls, connection_type, problem_a, problem_b):
        '''Create a new problem connection if it doesn't already exist

        Checks if a problem connection already exists in the _registry.
        If it does, return it with new=False. If it doesn't, create it
        and return it with new=True. The "new" attribute is used by
        __init__ to distinguish between new vs. existing connections.
        '''
        # TODO: make connection_type an Enum
        if connection_type not in ('causal', 'scope'):
            raise InvalidConnectionType(connection_type)
        if problem_a == problem_b:
            raise CircularConnection(problem_a)

        key = (connection_type, problem_a, problem_b)
        problem_connection = ProblemConnection._registry.get(key, None)
        if problem_connection:
            problem_connection.new = False
            return problem_connection
        else:
            # TODO: ? instead of calling object's __new__, call parent's __new__
            problem_connection = object.__new__(cls, connection_type,
                                                problem_a, problem_b)
            problem_connection.new = True
            ProblemConnection._registry[key] = problem_connection
            return problem_connection

    def __init__(self, connection_type, problem_a, problem_b):
        if self.new:
            self.connection_type = connection_type
            self.problem_a = problem_a
            self.problem_b = problem_b
            self.ratings = []
        del self.new

    def __repr__(self):
        ct = '->' if self.connection_type == 'causal' else '::'
        return '<{cname}: ({conn_type}) {p_a!r} {ct} {p_b!r}>'.format(
            cname=self.__class__.__name__,
            conn_type=self.connection_type,
            p_a=self.problem_a.name, ct=ct, p_b=self.problem_b.name)

    def __str__(self):
        ct = '->' if self.connection_type == 'causal' else '::'
        return '{p_a} {ct} {p_b}'.format(
            p_a=self.problem_a.name,
            ct=ct,
            p_b=self.problem_b.name
        )


class Problem(object):
    '''Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by geo, organization, and problem context.
    '''
    # TODO: add db support

    # keeps track of all instances
    _registry = {}

    def __new__(cls, name, definition=None, definition_url=None, images=[],
                drivers=[], impacts=[], broader=[], narrower=[]):
        '''Create a new problem if it doesn't already exist

        Checks if a problem already exists with the given name in the
        _registry. If it does, return it with new=False. If it doesn't,
        create it and return it with new=True. The "new" attribute is
        used by __init__ to distinguish between new vs. existing
        problems.
        '''
        human_id = name.strip().lower().replace(' ', '_')
        problem = Problem._registry.get(human_id, None)
        if problem:
            problem.new = False
            return problem
        else:
            # TODO:? instead of calling object's __new__, call parent's __new__
            problem = object.__new__(cls, name, definition=None,
                                     definition_url=None, images=[])
            problem.human_id = human_id
            problem.new = True
            Problem._registry[human_id] = problem
            return problem

    def __init__(self, name, definition=None, definition_url=None, images=[],
                 drivers=[], impacts=[], broader=[], narrower=[]):
        '''Initialize a new problem or set fields on an existing problem

        Inputs are key-value pairs based on the JSON problem schema. If
        the problem is new, initialize the name and the other fields. If
        the problem already exists in the _registry, each field is set
        only if the corresponding input value is None or [] for lists. A
        FieldCollision exception is raised if the existing field and
        the input both have values (or len>0 for lists).
        '''

        if self.new:
            self.name = titlecase(name.strip())
            self.definition = definition
            self.definition_url = definition_url
            self.images = images
            self.drivers = []
            self.impacts = []
            self.broader = []
            self.narrower = []
        else:
            if definition:
                if not self.definition:
                    self.definition = definition
                else:
                    raise FieldCollision(field='definition', entity=self)
            if definition_url:
                if not self.definition_url:
                    self.definition_url = definition_url
                else:
                    raise FieldCollision(field='definition_url', entity=self)
            if len(images) > 0:
                if len(self.images) == 0:
                    self.images = images
                else:
                    raise FieldCollision('images', self)
        del self.new

        self.load_connections(connections_name='drivers', connections_data=drivers)
        self.load_connections(connections_name='impacts', connections_data=impacts)
        self.load_connections(connections_name='broader', connections_data=broader)
        self.load_connections(connections_name='narrower', connections_data=narrower)

    def load_connections(self, connections_name, connections_data):
        values = {
            'drivers': ('causal', 'adjacent_problem', 'self', 'impacts'),
            'impacts': ('causal', 'self', 'adjacent_problem', 'drivers'),
            'broader': ('scope', 'adjacent_problem', 'self', 'narrower'),
            'narrower': ('scope', 'self', 'adjacent_problem', 'broader'),
        }
        conn_type, p_a, p_b, inverse_type = values[connections_name]
        connections = getattr(self, connections_name)

        for connection_data in connections_data:
            adjacent_problem_name = connection_data.get('adjacent_problem', None)
            if adjacent_problem_name is None:
                raise MissingRequiredField(field='adjacent_problem_name',
                                           classname='Problem')
            adjacent_problem = Problem(name=adjacent_problem_name)
            connection = ProblemConnection(conn_type, locals()[p_a], locals()[p_b])
            if connection not in connections:
                connections.append(connection)
                getattr(adjacent_problem, inverse_type).append(connection)
            # Set the ratings, whether or not the connection is new
            ratings_data = connection_data.get('problem_connection_ratings', [])
            for rating_data in ratings_data:
                connection_rating = ProblemConnectionRating(
                    connection=connection,
                    problem_scope=self,
                    **rating_data
                )
                connection.ratings.append(connection_rating)

    def __repr__(self):
        cname = self.__class__.__name__
        return '<{cname}: {name!r}>'.format(cname=cname, name=self.name)

    def __str__(self):
        indent = ' '*4
        fields = dict(
            name=self.name,
            definition=self.definition,
            url=self.definition_url,
            images=self.images,
            drivers=[c.problem_a.name for c in self.drivers],
            impacts=[c.problem_b.name for c in self.impacts],
            broader=[c.problem_a.name for c in self.broader],
            narrower=[c.problem_b.name for c in self.narrower],
        )
        field_order = ['name', 'definition', 'url', 'images',
                       'drivers', 'impacts', 'broader', 'narrower']
        string = []
        for field in field_order:
            data = fields[field]
            if data is None:
                continue
            if isinstance(data, basestring) and not data.strip():
                continue
            if not data:
                continue
            if field == 'name':
                data_str = 'Problem: {' + field + '}'
            else:
                if isinstance(data, (list, type(iter(list())))):
                    data_str = '  {field}:\n'.format(field=field)
                    data = '\n'.join(indent+'{}'.format(v) for v in data)
                    fields[field] = data
                else:
                    data_str = '  {field}: '.format(field=field)
                data_str += '{' + field + '}'
            data_str = data_str.format(**fields)
            string.append(data_str)
        return '\n'.join(string)


def decode_problems(json_data):
    '''Returns problems created from the json_data

    Takes as input a list of json data loads, each from a separate JSON
    file and returns a dictionary of problems keyed by human_id's.
    '''

    problems = {}
    for json_data_load in json_data:
        for data_key, data_value in json_data_load.items():
            problem = Problem(name=data_key, **data_value)
            problems[problem.human_id] = problem
    # TODO: change this to only return problems that were loaded since
    # there may already be problems in the registry before loading more.
    # This is non-trivial because problems can be created based on the
    # connection references.
    return Problem._registry


def decode(json_path, *args, **options):
    '''Loads JSON files within a path and returns data structures

    Given a path to a JSON file or a directory containing JSON files,
    returns a dictionary of the objects loaded from the JSON file(s).
    Calls another function to actually decode the json_data. This
    other function's name begins with 'decode_' and ends with the
    innermost directory in the json_path: decode_<directory>(json_data)

    Usage:
    >>> json_path = '/data/problems/problems.json'
    >>> problems = decode(json_path)
    >>> p0 = problems['poverty']
    >>> p1 = problems['homelessness']
    >>> p2 = problems['domestic_violence']
    '''

    # Gather valid json_paths based on the given file or directory
    if isfile(json_path) and json_path.rsplit('.', 1)[-1].lower() == 'json':
        json_paths = [json_path]
    elif isdir(json_path):
        json_paths = [join(json_path, f) for f in listdir(json_path)
                      if (isfile(join(json_path, f)) and
                          f.rsplit('.', 1)[-1].lower() == 'json' and
                          'schema' not in f.lower()]
    if len(json_paths) == 0:
        raise InvalidJSONPath(path=json_path)

    # Load raw json_data from each of the json_paths
    json_data = []
    for path in json_paths:
        with open(path) as json_file:
            # TODO: May need to change this to load incrementally in the future
            json_data.append(json.load(json_file))

    # Determine the decode function based on directory name and then call it
    if isfile(json_path):
        dir_name = abspath(json_path).rsplit('/', 2)[-2]
    else:
        dir_name = abspath(json_path).rsplit('/', 1)[-1]
    function_name = 'decode_' + dir_name
    module = sys.modules[__name__]
    decode_function = getattr(module, function_name)
    return decode_function(json_data)


if __name__ == '__main__':
    from docopt import docopt

    def fix(option):
        option = option.lstrip('--')
        option = option.lstrip('<').rstrip('>')
        option = option.replace('-', '_')
        return option

    options = {fix(k): v for k, v in docopt(__doc__).items()}
    if options.get('verbose'):
        logging.basicConfig(level=logging.DEBUG)
    elif options.get('quiet'):
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    decode(**options)
