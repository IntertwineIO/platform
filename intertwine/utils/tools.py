#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
import numbers
import re
import sys
from functools import partial
from itertools import chain, islice
from mock import create_autospec
from numbers import Real

from past.builtins import basestring

if sys.version_info < (3,):
    lzip = zip  # legacy zip returning list of tuples
    from itertools import izip as zip
else:
    unicode = str


def add_leading_zeros(number, width):
    number_string = str(number)
    return '0' * (width - len(number_string)) + number_string


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


def define_constants_at_module_scope(module_name, module_class,
                                     constant_values):
    '''
    Define constants at module scope

    Enforce naming convention in which constant names match the values,
    but are in ALL_CAPS with _'s instead of spaces.
    '''
    module = sys.modules[module_name]

    for constant_value in constant_values:
        constant_name = constant_value.upper().replace(' ', '_')
        setattr(module, constant_name, getattr(module_class, constant_name))


def _derive_defaults_py3(func):
    '''
    Derive Defaults (Python 3.x)

    Return generator of (arg, default) tuples for the given function
    https://stackoverflow.com/questions/12627118/get-a-function-arguments-default-value

    Never use directly; use derive_defaults instead.
    '''
    signature = inspect.signature(func)
    return ((k, v.default) for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty)


def _derive_defaults_py2(func):
    '''
    Derive Defaults (Python 2.6+)

    Return generator of (arg, default) tuples for the given function
    https://stackoverflow.com/questions/12627118/get-a-function-arguments-default-value

    Never use directly; use derive_defaults instead.
    '''
    args, varargs, keywords, defaults = inspect.getargspec(func)
    return zip(args[-len(defaults):], defaults)


derive_defaults = (_derive_defaults_py2 if sys.version_info < (3,)
                   else _derive_defaults_py3)


def find_all_words(text, words):
    '''Find all exact search words (a set) in text'''
    search_words = words if isinstance(words, set) else set(words)
    text_words = set(text.split())
    return text_words & search_words


def find_any_words(text, words):
    '''True iff any exact search words (a set) found in text'''
    search_words = words if isinstance(words, set) else set(words)
    for text_word in text.split():
        if text_word in search_words:
            return True
    return False


def isiterator(iterable):
    '''Determine if an iterable (or any object) is an iterator'''
    return hasattr(iterable, '__iter__') and not hasattr(iterable, '__len__')


def iterator(*elements):
    for element in elements:
        yield element


def nth_key(iterable, n):
    '''Return the nth key from an iterable'''
    return next(islice(iterable, n, None))


def nth_value(iterable, n):
    '''Return the nth value from an iterable'''
    key = nth_key(iterable, n)
    return iterable[key]


def nth_item(iterable, n):
    '''Return the nth item from an iterable'''
    key = nth_key(iterable, n)
    return (key, iterable[key])


def kwargify(parg_tuples=None, arg_tuples=(), kwargs=None,
             exclude=set(), selfish=False):
    '''
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
    '''
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
    '''
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
    '''
    limit = float('inf') if limit < 0 else limit
    ind = _lvl * 4 * ' '
    len_thing = -1
    strings = []

    for single_loop_to_enable_exception_flow_control in range(1):
        # If a namedtuple, stringify it whole
        try:
            thing._asdict()  # Raise AttributeError if not namedtuple
            strings.append(u'{ind}{namedtuple}'.format(
                ind=ind, namedtuple=thing))
            continue  # Execution proceeds after single loop
        except AttributeError:
            pass

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

    # After single loop: execution proceeds here

    if len_thing > limit:
        strings.append('{ind}({limit} of {total})'.format(
            ind=ind, limit=limit, total=len_thing))

    return '\n'.join(strings)


def vardygrify(cls, **kwds):
    u'''
    Vardygrify

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
    EXCLUDED_BUILTINS = {'__new__', '__init__', '__class__', '__setattr__'}
    INCLUDED_BUILTINS = {'__repr__', '__str__', '__unicode__'}

    vardygr = create_autospec(cls, spec_set=False, instance=True)

    for k, v in kwds.items():
        setattr(vardygr, k, v)

    for attr_name in dir(cls):
        if attr_name in EXCLUDED_BUILTINS:
            continue

        attribute = getattr(cls, attr_name)

        try:
            # works if attribute is a function
            argspec = inspect.getargspec(attribute)
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
            elif isinstance(attribute, (basestring, Real, tuple, list)):
                setattr(vardygr, attr_name, attribute)

    return vardygr
