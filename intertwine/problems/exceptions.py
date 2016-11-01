# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from ..exceptions import DataProcessException


class InconsistentArguments(DataProcessException):
    '''Argument '{arg1_name}' with value '{arg1_value}' is inconsistent
    with '{arg2_name}' with value '{arg2_value}'.'''


class InvalidJSONPath(DataProcessException):
    '''No JSON files found in path {path}.'''


class MissingRequiredField(DataProcessException):
    '''Required field '{field}' on {classname!r} is missing.'''


class InvalidEntity(DataProcessException):
    ''''{variable}' value of {value!r} is not a valid {classname}.'''


class InvalidConnectionAxis(DataProcessException):
    '''Connection axis '{axis}' is not valid. Must be 'causal' or
    'scoped'.'''


class CircularConnection(DataProcessException):
    '''{problem!r} cannot be connected to itself.'''


class InvalidProblemConnectionRating(DataProcessException):
    '''Rating of {rating} on {connection!r} is not valid. Must be an int
    between 0 and 4 (inclusive).'''


class InvalidProblemConnectionWeight(DataProcessException):
    '''Weight {weight} for {user} rating on {connection!r}
    for {problem!r} at {org!r} in {geo!r} is not valid.'''


class InvalidAggregateConnectionRating(DataProcessException):
    '''Aggregate rating of {rating} on {connection!r} is not valid. Must
    be a Real number between 0 and 4 (inclusive).'''


class InvalidAggregation(DataProcessException):
    '''Aggregation '{aggregation}' is not valid. Must be 'strict'.'''


class InvalidUser(DataProcessException):
    '''User {user!r} on rating of {connection!r} is not a valid.'''


class InvalidProblemForConnection(DataProcessException):
    '''{problem!r} must be a problem in {connection!r}.'''
