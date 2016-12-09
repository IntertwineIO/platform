#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.skip('Feature not ready')
def test_singleton_blueprints():
    from intertwine.utils.blueprints import create_singleton_blueprint

    x = create_singleton_blueprint('example', __name__)
    y = create_singleton_blueprint('example', __name__)
    assert(x == y)
    assert(x is y)

    z = create_singleton_blueprint('example2', __name__)
    assert(x != z)


@pytest.mark.skip('Feature not ready')
def test_singleton_decorator():
    from intertwine.utils.decorators import singleton

    @singleton(parametric=True)
    def test(*args, **kwds):
        print('hi')
        return 'Blissful:', args, kwds

    x = test()
    y = test()
    assert x == y


def test_memoize_decorator():
    from intertwine.utils.decorators import memoize

    @memoize
    def test(*args, **kwds):
        print('hi')
        return 'Blissful:', args, kwds

    x = test()
    y = test()
    assert x == y
