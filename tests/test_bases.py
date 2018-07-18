#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest

from tests.builders.master import Builder


@pytest.mark.unit
def test_uri_formation_and_instantiation(session):
    """Test URI formation and instantiation"""
    from intertwine.trackable import Trackable
    from intertwine import IntertwineModel
    from intertwine.utils.enums import UriType

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
