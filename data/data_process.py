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
import os
import os.path
import six
import sys
from titlecase import titlecase

log = logging.getLogger('data_process')


class DataProcessException(Exception):
    '''Data Process exception'''

    # TODO: make this work with *args
    def __init__(self, message=None, *args, **kwds):
        if message is not None:
            message = message.format(**kwds) if kwds else message
        else:
            normalized_doc = ' '.join(self.__doc__.split())
            message = normalized_doc.format(**kwds) if kwds else normalized_doc
        log.error(message)
        Exception.__init__(self, message)


class InvalidJSONPath(DataProcessException):
    '''No JSON files found in path {path}.'''


class MissingRequiredField(DataProcessException):
    '''Required field '{field}' on {classname!r} is missing.'''


class InvalidConnectionType(DataProcessException):
    '''Connection type '{connection_type}' is not valid. Must be
    'causal' or 'scoped'.'''


class CircularConnection(DataProcessException):
    '''{problem!r} cannot be connected to itself.'''


class InvalidRegistryKey(DataProcessException):
    '''{key!r} is not a valid registry key for class {classname}'''


class InvalidEntity(DataProcessException):
    ''''{variable}' value of {value!r} is not a valid {classname}.'''


class InvalidProblemConnectionRating(DataProcessException):
    '''Rating of {rating} on {connection!r} is not valid. Must be an int
    between 0 and 4 (inclusive).'''


class InvalidUser(DataProcessException):
    '''User {user!r} on rating of {connection!r} is not a valid.'''


class InvalidProblemScope(DataProcessException):
    '''{problem_scope!r} must be a problem on one end of {connection!r}.'''


class Trackable(type):
    '''Metaclass providing ability to track instances

    Each class of type Trackable maintains a registry of instances and
    only creates a new instance if it does not already exist. Existing
    instances can be updated with new data if a 'modify' method has been
    defined.

    The registry key for an instance can either be explicitly provided
    by passing it in the 'key' parameter or constructed using the
    'create_key' method on the class (if 'key' is None).

    Any updates that result from the creation or modification
    of the instance can also be tracked. New instance creations are tracked
    automatically. Modifications of instances must be tracked using the
    '_modified' field on the instance, which is the set of instances of
    the same type that were modified.

    A class of type Trackable is subscriptable (indexed by key) and
    iterable.
    '''

    def __new__(meta, name, bases, attr):
        # track instances for each class of type Trackable
        attr['_instances'] = {}
        # track any new or modified instances
        attr['_updates'] = set()
        return super(Trackable, meta).__new__(meta, name, bases, attr)

    def __call__(cls, key=None, *args, **kwds):
        if key is None:
            key = cls.create_key(*args, **kwds)
            if key is None or key == '':
                raise InvalidRegistryKey(key=key, classname=cls.__name__)
        inst = cls._instances.get(key, None)
        if inst is None:
            inst = super(Trackable, cls).__call__(*args, **kwds)
            cls._instances[key] = inst
            cls._updates.add(inst)
        else:
            if hasattr(cls, 'modify') and (args or kwds):
                inst._modified = set()
                cls.modify(inst, *args, **kwds)
        if hasattr(inst, '_modified'):
            cls._updates.update(inst._modified)
            del inst._modified
        return inst

    def __getitem__(cls, key):
        return cls._instances[key]

    def __setitem__(cls, key, value):
        cls._instances[key] = value

    def __iter__(cls):
        for inst in cls._instances:
            yield inst


