# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import (abort, current_app, jsonify, make_response, render_template,
                   # redirect, request
                   )

from . import blueprint
from .models import Problem, ProblemConnection
from ..exceptions import InterfaceException, ResourceAlreadyExists
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


@blueprint.route('/{subcategory}/<axis>/<problem_a_key>/<problem_b_key>'
                 .format(subcategory=ProblemConnection.BLUEPRINT_SUBCATEGORY),
                 methods=['POST'])
def add_problem_connection(axis, problem_a_key, problem_b_key):
    '''Add a connection between two problems

    Usage:
    curl -H "Content-Type: application/json" -X POST -d '{
    "community_problem_key":"homelessness","community_geo_key":"us/tx/austin"
    }' 'http://localhost:5000/problems/connections/causal/natural_disasters/homelessness'
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
            problem_name = Problem.infer_name_from_key(problem_key)
            try:
                problem = Problem(problem_name)
            except NameError as e:
                raise InvalidProblemName(str(e))
            if problem.human_id != problem_key:
                raise InvalidProblemName('Key derived from problem name '
                                         'differs from resource key')
        problems.append(problem)

    problem_a, problem_b = problems

    connection = ProblemConnection.query.filter_by(
        axis=axis, problem_a_id=problem_a.id, problem_b_id=problem_b.id
    ).first()

    if connection is not None:
        raise ResourceAlreadyExists(cls='ProblemConnection')

    connection = ProblemConnection(
        axis=axis, problem_a=problem_a, problem_b=problem_b)
    session = connection.session()
    session.add(connection)
    session.commit()
    return jsonify(connection.jsonify())

    # # Temporary: Redirect instead of returning the connection JSON:
    # payload = request.get_json()
    # community_problem_key = payload.get('community_problem_key')
    # community_org_key = payload.get('community_org_key')
    # community_geo_key = payload.get('community_geo_key')
    # from ..communities.models import Community
    # community_uri = Community.form_uri(problem=community_problem_key,
    #                                    org=community_org_key,
    #                                    geo=community_geo_key)
    # return redirect(community_uri, code=302)
