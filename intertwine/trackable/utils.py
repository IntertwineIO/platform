#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import sys
from itertools import islice

from past.builtins import basestring

# Python version compatibilities
if sys.version_info < (3,):
    lzip = zip  # legacy zip returning list of tuples
    from itertools import izip as zip


SELF_REFERENTIAL_PARAMS = {'self', 'cls', 'meta'}


def build_table_model_map(base):
    '''Build table model map given SQLAlchemy declarative base'''
    return {model.__table__.fullname: model
            for model in base._decl_class_registry.values()
            if hasattr(model, '__table__')}


def isiterator(obj):
    '''Determine if an object is an iterator (not just iterable)'''
    return hasattr(obj, '__iter__') and not hasattr(obj, '__len__')


def isnamedtuple(obj):
    '''Determine if an object is a namedtuple'''
    return isinstance(obj, tuple) and hasattr(obj, '_asdict')


def isnonstringsequence(obj):
    '''Determine if an object is a non-string sequence, i.e. list, tuple'''
    return (hasattr(obj, '__iter__') and hasattr(obj, '__getitem__') and
            not isinstance(obj, basestring))


def merge_args(func, *args, **kwds):
    '''Merge args into kwds, with keys based on func parameter order'''
    if not args:
        return kwds

    try:  # py3
        func_args = inspect.getfullargspec(func).args
    except AttributeError:  # py2
        func_args = inspect.getargspec(func).args

    start = 1 if func_args[0] in SELF_REFERENTIAL_PARAMS else 0
    arg_names = islice(func_args, start, len(func_args))

    for arg_name, arg_value in zip(arg_names, args):
        if arg_name in kwds:
            raise TypeError('Keyword arg {kwd_name} conflicts with '
                            'positional arg'.format(kwd_name=arg_name))
        kwds[arg_name] = arg_value

    return kwds
