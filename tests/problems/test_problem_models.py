#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_model(session):
    """Tests simple problem model interaction"""
    from intertwine.problems.models import Image, Problem

    problem_name = 'This is a Test Problem'
    problem = Problem(problem_name)
    assert Problem[problem.derive_key()] is problem
    session.add(problem)
    session.commit()
    assert session.query(Problem).first() is problem


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_connection_model(session):
    """Tests simple problem connection model interaction"""
    from intertwine.problems.models import Problem, ProblemConnection

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection = ProblemConnection('causal', problem1, problem2)
    assert ProblemConnection[connection.derive_key()] is connection
    session.add(problem1)
    session.add(problem2)
    session.add(connection)
    session.commit()
    problems = session.query(Problem).order_by(Problem.name).all()
    assert len(problems) == 2
    assert problems[0] is problem1
    assert problems[1] is problem2
    connections = session.query(ProblemConnection).all()
    assert len(connections) == 1
    assert connections[0] is connection
    assert problem1.impacts.all()[0].impact is problem2
    assert problem2.drivers.all()[0].driver is problem1


@pytest.mark.unit
@pytest.mark.smoke
def test_problem_connection_rating_model(session):
    """Tests simple problem connection rating model interaction"""
    from intertwine.geos.models import Geo
    from intertwine.problems.models import (Problem,
                                            ProblemConnection,
                                            ProblemConnectionRating)

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection = ProblemConnection('causal', problem1, problem2)
    org = None
    geo = Geo('Test Geo')
    rating = ProblemConnectionRating(rating=2,
                                     weight=1,
                                     connection=connection,
                                     problem=problem1,
                                     org=org,
                                     geo=geo,
                                     user='new_user')

    assert ProblemConnectionRating[rating.derive_key()] is rating
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


@pytest.mark.unit
@pytest.mark.smoke
def test_aggregate_problem_connection_rating_model(session):
    """Tests aggregate problem connection rating model interaction"""
    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import (Problem,
                                            ProblemConnection,
                                            ProblemConnectionRating,
                                            AggregateProblemConnectionRating)

    problem_name_base = 'Test Problem'
    problem1 = Problem(problem_name_base + ' 01')
    problem2 = Problem(problem_name_base + ' 02')
    connection12 = ProblemConnection('causal', problem1, problem2)
    org1 = 'University of Texas'
    geo1 = Geo('Austin')
    community1 = Community(problem=problem1, org=org1, geo=geo1)
    user1, user2, user3, user4 = 'user1', 'user2', 'user3', 'user4'

    session.add(geo1)
    session.add(problem1)
    session.add(problem2)
    session.add(connection12)
    session.add(community1)
    session.commit()

    rating1 = ProblemConnectionRating(rating=1,
                                      weight=1,
                                      connection=connection12,
                                      problem=problem1,
                                      org=org1,
                                      geo=geo1,
                                      user=user1)
    rating2 = ProblemConnectionRating(rating=2,
                                      weight=2,
                                      connection=connection12,
                                      problem=problem1,
                                      org=org1,
                                      geo=geo1,
                                      user=user2)
    rating3 = ProblemConnectionRating(rating=3,
                                      weight=3,
                                      connection=connection12,
                                      problem=problem1,
                                      org=org1,
                                      geo=geo1,
                                      user=user3)
    rating4 = ProblemConnectionRating(rating=4,
                                      weight=4,
                                      connection=connection12,
                                      problem=problem1,
                                      org=org1,
                                      geo=geo1,
                                      user=user4)

    for rating in connection12.ratings:
        session.add(rating)

    session.commit()

    rs = session.query(ProblemConnectionRating).order_by(
                       ProblemConnectionRating.id).all()

    assert rs[0].rating is rating1.rating
    assert rs[1].rating is rating2.rating
    assert rs[2].rating is rating3.rating
    assert rs[3].rating is rating4.rating

    ar1 = AggregateProblemConnectionRating(connection=connection12,
                                           community=community1,
                                           aggregation='strict')

    assert AggregateProblemConnectionRating[ar1.derive_key()] is ar1
    adjacent_problem = problem2
    assert ar1.adjacent_problem_name == adjacent_problem.name
    adjacent_community_url = Community.form_uri(Community.Key(
        adjacent_problem, org1, geo1))
    assert ar1.adjacent_community_url == adjacent_community_url

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
