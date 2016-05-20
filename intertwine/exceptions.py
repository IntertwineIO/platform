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


class InvalidRegistryKey(DataProcessException):
    '''{key!r} is not a valid registry key for class {classname}'''


class KeyRegisteredAndNoModify(DataProcessException):
    '''{key!r} has already been registered for class {classname} and
    {classname}.modify() has not been implemented'''
