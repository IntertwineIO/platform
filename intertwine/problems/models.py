# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from collections import namedtuple, OrderedDict
from numbers import Real
from operator import attrgetter

from past.builtins import basestring
from sqlalchemy import Column, ForeignKey, Index, or_, orm, types
from titlecase import titlecase

from .. import IntertwineModel
from ..geos.models import Geo
from ..third_party import urlnorm
from .exceptions import (
    CircularConnection,
    InconsistentArguments,
    InvalidAggregateConnectionRating,
    InvalidAggregation,
    InvalidConnectionAxis,
    InvalidEntity,
    InvalidProblemConnectionRating,
    InvalidProblemConnectionWeight,
    InvalidProblemForConnection,
    InvalidUser,
)

BaseProblemModel = IntertwineModel


class Image(BaseProblemModel):
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

    Key = namedtuple('ImageKey', 'problem, url')

    @classmethod
    def create_key(cls, problem, url, **kwds):
        '''Create key for an image

        Return a key allowing the Trackable metaclass to register an
        image. The key is a namedtuple of problem and url.
        '''
        return cls.Key(problem, urlnorm.norm(url))

    def derive_key(self):
        '''Derive key from an image instance

        Return the registry key used by the Trackable metaclass from an
        image instance. The key is a namedtuple of problem and url.
        '''
        return self.__class__.Key(self.problem, self.url)

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


