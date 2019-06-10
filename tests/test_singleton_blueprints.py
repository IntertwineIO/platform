# -*- coding: utf-8 -*-
from intertwine.utils.blueprints import create_singleton_blueprint


def test_singleton_blueprints():
    x = create_singleton_blueprint('example', __name__)
    y = create_singleton_blueprint('example', __name__)
    assert(x == y)
    assert(x is y)

    z = create_singleton_blueprint('example2', __name__)
    assert(x != z)
