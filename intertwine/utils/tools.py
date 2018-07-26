#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import numbers
import re
import sys
from collections import namedtuple
from itertools import chain, islice

if sys.version_info < (3,):
    lzip = zip  # legacy zip returning list of tuples
    from itertools import izip as zip
else:
    unicode = str

SELF_REFERENTIAL_PARAMS = {'self', 'cls', 'meta'}


def add_leading_zeros(number, width):
    """Add Leading Zeros to a number given a target width"""
    number_string = str(number)
    return '0' * (width - len(number_string)) + number_string


def bind(func, asname, instance=None, cls=None):
    """Bind function as name to instance or class"""
    cls = cls or instance.__class__
    bound = func.__get__(instance, cls)
    if instance:
        setattr(instance, asname, bound)
    else:
        setattr(cls, asname, bound)


def camelCaseTo_snake_case(string):
    """Convert CamelCase to snake_case"""
    patterns = [
        (r'(.)([0-9]+)', r'\1_\2'),
        (r'([a-z]+)([A-Z])', r'\1_\2'),
    ]
    engines = (
        (pattern, replacement, re.compile(pattern))
        for pattern, replacement in patterns
    )
    for data in engines:
        pattern, replacement, eng = data
        string = eng.sub(replacement, string)
    string = string.lower()
    return string


def define_constants_at_module_scope(module_name, module_class,
                                     constant_values):
    """
    Define constants at module scope

    Enforce naming convention in which constant names match the values,
    but are in ALL_CAPS with _'s instead of spaces.
    """
    module = sys.modules[module_name]

    for constant_value in constant_values:
        constant_name = constant_value.upper().replace(' ', '_')
        setattr(module, constant_name, getattr(module_class, constant_name))


ord_A = ord('A')
ord_Z = ord('Z')
ord_a = ord('a')
ord_z = ord('z')


def dehumpify(camelcase):
    """Emit strings by progressively removing camel humps from end"""
    length = len(camelcase)
    for i, c in enumerate(reversed(camelcase), start=1):
        following_idx = length - i + 1
        followed_by_lower = (following_idx < length and
                             ord_a <= ord(camelcase[following_idx]) <= ord_z)
        is_upper = ord_A <= ord(c) <= ord_Z
        preceding_idx = length - i - 1
        preceded_by_upper = (preceding_idx > -1 and
                             ord_A <= ord(camelcase[preceding_idx]) <= ord_Z)
        if is_upper and (followed_by_lower or not preceded_by_upper):
            yield camelcase[:-i]


def derive_args(func, include_self=False, include_optional=True,
                include_private=False):
    """
    Derive Args (Python 2.6+)

    Return arg generator for the given function

    I/O:
    include_self=False:
    include_optional=True:
    include_private=False:
    return: arg generator
    """
    fullargspec = gethalffullargspec(func)
    args, defaults = fullargspec.args, fullargspec.defaults
    start = 1 if not include_self and args[0] in SELF_REFERENTIAL_PARAMS else 0
    num_args = len(args) if args else 0
    num_defaults = len(defaults) if defaults else 0
    end = num_args if include_optional else num_args - num_defaults
    arg_generator = islice(args, start, end)
    if not include_private:
        arg_generator = (arg for arg in arg_generator if arg[0] != '_')
    return arg_generator


def _derive_defaults_py3(func, public_only=True):
    """
    Derive Defaults (Python 3.x)

    Return generator of (arg, default) tuples for the given function
    https://stackoverflow.com/questions/12627118/get-a-function-arguments-default-value

    Never use directly; use derive_defaults instead.
    """
    signature = inspect.signature(func)
    arg_defaults = ((k, v.default) for k, v in signature.parameters.items()
                    if v.default is not inspect.Parameter.empty)
    if public_only:
        return exclude_private_keys(arg_defaults)
    return arg_defaults


def _derive_defaults_py2(func, public_only=True):
    """
    Derive Defaults (Python 2.6+)

    Return generator of (arg, default) tuples for the given function
    https://stackoverflow.com/questions/12627118/get-a-function-arguments-default-value

    Never use directly; use derive_defaults instead.
    """
    fullargspec = gethalffullargspec(func)
    args, defaults = fullargspec.args, fullargspec.defaults
    arg_defaults = zip(args[-len(defaults):], defaults)
    if public_only:
        return exclude_private_keys(arg_defaults)
    return arg_defaults


derive_defaults = (_derive_defaults_py2 if sys.version_info < (3,)
                   else _derive_defaults_py3)


