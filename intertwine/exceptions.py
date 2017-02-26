#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

log = logging.getLogger('intertwine.exceptions')


class IntertwineException(Exception):
    '''Base Intertwine exception class'''

    def __init__(self, message=None, *args, **kwds):
        template = message if message else ' '.join(self.__doc__.split())
        message = template.format(**kwds) if kwds else (
            template.format(*args) if args else template)
        log.error(message)
        # TODO: Change to super() once on Python 3.6
        Exception.__init__(self, message)


class AttributeConflict(IntertwineException):
    '''{inst1!r}.{attr1!s} conflicts with {inst2!r}.{attr2!s}'''


class CircularReference(IntertwineException):
    '''Setting {attr!s} on {inst!r} to {value!r} would create a
    circular reference'''


class InterfaceException(IntertwineException):
    '''Invalid usage is the base exception class for the API'''
    error_key = 'error'
    status_code = 400  # Default error code

    def __init__(self, message=None, status_code=None, payload=None,
                 *args, **kwds):
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        # TODO: Change to super() once on Python 3.6
        IntertwineException.__init__(self, message, *args, **kwds)

    def jsonify(self):
        error = {'message': str(self),
                 'type': self.__class__.__name__}
        if self.payload:
            error['payload'] = self.payload
        return {self.error_key: error}


class ResourceAlreadyExists(InterfaceException):
    '''{cls} resource already exists for key: {key}'''


class ResourceDoesNotExist(InterfaceException):
    '''{cls} resource does not exist for key: {key}'''
