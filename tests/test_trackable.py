# -*- coding: utf-8 -*-
import pytest

from intertwine.communities.models import Community
from intertwine.problems.models import Problem
from intertwine.trackable import Trackable
from intertwine.trackable.exceptions import KeyMissingFromRegistryAndDatabase
from tests.builders.master import Builder


@pytest.mark.unit
def test_trackable_class_keys(session):
    """Test Trackable Class Keys"""
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
@pytest.mark.parametrize('org_is_null', [(False,), (True,)])
def test_trackable_deconstruction_reconstruction(session, org_is_null):
    """Test Trackable Deconstruction & Reconstruction"""
    for class_name, cls in Trackable._classes.items():
        builder = Builder(cls, optional=False)

        # Test null query parameter value
        has_null_org = org_is_null and 'org' in cls.Key._fields
        inst = builder.build(org=None) if has_null_org else builder.build()

        path, query = inst.deconstruct(query_fields={'org'})
        path_values = list(path.values())
        query = dict(query)

        # Reconstruct with retrieve=False
        kwargs = dict(query=query, query_fields={'org'}, retrieve=False)
        reconstructed = cls.reconstruct(path, **kwargs)
        assert reconstructed is inst
        reconstructed_via_list = cls.reconstruct(path_values, **kwargs)
        assert reconstructed_via_list is inst

        # Reconstruct as hyper-key
        hyper_key = cls.reconstruct_key(path, query=query, query_fields={'org'})
        hyper_key_via_list = cls.reconstruct_key(path_values, query=query, query_fields={'org'})
        assert hyper_key_via_list == hyper_key

        # Reconstitute from hyper-key
        reconstituted = cls.reconstitute(hyper_key)
        assert reconstituted is inst

        session.add(inst)
        session.commit()

        # Retrieve from hyper-key (query db)
        retrieved = cls.retrieve(hyper_key)
        assert retrieved is inst

        # Reconstruct with retrieve=True (query db)
        kwargs = dict(query=query, query_fields={'org'}, retrieve=True)
        reconstructed = cls.reconstruct(path, **kwargs)
        assert reconstructed is inst
        reconstructed_via_list = cls.reconstruct(path_values, **kwargs)
        assert reconstructed_via_list is inst


@pytest.mark.unit
def test_trackable_tget(session):
    """Test Trackable get (tget)"""
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
    """Test Trackable indexability (via []s)"""
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
