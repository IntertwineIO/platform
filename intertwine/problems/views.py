# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import flask
from flask import abort, redirect, render_template

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


@blueprint.route('/<path:problem_human_id>', methods=['GET'])
def render_problem(problem_human_id):
    '''Problem page redirects to global community page'''
    if problem_human_id and problem_human_id[-1] == '/':
        problem_human_id = problem_human_id.rstrip('/')

    problem_human_id = problem_human_id.lower()
    problem = Problem.query.filter_by(human_id=problem_human_id).first()

    if problem is None:
        # TODO: Instead of aborting, reroute to problem_not_found page
        # Oops! 'X' is not a problem found in Intertwine.
        # Did you mean:
        # <related_problem_1>
        # <related_problem_2>
        # <related_problem_3>
        # Or, you can create 'X' in Intertwine'
        abort(404)

    from ..communities.models import Community
    community_uri = Community.form_uri(problem=problem, org=None, geo=None)
    return redirect(community_uri, code=302)