@six.add_metaclass(Trackable)
class ProblemConnectionRating(object):
    '''Base class for problem connection ratings

    Problem connection ratings are input by users and are scoped by
    geo, organization, AND problem context. It is perfectly valid
    for the same user to provide a different rating of A -> B from
    the context of problem A vs. problem B because the perceived
    importance of B as an impact of A may be quite different from
    the perceived importance of A as a driver of B.
    '''

    @staticmethod
    def create_key(user_id, connection, problem_scope,
                   geo_scope=None, org_scope=None, *args, **kwds):
        '''Create key for a problem connection rating

        Return a registry key allowing the Trackable metaclass to look
        up a problem connection rating instance. The key is created from
        the explicit parameters.
        '''
        return (user_id, connection, problem_scope, geo_scope, org_scope)

    def derive_key(self):
        '''Derive key from a problem connection rating instance

        Return the registry key used by the Trackable metaclass from a
        problem connection rating instance. The key is derived from the
        user, connection, problem_scope, geo_scope, and org_scope
        fields.
        '''
        return (self.user, self.connection, self.problem_scope,
                self.geo_scope, self.org_scope)

    def __init__(self, rating, user_id, connection,
                 problem_scope, geo_scope=None, org_scope=None):
        '''Initialize a new problem connection rating

        Inputs connection and problem_scope are instances while the rest
        are literals based on the JSON problem connection rating schema.
        The rating parameter must be an integer between 0 and 4
        inclusive.'''
        if not isinstance(connection, ProblemConnection):
            raise InvalidEntity(variable='connection', value=connection,
                                classname='ProblemConnection')
        if not isinstance(rating, int) or rating < 0 or rating > 4:
            raise InvalidProblemConnectionRating(rating=rating,
                                                 connection=connection)
        if user_id is None or user_id == '':
            raise InvalidUser(user=user_id, connection=connection)
        if problem_scope not in (connection.problem_a, connection.problem_b):
            raise InvalidProblemScope(problem_scope=problem_scope,
                                      connection=connection)
        self.rating = rating
        # TODO: assign user based on user_id
        self.user = user_id
        self.connection = connection
        self.problem_scope = problem_scope
        # TODO: make geo and org entities rather than strings
        self.geo_scope = geo_scope
        self.org_scope = org_scope

    def modify(self, *args, **kwds):
        '''Modify an existing problem connection rating

        Modify the rating field if a new value is provided flag the
        problem connection rating as modified. Required by the Trackable
        metaclass.
        '''
        rating = kwds.get('rating', None)
        if not isinstance(rating, int) or rating < 0 or rating > 4:
            raise InvalidProblemConnectionRating(rating=rating,
                                                 connection=self.connection)
        if rating != self.rating:
            self.rating = rating
            self._modified.add(self)

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
        if prob == self.connection.problem_a.name:
            conn = str(self.connection).replace(prob, '@' + prob, 1)
        else:
            conn = ('@' + prob).join(str(self.connection).rsplit(prob, 1))
        rating = self.rating
        user = self.user
        org = self.org_scope
        geo = self.geo_scope
        s = '{cname}: {rating} by {user}\n'.format(cname=cname,
                                                   rating=rating,
                                                   user=user)
        s += '  on {conn}\n'.format(conn=conn)
        s += '  at {org} '.format(org=org) if org is not None else '  '
        # TODO: convert to more friendly geo
        s += 'in {geo}'.format(geo=geo) if geo is not None else '(globally)'
        return s


