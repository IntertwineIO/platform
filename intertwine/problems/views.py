# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import (abort, current_app, jsonify, make_response, render_template,
                   # redirect,
                   request)

from . import blueprint
from .models import Problem, ProblemConnection
from ..exceptions import (InterfaceException, ResourceAlreadyExists,
                          ResourceDoesNotExist)
from .exceptions import InvalidAxis, InvalidProblemName


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
        "problem_a_name": "Natural Disasters",
        "problem_b_name": "Homelessness",
        "community": {
            "problem": "homelessness",
            "org": null,
            "geo": "us/tx/austin"
        }
    }' 'http://localhost:5000/problems/connections'
    '''
    payload = request.get_json()
    axis = payload.get('axis').lower()
    valid_axes = ProblemConnection.AXES
    if axis not in valid_axes:
        raise InvalidAxis(invalid_axis=axis, valid_axes=valid_axes)

    problem_a_name = payload.get('problem_a_name')
    problem_b_name = payload.get('problem_b_name')
    problem_data = (problem_a_name, problem_b_name)
    problems = []
    for problem_name in problem_data:
        if not problem_name:
            raise InvalidProblemName(problem_name=problem_name)
        problem_key = Problem.create_key(problem_name)
        problem = Problem.query.filter_by(**problem_key._asdict()).first()
        if problem is None:
            try:
                problem = Problem(problem_name)
            except NameError as e:
                raise InvalidProblemName(str(e))
            if problem.derive_key() != problem_key:
                raise InvalidProblemName('Key derived from problem name '
                                         'differs from resource key')
        problems.append(problem)

    problem_a, problem_b = problems

    connection = ProblemConnection.query.filter_by(
        axis=axis, problem_a_id=problem_a.id, problem_b_id=problem_b.id
    ).first()

    if connection is not None:
        raise ResourceAlreadyExists(cls='ProblemConnection',
                                    key=connection.derive_key())

    connection = ProblemConnection(
        axis=axis, problem_a=problem_a, problem_b=problem_b)
    session = connection.session()
    session.add(connection)
    session.commit()
    return jsonify(connection.jsonify())

    # # Temporary: Redirect instead of returning the connection JSON:
    # community_dict = payload.get('community')
    # problem_human_id = community_dict.get('problem_human_id')
    # org_human_id = community_dict.get('org_human_id')
    # geo_human_id = community_dict.get('geo_human_id')
    # from ..communities.models import Community
    # community_uri = Community.form_uri(problem=problem_human_id,
    #                                    org=org_human_id,
    #                                    geo=geo_human_id)
    # return redirect(community_uri, code=302)


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
        problem = Problem.query.filter_by(human_id=problem_key).first()
        if problem is None:
            raise ResourceDoesNotExist(cls='Problem', key=problem_key)
        problems.append(problem)

    problem_a, problem_b = problems

    connection = ProblemConnection.query.filter_by(
        axis=axis, problem_a_id=problem_a.id, problem_b_id=problem_b.id
    ).first()

    if connection is None:
        key = ProblemConnection.create_key(axis, problem_a, problem_b)
        raise ResourceDoesNotExist(cls='ProblemConnection', key=key)

    return jsonify(connection.jsonify())
