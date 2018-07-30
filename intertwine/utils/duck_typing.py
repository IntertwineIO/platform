#!/usr/bin/env python
# -*- coding: utf-8 -*-
from past.builtins import basestring


def iscollection(obj):
    """Check if object is a collection: list, tuple, dict, set..."""
    if isinstance(obj, basestring) or not hasattr(obj, '__len__'):
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
    """Check if object is a non-string sequence, e.g. list, tuple"""
    if (isinstance(obj, basestring) or hasattr(obj, 'items') or not hasattr(obj, '__getitem__')):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def issequence(obj):
    """Check if object is a sequence, e.g. list, tuple"""
    if (hasattr(obj, 'items') or not hasattr(obj, '__getitem__')):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False
