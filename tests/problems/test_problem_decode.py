# -*- coding: utf-8 -*-
import os
import pytest

import settings
from data.data_process import decode
from intertwine.geos.models import Geo
from intertwine.problems.models import (
    Problem, ProblemConnection, ProblemConnectionRating)
from intertwine.trackable import Trackable

PROBLEM_DATA_DIRECTORY = os.path.join(settings.PROJECT_ROOT, 'data/problems')


def create_geo_data(session):
    """Util to create geos referenced in problem JSON"""
    assert Geo.query.all() == []
    us = Geo(name='United States', abbrev='U.S.')
    tx = Geo(name='Texas', abbrev='TX', path_parent=us, parents=[us])
    austin = Geo(name='Austin', path_parent=tx, parents=[tx])
    session.add_all((us, tx, austin))
    session.commit()
    geo = Geo.query.filter_by(human_id='us/tx/austin').one()
    assert geo is Geo['us/tx/austin']


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem(session, caching):
    """Test decoding a standard problem"""
    assert session is not None
    assert Problem.query.all() == []

    create_geo_data(session)

    json_path = os.path.join(PROBLEM_DATA_DIRECTORY, 'problems01.json')
    u1 = decode(session, json_path)
    for updates in u1.values():
        session.add_all(updates)
    session.commit()

    p1 = Problem.query.filter_by(name='Homelessness').one()
    assert p1 is Problem['homelessness']
    assert len(p1.definition) > 0
    assert len(p1.definition_url) > 0
    assert len(p1.images.all()) > 0
    assert len(p1.drivers.all()) > 0
    assert len(p1.impacts.all()) > 0
    assert len(p1.broader.all()) > 0
    assert len(p1.narrower.all()) > 0


@pytest.mark.unit
@pytest.mark.smoke
# @pytest.mark.xfail(reason='python3 unicode issue')
def test_decode_problem_connection(session, caching):
    """Test decoding a standard problem connection"""
    assert session is not None
    assert Problem.query.all() == []
    assert ProblemConnection.query.all() == []

    create_geo_data(session)

    json_path = os.path.join(PROBLEM_DATA_DIRECTORY, 'problems00.json')
    u0 = decode(session, json_path)
    for updates in u0.values():
        session.add_all(updates)
    session.commit()

    p0 = Problem.query.filter_by(name='Poverty').one()
    assert p0 is Problem['poverty']
    p1 = Problem.query.filter_by(name='Homelessness').one()
    assert p1 is Problem['homelessness']

    c1 = ProblemConnection.query.filter(
        ProblemConnection.axis == 'scoped',
        ProblemConnection.broader == p0,
        ProblemConnection.narrower == p1).one()
    assert c1.axis == 'scoped'
    assert c1.broader == p0
    assert c1.narrower == p1


@pytest.mark.unit
@pytest.mark.smoke
# @pytest.mark.xfail(reason='python3 unicode issue')
def test_decode_problem_connection_rating(session, caching):
    """Test decoding ratings on a single problem connection"""
    create_geo_data(session)

    u = decode(session, PROBLEM_DATA_DIRECTORY)  # Decode entire directory
    for updates in u.values():
        session.add_all(updates)
    session.commit()

    p0 = Problem.query.filter_by(name='Poverty').one()
    p1 = Problem.query.filter_by(name='Homelessness').one()

    c1 = ProblemConnection.query.filter(
        ProblemConnection.axis == 'scoped',
        ProblemConnection.broader == p0,
        ProblemConnection.narrower == p1).one()

    rs1 = ProblemConnectionRating.query.filter(
        ProblemConnectionRating.connection == c1)
    assert len(rs1.all()) > 0
    for r in rs1:
        assert r.connection is c1


@pytest.mark.unit
@pytest.mark.smoke
# @pytest.mark.xfail(reason='python3 unicode issue')
def test_incremental_decode(session, caching):
    """Test decoding multiple files incrementally"""
    create_geo_data(session)

    # Initial data load:
    json_path = os.path.join(PROBLEM_DATA_DIRECTORY, 'problems00.json')
    u0 = decode(session, json_path)
    for updates in u0.values():
        session.add_all(updates)
    session.commit()
    p0 = Problem.query.filter_by(name='Poverty').one()
    assert p0 is Problem['poverty']

    # Simulate impact of app restart on Trackable by clearing it:
    Trackable.clear_all()

    # Next data load:
    json_path = os.path.join(PROBLEM_DATA_DIRECTORY, 'problems01.json')
    u1 = decode(session, json_path)
    for updates in u1.values():
        session.add_all(updates)
    session.commit()
    p0 = Problem.query.filter_by(name='Poverty').one()
    assert p0 is Problem['poverty']
    p1 = Problem.query.filter_by(name='Homelessness').one()
    assert p1 is Problem['homelessness']

    # Simulate impact of app restart on Trackable by clearing it:
    Trackable.clear_all()

    # Next data load:
    json_path = os.path.join(PROBLEM_DATA_DIRECTORY, 'problems02.json')
    u2 = decode(session, json_path)
    for updates in u2.values():
        session.add_all(updates)
    session.commit()

    # Make sure they're still the same problems
    p0 = Problem.query.filter_by(name='Poverty').one()
    assert p0 is Problem['poverty']
    p1 = Problem.query.filter_by(name='Homelessness').one()
    assert p1 is Problem['homelessness']
    p2 = Problem.query.filter_by(name='Domestic Violence').one()
    assert p2 is Problem['domestic_violence']

    c1 = ProblemConnection.query.filter(
        ProblemConnection.axis == 'scoped',
        ProblemConnection.broader == p0,
        ProblemConnection.narrower == p1).one()
    assert c1.axis == 'scoped'
    assert c1.broader is p0
    assert c1.narrower is p1

    c2 = ProblemConnection.query.filter(
        ProblemConnection.axis == 'causal',
        ProblemConnection.driver == p2,
        ProblemConnection.impact == p1).one()
    assert c2.axis == 'causal'
    assert c2.driver is p2
    assert c2.impact is p1

    rs1 = ProblemConnectionRating.query.filter(
        ProblemConnectionRating.connection == c1)
    assert len(rs1.all()) > 0
    for r in rs1:
        assert r.connection is c1

    geo = Geo['us/tx/austin']
    rs2 = ProblemConnectionRating.query.filter(
        ProblemConnectionRating.problem == p1,
        ProblemConnectionRating.connection == c2,
        ProblemConnectionRating.org.is_(None),
        ProblemConnectionRating.geo == geo)
    assert len(rs2.all()) > 0
    for r in rs2:
        assert r.problem == p1
        assert r.connection == c2
        assert r.org is None
        assert r.geo is geo


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_same_data(session, caching):
    """Test decoding incrementally"""
    create_geo_data(session)

    json_path = os.path.join(PROBLEM_DATA_DIRECTORY, 'problems02.json')
    u2 = decode(session, json_path)
    for updates in u2.values():
        session.add_all(updates)
    session.commit()
    p2 = Problem.query.filter_by(name='Domestic Violence').one()
    assert p2 is Problem['domestic_violence']

    # Simulate impact of app restart on Trackable by clearing it:
    Trackable.clear_all()

    # Try reloading existing data (none should be loaded):
    u2_repeat = decode(session, json_path)
    for updates in u2_repeat.values():
        assert len(updates) == 0
