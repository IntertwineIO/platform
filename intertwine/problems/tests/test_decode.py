#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem(options):
    '''Tests decoding a standard problem'''
    from intertwine.config import ToxConfig
    from intertwine.problems.models import Problem
    from data.data_process import DataSessionManager, erase_data, decode

    # DSM only creates a session if one doesn't exist
    dsm = DataSessionManager(ToxConfig.DATABASE)
    session = dsm.session
    assert session is not None

    # Erase data
    erase_data(session, confirm='ERASE')

    # Decode
    u1 = decode(session, 'data/problems/problems01.json')
    for updates in u1.values():
        session.add_all(updates)
    session.commit()

    p1 = session.query(Problem).filter_by(name='Homelessness').one()
    assert p1.name == 'Homelessness'
    assert len(p1.definition) > 0
    assert len(p1.definition_url) > 0
    assert len(p1.images.all()) > 0
    assert len(p1.drivers.all()) > 0
    assert len(p1.impacts.all()) > 0
    assert len(p1.broader.all()) > 0
    assert len(p1.narrower.all()) > 0


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem_connection(options):
    '''Tests decoding a standard problem connection'''
    from intertwine.config import ToxConfig
    from intertwine.problems.models import Problem, ProblemConnection
    from data.data_process import DataSessionManager, erase_data, decode

    # DSM only creates a session if one doesn't exist
    dsm = DataSessionManager(ToxConfig.DATABASE)
    session = dsm.session
    assert session is not None

    # Erase data
    erase_data(session, confirm='ERASE')

    # Decode
    u0 = decode(session, 'data/problems/problems00.json')
    for updates in u0.values():
        session.add_all(updates)
    session.commit()

    p0 = session.query(Problem).filter_by(name='Poverty').one()
    p1 = session.query(Problem).filter_by(name='Homelessness').one()

    c1 = session.query(ProblemConnection).filter(
        ProblemConnection.connection_type == 'scoped',
        ProblemConnection.broader == p0,
        ProblemConnection.narrower == p1).one()
    assert c1.connection_type == 'scoped'
    assert c1.broader == p0
    assert c1.narrower == p1


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem_connection_rating(options):
    '''Tests decoding ratings on a single problem connection'''
    from intertwine.config import ToxConfig
    from intertwine.problems.models import (Problem, ProblemConnection,
                                            ProblemConnectionRating)
    from data.data_process import DataSessionManager, erase_data, decode

    # DSM only creates a session if one doesn't exist
    dsm = DataSessionManager(ToxConfig.DATABASE)
    session = dsm.session
    assert session is not None

    # Erase data
    erase_data(session, confirm='ERASE')

    # Decode directory:
    u = decode(session, 'data/problems/')
    for updates in u.values():
        session.add_all(updates)
    session.commit()

    p0 = session.query(Problem).filter_by(name='Poverty').one()
    p1 = session.query(Problem).filter_by(name='Homelessness').one()

    c1 = session.query(ProblemConnection).filter(
        ProblemConnection.connection_type == 'scoped',
        ProblemConnection.broader == p0,
        ProblemConnection.narrower == p1).one()

    rs1 = session.query(ProblemConnectionRating).filter(
        ProblemConnectionRating.connection == c1)
    assert len(rs1.all()) > 0
    for r in rs1:
        assert r.connection == c1


@pytest.mark.unit
@pytest.mark.smoke
def test_incremental_decode(options):
    '''Tests decoding incrementally'''
    from intertwine.config import ToxConfig
    from intertwine.problems.models import (Problem, ProblemConnection,
                                            ProblemConnectionRating, Trackable)
    from data.data_process import DataSessionManager, erase_data, decode

    # DSM only creates a session if one doesn't exist
    dsm = DataSessionManager(ToxConfig.DATABASE)
    session = dsm.session
    assert session is not None

    # Erase data
    erase_data(session, confirm='ERASE')

    # Initial data load:
    u0 = decode(session, 'data/problems/problems00.json')
    for updates in u0.values():
        session.add_all(updates)
    session.commit()
    p0 = session.query(Problem).filter_by(name='Poverty').one()
    assert p0.name == 'Poverty'

    # Simulate impact of app restart on Trackable by clearing it:
    Trackable.clear_instances()

    # Next data load:
    u1 = decode(session, 'data/problems/problems01.json')
    for updates in u1.values():
        session.add_all(updates)
    session.commit()
    p1 = session.query(Problem).filter_by(name='Homelessness').one()
    assert p1.name == 'Homelessness'

    # Simulate impact of app restart on Trackable by clearing it:
    Trackable.clear_instances()

    # Next data load:
    u2 = decode(session, 'data/problems/problems02.json')
    for updates in u2.values():
        session.add_all(updates)
    session.commit()
    p2 = session.query(Problem).filter_by(name='Domestic Violence').one()
    assert p2.name == 'Domestic Violence'

    # Make sure they're still the same problems
    assert p0 == Problem['poverty']
    assert p1 == Problem['homelessness']
    assert p2 == Problem['domestic_violence']

    c1 = session.query(ProblemConnection).filter(
        ProblemConnection.connection_type == 'scoped',
        ProblemConnection.broader == p0,
        ProblemConnection.narrower == p1).one()
    assert c1.connection_type == 'scoped'
    assert c1.broader == p0
    assert c1.narrower == p1

    c2 = session.query(ProblemConnection).filter(
        ProblemConnection.connection_type == 'causal',
        ProblemConnection.driver == p2,
        ProblemConnection.impact == p1).one()
    assert c2.connection_type == 'causal'
    assert c2.driver == p2
    assert c2.impact == p1

    rs1 = session.query(ProblemConnectionRating).filter(
        ProblemConnectionRating.connection == c1)
    assert len(rs1.all()) > 0
    for r in rs1:
        assert r.connection == c1

    rs2 = session.query(ProblemConnectionRating).filter(
        ProblemConnectionRating.connection == c2,
        ProblemConnectionRating.problem_scope == p1,
        ProblemConnectionRating.org_scope.is_(None),
        ProblemConnectionRating.geo_scope == 'United States/Texas/Austin')
    assert len(rs2.all()) > 0
    for r in rs2:
        assert r.connection == c2
        assert r.problem_scope == p1
        assert r.org_scope is None
        assert r.geo_scope == 'United States/Texas/Austin'

    # Simulate impact of app restart on Trackable by clearing it:
    Trackable.clear_instances()

    # Try reloading existing data (none should be loaded):
    u2_repeat = decode(session, 'data/problems/problems02.json')
    for updates in u2_repeat.values():
        assert len(updates) == 0
