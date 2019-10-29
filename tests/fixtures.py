# -*- coding: utf-8 -*-
import os

import pytest
from alchy.model import extend_declarative_base

from intertwine import IntertwineModel, create_app, intertwine_db
from intertwine.trackable import Trackable
from config import ToxConfig


@pytest.fixture(scope="module")
def options():
    """Capture configuration data and validate data is available"""
    options = {
        'host': '127.0.0.1',
        'port': 5000,
        'config': ToxConfig(),
    }

    return options


# TODO: Update for alchy
TESTDB = 'test-sqlite.db'
TESTDB_FOLDER = os.path.dirname(os.path.realpath(__file__))
TESTDB_PATH = os.path.join(TESTDB_FOLDER, TESTDB)
TEST_DATABASE_URI = 'sqlite:///' + TESTDB_PATH


class PyTestConfig(ToxConfig):
    SQLALCHEMY_DATABASE_URI = TEST_DATABASE_URI
    # SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture(scope='function')
def app(request):
    """Create session-wide test `Flask` application"""
    app = create_app(__name__, PyTestConfig)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        Trackable.clear_all()
        ctx.pop()

    # Teardown application context at the end of usage (session)
    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='function')
def db(app, request):
    """Create session-wide test database"""
    if os.path.exists(TESTDB_PATH):
        os.unlink(TESTDB_PATH)

    intertwine_db.app = app
    intertwine_db.create_all()

    def teardown():
        Trackable.clear_all()
        intertwine_db.drop_all()
        if os.path.exists(TESTDB_PATH):
            os.unlink(TESTDB_PATH)

    request.addfinalizer(teardown)
    return intertwine_db


@pytest.fixture(scope='function')
def session(db, request):
    """Create new database session for a test"""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)

    extend_declarative_base(IntertwineModel, session=session)

    db.session = session

    def teardown():
        Trackable.clear_all()
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    assert session is not None
    return session


@pytest.fixture(scope='function')
def client(app, request):
    """Create test client"""
    app.config['TESTING'] = True
    client = app.test_client()

    def teardown():
        app.config['TESTING'] = False

    request.addfinalizer(teardown)
    return client


@pytest.fixture(scope='function')
def caching(app, request):
    """Enable caching of model instances"""
    with Trackable.caching():
        yield
