#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import sys
from collections import namedtuple, OrderedDict

from alchy.model import ModelMeta
from past.builtins import basestring
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import aliased, class_mapper
from sqlalchemy.orm.attributes import InstrumentedAttribute

from .exceptions import (
    InvalidRegistryKey, KeyConflictError, KeyInconsistencyError,
    KeyMissingFromRegistry, KeyMissingFromRegistryAndDatabase,
    KeyRegisteredAndNoModify)
from .utils import (build_table_model_map, dehumpify, get_class, isiterator,
                    isnamedtuple, merge_args)

# Python version compatibilities
U_LITERAL = 'u' if sys.version_info < (3,) else ''


def trepr(self, named=False, raw=True, tight=False, outclassed=True, _lvl=0):
    '''
    Trackable Representation (trepr)

    trepr is the default repr for Trackable classes.

    It returns a string that when evaluated returns the instance. It
    utilizes the registry and indexability provided by Trackable.

    I/O:
    named=False:     By default, named tuples are treated as regular
                     tuples. Set to True to print named tuple info.

    raw=True:        By default, escaped values are escaped again to
                     display raw values when printed, just as repr does.
                     If False, unicode characters print as intended.

    tight=False:     By default, newlines/indents are added when a line
                     exceeds MAX_WIDTH. Excludes whitespace when True.

    outclassed=True: By default, the outer class and []'s are included
                     in the return value so it evals to the instance.
                     Set to False for a value that evals to the key.

    Usage:
    >>> from intertwine.problems.models import Problem
    >>> p1 = Problem('Homelessness')
    >>> p1  # interpreter calls repr(p1)
    <BLANKLINE>
    Problem['homelessness']
    >>> p2 = eval(repr(p1))
    >>> p1 is p2
    True
    '''
    if tight:
        sp = ind1 = ''
    else:
        sp, ind1, ind2 = ' ', (' ' * 4 * _lvl), (' ' * 4 * (_lvl + 1))

    try:
        key = self.derive_key()
    except AttributeError:
        if isinstance(self, basestring) and not raw:
            return u"{u}'{s}'".format(u=U_LITERAL, s=self)
        # repr adds u''s and extra escapes for printing unicode
        return repr(self)

    osqb, op, cp, csqb = '[', '(', ')', ']'
    cls = get_class(self).__name__
    if not outclassed and _lvl == 0:
        cls = osqb = csqb = ''

    # Unpack unnamed 1-tuple key unless the value is itself a tuple
    if not named and len(key) == 1 and not isinstance(key[0], tuple):
        op = cp = ''

    try:
        if not named:
            raise ValueError
        key_name = type(key).__name__.replace('_', '.')
        treprs = [u'{f}={trepr}'.format(
                  f=f, trepr=trepr(getattr(key, f),
                                   named, raw, tight, outclassed, _lvl + 1))
                  for f in key._fields]

    except (ValueError, AttributeError):
        key_name = ''
        treprs = [trepr(v, named, raw, tight, outclassed, _lvl + 1)
                  for v in key]

    all_1_line = (u'{cls}{osqb}{key_name}{op}{treprs}{cp}{csqb}'
                  .format(cls=cls, osqb=osqb, key_name=key_name, op=op,
                          treprs=(u',' + sp).join(treprs), cp=cp, csqb=csqb))

    if len(ind1) + len(all_1_line) < Trackable.MAX_WIDTH or tight:
        return all_1_line
    else:
        return (u'{cls}{osqb}{key_name}{op}\n{ind2}{treprs}\n{ind1}{cp}{csqb}'
                .format(cls=cls, osqb=osqb, key_name=key_name, op=op,
                        ind2=ind2, treprs=(u',\n' + ind2).join(treprs),
                        ind1=ind1, cp=cp, csqb=csqb))


def _repr_(self):
    '''Default repr for Trackable classes'''
    # Prefix newline due to ipython pprint bug related to lists
    return '\n' + trepr(self)


def register(self, key=None):
    '''Register self by deriving key if not passed'''
    get_class(self)._register_(self, key)


def deregister(self, key=None):
    '''Deregister self with silent failure, deriving key if needed'''
    get_class(self)._deregister_(self, key)


