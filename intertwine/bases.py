# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from alchy.model import ModelBase

from intertwine.trackable import Trackable
from intertwine.utils.jsonable import Jsonable
from intertwine.utils.mixins import AutoTableMixin


class BaseIntertwineMeta(Trackable):

    def __init__(cls, name, bases, attr):
        super(BaseIntertwineMeta, cls).__init__(name, bases, attr)
        cls._class_init_()


class BaseIntertwineModel(Jsonable, AutoTableMixin, ModelBase):

    @classmethod
    def _class_init_(cls):
        # the delegation chain stops here
        assert not hasattr(super(BaseIntertwineModel, cls), '_class_init_')
