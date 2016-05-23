#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import orm, types, Column, ForeignKey, Index, Table, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from ..utils import AutoTableMixin, Trackable
from ..exceptions import AttributeConflict, CircularReference


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
    _abbrev = Column('abbrev', types.String(10))
    _human_id = Column('human_id', types.String(100), index=True, unique=True)
    path_parent_id = Column(types.Integer, ForeignKey('geo.id'))
    _path_parent = orm.relationship(
                'Geo',
                primaryjoin=('Geo.path_parent_id==Geo.id'),
                remote_side='Geo.id',
                backref=orm.backref('path_children', lazy='dynamic'),
                lazy='joined')

    the_prefix = Column(types.Boolean)
    main_geo_id = Column(types.Integer, ForeignKey('geo.id'))
    _main_geo = orm.relationship(
                'Geo',
                primaryjoin=('Geo.main_geo_id==Geo.id'),
                remote_side='Geo.id',
                backref=orm.backref('alternates', lazy='dynamic'),
                lazy='joined')

    # geo_type      us geo      us parents
    # country       US          None
    # subdivision1  state       US
    # csa           csa         state(s)
    # cbsa          cbsa        csa (if exists) and state(s)
    # subdivision2  county      cbsa (if exists) and state
    # place         place       county or counties (if exists) and state
    parents = orm.relationship(
                'Geo', secondary='geo_association',
                primaryjoin='Geo.id==geo_association.c.child_id',
                secondaryjoin='Geo.id==geo_association.c.parent_id',
                backref=orm.backref('children', lazy='dynamic'),
                lazy='joined')

    # geo_type = Column(types.String(30))

    # # city, town, village, parish, etc.; based on lsad for places
    # descriptor = Column(types.String(60))

    # # enables population-based prioritization and urban/rural designation
    # total_pop = Column(types.Integer)
    # urban_pop = Column(types.Integer)

    delimiter = '>'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        # Not during __init__() and there's no abbreviation used instead
        if self.human_id is not None and self.abbrev is None:
            self.human_id = Geo.create_key(name=val,
                                           path_parent=self.path_parent,
                                           main_geo=self.main_geo)
        nstr = val.lower()
        self.the_prefix = (nstr.find('states') > -1 or
                           nstr.find('islands') > -1 or
                           nstr.find('republic') > -1)
        self._name = val  # set name last

    name = orm.synonym('_name', descriptor=name)

    @property
    def abbrev(self):
        return self._abbrev

    @abbrev.setter
    def abbrev(self, val):
        if self.human_id is not None:  # Not during __init__()
            self.human_id = Geo.create_key(name=self.name, abbrev=val,
                                           path_parent=self.path_parent,
                                           main_geo=self.main_geo)
        self._abbrev = val  # set abbrev last

    abbrev = orm.synonym('_abbrev', descriptor=abbrev)

    @property
    def path_parent(self):
        return self._path_parent

    @path_parent.setter
    def path_parent(self, val):
        if self.human_id is not None:  # Not during __init__()
            self.human_id = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                           path_parent=val,
                                           main_geo=self.main_geo)
        self._path_parent = val

    path_parent = orm.synonym('_path_parent', descriptor=path_parent)

    @property
    def main_geo(self):
        return self._main_geo

    @main_geo.setter
    def main_geo(self, val):
        if val is None:
            self._main_geo = val
            return

        alts = self.alternates.all()
        if alts:
            if val in alts:
                val.promote_to_main()
            else:
                for alt in alts:
                    alt.main_geo = val  # recurse on alternates
                self.main_geo = val  # recurse on self w/o alternates
            return

        if val.main_geo is not None:  # val is an alternate, so redirect
            val = val.main_geo
            # a main_geo's alternates cannot themselves have alternates
            assert val.main_geo is None

        if val == self:
            raise CircularReference(attr='main_geo', inst=self, value=val)

        # more stringent requirements
        # self.path_parent = val.path_parent
        # self.parents = []
        # self.children = []
        self._main_geo = val

    main_geo = orm.synonym('_main_geo', descriptor=main_geo)

    @property
    def human_id(self):
        return self._human_id

    @human_id.setter
    def human_id(self, val):
        if val is None:
            raise ValueError('human_id cannot be set to None')
        if val == self.human_id:
            return
        # check if it's already registered by a different geo
        geo = Geo._instances.get(val, None)
        if geo is not None and geo is not self:
            raise NameError("'{}' is already registered.".format(val))
        if hasattr(self, '_human_id'):  # unregister old human_id
            # Default None since Trackable registers after Geo.__init__()
            Geo._instances.pop(self.human_id, None)
        Geo[val] = self  # register the new human_id
        self._human_id = val  # set human_id last
        # recursively propagate change to path_children
        for pc in self.path_children:
            pc.human_id = Geo.create_key(name=pc.name, abbrev=pc.abbrev,
                                         path_parent=self,
                                         main_geo=pc.main_geo)

    human_id = orm.synonym('_human_id', descriptor=human_id)

    @staticmethod
    def create_key(name=None, abbrev=None, path_parent=None, main_geo=None,
                   **kwds):
        '''Create key for a geo

        Return a registry key allowing the Trackable metaclass to look
        up a geo instance. The key is created by concatenating the
        human_id of the path_parent with the abbreviation or name
        provided, separated by the Geo delimiter. If no path_parent is
        provided, but there is a main_geo, the human_id of the
        main_geo's path_parent is used instead.
        '''
        if path_parent is None and main_geo is not None:
        # if main_geo is not None:
            path_parent = main_geo.path_parent
        human_base = '' if path_parent is None else (path_parent.human_id +
                                                     Geo.delimiter)
        return (human_base +
                (abbrev if abbrev else name)).lower().replace(' ', '_')

    def derive_key(self):
        '''Derive key from a geo instance

        Return the registry key used by the Trackable metaclass from a
        geo instance. The key is the human_id.
        '''
        return self.human_id

    def __init__(self, name, abbrev=None, path_parent=None, main_geo=None,
                 the_prefix=None, parents=[], children=[]):
                # geo_type=None, descriptor=None,
                # total_pop=None, urban_pop=None):
        self.name = name
        if the_prefix is not None:  # Override calculated value, if provided
            self.the_prefix = the_prefix
        self.abbrev = abbrev
        if path_parent is None and main_geo is not None:
            path_parent = main_geo.path_parent
        # if main_geo is not None:
        #     if path_parent is None:
        #         path_parent = main_geo.path_parent
        #     elif path_parent != main_geo.path_parent:
        #         raise AttributeConflict(attr1='path_parent',
        #                                 attr_val1=path_parent,
        #                                 attr2='main_geo',
        #                                 attr_val2=main_geo,
        #                                 inst=self)
        self.path_parent = path_parent
        self.main_geo = main_geo
        self.human_id = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                       path_parent=self.path_parent,
                                       main_geo=self.main_geo)
        # if self.main_geo is not None:
        #     return
        self.parents = parents
        self.children = children
        # self.geo_type = geo_type
        # self.descriptor = descriptor
        # self.total_pop = total_pop
        # self.urban_pop = urban_pop

    def promote_to_main(self):
        '''Promote geo's name/abbrev to the main geo

        Swap the geo's name/abbrev with the name/abbrev of the main geo.
        Has no effect if the geo is a main geo.
        '''
        mg = self.main_geo
        if mg is None:  # self is already a main_geo
            return
        # a main_geo's alternates cannot themselves have alternates
        assert mg.main_geo is None

        # CircularDependencyError on commit():
        # self.main_geo = None
        # alts = mg.alternates.all() + [mg]
        # for alt in alts:
        #     alt.main_geo = self

        # Set up temp names/abbrevs to prevent registry key clashes
        n1, a1 = '***NAME1***', '***ABBREV1***'
        n2, a2 = '***NAME2***', '***ABBREV2***'

        # Swap names/abbrevs for temps
        self.name, n1 = n1, self.name
        self.abbrev, a1 = a1, self.abbrev
        mg.name, n2 = n2, mg.name
        mg.abbrev, a2 = a2, mg.abbrev

        # Swap temps for names/abbrevs, reversing geos
        self.name, n2 = n2, self.name
        self.abbrev, a2 = a2, self.abbrev
        mg.name, n1 = n1, mg.name
        mg.abbrev, a1 = a1, mg.abbrev

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '<{cls}: {geo!r}>'.format(cls=cls_name, geo=self.human_id)

    def __str__(self):
        return '{prefix}{name}'.format(
                prefix='The ' if self.the_prefix else '',
                name=self.name)

# TODO: Implement alternate_names
# new Geo attribute: main_geo_id with main/alternates relationship
# values:
# None - geo is the main geo
# some other geo - geo is an alternate name for the other geo

# TODO: Create GeoType class to track geo types and descriptors
# class GeoType(BaseGeoModel, AutoTableMixin):
#     geo_id (foreign key, M to 1)
#     name - country, subdivision1, subdivision2, place, csa, cbsa
#     descriptor - state, county, city, etc. (lsad for place)

# TODO: Create GeoID class to map geos (by type) to 3rd party IDs
# class GeoMap(BaseGeoModel, AutoTableMixin):
#     geo_type_id (foreign key, M to 1)
#     id_type - FIPS, ANSI, etc.
#     id - 4805000, 02409761

# TODO: Create GeoData class to store data related to the geo
# class GeoData(BaseGeoModel, AutoTableMixin):
#     geo_id (foreign key, 1 to 1)
#     total_pop
#     urban_pop
#     other attributes related to demographics, geography, climate, etc.
