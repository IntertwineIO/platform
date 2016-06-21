#!/usr/bin/env python
import inspect
import re

from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declared_attr
from alchy.model import ModelMeta
from intertwine.exceptions import InvalidRegistryKey, KeyRegisteredAndNoModify


def camelCaseTo_snake_case(string):
    '''Converts CamelCase to snake_case'''
    patterns = [
        (r'(.)([0-9]+)', r'\1_\2'),
        (r'([a-z]+)([A-Z])', r'\1_\2'),
    ]
    engines = [
        (pattern, replacement, re.compile(pattern))
        for pattern, replacement in patterns
    ]
    for data in engines:
        pattern, replacement, eng = data
        string = eng.sub(replacement, string)
    string = string.lower()
    return string


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


def stringify(thing, limit=20, level=0):
    '''Stringify

    Converts things into nicely formatted unicode strings for printing.
    The input, 'thing', may be a 'literal' (e.g. integer, boolean,
    string, etc.), a custom object, a list/tuple, or a dictionary.
    Custom objects are included using their own unicode methods, but are
    appropriately indented. Lists, tuples and dictionaries recursively
    stringify their items.

    Dictionary keys with empty values are excluded. Values that
    are a single line are included on the same line as the key. Multi-
    line values are listed below the key and indented further.

    An optional 'limit' parameter caps the number of list/tuple/dict
    items to include. If capped, the cap and total number of items is
    noted. If the limit is negative, no cap is applied.
    '''
    limit = float('inf') if limit < 0 else limit
    indent = level*4*' '
    len_thing = -1
    strings = []

    # If a list/tuple, stringify and add each item
    if isinstance(thing, (list, tuple)):
        len_thing = len(thing)  # Used for limit message later
        for i, t in enumerate(thing):
            if i == limit:
                break
            strings.append(stringify(t, limit, level))

    # If a dict, add each key and stringify + further indent each value
    elif isinstance(thing, dict):
        len_thing = len(thing)  # Used for limit message later
        i = 0
        for k, v in thing.iteritems():
            if i == limit:
                break
            v_str = stringify(v, limit, level+1)
            # If key has an empty value, don't include it
            if len(v_str.strip()) == 0:
                continue
            # If there's one value, put the key and value on one line
            elif len(v_str.split('\n')) == 1:
                strings.append(u'{indent}{key}: {value}'.format(
                                indent=indent, key=k, value=v_str.strip()))
            # There are multiple values, so list them below the key
            else:
                strings.append(u'{indent}{key}:\n{value}'.format(
                                indent=indent, key=k, value=v_str))
            i += 1

    # If a custom object, use its __unicode__ method, but indent it
    elif hasattr(thing, '__dict__'):
        strings.append(
            (('\n' + indent).join('' + unicode(thing).split('\n')))[1:])

    # It is a 'primitive' (e.g. integer, boolean, string, etc.)
    else:
        strings.append(u'{indent}{thing}'.format(indent=indent, thing=thing))

    if len_thing > limit:
        strings.append('{indent}({limit} of {total})'.format(
                        indent=indent, limit=limit, total=len_thing))

    return '\n'.join(strings)


def __trepr__(self, tight=False, raw=True, outclassed=True, level=0):
    ''''Trackable Representation', Default repr for Trackable classes

    Returns a string that when evaluated returns the instance. It works
    by utilizing the registry and indexability provided by Trackable.
    The following inputs may be specified:

    tight=False:     By default, newlines/indents are added when a line
                     exceeds max_width. Excludes whitespace when True.

    raw=True:        By default, escaped values are escaped again to
                     display raw values properly when printed. Set to
                     False if the trepr needs to be correct when not
                     printed, such as when embedding in JSON.

    outclassed=True: By default, the outer class and []'s are included
                     in the string to uniquely identify the instance and
                     so the string evals to the instance. Set to False
                     to return a string that evals to just the key.

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
        indent = space = ''
    else:
        indent, space = ' '*4*level, ' '

    if self is None or isinstance(self, basestring):
        # repr adds u''s and extra escapes for printing unicode
        selfie = repr(self) if raw else u"u'{}'".format(self)
        return u'{indent}{selfie}'.format(indent=indent, selfie=selfie)

    key = self.derive_key()
    cls = u'{indent}{cls}'.format(indent=indent, cls=self.__class__.__name__)

    osqb, op, cp, csqb = '[', '(', ')', ']'
    if not outclassed and level == 0:
        cls = osqb = csqb = ''

    if not isinstance(key, tuple):
        op = cp = ''
        key = (key,)

    treprs = map(lambda x: __trepr__(x, tight, raw, outclassed, level+1), key)
    all_1_line = (cls + osqb + op +
                  (',' + space).join(map(unicode.strip, treprs)) + cp + csqb)

    if len(all_1_line) < Trackable.max_width or tight:
        return unicode(all_1_line)
    else:
        return unicode(cls + osqb + op + '\n' + ',\n'.join(treprs) +
                       '\n{indent}'.format(indent=indent) + cp + csqb)


def __repr__(self):
    '''Default repr for Trackable classes'''
    # Prefix newline due to ipython pprint bug related to lists
    return '\n' + self.__trepr__()


class Trackable(ModelMeta):
    '''Metaclass providing ability to track instances

    Each class of type Trackable maintains a registry of instances and
    only creates a new instance if it does not already exist. Existing
    instances can be updated with new data using the constructor if a
    'modify' method has been defined.

    A 'create_key' staticmethod must be defined on each Trackable class
    that returns a registry key based on the classes constructor input.
    A 'derive_key' (instance) method must also be defined on each
    Trackable class that returns the registry key based on the
    instance's data.

    Any updates that result from the creation or modification of an
    instance using the class constructor can also be tracked. New
    instances are tracked automatically. Modifications of instances may
    be tracked using the '_modified' field on the instance, which is the
    set of instances of the same type that were modified.

    A class of type Trackable is subscriptable (indexed by key) and
    iterable.
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
        repr_fn = attr.get('__repr__', None)
        if repr_fn is None:
            # Provide default __repr__()
            attr['__repr__'] = __repr__
            attr['__trepr__'] = __trepr__
        new_cls = super(Trackable, meta).__new__(meta, name, bases, attr)
        if new_cls.__name__ != 'Base':
            meta._classes[name] = new_cls
        return new_cls

    def __call__(cls, *args, **kwds):
        # Convert args to kwds for create_key() and modify() so
        # parameter order need not match __init__()
        all_kwds = kwds.copy()
        arg_names = inspect.getargspec(cls.__init__)[0][1:len(args)+1]
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
        return cls._instances.get(key, None)

    def __setitem__(cls, key, value):
        cls._instances[key] = value

    def __iter__(cls):
        for inst in cls._instances.values():
            yield inst

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
            updates[cls.__name__] = cls._updates
        return updates
