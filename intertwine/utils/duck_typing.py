# -*- coding: utf-8 -*-
from intertwine.utils.tools import TEXT_TYPES


def iscollection(obj):
    """Check if object is a collection: list, tuple, dict, set..."""
    if isinstance(obj, TEXT_TYPES) or not hasattr(obj, '__len__'):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def isiterable(obj):
    """Check if object is iterable: str, list, tuple, dict"""
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def isiterator(obj):
    """Check if object is an iterator (not just iterable)"""
    cls = obj.__class__
    return hasattr(cls, '__next__') and not hasattr(cls, '__len__')


def isnamedtuple(obj):
    """Check if object is a namedtuple"""
    return isinstance(obj, tuple) and hasattr(obj, '_asdict')


def isnonstringsequence(obj):
    """Check if object is non-string sequence: list, tuple, range..."""
    if (isinstance(obj, TEXT_TYPES) or hasattr(obj, 'items') or not hasattr(obj, '__getitem__')):
        return False
    return isiterable(obj)


def issequence(obj):
    """Check if object is a sequence, e.g. list, tuple"""
    if (hasattr(obj, 'items') or not hasattr(obj, '__getitem__')):
        return False
    return isiterable(obj)
