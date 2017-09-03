# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from alchy.model import ModelBase

from .trackable import Trackable
from .utils.mixins import AutoTableMixin, Jsonable


class BaseIntertwineMeta(Trackable):

    def __init__(cls, name, bases, attr):
        super(BaseIntertwineMeta, cls).__init__(name, bases, attr)
        cls._class_init_()


class BaseIntertwineModel(Jsonable, AutoTableMixin, ModelBase):

    @classmethod
    def _class_init_(cls):
        # the delegation chain stops here
        assert not hasattr(super(BaseIntertwineModel, cls), '_class_init_')
