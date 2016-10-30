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


class AttributeConflict(DataProcessException):
    '''{inst1!r}.{attr1!s} conflicts with {inst2!r}.{attr2!s}'''


class CircularReference(DataProcessException):
    '''Setting {attr!s} on {inst!r} to {value!r} would create a
    circular reference'''
