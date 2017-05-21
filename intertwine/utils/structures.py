#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
from collections import Counter, OrderedDict, namedtuple
from operator import eq, attrgetter, itemgetter

if sys.version.startswith('3'):
    imap = map
else:
    from itertools import imap


class Sentinel(object):
    '''Sentinels are unique objects for special comparison use cases'''
    _id = 0

    def __init__(self):
        self.id = self.__class__._id
        self.__class__._id += 1

    def __repr__(self):
        return '<{cls}: {id}>'.format(cls=self.__class__.__name__, id=self.id)


class InsertableOrderedDict(OrderedDict):
    '''InsertableOrderedDict is an OrderedDict that supports insertion'''
    sentinel = Sentinel()
    ValueTuple = namedtuple('InsertableOrderedDictValueTuple',
                            'value, next, prior')

    @property
    def _dict(self):
        '''Property for accessing inherited dict'''
        return super(InsertableOrderedDict, self)

    def insert(self, insert_key, key, value, after=False):
        '''
        Insert a key/value pair

        I/O:
        insert_key  Reference key used for insertion
        key         Key to be inserted
        value       Value to be inserted
        after=False If True, inserts after reference key
        return      None
        '''
        if after:
            prior_key = insert_key
            next_key = self._get(insert_key)[1]
        else:
            prior_key = self._get(insert_key)[-1]
            next_key = insert_key

        self._insert_between(prior_key=prior_key, next_key=next_key,
                             key=key, value=value)

    def append(self, key, value):
        self._insert_between(prior_key=self._end, next_key=self.sentinel,
                             key=key, value=value)

    def prepend(self, key, value):
        self._insert_between(prior_key=self.sentinel, next_key=self._beg,
                             key=key, value=value)

    def _insert_between(self, prior_key, next_key, key, value):
        if self.get(key, self.sentinel) is not self.sentinel:
            raise KeyError(u"Key already exists: '{}'".format(key))

        self._setitem(key, (value, next_key, prior_key))

        if next_key is not self.sentinel:
            next_item = self._get(next_key)
            self._setitem(next_key, (next_item[0], next_item[1], key))
        else:
            self._end = key

        if prior_key is not self.sentinel:
            prior_item = self._get(prior_key)
            self._setitem(prior_key, (prior_item[0], key, prior_item[-1]))
        else:
            self._beg = key

    def copy(self):
        return self.__class__(self)

    def __repr__(self):
        cls = self.__class__.__name__
        return u'{cls}({tuples})'.format(cls=cls, tuples=tuple(self.items()))

    def _get(self, key, default=None):
        return self._dict.get(key, default)

    def get(self, key, default=None):
        item = self._get(key, self.sentinel)
        return item[0] if item is not self.sentinel else default

    def _getitem(self, key):
        return self._dict.__getitem__(key)

    def __getitem__(self, key):
        return self._getitem(key)[0]

    def _setitem(self, key, value):
        self._dict.__setitem__(key, value)

    def __setitem__(self, key, value):
        try:
            item = self._getitem(key)
            self._setitem(key, (value, item[1], item[-1]))
        except KeyError:
            self.append(key, value)

    def _delitem(self, key):
        self._dict.__delitem__(key)

    def __delitem__(self, key):
        _, next_key, prior_key = self._getitem(key)
        if next_key is not self.sentinel:
            next_item = self._getitem(next_key)
            self._setitem(next_key, (next_item[0], next_item[1], prior_key))
        else:
            self._end = prior_key

        if prior_key is not self.sentinel:
            prior_item = self._getitem(prior_key)
            self._setitem(prior_key, (prior_item[0], next_key, prior_item[-1]))
        else:
            self._beg = next_key

        self._delitem(key)

    def pop(self, key):
        pop_value = self[key]
        del self[key]
        return pop_value

    def clear(self):
        self._dict.clear()
        self._beg = self.sentinel
        self._end = self.sentinel

    def __iter__(self):
        key = self._beg
        while key is not self.sentinel:
            yield key
            key = self._getitem(key)[1]

    def __reversed__(self):
        key = self._end
        while key is not self.sentinel:
            yield key
            key = self._getitem(key)[-1]

    def reverse(self):
        for key in tuple(self.keys()):  # copy keys to permit rewiring
            item = self._getitem(key)
            self._setitem(key, (item[0], item[-1], item[1]))
        self._beg, self._end = self._end, self._beg

    def items(self):
        '''item generator (python 3 style)'''
        key = self._beg
        while key is not self.sentinel:
            yield (key, self._getitem(key)[0])
            key = self._getitem(key)[1]

    def keys(self):
        '''key generator (python 3 style)'''
        return self.__iter__()

    def values(self):
        '''value generator (python 3 style)'''
        key = self._beg
        while key is not self.sentinel:
            yield self._getitem(key)[0]
            key = self._getitem(key)[1]

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        if isinstance(other, (OrderedDict, InsertableOrderedDict)):
            return all(imap(eq, self.items(), other.items()))
        return all((eq(self[key], other.get(key)) for key in self))

    def __ne__(self, other):
        return not self.__eq__(other)

    def _initialize(self, _iter_or_map, _as_iter):
        # self._dict = {}
        s = self.sentinel
        keygetter = itemgetter(0) if _as_iter else lambda x: x
        valgetter = itemgetter(1) if _as_iter else lambda x: _iter_or_map[x]
        peekable = PeekableIterator(_iter_or_map, sentinel=s)
        self._beg = keygetter(peekable.peek()) if peekable.has_next() else s
        prior_key = s
        for obj in peekable:
            key, value = keygetter(obj), valgetter(obj)
            if self.get(key, s) is not s:
                raise KeyError(u"Duplicate key: '{}'".format(key))
            next_key = keygetter(peekable.peek()) if peekable.has_next() else s
            self._setitem(key, (value, next_key, prior_key))
            prior_key = key
        self._end = key if self._beg is not s else s

    def __init__(self, _iter_or_map=(), *args, **kwds):
        super(InsertableOrderedDict, self).__init__(*args, **kwds)
        try:
            self._initialize(_iter_or_map, _as_iter=True)
        except (IndexError, TypeError):
            self._initialize(_iter_or_map, _as_iter=False)


