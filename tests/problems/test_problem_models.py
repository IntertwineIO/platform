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
    # from config import DevConfig; test_config = DevConfig
    test_config = options['config']
    dsm = DataSessionManager(test_config.DATABASE)
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
    # from config import DevConfig; test_config = DevConfig
    test_config = options['config']
    dsm = DataSessionManager(test_config.DATABASE)
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
    from data.data_process import DataSessionManager, erase_data
    from intertwine.geos.models import Geo
    from intertwine.problems.models import (Problem,
                                            ProblemConnection,
                                            ProblemConnectionRating)
    # To test in interpreter, use below:
    # from config import DevConfig; test_config = DevConfig
    test_config = options['config']
    dsm = DataSessionManager(test_config.DATABASE)
    session = dsm.session

    assert session is not None
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []
    assert session.query(Geo).all() == []

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection = ProblemConnection('causal', problem1, problem2)
    org = None
    geo = Geo('Test Geo')
    rating = ProblemConnectionRating(rating=2,
                                     problem=problem1,
                                     connection=connection,
                                     org=org,
                                     geo=geo,
                                     user='new_user')
    session.add(geo)
    session.add(problem1)
    session.add(problem2)
    session.add(connection)
    session.add(rating)
    session.commit()
    ratings = session.query(ProblemConnectionRating).all()
    assert len(ratings) == 1
    r = ratings[0]
    assert r is rating
    assert r.problem is problem1
    assert r.connection is connection
    assert r.org == org
    assert r.geo is geo
    assert r.rating == 2
    # Clean up after ourselves
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []
    assert session.query(Geo).all() == []


@pytest.mark.unit
@pytest.mark.smoke
def test_aggregate_problem_connection_rating_model(options):
    '''Tests aggregate problem connection rating model interaction'''
    from data.data_process import DataSessionManager, erase_data
    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import (Problem,
                                            ProblemConnection,
                                            ProblemConnectionRating,
                                            AggregateProblemConnectionRating)
    # To test in interpreter, use below:
    # from config import DevConfig; test_config = DevConfig
    test_config = options['config']
    dsm = DataSessionManager(test_config.DATABASE)
    session = dsm.session

    assert session is not None
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []
    assert session.query(AggregateProblemConnectionRating).all() == []
    assert session.query(Geo).all() == []
    assert session.query(Community).all() == []

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection12 = ProblemConnection('causal', problem1, problem2)
    org1 = 'University of Texas'
    geo1 = Geo('Austin')
    community1 = Community(problem=problem1, org=org1, geo=geo1)
    user1, user2, user3, user4 = 'user1', 'user2', 'user3', 'user4'

    rating1 = ProblemConnectionRating(problem=problem1,
                                      connection=connection12,
                                      org=org1,
                                      geo=geo1,
                                      user=user1,
                                      rating=1,
                                      weight=1)
    rating2 = ProblemConnectionRating(problem=problem1,
                                      connection=connection12,
                                      org=org1,
                                      geo=geo1,
                                      user=user2,
                                      rating=2,
                                      weight=2)
    rating3 = ProblemConnectionRating(problem=problem1,
                                      connection=connection12,
                                      org=org1,
                                      geo=geo1,
                                      user=user3,
                                      rating=3,
                                      weight=3)
    rating4 = ProblemConnectionRating(problem=problem1,
                                      connection=connection12,
                                      org=org1,
                                      geo=geo1,
                                      user=user4,
                                      rating=4,
                                      weight=4)
    session.add(geo1)
    session.add(problem1)
    session.add(problem2)
    session.add(connection12)
    session.add(community1)
    for rating in connection12.ratings:
        session.add(rating)

    session.commit()
    ar1 = AggregateProblemConnectionRating(connection=connection12,
                                           community=community1,
                                           aggregation='strict')
    session.add(ar1)

    session.commit()
    ars = session.query(AggregateProblemConnectionRating).order_by(
                        AggregateProblemConnectionRating.id).all()
    assert len(ars) == 1
    assert ars[0] is ar1
    assert round(ar1.rating, 1) == 3.0
    assert round(ar1.weight, 1) == 10.0

    # Change rating and validate that aggregate rating updated
    rating3.rating = 0
    assert round(ar1.rating, 1) == 2.1
    assert round(ar1.weight, 1) == 10.0

    # Clean up after ourselves
    erase_data(session, confirm='ERASE')
    assert session.query(Problem).all() == []
    assert session.query(ProblemConnection).all() == []
    assert session.query(ProblemConnectionRating).all() == []
    assert session.query(AggregateProblemConnectionRating).all() == []
    assert session.query(Geo).all() == []
    assert session.query(Community).all() == []
