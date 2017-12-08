#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import flask
from flask import (abort, jsonify, make_response, redirect, render_template,
                   request)

from . import blueprint
from intertwine.exceptions import (InterfaceException, IntertwineException,
                                   ResourceDoesNotExist)
from intertwine.geos.models import Geo
from intertwine.problems.models import Problem, ProblemConnection
from intertwine.utils.flask_utils import json_requested
from intertwine.utils.jsonable import Jsonable
from intertwine.utils.tools import vardygrify
from .models import Community


@blueprint.errorhandler(InterfaceException)
def handle_interface_exception(error):
    '''
    Handle Interface Exception

    Intercept the error and return a response consisting of the status
    code and a JSON representation of the error.
    '''
    return make_response(jsonify(error.jsonify()), error.status_code)


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


@blueprint.route('/<problem_huid>/', methods=['GET'])
def get_global_community(problem_huid):
    return get_community(problem_huid, '')


@blueprint.route('/<problem_huid>/<path:geo_huid>', methods=['GET'])
def get_community(problem_huid, geo_huid):
    '''Community Page'''
    # TODO: add org to URL or query string
    org_huid = None
    if json_requested():
        return get_community_json(problem_huid, org_huid, geo_huid)

    return get_community_html(problem_huid, org_huid, geo_huid)


def get_community_json(problem_huid, org_huid, geo_huid):
    '''
    Get Community JSON

    Usage:
    curl -H 'accept:application/json' -X GET \
    'http://localhost:5000/communities/homelessness/us/tx/austin'
    '''
    json_kwargs = dict(Community.objectify_json_kwargs(request.args))

    try:
        community = Community.manifest(problem_huid, org_huid, geo_huid)

    except IntertwineException as e:
        raise ResourceDoesNotExist(str(e))

    if not request.args.get('config'):
        json_kwargs['config'] = configure_community_json()
    return jsonify(community.jsonify(**json_kwargs))


def get_community_html(problem_huid, org_huid, geo_huid):
    problem_huid = problem_huid.lower()
    problem = Problem.query.filter_by(human_id=problem_huid).first()

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
    geo_huid = geo_huid.lower()

    if geo_huid:
        corrected_url = False
        if geo_huid[-1] == '/':
            geo_huid = geo_huid.rstrip('/')
            corrected_url = True

        geo = Geo.query.filter_by(human_id=geo_huid).first()

        if geo is None:
            # TODO: Instead of aborting, reroute to geo_not_found page
            # Oops! 'X' is not a geo found in Intertwine.
            # Did you mean:
            # <geo_1>
            # <geo_2>
            # <geo_3>
            abort(404)

        alias_targets = geo.alias_targets
        if alias_targets:
            return redirect(Community.form_uri(
                Community.Key(problem, org, alias_targets[0])), code=302)
        if corrected_url:
            return redirect(Community.form_uri(
                Community.Key(problem, org, geo)), code=302)
    else:
        geo = None

    community = Community.query.filter_by(
        problem=problem, org=org, geo=geo).first()

    if not community:
        community = vardygrify(Community, problem=problem, org=org, geo=geo,
                               num_followers=0)

    config = configure_community_json()
    payload = community.jsonify(config=config)

    template = render_template(
        'community.html',
        current_app=flask.current_app,
        title=community.name,
        payload=payload)
    return template


def configure_community_json():
    config = {
        '.problem': 1,
        '.geo': 1,
        '.aggregate_ratings': -2
    }
    for category in ProblemConnection.CATEGORY_MAP:
        config[Jsonable.form_path('.problem', category)] = 0
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'rating')] = 1
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'adjacent_problem_name')] = 1
        config[Jsonable.form_path('.aggregate_ratings', category,
                                  'adjacent_community_url')] = 1
    return config
