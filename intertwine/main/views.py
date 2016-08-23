#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask
from flask import render_template

from . import blueprint
from ..problems.models import Problem


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    problems = Problem.query.order_by(Problem.name).all()
    template = render_template(
        'main.html',
        current_app=flask.current_app,
        title="Main",
        problems=problems)
    return template
