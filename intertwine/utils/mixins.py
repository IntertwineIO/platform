#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
from collections import OrderedDict
from itertools import chain
from math import floor
from mock.mock import NonCallableMagicMock
from operator import attrgetter, itemgetter

from sqlalchemy import Column, Integer, orm
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.collections import MappedCollection
from sqlalchemy.orm.descriptor_props import SynonymProperty as SP
from sqlalchemy.orm.properties import ColumnProperty as CP
from sqlalchemy.orm.relationships import RelationshipProperty as RP

from ..utils.tools import stringify
from .structures import InsertableOrderedDict
from .tools import camelCaseTo_snake_case, kwargify

if sys.version.startswith('3'):
    unicode = str


class AutoIdMixin(object):
    '''Automatically creates a primary id key'''
    id = Column(Integer, primary_key=True)


class AutoTablenameMixin(object):
    '''Autogenerates table name'''
    @declared_attr
    def __tablename__(cls):
        return camelCaseTo_snake_case(cls.__name__)


class AutoTableMixin(AutoIdMixin, AutoTablenameMixin):
    '''Standardizes automatic tables'''


class JsonProperty(object):

    _count = 0

    def __init__(self, name, method=None, kwargs=None, before=None, after=None,
                 show=True, *args, **kwds):
        if before and after:
            raise ValueError('JsonProperty {name} cannot have both '
                             "'before' and 'after' values".format(name=name))
        self.name = name
        self.method = method
        self.kwargs = kwargs or {}
        self.before = before
        self.after = after
        self.show = show
        self.index = self.__class__._count
        self.__class__._count += 1
        super(JsonProperty, self).__init__(*args, **kwds)

    def __call__(self, obj, *args, **kwds):
        if self.method:
            func = getattr(obj, self.method)
            merged_kwds = self.kwargs.copy()
            merged_kwds.update(kwds)
            rv = func(*args, **merged_kwds)
        else:
            rv = getattr(obj, self.name)
        return rv


