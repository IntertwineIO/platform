#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple
import re
from numbers import Real

from alchy.model import ModelBase, make_declarative_base
from past.builtins import basestring
from sqlalchemy import orm, types, Column, ForeignKey, Index, UniqueConstraint

from titlecase import titlecase
import urlnorm

from ..utils import AutoTableMixin, Trackable


from .exceptions import (
    InconsistentArguments,
    InvalidEntity,
    InvalidConnectionType,
    CircularConnection,
    InvalidProblemConnectionRating,
    InvalidAggregateConnectionRating,
    InvalidAggregation,
    InvalidUser,
    InvalidProblemForConnection,
)


BaseProblemModel = make_declarative_base(Base=ModelBase, Meta=Trackable)


class Image(BaseProblemModel, AutoTableMixin):
    '''Base class for images'''

    # TODO: make Image work with any entity (not just problems), where
    # each image can be attached to multiple entities
    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    problem = orm.relationship('Problem', back_populates='images')
    url = Column(types.String(2048))

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
    # ratings       # common Base for ContentRating & ProblemConnectionRating?
    #
    # image-specific:
    # caption       # additional text beyond title
    # date          # date original was made
    # location      # where the photo was captured, if applicable
    # file          # local copy of image
    # dimensions    # in pixels

    Key = namedtuple('Key', 'problem, url')

    @classmethod
    def create_key(cls, problem, url, **kwds):
        '''Create key for an image

        Return a registry key allowing the Trackable metaclass to look
        up an image. The key is created from the given problem and url.
        '''
        return cls.Key(problem, urlnorm.norm(url))

    def derive_key(self):
        '''Derive key from an image instance

        Return the registry key used by the Trackable metaclass from an
        image instance. The key is derived from the problem and url
        fields.
        '''
        return type(self).Key(self.problem, self.url)

    def __init__(self, url, problem):
        '''Initialize a new image from a url

        Inputs are key-value pairs based on the JSON problem schema.
        '''
        self.url = urlnorm.norm(url)
        self.problem = problem

    # Use default __repr__() from Trackable:
    # Image[(Problem[<human_id>], <url>)]
    # or if over 79 chars:
    # Image[(
    #     Problem[<human_id>],
    #     <url>
    # )]

    def __str__(self):
        return '{url}'.format(url=self.url)


