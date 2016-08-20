#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import render_template

from . import blueprint
from .models import Community


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    communities = Community.query.all()
    template = render_template(
        'communities.html',
        current_app=flask.current_app,
        title="Communities",
        communities=communities)
    return template