@six.add_metaclass(Trackable)
class ProblemConnection(object):
    '''Base class for problem connections

    There are four ways in which problems can be connected:

                               broader
                                  |
                    drivers -> problem -> impacts
                                  |
                               narrower

    Drivers/impacts are 'causal' connections while broader/narrower are
    'scoped' connections.

    A problem connection is uniquely defined by its connection_type
    ('causal' or 'scoped') and the two problems it connects: problem_a
    and problem_b. In causal connections, problem_a drives problem_b,
    while in scoped connections, problem_a is broader than problem_b.
    '''

    @staticmethod
    def create_key(connection_type, problem_a, problem_b, *args, **kwds):
        '''Create key for a problem connection

        Return a registry key allowing the Trackable metaclass to look
        up a problem connection instance. The key is created from
        the explicit parameters.
        '''
        return (connection_type, problem_a, problem_b)

    def derive_key(self):
        '''Derive key from a problem connection instance

        Return the registry key used by the Trackable metaclass from a
        problem connection instance. The key is derived from the
        connection_type, problem_a, and problem_b fields on the problem
        connection instance.
        '''
        return (self.connection_type, self.problem_a, self.problem_b)

    def __init__(self, connection_type, problem_a, problem_b,
                 ratings_data=None, problem_scope=None):
        '''Initialize a new problem connection

        Required inputs include connection_type, a string with value
        'causal' or 'scoped' and two problem instances. A connection_type
        of 'causal' means problem_a is a driver of problem_b, while a
        connection_type of 'scoped' means problem_a is broader than
        problem_b.

        The optional ratings_data parameter is a list of ratings based
        on the JSON problem connection rating schema. The problem_scope
        parameter must be provided if ratings_data is specified, as it
        is required to define a problem connection rating.
        '''
        # TODO: make connection_type an Enum
        if connection_type not in ('causal', 'scoped'):
            raise InvalidConnectionType(connection_type=connection_type)
        if problem_a is problem_b:
            raise CircularConnection(problem=problem_a)
        self.connection_type = connection_type
        self.problem_a = problem_a
        self.problem_b = problem_b
        self.ratings = []

        if ratings_data and problem_scope:
            self.load_ratings(ratings_data, problem_scope)

    def modify(self, *args, **kwds):
        '''Modify an existing problem connection

        Append any new problem connection ratings to the ratings field
        if ratings_data and problem_scope are specified. If a rating is
        added, flag the connection as modified (via load_ratings). No
        other fields may be modified. Required by the Trackable
        metaclass.
        '''
        ratings_data = kwds.get('ratings_data', None)
        problem_scope = kwds.get('problem_scope', None)
        if ratings_data and problem_scope:
            self.load_ratings(ratings_data, problem_scope)

    def load_ratings(self, ratings_data, problem_scope):
        '''Load a problem connection's ratings

        For each rating in the ratings_data, if the rating does not
        already exist, create it, else update it. Newly created ratings
        are appended to the 'ratings' field of the problem connection.
        If a rating is added, flag the connection as modified.
        '''
        rating_added = False
        for rating_data in ratings_data:
            connection_rating = ProblemConnectionRating(
                connection=self,
                problem_scope=problem_scope,
                **rating_data)
            if connection_rating not in self.ratings:
                self.ratings.append(connection_rating)
                rating_added = True
        if rating_added and hasattr(self, '_modified'):
            self._modified.add(self)

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
            p_b=self.problem_b.name)