class AggregateProblemConnectionRating(BaseProblemModel, AutoTableMixin):
    '''Base class for aggregate problem connection ratings

    Rating aggregations are used to display connections on the problem
    network and this class enables caching so they do not need to be
    recalculated on each request. Ratings are aggregated across users
    within a community context of problem, org, and geo.

    An 'aggregation' parameter allows for different aggregation
    algorithms. The default implementation is 'strict' in that only
    ratings with matching problem, org scope, and geo scope are
    included. Other implementations may include:
        - 'inclusive' to include all ratings within sub-orgs/geos
        - 'inherited' to point to a different context for ratings

    Currently, aggregations are only created when the problem network is
    first rendered within a given problem/org/geo context. The
    cumulative weight across all the ratings aggregated is also stored,
    allowing the aggregate rating to be updated without having to
    recalculate the aggregation across all the included ratings.
    '''
    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    problem = orm.relationship('Problem')

    connection_id = Column(types.Integer, ForeignKey('problem_connection.id'))
    connection = orm.relationship('ProblemConnection',
                                  back_populates='aggregate_ratings')

    # TODO: rename org_scope to org_scope_id, make it a foreign key, and
    #       create an org_scope relationship
    org_scope = Column(types.String(256))

    # TODO: rename geo_scope to geo_scope_id, make it a foreign key, and
    #       create a geo_scope relationship
    geo_scope = Column(types.String(256))

    aggregation = Column(types.String(16))
    rating = Column(types.Float)
    weight = Column(types.Float)

    Key = namedtuple('Key', 'problem, connection, org_scope, geo_scope, '
                            'aggregation')

    __table_args__ = (Index('ux_aggregate_problem_connection_rating',
                            # ux for unique index
                            'problem_id',
                            'connection_id',
                            'org_scope',
                            'geo_scope',
                            'aggregation',
                            unique=True),)

    @classmethod
    def create_key(cls, problem, connection, org_scope=None, geo_scope=None,
                   aggregation='strict', **kwds):
        '''Create key for an aggregate rating

        Return a registry key allowing the Trackable metaclass to look
        up an aggregate problem connection rating instance.
        '''
        return cls.Key(problem, connection, org_scope, geo_scope, aggregation)

    def derive_key(self):
        '''Derive key from an aggregate rating instance

        Return the registry key used by the Trackable metaclass from an
        aggregate problem connection rating instance. The key is derived
        from the problem, connection, org_scope, and geo_scope fields.
        '''
        return type(self).Key(self.problem, self.connection, self.org_scope,
                              self.geo_scope, self.aggregation)

    def __init__(self, problem, connection, org_scope=None, geo_scope=None,
                 aggregation='strict', rating=None, weight=None):
        '''Initialize a new aggregate rating

        Inputs connection and problem are instances while org_scope,
        geo_scope, aggregation, rating, and weight are literals based on
        the JSON aggregate problem connection rating schema.

        The rating must be a real number between 0 and 4 inclusive. The
        weight reflects the total weight of all the ratings included and
        must also be a real number. Rating and weight must both be
        provided or both be None.

        If both rating and weight are None, The value and weight are
        calculated from the set of problem connection ratings using the
        method specified in the aggregation argument.

        The default aggregation is 'strict', which only includes those
        ratings which exactly match the problem, org_scope, and
        geo_scope. However, note that org_scope of None includes all
        orgs and geo_scope of None includes all geos.
        '''
        if not isinstance(connection, ProblemConnection):
            raise InvalidEntity(variable='connection', value=connection,
                                classname='ProblemConnection')
        is_causal = connection.connection_type == 'causal'
        p_a = connection.driver if is_causal else connection.broader
        p_b = connection.impact if is_causal else connection.narrower
        if problem not in (p_a, p_b):
            raise InvalidProblemForConnection(problem=problem,
                                              connection=connection)
        # TODO: add 'inclusive' to include all ratings within sub-orgs/geos
        # TODO: add 'inherited' to point to a different context for ratings
        if aggregation not in ('strict'):
            raise InvalidAggregation(aggregation=aggregation)
        if ((rating is None and weight is not None) or
                (rating is not None and weight is None)):
            raise InconsistentArguments(arg1_name='rating', arg1_value=rating,
                                        art2_name='weight', arg2_value=weight)
        if rating is None:
            if aggregation == 'strict':
                rq = ProblemConnectionRating.query.filter_by(
                                                        problem=problem,
                                                        connection=connection)
                rq = rq.filter_by(org_scope=org_scope) if org_scope else rq
                rq = rq.filter_by(geo_scope=geo_scope) if geo_scope else rq
                ratings = rq.all()
                # ratings = (r for r in connection.ratings.all() if
                #            r.problem == problem and
                #            (org_scope is None or r.org_scope == org_scope) and
                #            (geo_scope is None or r.geo_scope == geo_scope))
                weighted_rating_total = weight_total = 0
                r_user_expertise = 1  # Placeholder - see below
                for r in ratings:
                    weighted_rating_total += r.rating * r_user_expertise
                    # Sub w/ r.user.expertise(problem, org_scope, geo_scope)
                    weight_total += r_user_expertise
                rating = (weighted_rating_total * 1.0 / weight_total if
                          weight_total > 0 else 0)
                weight = weight_total
        if (not isinstance(rating, Real) or rating < 0 or rating > 4):
            raise InvalidAggregateConnectionRating(rating=rating,
                                                   connection=connection)
        if not isinstance(weight, Real):
            raise TypeError('Weight must be a Real number.')
        self.problem = problem
        self.connection = connection
        # TODO: make org and geo entities rather than strings
        self.org_scope = org_scope
        self.geo_scope = geo_scope
        self.aggregation = aggregation
        self.rating = rating
        self.weight = weight

    def modify(self, **kwds):
        '''Modify an existing aggregate rating

        Modify the rating and/or weight if new values are provided and
        flag the aggregate problem connection rating as modified.
        Required by the Trackable metaclass.
        '''
        rating = kwds.get('rating', None)
        if (not isinstance(rating, Real) or
                rating < 0 or rating > 4):
            raise InvalidAggregateConnectionRating(rating=rating,
                                                   connection=self.connection)
        weight = kwds.get('weight', None)
        if not isinstance(weight, Real):
            raise TypeError('Argument weight must be a Real number.')
        if rating != self.rating or weight != self.weight:
            self.rating = rating
            self.weight = weight
            self._modified.add(self)

    # Use default __repr__() from Trackable:
    # AggregateProblemConnectionRating[(
    #     Problem[<human_id>],
    #     ProblemConnection[(
    #         <conn_type>,
    #         Problem[<human_id>],
    #         Problem[<human_id>]
    #     )],
    #     <org>,
    #     Geo[<human_id>],
    #     <aggregation>
    # )]

    def __str__(self):
        cls_name = self.__class__.__name__
        p_name = self.problem.name
        conn = self.connection
        is_causal = conn.connection_type == 'causal'
        p_a = conn.driver.name if is_causal else conn.broader.name
        if p_name == p_a:
            conn_str = str(conn).replace(p_name, '@' + p_name, 1)
        else:
            conn_str = ('@' + p_name).join(str(conn).rsplit(p_name, 1))
        org = self.org_scope
        geo = self.geo_scope
        s = '{cls}: {rating:.2f} with {weight:.2f} weight ({agg})\n'.format(
                                                        cls=cls_name,
                                                        rating=self.rating,
                                                        weight=self.weight,
                                                        agg=self.aggregation)
        s += '  on {conn}\n'.format(conn=conn_str)
        s += '  at {org} '.format(org=org) if org is not None else '  '
        # TODO: convert to more friendly geo
        s += 'in {geo}'.format(geo=geo) if geo is not None else '(globally)'
        return s