# Map of mypy-style type annotations and corresponding types
ANNOTATION_TYPE_MAP = {
    'Dict': dict,
    'List': list,
    'Set': set,
    'Text': unicode,
    'Tuple': tuple,
    'bool': bool,
    'float': float,
    'int': int,
    'str': str,
    'unicode': unicode,
}


def derive_arg_type(line, custom_map=None):
    """
    Derive Arg Type

    Given a code line with a mypy-style named parameter type annotation,
    return the parameter (name, type) tuple.
    """
    arg_definition, type_comment = line.split('# type:')
    arg_name = arg_definition.split('=')[0].strip().strip(',')
    type_annotation = type_comment.split('#')[0].strip().split('[')[0].strip()
    arg_type = ANNOTATION_TYPE_MAP.get(type_annotation)
    if arg_type is None and custom_map:
        arg_type = custom_map.get(type_annotation)
    if arg_type is None:
        arg_type = object
    return arg_name, arg_type


def derive_arg_types(func, custom=None, public_only=True):
    """
    Derive Arg Types

    Given a function with mypy-style named parameter type annotations,
    return a generator that emits parameter (name, type) tuples.
    """
    source_lines, _ = inspect.getsourcelines(func)
    custom_map = {typ_.__name__: typ_ for typ_ in custom} if custom else None
    for line in source_lines:
        # Skip commented lines
        if line.strip()[0] == '#':  # Skip commented lines
            continue
        if '# type:' in line:
            arg_name, arg_type = derive_arg_type(line, custom_map)
            if public_only and arg_name and arg_name[0] == '_':
                continue
            yield arg_name, arg_type
        else:
            if "'''" in line or '"""' in line:
                break


def enumify(enum_class, value):
    """
    Enumify

    Convert value to Enum/IntEnum value via enum_class, attempting name,
    value, and then int(value). ValueError is raised on all failures.
    """
    try:
        return enum_class[value]
    except KeyError:
        try:
            return enum_class(value)
        except ValueError:
            try:
                return enum_class(int(value))
            except ValueError:
                raise ValueError(f'{value} is not a valid {enum_class} enum')


def exclude_private_keys(iterator):
    """Given an iterator, return generator that excludes private keys"""
    return ((key, value) for key, value in iterator if key[0] != '_')


def find_all_words(text, words):
    """Find all exact search words (a set) in text"""
    search_words = words if isinstance(words, set) else set(words)
    text_words = set(text.split())
    return text_words & search_words


def find_any_words(text, words):
    """True iff any exact search words (a set) found in text"""
    search_words = words if isinstance(words, set) else set(words)
    for text_word in text.split():
        if text_word in search_words:
            return True
    return False


def get_class(obj):
    """Get object's class, supporting model_class override"""
    if hasattr(obj, 'model_class'):
        return obj.model_class
    return obj.__class__


def get_value(value, default, checks=None):
    """Get value or default as determined by checks"""
    checks = checks or {None}
    return value if value not in checks else default


if sys.version_info < (3,):
    FullArgSpec = namedtuple('FullArgSpec', 'args, varargs, varkw, defaults, '
                             'kwonlyargs, kwonlydefaults, annotations')


def gethalffullargspec(func):
    """
    gethalffullargspec

    Call getfullargspec (py3) or getargspec (py2) and return the py3
    FullArgSpec namedtuple in both cases - hence, it's 1/2 full...
    FullArgSpec has a varkw term instead of ArgSpec's keywords term.
    In py2, kwonlyargs, kwonlydefaults, and annotations are None.
    """
    try:  # py3
        return inspect.getfullargspec(func)

    except AttributeError:  # py2
        argspec = inspect.getargspec(func)
        return FullArgSpec(
            kwonlyargs=None, kwonlydefaults=None, annotations=None, *argspec)


def iterator(obj):
    """Return object's iterator if iterable, else None"""
    try:
        return iter(obj)
    except Exception:
        return


def nth_key(iterable, n):
    """Return the nth key from an iterable"""
    return next(islice(iterable, n, None))


def nth_value(iterable, n):
    """Return the nth value from an iterable"""
    key = nth_key(iterable, n)
    return iterable[key]


def nth_item(iterable, n):
    """Return the nth item from an iterable"""
    key = nth_key(iterable, n)
    return (key, iterable[key])


