#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_app_created(options):
    '''Tests that a working app is created'''
    import flask
    from intertwine import create_app

    config = options['config']
    app = create_app(config)
    assert 'HOST' in app.config
    assert 'PORT' in app.config
    host = app.config['HOST']
    port = app.config['PORT']
    assert 'SERVER_NAME' in app.config
    app.config['SERVER_NAME'] = '{}:{}'.format(host, port)

    with app.app_context():
        rv = flask.url_for('index')
        assert rv == 'http://{}:{}/'.format(host, port)


@pytest.mark.unit
@pytest.mark.smoke
def test_database_created(options):
    '''Tests that database is created'''
    import os
    import flask
    from intertwine import create_app

    config = options['config']
    filepath = config['DATABASE'].split('///')[-1]
    if os.path.exists(filepath):
        os.remove(filepath)
    app = create_app(config)
    assert 'HOST' in app.config
    assert 'PORT' in app.config
    host = app.config['HOST']
    port = app.config['PORT']
    assert 'SERVER_NAME' in app.config
    app.config['SERVER_NAME'] = '{}:{}'.format(host, port)

    with app.app_context():
        rv = flask.url_for('index')
        assert rv == 'http://{}:{}/'.format(host, port)

    assert os.path.exists(filepath)


@pytest.mark.unit
@pytest.mark.smoke
def test_table_generation(options):
    '''Tests decoding incrementally'''
