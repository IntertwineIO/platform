#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_app_created(options):
    """Test that a working app is created"""
    import flask
    from intertwine import create_app

    config = options['config']
    app = create_app(config=config)
    assert 'SERVER_NAME' in app.config
    server = '{}:{}'.format(options['host'], options['port'])
    host = (app.config.get('SERVER_NAME') or server).split(':')[0]
    port = (app.config.get('SERVER_NAME') or server).split(':')[-1]
    app.config['SERVER_NAME'] = '{}:{}'.format(host, port)

    with app.app_context():
        rv = flask.url_for('main.render')
        assert rv == 'https://{}:{}/'.format(host, port)


@pytest.mark.unit
@pytest.mark.smoke
def test_database_created(options):
    """Test that database is created"""
    import os
    from intertwine import create_app

    # Find the database file
    config = options['config']
    app = create_app(config=config)
    filepath = app.config['DATABASE'].split('///')[-1]
    if os.path.exists(filepath):
        os.remove(filepath)
    # Start over -- this should recreate the database
    app = create_app(config=config)
    assert 'SERVER_NAME' in app.config
    server = '{}:{}'.format(options['host'], options['port'])
    host = (app.config.get('SERVER_NAME') or server).split(':')[0]
    port = (app.config.get('SERVER_NAME') or server).split(':')[-1]
    app.config['SERVER_NAME'] = '{}:{}'.format(host, port)

    with app.app_context():
        if not filepath.endswith('://'):
            assert os.path.exists(filepath)
