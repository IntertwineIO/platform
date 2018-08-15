#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
from collections import Counter, OrderedDict, namedtuple
from enum import IntEnum
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
        """item generator"""
        key = self._beg
        while key is not self.sentinel:
            yield (key, self._getitem(key).value)
            key = self._getitem(key).next

    def keys(self):
        """key generator"""
        return self.__iter__()

    def values(self):
        """value generator"""
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


class MultiKeyMap:
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


class PeekableIterator:
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


class Stack(list):
    """Basic stack data structure"""
    sentinel = Sentinel('Stack')

    def push(self, item):
        """Push item onto the stack"""
        super().append(item)

    def append(self, item):
        """Append is not supported; see 'push'"""
        raise AttributeError("'Stack' object has no attribute 'append'")

    def peek(self):
        """Peek at item to be returned if 'pop' is called next"""
        return self[-1] if self else self.sentinel

    def __init__(self, iterable=Sentinel.by_key('Stack')):
        super().__init__() if iterable is self.sentinel else super().__init__(iterable)


class FieldPath(Stack):
    """
    Field path

    Track traversal of related model instances (via their fields) to
    generate all relevant paths.

    The paths include the absolute path from the base model followed by
    all relative paths anchored by the models given at initialization.
    Paths are ordered from longest to shortest, so higher specificity
    takes precedence over lower specificity.

    Each value emitted is a 2-tuple in the form (model, path), where
    model is the class anchoring the path.

    Usage:

    >>> fp = FieldPath(base=Child, models={Father, Mother})

    >>> list(fp.paths)
    [(__main__.Child, '.')]

    >>> fp.push('dad', Father)

    >>> list(fp.paths)
    [(__main__.Child, '.dad'), (__main__.Father, '.')]

    >>> fp.push('wife', Mother)

    >>> list(fp.paths)
    [(__main__.Child, '.dad.wife'),
     (__main__.Father, '.wife'),
     (__main__.Mother, '.')]

    >>> fp.push('children', Child)

    >>> list(fp.paths)
    [(__main__.Child, '.dad.wife.children'),
     (__main__.Father, '.wife.children'),
     (__main__.Mother, '.children')]

    >>> fp.pop()
    ['children', __main__.Child]

    >>> fp.push('dad', Father)

    >>> list(fp.paths)
    [(__main__.Child, '.dad.wife.dad'),
     (__main__.Father, '.wife.dad'),
     (__main__.Mother, '.dad'),
     (__main__.Father, '.')]
    """
    SELF_DESIGNATION = '.'
    PATH_DELIMITER = '.'
    Field = IntEnum('Field', 'FIELD MODEL', start=0, module=__name__)
    Path = namedtuple('Path', 'model path')

    def push(self, field, model=None):
        length = len(self)
        # Use lists instead of (named)tuples here for mutability
        super().push([field, model])
        if not length or model in self.models:
            self._starts.append(length)

    def pop(self):
        component = super().pop()
        model = component[self.Field.MODEL]
        length = len(self)
        if not length or model in self.models:
            index = self._starts.pop()
            assert index == length
        return component

    @property
    def last_field(self):
        return self[-1][self.Field.FIELD]

    @last_field.setter
    def last_field(self, value):
        self[-1][self.Field.FIELD] = value

    @property
    def last_model(self):
        return self[-1][self.Field.MODEL]

    @last_model.setter
    def last_model(self, value):
        length = len(self)
        if length != 1:
            old_value = self.last_model
            if (old_value in self.models) != (value in self.models):
                if old_value in self.models:
                    index = self._starts.pop()
                    assert index == length - 1
                else:  # value in self.models
                    self._starts.append(length - 1)

        self[-1][self.Field.MODEL] = value

    def form_path(self, start=0):
        """Form path relative to the given start index"""
        length = len(self)
        if length - start == 1:
            return self.SELF_DESIGNATION
        # Use list vs. generator for joining: https://stackoverflow.com/a/26635939/5521300
        # Use range vs. (i)slice for list iteration: https://stackoverflow.com/q/8671280/5521300
        field_names = ['' if i == start else self[i][self.Field.FIELD]
                       for i in range(start, length)]
        return self.PATH_DELIMITER.join(field_names)

    @property
    def paths(self):
        """
        Paths

        Property returning a path generator that emits the absolute path
        followed by each relative path anchored by an initialized model,
        in order from longest to shortest. This ordering allows higher
        specificity to take precedence over lower specificity.

        Each value emitted is a 2-tuple in the form (model, path), where
        model is the class anchoring the path.
        """
        return ((self[start][self.Field.MODEL], self.form_path(start))
                for start in self._starts)

    def __init__(self, base, models):
        super().__init__()
        self.models = {model for model in models} if models else set()
        self._starts = []
        self.push(self.SELF_DESIGNATION, base)