class AggregateProblemConnectionRating(BaseProblemModel):
    '''Base class for aggregate problem connection ratings

    Rating aggregations are used to display connections on the problem
    network and this class enables caching so they do not need to be
    recalculated on each request. Ratings are aggregated across users
    within a community context of problem, org, and geo.

    Currently, aggregations are only created when the problem network is
    first rendered within a given community. The cumulative weight
    across all the ratings aggregated is also stored, allowing the
    aggregate rating to be updated without having to recalculate the
    aggregation across all the included ratings.

    Args:
        community: Community context for the aggregate rating
        connection: Connection being rated
        aggregation='strict': String specifying the aggregation method:
            - 'strict': include only ratings in the associated community
            - 'inclusive': include all ratings within sub-orgs/geos
            - 'inherited': include ratings from a different community
        rating=None: Real number between 0 and 4 inclusive; rating and
            weight must both be defined or both be None
        weight=None: Real number greater than or equal to 0 that
            reflects the cumulative weight of all aggregated ratings
        ratings=None: Iterable of ProblemConnectionRating specifying the
            set of ratings to be aggregated. Ratings and rating/weight
            cannot both be specified.
    '''
    community_id = Column(types.Integer, ForeignKey('community.id'))
    community = orm.relationship('Community',
                                 back_populates='aggregate_ratings')

    connection_id = Column(types.Integer, ForeignKey('problem_connection.id'))
    connection = orm.relationship('ProblemConnection',
                                  back_populates='aggregate_ratings')

    connection_category = Column(types.String(16))
    aggregation = Column(types.String(16))
    rating = Column(types.Float)
    weight = Column(types.Float)

    __table_args__ = (
        Index('ux_aggregate_problem_connection_rating',
              # ux for unique index
              'community_id',
              'aggregation',
              'connection_id',
              unique=True),
        Index('ix_aggregate_problem_connection_rating:by_category',
              # ix for index
              'community_id',
              'aggregation',
              'connection_category'),)

    NO_RATING = -1
    NO_WEIGHT = 0

    Key = namedtuple('AggregateProblemConnectionRatingKey',
                     'community, connection, aggregation')

    @classmethod
    def create_key(cls, community, connection, aggregation='strict', **kwds):
        '''Create key for an aggregate rating

        Return a key allowing the Trackable metaclass to register an
        aggregate problem connection rating instance. The key is a
        namedtuple of community, connection, and aggregation.
        '''
        return cls.Key(community, connection, aggregation)

    def derive_key(self):
        '''Derive key from an aggregate rating instance

        Return the registry key used by the Trackable metaclass from an
        aggregate problem connection rating instance. The key is a
        namedtuple of community, connection, and aggregation fields.
        '''
        return self.__class__.Key(self.community, self.connection, self.aggregation)

    @classmethod
    def calculate_values(cls, ratings):
        '''Calculate values

        Given an iterable of ratings, returns a tuple consisting of the
        aggregate rating and the aggregate weight. If ratings is empty,
        the aggregate rating defaults to -1 and the aggregate weight
        defaults to 0.
        '''
        weighted_rating_total = aggregate_weight = cls.NO_WEIGHT
        for r in ratings:
            weighted_rating_total += r.rating * r.weight
            # Sub w/ r.user.expertise(problem, org, geo)
            aggregate_weight += r.weight

        aggregate_rating = ((weighted_rating_total * 1.0 / aggregate_weight)
                            if aggregate_weight > 0 else cls.NO_RATING)

        return (aggregate_rating, aggregate_weight)

    def update_values(self, new_user_rating, new_user_weight,
                      old_user_rating=None, old_user_weight=None):
        '''Update values'''

        old_user_rating = 0 if old_user_rating is None else old_user_rating
        old_user_weight = 0 if old_user_weight is None else old_user_weight

        increase = new_user_rating * new_user_weight
        decrease = old_user_rating * old_user_weight

        new_aggregate_weight = (
            self.weight + new_user_weight - old_user_weight)
        new_aggregate_rating = (
            (self.rating * self.weight + increase - decrease) * 1.0 /
            new_aggregate_weight)

        self.rating, self.weight = new_aggregate_rating, new_aggregate_weight

    def __init__(self, community, connection, aggregation='strict',
                 rating=None, weight=None, ratings=None):
        problem, org, geo = community.derive_key()
        is_causal = connection.axis == 'causal'
        p_a = connection.driver if is_causal else connection.broader
        p_b = connection.impact if is_causal else connection.narrower
        if problem not in (p_a, p_b):
            raise InvalidProblemForConnection(problem=problem,
                                              connection=connection)
        if is_causal:
            self.connection_category = ('drivers' if problem is p_b
                                        else 'impacts')
        else:
            self.connection_category = ('broader' if problem is p_b
                                        else 'narrower')

        # TODO: add 'inclusive' to include all ratings within sub-orgs/geos
        # TODO: add 'inherited' to point to a different context for ratings
        if aggregation not in ('strict'):
            raise InvalidAggregation(aggregation=aggregation)
        if ((rating is None and weight is not None) or
                (rating is not None and weight is None)):
            raise InconsistentArguments(arg1_name='rating', arg1_value=rating,
                                        art2_name='weight', arg2_value=weight)
        if (ratings is not None and rating is not None):
            ratings_str = '<{type} of length {length}>'.format(
                                type=type(ratings), length=len(list(ratings)))
            raise InconsistentArguments(
                                arg1_name='ratings', arg1_value=ratings_str,
                                art2_name='rating', arg2_value=rating)

        if ratings:
            rating, weight = (
                AggregateProblemConnectionRating.calculate_values(ratings))

        elif rating is None:
            if aggregation == 'strict':
                rq = ProblemConnectionRating.query.filter_by(
                        problem=problem, org=org, geo=geo,
                        connection=connection)
                # TODO: implement inclusive aggregation
                # Removed since it is not strict:
                # rq = rq.filter_by(org=org) if org else rq
                # rq = rq.filter_by(geo=geo) if geo else rq
                # ratings = rq.all()
                rating, weight = (
                    AggregateProblemConnectionRating.calculate_values(rq))

        for field, value in (('Rating', rating), ('Weight', weight)):
            if not isinstance(value, Real):
                raise TypeError(
                    '{field} value of {value} is not a Real number.'
                    .format(field=field, value=value))

        if not ((rating >= 0 and rating <= 4) or rating == -1):
            raise InvalidAggregateConnectionRating(rating=rating,
                                                   connection=connection)

        self.community = community
        self.connection = connection
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
        weight = kwds.get('weight', None)

        for field, value in (('Rating', rating), ('Weight', weight)):
            if not isinstance(value, Real):
                raise TypeError(
                    '{field} value of {value} is not a Real number.'
                    .format(field=field, value=value))

        if not ((rating >= 0 and rating <= 4) or rating == -1):
            raise InvalidAggregateConnectionRating(rating=rating,
                                                   connection=self.connection)
        if rating != self.rating or weight != self.weight:
            self.rating, self.weight = rating, weight
            self._modified.add(self)

    def json(self, hide=[], wrap=True, tight=True, raw=False, limit=10):
        od = OrderedDict((
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('community', self.community.trepr(tight=tight, raw=raw)),
            ('connection', self.connection.trepr(tight=tight, raw=raw)),
            ('aggregation', self.aggregation),
            ('rating', self.rating),
            ('weight', self.weight)
        ))
        for field in hide:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # AggregateProblemConnectionRating[(
    #     Community[(
    #         Problem[<problem_human_id>],
    #         <org>
    #         Geo[<geo_human_id>],
    #     )],
    #     ProblemConnection[(
    #         <axis>,
    #         Problem[<problem_a_human_id>],
    #         Problem[<problem_b_human_id>]
    #     )],
    #     <aggregation>
    # )]

    def __str__(self):
        cls_name = self.__class__.__name__
        problem, org, geo = self.community.derive_key()
        p_name = self.problem.name
        conn = self.connection
        is_causal = conn.axis == 'causal'
        p_a = conn.driver.name if is_causal else conn.broader.name
        if p_name == p_a:
            conn_str = str(conn).replace(p_name, '@' + p_name, 1)
        else:
            conn_str = ('@' + p_name).join(str(conn).rsplit(p_name, 1))
        return ('{cls}: {rating:.2f} with {weight:.2f} weight ({agg})\n'
                '  on {conn}\n'
                '  {org}{geo}'.format(
                   cls=cls_name,
                   rating=self.rating,
                   weight=self.weight,
                   agg=self.aggregation,
                   conn=conn_str,
                   org=''.join(('at ', org, ' ')) if org is not None else '',
                   geo=''.join(('in ', geo)) if geo is not None else ''))


