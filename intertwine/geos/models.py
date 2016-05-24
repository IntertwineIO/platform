#!/usr/bin/env python
# -*- coding: utf-8 -*-
from alchy.model import ModelBase, make_declarative_base
from sqlalchemy import orm, types, Column, ForeignKey, Index, Table

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

    # mcka: more commonly known as
    # akas: also known as's (plural)
    # if geo.mcka is None, geo is the one more commonly known
    mcka_id = Column(types.Integer, ForeignKey('geo.id'))
    _mcka = orm.relationship(
                'Geo',
                primaryjoin=('Geo.mcka_id==Geo.id'),
                remote_side='Geo.id',
                backref=orm.backref('akas', lazy='dynamic'),
                lazy='joined',
                post_update=True)  # Needed to avoid CircularDependencyError

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
                                           mcka=self.mcka)
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
                                           mcka=self.mcka)
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
                                           mcka=self.mcka)
        self._path_parent = val

    path_parent = orm.synonym('_path_parent', descriptor=path_parent)

    @property
    def mcka(self):
        return self._mcka

    @mcka.setter
    def mcka(self, val):
        if val is None:
            self._mcka = val
            return

        akas = self.akas.all()
        if akas:
            if val in akas:
                val.promote_to_mcka()
            else:
                for aka in akas:
                    aka.mcka = val  # recurse on each aka
                self.mcka = val  # recurse on self w/o any aka
            return

        if val.mcka is not None:  # val is an aka, so redirect
            val = val.mcka
            # an aka cannot itself have an aka
            assert val.mcka is None

        if val == self:
            raise CircularReference(attr='mcka', inst=self, value=val)

        self._mcka = val

    mcka = orm.synonym('_mcka', descriptor=mcka)

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
                                         mcka=pc.mcka)

    human_id = orm.synonym('_human_id', descriptor=human_id)

    @staticmethod
    def create_key(name=None, abbrev=None, path_parent=None, mcka=None,
                   **kwds):
        '''Create key for a geo

        Return a registry key allowing the Trackable metaclass to look
        up a geo instance. The key is created by concatenating the
        human_id of the path_parent with the abbreviation or name
        provided, separated by the Geo delimiter. If no path_parent is
        provided, but there is a mcka, the human_id of the mcka's
        path_parent is used instead.
        '''
        if path_parent is None and mcka is not None:
            path_parent = mcka.path_parent
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

    def __init__(self, name, abbrev=None, path_parent=None, mcka=None,
                 the_prefix=None, parents=[], children=[]):
                # geo_type=None, descriptor=None,
                # total_pop=None, urban_pop=None):
        self.name = name
        if the_prefix is not None:  # Override calculated value, if provided
            self.the_prefix = the_prefix
        self.abbrev = abbrev
        if path_parent is None and mcka is not None:
            path_parent = mcka.path_parent
        self.path_parent = path_parent
        self.mcka = mcka
        self.human_id = Geo.create_key(name=self.name, abbrev=self.abbrev,
                                       path_parent=self.path_parent,
                                       mcka=self.mcka)
        # if self.mcka is not None:
        #     return
        self.parents = parents
        self.children = children
        # self.geo_type = geo_type
        # self.descriptor = descriptor
        # self.total_pop = total_pop
        # self.urban_pop = urban_pop

    def promote_to_mcka(self):
        '''Promote geo to the mcka (more commonly known as)

        Used to convert an aka geo into a mcka geo. The existing mcka
        geo is converted into an aka of the new mcka. Has no effect if
        the geo is already a mcka geo.
        '''
        mg = self.mcka
        if mg is None:  # self is already a mcka
            return
        # an aka cannot itself have an aka
        assert mg.mcka is None

        self.mcka = None
        akas = mg.akas.all() + [mg]
        for aka in akas:
            aka.mcka = self

        # transfer all other references to new mcka geo:
        # ratings, follows, posts, ideas, projects

    def display(self, show_the=True, show_abbrev=True, abbrev_path=True,
                max_path=float('Inf')):
        geostr = ''
        geo = self
        level = 0
        while geo is not None and level <= max_path:
            the = ('The ' if geo.the_prefix and show_the and level < 1 else '')
            if geo.abbrev is None:
                geostr += '{the}{name}'.format(the=the, name=geo.name)
            elif show_abbrev and level < 1:
                geostr += '{the}{name} ({abbrev})'.format(the=the,
                                                         name=geo.name,
                                                         abbrev=geo.abbrev)
            elif abbrev_path and level > 0:
                geostr += '{abbrev}'.format(abbrev=geo.abbrev)

            if geo.path_parent is not None and level < max_path:
                geostr += ', '

            geo = geo.path_parent
            level += 1
        return geostr

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{cls}[{geo!r}]'.format(cls=cls_name, geo=self.human_id)

    def __str__(self):
        # return '{prefix}{name}{abbrev}'.format(
        #         prefix='The ' if self.the_prefix else '',
        #         name=self.name,
        #         abbrev=(' (' + self.abbrev + ')') if self.abbrev else '')

        indent = ' ' * 4
        fields = dict(
            display=self.display(max_path=0, show_the=True, show_abbrev=True,
                                 abbrev_path=True),
            human_id=self.human_id,
            mcka=self.mcka.display() if self.mcka else None,
            akas=[aka.display() for aka in self.akas],
            parents=[p.display() for p in self.parents],
            children=[c.display(max_path=0) for c in self.children],
        )

        field_order = ['display', 'human_id', 'mcka', 'akas',
                       'parents', 'children']
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
