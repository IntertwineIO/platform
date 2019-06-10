# -*- coding: utf-8 -*-
from ..exceptions import IntertwineException


#######################
# Intertwine Exceptions

class InconsistentArguments(IntertwineException):
    """Argument '{arg1_name}' with value '{arg1_value}' is inconsistent
    with '{arg2_name}' with value '{arg2_value}'."""


class InvalidJSONPath(IntertwineException):
    """No JSON files found in path {path}."""


class MissingRequiredField(IntertwineException):
    """Required field '{field}' on {classname!r} is missing."""


class InvalidEntity(IntertwineException):
    """'{variable}' value of {value!r} is not a valid {classname}."""


class InvalidConnectionAxis(IntertwineException):
    """Invalid axis: {axis}. Valid axes: {valid_axes}"""


class CircularConnection(IntertwineException):
    """{problem!r} cannot be connected to itself."""


class InvalidProblemConnectionRating(IntertwineException):
    """Rating of {rating} on {connection!r} is not valid. Must be an int
    between 0 and 4 (inclusive)."""


class InvalidProblemConnectionWeight(IntertwineException):
    """Weight {weight} for {user} rating on {connection!r}
    for {problem!r} at {org!r} in {geo!r} is not valid."""


class InvalidAggregateConnectionRating(IntertwineException):
    """Aggregate rating of {rating} on {connection!r} is not valid. Must
    be a Real number between 0 and 4 (inclusive)."""


class InvalidAggregation(IntertwineException):
    """Aggregation '{aggregation}' is not valid. Must be 'strict'."""


class InvalidUser(IntertwineException):
    """User {user!r} on rating of {connection!r} is not a valid."""


class InvalidProblemForConnection(IntertwineException):
    """{problem!r} must be a problem in {connection!r}."""


class InvalidProblemName(IntertwineException):
    """Invalid problem name: {problem_name}"""