class ProblemConnectionRating(BaseProblemModel, AutoTableMixin):
    '''Base class for problem connection ratings

    Problem connection ratings are input by users within the context of
    a problem, org, and geo. For example, it is perfectly valid for the
    same user to provide a different rating of A -> B from the context
    of problem A vs. problem B because the perceived importance of B as
    an impact of A may be quite different from the perceived importance
    of A as a driver of B.
    '''

    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    problem = orm.relationship('Problem')

    connection_id = Column(types.Integer, ForeignKey('problem_connection.id'))
    connection = orm.relationship('ProblemConnection',
                                  back_populates='ratings')

    # TODO: rename org_scope to org_scope_id, make it a foreign key, and
    #       create an org_scope relationship
    org_scope = Column(types.String(256))

    # TODO: rename geo_scope to geo_scope_id, make it a foreign key, and
    #       create a geo_scope relationship
    geo_scope = Column(types.String(256))

    # TODO: rename user to user_id, make it a foreign key, and create a
    #       user relationship
    user = Column(types.String(60))

    _rating = Column('rating', types.Integer)

    Key = namedtuple('Key', 'problem, connection, org_scope, geo_scope, user')

    # Querying use cases:
    #
    # 1. The Problem Page needs weighted average ratings on each connection
    #    to order them and modulate how they are displayed. This may end
    #    up being pre-processed, but it must be queried when calculated.
    #    cols: problem_id, connection_id, org_scope, geo_scope
    #       where most commonly org_scope == None
    #    cols: problem_id, connection_id, org_scope
    #    cols: problem_id, connection_id
    #    cols: problem_id (if faster to query all together)
    #
    # 2. The Problem Page needs to ask the user to rate connections that
    #    the user has not yet rated).
    #    cols: user, problem_id
    #
    # 3. The Personal Dashboard needs to track history of all the user's
    #    inputs including connection ratings.
    #    cols: user
    #
    # __table_args__ = (UniqueConstraint('problem_id',
    #                                    'connection_id',
    #                                    'org_scope',
    #                                    'geo_scope',
    #                                    'user',
    #                                    name='uq_problem_connection_rating'),)
    #
    __table_args__ = (Index('ux_problem_connection_rating',
                            # ux for unique index
                            'problem_id',
                            'connection_id',
                            'org_scope',
                            'geo_scope',
                            'user',
                            unique=True),
                      Index('ix_problem_connection_rating:user+problem_id',
                            # ix for index
                            'user',
                            'problem_id'),)

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, val):
        if not isinstance(val, int) or val < 0 or val > 4:
            raise InvalidProblemConnectionRating(rating=val,
                                                 connection=self.connection)
        old_val = self.rating if hasattr(self, '_rating') else None
        if (val != old_val):
            # Update aggregate ratings affected by this rating
            self._rating = val
            self.update_aggregate_ratings(new_rating=val, old_rating=old_val)

    rating = orm.synonym('_rating', descriptor=rating)

    @classmethod
    def create_key(cls, problem, connection, org_scope=None,
                   geo_scope=None, user='Intertwine', **kwds):
        '''Create key for a problem connection rating

        Return a registry key allowing the Trackable metaclass to look
        up a problem connection rating instance.
        '''
        return cls.Key(problem, connection, org_scope, geo_scope, user)

    def derive_key(self):
        '''Derive key from a problem connection rating instance

        Return the registry key used by the Trackable metaclass from a
        problem connection rating instance. The key is derived from the
        problem, connection, org_scope, geo_scope, and user fields.
        '''
        return type(self).Key(self.problem, self.connection, self.org_scope,
                              self.geo_scope, self.user)

    def __init__(self, rating, problem, connection, org_scope=None,
                 geo_scope=None, user_id='Intertwine'):
        '''Initialize a new problem connection rating

        Inputs problem and connection are instances while the rest
        are literals based on the JSON problem connection rating schema.
        The rating parameter must be an integer between 0 and 4
        inclusive.'''
        if not isinstance(connection, ProblemConnection):
            raise InvalidEntity(variable='connection', value=connection,
                                classname='ProblemConnection')
        is_causal = connection.connection_type == 'causal'
        p_a = connection.driver if is_causal else connection.broader
        p_b = connection.impact if is_causal else connection.narrower
        if problem not in (p_a, p_b):
            raise InvalidProblemForConnection(problem=problem,
                                              connection=connection)
        if user_id is None or user_id == '':
            raise InvalidUser(user=user_id, connection=connection)
        self.problem = problem
        self.connection = connection
        # TODO: make org and geo entities rather than strings
        self.org_scope = org_scope
        self.geo_scope = geo_scope
        # TODO: assign user based on user_id
        self.user = user_id
        self.rating = rating

    def modify(self, **kwds):
        '''Modify an existing problem connection rating

        Modify the rating field if a new value is provided and flag the
        problem connection rating as modified. Required by the Trackable
        metaclass.
        '''
        rating = kwds.get('rating', None)
        if rating != self.rating:
            self.rating = rating
            self._modified.add(self)

    def update_aggregate_ratings(self, new_rating, old_rating=None):
        # Update strict aggregate ratings
        ars = [ar for ar in self.connection.aggregate_ratings.all() if
               ar.problem == self.problem and
               (ar.org_scope is None or ar.org_scope == self.org_scope) and
               (ar.geo_scope is None or ar.geo_scope == self.geo_scope) and
               ar.aggregation == 'strict']
        if ars:
            # user.expertise(self.problem, self.org_scope, self.geo_scope)
            user_w = user_expertise = 1
            deduction = (old_rating * user_w) if old_rating else 0
            addition = new_rating * user_w
            for ar in ars:
                new_w = ar.weight + (user_w if old_rating is None else 0)
                new_r = ((ar.rating*ar.weight - deduction + addition) / new_w)
                AggregateProblemConnectionRating(problem=ar.problem,
                                                 connection=ar.connection,
                                                 org_scope=ar.org_scope,
                                                 geo_scope=ar.geo_scope,
                                                 aggregation='strict',
                                                 rating=new_r,
                                                 weight=new_w)

    # Use default __repr__() from Trackable:
    # ProblemConnectionRating[(
    #     Problem[<human_id>],
    #     ProblemConnection[(
    #         <conn_type>,
    #         Problem[<human_id>],
    #         Problem[<human_id>])
    #     )],
    #     <org>,
    #     Geo[<human_id>],
    #     <user>
    # )]

    def __str__(self):
        cls_name = self.__class__.__name__
        p_name = self.problem.name
        conn = self.connection
        is_causal = conn.connection_type == 'causal'
        p_a = conn.driver.name if is_causal else conn.broader.name
        if p_name == p_a:
            conn_str = str(conn).replace(p_name, '@' + p_name, 1)
        else:
            conn_str = ('@' + p_name).join(str(conn).rsplit(p_name, 1))
        rating = self.rating
        user = self.user
        org = self.org_scope
        geo = self.geo_scope
        s = '{cls}: {rating} by {user}\n'.format(cls=cls_name,
                                                 rating=rating,
                                                 user=user)
        s += '  on {conn}\n'.format(conn=conn_str)
        s += '  at {org} '.format(org=org) if org is not None else '  '
        # TODO: convert to more friendly geo
        s += 'in {geo}'.format(geo=geo) if geo is not None else '(globally)'
        return s


