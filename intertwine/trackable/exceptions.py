#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

log = logging.getLogger('intertwine.trackable.exceptions')


class TrackableException(Exception):
    '''Trackable exception'''

    def __init__(self, message=None, *args, **kwds):
        template = message if message else ' '.join(self.__doc__.split())
        message = template.format(**kwds) if kwds else (
            template.format(*args) if args else template)
        # No handlers could be found for logger "intertwine.trackable.exceptions"
        # log.error(message)
        # TODO: Change to super() once on Python 3.6
        Exception.__init__(self, message)


class InvalidRegistryKey(TrackableException, KeyError):
    '''{key!r} is not a valid registry key for class {classname}'''


class KeyConflictError(TrackableException, KeyError):
    '''Key has already been registered: {key!r}'''


class KeyInconsistencyError(TrackableException, KeyError):
    '''Derived key inconsistent with registered key.
    Derived: {derived_key!r} Registered: {registered_key!r}
    Registry repaired: {registry_repaired}'''


class KeyMissingFromRegistryAndDatabase(TrackableException, KeyError):
    '''Key missing from Trackable registry and database: {key!r}'''


class KeyRegisteredAndNoModify(TrackableException, KeyError):
    '''{key!r} has already been registered for class {classname} and
    {classname}.modify() has not been implemented'''
