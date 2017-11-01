#!/usr/bin/env python
# -*- coding: utf-8 -*-
from uuid import uuid4


class DefaultConfig(object):
    '''Base class for all configurations'''

    DEBUG = False
    TESTING = False
    PROPAGATE_EXCEPTIONS = False
    SECRET_KEY = 'In73rTwine'  # required for updating cookies
    LOGGER_NAME = 'intertwine'
    PREFERRED_URL_SCHEME = 'https'
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    CSRF_ENABLED = True  # cross-site forgery protection
    HOST = '0.0.0.0'


class DevelopmentConfig(DefaultConfig):
    '''For use with development'''

    DEBUG = True
    PROPAGATE_EXCEPTIONS = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    PERMANENT_SESSION_LIFETIME = 60 * 5  # 5 minutes: in seconds
    TRAP_HTTP_EXCEPTIONS = True  # regular traceback on http exceptions
    TRAP_BAD_REQUEST_ERRORS = True  # regular traceback on bad requests
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True


class TestingConfig(DefaultConfig):
    '''For use with testing'''

    TESTING = True
    PROPAGATE_EXCEPTIONS = True
    TRAP_HTTP_EXCEPTIONS = True  # regular traceback on http exceptions
    TRAP_BAD_REQUEST_ERRORS = True  # regular traceback on bad requests
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True


class DeployableConfig(DefaultConfig):
    '''For use on deployed system'''
    SECRET_KEY = uuid4().bytes
    PERMANENT_SESSION_LIFETIME = 60 * 120  # 2 hours: in seconds
    JSON_SORT_KEYS = False


class ProductionConfig(DeployableConfig):
    '''For use on production system'''
    SERVER_NAME = 'intertwine.io'
    SECRET_KEY = uuid4().bytes
    PERMANENT_SESSION_LIFETIME = 60 * 120  # 2 hours: in seconds
    JSON_SORT_KEYS = False