class Jsonable(object):

    ROOT_KEY = 'root_key'
    PATH_DELIMITER = '.'

    @classmethod
    def fields(cls):
        try:
            return cls._fields
        except AttributeError:
            cls._fields = cls._derive_fields()
            return cls._fields

    @classmethod
    def _derive_fields(cls):
        '''Derives fields and their SQLAlchemy and JSON properties

        Nets out a model's SQLAlchemy column, relationship, and synonym
        properties and any JSON properties and returns an insertable
        ordered dictionary keyed by name, sequenced as follows:
        - SA properties initially in class_mapper iterate_property order
        - The 'id' column, if any, is relocated to the first position
        - Relationships w/ local foreign keys replace 1st column matched
        - Self-referential relationships grouped w/ backpopulate fields
        - Relationships w/ local primary key follow all prior properties
        - Synonyms replace their mapped column/relationship properties
        - Python properties follow in alphabetical order
        - JsonProperties replace any matching fields and the rest follow

        I/O:
        cls:  SQLAlchemy model from which to derive fields
        return: Insertable ordered dict of properties keyed by name
        '''
        mapper = orm.class_mapper(cls)
        pk = tuple(c.key for c in mapper.primary_key)
        # Catalog SA properties based on type and primary key
        sa_properties = {k: ([] if k is SP else ([], []))
                         for k in (CP, RP, SP)}
        for sa_property in mapper.iterate_properties:
            if isinstance(sa_property, RP):
                has_pk = set(pk) <= set((c.key for c in
                                        sa_property.local_columns))
                sa_properties[RP][has_pk].append(sa_property)
            elif isinstance(sa_property, CP):
                is_pk = sa_property.key in pk
                sa_properties[CP][is_pk].append(sa_property)
            elif isinstance(sa_property, SP):
                sa_properties[SP].append(sa_property)
            else:
                raise TypeError('Unknown property type for {}'
                                .format(sa_property))
        # Load column properties, starting with primary key columns
        fields = InsertableOrderedDict(
            ((cp.key, cp) for cp in chain(sa_properties[CP][1],
                                          sa_properties[CP][0])))

        # Add relationships, non-pk first, replacing any foreign key columns
        rp_anchor_map = {}
        columns_to_remove = set()
        MANYTOMANY = 'MANYTOMANY'
        FOREIGN_KEY_ENDING = '_id'
        FKE_LEN = len(FOREIGN_KEY_ENDING)
        for rp in chain(sa_properties[RP][0], sa_properties[RP][1]):
            for column_name in (c.key for c in rp.local_columns):
                is_primary_key = column_name in pk
                is_foreign_key = (not is_primary_key and
                                  len(column_name) >= FKE_LEN and
                                  column_name[-FKE_LEN:] == FOREIGN_KEY_ENDING)
                matching_name = column_name in fields
                if is_foreign_key and matching_name:
                    columns_to_remove.add(column_name)
                    # if rp not yet mapped to a column, map and insert it
                    if rp_anchor_map.get(rp.key) is None:
                        fields.insert(column_name, rp.key, rp)
                        rp_anchor_map[rp.key] = column_name
                elif is_primary_key:
                    # if model relates to itself, look for reverse property
                    reverse_property = fields.get(rp.back_populates)
                    if rp.mapper.class_ is cls and reverse_property:
                        reverse_anchor = rp_anchor_map[reverse_property.key]
                        is_after = rp.direction.name == MANYTOMANY
                        fields.insert(reverse_anchor, rp.key, rp, is_after)
                    else:
                        fields[rp.key] = rp
                        rp_anchor_map[rp.key] = rp.key
        # Remove foreign keys last as they serve as insertion points
        for column_name in columns_to_remove:
            del fields[column_name]

        # Replace column/relationship properties with their synonyms
        for sp in sa_properties[SP]:
            syn_name = sp.name
            new_name = sp.descriptor.fget.__name__
            fields.insert(syn_name, new_name, sp)
            del fields[syn_name]

        # Add any (non-SQLAlchemy) Python properties alphabetically
        py_properties = [(k, v) for k, v in cls.__dict__.items()
                         if isinstance(v, property)]
        py_properties.sort(key=itemgetter(0))
        for k, v in py_properties:
            fields[k] = v

        # Add JsonifyProperties, replacing any matches
        jsonify_properties = [v for v in cls.__dict__.values()
                              if isinstance(v, JsonProperty)]
        jsonify_properties.sort(key=attrgetter('index'))
        for jsonify_property in jsonify_properties:
            before, after = jsonify_property.before, jsonify_property.after
            jp_name = jsonify_property.name
            if jp_name in fields and (before or after):
                del fields[jp_name]  # we'll add it back before/after
            if before:
                fields.insert(before, jp_name, jsonify_property)
            elif after:
                fields.insert(after, jp_name, jsonify_property, after=True)
            else:
                fields[jp_name] = jsonify_property

        return fields

    @classmethod
    def form_path(cls, base, *fields):
        path_components = list(fields)
        path_components.insert(0, base)
        return cls.PATH_DELIMITER.join(path_components)

    def jsonify(self, config=None, hide_all=False, hide=None, nest=False,
                tight=True, raw=False, limit=10, depth=1,
                _path=None, _json=None):
        '''Jsonify

        Return a JSON-serializable dict representing the instance.

        I/O:
        config=None:
            Dictionary of field-level settings, in which keys are paths
            to fields and values are numeric:
                0:   Hide field (non-zero for show field)
                N:   Show related objects to depth N; any decimals are
                     ignored (e.g. 0.5 -> 0 depth, but field is shown)
                N>0: Show all fields in related objects by default
                N<0: Hide all fields in related objects by default
            Example:
                {
                    '.field_1': 0,
                    '.field_2': 2,
                    '.field_2.field_2a': 0,
                    '.field_3': -1,
                    '.field_3.field_3a': 1,
                    '.field_3.field_3b': -1,
                    '.field_3.field_3b.field_2bi': 1,
                }

        hide_all=False:
            By default, all fields are included, but can be individually
            excluded via config or hide; if true, all fields are
            excluded, but can be individually included via config

        hide=None:
            Set of field names to be excluded

        nest=False:
            By default all relationships are by reference with JSON
            objects stored in the top-level dict

        tight=True:
            Make all repr values tight (without whitespace)

        raw=False:
            If True, add an extra escape to unicode trepr (for printing)

        limit=10:
            Cap number of list or dictionary items beneath main level;
            a negative limit indicates no cap

        depth=1:
            Recursion depth:
                1: current object only (NO references as keys)
                2: current object and 1st relation objects
                3: current object and 1st+2nd relation objects

        _path=None:
            Path to current field from the base object:
                .<base_field>.<related_object_field> (etc.)

        _json=None:
            Top-level JSON dict
        '''
        assert depth > 0
        config = {} if config is None else config
        hide = set() if hide is None else hide
        hide = set(hide) if not isinstance(hide, set) else hide
        _path = '' if _path is None else _path
        _json = OrderedDict() if _json is None else _json
        json_kwargs = kwargify(exclude=('hide_all', 'depth', '_path'))

        # TODO: Check if item already exists and needs to be enhanced?
        self_json = OrderedDict()
        if not nest:
            self_key = self.trepr(tight=tight, raw=raw)
            if len(_json) == 0:
                _json[self.ROOT_KEY] = self_key
            _json[self_key] = self_json

        fields = self.fields()

        for field, prop in fields.items():
            if field in hide:
                continue

            field_depth = depth - 1
            field_hide_all = hide_all

            field_path = self.form_path(_path, field)
            if field_path in config:
                field_setting = config[field_path]
                if not field_setting:
                    continue
                field_depth = int(floor(abs(field_setting)))
                field_hide_all = field_setting < 0
            elif hide_all:
                continue

            if isinstance(prop, JsonProperty):
                if prop.show:
                    self_json[field] = prop(
                        obj=self, hide_all=field_hide_all,
                        depth=field_depth if field_path in config else depth,
                        _path=field_path, **json_kwargs)
                continue

            value = getattr(self, field)

            if isinstance(value, orm.dynamic.AppenderQuery):
                items = []
                self_json[field] = items
                for i, item in enumerate(value):
                    item_key = item.trepr(tight=tight, raw=raw)
                    items.append(item_key)
                    if field_depth > 0 and item_key not in _json:
                        item.jsonify(hide_all=field_hide_all,
                                     depth=field_depth, _path=field_path,
                                     **json_kwargs)
                    if i + 1 == limit:
                        break

            elif hasattr(value, 'jsonify'):
                # TODO: Replace trepr with URI
                item = value
                item_key = item.trepr(tight=tight, raw=raw)
                self_json[field] = item_key
                if field_depth > 0 and item_key not in _json:
                    item.jsonify(hide_all=field_hide_all,
                                 depth=field_depth, _path=field_path,
                                 **json_kwargs)

            elif (not hasattr(value, '__dict__') or
                    isinstance(value, MappedCollection)):
                self_json[field] = value

            elif isinstance(value, NonCallableMagicMock):
                self_json[field] = None

            else:
                raise NotImplementedError('{value} has no jsonify method'
                                          .format(value=value))

        return self_json if nest else _json

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        jsonified = self.jsonify(depth=1, limit=-1)
        del jsonified[self.ROOT_KEY]
        return stringify(jsonified, limit=10)