class ProblemConnection(BaseProblemModel, AutoTableMixin):
    '''Base class for problem connections

    A problem connection is uniquely defined by its connection_type
    ('causal' or 'scoped') and the two problems it connects: problem_a
    and problem_b.

    In causal connections, problem_a drives problem_b, so problem_a is
    the 'driver' and problem_b is the 'impact' in the database
    relationships. (Of course, this means from the perspective
    of the driver, the given connection is in the 'impacts' field.)

    In scoped connections, problem_a is broader than problem_b, so
    problem_a is 'broader' and problem_b is 'narrower' in the database
    relationships. (Again, this means from the perspective of the
    broader problem, the given connection is in the 'narrower' field.)

                  'causal'                          'scoped'

                                                    problem_a
        problem_a    ->    problem_b               ('broader')
        ('driver')         ('impact')                  ::
                                                    problem_b
                                                   ('narrower')
    '''

    connection_type = Column(types.String(6))
    problem_a_id = Column(types.Integer, ForeignKey('problem.id'))
    problem_b_id = Column(types.Integer, ForeignKey('problem.id'))
    ratings = orm.relationship('ProblemConnectionRating',
                               back_populates='connection',
                               lazy='dynamic')
    aggregate_ratings = orm.relationship('AggregateProblemConnectionRating',
                                         back_populates='connection',
                                         lazy='dynamic')

    Key = namedtuple('Key', 'connection_type, problem_a, problem_b')

    __table_args__ = (UniqueConstraint('problem_a_id',
                                       'problem_b_id',
                                       'connection_type',
                                       name='uq_problem_connection'),)

    # TODO: Add index for (connection_type, problem_a_id)
    # TODO: Add index for (connection_type, problem_b_id)

    @classmethod
    def create_key(cls, connection_type, problem_a, problem_b, **kwds):
        '''Create key for a problem connection

        Return a registry key allowing the Trackable metaclass to look
        up a problem connection instance.
        '''
        return cls.Key(connection_type, problem_a, problem_b)

    def derive_key(self):
        '''Derive key from a problem connection instance

        Return the registry key used by the Trackable metaclass from a
        problem connection instance. The key is derived from the
        connection_type, problem_a, and problem_b fields on the problem
        connection instance.
        '''
        is_causal = self.connection_type == 'causal'
        p_a = self.driver if is_causal else self.broader
        p_b = self.impact if is_causal else self.narrower
        return type(self).Key(self.connection_type, p_a, p_b)

    def __init__(self, connection_type, problem_a, problem_b,
                 ratings_data=None, ratings_context_problem=None):
        '''Initialize a new problem connection

        Required inputs include connection_type, a string with value
        'causal' or 'scoped' and two problem instances. A connection_type
        of 'causal' means problem_a is a driver of problem_b, while a
        connection_type of 'scoped' means problem_a is broader than
        problem_b.

        The optional ratings_data parameter is a list of ratings based
        on the JSON problem connection rating schema. The problem
        parameter must be provided if ratings_data is specified, as it
        is required to define a problem connection rating.
        '''
        # TODO: make connection_type an Enum
        if connection_type not in ('causal', 'scoped'):
            raise InvalidConnectionType(connection_type=connection_type)
        if problem_a is problem_b:
            raise CircularConnection(problem=problem_a)
        self.connection_type = connection_type
        is_causal = self.connection_type == 'causal'
        self.driver = problem_a if is_causal else None
        self.impact = problem_b if is_causal else None
        self.broader = problem_a if not is_causal else None
        self.narrower = problem_b if not is_causal else None
        self.ratings = []
        self.aggregate_ratings = []

        if ratings_data and ratings_context_problem:
            self.load_ratings(ratings_data, ratings_context_problem)

    def modify(self, **kwds):
        '''Modify an existing problem connection

        Append any new problem connection ratings to the ratings field
        if problem and ratings_data are specified. If a rating is
        added, flag the connection as modified (via load_ratings). No
        other fields may be modified. Required by the Trackable
        metaclass.
        '''
        ratings_data = kwds.get('ratings_data', None)
        ratings_context_problem = kwds.get('ratings_context_problem', None)
        if ratings_data and ratings_context_problem:
            self.load_ratings(ratings_data, ratings_context_problem)

    def load_ratings(self, ratings_data, ratings_context_problem):
        '''Load a problem connection's ratings

        For each rating in the ratings_data, if the rating does not
        already exist, create it, else update it. Newly created ratings
        are appended to the 'ratings' field of the problem connection.
        If a rating is added, flag the connection as modified.
        '''
        rating_added = False
        for rating_data in ratings_data:
            connection_rating = ProblemConnectionRating(
                problem=ratings_context_problem,
                connection=self,
                **rating_data)
            if connection_rating not in self.ratings:
                self.ratings.append(connection_rating)
                rating_added = True
        if rating_added and hasattr(self, '_modified'):
            self._modified.add(self)

    def aggregate_rating_in_context(self, problem, org_scope=None,
                                    geo_scope=None, aggregation='strict',
                                    session=None):
        '''Emit aggregate rating for the connection within a context

        Given a problem, org_scope, geo_scope, aggregation, and a
        session, return an aggregate problem connection rating. If an
        aggregate rating matching the criteria already exists, it is
        returned. If not, a new one is created and persisted to the
        database.
        '''
        aggregate_ratings = [ar for ar in self.aggregate_ratings.all() if
                             ar.problem == problem and
                             ar.org_scope == org_scope and
                             ar.geo_scope == geo_scope and
                             ar.aggregation == aggregation]
        assert(len(aggregate_ratings) < 2)
        if len(aggregate_ratings) == 1:
            aggregate_rating = aggregate_ratings[0]
        else:
            aggregate_rating = AggregateProblemConnectionRating(
                                                problem=problem,
                                                connection=self,
                                                org_scope=org_scope,
                                                geo_scope=geo_scope,
                                                aggregation=aggregation)
            if session is not None:
                session.add(aggregate_rating)
                session.commit()
        return aggregate_rating

    # Use default __repr__() from Trackable:
    # ProblemConnection[(<conn_type>, Problem[<human_id>], Problem[<human_id>])]
    # or if over 79 chars:
    # ProblemConnection[(
    #     <conn_type>,
    #     Problem[<human_id>],
    #     Problem[<human_id>]
    # )]

    def __str__(self):
        is_causal = self.connection_type == 'causal'
        ct = '->' if is_causal else '::'
        p_a = self.driver.name if is_causal else self.broader.name
        p_b = self.impact.name if is_causal else self.narrower.name
        return '{p_a} {ct} {p_b}'.format(p_a=p_a, ct=ct, p_b=p_b)


