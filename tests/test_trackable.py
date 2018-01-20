#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from tests.builders.master import Builder


@pytest.mark.unit
def test_trackable_class_keys(session):
    '''Test Trackable Class Keys'''
    from intertwine.trackable import Trackable

    for class_name, cls in Trackable._classes.items():
        key_class_name = cls.Key.__name__.split('Key')[0]
        assert key_class_name == class_name

        builder = Builder(cls, optional=False)
        inst = builder.build()
        derived_key = inst.derive_key()
        assert cls.key_model(derived_key) is cls

        created_key = cls.create_key(**derived_key._asdict())
        assert created_key == derived_key
        assert created_key._asdict() == derived_key._asdict()


@pytest.mark.unit
def test_trackable_deconstruction_reconstruction(session):
    '''Test Trackable Deconstruction & Reconstruction'''
    from intertwine.trackable import Trackable

    for class_name, cls in Trackable._classes.items():
        builder = Builder(cls, optional=False)
        inst = builder.build()
        path_as_list, query_as_list = inst.deconstruct(named=False)
        path_as_od, query_as_od = inst.deconstruct(named=True)
        query_as_dict = dict(query_as_od)

        # Reconstruct with retrieve=False
        reconstructed_via_list = cls.reconstruct(path_as_list, query_as_list)
        assert reconstructed_via_list is inst
        reconstructed_via_od = cls.reconstruct(path_as_od, query_as_od)
        assert reconstructed_via_od is inst
        reconstructed_via_dict = cls.reconstruct(path_as_od, query_as_dict)
        assert reconstructed_via_dict is inst

        # Reconstruct as hyper-key
        hyper_key_via_list = cls.reconstruct(path_as_list, query_as_list,
                                             retrieve=True, as_key=True)
        hyper_key_via_od = cls.reconstruct(path_as_od, query_as_od,
                                           retrieve=True, as_key=True)
        assert hyper_key_via_list == hyper_key_via_od

        # Reconstitute from hyper-key
        reconstituted_via_list = cls.reconstitute(hyper_key_via_list)
        assert reconstituted_via_list is inst
        reconstituted_via_od = cls.reconstitute(hyper_key_via_od)
        assert reconstituted_via_od is inst

        session.add(inst)
        session.commit()

        # Reconstruct with retrieve=True (and as_key=False) queries the db
        reconstructed_via_list = cls.reconstruct(path_as_list, query_as_list,
                                                 retrieve=True)
        assert reconstructed_via_list is inst
        reconstructed_via_od = cls.reconstruct(path_as_od, query_as_od,
                                               retrieve=True)
        assert reconstructed_via_od is inst

        # Reconstruct as key
        key = inst.derive_key()
        key_via_list = cls.reconstruct(path_as_list, query_as_list,
                                       as_key=True)
        assert key_via_list == key
        key_via_od = cls.reconstruct(path_as_od, query_as_od, as_key=True)
        assert key_via_od == key


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
