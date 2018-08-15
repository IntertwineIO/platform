#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
from collections import Counter, OrderedDict, namedtuple
from operator import eq, attrgetter, itemgetter

from .tools import nth_key

# Python version compatibilities
if sys.version_info < (3,):
    lmap = map  # legacy map returning list
    from itertools import imap as map


class Sentinel:
    """Sentinels are unique objects for special comparison use cases"""
    _count = 0
    _registry = {}
    _default_key_template = 'sentinel_{id}'

    @classmethod
    def by_key(cls, key):
        return cls._registry[key]

    def __init__(self, key=None):
        cls = self.__class__
        self.id = cls._count
        cls._count += 1
        key = self._default_key_template.format(id=self.id) if key is None else key
        if key in cls._registry:
            raise KeyError(f"Sentinel key '{key}' already in use!")
        self.key = key
        cls._registry[key] = self

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"{class_name}.by_key('{self.key}')"

    def __bool__(self):
        """Sentinels evaluate to False like None or empty string"""
        return False


class InsertableOrderedDict(OrderedDict):
    """InsertableOrderedDict is an OrderedDict that supports insertion"""
    sentinel = Sentinel('InsertableOrderedDict')
    ValueTuple = namedtuple('InsertableOrderedDictValueTuple',
                            'value, next, prior')

    @property
    def _dict(self):
        """Property for accessing inherited dict"""
        return super(InsertableOrderedDict, self)

    def insert(self, reference, key, value, after=False, by_index=False):
        """
        Insert a key/value pair

        I/O:
        reference: Key/index used to guide insertion based on by_index
        key: Key to be inserted
        value: Value to be inserted
        after=False: If True, inserts after reference key
        by_index=False: If True, use reference as index for insertion;
            by default, use reference as key for insertion
        return: None
        """
        insert_key, after = self._derive_insertion(reference, after, by_index)

        if after:
            prior_key = insert_key
            next_key = self._get(insert_key).next
        else:
            prior_key = self._get(insert_key).prior
            next_key = insert_key

        self._insert_between(key=key, value=value, next_key=next_key,
                             prior_key=prior_key)

    def append(self, key, value):
        self._insert_between(key=key, value=value, next_key=self.sentinel,
                             prior_key=self._end)

    def prepend(self, key, value):
        self._insert_between(key=key, value=value, next_key=self._beg,
                             prior_key=self.sentinel)

    def _derive_insertion(self, reference, after, by_index):
        valid = False
        try:
            insert_key = (nth_key(self.keys(), reference) if by_index
                          else reference)
            return insert_key, after

        except ValueError:
            if reference == -1 and after:
                reference, after, valid = 0, False, True
        except StopIteration:
            if reference == len(self) and not after:
                reference, after, valid = len(self) - 1, True, True

        if not valid:
            raise ValueError('Insert reference out of range: {rel} {idx}'
                             .format(rel='after' if after else 'before',
                                     idx=reference))
        insert_key = nth_key(self.keys(), reference)
        return insert_key, after

    def _insert_between(self, key, value, next_key, prior_key):
        if self.get(key, self.sentinel) is not self.sentinel:
            raise KeyError('Key already exists: {!r}'.format(key))

        self._setitem(key, self.ValueTuple(value, next_key, prior_key))

        if next_key is not self.sentinel:
            next_item = self._get(next_key)
            self._setitem(next_key, self.ValueTuple(
                next_item.value, next_item.next, key))
        else:
            self._end = key

        if prior_key is not self.sentinel:
            prior_item = self._get(prior_key)
            self._setitem(prior_key, self.ValueTuple(
                prior_item.value, key, prior_item.prior))
        else:
            self._beg = key

    def copy(self):
        return self.__class__(self)

    def __repr__(self):
        return u'{cls}({tuples})'.format(cls=self.__class__.__name__,
                                         tuples=tuple(self.items()))

    def _get(self, key, default=None):
        return self._dict.get(key, default)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _getitem(self, key):
        return self._dict.__getitem__(key)

    def __getitem__(self, key):
        return self._getitem(key).value

    def _setitem(self, key, value):
        self._dict.__setitem__(key, value)

    def __setitem__(self, key, value):
        try:
            item = self._getitem(key)
            self._setitem(key, self.ValueTuple(value, item.next, item.prior))
        except KeyError:
            self.append(key, value)

    def _delitem(self, key):
        self._dict.__delitem__(key)

    def __delitem__(self, key):
        _, next_key, prior_key = self._getitem(key)
        if next_key is not self.sentinel:
            next_item = self._getitem(next_key)
            self._setitem(next_key, self.ValueTuple(
                next_item.value, next_item.next, prior_key))
        else:
            self._end = prior_key

        if prior_key is not self.sentinel:
            prior_item = self._getitem(prior_key)
            self._setitem(prior_key, self.ValueTuple(
                prior_item.value, next_key, prior_item.prior))
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
            key = self._getitem(key).next

    def __reversed__(self):
        key = self._end
        while key is not self.sentinel:
            yield key
            key = self._getitem(key).prior

    def reverse(self):
        # copy keys to permit rewiring during iteration
        for key in tuple(self.keys()):
            item = self._getitem(key)
            self._setitem(key, self.ValueTuple(
                item.value, item.prior, item.next))
        self._beg, self._end = self._end, self._beg

    def items(self):
        """item generator (python 3 style)"""
        key = self._beg
        while key is not self.sentinel:
            yield (key, self._getitem(key).value)
            key = self._getitem(key).next

    def keys(self):
        """key generator (python 3 style)"""
        return self.__iter__()

    def values(self):
        """value generator (python 3 style)"""
        key = self._beg
        while key is not self.sentinel:
            yield self._getitem(key).value
            key = self._getitem(key).next

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        if isinstance(other, (OrderedDict, InsertableOrderedDict)):
            return all(map(eq, self.items(), other.items()))
        return all((eq(self[key], other.get(key)) for key in self))

    def __ne__(self, other):
        return not self.__eq__(other)

    def _initialize(self, _iter_or_map, _as_iter):
        # self._dict = {}
        sentinel = self.sentinel
        keygetter = itemgetter(0) if _as_iter else lambda x: x
        valgetter = itemgetter(1) if _as_iter else lambda x: _iter_or_map[x]
        peekable = PeekableIterator(_iter_or_map, sentinel=sentinel)
        self._beg = (keygetter(peekable.peek()) if peekable.has_next()
                     else sentinel)
        prior_key = sentinel
        for obj in peekable:
            key, value = keygetter(obj), valgetter(obj)
            if self.get(key, sentinel) is not sentinel:
                raise KeyError(u"Duplicate key: '{}'".format(key))
            next_key = (keygetter(peekable.peek()) if peekable.has_next()
                        else sentinel)
            self._setitem(key, self.ValueTuple(value, next_key, prior_key))
            prior_key = key
        self._end = key if self._beg is not sentinel else sentinel

    def __init__(self, _iter_or_map=(), *args, **kwds):
        super(InsertableOrderedDict, self).__init__(*args, **kwds)
        try:
            self._initialize(_iter_or_map, _as_iter=True)
        except (IndexError, TypeError):
            self._initialize(_iter_or_map, _as_iter=False)


