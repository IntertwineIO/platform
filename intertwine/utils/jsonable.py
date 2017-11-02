#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import sys
from collections import OrderedDict
from datetime import datetime
from itertools import chain, islice
from math import floor
from mock.mock import NonCallableMagicMock
from operator import attrgetter, itemgetter
from past.builtins import basestring

from sqlalchemy import orm
from sqlalchemy.orm.descriptor_props import SynonymProperty as SP
from sqlalchemy.orm.properties import ColumnProperty as CP
from sqlalchemy.orm.relationships import RelationshipProperty as RP

from .structures import InsertableOrderedDict, PeekableIterator
from .tools import derive_defaults, isiterator, stringify

# Python version compatibilities
if sys.version_info < (3,):
    JSON_NUMBER_TYPES = (bool, float, int, long)  # noqa: ignore=F821
    lmap = map  # legacy map returning list
    from itertools import imap as map
else:
    JSON_NUMBER_TYPES = (bool, float, int)
    unicode = str


class JsonProperty(object):

    _count = 0

    def __init__(self, name, method=None, kwargs=None, begin=None, end=None,
                 before=None, after=None, hide=False, *args, **kwds):
        if sum(map(bool, (begin, end, before, after))) > 1:
            raise ValueError('JsonProperty {name} may only specify one of '
                             "(begin, end, before, after)".format(name=name))
        self.name = name
        self.method = method
        self.kwargs = kwargs or {}
        self.begin = begin
        self.end = end
        self.before = before
        self.after = after
        self.hide = hide
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
            value = getattr(obj, self.name)
            rv = list(value) if isiterator(value) else value
        return rv


