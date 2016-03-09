#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import render_template

from titlecase import titlecase

from . import blueprint

from .models import Problem, db


@blueprint.route('/', methods=['GET'])
def render():
    '''Generic page rendering for top level'''
    app = flask.current_app
    with app.app_context():
        session = db.session
        problems = session.query(Problem).order_by(Problem.name).all()
        template = render_template(
            'problems.html',
            current_app=flask.current_app,
            title="Problems",
            problems=problems)
        return template


@blueprint.route('/<problem_name>', methods=['GET'])
def render_problem(problem_name):
    '''Problem Page'''
    p_name = titlecase(problem_name.replace('_', ' '))
    app = flask.current_app
    with app.app_context():
        session = db.session
        problem = session.query(Problem).filter_by(name=p_name).one()
        template = render_template(
            'problem.html',
            current_app=app,
            title=problem.name,
            problem=problem)
        return template
