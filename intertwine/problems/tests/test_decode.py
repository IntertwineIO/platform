#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem(options):
    '''Tests decoding a standard problem'''


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem_connection(options):
    '''Tests decoding a standard problem connection'''
    from intertwine import create_app
    from intertwine.config import ToxConfig
    from intertwine.problems.models import db

    app = create_app(ToxConfig)
    with app.app_context():
        session = db.session
    assert session is not None


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem_connection_rating(options):
    '''Tests decoding a standard problem connection rating'''
    from intertwine import create_app
    from intertwine.config import ToxConfig
    from intertwine.problems.models import db

    app = create_app(ToxConfig)
    with app.app_context():
        session = db.session
    assert session is not None


@pytest.mark.unit
@pytest.mark.smoke
def test_incremental_decode(options):
    '''Tests decoding incrementally'''
    from intertwine import create_app
    from intertwine.config import ToxConfig
    from intertwine.problems.models import db

    app = create_app(ToxConfig)
    with app.app_context():
        session = db.session
    assert session is not None
