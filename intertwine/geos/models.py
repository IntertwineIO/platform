#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import OrderedDict

from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import desc, orm, types, Column, ForeignKey, Index, Table
from sqlalchemy.orm.collections import attribute_mapped_collection

from ..utils import AutoTableMixin, stringify, Trackable
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

    # e.g. 'The United States'
    the_prefix = Column(types.Boolean)

    # TODO: Add 'pre' and 'post' and rename 'the_prefix' to 'the' where
    # human_id is based on (pre + (abbrev or name) + post) and display is
    # based on (the + pre + (abbrev or name) + post)
    # Use cases:
    # a) CBSAs and CSAs, e.g. 'The Greater Austin Area'
    # b) Duplicate names, e.g. 'Chula Vista CDP in Cameron County'

    # If geo.alias_target is None, the geo is not an alias, but it could
    # be the target of one or more aliases.
    alias_target_id = Column(types.Integer, ForeignKey('geo.id'))
    _alias_target = orm.relationship(
                'Geo',
                primaryjoin=('Geo.alias_target_id==Geo.id'),
                remote_side='Geo.id',
                backref=orm.backref('aliases', lazy='dynamic'),
                lazy='joined',
                post_update=True)  # Needed to avoid CircularDependencyError

    _data = orm.relationship('GeoData', uselist=False, back_populates='_geo')

    # _levels is a dictionary where GeoLevel.level is the key
    _levels = orm.relationship(
                'GeoLevel',
                collection_class=attribute_mapped_collection('level'),
                cascade='all, delete-orphan',
                backref='_geo')

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
                backref=orm.backref('children',
                                    lazy='dynamic',
                                    # order_by='Geo.name'
                                    ),
                lazy='dynamic')

    delimiter = '/'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        # Not during __init__() and there's no abbreviation used instead
        if self.human_id is not None and self.abbrev is None:
            self.human_id = Geo.create_key(name=val,
                                           path_parent=self.path_parent,
                                           alias_target=self.alias_target)
        nstr = val.lower()
        self.the_prefix = (nstr.find('states') > -1 or
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
            self.human_id = Geo.create_key(name=self.name, abbrev=val,
                                           path_parent=self.path_parent,
                                           alias_target=self.alias_target)
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
                                           alias_target=self.alias_target)
        self._path_parent = val

    path_parent = orm.synonym('_path_parent', descriptor=path_parent)

    @property
    def alias_target(self):
        return self._alias_target

    @alias_target.setter
    def alias_target(self, val):
        if val is None:
            self._alias_target = None
            return

        aliases = self.aliases.all()
        if aliases:
            if val in aliases:
                val.promote_to_alias_target()
            else:
                for alias in aliases:
                    alias.alias_target = val  # recurse on each alias
                self.alias_target = val  # recurse on self w/o any alias
            return

        if val.alias_target is not None:  # val is an alias, so redirect
            val = val.alias_target
            # an alias cannot itself have an alias
            assert val.alias_target is None

        if val == self:
            raise CircularReference(attr='alias_target', inst=self, value=val)

        if self.alias_target is None:
            self.transfer_references(val)

        self._alias_target = val

    alias_target = orm.synonym('_alias_target', descriptor=alias_target)

    @property
    def human_id(self):
        return self._human_id

    @human_id.setter
    def human_id(self, val):
        if val is None:
            raise ValueError('human_id cannot be set to None')
        # check if it's already registered by a different geo
        geo = Geo[val]
        if geo is not None and geo is not self:
            raise ValueError("'{}' is already registered.".format(val))
        if hasattr(self, '_human_id'):  # unregister old human_id
            # Default None since Trackable registers after Geo.__init__()
            Geo._instances.pop(self.human_id, None)
        Geo[val] = self  # register the new human_id
        self._human_id = val  # set human_id last
        # recursively propagate change to path_children
        for pc in self.path_children:
            pc.human_id = Geo.create_key(name=pc.name, abbrev=pc.abbrev,
                                         path_parent=self,
                                         alias_target=pc.alias_target)

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

    @property
    def levels(self):
        return self._levels

    @levels.setter
    def levels(self, val):
        for geo_level in val.values():
            geo_level.geo = self  # invoke GeoLevel.geo setter

    levels = orm.synonym('_levels', descriptor=levels)

    @staticmethod
    def create_key(name=None, abbrev=None, path_parent=None, alias_target=None,
                   **kwds):
        '''Create key for a geo

        Return a registry key allowing the Trackable metaclass to look
        up a geo instance. The key is created by concatenating the
        human_id of the path_parent with the abbreviation or name
        provided, separated by the Geo delimiter. If no path_parent is
        provided, but there is an alias_target, the human_id of the
        alias_target's path_parent is used instead.
        '''
        if path_parent is None and alias_target is not None:
            path_parent = alias_target.path_parent
        path = '' if path_parent is None else (path_parent.human_id +
                                               Geo.delimiter)
        qualifier = abbrev if abbrev else name
        qualifier = (qualifier.replace('.', '').replace(', ', '-')
                     ).replace('/', '-').replace(' ', '_').lower()
        return path + qualifier

    def derive_key(self):
        '''Derive key from a geo instance

        Return the registry key used by the Trackable metaclass from a
        geo instance. The key is the human_id.
        '''
        return self.human_id

    def __init__(self, name, abbrev=None, path_parent=None, alias_target=None,
                 the_prefix=None, data=None, levels={},
                 parents=[], children=[], data_level=None):
        '''Initialize a new geo

        The data parameter is the GeoData JSON, though the geo need not
        be specified since the geo should be self. The levels parameter
        is a dictionary of GeoLevel JSON keyed by level, where the geo
        and level need not be specified in the GeoLevel JSON since the
        geo should be self and the level should match the key.
        '''
        self.name = name
        if the_prefix is not None:  # Override calculated value, if provided
            self.the_prefix = the_prefix
        self.abbrev = abbrev
        if path_parent is None and alias_target is not None:
            path_parent = alias_target.path_parent
        self.path_parent = path_parent
        self.alias_target = alias_target
        self.human_id = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                       path_parent=self.path_parent,
                                       alias_target=self.alias_target)
        # if self.alias_target is not None:
        #     return

        self.parents = parents
        self.children = children

        data_children = self.children.all() if data_level is None else [
                            child for child in self.children
                            if child.levels.get(data_level, None) is not None]

        if data is not None:
            # The geo for the data should always be self. If a geo key
            # is provided, make sure it matches and remove it.
            data_geo = data.get('geo', None)
            if data_geo == self.trepr(tight=True, raw=False):
                data = data.copy()
                data.pop('geo')
            elif data_geo is not None:
                raise KeyError('Geo data json contains a geo key that '
                               'does not match geo being created')

        # if no data, calculate the data from children (if any)
        elif len(data_children) > 0:
            fields = ('total_pop', 'urban_pop', 'land_area', 'water_area')
            data = {f: sum((c.data[f] for c in data_children)) for f in fields}
            fields = ('latitude', 'longitude')
            for f in fields:
                data[f] = sum((c.data[f] * (
                              c.data['land_area'] + c.data['water_area'])
                              for c in data_children)) * 1.0 / (
                          sum((c.data['land_area'] + c.data['water_area'])
                              for c in data_children))

        self.data = GeoData(geo=self, **data) if data is not None else None

        self.levels = {}
        for lvl, glvl in levels.iteritems():
            new_glvl = glvl
            # The geo for the geolevel should always be self. If a geo
            # key is provided, make sure it matches and remove it.
            glvl_geo = new_glvl.get('geo', None)
            if glvl_geo == self.trepr(tight=True, raw=False):
                new_glvl = glvl.copy()
                new_glvl.pop('geo')
            elif glvl_geo is not None:
                raise KeyError('Geo level json contains a geo key that '
                               'does not match geo being created')
            # The level for the geolevel should always be the key. If a
            # level is provided, make sure it matches and remove it.
            glvl_level = new_glvl.get('level', None)
            if glvl_level == lvl:
                if new_glvl == glvl:
                    new_glvl = glvl.copy()
                new_glvl.pop('level')

            elif glvl_level is not None:
                raise KeyError('Geo level json contains a level that '
                               'does not match key for the geo level')
            self.levels[lvl] = GeoLevel(geo=self, level=lvl, **new_glvl)

    def __getitem__(self, key):
        return Geo[Geo.create_key(name=key, path_parent=self)]

    # __setitem__ is unnecessary and would be awkward since the key must
    # always be derived from the value

    def transfer_references(self, geo):
        '''Transfer references

        Utility function for transfering references to another geo, for
        example, when making a geo an alias of another geo.'''
        attributes = {'parents': ('dynamic', []),
                      'children': ('dynamic', []),
                      'data': ('not dynamic', None),
                      'levels': ('not dynamic', {})}

        for attr, (load, empty) in attributes.iteritems():
            # load, rel = attributes[attr]
            self_attr_val = getattr(self, attr)
            if load == 'dynamic':
                self_attr_val = self_attr_val.all()
            if self_attr_val:
                geo_attr_val = getattr(geo, attr)
                if load == 'dynamic':
                    geo_attr_val = geo_attr_val.all()
                if geo_attr_val:
                    raise AttributeConflict(inst1=self, attr1=attr,
                                            inst2=geo, attr2=attr)
                setattr(geo, attr, self_attr_val)
                setattr(self, attr, empty)

    def promote_to_alias_target(self):
        '''Promote alias to alias_target

        Used to convert an alias into an alias_target. The existing
        alias_target is converted into an alias of the new alias_target.
        Has no effect if the geo is already an alias_target.
        '''
        at = self.alias_target
        if at is None:  # self is already an alias_target
            return
        # an alias cannot itself have an alias
        assert at.alias_target is None

        self.alias_target = None
        aliases = at.aliases.all() + [at]
        for alias in aliases:
            # transfer references when alias_target setter called on at
            alias.alias_target = self

    def display(self, show_the=True, show_abbrev=True, abbrev_path=True,
                max_path=float('Inf')):
        '''Generate text for displaying a geo to a user

        Returns a string derived from the name, abbrev, the_prefix, and
        the geo path established by the path_parent. The following
        parameters affect the output:
        - show_the=True: The name of the geo is prefixed by 'The' if the
          geo has the flag (geo.the_prefix == True)
        - show_abbrev=True: The abbrev is displayed in parentheses after
          the geo name if the geo has an abbrev
        - abbrev_path=True: Any path geos appearing after the geo are
          displayed in abbrev form, if one exists
        - max_path=Inf: Determines the number of levels in the geo path
          beyond the current geo that should be included. A value of 0
          limits the display to just the geo, a value of 1 includes the
          immediate path_parent, etc.
        '''
        geostr = ''
        geo = self
        plvl = 0
        while geo is not None and plvl <= max_path:
            the = ('The ' if geo.the_prefix and show_the else '')
            if plvl == 0:
                geostr += u'{the}{name}'.format(the=the, name=geo.name)
                if geo.abbrev and show_abbrev:
                    geostr += u' ({abbrev})'.format(abbrev=geo.abbrev)
            elif abbrev_path:
                geostr += u'{abbrev}'.format(abbrev=geo.abbrev)
            else:
                geostr += u'{name}'.format(name=geo.name)

            if geo.path_parent is not None and plvl < max_path:
                geostr += ', '
            geo = geo.path_parent
            plvl += 1
        return geostr

    def related_geos_by_level(self, relation, tight=True, raw=False, limit=10):
        '''Related geos by level

        Given a relation (e.g. parent/child), returns an ordered
        dictionary of geo reprs stratified (keyed) by level. The levels
        are ordered top to bottom for children and bottom to top for
        parents.

        The following inputs may be specified:
        tight=True: make all repr values tight (without whitespace)
        raw=False: when True, adds extra escapes (for printing)
        limit=10: caps the number of list items within any geo level;
                  a negative limit indicates no cap
        '''
        if relation not in set(('parents', 'children')):
            raise ValueError('{rel} is not an allowed value for '
                             'relation'.format(rel=relation))

        base_q = getattr(self, relation).join(Geo.data).join(Geo.levels)
        levels = (lvl for lvl in (
            GeoLevel.up if relation == 'parents' else GeoLevel.down))

        if limit < 0:
            od = OrderedDict(
                (lvl, [g.trepr(tight=tight, raw=raw) for g in
                 base_q.filter(GeoLevel.level == lvl).order_by(
                 desc(GeoData.total_pop)).all()]) for lvl in levels)
        else:
            od = OrderedDict(
                (lvl, [g.trepr(tight=tight, raw=raw) for g in
                 base_q.filter(GeoLevel.level == lvl).order_by(
                 desc(GeoData.total_pop)).limit(limit).all()
                 ]) for lvl in levels)

        for lvl, geos in od.iteritems():
            if len(geos) == 0:
                od.pop(lvl)

        return od

    def json(self, mute=[], wrap=True, tight=True, raw=False, limit=10):
        '''JSON structure for a geo data instance

        Returns a structure for the given geo data instance that will
        serialize to JSON.

        The following inputs may be specified:
        mute=[]: mutes (excludes) any field names listed
        wrap=True: wrap the instance in a dictionary keyed by repr
        tight=True: make all repr values tight (without whitespace)
        raw=False: when True, adds extra escapes (for printing)
        limit=10: caps the number of list or dictionary items beneath
                  the main level; a negative limit indicates no cap
        '''
        od = OrderedDict((
            # ('repr', self.trepr(tight=tight, raw=raw)),
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('display', self.display(max_path=1, show_the=True,
                                     show_abbrev=False, abbrev_path=True)),
            ('name', self.name),
            ('the_prefix', self.the_prefix),
            ('abbrev', self.abbrev),

            ('path_parent', (self.path_parent.trepr(tight=tight, raw=raw)
                             if self.path_parent is not None else None)),

            ('alias_target', (self.alias_target.trepr(tight=tight, raw=raw)
                              if self.alias_target else None)),

            ('aliases', [alias.trepr(tight=tight, raw=raw)
                         for alias in self.aliases.all()]),

            ('data', (self.data.json(mute=mute+['key', 'geo'], wrap=False,
                                     tight=tight, raw=raw, limit=limit)
                      if self.data else {})),

            ('levels', OrderedDict(
                (lvl, self.levels[lvl].json(mute=mute+['key', 'geo', 'level'],
                                            wrap=False, tight=tight, raw=raw,
                                            limit=limit))
                for lvl in GeoLevel.down if self.levels.get(lvl, None))),

            ('parents', self.related_geos_by_level(
                relation='parents', tight=tight, raw=raw, limit=limit)),

            ('children', self.related_geos_by_level(
                relation='children', tight=tight, raw=raw, limit=limit))
        ))

        for field in mute:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # Geo[<human_id>]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return stringify(
            self.json(wrap=True, tight=False, raw=True, limit=-1), limit=10)