class ProblemConnectionRating(BaseProblemModel):
    '''Base class for problem connection ratings

    Problem connection ratings are input by users within the context of
    a problem, org, and geo. For example, it is perfectly valid for the
    same user to provide a different rating of A -> B from the context
    of problem A vs. problem B because the perceived importance of B as
    an impact of A may be quite different from the perceived importance
    of A as a driver of B.

    Maintain problem/org/geo rather than substitute with community as
    this will most likely become a separate microservice and this extra
    granularity may be useful.
    '''
    # TODO: replace with problem_human_id and remove relationship
    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    problem = orm.relationship('Problem')

    # TODO: replace with org_human_id
    org = Column(types.String(256))

    # TODO: replace with geo_human_id and remove relationship
    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    geo = orm.relationship('Geo')

    # TODO: replace with other_problem_human_id and connection_category
    # and remove relationship. Connection category values include
    # drivers, impacts, broader, narrower; allows retrieving all ratings
    # in a community with a single query
    connection_id = Column(types.Integer, ForeignKey('problem_connection.id'))
    connection = orm.relationship('ProblemConnection',
                                  back_populates='ratings')

    connection_category = Column(types.String(16))

    # TODO: replace with user_id
    user = Column(types.String(60))

    _rating = Column('rating', types.Integer)
    _weight = Column('weight', types.Integer)

    # Querying use cases:
    #
    # 1. The Problem Page needs weighted average ratings on each connection
    #    to order them and modulate how they are displayed. This may end
    #    up being pre-processed, but it must be queried when calculated.
    #    cols: problem_id, org, geo, connection_id
    #       where most commonly org is None
    #    cols: problem_id, org, geo
    #
    # 2. The Problem Page needs to ask the user to rate connections that
    #    the user has not yet rated).
    #    cols: user, problem_id, org, geo
    #
    # 3. The Personal Dashboard needs to track history of all the user's
    #    inputs including connection ratings.
    #    cols: user
    #
    # __table_args__ = (UniqueConstraint('problem_id',
    #                                    'connection_id',
    #                                    'org',
    #                                    'geo',
    #                                    'user',
    #                                    name='uq_problem_connection_rating'),)
    #
    __table_args__ = (Index('ux_problem_connection_rating',
                            # ux for unique index
                            'problem_id',
                            'connection_id',
                            'org',
                            'geo_id',
                            'user',
                            unique=True),
                      Index('ix_problem_connection_rating:user+problem_id',
                            # ix for index
                            'user',
                            'problem_id',
                            'org',
                            'geo_id'),)

    Key = namedtuple('ProblemConnectionRatingKey',
                     'connection, problem, org, geo, user')

    @classmethod
    def create_key(cls, connection, problem, org=None, geo=None,
                   user='Intertwine', **kwds):
        '''Create key for a problem connection rating

        Return a key allowing the Trackable metaclass to register a
        problem connection rating instance. The key is a namedtuple of
        connection, problem, org, geo, and user.
        '''
        return cls.Key(connection, problem, org, geo, user)

    def derive_key(self):
        '''Derive key from a problem connection rating instance

        Return the registry key used by the Trackable metaclass from a
        problem connection rating instance. The key is a namedtuple of
        connection, problem, org, geo, and user.
        '''
        return self.__class__.Key(self.connection, self.problem, self.org,
                                  self.geo, self.user)

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, val):
        self.update_values(rating=val)

    rating = orm.synonym('_rating', descriptor=rating)

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, val):
        self.update_values(weight=val)

    weight = orm.synonym('_weight', descriptor=weight)

    def update_values(self, rating=None, weight=None):
        '''Update values

        Provides way to update both rating and weight at same time,
        since any change must be propagated to all affected aggregate
        ratings via the relevant communities.
        '''
        if rating is None and weight is None:
            raise ValueError('rating and weight cannot both be None')

        has_updated = False

        if rating is None:
            rating = self.rating
        elif not isinstance(rating, int) or rating < 0 or rating > 4:
            raise InvalidProblemConnectionRating(rating=rating,
                                                 *self.derive_key())
        else:
            old_rating = self.rating if hasattr(self, '_rating') else None
            if rating != old_rating:
                self._rating = rating
                has_updated = True

        if weight is None:
            weight = self.weight
        elif not isinstance(weight, int) or weight < 0:
            raise InvalidProblemConnectionWeight(weight=weight,
                                                 *self.derive_key())
        else:
            old_weight = self.weight if hasattr(self, '_weight') else None
            if weight != old_weight:
                self._weight = weight
                has_updated = True

        if has_updated:
            from ..communities.models import Community

            community = Community.query.filter_by(problem=self.problem,
                                                  org=self.org,
                                                  geo=self.geo).first()
            if community:
                community.update_aggregate_ratings(connection=self.connection,
                                                   user=self.user,
                                                   new_user_rating=rating,
                                                   new_user_weight=weight,
                                                   old_user_rating=old_rating,
                                                   old_user_weight=old_weight)

    def __init__(self, rating, problem, connection, org=None, geo=None,
                 user='Intertwine', weight=None):
        '''Initialize a new problem connection rating

        The connection parameter is an instance, problem and geo
        may be either instances or human_ids, and the rest are literals
        based on the JSON problem connection rating schema. The rating
        parameter must be an integer between 0 and 4 inclusive.
        '''
        if not isinstance(connection, ProblemConnection):
            raise InvalidEntity(variable='connection', value=connection,
                                classname='ProblemConnection')
        is_causal = connection.axis == 'causal'
        p_a = connection.driver if is_causal else connection.broader
        p_b = connection.impact if is_causal else connection.narrower
        if is_causal:
            self.connection_category = ('drivers' if problem is p_b
                                        else 'impacts')
        else:
            self.connection_category = ('broader' if problem is p_b
                                        else 'narrower')

        if isinstance(problem, basestring):
            problem = Problem.query.filter_by(human_id=problem).one()
        if problem not in (p_a, p_b):
            raise InvalidProblemForConnection(problem=problem,
                                              connection=connection)

        if isinstance(geo, basestring):
            geo = Geo.query.filter_by(human_id=geo).one()

        # TODO: take user instance in addition to user_id
        if user is None or user == '':
            raise InvalidUser(user=user, connection=connection)

        self.problem = problem
        self.connection = connection
        # TODO: make org an entity rather than a string
        self.org = org
        self.geo = geo
        self.user = user
        # weight = user.expertise(problem, org, geo)
        weight = 1 if weight is None else weight
        self.update_values(rating=rating, weight=weight)

    def modify(self, **kwds):
        '''Modify an existing problem connection rating

        Modify the rating field if a new value is provided and flag the
        problem connection rating as modified. Required by the Trackable
        metaclass.
        '''
        rating = kwds.get('rating', None)
        weight = kwds.get('weight', None)
        try:
            self.update_values(rating=rating, weight=weight)
            self._modified.add(self)
        except ValueError:
            pass

    # Use default __repr__() from Trackable:
    # ProblemConnectionRating[(
    #     Problem[<problem_human_id>],
    #     <org>,
    #     Geo[<geo_human_id>],
    #     ProblemConnection[(
    #         <axis>,
    #         Problem[<problem_a_human_id>],
    #         Problem[<problem_b_human_id>])
    #     )],
    #     <user>
    # )]

    def __str__(self):
        p_name = self.problem.name
        conn = self.connection
        is_causal = conn.axis == 'causal'
        p_a = conn.driver.name if is_causal else conn.broader.name
        if p_name == p_a:
            conn_str = str(conn).replace(p_name, '@' + p_name, 1)
        else:
            conn_str = ('@' + p_name).join(str(conn).rsplit(p_name, 1))
        org = self.org
        geo = self.geo
        return ('{cls}: {rating} by {user} with {weight} weight\n'
                '  on {conn}\n'
                '  {org}{geo}'.format(
                   cls=self.__class__.__name__,
                   rating=self.rating,
                   user=self.user,
                   weight=self.weight,
                   conn=conn_str,
                   org=''.join('at ', org, ' ') if org is not None else '',
                   geo=''.join('in ', geo) if geo is not None else ''))


