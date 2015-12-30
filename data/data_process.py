#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Decodes data

Usage:
    process [options] <json_data_path>

Options:
    -h --help       This message
    -v --verbose    More information
    -q --quiet      Less information
'''
from __future__ import print_function

import json
import logging
import os


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


class MissingRequiredField(DataProcessException):
    '''Required field "{field!s}" on {classname!r} is missing.'''


class FieldCollision(DataProcessException):
    '''Field "{field!s}" on {entity!r} has already been set.'''


class AsymmetricConnection(DataProcessException):
    '''{problem_a!r} defines {problem_b!r} as {connected_type_a!s},
    but {problem_b!r} does not define {problem_a!r} as {not_connected_type_b!s}.
    '''


class InvalidConnectionType(DataProcessException):
    '''Connection type "{connection_type!s}" is not valid.'''


class CircularConnection(DataProcessException):
    '''"{problem!r}" cannot be connected to itself.'''


class ProblemConnectionRating(object):
    '''Base class for problem connection ratings

    Problem connection ratings are input by users and are scoped by
    geo, organization, AND problem context. It is perfectly valid
    for the same user to provide a different rating of A -> B from
    the context of problem A vs. problem B because the perceived
    importance of B as an impact of A may be quite different from
    the perceived importance of A as a driver of B.'''


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
    its type, first problem, and second problem.'''

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
            # TODO?: instead of calling object's __new__, call parent's __new__
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

        del self.new

    def __repr__(self):
        cname = self.__class__.__name__
        return '<{!s}: {!s} {!r}-{!r}>'.format(cname, self.connection_type,
                                               self.problem_a, self.problem_b)

    def __str__(self):
        if self.connection_type == 'causal':
            s = '<{!s} -> {!s}>'.format(self.problem_a.name, self.problem_b.name)
        elif self.connection_type == 'scope':
            indent = ' ' * (len(self.problem_a.name)/2 + 1)
            s = '<{!s}\n{!s}|\n{!s}>'.format(self.problem_a.name, indent, self.problem_b.name)
        return s


class Problem(object):
    '''Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by geo, organization, and problem context.'''
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
        key = name.title()
        problem = Problem._registry.get(key, None)
        if problem:
            problem.new = False
            return problem
        else:
            # TODO?: instead of calling object's __new__, call parent's __new__
            problem = object.__new__(cls, name, definition=None, definition_url=None, images=[])
            problem.new = True
            Problem._registry[key] = problem
            return problem

    def __init__(self, name, definition=None, definition_url=None, images=[],
                 drivers=[], impacts=[], broader=[], narrower=[]):
        '''Initialize a new problem or set fields on an existing problem

        Inputs are key-value pairs based on the JSON problem schema. If
        the problem is new, initialize the name and the other fields. If
        the problem already exists in the _registry, each field is set
        only if the corresponding input value is None or [] for lists. A
        FieldCollision exception is raised if the existing field and
        the input both have values (or len>0 for lists).'''

        if self.new:
            self.name = name.title()
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

        for problem_connection_data in drivers:
            adjacent_problem_name = problem_connection_data.get('adjacent_problem', None)
            if adjacent_problem_name == None:
                raise MissingRequiredField(field='adjacent_problem_name', classname='Problem')
            adjacent_problem_name = adjacent_problem_name.title()
            adjacent_problem = Problem(name=adjacent_problem_name)
            problem_connection = ProblemConnection('causal', adjacent_problem, self)
            if problem_connection not in self.drivers:
                self.drivers.append(problem_connection)
                adjacent_problem.impacts.append(problem_connection)
            # TODO: add problem connection ratings

        for problem_connection_data in impacts:
            adjacent_problem_name = problem_connection_data.get('adjacent_problem', None)
            if adjacent_problem_name == None:
                raise MissingRequiredField(field='adjacent_problem_name', classname='Problem')
            adjacent_problem_name = adjacent_problem_name.title()
            adjacent_problem = Problem(name=adjacent_problem_name)
            problem_connection = ProblemConnection('causal', self, adjacent_problem)
            if problem_connection not in self.impacts:
                self.impacts.append(problem_connection)
                adjacent_problem.drivers.append(problem_connection)
            # TODO: add problem connection ratings

        # TODO: add broader connections
        # TODO: add narrower connections

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
            drivers=[d.problem_a.name for d in self.drivers],
            impacts=[d.problem_b.name for d in self.impacts],
            broader=[d.problem_a.name for d in self.broader],
            narrower='\n'.join(indent+'{}'.format(d.problem_b.name) for d in self.narrower),
        )
        field_order = ['name', 'definition', 'url', 'images', 'drivers', 'impacts', 'broader', 'narrower']
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
            try:
                data_str = data_str.format(**fields)
                string.append(data_str)
            except KeyError:
                print(data_str)
                print(fields)
                import pdb; pdb.set_trace()
        return '\n'.join(string)


def decode_problems(problem_name, problem_data):
    pass


def decode(json_data_path, *args, **options):
    '''Loads JSON files within a path and returns data structures

    Returns a dictionary in which the keys are plural forms of the
    objects defined by the JSON problem schema, and the values are
    dictionaries containing each object type.

    Usage:
    >>> json_path = '/data/problems/problems.json'
    >>> data = decode(json_path)
    >>> problems = data['problems']
    >>> p = problems['Homelessness']
    >>> connections = data['connections']
    '''

    # TODO: ability to read in all json files in a directory
    if os.path.isdir(json_data_path):
        raise TypeError('"{}" is a folder and must be file'.format(json_data_path))
    with open(json_data_path) as json_file:
        # May need to change this to load incrementally in the future
        data = json.load(json_file)

    # TODO: determine object type to be decoded, based on directory name
    entities = {
        'problems': {},
        'connections': {}
    }

    for problem_name, problem_data in data.items():
        problem_name = problem_name.title()
        problem = Problem(name=problem_name, **problem_data)

    entities['problems'] = Problem._registry
    entities['connections'] = ProblemConnection._registry
    return entities


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