def destroy(self):
    '''Destroy itself via deregister and delete'''
    self.deregister()
    self.session().delete(self)


def register_update(self, key, _prefix='_', _suffix=''):
    '''Register update

    Register update should be used from within a model's setter property
    when updating a field that is a component of the registry key.

    Register the instance with the new key, derive new field values from
    the key, and update field values without invoking setter properties
    (to avoid infinite recursion).

    Also validate that the newly registered key matches the self-derived
    key. If not, attempt to correct the registry to use the derived key
    before raising KeyInconsistencyError.

    I/O:
    key: new registry key, a namedtuple
    _prefix='_': string prepended to field to identify affixed fields
    _suffix='': string appended to field to identify affixed fields
    return: True iff any fields have been updated with new values
    '''
    derived_key = self.derive_key()
    if key == derived_key:
        return False
    self.register(key)  # Raise KeyConflictError if already registered
    self.deregister(derived_key)
    updated = self._update_(_prefix=_prefix, _suffix=_suffix, **key._asdict())
    self._validate_(key)
    return updated


def _update_(self, _prefix='_', _suffix='', **fields):
    '''
    Update (fields)

    Private method to update fields without invoking setter properties.
    An "affix" (prefix/suffix) convention is applied to find underlying
    fields. An affixed field update is attempted first and fails over to
    the field as given.

    I/O:
    _prefix='_': string prepended to field to identify affixed fields
    _suffix='': string appended to field to identify affixed fields
    **fields: unaffixed fields to be updated
    return: True iff any fields have been updated with new values
    '''
    updated = False
    for field, value in fields.items():
        affixed_field = '{prefix}{field}{suffix}'.format(
            prefix=_prefix, field=field, suffix=_suffix)
        try:
            old_value = getattr(self, affixed_field)

        except AttributeError:
            old_value = getattr(self, field)
            affixed_field = field

        if value == old_value:
            continue

        setattr(self, affixed_field, value)
        updated = True

    if updated:
        get_class(self)._updates.add(self)
    return updated


def _validate_(self, registry_key):
    '''
    Validate (key)

    Validate that the given registered key matches the self-derived key.
    If not, attempt to correct the registry to use the derived key
    before raising KeyInconsistencyError.
    '''
    derived_key = self.derive_key()
    if derived_key != registry_key:
        try:
            self.register(derived_key)
            registry_repaired = True
        except KeyConflictError:
            registry_repaired = False
        finally:
            self.deregister(registry_key)
            raise KeyInconsistencyError(derived_key=derived_key,
                                        registry_key=registry_key,
                                        registry_repaired=registry_repaired)


URIComponents = namedtuple('URIComponents', 'path, query')


def deconstruct(self, query_fields=None, named=True):
    '''
    Deconstruct

    Deconstruct instance into path and query URI components based on the
    Trackable key and specified query_fields. Object key components are
    deconstructed recursively in a depth-first manner.

    query_fields=None: set of query parameter field names
    named=True: by default, path and query are OrderedDicts, in which
        each key includes the full field path delimited by period ('.');
        if False, path and query are lists.
    return: URIComponents namedtuple, in the form, (path, query), where
        path contains the URI path parameter values and query contains
        the URI query string parameter values. The path and query are
        OrderedDicts if named is True and lists otherwise.
    '''
    cls = get_class(self)
    key = self.derive_key()
    return cls.deconstruct_key(key=key, query_fields=query_fields, named=named)