class ProblemConnection(BaseProblemModel):
    '''Base class for problem connections

    A problem connection is uniquely defined by its axis ('causal' or
    'scoped') and the two problems it connects: problem_a and problem_b.

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

    axis = Column(types.String(6))
    problem_a_id = Column(types.Integer, ForeignKey('problem.id'))
    problem_b_id = Column(types.Integer, ForeignKey('problem.id'))
    # TODO: remove ratings relationship
    ratings = orm.relationship('ProblemConnectionRating',
                               back_populates='connection',
                               lazy='dynamic')
    # TODO: remove aggregate ratings relationship?
    aggregate_ratings = orm.relationship('AggregateProblemConnectionRating',
                                         back_populates='connection',
                                         lazy='dynamic')

    __table_args__ = (Index('ux_problem_connection',
                            # ux for unique index
                            'problem_a_id',
                            'axis',
                            'problem_b_id',
                            unique=True),
                      Index('ix_problem_connection:problem_b_id+axis',
                            # ix for index
                            'problem_b_id',
                            'axis'),)

    CategoryMapRecord = namedtuple(
        'ProblemConnectionCategoryMapRecord',
        'axis, category, component, ab_id, relative_a, '
        'relative_b, i_ab_id, i_component, i_category')

    CATEGORY_MAP = OrderedDict((
        ('drivers', CategoryMapRecord(
            'causal', 'drivers', 'driver', 'problem_a_id', 'adjacent_problem',
            'self', 'problem_b_id', 'impact', 'impacts')),
        ('impacts', CategoryMapRecord(
            'causal', 'impacts', 'impact', 'problem_b_id', 'self',
            'adjacent_problem', 'problem_a_id', 'driver', 'drivers')),
        ('broader', CategoryMapRecord(
            'scoped', 'broader', 'broader', 'problem_a_id', 'adjacent_problem',
            'self', 'problem_b_id', 'narrower', 'narrower')),
        ('narrower', CategoryMapRecord(
            'scoped', 'narrower', 'narrower', 'problem_b_id', 'self',
            'adjacent_problem', 'problem_a_id', 'broader', 'broader'))
    ))

    Key = namedtuple('ProblemConnectionKey', 'axis, problem_a, problem_b')

    @classmethod
    def create_key(cls, axis, problem_a, problem_b, **kwds):
        '''Create key for a problem connection

        Return a key allowing the Trackable metaclass to register a
        problem connection instance. The key is a namedtuple of axis,
        problem_a, and problem_b.
        '''
        return cls.Key(axis, problem_a, problem_b)

    def derive_key(self):
        '''Derive key from a problem connection instance

        Return the registry key used by the Trackable metaclass from a
        problem connection instance. The key is a namedtuple of axis,
        problem_a, and problem_b.
        '''
        is_causal = self.axis == 'causal'
        p_a = self.driver if is_causal else self.broader
        p_b = self.impact if is_causal else self.narrower
        return self.__class__.Key(self.axis, p_a, p_b)

    def __init__(self, axis, problem_a, problem_b,
                 ratings_data=None, ratings_context_problem=None):
        '''Initialize a new problem connection

        Required inputs include axis, a string with value 'causal' or
        'scoped' and two problem instances. An axis of 'causal' means
        problem_a is a driver of problem_b, while an axis of 'scoped'
        means problem_a is broader than problem_b.

        The optional ratings_data parameter is a list of ratings based
        on the JSON problem connection rating schema. The problem
        parameter must be provided if ratings_data is specified, as it
        is required to define a problem connection rating.
        '''
        # TODO: make axis an Enum
        if axis not in ('causal', 'scoped'):
            raise InvalidConnectionAxis(axis=axis)
        if problem_a is problem_b:
            raise CircularConnection(problem=problem_a)
        self.axis = axis
        is_causal = self.axis == 'causal'
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
                connection=self,
                problem=ratings_context_problem,
                **rating_data)
            # TODO: add tracking of new to Trackable and check it here
            if connection_rating not in self.ratings:
                self.ratings.append(connection_rating)
                rating_added = True
        if rating_added and hasattr(self, '_modified'):
            self._modified.add(self)

    # Use default __repr__() from Trackable:
    # ProblemConnection[(
    #     <axis>,
    #     Problem[<human_id_a>],
    #     Problem[<human_id_b>]
    # )]

    def __str__(self):
        is_causal = self.axis == 'causal'
        ct = '->' if is_causal else '::'
        p_a = self.driver.name if is_causal else self.broader.name
        p_b = self.impact.name if is_causal else self.narrower.name
        return '{p_a} {ct} {p_b}'.format(p_a=p_a, ct=ct, p_b=p_b)


class Problem(BaseProblemModel):
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
                            "ProblemConnection.axis=='causal')",
                backref='impact',
                lazy='dynamic')
    impacts = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_a_id, "
                            "ProblemConnection.axis=='causal')",
                backref='driver',
                lazy='dynamic')
    broader = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_b_id, "
                            "ProblemConnection.axis=='scoped')",
                backref='narrower',
                lazy='dynamic')
    narrower = orm.relationship(
                'ProblemConnection',
                primaryjoin="and_(Problem.id==ProblemConnection.problem_a_id, "
                            "ProblemConnection.axis=='scoped')",
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
        self.definition_url = (definition_url.strip()
                               if definition_url else None)
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
            elif k in ProblemConnection.CATEGORY_MAP.keys():
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
        cat_map = ProblemConnection.CATEGORY_MAP[category]
        axis, inverse_name = cat_map.axis, cat_map.i_category
        p_a, p_b = cat_map.relative_a, cat_map.relative_b

        connections = getattr(self, category)

        for connection_data in data:
            adjacent_name = connection_data.get('adjacent_problem', None)
            adjacent_problem = Problem(name=adjacent_name)
            ratings_data = connection_data.get('problem_connection_ratings',
                                               [])
            connection = ProblemConnection(
                axis=axis,
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

    def connections(self):
        '''Connections

        Returns a generator that iterates through all the problem's
        connections
        '''
        # ['impact', 'driver', 'narrower', 'broader']
        categories = map(attrgetter('i_component'),
                         ProblemConnection.CATEGORY_MAP.values())

        return ProblemConnection.query.filter(or_(
            *map(lambda x: getattr(ProblemConnection, x) == self, categories)))

    def connections_by_category(self):
        '''Connections by category

        Returns an ordered dictionary of connection queries keyed by
        category that iterate alphabetically by the name of the
        adjoining problem. The category order is specified by the
        problem connection category map.
        '''
        PC = ProblemConnection
        connections = OrderedDict()
        for category in PC.CATEGORY_MAP:
            component = getattr(PC, PC.CATEGORY_MAP[category].component)
            connections[category] = (getattr(self, category).join(component)
                                     .order_by(Problem.name))
        return connections

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
