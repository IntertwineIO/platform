#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask
from flask import abort, render_template

from . import blueprint, problem_db
from .models import Problem


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    problems = Problem.query.order_by(Problem._name).all()
    template = render_template(
        'problems.html',
        current_app=flask.current_app,
        title="Social Problems",
        problems=problems)
    return template


@blueprint.route('/<problem_name>', methods=['GET'])
def render_problem(problem_name):
    '''Problem Page'''
    human_id = problem_name.lower()
    problem = Problem.query.filter_by(human_id=human_id).first()
    # TODO: add geo and org to query strings
    geo = 'United States/Texas/Austin'
    org = None
    connections = problem.connections_with_ratings(geo_scope=geo,
                                                   org_scope=org,
                                                   aggregation='strict',
                                                   session=problem_db.session)
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
        problem=problem,
        connections=connections,
        )
    return template
