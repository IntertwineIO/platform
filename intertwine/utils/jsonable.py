#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import json
import sys
from collections import OrderedDict, namedtuple
from datetime import datetime
from enum import Enum, EnumMeta
from functools import partial
from itertools import chain, islice
from math import floor
from mock.mock import NonCallableMagicMock
from operator import attrgetter, itemgetter
from past.builtins import basestring

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm.descriptor_props import SynonymProperty as SP
from sqlalchemy.orm.properties import ColumnProperty as CP
from sqlalchemy.orm.relationships import RelationshipProperty as RP

from .duck_typing import isiterable, isiterator
from .structures import InsertableOrderedDict, PeekableIterator
from .tools import derive_defaults, derive_arg_types, enumify, get_class, stringify

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
        # print(self.index, self.name)
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
    JSON_PAGINATION = 'pagination'
    JSON_PATH_DELIMITER = '.'
    JSON_PRIVATE_DESIGNATION = '_'
    JSON_PROPERTY_EXCLUSIONS = {'descriptor_dict', 'object_session'}
    ID_FIELDS = {'id', 'pk', 'qualified_pk', 'json_key'}
    _fields = {}

    JsonKeyType = Enum('JsonKeyType', 'PRIMARY, NATURAL, URI',
                       module=__name__)

    QualifiedPrimaryKey = namedtuple('QualifiedPrimaryKey', 'model, pk')

    @property
    def PrimaryKey(self):
        """PrimaryKey is a namedtuple for the primary key fields"""
        return self.PrimaryKeyTuple()

    jsonified_PrimaryKey = JsonProperty(name='PrimaryKey', hide=True)

    @classmethod
    def PrimaryKeyTuple(cls):
        """PrimaryKeyTuple is the PrimaryKey namedtuple constructor"""
        try:
            return cls._PrimaryKey
        except AttributeError:
            pk_fields = (c.key for c in sqlalchemy.inspect(cls).primary_key)
            cls._PrimaryKey = namedtuple('PrimaryKey', pk_fields)
            return cls._PrimaryKey

    @classmethod
    def primary_key_fields(cls):
        """Primary key fields from the PrimaryKey namedtuple"""
        return cls.PrimaryKeyTuple()._fields

    @property
    def pk(self):
        """
        pk

        Return PrimaryKey namedtuple of primary key values. Abbreviated
        as "pk" to avoid conflict with alchy's primary_key.
        """
        return self.PrimaryKey(
            *(getattr(self, f) for f in self.primary_key_fields()))

    jsonified_pk = JsonProperty(name='pk', end=True, hide=True)

    @property
    def qualified_pk(self):
        return self.QualifiedPrimaryKey(self.model_class, self.pk)

    jsonified_qualified_pk = JsonProperty(name='qualified_pk', end=True, hide=True)

    def json_key(self, key_type=None, **kwds):
        """JSON key defaults to unique key repr, but can be overridden"""
        if not key_type or key_type is self.JsonKeyType.PRIMARY:
            return repr(self.qualified_pk)
        else:
            raise NotImplementedError('Unsupported JsonKeyType: {}'
                                      .format(key_type))

    jsonified_json_key = JsonProperty(name='json_key', method='json_key',
                                      end=True)

    @classmethod
    def fields(cls):
        """
        Return fields and their SQLAlchemy and JSON properties

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
        """
        try:
            return cls._fields[cls.__name__]
        except KeyError:
            cls._fields[cls.__name__] = cls._derive_fields()
            return cls._fields[cls.__name__]

    @classmethod
    def _derive_fields(cls):
        """Derive fields associated with the model (see "fields")"""
        mapper = orm.class_mapper(cls)
        pk = set(cls.primary_key_fields())
        # Catalog SA properties based on type and primary key
        sa_properties = {k: ([] if k is SP else ([], []))
                         for k in (CP, RP, SP)}
        for sa_property in mapper.iterate_properties:
            if isinstance(sa_property, RP):
                has_pk = pk <= set((c.key for c in sa_property.local_columns))
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
                # Insert after other 'end' fields
                fields.insert(len(fields) - 1, jp_name, prop, after=True,
                              by_index=True)
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
    def jsonify_value(cls, value, kwarg_map=None, _path=None, _json=None):
        """
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
                in the kwarg_map - or ensure_json_safe - is used.
            4.  If iterable.items(), return an OrderedDict in which
                jsonify_value is recursively called on each key/value.
            5.  Else if an iterable without items(), return sequence in
                which jsonify_value is recursively called on each item.
                If the iterable is a namedtuple, the sequence is a
                namedtuple and any limit is ignored. Otherwise, the
                sequence is a list.

        I/O:
        value: The item to be jsonified.

        kwarg_map=None: Dictionary of JSON kwargs keyed by class. The
            'object' kwargs are initial defaults. JSON kwargs may not
            include root/kwarg_map/_path/_json as root is predetermined
            and kwarg_map/_path/_json are passed separately.

        _path=None: Private path to current field from base object

        _json=None: Private top-level JSON dict for recursion
        """
        kwarg_map = {} if kwarg_map is None else kwarg_map
        _path = '' if _path is None else _path

        if _json is None:
            _json = OrderedDict()
            _json[cls.JSON_ROOT] = cls.jsonify_value(
                value, kwarg_map, _path, _json)
            return _json

        json_kwargs = (kwarg_map.get(get_class(value)) or
                       kwarg_map.get(object, {}))
        json_kwargs[cls.JSON_ROOT] = False  # _json['root'] is already set

        depth, limit, key_type, nest, default = (
            cls.extract_json_kwargs(
                json_kwargs, 'depth', 'limit', 'key_type', 'nest', 'default'))

        value_is_class = inspect.isclass(value)

        if hasattr(value, cls.JSONIFY) and not value_is_class:
            try:
                item_key = value.json_key(**json_kwargs)
            except AttributeError:
                item_key = None
            is_nested = not item_key or (depth > 0 and nest)
            if is_nested or (depth > 0 and item_key not in _json):
                jsonified = value.jsonify(_json=_json, kwarg_map=kwarg_map, **json_kwargs)
            return jsonified if is_nested else item_key

        if isinstance(value, NonCallableMagicMock):
            return None

        if not isiterable(value) or isinstance(value, basestring) or value_is_class:
            default = default or cls.ensure_json_safe
            return default(value)

        all_item_iterator = PeekableIterator(value)
        item_iterator = (islice(all_item_iterator, limit) if limit > 0
                         else all_item_iterator)

        if hasattr(value, 'items'):  # dictionary
            items = OrderedDict(
                (cls.jsonify_value(k, kwarg_map, _path, _json),
                 cls.jsonify_value(value[k], kwarg_map, _path, _json))
                for k in item_iterator)

        else:  # tuple/list
            try:
                constructor = value._make  # namedtuple
                item_iterator = all_item_iterator  # all fields required
            except AttributeError:
                constructor = list

            items = constructor(
                cls.jsonify_value(item, kwarg_map, _path, _json)
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

    def jsonify(self,
                config=None,     # type: Dict[Text, Union[int, float, Dict[Any, Any]]]
                depth=1,         # type: int
                hide=None,       # type: Set[Text]
                hide_all=False,  # type: bool
                limit=10,        # type: int
                key_type=None,   # type: JsonKeyType
                raw=False,       # type: bool
                tight=True,      # type: bool
                nest=False,      # type: bool
                root=True,       # type: bool
                default=None,    # type: Callable[Any, [bool, int, float, str, None]]
                kwarg_map=None,  # type: Dict[type, Dict[Text, Union[int, float, Dict[Any, Any]]]]
                _path=None,      # type: Text
                _json=None):     # type: Dict[Text, Any]
        """
        Jsonify

        Return a JSON-serializable dict representing the instance.

        I/O:

        config=None:
            Dictionary of field-level settings, in which keys are paths
            to fields and values are numeric or JSON kwarg dictionaries.
            Numeric values:
                0:      Hide field (non-zero for show field)
                +/-N:   Show related objects to depth N; decimals are
                        ignored: e.g. 0.5 -> 0 depth, but field is shown
                N>0:    Show all fields in related objects by default
                N<0:    Hide all fields in related objects by default
            Dictionary values may include any public jsonify parameter.

            Usage:
                >>> geo = Geo['us/tx/austin']
                >>> config = {
                    '.': -1,  # Hide all fields and set depth to 1
                    '.path_parent': 1,  # Show TX (path_parent of Austin)
                    '.path_parent.children': 0,  # Hide TX's children
                    '.path_parent.path_children': 0,  # Hide TX's path children
                    '.path_parent.path_parent': -1,  # Show US, but hide fields
                    '.path_parent.path_parent.path_children': 0.5  # Show US...
                    }  # ...path children references only – no objects
                >>> geo.jsonify(config=config)

        depth=1:
            Recursion depth:
                1: current object only (references but no objects)
                2: current object and 1st relation objects
                3: current object and 1st+2nd relation objects

        hide=None:
            Set of field names to be excluded.

        hide_all=False:
            By default, all fields are included, but can be individually
            excluded via config or hide; if true, all fields are
            excluded, but can be individually included via config.

        limit=10:
            Cap number of list or dictionary items beneath main level;
            a negative limit indicates no cap.

        key_type=None:
            A JsonKeyType enumeration with these options:
            PRIMARY: QualifiedPrimaryKey, a module/class-scoped primary
                key namedtuple. It is the default and only supported
                option unless json_key() is overridden
            NATURAL: A natural key composed of fields that determine
                uniqueness; NotImplemented in Jsonable, but see Trackable
            URI: An item's Uniform Resource Identifier; NotImplemented
                in Jsonable, but may be added by overriding json_key()

        raw=False:
            If True, add extra escape to unicode trepr (for printing).

        tight=True:
            Make all repr values tight (without whitespace).

        nest=False:
            By default all relationships are by reference with JSON
            objects stored in the top-level dict.

        root=True:
            If True, add root key to top-level dict.

        default=None:
            Default function used to ensure value is json-safe. Defaults
            to Jsonable.ensure_json_safe.

        kwarg_map=None:
            Dictionary of JSON kwargs keyed by class. Any 'object' class
            values in kwarg_map will be overwritten by the other JSON
            kwargs (further mutated by field). JSON kwargs may include
            any jsonify kwargs except root, kwarg_map, and _json as root
            is predetermined and kwarg_map/_json are passed separately.

        _path=None:
            Private path to current field from base object:
                .<base_object_field>.<related_object_field> (etc.)

        _json=None:
            Private top-level JSON dict for recursion.
        """
        _json = OrderedDict() if _json is None else _json
        config = {} if config is None else config
        hide = set() if hide is None else hide
        default = default or self.ensure_json_safe
        kwarg_map = {} if kwarg_map is None else kwarg_map.copy()
        dot_setting_kwargs = None

        if _path is None:
            _path = ''
            if '.' in config:
                dot_setting_kwargs = self.extract_settings('.', config, use_floor=True)

        base_json_kwargs = dict(
            config=config, depth=depth, hide=hide, hide_all=hide_all,
            limit=limit, key_type=key_type, raw=raw, tight=tight, nest=nest,
            root=False, default=default)  # exclude: _path, _json
        if dot_setting_kwargs:
            base_json_kwargs.update(dot_setting_kwargs)

        hide_all = base_json_kwargs['hide_all']
        nest = base_json_kwargs['nest']

        # TODO: Check if item already exists and needs to be enhanced?
        self_json = OrderedDict()
        if not nest:
            self_key = self.json_key(**base_json_kwargs)
            _json[self_key] = self_json

        depth = base_json_kwargs.pop('depth')
        if depth < 1:
            raise ValueError(f'Jsonify depth must be >= 1; value: {depth}')

        fields = self.fields()

        for field, prop in fields.items():
            if field in hide:
                continue

            field_setting_kwargs = field_setting_depth = None
            field_path = self.form_path(_path, field)

            if field_path in config:
                field_setting_kwargs = self.extract_settings(field_path, config)

                if 'depth' in field_setting_kwargs:
                    field_setting_depth = field_setting_kwargs['depth']
                    if field_setting_depth == 0:
                        continue
                    field_setting_kwargs['depth'] = int(floor(field_setting_depth))

            elif hide_all:
                continue

            field_json_kwargs = dict(depth=depth - 1, **base_json_kwargs)
            if field_setting_kwargs:
                field_json_kwargs.update(field_setting_kwargs)

            if isinstance(prop, JsonProperty):
                if not prop.hide:
                    # Defer depth decrement handling to JSON property
                    if field_setting_depth is None:
                        field_json_kwargs['depth'] = depth
                    self_json[field] = prop(
                        obj=self, _json=_json, _path=field_path, **field_json_kwargs)
                continue

            value = getattr(self, field)

            kwarg_map[object] = field_json_kwargs

            # jsonify_value returns jsonified item if nest
            self_json[field] = self.jsonify_value(value, kwarg_map, field_path, _json)

        if root and not nest and self.JSON_ROOT not in _json:
            _json[self.JSON_ROOT] = self_key

        return self_json if nest else _json

    def extract_settings(self, path, config, use_floor=False):
        """Extract settings for the given path and config"""
        settings = config[path]
        if hasattr(settings, 'items'):
            setting_kwargs = {k: v for k, v in settings.items()
                              if isinstance(v, self.JSONIFY_ARG_TYPES[k])}
            if len(setting_kwargs) < len(settings):
                missing = {k: v for k, v in settings.items() if k not in setting_kwargs}
                raise ValueError(f'Invalid type for setting in path {path!r}: {missing}')
            if 'depth' in setting_kwargs:
                if setting_kwargs['depth'] < 0:
                    raise ValueError('Jsonify depth setting must be >= 0; '
                                     f"value: {setting_kwargs['depth']}")
        else:
            depth = int(floor(abs(settings))) if use_floor else abs(settings)
            hide_all = settings < 0
            setting_kwargs = {'depth': depth, 'hide_all': hide_all}

        return setting_kwargs

    JSONIFY_ARG_TYPES = OrderedDict(derive_arg_types(jsonify, custom=[JsonKeyType]))
    JSONIFY_ARG_DEFAULTS = OrderedDict(derive_defaults(jsonify))

    @classmethod
    def extract_json_kwargs(cls, json_kwargs, *kwarg_names):
        """Extract JSON Kwargs sequentially as specified (default all)"""
        kwarg_names = kwarg_names or cls.JSONIFY_ARG_DEFAULTS.keys()
        return (json_kwargs.get(kwarg, cls.JSONIFY_ARG_DEFAULTS[kwarg])
                for kwarg in kwarg_names)

    @classmethod
    def objectify_json_kwargs(cls, json_kwargs, *kwarg_names):
        """
        Objectify JSON Kwargs

        Yield specified JSON kwarg (name, value) tuples sequentially,
        casting each to its annotated type in jsonify(). Casting allows
        transmission of JSON kwargs via query string. Any missing/None
        values are replaced by jsonify arg defaults. If no kwarg names
        are given, all JSON kwargs are yielded.

        json_kwargs: dict or dict-like object with a get() method
        *kwarg_names: names of JSON kwargs to be objectified
        return: generator that emits JSON kwarg (name, value) tuples
        """
        kwarg_names = kwarg_names or cls.JSONIFY_ARG_DEFAULTS.keys()

        for kwarg_name in kwarg_names:
            kwarg_value = json_kwargs.get(kwarg_name)
            try:
                # Convert JSON strings to objects (i.e. dicts/lists)
                kwarg_value = json.loads(kwarg_value)
            except (ValueError, TypeError):  # (string literal, non-string)
                pass

            if kwarg_value is not None:
                kwarg_type = cls.JSONIFY_ARG_TYPES.get(kwarg_name)
                if isinstance(kwarg_type, EnumMeta):
                    kwarg_type = partial(enumify, kwarg_type)
                if kwarg_type:
                    kwarg_value = kwarg_type(kwarg_value)
            else:
                kwarg_value = cls.JSONIFY_ARG_DEFAULTS[kwarg_name]

            yield kwarg_name, kwarg_value

    @classmethod
    def paginate(cls, page_items, page_size, total_items, start=1):
        """Append pagination for collections"""
        page = (start - 1) // page_size + 1
        full_pages, remainder = divmod(total_items, page_size)
        total_pages = full_pages + bool(remainder)
        end = start + page_items - 1
        return ('({start}-{end} of {items}; page {page} of {pages})'
                .format(start=start, end=end, items=total_items,
                        page=page, pages=total_pages))

    def print(self):
        jsonified = self.jsonify(depth=1, limit=10, root=False,
                                 key_type=self.JsonKeyType.NATURAL)
        print(stringify(jsonified, limit=-1))

    def __bytes__(self):  # py3 only
        return self.__unicode__().encode('utf-8')

    def __str__(self):
        if sys.version_info < (3,):
            return self.__bytes__()
        return self.__unicode__()

    def __unicode__(self):  # py2 only
        jsonified = self.jsonify(depth=1, limit=10, root=False,
                                 key_type=self.JsonKeyType.NATURAL)
        return stringify(jsonified, limit=-1)