def kwargify(parg_tuples=None, arg_tuples=(), kwargs=None,
             exclude=set(), selfish=False):
    """
    Kwargify

    Consolidate positional args, *args, and **kwargs into a new dict.
    Only use for testing/logging due to reliance on stack.
    https://stackoverflow.com/questions/9938980/inspect-currentframe-may-not-work-under-some-implementations

    I/O:

    parg_tuples=None: iterable of name/value tuples for positional args;
        defaults to current value of calling function's positional args

    arg_tuples=(): iterable of name/value tuples for args

    kwargs=None: dictionary of keyword arguments; defaults to current
        value of calling function's kwargs

    exclude=None: sequence of keys to be excluded

    selfish=False: by default, 'self' is added to exclusions

    return: generator of consolidated pargs, args, and kwargs
    """
    derived = not parg_tuples or not kwargs
    if derived:
        prior_frame = inspect.stack()[1][0]
        try:
            parg_names, args_name, kwargs_name, frame_locals = (
                inspect.getargvalues(prior_frame))
        finally:
            # https://docs.python.org/2.7/library/inspect.html#the-interpreter-stack
            del prior_frame

    if parg_tuples:
        parg_names, parg_values = zip(*parg_tuples)
    else:
        parg_tuples = ((parg_name, frame_locals[parg_name])
                       for parg_name in parg_names)

    kwargs = kwargs or frame_locals.get(kwargs_name, {})

    if arg_tuples:
        arg_names, arg_values = zip(*arg_tuples)
        parg_set, arg_set, kwarg_set = (
            map(set, (parg_names, arg_names, kwargs)))
        # Check for duplicate arg names
        if parg_set & arg_set:
            raise KeyError('parg/arg dupes: {}'.format(parg_set & arg_set))
        if kwarg_set & arg_set:
            raise KeyError('kwarg/arg dupes: {}'.format(kwarg_set & arg_set))

    if not derived:
        if not arg_tuples:
            parg_set, kwarg_set = set(parg_names), set(kwargs)
        if kwarg_set & parg_set:
            raise KeyError('kwarg/parg dupes: {}'.format(kwarg_set & parg_set))

    all_args = chain(parg_tuples, arg_tuples, kwargs.items())

    exclusions = exclude if selfish else exclude | {'self', 'cls'}

    return ((name, value) for name, value in all_args
            if name not in exclusions)


def stringify(thing, limit=-1, _lvl=0):
    """
    Stringify

    Convert things into nicely formatted unicode strings for printing.
    Custom objects are stringified with their own str/unicode methods
    with appropriate indentation. Lists, tuples, and dictionaries
    recursively stringify their items.

    Dictionary keys with empty values are excluded. Values that
    are a single line are included on the same line as the key. Multi-
    line values are listed below the key and indented further.

    I/O:

    thing: Object to be converted to a string. May be a 'literal' (e.g.
        integer, boolean, string, etc.), a list/tuple, or a dictionary,
        a custom object.

    limit=-1: Cap iterables to this number and indicate when doing so.
        A negative limit (the default) means no cap is applied.

    _lvl=0: Private parameter to determine indentation during recursion
    """
    limit = float('inf') if limit < 0 else limit
    ind = _lvl * 4 * ' '
    len_thing = -1
    strings = []

    # If a namedtuple, stringify it whole
    if hasattr(thing, '_asdict'):
        strings.append(u'{ind}{namedtuple}'.format(
            ind=ind, namedtuple=thing))

    # If a list/tuple, stringify and add each item
    elif isinstance(thing, (list, tuple)):
        len_thing = len(thing)  # Used for limit message later
        for i, t in enumerate(thing):
            if i == limit:
                break
            strings.append(stringify(t, limit, _lvl))

    # If a dict, add each key and stringify + further indent each value
    elif isinstance(thing, dict):
        for k, v in thing.items():
            v_str = stringify(v, limit, _lvl + 1)
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
        strings.append(u'{ind}{object}'.format(
            ind=ind, object=('\n' + ind).join(unicode(thing).split('\n'))))

    # If a number, use commas for readability
    elif isinstance(thing, numbers.Number) and not isinstance(thing, bool):
        strings.append(u'{ind}{number:,}'.format(ind=ind, number=thing))

    # It is a non-numeric 'primitive' (e.g. boolean, string, etc.)
    else:
        strings.append(u'{ind}{primitive}'.format(
            ind=ind, primitive=thing))

    if len_thing > limit:
        strings.append('{ind}({limit} of {total})'.format(
            ind=ind, limit=limit, total=len_thing))

    return '\n'.join(strings)
