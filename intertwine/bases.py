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

    def json_key(self, key_type=None, raw=False, tight=True, **kwds):
        '''JSON key supports NATURAL_KEY (default), URI, and PRIMARY_KEY'''
        if not key_type or key_type is self.JsonKeyType.NATURAL_KEY:
            return self.trepr(raw=raw, tight=tight)
        if key_type is self.JsonKeyType.URI:
            return self.uri
        return super(BaseIntertwineModel, self).json_key(
            key_type=key_type, raw=raw, tight=tight, **kwds)
