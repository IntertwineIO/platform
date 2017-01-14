#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect

from alchy.model import ModelMeta
from past.builtins import basestring

from .exceptions import InvalidRegistryKey, KeyRegisteredAndNoModify


def trepr(self, named=False, tight=False, raw=True, outclassed=True, _lvl=0):
    ''''Trackable Representation', Default repr for Trackable classes

    Returns a string that when evaluated returns the instance. It works
    by utilizing the registry and indexability provided by Trackable.
    The following inputs may be specified:

    named=False:     By default, named tuples are treated as regular
                     tuples. Set to True to print named tuple info.

    tight=False:     By default, newlines/indents are added when a line
                     exceeds max_width. Excludes whitespace when True.

    raw=True:        By default, escaped values are escaped again to
                     display raw values when printed, just as repr does.
                     Set to False for unicode characters to print as
                     intended or if the unicode must be correct when not
                     printed, such as when embedding in JSON.

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
        sp = ind = ''
    else:
        sp, ind, ind_p1 = ' ', (' ' * 4 * _lvl), (' ' * 4 * (_lvl + 1))

    if self is None:
        return repr(self)
    elif isinstance(self, basestring):
        # repr adds u''s and extra escapes for printing unicode
        return repr(self) if raw else u"u'{}'".format(self)

    key = self.derive_key()
    if not isinstance(key, tuple):
        key = (key,)
    if len(key) == 1:
        op = cp = ''

    cls = self.__class__.__name__

    osqb, op, cp, csqb = '[', '(', ')', ']'
    if not outclassed and _lvl == 0:
        cls = osqb = csqb = ''

    try:
        if not named:
            raise ValueError
        key_name = (u'{cls_name}.{key_cls_name}'
                    .format(cls_name=self.__class__.__name__,
                            key_cls_name=key.__class__.__name__))
        treprs = [u'{f}={trepr}'.format(
                  f=f, trepr=trepr(getattr(key, f),
                                   named, tight, raw, outclassed, _lvl + 1))
                  for f in key._fields]

    except (ValueError, AttributeError):
        key_name = ''
        treprs = [trepr(v, named, tight, raw, outclassed, _lvl + 1)
                  for v in key]

    all_1_line = (u'{cls}{osqb}{key_name}{op}{treprs}{cp}{csqb}'
                  .format(cls=cls, osqb=osqb, key_name=key_name, op=op,
                          treprs=(u',' + sp).join(treprs), cp=cp, csqb=csqb))

    if len(ind) + len(all_1_line) < Trackable.max_width or tight:
        return all_1_line
    else:
        return (u'{cls}{osqb}{key_name}{op}\n{ind_p1}{treprs}\n{ind}{cp}{csqb}'
                .format(cls=cls, osqb=osqb, key_name=key_name, op=op,
                        ind_p1=ind_p1, treprs=(u',\n' + ind_p1).join(treprs),
                        ind=ind, cp=cp, csqb=csqb))


def _repr_(self):
    '''Default repr for Trackable classes'''
    # Prefix newline due to ipython pprint bug related to lists
    return '\n' + trepr(self)


class Trackable(ModelMeta):
    '''Metaclass providing ability to track instances

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

    A 'create_key' static method must be defined on each Trackable class
    that returns a registry key based on the classes constructor input.
    A 'derive_key' (instance) method must also be defined on each
    Trackable class that returns the registry key based on the
    instance's data.

    Any updates that result from the creation or modification of an
    instance using the class constructor can also be tracked. New
    instances are tracked automatically. Modifications of instances may
    be tracked using the '_modified' field on the instance, which is the
    set of instances of the same type that were modified.
    '''

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
        custom_repr = attr.get('__repr__', None)
        attr['__repr__'] = _repr_ if custom_repr is None else custom_repr
        attr['trepr'] = trepr
        new_cls = super(Trackable, meta).__new__(meta, name, bases, attr)
        if new_cls.__name__ != 'Base':
            meta._classes[name] = new_cls
        return new_cls

    def __call__(cls, *args, **kwds):
        # Convert args to kwds for create_key() and modify() so
        # parameter order need not match __init__()
        all_kwds = kwds.copy()
        arg_names = inspect.getargspec(cls.__init__)[0][1:len(args) + 1]
        for arg_name, arg in zip(arg_names, args):
            all_kwds[arg_name] = arg
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

    def __getitem__(cls, key):
        try:
            return cls._instances[key]
        except KeyError:
            if not isinstance(key, tuple):
                key = cls.Key(key)  # convert non-tuple to namedtuple
                try:
                    return cls._instances[key]
                except KeyError:
                    pass
            else:
                key = cls.Key(*key)  # convert tuple to namedtuple

        instance = cls.query.filter_by(**key._asdict()).first()

        if instance is not None:
            cls[key] = instance
        return instance

    def __setitem__(cls, key, value):
        cls._instances[key] = value

    def __iter__(cls):
        for inst in cls._instances.values():
            yield inst

    def register(cls, inst):
        key = inst.derive_key()
        existing = cls[key]
        if existing is not None and existing is not inst:
            raise ValueError('{} is already registered.'.format(key))
        cls[key] = inst

    def unregister(cls, inst):
        key = inst.derive_key()
        cls._instances.pop(key)  # Throw exception if key not found
        cls._updates.discard(key)  # Fail silently if key not found

    @classmethod
    def register_existing(meta, session, *args):
        '''Register existing instances of Trackable classes (in the DB)

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
        '''Clear instances tracked by Trackable classes

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
        '''Clear updates tracked by Trackable classes

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
    def catalog_updates(meta, *args):
        '''Catalog updates tracked by Trackable classes

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
