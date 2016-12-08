#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numbers
import re
import sys
from collections import namedtuple, OrderedDict
from functools import partial
from inspect import getargspec, getargvalues, stack
from itertools import chain
from mock import create_autospec
from operator import eq, itemgetter

if sys.version.startswith('3'):
    imap = map
    izip = zip
else:
    from itertools import imap, izip


class Sentinel(object):
    _id = 0

    def __init__(self):
        self.id = self.__class__._id
        self.__class__._id += 1

    def __repr__(self):
        return '<{cls}: {id}>'.format(cls=self.__class__.__name__, id=self.id)


class InsertableOrderedDict(object):
    '''Reimplementation of OrderedDict that supports insertion'''
    sentinel = Sentinel()
    ValueTuple = namedtuple('InsertableOrderedDictValueTuple',
                            'value, next, prior')

    def _initialize(self, _iter_or_map, _as_iter):
        self._iod = {}
        s = self.sentinel
        keygetter = itemgetter(0) if _as_iter else lambda x: x
        valgetter = itemgetter(1) if _as_iter else lambda x: _iter_or_map[x]
        peekable = PeekableIterator(_iter_or_map, sentinel=s)
        self._beg = keygetter(peekable.peek()) if peekable.has_next() else s
        prior_key = s
        for obj in peekable:
            key, value = keygetter(obj), valgetter(obj)
            if self._iod.get(key, s) is not s:
                raise KeyError(u"Duplicate key: '{}'".format(key))
            next_key = keygetter(peekable.peek()) if peekable.has_next() else s
            self._iod[key] = (value, next_key, prior_key)
            prior_key = key
        self._end = key if self._beg is not s else s

    def __init__(self, _iter_or_map=(), *args, **kwds):
        try:
            self._initialize(_iter_or_map, _as_iter=True)
        except IndexError:
            self._initialize(_iter_or_map, _as_iter=False)
        super(InsertableOrderedDict, self).__init__(*args, **kwds)

    def insert(self, insert_key, key, value, after=False):
        '''insert a key/value pair

        I/O:
        insert_key  Reference key used for insertion
        key         Key to be inserted
        value       Value to be inserted
        after=False If True, inserts after reference key
        return      None
        '''
        if after:
            next_key = self._iod[insert_key][1]
            prior_key = insert_key
        else:
            next_key = insert_key
            prior_key = self._iod[insert_key][-1]

        self._insert_between(next_key=next_key, prior_key=prior_key,
                             key=key, value=value)

    def append(self, key, value):
        self._insert_between(next_key=self.sentinel, prior_key=self._end,
                             key=key, value=value)

    def prepend(self, key, value):
        self._insert_between(next_key=self._beg, prior_key=self.sentinel,
                             key=key, value=value)

    def _insert_between(self, next_key, prior_key, key, value):
        if self.get(key, self.sentinel) is not self.sentinel:
            raise KeyError(u"Key already exists: '{}'".format(key))

        self._iod[key] = value, next_key, prior_key

        if next_key is not self.sentinel:
            next_item = self._iod[next_key]
            self._iod[next_key] = (next_item[0], next_item[1], key)
        else:
            self._end = key

        if prior_key is not self.sentinel:
            prior_item = self._iod[prior_key]
            self._iod[prior_key] = (prior_item[0], key, prior_item[-1])
        else:
            self._beg = key

    def copy(self):
        return self.__class__(self)

    def __repr__(self):
        cls = self.__class__.__name__
        return u'{cls}({tuples})'.format(cls=cls, tuples=tuple(self.items()))

    def __len__(self):
        return len(self._iod)

    def __getitem__(self, key):
        return self._iod[key][0]

    def __setitem__(self, key, value):
        try:
            item = self._iod[key]
            self._iod[key] = (value, item[1], item[-1])
        except KeyError:
            self.append(key, value)

    def __delitem__(self, key):
        _, next_key, prior_key = self._iod[key]
        if next_key is not self.sentinel:
            next_item = self._iod[next_key]
            self._iod[next_key] = (next_item[0], next_item[1], prior_key)
        else:
            self._end = prior_key

        if prior_key is not self.sentinel:
            prior_item = self._iod[prior_key]
            self._iod[prior_key] = (prior_item[0], next_key, prior_item[-1])
        else:
            self._beg = next_key

        del self._iod[key]

    def __contains__(self, key):
        return key in self._iod

    def has_key(self, key):
        return key in self._iod

    def get(self, key, default=None):
        item = self._iod.get(key, self.sentinel)
        return item[0] if item is not self.sentinel else default

    def clear(self):
        self._iod.clear()
        self._beg = self.sentinel
        self._end = self.sentinel

    def __iter__(self):
        key = self._beg
        while key is not self.sentinel:
            yield key
            key = self._iod[key][1]

    def __reversed__(self):
        key = self._end
        while key is not self.sentinel:
            yield key
            key = self._iod[key][-1]

    def reverse(self):
        for key, item in self._iod.items():
            self._iod[key] = (item[0], item[-1], item[1])
        self._beg, self._end = self._end, self._beg

    def items(self):
        key = self._beg
        while key is not self.sentinel:
            yield (key, self._iod[key][0])
            key = self._iod[key][1]

    def keys(self):
        return self.__iter__()

    def values(self):
        key = self._beg
        while key is not self.sentinel:
            yield self._iod[key][0]
            key = self._iod[key][1]

    # def items(self):
    #     return [item for item in self.iteritems()]

    # def keys(self):
    #     return [key for key in self.iterkeys()]

    # def values(self):
    #     return [value for value in self.itervalues()]

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        if isinstance(other, (OrderedDict, InsertableOrderedDict)):
            return all(imap(eq, self.items(), other.items()))
        return all((eq(self[key], other.get(key)) for key in self))

    def __ne__(self, other):
        return not self.__eq__(other)


