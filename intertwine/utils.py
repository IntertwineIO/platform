#!/usr/bin/env python
import numbers
import re

from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declared_attr


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


class PeekableIterator(object):
    def __init__(self, it, sentinel=object()):
        self.it = iter(it)
        self.sentinel = sentinel
        self.next_item = next(self.it, self.sentinel)

    def next(self):
        rv = self.next_item
        self.next_item = next(self.it, self.sentinel)
        return rv

    def has_next(self):
        return self.next_item is not self.sentinel

    def peek(self):
        return self.next_item

    def __iter__(self):
        while self.has_next():
            yield self.next()


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
        for k, v in thing.iteritems():
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
        strings.append(
            (('\n' + ind).join('' + unicode(thing).split('\n')))[1:])

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
