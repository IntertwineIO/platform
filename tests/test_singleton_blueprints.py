#!/usr/bin/env python
# -*- coding: utf-8 -*-


def test_singleton_blueprints():
    from intertwine.utils.blueprints import create_singleton_blueprint

    x = create_singleton_blueprint('example', __name__)
    y = create_singleton_blueprint('example', __name__)
    assert(x == y)
    assert(x is y)

    z = create_singleton_blueprint('example2', __name__)
    assert(x != z)
