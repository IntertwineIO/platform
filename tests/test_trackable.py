#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from tests.builders.master import Builder


@pytest.mark.unit
def test_trackable_class_keys(session):
    '''Test Trackable Class Keys'''
    from intertwine.trackable import Trackable

    for class_name, cls in Trackable._classes.items():
        Key = cls.Key
        key_class_name, key_name = Key.__name__.split('_')
        assert key_class_name == class_name
        assert key_name == 'Key'

        builder = Builder(cls, optional=False)
        inst = builder.build()
        derived_key = inst.derive_key(generic=True)
        assert cls.key_model(derived_key) is cls

        created_key = cls.create_key(**derived_key._asdict())
        assert created_key == derived_key


@pytest.mark.unit
def test_trackable_deconstruction_reconstruction(session):
    '''Test Trackable Deconstruction & Reconstruction'''
    from intertwine.trackable import Trackable

    for class_name, cls in Trackable._classes.items():
        builder = Builder(cls, optional=False)
        inst = builder.build()
        deconstructed_via_list = list(inst.deconstruct())
        deconstructed_via_tuple = tuple(inst.deconstruct())

        # Reconstruct with retrieve=False
        reconstructed = cls.reconstruct(inst.deconstruct())
        assert reconstructed is inst
        reconstructed = cls.reconstruct(deconstructed_via_list)
        assert reconstructed is inst
        reconstructed = cls.reconstruct(deconstructed_via_tuple)
        assert reconstructed is inst

        # Reconstruct as hyper-key
        hyper_key = cls.reconstruct(inst.deconstruct(),
                                    retrieve=True, as_key=True)
        hyper_key_via_list = cls.reconstruct(deconstructed_via_list,
                                             retrieve=True, as_key=True)
        assert hyper_key_via_list == hyper_key
        hyper_key_via_tuple = cls.reconstruct(deconstructed_via_tuple,
                                              retrieve=True, as_key=True)
        assert hyper_key_via_tuple == hyper_key

        # Reconstitute from hyper-key
        reconstituted = cls.reconstitute(hyper_key)
        assert reconstituted is inst

        session.add(inst)
        session.commit()

        # Reconstruct with retrieve=True (and as_key=False) queries the db
        reconstructed = cls.reconstruct(inst.deconstruct(), retrieve=True)
        assert reconstructed is inst
        reconstructed = cls.reconstruct(deconstructed_via_list, retrieve=True)
        assert reconstructed is inst
        reconstructed = cls.reconstruct(deconstructed_via_tuple, retrieve=True)
        assert reconstructed is inst

        # Reconstruct as key
        key = cls.reconstruct(inst.deconstruct(), as_key=True)
        assert key == inst.derive_key()
        key_via_list = cls.reconstruct(deconstructed_via_list, as_key=True)
        assert key_via_list == key
        key_via_tuple = cls.reconstruct(deconstructed_via_tuple, as_key=True)
        assert key_via_tuple == key


@pytest.mark.unit
def test_trackable_tget(session):
    '''Tests Trackable get (tget)'''
    from intertwine.problems.models import Problem
    from intertwine.trackable import Trackable

    problem_name = 'Test Problem'
    problem_key = Problem.create_key(name='Test Problem')
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
def test_trackable_indexability(session):
    '''Tests Trackable indexability (via []s)'''
    from intertwine.problems.models import Problem
    from intertwine.trackable import Trackable
    from intertwine.trackable.exceptions import (
        KeyMissingFromRegistryAndDatabase)

    problem_name = 'Test Problem'
    problem_key = Problem.create_key(name='Test Problem')
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
