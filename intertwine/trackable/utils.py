# -*- coding: utf-8 -*-
import inspect
from itertools import islice

SELF_REFERENTIAL_PARAMS = {'self', 'cls', 'meta'}
TEXT_TYPES = (str, bytes)


ord_A = ord('A')
ord_Z = ord('Z')
ord_a = ord('a')
ord_z = ord('z')


def dehumpify(camelcase):
    """Emit strings by progressively removing camel humps from end"""
    length = len(camelcase)
    for i, c in enumerate(reversed(camelcase), start=1):
        following_idx = length - i + 1
        followed_by_lower = (
            following_idx < length and ord_a <= ord(camelcase[following_idx]) <= ord_z)
        is_upper = ord_A <= ord(c) <= ord_Z
        preceding_idx = length - i - 1
        preceded_by_upper = (
            preceding_idx > -1 and ord_A <= ord(camelcase[preceding_idx]) <= ord_Z)
        if is_upper and (followed_by_lower or not preceded_by_upper):
            yield camelcase[:-i]


def build_table_model_map(base):
    """Build table model map given SQLAlchemy declarative base"""
    return {model.__table__.fullname: model
            for model in base._decl_class_registry.values()
            if hasattr(model, '__table__')}


def get_class(obj):
    """Get object's class, supporting model_class override"""
    if hasattr(obj, 'model_class'):
        return obj.model_class
    return obj.__class__


def isiterator(obj):
    """Check if object is iterator (not just iterable)"""
    cls = obj.__class__
    return hasattr(cls, '__next__') and not hasattr(cls, '__len__')


def isnamedtuple(obj):
    """Check if object is namedtuple"""
    return isinstance(obj, tuple) and hasattr(obj, '_asdict')


def isnonstringsequence(obj):
    """Check if object is non-string sequence: list, tuple, range..."""
    if (isinstance(obj, TEXT_TYPES) or hasattr(obj, 'items') or not hasattr(obj, '__getitem__')):
        return False
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def merge_args(func, *args, **kwds):
    """Merge args into kwds, with keys based on func parameter order"""
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
