#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class InitiationMetaMixin(object):

    def __init__(cls, name, bases, attr):
        super(InitiationMetaMixin, cls).__init__(name, bases, attr)
        cls._class_init_()


class InitiationMixin(object):

    @classmethod
    def _class_init_(cls):
        # the delegation chain stops here
        assert not hasattr(super(InitiationMixin, cls), '_class_init_')
