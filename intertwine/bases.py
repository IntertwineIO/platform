# -*- coding: utf-8 -*-
from collections import OrderedDict
from itertools import chain
from operator import attrgetter

from alchy.model import ModelBase
from sqlalchemy import Column, Integer, orm
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.descriptor_props import SynonymProperty as SP
from sqlalchemy.orm.properties import ColumnProperty as CP
from sqlalchemy.orm.relationships import RelationshipProperty as RP

from .trackable import Trackable
from .utils import InsertableOrderedDict, camelCaseTo_snake_case, kwargify


class BaseIntertwineMeta(Trackable):

    def __init__(cls, name, bases, attr):
        # import ipdb; ipdb.set_trace()

        super(BaseIntertwineMeta, cls).__init__(name, bases, attr)
        cls._class_init_()


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


class JsonifyProperty(object):

    _count = 0

    def __init__(self, name, method=None, kwargs=None, before=None, after=None,
                 show=True, *args, **kwds):
        if before and after:
            raise ValueError('JsonifyProperty {name} cannot have both '
                             "'before' and 'after' values".format(name=name))
        self.name = name
        self.method = method
        self.kwargs = kwargs or {}
        self.before = before
        self.after = after
        self.show = show
        self.index = self.__class__._count
        self.__class__._count += 1
        super(JsonifyProperty, self).__init__(*args, **kwds)

    def __call__(self, obj, *args, **kwds):
        func = getattr(obj, self.method)
        merged_kwds = self.kwargs.copy()
        merged_kwds.update(kwds)
        return func(*args, **merged_kwds)


class Jsonable(object):

    @classmethod
    def fields(cls):
        try:
            return cls._fields
        except AttributeError:
            cls._fields = cls.derive_fields()
            return cls._fields

    @classmethod
    def derive_fields(cls):
        '''Derives fields and their SQLAlchemy and Jsonify properties

        Nets out a model's SQLAlchemy column, relationship, and synonym
        properties and any Jsonify properites and returns an insertable
        ordered dictionary keyed by name, sequenced as follows:
        - SA properties initially in class_mapper iterate_property order
        - The 'id' column, if any, is relocated to the first position
        - Relationships w/ local foreign keys replace 1st column matched
        - Self-referential relationships grouped w/ backpopulate fields
        - Relationships w/ local primary key follow all prior properties
        - Synonyms replace their mapped column/relationship properties
        - Jsonify properties replace any matching fields and rest follow
        # - Regular Python properties follow in alphabetical order

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
        # Add JsonifyProperties, replacing any matches
        jsonify_properties = [v for v in cls.__dict__.values()
                              if isinstance(v, JsonifyProperty)]
        jsonify_properties.sort(key=attrgetter('index'))
        for jsonify_property in jsonify_properties:
            before, after = jsonify_property.before, jsonify_property.after
            jp_name = jsonify_property.name
            if jp_name in fields:
                if before or after:
                    raise ValueError('JsonifyProperty {name} matches existing '
                                     'field, so before/after must be None'
                                     .format(name=jp_name))
                fields[jp_name] = jsonify_property
            elif before:
                fields.insert(before, jp_name, jsonify_property)
            elif after:
                fields.insert(after, jp_name, jsonify_property, after=True)
            else:
                fields[jp_name] = jsonify_property

        return fields

    def jsonify(self, hide=None, nest=False, tight=True, raw=False, limit=10,
                depth=1, _json=None):
        '''JSON structure for a community instance

        Returns a structure for the given community instance that will
        serialize to JSON.

        Parameters:
        hide=None:  Set of field names to be excluded
        nest=False: By default all relationships are by reference and
                    the top level JSON is a dictionary of objects
        tight=True: Make all repr values tight (without whitespace)
        raw=False:  If True, adds extra escapes to treprs (for printing)
        limit=10:   Cap the number of list or dictionary items beneath
                    the main level; a negative limit indicates no cap
        depth=1:    recursion depth:
                    1: current instance only (NO references as keys)
                    2: current instance and 1st relation instances
                    3: current instance and 1st+2nd relation instances
        _json=None: private top-level json object
        '''
        assert depth > 0
        hide = set() if hide is None else hide
        hide = hide if isinstance(hide, set) else set(hide)
        _json = OrderedDict() if _json is None else _json
        json_params = kwargify()  # includes updated _json value
        del json_params['depth']

        # TODO: Check if item already exists and needs to be enhanced?
        self_json = OrderedDict()
        if not nest:
            self_key = self.trepr(tight=tight, raw=raw)
            _json[self_key] = self_json

        fields = self.fields()

        for field, prop in fields.items():
            if field in hide:
                continue

            if isinstance(prop, JsonifyProperty):
                if prop.show:
                    self_json[field] = prop(obj=self, depth=depth,
                                            **json_params)
                continue

            value = getattr(self, field)

            if hasattr(value, 'jsonify'):
                # TODO: Replace trepr with URI
                item = value
                item_key = item.trepr(tight=tight, raw=raw)
                self_json[field] = item_key
                if depth > 1 and item_key not in _json:
                    item.jsonify(depth=depth - 1, **json_params)

            elif isinstance(value, orm.dynamic.AppenderQuery):
                items = []
                self_json[field] = items
                for i, item in enumerate(value):
                    item_key = item.trepr(tight=tight, raw=raw)
                    items.append(item_key)
                    if depth > 1 and item_key not in _json:
                        item.jsonify(depth=depth - 1, **json_params)
                    if i + 1 == limit:
                        break

            else:
                self_json[field] = value

        return self_json if nest else _json


class BaseIntertwineModel(Jsonable, AutoTableMixin, ModelBase):

    @classmethod
    def _class_init_(cls):
        # the delegation chain stops here
        assert not hasattr(super(BaseIntertwineModel, cls), '_class_init_')