class MultiKeyMap(object):
    """
    MultiKeyMap provides an ordered map of things keyed by each field

    I/O:
    fields: iterable of fields, where each field is individually unique
    things: list or tuple of objects to be referenced; each object must
            have all given fields defined (but may also have others).
    return: MultiKeyMap instance
    """
    def get_by(self, field, key, default=None):
        """Return the object for which the field value equals the key"""
        return self.maps[field].get(key, default)

    def get_map_by(self, field):
        """Return the (ordered) map for the given field"""
        return self.maps[field]

    def _check_for_duplicates(self, field, things):
        """Raise ValueError if any dupe things for the given field"""
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
    """Iterable that supports peeking at the next item"""
    _default_sentinel = Sentinel('PeekableIterator')

    def peek(self):
        """Peek at the next item, returning it"""
        return self.next_item

    def has_next(self):
        """Return True if the iterator has a next item"""
        return self.next_item is not self.sentinel

    def next(self):
        """Increment the iterator and return the next item"""
        rv = self.next_item
        self.next_item = next(self.iterable, self.sentinel)
        return rv

    def __iter__(self):
        while self.has_next():
            yield self.next()

    def __init__(self, iterable, sentinel=None, *args, **kwds):
        self.iterable = iter(iterable)
        self.sentinel = sentinel or self._default_sentinel
        self.next_item = next(self.iterable, self.sentinel)
        super(PeekableIterator, self).__init__(*args, **kwds)
