#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import render_template

from . import blueprint


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    template = render_template(
        'problems.html',
        current_app=flask.current_app,
        title="Problems")
    return template