class Jsonable(object):

    JSONIFY = 'jsonify'  # Must match the method name
    JSON_ROOT = 'root'
    JSON_PATH_DELIMITER = '.'
    JSON_PRIVATE_DESIGNATION = '_'
    JSON_PROPERTY_EXCLUSIONS = {'descriptor_dict', 'object_session'}
    JSON_PAGINATION = 'pagination'

    @classmethod
    def fields(cls):
        try:
            return cls._fields
        except AttributeError:
            cls._fields = cls._derive_fields()
            return cls._fields

    @classmethod
    def _derive_fields(cls):
        '''
        Derive fields and their SQLAlchemy and JSON properties

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
            # Require synonym field names to be public versions
            new_name = syn_name.strip('_')
            # new_name = sp.descriptor.fget.__name__
            fields.insert(syn_name, new_name, sp)
            del fields[syn_name]

        # Gather non-SQLAlchemy public properties
        property_generator = ((k, v) for k, v in inspect.getmembers(cls)
                              if k[0] != cls.JSON_PRIVATE_DESIGNATION and
                              k not in cls.JSON_PROPERTY_EXCLUSIONS and
                              isinstance(v, (property, JsonProperty)))

        py_properties = []
        jsonify_properties = []
        for k, v in property_generator:
            if isinstance(v, JsonProperty):
                jsonify_properties.append(v)
            else:  # property
                py_properties.append((k, v))

        # Append regular Python properties ordered alphabetically
        py_properties.sort(key=itemgetter(0))
        for k, v in py_properties:
            fields[k] = v

        # Insert JSON properties
        jsonify_properties.sort(key=attrgetter('index'))
        begin_count = end_count = 0
        for jp in jsonify_properties:
            jp_name = jp.name
            begin, end, before, after = jp.begin, jp.end, jp.before, jp.after
            method = jp.method
            # Override if method; otherwise just relocate original
            prop = jp if method else fields[jp_name]
            if jp_name in fields:
                if sum(map(bool, (begin, end, before, after))) == 0:
                    fields[jp_name] = prop  # Replace at same location
                    continue
                del fields[jp_name]  # Delete as it's reinserted below
            if begin:
                # Insert after other 'begin' fields
                fields.insert(begin_count, jp_name, prop, by_index=True)
                begin_count += 1
            elif end:
                # Append after other 'end' fields
                fields.append(jp_name, prop)
                end_count += 1
            elif before:
                fields.insert(before, jp_name, prop)
            elif after:
                fields.insert(after, jp_name, prop, after=True)
            else:
                # Insert before 'end' fields
                fields.insert(len(fields) - end_count - 1, jp_name,
                              prop, after=True, by_index=True)
        # Remove hidden last so they can serve as before/after anchors
        for jp in jsonify_properties:
            if jp.hide and jp.name in fields:
                del fields[jp.name]

        return fields

    @classmethod
    def ensure_json_safe(cls, value):
        if isinstance(value, JSON_NUMBER_TYPES) or value is None:
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, NonCallableMagicMock):
            return None
        return unicode(value)

    @classmethod
    def form_path(cls, base, *fields):
        path_components = list(fields)
        path_components.insert(0, base)
        return cls.JSON_PATH_DELIMITER.join(path_components)

    @classmethod
    def jsonify_value(cls, value, json_kwarg_map=None, _json=None):
        '''
        Jsonify value

        Convert any value or acyclic collection to a JSON-serializable
        dict. The conversion utilizes the following rules:

            1.  If the value has a jsonify method, invoke it if either:
                a.  nest is True or
                b.  value has no key or
                c.  both depth > 0 and the key is new (not in _json)
                Return the key if it exists and not nesting; otherwise
                return the jsonified value.
            2.  If the value is a NonCallableMagicMock, return None
            3.  If the value is not iterable, the given default method
                in the json_kwarg_map - or ensure_json_safe - is used.
            4.  If iterable.items(), return an OrderedDict in which
                jsonify_value is recursively called on each key/value.
            5.  Else if an iterable without items(), return sequence in
                which jsonify_value is recursively called on each item.
                If the iterable is a namedtuple, the sequence is a
                namedtuple and any limit is ignored. Otherwise, the
                sequence is a list.

        I/O:
        value: The item to be jsonified.

        json_kwarg_map=None: Dictionary of JSON kwargs keyed by class.
            The 'object' class can store default values for all classes.
            JSON kwargs may include any of the jsonify kwargs, though
            root and _json are ignored as the former is predetermined
            and the latter is passed separately.

        _json=None: Private top-level JSON dict for recursion
        '''
        json_kwarg_map = {} if json_kwarg_map is None else json_kwarg_map

        if _json is None:
            _json = OrderedDict()
            _json[cls.JSON_ROOT] = cls.jsonify_value(
                value, json_kwarg_map, _json)
            return _json

        json_kwargs = (json_kwarg_map.get(value.__class__) or
                       json_kwarg_map.get(object, {}))
        json_kwargs[cls.JSON_ROOT] = False  # _json['root'] is already set

        depth, limit, tight, raw, default, nest = cls._get_json_kwargs(
            json_kwargs, 'depth', 'limit', 'tight', 'raw', 'default', 'nest')

        if hasattr(value, cls.JSONIFY):
            try:
                # TODO: Replace trepr with URI
                item_key = None if nest else value.trepr(tight=tight, raw=raw)
            except AttributeError:
                item_key = None

            if not item_key or (depth > 0 and item_key not in _json):
                jsonified = value.jsonify(_json=_json, **json_kwargs)

            return item_key if item_key else jsonified

        if isinstance(value, NonCallableMagicMock):
            return None

        try:
            if isinstance(value, basestring):
                raise TypeError
            # TODO: apply limit() if a query and then count() for total
            all_item_iterator = PeekableIterator(value)  # non-iterables raise

        except TypeError:
            default = default or cls.ensure_json_safe
            return default(value)

        else:  # value is iterable and not a string
            item_iterator = (islice(all_item_iterator, limit) if limit > 0
                             else all_item_iterator)

            if hasattr(value, 'items'):  # dictionary
                items = OrderedDict(
                    (cls.jsonify_value(k, json_kwarg_map, _json),
                     cls.jsonify_value(value[k], json_kwarg_map, _json))
                    for k in item_iterator)

            else:  # tuple/list
                try:
                    constructor = value._make  # namedtuple
                    item_iterator = all_item_iterator  # all fields required
                except AttributeError:
                    constructor = list

                items = constructor(
                    cls.jsonify_value(item, json_kwarg_map, _json)
                    for item in item_iterator)

            if all_item_iterator.has_next():  # paginate
                try:
                    total = len(value)
                except TypeError:
                    total = value.count()
                if limit < total:
                    pagination = cls.paginate(len(items), limit, total)
                    try:
                        items.append(pagination)
                    except AttributeError:
                        items[cls.JSON_PAGINATION] = pagination

            return items

    def jsonify(self, config=None, depth=1, hide=None, hide_all=False,
                limit=10, tight=True, raw=False, default=None, nest=False,
                root=True, _path=None, _json=None):
        '''
        Jsonify

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

            Usage:
                >>> geo = Geo['us/tx/austin']
                >>> config = {
                    '.path_parent': 1,  # Show TX (path_parent of Austin)
                    '.path_parent.children': 0,  # Hide TX's children
                    '.path_parent.path_children': 0,  # Hide TX's path children
                    '.path_parent.path_parent': -1,  # Show US, but hide fields
                    '.path_parent.path_parent.path_children': 0.5  # Show US...
                    }  # ...path children references, without the objects
                >>> geo.jsonify(config=config)

        depth=1:
            Recursion depth:
                1: current object only (references but no objects)
                2: current object and 1st relation objects
                3: current object and 1st+2nd relation objects

        hide=None:
            Set of field names to be excluded

        hide_all=False:
            By default, all fields are included, but can be individually
            excluded via config or hide; if true, all fields are
            excluded, but can be individually included via config

        limit=10:
            Cap number of list or dictionary items beneath main level;
            a negative limit indicates no cap

        tight=True:
            Make all repr values tight (without whitespace)

        raw=False:
            If True, add an extra escape to unicode trepr (for printing)

        default=None:
            Default function used to ensure value is json-safe. Defaults
            to Jsonable.ensure_json_safe.

        nest=False:
            By default all relationships are by reference with JSON
            objects stored in the top-level dict

        root=True:
            Add root key to top-level dict

        _path=None:
            Private path to current field from the base object:
                .<base_object_field>.<related_object_field> (etc.)

        _json=None:
            Private top-level JSON dict for recursion
        '''
        assert depth > 0
        config = {} if config is None else config
        hide = set() if hide is None else hide
        hide = set(hide) if not isinstance(hide, set) else hide
        default = default or self.ensure_json_safe
        _path = '' if _path is None else _path
        _json = OrderedDict() if _json is None else _json
        json_kwargs = dict(
            config=config, hide=hide, limit=limit, tight=tight, raw=raw,
            default=default, nest=nest, root=False)

        # TODO: Check if item already exists and needs to be enhanced?
        self_json = OrderedDict()
        if not nest:
            self_key = self.trepr(tight=tight, raw=raw)
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
                if not prop.hide:
                    self_json[field] = prop(
                        obj=self, hide_all=field_hide_all,
                        depth=field_depth if field_path in config else depth,
                        _path=field_path, _json=_json, **json_kwargs)
                continue

            value = getattr(self, field)

            # Short circuit if we can just use the key
            if not nest and hasattr(value, self.JSONIFY):
                try:
                    # TODO: Replace trepr with URI
                    item_key = value.trepr(tight=tight, raw=raw)
                except AttributeError:
                    pass
                else:
                    if field_depth == 0 or item_key in _json:
                        self_json[field] = item_key
                        continue

            json_field_kwargs = dict(
                hide_all=field_hide_all, depth=field_depth, _path=field_path,
                **json_kwargs)
            json_kwarg_map = {object: json_field_kwargs}

            # jsonify_value returns jsonified item if nest
            self_json[field] = self.jsonify_value(
                value, json_kwarg_map, _json)

        if not nest and root and _json.get(self.JSON_ROOT) is None:
            _json[self.JSON_ROOT] = self_key

        return self_json if nest else _json

    JSON_KWARG_DEFAULTS = OrderedDict(derive_defaults(jsonify))

    @classmethod
    def _get_json_kwargs(cls, json_kwargs, *kwarg_names):
        return (json_kwargs.get(kwarg, cls.JSON_KWARG_DEFAULTS[kwarg])
                for kwarg in kwarg_names)

    @classmethod
    def paginate(cls, page_items, page_size, total_items, start=1):
        '''Append pagination for collections'''
        page = (start - 1) // page_size + 1
        full_pages, remainder = divmod(total_items, page_size)
        total_pages = full_pages + bool(remainder)
        end = start + page_items - 1
        return ('({start}-{end} of {items}; page {page} of {pages})'
                .format(start=start, end=end, items=total_items,
                        page=page, pages=total_pages))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        jsonified = self.jsonify(depth=1, limit=10, root=False)
        return stringify(jsonified, limit=-1)