class PeekableIterator(object):
    '''Iterable that supports peeking at the next item'''
    def __init__(self, iterable, sentinel=object(), *args, **kwds):
        self.iterable = iter(iterable)
        self.sentinel = sentinel
        self.next_item = next(self.iterable, self.sentinel)
        super(PeekableIterator, self).__init__(*args, **kwds)

    def next(self):
        rv = self.next_item
        self.next_item = next(self.iterable, self.sentinel)
        return rv

    def has_next(self):
        return self.next_item is not self.sentinel

    def peek(self):
        return self.next_item

    def __iter__(self):
        while self.has_next():
            yield self.next()


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


def kwargify(arg_names=None, arg_values=None, kwargs=None,
             parg_names=None, parg_values=None, pargs=None,
             exclude=None, selfish=False):
    '''Kwargify

    Consolidate positional args, *args, and **kwargs into a new dict.

    I/O:
    arg_names=None:
        Sequence of names for arg_values; the only 'required' field, and
        only if the calling function's parameters includes *args

    arg_values=None:
        Sequence of arg values, keyed by arg_names; defaults to current
        value of the calling function's (*)args

    kwargs=None:
        Dictionary of keyword arguments; defaults to the current value
        of the calling function's (**)kwargs

    parg_names=None:
        Sequence of positional arg names; defaults to the calling
        function's positional arg names

    parg_values=None:
        Sequence of positional arg values, keyed by parg_names; defaults
        to current value of calling function's positional arg values

    pargs=None:
        Dictionary of positional keyword arguments; an alternative to
        parg_names/parg_values, but all will be loaded if unique keys

    exclude=None:
        Sequence of keys to be excluded from the return dict

    selfish=False:
        By default, 'self' is added to exclusions

    return:
        New consolidated dict of positional args, (*)args & (**)kwargs
    '''
    parg_names_, args_name, kwargs_name, frame_locals = getargvalues(
                                                            stack()[1][0])

    arg_names = () if arg_names is None else arg_names
    arg_values = (frame_locals.get(args_name, ())
                  if arg_values is None else arg_values)
    kwargs = frame_locals.get(kwargs_name, {}) if kwargs is None else kwargs
    kwargs = kwargs.copy() if kwargs else {}
    parg_names = parg_names_ if parg_names is None else parg_names
    parg_values = (tuple((frame_locals[parg_name] for parg_name in parg_names))
                   if parg_values is None else parg_values)
    exclude = () if exclude is None else exclude

    if pargs:
        kwargs.update(pargs)

    for param, keys, values in (('parg_values', parg_names, parg_values),
                                ('arg_values', arg_names, arg_values)):
        diff = len(values) - len(keys)
        if diff > 0:
            raise KeyError('Missing keys for these {param}: {values}'
                           .format(param=param, values=values[-diff:]))

    for key, value in chain(izip(parg_names, parg_values),
                            izip(arg_names, arg_values)):
        if key in kwargs:
            raise KeyError('Duplicate key: {}'.format(key))
        kwargs[key] = value

    exclusions = chain(exclude, ('self',)) if not selfish else exclude

    for key in exclusions:
        if key in kwargs:
            del kwargs[key]

    return kwargs


