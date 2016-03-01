#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_create_local_database(options):
    '''Tests that a local database is generated'''
    import os
    import flask
    from intertwine import create_app

    config = options['config']
    filepath = config['DATABASE'].split('///')[-1]
    if os.path.exists(filepath):
        os.remove(filepath)
    app = create_app(config)
    host = app.config.get('HOST') or options.get('host')
    port = app.config.get('PORT') or options.get('port')
    app.config['SERVER_NAME'] = '{}:{}'.format(host, port)

    with app.app_context():
        rv = flask.url_for('index')
        assert rv == 'https://localhost/'

    assert os.path.exists(filepath)


@pytest.mark.unit
@pytest.mark.smoke
def test_table_generation(options):
    '''Tests decoding incrementally'''

