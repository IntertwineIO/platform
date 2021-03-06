# -*- coding: utf-8 -*-
import math
from collections import namedtuple
from itertools import groupby
from operator import attrgetter

from sqlalchemy import Column, ForeignKey, Index, desc, orm, types
from sqlalchemy.orm.exc import DetachedInstanceError

from intertwine import IntertwineModel
from intertwine.problems.exceptions import InvalidAggregation
from intertwine.problems.models import (
    AggregateProblemConnectionRating as APCR,
    ProblemConnection as PC,
    ProblemConnectionRating as PCR,
    Problem)
from intertwine.trackable.exceptions import KeyMissingFromRegistryAndDatabase
from intertwine.utils.jsonable import JsonProperty
from intertwine.utils.structures import PeekableIterator
from intertwine.utils.vardygr import vardygrify

BaseCommunityModel = IntertwineModel


class Community(BaseCommunityModel):
    """Base class for communities

    A 'community' resides at the intersection of a (social) problem, a
    geo, and an org and is uniquely defined by them. Each term may have
    a value of None, indicating the scope encompasses all values:
    - problem is None: 'All Problems'
    - org is None: 'Any Organization (or None)'
    - geo is None: 'The World'
    """
    # Future: Create a top-level entity for each and let None mean None?
    # 'All Problems', 'Any Organization (or None)', and 'The World'.
    # There could also be an 'All Organizations' org that does not
    # include None. A problem and geo must always be defined, whereas an
    # org may each be None, indicating no org affiliation.

    ALPHABETIZE_UNRATED_CONNECTIONS = False  # Adds overhead when True

    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    _problem = orm.relationship('Problem', lazy='joined')

    # TODO: Replace with Org model relationship
    _org = Column(types.String)
    # org_id = Column(types.Integer, ForeignKey('org.id'))
    # _org = orm.relationship('Org', lazy='joined')

    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    _geo = orm.relationship('Geo', lazy='joined')

    aggregate_ratings = orm.relationship('AggregateProblemConnectionRating',
                                         back_populates='community',
                                         lazy='dynamic')
    jsonified_aggregate_ratings = JsonProperty(
        name='aggregate_ratings', method='jsonify_aggregate_ratings')

    num_followers = Column(types.Integer)

    @property
    def name(self):
        return '{problem}{org_clause}{geo_clause}'.format(
            problem=self.problem.name,
            org_clause=(' at {org}'.format(org=self.org) if self.org else ''),
            geo_clause=(' in {geo}'.format(
                geo=self.geo.display(show_abbrev=False)) if self.geo else ''))

    jsonified_name = JsonProperty(name='name', begin=True)

    @property
    def problem(self):
        return self._problem

    @problem.setter
    def problem(self, val):
        # val is None is valid and means 'All Problems'
        # During __init__()
        if self._problem is None:
            self._problem = val
            return
        # Not during __init__()
        key = self.model_class.Key(problem=val, org=self.org, geo=self.geo)
        self.register_update(key)

    problem = orm.synonym('_problem', descriptor=problem)

    @property
    def org(self):
        return self._org

    @org.setter
    def org(self, val):
        # val is None is valid and means 'Any Organization (or None)'
        # During __init__()
        if self._org is None:
            self._org = val
            return
        # Not during __init__()
        key = self.model_class.Key(problem=self.problem, org=val, geo=self.val)
        self.register_update(key)

    org = orm.synonym('_org', descriptor=org)

    @property
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        # if val is None is valid and means 'The World'
        # During __init__()
        if self._geo is None:
            self._geo = val
            return
        # Not during __init__()
        key = self.model_class.Key(problem=self.problem, org=self.org, geo=val)
        self.register_update(key)

    geo = orm.synonym('_geo', descriptor=geo)

    @property
    def significance(self):
        """Float reflecting a community's importance; minimum 1"""
        return math.log((self.num_followers or 0) + 1) + 1

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

    Key = namedtuple('CommunityKey', 'problem, org, geo')

    @classmethod
    def create_key(cls, problem, org, geo, **kwds):
        """Create key for a community

        Return a key allowing the Trackable metaclass to register a
        community instance. The key is a namedtuple of problem, org, and
        geo.
        """
        return cls.Key(problem, org, geo)

    def derive_key(self, **kwds):
        """Derive key from a community instance

        Return the registry key used by the Trackable metaclass from a
        community instance. The key is a namedtuple of problem, org, and
        geo.
        """
        return self.model_class.Key(self.problem, self.org, self.geo)

    @classmethod
    def manifest(cls, problem_huid, org_huid, geo_huid):
        """Manifest community, either real or vardygr"""
        # Raise if any human ids don't exist
        key = cls.reconstruct((problem_huid, org_huid, geo_huid), as_key=True)
        try:
            return cls[key]
        except KeyMissingFromRegistryAndDatabase:
            return vardygrify(cls, num_followers=0, **key._asdict())

    def __init__(self, problem, org, geo, num_followers=0):
        """Initialize a new community"""
        self.problem = problem
        self.org = org
        self.geo = geo
        self.num_followers = num_followers

    def update_inclusive_aggregate_ratings(self, connection, user,
                                           new_user_rating,
                                           old_user_rating=None):
        """
        Update inclusive aggregate ratings

        Update aggregate ratings for the current community and recurse
        on immediately encompassing communities.
        """
        # TODO
        pass

    def update_aggregate_ratings(self, connection, user,
                                 new_user_rating, new_user_weight,
                                 old_user_rating=None, old_user_weight=None):
        """
        Update aggregate ratings

        Given a connection, a user, and new/old rating & weight values,
        update all affected aggregate ratings. Intended to be called in
        conjunction with or shortly after the rating has been updated.
        """
        # Update the strict aggregate rating for this community
        apcr = APCR.query.filter_by(community=self, connection=connection,
                                    aggregation='strict').first()
        if apcr:
            apcr.update_values(new_user_rating=new_user_rating,
                               new_user_weight=new_user_weight,
                               old_user_rating=old_user_rating,
                               old_user_weight=old_user_weight)
        # Update inclusive aggregate ratings in encompassing communities
        self.update_inclusive_aggregate_ratings(
            connection=connection, user=user,
            new_user_rating=new_user_rating, old_user_rating=old_user_rating)

    def aggregate_connection_ratings(self, aggregation='strict'):
        """
        Aggregate connection ratings

        Aggregate and return a community's connection ratings using the
        specified aggregation method. If an aggregate rating already
        exists, it is updated; otherwise, a new one is created.

        If called on a vardygr community and ratings exist, a real
        community is created and linked to the new aggregate ratings.
        """
        community = self
        community_key = self.derive_key()
        problem, org, geo = community_key

        if aggregation not in ('strict'):
            raise InvalidAggregation(aggregation=aggregation)

        pcrs = (PCR.query.filter_by(problem=problem, org=org, geo=geo)
                         .order_by(PCR.connection_category, PCR.connection_id))
        pcrs = PeekableIterator(pcrs)
        # Create and persist a community only if necessary
        if not isinstance(self, Community) and pcrs.has_next():
            existing_community = Community.tget(community_key)
            if existing_community:
                community = existing_community
            else:
                community = Community(problem=problem, org=org, geo=geo)
                session = community.session()
                session.add(community)
                session.commit()

        # TODO: give Trackable fine-grained registration and register
        # aggregate ratings associated with the community to enable the
        # constructor to fail over to modify existing aggregate ratings.

        ars = []
        # Create aggregate ratings from ratings
        for connection, ratings in groupby(pcrs, key=attrgetter('connection')):
            # If an aggregate rating already exists, it will be modified
            ars.append(APCR(community=community, connection=connection,
                            aggregation=aggregation, ratings=ratings))
        # Persist aggregate ratings
        if len(ars) > 0:
            session = ars[0].session()
            session.add_all(ars)
            session.commit()

        return ars

    def jsonify_connection_category(self, problem, category, aggregation,
                                    aggregate_ratings, depth, **json_kwargs):
        """
        Jsonify connection category

        Yield the next aggregate rating JSON, where the order matches
        the input iterable and is followed by unrated connections. The
        latter are alphabetized by adjacent problem if so configured.

        I/O:
        problem:            Problem instance
        category:           ProblemConnection category, e.g. 'drivers'
        aggregate_ratings:  AggregateProblemConnectionRating iterable
        depth:              jsonify depth
        json_kwargs:        one or more JSON kwargs, excluding depth
        """
        _json = json_kwargs['_json']
        nest = json_kwargs.get('nest', False)
        rated_connections = set()
        if aggregate_ratings:
            for aggregate_rating in aggregate_ratings:
                rated_connections.add(aggregate_rating.connection)

                key = aggregate_rating.json_key(**json_kwargs)
                if depth > 1 and (nest or key not in _json):
                    jsonified = aggregate_rating.jsonify(depth=depth - 1, **json_kwargs)

                yield jsonified if depth > 1 and nest else key

        if self.ALPHABETIZE_UNRATED_CONNECTIONS:
            try:
                component = getattr(PC, PC.CATEGORY_MAP[category].component)
                connections = (getattr(problem, category)
                               .join(component).order_by(Problem.name))
            except DetachedInstanceError:
                connections = getattr(problem, category)
        else:
            connections = getattr(problem, category)

        for connection in connections:
            if connection not in rated_connections:
                aggregate_rating = vardygrify(APCR,
                                              community=self,
                                              connection=connection,
                                              connection_category=connection.derive_category(problem),
                                              aggregation=aggregation,
                                              rating=APCR.NO_RATING,
                                              weight=APCR.NO_WEIGHT)

                key = aggregate_rating.json_key(**json_kwargs)
                if depth > 1 and (nest or key not in _json):
                    jsonified = aggregate_rating.jsonify(depth=depth - 1, **json_kwargs)

                yield jsonified if depth > 1 and nest else key

    def jsonify_aggregate_ratings(self, aggregation='strict', depth=1,
                                  _path=None, **json_kwargs):
        """
        Jsonify aggregate ratings

        Return a dictionary keyed by connection category ('drivers',
        'impacts', 'broader', 'narrower') where values are lists of
        aggregate rating JSON in descending order by rating.

        Searches for existing aggregate connection ratings with the
        specified aggregation method, and if none are found, aggregates
        them from ratings. Connections without ratings are included last
        in alphabetical order by problem name if so configured.
        """
        community = self
        community_exists = type(self) is Community
        problem, org, geo = self.derive_key()

        if community_exists:
            ars = (APCR.query
                       .filter_by(community=self, aggregation=aggregation)
                       .order_by(APCR.connection_category, desc(APCR.rating)))
            ars = PeekableIterator(ars)

        if not community_exists or not ars.has_next():
            ars = self.aggregate_connection_ratings(aggregation=aggregation)
            if ars:
                community = ars[0].community
                ars.sort(key=attrgetter('connection_category', 'rating'),
                         reverse=True)

        with _path.component('{category}'):

            rv = {category: list(community.jsonify_connection_category(
                  problem, category, aggregation, aggregate_ratings, depth,
                  _path=_path.with_last_field_as(category), **json_kwargs))
                  for category, aggregate_ratings
                  in groupby(ars, key=attrgetter('connection_category'))}

            for category in PC.CATEGORY_MAP:
                if category not in rv:
                    rv[category] = list(community.jsonify_connection_category(
                        problem, category, aggregation, None, depth,
                        _path=_path.with_last_field_as(category), **json_kwargs))

        return rv
