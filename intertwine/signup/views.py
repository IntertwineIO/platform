# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import flask
from flask import render_template

from . import blueprint


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    template = render_template(
        'sign-up.html',
        current_app=flask.current_app,
        title="Signup")
    return template