class GeoData(BaseGeoModel, AutoTableMixin):
    '''Base class for geo data'''

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
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._geo is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = GeoData.create_key(geo=val)
            inst = GeoData[key]
            if inst is not None and inst is not self:
                raise ValueError('{!r} is already registered.'.format(key))
            # update registry with new key
            GeoData.unregister(self)
            GeoData[key] = self

        self._geo = val  # set new value last

    geo = orm.synonym('_geo', descriptor=geo)

    @staticmethod
    def create_key(geo, **kwds):
        '''Create key for geo data

        Return a key allowing the Trackable metaclass to register a geo
        data instance. The key is the corresponding geo.
        '''
        return geo

    def derive_key(self):
        '''Derive key from a geo data instance

        Return the registry key used by the Trackable metaclass from a
        geo data instance. The key is the geo to which it is linked.
        '''
        return self.geo

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

    def json(self, mute=[], wrap=True, tight=True, raw=False, limit=10):
        '''JSON structure for a geo data instance

        Returns a structure for the given geo data instance that will
        serialize to JSON.

        The following inputs may be specified:
        mute=[]: mutes (excludes) any field names listed
        wrap=True: wrap the instance in a dictionary keyed by repr
        tight=True: make all repr values tight (without whitespace)
        raw=False: when True, adds extra escapes (for printing)
        limit=10: caps the number of list or dictionary items beneath
                  the main level; a negative limit indicates no cap
        '''
        od = OrderedDict((
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('geo', self.geo.trepr(tight=tight, raw=raw)),
            ('total_pop', self.total_pop),
            ('urban_pop', self.urban_pop),
            ('latitude', self.latitude),
            ('longitude', self.longitude),
            ('land_area', self.land_area),
            ('water_area', self.water_area)
        ))

        for field in mute:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # GeoData[Geo[<human_id>]]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return stringify(
            self.json(wrap=True, tight=False, raw=True, limit=-1), limit=10)


