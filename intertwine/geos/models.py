#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import orm, types, Column, ForeignKey, Index, Table, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from ..utils import AutoTableMixin, Trackable


BaseGeoModel = make_declarative_base(Base=ModelBase, Meta=Trackable)


geo_association_table = Table(
    'geo_association', BaseGeoModel.metadata,
    Column('parent_id', types.Integer, ForeignKey('geo.id')),
    Column('child_id', types.Integer, ForeignKey('geo.id'))
)


class Geo(BaseGeoModel, AutoTableMixin):
    '''Base class for geos

    human_id must be unique, so geos must be properly qualified. It
    aligns to the path established by path_parent geos (abbreviated).
    Distinguishes Austin, TX from Austin in AR, IN, MN, NV, or PA.
    geo_type      geo                   path_parent  human_id
    country       US                    (none)       us
    subdivision1  TX                    US           us/tx
    csa           Greater Houston Area  TX           us/tx/greater_houston_area
    cbsa          Austin Area           TX           us/tx/austin_area
    subdivision2  Travis County         TX           us/tx/travis_county
    place         Austin                TX           us/tx/austin
    '''
    _name = Column('name', types.String(60))
    _abbrev = Column('abbrev', types.String(4))
    _human_id = Column('human_id', types.String(60), index=True, unique=True)
    path_parent_id = Column(types.Integer, ForeignKey('geo.id'))
    _path_parent = orm.relationship(
                'Geo',
                primaryjoin=('Geo.path_parent_id==Geo.id'),
                remote_side='Geo.id',
                backref=orm.backref('path_children', lazy='dynamic'),
                lazy='joined')

    the_prefix = Column(types.Boolean)
    geo_type = Column(types.String(30))

    # city, town, village, parish, etc.; based on lsad for places
    descriptor = Column(types.String(60))

    # geo_type      us geo      us parents
    # country       US          None
    # subdivision1  state       US
    # csa           csa         state
    # cbsa          cbsa        csa or state (if no csa)
    # subdivision2  county      cbsa or state (if no cbsa)
    # place         place       county or counties or state (if no county)
    parents = orm.relationship(
                'Geo', secondary='geo_association',
                primaryjoin='Geo.id==geo_association.c.child_id',
                secondaryjoin='Geo.id==geo_association.c.parent_id',
                backref=orm.backref('children', lazy='dynamic'),
                lazy='joined')

    # enables population-based prioritization and urban/rural designation
    total_pop = Column(types.Integer)
    urban_pop = Column(types.Integer)
    # TODO: add other attributes such as demographics, geography, etc.

    delimiter = '>'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        # Not during __init__() and there's no abbreviation used instead
        if self.human_id is not None and self.abbrev is None:
            self.human_id = Geo.create_key(name=val,
                                           path_parent=self.path_parent)
        self._name = val  # set name last

    name = orm.synonym('_name', descriptor=name)

    @property
    def abbrev(self):
        return self._abbrev

    @abbrev.setter
    def abbrev(self, val):
        if self.human_id is not None:  # Not during __init__()
            self.human_id = Geo.create_key(name=self.name, abbrev=val,
                                           path_parent=self.path_parent)
        self._abbrev = val  # set abbrev last

    abbrev = orm.synonym('_abbrev', descriptor=abbrev)

    @property
    def path_parent(self):
        return self._path_parent

    @path_parent.setter
    def path_parent(self, val):
        if self.human_id is not None:  # Not during __init__()
            self.human_id = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                           path_parent=val)
        self._path_parent = val

    path_parent = orm.synonym('_path_parent', descriptor=path_parent)

    @property
    def human_id(self):
        return self._human_id

    @human_id.setter
    def human_id(self, val):
        if val is None:
            val = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                 path_parent=self.path_parent)
        if val == self.human_id:
            return
        # check if it's already registered by a different geo
        geo = Geo._instances.get(val, None)
        if geo is not None and geo is not self:
            raise NameError("'{}' is already registered.".format(val))
        # recursively propagate change to path_children
        for pc in self.path_children:
            pc.human_id = Geo.create_key(name=pc.name, abbrev=pc.abbrev,
                                         human_base=val)
        if hasattr(self, '_human_id'):  # unregister old human_id
            # Default None since Trackable registers after Geo.__init__()
            Geo._instances.pop(self.human_id, None)
        Geo[val] = self  # register the new human_id
        self._human_id = val  # set human_id last

    human_id = orm.synonym('_human_id', descriptor=human_id)

    @staticmethod
    def create_key(name=None, abbrev=None, path_parent=None, human_base=None,
                   **kwds):
        '''Create key for a geo

        Return a registry key allowing the Trackable metaclass to look
        up a geo instance. The key is created by concatenating a
        human_base with the given abbreviation if provided, else name.
        By default, the human_base is assembled by recursively following
        the path_parent. Alternatively, a human_base using the same
        format can be provided directly for optimization purposes. The
        latter is recommended for bulk loads. All geo abbreviations and
        names are separated by the Geo.delimiter.
        '''
        if human_base is None or human_base == '':
            human_base = ''
            path_finder = path_parent
            while path_finder is not None:
                if path_finder.abbrev:
                    path_geo = path_finder.abbrev
                else:
                    path_geo = path_finder.name
                human_base = path_geo + Geo.delimiter + human_base
                path_finder = path_finder.path_parent
        else:
            human_base += Geo.delimiter

        return (human_base +
                abbrev if abbrev else name).lower().replace(' ', '_')

    def derive_key(self):
        '''Derive key from a geo instance

        Return the registry key used by the Trackable metaclass from a
        geo instance. The key is the human_id.
        '''
        return self.human_id

    def __init__(self, name, abbrev=None, path_parent=None, human_base=None,
                 the_prefix=None, geo_type=None, descriptor=None,
                 parents=[], children=[], total_pop=None, urban_pop=None):
        self.name = name
        self.abbrev = abbrev
        self.path_parent = path_parent
        self.human_id = Geo.create_key(name=name, abbrev=abbrev,
                                       path_parent=path_parent,
                                       human_base=human_base)
        if the_prefix is not None:
            self.the_prefix = the_prefix
        else:
            nstr = self.name.lower()
            self.the_prefix = (nstr.find('states') > -1 or
                               nstr.find('islands') > -1 or
                               nstr.find('republic') > -1)
        self.geo_type = geo_type
        self.descriptor = descriptor
        self.parents = parents
        self.children = children
        self.total_pop = total_pop
        self.urban_pop = urban_pop

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '<{cls}: {geo!r}>'.format(cls=cls_name, geo=self.human_id)

    def __str__(self):
        return '{prefix}{name}'.format(
                prefix='The ' if self.the_prefix else '',
                name=self.name)

# class GeoCode(BaseGeoModel, AutoTableMixin):
#     geo_id
#     code - 4805000
#     code_type - FIPS