@six.add_metaclass(Trackable)
class Problem(object):
    '''Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by geo, organization, and problem context.

    Problem instances are Trackable (metaclass), where the registry
    keys are the problem names in lowercase with underscores instead of
    spaces.
    '''
    # TODO: add db support

    @staticmethod
    def create_key(name, *args, **kwds):
        '''Create key for a problem

        Return a registry key allowing the Trackable metaclass to look
        up a problem instance. The key is created from the given name
        parameter.
        '''
        return name.strip().lower().replace(' ', '_')

    def derive_key(self):
        '''Derive key from a problem instance

        Return the registry key used by the Trackable metaclass from a
        problem instance. The key is derived from the name field on the
        problem instance.
        '''
        return self.name.strip().lower().replace(' ', '_')

    def __init__(self, name, definition=None, definition_url=None, images=[],
                 drivers=[], impacts=[], broader=[], narrower=[]):
        '''Initialize a new problem

        Inputs are key-value pairs based on the JSON problem schema.
        '''
        self.name = titlecase(name.strip())
        self.definition = definition.strip() if definition else None
        self.definition_url = definition_url.strip() if definition_url else None
        self.images = images if images else []
        self.drivers = []
        self.impacts = []
        self.broader = []
        self.narrower = []

        # track problems modified by the creation of this problem via
        # new connections to existing problems
        self._modified = set()
        problem_connections_data = {'drivers': drivers, 'impacts': impacts,
                                    'broader': broader, 'narrower': narrower}
        for k, v in problem_connections_data.items():
            self.load_connections(connections_name=k, connections_data=v)

    def modify(self, *args, **kwds):
        '''Modify an existing problem

        Inputs are key-value pairs based on the JSON problem schema.
        Modify the definition and definition_url if new values differ
        from existing values. Append any new images and problem
        connections (the latter within drivers, impacts, broader, and
        narrower). Track all problems modified, whether directly or
        indirectly through new connections.

        New problem connections and ratings are added while existing
        ones are updated (via load_connections). Required by the
        Trackable metaclass.
        '''
        for k, v in kwds.items():
            if k == 'name':
                continue  # name cannot be updated via upload
            elif k == 'definition':
                definition = v.strip()
                if definition != self.definition:
                    self.definition = definition
                    self._modified.add(self)
            elif k == 'definition_url':
                definition_url = v.strip()
                if definition_url != self.definition_url:
                    self.definition_url = definition_url
                    self._modified.add(self)
            elif k == 'images':
                images = v if v else []
                for image in images:
                    if image not in self.images:
                        self.images.append(image)
                        self._modified.add(self)
            elif k in ['drivers', 'impacts', 'broader', 'narrower']:
                self.load_connections(connections_name=k, connections_data=v)
            else:
                raise NameError('{} not found.'.format(k))

    def load_connections(self, connections_name, connections_data):
        '''Load a problem's drivers, impacts, broader, or narrower

        The connections_name is the field name for a set of connections
        on a problem, either 'drivers', 'imapcts', 'broader', or
        'narrower'. The connections_data is the corresponding JSON data.
        The method loads the data and flags the set of problems
        modified in the process (including those that are also new).
        '''
        derived_vars = {
            'drivers': ('causal', 'adjacent_problem', 'self', 'impacts'),
            'impacts': ('causal', 'self', 'adjacent_problem', 'drivers'),
            'broader': ('scoped', 'adjacent_problem', 'self', 'narrower'),
            'narrower': ('scoped', 'self', 'adjacent_problem', 'broader'),
        }
        assert connections_name in derived_vars
        conn_type, p_a, p_b, inverse_type = derived_vars[connections_name]
        connections = getattr(self, connections_name)

        for connection_data in connections_data:
            adjacent_name = connection_data.get('adjacent_problem', None)
            adjacent_problem = Problem(name=adjacent_name)
            ratings_data = connection_data.get('problem_connection_ratings', [])
            connection = ProblemConnection(
                connection_type=conn_type,
                problem_a=locals()[p_a],
                problem_b=locals()[p_b],
                ratings_data=ratings_data,
                problem_scope=self)
            if connection not in connections:
                connections.append(connection)
                getattr(adjacent_problem, inverse_type).append(connection)
                self._modified.add(adjacent_problem)

        if len(self._modified) > 0:
            self._modified.add(self)

    def __repr__(self):
        cname = self.__class__.__name__
        return '<{cname}: {name!r}>'.format(cname=cname, name=self.name)

    def __str__(self):
        indent = ' ' * 4
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
                    data = '\n'.join(indent + '{}'.format(v) for v in data)
                    fields[field] = data
                else:
                    data_str = '  {field}: '.format(field=field)
                data_str += '{' + field + '}'
            data_str = data_str.format(**fields)
            string.append(data_str)
        return '\n'.join(string)


def decode_problems(json_data):
    '''Returns entities created from problem json_data

    Takes as input a list of json data loads, each from a separate JSON
    file and returns a dictionary where the keys are classes and the
    values are corresponding sets of objects updated from the JSON
    file(s).

    Resets the tracking of updates via the Trackable metaclass for
    problems, connections, and ratings each time it is called.
    '''
    Problem._updates = set()
    ProblemConnection._updates = set()
    ProblemConnectionRating._updates = set()

    for json_data_load in json_data:
        for data_key, data_value in json_data_load.items():
            Problem(name=data_key, **data_value)

    updates = {
        'Problem': Problem._updates,
        'ProblemConnection': ProblemConnection._updates,
        'ProblemConnectionRating': ProblemConnectionRating._updates,
    }
    return updates


def decode(json_path, *args, **options):
    '''Loads JSON files within a path and returns data structures

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
    >>> for k in Problem:  # Problem is iterable
    ...    print(Problem[k])
    '''
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
        with open(path) as json_file:
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
