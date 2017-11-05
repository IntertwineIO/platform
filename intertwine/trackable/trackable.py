#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import sys
from itertools import islice

from alchy.model import ModelMeta
from past.builtins import basestring
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from .exceptions import (
    InvalidRegistryKey, KeyConflictError, KeyInconsistencyError,
    KeyMissingFromRegistry, KeyMissingFromRegistryAndDatabase,
    KeyRegisteredAndNoModify)

# Python version compatibilities
if sys.version_info < (3,):
    lzip = zip  # legacy zip returning list of tuples
    from itertools import izip as zip
    U_LITERAL = 'u'
else:
    unicode = str
    U_LITERAL = ''


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
                     exceeds max_width. Excludes whitespace when True.

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
    cls = self.__class__.__name__
    if not outclassed and _lvl == 0:
        cls = osqb = csqb = ''

    # Unpack 1-tuple key unless the value is itself a tuple
    if len(key) == 1 and not isinstance(key[0], tuple):
        op = cp = ''

    try:
        if not named:
            raise ValueError
        key_name = (u'{cls_name}.{key_cls_name}'
                    .format(cls_name=self.__class__.__name__,
                            key_cls_name=Trackable.KEY_NAMEDTUPLE_NAME))
        #                     key_cls_name=key.__class__.__name__))
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

    if len(ind1) + len(all_1_line) < Trackable.max_width or tight:
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
    self.__class__._register_(self, key)


def deregister(self, key=None):
    '''Deregister self with silent failure, deriving key if needed'''
    self.__class__._deregister_(self, key)


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
        self.__class__._updates.add(self)
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

    KEY_NAMEDTUPLE_NAME = 'Key'

    # Keep track of all classes that are Trackable
    _classes = {}

    # Max width used for Trackable's default repr
    max_width = 79

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
        new_cls = super(Trackable, meta).__new__(meta, name, bases, attr)
        if new_cls.__name__ != 'Base':
            meta._classes[name] = new_cls
        return new_cls

    def __call__(cls, *args, **kwds):
        all_kwds = cls.merge_args(*args, **kwds)
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

    def _create_(cls, *args, **kwds):
        inst = cls(*args, **kwds)
        session = cls.session()
        session.add(inst)
        session.flush()
        return inst

    def get_or_create(cls, _query_on_miss=True, _nested_transaction=True,
                      *args, **kwds):
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
        all_kwds = cls.merge_args(*args, **kwds)
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
                        inst = cls._create_(*args, **kwds)
                else:
                    inst = cls._create_(*args, **kwds)
                return inst, True

            except IntegrityError:
                session.rollback()

            # Remove once __call__() is refactored to no longer get
            except KeyRegisteredAndNoModify:
                pass

            inst = cls[key]
            return inst, False

    def update_or_create(cls, _query_on_miss=True, _nested_transaction=True,
                         _prefix='_', _suffix='', *args, **kwds):
        '''
        Update or create

        Given args/kwds as defined by the model's __init__, look for an
        existing object based on the unique key fields. If found, the
        object is updated based on the remaining fields. If not found,
        an new object is created. The return value is a tuple of the
        object and a boolean indicating whether the object was created.

        The existence check first looks in Trackable's registry and upon
        a miss looks in the database. The create fails over to looking
        for an existing object to address race conditions.
        '''
        all_kwds = cls.merge_args(*args, **kwds)
        inst, created = cls.get_or_create(
            _query_on_miss=_query_on_miss,
            _nested_transaction=_nested_transaction, **all_kwds)

        if created:
            return inst, True

        inst._update_(_prefix=_prefix, _suffix=_suffix, **all_kwds)
        return inst, False

    def merge_args(cls, *args, **kwds):
        '''
        Convert args to kwds for create_key(), modify(), etc. so
        parameter order need not match __init__()
        '''
        if not args:
            return kwds

        try:  # py3
            init_args = inspect.getfullargspec(cls.__init__).args
        except AttributeError:  # py2
            init_args = inspect.getargspec(cls.__init__).args

        arg_names_gen = islice(init_args, 1, len(args) + 1)

        for arg_name, arg_value in zip(arg_names_gen, args):
            if arg_name in kwds:
                raise TypeError('Keyword arg {kwd_name} conflicts with '
                                'positional arg'.format(kwd_name=arg_name))
            kwds[arg_name] = arg_value

        return kwds

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

        key = cls.Key(*key)  # convert tuple to namedtuple
        key_dict = key._asdict()
        try:
            instance = cls.query.filter_by(**key_dict).first()

        except InvalidRequestError:  # cls does not have a field
            for field, value in key._asdict().items():
                if not hasattr(cls, field):
                    del key_dict[field]
                    key_dict[field + '_id'] = getattr(value, 'id')

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

    def __repr__(cls):
        return '.'.join((inspect.getmodule(cls).__name__, cls.__name__))

    def __str__(cls):
        return unicode(cls).encode('utf-8')

    def __unicode__(cls):
        return cls.__name__

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
