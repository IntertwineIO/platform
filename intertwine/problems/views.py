#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask
from flask import abort, render_template

from titlecase import titlecase

from . import blueprint
from .models import Problem


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    problems = Problem.query.order_by(Problem.name).all()
    template = render_template(
        'problems.html',
        current_app=flask.current_app,
        title="Social Problems",
        problems=problems)
    return template


@blueprint.route('/<problem_name>', methods=['GET'])
def render_problem(problem_name):
    '''Problem Page'''
    p_name = titlecase(problem_name.replace('_', ' '))
    problem = Problem.query.filter_by(name=p_name).first()
    if problem is None:
        # TODO: Instead of aborting, reroute to problem_not_found page
        # Oops! 'X' is not a problem found in Intertwine.
        # Did you mean:
        # <related_problem_1>
        # <related_problem_2>
        # <related_problem_3>
        # Or, you can create 'X' in Intertwine'
        abort(404)
    template = render_template(
        'problem.html',
        current_app=flask.current_app,
        title=problem.name,
        problem=problem)
    return template
