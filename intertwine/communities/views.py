#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import abort, redirect, render_template

from . import blueprint
from .models import Community
from ..utils import make_vardygr
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
        community = make_vardygr(Community, problem=problem, org=org, geo=geo,
                                 num_followers=0)

    connections = community.assemble_connections_with_ratings(
                                                        aggregation='strict')

    template = render_template(
        'community.html',
        current_app=flask.current_app,
        title=problem.name,  # Update to include org/geo
        problem=problem,
        connections=connections,
        org=org,
        geo=geo
        )
    return template
