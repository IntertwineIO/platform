#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pendulum
from sqlalchemy import Column, orm, types
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func

from .jsonable import JsonProperty
from .structures import MultiKeyMap
from .tools import camelCaseTo_snake_case


class AutoIdMixin(object):
    '''Automatically creates a primary id key'''
    id = Column(types.Integer, primary_key=True)
    # Ensure id is first field when jsonified
    jsonified_id = JsonProperty(name='id', begin=True)


class AutoTablenameMixin(object):
    '''Autogenerates table name'''
    @declared_attr
    def __tablename__(cls):
        return camelCaseTo_snake_case(cls.__name__)


class AutoTableMixin(AutoIdMixin, AutoTablenameMixin):
    '''Standardizes automatic tables'''


class AutoTimestampMixin(object):
    '''Automatically save timestamps on create and update'''
    tz = pendulum.timezone('UTC')

    _created_timestamp = Column(types.DateTime(), server_default=func.now())
    _updated_timestamp = Column(types.DateTime(), onupdate=func.now())

    @property
    def _get_created_timestamp(self):
        created = self._created_timestamp
        return self.tz.convert(created) if created else None

    @declared_attr
    def created_timestamp(cls):  # @NoSelf
        return orm.synonym('_created_timestamp',
                           descriptor=cls._get_created_timestamp)

    jsonified_created_timestamp = JsonProperty(name='created_timestamp',
                                               end=True)

    @property
    def _get_updated_timestamp(self):
        updated = self._updated_timestamp
        return (self.tz.convert(updated) if updated
                else self.created_timestamp)

    @declared_attr
    def updated_timestamp(cls):  # @NoSelf
        return orm.synonym('_updated_timestamp',
                           descriptor=cls._get_updated_timestamp)

    jsonified_updated_timestamp = JsonProperty(name='updated_timestamp',
                                               end=True)


class KeyedUp(object):
    '''KeyedUp mixin for caching with multiple distinct field keys'''

    # Override with fields to be used by KeyedUp
    KEYED_UP_FIELDS = NotImplemented
    _keyed_up_map = None

    @classmethod
    def get_by(cls, field, key, default=None):
        if cls._keyed_up_map is None:
            cls._create_keyed_up_map()
        return cls._keyed_up_map.get_by(field, key, default)

    @classmethod
    def get_map_by(cls, field):
        if cls._keyed_up_map is None:
            cls._create_keyed_up_map()
        return cls._keyed_up_map.get_map_by(field)

    @classmethod
    def _create_keyed_up_map(cls):
        cls._keyed_up_map = MultiKeyMap(fields=cls.KEYED_UP_FIELDS,
                                        things=cls._all_the_keyed_up_things())

    @classmethod
    def _all_the_keyed_up_things(cls):
        return cls.query.all()

    def __init__(self, *args, **kwds):
        if self.KEYED_UP_FIELDS is NotImplemented:
            raise NotImplementedError(
                'KEYED_UP_FIELDS must be defined for KeyedUp class')
        super(KeyedUp, self).__init__(*args, **kwds)
