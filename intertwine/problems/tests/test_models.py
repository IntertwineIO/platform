#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_model(options):
    '''Tests simple problem model interaction'''
    from intertwine import create_app
    from intertwine.config import ToxConfig
    from intertwine.problems import problems_db
    from intertwine.problems.models import Problem as Model

    app = create_app(ToxConfig)
    with app.app_context():
        session = problems_db.session
        assert session is not None
        assert session.query(Model).all() == []
        problem_name = 'testProblem'
        problem = Model(problem_name)
        session.add(problem)
        session.commit()
        assert session.query(Model).all() != []
        query = session.query(Model).filter_by(name='testProblem')
        assert problem in query.all()


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_connection_model(options):
    '''Tests simple problem model interaction'''
    from intertwine import create_app
    from intertwine.config import ToxConfig
    from intertwine.problems import problems_db
    from intertwine.problems.models import ProblemConnection, Problem

    app = create_app(ToxConfig)
    with app.app_context():
        session = problems_db.session
        assert session is not None
        assert session.query(ProblemConnection).all() == []
        problem_name = 'testProblem'
        problem1 = Problem(problem_name + '01')
        problem2 = Problem(problem_name + '02')
        connection = ProblemConnection('causal',problem1, problem2)
        session.add(problem1)
        session.add(problem2)
        session.add(connection)
        session.commit()
        assert session.query(Problem).all() != []
        assert session.query(ProblemConnection).all() != []
        query = session.query(ProblemConnection)
        assert connection in query.all()
