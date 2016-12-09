#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import flask
from flask import abort, redirect, render_template

from . import blueprint
from .models import Community
from ..utils.mixins import Jsonable
from ..utils.tools import vardygrify
from ..problems.models import Problem, ProblemConnection
from ..geos.models import Geo


def configure_community_json():
    config = {}
    config['.aggregate_ratings'] = -2
    for category, category_record in ProblemConnection.CATEGORY_MAP.items():
        component = category_record.component
        config[Jsonable.form_path('.problem', category)] = 0
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'rating')] = 1
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'connection')] = -1
        config[Jsonable.form_path('.aggregate_ratings', category, 'connection',
                                  component)] = -1
        config[Jsonable.form_path('.aggregate_ratings', category, 'connection',
                                  component, 'name')] = 1
        config[Jsonable.form_path('.aggregate_ratings', category, 'connection',
                                  component, 'human_id')] = 1
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

    if geo_human_id and geo_human_id[-1] == '/':
        return redirect('/communities/{problem}/{geo}'
                        .format(problem=problem_human_id,
                                geo=geo_human_id.rstrip('/')), code=302)

    if geo_human_id:
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
            return redirect('/communities/{problem}/{geo}'
                            .format(problem=problem_human_id,
                                    geo=geo.alias_target.human_id), code=302)
    else:
        geo = None

    community = Community.query.filter_by(
                                    problem=problem, org=org, geo=geo).first()

    if not community:
        community = vardygrify(Community, problem=problem, org=org, geo=geo,
                               num_followers=0)

    connections = community.assemble_connections_with_ratings(
                                                        aggregation='strict')
    config = configure_community_json()

    template = render_template(
        'community.html',
        current_app=flask.current_app,
        title=community.name,
        payload=community.jsonify(config=config, depth=2),
        key=community.trepr(tight=True, raw=False),
        problem=problem,
        connections=connections,
        org=org,
        geo=geo
        )
    return template
