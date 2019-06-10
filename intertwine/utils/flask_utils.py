# -*- coding: utf-8 -*-
from datetime import timedelta
from functools import update_wrapper

from flask import make_response, request, current_app

from intertwine.utils.tools import TEXT_TYPES


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    """
    Crossdomain

    Decorator for the HTTP Access Control

    Cross-site HTTP requests are HTTP requests for resources from a
    different domain than the domain of the resource making the request.
    For instance, a resource loaded from Domain A makes a request for a
    resource on Domain B. The way this is implemented in modern browsers
    is by using HTTP Access Control headers: Documentation on
    developer.mozilla.org.

    I/O:

    methods:    Optional list of methods allowed for this view. If not
                provided allow all implemented methods.
    headers:    Optional list of headers allowed for this request.
    origin:     '*' to allow all origins, otherwise a string with a URL
                or a list of URLs that might access the resource.
    max_age:    Number of seconds as integer or timedelta for which the
                preflighted request is valid.
    attach_to_all: True if the decorator should add access control
                headers to all HTTP methods or False if it should only
                add them to OPTIONS responses.
    automatic_options: If enabled, the decorator will use the default
                Flask OPTIONS response and attach the headers there,
                otherwise the view function will be called to generate
                an appropriate response.

    This snippet by Armin Ronacher can be used freely for anything you
    like. Consider it public domain.
    http://flask.pocoo.org/snippets/56/
    """
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, TEXT_TYPES):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, TEXT_TYPES):
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
    """
    JSON requested

    If JSON is explicitly listed in the accept mime types, return True.

    Otherwise, continue with Armin's best match logic:

    Why check if JSON has a higher quality than HTML and not just go
    with the best match? Because some browsers accept on */* and we
    don't want to deliver JSON to an ordinary browser.

    This snippet by Armin Ronacher can be used freely for anything you
    like. Consider it public domain.

    http://flask.pocoo.org/snippets/45/
    """
    accept_mimetypes = request.accept_mimetypes

    for mimetype in accept_mimetypes.values():
        if mimetype == 'application/json':
            return True

    best = accept_mimetypes.best_match(['application/json', 'text/html'])
    return (best == 'application/json' and accept_mimetypes[best] > accept_mimetypes['text/html'])
