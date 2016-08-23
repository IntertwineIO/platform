#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import abort, render_template

from . import blueprint
from .models import Community
from ..problems import problem_db
from ..problems.models import Problem
from ..geos.models import Geo


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


@blueprint.route('/<problem_human_id>/<geo_human_id>', methods=['GET'])
def render_problem(problem_human_id, geo_human_id):
    '''Problem Page'''
    problem_human_id = problem_human_id.lower()
    problem = Problem.query.filter_by(human_id=problem_human_id).first()
    # TODO: add org to URL or query string
    org = None
    # org = 'University of Texas'
    org_display = org
    # geo = None
    # geo_display = None
    geo = Geo.query.filter_by(human_id=geo_human_id).first()

    geo_display = geo.display()
    connections = problem.connections_with_ratings(org_scope=org,
                                                   geo_scope=geo,
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
        'community.html',
        current_app=flask.current_app,
        title=problem.name,  # Update to include org/geo
        problem=problem,
        connections=connections,
        org_display=org_display,
        geo_display=geo_display
        )
    return template
