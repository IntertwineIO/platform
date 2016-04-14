#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging


log = logging.getLogger('intertwine.problems.exceptions')


class DataProcessException(Exception):
    '''Data Process exception'''

    # TODO: make this work with *args
    def __init__(self, message=None, *args, **kwds):
        if message is not None:
            message = message.format(**kwds) if kwds else message
        else:
            normalized_doc = ' '.join(self.__doc__.split())
            message = normalized_doc.format(**kwds) if kwds else normalized_doc
        log.error(message)
        Exception.__init__(self, message)


class InconsistentArguments(DataProcessException):
    '''Argument '{arg1_name}' with value '{arg1_value}' is inconsistent
    with '{arg2_name}' with value '{arg2_value}'.'''


class InvalidJSONPath(DataProcessException):
    '''No JSON files found in path {path}.'''


class MissingRequiredField(DataProcessException):
    '''Required field '{field}' on {classname!r} is missing.'''


class InvalidRegistryKey(DataProcessException):
    '''{key!r} is not a valid registry key for class {classname}'''


class InvalidEntity(DataProcessException):
    ''''{variable}' value of {value!r} is not a valid {classname}.'''


class InvalidConnectionType(DataProcessException):
    '''Connection type '{connection_type}' is not valid. Must be
    'causal' or 'scoped'.'''


class CircularConnection(DataProcessException):
    '''{problem!r} cannot be connected to itself.'''


class InvalidProblemConnectionRating(DataProcessException):
    '''Rating of {rating} on {connection!r} is not valid. Must be an int
    between 0 and 4 (inclusive).'''


class InvalidAggregateConnectionRating(DataProcessException):
    '''Aggregate rating of {rating} on {connection!r} is not valid. Must
    be a Real number between 0 and 4 (inclusive).'''


class InvalidAggregation(DataProcessException):
    '''Aggregation '{aggregation}' is not valid. Must be 'strict'.'''


class InvalidUser(DataProcessException):
    '''User {user!r} on rating of {connection!r} is not a valid.'''


class InvalidProblemForConnection(DataProcessException):
    '''{problem!r} must be a problem in {connection!r}.'''
