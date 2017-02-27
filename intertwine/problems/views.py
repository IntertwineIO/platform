# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import (abort, current_app, jsonify, make_response, render_template,
                   # redirect,
                   request)

from . import blueprint
from .models import Problem, ProblemConnection
from .models import AggregateProblemConnectionRating as APCR
from ..exceptions import InterfaceException, ResourceDoesNotExist
from .exceptions import InvalidAxis
from ..utils.tools import vardygrify


@blueprint.errorhandler(InterfaceException)
def handle_interface_exception(error):
    '''Handle invalid usage

    Intercepts the error and returns a response consisting of the status
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


@blueprint.route('/<problem_key>', methods=['GET'])
def render_problem(problem_key):
    '''Problem page redirects to global community page'''
    problem_key = problem_key.lower()
    problem = Problem.query.filter_by(human_id=problem_key).first()

    if problem is None:
        # TODO: Instead of aborting, reroute to problem_not_found page
        # Oops! 'X' is not a problem found in Intertwine.
        # Did you mean:
        # <related_problem_1>
        # <related_problem_2>
        # <related_problem_3>
        # Or, you can create 'X' in Intertwine'
        abort(404)

    # from ..communities.models import Community
    # community_uri = Community.form_uri(problem=problem, org=None, geo=None)
    # return redirect(community_uri, code=302)


@blueprint.route('/' + ProblemConnection.BLUEPRINT_SUBCATEGORY,
                 methods=['POST'])
def add_problem_connection():
    '''Add a connection between two problems

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


@blueprint.route('/{subcategory}/<axis>/<problem_a_key>/<problem_b_key>'
                 .format(subcategory=ProblemConnection.BLUEPRINT_SUBCATEGORY),
                 methods=['GET'])
def get_problem_connection(axis, problem_a_key, problem_b_key):
    '''Get a problem connection

    Usage:
    curl -H "Content-Type: application/json" -X GET \
    'http://localhost:5000/problems/connections/scoped/poverty/homelessness'
    '''
    axis = axis.lower()
    valid_axes = ProblemConnection.AXES
    if axis not in valid_axes:
        raise InvalidAxis(invalid_axis=axis, valid_axes=valid_axes)

    problem_data = (problem_a_key.lower(), problem_b_key.lower())
    problems = []
    for problem_key in problem_data:
        problem = Problem[problem_key]
        if problem is None:
            raise ResourceDoesNotExist(cls='Problem', key=problem_key)
        problems.append(problem)

    problem_a, problem_b = problems
    connection_key = ProblemConnection.Key(axis, problem_a, problem_b)
    connection = ProblemConnection[connection_key]

    if connection is None:
        raise ResourceDoesNotExist(cls='ProblemConnection', key=connection_key)

    return jsonify(connection.jsonify())


@blueprint.route('/' + APCR.BLUEPRINT_SUBCATEGORY, methods=['POST'])
def add_rated_problem_connection():
    '''Add a problem connection and return the aggregate rating

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

    aggregation = payload.get('aggregation')
    aggregate_rating = vardygrify(
        cls=APCR, community=community, connection=connection,
        aggregation=aggregation, rating=APCR.NO_RATING, weight=APCR.NO_WEIGHT)

    return jsonify(aggregate_rating.jsonify())
