# -*- coding: utf-8 -*-
from types import FunctionType


class singleton:
    memoized = {}

    def __init__(self, *args, **kwds):
        # determine type of decoration

        self.args = args
        self.kwds = kwds
        self.key = (args, tuple((k, v) for k, v in kwds.items()))
        self.func = args[0] if len(args) > 0 and isinstance(args[0], FunctionType) else None
        if self.func and self.key not in self.memoized:
            self.memoized[self.key] = self.func(*args, **kwds)
        print('init args:', args)
        print('init kwds:', kwds)

    def __call__(self, *args, **kwds):

        if self.func is None:
            self.func = args[0] if len(args) > 0 and isinstance(args[0], FunctionType) else None
        if self.func and self.key not in self.memoized:
            self.memoized[self.key] = self.func(*args, **kwds)

        return self.memoized[self.key]
        print('call args:', args)
        print('call kwds:', kwds)


def memoize(func):

    return singleton(func)
