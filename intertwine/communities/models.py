#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import namedtuple, OrderedDict

from sqlalchemy import orm, types, Column, ForeignKey, Index

from ..utils import AutoTableMixin, BaseIntertwineModel, stringify


BaseCommunityModel = BaseIntertwineModel


class Community(BaseCommunityModel, AutoTableMixin):
    '''Base class for communities

    A 'community' resides at the intersection of a (social) problem, a
    geo, and an org and is uniquely defined by them. A problem and geo
    must always be defined, whereas an org may each be None, indicating
    no org affiliation. There is a single top-level entity for each:
    'All Problems', 'The World', and 'Any Organization (or None)'. There
    is also an 'All Organizations' org that does not include None.
    '''
    problem_id = Column(types.Integer, ForeignKey('problem.id'))
    _problem = orm.relationship('Problem', lazy='joined')

    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    _geo = orm.relationship('Geo', lazy='joined')

    # TODO: Replace with Org model relationship
    _org = Column(types.String)
    # org_id = Column(types.Integer, ForeignKey('org.id'))
    # _org = orm.relationship('Org', lazy='joined')

    num_followers = Column(types.Integer)

    @property
    def problem(self):
        return self._problem

    @problem.setter
    def problem(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._problem is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = Community.create_key(problem=val, geo=self.geo, org=self.org)
            inst = Community[key]
            if inst is not None and inst is not self:
                raise ValueError('{!r} is already registered.'.format(key))
            # update registry with new key
            Community.unregister(self)
            Community[key] = self

        self._problem = val  # set new value last

    problem = orm.synonym('_problem', descriptor=problem)

    @property
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

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

    @property
    def org(self):
        return self._org

    @org.setter
    def org(self, val):
        # Okay if val is None

        if self._org is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = Community.create_key(problem=self.problem, geo=self.val,
                                       org=val)
            inst = Community[key]
            if inst is not None and inst is not self:
                raise ValueError('{!r} is already registered.'.format(key))
            # update registry with new key
            Community.unregister(self)
            Community[key] = self

        self._org = val  # set new value last

    org = orm.synonym('_org', descriptor=org)

    # Querying use cases:
    #
    # 1. Fetch the community for a particular problem, geo, and org to
    #    display on community page
    #    cols: problem, geo, org
    # 2. Fetch all communities for a particular problem to circulate
    #    (problem-focused) content across geos
    #    cols: problem, geo
    # 3. Fetch all communities for a particular geo to display top/
    #    trending problems and circulate content to related problems
    #    cols: geo, problem
    # 4. Fetch all communities for a particular org to display top/
    #    trending problems and circulate content to related problems
    #    cols: org, problem
    __table_args__ = (Index('ux_community:problem+geo+org',
                            # ux for unique index
                            'problem_id',
                            'geo_id',
                            '_org',
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

    Key = namedtuple('Key', 'problem, geo, org')

    @classmethod
    def create_key(cls, problem, geo, org, **kwds):
        '''Create key for a community

        Return a key allowing the Trackable metaclass to register a
        community instance. The key is a namedtuple of problem, geo, and
        org.
        '''
        return cls.Key(problem, geo, org)

    def derive_key(self):
        '''Derive key from a community instance

        Return the registry key used by the Trackable metaclass from a
        community instance. The key is a namedtuple of problem, geo, and
        org.
        '''
        return type(self).Key(self.problem, self.geo, self.org)

    def __init__(self, problem=None, geo=None, org=None):
        '''Initialize a new community'''
        self.problem = problem
        self.geo = geo
        self.org = org
        self.num_followers = 0

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
        od = OrderedDict((
            ('class', type(self).__name__),
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('problem', self.problem.trepr(tight=tight, raw=raw, outclassed=True)),
            ('geo', self.geo.trepr(tight=tight, raw=raw, outclassed=True)),
            ('org', self.org.trepr(tight=tight, raw=raw, outclassed=True)),
            ('num_followers', self.num_followers)
        ))

        for field in mute:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # Community[(
    #     Problem[<problem>],
    #     Geo[<geo>],
    #     <org>
    # )]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return stringify(
            self.json(wrap=True, tight=False, raw=True, limit=-1), limit=10)
