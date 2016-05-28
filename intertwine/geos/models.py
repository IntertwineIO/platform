#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import orm, types, Column, ForeignKey, Index, Table
from sqlalchemy.orm.collections import attribute_mapped_collection

from ..utils import AutoTableMixin, Trackable
from ..exceptions import CircularReference


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
                backref=orm.backref('children', lazy='dynamic'),
                lazy='joined')

    # geo_type = Column(types.String(30))

    # # city, town, village, parish, etc.; based on lsad for places
    # designation = Column(types.String(60))

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
                                           alias_target=self.alias_target)
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
            self._alias_target = val
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
                                         alias_target=pc.alias_target)

    human_id = orm.synonym('_human_id', descriptor=human_id)

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
        string = '' if path_parent is None else (path_parent.human_id +
                                                 Geo.delimiter)
        string += (abbrev if abbrev else name).lower()
        string = string.replace('.', '').replace(' ', '_')
        return string

    def derive_key(self):
        '''Derive key from a geo instance

        Return the registry key used by the Trackable metaclass from a
        geo instance. The key is the human_id.
        '''
        return self.human_id

    # TODO: add levels=[]  # a list of (level, designation, geo_ids) tuples,
    #                      # where geo_ids is a list of (standard, code) tuples
    # TODO: add data={}  # a dictionary of attribute/value pairs
    def __init__(self, name, abbrev=None, path_parent=None, alias_target=None,
                 the_prefix=None, parents=[], children=[]):
                # total_pop=None, urban_pop=None):
        '''Initialize a new geo'''
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
        # self.geo_type = geo_type
        # self.designation = designation
        # self.total_pop = total_pop
        # self.urban_pop = urban_pop

    def promote_to_alias_target(self):
        '''Promote alias to alias_target

        Used to convert an alias into an alias_target. The existing
        alias_target is converted into an alias of the new alias_target.
        Has no effect if the geo is already a alias_target.
        '''
        at = self.alias_target
        if at is None:  # self is already an alias_target
            return
        # an alias cannot itself have an alias
        assert at.alias_target is None

        self.alias_target = None
        aliases = at.aliases.all() + [at]
        for alias in aliases:
            alias.alias_target = self

        # transfer all other references to new alias_target geo:
        # geodata, geolevels, ratings, follows, posts, ideas, projects
        self.levels = at.levels

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
                geostr += '{the}{name}'.format(the=the, name=geo.name)
                if geo.abbrev and show_abbrev:
                    geostr += ' ({abbrev})'.format(abbrev=geo.abbrev)
            elif abbrev_path:
                geostr += '{abbrev}'.format(abbrev=geo.abbrev)
            else:
                geostr += '{name}'.format(name=geo.name)

            if geo.path_parent is not None and plvl < max_path:
                geostr += ', '
            geo = geo.path_parent
            plvl += 1
        return geostr

    # Use default __repr__() from Trackable, e.g. Geo[<human_id>]

    def __str__(self):
        indent = ' ' * 4
        fields = dict(
            display=self.display(max_path=0, show_the=True, show_abbrev=True,
                                 abbrev_path=True),
            human_id=self.human_id,
            alias_target=(self.alias_target.display() if self.alias_target
                          else None),
            aliases=[alias.display() for alias in self.aliases],
            levels=self.levels.values(),
            parents=[p.display() for p in self.parents],
            children=[c.display(max_path=0) for c in self.children],
        )

        field_order = ['display', 'human_id', 'alias_target', 'aliases',
                       'levels', 'parents', 'children']
        string = []
        for field in field_order:
            data = fields[field]
            if data is None:
                continue
            if isinstance(data, basestring) and not data.strip():
                continue
            if not data:
                continue
            if field == 'display':
                data_str = 'Geo: {' + field + '}'
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


# TODO: Create GeoData class to store data related to the geo
# class GeoData(BaseGeoModel, AutoTableMixin):
#     geo_id (foreign key, 1:1)
#     total_pop
#     urban_pop
#     longitude
#     latitude
#     other attributes related to demographics, geography, climate, etc.


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

    # designation values: state, county, city, etc. (lsad for place)
    designation = Column(types.String(60))

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

    down = {
        'country': 'subdivision1',
        'subdivision1': ('subdivision2', 'csa', 'cbsa', 'place'),
        'subdivision2': 'place',
        'csa': ('subdivision2', 'cbsa', 'place'),
        'cbsa': ('subdivision2', 'place'),
        'place': None
    }

    up = {
        'country': None,
        'subdivision1': 'country',
        'subdivision2': ('cbsa', 'csa', 'subdivision1'),
        'csa': 'subdivision1',
        'cbsa': ('csa', 'subdivision1'),
        'place': ('cbsa', 'csa', 'subdivision2', 'subdivision1')
    }

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
            inst = Geo[key]
            if inst is not None and inst is not self:
                raise NameError('{} is already registered.'.format(key))
            # update registry with new key
            GeoLevel._instances.pop(self.derive_key(), None)
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
            inst = Geo[key]
            if inst is not None and inst is not self:
                raise NameError('{} is already registered.'.format(key))
            # update registry with new key
            GeoLevel._instances.pop(self.derive_key(), None)
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
        geo instance. The key is a tuple of the geo and level fields.
        '''
        return (self.geo, self.level)

    def __init__(self, geo, level, designation=None):
        '''Initialize a new geo level'''
        self.level = level
        self.designation = designation

        # Must follow level assignment to provide key for Geo.levels
        self.geo = geo

    # Use default __repr__() from Trackable
    # Format: GeoLevel[Geo[<human_id>], <level>]

    def __str__(self):
        geo_level_str = '{cls}: {geo} as a {desc} ({level})'
        return geo_level_str.format(cls=self.__class__.__name__,
                                    geo=self.geo.display(show_abbrev=False,
                                                         max_path=0),
                                    desc=self.designation,
                                    level=self.level)

# TODO: Create GeoID class to map geos (by level) to 3rd party IDs
# class GeoID(BaseGeoModel, AutoTableMixin):
#     geo_level_id (foreign key, M:1)
#     standard - FIPS, ANSI, etc.
#     code - 4805000, 02409761
