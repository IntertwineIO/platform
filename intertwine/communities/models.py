#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple, OrderedDict
from functools import partial
from operator import attrgetter
from itertools import groupby, imap, tee

from sqlalchemy import desc, orm, types, Column, ForeignKey, Index

from .. import BaseIntertwineModel
from ..utils import (AutoTableMixin, PeekableIterator, stringify)
from ..problems.models import (AggregateProblemConnectionRating as APCR,
                               ProblemConnectionRating as PCR,
                               ProblemConnection as PC,
                               Problem)

from ..problems.exceptions import InvalidAggregation

BaseCommunityModel = BaseIntertwineModel


class Community(BaseCommunityModel, AutoTableMixin):
    '''Base class for communities

    A 'community' resides at the intersection of a (social) problem, a
    geo, and an org and is uniquely defined by them. Each term may have
    a value of None, indicating the scope encompasses all values:
    - problem is None: 'All Problems'
    - org is None: 'Any Organization (or None)'
    - geo is None: 'The World'
    '''
    # Future: Create a top-level entity for each and let None mean None?
    # 'All Problems', 'Any Organization (or None)', and 'The World'.
    # There could also be an 'All Organizations' org that does not
    # include None. A problem and geo must always be defined, whereas an
    # org may each be None, indicating no org affiliation.

    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    _problem = orm.relationship('Problem', lazy='joined')

    # TODO: Replace with Org model relationship
    _org = Column(types.String)
    # org_id = Column(types.Integer, ForeignKey('org.id'))
    # _org = orm.relationship('Org', lazy='joined')

    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    _geo = orm.relationship('Geo', lazy='joined')

    num_followers = Column(types.Integer)

    aggregate_ratings = orm.relationship('AggregateProblemConnectionRating',
                                         back_populates='community',
                                         lazy='dynamic')

    @property
    def problem(self):
        return self._problem

    @problem.setter
    def problem(self, val):
        # val is None is valid and means 'All Problems'
        if self._problem is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = Community.create_key(problem=val, org=self.org, geo=self.geo)
            inst = Community[key]
            if inst is not None and inst is not self:
                raise ValueError('{!r} is already registered.'.format(key))
            # update registry with new key
            Community.unregister(self)
            Community[key] = self
        self._problem = val  # set new value last

    problem = orm.synonym('_problem', descriptor=problem)

    @property
    def org(self):
        return self._org

    @org.setter
    def org(self, val):
        # val is None is valid and means 'Any Organization (or None)'
        if self._org is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = Community.create_key(problem=self.problem, org=val,
                                       geo=self.val)
            inst = Community[key]
            if inst is not None and inst is not self:
                raise ValueError('{!r} is already registered.'.format(key))
            # update registry with new key
            Community.unregister(self)
            Community[key] = self
        self._org = val  # set new value last

    org = orm.synonym('_org', descriptor=org)

    @property
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        # if val is None is valid and means 'The World'
        if self._geo is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = Community.create_key(problem=self.problem, geo=val,
                                       org=self.org)
            inst = Community[key]
            if inst is not None and inst is not self:
                raise ValueError('{!r} is already registered.'.format(key))
            # update registry with new key
            Community.unregister(self)
            Community[key] = self
        self._geo = val  # set new value last

    geo = orm.synonym('_geo', descriptor=geo)

    # Querying use cases:
    #
    # 1. Fetch the community for a particular problem, org, and geo, to
    #    display on community page
    #    cols: problem, org, geo
    # 2. Fetch all communities for a particular problem to circulate
    #    (problem-focused) content across geos
    #    cols: problem, geo
    # 3. Fetch all communities for a particular geo to display top/
    #    trending problems and circulate content to related problems
    #    cols: geo, problem
    # 4. Fetch all communities for a particular org to display top/
    #    trending problems and circulate content to related problems
    #    cols: org, problem
    __table_args__ = (Index('ux_community:problem+org+geo',
                            # ux for unique index
                            'problem_id',
                            '_org',
                            'geo_id',
                            unique=True),
                      Index('ix_community:geo+problem',
                            # ix for index
                            'geo_id',
                            'problem_id'),
                      Index('ix_community:org+problem',
                            # ix for index
                            '_org',
                            'problem_id'),
                      )

    Key = namedtuple('Key', 'problem, org, geo')

    @classmethod
    def create_key(cls, problem, org, geo, **kwds):
        '''Create key for a community

        Return a key allowing the Trackable metaclass to register a
        community instance. The key is a namedtuple of problem, org, and
        geo.
        '''
        return cls.Key(problem, org, geo)

    def derive_key(self):
        '''Derive key from a community instance

        Return the registry key used by the Trackable metaclass from a
        community instance. The key is a namedtuple of problem, org, and
        org.
        '''
        # Use __class__ instead of type() to support mocks
        return self.__class__.Key(self.problem, self.org, self.geo)

    def __init__(self, problem=None, org=None, geo=None, num_followers=0):
        '''Initialize a new community'''
        self.problem = problem
        self.org = org
        self.geo = geo
        self.num_followers = num_followers

    def update_inclusive_aggregate_ratings(self, connection, user,
                                           new_user_rating,
                                           old_user_rating=None):
        '''Update inclusive aggregate ratings

        Works by updating the inclusive aggregate ratings for the
        current community and then recursively calling itself on
        immediately encompassing communities.
        '''
        # TODO
        pass

    def update_aggregate_ratings(self, connection, user,
                                 new_user_rating, new_user_weight,
                                 old_user_rating=None, old_user_weight=None):
        '''Update aggregate ratings

        Given a connection, a user, and new/old rating and weight
        values, updates all affected aggregate ratings. Intended to be
        called in conjunction with or shortly after the rating has been
        updated.
        '''
        # Update the strict aggregate rating for this community
        apcr = APCR.query.filter_by(community=self, connection=connection,
                                    aggregation='strict').first()
        if apcr:
            APCR.update_values(new_user_rating=new_user_rating,
                               new_user_weight=new_user_weight,
                               old_user_rating=old_user_rating,
                               old_user_weight=old_user_weight)
        # Update inclusive aggregate ratings in encompassing communities
        self.update_inclusive_aggregate_ratings(
            connection=connection, user=user,
            new_user_rating=new_user_rating, old_user_rating=old_user_rating)

    def aggregate_connection_ratings(self, aggregation='strict'):
        return Community.aggregate_connection_ratings_x(
                                community=self, aggregation=aggregation)

    @staticmethod
    def aggregate_connection_ratings_x(problem=None, org=None, geo=None,
                                       community=None, aggregation='strict'):
        '''Aggregate connection ratings (external)

        Aggregates a community's connection ratings using the specified
        aggregation method and returns them. If an aggregate rating
        already exists, it is updated; otherwise, a new aggregate rating
        is created.
        '''
        if aggregation not in ('strict'):
            raise InvalidAggregation(aggregation=aggregation)

        if community:
            problem, org, geo = community.derive_key()

        pcrs = (PCR.query.filter_by(
                problem=problem, org=org, geo=geo)
                .order_by(PCR.connection_category, PCR.connection_id))

        pcrs = PeekableIterator(pcrs)

        if not community and pcrs.has_next():
            community = Community(problem=problem, org=org, geo=geo)
            session = community.session()
            session.add(community)
            session.commit()

        # TODO: give Trackable fine-grained registration and then
        # register any aggregate ratings associated with the community.
        # This will enable the APCR constructor to fail over to modify
        # any existing aggregate ratings

        rv = []

        # Create aggregate ratings from ratings
        for connection, ratings in groupby(pcrs, key=attrgetter('connection')):
            # If an aggregate rating already exists, it will be modified
            rv.append(APCR(community=community, connection=connection,
                           aggregation=aggregation, ratings=ratings))
        # Persist aggregate ratings
        if len(rv) > 0:
            session = rv[0].session()
            session.add_all(rv)
            session.commit()

        return rv

    @staticmethod
    def prepare_connections_x(problem, category, aggregate_ratings=[]):
        '''Prepare connections
        '''
        rated_connections = set()
        for aggregate_rating in aggregate_ratings:
            rated_connections.add(aggregate_rating.connection)
            yield (aggregate_rating.connection, aggregate_rating.rating)

        component = getattr(PC, PC.CATEGORY_MAP[category].component)
        connections = (getattr(problem, category).join(component)
                                                 .order_by(Problem.name))

        for connection in connections:
            if connection not in rated_connections:
                yield (connection, APCR.NO_RATING)

    def assemble_connections_with_ratings(self, aggregation='strict'):
        '''Assemble connections with ratings for the community (self)'''
        return Community.assemble_connections_with_ratings_x(
                                community=self, aggregation=aggregation)

    @staticmethod
    def assemble_connections_with_ratings_x(problem=None, org=None, geo=None,
                                            community=None,
                                            aggregation='strict'):
        '''Assemble connections with ratings (external)

        Returns a dictionary keyed by connection category ('drivers',
        'impacts', 'broader', 'narrower') where values are [generators
        for (?)] connection/aggregate rating tuples in descending order.

        Searches for existing aggregate connection ratings first, and if
        none are found, aggregates them from ratings. Connections
        without ratings are included last in alphabetical order by the
        name of the adjoining problem.

        The 'x' indicates this method is the 'external' version that
        does not require a community instance. However, if a community
        exists for the given problem/org/geo, it must be passed. This
        enables community pages without ratings to be rendered without
        creating a community instance, which is important due to bots.
        '''
        if community:
            problem, org, geo = community.derive_key()
            aggregate_ratings = (APCR.query.filter_by(community=community,
                                                      aggregation=aggregation)
                                 .order_by(APCR.connection_category,
                                           desc(APCR.rating)))
            aggregate_ratings = PeekableIterator(aggregate_ratings)

        if not community or not aggregate_ratings.has_next():
            aggregate_ratings = Community.aggregate_connection_ratings_x(
                                problem=problem, org=org, geo=geo,
                                community=community, aggregation=aggregation)
            aggregate_ratings.sort(
                key=attrgetter('connection_category', 'rating'), reverse=True)

        rv = {category: list(Community.prepare_connections_x(
                                                    problem, category, ars))
              for category, ars in groupby(
              aggregate_ratings, key=attrgetter('connection_category'))}

        for category in PC.CATEGORY_MAP:
            if category not in rv:
                rv[category] = list(Community.prepare_connections_x(
                                                    problem, category, []))

        return rv

    def json(self, mute=[], wrap=True, tight=True, raw=False, limit=10):
        '''JSON structure for a community instance

        Returns a structure for the given community instance that will
        serialize to JSON.

        The following inputs may be specified:
        mute=[]:    mutes (excludes) any field names listed
        wrap=True:  wrap the instance in a dictionary keyed by repr
        tight=True: make all repr values tight (without whitespace)
        raw=False:  when True, adds extra escapes (for printing)
        limit=10:   caps the number of list or dictionary items beneath
                    the main level; a negative limit indicates no cap
        '''
        import ipdb; ipdb.set_trace

        od = OrderedDict((
            ('class', self.__class__.__name__),
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('problem', self.problem.trepr(tight=tight, raw=raw,
                                           outclassed=True)),
            ('org', self.org),
            ('geo', self.geo.trepr(tight=tight, raw=raw, outclassed=True)),
            ('num_followers', self.num_followers)
        ))

        for field in mute:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # Community[(
    #     Problem[<problem_human_id>],
    #     <org>
    #     Geo[<geo_human_id>],
    # )]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return stringify(
            self.json(wrap=True, tight=False, raw=True, limit=-1), limit=10)