class GeoLevel(BaseGeoModel, AutoTableMixin):
    '''Base class for geo levels

    A geo level contains level information for a particular geo, where
    the level indicates the type of geo and/or where the geo fits in the
    geo tree. The levels were designed to allow global normalization and
    include country, subdivision1..subdivisionN, place, csa, and cbsa.

    The designation indicates how the geo is described at the given
    level. For example, in the U.S., the subdivision1 geos are mainly
    states, but also includes some territories (e.g. Puerto Rico) and a
    federal district (DC).

    A single geo may have multiple levels. For example, San Francisco
    has a consolidated government that is both a county (subdivision2)
    and a city (place). DC is simultaneously a federal district
    (subdivision1), a county equivalent (subdivision2), and a city
    (place).
    '''
    geo_id = Column(types.Integer, ForeignKey('geo.id'))
    # _geo relationship defined via backref on Geo._levels

    # level values: country, subdivision1, subdivision2, place, csa, cbsa
    _level = Column('level', types.String(30))

    # designations: state, county, city, etc. (lsad for place)
    designation = Column(types.String(60))

    # ids is a dictionary where GeoID.standard is the key
    ids = orm.relationship(
                'GeoID',
                collection_class=attribute_mapped_collection('standard'),
                cascade='all, delete-orphan',
                backref='level')

    # Querying use cases:
    #
    # 1. Fetch a particular level (e.g. subdivision2) for a particular
    #    geo (e.g. Travis County) to determine designation (e.g. county)
    #    or to map to 3rd-party IDs (e.g. FIPS codes)
    #    cols: level, geo_id
    # 2. For a particular level (e.g. subdivision2), obtain all the geos
    #    (this will often be a large number).
    #    cols: level
    # 3. For a particular geo (e.g. Washington, D.C.), obtain all the
    #    levels (e.g. subdivision1, subdivision2, place)
    #    cols: geo_id
    __table_args__ = (Index('ux_geo_level',
                            # ux for unique index
                            'level',
                            'geo_id',
                            unique=True),)

    down = OrderedDict((
        ('country', ('subdivision1',)),
        ('subdivision1', ('csa', 'cbsa', 'subdivision2', 'place')),
        ('csa', ('cbsa', 'subdivision2', 'place')),
        ('cbsa', ('subdivision2', 'place')),
        ('subdivision2', ('place',)),
        ('place', ())
        ))

    up = OrderedDict((
        ('place', ('subdivision2', 'cbsa', 'csa', 'subdivision1')),
        ('subdivision2', ('cbsa', 'csa', 'subdivision1')),
        ('cbsa', ('csa', 'subdivision1')),
        ('csa', ('subdivision1',)),
        ('subdivision1', ('country',)),
        ('country', ())
        ))

    @property
    def geo(self):
        return self._geo

    @geo.setter
    def geo(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._geo is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = GeoLevel.create_key(geo=val, level=self.level)
            inst = GeoLevel[key]
            if inst is not None and inst is not self:
                raise ValueError('{} is already registered.'.format(key))
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
            # ensure new key is not already registered
            key = GeoLevel.create_key(geo=self.geo, level=val)
            inst = GeoLevel[key]
            if inst is not None and inst is not self:
                raise ValueError('{} is already registered.'.format(key))
            # update registry with new key
            GeoLevel.unregister(self)
            GeoLevel[key] = self  # register the new key

        self._level = val  # set new value last

    level = orm.synonym('_level', descriptor=level)

    @staticmethod
    def create_key(geo, level, **kwds):
        '''Create key for a geo level

        Return a key allowing the Trackable metaclass to register a geo
        level instance. The key is a tuple containing the geo and level.
        '''
        return (geo, level)

    def derive_key(self):
        '''Derive key from a geo level instance

        Return the registry key used by the Trackable metaclass from a
        geo level instance. The key is a tuple of geo and level.
        '''
        return (self.geo, self.level)

    def __init__(self, geo, level, designation=None):
        '''Initialize a new geo level'''
        self.level = level
        self.designation = designation

        # Must follow level assignment to provide key for Geo.levels
        self.geo = geo

    def json(self, mute=[], wrap=True, tight=True, raw=False, limit=10):
        '''JSON structure for a geo level instance

        Returns a structure for the given geo level instance that will
        serialize to JSON.

        The following inputs may be specified:
        mute=[]: mutes (excludes) any field names listed
        wrap=True: wrap the instance in a dictionary keyed by repr
        tight=True: make all repr values tight (without whitespace)
        raw=False: when True, adds extra escapes (for printing)
        limit=10: caps the number of list or dictionary items beneath
                  the main level; a negative limit indicates no cap
        '''
        od = OrderedDict((
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('geo', self.geo.trepr(tight=tight, raw=raw)),
            ('level', self.level),
            ('designation', self.designation),
            ('ids', OrderedDict(
                (standard, self.ids[standard].json(
                                mute=mute+['key', 'level', 'standard'],
                                wrap=False, tight=tight, raw=raw,
                                limit=limit))
                for standard in self.ids.iterkeys())),
        ))

        for field in mute:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # GeoLevel[(Geo[<human_id>], <level>)]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return stringify(
            self.json(wrap=True, tight=False, raw=True, limit=-1), limit=10)