class Trackable(ModelMeta):
    '''
    Trackable

    Trackable is a metaclass for tracking instances. This enables the
    following capabilities:
    - dirty detection
    - caching with failover to query
    - default repr based on natural keys

    Each class of type Trackable maintains a registry of instances. New
    instances are automatically registered and the constructor only
    creates a new instance if it does not already exist. Existing
    instances can be updated with new data using the constructor if a
    'modify' method has been defined.

    Trackable classes are subscriptable (indexed by key) and iterable.
    Invoking the subscript attempts to retrieve the instance
    corresponding to the given key from the registry. If no instance is
    found, it then attempts to retrieve the instance from the database
    and then register it.

    A 'create_key' classmethod must be defined on each Trackable class
    that returns a registry key based on the classes constructor input.
    A 'derive_key' (instance) method must also be defined on each
    Trackable class that returns the registry key based on the
    instance's data.

    Keys are namedtuples of the fields required for uniqueness. While a
    primary key id will work, it is better to use 'natural' key fields
    that have some intrinsic meaning. When a key consists of a single
    field, the key is a one-tuple, though the unpacked field will also
    work as a key as long as it is not itself a tuple.

    Any instance updates that result from the creation or modification
    of an instance using the class constructor can also be tracked. New
    instances are tracked automatically. Modifications of instances may
    be tracked using the '_modified' field on the instance, which is the
    set of modified instances of the same type.
    '''

    # Max width used for Trackable's default repr
    MAX_WIDTH = 79

    ID_TAG = 'id'
    _ID_TAG = '_id'

    # Keep track of all classes that are Trackable
    _classes = {}

    QualifiedKey = namedtuple('QualifiedKey', 'model, key')

    def __new__(meta, name, bases, attr):
        # Track instances for each class of type Trackable
        attr['_instances'] = {}
        # Track any new or modified instances
        attr['_updates'] = set()
        # Provide default __repr__()
        custom_repr = attr.get('__repr__')
        attr['__repr__'] = custom_repr or _repr_
        attr['trepr'] = trepr
        attr['register'] = register
        attr['deregister'] = deregister
        attr['destroy'] = destroy
        attr['register_update'] = register_update
        attr['_update_'] = _update_
        attr['_validate_'] = _validate_
        attr['deconstruct'] = deconstruct
        new_cls = super(Trackable, meta).__new__(meta, name, bases, attr)
        if new_cls.__name__ != 'Base':
            meta._classes[name] = new_cls
        return new_cls

    def __call__(cls, *args, **kwds):
        all_kwds = merge_args(cls.__init__, *args, **kwds) if args else kwds
        key = cls.create_key(**all_kwds)
        if key is None or key == '':
            raise InvalidRegistryKey(key=key, classname=cls.__name__)
        inst = cls._instances.get(key, None)
        if inst is None:
            inst = super(Trackable, cls).__call__(*args, **kwds)
            cls._instances[key] = inst
            cls._updates.add(inst)
        else:
            if not hasattr(cls, 'modify'):
                raise KeyRegisteredAndNoModify(key=key, classname=cls.__name__)
            inst._modified = set()
            cls.modify(inst, **all_kwds)
        if hasattr(inst, '_modified'):
            cls._updates.update(inst._modified)
            del inst._modified
        return inst

    def _create_(cls, _save=True, *args, **kwds):
        inst = cls(*args, **kwds)
        if _save:
            session = cls.session()
            session.add(inst)
            session.flush()
        return inst

    def get_or_create(cls, _query_on_miss=True, _nested_transaction=False,
                      _save=True, *args, **kwds):
        '''
        Get or create

        Given args/kwds as defined by the model's __init__, return the
        existing object if one exists, otherwise create it. The return
        value is a tuple of the object and a boolean indicating whether
        the object was created.

        The existence check first looks in Trackable's registry and upon
        a miss looks in the database. The create fails over to looking
        for an existing object to address race conditions.
        '''
        all_kwds = merge_args(cls.__init__, *args, **kwds) if args else kwds
        key = cls.create_key(**all_kwds)

        try:
            inst = cls.tget(key, query_on_miss=_query_on_miss)
            if not inst:
                raise KeyMissingFromRegistry
            return inst, False

        except KeyMissingFromRegistry:
            session = cls.session()
            try:
                if _nested_transaction:
                    # pysqlite DBAPI driver bugs render SERIALIZABLE isolation,
                    # transactional DDL, and SAVEPOINT non-functional. In order
                    # to use these features, workarounds must be taken. (TODO)
                    # stackoverflow: https://goo.gl/aGibhe
                    with session.begin_nested():
                        inst = cls._create_(_save=_save, *args, **kwds)
                else:
                    inst = cls._create_(_save=_save, *args, **kwds)
                return inst, True

            except IntegrityError:
                session.rollback()

            # Remove once __call__() is refactored to no longer get
            except KeyRegisteredAndNoModify:
                pass

            inst = cls[key]
            return inst, False

    def update_or_create(cls, _query_on_miss=True, _nested_transaction=False,
                         _save=True, _prefix='_', _suffix='', *args, **kwds):
        '''
        Update or create

        Given args/kwds as defined by the model's __init__, look for an
        existing object based on the unique key fields. If found, the
        object is updated based on the remaining fields. If not found,
        a new object is created. The return value is a tuple of the
        object and a boolean indicating whether the object was created.

        The existence check first looks in Trackable's registry and upon
        a miss looks in the database. The create fails over to looking
        for an existing object to address race conditions.
        '''
        all_kwds = merge_args(cls.__init__, *args, **kwds) if args else kwds
        inst, created = cls.get_or_create(
            _query_on_miss=_query_on_miss,
            _nested_transaction=_nested_transaction, _save=_save, **all_kwds)

        if created:
            return inst, True

        inst._update_(_prefix=_prefix, _suffix=_suffix, **all_kwds)
        return inst, False

    def deconstruct_key(cls, key, query_fields=None, named=True, _base=None,
                        _path=None, _query=None, _is_query_param=False):
        '''
        Deconstruct Key

        Deconstruct Trackable key into path and query URI components,
        given the specified query_fields. Object key components are
        deconstructed recursively in a depth-first manner.

        query_fields=None: set of query parameter field names
        named=True: by default, path and query are OrderedDicts, in
            which each key includes the full field path delimited by
            period ('.'); if False, path and query are lists.
        return: URIComponents namedtuple, in the form, (path, query),
            where path contains the URI path parameter values and query
            contains the URI query string parameter values. The path and
            query are OrderedDicts if named is True and lists otherwise.
        '''
        if named:
            path = _path or OrderedDict()
            query = _query or OrderedDict()
            query_fields = set() if query_fields is None else query_fields
            for field, component in key._asdict().items():
                name = '.'.join((_base, field)) if _base else field

                is_query_param = (_is_query_param or field in query_fields or
                                  name in query_fields)

                try:
                    component_key = component.derive_key()
                    component_cls = get_class(component)
                    component_path, component_query = (
                        component_cls.deconstruct_key(
                            key=component_key, query_fields=query_fields,
                            named=True, _base=name, _path=path, _query=query,
                            _is_query_param=is_query_param))
                    path.update(component_path)
                    query.update(component_query)

                except AttributeError:
                    if is_query_param:
                        query[name] = component
                    else:
                        path[name] = component

            return URIComponents(path, query)
        else:
            # If named is False, recurse with names but don't return them
            path, query = cls.deconstruct_key(key, query_fields=query_fields,
                                              named=True)
            return URIComponents(tuple(path.values()), tuple(query.values()))

    def reconstruct(cls, path=None, query=None, retrieve=False, as_key=False,
                    query_fields=None, _is_query_param=False, _base=None,
                    _path_list=None, _query_list=None,
                    _path_ismap=None, _query_ismap=None, _pidx=0, _qidx=0):
        '''
        Reconstruct

        Instantiate from deconstructed object's key components by
        recursively reconstructing in a depth-first manner.

        I/O:
        path=None: URI path parameter values as a list or OrderedDict
        query=None: URI query string values as a list or dict
        retrieve=False: if retrieve is False (default), instantiate
            foreign keys during reconstruction; if retrieve is True,
            reconstruct via single query, but forgo Trackable caching;
            if as_key is also True, return hyper_key instead of instance
        as_key=False: if not as_key (default), return instance;
            if as_key is True and retrieve is False, return key;
            if as_key is True and retrieve is True, return hyper_key
        query_fields=None: set of fields to be sourced from query string
        return: instance (or key if as_key) matching given components
        raise: if no instance is found:
            KeyMissingFromRegistryAndDatabase (retrieve=False)
            NoResultFound (retrieve=True)
        '''
        if _base is None:
            if isiterator(path):
                path = tuple(path)
            _path_ismap = hasattr(path, 'items')
            _query_ismap = hasattr(query, 'items')
            if _path_ismap and not isinstance(path, OrderedDict):
                raise TypeError('path must be ordered')
            _path_list = list(path.values()) if _path_ismap else path
            _query_list = list(query.values()) if _query_ismap else query

        query_fields = query_fields or set()
        key_components = []
        fields = cls.Key._fields

        for field in fields:
            name = '.'.join((_base, field)) if _base else field

            is_query_param = (_is_query_param or field in query_fields or
                              (_query_ismap and name in query))

            try:
                component_cls = cls.related_model(field)
                component_value, _pidx, _qidx = component_cls.reconstruct(
                    path=path, query=query, retrieve=retrieve, as_key=False,
                    query_fields=query_fields, _is_query_param=is_query_param,
                    _base=name, _path_list=_path_list, _query_list=_query_list,
                    _path_ismap=_path_ismap, _query_ismap=_query_ismap,
                    _pidx=_pidx, _qidx=_qidx)
                key_components.append(component_value)

            except AttributeError:
                if is_query_param:
                    key_components.append(query[name] if _query_ismap
                                          else _query_list[_qidx])
                    _qidx += 1
                else:
                    key_components.append(path[name] if _path_ismap
                                          else _path_list[_pidx])
                    _pidx += 1

        key = cls.create_key(*key_components)

        if as_key:
            return key if _base is None else (key, _pidx, _qidx)

        if retrieve:
            return cls.retrieve(key) if _base is None else (key, _pidx, _qidx)

        inst = cls[key]
        return inst if _base is None else (inst, _pidx, _qidx)

    def retrieve(cls, hyper_key, _alias=None, _query=None):
        '''
        Retrieve

        Instantiate from hyper key by recursively building query in a
        depth-first manner and then executing it with the expectation
        there will be a single result.

        I/O:
        hyper_key: Trackable key in which objects are replaced by keys
            Example:
            ProblemConnection_CausalKey(
                axis=u'causal',
                driver=Problem_Key(human_id=u'domestic_violence'),
                impact=Problem_Key(human_id=u'homelessness')
            )
        _alias=None: Private parameter containing SQLAlchemy alias for
            each foreign key join; used to distinguish between multiple
            joins to the same table (e.g. driver vs. impact above)
        _idx=None: private parameter for tracking the index in recursion
        return: instance matching given query_key
        raise: NoResultFound if no instance is found
        '''
        query = _query or cls.query
        if hasattr(cls, 'mutate_key'):
            hyper_key = cls.mutate_key(hyper_key)
        for name, value in hyper_key._asdict().items():
            field = getattr(_alias, name) if _alias else getattr(cls, name)

            if not isnamedtuple(value):
                query = query.filter(field == value)

            else:
                component_key = value
                component_cls = cls.key_model(component_key)
                alias = aliased(component_cls)  # UnmappedClassError if invalid
                query = query.join(alias, field)
                query = component_cls.retrieve(
                    hyper_key=component_key, _alias=alias, _query=query)

        return query.one() if _query is None else query

    def reconstitute(cls, hyper_key):
        '''
        Reconstitute

        I/O:
        hyper_key: Trackable key in which objects are replaced by keys
            Example:
            ProblemConnection_CausalKey(
                axis=u'causal',
                driver=Problem_Key(human_id=u'domestic_violence'),
                impact=Problem_Key(human_id=u'homelessness')
            )
        return: instance matching given query_key
        raise: KeyMissingFromRegistryAndDatabase if no instance is found
        '''
        key_components = []

        for name, value in hyper_key._asdict().items():

            if not isnamedtuple(value):
                key_components.append(value)

            else:
                component_key = value
                component_cls = cls.key_model(component_key)
                component_inst = component_cls.reconstitute(component_key)
                key_components.append(component_inst)

        key = cls.create_key(*key_components)
        inst = cls[key]
        return inst

    def instrumented_attribute(cls, field_name):
        '''
        Instrumented Attribute

        Retrieve instrumented attribute given field/relation name.

        I/O:
        field_name: name of a foreign key field or relation
        raise: AttributeError on failure
        return: SQAlchemy instrumented attribute
        '''
        field = None

        try:
            field = getattr(cls, field_name)  # Raise if no such member
            if not isinstance(field, InstrumentedAttribute):
                raise AttributeError(
                    "'{cls}.{field}' not an InstrumentedAttribute"
                    .format(cls=cls.__name__, field=field_name))

        except AttributeError as e1:
            try:
                if field_name[-3:] == cls._ID_TAG:
                    raise
                field_name_with_id = field_name + cls._ID_TAG
                if not hasattr(cls, field_name_with_id):
                    raise AttributeError(
                        str(e1) + ", '{field_id}' does not exist"
                        .format(field_id=field_name_with_id))
                field = getattr(cls, field_name_with_id)
                if not isinstance(field, InstrumentedAttribute):
                    raise AttributeError(
                        str(e1) + ", '{field_id}' not instrumented"
                        .format(field_id=field_name_with_id))
            except AttributeError as e2:
                try:
                    # Find underlying field if field is a synonym
                    # Only works once ORM has loaded an instance
                    underlying_name = field.property.key  # Non-synonym raises
                except AttributeError as e3:
                    raise AttributeError(
                        str(e3) + " and '{field}' not a synonym"
                        .format(field=field_name))

                if not hasattr(cls, underlying_name):
                    raise AttributeError(
                        str(e2) + ", and underlying '{field}' does not exist"
                        .format(field=underlying_name))
                field = getattr(cls, underlying_name)
                if not isinstance(field, InstrumentedAttribute):
                    raise AttributeError(
                        str(e2) + ", and underlying '{field}' not instrumented"
                        .format(field=underlying_name))

        return field

    def related_model(cls, field_name):
        '''
        Related Model

        Retrieve related model given foreign key field or relation name.

        I/O:
        field_name: name of a foreign key field or relation
        raise: AttributeError on failure
        return: related SQAlchemy model
        '''
        field = cls.instrumented_attribute(field_name)
        try:
            return field.property.mapper.entity
        except AttributeError:
            try:
                foreign_key = tuple(field.expression.foreign_keys)[0]
            except (AttributeError, IndexError):
                raise AttributeError('Field has no mapping or foreign key')
            try:
                related_table_name = foreign_key.target_fullname.split('.')[0]
                # return cls.table_model_map[related_table_name]
                return cls.table_model(related_table_name)
            except (AttributeError, KeyError):
                raise AttributeError("No model found for field's foreign key")

    def key_model(cls, key):
        '''Retrieve model from Trackable key'''
        key_name = type(key).__name__
        for model_name in dehumpify(key_name):
            try:
                return cls._classes[model_name]
            except KeyError:
                pass

    def table_model(cls, table_name):
        '''Retrieve model given table name'''
        try:
            return cls._table_model_map[table_name]
        except AttributeError:
            cls._table_model_map = build_table_model_map(cls)
            return cls._table_model_map[table_name]

    def tget(cls, key, default=None, query_on_miss=True):
        '''
        Trackable get (tget)

        Given a key, gets the corresponding instance from the registry.
        If the key is unregistered and query_on_miss is True (default),
        the database is queried. Returns any instance found, otherwise
        returns the default.

        I/O:
        key:
            A natural key tuple as defined by the create_key/derive_key
            methods on the Trackable class. In the case of a 1-tuple,
            the key may be the unpacked 1-tuple (the value within).

        default=None:
            The value returned if no instance is found.

        query_on_miss=True:
            When True, the database is queried if the key is not found
            in the registry.
        '''
        try:
            return cls._instances[key]
        except KeyError:
            pass

        if not isinstance(key, tuple):
            key = (key,)  # convert non-tuple to 1-tuple
            try:
                return cls._instances[key]
            except KeyError:
                pass

        if not query_on_miss:
            return default

        key = cls.create_key(*key)  # convert tuple to key
        key_dict = key._asdict()
        try:
            instance = cls.query.filter_by(**key_dict).first()
            if instance is None:
                raise ValueError

        # Field doesn't exist or it's not a SQLAlchemy field
        except (InvalidRequestError, ValueError):
            mapper = class_mapper(cls)
            props = set(p.key for p in mapper.iterate_properties)

            for field, value in key._asdict().items():
                if field not in props:
                    del key_dict[field]
                    key_dict[field + cls._ID_TAG] = getattr(value, cls.ID_TAG)

            instance = cls.query.filter_by(**key_dict).first()

        if instance is None:
            return default

        cls._instances[key] = instance
        return instance

    def __getitem__(cls, key):
        instance = cls.tget(key)
        if instance is None:
            raise KeyMissingFromRegistryAndDatabase(key=key)
        return instance

    def __setitem__(cls, key, inst):
        derived_key = inst.derive_key()
        if derived_key != key:
            raise KeyInconsistencyError(derived_key=derived_key,
                                        registry_key=key,
                                        registry_repaired=True)
        cls._register_(inst, key)

    def __delitem__(cls, key):
        # Raise KeyError if unregistered
        inst = cls._instances[key]
        cls._deregister_(inst, key)

    def __iter__(cls):
        for inst in cls._instances.values():
            yield inst

    def __repr__(cls):
        return '.'.join((inspect.getmodule(cls).__name__, cls.__name__))

    def _register_(cls, inst, key=None):
        '''Register instance, deriving key if not provided'''
        key = key or inst.derive_key()
        existing = cls.tget(key)
        if existing is not None and existing is not inst:
            raise KeyConflictError(key=key)
        cls._instances[key] = inst

    def _deregister_(cls, inst, key=None):
        '''Deregister instance with silent failure, deriving key if needed'''
        key = key or inst.derive_key()
        cls._instances.pop(key, None)
        cls._updates.discard(inst)

    @classmethod
    def register_existing(meta, session, *args):
        '''
        Register existing instances of Trackable classes

        Takes a session and optional Trackable classes as input. The
        specified classes have their instances loaded from the database
        and registered. If no classes are provided, instances of all
        Trackable classes are loaded from the database and registered.
        If a class is not Trackable, a TypeError is raised.
        '''
        classes = meta._classes.values() if len(args) == 0 else args
        for cls in classes:
            if cls.__name__ not in meta._classes:
                raise TypeError('{} not Trackable.'.format(cls.__name__))
            instances = session.query(cls).all()
            for inst in instances:
                cls._instances[inst.derive_key()] = inst

    @classmethod
    def clear_instances(meta, *args):
        '''
        Clear instances tracked by Trackable classes

        If no arguments are provided, all Trackable classes have their
        instances cleared from the registry. If one or more classes are
        passed as input, only these classes have their instances
        cleared. If a class is not Trackable, a TypeError is raised.
        '''
        classes = meta._classes.values() if len(args) == 0 else args
        for cls in classes:
            if cls.__name__ not in meta._classes:
                raise TypeError('{} not Trackable.'.format(cls.__name__))
            cls._instances = {}

    @classmethod
    def clear_updates(meta, *args):
        '''
        Clear updates tracked by Trackable classes

        If no arguments are provided, all Trackable classes have their
        updates cleared (i.e. reset). If one or more classes are passed
        as input, only these classes have their updates cleared. If a
        class is not Trackable, a TypeError is raised.
        '''
        classes = meta._classes.values() if len(args) == 0 else args
        for cls in classes:
            if cls.__name__ not in meta._classes:
                raise TypeError('{} not Trackable.'.format(cls.__name__))
            cls._updates = set()

    @classmethod
    def clear_all(meta, *args):
        '''
        Clear all instances/updates tracked by Trackable classes

        If no arguments are provided, all Trackable classes have their
        updates cleared (i.e. reset). If one or more classes are passed
        as input, only these classes have their updates cleared. If a
        class is not Trackable, a TypeError is raised.
        '''
        meta.clear_instances(*args)
        meta.clear_updates(*args)

    @classmethod
    def catalog_updates(meta, *args):
        '''
        Catalog updates tracked by Trackable classes

        Returns a dictionary keyed by class name, where the values are
        the corresponding sets of updated instances.

        If no arguments are provided, updates for all Trackable classes
        are included. If one or more classes are passed as input, only
        updates from these classes are included. If a class is not
        Trackable, a TypeError is raised.
        '''
        classes = meta._classes.values() if len(args) == 0 else args
        updates = {}
        for cls in classes:
            if cls.__name__ not in meta._classes:
                raise TypeError('{} not Trackable.'.format(cls.__name__))
            if len(cls._updates) > 0:
                updates[cls.__name__] = cls._updates
        return updates
