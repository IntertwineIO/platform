# -*- coding: utf-8 -*-
import pytest


def get_decorator(*dargs, **dkwds):
    from intertwine.auth.decorators import login_required

    if dargs and dkwds:
        decorator = login_required(*dargs, **dkwds)
    elif dargs:
        decorator = login_required(*dargs)
    elif dkwds:
        decorator = login_required(**dkwds)
    else:
        decorator = login_required
    return decorator


def get_output(callable, *args, **kwds):
    if args and kwds:
        output = callable(*args, **kwds)
    elif args:
        output = callable(*args)
    elif kwds:
        output = callable(**kwds)
    else:
        output = callable()

    return output


def get_app():
    from flask import Flask
    from werkzeug.routing import Rule

    app = Flask(__name__)
    app.url_map.add(Rule('/', endpoint='index'))
    return app


@pytest.mark.unit
@pytest.mark.parametrize("args, kwds, dargs, dkwds, expected, raises", [
    (None, None, None, None, None, False),
    (('a', 'b'), {'c': 'd'}, None, None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None, None, ('e', 'f'), False),
    (None, {'g': 'h'}, None, None, {'g': 'h'}, False),

    (None, None, (1, ), None, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ), None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ), None, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ), None, {'g': 'h'}, False),

    (None, None, (1, ), {'3': '4'}, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ),  {'3': '4'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ),  {'3': '4'}, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ),  {'3': '4'}, {'g': 'h'}, False),

    (None, None, None, {'5': '6'}, None, False),
    (('a', 'b'), {'c': 'd'}, None,  {'5': '6'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None,  {'5': '6'}, ('e', 'f'), False),
    (None, {'g': 'h'}, None,  {'5': '6'}, {'g': 'h'}, False),
])
def test_function_decorator(args, kwds, dargs, dkwds, expected, raises):
    args = () if args is None else args
    kwds = {} if kwds is None else kwds
    dargs = () if dargs is None else dargs
    dkwds = {} if dkwds is None else dkwds
    decorator = get_decorator(*dargs, **dkwds)

    if not raises:
        @decorator
        def foo(*targs, **tkwds):
            if targs and tkwds:
                return targs, tkwds
            elif targs:
                return targs
            elif tkwds:
                return tkwds

        output = get_output(foo, *args, **kwds)
        assert output == expected


@pytest.mark.unit
@pytest.mark.parametrize("args, kwds, dargs, dkwds, expected, raises", [
    (None, None, None, None, None, False),
    (('a', 'b'), {'c': 'd'}, None, None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None, None, ('e', 'f'), False),
    (None, {'g': 'h'}, None, None, {'g': 'h'}, False),

    (None, None, (1, ), None, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ), None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ), None, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ), None, {'g': 'h'}, False),

    (None, None, (1, ), {'3': '4'}, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ),  {'3': '4'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ),  {'3': '4'}, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ),  {'3': '4'}, {'g': 'h'}, False),

    (None, None, None, {'5': '6'}, None, False),
    (('a', 'b'), {'c': 'd'}, None,  {'5': '6'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None,  {'5': '6'}, ('e', 'f'), False),
    (None, {'g': 'h'}, None,  {'5': '6'}, {'g': 'h'}, False),
])
def test_class_decorator(args, kwds, dargs, dkwds, expected, raises):
    args = () if args is None else args
    kwds = {} if kwds is None else kwds
    dargs = () if dargs is None else dargs
    dkwds = {} if dkwds is None else dkwds
    decorator = get_decorator(*dargs, **dkwds)

    if not raises:
        @decorator
        class bar(object):

            def __init__(self, *targs, **tkwds):
                self.args = targs
                self.kwds = tkwds

            @property
            def value(self):
                if self.args and self.kwds:
                    value = self.args, self.kwds
                elif self.args:
                    value = self.args
                elif self.kwds:
                    value = self.kwds
                else:
                    value = None
                return value

        instance = bar(*args, **kwds)
        assert instance.value == expected


@pytest.mark.unit
@pytest.mark.parametrize("args, kwds, dargs, dkwds, expected, raises", [
    pytest.mark.xfail((None, None, None, None, None, False), reason='decorated class method needs self'),
    pytest.mark.xfail((('a', 'b'), {'c': 'd'}, None, None, (('a', 'b'), {'c': 'd'}), False), reason='decorated class method needs self'),
    pytest.mark.xfail((('e', 'f'), None, None, None, ('e', 'f'), False), reason='decorated class method needs self'),
    pytest.mark.xfail((None, {'g': 'h'}, None, None, {'g': 'h'}, False), reason='decorated class method needs self'),

    (None, None, (1, ), None, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ), None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ), None, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ), None, {'g': 'h'}, False),

    (None, None, (1, ), {'3': '4'}, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ),  {'3': '4'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ),  {'3': '4'}, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ),  {'3': '4'}, {'g': 'h'}, False),

    (None, None, None, {'5': '6'}, None, False),
    (('a', 'b'), {'c': 'd'}, None,  {'5': '6'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None,  {'5': '6'}, ('e', 'f'), False),
    (None, {'g': 'h'}, None,  {'5': '6'}, {'g': 'h'}, False),
])
def test_class_method_decorator(args, kwds, dargs, dkwds, expected, raises):
    args = () if args is None else args
    kwds = {} if kwds is None else kwds
    dargs = () if dargs is None else dargs
    dkwds = {} if dkwds is None else dkwds
    decorator = get_decorator(*dargs, **dkwds)

    if not raises:
        class bar(object):

            def __init__(self, *targs, **tkwds):
                self.args = targs
                self.kwds = tkwds

            @decorator
            def value(self):
                if self.args and self.kwds:
                    value = self.args, self.kwds
                elif self.args:
                    value = self.args
                elif self.kwds:
                    value = self.kwds
                else:
                    value = None
                return value

        instance = bar(*args, **kwds)
        assert instance.value() == expected


@pytest.mark.unit
@pytest.mark.parametrize("args, kwds, dargs, dkwds, expected, raises", [
    (None, None, None, None, None, False),
    (('a', 'b'), {'c': 'd'}, None, None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None, None, ('e', 'f'), False),
    (None, {'g': 'h'}, None, None, {'g': 'h'}, False),

    (None, None, (1, ), None, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ), None, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ), None, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ), None, {'g': 'h'}, False),

    (None, None, (1, ), {'3': '4'}, None, False),
    (('a', 'b'), {'c': 'd'}, (1, ),  {'3': '4'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, (1, ),  {'3': '4'}, ('e', 'f'), False),
    (None, {'g': 'h'}, (1, ),  {'3': '4'}, {'g': 'h'}, False),

    (None, None, None, {'5': '6'}, None, False),
    (('a', 'b'), {'c': 'd'}, None,  {'5': '6'}, (('a', 'b'), {'c': 'd'}), False),
    (('e', 'f'), None, None,  {'5': '6'}, ('e', 'f'), False),
    (None, {'g': 'h'}, None,  {'5': '6'}, {'g': 'h'}, False),
])
def test_function_double_decorator(args, kwds, dargs, dkwds, expected, raises):
    args = () if args is None else args
    kwds = {} if kwds is None else kwds
    dargs = () if dargs is None else dargs
    dkwds = {} if dkwds is None else dkwds
    decorator = get_decorator(*dargs, **dkwds)
    app = get_app()

    if not raises:
        @decorator
        @app.endpoint('index')
        def foo(*targs, **tkwds):
            if targs and tkwds:
                return targs, tkwds
            elif targs:
                return targs
            elif tkwds:
                return tkwds

        output = get_output(foo, *args, **kwds)
        assert output == expected