class GeoID(BaseGeoModel, AutoTableMixin):
    '''Geo ID base class

    Used to map geos (by level) to 3rd party IDs and vice versa.
    '''
    level_id = Column(types.Integer, ForeignKey('geo_level.id'))
    # level relationship defined via backref on GeoLevel.ids

    _standard = Column('standard', types.String(20))  # FIPS, ANSI, etc.
    _code = Column('code', types.String(20))  # 4805000, 02409761

    # Querying use cases:
    #
    # 1. Fetch the geo level (e.g. DC as a place) for a particular
    #    id code (e.g. FIPS 4805000)
    #    cols: standard, code
    # 2. Fetch the id code for a particular geo level and standard
    #    cols: level, standard
    __table_args__ = (Index('ux_geo_id:standard+code',
                            # ux for unique index
                            'standard',
                            'code',
                            unique=True),
                      # Index('ux_geo_id:level+standard',
                      #       # ux for unique index
                      #       'level',
                      #       'standard',
                      #       unique=True),
                      )

    @property
    def standard(self):
        return self._standard

    @standard.setter
    def standard(self, val):
        if val is None:
            raise ValueError('Cannot be set to None')

        if self._standard is not None:  # Not during __init__()
            # ensure new key is not already registered
            key = GeoID.create_key(standard=val, code=self.code)
            inst = GeoID[key]
            if inst is not None and inst is not self:
                raise ValueError('{} is already registered.'.format(key))
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
            # ensure new key is not already registered
            key = GeoID.create_key(standard=self.standard, code=val)
            inst = GeoID[key]
            if inst is not None and inst is not self:
                raise ValueError('{} is already registered.'.format(key))
            # update registry with new key
            GeoID.unregister(self)
            GeoID[key] = self

        self._code = val  # set new value last

    code = orm.synonym('_code', descriptor=code)

    @staticmethod
    def create_key(standard, code, **kwds):
        '''Create key for a geo ID

        Return a key allowing the Trackable metaclass to register a
        geo ID instance. The key is a tuple containing the standard and
        the code.
        '''
        return (standard, code)

    def derive_key(self):
        '''Derive key from a geo ID instance

        Return the registry key used by the Trackable metaclass from a
        geo ID instance. The key is a tuple of standard and code.
        '''
        return (self.standard, self.code)

    def __init__(self, level, standard, code):
        '''Initialize a new geo ID'''
        self.standard = standard
        self.code = code

        # Must follow standard assignment to create key for GeoLevel.ids
        self.level = level

    def json(self, mute=[], wrap=True, tight=True, raw=False, limit=10):
        '''JSON structure for a geo ID instance

        Returns a structure for the given geo ID instance that will
        serialize to JSON.

        The following inputs may be specified:
        mute=[]: mutes (excludes) any field names listed
        wrap=True: wrap the instance in a dictionary keyed by repr
        tight=True: make all repr values tight (without whitespace)
        raw=False: when True, adds extra escapes (for printing)
        limit=10: caps the number of list or dictionary items beneath
                  the main level; a negative limit indicates no cap
        '''
        od = OrderedDict((
            ('key', self.trepr(tight=tight, raw=raw, outclassed=False)),
            ('level', self.level.trepr(tight=tight, raw=raw)),
            ('standard', self.standard),
            ('code', self.code),
        ))

        for field in mute:
            od.pop(field, None)  # fail silently if field not present

        rv = (OrderedDict(((self.trepr(tight=tight, raw=raw), od),))
              if wrap else od)
        return rv

    # Use default __repr__() from Trackable:
    # GeoID[(<standard>, <code>)]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return stringify(
            self.json(wrap=True, tight=False, raw=True, limit=-1), limit=10)
