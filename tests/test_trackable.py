#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_trackable_tget(session):
    '''Tests Trackable get (tget)'''
    from intertwine.problems.models import Problem
    from intertwine.trackable import Trackable

    problem_name = 'Test Problem'
    problem_key = Problem.create_key('Test Problem')
    assert len(problem_key) == 1
    nada = 'nada'

    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=False)
    assert tget_problem == nada

    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=True)
    assert tget_problem == nada

    problem = Problem(problem_name)  # This registers the key

    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=False)
    assert tget_problem is problem

    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=True)
    assert tget_problem is problem

    # Unpacked 1-tuples can also be used to get from the registry
    tget_problem = Problem.tget(problem_key.human_id, query_on_miss=False)
    assert tget_problem is problem

    session.add(problem)
    session.commit()

    Trackable.clear_all()  # This deregisters the key

    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=False)
    assert tget_problem == nada

    # This registers the key since it is found in the database
    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=True)
    assert tget_problem is problem

    tget_problem = Problem.tget(problem_key, default=nada, query_on_miss=False)
    assert tget_problem is problem

    Trackable.clear_all()  # This deregisters the key

    # Unpacked 1-tuples can also be used to get from the database
    tget_problem = Problem.tget(problem_key.human_id, query_on_miss=True)
    assert tget_problem is problem


@pytest.mark.unit
@pytest.mark.smoke
def test_trackable_indexability(session):
    '''Tests Trackable indexability (via []s)'''
    from intertwine.problems.models import Problem
    from intertwine.trackable import Trackable
    from intertwine.trackable.exceptions import (
        KeyMissingFromRegistryAndDatabase)

    problem_name = 'Test Problem'
    problem_key = Problem.create_key('Test Problem')
    assert len(problem_key) == 1

    with pytest.raises(KeyMissingFromRegistryAndDatabase):  # a KeyError
        Problem[problem_key]

    with pytest.raises(KeyError):
        Problem[problem_key]

    problem = Problem(problem_name)  # This registers the key

    indexed_problem = Problem[problem_key]
    assert indexed_problem is problem

    # Unpacked 1-tuples can also be used to index from the registry
    indexed_problem = Problem[problem_key.human_id]
    assert indexed_problem is problem

    session.add(problem)
    session.commit()
    Trackable.clear_all()  # This deregisters the key

    # This registers the key since it is found in the database
    indexed_problem = Problem[problem_key]
    assert indexed_problem is problem

    Trackable.clear_all()  # This deregisters the key

    # Unpacked 1-tuples can also be used to index from the database
    indexed_problem = Problem[problem_key.human_id]
    assert indexed_problem is problem