class Problem(BaseProblemModel, AutoTableMixin):
    '''Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by organization, geo, and problem context.

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
    _name = Column('name', types.String(60), index=True, unique=True)
    _human_id = Column('human_id', types.String(60), index=True, unique=True)
    definition = Column(types.String(200))
    definition_url = Column(types.String(2048))
    # TODO: support multiple sponsors in different org/geo contexts
    sponsor = Column(types.String(60))
    images = orm.relationship(
                'Image',
                back_populates='problem',
                lazy='dynamic')
    drivers = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_b_id, "
                            "ProblemConnection.connection_type=='causal')",
                backref='impact',
                lazy='dynamic')
    impacts = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_a_id, "
                            "ProblemConnection.connection_type=='causal')",
                backref='driver',
                lazy='dynamic')
    broader = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_b_id, "
                            "ProblemConnection.connection_type=='scoped')",
                backref='narrower',
                lazy='dynamic')
    narrower = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_a_id, "
                            "ProblemConnection.connection_type=='scoped')",
                backref='broader',
                lazy='dynamic')

    # URL Guidance: perishablepress.com/stop-using-unsafe-characters-in-urls
    # Exclude unsafe:            "<>#%{}|\^~[]`
    # Exclude reserved:          ;/?:@=&
    # Potentially include:       !*_
    # Include safe plus space:   $-.+'(), a-zA-Z0-9
    name_pattern = re.compile(r'''^[$-.+'(), a-zA-Z0-9]+$''')

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        name = titlecase(val.strip())
        if Problem.name_pattern.match(name) is None:  # check for valid name
            raise NameError("'{}' is not a valid problem name.".format(name))
        self.human_id = Problem.create_key(name)  # set the human_id
        self._name = name  # set the name last

    name = orm.synonym('_name', descriptor=name)

    @property
    def human_id(self):
        return self._human_id

    @human_id.setter
    def human_id(self, val):
        # check if it's already registered by a different problem
        problem = Problem._instances.get(val, None)
        if problem is not None and problem is not self:
            raise NameError("'{}' is already registered.".format(val))
        if hasattr(self, '_human_id'):  # unregister old human_id
            # Default None since Trackable registers after Problem.__init__()
            Problem._instances.pop(self.human_id, None)
        Problem[val] = self  # register the new human_id
        self._human_id = val  # set the new human_id last

    human_id = orm.synonym('_human_id', descriptor=human_id)

    @staticmethod
    def create_key(name, **kwds):
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
        return self.human_id

    def __init__(self, name, definition=None, definition_url=None,
                 sponsor=None, images=[],
                 drivers=[], impacts=[], broader=[], narrower=[]):
        '''Initialize a new problem

        Inputs are key-value pairs based on the JSON problem schema.
        '''
        self.name = name
        self.definition = definition.strip() if definition else None
        self.definition_url = definition_url.strip() if definition_url else None
        self.sponsor = sponsor.strip() if sponsor else None
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
        problem_connection_data = {'drivers': drivers, 'impacts': impacts,
                                   'broader': broader, 'narrower': narrower}
        for k, v in problem_connection_data.items():
            self.load_connections(category=k, data=v)

    def modify(self, **kwds):
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
                definition = v.strip() if v else None
                if definition != self.definition:
                    self.definition = definition
                    self._modified.add(self)
            elif k == 'definition_url':
                definition_url = v.strip() if v else None
                if definition_url != self.definition_url:
                    self.definition_url = definition_url
                    self._modified.add(self)
            elif k == 'sponsor':
                sponsor = v.strip() if v else None
                if sponsor != self.sponsor:
                    self.sponsor = sponsor
                    self._modified.add(self)
            elif k == 'images':
                image_urls = v if v else []
                for image_url in image_urls:
                    image = Image(url=image_url, problem=self)
                    if image not in self.images:
                        self.images.append(image)
                        self._modified.add(self)
            elif k in ['drivers', 'impacts', 'broader', 'narrower']:
                self.load_connections(category=k, data=v)
            else:
                raise NameError('{} not found.'.format(k))

    def load_connections(self, category, data):
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
        assert category in derived_vars
        conn_type, p_a, p_b, inverse_name = derived_vars[category]
        connections = getattr(self, category)

        for connection_data in data:
            adjacent_name = connection_data.get('adjacent_problem', None)
            adjacent_problem = Problem(name=adjacent_name)
            ratings_data = connection_data.get('problem_connection_ratings', [])
            connection = ProblemConnection(
                connection_type=conn_type,
                problem_a=locals()[p_a],
                problem_b=locals()[p_b],
                ratings_data=ratings_data,
                ratings_context_problem=self)
            if connection not in connections:
                connections.append(connection)
                getattr(adjacent_problem, inverse_name).append(connection)
                self._modified.add(adjacent_problem)

        if len(self._modified) > 0:
            self._modified.add(self)

    def connections_with_ratings(self, org_scope=None, geo_scope=None,
                                 aggregation='strict', session=None):
        '''Pair connections with ratings and sort by connection category
        '''
        connections_with_ratings = {}
        for category in ['drivers', 'impacts', 'broader', 'narrower']:
            connections_with_ratings[category] = [
                    (c, c.aggregate_rating_in_context(problem=self,
                                                      org_scope=org_scope,
                                                      geo_scope=geo_scope,
                                                      aggregation=aggregation,
                                                      session=session).rating)
                    for c in getattr(self, category).all()]
            connections_with_ratings[category].sort(key=lambda c: c[1],
                                                    reverse=True)
        return connections_with_ratings

    # Use default __repr__() from Trackable:
    # Problem[<human_id>]

    def __str__(self):
        indent = ' ' * 4
        fields = dict(
            name=self.name,
            human_id=self.human_id,
            definition=self.definition,
            definition_url=self.definition_url,
            images=[i.url for i in self.images],
            drivers=[c.driver.name for c in self.drivers],
            impacts=[c.impact.name for c in self.impacts],
            broader=[c.broader.name for c in self.broader],
            narrower=[c.narrower.name for c in self.narrower],
        )
        field_order = ['name', 'human_id', 'definition', 'definition_url',
                       'images', 'drivers', 'impacts', 'broader', 'narrower']
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
