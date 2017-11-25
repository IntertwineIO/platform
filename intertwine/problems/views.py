#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import (abort, current_app, jsonify, make_response, redirect,
                   render_template, request)

from . import blueprint
from .models import Problem, ProblemConnection
from .models import AggregateProblemConnectionRating as APCR
from ..exceptions import (InterfaceException, IntertwineException,
                          ResourceDoesNotExist)
from intertwine.utils.flask_utils import json_requested
from intertwine.utils.tools import vardygrify


@blueprint.errorhandler(InterfaceException)
def handle_interface_exception(error):
    '''Handle invalid usage

    Intercept the error and return a response consisting of the status
    code and a JSON representation of the error.
    '''
    return make_response(jsonify(error.jsonify()), error.status_code)


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    problems = Problem.query.order_by(Problem.name).all()
    template = render_template(
        'problems.html',
        current_app=current_app,
        title="Social Problems",
        problems=problems)
    return template


@blueprint.route(Problem.form_uri(
    Problem.Key('<problem_huid>'), sub=True), methods=['GET'])
def get_problem(problem_huid):
    '''Get problem endpoint'''
    if json_requested():
        return get_problem_json(problem_huid)

    return get_problem_html(problem_huid)


def get_problem_json(problem_huid):
    '''
    Get problem JSON

    Usage:
    curl -H 'accept:application/json' -X GET \
    'http://localhost:5000/problems/homelessness'
    '''
    json_kwargs = dict(Problem.objectify_json_kwargs(request.args))

    try:
        problem = Problem.get_problem(problem_huid, raise_on_miss=True)
    except IntertwineException as e:
        raise ResourceDoesNotExist(str(e))

    return jsonify(problem.jsonify(**json_kwargs))


def get_problem_html(problem_huid):
    '''
    Get problem HTML

    Redirect to global problem community page

    Usage:
    curl -H 'accept:text/html' -X GET \
    'http://localhost:5000/problems/homelessness'
    '''
    problem = Problem.get_problem(problem_huid)

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
    community_uri = Community.form_uri(Community.Key(problem, None, None))
    return redirect(community_uri, code=302)


@blueprint.route(ProblemConnection.form_uri(
    ProblemConnection.Key('<axis>', '<problem_a_huid>', '<problem_b_huid>'),
    sub=True), methods=['GET'])
def get_problem_connection(axis, problem_a_huid, problem_b_huid):
    '''Get problem connection endpoint'''
    if json_requested():
        return get_problem_connection_json(axis, problem_a_huid,
                                           problem_b_huid)

    return get_problem_connection_html(axis, problem_a_huid, problem_b_huid)


def get_problem_connection_json(axis, problem_a_huid, problem_b_huid):
    '''
    Get problem connection JSON

    Usage:
    curl -H 'accept:application/json' -X GET \
    'http://localhost:5000/problems/connections/scoped/poverty/homelessness'
    '''
    json_kwargs = dict(ProblemConnection.objectify_json_kwargs(request.args))

    try:
        connection = ProblemConnection.get_problem_connection(
            axis, problem_a_huid, problem_b_huid, raise_on_miss=True)
    except IntertwineException as e:
        raise ResourceDoesNotExist(str(e))

    return jsonify(connection.jsonify(**json_kwargs))


def get_problem_connection_html(axis, problem_a_huid, problem_b_huid):
    # TODO: add problem connection page
    abort(404)


@blueprint.route('/' + ProblemConnection.SUB_BLUEPRINT, methods=['POST'])
def add_problem_connection():
    '''
    Add problem connection

    Usage:
    curl -H "Content-Type: application/json" -X POST -d '{
        "axis": "causal",
        "problem_a": "Natural Disasters",
        "problem_b": "Homelessness"
    }' 'http://localhost:5000/problems/connections'
    '''
    connection_dict = request.get_json()
    connection = ProblemConnection(**connection_dict)

    session = connection.session()
    session.add(connection)
    session.commit()
    return jsonify(connection.jsonify(depth=2))


@blueprint.route('/' + APCR.SUB_BLUEPRINT, methods=['POST'])
def add_rated_problem_connection():
    '''
    Add problem connection and return aggregate rating

    Usage:
    curl -H "Content-Type: application/json" -X POST -d '{
        "connection": {
            "axis": "causal",
            "problem_a": "Natural Disasters",
            "problem_b": "Homelessness"
        },
        "community": {
            "problem": "homelessness",
            "org": null,
            "geo": "us/tx/austin"
        },
        "aggregation": "strict"
    }' 'http://localhost:5000/problems/rated_connections'
    '''
    from ..geos.models import Geo
    from ..communities.models import Community

    payload = request.get_json()

    community_dict = payload.get('community')

    problem = Problem[community_dict.get('problem')]
    org = community_dict.get('org')  # Replace with Org model
    geo = Geo[community_dict.get('geo')]
    try:
        community = Community[(problem, org, geo)]
    except KeyError:
        community = vardygrify(
            cls=Community, problem=problem, org=org, geo=geo, num_followers=0)

    connection_dict = payload.get('connection')
    connection = ProblemConnection(**connection_dict)

    session = connection.session()
    session.add(connection)
    session.commit()

    connection_category = connection.derive_category(problem)
    aggregation = payload.get('aggregation')

    aggregate_rating = vardygrify(
        cls=APCR, community=community, connection=connection,
        connection_category=connection_category, aggregation=aggregation,
        rating=APCR.NO_RATING, weight=APCR.NO_WEIGHT)

    return jsonify(aggregate_rating.jsonify())
