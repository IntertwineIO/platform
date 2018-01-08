# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
from itertools import chain

from alchy.model import ModelBase

from intertwine.initiation import InitiationMixin, InitiationMetaMixin
from intertwine.trackable import Trackable
from intertwine.trackable.utils import build_table_model_map
from intertwine.utils.enums import UriType
from intertwine.utils.jsonable import Jsonable, JsonProperty
from intertwine.utils.mixins import AutoTableMixin

if sys.version_info >= (3,):
    unicode = str


class BaseIntertwineMeta(InitiationMetaMixin, Trackable):
    pass


class BaseIntertwineModel(InitiationMixin, Jsonable, AutoTableMixin,
                          ModelBase):

    ID_FIELDS = Jsonable.ID_FIELDS | {'uri'}
    URI_TYPE = UriType.NATURAL
    URI_EXCLUSIONS = {'org'}  # Org is not yet supported

    @classmethod
    def get_blueprint_name(cls):
        '''Get blueprint name from containing module'''
        try:
            return cls._blueprint_name
        except AttributeError:
            cls._blueprint_name = cls.__module__.split('.')[-2]
            return cls._blueprint_name

    @classmethod
    def get_sub_blueprint_name(cls):
        '''Get sub-blueprint name from class constant'''
        try:
            return cls.SUB_BLUEPRINT
        except AttributeError:
            return None

    @property
    def uri(self):
        '''Default URI property based on natural or primary key'''
        try:
            if self.__class__.URI_TYPE is UriType.NATURAL:
                return self.form_uri(self.derive_key())
            elif self.__class__.URI_TYPE is UriType.PRIMARY:
                return self.form_uri(self.pk)
            else:
                raise ValueError('Unknown UriType: {}'.format(
                    self.__class__.URI_TYPE))
        except AttributeError:
            return None

    jsonified_uri = JsonProperty(name='uri', before='json_key')

    @classmethod
    def form_uri(cls, components, sub=False, deconstruct=True):
        '''
        Form URI from given components

        components: Iterable of URL components, usually a Trackable Key
            namedtuple derived from the instance or formed manually
        sub=False: If True, start with sub-blueprint (exclude blueprint)
        deconstruct=True If True, recursively deconstruct components
        return: URI composed from the components
        '''
        # Check for exclusions and filter them out
        exclusions = None
        try:
            exclusions = cls.URI_EXCLUSIONS
            components_dict = components._asdict()
            components = (
                component for field, component in components_dict.items()
                if field not in exclusions)
        except AttributeError:
            pass
        # Recursively deconstruct components if flag is True (default)
        if deconstruct:
            components = chain(*(
                component.deconstruct(exclusions=exclusions)
                if hasattr(component, 'deconstruct')
                else (component,) for component in components))

        components = (unicode(component) if component is not None else ''
                      for component in components)

        sub_blueprint = cls.get_sub_blueprint_name()

        if sub:
            all_components = (
                chain(('', sub_blueprint), components)  # '' to prefix /
                if sub_blueprint else chain(('',), components))
        else:
            blueprint = cls.get_blueprint_name()
            all_components = (
                chain(('', blueprint, sub_blueprint), components)
                if sub_blueprint else chain(('', blueprint), components))

        return '/'.join(all_components)

    def json_key(self, key_type=None, raw=False, tight=True, **kwds):
        '''JSON key supports URI (default), NATURAL, and PRIMARY'''
        if key_type:
            if key_type is self.JsonKeyType.URI:
                uri = self.uri
                if uri:
                    return uri
                raise NotImplementedError('{cls} instance missing URI'
                                          .format(cls=self.__class__))
            if key_type is self.JsonKeyType.NATURAL:
                return self.trepr(raw=raw, tight=tight)
            return super(BaseIntertwineModel, self).json_key(
                key_type=key_type, raw=raw, tight=tight, **kwds)

        for default_key_type in reversed(self.JsonKeyType):
            try:
                return self.json_key(default_key_type, raw, tight, **kwds)
            except (AttributeError, TypeError, NotImplementedError):
                pass

        raise KeyError('Unable to create JSON key')

    @classmethod
    def initialize_table_model_map(cls):
        '''Initialize table model map; invoke after loading all models'''
        cls._table_model_map = build_table_model_map(cls)
