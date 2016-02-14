#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import (
    declarative_base,
    DeclarativeMeta,
    declared_attr,
)
from titlecase import titlecase
import urlnorm

from ..utils import camelCaseTo_snake_case
from . import problems_db as db
from .exceptions import (
    InvalidRegistryKey,
    InvalidEntity,
    InvalidProblemConnectionRating,
    InvalidUser,
    InvalidProblemScope,
    InvalidConnectionType,
    CircularConnection,
)


class Trackable(DeclarativeMeta):
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

    # keep track of all classes that are Trackable
    _classes = {}

    def __new__(meta, name, bases, attr):
        # track instances for each class of type Trackable
        attr['_instances'] = {}
        # track any new or modified instances
        attr['_updates'] = set()
        new_cls = super(Trackable, meta).__new__(meta, name, bases, attr)
        meta._classes[name] = new_cls
        return new_cls

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

    @classmethod
    def clear_updates(meta, *args):
        '''Clear updates tracked by Trackable classes

        If no arguments are provided, all Trackable classes will have
        updates cleared (i.e. reset). If one or more classes are passed
        as input, only these classes will have updates cleared. If a
        class is not Trackable, a TypeError is raised.
        '''
        if len(args) == 0:
            for cname, cls in meta._classes.items():
                cls._updates = set()
        else:
            for cls in args:
                if cls.__name__ not in meta._classes:
                    raise TypeError('{} not Trackable.'.format(cls.__name__))
                cls._updates = set()

    @classmethod
    def catalog_updates(meta, *args):
        '''Catalog updates tracked by Trackable classes

        Returns a dictionary keyed by class name, where the values are
        the corresponding sets of updated instances.

        If no arguments are provided, updates for all Trackable classes
        will be included. If one or more classes are passed as input,
        only updates from these classes will be included. If a class is
        not Trackable, a TypeError is raised.
        '''
        updates = {}
        if len(args) == 0:
            for cname, cls in meta._classes.items():
                updates[cname] = cls._updates
        else:
            for cls in args:
                if cls.__name__ not in meta._classes:
                    raise TypeError('{} not Trackable.'.format(cls.__name__))
                updates[cls.__name__] = cls._updates
        return updates


BaseProblemModel = declarative_base(metaclass=Trackable)


class AutoTableMixin(object):
    '''Automatically creates a table from class name'''

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        return camelCaseTo_snake_case(cls.__name__)


class Image(AutoTableMixin, BaseProblemModel):
    '''Base class for images'''

    url = db.Column(db.String(2048))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem = db.relationship('Problem', back_populates='images')

    # TODO: add following:
    #
    # attribution:
    # title         # title of the work
    # author        # name or username (on source site) who owns the material
    # org           # organization that owns the material
    # source        # same as url? consider renaming url as source?
    # license       # name of license; mapped to license_url
    #               # acceptable licenses on Intertwine:
    #               # NONE:      PUBLIC DOMAIN
    #               # CC BY:     ATTRIBUTION
    #               # CC BY-SA:  ATTRIBUTION-SHAREALIKE
    #               # CC BY-ND:  ATTRIBUTION-NODERIVS
    #               # foter.com/blog/how-to-attribute-creative-commons-photos/
    #
    # users:
    # authored_by   # user who is author
    # added_by      # user who added
    # modified_by   # users who modified
    #
    # image-specific:
    # caption       # additional text beyond title
    # date          # date original was made
    # location      # where the photo was captured, if applicable
    # file          # local copy of image
    # dimensions    # in pixels

    @staticmethod
    def create_key(url, *args, **kwds):
        '''Create key for an image

        Return a registry key allowing the Trackable metaclass to look
        up an image. The key is created from the given url
        parameter.
        '''
        return urlnorm.norm(url)

    def derive_key(self):
        '''Derive key from an image instance

        Return the registry key used by the Trackable metaclass from an
        image instance. The key is derived from the url field on the
        image instance.
        '''
        return self.url

    def __init__(self, url, problem):
        '''Initialize a new image from a url

        Inputs are key-value pairs based on the JSON problem schema.
        '''
        self.url = urlnorm.norm(url)
        self.problem = problem

    def __repr__(self):
        cname = self.__class__.__name__
        form_str = '<{cname}: ({problem!r}) {url!r}>'
        return form_str.format(cname=cname, problem=self.problem, url=self.url)

    def __str__(self):
        return '{url}'.format(url=self.url)


