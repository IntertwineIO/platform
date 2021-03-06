# -*- coding: utf-8 -*-
import os
import pytest

from intertwine import create_app


@pytest.mark.skip("Auth is currently disabled")
@pytest.mark.unit
@pytest.mark.smoke
def test_auth_admin_(options):
    """Test auth"""
    config = options['config']
    app = create_app(config)
    assert 'auth' in app.blueprints

    app_rules = {
        rule.endpoint: rule
        for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith('auth')
    }

    endpoints = {
        'auth.render': '/',
        'auth.login': '/login',
        'auth.logout': '/logout',
    }
    for endpoint, rule in app_rules.items():
        url = endpoints[endpoint]
        assert rule.rule.endswith(url)


@pytest.mark.skip("Auth is currently disabled")
@pytest.mark.unit
@pytest.mark.smoke
def test_auth_table_generation(options):
    """Test decoding incrementally"""
    config = options['config']
    app = create_app(config)
    filepath = app.config['DATABASE'].split('///')[-1]
    assert 'SERVER_NAME' in app.config
    server = '{}:{}'.format(options['host'], options['port'])
    host = (app.config.get('SERVER_NAME') or server).split(':')[0]
    port = (app.config.get('SERVER_NAME') or server).split(':')[-1]
    app.config['SERVER_NAME'] = '{}:{}'.format(host, port)

    with app.app_context():
        if not filepath.endswith('://'):
            assert os.path.exists(filepath)