class MultiKeyMap(object):
    '''
    MultiKeyMap provides an ordered map of things keyed by each field

    I/O:
    fields: iterable of fields, where each field is individually unique
    things: list or tuple of objects to be referenced; each object must
            have all given fields defined (but may also have others).
    returns: MultiKeyMap instance
    '''
    def get_by(self, field, key, default=None):
        '''Return the object for which the field value equals the key'''
        return self.maps[field].get(key, default)

    def get_map_by(self, field):
        '''Return the (ordered) map for the given field'''
        return self.maps[field]

    def _check_for_duplicates(self, field, things):
        '''Raise ValueError if any dupe things for the given field'''
        if len(self.maps[field]) == len(things):
            return

        field_key_counts = Counter(getattr(thing, field) for thing in things)
        dupes = {key for key, count in field_key_counts.items() if count > 1}
        raise ValueError('Field {field} is not unique. Duplicates: {dupes}'
                         .format(field=field, dupes=dupes))

    def __init__(self, fields, things, *args, **kwds):
        self.maps = OrderedDict()

        for field in fields:
            things_by_field = sorted(things, key=attrgetter(field))
            field_map = OrderedDict(
                ((getattr(thing, field), thing) for thing in things_by_field))
            self.maps[field] = field_map
            self._check_for_duplicates(field, things)

        super(MultiKeyMap, self).__init__(*args, **kwds)


class PeekableIterator(object):
    '''Iterable that supports peeking at the next item'''

    def peek(self):
        '''Peek at the next item, returning it'''
        return self.next_item

    def has_next(self):
        '''Return True if the iterator has a next item'''
        return self.next_item is not self.sentinel

    def next(self):
        '''Increment the iterator and return the next item'''
        rv = self.next_item
        self.next_item = next(self.iterable, self.sentinel)
        return rv

    def __iter__(self):
        while self.has_next():
            yield self.next()

    def __init__(self, iterable, sentinel=object(), *args, **kwds):
        self.iterable = iter(iterable)
        self.sentinel = sentinel
        self.next_item = next(self.iterable, self.sentinel)
        super(PeekableIterator, self).__init__(*args, **kwds)
