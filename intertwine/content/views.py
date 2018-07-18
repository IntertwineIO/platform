#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import (current_app, jsonify, make_response, render_template,
                   # redirect,
                   # request
                   )

from . import blueprint
from .models import Content
from ..exceptions import InterfaceException


@blueprint.errorhandler(InterfaceException)
def handle_interface_exception(error):
    """
    Handle Interface Exception

    Intercepts the error and returns a response consisting of the status
    code and a JSON representation of the error.
    """
    return make_response(jsonify(error.jsonify()), error.status_code)


@blueprint.route('/', methods=['GET'])
def render():
    """Generic page rendering for top level"""
    content_list = Content.query.order_by(
        Content.created_timestamp).limit(100).all()

    template = render_template(
        'content_list.html',
        current_app=current_app,
        page_title='Content',
        content_list=content_list)

    return template