def stringify(thing, limit=10, _lvl=0):
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

    An optional 'limit' parameter caps the number of list/tuple items to
    include. If capped, the cap and total number of items is noted. If
    the limit is negative, no cap is applied.
    '''
    limit = float('inf') if limit < 0 else limit
    ind = _lvl*4*' '
    len_thing = -1
    strings = []

    # If a list/tuple, stringify and add each item
    if isinstance(thing, (list, tuple)):
        len_thing = len(thing)  # Used for limit message later
        for i, t in enumerate(thing):
            if i == limit:
                break
            strings.append(stringify(t, limit, _lvl))

    # If a dict, add each key and stringify + further indent each value
    elif isinstance(thing, dict):
        for k, v in thing.items():
            v_str = stringify(v, limit, _lvl+1)
            # If key has an empty value, don't include it
            if len(v_str.strip()) == 0:
                continue
            # If there's one value, put the key and value on one line
            elif len(v_str.split('\n')) == 1:
                strings.append(u'{ind}{key}: {value}'.format(
                                ind=ind, key=k, value=v_str.strip()))
            # There are multiple values, so list them below the key
            else:
                strings.append(u'{ind}{key}:\n{value}'.format(
                                ind=ind, key=k, value=v_str))

    # If a custom object, use its __unicode__ method, but indent it
    elif hasattr(thing, '__dict__'):
        strings.append(u'{ind}{thing}'.format(
                       ind=ind, thing=''.join(('\n', ind))
                                        .join(unicode(thing).split('\n'))))

    # If a number, use commas for readability
    elif isinstance(thing, numbers.Number) and not isinstance(thing, bool):
        strings.append(u'{ind}{thing:,}'.format(ind=ind, thing=thing))

    # It is a non-numeric 'primitive' (e.g. boolean, string, etc.)
    else:
        strings.append(u'{ind}{thing}'.format(ind=ind, thing=thing))

    if len_thing > limit:
        strings.append('{ind}({limit} of {total})'.format(
                        ind=ind, limit=limit, total=len_thing))

    return '\n'.join(strings)


def vardygrify(cls, **kwds):
    u'''Vardygrify

    From Wikipedia (https://en.wikipedia.org/wiki/Vard%C3%B8ger):

        Vardoger, also known as vardyvle or vardyger, is a spirit
        predecessor in Scandinavian folklore. Stories typically include
        instances that are nearly deja vu in substance, but in reverse,
        where a spirit with the subject's footsteps, voice, scent, or
        appearance and overall demeanor precedes them in a location or
        activity, resulting in witnesses believing they've seen or heard
        the actual person before the person physically arrives. This
        bears a subtle difference from a doppelganger, with a less
        sinister connotation. It has been likened to being a phantom
        double, or form of bilocation.

    A convenience method for creating a non-persisted mock instance of
    a classes. Adds method mimicry capabilities on top of Mock.
    '''
    EXCLUDED_BUILTINS = {'__new__', '__init__'}
    INCLUDED_BUILTINS = {'__repr__', '__str__', '__unicode__'}

    vardygr = create_autospec(cls, spec_set=False, instance=True)

    for k, v in kwds.items():
        setattr(vardygr, k, v)

    for attr_name in dir(cls):
        if attr_name in EXCLUDED_BUILTINS:
            continue

        attribute = getattr(cls, attr_name)

        try:
            argspec = getargspec(attribute)  # works if attribute is a function
            args = argspec.args
            if (len(args) > 0 and args[0] == 'self' and
                    attr_name not in INCLUDED_BUILTINS):
                setattr(vardygr, attr_name, partial(attribute, vardygr))
            else:  # classmethod, staticmethod, or included builtin
                setattr(vardygr, attr_name, attribute)

        except TypeError:  # attribute is not a function
            # properties must be set on the type to be used on an instance
            if isinstance(attribute, property):
                setattr(type(vardygr), attr_name, property(attribute.fget))

    return vardygr
