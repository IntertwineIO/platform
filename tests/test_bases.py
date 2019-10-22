# -*- coding: utf-8 -*-
import pytest

from intertwine import IntertwineModel
from intertwine.communities.models import Community
from intertwine.trackable import Trackable
from intertwine.utils.enums import UriType
from tests.builders.master import Builder

@pytest.mark.unit
def test_uri_formation_and_instantiation(session, caching):
    """Test URI formation and instantiation"""
    for class_name, cls in Trackable._classes.items():
        # Register existing for builders since registry is cleared below
        Trackable.register_existing(session)

        builder = Builder(cls, optional=False)
        inst = builder.build()
        uri = inst.uri
        if cls.URI_TYPE is UriType.NATURAL:
            instantiated_via_uri = IntertwineModel.instantiate_uri(uri)
            assert instantiated_via_uri is inst

        session.add(inst)
        session.commit()
        uri = inst.uri

        Trackable.clear_all()  # Deregister key to test retrieve from db

        instantiated_from_db_via_uri = IntertwineModel.instantiate_uri(uri)
        assert instantiated_from_db_via_uri is inst


@pytest.mark.unit
def test_uri_formation_and_instantiation_with_null_query_value(session, caching):
    """Test URI formation and instantiation"""
    cls = Community
    # Register existing for builders since registry is cleared below
    Trackable.register_existing(session)

    builder = Builder(cls, optional=False)
    inst = builder.build(org=None)  # org is a query parameter

    uri = inst.uri
    assert 'org' not in uri, 'org should not be in uri since it is null'
    assert '?' not in uri, 'there should be no query string since org is null'

    assert cls.URI_TYPE is UriType.NATURAL
    instantiated_via_uri = IntertwineModel.instantiate_uri(uri)
    assert instantiated_via_uri is inst

    session.add(inst)
    session.commit()
    uri = inst.uri

    Trackable.clear_all()  # Deregister key to test retrieve from db

    instantiated_from_db_via_uri = IntertwineModel.instantiate_uri(uri)
    assert instantiated_from_db_via_uri is inst
