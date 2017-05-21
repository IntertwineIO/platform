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


class InvalidRegistryKey(TrackableException):
    '''{key!r} is not a valid registry key for class {classname}'''


class KeyMissingFromRegistryAndDatabase(TrackableException, KeyError):
    '''Key missing from Trackable registry and database: {key!r}'''


class KeyRegisteredAndNoModify(TrackableException):
    '''{key!r} has already been registered for class {classname} and
    {classname}.modify() has not been implemented'''
