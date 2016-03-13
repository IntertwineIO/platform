#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_model(options):
    '''Tests simple problem model interaction'''
    from intertwine.config import ToxConfig
    from intertwine.problems.models import Problem
    from data.data_process import DataSessionManager, erase_data

    # DSM only creates a session if one doesn't exist
    dsm = DataSessionManager(ToxConfig.DATABASE)
    session = dsm.session
    assert session is not None
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []
    problem_name = 'This is a Test Problem'
    problem = Problem(problem_name)
    session.add(problem)
    session.commit()
    assert session.query(Problem).first() == problem


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_connection_model(options):
    '''Tests simple problem model interaction'''
    from intertwine.config import ToxConfig
    from intertwine.problems.models import Problem, ProblemConnection
    from data.data_process import DataSessionManager, erase_data

    # DSM only creates a session if one doesn't exist
    dsm = DataSessionManager(ToxConfig.DATABASE)
    session = dsm.session
    assert session is not None
    erase_data(session, confirm='ERASE')
    assert session.query(ProblemConnection).all() == []
    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection = ProblemConnection('causal', problem1, problem2)
    session.add(problem1)
    session.add(problem2)
    session.add(connection)
    session.commit()
    problems = session.query(Problem).order_by(Problem.name).all()
    assert len(problems) == 2
    assert problems[0] == problem1
    assert problems[1] == problem2
    connections = session.query(ProblemConnection).all()
    assert len(connections) == 1
    assert connection == connections[0]
    assert problem1.impacts.all()[0].impact == problem2
    assert problem2.drivers.all()[0].driver == problem1
