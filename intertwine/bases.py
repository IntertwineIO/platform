# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from alchy.model import ModelBase

from intertwine.initiation import InitiationMixin, InitiationMetaMixin
from intertwine.trackable import Trackable
from intertwine.utils.jsonable import Jsonable
from intertwine.utils.mixins import AutoTableMixin


class BaseIntertwineMeta(InitiationMetaMixin, Trackable):
    pass


class BaseIntertwineModel(InitiationMixin, Jsonable, AutoTableMixin,
                          ModelBase):
    pass