class ProblemConnectionRating(AutoTableMixin, BaseProblemModel):
    '''Base class for problem connection ratings

    Problem connection ratings are input by users and are scoped by
    geo, organization, AND problem context. It is perfectly valid
    for the same user to provide a different rating of A -> B from
    the context of problem A vs. problem B because the perceived
    importance of B as an impact of A may be quite different from
    the perceived importance of A as a driver of B.
    '''

    rating = db.Column(db.Integer)
    # TODO: make user_id a foreign key
    user_id = db.Column(db.String(60))
    connection_id = db.Column(db.Integer, db.ForeignKey('problem_connection.id'))
    problem_scope_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    # TODO: make geo_scope_id a foreign key
    geo_scope_id = db.Column(db.String(256))
    # TODO: make org_scope_id a foreign key
    org_scope_id = db.Column(db.String(256))
    connection = db.relationship('ProblemConnection', back_populates='ratings')
    problem_scope = db.relationship('Problem')
    __table_args__ = (db.UniqueConstraint('user_id',
                                          'connection_id',
                                          'problem_scope_id',
                                          'geo_scope_id',
                                          'org_scope_id'),)

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


class ProblemConnection(AutoTableMixin, BaseProblemModel):
    '''Base class for problem connections

    A problem connection is uniquely defined by its connection_type
    ('causal' or 'scoped') and the two problems it connects: problem_a
    and problem_b.

    In causal connections, problem_a drives problem_b, so problem_a is
    the 'driving_problem' and problem_b is the 'impacted_problem' in the
    database relationships. (Of course, this means from the perspective
    of the driving_problem, the given connection is in the 'impacts'
    field.)

    In scoped connections, problem_a is broader than problem_b, so
    problem_a is the 'broader_problem' and problem_b is the
    'narrower_problem' in the database relationships. (Again, this means
    from the perspective of the broader_problem, the given connection is
    in the 'narrower' field.)

                  'causal'                          'scoped'

                                                    problem_a
        problem_a    ->    problem_b            (broader_problem)
    (driving_problem)  (impacted_problem)              ::
                                                    problem_b
                                                (narrower_problem)

    '''

    connection_type = db.Column(db.String(6))
    problem_a_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem_b_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    ratings = db.relationship('ProblemConnectionRating',
                              back_populates='connection',
                              lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('problem_a_id',
                                          'problem_b_id',
                                          'connection_type'),)

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


class Problem(AutoTableMixin, BaseProblemModel):
    '''Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by geo, organization, and problem context.

    Problem instances are Trackable (metaclass), where the registry
    keys are the problem names in lowercase with underscores instead of
    spaces.

    Problems can connect to other problems in four ways:

                               broader
                                  ::
                    drivers -> problem -> impacts
                                  ::
                               narrower

    Drivers/impacts are 'causal' connections while broader/narrower are
    'scoped' connections.
    '''
    name = db.Column(db.String(60), index=True, unique=True)
    definition = db.Column(db.String(200))
    definition_url = db.Column(db.String(2048))
    images = db.relationship('Image', back_populates='problem', lazy='dynamic')

    drivers = db.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_b_id, "
                            "ProblemConnection.connection_type=='causal')",
                # backref='problem_b',
                backref='impacted_problem',
                lazy='dynamic')
    impacts = db.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_a_id, "
                            "ProblemConnection.connection_type=='causal')",
                # backref='problem_a',
                backref='driving_problem',
                lazy='dynamic')
    broader = db.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_b_id, "
                            "ProblemConnection.connection_type=='scoped')",
                # backref='problem_b',
                backref='narrower_problem',
                lazy='dynamic')
    narrower = db.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_a_id, "
                            "ProblemConnection.connection_type=='scoped')",
                # backref='problem_a',
                backref='broader_problem',
                lazy='dynamic')

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
        self.images = []
        self.drivers = []
        self.impacts = []
        self.broader = []
        self.narrower = []

        for image_url in images:
            image = Image(url=image_url, problem=self)
            if image not in self.images:
                self.images.append(image)

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
                image_urls = v if v else []
                for image_url in image_urls:
                    image = Image(url=image_url, problem=self)
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
            definition_url=self.definition_url,
            images=[i.url for i in self.images],
            drivers=[c.problem_a.name for c in self.drivers],
            impacts=[c.problem_b.name for c in self.impacts],
            broader=[c.problem_a.name for c in self.broader],
            narrower=[c.problem_b.name for c in self.narrower],
        )
        field_order = ['name', 'definition', 'definition_url', 'images',
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
