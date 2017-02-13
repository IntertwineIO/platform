#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import flask
from flask import abort, redirect, render_template

from . import blueprint
from ..geos.models import Geo
from ..problems.models import Problem, ProblemConnection
from ..utils.mixins import Jsonable
from ..utils.tools import vardygrify
from .models import Community


def configure_community_json():
    config = {}
    config['.aggregate_ratings'] = -2
    for category in ProblemConnection.CATEGORY_MAP:
        config[Jsonable.form_path('.problem', category)] = 0
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'rating')] = 1
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'adjacent_problem_name')] = 1
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'adjacent_community_url')] = 1
    return config


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


@blueprint.route('/<problem_human_id>/', methods=['GET'])
def render_global_community(problem_human_id):
    return render_community(problem_human_id, '')


@blueprint.route('/<problem_human_id>/<path:geo_human_id>', methods=['GET'])
def render_community(problem_human_id, geo_human_id):
    '''Community Page'''
    problem_human_id = problem_human_id.lower()
    problem = Problem.query.filter_by(human_id=problem_human_id).first()

    if problem is None:
        # TODO: Instead of aborting, reroute to problem_not_found page
        # Oops! 'X' is not a problem found in Intertwine.
        # Did you mean:
        # <problem_1>
        # <problem_2>
        # <problem_3>
        # Or, you can create 'X' in Intertwine'
        abort(404)

    # TODO: add org to URL or query string
    org = None
    # org = 'University of Texas'
    geo_human_id = geo_human_id.lower()

    if geo_human_id:
        corrected_url = False
        if geo_human_id[-1] == '/':
            geo_human_id = geo_human_id.rstrip('/')
            corrected_url = True

        geo = Geo.query.filter_by(human_id=geo_human_id).first()

        if geo is None:
            # TODO: Instead of aborting, reroute to geo_not_found page
            # Oops! 'X' is not a geo found in Intertwine.
            # Did you mean:
            # <geo_1>
            # <geo_2>
            # <geo_3>
            abort(404)

        if geo.alias_target:
            return redirect(Community.form_uri(problem, org, geo.alias_target),
                            code=302)
        if corrected_url:
            return redirect(Community.form_uri(problem, org, geo), code=302)
    else:
        geo = None

    community = Community.query.filter_by(
        problem=problem, org=org, geo=geo).first()

    if not community:
        community = vardygrify(Community, problem=problem, org=org, geo=geo,
                               num_followers=0)

    config = configure_community_json()
    payload = community.jsonify(config=config, depth=2)

    template = render_template(
        'community.html',
        current_app=flask.current_app,
        title=community.name,
        payload=payload)
    return template
