#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_model(options):
    '''Tests simple problem model interaction'''
    from intertwine.problems.models import Problem
    from data.data_process import DataSessionManager, erase_data
    # To test in interpreter, use below:
    # from config import DevConfig; config = DevConfig
    config = options['config']
    dsm = DataSessionManager(config.DATABASE)
    session = dsm.session
    assert session is not None
    assert session.query(Problem).all() == []
    problem_name = 'This is a Test Problem'
    problem = Problem(problem_name)
    session.add(problem)
    session.commit()
    assert session.query(Problem).first() == problem
    # Clean up after ourselves
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_connection_model(options):
    '''Tests simple problem connection model interaction'''
    from intertwine.problems.models import Problem, ProblemConnection
    from data.data_process import DataSessionManager, erase_data
    # To test in interpreter, use below:
    # from config import DevConfig; config = DevConfig
    config = options['config']
    dsm = DataSessionManager(config.DATABASE)
    session = dsm.session
    assert session is not None
    assert session.query(Problem).all() == []
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
    # Clean up after ourselves
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_connection_rating_model(options):
    '''Tests simple problem connection rating model interaction'''
    from intertwine.problems.models import (Problem, ProblemConnection,
                                            ProblemConnectionRating)
    from data.data_process import DataSessionManager, erase_data
    # To test in interpreter, use below:
    # from config import DevConfig; config = DevConfig
    config = options['config']
    dsm = DataSessionManager(config.DATABASE)
    session = dsm.session
    assert session is not None
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection = ProblemConnection('causal', problem1, problem2)
    org = None
    geo = 'United States/Texas/Austin'
    rating = ProblemConnectionRating(problem=problem1,
                                     connection=connection,
                                     org=org,
                                     geo=geo,
                                     user='new_user',
                                     rating=2)
    session.add(problem1)
    session.add(problem2)
    session.add(connection)
    session.add(rating)
    session.commit()
    ratings = session.query(ProblemConnectionRating).all()
    assert len(ratings) == 1
    r = ratings[0]
    assert r == rating
    assert r.problem == problem1
    assert r.connection == connection
    assert r.org == org
    assert r.geo == geo
    assert r.rating == 2
    # Clean up after ourselves
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []


@pytest.mark.unit
@pytest.mark.smoke
def test_aggregate_problem_connection_rating_model(options):
    '''Tests aggregate problem connection rating model interaction'''
    from alchy import Manager
    from alchy.model import extend_declarative_base
    from data.data_process import erase_data
    from intertwine.problems.models import (BaseProblemModel,
                                            Problem,
                                            ProblemConnection,
                                            ProblemConnectionRating,
                                            AggregateProblemConnectionRating)
    # To test in interpreter, use below:
    # from config import DevConfig; config = DevConfig
    config = options['config']
    problem_db = Manager(Model=BaseProblemModel, config=config)
    problem_db.create_all()
    session = problem_db.session
    assert session is not None
    extend_declarative_base(BaseProblemModel, session=session)
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []
    assert session.query(AggregateProblemConnectionRating).all() == []

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection = ProblemConnection('causal', problem1, problem2)
    org1 = 'University of Texas'
    org2 = None
    geo1 = 'United States/Texas/Austin'
    geo2 = None
    r1 = ProblemConnectionRating(problem=problem1,
                                 connection=connection,
                                 org=org1,
                                 geo=geo1,
                                 user='new_user',
                                 rating=1)
    r2 = ProblemConnectionRating(problem=problem1,
                                 connection=connection,
                                 org=org2,
                                 geo=geo1,
                                 user='new_user',
                                 rating=2)
    r3 = ProblemConnectionRating(problem=problem1,
                                 connection=connection,
                                 org=org1,
                                 geo=geo2,
                                 user='new_user',
                                 rating=3)
    r4 = ProblemConnectionRating(problem=problem1,
                                 connection=connection,
                                 org=org2,
                                 geo=geo2,
                                 user='new_user',
                                 rating=4)
    session.add(problem1)
    session.add(problem2)
    session.add(connection)
    for r in connection.ratings:
        session.add(r)

    session.commit()
    ar1 = AggregateProblemConnectionRating(problem=problem1,
                                           connection=connection,
                                           org=org1,
                                           geo=geo1,
                                           aggregation='strict')
    ar2 = AggregateProblemConnectionRating(problem=problem1,
                                           connection=connection,
                                           org=org2,
                                           geo=geo1,
                                           aggregation='strict')
    ar3 = AggregateProblemConnectionRating(problem=problem1,
                                           connection=connection,
                                           org=org1,
                                           geo=geo2,
                                           aggregation='strict')
    ar4 = AggregateProblemConnectionRating(problem=problem1,
                                           connection=connection,
                                           org=org2,
                                           geo=geo2,
                                           aggregation='strict')
    for ar in connection.aggregate_ratings:
        session.add(ar)

    session.commit()
    ars = session.query(AggregateProblemConnectionRating).order_by(
            AggregateProblemConnectionRating.id).all()
    assert len(ars) == 4
    assert round(ars[0].rating) == 1.0
    assert round(ars[0].weight) == 1.0
    assert round(ars[1].rating, 2) == 1.5
    assert round(ars[1].weight, 2) == 2.0
    assert round(ars[2].rating, 2) == 2.0
    assert round(ars[2].weight, 2) == 2.0
    assert round(ars[3].rating, 2) == 2.5
    assert round(ars[3].weight, 2) == 4.0

    # Change rating on r2 and validate that aggregates 2 and 4 updated
    r2.rating = 0
    assert round(ars[0].rating) == 1.0
    assert round(ars[0].weight) == 1.0
    assert round(ars[1].rating, 2) == 0.5
    assert round(ars[1].weight, 2) == 2.0
    assert round(ars[2].rating, 2) == 2.0
    assert round(ars[2].weight, 2) == 2.0
    assert round(ars[3].rating, 2) == 2.0
    assert round(ars[3].weight, 2) == 4.0

    # Clean up after ourselves
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []
    assert session.query(AggregateProblemConnectionRating).all() == []
