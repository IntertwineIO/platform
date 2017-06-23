#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from collections import OrderedDict, namedtuple
from functools import reduce

from sqlalchemy import Column, ForeignKey, Index, Table, desc, orm, types
from sqlalchemy.orm.collections import attribute_mapped_collection

from intertwine import IntertwineModel
from intertwine.exceptions import AttributeConflict, CircularReference
from intertwine.utils.mixins import JsonProperty
from intertwine.utils.tools import define_constants_at_module_scope

# BaseGeoModel = make_declarative_base(Base=ModelBase, Meta=Trackable)
BaseGeoModel = IntertwineModel


class GeoID(BaseGeoModel):
    '''
    Geo ID base class

    Used to map geos (by level) to 3rd party IDs and vice versa.
    '''
    LEVEL = 'level'
    STANDARD = 'standard'
    CODE = 'code'

    FIPS = 'FIPS'  # Federal Information Processing Series (formerly Standard)
    ANSI = 'ANSI'  # American National Standards Institute
    ISO_A2 = 'ISO_A2'  # ISO 3166-1 alpha-2
    ISO_A3 = 'ISO_A3'  # ISO 3166-1 alpha-3
    ISO_N3 = 'ISO_N3'  # ISO 3166-1 numeric-3
    CSA_2010 = 'CSA_2010'  # Combined Statistical Area, 2010
    CBSA_2010 = 'CBSA_2010'  # Core Based Statistical Area, 2010

    STANDARDS = {FIPS, ANSI, ISO_A2, ISO_A3, ISO_N3, CSA_2010, CBSA_2010}

    level_id = Column(types.Integer, ForeignKey('geo_level.id'))
    # level relationship defined via backref on GeoLevel.ids

    _standard = Column(STANDARD, types.String(20))  # FIPS, ANSI, etc.
    _code = Column(CODE, types.String(20))  # 4805000, 02409761

    # Querying use cases:
    #
    # 1. Fetch the geo level (e.g. DC as a place) for a particular
    #    id code (e.g. FIPS 4805000)
    #    cols: standard, code
    # 2. Fetch the id code for a particular geo level and standard
    #    cols: level, standard
    __table_args__ = (Index('ux_geo_id:standard+code',
                            # ux for unique index
                            STANDARD,
                            CODE,
                            unique=True),
                      # Index('ux_geo_id:level+standard',
                      #       # ux for unique index
                      #       LEVEL,
                      #       STANDARD,
                      #       unique=True),
                      )

    Key = namedtuple('GeoIDKey', (STANDARD, CODE))

    @classmethod
    def create_key(cls, standard, code, **kwds):
        '''Create Trackable key (standard/code tuple) for a geo ID'''
        return cls.Key(standard, code)

    def derive_key(self):
        '''Derive Trackable key (standard/code tuple) from a geo ID'''
        return self.__class__.Key(self.standard, self.code)

    @property
    def standard(self):
        return self._standard

    @standard.setter
    def standard(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._standard is not None:  # Not during __init__()
            # ensure key is new
            key = GeoID.create_key(standard=val, code=self.code)
            inst = GeoID.tget(key)
            if inst is not None and inst is not self:
                raise ValueError('Key already exists: {}'.format(key))
            # update registry with new key
            GeoID.unregister(self)
            GeoID[key] = self

        self._standard = val  # set new value last

    standard = orm.synonym('_standard', descriptor=standard)

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._code is not None:  # Not during __init__()
            # ensure key is new
            key = GeoID.create_key(standard=self.standard, code=val)
            inst = GeoID.tget(key)
            if inst is not None and inst is not self:
                raise ValueError('Key already exists: {}'.format(key))
            # update registry with new key
            GeoID.unregister(self)
            GeoID[key] = self

        self._code = val  # set new value last

    code = orm.synonym('_code', descriptor=code)

    def __init__(self, level, standard, code):
        '''Initialize a new geo ID'''
        if standard not in self.STANDARDS:
            raise ValueError('Unknown standard: {}'.format(standard))
        if not code:
            raise ValueError('Invalid code: {}'.format(code))
        if not level:
            raise ValueError('Invalid level: {}'.format(level))
        self.standard = standard
        self.code = code

        # Must follow standard assignment to create key for GeoLevel.ids
        self.level = level


class GeoLevel(BaseGeoModel):
    '''
    Base class for geo levels

    A geo level contains level information for a particular geo, where
    the level indicates the type of geo and/or where the geo fits in the
    geo tree. The levels were designed to allow global normalization and
    include country, subdivision1..subdivisionN, combined_area,
    core_area, and place.

    The designation indicates how the geo is described at the given
    level. For example, in the U.S., the subdivision1 geos are mainly
    states, but also includes some territories (e.g. Puerto Rico) and a
    federal district (DC).

    A single geo may have multiple levels. For example, San Francisco
    has a consolidated government that is both a county (subdivision2)
    and a city (place). DC is simultaneously a federal district
    (subdivision1), a county equivalent (subdivision2), a county
    subdivision equivalent (subdivision3), and a city
    (place).
    '''
    GEO = 'geo'
    LEVEL = 'level'

    COUNTRY = 'country'
    SUBDIVISION1 = 'subdivision1'
    SUBDIVISION2 = 'subdivision2'
    SUBDIVISION3 = 'subdivision3'
    COMBINED_AREA = 'combined_area'
    CORE_AREA = 'core_area'
    PLACE = 'place'
    SUBPLACE = 'subplace'

    DOWN = OrderedDict((
        (COUNTRY, (SUBDIVISION1,)),
        (SUBDIVISION1, (COMBINED_AREA, CORE_AREA, SUBDIVISION2, PLACE)),
        (COMBINED_AREA, (CORE_AREA, SUBDIVISION2, PLACE)),
        (CORE_AREA, (SUBDIVISION2, PLACE)),
        (SUBDIVISION2, (SUBDIVISION3, PLACE,)),
        (SUBDIVISION3, (PLACE,)),
        (PLACE, (SUBPLACE, )),
        (SUBPLACE, ())
    ))

    UP = OrderedDict((
        (SUBPLACE, (PLACE, SUBDIVISION3, SUBDIVISION2, CORE_AREA,
                    COMBINED_AREA, SUBDIVISION1)),
        (PLACE, (SUBDIVISION2, CORE_AREA, COMBINED_AREA, SUBDIVISION1)),
        (SUBDIVISION3, (SUBDIVISION2, CORE_AREA, COMBINED_AREA, SUBDIVISION1)),
        (SUBDIVISION2, (CORE_AREA, COMBINED_AREA, SUBDIVISION1)),
        (CORE_AREA, (COMBINED_AREA, SUBDIVISION1)),
        (COMBINED_AREA, (SUBDIVISION1,)),
        (SUBDIVISION1, (COUNTRY,)),
        (COUNTRY, ())
    ))

    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    # _geo relationship defined via backref on Geo._levels

    # level values: country, subdivision1, subdivision2, place, csa, cbsa
    _level = Column(LEVEL, types.String(30))

    # designations: state, county, city, etc. (lsad for place)
    designation = Column(types.String(60))

    # ids is a dictionary where GeoID.standard is the key
    ids = orm.relationship(
        'GeoID',
        collection_class=attribute_mapped_collection(GeoID.STANDARD),
        cascade='all, delete-orphan',
        backref=GeoID.LEVEL)

    jsonified_ids = JsonProperty(name='ids', method='jsonify_ids')

    def jsonify_ids(self, nest, hide, **json_kwargs):
        geoids_json = OrderedDict()
        hidden = set(hide)
        hidden |= {'id', GeoID.LEVEL, GeoID.STANDARD}  # union update
        for standard, geoid in self.ids.items():
            geoids_json[standard] = geoid.jsonify(nest=True, hide=hidden,
                                                  **json_kwargs)
        return geoids_json

    # Querying use cases:
    #
    # 1. Fetch a particular level (e.g. subdivision2) for a particular
    #    geo (e.g. Travis County) to determine designation (e.g. county)
    #    or to map to 3rd-party IDs (e.g. FIPS codes)
    #    cols: geo_id, level
    # 2. For a particular geo (e.g. Washington, D.C.), obtain all the
    #    levels (e.g. subdivision1, subdivision2, place)
    #    cols: geo_id
    # 3. For a particular level (e.g. subdivision2), obtain all the geos
    #    (this will often be a large number).
    #    cols: level
    __table_args__ = (Index('ux_geo_level',
                            # ux for unique index
                            'geo_id',
                            LEVEL,
                            unique=True),)

    Key = namedtuple('GeoLevelKey', (GEO, LEVEL))

    @classmethod
    def create_key(cls, geo, level, **kwds):
        '''Create Trackable key (geo/level tuple) for a geo level'''
        return cls.Key(geo, level)

    def derive_key(self):
        '''Derive Trackable key (geo/level tuple) from a geo level'''
        return self.__class__.Key(self.geo, self.level)

    @property
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._geo is not None:  # Not during __init__()
            # ensure key is new
            key = GeoLevel.create_key(geo=val, level=self.level)
            inst = GeoLevel.tget(key)
            if inst is not None and inst is not self:
                raise ValueError('Key already exists: {}'.format(key))
            # update registry with new key
            GeoLevel.unregister(self)
            GeoLevel[key] = self  # register the new key

        self._geo = val  # set new value last

    geo = orm.synonym('_geo', descriptor=geo)

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._level is not None:  # Not during __init__()
            # ensure key is new
            key = GeoLevel.create_key(geo=self.geo, level=val)
            inst = GeoLevel.tget(key)
            if inst is not None and inst is not self:
                raise ValueError('Key already exists: {}'.format(key))
            # update registry with new key
            GeoLevel.unregister(self)
            GeoLevel[key] = self  # register the new key

        self._level = val  # set new value last

    level = orm.synonym('_level', descriptor=level)

    def __init__(self, geo, level, designation=None):
        '''Initialize a new geo level'''
        self.level = level
        self.designation = designation

        # Must follow level assignment to provide key for Geo.levels
        self.geo = geo


class GeoData(BaseGeoModel):
    '''Base class for geo data'''
    GEO = 'geo'

    TOTAL_POP = 'total_pop'
    URBAN_POP = 'urban_pop'
    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    LAND_AREA = 'land_area'
    WATER_AREA = 'water_area'

    SUMMED_FIELDS = (TOTAL_POP, URBAN_POP, LAND_AREA, WATER_AREA)
    AREA_AVERAGED_FIELDS = (LATITUDE, LONGITUDE)

    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    _geo = orm.relationship('Geo', back_populates='_data')

    # Enables population-based prioritization and urban/rural flagging
    total_pop = Column(types.Integer)
    urban_pop = Column(types.Integer)

    # Enables distance calculations
    latitude = Column(types.Float)
    longitude = Column(types.Float)

    # Enables lat/long calculation of combined geos (in sq kilometers)
    land_area = Column(types.Float)
    water_area = Column(types.Float)

    # future: demographics, geography, climate, etc.

    __table_args__ = (Index('ux_geo_data:geo_id',
                            # ux for unique index
                            'geo_id',
                            unique=True),
                      Index('ix_geo_data:total_pop',
                            # ix for index
                            'total_pop'),)

    @property
    def total_area(self):
        return self.land_area + self.water_area

    @property
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._geo is not None:  # Not during __init__()
            # ensure key is new
            key = GeoData.create_key(geo=val)
            inst = GeoData.tget(key)
            if inst is not None and inst is not self:
                raise ValueError('Key already exists: {!r}'.format(key))
            # update registry with new key
            GeoData.unregister(self)
            GeoData[key] = self

        self._geo = val  # set new value last

    geo = orm.synonym('_geo', descriptor=geo)

    Key = namedtuple('GeoDataKey', (GEO,))

    @classmethod
    def create_key(cls, geo, **kwds):
        '''Create Trackable key (geo 1-tupled) for a geo data'''
        return cls.Key(geo)

    def derive_key(self):
        '''Derive Trackable key (geo 1-tupled) from a geo data'''
        return self.__class__.Key(self.geo)

    @classmethod
    def create_parent_data(cls, parent_geo, child_level=None):
        '''
        Create parent data

        Constructor for aggregating geo data for a parent geo from its
        children geos at a given level.

        IO:
        parent_geo:
            The parent geo for which data is to be aggregated.

        child_level=None:
            The level of the children whose data is to be aggregated.
            Default of None includes all children data.

        returns:
            A GeoData instance in which values are aggregated from the
            parent_geo's children at the given level, if there are any.
            Or None if there are no children.
        '''
        children = (
            parent_geo.children.all() if child_level is None
            else [child for child in parent_geo.children
                  if child.levels.get(child_level) is not None])

        if not children:
            return None

        data = {field: sum((child.data[field] for child in children))
                for field in cls.SUMMED_FIELDS}

        for field in cls.AREA_AVERAGED_FIELDS:
            data[field] = (sum((child.data.total_area * child.data[field]
                                for child in children)) * 1.0 /
                           sum((child.data.total_area for child in children)))

        return cls(parent_geo, **data)

    def __init__(self, geo, total_pop=None, urban_pop=None,
                 longitude=None, latitude=None,
                 land_area=None, water_area=None):
        '''Initialize a new geo level'''
        self.geo = geo
        self.total_pop = total_pop
        self.urban_pop = urban_pop
        self.latitude = latitude
        self.longitude = longitude
        self.land_area = land_area
        self.water_area = water_area


geo_parent_child_association_table = Table(
    'geo_parent_child_association', BaseGeoModel.metadata,
    Column('parent_id', types.Integer, ForeignKey('geo.id')),
    Column('child_id', types.Integer, ForeignKey('geo.id'))
)


geo_alias_association_table = Table(
    'geo_alias_association', BaseGeoModel.metadata,
    Column('alias_target_id', types.Integer, ForeignKey('geo.id')),
    Column('alias_id', types.Integer, ForeignKey('geo.id'))
)


class Geo(BaseGeoModel):
    '''
    Geo

    A 'geo' is a geographical entity, legal or otherwise. Geos may have
    GeoData and one or more GeoLevels, which in turn may have one or
    more GeoIDs.

    Each geo has a human_id used in its URI and composed as follows:

        <path>/<transformed(<abbrev or name>[ <qualifier>])>

    The abbrev, name, and qualifier are transformed as follows:
        '.' -> ''
        '/' or ', ' -> '-'
        ' ' -> '_'

    level          abbrev/name      path_parent   human_id
    --------------------------------------------------------------------
    country        U.S.               (none)      us
    subdivision1   MA                   US        us/ma
    combined_area  Greater Boston       MA        us/ma/greater_boston
    core_area      Boston Area          MA        us/ma/boston_area
    subdivision2   Norfolk County       MA        us/ma/norfolk_county
    place          Westwood             MA        us/ma/westwood
    subdivision3   Westwood       Norfolk County  us/ma/norfolk_county/westwood

    I/O:
    name:
        The primary name of the Geo, used for display and in the
        human_id, unless the geo has an abbreviation.

    abbrev=None:
        The common abbreviation of the Geo, which replaces the name in
        the human_id.

    qualifier=None:
        Distinguish geos that share the same name/abbreviation and path
        for the purpose of creating a unique human_id. For such geos in
        the US, the qualifier takes these forms:

        geo level     qualifier
        ----------------------------------------------------------------
        place         <geo level designation> in <subdivision2 name>
        subdivision3  <geo level designation>

        Examples:
        Geo['us/md/chevy_chase_cdp_in_montgomery_county']
        Geo['us/md/chevy_chase_town_in_montgomery_county']

    path_parent=None:
        Indicate another geo as an immediate parent for the purpose of
        determining the path.  The human_id of a geo's path_parent is
        the path of the geo's human_id.

    alias_target=None:
        Identify the geo as an alias of the specified target geo. If
        no path_parent is provided, the alias_target's path_parent is
        used instead. A value of None indicates the geo is not an alias.

    uses_the=None:
        A boolean indicating the name should begin with 'the ' when
        displayed. It is derived automatically by default: True if the
        name includes 'states', 'islands', 'republic' or 'district', and
        False otherwise. When provided, a value serves as an override,
        but it will be recalculated whenever the name changes.

    data=None:
        Create an associated GeoData instance from JSON, a field/value
        map excluding geo. When not provided, data is aggregated from
        the geo's children at the level specified by child_data_level.

    levels=None:
        Create associated GeoLevel instances. The JSON is a dictionary
        of GeoLevel field/value maps keyed by level, where the GeoLevel
        maps exclude geo and level.

    parents=None:
        List of geos to be associated as parents of the geo.

    children=None:
        List of geos to be associated as children of the geo.

    child_data_level=None:
        The level of the geo's children whose data is to be aggregated
        to calculate the geo's data. If None, all children are included.
        Only used if data is not provided as a parameter.
    '''
    HUMAN_ID = 'human_id'

    PARENTS = 'parents'
    CHILDREN = 'children'
    PATH_CHILDREN = 'path_children'
    ALIASES = 'aliases'
    ALIAS_TARGETS = 'alias_targets'

    RELATIONS = {PARENTS, CHILDREN, PATH_CHILDREN, ALIASES, ALIAS_TARGETS}

    DYNAMIC = 'dynamic'
    NOT_DYNAMIC = 'not_dynamic'

    DATA = 'data'
    LEVELS = 'levels'

    uses_the = Column(types.Boolean)  # e.g. 'The United States'
    _name = Column('name', types.String(60))
    _abbrev = Column('abbrev', types.String(20))
    _qualifier = Column('qualifier', types.String(60))
    _human_id = Column(HUMAN_ID, types.String(200), index=True, unique=True)

    jsonified_display = JsonProperty(
        name='display', after=HUMAN_ID, method='display', kwargs=dict(
            max_path=1, show_the=True, show_abbrev=False, abbrev_path=True))

    _alias_targets = orm.relationship(
        'Geo',
        secondary='geo_alias_association',
        primaryjoin='Geo.id==geo_alias_association.c.alias_id',
        secondaryjoin='Geo.id==geo_alias_association.c.alias_target_id',
        lazy='joined',
        # post_update=True,  # Needed to avoid CircularDependencyError?
        # order_by='desc(Geo.data.total_pop)',
        # order_by=lambda: desc(Geo.data.total_pop),
        backref=orm.backref(
            '_aliases',
            lazy='dynamic',
            order_by='Geo.name',
        ))

    _data = orm.relationship('GeoData', uselist=False, back_populates='_geo')

    # _levels is a dictionary where GeoLevel.level is the key
    _levels = orm.relationship(
        'GeoLevel',
        collection_class=attribute_mapped_collection(GeoLevel.LEVEL),
        cascade='all, delete-orphan',
        backref='_geo')

    path_parent_id = Column(types.Integer, ForeignKey('geo.id'))
    _path_parent = orm.relationship(
        'Geo',
        primaryjoin=('Geo.path_parent_id==Geo.id'),
        remote_side='Geo.id',
        lazy='joined',
        backref=orm.backref(PATH_CHILDREN, lazy='dynamic'))

    parents = orm.relationship(
        'Geo',
        secondary='geo_parent_child_association',
        primaryjoin='Geo.id==geo_parent_child_association.c.child_id',
        secondaryjoin='Geo.id==geo_parent_child_association.c.parent_id',
        lazy='dynamic',
        # collection_class=attribute_mapped_collection('bottom_level_key'),
        backref=orm.backref(
            CHILDREN,
            lazy='dynamic',
            # collection_class=attribute_mapped_collection(
            #     'top_level_key'),
            # order_by='Geo.name'
        ))

    jsonified_parents = JsonProperty(name=PARENTS,
                                     method='jsonify_related_geos',
                                     kwargs=dict(relation=PARENTS))

    jsonified_children = JsonProperty(name=CHILDREN,
                                      method='jsonify_related_geos',
                                      kwargs=dict(relation=CHILDREN))

    jsonified_path_children = JsonProperty(name=PATH_CHILDREN, show=False)

    PATH_DELIMITER = '/'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        # Not during __init__() and there's no abbreviation used instead
        if self.human_id is not None and self.abbrev is None:
            key = Geo.create_key(name=val,
                                 qualifier=self.qualifier,
                                 path_parent=self.path_parent,
                                 alias_targets=self.alias_targets)
            self.human_id = key.human_id
        nstr = val.lower()
        self.uses_the = (nstr.find('states') > -1 or
                         nstr.find('islands') > -1 or
                         nstr.find('republic') > -1 or
                         nstr.find('district') > -1)
        self._name = val  # set name last

    name = orm.synonym('_name', descriptor=name)

    @property
    def abbrev(self):
        return self._abbrev

    @abbrev.setter
    def abbrev(self, val):
        if self.human_id is not None:  # Not during __init__()
            key = Geo.create_key(name=self.name, abbrev=val,
                                 qualifier=self.qualifier,
                                 path_parent=self.path_parent,
                                 alias_targets=self.alias_targets)
            self.human_id = key.human_id
        self._abbrev = val  # set abbrev last

    abbrev = orm.synonym('_abbrev', descriptor=abbrev)

    @property
    def qualifier(self):
        return self._qualifier

    @qualifier.setter
    def qualifier(self, val):
        if self.human_id is not None:  # Not during __init__()
            key = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                 qualifier=val,
                                 path_parent=self.path_parent,
                                 alias_targets=self.alias_targets)
            self.human_id = key.human_id
        self._qualifier = val  # set qualifier last

    qualifier = orm.synonym('_qualifier', descriptor=qualifier)

    @property
    def path_parent(self):
        return self._path_parent

    @path_parent.setter
    def path_parent(self, val):
        if self.human_id is not None:  # Not during __init__()
            key = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                 qualifier=self.qualifier,
                                 path_parent=val,
                                 alias_targets=self.alias_targets)
            self.human_id = key.human_id
        self._path_parent = val

    path_parent = orm.synonym('_path_parent', descriptor=path_parent)

    @property
    def alias_targets(self):
        return sorted(self._alias_targets, reverse=True,
                      key=lambda g: g.data.total_pop if g.data else -1)

    @alias_targets.setter
    def alias_targets(self, alias_targets):
        current_targets = set(self._alias_targets)
        new_targets = set(alias_targets)

        removed_targets = current_targets - new_targets
        for alias_target in removed_targets:
            self.remove_alias_target(alias_target)

        added_targets = new_targets - current_targets
        for alias_target in added_targets:
            self.add_alias_target(alias_target)

    alias_targets = orm.synonym('_alias_targets', descriptor=alias_targets)

    @property
    def aliases(self):
        return self._aliases

    @aliases.setter
    def aliases(self, aliases):
        current_aliases = set(self._aliases)
        new_aliases = set(aliases)

        removed_aliases = current_aliases - new_aliases
        for alias in removed_aliases:
            alias.remove_alias_target(self)

        added_aliases = new_aliases - current_aliases
        for alias in added_aliases:
            alias.add_alias_target(self)

    aliases = orm.synonym('_aliases', descriptor=aliases)

    def add_alias_target(self, val):
        if val is self:
            raise CircularReference(attr='alias_target', inst=self, value=val)

        alias_targets = self.alias_targets
        if val in alias_targets:  # nothing to do
            return

        aliases = self.aliases.all()
        if aliases:
            if val in aliases:  # val is an alias of self
                val.promote_to_alias_target()
            else:
                for alias in aliases:
                    alias.add_alias_target(val)  # recurse on each alias
                self.add_alias_target(val)  # recurse on self w/o any aliases
            return
        # all aliases of self have been redirected to val
        assert not aliases
        # val cannot be an alias as self would then be an alias of an alias
        assert not val.alias_targets

        # if self is becoming an alias, transfer references
        if not alias_targets:
            self.transfer_references(val)

        self._alias_targets.append(val)

    def remove_alias_target(self, val):
        self._alias_targets.remove(val)

    def promote_to_alias_target(self):
        '''
        Promote alias to alias_target

        Convert an alias (A) with one target (B) into an alias target.
        The existing target (B) is converted into an alias of the new
        target (A), transferring references in the process. All
        aliases of the existing target (B) become aliases of the new
        target (A). Has no effect if the geo (A) is not an alias. The
        alias (A) may not have multiple targets because each target
        could have its own set of references, so data would be lost.
        '''
        alias_targets = self.alias_targets
        if not alias_targets:  # self is already an alias_target
            return

        if len(alias_targets) > 1:
            raise ValueError('An alias for multiple geos cannot be promoted')

        at = alias_targets[0]
        # an alias cannot itself have an alias
        assert not at.alias_targets

        self.alias_targets = []
        for alias in at.aliases.all():
            alias.remove_alias_target(at)
            alias.add_alias_target(self)

        # transfer references occurs here
        at.add_alias_target(self)

    def transfer_references(self, geo):
        '''
        Transfer references

        Utility function for transferring references to another geo, for
        example, when making a geo an alias of another geo. Path
        references remain unchanged.
        '''
        attributes = {self.PARENTS: (self.DYNAMIC, []),
                      self.CHILDREN: (self.DYNAMIC, []),
                      self.DATA: (self.NOT_DYNAMIC, None),
                      self.LEVELS: (self.NOT_DYNAMIC, {})}

        for attr, (load, empty) in attributes.items():
            # load, rel = attributes[attr]
            self_attr_val = getattr(self, attr)
            if load == self.DYNAMIC:
                self_attr_val = self_attr_val.all()
            if self_attr_val:
                geo_attr_val = getattr(geo, attr)
                if load == self.DYNAMIC:
                    geo_attr_val = geo_attr_val.all()
                if geo_attr_val:
                    raise AttributeConflict(inst1=self, attr1=attr,
                                            inst2=geo, attr2=attr)
                setattr(geo, attr, self_attr_val)
                setattr(self, attr, empty)

    @property
    def human_id(self):
        return self._human_id

    @human_id.setter
    def human_id(self, val):
        if val is None:
            raise ValueError('human_id cannot be set to None')

        if self._human_id is not None:  # Not during __init__()
            # ensure key is new
            key = Geo.Key(human_id=val)
            inst = Geo.tget(key)
            if inst is not None and inst is not self:
                raise ValueError('Key already exists: {!r}'.format(key))
            # update registry with new key
            Geo.unregister(self)
            Geo[key] = self

        self._human_id = val  # set human_id last
        # recursively propagate change to path_children
        for pc in self.path_children:
            key = Geo.create_key(name=pc.name, abbrev=pc.abbrev,
                                 qualifier=pc.qualifier,
                                 path_parent=self,
                                 alias_targets=pc.alias_targets)
            pc.human_id = key.human_id
    human_id = orm.synonym('_human_id', descriptor=human_id)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, val):
        if val is None:
            self._data = None
            return
        val.geo = self  # invoke GeoData.geo setter

    data = orm.synonym('_data', descriptor=data)

    jsonified_data = JsonProperty(name=DATA, method='jsonify_data')

    def jsonify_data(self, nest, hide, **json_kwargs):
        data = self.data
        hidden = set(hide)
        hidden |= {'id', GeoData.GEO}  # union update
        return (data.jsonify(nest=True, hide=hidden, **json_kwargs)
                if data else None)

    @property
    def levels(self):
        return self._levels

    @levels.setter
    def levels(self, val):
        for geo_level in tuple(val.values()):
            geo_level.geo = self  # invoke GeoLevel.geo setter

    levels = orm.synonym('_levels', descriptor=levels)

    jsonified_levels = JsonProperty(name=LEVELS, method='jsonify_levels')

    def jsonify_levels(self, nest, hide, **json_kwargs):
        levels_json = OrderedDict()
        levels = self.levels
        hidden = set(hide)  # copy to just affect levels
        hidden |= {'id', GeoLevel.GEO, GeoLevel.LEVEL}  # union update
        for lvl in GeoLevel.DOWN:
            if lvl in levels:
                levels_json[lvl] = levels[lvl].jsonify(nest=True, hide=hidden,
                                                       **json_kwargs)
        return levels_json

    @property
    def level_down_keys(self):
        return (lvl for lvl in GeoLevel.DOWN if lvl in set(self.levels))

    jsonified_level_down_keys = JsonProperty(name='level_down_keys',
                                             after=LEVELS)

    @property
    def level_up_keys(self):
        return (lvl for lvl in GeoLevel.UP if lvl in set(self.levels))

    jsonified_level_up_keys = JsonProperty(name='level_up_keys', show=False)

    @property
    def top_level_key(self):
        return next(self.level_down_keys) if self.levels else None

    jsonified_top_level_key = JsonProperty(name='top_level_key', show=False)

    @property
    def bottom_level_key(self):
        return next(self.level_up_keys) if self.levels else None

    jsonified_bottom_level_key = JsonProperty(name='bottom_level_key',
                                              show=False)

    Key = namedtuple('GeoKey', (HUMAN_ID,))

    @classmethod
    def create_key(cls, name=None, abbrev=None, qualifier=None,
                   path_parent=None, alias_targets=None, **kwds):
        '''
        Create Trackable key (human_id 1-tupled) for a geo

        The key is created by concatenating the human_id of the
        path_parent with the name, separated by the Geo delimiter. If an
        abbreviation is provided, it replaces the name in the key.

        If a qualifier is provided, it is appended, delimited by a
        space. If no path_parent and a single alias_target, the
        path_parent of the alias_target is used instead. Prohibited
        characters and sequences are either replaced or removed.
        '''
        if path_parent is None and alias_targets:
            if len(alias_targets) > 1:
                raise ValueError('Path parent must be provided if '
                                 'multiple alias targets')
            path_parent = alias_targets[0].path_parent

        path = path_parent.human_id + Geo.PATH_DELIMITER if path_parent else ''
        nametag = u'{abbrev_or_name}{qualifier}'.format(
            abbrev_or_name=abbrev if abbrev else name,
            qualifier=' ' + qualifier if qualifier else '')
        nametag = (nametag.replace('.', '').replace(', ', '-')
                   .replace('/', '-').replace(' ', '_').lower())
        return cls.Key(path + nametag)

    def derive_key(self):
        '''Derive Trackable key (human_id 1-tupled) from a geo'''
        return self.__class__.Key(self.human_id)

    def __init__(self, name, abbrev=None, qualifier=None, path_parent=None,
                 alias_targets=None, aliases=None, uses_the=None,
                 parents=None, children=None, data=None, levels=None,
                 child_data_level=None):
        self.name = name
        if uses_the is not None:  # Override calculated value, if provided
            self.uses_the = uses_the
        self.abbrev = abbrev
        self.qualifier = qualifier

        if path_parent is None and alias_targets:
            if len(alias_targets) > 1:
                raise ValueError('Path parent must be provided if '
                                 'multiple alias targets')
            path_parent = alias_targets[0].path_parent

        self.path_parent = path_parent

        if alias_targets and aliases:
            raise ValueError('An alias may not have any aliases')
        self.alias_targets = alias_targets or []
        self.aliases = aliases or []

        key = Geo.create_key(name=self.name, abbrev=self.abbrev,
                             qualifier=self.qualifier,
                             path_parent=self.path_parent,
                             alias_targets=self.alias_targets)
        self.human_id = key.human_id
        # if self.alias_targets:
        #     return

        self.parents = parents or []
        self.children = children or []

        self.data = (
            GeoData(geo=self, **data) if data else
            GeoData.create_parent_data(
                self, child_level=child_data_level) if self.children else None)

        self.levels = {}
        if levels:
            for lvl, glvl in levels.items():
                new_glvl = glvl
                # The geo for the geolevel should always be self. If a geo
                # key is provided, make sure it matches and remove it.
                glvl_geo = new_glvl.get(GeoLevel.GEO, None)
                if glvl_geo == self.trepr(tight=True, raw=False):
                    new_glvl = glvl.copy()
                    new_glvl.pop(GeoLevel.GEO)
                elif glvl_geo is not None:
                    raise KeyError('Geo level json contains a geo key that '
                                   'does not match geo being created')
                # The level for the geolevel should always be the key. If a
                # level is provided, make sure it matches and remove it.
                glvl_level = new_glvl.get(GeoLevel.LEVEL, None)
                if glvl_level == lvl:
                    if new_glvl == glvl:
                        new_glvl = glvl.copy()
                    new_glvl.pop(GeoLevel.LEVEL)

                elif glvl_level is not None:
                    raise KeyError('Geo level json contains a level that '
                                   'does not match key for the geo level')
                self.levels[lvl] = GeoLevel(geo=self, level=lvl, **new_glvl)

    def __getitem__(self, key):
        return Geo[Geo.create_key(name=key, path_parent=self)]

    # __setitem__ is unnecessary and would be awkward since the key must
    # always be derived from the value

    def display(self, show_the=True, show_The=False, show_abbrev=True,
                show_qualifier=True, abbrev_path=True, max_path=float('Inf'),
                **json_kwargs):
        '''
        Generate text for displaying a geo to a user

        Returns a string derived from the name, abbrev, uses_the, and
        the geo path established by the path_parent. The following
        parameters affect the output:
        - show_the=True: The name of the geo is prefixed by 'the'
          (lowercase) if geo.uses_the; overriden by show_The (uppercase)
        - show_The=False: The name of the geo is prefixed by 'The'
          (uppercase) if geo.uses_the; overrides show_the (lowercase)
        - show_abbrev=True: The abbrev is displayed in parentheses after
          the geo name if the geo has an abbrev
        - show_qualifier=True: The qualifier is displayed after the geo
          name/abbrev if the geo has a qualifier
        - abbrev_path=True: Any path geos appearing after the geo are
          displayed in abbrev form, if one exists
        - max_path=Inf: Determines the number of levels in the geo path
          beyond the current geo that should be included. A value of 0
          limits the display to just the geo, a value of 1 includes the
          immediate path_parent, etc.
        '''
        geostr = []
        geo = self
        plvl = 0
        while geo is not None and plvl <= max_path:

            the = ('The ' if geo.uses_the and show_The else (
                   'the ' if geo.uses_the and show_the else ''))
            abbrev = (u' ({})'.format(geo.abbrev)
                      if geo.abbrev and show_abbrev else '')
            qualifier = (u' {}'.format(geo.qualifier)
                         if geo.qualifier and show_qualifier else '')
            if plvl == 0:
                geostr.append(u'{the}{name}{abbrev}{qualifier}'.format(
                    the=the, name=geo.name, abbrev=abbrev,
                    qualifier=qualifier))
            else:
                nametag = (geo.abbrev if abbrev_path and geo.abbrev
                           else geo.name)
                geostr.append(nametag)

            geo = geo.path_parent
            plvl += 1
        return ', '.join(geostr)

    def is_known_by(self, match_string, full_name=True, case_sensitive=True,
                    include_abbrev=True, include_aliases=True):
        '''
        Is Known By

        Determine if match string is a name by which the geo is known.

        I/O:
        match_string: string used for name-matching
        full_name=True: if True, match string must span the full name
        case_sensitive=True: if True, matches must be case-sensitive
        include_abbrev=True: if True, geo abbrev may be matched
        include_aliases=True: if True, aliases may be matched
        return: True iff match string matches geo name/abbrev/aliases
        '''
        names = {self.name}
        if include_abbrev and self.abbrev:
            names.add(self.abbrev)
        if include_aliases and self.aliases:
            names |= set(alias.name for alias in self.aliases)
            if include_abbrev:
                names |= set(alias.abbrev for alias in self.aliases
                             if alias.abbrev)

        if not case_sensitive:
            match_string = match_string.lower()
            names = {name.lower() for name in names}

        if full_name:
            return match_string in names

        for name in names:
            if match_string in name:
                return True

        return False

    @staticmethod
    def sorted(*geos):
        return sorted(geos, reverse=True,
                      key=lambda g: g.data.total_pop if g.data else -1)

    @staticmethod
    def get_largest_geo(*geos):
        geo_pop_tuples = ((geo, geo.data.total_pop) for geo in geos)
        largest = reduce(lambda x, y: x if x[1] > y[1] else y, geo_pop_tuples)
        return largest[0]

    def get_related_geos(self, relation, level=None):
        '''
        Get related geos (e.g. parents/children)

        Given a relation, returns a list of related geos in descending
        order by total population. Any geos missing data and/or levels
        (e.g. aliases) are excluded.

        I/O:
        relation: parents, children, path_children, etc.
        level=None: filter results by level, if provided
        '''
        if relation not in self.RELATIONS:
            raise ValueError('{rel} is not an allowed value for relation'
                             .format(rel=relation))
        if level:
            rv = (getattr(self, relation).join(Geo.data).join(Geo.levels)
                  .filter(GeoLevel.level == level)
                  .order_by(desc(GeoData.total_pop)).all())
        else:
            rv = (getattr(self, relation).join(Geo.data)
                  .order_by(desc(GeoData.total_pop)).all())

        return rv

    def jsonify_related_geos(self, relation, **json_kwargs):
        '''
        Jsonify related geos by level

        Given a relation (e.g. parents/children), returns an ordered
        dictionary of geo reprs stratified (keyed) by level. The levels
        are ordered top to bottom for children and bottom to top for
        parents. Within each level, the geos are listed in descending
        order by total population. Any geos that are missing data and/or
        levels (e.g. aliases) are excluded.

        I/O:
        tight=True: make all repr values tight (without whitespace)
        raw=False: when True, add extra escapes (for printing)
        limit=10: cap list items within each level; no cap if negative
        '''
        limit = json_kwargs['limit']

        if relation not in self.RELATIONS:
            raise ValueError('{rel} is not an allowed value for relation'
                             .format(rel=relation))

        base_q = getattr(self, relation).join(Geo.data).join(Geo.levels)
        levels = (lvl for lvl in (
            GeoLevel.UP if relation == self.PARENTS else GeoLevel.DOWN))

        if limit < 0:
            rv = OrderedDict(
                (lvl, [self.jsonify_geo(g, **json_kwargs)
                       for g in base_q.filter(GeoLevel.level == lvl)
                       .order_by(desc(GeoData.total_pop)).all()])
                for lvl in levels)
        else:
            rv = OrderedDict(
                (lvl, [self.jsonify_geo(g, **json_kwargs)
                       for g in base_q.filter(GeoLevel.level == lvl)
                       .order_by(desc(GeoData.total_pop)).limit(limit).all()])
                for lvl in levels)

        for lvl, geos in list(rv.items()):
            if len(geos) == 0:
                rv.pop(lvl)

        return rv

    def jsonify_geo(self, geo, depth, **json_kwargs):
        '''Jsonify geo'''
        _json = json_kwargs['_json']
        tight = json_kwargs['tight']
        raw = json_kwargs['raw']

        geo_key = geo.trepr(tight=tight, raw=raw)
        if depth > 1 and geo_key not in _json:
            geo.jsonify(depth=depth - 1, **json_kwargs)

        return geo_key


define_constants_at_module_scope(__name__, GeoID, GeoID.STANDARDS)
define_constants_at_module_scope(__name__, GeoLevel, GeoLevel.DOWN)
define_constants_at_module_scope(__name__, Geo, Geo.RELATIONS)
