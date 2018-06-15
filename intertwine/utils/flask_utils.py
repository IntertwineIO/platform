#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from past.builtins import basestring

from datetime import timedelta
from functools import update_wrapper

from flask import make_response, request, current_app


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


def json_requested():
    '''
    JSON requested

    Why check if json has a higher quality than HTML and not just go
    with the best match? Because some browsers accept on */* and we
    don't want to deliver JSON to an ordinary browser.

    This snippet by Armin Ronacher can be used freely for anything you
    like. Consider it public domain.
    '''
    accept_mimetypes = request.accept_mimetypes
    best = accept_mimetypes.best_match(['application/json', 'text/html'])
    return (best == 'application/json' and
            accept_mimetypes[best] > accept_mimetypes['text/html'])
